# econ_mpc: economic MPC with an online-identified grey-box model (S8 + S9)

`lab/controllers/econ_mpc.py`, stdlib only, `CONTROLLER = EconMPC`, assert-based self-check:
`.local/lab-venv/bin/python -m lab.controllers.econ_mpc`. It implements research strategies S9
(economic optimiser with a COP map and start costs) and S8 (forecast timing) of
`docs/research/HEAT_PUMP_CONTROL_RESEARCH.md`, on top of the S6 setpoint ride.

The controller plans the heat pump's output for the next 36 hours, every hour. The plan
minimises the electricity, plus the comfort cost, plus a start cost. It then carries out only
the first hour of the plan with setpoint writes, and plans again. The house model behind the
plan starts from the public house-model numbers. It learns online whatever those numbers get
wrong.

**Result after the review fixes (season, seeds 0-2, against `reference_tuned`): adjusted energy
-9.35 % ± 0.72.** The verdict is `better`, and it holds at both start costs. Energy alone is
-3.57 % (metered -3.41 %). Comfort is 511 K-hours better (mean |error| 0.40 against 0.51 K),
and the cold side is better too. Starts are 2.0 a day against 2.1. Writes are 20-22 a day, at
most 38 on any day. The verdict is `better` on all 20 mandatory robustness variants (seeds
0-1), and on all seven archive weeks. Section 8 lists the review fixes. Before the review the
score was -9.85 % with -4.82 % energy, but with 2.6 starts a day, the setpoint hunting and an
unsafe dead-thermometer path.

## 1. Idea

Three layers, all driven only by the `Observation`:

1. **Estimator** (every 10 minutes). This is a Kalman filter on a small grey-box house model. It
   fuses the room thermometer, the unit's inlet sensor and the heat into the loop. The heat
   comes from outlet - inlet.
2. **Planner** (every 60 minutes, and at once when the unit stops on its own). It searches 24
   blocks over 36 hours: 12 one-hour blocks, then 12 two-hour blocks. Each block gets an output
   level: off, minimum, 5, 6, 7 or 8.5 kW, or flat out. The search minimises

   `electricity(COP map at the predicted supply) + defrost cost + 0.54 kWh x K-hours of |room - aim| + c_start x starts - value of the heat still stored at the horizon end`.

3. **Executor** (every minute). It turns the first block into register writes. A block starts
   with the smallest setpoint that the firmware's restart rule accepts. The setpoint then rides
   near inlet + Q / (cp x flow), so the firmware's own error loop holds the planned output at the
   lowest supply temperature that delivers it. A block stops with a setpoint far below the
   control sensor. Between blocks the setpoint is parked at 25 °C.

The 0.54 kWh per K-hour comfort price is the ranking's own price. The controller therefore
minimises the ranked quantity itself. Its only extra rule is a slow trim that keeps the long-run
mean room on target, which the ranking requires.

## 2. The physics it uses

**House model** (HOUSE_MODEL.md section 1; time in hours, heat in kW, capacities in kWh/K):

```
C_s dT_s/dt = Q + k_sa (T_a - T_s) + k_sg (10 - T_s)                         slab, C_s 4.4
C_a dT_a/dt = k_sa (T_s - T_a) + k_ae (T_e - T_a) + k_ao (T_o - T_a) + q_air  air, C_a 4.3
C_e dT_e/dt = k_ae (T_a - T_e) + k_eo (T_o - T_e)                             envelope, C_e 74
k_sa 0.43, k_ae 1.35, k_sg 0.092 (to a 10 °C ground node)
k_ao 0.05, k_eo 0.064 (the published 0.111 kW/K to outdoors, split so that the time constants
come out at 2.2 h, 11 h and 430 h, as published)
q_air = 0.3 + d + g x GHI + theta x (T_o - 22)
```

- The steady heat to hold 22 °C is 6.39 / 5.04 / 3.69 / 2.34 kW at -20 / -10 / 0 / +10 °C. These
  are the published values.
- The 1-minute loop dynamics are ignored. The heat goes straight into the slab.
- The model is discretised exactly: a pure-Python matrix exponential, at 10 minutes for the
  filter and 1 hour for the plan.

**Learned online** (the filter states and the slow learners):

| quantity | how | why |
|---|---|---|
| `d` (kW, heat into the air) | state of the filter. It is an AR(1) process around a base: the 5-day mean of `d` plus a 24-value hour-of-day profile | people, cooking, airing and model error (HOUSE_MODEL.md section 7: hourly SD 1.1 kW, AR(1) 0.69/h) |
| `g` (kW per kW/m² GHI) | state, random walk while the sun is up | solar gain. The real gain comes through facades, so in low winter sun g settles at 10-14, and at 7 in November |
| `b` (K) | state: inlet sensor = slab + b (+ 0.2 K per kW while running) | the unit sees the loop return with an offset (return anchoring, SIMULATOR.md section 3). This makes the slab observable |
| `theta` (kW/K) | state, slow random walk | corrects the split between direct and envelope loss, which the data cannot pin down (section 5, step 6) |
| COP correction | metered electricity / modelled electricity, per outdoor band (4) x output band (2), steady minutes only | the COP map is a fit. It ends at 0.95-1.17 of the model |
| delivered / planned heat `eta` | measured loop heat over planned heat while a block runs, per outdoor band (5) | defrosts draw about 0.9 kWh each from the loop and stop the heat. Hot water pre-empts the heat. It ends at 0.82-0.86 below -3 °C and 0.93-0.98 above +2 °C |
| unit maximum | the output seen while running flat out | the manufacturer table (7.0 kW at -15 °C) is a prior, not the plant |
| aim trim | 7 % a day of the daily mean error of the estimated air | keeps the long-run mean room on target (±0.05 K is a ranking constraint) |

**Room measurement.** The thermometer reads warm in sunlight: about 0.8 K per kW/m² of GHI
(HOUSE_MODEL.md). The filter uses room - 0.8 x GHI_now. GHI_now comes from the PV power
(8.9 kW per kW/m², lab README), or from the forecast when PV is missing. Without this
correction, a controller that holds the thermometer on target holds the air about 0.05 K low
over the season.

**COP map** (UNIT_MODEL.md section 7.2, central model):
COP = COP6(T_out) x PL(Q) x exp(-0.031 (T_sup - 30)).
- COP6 is the 6-kW value: 2.85 / 3.33 / 3.81 / 5.47 at -15 / -7 / 0 / +7 °C, smooth.
- PL(Q) = 1 - 0.035 (6 - Q)² below 6 kW, and +1.5 % per kW above it, up to 9 kW. This
  reproduces the documented minimum-output penalty at -7, 0 and +7 °C within 2 %.
- T_sup = predicted slab + b + 0.70 K per kW (loop effectiveness 0.71 at 29 L/min).
- Defrost cost: the trigger builds per kWh of air heat. A defrost comes every 7.25 kWh below
  -1 °C, 9.9 at +1, 17 at +3 and 25 at +5 °C, and none above +10 °C. Each defrost costs
  0.13 kWh plus 0.9 kWh of heat bought back at the COP.

The map makes mid output (5-7 kW) clearly cheaper per kWh than the minimum (3-4 kW), even after
the higher supply temperature. At 0 °C, 6 kW at a 1.7 K warmer supply costs about 15 % less per
kWh than the minimum output. The planner therefore prefers fewer, shorter blocks at mid output
over long low-and-slow runs. Section 6 covers this.

**Firmware rules used by the executor** (UNIT_MODEL.md section 3):
- start when setpoint - t_ctrl >= restart_delta;
- stop at t_ctrl >= setpoint + 2 K, at once on a write that crosses it;
- output held while t_ctrl sits 0.1-1.0 K below the setpoint;
- t_ctrl = inlet - 0.7 K while idle, and outlet - 0.5 K while running.

## 3. The algorithm

**Planner.**
- *Prediction.* The room response is linear in the heat. One free trajectory (no heat) is
  simulated hourly over 36 h, using the forecast temperature and GHI and the learned `d`
  forecast. Each block adds its precomputed unit response, times its level, times `eta`.
- *Search.* Single-block changes, swaps of neighbouring on/off blocks, and *heat transfers*
  (one level more in block j and one less in a later block k, or the reverse). It starts from
  the previous plan, shifted, and stops when no move improves the cost (at most 5 passes).
- *Terminal value.* Heat that is still in the house at the horizon end (air + slab +
  envelope, per kW of each block, precomputed) is credited at 0.95 x the cheapest price of heat
  in the second half of the horizon. Without it the planner treats heat stored in the 74 kWh/K
  envelope as lost. It then lets the room fall 2.4 K in a cold week (section 5, step 1).
- *Start cost.* 0.7 kWh per start in the plan, plus 0.3 kWh per 10 K of outdoor below 0 °C
  (review fix R3; it was 0.3 kWh flat).
- *Cold-side comfort hinge.* Below aim - 0.5 K the comfort price rises from 0.54 to 1.04 kWh per
  K-hour (review fix R4).
- *Levels near the cap.* A discrete level within 1.5 kW of the cap merges into flat out (review
  fix R2).
- *Run limits.* Minimum run 60 min, minimum off 45 min, at most 7 starts in any 24 h.
- *Speed.* A plan takes a few milliseconds. On a heavily loaded machine (load average above
  300), a season with the simulator took 22 s of CPU, against 6 s with the baseline. The
  simulator alone takes about 3 s on an idle machine.

**Executor.**
- *Kick.* setpoint = ceil(inlet - 0.7 + 5 + 0.15). restart_delta is written to 5 K once. 5 K
  is a recorded value, so the 25 °C park holds the unit off until the control sensor is below
  20 °C.
- *Ride.* At a start and whenever the target output changes, setpoint =
  round(inlet + Q/2.02 - 0.25 - 0.025 (Q - 5)). After that, every 20 min at most, the setpoint
  moves ±1 K when the measured output (8-minute average) is more than 0.7 kW below or 0.9 kW
  above the plan. A step is never reversed within 45 min of the previous one. The setpoint is
  never closer than 1.6 K to the stop threshold.
  - Minimum-output blocks: the setpoint is held just below the control sensor, so the firmware
    ramps down to its floor and stays there.
  - Flat-out blocks: inlet + (Q + 2)/2.02, capped at 39 °C, rewritten only when it is more
    than 1 K off.
- *Stop.* Write floor(t_ctrl - 2.6), never below 25 °C. With a cool loop the firmware's
  3-minute rule then stops the unit once the water warms.
- *Park (backup thermostat).* Between blocks the setpoint is the lower of (a) the setpoint at
  which the firmware would restart by itself once the slab-side water falls below what holds
  the room at target - 1.5 K, and (b) the idle control sensor + restart_delta - 1, never below
  25 °C. While the controller is connected, (b) keeps every start its own. If the controller
  goes silent (link or Home Assistant down), the firmware keeps the slab from going cold.
- *Writes.* Every setpoint is inside 25-39 °C. A rolling 24-h budget stops trims at 38 writes,
  starts and parks at 45; stop writes always go through.
- *User switch.* If heating is switched off in the unit or Home Assistant, the controller
  writes nothing (it used to switch it back on).
- *No writes* during hot water, defrost, the 10 minutes after hot water, or link outages.

**Fail-safe.**
- *Link down.* No writes. The estimator assumes the last steady output if the unit was
  heating. Without this, a stale defrost reading counted as -10.5 kW for hours.
- *Room stale or missing.* A room value older than 90 min counts less with age (noise
  0.07 K + 0.06 K per hour of age). Older than 6 h, the thermometer counts as dead. Home
  Assistant cannot tell a dead battery from a steady room, and a steady room repeats its value
  for up to 7-9 h in the simulator. While dead:
  - the learned states (`d`, `g`, `b`, `theta`), their slow learners and both aim trims freeze;
    the inlet sensor may still correct the slab;
  - a daily *heat budget* steers the model. On every fully observed day the controller fits
    loop heat (kWh/day) = a + b (22 - T_out) + c min(GHI-sum, 2.5) by recursive least squares
    (forgetting 0.97, prior slope 0.19 x 24). On each mostly blind day it adds 0.5 x
    (delivered - expected) / 24 kW to the model's free-gain base (limit ±3 kW). When the
    thermometer returns, the correction is folded into the learned base.
- *Forecast missing.* Persistence of the 24-hour mean of the unit's outdoor sensor. GHI is 0.
- *Implausible estimate.* The filter restarts from the sensors and keeps its learned
  parameters.
- *Planner exception.* A low weather curve runs for 2 h.
- *Checks.*
  - A 3-day outage (`long_outage`, season seed 0): adjusted score unchanged (5747 against 5750
    kWh, with 0.2 kWh per start).
  - No forecast at all, plus no room reading 6 h a day (nov_mixed seed 0): mean |error| 0.29
    against 0.24 K, normalised energy +1.0 %.

## 4. Parameters (final)

| parameter | value | role |
|---|---|---|
| `w_comfort` | 0.54 kWh per K-h | comfort price (the ranking's) |
| `c_start` | 0.7 kWh (was 0.3) | start cost in the plan |
| `c_start_cold` | 0.3 kWh per 10 K below 0 °C | extra start cost in the cold (review R3) |
| `w_floor`, `floor_margin` | 0.5 kWh per K-h, 0.5 K | extra comfort price below aim - margin (review R4) |
| `flat_gap` | 1.5 kW | discrete levels this close to the cap merge into flat out (review R2) |
| `ride_rev_min` | 45 min | no ride step against the previous one within this (review R2) |
| `write_soft`, `write_hard` | 38, 45 per rolling 24 h | write budget: trims, then starts/parks; stops always (review R2) |
| `room_trust_min`, `room_stale_min` | 90, 360 min | room noise grows with age; older counts as dead (review R1) |
| `budget_gain` | 0.5 | dead-thermometer heat-budget integral, per day (review R1) |
| `stop_margin` | 2.6 K | stop write below the control sensor (review R7) |
| `park_backup`, `park_margin` | on, 1.5 K | park as a backup water thermostat for target - 1.5 K |
| `min_run` / `min_off` | 60 / 45 min | block limits |
| `max_starts_day` | 7 | hard cap (constraint 8) |
| `replan_min` | 60 | plus a replan after any unplanned stop |
| `levels` | 5, 6, 7, 8.5 kW (+ minimum, + flat out) | output levels of a block |
| `store_credit` | 0.95 | value of heat left at the horizon end |
| `transfer_span` | 8 blocks | heat-transfer moves |
| `restart_delta` | 5 K | written once |
| `ride_every` | 20 min | ride write rate |
| `d_tau_h` | 2.7 h | decay of the disturbance anomaly in the forecast |
| `sig_d`, `sig_g`, `sig_b`, `sig_th` | 0.25 kW, 0.05, 0.02 K, 0.0004 kW/K per 10 min | filter process noise |
| `r_room`, `r_inlet` | 0.07 K, 0.3 K | measurement noise |
| `d_slow_days` | 5 | level of `d` |
| `mean_fix_global` | 0.07 per day | long-run mean-air trim |
| `mean_fix` | 0 | per-outdoor-band aim trim (tested, off) |

## 5. Tuning record

All tuning was on seeds 0-2. Seeds 5-9 were never run. Scores are mean adjusted energy (kWh at
0.2 kWh per start) over season seeds 0-2. The baseline scores 6130.4, from 4811.6 kWh of mean
window electricity, so 10 kWh is about 0.2 %.

1. **No terminal value.** The first planner let the room fall to 19.6 °C in jan_cold, with a
   mean |error| of 2.4 K. Heat stored in the envelope looked lost at the horizon end, and the
   L1 comfort price could not pay for it at a COP of 2.3. Adding the stored-heat credit gave
   21.83 °C and 0.37 K.
2. **Speed.** Plans every 30 min over 36 hourly comfort points took 67 s of wall time per
   season. Changes:
   - hourly replanning;
   - a 24-point comfort grid;
   - interpolating the weather by index;
   - trying neighbour levels only.

   Result: 22 s of CPU under load.
3. **Executor.** Integer setpoints and the 0.9-K dead band let the output settle 1-1.5 kW below
   plan in cold weather. Feedback on the measured output closed the gap.
4. **Link outage.** A Modbus outage that began during a defrost froze the observation at
   -10.5 kW. The slab estimate fell to 10 °C and tripped a permanent fallback, after which
   season seed 0 ran at 22.73 °C. Changes:
   - assume the last steady output during an outage;
   - the inlet sensor became a filter measurement, with a learned offset;
   - a restart replaces the permanent fallback.

   Season seed 0 then came out at 4709 kWh normalised and 1752 K-h of comfort.
5. **First robust run** (snapshot v3, seeds 0-1). Better on all 20 variants, at -7.7 to -11.2 %.
   But mean air was 21.91-21.94 on `minute_only`, `low_flow` and `light_slab`, and cold days
   (below -10 °C) ran 0.26 K cool.
6. **Model check** (offline diagnostic only, not in the controller). The model was run open
   loop from the simulator's own states, with the true heat and disturbance.
   - It ran 0.2 K (nov_mixed) to 0.5 K (jan_cold) cold at 6-12 h. A constant +0.3 kW fixed
     nov_mixed. Cold weather needed more, which fits a weather-proportional error.
   - Moving k_ao by ±0.05 kW/K moved the 12-h bias by about ±1 K. The split is not identified.
   - So the controller learns `theta` online. It is not hard-coded.
7. **Delivered heat.** In cold weeks the plan assumed a 7-kW block delivers 7 kW. Defrosts and
   hot water left 82-86 % of it. Learning `eta` per outdoor band moved jan_cold's mean air from
   21.83 to 21.87 °C.
8. **Mean-air trims.** Season seed 0, score in kWh:

   | trim | score | mean air |
   |---|---|---|
   | none | 5732 | 21.96 |
   | global 0.3 a day | 5793 | |
   | per band, sunless hours, 0.3 a day | 5787 | 22.05 |
   | per band, sunless hours, 0.15 a day | 5765 | |
   | global 0.07 a day | 5759 | 22.00 |

   Every trim costs some comfort, because the L1 optimum tracks the median and not the mean.
   The weakest global trim was chosen for the ±0.05 K constraint.
9. **Capacity.** The robust run of snapshot v5 was undecided on `minute_only` (-7.0 ± 7.8 %,
   mean air 21.93). The planner's cap from the manufacturer table (5.6 kW at -25 °C) held the
   unit at 5 kW at -20 to -28 °C, and the room fell to 18.6 °C. The fix was a flat-out level,
   where the executor asks for more than the cap, plus a learned cap. `minute_only` seeds 0/1
   went from -4.6 / -6.5 % to -6.6 / -8.5 %.
10. **Parameter sweeps** (season seeds 0-2). Each row is a separate sweep against its own
    snapshot baseline:

    | snapshot | change | score | energy | K-h | starts/d | writes/d |
    |---|---|---|---|---|---|---|
    | v4 | as is | 5680.1 | 4604 | 1813 | 2.67 | 20.7 |
    | v4 | w_comfort 0.8 | 5680.9 | 4637 | 1746 | 2.79 | 20.9 |
    | v4 | c_start 0.4 | 5673.1 | 4614 | 1800 | 2.39 | 20.4 |
    | v4 | store_credit 0.9 / 1.0 | 5675.9 / 5671.7 | | | | |
    | v4 | levels 5, 6 only | 5709.6 | 4585 | 1917 | 2.47 | 16.1 |
    | v4 | levels 4.5-9 (5) | 5686.8 | | | | |
    | v4 | replan every 30 min | 5688.9 | 4615 | 1790 | 2.96 | 26.8 |
    | v4 | min_run 60 / min_off 45 | 5673.1 | | | 2.71 | |
    | v7 | c_start 0.3, ride_every 20 | 5677.7 | 4620 | 1787 | 2.53 | 22.9 |
    | v8 | w_comfort 0.7 | 5681.0 vs 5686.5 | | | | |
    | v8 | d_tau_h 5 | 5690.2 | | | | |
    | v8 | sig_d 0.15 | 5683.2 | | | | |

    Everything within about ±10 kWh is noise. The final defaults (c_start 0.3, min_run 60,
    min_off 45, ride_every 20) were chosen to keep starts and writes low at no measurable cost.
    The principled values stayed: w_comfort is the ranking's 0.54, and store_credit is 0.95.
11. **Heat-transfer moves.** One-block moves could not see "heat now, less later". A plan in a
    cold week let the room fall 1.4 K over 7 h before a big block. Adding transfers moved the
    score from 5686.5 to 5657.0 (seeds 5781 / 5628 / 5650 to 5750 / 5619 / 5603). It also
    removed the cold-day bias: days below -10 °C went from -0.25 to -0.09 K.

## 6. Results

All numbers in this section are from the version after the review fixes (section 8). Results
are in `.local/lab-results/controllers/econ_mpc/fix/` (`final_season`, `final_robust`,
`final_weeks`, `final_flat`, `faults_final`).

### Season, nominal, seeds 0-2

| seed | controller | kWh/d | COP | starts/d | run p50 min | outlet running °C | mean air | mean abs. error | K-h below -0.5 | K-h above +0.5 | min air | writes/d |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | reference_tuned | 27.06 | 2.91 | 2.1 | 288 | 30.3 | 22.00 | 0.49 | 204 | 516 | 20.2 | 9.7 |
| 0 | econ_mpc | 26.14 | 3.03 | 2.0 | 299 | 31.2 | 22.02 | 0.38 | 163 | 294 | 20.2 | 22.3 |
| 1 | reference_tuned | 26.19 | 2.91 | 2.0 | 276 | 30.1 | 22.01 | 0.53 | 230 | 578 | 19.9 | 9.8 |
| 1 | econ_mpc | 25.24 | 3.03 | 2.1 | 259 | 31.0 | 22.01 | 0.41 | 178 | 335 | 19.9 | 21.8 |
| 2 | reference_tuned | 26.07 | 2.89 | 2.0 | 270 | 30.0 | 22.01 | 0.52 | 214 | 596 | 19.5 | 9.3 |
| 2 | econ_mpc | 25.22 | 3.01 | 1.9 | 306 | 31.0 | 22.03 | 0.40 | 141 | 390 | 19.8 | 20.3 |

Rank line: adjusted -9.35 % ± 0.72 at c = 0.2 (-9.32 % at c = 0.05, -9.37 % at c = 0.3; the
candidate also has fewer starts, so the break-even start cost is negative); verdict `better`;
energy -3.57 %, metered -3.41 %; comfort -511 K-h; starts 2.0 against 2.1 a day; mean air
22.02 °C; mean |error| 0.40 against 0.51 K; no flags.

Other numbers (seed 0 unless noted):
- Minutes below 21 °C: 5920 / 6439 / 4274 against 6306 / 6715 / 6335 for the baseline (seeds
  0/1/2), 14 % fewer in all.
- Starts a day by outdoor temperature: below -10 °C 1.36-1.57 (baseline 0.93-1.23), -10..-4
  2.0-2.2 (1.4-1.7), -4..+4 1.8-2.2 (2.4-2.6), above +4 2.1-2.4 (2.1-2.4).
- Writes: 20.3-22.3 a day, at most 35-38 on one day. 24-27 % of in-run setpoint changes are
  reversed within 45 min. Most of these are 1-K steps 20-45 min apart, when the hourly plan
  changes its target output.
- Electricity by daily-mean outdoor band, seed 0 (baseline → econ_mpc): below -4 °C 2227 →
  2156 kWh, -4..+4 °C 1923 → 1866, above +4 °C 775 → 736. About 43 % of the saving falls on
  days below -4 °C. The ranking does not flag `cold_share` on nominal seeds 0-2. It flags it on
  three robust variants and on two archive weeks.
- No setpoint outside 25-39 °C, so the `setpoint_range` flag is gone.

### Robustness (season, seeds 0-1, all 20 mandatory variants)

| variant | adjusted % (c = 0.2) | ±90 % | verdict | energy % | comfort K-h | starts/d (base) | mean air | mean abs. error (base) | flags |
|---|---|---|---|---|---|---|---|---|---|
| forecast_pessimistic | -8.79 | 2.36 | better | -3.51 | -472 | 2.1 (2.1) | 22.02 | 0.40 (0.51) | |
| frost_melt_hi | -9.50 | 0.48 | better | -3.92 | -503 | 2.0 (2.0) | 22.02 | 0.39 (0.51) | |
| frost_melt_lo | -9.42 | 2.11 | better | -3.83 | -501 | 2.1 (2.1) | 22.02 | 0.40 (0.51) | |
| heavy_slab | -9.48 | 4.34 | better | -3.82 | -504 | 2.0 (2.0) | 22.02 | 0.41 (0.53) | |
| high_flow | -9.42 | 3.14 | better | -4.02 | -470 | 2.0 (1.9) | 22.02 | 0.41 (0.52) | |
| high_start_loss | -9.19 | 2.26 | better | -3.61 | -504 | 2.1 (2.1) | 22.02 | 0.39 (0.51) | |
| legacy_cop | -8.17 | 3.11 | better | -2.53 | -498 | 2.1 (2.1) | 22.02 | 0.40 (0.51) | |
| light_slab | -8.79 | 3.25 | better | -3.60 | -452 | 2.1 (2.3) | 22.00 | 0.38 (0.49) | |
| loss_minus20 | -9.25 | 1.21 | better | -4.34 | -402 | 2.1 (2.2) | 22.04 | 0.43 (0.53) | cold_share |
| low_flow | -7.90 | 1.25 | better | -2.88 | -465 | 2.1 (2.2) | 22.02 | 0.40 (0.51) | cold_share |
| minute_only | -7.60 | 5.21 | better | -2.62 | -495 | 2.0 (2.0) | 22.02 | 0.41 (0.52) | |
| nominal | -9.27 | 2.55 | better | -3.63 | -504 | 2.1 (2.1) | 22.02 | 0.39 (0.51) | |
| partload_hi | -10.39 | 5.07 | better | -5.04 | -490 | 2.1 (2.0) | 22.02 | 0.40 (0.51) | |
| partload_lo | -8.62 | 1.26 | better | -2.95 | -502 | 2.0 (2.1) | 22.02 | 0.40 (0.51) | |
| raw_return | -8.44 | 0.48 | better | -3.29 | -461 | 2.0 (2.1) | 22.02 | 0.41 (0.51) | |
| shallow_outlet | -9.69 | 2.01 | better | -4.19 | -500 | 2.1 (2.0) | 22.02 | 0.39 (0.51) | |
| sluggish | -9.24 | 2.65 | better | -3.71 | -500 | 2.1 (2.0) | 22.02 | 0.40 (0.51) | |
| steep_outlet | -9.03 | 3.53 | better | -3.29 | -510 | 2.0 (2.1) | 22.02 | 0.39 (0.51) | |
| sun_minus30 | -9.01 | 6.01 | better | -4.28 | -400 | 2.0 (2.1) | 22.03 | 0.42 (0.52) | cold_share |
| sun_plus30 | -8.89 | 2.58 | better | -3.20 | -526 | 2.0 (2.0) | 22.03 | 0.41 (0.53) | |
| flat_load (diagnostic, not mandatory) | -6.40 | 0.61 | better | -0.54 | -494 | 1.9 (2.2) | 22.02 | 0.40 (0.51) | |

All 20 are `better` at both start costs, with no constraint breaks.

### Fault checks (season seed 0, Observation-level wrappers, adjusted kWh at 0.2 kWh/start)

The baseline with a working thermometer scores 6197 kWh.

| fault | adjusted kWh | mean air | mean abs. error | monthly mean air range | min air |
|---|---|---|---|---|---|
| none (nominal) | 5761 | 22.02 | 0.38 | 21.95-22.09 | 20.2 |
| thermometer dead (None) from day 30 | 6189 | 22.12 | 0.56 | 21.53-22.84 | 19.4 |
| thermometer frozen (last value, age growing) from day 30 | 6164 | 22.06 | 0.55 | 21.49-22.77 | 19.3 |
| thermometer dead days 60-70, then back (pre-park snapshot) | | 22.01 | 0.39 | 21.94-22.09 | 20.3 |
| no forecast at all | 6037 | 22.12 | 0.45 | | 20.2 |
| 3-day link outage (`long_outage`) | 5754 (baseline 6209) | 22.02 | 0.38 | | 20.2 |

Before the fix the dead and frozen thermometer runs gave January means of 25.0-25.6 °C and
+53-68 % adjusted (review, seed 3).

### Archive weeks (seeds 0-2, diagnostics)

| week | adjusted % (c = 0.2) | ±90 % | verdict | energy % | metered % | starts/d (base) | mean air | mean abs. error (base) | flags / constraint breaks |
|---|---|---|---|---|---|---|---|---|---|
| apr_mild_sunny | -34.97 | 25.76 | better | -7.98 | +2.31 | 1.1 (1.1) | 22.54 | 0.91 (1.06) | runs_lt_15min, mean_air 22.28 / 22.55 / 22.78 |
| dec_damp | -2.61 | 2.28 | better | -2.59 | -2.37 | 2.6 (2.5) | 21.93 | 0.28 (0.28) | runs_lt_15min, mean_air 21.89 / 21.94 |
| feb_sunny_cold | -8.23 | 1.76 | better | -2.84 | -0.57 | 1.9 (1.3) | 22.04 | 0.43 (0.60) | runs_lt_15min, cold_share, mean_air 22.12 |
| jan_cold | -4.70 | 3.78 | better | -3.12 | -3.20 | 1.8 (1.2) | 21.97 | 0.41 (0.48) | runs_lt_15min, cold_share, mean_air 21.89 / 21.95 / 22.08 |
| mar_shoulder | -37.20 | 12.27 | better | -11.16 | +3.19 | 1.6 (1.6) | 22.30 | 0.78 (0.99) | runs_lt_15min, mean_air 22.26 / 22.28 / 22.35 |
| nov_mixed | -10.68 | 9.67 | better | -3.18 | +0.05 | 2.5 (3.2) | 22.05 | 0.27 (0.36) | runs_lt_15min, mean_air 22.08 |
| oct_mild | -41.00 | 36.46 | better | -9.70 | +8.41 | 1.6 (1.9) | 22.22 | 0.48 (0.66) | runs_lt_15min, mean_air 22.14 / 22.22 / 22.29 |

The mild-week percentages are not metered savings. Their denominators are small. The metered
electricity is higher in oct_mild, mar_shoulder and apr_mild_sunny (+2 to +8 %). The gain
there comes from less overshoot than the baseline, and from the run-out accounting: the house
ends the week warmer. Lead with the season numbers.

## 7. Known weaknesses

- **Warmer water, and more starts in deep cold.** This works against the owner's goal. The
  mean outlet while running is 31.0-31.2 against 30.0-30.3 °C. Starts in total are now at the
  baseline's level: 2.0 against 2.1 a day. Below -10 °C they are still 1.4-1.6 against
  0.9-1.2 a day. The optimiser follows the modelled part-load COP surface, where 5-7 kW beats
  the minimum output even at a 1-2 K warmer supply.
  - On the diagnostic `flat_load` the energy gain shrinks to -0.5 % (adjusted -6.4 %, almost
    all comfort). So the energy saving is a bet on the part-load curve. Settle it with the
    two-hold field test (UNIT_MODEL.md section 7.2, N3) before deploying.
  - The simulator under-predicts starts by 15-18 %, so on the real unit expect about 2.3-2.4
    starts a day.
- **Most of the score is comfort.** The -511 K-h is worth about 5.8 % of the electricity at
  0.54 kWh per K-h, which is more than the 3.6 % energy gain. Most of it is less warm
  overshoot (K-h above +0.5: 294-390 against 516-596). The cold side is now also better (K-h
  below -0.5: 141-178 against 204-230; 14 % fewer minutes below 21 °C).
- **Dead thermometer is a fallback, not closed loop.** With the thermometer dead from day 30
  the season scores about the same as the baseline with a working one. The monthly mean air
  wanders between 21.5 and 22.8 °C, because a few autumn weeks cannot pin the heat-against-
  weather relation.
- **Writes are 20-22 a day**, against about 10 for the baseline. The park backup adds about 3
  of them. The budget keeps every day at 38 or less.
- **About 43 % of the energy saving falls on days below -4 °C.** That regime has the least
  closed-loop validation (3 clean days). `cold_share` is flagged on three robust variants and
  on two weeks.
- **Weekly mean-air drift.** Each week starts from priors. The mean air runs 0.1-0.8 K warm in
  sunny mild weeks and up to 0.1 K cool in cold weeks. All weeks still rank better, but break
  the ±0.05 K constraint on most seeds. Weeks are diagnostics.
- **Priors from the public house summary.** The capacities and couplings are not learned. Only
  the disturbance, solar gain, water offset, loss trim, COP cells, delivered-heat ratio, cap
  and heat-budget relation are learned.
- **Solar is GHI-proportional.** Facade gain differs between low winter sun and spring sun.
- **Hot water is not anticipated.** A block that hot water pre-empts costs an extra start and a
  short run (`runs_lt_15min` on weeks).
- **The local search is not optimal.** It is a heuristic over levels, not a MILP.

## 8. Review fixes

Adversarial review (seeds 3-4, `.local/lab-results/controllers/econ_mpc/review/`). Tuning for
the fixes used seeds 0-2 only. Seeds 5-9 were never run.

| id | finding | verdict | fix | result |
|---|---|---|---|---|
| R1 (major) | dead or frozen thermometer overheats the house by 1-3.5 K | real | Room values older than 90 min lose weight, older than 6 h count as dead. While dead: the learned states, slow learners and aim trims freeze, and a daily heat budget (learned loop heat against weather) steers the model's free-gain base. | dead from day 30: mean 22.12 °C, monthly 21.5-22.8, adjusted 6189 against 6197 for the baseline with a working thermometer (was January 25.0-25.6 °C, +53 to +68 %) |
| R2 (major) | setpoint hunting, single days above 48 writes | real | Levels within 1.5 kW of the cap merge into flat out. The flat-out setpoint is rewritten only when more than 1 K off. Ride steps are never reversed within 45 min. Rolling 24-h write budget: trims stop at 38, starts and parks at 45, stops always pass. | max 35-38 writes on any day (was 49-50), mean 20-22. 24-27 % of in-run changes reverse within 45 min (the review measured 38 %); most are 1-K plan-target changes 20-45 min apart |
| R3 (major) | hotter water and more cycles | partly fixed, rest is a disclosed bet | Start cost 0.7 kWh + 0.3 kWh per 10 K below 0 °C (was 0.3 flat). The park doubles as a backup thermostat. | starts 2.0 against 2.1 a day (was 2.6). Below -10 °C 1.4-1.6 against 0.9-1.2 (was 2.1-2.3). Outlet still about 1 K warmer: that is the part-load COP bet (`flat_load`: energy -0.5 %) |
| R4 (major) | comfort gain only from less overshoot, cold side worse | real | Cold-side hinge: +0.5 kWh per K-h below aim - 0.5 K. Backup park: if the controller goes silent, the firmware holds the slab for target - 1.5 K. | minutes below 21 °C 16,633 against 19,356 for the baseline (was +40 %). K-h below -0.5 K 141-178 against 204-230. Seed 2's minimum went from 18.8 to 19.8 °C (a link outage during a -5 kW airing) |
| R5 (minor) | cold_share on nominal seeds 3-4 | real, disclosed | none | 43 % of the seed-0 saving is below -4 °C (section 7) |
| R6 (minor) | weekly mean-air breaks; mild-week gains are not metered | real, disclosed | none (weeks are diagnostics) | section 6 leads with season and metered numbers |
| R7 (minor) | writes at 20-24 °C; stop 0.1 K past the threshold | real | All writes clamped to 25-39 °C. Stop at t_ctrl - 2.6 K. With a cool loop the firmware's 3-min rule stops it once the water warms. | `setpoint_range` flag gone; 0 minutes outside 25-39 °C |
| R8 (minor) | forces heating_enabled back on | real | heating off → no writes at all | covered in the self-check |
| R9 (minor) | stale defrost fields during outages | simulator concern, already guarded | none | `long_outage` seed 0: 5754 against 6209 kWh |

Score cost of the fixes: adjusted -9.85 → -9.35 %, energy -4.82 → -3.57 %. Comfort (-481 →
-511 K-h) and starts (2.6 → 2.0 a day) both improved. The energy loss comes from the higher
start cost, the cold-side hinge (more heat on cold nights) and the write and anti-reversal
limits, each worth 0.2-0.4 % of energy.

A side finding while testing: `sp_min = 20` (stops written below 25 °C, as before the review)
with the other fixes produced a short-cycling collapse on season seed 1: 7.8 starts a day and
a 15.9 °C minimum. The cause was firmware self-starts around low stop setpoints, which then
used up the 7-start budget. The 25 °C floor removes that path.

## 9. Review fixes, round 2

Second adversarial review (seeds 3-4, `.local/lab-results/controllers/econ_mpc/review/r2/`).
Fix runs: `.local/lab-results/controllers/econ_mpc/fix3/`. Tuning used seeds 0-2 only.

| id | finding | verdict | fix | result |
|---|---|---|---|---|
| R2-1 (major) | a rejected restart_delta write blocks every start (retried every minute, eats the 45-write budget; jan_cold: mean 20.96 °C) | real | restart_delta write with backoff (10 min, 1 h, 6 h, then once a day), only while idle, never in DHW/defrost/off, never after the soft write budget. Success resets the backoff. Start setpoint and park keep working from the observed register. | wrapper that drops every restart_delta write (seed 0): jan_cold 22.05 °C, 47.9 K-h, 23.1 writes/day; nov_mixed 22.04 °C, 41.8 K-h. Same as the unwrapped controller (22.04 / 48.1, 22.03 / 42.9) and better than the baseline (68.1 / 57.3 K-h) |
| R2-2 (major) | hotter water and more cycles in cold months; energy gain bets on the part-load curve | partly real; tested, no change adopted | Tested on seeds 0-2: cold start cost 0.3 → 0.6 / 1.0 kWh per 10 K; part-load curvature 0.035 → 0.02 / 0.01; extra 4.5 kW level; min_run 90. | None moves outlet (31.0-31.2 °C in every case) or starts (1.8-2.0/day) materially; each costs score (-9.35 → -9.07 / -8.88 / -8.84 / -8.48 / -9.07 %). See below. |
| R2-3 (minor) | over half the score is comfort | real, disclosed | none | unchanged |
| R2-4 (minor) | stale claims JSON | real | claims regenerated from this doc | - |
| R2-5 (minor) | mild weeks: higher metered electricity, mean-air breaks | real, disclosed | none (diagnostics) | weeks below |
| R2-6 (minor) | fixed COP/defrost priors | real, disclosed | `pl_k` parameter exposed (part-load curvature); default unchanged | flat_load seeds 0-1: -6.40 % at pl_k 0.035, -6.39 % at 0.02 |
| R2-7 (minor) | writes double the baseline | real, within limits | none | 20-22/day |
| R2-8 (minor) | restart_delta write not gated by DHW/defrost | real | gated (part of R2-1) | - |

**Why the hotter outlet stays.** On season seed 0 the heat-weighted outdoor temperature while
heating is -2.63 °C for econ_mpc against -3.62 °C for the baseline, with 2313 against 2711
running hours. The planner moves heat into warmer hours and delivers it in fewer hours at higher
output. That is where the +1 K outlet comes from, and the seasonal COP is still higher (3.03
against 2.91). It is not the part-load curve: with the curvature cut from 0.035 to 0.01 the
outlet stays at 31.0 °C. Cold-month starts on seed 0 are Jan 1.84 against 1.39 and Feb 2.29
against 1.82 a day; over Jan-Feb 46 of 121 econ starts (40 of 94 baseline) follow less than 30
min off, mostly hot-water restarts by the firmware. Over the season, starts are 1.9-2.1 against
2.0-2.1. A higher cold start cost (up to 1.0 kWh per 10 K) removes almost none of the extra
cold starts, so they are not marginal decisions; I left the cost at 0.3.

**Results after round 2** (code otherwise unchanged; the restart_delta gating does not change
nominal behaviour):

- Season, seeds 0-2: adjusted -9.35 % ± 0.72 (c=0.05 -9.32, c=0.3 -9.37), better. Energy
  -3.57 %, metered -3.41 %, comfort -511 K-h, mean |error| 0.40 against 0.51 K, mean air 22.02,
  starts 2.0 against 2.1, writes 20.3-22.3/day, outlet 31.0-31.2 against 30.0-30.3 °C, COP
  3.01-3.03 against 2.89-2.91. No flags.
- Robust, seeds 0-1: 20 of 20 better, no constraint breaks. Range -7.60 % (minute_only) to
  -10.39 % (partload_hi); low_flow -7.90, legacy_cop -8.17, raw_return -8.44, partload_lo -8.62.
  cold_share flagged on loss_minus20, low_flow and sun_minus30. flat_load (diagnostic): -6.40 %,
  energy -0.54 %.
- Weeks, seeds 0-2: all 7 better (dec_damp -2.6, jan_cold -4.7, feb_sunny_cold -8.2, nov_mixed
  -10.7, apr_mild_sunny -35.0, mar_shoulder -37.2, oct_mild -41.0 %); mean-air breaks in all 7;
  metered higher in apr (+2.3 %), mar (+3.2 %) and oct (+8.4 %).
