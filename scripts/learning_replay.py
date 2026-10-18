"""Replay the controller, learning as it goes, against a house it does not know. Offline.

    python scripts/learning_replay.py DATA_DIR START END [--old REF]

DATA_DIR holds meteo.json (Open-Meteo hourly {time: [temperature, cloud %]}) and
loc.json. The plant is a house unlike the code's defaults (October's leakier
first house by default, with the heat pump's real restart rule); the
controller starts from the defaults, logs what it sees and refits every night
at 03:00 as the integration does. With --old REF the planner from that git
revision runs too, without learning, for comparison.
"""
import importlib.util, json, math, subprocess, sys, tempfile, time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OFFSET = 3  # local time UTC+3
TARGET = 22.0


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec); sys.modules[name] = loaded; spec.loader.exec_module(loaded)
    return loaded


mpc = module("mpc", ROOT / "custom_components/adaptive_heating/mpc.py")
learn = module("learn", ROOT / "custom_components/adaptive_heating/learn.py")

# What 11-18 Oct 2026 said about the first house: heat loss 0.19 kW/°C, sun from the east and south,
# no start below outlet + 4.5 °C, minimum output 3.8 kW, outlet 2.7 °C over the slab at rest.
OCTOBER = replace(mpc.House(), loss=0.195 / 21.29, sun_east=1.26, sun_south=1.71, restart_gap=4.5, q_min=3.8, idle_offset=2.7)


# Another house altogether: twice the loss, a slab half as heavy again, sun from the west, a 3 °C restart gap.
OTHER = replace(mpc.House(), loss=2 * mpc.House().loss, heat=mpc.House().heat / 1.5, sun_east=0.5, sun_south=1.0,
                sun_west=2.0, restart_gap=3.0, q_min=4.5, idle_offset=2.0)


class Weather:
    def __init__(self, folder):
        self.rows = json.loads((Path(folder) / "meteo.json").read_text())
        self.loc = json.loads((Path(folder) / "loc.json").read_text())

    def at(self, when):
        return self.rows[when.strftime("%Y-%m-%dT%H:00")]

    def forecast(self, when, hours=40):
        return [(when.replace(minute=0) + timedelta(hours=h), *self.at(when + timedelta(hours=h))[:2]) for h in range(hours)]

    def sun(self, when, clearness=None):
        return mpc.sunshine(when, self.loc["lat"], self.loc["lon"], self.at(when)[1], clearness)


class Learning:
    """The integration's planner path: estimate, plan, guard, lifts, nightly refit."""
    name = "learning"

    def __init__(self, comfort, planner=mpc, learns=True, lift=True, refits=True, boost_starts=False):
        self.mpc, self.learns, self.lift, self.refits, self.boost_starts = planner, learns, lift, refits, boost_starts
        self.house, self.comfort, self.estimate, self.seed, self.guard = planner.House(), comfort, planner.Estimate(), None, planner.Guard()
        self.rows, self.gaps, self.last_fit, self.reports = [], [], None, []

    def decide(self, when, room, outdoor, weather, setpoint, running, plant_state, heat, outlet):
        m = self.mpc
        place = (weather.loc["lat"], weather.loc["lon"])
        if self.learns:
            self.estimate.update(self.house, when.timestamp(), room, outdoor, setpoint, 1.0 if running else 0.0,
                                 weather.sun(when), heat)
            self.rows.append(learn.Row(when.timestamp(), room, outdoor, heat, 0.5, weather.at(when)[1], None,
                                       setpoint, self.estimate.slab, outlet, 1.0 if running else 0.0))
            self.rows = [r for r in self.rows if r.t >= when.timestamp() - learn.KEEP_DAYS * 86400]
            local = when + timedelta(hours=OFFSET)
            if self.refits and local.hour == 3 and local.minute < 30 and (self.last_fit is None or when - self.last_fit > timedelta(hours=20)):
                self.last_fit = when
                self.house, report = learn.refit(self.house, self.rows, place, when.timestamp(), self.gaps, rounds=800)
                if report.adopted:
                    self.estimate.bias = 0.0
                self.reports.append((when, report))
            steps = m.horizon(when, weather.forecast(when), self.comfort, *place, outdoor, OFFSET)
        else:
            self.estimate.update(self.house, when.timestamp(), room, outdoor, setpoint, 1.0 if running else 0.0, weather.sun(when))
            steps = m.horizon(when, weather.forecast(when), self.comfort, *place, outdoor, OFFSET)
        result = m.plan(self.house, self.comfort, steps, self.estimate.state(self.house), self.estimate.bias, running, self.seed,
                        self.run_left, setpoint)
        self.seed = result.levels
        boost = self.guard.update(room, steps[0].floor)
        delivers = self.house.heat_kw(result.water, self.estimate.slab) > 0
        if self.lift and not running:
            boosted = result.water + boost
            wants = (boost > 0 and self.boost_starts) or (self.house.heat_kw(boosted, self.estimate.slab) > 0
                                                          and self.house.starts(boosted, self.estimate.slab))
            water = m.start_level(boosted, wants, outlet, self.house.restart_gap)
        else:
            water = m.keep_running(result.water + boost, boost > 0 or delivers or self.run_left > 0, self.inlet)
        if self.run_left > 0:
            water = max(water, setpoint)
        if m.too_warm(room, steps[0].ceiling):
            return self.comfort.minimum_water, True
        return max(setpoint - self.comfort.fall_step, min(setpoint + self.comfort.rise_step, self.comfort.maximum_water, water)), False


def run(controller, plant, weather, start, end):
    when, setpoint, running = start, 25.0, False
    state = plant.resting(TARGET, weather.at(start)[0])
    kwh = starts = cold = warm = total = 0
    rooms, run_steps, ignored, heat = [], 0, 0, 0.0
    while when < end:
        outdoor = weather.at(when)[0]
        measured = round(plant.room(state) * 5) / 5  # the 0.2 °C thermometer
        controller.inlet = state[0] + (4.7 if running else plant.idle_offset)
        outlet = state[0] + (6.0 if running else plant.idle_offset)
        controller.run_left = max(0, mpc.MIN_RUN_STEPS - run_steps) if running else 0
        setpoint, fast = controller.decide(when, measured, outdoor, weather, setpoint, running, state, heat, outlet)
        setpoint = float(setpoint)
        if fast:
            pass
        heat = plant.heat_kw(setpoint, state[0])
        if not running and heat > 0 and not plant.starts(setpoint, state[0]):
            heat, ignored = 0.0, ignored + 1  # the unit ignores a setpoint under its restart gap
        if heat > 0:
            kwh += heat / plant.cop(setpoint, outdoor) * (1.15 if heat < plant.q_min else 1) * 0.5
            if not running:
                starts += 1
                if hasattr(controller, "gaps"):
                    controller.gaps = (controller.gaps + [round(setpoint - outlet, 2)])[-20:]
            run_steps = run_steps + 1 if running else 1
        running = heat > 0
        state = plant.step(state, heat, outdoor, weather.sun(when + timedelta(minutes=15)))
        room = plant.room(state); rooms.append(room); total += 1
        hour = (when.hour + OFFSET) % 24
        night = hour >= 22 or hour < 7
        cold += (room < (21.5 if night else TARGET) - 0.3)
        warm += room > TARGET + 0.5
        when += timedelta(minutes=30)
    days = total / 48
    return (f"{controller.name:10} {kwh / days:6.2f} kWh/day | room mean {sum(rooms) / total:5.2f} min {min(rooms):5.2f} max {max(rooms):5.2f}"
            f" | under band {cold / 2 / days:4.1f} h/day | over target+0.5 {warm / 2 / days:4.1f} h/day"
            f" | starts {starts / days:3.1f}/day | ignored setpoints {ignored / days:3.1f}/day")


if __name__ == "__main__":
    weather = Weather(sys.argv[1])
    start, end = (datetime.fromisoformat(d).replace(tzinfo=timezone.utc) for d in sys.argv[2:4])
    comfort = mpc.Comfort(target=TARGET, night_floor=21.5, rise_step=2.0, fall_step=5.0)
    controllers = [Learning(comfort)]
    if "--ablate" in sys.argv:
        for name, kw in (("no refit", dict(refits=False)), ("no lift", dict(lift=False)), ("boost starts", dict(boost_starts=True))):
            controller = Learning(comfort, **kw); controller.name = name; controllers.append(controller)
    if "--old" in sys.argv:
        ref = sys.argv[sys.argv.index("--old") + 1]
        source = subprocess.run(["git", "show", f"{ref}:custom_components/adaptive_heating/mpc.py"], cwd=ROOT,
                                capture_output=True, text=True, check=True).stdout
        path = Path(tempfile.mkdtemp()) / "mpc_old.py"; path.write_text(source)
        old = module("mpc_old", path)
        fields = {f for f in old.Comfort.__dataclass_fields__}
        controller = Learning(old.Comfort(**{k: getattr(comfort, k) for k in fields}), old, learns=False, lift=False)
        controller.name = f"old {ref}"
        controllers.append(controller)
    for controller in controllers:
        began = time.time()
        plant = OTHER if "--other" in sys.argv else OCTOBER
        print(run(controller, plant, weather, start, end), f"| {time.time() - began:.0f}s", flush=True)
        for when, report in getattr(controller, "reports", []):
            if report.adopted or report.error_before:
                print(f"   {when:%m-%d} {report.reason[:40]:40} rms {report.error_before or 0:.3f} -> {report.error_after or 0:.3f}"
                      f"  ua {learn.physical_of(controller.house)[0]:.3f}" if report is controller.reports[-1][1] else
                      f"   {when:%m-%d} {report.reason[:40]:40} rms {report.error_before or 0:.3f} -> {report.error_after or 0:.3f}")
        if getattr(controller, "learns", False):
            h = controller.house
            print(f"   learned: ua {learn.physical_of(h)[0]:.3f} (plant {learn.physical_of(plant)[0]:.3f}), sun E/S/W {h.sun_east:.2f}/{h.sun_south:.2f}/{h.sun_west:.2f}"
                  f" (plant {plant.sun_east}/{plant.sun_south}/{plant.sun_west}), gap {h.restart_gap}, q_min {h.q_min:.2f}, idle {h.idle_offset:.2f}")
