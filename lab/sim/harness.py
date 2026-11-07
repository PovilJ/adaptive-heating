"""Experiment harness: resolve controllers, run scenarios (in parallel), write results.

Used by lab/run.py; usable from Python too:

    from lab.sim.harness import run_one, run_many
    res = run_one("unit_curve", "jan_cold")                 # dict(meta, metrics, paths)
    rows = run_many(["unit_curve", "fixed_setpoint[setpoint=32]"], ["all"])
"""
from __future__ import annotations

import csv
import importlib
import importlib.util
import json
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from lab.data.common import RESULTS

OUT_DIR = RESULTS / "runs"


# ------------------------------------------------------------------------------------------
# controller specs: "name", "name[k=v,k=v]", "pkg.module:Class", "path/file.py:Class[k=v]"
# ------------------------------------------------------------------------------------------

def parse_value(v: str):
    s = v.strip()
    low = s.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("none", "null"):
        return None
    for cast in (int, float):
        try:
            return cast(s)
        except ValueError:
            pass
    try:
        return json.loads(s)
    except ValueError:
        return s


def parse_params(items):
    out = {}
    for it in items or ():
        if "=" not in it:
            raise ValueError(f"--param expects k=v, got {it!r}")
        k, v = it.split("=", 1)
        out[k.strip()] = parse_value(v)
    return out


def split_spec(spec: str):
    """'name[k=v,k=v]' -> ('name', {k: v})."""
    m = re.fullmatch(r"\s*([^\[\]]+?)\s*(?:\[(.*)\])?\s*", spec)
    if not m:
        raise ValueError(f"bad controller spec {spec!r}")
    base, inner = m.group(1), m.group(2)
    params = parse_params([p for p in (inner or "").split(",") if p.strip()])
    return base, params


def load_controller(base: str):
    """Instantiate a controller from a name in lab/controllers, 'pkg.module:Class' or 'file.py:Class'."""
    if ":" in base:
        mod_name, cls_name = base.rsplit(":", 1)
    else:
        mod_name, cls_name = base, None
    if mod_name.endswith(".py") or os.sep in mod_name:
        path = Path(mod_name).resolve()
        spec = importlib.util.spec_from_file_location(path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[path.stem] = mod
        spec.loader.exec_module(mod)
    else:
        try:
            mod = importlib.import_module(mod_name if "." in mod_name else f"lab.controllers.{mod_name}")
        except ModuleNotFoundError:
            mod = importlib.import_module(mod_name)
    if cls_name:
        cls = getattr(mod, cls_name)
    elif hasattr(mod, "CONTROLLER"):
        cls = mod.CONTROLLER
    else:
        cands = [v for v in vars(mod).values() if isinstance(v, type) and hasattr(v, "step") and hasattr(v, "reset")
                 and v.__module__ == mod.__name__]
        if len(cands) != 1:
            raise ValueError(f"{mod_name}: name the class with module:Class")
        cls = cands[0]
    return cls()


def _safe(s):
    return re.sub(r"[^A-Za-z0-9_.=+-]+", "_", s).strip("_")


def short_label(controller_spec):
    """Display label: file paths shortened to the file stem."""
    base, params = split_spec(controller_spec)
    mod, _, cls = base.partition(":")
    label = Path(mod).stem if (mod.endswith(".py") or os.sep in mod) else mod
    label += f":{cls}" if cls else ""
    if params:
        label += "[" + ",".join(f"{k}={v}" for k, v in params.items()) + "]"
    return label


def run_stem(controller_spec, scenario, variant, forecast, seed=0):
    """File stem of a run: scenario__controller__variant__forecast[__seedN]; a long controller
    label (file paths, many params) is shortened and made unique with a hash."""
    import hashlib
    label = _safe(short_label(controller_spec))
    if len(label) > 60:
        label = label[:50] + "_" + hashlib.sha1(controller_spec.encode()).hexdigest()[:8]
    return f"{scenario}__{label}__{_safe(variant)}__{forecast}" + (f"__seed{seed}" if seed else "")


# ------------------------------------------------------------------------------------------
# one run
# ------------------------------------------------------------------------------------------

CSV_FIELDS = ("t_out", "outdoor_s", "rh", "ghi", "pv", "dist", "room_s", "room_age", "t_air", "t_sens", "t_slab",
              "t_env", "t_ret", "t_sup", "outlet_s", "inlet_s", "t_ctrl", "sp", "delta", "quiet", "enabled", "mode",
              "comp", "started", "q", "p_out", "p_in", "p_tank", "dhw_dem", "writes", "link", "pump", "anchor")


def write_csv(path: Path, rec):
    import datetime as dt
    t = rec["t"]
    cols = [rec[k] for k in CSV_FIELDS]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(("time_utc", "local_hour") + CSV_FIELDS)
        lh = rec["local_hour"]
        stamps = [dt.datetime.fromtimestamp(int(x), dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ") for x in t]
        arr = np.column_stack([c.astype(float) for c in cols])
        txt = [",".join(f"{v:.4g}" if v == v else "" for v in row) for row in arr.tolist()]
        for s, h, row in zip(stamps, lh, txt):
            f.write(f"{s},{h:.3f},{row}\n")


def run_one(controller_spec: str, scenario: str, variant: str = "nominal", forecast: str = "noisy",
            params: dict | None = None, seed: int = 0, link_drops_per_day: float = 0.0, write: bool = True,
            csv_out: bool = True, out_dir: Path | None = None, record: bool = True):
    from lab.sim import scenarios as S
    from lab.sim import simulator as SIM

    base, spec_params = split_spec(controller_spec)
    ctrl = load_controller(base)
    p = dict(params or {})
    p.update(spec_params)
    if base == "reference_tuned" and "ref_target_offset" not in p:
        from lab.sim.ranking import tuned_offset
        p["ref_target_offset"] = tuned_offset(scenario, variant, seed, forecast, link_drops_per_day=link_drops_per_day,
                                              params={k: v for k, v in p.items() if k.startswith("ref_")})
    exo = S.build(scenario, variant, seed, link_drops_per_day)
    res = SIM.run(ctrl, exo, variant=variant, forecast=forecast, params=p, record=record or csv_out)
    res["meta"]["controller_spec"] = controller_spec
    paths = {}
    if write:
        od = Path(out_dir or OUT_DIR)
        od.mkdir(parents=True, exist_ok=True)
        stem = run_stem(controller_spec, scenario, variant, forecast, seed)
        jp = od / f"{stem}.json"
        jp.write_text(json.dumps(dict(meta=res["meta"], metrics=res["metrics"]), indent=1, default=float))
        paths["json"] = str(jp)
        if csv_out and res["rec"] is not None:
            cp = od / f"{stem}.csv"
            write_csv(cp, res["rec"])
            paths["csv"] = str(cp)
    res["paths"] = paths
    return res


def _job(args):
    kw = dict(args)
    res = run_one(**kw)
    m = res["metrics"]
    row = dict(scenario=kw["scenario"], controller=short_label(kw["controller_spec"]), variant=kw.get("variant", "nominal"),
               forecast=kw.get("forecast", "noisy"), seed=kw.get("seed", 0), wall_s=res["meta"]["wall_s"], **{
                   k: v for k, v in m.items() if not isinstance(v, (list, dict))})
    row["starts_by_outdoor"] = m.get("starts_by_outdoor")
    row["elec_by_outdoor"] = m.get("elec_by_outdoor")
    return row, res["paths"]


def run_many(controllers, scenarios, variants=("nominal",), forecast="noisy", params=None, seed=0,
             link_drops_per_day=0.0, jobs=None, csv_out=False, out_dir=None, write=True, seeds=None):
    """Run every controller x scenario x variant (x seed); returns a list of flat metric rows.
    `seeds` (list) overrides `seed`; rank multi-seed results with lab.sim.ranking.paired."""
    from lab.sim import scenarios as S

    names = []
    for s in scenarios:
        names.extend(S.expand(s))
    names = list(dict.fromkeys(names))
    seeds = list(seeds) if seeds else [seed]
    tasks = [dict(controller_spec=c, scenario=s, variant=v, forecast=forecast, params=params or {}, seed=sd,
                  link_drops_per_day=link_drops_per_day, write=write, csv_out=csv_out, out_dir=out_dir,
                  record=csv_out)
             for s in names for v in variants for sd in seeds for c in controllers]
    jobs = jobs or min(len(tasks), max(1, (os.cpu_count() or 2) - 1))
    t0 = time.time()
    if jobs <= 1 or len(tasks) == 1:
        results = [_job(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            results = list(ex.map(_job, tasks))
    rows = [r for r, _ in results]
    for r, (_, paths) in zip(rows, results):
        r["paths"] = paths
    return rows, time.time() - t0
