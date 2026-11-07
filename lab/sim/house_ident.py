"""Identify the house model (lab/sim/house.py) from the minute data; private outputs.

Method (see docs/research/lab/HOUSE_MODEL.md):
- The model is linear and time-invariant when the loop heat is the input, so the whole
  Feb-Nov minute record is simulated at once with exact (matrix-exponential) discretization and
  modal first-order filters (scipy lfilter), ~0.2 s per pass.
- A steady-state Kalman observer (room sensor + loop return; room only where the return is not
  a loop reading) gives the state at forecast origins every hour. From each origin the model runs
  open loop with the measured inputs (loop heat, ERA5 weather, sun). The fit minimizes the
  multi-step errors: room at 1, 3, 6, 12, 24 h ahead and return at 15 min, 1 h, 3 h ahead.
- Windows with air-conditioner use, uncertain (electricity-estimated) loop heat, or a missing
  room reading are excluded. Two minute-data blocks are held out (never in the fit).

Run:
  .local/lab-venv/bin/python -m lab.sim.house_ident compare     # structure comparison
  .local/lab-venv/bin/python -m lab.sim.house_ident fit          # central fit + validation
  .local/lab-venv/bin/python -m lab.sim.house_ident disturbance  # residual heat -> CSV
  .local/lab-venv/bin/python -m lab.sim.house_ident hourly       # season energy reconciliation
Outputs go to .local/lab-results/house/ (private) and .local/lab-data/disturbance_minute.csv.
"""
from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
from scipy.linalg import solve_discrete_are
from scipy.optimize import least_squares
from scipy.signal import lfilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from lab.data.common import DATA, epoch  # noqa: E402
from lab.sim import house as H  # noqa: E402
from lab.sim.house_prep import OUT, load  # noqa: E402

DT_H = 1.0 / 60.0
H_ROOM = (60, 180, 360, 720, 1440)
H_RET = (15, 60, 180)
W_RET = 0.5  # weight of return errors relative to room errors

FIT_RANGES = [
    ("A0", "2026-02-09T00:00Z", "2026-02-14T16:00Z"),  # cold week before the link outage
    ("A", "2026-02-26T00:00Z", "2026-05-06T15:00Z"),
    ("F", "2026-09-25T00:00Z", "2026-10-08T04:00Z"),  # heating off, free-floating room
    ("C", "2026-10-09T00:00Z", "2026-11-02T00:00Z"),
]
HOLD_RANGES = [
    ("hold_A", "2026-03-16T00:00Z", "2026-03-20T00:00Z"),
    ("hold_C", "2026-11-02T00:00Z", "2026-11-06T16:00Z"),
]

# process noise (K per sqrt(minute)) by state kind, measurement noise (K)
PNOISE = {"w": 0.05, "s": 0.004, "a": 0.012, "e": 0.003, "m": 0.004, "g": 0.01}
R_ROOM, R_RET = 0.07, 0.10


# ------------------------------------------------------------------------------------------
# data
# ------------------------------------------------------------------------------------------

class Data:
    dt_h = DT_H

    def __init__(self):
        a = load()
        self.a = a
        self.t = a["t"]
        n = len(self.t)
        self.n = n
        q = np.nan_to_num(a["q_loop"])
        hl = a["hour_local"]
        w = 2 * np.pi * hl / 24.0
        self.U = np.zeros((n, len(H.U_NAMES)))
        iu = {k: i for i, k in enumerate(H.U_NAMES)}
        self.iu = iu
        self.U[:, iu["q"]] = q
        self.U[:, iu["t_out"]] = a["t_out"]
        for k in ("poa_s", "poa_e", "poa_w", "ghi"):
            self.U[:, iu[k]] = np.nan_to_num(a[k])
        self.U[:, iu["one"]] = 1.0
        self.U[:, iu["c1"]] = np.cos(w)
        self.U[:, iu["s1"]] = np.sin(w)
        self.U[:, iu["c2"]] = np.cos(2 * w)
        self.U[:, iu["s2"]] = np.sin(2 * w)
        room = a["room"].copy()
        valid_room = ~np.isnan(room)
        # fill short NaNs for the observer input (held value)
        idx = np.where(valid_room, np.arange(n), 0)
        idx = np.maximum.accumulate(idx)
        first = np.argmax(valid_room)
        room_f = room[idx]
        room_f[:first] = room[first]
        self.room = room
        self.room_f = room_f
        ret = a["ret"]
        self.ret = ret
        vr = ~np.isnan(ret)
        # return usable by the observer: measured, or inside a gap <= 60 min (interpolated)
        ret_f = ret.copy()
        ii = np.arange(n)
        if vr.any():
            ret_f = np.interp(ii, ii[vr], ret[vr])
        prev = np.maximum.accumulate(np.where(vr, ii, -10**9))
        nxt = np.minimum.accumulate(np.where(vr, ii, 10**9)[::-1])[::-1]
        self.ret_obs = vr | ((nxt - prev) <= 60)
        self.ret_f = ret_f
        # window masks (cumulative counts of 'bad' minutes)
        bad = a["q_est"] | a["ac_any"] | ~valid_room
        self.cbad = np.concatenate([[0], np.cumsum(bad)])
        self.cac = np.concatenate([[0], np.cumsum(a["ac_any"])])
        self.valid_room = valid_room
        self.valid_ret = vr

    def idx(self, iso):
        return int(np.searchsorted(self.t, epoch(iso)))

    def ranges(self, which):
        rr = FIT_RANGES if which == "fit" else HOLD_RANGES
        return [(name, self.idx(a), self.idx(b)) for name, a, b in rr]

    def origins(self, which, step=60, hmax=1440):
        """Origin minute indices inside the ranges (window must fit inside too)."""
        out = []
        hold = [(self.idx(a), self.idx(b)) for _, a, b in HOLD_RANGES]
        for name, i0, i1 in self.ranges(which):
            o = np.arange(i0, i1 - hmax, step)
            if which == "fit":  # keep fit windows away from the holdout blocks
                keep = np.ones(len(o), bool)
                for h0, h1 in hold:
                    keep &= (o + hmax < h0) | (o >= h1)
                o = o[keep]
            out.append(o)
        return np.concatenate(out) if out else np.zeros(0, int)

    def labels(self, o):
        lab = np.empty(len(o), dtype=object)
        for name, i0, i1 in self.ranges("fit") + self.ranges("hold"):
            lab[(o >= i0) & (o < i1)] = name
        return lab


# ------------------------------------------------------------------------------------------
# fast linear simulation
# ------------------------------------------------------------------------------------------

def run_lti(F, G, x0):
    """x[k+1] = F x[k] + G[k], x[0] = x0; returns x for k = 0..T-1 (T x n)."""
    lam, V = np.linalg.eig(F)
    Vi = np.linalg.inv(V)
    Z = G @ Vi.T  # T x n (complex)
    z0 = Vi @ x0
    T, n = G.shape
    zs = np.empty((T, n), complex)
    for j in range(n):
        # z[k] = lam z[k-1] + Z[k-1]  ->  filter Z shifted by one
        inp = np.concatenate([[z0[j]], Z[:-1, j]])
        zs[:, j] = lfilter([1.0], [1.0, -lam[j]], inp)
    X = (zs @ V.T).real
    return X


def kalman_gain(Ad, C, names, rows, dt_min=1.0):
    q = np.array([PNOISE[nm[0]] ** 2 * dt_min for nm in names])
    Qn = np.diag(q)
    Cc = C[rows]
    Rn = np.diag([R_ROOM ** 2 if r == 0 else R_RET ** 2 for r in rows])
    P = solve_discrete_are(Ad.T, Cc.T, Qn, Rn)
    S = Cc @ P @ Cc.T + Rn
    L = P @ Cc.T @ np.linalg.inv(S)  # filter gain: x(k|k) = x(k|k-1) + L e
    return L


class Engine:
    def __init__(self, data: Data, glow_src="poa_s"):
        self.d = data
        self.dt_h = data.dt_h
        self.glow_src = glow_src
        self.U = data.U.copy()
        self.U[:, data.iu["i_glow"]] = self.U[:, data.iu[glow_src]] if glow_src in data.iu else 0.0

    def observe(self, p: H.HouseParams, i0=0, i1=None):
        """Observer pass. Returns predicted states x(k|k-1), filtered x(k|k), Ad, Bd, C."""
        d = self.d
        i1 = d.n if i1 is None else i1
        A, B, C, names = H.matrices(p, "heat")
        Ad, Bd = H.discretize(A, B, self.dt_h)
        U = self.U[i0:i1]
        BU = U @ Bd.T
        y = np.stack([d.room_f[i0:i1], d.ret_f[i0:i1]], 1)
        dm = self.dt_h * 60.0
        L2 = kalman_gain(Ad, C, names, [0, 1], dm)
        L1 = np.zeros((len(names), 2))
        L1[:, :1] = kalman_gain(Ad, C, names, [0], dm)
        use2 = d.ret_obs[i0:i1]
        # blocks of constant observer type
        edges = np.flatnonzero(np.diff(use2.astype(int))) + 1
        starts = np.concatenate([[0], edges])
        ends = np.concatenate([edges, [len(use2)]])
        n = len(names)
        Xp = np.empty((len(U), n))
        # quasi-steady start (slow envelope/slab states would otherwise need days to settle)
        hh = H.House(p, t_init=float(d.room_f[i0]),
                     t_out_init=float(np.mean(U[: int(24 / self.dt_h), d.iu["t_out"]])))
        x = hh.x.copy()
        for s0, s1 in zip(starts, ends):
            L = L2 if use2[s0] else L1
            yy = y[s0:s1].copy()
            if not use2[s0]:
                yy[:, 1] = 0.0
            F = Ad - Ad @ L @ C
            G = BU[s0:s1] + yy @ (Ad @ L).T
            X = run_lti(F, G, x)
            Xp[s0:s1] = X
            # next block start: one more step from the last state
            k = s1 - 1
            xf = X[-1] + L @ (yy[-1] - C @ X[-1])
            x = Ad @ xf + BU[k]
        # filtered states
        innov = y - Xp @ C.T
        innov[~use2, 1] = 0.0
        Xf = Xp.copy()
        Xf[use2] += innov[use2] @ L2.T
        Xf[~use2] += innov[~use2] @ L1.T
        return Xp, Xf, Ad, Bd, C, names

    def forecast_errors(self, p, origins, h_room=H_ROOM, h_ret=H_RET, Xf=None, ol=None):
        """Errors of open-loop forecasts from observer states at the origins."""
        d = self.d
        if Xf is None:
            _, Xf, Ad, Bd, C, names = self.observe(p)
        else:
            Ad, Bd, C, names = ol
        BU = self.U @ Bd.T
        Xol = run_lti(Ad, BU[:-1], Xf[0])
        Xol = np.vstack([Xol, Ad @ Xol[-1] + BU[-2]])
        Yol = Xol @ C.T
        out = {}
        D = Xf[origins] - Xol[origins]
        lam, V = np.linalg.eig(Ad)
        Vi = np.linalg.inv(V)
        for row, hs, meas, valid in ((0, h_room, d.room, d.valid_room), (1, h_ret, d.ret, d.valid_ret)):
            for h in hs:
                tgt = origins + h
                ok = tgt < d.n
                o, tg = origins[ok], tgt[ok]
                Ah = (V @ np.diag(lam ** h) @ Vi).real
                pred = Yol[tg, row] + D[ok] @ (C[row] @ Ah)
                e = pred - meas[tg]
                good = valid[tg] & ((d.cbad[tg + 1] - d.cbad[o]) <= 15)
                if row == 0:
                    good &= (d.cac[tg + 1] - np.maximum(d.cac[np.maximum(o - 180, 0)], 0)) == 0
                full = np.full(len(origins), np.nan)
                full[np.flatnonzero(ok)[good]] = e[good]
                out[(row, h)] = full
        return out


# ------------------------------------------------------------------------------------------
# parameterization
# ------------------------------------------------------------------------------------------

LOG = {"c_w", "u_ws", "c_s", "k_sa", "h_g", "c_a", "h_ao", "c_e", "k_ae", "h_eo", "a_s", "a_e",
       "a_w", "a_h", "tau_m_h", "tau_g_h", "g_glow"}
LOGIT = {"f_sol_slab"}


def to_theta(p, free):
    th = []
    for k in free:
        v = getattr(p, k)
        if k in LOG:
            th.append(math.log(max(v, 1e-6)))
        elif k in LOGIT:
            v = min(max(v, 1e-4), 1 - 1e-4)
            th.append(math.log(v / (1 - v)))
        else:
            th.append(v)
    return np.array(th)


def from_theta(base, free, th):
    kw = {}
    for k, v in zip(free, th):
        if k in LOG:
            kw[k] = math.exp(v)
        elif k in LOGIT:
            kw[k] = 1.0 / (1.0 + math.exp(-v))
        else:
            kw[k] = float(v)
    return replace(base, **kw)


def residuals(eng, base, free, origins, th):
    p = from_theta(base, free, th)
    if isinstance(eng, Joint):
        return eng.residuals(p)
    try:
        err = eng.forecast_errors(p, origins)
    except (np.linalg.LinAlgError, ValueError):
        return np.full(len(origins) * (len(H_ROOM) + len(H_RET)), 10.0)
    res = []
    for (row, h), e in err.items():
        w = 1.0 if row == 0 else W_RET
        e = np.where(np.isnan(e), 0.0, e)
        res.append(w * e / math.sqrt(len(e)))
    r = np.concatenate(res)
    return r


H_LONG = (2880, 5760)  # 2- and 4-day room horizons (energy balance)
H_SEASON = (24, 72, 168)  # hourly season: 1, 3 and 7 days ahead
W_SEASON = 1.0


class Joint:
    """Minute multi-step errors + long minute horizons + hourly cold-season errors."""

    def __init__(self, eng, origins, eng_s, origins_s, w_season=W_SEASON):
        self.eng, self.O, self.eng_s, self.O_s, self.w_s = eng, origins, eng_s, origins_s, w_season
        self.n_out = None

    def residuals(self, p):
        try:
            err = self.eng.forecast_errors(p, self.O, h_room=H_ROOM + H_LONG)
            err_s = self.eng_s.forecast_errors(p, self.O_s, h_room=H_SEASON, h_ret=())
        except (np.linalg.LinAlgError, ValueError):
            return np.full(self.n_out, 10.0)
        res = []
        for (row, h), e in err.items():
            w = 1.0 if row == 0 else W_RET
            res.append(w * np.where(np.isnan(e), 0.0, e) / math.sqrt(len(e)))
        for (row, h), e in err_s.items():
            res.append(self.w_s * np.where(np.isnan(e), 0.0, e) / math.sqrt(len(e)))
        r = np.concatenate(res)
        self.n_out = len(r)
        return r


def fit(eng, base, free, origins, max_nfev=60, verbose=1):
    th0 = to_theta(base, free)
    t0 = time.time()
    sol = least_squares(lambda th: residuals(eng, base, free, origins, th), th0, method="trf",
                        x_scale=1.0, diff_step=1e-3, max_nfev=max_nfev, verbose=0)
    p = from_theta(base, free, sol.x)
    # approximate parameter standard errors (log space for LOG params)
    J = sol.jac
    dof = max(len(sol.fun) - len(th0), 1)
    s2 = float(sol.fun @ sol.fun) / dof
    try:
        cov = np.linalg.pinv(J.T @ J) * s2
        se = np.sqrt(np.clip(np.diag(cov), 0, None))
        corr = cov / np.outer(se + 1e-30, se + 1e-30)
    except np.linalg.LinAlgError:
        se = np.full(len(th0), np.nan)
        corr = None
    if verbose:
        print(f"  fit {len(free)} params, cost {sol.cost:.5f}, nfev {sol.nfev}, {time.time() - t0:.0f} s")
    return p, sol, se, corr


def summarize(eng, p, origins, Xf=None, ol=None):
    err = eng.forecast_errors(p, origins, Xf=Xf, ol=ol)
    lab = eng.d.labels(origins)
    out = {}
    for group in sorted(set(lab[lab != None])):  # noqa: E711
        g = lab == group
        out[group] = {}
        for (row, h), e in err.items():
            ee = e[g]
            ee = ee[~np.isnan(ee)]
            key = ("room" if row == 0 else "ret") + f"_{h}m"
            out[group][key] = {"rmse": round(float(np.sqrt(np.mean(ee ** 2))), 3) if len(ee) else None,
                               "bias": round(float(np.mean(ee)), 3) if len(ee) else None, "n": int(len(ee))}
    return out


# ------------------------------------------------------------------------------------------
# structures
# ------------------------------------------------------------------------------------------

BASE_FREE = ["c_w", "u_ws", "c_s", "k_sa", "c_a", "h_ao", "a_s", "a_e", "a_w", "f_sol_slab", "q_int"]


def structures():
    """name -> (base params, free list, glow source)."""
    b = H.HouseParams(n_seg=3, c_e=0.0, tau_m_h=0.0, g_glow=0.0, h_ao=0.17)
    S = {}
    S["S1_loop1_2node"] = (replace(b, n_seg=1), BASE_FREE, "poa_s")
    S["S2_loop3_2node"] = (b, BASE_FREE, "poa_s")
    be = replace(b, c_e=8.0, k_ae=0.4, h_eo=0.2, h_ao=0.05)
    S["S3_+envelope"] = (be, BASE_FREE + ["c_e", "k_ae", "h_eo"], "poa_s")
    prof = ["q_c1", "q_s1", "q_c2", "q_s2"]
    S["S4_+profile"] = (be, BASE_FREE + ["c_e", "k_ae", "h_eo"] + prof, "poa_s")
    bs = replace(be, tau_m_h=0.2)
    S["S5_+sensor_lag"] = (bs, S["S4_+profile"][1] + ["tau_m_h"], "poa_s")
    for src in ("poa_s", "poa_e", "poa_w", "ghi"):
        bg = replace(bs, g_glow=0.002, tau_g_h=0.2)
        S[f"S6_+glow_{src}"] = (bg, S["S5_+sensor_lag"][1] + ["g_glow", "tau_g_h"], src)
    return S


def extra_structures(best_name, best_p, best_free, glow):
    """Alternatives built on the best structure."""
    S = {}
    S["X1_+ground"] = (replace(best_p, h_g=0.03, t_ground=10.0), best_free + ["h_g"], glow)
    S["X2_+skylight_ghi"] = (replace(best_p, a_h=0.5), best_free + ["a_h"], glow)
    S["X3_loop1"] = (replace(best_p, n_seg=1), best_free, glow)
    S["X4_loop6"] = (replace(best_p, n_seg=6), best_free, glow)
    S["X5_sun_all_air"] = (replace(best_p, f_sol_slab=0.0), [k for k in best_free if k != "f_sol_slab"], glow)
    return S


def cmd_compare():
    d = Data()
    O_fit = d.origins("fit", step=180)
    O_all = np.concatenate([d.origins("fit", step=60), d.origins("hold", step=60)])
    res = {}
    best = None
    for name, (base, free, glow) in structures().items():
        print(name)
        eng = Engine(d, glow)
        p, sol, se, _ = fit(eng, base, free, O_fit, max_nfev=40)
        summ = summarize(eng, p, O_all)
        res[name] = {"params": _pdict(p), "cost": float(sol.cost), "n_free": len(free), "summary": summ,
                     "glow_src": glow}
        _print_summary(name, summ)
        if best is None or sol.cost < best[1]:
            best = (name, sol.cost, p, free, glow)
    name, _, p, free, glow = best
    for xname, (base, xfree, g) in extra_structures(name, p, free, glow).items():
        print(xname)
        eng = Engine(d, g)
        px, sol, se, _ = fit(eng, base, xfree, O_fit, max_nfev=60)
        summ = summarize(eng, px, O_all)
        res[xname] = {"params": _pdict(px), "cost": float(sol.cost), "n_free": len(xfree), "summary": summ,
                      "glow_src": g}
        _print_summary(xname, summ)
    res["_best"] = name
    (OUT / "compare.json").write_text(json.dumps(res, indent=1))


def _pdict(p):
    dd = asdict(p)
    dd.pop("ranges", None)
    return {k: (round(v, 5) if isinstance(v, float) else v) for k, v in dd.items()}


def _print_summary(name, summ):
    for g, s in summ.items():
        r = s
        print(f"   {g:7s} room 1h {r['room_60m']['rmse']}  6h {r['room_360m']['rmse']}  "
              f"24h {r['room_1440m']['rmse']} (bias {r['room_1440m']['bias']})  "
              f"ret 15m {r['ret_15m']['rmse']} 1h {r['ret_60m']['rmse']}")




# ------------------------------------------------------------------------------------------
# central fit, validation and uncertainty variants
# ------------------------------------------------------------------------------------------

CENTRAL = "S6_+glow_ghi"  # best of the S-series by multi-step cost (compare.json)
CENTRAL_EXTRAS = ("X1_+ground",)  # lower cost, better holdout, and makes internal gains physical
JOINT = True  # reconcile with the hourly cold season (see cmd_fit)
GLOW_TAU_H = 0.05  # glow time constant runs to 0 in the fit; fixed at 3 min


def central_spec():
    cmp_ = json.loads((OUT / "compare.json").read_text())
    name = CENTRAL or cmp_["_best"]
    base, free, glow = structures()[name]
    pp = cmp_[name]["params"]
    p = H.HouseParams(**{k: v for k, v in pp.items() if k in H.HouseParams.__dataclass_fields__})
    for x in CENTRAL_EXTRAS:
        xb, xfree, glow = extra_structures(name, p, free, glow)[x]
        changed = {k: getattr(xb, k) for k in ("n_seg", "h_g", "a_h", "f_sol_slab") if getattr(xb, k) != getattr(p, k)}
        p = replace(p, **changed)
        free = xfree
    p = replace(p, tau_g_h=GLOW_TAU_H, glow_src=glow)
    free = [k for k in free if k != "tau_g_h"]
    return name, p, list(free), glow


def _fix(p, free, scale_keys, factor):
    kw = {k: getattr(p, k) * factor for k in scale_keys}
    return replace(p, **kw), [k for k in free if k not in scale_keys]


def cmd_fit():
    d = Data()
    name, p0, free, glow = central_spec()
    print("central structure", name, CENTRAL_EXTRAS, "free", free)
    eng = Engine(d, glow)
    O_fit = d.origins("fit", step=60, hmax=max(H_LONG) if JOINT else 1440)
    if JOINT:
        cal = heat_ratio_calibration(d)
        S = build_hourly_series(d, cal)
        eng_s = Engine(S, glow)
        hs = lambda iso: int(np.searchsorted(S.t, epoch(iso)))  # noqa: E731
        O_s = np.arange(hs("2026-01-09T00:00Z"), hs("2026-03-01T00:00Z") - 168, 3)
        O_s = O_s[(O_s + 168 < hs("2026-01-12T00:00Z")) | (O_s >= hs("2026-01-26T00:00Z"))]
        J = Joint(eng, O_fit, eng_s, O_s)
        J.residuals(p0)
        p, sol, se, corr = fit(J, p0, free, O_fit, max_nfev=120)
    else:
        p, sol, se, corr = fit(eng, p0, free, O_fit, max_nfev=120)
    O_all = np.concatenate([d.origins("fit", step=60), d.origins("hold", step=60)])
    summ = summarize(eng, p, O_all)
    _print_summary("central", summ)
    hi_corr = []
    if corr is not None:
        for i_ in range(len(free)):
            for j_ in range(i_ + 1, len(free)):
                if abs(corr[i_, j_]) > 0.8:
                    hi_corr.append((free[i_], free[j_], round(float(corr[i_, j_]), 2)))
    out = {"structure": name, "extras": list(CENTRAL_EXTRAS), "free": free, "params": _pdict(p),
           "h_total": round(p.h_total, 4), "cost": float(sol.cost),
           "se_theta": {k: round(float(v), 4) for k, v in zip(free, se)},
           "high_correlations": hi_corr, "summary": summ}
    (OUT / "central.json").write_text(json.dumps(out, indent=1))
    # uncertainty variants: fix one aspect, refit the rest (fewer origins for speed)
    O_v = d.origins("fit", step=180, hmax=max(H_LONG) if JOINT else 1440)
    eng_v = Joint(eng, O_v, eng_s, O_s) if JOINT else eng
    if JOINT:
        eng_v.residuals(p)
    base_cost = float(np.sum(residuals(eng_v, p, free, O_v, to_theta(p, free)) ** 2) / 2)
    loss_keys = [k for k in ("h_ao", "h_eo", "k_ae", "h_g") if getattr(p, k) > 0]
    sun_keys = [k for k in ("a_s", "a_e", "a_w", "a_h") if getattr(p, k) > 0]
    variants = {}
    for vname, keys, fac in (("heavy_slab", ["c_s"], 1.3), ("light_slab", ["c_s"], 0.7),
                             ("loss_plus20", loss_keys, 1.2), ("loss_minus20", loss_keys, 0.8),
                             ("sun_plus30", sun_keys, 1.3), ("sun_minus30", sun_keys, 0.7)):
        pv, fv = _fix(p, free, keys, fac)
        pv, solv, _, _ = fit(eng_v, pv, fv, O_v, max_nfev=50)
        sv = summarize(eng, pv, O_all)
        variants[vname] = {"params": _pdict(pv), "h_total": round(pv.h_total, 4),
                           "cost_increase_pct": round(100 * (float(solv.cost) / base_cost - 1), 1), "summary": sv}
        print(vname, "cost +%.1f %%" % variants[vname]["cost_increase_pct"], "H", round(pv.h_total, 3))
        _print_summary(vname, sv)
    out["variants"] = variants
    (OUT / "central.json").write_text(json.dumps(out, indent=1))

# ------------------------------------------------------------------------------------------
# room reconstruction and disturbance (residual heat) by deadbeat tracking
# ------------------------------------------------------------------------------------------

def reconstruct_room(room, smooth_min=31):
    """Piecewise-linear reconstruction of a report-on-change quantized sensor: anchor at each
    change at the midpoint of old and new value, linear between anchors, then a centred moving
    average. NaN stays NaN."""
    n = len(room)
    v = room.copy()
    ii = np.arange(n)
    ch = np.flatnonzero((v[1:] != v[:-1]) & ~np.isnan(v[1:]) & ~np.isnan(v[:-1])) + 1
    if len(ch) < 2:
        return v
    anchors_t = ch.astype(float)
    anchors_v = 0.5 * (v[ch - 1] + v[ch])
    out = np.interp(ii, anchors_t, anchors_v)
    out[np.isnan(v)] = np.nan
    if smooth_min > 1:
        k = np.ones(smooth_min) / smooth_min
        good = ~np.isnan(out)
        num = np.convolve(np.where(good, out, 0.0), k, "same")
        den = np.convolve(good.astype(float), k, "same")
        with np.errstate(invalid="ignore", divide="ignore"):
            out = np.where(good & (den > 0.5), num / den, np.nan)
    return out


def track(p, U, target, dt_h, x0=None, d_max=8.0):
    """Residual heat into the air node (kW) that makes the model follow `target` (the room
    sensor). The sensor model is inverted first: glow removed, then the first-order lag undone
    (air = sensor + tau d(sensor)/dt on the smoothed target), so the deadbeat acts on the air
    node. Where target is NaN the residual is 0 and the model runs free. Returns d (kW per step),
    the state trajectory and the state names."""
    A, B, C, names = H.matrices(p, "heat")
    Ad, Bd = H.discretize(A, B, dt_h)
    iu = {k: i for i, k in enumerate(H.U_NAMES)}
    bd = Bd[:, iu["q_air"]].copy()
    U = U.copy()
    U[:, iu["q_air"]] = 0.0
    BU = U @ Bd.T
    ia = names.index("a")
    gain = float(bd[ia])
    tgt = np.asarray(target, float).copy()
    if p.g_glow != 0:
        a_ = math.exp(-dt_h / p.tau_g_h)
        gl = lfilter([1 - a_], [1, -a_], p.g_glow * U[:, iu["i_glow"]])
        tgt = tgt - gl
    if p.tau_m_h > 0:
        dy = np.gradient(tgt) / dt_h
        tgt = tgt + p.tau_m_h * np.where(np.isnan(dy), 0.0, dy)
    n = len(U)
    X = np.empty((n, len(names)))
    x = np.full(len(names), 22.0) if x0 is None else x0.copy()
    d = np.zeros(n)
    for k in range(n - 1):
        X[k] = x
        xn = Ad @ x + BU[k]
        tg = tgt[k + 1]
        if tg == tg:
            dk = (tg - xn[ia]) / gain
            dk = min(max(dk, -d_max), d_max)
            d[k] = dk
            xn = xn + bd * dk
        x = xn
    X[-1] = x
    return d, X, names


def _glow_input(U, glow_src):
    iu = {k: i for i, k in enumerate(H.U_NAMES)}
    U = U.copy()
    U[:, iu["i_glow"]] = U[:, iu[glow_src]] if glow_src in iu else 0.0
    return U


def load_central():
    j = json.loads((OUT / "central.json").read_text())
    pp = j["params"]
    p = H.HouseParams(**{k: v for k, v in pp.items() if k in H.HouseParams.__dataclass_fields__})
    return p, j


def cmd_disturbance():
    import csv
    import datetime as dt

    d = Data()
    p, j = load_central()
    U = _glow_input(d.U, p.glow_src)
    target = reconstruct_room(d.room)
    # start the tracker from the observer state at the first minute with a room reading
    eng = Engine(d, p.glow_src)
    _, Xf, *_ = eng.observe(p)
    i0 = int(np.argmax(~np.isnan(target)))
    dk, X, names = track(p, U[i0:], target[i0:], DT_H, x0=Xf[i0])
    dist = np.zeros(d.n)
    dist[i0:] = dk
    a = d.a
    season = np.zeros(d.n, int)
    for name, s0, s1 in d.ranges("fit") + d.ranges("hold"):
        season[s0:s1] = 1
    flags = (a["ac_any"].astype(int) * 1 + a["q_est"].astype(int) * 2 + np.isnan(target).astype(int) * 4)
    path = DATA / "disturbance_minute.csv"
    sm = np.convolve(dist, np.ones(60) / 60, "same")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_utc", "dist_w", "dist_w_60min", "room_recon", "model_sensor", "q_loop_w",
                    "in_season", "flags"])
        ia = names.index("a")
        ysim = np.full(d.n, np.nan)
        A_, B_, C_, _ = H.matrices(p, "heat")
        ysim[i0:] = X @ C_[0]
        for k in range(d.n):
            w.writerow([dt.datetime.fromtimestamp(int(d.t[k]), dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                        f"{1000 * dist[k]:.0f}", f"{1000 * sm[k]:.0f}",
                        "" if np.isnan(target[k]) else f"{target[k]:.3f}",
                        "" if np.isnan(ysim[k]) else f"{ysim[k]:.3f}",
                        f"{1000 * d.U[k, 0]:.0f}", season[k], flags[k]])
    np.savez_compressed(OUT / "disturbance.npz", dist=dist, target=target, season=season, flags=flags,
                        t=d.t, hour_local=a["hour_local"], q=d.U[:, 0], t_out=a["t_out"])
    print("wrote", path)
    characterize()


def characterize():
    """Typical daily profile + random events of the residual heat (heating seasons only)."""
    import datetime as dt

    z = np.load(OUT / "disturbance.npz")
    dist, season, flags, t, hl, q = z["dist"], z["season"], z["flags"], z["t"], z["hour_local"], z["q"]
    use = (season == 1) & (flags == 0)
    n = len(dist)
    # hourly means
    nh = n // 60
    D = dist[: nh * 60].reshape(nh, 60).mean(1)
    Uh = use[: nh * 60].reshape(nh, 60).all(1)
    HL = np.floor(hl[: nh * 60].reshape(nh, 60)[:, 0]).astype(int)
    tt = t[: nh * 60: 60]
    wd = np.array([dt.datetime.fromtimestamp(int(x), dt.timezone.utc).weekday() for x in tt])
    prof = {}
    for lab, m in (("all", np.ones(nh, bool)), ("weekday", wd < 5), ("weekend", wd >= 5)):
        prof[lab] = [round(float(np.mean(D[Uh & m & (HL == h)])) * 1000, 0) for h in range(24)]
    # daily means and their spread (slow component)
    nd = nh // 24
    Dd = D[: nd * 24].reshape(nd, 24)
    Ud = Uh[: nd * 24].reshape(nd, 24).all(1)
    daily = Dd.mean(1)[Ud]
    # residual after profile: AR(1) on hourly values
    pr = np.array(prof["all"]) / 1000.0
    r = D - pr[np.clip(HL, 0, 23)]
    good = Uh[1:] & Uh[:-1]
    phi = float(np.corrcoef(r[1:][good], r[:-1][good])[0, 1])
    sig = float(np.std(r[Uh]))
    # events on the 15-min mean: |d| > 1 kW for >= 15 min
    k15 = np.convolve(dist, np.ones(15) / 15, "same")
    ev = []
    for sign in (1, -1):
        on = (sign * k15 > 1.0) & use
        edges = np.flatnonzero(np.diff(on.astype(int)))
        st = edges[::2] + 1 if on[0] == 0 else np.concatenate([[0], edges[1::2] + 1])
        en = edges[1::2] + 1 if on[0] == 0 else edges[::2] + 1
        for a0, a1 in zip(st, en):
            if a1 - a0 >= 15:
                e_kwh = float(dist[a0:a1].sum() / 60.0)
                ev.append({"sign": sign, "start_hour_local": float(hl[a0]), "minutes": int(a1 - a0),
                           "kwh": round(e_kwh, 3), "peak_kw": round(float(sign * k15[a0:a1].max() * sign), 2)})
    days_used = float(use.sum() / 1440.0)
    pos = [e for e in ev if e["sign"] > 0]
    neg = [e for e in ev if e["sign"] < 0]

    def stats(lst):
        if not lst:
            return {}
        m = np.array([e["minutes"] for e in lst])
        k = np.array([abs(e["kwh"]) for e in lst])
        h = np.array([e["start_hour_local"] for e in lst])
        return {"per_day": round(len(lst) / days_used, 2), "minutes_p50": float(np.median(m)),
                "minutes_p90": float(np.percentile(m, 90)), "kwh_p50": round(float(np.median(k)), 2),
                "kwh_p90": round(float(np.percentile(k, 90)), 2),
                "start_hour_hist": np.histogram(h, bins=8, range=(0, 24))[0].tolist()}

    out = {
        "days_used": round(days_used, 1),
        "minute_w_pct": {str(q_): round(float(np.percentile(dist[use], q_)) * 1000, 0) for q_ in (1, 5, 25, 50, 75, 95, 99)},
        "mean_w": round(float(dist[use].mean()) * 1000, 0),
        "hourly_profile_w": prof,
        "daily_mean_w": {"mean": round(float(daily.mean()) * 1000, 0), "sd": round(float(daily.std()) * 1000, 0),
                         "p10": round(float(np.percentile(daily, 10)) * 1000, 0),
                         "p90": round(float(np.percentile(daily, 90)) * 1000, 0), "n_days": int(len(daily))},
        "hourly_after_profile": {"sd_w": round(sig * 1000, 0), "ar1_phi": round(phi, 3)},
        "events_pos": stats(pos), "events_neg": stats(neg),
    }
    (OUT / "disturbance_stats.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return out


# ------------------------------------------------------------------------------------------
# season (hourly) reconciliation
# ------------------------------------------------------------------------------------------

def _read_hourly():
    import csv

    with open(DATA / "hourly.csv") as f:
        rows = list(csv.DictReader(f))
    t = np.array([epoch(r["time_utc"]) for r in rows])

    def g(k):
        return np.array([float(r[k]) if r[k] not in ("", "None") else np.nan for r in rows])

    return t, g


def heat_ratio_calibration(d: Data):
    """Daily space heat / space-heating electricity from the minute days with clean data."""
    a = d.a
    t = d.t
    day0 = t[0] - t[0] % 86400
    di = ((t - day0) // 86400).astype(int)
    rows = []
    for k in np.unique(di):
        m = di == k
        if m.sum() < 1440 or not a["heating_on"][m].all():
            continue
        if a["ok_unit"][m].mean() < 0.97 or np.isnan(a["elec_kw"][m]).mean() > 0.03:
            continue
        e = np.nan_to_num(a["elec_kw"][m])
        tank = a["valve_tank"][m] | a["dhw"][m]
        q = np.nan_to_num(a["q_loop"][m]).sum() / 60.0
        e_dhw = e[tank].sum() / 60.0
        e_sh = e[~tank].sum() / 60.0
        if e_sh < 2.0:
            continue
        rows.append((float(np.mean(a["t_out"][m])), q, e_sh, e_dhw, float(np.nanmean(a["rh"][m]))))
    R = np.array(rows)
    T, Q, Esh, Edhw = R[:, 0], R[:, 1], R[:, 2], R[:, 3]
    ratio = Q / Esh
    # physics shape from the unit model (steady COP at a typical 31.5 degC supply and 6 kW, minus
    # the defrost penalty of the unit report), scaled by one factor fitted on these days
    shape = _unit_ratio(T)
    kappa = float(np.sum(Esh * ratio / shape) / np.sum(Esh))
    coef = np.array([kappa])
    resid = ratio - kappa * shape
    dcoef, *_ = np.linalg.lstsq(np.stack([np.ones_like(T), T], 1), Edhw, rcond=None)
    return {"ratio_coef": coef.tolist(), "ratio_resid_sd": float(np.std(resid)), "n_days": int(len(T)),
            "dhw_coef": dcoef.tolist(), "T_range": [float(T.min()), float(T.max())],
            "table": [[round(float(x), 2) for x in r] for r in R]}


def _unit_ratio(T):
    from lab.sim import unit as UN

    pu = UN.central()
    pen_t, pen_v = (-10.0, -3.0, 0.0, 2.0, 4.0, 8.0), (0.17, 0.11, 0.09, 0.055, 0.01, 0.0)
    T = np.atleast_1d(np.asarray(T, float))
    return np.array([UN.cop_steady(pu, 31.5, x, 6.0) * (1 - np.interp(x, pen_t, pen_v)) for x in T])


def ratio_at(cal, T):
    return cal["ratio_coef"][0] * _unit_ratio(T)


class Series:
    """Hourly series for the engine (same attribute names as Data)."""
    dt_h = 1.0


def build_hourly_series(d: Data, cal, t_start="2025-10-26T00:00Z", t_end="2026-05-06T00:00Z"):
    import datetime as dt
    from zoneinfo import ZoneInfo

    sys.path.insert(0, str(ROOT / "lab" / "data"))
    import build_datasets as BD  # noqa: E402
    from lab.data import common as CM

    ht, g = _read_hourly()
    i0, i1 = np.searchsorted(ht, epoch(t_start)), np.searchsorted(ht, epoch(t_end))
    ht = ht[i0:i1]
    n = len(ht)
    site = BD.SITE
    grid = np.arange(ht[0], ht[-1] + 3600, 60.0)
    elev, az = CM.solar_position(grid + 30.0, site["lat"], site["lon"])
    toa = CM.toa_horizontal(grid + 30.0, elev)
    wx = BD.weather_minute(grid, toa, elev, az)
    def hmean(x):
        x = np.nan_to_num(x[: n * 60])
        return x.reshape(n, 60).mean(1)
    S = Series()
    S.t = ht
    S.n = n
    S.iu = {k: i for i, k in enumerate(H.U_NAMES)}
    U = np.zeros((n, len(H.U_NAMES)))
    T = g("wx_t")[i0:i1]
    U[:, S.iu["t_out"]] = T
    for k in ("poa_s", "poa_e", "poa_w"):
        U[:, S.iu[k]] = hmean(wx[k][0])
    U[:, S.iu["ghi"]] = hmean(wx["wx_ghi"][0])
    U[:, S.iu["one"]] = 1.0
    tz = ZoneInfo("Europe/Vilnius")
    hl = np.array([(dt.datetime.fromtimestamp(int(x) + 1800, tz).hour + 0.5) % 24 for x in ht])
    w = 2 * np.pi * hl / 24
    U[:, S.iu["c1"]], U[:, S.iu["s1"]] = np.cos(w), np.sin(w)
    U[:, S.iu["c2"]], U[:, S.iu["s2"]] = np.cos(2 * w), np.sin(2 * w)
    # heat: measured hourly mean where the minute data is clean, else electricity x ratio
    E = g("elec_out_kwh")[i0:i1]
    Eph = g("elec_kwh_phases")[i0:i1]
    E = np.where(np.isnan(E), Eph, E)
    day = ((ht - ht[0] + 0) // 86400).astype(int)
    Tday = np.array([np.nanmean(T[day == k]) for k in day])
    e_dhw_day = np.clip(cal["dhw_coef"][0] + cal["dhw_coef"][1] * Tday, 0.3, None)
    Eday = np.array([np.nansum(E[day == k]) for k in day])
    f_sh = np.clip(1.0 - e_dhw_day / np.maximum(Eday, 1e-3), 0.0, 1.0)
    q_est = ratio_at(cal, Tday) * np.nan_to_num(E) * f_sh
    q_meas = np.full(n, np.nan)
    mi = np.searchsorted(d.t, ht)
    for k in range(n):
        j0 = mi[k]
        if j0 + 60 <= d.n and d.t[j0] == ht[k]:
            seg = slice(j0, j0 + 60)
            if d.a["ok_unit"][seg].mean() >= 0.9 or not d.a["heating_on"][seg].any():
                q_meas[k] = np.nan_to_num(d.a["q_loop"][seg]).mean()
    q = np.where(np.isnan(q_meas), q_est, q_meas)
    U[:, S.iu["q"]] = q
    S.U = U
    S.q_measured = ~np.isnan(q_meas)
    S.q_est_series = q_est
    S.E = E
    # room at the hour boundary = mean of the two neighbouring hourly means
    room_m = g("room_mean")[i0:i1]
    wifi = g("room_wifi_mean")[i0:i1]
    both = ~np.isnan(room_m) & ~np.isnan(wifi)
    off = float(np.nanmedian(room_m[both] - wifi[both])) if both.any() else 1.0
    S.wifi_offset = off
    rm = np.where(np.isnan(room_m), wifi + off, room_m)
    S.room_is_main = ~np.isnan(room_m)
    yb = np.full(n, np.nan)
    yb[1:] = 0.5 * (rm[1:] + rm[:-1])
    S.room = np.where(np.concatenate([[False], S.room_is_main[1:] & S.room_is_main[:-1]]), yb, np.nan)
    S.room_obs_all = yb
    rf = yb.copy()
    ok = ~np.isnan(rf)
    rf = np.interp(np.arange(n), np.flatnonzero(ok), rf[ok])
    S.room_f = rf
    S.valid_room = ~np.isnan(S.room)
    S.ret = np.full(n, np.nan)
    S.ret_f = np.zeros(n)
    S.ret_obs = np.zeros(n, bool)
    S.valid_ret = np.zeros(n, bool)
    S.cbad = np.zeros(n + 1)
    S.cac = np.zeros(n + 1)
    S.T = T
    S.hl = hl
    return S


def cmd_hourly():
    import datetime as dt

    d = Data()
    p, j = load_central()
    cal = heat_ratio_calibration(d)
    print("heat/elec ratio calibration:", {k: v for k, v in cal.items() if k != "table"})
    S = build_hourly_series(d, cal)
    eng = Engine(S, p.glow_src)
    t_h = S.t

    def hidx(iso):
        return int(np.searchsorted(t_h, epoch(iso)))

    hold = (hidx("2026-01-12T00:00Z"), hidx("2026-01-26T00:00Z"))
    O = np.arange(hidx("2026-01-09T00:00Z"), hidx("2026-04-30T00:00Z"), 1)
    err = eng.forecast_errors(p, O, h_room=(1, 6, 24), h_ret=())
    res = {"cal": {k: v for k, v in cal.items() if k != "table"}, "wifi_offset": S.wifi_offset}
    in_hold = (O >= hold[0]) & (O + 24 < hold[1])
    cold = np.array([np.mean(S.T[o:o + 24]) < -5 for o in O])
    est_q = np.array([(~S.q_measured[o:o + 24]).mean() > 0.5 for o in O])
    groups = {"hold_jan12_26": in_hold, "fit_period_all": ~in_hold, "cold_days_Tmean<-5": cold,
              "elec_estimated_heat": est_q & ~in_hold, "measured_heat": ~est_q & ~in_hold}
    res["forecast"] = {}
    for gname, gm in groups.items():
        res["forecast"][gname] = {}
        for (row, h), e in err.items():
            ee = e[gm]
            ee = ee[~np.isnan(ee)]
            res["forecast"][gname][f"room_{h}h"] = {"rmse": round(float(np.sqrt(np.mean(ee ** 2))), 3) if len(ee) else None,
                                                    "bias": round(float(np.mean(ee)), 3) if len(ee) else None, "n": int(len(ee))}
    print(json.dumps(res["forecast"], indent=1))
    # open-loop free run over the holdout from the observer state at its start
    _, Xf, Ad, Bd, C, names = eng.observe(p)
    BU = S.U @ Bd.T
    x = Xf[hold[0]].copy()
    ys = []
    for k in range(hold[0], hold[1]):
        ys.append(C[0] @ x)
        x = Ad @ x + BU[k]
    ys = np.array(ys)
    yt = S.room[hold[0]:hold[1]]
    ok = ~np.isnan(yt)
    res["holdout_free_run_14d"] = {"rmse": round(float(np.sqrt(np.mean((ys[ok] - yt[ok]) ** 2))), 3),
                                   "bias": round(float(np.mean(ys[ok] - yt[ok])), 3),
                                   "max_abs": round(float(np.max(np.abs(ys[ok] - yt[ok]))), 3)}
    print("holdout free run", res["holdout_free_run_14d"])
    # residual heat by deadbeat tracking at the hourly step -> daily energy error
    U = _glow_input(S.U, p.glow_src)
    tgt = S.room_obs_all.copy()
    i0 = int(np.argmax(~np.isnan(tgt)))
    dk, X, _ = track(p, U[i0:], tgt[i0:], 1.0, x0=Xf[i0], d_max=20.0)
    dd = np.zeros(S.n)
    dd[i0:] = dk
    q = S.U[:, S.iu["q"]]
    day = ((t_h - t_h[0]) // 86400).astype(int)
    daily = []
    for k in np.unique(day):
        m = day == k
        if m.sum() < 24 or not S.room_is_main[m].all():
            continue
        daily.append((float(t_h[m][0]), float(np.mean(S.T[m])), float(q[m].sum()), float(dd[m].sum()),
                      float(S.q_measured[m].mean())))
    Dd = np.array(daily)
    rel = -Dd[:, 3] / np.maximum(Dd[:, 2], 1e-3)  # model needs less (+) or more (-) heat than supplied
    res["daily_energy"] = {}
    for gname, gm in (("Tmean<-5", Dd[:, 1] < -5), ("-5..0", (Dd[:, 1] >= -5) & (Dd[:, 1] < 0)),
                      ("0..5", (Dd[:, 1] >= 0) & (Dd[:, 1] < 5)), ("all", Dd[:, 1] < 99)):
        if gm.sum():
            res["daily_energy"][gname] = {
                "days": int(gm.sum()), "heat_kwh_per_day": round(float(Dd[gm, 2].mean()), 1),
                "residual_kwh_per_day": round(float(Dd[gm, 3].mean()), 2),
                "bias_pct": round(float(100 * -Dd[gm, 3].sum() / Dd[gm, 2].sum()), 1),
                "mae_pct": round(float(100 * np.mean(np.abs(rel[gm]))), 1)}
    # weekly view of the cold weeks
    weeks = []
    wk = ((Dd[:, 0] - Dd[0, 0]) // (7 * 86400)).astype(int)
    for k in np.unique(wk):
        m = wk == k
        weeks.append({"week_start": dt.datetime.fromtimestamp(Dd[m, 0][0], dt.timezone.utc).strftime("%Y-%m-%d"),
                      "days": int(m.sum()), "t_out": round(float(Dd[m, 1].mean()), 1),
                      "heat_kwh_day": round(float(Dd[m, 2].mean()), 1),
                      "residual_kwh_day": round(float(Dd[m, 3].mean()), 2),
                      "energy_error_pct": round(float(100 * -Dd[m, 3].sum() / Dd[m, 2].sum()), 1),
                      "measured_heat_share": round(float(Dd[m, 4].mean()), 2)})
    res["weekly"] = weeks
    print(json.dumps(res["daily_energy"], indent=1))
    for w_ in weeks:
        print(w_)
    # daily regression: Q = H*24*(Ti-To) - g*S - 24*q0 (independent of the dynamic model)
    res["daily_regression"] = daily_regression(S, p)
    print("daily regression", res["daily_regression"])
    (OUT / "hourly.json").write_text(json.dumps(res, indent=1))


def daily_regression(S, p):
    q = S.U[:, S.iu["q"]]
    sol = (p.a_s * S.U[:, S.iu["poa_s"]] + p.a_e * S.U[:, S.iu["poa_e"]] + p.a_w * S.U[:, S.iu["poa_w"]]
           + p.a_h * S.U[:, S.iu["ghi"]]) / 1000.0
    room = S.room_obs_all
    day = ((S.t - S.t[0]) // 86400).astype(int)
    rows = []
    for k in np.unique(day):
        m = day == k
        if m.sum() < 24 or np.isnan(room[m]).any() or not S.room_is_main[m].all():
            continue
        rows.append((q[m].sum(), np.mean(room[m] - S.T[m]) * 24, sol[m].sum(), np.mean(S.T[m]),
                     S.q_measured[m].mean()))
    R = np.array(rows)
    out = {}
    q0_model = p.q_int
    for name, m in (("all", np.ones(len(R), bool)), ("Tmean<0", R[:, 3] < 0), ("measured_heat", R[:, 4] > 0.9),
                    ("elec_estimated", R[:, 4] < 0.1)):
        if m.sum() < 8:
            continue
        Y = R[m, 0]
        X = np.stack([R[m, 1], -R[m, 2], -24 * np.ones(m.sum())], 1)
        c_free, *_ = np.linalg.lstsq(X, Y, rcond=None)
        # internal gains fixed at the model value
        X2 = np.stack([R[m, 1], -R[m, 2]], 1)
        c_fix, *_ = np.linalg.lstsq(X2, Y + 24 * q0_model, rcond=None)
        rng = np.random.default_rng(0)
        bs = []
        for _ in range(300):
            ii = rng.integers(0, m.sum(), m.sum())
            cb, *_ = np.linalg.lstsq(X2[ii], (Y + 24 * q0_model)[ii], rcond=None)
            bs.append(cb[0])
        out[name] = {"days": int(m.sum()), "H_free": round(float(c_free[0]), 4), "sun_scale_free": round(float(c_free[1]), 2),
                     "q0_free_kw": round(float(c_free[2]), 3), "H_q0_fixed": round(float(c_fix[0]), 4),
                     "H_q0_fixed_90ci": [round(float(np.percentile(bs, 5)), 4), round(float(np.percentile(bs, 95)), 4)],
                     "sun_scale_q0_fixed": round(float(c_fix[1]), 2)}
    out["model_H_total"] = round(p.h_total, 4)
    out["model_q_int"] = round(q0_model, 3)
    return out

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "compare"
    {"compare": cmd_compare, "fit": cmd_fit, "disturbance": cmd_disturbance, "hourly": cmd_hourly,
     "characterize": characterize}[cmd]()
