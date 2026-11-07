"""Validation only: replays the recorded register values (stdlib only).

Needs a recorded scenario: the simulator passes `recorded_registers`, a list of
(epoch seconds, setpoint, restart_delta, heating_enabled, quiet) at every change of the
recorded unit registers. At each minute the controller asks for the values in force then.
"""
from __future__ import annotations

import bisect

from lab.sim.interface import Command, Observation


class ReplayRecorded:
    name = "replay_recorded"

    def reset(self, params: dict) -> None:
        regs = params.get("recorded_registers")
        if not regs:
            raise ValueError("replay_recorded needs a recorded scenario (no recorded_registers given)")
        self.regs = sorted(regs)
        self.times = [r[0] for r in self.regs]

    def step(self, obs: Observation) -> Command:
        i = bisect.bisect_right(self.times, obs.time.timestamp()) - 1
        if i < 0:
            return Command()
        _, sp, delta, enabled, quiet = self.regs[i]
        cmd = {}
        if sp is not None and obs.setpoint != sp:
            cmd["setpoint"] = sp
        if delta is not None and obs.restart_delta != delta:
            cmd["restart_delta"] = delta
        if enabled is not None and obs.heating_enabled != enabled:
            cmd["heating_enabled"] = enabled
        if quiet is not None and obs.quiet != quiet:
            cmd["quiet"] = quiet
        return Command(**cmd)


CONTROLLER = ReplayRecorded
