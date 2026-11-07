# Lab simulator: closed loop, scenarios, metrics and validation

The simulator joins the unit model ([UNIT_MODEL.md](UNIT_MODEL.md), `lab/sim/unit.py`) and the
house model ([HOUSE_MODEL.md](HOUSE_MODEL.md), `lab/sim/house.py`) into a closed loop at a
1-minute step, with a controller in the loop that sees only what Home Assistant shows. It is the
test bench on which new control strategies are compared. How to write and run a controller is in
`lab/README.md`. Like the two models, it was built from the measured data and physics only.

| file | what |
|---|---|
| `lab/sim/interface.py` | `Observation`, `Command`, `Controller` (stdlib only) |
| `lab/sim/simulator.py` | the closed loop, sensors, write counting, plant variants; self-check |
| `lab/sim/exogenous.py` | weather, forecasts, hot water, disturbances, PV, outdoor-sensor error, return anchoring |
| `lab/sim/scenarios.py` | named scenarios, warm-up, steady-weather builder for sweeps |
| `lab/sim/metrics.py` | metrics of a run and the summary table |
| `lab/sim/ranking.py` | ranking score, constraints, paired multi-seed comparison, tuned baseline, mandatory variants |
| `lab/sim/harness.py`, `lab/run.py` | controller loading, parallel runs, output files, CLI |
| `lab/controllers/` | `reference` (warm-up and run-out), `reference_tuned` (ranking baseline), `replay_recorded` (validation), `unit_curve`, `fixed_setpoint`, `room_thermostat`, `probes` (metric-gaming probes and the review-round-2 strategy shapes) |
| `lab/data/forecast_pull.py` | archived forecasts for the site (Open-Meteo previous runs), the calibration of the forecast error (section 4) |
| `lab/sim/validate_sim.py` | every number on this page (private output: `.local/lab-results/sim_validation/`) |

## 1. Summary

Numbers after review round 2 (section 10 lists what changed and why; section 9 round 1).

| item | result |
|---|---|
| Closed-loop replay of the recorded setpoints, current season (26 clean days) | electricity **+0.7 %** (daily mean absolute error 5.4 %), heat +2.1 %, mean outlet while running 30.68 vs 30.53 °C. Room thermometer RMS 0.19 K over 4 weeks, but **that agreement is by construction** (the recorded disturbance is the residual that makes the model follow the recorded room) |
| House response without the recorded room (section 6.1, review round 2) | the same replay with the residual replaced by its daily means: room RMS **0.35 K** (spring 0.53 K); by its window mean 0.49 / 0.72 K; by recorded days drawn from elsewhere in the record 0.68-0.82 / 0.91-0.97 K; electricity within 0-5 % |
| Same, new Modbus bridge only (12 days) | electricity -1.5 % (daily 4.3 %), room RMS 0.12 K |
| Same, late winter/spring 2026 (50 days) | electricity +2.7 %, heat +1.3 %, defrosts 102 vs 85, room RMS 0.38 K |
| Same, cold week A0 (3 clean days, -15 to +1 °C) | electricity **+11 %** (+8 % below 0 °C), heat +7.6 %, COP 2.48 vs 2.57, defrosts 29 vs 29: the cold regime is the least validated (section 6.1) |
| Compressor starts in replay | **18 % too few** (3.15 vs 3.85 a day in the current season, 0.85 in spring); runs too long at the 75th percentile (214 vs 150 min); mild-weather defrosts over-predicted (22 vs 7 in the current season) |
| Season, room-holding reference controller vs metered daily electricity in the same weather | medians within ±7 % of the meter in most 4-K outdoor bins for two seeds; -9 to -12 % at -12..-8 °C, -7 / -20 % at 0..+4 °C (section 6.2) |
| Physics sweeps | +1 K of setpoint costs **2.2-3.1 %** more electricity for the same heat at 0 to +12 °C (1.1 % at -10 °C); on/off cycling once the load falls below the minimum output |
| Ranking (review round 2) | energy, comfort and starts kept apart: normalised energy + 0.54 kWh per K-hour of |air - target| (the baseline's own price of comfort), judged at start costs 0.05 and 0.3 kWh with the break-even start cost reported; mean air within ±0.05 K and mean |error| within baseline + 0.05 K; 20 mandatory variants; measured link outages by default (sections 5 and 10) |
| Metric-gaming and strategy probes | comfort-for-energy trades (day/night shift) now land at about zero; low-and-slow running is decided by the part-load bounds, not blocked by `flat_load` (section 10) |
| Speed | the 183-day `season` (plus 3-day warm-up and 3-day run-out, 270 720 minutes) runs in about **3 s** with a simple controller (about 11 µs per minute) |

## 2. The loop

Each simulated minute:

1. **Observation.** The controller gets an `Observation` of the state at the start of the minute.
   `time` is the UTC start of the minute.
2. **Command.** `step(obs)` returns a `Command`. Every non-None field is clamped to the unit's
   register range and resolution:
   - setpoint 20-55 °C in whole degrees;
   - restart hysteresis 2-10 K in whole kelvin.

   Each field that changes the register value counts as one **write**. A repeated or clamped-equal
   value is not a write. The new registers act from this minute on, so the effect first shows in
   the next observation.
3. **Hot water.** A pending hot-water request raises the unit's DHW demand. The demand stays up
   until the unit has spent the request's recorded compressor minutes in hot-water mode, so a
   request that pre-empts a heat run is delayed by the firmware's 7-minute pause, not shortened.
4. **Unit.** `VersatiUnit.step` takes:
   - setpoint, hysteresis, quiet, heating enabled;
   - the return temperature (house loop return plus the anchoring offset, section 3);
   - outdoor air and humidity;
   - the DHW demand.

   It returns the heat into the loop, the electricity (metered outdoor unit, unmetered indoor
   unit, tank heater) and the status.
5. **House.** The loop, slab, air and envelope advance with the exact matrix exponential. The
   input is the unit's heat, which makes the coupling energy-exact. The exogenous part (outdoor,
   facade sun, internal-gain profile, thermometer glow, disturbance) is precomputed for the whole
   run, which is why one minute costs about 10 µs.
6. **Sensors.**
   - **Room thermometer:** reports in 0.1 K steps when its true reading has moved by at least
     0.075 K (report-on-change, the house model's rule), and at least once an hour (the real
     0.1-K device's value changes cluster at 60 minutes: 25th/50th/75th/90th percentiles 11 / 30
     / 60 / 60 min). Home Assistant records the hourly report only when the rounded value
     changed. `room_age_min` counts the minutes since the last recorded change. Simulated
     intervals: median 23-25 min and 90th percentile 90-120 min in the recorded weeks; median
     10-18 min in the archive weeks, where the weather moves the room more (the same dates run as
     an archive scenario give 16-20 min). The flag `sparse_thermometer` adds a 20-minute minimum
     gap for room-reactive controllers.
   - **Unit water sensors:** every minute in 0.1 K steps.
   - **Hot water:** while the 3-way valve is on the tank, outlet and inlet show tank-coil water.
     They climb 0.95 K/min from the loop temperature, with the outlet 2-8 K above the inlet. For
     3 minutes after the run they hold about 47 °C, then fall back to the loop over 4 minutes.
     These are the median shapes of 98 recorded DHW runs.
   - **Outdoor sensor:** the true local air (archive scenarios: ERA5 plus a local departure,
     section 4) plus the sensor's own slow error (AR(1), 3 h; SD 0.8 K in archive scenarios, 1.0 K
     around ERA5 in recorded ones) and -0.48 K at night. Sun warming adds 0.012 K per W/m² of
     global irradiance while idle and 0.003 while running, capped at 6 K. It reads in 0.5 K steps.
     Measured against ERA5 on the minute grid: median idle bias +0.8 K at 100-300 W/m² and +4.3 K
     above 300 W/m².
   - **Space heating off** (`heating_enabled` False): the circulation pump stops (ASSUMED). The
     loop water stands still and exchanges heat only with the slab; the unit's water sensors
     drift to the plant room (20 °C, 30-minute time constant, ASSUMED). When heating is switched
     on again the pump purges the loop for 3 minutes before a start can happen, and the sensors
     blend back to the loop water. The indoor unit then draws 0.02 kW instead of 0.10. The record
     holds only 2 mode changes, so every run that switches it is flagged `heating_off`.
   - **Electricity:** `electric_kw` is the metered outdoor-unit minute mean and `energy_kwh` its
     cumulative count.
7. **Run-out (archive scenarios).** After the measured window the plain reference controller
   runs the house for 3 more days in the recorded weather. Its electricity is reported separately
   and enters the ranking energy (section 5), so heat a controller leaves in or takes out of the
   house at the window end is paid back as the house really would.
8. **Link outages (review round 2, N10).** During one, every unit field of the observation repeats
   its last value, `link_ok` is False, and commands wait until the link is back. The CLI default
   (`--link-drops measured`) draws them as the record had them in the heating season (February-
   April and October-November 2026, both bridges): 0.34 a day, lengths drawn from the 38 measured
   outages up to a day (median 32 min, 25-75 % 12-128 min, longest 23 h), the same draw for every
   controller with the same seed. The 993 outages in events.csv (3.7 a day) are mostly May-June,
   when the old bridge failed outside the heating season, so they are not the default. `--link-drops
   N` sets another rate (same lengths), 0 switches them off. The flag token `long_outage` adds one
   3-day outage from the middle of the window (the record has a 10-day one in February 2026): a
   fail-safe check, not a ranking variant. Validation replays use the recorded registers and no
   synthetic outages.

Controllers never see the true air, slab, heat or supply temperature. A self-check
(`python -m lab.sim.simulator`) asserts the field list, the command timing, the write counting
and clamping, a heating-off decay, determinism, the energy bookkeeping and the season speed.

## 3. Return-temperature anchoring (integration finding)

The first closed-loop replay delivered **13 % more heat** than the real house and drifted
**+0.75 K warm** over four weeks (variant `raw_return` below). The cause is in the house model's
water temperatures, not in its energy balance.

Drive the house model with the recorded loop heat and let it track the recorded room (the residual
of HOUSE_MODEL.md section 7). Its loop return then differs from the measured inlet in a way that
depends on the load. The constant-parameter slab/ground structure cannot match the measured
water-room relation at both ends of the load range. In the closed loop the unit then sees water
about 1.4 K too cold in mild weather: it starts earlier, reaches the stop threshold later and
delivers too much heat.

**What the simulator does.** It adds an offset to the return that the **unit and the controller**
see. The house model's heat balance is untouched, since it is driven by heat, not temperature.

**What the offset depends on (review round 1, M2).** It used to be interpolated on the run's own
24-hour mean loop heat. A controller could then pump it: delivering more heat made the water look
colder and the COP better (in oct_mild the mean anchor was +1.08 K for `unit_curve` and +1.43 K
for the reference). It is now a function of the **weather-driven steady load**: the house's
steady heat demand at 22 °C for the 24-hour exponential mean of the outdoor temperature. No
controller can change it.

| weather load (kW) | 1.25 | 1.75 | 2.25 | 2.75 | 3.25 | 3.75 | 4.25 | 4.75 | 5.25 | 5.75 |
|---|---|---|---|---|---|---|---|---|---|---|
| days of record | 2.7 | 9.2 | 39 | 65 | 44 | 16 | 6.1 | 3.0 | 2.6 | 1.2 |
| measured minus model return, central (K) | +1.74 | +1.63 | +1.39 | +1.33 | +0.82 | -0.20 | -0.58 | -0.95 | -1.79 | -1.68 |
| same, `minute_only` house | +0.22 | +0.40 | +0.46 | +0.42 | +0.37 | -0.71 | -0.96 | -1.03 | -1.06 | -1.74 |

The weather load is 3.7 kW at 0 °C and 5.05 kW at -10 °C, so the knots above 4.5 kW (the cold
regime) rest on 1-3 days each. The table is re-derived for every house variant (`loss_minus20`
reaches -6.5 K at high load). Flag tokens: `raw_return` switches the anchoring off,
`anchor_heat` restores the old heat-based anchoring. Both `raw_return` and `minute_only` are
mandatory ranking variants, and `anchor_mean_running_k` reports the mean offset a run's unit saw
while heating.

**Effect on the replay** (current season, 26 days):

| | raw return | anchored on heat (before) | anchored on weather (now) |
|---|---|---|---|
| electricity sim / real | 1.104 | 1.038 | **1.018** |
| heat sim / real | 1.131 | 1.036 | **1.017** |
| room RMS / bias over 4 weeks | 0.78 / +0.75 K | 0.26 / +0.21 K | **0.19 / +0.11 K** |
| daily electricity error (mean absolute) | 13.5 % | 5.7 % | 5.9 % |

(The heat-based column is the current unit model with `anchor_heat`; the original replay with the
old unit model gave 1.015 / 1.037 / 0.27 K.) This is an empirical correction at the interface.
The proper fix is a house structure whose water temperatures stay right in free running, for
example a temperature-dependent or two-zone floor. A floor or screed sensor would settle it
(HOUSE_MODEL.md section 10).

## 4. Exogenous inputs

| input | recorded scenarios | archive scenarios |
|---|---|---|
| weather | ERA5 on the minute grid (the house fit's input) | Open-Meteo hourly turned into minutes the same way: linear temperature/humidity, clearness-index shaping of the hourly radiation means, facade irradiance (isotropic sky, albedo 0.2/0.6 on snow). It matches the data stage's columns to < 0.01 K and < 0.1 W/m² on average. The house and the unit run on the **true local air = ERA5 + a local departure** (AR(1), SD 1.1 K, 6 h; review round 1, M5); the forecast stays on ERA5 |
| hot water | recorded requests: start (DHW compressor start, or the stop of the heat run it pre-empted) and compressor minutes | whole recorded days drawn at random from the heating-season days with complete unit data (0.85 runs a day over the season, starts clustered 07-09 h and afternoon) |
| disturbance (residual heat into the room air) | re-derived for the chosen house parameters by deadbeat tracking of the recorded room through the whole record (HOUSE_MODEL.md section 7). Under the recorded heat this reproduces the recorded room exactly | **bootstrap of recorded residual days** (review round 1): whole local days of the tracked residual for the same house parameters (heating on, ≥ 97 % unit data, room data), chained as a Markov bootstrap (the next recorded day with probability 0.72, the measured lag-1 correlation of daily means, else a random day), recorded month offsets swapped for the target month's, jumps cross-faded over 30 min. Hourly SD 0.97-1.15 kW (recorded 1.12). The parametric generator (profile + month offset + Poisson events with 30-min edges + daily AR(1) of SD 0.35 kW + hourly AR(1)) is the flag `synthetic_dist` |
| PV | recorded (gaps from global irradiance) | 8.9 kW per kW/m² of global irradiance, capped at 9.2 kW (least squares on the minute grid, RMSE 0.9 kW) |
| initial state | the tracked house state at the window start; unit idle; recorded registers | quasi-steady at 22 °C, with the envelope set by the 450-hour exponential mean of earlier outdoor temperatures. Then a 3-day warm-up under `reference` |

**Forecast** (`Observation.forecast`): 48 hourly dicts starting with the next full hour, the same
tuple object for a whole hour. Radiation values are means over the hour ending at `time`
(Open-Meteo convention).

- **perfect:** the weather series itself.
- **noisy** (review round 2, N9: calibrated): issued every 6 hours (00/06/12/18 UTC).
  `lab/data/forecast_pull.py` pulled the site's archived forecasts (Open-Meteo previous runs:
  the latest run and the runs one and two days earlier, for every hour of 2025-10 .. 2026-11).
  Against ERA5 over the 2025/26 heating season the latest run's temperature error has SD 1.17 K
  and the run one day earlier 1.70 K; the two errors at the same valid hour correlate 0.78 (the
  earlier one is the later one plus an almost independent increment of SD 1.07 K); along valid
  time the error decorrelates to 0.45 within 6 h but stays near 0.3 for 2-5 days; the mean bias
  is -0.2 / -0.4 K with a daily cycle. Global irradiance log-ratio SD 0.42-0.45 in daylight, cloud
  SD 35-37 %-points, humidity 9 %-points. The model:
  - temperature error = bias(UTC hour, lead below / above 24 h, measured) + a(lead) x shared(valid
    time) + issue-specific(lead). The shared part depends only on the valid time (a slow AR(1),
    SD 0.6 K, 120 h, plus a fast one, SD 0.85 K, 4 h), so successive issues make correlated errors
    and averaging issues does not cancel them; a(lead) rises from 1 to 1.15 at 36 h; the
    issue-specific part is AR(1) along lead (φ 0.95), SD 0.2 K at lead 0 to 1.1 K at 36 h and
    1.4 K at 48 h. Simulated over the season: SD 1.0-1.1 / 1.2 / 1.4 / 1.6 / 1.8 K at 1 / 12 / 24 /
    36 / 48 h, 0.63-0.70 correlation between issues a day apart;
  - cloud SD 30-38 %-points, global irradiance lognormal SD 0.40-0.50 (anti-correlated with the
    cloud error, capped near clear sky), humidity SD 8-10 %-points, issue-specific (their sharing
    between issues was not calibrated).

  The errors depend only on the seed, the issue time and the valid time, so every controller sees
  the same forecast. **pessimistic** (`--forecast pessimistic`, or the variant token
  `forecast_pessimistic`, mandatory in the ranking): every error and bias x 1.5.

The **noisy forecast is the default** (CLI and harness) since review round 1. In archive
scenarios the forecast error comes on top of the local departure: the forecast describes ERA5,
the house feels ERA5 + departure.

**Local departure from ERA5** (review round 1, M5). At night with the compressor idle (685 hours),
the unit's sensor minus ERA5 has variance 2.02 K², the ventilation unit's intake minus ERA5 1.55 K²,
and their covariance is 1.34 K²: the two local sensors share a real departure from ERA5 of SD about
1.16 K. Its autocovariance falls to 0.42 of lag 0 in 6 hours. The simulator draws it as an AR(1)
of SD 1.1 K and 6-hour time constant. The unit sensor's own error is the rest (0.68 K², SD 0.8 K)
plus a mean -0.48 K at night (ASSUMED split: which of the two sensors is biased cannot be told).
The flag `era5_only` restores the old behaviour (house on ERA5, sensor error SD 1.0 K). Recorded
scenarios keep ERA5: their tracked disturbance already contains the departure.

## 5. Scenarios and metrics

| scenario | period | weather | purpose |
|---|---|---|---|
| `recorded` | 2026-10-09 .. 11-06 | recorded | current season, both Modbus bridges; replay validation; all controllers start from the recorded state |
| `recorded_c2` | 2026-10-23 .. 11-06 | recorded | clean new-bridge data |
| `recorded_spring` | 2026-02-26 .. 05-06 | recorded | legacy controller, late winter and spring (link outages) |
| `recorded_a0` | 2026-02-09 15:00 .. 02-14 | recorded | the only clean cold minute data (-19..+2 °C); replay validation of the cold regime |
| `oct_mild` | 2025-10-08 .. 10-15 | mean +7.6 °C (+1.6..+15.3) | mild: load below minimum output |
| `nov_mixed` | 2025-11-10 .. 11-17 | mean +4.3 °C (-3.7..+9.7), humid, dull | mixed |
| `dec_damp` | 2025-12-14 .. 12-21 | mean +0.7 °C (-2.1..+3.9), RH 97 %, no sun | defrost-heavy |
| `jan_cold` | 2026-01-15 .. 01-22 | mean -14.1 °C (-18.4..-7.9) | coldest week of January 2026 |
| `feb_sunny_cold` | 2026-02-15 .. 02-22 | mean -10.2 °C (-19.3..-1.4), 1.8 kWh/m²/day sun | cold with strong sun |
| `mar_shoulder` | 2026-03-05 .. 03-12 | mean +3.0 °C (-4.2..+14.3), sunny | shoulder, big daily swing |
| `apr_mild_sunny` | 2026-04-18 .. 04-25 | mean +7.5 °C (-0.2..+14.8), 5.6 kWh/m²/day sun | solar overheating |
| `season` | 2025-10-15 .. 2026-04-15 | archive | **primary ranking** (183 days) |

Groups: `all` = `recorded` plus the seven weeks; `weeks`; `everything` = `all` plus `season`.

Archive scenarios have a 3-day warm-up under `reference` before the window and a 3-day run-out
under `reference` after it, both excluded from the window metrics. The `seed` option redraws the
synthetic hot water, the disturbance bootstrap, the local weather departure, the sensor error and
the noisy forecast. `scenarios.steady(t_out, ...)` builds constant-weather runs for sweeps.

`metrics.compute` reports:

- **Electricity:** metered total and per day, split into space heating (everything outside hot
  water, including defrost and standby) and DHW. The unmetered indoor unit and tank heater are
  reported separately, and `elec_all_kwh` adds them in.
- **Ranking energy** (review round 1, C3):
  - `storage_delta_kwh`: heat stored in loop water, slab, air and envelope (sum C_i x_i) at the
    window end minus its start. Every controller starts from the same state.
  - `elec_corr_kwh` = elec - storage_delta / COP;
  - `elec_runout_kwh` = window + run-out electricity, with the storage left over after the
    run-out bought back at the COP;
  - `elec_norm_kwh` = elec_runout (or elec_corr without a run-out) - h_total x (mean air -
    target) x hours / COP, with the house's steady loss coefficient (0.187 kW/K central);
  - `elec_norm_kwh_per_day` divides by window + run-out days.
- **Heat:** net heat into the loop (defrost draw subtracted). Seasonal COP is heat over
  space-heating metered electricity, also given with the pump included.
- **Compressor:** starts total, per day, and per day by daily-mean outdoor bucket. Run lengths:
  median, quartiles, % of runs under 15, 30 and 60 minutes, compressor hours.
- **Water:** mean outlet sensor and true supply while running; mean anchoring offset while
  running; time-weighted mean, max and min setpoint; % of time heating enabled and quiet.
- **Comfort,** on both the true air and the thermometer: mean, `mae` (time-weighted mean
  |error|, the symmetric measure), RMS, degree-hours below target - 0.5 and above target + 0.5
  (information only), min/max, room at 07:00 local; thermometer report intervals.
- **Cold share:** electricity and heat by daily-mean outdoor bucket (< -4, -4..+4, > +4 °C).
- **Comfort K-hours** (`comfort_kh`, review round 2): the integral of |air - target| over the
  window, the comfort quantity the ranking prices.
- **Assumption flags** (`assumption_flags`, also the last column of the summary table): `quiet`,
  `restart_delta` (outside 4-5 K), `setpoint_range` (outside the 25-39 °C ever written; the share
  of time is `setpoint_out_of_range_pct`),
  `min_off` (a start waited for the ASSUMED minimum off time), `heating_off` (space heating
  switched off: pump behaviour ASSUMED), `runs_lt_15min` (more than 5 % of runs), `starts_gt_8`
  (per day), `writes_gt_48` (per day, ASSUMED register-wear limit).
- **Other:** writes (total, per day, per field); defrost count, electricity and heat drawn; DHW
  runs and energy; per-day rows.

**Ranking** (`lab/sim/ranking.py`, `run.py --rank`; review round 2):

- **energy, comfort and starts are kept apart.** Per run:
  - energy = `elec_norm_kwh`;
  - comfort = `comfort_kh`, the K-hours of |air - target| in the window;
  - starts = compressor starts.

  The ranking quantity is adjusted energy = energy + 0.54 kWh x comfort_kh + c x starts, as a
  paired difference against the baseline in % of its window electricity, with a 90 % Student-t
  interval over the seeds;
- **the price of comfort, 0.54 kWh per K-hour,** is what the baseline itself saves when it trades
  comfort for energy the cheapest way found: aiming 0.2 / 0.4 / 0.6 K warmer by day (10-22 local)
  and as much cooler at night, each tuned back to the target mean air (validate_sim `comfort`,
  season, 6 seeds: 0 / -0.3 / -1.3 % energy for +0 / +0.6 / +4.4 % comfort K-hours; least squares
  through zero over the 11 seed pairs, single pairs 0.07-1.9). Charging every candidate that
  price puts it on the baseline's own energy/comfort line: a pure comfort trade scores about
  zero, an energy saving at equal comfort counts in full, and better tracking is credited at the
  same price. Energy alone and the comfort difference are reported next to it (a Pareto pair);
- **starts are priced only inside a band.** The measured start energy is 0.02-0.04 kWh; wear has no
  data. The verdict `better` needs the 90 % interval below zero at both c = 0.05 and c = 0.3 kWh
  per start, `worse` above zero at both; anything else is `undecided`. The break-even start cost
  (where the sign flips) is reported for every pair, and starts per day of candidate and
  baseline sit next to it, to be judged against a cycle budget rather than folded into
  efficiency. c = 0.2 is the summary column;
- constraints: mean air within ±0.05 K of target (the baseline is tuned to within 0.03 K); mean
  |error| at most the baseline's + 0.05 K; at most 8 starts and 48 writes a day. A run that breaks
  one is marked `!`;
- mandatory variants (`--robust`, 20): `nominal`, `partload_lo`, `partload_hi`, `legacy_cop`,
  `high_start_loss`, `sluggish`, `raw_return`, `minute_only`, `low_flow`, `high_flow`,
  `loss_minus20`, `steep_outlet`, `shallow_outlet`, `frost_melt_lo`, `frost_melt_hi`,
  `light_slab`, `heavy_slab`, `sun_plus30`, `sun_minus30`, `forecast_pessimistic`. A ranking is
  accepted only if it is `better` on all of them. Diagnostics: `flat_load`, `frost_no_melt`,
  `legacy_frost_r1`, `long_outage`;
- ranking runs include the measured link outages (CLI default);
- the season is the primary ranking (storage < 1 % of its energy; run-out included). Weeks are
  diagnostic: use 5 or more seeds there;
- a season advantage that comes mostly (> 50 %) from days below -4 °C is flagged `cold_share`;
- `setpoint_range` is shown in the ranking only when the candidate spends more time outside the
  recorded 25-39 °C than the baseline (`setpoint_out_of_range_pct`);
- `reference_tuned`: the reference with gains kp 3 K/K and ki 0.3 K/(K h) (review round 2: of a
  gain family, the one that beat the round-1 gains on energy, comfort and starts at once), setpoints
  25-45 °C, aimed so that the scenario's mean air is on target within 0.03 K (secant search per
  scenario, variant, seed, forecast and outage rate, cached under a plant-version key).

## 6. Validation

### 6.1 Closed-loop replay of the recorded setpoints

`replay_recorded` writes the recorded setpoint, hysteresis and heating mode at every minute. The
recorded weather, hot water and disturbance drive the loop from the recorded house state. Nothing
in the loop is reset to measurements, so the house runs free for the whole window. Day-level
comparisons use days with at least 97 % unit and meter data. Numbers after review round 2.

**The room agreement in this replay is true by construction** (review round 2, N5). The recorded
disturbance is the residual heat that makes the house model follow the recorded room under the
recorded heat (HOUSE_MODEL.md section 7). When the simulated heat matches the recorded heat, the
simulated room matches the recorded room whatever the house model's dynamics. The room numbers
below therefore check that the simulated heat matched the recorded heat, not that the house
responds correctly to a different heating pattern. The house test without the recorded room is
the next table.

| | current season (26 d) | new bridge (12 d) | late winter/spring (50 d) | cold week A0 (3 d) |
|---|---|---|---|---|
| starts/day real -> sim | 3.85 -> 3.15 (0.82) | 3.83 -> 3.17 (0.83) | 2.02 -> 1.72 (0.85) | 2.0 -> 1.33 (0.67) |
| daily start error (mean absolute) | 0.92 | 0.67 | 0.50 | 0.67 |
| run minutes p25/p50/p75 real | 64 / 115 / 150 | 82 / 120 / 150 | 125 / 218 / 268 | 152 / 437 / 549 |
| run minutes p25/p50/p75 sim | 83 / 128 / 214 | 89 / 124 / 209 | 139 / 238 / 353 | 375 / 488 / 1103 |
| runs under 60 min real / sim | 22 % / 17 % | 15 % / 13 % | 3 % / 2 % | 14 % / 0 % |
| runs ending within ±6 min of a 120-min mark, real / sim | 30 % / 23 % | 35 % / 26 % | 53 % / 30 % | 17 % / 20 % |
| compressor minutes sim / real | 1.02 | 0.98 | 1.02 | 1.09 |
| electricity kWh/day real -> sim | 11.66 -> 11.74 (**+0.7 %**) | 12.43 -> 12.24 (-1.5 %) | 12.79 -> 13.14 (+2.7 %) | 37.4 -> 41.5 (**+11 %**) |
| daily electricity error (mean absolute) | 5.4 % | 4.3 % | 13.6 % | 12.6 % |
| heat sim / real | 1.021 | 0.996 | 1.013 | 1.076 |
| COP real / sim | 4.23 / 4.29 | 4.10 / 4.15 | 3.27 / 3.22 | 2.57 / 2.48 |
| mean outlet while running real / sim | 30.53 / 30.68 °C | 30.37 / 30.55 | 29.59 / 29.74 | 31.71 / 31.69 |
| room thermometer RMS / bias over the window (by construction) | 0.19 / +0.12 K | 0.12 / -0.01 | 0.38 / +0.11 | 0.24 / +0.05 |
| defrosts real / sim | 7 / 22 | 3 / 12 | 85 / 102 | 29 / 29 |
| DHW runs real / sim | 26 / 26 | 14 / 14 | 52 / 52 | 4 / 4 |

**House response without the recorded room** (`validate_sim house`, review round 2, N5): the
same replay with the residual replaced by something that does not use the recorded room. Room
thermometer error against the recorded room over the window:

| residual used | current season: RMS / bias / p95 | first 24 h / 72 h RMS | spring: RMS / bias / p95 | first 24 h / 72 h RMS | electricity sim / real (current / spring) |
|---|---|---|---|---|---|
| recorded (by construction) | 0.19 / +0.12 / 0.3 K | 0.17 / 0.15 | 0.38 / +0.11 / 0.7 | 0.16 / 0.14 | 1.007 / 1.027 |
| its daily means (slow part only) | 0.35 / +0.09 / 0.7 | 0.31 / 0.27 | 0.53 / +0.16 / 1.1 | 0.27 / 0.21 | 1.003 / 1.042 |
| its window mean | 0.49 / +0.06 / 0.9 | 0.60 / 0.68 | 0.72 / +0.18 / 1.5 | 0.29 / 0.21 | 1.010 / 1.014 |
| zero | 0.48 / -0.12 / 0.9 | 0.66 / 0.76 | 1.13 / +0.89 / 2.2 | 0.29 / 0.40 | 1.029 / 0.950 |
| recorded days from elsewhere in the record (3 draws) | 0.68-0.82 / -0.30..+0.17 / 1.3-1.6 | 0.64-0.90 / 0.77-1.10 | 0.91-0.97 / +0.17..+0.41 / 1.9-2.2 | 0.36-0.45 / 0.36-0.43 | 1.00-1.05 / 1.01-1.03 |

- Without the recorded intra-day residual the house still follows the room to 0.35 K (0.53 K in
  spring) when the daily means are known, and to about 0.5-0.7 K with only the window mean. The
  bootstrap rows are the honest picture for archive scenarios: someone else's days of airing,
  cooking and sun misfit move the room by 0.7-1.0 K RMS. Electricity barely moves (0-5 %): the
  energy balance is held by the heat, the room by the residual.
- **The house has only seen two controllers with similar patterns** (setpoints written every
  30 minutes, 25-39 °C). Responses to pulses, deep setbacks or long low-output runs rest on the
  24 h held-out forecast (0.41 K RMS, HOUSE_MODEL.md section 5) and are extrapolated. The
  residual applied to a candidate in a recorded scenario also carries the recorded controller's
  model-error pattern. Rank on archive scenarios (bootstrapped residual) and treat recorded
  scenarios as replays.
- **Out-of-pattern test on the real house (proposed):** two deliberately different heating
  patterns of about two days each, for example a night setback (setpoint 25 °C from 22 to 05 h,
  normal otherwise) and a fixed low-output pattern (setpoint held a few K above the return so the
  unit runs at minimum output). Predict the room with the residual's daily means before each test
  and compare.

**By daily-mean outdoor temperature** (electricity sim / real, starts real / sim):

| bucket | days | electricity | heat | starts | room bias |
|---|---|---|---|---|---|
| below 0 °C (A0 2 d + spring 1 d) | 3 | 1.08 (A0) / 1.05 (spring) | 1.05 / 1.00 | 2 / 2, 1 / 1 | -0.09 / -0.17 K |
| 0..+4 °C (spring 12 d + A0 1 d) | 13 | 1.07 / 1.21 | 1.02 / 1.15 | 33 / 24, 4 / 2 | +0.02 / +0.13 K |
| +4..+12 °C (current 26 d, spring 33 d) | 59 | 1.007 / 0.994 | 1.02 / 1.01 | 100 / 82, 66 / 59 | +0.13 / +0.04 K |

Plant variants on the current season:

| variant | starts ratio | electricity ratio | heat ratio | room RMS / bias | defrosts (real 7) |
|---|---|---|---|---|---|
| nominal | 0.82 | 1.007 | 1.021 | 0.19 / +0.12 | 22 |
| `raw_return` | 0.85 | 1.093 | 1.134 | 0.80 / +0.77 | 22 |
| `anchor_heat` (old anchoring) | 0.79 | 1.019 | 1.040 | 0.28 / +0.23 | 23 |
| `minute_only` | 0.80 | 1.003 | 1.019 | 0.27 / +0.18 | 21 |
| `low_flow` (25 L/min) | 0.89 | 1.099 | 0.980 | 0.20 / -0.10 | 20 |
| `high_flow` (33 L/min) | 0.77 | 0.940 | 1.064 | 0.35 / +0.30 | 20 |
| `sluggish` | 0.83 | 1.000 | 1.017 | 0.19 / +0.11 | 21 |
| `partload_lo` / `partload_hi` | 0.82 / 0.84 | 1.012 / 0.998 | 1.021 / 1.018 | 0.19 / +0.12, 0.19 / +0.11 | 21 / 20 |
| `flat_load` | 0.84 | 1.010 | 1.021 | 0.20 / +0.13 | 20 |
| `legacy_cop` | 0.83 | 1.011 | 1.021 | 0.19 / +0.12 | 20 |
| `frost_melt_lo` / `frost_melt_hi` | 0.82 / 0.86 | 1.007 / 1.013 | 1.019 / 1.019 | 0.19 / +0.11, 0.19 / +0.12 | 17 / 17 |
| `frost_no_melt` / `legacy_frost_r1` | 0.83 / 0.82 | 1.019 / 1.029 | 1.022 / 1.022 | 0.20 / +0.13, 0.21 / +0.13 | 13 / 11 |
| `surge_from_start` | 0.83 | 1.004 | 1.018 | 0.19 / +0.12 | 20 |

Reading:

- **Energy and water temperature are reproduced in mild weather,** within 3 % over every mild
  window. The room trajectory in replay is not evidence for the house dynamics (see above).
- **The cold regime is the weak end.** A0 is the only clean cold minute data: 3 good days. There
  the simulator uses 8-21 % more electricity, delivers 5-15 % more heat and runs 9 % more
  compressor minutes; defrosts now match (29 / 29, was 36). Below -4 °C the season is about
  46 % of the energy (section 6.2), so a strategy whose advantage sits there is flagged
  `cold_share` in the ranking and must be confirmed on the real unit.
- **Starts are 15-18 % low and long runs too long.** The open-loop unit validation shows the
  same thing (UNIT_MODEL.md section 11). Review round 2 classified every clean recorded stop:
  almost all natural stops come at surges, defrosts, writes or hot water, so no stop mechanism
  is missing; the misses in replay are setpoint writes the recorded controller placed exactly at
  the firmware's stop threshold, where the simulated control sensor sat 0.3-0.5 K lower
  (UNIT_MODEL.md section 3.3). The share of runs that end at a 120-minute mark is now lower in the
  simulation than in the data (23-30 % against 30-53 %), not higher. Start counts are a relative
  measure.
- **Mild-weather defrosts are over-predicted in replay** (22 vs 7 and 12 vs 3 in the autumn
  windows, 102 vs 85 in spring), while the cold week matches. The frost model matches the
  recorded counts on the recorded running pattern (UNIT_MODEL.md section 8); in closed loop the
  simulated runs are longer, keep more of the trigger state and defrost more. Mild-weather
  defrosts are short (2 min) and the energy effect is small (replay electricity within 1-3 %),
  but on/off-versus-continuous comparisons in mild weather must hold on `frost_melt_lo` and
  `frost_melt_hi`.
- **Flow.** The flow stays the main open uncertainty for absolute COP (±14 %).

### 6.2 Season sanity: daily electricity against the meter

The whole 2025/26 season (archive weather, bootstrapped disturbances, synthetic hot water, noisy
forecast) is run with two controllers. The real house was run by other controllers, so this is a
plausibility check, not an equality test:

- `unit_curve`: the unit's own weather curve;
- `reference`: the warm-up controller, which holds the room near 22 °C as the real controllers
  did (two seeds).

Real days are local days with 24 valid hourly meter readings from 2025-10-15 to 2026-05-06
(simulated days are binned by their true local outdoor temperature). All figures are metered
outdoor-unit electricity including hot water, median (p25-p75) kWh/day:

| daily mean outdoor | real days | real | `reference` seed 0 | `reference` seed 1 | `unit_curve` |
|---|---|---|---|---|---|
| -20..-12 °C | 19 | 52.6 (50.0-60.1) | 52.5 (48.4-56.9) | 51.7 (47.3-54.0) | 67.6 (65.7-69.7) |
| -12..-8 | 14 | 52.5 (48.6-54.5) | 48.0 (42.9-49.2) | 46.5 (42.2-50.4) | 59.7 (57.7-62.4) |
| -8..-4 | 13 | 42.8 (39.6-46.1) | 40.7 (37.9-43.2) | 40.8 (35.5-41.9) | 54.1 (50.0-55.0) |
| -4..0 | 26 | 34.7 (30.1-37.0) | 34.6 (30.9-38.0) | 33.3 (30.7-36.9) | 40.0 (38.3-43.6) |
| 0..+4 | 39 | 25.5 (17.3-28.1) | 23.6 (16.5-27.3) | 20.4 (15.7-26.0) | 27.7 (24.5-32.5) |
| +4..+8 | 54 | 12.5 (10.1-15.1) | 12.7 (10.7-15.4) | 12.9 (9.0-16.6) | 16.0 (14.1-18.1) |
| +8..+12 | 12 | 7.9 (7.0-10.0) | 8.2 (6.7-9.5) | 8.2 (6.6-9.3) | 11.5 (9.2-12.9) |

(Review round 2 numbers: new frost model, setpoints clamped at 25 °C, no link outages in this
check.)

- The room-holding reference lands within 5 % of the meter below -12 °C, at -4..0 °C and above
  +4 °C; it is 5-12 % low at -12..-4 °C and 7-20 % low at 0..+4 °C (the two seeds differ by 3
  kWh/day there: the bin's spread is wide, 17-28 kWh/day in reality).
- `unit_curve` uses 10-30 % more, because the unit's curve overheats the house: the room median is
  23-25 °C in every bin.
- Season totals: `reference` 4 945 / 4 793 kWh for seeds 0 / 1 (2.1 starts a day; 995 / 967
  defrosts, was 1 107 / 1 095), room 22.01 / 22.02 °C mean (mean |error| 0.50 / 0.53 K). Days
  below -4 °C carry 46-48 % of the electricity. `unit_curve` 6 207 kWh, room 24.3 °C. The
  plain reference no longer writes setpoints below 25 °C, so it carries no assumption flag.

### 6.3 Steady-weather sweeps

These are constant outdoor temperature runs at 85 % RH with no sun, no hot water and no
disturbance. The daily internal-gain profile stays on. Each point runs twice:

- the first pass finds the mean heat;
- the second starts from the house's steady state at that heat and is measured over 7 days.

**Constant setpoint** (electricity kWh/day / heat kWh/day / COP / starts per day / room °C):

| setpoint | -10 °C | 0 °C | +7 °C | +12 °C |
|---|---|---|---|---|
| 26 | 36.8 / 97 / 2.64 / 0.1 / 18.1 | 21.6 / 66 / 3.06 / 1.7 / 20.2 | 8.8 / 46 / 5.21 / 2.9 / 20.3 | 6.5 / 38 / 5.79 / 2.7 / 21.1 |
| 28 | 39.8 / 103 / 2.58 / 0.1 / 19.8 | 25.6 / 77 / 3.00 / 2.3 / 21.2 | 11.8 / 58 / 4.93 / 3.3 / 21.5 | 9.9 / 54 / 5.48 / 2.9 / 22.2 |
| 30 | 43.3 / 110 / 2.53 / 0.1 / 21.3 | 31.4 / 91 / 2.91 / 2.0 / 22.2 | 15.7 / 74 / 4.68 / 4.0 / 22.5 | 12.7 / 66 / 5.20 / 3.1 / 23.5 |
| 32 | 50.0 / 123 / 2.46 / 0.0 / 22.2 | 36.7 / 105 / 2.86 / 1.9 / 23.2 | 19.2 / 85 / 4.45 / 3.9 / 23.8 | 15.0 / 73 / 4.89 / 3.3 / 25.3 |
| 34 | 56.3 / 134 / 2.39 / 0.0 / 23.2 | 41.5 / 115 / 2.76 / 1.1 / 24.6 | 22.2 / 94 / 4.22 / 4.0 / 25.4 | 17.4 / 80 / 4.61 / 3.3 / 27.0 |
| 36 | 62.0 / 144 / 2.32 / 0.0 / 24.3 | 46.5 / 123 / 2.64 / 0.1 / 26.0 | 25.1 / 100 / 3.99 / 3.9 / 27.1 | 20.2 / 88 / 4.36 / 3.3 / 28.6 |
| 38 | 67.5 / 152 / 2.25 / 0.0 / 25.4 | 51.5 / 130 / 2.52 / 0.1 / 27.5 | 28.7 / 107 / 3.75 / 2.1 / 28.8 | 22.9 / 94 / 4.12 / 3.1 / 30.4 |
| 40 | 70.3 / 156 / 2.22 / 0.1 / 25.6 | 56.6 / 136 / 2.40 / 0.1 / 29.1 | 31.8 / 115 / 3.61 / 2.9 / 30.3 | 26.4 / 103 / 3.91 / 3.1 / 31.7 |

- **Supply temperature costs efficiency.** At the same heat (regression of log electricity on log
  heat and setpoint over the points with a 19-26 °C room), +1 K of setpoint costs **+2.2 % at
  0 °C, +2.7 % at +7 °C and +3.1 % at +12 °C** (1.1 % at -10 °C, where setpoint and output move
  together and the flat high-output COP hides part of it). Round 1: 1.8 / 2.8 / 3.1 / 0.8 %.
- **The minimum output forces cycling.** At -10 °C the unit runs continuously; at 0 °C and above
  the load is at or below the minimum output and the unit cycles 1-4 times a day. Higher
  setpoints cycle less at 0 °C (the unit can hold minimum output against the load).
- **At -10 °C the maximum capacity binds from setpoint 39 °C** (39 and 40 give the same heat).

**Restart hysteresis** (setpoint held, electricity / heat / COP / starts per day / run median /
room):

| delta K | 0 °C, setpoint 31 | +7 °C, setpoint 29 | +12 °C, setpoint 27 |
|---|---|---|---|
| 2 | 35.5 / 100 / 2.81 / 2.6 / 368 / 22.8 | 17.0 / 73 / 4.30 / **69.4 / 9** / 22.4 | 10.4 / 53 / 5.08 / **58.7 / 8** / 22.1 |
| 3 | 35.4 / 100 / 2.83 / 2.1 / 382 / 22.8 | 15.8 / 73 / 4.64 / 4.1 / 243 / 22.4 | 9.1 / 50 / 5.53 / 4.4 / 123 / 22.0 |
| 4 | 34.2 / 99 / 2.89 / 1.9 / 540 / 22.7 | 13.7 / 66 / 4.79 / 3.7 / 243 / 22.0 | 8.3 / 46 / 5.61 / 2.4 / 243 / 21.7 |
| 5 | 33.0 / 97 / 2.94 / 1.7 / 456 / 22.5 | 12.2 / 61 / 5.00 / 3.0 / 243 / 21.6 | 6.9 / 40 / 5.75 / 2.0 / 243 / 21.2 |
| 6 | 31.7 / 94 / 2.98 / 1.6 / 708 / 22.3 | 11.4 / 58 / 5.10 / 2.1 / 243 / 21.3 | 5.7 / 34 / 5.86 / 1.6 / 243 / 20.8 |
| 7 | 30.4 / 90 / 2.96 / 1.1 / 966 / 22.4 | 10.3 / 53 / 5.15 / 1.6 / 294 / 21.1 | 4.9 / 29 / 5.91 / 1.1 / 243 / 20.2 |
| 8 | 30.6 / 91 / 2.97 / 0.9 / 1365 / 22.0 | 9.1 / 48 / 5.24 / 1.3 / 327 / 20.8 | 4.7 / 28 / 5.99 / 1.0 / 243 / 19.5 |

- A larger hysteresis lowers the average water temperature and the number of starts.
- At a fixed setpoint it also lowers the delivered heat, so compare at equal comfort.
- With 2 K the unit short-cycles in mild weather, with 8-9-minute runs: COP falls 9-10 %.
- Only 4 and 5 K were ever observed. Other values are ASSUMED and flagged `restart_delta`.

**Quiet mode** (no data in this house: capacity x 0.7 ASSUMED; frost now follows the lower output
instead of an ASSUMED x1.5):

| | electricity | heat | COP | starts per day | defrosts per day | room |
|---|---|---|---|---|---|---|
| -10 °C, setpoint 36, off / on | 62.0 / 49.7 | 144 / 123 | 2.32 / 2.47 | 0 / 0 | 14.7 / 12.4 | 24.3 / 22.2 |
| 0 °C, setpoint 31, off / on | 34.2 / 35.2 | 99 / 100 | 2.89 / 2.83 | 1.9 / 0.1 | 7.9 / 8.3 | 22.7 / 22.8 |
| +7 °C, setpoint 29, off / on | 13.7 / 14.5 | 66 / 69 | 4.79 / 4.75 | 3.7 / 2.7 | 1.0 / 1.0 | 22.0 / 22.1 |

In the model quiet mode caps capacity, so the unit runs longer and cycles less. Treat any
quiet-mode result as a hypothesis to test on the real unit (flag `quiet`).

### 6.4 Speed

| run | wall time |
|---|---|
| `season` (270 720 minutes incl. warm-up and run-out), `fixed_setpoint` / `unit_curve` / `room_thermostat` | 2.9 / 2.9 / 2.5 s (9-11 µs per minute; controller share 0.1 s) |
| same with scenario build, JSON and the per-minute CSV | 4.6 s |
| 5 controllers x 8 scenarios (`--compare -s all`), parallel | 4.0 s |
| 1 300 probe runs of `validate_sim review` (4 weeks x 5 variants x 5 seeds x 13 controllers) | 71 s on 8 cores |

## 7. What the simulator does not model, or only assumes

- **One room.** The thermometer is the living-room sensor of the house model. The rest of the
  house is folded into the air and envelope nodes. There are no room thermostats or zone valves.
- **Return anchoring is empirical** (section 3). Absolute water temperatures carry about ±0.5 K of
  uncertainty, and more in the house variants and in deep cold, where its knots rest on 1-3 days.
- **The cold regime is the least validated** (section 6.1): 3 clean days below +2 °C in closed
  loop, +10-19 % electricity there. Results flagged `cold_share` rest on it.
- **Compressor starts are under-predicted by 15-18 %** and long runs are too long (section 6.1).
  This comes from the unit model's stop-threshold sensitivity, not from a missing stop rule
  (review round 2). Because the frost trigger now loses part of itself at every stop, the long
  runs also make the simulation defrost more often than the unit in mild weather.
- **The house response to new heating patterns is extrapolated** (review round 2, N5): the replay's
  room agreement is by construction; without the recorded room the house follows it to 0.35-0.5 K
  RMS (daily-mean residual) and 0.7-1.0 K with someone else's days (section 6.1). Two
  deliberately different heating patterns on the real house would test it.
- **Flow is assumed** at 29 L/min (25-33 in the variants). Absolute COP scales with it.
- **Firmware behaviour never observed is ASSUMED** (UNIT_MODEL.md) and flagged in the metrics:
  - quiet mode (`quiet`);
  - restart hysteresis other than 4/5 K (`restart_delta`);
  - minimum off time (`min_off` when it delays a start);
  - space heating switched off: pump stop, sensor drift, 3-minute purge (`heating_off`);
  - setpoints outside 25-39 °C (`setpoint_range`);
  - more than 8 starts a day or many runs under 15 minutes (`starts_gt_8`, `runs_lt_15min`);
  - the tank-heater rating (2 kW for 23 min after each DHW run).

  The share of the frost-trigger state lost while the compressor is off is fitted (UNIT_MODEL.md
  section 8) and bounded by mandatory variants.

  Backup heaters, anti-freeze, legionella cycles and the unit's internal weather curve and
  room-thermostat modes are not simulated. `unit_curve` emulates the weather curve through
  setpoint writes.
- **Hot water is exogenous.** Requests do not depend on the tank temperature or the controller.
  A controller cannot schedule or shift DHW. While the valve is on the tank the floor loop is
  still modelled as circulating without heat.
- **Disturbances are residuals.** They include model error as well as people, cooking and airing.
  Archive scenarios reuse recorded residual days (bootstrap), so they carry the residual's
  statistics, not its causes, and residual days move to other weather. There are no window
  contacts and no occupancy signal.
- **Weather is ERA5-like.** The local departure from ERA5 is an AR(1) of measured size; how it
  splits between the true air and the two local sensors' own errors is ASSUMED. The noisy
  forecast is synthetic but calibrated on the site's archived forecasts (temperature SD, bias,
  sharing between issues); cloud, irradiance and humidity errors are calibrated in size only.
- **PV is a linear function of global irradiance** in archive scenarios. There is no
  self-consumption, tariff or grid model; `pv_kw` is information only.
- **Electricity is the outdoor-unit meter.** The indoor unit (0.10 kW, 0.02 kW with space heating
  off) and tank heater are added by assumption.
- **Sensor faults:** Modbus link outages at the measured heating-season rate and lengths (CLI
  default), a 3-day outage as a fail-safe check (`long_outage`), and the hourly-report
  thermometer. No frozen or biased sensors.
- **Wear is not costed in energy** (review round 2): a ranking must hold for start costs of 0.05-0.3
  kWh, the break-even start cost and starts per day are reported, 48 writes a day is the
  register-wear limit.
- **Comfort has a price, not a utility:** 0.54 kWh per K-hour of |air - target|, the baseline's
  own cheapest trade (section 5). The owner's real willingness to trade comfort is not known.
- **The comfort normalisation is linear.** After the run-out and the h_total normalisation the
  ranking energy still depends on the mean air by a few % per K (`validate_sim normalisation`,
  section 10): warmer water costs COP. The ±0.05 K mean-air tolerance is worth at most about
  0.3 %.
- **Before 2026-02 there is no minute data.** The archive weeks rest on the models' extrapolation;
  the deep-cold weeks rest on the house model's cold-season reconciliation (HOUSE_MODEL.md
  section 6).

## 8. Reproduce

```
.local/lab-venv/bin/python -m lab.sim.simulator                  # self-check (~5 s)
.local/lab-venv/bin/python -m lab.sim.validate_sim replay        # 6.1 (~15 s)
.local/lab-venv/bin/python -m lab.sim.validate_sim season        # 6.2
.local/lab-venv/bin/python -m lab.sim.validate_sim sweeps        # 6.3 (~30 s)
.local/lab-venv/bin/python -m lab.sim.validate_sim speed         # 6.4
.local/lab-venv/bin/python -m lab.sim.validate_sim normalisation # section 9
.local/lab-venv/bin/python -m lab.sim.validate_sim review        # section 9 (~70 s)
.local/lab-venv/bin/python -m lab.sim.validate_sim house         # section 6.1, house without the recorded room
.local/lab-venv/bin/python -m lab.sim.validate_sim comfort       # section 5, price of comfort and baseline gains
.local/lab-venv/bin/python -m lab.sim.validate_sim review2       # section 10 (~30 min on 9 cores, tuning included)
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,unit_curve,room_thermostat -s season --seeds 0-1 --robust
```

## 9. Review fixes (round 1)

An adversarial review found that several shortcuts could decide a ranking. Each finding, what was
changed, and what the probes in `lab/controllers/probes.py` show now. "Energy" below is the
ranking energy (`elec_norm_kwh`) and "score" adds the start cost, both as paired differences
against `reference_tuned` in % of its window electricity, mean ± 90 % interval over 5 seeds.

| id | finding | change |
|---|---|---|
| C1 | COP rose with output to the maximum | smooth COP with a peaked output surface, held above the measured 95th percentile; `flat_load` refitted and mandatory (UNIT_MODEL.md 7.1) |
| C2 | frost per run-minute | frost per kWh of air heat (UNIT_MODEL.md 8) |
| C3 | week energy dominated by heat left in storage; ±0.5 K dead-band comfort | storage bookkeeping, 3-day common run-out, normalisation to the target mean air, symmetric `mae`, mean-air constraint, season primary (section 5) |
| C4 | staircase COP against outdoor temperature | smooth eta plus an explicit coil-frost term (UNIT_MODEL.md 7.1) |
| M1 | short cycling almost free | 0.2 kWh per start in the score, flags beyond 8 starts a day and 5 % of runs under 15 min, start energy measured against the off time, `high_start_loss` and `sluggish` mandatory |
| M2 | anchoring pumpable by the controller | anchored on the weather-driven load; `raw_return` and `minute_only` mandatory (section 3) |
| M3 | cold regime unvalidated | A0 replay and per-bucket replay tables; `cold_share` flag (section 6.1) |
| M4 | heating off kept the loop circulating | pump stops, stagnant loop, sensor drift, purge (ASSUMED, flagged `heating_off`; `pump_always_on` variant) |
| M5 | house driven exactly by the forecast's own weather | local departure from ERA5 shared with the unit sensor; noisy forecast default (section 4) |
| M6 | one random draw per scenario; synthetic disturbance lacked day-to-day persistence | `--seeds`, paired 90 % intervals; recorded-day bootstrap (daily persistence 0.72, hourly SD as recorded) |
| M7 | surge chance by outdoor temperature only | by the preceding power (UNIT_MODEL.md 3.3) |
| m1 | flapped setpoint billed pre-start forever | a begun pre-start finishes; `writes_gt_48` flag |
| m2 | ASSUMED behaviour not flagged | `assumption_flags` in every result and the tables |
| m3 | thermometer reported too often | hourly-report model of the real device; `sparse_thermometer` flag (section 2) |
| m4 | loose-comfort baseline | `reference_tuned` (mean air on target within 0.05 K) |

**Normalisation check** (`validate_sim normalisation`: reference aimed at target -0.5 / 0 / +0.5 K,
3 seeds; % of window electricity per K of mean air):

| | metered | storage-corrected | ranking energy (run-out + normalised) |
|---|---|---|---|
| oct_mild | +57 %/K | +18 %/K | +6.5 %/K |
| nov_mixed | +32 | +13 | +1.5 |
| jan_cold | +15 | +3.4 | -0.5 |
| mar_shoulder | +46 | +12 | -0.8 |
| season (2 seeds) | +9.3 | +8.8 | +3.1 |

**Probes** (`validate_sim review`; energy % / score %, nominal plant; `!` = breaks a constraint):

| probe | oct_mild | nov_mixed | dec_damp | before review round 1 |
|---|---|---|---|---|
| plain reference | +0.2 / +0.5 | +0.2 / +0.2 | +0.4 / +0.4 | (baseline) |
| heating off for the last 18 h | 0.0 ± 1.6 / -0.3 | -0.3 ± 0.9 / -0.6 | +0.2 ± 0.8 / -0.1 | -13.1 % (nov_mixed) |
| same through setpoint 20 °C | +0.1 / -0.2 | -0.5 / -0.8 | +0.2 / 0.0 | |
| heating off for the last 36 h | -0.4 / -1.6 ! | -3.2 / -3.8 ! | -1.2 / -1.8 ! | -24.7 % |
| reference aimed at target - 0.45 K | -1.8 / -3.1 ! | -0.4 / -0.5 ! | -2.3 / -2.3 ! | -9.6 % |
| pulses at 40 °C, 3-h period | -0.1 ± 3.3 / +13.9 ! | +0.7 ± 2.0 / +5.7 ! | +3.1 ± 1.4 / +7.0 ! | -5.5 % nov_mixed, -0.1 % dec_damp |
| PWM 7 min on / 13 off at 40 °C | +13.5 / +174 ! | +1.9 / +74 ! | +2.1 / +51 ! | COP +2.4 % (oct_mild) |
| bang-bang 55 / 20 °C | +13.4 / +11.9 | +5.4 / +4.0 | +3.9 / +3.5 | COP -0.4 % at +3.8 K supply (dec_damp) |
| reference, restart_delta 2 | +4.4 / +24.8 ! | +5.6 / +30.6 ! | +4.2 / +14.9 ! | +0.9 % (oct_mild), +1.7 % (nov_mixed) |
| reference, restart_delta 10 | -1.8 / -5.0 ! | +0.4 / -1.7 ! | +2.1 / +0.9 | |
| reference, quiet mode | +1.0 / +0.4 | +2.1 / +1.2 | +2.2 / +1.4 | +2.4 % (nov_mixed, defrosts 30 vs 18) |
| setpoint 55 / 20 every minute | +56 / +327 ! | +13 / +134 ! | +1.5 / +84 ! | 0 starts, 27 kWh of pre-start |

- The end-of-window exploits are gone within ±1 % when the comfort constraint holds; the 36-hour
  coast that still gains breaks it.
- **Pulsing** no longer wins on energy: +0.7 % in nov_mixed (nominal), and it does not hold on
  the variants: `flat_load` +8.6 %, `legacy_cop` -2.0 %, `high_start_loss` +4.2 %. Over the
  season (2 seeds) it is -1.0 % energy on nominal, +7.3 % on `flat_load`, +0.7 % on
  `legacy_cop`, and flagged `cold_share` and `starts_gt_8`. In dec_damp it now defrosts 47 times
  against the baseline's 41 (it got about half the defrosts before).
- **Short cycling** costs COP now: restart_delta 2 gives 11-27 starts a day and +4-6 % energy,
  +15-31 % with the start cost; `high_start_loss` makes it +14-27 %.
- **mar_shoulder** is dominated by sun: the plain reference runs 22.5 °C mean and uses 39 % more
  electricity than the tuned one at 22.0 °C (+9 % after normalisation); every probe is within a
  wide band there. Use the season for ranking.
- The plain `reference` is flagged `setpoint_range`: it writes setpoints down to 22 °C in mild
  weather, below the 25 °C ever recorded.

## 10. Review fixes (round 2)

A second adversarial review found that frost, comfort, the part-load variant set and the start
cost could still decide a ranking, and that several uncertainties were missing from the mandatory
variants. Each finding, what was changed, and what the probes show now. Section 1 and sections
4-7 already carry the new numbers.

| id | finding | change |
|---|---|---|
| N1 | frost kept while idle; the K table averaged melting in, so continuous runners got too few defrosts and on/off strategies too many | the frost-trigger state loses up to 40 % over each compressor-off block; K refitted per minute temperature from all 186 inter-defrost segments (timing decides the loss share, counts by outdoor band and on/off class set K); `frost_melt_lo` / `frost_melt_hi` (refitted at 0.2 / 0.6) mandatory; `frost_no_melt` diagnostic (UNIT_MODEL.md section 8) |
| N2 | comfort outside the score, loose constraints: trading comfort for energy won | comfort priced into the ranking at the baseline's own trade (0.54 kWh per K-hour of |air - target|); mean air within ±0.05 K, mean |error| within baseline + 0.05 K; energy and comfort reported as a pair; baseline gains chosen from a tuned family (kp 3, ki 0.3: lower energy, better comfort and fewer starts than round 1's) (section 5) |
| N3 | `flat_load`, rejected by the data, was mandatory, so output-level strategies could not be decided | mandatory `partload_lo` / `partload_hi` (output dependence of the COP surface x0.5 / x1.5, refitted); `flat_load` diagnostic; a two-hold field test proposed (UNIT_MODEL.md section 7.2) |
| N4 | the assumed 0.2 kWh per start decided close calls | verdicts must hold at 0.05 and 0.3 kWh per start; break-even start cost and starts per day reported for every pair (section 5) |
| N5 | replay room accuracy is true by construction | stated (section 6.1); house test without the recorded room (0.35-0.5 K RMS with the residual's daily or window means, 0.7-1.0 K with other days'); real-house out-of-pattern test proposed |
| N6 | runs too long, short cold runs missing | all clean recorded stops classified: no further firmware stop rule (5 of 231 natural stops unexplained); the 120-min surge timer restarts after a defrost; t_ctrl offset depends on output. Replay starts 0.82-0.85, run p75 still 40-80 min long, runs ending at a 120-min mark now 23-30 % sim vs 30-53 % real (UNIT_MODEL.md section 3.3) |
| N7 | slab, sun and frost uncertainty missing from the mandatory set; parallel runs crashed on a half-written cache | `light_slab`, `heavy_slab`, `sun_plus30`, `sun_minus30`, `frost_melt_lo`, `frost_melt_hi`, `forecast_pessimistic` mandatory (20 variants); cache files built under a file lock and published by atomic rename (track and tuning caches); the orphan cache removed |
| N8 | `setpoint_range` fired on the baseline | reference and reference_tuned clamp at 25 °C (the lowest recorded setpoint); the ranking shows the flag only when a candidate spends more time outside 25-39 °C than the baseline |
| N9 | synthetic forecast error uncalibrated, independent between issues | calibrated on the site's archived forecasts (Open-Meteo previous runs): shared valid-time component, measured bias, SD 1.2 / 1.6 K at 12 / 36 h; `forecast_pessimistic` (x1.5) mandatory (section 4) |
| N10 | link drops off by default | measured heating-season outages by default (0.34 a day, median 32 min; the 3.7 a day of the record is mostly May-June); `long_outage` (3 days) as a fail-safe check (section 2) |

**Probes through the new ranking** (`validate_sim review2`: season 2 seeds, weeks 3 seeds;
adjusted energy at c = 0.2 kWh per start in % of the baseline's window electricity, 90 %
interval; energy alone and the comfort cost beside it; nominal plant unless stated):

| probe | season | nov_mixed | dec_damp | jan_cold |
|---|---|---|---|---|
| day/night aim shift ±0.6 K (`SymShift`): adjusted / energy / comfort cost | -0.1 ± 4.6 / -1.2 / +0.8, undecided | +0.7 ± 2.4 / -1.6 / +2.1 | +4.2 ± 2.7 / -0.6 / +4.7, worse | -0.1 ± 0.8 / -1.0 / +0.6 |
| afternoon shift ±0.4 K (`DayShift`) | -0.1 ± 2.6 / -0.2 / -0.1 | -0.1 ± 3.1 / -0.5 / +0.1 | +2.9 ± 1.2 / -0.1 / +2.8, worse | +0.6 ± 0.7 / +0.5 / +0.1 |
| reference aimed at target - 0.09 K (`low_band`) | +1.5 ± 1.7, mean air 21.93 ! | +1.3 ± 3.7 ! | +1.5 ± 1.1, worse ! | +1.4 ± 1.7 ! |
| weather curve on the forecast, room trim (`WC`, untuned) | +2.8 ± 2.4, worse, mean air 22.16 ! | +2.4 ± 3.7 ! | +3.1 ± 2.7 | +6.9 ± 12 ! |
| long low-power runs (`LowSlow`: setpoint = inlet + 3 K while on) | +1.0 ± 0.5, worse (energy -3.3, comfort cost +4.7; mean |error| 0.61 vs 0.51 !) | -2.6 ± 5.0, mean air 22.16 ! | **-4.0 ± 1.5, better on every mandatory variant** (`flat_load` +2.5) | +2.3 ± 2.6 ! |
| pulses at 40 °C, 3-h period | +10.6 ± 5.0, worse | +18.2 ± 4.3, worse | +19.1 ± 7.6, worse | +1.5 ± 1.4 |
| reference with restart_delta 2 | +12.8 ± 0.6, worse | +34.4 ± 8.1, worse | +16.4 ± 11.5, worse | +3.6 ± 2.8 |

(`!` = breaks a constraint. Variants: `partload_lo`, `partload_hi`, `frost_melt_lo`,
`frost_melt_hi`, `light_slab`, `heavy_slab`, `sun_plus30`, `sun_minus30`, `forecast_pessimistic`
and the diagnostic `flat_load`; per-variant results in the private
`.local/lab-results/sim_validation/review2_probes.txt`.)

- **Comfort trades no longer win.** The two day/night shifts saved 0.2-1.6 % of energy and gave it
  back in comfort: adjusted -0.1 % ± 2.6-4.6 over the season (round 2 review: -0.78 % ± 0.58 and
  -0.55 % ± 0.13 as wins), worse in the dull December week. Running 0.09 K cold is worse
  everywhere and breaks the ±0.05 K mean-air constraint.
- **Low-and-slow running can now be decided.** In `dec_damp` long low-power runs are better by
  4.0 ± 1.5 % on all mandatory variants, including both part-load bounds (-2.6 % with
  `partload_lo`, -5.6 % with `partload_hi`); only the diagnostic `flat_load` disagrees (+2.5 %).
  Over the season the probe saves 3.3 % energy but tracks the room worse (mean |error| 0.61 against
  0.51 K) and comes out +1.0 % ± 0.5 after the comfort price: the shape is promising, the probe's
  room control is not. That is the owner's central question, now answerable by a candidate that
  holds the room as well as the baseline.
- **Start costs.** Every probe's verdict is the same at 0.05 and 0.3 kWh per start except where
  the interval spans zero anyway; the break-even start costs of the shifts are 0.24-0.30 kWh (they
  add 0.3-0.4 starts a day), so they would need a start cost below that to show any saving.
- **Normalisation check** (`validate_sim normalisation`, reference aimed at -0.5 / 0 / +0.5 K,
  ranking energy per K of mean air): oct_mild +13.9 %/K (the 25 °C setpoint floor makes the
  colder aim asymmetric there), nov_mixed +1.9, jan_cold 0.0, mar_shoulder +0.6, season +3.5 %/K.
  The ±0.05 K mean-air tolerance is therefore worth at most 0.2 % over the season (0.7 % in
  oct_mild).
- **The round-1 probes under the new rules** (`validate_sim review`, 5 seeds, nominal): no probe is
  `better` anywhere. 'Heating off for the last 18 h' is +0.7 ± 1.9 % (nov_mixed) to +2.1 ± 4.3 %
  (oct_mild), undecided; 36 h is worse (+5.7 to +10.4 %); restart_delta 2 +32 % (nov_mixed); PWM
  7/13 min +85 %; the setpoint flapper +151 %; the plain reference (round-1 gains) +0.3 to +1.7 %
  against the tuned one.
