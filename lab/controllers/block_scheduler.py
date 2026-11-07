"""Energy-budget block scheduler (strategy S5 of HEAT_PUMP_CONTROL_RESEARCH.md, with S8 timing and
S6 soft start / setpoint riding underneath). Stdlib only.

Separate WHEN to run from HOW HOT:

- **What the house needs.** A small grey-box model of the house (slab, room air, envelope; the
  public lab house model's structure and rounded central values) is kept on the observed room
  thermometer (minus its sun glow) and the heat the unit puts into the loop (measured from outlet -
  inlet). An air-node disturbance bias is learned online from the room innovations (its slow part
  persists over the plan, its fast part fades over a few hours), and a slow trim keeps the mean
  room on target. Over the next 30 h the model gives the free room trajectory from the forecast
  (outdoor, facade sun) and the response of the room to an hour of heat.
- **When to run.** Every 30 minutes a rolling plan places whole hours of running at a fixed block
  output into the next 30 h: greedily, the hour whose heat lowers 'electricity + comfort' the most
  is switched on (extending an existing block is free, a new block pays a start cost and must be
  at least `min_block_h` long), until no hour pays for itself. Electricity per hour of running
  comes from a COP prior in outdoor temperature (defrost included) and the predicted supply
  temperature (slab + output / emitter conductance); comfort is priced at 0.54 kWh per K-hour of
  |room - target| (the ranking's own price); heat still stored in the house at the end of the
  horizon is credited at the horizon's mean cost. The plan is the day's energy budget, delivered as
  few long blocks in the cheapest (warmest, least frosty) hours the slab's storage allows.
- **How hot.** A block runs at `q_run` (about 5.5 kW in mild weather: the unit model's COP is
  20-45 % worse at the minimum output, so 'minimum output' is not the efficient level here; in
  colder weather the block output rises with the load). The water temperature follows from that
  output and the slab: the setpoint rides at inlet + q / (cp x flow) + 0.2 K, so the firmware's
  own error loop holds the chosen output at the lowest supply that delivers it (re-written only
  when the delivered output misses the plan by > 0.8 kW, and kept up before each 120-min surge
  mark). A block starts with the smallest setpoint the restart rule accepts (soft start, first
  15 min at the base level) and ends with one write straight to the park setpoint.

Fail-safe: link down -> no writes, the model runs on the last known unit state; room missing ->
the model runs open loop on the forecast and the learned bias; forecast missing -> the 24-h mean
of the unit's outdoor sensor, no sun; DHW, defrost and the minutes after them freeze the executor
and the heat measurement.
"""
from __future__ import annotations

import math
from datetime import timedelta

from lab.sim.interface import Command, Observation

PARK_SP = 25.0          # lowest setpoint ever written to the real unit; parks the compressor
CP_FLOW = 2.02          # kW per K of loop delta-T at the documented 29 L/min
LAT, LON = 54.7, 25.3   # the city (public), for the sun position

# COP prior: steady COP at a 30 degC supply and ~5.5 kW (unit model, UNIT_MODEL.md 7.2) times the
# documented defrost penalty (UNIT_MODEL.md 8: 16 % at -10, 13 % at -3, 10 % at 0, 6 % at +2, <1 %
# above +4 degC)
COP_T = (-20.0, -15.0, -10.0, -7.0, -5.0, -3.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 15.0)
COP_V = (2.15, 2.45, 2.65, 2.80, 2.90, 3.00, 3.20, 3.38, 3.60, 3.89, 4.20, 4.55, 4.85, 5.14, 5.36, 5.50, 5.67, 5.83)


def _interp(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            f = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + f * (ys[i] - ys[i - 1])
    return ys[-1]


# ---------------------------------------------------------------------------- small linear algebra
def _matmul(a, b):
    n, m, p = len(a), len(b), len(b[0])
    return [[sum(a[i][k] * b[k][j] for k in range(m)) for j in range(p)] for i in range(n)]


def _expm(a):
    """Matrix exponential (scaling and squaring + Taylor), for the small model matrices."""
    n = len(a)
    norm = max(sum(abs(v) for v in row) for row in a)
    s = max(0, int(math.ceil(math.log2(norm))) + 1) if norm > 0.5 else 0
    sc = 2.0 ** -s
    a = [[v * sc for v in row] for row in a]
    res = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    term = [row[:] for row in res]
    for k in range(1, 18):
        term = _matmul(term, a)
        term = [[v / k for v in row] for row in term]
        res = [[res[i][j] + term[i][j] for j in range(n)] for i in range(n)]
    for _ in range(s):
        res = _matmul(res, res)
    return res


def _discretize(A, B, dt):
    """x+ = Phi x + Gam u for piecewise-constant u over dt (augmented exponential)."""
    n, m = len(A), len(B[0])
    M = [[0.0] * (n + m) for _ in range(n + m)]
    for i in range(n):
        for j in range(n):
            M[i][j] = A[i][j] * dt
        for j in range(m):
            M[i][n + j] = B[i][j] * dt
    E = _expm(M)
    return [row[:n] for row in E[:n]], [row[n:] for row in E[:n]]


# ---------------------------------------------------------------------------- sun on the facades
def _sun(t_utc):
    """Solar elevation and azimuth (rad; azimuth from north, clockwise) - NOAA short form."""
    doy = t_utc.timetuple().tm_yday
    hr = t_utc.hour + t_utc.minute / 60.0
    g = 2 * math.pi / 365.0 * (doy - 1 + (hr - 12) / 24.0)
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
            + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g)
                    - 0.040849 * math.sin(2 * g))
    tst = hr * 60.0 + eqt + 4.0 * LON
    ha = math.radians(tst / 4.0 - 180.0)
    lat = math.radians(LAT)
    cz = math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(ha)
    cz = max(-1.0, min(1.0, cz))
    zen = math.acos(cz)
    el = math.pi / 2 - zen
    # azimuth from north, clockwise
    y = -math.sin(ha) * math.cos(decl)
    x = (math.sin(decl) - math.sin(lat) * cz) / math.cos(lat)
    return el, math.atan2(y, x) % (2 * math.pi)


def _facade_kw(t_mid, ghi, dni, dhi, aps):
    """Solar gain on the air node (kW) through effective apertures (south, east, west m2):
    isotropic sky, ground albedo 0.2."""
    if ghi <= 0.0:
        return 0.0
    el, az = _sun(t_mid)
    if dni is None or dhi is None:
        dhi = ghi if dhi is None else dhi
        dni = 0.0 if el <= 0 else max(0.0, (ghi - dhi) / max(math.sin(el), 0.05))
    tot = 0.0
    for area, f_az in zip(aps, (math.pi, math.pi / 2, 1.5 * math.pi)):
        if area <= 0:
            continue
        cos_i = math.cos(el) * math.cos(az - f_az) if el > 0 else 0.0
        irr = dni * max(0.0, cos_i) + 0.5 * dhi + 0.5 * 0.2 * ghi
        tot += area * irr
    return tot / 1000.0


class BlockScheduler:
    name = "block_scheduler"

    # ------------------------------------------------------------------ setup
    def reset(self, params: dict) -> None:
        g = lambda k, d: float(params.get(k, d))  # noqa: E731
        # house model (public lab house model, rounded central values; HOUSE_MODEL.md 1 and 8)
        self.c_s = g("c_s", 4.66)        # slab + loop water, kWh/K
        self.k_sa = g("k_sa", 0.43)      # slab -> air, kW/K
        self.h_g = g("h_g", 0.09)        # slab -> 10 degC ground
        self.c_a = g("c_a", 4.3)         # air + furniture
        self.h_ao = g("h_ao", 0.045)     # air -> outdoors
        self.c_e = g("c_e", 74.0)        # envelope / heavy mass
        self.k_ae = g("k_ae", 1.35)
        self.h_eo = g("h_eo", 0.07)
        self.q_int = g("q_int", 0.31)    # mean internal gain, kW
        self.aps = (g("a_s", 2.7), g("a_e", 6.4), g("a_w", 3.7))
        self.glow = g("glow", 0.0008)    # K per W/m2 GHI on the thermometer
        self.k_emit = g("k_emit", 1.43)  # kW per K of supply above slab (2.53 kW/K loop->slab, eff. 0.71)
        # Kalman filter noise (per hour of process, per minute of measurement)
        self.qn_d = g("qn_d", 0.6)       # air-node bias random walk, kW^2 per hour
        self.qn_a = g("qn_a", 0.01)      # air state, K^2 per hour
        self.qn_s = g("qn_s", 0.01)      # slab state (heat-measurement error), K^2 per hour
        self.qn_e = g("qn_e", 0.0005)    # envelope
        self.r_room = g("r_room", 0.05)  # thermometer variance per minute, K^2 (0.1-K steps, correlated)
        self.qn_o = g("qn_o", 0.01)      # inlet-slab offset random walk, K^2 per hour
        self.r_inlet = g("r_inlet", 0.05)  # inlet as slab thermometer, K^2 per minute
        self.ret_k = g("ret_k", 0.2)     # K of return above the slab per kW of heat
        self.use_inlet = bool(g("use_inlet", 1))
        self.tau_fast_h = g("tau_fast_h", 3.0)   # fast part of the bias fades over this in the plan
        self.tau_slow_h = g("tau_slow_h", 24.0)  # slow (persistent) part of the bias
        self.k_trim = g("k_trim", 0.015)  # K of aim per K-hour of room error (slow integral on the mean)
        self.trim_lim = g("trim_lim", 0.8)
        # start-up (review-2 R3): the trim learns trim_boost times faster at first, fading over
        # trim_boost_d days, so a fresh install (or a short test) reaches the mean target sooner
        self.trim_boost = g("trim_boost", 0.0)
        self.trim_boost_d = g("trim_boost_d", 3.0)
        self.aim_off = g("aim_off", 0.0)  # fixed aim offset, K
        # plan
        self.n_h = int(g("horizon_h", 30))
        self.lam = g("lam", 0.54)        # kWh per K-hour of |room - aim|
        self.lam_mean = g("lam_mean", 0.0)  # kWh per K-hour of the mean deviation over n_mean hours
        self.n_mean = int(g("n_mean", 18))
        self.c_start = g("c_start", 2.5)  # kWh per start in the plan
        self.min_block = int(g("min_block_h", 2))
        self.q_eff = g("q_run", 5.0)     # block output in mild weather, kW
        self.q_max = g("q_max", 8.5)
        self.q_cont_k = g("q_cont_k", 1.05)  # continuous level = this x the next 6 h mean load (0 = off)
        self.q_steps = (g("q_step1", 1.0), g("q_step2", 2.5))  # higher block outputs the plan may pick
        self.sup_pen = g("sup_pen", 0.033)  # electricity per K of supply
        self.sup_slab = g("sup_slab", 0.0)  # share of the predicted slab swing in the supply estimate
        # heat credit: tv_full (default) credits every hour at the horizon's mean cost of the same
        # heat; otherwise tv_k x mean cost x the heat retained at the horizon end (tv_flat: the
        # smallest retention for every hour)
        self.tv_full = bool(g("tv_full", 1))
        self.tv_k = g("tv_k", 1.0)
        self.tv_flat = bool(g("tv_flat", 1))
        self.cop_timing = g("cop_timing", 1.0)  # 1: each hour's COP; 0: no timing preference
        self.replan_min = int(g("replan_min", 30))
        self.polish = bool(g("polish", 1))  # local search after the greedy fill (review-2)
        # executor
        self.min_run = g("min_run", 60.0)
        self.min_off = g("min_off", 45.0)
        self.ride_every = g("ride_every", 15.0)
        self.ride_off = g("ride_off", 0.2)  # firmware stops ramping up at setpoint - t_ctrl = 1 K
        self.ride_hyst = g("ride_hyst", 0.75)  # re-ride only when the target moved this far, K
        # output deadband (review-2 R6): once a block has settled, re-ride only when the delivered
        # output (20-min mean) misses the plan by more than q_tol kW in the direction of the
        # change, or the plan's level moved
        self.q_tol = g("q_tol", 0.8)
        self.park_pred = bool(g("park_pred", 1))
        self.wr_soft = int(g("wr_soft", 28))   # writes in the last 24 h: above this, ride hourly
        self.wr_hard = int(g("wr_hard", 38))   # ... above this, start/stop/park writes only
        # safety park (review R2): in the cold, park at a setpoint at which the firmware itself
        # restarts once the slab has fallen park_margin below its steady level for the load, so a
        # lost controller (Home Assistant down) still leaves a working thermostat on the unit
        self.park_margin = g("park_margin", 2.0)
        self.park_max = g("park_max", 34.0)
        # room thermometer staleness (review R1): full weight up to room_fresh min since the last
        # change, fading weight up to room_stale, ignored beyond; the trim learns only while fresh
        self.room_fresh = g("room_fresh", 120.0)
        self.room_stale = g("room_stale", 360.0)
        self.tau_miss_h = g("tau_miss_h", 3.0)  # bias relaxes to its 24-h mean while the room is missing
        # online loss correction (review-2 R2): the learned air-node bias is regressed on the
        # indoor-outdoor difference over a h_mem_d-day memory; the slope is the house's heat-loss
        # error (kW/K) and moves the planned bias with the forecast outdoor temperature
        self.h_learn = bool(g("h_learn", 0))
        self.h_mem_d = g("h_mem_d", 10.0)
        self.h_ridge_d = g("h_ridge_d", 2.0)   # prior (b = 0) worth this many days of 5-K spread
        self.h_lim = g("h_lim", 0.08)          # |slope| limit, kW/K (0.08 = 40 % of the loss)
        # frozen thermometer (review-2 R5): the reading's effective age is the time since its
        # value last changed, whatever its timestamp says
        self.frozen_check = bool(g("frozen_check", 1))
        # soft first ride (review-2 R7): the first ride_soft_min of a block ride at the base level
        self.ride_soft_min = g("ride_soft_min", 15.0)
        # state
        self._build_model()
        self.x = None              # [Ts, Ta, Te]
        self.z = None              # observer state [Ts, Ta, Te, d, o]
        self.P = None
        self.d = 0.0
        self.d_long = 0.0
        self.trim = 0.0
        self.n_learn = 0           # minutes of trim learning so far
        self.t_avg = None
        self.since_dhw = 999
        self.since_def = 999
        self.run_min = 0           # unit run minutes (observed)
        self.off_min = 999
        self.want = False          # plan says run now
        self.q_plan = self.q_eff
        self.last_plan = -999
        self.last_ride = -999
        self.plan = []
        self.budget_kwh = 0.0
        self.prev_comp = False
        self.n_plans = 0
        self.park_sp = PARK_SP     # weather-dependent safety park, refreshed by the plan
        self.writes = []           # minutes of our own register writes (rolling 24 h)
        self.ride_sp = None        # last continuous ride target that was written
        self.q_ema = None          # delivered output, 20-min mean while running
        self.q_rode = None         # plan level at the last ride write
        self.prev_h = None         # the previous forecast hour (for 'irradiance now')
        self.cur_h = None
        self.room_ok = False
        self.link_quiet = 0        # minutes since the link came back (heat unknown while down)
        self.room_last = None      # last room value and the minute it changed
        self.room_chg = 0
        self.h_s = [0.0, 0.0, 0.0, 0.0, 0.0]  # weighted sums: n, x, xx, y, xy
        self.h_b = 0.0             # learned loss slope, kW/K (negative: house loses more)
        self.dT_long = None        # 24-h mean of (air - outdoor), same memory as d_long
        self.q_base = self.q_eff

    def _build_model(self):
        cs, ca, ce = self.c_s, self.c_a, self.c_e
        A = [[-(self.k_sa + self.h_g) / cs, self.k_sa / cs, 0.0],
             [self.k_sa / ca, -(self.k_sa + self.h_ao + self.k_ae) / ca, self.k_ae / ca],
             [0.0, self.k_ae / ce, -(self.k_ae + self.h_eo) / ce]]
        # inputs: Q (kW to slab), To, P_air (kW: sun + gains + bias), 1 (ground at 10 degC)
        B = [[1.0 / cs, 0.0, 0.0, self.h_g * 10.0 / cs],
             [0.0, self.h_ao / ca, 1.0 / ca, 0.0],
             [0.0, self.h_eo / ce, 0.0, 0.0]]
        self.Ph, self.Gh = _discretize(A, B, 1.0)
        # observer model: augmented with the air-node bias d (kW, random walk) and the offset o
        # (K, slow random walk) between the inlet sensor and the slab while the loop circulates
        A5 = [row[:] + [0.0, 0.0] for row in A] + [[0.0] * 5, [0.0] * 5]
        A5[1][3] = 1.0 / ca
        B5 = [row[:] for row in B] + [[0.0] * 4, [0.0] * 4]
        self.F5, self.G5 = _discretize(A5, B5, 1.0 / 60.0)
        self.F5t = [list(r) for r in zip(*self.F5)]
        self.qn5 = [self.qn_s / 60.0, self.qn_a / 60.0, self.qn_e / 60.0, self.qn_d / 60.0, self.qn_o / 60.0]
        # responses to one hour of 1 kW, j hours after its start (state at the end of hour j-1)
        n = self.n_h + 2
        x = [self.Gh[i][0] for i in range(3)]
        self.ga, self.gs, self.gE = [0.0], [0.0], [0.0]
        for _ in range(n):
            self.ga.append(x[1])
            self.gs.append(x[0])
            self.gE.append(cs * x[0] + ca * x[1] + ce * x[2])
            x = [sum(self.Ph[i][k] * x[k] for k in range(3)) for i in range(3)]

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _q_min(t_out):
        return CP_FLOW * min(max(1.8 + 0.05 * t_out, 1.4), 2.4)

    def _steady_x(self, ta, to):
        te = (self.k_ae * ta + self.h_eo * to) / (self.k_ae + self.h_eo)
        load_air = self.h_ao * (ta - to) + self.k_ae * (ta - te) - self.q_int
        ts = ta + max(load_air, 0.0) / self.k_sa
        return [ts, ta, te]

    def _hourly(self, obs):
        """Outdoor and sun (kW on the air node) per plan hour, from the forecast or a fallback."""
        fc = obs.forecast
        n = self.n_h
        if fc and len(fc) >= 2:
            half = obs.time.minute >= 30
            to, sun = [], []
            m = len(fc)
            for k in range(n):
                i = min(k, m - 1)
                h = fc[i]
                t1 = h["outdoor"]
                s1 = self._sun_of(h)
                if half:
                    h2 = fc[min(k + 1, m - 1)]
                    t1 = 0.5 * (t1 + h2["outdoor"])
                    s1 = 0.5 * (s1 + self._sun_of(h2))
                to.append(t1)
                sun.append(s1)
            return to, sun, True
        t = self.t_avg if self.t_avg is not None else obs.outdoor
        return [t] * n, [0.0] * n, False

    def _sun_of(self, h):
        key = id(h)
        c = self._sun_cache.get(key) if hasattr(self, "_sun_cache") else None
        if c is not None and c[0] is h:
            return c[1]

        ghi = h.get("ghi", 0.0) or 0.0
        v = _facade_kw(h["time"] - timedelta(minutes=30), ghi, h.get("dni"), h.get("dhi"), self.aps)
        if not hasattr(self, "_sun_cache") or len(self._sun_cache) > 4000:
            self._sun_cache = {}
        self._sun_cache[key] = (h, v)
        return v

    @staticmethod
    def _cop(t_out):
        return _interp(t_out, COP_T, COP_V)

    # ------------------------------------------------------------------ observer
    def _observe(self, obs, q_meas, sun_now, to_now, inlet_ok):
        """Kalman filter on [slab, air, envelope, air-node bias, inlet offset]. Measurements: the
        room thermometer minus its sun glow (air), and the inlet sensor while the loop water is
        settled (slab + offset + 0.2 K per kW of heat: return = slab + 0.29 x (supply - slab))."""
        if self.z is None:
            ta = obs.room - self.glow * self._ghi_now(obs) if obs.room is not None else obs.target
            x = self._steady_x(ta, to_now)
            o0 = (obs.inlet - x[0]) if inlet_ok else 0.0
            self.z = [x[0], x[1], x[2], 0.0, o0]
            self.P = [[(0.25 if i == j else 0.0) for j in range(5)] for i in range(5)]
            self.P[3][3] = 1.0
            self.P[4][4] = 1.0
        F, G = self.F5, self.G5
        u = (q_meas, to_now, sun_now + self.q_int, 1.0)
        z = self.z
        z = [sum(F[i][k] * z[k] for k in range(5)) + sum(G[i][j] * u[j] for j in range(4)) for i in range(5)]
        FP = [[sum(F[i][k] * self.P[k][j] for k in range(5)) for j in range(5)] for i in range(5)]
        Ft = self.F5t
        P = [[sum(FP[i][k] * Ft[k][j] for k in range(5)) for j in range(5)] for i in range(5)]
        for i in range(5):
            P[i][i] += self.qn5[i]
        age = obs.room_age_min if obs.room_age_min is not None else 0.0
        if obs.room is not None:
            if self.room_last is None or obs.room != self.room_last:
                self.room_last = obs.room
                self.room_chg = obs.minute
            if self.frozen_check:
                age = max(age, obs.minute - self.room_chg)
        self.room_ok = obs.room is not None and age <= self.room_stale
        # learn slow quantities only while the heat into the house is known (link up for 30 min)
        learn = self.link_quiet > 30
        if self.room_ok:
            y = obs.room - self.glow * self._ghi_now(obs)
            # a reading that has not changed for hours is either a very steady room or a dead
            # sensor: its weight fades with age beyond room_fresh, and it is ignored beyond
            # room_stale (the real device reports at least hourly; 99.7 % of simulated ages < 6 h)
            r = self.r_room * max(1.0, age / self.room_fresh) ** 2
            z, P = self._update(z, P, (1,), y, r, 1.0)
            if age <= self.room_fresh and learn:
                # slow aim trim from the (glow-corrected) room error
                kt = self.k_trim * (1.0 + self.trim_boost * math.exp(-self.n_learn / (1440.0 * self.trim_boost_d)))
                self.n_learn += 1
                self.trim -= kt * (y - obs.target) / 60.0
                self.trim = max(-self.trim_lim, min(self.trim_lim, self.trim))
        else:
            # no usable thermometer: the bias relaxes to its 24-h mean (open loop on the model)
            z[3] += (self.d_long - z[3]) / (60.0 * self.tau_miss_h)
        if inlet_ok:
            z, P = self._update(z, P, (0, 4), obs.inlet - self.ret_k * q_meas, self.r_inlet, 0.7)
        z[3] = max(-3.0, min(3.0, z[3]))
        z[4] = max(-4.0, min(4.0, z[4]))
        self.z, self.P = z, P
        self.x = [z[0], z[1], z[2]]
        self.d = z[3]
        dT = self.x[1] - to_now
        if self.dT_long is None:
            self.dT_long = dT
        if self.room_ok and learn:
            a = 1.0 / (60.0 * self.tau_slow_h)
            self.d_long += a * (self.d - self.d_long)
            self.dT_long += a * (dT - self.dT_long)
            if self.h_learn:
                self._learn_loss(dT - 25.0, self.d)

    def _learn_loss(self, xc, y):
        """Exponentially weighted least squares of the bias on the centred indoor-outdoor
        difference, with a ridge prior on the slope."""
        lam = 1.0 - 1.0 / (self.h_mem_d * 1440.0)
        s = self.h_s
        for i, v in enumerate((1.0, xc, xc * xc, y, xc * y)):
            s[i] = lam * s[i] + v
        n, sx, sxx, sy, sxy = s
        if n < 1440.0:
            return
        ridge = self.h_ridge_d * 1440.0 * 25.0
        var = sxx - sx * sx / n
        cov = sxy - sx * sy / n
        b = cov / (var + ridge)
        self.h_b = max(-self.h_lim, min(self.h_lim, b))

    @staticmethod
    def _update(z, P, idx, y, r, clip):
        """Scalar measurement y = sum(z[i] for i in idx) + noise(r)."""
        ph = [sum(P[i][k] for k in idx) for i in range(5)]
        s = sum(ph[k] for k in idx) + r
        K = [v / s for v in ph]
        e = y - sum(z[k] for k in idx)
        e = max(-clip, min(clip, e))
        z = [z[i] + K[i] * e for i in range(5)]
        P = [[P[i][j] - K[i] * ph[j] for j in range(5)] for i in range(5)]
        return z, P

    def _track_hours(self, obs):
        fc = obs.forecast
        if not fc:
            return
        h0 = fc[0]
        if self.cur_h is None or h0["time"] != self.cur_h["time"]:
            if self.cur_h is not None and h0["time"] - self.cur_h["time"] == timedelta(hours=1):
                self.prev_h = self.cur_h
            else:
                self.prev_h = None
            self.cur_h = h0

    def _now_val(self, obs, fn):
        """Value 'now' of an hourly-mean quantity: interpolated between the hour-mean centres of
        the previous hour, the current hour (fc[0]) and the next one (review R8)."""
        fc = obs.forecast
        if not fc:
            return 0.0
        m = obs.time.minute + obs.time.second / 60.0
        v0 = fn(fc[0])
        if m < 30.0:
            vp = fn(self.prev_h) if self.prev_h is not None else v0
            return vp + (m + 30.0) / 60.0 * (v0 - vp)
        v1 = fn(fc[1]) if len(fc) > 1 else v0
        return v0 + (m - 30.0) / 60.0 * (v1 - v0)

    def _ghi_now(self, obs):
        return self._now_val(obs, lambda h: h.get("ghi", 0.0) or 0.0)

    # ------------------------------------------------------------------ plan
    def _plan(self, obs, running):
        n = self.n_h
        to, sun, have_fc = self._hourly(obs)
        aim = obs.target + self.aim_off + self.trim
        # free trajectory (no heat) over the horizon
        x = list(self.x)
        ta_f, ts_f = [x[1]], [x[0]]
        load = []
        hb = self.h_b
        dT_l = self.dT_long if self.dT_long is not None else 25.0
        d_fast = self.d - self.d_long - hb * ((self.x[1] - to[0]) - dT_l)
        dk = []
        for k in range(n):
            d = (self.d_long + hb * ((aim - to[k]) - dT_l)
                 + d_fast * math.exp(-(k + 0.5) / self.tau_fast_h))
            dk.append(d)
            u = (0.0, to[k], sun[k] + self.q_int + d, 1.0)
            x = [sum(self.Ph[i][j] * x[j] for j in range(3)) + sum(self.Gh[i][j] * u[j] for j in range(4))
                 for i in range(3)]
            ta_f.append(x[1])
            ts_f.append(x[0])
            load.append(max(0.0, 3.7 + 0.187 * (aim - 22.0) - 0.135 * to[k] - sun[k] - d))
        self.load_24 = sum(load[:24])
        # safety park (review R2): the setpoint at which the firmware restarts by itself once the
        # control sensor (idle: inlet - 0.7 K = slab + o - 0.7 K) has fallen to the steady slab for
        # the next 6 h load minus park_margin
        p6 = sum(load[:6]) / 6.0
        ts6 = (p6 + self.k_sa * obs.target + self.h_g * 10.0) / (self.k_sa + self.h_g)
        t_ctrl_floor = ts6 - self.park_margin + self.z[4] - 0.7
        self.park_sp = float(min(max(math.floor(t_ctrl_floor + obs.restart_delta), PARK_SP), self.park_max))
        t6 = sum(to[:6]) / 6.0
        qa = min(max(self.q_eff, self._q_min(t6)), self.q_max)
        levels = [qa]
        for step in self.q_steps:
            qb = min(qa + step, self.q_max)
            if qb > levels[-1] + 0.3:
                levels.append(qb)
        # continuous mode: when the next hours' load is above the unit's minimum output, a level
        # that just carries the load lets the plan run without stopping (S5's cold branch)
        q_c = min(sum(load[:6]) / 6.0 * self.q_cont_k, self.q_max)
        if self.q_cont_k > 0 and q_c > self._q_min(t6) + 0.2 and all(abs(q_c - v) > 0.3 for v in levels):
            levels.append(q_c)
        best = None
        self._q_ref = levels[0]
        self.q_base = levels[0]
        for q in levels:
            u, j = self._greedy(q, to, ta_f, ts_f, aim, running, load)
            if best is None or j < best[1] - 1e-9:
                best = (u, j, q, self._ta_plan, self._ts_plan)
        u, _, q, self.ta_pred, self.ts_pred = best
        self.plan = u
        self.q_plan = q
        self.budget_kwh = q * sum(u[:24])
        self.n_plans += 1
        return bool(u[0])

    def _greedy(self, q, to, ta_f, ts_f, aim, running, load=None):
        """Switch on, one at a time, the plan hour (or new block) that lowers electricity +
        comfort + start cost - stored-heat credit the most. Returns (on/off list, total cost)."""
        n = self.n_h
        lam = self.lam
        ga, gs, gE = self.ga, self.gs, self.gE
        el_base = []
        t_mean = sum(to) / n
        for k in range(n):
            # timing: the hour's own outdoor temperature, blended towards the horizon mean
            t_k = t_mean + self.cop_timing * (to[k] - t_mean)
            pl = 1.0 + _interp(t_k, (-10.0, 0.0, 7.0), (0.165, 0.12, 0.083)) * max(0.0, 5.5 - q)
            el_base.append(q * pl / self._cop(t_k))
        mean_cost = sum(1.0 / self._cop(t) for t in to) / n
        # heat still stored in the house at the horizon end is credited at the horizon's mean
        # cost; the same (smallest) retention for every hour, so the credit itself never moves
        # heat towards the end of the horizon. tv_k = 0 (default 'full' mode): every hour is
        # credited at the horizon's mean cost of the same heat, so only differences between hours
        # (outdoor temperature, supply temperature) and starts are priced, not the heat itself:
        # how much heat the house needs is decided by comfort alone.
        q_ref = self._q_ref
        if self.tv_full:
            t_m = sum(to) / n
            pl_ref = 1.0 + _interp(t_m, (-10.0, 0.0, 7.0), (0.165, 0.12, 0.083)) * max(0.0, 5.5 - q_ref)
            tv = q * pl_ref * sum(1.0 / self._cop(t_m + self.cop_timing * (t - t_m)) for t in to) / n
        else:
            tv = self.tv_k * mean_cost * q * (gE[n] if self.tv_flat else 0.0)
        # supply-temperature reference: the steady slab for the mean load, plus the block's lift
        p_mean = max(0.5, sum(load) / len(load)) if load else 2.0
        ts_ss = (p_mean + self.k_sa * aim + self.h_g * 10.0) / (self.k_sa + self.h_g)
        tsup_ref = ts_ss + q_ref / self.k_emit if self.tv_full else 30.0
        ta = ta_f[:]
        ts = ts_f[:]
        u = [0] * n
        total = lam * sum(abs(ta[j] - aim) for j in range(1, n + 1))
        # no systematic offset: the mean deviation over the next n_mean hours is priced too
        nm = min(n, self.n_mean)
        lm = self.lam_mean
        sdev = sum(ta[j] - aim for j in range(1, nm + 1))
        total += lm * abs(sdev)
        if running and self.run_min < self.min_run:
            forced = max(1, int(math.ceil((self.min_run - self.run_min) / 60.0)))
        else:
            forced = 0
        blocked = (not running) and self.off_min < self.min_off

        def step_cost(k):
            # supply temperature of the hour: the block's lift above the slab, plus (sup_slab) the
            # slab's predicted departure from its steady level for the load
            tsup = ts_ss + self.sup_slab * (ts[k] - ts_ss) + q / self.k_emit
            el = el_base[k] * math.exp(self.sup_pen * (tsup - tsup_ref))
            if not self.tv_flat and not self.tv_full:
                return el - self.tv_k * mean_cost * q * gE[n - k]
            return el - tv

        def add(k):
            for j in range(k + 1, n + 1):
                ta[j] += q * ga[j - k]
                ts[j] += q * gs[j - k]
            u[k] = 1

        for k in range(forced):
            old = sum(abs(ta[j] - aim) for j in range(k + 1, n + 1))
            total += step_cost(k)
            add(k)
            total += lam * (sum(abs(ta[j] - aim) for j in range(k + 1, n + 1)) - old)
        s_new = sum(ta[j] - aim for j in range(1, nm + 1))
        total += lm * (abs(s_new) - abs(sdev))
        sdev = s_new

        while True:
            best, best_k, best_len = 0.0, -1, 0
            for k in range(n):
                if u[k]:
                    continue
                ext = (k > 0 and u[k - 1]) or (k + 1 < n and u[k + 1]) or (k == 0 and running)
                if ext:
                    ln = 1
                    c = 0.0
                else:
                    if k == 0 and blocked:
                        continue
                    ln = self.min_block
                    if k + ln > n or any(u[k + i] for i in range(ln)):
                        continue
                    c = self.c_start
                for kk in range(k, k + ln):
                    c += step_cost(kk)
                dc = 0.0
                ds = 0.0
                for j in range(k + 1, n + 1):
                    add_t = 0.0
                    for kk in range(k, min(k + ln, j)):
                        add_t += ga[j - kk]
                    old = ta[j] - aim
                    dc += abs(old + q * add_t) - abs(old)
                    if j <= nm:
                        ds += q * add_t
                c += lam * dc + lm * (abs(sdev + ds) - abs(sdev))
                if c < best:
                    best, best_k, best_len, best_ds = c, k, ln, ds
            if best_k < 0:
                break
            total += best
            sdev += best_ds
            for kk in range(best_k, best_k + best_len):
                add(kk)
        if self.polish and lm == 0.0:
            total = self._polish(u, ta, q, aim, total, [step_cost(k) for k in range(n)], forced, running,
                                 blocked)
        self._ta_plan = ta
        self._ts_plan = ts
        return u, total

    def _polish(self, u, ta, q, aim, total, sc, forced, running, blocked):
        """Local search after the greedy fill (review-2: the greedy can strand a cold gap before
        a cheap warm stretch): flip single hours, or fill a whole off-gap between two blocks, while
        that lowers the plan cost and every block keeps its minimum length."""
        n, lam, ga = self.n_h, self.lam, self.ga

        def n_starts(v):
            s = 0
            for k in range(n):
                if v[k] and (k == 0 and not running or k > 0 and not v[k - 1]):
                    s += 1
            return s

        def feasible(v):
            if v[0] and blocked:
                return False
            k = 0
            while k < n:
                if v[k]:
                    j = k
                    while j < n and v[j]:
                        j += 1
                    cont = k == 0 and running
                    if not cont and j - k < self.min_block and j < n:
                        return False
                    k = j
                else:
                    k += 1
            return all(v[k] for k in range(forced))

        def delta(ks, sign):
            dc = 0.0
            for j in range(1, n + 1):
                add_t = 0.0
                for kk in ks:
                    if kk < j:
                        add_t += ga[j - kk]
                if add_t:
                    old = ta[j] - aim
                    dc += abs(old + sign * q * add_t) - abs(old)
            return lam * dc + sign * sum(sc[kk] for kk in ks)

        def apply(ks, sign):
            for kk in ks:
                for j in range(kk + 1, n + 1):
                    ta[j] += sign * q * ga[j - kk]
                u[kk] = 1 if sign > 0 else 0

        st = n_starts(u)
        for _ in range(4):
            improved = False
            moves = [[k] for k in range(forced, n)]
            k = 0
            while k < n:            # off-gaps between (or before) blocks
                if not u[k]:
                    j = k
                    while j < n and not u[j]:
                        j += 1
                    if j < n and j - k > 1 and k >= forced:
                        moves.append(list(range(k, j)))
                    k = j
                else:
                    k += 1
            for ks in moves:
                sign = -1 if u[ks[0]] else 1
                if any((u[kk] == 1) != (sign < 0) for kk in ks):
                    continue
                v = u[:]
                for kk in ks:
                    v[kk] = 0 if sign < 0 else 1
                if not feasible(v):
                    continue
                st_v = n_starts(v)
                dc = delta(ks, sign) + self.c_start * (st_v - st)
                if dc < -1e-6:
                    apply(ks, sign)
                    st = st_v
                    total += dc
                    improved = True
            if not improved:
                break
        return total

    # ------------------------------------------------------------------ step
    def step(self, obs: Observation) -> Command:
        self.link_quiet = self.link_quiet + 1 if obs.link_ok else 0
        a = 1.0 / (24 * 60)
        self.t_avg = obs.outdoor if self.t_avg is None else self.t_avg + a * (obs.outdoor - self.t_avg)
        mode = obs.mode
        if mode == "dhw" or (obs.link_ok and mode == "off" and obs.heating_enabled):
            self.since_dhw = 0
        else:
            self.since_dhw += 1
        if mode == "defrost":
            self.since_def = 0
        else:
            self.since_def += 1
        comp_heat = obs.compressor_on and mode in ("heat", "defrost")
        if comp_heat:
            self.run_min += 1
            self.off_min = 0
        else:
            self.run_min = 0
            self.off_min += 1
        # heat into the loop (measured)
        if obs.link_ok and comp_heat and self.since_dhw > 12:
            q_meas = CP_FLOW * (obs.outlet - obs.inlet + 0.3)
        elif not obs.link_ok and obs.compressor_on and mode == "heat":
            q_meas = self.q_plan
        else:
            q_meas = 0.0
        if comp_heat and obs.link_ok and mode == "heat" and self.since_dhw > 12 and self.since_def > 10:
            self.q_ema = q_meas if self.q_ema is None else self.q_ema + (q_meas - self.q_ema) / 20.0
        elif not comp_heat:
            self.q_ema = None
        fc = obs.forecast
        self._track_hours(obs)
        if fc:
            to_now = fc[0]["outdoor"]
            sun_now = self._now_val(obs, self._sun_of)
        else:
            to_now = self.t_avg
            sun_now = 0.0
        inlet_ok = (self.use_inlet and obs.link_ok and self.since_dhw > 20 and self.since_def > 10
                    and mode in ("heat", "idle") and ((comp_heat and self.run_min > 10)
                                                      or (not comp_heat and self.off_min > 10)))
        self._observe(obs, q_meas, sun_now, to_now, inlet_ok)

        running = comp_heat
        # replan
        if obs.minute - self.last_plan >= self.replan_min or (running != self.prev_comp):
            self.want = self._plan(obs, running)
            self.last_plan = obs.minute
        self.prev_comp = running

        if not obs.link_ok:
            return Command()
        if not obs.heating_enabled:
            # the owner (or Home Assistant) switched space heating off: respect it (review R7)
            return Command()
        cmd = self._execute(obs, running)
        if cmd.setpoint is not None:
            self.writes.append(obs.minute)
        return cmd

    # ------------------------------------------------------------------ executor
    def _write(self, obs, sp):
        sp = float(min(max(round(sp), PARK_SP), 45.0))
        if sp == obs.setpoint:
            return Command()
        return Command(setpoint=sp)

    def _n_writes(self, obs):
        cut = obs.minute - 1440
        while self.writes and self.writes[0] <= cut:
            self.writes.pop(0)
        return len(self.writes)

    def _park_pred(self, obs):
        """Highest park that the predicted slab keeps from starting the unit until the plan's next
        block (review-2 R6: one park write per stop instead of an hourly staircase)."""
        ts = getattr(self, "ts_pred", None)
        if not ts or not self.plan:
            return PARK_SP
        m = next((k for k, v in enumerate(self.plan) if v and k > 0), len(self.plan))
        m = max(1, min(m, 12, len(ts) - 1))
        ts_min = min(ts[:m + 1])
        return math.floor(ts_min + self.z[4] - 0.7 + obs.restart_delta - 0.8)

    def _park(self, obs):
        """Idle and planned off: hold the safety park, but never one that starts the unit now."""
        t_ctrl = obs.inlet - 0.7
        sp = min(self.park_sp, math.floor(t_ctrl + obs.restart_delta - 0.5))
        if self.park_pred:
            sp = min(sp, self._park_pred(obs))
        sp = max(sp, PARK_SP)
        # re-write only on a change of at least 1 K (whole degrees) and not in the first minutes
        # after a stop (the water still reads the run)
        if self.off_min < 3 or abs(sp - obs.setpoint) < 1.0:
            return Command()
        # lowering the park towards 25 is always safe; raising it costs a write, so only when the
        # write budget allows
        if sp > obs.setpoint and self._n_writes(obs) >= self.wr_hard:
            return Command()
        return self._write(obs, sp)

    def _execute(self, obs, running):
        mode = obs.mode
        if mode in ("dhw", "defrost", "off") or self.since_dhw < 10:
            return Command()
        if self.want:
            if not running:
                if self.off_min < self.min_off:
                    return self._park(obs)
                # soft start: the smallest setpoint the restart rule accepts
                sp = math.ceil(obs.inlet - 0.8 + obs.restart_delta + 0.15)
                self.ride_sp = None
                return self._write(obs, max(sp, obs.setpoint) if obs.setpoint > PARK_SP else sp)
            # ride: hold the block output at the lowest supply that delivers it
            nw = self._n_writes(obs)
            every = self.ride_every if nw < self.wr_soft else 60.0
            if nw >= self.wr_hard and self.run_min > 2:
                return Command()
            if obs.minute - self.last_ride >= every or self.run_min <= 2:
                q_r = self.q_plan
                if self.run_min < self.ride_soft_min:
                    q_r = min(q_r, max(self.q_base, self._q_min(obs.outdoor)))
                sp = obs.inlet + q_r / CP_FLOW + self.ride_off
                sp = max(sp, obs.outlet - 0.5 - 1.5)   # never write a stop by accident
                # hysteresis on the continuous target: no flapping across a rounding edge
                if self.run_min > 2 and abs(sp - obs.setpoint) < self.ride_hyst:
                    return Command()
                # ...except in the 20 min before each 120-min surge mark, where a setpoint that has
                # fallen behind the warming loop lets the surge stop the run (UNIT_MODEL 3.3)
                pre_surge = self.run_min % 120 >= 100
                if pre_surge and self.q_tol > 0 and sp < obs.setpoint:
                    return Command()   # before the mark only a lagging (too low) setpoint is fixed
                if (self.q_tol > 0 and not pre_surge and self.run_min > self.ride_soft_min + 15 and self.q_ema is not None
                        and self.q_rode is not None and abs(q_r - self.q_rode) < 0.5):
                    miss = q_r - self.q_ema   # > 0: delivering too little
                    if not ((sp > obs.setpoint and miss > self.q_tol) or (sp < obs.setpoint and miss < -self.q_tol)):
                        return Command()
                cmd = self._write(obs, sp)
                if cmd.setpoint is not None:
                    self.last_ride = obs.minute
                    self.q_rode = q_r
                return cmd
            return Command()
        # plan says off
        if running:
            if self.run_min < self.min_run:
                return Command()
            # stop: a write that puts the control sensor (outlet - 0.5 K while running) 2 K above
            # the setpoint stops at once; with park_pred it lands directly on the park (1 K margin)
            sp = PARK_SP
            if self.park_pred:
                sp = max(PARK_SP, min(self.park_sp, self._park_pred(obs), math.floor(obs.outlet - 3.5)))
            return self._write(obs, sp)
        return self._park(obs)


CONTROLLER = BlockScheduler


if __name__ == "__main__":
    from datetime import datetime, timedelta, timezone

    c = BlockScheduler()
    c.reset({})
    t0 = datetime(2026, 1, 10, 0, 0, tzinfo=timezone.utc)
    fc = tuple({"time": t0 + timedelta(hours=h + 1), "outdoor": 0.0, "rh": 85, "ghi": 0.0, "dni": 0.0,
                "dhi": 0.0, "cloud": 100} for h in range(48))
    base = dict(time=t0, local_hour=2.0, room=21.4, room_age_min=5, outdoor=0.0, outlet=25.5, inlet=25.8,
                setpoint=25.0, restart_delta=5.0, quiet=False, heating_enabled=True, compressor_on=False,
                mode="idle", electric_kw=0.02, energy_kwh=0.0, target=22.0, forecast=fc, pv_kw=None)
    cmds = [c.step(Observation(minute=m, **base)) for m in range(5)]
    assert any(x.setpoint and x.setpoint >= 30 for x in cmds), "a cold room at 0 degC must start a block"
    # warm room, mild weather: no block now
    c.reset({})
    fcm = tuple({**h, "outdoor": 10.0} for h in fc)
    o = Observation(minute=0, **{**base, "room": 22.6, "forecast": fcm, "outdoor": 10.0})
    sp_w = c.step(o).setpoint
    assert sp_w is None or sp_w - (o.inlet - 0.7) < o.restart_delta, "a warm room in mild weather must not start"
    # fail-safes
    c.reset({})
    assert c.step(Observation(minute=0, link_ok=False, **base)) == Command(), "no writes while the link is down"
    c.step(Observation(minute=1, **{**base, "room": None, "forecast": ()}))
    c.step(Observation(minute=2, **{**base, "mode": "dhw", "compressor_on": True}))
    # sun position sanity: noon in January is in the south, low
    el, az = _sun(datetime(2026, 1, 10, 10, 30, tzinfo=timezone.utc))
    assert 0.1 < el < 0.3 and abs(math.degrees(az) - 180) < 15, (math.degrees(el), math.degrees(az))
    print("self-check ok")
