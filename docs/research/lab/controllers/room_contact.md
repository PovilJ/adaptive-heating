# room_contact: room-thermostat on/off with a weather-curve water temperature (S7)

`lab/controllers/room_contact.py` (stdlib only, `CONTROLLER = RoomContact`, self-check:
`.local/lab-venv/bin/python -m lab.controllers.room_contact`).

Strategy S7 of `docs/research/HEAT_PUMP_CONTROL_RESEARCH.md`, done with setpoint writes instead of a
thermostat relay. **The room decides when the heat pump runs. A weather curve decides how warm the
water is while it runs.** The firmware never decides a start or a stop on its own.

All numbers are from the lab simulator (season 2025-10-15 .. 2026-04-15, noisy forecast, measured
link outages), paired against `reference_tuned`, tuned on seeds 0-2 only.

## 1. Result in one table

> **Current version: after the second review (section 10).** Season, seeds 0-2: **-7.41 % ± 0.75**
> (c = 0.05: -7.59, c = 0.3: -7.29), `better`, break-even 6.3 kWh/start; energy alone -3.11 %,
> comfort -404 K-h (mae 0.42 vs 0.51 K), mean air 21.99, 2.4 vs 2.0-2.1 starts/d, 9.8-10.1 vs
> 9.3-9.8 writes/d, mean outlet while running 31.0-31.1 vs 30.0-30.3 °C; better on all 20 robust
> variants (seeds 0-1), no constraint break. **Read it as a comfort / sun-anticipation controller,
> not as the answer to "too hot water, too many starts"**: it makes both slightly worse. The
> table below is the pre-review version, kept for the record; section 9 is round 1.

| | reference_tuned | room_contact |
|---|---|---|
| adjusted energy, c = 0.2 kWh/start (season, seeds 0-2) | 0 | **-7.39 % ± 0.80** (c = 0.05: -7.57, c = 0.3: -7.27), `better` |
| normalised electricity (energy alone) | 0 | **-2.97 %** |
| metered electricity | 0 | -2.98 % |
| comfort, K-hours of \|air - target\| | | **-415 K-h** (mean \|error\| 0.42 vs 0.51 K) |
| mean air | 22.00-22.01 | 21.99-22.00 |
| starts per day | 2.0-2.1 | 2.4 (break-even start cost 6.2 kWh) |
| writes per day | 9.3-9.8 | 9.5-10.2 |
| mean outlet while running | 30.0-30.3 °C | **31.4 °C** (warmer, see section 2.3) |
| median run | 270-288 min | 209-238 min (6-7 % of runs under 60 min) |
| robust variants (20, seeds 0-1) | | **better on all 20**, -5.2 % (`low_flow`) to -9.4 % (`partload_hi`), no constraint break |

About 60 % of the adjusted gain is comfort (415 K-h x 0.54 kWh = 224 kWh, about 4.6 % of the
baseline's electricity) and 40 % energy. The energy gain sits mostly in days below -4 °C
(flag `cold_share`, section 8); the comfort gain sits mostly in mild, sunny weather.

## 2. The idea and the physics

### 2.1 When: the room, projected ahead

The slab carries heat into the room for hours after a run (time constants 2.2 h and 11 h,
HOUSE_MODEL.md), so a thermostat on the present reading overshoots after every run and
undershoots after every pause. The controller therefore switches on a projection:

    projected = room + slope x look_h + k_sun x (forecast global irradiation of the next sun_h hours)

- `slope`: least-squares slope of the last 120 min of room readings (sampled every 5 min,
  capped at ±0.4 K/h). The thermometer reports in 0.1 K steps on change, so a 2 h window is the
  shortest that gives a usable slope.
- `look_h` = 2 h: about the slab-to-room lag.
- the sun term: 0.6 K per kWh/m² of forecast global irradiation in the next 10 h. A clear
  March day gives 2-3 kWh/m² in 10 h, so from the small hours on the projection rises by up to
  1.2-1.8 K, and the call that would have charged the slab before the sun is skipped or cut
  short. This is the "anticipation" part of S7 extended from the slab lag to the solar gain.

A call for heat starts when `projected <= centre - 0.25 K` and ends when `projected >= centre +
0.25 K`, with a minimum call of 90 min, a minimum pause of 60 min, and no end within 30 min of a
compressor start or 10 min of a start write.

`centre` = target + `bias`. `bias` integrates (target - room) at 0.02 K per K-hour, clamped to
±1.5 K, so the long-run mean room sits on target despite the asymmetry of the projection. A room
that is warm more than 8 h after the last call (sun, occupants: nothing the controller did) counts
at half weight. With full weight the sunny spring weeks wind the bias down and the following weeks
run cold (mean 21.95, with the ±1 K clamp of steps 9-10); with zero weight the uncontrollable warm hours are never compensated and
the season mean ends at 22.08-22.15 (both break the ±0.05 K constraint, section 5).

### 2.2 How: one write to start, a curve while running, one write to stop

The Versati starts when setpoint - control sensor >= restart_delta and stops when the control
sensor is >= setpoint + 2 K (at once on a write that crosses it). Its output follows the
setpoint - control sensor error (UNIT_MODEL.md sections 3-4). So:

- **Start** (call on, compressor off, no hot water or defrost in the last 15 min): write
  `ceil(inlet - 0.7 + restart_delta + 0.4)` (idle control sensor = inlet - 0.7 K), or the curve if
  that is higher. restart_delta is set once to 5 K (a recorded value, no assumption flag).
- **Run**: setpoint = `round(24.0 + 0.33 x (22 - T_eff))`, with T_eff the mean of the 12-hour
  average of the unit's outdoor sensor and the next 6 forecast hours. That is 28.6 °C at +8,
  29.0 at +7, 31.3 at 0, 34.6 at -10 and 37.9 at -20 °C (capped at 39, the highest recorded
  setpoint). A "ride floor" keeps the setpoint no more than 1.6 K below the control sensor
  (raised to t_ctrl - 0.8 when reached), so the firmware never ends a call's run by itself;
  once the curve is above the floor, the firmware modulates the output to hold the supply near
  the curve.
- **Stop** (call off): write 25 °C (the lowest recorded setpoint). The control sensor is then
  2 K or more above it in every heating case, so the compressor stops at once. The call-off write
  is sent even during hot water, so the firmware cannot restart a heat run 7 min after a tank
  cycle.
- **Park** (10 min after the stop): write 26 °C (28 °C when T_eff is below -5 °C). With the 5 K
  gap the firmware then restarts on its own only if the control sensor falls to 21 (23) °C, i.e.
  the loop water is down to about room + 0 (+1.5) K. In normal operation the room calls first;
  the park value is a backstop for a lost Modbus link, during which the last written setpoint
  stays in force (with 25 °C parked, a 3-day outage in `jan_cold` left the house unheated:
  mean air 21.1 °C). A firmware start from the parked value is accepted as a call.
- Space heating stays enabled (`heating_enabled` is never switched off). In the simulator
  switching it off stops the circulation pump (ASSUMED, flagged `heating_off`) and saves
  unmetered indoor-unit power that the ranking does not count; using it would rest on an
  unvalidated assumption and was not tried.

Writes: one start, one or two curve or floor corrections, one stop and one park per call: 9.5-10.2 a day.

### 2.3 Why the curve is not "as low as possible"

The strategy brief says "low water". In this simulator the lowest water is not the cheapest:

- During a run the supply temperature is set by the output, not the other way round: supply ≈
  slab + Q / 1.43 kW/K (loop effectiveness 0.71 x 2.02 kW/K). Riding at minimum output (about
  4 kW) gives the coolest water; 6 kW costs about 1.4 K more.
- The unit model's COP rises from minimum output to about 6 kW by 12-25 % (central fit, measured
  4.7 at 3-4 kW vs 5.5 at 5-7 kW) and loses 3.2-3.7 % per K of supply. 1.4 K costs about 5 %;
  the output gain is 12-25 %. So 5-6 kW wins by roughly 7-20 % per kWh of heat.
- The tuning agrees (section 5): the curve that rides at minimum output (`curve_base` 20.5,
  mean outlet 29.6 °C) gets 1.1 % energy and cannot hold the room in cold weather without a trim;
  the same-outlet curve (`curve_base` 22, mean outlet 30.3 °C, equal to the baseline) gets
  -5.6 %; `curve_base` 23.5-24.5 (mean outlet 31.4 °C) is best at -7.6 %, and 25.5 (32.2 °C)
  falls back to -7.1 % (all before the park backstop, which costs about 0.2 points).

So the controller gives the owner runs and pauses decided by the room and a fixed, predictable
water temperature, with slightly more starts (2.4 against 2.1 a day) and **about 1 K warmer water
than today's baseline**, not cooler. This rests on the part-load COP surface; it holds on
`partload_lo` (half the output dependence), section 6.

In deep cold (below about -12 °C) the curve asks for more than the unit can give (setpoint
35-37, supply 33-34 °C, unit at maximum), the call stays on and the room sags to 21.2-21.5 °C
in long cold spells (the baseline's room sags in the same spells).

## 3. Fail-safe behaviour

| situation | behaviour |
|---|---|
| `link_ok` False | no command at all (state keeps integrating); commands wait anyway |
| room `None` or no report for 6 h | learned, sun-aware weather curve with the firmware's 5 K restart gap (section 9, R4) |
| Modbus link lost for days | idle: the parked setpoint stays and the firmware restarts only on cooled water; mid-call: restart_delta is already 10 K, so after the next firmware stop the unit restarts only when the water has fallen 10 K below the call setpoint (section 9, R2) |
| forecast missing or malformed | T_eff = 12-hour mean of the unit's outdoor sensor; sun term 0 |
| hot water, defrost and 15 min after | no start, curve or floor writes (the sensors show tank water or the defrost dip); only the call-off write |
| firmware stop during a call (120-min surge, defrost) | the call ends if the projection is already at or above the centre and the call is 45 min old, otherwise the next minute re-kicks |
| `heating_enabled` found False | owner's switch: pause, write nothing (review R7; before: set True) |

The hot-water start cannot be foreseen (exogenous in the lab), so a start written a few minutes
before a tank cycle still gives one short run now and then (`runs_lt_15min` in one of three
`feb_sunny_cold` seeds: 1 of 20 runs).

## 4. Parameters (final)

| parameter | value | role |
|---|---|---|
| `h_dn`, `h_up` | 0.25, 0.25 K | switching band around the centre, on the projection |
| `look_h`, `slope_win`, `slope_cap` | 2 h, 120 min, 0.4 K/h | slab-lag anticipation |
| `k_sun`, `sun_h` | 0.6 K per kWh/m², 10 h | solar anticipation |
| `min_on`, `min_off`, `min_run` | 90, 60, 30 min | long calls, few starts |
| `ki_bias`, `bias_lim` | 0.02 K per K-h, ±1.5 K | mean room on target |
| `aw_min`, `w_unctl` | 480 min, 0.5 | anti-windup for warm rooms long after a call |
| `curve_base`, `curve_slope` | 24.0 °C, 0.33 K/K | water during a call |
| `ride_gap`, `ride_to` | 1.6 K, 0.8 K | ride floor under the control sensor |
| `delta` | 5 K | restart_delta register (start gap) |
| `stale_min` | 360 min | no room report this long: fail-safe curve |
| `s_need0`, `s_gain` | 0.27 K/K, 0.3 per day | learned need: continuous-equivalent mean water = target + s_need x (22 - outdoor) (section 9) |
| `fb_off`, `fb_sun` | +1.7 K, 3 K per kWh/m² | fail-safe setpoint = need + fb_off - fb_sun x forecast sun of 10 h (section 9) |
| `cap_margin`, `cap_cold`, `cc_lo`, `cc_hi` | 5 K, 3.5 K, 0 °C, +5 °C | call setpoint and ride floor never above need + 3.5 K at T_eff <= 0 °C, need + 5 K at >= +5 °C, linear between (sections 9, 10) |
| `call_delta` | 0 (off) | round 1 wrote 10 K while a call ran; off since round 2, so only the 5 K value used on the real unit is ever written (section 10) |
| `park`, `park_cold`, `park_cold_below`, `park_warm`, `park_hold`, `park_after` | 26 °C, 28 °C, -5 °C, 0.6 K, 60 min, 10 min | idle setpoint between calls (link-loss backstop); 28 °C only while the room is below centre + 0.6 K |
| `park_pre`, `park_pre_k`, `park_pre_to` | 1 K, 0.5 K, 27 °C | the 28 °C park steps down to 27 °C when the water is within 1 K of its restart point and the projection is >= centre + 0.5 K (section 10) |
| `st_budget`, `kick_over`, `cap_warm` | 0, 99, 0 (off) | start budget, kick ceiling and warm-room ceiling, tried in round 2 and left off |
| `park_run`, `cap_pause` | 60 min, 60 min | minimum run of a parked start into a room that does not need heat; pause after a stop at the cap |
| `natural_ends`, `renew_kick` | 1, 4 min | firmware stops end a satisfied call; repeat a start write that did not start |

House and unit knowledge hard-coded: the sensor offsets (inlet - 0.7, outlet - 0.5 K for the
control sensor), the 25-39 °C recorded setpoint range and the firmware rules. Adapted online: the
switching centre. Not adapted: the curve (a trim was built and dropped, section 5).

## 5. Tuning record (season, seeds 0-2, adjusted % at c = 0.2 unless noted)

| step | change | adjusted % | notes |
|---|---|---|---|
| 0 | skeleton found in place (earlier attempt): kick, ride at inlet + 1.5, PI-style trim | -0.50 ± 0.32 | outlet 30.9 °C, 2.4 starts/d |
| 1 | rewrite: ride floor, start/stop writes, trim only after 3 h of call | -2.30 ± 0.51 | mean air 22.09 (breaks); trim ratcheted to +4 K so mild runs ran at 8-10 kW and 33 °C |
| 2 | trim leaks outside long calls | -3.45 (curve_base 22.2) / -3.72 (20.5) | mean air still 22.05-22.08 |
| 3 | bias clamp ±1 K, solar term k_sun 0.1 / 0.2 / 0.4 | -3.93 / -4.74 / -5.85 | spring overheating (sun on a charged slab) was the warm bias |
| 4 | k_sun 0.6 / 0.9, look_h 1 / 3 h | -6.26 / -6.80, -6.08 / -6.29 | mean air drifting to 21.96 |
| 5 | curve step-down on warm call ends, k_down 0 / 0.2 / 0.5 / 1 | -6.26 / -6.05 / -5.51 / -4.30 | lowering the water in cold costs energy in this model |
| 6 | robust, seeds 0-1, k_down 0 and 0.5 | better on all 20 | but mean air 21.90-21.95 on 4 variants |
| 7 | fixed curve, no trim: base 20.5 / 22 / 23.5 / 25 (slope 0.37) | -3.26 / -5.89 / -6.48 / -5.79 | slope 0.30 / 0.45 at 23.5: -6.14 / -5.63 |
| 8 | base 24, slope 0.33 | -6.69 | trims ±2 K: -5.9 .. -6.4 |
| 9 | anti-windup of the bias (warm room > 4-8 h after a call ignored) | -7.4 .. -7.9 | mean air 22.08-22.15 (breaks) |
| 10 | warm-room weight w_unctl 0.2 / 0.4 / 0.6 | -7.66 / -7.40 / -7.11 | mean 22.05 / 22.02 / 22.00: 0.5 chosen |
| 11 | band 0.1 / 0.25 K, look 1.5 / 3 h, slope window 60 / 180 min | -7.06 .. -7.28 | flat; 0.25 K cuts starts 2.5 -> 2.2/d |
| 12 | band 0.35 K; min times 150/90 and 60/45; natural_ends off; sun_h 10 | -6.57 (2.0 starts/d); -6.92; -7.15; -7.17; **-7.62** | |
| 13 | min_run 30 min; trim (ki 0.15-0.3, k_down 0.15-0.3) re-tested | -7.67; -7.04 .. -7.30 | trim removed: it changes neither the season nor the cold weeks |
| 14 | ablations (below) | | |
| 15 | fail-safe curve 21.0 + 0.37 x (22 - T) | | no-room season mean 22.20 (23.7 with the run curve) |
| 16 | call-off write also during hot water; no call end within 10 min of a start write | -7.57 ± 0.86 | removes a 6-14 min run after some tank cycles |
| 17 | robust check: `minute_only` mean air 21.94-21.95 (centre clamped at +1 K in the cold weeks); upward-only curve trim 0.3 / 0.6 / 1.0 K per K-h re-tested | nominal -7.23 / -7.12 / -6.84 | `minute_only` still 21.94-21.95: trim dropped again |
| 18 | bias clamp ±1.5 K (and ki_bias 0.03) | -7.60 ± 0.92 (-7.37) | `minute_only` 21.98 (21.97) |
| 19 | `long_outage` check: parking at 25 °C leaves the unit off for the whole outage (`jan_cold` +6.4 %, worse, mean air 21.10). Parked setpoint 27 / 28 everywhere: seeds 0-1 -5.3 / -3.9 (unwanted firmware starts in mild weather); 26: -7.45; 26 with 28 below -5 °C: -7.54 (`jan_cold` outage -3.9 %, mean air 21.89) | **-7.39 ± 0.80** | final: starts 2.2 -> 2.4/d, writes 7 -> 10/d |

Ablations at step 14 (season, seeds 0-2):

| variant | adjusted % | energy % | comfort K-h | mean outlet | mean air |
|---|---|---|---|---|---|
| step-13 configuration | -7.67 | -2.79 | -446 | 31.4 | 22.00 |
| no solar term (k_sun 0) | -3.17 | -1.59 | -154 | 31.5 | 22.02 |
| curve at the baseline's water (base 22) | -5.62 | -1.90 | -334 | 30.3 | 21.98 |
| minimum-output riding (base 20.5) | -1.04, undecided | -1.12 | +5 | 29.6 | 21.86 (breaks) |
| minimum-output riding, no solar term | +1.98, worse | -0.11 | +187 | 29.6 | 21.89 (breaks) |
| hotter curve (base 25.5) | -7.07 | -2.36 | -438 | 32.2 | 22.01 |
| bias without anti-windup | -6.82 | -2.78 | -372 | 31.4 | 21.95 |

The classic S7 (room on/off, minimum-output water, no solar look-ahead) is not better than the
baseline here. What makes it better is the solar anticipation (about 4.5 points), a curve that
runs the unit at 5-6 kW (about 6 points over minimum output) and the anti-windup of the switching
centre (about 1 point).

Per daily-mean outdoor band (seed 0, final vs baseline):

| band | days | starts/d | median run, min | output kW | outlet °C | heating COP | defrosts/d | kWh/d | mean \|error\| K |
|---|---|---|---|---|---|---|---|---|---|
| below -5 °C | 45 | 2.53 vs 1.49 | 232 vs 771 | 7.7 vs 6.0 | 32.6 vs 31.4 | 2.55 vs 2.47 | 11.6 vs 10.8 | 46.0 vs 47.8 | 0.41 vs 0.43 |
| -5..0 | 26 | 2.38 vs 2.04 | 274 vs 442 | 6.7 vs 5.3 | 32.1 vs 30.7 | 2.92 vs 2.88 | 9.8 vs 8.9 | 35.1 vs 34.9 | 0.25 vs 0.31 |
| 0..+3 | 37 | 2.30 vs 2.32 | 239 vs 340 | 6.2 vs 5.0 | 31.1 vs 29.9 | 3.23 vs 3.17 | 5.3 vs 5.0 | 24.0 vs 24.5 | 0.40 vs 0.47 |
| +3..+6 | 38 | 2.29 vs 2.58 | 234 vs 243 | 5.5 vs 4.9 | 30.2 vs 29.3 | 3.80 vs 3.64 | 1.8 vs 2.3 | 14.5 vs 15.8 | 0.43 vs 0.58 |
| above +6 | 36 | 2.22 vs 2.44 | 174 vs 243 | 5.4 vs 4.8 | 29.4 vs 28.4 | 4.32 vs 4.03 | 0.7 vs 0.9 | 9.9 vs 10.1 | 0.48 vs 0.63 |

(heating COP here = loop heat / outdoor-unit electricity of the band, including standby and
defrost.)

## 6. Robustness (season, seeds 0-1, 20 mandatory variants)

| variant | adjusted % (c = 0.2) ± 90 % | c = 0.05 / 0.3 | verdict | energy % | comfort K-h | starts/d (base) | mean air | mae (base) | flags |
|---|---|---|---|---|---|---|---|---|---|
| forecast_pessimistic | -7.13 ± 1.53 | -7.33 / -7.00 | better | -2.94 | -400 | 2.4 (2.1) | 21.99 | 0.42 (0.51) | cold_share |
| frost_melt_hi | -7.67 ± 1.56 | -7.89 / -7.51 | better | -3.27 | -423 | 2.4 (2.0) | 21.99 | 0.41 (0.51) | cold_share |
| frost_melt_lo | -7.69 ± 1.86 | -7.88 / -7.57 | better | -3.11 | -433 | 2.4 (2.1) | 21.99 | 0.41 (0.51) | cold_share |
| heavy_slab | -8.07 ± 3.88 | -8.24 / -7.96 | better | -3.01 | -472 | 2.3 (2.0) | 22.01 | 0.42 (0.53) | cold_share |
| high_flow | -8.08 ± 2.09 | -8.25 / -7.96 | better | -3.37 | -425 | 2.2 (1.9) | 22.01 | 0.42 (0.52) | cold_share |
| high_start_loss | -7.29 ± 2.11 | -7.46 / -7.18 | better | -2.76 | -431 | 2.4 (2.1) | 21.99 | 0.41 (0.51) | cold_share |
| legacy_cop | -5.44 ± 2.07 | -5.64 / -5.31 | better | -0.77 | -435 | 2.4 (2.1) | 21.99 | 0.41 (0.51) | min_off |
| light_slab | -6.57 ± 1.94 | -6.77 / -6.43 | better | -3.15 | -331 | 2.7 (2.3) | 21.96 | 0.41 (0.49) | min_off,cold_share |
| loss_minus20 | -5.82 ± 0.77 | -6.36 / -5.45 | better | -3.77 | -231 | 3.1 (2.2) | 21.99 | 0.47 (0.53) | cold_share |
| low_flow | -5.21 ± 0.31 | -5.56 / -4.98 | better | -2.09 | -339 | 2.9 (2.2) | 21.97 | 0.43 (0.51) | cold_share |
| minute_only | -6.38 ± 4.70 | -6.56 / -6.26 | better | -2.47 | -412 | 2.3 (2.0) | 21.97 | 0.43 (0.52) | cold_share |
| nominal | -7.54 ± 2.51 | -7.71 / -7.43 | better | -2.95 | -431 | 2.4 (2.1) | 21.99 | 0.41 (0.51) | cold_share |
| partload_hi | -9.43 ± 3.68 | -9.64 / -9.28 | better | -4.93 | -433 | 2.4 (2.0) | 21.99 | 0.41 (0.51) | cold_share |
| partload_lo | -6.37 ± 1.89 | -6.56 / -6.24 | better | -1.58 | -449 | 2.4 (2.1) | 22.00 | 0.41 (0.51) | min_off,cold_share |
| raw_return | -5.65 ± 0.80 | -5.87 / -5.50 | better | -2.75 | -288 | 2.5 (2.1) | 22.01 | 0.45 (0.51) |  |
| shallow_outlet | -7.74 ± 2.87 | -7.96 / -7.58 | better | -3.32 | -426 | 2.4 (2.0) | 21.99 | 0.41 (0.51) | cold_share |
| sluggish | -7.66 ± 3.35 | -7.88 / -7.51 | better | -3.06 | -439 | 2.4 (2.0) | 21.99 | 0.41 (0.51) | cold_share |
| steep_outlet | -7.73 ± 2.87 | -7.90 / -7.61 | better | -2.97 | -445 | 2.4 (2.1) | 22.00 | 0.41 (0.51) | cold_share |
| sun_minus30 | -6.27 ± 2.75 | -6.61 / -6.05 | better | -3.52 | -274 | 2.7 (2.1) | 21.99 | 0.45 (0.52) | cold_share |
| sun_plus30 | -7.85 ± 1.74 | -7.96 / -7.78 | better | -2.61 | -502 | 2.2 (2.0) | 22.02 | 0.42 (0.53) | cold_share |

**Better on all 20 mandatory variants, no constraint break.** Weakest: `low_flow` (-5.2 %, 2.9
starts/d), `legacy_cop` (-5.4 %, energy only -0.8 %: the old COP model has no part-load penalty
to avoid), `raw_return` (-5.7 %, comfort gain halves) and `loss_minus20` (-5.8 %, 3.1 starts/d: in
a better-insulated house the loop water cools to the parked backstop more often). The comfort
gain (-230 to -500 K-h) is present on every variant. Flags: `cold_share` on most (energy savings
mostly below -4 °C; not on `legacy_cop` and `raw_return`), `min_off` on a few (a start waited
for the ASSUMED 3-min minimum off time, rare).

## 7. Weeks (diagnostic, seeds 0-2)

| week | adjusted % ± 90 % | verdict | energy % | comfort K-h | metered % | starts/d (base) | mean air | mae (base) | flags / breaks |
|---|---|---|---|---|---|---|---|---|---|
| oct_mild | -39.43 ± 7.21 | better | -10.56 | -28 | +2.12 | 1.7 (1.9) | 22.10 | 0.49 (0.66) | mean air 22.07,mean air 22.08,mean air 22.16 |
| nov_mixed | -7.66 ± 5.71 | better | -1.25 | -15 | +0.40 | 3.3 (3.2) | 22.02 | 0.27 (0.36) | mean air 22.06 |
| dec_damp | -3.29 ± 1.67 | better | -2.83 | -3 | -2.79 | 3.0 (2.5) | 21.95 | 0.26 (0.28) | mean air 21.90 |
| jan_cold | -3.45 ± 0.90 | better | -3.55 | -2 | -3.37 | 2.5 (1.2) | 21.86 | 0.46 (0.48) | cold_share,mean air 21.76,mean air 21.83 |
| feb_sunny_cold | -6.31 ± 2.79 | better | -4.33 | -16 | -1.77 | 3.6 (1.3) | 21.96 | 0.51 (0.60) | cold_share,mean air 21.89 |
| mar_shoulder | -13.93 ± 10.03 | better | -1.88 | -16 | +7.29 | 1.7 (1.6) | 22.23 | 0.89 (0.99) | mean air 22.18,mean air 22.21,mean air 22.31 |
| apr_mild_sunny | -25.28 ± 55.88 | undecided | -6.88 | -21 | +0.77 | 1.1 (1.1) | 22.42 | 0.94 (1.06) | mean air 22.36,mean air 22.91 |

The weeks break the mean-air constraint in both directions. In the sunny mild weeks the house
overheats on its own and the controller's switching centre, starting from zero after the
reference warm-up, cannot pull the week's mean back (the baseline is aimed per week with
hindsight). In the cold weeks the unit is at its maximum for days and the room sags to 21.8 °C,
and the 28 °C parked backstop adds firmware starts (`feb_sunny_cold` 3.6 against 1.3 a day). The
mild weeks' adjusted percentages are large because the baseline's window electricity is small and
the run-out normalisation dominates; read them as signs only. The season is the ranking.

## 8. Known weaknesses

- **Warmer water than the baseline** (31.4 vs 30.0-30.3 °C mean outlet while running). The gain over
  minimum-output riding rests on the unit model's part-load COP surface; it survives
  `partload_lo`, but on the real unit the two-hold test of UNIT_MODEL.md section 7.2 should come
  first. The owner-preferred setting `curve_base=22` (same water as today) scored -5.6 % (step 14,
  before the park backstop).
- **Most of the score is comfort and solar anticipation.** Without the sun term the controller
  scored -3.2 % (step 14). The solar gain depends on the forecast's irradiance skill and on the house model's
  solar apertures (it holds on `sun_plus30`, `sun_minus30` and `forecast_pessimistic`).
- **Energy savings concentrate below -4 °C** (`cold_share`): pulsing at 7-8 kW with long pauses
  is cheaper there only because the model's COP keeps rising with output below -5 °C. That regime
  has 3 clean validation days.
- **Deep cold, capacity-limited**: the room sags to 21.2-21.5 °C for days in January (min air
  19.7-20.2 °C over the season, baseline 19.5-20.2); a forecast pre-charge before a cold spell (S8/S9)
  is not part of this strategy.
- **Weekly mean air** off by up to ±0.3 K in short windows (section 7); the switching-centre
  integrator needs weeks, and it deliberately undercools after uncontrollable sunny spells to
  hold the season mean.
- **Starts**: 2.4 a day against 2.0-2.1; 6-7 % of runs are shorter than an hour (calls ended
  by a firmware surge stop or a hot-water cycle). The parked backstop setpoint adds about 0.2 a day
  on the season and more in cold weeks (`feb_sunny_cold` 3.6 against 1.3 a day; `loss_minus20`
  and `low_flow` 2.9-3.1): when the loop water falls to the backstop the firmware starts before the
  room asks. Without the backstop (`park=0`) the season is -7.6 % at 2.2 starts a day but a lost
  link in a cold spell leaves the house unheated. A wider band (0.35 K) gave 2.0 starts/day at
  -6.6 % (step 12).
- **Lost link** (updated in section 9): mid-call the 10 K restart_delta (ASSUMED register
  behaviour) bounds the overheating; in the idle phase the 26/28 °C park under-heats a cold spell
  (room 21.1-21.7 °C over a 3-day outage). The real integration should also alarm on a lost link.
- **Room thermometer dependence**: one living-room sensor decides everything; a misplaced or
  sun-lit sensor biases the whole house. Without it the learned fallback curve (section 9) holds
  21.9-22.2 °C with a 0.62 K mean error, about 5 % worse than the baseline.
- **Hot water is exogenous** in the lab: a start a few minutes before a tank cycle gives a short
  run now and then.

## 9. Review fixes (2026-11-07)

An adversarial review (seeds 3-4, its own wrappers) confirmed the headline but found four major
problems. All numbers below are seeds 0-2 (season, weeks) or 0-1 (robust); seeds 3-4 and 5-9 were
not run by me. Results: `.local/lab-results/controllers/room_contact/fix_*`.

### R1: the 28 °C cold park forced heat into a warm room (real, fixed)

A firmware start from the parked setpoint was accepted as a call and then locked for `min_on` = 90
min. With 28 °C parked below -5 °C, in `feb_sunny_cold` it started the compressor into rooms at
22.3-24.7 °C. Changes:

- the 28 °C park is written only while the room reads below centre + 0.6 K (`park_warm`); the
  choice is re-made at most hourly (`park_hold`), otherwise 26 °C;
- a parked start into a room whose projection is not below the centre is no longer locked for
  90 min: it may end after `park_run` = 60 min (30 min was tried: season -7.55 % but 12-13 % of
  runs under an hour and 3.2 starts/d in `feb_sunny_cold`; 90 min: -7.19 %, 2.5 starts/d).

`feb_sunny_cold` (seeds 0-2): 2.9 starts/d against 1.3 for the baseline, `better` -6.10 ± 2.64
(before: 3.6/d; with the cold park removed entirely, 2.2/d but the idle-phase 3-day outage in
`jan_cold` left the room at 21.2 °C, +2.9 % worse). The reviewer's 5-6 starts/d came from seed 3;
I did not rerun it.

### R2: a link lost mid-call held the hot call setpoint for days (real, fixed by a new mechanism)

A ceiling on the call setpoint alone does not work: on/off control needs water about 3 K above
the continuous need, so a ceiling at need + 2 K cost 9 points and broke mean air (season -1.6 %,
mean air 21.91-21.95), need + 3 K cost 1.6 points, need + 4 K 0.5 points. What the unit keeps
during an outage is both registers, so the fix uses the second one:

- **once a call's run is 5 min old, restart_delta is written to 10 K (`call_delta`)**; it is
  written back to 5 K with the next start kick or with the call-off write. During normal
  operation nothing changes (the controller starts every run itself with a kick that already
  writes 5 K). If the link dies mid-call, the firmware runs on until its next stop (stop
  threshold, 120-min surge, defrost) and then restarts only when the control sensor has fallen
  10 K below the call setpoint, i.e. it degrades into a long-pause on/off at the water side;
- a learned ceiling need + 5 K on the call setpoint and the ride floor (`cap_margin`), with a
  60-min pause after a stop at the ceiling. It rarely binds (cost 0.0 points) and is a guard
  against the ride floor ratcheting; need is learned online (R4).

Evidence, wrapper `OutInCall` (3 days without any write, starting 40 min into a call run after
day 2), seeds 0-2, adjusted % vs `reference_tuned`:

| scenario | call_delta 10 (final) | call_delta 0 (as before) |
|---|---|---|
| `feb_sunny_cold` | +0.32 ± 3.59, mean air 22.19, mae 0.63 | +6.98 ± 5.18 worse, mean air 22.36, mae 0.78 |
| `jan_cold` | +1.24 ± 12.1, mean air 22.20, mae 0.61 | +6.48 ± 11.1, mean air 22.33, mae 0.73 |
| season (outage in October) | -6.33 ± 1.76 | -7.09 ± 0.97 |

In mild October the wide hysteresis under-heats a little during the outage; in the cold weeks it
removes most of the overheating. **ASSUMED:** restart_delta values other than 4-5 K were never
recorded on the unit (register range 2-10, UNIT_MODEL.md); the ranking flags `restart_delta` on
every run for that reason. It must be checked on the real unit before deployment (write 10, watch
one natural restart). The outcome of a long outage still depends on the phase: an idle-phase
outage with 26 °C parked in a cold spell under-heats (`long_outage` `jan_cold` mean air 21.41,
one seed 21.14, -1.19 ± 4.57 undecided; `feb_sunny_cold` -0.27 ± 5.79 undecided; season -7.21 %
better). The integration should alarm on a lost link; no setpoint can be right for both phases.

### R3: the gain is comfort, sun forecast and a COP-surface effect, with hotter water (agreed, reframed)

This is correct and was already stated in sections 2.3 and 8; the fixes do not change it
(energy alone -2.93 %, `legacy_cop` energy -0.79 %, `partload_lo` -1.62 %, mean outlet 31.3 °C vs
30.0-30.3, 2.4 vs 2.1 starts/d). The result should be read as: **the room-side ideas (solar
anticipation, slab-lag projection, anti-windup centre) are worth about 4-5 % in comfort credit,
and the on/off water side is at best neutral**. Those room-side ideas could be added to a
continuous low-water controller. No efficiency claim for S7 itself should be made before the
two-hold COP test of UNIT_MODEL.md section 7.2. On the owner's two complaints this controller
makes both slightly worse (about 1 K warmer water, about 15 % more starts).

### R4: the no-room fallback was much worse than the baseline (real, improved, still worse)

The fixed curve 21 + 0.37 x (22 - T) without sun was replaced by a learned, sun-aware curve:

- while the room is known, each 24 h of non-tank, non-defrost minutes gives an estimate of the
  continuous-equivalent water the house needed: s = (mean of outlet and inlet - target) /
  (22 - mean outdoor), on days at least 8 K below 22 °C; `s_need` follows it with weight 0.3 per
  day (start 0.27, clamp 0.1-0.6). On the season s is about 0.22-0.28;
- fallback setpoint = target + s_need x (22 - T_eff) + 1.7 K - 3 K per kWh/m² of forecast sun in
  the next 10 h, with the firmware's 5 K hysteresis.

| test (seeds 0-1 unless noted) | adjusted % | mean air | mae (base 0.51) |
|---|---|---|---|
| old fallback, no room all season (`stale_min=-1`) | +31.9 worse | 22.67-22.91 | 1.08 |
| new, no room all season, seeds 0-2 | +4.93 ± 3.71 worse | 21.89-22.18 | 0.62 |
| new, room lost for good after day 45 (`RoomDies`), seeds 0-2 | +5.76 ± 9.82 undecided | 21.91-22.18 | 0.65 |
| new, no room, `jan_cold` / `feb_sunny_cold`, seeds 0-2 | +6.7 / +4.4 undecided | 22.4-22.5 | 0.62 / 0.64 |

The fallback is now a usable weather-compensated mode, still about 5 % worse than the baseline's
room-fed controller and above the mean-air band. It does not need to beat it: it is what runs
while a thermometer battery is flat.

### Minor items

- **R5** (two robust variants undecided on seeds 3-4): on seeds 0-1 all 20 are better; the two weak ones
  improved with R1: `low_flow` -6.03 ± 2.17 (was -5.21; 2.8 starts/d, was 2.9), `loss_minus20`
  -6.62 ± 3.79 (was -5.82; 2.8, was 3.1). Seeds 3-4 were not rerun here.
- **R6** (frequent link drops): not changed. Commands wait during an outage and are reissued
  when the link returns. R2 bounds the call setpoint's effect.
- **R7** (overriding the owner): fixed. `heating_enabled` False is the owner's switch: the
  controller pauses and writes nothing. restart_delta is written once at start (5 K), and
  afterwards only the controller's own 10 K is undone.
- **R8** (weekly mean air): not fixed. It is structural (section 7). Weeks, seeds 0-2: better in 5
  of 7 (`oct` -40.6, `dec` -2.8, `jan` -4.6, `feb` -6.1, `mar` -17.9), undecided `nov`
  -8.1 ± 8.2 and `apr` -27 ± 49. Mean air breaks ±0.05 K in all but `nov`.

### Final result (seeds 0-2 season, 0-1 robust)

| | reference_tuned | room_contact (after review) |
|---|---|---|
| adjusted, c = 0.2 | 0 | **-7.41 % ± 0.82**, `better` (c = 0.05 -7.60, c = 0.3 -7.28; break-even 6.0 kWh/start) |
| energy alone / metered | | -2.93 % / -2.91 % |
| comfort | | -422 K-h, mae 0.42 vs 0.51 K |
| mean air | 22.00-22.01 | 21.99-22.00 |
| starts/d | 2.0-2.1 | 2.4-2.5 (7-8 % of runs under 60 min) |
| writes/d | 9.3-9.8 | 14.2-15.0 (two restart_delta writes per call) |
| mean outlet while running | 30.0-30.3 °C | 31.3 °C |
| robust, 20 variants | | better on all 20: -5.42 % (`legacy_cop`, energy -0.79 %) to -9.60 % (`partload_hi`) |

## 10. Review fixes, round 2 (2026-11-07)

A second adversarial review (seeds 3-4) confirmed the headline and found no cheating, but found
four major issues (I1-I4) and four minor ones (I5-I8). All numbers below are mine, on seeds 0-2
(season, weeks, outage tests) or 0-1 (robust); I did not run seeds 3-9. Results:
`.local/lab-results/controllers/room_contact/r2_final_{season,robust,weeks,outage}` and `r2/`
(sweeps and outage-phase tests; wrapper `r2w/wrap2.py`, analyser `r2w/an2.py`).

### I1: a link lost during a call could hold a hot setpoint for days (real; bounded, not eliminated)

The reviewer's case (`feb_sunny_cold` `long_outage`, seed 4): the outage began one minute into a
run, before the 10 K `call_delta` was written, so the unit kept setpoint 33 °C and restart_delta
5 K and ran for 72 h; the room reached 26.1 °C. Even with 10 K written the unit ran 32 h. The
root cause is not the restart hysteresis but the setpoint: where the house can absorb the unit's
minimum output (below about +3 °C outdoor, 3.7 kW against 0.19 kW/K), a run on a frozen setpoint
never stops by itself, and the room settles about 0.8 K higher per K of mean water above the need.
Round 1 allowed need + 5 K.

Fix: **the call setpoint ceiling depends on the weather: need + 3.5 K at T_eff <= 0 °C, need + 5 K
at >= +5 °C, linear between** (`cap_cold`, `cc_lo`, `cc_hi`; need is the learned
continuous-equivalent water of section 9). The ride floor and the curve are clipped to it, so the
register a lost link freezes in cold weather is one the house can take continuously. Where the
house cannot absorb the minimum output (mild weather) the firmware stops and restarts on its own
5 K hysteresis, so a frozen mild-weather setpoint cycles instead of running for days.

Outage test (wrapper `Out` in `r2w/wrap2.py`: the controller goes silent for 3 days, starting at
a chosen point of a call after day `od`: `ph=3` two minutes into a run, i.e. before round 1's
`call_delta` write, the reviewer's case; `ph=40` 40 min into the run; `od` = 1, 2, 3, 4), seeds
0-2, 24 outages per week, room during the 3-day silence (script `r2w/hunt.sh`):

| week | round 1 code: mean of outage means (worst) / highest max | final: mean (worst) / highest max | ceiling need + 2.5 K |
|---|---|---|---|
| `feb_sunny_cold` | 22.57 (23.43) / 25.93 °C | 22.37 (22.82) / 25.65 °C | 22.11 (22.81) / 25.31 °C |
| `jan_cold` | 22.44 (23.17) / 24.86 °C | 22.40 (23.03) / 24.68 °C | 22.19 (22.90) / 24.56 °C |
| `nov_mixed` | 21.68 (20.75 lowest) / 24.79 °C | 22.15 / 25.01 °C | 22.15 / 25.11 °C |

The baseline's own week maxima without any outage are 23.4-24.0 (`jan`) and 24.3-24.8 °C (`feb`):
the highest values in this table are sunny days, which no frozen register can prevent. On seeds
0-2 I could not reproduce the reviewer's 26.1 °C (worst round-1 case here: 60 h run at 35 °C,
outage mean 23.4, max 25.0). The fix lowers the worst outage mean by about 0.5 K and the 3-day
runs now hold at most need + 3.5 K, but a 3-day silence that starts early in a cold-weather call
still runs the unit for 1-3 days and leaves the room 0.5-1 K warm. A warm-room ceiling (need + 1.5
or 2 K once the room is back at the centre, `cap_warm`, built and left off) gained only 0.1 K.
In mild sunny weather (`mar_shoulder`) a frozen 29-30 °C setpoint cycles on the firmware
hysteresis and the room runs 1-1.5 K warm for 3 days (outage mean 22.9-23.4, max 26.2 °C; round
1 with 10 K: 22.4-23.6, max 26.6); a mild ceiling of need + 4 K barely helped and cost 0.4
points, so it stays at 5 K.

The sim's `long_outage` (outage from the middle of the window, any phase), seeds 0-2: season
-6.81 ± 1.42 `better`; `jan_cold` +0.00 ± 3.48 undecided (mean air 21.14-21.68); `feb_sunny_cold`
-1.23 ± 6.71 undecided (21.22-22.11). The idle-phase backstop (26-28 °C park) still under-heats a
3-day cold outage to 20.4-21.6 °C mean (minimum 19.1 °C). No single frozen register suits both
phases; the integration should raise an alarm on a lost link and write a safe curve setpoint as
soon as it returns (the controller does the latter by construction: it writes on the first step
with `link_ok`).

Season cost of the cold ceiling (seeds 0-2): need + 2.5 K -6.55 %, + 3 K -7.16 %, + 3.5 K -7.41 %
(with the I8 change; round 1 was -7.41 %). + 3 K broke mean air on the `minute_only` robust variant
(21.95 on seed 0); + 3.5 K does not (21.97).

### I2: the energy gain comes from the COP surface and cold days (agreed, reduced, reframed)

Correct, and stated in sections 2.3, 8 and 9 (R3). The cold ceiling lowers the water in deep cold,
which moves the controller away from the "pulse at maximum output" regime the review doubted.
Share of the metered saving from days below -4 °C: 46-57 % (seeds 0-2), was 62-67 % (seeds 3-4,
reviewer). `legacy_cop`: energy alone -1.32 % (was -0.79 %), adjusted -5.72 %. `partload_lo`:
energy -2.01 %. About 58 % of the adjusted gain is still comfort credit (404 K-h x 0.54 kWh). No
efficiency claim for S7 itself should be made before the two-hold COP test (UNIT_MODEL.md 7.2).

### I3: hotter water and more starts (agreed; slightly reduced, reframed)

- Water: mean outlet while running 31.0-31.1 °C (was 31.3-31.4) against 30.0-30.3. Maximum
  setpoint written 36-37 °C (was 39).
- Starts: season 2.4/d against 2.0-2.1 (unchanged). In `feb_sunny_cold` 2.0-2.3/d (seeds 0-2;
  was 2.6 with the same code before the I8 change, and 2.9 after round 1) against 1.3; `jan_cold`
  2.1-2.4 against 1.2. The start budget the review suggested (`st_budget`: min_off 150-200 min
  once 3-4 starts happened in 24 h) was built and tried: it changed season starts by less than
  0.1/d and cost 0.1-1 points in the cold weeks, so it is off. Most of the extra starts are the
  design itself (the room, not the water, ends a run) and DHW cycles.
- The controller is reported as a comfort and sun-anticipation controller (section 1). On the
  owner's two complaints it is slightly worse than today's controller, not better.

### I4: restart_delta = 10 K was never used on the real unit (agreed, removed)

With the cold ceiling, the 10 K call_delta is no longer needed: in the outage-phase tests
`call_delta=0` was as good or better in cold weeks and clearly better in mild ones (where 10 K
left the room at 20.8-21.3 °C for 3 days), and the season scored -6.55 vs -6.45 % (at a 2.5 K
ceiling). `call_delta` now defaults to 0: the controller writes restart_delta only once at start
(5 K, the recorded value) and never again. The `restart_delta` ranking flag is gone and writes
fell from 14-15 to 9.8-10.1 per day.

### Minor items

- **I5** (stale claim): the result is restated from this code (section 1 and the structured
  result).
- **I6** (cold-week mean air): not changed. Weeks, seeds 0-2: `jan_cold` -3.87 ± 2.72 `better`,
  mean air 21.73-21.89, mae 0.47 vs 0.48; `dec_damp` -3.20 `better`, 21.92-21.98; mean air misses
  ±0.05 K in all seven weeks (structural, section 7). Forecast-cold pre-charge was not built.
- **I7** (None/NaN sensors): fixed. Unit sensors (outdoor, outlet, inlet, setpoint, restart_delta)
  that are None or NaN are replaced by their last good value (outdoor: the forecast's first hour
  if never seen); the need learning skips such minutes; a NaN room counts as missing; a
  non-numeric room age counts as stale. Covered by the self-check.
- **I8** (parked starts): fixed in part. The 28 °C cold park now steps down to 27 °C when the
  idle water is within 1 K of its restart point (control sensor <= 28 - restart_delta + 1) and the
  projected room is at least centre + 0.5 K (`park_pre`, `park_pre_k`, `park_pre_to`). In
  `feb_sunny_cold` seed 0 this removed most parked starts into sunny-morning rooms at 22.3-22.9 °C. Stepping to
  26 °C instead removed slightly more starts but made `jan_cold` `long_outage` `worse` (+2.8 %,
  room 20.2-21.0 °C over the outage); 27 °C keeps it undecided (+0.0 %).

### Final result (round 2; seeds 0-2 season, 0-1 robust)

| | reference_tuned | room_contact |
|---|---|---|
| adjusted, c = 0.2 | 0 | **-7.41 % ± 0.75**, `better` (c = 0.05 -7.59, c = 0.3 -7.29; break-even 6.3 kWh/start) |
| energy alone / metered | | -3.11 % / -3.11 % |
| comfort | | -404 K-h, mae 0.42 vs 0.51 K |
| mean air | 22.00-22.01 | 21.99 |
| starts/d | 2.0-2.1 | 2.4 (6-9 % of runs under 60 min, median run 209-243 min) |
| writes/d | 9.3-9.8 | 9.8-10.1 (robust max 11.8) |
| mean outlet while running | 30.0-30.3 °C | 31.0-31.1 °C |
| robust, 20 variants | | better on all 20, no constraint break: -5.57 % (`raw_return`) to -9.26 % (`partload_hi`); `legacy_cop` -5.72 (energy -1.32), `minute_only` -6.21 (air 21.97), `low_flow` -6.29 (2.6 starts/d), `loss_minus20` -6.46 (2.8 starts/d, break-even 2.8 kWh) |
| weeks (seeds 0-2) | | better in 6 of 7 (`oct` -40.7, `nov` -7.3, `dec` -3.2, `jan` -3.9, `feb` -6.2, `mar` -21.5); `apr` undecided -27.7 ± 49 |
