# Setpoint rider (strategy S6)

`lab/controllers/setpoint_rider.py` (`CONTROLLER = SetpointRider`, name `setpoint_rider`). Stdlib
only. It reads nothing but the `Observation`. Self-check:
`.local/lab-venv/bin/python -m lab.controllers.setpoint_rider`.

## 1. Result in one paragraph

> **After the review (section 10)** the defaults changed (q_run 5 kW, ceiling 31 °C, a hard cap
> on every write, a start back-off, a wider stop gap, a stale-thermometer rule). Current numbers:
> season seeds 0-2 **-7.51 ± 0.79 %** adjusted, energy -4.00 %, comfort -316 K-h, starts 2.1/d
> (baseline 2.1), writes 10.0-10.4/d (max 18 on any day), mean outlet +0.55 K over the baseline;
> 20/20 mandatory variants `better`; flat_load -4.76 % with energy -1.04 %. The paragraph below
> and sections 4-5 describe the pre-review version.

Over the 2025/26 season (seeds 0-2, nominal plant) the rider uses **4.5 % less ranking energy**
than `reference_tuned` and holds the room better: mean |error| 0.44 K against 0.51 K, 308 fewer
K-hours. The adjusted score is **-7.9 ± 0.9 %** (c = 0.2 kWh per start). The verdict is `better`
at both ends of the start-cost band, with a break-even start cost of 14 kWh. It is `better` on all
20 mandatory variants (seeds 0-1) and on the three diagnostics. It makes 2.2 starts a day against
2.1 and writes the setpoint 12.7 times a day (at most 24 on any day). Its supply water is about
**0.9 K warmer** while running (mean outlet 31.0 against 30.1 °C). Two things decide the result,
and neither is "low and slow":

- **Mid-output riding.** The firmware is held at about 6-7 kW, not at its minimum. The lab's
  measured COP surface makes the minimum output 15-25 % less efficient at the same water
  temperature. Riding at the minimum, as S6 was first written, gives up about 2.7 points of the
  energy gain.
- **A learned daily heat profile** (repetitive control on the room error). It moves heat out of
  the early morning and into the afternoon and evening. This halves the house's recurring
  warm-afternoon / cold-night swing. It also buys about 0.8 K of warmer air for the compressor.

## 2. Physics and firmware facts used

All of these come from the public lab documents (UNIT_MODEL.md sections 3-4 and 7, HOUSE_MODEL.md
section 1).

- **A setpoint is a power request.** The Versati's capacity loop works on
  e = setpoint − t_ctrl:
  - e ≥ 1.0 K: output ramps up at about 0.2 kW/min;
  - 0.1 K < e < 1.0 K: output holds;
  - e ≤ 0.1 K: output ramps down, faster the larger the overshoot.

  While running, t_ctrl ≈ supply − 0.8 K and supply = return + Q / (cp·flow), so a setpoint near
  **inlet + Q / 2.02 − 0.25** puts the hold band around output Q. The supply temperature then
  follows from the slab. The controller never chooses it directly.
- **Start rule.** setpoint − t_ctrl ≥ restart_delta, with idle t_ctrl ≈ inlet − 0.8. The smallest
  kick is ceil(inlet − 0.8 + delta). In this model every start delivers 7.3 kW for 10 minutes
  whatever the gap (the measured median start). A soft start therefore cannot be shown here (see
  section 8).
- **Stop rule.** t_ctrl ≥ setpoint + 2 K for 3 minutes, or at once when a write makes that true.
  - The controller stops a block by writing a setpoint 2.3 K under its estimate of t_ctrl,
    outlet − 0.5 + 0.025·(5 − Q). That value is never below 25 °C.
  - It never rides below t_ctrl − 1.5 K, so a ride write cannot stop the unit by accident.
  - Riding at about 6 kW also sits above the surge stop band. A 120-minute surge lifts t_ctrl by
    about 3 K, and that stops a minimum-output ride (setpoint ≈ return + 1.7 K) but not a 6 kW
    ride (≈ return + 2.7 K).
- **COP against output and supply temperature.**
  - Central fit: COP(6 kW) / COP(minimum) is 1.25 at 0 °C and 1.12 at +7 °C. This is the same
    for every variant except the two part-load bounds, which give 1.18 and 1.34 at 0 °C.
  - Each +1 K of supply costs 3.2-3.7 %. The supply needed for output Q is about slab + 0.70·Q
    (loop-to-slab effectiveness 0.71 at 29 L/min). Going from 3.7 to 6 kW therefore raises the
    supply about 1.6 K, which costs about 5-6 %, against a 12-25 % COP gain.
  - So in this house the efficient block output is mid output, not the minimum. The lab bears
    this out (section 5, ablation).
- **Outdoor temperature.** COP gains 1-6 % per K of warmer air. A slab of 4.4 kWh/K plus a large
  envelope mass can move heat by many hours.
- **The room's daily swing is large and recurring.** Under `reference_tuned` the season-mean air
  error by local hour runs from −0.40 K (02-06 h) to +0.68 K (13-14 h). That cycle is about 80 %
  of the baseline's comfort K-hours. Its causes are the internal-gain profile, the sun, and the
  daily shape of the bootstrapped residual (people, cooking, and model error). Heat reaches the
  air through the slab about 9 hours later in phase at the daily period. That figure was found
  empirically (section 4) and fits the 2.2 h and 11 h time constants.

## 3. Control law

Every minute:

1. **Demand.** It is computed as

   P_dem = a0 − b·T_fc + h·(target − 22) − g_sun·GHI_fc + profile(hour) + kp·e + I.

   - T_fc and GHI_fc are the forecast means 2-10 h ahead. With no forecast, T_fc is the unit
     sensor's 24 h mean.
   - The load line is a0 = 3.7 kW and b = 0.135 kW/K (the house model's steady load at 22 °C).
   - e = target − (room − 0.0008·GHI_now) + trim. The first term corrects the thermometer's sun
     glow, and the trim is the slow aim correction of item 3.
   - I integrates ki·e and is clamped at ±3 kW.
   - P_dem may go negative, so surplus heat is booked too. Clamping it at zero made the mean room
     run 0.06-0.16 K warm.
2. **Daily profile.** 24 hourly bins hold a heat correction in kW.
   - At local hour h, the bin for hour h − 9 integrates k_prof·e0, with e0 the glow-corrected room
     error, clipped to ±1 K.
   - The bins are then kept at zero mean (the integral owns the mean) and clamped at ±2 kW.
   - The demand reads the bin of the current hour, interpolated.
   - It learns in about one to two weeks. It freezes when the room reading is missing.
3. **Mean trim.** trim += e0 / (720 h) per hour, clamped at ±0.5 K. This is a 30-day correction
   of the aim. It keeps the season's mean air within ±0.03 K of target on every variant, and it
   costs about 0.3 % of score (section 5).
4. **Heat accounting.**
   - Measured loop heat is Q = 2.02·(outlet − inlet + 0.3). It is counted only while the
     compressor runs in heat or defrost mode, and not during or within 10 minutes after hot water.
   - The balance D += (P_dem − Q)/60 is clamped at ±max(5, E/2 + 0.5) kWh.
5. **Blocks** (sigma-delta).
   - A block starts when D ≥ E/2 = 4 kWh and the unit has been off for 30 minutes or more.
   - It ends when D ≤ −4 kWh after at least 60 minutes of running, unless the demand smoothed
     over 1 h is at least max(4.5 kW, the unit's floor). In that case the run is continuous.
6. **Ride target.**
   - In a block: q = max(6 kW, floor, P_dem + D/2 h).
   - Continuous: q = max(floor, P_dem + D/2 h).
   - The setpoint is round(inlet + q/2.02 − 0.25). It is capped by a weather ceiling,
     32 + 0.5·max(0, −T_fc) °C, and kept at t_ctrl − 1.5 or above.
   - A ride write happens only when the ideal value moved by more than 0.75 K, at most every 10
     minutes, and not within 10 minutes of a defrost.
   - Downward writes are skipped during a power surge (electricity above 1.5 × its 30-minute mean).
7. **Kick.** While a block is on and the compressor is off (and not in DHW or defrost), the kick
   writes ceil(inlet − 0.8 + delta), one degree more after 4 minutes without a start.
   - If the firmware ended the run itself (surge, defrost, DHW), the kick waits until the unit has
     been off for 6 minutes.
   - Until then, if the current setpoint would let the restart rule fire, it writes a setpoint 1 K
     under the threshold.
8. **Stop and park.**
   - Stop writes max(25, floor(t_ctrl − 2.3)).
   - While idle that value is kept. It is lowered (to threshold − 1.2 K, never below 25) only when
     the restart rule comes within 0.7 K of firing.
   - So during a long link loss the firmware restarts by itself once the loop has cooled about
     3 K. That is the outage backstop: `long_outage` is `better`, −7.6 %.
9. **Write budget.** At most 44 writes in any 24 h. Ride writes are dropped first; start, stop
   and park writes always go out. The season maximum was 24 a day.

Fail-safe summary:

- Link down: no writes, and the balance holds its last heat reading.
- Room missing: the integral, trim and profile freeze, and the load line carries on.
- Forecast missing: 24 h mean of the outdoor sensor.
- DHW and defrost: no ride writes, and no heat counted from tank water.

### Parameters (defaults = tuned values)

| group | parameter | value | meaning |
|---|---|---|---|
| load | a0, b, h_tgt | 3.7 kW, 0.135 kW/K, 0.187 kW/K | load line from the public house model |
| load | lead_h, horizon_h | 2, 8 | forecast hours used: 2-10 h ahead |
| load | g_sun | 0.012 kW per W/m² | forecast sun |
| room | kp, ki, i_lim | 2.5 kW/K, 0.05 kW/(K·h), 3 kW | PI |
| room | glow | 0.0008 K per W/m² | thermometer glow correction (HOUSE_MODEL.md) |
| room | tau_mean_h, mean_lim | 720 h, 0.5 K | slow aim trim |
| profile | k_prof, prof_lead_h, prof_lim | 0.5 kW/(K·h), 9 h, 2 kW | learned daily profile |
| blocks | e_blk, d_lim | 8 kWh, 5 kWh | start/stop at ±4 kWh, balance clamp |
| blocks | min_run, min_off, q_cont, tau_c | 60 min, 30 min, 4.5 kW, 2 h | |
| ride | q_run, ride_off, ride_hyst, ride_every | 5 kW (was 6), 0.25 K, 0.75 K, 10 min | |
| ride | ceil_a, ceil_b | 31 °C (was 32), 0.5 K/K | weather ceiling |
| safety | max_writes, dhw_guard, park_high | 44 per 24 h (ride writes), 10 min, on | |
| safety | hard_writes, kick_writes | 46, 42 per 24 h | cap on every write; start requests stop at 42, the rest is kept for stops |
| safety | kick_fail, kick_back | 15 min, 15 min doubling to 240 | failed start request and its back-off |
| safety | stop_gap | 2.8 K (was 2.3) | stop write floor(t_ctrl_est − gap), confirmed after 5 min |
| safety | room_stale_min | 180 min | older thermometer counts as missing |
| blocks | q_exit, tau_mean_min_h | 0, 720 h | continuous-mode exit hysteresis and initial trim speed (both tested, both left off; section 10) |

## 4. Tuning record (season, seeds 0-2 only, nominal plant)

Adjusted score at c = 0.2 kWh per start, paired against `reference_tuned`, as a % of its window
electricity. Each step keeps the previous ones.

| step | change | adj % | energy % | comfort K-h | mean air | note |
|---|---|---|---|---|---|---|
| v1 | first version: kp 1.5, ki 0.3, demand clamped at 0, q_run 6 | −0.8 | −2.9 | +150 | 22.06 ! | mean air breaks ±0.05 |
| 2 | let demand go negative into the balance | −0.2 | −2.6 | +188 | 22.06 ! | |
| 3 | stronger PI (kp 3-4, ki 0.3-0.6) | +0.6..+3.7 | | +231..+474 | 22.07-22.14 ! | worse: the slab lags; strong integral action hunts |
| 4 | ki 0.1, aim −0.05 | −1.6 | −3.1 | +85 | 21.97 | |
| 5 | forecast sun g_sun 0.008-0.012, 168 h aim trim instead of the fixed aim | −2.2 | −2.9 | +32 | 22.00 | |
| 6 | tried: freeze the integral on sunny warm minutes | −2.1..−2.8 | | −56..+30 | 22.04-22.20 ! | better comfort, mean air breaks; dropped |
| 7 | tried: q_run 4/5/7/8, e_blk 4/6/10, q_cont, tau_c, ride_hyst | −1.1..−2.2 | | | | flat; e_blk 4 adds starts (break-even c 0.1) |
| 8 | **daily profile**, k 0.5, lead 2-3 h | −1.4..−0.6 | | +70..+126 | | wrong phase: worse |
| 9 | profile lead 5 / 6 / 8 / 10 / 12 h | −2.8 / −3.7 / −5.0 / −4.6 / −2.9 | −3.5 at 8 h | −144 at 8 h | 22.00 | phase about 8-10 h |
| 10 | forecast window 2-10 h, kp 2.5, ki 0.05 | −6.7 | −3.9 | −252 | 22.00 | |
| 11 | profile lead 9 h | −6.8 | −4.2 | −236 | 21.99 | |
| 12 | balance clamp d_lim 6 → 5 | −7.4 | −4.5 | −272 | 22.00 | stops overwound balances after sunny spells |
| 13 | high park (outage backstop), min-off guard, DHW guard 10 min | −7.4 | −4.5 | −272 | 22.00 | neutral |
| 14 | aim trim 168 h → 720 h (final) | **−7.9** | **−4.5** | **−308** | 22.00 | no trim: −8.2 % but mean air up to 22.04 on `raw_return` |

Ablations of the final configuration (season, seeds 0-2):

| ablation | adj % | energy % | comfort K-h | starts/d |
|---|---|---|---|---|
| final | −7.9 ± 0.9 | −4.5 | −308 | 2.2 |
| no daily profile (k_prof 0) | −4.9 ± 0.7 | −3.6 | −150 | 2.6 |
| no forecast sun (g_sun 0) | −5.9 ± 0.6 | −4.2 | −180 | 2.5 |
| no proportional room term (kp 0) | −0.3 ± 2.4 | −4.2 | +334 | 2.3 |
| **ride at the minimum output** (q_run 4, ride_off 0.7, so the band sits on the floor) | −5.3 ± 0.5 | **−1.8** | −294 | 1.9 |
| ride at 5 kW (q_run 5, ride_off 0.7) | −6.3 ± 0.3 | −2.8 | −306 | 2.0 |
| no slow trim (tau_mean_h 0) | −8.2 ± 0.9 | −4.6 | −330 | 2.2 |

(The five ablations between the first and last rows were run on the 168 h-trim version. That
version scores −7.4 ± 0.7 %, energy −4.5 %, −272 K-h, so read them against that, not against the
final row.)

Where the energy comes from (seed 0, season, per-minute CSV):

- The heat-weighted outdoor temperature while heating is −2.8 °C against −3.6 °C for the
  baseline. That is worth about 2.5-3 % of COP and comes from the profile shifting heat.
- Of the heat delivered, 41 % comes at 4-6 kW and 46 % at 6-8 kW (baseline 53 % and 30 %).
- The mean supply while heating is 31.5 °C against 30.8 °C.

The error by local hour shrinks from −0.40…+0.68 K to −0.36…+0.44 K. The night-time cold is the
part that improved most: −0.14 K at 00-04 h against −0.40 K.

## 5. Results

### Season, nominal plant, seeds 0-2

| | reference_tuned | setpoint_rider |
|---|---|---|
| electricity, kWh/day (seeds 0 / 1 / 2) | 27.06 / 26.19 / 26.07 | 25.83 / 24.94 / 24.91 |
| normalised energy, kWh/day | 26.81 / 25.96 / 25.80 | 25.60 / 24.75 / 24.66 |
| space-heating COP | 2.89-2.91 | 3.04-3.06 |
| starts/day | 2.0-2.1 | 2.1-2.2 |
| run median, min | 270-288 | 271-320 |
| mean outlet while running, °C | 30.0-30.3 | 30.9-31.1 |
| mean setpoint, °C | 28.3-28.7 | 28.9-29.2 |
| mean air, °C | 22.00-22.01 | 22.00 |
| mean \|error\|, K | 0.49-0.53 | 0.43-0.45 |
| K-h below −0.5 / above +0.5 | 204-230 / 516-596 | 223-248 / 330-394 |
| writes/day | 9.3-9.8 | 12.7-12.9 |
| defrosts | 989-1021 | 1004-1028 |

Ranking line: **adj −7.89 % ± 0.94 (c = 0.05: −7.97, c = 0.3: −7.83), break-even c 14.4 kWh,
`better`; energy −4.54 %, comfort −308 K-h, metered −4.58 %, starts 2.2 vs 2.1, air 22.00, mae
0.44 vs 0.51.** No flags. On seed 0 the most writes on any day was 24 (p95 19), the most starts
on any day was 5, and 5 of 408 runs were under 30 minutes.

### Mandatory variants, seeds 0-1 (adj % at c = 0.2 ± 90 %, c = 0.05 / 0.3, verdict)

| variant | adj % | c 0.05 / 0.3 | break-even c | verdict | energy % | starts/d (base) | air | mae (base) |
|---|---|---|---|---|---|---|---|---|
| nominal | −7.82 ± 3.42 | −7.91 / −7.76 | 13.2 | better | −4.61 | 2.2 (2.1) | 22.00 | 0.44 (0.51) |
| partload_lo | −6.83 ± 2.52 | −6.93 / −6.75 | 9.7 | better | −3.48 | 2.3 (2.1) | 22.00 | 0.44 (0.51) |
| partload_hi | −9.56 ± 3.61 | −9.69 / −9.48 | 11.8 | better | −6.40 | 2.3 (2.0) | 22.00 | 0.44 (0.51) |
| legacy_cop | −5.83 ± 2.60 | −5.92 / −5.76 | 9.0 | better | −2.50 | 2.2 (2.1) | 22.00 | 0.44 (0.51) |
| high_start_loss | −7.71 ± 2.67 | −7.80 / −7.65 | 13.5 | better | −4.51 | 2.2 (2.1) | 22.00 | 0.44 (0.51) |
| sluggish | −7.88 ± 2.94 | −7.97 / −7.81 | 12.1 | better | −4.67 | 2.2 (2.0) | 22.00 | 0.44 (0.51) |
| raw_return | −6.01 ± 2.53 | −6.18 / −5.89 | 5.5 | better | −3.89 | 2.4 (2.1) | 22.03 | 0.46 (0.51) |
| minute_only | −7.19 ± 6.14 | −7.21 / −7.18 | 77 | better | −3.30 | 2.0 (2.0) | 22.00 | 0.43 (0.52) |
| low_flow | −7.01 ± 1.21 | −7.11 / −6.94 | 10.9 | better | −4.19 | 2.4 (2.2) | 22.00 | 0.45 (0.51) |
| high_flow | −8.58 ± 3.55 | −8.69 / −8.50 | 11.4 | better | −4.98 | 2.1 (1.9) | 22.00 | 0.44 (0.52) |
| loss_minus20 | −7.47 ± 0.67 | −7.57 / −7.39 | 10.5 | better | −5.08 | 2.4 (2.2) | 22.01 | 0.48 (0.53) |
| steep_outlet | −7.96 ± 2.86 | −8.05 / −7.91 | 14.2 | better | −4.57 | 2.2 (2.1) | 22.00 | 0.44 (0.51) |
| shallow_outlet | −8.08 ± 3.13 | −8.20 / −8.00 | 10.5 | better | −4.95 | 2.2 (2.0) | 22.00 | 0.44 (0.51) |
| frost_melt_lo | −8.03 ± 3.30 | −8.12 / −7.98 | 14.9 | better | −4.71 | 2.2 (2.1) | 22.00 | 0.44 (0.51) |
| frost_melt_hi | −7.99 ± 2.46 | −8.11 / −7.91 | 10.3 | better | −4.84 | 2.2 (2.0) | 22.00 | 0.44 (0.51) |
| light_slab | −7.46 ± 3.59 | −7.47 / −7.46 | 121 | better | −4.50 | 2.3 (2.3) | 21.98 | 0.42 (0.49) |
| heavy_slab | −8.36 ± 2.82 | −8.48 / −8.28 | 10.7 | better | −4.61 | 2.2 (2.0) | 22.00 | 0.45 (0.53) |
| sun_plus30 | −7.94 ± 2.00 | −8.04 / −7.88 | 12.9 | better | −4.14 | 2.2 (2.0) | 22.01 | 0.45 (0.53) |
| sun_minus30 | −7.43 ± 3.25 | −7.56 / −7.34 | 8.9 | better | −4.84 | 2.3 (2.1) | 22.00 | 0.46 (0.52) |
| forecast_pessimistic | −7.57 ± 2.94 | −7.66 / −7.51 | 12.8 | better | −4.55 | 2.2 (2.1) | 22.00 | 0.45 (0.51) |

All 20 are `better` and no constraint is broken. `loss_minus20` and `sun_minus30` carry the
`cold_share` flag: more than half of their advantage comes from days below −4 °C. Diagnostics
(seeds 0-1):

- `flat_load` −3.78 ± 2.94 (energy −0.29 %, so almost all of it is comfort);
- `frost_no_melt` −8.12 ± 2.84;
- `long_outage` −7.58 ± 0.04.

All three are `better`.

### Weeks, nominal, seeds 0-2 (diagnostic)

| week | adj % | verdict | energy % | comfort K-h | starts/d (base) | air | mae (base) | flags / violations |
|---|---|---|---|---|---|---|---|---|
| oct_mild | −33.7 ± 19.2 | better | −6.9 | −27 | 1.9 (1.9) | 22.09 | 0.50 (0.66) | runs_lt_15min, mean air 22.08 / 22.16 |
| nov_mixed | −8.1 ± 3.8 | better | −3.9 | −11 | 3.9 (3.2) | 22.07 | 0.29 (0.36) | mean air 22.06 / 22.10 |
| dec_damp | −2.3 ± 1.8 | better | −3.7 | +3 | 3.5 (2.5) | 22.00 | 0.29 (0.28) | runs_lt_15min |
| jan_cold | −3.2 ± 2.7 | better | −2.6 | −7 | 2.3 (1.2) | 22.02 | 0.44 (0.48) | cold_share, mean air 22.09 |
| feb_sunny_cold | −6.3 ± 2.9 | better | −3.4 | −17 | 2.3 (1.3) | 22.05 | 0.50 (0.60) | cold_share, runs_lt_15min, mean air 22.08 |
| mar_shoulder | −16.1 ± 8.0 | better | −5.2 | −15 | 1.7 (1.6) | 22.17 | 0.90 (0.99) | runs_lt_15min, mean air 22.08 / 22.20 / 22.25 |
| apr_mild_sunny | −23.1 ± 40.5 | undecided | −5.7 | −18 | 0.9 (1.1) | 22.35 | 0.95 (1.06) | mean air 22.20 / 22.86 |

The rider wins energy and comfort in every week. In most weeks one or more seeds break the
weekly ±0.05 K mean-air constraint. That is structural, not tuning:

- The baseline is re-aimed per week and seed by a secant search on the true mean air. The rider
  starts each week with an empty profile, a zero integral and a zero trim, straight after a
  warm-up under `reference`.
- In sunny weeks the room overheats with the heating off, which no controller can undo within
  the week.

The `runs_lt_15min` flags come from runs cut short by exogenous hot water right after a start,
and from a run carried over from the warm-up at the window start. With about 25 runs a week, two
such runs pass 5 %.

## 6. Robustness and deployability

- **Online adaptation, not hard-coding.** The hard-coded house knowledge is the public load line,
  the minimum-output line, the glow coefficient and the sensor offsets. The integral, the 30-day
  trim and the daily profile adapt everything else.
- **Every mandatory variant passes, with similar margins.** That includes ±20 % loss, ±30 % sun,
  slab mass and three different flows.
- **Writes.** 12-13 a day on average and 24 at most, against a budget of 48. The controller caps
  itself at 44 per rolling 24 h.
- **Inputs.** Only what Home Assistant shows: room thermometer, outlet, inlet, setpoint,
  restart_delta, compressor flag, mode, metered power (used only to spot surges), the forecast
  and the local clock. It never touches restart_delta, quiet mode or heating_enabled, so it raises
  no `restart_delta`, `quiet` or `heating_off` flag. Setpoints stay within 25-37 °C.

## 7. Known weaknesses

- **Warmer water than the baseline.** The mean outlet while running is +0.9 K, and 18.5 % of
  running minutes draw more than 2.5 kW (13 % for the baseline). This goes against the owner's
  wish for cooler water. The rider wins because, in this unit's measured COP surface, mid output
  beats the cooler water that minimum output would allow. That trade rests on the part-load COP
  data:
  - it holds on both `partload_lo` and `partload_hi`;
  - under `flat_load` (rejected by the data) the energy gain falls to −0.3 %.

  The two-hold field test proposed in UNIT_MODEL.md 7.2 would settle it.
- **The profile is most of the comfort gain, and it rests on the residual's daily shape.** About
  half the score is comfort. It comes from cancelling a recurring daily swing that, in archive
  scenarios, partly reflects the recorded residual days (people, cooking, and house-model
  error). If the real house's daily pattern is weaker or shifted, the profile learns a smaller
  correction. The 9-hour phase lag was found by sweeping, not identified on the real house.
- **The profile runs at its ±2 kW limit in spring** (a square wave: heat from 13 h to 24 h, none
  from 02 h to 12 h). In practice it is then a learned fixed schedule. A holiday or a change of
  habits takes about a week to relearn.
- **The mean air is held only on average over weeks.** It is fine over the season (21.98-22.03
  on every variant), but single weeks miss ±0.05 K, especially sunny ones and right after the
  controller takes over.
- **Slightly more starts in damp mild weather.** In `dec_damp` it makes 3.5 a day against 2.5
  (break-even start cost 0.85 kWh). Over the season it is 2.2 against 2.1.
- **Heat accounting assumes 29 L/min.** At 25 or 33 L/min the measured heat is off by ±14 %. The
  integral absorbs this, and `low_flow` and `high_flow` both pass.
- **Long link loss while parked.** The backstop restarts the unit only after the loop has cooled
  about 3 K, and the firmware then holds a fixed setpoint with a 4-6 K hysteresis. Comfort would
  sag, but heat does not stop.
- **Soft start does nothing in the lab.** The model's starts always deliver 7.3 kW for 10
  minutes, so the "smallest gap" kick only avoids an extra ramp-up. Whether a small gap really
  starts the real compressor slower (research hypothesis H1) is untested here.

## 8. Simulator observations

- **The start output is fixed.** Every start is 3.6 K of delta-T (7.3 kW) for 10 minutes,
  whatever the setpoint gap. That is the measured median start, but it makes the "soft start"
  half of S6 unmeasurable.
- **The `min_off` flag can fire in the run-out.** The minimum-off counter (`unit_counters.
  minoff_wait_min`) also counts run-out minutes. When `reference` takes over at the window end
  and writes 31 °C right after the candidate's last run stopped, the flag is raised (seen once on
  `light_slab`, 2 minutes). Nothing the candidate did caused it.
- **`runs_lt_15min` can fire from a run that was not the candidate's.** In weeks, a run still
  going from the warm-up and ending in the first minutes of the window counts as a short run of
  the candidate.
- **Weekly mean-air checks favour the per-week tuned baseline.** No causal feedback controller
  can meet ±0.05 K in a sunny week that begins after a warm-up under another controller. Weeks
  are best read as energy and comfort pairs.
- **The comfort price makes daily-profile learning very valuable.** Comfort is about a quarter of
  the score, and about 80 % of the baseline's comfort K-hours come from a recurring daily cycle.
  Whether that cycle is as strong in the real house as in the bootstrapped residual days is the
  most important thing to check before trusting the size of this result. The out-of-pattern
  house test proposed in SIMULATOR.md 6.1 would also test it.
- No gaming was found or used. The controller does not shape the heat left in the slab at the
  window end. Its end-of-window behaviour is the same as at any other time.

## 10. Review fixes (2026-11-07)

An adversarial review (held-out seeds 3-4, results in `review/`) confirmed the result and raised
three major and six minor issues. Fix runs are in `.local/lab-results/controllers/setpoint_rider/fix/`;
all tuning used seeds 0-2 only.

### R1 (major, fixed): essential writes bypassed the write budget

Real. Start requests, stops, park and minimum-off writes skipped the 44/24 h check, and the start
request was re-ceiled every minute from a noisy inlet, so a unit that never answers a start
request (lockout, fault, a longer real minimum-off time) could get hundreds of writes a day.
Changes:

- every write now goes through one rolling 24 h log with a **hard cap of 46**; ride writes stop at
  44, start requests at 42, and the last slots are kept for stop writes (a stop is the write that
  must never be refused);
- a start request is computed **once per attempt** (no re-rounding on a noisy inlet) and bumped
  by 1 K once after 4 minutes. With no start after 15 minutes the attempt counts as failed; the
  setpoint is left where it is (the firmware's own restart rule can still fire) and the next
  attempt waits 15, 30, 60 ... up to 240 minutes;
- the minimum-off guard writes at most once per firmware-ended run.

Self-check case 7: a unit that never starts, inlet quantised to 0.1 K with 0.4 K noise and
slowly cooling, gives 37 writes in 3 days (the reviewer measured 610 a day before the fix).
Season writes fell from 12.7 to 10.0-10.4 a day, at most 18 on any day (seed 0).

### R2 (major, partly fixed): the energy gain leaned on the part-load COP surface; warmer water

Real. Season sweep, seeds 0-2 (adj % at c = 0.2 / energy %):

| q_run, ceil_a | nominal | flat_load | starts/d | mean outlet running (nominal) |
|---|---|---|---|---|
| 6 kW, 32 °C (old) | -7.74 / -4.64 | -3.68 / -0.32 | 2.3 | 30.88-31.09 |
| 5.5 kW, 32 °C | -7.84 / -4.46 | -4.01 / -0.48 | 2.2 | 30.78-31.00 |
| **5 kW, 31 °C (new)** | **-7.51 / -4.00** | **-4.76 / -1.04** | **2.1** | **30.57-30.79** |
| 5 kW, 30 °C | -6.76 / -3.48 | -4.94 / -1.45 | 2.1 | |
| 4.5 kW, 31 °C | -7.23 / -3.78 | -4.82 / -1.07 | 2.1 | |
| 4 kW, 32 °C | -7.04 / -3.47 | -4.44 / -0.74 | 2.1 | |

(reference_tuned outlet 30.04-30.27 °C.) The new default gives up 0.23 points in the nominal
plant to gain 1.1 points under flat_load. Energy is now negative even without any part-load COP
benefit, the starts match the baseline and the water is 0.5 K (was 0.9 K) warmer than the
baseline's. The rest of the warmer water is the ride itself: in blocks it holds the compressor
at about 5 kW for a shorter run instead of letting it fall to the floor. Whether mid output
really beats the minimum on the real unit still needs an A/B check (a few days at q_run 5 vs a
floor ride, same weather band, compare the metered COP). The result should be read as
"comfort + a COP surface that is at least flat".

### R3 (major, investigated; partly disagree): weeks weaker, mean air off, cold-week starts

- **Cold-week starts.** The rider does not lose continuous mode through DHW or defrost: run
  traces for jan_cold seed 0 show two controller stops a day, at about 03:00 and about 12:00.
  The learned daily profile takes up to 2 kW out of 02-12 h, so the smoothed demand drops below
  4.5 kW and the block logic ends the run on a heat surplus while the room is above target. This
  is the design working. Holding continuous mode longer (`q_exit`, exit hysteresis below the
  entry level) does cut starts but costs energy because the unit then runs at its floor:
  jan_cold 2.3 / 2.2 / 2.0 / 1.6 starts a day for q_exit 0 / 0.5 / 1 / 2 kW, with energy
  -2.43 / -1.98 / -1.40 / +0.12 %; feb_sunny_cold -3.80 / -3.38 / -2.81 / -1.23 %. The break-even
  start cost of the extra starts is about 1.5 kWh, five times the top of the ranking's band, so
  `q_exit` stays 0. The new q_run 5 brings season starts to 2.1 (baseline 2.1) and jan_cold to
  2.1 (was 2.3) / dec_damp 3.1 (was 3.5) a day against 1.2 / 2.5.
- **Weekly mean air.** A faster initial trim (time constant growing from 48 or 120 h to 720 h)
  was tested: weekly mean |mean air − 22| 0.117 K (default), 0.104 (48 h), 0.103 (120 h), with
  breaks in 15, 11 and 13 of 21 week-seeds, but adjusted scores fell (mar_shoulder comfort -14
  → -4 K-h, jan_cold energy -2.43 → -1.95 %) and the season got no better (-7.71 / -7.65 vs
  -7.74). The baseline itself is off by 0.069 K on average and breaks 5 of 21 even though it is
  re-aimed per week and per seed on the true air, which a causal controller cannot do; in the
  mild sunny weeks it reads 22.13 / 22.86 with the heat mostly off. `tau_mean_min_h` stays at
  720 h. Weekly mean-air breaks remain (structural, see section 8).
- **Metered electricity higher in some weeks.** That is the heat left in the slab when the week's
  mean air is above target; the ranking's normalisation is the right measure. It falls with q_run 5
  on feb_sunny_cold (+2.2 % seeds 3-4 before; -0.98 % seeds 0-2 now) but not on mar/oct.

Weeks now (seeds 0-2, adj % at c = 0.2 / energy % / starts vs baseline):

| week | adj % | energy % | starts/d | verdict |
|---|---|---|---|---|
| oct_mild | -31.97 ± 16.6 | -5.97 | 2.0 vs 1.9 | better |
| nov_mixed | -6.33 ± 3.6 | -2.20 | 3.6 vs 3.2 | better |
| dec_damp | -0.88 ± 3.2 | -2.32 | 3.1 vs 2.5 | undecided (was better, -2.30) |
| jan_cold | -2.34 ± 1.8 | -1.81 | 2.1 vs 1.2 | better |
| feb_sunny_cold | -5.88 ± 3.7 | -3.02 | 2.2 vs 1.3 | better |
| mar_shoulder | -14.01 ± 2.5 | -3.55 | 1.7 vs 1.6 | better |
| apr_mild_sunny | -21.52 ± 38.9 | -5.58 | 0.9 vs 1.1 | undecided |

Every week still has at least one seed outside ±0.05 K mean air (dec_damp and jan_cold one seed each, 21.95 and 22.09); runs_lt_15min flags as before.

### Minor issues

- **R4 glow correction** (not changed). The 0.8 mK per W/m² comes from the public house fit.
  Learning it online needs idle sunny days with a flat slab; that is a reasonable deployment
  step but was not built. A glow ±50 % variant is a simulator request.
- **R5 profile is a learned schedule** (not changed). Agreed; the synthetic_dist result the
  reviewer ran (-6.53 %) shows it is not only bootstrapped pattern.
- **R6 long outage while riding** (accepted, documented). No write is possible during an outage,
  so the last ride setpoint stays; the ceiling cut to 31 °C at 0 °C lowers that fallback by 1 K.
- **R7 stop margin** (fixed). Stops write floor(t_ctrl_est − 2.8) and, if the compressor is
  still on in heat mode 5 minutes later, write again 1 K lower (at most twice). In practice the
  firmware holds t_ctrl about 0.1 K under the setpoint, so stop writes are setpoint − 3 or − 4 K.
- **R8 stale thermometer** (fixed). room_age_min > 180 counts as missing (integral, trim and
  profile freeze). The reviewer's frozen-thermometer test (4 days from day 80, seed 0): true air
  mean 22.31 / max 23.66 against 22.14 / 23.14 without the fault (before the fix on seed 3:
  22.77 / 23.61 against 22.19).
- **R9** agreed (simulator limitation).

### Current results (defaults above)

- Season nominal, seeds 0-2: -7.51 ± 0.79 % (c = 0.05 -7.54, c = 0.3 -7.49, break-even 40 kWh),
  better; energy -4.00 %, metered -4.07 %, comfort -316 K-h, mae 0.44 vs 0.51 K, mean air 21.99;
  starts 2.1 vs 2.1/d; writes 10.0-10.4/d; mean outlet running 30.6-30.8 vs 30.0-30.3 °C; COP
  3.02-3.04 vs 2.89-2.91.
- Mandatory variants, seeds 0-1: 20/20 better, no constraint breaks. Lowest legacy_cop -5.82,
  raw_return -5.67, low_flow -6.12, loss_minus20 -6.35, partload_lo -6.44; highest partload_hi
  -8.90, heavy_slab -8.04. cold_share flag on loss_minus20 and sun_minus30 (information only).

## 11. Review fixes, round 2 (2026-11-07)

### B1 (major, fixed): a stop decided during hot water wrote a park setpoint from tank water

The block stop runs before the mode check, and `_stop()` computed the park value from the
outlet whenever the compressor was on, also in mode `dhw`, when the outlet shows tank water at
45-54 °C. The reviewer saw 44 °C written on seed 3 (sparse_thermometer) and 34-36 °C on others.
After a link drop that request would have survived the hot-water cycle as a hot space-heating
setpoint. Fix:

- the park comes from the outlet only in mode `heat` and past the 10-minute DHW guard;
  otherwise from `t_loop`, the last control-sensor estimate taken under those same conditions
  (or 25 °C when there is none);
- a stop is never written above the current setpoint (`park = min(park, floor(setpoint))`),
  so a stop can only lower the request;
- the "stop did not take, write 1 K lower" retry also waits for the DHW guard;
- self-check 8 in the module drives a block end during DHW with 48 °C on the outlet and asserts
  that no write exceeds the riding setpoint.

Check on seed 3 (not a tuning seed; nominal, sparse_thermometer, partload_lo): highest setpoint
37 °C, no setpoint_range flag, no setpoint change at all while the unit is in DHW. Seeds 0-2 and
the robust set are unchanged to the second decimal (the bug only fired on rare DHW-timed stops).

### C1 (major, fixed): stale claim numbers

The result block now reports the current code (q_run 5 kW, ceiling 31 + 0.5·max(0, −T) °C):
-7.51 % on seeds 0-2, not the pre-review -7.89 %.

### P1 (major, accepted as a model dependency; option documented, default kept)

Agreed that the energy gain rests on the part-load COP surface and the per-running-hour p0, and
that the water runs warmer (mean outlet while running 30.6-30.8 vs 30.0-30.3 °C). The reviewer's
code option, a lower weather ceiling, was swept (season, seeds 0-2 nominal; seeds 0-1 variants):

| setting | nominal adj % | energy % | outlet °C | flat_load adj / energy % | legacy_cop adj / energy % |
|---|---|---|---|---|---|
| default (q_run 5, ceil_a 31) | -7.51 ± 0.79 | -4.00 | 30.6-30.8 | -4.76 / -1.10 | -5.82 / -2.38 |
| ceil_a 30 | -6.76 ± 1.05 | -3.48 | 30.4-30.6 | -4.89 / -1.52 | -5.38 / -2.26 |
| ceil_a 29 | – | – | – | -4.72 / -2.04 | -4.39 / -2.00 |
| ceil_a 30, ceil_b 0.6 | -6.76 ± 1.23 | -3.43 | 30.4-30.6 | – | – |
| q_run 4.5 | -7.24 ± 0.66 | -3.74 | 30.6-30.8 | – | – |

A lower ceiling buys 0.2 K cooler water and a little energy under flat_load, but it costs comfort
everywhere (the ceiling clips the profile's evening heat) and 0.75 points on the nominal plant.
No setting brings the water down to the baseline's without giving up most of the gain, because
the warmer water is the ride itself (a short block at ~5 kW instead of a long one at the floor).
The defaults stay. For deployment: start with `ceil_a 30` if the owner wants the cooler-water
side, and run the A/B test from section 10 (a few days at q_run 5 against a floor ride in the
same weather band, metered COP) before relying on the mid-output gain.

### Minor (W1, D1, D2, M1, S1): not changed

- W1 weeks: the seeds 0-2 weeks are identical to section 10 (better on 5, undecided on dec_damp
  and apr_mild_sunny); the cold-week start increase and its q_exit trade-off are in R3.
- D1 missing forecast / sun: mean air 21.946-21.948 on the reviewer's seed 3 runs, just outside
  ±0.05 K, still better on energy. A sun proxy from PV or the outdoor sensor is a deployment item.
- D2 no thermometer: runs about 0.4 K warm (safe side). Noisy room: 15.6 writes/d, under the cap;
  the 42 °C write the reviewer saw there was B1 and is gone.
- M1 none needed; S1 the ride's hold band is a model assumption, to be logged on the real unit.

### Results after round 2 (current code)

- Season nominal seeds 0-2: -7.51 ± 0.79 % (c = 0.05 -7.54, c = 0.3 -7.49, break-even 40 kWh),
  better; energy -4.00 %, metered -4.07 %, comfort -316 K-h, mae 0.44 vs 0.51 K, mean air 21.99;
  starts 2.1 vs 2.1/d; writes 9.9-10.4/d; mean outlet running 30.6-30.8 vs 30.0-30.3 °C; COP
  3.02-3.04 vs 2.89-2.91; highest setpoint 36-37 °C.
- Mandatory variants seeds 0-1: 20/20 better, no constraint breaks; lowest raw_return -5.67,
  legacy_cop -5.82, low_flow -6.12, loss_minus20 -6.30; highest partload_hi -8.90.
- Results: `.local/lab-results/controllers/setpoint_rider/review2/` (sweep/, flat/, robust/,
  weeks/, b1check/).

## 9. Reproduce

```
.local/lab-venv/bin/python -m lab.controllers.setpoint_rider
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,setpoint_rider -s season --seeds 0-2
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,setpoint_rider -s season --seeds 0-1 --robust
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,setpoint_rider -s weeks --seeds 0-2
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,setpoint_rider -s season --seeds 0-1 --variant flat_load,frost_no_melt,long_outage
```

Private result files are in `.local/lab-results/controllers/setpoint_rider/`:

- `final2/`: nominal, weeks and diagnostics;
- `trim/`: mandatory variants at the final trim;
- `final_csv/`: seed-0 per-minute CSVs.
- `fix/`: review fixes (nominal/, robust/, weeks/, the q_run, q_exit and trim sweeps, frozen/).
