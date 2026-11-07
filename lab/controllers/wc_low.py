"""wc_low: low-and-slow weather compensation (strategies S1 + S2 + S3), stdlib only.

Leaving-water setpoint = a weather curve on an "equivalent outdoor temperature" taken from the
forecast (outdoor air plus a solar term, averaged over the hours in which heat sent now reaches the
room through the slab), plus room influence: a proportional term on the room error and a slow
integral that shifts the whole curve. The firmware does the cycling: the controller never times
starts or stops, it only moves the curve and holds the restart hysteresis at 5 K (a recorded value).
Design, tuning and results: docs/research/lab/controllers/wc_low.md.

Fail-safe behaviour:
- room missing or older than `stale_min`: no room term and the integral is frozen (pure curve);
- restart: the integral is the only learned state; a deployment restores it (param `trim0`, HA
  RestoreEntity). The curve is calibrated so that the integral averages near 0, so losing it costs
  little (review fix R1);
- forecast without irradiance (e.g. met.no): a climatological sun schedule by month and hour
  replaces it (review 2: most of the sun gain is this schedule; the forecast irradiance adds ~0.9 pt);
- forecast missing: the unit's own outdoor sensor, damped over `tau_meas_h`, plus the same
  climatological sun terms; a blind first step (no forecast, link down) seeds the sensor value even
  if stale, else a monthly mean;
- link down: the sensor damping skips the stale minutes; commands wait in the unit's queue;
- DHW and defrost need no special case: the setpoint only moves the curve, the firmware handles
  priority, and writes are whole degrees with hysteresis.
"""
from __future__ import annotations

import math

from lab.sim.interface import Command, Observation

# climatological irradiance shape near Vilnius (55 N): (peak W/m2 of the monthly mean day, sunrise,
# sunset in local hours); a schedule used only when the forecast carries no irradiance
_CLIM = {10: (230.0, 7.5, 18.0), 11: (130.0, 8.0, 16.0), 12: (70.0, 8.8, 15.8), 1: (100.0, 8.7, 16.3),
         2: (230.0, 8.0, 17.3), 3: (330.0, 6.8, 18.5), 4: (420.0, 6.0, 20.2), 5: (600.0, 5.2, 21.2),
         6: (650.0, 4.8, 21.8), 7: (630.0, 5.0, 21.6), 8: (530.0, 5.8, 20.8), 9: (420.0, 6.8, 19.5)}
# rough monthly mean outdoor temperature (degC), only for a blind first step with no data at all
_MONTH_T = {10: 7.0, 11: 2.0, 12: -2.0, 1: -4.5, 2: -3.5, 3: 1.0, 4: 7.5, 5: 13.0, 6: 16.5, 7: 18.5,
            8: 17.5, 9: 12.5}


class WcLow:
    name = "wc_low"

    def reset(self, params: dict) -> None:
        g = lambda k, d: float(params.get(k, d))
        # weather curve: sp = target + base + slope x (target - t_eq)
        self.slope = g("slope", 0.37)          # K of water per K of (target - t_eq)
        self.base = g("base", 0.8)             # K of water above target at t_eq = target
        # equivalent outdoor temperature: mean of forecast hours fc_skip .. fc_skip + h_fc - 1
        self.fc_skip = int(g("fc_skip", 3))    # hours skipped (the slab's delay)
        self.h_fc = int(g("h_fc", 4))          # hours averaged
        self.sun_g = g("sun_g", 8.0)           # K of equivalent outdoor per 100 W/m2 of global irradiance
        self.sun_d = g("sun_d", 5.0)           # same, for the mean irradiance of the next 24 h (sun stored in the slab)
        # cold-weather kink: below t_knee the unit stops cycling, so the mean water sits closer to the
        # setpoint and the setpoint needed rises more slowly
        self.k_cold = g("k_cold", 0.3)
        self.t_knee = g("t_knee", -2.0)
        self.tau_meas = g("tau_meas_h", 6.0)   # damping of the unit's outdoor sensor (fallback), hours
        # room influence
        self.kp = g("kp", 4.0)                 # K of water per K of room error
        self.ki = g("ki", 0.15)                # K of water per K-hour of room error
        self.i_lim = g("i_lim", 5.0)           # |integral| bound, K of water
        self.stale_min = g("stale_min", 360.0)  # room older than this is ignored
        # registers
        self.hyst = g("hyst", 1.0)             # K the wanted setpoint must move before a write
        self.sp_min = g("sp_min", 25.0)        # lowest setpoint ever written on the real unit
        self.sp_max = g("sp_max", 39.0)
        self.delta = g("delta", 5.0)           # restart hysteresis (4 and 5 K are the recorded values)
        # share of the downward integration kept while the setpoint is held at the floor (sun the
        # curve cannot prevent): 1 repays all of that overheating later, 0 is classic anti-windup
        self.floor_keep = g("floor_keep", 0.7)
        self.quiet_mode = bool(params.get("quiet", False))
        # climatological sun (review 2, R2-1/R2-6): used for the irradiance when the forecast carries
        # none, and on top of the damped unit sensor when there is no forecast at all
        self.clim = bool(params.get("clim", True))
        self.t_meas = None
        self.trim = g("trim0", 0.0)            # restored integral (HA: RestoreEntity); 0 on a first install
        self.current = None
        self.t_eq_last = None

    @staticmethod
    def clim_ghi(month: int, local_hour: float) -> float:
        """Climatological mean global irradiance (W/m2) near Vilnius by month and local hour: a
        half-sine day whose length and height follow the month (a schedule, no forecast skill)."""
        peak, rise, sett = _CLIM.get(month, (250.0, 7.0, 17.0))
        if not rise < local_hour < sett:
            return 0.0
        return peak * math.sin(math.pi * (local_hour - rise) / (sett - rise))

    def ghi_list(self, obs: Observation, fc) -> list:
        """Irradiance per forecast hour; climatology when the provider sends none."""
        g = [h.get("ghi") for h in fc]
        if self.clim and not any(x is not None and x == x for x in g):
            return [self.clim_ghi(h["time"].month if "time" in h else obs.time.month,
                                  (obs.local_hour + i + 1) % 24) for i, h in enumerate(fc)]
        return [x if x is not None and x == x else 0.0 for x in g]

    def t_equivalent(self, obs: Observation) -> float | None:
        fc = obs.forecast or ()
        ghi = self.ghi_list(obs, fc)
        num = 0.0
        n = 0
        for i in range(self.fc_skip, min(len(fc), self.fc_skip + self.h_fc)):
            t = fc[i].get("outdoor")
            if t is None or t != t:
                continue
            num += t + self.sun_g * ghi[i] / 100.0
            n += 1
        if n:
            t = num / n
            if self.sun_d:
                day = ghi[:24]
                t += self.sun_d * sum(day) / len(day) / 100.0
            return t
        if self.t_meas is None or not self.clim:
            return self.t_meas
        # no forecast at all: the damped unit sensor plus the same sun terms from climatology
        hrs = [self.clim_ghi(obs.time.month, (obs.local_hour + i + 1) % 24) for i in range(24)]
        sh = hrs[self.fc_skip:self.fc_skip + self.h_fc]
        return self.t_meas + self.sun_g * sum(sh) / len(sh) / 100.0 + self.sun_d * sum(hrs) / 24.0 / 100.0

    def step(self, obs: Observation) -> Command:
        if obs.outdoor is not None and obs.outdoor == obs.outdoor:
            if self.t_meas is None:
                self.t_meas = obs.outdoor          # seed even from a stale value (review 2, R2-7)
            elif obs.link_ok:
                self.t_meas += (obs.outdoor - self.t_meas) / (self.tau_meas * 60.0)
        t_eq = self.t_equivalent(obs)
        if t_eq is None:
            t_eq = self.t_eq_last if self.t_eq_last is not None else _MONTH_T.get(obs.time.month, 0.0)
        self.t_eq_last = t_eq
        target = obs.target
        ff = target + self.base + self.slope * (target - t_eq) - self.k_cold * max(0.0, self.t_knee - t_eq)

        err = 0.0
        if obs.room is not None and obs.room_age_min < self.stale_min:
            err = target - obs.room
            # while the setpoint sits at the 25 degC floor, sun the curve cannot prevent overheats the
            # room; 70 % of that error still winds the integral down, so part of it is paid back by a
            # cooler curve afterwards (the mean-air rule); full repayment ran 0.04 K cold, none 0.1 K warm
            d = self.ki * err / 60.0
            if d < 0 and ff + self.trim + self.kp * err <= self.sp_min:
                d *= self.floor_keep
            self.trim = min(max(self.trim + d, -self.i_lim), self.i_lim)
        want = min(max(ff + self.trim + self.kp * err, self.sp_min), self.sp_max)
        if self.current is None or abs(want - self.current) >= self.hyst:
            self.current = float(round(want))

        cmd = {}
        if obs.setpoint != self.current:
            cmd["setpoint"] = self.current
        if not obs.heating_enabled:
            cmd["heating_enabled"] = True
        if obs.restart_delta != self.delta:
            cmd["restart_delta"] = self.delta
        if obs.quiet != self.quiet_mode:
            cmd["quiet"] = self.quiet_mode
        return Command(**cmd)


CONTROLLER = WcLow


if __name__ == "__main__":  # small self-check
    from datetime import datetime, timedelta, timezone

    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def obs(room=22.0, outdoor=0.0, fc_t=0.0, ghi=0.0, fc=True, age=10.0, **kw):
        f = tuple(dict(time=t0 + timedelta(hours=i + 1), outdoor=fc_t, rh=80, ghi=ghi, dni=0, dhi=0, cloud=50)
                  for i in range(48)) if fc else ()
        base = dict(time=t0, local_hour=2.0, room=room, room_age_min=age, outdoor=outdoor, outlet=28.0, inlet=26.0,
                    setpoint=30.0, restart_delta=5.0, quiet=False, heating_enabled=True, compressor_on=False,
                    mode="idle", electric_kw=0.0, energy_kwh=0.0, target=22.0, forecast=f, pv_kw=None)
        base.update(kw)
        return Observation(**base)

    c = WcLow()
    c.reset({})
    c.step(obs(fc_t=0.0))
    sp0 = c.current
    assert sp0 == round(22.8 + 0.37 * 22), sp0
    c.reset({})
    c.step(obs(fc_t=-10.0))
    assert c.current > sp0                       # colder forecast, warmer water
    assert c.current == round(22.8 + 0.37 * 32 - 0.3 * 8)  # cold kink below -2 degC
    c.reset({})
    c.step(obs(fc_t=-25.0, room=19.0))
    assert c.current == 39.0                     # capped at the recorded range
    c.reset({"trim0": -2.0})
    c.step(obs(fc_t=0.0))
    assert c.current == sp0 - 2                  # restored integral
    c.reset({})
    c.step(obs(fc_t=0.0, ghi=400.0))
    assert c.current == 25.0                     # strong sun ahead: curve at the floor
    c.reset({})
    c.step(obs(room=None, fc=False, outdoor=5.0))  # no room, no forecast: sensor curve, no crash
    assert c.trim == 0.0 and 25.0 <= c.current <= 45.0
    c.reset({})
    for _ in range(600):
        c.step(obs(room=21.0, fc_t=0.0))
    assert c.trim > 0                            # cold room shifts the curve up
    c.reset({})
    for _ in range(600):
        c.step(obs(room=21.0, age=1000.0))
    assert c.trim == 0.0                         # stale room: integral frozen
    c.reset({})
    c.step(obs(fc_t=0.0, ghi=None, local_hour=2.0, time=datetime(2026, 4, 1, tzinfo=timezone.utc)))
    sp_clim = c.current
    c.reset({"clim": False})
    c.step(obs(fc_t=0.0, ghi=None, local_hour=2.0, time=datetime(2026, 4, 1, tzinfo=timezone.utc)))
    assert sp_clim < c.current                   # no irradiance in the forecast: April climatology lowers the water
    c.reset({})
    c.step(obs(fc=False, link_ok=False, outdoor=-20.0, local_hour=2.0))
    assert c.t_meas == -20.0 and c.current > sp0  # blind start seeds the stale sensor, not 0 degC
    c.reset({})
    out = c.step(obs(heating_enabled=False, restart_delta=4.0))
    assert out.heating_enabled is True and out.restart_delta == 5.0
    print("wc_low self-check ok")
