"""Metrics of one simulated run (measured part only, warm-up excluded).

Electricity:
- `elec_kwh`: what the outdoor-unit meter would read (the house meter in Home Assistant);
  split into `elec_heat_kwh` (everything outside hot water: heating, defrost, standby) and
  `elec_dhw_kwh` (hot-water compressor and its 7-minute pauses).
- `indoor_kwh`: the unmetered indoor unit (circulation pump + controls, 0.10 kW all the time);
  `tank_heater_kwh`: the unmetered DHW element (ASSUMED 2 kW for 23 min after each DHW run).
- `elec_all_kwh` = metered + indoor + tank heater.
Heat: `heat_kwh` is the net heat into the floor loop (defrost draw subtracted); seasonal COP =
heat / space-heating metered electricity (`cop_space`), and with the indoor unit added
(`cop_space_incl_pump`).
Comfort uses both the true room air (`*_air`) and the thermometer as Home Assistant sees it
(`*_sensor`, 0.1 K report-on-change).
Days are local (Europe/Vilnius) calendar days; partial days at the ends count by their minutes.

Review round 1 additions (see docs/research/lab/SIMULATOR.md, "Review fixes"):
- `storage_delta_kwh`: heat stored in the house (loop water, slab, air, envelope: sum C_i x_i)
  at the end minus the start of the measured window. All controllers start from the same state,
  so differences between runs are differences in heat left behind.
- `elec_corr_kwh` = elec - storage_delta / cop_space: electricity with the stored heat bought
  back at the run's own COP.
- `elec_runout_kwh` (archive scenarios): electricity of the window plus a common 3-day run-out
  under the plain reference controller in the same weather, with the storage difference left
  after the run-out bought back at the run's COP. The run-out pays back heat a controller left in
  or took out of the house the way the house really would (the storage correction alone left
  about -3 % for 'heating off for the last 18 h' in nov_mixed; the run-out leaves -2..+1 %).
- `elec_norm_kwh` = (elec_runout, or elec_corr without a run-out) - h_total x (mean air -
  target) x hours / cop_space: also normalised to the target mean air with the house's steady
  loss coefficient (kW/K). This is the energy to rank on (lab/sim/ranking.py compares it as a
  difference against the baseline's window electricity); its residual dependence on mean air is
  checked in validate_sim (`normalisation`). `elec_norm_kwh_per_day` divides by window + run-out
  days.
- `mae_air`: time-weighted mean |air - target| (symmetric comfort; the +-0.5 K degree-hours stay
  for information).
- `assumption_flags`: which ASSUMED or extrapolated behaviour a run used (quiet mode, restart
  hysteresis outside 4-5 K, setpoints outside 25-39 degC, the minimum off time binding, space
  heating switched off, runs under 15 min, more than 8 starts a day, more than 48 writes a day).
- `elec_by_outdoor`: electricity per daily-mean outdoor bucket (cold-share breakdown).
- `room_report_p50_min` / `room_report_p90_min`: thermometer report intervals.
"""
from __future__ import annotations

import numpy as np

from lab.sim.exogenous import local_day_index

T_BUCKETS = (-99.0, -10.0, -5.0, 0.0, 5.0, 10.0, 99.0)
FLAG_STARTS_PER_DAY = 8.0     # beyond the recorded range (data: up to about 8 starts a day)
FLAG_WRITES_PER_DAY = 48.0    # ASSUMED register-wear limit (EEPROM / Modbus)
FLAG_SHORT_RUN_MIN = 15.0     # runs shorter than this were (almost) never recorded ...
FLAG_SHORT_RUN_SHARE = 0.05   # ... flag when more than this share of runs is that short
SP_REC_MIN, SP_REC_MAX = 25.0, 39.0  # setpoints ever written to the real unit


def _runs(mask):
    m = np.r_[False, np.asarray(mask, bool), False].astype(np.int8)
    d = np.diff(m)
    return np.flatnonzero(d == 1), np.flatnonzero(d == -1)


def _r(v, nd=3):
    if v is None:
        return None
    if isinstance(v, (float, np.floating)):
        if not np.isfinite(v):
            return None
        return round(float(v), nd)
    if isinstance(v, (np.integer,)):
        return int(v)
    return v


def compute(rec, meta):
    n = len(rec["t"])
    if n == 0:
        return {}
    days = n / 1440.0
    tgt = float(meta.get("target", 22.0))
    mode = rec["mode"].astype(int)
    p_out = rec["p_out"].astype(float)
    q = rec["q"].astype(float)
    comp = rec["comp"] > 0.5
    dhw = mode == 4
    heat_run = comp & ((mode == 2) | (mode == 3))
    defrost = mode == 3
    air = rec["t_air"].astype(float)
    sens = rec["room_s"].astype(float)
    t_out = rec["t_out"].astype(float)

    elec = p_out.sum() / 60.0
    elec_dhw = p_out[dhw].sum() / 60.0
    elec_heat = elec - elec_dhw
    indoor = rec["p_in"].astype(float).sum() / 60.0
    tank = rec["p_tank"].astype(float).sum() / 60.0
    heat = q.sum() / 60.0
    heat_gross = np.clip(q, 0, None).sum() / 60.0
    starts = int(rec["started"].sum())

    sp = rec["sp"].astype(float)

    # runs (space heating, defrost inside a run belongs to the run)
    a, b = _runs(heat_run)
    runs = (b - a).astype(float)
    # do not count a run cut by the window end as complete
    full = runs[b < n] if len(runs) else runs
    run_stats = dict(
        runs=int(len(runs)),
        run_min_median=_r(float(np.median(full))) if len(full) else None,
        run_min_p25=_r(float(np.percentile(full, 25))) if len(full) else None,
        run_min_p75=_r(float(np.percentile(full, 75))) if len(full) else None,
        run_min_mean=_r(float(np.mean(full))) if len(full) else None,
        runs_under_30_pct=_r(100.0 * float(np.mean(full < 30))) if len(full) else None,
        runs_under_60_pct=_r(100.0 * float(np.mean(full < 60))) if len(full) else None,
        compressor_hours_heat=_r(heat_run.sum() / 60.0),
    )

    # per local day
    day = local_day_index(rec["t"].astype(float))
    ud, inv = np.unique(day, return_inverse=True)
    cnt = np.bincount(inv)
    full_day = cnt >= 1380
    d_starts = np.bincount(inv, weights=rec["started"].astype(float))
    d_elec = np.bincount(inv, weights=p_out) / 60.0
    d_elec_heat = np.bincount(inv, weights=np.where(dhw, 0.0, p_out)) / 60.0
    d_heat = np.bincount(inv, weights=q) / 60.0
    d_tout = np.bincount(inv, weights=t_out) / cnt
    per_day = [dict(day_index=int(u), minutes=int(c), t_out=_r(to, 2), starts=int(s), elec_kwh=_r(e),
                    elec_heat_kwh=_r(eh), heat_kwh=_r(h))
               for u, c, to, s, e, eh, h in zip(ud, cnt, d_tout, d_starts, d_elec, d_elec_heat, d_heat)]
    buckets = {}
    for lo, hi in zip(T_BUCKETS[:-1], T_BUCKETS[1:]):
        sel = full_day & (d_tout >= lo) & (d_tout < hi)
        if sel.any():
            key = f"<{hi:+.0f}" if lo <= -90 else f">{lo:+.0f}" if hi >= 90 else f"{lo:+.0f}..{hi:+.0f}"
            buckets[key] = dict(days=int(sel.sum()), starts_per_day=_r(float(d_starts[sel].mean()), 2),
                                elec_kwh_per_day=_r(float(d_elec[sel].mean()), 2))

    # electricity by daily-mean outdoor bucket (cold share)
    e_buckets = {}
    for lo, hi in ((-99.0, -4.0), (-4.0, 4.0), (4.0, 99.0)):
        sel = (d_tout >= lo) & (d_tout < hi)
        key = "<-4" if lo <= -90 else ">+4" if hi >= 90 else "-4..+4"
        e_buckets[key] = dict(days=_r(float(cnt[sel].sum() / 1440.0), 2), elec_kwh=_r(float(d_elec[sel].sum())),
                              heat_kwh=_r(float(d_heat[sel].sum())))

    # comfort
    lo_t, hi_t = tgt - 0.5, tgt + 0.5
    comfort = {}
    for tag, v in (("air", air), ("sensor", sens)):
        comfort[f"dh_below_{tag}"] = _r(np.clip(lo_t - v, 0, None).sum() / 60.0, 2)
        comfort[f"dh_above_{tag}"] = _r(np.clip(v - hi_t, 0, None).sum() / 60.0, 2)
        comfort[f"rms_{tag}"] = _r(float(np.sqrt(np.mean((v - tgt) ** 2))))
        comfort[f"mae_{tag}"] = _r(float(np.mean(np.abs(v - tgt))))
        comfort[f"mean_{tag}"] = _r(float(np.mean(v)))
        comfort[f"min_{tag}"] = _r(float(np.min(v)), 2)
        comfort[f"max_{tag}"] = _r(float(np.max(v)), 2)
    lh = rec["local_hour"].astype(float)
    at7 = (lh >= 7.0) & (lh < 7.0 + 1.0 / 60.0 - 1e-9)
    if at7.any():
        comfort["room_0700_air_mean"] = _r(float(air[at7].mean()))
        comfort["room_0700_air_min"] = _r(float(air[at7].min()), 2)
        comfort["room_0700_sensor_mean"] = _r(float(sens[at7].mean()))

    # setpoint, water
    running_heat = comp & (mode == 2)
    water = dict(
        mean_outlet_running=_r(float(rec["outlet_s"][running_heat].mean())) if running_heat.any() else None,
        mean_supply_running=_r(float(rec["t_sup"][running_heat].mean())) if running_heat.any() else None,
        mean_return=_r(float(rec["t_ret"].mean())),
        anchor_mean_running_k=_r(float(rec["anchor"][running_heat].mean())) if running_heat.any() else None,
        mean_setpoint=_r(float(sp.mean())),
        max_setpoint=_r(float(sp.max()), 1),
        min_setpoint=_r(float(sp.min()), 1),
        heating_enabled_pct=_r(100.0 * float(rec["enabled"].mean()), 1),
        quiet_pct=_r(100.0 * float(rec["quiet"].mean()), 1),
    )

    # defrost and DHW
    da, db = _runs(defrost)
    dwa, dwb = _runs(comp & (mode == 4))
    other = dict(
        defrosts=int(len(da)),
        defrost_elec_kwh=_r(p_out[defrost].sum() / 60.0),
        defrost_heat_drawn_kwh=_r(-q[defrost].sum() / 60.0),
        dhw_runs=int(len(dwa)),
        dhw_elec_kwh=_r(elec_dhw),
        dhw_energy_kwh=_r(elec_dhw + tank),
    )
    wc = meta.get("write_counts", {})
    writes = int(rec["writes"].sum())

    # storage correction and normalisation to the target mean air (review round 1, C3)
    cop_m = heat / elec_heat if elec_heat > 0 and heat > 0 else float("nan")
    st0, st1 = meta.get("storage_start_kwh"), meta.get("storage_end_kwh")
    storage = (st1 - st0) if (st0 is not None and st1 is not None) else 0.0
    h_tot = float(meta.get("house_h_total_kw_per_k", 0.0) or 0.0)
    mean_air = float(np.mean(air))
    run_el = meta.get("runout_elec_kwh")
    if run_el is not None and np.isfinite(cop_m):
        # window + common run-out, with what the run-out did not restore bought back at the COP
        resid = meta["storage_runout_end_kwh"] - st0
        elec_runout = elec + run_el - resid / cop_m
    else:
        elec_runout = None
    if np.isfinite(cop_m):
        elec_corr = elec - storage / cop_m
        base_e = elec_runout if elec_runout is not None else elec_corr
        elec_norm = base_e - h_tot * (mean_air - tgt) * (n / 60.0) / cop_m
    else:
        elec_corr = elec_norm = elec

    # thermometer report intervals
    rep_idx = np.flatnonzero(rec["room_age"].astype(float) == 0)
    gaps = np.diff(rep_idx) if len(rep_idx) > 2 else np.array([])

    # assumption / extrapolation flags (review round 1, m2 and M1)
    delta = rec["delta"].astype(float)
    flags = []
    if float(rec["quiet"].mean()) > 0:
        flags.append("quiet")
    if np.any((delta < 4) | (delta > 5)):
        flags.append("restart_delta")
    sp_out = float(np.mean((sp < SP_REC_MIN) | (sp > SP_REC_MAX)))
    if sp_out > 0:
        flags.append("setpoint_range")
    if (meta.get("unit_counters") or {}).get("minoff_wait_min", 0) > 0:
        flags.append("min_off")
    if wc.get("heating_enabled", 0) > 0 or float(rec["enabled"].mean()) < 1.0:
        flags.append("heating_off")
    if len(full) and float(np.mean(full < FLAG_SHORT_RUN_MIN)) > FLAG_SHORT_RUN_SHARE:
        flags.append("runs_lt_15min")
    if starts / days > FLAG_STARTS_PER_DAY:
        flags.append("starts_gt_8")
    if writes / days > FLAG_WRITES_PER_DAY:
        flags.append("writes_gt_48")
    m = dict(
        days=_r(days, 2),
        elec_kwh=_r(elec), elec_kwh_per_day=_r(elec / days),
        elec_heat_kwh=_r(elec_heat), elec_heat_kwh_per_day=_r(elec_heat / days),
        elec_dhw_kwh=_r(elec_dhw),
        indoor_kwh=_r(indoor), tank_heater_kwh=_r(tank), elec_all_kwh=_r(elec + indoor + tank),
        heat_kwh=_r(heat), heat_kwh_per_day=_r(heat / days), heat_gross_kwh=_r(heat_gross),
        cop_space=_r(heat / elec_heat if elec_heat > 0 else float("nan")),
        cop_space_incl_pump=_r(heat / (elec_heat + indoor) if elec_heat + indoor > 0 else float("nan")),
        starts=starts, starts_per_day=_r(starts / days, 2),
        **run_stats,
        **water,
        **comfort,
        writes=writes, writes_per_day=_r(writes / days, 2), writes_by_field={k: int(v) for k, v in wc.items()},
        storage_delta_kwh=_r(storage), elec_corr_kwh=_r(elec_corr), elec_norm_kwh=_r(elec_norm),
        elec_runout_kwh=_r(elec_runout) if elec_runout is not None else None,
        runout_elec_kwh=_r(run_el) if run_el is not None else None,
        elec_norm_kwh_per_day=_r(elec_norm / (days + float(meta.get("runout_days") or 0.0))),
        room_report_p50_min=_r(float(np.median(gaps)), 1) if len(gaps) else None,
        room_report_p90_min=_r(float(np.percentile(gaps, 90)), 1) if len(gaps) else None,
        runs_under_15_pct=_r(100.0 * float(np.mean(full < FLAG_SHORT_RUN_MIN))) if len(full) else None,
        assumption_flags=",".join(flags),
        setpoint_out_of_range_pct=_r(100.0 * sp_out, 2),
        comfort_kh=_r(float(np.sum(np.abs(air - tgt))) / 60.0, 2),
        elec_by_outdoor=e_buckets,
        **other,
        t_out_mean=_r(float(t_out.mean()), 2),
        starts_by_outdoor=buckets,
        per_day=per_day,
    )
    return m


SUMMARY_KEYS = (
    ("elec_kwh_per_day", "kWh/d", 2),
    ("elec_norm_kwh_per_day", "norm/d", 2),
    ("elec_heat_kwh_per_day", "heat kWh/d", 2),
    ("cop_space", "COP", 2),
    ("starts_per_day", "starts/d", 1),
    ("run_min_median", "run p50", 0),
    ("runs_under_60_pct", "%<60m", 0),
    ("mean_outlet_running", "outlet", 1),
    ("mean_setpoint", "sp mean", 1),
    ("max_setpoint", "sp max", 0),
    ("mean_air", "air", 2),
    ("mae_air", "mae", 2),
    ("rms_air", "rms air", 2),
    ("dh_below_air", "Kh<-0.5", 1),
    ("dh_above_air", "Kh>+0.5", 1),
    ("min_air", "min air", 1),
    ("room_0700_air_mean", "07:00", 2),
    ("writes_per_day", "wr/d", 1),
    ("defrosts", "defr", 0),
)


def table(rows, keys=SUMMARY_KEYS, label_cols=("scenario", "controller")):
    """Plain-text table: rows are dicts with label columns + metrics."""
    head = list(label_cols) + [k[1] for k in keys] + ["flags"]
    body = []
    for r in rows:
        line = [str(r.get(c, "")) for c in label_cols]
        fl = r.get("assumption_flags") or ""
        for key, _, nd in keys:
            v = r.get(key)
            if v is None:
                line.append("-")
            elif nd == 0:
                line.append(f"{v:.0f}")
            else:
                line.append(f"{v:.{nd}f}")
        line.append(fl)
        body.append(line)
    widths = [max(len(h), *(len(b[i]) for b in body)) if body else len(h) for i, h in enumerate(head)]
    out = ["  ".join(h.rjust(w) if i >= len(label_cols) else h.ljust(w) for i, (h, w) in enumerate(zip(head, widths)))]
    out.append("  ".join("-" * w for w in widths))
    for b in body:
        out.append("  ".join(c.rjust(w) if i >= len(label_cols) else c.ljust(w) for i, (c, w) in enumerate(zip(b, widths))))
    return "\n".join(out)
