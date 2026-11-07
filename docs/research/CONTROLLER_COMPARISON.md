# Controller comparison: ten ways to run the Versati

This document records the results of the controller race (2026-11-07). The race builds on:

- the research sweep, in `HEAT_PUMP_CONTROL_RESEARCH.md`;
- the lab simulator, in `lab/` and `docs/research/lab/`.

Nine controllers were written independently, each from one research strategy. None of their authors saw the production code. A tenth agent ported the production controller (0.5.3), and a final agent combined the mechanisms that proved real into `hybrid`. Each controller was then reviewed adversarially and fixed. Finally, all of them were re-ranked on held-out draws that no author had touched.

Every number below is from the simulator. The simulator reproduces the metered electricity within about 2 % in normal weather. It reads about 11 % high in the coldest recorded week, and it under-counts starts by about 15 %. See `lab/SIMULATOR.md`.

## 1. Result (season Oct–Apr, held-out seeds 5–9, against `reference_tuned`)

All controllers are compared with `reference_tuned`, a plain room-holding PI controller aimed exactly at target.

- **Adjusted**: normalised electricity plus comfort, where comfort is priced at 0.54 kWh per K·h of |air − target|. Lower is better.
- **Metered**: the raw meter difference.

| controller | strategy | adjusted | metered elec. | mean air °C | mean abs err K | starts/d | median run | mean outlet °C | writes/d | robust variants (seeds 5–6) |
|---|---|---|---|---|---|---|---|---|---|---|
| **hybrid** | slab thermostat, controller-owned start/ride/stop, sun + daily-pattern anticipation | **−10.6 %** | **−5.1 %** | 22.00 | 0.41 | 2.0 | ~300 min | 30.8 | 19 | 20/20 better |
| pmin_duty | duty-cycle on estimated slab temperature | −10.2 % | −5.1 % | 21.99 | 0.41 | 2.1 | ~270 | 30.8 | 19 | 20/20 |
| econ_mpc | online grey-box model + 36 h economic plan | −9.4 % | −3.4 % | 22.03 | 0.40 | 2.0 | ~290 | 31.1 | 21 | 20/20 (mean air 22.05–22.06 on two) |
| setpoint_rider | sigma-delta heat balance + setpoint riding | −7.6 % | −3.8 % | 21.99 | 0.44 | 2.1 | ~320 | 30.7 | 10 | 20/20 |
| room_contact | room thermostat with cool weather-curve water | −7.4 % | −3.2 % | 21.99 | 0.43 | 2.4 | ~225 | 31.1 | 10 | 20/20 |
| block_scheduler | daily heat budget in long blocks | −7.1 % | −4.4 % | 21.99 | 0.47 | 1.7 | ~330 | 30.8 | 14 | 20/20 (one mean-air 22.06) |
| degree_minutes | NIBE-style degree-minute integrator | −6.8 % | −3.2 % | 21.99 | 0.45 | 2.1 | ~265 | 31.0 | 15 | 20/20 (one mean-air 22.07) |
| wc_low | weather curve + sun anticipation + slow room trim | −6.7 % | −1.9 % | 21.99 | 0.43 | 1.8 | ~335 | 30.7 | 10 | 20/20 |
| self_learning_curve | self-tuning weather curve | −5.0 % | −1.5 % | 22.01 | 0.46 | 1.8 | ~330 | 30.5 | 8 | 19/20 |
| reference_tuned | baseline | 0 | 0 | 22.00 | 0.52 | 2.0 | ~280 | 30.1 | 10 | — |
| **current_port** (production 0.5.3) | 36 h setpoint plan + safety rules | +0.4 % (undecided) | **+1.8 %** | **22.33** | 0.53 | **2.6** | **~180** | **32.3** | 15 | 0/20 better, 4 worse; mean air broken on all 20 |

### Same weeks, metered electricity, held-out seeds

| week | current_port | hybrid | wc_low |
|---|---|---|---|
| oct_mild | **+43 %** (room 22.6) | −0.6 % (22.1) | +5.0 % (22.1) |
| nov_mixed | +7 % (22.3) | −5.6 % (22.0) | −1.1 % |
| dec_damp | +6 % | −3.2 % | −0.3 % |
| jan_cold | −2.6 % | −3.3 % | −0.3 % |
| feb_sunny_cold | +9 % (22.3) | −2.8 % | +1.1 % |
| mar_shoulder | **+59 %** (room 22.9) | −0.4 % (22.2) | +6.6 % |
| apr_mild_sunny | **+86 %** (room 23.1) | −10 % (22.2) | −9.3 % |

Against the production port over the season, the hybrid uses about **6–7 % less metered electricity** while holding the room 0.3 K closer to target. In mild, sunny weeks the gap is 40–90 %. The port overheats exactly there.

The port's fidelity was checked: an AST comparison of `mpc.py` and `learn.py` matched the production code. Replaying the recorded period gives 11.9 against 11.8 kWh/day recorded. Its mean outlet temperature is 32.0 °C in the replay against 30.7 °C recorded, so the port may run slightly hotter than production.

## 2. What actually produces the gain (hybrid ablation, season seeds 0–2)

| removed mechanism | adjusted | lost |
|---|---|---|
| (full hybrid) | −10.5 % | — |
| run at the unit's floor output instead of ~6.5 kW | −6.7 % | 3.8 points, nearly all energy |
| let the firmware cycle (no controller-owned kick/ride/stop) | −8.1 % | 2.4 points, energy |
| no forecast sun **and** no learned daily pattern | −4.9 % | 5.7 points, mostly comfort |
| no forecast at all | −7.3 % | 3.2 |
| no room P term | −8.0 % | 2.5, comfort |
| no warm-hour preference (forecast timing) | −10.2 % | 0.3 |
| duty band 0.8 K / 2.0 K (2.6 / 1.8 starts a day) | −10.4 / −9.8 % | starts are not a lever |
| model-based planning, learned curve, 24 h sun term | no gain | dropped |

About 45 % of the gain is energy, coming from the output level and from the controller owning the stop. Another 45 % is comfort, from anticipating sun, the daily pattern and the room. The remaining 10 % is small terms.

## 3. Answers to the questions behind this work

**"We use too much high-temperature water."** Partly true. The production port runs 32.3 °C mean outlet against 30.1–31 °C for the others, which is worth about 6–7 % of COP. Its bigger loss is overheating the house in mild and sunny weather, with the room at 22.3 °C on average and up to 23 °C in spring weeks.

The lab does *not* support "colder is always better" for this unit. Its measured COP at minimum output is poor: at 0 °C outdoor it is 3.06 at 3.6 kW against 3.81 at 6 kW (UNIT_MODEL §7.2, fitted on 33 k steady minutes). So the best controllers run about 0.7 K *warmer* water than the baseline, at mid output, for fewer hours.

**"We do a lot of on/off cycles."** True relative to the others: the port makes 2.6 starts a day with runs of about 3 h, against 2.0 starts and runs of about 5 h for the best controllers. But a start itself costs only 0.02–0.04 kWh (measured). Cycling is a symptom. The cost is in what surrounds it: overheating, firmware stops at awkward moments, and (per the research, not measurable in this lab) the hot burst at each forced start.

**"Maybe our code foundation is bad — too many side scenarios, or too few?"** The 36 h coordinate-descent planner with layered safety rules does no better than a ~90-line PI baseline (`reference_tuned` + `reference`) in this lab. Its own guard rules (the comfort floor, Guard +1 K, night minimum) push the room warm.

The winner is simpler: a slab thermostat read from the water sensors, about 370 lines. The ablation shows model-based planning added nothing over that.

## 4. How confident are we?

Solid, survives every variant and the held-out draws:

- Holding the room on target instead of 0.3 K warm.
- Not overheating mild and sunny weeks.
- Anticipating sun from the forecast.
- Learning the daily pattern.
- Fewer, longer runs.

Rests on one fitted curve: the energy half of the hybrid's gain, about 3–4 points, depends on the part-load COP surface. If COP were flat with output (the `flat_load` diagnostic), the hybrid's energy gain drops from −5.3 % to −1.4 %. The adjusted score stays better (−6.9 %).

Cannot be measured in this lab:

- **Soft start (S6).** The simulated start burst is fixed at about 7.3 kW for 10 minutes, whatever the setpoint gap.
- **Quiet mode and restart_delta other than 4–5 K.** Not observed in the data.

Scoring caveats:

- Comfort is about half of every score, at the baseline's own price of 0.54 kWh per K·h.
- Weekly mean-air constraints are hard for any causal controller, because the baseline is re-aimed per week with hindsight.

## 5. Recommendation

1. **Build the next production controller on `hybrid`, not on the current planner.**
   - Keep from it: the slab-temperature thermostat (start below target − 1.4 K, stop above + 1.4 K, 60 min minimum on, 45 min minimum off); the smallest setpoint that triggers a start; riding the setpoint in the firmware dead band; one stop write; and anticipation of forecast sun, the learned daily pattern and the room.
   - Drop: the 36 h planner and the guard layers.
   - The integration must persist the controller state across restarts and alert on a stale room sensor.
2. **Before relying on the energy half, run a two-hold field test.** Over 4–6 similar mild days, alternate whole runs held at minimum output and at about 6.5 kW (the hybrid's `q_run`), and compare metered COP. If COP turns out flat, set `q_run = 0`. The comfort half of the gain stays either way.
3. **A cheap first step if you want one now:** `wc_low` is a plain curve with no firmware tricks. It gives about −2 % electricity, a room 0.1 K steadier, and no mild-weather overheating. It mostly fixes the overheating loss.

## 6. Files

- Controllers: `lab/controllers/<name>.py`. Design docs, tuning records and review fixes: `docs/research/lab/controllers/<name>.md`.
- To reproduce the held-out ranking:

  ```bash
  .local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,current_port,hybrid,pmin_duty,econ_mpc,setpoint_rider,room_contact,degree_minutes,block_scheduler,wc_low,self_learning_curve -s season --seeds 5-9
  ```

  Add `--robust` for the 20 variants, or use `-s weeks`. Results go to `.local/lab-results/heldout/` (private).
