"""Open-loop validation of lab/sim/unit.py against the recorded minute data.

The unit model is driven with the recorded setpoint, restart hysteresis, return (inlet)
temperature, outdoor air temperature/humidity (ERA5, as in the fit) and the recorded hot-water
demand; its compressor starts, run lengths, outlet temperature and electricity are compared
with what the real unit did. Results (private: real dates) go to .local/lab-results/unit/.

    .local/lab-venv/bin/python -m lab.sim.validate_unit [variant]
"""
import json
import sys

import numpy as np

from lab.data.common import RESULTS, epoch, iso_min, load_minute
from lab.sim.unit import VARIANTS, VersatiUnit

PERIODS = {
    "A_legacy_winter": ("2026-02-25T00:00Z", "2026-05-06T00:00Z"),
    "C1_autumn_old_esp": ("2026-10-08T06:00Z", "2026-10-22T18:00Z"),
    "C2_autumn_new_esp": ("2026-10-23T00:00Z", "2026-11-06T16:00Z"),
}


def ffill(x):
    x = np.asarray(x, float).copy()
    ok = np.isfinite(x)
    if not ok.any():
        return x
    idx = np.where(ok, np.arange(len(x)), 0)
    np.maximum.accumulate(idx, out=idx)
    out = x[idx]
    out[: np.argmax(ok)] = x[np.argmax(ok)]
    return out


def runs_of(mask):
    """(start, end) index pairs of True stretches."""
    m = np.r_[False, mask, False].astype(int)
    d = np.diff(m)
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


def dhw_demand_from_record(status, comp, pre_pause=7):
    """Recorded hot-water compressor intervals, started earlier by the pre-pause when the unit
    was running (heat) or stopped less than the pause before, so the model's own pause lines up."""
    dhw = (status == "HOT WATER") & (comp == 1)
    dem = dhw.copy()
    for a, b in runs_of(dhw):
        lo = max(0, a - pre_pause)
        # was the compressor on in heat within the pause window? then the demand began then
        prior = comp[lo:a] == 1
        if prior.any():
            # find the last heat-running minute before a
            k = a - 1
            while k > lo and comp[k] != 1:
                k -= 1
            start = k + 1 if comp[k] == 1 else lo
            dem[start:a] = True
    return dem


# Return-temperature perturbation model used to close the loop when the simulated unit does
# something different from the real one (otherwise a simulated run that outlasts the real one
# sees the recorded return fall after the real stop and never stops). Fitted by least squares on
# all heating-mode minutes with Versati data (127 000 minutes, R2 0.20 on 1-minute changes):
# dT_ret/dt = A_LOOP*(T_supply(t-LAG) - T_ret) + B_LOOP*(T_room + 1 - T_ret).
# It is a crude stand-in for the floor model of the next stage.
A_LOOP, B_LOOP, LAG = 0.0266, 0.0117, 3


def simulate(d, sl, params, closed_loop=True):
    u = VersatiUnit(params)
    sp = ffill(d["setpoint"][sl])
    rd = ffill(d["restart_delta"][sl])
    rd[~np.isfinite(rd)] = 5.0
    status_r = d["unit_status"][sl]
    inl = np.asarray(d["inlet"][sl], float).copy()
    # during recorded hot water (and the valve pause after) the inlet sensor sees the tank coil:
    # hold the last loop value instead
    dh = status_r == "HOT WATER"
    hold = dh | (np.convolve(dh.astype(float), np.ones(9), "full")[: len(dh)] > 0)
    inl[hold] = np.nan
    tr = ffill(inl)
    comp_r = np.nan_to_num(d["compressor"][sl], nan=0.0)
    q_rec_dt = np.where((comp_r == 1) & (status_r == "HEAT"),
                        np.nan_to_num(d["outlet"][sl] - d["inlet"][sl] + 0.30), 0.0)
    ta = ffill(d["wx_t"][sl])
    rh = ffill(d["wx_rh"][sl])
    he = d["heating_mode"][sl]
    he = np.where(np.isfinite(he), he == 4, True)
    status = d["unit_status"][sl]
    comp = np.nan_to_num(d["compressor"][sl], nan=0.0)
    dem = dhw_demand_from_record(status, comp)
    n = len(sp)
    out = {k: np.zeros(n) for k in ("t_outlet", "q", "p", "comp", "started", "heat", "dhw", "defrost")}
    kf = params.k_flow
    dsup = np.zeros(n)  # simulated minus recorded supply
    dret = 0.0
    for i in range(n):
        if closed_loop and i >= LAG:
            dret = dret * (1 - A_LOOP - B_LOOP) + A_LOOP * dsup[i - LAG]
        r = u.step(sp[i], rd[i], tr[i] + dret, ta[i], rh[i], heating_enabled=bool(he[i]), dhw_demand=bool(dem[i]))
        if r.loop_flow_lpm > 0:
            dsup[i] = dret + r.q_loop / kf - q_rec_dt[i]
        else:
            dsup[i] = dsup[i - 1] if i else 0.0
        out["t_outlet"][i] = r.t_outlet
        out["q"][i] = r.q_loop
        out["p"][i] = r.p_outdoor
        out["comp"][i] = r.compressor
        out["started"][i] = r.started
        out["heat"][i] = r.status in ("heat", "defrost")
        out["dhw"][i] = r.status == "dhw"
        out["defrost"][i] = r.status == "defrost"
    out["n_defrost"] = u.n_defrost
    return out


def evaluate(d, name, a, b, params):
    T = d["time_epoch_s"]
    i0 = int(np.searchsorted(T, epoch(a)))
    i1 = int(np.searchsorted(T, epoch(b)))
    sl = slice(i0, i1)
    sim = simulate(d, sl, params)
    status = d["unit_status"][sl]
    comp = np.nan_to_num(d["compressor"][sl], nan=0.0)
    ok = d["versati_ok"][sl] == 1
    elec = d["elec_w"][sl] / 1000.0
    e_ok = np.isfinite(elec)
    rec_heat = (comp == 1) & (status == "HEAT")
    day = ((T[sl] - T[i0]) // 86400).astype(int)
    rows = []
    # recorded heat starts: compressor on-edges whose first minute is HEAT
    edge = (comp == 1) & (np.r_[0, comp[:-1]] == 0)
    rec_start = edge & (status == "HEAT")
    for u in np.unique(day):
        w = day == u
        if ok[w].mean() < 0.97 or e_ok[w].mean() < 0.97 or w.sum() < 1380:
            continue
        rows.append(dict(
            day=iso_min(T[sl][w][0])[:10],
            starts_rec=int(rec_start[w].sum()), starts_sim=int(sim["started"][w].sum()),
            heat_min_rec=int(rec_heat[w].sum()), heat_min_sim=int(sim["heat"][w].sum()),
            elec_rec=float(np.nansum(elec[w]) / 60), elec_sim=float(sim["p"][w].sum() / 60),
            elec_heat_rec=float(np.nansum(np.where(rec_heat[w] | (np.nan_to_num(d["defrost"][sl][w]) > 0) & (comp[w] == 1), elec[w], 0)) / 60),
            elec_heat_sim=float(np.sum(np.where(sim["heat"][w] == 1, sim["p"][w], 0)) / 60),
            wx_t=float(np.nanmean(d["wx_t"][sl][w])),
        ))
    # outlet error when both run in heat (not defrost), and run lengths
    both = rec_heat & (sim["heat"] == 1) & (sim["defrost"] == 0) & ok & (np.nan_to_num(d["defrost"][sl]) == 0)
    err = sim["t_outlet"][both] - d["outlet"][sl][both]
    age = np.zeros(len(rec_heat))
    for aa, bb in runs_of(rec_heat):
        age[aa:bb] = np.arange(bb - aa)
    bias_by_age = {}
    for lo, hi in ((0, 15), (15, 60), (60, 100000)):
        sel = both & (age >= lo) & (age < hi)
        e2 = sim["t_outlet"][sel] - d["outlet"][sl][sel]
        bias_by_age[f"{lo}-{hi}"] = round(float(np.mean(e2)), 3) if len(e2) else None
    k = params.k_flow
    q_rec = k * (d["outlet"][sl] - d["inlet"][sl] + 0.30)
    both_e = both & e_ok
    both_means = dict(q_sim=float(np.mean(sim["q"][both_e])), q_rec=float(np.nanmean(q_rec[both_e])),
                      p_sim=float(np.mean(sim["p"][both_e])), p_rec=float(np.nanmean(elec[both_e])))
    rec_runs = [bb - aa for aa, bb in runs_of(rec_heat)]
    sim_runs = [bb - aa for aa, bb in runs_of(sim["heat"] == 1)]
    # electricity per run: match recorded heat runs with overlapping simulated runs
    per_run = []
    for aa, bb in runs_of(rec_heat):
        if not ok[aa:bb].all() or not e_ok[aa:bb].all() or bb - aa < 15:
            continue
        per_run.append((float(np.sum(elec[aa:bb]) / 60), float(np.sum(sim["p"][aa:bb] * sim["heat"][aa:bb]) / 60)))
    per_run = np.array(per_run) if per_run else np.zeros((0, 2))
    days = len(rows)
    sr = sum(r["starts_rec"] for r in rows)
    ss = sum(r["starts_sim"] for r in rows)
    er = sum(r["elec_rec"] for r in rows)
    es = sum(r["elec_sim"] for r in rows)
    ehr = sum(r["elec_heat_rec"] for r in rows)
    ehs = sum(r["elec_heat_sim"] for r in rows)
    daily_e_err = [100 * (r["elec_sim"] / r["elec_rec"] - 1) for r in rows if r["elec_rec"] > 2]
    daily_s_err = [r["starts_sim"] - r["starts_rec"] for r in rows]
    summary = dict(
        period=name, days=days,
        starts_per_day_rec=sr / max(days, 1), starts_per_day_sim=ss / max(days, 1),
        starts_ratio=ss / max(sr, 1),
        daily_starts_mae=float(np.mean(np.abs(daily_s_err))) if rows else None,
        heat_min_ratio=sum(r["heat_min_sim"] for r in rows) / max(1, sum(r["heat_min_rec"] for r in rows)),
        elec_kwh_per_day_rec=er / max(days, 1), elec_kwh_per_day_sim=es / max(days, 1), elec_ratio=es / max(er, 1e-9),
        elec_heat_ratio=ehs / max(ehr, 1e-9),
        daily_elec_err_pct_mae=float(np.mean(np.abs(daily_e_err))) if daily_e_err else None,
        daily_elec_err_pct_p90=float(np.percentile(np.abs(daily_e_err), 90)) if daily_e_err else None,
        outlet_bias_k=float(np.mean(err)) if len(err) else None, outlet_bias_by_run_age=bias_by_age, both_running_means=both_means, outlet_rmse_k=float(np.sqrt(np.mean(err ** 2))) if len(err) else None,
        run_min_rec_p25_p50_p75=[float(x) for x in np.percentile(rec_runs, [25, 50, 75])] if rec_runs else None,
        run_min_sim_p25_p50_p75=[float(x) for x in np.percentile(sim_runs, [25, 50, 75])] if sim_runs else None,
        per_run_elec_ratio_median=float(np.median(per_run[:, 1] / per_run[:, 0])) if len(per_run) else None,
        per_run_elec_mape=float(np.mean(np.abs(per_run[:, 1] / per_run[:, 0] - 1)) * 100) if len(per_run) else None,
        defrosts_rec=int(np.sum(np.diff(np.r_[0, np.nan_to_num(d["defrost"][sl])]) > 0)), defrosts_sim=int(sim["n_defrost"]),
    )
    return summary, rows


def main(variant="central"):
    d = load_minute()
    params = VARIANTS[variant]()
    res = {}
    for name, (a, b) in PERIODS.items():
        s, rows = evaluate(d, name, a, b, params)
        res[name] = dict(summary=s, days=rows)
        print(f"\n== {name} ({s['days']} good days) variant={variant}")
        for k, v in s.items():
            if k in ("period", "days"):
                continue
            if isinstance(v, float):
                v = round(v, 3)
            elif isinstance(v, list):
                v = [round(x, 1) for x in v]
            print(f"  {k}: {v}")
    outdir = RESULTS / "unit"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"validation_{variant}.json").write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "central")
