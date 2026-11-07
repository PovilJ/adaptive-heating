# hybrid: the mechanisms that proved themselves, and nothing else

`lab/controllers/hybrid.py` (stdlib only, uses only the `Observation`, about 250 lines of logic
plus a self-check). It was built after a head-to-head run of every lab controller and a set of
ablations, to answer two questions: which mechanisms actually produce the gains in this lab, and
how few moving parts are needed to keep them. All numbers are from the lab simulator, tuned on
season seeds 0-2 only; robustness on seeds 0-1. Seeds 5-9 were never run. Results live in
`.local/lab-results/controllers/hybrid/`.

## 1. Summary

| | hybrid (season, seeds 0-2, paired against `reference_tuned`) |
|---|---|
| Adjusted energy | **-10.51 % ± 1.22** at c = 0.2 kWh/start (-10.51 at 0.05, -10.52 at 0.3), `better` |
| Energy alone | -5.29 % normalised, -5.29 % metered; COP 3.06-3.09 against 2.89-2.91 |
| Comfort | -464 K-h of \|air - target\|; mean \|error\| 0.41 against 0.51 K; mean air 22.00 on every seed |
| Starts | 2.0 a day (baseline 2.0); median run 300 min (baseline 278); 6 % of runs under 60 min |
| Writes | 18.4-18.9 a day, at most 37 in any day (baseline 9.6) |
| Water | mean outlet while running 30.8 °C (baseline 30.1); highest setpoint 35 °C (baseline 39) |
| Robust (20 variants, seeds 0-1) | **20 of 20 `better`**, -8.19 % (`legacy_cop`) to -12.05 % (`partload_hi`), no constraint broken (mean air 21.98-22.02) |
| Weeks (seeds 0-2, diagnostic) | `better` in all 7 weeks; mean air misses ±0.05 K in 13 of 21 week-seeds (warm in mild weeks from a fresh start) |
| Flags | `min_off` (a kick inside the ASSUMED 3-min minimum off); `setpoint_range` on 2 of 3 seeds at 0.00 % of the time (stop writes held a few minutes) |

The same-seed field (section 2) puts the previous best, `pmin_duty`, at -10.19 % and `econ_mpc` at
-9.35 %. The hybrid is a slightly simpler `pmin_duty`-style slab thermostat. The difference is
within the interval, so read it as "keeps the best result with fewer parts", not as a new
maximum. **About half the gain is energy that rests on the fitted part-load COP map, and half is
comfort timing (forecast sun + a learned daily pattern).** Running cooler water costs energy in
this lab (section 3).

## 2. The field (season, seeds 0-2, one run of all controllers)

`run.py --rank -c reference_tuned,current_port,wc_low,degree_minutes,block_scheduler,setpoint_rider,room_contact,econ_mpc,self_learning_curve,pmin_duty -s season --seeds 0-2`
(`cmp_season.txt`), plus the hybrid's final run (`abl_final.txt`, same seeds and baseline).

| controller | how it decides when / how hard | adj % c=0.2 | energy % | comfort K-h | starts/d | outlet °C | writes/d |
|---|---|---|---|---|---|---|---|
| reference_tuned | curve + room PI, firmware cycles | 0 | 0 | 0 | 2.0 | 30.1 | 9.6 |
| current_port | 36-h plan, hot pulses, firm floor | -0.43 (undecided, mean air 22.30 breaks) | -0.49 | -30 | 2.6 | 32.3 | 15.5 |
| self_learning_curve | learned curve + sun, firmware cycles | -4.98 | -1.53 | -289 | 1.8 | 30.5 | 8.5 |
| wc_low | curve + sun + PI, firmware cycles | -6.37 | -1.94 | -378 | 1.8 | 30.8 | 10.3 |
| block_scheduler | Kalman + block plan, ride ~5 kW | -6.57 | -4.25 | -184 | 1.7 | 30.8 | 14.0 |
| degree_minutes | degree-minute start/stop, ride ~6 kW, sun | -6.66 | -3.43 | -294 | 2.2 | 30.9 | 15.5 |
| room_contact | room thermostat + curve (5-6 kW), sun | -7.41 | -3.11 | -404 | 2.4 | 31.1 | 9.9 |
| setpoint_rider | heat balance, ride 5 kW, sun, daily profile | -7.51 | -4.00 | -316 | 2.1 | 30.7 | 10.1 |
| econ_mpc | MPC on a learned model, levels 5-8.5 kW | -9.35 | -3.57 | -511 | 2.0 | 31.1 | 21.5 |
| pmin_duty | slab thermostat, ride 6.5 kW, sun, daily pattern | -10.19 | -5.18 | -448 | 2.1 | 30.8 | 18.9 |
| **hybrid** | slab thermostat, ride 6.5 kW, sun, daily pattern | **-10.51** | **-5.29** | **-464** | 2.0 | 30.8 | 18.7 |

Weeks, seeds 0-2, adjusted % at c = 0.2 (`(u)` = undecided; `cmp_weeks.txt`, `weeks_final.txt`):

| controller | oct | nov | dec | jan | feb | mar | apr |
|---|---|---|---|---|---|---|---|
| wc_low | -41.4 | -9.0 | -0.4(u) | -2.7 | -7.4 | -19.3 | -28.4 |
| self_learning_curve | -24.1(u) | -3.9(u) | -1.5(u) | +0.5(u) | +1.0(u) | +0.8(u) | -15.3(u) |
| block_scheduler | -28.6 | -7.6 | -0.8(u) | -4.4(u) | -7.5 | -12.4 | -6.1(u) |
| degree_minutes | -36.2 | -10.1 | -0.9(u) | -5.0 | -6.5 | -11.3 | -5.3(u) |
| room_contact | -40.7 | -7.3 | -3.2 | -3.9 | -6.2 | -21.5 | -27.7(u) |
| setpoint_rider | -32.0 | -6.3 | -0.9(u) | -2.3 | -5.9 | -14.0 | -21.5(u) |
| econ_mpc | -41.0 | -10.7 | -2.6 | -4.7 | -8.2 | -37.2 | -35.0 |
| pmin_duty | -42.3 | -10.7 | -4.6 | -5.0 | -8.1 | -28.8 | -36.0 |
| **hybrid** | -46.4 | -11.7 | -5.0 | -5.7 | -10.4 | -30.6 | -45.1 |

What the field already says, before any ablation:

- **Every controller that beats the baseline on energy by more than 2 % runs the compressor at
  mid output (5-6.5 kW) and decides the stop itself.** The firmware-cycled curves (`wc_low`,
  `self_learning_curve`) save 1.5-2 % of energy; the riders save 3-5 %.
- **Every controller with a large comfort gain uses forecast sun**, and the three biggest add a
  learned daily pattern (`pmin_duty`, `setpoint_rider`) or a learned disturbance profile
  (`econ_mpc`).
- **Nobody runs cooler water than the baseline and wins.** Every better controller has a mean
  outlet 0.4-1.0 K above the baseline. The owner's "too hot" intuition does not survive this
  lab's COP map (section 3.1).
- **Starts are not where the money is.** The winners have the baseline's 2.0-2.1 starts a day;
  fewer starts (`block_scheduler` 1.7, `wc_low` 1.8) did not buy a better score.
- **The production port loses** because of an asymmetric comfort cost (a firm floor with cheap
  overshoot): mean air +0.3 K, hot night catch-up pulses, +25 % starts.

## 3. Ablations (hybrid, season, seeds 0-2, each row one change from the final file)

`abl_final.txt`; the per-run columns are seed means.

| row | change | adj % c=0.2 | energy % | comfort K-h | COP | outlet °C | starts/d | run p50 min | writes/d | mean air |
|---|---|---|---|---|---|---|---|---|---|---|
| final | - | **-10.51** | -5.29 | -464 | 3.08 | 30.83 | 2.0 | 300 | 18.7 | 22.00 |
| **output level** | `q_run=0` (the unit's floor, "low and slow") | -6.69 | -2.50 | -410 | 2.98 | 30.20 | 2.6 | 205 | 17.2 | 21.99 |
| | `q_run=5` | -8.67 | -3.66 | -438 | 3.02 | 30.43 | 2.0 | 337 | 17.6 | 22.00 |
| | `q_run=7.5` | -10.74 | -5.63 | -459 | 3.09 | 31.33 | 2.1 | 269 | 19.9 | 22.00 |
| **who runs the cycle** | `mode=fw`: same slab target, the firmware cycles a setpoint (no kick, ride or stop writes) | -8.12 | -2.67 | -466 | 2.99 | 30.83 | 1.8 | 323 | 10.4 | 22.02 |
| **sun** | `s=0` (no forecast sun) | -8.52 | -4.50 | -366 | 3.05 | 30.73 | 2.2 | 271 | 19.3 | 22.01 |
| **daily pattern** | `d_g=0` | -9.14 | -5.18 | -363 | 3.08 | 30.63 | 2.2 | 273 | 17.0 | 21.99 |
| | `s=0, d_g=0` (both) | -4.85 | -3.56 | -122 | 3.02 | 30.53 | 2.1 | 271 | 16.7 | 22.01 |
| **forecast** | `use_fc=0` (no forecast at all; sensor 24 h mean) | -7.32 | -3.76 | -320 | 3.02 | 30.70 | 2.1 | 280 | 18.7 | 21.97 |
| **room P** | `kp=0` (integral only) | -7.97 | -5.82 | -180 | 3.09 | 30.80 | 1.9 | 323 | 16.6 | 21.99 |
| **warm hours** | `kw=0` | -10.21 | -4.77 | -484 | 3.06 | 30.87 | 2.1 | 296 | 18.9 | 22.01 |
| **glow** | `glow=0` (no sun correction of the thermometer) | -10.15 | -5.37 | -422 | 3.08 | 30.83 | 2.0 | 304 | 18.7 | **21.96 (breaks)** |
| **band** | `band=0.8` | -10.35 | -5.47 | -471 | 3.08 | 30.97 | 2.6 | 221 | 22.4 | 22.00 |
| | `band=2.0` | -9.83 | -4.95 | -414 | 3.07 | 30.83 | 1.8 | 360 | 16.5 | 22.00 |
| **write economy** | `ride_hyst=0.8` | -10.84 | -5.47 | -476 | 3.08 | 31.20 | 2.0 | 281 | 28.0 | 22.00 |
| fallback curve | `tau_fb=0` (no room-lost fallback) | -10.58 | -5.32 | -469 | 3.08 | 30.83 | 2.1 | 294 | 18.8 | 22.00 |
| reference | `pmin_duty` | -10.19 | -5.18 | -448 | 3.07 | 30.83 | 2.1 | 291 | 18.9 | 22.00 |

Earlier sweeps (same seeds, on the version before ts0 and the fallback curve were settled, so
read only the differences): `kp` 2 / 4.5: -9.70 / -10.00 vs -9.97; `ki` 0.08 / 0.3: -9.94 /
-9.73; `d_lead` 4 / 7 h: -9.81 / -9.78; `d_g` 0.5 / 2: -9.98 / -9.87; `s` 0.015 / 0.03 / 0.04:
-9.67 / -10.25 / -10.32; forecast window 1-6 / 1-12 h: -9.08 / -9.84; `kw` 0.6: -9.56; a room
derivative term (kd 1-4 K per K/h): -10.01..-10.16 (+0.2, dropped); a 24-h sun term (s24):
no gain (dropped); aiming 0.02-0.04 K warm: no gain (dropped). The optimum is flat everywhere
except output level, sun and the daily pattern.

### 3.1 What produces the gain

| mechanism | worth (adj points) | of which energy | real and robust? |
|---|---|---|---|
| **Mid-output riding** (6.5 kW vs the floor) | **3.8** | 2.8 | It holds on every mandatory variant: energy -4.2 % on `partload_lo`, -3.2 % on `legacy_cop`. But it is a bet on the fitted part-load COP map: under the `flat_load` diagnostic the hybrid's energy is only -1.4 %. 6.5 kW was kept rather than 7.5 kW (+0.2 points) because every kW above 6-7 rests more on the map and runs hotter water |
| **Controller decides start/stop** (vs the firmware cycling the same target) | **2.4** | 2.6 | Same comfort, more energy. The firmware's start error makes it start at 7.3 kW and ramp down slowly, and it ends runs only at surges; the rider holds the chosen output and ends the run on time |
| **Forecast sun** (slab target lowered by 0.03 K per W/m² of forecast GHI, hours 1-9) | **2.0** (5.7 together with the daily pattern) | 0.8 | Yes. Holds on `sun_plus30` / `sun_minus30` and `forecast_pessimistic`. Climatology does part of it (the daily pattern) |
| **Learned daily pattern** (24 bins, lead 5 h, zero mean) | **1.4** (5.7 together with sun) | 0.1 | Yes, and also under `synthetic_dist` (-9.93 %), so it is not an artefact of the recorded-day bootstrap. It learns the house's regular cycle (internal-gain profile, morning disturbance dip, typical sun) |
| **Room proportional term** | **2.5** | -0.5 | Yes: without it the integral alone tracks too loosely (comfort +284 K-h) |
| **Glow correction** | 0.4 | 0 | Needed for the mean-air constraint (21.96 without it). It is the public HOUSE_MODEL thermometer term, which needs checking on the real sensor |
| **Warm-hour preference** | 0.3 | 0.5 | Small: a trade of comfort for energy (COP and frost in warmer hours) |
| **Duty band 1.4 K** | 0.2-0.7 | | Flat: 0.8 K gives 2.6 starts/day for the same score, 2.0 K gives 1.8 starts/day for -0.7 points |
| **Fewer starts** | ~0 | | Not a lever: start energy is 0.02-0.06 kWh; the verdict is the same at 0.05 and 0.3 kWh/start (break-even far outside the band) |
| **Low water temperature** | **negative** | | Running at the floor gives the baseline's water (30.2 vs 30.1 °C) and a 3-point loss. In this lab's COP map the floor output is 20-30 % less efficient than 6 kW at the slab's supply, more than the 3.3 %/K supply penalty of the extra ~1.5 K |
| **Soft start** | cannot be shown | | The unit model starts every run at 3.6 K of delta-T (7.3 kW) for 10 min, whatever the setpoint gap (UNIT_MODEL 4), so no controller can change the start burst in this lab |

So the **season result is roughly 45 % energy from the output level and the controller-owned
stop, 45 % comfort from anticipation (sun + daily pattern + P on the room), 10 % small terms.**
The energy part should be quoted as "1.4-5.3 % depending on the real part-load curve" until the
UNIT_MODEL 7.2 two-hold field test is done.

### 3.2 What was left out, and why

- **Model-based planning** (`econ_mpc`, `block_scheduler`, `current_port`): the best of them
  (-9.35 %, best comfort -511 K-h) does not beat a thermostat on the slab with the same
  anticipation terms; it costs a Kalman filter, a planner and 21 writes a day.
- **A learned weather curve during normal operation** (`pmin_duty`'s trim-to-curve transfer):
  -10.59 vs -10.51 without it. The hybrid keeps a curve only as the *fallback* when the room
  thermometer is lost (section 5.4), where it is needed.
- **Takeover boost, rollback of frozen-sensor learning, a 24-h sun term, a room derivative,
  aim offsets**: no measurable gain.
- **Quiet mode, restart hysteresis above 5 K, heating-off as a park**: ASSUMED firmware
  behaviour; not used.

## 4. The controller

Each minute, from the `Observation` only:

1. **Slab estimate** from the water side (the circulation pump never stops). Idle (15 min after
   a stop): slab = inlet. Running (8 min after a start): slab = (inlet - 0.29 x supply) / 0.71,
   supply = outlet + 0.3 K. Frozen during and 20 min after hot water and 10 min after a defrost,
   smoothed 0.2 per minute. It only needs to be a consistent index (return anchoring makes it
   differ from the model slab by up to ±1.7 K); the integral absorbs the offset.
2. **Slab target**
   `Ts* = target + 0.2 (target - T_fc) + ts0 - s GHI_fc + kp e + I + daily(hour) + kw warm`
   - `T_fc`, `GHI_fc`: forecast means over hours 1-9 ahead (the slab-to-room lag). Missing
     forecast: the hours of the last forecast still ahead, else the 24-h mean of the unit's
     sensor and no sun;
   - `e` = target - (room - 0.0008 x GHI_now), the thermometer corrected for its sun glow;
   - `I`: integral of e, 0.15 K per K-h, ±6 K;
   - `daily(hour)`: the room error at hour h moves bin h - 5 h (1 K per K-h per day), zero mean,
     ±2 K, 30-day leak;
   - `warm`: how much warmer the next 3 h are than the next 24 h (0.3 K per K).
3. **Duty cycle**: start when slab < Ts* - 1.4 K (at least 45 min off), stop when
   slab > Ts* + 1.4 K (at least 60 min on). A start the unit makes by itself while heat is due
   is adopted as a run.
4. **Execution** (S6 riding):
   - kick with ceil(inlet - 0.8 + restart_delta + 0.15), +1 K after 6 idle minutes (twice at
     most);
   - from minute 2, ride at inlet + Q/2.02 - 0.8 - 0.025 (Q - 5) + 0.55 inside the firmware's
     dead band, Q = max(6.5 kW, floor) + 2 kW per K of slab deficit beyond the band (30-min
     smoothing, at most 9 kW); rewrite only when the ideal setpoint moved 1.3 K and 8 min have
     passed; never closer than 1.5 K to the stop threshold; 25-39 °C;
   - stop with one write to 25 °C or t_ctrl - 2.1 K, whichever is lower (the firmware stops at
     once); stops wait out a defrost.
5. **Park** (outage fail-safe): while idle the setpoint is
   floor(Ts* - 1.4 - 0.3 + restart_delta - 0.8), never below 25 °C and never high enough to
   start the unit now. If the link fails, the firmware's own restart point sits just below the
   controller's start threshold, so the unit still restarts when the slab runs low.
6. **Registers**: restart_delta written to 5 K (a recorded value) at most 3 times per 24 h;
   writes budgeted at 40 (trims) and capped at 46 (everything) per rolling 24 h; the same value
   is not rewritten within 5 min.

## 5. Parameters (final defaults)

| name | value | meaning |
|---|---|---|
| `b`, `ts0` | 0.20 K/K, +1.0 K | prior slab need (the integral learns the level; ts0 set so the integral sits near 0 over the season) |
| `s`, `lead0`, `lead1` | 0.030 K per W/m², 1, 9 h | forecast sun and window |
| `kp`, `ki`, `i_lim` | 3 K/K, 0.15 K/(K h), 6 K | room feedback |
| `glow` | 0.0008 K per W/m² | thermometer sun correction (HOUSE_MODEL) |
| `d_g`, `d_lead`, `d_lim`, `d_leak` | 1 K/(K h day), 5 h, 2 K, 30 d | daily pattern |
| `kw` | 0.3 K/K | warm-hour preference |
| `band`, `min_run`, `min_off` | 1.4 K, 60, 45 min | duty cycle |
| `q_run`, `kq`, `q_hi` | 6.5 kW, 2 kW/K, 9 kW | run output (`q_run=0`: the unit's floor) |
| `ride_every`, `ride_hyst`, `budget` | 8 min, 1.3 K, 40 / 24 h | write economy (hard cap 46) |
| `delta` | 5 K | restart hysteresis |
| `stale_min`, `frozen_h`, `tau_fb` | 240 min, 12 h, 72 h | room-lost handling and fallback curve (knots -15, -5, +5, +15 °C) |

## 6. Results

### 6.1 Season, nominal, seeds 0-2

| seed | controller | kWh/d | norm/d | COP | starts/d | run p50 | outlet | air | mae | writes/d |
|---|---|---|---|---|---|---|---|---|---|---|
| 0-2 mean | reference_tuned | 26.44 | 26.19 | 2.90 | 2.0 | 278 | 30.13 | 22.01 | 0.51 | 9.6 |
| 0-2 mean | hybrid | 25.04 | 24.81 | 3.08 | 2.0 | 300 | 30.83 | 22.00 | 0.41 | 18.7 |

Paired: **-10.51 % ± 1.22** (c = 0.05 / 0.3: -10.51 / -10.52), `better`; energy -5.29 %, metered
-5.29 %; comfort -464 K-h. Starts per day by daily-mean outdoor (seed 0): below -10 °C 1.68,
-10..-5 1.95, -5..0 2.14, 0..+5 2.00, +5..+10 2.13. Highest setpoint 35 °C. Setpoint outside
25-39 °C 0.00 % of the time. Step time 5 µs mean, 0.9 ms worst.

### 6.2 Robust variants, seeds 0-1 (`robust_final.txt`)

| variant | adj % c=0.2 | ± | energy % | comfort K-h | starts/d (base) | air | mae (base) |
|---|---|---|---|---|---|---|---|
| nominal | -10.34 | 4.15 | -5.35 | -443 | 2.0 (2.1) | 22.00 | 0.41 (0.51) |
| partload_lo | -9.12 | 4.33 | -4.18 | -438 | 2.0 (2.1) | 22.00 | 0.41 (0.51) |
| partload_hi | -12.05 | 4.10 | -7.12 | -452 | 2.1 (2.0) | 22.00 | 0.41 (0.51) |
| legacy_cop | -8.19 | 2.96 | -3.20 | -442 | 2.1 (2.1) | 22.00 | 0.41 (0.51) |
| high_start_loss | -10.26 | 3.80 | -5.33 | -443 | 2.0 (2.1) | 22.00 | 0.41 (0.51) |
| sluggish | -10.40 | 4.11 | -5.43 | -438 | 1.9 (2.0) | 21.99 | 0.41 (0.51) |
| raw_return | -9.68 | 1.93 | -5.09 | -416 | 2.1 (2.1) | 22.01 | 0.41 (0.51) |
| minute_only | -8.34 | 7.47 | -4.23 | -416 | 2.1 (2.0) | 21.99 | 0.42 (0.52) |
| low_flow | -9.70 | 3.32 | -5.02 | -436 | 2.1 (2.2) | 22.00 | 0.41 (0.51) |
| high_flow | -10.33 | 5.05 | -5.38 | -429 | 2.0 (1.9) | 22.00 | 0.42 (0.52) |
| loss_minus20 | -11.36 | 1.00 | -6.52 | -401 | 2.1 (2.2) | 22.02 | 0.43 (0.53) |
| steep_outlet | -10.43 | 3.25 | -5.34 | -452 | 2.0 (2.1) | 22.00 | 0.41 (0.51) |
| shallow_outlet | -10.64 | 3.45 | -5.78 | -441 | 2.0 (2.0) | 22.00 | 0.41 (0.51) |
| frost_melt_lo | -10.50 | 3.56 | -5.52 | -448 | 2.1 (2.1) | 22.00 | 0.41 (0.51) |
| frost_melt_hi | -10.45 | 3.68 | -5.63 | -435 | 2.0 (2.0) | 22.00 | 0.41 (0.51) |
| light_slab | -9.99 | 3.15 | -5.53 | -402 | 2.3 (2.3) | 21.98 | 0.39 (0.49) |
| heavy_slab | -10.53 | 4.96 | -5.35 | -457 | 1.9 (2.0) | 22.00 | 0.42 (0.53) |
| sun_plus30 | -10.13 | 3.56 | -4.90 | -483 | 2.0 (2.0) | 22.01 | 0.42 (0.53) |
| sun_minus30 | -10.81 | 4.48 | -6.22 | -391 | 2.1 (2.1) | 22.00 | 0.43 (0.52) |
| forecast_pessimistic | -9.95 | 3.95 | -5.26 | -420 | 2.1 (2.1) | 22.00 | 0.41 (0.51) |

**20 of 20 `better`, 0 undecided, 0 worse, no constraint broken.** Flags: `min_off` everywhere,
`cold_share` on `loss_minus20`. (`pmin_duty` on the same seeds: -8.10 to -11.75.)

### 6.3 Weeks, seeds 0-2 (diagnostic, fresh start each week; `weeks_final.txt`)

| week | adj % | ± | energy % | metered % | starts/d (base) | mean air (breaks) |
|---|---|---|---|---|---|---|
| oct_mild | -46.4 | 24.3 | -10.8 | +2.7 | 1.9 (1.9) | 22.09 (3 of 3) |
| nov_mixed | -11.7 | 5.2 | -5.3 | -1.4 | 3.0 (3.2) | 22.05 (1) |
| dec_damp | -5.0 | 3.4 | -4.7 | -4.4 | 2.7 (2.5) | 21.98 (1) |
| jan_cold | -5.7 | 2.5 | -4.0 | -5.5 | 1.7 (1.2) | 21.94 (2) |
| feb_sunny_cold | -10.4 | 2.2 | -5.1 | -2.4 | 1.7 (1.3) | 22.00 (1) |
| mar_shoulder | -30.6 | 8.7 | -7.8 | +0.8 | 1.3 (1.6) | 22.16 (3) |
| apr_mild_sunny | -45.1 | 24.7 | -9.7 | -12.3 | 0.9 (1.1) | 22.31 (2) |

All seven `better`, but the mean-air band is missed in 13 of 21 week-seeds. The mild weeks run
warm from a fresh start: the prior `ts0` was set for the season mean, and the slab need is not
stationary (the learned integral is about +2 to +4 K in Oct-Feb and -1 to -6 K in sunny spring).
With `ts0` 0 the misses fall to 10 of 21 (warm and cold weeks both), with the season at -10.39 %
and a worse dead-thermometer case; no prior centres all seven weeks, which matches what
`pmin_duty` found. The baseline gets a per-week oracle offset. A deployment persists the
learned state through `state()` / `restore()` (section 6.5, restart rows).

### 6.4 Diagnostics (season, seeds 0-2; `diag_final.txt`)

| variant | hybrid adj % | energy % | pmin_duty adj % |
|---|---|---|---|
| `flat_load` (no part-load penalty) | -6.85 | -1.41 | -6.61 |
| `long_outage` (3-day Modbus loss) | -10.18 | -5.22 | -10.03 |
| `sparse_thermometer` | -10.63 | -5.31 | -10.40 |
| `synthetic_dist` | -9.93 | -5.22 | -10.01 |

### 6.5 Fault checks (season, seeds 0-2; wrappers in `.local/lab-results/controllers/hybrid/scripts/hyb_faults.py`, `faults_v5.txt`)

| fault | adj % | verdict | energy % | mean air | mae |
|---|---|---|---|---|---|
| forecast removed all season | -7.32 | better | -3.76 | 21.97 | 0.44 |
| forecast missing 2 days in every 7 | -10.26 | better | -5.17 | 22.00 | 0.41 |
| Home Assistant restart every 2 days, learned state persisted | -10.40 | better | -5.34 | 22.00 | 0.41 |
| same, learned state lost at every restart | -9.73 | better (mean air 22.06 / 22.10 breaks on 2 seeds) | -5.20 | 22.02 | 0.42 |
| room thermometer dead from day 30 | -3.50 | better, but breaks mae and mean air | -6.31 | 22.16 | 0.57 |
| room value frozen (still reported) from day 30 | -3.59 | better, but breaks mae and mean air | -6.31 | 22.16 | 0.57 |

Before the fallback curve (integral fading to the prior), a dead thermometer gave +26 % (mean
air 20.84 °C). The fallback curve learns the integral by outdoor temperature while the room is
known and takes over when it is lost; it barely changes nominal results (`tau_fb=0`: -10.58).
Without a room, nothing can follow the seasonal drift of the need, so the integration must raise
an alert when the room is stale or frozen.

## 7. The owner's two complaints

- **Too-hot water.** The hybrid's mean outlet while running is 30.8 °C against the baseline's
  30.1 °C, and its highest setpoint 35 °C against 39 °C. The literal low-water version
  (`q_run=0`) matches the baseline's water (30.2 °C) and loses 3.8 points, 2.8 of them energy.
  In this lab the waste is not the water temperature but the output level and the timing: no
  controller in the field won by running cooler. If the field test shows a flat part-load COP,
  set `q_run` to 0 (the structure and the comfort timing do not depend on it; `flat_load`
  then still gives -6.9 %).
- **Too many on/off cycles.** 2.0 starts a day, the same as the baseline, with longer median
  runs (300 vs 278 min) and 6 % of runs under 60 min. The verdict does not depend on the start
  price (break-even far outside 0.05-0.3 kWh). Below -10 °C it starts 1.6-1.7 times a day
  against the baseline's 1.2-1.3, because it runs 6.5-kW blocks where the baseline nearly
  modulates continuously.

## 8. Known weaknesses

- The energy half rests on the fitted part-load COP map (`flat_load` -1.4 %, `legacy_cop`
  -3.2 %, `partload_lo` -4.2 %). It is a hypothesis for the UNIT_MODEL 7.2 two-hold field test.
- About half the score is comfort priced at 0.54 kWh/K-h, from forecast sun and the learned
  daily pattern; the daily pattern needs 1-2 weeks to learn.
- Writes about 19 a day against the baseline's 10 (at most 37 in a day); `ride_hyst` 0.8 would
  add 0.3 points for 28 a day.
- Weekly mean air misses ±0.05 K in 13 of 21 fresh-start week-seeds; mild weeks run warm and
  meter +2.7 % (oct) / +0.8 % (mar) electricity; the normalisation and the comfort price turn
  that into a gain.
- Without a room thermometer it breaks the comfort constraints (mean air 22.16, mae 0.57).
- Relies on firmware behaviour: the immediate stop on a write 2 K under the control sensor,
  restart_delta 5 K, the dead-band hold during riding, and the ASSUMED 3-min minimum off
  (`min_off` flag on every run).
- The glow coefficient and the house priors come from the public lab docs (same real house),
  not from field measurements of this controller.
- It is close to `pmin_duty` by construction (both are slab thermostats with riding); its
  +0.3 point edge on the season is inside the interval.

## 9. Simulator observations

- The start burst is fixed (7.3 kW for 10 min whatever the setpoint gap), so soft-start
  strategies (research S6) cannot be credited or penalised.
- The ranking's energy side is decided mostly by the part-load COP surface (output level is
  worth 2.8 energy points, -1.4 % on `flat_load`).
- Weekly mean-air rule: the baseline is re-aimed per week with hindsight; fresh-start learning
  controllers cannot meet ±0.05 K reliably, whatever the prior.
- Normalised energy hides metered differences in mild weeks (oct metered +2.7 % reads as
  -10.8 % energy, because the hybrid ends the week warmer and the run-out buys it back).
- Harness: controller specs given as `path/file.py:Class` can fail in the process pool
  (reported earlier by others); `module:Class` via PYTHONPATH works and was used for the fault
  wrappers.

## 10. Reproduce

```
.local/lab-venv/bin/python -m lab.controllers.hybrid                      # self-check
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,hybrid -s season --seeds 0-2
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,hybrid -s season --seeds 0-1 --robust
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,hybrid -s weeks --seeds 0-2
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,hybrid,"hybrid[q_run=0]","hybrid[mode=fw]","hybrid[s=0]","hybrid[d_g=0]" -s season --seeds 0-2   # ablations
```
