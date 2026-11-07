"""Controller interface of the lab simulator (stdlib only).

A controller is any object with a `name`, a `reset(params)` and a `step(obs) -> Command`. The
simulator calls `step` once per simulated minute with what Home Assistant would show at that
moment, and applies the returned command to the unit for the minute that follows. Controllers
never see hidden plant states (slab temperature, true air temperature, heat output).

Conventions (see lab/README.md):
- `Observation.time` is the UTC start of the minute about to be simulated; every field shows the
  state reached at that instant (after the previous minute).
- A `Command` field left as None changes nothing. A field that changes the unit's register (after
  clamping to the real range and resolution) counts as one write.
- `forecast` is a tuple of 48 hourly dicts starting with the next full hour:
  {'time': datetime (UTC, end of the hour the values describe), 'outdoor': degC, 'rh': %,
   'ghi'/'dni'/'dhi': W/m2 (mean over the hour ending at 'time', Open-Meteo convention),
   'cloud': %}. It is the same object for every minute of an hour.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class Observation:
    time: datetime            # UTC, tz-aware; one call per simulated minute
    local_hour: float         # Europe/Vilnius clock hour 0-24 (for schedules)
    room: float | None        # living-room thermometer as Home Assistant sees it: 0.1 degC steps, last reported value
    room_age_min: float       # minutes since that value was last reported
    outdoor: float            # unit's outdoor sensor, degC
    outlet: float             # leaving water, degC
    inlet: float              # return water, degC
    setpoint: float           # leaving-water setpoint active on the unit, degC
    restart_delta: float      # restart hysteresis active on the unit, K
    quiet: bool
    heating_enabled: bool
    compressor_on: bool
    mode: str                 # 'heat' | 'dhw' | 'defrost' | 'idle' | 'off'
    electric_kw: float        # unit electricity now (metered outdoor unit, minute mean)
    energy_kwh: float         # cumulative unit electricity (metered)
    target: float             # room target, degC (22.0 default)
    forecast: tuple           # hourly dicts for the next 48 h: {'time','outdoor','rh','ghi','dni','dhi','cloud'}
    pv_kw: float | None       # PV production now, if known
    # additions (lab): the minute index since the controller took over, and whether the Modbus
    # link is down this minute (unit fields then repeat their last values and commands wait)
    minute: int = 0
    link_ok: bool = True


@dataclass(frozen=True)
class Command:
    setpoint: float | None = None        # new leaving-water setpoint; the simulator clamps to the unit's real range and resolution
    restart_delta: float | None = None   # new restart hysteresis within the real register range
    quiet: bool | None = None
    heating_enabled: bool | None = None  # space-heating mode on/off (unit stays available for hot water)


NO_CHANGE = Command()


class Controller(Protocol):
    name: str

    def reset(self, params: dict) -> None: ...

    def step(self, obs: Observation) -> Command: ...   # called every simulated minute; return Command() to change nothing
