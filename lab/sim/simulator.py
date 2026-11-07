"""Closed-loop simulator: controller -> Versati unit model -> floor loop / house model -> sensors.

One step is one minute:

1. The controller gets an `Observation` of the state at the start of the minute (what Home
   Assistant would show) and returns a `Command`.
2. The command is clamped to the unit's register range/resolution and applied; it acts from this
   minute on, so its effect first shows in the next observation. Every field that changes a
   register value counts as one write.
3. The unit model (lab/sim/unit.py) steps with the house's return temperature, the outdoor air,
   humidity and the hot-water request; it returns the heat into the loop and the electricity.
4. The house model (lab/sim/house.py, exact discretisation, heat as input) steps with that heat,
   the weather, the sun, the internal gains and the disturbance.
5. Sensors: the room thermometer reports in 0.1 K steps when the value moves by >= 0.075 K
   (report-on-change, like the Zigbee sensor); unit water sensors read every minute in 0.1 K;
   the unit's outdoor sensor carries a slow local error and sun warming (0.5 K steps).

Everything the simulator needs from outside (weather, hot water, disturbances, PV, initial
state) comes in an `Exo` built by lab/sim/scenarios.py. `run()` returns per-minute arrays and the
metrics of lab/sim/metrics.py for the measured part (the warm-up under the neutral reference
controller is excluded).
"""
from __future__ import annotations

import datetime as dt
import math
import time
from dataclasses import dataclass, field

import numpy as np

from lab.sim import house as H
from lab.sim import unit as UM
from lab.sim.exogenous import SUN_BIAS_IDLE, SUN_BIAS_RUN, Forecast
from lab.sim.interface import Command, Observation

UTC = dt.timezone.utc
MODE_CODE = {"off": 0, "idle": 1, "heat": 2, "defrost": 3, "dhw": 4}
MODE_NAME = {v: k for k, v in MODE_CODE.items()}
ROOM_RES = 0.1
ROOM_REPORT_K = 0.075  # report when the true reading moved by >= 0.75 of a step (house model rule) ...
ROOM_HEARTBEAT_MIN = 60  # ... and at least once an hour (the new 0.1-K device: value changes cluster at 60 min)
ROOM_MIN_GAP_MIN = 0  # no minimum gap (the real device reports 2-3 min apart at its 10th percentile)
WATER_RES = 0.1
OUTDOOR_RES = 0.5


# ------------------------------------------------------------------------------------------
# plant variants
# ------------------------------------------------------------------------------------------

FLAG_TOKENS = ("raw_return", "anchor_heat", "era5_only", "synthetic_dist", "sparse_thermometer", "forecast_pessimistic",
               "long_outage")
LONG_OUTAGE_DAYS = 3.0  # flag token long_outage: one link outage this long from the middle of the window


def variant_names():
    return (["nominal"] + [k for k in UM.VARIANTS if k != "central"] + [k for k in H.VARIANTS if k != "central"]
            + list(FLAG_TOKENS))


def variant_flags(variant: str) -> set:
    return {p.strip() for p in (variant or "").split("+") if p.strip() in FLAG_TOKENS}


def plant(variant: str = "nominal"):
    """(UnitParams, HouseParams) for a variant name. Names of unit and house variants can be
    combined with '+', e.g. 'low_flow+heavy_slab'. The unit's flow variants scale the house
    (house.flow_scaled) so that both stay consistent with the measured heat."""
    up, hp = UM.central(), H.central()
    for part in (variant or "nominal").split("+"):
        part = part.strip()
        if part in ("", "nominal", "central") or part in FLAG_TOKENS:
            continue
        if part in UM.VARIANTS:
            up = UM.VARIANTS[part]()
        elif part in H.VARIANTS:
            hp = H.VARIANTS[part]()
        else:
            raise ValueError(f"unknown variant {part!r}; known: {', '.join(variant_names())}")
    if abs(up.flow_lpm - hp.flow_lpm) > 1e-9:
        hp = H.flow_scaled(hp, up.flow_lpm)
    return up, hp


# ------------------------------------------------------------------------------------------
# exogenous bundle
# ------------------------------------------------------------------------------------------

@dataclass
class Exo:
    """Everything outside the controller and the plant for one scenario run."""

    name: str
    grid: np.ndarray            # epoch seconds, 60 s step, warm-up + measured part
    n_warm: int                 # minutes of warm-up at the start of grid
    t_out: np.ndarray           # true outdoor air (ERA5-like), degC
    rh: np.ndarray
    ghi: np.ndarray
    poa_s: np.ndarray
    poa_e: np.ndarray
    poa_w: np.ndarray
    local_hour: np.ndarray
    dist: np.ndarray            # residual heat into the room-air node, kW
    pv: np.ndarray              # PV kW (NaN = unknown)
    outdoor_base: np.ndarray    # unit outdoor sensor before sun bias and quantisation
    dhw_requests: list          # [(grid index, compressor minutes)]
    x0: np.ndarray | None = None  # initial house state (None: quasi-steady at 22 degC)
    t_out_init: float = 5.0     # outdoor temperature for the quasi-steady start
    qbar0: float | None = None  # initial 24-h mean loop heat for the return anchoring (None: steady)
    t_ew0: float | None = None  # initial 24-h mean outdoor temperature (weather anchoring; None: t_out[0])
    t_out_era5: np.ndarray | None = None  # ERA5 temperature (what the forecast is built on); None = t_out
    n_tail: int = 0  # minutes of common run-out under the reference after the measured window (review round 1)
    registers: dict = field(default_factory=lambda: dict(setpoint=30.0, restart_delta=4.0, quiet=False,
                                                         heating_enabled=True))
    target: float = 22.0
    context: dict = field(default_factory=dict)   # extra controller params (e.g. recorded registers)
    seed: int = 0
    link_drops_per_day: float = 0.0
    link_durations: tuple | None = None  # outage lengths to draw from (None: measured heating season)
    description: str = ""


# ------------------------------------------------------------------------------------------
# simulator
# ------------------------------------------------------------------------------------------

REC_FIELDS = ("t_out", "rh", "ghi", "outdoor_s", "room_s", "room_age", "t_air", "t_sens", "t_slab", "t_env",
              "t_ret", "t_sup", "outlet_s", "inlet_s", "t_ctrl", "sp", "delta", "quiet", "enabled", "mode",
              "comp", "started", "q", "p_out", "p_in", "p_tank", "dhw_dem", "dist", "pv", "writes", "link", "anchor",
              "pump")
T_PLANT_ROOM = 20.0  # ASSUMED: what the unit's water sensors drift to while the pump is off
T_PLANT_TAU_MIN = 30.0


def _q(v, res):
    return round(round(v / res) * res, 2)


class _Clamp:
    def __init__(self, up):
        self.up = up

    def setpoint(self, v):
        p = self.up
        v = min(max(float(v), p.sp_min), p.sp_max)
        return float(round(v / p.sp_step) * p.sp_step)

    def delta(self, v):
        p = self.up
        return float(round(min(max(float(v), p.delta_min), p.delta_max)))


def run(controller, exo: Exo, variant: str = "nominal", forecast: str = "perfect", params: dict | None = None,
        reference=None, record: bool = True, plant_params=None):
    """Run one closed-loop simulation. Returns dict(meta, rec (per-minute arrays of the measured
    part), metrics)."""
    from lab.sim import metrics as M

    t_wall = time.perf_counter()
    up, hp = plant_params if plant_params is not None else plant(variant)
    unit = UM.VersatiUnit(up)
    clamp = _Clamp(up)
    if forecast == "noisy" and "forecast_pessimistic" in variant_flags(variant):
        forecast_mode = "pessimistic"
    else:
        forecast_mode = forecast
    fc = Forecast(forecast_mode, seed=exo.seed)
    n = len(exo.grid)
    n_warm = exo.n_warm
    n_tail = int(exo.n_tail or 0)
    k_end = n - n_tail  # first run-out minute

    # ---- house: exact discretisation, exogenous part precomputed ---------------------------
    A, B, C, names = H.matrices(hp, "heat")
    Ad, Bd = H.discretize(A, B, 1.0 / 60.0)
    iu = {k: i for i, k in enumerate(H.U_NAMES)}
    U = np.zeros((n, len(H.U_NAMES)))
    U[:, iu["t_out"]] = exo.t_out
    U[:, iu["poa_s"]] = exo.poa_s
    U[:, iu["poa_e"]] = exo.poa_e
    U[:, iu["poa_w"]] = exo.poa_w
    U[:, iu["ghi"]] = exo.ghi
    U[:, iu["one"]] = 1.0
    w = 2.0 * np.pi * exo.local_hour / 24.0
    U[:, iu["c1"]], U[:, iu["s1"]] = np.cos(w), np.sin(w)
    U[:, iu["c2"]], U[:, iu["s2"]] = np.cos(2 * w), np.sin(2 * w)
    U[:, iu["i_glow"]] = {"poa_s": exo.poa_s, "poa_e": exo.poa_e, "poa_w": exo.poa_w,
                          "ghi": exo.ghi}.get(hp.glow_src, 0.0)
    U[:, iu["q_air"]] = exo.dist
    E = U @ Bd.T
    bq = Bd[:, iu["q"]].copy()
    # pump stopped (space heating disabled, review round 1): loop water stagnant, exchanging
    # only with the slab; discretised lazily on first use
    off_sys = None
    c_room = C[0].copy()
    ix = {k: i for i, k in enumerate(names)}
    ia, islab, iret = ix["a"], ix["s"], ix[f"w{hp.n_seg}"]
    ie = ix.get("e", ia)
    cap = np.zeros(len(names))  # heat capacity per state (kWh/K) for the storage bookkeeping
    for k_, i_ in ix.items():
        cap[i_] = {"s": hp.c_s, "a": hp.c_a, "e": hp.c_e}.get(k_, hp.c_w / hp.n_seg if k_.startswith("w") else 0.0)
    if exo.x0 is not None:
        x = np.array(exo.x0, float).copy()
    else:
        hh = H.House(hp)
        hh.reset(22.0, t_out=exo.t_out_init)
        x = hh.x.copy()

    # ---- return anchoring (see exogenous._anchor_fit) ----------------------------------------
    flags = variant_flags(variant)
    anchor_on = "raw_return" not in flags
    anchor_heat = anchor_on and "anchor_heat" in flags
    from lab.sim.exogenous import ANCHOR_TAU_MIN, return_anchor, weather_load
    if anchor_on and not anchor_heat:
        # review round 1: a function of the weather-driven load (24-h mean outdoor), which no
        # controller can change; precomputed for the whole run
        kq, kb = return_anchor(hp, "weather")
        t0w = exo.t_ew0 if exo.t_ew0 is not None else float(exo.t_out[0])
        qw, _ = weather_load(hp, exo.t_out, t0=t0w)
        b_arr = np.interp(qw, kq, kb).tolist()
        anchor_tab = None
        a_q = 0.0
    elif anchor_heat:
        kq, kb = return_anchor(hp, "heat")
        anchor_tab = [float(v) for v in np.interp(np.arange(0, 161) * 0.05, kq, kb)]
        a_q = 1.0 / ANCHOR_TAU_MIN
        b_arr = None
    else:
        anchor_tab = [0.0] * 161
        a_q = 0.0
        b_arr = None
    qbar = exo.qbar0 if exo.qbar0 is not None else H.steady_heat(hp, 22.0, exo.t_out_init)
    b_anchor = b_arr[0] if b_arr is not None else anchor_tab[min(max(int(qbar * 20.0 + 0.5), 0), 160)]

    # ---- registers and sensor state ---------------------------------------------------------
    reg = exo.registers
    sp = clamp.setpoint(reg.get("setpoint", 30.0))
    delta = clamp.delta(reg.get("restart_delta", 4.0))
    quiet = bool(reg.get("quiet", False))
    enabled = bool(reg.get("heating_enabled", True))
    unit.last_sp = sp
    ret = float(x[iret]) + b_anchor  # return on the unit's sensor scale
    y = float(c_room @ x)
    rep = _q(y, ROOM_RES)
    rep_age = 0.0
    hb_age = 0
    room_thr = float(getattr(exo, "room_report_k", None) or ROOM_REPORT_K)
    room_min_gap = int(getattr(exo, "room_min_gap", None) or ROOM_MIN_GAP_MIN)
    if "sparse_thermometer" in variant_flags(variant):
        room_min_gap = max(room_min_gap, 20)  # robustness check for room-reactive controllers
    outlet_s = _q(ret - 0.3, WATER_RES)
    inlet_s = _q(ret, WATER_RES)
    mode_s = "idle" if enabled else "off"
    comp_s = False
    pe = UM.p_idle(up, float(exo.t_out[0]))
    energy = 0.0
    target = float(exo.target)
    pv_arr = exo.pv
    has_pv = np.isfinite(pv_arr)

    # link drops (minutes with the Modbus link down). Review round 2 (N10): durations drawn from
    # the measured heating-season outages (exogenous.link_outage_model) unless exo.link_durations
    # says otherwise; the same draw for every controller with the same seed.
    link = np.ones(n, bool)
    if exo.link_drops_per_day > 0:
        rng = np.random.default_rng([exo.seed, 404])
        durs = exo.link_durations
        if durs is None:
            from lab.sim.exogenous import link_outage_model
            durs = link_outage_model()[1]
        durs = np.asarray(durs or (1, 2), int)
        k_drops = rng.poisson(exo.link_drops_per_day * n / 1440.0)
        for k0 in rng.integers(0, n, k_drops):
            link[k0:k0 + int(durs[rng.integers(len(durs))])] = False
    if "long_outage" in variant_flags(variant):
        k0 = n_warm + (k_end - n_warm) // 2
        link[k0:min(k0 + int(LONG_OUTAGE_DAYS * 1440), k_end)] = False
    stale = None
    pending = {}

    # hot water
    reqs = sorted(exo.dhw_requests)
    jreq = 0
    active = None
    dhw_min = 0
    post_min = 99
    dhw_base = ret
    dhw_last_in = ret
    # pump-off sensor drift and purge (ASSUMED)
    pump_prev = True
    off_sens = ret
    purge_k = 0
    purge_from = ret
    storage_start = None

    # ---- recording ----------------------------------------------------------------------------
    rec = {k: np.zeros(n, np.float32) for k in REC_FIELDS}
    R = rec
    r_t_out, r_rh, r_ghi, r_outdoor, r_room, r_age = R["t_out"], R["rh"], R["ghi"], R["outdoor_s"], R["room_s"], R["room_age"]
    r_air, r_sens, r_slab, r_env, r_ret, r_sup = R["t_air"], R["t_sens"], R["t_slab"], R["t_env"], R["t_ret"], R["t_sup"]
    r_outlet, r_inlet, r_ctrl, r_sp, r_delta, r_quiet = R["outlet_s"], R["inlet_s"], R["t_ctrl"], R["sp"], R["delta"], R["quiet"]
    r_en, r_mode, r_comp, r_started, r_q, r_pout = R["enabled"], R["mode"], R["comp"], R["started"], R["q"], R["p_out"]
    r_pin, r_ptank, r_dem, r_dist, r_pv, r_writes, r_link = R["p_in"], R["p_tank"], R["dhw_dem"], R["dist"], R["pv"], R["writes"], R["link"]
    r_anchor = R["anchor"]
    r_pump = R["pump"]
    write_counts = {"setpoint": 0, "restart_delta": 0, "quiet": 0, "heating_enabled": 0}

    t_out_a = exo.t_out
    rh_a = exo.rh
    ghi_a = exo.ghi
    lh_a = exo.local_hour
    ob_a = exo.outdoor_base
    grid = exo.grid
    params = dict(params or {})
    ctx = dict(exo.context)
    if n_warm > 0:
        if reference is None:
            from lab.controllers.reference import ReferenceController
            reference = ReferenceController()
        ctrl = reference
        ctrl.reset(dict(ctx, target=target))
    else:
        ctrl = controller
        ctrl.reset(dict(ctx, **params))
    t_ctrl_s = 0.0
    n_ctrl_calls = 0
    p_idle_cache = {}

    for k in range(n):
        ts = float(grid[k])
        if k == n_warm:
            storage_start = float(cap @ x)
            minoff0 = unit.n_minoff_wait
        if k == n_warm and n_warm > 0:
            ctrl = controller
            ctrl.reset(dict(ctx, **params))
        if k == k_end and n_tail > 0:
            # common run-out: every controller hands the same weather to the plain reference, so
            # heat it left in (or took out of) the house is paid back the same way (review, C3)
            storage_end = float(cap @ x)
            from lab.controllers.reference import ReferenceController
            ctrl = ReferenceController()
            ctrl.reset(dict(ctx, target=target))
        # ---------------- observation ----------------
        t_amb = float(t_out_a[k])
        g = float(ghi_a[k])
        bias = min(g * (SUN_BIAS_RUN if comp_s else SUN_BIAS_IDLE), 6.0)
        outdoor_s = _q(float(ob_a[k]) + bias, OUTDOOR_RES)
        lk = bool(link[k])
        if lk:
            stale = (outdoor_s, outlet_s, inlet_s, sp, delta, quiet, enabled, comp_s, mode_s, pe, energy)
        u_out, u_outlet, u_inlet, u_sp, u_delta, u_quiet, u_en, u_comp, u_mode, u_pe, u_energy = stale
        pvk = float(pv_arr[k]) if has_pv[k] else None
        obs = Observation(
            time=dt.datetime.fromtimestamp(ts, UTC), local_hour=float(lh_a[k]), room=rep, room_age_min=rep_age,
            outdoor=u_out, outlet=u_outlet, inlet=u_inlet, setpoint=u_sp, restart_delta=u_delta, quiet=u_quiet,
            heating_enabled=u_en, compressor_on=u_comp, mode=u_mode, electric_kw=u_pe, energy_kwh=u_energy,
            target=target, forecast=fc.at(ts), pv_kw=pvk, minute=k - n_warm, link_ok=lk)
        t0c = time.perf_counter()
        cmd = ctrl.step(obs)
        t_ctrl_s += time.perf_counter() - t0c
        n_ctrl_calls += 1
        # ---------------- apply command ----------------
        nw = 0
        if cmd is not None and cmd != Command():
            for f in ("setpoint", "restart_delta", "quiet", "heating_enabled"):
                v = getattr(cmd, f)
                if v is not None:
                    pending[f] = v
        if pending and lk:
            for f, v in pending.items():
                if f == "setpoint":
                    v = clamp.setpoint(v)
                    if v != sp:
                        sp = v
                        nw += 1
                        if n_warm <= k < k_end:
                            write_counts[f] += 1
                elif f == "restart_delta":
                    v = clamp.delta(v)
                    if v != delta:
                        delta = v
                        nw += 1
                        if n_warm <= k < k_end:
                            write_counts[f] += 1
                elif f == "quiet":
                    v = bool(v)
                    if v != quiet:
                        quiet = v
                        nw += 1
                        if n_warm <= k < k_end:
                            write_counts[f] += 1
                else:
                    v = bool(v)
                    if v != enabled:
                        enabled = v
                        nw += 1
                        if n_warm <= k < k_end:
                            write_counts[f] += 1
            pending = {}
        # ---------------- hot water request ----------------
        if active is None and jreq < len(reqs) and reqs[jreq][0] <= k:
            active = max(int(reqs[jreq][1]), 1)
            jreq += 1
        dem = active is not None
        # ---------------- unit ----------------
        r = unit.step(sp, delta, ret, t_amb, float(rh_a[k]), quiet=quiet, heating_enabled=enabled, dhw_demand=dem)
        status = r.status
        umode = unit.mode
        if status == "dhw":
            if dhw_min == 0:
                dhw_base = ret
            dhw_min += 1
            active -= 1
            if active <= 0:
                active = None
        # ---------------- house ----------------
        if r.pump:
            x = Ad @ x
            x += bq * r.q_loop
            x += E[k]
        else:
            if off_sys is None:
                A0, B0, _, _ = H.matrices(hp, "heat", flow_lpm=0.0)
                off_sys = H.discretize(A0, B0, 1.0 / 60.0)
            x = off_sys[0] @ x + off_sys[1] @ U[k]
        if b_arr is not None:
            b_anchor = b_arr[k]
        else:
            qbar += a_q * (r.q_loop - qbar)
            b_anchor = anchor_tab[min(max(int(qbar * 20.0 + 0.5), 0), 160)]
        ret = float(x[iret]) + b_anchor
        y = float(c_room @ x)
        hb_age += 1
        if abs(y - rep) >= room_thr and hb_age >= room_min_gap:
            rep = _q(y, ROOM_RES)
            rep_age = 0.0
            hb_age = 0
        elif hb_age >= ROOM_HEARTBEAT_MIN:
            # periodic report: Home Assistant records it only when the rounded value changed
            hb_age = 0
            v_ = _q(y, ROOM_RES)
            if v_ != rep:
                rep = v_
                rep_age = 0.0
            else:
                rep_age += 1.0
        else:
            rep_age += 1.0
        # ---------------- unit sensors ----------------
        if status == "dhw":
            inlet_v = min(dhw_base + 0.95 * dhw_min, 50.0)
            outlet_v = inlet_v + 2.0 + 6.0 * (1.0 - math.exp(-dhw_min / 8.0))
            dhw_last_in = inlet_v
            post_min = 0
            mode_s = "dhw"
        else:
            if dhw_min > 0:
                dhw_min = 0
            post_min += 1
            if post_min <= 3:
                inlet_v = outlet_v = dhw_last_in - 0.3 * post_min
            elif post_min <= 7:
                f_ = (post_min - 3) / 4.0
                inlet_v = (1 - f_) * dhw_last_in + f_ * ret
                outlet_v = (1 - f_) * dhw_last_in + f_ * r.t_outlet
            else:
                inlet_v = ret
                outlet_v = r.t_outlet
            if umode in ("pre_dhw", "post_dhw"):
                mode_s = "dhw"
            else:
                mode_s = status
            # pump off: the unit's water sensors drift to the plant room; after the pump restarts
            # they blend back to the loop over the purge minutes (ASSUMED)
            if not r.pump:
                if pump_prev:
                    off_sens = inlet_v
                off_sens += (T_PLANT_ROOM - off_sens) / T_PLANT_TAU_MIN
                inlet_v = outlet_v = off_sens
                purge_k = 0
            elif not pump_prev:
                purge_k = up.purge_min
                purge_from = off_sens
            if r.pump and purge_k > 0:
                f_ = purge_k / (up.purge_min + 1.0)
                inlet_v = f_ * purge_from + (1 - f_) * inlet_v
                outlet_v = f_ * purge_from + (1 - f_) * outlet_v
                purge_k -= 1
        pump_prev = r.pump
        outlet_s = _q(outlet_v, WATER_RES)
        inlet_s = _q(inlet_v, WATER_RES)
        comp_s = r.compressor
        pe = r.p_outdoor
        energy += pe / 60.0
        # ---------------- record ----------------
        r_t_out[k] = t_amb
        r_rh[k] = rh_a[k]
        r_ghi[k] = g
        r_outdoor[k] = outdoor_s
        r_room[k] = rep
        r_age[k] = rep_age
        r_air[k] = x[ia]
        r_sens[k] = y
        r_slab[k] = x[islab]
        r_env[k] = x[ie]
        r_ret[k] = ret
        r_anchor[k] = b_anchor
        r_sup[k] = r.t_supply
        r_outlet[k] = outlet_s
        r_inlet[k] = inlet_s
        r_ctrl[k] = r.t_ctrl
        r_sp[k] = sp
        r_delta[k] = delta
        r_quiet[k] = quiet
        r_en[k] = enabled
        r_mode[k] = MODE_CODE[mode_s]
        r_comp[k] = comp_s
        r_started[k] = r.started
        r_q[k] = r.q_loop
        r_pout[k] = pe
        r_pin[k] = r.p_total - pe
        r_ptank[k] = r.p_tank_heater
        r_dem[k] = dem
        r_pv[k] = pvk if pvk is not None else np.nan
        r_writes[k] = nw
        r_link[k] = lk
        r_pump[k] = r.pump
    if n_tail > 0:
        storage_runout_end = float(cap @ x)
        tail = slice(k_end, n)
        runout = dict(runout_days=round(n_tail / 1440.0, 2), runout_elec_kwh=float(rec["p_out"][tail].sum() / 60.0),
                      runout_heat_kwh=float(rec["q"][tail].sum() / 60.0), storage_runout_end_kwh=storage_runout_end)
    else:
        storage_end = float(cap @ x)
        runout = {}
    r_dist = rec["dist"]
    r_dist[:] = exo.dist
    wall = time.perf_counter() - t_wall
    sl = slice(n_warm, k_end)
    out = {k: v[sl] for k, v in rec.items()}
    out["t"] = exo.grid[sl].astype(np.int64)
    out["local_hour"] = exo.local_hour[sl].astype(np.float32)
    meta = dict(controller=getattr(controller, "name", type(controller).__name__), scenario=exo.name,
                variant=variant, forecast=forecast, params=params, minutes=int(k_end - n_warm), warmup_minutes=int(n_warm),
                target=target, start_utc=dt.datetime.fromtimestamp(float(exo.grid[n_warm]), UTC).isoformat(),
                end_utc=dt.datetime.fromtimestamp(float(exo.grid[k_end - 1]) + 60, UTC).isoformat(),
                wall_s=round(wall, 2), controller_s=round(t_ctrl_s, 2), write_counts=write_counts,
                unit_counters=dict(starts=unit.n_starts, dhw=unit.n_dhw, defrosts=unit.n_defrost, surges=unit.n_oil,
                                   minoff_wait_min=unit.n_minoff_wait - minoff0, prestart_aborts=unit.n_prestart_abort),
                flow_lpm=up.flow_lpm, seed=exo.seed, link_drops_per_day=exo.link_drops_per_day,
                link_down_min=int((~link[n_warm:k_end]).sum()), forecast_mode=forecast_mode, return_anchoring=("off" if not anchor_on else "heat" if anchor_heat
                                                                       else "weather"),
                storage_start_kwh=storage_start, storage_end_kwh=storage_end, **runout,
                house_h_total_kw_per_k=float(hp.h_total))
    metrics = M.compute(out, meta)
    return dict(meta=meta, rec=out if record else None, metrics=metrics)


# ------------------------------------------------------------------------------------------
# self-check
# ------------------------------------------------------------------------------------------

def _self_check():
    from dataclasses import fields

    from lab.sim import scenarios as S
    from lab.controllers.fixed_setpoint import FixedSetpoint
    from lab.controllers.unit_curve import UnitCurve

    # 1) the observation carries only what Home Assistant shows
    names = [f.name for f in fields(Observation)]
    hidden = {"t_air", "t_slab", "slab", "air", "q_loop", "heat", "t_supply", "t_envelope"}
    assert not hidden & set(names), names

    # 2) command timing and write counting
    class Probe:
        name = "probe"

        def reset(self, params):
            self.seen = {}

        def step(self, obs):
            self.seen[obs.minute] = obs.setpoint
            if obs.minute in (10, 11, 12):
                return Command(setpoint=33.4)      # same register value three times -> one write
            if obs.minute == 20:
                return Command(setpoint=99.0)      # clamped to the register maximum
            if obs.minute == 30:
                return Command(restart_delta=4.2)  # rounds to the current value -> no write
            return Command()

    exo = S.steady(0.0, days=1)
    pr = Probe()
    r = run(pr, exo)
    rec = r["rec"]
    assert rec["sp"][9] != 33.0 and rec["sp"][10] == 33.0, (rec["sp"][9], rec["sp"][10])
    assert pr.seen[10] != 33.0 and pr.seen[11] == 33.0
    assert rec["sp"][20] == 55.0
    assert r["meta"]["write_counts"] == {"setpoint": 2, "restart_delta": 0, "quiet": 0, "heating_enabled": 0}, \
        r["meta"]["write_counts"]
    assert int(rec["writes"].sum()) == 2

    # 3) heating disabled: no space-heating heat, room falls
    class Off:
        name = "off"

        def reset(self, params):
            pass

        def step(self, obs):
            return Command(heating_enabled=False)

    r = run(Off(), S.steady(-5.0, days=2))
    assert float(np.abs(r["rec"]["q"]).max()) == 0.0
    assert r["rec"]["t_air"][-1] < r["rec"]["t_air"][0] - 1.0
    # review round 1: pump stops, sensors drift to the plant room, stored heat falls
    assert not r["rec"]["pump"].any()
    assert abs(float(r["rec"]["inlet_s"][-1]) - T_PLANT_ROOM) < 0.3, r["rec"]["inlet_s"][-1]
    assert r["metrics"]["storage_delta_kwh"] < -5.0 and "heating_off" in r["metrics"]["assumption_flags"]
    assert float(r["rec"]["p_in"].max()) < 0.05

    # 3b) a setpoint flapped every minute: pre-start is finished, not billed over and over
    class Flap:
        name = "flap"

        def reset(self, params):
            pass

        def step(self, obs):
            return Command(setpoint=55.0 if obs.minute % 2 == 0 else 20.0)

    r = run(Flap(), S.steady(0.0, days=1))
    m = r["metrics"]
    assert m["starts"] > 5 and m["heat_kwh"] > 5.0, (m["starts"], m["heat_kwh"])
    assert "writes_gt_48" in m["assumption_flags"] and "setpoint_range" in m["assumption_flags"]

    # 3c) review round 2: measured link outages and the long-outage check; commands wait
    from lab.sim.exogenous import link_outage_model
    rate, durs = link_outage_model()
    assert 0.1 < rate < 2.0 and len(durs) > 10, (rate, len(durs))
    exo_l = S.steady(0.0, days=6)
    exo_l.link_drops_per_day = 2.0
    r = run(pr, exo_l)
    assert r["meta"]["link_down_min"] > 0
    r = run(Probe(), S.steady(0.0, days=8), variant="long_outage")
    assert r["meta"]["link_down_min"] == int(LONG_OUTAGE_DAYS * 1440), r["meta"]["link_down_min"]
    assert r["meta"]["write_counts"]["setpoint"] == 2  # writes before the outage (it starts on day 4) apply
    # pessimistic forecast: larger errors than noisy, same seed
    from lab.sim.exogenous import Forecast
    import statistics
    fn, fp = Forecast("noisy", 1), Forecast("pessimistic", 1)
    ts0 = S.SCENARIOS["season"]
    t_iss = S.epoch(ts0.start) + 86400 * 30
    en = [h["outdoor"] for h in fn.at(t_iss)]
    ep = [h["outdoor"] for h in fp.at(t_iss)]
    tru = [h["outdoor"] for h in Forecast("perfect", 1).at(t_iss)]
    assert statistics.pstdev([a - b for a, b in zip(ep, tru)]) > statistics.pstdev([a - b for a, b in zip(en, tru)])

    # 4) determinism and bookkeeping on an archive week
    a = run(UnitCurve(), S.build("jan_cold"))
    b = run(UnitCurve(), S.build("jan_cold"))
    assert a["metrics"]["elec_kwh"] == b["metrics"]["elec_kwh"] and a["metrics"]["starts"] == b["metrics"]["starts"]
    m = a["metrics"]
    assert abs(m["heat_kwh"] - float(a["rec"]["q"].astype(float).sum()) / 60.0) < 0.05
    assert abs(m["elec_heat_kwh"] + m["elec_dhw_kwh"] - m["elec_kwh"]) < 0.01
    assert 1.5 < m["cop_space"] < 4.0, m["cop_space"]
    assert abs(m["elec_corr_kwh"] - (m["elec_kwh"] - m["storage_delta_kwh"] / m["cop_space"])) < 0.05
    print(f"jan_cold unit_curve: {m['elec_kwh_per_day']} kWh/d, COP {m['cop_space']}, starts/d {m['starts_per_day']}, "
          f"room {m['mean_air']}")

    # 5) speed: the season with a simple controller
    t0 = time.perf_counter()
    r = run(FixedSetpoint(), S.build("season"), params=dict(setpoint=31.0))
    dt_s = time.perf_counter() - t0
    print(f"season ({r['meta']['minutes'] + r['meta']['warmup_minutes']} minutes) in {dt_s:.1f} s")
    assert dt_s < 120
    print("simulator self-check OK")


if __name__ == "__main__":
    _self_check()
