"""Self-learning heating curve (strategy S11: room-trajectory auto-adaptation), stdlib only.

The leaving-water setpoint is a weather curve on an *effective* outdoor temperature (the mean
forecast of the next 12 hours; see the forecast fallback below) minus the
cooling the forecast sun calls for, plus a room-feedback trim. The curve's offset, slope and sun
weight are learned online from how the room responded: every day the controller forms one sample

    y = mean setpoint it applied (without the fast P term) + G x mean room error

('the setpoint that would have held the room on target that day', residual clipped to +-3 K)
against the day's mean (target - effective outdoor) and forecast sun, and refits the curve by a
ridge-regularised weighted least-squares fit over the recent samples (daily forgetting, a weak
pull towards the initial curve; slope bounded to 0.15-0.9 K/K). A change of the curve is handed over bumplessly to the integral,
so the setpoint never jumps when the curve learns.

The default initial curve is a sensible one for this house (c0 4, c1 0.18, c2 8); `c0=0,c1=0.5,c2=0`
reproduces the deliberately poor start of the first version, and `learn=0` freezes the curve. The
learned state can be exported with `snapshot()` and handed back through `reset({'state': ...})`
(a deployment persists it across restarts).

Execution (review fixes): whole-degree setpoints with 0.9 K hysteresis, a 40-minute dwell, at most
3 K per write, 25-39 degC; a downward write during a heat run is held above the firmware's
immediate-stop threshold unless the room is clearly warm; no upward write in the 2 hours after a
compressor start (the firmware's start burst is not pushed harder); the P and trajectory parts are
capped.
Writes: a value is sent when the controller decides it, re-sent at most twice if the unit does not
show it, then the reported value is adopted and the controller backs off; a rolling 24-hour budget
caps all writes. The restart hysteresis is written once at take-over; the space-heating switch is
never touched, and while the owner has heating off the controller writes nothing and freezes its
integral, mean-error aim and learning; DHW and defrost minutes also freeze them.

Only the Observation is used. Fail-safe: with the room sensor stale or missing the trim freezes and
the curve alone runs. Forecast fallback: the last forecast received is used (shifted to the
current hour) for up to 36 h; after that a persistence forecast stands in (each hour of yesterday's
sun-corrected unit sensor plus today's anomaly over the last 3 h, and 0.7 x yesterday's PV-derived
irradiance); with less than a day of history the filtered unit sensor and no sun term. During a
link outage nothing is written.
"""
from __future__ import annotations

import math

from lab.sim.interface import Command, Observation

GLOW_K_PER_WM2 = 0.0008      # thermometer reads warm in sun (HOUSE_MODEL: 0.8 mK per W/m2 GHI)
PV_KW_PER_KWM2 = 8.9          # PV output per kW/m2 of global irradiance (SIMULATOR section 4)


def _clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def _solve3(A, b):
    """Gaussian elimination with partial pivoting for a 3x3 system."""
    M = [list(A[i]) + [b[i]] for i in range(3)]
    for c in range(3):
        piv = max(range(c, 3), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-12:
            return None
        M[c], M[piv] = M[piv], M[c]
        for r in range(c + 1, 3):
            f = M[r][c] / M[c][c]
            for k in range(c, 4):
                M[r][k] -= f * M[c][k]
    x = [0.0] * 3
    for i in (2, 1, 0):
        x[i] = (M[i][3] - sum(M[i][k] * x[k] for k in range(i + 1, 3))) / M[i][i]
    return x


class SelfLearningCurve:
    name = "self_learning_curve"

    # ------------------------------------------------------------------ setup
    def reset(self, params: dict) -> None:
        p = params
        g = lambda k, d: float(p.get(k, d))  # noqa: E731
        # curve: sp = target + c0 + c1 * (target - T_eff) - c2 * G   (G: mean forecast GHI, kW/m2)
        self.c = [g("c0", 4.0), g("c1", 0.18), g("c2", 8.0)]
        self.learn = bool(int(p.get("learn", 1)))
        self.lam = g("lam", 0.98)                  # daily forgetting factor of the samples
        self.memory = int(g("memory_d", 120))       # days of samples kept
        # ridge weights (days of perfect data equivalent) pulling towards the initial curve
        self.ridge = [g("r0", 0.5), g("r1", 5.0), g("r2", 5.0)]
        self.g_room = g("g_room", 1.5)             # K of setpoint per K of daily mean room error
        self.xc = g("x_centre", 17.0)              # centre of the slope regressor (K of target - T_eff)
        self.y_clip = g("y_clip", 3.0)             # clip of one day's residual against the curve
        # feedback
        self.kp = g("kp", 4.0)                     # K water per K of (predicted) room error
        self.ki = g("ki", 0.3)                     # K water per K-hour
        self.i_lim = g("i_lim", 4.0)
        self.td_h = g("td_h", 2.0)                 # look-ahead on the room trajectory, hours
        self.slope_win = int(g("slope_win", 180))  # minutes of room history for the slope
        self.d_max = g("d_max", 1.5)               # cap of the trajectory part (K of setpoint)
        self.fb_max = g("fb_max", 3.0)             # cap of P + trajectory (K of setpoint)
        self.glow = bool(int(p.get("glow", 1)))
        # weather input
        self.fc_h0 = int(g("fc_h0", 0))
        self.fc_h1 = int(g("fc_h1", 12))
        self.sun_h0 = int(g("sun_h0", 1))
        self.sun_h1 = int(g("sun_h1", 10))
        self.tau_out = g("tau_out_h", 3.0) * 60
        self.fc_keep_h = g("fc_keep_h", 36.0)       # use a cached forecast this long after it stopped
        self.persist_sun = g("persist_sun", 0.7)    # weight of yesterday's sun in the persistence forecast
        self.persist = bool(int(p.get("persist", 1)))
        # curve bounds (physics: water-to-room needs about 0.3 K per K outdoors at the outlet; the
        # setpoint slope is lower because cold-weather water rides above it, but not below ~half)
        self.c1_min = g("c1_min", 0.15)
        self.c1_max = g("c1_max", 0.9)
        self.c2_max = g("c2_max", 20.0)
        self.freeze_dhw = bool(int(p.get("freeze_dhw", 1)))
        # execution
        self.sp_min = g("sp_min", 25.0)
        self.sp_max = g("sp_max", 39.0)
        self.hyst = g("hyst", 0.9)
        self.min_dwell = int(g("min_dwell", 40))
        self.max_step = g("max_step", 3.0)          # K per write
        self.stop_guard = bool(int(p.get("stop_guard", 1)))
        self.stop_margin = g("stop_margin", 0.5)    # K kept below the outlet + 2 K immediate-stop line
        self.warm_stop = g("warm_stop", 0.4)        # room this much over target: a stop is wanted
        self.period = int(g("period", 5))
        self.soft_k = g("soft_k", 0.0)              # K the setpoint is lowered right after a start
        self.soft_min = int(g("soft_min", 30))      # for this many minutes (softer first burst)
        self.up_hold = int(g("up_hold", 120))       # no upward write this many minutes after a start
        self.delta = p.get("restart_delta", 5)
        self.room_stale = g("room_stale_min", 240)
        self.k_mean = g("k_mean", 1.0)              # aim correction per K of long-run mean error
        self.mean_tau = g("mean_tau_d", 7.0) * 1440
        self.aim_max = g("aim_max", 0.3)            # cap of the aim shift, K
        self.mean_tau0 = g("mean_tau0_d", 1.0) * 1440   # shorter averaging while history is short
        # write discipline
        self.budget = int(g("write_budget", 36))    # writes in any rolling 24 h
        self.retries = int(g("retries", 2))         # re-sends of one value the unit does not show
        self.retry_gap = int(g("retry_gap", 15))    # minutes between re-sends
        self.backoff = int(g("backoff_min", 360))   # minutes without setpoint writes after a refusal

        self.fc_cache = ()
        self.was_on = False
        self.soft_until = -1
        self.soft_base = None
        self.last_start = -10 ** 9
        self.fc_cache_t = None
        self.hours = {}                # hour index -> [sum outdoor, sum ghi, n] (persistence forecast)
        self.fc_src = "none"
        self.mean_err = 0.0
        self.mean_n = 0.0                            # minutes of room history in mean_err
        self.integral = 0.0
        self.t_meas = None
        self.err_f = None
        self.hist = []                 # (minute, room estimate)
        self.current = None            # register value the controller wants on the unit
        self.last_change = -10 ** 9    # minute the controller last decided a new value
        self.sent_at = None            # minute of the last send of `current`
        self.sends = 0                 # sends of the current value
        self.backoff_until = -1
        self.write_log = []            # minutes of all writes sent (rolling budget)
        self.delta_tries = 0
        self.day = None
        self.acc = None
        self.c_init = list(self.c)
        self.samples = []              # (x = target - t_eff, sun, y) per day, newest last
        self.n_learn = 0
        self.last_x = 17.0
        self.last_g = 0.0
        self.want = None
        self.base_now = 0.0
        self.err_now = None
        self.log = []                  # (day, c0, c1, c2) for diagnostics
        st = p.get("state")
        if isinstance(st, dict):
            self.restore(st)

    # ----------------------------------------------------------- persistence
    def snapshot(self) -> dict:
        """Learned state for a deployment to store (JSON-serialisable)."""
        return {"c": list(self.c), "c_init": list(self.c_init), "integral": self.integral,
                "mean_err": self.mean_err, "mean_n": self.mean_n,
                "samples": [list(s) for s in self.samples]}

    def restore(self, st: dict) -> None:
        try:
            c = [float(v) for v in st.get("c", self.c)]
            if len(c) == 3 and all(math.isfinite(v) for v in c):
                self.c = [_clamp(c[0], -6.0, 10.0), _clamp(c[1], self.c1_min, self.c1_max),
                          _clamp(c[2], 0.0, self.c2_max)]
            ci = [float(v) for v in st.get("c_init", self.c_init)]
            if len(ci) == 3 and all(math.isfinite(v) for v in ci):
                self.c_init = ci
            self.integral = _clamp(float(st.get("integral", 0.0)), -self.i_lim, self.i_lim)
            self.mean_err = _clamp(float(st.get("mean_err", 0.0)), -1.0, 1.0)
            self.mean_n = max(0.0, float(st.get("mean_n", 0.0)))
            self.samples = [tuple(float(v) for v in s) for s in st.get("samples", [])
                            if len(s) == 3][-self.memory:]
        except (TypeError, ValueError):
            pass

    # ------------------------------------------------------------ estimators
    @staticmethod
    def _ghi_now(obs):
        if obs.pv_kw is not None:
            return max(0.0, obs.pv_kw) * 1000.0 / PV_KW_PER_KWM2
        fc = obs.forecast or ()
        if fc and fc[0].get("ghi") is not None:
            return float(fc[0]["ghi"])
        return 0.0

    def _forecast(self, obs, meas, ghi):
        """The live forecast; else the last one received (aged out); else a persistence forecast
        built from the last 24 h of the unit's sun-corrected sensor and the PV-derived irradiance."""
        hr = obs.minute // 60
        b = self.hours.get(hr)
        if b is None:
            b = self.hours[hr] = [0.0, 0.0, 0]
            for k in [k for k in self.hours if k < hr - 49]:
                del self.hours[k]
        b[0] += meas
        b[1] += ghi
        b[2] += 1
        fc = obs.forecast or ()
        if fc:
            self.fc_cache, self.fc_cache_t = fc, obs.minute
            self.fc_src = "live"
            return fc
        if self.fc_cache and obs.minute - self.fc_cache_t <= self.fc_keep_h * 60:
            rest = tuple(h for h in self.fc_cache if h.get("time") is None or h["time"] > obs.time)
            if len(rest) >= self.fc_h1:
                self.fc_src = "cached"
                return rest
        if not self.persist:
            self.fc_src = "none"
            return ()
        # persistence: tomorrow's hour = yesterday's hour + today's anomaly (last 3 h vs a day before)
        def mean_t(k0, k1):
            v = [self.hours[k][0] / self.hours[k][2] for k in range(k0, k1) if k in self.hours]
            return sum(v) / len(v) if v else None
        now3, then3 = mean_t(hr - 2, hr + 1), mean_t(hr - 26, hr - 23)
        if now3 is None or then3 is None:
            self.fc_src = "none"
            return ()
        anom = now3 - then3
        out = []
        for h in range(max(self.fc_h1, self.sun_h1)):
            k = hr + 1 + h - 24
            bk = self.hours.get(k)
            if bk is None or bk[2] == 0:
                return ()
            out.append({"outdoor": bk[0] / bk[2] + anom, "ghi": self.persist_sun * bk[1] / bk[2]})
        self.fc_src = "persist"
        return tuple(out)

    def _weather(self, obs):
        """Effective outdoor temperature for the curve and the forecast sun (kW/m2)."""
        ghi = self._ghi_now(obs)
        # the unit's sensor reads warm in sun (about 0.012 K per W/m2 while idle): strip most of it
        meas = obs.outdoor - (0.010 if not obs.compressor_on else 0.003) * ghi
        a = 1.0 / self.tau_out
        self.t_meas = meas if self.t_meas is None else self.t_meas + a * (meas - self.t_meas)
        fc = self._forecast(obs, meas, ghi)
        temps = [h["outdoor"] for h in fc[self.fc_h0:self.fc_h1] if h.get("outdoor") is not None]
        t_eff = sum(temps) / len(temps) if temps else self.t_meas
        sun = [h.get("ghi") or 0.0 for h in fc[self.sun_h0:self.sun_h1]]
        g_sun = sum(sun) / len(sun) / 1000.0 if sun else 0.0
        return t_eff, g_sun, ghi

    def curve(self, x, g_sun):
        """Water above target for x = target - T_eff (K) and forecast sun g_sun (kW/m2)."""
        c0, c1, c2 = self.c
        return c0 + c1 * x - c2 * g_sun

    def _room(self, obs, ghi):
        if obs.room is None or obs.room_age_min > self.room_stale:
            return None
        r = obs.room
        if self.glow:
            r -= GLOW_K_PER_WM2 * ghi
        return r

    def _slope(self):
        """Room trend (K/h) from a least-squares line over the recent history."""
        h = self.hist
        if len(h) < 10 or h[-1][0] - h[0][0] < self.slope_win * 0.7:
            return 0.0
        n = len(h)
        mx = sum(x for x, _ in h) / n
        my = sum(y for _, y in h) / n
        sxx = sum((x - mx) ** 2 for x, _ in h)
        if sxx <= 0:
            return 0.0
        sxy = sum((x - mx) * (y - my) for x, y in h)
        return sxy / sxx * 60.0

    # -------------------------------------------------------------- learning
    def _learn(self):
        """One daily sample, then a ridge-regularised weighted least-squares refit of the curve."""
        a = self.acc
        if a is None or a["n"] < 18 * 60 or a["ne"] < 12 * 60:
            return
        x = a["x"] / a["n"]
        gs = a["g"] / a["n"]
        e = a["e"] / a["ne"]
        u = a["u"] / a["n"]
        y = u + self.g_room * e
        pred = self.curve(x, gs)
        y = pred + _clamp(y - pred, -self.y_clip, self.y_clip)
        self.samples.append((x, gs, y))
        if len(self.samples) > self.memory:
            self.samples.pop(0)
        # normal equations in the centred slope variable (decouples offset and slope)
        A = [[0.0] * 3 for _ in range(3)]
        b = [0.0] * 3
        w = 1.0
        for (xi, gi, yi) in reversed(self.samples):
            r = (1.0, xi - self.xc, -gi)
            for i in range(3):
                b[i] += w * r[i] * yi
                for j in range(3):
                    A[i][j] += w * r[i] * r[j]
            w *= self.lam
        # prior in the same coordinates: offset at the centre, slope, sun
        c0, c1, c2 = self.c_init
        prior = (c0 + c1 * self.xc, c1, c2)
        scale = (1.0, 25.0, 0.01)      # typical regressor magnitude^2: (K)^2 spread, (kW/m2)^2
        for i in range(3):
            r = self.ridge[i] * scale[i]
            A[i][i] += r
            b[i] += r * prior[i]
        th = _solve3(A, b)
        if th is None:
            return
        m, c1n, c2n = th
        c1n = _clamp(c1n, self.c1_min, self.c1_max)
        c2n = _clamp(c2n, 0.0, self.c2_max)
        c0n = _clamp(m - c1n * self.xc, -6.0, 10.0)
        old = self.curve(self.last_x, self.last_g)
        self.c = [c0n, c1n, c2n]
        new = self.curve(self.last_x, self.last_g)
        self.integral = _clamp(self.integral + old - new, -self.i_lim, self.i_lim)
        self.n_learn += 1

    # ------------------------------------------------------------- execution
    def _decide(self, obs, m):
        """New register value from `want`, with hysteresis, dwell, step limit and the stop guard."""
        want = self.want
        if self.soft_base is not None:
            if m < self.soft_until and obs.compressor_on and obs.mode == "heat":
                floor = math.ceil(obs.outlet - 2.0 + self.stop_margin + 0.5)
                return float(max(self.soft_base - self.soft_k, floor, self.sp_min))
            # window over: back to the normal rules at once
            base, self.soft_base = self.soft_base, None
            self.last_change = -10 ** 9
            if abs(want - base) < self.hyst:
                return base
        if self.current is None:
            return float(round(_clamp(want, obs.setpoint - self.max_step, obs.setpoint + self.max_step)))
        if m < self.backoff_until:
            return self.current
        if abs(want - self.current) < self.hyst or m - self.last_change < self.min_dwell:
            return self.current
        step = _clamp(round(want) - self.current, -self.max_step, self.max_step)
        if step > 0 and m - self.last_start < self.up_hold:
            return self.current
        new = self.current + step
        if (step < 0 and self.stop_guard and obs.compressor_on and obs.mode == "heat"
                and not (self.err_now is not None and self.err_now < -self.warm_stop)):
            # the firmware stops at once when a write puts the control sensor >= setpoint + 2 K;
            # the outlet stands in for it. Keep the run going unless the room is clearly warm.
            floor = math.ceil(obs.outlet - 2.0 + self.stop_margin)
            new = max(new, float(floor))
            if new >= self.current:
                return self.current
        return float(new)

    def _budget_ok(self, m):
        while self.write_log and self.write_log[0] <= m - 1440:
            self.write_log.pop(0)
        return len(self.write_log) < self.budget

    # ------------------------------------------------------------------ step
    def step(self, obs: Observation) -> Command:
        t_eff, g_sun, ghi = self._weather(obs)
        x = obs.target - t_eff
        self.last_x, self.last_g = x, g_sun
        room = self._room(obs, ghi)
        m = obs.minute
        heating = obs.heating_enabled and obs.mode != "off"
        # DHW and defrost pause space heating: the room drifts for reasons the curve cannot fix,
        # so the integral, the mean-error aim and the learning sample do not count those minutes
        if self.freeze_dhw and obs.mode in ("dhw", "defrost"):
            heating = False
        if room is not None:
            if not self.hist or self.hist[-1][1] != room or m - self.hist[-1][0] >= 15:
                self.hist.append((m, room))
            while self.hist and self.hist[0][0] < m - self.slope_win:
                self.hist.pop(0)
        else:
            self.hist = []

        # daily learning sample
        day = int(obs.time.timestamp() // 86400)  # UTC day (02-03 local): a quiet hour to learn
        if self.day != day:
            if self.learn and self.acc is not None:
                self._learn()
                self.log.append((day, *self.c))
                del self.log[:-400]
            self.day = day
            self.acc = {"n": 0, "x": 0.0, "g": 0.0, "u": 0.0, "e": 0.0, "ne": 0}

        if m % self.period == 0 or self.want is None:
            err = None
            if room is not None:
                err = obs.target - room
                if heating:
                    # long-run mean error: sun and occupants push the room warm in hours the heating
                    # cannot cool; aim that much lower elsewhere so the mean stays on target. The
                    # averaging window grows from 1 to 7 days so a fresh start re-aims quickly.
                    self.mean_n += self.period
                    tau = _clamp(self.mean_n, self.mean_tau0, self.mean_tau)
                    self.mean_err += (err - self.mean_err) * self.period / tau
                aim = _clamp(self.k_mean * self.mean_err, -self.aim_max, self.aim_max)
                e_c = err + aim
                self.err_f = e_c if self.err_f is None else self.err_f + (e_c - self.err_f) * min(1.0, self.period / 20.0)
                if heating:
                    self.integral = _clamp(self.integral + self.ki * e_c * self.period / 60.0, -self.i_lim, self.i_lim)
            base = self.curve(x, g_sun) + self.integral
            fb = 0.0
            if self.err_f is not None and room is not None:
                d = _clamp(self.kp * self.td_h * self._slope(), -self.d_max, self.d_max)
                fb = _clamp(self.kp * self.err_f - d, -self.fb_max, self.fb_max)
            self.want = _clamp(obs.target + base + fb, self.sp_min, self.sp_max)
            self.base_now = base
            self.err_now = err

        ac = self.acc
        if heating:
            ac["n"] += 1
            ac["x"] += x
            ac["g"] += g_sun
            ac["u"] += self.base_now
            if self.err_now is not None:
                ac["e"] += self.err_now
                ac["ne"] += 1

        if not obs.link_ok or not obs.heating_enabled:
            # link down: commands would wait; space heating off: the owner's choice, leave the unit alone
            return Command()
        cmd = {}
        on = obs.compressor_on and obs.mode == "heat"
        if (self.soft_k > 0 and on and not self.was_on and self.current is not None
                and self.soft_base is None and m >= self.backoff_until):
            self.soft_base, self.soft_until = self.current, m + self.soft_min
        if on and not self.was_on:
            self.last_start = m
        self.was_on = on
        new = self._decide(obs, m)
        if new != self.current:
            self.current = new
            self.last_change = m
            self.sends = 0
            self.sent_at = None
        if obs.setpoint != self.current:
            if self.sends > self.retries:
                # the unit does not take the value (installer limit, refused write): adopt what it
                # reports and leave it alone for a while
                self.current = float(obs.setpoint)
                self.backoff_until = m + self.backoff
                self.sends = 0
            elif (self.sent_at is None or m - self.sent_at >= self.retry_gap) and self._budget_ok(m):
                cmd["setpoint"] = self.current
                self.sent_at = m
                self.sends += 1
                self.write_log.append(m)
        # restart hysteresis: once at take-over (never fight a later change by the owner)
        if self.delta is not None and self.delta_tries < 3:
            if obs.restart_delta == float(self.delta):
                self.delta_tries = 3
            elif self._budget_ok(m):
                cmd["restart_delta"] = float(self.delta)
                self.delta_tries += 1
                self.write_log.append(m)
        return Command(**cmd) if cmd else Command()


CONTROLLER = SelfLearningCurve


def _self_check():
    from datetime import datetime, timedelta, timezone

    t0 = datetime(2025, 11, 1, tzinfo=timezone.utc)
    fc = tuple({"time": t0 + timedelta(hours=h + 1), "outdoor": 0.0, "rh": 90, "ghi": 0.0, "dni": 0.0,
                "dhi": 0.0, "cloud": 100} for h in range(48))

    def ob(minute, room=22.0, link=True, forecast=fc, outdoor=0.0, setpoint=30.0, heating=True, delta=5,
           comp=False, outlet=28.0):
        return Observation(time=t0 + timedelta(minutes=minute), local_hour=(2 + minute / 60) % 24, room=room,
                           room_age_min=5, outdoor=outdoor, outlet=outlet, inlet=outlet - 2, setpoint=setpoint,
                           restart_delta=delta, quiet=False, heating_enabled=heating, compressor_on=comp,
                           mode="heat" if comp else "idle", electric_kw=0.0, energy_kwh=0.0, target=22.0,
                           forecast=forecast, pv_kw=0.0, minute=minute, link_ok=link)

    c = SelfLearningCurve()
    c.reset({})
    cmd = c.step(ob(0, setpoint=35.0))
    assert cmd.setpoint == 32.0                            # wants 30, at most 3 K from the unit's 35
    assert cmd.restart_delta is None and cmd.heating_enabled is None
    # link down: nothing is written
    assert c.step(ob(1, link=False, setpoint=20.0)) == Command()
    # no room, no forecast: still a sane setpoint from the curve and the unit's sensor
    c2 = SelfLearningCurve()
    c2.reset({})
    cmd = c2.step(ob(0, room=None, forecast=(), outdoor=-10.0))
    assert cmd.setpoint is not None and 25 <= cmd.setpoint <= 39
    # a cold room raises the request, a warm one lowers it
    lo, hi = SelfLearningCurve(), SelfLearningCurve()
    lo.reset({})
    hi.reset({})
    for m in range(0, 600):
        lo.step(ob(m, room=22.6))
        hi.step(ob(m, room=21.4))
    assert hi.want > lo.want + 2
    # learning: a room that stays 0.5 K cold for days pulls the curve up, within its bounds
    c3 = SelfLearningCurve()
    c3.reset({})
    before = c3.curve(22.0, 0.0)
    for m in range(0, 5 * 1440):
        c3.step(ob(m, room=21.5, setpoint=c3.current or 30.0))
    assert c3.n_learn >= 4 and c3.curve(22.0, 0.0) > before
    assert 0.05 <= c3.c[1] <= 0.9 and 0.0 <= c3.c[2] <= 20.0
    # persistence round trip
    c3b = SelfLearningCurve()
    c3b.reset({"state": c3.snapshot()})
    assert c3b.c == c3.c and len(c3b.samples) == len(c3.samples)
    # a unit that never takes the value (installer limit at 30): bounded writes, then adoption
    c4 = SelfLearningCurve()
    c4.reset({})
    writes = 0
    for m in range(1440):
        cmd = c4.step(ob(m, room=20.0, outdoor=-12.0, setpoint=30.0))
        writes += sum(v is not None for v in (cmd.setpoint, cmd.restart_delta, cmd.heating_enabled))
    assert writes <= 24, writes
    # heating switched off by the owner: never re-enabled, integral frozen
    c5 = SelfLearningCurve()
    c5.reset({})
    for m in range(600):
        cmd = c5.step(ob(m, room=20.0, heating=False))
        assert cmd == Command()
    assert c5.integral == 0.0
    # restart hysteresis changed by the owner later: not fought
    c6 = SelfLearningCurve()
    c6.reset({})
    c6.step(ob(0))
    assert all(c6.step(ob(m, delta=4)).restart_delta is None for m in range(1, 300))
    # a downward write during a run does not cross the immediate-stop line (room near target)
    c7 = SelfLearningCurve()
    c7.reset({"c0": 0.0})
    c7.current, c7.last_change, c7.want, c7.err_now = 34.0, -100, 28.0, 0.0
    assert c7._decide(ob(0, setpoint=34.0, comp=True, outlet=33.0), 0) >= 32.0
    # bounded write rate with a swinging room
    w, sp = 0, 30.0
    c8 = SelfLearningCurve()
    c8.reset({})
    for m in range(1440):
        cmd = c8.step(ob(m, room=22.0 + 0.5 * ((m // 90) % 2), setpoint=sp))
        if cmd.setpoint is not None and cmd.setpoint != sp:
            sp = cmd.setpoint
            w += 1
    assert w <= 36, w
    # forecast lost: cached forecast first, then a persistence forecast from the unit's history
    c9 = SelfLearningCurve()
    c9.reset({})
    for m in range(0, 60 * 60):
        c9.step(ob(m, forecast=fc if m < 60 else (), outdoor=-5.0))
        if m == 600:
            assert c9.fc_src == "cached"
    assert c9.fc_src == "persist" and abs(c9.last_x - 27.0) < 0.5, (c9.fc_src, c9.last_x)
    # no upward write in the 2 h after a compressor start
    c10 = SelfLearningCurve()
    c10.reset({})
    c10.current, c10.last_change, c10.want, c10.last_start = 30.0, -100, 34.0, -30
    assert c10._decide(ob(0, setpoint=30.0, comp=True), 0) == 30.0
    c10.last_start = -200
    assert c10._decide(ob(0, setpoint=30.0, comp=True), 0) == 33.0
    print("self_learning_curve self-check ok")


if __name__ == "__main__":
    _self_check()
