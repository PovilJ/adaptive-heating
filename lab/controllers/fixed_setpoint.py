"""Baseline: one constant leaving-water setpoint (stdlib only).

params: setpoint (30 degC), restart_delta (unchanged when absent), quiet (unchanged when absent).
"""
from __future__ import annotations

from lab.sim.interface import Command, Observation


class FixedSetpoint:
    name = "fixed_setpoint"

    def reset(self, params: dict) -> None:
        self.sp = float(params.get("setpoint", 30.0))
        self.delta = params.get("restart_delta")
        self.quiet = params.get("quiet")

    def step(self, obs: Observation) -> Command:
        cmd = {}
        if obs.setpoint != self.sp:
            cmd["setpoint"] = self.sp
        if not obs.heating_enabled:
            cmd["heating_enabled"] = True
        if self.delta is not None and obs.restart_delta != float(self.delta):
            cmd["restart_delta"] = float(self.delta)
        if self.quiet is not None and obs.quiet != bool(self.quiet):
            cmd["quiet"] = bool(self.quiet)
        return Command(**cmd)


CONTROLLER = FixedSetpoint
