"""Evidence for the water-side unit model (lab/sim/unit.py), computed from the minute data.

Every number quoted in docs/research/lab/UNIT_MODEL.md comes from this script. It reads the
private dataset in .local/lab-data/ and writes .local/lab-results/unit/analysis.json (private:
it contains dates). Run from the repository root:

    .local/lab-venv/bin/python -m lab.sim.unit_analysis

Sections: firmware on/off logic, idle circulation, capacity control, loop flow (four methods),
refrigerant temperatures, COP fit (Carnot fraction + running overhead) for several assumed
flows and outlet penalties, start-up cost, defrost, hot water.
"""
from __future__ import annotations

import json
import math
import warnings
from collections import Counter

import numpy as np
from scipy.interpolate import RegularGridInterpolator
from scipy.optimize import least_squares

from lab.data.common import RESULTS, iso_min, load_minute

warnings.filterwarnings("ignore", category=RuntimeWarning)

CP = 4.186
SENSOR_DT_OFFSET = 0.30  # outlet - inlet reads -0.30 K while water circulates without heating
ETA_KNOTS = np.array([-10.0, -5.0, -2.0, 0.0, 2.0, 4.0, 6.0, 8.0, 12.0, 16.0])
OUT = {}


def runs_of(mask):
    m = np.r_[False, np.asarray(mask, bool), False].astype(np.int8)
    dd = np.diff(m)
    return list(zip(np.where(dd == 1)[0], np.where(dd == -1)[0]))


def pct(x, q=(5, 25, 50, 75, 95)):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return [round(float(v), 2) for v in np.percentile(x, q)] if len(x) else None


def kflow(F):
    return CP * F / 60.0


class D:
    """Minute data plus derived masks."""

    def __init__(self):
        d = load_minute()
        self.d = d
        self.T = d["time_epoch_s"]
        self.n = len(self.T)
        self.comp = np.nan_to_num(d["compressor"], nan=-1)
        self.on = self.comp == 1
        self.st = d["unit_status"]
        self.ok = d["versati_ok"] == 1
        self.sp = d["setpoint"]
        self.ow = d["opt_water"]
        self.out = d["outlet"]
        self.inl = d["inlet"]
        self.rd = d["restart_delta"]
        self.P = d["elec_w"] / 1000.0
        self.wx = d["wx_t"]
        self.rh = d["wx_rh"]
        self.hm = d["heating_mode"] == 4
        self.dTt = self.out - self.inl + SENSOR_DT_OFFSET  # true loop delta-T estimate
        self.tsup = self.inl + self.dTt  # true supply on the inlet-sensor scale
        self.age = np.zeros(self.n)
        self.runs = runs_of(self.on)
        for a, b in self.runs:
            self.age[a:b] = np.arange(b - a)
        df = (np.nan_to_num(d["defrost"]) > 0) | (np.nan_to_num(d["defrost_sig"]) > 0)
        self.df = np.nan_to_num(d["defrost"]) > 0
        self.near_df = np.convolve(df.astype(float), np.ones(15), "full")[: self.n] > 0
        idx = np.arange(self.n)
        lo = np.where(self.on, idx, -10**7)
        np.maximum.accumulate(lo, out=lo)
        self.since_on = idx - lo
        dh = self.st == "HOT WATER"
        ld = np.where(dh, idx, -10**7)
        np.maximum.accumulate(ld, out=ld)
        self.since_dhw = idx - ld
        # steady heat-running minutes: >= 20 min into a run, no defrost within 15 min, stable power
        e = self.P
        ep = np.r_[np.full(2, np.nan), e, np.full(2, np.nan)]
        W = np.lib.stride_tricks.sliding_window_view(ep, 5)
        stab = (np.nanmax(W, 1) - np.nanmin(W, 1)) < 0.08 * np.nanmean(W, 1)
        self.steady = (self.on & self.ok & (self.st == "HEAT") & (self.age >= 20) & ~self.near_df
                       & np.isfinite(e) & stab & np.isfinite(self.dTt) & (self.dTt > 0.8))


# ------------------------------------------------------------------------------------------
# 1. on/off logic
# ------------------------------------------------------------------------------------------

def start_rule(x: D):
    rows = []
    prev_end = -10**9
    for a, b in x.runs:
        if (x.st[a] == "HEAT" and a - prev_end >= 10 and x.ok[max(0, a - 30):a + 1].all()
                and not (x.st[max(0, a - 30):a] == "HOT WATER").any()):
            wrote_5 = bool(np.nanmax(np.abs(np.diff(x.sp[a - 6:a + 1]))) > 0)
            wrote_now = bool(x.sp[a] != x.sp[a - 1])
            rows.append(dict(rd=float(x.rd[a]), drift=not wrote_5, now=wrote_now,
                             g_ow=float(x.sp[a] - x.ow[a - 1]), g_out=float(x.sp[a] - x.out[a - 1]),
                             g_in=float(x.sp[a] - x.inl[a - 1])))
        prev_end = b
    res = {"n_starts_from_idle": len(rows)}
    for rd in (5.0, 4.0):
        for kind in ("drift", "write"):
            sel = [r for r in rows if r["rd"] == rd and (r["drift"] if kind == "drift" else not r["drift"])]
            res[f"delta{int(rd)}_{kind}"] = dict(
                n=len(sel), gap_opt_water=pct([r["g_ow"] for r in sel], (0, 5, 50, 95, 100)),
                gap_outlet=pct([r["g_out"] for r in sel], (0, 5, 50, 95, 100)),
                gap_inlet=pct([r["g_in"] for r in sel], (0, 5, 50, 95, 100)))
    # counter-test: idle minutes with setpoint - opt_water >= delta and no start within 2 min
    g = x.sp - x.ow
    idle = (x.comp == 0) & x.hm & x.ok & np.isfinite(g) & np.isfinite(x.rd) & (x.since_dhw > 20)
    nxt = np.r_[x.on[1:], False] | np.r_[x.on[2:], False, False]
    viol = idle & (g >= x.rd) & ~nxt
    clusters = runs_of(viol)
    kinds = Counter()
    for a, b in clusters:
        nxt_on = np.argmax(x.on[a:a + 600]) if x.on[a:a + 600].any() else -1
        st_next = x.st[a + nxt_on] if nxt_on >= 0 else ""
        kinds["followed by hot water within 10 min" if (st_next == "HOT WATER" and nxt_on <= 10)
              else "link glitch / other"] += 1
    res["idle_minutes_gap_ge_delta"] = int((idle & (g >= x.rd)).sum())
    res["of_which_no_start_within_2min"] = int(viol.sum())
    res["violation_clusters"] = dict(kinds)
    OUT["start_rule"] = res


def stop_rule(x: D):
    rows = []
    for a, b in x.runs:
        if x.st[a] != "HEAT" or b + 15 >= x.n or not x.ok[max(0, a - 2):b + 15].all():
            continue
        dhw_next = bool((x.st[b:b + 15] == "HOT WATER").any())
        dfend = bool(x.df[max(a, b - 8):b + 1].any())
        L = b - a
        ov = x.ow[a:b] - x.sp[a:b]
        tail = 0
        while tail < L and ov[L - 1 - tail] >= 2.0 - 1e-6:
            tail += 1
        wrote = bool((x.sp[b - 6:b + 1] != x.sp[b - 7]).any())
        rows.append(dict(L=L, dhw=dhw_next, dfend=dfend, wrote=wrote, tail=tail,
                         ov_new=float(x.ow[b - 1] - x.sp[b]), p_end=float(np.nanmean(x.P[b - 4:b - 1])),
                         a=int(a)))
    nat = [r for r in rows if not r["dhw"] and not r["dfend"]]
    nw = [r for r in nat if not r["wrote"]]
    w = [r for r in nat if r["wrote"]]
    res = dict(heat_runs=len(rows), stopped_for_dhw=sum(r["dhw"] for r in rows),
               ended_at_defrost=sum(r["dfend"] and not r["dhw"] for r in rows), natural=len(nat),
               natural_no_write=len(nw), natural_after_write=len(w),
               no_write_tail_minutes_ow_ge_sp_plus_2=dict(Counter(r["tail"] for r in nw).most_common()),
               no_write_power_last_3min_kw=pct([r["p_end"] for r in nw], (10, 50, 90)),
               write_ow_minus_new_sp_at_stop=pct([r["ov_new"] for r in w], (0, 5, 25, 50)),
               no_write_run_minutes=sorted(int(r["L"]) for r in nw))
    near_mark = sum(1 for r in nw if (r["L"] % 120) <= 12 or (r["L"] % 120) >= 118)
    res["no_write_stops_within_12min_after_120min_mark"] = near_mark
    # overshoot streaks inside runs that did not end the run
    streak = {}
    for xthr in (1.5, 1.8, 2.0):
        lens = []
        for a, b in x.runs:
            if x.st[a] != "HEAT" or not x.ok[a:b].all():
                continue
            ov = (x.ow[a:b] - x.sp[a:b] >= xthr - 1e-6) & ~x.df[a:b]
            for s0, s1 in runs_of(ov):
                if s1 < b - a:
                    lens.append(s1 - s0)
        lens = np.array(lens)
        streak[str(xthr)] = dict(n=len(lens), ge3=int((lens >= 3).sum()), max=int(lens.max()) if len(lens) else 0)
    res["overshoot_streaks_not_ending_run"] = streak
    # min run: shortest natural run
    res["shortest_runs"] = sorted(int(r["L"]) for r in rows)[:6]
    OUT["stop_rule"] = res


def surge_marks(x: D):
    """Power surges at 120-min multiples of continuous running (probably oil return)."""
    res = []
    for a, b in x.runs:
        if x.st[a] != "HEAT":
            continue
        for mark in (120, 240, 360, 480, 600):
            if b - a < mark - 2:
                break
            s = a + mark
            if (not x.ok[s - 15:s + 10].all() or x.df[s - 15:min(b, s + 10)].any()
                    or (x.sp[s - 15:min(b + 1, s + 10)] != x.sp[s - 15]).any()):
                continue
            p0 = np.nanmean(x.P[s - 30:s - 4])
            pmax = np.nanmax(x.P[s - 4:min(b, s + 8)])
            res.append((mark, x.ow[s - 5] - x.sp[s - 5], p0, pmax, b < s + 12, x.wx[s]))
    R = np.array(res, float)
    surge = R[:, 3] - R[:, 2] > 0.4
    out = dict(marks=len(R), surges=int(surge.sum()), stopped_within_12=int(R[:, 4].sum()),
               stopped_with_surge=int((surge & (R[:, 4] == 1)).sum()),
               surge_without_stop=int((surge & (R[:, 4] == 0)).sum()),
               surge_power_before_peak_kw=[round(float(np.median(R[surge, 2])), 2), round(float(np.median(R[surge, 3])), 2)])
    by_p = []
    for lo, hi in ((0, 0.8), (0.8, 1.0), (1.0, 1.2), (1.2, 1.5), (1.5, 2.0), (2.0, 9)):
        m = (R[:, 2] >= lo) & (R[:, 2] < hi)
        by_p.append(dict(p_kw=f"{lo}-{hi}", n=int(m.sum()), surge=int(surge[m].sum())))
    out["by_running_power"] = by_p
    by_ov = []
    for lo, hi in ((-9, -0.5), (-0.5, 0.2), (0.2, 9)):
        m = (R[:, 1] >= lo) & (R[:, 1] < hi)
        by_ov.append(dict(ow_minus_sp=f"{lo}..{hi}", n=int(m.sum()), surge=int(surge[m].sum())))
    out["by_ow_minus_sp"] = by_ov
    OUT["surge_120min"] = out


def off_times(x: D):
    offs, dhw2heat = [], []
    for (a0, b0), (a1, b1) in zip(x.runs[:-1], x.runs[1:]):
        if not x.ok[b0:a1 + 1].all():
            continue
        if x.st[a0] == "HEAT" and x.st[a1] == "HEAT":
            offs.append(a1 - b0)
        if x.st[a0] == "HOT WATER" and x.st[a1] == "HEAT" and x.hm[b0]:
            dhw2heat.append(a1 - b0)
    # heat -> hot water pause (heat run pre-empted)
    pre = []
    for (a0, b0), (a1, b1) in zip(x.runs[:-1], x.runs[1:]):
        if x.st[a0] == "HEAT" and x.st[a1] == "HOT WATER" and x.ok[b0:a1 + 1].all() and a1 - b0 < 20:
            pre.append(a1 - b0)
    OUT["off_times"] = dict(heat_to_heat_min=dict(n=len(offs), min=int(min(offs)), p=pct(offs, (1, 5, 10, 50))),
                            dhw_to_heat_min=dict(n=len(dhw2heat), min=int(min(dhw2heat)), p=pct(dhw2heat, (0, 10, 25, 50))),
                            heat_stopped_to_dhw_start_min=dict(n=len(pre), values=dict(Counter(pre).most_common())))


def idle_circulation(x: D):
    base = (x.comp == 0) & x.ok & x.hm & (x.since_dhw > 30)
    rows = []
    for lo, hi in ((2, 5), (10, 30), (60, 180), (180, 600)):
        m = base & (x.since_on >= lo) & (x.since_on < hi)
        rows.append(dict(idle_min=f"{lo}-{hi}", n=int(m.sum()),
                         ow_minus_inlet=round(float(np.nanmedian(x.ow[m] - x.inl[m])), 2),
                         outlet_minus_inlet=round(float(np.nanmedian(x.out[m] - x.inl[m])), 2),
                         inlet_minus_room=round(float(np.nanmedian(x.inl[m] - x.d["room"][m])), 2)))
    m = x.on & x.ok & (x.st == "HEAT") & ~x.near_df
    OUT["idle_circulation"] = dict(
        by_idle_age=rows,
        running_ow_minus_outlet=round(float(np.nanmedian(x.ow[m] - x.out[m])), 2),
        ow_minus_inlet_idle_by_level={f"{lo}-{lo + 2}": round(float(np.nanmean((x.out - x.inl)[base & (x.since_on > 20) & (x.inl >= lo) & (x.inl < lo + 2)])), 3)
                                      for lo in (22, 24, 26, 28)})
    # 2025 indoor-unit meter: indoor kWh per hour vs outdoor kWh per hour
    import csv
    from lab.data.common import DATA
    rr = list(csv.DictReader(open(DATA / "hourly.csv")))
    xs = np.array([(float(r["elec_in_kwh"]), float(r["elec_out_kwh"])) for r in rr
                   if r["elec_in_kwh"] not in ("", "nan") and r["elec_out_kwh"] not in ("", "nan")])
    meter = []
    for lo, hi in ((0, 0.03), (0.03, 0.5), (0.5, 2), (2, 9)):
        s = (xs[:, 1] >= lo) & (xs[:, 1] < hi)
        meter.append(dict(outdoor_kwh_per_h=f"{lo}-{hi}", hours=int(s.sum()), indoor_kwh_per_h=round(float(np.median(xs[s, 0])), 3)))
    OUT["indoor_meter_2025"] = meter


# ------------------------------------------------------------------------------------------
# 2. capacity control
# ------------------------------------------------------------------------------------------

def capacity_control(x: D, F=29.0):
    k = kflow(F)
    Q = k * x.dTt
    # start-up profile
    prof = []
    prev = -999
    for a, b in x.runs:
        if (x.st[a] == "HEAT" and a - prev >= 30 and b - a >= 40 and x.ok[a - 3:a + 40].all()
                and not x.near_df[a:a + 40].any() and (x.sp[a:a + 30] == x.sp[a]).all()
                and np.isfinite(x.P[a - 2:a + 40]).all()):
            prof.append((x.P[a - 2:a + 40], Q[a - 2:a + 40], x.ow[a - 2:a + 40] - x.sp[a]))
        prev = b
    P = np.array([p[0] for p in prof])
    QQ = np.array([p[1] for p in prof])
    E = np.array([p[2] for p in prof])
    start = [dict(minute=j - 2, p_kw=round(float(np.median(P[:, j])), 2),
                  q_kw=round(float(np.nanmedian(QQ[:, j])), 2), ow_minus_sp=round(float(np.nanmedian(E[:, j])), 2))
             for j in list(range(0, 16)) + [19, 24, 29, 39]]
    # rate of change vs error
    n = x.n
    dP = np.full(n, np.nan)
    dP[:-4] = (x.P[4:] - x.P[:-4]) / 4
    dQ = np.full(n, np.nan)
    dQ[:-4] = (Q[4:] - Q[:-4]) / 4
    on4 = x.on.copy()
    on4[:-4] &= x.on[4:]
    spw = np.r_[False, np.diff(x.sp) != 0]
    rw = np.convolve(spw.astype(float), np.ones(5), "full")[:n] > 0
    mk = ((x.age % 120) >= 115) | ((x.age % 120) <= 12)
    g = on4 & x.ok & (x.st == "HEAT") & (x.age >= 14) & ~x.near_df & ~rw & ~mk & np.isfinite(dP)
    err = x.sp - x.ow
    rate = []
    for lo, hi in ((-3, -1.5), (-1.5, -0.6), (-0.6, -0.3), (-0.3, 0), (0, 0.6), (0.6, 1.0), (1.0, 1.5), (1.5, 2.5)):
        s = g & (err >= lo) & (err < hi)
        rate.append(dict(err=f"{lo}..{hi}", n=int(s.sum()), dP_w_per_min_mean=round(1000 * float(np.nanmean(dP[s])), 1),
                         dQ_kw_per_min_mean=round(float(np.nanmean(dQ[s])), 3), dT_k_per_min_mean=round(float(np.nanmean(dQ[s])) / k, 3)))
    # run-wise minimum sustained capacity (10-min means)
    rows = []
    for a, b in x.runs:
        if x.st[a] != "HEAT" or b - a < 45:
            continue
        best = None
        for s0 in range(a + 20, b - 10):
            w = slice(s0, s0 + 10)
            if (not x.ok[w].all() or x.near_df[w].any() or mk[w].any() or (x.st[w] != "HEAT").any()
                    or not np.isfinite(x.P[w]).all()):
                continue
            dt = float(np.nanmean(x.dTt[w]))
            if best is None or dt < best[0]:
                best = (dt, float(np.mean(x.P[w])), float(np.mean(x.wx[w])), float(np.mean(err[w])))
        if best:
            rows.append(best)
    R = np.array(rows)
    floor = R[:, 3] < 0.0
    c = np.polyfit(R[floor, 2], R[floor, 0], 1)
    cp_ = np.polyfit(R[floor, 2], R[floor, 1], 1)
    bands = []
    for lo, hi in ((-20, -5), (-5, 0), (0, 3), (3, 6), (6, 9), (9, 16)):
        s = (R[:, 2] >= lo) & (R[:, 2] < hi)
        bands.append(dict(wx=f"{lo}..{hi}", runs=int(s.sum()), min_dT_p25_p50=pct(R[s, 0], (25, 50)),
                          p_kw_p50=round(float(np.median(R[s, 1])), 2) if s.any() else None))
    # ceiling
    gg = x.on & x.ok & (x.st == "HEAT") & (x.age >= 3) & ~x.near_df & np.isfinite(x.P)
    ceil = []
    for lo, hi in ((-20, -12), (-12, -5), (-5, 0), (0, 5), (5, 10), (10, 20)):
        s = gg & (x.wx >= lo) & (x.wx < hi)
        ceil.append(dict(wx=f"{lo}..{hi}", minutes=int(s.sum()), p_kw_p99=round(float(np.percentile(x.P[s], 99)), 2),
                         dT_p99=round(float(np.nanpercentile(x.dTt[s], 99)), 2)))
    OUT["capacity"] = dict(flow_assumed_lpm=F, n_clean_starts=len(prof), startup=start, rate_vs_error=rate,
                           min_sustained_by_band=bands, min_dT_fit=dict(a=round(float(c[1]), 2), b_per_K=round(float(c[0]), 3), runs=int(floor.sum())),
                           min_p_fit=dict(a=round(float(cp_[1]), 2), b_per_K=round(float(cp_[0]), 3)), ceiling=ceil)


# ------------------------------------------------------------------------------------------
# 3. flow, refrigerant temperatures, COP
# ------------------------------------------------------------------------------------------

def refrigerant_temps(x: D, F=29.0):
    k = kflow(F)
    Q = k * x.dTt
    g = x.steady & np.isfinite(x.d["defrost_t"])
    te = x.d["defrost_t"]
    X = np.c_[np.ones(g.sum()), Q[g]]
    c, *_ = np.linalg.lstsq(X, te[g] - x.wx[g], rcond=None)
    plateau = []
    for lo in range(-10, 16, 2):
        s = g & (x.wx >= lo) & (x.wx < lo + 2)
        if s.sum() > 50:
            plateau.append(dict(wx=f"{lo}..{lo + 2}", coil_t=round(float(np.median(te[s])), 1), n=int(s.sum())))
    cond = {}
    for name in ("disch_press_t", "liquid_pipe_t"):
        v = x.d[name]
        s = g & np.isfinite(v)
        cc, *_ = np.linalg.lstsq(np.c_[np.ones(s.sum()), Q[s]], v[s] - x.out[s], rcond=None)
        cond[name] = dict(minus_outlet_at_0kw=round(float(cc[0]), 2), per_kw=round(float(cc[1]), 3))
    s = x.steady
    OUT["refrigerant"] = dict(
        coil_minus_wx_fit=dict(a=round(float(c[0]), 2), per_kw=round(float(c[1]), 3)), coil_by_wx=plateau, condensing=cond,
        suction_minus_coil=pct((x.d["suction_t"] - te)[s], (10, 50, 90)),
        discharge_t=pct(x.d["discharge_t"][s], (10, 50, 90)),
        econ_out_minus_in=pct((x.d["econ_out_t"] - x.d["econ_in_t"])[s], (10, 50, 90)))


def _cycle_grid():
    from lab.sim import r32
    te = np.arange(-25, 16, 2.5)
    tc = np.arange(22, 58, 2.0)
    G = np.array([[r32.cycle(a, b, superheat=3, subcool=2, eta_overall=1.0, shell_loss=0.0)[0] for b in tc] for a in te])
    return RegularGridInterpolator((te, tc), G, bounds_error=False, fill_value=None)


def _datasheet_cop():
    # Versati III SP10 datasheet (incl. ~0.075 kW pump) converted to outdoor-unit COP; log-linear
    ta = np.array([-7.0, 7.0])
    tw = np.array([35.0, 45.0, 55.0])
    Q = np.array([[6.65, 6.65, 6.08], [9.5, 9.5, 8.74]])
    C = np.array([[2.81, 2.23, 1.58], [4.61, 3.60, 2.59]])
    f = RegularGridInterpolator((ta, tw), np.log(Q / (Q / C - 0.075)), bounds_error=False, fill_value=None)
    return lambda a, w: np.exp(f(np.c_[a, w]))


def flow_estimates(x: D):
    res = {}
    s = x.steady
    idx = np.where(s & np.isfinite(x.d["defrost_t"]))[0]
    # (a) refrigerant cycle: COP from evaporating (coil sensor) and condensing (outlet + approach)
    # temperatures with an overall compressor efficiency
    f = _cycle_grid()
    a = {}
    for eta in (0.5, 0.6, 0.7):
        for capp in (0.5, 1.0, 2.0):
            ci = f(np.c_[x.d["defrost_t"][idx], x.out[idx] + capp])
            Q = ((ci - 1) * eta + 1) * (x.P[idx] - 0.06)
            a[f"eta{eta}_cond+{capp}"] = round(float(np.median(Q / (CP * x.dTt[idx]) * 60)), 1)
    res["a_refrigerant_cycle"] = a
    # calibration of eta on the datasheet points (full load): approach 7 K evap, 2.5 K cond
    pts = [("A7/W35", 7, 35, 9.5, 4.61), ("A7/W45", 7, 45, 9.5, 3.60), ("A-7/W35", -7, 35, 6.65, 2.81), ("A-7/W45", -7, 45, 6.65, 2.23)]
    cal = {}
    for n_, ta, tw, q, cop in pts:
        cop_c = q / (q / cop - 0.15)
        ci = float(f(np.c_[ta - 7, tw + 2.5])[0])
        cal[n_] = round((cop_c - 1) / (ci - 1), 3)
    res["a_eta_overall_implied_by_datasheet"] = cal
    # (b) design flow for the nominal rating at 5 K spread
    res["b_nominal_9p5kw_at_5K_lpm"] = round(9.5 / (CP * 5) * 60, 1)
    # (b') datasheet COP applied to near-full-load operation
    cop_ds = _datasheet_cop()
    th = np.nan_to_num(x.d["tank_heater"])
    dh = []
    for a0, b0 in runs_of(x.on & (x.st == "HOT WATER")):
        if b0 - a0 < 15 or not x.ok[a0 - 2:b0].all() or th[a0:b0].any():
            continue
        w = slice(a0 + 3, b0)
        g = np.isfinite(x.dTt[w]) & np.isfinite(x.P[w])
        if g.sum() < 10:
            continue
        cop = cop_ds(x.wx[w][g], x.out[w][g])
        dh.append(float(np.sum(cop * x.P[w][g]) / np.sum(CP * x.dTt[w][g] / 60)))
    res["b_datasheet_cop_dhw_runs_lpm"] = dict(n=len(dh), p25_50_75=pct(dh, (25, 50, 75)))
    hb = {}
    for lo, hi in ((1.8, 2.4), (2.4, 3.2), (3.2, 5.0)):
        k = np.where(s & (x.P >= lo) & (x.P < hi))[0]
        Fk = cop_ds(x.wx[k], x.out[k]) * x.P[k] / (CP * x.dTt[k] / 60)
        hb[f"P {lo}-{hi} kW"] = dict(n=len(k), wx_median=round(float(np.median(x.wx[k])), 1), p25_50_75=pct(Fk, (25, 50, 75)))
    res["b_datasheet_cop_heat_high_power_lpm"] = hb
    # (b'') maximum-capacity table at -15 degC: Qmax(-15, W35) = 0.74 x 9.5 kW
    k = np.where(s & (x.wx < -12))[0]
    res["b_qmax_table_cold_upper_bound_lpm"] = dict(n=len(k), wx=round(float(np.median(x.wx[k])), 1),
                                                    p_kw=round(float(np.median(x.P[k])), 2), dT=round(float(np.median(x.dTt[k])), 2),
                                                    flow_if_at_table_max=round(0.74 * 9.5 / (CP * float(np.median(x.dTt[k]))) * 60, 1))
    # (c) house energy consistency: implied heat demand slope for each flow (hourly, Feb-Apr)
    hours = {}
    t0 = x.T[0]
    hidx = ((x.T - t0) // 3600).astype(int)
    heat_dT = np.where(x.on & (x.st == "HEAT"), np.nan_to_num(x.dTt), 0.0)
    nh = hidx.max() + 1
    sdT = np.bincount(hidx, heat_dT, nh) / 60  # K*h
    cnt = np.bincount(hidx, x.ok.astype(float), nh)
    wxh = np.bincount(hidx, np.nan_to_num(x.wx), nh) / np.maximum(np.bincount(hidx, minlength=nh), 1)
    roomh = np.bincount(hidx, np.nan_to_num(x.d["room"]), nh) / np.maximum(np.bincount(hidx, minlength=nh), 1)
    dhw_h = np.bincount(hidx, (x.st == "HOT WATER").astype(float), nh)
    good = (cnt >= 60) & (dhw_h == 0)
    # daily aggregation (reduces slab storage effects)
    day = np.arange(nh) // 24
    nd = day.max() + 1
    dd = np.bincount(day[good], sdT[good], nd)
    hd = np.bincount(day[good], minlength=nd)
    dwx = np.bincount(day[good], wxh[good], nd) / np.maximum(hd, 1)
    drm = np.bincount(day[good], roomh[good], nd) / np.maximum(hd, 1)
    use = (hd >= 22) & (dwx < 8)
    for F in (25.0, 29.0, 33.0):
        q = kflow(F) * dd[use] / hd[use]  # mean kW
        dtin = drm[use] - dwx[use]
        c = np.polyfit(dtin, q, 1)
        hours[f"{F:.0f}"] = dict(days=int(use.sum()), ua_kw_per_k=round(float(c[0]), 3), intercept_kw=round(float(c[1]), 2))
    res["c_house_daily_heat_vs_indoor_outdoor_dT"] = hours
    # (d) DHW tank: integral of loop delta-T over the run / tank sensor rise = V_tank / F
    ratio = []
    for a0, b0 in runs_of(x.on & (x.st == "HOT WATER")):
        if b0 - a0 < 15 or not x.ok[a0 - 5:b0 + 3].all() or th[a0 - 5:b0].any():
            continue
        I = np.nansum(x.dTt[a0:b0])
        t0_ = np.nanmin(x.d["tank_t"][a0 - 3:a0 + 2])
        t1_ = np.nanmax(x.d["tank_t"][b0 - 2:b0 + 1])
        if np.isfinite(I) and t1_ - t0_ >= 5:
            ratio.append(I / (t1_ - t0_))
    r = float(np.median(ratio))
    res["d_dhw_tank_v_over_f_min"] = dict(n=len(ratio), median=round(r, 2), p25_75=pct(ratio, (25, 75)),
                                          flow_if_tank_l={str(v): round(v / r, 1) for v in (190, 250, 300)})
    OUT["flow"] = res


def fit_cop(x: D, F: float, x_pen: float | None, p0_fixed: float | None = None, thin=3):
    """Fit P = p0 + Q / (eta(T_out) * Carnot(Tc, Te) * exp(-x_pen (T_sup - 30)))."""
    s = np.where(x.steady & np.isfinite(x.wx))[0][::thin]
    dT, tsup, ta, P = x.dTt[s], x.tsup[s], x.wx[s], x.P[s]
    day = x.T[s] // 86400
    _, inv, cnt = np.unique(day, return_inverse=True, return_counts=True)
    w = 1 / np.sqrt(cnt[inv])
    k = kflow(F)

    def model(par):
        eta = np.interp(ta, ETA_KNOTS, par[:10])
        p0 = par[10] if p0_fixed is None else p0_fixed
        xp = par[11] if x_pen is None else x_pen
        Q = k * dT
        tc = tsup + 1.0 + 0.10 * Q
        te = np.minimum(ta - 1.35 - 0.42 * Q, 2.5)
        core = eta * (tc + 273.15) / np.maximum(tc - te, 5.0) * np.exp(-xp * (tsup - 30.0))
        return p0 + Q / core

    r = least_squares(lambda p: (model(p) - P) * w, np.r_[np.full(10, 0.5), 0.3, 0.0],
                      bounds=(np.r_[np.full(10, 0.05), 0.0, -0.05], np.r_[np.full(10, 2.0), 1.0, 0.1]))
    pred = model(r.x)
    return dict(F=F, eta=[round(float(v), 4) for v in r.x[:10]],
                p0=round(float(r.x[10] if p0_fixed is None else p0_fixed), 3),
                x_pen=round(float(r.x[11] if x_pen is None else x_pen), 4),
                rmse_kw=round(float(np.sqrt(np.mean((pred - P) ** 2))), 3), n=len(s))


def empirical_outlet_sensitivity(x: D, F=29.0):
    k = kflow(F)
    Q = k * x.dTt
    g = x.steady & (Q > 2) & (x.wx > -20) & (x.wx < 16)
    out = {}
    rng = np.random.default_rng(0)
    for lo, hi in ((-20, -3), (-3, 3), (3, 6), (6, 16), (-20, 16)):
        s = g & (x.wx >= lo) & (x.wx < hi)
        X = np.c_[np.ones(s.sum()), x.tsup[s], np.log(Q[s]), x.wx[s]]
        y = np.log(Q[s] / x.P[s])
        c, *_ = np.linalg.lstsq(X, y, rcond=None)
        days = (x.T[s] // 86400).astype(int)
        ud = np.unique(days)
        groups = {u: np.where(days == u)[0] for u in ud}
        bs = []
        for _ in range(200):
            idx = np.concatenate([groups[u] for u in rng.choice(ud, len(ud))])
            cc, *_ = np.linalg.lstsq(X[idx], y[idx], rcond=None)
            bs.append(cc[1])
        out[f"wx {lo}..{hi}"] = dict(n=int(s.sum()), days=len(ud), pct_per_K=round(100 * float(c[1]), 2),
                                     ci90=[round(100 * float(np.percentile(bs, 5)), 2), round(100 * float(np.percentile(bs, 95)), 2)],
                                     load_exponent=round(float(c[2]), 2))
    OUT["empirical_outlet_sensitivity"] = out


def startup_cost(x: D, fit):
    """Electricity in the first 20 min of runs vs the steady model at the same measured heat."""
    from lab.sim import unit as U
    p = U.UnitParams(flow_lpm=fit["F"], eta=tuple(fit["eta"]), p0_kw=fit["p0"], x_pen=fit["x_pen"], cop_form="knots")
    k = kflow(fit["F"])
    rows = []
    prev = -999
    for a, b in x.runs:
        if (x.st[a] == "HEAT" and a - prev >= 30 and b - a >= 45 and x.ok[a - 3:a + 45].all()
                and not x.near_df[a:a + 45].any() and np.isfinite(x.P[a - 2:a + 45]).all()
                and np.isfinite(x.dTt[a:a + 46]).all()):
            def excess(lo, hi):
                el = 0.0
                ex = 0.0
                for j in range(a + lo, a + hi):
                    q = k * 0.5 * (x.dTt[j] + x.dTt[j + 1])  # heat over the minute (temps are instants)
                    ts = x.inl[j] + 0.5 * (x.dTt[j] + x.dTt[j + 1])
                    pm = U.p_running(p, ts, x.wx[j], max(q, 0.5)) if q > 0.3 else p.p0_kw
                    el += x.P[j] / 60
                    ex += (x.P[j] - pm) / 60
                return el, ex
            e20, ex20 = excess(0, 20)
            e40, ex40 = excess(20, 45)
            pre = float(x.P[a - 1] - x.P[a - 3]) / 60
            rows.append((ex20, ex40 * 20 / 25, pre, e20))
        prev = b
    R = np.array(rows)
    # electricity after the stop (residual) above idle
    post = []
    for a, b in x.runs:
        if x.st[a] == "HEAT" and b + 6 < x.n and x.ok[b - 1:b + 6].all() and np.isfinite(x.P[b:b + 6]).all() and b - a > 20:
            post.append(float(np.sum(x.P[b:b + 3] - x.P[b + 5])) / 60)
    OUT["startup_cost"] = dict(runs=len(R), excess_kwh_first20_vs_model=pct(R[:, 0], (25, 50, 75)),
                               excess_kwh_min20_45_scaled_to_20=pct(R[:, 1], (25, 50, 75)),
                               prestart_minute_kwh=pct(R[:, 2], (25, 50, 75)), post_stop_kwh=pct(post, (25, 50, 75)))


# ------------------------------------------------------------------------------------------
# 4-5. defrost and hot water
# ------------------------------------------------------------------------------------------

def defrost_stats(x: D, F=29.0):
    k = kflow(F)
    starts = np.where(x.df & ~np.r_[False, x.df[:-1]])[0]
    okm = x.ok & np.isfinite(x.wx)
    freq = []
    edges = [-25, -10, -5, -2, 0, 2, 4, 6, 8, 20]
    for lo, hi in zip(edges[:-1], edges[1:]):
        s = x.on & okm & (x.wx >= lo) & (x.wx < hi)
        n = int(((x.wx[starts] >= lo) & (x.wx[starts] < hi) & x.ok[starts]).sum())
        freq.append(dict(wx=f"{lo}..{hi}", run_h=round(float(s.sum() / 60), 1), defrosts=n,
                         run_h_per_defrost=round(float(s.sum() / 60 / max(n, 1)), 1),
                         rh_mean=round(float(np.nanmean(x.rh[s])), 0)))
    rhb = []
    for rl, rhh in ((0, 80), (80, 90), (90, 95), (95, 101)):
        s = x.on & okm & (x.wx >= -5) & (x.wx < 4) & (x.rh >= rl) & (x.rh < rhh)
        n = int(((x.wx[starts] >= -5) & (x.wx[starts] < 4) & (x.rh[starts] >= rl) & (x.rh[starts] < rhh) & x.ok[starts]).sum())
        rhb.append(dict(rh=f"{rl}-{rhh}", run_h=round(float(s.sum() / 60), 1), defrosts=n, run_h_per_defrost=round(float(s.sum() / 60 / max(n, 1)), 1)))
    ev = []
    for a, b in runs_of(x.df):
        if not x.ok[a - 3:b + 10].all():
            continue
        q = k * (x.out[a:b + 6] - x.inl[a:b + 6] + SENSOR_DT_OFFSET)
        ev.append((b - a, float(np.sum(np.minimum(q, 0)) / 60), float(np.nansum(x.P[a:b]) / 60), float(x.wx[a]),
                   float(np.sum(np.minimum(q[:b - a], 0)) / 60 / max(b - a, 1) * 60 / k)))
    E = np.array(ev)
    per = []
    for lo, hi in ((-25, -5), (-5, 0), (0, 3), (3, 20)):
        s = (E[:, 3] >= lo) & (E[:, 3] < hi)
        per.append(dict(wx=f"{lo}..{hi}", n=int(s.sum()), minutes=pct(E[s, 0], (25, 50, 75)),
                        loop_heat_drawn_kwh=round(float(np.median(E[s, 1])), 3), elec_kwh=round(float(np.median(E[s, 2])), 3),
                        draw_dT_k=round(float(np.median(E[s, 4])), 2)))
    OUT["defrost"] = dict(flow_assumed_lpm=F, frequency=freq, rh_effect_wx_m5_to_4=rhb, per_event=per)


def dhw_stats(x: D):
    rows = []
    for a, b in runs_of(x.on & (x.st == "HOT WATER")):
        if not x.ok[a:b].all():
            continue
        hr_local = ((x.T[a] + 2 * 3600) % 86400) / 3600  # Europe/Vilnius winter time, for the histogram only
        rows.append((b - a, float(np.nansum(x.P[a:b]) / 60), hr_local, float(x.wx[a]), float(x.d["tank_t"][a - 1]),
                     float(np.nanmax(x.d["tank_t"][b - 2:b + 1])), float(np.nanmax(x.P[a:b]))))
    R = np.array(rows)
    prof = []
    for j in range(0, 40, 3):
        vals = []
        for a, b in runs_of(x.on & (x.st == "HOT WATER")):
            if b - a > j and x.ok[a:b].all() and np.isfinite(x.P[a + j]):
                vals.append(x.P[a + j])
        prof.append(dict(minute=j, n=len(vals), p_kw=round(float(np.median(vals)), 2) if vals else None))
    c = np.polyfit(R[:, 3], R[:, 1], 1)
    th = np.nan_to_num(x.d["tank_heater"]) > 0
    heater = [b - a for a, b in runs_of(th)]
    days = (x.T[-1] - x.T[0]) / 86400
    OUT["dhw"] = dict(runs=len(R), minutes=pct(R[:, 0], (10, 25, 50, 75, 90)), elec_kwh=pct(R[:, 1], (10, 50, 90)),
                      elec_kwh_vs_wx=dict(a=round(float(c[1]), 3), b_per_K=round(float(c[0]), 4)),
                      start_hour_local_hist=dict(Counter(int(h) for h in R[:, 2]).most_common()),
                      tank_start_end=[pct(R[:, 4], (50,)), pct(R[:, 5], (50,))], peak_p_kw=pct(R[:, 6], (10, 50, 90)),
                      power_profile=prof, tank_heater_runs=len(heater), tank_heater_minutes=pct(heater, (25, 50, 75)),
                      runs_per_day_heating_seasons=None, window_days=round(days, 1))


def model_numbers():
    """Controller-relevant sensitivities of the fitted model and its variants (no data needed)."""
    from lab.sim import unit as U
    res = {}
    for name, fn in U.VARIANTS.items():
        p = fn()
        r = {}
        for ta in (-7.0, 0.0, 7.0):
            qs = {"min": U.q_min(p, ta), "mid": 6.0, "max": U.q_max(p, ta, 35.0)}
            for lab_, q in qs.items():
                c30 = U.cop_steady(p, 30.0, ta, q)
                c35 = U.cop_steady(p, 35.0, ta, q)
                r[f"{ta:+.0f}C_{lab_}"] = dict(q_kw=round(q, 2), cop_w30=round(c30, 2), cop_w35=round(c35, 2),
                                               pct_per_K_30_31=round(100 * (U.cop_steady(p, 31.0, ta, q) / c30 - 1), 2),
                                               pct_per_K_avg_30_35=round(100 * ((c35 / c30) ** 0.2 - 1), 2))
        res[name] = r
    # datasheet comparison (central): outdoor-unit COP at rated points
    p = U.UnitParams()
    res["datasheet_check_central"] = {
        "A7/W35 9.5kW": round(U.cop_steady(p, 35.0, 7.0, 9.5), 2), "A7/W45 9.5kW": round(U.cop_steady(p, 45.0, 7.0, 9.5), 2),
        "A-7/W35 6.65kW": round(U.cop_steady(p, 35.0, -7.0, 6.65), 2), "A-7/W45 6.65kW": round(U.cop_steady(p, 45.0, -7.0, 6.65), 2),
        "datasheet_outdoor_unit": {"A7/W35": 4.80, "A7/W45": 3.72, "A-7/W35": 2.93, "A-7/W45": 2.29}}
    # start penalty of the dynamic model: a 60-min run vs the same heat at steady state
    pen = {}
    for name in ("central", "high_start_loss"):
        p = U.VARIANTS[name]()
        u = U.VersatiUnit(p)
        e = q = 0.0
        tr = 26.0
        started = False
        for i in range(80):
            r = u.step(31.0, 4, tr, 3.0)
            if r.compressor:
                started = True
            if started:
                e += r.p_outdoor / 60
                q += r.q_loop / 60
            if started and not r.compressor:
                break
            if i > 70:
                break
        steady = q / U.cop_steady(p, tr + 3.0, 3.0, 6.5)
        pen[name] = dict(run_kwh_el=round(e, 3), run_kwh_heat=round(q, 2), steady_equiv_el=round(steady, 3),
                         start_penalty_kwh=round(e - steady, 3))
    res["model_start_penalty_60min_run"] = pen
    # defrost penalty by outdoor temperature (central): extra electricity + loop heat per run hour
    p = U.UnitParams()
    dfp = {}
    for ta, rh in ((-10.0, 88.0), (-3.0, 90.0), (0.0, 90.0), (2.0, 88.0), (4.0, 85.0), (7.0, 82.0)):
        rate_h = U.frost_rate_per_min(p, ta, rh, False) * 60  # defrosts per run hour
        dur = p.defrost_min_cold if ta < 3.0 else p.defrost_min_mild
        q_draw = p.defrost_draw_k * p.k_flow * dur / 60
        el = p.defrost_p_kw * dur / 60
        q_h = 6.0
        cop = U.cop_steady(p, 31.0, ta, q_h)
        n = rate_h
        heat = q_h * (60 - n * dur) / 60 - n * q_draw
        elec = q_h / cop * (60 - n * dur) / 60 + n * el
        dfp[f"{ta:+.0f}C_rh{rh:.0f}"] = dict(defrosts_per_run_h=round(n, 3), cop_steady=round(cop, 2),
                                              cop_with_defrost=round(heat / elec, 2),
                                              penalty_pct=round(100 * (1 - heat / elec / cop), 1))
    res["defrost_penalty_central"] = dfp
    OUT["model_numbers"] = res


# ------------------------------------------------------------------------------------------
# review round 1: smooth COP surface, frost per kWh of air heat, surge vs power, start cost
# ------------------------------------------------------------------------------------------

SMOOTH_TK = np.array([-12.0, -4.0, 2.0, 6.0, 12.0])  # outdoor knots of the output-correction surface
SMOOTH_QK = np.array([3.0, 5.0, 7.0, 9.0, 11.0])     # output knots (kW)
DHW_SUPPLY_C = 45.0  # supply assumed for the air heat of hot-water runs (tank 37 -> 46 degC)


def _smooth5(v):
    from scipy.ndimage import uniform_filter1d
    return uniform_filter1d(np.nan_to_num(v), 5)


def frost_level(x: D, F=29.0):
    """Frost proxy for every minute: the share of the heat drawn from the air (heat - electricity,
    heat runs only) accumulated since the end of the last defrost, relative to the total drawn
    before the next defrost. NaN outside clean inter-defrost intervals."""
    k = kflow(F)
    heat = x.on & (x.st == "HEAT") & ~x.df
    q = np.clip(np.nan_to_num(k * x.dTt), 0, None) * heat
    air = np.clip(q - np.nan_to_num(x.P), 0, None) * heat
    cum = np.cumsum(air)
    starts = np.where(x.df & ~np.r_[False, x.df[:-1]])[0]
    ends = np.where(~x.df & np.r_[False, x.df[:-1]])[0]
    fr = np.full(x.n, np.nan)
    for a, b in zip(starts[:-1], starts[1:]):
        e0 = ends[(ends > a) & (ends < b)]
        if len(e0) == 0:
            continue
        e0 = e0[0]
        if b - e0 > 3 * 1440 or (~x.ok[e0:b]).mean() > 0.03:
            continue
        tot = cum[b - 1] - cum[e0]
        if tot > 1.0:
            fr[e0:b] = (cum[e0:b] - cum[e0]) / tot
    return fr


def smooth_cop_model(par, ta, tsup, Q, frz, xp, tk=SMOOTH_TK, qk=SMOOTH_QK):
    """Electricity of the smooth COP model (vectorised twin of lab/sim/unit.py p_running)."""
    e0, e1, tm, sc, e2, p0, d = par[:7]
    G = np.asarray(par[7:], float).reshape(len(tk), len(qk))
    ti = np.clip(np.searchsorted(tk, ta) - 1, 0, len(tk) - 2)
    qi = np.clip(np.searchsorted(qk, Q) - 1, 0, len(qk) - 2)
    ft = np.clip((ta - tk[ti]) / (tk[ti + 1] - tk[ti]), 0, 1)
    fq = np.clip((Q - qk[qi]) / (qk[qi + 1] - qk[qi]), 0, 1)
    g = (G[ti, qi] * (1 - ft) * (1 - fq) + G[ti + 1, qi] * ft * (1 - fq) + G[ti, qi + 1] * (1 - ft) * fq
         + G[ti + 1, qi + 1] * ft * fq)
    eta = (e0 + e1 * np.tanh((ta - tm) / sc) + e2 * ta) * (1 - d * frz) * np.exp(g)
    tc = tsup + 1.0 + 0.10 * Q
    te = np.minimum(ta - 1.35 - 0.42 * Q, 2.5)
    carnot = (tc + 273.15) / np.maximum(tc - te, 5.0) * np.exp(-xp * (tsup - 30.0))
    return p0 + Q / (eta * carnot)


def fit_cop_smooth(x: D, F: float, xp: float, p0_fixed: float | None = None, surface: bool = True,
                   lam=0.5, lam_t=4.0, fr=None):
    """Smooth COP model (review round 1, replaces the 10-knot Carnot fraction):

        P = p0 + Q / (eta(T) * (1 - d * frost) * exp(G(T, Q)) * Carnot(Tc, Te) * exp(-x (T_sup - 30)))
        eta(T) = e0 + e1 tanh((T - tm) / sc) + e2 T      (smooth, monotone over the data range)

    G is a bilinear correction surface on 5 x 5 knots (outdoor x output), penalised towards zero
    and towards smoothness (strongly along the outdoor axis), so COP can peak at mid output where
    the data say so. `frost` is the frost proxy of frost_level() (0 just after a defrost, 1 just
    before the next). Fitted on 5-minute smoothed steady minutes (less dilution of the output
    axis by sensor noise), weight per day 1/sqrt(minutes)."""
    k = kflow(F)
    from scipy.ndimage import uniform_filter1d
    ok5 = uniform_filter1d(x.steady.astype(float), 5) > 0.99
    s = np.where(x.steady & ok5 & np.isfinite(x.wx))[0]
    Q = k * _smooth5(x.dTt)[s]
    P = _smooth5(x.P)[s]
    ta, tsup = x.wx[s], x.tsup[s]
    if fr is None:
        fr = frost_level(x, F)
    f = fr[s]
    frz = np.where(np.isfinite(f), f, np.where(ta > 5, 0.0, 0.5))
    day = x.T[s] // 86400
    _, inv, cnt = np.unique(day, return_inverse=True, return_counts=True)
    w = 1 / np.sqrt(cnt[inv])
    NG = len(SMOOTH_TK) * len(SMOOTH_QK)

    def resid(par):
        r = (smooth_cop_model(par, ta, tsup, Q, frz, xp) - P) * w
        G = par[7:].reshape(len(SMOOTH_TK), len(SMOOTH_QK))
        sc_ = lam * np.sqrt(len(P)) * np.mean(w) * 0.05
        pen = np.r_[sc_ * lam_t * np.diff(G, 2, axis=0).ravel(), sc_ * np.diff(G, 2, axis=1).ravel(),
                    sc_ * 0.3 * G.ravel()]
        return np.r_[r, pen]

    x0 = np.r_[0.6, 0.1, 4.0, 3.0, 0.005, 0.3, 0.1, np.zeros(NG)]
    lb = np.r_[0.1, 0.0, -5.0, 1.0, -0.02, 0.0, -0.3, np.full(NG, -0.5)]
    ub = np.r_[1.5, 0.6, 10.0, 20.0, 0.03, 1.0, 0.6, np.full(NG, 0.5)]
    if p0_fixed is not None:
        x0[5], lb[5], ub[5] = p0_fixed, p0_fixed - 1e-9, p0_fixed + 1e-9
    if not surface:
        lb[7:], ub[7:] = -1e-12, 1e-12
    r = least_squares(resid, x0, bounds=(lb, ub))
    par = r.x
    pred = smooth_cop_model(par, ta, tsup, Q, frz, xp)
    # residual table (model / measured electricity) by outdoor band x output bin, and q p95 per band
    table = {}
    q95 = {}
    for lo, hi in ((-25, -5), (-5, 0), (0, 3), (3, 6), (6, 9), (9, 20)):
        mb = (ta >= lo) & (ta < hi)
        q95[f"{lo}..{hi}"] = round(float(np.percentile(Q[mb], 95)), 2)
        row = {}
        for a, b in ((0, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9), (9, 10), (10, 13)):
            kk = mb & (Q >= a) & (Q < b)
            if kk.sum() >= 60:
                row[f"{a}-{b}"] = dict(n=int(kk.sum()), cop_meas=round(float(Q[kk].sum() / P[kk].sum()), 2),
                                       ratio=round(float(pred[kk].sum() / P[kk].sum()), 3),
                                       supply_med=round(float(np.median(tsup[kk])), 1))
        table[f"{lo}..{hi}"] = row
    fr_tab = {}
    for lo, hi in ((0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.01)):
        kk = np.isfinite(f) & (f >= lo) & (f < hi)
        fr_tab[f"{lo}-{hi}"] = dict(n=int(kk.sum()), ratio=round(float(pred[kk].sum() / P[kk].sum()), 3))
    return dict(F=F, x_pen=xp, eta=[round(float(v), 5) for v in par[:5]], p0=round(float(par[5]), 4),
                frost_d=round(float(par[6]), 4), G=[[round(float(v), 4) for v in row] for row in
                                                    par[7:].reshape(len(SMOOTH_TK), len(SMOOTH_QK))],
                rmse_kw=round(float(np.sqrt(np.mean((pred - P) ** 2))), 4), n=int(len(s)), residual_ratio=table,
                q_p95_by_band=q95, residual_by_frost=fr_tab)


FROST_Q_EXP = 0.28  # frost per kWh of air heat rises as (Q / 5 kW)^this (fitted below, iterated once)


def _air_heat_minutes(x: D, F=29.0, q_exp=FROST_Q_EXP):
    """kW drawn from the outdoor air per minute, weighted by (Q / 5 kW)^q_exp exactly as the model
    accumulates frost: heat - electricity in heat runs; for hot-water runs (no loop heat measured)
    electricity x (COP - 1) with the central steady COP at a 45 degC supply and 6 kW."""
    from lab.sim import unit as U
    k = kflow(F)
    heat = x.on & (x.st == "HEAT") & ~x.df
    dhw = x.on & (x.st == "HOT WATER")
    P = np.nan_to_num(x.P)
    q = np.clip(np.nan_to_num(k * x.dTt), 0, None)
    air = np.where(heat, np.clip(q - P, 0, None), 0.0)
    p = U.UnitParams()
    ta = np.nan_to_num(x.wx, nan=5.0)
    tgrid = np.arange(-25, 21)
    cop_d = np.array([U.cop_steady(p, DHW_SUPPLY_C, float(t), 6.0) for t in tgrid])
    cd = np.interp(ta, tgrid, cop_d)
    air = np.where(dhw, P * np.clip(cd - 1.0, 0, None), air)
    qq = np.where(dhw, P * cd, q)
    return air * (np.maximum(qq, 1.0) / 5.0) ** q_exp


def defrost_per_kwh(x: D, F=29.0, q_exp=FROST_Q_EXP):
    """Frost per kWh of heat drawn from the air (review round 1, replaces frost per run-minute).

    - kWh of air heat per defrost by outdoor band (defrosts counted by the outdoor temperature at
      the defrost start, air heat by the minute's outdoor temperature; the old run-hour table's
      method);
    - the humidity effect inside -5..+4 degC as a per-%RH gain;
    - an interval check: the 'run hours between defrosts vs mean output' exponent in the data and
      the exponent the per-kWh rule implies."""
    air = _air_heat_minutes(x, F, q_exp)
    air0 = _air_heat_minutes(x, F, 0.0)
    starts = np.where(x.df & ~np.r_[False, x.df[:-1]])[0]
    okm = x.ok & np.isfinite(x.wx)
    edges = [-25, -10, -5, -2, 0, 2, 4, 6, 8, 20]
    tab = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        s = okm & (x.wx >= lo) & (x.wx < hi)
        n = int(((x.wx[starts] >= lo) & (x.wx[starts] < hi) & x.ok[starts]).sum())
        kwh = float(air[s].sum() / 60)
        tab.append(dict(wx=f"{lo}..{hi}", air_kwh=round(kwh, 1), defrosts=n, kwh_per_defrost=round(kwh / max(n, 1), 1),
                        rh_mean=round(float(np.nanmean(x.rh[s & (air > 0)])), 0)))
    rhb = []
    for rl, rhh in ((0, 80), (80, 90), (90, 95), (95, 101)):
        s = okm & (x.wx >= -5) & (x.wx < 4) & (x.rh >= rl) & (x.rh < rhh)
        n = int(((x.wx[starts] >= -5) & (x.wx[starts] < 4) & (x.rh[starts] >= rl) & (x.rh[starts] < rhh)
                 & x.ok[starts]).sum())
        kwh = float(air[s].sum() / 60)
        rhb.append(dict(rh=f"{rl}-{rhh}", rh_mean=round(float(np.nanmean(x.rh[s & (air > 0)])), 1), air_kwh=round(kwh, 1),
                        defrosts=n, kwh_per_defrost=round(kwh / max(n, 1), 1)))
    # gain: rate ~ 1 + g (RH - 87) fitted on the four RH bins (weighted by defrost counts)
    rr = np.array([b["rh_mean"] for b in rhb]) - 87.0
    rate = np.array([b["defrosts"] / max(b["air_kwh"], 1e-9) for b in rhb])
    wts = np.array([b["defrosts"] for b in rhb], float)
    A = np.c_[np.ones(4), rr] * np.sqrt(wts)[:, None]
    c = np.linalg.lstsq(A, rate * np.sqrt(wts), rcond=None)[0]
    gain = float(c[1] / c[0])
    # intervals between defrosts: run hours and mean output; exponent of run hours on output
    k = kflow(F)
    heat = x.on & (x.st == "HEAT")
    q = np.clip(np.nan_to_num(k * x.dTt), 0, None)
    rows = []
    for a, b in zip(starts[:-1], starts[1:]):
        seg = slice(a + 8, b)
        if (~x.ok[seg]).mean() > 0.03:
            continue
        run = heat[seg] & ~x.df[seg]
        dh = (x.st[seg] == "HOT WATER") & x.on[seg]
        rmin = run.sum() + dh.sum()
        if rmin < 20 or (b - a) > 3 * 1440:
            continue
        rows.append((rmin / 60, float(air0[seg].sum() / 60), float(np.nanmean(x.wx[seg][run])) if run.any() else np.nan,
                     float(np.nanmean(x.rh[seg][run])) if run.any() else np.nan, float(q[seg][run].mean()) if run.any() else np.nan))
    R = np.array(rows)
    R = R[np.isfinite(R).all(1)]
    sel = (R[:, 2] > -8) & (R[:, 2] < 5)
    X_ = np.c_[np.ones(sel.sum()), np.log(R[sel, 4]), R[sel, 2], R[sel, 3]]
    cc = np.linalg.lstsq(X_, np.log(R[sel, 0]), rcond=None)[0]
    cc2 = np.linalg.lstsq(X_, np.log(R[sel, 1]), rcond=None)[0]
    OUT["defrost_per_kwh"] = dict(air_heat_note="heat - electricity in heat runs; DHW: electricity x (COP45 - 1); "
                                  f"weighted by (Q / 5 kW)^{q_exp} in the table",
                                  by_outdoor=tab, rh_bins=rhb, rh_gain_per_pct=round(gain, 4),
                                  intervals=int(len(R)), intervals_fit=int(sel.sum()),
                                  exp_run_hours_on_output=round(float(cc[1]), 2),
                                  exp_air_kwh_per_defrost_on_output=round(float(cc2[1]), 2),
                                  median_air_kwh_per_interval=round(float(np.median(R[sel, 1])), 1))


def surge_vs_power(x: D):
    """Surge probability at the 120-minute marks against the mean electricity of the 30 minutes
    before the mark, and jointly with the outdoor temperature (logistic fit)."""
    res = []
    for a, b in x.runs:
        if x.st[a] != "HEAT":
            continue
        for mark in (120, 240, 360, 480, 600):
            if b - a < mark - 2:
                break
            s = a + mark
            if (not x.ok[s - 30:s + 10].all() or x.df[s - 15:min(b, s + 10)].any()
                    or (x.sp[s - 15:min(b + 1, s + 10)] != x.sp[s - 15]).any()):
                continue
            p0 = float(np.nanmean(x.P[s - 30:s - 4]))
            pmax = float(np.nanmax(x.P[s - 4:min(b, s + 8)]))
            res.append((p0, pmax - p0 > 0.4, float(x.wx[s])))
    R = np.array(res, float)
    R = R[np.isfinite(R).all(1)]
    tab = []
    for lo, hi in ((0, 0.9), (0.9, 1.1), (1.1, 1.3), (1.3, 1.6), (1.6, 9)):
        m = (R[:, 0] >= lo) & (R[:, 0] < hi)
        tab.append(dict(p_kw=f"{lo}-{hi}", n=int(m.sum()), rate=round(float(R[m, 1].mean()), 3) if m.any() else None,
                        p_mean=round(float(R[m, 0].mean()), 3) if m.any() else None))
    from scipy.optimize import minimize

    def nll(c, X, y):
        z = X @ c
        return float(np.sum(np.logaddexp(0, z) - y * z))
    y = R[:, 1]
    X1 = np.c_[np.ones(len(R)), R[:, 0]]
    X2 = np.c_[np.ones(len(R)), R[:, 0], R[:, 2]]
    X3 = np.c_[np.ones(len(R)), R[:, 2]]
    f1 = minimize(nll, np.zeros(2), args=(X1, y))
    f2 = minimize(nll, np.zeros(3), args=(X2, y))
    f3 = minimize(nll, np.zeros(2), args=(X3, y))
    OUT["surge_vs_power"] = dict(marks=len(R), by_power=tab,
                                 logit_power=dict(coef=[round(float(v), 3) for v in f1.x], nll=round(f1.fun, 2)),
                                 logit_power_outdoor=dict(coef=[round(float(v), 3) for v in f2.x], nll=round(f2.fun, 2)),
                                 logit_outdoor=dict(coef=[round(float(v), 3) for v in f3.x], nll=round(f3.fun, 2)))


def start_cost_vs_off(x: D):
    """Electricity of the first 20 minutes of runs above the steady model at the same heat, by the
    length of the preceding off period (M1 of review round 1)."""
    from lab.sim import unit as U
    p = U.UnitParams()
    k = kflow(p.flow_lpm)
    rows = []
    prev_end = None
    for a, b in x.runs:
        gap = (a - prev_end) if prev_end is not None else None
        prev_end = b
        if gap is None or x.st[a] != "HEAT" or b - a < 25 or not x.ok[a - 3:a + 25].all():
            continue
        if x.near_df[a:a + 25].any() or not np.isfinite(x.P[a - 2:a + 25]).all() or not np.isfinite(x.dTt[a:a + 26]).all():
            continue
        if not x.ok[a - min(gap, 60):a].all():
            continue
        if (x.st[max(0, a - gap):a] == "HOT WATER").any():
            continue
        el = ex = 0.0
        for j in range(a, a + 20):
            q = k * 0.5 * (x.dTt[j] + x.dTt[j + 1])
            ts = x.inl[j] + 0.5 * (x.dTt[j] + x.dTt[j + 1])
            pm = U.p_running(p, ts, x.wx[j], max(q, 0.5)) if q > 0.3 else p.p0_kw
            el += x.P[j] / 60
            ex += (x.P[j] - pm) / 60
        rows.append((gap, ex))
    R = np.array(rows)
    tab = []
    for lo, hi in ((0, 15), (15, 30), (30, 60), (60, 120), (120, 240), (240, 100000)):
        m = (R[:, 0] >= lo) & (R[:, 0] < hi)
        if m.any():
            tab.append(dict(off_min=f"{lo}-{hi}", n=int(m.sum()), excess_kwh_p25_50_75=pct(R[m, 1], (25, 50, 75)),
                            mean=round(float(R[m, 1].mean()), 3)))
    OUT["start_cost_vs_off"] = dict(runs=int(len(R)), by_off_minutes=tab,
                                    shortest_off_min=int(R[:, 0].min()) if len(R) else None)


# ------------------------------------------------------------------------------------------
# review round 2: frost removed while the compressor is off (N1), part-load bounds (N3)
# ------------------------------------------------------------------------------------------

FROST_TK = (-15.0, -7.0, -3.0, -1.0, 1.0, 3.0, 5.0, 8.0)  # knots of log K(T); no frost above +10 degC
FROST_OFF_C = 10.0
FROST_TAU_MIN = 15.0


def frost_segments(x: D):
    """Inter-defrost segments over the whole record: (start, end, event). A segment starts at the
    end of a defrost (or after a data gap of >= 30 min) and ends at the next defrost start (event)
    or at the next gap (right-censored: frost never reached the trigger). Segments with < 20 run
    minutes or > 3 % missing data are dropped."""
    good = x.ok & (x.comp != -1) & np.isfinite(x.wx)
    dstart = np.flatnonzero(x.df & ~np.r_[False, x.df[:-1]])
    dend = np.flatnonzero(~x.df & np.r_[False, x.df[:-1]])
    gaps = [(a, b) for a, b in runs_of(~good) if b - a >= 30]
    gap_end = dict(gaps)
    bounds = sorted([(int(e), "d") for e in dstart] + [(int(a), "g") for a, _ in gaps])
    start = int(np.argmax(good))
    out = []
    for p, kind in bounds:
        if p <= start:
            if kind == "g":
                start = max(start, gap_end[p])
            else:
                de = dend[dend > p]
                start = max(start, int(de[0]) if len(de) else x.n)
            continue
        if kind == "d":
            if x.on[start:p].sum() >= 20 and (~good[start:p]).mean() < 0.03:
                out.append((start, p, True))
            de = dend[dend > p]
            start = int(de[0]) if len(de) else x.n
        else:
            if x.on[start:p].sum() >= 20:
                out.append((start, p, False))
            start = gap_end[p]
    return out


class _FrostData:
    """Minute inputs of the frost fit, laid out as on/off blocks per segment."""

    def __init__(self, x: D, segs):
        good = x.ok & (x.comp != -1)
        self.segs = segs
        self.ev = np.array([e for _, _, e in segs])
        idx = np.concatenate([np.arange(a, b) for a, b, _ in segs])
        sid = np.concatenate([np.full(b - a, i) for i, (a, b, _) in enumerate(segs)])
        self.idx, self.sid = idx, sid
        self.T = np.nan_to_num(x.wx, nan=5.0)[idx]
        self.RH = np.nan_to_num(x.rh, nan=85.0)[idx]
        self.on = (x.on & good)[idx]
        self.air = _air_heat_minutes(x)[idx]  # (Q - P) x (Q / 5 kW)^0.28, kW
        chg = np.r_[True, (self.on[1:] != self.on[:-1]) | (sid[1:] != sid[:-1])]
        self.bs = np.flatnonzero(chg)
        self.b_on = self.on[self.bs]
        self.b_sid = sid[self.bs]
        self.blen = np.diff(np.r_[self.bs, len(idx)])
        self.t_run = np.array([np.mean(x.wx[a:b][x.on[a:b]]) for a, b, _ in segs])
        self.idle_warm = np.array([int((~x.on[a:b] & (x.wx[a:b] > 1.0)).sum()) for a, b, _ in segs])
        a0 = _air_heat_minutes(x, q_exp=0.0)
        self.air_kwh = np.array([float(np.sum(a0[a:b]) / 60) for a, b, _ in segs])

    def paths(self, logk, g, rmax, tau=FROST_TAU_MIN, per_minute=False):
        """Frost at the end of every segment and its maximum; optionally the per-minute path.
        Running minute: f += air / 60 / K(T) x max(0.3, 1 + g (RH - 87)); off block of L minutes:
        f *= 1 - rmax (1 - exp(-L / tau))."""
        acc = (self.air / 60.0 * np.maximum(0.3, 1.0 + g * (self.RH - 87.0))
               * np.exp(-np.interp(self.T, FROST_TK, logk)) * (self.T < FROST_OFF_C))
        keep = 1.0 - rmax * (1.0 - np.exp(-self.blen / tau))
        A = np.add.reduceat(acc, self.bs)
        n = len(self.segs)
        fe, fm = np.zeros(n), np.zeros(n)
        f, s, mx = 0.0, self.b_sid[0], 0.0
        path = np.zeros(len(self.idx)) if per_minute else None
        for j in range(len(self.bs)):
            if self.b_sid[j] != s:
                f, s, mx = 0.0, self.b_sid[j], 0.0
            if per_minute:
                k0, k1 = self.bs[j], self.bs[j] + self.blen[j]
                if self.b_on[j]:
                    path[k0:k1] = f + np.cumsum(acc[k0:k1])
                else:
                    path[k0:k1] = f * (1.0 - rmax * (1.0 - np.exp(-np.arange(1, k1 - k0 + 1) / tau)))
            if self.b_on[j]:
                f += A[j]
                mx = max(mx, f)
            else:
                f *= keep[j]
            fe[s], fm[s] = f, mx
        return (fe, fm, path) if per_minute else (fe, fm)


def _frost_nll(p, fd: _FrostData, rmax, tau):
    """Lognormal trigger: log(frost at a defrost) ~ N(0, sigma); a censored segment contributes
    P(trigger > its maximum frost)."""
    from scipy.stats import norm
    nk = len(FROST_TK)
    lk, g, sg = p[:nk], p[nk], math.exp(p[nk + 1])
    fe, fm = fd.paths(lk, g, rmax, tau)
    le = np.log(np.maximum(fe[fd.ev], 1e-4))
    ll = np.sum(-math.log(sg) - 0.5 * (le / sg) ** 2)
    ll += np.sum(norm.logsf(np.log(np.maximum(fm[~fd.ev], 1e-6)) / sg))
    return -float(ll)


def _frost_fit_given(fd, rmax, tau, x0):
    from scipy.optimize import minimize
    r = minimize(_frost_nll, x0, args=(fd, rmax, tau), method="Powell",
                 options=dict(maxiter=40000, xtol=1e-4, ftol=1e-7))
    r = minimize(_frost_nll, r.x, args=(fd, rmax, tau), method="Nelder-Mead",
                 options=dict(maxiter=40000, xatol=1e-4, fatol=1e-7))
    return r.x, float(r.fun)


def _frost_classes(fd, fe):
    """Median frost at the defrost by running-mean outdoor band, for intervals with < 2 h and
    >= 4 h of idle above +1 degC (the review-round-2 classes; 1.0 = unbiased)."""
    out = {}
    for lo, hi in ((-20, -2), (-2, 1), (1, 3), (3, 6), (6, 12)):
        s = fd.ev & (fd.t_run >= lo) & (fd.t_run < hi)
        sh, lg = s & (fd.idle_warm < 120), s & (fd.idle_warm >= 240)
        out[f"{lo}..{hi}"] = dict(short_idle=round(float(np.median(fe[sh])), 2) if sh.any() else None, n_short=int(sh.sum()),
                                  long_idle=round(float(np.median(fe[lg])), 2) if lg.any() else None, n_long=int(lg.sum()),
                                  air_kwh_short=round(float(np.median(fd.air_kwh[sh])), 1) if sh.any() else None,
                                  air_kwh_long=round(float(np.median(fd.air_kwh[lg])), 1) if lg.any() else None)
    return out


FROST_RMAX_GRID = (0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.75)
FROST_MIN_INTERVAL_RUN_MIN = 50  # no defrost before 50 run minutes since the last one (data: 5th pct 52, min 32)


class _FirstPassage:
    """Event simulation of the defrost trigger on the recorded running pattern: from the end of
    each recorded defrost, accumulate the frost state minute by minute (removal while off) and
    find where the model would defrost (state >= 1, run age >= 10 min, >= 50 run minutes since the
    last defrost). Compared with where the unit did, in kWh of air heat drawn."""

    def __init__(self, x: D, fd: _FrostData):
        self.fd = fd
        self.age = x.age[fd.idx]
        nb = len(fd.bs)
        self.bend = fd.bs + fd.blen
        self.first = np.r_[True, fd.b_sid[1:] != fd.b_sid[:-1]]
        a0 = _air_heat_minutes(x, q_exp=0.0)[fd.idx]
        self.CA = np.r_[0.0, np.cumsum(a0) / 60.0]
        self.CR = np.r_[0.0, np.cumsum(fd.on.astype(float))]
        counts = np.bincount(fd.sid, minlength=len(fd.segs))
        self.s0 = np.r_[0, np.cumsum(counts)[:-1]]
        self.s1 = self.s0 + counts
        self.air_rec = self.CA[self.s1] - self.CA[self.s0]
        self.nb = nb

    def run(self, lk, g, rmax, tau=FROST_TAU_MIN):
        fd = self.fd
        acc = (fd.air / 60.0 * np.maximum(0.3, 1.0 + g * (fd.RH - 87.0)) * np.exp(-np.interp(fd.T, FROST_TK, lk))
               * (fd.T < FROST_OFF_C))
        C = np.r_[0.0, np.cumsum(acc)]
        keep = 1.0 - rmax * (1.0 - np.exp(-fd.blen / tau))
        trig = np.full(len(fd.segs), -1)
        fend = np.zeros(len(fd.segs))
        f, s, done = 0.0, -1, False
        for j in range(self.nb):
            if self.first[j]:
                f, s, done = 0.0, fd.b_sid[j], False
            if done:
                continue
            k0, k1 = fd.bs[j], self.bend[j]
            if fd.b_on[j]:
                fe = f + C[k1] - C[k0]
                if fe >= 1.0:
                    kk = k0 + int(np.searchsorted(C[k0 + 1:k1 + 1] - C[k0] + f, 1.0))
                    rs = self.CR[self.s0[s]]
                    while kk < k1 and (self.age[kk] < 10 or self.CR[kk + 1] - rs < FROST_MIN_INTERVAL_RUN_MIN):
                        kk += 1
                    if kk < k1:
                        trig[s] = kk
                        done = True
                        continue
                f = fe
            else:
                f *= keep[j]
            fend[s] = f
        return trig, fend

    def resid(self, p, rmax):
        """log(model / recorded) kWh of air heat to the defrost. A segment the model never ends is
        extrapolated as recorded / final state; a censored segment counts only if the model
        defrosts inside it."""
        trig, fend = self.run(p[:8], p[8], rmax)
        air_sim = np.where(trig >= 0, self.CA[np.maximum(trig, 0) + 1] - self.CA[self.s0],
                           self.air_rec / np.maximum(fend, 0.05))
        r = np.log(np.maximum(air_sim, 0.05) / np.maximum(self.air_rec, 0.05))
        ev = self.fd.ev
        return np.where(ev, r, np.minimum(r, 0.0)), trig, fend

    def loss(self, p, rmax):
        return float(np.sum(self.resid(p, rmax)[0] ** 2))


def _fp_fit(fp, rmax, starts):
    from scipy.optimize import minimize
    best = None
    for x0 in starts:
        r = minimize(fp.loss, x0, args=(rmax,), method="Powell", options=dict(maxiter=20000, xtol=1e-3, ftol=1e-6))
        r = minimize(fp.loss, r.x, args=(rmax,), method="Nelder-Mead", options=dict(maxiter=8000, xatol=1e-3, fatol=1e-6))
        if best is None or r.fun < best.fun:
            best = r
    return best.x, float(best.fun)


def frost_stop_fit(x: D):
    """Review round 2 (N1): joint fit of K(T) (kWh of air heat per defrost), the humidity gain
    and the share of the defrost-trigger state lost while the compressor is off: an off block of
    L minutes keeps 1 - rmax (1 - exp(-L / 15 min)). Fitted by event simulation (first passage) on
    every inter-defrost segment of the record, profiled over rmax; the endpoint likelihood (frost
    at the recorded defrost ~ lognormal around 1, censored segments included) is reported too."""
    segs = frost_segments(x)
    fd = _FrostData(x, segs)
    fp = _FirstPassage(x, fd)
    starts = [np.r_[np.log([9.0, 7.5, 7.6, 7.5, 10.5, 18.0, 25.0, 23.0]), 0.0],
              np.r_[np.log([12, 11, 11, 12, 15, 30, 40, 60.0]), 0.01],
              np.r_[np.log([8.7, 8.0, 7.0, 7.9, 8.9, 12.1, 12.3, 9.0]), 0.01]]
    fits = {}
    for rm in FROST_RMAX_GRID:
        p, loss = _fp_fit(fp, rm, starts)
        starts = [p] + starts[1:]
        r, trig, fend = fp.resid(p, rm)
        fe_equiv = np.exp(-r)  # recorded / model air to the defrost: 1 = on time, > 1 = model late
        nll_end = _frost_nll(np.r_[p, math.log(0.45)], fd, rm, FROST_TAU_MIN)
        fits[rm] = dict(rmax=rm, loss=round(loss, 2), sd_log=round(float(np.std(r[fd.ev])), 3),
                        K=[round(float(v), 2) for v in np.exp(p[:8])], rh_gain=round(float(p[8]), 4),
                        early_in_censored=int((trig[~fd.ev] >= 0).sum()), endpoint_nll=round(nll_end, 1),
                        classes=_frost_classes(fd, fe_equiv), par=[float(v) for v in p])
        print(f"frost rmax {rm}: loss {loss:.2f} K {np.round(np.exp(p[:8]), 1)} g {p[8]:.4f}", flush=True)
    best = min(fits.values(), key=lambda f: f["loss"])
    sig2 = best["sd_log"] ** 2
    OUT["frost_stop_fit"] = dict(
        method="first passage on the recorded running pattern, squared log ratio of air heat to the defrost",
        segments=len(segs), events=int(fd.ev.sum()), censored=int((~fd.ev).sum()), tau_min=FROST_TAU_MIN,
        min_interval_run_min=FROST_MIN_INTERVAL_RUN_MIN, knots_c=list(FROST_TK), off_above_c=FROST_OFF_C,
        profile={str(k): {kk: vv for kk, vv in v.items() if kk != "par"} for k, v in fits.items()},
        best_rmax=best["rmax"],
        delta_loss_90pct=round(2.71 * sig2, 2),
        note="classes: median recorded/model air heat to the defrost (1 = unbiased) by idle class")
    return fits, fd


FROST_COUNT_BANDS = (-30.0, -8.0, -4.0, -2.0, 0.0, 2.0, 4.0, 6.0, 12.0)


class _FrostCounts:
    """Event simulation over every clean stretch of the record (gaps >= 30 min split it): the
    model's frost state on the recorded running pattern, reset only where the MODEL defrosts.
    Defrosts are counted by outdoor band (ERA5 at the defrost) and by class: whether an off block
    of >= 4 h ended within the 12 h before (the on/off regime the second review singled out).
    Recorded defrosts are classified the same way, independently of the model."""

    def __init__(self, x: D):
        good = x.ok & (x.comp != -1) & np.isfinite(x.wx)
        stretch = np.ones(x.n, bool)
        for a, b in runs_of(~good):
            if b - a >= 30:
                stretch[a:b] = False
        idx = np.flatnonzero(stretch)
        sid = np.cumsum(np.r_[True, np.diff(idx) > 1]) - 1
        on = (x.on & good)[idx] & ~x.df[idx]
        self.T = np.nan_to_num(x.wx, nan=5.0)[idx]
        self.RH = np.nan_to_num(x.rh, nan=85.0)[idx]
        self.air = _air_heat_minutes(x)[idx]
        self.age = x.age[idx]
        self.on = on
        off = ~x.on[idx]
        last_long = np.full(len(idx), -10 ** 9)
        for a, b in runs_of(off):
            if b - a >= 240:
                last_long[b:] = np.maximum(last_long[b:], b)
        self.cls = (np.arange(len(idx)) - last_long) <= 720
        dst = np.flatnonzero((x.df & ~np.r_[False, x.df[:-1]])[idx])
        self.nc = (len(FROST_COUNT_BANDS) - 1) * 2
        self.n_rec = np.zeros(self.nc)
        for k in dst:
            self.n_rec[self._cell(k)] += 1
        chg = np.r_[True, (on[1:] != on[:-1]) | (sid[1:] != sid[:-1])]
        self.bs = np.flatnonzero(chg)
        self.bl = np.diff(np.r_[self.bs, len(idx)])
        self.be = self.bs + self.bl
        self.b_on = on[self.bs]
        self.first = np.r_[True, sid[self.bs][1:] != sid[self.bs][:-1]]
        self.CR = np.r_[0.0, np.cumsum(on.astype(float))]

    def _cell(self, k):
        b = int(np.clip(np.searchsorted(FROST_COUNT_BANDS, self.T[k]) - 1, 0, len(FROST_COUNT_BANDS) - 2))
        return 2 * b + int(self.cls[k])

    def events(self, lk, g, rmax, tau=FROST_TAU_MIN):
        acc = (self.air / 60.0 * np.maximum(0.3, 1 + g * (self.RH - 87.0)) * np.exp(-np.interp(self.T, FROST_TK, lk))
               * (self.T < FROST_OFF_C) * self.on)
        C = np.r_[0.0, np.cumsum(acc)]
        keep = 1.0 - rmax * (1.0 - np.exp(-self.bl / tau))
        n = np.zeros(self.nc)
        f, last_cr = 0.0, -1e9
        for j in range(len(self.bs)):
            if self.first[j]:
                f, last_cr = 0.0, -1e9
            k0, k1 = self.bs[j], self.be[j]
            if self.b_on[j]:
                base = C[k0] - f
                while C[k1] - base >= 1.0:
                    kk = k0 + int(np.searchsorted(C[k0 + 1:k1 + 1] - base, 1.0))
                    while kk < k1 and (self.age[kk] < 10 or self.CR[kk + 1] - last_cr < FROST_MIN_INTERVAL_RUN_MIN):
                        kk += 1
                    if kk >= k1:
                        break
                    n[self._cell(kk)] += 1
                    last_cr = self.CR[kk + 1]
                    base, k0 = C[kk + 1], kk + 1
                    if k0 >= k1:
                        break
                f = C[k1] - base
            else:
                f *= keep[j]
        return n

    def deviance(self, n):
        n = np.maximum(n, 1e-3)
        r = self.n_rec
        return float(2 * np.sum(np.where(r > 0, r * np.log(np.maximum(r, 1e-9) / n), 0.0) - (r - n)))


def frost_count_fit(x: D, fp_fits: dict, smooth=4.0):
    """Review round 2 (N1), second step: at each removal share rmax of the first-passage profile,
    set the level of K(T) so that the model's defrosts on the recorded running pattern match the
    recorded counts by outdoor band and on/off class (Poisson deviance + a smoothness penalty on
    log K; humidity gain 0, as the first-passage fit found). The first-passage fit decides rmax
    (timing); this one makes the counts, which carry the energy, right."""
    from scipy.optimize import minimize
    fc = _FrostCounts(x)
    out = {}
    for rm, fit in fp_fits.items():
        st = np.log(np.asarray(fit["K"], float))

        def obj(p):
            return fc.deviance(fc.events(p, 0.0, rm)) + smooth * float(np.sum(np.diff(p, 2) ** 2))

        best = None
        for s0 in (st, st + 0.3):
            r = minimize(obj, s0, method="Powell", options=dict(maxiter=20000, xtol=1e-3, ftol=1e-6))
            r = minimize(obj, r.x, method="Nelder-Mead", options=dict(maxiter=6000, xatol=1e-3, fatol=1e-6))
            if best is None or r.fun < best.fun:
                best = r
        n = fc.events(best.x, 0.0, rm)
        out[rm] = dict(rmax=rm, K=[round(float(v), 2) for v in np.exp(best.x)], deviance=round(fc.deviance(n), 2),
                       total_model=int(n.sum()), total_recorded=int(fc.n_rec.sum()),
                       cells_model=n.reshape(-1, 2).astype(int).tolist(),
                       cells_recorded=fc.n_rec.reshape(-1, 2).astype(int).tolist())
        print(f"frost counts rmax {rm}: deviance {out[rm]['deviance']} K {out[rm]['K']}", flush=True)
    OUT["frost_count_fit"] = dict(bands_c=list(FROST_COUNT_BANDS), cells="[band][no long idle, long idle within 12 h]",
                                  smooth=smooth, fits={str(k): v for k, v in out.items()})
    return out


def frost_level_model(x: D, fit, fd=None):
    """Frost proxy for the COP fit from the fitted frost model: the model's frost path through
    every event segment, divided by its value at the defrost (0 after a defrost, 1 at the next).
    NaN outside event segments."""
    fd = fd or _FrostData(x, frost_segments(x))
    p = fit["par"]
    fe, _, path = fd.paths(p[:8], p[8], fit["rmax"], per_minute=True)
    fr = np.full(x.n, np.nan)
    for i, (a, b, ev) in enumerate(fd.segs):
        if ev and fe[i] > 1e-6:
            sel = fd.sid == i
            fr[fd.idx[sel]] = np.minimum(path[sel] / fe[i], 1.5)
    return fr


def partload_fit(x: D, base: dict, scale: float, fr, F=29.0, xp=0.015, fix_p0=False):
    """Review round 2 (N3): the output-dependence of the central G surface scaled by `scale`
    (relative to its value at 5 kW per outdoor knot), held fixed, with eta, p0 and d refitted
    (p0 also fixed when fix_p0). Bounds the part-load slope of COP."""
    G = np.asarray(base["G"], float)
    j5 = list(SMOOTH_QK).index(5.0)
    Gs = G[:, [j5]] + scale * (G - G[:, [j5]])
    k = kflow(F)
    from scipy.ndimage import uniform_filter1d
    ok5 = uniform_filter1d(x.steady.astype(float), 5) > 0.99
    s = np.where(x.steady & ok5 & np.isfinite(x.wx))[0]
    Q = k * _smooth5(x.dTt)[s]
    P = _smooth5(x.P)[s]
    ta, tsup = x.wx[s], x.tsup[s]
    f = fr[s]
    frz = np.where(np.isfinite(f), f, np.where(ta > 5, 0.0, 0.5))
    day = x.T[s] // 86400
    _, inv, cnt = np.unique(day, return_inverse=True, return_counts=True)
    w = 1 / np.sqrt(cnt[inv])
    p0c = base["p0"]

    def full(par):
        p0 = p0c if fix_p0 else par[5]
        return np.r_[par[:5], p0, par[-1], Gs.ravel()]

    def resid(par):
        return (smooth_cop_model(full(par), ta, tsup, Q, frz, xp) - P) * w

    x0 = np.r_[base["eta"], p0c, base["frost_d"]] if not fix_p0 else np.r_[base["eta"], base["frost_d"]]
    if fix_p0:
        def resid(par):  # noqa: F811
            return (smooth_cop_model(full(np.r_[par[:5], 0.0, par[5]]), ta, tsup, Q, frz, xp) - P) * w
        lb, ub = np.r_[0.1, 0.0, -5.0, 1.0, -0.02, -0.3], np.r_[1.5, 0.6, 10.0, 20.0, 0.03, 0.6]
    else:
        lb, ub = np.r_[0.1, 0.0, -5.0, 1.0, -0.02, 0.0, -0.3], np.r_[1.5, 0.6, 10.0, 20.0, 0.03, 1.0, 0.6]
    r = least_squares(resid, x0, bounds=(lb, ub))
    par = r.x
    eta = par[:5]
    p0 = p0c if fix_p0 else par[5]
    d = par[-1]
    pred = smooth_cop_model(np.r_[eta, p0, d, Gs.ravel()], ta, tsup, Q, frz, xp)
    table = {}
    for lo, hi in ((-25, -5), (-5, 0), (0, 3), (3, 6), (6, 9), (9, 20)):
        mb = (ta >= lo) & (ta < hi)
        row = {}
        for a, b in ((3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 10), (10, 13)):
            kk = mb & (Q >= a) & (Q < b)
            if kk.sum() >= 60:
                row[f"{a}-{b}"] = round(float(pred[kk].sum() / P[kk].sum()), 3)
        table[f"{lo}..{hi}"] = row
    return dict(scale=scale, fix_p0=fix_p0, eta=[round(float(v), 5) for v in eta], p0=round(float(p0), 4),
                frost_d=round(float(d), 4), G=[[round(float(v), 4) for v in row] for row in Gs],
                rmse_kw=round(float(np.sqrt(np.mean((pred - P) ** 2))), 4), residual_ratio=table)


def _merge_out():
    path = RESULTS / "unit" / "analysis.json"
    old = json.loads(path.read_text()) if path.exists() else {}
    old.update(json.loads(json.dumps(OUT, default=float)))
    path.write_text(json.dumps(old, indent=1, default=float))


def review2_main(parts=("frost", "cop")):
    """Review-round-2 analyses: the frost-removal fit and its profile (`frost`); the COP's
    coil-frost proxy check and the part-load bounds (`cop`). Merges into analysis.json."""
    x = D()
    if "frost" in parts:
        fits, fd = frost_stop_fit(x)
        _merge_out()
        print(json.dumps(OUT["frost_stop_fit"], default=float))
        frost_count_fit(x, {rm: fits[rm] for rm in (0.0, 0.2, 0.4, 0.6) if rm in fits})
        _merge_out()
    if "cop" in parts:
        fr_old = frost_level(x)
        cop = {"old_proxy": fit_cop_smooth(x, 29.0, 0.015, fr=fr_old)}
        prof = json.loads((RESULTS / "unit" / "analysis.json").read_text()).get("frost_stop_fit", {}).get("profile", {})
        if "frost" in parts:
            best = min(fits.values(), key=lambda f: f["loss"])
            fr_new = frost_level_model(x, best, fd)
            cop["trigger_proxy"] = fit_cop_smooth(x, 29.0, 0.015, fr=fr_new)
        del prof
        for k_, v in cop.items():
            print("COP frost proxy", k_, v["rmse_kw"], "d", v["frost_d"], flush=True)
        OUT["cop_frost_proxy_r2"] = {k_: dict(rmse_kw=v["rmse_kw"], frost_d=v["frost_d"],
                                              residual_by_frost=v["residual_by_frost"]) for k_, v in cop.items()}
        pl = {"central": dict(scale=1.0, rmse_kw=cop["old_proxy"]["rmse_kw"], eta=cop["old_proxy"]["eta"],
                              p0=cop["old_proxy"]["p0"], frost_d=cop["old_proxy"]["frost_d"])}
        for sc in (0.5, 1.5):
            for fp_ in (False, True):
                key = f"partload_x{sc}" + ("_p0fixed" if fp_ else "")
                pl[key] = partload_fit(x, cop["old_proxy"], sc, fr_old, fix_p0=fp_)
                print(key, pl[key]["rmse_kw"], pl[key]["eta"], pl[key]["p0"], pl[key]["frost_d"], flush=True)
        OUT["partload_fits"] = pl
        _merge_out()


REVIEW_FITS = ((29.0, 0.015, None, True, "F29_x0.015"), (25.0, 0.015, None, True, "F25_x0.015"),
               (33.0, 0.015, None, True, "F33_x0.015"), (29.0, 0.0, None, True, "F29_x0.0"),
               (29.0, 0.03, None, True, "F29_x0.03"), (29.0, 0.015, 0.15, False, "F29_x0.015_flat"))


def review_main():
    """Only the review-round-1 analyses (faster than main()); merges into analysis.json."""
    x = D()
    fr = frost_level(x)
    fits = {}
    for F, xp, p0f, surf, key in REVIEW_FITS:
        fits[key] = fit_cop_smooth(x, F, xp, p0_fixed=p0f, surface=surf, fr=fr if F == 29.0 else None)
        print(key, fits[key]["rmse_kw"], fits[key]["eta"], fits[key]["p0"], fits[key]["frost_d"])
    OUT["cop_fits_smooth"] = fits
    defrost_per_kwh(x)
    surge_vs_power(x)
    start_cost_vs_off(x)
    path = RESULTS / "unit" / "analysis.json"
    old = json.loads(path.read_text()) if path.exists() else {}
    old.update(json.loads(json.dumps(OUT, default=float)))
    path.write_text(json.dumps(old, indent=1, default=float))
    for k_ in ("defrost_per_kwh", "surge_vs_power", "start_cost_vs_off"):
        print(f"\n## {k_}\n" + json.dumps(OUT[k_], default=float))


def main():
    x = D()
    start_rule(x)
    stop_rule(x)
    surge_marks(x)
    off_times(x)
    idle_circulation(x)
    capacity_control(x)
    refrigerant_temps(x)
    flow_estimates(x)
    fits = {}
    for F in (25.0, 29.0, 33.0):
        for xp in (0.0, 0.015, 0.03, None):
            key = f"F{F:.0f}_x{'fit' if xp is None else xp}"
            fits[key] = fit_cop(x, F, xp)
    fits["F29_x0.015_p0_0.15"] = fit_cop(x, 29.0, 0.015, p0_fixed=0.15)
    OUT["cop_fits"] = fits
    empirical_outlet_sensitivity(x)
    startup_cost(x, fits["F29_x0.015"])
    defrost_stats(x)
    dhw_stats(x)
    model_numbers()
    # review round 1 (also available alone: `python -m lab.sim.unit_analysis review`)
    fr = frost_level(x)
    OUT["cop_fits_smooth"] = {key: fit_cop_smooth(x, F, xp, p0_fixed=p0f, surface=surf, fr=fr if F == 29.0 else None)
                              for F, xp, p0f, surf, key in REVIEW_FITS}
    defrost_per_kwh(x)
    surge_vs_power(x)
    start_cost_vs_off(x)
    out = RESULTS / "unit"
    out.mkdir(parents=True, exist_ok=True)
    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        return o

    OUT.update(clean(OUT))
    (out / "analysis.json").write_text(json.dumps(OUT, indent=1, default=float))
    for k_, v in OUT.items():
        print(f"\n## {k_}")
        print(json.dumps(v, default=float)[:3000])


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) > 1 and _sys.argv[1] == "review":
        review_main()
    elif len(_sys.argv) > 1 and _sys.argv[1] == "frost_counts":
        _x = D()
        _prof = json.loads((RESULTS / "unit" / "analysis.json").read_text())["frost_stop_fit"]["profile"]
        frost_count_fit(_x, {float(k): v for k, v in _prof.items() if float(k) in (0.0, 0.2, 0.4, 0.6)})
        _merge_out()
    elif len(_sys.argv) > 1 and _sys.argv[1] == "review2":
        review2_main(tuple(_sys.argv[2].split(",")) if len(_sys.argv) > 2 else ("frost", "cop"))
    else:
        main()
