"""Exogenous inputs of the closed-loop simulator: weather, sun, forecasts, hot water,
disturbances, PV and the unit's outdoor-sensor error.

Everything here is independent of the controller. Arrays are on a 1-minute UTC grid of epoch
seconds. Private inputs are read from `.local/lab-data/` (weather, site, minute grid) and cached
results go to `.local/lab-results/sim/cache/`.

Sources and the numbers behind each synthetic generator:
- weather: Open-Meteo hourly (ERA5 archive / forecast), turned into minutes exactly as the data
  stage does (linear temperature/humidity, clearness-index reshaping of the hourly radiation means,
  facade irradiance with an isotropic sky and albedo 0.2/0.6 on snow), so the house model sees the
  same kind of input it was fitted on.
- hot water: requests (start, compressor minutes) replayed from the record, or whole recorded days
  drawn at random (bootstrap of the heating-season days with complete unit data).
- disturbance (residual heat into the room-air node, kW): either re-derived for the chosen house
  parameters by deadbeat tracking of the recorded room (the same method as HOUSE_MODEL.md section
  7, so the recorded room is reproduced exactly under the recorded heat), or synthetic: hourly
  profile (weekday/weekend) + seasonal offset + hourly AR(1) + Poisson events (HOUSE_MODEL.md).
- PV: recorded, or 8.9 kW per kW/m2 of global irradiance capped at 9.2 kW (least squares on the
  minute data, RMSE 0.9 kW).
- outdoor sensor: ERA5 + slow local deviation (AR(1), SD 1.0 K, 3 h) + sun warming (median idle
  bias +0.8 K at 100-300 W/m2 and +4.3 K above 300 W/m2 global irradiance; much less while
  running), quantized to 0.5 K. Measured on the minute grid against ERA5.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import os
from contextlib import contextmanager
from functools import lru_cache
from zoneinfo import ZoneInfo

import numpy as np

from lab.data.common import DATA, RESULTS, epoch, solar_position, toa_horizontal

TZ = ZoneInfo("Europe/Vilnius")
CACHE = RESULTS / "sim" / "cache"
UTC = dt.timezone.utc


# ------------------------------------------------------------------------------------------
# site and hourly weather
# ------------------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def site():
    return json.loads((DATA / "site.json").read_text())


@lru_cache(maxsize=1)
def weather_hourly():
    """Hourly Open-Meteo table as arrays. Stamps are UTC hour ends for radiation (preceding-hour
    means) and instants for temperature/humidity/cloud."""
    with open(DATA / "weather" / "weather_hourly.csv") as f:
        rows = list(csv.DictReader(f))

    def get(k):
        return np.array([float(r[k]) if r[k] not in ("", "None") else np.nan for r in rows])

    w = dict(
        t=np.array([epoch(r["time_utc"]) for r in rows]),
        t2m=get("temperature_2m"), rh=get("relative_humidity_2m"), dew=get("dew_point_2m"),
        ghi=get("shortwave_radiation"), dhi=get("diffuse_radiation"), dni=get("direct_normal_irradiance"),
        cloud=get("cloud_cover"), wind=get("wind_speed_10m"), snow=get("snow_depth"),
        archive=np.array([r["source"] == "archive" for r in rows]),
    )
    return w


def local_hour(grid):
    """Europe/Vilnius clock hour (float) for each epoch second (DST-correct per hour block)."""
    grid = np.asarray(grid, float)
    out = np.empty(len(grid))
    i0 = 0
    n = len(grid)
    while i0 < n:
        ts = dt.datetime.fromtimestamp(float(grid[i0]), TZ)
        off = ts.utcoffset().total_seconds()
        # the offset is constant to the end of this UTC hour
        h_end = (math.floor(grid[i0] / 3600.0) + 1) * 3600.0
        i1 = int(np.searchsorted(grid, h_end, side="left"))
        i1 = max(i1, i0 + 1)
        out[i0:i1] = ((grid[i0:i1] + off) % 86400.0) / 3600.0
        i0 = i1
    return out


def local_day_index(grid):
    """Integer local (Europe/Vilnius) day number for each epoch second."""
    grid = np.asarray(grid, float)
    lh = local_hour(grid)
    # local midnight = time - local_hour hours
    return np.floor((grid - lh * 3600.0 + 1800.0) / 86400.0).astype(np.int64)


def weather_minute(grid):
    """Minute weather on `grid` (epoch seconds, 60 s step) from the hourly table, the same way
    lab/data/build_datasets.py builds the minute grid's wx_* and poa_* columns."""
    w = weather_hourly()
    s = site()
    grid = np.asarray(grid, float)
    elev, az = solar_position(grid + 30.0, s["lat"], s["lon"])
    toa = toa_horizontal(grid + 30.0, elev)
    ht = w["t"]

    def lin(vals, at=grid, times=ht):
        ok = ~np.isnan(vals)
        return np.interp(at, times[ok], vals[ok])

    res = dict(t_out=lin(w["t2m"]), rh=lin(w["rh"]), cloud=lin(w["cloud"]), wind=lin(w["wind"]),
               snow=lin(w["snow"]), sun_elev=elev, sun_az=az)
    k_hour = np.clip(np.searchsorted(ht, grid + 60.0, side="left"), 1, len(ht) - 1)
    sums = np.bincount(k_hour, weights=toa, minlength=len(ht))
    counts = np.bincount(k_hour, minlength=len(ht))
    with np.errstate(invalid="ignore", divide="ignore"):
        toa_hour = np.where(counts > 0, sums / np.maximum(counts, 1), np.nan)
    # hours not covered by the grid: hourly mean of the extraterrestrial irradiance from 6 samples
    miss = counts == 0
    if miss.any():
        tt = ht[miss][:, None] - 3600.0 + np.arange(5, 3600, 600)[None, :]
        e2, _ = solar_position(tt.ravel(), s["lat"], s["lon"])
        toa_hour[miss] = toa_horizontal(tt.ravel(), e2).reshape(tt.shape).mean(axis=1)
    centers = ht - 1800.0
    out_rad = {}
    for key in ("ghi", "dhi"):
        vals = w[key]
        with np.errstate(invalid="ignore", divide="ignore"):
            kt = np.where(toa_hour > 5.0, vals / toa_hour, np.nan)
        kt = np.clip(kt, 0, 1.2)
        valid = ~np.isnan(kt)
        i = np.arange(len(kt))
        ff = np.where(valid, i, -1)
        np.maximum.accumulate(ff, out=ff)
        bf = np.minimum.accumulate(np.where(valid, i, len(kt))[::-1])[::-1]
        use_ff = (ff >= 0) & ((bf >= len(kt)) | (i - ff <= bf - i))
        src_i = np.where(use_ff, ff, bf)
        kt_f = kt[np.clip(src_i, 0, len(kt) - 1)]
        out_rad[key] = np.nan_to_num(np.interp(grid + 30.0, centers, kt_f) * toa)
    ghi = out_rad["ghi"]
    dhi = np.minimum(out_rad["dhi"], ghi)
    sin_e = np.sin(np.radians(elev))
    with np.errstate(invalid="ignore", divide="ignore"):
        dni = np.where(elev > 2.0, (ghi - dhi) / sin_e, 0.0)
    dni = np.clip(np.nan_to_num(dni), 0, 1050)
    albedo = np.where(res["snow"] > 0.02, 0.6, 0.2)
    res.update(ghi=ghi, dhi=dhi, dni=dni)
    for name, face in (("poa_s", 180.0), ("poa_e", 90.0), ("poa_w", 270.0)):
        cos_inc = np.cos(np.radians(elev)) * np.cos(np.radians(az - face))
        beam = dni * np.clip(cos_inc, 0, None) * (elev > 0)
        res[name] = beam + dhi / 2 + ghi * albedo / 2
    return res


def ewma_outdoor(t_start, tau_h=450.0):
    """Exponentially weighted mean of the hourly outdoor temperature before t_start (time constant
    of the house envelope), used for a quasi-steady initial state."""
    w = weather_hourly()
    m = (w["t"] <= t_start) & np.isfinite(w["t2m"])
    if not m.any():
        return 5.0
    age_h = (t_start - w["t"][m]) / 3600.0
    wt = np.exp(-age_h / tau_h)
    return float(np.sum(wt * w["t2m"][m]) / np.sum(wt))


# ------------------------------------------------------------------------------------------
# forecasts
# ------------------------------------------------------------------------------------------

# Forecast error model (review round 2, N9), calibrated on the site's archived forecasts
# (lab/data/forecast_pull.py: Open-Meteo previous-runs, heating season 2025/26) against ERA5:
# - temperature error SD 1.17 K for the latest run (lead 0-23 h), 1.70 K one day earlier; errors of
#   the two issues at the same valid hour correlate 0.78, and the day-earlier error is the latest
#   one plus a nearly independent increment (SD 1.07 K, correlation 0.15 with it). Along valid time
#   the latest-run error decorrelates to 0.45 within 6 h but keeps ~0.3 for 2-5 days;
# - so: error = bias(hour, lead) + a(lead) x shared(valid time) + issue-specific(lead), with the
#   shared part a slow AR(1) (SD 0.6 K, 120 h) plus a fast one (SD 0.85 K, 4 h), a(lead) = 1 ->
#   1.15 at 36 h, and the issue-specific part AR(1) along lead (phi 0.95), SD 0.2 K -> 1.1 K at
#   36 h -> 1.4 K at 48 h. Simulated over the season (3 seeds): SD 1.0-1.1 / 1.2 / 1.4 / 1.6 / 1.8 K
#   at 1 / 12 / 24 / 36 / 48 h, correlation 0.63-0.70 between issues a day apart (measured 0.78);
# - mean bias by UTC hour (forecast minus ERA5, -0.55..+0.13 K for lead < 24 h, -0.65..-0.14 K
#   beyond);
# - global irradiance lognormal SD 0.40 -> 0.50 (measured log-ratio SD 0.42-0.45 in daylight),
#   cloud SD 30 -> 38 %-points (measured 35-37), humidity 8 -> 10 %-points (measured 9). These
#   are issue-specific (sharing between issues not calibrated).
# 'pessimistic' (flag token forecast_pessimistic): every error and bias x 1.5.
FC_BIAS_D0 = (-0.17, -0.13, -0.09, -0.1, -0.07, -0.1, -0.23, -0.4, -0.55, -0.45, -0.48, -0.52, -0.37, -0.38, -0.3,
              -0.02, 0.12, 0.13, -0.03, -0.05, -0.1, -0.18, -0.18, -0.16)
FC_BIAS_D1 = (-0.33, -0.29, -0.26, -0.14, -0.14, -0.21, -0.33, -0.54, -0.65, -0.63, -0.6, -0.55, -0.51, -0.5, -0.45,
              -0.35, -0.24, -0.2, -0.39, -0.44, -0.48, -0.48, -0.46, -0.4)
FC_SHARED_SLOW = (0.6, 120.0)  # SD K, time constant h
FC_SHARED_FAST = (0.85, 4.0)


class Forecast:
    """48-hour hourly forecast seen by controllers.

    'perfect': the weather series itself. 'noisy' (default) and 'pessimistic' (errors x 1.5):
    issued every 6 h (00/06/12/18 UTC) with the calibrated error model above. A shared error
    component depends on the valid time only, so successive issues make correlated errors (an
    average over issues does not cancel them); the issue-specific part depends on (seed, issue
    time). Two controllers with the same seed see the same forecast."""

    HOURS = 48

    def __init__(self, mode="perfect", seed=0):
        if mode not in ("perfect", "noisy", "pessimistic"):
            raise ValueError(f"forecast mode {mode!r}")
        self.mode = mode
        self.scale = 1.5 if mode == "pessimistic" else 1.0
        self.seed = seed
        w = weather_hourly()
        self.w = w
        self.t = w["t"]
        self._cache_hour = None
        self._cache_val = ()
        self._issue_cache = {}
        s = site()
        el, _ = solar_position(self.t - 1800.0, s["lat"], s["lon"])
        self.clear = 1.0 * toa_horizontal(self.t - 1800.0, el) * 0.80  # rough clear-sky cap
        self.hod = ((self.t // 3600) % 24).astype(int)
        if mode != "perfect":
            n = len(self.t)
            rng = np.random.default_rng([seed, 717])
            shared = np.zeros(n)
            for sd, tau in (FC_SHARED_SLOW, FC_SHARED_FAST):
                phi = math.exp(-1.0 / tau)
                z = rng.standard_normal(n)
                a = np.empty(n)
                a[0] = z[0]
                c = math.sqrt(1 - phi * phi)
                for i in range(1, n):
                    a[i] = phi * a[i - 1] + c * z[i]
                shared += sd * a
            self.shared = shared

    def _errors(self, issue_ts):
        key = int(issue_ts)
        e = self._issue_cache.get(key)
        if e is not None:
            return e
        n = self.HOURS + 7
        rng = np.random.default_rng([self.seed, key // 3600])

        def ar(phi):
            z = rng.standard_normal(n)
            out = np.empty(n)
            out[0] = z[0]
            c = math.sqrt(1 - phi * phi)
            for i in range(1, n):
                out[i] = phi * out[i - 1] + c * z[i]
            return out

        k = self.scale
        lead = np.arange(n, dtype=float)
        s_t = 0.2 + 0.9 * np.minimum(lead, 36) / 36 + 0.3 * np.clip(lead - 36, 0, 12) / 12
        a_t = 1.0 + 0.15 * np.minimum(lead, 36) / 36
        s_c = 30.0 + 8.0 * np.minimum(lead, 48) / 48
        s_g = 0.40 + 0.10 * np.minimum(lead, 48) / 48
        s_h = 8.0 + 2.0 * np.minimum(lead, 48) / 48
        zc = ar(0.8)
        zg = -0.7 * zc + math.sqrt(1 - 0.49) * ar(0.8)
        sg = k * s_g
        e = dict(t=k * s_t * ar(0.95), a=k * a_t, c=k * s_c * zc, g=np.exp(sg * zg - 0.5 * sg ** 2), h=k * s_h * ar(0.9))
        if len(self._issue_cache) > 64:
            self._issue_cache.clear()
        self._issue_cache[key] = e
        return e

    def at(self, ts):
        """Forecast tuple for the minute starting at epoch ts (cached per hour)."""
        hour = int(ts // 3600)
        if hour == self._cache_hour:
            return self._cache_val
        h_next = (hour + 1) * 3600.0
        i0 = int(np.searchsorted(self.t, h_next, side="left"))
        i1 = min(i0 + self.HOURS, len(self.t))
        w = self.w
        idx = range(i0, i1)
        if self.mode == "perfect":
            vals = tuple(dict(time=dt.datetime.fromtimestamp(float(self.t[i]), UTC),
                              outdoor=float(w["t2m"][i]), rh=float(w["rh"][i]), ghi=float(w["ghi"][i]),
                              dni=float(w["dni"][i]), dhi=float(w["dhi"][i]), cloud=float(w["cloud"][i]))
                         for i in idx)
        else:
            issue = math.floor(ts / 21600.0) * 21600.0
            e = self._errors(issue)
            out = []
            for i in idx:
                L = int(round((self.t[i] - issue) / 3600.0))
                L = min(max(L, 0), len(e["t"]) - 1)
                ghi, dhi, dni = float(w["ghi"][i]), float(w["dhi"][i]), float(w["dni"][i])
                f = float(e["g"][L])
                ghi_f = min(ghi * f, max(float(self.clear[i]), ghi))
                fr = ghi_f / ghi if ghi > 1e-6 else 1.0
                dhi_f = min(dhi * math.sqrt(fr), ghi_f)
                beam = ghi - dhi
                dni_f = dni * (ghi_f - dhi_f) / beam if beam > 1e-6 else 0.0
                bias = (FC_BIAS_D0 if L < 24 else FC_BIAS_D1)[self.hod[i]] * self.scale
                out.append(dict(time=dt.datetime.fromtimestamp(float(self.t[i]), UTC),
                                outdoor=float(w["t2m"][i] + bias + e["a"][L] * self.shared[i] + e["t"][L]),
                                rh=float(min(max(w["rh"][i] + e["h"][L], 20.0), 100.0)),
                                ghi=ghi_f, dni=max(dni_f, 0.0), dhi=dhi_f,
                                cloud=float(min(max(w["cloud"][i] + e["c"][L], 0.0), 100.0))))
            vals = tuple(out)
        self._cache_hour = hour
        self._cache_val = vals
        return vals


# ------------------------------------------------------------------------------------------
# recorded minute data helpers
# ------------------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def minute_data():
    from lab.data.common import load_minute
    return load_minute()


def ffill(x, default=np.nan):
    x = np.asarray(x, float).copy()
    ok = np.isfinite(x)
    if not ok.any():
        return np.full(len(x), default)
    idx = np.where(ok, np.arange(len(x)), 0)
    np.maximum.accumulate(idx, out=idx)
    out = x[idx]
    out[: np.argmax(ok)] = x[np.argmax(ok)]
    return out


def _runs(mask):
    m = np.r_[False, np.asarray(mask, bool), False].astype(np.int8)
    dd = np.diff(m)
    return list(zip(np.flatnonzero(dd == 1), np.flatnonzero(dd == -1)))


def recorded_dhw_requests(i0=None, i1=None):
    """Hot-water requests from the record as (minute index on the minute grid, compressor minutes).
    The request starts when the unit was told to go to the tank: at the DHW compressor start, or
    earlier at the stop of a heat run that the request pre-empted (within the 7-minute pause)."""
    d = minute_data()
    st = d["unit_status"]
    comp = np.nan_to_num(d["compressor"])
    dhw = (st == "HOT WATER") & (comp == 1)
    out = []
    for a, b in _runs(dhw):
        start = a
        lo = max(0, a - 7)
        prior = np.flatnonzero(comp[lo:a] == 1)
        if len(prior):
            start = lo + int(prior[-1]) + 1
        out.append((int(start), int(b - a)))
    if i0 is not None:
        out = [(s, n) for s, n in out if i0 <= s < i1]
    return out


@lru_cache(maxsize=1)
def dhw_day_library():
    """Recorded hot-water days for bootstrap: list of [(local minute of day, compressor minutes)],
    one per local day with heating on and >= 97 % unit data."""
    d = minute_data()
    t = d["time_epoch_s"].astype(float)
    day = local_day_index(t)
    lh = local_hour(t)
    ok = np.nan_to_num(d["versati_ok"]) == 1
    mode = ffill(d["heating_mode"], 4.0)
    reqs = recorded_dhw_requests()
    by_day = {}
    for s, n in reqs:
        by_day.setdefault(int(day[s]), []).append((int(round(lh[s] * 60)), n))
    lib = []
    for u in np.unique(day):
        w = day == u
        if w.sum() < 1380 or ok[w].mean() < 0.97 or (mode[w] != 4).any():
            continue
        lib.append(sorted(by_day.get(int(u), [])))
    return lib


def synthetic_dhw_requests(grid, seed):
    """Bootstrap whole recorded days of hot-water requests. Returns [(grid index, minutes)]."""
    lib = dhw_day_library()
    rng = np.random.default_rng([seed, 101])
    day = local_day_index(grid)
    lh = local_hour(grid)
    out = []
    for u in np.unique(day):
        idx = np.flatnonzero(day == u)
        first = idx[0]
        midnight = grid[first] - lh[first] * 3600.0
        for minute_of_day, n in lib[int(rng.integers(len(lib)))]:
            ts = midnight + minute_of_day * 60.0
            k = int(round((ts - grid[0]) / 60.0))
            if 0 <= k < len(grid):
                out.append((k, n))
    return sorted(out)


# ------------------------------------------------------------------------------------------
# disturbances
# ------------------------------------------------------------------------------------------

_DEFAULT_STATS = dict(
    hourly_profile_w=dict(
        weekday=[-157, -82, -3, 86, 130, 115, -86, -317, -374, -384, -386, -565, -213, -304, -482, -404, -312,
                 236, 151, -101, -130, -155, -197, -210],
        weekend=[-130, -32, 34, 216, 208, 125, -112, -67, 284, -304, -804, -944, -236, 83, -352, -663, -508,
                 -329, 215, 162, 0, 2, -7, -53]),
    hourly_after_profile=dict(sd_w=1120.0, ar1_phi=0.62),
    events_pos=dict(per_day=1.77, minutes_p50=63.0, minutes_p90=185.3, kwh_p50=1.72, kwh_p90=6.54,
                    start_hour_hist=[5, 7, 41, 35, 33, 52, 21, 4]),
    events_neg=dict(per_day=2.38, minutes_p50=64.0, minutes_p90=212.4, kwh_p50=1.9, kwh_p90=8.22,
                    start_hour_hist=[3, 0, 82, 54, 49, 41, 28, 10]),
)
# daily-mean residual by month (HOUSE_MODEL.md section 7: spring about -0.33 kW, Oct-Nov +0.06 to
# +0.15 kW, the cold week near 0); applied instead of the all-season profile mean
MONTH_OFFSET_KW = {1: 0.0, 2: 0.0, 3: -0.2, 4: -0.33, 5: -0.33, 9: 0.1, 10: 0.1, 11: 0.1, 12: 0.0}
# day-to-day part (review round 1): the synthetic generator without it gave a daily-mean SD of
# 0.36-0.40 kW against 0.52 recorded (HOUSE_MODEL.md section 7); the recorded daily means have a
# lag-1 correlation of 0.72 (109 day pairs). SD of the added daily AR(1): sqrt(0.52^2 - 0.38^2).
DAILY_AR_SD_KW = 0.35
EVENT_SMOOTH_MIN = 30
DAILY_AR_PHI = 0.72


@lru_cache(maxsize=1)
def disturbance_stats():
    path = RESULTS / "house" / "disturbance_stats.json"
    try:
        s = json.loads(path.read_text())
        if "hourly_profile_w" in s and "events_pos" in s:
            return s
    except (OSError, ValueError):
        pass
    return _DEFAULT_STATS


def _lognormal(rng, p50, p90, size):
    sig = max(math.log(max(p90, p50 * 1.01) / p50) / 1.2816, 1e-3)
    return p50 * np.exp(sig * rng.standard_normal(size))


def synthetic_disturbance(grid, seed):
    """Residual heat into the room-air node (kW per minute) for a synthetic scenario."""
    st = disturbance_stats()
    rng = np.random.default_rng([seed, 202])
    n = len(grid)
    lh = local_hour(grid)
    day = local_day_index(grid)
    # weekday from local day number (1970-01-01 was a Thursday -> weekday 3)
    wd = (day + 3) % 7
    weekend = wd >= 5
    pw = np.array(st["hourly_profile_w"]["weekday"], float) / 1000.0
    pe = np.array(st["hourly_profile_w"]["weekend"], float) / 1000.0
    allmean = (5 * pw.mean() + 2 * pe.mean()) / 7
    # smooth profile: bins centred at h + 0.5, periodic linear interpolation
    xs = np.r_[np.arange(24) + 0.5 - 24, np.arange(24) + 0.5, np.arange(24) + 0.5 + 24]
    prof = np.where(weekend, np.interp(lh, xs, np.tile(pe, 3)), np.interp(lh, xs, np.tile(pw, 3))) - allmean
    months = np.array([dt.datetime.fromtimestamp(float(x), UTC).month for x in grid[::1440]])
    month = np.repeat(months, 1440)[:n]
    offset = np.array([MONTH_OFFSET_KW.get(int(m), 0.0) for m in month])
    # events
    ev = np.zeros(n)
    n_days = n / 1440.0
    for key, sign in (("events_pos", 1.0), ("events_neg", -1.0)):
        e = st[key]
        k = rng.poisson(e["per_day"] * n_days)
        hist = np.array(e["start_hour_hist"], float)
        hist = hist / hist.sum()
        bins = rng.choice(len(hist), size=k, p=hist)
        width = 24.0 / len(hist)
        hours = (bins + rng.random(k)) * width
        days = rng.integers(0, max(int(math.ceil(n_days)), 1), size=k)
        dur = np.clip(_lognormal(rng, e["minutes_p50"], e["minutes_p90"], k), 15, 600).astype(int)
        kwh = _lognormal(rng, e["kwh_p50"], e["kwh_p90"], k)
        kw = np.clip(kwh / (dur / 60.0), 0.3, 6.0)
        lh0 = lh[0]
        for dd, hh, du, p in zip(days, hours, dur, kw):
            k0 = int(round((dd * 24 + hh - lh0) * 60))
            if k0 >= n or k0 + du <= 0:
                continue
            ev[max(k0, 0):min(k0 + du, n)] += sign * p
    if EVENT_SMOOTH_MIN > 1:
        # event edges ramp over EVENT_SMOOTH_MIN minutes (energy kept): sharp steps gave the
        # synthetic disturbance ~3x the recorded minute-to-minute variation (review round 1, m3)
        from scipy.ndimage import uniform_filter1d
        ev = uniform_filter1d(ev, EVENT_SMOOTH_MIN, mode="constant")
    # day-to-day persistence (review round 1): a daily AR(1) (phi 0.72, measured lag-1 correlation
    # of the recorded daily means) sized so that the daily-mean SD matches the recorded 0.52 kW
    nd = int(math.ceil(n / 1440)) + 2
    zd = rng.standard_normal(nd)
    dm = np.empty(nd)
    dm[0] = zd[0] * DAILY_AR_SD_KW
    cd = math.sqrt(1 - DAILY_AR_PHI ** 2) * DAILY_AR_SD_KW
    for i in range(1, nd):
        dm[i] = DAILY_AR_PHI * dm[i - 1] + cd * zd[i]
    daily = np.interp(np.arange(n) / 1440.0, np.arange(nd) - 0.5, dm)
    # AR(1) hourly part, scaled so that events + daily + AR together have the measured hourly SD
    nh = int(math.ceil(n / 60)) + 2
    ev_h = np.add.reduceat(ev, np.arange(0, n, 60)) / 60.0
    var_ev = float(np.var(ev_h)) if len(ev_h) > 10 else 0.0
    sd_tot = st["hourly_after_profile"]["sd_w"] / 1000.0
    phi = st["hourly_after_profile"]["ar1_phi"]
    sd_ar = math.sqrt(max(sd_tot ** 2 - var_ev - DAILY_AR_SD_KW ** 2, 0.3 ** 2))
    z = rng.standard_normal(nh)
    a = np.empty(nh)
    a[0] = z[0] * sd_ar
    c = math.sqrt(1 - phi * phi) * sd_ar
    for i in range(1, nh):
        a[i] = phi * a[i - 1] + c * z[i]
    ar = np.interp(np.arange(n) / 60.0, np.arange(nh) - 0.5, a)
    return prof + offset + ev + ar + daily


@lru_cache(maxsize=4)
def _dist_day_library(house_key):
    hp = _HP_BY_KEY[house_key]
    tr = recorded_house_track(hp)
    d = minute_data()
    t = d["time_epoch_s"].astype(float)
    day = local_day_index(t)
    lh = local_hour(t)
    ok = (np.nan_to_num(d["versati_ok"]) == 1) & np.isfinite(d["room"].astype(float))
    mode = ffill(d["heating_mode"], 4.0)
    dist = np.asarray(tr["dist"], float)
    days, arrs = [], []
    for u in np.unique(day):
        w = np.flatnonzero(day == u)
        if len(w) < 1380 or ok[w].mean() < 0.97 or (mode[w] != 4).any() or not np.any(dist[w]):
            continue
        month = dt.datetime.fromtimestamp(float(t[w[0]]) + 43200, UTC).month
        mins = np.clip(np.round(lh[w] * 60).astype(int), 0, 1439)
        prof = np.full(1440, np.nan)
        prof[mins] = dist[w] - MONTH_OFFSET_KW.get(month, 0.0)
        prof = ffill(prof, 0.0)
        days.append(int(u))
        arrs.append(prof)
    return np.array(days), np.array(arrs)


_HP_BY_KEY = {}


def bootstrap_disturbance(grid, seed, hp):
    """Residual heat for an archive scenario drawn from the recorded residual (review round 1):
    whole recorded local days (heating on, >= 97 % unit data, room data) of the house track for
    these house parameters, chained as a Markov bootstrap: with probability DAILY_AR_PHI the next
    day is the recorded day that followed, otherwise a random day. Recorded month offsets are
    swapped for the target month's. Jumps between unrelated days are cross-faded over 30 minutes.
    This keeps the recorded minute, hourly and day-to-day statistics by construction (the
    parametric generator, `synthetic_dist` flag, under-states day-to-day persistence and
    over-states hour-to-hour variation)."""
    key = _house_key(hp)
    _HP_BY_KEY[key] = hp
    days, arrs = _dist_day_library(key)
    rng = np.random.default_rng([seed, 909])
    dayset = {int(u): i for i, u in enumerate(days)}
    n = len(grid)
    lh = local_hour(grid)
    tday = local_day_index(grid)
    out = np.zeros(n)
    cur = None
    prev_end = None
    for u in np.unique(tday):
        idx = np.flatnonzero(tday == u)
        if cur is not None and rng.random() < DAILY_AR_PHI and (days[cur] + 1) in dayset:
            cur = dayset[days[cur] + 1]
            jump = False
        else:
            cur = int(rng.integers(len(days)))
            jump = True
        month = dt.datetime.fromtimestamp(float(grid[idx[0]]) + 43200, UTC).month
        mins = np.clip(np.round(lh[idx] * 60).astype(int), 0, 1439)
        seg = arrs[cur][mins] + MONTH_OFFSET_KW.get(month, 0.0)
        if jump and prev_end is not None:
            m = min(30, len(seg))
            f = np.arange(1, m + 1) / (m + 1.0)
            seg[:m] = (1 - f) * prev_end + f * seg[:m]
        out[idx] = seg
        prev_end = float(seg[-1])
    return out


def _house_key(hp):
    from dataclasses import asdict
    d = asdict(hp)
    d.pop("ranges", None)
    return hashlib.sha1(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()[:12]


def recorded_house_track(hp):
    """Deadbeat tracking of the recorded room through the whole minute record with the recorded
    loop heat, for house parameters `hp` (cached). Returns dict(t, dist, X, names): the residual
    heat (kW per minute, applied over minute k) and the model state at the start of every minute.
    Under the recorded heat this reproduces the recorded room exactly; the state at any minute is
    the 'recorded state' a closed-loop replay starts from."""
    from lab.sim import house as H
    from lab.sim import house_ident as HI

    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"track_{_house_key(hp)}_a{ANCHOR_VERSION}.npz"
    # review round 2 (N7): parallel workers used to race on this file (a reader could load a
    # half-written one). Build under an exclusive lock and publish with an atomic rename.
    with cache_lock(path):
        if path.exists():
            with np.load(path) as z:
                return {k: z[k] for k in z.files} | {"names": list(H.state_names(hp))}
        out = _track_build(hp)
        tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
        with open(tmp, "wb") as f:
            np.savez_compressed(f, **{k: v for k, v in out.items() if k != "names"})
        os.replace(tmp, path)
    return out


@contextmanager
def cache_lock(path):
    """Exclusive inter-process lock for building a cache file (POSIX flock on a side file)."""
    import fcntl
    lock = path.with_name(path.name + ".lock")
    with open(lock, "a+") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _track_build(hp):
    from lab.sim import house as H
    from lab.sim import house_ident as HI
    d = HI.Data()
    U = HI._glow_input(d.U, hp.glow_src)
    target = HI.reconstruct_room(d.room)
    i0 = int(np.argmax(~np.isnan(target)))
    h = H.House(hp)
    h.reset(float(target[i0]), t_out=ewma_outdoor(float(d.t[i0])))
    dist_k, X, names = HI.track(hp, U[i0:], target[i0:], 1.0 / 60.0, x0=h.x.copy())
    dist = np.zeros(d.n)
    dist[i0:] = dist_k
    Xa = np.empty((d.n, len(names)))
    Xa[:i0] = X[0]
    Xa[i0:] = X
    out = dict(t=d.t.astype(np.int64), dist=dist, X=Xa.astype(np.float32), q=d.U[:, 0].astype(np.float32))
    out.update(_anchor_fit(hp, d, Xa, names))
    return out | {"names": names}


ANCHOR_TAU_MIN = 1440.0  # EWMA time constant of the loop heat that the return anchoring uses
ANCHOR_KNOTS = np.arange(0.25, 6.01, 0.5)


def ewma(x, tau_min, x0):
    from scipy.signal import lfilter
    a = 1.0 / tau_min
    return lfilter([a], [1.0, -(1.0 - a)], np.asarray(x, float), zi=[(1.0 - a) * x0])[0]


def weather_load(hp, t_out, tau_min=None, t0=None):
    """Weather-driven steady loop heat (kW) for the house at 22 degC, from the exponential mean
    (24 h) of the outdoor temperature. The return anchoring is a function of this (review round 1:
    a state the controller cannot pump), not of the heat the controller delivered."""
    from lab.sim import house as H
    tau = ANCHOR_TAU_MIN if tau_min is None else tau_min
    t_out = np.asarray(t_out, float)
    tew = ewma(t_out, tau, t_out[0] if t0 is None else t0)
    tg = np.linspace(-30.0, 25.0, 56)
    qg = np.array([H.steady_heat(hp, 22.0, float(t)) for t in tg])
    return np.interp(tew, tg, qg), tew


def weather_load_table(hp):
    """(outdoor knots, steady heat) for the simulator's per-minute lookup."""
    from lab.sim import house as H
    tg = np.linspace(-30.0, 25.0, 111)
    return tg, np.array([H.steady_heat(hp, 22.0, float(t)) for t in tg])


def _anchor_fit(hp, d, X, names):
    """Return-temperature anchoring: recorded loop return minus the model's return when the
    model is driven with the recorded heat and tracks the recorded room, as a function of the
    24-hour mean loop heat. The house model's free-running water temperatures drift from the
    measured ones (about +1.4 K real-minus-model at 1-2 kW mean heat, -1.4 K at 4-5 kW, central
    fit), because its slab-to-room/ground structure cannot match the measured water-room relation
    at both ends of the load range. The simulator adds this offset to what the unit and the
    controller see (not to the house's heat balance), so the firmware's start/stop thresholds and
    the COP act on realistic water temperatures. Disable with the variant token 'raw_return'."""
    from lab.sim import house as H
    iw = names.index(f"w{hp.n_seg}")
    model_ret = np.r_[X[1:, iw], np.nan]
    ret = d.ret
    q = np.nan_to_num(d.U[:, 0])
    qbar = ewma(q, ANCHOR_TAU_MIN, 2.0)
    t_out = np.asarray(d.U[:, list(H.U_NAMES).index("t_out")], float)
    t_out = ffill(t_out, 5.0)
    qw, _ = weather_load(hp, t_out)
    e = ret - model_ret
    ok = np.isfinite(e)
    out = {}
    for tag, var in (("", qw), ("_heat", qbar)):
        b = np.full(len(ANCHOR_KNOTS), np.nan)
        cnt = np.zeros(len(ANCHOR_KNOTS))
        for i, c in enumerate(ANCHOR_KNOTS):
            m = ok & (np.abs(var - c) <= 0.5)
            cnt[i] = m.sum()
            if m.sum() >= 1440:
                b[i] = float(np.median(e[m]))
        good = np.isfinite(b)
        if good.sum() >= 2:
            b = np.interp(ANCHOR_KNOTS, ANCHOR_KNOTS[good], b[good])  # flat beyond the measured range
        else:
            b = np.zeros(len(ANCHOR_KNOTS))
        out[f"anchor_q{tag}"] = ANCHOR_KNOTS.copy()
        out[f"anchor_b{tag}"] = b
        out[f"anchor_minutes{tag}"] = cnt
    return out


ANCHOR_VERSION = 2  # 2: anchored on the weather-driven load (review round 1); cache key


def return_anchor(hp, on="weather"):
    """(knots kW, offset K) for house parameters hp. on='weather': knots of the weather-driven
    steady load (weather_load); on='heat': knots of the run's own 24-h mean loop heat (before
    review round 1, flag token 'anchor_heat')."""
    tr = recorded_house_track(hp)
    tag = "" if on == "weather" else "_heat"
    return np.asarray(tr[f"anchor_q{tag}"], float), np.asarray(tr[f"anchor_b{tag}"], float)


# ------------------------------------------------------------------------------------------
# PV and outdoor sensor
# ------------------------------------------------------------------------------------------

PV_KW_PER_GHI = 0.0089  # kW per W/m2 (least squares on the minute grid)
PV_MAX_KW = 9.2


def pv_from_ghi(ghi):
    return np.clip(PV_KW_PER_GHI * np.asarray(ghi, float), 0.0, PV_MAX_KW)


def _ar_minutes(n, seed_key, tau_min, sd, step_min=15):
    rng = np.random.default_rng(seed_key)
    nh = n // step_min + 2
    phi = math.exp(-step_min / tau_min)
    z = rng.standard_normal(nh)
    a = np.empty(nh)
    a[0] = z[0]
    c = math.sqrt(1 - phi * phi)
    for i in range(1, nh):
        a[i] = phi * a[i - 1] + c * z[i]
    return np.interp(np.arange(n) / step_min, np.arange(nh), a) * sd


def outdoor_sensor_base(t_out, seed, sd=1.0, ghi=None, night_bias=0.0):
    """Unit outdoor sensor before sun bias and quantisation: `t_out` + the sensor's own slow error
    (AR(1), 3 h). Recorded scenarios: SD 1.0 K around ERA5 (the house there is driven by ERA5 and
    the recorded disturbance already holds the local departure). Archive scenarios (review round
    1): `t_out` is the true local air (ERA5 + local departure) and the sensor's own error is SD
    0.8 K, with a -0.48 K bias at night (ghi < 1 W/m2); measured at night against ERA5 and the
    ventilation unit's intake sensor (SIMULATOR.md, review fixes)."""
    n = len(t_out)
    out = np.asarray(t_out, float) + _ar_minutes(n, [seed, 303], 180.0, sd)
    if ghi is not None and night_bias:
        out = out + np.where(np.asarray(ghi, float) < 1.0, night_bias, 0.0)
    return out


LOCAL_DEV_SD_K = 1.1   # shared night-time departure of the two local sensors from ERA5: cov 1.34 K^2
LOCAL_DEV_TAU_MIN = 360.0  # its autocovariance falls to 0.42 of lag 0 in 6 h (e-folding ~ 6-7 h)
SENSOR_OWN_SD_K = 0.8  # unit sensor's own error: var(unit - ERA5) 2.02 - shared 1.34 = 0.68 K^2
SENSOR_NIGHT_BIAS_K = -0.48


def local_deviation(n, seed):
    """True local air minus ERA5 (AR(1), SD 1.1 K, 6 h) for archive scenarios (review round 1)."""
    return _ar_minutes(n, [seed, 505], LOCAL_DEV_TAU_MIN, LOCAL_DEV_SD_K)


SUN_BIAS_IDLE = 0.012  # K per W/m2 of global irradiance while the compressor is off (cap 6 K)
SUN_BIAS_RUN = 0.003   # while running (fan draws ambient air over the sensor)


# ------------------------------------------------------------------------------------------
# Modbus link outages (review round 2, N10)
# ------------------------------------------------------------------------------------------

LINK_SEASON_WINDOWS = (("2026-02-08T00:00Z", "2026-05-01T00:00Z"), ("2026-10-08T00:00Z", "2026-11-07T00:00Z"))
LINK_MAX_MIN = 1440  # longer outages (the 10-day one in February 2026) belong to the long_outage check


@lru_cache(maxsize=1)
def link_outage_model():
    """(outages per day, durations in minutes) of the Versati Modbus link in the heating-season
    windows of the record (old and new bridge), from the minute grid's versati_ok flag. The
    May-September record (about 900 outages, mostly while the bridge was being reworked) is left
    out: it is not how the heating-season link behaves."""
    from lab.data.common import epoch as _ep
    d = minute_data()
    t = d["time_epoch_s"].astype(float)
    ok = np.nan_to_num(d["versati_ok"]) == 1
    durs, days = [], 0.0
    for a_, b_ in LINK_SEASON_WINDOWS:
        sel = (t >= _ep(a_)) & (t < _ep(b_))
        days += sel.sum() / 1440.0
        for a, b in _runs(sel & ~ok):
            if b - a <= LINK_MAX_MIN:
                durs.append(int(b - a))
    return len(durs) / max(days, 1e-9), tuple(sorted(durs))
