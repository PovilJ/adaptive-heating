# wc_low: low-and-slow weather compensation (S1 + S2 + S3)

`lab/controllers/wc_low.py`, stdlib only, about 60 lines of logic. This is the "boring" baseline
from the research (S2 curve, S3 slow room trim, S1 unit settings). It moves the heating curve. It
never times a start or a stop: the Versati firmware does all the cycling with its own restart and
stop rules (UNIT_MODEL.md section 3).

## 1. Idea

Every minute the controller computes:

```
t_eq  = mean over forecast hours 3..6 ahead of ( outdoor + sun_g x GHI / 100 )
      + sun_d x (mean GHI of the next 24 h) / 100            # added in the review fixes (section 9)
sp    = target + base + slope x (target - t_eq)              # the weather curve
      - k_cold x max(0, t_knee - t_eq)                       # cold kink, added in the review fixes
      + kp x (target - room)                                 # room influence
      + trim                                                 # slow integral: trim += ki x (target - room) dt
                                                             # (x 0.7 when winding down at the floor)
setpoint = round(sp), clamped to 25..39 °C; written only when sp has moved >= 1.0 K from the last write
          (0.8 K before review round 2)
GHI       = forecast irradiance, or a monthly climatological sun schedule when the forecast has none;
            with no forecast at all, t_eq = damped unit sensor + the same climatological sun terms
restart_delta = 5 K (held), quiet off, space heating on
```

Sections 2-8 describe the first version and its tuning record. Section 9 lists the changes made
after the first adversarial review, section 10 those after the second; where they differ, the
later section wins.

- **The curve is the feed-forward.** It uses the same slope as the reference (0.37 K of water per
  K). Changing it made no difference, because the integral takes the level (section 4).
- **The equivalent outdoor temperature comes from the forecast, not from the unit's sensor.** It
  averages forecast hours 3 to 6 ahead, because water sent into the slab now reaches the room
  about 2-6 h later (house time constants 2.2 h and 11 h). Each hour gets a solar term: 100 W/m²
  of global irradiance counts as 8 K warmer air. Sun expected in the next few hours therefore
  lowers the water before the sun arrives. Most of the gain comes from this term.
- **Room influence.** A proportional term (4 K of water per K of room error) and a slow integral
  (0.15 K per K-hour, bounded at ±5 K). Together they shift the curve, as in the S3 day-to-day
  compensation, but the integral works continuously instead of once a day. On purpose, the
  integral has no anti-windup at the 25 °C floor. If the sun overheats the house while the
  setpoint already sits at the floor, the excess is paid back later by a slightly cooler curve.
  That is what holding the mean room temperature requires. With anti-windup the mean air drifted
  to 22.15-22.2 °C, which breaks the ±0.05 K constraint.
- **Unit settings (S1 part).** The restart hysteresis is held at 5 K. Of the two recorded values
  (4 and 5 K), 5 K gives fewer, longer runs: 1.8 starts a day against 2.1 for the baseline, with
  median runs of 300-350 min. Values above 5 K are ASSUMED firmware behaviour and did not help
  (section 4). Quiet mode stays off (section 4).
- **Fail-safe behaviour.**
  - **Room value missing or older than 6 h:** the room terms drop out and the integral freezes, so
    the controller runs on the pure curve.
  - **Forecast missing:** the unit's outdoor sensor, damped over 6 h, takes its place.
  - **Link down:** commands wait.
  - **DHW and defrost:** no special case is needed. The controller only moves the curve.
  - **Space heating:** if it is found switched off, the controller switches it back on.

  Writes: about 12 a day, almost all of them setpoint writes.

## 2. Physics behind it

- **The level of the water temperature.** The house needs 3.1 kW on average over the season. The
  unit's smallest steady output is 3.6-4.3 kW, so above about -5 °C the unit has to cycle
  whatever the controller does. In this simulator the cheapest heat is a run at mid output
  (5.5-6 kW: COP at 6 kW is 1.12-1.34 times the COP at minimum output) with the water no hotter
  than that output needs. Holding the water lower than that only makes the unit sit at minimum
  output, where the part-load penalty is larger than the 3-3.5 %/K lift benefit. So "low" here
  means no water warmer than the room needs, not the lowest setpoint the firmware accepts.
- **Where the gain comes from.** It comes mostly from comfort: time-weighted mean |error| 0.43 K
  against 0.51 K for the baseline. The per-minute error by hour of day shows why. The baseline
  is 0.6 K warm at 12-15 h and 0.4 K cold at 2-6 h. wc_low cuts the midday overshoot to
  +0.35..+0.42 K and the night undershoot to -0.2..-0.36 K. Both changes come from the
  sun-anticipating curve, which delivers less heat before sunny hours. Energy alone falls about
  1.9 %. Most of that drop is in March and April, where wc_low no longer pushes heat into a house
  the sun is about to warm (kWh/day 9.8 vs 11.1 in March, 12.4 vs 14.3 in April).
- **What it does not change.** The mean outlet temperature while running is 0.5-0.7 K *higher*
  than the baseline's (30.7-30.8 vs 30.0-30.3 °C). Fewer and longer runs at higher output, and
  less room-chasing, are worth more in this model than lower water.

## 3. Parameters (final)

| parameter | value | meaning |
|---|---|---|
| `slope` / `base` | 0.37 / 0.8 K (base was 0.2) | curve: sp = target + base + slope x (target - t_eq) |
| `k_cold` / `t_knee` | 0.3 / -2 °C (new) | curve kink: minus k_cold x (t_knee - t_eq) below t_knee |
| `sun_d` | 5 K per 100 W/m² (new) | solar term on the mean GHI of the next 24 h |
| `floor_keep` | 0.7 (new) | share of downward integration kept while the setpoint sits at the floor |
| `trim0` | 0 (new) | restored integral; a deployment saves and restores it |
| `fc_skip` / `h_fc` | 3 / 4 h | forecast hours 3..6 ahead averaged |
| `sun_g` | 8 K per 100 W/m² | solar term of the equivalent outdoor temperature |
| `kp` | 4 K/K | room proportional |
| `ki` / `i_lim` | 0.15 K/(K h) / ±5 K | slow integral (curve shift) |
| `stale_min` | 360 min | room older than this is ignored |
| `hyst` | 0.8 K | setpoint write hysteresis (whole degrees) |
| `sp_min` / `sp_max` | 25 / 39 °C (was 45) | the recorded setpoint range of the real unit |
| `delta` | 5 K | restart hysteresis (recorded value; no `restart_delta` flag) |
| `quiet` | off | |

House and unit knowledge hard-coded from the public lab docs: the 25 °C floor and the 5 K
hysteresis. The curve slope is the reference's. Everything else was tuned on season seeds 0-2.

## 4. Tuning record (season, nominal, seeds 0-2, paired against `reference_tuned`)

Adjusted score in % of the baseline's electricity at c = 0.05 / 0.3 kWh per start. Negative is
better. The ± values are 90 % intervals over 3 seeds.

| step | change | adj c=0.05 | adj c=0.3 | energy % | mae | mean air | note |
|---|---|---|---|---|---|---|---|
| 0 | draft: forecast/sensor blend, kp 0, ki 0.3 | +1.98 ± 1.36 | +2.04 | +0.11 | 0.551 | 22.06 | integral alone tracks the room too loosely |
| 1 | kp 3 | -1.14 ± 0.35 | -1.09 | +0.08 | 0.488 | 22.06 | room influence needed (disturbances about 1 kW hourly SD) |
| 2 | kp 3, delta 5 | -1.40 ± 0.32 | -1.62 | -0.45 | 0.495 | 22.04 | fewer starts |
| 3 | delta 6 | -0.62 ± 0.30 | -1.06 | -0.35 | 0.510 | 22.04 | worse comfort; ASSUMED |
| 4 | forecast only (6 h), kp 4, ki 0.15 | about -2 | | | | | |
| 5 | + sun term (forecast GHI) | -4.3..-5.3 | | -1.1..-1.4 | 0.435-0.449 | 21.99 | the main step |
| 6 | anti-windup at the clamps | (-5.9) | | | 0.416 | **22.15** | breaks the mean-air rule: rejected |
| 7 | flat slope 0.20-0.30 (base matched) | -3.9..-4.2 | | | 0.457 | 21.98 | worse: a steeper curve anticipates forecast swings |
| 8 | steep slope 0.45-0.55 | -4.7..-4.9 | | | 0.44 | 21.99 | no gain |
| 9 | forecast hours 2..7 instead of 0..5 | -5.18 ± 0.65 | -5.41 | -1.20 | 0.433 | 21.98 | slab delay |
| 10 | hours 6..11 | -3.05 ± 1.07 | | | 0.485 | | too far ahead |
| 11 | quiet mode below t_eq -15 / -10 / -5 / 0 / +5 °C | -4.5 / -4.0 / -4.0 / -3.8 / -3.7 | | -1.3..-1.9 | 0.45-0.48 | 21.95 | saves energy, loses more comfort; ASSUMED |
| 12 | delta 7 above t_eq 8 °C | -5.29 ± 0.51 | -5.58 | | | | no different from delta 5 |
| 13 | i_lim 3 | -6.32 ± 0.66 | -6.56 | | 0.417 | 22.03 | moves the mean air towards the limit: not taken |
| 14 | **final** (hours 3..6, sun_g 8, hyst 0.8) | **-6.01 ± 0.87** | **-6.24 ± 0.83** | -1.90 | 0.431 | 21.98 | |
| 15 | final with delta 4 / quiet on / kp 3 / hyst 0.6 | -5.76 / -4.82 / -5.89 / -6.01 | | | | | flat optimum around the final values |
| 16 | final with slope 0.33 or 0.41 (base matched) | -5.90 / -6.02 | | | | | flat |

The optimum is flat in every parameter except the solar term and the forecast window. The
solar gain of 8 K per 100 W/m² is larger than the physical aperture estimate (about 1-3 K). It
partly stands in for the slab delay and for the thermometer's glow. `sun_g` 10 was nominally
better (-6.45) but noisier, so the value was not pushed further.

## 5. Results

### Season, nominal, seeds 0-2 (`run.py --rank -c reference_tuned,wc_low -s season --seeds 0-2`)

| | reference_tuned | wc_low |
|---|---|---|
| adjusted, c = 0.05 / 0.2 / 0.3 | 0 | **-6.01 / -6.15 ± 0.85 / -6.24 %, better** |
| normalised energy | 0 | -1.90 % (metered -2.04 %) |
| comfort K-hours | 0 | -362 K-h |
| mean air / mean abs error | 22.00 / 0.51 K | 21.98 / 0.43 K |
| starts per day | 2.1 | 1.8 |
| median run (seed 0 / 1 / 2) | 288 / 276 / 270 min | 347 / 320 / 300 min |
| writes per day | 9.3-9.8 | 12.3-12.5 |
| mean outlet while running | 30.0-30.3 °C | 30.7-30.8 °C |
| defrosts (seed 0) | 1021 | 1017 |
| break-even start cost | | -6.5 kWh (it saves starts too) |

Monthly picture for seed 0 (mean air / mean |error| / kWh per day):

| month | baseline | wc_low |
|---|---|---|
| Oct | 21.94 / 0.50 / 13.3 | 21.94 / 0.37 / 12.9 |
| Nov | 21.92 / 0.29 / 21.9 | 21.99 / 0.26 / 21.6 |
| Dec | 21.95 / 0.28 / 29.4 | 22.00 / 0.28 / 29.7 |
| Jan | 21.97 / 0.37 / 47.5 | 22.01 / 0.34 / 47.4 |
| Feb | 22.01 / 0.49 / 39.8 | 21.94 / 0.44 / 38.9 |
| Mar | 22.18 / 0.84 / 11.1 | 21.99 / 0.68 / 9.8 |
| Apr | 22.06 / 0.88 / 14.3 | 21.91 / 0.67 / 12.4 |

### Robustness (`--robust`, season, seeds 0-1): better on all 20 mandatory variants

| variant | adj c=0.2 ± 90 % | energy % | variant | adj c=0.2 ± 90 % | energy % |
|---|---|---|---|---|---|
| nominal | -6.30 ± 2.72 | -1.91 | frost_melt_lo | -6.66 ± 2.21 | -2.21 |
| partload_lo | -6.46 ± 2.42 | -1.90 | frost_melt_hi | -6.76 ± 1.56 | -2.36 |
| partload_hi | -6.71 ± 1.46 | -2.37 | light_slab | -6.20 ± 3.07 | -2.12 |
| legacy_cop | -6.03 ± 1.62 | -1.61 | heavy_slab | -6.73 ± 2.75 | -1.97 |
| high_start_loss | -6.38 ± 2.44 | -2.05 | sun_plus30 | -6.59 ± 1.87 | -1.67 |
| sluggish | -6.25 ± 2.63 | -1.95 | sun_minus30 | -6.44 ± 1.93 | -2.52 |
| raw_return | -6.23 ± 1.23 | -1.68 | forecast_pessimistic | -6.10 ± 2.10 | -1.81 |
| minute_only | -6.15 ± 2.76 | -1.60 | low_flow | -6.69 ± 2.55 | -2.26 |
| high_flow | -6.29 ± 2.64 | -1.92 | loss_minus20 | -6.85 ± 1.75 | -2.40 (flag `cold_share`) |
| steep_outlet | -6.43 ± 2.11 | -1.93 | shallow_outlet | -6.54 ± 2.75 | -2.28 |

- The verdict is `better` at both ends of the start-cost band on every variant.
- No constraint is broken: mean air 21.96-22.02 °C, mean |error| 0.41-0.45 against 0.49-0.53 K.
- Diagnostics: `flat_load` -5.16 ± 2.77 (energy only -0.42 %); `long_outage` -6.28 ± 2.06,
  better.

### Weeks (diagnostic, seeds 0-2)

| week | adj c=0.2 ± 90 % | verdict | energy % | mean air | notes |
|---|---|---|---|---|---|
| oct_mild | -38.5 ± 22.6 | better | -9.0 | 21.99 (21.93 on one seed !) | `runs_lt_15min` on one seed |
| nov_mixed | -7.1 ± 9.2 | undecided | -0.6 | 22.02 | |
| dec_damp | -1.4 ± 2.2 | undecided | -1.1 | 22.00 | |
| jan_cold | -3.6 ± 3.3 | better | -0.9 | 22.07 (22.15 on one seed !) | `setpoint_range` (40-41 °C peaks), `cold_share` |
| feb_sunny_cold | -7.7 ± 0.4 | better | -2.0 | 22.06-22.11 ! | |
| mar_shoulder | -22.2 ± 4.5 | better | -1.8 | 22.24-22.29 ! | |
| apr_mild_sunny | -35.1 ± 18.3 | better | -7.0 | 21.92-22.68 ! | |

- Week percentages are relative to small window energies and are dominated by comfort.
- The slow integral is not meant to centre the mean air within a single week. The baseline is
  re-aimed per week, which is why several weeks break the ±0.05 K mean-air rule. The rule holds
  over the season, which is the primary ranking.
- The dull, damp weeks (nov_mixed, dec_damp) show no decided advantage. There is no sun to
  anticipate there, and the structure is nearly the baseline's.

## 6. Known weaknesses

- **Most of the advantage is comfort, not electricity.** Roughly 4 of the 6 points come from the
  0.54 kWh per K-hour comfort price, about 2 points from energy. On `flat_load` the energy gain
  shrinks to 0.4 %.
- **It does not lower the water temperature.** The mean running outlet is 0.5-0.7 K above the
  baseline's. The owner's "too-hot water" complaint is not answered by this controller in this
  simulator: the part-load COP surface favours mid output over minimum output.
- **The solar gain (8 K per 100 W/m²) is empirical and large.** It depends on the forecast
  irradiance being right a few hours ahead. It held on `sun_plus30` / `sun_minus30` and
  `forecast_pessimistic`, but a real forecast with sunny-day biases could move it. A real-house
  trial should start lower (4-6).
- **No anti-windup is deliberate, but it is a lever on the mean temperature.** The integral bound
  (±5 K) decides how much spring overheating is repaid. `i_lim` 3 moved the mean air +0.05 K.
- **Within-day error remains.** The house is still 0.35-0.42 K warm at 12-15 h and 0.2-0.36 K cold
  at 4-7 h. A pure curve cannot remove what the slab delay and the unknown internal-gain profile
  cause. A learned diurnal offset could, but that is a timing element outside this strategy.
- **Writes.** About 12 setpoint writes a day, against 9.5 for the baseline. That is well inside
  48, and `hyst` 1.0 or `kp` 3 gives about 10 at a cost of about 0.2 points.
- **Cold weeks.** In jan_cold the room term pushes setpoints to 40-41 °C at times (the
  `setpoint_range` flag). `sp_max` 39 would avoid this at a small comfort cost (not tested).
- **Weeks are not mean-centred** (see above).
- **Quiet mode and hysteresis above 5 K were not adopted.** Both are ASSUMED in the model. Quiet
  saved 0.6-1 % energy but cost more in comfort, because it limits catch-up capacity.

## 7. Simulator observations

- The integral's lack of anti-windup decides whether a weather-compensation controller meets the
  mean-air rule in spring. The 25 °C floor plus sun make overheating unavoidable for any
  controller, so the rule rewards controllers that repay it later.
- The ±0.05 K mean-air rule is applied per week on 7-day windows, where a slowly integrating
  controller cannot centre. The baseline gets a per-week offset tuned on the true air.
- None of the gain needed ASSUMED behaviour: hysteresis 5 K, setpoints 25-39 °C on the season,
  no quiet mode, heating never switched off.

## 8. Reproduce

```
.local/lab-venv/bin/python -m lab.controllers.wc_low          # self-check
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,wc_low -s season --seeds 0-2
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,wc_low -s season --seeds 0-1 --robust
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,wc_low -s weeks --seeds 0-2
```

Private outputs: `.local/lab-results/controllers/wc_low/` (`rank_season_nominal.txt`,
`rank_season_robust.txt`, `rank_weeks.txt`, `rank_season_diag.txt`).

## 9. Review fixes

The adversarial review (seeds 3-4, `.local/lab-results/controllers/wc_low/review/`) found three
major issues (R1-R3) and four minor ones (R4-R7). All tuning below used season seeds 0-2 only.
Test harness: `.local/lab-results/controllers/wc_low/fix/` (`suite.py`, `rst.py`, `lg.py`). The
"restart every 2 days" wrapper resets the controller every 2880 minutes, as in the review.

### R1 (major, real): the curve was about 3 K wrong and the integral covered it

I logged the integral on season seed 0 and binned it by the 24 h mean `t_eq`. It sat at -1.5 to
-3.6 K below a `t_eq` of -4 °C, and at -2 to -3.8 K above 14 °C (sunny spring). Its season mean was
-0.97 K with SD 2.0 K, and it hit the ±5 K bound 2.2 % of hours. Fixes:

- **Cold kink.** Below `t_knee` = -2 °C the curve now rises 0.3 K per K less steeply. Physical
  reason: in mild weather the unit cycles between the restart point (setpoint - 5 K) and the stop
  point, so the mean water sits well below the setpoint. Once the house needs more than the
  minimum output (below about -2..-5 °C), the unit runs continuously and the mean water sits near
  the setpoint. The same water temperature then needs a lower setpoint. The slope above the knee is
  unchanged.
- **Daily sun term.** `t_eq` gets 5 K per 100 W/m² of the mean irradiance of the next 24 h, on top
  of the 3-6 h term. A sunny day stores heat in the slab, so the water is lower all day, including
  the hours before and after the sun.
- **Base** 0.2 → 0.8 K, which recentres the curve after the two changes above.
- **Integral persistence.** `trim0` seeds the integral, so a Home Assistant integration can restore
  it after a restart (RestoreEntity). The simulator cannot test this, so the curve fix has to work
  without it.

After the fix, the integral on seed 0 has mean -0.12 K, SD 1.58 K, and is at the bound 0.5 % of
hours. Monthly means are Oct +1.1, Nov +0.3, Dec +0.7, Jan -0.6, Feb -0.3, Mar -1.8 and Apr +0.8 K
(before: +0.7, +0.4, +1.0, -1.9, -1.6, -3.4 and -1.7).

| test (season, seeds 0-2) | before | after |
|---|---|---|
| restart every 2 days: mean air | 22.06 / 22.11 / 22.12 (fails) | 22.00 / 22.05 / 22.05 (passes, at the edge) |
| restart every 2 days: mean abs error | 0.415 | 0.417 |
| week seed-mean air, jan_cold / feb / mar / apr | 22.07 / 22.06 / 22.25 / 22.30 | 22.00 / 22.03 / 22.20 / 22.21 |

### R2 (major, partly real): the gain is comfort plus forecast, and the water is not cooler

This is true and is now reported that way. The controller is **sun anticipation that improves
comfort at slightly lower energy**. It is not a low-water-temperature controller.

- Season nominal, seeds 0-2: energy -1.84 %, metered -1.87 %. Comfort is -392 K-h, which is
  about 4.6 of the 6.4 points. On `flat_load` energy is -0.44 %.
- **With the forecast removed** (seeds 0-2, fallback to the damped unit sensor): electricity is
  4952 / 4786 / 4763 kWh against the baseline's 4960 / 4802 / 4772 (-0.2..-0.3 %). Mean abs error
  is 0.48 / 0.515 / 0.514 against 0.49 / 0.53 / 0.52. Mean air is 22.06-22.09, warm and safe. Without
  a forecast the controller is the baseline.
- The mean outlet while running is still about 0.6 K above the baseline's (30.7-30.8 against
  30.0-30.3 °C). In this model, lowering it at the price of more time at minimum output costs
  more than it saves (section 2). I did not change this.

### R3 (major, disputed in part): mean air depends on windup

I agree that full repayment of floor overheating is a crude lever. I disagree that it is a
controller artefact without physical basis: the sun overheats the house while the setpoint is
already at the 25 °C floor, and that heat cannot be avoided. The baseline overheats too: its
own mean air is 22.06-22.13 on mar_shoulder and 22.86 on apr_mild_sunny seed 1. A controller that
meets the mean-air rule therefore has to sit a little cool at other times. Classic anti-windup
on the recalibrated curve still runs warm: 22.10-22.13 on seeds 0-2.

The fix makes the trade-off explicit. While the setpoint sits at the floor, only 70 % of the
downward integration is kept (`floor_keep` 0.7). Results:

| floor_keep | season mean air (seeds 0-2) | mean abs error | comfort K-h | restart every 2 d |
|---|---|---|---|---|
| 1.0 (full repayment) | 21.96 / 21.96 / 21.97 (two variants fail at 21.93-21.94) | 0.436 | 1902 | 21.99-22.03 |
| **0.7** | **21.99 / 22.00 / 22.00** | **0.423** | **1850** | **22.00-22.05** |
| 0.5 | 22.01 / 22.03 / 22.03 | 0.415 | 1813 | 22.02-22.07 (fails) |
| 0 (anti-windup) | 22.10 / 22.12 / 22.13 (fails) | 0.406 | 1775 | |

The rule still rewards repaying unavoidable sun heat; see section 7.

### R4 (minor, fixed): no room sensor ran 0.45 K warm

With the room value always `None` (seed 0), mean air is now 21.88 with mean abs error 0.68 K
(before: 22.29 and 0.94). It now errs 0.12 K cool instead of 0.3-0.5 K warm. A real outage
freezes the restored integral, which is better than this test.

### R5 (minor, fixed): setpoints above 39 °C

`sp_max` is now 39 °C, the top of the recorded range. The cold kink also lowers the peaks: season
max setpoint is 36-39 °C, and no `setpoint_range` flag remains in season, robust or week runs.

### R6 (minor, real): week results with mean-air breaks were called wins

Week runs that break mean-air are now listed as constraint failures. The table counts per-seed
breaks (|mean air - 22| > 0.05 on a seed); "seed mean" is the mean over the 3 seeds.

| week | adj c=0.2 ± 90 % | energy % | metered % | seed mean air | per-seed breaks | baseline seed means |
|---|---|---|---|---|---|---|
| oct_mild | -41.7 ± 24.1 | -11.3 | +0.9 | 22.06 | 2 of 3 (22.06, 22.11) | 21.98-22.01 |
| nov_mixed | -8.4 ± 6.7 | -1.1 | +1.9 | 22.02 | 1 (22.06) | 21.99-22.02 |
| dec_damp | -1.1 ± 1.9 (undecided) | -1.0 | -0.5 | 22.02 | 1 (22.05) | 22.00-22.01 |
| jan_cold | -2.2 ± 2.0 | -0.5 | +0.0 | 22.00 | 2 (21.91, 22.09) | 21.99-22.01 |
| feb_sunny_cold | -7.4 ± 0.3 | -2.0 | +0.9 | 22.03 | 2 (22.05, 22.06) | 21.98-22.02 |
| mar_shoulder | -18.3 ± 9.6 | -1.0 | +9.3 | 22.20 | 3 (22.16-22.23) | 22.06-22.13 (2 of 3 break too) |
| apr_mild_sunny | -28.6 ± 26.2 | -7.6 | -14.6 | 22.21 | 3 (21.88, 22.15, 22.61) | 22.00-22.86 (2 of 3 break too) |

The seed means are now within ±0.05 K on five of seven weeks (two were before). Single seeds
still break, because a slow integral cannot correct a 7-day weather departure. The baseline is
re-aimed per seed and week on the true air. mar_shoulder still runs 0.1-0.2 K warm, with
metered electricity +9 %. Its "better" verdict comes from normalising that warm room and should
not be read as a win.

### R7 (minor, tested, not adopted): writes and stop-triggering drops

I tested holding a setpoint drop while the compressor runs whenever the new stop threshold would
be within 0.5 K or 2 K of the outlet. It cut starts to 1.72-1.76 a day and writes to 9-11 a day.
It cost 45-70 K-h of comfort (about 25-40 kWh at the comfort price), against about 5 kWh of
start cost saved, so I did not adopt it. Writes are now 12.0 a day (was 12.4).

### Results after the fixes

**Season nominal, seeds 0-2** (`rank_season_nominal_v2.txt`):

| measure | value |
|---|---|
| adjusted energy | **-6.29 / -6.43 ± 1.04 / -6.52 %** at c = 0.05 / 0.2 / 0.3, better (was -6.01 / -6.15 / -6.24) |
| normalised energy | -1.84 % (metered -1.87 %) |
| comfort | -392 K-h |
| mean air | 21.99-22.00 |
| mean abs error | 0.42 vs 0.51 K |
| starts per day | 1.8 vs 2.0-2.1 (median run 314-329 min) |
| writes per day | 12.0-12.1 |
| mean outlet while running | 30.7-30.8 vs 30.0-30.3 °C |
| max setpoint | 36-39 °C |

**Robust, seeds 0-1** (`rank_season_robust_v2.txt`): better on all 20 variants, 0 undecided,
0 worse. Adjusted at c = 0.2 ranges from -5.95 ± 4.04 (`minute_only`) and -5.96 ± 1.56
(`raw_return`) to -7.10 ± 2.23 (`loss_minus20`). No constraint is broken: mean air 21.97-22.02.

Flags:
- `cold_share` on `loss_minus20` and `sun_minus30`;
- `min_off` on `heavy_slab` (the ASSUMED minimum off-time was reached at least once).

Diagnostics:
- `flat_load`: -5.34 ± 3.63, energy -0.44 %;
- `long_outage`: -6.48 ± 2.41.

Both are better.

**Remaining weaknesses** are as in section 6, with three changes:
- the integral no longer carries a large curve error;
- no setpoint exceeds 39 °C;
- the no-room fallback now errs slightly cool rather than warm.

The cold kink (0.3 K/K below -2 °C) and the daily sun term (5 K per 100 W/m²) are fitted on
simulated seasons, so a real trial should check them against logged integral values.

Reproduce:

```
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,wc_low -s season --seeds 0-2
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,wc_low -s season --seeds 0-1 --robust
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,wc_low -s weeks --seeds 0-2
.local/lab-venv/bin/python .local/lab-results/controllers/wc_low/fix/suite.py '{}' season,r2,noroom,weeks
```

## 10. Review fixes (round 2)

The second review (seeds 3-4, `.local/lab-results/controllers/wc_low/review/r2/`) confirmed the
headline and found three major issues (R2-1..R2-3) and five minor ones. All tuning below used season
seeds 0-2 only. Harness: `.local/lab-results/controllers/wc_low/fix2/` (`suite2.py` with the
wrappers `GhiNone`, `NoFc`, `R2` = restart every 2 days without the integral; `floorheat.py`).
Official ranks: `.local/lab-results/controllers/wc_low/v3/`.

### Code changes

| change | why | effect (season seeds 0-2, adj % c=0.2) |
|---|---|---|
| **climatological sun schedule** (`clim`, on): a monthly half-sine irradiance day near 55 N (peak 70-420 W/m², sunrise/sunset by month), used when the forecast has no `ghi` | R2-1, R2-6: HA weather entities carry no irradiance | forecast without irradiance: **-5.40**, mean air 21.99-22.00 (was -3.42, 22.05-22.07) |
| the same schedule on top of the damped unit sensor when there is **no forecast at all** | R2-1 | no forecast: **-4.34**, mean air 21.98-21.99 (was -0.59, 22.06-22.09, i.e. the baseline) |
| blind start: the outdoor sensor seeds `t_meas` even when the link is down; with nothing at all, a monthly mean outdoor temperature instead of 0 °C | R2-7 | probe (link down, no forecast, -20 °C) now gives 33 °C, not 31 °C |
| `hyst` 0.8 → **1.0 K** | R2-8: fewer writes | -6.33 vs -6.38 (noise), writes 12.0 → 10.3 a day |

Tested and **not** adopted (season + weeks, seeds 0-2):
- a learning boost after a fresh start (ki x 4 or x 7 decaying over 48-72 h): season -6.38/-6.51,
  week seed means unchanged (feb 22.05/21.92/22.01, mar 22.20/22.09/22.17);
- a daily-level slope correction on the 24 h forecast mean (`s_day` 0.15, base 0.8 or 1.6), suggested
  by a regression of the daily integral on outdoor temperature (+0.17 K per K): season -6.37/-6.60
  (noise), weeks warmer (mar 22.25-22.34).

### R2-1 (major, real): the sun gain is mostly a schedule

Agreed. With the forecast irradiance replaced by the fixed climatological schedule the score is
-5.40 against -6.37 with the forecast, so day-specific irradiance adds about 1 point; the rest is a
seasonal and diurnal pre-noon lowering. The controller now uses that schedule whenever irradiance
is missing, so a met.no-only deployment keeps most of the gain and stays centred. The `sun_g` 8 K
per 100 W/m² should be read as "lower the water in the hours before the usual sunny period, more
in spring", not as a forecast-skill claim.

### R2-2 (major, real): energy is small and the water is not cooler

Agreed; reported, not fixed. Season seeds 0-2: normalised energy -1.94 % (metered -1.97 %), comfort
-378 K-h, about 4.4 of the 6.4 points. `flat_load`: energy -0.38 %, adjusted -5.07. The running
outlet is 30.7-30.9 against 30.0-30.3 °C: fewer, longer runs at higher output. **This controller is
not an answer to "the water is too hot"**; it is sun anticipation plus slower cycling, roughly
energy-neutral on a flat part-load curve. In this model lowering the water further pushes the unit
to minimum output, which costs more than the lift saves (section 2); the real unit may differ.

### R2-3 (major, disputed with evidence): warm weeks are sun heat at the 25 °C floor

The week mean-air breaks are real constraint failures and are reported as such. But the cause is
not a warm curve. `floorheat.py` splits each week's mean air into minutes when the setpoint sits at
the 25 °C floor, the compressor is off and the room is above 22.3 °C (sun heat no heating
controller can remove) and the rest:

| week, seed | controller | floor-idle-warm share | its contribution to mean air | mean air in the rest | window mean |
|---|---|---|---|---|---|
| feb_sunny_cold s0 | baseline / wc_low | 15.7 / 10.6 % | +0.22 / +0.13 K | 21.71 / 21.92 | 21.98 / 22.06 |
| feb_sunny_cold s2 | baseline / wc_low | 12.9 / 7.9 % | +0.18 / +0.07 K | 21.81 / 21.98 | 22.02 / 22.05 |
| feb_sunny_cold s3 (review seed, diagnosis only) | baseline / wc_low | 18.5 / 18.9 % | +0.27 / +0.26 K | 21.66 / 21.94 | 21.99 / 22.21 |
| mar_shoulder s0 | baseline / wc_low | 33.4 / 38.2 % | +0.54 / +0.57 K | 21.39 / 21.42 | 22.13 / 22.21 |
| oct_mild s2 | baseline / wc_low | 21.9 / 24.8 % | +0.29 / +0.26 K | 21.61 / 21.80 | 21.98 / 22.11 |

wc_low has the same or less floor overheating than the baseline. The baseline reaches 22.00 because
its per-week offset is re-aimed on the true air, which holds the other hours 0.3-0.6 K cold
(21.4-21.8 °C). wc_low holds them at 21.8-22.0. The extra metered electricity on feb_sunny_cold
seed 3 (+8 %) is the cost of not running the room 0.34 K cold for the rest of the week; normalised
to equal mean air it is +0.06 %. On the seed-3 trajectory the integral reached -5 K (its bound) by
day 3 and the room then ran 21.1-21.8 °C: the controller was repaying, not running warm. A faster
integral (learning boost above) did not centre weeks. Centring a 7-day window on sun heat would
mean running deliberately cold, which is a comfort choice, not efficiency.

### R2-4 (minor, real): thin season margins

Documented. `floor_keep` 0.7 is a comfort-level choice: it decides how much unavoidable sun heat
is repaid later. A deployment must persist the integral (`trim0`, HA RestoreEntity); without it,
restarts every 2 days give mean air 21.99/22.04/22.05 (passes, at the edge).

### R2-5 (minor): stale claims

The parameters of record are the table below; the results of record are the v3 runs.

### Parameters of record (round 2)

As in section 3 and section 9, plus: `hyst` 1.0 K; `clim` on (monthly irradiance schedule
`_CLIM` in the code); base 0.8, sp_max 39, floor_keep 0.7, sun_d 5, k_cold 0.3, t_knee -2,
sun_g 8, fc 3..6 h, kp 4, ki 0.15, i_lim 5, delta 5, quiet off.

### Results after round 2 (`v3/`)

**Season nominal, seeds 0-2** (`rank_season_nominal_v3.txt`): adjusted **-6.24 / -6.37 ± 1.08 /
-6.46 %** at c = 0.05 / 0.2 / 0.3, better. Normalised energy -1.94 % (metered -1.97 %), comfort
-378 K-h, mean air 21.99-22.00, mae 0.43 vs 0.51 K, starts 1.8-1.9 vs 2.0-2.1 a day (median run
305-340 vs 270-288 min), writes 10.3-10.4 vs 9.3-9.8 a day, running outlet 30.7-30.9 vs 30.0-30.3 °C,
max setpoint 36-39 °C. Flag `min_off` on seed 0 (ASSUMED minimum off-time reached at least once).

**Robust, seeds 0-1** (`rank_season_robust_v3.txt`): better on 20 of 20, 0 undecided, 0 worse.
Adjusted at c=0.2 from -5.88 ± 0.27 (`raw_return`) and -5.89 ± 3.28 (`minute_only`) to -7.04 ± 3.51
(`loss_minus20`, flag `cold_share`). Mean air 21.97-22.02, no constraint broken. Flags: `min_off`
on nominal, high_start_loss, shallow_outlet. Diagnostics: `flat_load` -5.07 ± 3.16 (energy
-0.38 %), `long_outage` -6.58 ± 1.68, both better.

**Weeks, seeds 0-2** (`rank_weeks_v3.txt`): better on oct_mild -41.4 ± 22.2, nov_mixed -9.0 ± 7.0,
jan_cold -2.7 ± 2.3, feb_sunny_cold -7.4 ± 0.5, mar_shoulder -19.3 ± 4.0, apr_mild_sunny -28.4 ±
28.1; undecided on dec_damp -0.4 ± 4.3. Mean-air breaks (failures) on 12 of 21 week-seed runs
(21.86-22.61), mostly sunny weeks; see R2-3. mar_shoulder is +8.9 % metered at 22.20 mean air.
feb_sunny_cold and jan_cold make slightly more starts than the baseline (break-even +10/+9 kWh per
start), still better at 0.3.
