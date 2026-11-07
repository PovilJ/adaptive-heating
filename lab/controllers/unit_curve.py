"""Baseline: the Versati's own weather-compensation curve (stdlib only).

Water setpoint interpolated linearly between the unit's configured end points and clamped:
(lower ambient -20 degC -> upper water 40 degC) and (upper ambient +15 degC -> lower water
26 degC), i.e. 32 degC at 0 degC outdoor. Driven by the unit's own outdoor sensor, smoothed
over about an hour (the firmware's filtering is unknown), whole degrees with 0.6 K hysteresis.

params: at_lo (-20), at_hi (15), wt_hi (40), wt_lo (26), offset (0 K), restart_delta (unchanged
when absent), tau_min (60).
"""
from __future__ import annotations

from lab.sim.interface import Command, Observation


class UnitCurve:
    name = "unit_curve"

    def reset(self, params: dict) -> None:
        self.at_lo = float(params.get("at_lo", -20.0))
        self.at_hi = float(params.get("at_hi", 15.0))
        self.wt_hi = float(params.get("wt_hi", 40.0))
        self.wt_lo = float(params.get("wt_lo", 26.0))
        self.offset = float(params.get("offset", 0.0))
        self.delta = params.get("restart_delta")
        self.tau = float(params.get("tau_min", 60.0))
        self.t_f = None
        self.current = None

    def curve(self, t_out: float) -> float:
        t = min(max(t_out, self.at_lo), self.at_hi)
        f = (t - self.at_lo) / (self.at_hi - self.at_lo)
        return self.wt_hi + f * (self.wt_lo - self.wt_hi) + self.offset

    def step(self, obs: Observation) -> Command:
        self.t_f = obs.outdoor if self.t_f is None else self.t_f + (obs.outdoor - self.t_f) / self.tau
        want = self.curve(self.t_f)
        if self.current is None or abs(want - self.current) >= 0.6:
            self.current = float(round(want))
        cmd = {}
        if obs.setpoint != self.current:
            cmd["setpoint"] = self.current
        if not obs.heating_enabled:
            cmd["heating_enabled"] = True
        if self.delta is not None and obs.restart_delta != float(self.delta):
            cmd["restart_delta"] = float(self.delta)
        return Command(**cmd)


CONTROLLER = UnitCurve
