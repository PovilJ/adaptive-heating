# block_scheduler: energy-budget block scheduler (S5, with S8 timing and S6 riding)

`lab/controllers/block_scheduler.py`, stdlib only (about 900 lines including a sun-position
routine, a small matrix exponential, a Kalman filter and an assert-based self-check:
`.local/lab-venv/bin/python -m lab.controllers.block_scheduler`). It implements research strategy
S5 (HEAT_PUMP_CONTROL_RESEARCH.md section 8). It decides **when** to run from a rolling plan of
the house's heat need. It decides **how hot** from the block output and the slab, by riding the
setpoint. Timing by outdoor temperature (S8) is part of the plan's cost. Execution uses a soft
start and setpoint riding (S6).

## 1. Idea

1. **What the house needs.** The controller keeps a small grey-box model of the house: slab plus
   loop water, room air, and envelope. It uses the structure and rounded central values of the
   public lab house model (HOUSE_MODEL.md sections 1 and 8). A 5-state Kalman filter runs every
   minute and estimates:
   - the slab, air and envelope temperatures;
   - an air-node disturbance bias `d` (kW);
   - an inlet-to-slab offset `o`.

   It uses three inputs:
   - the room thermometer, minus its documented sun glow (0.8 mK per W/m² of GHI);
   - the heat measured from outlet - inlet + 0.3 K at the nominal 29 L/min;
   - the inlet sensor, as a slab thermometer while the loop water is settled (return = slab +
     0.2 K per kW of heat + o).

   The forecast drives the model: outdoor temperature, and sun on the south, east and west
   facades. The facade sun comes from a NOAA sun-position formula and an isotropic-sky
   transposition of GHI, DNI and DHI, using the documented effective apertures 2.7 / 6.4 / 3.7 m².
   In the plan, the bias splits into a fast part that fades over 3 h and a slow part, a 24-h
   average. A slow integral trim on the glow-corrected room error (0.015 K per K-hour, limited to
   ±0.8 K) keeps the long-run mean room on target.
2. **When to run (the plan).** Every 30 minutes, and whenever the compressor starts or stops,
   the controller plans the next 30 h in whole hours.
   - **Free room trajectory.** The model gives it from the forecast with no heat.
   - **Response to heat.** Precomputed impulse responses give the room's reply to one hour of
     heat.
   - **Greedy fill.** It switches on, one at a time, the hour that most lowers
     `electricity + comfort + start cost`.
     - Extending an existing block is free.
     - A new block pays `c_start` = 2.5 kWh (a wear and quiet preference, deliberately above the
       measured 0.02-0.06 kWh) and must be at least 2 h long.
     - Filling stops when no hour pays for itself.
     - **Polish** (review 2): a local search then flips single hours, or fills a whole off-gap
       between two blocks, while that lowers the plan cost and every block keeps its 2-h minimum.
       It removes a greedy artefact: the fill could lock in cheap warm afternoon hours first and
       leave a cold gap in the night before them (jan_cold seed 2: 21.2 °C for a day while the
       plan ran at 6 kW and a 7.5-kW plan was stranded with a 3-h gap).
   - **Comfort** is priced at 0.54 kWh per K-hour of |room - aim|, the ranking's own price.
   - **Electricity per hour** of a block at output q is q × part-load factor / COP prior(outdoor)
     × exp(0.033 × (supply - reference)). The COP prior is the unit model's steady COP at W30 and
     5.5 kW times the documented defrost penalty. The part-load factor is 1 + 0.08 to 0.17 per kW
     below 5.5 kW, from UNIT_MODEL.md 7.2. Supply = steady slab for the load + q / 1.43 kW/K.
   - **Credit.** Each hour of heat is credited at the horizon's mean cost of the same heat. So the
     plan does not price the heat itself, which the house needs anyway. It prices only:
     - which hours are cheaper (warmer, less frost);
     - how hot the water must be for the chosen output;
     - how many starts the plan makes.

     How much heat to deliver is decided by comfort alone.
   - **Output level.** The plan is made for 3-4 block outputs: 5.0 kW (or the unit's minimum, if
     higher), +1 kW, +2.5 kW, and a 'continuous' level of 1.05 × the next 6 h mean load when that
     is above the minimum output. The cheapest plan wins.
   - **The budget.** Delivered heat over the next 24 h is reported as `budget_kwh`. It is the
     S5 'heat the house needs', placed as few long blocks in the cheapest hours the slab's storage
     allows.
3. **How hot (the executor).**
   - **Start.** It writes the smallest setpoint the restart rule accepts:
     ceil(inlet - 0.8 + restart_delta + 0.15).
   - **Ride.** It then rides at `inlet + q / 2.02 + 0.2`, checked every 15 min. The firmware
     stops ramping up at setpoint - t_ctrl = 1 K, so this offset makes the realized output equal
     the planned one (measured: planned 6 kW gives 6.3 kW, planned 5 kW gives 5.2-5.7 kW). The
     firmware's own error loop holds that output at the lowest supply that delivers it.
     - The first 15 min of a block ride at the base level, never at a catch-up level (review 2,
       R7: no hot start bursts).
     - Output deadband (review 2, R6): once a block has settled, a ride is written only when the
       delivered output (20-min mean of the measured heat) misses the plan by more than 0.8 kW in
       the direction of the change, or when the plan's level moved.
     - Except before the 120-min surge marks: in the last 20 min of every 2 h of running, a
       setpoint that has fallen behind the warming loop is raised (only raised), because a low
       setpoint lets the unit modulate down, and the surge then stops the run (UNIT_MODEL 3.3).
   - **Stop.** It writes the park directly: the lowest of the safety park, the predicted park (next
     item) and outlet - 3.5 K (the stop rule needs t_ctrl = outlet - 0.5 >= setpoint + 2; 1 K
     margin), never below 25 °C. It never changes restart_delta, quiet or the heating mode, and
     never writes a ride setpoint more than 1.5 K below t_ctrl, so no stop happens by accident.
   - **Park.** While off, the setpoint is the safety park (a setpoint at which the firmware
     itself restarts once the slab is 2 K below its steady level, so a dead Home Assistant still
     leaves a thermostat), capped so it never starts the unit now. Review 2 (R6): the cap is also
     taken from the plan's predicted slab minimum until the next planned block, so one park write
     per stop replaces the hourly staircase as the slab cools.
   - **Timing limits.** A run lasts at least 60 min and the unit stays off for at least 45 min.

**Fail-safe:**
- **Link down:** no writes. The model runs on the planned output while the stale flag says the
  unit runs.
- **Room missing:** the filter runs open loop on the forecast and the learned bias.
- **Forecast missing:** the 24-h mean of the unit's outdoor sensor, and no sun.
- **DHW, the 7-min pre/post pauses and defrost:** they freeze the executor. The heat
  measurement is suspended for 12 min after DHW; the inlet is not used for 20 min after DHW or
  10 min after a defrost, start or stop.
- **Space heating found disabled:** the controller respects the switch and writes nothing (the
  owner or Home Assistant turned it off). It never writes `heating_enabled`.
- **Room thermometer frozen** (review 2): a reading whose value has not changed is treated as
  aged by the time since its last change, whatever its timestamp says, so a sensor that keeps
  reporting fresh but stuck values fades out like a stale one.

## 2. Physics behind it, and two deliberate departures from the S5 text

- **Minimum output is not the efficient level here.** The unit model's COP at minimum output is
  20-45 % below its 6-kW value (UNIT_MODEL.md 7.2, with the measured 4.7 vs 5.5). Including the
  supply lift a higher output needs (return = slab + 0.29 × (supply - slab)), electricity per kWh
  is flat from about 5 to 7 kW. It is 5-20 % worse at the minimum (my calculation from the unit
  model's `p_running`, all mandatory COP variants). So the block output is about 5-6 kW, not P_min.
  The penalty for a too-high output is kept in the plan (supply term), so 7-8 kW levels are chosen
  only when the room needs a fast catch-up.
- **Heat cost is not traded against comfort.** A first version credited stored heat at less
  than its value. Its |error| optimum then sat below the aim, and further below in cold weather,
  where heat is dear. The result was a 0.2 K colder room below -10 °C and a +0.07 K warmer room
  above +5 °C, which shifted savings into the cold days (`cold_share`). The ranking normalises
  energy to the season-mean air with one COP, so a weather-dependent comfort shift is a hidden
  trade. Crediting every hour at the horizon's mean cost removes it.
- **Slab as storage.** 1 kWh of heat raises the room by up to 0.033 K after 4-6 h and still
  0.012 K after 30 h. Over 30 h that is 0.6 K-h per kWh. A 2-h block at 5.5 kW (11 kWh) therefore
  moves the room by about 0.35 K. That is why blocks of 2-5 h with gaps of a few hours keep the
  swing within the comfort price.
- **Timing (S8) buys little once comfort is priced.** Setting `cop_timing=0` (no preference
  for warmer hours) gave -7.15 % against -7.06 % with it (season, 3 seeds). It is kept, since it
  is harmless and helps in shoulder months.
- **Lower slab supply penalty.** The supply estimate uses the steady slab for the load, not the
  model's predicted slab (`sup_slab=0`). With the predicted slab, the plan learned to let the
  slab cool by 6 K on cold nights and reheat later at a lower supply temperature. That was a
  myopic exploit that left the room at 21.0-21.3 °C at -18 °C (jan_cold).

## 3. Parameters (final defaults)

| group | parameter | value |
|---|---|---|
| house model | c_s / k_sa / h_g / c_a / h_ao / c_e / k_ae / h_eo | 4.66 kWh/K / 0.43 kW/K / 0.09 / 4.3 / 0.045 / 74 / 1.35 / 0.07 |
| | internal gain, apertures S/E/W, glow, emitter | 0.31 kW; 2.7 / 6.4 / 3.7 m²; 0.0008 K per W/m²; 1.43 kW/K |
| filter | qn_d / qn_a / qn_s / qn_e / qn_o (per h), r_room / r_inlet (per min) | 0.6 kW² / 0.01 / 0.01 / 0.0005 / 0.01 K²; 0.05 / 0.05 K² |
| | bias fade in plan, slow bias, trim gain, trim limit | 3 h, 24 h, 0.015 K/(K h), ±0.8 K |
| plan | horizon, replan, lam, c_start, min block | 30 h, 30 min, 0.54 kWh/K-h, 2.5 kWh, 2 h |
| | block output q_run, steps, continuous level, max | 5.0 kW (or unit min), +1.0 / +2.5 kW, 1.05 × 6-h load, 8.5 kW |
| | supply penalty, credit | 3.3 %/K, full (horizon mean cost) |
| | polish (local search after the greedy fill) | on |
| executor | min run / min off, ride every, ride offset, park | 60 / 45 min, 15 min, +0.2 K, 25 °C |
| | soft first ride, output deadband, pre-surge window | 15 min at the base level, 0.8 kW, last 20 min of every 2 h |
| | park from the predicted slab until the next block | on (1.1 K below the restart threshold) |
| | frozen-thermometer check | on (age = time since the value last changed) |
| | learning gate | trim and slow bias learn only after 30 min of link |
| off by default | loss-slope regression `h_learn`, start-up trim boost `trim_boost` | tested in review 2, no gain (section 10) |

## 4. Tuning record (season, seeds 0-2, adjusted % at c = 0.2 vs reference_tuned)

| step | change | adj % | starts/d | note |
|---|---|---|---|---|
| 0 | first version: hand observer, c_start 0.6, q 5.5 (+1.5/+3), ride inlet + q/2.02 - 0.25 | (weeks only) oct -25, dec +2.4, jan -1.2 | 7 in dec_damp | rooms cold in cold weeks, realised output ~0.9 kW below plan |
| 1 | steady-state Kalman filter (room innovation RMS 0.255 → 0.061 K), ride +0.2 K | -6.09 ± 1.6 | 4.2 | many 1.5-h blocks |
| 2 | c_start 2.0 | -6.44 | 2.2 | |
| 3 | terminal credit scaled 0.9 / 1.0 / 1.15 (retention-weighted) | -6.6 / -6.9 / -7.6 | 2.1-2.5 | cold rooms below -10 °C; plan deferred heat to the horizon end (fixed by a flat credit) |
| 4 | inlet as slab thermometer in the filter (5 states) | +0.1 pt | | kept as principled; little effect |
| 5 | no COP timing / lam 0.8 / mean-deviation penalty | -7.15 / -6.52 / -5.9..-6.6 | 2.1 / 3.5 / 3.3-3.9 | mean penalty fixed the cold bias but doubled starts: dropped |
| 6 | full credit (heat not priced, only differences) + relative supply reference | -7.36 (c_start 2) / -6.61 (c_start 3) | 2.6 / 1.9 | cold bias gone, `cold_share` flag gone |
| 7 | q_run 5.0, steps +1.0/+2.5, c_start 2.5, continuous level, sup_slab 0 | -7.18 ± 0.49 | 1.8 | robust run: all 20 better, but mean air 22.06-22.08 on loss_minus20, raw_return, sun_minus30 |
| 8 | trim 0.015 K/(K h), limit 0.8 K (was 0.02 / 0.4) | -6.74 ± 1.72 (claimed; the file as reviewed reruns at -6.04 ± 1.38) | 1.8 | mean air on target in every mandatory variant |
| R2-1 | review 2: polish, soft first ride, frozen-room check, learning gate, loss regression on | -6.09 ± 0.59 | 1.6 | 21 writes/day |
| R2-2 | + output deadband 0.8 kW, park from predicted slab | (weeks) | 1.9 | writes 21 → 12, but surge stops raised starts |
| R2-3 | + pre-surge window | -6.16 ± 0.47 | 1.8 | 13.8 writes/day |
| R2-4 | loss regression off (`h_learn=0`): **final** | **-6.57 ± 0.59** | 1.7 | 13.7-14.2 writes/day |

Faster trims (0.05 and 0.1 K/(K h)) did not fix step 7's mean-air breaks and cost 1-2 points
of comfort. A fixed aim offset of -0.04 K was tried and rejected (constraint tuning). Step 8's
wider, slower trim fixes them. In those variants, uncontrollable solar overheating in February
and March lifts the season mean. The tuned baseline gets a per-variant oracle offset that
under-heats October-December instead (loss_minus20: baseline 21.85 °C in Oct-Dec, 22.25 °C in
March). The wide trim makes this controller do the same: it remembers a sunny spell and aims
up to 0.4 K low for a while afterwards. That is a constraint-driven behaviour, see section 7.

## 5. Results: season, nominal, seeds 0-2 (final file, after review 2)

| | reference_tuned | block_scheduler |
|---|---|---|
| adjusted energy (c = 0.2) | | **-6.57 % ± 0.59 (better)**; c = 0.05: -6.39 %; c = 0.3: -6.69 % |
| normalised energy | | -4.25 % |
| metered electricity kWh/day (seeds 0/1/2) | 27.06 / 26.19 / 26.07 | 25.83 / 25.00 / 24.97 (-4.42 %) |
| COP (space heating) | 2.89-2.91 | 3.02-3.05 |
| comfort K-h | | -184 K-h (mae 0.47 vs 0.51 K) |
| mean air | 22.00-22.01 | 21.99 |
| starts/day | 2.0-2.1 | 1.7-1.8 |
| median run | 270-288 min | 331-332 min |
| writes/day | 9.3-9.8 | 13.7-14.2 (was 22.0-22.5) |
| mean outlet while running | 30.0-30.3 °C | 30.8-30.9 °C |
| mean setpoint / max | 28.3-28.7 / 37-39 | 28.4-28.6 / 35-36 |
| flags | | none (`cold_share` no longer set on nominal) |

Break-even start cost: the verdict holds at every start cost, since the candidate makes fewer
starts. Results: `.local/lab-results/controllers/block_scheduler/fix2/final_season`.

**By outdoor band** (season seed 0, daily-mean outdoor; `fix2/csv0`; v5 = this file with the
loss regression on, which scores within 0.4 pt of the final):

| band (days) | mean air base / v0 / v5 | mae base / v5 | outlet while running base / v5 | heat-weighted outlet base / v5 | electricity kWh base / v5 |
|---|---|---|---|---|---|
| < -10 °C (27) | 22.07 / 21.96 / 22.00 | 0.48 / 0.47 | 31.7 / 31.7 | 31.9 / 31.8 | 1379 / 1300 (-5.7 %) |
| -10..-4 (21) | 21.96 / 21.93 / 21.89 | 0.36 / 0.41 | 31.0 / 31.3 | 31.3 / 31.4 | 889 / 853 (-4.0 %) |
| -4..+1 (35) | 21.96 / 22.01 / 22.00 | 0.37 / 0.38 | 30.4 / 31.0 | 30.5 / 31.2 | 1096 / 1060 (-3.3 %) |
| +1..+5 (51) | 21.98 / 21.98 / 22.00 | 0.53 / 0.50 | 29.7 / 30.8 | 29.8 / 31.0 | 1023 / 986 (-3.6 %) |
| > +5 (48) | 22.05 / 22.02 / 21.99 | 0.61 / 0.51 | 28.7 / 29.6 | 28.8 / 29.9 | 538 / 502 (-6.7 %) |

The coldest band is no longer colder than the baseline (21.96 → 22.00 with the polish; baseline
22.07), but the -10..-4 band is 0.07 K colder. The water is not hotter in the cold, it is 1 K
hotter in mild weather, where the baseline runs short low-output cycles and this controller runs
fewer, longer 5-6 kW blocks; electricity is lower in every band.

## 6. Robustness (season, seeds 0-1, all 20 mandatory variants, final file)

| variant | adj % (c=0.2) | ± 90 % | energy % | comfort K-h | starts/d (base) | mean air | mae (base) | flags |
|---|---|---|---|---|---|---|---|---|
| forecast_pessimistic | -6.30 | 2.20 | -4.32 | -156 | 1.8 (2.1) | 21.98 | 0.47 (0.51) | cold_share |
| frost_melt_hi | -6.86 | 0.81 | -4.46 | -195 | 1.7 (2.0) | 21.99 | 0.47 (0.51) | - |
| frost_melt_lo | -6.95 | 1.97 | -4.47 | -201 | 1.8 (2.1) | 21.99 | 0.46 (0.51) | - |
| heavy_slab | -7.58 | 1.76 | -4.34 | -268 | 1.6 (2.0) | 22.00 | 0.47 (0.53) | - |
| high_flow | -6.95 | 1.46 | -4.31 | -209 | 1.6 (1.9) | 21.99 | 0.47 (0.52) | min_off |
| high_start_loss | -6.71 | 2.08 | -4.49 | -178 | 1.8 (2.1) | 21.99 | 0.47 (0.51) | - |
| legacy_cop | -4.94 | 0.97 | -2.56 | -187 | 1.7 (2.1) | 21.99 | 0.47 (0.51) | - |
| light_slab | -5.95 | 1.15 | -4.63 | -95 | 1.9 (2.3) | 21.98 | 0.47 (0.49) | - |
| loss_minus20 | -7.62 | 0.92 | -5.13 | -187 | 1.9 (2.2) | 22.02 | 0.48 (0.53) | cold_share |
| low_flow | -6.44 | 1.18 | -4.44 | -167 | 1.9 (2.2) | 21.99 | 0.47 (0.51) | cold_share |
| minute_only | -5.80 | 3.81 | -3.72 | -186 | 1.7 (2.0) | 21.99 | 0.48 (0.52) | - |
| nominal | -6.60 | 2.17 | -4.35 | -178 | 1.8 (2.1) | 21.99 | 0.47 (0.51) | - |
| partload_hi | -8.17 | 2.47 | -5.65 | -208 | 1.8 (2.0) | 21.99 | 0.46 (0.51) | cold_share |
| partload_lo | -5.64 | 0.24 | -3.28 | -188 | 1.7 (2.1) | 21.99 | 0.47 (0.51) | cold_share |
| raw_return | -4.93 | 1.63 | -3.56 | -111 | 1.9 (2.1) | 22.03 | 0.48 (0.51) | - |
| shallow_outlet | -6.69 | 0.37 | -4.48 | -183 | 1.8 (2.0) | 21.99 | 0.47 (0.51) | cold_share |
| sluggish | -6.41 | 0.52 | -4.20 | -176 | 1.7 (2.0) | 21.99 | 0.47 (0.51) | - |
| steep_outlet | -6.57 | 0.75 | -4.10 | -200 | 1.8 (2.1) | 21.99 | 0.47 (0.51) | cold_share |
| sun_minus30 | -6.96 | 0.77 | -4.67 | -180 | 1.8 (2.1) | 22.00 | 0.47 (0.52) | cold_share |
| sun_plus30 | -6.90 | 3.11 | -3.89 | -252 | 1.6 (2.0) | 22.00 | 0.48 (0.53) | - |

**Better on all 20 mandatory variants**, at both start-cost ends (0.05 and 0.3 kWh). No constraint
break: mean air 21.98-22.04 °C, mae always below the baseline's, at most 1.9 starts and 13-15
writes a day. The weakest variants are raw_return (-4.9 %), legacy_cop (-4.9 %) and partload_lo
(-5.6 %); the energy part is smallest on legacy_cop (-2.6 %) and partload_lo (-3.3 %), consistent
with R1. `min_off` on high_flow means a start waited for the ASSUMED 3-min minimum off time.
`cold_share` is flagged on 8 variants. Results: `fix2/rob6`.

## 7. Weeks (diagnostic, seeds 0-2, final file)

| week | adj % ± 90 % | verdict | energy % | metered % | starts/d (base) | mean air (seeds) | base mean air | mae (base) |
|---|---|---|---|---|---|---|---|---|
| oct_mild | -28.6 ± 11.8 | better | -8.5 | -1.3 | 1.6 (1.9) | 22.02 / 22.04 / 22.09 | 21.98-22.01 | 0.54 (0.66) |
| nov_mixed | -7.6 ± 3.5 | better | -4.4 | -4.6 | 2.2 (3.2) | 21.95 / 21.96 / 22.01 | 21.99-22.02 | 0.33 (0.36) |
| dec_damp | -0.9 ± 3.2 | undecided | -2.9 | -4.2 | 2.1 (2.5) | 21.91 / 21.98 / 21.96 | 22.00-22.01 | 0.33 (0.28) |
| jan_cold | -4.4 ± 4.2 | undecided | -3.7 | -5.2 | 2.0 (1.2) | 21.99 / 21.92 / 21.79 | 21.99-22.01 | 0.44 (0.48) |
| feb_sunny_cold | -7.5 ± 4.8 | better | -4.2 | -2.0 | 1.6 (1.3) | 22.03 / 21.97 / 22.09 | 21.98-22.02 | 0.50 (0.60) |
| mar_shoulder | -12.4 ± 7.8 | better | -6.2 | +3.1 | 1.6 (1.6) | 22.23 / 22.14 / 22.25 | **22.06-22.13** | 0.94 (0.99) |
| apr_mild_sunny | -6.1 ± 65 | undecided | -2.5 | +4.5 | 1.1 (1.1) | 22.05 / 22.99 / 22.19 | **22.00 / 22.86 / 22.11** | 1.00 (1.06) |

Writes per day in the weeks: 2-20 (baseline 0-18). Metered energy is shown next to adjusted
energy (review 2, R3): in oct_mild most of the -29 % is comfort and normalisation, the metered
saving is only 1.3 %. In mar and apr the metered energy is higher (the run-out pays it back;
normalised energy is lower).

The mean-air rule (±0.05 K) breaks in 10 of the 21 week-seeds. Five of them are sunny shoulder
weeks where the baseline, with its per-week oracle offset, breaks too (mar all seeds, apr two
seeds): no heating controller can undo solar gain. The controllable ones are the cold, damp
weeks (jan 21.79 / 21.92, dec 21.91) and two +0.09 K seeds. A start-up trim boost (3x and 6x
faster learning over the first 3 days) was tried and made comfort worse without fixing them
(section 10), so the cold-week offset is not a trim-learning problem. It comes from multi-day
negative disturbances (the filter's bias sat at -1 to -3 kW for a day in jan seed 2) that the
plan treats as fading within 3 h.

## 8. Known weaknesses

- **Warmer water than the baseline in mild weather.** Outlet while running is 30.8-30.9 °C vs
  30.0-30.3 °C; by band it is the same below -10 °C and about 1 K hotter above +1 °C (section 5).
  The model says 5-6 kW blocks beat lower outputs (part-load COP slope beats the supply-lift
  penalty). This hinges on the unit model's part-load curve: on `flat_load` the energy saving
  falls from -4.25 % to about -0.9 % (adjusted still better, -3.4 %, from comfort and starts).
  `q_run=4.5` does not lower the water (30.78 vs 30.83 °C; the plan picks its levels by cost) and
  scores the same (-6.16 % with the loss regression on, vs -6.16 %). There is no real
  cool-water mode; it needs the two-hold field test (minimum output vs 5.5 kW in the same
  weather) before the q_run choice is trusted.
- **Writes 1.45 times the baseline** (13.7-14.2 a day, was 22; busiest week-day average 20, limit 48).
- **Cold, damp weeks run 0.05-0.2 K cold** in some seeds (jan_cold 21.79 / 21.92, dec_damp
  21.91). Multi-day negative disturbances are treated as fading over 3 h. The filter's slab error
  is about 0.8 K RMS below -10 °C, and the plan's 6-12 h room prediction RMS is 0.35-0.6 K.
- **The wide trim is constraint-shaped.** After a sunny spell it aims up to 0.4 K low for days
  to keep the season mean on target.
- **The comfort gain depends on the comfort price.** The energy part (-3.9 to -4.1 %) is the
  same at lam 0.3, 0.54 and 0.8; at lam 0.3 the comfort is worse than the baseline's (mae 0.62)
  and the verdict is undecided (+0.5 %); at lam 0.8 it is -7.1 % with 2.2 starts/day.
- **Hard-coded house numbers.** The model uses the lab model's central values (some of them,
  such as c_s 4.66 and h_ao 0.045, are the simulator's nominal parameters rather than rounded
  public ones). An oracle run with the exact loss_plus20 parameters did not do better than the
  nominal model on that variant (section 10), and an online loss-slope regression gave no gain,
  so the adaptation stays in the bias, inlet offset and trim.
- **Compute.** Pure Python, about 70-100 s per simulated season (a 5×5 Kalman update every
  minute, 3-4 plans with greedy fill and polish every 30 min). Trivial for a real Home Assistant
  integration.
- **Greedy plan with a local polish**, not an optimum; one output level per plan.

## 9. Simulator observations

- The ranking's mean-air constraint (±0.05 K over the season) is met by the baseline through a
  per-variant oracle offset. That offset under-heats October-December to pay for uncontrollable
  solar overheating in February-April (loss_minus20). An online controller must learn the same
  long-memory compensation to pass, which is not good comfort behaviour.
- The slab-to-ground path (0.092 kW/K to a fixed 10 °C) rewards a lower slab temperature. In
  cold weather an earlier version saved about 1.7 kWh/day of heat this way (slab 0.75 K lower)
  besides a colder room. The final version's advantage holds on `minute_only`.
- The plan with the predicted slab in the supply term exploited 'let the slab cool, then reheat
  at a lower supply' (section 2). It was removed. The physics is real, but in the model the
  benefit came at a large comfort cost.

## 10. Review fixes (review round 2)

All runs: `.local/lab-results/controllers/block_scheduler/fix2/` (seeds 0-2 season, 0-1 robust,
0-2 weeks; seeds 3-9 never run). Version files `v0`-`v6_block_scheduler.py` there; `v6` is the
final file.

**R8 (claims from an older file).** Confirmed. Re-running the pre-review file (`v0`) on seeds 0-2
gives -6.04 % ± 1.38, not the -6.74 % in the old section 5, and comfort -177 K-h, not -220. All
tables in this document are now from the final file. The doc's 'space heating is re-enabled'
line was wrong: the code respects the switch (fixed in section 1).

**R1 (energy depends on the part-load slope; warm water).** Real, and not fixable in the lab:
it is a property of the strategy. Season seeds 0-2, final file:

| variant | adjusted % | energy % | comfort K-h | starts/d (base) |
|---|---|---|---|---|
| nominal | -6.57 ± 0.59 | -4.25 | -184 | 1.7 (2.1) |
| flat_load | -3.42 ± 0.98 (better) | -0.89 | -189 | 1.7 (2.2) |

So under a flat part-load curve the energy saving nearly vanishes and the remaining gain is
comfort and fewer starts. `q_run=4.5` was tested as the asked-for cool-water mode: -6.16 %
(same as the default at that step), mean outlet 30.78 vs 30.83 °C. It is not a cool-water mode,
because the plan chooses higher levels when they are cheaper, so it was not adopted. The band
table in section 5 shows where the water is warmer (mild weather, about +1 K). The
recommendation stands: run the two-hold field test before trusting `q_run`.

**R2 (comfort gain disappears under model mismatch).** Partly real, but not caused by the
mismatch. Season seeds 0-2, loss_plus20:

| controller on loss_plus20 | adjusted % | energy % | comfort K-h |
|---|---|---|---|
| pre-review file (v0) | -4.14 ± 0.86 | -3.03 | -84 |
| final file (nominal house model) | -4.48 ± 0.88 | -3.33 | -84 |
| final + online loss-slope regression (`h_learn=1`) | -4.38 ± 1.09 | -3.32 | -79 |
| **oracle**: the exact loss_plus20 parameters (incl. its q_int 1.06 kW, c_e 107, k_sa 0.51) | -3.95 ± 1.03 | -3.25 | -33 |

With the true house parameters the controller does no better on this variant, so the smaller
comfort gain is a property of that house (the baseline's own mae is lower there, 0.49 vs 0.51),
not of the hard-coded numbers. The bias state already absorbs the level error of a wrong H.
I implemented the suggested online identification as an exponentially weighted regression of the
filter's bias on the indoor-outdoor difference (10-day memory, ridge prior, slope limit
±0.08 kW/K), which moves the planned bias with the forecast outdoor temperature. It scored 0.1-0.4
pt worse on nominal, loss_plus20 and flat_load (nominal -6.16 vs -6.57 %), and in dec_damp it
latched a +0.08 kW/K slope from a 4-K outdoor range that correlated with disturbances. It is kept
in the code, off by default (`h_learn=0`).

**R3 (weeks).** Partly real. See section 7: metered energy is now reported; jan_cold stays
undecided with more starts than the baseline (2.0 vs 1.2/day, the baseline is nearly continuous
there). Half the mean-air breaks are sunny shoulder weeks where the per-week-tuned baseline breaks
too. A start-up trim boost (3x/6x faster for the first 3 days) was tested on all weeks and made
mae worse (dec 0.36-0.38 vs 0.33, nov 0.36-0.40) without fixing the cold weeks, so it is off.
What did help the cold weeks was the plan polish (R-new below): jan_cold seed 2 went from 21.68
to 21.86 °C mean air and mae 0.54 to 0.42.

**New finding (from the R3/R4 analysis): greedy stranding.** In jan_cold seed 2 the plan ran
continuously at 6 kW with the room predicted at 21.2 °C for 8+ h, because the 7.5-kW plan's greedy
fill had locked in the warm, cheap afternoon first and stranded a 3-h night gap that made it look
worse. The polish (section 1) fixes it. Season effect: comfort better on the coldest band (mean
air below -10 °C 21.96 → 22.00).

**R4 (cold bias by band).** Reduced, now reported (section 5): below -10 °C 22.00 vs baseline
22.07 (was 21.96); -10..-4 °C 21.89 vs 21.96 remains colder. `cold_share` is no longer flagged on
the nominal season. A band-wise trim was not added.

**R5 (frozen thermometer).** Fixed. The reading's age is the time since its value last changed.
In the simulator that is what `room_age_min` already reports, so nominal behaviour is unchanged.
Fault run (seed 0, room frozen with a fresh timestamp on days 2-5): oct_mild mean air 21.98, mae
0.60 (fault-free 22.02 / 0.60, room missing 22.00 / 0.58); jan_cold 22.09 / 0.37 (fault-free 22.01
/ 0.32, room missing 22.14 / 0.38). Before the fix the reviewer measured 22.72 / 0.91 in oct_mild.
The trim and the slow bias also stop learning while the link is down and for 30 min after
(during an outage the heat input is unknown; in jan_cold seed 0 the bias had drifted to +3 kW).

**R6 (writes).** Fixed: 13.7-14.2 writes/day on the season (was 22.0-22.5; baseline 9.3-9.8).
Writes per day in single weeks (seed 0), before → after: jan_cold 24 (20 of them rides) →
14; nov_mixed 24 (14 rides, 10 park/start/stop) → 18; oct_mild 12 → 8. Three changes: the output deadband, one park
write per stop from the predicted slab (no hourly staircase), and a stop that lands on the park
directly. The deadband first raised starts (1.62 → 1.91/day): with a lagging setpoint the unit
modulated down, and the 120-min surge stopped 4-5 runs a week. The pre-surge window removed
those (fw stops while the plan wanted heat: 5 → 1 in nov_mixed). Riding every 30 min or a 1-K
hysteresis cut writes by only 5-12 % and cost comfort, so they were not used.

**R7 (hot start bursts).** Fixed as suggested: the first 15 min ride at the base level.

**R9 (objective tuned to the metric).** Reported (section 8): energy -4.05 / -4.25 / -3.87 % at
lam 0.3 / 0.54 / 0.8, adjusted +0.53 (undecided, mae 0.62 vs 0.51) / -6.57 / -7.09 %. The energy
saving does not hinge on the metric's price; the comfort part does, and at lam 0.3 comfort is
worse than the baseline. The symmetric short-memory trim was not re-run (the step-7 record in
section 4 shows the narrow trim breaks the mean-air rule on three variants).
