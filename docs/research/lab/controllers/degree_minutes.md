# degree_minutes: slab-scaled degree-minute controller (S4)

`lab/controllers/degree_minutes.py`, stdlib only, about 150 lines of logic plus an assert-based
self-check (`.local/lab-venv/bin/python -m lab.controllers.degree_minutes`). It implements
research strategy S4 (HEAT_PUMP_CONTROL_RESEARCH.md sections 4.3 and 8): a NIBE/Vaillant-style
degree-minute integrator, rescaled for a slab. The integrator decides **when** the compressor
runs. A setpoint ride decides **how hard** it runs. The Versati's own 4 K restart gap no longer
decides either.

## 1. Idea

Every minute:

```
t_eff = 0.7 x mean(forecast outdoor, next 12 h) + 0.3 x EMA_12h(unit outdoor sensor)
sun   = mean(forecast GHI, next 8 h)
room' = room - 0.0008 x GHI_now                       # thermometer reads warm in sun (house model)
err   = target - room'
I    += 0.15 x err dt[h]                               # clamped to ±6 K
T_c   = 25.4 + 0.21 x (target - t_eff) - 0.045 x sun + 2.0 x err + I      # target mean outlet
DM   += (outlet - T_c) x 1 min        # only while the water reading is valid; clamped to [-1200, +500]
```

- **Start** when DM <= -225 K·min (review round 2; was -250), the unit is idle and it has been off for at least 30 min.
  Write the smallest setpoint the firmware's restart rule accepts:
  ceil(inlet - 0.7 + restart_delta + 0.3). Here inlet - 0.7 is the idle control-sensor estimate
  (UNIT_MODEL.md section 2). If no start follows within 4 min, add 1 K, at most twice; then give
  up and park (review round 2).
- **Ride** (from 2 min after the compressor starts, at most one write every 15 min):
  `sp = max(inlet + q_run/2.02 - 0.8 - 0.025 (q_run - 5) + 0.55,  T_c - 0.3 - DM/120)`.
  - The first term puts the firmware's control sensor in the middle of its +0.1..+1.0 K dead
    band at the chosen output q_run = 5.5 kW. The unit then settles about 0.5 kW above it, at
    6.0-6.5 kW.
  - The second term is the continuous mode. When the house needs more than q_run, the outlet is
    held at T_c, plus a DM correction with a 2-hour time constant. This is the case below about
    -5 °C.
  - A hot start burst is not possible: the ride setpoint is 2-4 K below the kick.
- **Stop** when DM >= +200 K·min (review round 2; was +120) and the run is at least 40 min old.
  Write `min(park, floor(outlet - 3.0))`, never below 25 °C. This crosses the
  firmware's stop threshold (t_ctrl >= sp + 2 K), so the compressor stops at once. The controller
  then waits in a `stopping` state until the compressor is off, and steps 1 K lower every 3 min if
  it is not (review fix R3). If the 25 °C floor cannot stop a cool run within 30 min, the run is
  handed back to the ride.
- **Park** at max(25, round(T_c - 3)). It acts as a low thermostat if Home Assistant goes away.
  The park setpoint is refreshed only when it is 2 K off and the write cannot trigger a firmware
  start. **Guard** (review fix R4): while idle and DM does not ask for heat, when setpoint -
  (inlet - 0.7) reaches restart_delta - 0.6 K, the park is pulled to 1 K under the restart
  threshold, never below 25 °C. Without the guard the park did let the firmware start on its own
  as the loop cooled.
- **Unexpected stops** (120-min surge, post-defrost, hot water) end the run. The controller
  parks, and DM decides the next start.
- **Registers:** setpoint only, always inside the recorded 25-39 °C range (review round 2: the
  24 °C guard park and the 22 °C stop floor of round 1 are gone, and so is the `setpoint_range`
  flag). restart_delta stays at the unit's 4 K, and quiet mode stays off.
- **Fail-safe behaviour.**
  - Link down, or any of outdoor/outlet/inlet/setpoint/restart_delta unavailable (None or not
    finite): no writes. DM, the states and the outdoor average are frozen. The room integral keeps
    learning from the thermometer for the first 120 min of an outage, then freezes.
  - Hot water: while the unit reports `dhw` and for 10 min after, DM is frozen, because the
    sensors read tank water. A run interrupted by hot water counts as stopped.
  - Defrost: no state change. DM keeps integrating the cold defrost outlet on purpose: the
    defrost draws real heat from the loop, so it is a true deficit.
  - Room missing, or not reported for 90 min: the room terms drop out and I freezes.
  - Forecast missing: the hours of the last forecast still ahead of now are used (a stale issue).
    With none left, t_eff falls back to the smoothed unit sensor, the sun term is 0, the
    thermometer glow correction uses irradiance from PV (112 W/m² per kW, SIMULATOR.md, re-learnt
    online while forecast and PV are both known), and the room integral runs 1.5x faster.
  - Space heating off at hand-over: switched on once. Switched off later (by the owner):
    respected, no writes.
  - A start that the firmware makes on its own is adopted as a run.

## 2. Physics behind it

- **DM measures the slab's heat deficit.** The circulation pump never stops, so while the
  compressor rests the outlet reads loop water at about slab temperature. While it runs, the
  outlet sits at slab + Q/1.43 K (loop effectiveness 0.71 at 29 L/min, HOUSE_MODEL.md).
  ∫(outlet - T_c) is therefore about (slab-temperature deficit + delivered heat / 1.43 kW/K)
  integrated over time, roughly 42 K·min per kWh. The start/stop swing of 370 K·min is a cycle of
  roughly 7-9 kWh, which is 1.5-2 K of slab (4.4 kWh/K). After a sunny afternoon the idle water
  is warm, DM barely falls, and the next start is delayed by itself.
- **The output level, not the lowest water temperature, is the efficiency lever in this model.**
  - The COP surface (UNIT_MODEL.md section 7.2) puts the minimum output 12-25 % below the 6-kW
    COP. That is more than the 3.3 %/K penalty for the 1.2-1.7 K of extra supply that 6 kW needs.
  - The baseline's firmware-driven runs settle at 4.8-5.3 kW. This controller holds 6.0-6.5 kW
    for 3-8 h runs.
  - Its mean running outlet is therefore **higher** (31.1 vs 30.3 °C), but its running COP is
    higher too (4.39 vs 4.08 at +3..+6 °C; 5.21 vs 4.72 above +6 °C).
  - A ride at the floor (q_run 3.5) saved only 1.65 % energy, against 3.7 % at q_run 5.5.
- **Sun anticipation does most of the comfort work.** Solar gain through the east, south and
  west glazing reaches several kW on clear days, comparable to the whole heat load. The slab
  delivers heat with a 2-6 h lag. Lowering T_c by up to about 10 K when the next 8 h are forecast
  sunny stops the heating before the sun arrives. The fitted coefficient is about 4-5x the steady
  "kW of sun per kW of load" equivalent, because an 8-h mean includes dark hours and the lag
  needs a lead.
- **Thermometer glow.** The house model's thermometer reads about 0.8 mK per W/m² warm in sun.
  Without the correction, the room integral holds the sensor (not the air) on target, and the
  mean air sits 0.03-0.04 K low.

## 3. Parameters (final defaults)

| group | parameter | value | role |
|---|---|---|---|
| curve | c0, c1 | 25.4 °C, 0.21 K/K | mean outlet at outdoor = target; slope. Fitted on the baseline's season run (daily mean outlet = 25.4 + 0.18 (22 - T_out) - 0.022 GHI_day; slope then tuned) |
| | h_fc, w_fc, tau_out_h | 12 h, 0.7, 12 h | forecast horizon, its weight, EMA of the unit sensor |
| | sun_k, h_sun | 0.045 K per W/m², 8 h | forecast-sun term |
| room | kp, ki, i_lim | 2.0 K/K, 0.15 K/(K h), ±6 K | proportional, integral, clamp |
| | glow | 0.0008 K per W/m² | thermometer sun correction (house model) |
| DM | dm_start, dm_stop | 225, 200 K·min | start and stop thresholds (round 2; were 250, 120) |
| | dm_lo, dm_hi | 1200, 300 K·min | anti-windup (deficit; surplus above dm_stop) |
| run | q_run | 5.5 kW | ride output |
| | tau_dm | 120 min | DM feedback in continuous mode |
| | min_run, min_off | 40, 30 min | |
| | ride_gap | 15 min | minimum spacing of ride writes |
| | park_margin | 3 K | park below T_c |
| | guard, guard_margin, park_floor | on, 0.6 K, 25 °C | keep the idle park under the restart threshold (round 2; was 24) |
| | sp_stop | 25 °C | lowest stop write (round 2; was 22) |
| | dm_ride_cap | 3 K | most the deficit may lift the continuous-mode ride setpoint |
| room | room_stale_min | 90 min | room terms drop out after this |
| | ki_nofc | 1.5 | integral speed-up when no forecast hour is usable (round 2) |
| | pv_ghi | 112 W/m² per kW | PV -> irradiance for the glow correction without forecast (round 2) |
| | int_outage_min | 120 min | room integral keeps running this long into a link outage (round 2) |
| | max_starts | 7 per 24 h | beyond it the start threshold doubles (never reached) |

Hard-coded unit knowledge, all from UNIT_MODEL.md:

- idle t_ctrl = inlet - 0.7;
- running t_ctrl = supply - 0.8 - 0.025 (Q - 5);
- dead band +0.1..+1.0 K;
- 2.02 kW/K at 29 L/min (a scale only);
- recorded setpoint range 25-39 °C (kept by every write since review round 2).

The room integral absorbs the house numbers (curve level and sun gain). The flow scale only
shifts the realised ride output, and the low_flow and high_flow variants pass.

## 4. Tuning record (season, seeds 0-2, nominal, paired against reference_tuned)

"adj" is the ranking's adjusted energy in % of the baseline's window electricity, given at start
costs c = 0.05 / 0.3 kWh. Negative is better.

| step | change | adj .05 / .3 | energy % | comfort K-h | mean air | starts/d | note |
|---|---|---|---|---|---|---|---|
| v0 | first build: kp 1.5, ki 0.3, sun 0.01, q_run 5.5, DM 300/60, sp max 45 | -4.33 / -3.53 | -3.04 | -129 | 22.02 | 2.9 | `setpoint_range` and `cold_share` flags; robust: better on all 20, but mean air 22.05-22.08 on loss_minus20, raw_return, sun_minus30 |
| | sp max 39 | | | | | | `setpoint_range` gone |
| | q_run 4.5 / 6.5 | -3.48 / -2.96, -4.64 / -3.53 | -1.98, -3.58 | | | 2.6, 3.2 | |
| | sun_k 0 / 0.02 / 0.03 / 0.04 | -1.43, -5.16, -5.89, -6.33 (c .3) | | +27 .. -295 | | | sun anticipation is the big lever |
| | h_sun 4 / 12 / 16 (sun 0.02-0.03) | -4.10, -4.79, -2.08 (c .3) | | | | | 8 h best |
| | ki 0.15 (sun 0.035) | -6.85 / -6.20 | -3.88 | -276 | 21.97 | 2.75 | |
| | adaptive curve slope (ks 0.02) | -5.09 / -4.55 | | -161 | | | worse, dropped |
| | forecast-warmth start timing (kt 0.1-0.2) | ±0.1 | | | | | no effect, dropped |
| | kp 0.8 / 2.5 | -5.96 / -6.13 (c .3) | | | | | flat |
| | q_run 4.5 / 5.5 / 6.5 / 7.5 on nominal, partload_lo, legacy_cop, sun ±30, loss_minus20, raw_return (seeds 0-1) | 5.5 is never worst; 6.5-7.5 win nominal but lose partload_lo / legacy_cop | | | | | kept 5.5 (does not lean on the part-load slope) |
| | asymmetric integral (slower wind-down when too warm after a long idle) | up to -7.45 (c .3) | | -388 | **22.07** | | breaks ±0.05 K. Recentring it with a slow aim bias gave the comfort back, so it was dropped as a comfort-for-mean trade |
| | glow correction 0.0008 | -7.37 / -6.70 | -3.78 | -331 | 22.01 | 2.76 | centred the mean air |
| | sun_k 0.045, kp 2.0, c1 0.21, DM 250/120, w_fc 0.7 (each worth 0.1-0.4 %) | -7.80 / -7.49 | -3.62 | -378 | 22.02 | 2.39 | robust check: mean air 22.06 on loss_minus20 and 22.05 on raw_return (I at its -4 K clamp 6.5 % of the time) |
| final | i_lim 6 | -7.35 / -7.01 | -3.68 | -332 | 22.01 | 2.41 | constraint-safe on every variant |
| | ride_gap 30, DM 300/150, min_run 60, sun 0.055, kp 2.5 + ki 0.2 | -6.76 .. -7.07 (c .3) | | | | | plateau; defaults kept |

Ablations of the final controller (season, seeds 0-2, nominal):

| ablation | adj .05 / .3 | energy % | comfort K-h | mean air |
|---|---|---|---|---|
| final | -7.35 / -7.01 | -3.68 | -332 | 22.01 |
| no sun term (sun_k 0) | -2.23 / -1.75 | -2.37 | +4 | 22.03 |
| no sun term, no glow | -2.35 / -1.90 | -2.54 | +9 | 22.00 |
| no glow | -6.87 / -6.56 | -3.68 | -290 | 21.97 |
| ride near the floor (q_run 3.5) | -5.45 / -5.20 | -1.65 | -343 | 22.01 |

So:

- about 2.4 % of energy comes from DM timing plus the 6-kW ride;
- about another 1.3 % of energy and all of the comfort gain come from the forecast-sun term;
- the comfort gain alone is worth about 3.5 % at the ranking's price.

## 5. Results

> Sections 5-7 are the round-1 record. Section 8 has the current numbers (review round 2).

### 5.1 Season, nominal, seeds 0-2 (`--rank -s season --seeds 0-2`)

| | reference_tuned | degree_minutes |
|---|---|---|
| electricity kWh/d (seed 0 / 1 / 2) | 27.06 / 26.19 / 26.07 | 26.11 / 25.16 / 25.17 |
| normalised kWh/d | 26.81 / 25.96 / 25.80 | 25.86 / 24.95 / 24.88 |
| mean air °C | 22.00 / 22.01 / 22.01 | 22.00 / 22.01 / 22.01 |
| mean abs. error K | 0.49 / 0.53 / 0.52 | 0.42 / 0.45 / 0.45 |
| starts/d | 2.1 / 2.0 / 2.0 | 2.4 / 2.4 / 2.4 |
| writes/d | 9.7 / 9.8 / 9.3 | 17.1 / 16.8 / 16.4 |
| mean outlet while running °C | 30.3 / 30.1 / 30.0 | 31.1 / 31.0 / 30.9 |
| median run, min | 288 / 276 / 270 | 245 / 230 / 226 |
| runs < 60 min | 3 / 2 / 1 % | 3 / 7 / 6 % |
| flags | none | none |

**Ranking line:**

| adj % at c = 0.2 | ±90 % | c = 0.05 / 0.3 | break-even start cost | verdict | energy % | comfort K-h | starts/d (base) |
|---|---|---|---|---|---|---|---|
| **-7.15** | 0.66 | -7.35 / -7.01 | 5.6 kWh | **better** | -3.68 | -332 | 2.4 (2.1) |

Mean air 22.01, mean abs. error 0.44 vs 0.51 K.

Seed 0, by daily-mean outdoor temperature (baseline -> degree_minutes):

| outdoor | starts/d | median run, min | output while running, kW | outlet while running, °C | running COP | electricity kWh/d |
|---|---|---|---|---|---|---|
| < -5 °C (45 d) | 1.5 -> 2.0 | 873 -> 488 | 5.95 -> 6.50 | 31.4 -> 31.8 | 2.66 -> 2.74 | 47.8 -> 46.2 |
| -5..0 (26 d) | 2.0 -> 2.5 | 426 -> 326 | 5.30 -> 5.96 | 30.7 -> 31.4 | 3.12 -> 3.18 | 34.9 -> 34.5 |
| 0..+3 (37 d) | 2.3 -> 2.8 | 347 -> 259 | 5.04 -> 6.09 | 29.9 -> 30.7 | 3.50 -> 3.64 | 24.5 -> 23.5 |
| +3..+6 (38 d) | 2.6 -> 2.5 | 243 -> 204 | 4.90 -> 6.33 | 29.3 -> 30.6 | 4.08 -> 4.39 | 15.8 -> 14.7 |
| > +6 (36 d) | 2.4 -> 2.3 | 243 -> 177 | 4.82 -> 6.17 | 28.4 -> 29.9 | 4.72 -> 5.21 | 10.1 -> 9.6 |

- The metered saving is split -74 / -65 / -34 kWh over the < -4 / -4..+4 / > +4 °C buckets, so
  there is no `cold_share` flag.
- Run ends (seed 0, 438 runs):
  - 332 by the DM stop write (median run 253 min);
  - 75 by hot water;
  - 17 at a 120-minute surge;
  - 14 after a defrost.

  The baseline ends 178 of 392 runs at surges.
- Defrosts: 1019 vs 1021.
- Runs under 15 min: 0.2 %.
- Comfort: the mean abs. error falls on 6-hour timescales (0.43 -> 0.36 K for the 6-hour-mean
  error). On days with GHI above 80 W/m² it falls from 0.88 to 0.70 K. The daily-mean error is
  unchanged (0.20 -> 0.21 K).

### 5.2 Robust variants (`--rank -s season --seeds 0-1 --robust`)

**Better on all 20 mandatory variants, with no constraint break.**

| variant | adj % c=0.2 ±90 % | c=0.05 / 0.3 | energy % | comfort K-h | starts/d (base) | mean air | mae (base) | flags |
|---|---|---|---|---|---|---|---|---|
| nominal | -7.23 ± 2.26 | -7.41 / -7.11 | -3.74 | -334 | 2.4 (2.1) | 22.00 | 0.43 (0.51) | |
| partload_lo | -6.27 ± 1.05 | -6.46 / -6.15 | -2.79 | -332 | 2.4 (2.1) | 22.01 | 0.43 (0.51) | |
| partload_hi | -8.61 ± 1.92 | -8.80 / -8.48 | -5.10 | -341 | 2.4 (2.0) | 22.00 | 0.43 (0.51) | |
| legacy_cop | -5.83 ± 0.64 | -6.01 / -5.71 | -2.31 | -333 | 2.4 (2.1) | 22.01 | 0.43 (0.51) | |
| high_start_loss | -6.97 ± 1.96 | -7.15 / -6.85 | -3.52 | -334 | 2.4 (2.1) | 22.00 | 0.43 (0.51) | |
| sluggish | -7.09 ± 1.72 | -7.28 / -6.97 | -3.64 | -331 | 2.4 (2.0) | 22.01 | 0.43 (0.51) | |
| raw_return | -5.69 ± 1.88 | -5.94 / -5.52 | -3.35 | -240 | 2.6 (2.1) | 22.04 | 0.46 (0.51) | |
| minute_only | -6.51 ± 5.98 | -6.67 / -6.40 | -2.93 | -377 | 2.3 (2.0) | 22.00 | 0.43 (0.52) | |
| low_flow | -6.45 ± 2.16 | -6.60 / -6.34 | -3.64 | -284 | 2.5 (2.2) | 22.00 | 0.44 (0.51) | |
| high_flow | -7.32 ± 2.16 | -7.57 / -7.16 | -3.77 | -334 | 2.3 (1.9) | 22.01 | 0.44 (0.52) | |
| loss_minus20 | -7.20 ± 0.58 | -7.43 / -7.04 | -4.45 | -256 | 2.6 (2.2) | 22.03 | 0.47 (0.53) | cold_share |
| steep_outlet | -7.24 ± 1.49 | -7.44 / -7.10 | -3.65 | -344 | 2.4 (2.1) | 22.00 | 0.43 (0.51) | |
| shallow_outlet | -7.50 ± 0.85 | -7.71 / -7.36 | -4.11 | -332 | 2.4 (2.0) | 22.00 | 0.43 (0.51) | |
| frost_melt_lo | -7.23 ± 1.03 | -7.42 / -7.10 | -3.76 | -334 | 2.4 (2.1) | 22.01 | 0.43 (0.51) | |
| frost_melt_hi | -7.44 ± 0.54 | -7.65 / -7.29 | -3.96 | -339 | 2.4 (2.0) | 22.01 | 0.43 (0.51) | |
| light_slab | -6.85 ± 1.48 | -7.07 / -6.70 | -4.28 | -257 | 2.7 (2.3) | 21.99 | 0.43 (0.49) | |
| heavy_slab | -7.61 ± 2.09 | -7.75 / -7.52 | -3.45 | -389 | 2.2 (2.0) | 22.01 | 0.44 (0.53) | |
| sun_plus30 | -7.21 ± 1.37 | -7.34 / -7.12 | -3.10 | -399 | 2.3 (2.0) | 22.02 | 0.44 (0.53) | |
| sun_minus30 | -6.74 ± 2.58 | -6.99 / -6.57 | -4.14 | -252 | 2.5 (2.1) | 22.02 | 0.46 (0.52) | |
| forecast_pessimistic | -6.78 ± 1.46 | -6.96 / -6.66 | -3.56 | -310 | 2.4 (2.1) | 22.00 | 0.44 (0.51) | |

Diagnostics (season, seed 0, normalised kWh/d, baseline -> degree_minutes):

| diagnostic | normalised kWh/d | other |
|---|---|---|
| `flat_load` | 26.01 -> 26.02 | the energy advantage vanishes; mae 0.49 -> 0.42 remains |
| `frost_no_melt` | 26.79 -> 25.68 | |
| `long_outage` (3-day link loss) | 26.82 -> 25.86 | mean air 22.00, min air 20.2 °C |
| `sparse_thermometer` | 26.87 -> 25.91 | |

### 5.3 Weeks (`--rank -s weeks --seeds 0-2`, diagnostic)

| week | adj % c=0.2 ± 90 % | verdict | energy % | comfort K-h | starts/d (base) | mean air | mae (base) | note |
|---|---|---|---|---|---|---|---|---|
| oct_mild | -35.8 ± 8.0 | better | -8.7 | -27 | 1.9 (1.9) | 22.08 | 0.49 (0.66) | comfort dominates in a low-energy week; mean air 22.09 / 22.14 on two seeds |
| nov_mixed | -9.3 ± 6.0 | better | -2.8 | -16 | 3.5 (3.2) | 22.05 | 0.26 (0.36) | 22.08 on one seed |
| dec_damp | -0.8 ± 2.5 | undecided | -2.1 | +2 | 3.5 (2.5) | 22.02 | 0.29 (0.28) | break-even start cost 0.43 kWh; 22.07 on one seed |
| jan_cold | -4.8 ± 2.8 | better | -2.5 | -16 | 1.6 (1.2) | 22.00 | 0.38 (0.48) | cold_share; 21.92 / 22.06 on two seeds |
| feb_sunny_cold | -6.2 ± 5.0 | better | -2.4 | -20 | 1.6 (1.3) | 22.04 | 0.49 (0.60) | |
| mar_shoulder | -11.9 ± 8.2 | better | -5.9 | -8 | 1.7 (1.6) | 22.22 | 0.94 (0.99) | sun-driven: 22.15-22.26 |
| apr_mild_sunny | -13.0 ± 52 | undecided | -2.7 | -14 | 1.0 (1.1) | 22.38 | 0.98 (1.06) | the house overheats with the heating off (22.91 on seed 1; the untuned reference gets 22.86 there) |

The weeks break the ±0.05 K mean-air rule on 6 of 7 weeks for at least one seed:

- The baseline's aim is tuned per scenario and seed by a secant search. This controller is not
  tuned per scenario, and one week is too short for its integral (0.15 K per K-hour) to centre
  the mean.
- In the spring weeks no controller can, because the sun alone holds the room above target.

Over the season, which is the primary ranking, the mean air is 21.99-22.04 on every variant.

## 6. Known weaknesses

- **The energy gain rests on the part-load COP surface.** The controller holds about 6-6.5 kW
  where the baseline drifts to about 5 kW. The flat-output COP diagnostic (`flat_load`, rejected
  by the data) erases the whole energy advantage. `legacy_cop` and `partload_lo` keep -2.3 % and
  -2.8 %.
  - The research's two-hold field test (UNIT_MODEL.md section 7.2) should be done before
    trusting the energy half of the gain.
  - The comfort half (sun anticipation) does not depend on it.
- **Hotter water while running** (+0.7-0.9 K mean outlet) is the opposite of the owner's
  intuition. The model says a moderate output at slightly warmer water beats the floor output.
  This is unverified on the real unit, as is the firmware's frequency law under a riding setpoint.
- **More starts:** 2.4 vs 2.1 a day over the season, and 3.5 vs 2.5 in the damp December week,
  where the result is only undecided. The season's break-even start cost of 5.6 kWh is far above
  any plausible start cost, but the simulator under-predicts starts by 15-18 %.
- **More writes:** 17 a day against the baseline's 9.5, well inside the 48 budget. Ride writes
  are about half of them.
- **The sun term is a fitted gain,** about 4-5x the steady-state solar equivalent.
  - It passed sun ±30 % and pessimistic forecasts.
  - The forecast's GHI error is calibrated in size only, and its sharing between issues is not
    calibrated.
  - The real house's solar response to a strongly sun-anticipating controller is extrapolated
    (SIMULATOR.md section 6.1).
- **The glow correction uses the house model's own thermometer coefficient.** It was fitted on the
  real sensor, but using it here is partly circular. Without it, the gain is -6.56 % instead of
  -7.01 % at c = 0.3, and the mean air is 21.97.
- **Intra-day disturbances are not addressed.** The daily-mean error is unchanged. The slab's
  lag leaves the 0.2 K daily-mean wander to the integral.
- **The weekly mean air is not centred** (section 5.3). An owner would see a few warm weeks in
  spring. Nothing in the controller cools the house.
- **Untested on the real firmware:**
  - the start-kick estimate (inlet - 0.7 K);
  - the 24-25 °C park and 22-24 °C stop writes;
  - whether a 1 K ride write during a run moves the frequency as the dead-band model says.

  The start kick has a +1 K retry. The parked setpoint keeps a firmware backstop.

## 7. Review fixes (round 1)

An adversarial review (seeds 3-4) raised two major and six minor issues. Every result below was
re-run on seeds 0-2 (nominal and weeks) and 0-1 (`--robust`) only. Results are in
`.local/lab-results/controllers/degree_minutes/fix*/`.

| id | issue | verdict | fix |
|---|---|---|---|
| R1 (major) | raw_return mean air 22.06 on seeds 3-4 | real | cause found, fixed by R4 |
| R2 (major) | energy gain is the part-load COP surface; the rest is the sun term | real (reporting) | reported as two parts below |
| R3 | stop write clamped to 25 °C cannot stop a cool run; the run is re-adopted as a phantom start | real | stop writes down to 22 °C; `stopping` state |
| R4 | the park does not prevent firmware self-starts | real, smaller than counted | idle guard |
| R5 | weekly mean air not centred | real, disclosed | unchanged |
| R6 | setpoint pegged at 38-39 °C for about 100 h in deep cold | real | DM lift of the ride capped at 3 K |
| R7 | docstring/defrost, 6-h stale room, heating-off fight | real | docs fixed, 90 min, owner off respected |
| R8 | firmware behaviours are model inferences | agreed | field test listed in section 6 |

**R1 and R4.** The reviewer counted 108 of 440 heat starts as firmware self-starts. Most of these
(about 75 of 112 on seed 0 with the old code) are the heat run resuming after a defrost: the one
idle minute between defrost and heat looks like a start. The rest (37 on seed 0) are real: the
loop cools under a fixed park until setpoint - t_ctrl reaches 4 K, typically park 26 °C with
t_ctrl 22 °C in mild weather. The controller adopts each one as a run for at least 40 min. Under
`raw_return` the unit sees about 1.4 K colder water in mild weather, so these unrequested starts
come more often. This was the source of the warm bias: mean air 22.04 on seeds 0-1 with the old
code. The guard keeps the idle setpoint under the restart threshold whenever DM does not ask for
heat. Real self-starts fall from 37 to 6 per season on seed 0. The 6 left happen while DM already
asks for heat but min_off has not elapsed. raw_return mean air is now 21.99 on seeds 0-2.

A 25 °C floor for the guard (staying inside the recorded range) only partly works: it cannot hold
off a start once t_ctrl < 21 °C, which is the mild-weather case. That floor scores -6.70 % instead
of -7.34 % and drops the `setpoint_range` flag. I chose 24 °C. The same rules apply there, and
the flag is disclosed.

**R3.** The stop write may now go down to 22 °C (the register allows 20). The controller stays in
`stopping` until compressor_on is false, and steps 1 K lower every 3 min if the stop did not take.
Failed stop writes per season (seed 0) went from 72 to 0. No phantom starts or re-adopted runs are
left.

**R6.** In continuous mode the ride setpoint was T_c - 0.3 - DM/120. DM down to -1200 added up to
10 K. The lift is now capped at +3 K. Heat-run minutes at setpoint >= 38 °C on seed 0 went from
6739 to 172. jan_cold is still better (-4.57 %).

**R7.**
- (a) Defrost: DM keeps integrating on purpose, and the docstring now says so.
- (b) The stale-room limit is 90 min instead of 6 h.
- (c) The controller switches heating on only if it is off at hand-over. Once it has seen heating
  on, a later off is respected (no writes at all).
- (d) A missing room is still biased warm. That is a fail-safe, not a ranking case.

**R2: what the score is made of** (seeds 0-2, c = 0.2):

- Energy: -3.71 %. Under `flat_load` it is +0.02 % (seeds 0-2; the reviewer: +0.33 % on seeds 3-4).
  This part is the moderate ~6 kW output on the part-load COP surface, not cooler water or fewer
  cycles. The running outlet is still about 1 K hotter than the baseline, and starts are
  2.4 vs 2.1/d. It needs the two-hold field test before it is claimed as an efficiency gain.
- Comfort: -343 K·h, about 3.6 % of the score. It comes mostly from the forecast-sun term: the
  reviewer found sun_k = 0 gives -2.0 %, and no forecast -1.1 %.

### 7.1 Results after the fixes

Season, nominal, seeds 0-2: **-7.34 % +-0.70** at c = 0.2 (-7.50 % at 0.05, -7.23 % at 0.3),
better.
- Normalised energy -3.71 %, metered -3.80 %, comfort -343 K·h.
- mae 0.43 vs 0.51 K; mean air 21.98-21.99.
- Starts 2.4 vs 2.1/d (break-even 6.9 kWh/start); writes 16.0-16.4/d.
- Mean outlet 31.0-31.2 vs 30.0-30.3 °C.
- Flag: `setpoint_range`.

Robust, seeds 0-1: 19 of 20 better, 1 undecided (`minute_only`), 0 worse, no constraint break.
- Range: -5.85 % (`legacy_cop`) to -8.74 % (`partload_hi`). `raw_return` is -7.08 % at mean air
  21.99.
- Mean air is 21.96-22.00 on every variant.
- `minute_only` is -6.64 % +-6.79. Both seeds are clearly better: normalised -0.86 kWh/d on each,
  and comfort -201 and -305 K·h. The interval at n = 2 is t(0.95, 1) = 6.31 times the seed
  spread, which here is a comfort difference. On seeds 0-2 `minute_only` is -6.80 % +-1.87,
  better. The old code passed it at -6.51 % +-5.98 by the same margin of luck.

Diagnostics, seeds 0-2, all better:
- `flat_load` -3.75 % (energy +0.02 %, comfort only);
- `long_outage` -7.01 %, `frost_no_melt` -7.57 %, `sparse_thermometer` -7.60 %;
- `sparse_thermometer+raw_return` -7.27 % at mean air 21.99 (was 22.05 on seeds 3-4).

Weeks, seeds 0-2, adjusted at c = 0.2:
- Better in 5 weeks: oct_mild -42.5 %, nov_mixed -8.8 %, jan_cold -4.6 %, feb_sunny_cold -7.3 %,
  mar_shoulder -19.7 % (was -11.9 %).
- Undecided in 2: dec_damp -0.6 % +-5.0 (3.4 vs 2.5 starts/d; one seed breaks mae 0.33 and mean
  air 22.11) and apr_mild_sunny (mean air up to 22.58, was 22.91).
- The weekly mean-air rule still breaks on some seed in most weeks (R5, unchanged).

## 8. Review fixes (round 2)

A second adversarial review (seeds 3-4) raised four major and four minor issues. Everything
below was re-tuned and re-run on seeds 0-2 (nominal, weeks, stress wrappers) and 0-1
(`--robust`) only. Results are in `.local/lab-results/controllers/degree_minutes/fix6/`.

| id | issue | verdict | fix |
|---|---|---|---|
| R1 (major) | claimed numbers stale; shipped file flagged `setpoint_range` (24 °C park, 22 °C stop) | real | park and stop floors 25 °C; every number below refreshed from the shipped file |
| R2 (major) | energy gain is the part-load COP surface and the inferred capacity loop | real (claim) | claim restated as conditional, below; no code change |
| R3 (major) | no forecast: comfort gain gone, mean air 21.93 (breaks ±0.05) | real | stale-forecast reuse, PV-based glow correction, 1.5x integral; centring fixed, comfort gain still needs a forecast |
| R4 (major) | more starts and hotter water than the baseline | real | DM thresholds re-tuned to 225/200: starts 2.2 vs 2.1/d (was 2.4); hotter water unchanged, stated |
| R5 | weekly mean air not centred; jan_cold seed-sensitive | real, disclosed | none |
| R6 | mean air biased cool, 21.96 on light_slab | partly | with the fixes nominal is 21.98-22.00, light_slab 21.97; no extra bias term (it would be fitted to the thermometer model) |
| R7 | None sensors would raise; integral winds during outages; kick can climb | real | None/NaN unit values treated as an outage; integral frozen after 120 min of outage; at most two +1 K kick retries |
| R8 | start burst identical in the simulator | agreed | simulator limitation, reported |

**R1.** The 24 °C guard park and the 22 °C stop floor are gone; every write is inside 25-39 °C.
The price on seeds 0-2 is about 0.65 points (-7.23 % -> -6.56 % at c = 0.3 with the old DM
thresholds): with a 25 °C floor the guard cannot hold off a firmware self-start once the idle
control sensor drops under 21 °C (mild weather, long off-time); the controller adopts those runs.
A 25 °C stop write cannot stop a run whose control sensor is under 27 °C; after 30 min in
`stopping` such a run is handed back to the ride (DM then stops it once the water is warm enough).

**R2. What the energy part is.** Energy -3.43 % (nominal, seeds 0-2). Under `flat_load` the
energy difference is about zero (round-1 measurement +0.02 %, reviewer +0.12 %), and under
`legacy_cop` it is -2.07 %, `partload_lo` -2.73 %. So the energy gain is the model's statement
that a 6-6.5 kW ride is more efficient than the baseline's ~5 kW, through the fitted part-load COP
surface and the inferred dead-band capacity loop. It is **not** a demonstrated better use of the
heat pump. It is a hypothesis for the two-hold field test (about 5 and about 6.5 kW holds on
comparable days). The comfort part (-294 K·h, about 3.2 points) is the firmer one, but it needs a
forecast (R3).

**R3. Forecast missing.** Three changes:
- The last forecast is cached; when the current one is empty, its hours still ahead of now are
  used. A forecast that only arrives every 12 h costs almost nothing: -6.33 % vs -6.62 % at
  c = 0.3 (seeds 0-2).
- With no usable forecast hour, the thermometer glow correction takes irradiance from PV
  (8.9 kW per kW/m² in SIMULATOR.md, i.e. 112 W/m² per kW, refined online). This is what fixes
  the centring: the old fallback had no glow correction, so it centred a reading that is warm in
  sun.
- The room integral runs 1.5x faster without a forecast (3x over-shot warm: 22.05).

A PV-persistence sun term (current irradiance as the next hours' mean) was tried and lost
(+0.7 % to +1.6 % worse), so there is no sun anticipation without a forecast.

| wrapper (season, seeds 0-2) | adj c=0.05 / 0.3 | energy | comfort K·h | mean air | mae (base) |
|---|---|---|---|---|---|
| no forecast, PV present | -0.63 / -0.42 % | -2.21 % | +137 | 22.01 (22.005-22.025) | 0.545 (0.513) |
| no forecast, no PV | -0.45 / -0.29 % | -2.25 % | +158 | 21.97 (21.953-21.979) | 0.549 (0.513) |
| forecast only every 12 h | -6.43 / -6.33 % | -3.32 % | -279 | 21.99 | 0.450 (0.513) |
| no room all season | -0.51 / -0.44 % | -3.13 % | +229 | 22.32 (fails warm) | 0.566 (0.513) |

Without a forecast the controller is about even with the baseline (no longer better) and the
mean-air constraint holds. The whole comfort advantage is the forecast-sun term.

**R4. Cycling and water temperature.** The DM thresholds were the cheapest lever. Season, seeds
0-2, nominal, at c = 0.05 / 0.3 and starts/d (baseline 2.06):

| dm_start / dm_stop | adj % | starts/d | mean outlet running |
|---|---|---|---|
| 250 / 120 (round 1) | -6.80 / -6.48 | 2.40 | 30.98 |
| 250 / 200 | -6.54 / -6.49 | 2.11 | 31.02 |
| **225 / 200 (chosen)** | **-6.71 / -6.62** | **2.16** | **30.96** |
| 200 / 200 | -6.89 / -6.74 | 2.21 | 30.91 |
| 225 / 225 | -6.41 / -6.38 | 2.09 | 30.96 |
| 250 / 250 | -6.03 / -6.06 | 2.03 | 31.05 |
| 350 / 200 | -5.74 / -5.80 | 2.00 | 31.19 |
| q_run 4.5 (250 / 120) | -6.07 / -5.89 | 2.25 | 30.71 |

Starts are now 2.2 vs 2.1/d over the season (+5 %, was +17 %). dec_damp is still 3.0 vs 2.5/d.
The running water stays about 0.8 K hotter than the baseline (31.0 vs 30.1 °C mean outlet). Lowering
the ride output cools it and cuts energy gain in the model. **So the controller trades the owner's
"cooler water" goal for model-predicted part-load COP**, and that trade is exactly what the field
test must confirm or reject. If the field test shows the flat_load picture, q_run 4.0-4.5 is the
setting that meets the owner's goals at the same comfort.

**R7.** `step()` checks outdoor, outlet, inlet, setpoint and restart_delta for None/NaN and treats
a bad value as a link outage (no writes, DM and states frozen). The room integral keeps running
from the thermometer for the first 120 min of an outage (short drops; freezing it at once cost
0.2 points) and then freezes. The start kick now retries +1 K at most twice, then gives up and
parks.

### 8.1 Results after round 2 (shipped file)

Season, nominal, seeds 0-2 (`--rank`): **-6.66 % ±0.70** at c = 0.2 (-6.71 % at 0.05, -6.62 % at
0.3), **better, no flags**. Break-even 17 kWh/start.
- Normalised energy -3.43 %, metered -3.46 %, comfort -294 K·h; mae 0.45 vs 0.51 K.
- Mean air 21.98 / 21.99 / 22.00.
- Starts 2.2 / 2.1 / 2.2 vs 2.1 / 2.0 / 2.0 per day; median run 276 / 259 / 254 vs 288 / 276 / 270 min.
- Writes 15.2-15.8/d (baseline 9.3-9.8). Max setpoint 38-39 °C.
- Mean outlet running 31.1 / 30.9 / 30.8 vs 30.3 / 30.1 / 30.0 °C. COP 3.00-3.02 vs 2.89-2.91.

Robust, seeds 0-1: **20 of 20 better, 0 undecided, 0 worse**, no constraint break, no
`setpoint_range` flag (loss_minus20 carries `cold_share`).
- Range at c = 0.2: -5.15 % (`raw_return`) and -5.19 % (`legacy_cop`) to -8.00 % (`partload_hi`).
  `minute_only` -6.63 % ±6.14 is better this time but is still the widest interval.
- Mean air 21.97 (`light_slab`) to 22.03 (`raw_return`).

Weeks, seeds 0-2, at c = 0.2:
- Better in 5: oct_mild -36.2 %, nov_mixed -10.1 %, jan_cold -5.0 % (cold_share), feb_sunny_cold
  -6.5 %, mar_shoulder -11.3 %.
- Undecided in 2: dec_damp -0.9 % ±3.9 (3.0 vs 2.5 starts/d) and apr_mild_sunny (±59 %).
- The weekly mean-air rule breaks on some seed in 6 of 7 weeks, as before (R5). jan_cold was
  undecided on the reviewer's seeds 3-4.
- oct_mild seed 1 carries `runs_lt_15min`: 1 of its 16 heat runs (6.25 %) lasted 2 min, because
  a hot-water cycle took the compressor right after the heat start kick (DHW priority). A mild
  week has so few runs that one such run passes the 5 % flag share. The season has no such flag.

### 8.2 Weaknesses after round 2

- The energy half (-3.4 %) rests on the part-load COP surface and the inferred capacity loop;
  flat_load removes it. Two-hold field test needed before claiming it.
- The comfort half (-294 K·h) rests on the forecast-sun term (sun_k fitted against the house
  model's solar apertures); without a forecast the controller is only even with the baseline.
- Running water about 0.8 K hotter than the baseline, against the owner's intuition.
- Starts +5 % on the season, +20 % in dec_damp; writes about 15.5/d vs 9.5.
- The 25 °C floor lets the firmware self-start in mild weather when the idle loop drops under
  about 21.7 °C; those runs are adopted, not prevented.
- A missing room thermometer fails warm (mean air 22.3).
