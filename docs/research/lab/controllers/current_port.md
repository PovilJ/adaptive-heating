# current_port: the production controller (adaptive_heating 0.5.3) in the lab

`lab/controllers/current_port.py`, stdlib only. This is not a new strategy. It is a port of the
Home Assistant integration that runs in the house today (`custom_components/adaptive_heating/`,
version 0.5.3), so that the new lab strategies can be compared with what actually runs. The
decision logic was ported as written. Nothing was tuned to the lab metrics. Every place where
the lab cannot reproduce the integration exactly is listed in section 4.

## 1. Idea (what the production controller does)

Every 30 minutes (every 2 minutes while paused), the coordinator does the following:

1. **Reads** the room (averaged over the last 30 minutes of sensor changes), the unit's outdoor
   sensor, the water setpoint, inlet and outlet, the operating state and the electricity meter. It
   **pauses** (writes nothing) when the room is older than 120 min, the link is down, the unit is
   on hot water or defrosting, or space heating is off.
2. **Estimates the hidden state** (`mpc.Estimate`). A three-store house model (slab, building,
   sun "glow") is advanced with the heat that went in. Over a whole interval that heat is the
   electricity meter x a Carnot COP; otherwise it comes from the emitter model (setpoint above the
   slab x duty). The model is then corrected toward the measured room:
   - while idle, a warm surprise is treated as sun glow and the slab may only cool;
   - while heating, the slab moves at most 0.6 K/h;
   - a slow drift term (±0.05 K/h) absorbs persistent error.
3. **Plans** (`mpc.plan`). It runs a coordinate search over 13 blocks of water setpoints
   (25-40 °C, whole degrees) covering 36 h at half-hour steps, and picks the cheapest schedule.
   - Cost: electricity (heat / COP, x1.15 below the minimum output, 30 % cheaper under full sun)
     + 0.15 kWh per start + 60 per K² h below the comfort floor + 4 per K h above target + 0.3 K.
   - Constraints:
     - an idle compressor starts only if the setpoint clears slab + 2.8 + restart gap;
     - a run lasts at least one hour;
     - each block is capped at the weather curve + 5 K;
     - the setpoint moves within the rise and fall limits.
   - Seven start points: the minimum water, a "hold" level, flat levels 27/29/31/33 °C and the
     previous plan.
4. **Applies safety rules** on the first block:
   - **Guard:** if the room is more than 0.2 K under the floor *and* under the model's
     prediction, add +1 K per cycle (up to 6).
   - **start_level:** if the plan wants to start an idle compressor, lift the setpoint to
     ceil(outlet + restart gap).
   - **keep_running:** if the compressor runs and heat is wanted, hold the setpoint at least
     ceil(inlet + 1.5).
   - **One-hour hold:** a run that started under an hour ago is never lowered.
   - **too_warm:** if the room is more than 0.2 K over target + 0.3, write the minimum water
     (25 °C) at once. This bypasses the fall limit.
   - After hot water (30 min) the loop temperatures are ignored for the lifts.
5. **Limits and writes.** The result is clamped to 25-40 °C and moves at most rise 6 / fall 10 K
   per hour. It is written only on a due cycle (≥ 29 min since the last one) and only if it
   differs from the current setpoint. The unit's own firmware does all the starting and stopping.
6. **Learns** every night at 03:00 local (`learn.refit`):
   - The device values are measured directly: the restart gap (the 2nd-smallest of the last 20
     observed start gaps), the minimum output (10th percentile of full-interval heat), and the
     idle outlet above the slab.
   - Heat loss and the east/south/west sun gains are refitted by Nelder-Mead on up to 28 days of
     half-hour log rows. The refit is adopted only if it forecasts the held-out last 48 h at least
     3 % better.

When the forecast is missing, the heating-curve fallback (`engine.decide`) is used instead:
22 + 3 + 0.45 x (22 - outdoor), plus 2 K per K of room error and a short-horizon cold-forecast
lookahead.

## 2. Physics behind it (as the production code sees it)

- The planner's house model is a fit to the first house:
  - 0.151 K of slab per kWh;
  - slab-to-building exchange 0.64 h⁻¹;
  - loss 0.0065 h⁻¹ × building heat capacity, about 0.19 kW/K once converted;
  - emitter 0.8 kW per K of water above slab + 1.8 K.

  It thinks in half-hour *average* heat: a setpoint is "x kW", and below the minimum output the
  unit cycles at 15 % extra cost. It does not model the firmware's 2-K stop rule, the 120-min
  surge or the restart hysteresis beyond the start test.
- The comfort cost is **asymmetric**:
  - steep and quadratic below the floor (= target);
  - linear and 15x cheaper above target + 0.3.

  So the cheapest plan rides just above target and lets the sun push the room higher. In the lab
  this shows as a mean air about 0.3 K above target (section 5).
- The COP model (Carnot fraction 0.42, 8 K lift) makes cooler water cheaper per kWh. The
  start-cost term and the one-hour run rule push toward fewer, hotter pulses. In the lab the
  result is a bimodal setpoint: 25 °C (idle) about 45 % of the time, otherwise 31-38 °C.

## 3. Parameters (frozen; nothing tuned on the lab)

| parameter | value | source |
|---|---|---|
| target | the lab target (22.0) | Observation |
| minimum / maximum water | 25 / 40 °C | const.DEFAULTS |
| rise / fall limit | **6 / 10 K per hour** | the owner's live options, from the project's operating notes (code defaults are 4 / 2) |
| control interval / stale room | 30 / 120 min | const.DEFAULTS |
| curve slope / offset / allowance | 0.45 / 3 / +5 K | const.DEFAULTS, mpc.Comfort |
| comfort headroom / weights | 0.3 K; 60 per K² h below, 4 per K h above | mpc.Comfort |
| start cost / cycling loss / sun discount | 0.15 kWh / 15 % / 30 % | mpc.Comfort |
| night window | 20:00-09:00 | planner.DEFAULTS (quiet_start_hour, morning_hour); docs/PREDICTIVE.md records 22:00-07:00, night_minimum 21.5, curve_offset 0.5, stale 360 as the options applied with 0.4.0. They are exposed as parameters and evaluated in full (season, weeks, robust) as the "live options" configuration in section 8, R5 |
| **night_minimum** | **22 (= target, so no night setback)** | code default 20. See below |
| House | mpc.House defaults, then learned nightly | mpc.py / learn.py |
| learning | on (`learn=1`) | 0.5.x behaviour |
| PV nowcast | on (`use_pv=1`), PV from `pv_kw` | coordinator.sky |
| location | city-level coordinates, rounded (sun geometry only) | not private |

**The night_minimum choice.** The predictive planner's night comfort floor is
min(target, night_minimum). The code default for night_minimum is 20 °C. With 20, the planner
plans a night setback toward 21.4-21.6 °C. On the recorded scenario that is clearly *not* what
the real house did: the real night room sat at 22.3-22.4 °C, and with 20 the port delivered 6 %
less heat than the recorded controller. With night_minimum = target (22) the port matches the
recorded hourly setpoint pattern and the heat (table in section 5.1). I take 22 as the live
configuration and report the code default 20 as a sensitivity. Both are shown in 5.2.

## 4. Port simplifications and deviations (complete list)

1. **Plan search speed.** The production `mpc.plan` takes 1-2 s per call in the lab. The port
   runs exactly the same coordinate search, with three changes that do not change the result:
   - each trial is simulated from its block's start, reusing the cached prefix state;
   - a trial stops early once its partial cost can no longer win (every cost term is ≥ 0, and
     this is used only when all simulated waters are ≥ the minimum water);
   - results are cached per level vector.

   The `__main__` self-test checks that the plan levels and cost are identical to the verbatim
   search (`fast=0` runs the verbatim one). About 0.1 s CPU per plan; a season takes about
   15 CPU-minutes.
2. **Sensors mapped from the Observation:**
   - `mode` 'heat' = operating state HEAT;
   - 'idle' = OFF;
   - 'dhw' = hot water;
   - 'defrost' = the defrost entity is on (paused, floor not heating);
   - link down = every Versati entity unavailable (setpoint, outdoor, inlet/outlet, operating
     state, and the energy meter, which is assumed to drop with the link).

   The room report age stands in for HA's `last_reported`.
3. **Event-driven state** is rebuilt from the per-minute Observation:
   - the compressor duty between snapshots (per-minute integration instead of HA state-change
     events);
   - `run_started`;
   - the 30-min room average (the room "state changes" are changes of the 0.1-K value);
   - `hot_water_at`;
   - start gaps (the setpoint minus the *previous minute's* outlet at the first heating minute).
4. **Not ported:**
   - **The engine `Model` (old loss/gain learner).** Its output only matters inside
     `engine.decide` when a forecast exists, and then the predictive plan always replaces it.
   - **The cold-night planner (`planner.py`).** It is disabled by default (phase "disabled").
   - **AC assistance and tank disinfection.** The lab has no AC and no tank-target control.
   - **Solar preheat (`solar_preheat`).** Off by default.
   - **The legacy PyScript seeding.**
   - **The update/restart blocks.**
5. **Manual hold.** The `manual_hold` logic is ported: a setpoint change that we did not command,
   or a write not confirmed within 2 min, blocks control. It never fired in the diagnostic runs where it was counted (nov_mixed, dec_damp). One
   difference: production refuses to write when the current setpoint is outside 25-40 °C ("must
   be corrected manually"). The port emulates the owner's one manual correction by writing the
   clamped value once. This is counted; it never happened in the diagnostic runs.
6. **Learning state starts empty** at the controller's takeover:
   - no 28-day log;
   - default House;
   - default restart gap 5;
   - no PV scale.

   On the real install these persist. In a week scenario the first house refit can be adopted
   only after about 4-5 days. Over the season it runs nightly as in production. The refit runs
   instantly in the port; production runs it in the executor and applies it seconds later.
7. **Forecast:**
   - HA's hourly forecast is the lab's noisy forecast, re-read every 30 min (production caches it
     for 30 min).
   - The forecast `time` (end of the hour) is used as the row time. HA labels an hourly row by
     its start, so the port's forecast can sit up to 1 h later than production's (review R8c).
   - Cloud cover is the lab's `cloud`.
8. **Location.** The sun geometry uses rounded city-level coordinates instead of the HA config.
9. **Output entity.** Taken as min 20 °C, step 1 °C (Versati number).
10. **Restart hysteresis, quiet mode and the heating enable** are never written. Production
    writes only the setpoint.

## 5. Results

### 5.1 Does the port behave like the real controller? (`recorded`, 2026-10-09 .. 11-06)

`run.py --compare -c replay_recorded,current_port -s recorded`.

The recorded registers cover versions 0.4.4 → 0.5.3 and an owner target change from 22.5 to
22.0 in the first week. The lab target is 22.0 throughout. So expect resemblance, not identity.

| | replay_recorded (real setpoints) | current_port (night_minimum 22) | current_port (20, code default) |
|---|---|---|---|
| electricity / normalised, kWh/d | 11.78 / 10.80 | 11.92 / 11.04 | 11.14 / 10.78 |
| loop heat, kWh/d | 10.51 | 10.65 | 9.88 |
| starts/day | 3.2 | 2.5 | 2.5 |
| median run, min | 126 | 119 | 122 |
| runs < 60 min | 16 % | 7 % | 10 % |
| mean outlet while running | 30.7 °C | 32.0 °C | 31.2 °C |
| mean / max setpoint | 27.4 / 38 °C | 27.2 / 38 °C | 26.9 / 37 °C |
| share of time at 25 °C | 47 % | 66 % | 65 % |
| setpoint by 3 h (00..21 h) | 28.1 28.0 27.2 26.8 26.3 27.0 27.1 28.5 | 29.0 27.5 25.9 25.3 25.9 27.4 27.3 29.2 | 25.8 27.0 28.5 27.2 25.8 27.3 27.2 26.3 |
| air by 3 h | 22.38 22.33 22.25 22.36 22.83 22.83 22.59 22.36 | 22.22 22.24 22.14 22.13 22.50 22.51 22.31 22.15 | 21.73 21.56 21.57 21.87 22.45 22.46 22.23 21.94 |
| mean air / mae | 22.49 / 0.53 | 22.28 / 0.36 | 21.98 / 0.42 |
| writes/day | 16.6 | 12.4 | 12.7 |

The port with night_minimum 22 reproduces the recorded controller well:

- the same heat (within 1.3 %);
- the same daily shape (high setpoints in the evening and night, 25 °C around noon, sun-warmed
  afternoons);
- the same run lengths and maximum setpoint.

It differs in three ways:

- It holds 25 °C more often and pulses a bit hotter: outlet +1.3 K.
- It starts less often: 2.5 vs 3.2 a day. Part of the recorded starts came from 0.4.x versions
  with shorter runs, and the simulator under-predicts starts by 15-18 %.
- It writes less.

The recorded mean air is 0.2 K higher, mostly from the 22.5 °C target of the first week.

### 5.2 Season, nominal, seeds 0-2

`run.py --rank -c reference_tuned,current_port -s season --seeds 0-2`. The adjusted score is in
% of the baseline's electricity. Negative is better.

| | reference_tuned | current_port (night_minimum 22) | current_port (20, code default) |
|---|---|---|---|
| adjusted c = 0.05 / 0.2 / 0.3 | 0 | -0.72 / **-0.43 ± 1.74** / -0.23 %, **undecided** | -1.08 / -0.69 ± 1.00 / -0.42 %, undecided |
| normalised energy | 0 | -0.49 % | -2.57 % |
| metered electricity | 0 | +1.57 % | -3.01 % |
| comfort K-h (paired mean difference) | 0 | -30 | +121 |
| mean air (per seed) | 22.00-22.01 | **22.27 / 22.30 / 22.32 (breaks ±0.05)** | **21.91 / 21.95 / 21.97 (breaks)** |
| mean abs error | 0.49-0.53 | 0.49-0.54 | 0.53-0.55 |
| starts/day | 2.0-2.15 | 2.4-2.7 | 2.6-2.9 |
| median run | 270-288 min | 179-194 min | 149-179 min |
| runs < 60 min | 1-3 % | 6-8 % | 7-9 % |
| mean outlet while running | 30.0-30.3 °C | 32.2-32.4 °C | 31.5-31.6 °C |
| mean setpoint / max | 28.3-28.7 / 37-39 | 29.2-29.4 / 40 | 28.6-28.9 / 40 |
| writes/day | 9.3-9.8 | 15.2-16.0 | 14.7-15.8 |
| flags | | setpoint_range (40 °C), min_off (1 seed) | setpoint_range, min_off |

On seeds 0-2 the production controller is **level with the baseline on adjusted energy**
(undecided). This was the favourable side of the seeds: on season seeds 3-4 (run by the reviewer)
the same configuration is **worse**, +1.44 ± 0.92 % (+1.15 / +1.63 at c = 0.05 / 0.3), comfort
+134 K-h; pooled over seeds 0-4 it is +0.32 ± 1.20 %, undecided, comfort +36 K-h. The honest
season verdict for this configuration is **not better** (section 8, R1). It
**fails the mean-air constraint** in both configurations: +0.3 K warm without a night setback,
-0.07 K cold with the default setback. Compared with the baseline it uses hotter water (+2 K
outlet), about 25 % more starts and runs about 35 % shorter. Its normalised energy is about the
same: lower COP per kWh of heat is offset by less overheating and by the sun discount steering
heat into sunny hours.

Hourly profile (seed 0, air by 3 h, 00..21):

- baseline: 21.63 21.60 21.69 22.28 22.65 22.43 22.01 21.74;
- port: 22.03 22.03 22.05 22.50 22.76 22.55 22.20 22.04.

The port's room never goes below about 22.0 (the firm floor). All of its excess is
sun-driven daytime overshoot on top of that floor.

### 5.3 Robustness variants (season, seeds 0-1, 20 mandatory variants)

Complete (40 port seasons + 40 baseline seasons in
`.local/lab-results/controllers/current_port/robust/`, paired table in `robust_rank.txt`).
Adjusted % at c = 0.2 (c = 0.05 / 0.3), 90 % interval, n = 2:

| variant | adjusted % | verdict | energy % | metered % | comfort K-h | mean air (2 seeds) |
|---|---|---|---|---|---|---|
| nominal | -0.86 ± 4.47 (-1.18 / -0.65) | undecided | -0.46 | +1.51 | -73 | 22.27 / 22.30 |
| partload_lo | **+0.97 ± 0.55 (+0.68 / +1.17)** | **worse** | +0.69 | +2.76 | -10 | 22.27 / 22.32 |
| partload_hi | -2.41 ± 4.13 | undecided | -2.48 | -0.46 | -34 | 22.27 / 22.32 |
| legacy_cop | +0.68 ± 3.21 | undecided | +0.99 | +2.88 | -64 | 22.25 / 22.28 |
| high_start_loss | -0.52 ± 2.32 | undecided | -0.39 | +1.62 | -54 | 22.27 / 22.30 |
| sluggish | -0.61 ± 1.98 | undecided | -0.78 | +1.22 | -23 | 22.26 / 22.32 |
| raw_return | +0.60 ± 0.57 | undecided (c=0.05 interval just touches 0) | -0.63 | +1.48 | +70 | 22.29 / 22.34 |
| minute_only | +1.04 ± 1.84 | undecided | -0.73 | +0.44 | +144 | 22.14 / 22.21 |
| low_flow | +0.83 ± 1.30 | undecided | +1.30 | +3.33 | -106 | 22.30 / 22.33 |
| high_flow | -1.61 ± 3.58 | undecided | -1.61 | +0.16 | -19 | 22.21 / 22.28 |
| loss_minus20 | +0.19 ± 3.28 | undecided | -0.81 | +1.36 | +57 | 22.34 / 22.41 |
| steep_outlet | -0.51 ± 2.07 | undecided | -0.16 | +1.83 | -68 | 22.25 / 22.30 |
| shallow_outlet | -1.79 ± 3.63 | undecided | -1.45 | +0.52 | -71 | 22.27 / 22.29 |
| frost_melt_lo | -0.72 ± 4.84 | undecided | -0.80 | +1.21 | -28 | 22.27 / 22.30 |
| frost_melt_hi | -1.41 ± 3.46 | undecided | -1.02 | +1.01 | -75 | 22.27 / 22.30 |
| light_slab | -0.87 ± 2.82 | undecided | -0.94 | +0.87 | -24 | 22.26 / 22.29 |
| heavy_slab | -0.61 ± 1.07 | undecided | -0.63 | +1.54 | -34 | 22.27 / 22.33 |
| sun_plus30 | -0.97 ± 4.22 | undecided | -0.58 | +1.30 | -78 | 22.27 / 22.28 |
| sun_minus30 | +0.37 ± 1.94 | undecided | -0.16 | +2.00 | +14 | 22.32 / 22.37 |
| forecast_pessimistic | -0.35 ± 1.90 | undecided | -0.67 | +1.34 | -8 | 22.27 / 22.31 |

**Summary: 0 better, 19 undecided, 1 worse (partload_lo); every one of the 20 variants breaks the
mean-air constraint (22.14-22.41) on both seeds, and the `setpoint_range` flag (40 °C) appears in
all of them.** The port does not pass `--robust`. Metered electricity is higher than the baseline
in 19 of 20 variants. The apparent energy parity depends on the part-load slope: the port runs
markedly higher compressor power early in its runs (hotter, shorter pulses), which partload_lo
punishes.

### 5.4 Weeks (seeds 0-2)

`run.py --rank -c reference_tuned,current_port -s weeks --seeds 0-2` (night_minimum 22).

| week | adj % c=0.2 (± 90 %) | verdict | energy % | **metered %** | starts/d (base) | mean air (per seed) | mae (base) | constraint breaks |
|---|---|---|---|---|---|---|---|---|
| oct_mild | +10.7 ± 20.3 | undecided | +4.0 | **+42.3** | 2.6 (1.9) | 22.52 / 22.57 / 22.62 | 0.69 (0.66) | mean_air x3, mae 0.71 |
| nov_mixed | +6.8 ± 7.4 | undecided | +4.3 | +12.1 | 3.0 (3.2) | 22.14 / 22.23 / 22.27 | 0.39 (0.36) | mean_air x3, mae 0.42 |
| dec_damp | +5.2 ± 2.6 | **worse** | +1.0 | +3.0 | 3.1 (2.5) | 22.08 / 22.12 (+1 inside) | 0.36 (0.28) | mean_air x2, mae 0.34 / 0.35 / 0.39 |
| jan_cold | -1.5 ± 0.5 | better on 0-2 (does not reproduce on 3-4: -1.9 ± 11.4) | -1.9 | -1.0 | 1.8 (1.2) | 21.89 / 21.95 / 22.11 | 0.48 (0.48) | mean_air x3 |
| feb_sunny_cold | -1.9 ± 1.4 | better on 0-2 | +0.1 | +5.6 | 1.9 (1.3) | 22.11 / 22.24 (+1 inside) | 0.54 (0.60) | mean_air x2 |
| mar_shoulder | +18.3 ± 18.8 | undecided | +15.7 | **+70.7** | 1.7 (1.6) | 22.82 / 22.96 / 22.98 | 1.01 (0.99) | mean_air x3, mae 1.04 |
| apr_mild_sunny | +56.7 ± 63.8 | undecided | +13.8 | **+81.1** | 1.6 (1.1) | 22.84 / 23.23 / 23.36 | 1.23 (1.06) | mean_air x3, mae 1.34 / 1.41 |

Every week breaks at least one constraint, so no week counts as a pass, including the two whose
adjusted-energy interval is below zero. Metered electricity (what the owner pays) is far above
the normalised figure in the mild and sunny weeks: the extra heat goes into a warmer room and the
normalisation removes most of it, while the comfort term (0.54 kWh per K-h) prices overheating
cheaply.

The mean-air constraint is broken in every week except parts of jan_cold. The pattern is
consistent:

- **Cold weeks:** the port is slightly better. It sends hot water into the slab ahead of the cold
  hours, and the firm floor protects comfort.
- **Damp/mixed weeks:** the port is worse, from more starts and hotter water.
- **Sunny shoulder weeks:** it is much worse, as section 5.2's day profile predicts. When the
  room drops just under 22.0 in the evening after a sunny day, the planner (firm floor at target
  all night) buys a reactive catch-up pulse of 32-36 °C water; the next day's sun then takes the
  room to 24-25 °C. Section 8 (R3) attributes these pulses. The too_warm stop
  then holds 25 °C but cannot remove heat already in the slab. A day of apr_mild_sunny (seed 1)
  in the per-minute CSV: a 34-36 °C pulse at 01-03 h, room 21.7 → 22.0, then sun to 25.3 °C by
  noon. The planner's sun model expected some glow, but not enough to skip the night pulse.

## 6. Known weaknesses (of the production controller, as seen in the lab)

- **Asymmetric comfort: the mean air sits above target.** The floor equals the target, and
  overshoot is priced 15x below undershoot. Season mean +0.3 K, sunny weeks +0.8-1.4 K. This
  alone breaks the ranking constraint.
- **Reactive night catch-up pulses.** When the room dips 0.1-0.2 K under the night floor after
  a sunny day, the planner (80 % of cases) and the Guard / start_level lifts buy a 32-36 °C pulse;
  the next day's sun then overheats the room. Metered electricity +42 / +71 / +81 % in the
  oct / mar / apr weeks, hidden by the normalised metric (+4 / +16 / +14 %).
- **Not better on fresh seeds and not robust.** Season seeds 3-4 worse (+1.44 %), pooled 0-4
  undecided; robust 0 better / 19 undecided / 1 worse (partload_lo); every season run and every
  week breaks mean_air, 5 of 7 weeks also break mae.
- **Runs ended by our own writes.** About 95 % of heating stops follow a setpoint drop (baseline
  about 20 %), and early-run compressor power is about 40 % higher, which partload_lo punishes.
- **Hot fallback without a forecast** (curve offset 3): up to 37 °C at -5 °C outdoor.
- **Hot, short pulses.** Mean outlet 32 °C against 30 °C for the baseline. Median runs are 3 h
  against 4.5-5 h, and starts +25 %. The half-hour model treats the setpoint as average heat and
  does not see the firmware's own cycling, the 2-K stop or the surge timer. The start_level lift
  then adds outlet + 5 K on top of the plan.
- **Setpoint at the 40 °C ceiling** (flag `setpoint_range`), now and then on cold mornings, from
  the Guard and start_level stacking.
- **Many writes:** about 15 a day, still under 48.
- **Configuration sensitivity:** night_minimum flips the mean-air error from +0.3 to -0.07 K;
  the documented live options give +0.18 K and turn the season energy verdict from undecided
  to better, yet still break mean_air (section 8, R5).
- **Learning starts cold in the lab.** Short weeks run mostly on the default house.

## 7. Reproduce

```
.local/lab-venv/bin/python -m lab.controllers.current_port        # self-test: fast plan == production plan
.local/lab-venv/bin/python lab/run.py --compare -c replay_recorded,current_port -s recorded
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,current_port -s season --seeds 0-2
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,"current_port[night_minimum=20]" -s season --seeds 0-2
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,current_port -s season --seeds 0-1 --robust
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,current_port -s weeks --seeds 0-2
# live options (section 8, R5)
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,"current_port[night_minimum=21.5,quiet_start_hour=22,morning_hour=7,curve_offset=0.5,stale_minutes=360]" -s season --seeds 0-2
```

Results: `.local/lab-results/controllers/current_port/`. A season run takes about 15 CPU-minutes
(the plan search), against about 3 s for the simple controllers.

## 8. Review fixes (adversarial review, 2026-11-07)

The reviewer confirmed the fidelity of the port (AST-identical decision logic, no cheating, no
hidden state, deployable: no writes while paused, 15-17 writes/day). Its performance findings are
real. Because this controller is a *port*, the fix is not to retune it (that would stop it being
the production controller) but to report it correctly, finish the robust table, and evaluate the
documented live configuration. **The controller code is unchanged.** Every claim below comes
from runs on seeds 0-2 (season, weeks) and 0-1 (robust); seeds 3-4 numbers are the reviewer's.

**R1 (major, accepted): the season result does not hold on fresh seeds.** Seeds 3-4: worse,
+1.44 ± 0.92 %; pooled 0-4: +0.32 ± 1.20 %, undecided. Section 5.2 now states "not better".

**R2 (major, accepted): the port fails `--robust`.** The robust run is now complete (section
5.3): 0 better / 19 undecided / 1 worse (partload_lo, +0.97 ± 0.55 % at c = 0.2, worse at both
start costs), and every variant breaks the mean-air constraint. The earlier summary should have
stated the partload_lo verdict, which was already computable from the partial files.

**R3 (major, accepted, with a refinement of the mechanism): overheating and metered
electricity.** The weeks table (5.4) now shows metered % beside normalised %: +42 % (oct),
+71 % (mar), +81 % (apr) metered against +4 / +16 / +14 % normalised. I traced the cause in
apr_mild_sunny seeds 0-2 by instrumenting the plan, Guard and lifts on every control cycle
(script outside the repo, controller unchanged). All 176 cycles with a setpoint ≥ 31 °C were at
night (20-09 h local); the room was 21.8-21.9 °C, just under the 22.0 night floor. Of those,
**140 (80 %) came from the plan itself** (mean planned water 32.5-34.1 °C), 23 (13 %) from the
Guard and 13 (7 %) from the start_level lift. So the reviewer's "reactive night catch-up with hot
water" is right, and it is mainly the planner, not the Guard: a firm quadratic floor at the
target all night makes a 0.1-0.2 K evening dip after a sunny day expensive enough to buy a
32-36 °C pulse, and the next day's sun then overheats the slab-warmed room.

**R4 (major, accepted): constraint breaks under-reported.** 5.4 now lists every break per week:
mean_air breaks in all 7 weeks and mae in 5 of 7 (oct, nov, dec, mar, apr). The two "better"
weeks (jan_cold, feb_sunny_cold) break mean_air, so they are not passes; jan_cold's "better" also
does not reproduce on seeds 3-4 (-1.87 ± 11.4, undecided).

**R5 (minor, done): the documented live options.** I ran the options recorded for the first house
in docs/PREDICTIVE.md (night_minimum 21.5, night 22-07 h, curve_offset 0.5, stale 360 min) on the
full set:

| | night_minimum 22 (5.2) | **live options** |
|---|---|---|
| season seeds 0-2, adjusted c=0.2 (c=0.05 / 0.3) | -0.43 ± 1.74 (undecided) | **-1.87 ± 0.97 (-2.23 / -1.64), better on energy** |
| normalised / metered energy | -0.49 / +1.57 % | -1.28 / +0.00 % |
| comfort K-h | -30 | -94 |
| mean air per seed | 22.27 / 22.30 / 22.32 | **22.14 / 22.19 / 22.22 (still breaks ±0.05)** |
| mae (base) | 0.49-0.54 (0.49-0.53) | 0.48-0.50 (0.49-0.53) |
| starts/d (base), median run | 2.4-2.7 (2.0-2.1), 179-194 min | 2.6-2.7, 179 min |
| mean outlet running | 32.2-32.4 °C | 31.9-32.1 °C |
| writes/day | 15.2-16.0 | 16.4-17.2 |
| robust, seeds 0-1 | 0 / 19 / 1 (better / undecided / worse) | 3 / 17 / 0 (better: partload_hi, raw_return, sun_minus30; partload_lo -0.67 ± 2.77) |
| robust mean-air breaks | 40 of 40 runs | 39 of 40 runs (only minute_only seed 0 inside) |

Results: `.local/lab-results/controllers/current_port/live_opts/` (season), `weeks_live/`,
`robust_live/` with the paired table in `robust_live_rank.txt` (variant means of mean air
22.07-22.26, all variants flagged `setpoint_range`).

Weeks with live options (seeds 0-2, adjusted % c=0.2, metered %): oct +0.5 ± 35.6 (+34 %),
nov +5.4 ± 9.6 (+6 %), dec **+5.2 ± 3.2 worse**, jan -0.8 ± 0.3 (-3 %), feb -2.2 ± 1.9,
mar +0.3 ± 14.9 (+50 %), apr +25.3 ± 44.4 (+63 %). Every week still breaks mean_air, and mae
breaks in oct, nov, dec, jan and apr. Live options halve the warm bias and soften the spring
pulses but do not remove them. On the season the live configuration is better than the baseline on
adjusted energy (seeds 0-2) and even has fewer comfort K-h, but its mean air is 0.14-0.22 K above
target on every seed, so it still fails the ranking constraint and is **not a pass**.

**R6 (minor, noted).** Of 423 heating stops in the reviewer's seed-0 season, 403 followed a
setpoint drop (mean 5.1 K), against 60 of 292 for the baseline; outdoor-unit power 30-90 min
into a run is about 2.05 kW against 1.45 kW. Added to the weaknesses.

**R7 (minor, noted).** Without a forecast the fallback curve (offset 3, slope 0.45 plus room
feedback) ramps to 37 °C at -5 °C outdoor, against about 30 °C needed. With curve_offset 0.5
(live options) the fallback is 2.5 K cooler. Faithful to production, a deployment risk.

**R8 (minor, documented).** (b) the emulated clamp write and (c) the forecast label shift are now
stated in section 4 (items 5 and 7). The other divergences do not affect results.

**R9, R10:** no action needed.
