"""Shared helpers for the lab data pipeline (numpy only, no pandas).

Conventions used everywhere in the lab datasets:
- All timestamps are UTC. CSV times are ISO strings ending in 'Z'; arrays use epoch seconds.
- A Home Assistant state is a step function: it holds from the time it was recorded until the
  next recorded state. 'unavailable'/'unknown'/null states are gaps (NaN), never carried forward.
"""
import datetime as dt
import gzip
import json
import math
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / ".local" / "lab-data"
RAW = DATA / "raw"
RESULTS = ROOT / ".local" / "lab-results"
UTC = dt.timezone.utc
INVALID = {"unavailable", "unknown", "none", "", "null"}


def iso(ts):
    return dt.datetime.fromtimestamp(float(ts), UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_min(ts):
    return dt.datetime.fromtimestamp(float(ts), UTC).strftime("%Y-%m-%dT%H:%MZ")


def epoch(text):
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def read_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def series_ids():
    return sorted(p.name[: -len(".json.gz")] for p in (RAW / "series").glob("*.json.gz"))


def friendly_names():
    return {s["entity_id"]: s.get("name") or "" for s in json.loads((RAW / "states_index.json").read_text())}


def find_ids(pattern, ids=None, names=None):
    """Entity ids whose id (or friendly name, when `names` is given) matches the regex."""
    ids = series_ids() if ids is None else ids
    rx = re.compile(pattern, re.I)
    if names is not None:
        return [e for e in ids if rx.search(names.get(e, ""))]
    return [e for e in ids if rx.search(e)]


def is_valid(state):
    return state is not None and str(state).strip().lower() not in INVALID


def to_float(state):
    if not is_valid(state):
        return math.nan
    try:
        return float(state)
    except (TypeError, ValueError):
        return math.nan


def to_bin(state):
    s = str(state).lower() if state is not None else ""
    return 1.0 if s == "on" else 0.0 if s == "off" else math.nan


def sample(t, v, grid):
    """Value of the step function (t, v) at each grid time; NaN before the first event."""
    t = np.asarray(t, float)
    v = np.asarray(v)
    k = np.searchsorted(t, grid, side="right") - 1
    if v.dtype.kind in "fc":
        out = np.full(len(grid), np.nan)
    else:
        out = np.full(len(grid), "", dtype=object)
    ok = k >= 0
    out[ok] = v[k[ok]]
    return out


def last_event_age_min(t_events, grid):
    """Minutes since the most recent event at or before each grid time (NaN before the first)."""
    t_events = np.asarray(t_events, float)
    k = np.searchsorted(t_events, grid, side="right") - 1
    out = np.full(len(grid), np.nan)
    ok = k >= 0
    out[ok] = (grid[ok] - t_events[k[ok]]) / 60.0
    return out


def interval_mean(t, v, edges):
    """Time-weighted mean of a step function over consecutive intervals [edges[i], edges[i+1]).

    NaN parts of the step function are excluded; returns (mean, valid_seconds)."""
    t = np.asarray(t, float)
    v = np.asarray(v, float)
    edges = np.asarray(edges, float)
    valid = ~np.isnan(v)
    vv = np.where(valid, v, 0.0)
    gaps = np.diff(t)
    cum_i = np.concatenate([[0.0], np.cumsum(vv[:-1] * gaps)])
    cum_w = np.concatenate([[0.0], np.cumsum(valid[:-1] * gaps)])
    k = np.searchsorted(t, edges, side="right") - 1
    before = k < 0
    kk = np.clip(k, 0, None)
    integral = cum_i[kk] + vv[kk] * (edges - t[kk])
    weight = cum_w[kk] + valid[kk] * (edges - t[kk])
    integral[before] = 0.0
    weight[before] = 0.0
    num = np.diff(integral)
    den = np.diff(weight)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(den > 0, num / den, np.nan)
    return mean, den


def integrate(t, v, a, b):
    """Integral of the step function over [a, b] (value-seconds), ignoring NaN parts."""
    mean, w = interval_mean(t, v, np.array([a, b], float))
    return float(np.nan_to_num(mean[0]) * w[0]), float(w[0])


def solar_position(ts, lat, lon):
    """Sun elevation and azimuth (degrees, azimuth clockwise from north) for UTC epoch seconds.

    NOAA solar calculator equations (Meeus low-precision series: geometric mean longitude,
    equation of centre, apparent longitude, obliquity, equation of time). Geometric elevation:
    no refraction correction. Accuracy about 0.01-0.02 degrees for years 1950-2050."""
    ts = np.asarray(ts, float)
    jc = (ts / 86400.0 + 2440587.5 - 2451545.0) / 36525.0
    l0 = np.radians((280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360)
    m = np.radians(357.52911 + jc * (35999.05029 - 0.0001537 * jc))
    e = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)
    c = (np.sin(m) * (1.914602 - jc * (0.004817 + 0.000014 * jc)) + np.sin(2 * m) * (0.019993 - 0.000101 * jc)
         + np.sin(3 * m) * 0.000289)
    omega = np.radians(125.04 - 1934.136 * jc)
    app_long = np.radians(np.degrees(l0) + c - 0.00569 - 0.00478 * np.sin(omega))
    obliq = 23 + (26 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60) / 60
    obliq = np.radians(obliq + 0.00256 * np.cos(omega))
    decl = np.arcsin(np.sin(obliq) * np.sin(app_long))
    y = np.tan(obliq / 2) ** 2
    eqtime = 4 * np.degrees(y * np.sin(2 * l0) - 2 * e * np.sin(m) + 4 * e * y * np.sin(m) * np.cos(2 * l0)
                            - 0.5 * y * y * np.sin(4 * l0) - 1.25 * e * e * np.sin(2 * m))
    minutes = (ts % 86400.0) / 60.0
    tst = (minutes + eqtime + 4 * lon) % 1440
    ha = np.radians(tst / 4 - 180)
    phi = np.radians(lat)
    cosz = np.sin(phi) * np.sin(decl) + np.cos(phi) * np.cos(decl) * np.cos(ha)
    elev = np.degrees(np.arcsin(np.clip(cosz, -1, 1)))
    az = np.degrees(np.arctan2(np.sin(ha), np.cos(ha) * np.sin(phi) - np.tan(decl) * np.cos(phi))) + 180.0
    return elev, az % 360.0


def toa_horizontal(ts, elev_deg):
    """Extraterrestrial irradiance on a horizontal plane, W/m2."""
    days = np.asarray(ts, float) / 86400.0
    doy = (days % 365.2422)  # phase only matters for the 3% eccentricity term
    e0 = 1 + 0.033 * np.cos(2 * np.pi * doy / 365.2422 - 2 * np.pi * 3 / 365.2422)
    return 1361.0 * e0 * np.clip(np.sin(np.radians(elev_deg)), 0, None)


def load_minute(path=None):
    """Load minute.npz (fast path for later lab stages) into a dict of arrays."""
    path = path or DATA / "minute.npz"
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}
