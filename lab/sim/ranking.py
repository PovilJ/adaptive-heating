"""Ranking rules for candidate controllers (review rounds 1 and 2).

A ranking is only accepted when it holds:
- on several random draws (seeds) of the synthetic hot water, disturbance, local weather,
  forecast error and link outages, judged on paired differences against a common baseline with a
  90 % interval;
- on the mandatory robustness variants (ROBUSTNESS_VARIANTS);
- for every start cost from START_COST_BAND[0] to START_COST_BAND[1] kWh (review round 2, N4);
- with the noisy forecast and the measured link outages (the CLI defaults).

What is compared (review round 2, N2 and N4: energy, comfort and wear are kept apart):

- `energy`: `elec_norm_kwh` (metrics.py): metered electricity of the window plus a common 3-day
  run-out, normalised to the target mean air;
- `comfort`: `comfort_kh`, the K-hours of |air - target| over the window. It enters the ranking
  energy at COMFORT_KWH_PER_KH (the price of comfort, see below), so a candidate that saves
  energy only by holding the room less tightly gains nothing;
- `starts`: compressor starts, reported per day and priced only inside the start-cost band.

    adjusted_kwh(c) = elec_norm_kwh + COMFORT_KWH_PER_KH x comfort_kh + c x starts

The ranking difference is adjusted_kwh(candidate) - adjusted_kwh(baseline) in % of the
baseline's window electricity, at c = 0.05, START_COST_KWH (0.2, the summary) and 0.3. A
candidate is better only if the 90 % interval is below zero at both ends of the band; the
break-even start cost (where the sign flips) is reported for every pair.

COMFORT_KWH_PER_KH is the energy the baseline itself saves per K-hour of comfort it gives up when
it shifts its aim (warmer by day, cooler by night, the cheapest comfort-for-energy trade found:
validate_sim `comfort`). Charging every candidate that price puts each one on the baseline's own
energy/comfort trade-off line: a pure comfort trade scores about zero, an energy saving at equal
comfort scores in full. `paired` also reports energy and comfort separately (a Pareto pair).

Constraints (a run that breaks one is marked, not ranked):
- |mean air - target| <= COMFORT_MEAN_TOL_K (0.05 K; the baseline is tuned to within 0.05 K);
- mean |air - target| <= baseline's + MAE_OVER_BASE_K (0.05 K);
- starts/day <= 8 and writes/day <= 48 (metrics.FLAG_*).

Flags (from metrics.assumption_flags) mark results that rest on ASSUMED firmware behaviour;
`setpoint_range` is kept only when the candidate spends more time outside the recorded 25-39 degC
than the baseline. A season result whose advantage comes mostly from days below -4 degC is marked
`cold_share`: that regime has the least closed-loop validation (SIMULATOR.md section 6).

The season (storage < 1 % of the energy) is the primary ranking; the weeks are diagnostic.
"""
from __future__ import annotations

import json
import math

from lab.data.common import RESULTS

START_COST_KWH = 0.2  # summary value inside the band (ASSUMED energy-plus-wear equivalent)
START_COST_BAND = (0.05, 0.3)  # a ranking must hold over this whole range (review round 2, N4)
# review round 2 (N2): kWh per K-hour of |air - target|. validate_sim `comfort`, season, 6 seeds:
# the baseline aimed 0.2 / 0.4 / 0.6 K warmer by day and cooler by night (each tuned to the target
# mean air) saved 0 / 0.3 / 1.3 % of the energy for +0 / +0.6 / +4.4 % comfort K-hours; least
# squares through zero over the 11 seed pairs gives 0.54 kWh per K-h (single pairs 0.07-1.9)
COMFORT_KWH_PER_KH = 0.54
COMFORT_MEAN_TOL_K = 0.05
MAE_OVER_BASE_K = 0.05
MAE_LIMIT_K = None  # review round 1 used max(0.6, baseline + 0.15); now baseline + MAE_OVER_BASE_K
# mandatory variants. Review round 2: flat_load (rejected by the data) replaced by the part-load
# bounds; frost removal bounds, slab mass, sun and the pessimistic forecast added (N1, N3, N7)
ROBUSTNESS_VARIANTS = ("nominal", "partload_lo", "partload_hi", "legacy_cop", "high_start_loss", "sluggish",
                       "raw_return", "minute_only", "low_flow", "high_flow", "loss_minus20", "steep_outlet",
                       "shallow_outlet", "frost_melt_lo", "frost_melt_hi", "light_slab", "heavy_slab", "sun_plus30",
                       "sun_minus30", "forecast_pessimistic")
DIAGNOSTIC_VARIANTS = ("flat_load", "frost_no_melt", "legacy_frost_r1", "long_outage")
TUNE_CACHE = RESULTS / "sim" / "cache" / "tuned_reference.json"
TUNE_VERSION = "r2.1"  # plant version in the tuning-cache key: bump when the unit or house model changes

# two-sided 90 % Student t quantiles by degrees of freedom
_T90 = {1: 6.314, 2: 2.920, 3: 2.353, 4: 2.132, 5: 2.015, 6: 1.943, 7: 1.895, 8: 1.860, 9: 1.833, 10: 1.812,
        15: 1.753, 20: 1.725, 30: 1.697}


def t90(df):
    if df <= 0:
        return float("nan")
    keys = sorted(_T90)
    for k in keys:
        if df <= k:
            return _T90[k]
    return 1.645


def adjusted(m: dict, start_cost: float = START_COST_KWH, comfort_price: float | None = None) -> float:
    """Ranking energy: normalised electricity + comfort at its price + starts at `start_cost`."""
    lam = COMFORT_KWH_PER_KH if comfort_price is None else comfort_price
    return float(m["elec_norm_kwh"]) + lam * float(m.get("comfort_kh") or 0.0) + start_cost * float(m["starts"])


def score(m: dict) -> float:
    return adjusted(m)


def violations(m: dict, target: float = 22.0, base: dict | None = None) -> list:
    """Mean air off target by more than 0.05 K, mean |error| more than 0.05 K above the
    baseline's, > 8 starts or > 48 writes a day."""
    out = []
    if abs(float(m["mean_air"]) - target) > COMFORT_MEAN_TOL_K + 1e-9:
        out.append(f"mean_air {m['mean_air']:.2f}")
    if base is not None and float(m.get("mae_air") or 0) > float(base.get("mae_air") or 0) + MAE_OVER_BASE_K + 1e-9:
        out.append(f"mae {m['mae_air']:.2f}")
    flags = (m.get("assumption_flags") or "").split(",")
    for f in ("starts_gt_8", "writes_gt_48"):
        if f in flags:
            out.append(f)
    return out


def _stats(d):
    n = len(d)
    mean = sum(d) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in d) / (n - 1)) if n > 1 else float("nan")
    half = t90(n - 1) * sd / math.sqrt(n) if n > 1 else float("nan")
    return mean, half


def paired(rows, baseline: str, comfort_price: float | None = None):
    """Paired differences of every controller against `baseline` per (scenario, variant) over the
    seeds present in both. rows: flat metric rows from harness.run_many (with 'seed')."""
    lam = COMFORT_KWH_PER_KH if comfort_price is None else comfort_price
    by = {}
    for r in rows:
        by.setdefault((r["scenario"], r["variant"], r["controller"]), {})[r.get("seed", 0)] = r
    out = []
    keys = sorted({(s, v) for s, v, _ in by})
    ctrls = sorted({c for _, _, c in by if c != baseline})
    for s, v in keys:
        base = by.get((s, v, baseline))
        if not base:
            continue
        for c in ctrls:
            cand = by.get((s, v, c))
            if not cand:
                continue
            seeds = sorted(set(base) & set(cand))
            n = len(seeds)

            def pct(fn):
                return [100.0 * (fn(cand[k]) - fn(base[k])) / base[k]["elec_kwh"] for k in seeds]

            # score at the band ends and the summary start cost (comfort priced in)
            band = {}
            for sc in (START_COST_BAND[0], START_COST_KWH, START_COST_BAND[1]):
                band[sc] = _stats(pct(lambda m, sc=sc: adjusted(m, sc, lam)))
            mean, half = band[START_COST_KWH]
            # break-even start cost: where the comfort-adjusted energy difference and the start
            # difference cancel
            dE = sum(adjusted(cand[k], 0.0, lam) - adjusted(base[k], 0.0, lam) for k in seeds) / n
            dS = sum(float(cand[k]["starts"]) - float(base[k]["starts"]) for k in seeds) / n
            breakeven = (-dE / dS) if abs(dS) > 1e-9 else None
            lo_m, lo_h = band[START_COST_BAND[0]]
            hi_m, hi_h = band[START_COST_BAND[1]]
            better = n > 1 and lo_m + lo_h < 0 and hi_m + hi_h < 0
            worse = n > 1 and lo_m - lo_h > 0 and hi_m - hi_h > 0
            de = [100.0 * (cand[k]["elec_kwh"] / base[k]["elec_kwh"] - 1.0) for k in seeds]
            dn = pct(lambda m: float(m["elec_norm_kwh"]))
            dc = [float(cand[k].get("comfort_kh") or 0) - float(base[k].get("comfort_kh") or 0) for k in seeds]
            viol = sorted({x for k in seeds for x in violations(cand[k], base=base[k])})
            flags = set()
            for k in seeds:
                fl = {f for f in (cand[k].get("assumption_flags") or "").split(",") if f}
                if "setpoint_range" in fl and float(cand[k].get("setpoint_out_of_range_pct") or 0) <= \
                        float(base[k].get("setpoint_out_of_range_pct") or 0) + 0.5:
                    fl.discard("setpoint_range")  # the baseline goes there as much (review round 2, N8)
                flags |= fl
            flags = sorted(flags)
            # cold share of the advantage (season-length runs)
            cold = None
            tot = 0.0
            eb_c, eb_b = cand[seeds[0]].get("elec_by_outdoor"), base[seeds[0]].get("elec_by_outdoor")
            if eb_c and eb_b and "<-4" in eb_c and "<-4" in eb_b:
                tot = sum(cand[k]["elec_kwh"] - base[k]["elec_kwh"] for k in seeds)
                cd = sum(cand[k]["elec_by_outdoor"]["<-4"]["elec_kwh"] - base[k]["elec_by_outdoor"]["<-4"]["elec_kwh"]
                         for k in seeds)
                if abs(tot) > 1e-9:
                    cold = cd / tot
            if cold is not None and tot < 0 and cold > 0.5:
                flags.append("cold_share")
            nn, nh = _stats(dn)
            out.append(dict(scenario=s, variant=v, controller=c, baseline=baseline, seeds=n,
                            score_diff_pct=round(mean, 2), ci90_pct=round(half, 2) if half == half else None,
                            score_lo_cost_pct=round(lo_m, 2), score_hi_cost_pct=round(hi_m, 2),
                            ci90_lo_cost_pct=round(lo_h, 2) if lo_h == lo_h else None,
                            ci90_hi_cost_pct=round(hi_h, 2) if hi_h == hi_h else None,
                            breakeven_start_kwh=None if breakeven is None else round(breakeven, 3),
                            verdict="better" if better else "worse" if worse else "undecided",
                            elec_diff_pct=round(sum(de) / n, 2), norm_diff_pct=round(nn, 2),
                            norm_ci90_pct=round(nh, 2) if nh == nh else None,
                            comfort_kh_diff=round(sum(dc) / n, 1),
                            comfort_cost_pct=round(sum(100.0 * lam * x / base[k]["elec_kwh"] for x, k in zip(dc, seeds)) / n, 2),
                            starts_per_day=round(sum(cand[k]["starts_per_day"] for k in seeds) / n, 2),
                            base_starts_per_day=round(sum(base[k]["starts_per_day"] for k in seeds) / n, 2),
                            significant=bool(better or worse), violations=viol, flags=flags,
                            cold_share_of_diff=None if cold is None else round(cold, 2),
                            mean_air=round(sum(cand[k]["mean_air"] for k in seeds) / n, 3),
                            base_mean_air=round(sum(base[k]["mean_air"] for k in seeds) / n, 3),
                            mae_air=round(sum(cand[k]["mae_air"] for k in seeds) / n, 3),
                            base_mae_air=round(sum(base[k]["mae_air"] for k in seeds) / n, 3)))
    return out


def paired_table(prs) -> str:
    head = ("scenario", "variant", "controller", "n", "adj % c=0.2", "+-90%", "c=0.05", "c=0.3", "break-even c",
            "verdict", "energy %", "comfort Kh", "metered %", "starts/d", "base st/d", "air", "mae", "base mae",
            "flags / violations")
    lines = []
    for p in prs:
        lines.append((p["scenario"], p["variant"], p["controller"], str(p["seeds"]), f"{p['score_diff_pct']:+.2f}",
                      "-" if p["ci90_pct"] is None else f"{p['ci90_pct']:.2f}", f"{p['score_lo_cost_pct']:+.2f}",
                      f"{p['score_hi_cost_pct']:+.2f}",
                      "-" if p["breakeven_start_kwh"] is None else f"{p['breakeven_start_kwh']:.2f}", p["verdict"],
                      f"{p['norm_diff_pct']:+.2f}", f"{p['comfort_kh_diff']:+.0f}", f"{p['elec_diff_pct']:+.2f}",
                      f"{p['starts_per_day']:.1f}", f"{p['base_starts_per_day']:.1f}", f"{p['mean_air']:.2f}",
                      f"{p['mae_air']:.2f}", f"{p['base_mae_air']:.2f}",
                      ",".join(p["flags"] + [f"!{x}" for x in p["violations"]])))
    w = [max(len(h), *(len(l[i]) for l in lines)) if lines else len(h) for i, h in enumerate(head)]
    out = ["  ".join(h.ljust(w[i]) for i, h in enumerate(head)), "  ".join("-" * x for x in w)]
    out += ["  ".join(c.ljust(w[i]) for i, c in enumerate(l)) for l in lines]
    return "\n".join(out)


def verdict_summary(prs) -> str:
    """One line per (scenario, controller): the verdict across all variants present."""
    by = {}
    for p in prs:
        by.setdefault((p["scenario"], p["controller"]), []).append(p)
    lines = []
    for (s, c), ps in sorted(by.items()):
        vs = {p["verdict"] for p in ps}
        viol = sorted({x for p in ps for x in p["violations"]})
        overall = ("better on every variant" if vs == {"better"} else "worse on every variant" if vs == {"worse"}
                   else "not decided: " + ", ".join(f"{p['variant']}={p['verdict']}" for p in ps if p["verdict"] != "better"))
        lines.append(f"{s} / {c}: {overall}" + (f"; constraint breaks: {', '.join(viol)}" if viol else ""))
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------
# tuned baseline (m4)
# ------------------------------------------------------------------------------------------

def _load_cache():
    try:
        return json.loads(TUNE_CACHE.read_text())
    except (OSError, ValueError):
        return {}


def tuned_offset(scenario: str, variant: str = "nominal", seed: int = 0, forecast: str = "noisy",
                 tol: float = 0.03, max_iter: int = 8, link_drops_per_day: float = 0.0, params: dict | None = None) -> float:
    """Target offset for reference_tuned so that the mean true air of the measured window is
    within `tol` of the target (secant iteration, cached). `params` (other ref_* settings, e.g. a
    gain or a day/night shift) and the link outages are part of the cache key."""
    from lab.controllers.reference_tuned import ReferenceTuned
    from lab.sim import scenarios as S
    from lab.sim import simulator as SIM
    extra = dict(params or {})
    extra.pop("ref_target_offset", None)
    pk = ",".join(f"{k}={extra[k]}" for k in sorted(extra))
    key = f"{TUNE_VERSION}|{scenario}|{variant}|{seed}|{forecast}|{round(float(link_drops_per_day), 3)}|{pk}"
    cache = _load_cache()
    if key in cache:
        return float(cache[key])
    exo = S.build(scenario, variant, seed, link_drops_per_day)

    def err(off):
        r = SIM.run(ReferenceTuned(), exo, variant=variant, forecast=forecast, params=dict(extra, ref_target_offset=off),
                    record=False)
        return r["metrics"]["mean_air"] - exo.target

    x0, e0 = 0.0, err(0.0)
    if abs(e0) <= tol:
        best = x0
    else:
        x1 = -e0
        e1 = err(x1)
        best = x1 if abs(e1) < abs(e0) else x0
        for _ in range(max_iter):
            if abs(e1) <= tol or e1 == e0:
                break
            x2 = x1 - e1 * (x1 - x0) / (e1 - e0)
            x2 = max(min(x2, 2.0), -2.0)
            x0, e0, x1, e1 = x1, e1, x2, err(x2)
            best = x1
    _cache_put(key, round(float(best), 3))
    return float(best)


def _cache_put(key, value):
    """Read-modify-write of the tuning cache under an exclusive lock with an atomic rename
    (review round 2, N7: parallel workers used to overwrite each other's entries)."""
    import os
    from lab.sim.exogenous import cache_lock
    TUNE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with cache_lock(TUNE_CACHE):
        cache = _load_cache()
        cache[key] = value
        tmp = TUNE_CACHE.with_name(TUNE_CACHE.name + f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(cache, indent=1))
        os.replace(tmp, TUNE_CACHE)
