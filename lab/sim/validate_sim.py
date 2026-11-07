"""Validation of the closed-loop simulator (numbers for docs/research/lab/SIMULATOR.md).

    .local/lab-venv/bin/python -m lab.sim.validate_sim [replay|season|sweeps|speed|normalisation|review|house|comfort|review2|all]

- replay: closed-loop replay of the recorded registers over the recorded windows, from the
  recorded house state, against what the real house and unit did.
- season: daily electricity vs outdoor temperature for the unit_curve and reference baselines
  over the 2025/26 season against the metered daily electricity in similar weather.
- sweeps: steady-weather sweeps of the constant setpoint, the restart hysteresis and quiet mode.
- speed: wall time of the 'season' scenario.
- normalisation (review round 1): does the storage- and comfort-normalised energy still depend on
  the mean room air? Reference aimed at target -0.5 / 0 / +0.5 K.
- review (review round 1): the probe controllers of lab/controllers/probes.py against the tuned
  reference, several seeds, nominal and the mandatory variants.

Private output (real dates): .local/lab-results/sim_validation/.
"""
from __future__ import annotations

import csv
import json
import sys
import time

import numpy as np

from lab.data.common import DATA, RESULTS, epoch
from lab.sim import exogenous as X
from lab.sim import house as H
from lab.sim import scenarios as S
from lab.sim import simulator as SIM

OUT = RESULTS / "sim_validation"


def _ctrl(name, **kw):
    from lab.sim.harness import load_controller
    c = load_controller(name)
    return c, kw


def _runs(mask):
    m = np.r_[False, np.asarray(mask, bool), False].astype(np.int8)
    d = np.diff(m)
    return np.flatnonzero(d == 1), np.flatnonzero(d == -1)


def _pct(a, q):
    return [round(float(x), 1) for x in np.percentile(a, q)] if len(a) else None


# ------------------------------------------------------------------------------------------
# (a) closed-loop replay
# ------------------------------------------------------------------------------------------

def _mark_share(runs):
    """Share of heat runs (>= 20 min) that end within +-6 min of 120 k + 4 minutes."""
    r = np.asarray(runs, float)
    r = r[r >= 20]
    if not len(r):
        return None
    return round(100.0 * float(np.mean([any(abs(x - (120 * k + 4)) <= 6 for k in range(1, 12)) for x in r])), 1)


def replay(name="recorded", variant="nominal", dist=None):
    exo = S.build(name, variant)
    if dist is not None:
        import dataclasses
        exo = dataclasses.replace(exo, dist=np.asarray(dist, float))
    ctrl, _ = _ctrl("replay_recorded")
    res = SIM.run(ctrl, exo, variant=variant)
    rec = res["rec"]
    i0, i1 = exo.context["recorded_window"]
    d = X.minute_data()
    sl = slice(i0, i1)
    st = d["unit_status"][sl]
    comp = np.nan_to_num(d["compressor"][sl])
    ok = np.nan_to_num(d["versati_ok"][sl]) == 1
    elec = d["elec_w"][sl].astype(float) / 1000.0
    e_ok = np.isfinite(elec)
    room = d["room"][sl].astype(float)
    outlet = d["outlet"][sl].astype(float)
    heat_status = (st == "HEAT")
    rec_heat = (comp == 1) & heat_status
    edge = (comp == 1) & (np.r_[0, comp[:-1]] == 0) & heat_status
    from lab.sim import house_prep
    prep = house_prep.load()
    q_rec = np.nan_to_num(prep["q_loop"][sl])
    t = exo.grid
    day = X.local_day_index(t)
    rows = []
    sim_heat = (rec["comp"] > 0.5) & ((rec["mode"] == 2) | (rec["mode"] == 3))
    sim_run_heat = (rec["comp"] > 0.5) & (rec["mode"] == 2)
    for u in np.unique(day):
        w = day == u
        if w.sum() < 1380:
            continue
        good = ok[w].mean() >= 0.97 and e_ok[w].mean() >= 0.97
        rr = np.isfinite(room[w])
        rows.append(dict(
            day=int(u), good=bool(good), t_out=float(np.mean(exo.t_out[w])),
            starts_rec=int(edge[w].sum()), starts_sim=int(rec["started"][w].sum()),
            elec_rec=float(np.nansum(elec[w]) / 60), elec_sim=float(rec["p_out"][w].sum() / 60),
            heat_rec=float(q_rec[w].sum() / 60), heat_sim=float(rec["q"][w].sum() / 60),
            heat_min_rec=int(rec_heat[w].sum()), heat_min_sim=int(sim_heat[w].sum()),
            room_rec=float(np.mean(room[w][rr])) if rr.any() else None,
            room_sim=float(np.mean(rec["room_s"][w][rr])) if rr.any() else None,
        ))
    good = [r for r in rows if r["good"]]
    gm = np.zeros(len(t), bool)
    gdays = {r["day"] for r in good}
    gm[np.isin(day, list(gdays))] = True
    # run lengths (heat runs, defrost inside counts as running)
    ra, rb = _runs(rec_heat & gm)
    rec_runs = (rb - ra)[(ra > 0) & (rb < len(t))]
    sa, sb = _runs(sim_heat & gm)
    sim_runs = (sb - sa)[(sa > 0) & (sb < len(t))]
    # outlet while running (recorded: HEAT & compressor & no defrost)
    dfr = np.nan_to_num(d["defrost"][sl]) > 0
    rr_out = rec_heat & ok & ~dfr & gm & np.isfinite(outlet)
    # room trajectory
    rv = np.isfinite(room)
    err_s = rec["room_s"][rv] - room[rv]
    recon = X.minute_data()  # noqa: F841 (kept for symmetry)
    n_days = len(good)

    def tot(k):
        return sum(r[k] for r in good)

    daily_e_err = [100 * (r["elec_sim"] / r["elec_rec"] - 1) for r in good if r["elec_rec"] > 2]
    daily_s_err = [r["starts_sim"] - r["starts_rec"] for r in good]
    summ = dict(
        scenario=name, variant=variant, days=len(rows), good_days=n_days,
        starts_per_day_rec=round(tot("starts_rec") / max(n_days, 1), 2),
        starts_per_day_sim=round(tot("starts_sim") / max(n_days, 1), 2),
        starts_ratio=round(tot("starts_sim") / max(tot("starts_rec"), 1), 3),
        daily_starts_mae=round(float(np.mean(np.abs(daily_s_err))), 2) if good else None,
        run_min_rec_p25_50_75=_pct(rec_runs, [25, 50, 75]), run_min_sim_p25_50_75=_pct(sim_runs, [25, 50, 75]),
        runs_under_60_pct_rec=round(100 * float(np.mean(rec_runs < 60)), 1) if len(rec_runs) else None,
        runs_under_60_pct_sim=round(100 * float(np.mean(sim_runs < 60)), 1) if len(sim_runs) else None,
        runs_end_at_120_mark_pct_rec=_mark_share(rec_runs), runs_end_at_120_mark_pct_sim=_mark_share(sim_runs),
        heat_min_ratio=round(tot("heat_min_sim") / max(tot("heat_min_rec"), 1), 3),
        elec_per_day_rec=round(tot("elec_rec") / max(n_days, 1), 2),
        elec_per_day_sim=round(tot("elec_sim") / max(n_days, 1), 2),
        elec_ratio=round(tot("elec_sim") / max(tot("elec_rec"), 1e-9), 3),
        daily_elec_err_mae_pct=round(float(np.mean(np.abs(daily_e_err))), 1) if daily_e_err else None,
        heat_per_day_rec=round(tot("heat_rec") / max(n_days, 1), 2),
        heat_per_day_sim=round(tot("heat_sim") / max(n_days, 1), 2),
        heat_ratio=round(tot("heat_sim") / max(tot("heat_rec"), 1e-9), 3),
        cop_rec=round(tot("heat_rec") / max(tot("elec_rec"), 1e-9), 2),
        cop_sim=round(tot("heat_sim") / max(tot("elec_sim"), 1e-9), 2),
        mean_outlet_running_rec=round(float(np.mean(outlet[rr_out])), 2) if rr_out.any() else None,
        mean_outlet_running_sim=round(float(np.mean(rec["outlet_s"][sim_run_heat & gm])), 2),
        room_rms_k=round(float(np.sqrt(np.mean(err_s ** 2))), 3),
        room_bias_k=round(float(np.mean(err_s)), 3),
        room_err_p95_abs_k=round(float(np.percentile(np.abs(err_s), 95)), 2),
        room_max_abs_k=round(float(np.max(np.abs(err_s))), 2),
        room_rec_mean=round(float(np.mean(room[rv])), 2), room_sim_mean=round(float(np.mean(rec["room_s"][rv])), 2),
        defrosts_rec=int(len(_runs(dfr & gm)[0])), defrosts_sim=int(len(_runs((rec["mode"] == 3) & gm)[0])),
        dhw_runs_rec=int(len(_runs((st == "HOT WATER") & (comp == 1))[0])),
        dhw_runs_sim=int(len(_runs((rec["mode"] == 4) & (rec["comp"] > 0.5))[0])),
        writes_sim=int(rec["writes"].sum()),
        wall_s=res["meta"]["wall_s"],
    )
    # by daily-mean outdoor bucket (review round 1, M3)
    buckets = {}
    for lo, hi in ((-30, 0), (0, 4), (4, 12), (12, 30)):
        bd = [r for r in good if lo <= r["t_out"] < hi]
        if not bd:
            continue
        dsel = np.isin(day, [r["day"] for r in bd])
        rv_b = rv & dsel
        e_b = rec["room_s"][rv_b] - room[rv_b]
        oo = rr_out & dsel
        so = sim_run_heat & dsel
        buckets[f"{lo:+d}..{hi:+d}"] = dict(
            days=len(bd), starts_rec=sum(r["starts_rec"] for r in bd), starts_sim=sum(r["starts_sim"] for r in bd),
            elec_rec=round(sum(r["elec_rec"] for r in bd), 1), elec_sim=round(sum(r["elec_sim"] for r in bd), 1),
            elec_ratio=round(sum(r["elec_sim"] for r in bd) / max(sum(r["elec_rec"] for r in bd), 1e-9), 3),
            heat_ratio=round(sum(r["heat_sim"] for r in bd) / max(sum(r["heat_rec"] for r in bd), 1e-9), 3),
            outlet_rec=round(float(np.mean(outlet[oo])), 2) if oo.any() else None,
            outlet_sim=round(float(np.mean(rec["outlet_s"][so])), 2) if so.any() else None,
            room_bias=round(float(np.mean(e_b)), 3) if len(e_b) else None,
            room_rms=round(float(np.sqrt(np.mean(e_b ** 2))), 3) if len(e_b) else None)
    summ["by_outdoor"] = buckets
    # room error growth with time since start (drift check)
    k = np.flatnonzero(rv)
    for hrs in (24, 72, 168, 336):
        sel = k < hrs * 60
        if sel.any():
            summ[f"room_rms_first_{hrs}h"] = round(float(np.sqrt(np.mean(err_s[sel] ** 2))), 3)
    return summ, rows


def cmd_replay():
    out = {}
    for name in ("recorded", "recorded_c2", "recorded_spring", "recorded_a0"):
        extra = ()
        if name == "recorded":
            extra = ("raw_return", "anchor_heat", "minute_only", "low_flow", "high_flow", "sluggish", "flat_load",
                     "partload_lo", "partload_hi", "legacy_cop", "frost_melt_lo", "frost_melt_hi", "frost_no_melt",
                     "legacy_frost_r1", "surge_from_start")
        elif name in ("recorded_spring", "recorded_a0"):
            extra = ("raw_return", "frost_melt_lo", "frost_melt_hi", "frost_no_melt", "legacy_frost_r1",
                     "surge_from_start")
        for variant in ("nominal",) + extra:
            s, rows = replay(name, variant)
            out[f"{name}/{variant}"] = dict(summary=s, days=rows)
            print(f"\n== replay {name} variant={variant}")
            for kk, v in s.items():
                print(f"  {kk}: {v}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "replay.json").write_text(json.dumps(out, indent=1))
    return out


# ------------------------------------------------------------------------------------------
# (b) season sanity
# ------------------------------------------------------------------------------------------

def actual_daily(t0="2025-10-15T00:00Z", t1="2026-05-06T00:00Z"):
    """Metered outdoor-unit electricity per local day from hourly.csv (days with 24 valid hours)."""
    rows = list(csv.DictReader(open(DATA / "hourly.csv")))
    T = np.array([epoch(r["time_utc"]) for r in rows])
    e = np.array([float(r["elec_out_kwh"]) if r["elec_out_kwh"] else np.nan for r in rows])
    flag = np.array([int(float(r["elec_flag"])) if r["elec_flag"] else 9 for r in rows])
    tt = np.array([float(r["wx_t"]) if r["wx_t"] else np.nan for r in rows])
    room = np.array([float(r["room_mean"]) if r["room_mean"] else np.nan for r in rows])
    m = (T >= epoch(t0)) & (T < epoch(t1))
    T, e, flag, tt, room = T[m], e[m], flag[m], tt[m], room[m]
    day = X.local_day_index(T)
    out = []
    for u in np.unique(day):
        w = day == u
        if w.sum() != 24 or (flag[w] != 0).any() or np.isnan(e[w]).any():
            continue
        out.append(dict(day=int(u), elec=float(e[w].sum()), t_out=float(np.nanmean(tt[w])),
                        room=float(np.nanmean(room[w])) if np.isfinite(room[w]).any() else None))
    return out


def _bins(days, key_t="t_out", key_e="elec", edges=(-20, -12, -8, -4, 0, 4, 8, 12, 16)):
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        v = [d[key_e] for d in days if lo <= d[key_t] < hi]
        if v:
            out.append(dict(bin=f"{lo:+d}..{hi:+d}", n=len(v), median=round(float(np.median(v)), 1),
                            p25=round(float(np.percentile(v, 25)), 1), p75=round(float(np.percentile(v, 75)), 1)))
    return out


def cmd_season():
    act = actual_daily()
    res = {"actual": dict(n_days=len(act), bins=_bins(act))}
    for ctrl_name, seed in (("unit_curve", 0), ("reference", 0), ("reference", 1)):
        c, _ = _ctrl(ctrl_name)
        t0 = time.perf_counter()
        r = SIM.run(c, S.build("season", seed=seed), forecast="noisy")
        ctrl_name = f"{ctrl_name}" + (f"_seed{seed}" if seed else "")
        wall = time.perf_counter() - t0
        m = r["metrics"]
        sim_days = [dict(t_out=dd["t_out"], elec=dd["elec_kwh"]) for dd in m["per_day"] if dd["minutes"] >= 1380]
        res[ctrl_name] = dict(wall_s=round(wall, 1), bins=_bins(sim_days),
                              totals={k: m[k] for k in ("elec_kwh", "elec_heat_kwh", "elec_dhw_kwh", "heat_kwh",
                                                       "cop_space", "starts_per_day", "run_min_median",
                                                       "mean_outlet_running", "mean_air", "rms_air", "min_air",
                                                       "max_air", "dh_below_air", "dh_above_air", "defrosts",
                                                       "dhw_runs", "starts_by_outdoor", "elec_norm_kwh",
                                                       "storage_delta_kwh", "mae_air", "elec_by_outdoor",
                                                       "assumption_flags", "room_report_p50_min",
                                                       "room_report_p90_min")})
        # room by outdoor bin (comfort of the baseline)
        rec = r["rec"]
        day = X.local_day_index(rec["t"].astype(float))
        rb = []
        for u in np.unique(day):
            w = day == u
            if w.sum() >= 1380:
                rb.append(dict(t_out=float(rec["t_out"][w].mean()), elec=float(rec["t_air"][w].mean())))
        res[ctrl_name]["room_bins"] = _bins(rb)
    print(json.dumps(res, indent=1))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "season.json").write_text(json.dumps(res, indent=1))
    return res


# ------------------------------------------------------------------------------------------
# (c) steady-weather sweeps
# ------------------------------------------------------------------------------------------

def steady_run(controller, params, t_out, rh=85.0, variant="nominal", days=10, measure_days=7):
    """Two passes: pass 1 from a quasi-steady 22 degC state finds the mean loop heat; pass 2 starts
    from the house's steady state at that heat and is measured over its last `measure_days`."""
    up, hp = SIM.plant(variant)
    c, _ = _ctrl(controller)
    r1 = SIM.run(c, S.steady(t_out, days=days, rh=rh), variant=variant, params=params, plant_params=(up, hp))
    q_mean = float(np.mean(r1["rec"]["q"][-4 * 1440:]))
    x0, _ = H.steady_state(hp, q_mean, t_out)
    exo = S.steady(t_out, days=measure_days, rh=rh, x0=x0, warmup_days=days - measure_days)
    c, _ = _ctrl(controller)
    r2 = SIM.run(c, exo, variant=variant, params=params, plant_params=(up, hp))
    m = r2["metrics"]
    rec = r2["rec"]
    air = rec["t_air"].astype(float)
    return dict(t_out=t_out, elec_per_day=m["elec_kwh_per_day"], heat_per_day=m["heat_kwh_per_day"],
                cop=m["cop_space"], starts_per_day=m["starts_per_day"], run_min_median=m["run_min_median"],
                runs_under_60_pct=m["runs_under_60_pct"], mean_outlet_running=m["mean_outlet_running"],
                mean_supply_running=m["mean_supply_running"], room=m["mean_air"],
                room_swing_p5_p95=round(float(np.percentile(air, 95) - np.percentile(air, 5)), 2),
                defrosts_per_day=round(m["defrosts"] / m["days"], 2),
                kwh_el_per_kwh_heat=round(m["elec_heat_kwh"] / m["heat_kwh"], 4) if m["heat_kwh"] > 0 else None)


def cmd_sweeps(quick=False):
    temps = (-10.0, 0.0, 7.0, 12.0)
    sps = range(26, 41, 1 if not quick else 2)
    out = {"setpoint": {}, "restart_delta": {}, "quiet": {}}
    for t in temps:
        rows = []
        for sp in sps:
            r = steady_run("fixed_setpoint", dict(setpoint=float(sp)), t)
            r["setpoint"] = sp
            rows.append(r)
            print(f"t_out {t:+.0f} sp {sp}: el {r['elec_per_day']:.2f} heat {r['heat_per_day']:.1f} COP {r['cop']} "
                  f"starts {r['starts_per_day']} run p50 {r['run_min_median']} room {r['room']} swing {r['room_swing_p5_p95']}")
        out["setpoint"][f"{t:+.0f}"] = rows
    # restart hysteresis at a setpoint that holds roughly 22 degC
    for t, sp in ((0.0, 31.0), (7.0, 29.0), (12.0, 27.0)):
        rows = []
        for dl in range(2, 9):
            r = steady_run("fixed_setpoint", dict(setpoint=sp, restart_delta=float(dl)), t)
            r["restart_delta"] = dl
            rows.append(r)
            print(f"t_out {t:+.0f} sp {sp} delta {dl}: el {r['elec_per_day']:.2f} heat {r['heat_per_day']:.1f} COP "
                  f"{r['cop']} starts {r['starts_per_day']} run p50 {r['run_min_median']} room {r['room']} "
                  f"swing {r['room_swing_p5_p95']}")
        out["restart_delta"][f"{t:+.0f}"] = dict(setpoint=sp, rows=rows)
    for t, sp in ((-10.0, 36.0), (0.0, 31.0), (7.0, 29.0)):
        rows = []
        for q in (False, True):
            r = steady_run("fixed_setpoint", dict(setpoint=sp, quiet=q), t)
            r["quiet"] = q
            rows.append(r)
            print(f"t_out {t:+.0f} sp {sp} quiet {q}: el {r['elec_per_day']:.2f} heat {r['heat_per_day']:.1f} "
                  f"COP {r['cop']} starts {r['starts_per_day']} defrost/d {r['defrosts_per_day']} room {r['room']}")
        out["quiet"][f"{t:+.0f}"] = dict(setpoint=sp, rows=rows)
    # slope: % electricity per kWh heat per K of setpoint (continuous-running cases)
    slopes = {}
    for t, rows in out["setpoint"].items():
        x = np.array([r["setpoint"] for r in rows], float)
        y = np.array([r["kwh_el_per_kwh_heat"] or np.nan for r in rows], float)
        ok = np.isfinite(y)
        if ok.sum() > 3:
            b = np.polyfit(x[ok], np.log(y[ok]), 1)[0]
            slopes[t] = round(100 * (np.exp(b) - 1), 2)
    out["el_per_heat_pct_per_K"] = slopes
    # same heat: ln(el) = a + b ln(heat) + c setpoint over the rows with a 19-26 degC room
    same = {}
    for t, rows in out["setpoint"].items():
        rr = [r for r in rows if 19.0 <= r["room"] <= 26.0]
        if len(rr) >= 4:
            sp = np.array([r["setpoint"] for r in rr], float)
            A = np.c_[np.ones(len(rr)), np.log([r["heat_per_day"] for r in rr]), sp]
            c = np.linalg.lstsq(A, np.log([r["elec_per_day"] for r in rr]), rcond=None)[0]
            same[t] = round(100 * (np.exp(c[2]) - 1), 2)
    out["el_pct_per_K_same_heat"] = same
    print("electricity % per K of setpoint at the same heat (regression):", same)
    print("electricity per heat, % per K of setpoint:", slopes)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sweeps.json").write_text(json.dumps(out, indent=1))
    return out


# ------------------------------------------------------------------------------------------
# (e) normalisation check and (f) review probes (review round 1)
# ------------------------------------------------------------------------------------------

def _one(args):
    ctrl_name, cls, params, scen, variant, seed = args[:6]
    base_name = args[6] if len(args) > 6 else ctrl_name
    import importlib
    from lab.sim.exogenous import link_outage_model
    if cls:
        mod = importlib.import_module("lab.controllers.probes")
        c = getattr(mod, cls)()
    else:
        c, _ = _ctrl(base_name)
    drops = link_outage_model()[0]  # review round 2 (N10): measured heating-season outages
    exo = S.build(scen, variant, seed, drops)
    p = dict(params)
    if "total_min" in p and p["total_min"] is None:
        p["total_min"] = len(exo.grid) - exo.n_warm - int(exo.n_tail or 0)
    if base_name == "reference_tuned" and "ref_target_offset" not in p:
        from lab.sim.ranking import tuned_offset
        p["ref_target_offset"] = tuned_offset(scen, variant, seed, "noisy", link_drops_per_day=drops,
                                              params={k: v for k, v in p.items() if k.startswith("ref_")})
    r = SIM.run(c, exo, variant=variant, forecast="noisy", params=p, record=False)
    m = r["metrics"]
    keep = ("elec_kwh", "elec_corr_kwh", "elec_norm_kwh", "storage_delta_kwh", "heat_kwh", "cop_space", "starts",
            "starts_per_day", "run_min_median", "runs_under_15_pct", "mean_air", "mae_air", "rms_air", "dh_below_air",
            "mean_supply_running", "defrosts", "defrost_heat_drawn_kwh", "writes_per_day", "assumption_flags",
            "comfort_kh", "setpoint_out_of_range_pct", "elec_by_outdoor", "min_setpoint")
    return dict(controller=ctrl_name, scenario=scen, variant=variant, seed=seed, params=params,
                **{k: m.get(k) for k in keep})


def _pool(tasks):
    from concurrent.futures import ProcessPoolExecutor
    import os
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 2) - 1)) as ex:
        return list(ex.map(_one, tasks))


def cmd_normalisation():
    """Energy against mean air for the reference aimed at target-0.5 / 0 / +0.5 K (3 seeds)."""
    scen = ("oct_mild", "nov_mixed", "jan_cold", "mar_shoulder", "season")
    tasks = [("reference_tuned", None, dict(ref_target_offset=off), sc, "nominal", sd)
             for sc in scen for off in (-0.5, 0.0, 0.5) for sd in ((0, 1) if sc == "season" else (0, 1, 2))]
    rows = _pool(tasks)
    out = {}
    for sc in scen:
        rr = [r for r in rows if r["scenario"] == sc]
        x = np.array([r["mean_air"] for r in rr])
        res = {}
        for key in ("elec_kwh", "elec_corr_kwh", "elec_norm_kwh"):
            y = np.array([r[key] for r in rr])
            b = np.polyfit(x, y, 1)[0]
            # % of the window's metered electricity (elec_norm includes the common run-out)
            res[f"{key}_pct_per_K"] = round(100 * b / float(np.mean([r["elec_kwh"] for r in rr])), 2)
        res["storage_kwh_range"] = [round(min(r["storage_delta_kwh"] for r in rr), 1),
                                    round(max(r["storage_delta_kwh"] for r in rr), 1)]
        res["mean_air_range"] = [round(float(x.min()), 2), round(float(x.max()), 2)]
        out[sc] = res
        print(sc, res)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "normalisation.json").write_text(json.dumps(dict(summary=out, rows=rows), indent=1))
    return out


REVIEW_PROBES = (
    ("reference_tuned", None, {}),
    ("reference", None, {}),
    ("probe_end_coast_18h", "EndCoast", dict(hours=18, total_min=None)),
    ("probe_end_coast_36h", "EndCoast", dict(hours=36, total_min=None)),
    ("probe_end_coast_sp_18h", "EndCoastSetpoint", dict(hours=18, total_min=None)),
    ("probe_low_band", "LowBand", dict(off=0.45)),
    ("probe_flapper", "Flapper", {}),
    ("probe_bangbang55", "BangBang", dict(hi=55)),
    ("probe_ref_delta2", "RefDelta", dict(restart_delta=2)),
    ("probe_ref_delta10", "RefDelta", dict(restart_delta=10)),
    ("probe_ref_quiet", "RefDelta", dict(quiet=True)),
    ("probe_pulse40", "Pulse", dict(hi=40, period=180)),
    ("probe_pwm_7_13", "Pulse", dict(hi=40, period=20, duty=0.35)),
)


def cmd_review(seeds=(0, 1, 2, 3, 4), scen=("oct_mild", "nov_mixed", "dec_damp", "mar_shoulder"),
               variants=("nominal", "flat_load", "legacy_cop", "high_start_loss", "raw_return")):
    from lab.sim import ranking as RK
    tasks = [(c, cls, p, sc, v, sd) for sc in scen for v in variants for sd in seeds for c, cls, p in REVIEW_PROBES]
    rows = _pool(tasks)
    prs = RK.paired(rows, "reference_tuned")
    txt = RK.paired_table(prs)
    print(txt)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "review_probes.json").write_text(json.dumps(dict(rows=rows, paired=prs), indent=1))
    (OUT / "review_probes.txt").write_text(txt + "\n")
    return prs


# ------------------------------------------------------------------------------------------
# review round 2
# ------------------------------------------------------------------------------------------

def cmd_house():
    """N5: the replay's room agreement is true by construction (the recorded residual is the heat
    that makes the model follow the recorded room under the recorded heat). Replace the residual by
    something that does not use the recorded room and see how far the simulated room drifts:
    zero, its window mean, its daily means (slow part only), and a bootstrap of other recorded
    days (three draws)."""
    out = {}
    for name in ("recorded", "recorded_spring"):
        exo = S.build(name)
        d0 = np.asarray(exo.dist, float)
        day = X.local_day_index(exo.grid)
        _, inv = np.unique(day, return_inverse=True)
        dm = np.bincount(inv, d0) / np.bincount(inv)
        _, hp = SIM.plant("nominal")
        modes = {"recorded (by construction)": d0, "zero": np.zeros_like(d0), "window mean": np.full_like(d0, d0.mean()),
                 "daily mean": dm[inv]}
        for sd in (0, 1, 2):
            modes[f"bootstrap seed {sd}"] = X.bootstrap_disturbance(exo.grid, 9000 + sd, hp)
        res = {}
        for tag, dist in modes.items():
            s, _ = replay(name, "nominal", dist=dist)
            res[tag] = {k: s[k] for k in ("room_rms_k", "room_bias_k", "room_err_p95_abs_k", "room_max_abs_k",
                                          "room_rms_first_24h", "room_rms_first_72h", "elec_ratio", "heat_ratio",
                                          "starts_ratio") if k in s}
            res[tag]["dist_mean_kw"] = round(float(np.mean(dist)), 3)
            print(name, tag, res[tag], flush=True)
        out[name] = res
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "house_free.json").write_text(json.dumps(out, indent=1))
    return out


def cmd_comfort(seeds=(0, 1, 2, 3), scen=("season",), gains=True):
    """N2: price of comfort. reference_tuned with a day/night aim shift of 0 / 0.2 / 0.4 / 0.6 K
    (warmer 10-22 local, cooler otherwise; every member tuned to the target mean air): energy
    saved per K-hour of extra |air - target|. Also the gain family (ref_kp, ref_ki) for the
    baseline choice."""
    tasks = []
    fam = [dict(ref_shift_k=a) for a in (0.0, 0.2, 0.4, 0.6)]
    if gains:
        fam += [dict(ref_kp=kp, ref_ki_per_h=ki) for kp, ki in ((1.0, 0.1), (2.0, 0.15), (3.0, 0.3), (4.0, 0.5),
                                                                (6.0, 0.8))]
    for sc in scen:
        for sd in seeds:
            for f in fam:
                tasks.append(("reference_tuned", None, f, sc, "nominal", sd))
    rows = _pool(tasks)
    out = {}
    for sc in scen:
        res = {}
        for f in fam:
            key = ",".join(f"{k}={v}" for k, v in f.items())
            rr = [r for r in rows if r["scenario"] == sc and r["params"] == f]
            res[key] = dict(n=len(rr), elec_norm=round(float(np.mean([r["elec_norm_kwh"] for r in rr])), 1),
                            comfort_kh=round(float(np.mean([r["comfort_kh"] for r in rr])), 1),
                            mae=round(float(np.mean([r["mae_air"] for r in rr])), 3),
                            mean_air=round(float(np.mean([r["mean_air"] for r in rr])), 3),
                            starts_per_day=round(float(np.mean([r["starts_per_day"] for r in rr])), 2),
                            elec=round(float(np.mean([r["elec_kwh"] for r in rr])), 1))
        base = [r for r in rows if r["scenario"] == sc and r["params"] == dict(ref_shift_k=0.0)]
        prices = []
        for a in (0.2, 0.4, 0.6):
            sh = [r for r in rows if r["scenario"] == sc and r["params"] == dict(ref_shift_k=a)]
            for b_ in base:
                m = [r for r in sh if r["seed"] == b_["seed"]]
                if m and m[0]["comfort_kh"] > b_["comfort_kh"]:
                    prices.append(((b_["elec_norm_kwh"] - m[0]["elec_norm_kwh"]), (m[0]["comfort_kh"] - b_["comfort_kh"]), a))
        de = np.array([p[0] for p in prices])
        dk = np.array([p[1] for p in prices])
        lam = float(np.sum(de * dk) / np.sum(dk * dk)) if len(dk) else float("nan")  # least squares through 0
        res["price_kwh_per_kh"] = round(lam, 4)
        res["price_points"] = [[round(a, 3), round(b, 1), c] for a, b, c in prices]
        out[sc] = res
        print(sc, json.dumps(res, indent=1))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "comfort_price.json").write_text(json.dumps(dict(summary=out, rows=rows), indent=1, default=float))
    return out


REVIEW2_PROBES = (
    ("reference_tuned", None, {}),
    ("probe_symshift06", None, dict(ref_shift_k=0.6), "reference_tuned"),
    ("probe_dayshift04", None, dict(ref_shift_k=0.4), "reference_tuned"),
    ("probe_low_band", "LowBand", dict(off=0.09)),
    ("probe_wc", "WeatherComp", {}),
    ("probe_lowslow", "LowSlow", {}),
    ("probe_pulse40", "Pulse", dict(hi=40, period=180)),
    ("probe_ref_delta2", "RefDelta", dict(restart_delta=2)),
)


def cmd_review2(seeds=(0, 1, 2), scen=("season", "nov_mixed", "dec_damp", "jan_cold"), variants=None):
    """Review-round-2 probes through the new ranking: comfort priced in, start-cost band, the new
    mandatory variants."""
    from lab.sim import ranking as RK
    variants = variants or ("nominal", "partload_lo", "partload_hi", "flat_load", "frost_melt_lo", "frost_melt_hi",
                            "light_slab", "heavy_slab", "sun_plus30", "sun_minus30", "forecast_pessimistic")
    tasks = []
    for sc in scen:
        sds = seeds[:2] if sc == "season" else seeds
        for v in variants:
            for sd in sds:
                for pr in REVIEW2_PROBES:
                    tasks.append(pr + (sc, v, sd) if len(pr) == 3 else (pr[0], pr[1], pr[2], sc, v, sd, pr[3]))
    rows = _pool(tasks)
    prs = RK.paired(rows, "reference_tuned")
    txt = RK.paired_table(prs) + "\n\n" + RK.verdict_summary(prs)
    print(txt)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "review2_probes.json").write_text(json.dumps(dict(rows=rows, paired=prs), indent=1, default=float))
    (OUT / "review2_probes.txt").write_text(txt + "\n")
    return prs


# ------------------------------------------------------------------------------------------
# (d) speed
# ------------------------------------------------------------------------------------------

def cmd_speed():
    out = {}
    t0 = time.perf_counter()
    exo = S.build("season")
    out["build_s"] = round(time.perf_counter() - t0, 2)
    for name in ("fixed_setpoint", "unit_curve", "room_thermostat"):
        c, _ = _ctrl(name)
        t0 = time.perf_counter()
        r = SIM.run(c, exo)
        wall = time.perf_counter() - t0
        out[name] = dict(wall_s=round(wall, 2), minutes=len(exo.grid),
                         us_per_step=round(1e6 * wall / len(exo.grid), 1), controller_s=r["meta"]["controller_s"])
        print(name, out[name])
    from lab.sim.harness import run_one
    t0 = time.perf_counter()
    run_one("unit_curve", "season", write=True, csv_out=True, out_dir=OUT / "speed")
    out["unit_curve_with_build_and_csv_s"] = round(time.perf_counter() - t0, 2)
    print(out)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "speed.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("replay", "all"):
        cmd_replay()
    if what in ("season", "all"):
        cmd_season()
    if what in ("sweeps", "all"):
        cmd_sweeps()
    if what in ("speed", "all"):
        cmd_speed()
    if what in ("normalisation", "all"):
        cmd_normalisation()
    if what in ("review", "all"):
        cmd_review()
    if what in ("house", "all"):
        cmd_house()
    if what == "comfort":
        cmd_comfort()
    if what in ("review2", "all"):
        cmd_review2()
