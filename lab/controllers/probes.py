"""Probe controllers that try to game the metrics or stress the plant model (stdlib only).

Not candidates. lab/sim/validate_sim.py (`review`) runs them to check that the storage
correction, the comfort normalisation, the start cost and the assumption flags catch what
review round 1 found. Each is a thin wrapper around the reference controller or a fixed pattern.
"""
from __future__ import annotations

from dataclasses import replace

from lab.controllers.reference import ReferenceController
from lab.sim.interface import Command


class LowBand:
    """Reference aimed at target - off (rides the bottom of a +-0.5 K band)."""
    name = "probe_low_band"

    def reset(self, params):
        self.off = float(params.get("off", 0.45))
        self.r = ReferenceController()
        self.r.reset(params)

    def step(self, obs):
        return self.r.step(replace(obs, target=obs.target - self.off))


class EndCoast:
    """Reference, but space heating disabled for the last `hours` of the window."""
    name = "probe_end_coast"

    def reset(self, params):
        self.hours = float(params.get("hours", 18))
        self.total = int(params.get("total_min", 7 * 1440))
        self.r = ReferenceController()
        self.r.reset(params)

    def step(self, obs):
        if obs.minute >= self.total - self.hours * 60:
            return Command(heating_enabled=False) if obs.heating_enabled else Command()
        return self.r.step(obs)


class EndCoastSetpoint:
    """Reference, but the setpoint is written to 20 degC for the last `hours` (no mode toggle)."""
    name = "probe_end_coast_sp"

    def reset(self, params):
        self.hours = float(params.get("hours", 18))
        self.total = int(params.get("total_min", 7 * 1440))
        self.r = ReferenceController()
        self.r.reset(params)

    def step(self, obs):
        if obs.minute >= self.total - self.hours * 60:
            return Command(setpoint=20.0) if obs.setpoint != 20.0 else Command()
        return self.r.step(obs)


class Flapper:
    """Setpoint 55 / 20 alternating every `period` minutes."""
    name = "probe_flapper"

    def reset(self, params):
        self.period = int(params.get("period", 1))

    def step(self, obs):
        return Command(setpoint=55.0 if (obs.minute // self.period) % 2 == 0 else 20.0, heating_enabled=True)


class BangBang:
    """Room thermostat through setpoint writes: `hi` when cold, 20 when warm."""
    name = "probe_bangbang"

    def reset(self, params):
        self.hi = float(params.get("hi", 55))
        self.h = float(params.get("hyst", 0.3))
        self.on = True
        self.delta = params.get("restart_delta")

    def step(self, obs):
        if obs.room is not None:
            if obs.room <= obs.target - self.h / 2:
                self.on = True
            elif obs.room >= obs.target + self.h / 2:
                self.on = False
        c = dict(setpoint=self.hi if self.on else 20.0, heating_enabled=True)
        if self.delta is not None:
            c["restart_delta"] = float(self.delta)
        return Command(**c)


class RefDelta:
    """Reference with a fixed restart_delta and optional quiet mode."""
    name = "probe_ref_delta"

    def reset(self, params):
        self.d = params.get("restart_delta")
        self.q = params.get("quiet")
        self.r = ReferenceController()
        self.r.reset(params)

    def step(self, obs):
        c = self.r.step(obs)
        kw = dict(setpoint=c.setpoint, heating_enabled=c.heating_enabled)
        if self.d is not None:
            kw["restart_delta"] = float(self.d)
        if self.q is not None:
            kw["quiet"] = bool(self.q)
        return Command(**kw)


class Pulse:
    """Pulse heating: every `period` minutes write `hi` for a duty share, then 20; the duty is
    trimmed by the room error once an hour (the review's 'short_hard')."""
    name = "probe_pulse"

    def reset(self, params):
        self.period = int(params.get("period", 180))
        self.duty = float(params.get("duty", 0.4))
        self.hi = float(params.get("hi", 40))
        self.gain = float(params.get("gain", 0.05))
        self.i = 0.0

    def step(self, obs):
        if obs.room is not None and obs.minute % 60 == 0:
            self.i = min(max(self.i + self.gain * (obs.target - obs.room), -0.5), 0.6)
        d = min(max(self.duty + self.i, 0.05), 1.0)
        on = (obs.minute % self.period) < d * self.period
        return Command(setpoint=self.hi if on else 20.0, heating_enabled=True)


# ------------------------------------------------------------------------------------------
# review round 2 probes: realistic strategy shapes the second review used to show that the
# ranking traded comfort for energy (N2), that flat_load blocked any output-level strategy (N3)
# and that the start cost decided close calls (N4)
# ------------------------------------------------------------------------------------------

class WeatherComp:
    """Weather compensation on the forecast's next-6-hour mean with a slow room trim (the README
    example)."""

    name = "probe_wc"

    def reset(self, params):
        self.slope = float(params.get("slope", 0.37))
        self.off = float(params.get("off", 0.2))
        self.trim = 0.0

    def step(self, obs):
        if obs.minute % 30:
            return Command()
        t = sum(h["outdoor"] for h in obs.forecast[:6]) / 6
        if obs.room is not None:
            self.trim = min(max(self.trim + 0.15 * (obs.target - obs.room), -4.0), 4.0)
        sp = 22 + self.slope * (22 - t) + self.off + self.trim
        return Command(setpoint=round(min(max(sp, 25), 45)))


class LowSlow:
    """Long low-power runs: while on, setpoint = inlet + gap (minimum output); start by writing
    just enough to start, stop by writing 25 degC; room hysteresis +-h around target."""

    name = "probe_lowslow"

    def reset(self, params):
        self.on = True
        self.gap = float(params.get("gap", 3.0))
        self.h = float(params.get("hyst", 0.2))

    def step(self, obs):
        if obs.room is not None:
            if obs.room <= obs.target - self.h:
                self.on = True
            elif obs.room >= obs.target + self.h:
                self.on = False
        if obs.minute % 10:
            return Command()
        if not self.on:
            sp = 25.0
        elif obs.compressor_on:
            sp = round(obs.inlet + self.gap)
        else:
            sp = round(obs.inlet + 0.8 + 4.0)
        sp = min(max(sp, 25.0), 45.0)
        return Command(setpoint=sp) if sp != obs.setpoint else Command()
