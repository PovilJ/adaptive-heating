"""Neutral reference controller, used for every scenario's warm-up (stdlib only).

Not a candidate: it exists so that every controller starts from the same, reasonably settled
house state. A weather curve sized from the house model's steady loads (supply about 29.8 degC at
0 degC outdoor, 37 at -20, 26 at +10) on the 24-hour mean of the unit's outdoor sensor, plus a
slow PI trim on the room thermometer. Whole-degree setpoints with 0.6 K hysteresis.

Review round 2 (N8): setpoints are clamped to 25-45 degC. 25 degC is the lowest setpoint ever
written to the real unit; the old 22 degC floor made the baseline itself rely on never-recorded
behaviour in mild weather. `ref_sp_min` overrides it.
"""
from __future__ import annotations

from lab.sim.interface import Command, Observation


class ReferenceController:
    name = "reference"

    def reset(self, params: dict) -> None:
        self.kp = float(params.get("ref_kp", 2.0))          # K of water per K of room error
        self.ki = float(params.get("ref_ki_per_h", 0.15))   # K of water per K of room error per hour
        self.i_lim = float(params.get("ref_i_limit", 5.0))
        self.offset = float(params.get("ref_target_offset", 0.0))  # aim at target + offset (tuned baseline)
        self.sp_min = float(params.get("ref_sp_min", 25.0))
        self.sp_max = float(params.get("ref_sp_max", 45.0))
        # review round 2 (N2): aim `ref_shift_k` warmer over 10-22 local time and as much cooler
        # otherwise (the comfort-for-energy trade that prices comfort in the ranking)
        self.shift = float(params.get("ref_shift_k", 0.0))
        self.integral = 0.0
        self.t_avg = None
        self.current = None

    def step(self, obs: Observation) -> Command:
        a = 1.0 / (24 * 60)
        self.t_avg = obs.outdoor if self.t_avg is None else self.t_avg + a * (obs.outdoor - self.t_avg)
        base = 22.0 + 0.37 * (22.0 - self.t_avg) + 0.2
        aim = obs.target + self.offset
        if self.shift:
            aim += self.shift if 10.0 <= obs.local_hour < 22.0 else -self.shift
        err = 0.0 if obs.room is None else aim - obs.room
        self.integral = min(max(self.integral + self.ki * err / 60.0, -self.i_lim), self.i_lim)
        want = min(max(base + self.kp * err + self.integral, self.sp_min), self.sp_max)
        if self.current is None or abs(want - self.current) >= 0.6:
            self.current = float(round(want))
        if obs.setpoint != self.current or not obs.heating_enabled:
            return Command(setpoint=self.current, heating_enabled=True)
        return Command()


CONTROLLER = ReferenceController
