"""Hourly weather for the site from Open-Meteo (no API key), stdlib only.

    python3 lab/data/weather_pull.py

Reads the rounded site location from .local/lab-data/site.json and writes
.local/lab-data/weather/{archive,historical_forecast,forecast}.json plus one merged
hourly CSV (weather_hourly.csv). All times are UTC.

Sources
- archive:              ERA5/ERA5-Land reanalysis (archive-api), ~5 day delay.
- historical_forecast:  archived high-resolution model runs (historical-forecast-api),
                        kept as an independent second opinion.
- forecast:             forecast API with past_days=14, covers the last days and +2 days.
Radiation and precipitation values are means/sums over the PRECEDING hour (Open-Meteo
convention); temperature, humidity, cloud cover, wind and snow depth are instantaneous.
"""
import csv
import datetime as dt
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / ".local" / "lab-data"
OUT = DATA / "weather"
START = dt.date(2025, 10, 1)
VARS = ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "shortwave_radiation", "direct_radiation",
        "diffuse_radiation", "direct_normal_irradiance", "cloud_cover", "wind_speed_10m", "wind_direction_10m",
        "precipitation", "snowfall", "snow_depth", "surface_pressure"]


def get(url, params, tries=4):
    full = url + "?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(full, timeout=120) as response:
                return json.load(response)
        except Exception as error:
            if attempt == tries - 1:
                raise
            print("retry", type(error).__name__, str(error)[:200])
            time.sleep(5 * (attempt + 1))


def main():
    site = json.loads((DATA / "site.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    today = dt.datetime.now(dt.timezone.utc).date()
    base = {"latitude": site["lat"], "longitude": site["lon"], "hourly": ",".join(VARS), "timezone": "UTC",
            "wind_speed_unit": "ms"}
    pulls = {
        "archive": ("https://archive-api.open-meteo.com/v1/archive",
                    {**base, "start_date": START.isoformat(), "end_date": (today - dt.timedelta(days=2)).isoformat()}),
        "historical_forecast": ("https://historical-forecast-api.open-meteo.com/v1/forecast",
                                {**base, "start_date": START.isoformat(), "end_date": today.isoformat()}),
        "forecast": ("https://api.open-meteo.com/v1/forecast", {**base, "past_days": 14, "forecast_days": 2}),
    }
    frames = {}
    for name, (url, params) in pulls.items():
        data = get(url, params)
        data["_pulled_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        (OUT / f"{name}.json").write_text(json.dumps(data))
        hourly = data["hourly"]
        frames[name] = {t: {v: hourly.get(v, [None] * len(hourly["time"]))[i] for v in VARS}
                        for i, t in enumerate(hourly["time"])}
        valid = [t for t, row in frames[name].items() if row["temperature_2m"] is not None]
        print(f"{name}: {len(hourly['time'])} hours, valid temperature {valid[0] if valid else '-'} .. {valid[-1] if valid else '-'}"
              f"; model elevation {data.get('elevation')} m")
    # merged table: archive first, forecast for hours the archive does not have yet.
    times = sorted(set(frames["archive"]) | set(frames["forecast"]))
    with open(OUT / "weather_hourly.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_utc", "source"] + VARS + [f"hf_{v}" for v in ("temperature_2m", "shortwave_radiation", "cloud_cover")])
        for t in times:
            row, src = frames["archive"].get(t), "archive"
            if row is None or row["temperature_2m"] is None:
                row, src = frames["forecast"].get(t), "forecast"
            if row is None or row["temperature_2m"] is None:
                continue
            hf = frames["historical_forecast"].get(t, {})
            w.writerow([t + ":00Z", src] + [row[v] for v in VARS] +
                       [hf.get(v) for v in ("temperature_2m", "shortwave_radiation", "cloud_cover")])
    print("weather_hourly.csv:", len(times), "hours")


if __name__ == "__main__":
    main()
