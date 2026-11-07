# pmin_duty: a slab-thermostat duty-cycle controller

`lab/controllers/pmin_duty.py` (stdlib only, uses only the `Observation`). Strategy family: S5/S6
of [HEAT_PUMP_CONTROL_RESEARCH.md](../../HEAT_PUMP_CONTROL_RESEARCH.md), with S8-style timing.
All numbers are from the lab simulator ([SIMULATOR.md](../SIMULATOR.md)) on tuning seeds 0-2.

## 1. Summary

| | result (season, paired against `reference_tuned`) |
|---|---|
| Ranking, seeds 0-2, nominal | **-10.19 % ± 1.10 adjusted energy** (c = 0.2 kWh/start; -10.21 at c = 0.05, -10.18 at c = 0.3), `better`. Reviewer's seeds 3-4: -9.49 % ± 0.80 |
| Energy alone | **-5.18 %** normalised electricity (COP 3.06-3.08 against 2.89-2.91). This rests on the fitted part-load COP surface: -1.1 % under `flat_load`, -2.0 % with literal P_min. Read it as **roughly 1-5 % energy until a field test confirms the COP map** (section 10, M1) |
| Comfort | -448 K-h of \|air - target\| over the season (mean \|error\| 0.41 K against 0.51 K); about 46 % of the adjusted gain |
| Mean air | 22.00 °C (constraint ±0.05 K) |
| Starts | 2.1 a day (baseline 2.1); more than the baseline below -10 °C (1.6-1.8 against 1.2-1.3 a day) |
| Writes | 18.6-19.5 a day (baseline 10; limit 48; a rolling budget of 40 and a hard cap of 46) |
| Robust variants (20, seeds 0-1) | `better` on all 20 (-8.1 to -11.8 %), no constraint break |
| Weeks (seeds 0-2, diagnostic) | `better` in all seven weeks on seeds 0-2, but only 5 of 7 on seeds 3-4; 10 of 21 runs miss the mean-air band (section 9, M2) |
| Faults (seeds 0-2) | forecast removed: -7.20 %, better; room value frozen but still reported: -2.75 %, undecided, safe (mean air 21.84-22.24, 2.0 starts/d; before the guard +108 %, 18.97 °C) |

The headline finding is that the strategy's literal premise does not hold in this lab: **running
at the unit's minimum output is the least efficient way to cycle.** The measured COP map (UNIT_MODEL.md
7.2) makes 6-7 kW 10-25 % more efficient than the 3.6-4.4 kW floor at the supply temperature the
slab needs. The duty-cycle structure (few long blocks, slab as the buffer, run fraction from the
heat need) is kept, but the blocks run at about 6.5 kW. The literal P_min version (`q_run=0`) is
still better than the baseline (-6.6 %) but only through comfort; its energy is -2.0 %, against
-5.3 % at 6.5 kW.

## 2. Physics behind it

**Why it must cycle.** The house loses about 0.19 kW/K seen from the room: 3.7 kW at 0 °C and
2.35 kW at +10 °C, less sun and internal gains. The unit's floor is 1.8 + 0.05 x T_out K of loop
delta-T at 29 L/min, 3.6 kW at 0 °C and 4.3 kW at +7 °C. Above about 0 °C (lower on sunny days) the
compressor cannot run continuously, so the question is only *at what output* and *when* it runs.

**What the slab can buffer.** The slab holds 4.4 kWh/K and couples to the room at 0.43 kW/K.
Within a few hours a slab change of 1 K moves the room by only about 0.24 K (the room and the
heavy envelope, 74 kWh/K, absorb it; the steady gain is 0.8 K/K but with a time constant of days).
So a slab swing of ±1.4 K, which gives runs of 3-7 hours and about two starts a day, costs little
comfort. Measured: widening the band from 0.8 to 1.4 K cut starts from 3.2 to 2.2 a day with no
loss in the score.

**Which output to cycle at.** The supply temperature needed to put Q into the slab is
slab + Q / 1.43 kW/K (loop to slab 2.5 kW/K, effectiveness 0.71 at 29 L/min). Steady COP from the
unit model at that supply (central model and the COP variants; `pd_cop.py` analysis, slab
29.5 / 28.5 / 26.5 / 25.5 °C):

| outdoor | output | Q_min | 4.5 kW | 5 kW | 6 kW | 7 kW | 8 kW | 9 kW |
|---|---|---|---|---|---|---|---|---|
| -5 °C | central | 2.32 | 2.80 | 2.98 | 3.05 | **3.11** | 3.07 | 3.00 |
| -5 °C | partload_lo / hi | 2.57 / 2.08 | | | 3.04 / 3.09 | 3.06 / 3.18 | | |
| 0 °C | central | 2.95 | 3.26 | 3.44 | 3.49 | **3.51** | 3.45 | 3.37 |
| +7 °C | central | 4.97 | 5.03 | 5.23 | 5.33 | **5.36** | 5.30 | 5.18 |
| +10 °C | central | 5.60 | - | 5.74 | **5.82** | 5.81 | 5.73 | 5.61 |

Every COP variant puts the optimum at 6-7 kW, because the fixed running overhead (p0, about
0.25 kW) and the measured part-load surface outweigh the 3.3 %/K supply penalty of the extra
1.4-2 K. The same table says that in cold weather cycling at 7 kW beats continuous modulation at
the minimum. So "continuous modulation on a low curve below the balance point" happens here only
when the slab cannot keep up at 6.5 kW (below about -12 °C): the ride output then rises with the
slab deficit. Under `flat_load` (a diagnostic COP model without the part-load penalty, rejected
by the data) the energy advantage shrinks to -0.6 %, so the energy part of this result rests on
the measured part-load curve.

**What the comfort term rewards.** The baseline's room error has a strong daily shape (night
-0.4 K, afternoon +0.7 K: internal-gain profile, the measured disturbance profile and sun). A
slab-based controller can lean against it only by timing: heat in the evening and at night,
little in the late morning, and less before a sunny day. That timing, plus forecast sun, is
where about half of the score comes from.

## 3. The controller

Each minute:

1. **Slab estimate** from the water side. Idle (15 min after a stop): Ts = inlet. Running (8 min
   after a start): Ts = (inlet - 0.29 x supply) / 0.71, supply = outlet + 0.3 K. Frozen during and
   20 min after hot water and 10 min after a defrost; smoothed (0.2 per minute). Note that the
   simulator's return anchoring (SIMULATOR.md 3) makes the observed water differ from the house
   model's slab by -1.7..+1.7 K depending on the weather; the controller only needs a consistent
   index, and the learned curve absorbs the difference.
2. **Slab target**
   `Ts* = target + b (target - T_fc) - s GHI_fc + ts0 + kp e + trim + curve(T_fc) + daily(hour) + kw warm`
   - `T_fc`, `GHI_fc`: forecast means over hours 1-9 ahead (24 h mean of the unit's sensor if
     the forecast is missing);
   - `e` = target - room, the room corrected for sun on the thermometer (0.8 mK per W/m²);
   - `trim`: integral of e (0.15 K/K-h; x3 at takeover, fading over 2 days); its persistent part
     moves (time constant 120 h) into `curve`, a 5-knot curve over outdoor temperature (-25 ..
     +15 °C), half as a uniform offset and half on the knots around today's temperature, so the
     controller learns both the offset and the slope of the slab need;
   - `daily(hour)`: iterative learning over days. The room error at hour h is added (1 K per
     K-h per day) to a 24-bin correction applied at hour h - 5 h; zero-mean, ±2 K, 30-day leak;
   - `warm`: how much warmer the next 3 hours are than the next 24 (0.3 K per K): a small push
     of the runs into the warmer hours (COP, frost).
3. **Duty cycle**: start when Ts < Ts* - 1.4 K (after at least 45 min off), stop when
   Ts > Ts* + 1.4 K (after at least 60 min on).
4. **Run execution** (riding, S6c): kick with ceil(inlet - 0.8 + restart_delta + 0.15); from
   minute 2 ride at `inlet + Q/2.02 - 0.8 - 0.025 (Q - 5) + 0.55`, i.e. inside the firmware's
   dead band for the target output Q = max(6.5 kW, Q_min) + 2 kW per K of slab deficit beyond the
   band (smoothed over 30 min, at most 9 kW). Rewrite only when the ideal setpoint moved 1.3 K (0.8 K before the review)
   and 8 min have passed; never below t_ctrl - 1.5 K (an accidental stop). Stop with 25 °C, or
   t_ctrl - 2.1 K if that is lower, so the firmware stops at once; stops are deferred during a
   defrost (the outlet then reads the reversed cycle).
5. **Parking.** restart_delta is written once to 5 K (inside the recorded 4-5 K). While idle the
   setpoint follows the slab target, `floor(Ts* - band - 0.3 + delta - 0.8)`, never below 25 °C
   and never high enough to start the unit: the firmware's own restart threshold sits just
   below the controller's, so if the link fails the unit still restarts when the slab runs low.
   A start the unit makes by itself while heat is due is adopted as a run.

Safety and deployability: no writes while `link_ok` is False; DHW and defrost pause the run
logic; a rolling budget of 40 writes per 24 h (kicks and parks are always allowed); room lost
for 4 h → the short-term trim fades, the learned curve and forecast carry on.

## 4. Parameters (final defaults)

| name | value | meaning |
|---|---|---|
| `b`, `ts0` | 0.20 K/K, -1.5 K | prior slab need; learned away by the curve |
| `s` | 0.022 K per W/m² | forecast sun lowers the slab target |
| `lead0`, `lead1` | 1, 9 h | forecast window |
| `kp`, `ki` | 3 K/K, 0.15 K/(K h) | room feedback on the slab target |
| `ki_boost`, `boost_days` | 2, 2 d | faster trim at takeover (commissioning) |
| `tau_curve`, `curve_glob` | 120 h, 0.5 | trim to curve transfer |
| `ilc_g`, `ilc_lead`, `ilc_lim`, `ilc_leak` | 1 K/(K h day), 5 h, 2 K, 30 d | daily pattern |
| `kw` | 0.3 K/K | warm-hour preference |
| `glow` | 0.0008 K per W/m² | thermometer sun correction |
| `band`, `min_run`, `min_off` | 1.4 K, 60 min, 45 min | duty cycle |
| `q_run`, `kq`, `q_hi`, `tau_q` | 6.5 kW, 2 kW/K, 9 kW, 30 min | run output |
| `ride_every`, `ride_hyst`, `budget` | 8 min, 1.3 K (0.8 before the review), 40/day | write economy; hard cap 46/day for every write |
| `delta`, `delta_tries`, `failsafe`, `park_min` | 5 K, 3 per 24 h, on, 25 °C | parking (review fixes, section 9) |
| `curve0`, `room_hold` | 0 at every knot, off | curve prior; hold the trim while the room is lost (tested, worse) |
| `frozen_h` | 12 h | a room value unchanged (< 0.05 K) this long counts as stale; its learning is rolled back (review 2, section 10) |

## 5. Tuning record (season, seeds 0-2, nominal, adjusted % at c = 0.2)

| step | change | adj % | energy % | starts/d | note |
|---|---|---|---|---|---|
| 0 | first draft: heat-accounting (sigma-delta) duty cycle, run at Q_min | +2.95 worse | +0.42 | 2.8 | mean air 22.07, broke the constraint |
| 1 | rewrite as slab thermostat, Q_run 6.5 kW, band 0.8 K | -7.14 | -3.99 | 3.2 | |
| 1a | same, literal P_min (Q_run = Q_min) | -0.10 undecided | +0.36 | 5.8 | short runs, surges at low power |
| 1b | Q_run 5 / 8 kW | -4.91 / -6.63 | -1.79 / -3.87 | 2.7 / 3.9 | |
| 2 | no stop writes during defrost; ride guard against accidental stops | -7.19 | -4.02 | 3.2 | P_min: -2.52 |
| 3 | band 1.1 / 1.4 K | -7.60 / -7.38 | -4.16 / -4.00 | 2.6 / 2.2 | |
| 4 | forecast sun s 0.016 | -8.10 | -4.39 | 2.4 | |
| 5 | daily pattern (ILC), lead 5 h | -9.06 | -4.36 | 2.3 | mean air 22.07: broke |
| 6 | robust check: mean air 22.06-22.09 on `raw_return` and `loss_minus20`; spontaneous 6-min starts in `raw_return` (parked 25 °C setpoint inside the restart band) | | | 3.6-6 | |
| 7 | learned curve (120 h), restart_delta 5 K, park below the restart band, adopt unit starts | -8.95 | -4.54 | 2.3 | all constraints held |
| 8 | forecast window 1-9 h, kp 3, s 0.022, ride every 8 min | -10.41 | -4.91 | 2.4 | 30 writes/d |
| 9 | ride hysteresis 0.8 K, band 1.4, write budget, smoothed ride target | -10.18 | -4.82 | 2.1 | 24 writes/d; `jan_cold` had 50 writes/d before |
| 10 | warm-hour preference kw 0.3 (0.5 / 0.8: -10.18 / -9.04) | -10.42 | -5.34 | 2.1 | |
| 11 | fail-safe park (setpoint follows the slab target) | -10.37 | -5.25 | 2.1 | 29 writes/d |
| 12 | prior b 0.20, ts0 -1.5 (blind room test: mean air 22.4-22.7 → 21.8-22.2) | -10.51 | -5.30 | 2.1 | |
| 13 | trim boost at takeover (weeks start-up) | see section 6 | | | |

Neighbourhood of the final point (each one change; all `better`): `ki` 0.25 -10.33; `kp` 4
-10.30; `tau_curve` 72 / 240 -10.38 / -10.50; `band` 1.7 -10.14 (1.9 starts/d); `lead0` 0 -10.36;
`ilc_lim` 3 / 4 -10.07 / -9.74; `min_off` 90 -10.17; `ride_every` 30 -8.50.

Ablations from the final point (step 12):

| without | adj % | energy % | comfort K-h | note |
|---|---|---|---|---|
| (final) | -10.51 | -5.30 | -467 | |
| daily pattern (`ilc_g=0`) | -8.87 | -5.20 | -341 | the daily pattern is worth 1.6 % |
| forecast sun (`s=0`) | -8.67 | -4.69 | -366 | |
| warm-hour preference (`kw=0`) | -10.15 | -4.79 | -477 | trades comfort for energy |
| learned curve (`tau_curve=0`) | -10.59 | -5.44 | -459 | kept for the variants (step 6) and the blind-room fail-safe |
| run output: Q_min (literal P_min) | -6.56 | -2.03 | -413 | runs at 4.9-5.8 kW in practice: the firmware starts at 7.3 kW and ramps down slowly; 91 short runs |
| run output 5 / 6 / 7.5 kW | -9.19 / -10.31 / -10.43 | -4.01 / -5.13 / -5.39 | | 1.8 / 2.0 / 2.3 starts/d |

## 6. Results

### 6.1 Season, nominal, seeds 0-2

| seed | controller | kWh/d | norm/d | COP | starts/d | run p50 min | mean outlet running | air | mae | writes/d | defrosts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | reference_tuned | 27.06 | 26.81 | 2.91 | 2.1 | 288 | 30.3 | 22.00 | 0.49 | 9.7 | 1021 |
| 0 | pmin_duty | 25.63 | 25.39 | 3.09 | 2.1 | 279 | 31.3 | 22.00 | 0.40 | 28.4 | 1019 |
| 1 | reference_tuned | 26.19 | 25.96 | 2.91 | 2.0 | 276 | 30.1 | 22.01 | 0.53 | 9.8 | 999 |
| 1 | pmin_duty | 24.72 | 24.52 | 3.09 | 2.1 | 260 | 31.1 | 22.00 | 0.41 | 28.9 | 989 |
| 2 | reference_tuned | 26.07 | 25.80 | 2.89 | 2.0 | 270 | 30.0 | 22.01 | 0.52 | 9.3 | 989 |
| 2 | pmin_duty | 24.71 | 24.46 | 3.06 | 2.1 | 264 | 31.1 | 22.00 | 0.41 | 27.9 | 1006 |

Paired ranking: **adjusted -10.52 % ± 1.40** (c = 0.2; -10.56 at c = 0.05, -10.50 at c = 0.3;
break-even start cost 44 kWh, i.e. the verdict does not depend on the start price), `better`;
energy -5.36 %, metered -5.36 %, comfort -463 K-h, starts 2.1 against 2.1 a day, mean air 22.00,
mean |error| 0.41 against 0.51 K. Flag: `setpoint_range`. The review found this understated (section 9, M3).

Per daily-mean outdoor bucket, seed 0 (true supply while running, COP of running minutes; baseline
run with offset 0, mean air 22.00; controller at step 12):

| bucket | days | baseline kWh/d | pmin_duty kWh/d | baseline Q_run / supply / COP | pmin_duty Q_run / supply / COP | starts/d base / pmin |
|---|---|---|---|---|---|---|
| < -10 °C | 27 | 51.1 | 47.0 | 6.2 kW / 32.0 / 2.55 | 6.7 kW / 32.0 / 2.70 | 1.3 / 1.8 |
| -10..-5 | 18 | 42.9 | 42.8 | 5.6 / 31.3 / 2.85 | 6.5 / 32.3 / 2.94 | 1.8 / 2.3 |
| -5..0 | 26 | 34.9 | 34.0 | 5.3 / 31.0 / 3.12 | 6.3 / 31.9 / 3.24 | 2.0 / 2.3 |
| 0..+5 | 63 | 21.1 | 19.7 | 5.0 / 30.0 / 3.65 | 6.5 / 31.3 / 3.93 | 2.4 / 2.3 |
| > +5 | 48 | 11.2 | 10.5 | 4.8 / 29.0 / 4.59 | 6.3 / 30.5 / 5.16 | 2.6 / 2.1 |

Run lengths (seed 0): median 270 min, quartiles 165 / 441 min, 5 % under 60 min. Room error by
local hour: the baseline's daily shape -0.39 K (04-05 h) / +0.67 K (13-14 h) becomes -0.35 /
+0.39 K. The supply is about 1 K warmer than the baseline's (the price of 6.5 kW runs) and COP of
the running minutes is still 3-12 % higher.

### 6.2 Robust variants, seeds 0-1

| variant | adj % (c=0.2) | ±90 % | c=0.05 / c=0.3 | energy % | comfort K-h | starts/d (base) | air | mae (base) | verdict |
|---|---|---|---|---|---|---|---|---|---|
| nominal | -10.44 | 5.17 | -10.47 / -10.41 | -5.44 | -451 | 2.1 (2.1) | 22.00 | 0.41 (0.51) | better |
| partload_lo | -9.33 | 3.61 | -9.37 / -9.31 | -4.30 | -452 | 2.1 (2.1) | 22.00 | 0.41 (0.51) | better |
| partload_hi | -12.05 | 5.67 | -12.11 / -12.00 | -7.16 | -450 | 2.2 (2.0) | 22.00 | 0.41 (0.51) | better |
| legacy_cop | -8.53 | 3.36 | -8.57 / -8.50 | -3.39 | -459 | 2.1 (2.1) | 22.00 | 0.40 (0.51) | better |
| high_start_loss | -10.29 | 4.88 | -10.33 / -10.27 | -5.36 | -451 | 2.1 (2.1) | 22.00 | 0.41 (0.51) | better |
| sluggish | -10.42 | 4.17 | -10.47 / -10.39 | -5.46 | -451 | 2.1 (2.0) | 22.00 | 0.41 (0.51) | better |
| raw_return | -10.05 | 3.35 | -10.05 / -10.05 | -5.17 | -440 | 2.1 (2.1) | 22.00 | 0.41 (0.51) | better |
| minute_only | -8.40 | 6.12 | -8.48 / -8.35 | -4.18 | -429 | 2.1 (2.0) | 22.00 | 0.42 (0.52) | better |
| low_flow | -10.50 | 3.09 | -10.44 / -10.54 | -5.54 | -461 | 2.1 (2.2) | 22.00 | 0.40 (0.51) | better |
| high_flow | -10.83 | 5.58 | -10.94 / -10.75 | -5.92 | -435 | 2.1 (1.9) | 22.00 | 0.41 (0.52) | better |
| loss_minus20 | -11.89 | 3.10 | -11.86 / -11.90 | -6.57 | -440 | 2.1 (2.2) | 22.01 | 0.42 (0.53) | better (`cold_share`) |
| steep_outlet | -10.47 | 4.34 | -10.52 / -10.43 | -5.40 | -459 | 2.2 (2.1) | 22.00 | 0.41 (0.51) | better |
| shallow_outlet | -10.59 | 4.38 | -10.67 / -10.54 | -5.77 | -445 | 2.1 (2.0) | 22.00 | 0.41 (0.51) | better |
| frost_melt_lo | -10.49 | 5.10 | -10.55 / -10.45 | -5.54 | -450 | 2.2 (2.1) | 22.00 | 0.41 (0.51) | better |
| frost_melt_hi | -10.67 | 4.16 | -10.73 / -10.63 | -5.71 | -453 | 2.1 (2.0) | 22.00 | 0.41 (0.51) | better |
| light_slab | -10.19 | 3.41 | -10.31 / -10.12 | -5.70 | -417 | 2.5 (2.3) | 21.98 | 0.39 (0.49) | better |
| heavy_slab | -10.42 | 5.94 | -10.41 / -10.43 | -5.25 | -460 | 2.0 (2.0) | 22.01 | 0.42 (0.53) | better |
| sun_plus30 | -10.11 | 3.80 | -10.12 / -10.10 | -4.86 | -490 | 2.1 (2.0) | 22.01 | 0.42 (0.53) | better |
| sun_minus30 | -10.84 | 6.20 | -10.85 / -10.83 | -6.05 | -412 | 2.1 (2.1) | 22.00 | 0.42 (0.52) | better |
| forecast_pessimistic | -10.15 | 4.56 | -10.17 / -10.13 | -5.33 | -435 | 2.1 (2.1) | 22.00 | 0.41 (0.51) | better |

**20 of 20 better, 0 undecided, 0 worse; no constraint broken** (mean air 21.98-22.01; flags only
`setpoint_range`, `min_off`, `cold_share`). The intervals are wide because n = 2 seeds.

### 6.3 Weeks, seeds 0-2 (diagnostic)

| week | adj % (c=0.2) | ±90 % | energy % | comfort K-h | starts/d (base) | air (per-seed breaks) | mae (base) | verdict |
|---|---|---|---|---|---|---|---|---|
| oct_mild | -41.98 | 27.05 | -12.45 | -29 | 1.7 (1.9) | 21.97 (21.90) | 0.48 (0.66) | better |
| nov_mixed | -11.07 | 4.20 | -6.44 | -10 | 3.0 (3.2) | 22.00 | 0.30 (0.36) | better |
| dec_damp | -4.10 | 2.46 | -4.60 | +1 | 2.8 (2.5) | 21.94 (21.92) | 0.28 (0.28) | better |
| jan_cold | -5.06 | 2.82 | -3.93 | -9 | 2.1 (1.2) | 21.89 (21.81, 21.88) | 0.42 (0.48) | better |
| feb_sunny_cold | -8.36 | 3.25 | -5.07 | -18 | 1.9 (1.3) | 21.96 (21.90) | 0.50 (0.60) | better |
| mar_shoulder | -30.35 | 5.33 | -9.96 | -26 | 1.3 (1.6) | 21.99 (21.93, 22.06) | 0.83 (0.99) | better |
| apr_mild_sunny | -38.20 | 33.33 | -8.31 | -26 | 0.7 (1.1) | 22.18 (22.06, 22.54) | 0.90 (1.06) | better |

All seven weeks `better` on seeds 0-2 (not on the reviewer's seeds 3-4: section 9, M2), but 9 of 21 week-seed runs break the ±0.05 K mean-air constraint
(start-up learning; the baseline is tuned per week). In the mild weeks the adjusted % is
dominated by comfort K-h against a small baseline electricity. Cold weeks start more often than
the baseline (2.1 against 1.2 a day in `jan_cold`).

### 6.4 Diagnostics and fail-safe checks (seeds 0-1, version of step 10)

| check | adj % | energy % | note |
|---|---|---|---|
| `flat_load` (no part-load penalty) | -5.79 | -0.64 | the energy gain is the part-load curve |
| `frost_no_melt` / `legacy_frost_r1` | -10.70 / -10.02 | -5.78 / -5.28 | |
| `long_outage` (3-day Modbus loss) | -10.19 | -5.44 | room 21.0-22.4 °C during the outage at -14 °C |
| `sparse_thermometer` | -10.60 | -5.49 | |
| `synthetic_dist` | -10.19 | -5.56 | the daily-pattern gain is not an artefact of the recorded-day bootstrap |
| `era5_only` | -10.38 | -5.41 | |
| forecast removed for the whole season | -7.63 | -4.06 | falls back to the 24 h mean of the unit's sensor |
| room sensor dead after day 30 (step 12) | -3.41 | -7.28 | mean air 21.84-22.17, mean \|error\| 0.59-0.62: breaks the comfort constraints but stays safe |

## 7. Known weaknesses

- **The energy gain depends on the part-load COP curve.** Under `flat_load` it falls to -0.6 %;
  under `partload_lo` and `legacy_cop` it is -4.3 % and -3.4 %. A field test (two 3-hour holds
  at equal supply, one at minimum output and one at 6 kW, UNIT_MODEL.md 7.2) would settle it.
- **About half the score is comfort**, mostly from timing heat against the house's daily pattern
  and the sun. It is real tracking, priced at the baseline's own rate, but it depends on the
  simulated disturbance profile and the forecast sun; the ILC needs 1-2 weeks to learn.
- **Start-up.** Learned state (trim, curve, daily pattern) starts at zero. In 7-day weeks the
  mean air misses ±0.05 K in 9 of 21 week-seed runs (21.81-22.06 °C; up to 22.54 °C in the sunny April week,
  where no heating-only controller can avoid overheating without undercooling at night, which
  the per-week-tuned baseline does by construction). A real deployment would keep its learned
  state across restarts.
- **Writes**: about 28 a day (the baseline writes 10). Riding to hold 6.5 kW needs a setpoint
  change roughly every hour as the return warms, plus kick, stop and park writes per run. The
  rolling budget keeps it under 40.
- **Supply about 1 K warmer than the baseline** during runs (31.3 against 30.3 °C mean outlet).
  The owner's "too-hot water" concern is answered by efficiency, not by the lowest temperature.
- **Assumed firmware behaviour**: the controller relies on the firmware's stop-at-once rule
  for writes 2 K below the control sensor, on restart_delta 5 K, and on stopping by setpoint
  rather than by heating off. A stop at a low control temperature still needs a setpoint below
  25 °C for a few minutes (0.00-0.01 % of the time after the review fixes; section 9, M3).
- **Short hot-water pre-emptions** still make a few runs under 15 minutes (`runs_lt_15min` /
  `min_off` flags appear in some seeds).
- Defaults were tuned on season seeds 0-2 only; seeds 5-9 were never run.

## 8. Reproduce

```
.local/lab-venv/bin/python -m lab.controllers.pmin_duty                       # self-check
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,pmin_duty -s season --seeds 0-2
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,pmin_duty -s season --seeds 0-1 --robust
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,pmin_duty -s weeks --seeds 0-2
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,"pmin_duty[q_run=0]" -s season --seeds 0-2   # literal P_min
```

## 9. Review fixes (2026-11-07)

An adversarial review (seeds 3-4, its files in
`.local/lab-results/controllers/pmin_duty/review/`) confirmed the season result (-10.03 % on
seeds 3-4) and raised three major issues. All three were real and are fixed or answered below.
Fix runs are in `.local/lab-results/controllers/pmin_duty/fix*/`, and the helper scripts are in
`fix/scripts/`.

**M1: the restart_delta write could storm and block runs (fixed).** The old code returned
`Command(restart_delta=5)` every idle minute while the register did not read back 5, before the
run logic. Now:
- it compares with a 0.25 K tolerance;
- it tries at most 3 times per rolling 24 h, 30 minutes apart, and only in mode `idle`;
- each try counts in the write log;
- the try rides on the command the run logic produced, so there is no early return;
- if the value never takes, the kick and park arithmetic use the restart_delta the unit reports.

Two more guards cover writes that never take:
- a hard cap of 46 writes per rolling 24 h applies to every write, kicks and stops included;
- an identical setpoint is not rewritten within 5 minutes.

On the reviewer's `edge.py` (restart_delta stuck at 4, a static observation where no write ever
shows up) the writes fall from 1440/day to 45/day. The self-check now asserts that a stuck delta
makes at most 6 tries in 2 days and that a cold slab still kicks a run.

**M3: setpoints below 25 °C (fixed).** The reviewer's numbers (6 % of minutes under
`raw_return`) had three causes:
1. the idle park cap `floor(inlet - 0.8 + delta - 0.6)` fell under 25 °C when the return water
   was about 21 °C;
2. after a stop write, raising back to 25 °C was held back by the write budget and by the
   "small raises wait 120 min" rule;
3. under `raw_return`, the ride setpoint (return + Q/KF) itself fell under 25 °C early in a run.

Now:
- the idle park never goes below `park_min` = 25 °C;
- climbing back to the floor after a stop is critical (it bypasses the budget and the wait);
- the ride setpoint is floored at 25 °C;
- if very cold return water lets the unit start by itself at the 25 °C floor, the controller
  keeps that run as a normal run instead of stopping it.

Three options were tested on `raw_return`, season seeds 0-2:

| option | adjusted % | starts/day | setpoints below 25 °C |
|---|---|---|---|
| keep self-starts (chosen) | -9.69 | 2.2 | 0.01 % of time, no flag |
| stop them, floor only | -9.73 | 2.4 | `runs_lt_15min` 9-14 % of runs |
| hold sub-25 setpoints for 7 days after a self-start | -10.07 | 2.1 | 3.5-5.7 % of time |

Final defaults:
- `setpoint_out_of_range_pct` is 0.00 % (nominal) and 0.01 % (`raw_return`), on seeds 0-2 and on
  seed 3;
- what remains are stop writes held for a few minutes while the unit runs down;
- the robust run shows no `setpoint_range` flag on any variant.

Heating-off as a park was not used: its pump-stop and purge behaviour is ASSUMED and it would
blind the slab estimate.

**M2: the weeks claim (corrected, partly a limit of the scoring).** The claim "better in all 7
weeks" holds on seeds 0-2 only; on seeds 3-4 two weeks are undecided. The mean-air misses in
weeks are not fixed, and the evidence shows they cannot be fixed by a non-oracle controller
against this baseline:
- **Persistence added.** `state()` and `restore()` carry the learned trim, curve, daily pattern
  and age (the commissioning boost now fades with the persisted `age`, not `obs.minute`). A Home
  Assistant integration saves this in a Store.
- **Persisted state gives a better score but does not cure mean air.** A wrapper restored the
  state a season run (seed 0) had at each week's start date (`fix/scripts/persist.py`). Weeks,
  seeds 0-2: adjusted % improves in 6 of 7 weeks (jan_cold -6.1 vs -5.1, mar_shoulder -32.2 vs
  -28.1, feb -9.3 vs -8.2, nov -12.5 vs -11.1, oct -44.0 vs -41.6, apr -39.2 vs -36.6, dec -3.5
  vs -4.3). Mean-air misses are 10 of 21, against 11 of 21 from a cold start.
- **A curve prior does not help.** The learned curve is not stationary: about +2 to +4 K in
  Nov-Feb, about 0 K in March and April, at the same outdoor temperatures. Priors of 1.5 K and
  2 K at every knot moved the misses around (10 and 12 of 21) without removing them. The prior
  stays at zero.
- **The baseline fails the same band without its oracle.** `reference_tuned` uses a mean-air
  offset fitted per week (for example -0.45 K for oct_mild, -0.37 K for jan_cold, 0 for apr,
  against -0.07 K for the season). With the season offset fixed for all weeks it misses ±0.05 K
  in 14 of 21 week-seed runs, by up to +0.98 K (`fix/wref`). The weekly band therefore measures
  week-to-week variance of mean air (about ±0.1 K for this controller), which only a per-week
  oracle avoids.

Final weeks (seeds 0-2, after the fixes): all 7 `better`. Adjusted %: oct -42.3, nov -10.7, dec
-4.6, jan -5.0, feb -8.1, mar -28.8, apr -36.0. Mean air misses ±0.05 K in 10 of 21 runs
(21.81-22.07; apr seed 1 22.57).

**Minor items.**

| item | what was done |
|---|---|
| m1 COP slope | Not changed. It is disclosed; the field test in UNIT_MODEL 7.2 is still the gate. |
| m2 comfort share | Energy and comfort are reported separately in every table. |
| m3 room dead | Holding the trim was tested (`room_hold=1`): -1.33 % undecided, mean air 21.88-22.46. Letting it fade (default): -3.36 % better, mean air 21.85-22.18. Both break the mae and mean-air limits. Cause: the curve is not stationary, so without a room sensor the slab target cannot follow the seasonal drift. A deployment must raise an alert when the room has been stale for more than a few hours. The fade stays. |
| m4 writes | `ride_hyst` 0.8 → 1.3 K: 18.6-19.5 writes/day instead of 28; costs 0.3 points of adjusted % (-10.19 vs -10.50); also lowers the mean outlet 31.1-31.3 → 30.8-30.9 °C. `ride_hyst` 1.0 was free but only went to 26.5/day. |
| m5 NaN | A non-finite outdoor, outlet, inlet, setpoint or restart_delta is treated as a link drop (`Command()`, no state update); a NaN room is treated as missing. Covered by the self-check. |
| m6 restart | The boost uses the persisted `age`; the learned state persists (above). Timers (`t_state`, the write log) are short-lived and are rebuilt within an hour. The `min_off` flag remains: the unit's own ASSUMED 3-minute minimum off time sometimes delays a kick right after a stop or a hot-water cycle. |

**Results after the fixes.**

Season, seeds 0-2, nominal, against `reference_tuned`:

| metric | pmin_duty | reference_tuned |
|---|---|---|
| adjusted % (c=0.2 / 0.05 / 0.3) | -10.19 ± 1.10 / -10.21 / -10.18 | |
| energy % | -5.18 | |
| comfort K-h | -448 | |
| starts/day | 2.1 | 2.1 |
| writes/day | 18.6-19.5 | 9.3-9.8 |
| mean outlet while running | 30.8-30.9 °C | 30.0-30.3 °C |
| COP | 3.06-3.08 | 2.89-2.91 |
| mean air | 22.00 | |
| mae | 0.41 | 0.51 |

Verdict: better; flags `min_off`, `setpoint_range` (0.00 %).

Robust, seeds 0-1: **20 of 20 better**, 0 undecided, 0 worse, no constraint broken:
- adjusted % ranges from -8.10 (`legacy_cop`) and -8.18 (`minute_only`) to -11.75
  (`partload_hi`); nominal is -10.00;
- energy % ranges from -3.23 (`legacy_cop`) to -7.03 (`partload_hi`);
- mean air is 21.98-22.01.

## 10. Review 2 fixes (2026-11-07)

A second adversarial review (seeds 3-4, files in `.local/lab-results/controllers/pmin_duty/review/`)
reproduced the season result on the current build (-9.49 % ± 0.80, `better`), found no cheating
and raised three major issues. Runs for this round are in
`.local/lab-results/controllers/pmin_duty/review2/` (scripts in `review2/scripts/`).

**M2: a frozen room sensor that keeps reporting drove the house cold (real, fixed).** The guard
the review asked for is in place:
- A room value that has not moved by 0.05 K or more for `frozen_h` = 12 h is treated as stale
  even if its age looks fresh. `room_frozen` is set, which a Home Assistant integration raises as
  an alert. The value counts as fresh again as soon as it moves.
- The learned state (trim, curve, daily pattern) is snapshotted each time the room value changes.
  When the freeze is detected, the snapshot from the start of the frozen spell is restored, so
  what the frozen value taught is undone. That is a stronger fix than rate-limiting the drift.
- From then on the controller behaves as with a lost room: the trim fades, the curve and the
  daily pattern are frozen, and the forecast and the learned curve carry on.

Why 12 h: in nominal and variant runs (seeds 0-2, `review2/scripts/frozen_stats.py`), the longest
natural spell of an unchanged room value was 9.5-12.7 h, with one 23 h spell in `heavy_slab`.
The slab-movement test the reviewer suggested does not separate cases: natural spells over 6 h
had up to 4.2 K of slab range. A false trigger only pauses learning and rolls back a few hours of
it, so a nominal season is unaffected. Nominal, robust and weeks results are identical to two
decimals.

Result (season, seeds 0-2, room frozen at its day-30 value with age 5 min, `review2/scripts/pd_stuck.py`):

| | before (review, seeds 3-4) | after (seeds 0-2) |
|---|---|---|
| adjusted % | +108 % (worse) | -2.75 % ± 2.79 (undecided) |
| mean air | 18.97 °C (minimum 15.5) | 21.84 / 22.24 / 22.01 (minimum 19.6-19.9) |
| mae | 3.09 | 0.59-0.62 |
| starts/day | 7.6 | 1.9-2.0 |

The fault still breaks the mae and mean-air limits, as a dead room sensor does (section 9, m3):
without a room reading the slab target cannot follow the seasonal drift of the learned curve. It
is now safe, does not cycle, and the integration knows to alert.

**M1: the energy gain depends on the fitted part-load COP surface (agreed, disclosed).** No code
change can fix this; it is a question about the real unit. The review's numbers are reproduced
in substance: `flat_load` gives -1.1 % energy, literal P_min (`q_run=0`) -2.0 %, and about 53 %
of the saved kWh comes from days below -4 °C, where the simulator has the fewest validation days.
The summary (section 1) now reports energy as "roughly 1-5 % plus comfort timing". The 6-7 kW
run output must not be deployed as a claimed saving until the two-hold field test in UNIT_MODEL
7.2 (minimum output against 6 kW at the same supply) confirms the COP slope. If the test shows a
flat COP, set `q_run` to the unit's minimum. The duty-cycle structure and the comfort timing do
not depend on the COP map.

The review's minor point m2 (more starts below -5 °C, slightly warmer water) belongs here. It
is a direct consequence of the same COP assumption: below the balance point the baseline nearly
modulates continuously, while this controller still runs blocks at 6.5 kW or more. It is
disclosed and was not changed, because continuous modulation at lower output costs energy under
the lab's COP map. If the field test shows a flat COP, both concerns go away together with
`q_run` at the minimum.

**M3: weeks (agreed, reporting corrected).** On seeds 3-4, `feb_sunny_cold` and
`apr_mild_sunny` are undecided, so the claim "better in all 7 weeks" holds only on seeds 0-2.
Weeks are now reported as a diagnostic with n = 3 intervals. Final weeks on seeds 0-2 (this
build, `review2/weeks.txt`) are unchanged:

| week | adjusted % | ± |
|---|---|---|
| oct | -42.3 | 24.6 |
| nov | -10.7 | 4.3 |
| dec | -4.6 | 2.3 |
| jan | -5.0 | 2.7 |
| feb | -8.1 | 2.6 |
| mar | -28.8 | 8.0 |
| apr | -36.0 | 32.8 |

Mean air misses the band in 10 of 21 runs. Both remedies the review asked for were done in round 1
(section 9, M2):
- learned state persists through `state()` and `restore()`;
- weeks were run with the state of a season run restored at each week's start. That improved 6
  of 7 weeks but did not cure mean air: 10 of 21 misses.
- the baseline without its per-week oracle offset misses in 14 of 21.

**Minor items.**

| item | what was done |
|---|---|
| m1 stale claims | Section 1 and the returned summary now describe the shipped build: `ride_hyst` 1.3, 18.6-19.5 writes/day, -10.19 % on seeds 0-2, mean outlet 30.8-30.9 °C. |
| m2 water temperature, cold starts | Disclosed (M1 above): mean outlet while running 30.8-30.9 against 30.0-30.3 °C; on days below -10 °C, 1.6-1.8 against 1.2-1.3 starts/day. |
| m3 `min_off`, `glow` | Not changed. `glow` is the public HOUSE_MODEL thermometer term for the same real thermometer. A deployment should check it against the sensor in the field, and it is listed as a field-check item. The `min_off` flag comes from a kick landing inside the unit's ASSUMED 3-minute minimum off time. The unit simply delays the start, so a longer real minimum off only delays the kick. |
| m4 harness loader | Not a controller issue. Reported as a simulator concern. Fault wrappers here are separate files exposing `CONTROLLER`, and they load reliably. |

**Results of this build** (season, seeds 0-2, nominal):
- adjusted -10.19 % ± 1.10 (c = 0.05: -10.21, c = 0.3: -10.18), `better`;
- energy -5.18 %, comfort -448 K-h;
- 2.1 starts/day (baseline 2.1);
- 18.6-19.5 writes/day;
- mean outlet while running 30.8-30.9 °C (baseline 30.0-30.3);
- mean air 22.00, mae 0.41 against 0.51.

Robust, seeds 0-1: 20 of 20 `better`, no constraint broken:
- adjusted % from -8.10 (`legacy_cop`) and -8.18 (`minute_only`) to -11.75 (`partload_hi`);
- nominal -10.00;
- mean air 21.98-22.01.

Forecast removed for the whole season: -7.20 %, `better`, mean air 21.95-21.96.
