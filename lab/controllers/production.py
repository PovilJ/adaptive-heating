"""production: the Home Assistant controller core (custom_components/adaptive_heating/slab.py)
driven through the lab Observation, the way the integration's coordinator drives it.

It imports the production file itself (no copy, no Home Assistant), so a lab run measures the
code that ships. The input mapping follows the coordinator:

- GHI is rebuilt from the forecast's cloud cover (clear-sky Haurwitz x the site cloud factor,
  the integration's `slab.hour_ghi`) at the site location in `.local/lab-data/site.json`.
  `ghi=forecast` uses the lab forecast's own GHI instead (core-equivalence check).
- The room is the reported value, as the coordinator passes it (the core limits how fast it may
  move, `slab.Params.room_slew`). `smooth=1` is a diagnostic: the 30-minute time-weighted mean
  that 0.4.5-0.5.3 used (it costs comfort; CONTROLLER.md).
- The production safety rules are on (CONTROLLER.md, "Differences from the lab hybrid");
  `production[lab_hybrid=1,ghi=forecast,write_max=45]` is the lab hybrid at the unit's 4 K,
  bit for bit (`hybrid[delta=4]`).
- The restart hysteresis is read from the unit and never written (the simulator starts at 4 K,
  the real unit's value since 2026-10-21).
- Setpoint limits are the integration's defaults (Minimum water 25, Maximum water 40 °C).

Any `slab.Params` field can be set as a parameter, e.g. `production[q_run=0]`.
"""
from __future__ import annotations

from datetime import datetime
import importlib.util
import json
from pathlib import Path
import sys

from lab.sim.interface import Command, Observation

ROOT = Path(__file__).resolve().parents[2]
_NAME = "adaptive_heating_slab_core"
if _NAME in sys.modules:
    slab = sys.modules[_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_NAME, ROOT / "custom_components" / "adaptive_heating" / "slab.py")
    slab = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = slab
    _spec.loader.exec_module(slab)

# Integration defaults (const.DEFAULTS): Minimum water 25, Maximum water 40 °C.
PRODUCTION_LIMITS = {"sp_floor": 25.0, "sp_ceil": 39.0, "write_max": 40.0}


def _c(cloud):
    return 1.0 if cloud is None or cloud != cloud else min(max(cloud / 100.0, 0.0), 1.0)


CLOUD_LAWS = {
    "site": lambda cl: slab.cloud_factor(cl),
    "old": lambda cl: 1.0 - 0.36 * _c(cl) - 0.16 * _c(cl) ** 20,    # 0.6.0-0.6.2 site irradiance fit
    "lin": lambda cl: 1.0 - _c(cl),
    "zero": lambda cl: 0.0,
}


def _site():
    path = ROOT / ".local" / "lab-data" / "site.json"
    data = json.loads(path.read_text())
    return float(data["lat"]), float(data["lon"])


class Production:
    name = "production"

    def reset(self, params: dict) -> None:
        params = dict(params)
        self.ghi_source = str(params.pop("ghi", "cloud"))
        self.smooth = float(params.pop("smooth", 0)) > 0
        # diagnostic: cloud -> sun law used to rebuild GHI (`site` = the shipped slab.cloud_factor,
        # Kasten-Czeplak since 0.6.3; the others were the 0.6.3 comparison, docs/CONTROLLER.md "Sun")
        self.cloudf = CLOUD_LAWS[str(params.pop("cloudf", "site"))]
        self.place = _site() if self.ghi_source == "cloud" else None
        self.core = slab.SlabController(slab.Params.from_mapping(PRODUCTION_LIMITS | params))
        self.fc_id = None
        self.fc = ()
        self.readings = []      # (minute, value) when the reported room value changed
        self.last_room = None

    def _forecast(self, obs: Observation) -> tuple:
        if id(obs.forecast) != self.fc_id:
            self.fc_id = id(obs.forecast)
            hours = []
            for h in obs.forecast:
                minute = obs.minute + (h["time"] - obs.time).total_seconds() / 60.0
                if self.place is None:
                    ghi = h.get("ghi")
                else:
                    ghi = slab.hour_ghi(h["time"], *self.place, 0.0) * self.cloudf(h.get("cloud"))
                hours.append(slab.Hour(minute, h["outdoor"], ghi))
            self.fc = tuple(hours)
        return self.fc

    def _room(self, obs: Observation):
        """The room as the coordinator passes it: the reported value (`smooth=1`: the 0.4.5-0.5.3
        time-weighted 30-minute mean, a diagnostic)."""
        room = obs.room
        if room is None or room != room:
            return None
        if room != self.last_room:
            self.last_room = room
            self.readings = (self.readings + [(obs.minute - obs.room_age_min, room)])[-20:]
        if not self.smooth:
            return room
        now, start = obs.minute, obs.minute - 30
        earlier = [v for t, v in self.readings if t <= start]
        points = ([(start, earlier[-1])] if earlier else []) + [(t, v) for t, v in self.readings if start < t <= now]
        if not points or points[-1][1] != room:
            return room
        ends = [t for t, _ in points[1:]] + [now]
        spans = [b - a for (a, _), b in zip(points, ends)]
        total = sum(spans)
        return sum(v * s for (_, v), s in zip(points, spans)) / total if total > 0 else room

    def step(self, obs: Observation) -> Command:
        x = slab.Inputs(
            minute=float(obs.minute), local_hour=obs.local_hour, target=obs.target, outdoor=obs.outdoor,
            outlet=obs.outlet, inlet=obs.inlet, setpoint=obs.setpoint, restart_delta=obs.restart_delta,
            compressor_on=obs.compressor_on, mode=obs.mode, room=self._room(obs), room_age_min=obs.room_age_min,
            forecast=self._forecast(obs), link_ok=obs.link_ok)
        d = self.core.step(x)
        return Command(setpoint=d.setpoint) if d.setpoint is not None else Command()


CONTROLLER = Production


if __name__ == "__main__":
    from datetime import timedelta, timezone

    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fc = tuple({"time": t0 + timedelta(hours=h + 1), "outdoor": 0.0, "rh": 80, "ghi": 0, "dni": 0, "dhi": 0,
                "cloud": 100} for h in range(48))
    base = dict(time=t0, local_hour=2.0, room=21.5, room_age_min=5, outdoor=0.0, outlet=24.0, inlet=24.3,
                setpoint=25.0, restart_delta=5.0, quiet=False, heating_enabled=True, compressor_on=False,
                mode="idle", electric_kw=0.02, energy_kwh=0.0, target=22.0, forecast=fc, pv_kw=None)
    c = Production()
    c.reset({"ghi": "forecast"})
    cmds = [c.step(Observation(minute=m, **base)) for m in range(60)]
    assert any(x.setpoint and x.setpoint >= 28 for x in cmds), "a cold slab must kick a run"
    assert c.step(Observation(minute=61, link_ok=False, **base)) == Command(), "no writes while the link is down"
    print("self-check ok")
