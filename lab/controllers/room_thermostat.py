"""Baseline: naive on/off room thermostat (stdlib only).

Space heating is switched on below target - hysteresis/2 and off above target + hysteresis/2
on the room thermometer; while on, the unit runs to a fixed 35 degC water setpoint. Hot water
stays available (heating_enabled only switches space heating).

params: water (35 degC), hysteresis (0.3 K).
"""
from __future__ import annotations

from lab.sim.interface import Command, Observation


class RoomThermostat:
    name = "room_thermostat"

    def reset(self, params: dict) -> None:
        self.water = float(params.get("water", 35.0))
        self.hyst = float(params.get("hysteresis", 0.3))
        self.on = None

    def step(self, obs: Observation) -> Command:
        if obs.room is not None:
            if obs.room <= obs.target - self.hyst / 2:
                self.on = True
            elif obs.room >= obs.target + self.hyst / 2:
                self.on = False
        if self.on is None:
            self.on = obs.heating_enabled
        cmd = {}
        if obs.setpoint != self.water:
            cmd["setpoint"] = self.water
        if obs.heating_enabled != self.on:
            cmd["heating_enabled"] = self.on
        return Command(**cmd)


CONTROLLER = RoomThermostat
