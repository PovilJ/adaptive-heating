"""Fit mpc.House to recorded history. Offline; reads JSON exports, prints the fitted values.

    python scripts/fit_house.py DATA_DIR

DATA_DIR holds lts.json (HA hourly statistics: room, heat-pump electricity),
meteo.json (Open-Meteo hourly {time: [temperature, cloud %, ...]}) and loc.json.
"""
import importlib.util, json, math, sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mpc", ROOT / "custom_components/adaptive_heating/mpc.py")
mpc = importlib.util.module_from_spec(spec); sys.modules["mpc"] = mpc; spec.loader.exec_module(mpc)

STANDBY_KW = 0.04
# Fitted as physical quantities, then converted: kW/°C lost outdoors, kWh/°C of slab,
# kW/°C slab-to-building, kWh/°C of building, sun glow °C/h per kW/m², glow fade 1/h,
# share of glow kept by the building, kW of gains.
PHYSICAL = ("ua", "slab", "couple", "building", "east", "south", "west", "fade", "keep", "gains", "mix")
LOW = (0.05, 2, 0.2, 2, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0, 0.0)
HIGH = (0.5, 80, 4.0, 150, 30, 30, 30, 2.0, 1.0, 1.5, 0.9)


def load(folder, start="2026-01-10", end="2026-05-10", extra=("2026-10-08", "2026-10-11")):
    folder = Path(folder)
    lts, meteo, loc = (json.loads((folder / n).read_text()) for n in ("lts.json", "meteo.json", "loc.json"))
    hour = lambda row: datetime.fromtimestamp(row["start"] / 1000, timezone.utc)
    room = {hour(r): r["mean"] for r in lts["sensor.salionas_temperature"] if r.get("mean") is not None}
    # The thermal-power sensor has gaps and impossible COPs; the electricity meter is sound.
    used = {hour(r): r["change"] for r in lts["sensor.oras_vanduo_combined_total_energy"] if r.get("change") is not None}
    base = mpc.House()
    heat = {}
    for at, kwh in used.items():
        outdoor = (meteo.get(at.strftime("%Y-%m-%dT%H:00")) or [None])[0]
        if outdoor is not None and at in room:
            water = room[at] + 0.47 * max(0, room[at] - outdoor) + 2  # the PyScript's steady-state water
            heat[at] = max(0.0, kwh - STANDBY_KW) * base.cop(water, outdoor)
    rows = []
    for key, values in sorted(meteo.items()):
        at = datetime.fromisoformat(key).replace(tzinfo=timezone.utc)
        day = key[:10]
        if not (start <= day < end or extra[0] <= day < extra[1]) or at not in room or at not in heat:
            continue
        sun = mpc.sunshine(at + timedelta(minutes=30), loc["lat"], loc["lon"], values[1])
        rows.append((at, room[at], max(0.0, heat[at]), values[0], sun))
    return rows


def days(rows):
    """Contiguous runs of hours, cut at every midnight so the room is re-anchored daily."""
    out, run = [], []
    for row in rows:
        if run and (row[0] - run[-1][0] != timedelta(hours=1) or row[0].hour == 0):
            out.append(run); run = []
        run.append(row)
    return out + [run]


def error(house, runs, detail=False, hours=None):
    total = count = 0.0
    slab = None
    previous_end = None
    errors = []
    for run in runs:
        if len(run) < 12:
            slab = None
            continue
        if slab is None or previous_end is None or run[0][0] - previous_end > timedelta(hours=1):
            slab, glow = house.resting(run[0][1], run[0][3])[0], 0.0
        state = house.resting(run[0][1], 0.0, glow, slab)  # re-anchor the measured room, keep slab and glow
        for (at, _, heat, outdoor, sun), nxt in zip(run, run[1:]):
            for _ in range(2):
                state = house.step(state, heat, outdoor, sun)
            miss = house.room(state) - nxt[1]
            if hours is not None and not (at.hour in hours):
                continue
            total += miss * miss if abs(miss) < 1 else 2 * abs(miss) - 1  # Huber
            count += 1
            errors.append(miss)
        slab, glow = state[0], state[2]
        previous_end = run[-1][0]
    if detail:
        errors.sort(key=abs)
        return math.sqrt(sum(e * e for e in errors) / len(errors)), abs(errors[len(errors) // 2]), abs(errors[int(len(errors) * .9)])
    return total / max(count, 1)


def nelder_mead(f, x, scale, rounds=4000):
    n = len(x)
    simplex = [list(x)] + [[v + (scale[i] if i == j else 0) for i, v in enumerate(x)] for j in range(n)]
    values = [f(p) for p in simplex]
    for _ in range(rounds):
        order = sorted(range(n + 1), key=values.__getitem__)
        simplex, values = [simplex[i] for i in order], [values[i] for i in order]
        if values[-1] - values[0] < 1e-9:
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


def physical(x):
    return [low + (high - low) / (1 + math.exp(-v)) for v, low, high in zip(x, LOW, HIGH)]


def house_from(x):
    ua, slab, couple, building, east, south, west, fade, keep, gains, mix = physical(x)
    return replace(mpc.House(), heat=1 / slab, release=couple / slab, warm=couple / building, loss=ua / building,
                   sun_east=east, sun_south=south, sun_west=west, sun_fade=fade, sun_keep=keep, gains=gains / building, mix=mix)


if __name__ == "__main__":
    rows = load(sys.argv[1])
    runs = days(rows)
    print(len(rows), "hours in", len(runs), "runs;", "mean heat kW", round(sum(r[2] for r in rows) / len(rows), 2))
    logit = lambda v, low, high: math.log((v - low) / (high - v))
    best, value = None, math.inf
    for guess in ((0.17, 10, 1.5, 40, 3, 2, 1, 0.4, 0.2, 0.3, 0.2), (0.12, 30, 0.8, 80, 6, 3, 1, 0.8, 0.5, 0.2, 0.4), (0.22, 5, 2.5, 20, 2, 4, 3, 0.2, 0.1, 0.5, 0.1)):
        x = [logit(v, low, high) for v, low, high in zip(guess, LOW, HIGH)]
        for attempt in range(2):
            x, v = nelder_mead(lambda p: error(house_from(p), runs), x, [1.0 / (attempt + 1)] * len(x))
        print("  start", guess, "->", round(v, 4), flush=True)
        if v < value:
            best, value = x, v
    house = house_from(best)
    print(dict(zip(PHYSICAL, (round(v, 3) for v in physical(best)))))
    print({n: round(getattr(house, n), 5) for n in ("heat", "release", "warm", "loss", "sun_east", "sun_south", "sun_west", "sun_fade", "sun_keep", "gains", "mix")})
    print("dark hours only (17–04 UTC): rms %.2f  median %.2f  90%% %.2f °C" % error(house, runs, detail=True, hours=set(range(17, 24)) | set(range(0, 5))))
    print("24 h roll-out error: rms %.2f  median %.2f  90%% %.2f °C" % error(house, runs, detail=True))
