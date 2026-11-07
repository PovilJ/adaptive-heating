"""degree_minutes: slab-scaled degree-minute controller (research strategy S4), stdlib only.

Idea (HEAT_PUMP_CONTROL_RESEARCH.md section 4.3 and S4, NIBE/Vaillant logic rescaled to a slab):

- **Target flow** T_c: the mean leaving-water temperature the house needs, from a low weather
  curve on the outdoor temperature (forecast for the next hours blended with the smoothed unit
  sensor), minus a forecast-sun term, plus a room trim (proportional + slow integral on the room
  thermometer, corrected for its known reading in sun).
- **Degree-minutes** DM integrate (outlet - T_c) every minute the water reading is valid. While
  the compressor rests, the circulating loop water sits near the slab temperature, so DM falls at
  the rate the slab is below what the house needs; while it runs, DM climbs with the heat put in.
  DM is therefore the accumulated heat deficit of the slab, and the run length is set by DM
  thresholds rather than by the firmware's 4 K restart gap.
- **Start** when DM <= -dm_start: write the smallest setpoint the firmware's restart rule accepts
  (estimated control sensor + restart_delta). Once the compressor runs, **ride** the setpoint at
  the level that keeps the firmware's capacity loop at a moderate output q_run (setpoint about
  inlet + q_run / (cp x flow)), or higher when the curve itself needs more (continuous running in
  cold weather, with DM feedback on top, capped at +3 K so the setpoint cannot wind up to 39).
- **Stop** when DM >= dm_stop (after a minimum run): write a setpoint far enough below the control
  sensor that the firmware stops at once (never below 25 degC, the recorded range) and wait in
  'stopping' until the compressor is off, stepping lower if it is not; then **park** the setpoint
  a few kelvin below the curve. While idle and DM does not ask for heat, a **guard** pulls the park
  under the firmware's restart threshold (estimated control sensor + restart_delta - 0.6) as the
  loop cools, never below 25 degC, so the firmware does not start on its own but would still heat
  (as a low thermostat) if Home Assistant went away.

Fail-safes: link down -> no writes, DM and states frozen; hot water (and the minutes after it,
when the water sensors read tank water) -> DM frozen, the run state waits for the unit; defrost ->
the run state waits, DM keeps integrating (a defrost really draws heat from the loop, so the cold
outlet is a true deficit); room missing or stale (> 90 min) -> curve plus the learned trim only;
forecast missing -> the last forecast still covering the coming hours; none -> smoothed unit
sensor, sun from PV (current irradiance, for the thermometer correction only) and a 1.5x faster
room integral; unavailable (None) water or outdoor readings -> treated as a link outage (room trim
frozen after 120 min of it); space heating off at hand-over ->
switched on once; switched off later (by the owner) -> respected, no writes.
"""
from __future__ import annotations

import math

from lab.sim.interface import Command, Observation

CP_FLOW = 2.02      # kW per K of loop delta-T at the documented ~29 L/min (only scales the ride)
SP_MIN = 25.0       # lowest park / run setpoint
SP_STOP = 25.0      # lowest transient stop write: inside the recorded range (review round 2)
SP_PARK_FLOOR = 25.0  # lowest park when the park is pulled under the restart threshold
PV_GHI = 112.0      # W/m2 of global irradiance per kW of PV (SIMULATOR.md: 8.9 kW per kW/m2);
                    # only a start value, re-learnt online whenever forecast and PV are both known
SP_MAX = 39.0       # highest setpoint of the recorded range (25-39 degC)


class DegreeMinutes:
    name = "degree_minutes"

    def reset(self, params: dict) -> None:
        g = lambda k, d: float(params.get(k, d))  # noqa: E731
        # curve: mean outlet (over on and off time) the house needs; fitted on a room-holding
        # season run, the room integral learns the rest
        self.c0 = g("c0", 25.4)            # degC at outdoor = target
        self.c1 = g("c1", 0.21)            # K per K of (target - t_eff)
        self.h_fc = int(g("h_fc", 12))     # forecast hours averaged for t_eff
        self.w_fc = g("w_fc", 0.7)         # weight of the forecast in t_eff (rest: smoothed sensor)
        self.tau_out = g("tau_out_h", 12.0)
        self.sun_k = g("sun_k", 0.045)     # K of T_c per W/m2 of forecast GHI (mean of the next h_sun hours)
        self.h_sun = int(g("h_sun", 8))
        # room trim
        self.kp = g("kp", 2.0)             # K of T_c per K of room error
        self.ki = g("ki", 0.15)            # K of T_c per K-hour of room error
        self.i_lim = g("i_lim", 6.0)
        self.glow = g("glow", 0.0008)      # thermometer reads warm in sun: K per W/m2 of GHI (house model)
        self.room_stale = g("room_stale_min", 90.0)
        # degree-minute thresholds (K min)
        self.dm_start = g("dm_start", 225.0)
        self.dm_stop = g("dm_stop", 200.0)
        self.dm_lo = g("dm_lo", 1200.0)    # clamp of the deficit (anti-windup)
        self.dm_hi = g("dm_hi", 300.0)     # surplus allowed above dm_stop (sunny days)
        # run execution
        self.q_run = g("q_run", 5.5)       # kW the ride aims at (the unit settles about 0.5 kW above)
        self.tau_dm = g("tau_dm", 120.0)   # min: DM feedback on the ride setpoint (continuous mode)
        self.min_run = g("min_run", 40.0)
        self.min_off = g("min_off", 30.0)
        self.ride_gap = g("ride_gap", 15.0)  # minutes between ride writes
        self.park_margin = g("park_margin", 3.0)
        self.max_starts = g("max_starts", 7.0)  # per rolling 24 h before the start threshold doubles
        # state
        self.dm = 0.0
        self.integral = 0.0
        self.t_avg = None
        self.state = "off"          # off | starting | run
        self.t_state = 0            # minute the state was entered
        self.last_write = -10_000
        self.mask = 0               # minutes of invalid water readings left (hot water)
        self.start_log = []
        self.park_due = False
        self.last_tc = None
        self.dm_ride_cap = g("dm_ride_cap", 3.0)  # K: most the deficit may lift the ride setpoint
        self.guard = g("guard", 1.0) > 0      # pull the park under the restart threshold when idle
        self.guard_margin = g("guard_margin", 0.6)
        self.sp_stop = g("sp_stop", SP_STOP)
        self.park_floor = g("park_floor", SP_PARK_FLOOR)
        self.seen_enabled = False   # heating seen on: a later off is the owner's and is respected
        self.ki_nofc = g("ki_nofc", 1.5)       # integral speed-up when no forecast is usable
        self.fc_cache = ()          # last forecast received (stale fallback)
        self.pv_ghi = g("pv_ghi", PV_GHI)
        self.int_outage = g("int_outage_min", 120.0)  # minutes of a link outage the room trim keeps integrating
        self.outage = 0
        self.kicks = 0

    # ------------------------------------------------------------------ inputs
    def _forecast(self, obs: Observation):
        """The current forecast, or the hours of the last one still ahead of now (stale issue)."""
        fc = obs.forecast
        if fc and len(fc) >= 6:
            self.fc_cache = fc
            return fc
        old = self.fc_cache
        if not old:
            return ()
        try:
            ahead = tuple(h for h in old if h["time"] > obs.time)
        except (KeyError, TypeError):
            return ()
        return ahead if len(ahead) >= 3 else ()

    @staticmethod
    def _fc_mean(fc, key: str, n: int):
        if not fc or n <= 0:
            return None
        n = min(n, len(fc))
        try:
            return sum(float(h.get(key) or 0.0) for h in fc[:n]) / n
        except (AttributeError, TypeError, ValueError):
            return None

    def t_eff(self, fc) -> float:
        tf = self._fc_mean(fc, "outdoor", self.h_fc) if self.w_fc > 0 else None
        if tf is None:
            return self.t_avg
        return self.w_fc * tf + (1.0 - self.w_fc) * self.t_avg

    def _pv(self, obs: Observation):
        try:
            pv = float(obs.pv_kw)
        except (TypeError, ValueError):
            return None
        return pv if math.isfinite(pv) and pv >= 0.0 else None

    def target_flow(self, obs: Observation, integrate: bool = True) -> float:
        fc = self._forecast(obs)
        pv = self._pv(obs)
        ghi_fc = self._fc_mean(fc, "ghi", 1)
        if ghi_fc is not None and pv is not None and ghi_fc > 150.0 and pv > 1.0:
            # learn the PV -> irradiance scale while both are known (slow: hourly vs minute values)
            self.pv_ghi += (min(max(ghi_fc / pv, 50.0), 250.0) - self.pv_ghi) / 2000.0
        if ghi_fc is not None:
            ghi_now = ghi_fc
        elif pv is not None:
            ghi_now = pv * self.pv_ghi
        else:
            ghi_now = 0.0
        err = 0.0
        if obs.room is not None and obs.room_age_min <= self.room_stale:
            err = obs.target - (obs.room - self.glow * ghi_now)
            if integrate:
                ki = self.ki * (1.0 if fc else self.ki_nofc)
                self.integral = min(max(self.integral + ki * err / 60.0, -self.i_lim), self.i_lim)
        sun = self._fc_mean(fc, "ghi", self.h_sun)
        if sun is None:
            sun = 0.0   # no forecast: no anticipation (a PV persistence term was tried and lost)
        return (self.c0 + self.c1 * (obs.target - self.t_eff(fc)) - self.sun_k * sun
                + self.kp * err + self.integral)

    # ------------------------------------------------------------------ registers
    def _write(self, obs: Observation, sp: float, lo: float = SP_MIN) -> Command:
        sp = float(min(max(round(sp), lo), SP_MAX))
        if sp == obs.setpoint:
            return Command()
        self.last_write = obs.minute
        return Command(setpoint=sp)

    def _park_sp(self, tc: float) -> float:
        return max(SP_MIN, round(tc - self.park_margin))

    def _ride_sp(self, obs: Observation, tc: float) -> float:
        # the firmware holds its control sensor in [sp - 1.0, sp - 0.1]; t_ctrl ~ supply - 0.8 -
        # 0.025 (Q - 5) and supply ~ inlet + Q / (cp flow): aim the middle of the band at q_run
        q = self.q_run
        sp_q = obs.inlet + q / CP_FLOW - 0.8 - 0.025 * (q - 5.0) + 0.55
        # continuous mode: the outlet (about sp + 0.3) should sit at the curve, pulled by the deficit
        sp_c = tc - 0.3 + min(-self.dm / self.tau_dm, self.dm_ride_cap)
        return max(sp_q, sp_c)

    # ------------------------------------------------------------------ step
    @staticmethod
    def _valid(obs: Observation) -> bool:
        for v in (obs.outdoor, obs.outlet, obs.inlet, obs.setpoint, obs.restart_delta):
            try:
                if not math.isfinite(float(v)):
                    return False
            except (TypeError, ValueError):
                return False
        return True

    def step(self, obs: Observation) -> Command:
        if not obs.link_ok or not self._valid(obs):
            # stale or unavailable unit values: no writes, DM and states frozen. The room trim
            # keeps learning from the (independent) thermometer through a short drop, and freezes
            # in a long outage, where it could only wind up against a unit it cannot reach.
            self.outage += 1
            if self.outage <= self.int_outage and self.t_avg is not None:
                self.target_flow(obs)
            return Command()
        self.outage = 0
        if self.t_avg is None:
            self.t_avg = obs.outdoor
        self.t_avg += (obs.outdoor - self.t_avg) / (self.tau_out * 60.0)
        tc = self.target_flow(obs)
        self.last_tc = tc
        if not obs.heating_enabled:
            if self.seen_enabled:
                return Command()                   # switched off by the owner: hands off
            return Command(heating_enabled=True)   # off at hand-over: the controller was asked to heat
        self.seen_enabled = True

        # hot water: the sensors read tank water during it and for ~7 minutes after
        if obs.mode == "dhw":
            self.mask = 10
        elif self.mask > 0:
            self.mask -= 1
        water_ok = obs.mode != "dhw" and self.mask == 0

        if water_ok:
            self.dm = min(max(self.dm + obs.outlet - tc, -self.dm_lo), self.dm_stop + self.dm_hi)

        now = obs.minute
        self.start_log = [t for t in self.start_log if now - t < 1440]
        age = now - self.t_state

        if self.state == "starting":
            if obs.compressor_on and obs.mode == "heat":
                self.state, self.t_state = "run", now
                self.start_log.append(now)
                return Command()
            if obs.mode == "dhw":
                return Command()                   # the unit serves the tank first; wait
            if age >= 20 or (age >= 4 and self.kicks >= 2):
                # no start after the kick and two retries: give up, park, let DM ask again later
                self.state, self.t_state = "off", now
                self.park_due = True
                return Command()
            if age >= 4 and water_ok:
                # the kick did not start it (control-sensor estimate off): one more kelvin, twice at most
                self.t_state = now
                self.kicks += 1
                return self._write(obs, obs.setpoint + 1)
            return Command()

        if self.state == "stopping":
            if not obs.compressor_on or obs.mode != "heat":
                self.state, self.t_state = "off", now
                return Command()
            if age >= 30 and obs.setpoint <= self.sp_stop:
                # the floor write cannot stop a cool run: hand it back to the run state (the ride
                # keeps the output at the floor; the next stop comes when the water is warmer)
                self.state, self.t_state = "run", now - int(self.min_run)
                return Command()
            if age >= 3 and now - self.last_write >= 3:
                # still running (control sensor estimate off): one more step down
                return self._write(obs, min(obs.setpoint, obs.outlet - 3.0) - 1, self.sp_stop)
            return Command()

        if self.state == "run":
            if obs.mode in ("dhw", "defrost"):
                return Command()
            if not obs.compressor_on:
                # stopped by the unit (surge, defrost, hot water): park and let DM decide
                self.state, self.t_state = "off", now
                park = self._park_sp(tc)
                if water_ok and obs.setpoint > park:
                    return self._write(obs, park)
                self.park_due = True
                return Command()
            if self.dm >= self.dm_stop and age >= self.min_run:
                sp = min(self._park_sp(tc), math.floor(obs.outlet - 0.5 - 2.5))
                self.state, self.t_state = "stopping", now
                self.park_due = sp < self._park_sp(tc)
                return self._write(obs, sp, self.sp_stop)
            if age >= 2 and now - self.last_write >= self.ride_gap:
                sp = round(self._ride_sp(obs, tc))
                if sp != obs.setpoint:
                    return self._write(obs, sp)
            return Command()

        # state off
        if not water_ok or obs.mode == "defrost":
            return Command()
        if obs.compressor_on and obs.mode == "heat":
            # the firmware started on its own (backstop start): adopt the run
            self.state, self.t_state = "run", now
            self.start_log.append(now)
            return Command()
        thr = self.dm_start * (2.0 if len(self.start_log) >= self.max_starts else 1.0)
        if self.dm <= -thr and age >= self.min_off:
            sp = math.ceil(obs.inlet - 0.7 + obs.restart_delta + 0.3)
            self.state, self.t_state = "starting", now
            self.park_due = False
            self.kicks = 0
            return self._write(obs, sp)
        # keep the firmware from starting on its own while DM does not ask for heat: as the loop
        # cools, pull the park under the restart threshold (never below SP_PARK_FLOOR, so the
        # park stays a low backstop thermostat if Home Assistant goes away)
        ctrl_est = obs.inlet - 0.7
        if (self.guard and self.dm > -thr and now - self.last_write >= 10
                and obs.setpoint - ctrl_est >= obs.restart_delta - self.guard_margin
                and obs.setpoint > self.park_floor):
            return self._write(obs, math.floor(ctrl_est + obs.restart_delta - self.guard_margin - 1.0),
                               self.park_floor)
        # keep the park setpoint near the curve (backstop), without risking a firmware start
        park = self._park_sp(tc)
        if age >= 20 and (self.park_due or abs(obs.setpoint - park) >= 2):
            if park - (obs.inlet - 0.7) < obs.restart_delta - 1.0 or park < obs.setpoint:
                self.park_due = False
                return self._write(obs, park)
        return Command()


CONTROLLER = DegreeMinutes


if __name__ == "__main__":
    from datetime import datetime, timezone

    def ob(**kw):
        base = dict(time=datetime(2026, 1, 1, tzinfo=timezone.utc), local_hour=12.0, room=22.0, room_age_min=5,
                    outdoor=5.0, outlet=27.0, inlet=27.3, setpoint=27.0, restart_delta=4.0, quiet=False,
                    heating_enabled=True, compressor_on=False, mode="idle", electric_kw=0.0, energy_kwh=0.0,
                    target=22.0, forecast=(), pv_kw=None, minute=0, link_ok=True)
        base.update(kw)
        return Observation(**base)

    c = DegreeMinutes()
    c.reset({})
    assert c.step(ob(link_ok=False)) == Command()                       # link down: never writes
    assert c.step(ob(outlet=None, inlet=None, outdoor=None)) == Command()  # unavailable sensors: no writes
    assert c.integral == 0.0 and c.t_avg is None                         # ... and nothing integrates
    assert c.step(ob(minute=1, heating_enabled=False)) == Command(heating_enabled=True)
    # cold water, idle: DM falls, then a start kick at least restart_delta above the control sensor
    m = 1
    for m in range(2, 3000):
        cmd = c.step(ob(minute=m, outlet=24.0, inlet=24.3, setpoint=25.0))
        if cmd.setpoint is not None and cmd.setpoint >= 24.3 - 0.7 + 4.0:
            break
    assert c.state == "starting", (c.state, c.dm)
    # hot water: DM frozen, no writes
    dm0 = c.dm
    assert c.step(ob(minute=m + 1, mode="dhw", outlet=45.0, inlet=44.0)) == Command()
    assert c.dm == dm0
    # running: the ride setpoint stays well below a hot burst and inside the recorded range
    c.state, c.t_state, c.dm, c.mask = "run", m, -100.0, 0
    cmd = c.step(ob(minute=m + 30, compressor_on=True, mode="heat", outlet=28.0, inlet=25.0, setpoint=29.0))
    assert cmd.setpoint is None or 25 <= cmd.setpoint <= 30, cmd
    # deficit paid back: a stop write crosses the firmware's stop threshold (t_ctrl >= sp + 2)
    c.dm = c.dm_stop + 1
    cmd = c.step(ob(minute=m + 90, compressor_on=True, mode="heat", outlet=30.0, inlet=27.0, setpoint=29.0))
    assert cmd.setpoint is not None and 30.0 - 0.5 - cmd.setpoint >= 2.0, cmd
    # stopping: wait until the compressor is off, step lower if the stop write did not take
    assert c.state == "stopping"
    cmd = c.step(ob(minute=m + 95, compressor_on=True, mode="heat", outlet=30.0, inlet=27.0, setpoint=26.0))
    assert cmd.setpoint is not None and cmd.setpoint < 26.0, cmd
    c.step(ob(minute=m + 96, compressor_on=False, mode="idle", outlet=29.0, inlet=27.0, setpoint=25.0))
    assert c.state == "off"
    # heating switched off by the owner after it was on: respected
    assert c.step(ob(minute=m + 100, heating_enabled=False)) == Command()
    # room and forecast missing: a finite target
    assert math.isfinite(c.target_flow(ob(room=None, forecast=())))
    print("degree_minutes self-check ok")
