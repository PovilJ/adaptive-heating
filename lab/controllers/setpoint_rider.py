"""Setpoint rider (S6): decide a heat rate from the weather and the room, then hold the compressor
at a chosen output by riding the leaving-water setpoint just above the water the unit sees
(stdlib only). Design notes and results: docs/research/lab/controllers/setpoint_rider.md.

The Versati sets its compressor speed from the error setpoint - control sensor: it ramps up while
the error is above about 1 K, holds while it sits in a band of about 0.1..1.0 K and ramps down
below that; it stops when the control sensor is 2 K above the setpoint for 3 minutes (at once if a
write makes that true). So a setpoint is a power request, not a temperature request. This
controller uses that directly:

- **Heat rate wanted** P_dem (kW): a load line on the forecast outdoor temperature 2-10 h ahead,
  minus forecast sun, plus a learned daily profile, plus a PI term on the room error (thermometer
  corrected for its sun glow, aim trimmed slowly so the long-run mean room sits on target).
- **Daily profile** (repetitive control): 24 hour bins of heat correction, each integrating the
  room error seen 9 h later (the slab-and-room lag), zero mean, +-2 kW. It learns, within one or
  two weeks, to put heat into the afternoon and evening and to hold back in the early morning, which
  cancels the house's recurring warm-afternoon / cold-night swing (internal gains, sun, habits).
- **When to run** (sigma-delta heat accounting): a balance D (kWh, clamped +-5) integrates P_dem
  minus the heat the unit puts into the loop, measured from the unit's own outlet - inlet. A block
  starts when D reaches +E/2 and ends when it falls to -E/2. When the smoothed demand exceeds what
  the unit delivers at its floor the run never ends (continuous modulation).
- **How hard to run** (the ride): the target output is q_run (5 kW) in blocks and P_dem + D / tau
  when running continuously. The setpoint is written at inlet + q / cp_flow - 0.25, which puts the
  firmware's hold band around that output, so the firmware's own error loop holds it at the
  lowest supply temperature that delivers it. Writes are hysteretic (only when the ideal setpoint
  moved by more than 0.75 K, at most every 10 min) and never below control sensor - 1.5 K (no
  accidental stop) or above a weather ceiling (no catch-up bursts). Mid output, not the minimum:
  in this unit's measured COP surface the minimum output is 15-25 % less efficient at the same
  water temperature, and riding at the minimum cost about 3 % more energy in the lab.
- **Starts** use the smallest setpoint the restart rule accepts (inlet - 0.8 + restart_delta);
  **stops** write a setpoint 2.3 K under the control sensor (never below 25 degC), so the firmware
  stops at once; it is kept while parked as an outage backstop (the firmware restarts by itself
  once the loop has cooled about 3 K) and lowered only when the restart rule is about to fire.

Fail-safe: link down -> no writes (the heat accounting holds its last reading); room missing ->
integral, trim and profile freeze, the load line carries on; forecast missing -> the unit's
outdoor sensor smoothed over 24 h; DHW -> no loop heat counted and no ride writes during DHW and
the 10 minutes after it (tank water on the sensors), and a stop decided then takes its park value
from the last loop reading and never raises the setpoint; a run the firmware ended (surge, defrost,
DHW) is re-kicked only after 6 minutes off (minimum off time), with the restart rule held shut
until then; defrost -> no ride writes for 10 minutes; thermometer older than 3 h -> treated as
missing. Writes: a hard cap of 46 in any 24 h covers every write (ride writes stop at 44, start
requests at 42, the rest is kept for stops); a start request is fixed per attempt and backs off
(15, 30, 60 ... 240 min) when the unit does not answer; a stop that does not take is written again
1 K lower after 5 minutes (twice at most).
"""
from __future__ import annotations

import math

from lab.sim.interface import Command, Observation

PARK_SP = 25.0      # lowest setpoint ever written to the real unit; parks the compressor
SP_MAX = 45.0
KF = 2.02           # kW per K of loop delta-T at the documented 29 L/min (a scale only)
GLOW_K_PER_WM2 = 0.0008  # thermometer sun glow (HOUSE_MODEL.md: 0.8 mK per W/m2 of global irradiance)


def q_floor(t_out: float) -> float:
    """The unit's minimum steady heat output, kW (UNIT_MODEL.md section 4: 1.8 K + 0.05 K/K)."""
    return KF * min(max(1.8 + 0.05 * t_out, 1.4), 2.4)


class SetpointRider:
    name = "setpoint_rider"

    def reset(self, params: dict) -> None:
        g = lambda k, d: float(params.get(k, d))  # noqa: E731
        # load line at 22 degC (public house model: 3.7 kW at 0 degC, 0.135 kW/K; 0.187 kW/K of target)
        self.a0 = g("a0", 3.7)
        self.b = g("b", 0.135)
        self.h_tgt = g("h_tgt", 0.187)
        self.g_sun = g("g_sun", 0.012)        # kW per W/m2 of forecast global irradiance
        self.lead = int(g("lead_h", 2))       # forecast hours skipped (slab lag)
        self.horizon = int(g("horizon_h", 8))
        self.glow = g("glow", GLOW_K_PER_WM2)
        self.aim = g("aim", 0.0)              # aim offset on the corrected room reading, K
        self.tau_mean = g("tau_mean_h", 720.0)  # h: slow aim trim that holds the long-run mean room on target (0 = off)
        self.mean_lim = g("mean_lim", 0.5)
        # daily profile (repetitive control): a learned heat correction per local hour that cancels
        # the room's recurring day/night swing (internal gains, sun, habits). Each hour bin integrates
        # the room error seen `prof_lead_h` later (the slab's lag), zero mean (the integral owns the mean).
        self.k_prof = g("k_prof", 0.5)        # kW per K-hour of error (0 = off)
        self.prof_lead = g("prof_lead_h", 9.0)
        self.prof_lim = g("prof_lim", 2.0)
        # room feedback
        self.kp = g("kp", 2.5)                # kW per K
        self.ki = g("ki", 0.05)                # kW per K-hour
        self.i_lim = g("i_lim", 3.0)
        # heat accounting / blocks
        self.q_run = g("q_run", 5.0)          # kW in blocks (review: 6 -> 5, cooler water, flatter COP risk)
        self.e_blk = g("e_blk", 8.0)          # kWh between start and stop thresholds
        self.min_run = g("min_run", 60.0)
        self.min_off = g("min_off", 30.0)
        self.tau_c = g("tau_c", 2.0)          # h over which a continuous run works off the balance
        self.q_cont = g("q_cont", 4.5)        # kW of (smoothed) demand above which the unit runs continuously
        self.d_lim = max(g("d_lim", 5.0), self.e_blk / 2 + 0.5)  # balance clamp, kWh (must exceed the start threshold)
        # ride
        self.ride_every = g("ride_every", 10.0)
        self.ride_hyst = g("ride_hyst", 0.75)
        self.dhw_guard = int(g("dhw_guard", 10))  # minutes after the unit leaves hot water before loop readings count
        self.ride_off = g("ride_off", 0.25)   # K: setpoint = inlet + q / cp_flow - this
        self.ceil_a = g("ceil_a", 31.0)       # ceiling setpoint at 0 degC ...
        self.ceil_b = g("ceil_b", 0.5)        # ... rising this much per K colder
        self.max_writes = g("max_writes", 44.0)  # rolling 24 h budget for ride writes
        self.hard_writes = g("hard_writes", 46.0)  # rolling 24 h cap on EVERY write (rule: 48)
        self.kick_writes = g("kick_writes", 42.0)  # start requests stop here; the rest is kept for stops
        self.kick_fail = g("kick_fail", 15.0)  # min without a start before a request counts as failed
        self.kick_back = g("kick_back", 15.0)  # first back-off after a failed request, min (doubles, max 4 h)
        self.stop_gap = g("stop_gap", 2.8)    # K: stop writes floor(t_ctrl_est - this)
        self.q_exit = g("q_exit", 0.0)        # kW: continuous mode is left only this far below where it is entered
        self.tau_mean_min = g("tau_mean_min_h", 720.0)  # h: aim-trim time constant at takeover (grows to tau_mean)
        self.room_stale = g("room_stale_min", 180.0)  # thermometer older than this counts as missing
        self.park_high = bool(params.get("park_high", True))  # park just under the stop threshold (outage backstop)
        # state
        self.I = 0.0
        self.trim = 0.0
        self.prof = [0.0] * 24
        self.D = 0.0
        self.running = False
        self.t_state = 10_000
        self.last_write = -10_000
        self.write_log: list[int] = []
        self.t_avg = None
        self.since_dhw = 10_000
        self.since_defrost = 10_000
        self.q_meas = 0.0
        self.q_smooth = 0.0
        self.p_smooth = 0.0
        self.kick_wait = 0
        self.off_min = 10_000
        self.park = None
        self.p_dem = 0.0
        self.p_slow = None
        self.q_tgt = 0.0
        self.cont = False
        self.kick_sp = None
        self.kick_n = 0
        self.kick_hold = 0
        self.guard_done = False
        self.stop_age = 10_000
        self.stop_tries = 0
        self.hours = 0.0
        self.t_loop = None  # last control-sensor estimate from loop water (heat mode, past the DHW guard)

    # ------------------------------------------------------------------ helpers
    def _weather(self, obs: Observation) -> tuple[float, float, float]:
        """(outdoor for the feed-forward, its sun, global irradiance now)."""
        a = 1.0 / (24 * 60)
        self.t_avg = obs.outdoor if self.t_avg is None else self.t_avg + a * (obs.outdoor - self.t_avg)
        fc = obs.forecast
        n = self.lead + self.horizon
        if fc and len(fc) >= n:
            hs = fc[self.lead:n]
            t = sum(h["outdoor"] for h in hs) / len(hs)
            ghi = sum((h.get("ghi") or 0.0) for h in hs) / len(hs)
            ghi_now = fc[0].get("ghi") or 0.0
            return t, ghi, ghi_now
        return self.t_avg, 0.0, 0.0

    def _profile(self, obs: Observation, e0: float | None) -> float:
        """Learned daily heat profile, kW (zero mean), interpolated at the current local hour."""
        if self.k_prof <= 0:
            return 0.0
        if e0 is not None:
            h = (obs.local_hour - self.prof_lead) % 24.0
            i = int(h) % 24
            f = h - int(h)
            d = self.k_prof * max(-1.0, min(1.0, e0)) / 60.0
            self.prof[i] += d * (1.0 - f)
            self.prof[(i + 1) % 24] += d * f
            m = sum(self.prof) / 24.0
            self.prof = [min(max(x - m, -self.prof_lim), self.prof_lim) for x in self.prof]
        h = obs.local_hour % 24.0
        i = int(h) % 24
        f = h - int(h)
        return self.prof[i] * (1.0 - f) + self.prof[(i + 1) % 24] * f

    def _write(self, obs: Observation, sp: float, essential: bool = False) -> Command:
        sp = float(min(max(round(sp), PARK_SP), SP_MAX))
        if sp == obs.setpoint:
            return Command()
        self.write_log = [m for m in self.write_log if obs.minute - m < 1440]
        n = len(self.write_log)
        cap = self.hard_writes if essential == "stop" else self.kick_writes if essential else self.max_writes
        if n >= min(cap, self.hard_writes):
            return Command()
        self.write_log.append(obs.minute)
        self.last_write = obs.minute
        return Command(setpoint=sp)

    def _stop(self, obs: Observation) -> Command:
        """End a block: a setpoint 2.3 K under the control sensor stops the firmware at once. It is
        kept as the park value (never below 25 degC): high enough that, should the link be lost for
        hours, the firmware restarts by itself once the loop has cooled about 3 K (a backstop)."""
        loop_ok = obs.mode == "heat" and self.since_dhw >= self.dhw_guard
        if obs.compressor_on and self.park_high and loop_ok:
            self.park = max(PARK_SP, math.floor(self._t_ctrl(obs) - self.stop_gap))
        elif self.park_high and self.t_loop is not None:
            # hot water or defrost: the sensors show tank water (45-54 degC) or a reversed cycle, so
            # the park comes from the last loop reading, never from them
            self.park = max(PARK_SP, math.floor(self.t_loop - self.stop_gap))
        else:
            self.park = PARK_SP
        # a stop never raises the setpoint (a link drop right after it must not leave a hot request)
        self.park = max(PARK_SP, min(self.park, math.floor(obs.setpoint)))
        self.stop_age = 0
        self.stop_tries = 0
        return self._write(obs, self.park, essential="stop")

    def _park(self, obs: Observation) -> Command:
        """While idle: hold the park value, lowering it only when the restart rule is about to fire.
        A stop that has not taken after 5 minutes is written again 1 K lower (at most twice)."""
        if self.park is None:
            self.park = PARK_SP
        if (obs.compressor_on and obs.mode == "heat" and self.since_dhw >= self.dhw_guard
                and self.stop_age >= 5 and self.stop_tries < 2):
            self.stop_tries += 1
            self.stop_age = 0
            self.park = max(PARK_SP, min(self.park, math.floor(self._t_ctrl(obs) - self.stop_gap)) - 1)
            return self._write(obs, self.park, essential="stop")
        if self.park > obs.inlet - 0.8 + obs.restart_delta - 0.7:
            self.park = max(PARK_SP, math.floor(obs.inlet - 0.8 + obs.restart_delta - 1.2))
        if obs.setpoint > self.park or obs.setpoint < PARK_SP:
            return self._write(obs, self.park, essential="stop")
        return Command()

    def _kick(self, obs: Observation) -> Command:
        """Request a start with the smallest setpoint the restart rule accepts, fixed per attempt (no
        re-rounding on a noisy inlet), bumped by 1 K once after 4 minutes. An attempt without a start
        after kick_fail minutes counts as failed: the setpoint is left where it is (the firmware's own
        rule can still fire) and the next attempt waits 15, 30, 60 ... (max 240) minutes."""
        if self.kick_hold > 0:
            self.kick_hold -= 1
            return Command()
        need = math.ceil(obs.inlet + 0.05 - 0.8 + obs.restart_delta)
        if self.kick_sp is None:
            self.kick_sp = need
            self.kick_wait = 0
        self.kick_wait += 1
        if self.kick_wait > self.kick_fail:
            self.kick_n += 1
            self.kick_hold = int(min(240.0, self.kick_back * 2 ** (self.kick_n - 1)))
            self.kick_sp = None
            return Command()
        sp = self.kick_sp + (1 if self.kick_wait > 4 else 0)
        return self._write(obs, sp, essential=True)

    def _t_ctrl(self, obs: Observation) -> float:
        """Estimate of the unit's control sensor while running (UNIT_MODEL.md section 2)."""
        return obs.outlet - 0.5 + 0.025 * (5.0 - self.q_smooth)

    # ------------------------------------------------------------------ step
    def step(self, obs: Observation) -> Command:
        t_fc, ghi, ghi_now = self._weather(obs)
        # room feedback on the glow-corrected thermometer
        e0 = 0.0
        self.hours += 1.0 / 60.0
        self.stop_age += 1
        room_ok = obs.room is not None and obs.room_age_min <= self.room_stale
        if room_ok:
            e0 = obs.target - (obs.room - self.glow * ghi_now)
            if self.tau_mean > 0:
                tau = min(self.tau_mean, max(self.tau_mean_min, self.hours))
                self.trim = min(max(self.trim + e0 / (tau * 60.0), -self.mean_lim), self.mean_lim)
            e = e0 + self.aim + self.trim
            self.I = min(max(self.I + self.ki * e / 60.0, -self.i_lim), self.i_lim)
        else:
            e = 0.0
        ff = self.a0 - self.b * t_fc + self.h_tgt * (obs.target - 22.0) - self.g_sun * ghi
        ff += self._profile(obs, e0 if room_ok else None)
        p_dem = ff + self.kp * e + self.I   # may go negative: the balance must see surplus heat too
        self.p_dem = p_dem
        self.p_slow = p_dem if self.p_slow is None else self.p_slow + (p_dem - self.p_slow) / 60.0

        # measured heat into the loop (none while the valve is on the tank or just after)
        mode = obs.mode
        self.since_dhw = 0 if mode == "dhw" else self.since_dhw + 1
        self.since_defrost = 0 if mode == "defrost" else self.since_defrost + 1
        if obs.link_ok:
            if obs.compressor_on and mode in ("heat", "defrost") and self.since_dhw > self.dhw_guard:
                self.q_meas = KF * (obs.outlet - obs.inlet + 0.3)
            else:
                self.q_meas = 0.0
            if obs.compressor_on and mode == "heat" and self.since_dhw > self.dhw_guard:
                self.t_loop = self._t_ctrl(obs)
            if obs.compressor_on and mode == "heat":
                self.q_smooth += 0.2 * (self.q_meas - self.q_smooth)
                if self.p_smooth <= 0.0:
                    self.p_smooth = obs.electric_kw
                self.p_smooth += (1.0 / 30.0) * (obs.electric_kw - self.p_smooth)
        self.D = min(max(self.D + (p_dem - self.q_meas) / 60.0, -self.d_lim), self.d_lim)
        self.t_state += 1
        if obs.link_ok:
            self.off_min = 0 if obs.compressor_on else self.off_min + 1

        if not obs.link_ok:
            return Command()

        qf = q_floor(t_fc)
        q_cont = p_dem + self.D / self.tau_c
        if self.p_slow >= max(self.q_cont, qf):
            self.cont = True
        elif self.p_slow < max(self.q_cont, qf) - self.q_exit:
            self.cont = False
        continuous = self.cont
        q_tgt = max(qf, q_cont) if continuous else max(self.q_run, qf, q_cont)
        self.q_tgt = q_tgt

        # --- block state machine ---
        if not self.running:
            if self.D >= self.e_blk / 2 and self.t_state >= self.min_off:
                self.running = True
                self.t_state = 0
                self.kick_wait = 0
            else:
                return self._park(obs)
        if self.D <= -self.e_blk / 2 and self.t_state >= self.min_run and not continuous:
            self.running = False
            self.t_state = 0
            return self._stop(obs)

        # --- run execution ---
        if mode in ("dhw", "defrost", "off") or self.since_dhw < self.dhw_guard:
            return Command()
        if not obs.compressor_on:
            # kick: the smallest setpoint the restart rule accepts; bump it if nothing happens.
            # After a stop the firmware's minimum off time (3-5 min) is respected first.
            if self.off_min < 6:
                # the unit stopped on its own (surge, defrost, hot water): keep the restart rule from
                # firing inside the firmware's minimum off time (one write); the kick follows at 6 minutes
                if not self.guard_done and obs.setpoint >= obs.inlet - 0.8 + obs.restart_delta - 0.5:
                    self.guard_done = True
                    return self._write(obs, math.floor(obs.inlet - 0.8 + obs.restart_delta - 1.0), essential=True)
                return Command()
            return self._kick(obs)
        self.kick_wait = 0
        self.kick_n = 0
        self.kick_sp = None
        self.guard_done = False
        # riding
        if obs.minute - self.last_write < self.ride_every or self.since_defrost < 10:
            return Command()
        surge = obs.electric_kw > max(1.5 * self.p_smooth, self.p_smooth + 0.8)
        sp_ideal = obs.inlet + q_tgt / KF - self.ride_off
        ceiling = self.ceil_a + self.ceil_b * max(0.0, -t_fc)
        sp_ideal = min(sp_ideal, ceiling)
        lo = self._t_ctrl(obs) - 1.5          # never write into the stop threshold
        sp_ideal = max(sp_ideal, lo)
        if abs(sp_ideal - obs.setpoint) > self.ride_hyst:
            if sp_ideal < obs.setpoint and surge:
                return Command()
            sp = math.ceil(lo) if round(sp_ideal) < lo else round(sp_ideal)
            return self._write(obs, sp)
        return Command()


CONTROLLER = SetpointRider


if __name__ == "__main__":
    from datetime import datetime, timezone

    def fc_at(t_out, ghi=0.0):
        return tuple({"time": datetime(2026, 1, 1, h % 24, tzinfo=timezone.utc), "outdoor": t_out, "rh": 80,
                      "ghi": ghi, "dni": 0, "dhi": 0, "cloud": 100} for h in range(48))

    base = dict(time=datetime(2026, 1, 1, tzinfo=timezone.utc), local_hour=2.0, room=21.5, room_age_min=5,
                outdoor=5.0, outlet=26.0, inlet=26.3, setpoint=25.0, restart_delta=4.0, quiet=False,
                heating_enabled=True, compressor_on=False, mode="idle", electric_kw=0.02, energy_kwh=0.0,
                target=22.0, forecast=fc_at(5.0), pv_kw=None)
    state = {"sp": 25.0}

    def drive(c, obs_kw, minutes, link_ok=True):
        """Step the controller with the setpoint register echoing its writes; return the writes."""
        out = []
        for m in minutes:
            cmd = c.step(Observation(minute=m, link_ok=link_ok, **dict(obs_kw, setpoint=state["sp"])))
            if cmd.setpoint is not None:
                if link_ok:
                    state["sp"] = cmd.setpoint
                out.append(cmd.setpoint)
        return out

    c = SetpointRider()
    c.reset({})
    # 1) a cold room starts a block with the smallest accepted setpoint: ceil(26.3 + 0.05 - 0.8 + 4) = 30
    w = drive(c, base, range(200))
    assert w and w[0] == 30.0 and c.running, w
    # 2) running: the ride writes about inlet + q / KF - 0.25 (q 6-7 kW here), never into the stop band
    run = dict(base, compressor_on=True, mode="heat", outlet=29.0, inlet=26.0, electric_kw=1.2)
    w = drive(c, run, range(200, 260))
    assert w and 28.0 <= w[0] <= 29.0 and min(w) > 28.5 - 2.0, w
    # 3) a warm room ends the block with a stop write >= 2 K under the control sensor (about 28.5)
    w = drive(c, dict(run, room=23.5), range(260, 600))
    assert w and w[-1] <= 28.5 - 2.0 and not c.running, (w, c.running)
    # 4) parked: nothing is written while idle unless the restart rule is about to fire
    idle = dict(run, room=23.5, compressor_on=False, mode="idle", outlet=26.0, inlet=26.3)
    assert drive(c, idle, range(600, 620)) == []
    w = drive(c, dict(idle, inlet=state["sp"] - 4.0 + 0.8 + 0.2), range(620, 621))  # rule 0.2 K from firing
    assert w == [PARK_SP] or (w == [] and state["sp"] == PARK_SP), w
    # 5) link down: no writes; hot water: no ride; room and forecast missing: no crash, demand still sane
    c.reset({})
    assert drive(c, base, range(0, 5), link_ok=False) == []
    assert drive(c, dict(run, mode="dhw"), range(5, 8)) == []
    drive(c, {**base, "room": None, "forecast": ()}, range(8, 100))
    assert 0.0 < c.p_dem < 6.0, c.p_dem
    # 6) the write budget holds under a flapping inlet (a stuck or noisy sensor)
    c.reset({})
    n = 0
    for k in range(3000):
        o = dict(run, inlet=26.0 + 3.0 * (k // 11 % 2), outlet=29.0 + 3.0 * (k // 11 % 2), room=20.0)
        n += len(drive(c, o, range(k, k + 1)))
    assert n <= 44 * 3000 / 1440 + 2, n
    # 7) a unit that never answers a start request (lockout, fault): the requests back off and every
    #    write, start requests included, stays inside the hard 24 h cap, even with a noisy inlet
    import random
    rnd = random.Random(1)
    c.reset({})
    state["sp"] = 25.0
    n = 0
    for k in range(3 * 1440):
        o = dict(base, room=20.0, inlet=round(26.3 - 0.12 * (k % 600) / 60 + rnd.gauss(0, 0.4), 1))
        n += len(drive(c, o, range(k, k + 1)))
    assert n <= 3 * 30, n
    print("stuck-unit writes over 3 days:", n)
    # 8) a block that ends while the unit heats the tank never writes a park above the current
    #    setpoint (tank water at 48 degC on the sensors must not become a 44 degC heating request)
    c.reset({})
    state["sp"] = 25.0
    drive(c, base, range(200))
    drive(c, run, range(200, 260))
    sp_run = state["sp"]
    w = drive(c, dict(run, room=25.5, mode="dhw", outlet=48.0, inlet=45.0, electric_kw=2.0), range(260, 600))
    assert w and max(w) <= sp_run and max(w) <= 28.5 - 2.0, (w, sp_run)
    print("self-check ok")
