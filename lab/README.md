# Offline control lab

An independent lab for testing new heat-pump control strategies against a calibrated simulator of
this house and its Gree Versati air-to-water heat pump. It does not reuse the integration's controller
code or model; the plant is built from measured data and physics.

- `data/`: read-only pulls from Home Assistant and Open-Meteo, and the builders for the aligned
  datasets. See `docs/research/lab/data.md`. The Home Assistant pull and build scripts are
  owner-only and not committed (they name the house's entities and need a private helper with
  the Home Assistant URL and token); `common.py` and the Open-Meteo pulls are.
- `sim/unit.py`: 1-minute water-side model of the Versati (firmware on/off rules, capacity
  control, COP, defrost, hot-water interplay) with robustness variants. Evidence and validation:
  `docs/research/lab/UNIT_MODEL.md`. `sim/unit_analysis.py` recomputes every number from the
  data, `sim/validate_unit.py` replays the recorded setpoints, `sim/r32.py` holds refrigerant
  properties used only by the analysis.

- `sim/simulator.py` + `sim/interface.py` + `sim/scenarios.py` + `sim/metrics.py` + `sim/ranking.py`:
  the closed-loop simulator, metrics, ranking rules and experiment harness that controller authors
  use (below). Evidence and validation: `docs/research/lab/SIMULATOR.md`.
- `controllers/`: baseline controllers (stdlib only), the warm-up/run-out `reference`, the ranking
  baseline `reference_tuned`, and `probes.py` (controllers that try to game the metrics, used by
  `validate_sim review`). `production` drives the integration's own controller file
  (`custom_components/adaptive_heating/slab.py`, 0.6.0) with the coordinator's input mapping;
  see `docs/CONTROLLER.md`.
- `run.py`: the command line.

Private data and results never live here: datasets go to `.local/lab-data/`, results to
`.local/lab-results/` (both gitignored). The site location is read from `.local/lab-data/site.json`.

Run the data stage (owner only; the first four scripts are not in the repository):

```
.local/ha-test-venv/bin/python lab/data/ha_discover.py
.local/ha-test-venv/bin/python lab/data/ha_pull.py history
.local/ha-test-venv/bin/python lab/data/ha_pull.py stats5
.local/ha-test-venv/bin/python lab/data/ha_pull.py hourly
.local/ha-test-venv/bin/python lab/data/ha_pull.py series
python3 lab/data/weather_pull.py
python3 lab/data/forecast_pull.py      # archived forecasts (forecast-error calibration)
.local/lab-venv/bin/python lab/data/build_datasets.py
.local/lab-venv/bin/python lab/data/describe.py
```

Later stages load the minute grid with `lab/data/common.py: load_minute()`.

Unit model:

```
.local/lab-venv/bin/python -m lab.sim.unit             # physics self-check
.local/lab-venv/bin/python -m lab.sim.unit_analysis    # evidence -> .local/lab-results/unit/analysis.json
.local/lab-venv/bin/python -m lab.sim.unit_analysis review   # review-round-1 fits only (COP, frost, surge, start cost)
.local/lab-venv/bin/python -m lab.sim.unit_analysis review2  # review-round-2 fits (frost removal, part-load bounds; ~25 min)
.local/lab-venv/bin/python -m lab.sim.validate_unit [variant]
```

House model:

```
.local/lab-venv/bin/python -m lab.sim.house                     # physics self-check
.local/lab-venv/bin/python -m lab.sim.house_prep                # identification inputs (private)
.local/lab-venv/bin/python -m lab.sim.house_ident compare       # structure comparison
.local/lab-venv/bin/python -m lab.sim.house_ident fit           # central joint fit + variants
.local/lab-venv/bin/python -m lab.sim.house_ident hourly        # cold-season energy check
.local/lab-venv/bin/python -m lab.sim.house_ident disturbance   # residual heat -> .local/lab-data
```

`sim/house.py` is the grey-box loop + slab + room + envelope + thermometer model; evidence and
validation in `docs/research/lab/HOUSE_MODEL.md`.

## Testing a controller in the simulator

### Write one

A controller is a plain Python class (stdlib only: no numpy) with a `name`, `reset(params)` and
`step(obs) -> Command`. `step` is called once per simulated minute with an `Observation`, the
values Home Assistant would show at that moment (`lab/sim/interface.py`):

- room: `room` (0.1 °C, last reported value), `room_age_min`, `target`;
- weather: `outdoor` (the unit's own sensor: noisy, warm in sun), `forecast` (48 hourly dicts:
  time, outdoor, rh, ghi, dni, dhi, cloud);
- water: `outlet`, `inlet`;
- unit: `setpoint`, `restart_delta`, `quiet`, `heating_enabled`, `compressor_on`, `mode`
  (heat / dhw / defrost / idle / off);
- electricity: `electric_kw`, `energy_kwh`;
- other: `pv_kw`, `time` (UTC), `local_hour`, `minute`, `link_ok`.

You never see the true air, slab or heat output.

Return `Command()` to change nothing, or set any of `setpoint`, `restart_delta`, `quiet`,
`heating_enabled`. The command acts from the minute that follows the observation. Values are
clamped to the unit's registers: setpoint 20-55 °C in whole degrees, hysteresis 2-10 K. Every
field that changes a register counts as a write.

```python
# lab/controllers/my_curve.py
from lab.sim.interface import Command, Observation


class MyCurve:
    name = "my_curve"

    def reset(self, params: dict) -> None:
        self.slope = float(params.get("slope", 0.35))
        self.trim = 0.0

    def step(self, obs: Observation) -> Command:
        if obs.minute % 30:                      # decide every 30 minutes
            return Command()
        t_next = sum(h["outdoor"] for h in obs.forecast[:6]) / 6
        if obs.room is not None:
            self.trim += 0.2 * (obs.target - obs.room)
        sp = 22 + self.slope * (22 - t_next) + self.trim
        return Command(setpoint=round(sp))


CONTROLLER = MyCurve
```

### Run it

```
.local/lab-venv/bin/python lab/run.py --list
.local/lab-venv/bin/python lab/run.py -c my_curve -s jan_cold                       # one run: table + JSON + per-minute CSV
.local/lab-venv/bin/python lab/run.py -c my_curve -s all -p slope=0.4 --forecast noisy
.local/lab-venv/bin/python lab/run.py --compare -c my_curve,unit_curve,room_thermostat,"fixed_setpoint[setpoint=30]" -s all
.local/lab-venv/bin/python lab/run.py --compare -c my_curve,unit_curve -s season --variant nominal,low_flow,minute_only,sluggish
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,my_curve -s season --seeds 0-1 --robust   # the ranking
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,my_curve -s weeks --seeds 0-4              # diagnostics
```

- **Controller specs:** a name in `lab/controllers/`, `pkg.module:Class` or `path/file.py:Class`.
  Per-controller parameters go in brackets, `name[k=v,k=v]`, and `--param k=v` applies to all.
- **Scenarios:**
  - `recorded`, `recorded_c2`, `recorded_spring`: recorded weather, hot water and disturbances,
    starting from the recorded state;
  - seven archive weeks: `oct_mild`, `nov_mixed`, `dec_damp`, `jan_cold`, `feb_sunny_cold`,
    `mar_shoulder`, `apr_mild_sunny`;
  - `recorded_a0`: the cold week of February 2026 (only 3 clean days; validation);
  - `season`: 2025-10-15 .. 2026-04-15, the primary ranking;
  - groups: `all` = recorded + weeks, `weeks`, `everything`.

  Archive scenarios have a 3-day warm-up under `controllers/reference.py` before the window and a
  3-day run-out under it after the window, both outside the window metrics, so every controller
  starts from the same state and pays back the heat it leaves in the house. `--seed` / `--seeds`
  redraws the hot water, the disturbance bootstrap, the local weather departure and the noisy
  forecast.
- **Forecast:** `--forecast noisy` is the default (the ranking setting), calibrated on the site's
  archived forecasts, with errors shared between successive issues; `pessimistic` (errors x1.5)
  and `perfect` for checks.
- **Link outages:** `--link-drops measured` is the default: Modbus outages at the heating-season
  rate and lengths of the record (0.34 a day, median 32 min). During one the observation repeats
  stale unit values, `link_ok` is False and commands wait. `--link-drops 0` switches them off; the
  variant token `long_outage` adds a 3-day outage (fail-safe check).
- **Variants:** unit (`low_flow`, `high_flow`, `shallow_outlet`, `steep_outlet`, `partload_lo`,
  `partload_hi`, `flat_load`, `legacy_cop`, `legacy_frost`, `legacy_frost_r1`, `legacy_surge`,
  `surge_from_start`, `high_start_loss`, `sluggish`, `more_frost`, `less_frost`, `frost_melt_lo`,
  `frost_melt_hi`, `frost_no_melt`, `quiet_frost`, `pump_always_on`) and house (`heavy_slab`,
  `light_slab`, `loss_plus20`, `loss_minus20`, `sun_plus30`, `sun_minus30`, `minute_only`).
  Combine a unit and a house variant with `+`. Flag tokens: `raw_return` (no return anchoring),
  `anchor_heat` (old heat-based anchoring), `era5_only` (no local weather departure),
  `synthetic_dist` (parametric disturbance instead of the recorded-day bootstrap),
  `sparse_thermometer` (20-min minimum report gap), `forecast_pessimistic` (forecast errors
  x1.5), `long_outage` (a 3-day Modbus outage from the middle of the window).
- **Ranking** (`--rank`, `lab/sim/ranking.py`; review round 2): paired against the first
  controller (use `reference_tuned`) over the seeds, 90 % intervals, in % of the baseline's
  window electricity. Energy, comfort and starts are kept apart:
  - adjusted energy = normalised energy (`elec_norm_kwh`) + 0.54 kWh per K-hour of
    |air - target| (`comfort_kh`; the baseline's own price of comfort) + c kWh per start;
  - verdict `better` only if the interval is below zero at both c = 0.05 and c = 0.3 kWh per
    start; the break-even start cost, energy alone, the comfort difference and starts per day of
    both are reported next to it;
  - constraints: mean air within ±0.05 K of target, mean |error| at most the baseline's + 0.05 K,
    at most 8 starts and 48 writes a day;
  - the ranking must be `better` on every mandatory variant (`--robust`, 20: `nominal`,
    `partload_lo`, `partload_hi`, `legacy_cop`, `high_start_loss`, `sluggish`, `raw_return`,
    `minute_only`, `low_flow`, `high_flow`, `loss_minus20`, `steep_outlet`, `shallow_outlet`,
    `frost_melt_lo`, `frost_melt_hi`, `light_slab`, `heavy_slab`, `sun_plus30`, `sun_minus30`,
    `forecast_pessimistic`).

  The season is the primary ranking; use 5 or more seeds for weeks. The verdict lines at the end
  of the table summarise each candidate over the variants.
- **Output:** results go to `.local/lab-results/runs/`:
  - `<scenario>__<controller>__<variant>__<forecast>.json` (meta + metrics);
  - `.csv` (per minute: weather, room sensor and true air, slab, water temperatures, registers,
    mode, heat, electricity, writes);
  - in compare mode, `compare_<time>.txt/.json`.

  The season takes about 3 s per controller, and compare mode runs in parallel. From Python:
  `lab.sim.harness.run_one(...)` / `run_many(...)`, or `lab.sim.simulator.run(controller, exo)`
  with `exo = lab.sim.scenarios.build("jan_cold")`.

### Read the metrics

- **`elec_kwh`:** the metered outdoor unit over the window, split into `elec_heat_kwh` and
  `elec_dhw_kwh`. The unmetered indoor pump (`indoor_kwh`) and tank heater are reported
  separately. `cop_space` = loop heat / space-heating electricity.
- **`elec_norm_kwh`: the number to minimise.** Window plus the common run-out, normalised to the
  target mean air (`norm/d` in the table divides it by window + run-out days). Also
  `storage_delta_kwh`, `elec_corr_kwh`, `elec_runout_kwh`. Week energy without this is dominated by
  heat left in the slab and envelope: 0.1 K of mean air moved it 2-4.5 %.
- **Comfort:** `mean_air`, `mae_air` (mean |error|, symmetric), `comfort_kh` (K-hours of
  |error|, the ranking's comfort quantity), `rms_air`, `min_air`,
  `room_0700_air_mean`; `dh_below_air` / `dh_above_air` (degree-hours outside ± 0.5 K) are
  information only. The `_sensor` versions use the thermometer.
- **Flags** (`assumption_flags`, last table column): the run relied on ASSUMED or never-recorded
  behaviour (`quiet`, `restart_delta`, `setpoint_range`, `min_off`, `heating_off`,
  `runs_lt_15min`, `starts_gt_8`, `writes_gt_48`). Such a result is a hypothesis to test on the
  real unit, not a ranking. In the ranking, `setpoint_range` is shown only when the candidate
  spends more time outside 25-39 °C than the baseline (the baseline is clamped at 25 °C).
- **Cold share:** `elec_by_outdoor` splits the energy at -4 and +4 °C daily mean. A season
  advantage that comes mostly from days below -4 °C is flagged `cold_share`: that regime has 3
  clean days of closed-loop validation.
- **Cycling:** `starts_per_day`, `starts_by_outdoor` (per daily-mean outdoor bucket),
  `run_min_median`, `runs_under_15_pct` / `runs_under_30_pct` / `runs_under_60_pct`. The simulator
  under-predicts starts by about 15-18 %, so read them relatively.
- **Water:** `mean_outlet_running`, `anchor_mean_running_k` (the return offset the unit saw),
  `mean_setpoint` / `max_setpoint`, `writes_per_day`.
- **Other:** `defrosts`, `defrost_elec_kwh`, `dhw_energy_kwh`, `per_day` rows.

### What the simulator does NOT model, or only assumes

Details and evidence: `docs/research/lab/SIMULATOR.md`, section 7.

- One room thermometer (the living room). No zones, no room thermostats, no window contacts or
  occupancy.
- Water temperatures are anchored to the measured ones by an empirical offset that depends on the
  weather-driven load (SIMULATOR.md section 3). Absolute water temperatures are uncertain to about
  ±0.5 K.
- The cold regime has 3 clean days of closed-loop validation, where the simulator used 10-19 %
  more electricity than the real unit.
- Compressor starts are under-predicted by about 15-18 %, and long runs are too long. Outcomes of
  setpoint drops written within about 0.5 K of the stop threshold (t_ctrl ≥ setpoint + 2 K) are
  not reliable. Mild-weather defrosts are over-predicted in closed loop (longer runs keep more of
  the frost-trigger state).
- The room agreement of the recorded replays is by construction (the recorded disturbance is the
  residual that reproduces the recorded room). Without the recorded room the house follows it to
  0.35-0.5 K RMS; with other days' disturbances 0.7-1.0 K. Responses to heating patterns unlike
  the recorded controllers' are extrapolated.
- Loop flow is assumed at 29 L/min (25-33 in the variants). Absolute heat and COP scale with it.
- ASSUMED firmware behaviour (flagged in every result): quiet mode (capacity x 0.7), restart
  hysteresis other than 4/5 K, minimum off time (3 min), space heating switched off (pump stops,
  3-minute purge), tank-heater rating (2 kW for 23 min), setpoints outside 25-39 °C, more than 8
  starts a day. The frost-trigger loss while the compressor is off is fitted, with mandatory
  bounds.
- Not simulated: backup heaters, legionella cycles, anti-freeze, the unit's internal curve and
  room modes.
- Hot water is exogenous (recorded or drawn from recorded days). Controllers cannot move it, and
  it does not depend on tank temperature.
- Disturbances are model residuals, recorded, or recorded days bootstrapped into archive weather.
  They are not causal people, airing or cooking events.
- Weather is ERA5-like plus a measured local departure (SD 1.1 K) that the forecast does not
  know. The noisy forecast is synthetic but calibrated on archived forecasts (temperature SD
  1.2 K at 12 h, 1.6 K at 36 h, errors shared between issues). The outdoor sensor is
  statistical (noise + night bias + sun bias, no lag).
- PV comes from global irradiance in archive scenarios. There are no tariffs, no grid and no
  self-consumption accounting.
- Electricity is the outdoor-unit meter. The indoor unit and tank heater are added by assumption.
- Sensor faults: Modbus outages at the measured rate (default), a 3-day outage check
  (`long_outage`); no frozen or biased sensors.
- Wear is not folded into energy: rankings must hold for 0.05-0.3 kWh per start; comfort is
  priced at the baseline's own trade (0.54 kWh per K-hour), not at the owner's preference.

Simulator self-check and validation:

```
.local/lab-venv/bin/python -m lab.sim.simulator
.local/lab-venv/bin/python -m lab.sim.validate_sim [replay|season|sweeps|speed|normalisation|review|house|comfort|review2|all]
```

## Review fixes (round 1)

An adversarial review of the simulator found four critical and seven major issues. All were
fixed from the data or, where the data cannot say, made explicit, conservative and switchable.
Details and new numbers: `docs/research/lab/SIMULATOR.md` section 9, `UNIT_MODEL.md` section 13,
`HOUSE_MODEL.md` section 11.

- **COP model** (C1, C4): smooth in outdoor temperature (no staircase), peaks at mid output and
  stays flat above the measured 95th percentile of output, with an explicit coil-frost term.
  `flat_load` and `legacy_cop` (the old model) are mandatory ranking variants.
- **Defrost** (C2): frost per kWh drawn from the air, not per run-minute; period A 115 vs 119
  defrosts.
- **Ranking energy** (C3, m4): heat left in the house is paid back by a common 3-day run-out;
  energy normalised to the target mean air; symmetric comfort (`mae_air`); mean-air constraint;
  a tuned room-holding baseline (`reference_tuned`); the season is primary. 'Heating off for the
  last 18 h' went from -13 % to -0.3 ± 0.9 %.
- **Cycling** (M1, m1): 0.2 kWh per start in the score, flags beyond 8 starts a day; a begun
  pre-start finishes. Restart_delta 2 now costs +4-6 % energy (+15-31 % score).
- **Anchoring** (M2) depends on the weather-driven load, not on the heat a controller delivers.
- **Cold regime** (M3): replay of the cold week A0 and per-bucket replay tables; `cold_share`
  flag.
- **Space heating off** (M4): the pump stops (ASSUMED, flagged).
- **Weather** (M5): local departure from ERA5; noisy forecast by default.
- **Seeds** (M6): `--seeds`, paired 90 % intervals; recorded-day disturbance bootstrap with the
  recorded day-to-day persistence.
- **Surge** (M7) by preceding compressor power. **Flags** (m2) in every result. **Thermometer**
  (m3) hourly-report model.

## Review fixes (round 2)

A second adversarial review found three critical and four major issues, plus three minor ones.
All were fixed from the data or, where the data cannot say, made explicit, conservative and
switchable. Details and new numbers: `docs/research/lab/SIMULATOR.md` section 10,
`UNIT_MODEL.md` section 14, `HOUSE_MODEL.md` section 12.

- **Frost** (N1): the defrost-trigger state loses up to 40 % over each compressor-off block and
  no defrost comes within 50 compressor minutes of the last; K refitted per minute temperature on
  all 186 inter-defrost segments (timing decides the loss share: 'kept while off' is clearly
  worse; counts by outdoor band and on/off class set K). `frost_melt_lo` / `frost_melt_hi`
  mandatory, `frost_no_melt` diagnostic.
- **Comfort in the ranking** (N2): 0.54 kWh per K-hour of |air - target| (the baseline's own
  price of comfort), mean air within ±0.05 K, mean |error| within baseline + 0.05 K; the baseline
  gains re-chosen (kp 3, ki 0.3). Day/night comfort trades went from wins of -0.6..-0.8 % to
  -0.1 % ± 2.6-4.6 (undecided) over the season.
- **Part load** (N3): `flat_load` (rejected by the data) replaced in the mandatory set by
  `partload_lo` / `partload_hi` (part-load slope x0.5 / x1.5, refitted). Long low-power runs are
  now decidable: better by 4.0 ± 1.5 % on every mandatory variant in the damp December week.
- **Start cost** (N4): a verdict must hold at 0.05 and 0.3 kWh per start; break-even start cost
  and starts per day are reported, not folded into efficiency.
- **House validation** (N5): the replay's room agreement is by construction; without the recorded
  room the house follows it to 0.35-0.5 K RMS (0.7-1.0 K with other days' disturbances).
- **Stops** (N6): no firmware stop rule is missing (5 of 231 natural stops unexplained); the
  120-minute surge timer restarts after a defrost; the control-sensor offset depends on output.
- **Mandatory variants and cache** (N7): slab, sun, frost and pessimistic-forecast variants added
  (20 in all); cache files built under a lock with atomic rename.
- **Minor** (N8-N10): baseline setpoints clamped at 25 °C and `setpoint_range` shown relative to
  the baseline; the forecast error calibrated on archived forecasts with errors shared between
  issues; measured link outages on by default.
