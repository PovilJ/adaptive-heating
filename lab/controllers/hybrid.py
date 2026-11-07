"""hybrid: slab-thermostat duty cycle + mid-output riding + sun and daily-pattern anticipation
(stdlib only). Design, ablations and results: docs/research/lab/controllers/hybrid.md.

It keeps only the mechanisms that the lab's competing controllers (and this file's own
ablations) showed to be worth something on every mandatory variant:

1. **When to run: a thermostat on the floor slab**, seen through the water (the circulation pump
   never stops): idle, slab = inlet; running, slab = (inlet - 0.29 x supply) / 0.71. Start when
   the slab is `band` under its target, stop when it is `band` over (minimum on/off times). The
   run fraction then equals heat need / run output, with about two long runs a day.
2. **How hard to run: ride the setpoint** at return + Q / (cp x flow) so the firmware's own
   dead band holds Q = `q_run` (about 6 kW: the measured part-load COP map makes mid output
   10-25 % cheaper per kWh than the 3.6-4.4 kW floor at the supply the slab needs). Kick with the
   smallest setpoint the restart rule accepts, stop with one write 2 K under the control sensor.
   When the slab falls behind (deep cold) the output rises with the deficit.
3. **Slab target** = target + b (target - T_fc) + ts0 - s x GHI_fc (forecast hours 1-9)
   + kp e + integral(e) + daily(hour) + kw x (next 3 h warmer than the day), with e the room
   error on the thermometer corrected for its sun glow. `daily` is a 24-bin pattern learned over
   days (the room error at hour h charged to hour h - lead), zero mean.

Fail-safes: no writes while the link is down or a unit value is NaN; DHW / defrost freeze the
slab estimate and the run waits; room missing, stale (> 4 h) or frozen (unchanged 12 h) ->
learning freezes, the room terms drop and the integral relaxes to a fallback curve (the integral
the room needed at this outdoor temperature, learned while the room was known); forecast missing
-> the hours of the last forecast still ahead, else the 24 h mean of the unit's sensor; while
idle the parked setpoint sits just under the firmware's own restart point for the slab start
threshold, so an outage still restarts the unit when the slab runs low. Rolling write budget
(soft 40, hard 46 per 24 h). state()/restore() carry the learned integral, daily pattern and
fallback curve across Home Assistant restarts.

`mode=fw` is an ablation only: the same slab target, but the firmware cycles a setpoint.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import replace

from lab.sim.interface import Command, Observation

KF = 2.02           # kW per K of loop delta-T at 29 L/min (scale only)
CTRL_RUN = -0.80    # control sensor - true supply while running (UNIT_MODEL.md 2)
CTRL_IDLE = -0.80   # control sensor - inlet while idle (effective start offset)
OUTLET_OFF = 0.30   # true supply - outlet sensor
SP_FLOOR = 25.0     # lowest setpoint ever written to the real unit
SP_CEIL = 39.0      # highest recorded
HARD_CAP = 46       # writes per rolling 24 h, everything included
KNOTS = (-15.0, -5.0, 5.0, 15.0)  # outdoor knots of the room-lost fallback curve


class Hybrid:
    name = "hybrid"

    def reset(self, params: dict) -> None:
        g = lambda k, d: float(params.get(k, d))  # noqa: E731
        # slab target (priors from HOUSE_MODEL; the integral learns the level)
        self.b = g("b", 0.20)               # K slab per K (target - outdoor)
        self.ts0 = g("ts0", 1.0)
        self.aim = g("aim", 0.0)            # K added to the room target
        self.s = g("s", 0.030)              # K slab per W/m2 of forecast GHI (hours lead0..lead1)
        self.lead0 = int(g("lead0", 1))
        self.lead1 = int(g("lead1", 9))
        self.kp = g("kp", 3.0)              # K slab per K room error
        self.ki = g("ki", 0.15)             # K slab per K-hour
        self.i_lim = g("i_lim", 6.0)
        self.glow = g("glow", 0.0008)       # K per W/m2: sun on the thermometer
        self.kw = g("kw", 0.3)              # K slab per K the next 3 h beat the 24 h mean
        self.d_g = g("d_g", 1.0)            # daily pattern: K slab per K-hour per day
        self.d_lead = g("d_lead", 5.0)      # h, slab -> room lag
        self.d_lim = g("d_lim", 2.0)
        self.d_leak = g("d_leak", 30.0)     # days
        # duty cycle
        self.band = g("band", 1.4)
        self.min_run = g("min_run", 60.0)
        self.min_off = g("min_off", 45.0)
        # execution
        self.mode = str(params.get("mode", "ride"))  # 'ride' | 'fw' (ablation: firmware cycles a setpoint)
        self.q_run = g("q_run", 6.5)        # kW; 0 = the unit's floor
        self.kq = g("kq", 2.0)              # extra kW per K of slab deficit beyond the band
        self.q_hi = g("q_hi", 9.0)
        self.ride_every = g("ride_every", 8.0)
        self.ride_hyst = g("ride_hyst", 1.3)
        self.budget = g("budget", 40.0)
        self.delta = g("delta", 5.0)
        self.eff = g("eff", 0.71)
        self.stale_min = g("stale_min", 240.0)
        self.frozen_h = g("frozen_h", 12.0)
        self.tau_fb = g("tau_fb", 72.0)     # h: the fallback curve follows the integral by outdoor temperature
        self.use_fc = g("use_fc", 1.0) > 0    # ablation / fault check: ignore the forecast
        # learned state
        self.integ = g("integ0", 0.0)
        self.daily = [0.0] * 24
        self.fb = [self.integ] * len(KNOTS)  # integral by outdoor temperature, used only when the room is lost
        # runtime
        self.t_avg = None
        self.fc_last = None
        self.ts = None
        self.run = False
        self.t_state = 999
        self.since_dhw = 999
        self.since_def = 999
        self.comp_min = 0
        self.kick_min = 0
        self.q_f = None
        self.wlog = deque()
        self.dlog = deque()
        self.last_write = -999
        self.last_sp = None
        self.room_ref = None
        self.room_since = 0
        self.frozen = False

    def state(self) -> dict:
        """Learned state to persist across Home Assistant restarts (hand it to restore())."""
        return {"integ": self.integ, "daily": list(self.daily), "fb": list(self.fb)}

    def restore(self, st: dict) -> None:
        v = st.get("integ")
        if isinstance(v, (int, float)) and math.isfinite(v):
            self.integ = float(v)
        for k, n in (("daily", 24), ("fb", len(KNOTS))):
            d = st.get(k)
            if isinstance(d, (list, tuple)) and len(d) == n and all(
                    isinstance(x, (int, float)) and math.isfinite(x) for x in d):
                setattr(self, k, [float(x) for x in d])

    @staticmethod
    def _w(t: float) -> list:
        if t <= KNOTS[0]:
            return [(0, 1.0)]
        if t >= KNOTS[-1]:
            return [(len(KNOTS) - 1, 1.0)]
        i = 0
        while t > KNOTS[i + 1]:
            i += 1
        f = (t - KNOTS[i]) / (KNOTS[i + 1] - KNOTS[i])
        return [(i, 1.0 - f), (i + 1, f)]

    # ------------------------------------------------------------------ inputs
    def _forecast(self, obs: Observation):
        fc = obs.forecast if self.use_fc else ()
        if fc and len(fc) >= 24:
            self.fc_last = fc
        elif self.fc_last is not None:
            fc = tuple(h for h in self.fc_last if h["time"] > obs.time)
        if not fc or len(fc) < max(self.lead1, 12):
            return None
        return fc

    def _weather(self, obs: Observation, fc):
        a = 1.0 / 1440.0
        self.t_avg = obs.outdoor if self.t_avg is None else self.t_avg + a * (obs.outdoor - self.t_avg)
        if fc is None:
            return self.t_avg, 0.0, 0.0, 0.0
        hs = fc[self.lead0:self.lead1]
        t_fc = sum(h["outdoor"] for h in hs) / len(hs)
        ghi = sum((h.get("ghi") or 0.0) for h in hs) / len(hs)
        n = min(len(fc), 24)
        warm = sum(h["outdoor"] for h in fc[:3]) / 3 - sum(h["outdoor"] for h in fc[:n]) / n
        return t_fc, ghi, warm, (fc[0].get("ghi") or 0.0)

    def _slab(self, obs: Observation) -> None:
        m = obs.mode
        self.since_dhw = 0 if m == "dhw" else self.since_dhw + 1
        self.since_def = 0 if m == "defrost" else self.since_def + 1
        if obs.compressor_on and m == "heat":
            self.comp_min += 1
        elif not obs.compressor_on:
            self.comp_min = 0
        if not obs.link_ok or self.since_dhw < 20 or self.since_def < 10:
            return
        if m == "heat" and obs.compressor_on and self.comp_min >= 8:
            x = (obs.inlet - (1.0 - self.eff) * (obs.outlet + OUTLET_OFF)) / self.eff
        elif m == "idle" and not obs.compressor_on and self.t_state >= 15 and not self.run:
            x = obs.inlet
        else:
            return
        self.ts = x if self.ts is None else self.ts + 0.2 * (x - self.ts)

    def _room_ok(self, obs: Observation) -> bool:
        if obs.room is None or obs.room_age_min >= self.stale_min:
            self.room_ref, self.frozen = None, False
            return False
        if self.room_ref is None or abs(obs.room - self.room_ref) >= 0.05:
            self.room_ref, self.room_since, self.frozen = obs.room, obs.minute, False
        elif self.frozen_h > 0 and obs.minute - self.room_since >= self.frozen_h * 60:
            self.frozen = True
        return not self.frozen

    def _daily_at(self, hour: float) -> float:
        x = hour - 0.5
        i = int(math.floor(x)) % 24
        f = x - math.floor(x)
        return self.daily[i] * (1.0 - f) + self.daily[(i + 1) % 24] * f

    # ------------------------------------------------------------------ writes
    def _write(self, obs: Observation, sp: float, critical: bool = True) -> Command:
        sp = float(min(max(round(sp), 20), 45))
        if sp == obs.setpoint:
            return Command()
        while self.wlog and obs.minute - self.wlog[0] >= 1440:
            self.wlog.popleft()
        if len(self.wlog) >= HARD_CAP or (not critical and len(self.wlog) >= self.budget):
            return Command()
        if sp == self.last_sp and obs.minute - self.last_write < 5:
            return Command()
        self.last_sp, self.last_write = sp, obs.minute
        self.wlog.append(obs.minute)
        return Command(setpoint=sp)

    def _stop(self, obs: Observation) -> Command:
        sp = SP_FLOOR
        if obs.compressor_on:
            sp = min(sp, math.floor(obs.outlet + OUTLET_OFF + CTRL_RUN - 2.1))
        return self._write(obs, sp)

    def _park(self, obs: Observation, ts_star: float) -> Command:
        """Idle setpoint: just under the firmware's own restart point for the slab start
        threshold (outage fail-safe), never high enough to start the unit now, never < 25."""
        cap = math.floor(obs.inlet + CTRL_IDLE + obs.restart_delta - 0.6)
        want = math.floor(ts_star - self.band - 0.3 + obs.restart_delta + CTRL_IDLE)
        park = max(min(cap, want), SP_FLOOR)
        if park == obs.setpoint:
            return Command()
        if park > obs.setpoint >= SP_FLOOR and park - obs.setpoint < 2 and obs.minute - self.last_write < 120:
            return Command()
        return self._write(obs, park, critical=park < obs.setpoint or obs.setpoint < SP_FLOOR)

    # ------------------------------------------------------------------ step
    def step(self, obs: Observation) -> Command:
        if not all(math.isfinite(x) for x in (obs.outdoor, obs.outlet, obs.inlet, obs.setpoint, obs.restart_delta)):
            return Command()
        if obs.room is not None and not math.isfinite(obs.room):
            obs = replace(obs, room=None)
        fc = self._forecast(obs)
        t_fc, ghi, warm, ghi_now = self._weather(obs, fc)
        self._slab(obs)
        self.t_state += 1

        e = 0.0
        if self._room_ok(obs):
            e = obs.target + self.aim - (obs.room - self.glow * ghi_now)
            self.integ = min(max(self.integ + self.ki * e / 60.0, -self.i_lim), self.i_lim)
            if self.d_g > 0:
                k = int((obs.local_hour - self.d_lead) % 24)
                self.daily[k] = min(max(self.daily[k] + self.d_g * e / 60.0, -self.d_lim), self.d_lim)
            if self.tau_fb > 0:
                for k, w in self._w(t_fc):
                    self.fb[k] += w * (self.integ - self.fb[k]) / (self.tau_fb * 60.0)
        else:
            # room lost: the integral relaxes (6 h) to what it was in this weather when the room was known
            ref = sum(self.fb[k] * w for k, w in self._w(t_fc))
            self.integ += (ref - self.integ) / 360.0
        if self.d_g > 0 and obs.minute % 60 == 0:
            mu = sum(self.daily) / 24.0
            f = 1.0 - 1.0 / (24.0 * self.d_leak)
            self.daily = [(c - mu) * f for c in self.daily]

        ts_star = (obs.target + self.b * (obs.target - t_fc) + self.ts0 - self.s * ghi
                   + self.kp * e + self.integ + self._daily_at(obs.local_hour) + self.kw * warm)
        if not obs.link_ok:
            return Command()
        ts = self.ts if self.ts is not None else obs.inlet
        cmd = self._fw(obs, ts_star) if self.mode == "fw" else self._decide(obs, ts, ts_star, t_fc)

        # restart hysteresis: a few tries a day while idle; otherwise work with the reported value
        if abs(obs.restart_delta - self.delta) > 0.25 and not obs.compressor_on and obs.mode == "idle":
            while self.dlog and obs.minute - self.dlog[0] >= 1440:
                self.dlog.popleft()
            if len(self.dlog) < 3 and len(self.wlog) < HARD_CAP and (not self.dlog or obs.minute - self.dlog[-1] >= 30):
                self.dlog.append(obs.minute)
                self.wlog.append(obs.minute)
                return replace(cmd, restart_delta=self.delta)
        return cmd

    def _fw(self, obs: Observation, ts_star: float) -> Command:
        """Ablation: no start/stop decisions; one setpoint whose firmware restart point is the
        slab start threshold, the firmware runs until its own stop."""
        sp = min(max(ts_star - self.band - CTRL_IDLE + obs.restart_delta, SP_FLOOR), SP_CEIL)
        if abs(sp - obs.setpoint) >= 1.0 and obs.minute - self.last_write >= 30:
            return self._write(obs, sp)
        return Command()

    def _decide(self, obs: Observation, ts: float, ts_star: float, t_fc: float) -> Command:
        q_min = KF * min(max(1.8 + 0.05 * t_fc, 1.4), 2.4)
        if not self.run:
            if ts < ts_star - self.band and self.t_state >= self.min_off and obs.mode != "dhw":
                self.run, self.t_state, self.kick_min = True, 0, 0
            elif obs.compressor_on and obs.mode == "heat" and self.comp_min <= 2 and (
                    ts < ts_star or obs.setpoint <= SP_FLOOR):
                self.run, self.t_state = True, 0          # the unit started by itself: adopt it
            else:
                if obs.compressor_on:
                    if obs.mode == "heat" and self.since_def >= 3:
                        return self._stop(obs)
                    return Command()
                return self._park(obs, ts_star)
        if ts > ts_star + self.band and self.t_state >= self.min_run:
            self.run, self.t_state = False, 0
            if obs.compressor_on and (obs.mode != "heat" or self.since_def < 3):
                return Command()
            return self._stop(obs)
        if obs.mode in ("dhw", "defrost", "off") or self.since_dhw < 8:
            return Command()
        if not obs.compressor_on:
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
        q_raw = min(max(self.q_run, q_min) + self.kq * deficit, self.q_hi)
        self.q_f = q_raw if self.q_f is None else self.q_f + (q_raw - self.q_f) / 30.0
        q = self.q_f
        sp = obs.inlet + q / KF + CTRL_RUN - 0.025 * (q - 5.0) + 0.55
        t_ctrl = obs.outlet + OUTLET_OFF + CTRL_RUN
        sp = min(max(sp, math.ceil(t_ctrl - 1.5), SP_FLOOR), SP_CEIL)
        if obs.minute - self.last_write >= self.ride_every or self.comp_min == 2:
            if abs(sp - obs.setpoint) >= self.ride_hyst and round(sp) != obs.setpoint:
                return self._write(obs, sp, critical=self.comp_min == 2)
        return Command()


CONTROLLER = Hybrid


if __name__ == "__main__":
    from datetime import datetime, timedelta, timezone

    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fc = tuple({"time": t0 + timedelta(hours=h + 1), "outdoor": 0.0, "rh": 80, "ghi": 0, "dni": 0, "dhi": 0,
                "cloud": 100} for h in range(48))
    base = dict(time=t0, local_hour=2.0, room=21.5, room_age_min=5, outdoor=0.0, outlet=24.0, inlet=24.3,
                setpoint=25.0, restart_delta=5.0, quiet=False, heating_enabled=True, compressor_on=False,
                mode="idle", electric_kw=0.02, energy_kwh=0.0, target=22.0, forecast=fc, pv_kw=None)
    c = Hybrid()
    c.reset({})
    cmds = [c.step(Observation(minute=m, **base)) for m in range(60)]
    assert any(x.setpoint and x.setpoint >= 28 for x in cmds), "a cold slab must kick a run"
    c.reset({})
    assert c.step(Observation(minute=0, link_ok=False, **base)) == Command(), "no writes while the link is down"
    c.step(Observation(minute=1, **{**base, "room": None, "forecast": ()}))
    c.step(Observation(minute=2, **{**base, "mode": "dhw", "inlet": 46.0, "outlet": 50.0}))
    assert c.step(Observation(minute=3, **{**base, "inlet": float("nan")})) == Command()
    c.step(Observation(minute=4, **{**base, "room": float("nan")}))
    # a restart_delta that never takes: a few tries a day, bounded writes, runs still kick
    c.reset({})
    stuck = dict(base, restart_delta=4.0)
    cmds = [c.step(Observation(minute=m, **stuck)) for m in range(2880)]
    assert sum(1 for x in cmds if x.restart_delta is not None) <= 6
    assert sum(1 for x in cmds if x != Command()) <= 2 * HARD_CAP
    # a frozen room value stops learning after 12 h
    c.reset({})
    for m in range(13 * 60):
        c.step(Observation(minute=m, **dict(base, room=23.0, inlet=27.0, outlet=26.7)))
    assert c.frozen
    i0 = c.integ
    c.step(Observation(minute=13 * 60, **dict(base, room=23.0, inlet=27.0, outlet=26.7)))
    assert abs(c.integ - i0) < 0.01
    # learned state round-trips
    c2 = Hybrid()
    c2.reset({})
    c2.restore(c.state())
    assert c2.state() == c.state()
    print("self-check ok")
