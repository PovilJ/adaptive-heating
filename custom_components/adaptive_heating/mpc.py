"""Predictive planner: a two-store house model and a search for the cheapest comfortable water schedule.

Pure Python, no Home Assistant imports. The coordinator supplies measurements
and forecasts; scripts/fit_house.py fits `House` to recorded history and
scripts/backtest.py replays controllers against it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import math

STEP_HOURS = 0.5
HORIZON_STEPS = 72  # 36 hours
# Fine decisions first, coarse later: 4 half-hours, then 1-, 2-, 3- and 6-hour blocks.
BLOCKS = (1, 1, 2, 2, 4, 4, 4, 6, 6, 6, 12, 12, 12)
assert sum(BLOCKS) == HORIZON_STEPS


@dataclass(frozen=True)
class House:
    """First-house fit (scripts/fit_house.py, January–October 2026). Units: °C, hours, kW.

    Three stores: the floor slab, the building (walls, furniture, air) and a
    quick "glow" of sun-warmed air that the thermometer sees and that fades.
    State is (slab, building, glow). The thermometer hangs in air between the
    warm floor and the walls: room = building + mix * (slab - building) + glow.
    """
    heat: float = 0.151        # slab °C per kWh of heat delivered
    release: float = 0.643     # slab cooling toward the building, 1/h
    warm: float = 0.200         # building warming from the slab, 1/h per °C of difference
    loss: float = 0.00654        # building loss to outdoors, 1/h per °C of difference
    sun_east: float = 2.25     # glow °C/h per kW/m² on an east, south and west wall
    sun_south: float = 1.35
    sun_west: float = 0.0
    sun_fade: float = 0.268     # glow decay, 1/h
    sun_keep: float = 0.21     # share of faded glow that stays in the building
    gains: float = 0.0        # people and appliances, °C/h
    mix: float = 0.0          # how much of the slab-building difference the room air shows
    emit: float = 0.8         # kW of heat per °C of water above the slab, beyond `dead`
    dead: float = 1.8         # °C of water above the slab that delivers nothing (thermostat hysteresis)
    q_max: float = 9.0        # kW
    q_min: float = 3.0        # kW; below this the compressor cycles
    cop_eta: float = 0.42     # fraction of the Carnot limit
    cop_lift: float = 8.0     # °C of exchanger temperature difference

    def cop(self, water: float, outdoor: float) -> float:
        return min(7.0, max(1.5, self.cop_eta * (water + 273.15) / max(5.0, water - outdoor + self.cop_lift)))

    def heat_kw(self, water: float, slab: float) -> float:
        return min(self.q_max, max(0.0, self.emit * (water - slab - self.dead)))

    def step(self, state: tuple, heat_kw: float, outdoor: float, sun: tuple, bias: float = 0.0,
             hours: float = STEP_HOURS) -> tuple:
        slab, building, glow = state
        fade = self.sun_fade * glow
        return (slab + hours * (self.heat * heat_kw - self.release * (slab - building)),
                building + hours * (self.warm * (slab - building) - self.loss * (building - outdoor)
                                    + self.sun_keep * fade + self.gains + bias),
                max(0.0, glow + hours * (self.sun_east * sun[0] + self.sun_south * sun[1] + self.sun_west * sun[2] - fade)))

    def room(self, state: tuple) -> float:
        return state[1] + self.mix * (state[0] - state[1]) + state[2]

    def resting(self, room: float, outdoor: float, glow: float = 0.0, slab: float | None = None) -> tuple:
        """State showing this room temperature: with the given slab, or else in balance with no sun."""
        if slab is None:
            excess = max(0.0, self.loss * (room - glow - outdoor) - self.gains) / (self.warm + self.mix * self.loss)
            return room - glow + (1 - self.mix) * excess, room - glow - self.mix * excess, glow
        return slab, (room - glow - self.mix * slab) / (1 - self.mix), glow


def sun_position(when: datetime, latitude: float, longitude: float) -> tuple[float, float]:
    """Elevation and azimuth (degrees, azimuth clockwise from north); NOAA low-accuracy formulas."""
    u = when.astimezone(timezone.utc)
    g = 2 * math.pi / 365 * (u.timetuple().tm_yday - 1 + (u.hour - 12) / 24)
    eq = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                   - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    dec = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
           + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    hour_angle = math.radians((u.hour * 60 + u.minute + u.second / 60 + eq + 4 * longitude) / 4 - 180)
    lat = math.radians(latitude)
    sin_el = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(hour_angle)
    elevation = math.asin(max(-1.0, min(1.0, sin_el)))
    azimuth = math.atan2(-math.sin(hour_angle) * math.cos(dec),
                         math.cos(lat) * math.sin(dec) - math.sin(lat) * math.cos(dec) * math.cos(hour_angle))
    return math.degrees(elevation), math.degrees(azimuth) % 360


def sunshine(when: datetime, latitude: float, longitude: float, cloud_percent: float | None) -> tuple:
    """kW/m² reaching an east, south and west wall and the horizontal sky, from sun geometry and cloud cover.

    The same construction is used for fitting and for planning, so its crude
    cloud law is absorbed into the fitted weights instead of biasing the plan.
    """
    elevation, azimuth = sun_position(when, latitude, longitude)
    if elevation <= 1:
        return 0.0, 0.0, 0.0, 0.0
    sin_el = math.sin(math.radians(elevation))
    beam = 0.95 * 0.7 ** ((1 / sin_el) ** 0.678)  # clear-sky direct normal, Meinel
    cloud = min(1.0, max(0.0, (50.0 if cloud_percent is None else cloud_percent) / 100))
    clear = 1 - 0.75 * cloud ** 3.4  # Kasten–Czeplak
    cos_el = math.cos(math.radians(elevation))
    wall = lambda facing: clear * beam * max(0.0, cos_el * math.cos(math.radians(azimuth - facing)))
    return wall(90), wall(180), wall(270), clear * beam * sin_el * 1.1


@dataclass(frozen=True)
class Comfort:
    target: float = 22.5
    night_floor: float = 21.5   # allowed from night_start until warm_by
    night_start: int = 22       # local hour
    warm_by: int = 7            # local hour
    day_margin: float = 0.0     # room may sit this far under target by day
    headroom: float = 0.5       # free heat storage above target
    minimum_water: float = 25.0
    maximum_water: float = 40.0
    water_step: float = 1.0
    cold_weight: float = 20.0   # kWh-equivalents per °C² hour below the band
    warm_weight: float = 1.5    # per °C² hour above it
    start_cost: float = 0.15    # kWh-equivalent per compressor start
    cycling_loss: float = 0.15  # extra electricity share when below minimum output
    sun_discount: float = 0.3   # electricity is this much cheaper under full sun (own PV)

    def floor(self, local_hour: float) -> float:
        night = (self.night_start <= local_hour or local_hour < self.warm_by) if self.night_start > self.warm_by \
            else self.night_start <= local_hour < self.warm_by
        return min(self.target - self.day_margin, self.night_floor) if night else self.target - self.day_margin


@dataclass(frozen=True)
class Step:
    outdoor: float
    sun: tuple
    floor: float
    ceiling: float
    price: float


def horizon(now: datetime, forecast: list[tuple[datetime, float, float | None]], comfort: Comfort,
            latitude: float, longitude: float, outdoor_now: float, local_offset_hours: float) -> list[Step]:
    """One Step per half hour. `forecast` rows are (time, outdoor °C, cloud %); the last row is held."""
    rows = sorted(forecast, key=lambda row: row[0])
    steps = []
    for index in range(HORIZON_STEPS):
        at = now + timedelta(hours=(index + 0.5) * STEP_HOURS)
        before = [row for row in rows if row[0] <= at]
        after = [row for row in rows if row[0] > at]
        if before and after:
            a, b = before[-1], after[0]
            share = (at - a[0]).total_seconds() / max(1.0, (b[0] - a[0]).total_seconds())
            outdoor = a[1] + (b[1] - a[1]) * share
            cloud = a[2] if share < 0.5 else b[2]
        elif after:  # before the first forecast hour: blend from the measured outdoor temperature
            outdoor, cloud = (outdoor_now + after[0][1]) / 2, after[0][2]
        else:
            outdoor, cloud = before[-1][1], before[-1][2]
        sun = sunshine(at, latitude, longitude, cloud)
        local_hour = (at.astimezone(timezone.utc).hour + at.minute / 60 + local_offset_hours) % 24
        steps.append(Step(outdoor, sun, comfort.floor(local_hour), comfort.target + comfort.headroom,
                          1 - comfort.sun_discount * min(1.0, sun[3] / 0.5)))
    return steps


def simulate(house: House, comfort: Comfort, steps: list[Step], waters: list[float], state: tuple,
             bias: float = 0.0, running: bool = False) -> tuple[float, list[float], float]:
    """Return (cost, room path, electricity kWh) for one water temperature per half hour."""
    cost = energy = 0.0
    path = []
    previous = waters[0]
    for step, water in zip(steps, waters):
        heat = house.heat_kw(water, state[0])
        if heat > 0:
            power = heat / house.cop(water, step.outdoor)
            if heat < house.q_min:
                power *= 1 + comfort.cycling_loss
            energy += power * STEP_HOURS
            cost += power * STEP_HOURS * step.price
            if not running:
                cost += comfort.start_cost
        running = heat > 0
        state = house.step(state, heat, step.outdoor, step.sun, bias)
        room = house.room(state)
        path.append(room)
        cold, warm = step.floor - room, room - step.ceiling
        if cold > 0:
            cost += comfort.cold_weight * cold * cold * STEP_HOURS
        elif warm > 0:
            cost += comfort.warm_weight * warm * warm * STEP_HOURS
        cost += 0.01 * abs(water - previous)  # no pointless setpoint chatter
        previous = water
    return cost, path, energy


def expand(levels: list[float]) -> list[float]:
    return [level for level, count in zip(levels, BLOCKS) for _ in range(count)]


@dataclass(frozen=True)
class Plan:
    water: float
    levels: list[float]
    waters: list[float]
    rooms: list[float]
    energy_kwh: float
    cost: float


def plan(house: House, comfort: Comfort, steps: list[Step], state: tuple, bias: float = 0.0,
         running: bool = False, seed: list[float] | None = None) -> Plan:
    """Coordinate search over block water temperatures; small enough to run every cycle."""
    count = int(round((comfort.maximum_water - comfort.minimum_water) / comfort.water_step))
    choices = [comfort.minimum_water + i * comfort.water_step for i in range(count + 1)]

    def score(levels):
        return simulate(house, comfort, steps, expand(levels), state, bias, running)[0]

    # Coordinate search cannot move heat between blocks in one move, so begin from both extremes:
    # no heating, and the water that would hold the target against the coldest forecast hour.
    coldest = min(step.outdoor for step in steps)
    hold = house.resting(comfort.target, coldest)[0] + house.dead + (
        house.loss * max(0.0, comfort.target - coldest) / house.heat / house.emit)
    hold = min(comfort.maximum_water, max(comfort.minimum_water, round(hold)))
    starts = [[comfort.minimum_water] * len(BLOCKS), [hold] * len(BLOCKS)]
    if seed and len(seed) == len(BLOCKS):
        starts.append([min(comfort.maximum_water, max(comfort.minimum_water, v)) for v in seed])
    best, best_cost = None, math.inf
    for levels in starts:
        levels = list(levels)
        current = score(levels)
        for _ in range(4):
            improved = False
            for index in range(len(BLOCKS)):
                for choice in choices:
                    if choice == levels[index]:
                        continue
                    trial = levels[:index] + [choice] + levels[index + 1:]
                    value = score(trial)
                    if value < current - 1e-9:
                        levels, current, improved = trial, value, True
            if not improved:
                break
        if current < best_cost:
            best, best_cost = levels, current
    waters = expand(best)
    cost, rooms, energy = simulate(house, comfort, steps, waters, state, bias, running)
    return Plan(best[0], best, waters, rooms, energy, cost)


@dataclass
class Estimate:
    """What the planner believes about heat it cannot measure: slab, sun glow and an unexplained drift."""
    slab: float | None = None
    glow: float = 0.0
    bias: float = 0.0
    room: float | None = None
    predicted: float | None = None
    at: float | None = None

    def state(self, house: House) -> tuple:
        return house.resting(self.room, 0.0, self.glow, self.slab)

    def update(self, house: House, now: float, room: float, outdoor: float, water: float | None,
               on_fraction: float, sun: tuple) -> None:
        """Advance with what the heat pump and the sky actually did, then correct toward the measured room."""
        if self.slab is None or self.at is None or self.room is None or not 0 < now - self.at <= 2 * 3600:
            if self.slab is None or self.at is None or now - self.at > 6 * 3600:
                self.slab, self.glow = house.resting(room, outdoor)[0], 0.0
            self.room, self.at, self.predicted = room, now, None
            return
        hours = (now - self.at) / 3600
        heat = house.heat_kw(water, self.slab) * min(1.0, max(0.0, on_fraction)) if water is not None else 0.0
        state = self.state(house)
        parts = max(1, round(hours / 0.25))
        for _ in range(parts):
            state = house.step(state, heat, outdoor, sun, self.bias, hours / parts)
        predicted = house.room(state)
        error = room - predicted
        # In daylight a surprise is mostly sun on the thermometer; in the dark it is the slab.
        sunny = sun[0] + sun[1] + sun[2] > 0.02
        self.glow = min(6.0, max(0.0, state[2] + (error if sunny else 0.0)))
        self.slab = min(45.0, max(room - 1.0, state[0] + (0.0 if sunny else error)))
        self.bias = min(0.3, max(-0.3, self.bias + 0.2 * error / max(hours, 0.25)))
        self.room, self.at, self.predicted = room, now, predicted


@dataclass
class Guard:
    """Safety net for a wrong model: a room left under its band gets hotter water each cycle until it is back."""
    boost: float = 0.0

    def update(self, room: float, floor: float) -> float:
        if room < floor - 0.2:
            self.boost = min(6.0, self.boost + 1.0)
        elif room >= floor:
            self.boost = max(0.0, self.boost - 1.0)
        return self.boost
