"""Run controllers on simulator scenarios and print a metrics table.

    .local/lab-venv/bin/python lab/run.py --controller unit_curve --scenario jan_cold
    .local/lab-venv/bin/python lab/run.py --controller fixed_setpoint --param setpoint=32 --scenario all
    .local/lab-venv/bin/python lab/run.py --compare --controller unit_curve,room_thermostat,"fixed_setpoint[setpoint=30]" --scenario all
    .local/lab-venv/bin/python lab/run.py --controller mypkg.mymod:MyController --scenario season --forecast noisy
    .local/lab-venv/bin/python lab/run.py --list
    .local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,my_ctrl -s weeks --seeds 0-4

A controller is a name in lab/controllers/, 'pkg.module:Class' or 'path/file.py:Class', optionally
with parameters in brackets: 'fixed_setpoint[setpoint=28,restart_delta=6]'. --param applies to
every controller. Results (JSON metrics + per-minute CSV) go to .local/lab-results/runs/; compare
mode writes JSON only unless --csv is given, plus one summary table (txt + json).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab.sim import harness  # noqa: E402
from lab.sim import metrics as M  # noqa: E402


def _split_list(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return [x.strip() for x in out if x.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--controller", "-c", default="unit_curve", help="controller spec(s), comma-separated")
    ap.add_argument("--scenario", "-s", default="all", help="scenario name, group (all, weeks, everything) or list")
    ap.add_argument("--param", "-p", action="append", default=[], help="k=v for every controller (repeatable)")
    ap.add_argument("--forecast", choices=("perfect", "noisy", "pessimistic"), default="noisy",
                    help="forecast seen by controllers (default noisy, the ranking setting)")
    ap.add_argument("--variant", default="nominal", help="plant variant(s), comma-separated; '+' combines")
    ap.add_argument("--seed", type=int, default=0, help="seed of the synthetic DHW/disturbance/forecast draws")
    ap.add_argument("--seeds", default=None, help="several seeds, e.g. 0-4 or 0,2,5 (paired ranking)")
    ap.add_argument("--rank", action="store_true",
                    help="paired ranking against the baseline (first controller) over the seeds; implies --compare")
    ap.add_argument("--robust", action="store_true", help="run every mandatory robustness variant (lab/sim/ranking.py)")
    ap.add_argument("--link-drops", default="measured",
                    help="Modbus link outages per day, or 'measured' (default: the heating-season rate and "
                         "durations of the record, about 0.34 a day, median 32 min); 0 switches them off")
    ap.add_argument("--compare", action="store_true", help="one table for all controllers x scenarios x variants")
    ap.add_argument("--csv", action="store_true", help="also write per-minute CSVs in compare mode")
    ap.add_argument("--no-csv", action="store_true", help="skip the per-minute CSV")
    ap.add_argument("--jobs", "-j", type=int, default=None, help="parallel processes (default: CPUs - 1)")
    ap.add_argument("--out", default=None, help="output directory (default .local/lab-results/runs)")
    ap.add_argument("--list", action="store_true", help="list scenarios, controllers and variants")
    a = ap.parse_args(argv)

    if a.list:
        from lab.sim import scenarios as S
        from lab.sim.simulator import variant_names
        print("scenarios:")
        for s in S.SCENARIOS.values():
            print(f"  {s.name:16s} {s.start[:10]} .. {s.end[:10]}  {s.kind:8s} {s.description}")
        print("groups:", ", ".join(f"{k} = {'+'.join(v)}" for k, v in S.GROUPS.items()))
        ctrls = sorted(p.stem for p in (ROOT / "lab" / "controllers").glob("*.py") if p.stem != "__init__")
        print("controllers:", ", ".join(ctrls))
        print("variants:", ", ".join(variant_names()))
        return 0

    controllers = _split_list(a.controller)
    scenarios = _split_list(a.scenario)
    variants = _split_list(a.variant)
    if a.robust:
        from lab.sim.ranking import ROBUSTNESS_VARIANTS
        variants = list(dict.fromkeys(variants + list(ROBUSTNESS_VARIANTS)))
    seeds = None
    if a.seeds:
        seeds = []
        for part in a.seeds.split(","):
            if "-" in part:
                lo, hi = part.split("-")
                seeds.extend(range(int(lo), int(hi) + 1))
            else:
                seeds.append(int(part))
    if a.rank:
        a.compare = True
    params = harness.parse_params(a.param)
    if str(a.link_drops).lower() == "measured":
        from lab.sim.exogenous import link_outage_model
        a.link_drops = link_outage_model()[0]
    else:
        a.link_drops = float(a.link_drops)
    csv_out = (a.csv or not a.compare) and not a.no_csv
    rows, wall = harness.run_many(controllers, scenarios, variants=variants, forecast=a.forecast, params=params,
                                  seed=a.seed, link_drops_per_day=a.link_drops, jobs=a.jobs, csv_out=csv_out,
                                  out_dir=a.out, seeds=seeds)
    label_cols = ["scenario", "controller"] + (["variant"] if len(variants) > 1 else []) + (["seed"] if seeds else [])
    txt = M.table(rows, label_cols=label_cols)
    print(txt)
    print(f"\n{len(rows)} run(s) in {wall:.1f} s wall ({sum(r['wall_s'] for r in rows):.1f} s simulated time)")
    if not a.compare:
        for r in rows:
            if r.get("starts_by_outdoor"):
                print(f"{r['scenario']} / {r['controller']}: starts/day by daily outdoor mean: "
                      + "; ".join(f"{k}: {v['starts_per_day']} ({v['days']} d)" for k, v in r["starts_by_outdoor"].items()))
        for r in rows:
            for k, v in r.get("paths", {}).items():
                print(f"  {k}: {v}")
    else:
        out = Path(a.out or harness.OUT_DIR)
        out.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        if a.rank:
            from lab.sim import ranking as RK
            from lab.sim.harness import short_label
            prs = RK.paired(rows, short_label(controllers[0]))
            ptxt = RK.paired_table(prs)
            print("\npaired against", short_label(controllers[0]), "(adjusted energy = normalised electricity + "
                  f"{RK.COMFORT_KWH_PER_KH} kWh per K-h of |air - target| + c kWh per start, c = "
                  f"{RK.START_COST_BAND[0]} / {RK.START_COST_KWH} / {RK.START_COST_BAND[1]}; % of the baseline's "
                  "window electricity, 90 % interval over seeds):")
            print(ptxt)
            vtxt = RK.verdict_summary(prs)
            print("\nverdicts (better = 90 % interval below zero at both ends of the start-cost band):")
            print(vtxt)
            txt += "\n\n" + ptxt + "\n\n" + vtxt
            (out / f"rank_{stamp}.json").write_text(json.dumps(prs, indent=1))
        (out / f"compare_{stamp}.txt").write_text(txt + "\n")
        (out / f"compare_{stamp}.json").write_text(json.dumps(rows, indent=1, default=float))
        print(f"table: {out / f'compare_{stamp}.txt'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
