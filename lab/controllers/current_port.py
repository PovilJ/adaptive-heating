"""current_port: the production Home Assistant controller (adaptive_heating 0.5.3) in the lab.

A black-box port, not a new design: the predictive planner (mpc.py), its slab/glow/drift
estimator, the Guard and too-warm safety nets, the start/keep-running lifts, the one-hour run
hold, the rise/fall limiter, the 30-minute command cadence with 2-minute re-checks while paused,
the heating-curve fallback (engine.decide) when the forecast is missing, and the nightly house
refit (learn.py: heat loss and sun gains, plus the measured device values). Everything is driven
by the lab Observation only. Stdlib only.

Port notes and every simplification: docs/research/lab/controllers/current_port.md.
The plan search (`plan`) is the production coordinate search; it is evaluated with prefix caching
and an exact early exit (every cost term is non-negative), which returns the same plan as the
plain loop (checked by the self-test under __main__).
"""
from __future__ import annotations

from dataclasses import dataclass, replace, fields
from datetime import datetime, timedelta, timezone
import math

from lab.sim.interface import Command, Observation

# ======================================================================================
# mpc.py (0.5.3), unchanged logic
# ======================================================================================

STEP_HOURS = 0.5
HORIZON_STEPS = 72  # 36 hours
BLOCKS = (1, 1, 2, 2, 4, 4, 4, 6, 6, 6, 12, 12, 12)
assert sum(BLOCKS) == HORIZON_STEPS
BLOCK_START = tuple(sum(BLOCKS[:i]) for i in range(len(BLOCKS)))
IS_BLOCK_START = tuple(k in BLOCK_START for k in range(sum(BLOCKS)))
MIN_RUN_STEPS = 2


@dataclass(frozen=True)
class House:
    heat: float = 0.151
    release: float = 0.643
    warm: float = 0.200
    loss: float = 0.00654
    sun_east: float = 2.25
    sun_south: float = 1.35
    sun_west: float = 0.0
    sun_fade: float = 0.268
    sun_keep: float = 0.21
    gains: float = 0.0
    mix: float = 0.0
    emit: float = 0.8
    dead: float = 1.8
    q_max: float = 9.0
    q_min: float = 3.0
    idle_offset: float = 2.8
    restart_gap: float = 5.0
    cop_eta: float = 0.42
    cop_lift: float = 8.0

    def cop(self, water: float, outdoor: float) -> float:
        return min(7.0, max(1.5, self.cop_eta * (water + 273.15) / max(5.0, water - outdoor + self.cop_lift)))

    def starts(self, water: float, slab: float) -> bool:
        return water >= slab + self.idle_offset + self.restart_gap

    def heat_kw(self, water: float, slab: float) -> float:
        heat = self.emit * (water - slab - self.dead)
        return 0.0 if heat < 0.5 * self.q_min else min(self.q_max, heat)

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
        if slab is None:
            excess = max(0.0, self.loss * (room - glow - outdoor) - self.gains) / (self.warm + self.mix * self.loss)
            return room - glow + (1 - self.mix) * excess, room - glow - self.mix * excess, glow
        return slab, (room - glow - self.mix * slab) / (1 - self.mix), glow


def sun_position(when: datetime, latitude: float, longitude: float) -> tuple[float, float]:
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


def sunshine(when: datetime, latitude: float, longitude: float, cloud_percent: float | None,
             clearness: float | None = None) -> tuple:
    elevation, azimuth = sun_position(when, latitude, longitude)
    if elevation <= 1:
        return 0.0, 0.0, 0.0, 0.0
    sin_el = math.sin(math.radians(elevation))
    beam = 0.95 * 0.7 ** ((1 / sin_el) ** 0.678)
    cloud = min(1.0, max(0.0, (50.0 if cloud_percent is None else cloud_percent) / 100))
    clear = 1 - 0.75 * cloud ** 3.4 if clearness is None else clearness
    cos_el = math.cos(math.radians(elevation))
    wall = lambda facing: clear * beam * max(0.0, cos_el * math.cos(math.radians(azimuth - facing)))
    return wall(90), wall(180), wall(270), clear * beam * sin_el * 1.1


@dataclass(frozen=True)
class Comfort:
    target: float = 22.5
    night_floor: float = 21.5
    night_start: int = 22
    warm_by: int = 7
    day_margin: float = 0.0
    headroom: float = 0.3
    minimum_water: float = 25.0
    maximum_water: float = 40.0
    water_step: float = 1.0
    rise_step: float = 2.0
    fall_step: float = 1.0
    cold_weight: float = 60.0
    warm_weight: float = 4.0
    start_cost: float = 0.15
    cycling_loss: float = 0.15
    sun_discount: float = 0.3
    curve_slope: float = 0.45
    curve_offset: float = 3.0
    curve_allowance: float = 5.0

    def ceiling_water(self, outdoor: float) -> float:
        curve = self.target + self.curve_offset + self.curve_slope * max(0.0, self.target - outdoor) + self.curve_allowance
        return min(self.maximum_water, max(self.minimum_water, curve))

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
    max_water: float = math.inf


NOWCAST_STEPS = 6


def horizon(now: datetime, forecast: list, comfort: Comfort, latitude: float, longitude: float,
            outdoor_now: float, local_offset_hours: float, clearness_now: float | None = None) -> list:
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
        elif after:
            outdoor, cloud = (outdoor_now + after[0][1]) / 2, after[0][2]
        else:
            outdoor, cloud = before[-1][1], before[-1][2]
        sun = sunshine(at, latitude, longitude, cloud)
        if clearness_now is not None and index < NOWCAST_STEPS:
            share = 1 - index / NOWCAST_STEPS
            forecast_clear = 1 - 0.75 * min(1.0, max(0.0, (50.0 if cloud is None else cloud) / 100)) ** 3.4
            sun = sunshine(at, latitude, longitude, cloud, share * clearness_now + (1 - share) * forecast_clear)
        local_hour = (at.astimezone(timezone.utc).hour + at.minute / 60 + local_offset_hours) % 24
        steps.append(Step(outdoor, sun, comfort.floor(local_hour), comfort.target + comfort.headroom,
                          1 - comfort.sun_discount * min(1.0, sun[3] / 0.5), comfort.ceiling_water(outdoor)))
    return steps


def simulate(house: House, comfort: Comfort, steps: list, waters: list, state: tuple,
             bias: float = 0.0, running: bool = False, run_left: int = 0,
             setpoint: float | None = None) -> tuple:
    """Production simulate(), verbatim (used by the self-test and for the final plan)."""
    cost = energy = 0.0
    path = []
    previous = waters[0]
    for step, water in zip(steps, waters):
        if setpoint is not None:
            water = setpoint = min(setpoint + comfort.rise_step, max(setpoint - comfort.fall_step, water))
        heat = house.heat_kw(water, state[0])
        if not running and run_left <= 0 and not house.starts(water, state[0]):
            heat = 0.0
        if run_left > 0:
            heat = max(heat, house.q_min)
        elif heat > 0 and not running:
            run_left = MIN_RUN_STEPS
        run_left -= 1
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
            cost += comfort.warm_weight * warm * STEP_HOURS
        cost += 0.01 * abs(water - previous)
        cost += (0.001 if heat > 0 else 0.02) * (water - comfort.minimum_water)
        previous = water
    return cost, path, energy


def expand(levels: list) -> list:
    return [level for level, count in zip(levels, BLOCKS) for _ in range(count)]


@dataclass(frozen=True)
class Plan:
    water: float
    levels: list
    waters: list
    rooms: list
    energy_kwh: float
    cost: float


class _FastSim:
    """The same arithmetic as simulate(), in the same order, for the plan search.

    `run(waters, start, carry, limit)` continues from the cached carry at step `start`
    (state, cost, running, run_left, setpoint, previous) and stops early once the cost reaches
    `limit` (all cost increments are >= 0 when every water is >= minimum_water, which the caller
    checks). Returns (cost, carries at block starts) or (None, None) on early exit.
    """

    def __init__(self, house: House, comfort: Comfort, steps: list, state: tuple, bias: float,
                 running: bool, run_left: int, setpoint: float | None):
        self.h, self.c = house, comfort
        self.out = [s.outdoor for s in steps]
        self.sun = [s.sun for s in steps]
        self.floor = [s.floor for s in steps]
        self.ceil = [s.ceiling for s in steps]
        self.price = [s.price for s in steps]
        self.bias = bias
        self.init = (state, 0.0, running, run_left, setpoint, None)

    def run(self, waters, start, carry, limit):
        h, c = self.h, self.c
        (slab, building, glow), cost, running, run_left, setpoint, previous = carry
        if previous is None:
            previous = waters[0]
        rise, fall = c.rise_step, c.fall_step
        emit, dead, half_qmin, q_max, q_min = h.emit, h.dead, 0.5 * h.q_min, h.q_max, h.q_min
        gate = h.idle_offset + h.restart_gap
        eta, lift = h.cop_eta, h.cop_lift
        cyc = 1 + c.cycling_loss
        start_cost, cold_w, warm_w, wmin = c.start_cost, c.cold_weight, c.warm_weight, c.minimum_water
        hheat, release, warmk, loss = h.heat, h.release, h.warm, h.loss
        keep, gains, bias, fadek = h.sun_keep, h.gains, self.bias, h.sun_fade
        se, ss, sw, mix = h.sun_east, h.sun_south, h.sun_west, h.mix
        out, sun, floor, ceil, price = self.out, self.sun, self.floor, self.ceil, self.price
        carries = {}
        is_start = IS_BLOCK_START
        hours = STEP_HOURS
        for k in range(start, HORIZON_STEPS):
            if is_start[k]:
                carries[k] = ((slab, building, glow), cost, running, run_left, setpoint, previous)
            water = waters[k]
            if setpoint is not None:
                lo = setpoint - fall
                if water < lo:
                    water = lo
                hi = setpoint + rise
                if hi < water:
                    water = hi
                setpoint = water
            heat = emit * (water - slab - dead)
            if heat < half_qmin:
                heat = 0.0
            elif heat > q_max:
                heat = q_max
            if not running and run_left <= 0 and not (water >= slab + gate):
                heat = 0.0
            if run_left > 0:
                if heat < q_min:
                    heat = q_min
            elif heat > 0 and not running:
                run_left = MIN_RUN_STEPS
            run_left -= 1
            o = out[k]
            if heat > 0:
                d = water - o + lift
                if d < 5.0:
                    d = 5.0
                cop = eta * (water + 273.15) / d
                if cop < 1.5:
                    cop = 1.5
                if cop > 7.0:
                    cop = 7.0
                power = heat / cop
                if heat < q_min:
                    power *= cyc
                cost += power * hours * price[k]
                if not running:
                    cost += start_cost
                running = True
                cost_extra = 0.001
            else:
                running = False
                cost_extra = 0.02
            fade = fadek * glow
            s = sun[k]
            sb = slab - building
            slab, building, glow = (
                slab + hours * (hheat * heat - release * sb),
                building + hours * (warmk * sb - loss * (building - o) + keep * fade + gains + bias),
                glow + hours * (se * s[0] + ss * s[1] + sw * s[2] - fade))
            if glow < 0.0:
                glow = 0.0
            room = building + mix * (slab - building) + glow
            cold = floor[k] - room
            if cold > 0:
                cost += cold_w * cold * cold * hours
            else:
                warm = room - ceil[k]
                if warm > 0:
                    cost += warm_w * warm * hours
            dw = water - previous
            cost += 0.01 * (dw if dw >= 0 else -dw)
            cost += cost_extra * (water - wmin)
            previous = water
            if cost >= limit:
                return None, None
        return cost, carries


def plan(house: House, comfort: Comfort, steps: list, state: tuple, bias: float = 0.0,
         running: bool = False, seed: list | None = None, run_left: int = 0,
         setpoint: float | None = None, fast: bool = True) -> Plan:
    count = int(round((comfort.maximum_water - comfort.minimum_water) / comfort.water_step))
    choices = [comfort.minimum_water + i * comfort.water_step for i in range(count + 1)]
    caps, at = [], 0
    for size in BLOCKS:
        caps.append(min([s.max_water for s in steps[at:at + size]] or [math.inf]))
        at += size
    allowed = [[c for c in choices if c <= cap + 1e-9] or [comfort.minimum_water] for cap in caps]
    fit = lambda levels: [max(comfort.minimum_water, min(v, max(a))) for v, a in zip(levels, allowed)]

    coldest = min(step.outdoor for step in steps)
    hold = house.resting(comfort.target, coldest)[0] + house.dead + (
        house.loss * max(0.0, comfort.target - coldest) / house.heat / house.emit)
    hold = min(comfort.maximum_water, max(comfort.minimum_water, round(hold)))
    starts = [[comfort.minimum_water] * len(BLOCKS), fit([hold] * len(BLOCKS))]
    starts += [fit([comfort.minimum_water + d] * len(BLOCKS)) for d in (2, 4, 6, 8)]
    if seed and len(seed) == len(BLOCKS):
        starts.append(fit(seed))
    # Early exit is exact only if every simulated water stays >= minimum_water.
    fast = fast and (setpoint is None or setpoint >= comfort.minimum_water)
    best, best_cost = None, math.inf
    if fast:
        sim = _FastSim(house, comfort, steps, state, bias, running, run_left, setpoint)
        cache = {}  # levels -> exact cost, or a lower bound when the evaluation stopped early
        for levels in starts:
            levels = list(levels)
            current, carries = sim.run(expand(levels), 0, sim.init, math.inf)
            for _ in range(4):
                improved = False
                for index in range(len(BLOCKS)):
                    b0 = BLOCK_START[index]
                    for choice in allowed[index]:
                        if choice == levels[index]:
                            continue
                        trial = levels[:index] + [choice] + levels[index + 1:]
                        key = tuple(trial)
                        known = cache.get(key)
                        limit = current - 1e-9
                        if known is not None and known >= limit:
                            continue  # an exact cost or a lower bound already rules it out
                        value, cs = sim.run(expand(trial), b0, carries[b0], limit)
                        cache[key] = limit if value is None else value
                        if value is not None and value < current - 1e-9:
                            # carries before b0 are unchanged
                            merged = {k: v for k, v in carries.items() if k < b0}
                            merged.update(cs)
                            levels, current, improved, carries = trial, value, True, merged
                if not improved:
                    break
            if current < best_cost:
                best, best_cost = levels, current
    else:
        def score(levels):
            return simulate(house, comfort, steps, expand(levels), state, bias, running, run_left, setpoint)[0]
        for levels in starts:
            levels = list(levels)
            current = score(levels)
            for _ in range(4):
                improved = False
                for index in range(len(BLOCKS)):
                    for choice in allowed[index]:
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
    cost, rooms, energy = simulate(house, comfort, steps, waters, state, bias, running, run_left, setpoint)
    return Plan(best[0], best, waters, rooms, energy, cost)


@dataclass
class Estimate:
    slab: float | None = None
    glow: float = 0.0
    bias: float = 0.0
    room: float | None = None
    predicted: float | None = None
    at: float | None = None

    def state(self, house: House) -> tuple:
        return house.resting(self.room, 0.0, self.glow, self.slab)

    def update(self, house: House, now: float, room: float, outdoor: float, water: float | None,
               on_fraction: float, sun: tuple, measured_heat: float | None = None) -> None:
        if self.slab is None or self.at is None or self.room is None or not 0 < now - self.at <= 2 * 3600:
            if self.slab is None or self.at is None or now - self.at > 6 * 3600:
                self.slab, self.glow = house.resting(room, outdoor)[0], 0.0
            self.room, self.at, self.predicted = room, now, None
            return
        hours = (now - self.at) / 3600
        if measured_heat is not None:
            heat = measured_heat
        else:
            heat = house.heat_kw(water, self.slab) * min(1.0, max(0.0, on_fraction)) if water is not None else 0.0
        state = self.state(house)
        parts = max(1, round(hours / 0.25))
        for _ in range(parts):
            state = house.step(state, heat, outdoor, sun, self.bias, hours / parts)
        predicted = house.room(state)
        error = room - predicted
        drive = house.sun_east * sun[0] + house.sun_south * sun[1] + house.sun_west * sun[2]
        idle = heat < 0.5 * house.q_min
        self.glow = min(6.0, max(0.0, state[2] + (error if idle else min(error, 0.5 * drive * hours))))
        limit = 0.6 * max(hours, 0.25)
        move = max(-limit, min(limit, error - (self.glow - state[2])))
        self.slab = min(45.0, max(room - (3.0 if idle else 1.0), state[0] + (min(0.0, move) if idle else move)))
        rate = max(-0.5, min(0.5, error / max(hours, 0.25)))
        self.bias = min(0.05, max(-0.05, self.bias + 0.04 * rate * min(hours, 0.5)))
        self.room, self.at, self.predicted = room, now, predicted


@dataclass
class Guard:
    boost: float = 0.0

    def update(self, room: float, floor: float, predicted: float | None = None) -> float:
        if room < floor - 0.2 and (predicted is None or room < predicted - 0.15):
            self.boost = min(6.0, self.boost + 1.0)
        elif room >= floor:
            self.boost = max(0.0, self.boost - 1.0)
        return self.boost


def too_warm(room: float, ceiling: float) -> bool:
    return room > ceiling + 0.2


def start_level(water: float, wants_start: bool, outlet: float | None, gap: float) -> float:
    if not wants_start or outlet is None:
        return water
    return max(water, math.ceil(outlet + gap))


def keep_running(water: float, wants_heat: bool, return_water: float | None, margin: float = 1.5) -> float:
    if not wants_heat or return_water is None:
        return water
    return max(water, math.ceil(return_water + margin))


# ======================================================================================
# engine.py (0.5.3): the heating-curve fallback, room trend, recovery assistance, limiter
# ======================================================================================

def finite(value) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def clamp(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


@dataclass
class Settings:
    target: float = 22.0
    minimum_water: float = 25.0
    maximum_water: float = 40.0
    comfort_band: float = 0.3
    curve_slope: float = 0.45
    curve_offset: float = 3.0
    room_feedback: float = 2.0
    thermal_response_hours: float = 3.0
    rise_per_hour: float = 4.0
    fall_per_hour: float = 2.0
    control_minutes: int = 30
    stale_minutes: int = 120


def cooling_trend(history: list) -> float | None:
    if len(history) < 7:
        return None
    span = history[-1][0] - history[0][0]
    if not 1800 <= span <= 3600 or any(not 0 < b[0] - a[0] <= 600 for a, b in zip(history, history[1:])):
        return None
    hours = [(t - history[0][0]) / 3600 for t, _ in history]
    mean_time = sum(hours) / len(hours)
    mean_room = sum(v for _, v in history) / len(history)
    variance = sum((t - mean_time) ** 2 for t in hours)
    return -sum((t - mean_time) * (v - mean_room) for t, (_, v) in zip(hours, history)) / variance


@dataclass
class Recovery:
    since: float | None = None
    last_time: float | None = None
    boost: float = 0.0

    def update(self, now: float, indoor, target: float, cooling_rate, settings: Settings, *, enabled: bool) -> float:
        elapsed = now - self.last_time if self.last_time is not None else 0
        if (not enabled or finite(cooling_rate) is None or finite(indoor) is None
                or elapsed < 0 or elapsed > 600 or indoor >= target):
            self.since, self.boost = None, 0.0
        elif indoor < target - 0.1 and cooling_rate >= -0.05:
            self.since = now if self.since is None else self.since
            overtime = now - self.since - settings.thermal_response_hours * 3600
            if overtime >= 0:
                steps = 1 + math.floor(overtime / (settings.control_minutes * 60))
                self.boost = max(self.boost, min(2.0, 0.5 * steps))
        else:
            self.since = None
            self.boost = max(0.0, self.boost - max(0, elapsed) / 3600)
        self.last_time = now
        return self.boost


def decide(settings: Settings, indoor: float, outdoor: float, forecasts: list, *,
           actual_setpoint: float | None = None, measured_cooling_rate: float | None = None,
           recovery_boost: float = 0.0) -> float:
    """engine.decide with an unusable empirical Model (the only case in which its result is used:
    the predictive plan replaces it whenever a forecast exists). Solar preheat is off (default)."""
    forecasts = [finite(v) for v in forecasts[:12]]
    if any(v is None or not -70 <= v <= 60 for v in forecasts):
        forecasts = []
    target = settings.target
    cooling = max(0.0, measured_cooling_rate) if finite(measured_cooling_rate) is not None else 0.0
    compensation = min(2.0, settings.room_feedback * cooling * settings.thermal_response_hours)
    boost = clamp(recovery_boost, 0, 2) if finite(recovery_boost) is not None else 0.0
    planning_outdoor = outdoor
    weather_curve = target + settings.curve_offset + settings.curve_slope * max(0, target - outdoor)
    start = actual_setpoint if finite(actual_setpoint) is not None else weather_curve
    for hour, (first, second) in enumerate(zip(forecasts, forecasts[1:]), start=1):
        future = max(first, second)
        future_water = clamp(target + settings.curve_offset + settings.curve_slope * max(0, target - future)
                             + settings.room_feedback * (target - indoor) + compensation + boost,
                             settings.minimum_water, settings.maximum_water)
        lead = settings.thermal_response_hours + max(0, future_water - start) / settings.rise_per_hour
        lead += settings.control_minutes / 60
        if hour <= lead:
            planning_outdoor = min(planning_outdoor, future)
    weather_curve = target + settings.curve_offset + settings.curve_slope * max(0, target - planning_outdoor)
    base = clamp(weather_curve + settings.room_feedback * (target - indoor) + compensation + boost,
                 settings.minimum_water, settings.maximum_water)
    return round(base, 2)


def limited_output(proposed, current, minimum, maximum, step, device_origin, elapsed_hours,
                   rise_per_hour, fall_per_hour):
    values = (proposed, current, minimum, maximum, step, device_origin, elapsed_hours, rise_per_hour, fall_per_hour)
    if any(finite(v) is None for v in values) or step <= 0 or minimum > maximum:
        return None
    if not minimum <= current <= maximum or elapsed_hours < 0:
        return None
    lower = max(minimum, current - fall_per_hour * elapsed_hours)
    upper = min(maximum, current + rise_per_hour * elapsed_hours)
    first = math.ceil((lower - device_origin) / step - 1e-8)
    last = math.floor((upper - device_origin) / step + 1e-8)
    if first > last:
        return None
    index = int(clamp(round((proposed - device_origin) / step), first, last))
    return round(device_origin + index * step, 6)


# ======================================================================================
# learn.py (0.5.3): half-hour log and the nightly refit
# ======================================================================================

KEEP_DAYS = 28
HOLDOUT_HOURS = 48
STANDBY_KW = 0.04
MIN_STEP_MINUTES = 29.5
MAX_STEP_MINUTES = 45
MIN_FIT_ROWS = 144
MIN_IMPROVEMENT = 0.97
LOW = (0.05, 2, 0.2, 2, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0, 0.0)
HIGH = (0.5, 80, 12.0, 150, 30, 30, 30, 2.0, 1.0, 1.5, 0.9)
FREE = (0, 4, 5, 6)
PRIOR_WIDTH = (1.5, 1.5, 1.5, 1.5, 3, 3, 3, 1.5, 1.5, 1.5, 1.5)
PRIOR_WEIGHT = 0.1


@dataclass
class Row:
    t: float
    room: float
    outdoor: float
    heat: float | None
    hours: float
    cloud: float | None
    pv: float | None
    setpoint: float | None
    slab: float | None
    outlet: float | None
    duty: float | None


class Log:
    def __init__(self):
        self.rows: list = []
        self.open: dict | None = None

    def add(self, *, now, room, outdoor, energy_kwh, cloud, pv_ratio, setpoint, slab, outlet, duty,
            floor_heat, cop_water, house: House) -> bool:
        current = self.open
        if current is not None:
            elapsed = now - current["t"]
            if elapsed < 0 or elapsed > MAX_STEP_MINUTES * 60:
                current = self.open = None
            else:
                current["clean"] = current["clean"] and floor_heat
                if duty is not None and current["duty"] is not None:
                    current["duty"] += duty * (elapsed - current["seen"])
                else:
                    current["duty"] = None
                current["seen"] = elapsed
        if current is not None and now - current["t"] < MIN_STEP_MINUTES * 60:
            return False
        closed = False
        if current is not None:
            hours = (now - current["t"]) / 3600
            heat = None
            if (current["clean"] and current["energy"] is not None and energy_kwh is not None
                    and 0 <= energy_kwh - current["energy"] < 20 * hours):
                electric = max(0.0, (energy_kwh - current["energy"]) / hours - STANDBY_KW)
                water = current["cop_water"] if current["cop_water"] is not None else current["room"] + 5
                heat = electric * house.cop(water, current["outdoor"])
            duty_share = current["duty"] / (now - current["t"]) if current["duty"] is not None else None
            self.rows.append(Row(current["t"], current["room"], current["outdoor"], heat, hours, current["cloud"],
                                 current["pv"], current["setpoint"], current["slab"], current["outlet"], duty_share))
            cut = now - KEEP_DAYS * 86400
            if self.rows and self.rows[0].t < cut:
                self.rows = [r for r in self.rows if r.t >= cut]
            closed = True
        if room is None or outdoor is None:
            self.open = None
            return closed
        self.open = {"t": now, "room": room, "outdoor": outdoor, "energy": energy_kwh, "cloud": cloud, "pv": pv_ratio,
                     "setpoint": setpoint, "slab": slab, "outlet": outlet, "cop_water": cop_water,
                     "clean": floor_heat, "duty": 0.0 if duty is not None else None, "seen": 0.0}
        return closed


def pv_scale(rows: list) -> float | None:
    ratios = sorted(r.pv for r in rows if r.pv is not None and r.pv > 0)
    if len(ratios) < 40:
        return None
    return ratios[int(len(ratios) * 0.9)]


def clearness_of(pv_ratio, scale):
    if pv_ratio is None or not scale:
        return None
    return min(1.1, max(0.0, pv_ratio / scale))


def logit(value, low, high):
    span = high - low
    value = min(high - 1e-2 * span, max(low + 1e-2 * span, value))
    return math.log((value - low) / (high - value))


def unlogit(v, low, high):
    return low + (high - low) / (1 + math.exp(-v))


def physical_of(house: House) -> list:
    building = 1 / house.heat * house.release / house.warm
    couple = house.release / house.heat
    return [house.loss * building, 1 / house.heat, couple, building, house.sun_east, house.sun_south,
            house.sun_west, house.sun_fade, house.sun_keep, house.gains * building, house.mix]


def house_of(values, base: House) -> House:
    ua, slab, couple, building, east, south, west, fade, keep, gains, mix = values
    return replace(base, heat=1 / slab, release=couple / slab, warm=couple / building, loss=ua / building,
                   sun_east=east, sun_south=south, sun_west=west, sun_fade=fade, sun_keep=keep,
                   gains=gains / building, mix=mix)


def runs_of(rows: list, place, scale) -> list:
    out, run = [], []
    for row in rows:
        middle = datetime.fromtimestamp(row.t + row.hours * 1800, timezone.utc)
        sun = sunshine(middle, *place, row.cloud, clearness_of(row.pv, scale))
        item = (row.t, row.room, row.heat, row.outdoor, sun, row.hours)
        if run:
            contiguous = abs(row.t - (run[-1][0] + run[-1][5] * 3600)) <= 120
            if not contiguous or run[-1][2] is None:
                out.append(run)
                run = []
            elif row.t - run[0][0] >= 86400:
                out.append(run + [item])
                run = []
        run.append(item)
    out.append(run)
    return [r for r in out if sum(1 for item in r[:-1] if item[2] is not None) >= 6]


def fit_error(house: House, runs: list) -> float:
    total = count = 0.0
    slab = glow = None
    previous_end = None
    for run in runs:
        if slab is None or previous_end is None or run[0][0] - previous_end > 3600:
            slab, glow = house.resting(run[0][1], run[0][3])[0], 0.0
        state = house.resting(run[0][1], 0.0, glow, slab)
        for item, nxt in zip(run, run[1:]):
            at, _, heat, outdoor, sun, hours = item
            if heat is None:
                break
            parts = max(1, round(hours / STEP_HOURS))
            for _ in range(parts):
                state = house.step(state, heat, outdoor, sun, 0.0, hours / parts)
            miss = house.room(state) - nxt[1]
            total += miss * miss if abs(miss) < 1 else 2 * abs(miss) - 1
            count += 1
        slab, glow = state[0], state[2]
        previous_end = run[-1][0]
    return total / count if count else math.inf


def nelder_mead(f, x, scale, rounds=4000, tolerance=1e-9):
    n = len(x)
    simplex = [list(x)] + [[v + (scale[i] if i == j else 0) for i, v in enumerate(x)] for j in range(n)]
    values = [f(p) for p in simplex]
    for _ in range(rounds):
        order = sorted(range(n + 1), key=values.__getitem__)
        simplex, values = [simplex[i] for i in order], [values[i] for i in order]
        if values[-1] - values[0] < tolerance:
            break
        centre = [sum(p[i] for p in simplex[:-1]) / n for i in range(n)]
        point = lambda t: [c + t * (c - w) for c, w in zip(centre, simplex[-1])]
        reflected = point(1); fr = f(reflected)
        if fr < values[0]:
            expanded = point(2); fe = f(expanded)
            simplex[-1], values[-1] = (expanded, fe) if fe < fr else (reflected, fr)
        elif fr < values[-2]:
            simplex[-1], values[-1] = reflected, fr
        else:
            contracted = point(-0.5); fc = f(contracted)
            if fc < values[-1]:
                simplex[-1], values[-1] = contracted, fc
            else:
                simplex = [simplex[0]] + [[(a + b) / 2 for a, b in zip(simplex[0], p)] for p in simplex[1:]]
                values = [values[0]] + [f(p) for p in simplex[1:]]
    return simplex[0], values[0]


def fit_house(house: House, runs, rounds=1500, free=FREE, weight=PRIOR_WEIGHT) -> House:
    values = physical_of(house)
    start = [logit(values[i], LOW[i], HIGH[i]) for i in free]

    def candidate(z):
        moved = list(values)
        for i, v in zip(free, z):
            moved[i] = unlogit(v, LOW[i], HIGH[i])
        return house_of(moved, house)

    prior = lambda z: weight * sum(((v - s) / PRIOR_WIDTH[i]) ** 2 for i, v, s in zip(free, z, start))
    z, _ = nelder_mead(lambda z: fit_error(candidate(z), runs) + prior(z), start, [0.5] * len(free), rounds)
    return candidate(z)


def fit_device(rows: list, house: House) -> dict:
    full = [(r.setpoint - r.slab, r.heat) for r in rows
            if r.heat is not None and r.duty is not None and r.duty >= 0.95 and r.setpoint is not None and r.slab is not None]
    found = {}
    if len(full) >= 20:
        xs, ys = [p[0] for p in full], [p[1] for p in full]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        sxx = sum((x - mx) ** 2 for x in xs)
        if sxx / len(xs) >= 1.0:
            slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
            if 0.2 <= slope <= 3.0:
                dead = mx - my / slope
                if 0.0 <= dead <= 8.0:
                    found.update(emit=slope, dead=dead)
        found["q_min"] = min(house.q_max, max(1.0, sorted(ys)[len(ys) // 10]))
    idle = sorted(r.outlet - r.slab for r in rows
                  if r.duty == 0 and r.outlet is not None and r.slab is not None and r.heat is not None)
    if len(idle) >= 20:
        found["idle_offset"] = min(8.0, max(0.0, idle[len(idle) // 2]))
    return found


def restart_gap(gaps: list, default: float) -> float:
    if len(gaps) < 3:
        return default
    return min(10.0, max(0.5, sorted(gaps)[min(1, len(gaps) - 1)]))


def refit(house: House, rows: list, place, now: float, start_gaps: list | None = None,
          rounds: int = 1500) -> tuple:
    """learn.refit. Returns (house, adopted, reason)."""
    usable = [r for r in rows if r.heat is not None]
    split = now - HOLDOUT_HOURS * 3600
    train = [r for r in rows if r.t < split]
    test = [r for r in rows if r.t >= split]
    holdout_rows = sum(1 for r in test if r.heat is not None)
    device = fit_device(rows, house)
    device["restart_gap"] = restart_gap(start_gaps or [], house.restart_gap)
    house = replace(house, **device)
    if len(usable) < MIN_FIT_ROWS or holdout_rows < 48:
        return house, False, "waiting"
    scale = pv_scale(rows)
    train_runs, test_runs = runs_of(train, place, scale), runs_of(test, place, scale)
    if not train_runs or not test_runs:
        return house, False, "broken"
    before = fit_error(house, test_runs)
    candidate = fit_house(house, train_runs, rounds)
    after = fit_error(candidate, test_runs)
    if not after <= before * MIN_IMPROVEMENT:
        return house, False, "kept"
    adopted = fit_house(candidate, runs_of(rows, place, scale), rounds // 2)
    if fit_error(adopted, test_runs) > after:
        adopted = candidate
    return adopted, True, "adopted"


# ======================================================================================
# coordinator.py (0.5.3) emulation: what HA sees, when it acts, what it writes
# ======================================================================================

# City-level location (rounded); only the sun geometry uses it.
PLACE = (54.7, 25.3)
DEVICE_MIN = 20.0   # the Versati water setpoint number entity: min 20, step 1
DEVICE_STEP = 1.0


class CurrentPort:
    name = "current_port"

    def reset(self, params: dict) -> None:
        g = lambda k, d: float(params.get(k, d))
        # The owner's live options per the project notes: rise 6 °C/h, fall 10 °C/h; the rest defaults.
        self.settings = Settings(rise_per_hour=g("rise_per_hour", 6.0), fall_per_hour=g("fall_per_hour", 10.0),
                                 minimum_water=g("minimum_water", 25.0), maximum_water=g("maximum_water", 40.0),
                                 curve_offset=g("curve_offset", 3.0), curve_slope=g("curve_slope", 0.45),
                                 stale_minutes=int(g("stale_minutes", 120)))
        # planner.DEFAULTS night_minimum is 20; the recorded replay fits "no night setback" (see doc)
        self.night_minimum = g("night_minimum", 22.0)
        self.quiet_start_hour = int(g("quiet_start_hour", 20))
        self.morning_hour = int(g("morning_hour", 9))
        self.learn = bool(int(g("learn", 1)))
        self.use_pv = bool(int(g("use_pv", 1)))
        self.fast = bool(int(g("fast", 1)))
        self.target_override = params.get("target")
        self.house = House()
        self.estimate = Estimate()
        self.guard = Guard()
        self.recovery = Recovery()
        self.log = Log()
        self.start_gaps: list = []
        self.pv_scale_value = None
        self.last_refit = None
        self.plan_seed = None
        self.too_warm_flag = False
        self.last_commanded = None
        self.last_command_time = None
        self.last_seen_output = None
        self.pending_deadline = None
        self.manual_hold = False
        self.last_cycle = None
        self.started = None
        self.next_refresh = None
        self.forecast_checked = None
        self.forecast_rows: list = []
        self.room_readings: list = []
        self.room_history: list = []
        self.previous = None            # last thermal-valid snapshot (time, floor_active)
        self.meter = None
        self.run_started = None
        self.hot_water_at = None
        self.in_hot_water = False
        # per-minute tracking of the floor-heating phase since the previous snapshot
        self.on_min = 0
        self.seen_min = 0
        self.phase_unknown = False
        self.last_phase = None
        self.last_room = None
        self.prev_outlet = None
        self.offset_hours = None
        # diagnostics
        self.stats = {"plans": 0, "refits": 0, "adopted": 0, "manual_hold": 0, "out_of_range_fix": 0,
                      "too_warm": 0, "guard": 0, "fallback": 0, "paused": 0}

    # -------------------------------------------------------------- per-minute event tracking
    def _phase(self, obs: Observation):
        if not obs.link_ok:
            return None
        return obs.mode == "heat"

    def _track_minute(self, obs: Observation) -> None:
        now = obs.time
        if self.started is None:
            self.started = now
        phase = self._phase(obs)
        # operating entity events
        if obs.link_ok:
            hot = obs.mode == "dhw"
            if hot or self.in_hot_water:
                self.hot_water_at = now
            self.in_hot_water = hot
            if obs.mode == "heat" and self.run_started is None:
                self.run_started = now
                if (self.prev_outlet is not None and not self._hot_recent(now, 20)
                        and 0 < obs.setpoint - self.prev_outlet <= 15):
                    self.start_gaps = (self.start_gaps + [round(obs.setpoint - self.prev_outlet, 2)])[-20:]
            elif obs.mode in ("idle", "dhw", "off"):
                self.run_started = None
            self.prev_outlet = obs.outlet
        # duty accumulation
        if phase is None:
            self.phase_unknown = True
        else:
            self.on_min += 1 if phase else 0
        self.seen_min += 1
        # room sensor state changes
        if obs.room is not None and obs.room != self.last_room:
            self.room_readings = (self.room_readings + [(now, obs.room)])[-20:]
        self.last_room = obs.room

    def _hot_recent(self, now, minutes=30):
        return self.hot_water_at is not None and 0 <= (now - self.hot_water_at).total_seconds() <= minutes * 60

    # -------------------------------------------------------------- snapshot
    def _room(self, now, current):
        start = now - timedelta(minutes=30)
        earlier = [v for t, v in self.room_readings if t <= start]
        points = ([(start, earlier[-1])] if earlier else []) + [(t, v) for t, v in self.room_readings if start < t <= now]
        if not points or points[-1][1] != current:
            return current
        spans = [((b[0] if b else now) - a[0]).total_seconds() for a, b in zip(points, points[1:] + [None])]
        total = sum(spans)
        return sum(v * span for (_, v), span in zip(points, spans)) / total if total > 0 else current

    def _snapshot(self, obs: Observation) -> dict:
        now = obs.time
        indoor = obs.room
        if indoor is not None and obs.room_age_min > self.settings.stale_minutes:
            indoor = None
        if indoor is not None:
            indoor = self._room(now, indoor)
        link = obs.link_ok
        outdoor = obs.outdoor if link else None
        inlet = obs.inlet if link else None
        outlet = obs.outlet if link else None
        water = (inlet + outlet) / 2 if inlet is not None and outlet is not None else None
        output = obs.setpoint if link else None
        mode = obs.mode if link else None
        active_heating = mode == "heat"
        idle = mode == "idle"
        hot_water = mode == "dhw"
        mode_enabled = bool(obs.heating_enabled) if link else False
        idle_heating = mode_enabled and idle
        compressor_active = True if active_heating or hot_water else False if idle else None
        floor_active = True if active_heating else False if idle or hot_water else None
        if mode == "defrost":
            floor_active = False
        # duty over the interval since the previous thermal-valid snapshot
        if self.previous is None or not isinstance(self.previous[1], bool):
            duty, uninterrupted = None, True
        elif self.phase_unknown or floor_active is None:
            duty, uninterrupted = None, False
        else:
            duty, uninterrupted = (self.on_min / self.seen_min if self.seen_min else None), True
        reason = ""
        if indoor is None or not 0 <= indoor <= 45:
            reason = "indoor"
        elif outdoor is None or not -70 <= outdoor <= 60:
            reason = "outdoor"
        elif output is None:
            reason = "output"
        elif not mode_enabled:
            reason = "heating mode"
        elif not active_heating and not idle_heating:
            reason = "state"
        if mode == "defrost" or not link:
            reason = reason or "defrost"
        valid = indoor is not None and 0 <= indoor <= 45 and outdoor is not None and -70 <= outdoor <= 60
        return {"time": now, "indoor": indoor, "outdoor": outdoor, "water": water, "output": output,
                "blocked": reason, "floor_heating_active": floor_active, "compressor_on_fraction": duty,
                "outlet": outlet, "inlet": inlet,
                "thermal_valid": valid and floor_active is not None and (not floor_active or water is not None)}

    # -------------------------------------------------------------- forecast (cached 30 min)
    def _forecasts(self, obs: Observation) -> list:
        now = obs.time
        if self.forecast_checked is None or (now - self.forecast_checked).total_seconds() >= 1800:
            self.forecast_checked = now
            self.forecast_rows = []
            for row in obs.forecast or ():
                when, value = row.get("time"), finite(row.get("outdoor"))
                if when is not None and value is not None and -70 <= value <= 60:
                    self.forecast_rows.append((when, value, finite(row.get("cloud"))))
        future = sorted((t, v) for t, v, _ in self.forecast_rows
                        if now - timedelta(minutes=30) <= t <= now + timedelta(hours=24))[:12]
        if len(future) < 2 or (future[0][0] - now).total_seconds() > 5400:
            return []
        if any(not 1800 <= (b[0] - a[0]).total_seconds() <= 5400 for a, b in zip(future, future[1:])):
            return []
        return [v for _, v in future[:12]]

    def _sky(self, now, obs: Observation):
        cloud = next((c for t, _, c in sorted(self.forecast_rows) if t >= now - timedelta(hours=1)), None)
        pv = obs.pv_kw * 1000 if (self.use_pv and obs.pv_kw is not None and obs.pv_kw >= 0) else None
        if pv is None:
            return cloud, None, None
        clear = sunshine(now, *PLACE, None, 1.0)[3]
        ratio = pv / clear if clear > 0.1 else None
        return cloud, ratio, clearness_of(ratio, self.pv_scale_value)

    # -------------------------------------------------------------- refresh
    def step(self, obs: Observation) -> Command:
        self._track_minute(obs)
        if self.next_refresh is not None and obs.minute < self.next_refresh:
            return Command()
        u = obs.time.astimezone(timezone.utc)   # local UTC offset now (follows DST, as dt_util.as_local)
        off = round(((obs.local_hour - (u.hour + u.minute / 60)) % 24) * 4) / 4
        self.offset_hours = off - 24 if off > 12 else off
        cmd, status = self._refresh(obs)
        self.next_refresh = obs.minute + (2 if status == "paused" else self.settings.control_minutes)
        if status == "paused":
            self.stats["paused"] += 1
        return cmd

    def _track_output(self, snapshot, now):
        output = snapshot["output"]
        if output is None:
            return
        if self.last_seen_output is not None and abs(output - self.last_seen_output) > 0.05:
            if self.last_commanded is None or abs(output - self.last_commanded) > 0.05:
                self.manual_hold = True
                self.stats["manual_hold"] += 1
        if self.pending_deadline:
            if abs(output - self.last_commanded) <= 0.05:
                self.pending_deadline = None
            elif now >= self.pending_deadline:
                self.manual_hold = True
                self.stats["manual_hold"] += 1
                self.pending_deadline = None
        self.last_seen_output = output

    def _refresh(self, obs: Observation):
        now = obs.time
        settings = self.settings
        if self.target_override is None:
            settings.target = obs.target
        snapshot = self._snapshot(obs)
        self._track_output(snapshot, now)
        forecasts = self._forecasts(obs)
        # planning_inputs: room history for the measured cooling trend (cold-night planner disabled)
        if snapshot["thermal_valid"]:
            self.room_history = [(t, v) for t, v in self.room_history if 0 <= (now - t).total_seconds() <= 3600]
            if self.room_history and (now - self.room_history[-1][0]).total_seconds() > 600:
                self.room_history = []
            if not self.room_history or (now - self.room_history[-1][0]).total_seconds() >= 240:
                self.room_history.append((now, snapshot["indoor"]))
        else:
            self.room_history = []
        rate = cooling_trend([(t.timestamp(), v) for t, v in self.room_history])
        blocked = snapshot["blocked"]
        if self.manual_hold:
            blocked = "manual"
        # engine.Model learning is skipped (its output is never used while the predictive plan runs)
        if snapshot["thermal_valid"]:
            self.previous = (now, snapshot["floor_heating_active"])
        else:
            self.previous = None
        self.on_min = self.seen_min = 0
        self.phase_unknown = False
        self._observe_house(now, snapshot, obs)
        self._record(now, snapshot, obs)
        recovery_allowed = not blocked
        recovery_boost = self.recovery.update(now.timestamp(), snapshot["indoor"], settings.target, rate, settings,
                                              enabled=recovery_allowed)
        if blocked:
            return Command(), "paused"
        proposed = decide(settings, snapshot["indoor"], snapshot["outdoor"], forecasts,
                          actual_setpoint=snapshot["output"],
                          measured_cooling_rate=rate if recovery_allowed else None, recovery_boost=recovery_boost)
        if (recovery_allowed and rate is not None and rate > 0.05
                and snapshot["indoor"] < settings.target - settings.comfort_band and proposed < snapshot["output"]):
            proposed = snapshot["output"]
        predictive = self._predictive_plan(now, snapshot, obs)
        if predictive is not None:
            proposed = predictive
        else:
            self.stats["fallback"] += 1
        limited = self._output_limit(proposed, snapshot["output"], now,
                                     fast_fall=predictive is not None and self.too_warm_flag)
        if limited is None:
            # Out-of-range setpoint (e.g. left by the warm-up controller): production pauses until the
            # owner corrects it. Emulate that one manual correction to the nearest allowed value.
            out = snapshot["output"]
            if out is not None and not settings.minimum_water <= out <= settings.maximum_water:
                self.stats["out_of_range_fix"] += 1
                fixed = clamp(out, settings.minimum_water, settings.maximum_water)
                self.last_commanded = fixed
                self.last_command_time = now
                self.pending_deadline = now + timedelta(minutes=2)
                self.last_cycle = now
                return Command(setpoint=fixed), "command_sent"
            return Command(), "paused"
        due = self.last_cycle is None or (now - self.last_cycle).total_seconds() >= settings.control_minutes * 60 - 60
        if not due:
            return Command(), "waiting"
        self.last_cycle = now
        if abs(limited - snapshot["output"]) < 0.05:
            return Command(), "maintaining"
        self.last_commanded = limited
        self.last_command_time = now
        self.pending_deadline = now + timedelta(minutes=2)
        return Command(setpoint=limited), "command_sent"

    def _output_limit(self, proposed, current, now, fast_fall=False):
        s = self.settings
        elapsed = (now - (self.last_command_time or self.started)).total_seconds() / 3600
        interval = s.control_minutes / 60
        elapsed = interval if elapsed >= interval - 1 / 60 else elapsed
        return limited_output(proposed, current, max(DEVICE_MIN, s.minimum_water), min(55.0, s.maximum_water),
                              DEVICE_STEP, DEVICE_MIN, elapsed, s.rise_per_hour,
                              1000.0 if fast_fall else s.fall_per_hour)

    def _observe_house(self, now, snapshot, obs):
        if not snapshot["thermal_valid"]:
            return
        cloud, _, clear = self._sky(now, obs)
        duty = snapshot["compressor_on_fraction"]
        if duty is None:
            duty = 1.0 if snapshot["floor_heating_active"] else 0.0
        energy = obs.energy_kwh if obs.link_ok else None
        measured = None
        if self.meter is not None and energy is not None and self.estimate.at is not None:
            began, used = self.meter
            hours = (now.timestamp() - began) / 3600
            if (abs(began - self.estimate.at) < 1 and 0.3 <= hours <= 2 and 0 <= energy - used < 20 * hours
                    and not self._hot_recent(now, hours * 60 + 5)):
                measured = max(0.0, (energy - used) / hours - STANDBY_KW) * self.house.cop(
                    snapshot["output"] if snapshot["output"] is not None else snapshot["indoor"] + 5, snapshot["outdoor"])
        before = self.estimate.at
        self.estimate.update(self.house, now.timestamp(), snapshot["indoor"], snapshot["outdoor"],
                             snapshot["output"], duty, sunshine(now, *PLACE, cloud, clear), measured)
        if self.estimate.at != before:
            self.meter = (self.estimate.at, energy) if energy is not None else None

    def _record(self, now, snapshot, obs):
        if obs.link_ok and obs.mode == "dhw":
            self.hot_water_at = now
        cloud, ratio, _ = self._sky(now, obs)
        floor_heat = snapshot["floor_heating_active"] is not None and not self._hot_recent(now, 35)
        self.log.add(now=now.timestamp(), room=snapshot["indoor"], outdoor=snapshot["outdoor"],
                     energy_kwh=obs.energy_kwh if obs.link_ok else None, cloud=cloud, pv_ratio=ratio,
                     setpoint=snapshot["output"], slab=self.estimate.slab, outlet=snapshot["outlet"],
                     duty=snapshot["compressor_on_fraction"], floor_heat=floor_heat, cop_water=snapshot["output"],
                     house=self.house)
        last = self.last_refit
        local_hour = int((obs.local_hour) % 24)
        due = (last is None or now.timestamp() - last >= 20 * 3600) and (last is None or local_hour == 3)
        if due:
            self.last_refit = now.timestamp()
            if self.learn:
                house, adopted, _ = refit(self.house, list(self.log.rows), PLACE, now.timestamp(),
                                          list(self.start_gaps))
                self.stats["refits"] += 1
                if adopted:
                    self.estimate.bias = 0.0
                    self.stats["adopted"] += 1
                self.house = house
            self.pv_scale_value = pv_scale(self.log.rows)

    def _predictive_plan(self, now, snapshot, obs):
        rows = [row for row in self.forecast_rows if row[0] >= now - timedelta(hours=1)]
        if self.estimate.slab is None or self.estimate.room is None or len(rows) < 12:
            return None
        s = self.settings
        comfort = Comfort(target=s.target, night_floor=min(s.target, self.night_minimum),
                          night_start=self.quiet_start_hour, warm_by=self.morning_hour,
                          minimum_water=s.minimum_water, maximum_water=s.maximum_water, water_step=1.0,
                          rise_step=s.rise_per_hour * STEP_HOURS, fall_step=s.fall_per_hour * STEP_HOURS,
                          curve_slope=s.curve_slope, curve_offset=s.curve_offset)
        steps = horizon(now, rows, comfort, *PLACE, snapshot["outdoor"], self.offset_hours, self._sky(now, obs)[2])
        minutes = ((now - self.run_started).total_seconds() / 60
                   if self.run_started is not None and snapshot["floor_heating_active"] else None)
        run_left = (math.ceil((MIN_RUN_STEPS * STEP_HOURS * 60 - minutes) / (STEP_HOURS * 60))
                    if minutes is not None and minutes < MIN_RUN_STEPS * STEP_HOURS * 60 else 0)
        p = plan(self.house, comfort, steps, self.estimate.state(self.house), self.estimate.bias,
                 bool(snapshot["floor_heating_active"]), self.plan_seed, run_left, snapshot["output"], fast=self.fast)
        self.stats["plans"] += 1
        self.plan_seed = p.levels
        boost = self.guard.update(snapshot["indoor"], steps[0].floor, self.estimate.predicted)
        if boost:
            self.stats["guard"] += 1
        delivers = self.house.heat_kw(p.water, self.estimate.slab) > 0
        running = bool(snapshot["floor_heating_active"])
        hot_loop = self._hot_recent(now)
        if running:
            wants_heat = boost > 0 or delivers
            held = keep_running(p.water + boost, wants_heat or run_left > 0, None if hot_loop else snapshot["inlet"])
        else:
            boosted = p.water + boost
            wants_heat = (self.house.heat_kw(boosted, self.estimate.slab) > 0
                          and self.house.starts(boosted, self.estimate.slab))
            held = start_level(boosted, wants_heat, None if hot_loop else snapshot["outlet"], self.house.restart_gap)
        if run_left > 0:
            held = max(held, snapshot["output"])
        warm = self.too_warm_flag = too_warm(snapshot["indoor"], steps[0].ceiling)
        if warm:
            self.stats["too_warm"] += 1
        return comfort.minimum_water if warm else min(comfort.maximum_water, held)


CONTROLLER = CurrentPort


if __name__ == "__main__":
    import random
    import time as _time

    # 1. The fast plan search returns exactly the production plan.
    rng = random.Random(1)
    house, now = House(), datetime(2026, 1, 10, 12, tzinfo=timezone.utc)
    for trial in range(6):
        comfort = Comfort(target=22.0, night_floor=20.0, night_start=20, warm_by=9, rise_step=3.0, fall_step=5.0)
        base = rng.uniform(-12, 8)
        rows = [(now + timedelta(hours=h + 1), base + 4 * math.sin(h / 4) + rng.gauss(0, 1), rng.uniform(0, 100))
                for h in range(48)]
        steps = horizon(now, rows, comfort, *PLACE, base, 2.0, rng.choice([None, 0.8]))
        state = house.resting(rng.uniform(21.0, 22.8), base)
        sp = float(rng.randint(25, 38))
        args = (house, comfort, steps, state, rng.uniform(-0.05, 0.05), rng.random() < 0.5, None,
                rng.choice([0, 1]), sp)
        t0 = _time.time(); slow = plan(*args, fast=False); t1 = _time.time(); quick = plan(*args, fast=True)
        t2 = _time.time()
        assert slow.levels == quick.levels and abs(slow.cost - quick.cost) < 1e-12, (slow.levels, quick.levels)
        print(f"plan {trial}: {quick.levels[:4]} slow {t1 - t0:.2f}s fast {t2 - t1:.2f}s")
    # 2. Limiter and lifts.
    assert limited_output(39, 30, 25, 40, 1, 20, 0.5, 6, 10) == 33
    assert limited_output(25, 30, 25, 40, 1, 20, 0.5, 6, 1000) == 25
    assert limited_output(30, 45, 25, 40, 1, 20, 0.5, 6, 10) is None
    assert start_level(28, True, 27.1, 5.0) == 33 and keep_running(25, True, 26.0) == 28
    assert too_warm(22.51, 22.3) and not too_warm(22.5, 22.3)
    print("self-check ok")
