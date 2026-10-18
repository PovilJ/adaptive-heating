"""The house learns itself: a half-hour log of what the heat pump and the house did, refitted daily.

Pure Python, no Home Assistant imports. The coordinator feeds `Log.add` every
cycle and runs `refit` in the executor once a day; scripts/fit_house.py uses
the same fit on exported history.

`mpc.House` holds the first house's values. They are only the starting point:
each day the model is refitted to the last four weeks, pulled toward the
values it already has, and adopted only when it forecasts the most recent two
days better than the current one. A different house therefore drifts to its
own values within days, and the first house follows its seasons.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, replace
from datetime import datetime, timedelta, timezone
import math

try:
    from . import mpc
except ImportError:  # loaded as a top-level module by the offline scripts
    import mpc

KEEP_DAYS = 28
HOLDOUT_HOURS = 48
STANDBY_KW = 0.04          # controller, pump and display while the compressor is off
MIN_STEP_MINUTES = 29.5    # one log row per control interval
MAX_STEP_MINUTES = 45      # a longer silence breaks the record
MIN_FIT_ROWS = 144         # three days of rows with measured heat
MIN_IMPROVEMENT = 0.97     # a new house must forecast the held-out days at least 3 % better

# Fitted as physical quantities, then converted: kW/°C lost outdoors, kWh/°C of slab,
# kW/°C slab-to-building, kWh/°C of building, sun glow °C/h per kW/m², glow fade 1/h,
# share of glow kept by the building, kW of gains, share of slab excess the thermometer sees.
PHYSICAL = ("ua", "slab", "couple", "building", "east", "south", "west", "fade", "keep", "gains", "mix")
LOW = (0.05, 2, 0.2, 2, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0, 0.0)
HIGH = (0.5, 80, 12.0, 150, 30, 30, 30, 2.0, 1.0, 1.5, 0.9)
# Ten days of October replayed (scripts/learning_replay.py): refitting all eleven
# values forecast the following two days worse than not learning (rms 0.44–0.60
# against 0.39 °C) because mild-weather data cannot tell slab from building.
# Heat loss and the sun on the east and south walls are what the data does
# pin down; learning those alone removed the model's +0.2 °C warm bias.
FREE = (0, 4, 5, 6)        # ua, east, south, west
PRIOR_WIDTH = (1.5, 1.5, 1.5, 1.5, 3, 3, 3, 1.5, 1.5, 1.5, 1.5)  # logit units; the sun is the least known
PRIOR_WEIGHT = 0.1         # in mean squared °C of forecast error


@dataclass
class Row:
    """One logged interval: the state at `t` and what happened until the next row."""
    t: float                  # epoch seconds
    room: float
    outdoor: float
    heat: float | None        # kW of space heat delivered over the interval; None when unknown or not the floor's
    hours: float              # length of the interval
    cloud: float | None       # forecast cloud % at t
    pv: float | None          # PV watts per kW/m² of clear-sky horizontal sun at t (None without PV or sun)
    setpoint: float | None
    slab: float | None        # the live estimate at t, for the emitter fit
    outlet: float | None
    duty: float | None        # share of the interval the compressor heated the floor

    def to_list(self) -> list:
        return [getattr(self, f.name) for f in fields(self)]

    @classmethod
    def from_list(cls, values: list) -> Row:
        return cls(*values)


@dataclass
class Log:
    """Rolling four weeks of rows, plus the interval still being measured."""
    rows: list = field(default_factory=list)
    open: dict | None = None

    def add(self, *, now: float, room: float | None, outdoor: float | None, energy_kwh: float | None,
            cloud: float | None, pv_ratio: float | None, setpoint: float | None, slab: float | None,
            outlet: float | None, duty: float | None, floor_heat: bool, cop_water: float | None,
            house: mpc.House) -> bool:
        """Record one cycle. Returns True when a row was closed.

        `floor_heat` False means the electricity of this cycle did not all go to
        the floor (hot water, AC, unknown operating state): the interval's heat
        becomes unknown, but the room and weather are still logged.
        """
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
            self.rows = [r for r in self.rows if r.t >= now - KEEP_DAYS * 86400]
            closed = True
        if room is None or outdoor is None:
            self.open = None
            return closed
        self.open = {"t": now, "room": room, "outdoor": outdoor, "energy": energy_kwh, "cloud": cloud, "pv": pv_ratio,
                     "setpoint": setpoint, "slab": slab, "outlet": outlet, "cop_water": cop_water,
                     "clean": floor_heat, "duty": 0.0 if duty is not None else None, "seen": 0.0}
        return closed

    def to_dict(self) -> dict:
        return {"rows": [r.to_list() for r in self.rows], "open": self.open}

    @classmethod
    def restore(cls, data: dict | None) -> Log:
        try:
            return cls([Row.from_list(r) for r in (data or {}).get("rows", [])], (data or {}).get("open"))
        except (TypeError, ValueError):
            return cls()


# ---------------------------------------------------------------- sunshine


def pv_scale(rows: list[Row]) -> float | None:
    """Watts of PV under a clear sky per kW/m² of clear-sky horizontal sun: a high quantile of what was seen."""
    ratios = sorted(r.pv for r in rows if r.pv is not None and r.pv > 0)
    if len(ratios) < 40:
        return None
    return ratios[int(len(ratios) * 0.9)]


def clearness(pv_ratio: float | None, scale: float | None) -> float | None:
    if pv_ratio is None or not scale:
        return None
    return min(1.1, max(0.0, pv_ratio / scale))


def sun_for(row: Row, place: tuple[float, float], scale: float | None) -> tuple:
    """Sunshine over the interval: measured by the panels where they exist, else the forecast's cloud."""
    middle = datetime.fromtimestamp(row.t + row.hours * 1800, timezone.utc)
    return mpc.sunshine(middle, *place, row.cloud, clearness(row.pv, scale))


# ---------------------------------------------------------------- fitting


def logit(value: float, low: float, high: float) -> float:
    span = high - low
    value = min(high - 1e-2 * span, max(low + 1e-2 * span, value))  # a value at its bound could never move
    return math.log((value - low) / (high - value))


def physical_of(house: mpc.House) -> list[float]:
    building = 1 / house.heat * house.release / house.warm  # kWh/°C: couple / warm, couple = release / heat
    couple = house.release / house.heat
    return [house.loss * building, 1 / house.heat, couple, building, house.sun_east, house.sun_south,
            house.sun_west, house.sun_fade, house.sun_keep, house.gains * building, house.mix]


def unlogit(v: float, low: float, high: float) -> float:
    return low + (high - low) / (1 + math.exp(-v))


def house_from(x: list[float], base: mpc.House) -> mpc.House:
    return house_of(map(unlogit, x, LOW, HIGH), base)


def house_of(values, base: mpc.House) -> mpc.House:
    ua, slab, couple, building, east, south, west, fade, keep, gains, mix = values
    return replace(base, heat=1 / slab, release=couple / slab, warm=couple / building, loss=ua / building,
                   sun_east=east, sun_south=south, sun_west=west, sun_fade=fade, sun_keep=keep,
                   gains=gains / building, mix=mix)


def x_of(house: mpc.House) -> list[float]:
    return [logit(v, low, high) for v, low, high in zip(physical_of(house), LOW, HIGH)]


def runs_of(rows: list[Row], place, scale) -> list[list[tuple]]:
    """Contiguous stretches with measured heat, cut at every 24 hours so the room is re-anchored daily.

    Each item is (t, room, heat kW, outdoor, sun, hours); the last item of a run only supplies its room.
    """
    out, run = [], []
    for row in rows:
        item = (row.t, row.room, row.heat, row.outdoor, sun_for(row, place, scale), row.hours)
        if run:
            contiguous = abs(row.t - (run[-1][0] + run[-1][5] * 3600)) <= 120
            if not contiguous or run[-1][2] is None:
                out.append(run)
                run = []
            elif row.t - run[0][0] >= 86400:
                out.append(run + [item])  # the new row closes the day's last step
                run = []
        run.append(item)
    out.append(run)
    return [r for r in out if sum(1 for item in r[:-1] if item[2] is not None) >= 6]


def error(house: mpc.House, runs: list[list[tuple]]) -> float:
    """Mean Huber error (°C²) of forecasting each next room reading from the measured heat and weather."""
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
            parts = max(1, round(hours / mpc.STEP_HOURS))
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


def fit_house(house: mpc.House, runs, rounds=1500, free=FREE, weight=PRIOR_WEIGHT) -> mpc.House:
    """Best house for these runs, pulled toward `house`: the data moves only what it can tell apart."""
    values = physical_of(house)
    start = [logit(values[i], LOW[i], HIGH[i]) for i in free]

    def candidate(z):  # only the free values move; the rest stay exactly as they were
        moved = list(values)
        for i, v in zip(free, z):
            moved[i] = unlogit(v, LOW[i], HIGH[i])
        return house_of(moved, house)

    prior = lambda z: weight * sum(((v - s) / PRIOR_WIDTH[i]) ** 2 for i, v, s in zip(free, z, start))
    z, _ = nelder_mead(lambda z: error(candidate(z), runs) + prior(z), start, [0.5] * len(free), rounds)
    return candidate(z)


# ---------------------------------------------------------------- the heat pump itself


def fit_device(rows: list[Row], house: mpc.House) -> dict:
    """Heat delivered against setpoint above the slab, the minimum output, and the outlet when idle.

    Only intervals the compressor heated throughout count for the emitter line;
    a fit needs a spread of setpoints and a positive slope, or the values stay.
    On the first house in October full runs gave 4.5–6 kW almost whatever the
    setpoint, so the line was rejected and only the minimum output was learned.
    """
    full = [(r.setpoint - r.slab, r.heat) for r in rows
            if r.heat is not None and r.duty is not None and r.duty >= 0.95 and r.setpoint is not None and r.slab is not None]
    found = {}
    if len(full) >= 20:
        xs, ys = [p[0] for p in full], [p[1] for p in full]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        sxx = sum((x - mx) ** 2 for x in xs)
        if sxx / len(xs) >= 1.0:  # at least a degree of spread
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


def restart_gap(gaps: list[float], default: float) -> float:
    """How far the setpoint must sit above the outlet before an idle compressor starts.

    Each start the coordinator saw records setpoint − outlet just before it.
    Setpoints rise in steps of a degree or two, so the smallest gaps that still
    started sit just above the unit's own threshold.
    """
    if len(gaps) < 3:
        return default
    return min(10.0, max(0.5, sorted(gaps)[min(1, len(gaps) - 1)]))


# ---------------------------------------------------------------- the daily refit


@dataclass
class Report:
    at: float
    rows: int
    holdout_rows: int
    error_before: float | None = None    # held-out forecast error of the house in use, rms °C
    error_after: float | None = None     # of the candidate
    adopted: bool = False
    reason: str = ""
    device: dict = field(default_factory=dict)


def refit(house: mpc.House, rows: list[Row], place: tuple[float, float], now: float,
          start_gaps: list[float] | None = None, rounds: int = 1500) -> tuple[mpc.House, Report]:
    """Daily learning. The heat pump's own values are measured directly; the house is refitted.

    The house is fitted on all but the last two days and kept only if it
    forecasts those two days better; the adopted house is then refined once
    more on all rows, from itself.
    """
    usable = [r for r in rows if r.heat is not None]
    split = now - HOLDOUT_HOURS * 3600
    train = [r for r in rows if r.t < split]
    test = [r for r in rows if r.t >= split]
    report = Report(now, len(usable), sum(1 for r in test if r.heat is not None))
    device = fit_device(rows, house)
    device["restart_gap"] = restart_gap(start_gaps or [], house.restart_gap)
    report.device = {k: round(v, 2) for k, v in device.items()}
    house = replace(house, **device)
    if len(usable) < MIN_FIT_ROWS or report.holdout_rows < 48:
        report.reason = f"Waiting for data: {len(usable)} of {MIN_FIT_ROWS} logged half hours with measured heat"
        return house, report
    scale = pv_scale(rows)
    train_runs, test_runs = runs_of(train, place, scale), runs_of(test, place, scale)
    if not train_runs or not test_runs:
        report.reason = "Logged half hours are too broken up to fit"
        return house, report
    before = error(house, test_runs)
    candidate = fit_house(house, train_runs, rounds)
    after = error(candidate, test_runs)
    report.error_before, report.error_after = math.sqrt(before), math.sqrt(after)
    if not after <= before * MIN_IMPROVEMENT:
        report.reason = "Kept the house values: a refit did not forecast the last two days better"
        return house, report
    adopted = fit_house(candidate, runs_of(rows, place, scale), rounds // 2)
    if error(adopted, test_runs) > after:
        adopted = candidate
    report.adopted = True
    report.reason = "Adopted refitted house values: they forecast the last two days better"
    return adopted, report


def house_to_dict(house: mpc.House) -> dict:
    return asdict(house)


def house_from_dict(data: dict | None, default: mpc.House) -> mpc.House:
    if not data:
        return default
    known = {f.name for f in fields(mpc.House)}
    try:
        values = {k: float(v) for k, v in data.items() if k in known and math.isfinite(float(v))}
        return replace(default, **values)
    except (TypeError, ValueError):
        return default
