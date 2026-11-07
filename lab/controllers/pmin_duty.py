"""Duty-cycle controller for a heat pump whose smallest output exceeds the house's need
(stdlib only). Design notes, tuning record and results: docs/research/lab/controllers/pmin_duty.md.

The house cannot absorb the unit's minimum output above about 0 degC, so the compressor must
cycle; the floor slab is the buffer. The controller manages the *slab*, which it sees through
the water temperatures (the circulation pump never stops), and leaves the room to the slab:

1. **Slab target** Ts*: target + b x (target - forecast outdoor) - s x forecast sun + ts0, plus
   room feedback (kp x error + a trim integral), a curve over outdoor temperature that the
   persistent part of the trim moves into (learns offset and slope), a learned daily pattern
   (iterative learning: the room error at hour h moves the target at hour h - 5 h) and a small
   bias towards heating in the warmer hours of the day (COP and frost).
2. **Slab estimate.** Idle: the loop water has the slab's temperature, so Ts = inlet. Running:
   return = slab + (1 - eff) x (supply - slab), so Ts = (inlet - (1 - eff) x supply) / eff.
3. **Duty cycle.** A run starts when Ts < Ts* - band and stops when Ts > Ts* + band (minimum
   on/off times): a slab thermostat, so the run fraction is the heat need over the run output
   by construction and the band (slab swing) sets run length and starts per day.
4. **Run execution** (S6 riding): kick with the smallest setpoint the restart rule accepts,
   then ride the setpoint at return + Q_run / (cp x flow) so the firmware's error loop holds
   the chosen output. Stop by writing a park setpoint at least 2 K under the control sensor
   (the firmware stops at once). When the slab falls behind (cold) the ride output rises with
   the deficit, which becomes continuous modulation below the balance point.
   Q_run defaults to 6.5 kW, not the unit's minimum: in this unit's measured COP map the
   minimum output (3.6-4.4 kW) is 10-25 % less efficient than 6-7 kW at the supply the slab
   needs, so the literal P_min variant (q_run=0) loses about 3 % of energy (see the doc).

Fail-safe: link down -> nothing is written; while parked the setpoint follows the slab target
so the firmware itself would restart the unit if the slab ran low during an outage; room
missing or stale -> the short-term trim fades and the learned curve plus forecast carry on; a
room value that keeps being reported but has not moved 0.1 K in 12 h counts as stale too, and
the learning it caused is rolled back (`room_frozen`, an alert for Home Assistant);
forecast missing -> a 24 h mean of the unit's outdoor sensor; hot water and defrost freeze
the slab estimate and the run waits for the unit; a rolling 24 h write budget limits riding.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import replace

from lab.sim.interface import Command, Observation

PARK_SP = 25.0      # setpoint while parked (lowest ever written to the real unit)
KF = 2.02           # kW per K of loop delta-T (29 L/min); scale only
CTRL_RUN = -0.80    # control sensor - true supply while running (UNIT_MODEL.md 2)
CTRL_IDLE = -0.80   # control sensor - inlet while idle (effective start offset)
OUTLET_OFF = 0.30   # true supply - outlet sensor
CURVE_T = (-25.0, -15.0, -5.0, 5.0, 15.0)  # knots of the learned slab-target curve, degC outdoor
CURVE0 = "0,0,0,0,0"  # prior of the learned curve (K at each knot)
HARD_CAP = 46       # writes per rolling 24 h, whatever happens (the lab limit is 48)
STATE_KEYS = ("trim", "curve", "corr", "age")


class PminDuty:
    name = "pmin_duty"

    def reset(self, params: dict) -> None:
        g = lambda k, d: float(params.get(k, d))  # noqa: E731
        # slab target (house priors; HOUSE_MODEL.md: room->outdoor 0.115 kW/K, slab->room 0.43 kW/K)
        self.b = g("b", 0.20)               # K of slab per K of (target - outdoor)
        self.s = g("s", 0.022)              # K of slab per W/m2 of forecast GHI
        self.ts0 = g("ts0", -1.5)           # K, constant (internal gains), learned by the trim
        self.lead0 = int(g("lead0", 1))     # forecast window (hours ahead) seen by the slab target
        self.lead1 = int(g("lead1", 9))
        self.kp = g("kp", 3.0)              # K of slab per K of room error
        self.ki = g("ki", 0.15)             # K of slab per K-hour of room error
        self.trim_lim = g("trim_lim", 4.0)
        self.ki_boost = g("ki_boost", 2.0)  # commissioning: ki x (1 + boost) at takeover, fading ...
        self.boost_days = g("boost_days", 2.0)  # ... with this time constant
        # learned curve: the persistent part of the trim moves, with time constant tau_curve, into a
        # slab-target curve over outdoor temperature (knots CURVE_T), which learns the slope b
        self.tau_curve = g("tau_curve", 120.0)  # hours; 0 = off
        self.curve_lim = g("curve_lim", 8.0)
        self.curve_glob = g("curve_glob", 0.5)
        self.aim = g("aim", 0.0)            # K added to the room target (sensor bias)
        self.kw = g("kw", 0.3)              # K of slab per K the next 3 h are warmer than the day (COP timing)
        self.glow = g("glow", 0.0008)       # K per W/m2: sun on the thermometer
        # daily pattern (iterative learning over days): the room error at hour h is charged to
        # the slab target at hour h - ilc_lead, so the slab anticipates the house's daily cycle
        self.ilc_g = g("ilc_g", 1.0)        # K of slab per K-hour of room error, per day
        self.ilc_lead = g("ilc_lead", 5.0)  # h: slab -> room lag
        self.ilc_lim = g("ilc_lim", 2.0)
        self.ilc_leak = g("ilc_leak", 30.0)  # days
        # duty cycle
        self.band = g("band", 1.4)          # K of slab around Ts*
        self.min_run = g("min_run", 60.0)   # minutes
        self.min_off = g("min_off", 45.0)
        # run execution
        self.q_run = g("q_run", 6.5)        # kW; 0 = the unit's minimum output (literal P_min)
        self.kq = g("kq", 2.0)              # extra kW per K of slab deficit beyond the band
        self.q_hi = g("q_hi", 9.0)
        self.ride_every = g("ride_every", 8.0)
        self.ride_hyst = g("ride_hyst", 1.3)  # K: rewrite only when the ideal setpoint moved this far
        self.budget = g("budget", 40.0)     # writes per rolling 24 h; beyond it only kicks and parks
        self.tau_q = g("tau_q", 30.0)       # minutes: smoothing of the ride output target
        self.failsafe = g("failsafe", 1.0) > 0  # weather-following park setpoint (outage fail-safe)
        self.delta = g("delta", 5.0)        # restart hysteresis written once (K): keeps the parked unit idle
        self.delta_tries = int(g("delta_tries", 3))  # at most this many restart_delta writes per 24 h
        self.park_min = g("park_min", 25.0)  # lowest idle park setpoint (lowest ever written to the real unit)
        self.room_hold = g("room_hold", 0.0) > 0  # room lost: 1 = hold the trim, 0 = let it fade (better, see doc)
        # frozen-room guard: a value that has not moved by 0.1 K for this long is treated as stale even
        # if it keeps being reported (normal spells in the lab are <= 13 h, one 23 h); the learning done
        # during the frozen spell is rolled back to the snapshot taken when the value last changed
        self.frozen_h = g("frozen_h", 12.0)     # hours; 0 = off
        self.eff = g("eff", 0.71)           # loop -> slab effectiveness
        # state (the learned part is what state()/restore() carry across restarts)
        self.trim = 0.0
        self.curve = [float(x) for x in str(params.get("curve0", CURVE0)).replace(":", ",").split(",")]
        self.corr = [0.0] * 24
        self.age = 0.0                      # minutes since install (persisted): fades the commissioning boost
        self.dlog = deque()                 # minutes of restart_delta writes (rolling 24 h)
        self.clock = 0
        self.ts = None
        self.t_avg = None
        self.run = False
        self.t_state = 999
        self.since_dhw = 999
        self.since_defrost = 999
        self.comp_min = 0
        self.last_write = -999
        self.last_sp = None
        self.kick_min = 0
        self.ts_star = None
        self.warm = 0.0
        self.wlog = deque()
        self.q_f = None
        self.room_ref = None                # last distinct room value, the minute it appeared ...
        self.room_since = 0
        self.room_snap = None               # ... and the learned state at that minute
        self.room_frozen = False            # exposed to Home Assistant as an alert

    # ------------------------------------------------------------------ persistence
    def state(self) -> dict:
        """Learned state to persist (Home Assistant Store) and hand to restore() after a restart."""
        return {k: (list(v) if isinstance(v, list) else v) for k, v in
                ((k, getattr(self, k)) for k in STATE_KEYS)}

    def restore(self, st: dict) -> None:
        for k in STATE_KEYS:
            v = st.get(k)
            if k in ("curve", "corr"):
                if isinstance(v, (list, tuple)) and len(v) == len(getattr(self, k)) and all(
                        isinstance(x, (int, float)) and math.isfinite(x) for x in v):
                    setattr(self, k, [float(x) for x in v])
            elif isinstance(v, (int, float)) and math.isfinite(v):
                setattr(self, k, float(v))

    def _room_check(self, obs: Observation) -> None:
        """Frozen-sensor guard (a value that keeps being reported but never moves)."""
        if obs.room is None or obs.room_age_min >= 240 or self.frozen_h <= 0:
            self.room_ref = None
            self.room_frozen = False
            return
        if self.room_ref is None or abs(obs.room - self.room_ref) >= 0.05:
            self.room_ref, self.room_since = obs.room, obs.minute
            self.room_snap = (self.trim, list(self.curve), list(self.corr))
            self.room_frozen = False
        elif not self.room_frozen and obs.minute - self.room_since >= self.frozen_h * 60:
            self.room_frozen = True
            self.trim, curve, corr = self.room_snap   # undo what the frozen value taught
            self.curve, self.corr = list(curve), list(corr)

    # ------------------------------------------------------------------ estimates
    def _weather(self, obs: Observation) -> tuple[float, float]:
        a = 1.0 / (24 * 60)
        self.t_avg = obs.outdoor if self.t_avg is None else self.t_avg + a * (obs.outdoor - self.t_avg)
        fc = obs.forecast
        self.warm = 0.0
        if fc and len(fc) >= max(self.lead1, 24):
            hs = fc[self.lead0:self.lead1]
            if self.kw:
                self.warm = sum(h["outdoor"] for h in fc[:3]) / 3 - sum(h["outdoor"] for h in fc[:24]) / 24
            return (sum(h["outdoor"] for h in hs) / len(hs),
                    sum((h.get("ghi") or 0.0) for h in hs) / len(hs))
        return self.t_avg, 0.0

    def _slab(self, obs: Observation) -> None:
        mode = obs.mode
        self.since_dhw = 0 if mode == "dhw" else self.since_dhw + 1
        self.since_defrost = 0 if mode == "defrost" else self.since_defrost + 1
        self.comp_min = self.comp_min + 1 if (obs.compressor_on and mode == "heat") else (
            0 if not obs.compressor_on else self.comp_min)
        if not obs.link_ok or self.since_dhw < 20 or self.since_defrost < 10:
            return
        if mode == "heat" and obs.compressor_on and self.comp_min >= 8:
            sup = obs.outlet + OUTLET_OFF
            x = (obs.inlet - (1.0 - self.eff) * sup) / self.eff
        elif mode == "idle" and not obs.compressor_on and self.t_state >= 15 and not self.run:
            x = obs.inlet
        else:
            return
        self.ts = x if self.ts is None else self.ts + 0.2 * (x - self.ts)

    @staticmethod
    def _weights(t: float) -> list:
        """Linear-interpolation weights of the curve knots at outdoor temperature t."""
        if t <= CURVE_T[0]:
            return [(0, 1.0)]
        if t >= CURVE_T[-1]:
            return [(len(CURVE_T) - 1, 1.0)]
        i = 0
        while t > CURVE_T[i + 1]:
            i += 1
        f = (t - CURVE_T[i]) / (CURVE_T[i + 1] - CURVE_T[i])
        return [(i, 1.0 - f), (i + 1, f)]

    def _curve(self, t: float) -> float:
        return sum(self.curve[k] * w for k, w in self._weights(t))

    def _daily(self, hour: float) -> float:
        """Learned daily correction of the slab target, linear between hourly bins."""
        if self.ilc_g <= 0:
            return 0.0
        x = hour - 0.5
        i = int(math.floor(x)) % 24
        f = x - math.floor(x)
        return self.corr[i] * (1.0 - f) + self.corr[(i + 1) % 24] * f

    def _ghi_now(self, obs: Observation) -> float:
        fc = obs.forecast
        return (fc[0].get("ghi") or 0.0) if fc else 0.0

    # ------------------------------------------------------------------ writes
    def _write(self, obs: Observation, sp: float, critical: bool = True) -> Command:
        sp = float(min(max(round(sp), 20), 45))
        if sp == obs.setpoint:
            return Command()
        while self.wlog and obs.minute - self.wlog[0] >= 1440:
            self.wlog.popleft()
        if not critical and len(self.wlog) >= self.budget:
            return Command()
        if len(self.wlog) >= HARD_CAP:
            return Command()   # hard ceiling, kicks and stops included
        if sp == self.last_sp and obs.minute - self.last_write < 5:
            return Command()   # the same value did not show up yet: no repeat within 5 minutes
        self.last_sp = sp
        self.wlog.append(obs.minute)
        self.last_write = obs.minute
        return Command(setpoint=sp)

    def _park(self, obs: Observation) -> Command:
        sp = PARK_SP
        if obs.compressor_on:
            t_ctrl = obs.outlet + OUTLET_OFF + CTRL_RUN
            sp = min(sp, math.floor(t_ctrl - 2.1))
        return self._write(obs, sp)

    def _idle_park(self, obs: Observation, ts_star: float) -> Command:
        """Setpoint while idle. Fail-safe park: the firmware's own restart threshold sits just
        below this controller's start threshold, so a unit left alone by a link outage still
        starts when the slab runs low. Never high enough to start the unit now."""
        cap = math.floor(obs.inlet + CTRL_IDLE + obs.restart_delta - 0.6)
        want = PARK_SP
        if self.failsafe:
            want = max(PARK_SP, math.floor(ts_star - self.band - 0.3 + obs.restart_delta + CTRL_IDLE))
        # never below the floor: if very cold return water lets the unit start by itself at the
        # floor, that run is adopted (step), which beats hours of untested sub-25 setpoints
        park = max(min(cap, want), self.park_min)
        if park == obs.setpoint:
            return Command()
        if (park > obs.setpoint >= self.park_min and park - obs.setpoint < 2
                and obs.minute - self.last_write < 120):
            return Command()   # small raises wait (write economy)
        # lowering, or back up to the floor after a stop write: never held back by the budget
        return self._write(obs, park, critical=park < obs.setpoint or obs.setpoint < self.park_min)

    # ------------------------------------------------------------------ step
    def step(self, obs: Observation) -> Command:
        self.age += 1.0
        self.clock = obs.minute
        if not all(math.isfinite(x) for x in (obs.outdoor, obs.outlet, obs.inlet, obs.setpoint, obs.restart_delta)):
            return Command()   # unavailable values (NaN from Home Assistant): act as if the link were down
        if obs.room is not None and not math.isfinite(obs.room):
            obs = replace(obs, room=None)
        t_fc, ghi = self._weather(obs)
        self._slab(obs)
        self.t_state += 1
        # room feedback (sensor corrected for sun on the thermometer)
        e = 0.0
        self._room_check(obs)
        if obs.room is None or obs.room_age_min >= 240 or self.room_frozen:
            if not self.room_hold:
                self.trim *= 1.0 - 1.0 / (24 * 60)   # room lost: forget the short-term trim, keep the curve
        else:
            e = obs.target + self.aim - (obs.room - self.glow * self._ghi_now(obs))
            ki = self.ki * (1.0 + self.ki_boost * math.exp(-self.age / (self.boost_days * 1440.0)))
            self.trim = min(max(self.trim + ki * e / 60.0, -self.trim_lim), self.trim_lim)
            if self.tau_curve > 0:
                tr = self.trim / (self.tau_curve * 60.0)
                self.trim -= tr
                # a share moves the whole curve (offset, generalises to unseen weather), the rest
                # the knots around today's outdoor temperature (slope)
                wl = dict(self._weights(t_fc))
                for k in range(len(self.curve)):
                    d = tr * (self.curve_glob + (1.0 - self.curve_glob) * wl.get(k, 0.0))
                    self.curve[k] = min(max(self.curve[k] + d, -self.curve_lim), self.curve_lim)
            if self.ilc_g > 0:
                k = int((obs.local_hour - self.ilc_lead) % 24)
                self.corr[k] = min(max(self.corr[k] + self.ilc_g * e / 60.0, -self.ilc_lim), self.ilc_lim)
        if self.ilc_g > 0 and obs.minute % 60 == 0:
            m = sum(self.corr) / 24.0
            f = 1.0 - 1.0 / (24.0 * self.ilc_leak)
            self.corr = [(c - m) * f for c in self.corr]
        ts_star = (obs.target + self.b * (obs.target - t_fc) - self.s * ghi + self.ts0
                   + self.trim + self.kp * e + self._daily(obs.local_hour) + self._curve(t_fc)
                   + self.kw * self.warm)
        self.ts_star = ts_star
        if not obs.link_ok:
            return Command()
        ts = self.ts if self.ts is not None else obs.inlet

        cmd = self._decide(obs, ts, ts_star, t_fc)
        # restart hysteresis: written while idle, a few tries a day at most and counted in the
        # budget; if it does not take, the run logic simply works with the value the unit reports
        if (self.delta and abs(obs.restart_delta - self.delta) > 0.25 and not obs.compressor_on
                and obs.mode == "idle"):
            while self.dlog and obs.minute - self.dlog[0] >= 1440:
                self.dlog.popleft()
            while self.wlog and obs.minute - self.wlog[0] >= 1440:
                self.wlog.popleft()
            if (len(self.dlog) < self.delta_tries and len(self.wlog) < HARD_CAP
                    and (not self.dlog or obs.minute - self.dlog[-1] >= 30)):
                self.dlog.append(obs.minute)
                self.wlog.append(obs.minute)
                return replace(cmd, restart_delta=self.delta)
        return cmd

    def _decide(self, obs: Observation, ts: float, ts_star: float, t_fc: float) -> Command:
        q_min = KF * min(max(1.8 + 0.05 * t_fc, 1.4), 2.4)
        if not self.run:
            if ts < ts_star - self.band and self.t_state >= self.min_off and obs.mode != "dhw":
                self.run, self.t_state, self.kick_min = True, 0, 0
            elif (obs.compressor_on and obs.mode == "heat" and self.comp_min <= 2
                  and (ts < ts_star or obs.setpoint <= self.park_min)):
                # the unit started by itself while heat is due, or at the park floor (very cold
                # return water): keep it as a normal run instead of a short cycle
                self.run, self.t_state = True, 0
            else:
                if obs.compressor_on:
                    # a stop waits for steady heating (the outlet reads the reversed cycle in a defrost)
                    if obs.mode == "heat" and self.since_defrost >= 3:
                        return self._park(obs)
                    return Command()
                return self._idle_park(obs, ts_star)
        # running
        if ts > ts_star + self.band and self.t_state >= self.min_run:
            self.run, self.t_state = False, 0
            if obs.compressor_on and (obs.mode != "heat" or self.since_defrost < 3):
                return Command()
            return self._park(obs)
        if obs.mode in ("dhw", "defrost", "off") or self.since_dhw < 8:
            return Command()
        if not obs.compressor_on:
            # kick: the smallest setpoint the restart rule accepts; one degree more after 6 idle
            # minutes (twice at most); the unit itself may still hold off (minimum off, after hot water)
            self.kick_min += 1
            self.q_f = None
            sp = math.ceil(obs.inlet + CTRL_IDLE + obs.restart_delta + 0.15) + min(self.kick_min // 6, 2)
            if obs.setpoint >= sp - 0.5 and self.kick_min % 6:
                return Command()
            return self._write(obs, sp)
        self.kick_min = 0
        if self.comp_min < 2:
            return Command()
        deficit = max(0.0, ts_star - self.band - ts)
        q_raw = min(max(max(self.q_run, q_min) + self.kq * deficit, q_min), self.q_hi)
        self.q_f = q_raw if self.q_f is None else self.q_f + (q_raw - self.q_f) / self.tau_q
        q_tgt = self.q_f
        sp = obs.inlet + q_tgt / KF + CTRL_RUN - 0.025 * (q_tgt - 5.0) + 0.55
        t_ctrl = obs.outlet + OUTLET_OFF + CTRL_RUN
        sp = max(sp, math.ceil(t_ctrl - 1.5), self.park_min)  # never low enough to stop the run by accident
        if obs.minute - self.last_write >= self.ride_every or self.comp_min == 2:
            if abs(sp - obs.setpoint) >= self.ride_hyst and round(sp) != obs.setpoint:
                return self._write(obs, sp, critical=self.comp_min == 2)
        return Command()


CONTROLLER = PminDuty


if __name__ == "__main__":
    from datetime import datetime, timezone

    c = PminDuty()
    c.reset({})
    fc = tuple({"time": datetime(2026, 1, 1, h, tzinfo=timezone.utc), "outdoor": 0.0, "rh": 80, "ghi": 0,
                "dni": 0, "dhi": 0, "cloud": 100} for h in range(24)) * 2
    base = dict(time=datetime(2026, 1, 1, tzinfo=timezone.utc), local_hour=2.0, room=21.5, room_age_min=5,
                outdoor=0.0, outlet=24.0, inlet=24.3, setpoint=25.0, restart_delta=5.0, quiet=False,
                heating_enabled=True, compressor_on=False, mode="idle", electric_kw=0.02, energy_kwh=0.0,
                target=22.0, forecast=fc, pv_kw=None)
    cmds = [c.step(Observation(minute=m, **base)) for m in range(60)]
    assert any(x.setpoint and x.setpoint >= 28 for x in cmds), "a cold slab must start a run"
    c.reset({})
    assert c.step(Observation(minute=0, link_ok=False, **base)) == Command(), "no writes while the link is down"
    c.step(Observation(minute=1, **{**base, "room": None, "forecast": ()}))
    c.step(Observation(minute=2, **{**base, "mode": "dhw", "inlet": 46.0, "outlet": 50.0}))
    # a restart_delta that never takes: a few tries a day, and the run logic still works
    c.reset({})
    stuck = dict(base, restart_delta=4.0)
    cmds = [c.step(Observation(minute=m, **stuck)) for m in range(2880)]
    nd = sum(1 for x in cmds if x.restart_delta is not None)
    nw = sum(1 for x in cmds if x != Command())
    assert nw <= 2 * HARD_CAP, f"{nw} writes in 2 days when nothing takes"
    assert nd <= 6, f"restart_delta written {nd} times in 2 days"
    assert any(x.setpoint and x.setpoint >= 28 for x in cmds), "a cold slab must start a run despite the delta"
    # unavailable values (NaN) are treated like a link drop
    assert c.step(Observation(minute=2881, **{**base, "inlet": float("nan")})) == Command()
    c.step(Observation(minute=2882, **{**base, "room": float("nan")}))
    # a room value that is reported but never moves is treated as stale after frozen_h
    c.reset({})
    fr = dict(base, room=23.0, inlet=27.0, outlet=26.7)
    for m in range(13 * 60):
        c.step(Observation(minute=m, **fr))
    assert c.room_frozen and c.trim == 0.0 and not any(c.corr), "frozen room must roll back its learning"
    c.step(Observation(minute=13 * 60, **{**fr, "room": 22.8}))
    assert not c.room_frozen
    # learned state round-trips
    c2 = PminDuty()
    c2.reset({})
    c2.restore(c.state())
    assert c2.state() == c.state()
    print("self-check ok")
