"""Replay controllers against the fitted house over recorded weather. Offline.

    python scripts/backtest.py DATA_DIR START END [--mismatch]

Compares the predictive planner, the previous heating curve and the archived
PyScript on electricity and comfort. The house is the fitted model itself (or a
deliberately wrong one with --mismatch), so this ranks controllers; it does not
predict the electricity bill.
"""
import ast, importlib.util, json, sys, time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import datetime as datetime_module

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "custom_components/adaptive_heating" / (name + ".py"))
    loaded = importlib.util.module_from_spec(spec); sys.modules[name] = loaded; spec.loader.exec_module(loaded)
    return loaded


mpc, engine = module("mpc"), module("engine")
TARGET, OFFSET = 22.5, 3  # local time is UTC+3 here; close enough for a ranking


class Weather:
    def __init__(self, folder):
        self.rows = json.loads((Path(folder) / "meteo.json").read_text())
        self.loc = json.loads((Path(folder) / "loc.json").read_text())

    def at(self, when):
        return self.rows[when.strftime("%Y-%m-%dT%H:00")]

    def forecast(self, when, hours=40):
        return [(when.replace(minute=0) + timedelta(hours=h), *self.at(when + timedelta(hours=h))[:2]) for h in range(hours)]

    def sun(self, when):
        return mpc.sunshine(when, self.loc["lat"], self.loc["lon"], self.at(when)[1])


class Predictive:
    name = "predictive"

    def __init__(self, house, comfort):
        self.house, self.comfort, self.estimate, self.seed, self.guard = house, comfort, mpc.Estimate(), None, mpc.Guard()

    def decide(self, when, room, outdoor, weather, setpoint, running):
        self.estimate.update(self.house, when.timestamp(), room, outdoor, setpoint, 1.0 if running else 0.0, weather.sun(when))
        steps = mpc.horizon(when, weather.forecast(when), self.comfort, weather.loc["lat"], weather.loc["lon"], outdoor, OFFSET)
        result = mpc.plan(self.house, self.comfort, steps, self.estimate.state(self.house), self.estimate.bias, running, self.seed)
        self.seed = result.levels
        boost = self.guard.update(room, steps[0].floor)
        return max(setpoint - 5, min(setpoint + 3, self.comfort.maximum_water, result.water + boost))


class Curve:
    def __init__(self, offset):
        self.name, self.settings = f"curve +{offset:g}", engine.Settings(target=TARGET, curve_offset=offset)

    def decide(self, when, room, outdoor, weather, setpoint, running):
        want = engine.decide(self.settings, engine.Model(), room, outdoor, [r[1] for r in weather.forecast(when, 13)[1:]]).proposed
        return round(max(setpoint - 1, min(setpoint + 2, want)))


class Legacy:
    name = "pyscript"

    def __init__(self):
        parsed = ast.parse((ROOT / "legacy/smart_heating.py").read_text())
        nodes = [n for n in parsed.body if isinstance(n, (ast.Assign, ast.FunctionDef))]
        for n in nodes:
            if isinstance(n, ast.FunctionDef):
                n.decorator_list = []
        quiet = lambda *a, **k: None
        self.ns = {"log": SimpleNamespace(info=quiet, warning=quiet, error=quiet)}
        exec(compile(ast.Module(nodes, type_ignores=[]), "legacy", "exec"), self.ns)

    def decide(self, when, room, outdoor, weather, setpoint, running):
        local = (when + timedelta(hours=OFFSET)).replace(tzinfo=None)
        clock = type("Clock", (datetime,), {"now": classmethod(lambda cls, tz=None: local)})
        real, datetime_module.datetime = datetime_module.datetime, clock
        try:
            elevation = mpc.sun_position(when, weather.loc["lat"], weather.loc["lon"])[0]
            sunset = when
            while mpc.sun_position(sunset, weather.loc["lat"], weather.loc["lon"])[0] <= 0: sunset += timedelta(minutes=30)
            while mpc.sun_position(sunset, weather.loc["lat"], weather.loc["lon"])[0] > 0: sunset += timedelta(minutes=10)
            ns = self.ns
            ns["get_forecast_data"] = lambda: [r[1] for r in weather.forecast(when, 13)[1:]]
            ns["is_sun_up"] = lambda: elevation > 0
            ns["get_hours_until_sunset"] = lambda: (sunset - when).total_seconds() / 3600
            sunny = weather.at(when)[1] < 60 and elevation >= 10
            current = {"indoor": room, "outdoor": outdoor, "water_in": setpoint - 2 if running else room + 1, "water_out": None,
                       "target": TARGET, "base_target": TARGET, "is_sunny": sunny, "k_loss": 0.01567, "k_gain": 0.03318}
            if local.hour >= 22 or local.hour < 6:
                ns["history_buffer"] = [s for s in ns["history_buffer"] + [{"time": local, "indoor": room}]
                                        if (local - s["time"]).total_seconds() < 14400]
            water = ns["optimize_heating"](current)[0]
        finally:
            datetime_module.datetime = real
        if room < TARGET - 0.3 and water < setpoint:
            return setpoint
        return max(setpoint - 1, min(setpoint + 2, water))


def run(controller, plant, weather, start, end):
    when, setpoint, running = start, 25.0, False
    state = plant.resting(TARGET, weather.at(start)[0])
    kwh = starts = cold = night_cold = warm = total = 0
    rooms = []
    while when < end:
        outdoor = weather.at(when)[0]
        measured = round(plant.room(state) * 5) / 5  # the 0.2 °C thermometer
        setpoint = float(controller.decide(when, measured, outdoor, weather, setpoint, running))
        heat = plant.heat_kw(setpoint, state[0])
        if heat > 0:
            kwh += heat / plant.cop(setpoint, outdoor) * (1.15 if heat < plant.q_min else 1) * 0.5
            starts += not running
        running = heat > 0
        state = plant.step(state, heat, outdoor, weather.sun(when + timedelta(minutes=15)))
        room = plant.room(state); rooms.append(room); total += 1
        hour = (when.hour + OFFSET) % 24
        night = hour >= 22 or hour < 7
        cold += (not night) and room < TARGET - 0.3
        night_cold += night and room < 21.4
        warm += room > TARGET + 0.5
        when += timedelta(minutes=30)
    days = total / 48
    return (f"{controller.name:12} {kwh / days:6.1f} kWh/day | room mean {sum(rooms) / total:5.2f} min {min(rooms):5.2f} max {max(rooms):5.2f}"
            f" | day <{TARGET - 0.3:.1f}: {cold / 2 / days:4.1f} h/day | night <21.4: {night_cold / 2 / days:4.1f} h/day"
            f" | >{TARGET + 0.5:.1f}: {warm / 2 / days:4.1f} h/day | starts {starts / days:3.1f}/day")


if __name__ == "__main__":
    weather = Weather(sys.argv[1])
    start, end = (datetime.fromisoformat(d).replace(tzinfo=timezone.utc) for d in sys.argv[2:4])
    house = mpc.House()
    plant = replace(house, loss=house.loss * 1.25, heat=house.heat * 0.75, warm=house.warm * 0.8, sun_east=house.sun_east * 0.6,
                    sun_south=house.sun_south * 1.5, emit=house.emit * 0.8) if "--mismatch" in sys.argv else house
    comfort = mpc.Comfort(target=TARGET)
    for controller in (Predictive(house, comfort), Predictive(house, replace(comfort, night_floor=TARGET)), Curve(3.0), Curve(0.5), Legacy()):
        began = time.time()
        print(run(controller, plant, weather, start, end), f"| {time.time() - began:.0f}s", flush=True)
