# Lab data stage

The lab compares new heat-pump control strategies offline, on a simulator calibrated to this house.
This page describes the measured data the simulator is built from: where it comes from, how it is
aligned, and what to watch out for. The data itself is private and stays in `.local/lab-data/`
(gitignored); its full data dictionary, per-column coverage and descriptive statistics are in
`.local/lab-data/README.md`.

## Sources

| source | how | span |
|---|---|---|
| Home Assistant recorder, raw states | `GET /api/history/period`, one request per entity group and UTC day, `significant_changes_only=0` | 2026-02-08 onward (the recorder keeps ~9 months, not ~10 days) |
| Home Assistant 5-minute statistics | websocket `recorder/statistics_during_period`, one statistic per call, month by month | same window as the raw states |
| Home Assistant long-term (hourly) statistics | same command, `period: hour` | from 2025-10 for energy, phase power and some temperature sensors |
| Open-Meteo | ERA5 archive, archived high-resolution forecasts, forecast API (`past_days=14`) | 2025-10-01 onward, hourly, UTC |
| Older ad-hoc pulls | `.local/analysis-2026-10-1x` | 2026-10-07..14 (inside the recorder window; merged, added no rows) |

All Home Assistant access is read-only: state and history GETs, statistics queries, nothing that
calls a service or changes a value.

## Pipeline (`lab/data/`)

| step | script | interpreter |
|---|---|---|
| list entities and statistic ids | `ha_discover.py` | `.local/ha-test-venv/bin/python` |
| pull raw history, 5-minute and hourly statistics, consolidate per entity | `ha_pull.py history`, `stats5`, `hourly`, `series` | same |
| pull weather | `weather_pull.py` | any Python 3 |
| build `minute.csv`/`minute.npz`, `hourly.csv`, `events.csv` | `build_datasets.py` | `.local/lab-venv/bin/python` (numpy) |
| write the private data dictionary and `daily_summary.csv` | `describe.py` | same |

The four Home Assistant scripts (`ha_discover.py`, `ha_pull.py`, `build_datasets.py`,
`describe.py`) are **owner-only and not in the repository** (`.gitignore`): they name the first
house's entities and import a private helper that holds the Home Assistant URL and token. The
committed `common.py`, `weather_pull.py` and `forecast_pull.py` carry no private data; the site
location is read from `.local/lab-data/site.json`. Without the private datasets the simulator
cannot run, so a clone of the repository can read the lab but not rerun it.

## Datasets

- **minute.csv / minute.npz**: 1-minute UTC grid over the raw window. Column groups: room and other
  indoor temperatures (with sensor ages), unit configuration registers (water setpoint, restart
  hysteresis, mode, DHW target, weather-curve registers), unit measurements (outlet, inlet, outdoor,
  refrigerant temperatures, tank), unit status / compressor / defrost / tank-heater flags, link
  availability, electricity (minute mean power, counter, phase powers), PV, ventilation, air
  conditioners, Open-Meteo weather, sun position and vertical-facade irradiance, and the previous
  controllers' commanded setpoint and mode (context only).
- **hourly.csv**: hourly UTC grid from 2025-10-01: metered electricity (with quality flags), room
  statistics, ventilation, PV, Open-Meteo (aligned to `[H, H+1h)`), and hourly aggregates of the
  minute grid.
- **events.csv**: compressor runs (heat/DHW), DHW runs, defrosts, tank-heater runs, power-only runs,
  link dropouts, frozen-meter stretches, setpoint and configuration writes.

## Alignment rules

- Everything is UTC. A Home Assistant state is a step function that holds until the next recorded
  state; Home Assistant records only changes. `unavailable`/`unknown` are gaps and are never carried
  forward. The synthetic row the history API inserts at each query start is removed.
- Power is integrated, not sampled: `elec_w` is the time-weighted mean over each minute.
- Open-Meteo radiation and precipitation are means/sums over the *preceding* hour. Hourly tables take
  them from the next stamp; the minute grid reshapes each hourly mean with the extraterrestrial
  irradiance (clearness index), which keeps the hourly mean. A cross-correlation of measured PV power
  against the result peaks within ~15 minutes of zero lag, which confirms the convention.
- Sun position uses the NOAA solar equations (agrees with Home Assistant's `sun.sun` to ~0.02 deg).
- Indoor sensors that stop changing for 24 h (48 h for humidity) are treated as dead and blanked,
  because Home Assistant keeps reporting the last value of a dead sensor.

## Things a model or controller study must not miss

- **The metered electricity is the outdoor unit only** (since 2025-12-18). The circulation pump,
  indoor electronics and the DHW tank electric heater are not metered; the tank heater runs most days
  after a DHW cycle.
- **Two sensor identity changes on 2026-10-22**: the living-room temperature entity name moved to a new
  device (the old device continues under a new name), and the heat pump's Modbus bridge was replaced
  (all unit entities changed prefix). The datasets merge both; `room` follows what the controllers
  saw and `room_old` keeps one device for the whole window.
- **Link quality**: the first Modbus bridge dropped out often (median ~11 min) and had multi-day
  outages, including a 10-day gap in a February cold spell. The replacement bridge has been clean.
  Filter on `versati_ok` before fitting anything on unit data; `power_run` events cover outages.
- **Meter defects**: the power sensor reported kW until 2026-10-08 (converted), and the meter froze a
  few times (one 30-hour stretch at a fake constant value). Frozen stretches are blanked and flagged.
- **Restart hysteresis changed** from 5 K to 4 K on 2026-10-21; any model of when the unit restarts
  must use the value in force.
- **Defrost**: the unit's defrost flag is reliable; a temperature signature (liquid pipe far below the
  outlet) confirms it with no false positives. Defrosts cannot be seen during link outages.
- **Outdoor temperature**: the unit's own sensor is sun-affected when idle and the ventilation unit's
  sensor reads warm (very warm in deep cold). ERA5 (`wx_t`) is the consistent reference; local
  sensors are useful as checks.
- **Air conditioners** can heat the living room directly (rare, logged from 2026-05-15). Check
  `ac_living_mode` before using room data to fit the house.
- **There is no flow meter**. Template heat-output and COP sensors in Home Assistant assume a fixed
  flow and are kept only as context.
- The previous controllers' decision texts and plans were deliberately not pulled: the lab builds the
  plant model from measurements and physics only.

## Archived forecasts (review round 2)

`python3 lab/data/forecast_pull.py` pulls Open-Meteo's previous-runs archive for the site
(temperature, humidity, cloud cover and global irradiance of the latest run and of the runs one
and two days earlier, for every hour from 2025-10-01) into
`.local/lab-data/weather/previous_runs.json` (private: the request carries the site
coordinates). The simulator's forecast error is calibrated on it against ERA5 (SIMULATOR.md
section 4).
