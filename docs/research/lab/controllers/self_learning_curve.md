# self_learning_curve: a heating curve that learns itself from the room (strategy S11)

Code: `lab/controllers/self_learning_curve.py` (stdlib only, `python -m lab.controllers.self_learning_curve`
runs an assert self-check). Results: `.local/lab-results/controllers/self_learning_curve/` (private;
the review-fix runs are under `fix/`).

Sections 1-6 describe the controller after the first adversarial review; where a number in
sections 4-5 comes from the first version it says so. Section 7 lists the first review's fixes.
**Section 8 (second review) supersedes the headline numbers, defaults and fail-safe notes below**:
slope floor 0.15, DHW/defrost freeze, forecast cache plus persistence fallback, and no upward write
in the 2 h after a start.

## 1. Idea

The leaving-water setpoint is a weather curve plus a room trim:

```
sp = target + c0 + c1 x (target - T_eff) - c2 x G_sun + I + clip(kp x e_f - clip(kp x td x dT_room/dt, ±1.5), ±3)
```

- **T_eff** is the mean forecast outdoor temperature of the next 12 hours (the slab answers in
  hours, so the curve looks ahead instead of at the past day). The unit's own outdoor sensor is
  used only when there is no forecast (it reads warm in sun and while idle; giving it any weight
  made the result worse, section 4).
- **G_sun** is the mean forecast global irradiance 1-10 hours ahead (kW/m2). Sun through the
  windows can cover the whole load of a mild day; the slab has to be cooler *before* it comes.
- **Room error** e = target - (thermometer - 0.8 mK per W/m2 x irradiance now). The thermometer
  is lit by the sun (HOUSE_MODEL.md: about +0.4 K in full sun); the irradiance now is taken from
  the PV output (8.9 kW per kW/m2), or the forecast hour without PV.
- **Trajectory term:** the room slope over the last 3 hours (least squares on the reported values)
  times 2 hours is subtracted from the error: the controller acts on where the room is going, not
  where it is (S11's "room trajectory"). The trajectory part is capped at ±1.5 K of setpoint and P
  plus trajectory at ±3 K, so thermometer noise cannot swing the setpoint far (section 7, R2).
- The curve uses `obs.target`, so a target change moves the water by (1 + c1) K per K.
- **I** is a slow integral (0.3 K per K-hour, limit ±4 K). A long-run mean error shifts the aim by
  as much (max ±0.3 K): hours that the heating cannot cool (sun, occupants) push the room warm, so
  the controller aims that much lower at other times and the mean air stays on target. Its averaging
  window grows from 1 day after a fresh start to 7 days.

**Learning.** Once a day the controller forms one sample: the mean setpoint it applied without the
fast P/trajectory part (curve + I) plus 1.5 K per K of the day's mean room error, against the day's
mean T_eff and G_sun. This is "the setpoint that would have held the room that day". The curve
(c0, c1, c2) is refitted by weighted least squares over the last 120 daily samples (weight 0.98 per
day of age, so about 50 days of memory), in a centred slope variable (centre at target - T_eff =
17 K, i.e. +5 °C outdoors, so offset and slope do not trade off when the weather spans a narrow band;
the first version centred it at +17 °C by mistake), with a weak ridge pull towards the
initial curve (0.5 / 5 / 5 "days" for offset / slope / sun) and bounds (c1 0.05-0.9, c2 0-20 K per
kW/m2). After each refit the change of the curve at the current weather is added to I (bumpless): the
setpoint never jumps when the curve learns; the curve takes over what I had to carry, and a new
weather regime starts from the learned curve rather than from zero.

The default initial curve is a sensible one for this house: c0 = 4, c1 = 0.18, c2 = 8 (about 27 °C
at +7 °C and 31 °C at -14 °C, the flat curve section 2 derives). The first version started from a
deliberately poor curve (c0 0, c1 0.5, c2 0: 2.5 K too warm at +7 °C, 9 K too warm at -14 °C) to show
the learning; `c0=0,c1=0.5,c2=0` still reproduces that start. The learned state (curve, initial
curve, integral, mean error, daily samples) is exported by `snapshot()` and restored with
`reset({"state": ...})`, so a deployment keeps its curve across restarts.

**Execution.** A decision every 5 minutes, the register changed only when the request moved by
0.9 K and at least 40 minutes after the last change, by at most 3 K per write (whole degrees,
25-39 °C, the recorded range). While the compressor runs a heat cycle, a lower setpoint is held at or
above outlet - 1.5 K, so a write does not trip the firmware's immediate stop (control sensor >=
setpoint + 2 K) unless the room is more than 0.4 K warm. Restart hysteresis is written once at
take-over to 5 K (inside the recorded 4-5 K) and never re-asserted. The firmware does the cycling;
no setpoint riding (tried, section 4).

**Write discipline.** A value is sent when decided, re-sent at most twice (15 minutes apart) if
the unit does not report it; then the controller adopts the reported value and leaves the setpoint
alone for 6 hours. A rolling 24-hour budget caps all writes at 36. The space-heating switch is
never written; while it is off the controller writes nothing and freezes its integral, aim and
learning.

**Fail-safe.** Room missing or older than 4 h: the trim and the trajectory term freeze and the curve
alone runs. No forecast: the sun-corrected, 3-hour filtered unit sensor stands in and the sun term is
zero. Link down: nothing is written (commands would wait anyway). Days with fewer than 18 h of
observations or 12 h of room data give no learning sample; one sample's residual against the
current curve is clipped to ±3 K. DHW and defrost need no special case: the controller never reacts to water temperatures.

## 2. Physics behind it

- The slab (4.4 kWh/K, 2.2 h and 11 h time constants) takes hours to change the room. A curve on
  the *past* 24 hours (the baseline) is late by about a day when the weather turns; the forecast
  of the next 12 hours is early by about the right amount. Window 6 h or 24 h: both worse.
- Sun: solar apertures of about 13 m2 effective (south 2.7, east 6.4, west 3.7) against a
  0.19 kW/K loss mean 300 W/m2 on the facades is worth 10-20 K of outdoor temperature. In March
  and April that is the whole load; the only defence against overheating is a cooler slab before
  the sun, i.e. a lower curve on a sunny forecast. This term alone is worth about 3.5 points of the
  score (section 4).
- The required curve in this house is flat: about 27 °C at +7 °C and 31 °C at -14 °C. In cold
  weather the unit runs continuously and its water rides above the setpoint; in mild weather the
  setpoint mainly sets when runs start (t_ctrl = sp - 5 K) and stop (sp + 2 K).
- Comfort is priced at 0.54 kWh per K-hour. The baseline holds the room to a mean |error| of
  0.51 K, worth about a quarter of the season's electricity, so tracking is the biggest lever a
  curve controller has; within-day disturbances (bootstrap residual, hourly SD about 1 kW) set a
  floor that no controller of a slab can remove.

## 3. Parameters (final defaults)

| parameter | value | meaning |
|---|---|---|
| c0, c1, c2 | 4, 0.18, 8 | initial curve (first version: 0, 0.5, 0) |
| lam, memory_d | 0.98, 120 | daily weight decay of samples, samples kept |
| r0, r1, r2 | 0.5, 5, 5 | ridge towards the initial curve (days of data equivalent) |
| x_centre | 17 K | centre of the slope regressor (+5 °C outdoors) |
| g_room, y_clip | 1.5, 3 K | K of setpoint per K of daily mean room error; clip of one day's residual |
| kp, td_h, slope_win | 4 K/K, 2 h, 180 min | P on the predicted room error |
| d_max, fb_max | 1.5 K, 3 K | caps of the trajectory part and of P + trajectory |
| ki, i_lim | 0.3 K per K-h, 4 K | integral |
| k_mean, mean_tau0_d..mean_tau_d, aim_max | 1, 1-7 d, 0.3 K | aim shift from the long-run mean error |
| fc_h0..fc_h1 | 0-12 h | outdoor window of the forecast (unit sensor only without a forecast) |
| sun_h0..sun_h1 | 1-10 h | sun window of the forecast |
| glow | 1 | subtract the thermometer's sun glow |
| sp_min, sp_max | 25, 39 °C | setpoint limits (first version 25-45) |
| hyst, min_dwell, max_step, period | 0.9 K, 40 min, 3 K, 5 min | write rules |
| stop_guard, stop_margin, warm_stop | 1, 0.5 K, 0.4 K | no immediate-stop write during a run unless the room is 0.4 K warm |
| write_budget, retries, retry_gap, backoff_min | 36 / 24 h, 2, 15 min, 360 min | write discipline |
| restart_delta | 5 K | written once at take-over |
| c1_min, c2_max | 0.15, 20 | curve bounds (second review; was 0.05) |
| up_hold | 120 min | no upward write after a compressor start (second review) |
| fc_keep_h, persist_sun | 36 h, 0.7 | forecast cache life; weight of yesterday's sun in the persistence forecast |
| freeze_dhw | 1 | DHW and defrost minutes freeze integral, aim and learning sample |

## 4. Tuning record (season, seeds 0-2, adjusted % vs reference_tuned at c = 0.2; negative is better)

| step | change | adj % | note |
|---|---|---|---|
| 0 | first version, recursive least squares, restart delta 4 | -4.6 | seed 1 RLS drifted (c1 to its floor), mean air 22.05 |
| 1 | batch ridge least squares instead of RLS | -4.5 (poor start) / -4.7 (good start) | slope no longer collapses; frozen good curve -3.7: learning is worth 1 point even from a good start |
| 2 | sp_min 24 -> 25 | -3.9 | 24 °C is outside the recorded setpoints (flag); kept 25 |
| 3 | restart_delta 4 -> 5 | -4.8 | fewer starts (1.9 vs 2.2 a day) |
| 4 | trajectory term td 0 / 1 / 2 / 3 h (kp 3-5) | -3.3 / -3.9 / -5.5 (kp 4) / -5.3 | td 2 h, kp 4 kept |
| 5 | sun term off (r2 huge) | -2.1 | sun anticipation is worth about 3.5 points |
| 6 | sun window 1-10 h vs 0-5 / 0-8 / 1-6 / 3-15 h | best 1-10 | 3-15 h -2.4 |
| 7 | outdoor window 0-6 / 0-12 / 0-24 h | -5.0 / -5.5 / -4.9 | |
| 8 | unit-sensor weight 0 / 0.3 / 0.6 | -5.6 / -5.5 / -4.9 | sensor dropped (fallback only) |
| 9 | ki 0.15, g_room 3, sp_max 39 | -5.2, -5.5, -5.3 | unchanged defaults |
| 10 | write hysteresis 0.6 -> 0.9 K, dwell 20 -> 40 min | -5.8 | slightly better, fewer writes |
| 11 | run-time riding (sp = outlet + k while running, k 1.5 / 0.5 / -0.5) | -5.7 / -5.6 / -5.3 | no gain: the central COP model peaks at mid output, so holding minimum output does not pay; dropped |
| 12 | long-run mean-error aim (k_mean 0 / 1 / 2) | -5.8 / -5.5 / -5.2 | k_mean 1 kept: without it loss_minus20 broke the mean-air constraint (22.06) |

Steps 0-12 tuned the first version (poor start). Review-fix tuning (sensible start, section 7):

| step | change | adj % | starts/d | note |
|---|---|---|---|---|
| 13 | all review fixes, max_step 2, slope_win 120 | -4.63 ± 0.52 | 1.8 | energy -1.08 % |
| 14 | the same with each fix undone: max_step 10 / stop_guard 0 / caps off / aim tau 7 d | -4.84 / -5.01 / -4.39 / -4.65 | 1.8-1.9 | caps off is worse even without noise |
| 15 | all fixes undone (v1 equivalent incl. poor start, old centre, no clip) | -5.51 ± 0.18 | 2.2 | reproduces the first version |
| 16 | max_step 3; warm_stop 0 / 0.2; stop_margin 0 | -5.08; -4.94 / -4.74; -4.79 | 1.8-1.9 | max_step 3 kept; guard kept at 0.4 K |
| 17 | with 0.15 K thermometer noise: max_step 2 / 3 / 3 + slope_win 180 / 3 + d_max 1 / 3 + kp 3 / v1 | -4.06 / -4.45 / -4.44 / -4.31 / -4.21 / -4.43 | 1.9 / 2.0 / 1.9 / 1.9 / 2.0 / **2.9** | v1 needed min_off |
| 18 | max_step 3 + slope_win 180 (nominal) | **-5.07 ± 0.67** | 1.8 | kept |
| 19 | aim_max 0.6, k_mean 1.5 (weeks only) | no better on the weeks | | aim_max stays 0.3 |

Glow correction off: same score, but mean air 21.98 and energy -1.5 % instead of -1.3 %: it mainly
moves the mean onto the target.

## 5. Results

### Season, nominal, seeds 0-2 (final, after the review fixes)

| | adj % c=0.2 (90 %) | c=0.05 / c=0.3 | verdict | energy % | comfort K-h | metered % | starts/d (base) | writes/d (base) | mean outlet running (base) | mean air | mae (base) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **self_learning_curve** | **-5.07 ± 0.67** | -4.94 / -5.15 | better | -1.36 | -315 | -1.34 | 1.8 (2.1) | 11.4-11.8 (9.3-9.8) | 30.7-30.8 (30.0-30.3) °C | 22.01-22.02 | 0.44 (0.51) |
| same, poor start (c0 0, c1 0.5, c2 0) | -4.77 ± 0.20 | -4.64 / -4.86 | better | -1.40 | -285 | -1.36 | 1.8 | | | 22.02 | 0.45 |
| same, curve frozen (learn=0) | -4.05 ± 0.37 | | better | -1.12 | -250 | -0.88 | 1.9 | | | 22.04 | 0.46 |
| first version (for reference) | -5.48 ± 0.59 | -5.54 / -5.44 | better | -1.77 | -338 | -1.72 | 2.2 | 12.6-13.2 | 30.9-31.0 | 22.01-22.02 | 0.44 |

No `cold_share` flag on the final nominal run; break-even start cost is negative (fewer starts than
the baseline). Diagnostic `long_outage` (seed 0): -4.70 %, mean air 22.01.

How the unit runs (season seeds 0 and 1, window, per-minute CSVs; reviewer's scripts):

| | reference_tuned | first version | final |
|---|---|---|---|
| setpoint steps >= 3 K per season | 0-5 | 398-448 | 88-94 (all exactly 3 K) |
| largest step | 2-5 K | 10-11 K | 3 K |
| setpoint max | 37-39 °C | 43-45 °C | 37-38 °C |
| compressor power while running, median | 1.55 kW | 1.76 kW | 1.65-1.67 kW |
| share of running minutes > 2.5 kW | 13-14 % | 21-23 % | 17-19 % |
| supply while running on mild days (> 4 °C), median | 29.7 °C | 30.5-30.7 °C | 30.2-30.4 °C |
| stops that follow a setpoint drop | 11 % | 29-33 % | 13-16 % |
| starts per day | 2.0-2.1 | 2.2 | 1.8-1.9 |

### Robustness, season, seeds 0-1, all 20 mandatory variants (final)

Better on **20 of 20**, no constraint breaks. Adjusted % at c = 0.2:

| variant | adj % | variant | adj % |
|---|---|---|---|
| nominal | -4.92 | low_flow | -4.96 |
| partload_lo | -5.26 | high_flow | -4.80 |
| partload_hi | -5.19 | loss_minus20 | -5.12 (mean air 22.04) |
| legacy_cop | -5.10 | steep_outlet | -5.27 |
| high_start_loss | -4.99 | shallow_outlet | -5.09 |
| sluggish | -5.06 | frost_melt_lo | -5.00 |
| raw_return | -4.27 | frost_melt_hi | -5.25 |
| minute_only | -4.50 | light_slab | -4.68 |
| heavy_slab | -5.21 | sun_plus30 | -5.22 |
| sun_minus30 | -5.06 | forecast_pessimistic | -4.64 |

Starts 1.6-2.0 a day against 1.9-2.3 for the baseline on every variant. `cold_share` remains on
loss_minus20, low_flow, shallow_outlet and the two sun variants.

### Thermometer-noise probe (season, seeds 0-2; AR(1) error, 30-min time constant, re-quantised)

| probe | first version | final |
|---|---|---|
| 0.15 K on the candidate only | -4.34 %, 2.9 starts/d, `min_off` | -4.44 %, 1.9 starts/d (baseline 2.1), no `min_off` |
| 0.3 K on the candidate only | -2.95 %, 4.1 starts/d | -3.93 %, 2.1 starts/d |
| 0.3 K on both controllers | -3.98 %, 4.1 vs 2.7 starts/d, break-even 0.97 kWh | -4.95 ± 0.61 %, 2.1 vs 2.7 starts/d, break-even negative |

### Weeks, seeds 0-2 (diagnostic, fresh start each week)

| week | adj % | verdict | metered % | mean air (base) | first version: adj % / mean air |
|---|---|---|---|---|---|
| oct_mild | -23.1 ± 27.0 | undecided | +1.5 | 22.05 (22.00) | -14.4 / up to 22.4 |
| nov_mixed | -4.8 ± 3.2 | better | -1.1 | 22.07 (22.00) | -2.0 |
| dec_damp | -0.6 ± 1.2 | undecided | -0.3 | 22.01 (22.00) | -0.7 |
| jan_cold | -0.5 ± 0.9 | undecided | +1.0 | 22.00 (22.00) | -0.3 / 22.41 |
| feb_sunny_cold | -0.6 ± 1.5 | undecided | +3.9 | 22.05 (22.00) | +0.1 / 22.50 |
| mar_shoulder | +2.1 ± 5.7 | undecided | +3.2 | 22.12 (22.11) | +6.1 / 22.65 |
| apr_mild_sunny | -17.5 ± 43 | undecided | -14.2 | 22.27 (22.33) | -10.5 / 22.76 |

With a sensible start the first week no longer runs far too warm: mean air is within 0.07 K of the
baseline's in every week, and the metered first-week penalty fell from up to +10.5 % to +3.9 %.
Single seeds still break the ±0.05 K mean-air rule (22.06-22.12 in oct, nov and feb; 21.94/22.08
in jan); in mar and apr the baseline itself is 0.1-0.3 K warm (sun), so the rule cannot be met by
either. A larger or faster aim shift (aim_max 0.6, k_mean 1.5, or a 7-day window from the start)
did not help (step 19).

### Convergence (first version, seed 0, mean |error| / mean air of the true air)

| days | 0-3 | 3-7 | 7-14 | 14-30 | 30-60 | 60-183 |
|---|---|---|---|---|---|---|
| poor start, learning | 0.51 / 22.23 | 0.60 / 21.83 | 0.38 / 22.05 | 0.29 / 22.00 | 0.24 / 21.99 | 0.46 / 22.02 |
| good start, learning | 0.57 / 22.09 | 0.59 / 21.86 | 0.36 / 22.05 | 0.29 / 21.98 | 0.24 / 21.99 | 0.46 / 22.03 |
| poor start, frozen | 0.46 / 22.30 | 0.62 / 21.94 | 0.40 / 22.02 | 0.27 / 22.02 | 0.24 / 22.01 | 0.52 / 22.27 |
| reference_tuned | 0.64 / 22.05 | 0.65 / 21.84 | 0.41 / 21.95 | 0.31 / 21.92 | 0.27 / 21.93 | 0.56 / 22.04 |

## 6. Known weaknesses

- **Comfort carries most of the gain.** Energy alone is -1.36 % over the season (-1.0 to -1.7 %
  across the variants); comfort is -315 K-h, about 3.7 % of the baseline's electricity at
  0.54 kWh per K-h. Energy-only and comfort-only both favour the controller, but the energy part
  is about 1.4 %, not 5 %.
- **Water is still a little warmer than the baseline's:** +0.5-0.6 K mean outlet while running,
  +0.5-0.7 K median supply on mild days (first version +0.8-1.0 K). The 5 K restart hysteresis
  gives fewer, longer, mid-output runs; that is where the COP gain (2.95 vs 2.90) comes from, and
  it rests on the central part-load COP curve.
- **Needs the forecast.** Without one (reviewer's probe, first version) it falls back to roughly
  baseline behaviour (-1.2 %, mae equal to the baseline). The simulator's sun-forecast error is
  multiplicative and cannot forecast sun on a day that turns out overcast; a harsher error model
  cost about 1 point.
- **Sun weight is poorly identified** (sunny days are also mild); it is bounded (0-20 K per kW/m2)
  and ridge-pulled towards 8.
- **Single weeks** still break the ±0.05 K mean-air rule on some seeds (section 5).
- **Writes** are 11-12 a day (baseline 9-10).
- **Thermometer glow correction** uses the house model's fitted coefficient; on the real house it
  needs its own check.
- **The stop guard uses the outlet** as a stand-in for the firmware's control sensor (the water
  sensor after the backup heater). A 0.5 K margin covers the usual offset; a real deployment should
  read the control sensor if it is exposed.

## 7. Review fixes

The adversarial review (R1-R8) found no cheating and reproduced the result on seeds 3-4. What was
changed, issue by issue:

- **R1 (major, hotter and harder running, large setpoint swings): fixed.** At most 3 K per write
  (the reviewer suggested 2 K; 2 K cost 0.4 points for little extra smoothing, step 13 vs 18),
  sp_max 39 °C (the recorded range), P + trajectory capped at ±3 K, and a stop guard: during a heat
  run a lower setpoint is held at or above outlet - 1.5 K unless the room is more than 0.4 K warm,
  so writes no longer trip the immediate stop by accident. Result (section 5 table): no step above
  3 K, setpoint max 37-38 °C, stops after a setpoint drop 13-16 % (baseline 11 %, first version
  29-33 %), median running power 1.66 vs 1.55 kW (first version 1.76), mild-weather supply
  +0.6 K over the baseline (first version +0.9 K), starts 1.8 a day (baseline 2.1, first version
  2.2). Cost: 0.4 points of adjusted score (-5.07 vs -5.48 %).
- **R2 (major, thermometer noise into starts): fixed.** Trajectory part capped at ±1.5 K, slope
  window 3 h instead of 2 h, P + trajectory capped at ±3 K, plus the step limit. With 0.15 K noise
  starts are 1.9 a day (first version 2.9) and no `min_off`; with 0.3 K noise on both controllers
  2.1 vs 2.7 starts a day and -4.95 % (first version 4.1 starts, -3.98 %).
- **R3 (major, write storm, overriding the owner): fixed.** A value is sent once when decided and
  re-sent at most twice; if the unit still reports something else the controller adopts the
  reported value and backs off for 6 h; a rolling 24-hour budget caps all writes at 36. Test: a
  unit that refuses every value (installer limit) now gets 11.7 writes a day instead of 1440.
  `heating_enabled` is never written; while heating is off nothing is written and the integral,
  aim and learning freeze. `restart_delta` is written once at take-over and never re-asserted
  (self-check: an owner's later change to 4 K is left alone).
- **R4 (major, cold start breaks mean air and costs energy): fixed in part.** The default initial
  curve is now the sensible one for this house (c0 4, c1 0.18, c2 8); the learned state is exported
  by `snapshot()` and restored by `reset({"state": ...})` for persistence; the mean-error aim
  averages over 1 day after a fresh start and widens to 7 days. Weeks: mean air within 0.07 K of
  the baseline in every week (first version up to 0.76 K too warm), first-week metered penalty at
  most +3.9 % (first version +10.5 %). Single seeds still break the ±0.05 K rule in oct, nov, jan
  and feb by 0.01-0.07 K; the baseline is re-aimed per week with hindsight, and in mar and apr it
  breaks the rule itself. The ranking rule on single weeks is not met; the season is.
- **R5 (minor, score mostly comfort):** energy and comfort are reported separately (sections 5, 6).
- **R6 (minor, needs the forecast):** documented (section 6).
- **R7 (minor, doc and code disagreed): fixed.** The daily residual is now clipped to ±3 K as the
  doc said; the docstring describes the batch ridge fit and the forecast-only outdoor input; the
  curve uses `obs.target`; the slope regressor is centred at +5 °C outdoors as intended (it was at
  +17 °C; the centring is score-neutral: -4.57 vs -4.63 %).
- **R8 (simulator note):** agreed; reported, not changed (lab/sim is not ours to edit).

## 8. Review fixes (second review, R1-R8)

The second adversarial review reproduced a better verdict on fresh seeds 3-4 but a smaller gain
(-4.29 %), found the claim block stale, and raised forecast dependence, curve identification and
hotter water. All runs below: season, seeds 0-2 (tuning) or 0-1 (robust), noisy forecast, default
link drops; results under `.local/lab-results/controllers/self_learning_curve/fix2/`.

### Headline (final defaults), season nominal, seeds 0-2, vs reference_tuned

| | adj % c=0.2 (90 %) | c=0.05 / 0.3 | energy % | metered % | comfort K-h | starts/d (base) | writes/d (base) | mean outlet running (base) | sp max | mean air | mae (base) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **final** | **-4.98 ± 0.33** | -4.83 / -5.09 | **-1.53** | -1.53 | -289 | 1.8 (2.1) | 8.3-8.8 (9.3-9.8) | 30.5-30.6 (30.0-30.3) °C | 35-37 | 22.01 | 0.45 (0.51) |
| poor start (c0 0, c1 0.5, c2 0) | -4.48 ± 0.54 | | -1.53 | -1.49 | -242 | 1.8 | | | | 22.02 | 0.46 |
| curve frozen (learn=0) | -3.55 ± 0.12 | | -1.18 | -0.98 | -196 | 1.8 | | | | 22.03 | 0.47 |
| no forecast at all (probe) | -3.60 ± 0.38 | | -1.28 | -1.27 | -187 | 1.8 | | | | 22.01 | 0.47 |
| forecast missing 2 days in 7 (probe) | -4.89 ± 0.59 | | -1.47 | -1.45 | -286 | 1.8 | | | | 22.01 | 0.45 |
| same, without cache and persistence | -3.36 ± 0.24 | | -1.18 | -1.17 | -174 | 1.8 | | | | 22.01 | 0.47 |

Split of the gain: about 1.5 points energy (normalised and metered alike) and about 3.5 points
comfort (289 K-h at 0.54 kWh per K-h). Read it as a tracking controller that also saves about 1.5 %
of the electricity, not as a 5 % efficiency controller. The reviewer's seeds 3-4 (-4.29 %, energy
-1.09 %) were run on the previous version; seeds 3-9 are not used here.

Robust, seeds 0-1, all 20 mandatory variants: **better on 20 of 20, no constraint breaks**.
Adjusted % from -3.96 (raw_return) to -5.30 (loss_minus20, mean air 22.04); energy -1.02 to
-1.96 %. forecast_pessimistic -4.48, partload_hi -4.62, light_slab -4.33, sun_minus30 -4.75.

### Issue by issue

- **R1 (claim stale; smaller gain on fresh seeds): fixed.** The result is re-stated above with the
  current code and all numbers re-run; the docstring now says 3 K per write. The gain is about
  -5.0 % on seeds 0-2 and was -4.3 % on the reviewer's seeds 3-4; quote it as "about -4 to -5 %".
- **R2 (mostly comfort): agreed, reported separately** (table above). The execution change for R3
  raised the energy part from -1.25 % to -1.53 % (seeds 0-2) at an unchanged adjusted score.
- **R3 (hotter water, harder running): real; mitigated, not removed.** Evidence:
  - With a flat part-load COP (`flat_load`, seeds 0-1) the previous version kept only -0.23 %
    energy (adjusted -4.25 %). So the reviewer was right that its COP gain rested on the central
    part-load surface.
  - Fix: no upward setpoint write in the 2 h after a compressor start (`up_hold` 120 min), so the
    firmware's start burst is not pushed harder by a rising request. Seeds 0-1:
    nominal -5.02 % (energy -1.53 % vs -1.22 %), `flat_load` -4.61 % (energy -1.08 % vs -0.23 %),
    writes 8.8 instead of 11.5 a day, setpoint max 35-37 °C. Mean outlet while running is now
    +0.3-0.4 K over the baseline (was +0.5-0.6 K). up_hold 60 / 90 / 150 / 180 / 300 min:
    -4.90 / -5.02 / -4.39 / -3.45 / +1.5 % (300 breaks comfort); 120 kept.
  - Tried and rejected: restart_delta 4 (outlet within 0.1-0.2 K of the baseline, starts equal to
    the baseline, `flat_load` -4.60 %/-1.09 % energy, but nominal only -4.00 %); a soft start
    (setpoint 1-2 K lower for 30-60 min after each start): energy -1.4 % but comfort worse,
    adjusted -4.2 to -4.6 % and twice the writes (22-24 a day).
  - Remaining: the 5 K restart hysteresis still gives fewer, longer runs with water slightly
    warmer than the baseline's. If the real unit's part-load COP turns out flat, restart_delta 4
    is the cooler-water setting (about 1 point less adjusted score on the central model).
- **R4 (needs the forecast): fixed.** Three layers: the live forecast; else the last forecast
  received, shifted to the current hour, for up to 36 h; else a persistence forecast from the
  controller's own history (each hour of yesterday's sun-corrected unit sensor plus today's
  anomaly over the last 3 h, and 0.7 x yesterday's PV-derived irradiance for the sun term). With
  no forecast for the whole season the gain went from -0.48 % (no fallback) to **-3.60 %**; with
  the forecast missing 2 days in every 7 the result is -4.89 % (-3.36 % without cache and
  persistence) against -4.98 % with a full forecast. Self-check covers cache then persistence.
- **R5 (curve not identified): fixed for the slope, argued for the sun weight.** The slope is now
  bounded at 0.15-0.9 K/K. Physics (HOUSE_MODEL: 0.111 kW/K to outdoors, slab-room 0.43 kW/K,
  loop-slab 2.5 kW/K at 0.71 effectiveness) puts the water-over-room slope near 0.3 K/K; the
  setpoint slope is lower because cold-weather water rides above the setpoint, but not below about
  half of that. Monthly snapshots (seed 0): from the default start c1 0.19, 0.17, 0.15, 0.15, 0.20,
  0.23; from the poor start (c1 0.5) 0.41, 0.24, 0.18, 0.16, 0.23, 0.26. Both starts end at the same
  curve (c0 2-3, c1 0.23-0.26), so the fit is identified from either side; before, c1 fell to 0.05.
  Cost: none (-4.98 vs -4.96 % with the old floor). The sun weight still reaches its bound of 20 in
  spring from either start; bounding it at 14 cost 0.4 points and a 4x stronger ridge on slope and
  sun cost 0.5 points. The sun term is anticipation (cool the slab before the sun), not the steady
  sun gain, and absorbs the sun forecast's error, so its physical value is not a tight bound. The
  default start (4, 0.18, 8) is close to the learned curve; the poor start costs 0.5 points
  (-4.48 %). Every seed is the same weather year, so a different-year check is still missing.
- **R6 (weeks, minor): unchanged, diagnostic.** Weeks seeds 0-2: oct -24.1, nov -3.9, dec -1.5,
  jan +0.5, feb +1.0, mar +0.8, apr -15.3 %; all undecided; mean-air breaks in every week except
  dec (22.05-22.18; jan/feb 21.93-22.08). A fresh start each week, a 1-7 day aim and a baseline
  re-aimed with hindsight. jan and feb are slightly worse than before (the 2-h up-hold slows the
  first cold-week catch-up). A deployment persists the curve (`snapshot()`).
- **R7 (glow correction exact only in the sim): agreed.** Kept; it is not load-bearing (reviewer:
  no PV -4.42 % vs -4.26 %). The coefficient needs a check on the real sensor.
- **R8 (integral winds during DHW and defrost): fixed.** DHW and defrost minutes no longer feed
  the integral, the mean-error aim or the daily learning sample (`freeze_dhw`). Score-neutral
  (-4.96 vs -5.07 %, within noise).

### Remaining weaknesses

- Energy alone is about -1.5 % (raw_return -1.0 %); the rest is comfort pricing.
- Water still 0.3-0.4 K warmer than the baseline's while running; the gain over a flat part-load
  COP is smaller (-1.1 % energy).
- Without a live forecast the persistence fallback keeps about 70 % of the gain, not all of it.
- Sun weight sits on its bound in spring.
- Single weeks still break the ±0.05 K mean-air rule; jan/feb weeks are slightly worse than the
  baseline from a fresh start.
- A forecast-gap probe on seed 1 raised a `min_off` flag once.
