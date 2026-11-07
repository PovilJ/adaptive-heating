"""Archived forecasts for the site from Open-Meteo's previous-runs API (no API key), stdlib only.

    python3 lab/data/forecast_pull.py

For every valid hour the API returns the value of the latest run (`..._previous_day0`, lead
0-23 h from the 00 UTC run of the same day in practice), the run one day earlier (`day1`, lead
24-47 h) and two days earlier (`day2`, lead 48-71 h). Comparing them with the ERA5 archive gives
the forecast error by lead time and, because the three values for one valid hour come from
different issues, how strongly errors are shared between issues (review round 2, N9).

Writes .local/lab-data/weather/previous_runs.json (private: site coordinates in the request).
"""
import datetime as dt
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / ".local" / "lab-data"
OUT = DATA / "weather" / "previous_runs.json"
START = dt.date(2025, 10, 1)
VARS = ("temperature_2m", "cloud_cover", "shortwave_radiation", "relative_humidity_2m")


def get(url, params, tries=4):
    full = url + "?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(full, timeout=180) as response:
                return json.load(response)
        except Exception as error:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            print("retry", type(error).__name__, str(error)[:200])
            time.sleep(5 * (attempt + 1))


def main():
    site = json.loads((DATA / "site.json").read_text())
    end = dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)
    hourly = []
    for v in VARS:
        hourly += [v] + [f"{v}_previous_day{k}" for k in (1, 2)]
    out = {"hourly": {}}
    a = START
    while a <= end:
        b = min(a + dt.timedelta(days=60), end)
        r = get("https://previous-runs-api.open-meteo.com/v1/forecast",
                {"latitude": site["lat"], "longitude": site["lon"], "hourly": ",".join(hourly),
                 "timezone": "UTC", "start_date": a.isoformat(), "end_date": b.isoformat()})
        for k, vals in r["hourly"].items():
            out["hourly"].setdefault(k, []).extend(vals)
        print(a, b, len(r["hourly"]["time"]))
        a = b + dt.timedelta(days=1)
    OUT.write_text(json.dumps(out))
    print("wrote", OUT, len(out["hourly"]["time"]), "hours")


if __name__ == "__main__":
    main()
