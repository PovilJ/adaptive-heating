"""Economic MPC with an online-identified grey-box house model and COP map (stdlib only).

Strategy S8+S9 of docs/research/HEAT_PUMP_CONTROL_RESEARCH.md; design note and results:
docs/research/lab/controllers/econ_mpc.md.

Three layers:

1. **Estimator** (every 10 min). A linear 3-node house (room air + furniture, slab, envelope;
   capacities and couplings from the public house-model summary) augmented with four learned
   states: an additive heat disturbance on the air node `d` (kW, AR(1) around a learned base),
   the solar gain `g` (kW per kW/m2 of global irradiance), the offset `b` between the unit's
   inlet sensor and the model slab, and a loss trim `theta` (extra air heat per K of outdoor
   below 22 degC). A Kalman filter fuses the room thermometer (corrected for its sunlight glow),
   the inlet sensor and the heat put into the loop (measured from outlet - inlet). Slow learners
   on top: the multi-day level of `d` and its hour-of-day profile, a COP correction per
   outdoor/output cell from the metered electricity, the share of the planned heat that really
   arrives (defrosts, hot-water interruptions) per outdoor band, the unit's real maximum output,
   and a slow trim that keeps the long-run mean room on target.
2. **Planner** (every 60 min, and at once when the unit stops on its own). A 36-hour plan over
   24 blocks (1 h for the first 12 h, 2 h after) of heat output levels {off, minimum, 5, 6, 7,
   8.5 kW, flat out}, chosen by local search (single-block changes, neighbour swaps, heat
   transfers between blocks) to minimise electricity (COP map at the predicted supply
   temperature, defrost cost per kWh of air heat) + 0.54 kWh per K-hour of |room - target| +
   a start cost - the value of heat still stored in the house at the horizon end. The room
   response is linear in the heat, so every move costs O(horizon).
3. **Executor** (every minute). Translates the first block into registers without hot bursts:
   start with the smallest setpoint the firmware's restart rule accepts, then ride the setpoint
   near inlet + Q/(cp flow) (trimmed on the measured output) so the firmware's own error loop
   holds the planned output at the lowest supply that delivers it; stop by writing a setpoint
   2.6 K below the control sensor, then park at 25 degC with a 5 K restart hysteresis. Writes stay
   inside the recorded 25-39 degC range and a rolling 24-h budget (trims stop at 38, everything
   but stops at 45); a ride step is never reversed within 45 min.

Fail-safe: link down -> no writes, the estimator assumes the last steady output; room value
older than 90 min -> it counts less with age, older than 6 h (dead or frozen thermometer) ->
the learned states and trims freeze and a daily heat budget (delivered loop heat against a
weather relation learned on fully observed days) steers the model's free-gain base;
forecast missing -> persistence of the unit's outdoor sensor; DHW and defrost -> no writes,
heat accounting frozen; heating switched off by the user -> hands off; implausible estimate ->
the estimator restarts from the sensors; planner error -> a low weather curve for two hours.

Review fixes (docs/research/lab/controllers/econ_mpc.md, 'Review fixes'): dead-thermometer
fail-safe, write budget and anti-saw-tooth, start cost 0.7 kWh + 0.3 per 10 K below 0 degC,
a cold-side comfort hinge (0.5 kWh/K-h below aim - 0.5 K), 25-39 degC write range, user
heating switch respected.
"""
from __future__ import annotations

import math

from lab.sim.interface import Command, Observation

# ---------------------------------------------------------------------------------------------
# public house / unit knowledge (docs/research/lab/HOUSE_MODEL.md, UNIT_MODEL.md)
# ---------------------------------------------------------------------------------------------
CP_FLOW = 2.02          # kW per K of loop delta-T at the documented 29 L/min
PARK_SP = 25.0          # lowest setpoint ever written to the real unit
SP_MAX = 39             # highest setpoint ever written to the real unit (flat-out requests stop here)
T_GROUND = 10.0
GLOW = 0.8              # K per kW/m2 of global irradiance on the thermometer (house model fit)
PV_PER_GHI = 8.9        # kW of PV per kW/m2 of global irradiance (lab README)
SUP_PER_KW = 0.70       # K of supply above the slab-side water per kW (effectiveness 0.71)
RET_PER_KW = 0.20       # K of return above the slab-side water per kW
NZ = 7                  # estimator states: air, slab, envelope, d, solar gain, water offset, loss trim


def _interp(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            f = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + f * (ys[i] - ys[i - 1])
    return ys[-1]


# steady COP at 6 kW, W30 (UNIT_MODEL.md 7.2, smooth in outdoor temperature)
_COP6_T = (-20.0, -15.0, -7.0, 0.0, 2.0, 4.0, 6.0, 7.0, 10.0, 15.0)
_COP6_V = (2.55, 2.85, 3.33, 3.81, 4.15, 4.60, 5.20, 5.47, 5.55, 5.60)
# air heat drawn per defrost, kWh (UNIT_MODEL.md section 8), log-linear
_DFK_T = (-15.0, -1.0, 1.0, 3.0, 5.0, 8.0, 10.0)
_DFK_V = (7.0, 7.25, 9.9, 17.0, 25.0, 60.0, 400.0)
_DFK_LV = tuple(math.log(v) for v in _DFK_V)


def cop_model(t_out, q, t_sup, pl_k=0.035):
    """Steady COP of the outdoor unit (central model shape, part-load curvature pl_k; scaled online)."""
    c = _interp(t_out, _COP6_T, _COP6_V)
    if q < 6.0:
        pl = 1.0 - pl_k * (6.0 - q) ** 2
    else:
        pl = 1.0 + 0.015 * min(q - 6.0, 3.0)
    return max(c * max(pl, 0.45) * math.exp(-0.031 * (t_sup - 30.0)), 1.2)


def q_min(t_out):
    return CP_FLOW * min(max(1.8 + 0.05 * t_out, 1.4), 2.4)


def q_max(t_out):
    """Maximum heat (manufacturer table x 9.5 kW: 7.0 kW at -15, 9.8 at 0, 10.8 at +7 degC)."""
    return _interp(t_out, (-25.0, -15.0, 0.0, 7.0), (5.6, 7.0, 9.8, 10.8))


def defrost_per_kwh_air(t_out):
    """Defrosts per kWh of air heat."""
    if t_out >= 10.0:
        return 0.0
    return 1.0 / math.exp(_interp(t_out, _DFK_T, _DFK_LV))


# ---------------------------------------------------------------------------------------------
# small dense linear algebra (lists of lists)
# ---------------------------------------------------------------------------------------------
def _mm(a, b):
    bt = list(zip(*b))
    return [[sum(x * y for x, y in zip(r, c)) for c in bt] for r in a]


def _mv(a, v):
    return [sum(x * y for x, y in zip(r, v)) for r in a]


def _eye(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _expm(a):
    n = len(a)
    norm = max(sum(abs(x) for x in r) for r in a)
    s = 0
    while norm > 0.5:
        norm /= 2.0
        s += 1
    sc = 1.0 / (2 ** s)
    a = [[x * sc for x in r] for r in a]
    res = _eye(n)
    term = _eye(n)
    for k in range(1, 12):
        term = [[x / k for x in r] for r in _mm(term, a)]
        res = [[x + y for x, y in zip(r1, r2)] for r1, r2 in zip(res, term)]
    for _ in range(s):
        res = _mm(res, res)
    return res


def discretize(A, B, dt):
    """Exact zero-order-hold discretisation: returns (Ad, Bd)."""
    n, m = len(A), len(B[0])
    M = [[0.0] * (n + m) for _ in range(n + m)]
    for i in range(n):
        for j in range(n):
            M[i][j] = A[i][j] * dt
        for j in range(m):
            M[i][n + j] = B[i][j] * dt
    E = _expm(M)
    return [r[:n] for r in E[:n]], [r[n:] for r in E[:n]]


class HouseModel:
    """x = [air, slab, envelope]; u = [q_loop, t_out, t_ground, q_air] (hours, kW, kWh/K)."""

    def __init__(self, ca=4.3, cs=4.4, ce=74.0, k_sa=0.43, k_ae=1.35, k_ao=0.05, k_eo=0.064, k_sg=0.092):
        A = [[-(k_sa + k_ae + k_ao) / ca, k_sa / ca, k_ae / ca],
             [k_sa / cs, -(k_sa + k_sg) / cs, 0.0],
             [k_ae / ce, 0.0, -(k_ae + k_eo) / ce]]
        B = [[0.0, k_ao / ca, 0.0, 1.0 / ca],
             [1.0 / cs, 0.0, k_sg / cs, 0.0],
             [0.0, k_eo / ce, 0.0, 0.0]]
        self.A, self.B = A, B
        self.h_room = k_ao + 1.0 / (1.0 / k_ae + 1.0 / k_eo) + 1.0 / (1.0 / k_sa + 1.0 / k_sg)
        self.k_sa, self.k_sg = k_sa, k_sg
        self.k_ao, self.k_ae, self.k_eo = k_ao, k_ae, k_eo
        self.d10 = discretize(A, B, 1.0 / 6.0)
        self.d60 = discretize(A, B, 1.0)

    def steady(self, t_air, t_out, q_air):
        """Slab and envelope at steady state for a given air temperature; and the loop heat."""
        te = (self.k_ae * t_air + self.k_eo * t_out) / (self.k_ae + self.k_eo)
        # air balance: k_sa (ts - ta) + k_ae (te - ta) + k_ao (to - ta) + q_air = 0
        ts = t_air - (self.k_ae * (te - t_air) + self.k_ao * (t_out - t_air) + q_air) / self.k_sa
        q = self.k_sa * (ts - t_air) + self.k_sg * (ts - T_GROUND)
        return ts, te, q


# ---------------------------------------------------------------------------------------------
# controller
# ---------------------------------------------------------------------------------------------
class EconMPC:
    name = "econ_mpc"

    def reset(self, params: dict) -> None:
        g = lambda k, d: float(params.get(k, d))  # noqa: E731
        self.w_comfort = g("w_comfort", 0.54)     # kWh per K-hour of |air - target|
        self.c_start = g("c_start", 0.7)          # kWh per start in the plan (review: fewer cycles)
        self.replan_min = int(g("replan_min", 60))
        self.min_run = g("min_run", 60.0)
        self.min_off = g("min_off", 45.0)
        self.max_starts_day = g("max_starts_day", 7)
        self.ride_every = g("ride_every", 20.0)
        self.delta_reg = g("restart_delta", 5.0)
        self.levels = tuple(float(x) for x in str(params.get("levels", "5.0,6.0,7.0,8.5")).replace(";", ",").split(","))
        self.d_tau_h = g("d_tau_h", 2.7)          # decay of the current disturbance anomaly (AR(1) phi 0.69/h)
        self.sig_d = g("sig_d", 0.25)             # kW per 10 min, disturbance random walk
        self.sig_g = g("sig_g", 0.05)             # solar gain random walk per 10 min
        self.r_room = g("r_room", 0.07) ** 2
        self.r_inlet = g("r_inlet", 0.3) ** 2
        self.sig_b = g("sig_b", 0.02)             # K per 10 min, water-offset random walk
        self.sig_th = g("sig_th", 0.0004)         # kW/K per 10 min, weather-proportional heat
        self.d_slow_days = g("d_slow_days", 5.0)
        self.mean_fix = g("mean_fix", 0.0)        # per day, per-band aim correction (sun-free hours)
        self.mean_fix_global = g("mean_fix_global", 0.07)  # per day: long-run mean air on target
        self.transfer_span = int(g("transfer_span", 8))  # slots ahead for heat-transfer moves
        self.store_credit = g("store_credit", 0.95)  # value of heat left in the house at the horizon end
        # review fixes
        self.c_start_cold = g("c_start_cold", 0.3)  # extra kWh per start per 10 K of outdoor below 0 degC
        self.w_floor = g("w_floor", 0.5)          # extra kWh per K-hour below aim - floor_margin
        self.floor_margin = g("floor_margin", 0.5)
        self.flat_gap = g("flat_gap", 1.5)        # discrete levels within this of the cap merge into flat out
        self.ride_rev_min = g("ride_rev_min", 45.0)  # no ride step against the previous one within this
        self.write_soft = int(g("write_soft", 38))  # rolling-24 h writes: above this only start/stop/park
        self.write_hard = int(g("write_hard", 45))  # ... above this only stop writes
        self.room_stale_min = g("room_stale_min", 360.0)  # older room value: thermometer treated as dead
        self.room_trust_min = g("room_trust_min", 90.0)   # older than this: room noise inflated with age
        self.budget_gain = g("budget_gain", 0.5)
        self.stop_margin = g("stop_margin", 2.6)  # K below the control sensor for a stop write
        self.sp_min = g("sp_min", PARK_SP)        # lowest setpoint written (recorded range: 25)
        self.flat_hold = g("flat_hold", 1.0)
        self.pl_k = g("pl_k", 0.035)              # part-load COP curvature below 6 kW
        self.park_backup = g("park_backup", 1.0) > 0
        self.park_margin = g("park_margin", 1.5)      # flat out: no trim while the request is within this  # room-dead mode: daily heat-budget integral gain
        self.slot_h = tuple([1] * 12 + [2] * 12)
        self.horizon = sum(self.slot_h)
        self.model = HouseModel()
        self._build_responses()
        # estimator state z = [ta, ts, te, d, g, b, theta]
        self.z = None
        self.P = None
        self.q_acc = 0.0
        self.n_acc = 0
        self.ghi_acc = 0.0
        self.tout_acc = 0.0
        self.d_slow = 0.0
        self.d_prof = [0.0] * 24
        self.b_w = None                           # inlet (slab-side water) minus model slab, K
        self.cop_cell = {}                        # (t band, q band) -> measured / model electricity
        self.cop_acc = [0.0, 0.0, None]
        self.eta_band = [1.0] * 5                 # delivered / planned heat per outdoor band
        self.cap_band = [None] * 5                # maximum heat seen when running flat out
        self.eta_acc = [0.0, 0.0, 0]
        # unit bookkeeping
        self.since_dhw = 999
        self.since_defrost = 999
        self.run_min = 0
        self.off_min = 999
        self.was_on = False
        self.start_minutes = []
        self.last_write = -999
        self.t_avg = None
        self.fc_bias = 0.0
        # plan
        self.plan = None
        self.plan_minute = -999
        self.plan_q0 = 0.0
        self.want_on = False
        self.q_avg = 0.0
        self.was_on_link = False
        self.mode_link = "idle"
        self.ride_q_tgt = None
        self.aim_band = [0.0] * 5
        self.aim_acc = [[0.0, 0] for _ in range(5)]
        self.n_day = 0
        self.aim_glob = 0.0
        self.glob_acc = [0.0, 0]
        self.fallback_until = -1
        self.write_minutes = []
        self.delta_tries = 0                      # restart_delta writes not (yet) taken by the unit
        self.delta_next = -1                      # earliest minute for the next restart_delta try
        self.ride_dir = 0
        self.ride_dir_min = -999
        self.room_dead_min = 0                    # minutes the thermometer has counted as dead
        self.day_acc = [0.0, 0.0, 0.0, 0, 0]      # loop heat kWh, outdoor sum, ghi sum, minutes, room-ok minutes
        self.hb = None                            # heat-budget relation: RLS on [1, 22 - t_out, ghi]
        self.hb_P = None
        self.budget_fix = 0.0                     # kW added to the air-gain base while the room is dead
        self.hb_n = 0
        self._air_acc = 0.0
        self.stats = {"plans": 0, "fallback": 0}
        self.debug = [] if params.get("debug") else None

    # ------------------------------------------------------------------ model responses
    def _build_responses(self):
        Ad, Bd = self.model.d60
        n = self.horizon
        # 1 kW of loop heat during hour 0: air (hour average) and slab (hour end) for each hour
        x = [Bd[i][0] for i in range(3)]
        prev_air = 0.0
        h_air, h_slab = [], []
        for _ in range(n):
            h_air.append(0.5 * (prev_air + x[0]))
            h_slab.append(x[1])
            prev_air = x[0]
            x = _mv(Ad, x)
        self.h_air, self.h_slab = h_air, h_slab
        self.slot_start = []
        s = 0
        for d in self.slot_h:
            self.slot_start.append(s)
            s += d
        # response of each slot (1 kW for its whole duration), averaged on the slot grid
        S = len(self.slot_h)
        self.w_grid = [float(d) for d in self.slot_h]
        self.R_air, self.R_slab = [], []
        for j, d in enumerate(self.slot_h):
            s0 = self.slot_start[j]
            ra = [0.0] * n
            rs = [0.0] * n
            for i in range(s0, s0 + d):
                for t in range(i, n):
                    ra[t] += h_air[t - i]
                    rs[t] += h_slab[t - i]
            ga = [sum(ra[s:s + dd]) / dd for s, dd in zip(self.slot_start, self.slot_h)]
            gs = [sum(rs[s:s + dd]) / dd for s, dd in zip(self.slot_start, self.slot_h)]
            self.R_air.append(ga)
            self.R_slab.append(gs)
        # heat still stored in the house at the horizon end, per kW of slot heat (kWh)
        caps = (4.3, 4.4, 74.0)
        st = []
        for i in range(n):
            x = [Bd[k][0] for k in range(3)]
            for _ in range(n - 1 - i):
                x = _mv(Ad, x)
            st.append(sum(c * v for c, v in zip(caps, x)))
        self.R_store = [sum(st[i] for i in range(self.slot_start[j], self.slot_start[j] + d))
                        for j, d in enumerate(self.slot_h)]
        assert S == len(self.R_air)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _ghi_now(obs):
        if obs.pv_kw is not None:
            return max(obs.pv_kw, 0.0) / PV_PER_GHI
        fc = obs.forecast
        if fc:
            return max(fc[0].get("ghi", 0.0) or 0.0, 0.0) / 1000.0
        return 0.0

    def _q_air_base(self, hour):
        return 0.3 + self.d_slow + self.budget_fix + self.d_prof[int(hour) % 24]

    def _room_ok(self, obs):
        return obs.room is not None and obs.room_age_min < self.room_stale_min

    def _init_state(self, obs):
        ta = obs.room if obs.room is not None else obs.target
        t_out = obs.outdoor
        ts, te, _ = self.model.steady(ta, t_out, 0.3)
        bw = obs.inlet - ts if (not obs.compressor_on and obs.mode in ("idle", "heat")) else 0.0
        gs, th = 5.0, 0.0
        if self.z is not None:   # restart after an implausible estimate: keep what was learned
            gs, bw, th = self.z[4], self.z[5], self.z[6]
            if obs.link_ok and not obs.compressor_on and obs.mode in ("idle", "heat"):
                ts = obs.inlet - bw
        self.z = [ta, ts, te, 0.0, gs, bw, th]
        self.P = [[0.0] * NZ for _ in range(NZ)]
        for i, v in enumerate((0.05, 1.0, 0.5, 0.5, 4.0, 1.0, 0.02 ** 2)):
            self.P[i][i] = v
        self.b_w = bw

    # ------------------------------------------------------------------ estimator
    def _kf_update(self, zn, Pn, i_state, y, h_const, r):
        """Scalar measurement y = z[i_state] (+ z[5] if i_state == 1) + h_const."""
        if i_state == 1:
            pred = zn[1] + zn[5] + h_const
            ph = [Pn[i][1] + Pn[i][5] for i in range(NZ)]
            s = ph[1] + ph[5] + r
        else:
            pred = zn[i_state] + h_const
            ph = [Pn[i][i_state] for i in range(NZ)]
            s = ph[i_state] + r
        k = [p / s for p in ph]
        innov = max(min(y - pred, 1.5), -1.5)
        zn = [zn[i] + k[i] * innov for i in range(NZ)]
        Pn = [[Pn[i][j] - k[i] * ph[j] for j in range(NZ)] for i in range(NZ)]
        return zn, Pn

    def _estimate(self, obs, hour):
        Ad, Bd = self.model.d10
        z = self.z
        q = self.q_acc / max(self.n_acc, 1)
        ghi = self.ghi_acc / max(self.n_acc, 1)
        t_out = self.tout_acc / max(self.n_acc, 1)
        # predict
        x = z[:3]
        d, gs, th = z[3], z[4], z[6]
        dt_o = t_out - 22.0
        u = (q, t_out, T_GROUND, 0.3 + d + gs * ghi + th * dt_o)
        xn = [Ad[i][0] * x[0] + Ad[i][1] * x[1] + Ad[i][2] * x[2] + Bd[i][0] * u[0] + Bd[i][1] * u[1]
              + Bd[i][2] * u[2] + Bd[i][3] * u[3] for i in range(3)]
        # d: AR(1) anomaly around its learned base
        base = self._q_air_base(hour) - 0.3
        a = math.exp(-(1.0 / 6.0) / 24.0)
        F = [[Ad[i][0], Ad[i][1], Ad[i][2], Bd[i][3], Bd[i][3] * ghi, 0.0, Bd[i][3] * dt_o] for i in range(3)]
        F.append([0.0, 0.0, 0.0, a, 0.0, 0.0, 0.0])
        F.append([0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0])
        F.append([0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0])
        F.append([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])
        zn = xn + [base + a * (d - base), gs, z[5], th]
        Pn = _mm(_mm(F, self.P), [list(r) for r in zip(*F)])
        room_ok = self._room_ok(obs)
        if room_ok:
            qn = (0.003 ** 2, 0.01 ** 2, 0.003 ** 2, self.sig_d ** 2, self.sig_g ** 2 if ghi > 0.02 else 0.0,
                  self.sig_b ** 2, self.sig_th ** 2)
        else:
            qn = (0.003 ** 2, 0.01 ** 2, 0.003 ** 2, 0.0, 0.0, 0.0, 0.0)
        for i in range(NZ):
            Pn[i][i] += qn[i]
        frozen = zn[3:]
        # room thermometer, corrected for its sunlight glow; an old value (a steady room or a dead
        # battery: Home Assistant cannot tell) counts less and less, and not at all after 6 h
        if room_ok:
            age_x = max(obs.room_age_min - self.room_trust_min, 0.0) / 60.0
            r = self.r_room + (0.06 * age_x) ** 2
            zn, Pn = self._kf_update(zn, Pn, 0, obs.room - GLOW * self._ghi_now(obs), 0.0, r)
        # loop water: the inlet sensor sees the slab-side water (+ an offset learned as a state)
        if obs.link_ok and self.since_dhw > 30 and obs.mode in ("idle", "heat"):
            if not obs.compressor_on and self.off_min > 30:
                zn, Pn = self._kf_update(zn, Pn, 1, obs.inlet, 0.0, self.r_inlet)
            elif obs.compressor_on and self.run_min > 30 and self.since_defrost > 15 and q > 0.5:
                zn, Pn = self._kf_update(zn, Pn, 1, obs.inlet, RET_PER_KW * q, self.r_inlet)
        if not room_ok:
            # without the room the learned states are unobservable: the inlet may correct the slab
            # only, and the disturbance relaxes to its learned base
            zn = zn[:3] + [frozen[0]] + list(frozen[1:])
        zn[4] = min(max(zn[4], 0.0), 15.0)
        zn[3] = min(max(zn[3], -4.0), 4.0)
        zn[5] = min(max(zn[5], -5.0), 5.0)
        zn[6] = min(max(zn[6], -0.08), 0.08)
        self.z, self.P = zn, Pn
        self.b_w = zn[5]
        # slow learners of the disturbance: daily level and hour-of-day profile (frozen while the
        # thermometer is dead: they are learned against it)
        if room_ok:
            self.d_slow += (zn[3] - self.d_slow - self.budget_fix) * (1.0 / (6 * 24 * self.d_slow_days))
            h = int(hour) % 24
            anomaly = zn[3] - self.d_slow - self.budget_fix - self.d_prof[h]
            self.d_prof[h] += 0.05 * anomaly
            m = sum(self.d_prof) / 24.0
            self.d_prof = [v - m for v in self.d_prof]
        self.q_acc = self.ghi_acc = self.tout_acc = 0.0
        self.n_acc = 0

    @staticmethod
    def _eta_band(t_out):
        return 0 if t_out < -8 else 1 if t_out < -3 else 2 if t_out < 2 else 3 if t_out < 6 else 4

    def _q_cap(self, t_out):
        """Maximum heat: the manufacturer table until the unit has shown its own cap here."""
        c = self.cap_band[self._eta_band(t_out)]
        return q_max(t_out) if c is None else min(max(c, 0.8 * q_max(t_out)), 1.5 * q_max(t_out))

    def _eta(self, t_out):
        return self.eta_band[self._eta_band(t_out)]

    @staticmethod
    def _cell(t_out, q):
        tb = 0 if t_out < -5 else 1 if t_out < 2 else 2 if t_out < 6 else 3
        return tb, 0 if q < 4.8 else 1

    def _cop_ratio(self, t_out, q):
        return self.cop_cell.get(self._cell(t_out, q), 1.0)

    # ------------------------------------------------------------------ forecast handling
    def _weather(self, obs):
        """Hourly outdoor and GHI (kW/m2) for the horizon, starting now."""
        n = self.horizon
        fc = obs.forecast
        if not fc or len(fc) < 6:
            t = self.t_avg if self.t_avg is not None else obs.outdoor
            return [t] * n, [0.0] * n, None
        # fc[i] describes the hour ending at fc[i]['time']; value at its mid-point, linear between
        off = (fc[0]["time"] - obs.time).total_seconds() / 3600.0 - 0.5   # mid of fc[0] from now
        m = len(fc)
        vt = [h["outdoor"] for h in fc]
        vg = [max(h.get("ghi", 0.0) or 0.0, 0.0) / 1000.0 for h in fc]
        out_t, out_g, out_rh = [], [], []
        for k in range(n):
            tm = k + 0.5
            x = tm - off
            i = int(math.floor(x))
            if i < 0:
                a0, a1, f = 0, 0, 0.0
            elif i >= m - 1:
                a0, a1, f = m - 1, m - 1, 0.0
            else:
                a0, a1, f = i, i + 1, x - i
            out_t.append(vt[a0] + f * (vt[a1] - vt[a0]) + self.fc_bias * math.exp(-tm / 6.0))
            out_g.append(vg[a0] + f * (vg[a1] - vg[a0]))
        return out_t, out_g, None

    # ------------------------------------------------------------------ planner
    def _plan(self, obs, hour):
        n = self.horizon
        S = len(self.slot_h)
        ss, sh = self.slot_start, self.slot_h
        tw, gw, _ = self._weather(obs)
        Ad, Bd = self.model.d60
        z = self.z
        x = z[:3]
        base_now = self.d_slow + self.d_prof[int(hour) % 24]
        anom = z[3] - base_now
        decay = math.exp(-1.0 / self.d_tau_h)
        air_h, slab_h = [], []
        prev_air = x[0]
        for k in range(n):
            qa = (self._q_air_base(hour + k + 0.5) + anom * decay ** (k + 0.5) + z[4] * gw[k]
                  + z[6] * (tw[k] - 22.0))
            u = (0.0, tw[k], T_GROUND, qa)
            x = [Ad[i][0] * x[0] + Ad[i][1] * x[1] + Ad[i][2] * x[2] + Bd[i][1] * u[1] + Bd[i][2] * u[2]
                 + Bd[i][3] * u[3] for i in range(3)]
            air_h.append(0.5 * (prev_air + x[0]))
            slab_h.append(x[1])
            prev_air = x[0]
        free_slab = [sum(slab_h[s0:s0 + d]) / d for s0, d in zip(ss, sh)]
        bw = self.b_w or 0.0
        # level sets and slot weather
        lv_sets, t_slot = [], []
        for j in range(S):
            t = sum(tw[ss[j]:ss[j] + sh[j]]) / sh[j]
            t_slot.append(t)
            qm, qx = q_min(t), self._q_cap(t)
            # a discrete level close to the cap merges into flat out (one executor mode, no hunting
            # between the two setpoint rules)
            lv = [0.0, qm] + [v for v in self.levels if qm + 0.4 < v < qx - self.flat_gap]
            if qx > lv[-1] + 0.4:
                lv.append(qx)                               # flat out (the executor asks for more)
            lv_sets.append(lv)
        # aim: the target, trimmed per outdoor band by the slow bias learner
        aims = [obs.target + self.aim_glob + self.aim_band[self._eta_band(t)] for t in t_slot]
        aim = aims[0]
        free_err = [sum(air_h[s0:s0 + d]) / d - a for s0, d, a in zip(ss, sh, aims)]
        # warm start from the previous plan, shifted by the time since it was made
        Q = [0.0] * S
        if self.plan is not None:
            shift_h = (obs.minute - self.plan_minute) / 60.0
            for j in range(S):
                hmid = ss[j] + shift_h
                for jj in range(S):
                    if ss[jj] <= hmid < ss[jj] + sh[jj]:
                        Q[j] = self._nearest(self.plan[jj], lv_sets[j])
                        break
        running = obs.compressor_on and obs.mode in ("heat", "defrost")
        # net heat actually delivered per kW planned (defrosts, hot-water interruptions, riding
        # error), learned per outdoor band
        eta = [self._eta(t) for t in t_slot]
        R_air = [[e * v for v in r] for e, r in zip(eta, self.R_air)]
        # electricity per slot and level; supply from the slab trajectory of the warm start
        slab = list(free_slab)
        for j in range(S):
            if Q[j]:
                r, qj = self.R_slab[j], Q[j] * eta[j]
                for t in range(j, S):
                    slab[t] += qj * r[t]
        E = []
        unit = []
        for j in range(S):
            t, dur = t_slot[j], sh[j]
            ts = slab[j] + bw
            row = [0.0]
            best_u = 9.0
            for qv in lv_sets[j][1:]:
                cop = cop_model(t, qv, ts + SUP_PER_KW * qv, self.pl_k)
                p = qv / cop * self._cop_ratio(t, qv)
                frost = (qv - p) * defrost_per_kwh_air(t) * (qv / 5.0) ** 0.28
                e = p + frost * (0.13 + 0.9 / cop)
                row.append(dur * e)
                best_u = min(best_u, e / qv)
            E.append(row)
            if j >= S // 2:
                unit.append(best_u)
        # heat left in the house at the horizon end is credited at the price of later heat
        c_heat = self.store_credit * sum(unit) / len(unit)
        for j in range(S):
            cr = c_heat * self.R_store[j] * eta[j]
            E[j] = [e - cr * qv for e, qv in zip(E[j], lv_sets[j])]
        # start cost, higher in the cold where the start/defrost interplay is least validated
        cs_slot = [self.c_start + self.c_start_cold * max(-t, 0.0) / 10.0 for t in t_slot]
        Q = self._search(Q, lv_sets, E, free_err, running, R_air, cs_slot)
        if self.debug is not None:
            pred = list(free_err)
            for j in range(S):
                for t in range(j, S):
                    pred[t] += Q[j] * R_air[j][t]
            self.debug.append((obs.minute, aim, pred, list(Q)))
        self.plan = Q
        self.plan_minute = obs.minute
        self.stats["plans"] += 1
        return Q[0]

    @staticmethod
    def _nearest(v, lv):
        if v <= 0:
            return 0.0
        return min(lv[1:], key=lambda x: abs(x - v))

    def _search(self, Q, lv_sets, E, free_err, running, R, cs_slot):
        """Local search over output levels per slot (moves: change one slot, swap neighbours)."""
        S = len(Q)
        w = self.w_comfort
        W = self.w_grid
        fm = self.floor_margin
        kf = self.w_floor / w

        if kf > 0:
            def cf(v):
                """|error| plus an extra hinge below the floor (cold side hurts more)."""
                return -v + kf * (-v - fm) if v < -fm else abs(v)
        else:
            cf = abs
        err = list(free_err)
        for j in range(S):
            if Q[j]:
                r, qj = R[j], Q[j]
                for t in range(j, S):
                    err[t] += qj * r[t]
        idx = [lv_sets[j].index(Q[j]) if Q[j] in lv_sets[j] else 0 for j in range(S)]
        on = [i > 0 for i in idx]

        def n_starts(a, b):
            """start cost among slots a..b (inclusive) given `on`."""
            c = 0.0
            prev = running if a == 0 else on[a - 1]
            for k in range(a, min(b, S - 1) + 1):
                if on[k] and not prev:
                    c += cs_slot[k]
                prev = on[k]
            return c

        for _ in range(5):
            improved = False
            for j in range(S):
                cur = idx[j]
                lv = lv_sets[j]
                qc = lv[cur]
                rj = R[j][j:]
                wj = W[j:]
                ej = err[j:]
                st_cur = n_starts(j, j + 1)
                base = w * sum(wt * cf(e) for e, wt in zip(ej, wj)) + E[j][cur] + st_cur
                best_k, best_v = cur, base - 1e-6
                nl = len(lv)
                if cur == 0:
                    cands = range(1, nl)
                else:
                    cands = {0, max(cur - 1, 1), min(cur + 1, nl - 1)}
                for k in cands:
                    if k == cur:
                        continue
                    dq = lv[k] - qc
                    on[j] = k > 0
                    c = w * sum(wt * cf(e + dq * r) for e, r, wt in zip(ej, rj, wj)) + E[j][k] + n_starts(j, j + 1)
                    if c < best_v:
                        best_k, best_v = k, c
                on[j] = best_k > 0
                if best_k != cur:
                    dq = lv[best_k] - qc
                    for t in range(j, S):
                        err[t] += dq * R[j][t]
                    idx[j] = best_k
                    improved = True
            # block shifts: swap neighbouring equal-length slots where one is on and one off
            for j in range(S - 1):
                if self.slot_h[j] != self.slot_h[j + 1] or on[j] == on[j + 1]:
                    continue
                qa, qb = lv_sets[j][idx[j]], lv_sets[j + 1][idx[j + 1]]
                ka = self._nearest(qb, lv_sets[j]) if qb > 0 else 0.0
                kb = self._nearest(qa, lv_sets[j + 1]) if qa > 0 else 0.0
                ia, ib = lv_sets[j].index(ka), lv_sets[j + 1].index(kb)
                da, db = ka - qa, kb - qb
                ra, rb = R[j], R[j + 1]
                old = (w * sum(W[t] * cf(err[t]) for t in range(j, S)) + E[j][idx[j]] + E[j + 1][idx[j + 1]]
                       + n_starts(j, j + 2))
                new_err = [err[t] + da * ra[t] + db * rb[t] for t in range(j, S)]
                on[j], on[j + 1] = ia > 0, ib > 0
                new = (w * sum(W[t] * cf(v) for t, v in zip(range(j, S), new_err)) + E[j][ia] + E[j + 1][ib]
                       + n_starts(j, j + 2))
                if new < old - 1e-6:
                    err[j:] = new_err
                    idx[j], idx[j + 1] = ia, ib
                    improved = True
                else:
                    on[j], on[j + 1] = not on[j], not on[j + 1]
            # transfers: one level more in slot j and one less in a later slot k (heat earlier),
            # or the reverse; single-slot moves cannot see that trade
            for j in range(min(S - 1, 12)):
                for k in range(j + 1, min(S, j + 1 + self.transfer_span)):
                    for sgn in (1, -1):
                        ia = self._step_idx(idx[j], sgn, len(lv_sets[j]))
                        ib = self._step_idx(idx[k], -sgn, len(lv_sets[k]))
                        if ia is None or ib is None:
                            continue
                        da = lv_sets[j][ia] - lv_sets[j][idx[j]]
                        db = lv_sets[k][ib] - lv_sets[k][idx[k]]
                        rj, rk = R[j], R[k]
                        old = (w * sum(W[t] * cf(err[t]) for t in range(j, S)) + E[j][idx[j]] + E[k][idx[k]]
                               + n_starts(j, k + 1))
                        new_err = [err[t] + da * rj[t] + db * rk[t] for t in range(j, S)]
                        oj, ok = on[j], on[k]
                        on[j], on[k] = ia > 0, ib > 0
                        new = (w * sum(W[t] * cf(v) for t, v in zip(range(j, S), new_err)) + E[j][ia] + E[k][ib]
                               + n_starts(j, k + 1))
                        if new < old - 1e-6:
                            err[j:] = new_err
                            idx[j], idx[k] = ia, ib
                            improved = True
                        else:
                            on[j], on[k] = oj, ok
            if not improved:
                break
        return [lv_sets[j][idx[j]] for j in range(S)]

    @staticmethod
    def _step_idx(i, sgn, n):
        """Index one output level up (sgn 1, from off to about 5 kW) or down (sgn -1)."""
        if sgn > 0:
            if i == 0:
                return 2 if n > 2 else 1
            return i + 1 if i + 1 < n else None
        return None if i == 0 else i - 1

    # ------------------------------------------------------------------ executor helpers
    def _write_sp(self, obs, sp, kind="ride"):
        """One setpoint write, inside the recorded 25-39 degC range and the rolling-24 h budget:
        trims stop at `write_soft`, starts and parks at `write_hard`; stops always go through."""
        sp = float(min(max(round(sp), self.sp_min), SP_MAX))
        if sp == obs.setpoint:
            return Command()
        n = len(self.write_minutes)
        if (kind == "ride" and n >= self.write_soft) or (kind in ("start", "park") and n >= self.write_hard):
            self.stats["write_budget"] = self.stats.get("write_budget", 0) + 1
            return Command()
        self.last_write = obs.minute
        self.write_minutes.append(obs.minute)
        return Command(setpoint=sp)

    def _fallback_curve(self, obs):
        t = self.t_avg if self.t_avg is not None else obs.outdoor
        sp = min(max(22.0 + 0.30 * (22.0 - t) + 1.0, 25.0), 38.0)
        if abs(sp - obs.setpoint) >= 1.0:
            return self._write_sp(obs, sp)
        return Command()

    # ------------------------------------------------------------------ step
    def step(self, obs: Observation) -> Command:
        hour = obs.local_hour
        a = 1.0 / (24 * 60)
        self.t_avg = obs.outdoor if self.t_avg is None else self.t_avg + a * (obs.outdoor - self.t_avg)
        if self.z is None:
            self._init_state(obs)
        mode = obs.mode
        on = obs.compressor_on and mode in ("heat", "defrost")
        # bookkeeping
        if mode == "dhw":
            self.since_dhw = 0
        else:
            self.since_dhw += 1
        if mode == "defrost":
            self.since_defrost = 0
        else:
            self.since_defrost += 1
        stopped_unplanned = False
        if on:
            if not self.was_on:
                self.start_minutes.append(obs.minute)
                self.run_min = 0
            self.run_min += 1
            self.off_min = 0
        else:
            if self.was_on and mode != "dhw" and self.want_on:
                stopped_unplanned = True
            if mode != "dhw":
                self.off_min += 1
        self.was_on = on
        self.start_minutes = [m for m in self.start_minutes if obs.minute - m < 1440]
        if self.write_minutes and obs.minute - self.write_minutes[0] >= 1440:
            self.write_minutes = [m for m in self.write_minutes if obs.minute - m < 1440]
        # heat into the loop (zero while the valve is on the tank and just after); during a link
        # outage the unit fields are stale: assume the last steady output if it was running
        if not obs.link_ok:
            q = self.q_avg if (self.was_on_link and self.mode_link == "heat") else 0.0
        elif mode != "dhw" and self.since_dhw > 12 and mode != "off":
            q = CP_FLOW * (obs.outlet - obs.inlet + 0.3)
        else:
            q = 0.0
        if obs.link_ok:
            self.was_on_link = on
            if mode != "defrost":
                self.mode_link = mode
        self.q_acc += q
        if obs.link_ok and on and mode == "heat" and self.since_defrost > 5:
            self.q_avg += (q - self.q_avg) / 8.0
        self.ghi_acc += self._ghi_now(obs)
        self.tout_acc += self._t_out_now(obs)
        self.n_acc += 1
        self._heat_budget(obs, q)
        # delivered against planned heat while a block is wanted (outside the start minutes)
        if self.want_on and self.run_min > 15 and self.plan_q0 > 0 and obs.link_ok:
            ea = self.eta_acc
            band = self._eta_band(self._t_out_now(obs))
            if ea[2] != band:
                ea[0] = ea[1] = 0.0
                ea[2] = band
            ea[0] += q if mode != "dhw" else 0.0
            ea[1] += max(self.plan_q0, q_min(self._t_out_now(obs)))
            if ea[1] > 6.0 * 60:   # about an hour of planned heat
                r = min(max(ea[0] / ea[1], 0.6), 1.2)
                self.eta_band[band] += 0.05 * (r - self.eta_band[band])
                ea[0] = ea[1] = 0.0
        # COP learning from the meter (steady running only)
        if (obs.link_ok and on and mode == "heat" and self.run_min > 20 and self.since_defrost > 15
                and self.since_dhw > 30 and q > 1.0):
            t_now = self._t_out_now(obs)
            pm = q / cop_model(t_now, q, obs.outlet + 0.3, self.pl_k)
            acc = self.cop_acc
            cell = self._cell(t_now, q)
            if acc[2] != cell:
                acc[0] = acc[1] = 0.0
                acc[2] = cell
            acc[0] += obs.electric_kw
            acc[1] += pm
            if acc[1] > 1.0:   # about an hour of data in one cell
                r = acc[0] / acc[1]
                old = self.cop_cell.get(cell, 1.0)
                self.cop_cell[cell] = old + 0.1 * (min(max(r, 0.6), 1.6) - old)
                acc[0] = acc[1] = 0.0
        # forecast bias against the unit's sensor (night, idle: least sun and compressor bias)
        fc = obs.forecast
        if fc and not on and self._ghi_now(obs) < 0.02 and obs.link_ok:
            e = obs.outdoor + 0.48 - fc[0]["outdoor"]
            self.fc_bias += (max(min(e, 5.0), -5.0) - self.fc_bias) / 360.0
        # estimator
        if obs.minute % 10 == 0:
            self._estimate(obs, hour)
            ta = self.z[0]
            if not (12.0 < ta < 32.0) or not (12.0 < self.z[1] < 45.0) or not (5.0 < self.z[2] < 30.0):
                # implausible estimate: restart the estimator from the sensors (keep the learners)
                self.stats["reinit"] = self.stats.get("reinit", 0) + 1
                self._init_state(obs)
            # slow per-band bias learner on the estimated air, sunlit hours excluded (sun
            # overshoot cannot be helped and would only push the aim down at night)
            room_ok = self._room_ok(obs)
            if room_ok and self.t_avg is not None and self._ghi_now(obs) < 0.05:
                acc = self.aim_acc[self._eta_band(self.t_avg)]
                acc[0] += ta - obs.target
                acc[1] += 1
            if room_ok:   # the trims correct against the thermometer, not the open-loop model
                self.glob_acc[0] += ta - obs.target
                self.glob_acc[1] += 1
            self.n_day += 1
            if self.n_day >= 144:
                self.n_day = 0
                m = self.glob_acc[0] / max(self.glob_acc[1], 1)
                self.aim_glob = min(max(self.aim_glob - self.mean_fix_global * m, -0.3), 0.3)
                self.glob_acc = [0.0, 0]
                for b, acc in enumerate(self.aim_acc):
                    if acc[1] >= 36:
                        m = acc[0] / acc[1]
                        self.aim_band[b] = min(max(self.aim_band[b] - self.mean_fix * m, -0.4), 0.4)
                    acc[0] = acc[1] = 0
        if obs.minute < self.fallback_until:
            self.stats["fallback"] += 1
            if not obs.link_ok:
                return Command()
            return self._fallback_curve(obs)
        # plan
        if (obs.minute - self.plan_minute >= self.replan_min) or stopped_unplanned or self.plan is None:
            try:
                self.plan_q0 = self._plan(obs, hour)
            except (ValueError, ZeroDivisionError, OverflowError, IndexError):
                self.fallback_until = obs.minute + 120   # low weather curve for two hours
                return Command()
        return self._execute(obs, on)

    def _heat_budget(self, obs, q):
        """Daily loop heat against weather, learned while the room is known; while the thermometer
        is dead, an integral on (delivered - expected) heat moves the model's air-gain base so the
        open-loop model cannot drift the house warm or cold."""
        room_ok = self._room_ok(obs)
        if room_ok:
            if self.room_dead_min:
                self.d_slow += self.budget_fix     # the thermometer is back: it takes over
                self.budget_fix = 0.0
            self.room_dead_min = 0
        else:
            self.room_dead_min += 1
        a = self.day_acc
        a[0] += q / 60.0
        a[1] += self._t_out_now(obs)
        a[2] += self._ghi_now(obs)
        a[3] += 1
        a[4] += 1 if room_ok else 0
        self._air_acc += (self.z[0] - obs.target) if self.z is not None else 0.0
        if a[3] < 1440:
            return
        # sun beyond about 2.5 kWh/m2 a day mostly overheats the house: it saves no more heat
        qd, tm, gm = a[0], a[1] / a[3], min(a[2] / a[3] * 24.0, 2.5)
        dev = self._air_acc / a[3]
        x = (1.0, 22.0 - tm, gm)
        if self.hb is None:
            # prior: the documented 0.19 kW/K loss; a few autumn weeks cannot pin the slope
            self.hb = [-10.0, 0.19 * 24.0, -10.0]
            self.hb_P = [[(400.0, 0.3, 400.0)[i] if i == j else 0.0 for j in range(3)] for i in range(3)]
        pred = sum(c * v for c, v in zip(self.hb, x))
        if a[4] == a[3] and abs(dev) < 0.5:
            # a fully observed day: heat that held the room, corrected for its mean error
            y = qd - 0.19 * 24.0 * dev
            lam = 0.97
            P = self.hb_P
            px = [sum(P[i][j] * x[j] for j in range(3)) for i in range(3)]
            den = lam + sum(x[i] * px[i] for i in range(3))
            k = [v / den for v in px]
            e = y - pred
            self.hb = [c + ki * e for c, ki in zip(self.hb, k)]
            self.hb_P = [[(P[i][j] - k[i] * px[j]) / lam for j in range(3)] for i in range(3)]
            self.hb_n += 1
        elif self.room_dead_min >= 720 and self.hb_n >= 10 and a[4] < 720:
            # mostly blind day: too much heat delivered -> raise the modelled free gain
            e = (qd - pred) / 24.0
            self.budget_fix = min(max(self.budget_fix + self.budget_gain * e, -3.0), 3.0)
            self.stats["budget"] = round(self.budget_fix, 3)
        self.day_acc = [0.0, 0.0, 0.0, 0, 0]
        self._air_acc = 0.0

    def _t_out_now(self, obs):
        fc = obs.forecast
        if fc:
            return fc[0]["outdoor"] + self.fc_bias
        return self.t_avg if self.t_avg is not None else obs.outdoor

    def _execute(self, obs, on):
        q0 = self.plan_q0
        mode = obs.mode
        # intention with minimum run/off times and a daily start budget
        if q0 > 0 and not self.want_on:
            if self.off_min >= self.min_off and len(self.start_minutes) < self.max_starts_day:
                self.want_on = True
        elif q0 <= 0 and self.want_on:
            if not on or self.run_min >= self.min_run:
                self.want_on = False
        if not obs.link_ok:
            return Command()
        if not obs.heating_enabled:
            return Command()     # heating switched off by the user (summer, manual): hands off
        if mode in ("dhw", "defrost", "off") or self.since_dhw < 10:
            return Command()
        if obs.restart_delta == self.delta_reg:
            self.delta_tries = 0
        elif (obs.minute >= self.delta_next and len(self.write_minutes) < self.write_soft
              and not (self.want_on and on)):
            # 5 K (a recorded value): the park setpoint of 25 degC then holds the unit off down to
            # a 20 degC control sensor, and starts are always ours. If the register does not take
            # it (panel setting, clamped register, rejected write), back off: 10 min, 1 h, 6 h,
            # then once a day; everything else works from the observed restart_delta.
            self.delta_tries += 1
            self.delta_next = obs.minute + (10, 60, 360, 1440)[min(self.delta_tries - 1, 3)]
            self.stats["delta_tries"] = self.stats.get("delta_tries", 0) + 1
            self.write_minutes.append(obs.minute)
            return Command(restart_delta=self.delta_reg)
        t_ctrl_idle = obs.inlet - 0.7
        if self.want_on:
            if not on:
                if len(self.start_minutes) >= self.max_starts_day or self.off_min < 4:
                    return Command()
                # the smallest setpoint the firmware's restart rule accepts
                sp = math.ceil(t_ctrl_idle + obs.restart_delta + 0.15)
                if obs.setpoint < sp:
                    return self._write_sp(obs, sp, "start")
                return Command()
            # riding: hold the planned output at the lowest supply that delivers it
            t_now = self._t_out_now(obs)
            qm = q_min(t_now)
            q_tgt = max(q0, qm)
            t_ctrl = obs.outlet - 0.5
            sp = obs.setpoint
            floor_sp = math.ceil(t_ctrl - 1.6)          # keep clear of the stop threshold (t_ctrl >= sp + 2)
            since_w = obs.minute - self.last_write
            if q_tgt <= qm + 0.4:
                want = math.floor(t_ctrl - 0.2)          # error below the dead band: output goes to its floor
                if sp <= want and sp >= floor_sp:
                    want = sp                            # already riding the floor: leave it
            elif q_tgt >= self._q_cap(t_now) - 0.3:
                # flat out: ask for more than the cap so the unit runs at its real maximum
                want = min(round(obs.inlet + (q_tgt + 2.0) / CP_FLOW), SP_MAX)
                if abs(sp - want) <= self.flat_hold or sp >= SP_MAX:
                    want = sp                            # error still large enough: no trim
                if (self.run_min > 30 and self.since_defrost > 20 and sp - t_ctrl > 1.2
                        and obs.minute % 10 == 0):
                    b = self._eta_band(t_now)
                    old = self.cap_band[b] if self.cap_band[b] is not None else q_max(t_now)
                    self.cap_band[b] = old + 0.05 * (self.q_avg - old)
            elif self.run_min <= 3 or self.ride_q_tgt != q_tgt:
                want = round(obs.inlet + q_tgt / CP_FLOW - 0.25 - 0.025 * (q_tgt - 5.0))
            else:
                want = sp
                if self.run_min >= 14 and since_w >= self.ride_every:
                    if self.q_avg < q_tgt - 0.7 and sp - t_ctrl < 1.6:
                        want = sp + 1
                    elif self.q_avg > q_tgt + 0.9:
                        want = sp - 1
            new_tgt = self.ride_q_tgt != q_tgt or self.run_min <= 3
            self.ride_q_tgt = q_tgt
            want = max(want, floor_sp)
            if want != sp and sp < floor_sp:
                return self._write_sp(obs, want, "start")   # keep the run alive: essential
            if want != sp and (since_w >= self.ride_every or (new_tgt and since_w >= 5)):
                d = 1 if want > sp else -1
                if d == -self.ride_dir and obs.minute - self.ride_dir_min < self.ride_rev_min:
                    return Command()                         # no saw-tooth: wait before reversing
                cmd = self._write_sp(obs, want)
                if cmd.setpoint is not None:
                    self.ride_dir, self.ride_dir_min = d, obs.minute
                return cmd
            return Command()
        self.ride_q_tgt = None
        # off: stop by a setpoint far below the control sensor, then park at 25 degC
        if on:
            t_ctrl = obs.outlet - 0.5
            # 2.5 K clear of the stop threshold (2.0-2.5 K is where the firmware is unreliable);
            # never below 25 degC: with a cool loop the 3-min rule stops it once the water warms
            sp = max(self.sp_min, math.floor(t_ctrl - self.stop_margin))
            if obs.setpoint > sp:
                return self._write_sp(obs, sp, "stop")
            return Command()
        # park: a backup thermostat on the loop water for when this controller goes silent (link,
        # Home Assistant down). The firmware restarts by itself only once the slab-side water is
        # below what holds the room at target - 1.5 K; while we are connected the park stays
        # below the restart rule, so every start is still ours.
        cap = math.floor(t_ctrl_idle + obs.restart_delta - 1.0)
        park = PARK_SP
        if self.park_backup:
            t_now = self._t_out_now(obs)
            ts_min, _, _ = self.model.steady(obs.target - self.park_margin, t_now, 0.3 + self.d_slow)
            pb = math.floor(ts_min + (self.b_w or 0.0) + obs.restart_delta - 0.7)
            park = max(PARK_SP, min(pb, cap, SP_MAX))
        if self.off_min >= 2 and obs.setpoint != park and (
                obs.setpoint > max(cap, PARK_SP) or abs(obs.setpoint - park) >= 2 or park == PARK_SP):
            return self._write_sp(obs, park, "park")
        return Command()


CONTROLLER = EconMPC


if __name__ == "__main__":
    import time as _time
    from datetime import datetime, timedelta, timezone

    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fc = tuple({"time": t0 + timedelta(hours=h + 1), "outdoor": 5.0, "rh": 80, "ghi": 0, "dni": 0, "dhi": 0,
                "cloud": 100} for h in range(48))
    base = dict(time=t0, local_hour=2.0, room=21.4, room_age_min=5, outdoor=5.0, outlet=26.0, inlet=26.3,
                setpoint=25.0, restart_delta=5.0, quiet=False, heating_enabled=True, compressor_on=False,
                mode="idle", electric_kw=0.02, energy_kwh=0.0, target=22.0, forecast=fc, pv_kw=0.0)
    c = EconMPC()
    c.reset({})
    tic = _time.perf_counter()
    cmds = [c.step(Observation(minute=m, **base)) for m in range(240)]
    dt = _time.perf_counter() - tic
    assert any(x.setpoint and x.setpoint >= 29 for x in cmds), "a cold room must start a block"
    # a warm room must not start one
    c.reset({})
    warm = {**base, "room": 23.5}
    cmds = [c.step(Observation(minute=m, **warm)) for m in range(240)]
    assert not any(x.setpoint and x.setpoint >= 29 for x in cmds), "a warm room must not start"
    # fail-safes
    c.reset({})
    assert c.step(Observation(minute=0, link_ok=False, **base)) == Command(), "no writes while the link is down"
    c.reset({})
    off = {**base, "heating_enabled": False}
    assert all(c.step(Observation(minute=m, **off)) == Command() for m in range(120)), "hands off when disabled"
    c.reset({})
    cold = {**base, "room": 20.5, "inlet": 19.0, "outlet": 18.7}
    sps = [x.setpoint for x in (c.step(Observation(minute=m, **cold)) for m in range(240)) if x.setpoint]
    assert all(25 <= v <= 39 for v in sps), "writes stay in the recorded range"
    c.reset({})
    for m in range(120):
        c.step(Observation(minute=m, **{**base, "room": None, "forecast": ()}))
    for m in range(30):
        cmd = c.step(Observation(minute=200 + m, **{**base, "mode": "dhw", "compressor_on": True}))
        assert cmd == Command(), "no writes during hot water"
    print(f"self-check ok ({dt * 1000 / 240:.2f} ms per step incl. plans)")
