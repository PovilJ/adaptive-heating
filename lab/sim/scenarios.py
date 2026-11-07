"""Named scenarios for the closed-loop simulator.

Two kinds:

- **recorded**: a window of the minute record with its recorded weather (ERA5 on the minute grid,
  the same input the house was fitted on), recorded hot-water requests, the recorded disturbance
  (residual heat re-derived for the chosen house parameters, so the recorded room is reproduced
  exactly under the recorded heat) and recorded PV. The run starts from the recorded state of the
  house at the window start (no warm-up) with the unit idle and the recorded registers. The
  controller context carries the recorded register history for `replay_recorded`.
- **archive**: Open-Meteo archive weather with synthetic hot water (recorded days drawn at random)
  and synthetic disturbances; a 3-day warm-up under the neutral reference controller
  (lab/controllers/reference.py) from a quasi-steady state, excluded from the metrics, so every
  controller starts from the same house state.

`build(name, variant)` returns the `Exo` bundle for lab/sim/simulator.py.
"""
from __future__ import annotations

import zlib
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from lab.data.common import epoch
from lab.sim import exogenous as X
from lab.sim.simulator import Exo, plant


@dataclass(frozen=True)
class Scenario:
    name: str
    start: str            # UTC ISO, first measured minute
    end: str              # UTC ISO, end (exclusive)
    kind: str             # 'recorded' | 'archive'
    warmup_days: float = 3.0
    description: str = ""
    runout_days: float = 3.0  # archive only: common run-out under the reference after the window


SCENARIOS = {s.name: s for s in (
    Scenario("recorded", "2026-10-09T00:00Z", "2026-11-06T16:00Z", "recorded", 0.0,
             "current season, recorded weather/DHW/disturbance (both Modbus bridges), from the recorded state"),
    Scenario("recorded_c2", "2026-10-23T00:00Z", "2026-11-06T16:00Z", "recorded", 0.0,
             "new Modbus bridge only (clean unit data)"),
    Scenario("recorded_spring", "2026-02-26T00:00Z", "2026-05-06T00:00Z", "recorded", 0.0,
             "legacy controller, late winter and spring (link outages: DHW and unit data incomplete)"),
    Scenario("recorded_a0", "2026-02-09T15:00Z", "2026-02-14T00:00Z", "recorded", 0.0,
             "cold week A0 (-19..+2 degC), legacy controller, the only clean cold minute data"),
    Scenario("oct_mild", "2025-10-08T00:00Z", "2025-10-15T00:00Z", "archive", 3.0,
             "mild autumn week, mean +7.6 degC (+1.6..+15.3)"),
    Scenario("nov_mixed", "2025-11-10T00:00Z", "2025-11-17T00:00Z", "archive", 3.0,
             "mixed November week, mean +4.3 degC (-3.7..+9.7), humid, dull"),
    Scenario("dec_damp", "2025-12-14T00:00Z", "2025-12-21T00:00Z", "archive", 3.0,
             "damp December week, mean +0.7 degC (-2.1..+3.9), RH 97 %, almost no sun (defrost-heavy)"),
    Scenario("jan_cold", "2026-01-15T00:00Z", "2026-01-22T00:00Z", "archive", 3.0,
             "coldest week of January 2026, mean -14.1 degC (-18.4..-7.9)"),
    Scenario("feb_sunny_cold", "2026-02-15T00:00Z", "2026-02-22T00:00Z", "archive", 3.0,
             "sunny cold February week, mean -10.2 degC (-19.3..-1.4), 1.8 kWh/m2/day sun"),
    Scenario("mar_shoulder", "2026-03-05T00:00Z", "2026-03-12T00:00Z", "archive", 3.0,
             "March shoulder week, mean +3.0 degC (-4.2..+14.3), sunny"),
    Scenario("apr_mild_sunny", "2026-04-18T00:00Z", "2026-04-25T00:00Z", "archive", 3.0,
             "mild sunny April week, mean +7.5 degC (-0.2..+14.8), 5.6 kWh/m2/day sun"),
    Scenario("season", "2025-10-15T00:00Z", "2026-04-15T00:00Z", "archive", 3.0,
             "full heating season for the final ranking (183 days)"),
)}

WEEKS = ("oct_mild", "nov_mixed", "dec_damp", "jan_cold", "feb_sunny_cold", "mar_shoulder", "apr_mild_sunny")
GROUPS = {
    "all": ("recorded",) + WEEKS,
    "weeks": WEEKS,
    "everything": ("recorded",) + WEEKS + ("season",),
}


def expand(names: str):
    out = []
    for part in names.split(","):
        part = part.strip()
        if part in GROUPS:
            out.extend(GROUPS[part])
        elif part in SCENARIOS:
            out.append(part)
        else:
            raise ValueError(f"unknown scenario {part!r}; known: {', '.join(list(SCENARIOS) + list(GROUPS))}")
    return list(dict.fromkeys(out))


def _seed(name, seed):
    return int(zlib.crc32(name.encode())) % 100000 + 1000 * int(seed or 0)


def build(name: str, variant: str = "nominal", seed: int = 0, link_drops_per_day: float = 0.0) -> Exo:
    return _build(name, variant, int(seed or 0), float(link_drops_per_day))


@lru_cache(maxsize=16)
def _build(name, variant, seed, link_drops_per_day):
    from lab.sim.simulator import variant_flags
    sc = SCENARIOS[name]
    s = _seed(name, seed)
    if sc.kind == "recorded":
        exo = _build_recorded(sc, variant, s)
    else:
        _, hp = plant(variant)
        fl = variant_flags(variant)
        exo = _build_archive(sc, s, local="era5_only" not in fl, hp=None if "synthetic_dist" in fl else hp)
    exo.link_drops_per_day = link_drops_per_day
    return exo


def _build_archive(sc: Scenario, seed: int, local: bool = True, hp=None) -> Exo:
    """Archive scenario. The house and the unit run on the true local air = ERA5 + a local
    departure (AR(1), SD 1.1 K, 6 h; review round 1); the forecast stays on ERA5; the unit's
    sensor reads the local air + its own error. `local=False` (flag token era5_only) drives
    everything with ERA5 and the old sensor model. The disturbance is a bootstrap of recorded
    residual days for house parameters `hp` (review round 1), or the parametric generator when
    hp is None (flag token synthetic_dist)."""
    t0 = epoch(sc.start) - sc.warmup_days * 86400.0
    t1 = epoch(sc.end) + sc.runout_days * 86400.0
    grid = np.arange(t0, t1, 60.0)
    w = X.weather_minute(grid)
    lh = X.local_hour(grid)
    if local:
        dev = X.local_deviation(len(grid), seed)
        t_true = w["t_out"] + dev
        base = X.outdoor_sensor_base(t_true, seed, sd=X.SENSOR_OWN_SD_K, ghi=w["ghi"],
                                     night_bias=X.SENSOR_NIGHT_BIAS_K)
    else:
        t_true = w["t_out"]
        base = X.outdoor_sensor_base(t_true, seed)
    return Exo(
        name=sc.name, grid=grid, n_warm=int(round(sc.warmup_days * 1440)), t_out=t_true, rh=w["rh"],
        ghi=w["ghi"], poa_s=w["poa_s"], poa_e=w["poa_e"], poa_w=w["poa_w"], local_hour=lh,
        dist=X.synthetic_disturbance(grid, seed) if hp is None else X.bootstrap_disturbance(grid, seed, hp),
        pv=X.pv_from_ghi(w["ghi"]), outdoor_base=base, dhw_requests=X.synthetic_dhw_requests(grid, seed),
        x0=None, t_out_init=X.ewma_outdoor(t0), seed=seed, description=sc.description,
        t_out_era5=w["t_out"], n_tail=int(round(sc.runout_days * 1440)),
    )


def _build_recorded(sc: Scenario, variant: str, seed: int) -> Exo:
    d = X.minute_data()
    T = d["time_epoch_s"].astype(float)
    i0 = int(np.searchsorted(T, epoch(sc.start)))
    i1 = int(np.searchsorted(T, epoch(sc.end)))
    sl = slice(i0, i1)
    grid = T[sl]
    _, hp = plant(variant)
    tr = X.recorded_house_track(hp)
    if int(tr["t"][i0]) != int(T[i0]):
        raise RuntimeError("recorded track and minute grid disagree")
    f = lambda k: np.nan_to_num(d[k][sl].astype(float))  # noqa: E731
    t_out = X.ffill(d["wx_t"][sl])
    ghi = f("wx_ghi")
    pv = d["pv_kw"][sl].astype(float)
    pv = np.where(np.isfinite(pv), pv, X.pv_from_ghi(ghi))
    # recorded registers (forward-filled through link gaps)
    sp = X.ffill(d["setpoint"][:i1])[i0:]
    delta = X.ffill(d["restart_delta"][:i1], 5.0)[i0:]
    mode = X.ffill(d["heating_mode"][:i1], 4.0)[i0:]
    quiet = X.ffill(d["quiet"][:i1], 0.0)[i0:]
    sp = np.where(np.isfinite(sp), sp, 30.0)
    regs = []
    last = None
    for k in range(len(grid)):
        cur = (float(sp[k]), float(delta[k]), bool(mode[k] == 4), bool(quiet[k] > 0.5))
        if cur != last:
            regs.append((float(grid[k]),) + cur)
            last = cur
    reqs = [(s - i0, n) for s, n in X.recorded_dhw_requests(i0, i1)]
    t_hist = X.ffill(d["wx_t"][max(0, i0 - 5 * 1440):i0 + 1])
    return Exo(
        name=sc.name, grid=grid, n_warm=0, t_out=t_out, rh=X.ffill(d["wx_rh"][sl]), ghi=ghi,
        poa_s=f("poa_s"), poa_e=f("poa_e"), poa_w=f("poa_w"), local_hour=X.local_hour(grid),
        dist=tr["dist"][sl].astype(float), pv=pv, outdoor_base=X.outdoor_sensor_base(t_out, seed),
        dhw_requests=reqs, x0=tr["X"][i0].astype(float),
        qbar0=float(X.ewma(tr["q"][:i0 + 1], X.ANCHOR_TAU_MIN, 2.0)[-1]),
        t_ew0=float(X.ewma(t_hist, X.ANCHOR_TAU_MIN, float(t_hist[0]))[-1]), t_out_era5=t_out,
        registers=dict(setpoint=float(sp[0]), restart_delta=float(delta[0]), quiet=bool(quiet[0] > 0.5),
                       heating_enabled=bool(mode[0] == 4)),
        context=dict(recorded_registers=regs, recorded_window=(i0, i1)), seed=seed, description=sc.description,
    )


def steady(t_out: float, days: float = 14.0, rh: float = 85.0, x0=None, start: str = "2026-01-05T00:00Z",
           warmup_days: float = 0.0, seed: int = 0) -> Exo:
    """Constant-weather scenario for sweeps: fixed outdoor temperature and humidity, no sun, no
    disturbance, no hot water (the daily internal-gain profile of the house model still runs).
    `x0` sets the initial house state (default: quasi-steady at 22 degC)."""
    t0 = epoch(start) - warmup_days * 86400.0
    grid = np.arange(t0, epoch(start) + days * 86400.0, 60.0)
    n = len(grid)
    z = np.zeros(n)
    t = np.full(n, float(t_out))
    return Exo(name=f"steady_{t_out:+.0f}C", grid=grid, n_warm=int(round(warmup_days * 1440)), t_out=t,
               rh=np.full(n, float(rh)), ghi=z, poa_s=z, poa_e=z, poa_w=z, local_hour=X.local_hour(grid), dist=z,
               pv=z, outdoor_base=t, dhw_requests=[], x0=None if x0 is None else np.asarray(x0, float),
               t_out_init=float(t_out), seed=seed, description=f"steady {t_out:+.1f} degC, RH {rh:.0f} %")
