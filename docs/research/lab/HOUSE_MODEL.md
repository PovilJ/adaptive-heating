# Lab house model: underfloor loop, slab, room and envelope

`lab/sim/house.py` simulates the heated house at a 1-minute step. It takes the heat (or the supply
temperature and flow) that the heat pump puts into the floor loop, the weather and the gains. It
returns the loop return temperature, which goes back to the unit model (`lab/sim/unit.py`), and the
living-room thermometer reading, which a controller sees.

The model is grey-box: a small network of thermal capacities and conductances whose values are
identified from this house's data. It was built from the measured data and physics only. It does
not use the Home Assistant integration's controller code or model documents. The identification is
`lab/sim/house_ident.py`, and the input preparation is `lab/sim/house_prep.py`. Their outputs are
private and live in `.local/lab-results/house/`. The residual-heat series is
`.local/lab-data/disturbance_minute.csv`.

Data: the 1-minute grid described in [data.md](data.md), and the hourly long-term statistics for
the deep-cold weeks of January 2026. The periods are the same as in [UNIT_MODEL.md](UNIT_MODEL.md):

| block | dates (2026) | what |
|---|---|---|
| A0 | Feb 9 - Feb 14 | cold week (-19 to +2 °C), just before a 10-day Modbus outage |
| A | Feb 26 - May 6 | legacy controller, late winter and spring |
| F | Sep 25 - Oct 8 | heating off, room floating (pump not serving the floor) |
| C | Oct 9 - Nov 2 | current season (C1 old bridge, C2 new bridge) |
| hold_A, hold_C | Mar 16-20, Nov 2-6 | **held out** (never in any fit) |
| season (hourly) | Oct 2025 - May 2026 | hourly electricity, room, ERA5 weather; Jan 12-26 **held out** |

## 1. Summary

| item | value | evidence |
|---|---|---|
| Structure | loop water (3 segments) -> slab -> room air/furniture <-> envelope -> outdoors; air -> outdoors directly; slab -> ground; solar on three facades; internal gain with a daily profile; thermometer with a sun "glow" term | multi-step comparison of 14 structures (section 4) |
| Total heat-loss coefficient | **0.187 kW/K** seen from the room (0.111 to outdoors + 0.076 through the slab to a 10 °C ground node) | joint fit; variants 0.147-0.224 |
| Steady heat to hold 22 °C (no sun) | 6.4 kW at -20 °C, 5.0 at -10, 3.7 at 0, 2.35 at +10 | `steady_heat()` |
| Slab capacity | **4.4 kWh/K** (variants 3.1-5.7) | fit |
| Loop -> slab | 2.5 kW/K; steady effectiveness 0.71 at 29 L/min, so return = slab + 0.29 x (supply - slab) | return-temperature errors |
| Slab -> room | 0.43 kW/K (variants 0.21-0.59) | |
| Room air + furniture | 4.3 kWh/K; envelope/heavy internal mass 74 kWh/K, coupled 1.35 kW/K | |
| Time constants | 1.4, 1.4, 3 and 6 min (loop), 2.2 h, 11 h, 450 h | eigenvalues |
| Solar apertures (effective m²) | south 2.7, east 6.4, west 3.7 (no extra horizontal term) | fit |
| Internal gain | 0.31 kW mean, daily profile ±0.35 kW | fit |
| Thermometer | no lag (the fit drives it below 1 min); glow 0.8 mK per W/m² of global irradiance, about 0.4 K in full sun | section 4 |
| Room forecast RMSE, held-out minute data | **1 h 0.18 K, 6 h 0.29-0.33 K, 24 h 0.41-0.42 K** | section 5 |
| Season (hourly) check, held-out 2 weeks at -8 to -16 °C | 24 h RMSE 0.38 K; 14-day free run RMSE 0.42 K (bias -0.10 K) | section 6 |
| Daily energy error (heat the model needs vs heat supplied) | -1 % below -5 °C (38 days), +0.5 % at -5..0 °C, **+17-21 % in March-April**, -3 to -7 % in October-November | sections 6, 7 |

The **flow scaling** from the unit stage carries through. Heat into the loop is measured as
cp x 29 L/min x delta-T, so every heat-related house number (capacities, conductances, apertures,
gains) scales with the assumed flow. `flow_scaled(p, 25)` and `flow_scaled(p, 33)` pair the house
with the unit model's `low_flow` and `high_flow` variants. Temperatures are unchanged.

## 2. Inputs prepared from the data

- **Heat into the loop** (`q_loop`): cp x 29 L/min x (outlet + 0.30 - inlet). The 0.30 K is the
  unit stage's idle sensor offset.
  - It is zero while the 3-way valve is on the tank (hot water and the 7 minutes after).
  - During defrost it is negative, as measured.
  - In Versati link gaps the heat is estimated from the metered electricity with the unit model's
    steady COP. Those minutes are flagged, and forecast windows with more than 15 of them are not
    scored.
- **Return** (`ret`): the inlet sensor. It is used only in heating mode (in the summer mode the
  pump does not serve the floor and the inlet reads plant-room water at 5-10 K above the room) and
  never within 15 minutes after hot water (tank-coil water).
- **Room**: the controllers' living-room sensor. Until 22 Oct it was the old device with 0.2 K
  steps, after that the new device with 0.1 K steps. Both report on change only.
- **Weather**: ERA5 2 m temperature; facade irradiance from Open-Meteo GHI/DHI/DNI and the sun
  position (isotropic sky, albedo 0.2, 0.6 on snow), as built in the data stage.
- **Excluded windows**: any living-room or bedroom air conditioner active (2 % of minutes in
  May-October, none in the heating blocks). The third AC sat in "heat" all of Oct-Nov with no
  extra electricity, so it was treated as idle.
- **Not used**:
  - The four room thermostats. Their targets are 4-17 K below their readings all the time, so
    they never call. Whether they close loops is unknown, and the loop behaves as fully open.
  - Ventilation. The HRV moves 20-50 m³/h with near-complete recovery: 0.002 kW/K at 85 %, about
    1 % of the loss. It is a documented part of `h_ao` (`vent_m3h`, `vent_eta`) and not fitted
    separately.
  - Whole-house electricity (0.6-0.7 kW mean, from July only). Tried as an internal-gain input
    in exploration; it covers too little of the data to fit, so the fitted constant + profile
    stands in for it.

## 3. Identification method

- **Linear time-invariant with heat as the input.** With the loop heat as input (water enters
  segment 1 at return + q / (cp flow)), the whole model is linear and time-invariant. The full
  9-month record is then simulated at once:
  - exact matrix-exponential discretization at 1 minute;
  - a modal decomposition, with each mode run as a first-order filter;
  - about 0.2 s per pass over 391 000 minutes.
- **State at each forecast origin.** A steady-state Kalman observer uses the room sensor and the
  loop return. Where the return is not a loop reading, it uses the room only. It starts from a
  quasi-steady state.
- **Forecasts.** From each origin (hourly), the model runs open loop with the measured inputs.
- **Fit criterion: multi-step error, not one-step.** The sum of squared errors of:
  - the room at 1, 3, 6, 12 and 24 h ahead;
  - the return at 15 min, 1 h and 3 h (weight 0.5).
- **The joint (central) fit adds two terms.** The room at 2 and 4 days ahead on the minute data,
  and the hourly cold season (room 1, 3 and 7 days ahead, Jan 9 - Mar 1, outside the January
  holdout). Section 6 explains why.
- **Optimizer:** least squares in log space, with finite-difference Jacobians. Standard errors
  come from the Jacobian. Each fit takes 1-3 minutes.
- **Holdout:** forecast windows that touch a holdout block are never in a fit.

## 4. Structures tested (minute-data fit; room RMSE in K at 1 h / 6 h / 24 h)

| structure | free | cost | A (fit) | C (fit) | hold_A | hold_C | return 15 min, hold C / A |
|---|---|---|---|---|---|---|---|
| S1 loop 1 segment, slab, room (2 nodes) | 11 | 0.461 | 0.27/0.48/0.47 | 0.26/0.50/0.46 | 0.22/0.40/0.44 | 0.22/0.37/0.47 | 0.31/0.21 |
| S2 same with 3 loop segments | 11 | 0.511 | 0.27/0.48/0.47 | 0.26/0.50/0.47 | 0.23/0.40/0.45 | 0.21/0.35/0.46 | 0.50/0.33 |
| S3 + envelope node | 14 | 0.345 | 0.25/0.41/0.42 | 0.22/0.41/0.42 | 0.18/0.28/0.44 | 0.21/0.43/0.57 | 0.13/0.18 |
| S4 + daily internal-gain profile | 18 | 0.335 | 0.25/0.40/0.42 | 0.22/0.40/0.42 | 0.18/0.28/0.45 | 0.20/0.39/0.55 | 0.13/0.18 |
| S5 + thermometer lag | 19 | 0.333 | 0.25/0.40/0.42 | 0.22/0.40/0.41 | 0.17/0.28/0.44 | 0.20/0.39/0.55 | 0.13/0.18 |
| S6 + glow on south facade | 21 | 0.330 | 0.25/0.41/0.41 | 0.22/0.41/0.42 | 0.17/0.27/0.41 | 0.19/0.38/0.51 | 0.11/0.16 |
| S6 + glow on east facade | 21 | 0.325 | 0.25/0.40/0.41 | 0.22/0.40/0.41 | 0.19/0.30/0.42 | 0.20/0.37/0.50 | 0.10/0.16 |
| S6 + glow on west facade | 21 | 0.326 | 0.25/0.41/0.41 | 0.21/0.39/0.41 | 0.17/0.26/0.39 | 0.20/0.40/0.52 | 0.12/0.16 |
| **S6 + glow on GHI** | 21 | 0.323 | 0.24/0.41/0.40 | 0.21/0.39/0.40 | 0.17/0.27/0.41 | 0.19/0.40/0.50 | 0.11/0.15 |
| **X1 = S6-GHI + slab-to-ground** | 22 | **0.317** | 0.24/0.40/0.40 | 0.21/0.39/0.41 | 0.17/0.27/0.39 | 0.19/0.39/0.49 | **0.10/0.11** |
| X2 + horizontal (skylight) aperture | 22 | 0.323 | identical (aperture -> 0) | | | | |
| X3 loop 1 segment | 21 | 0.322 | 0.25/0.41/0.40 | 0.21/0.39/0.40 | 0.17/0.27/0.41 | 0.19/0.40/0.50 | 0.10/0.17 |
| X4 loop 6 segments | 21 | 0.322 | 0.24/0.41/0.40 | 0.21/0.39/0.40 | 0.17/0.27/0.41 | 0.19/0.40/0.50 | 0.13/0.15 |
| X5 all sun on the air node | 20 | 0.323 | identical (fitted split was already ~0) | | | | |

What the comparison shows:

- **The envelope node is the big step.** Cost falls 25 %, and the 15-minute return error halves.
  Without it the slow store has to sit in the slab and the room, and both the return and the
  6-24 h room forecasts suffer.
- **Smaller gains:**
  - The internal-gain profile adds 3 %.
  - The sun "glow" on the thermometer adds 1-3 % and improves the held-out 24 h errors. Global
    irradiance works best, which fits a sensor lit through several windows.
  - The thermometer lag was not supported: the joint fit drives it below a minute.
- **The ground path** (slab to a fixed 10 °C) lowers the cost by a further 2 %. It is the only
  change that also cuts the held-out return error (0.15 -> 0.11 K). It also turns the fitted
  constant internal gain from negative (unphysical, -0.15 kW) to +0.33 kW.
- **Loop segments (1, 3 or 6) and the solar split are not identifiable** from this data. 3
  segments stay as the central choice, because a few segments give the return a realistic
  transport delay when the supply jumps.

## 5. Central fit and minute-data validation

Central parameters are in `HouseParams` (section 1 lists them).

- **Parameter standard errors:**
  - 1.4-5 % (log scale) for the capacities and couplings;
  - 2-4 % for the apertures;
  - 4 % for the ground path.
  - The glow is uncertain (8 %), the solar split and the thermometer lag are unidentified.
- **Strongly correlated pairs:** slab-room with ground (-0.87) and internal gain with ground
  (+0.82). The data mostly fixes their combinations.

Forecast errors from observer-initialized origins every hour (room in K, RMSE / bias):

| block | room 1 h | 3 h | 6 h | 12 h | 24 h | return 15 min | 1 h | 3 h |
|---|---|---|---|---|---|---|---|---|
| A0 (cold, fit) | 0.25 / 0.00 | 0.41 | 0.49 | 0.47 | 0.40 / +0.29 | 0.50 | 0.54 | 0.82 / +0.43 |
| A (fit) | 0.26 / +0.03 | 0.39 | 0.43 | 0.45 | 0.49 / -0.05 | 0.20 | 0.29 | 0.51 / -0.35 |
| F (floating, fit) | 0.20 / 0.00 | 0.31 | 0.38 | 0.38 | 0.40 / -0.06 | - | - | - |
| C (fit) | 0.23 / +0.02 | 0.40 | 0.45 | 0.45 | 0.44 / -0.08 | 0.21 | 0.28 | 0.48 / -0.44 |
| **hold_A** (Mar 16-20) | **0.18** / +0.05 | 0.28 | **0.29** | 0.35 | **0.41** / +0.29 | 0.14 | 0.15 | 0.24 / -0.19 |
| **hold_C** (Nov 2-6) | **0.18** / -0.01 | 0.30 | **0.33** | 0.35 | **0.42** / -0.21 | 0.16 | 0.22 | 0.37 / -0.33 |

Notes:

- **The noise floor is high.** The 0.1-0.2 K report-on-change thermometer and the occupants
  (section 7) set it. About half the 1 h error is sensor quantization.
- **The 3 h return error has a bias of -0.3 to -0.45 K in mild weather and +0.4 K in the cold
  week.** The model's loop water runs slightly too cold in mild weather and too warm in deep cold
  (section 6). For a controller this means the simulated supply temperature needed for a given
  heat is off by about this much: about 1 % COP per 0.3 K (unit stage, -3 %/K).
- **The minute-only fit does better on the minute data**, which was its only target. Its room
  24 h error is 0.40 K in A and its 3 h return bias -0.03 to -0.17 K. But it fails the
  cold-season energy balance (section 6), so it is kept only as the `minute_only` variant.

## 6. Season (hourly) check and reconciliation

**Heat in the hourly-only season.** There was no unit data before February, so the heat comes from
electricity x a calibrated heat/electricity ratio:

- The ratio's shape is the unit model's steady COP (supply 31.5 °C, 6 kW) minus the unit stage's
  defrost penalty.
- One factor, **0.92**, scales it. That factor was fitted on 80 clean minute-data days (-15 to
  +16 °C daily means). The 8 % below steady covers starts, idle draw and transients.
- The resulting ratio is 1.9 at -20 °C, 2.2 at -10, 2.7 at 0, 4.0 at +5 and 4.8 at +10.
- Hot-water electricity (1.2 kWh/day, from the minute data) is removed first.
- **Weak point:** only 2 clean days below -5 °C anchor the cold end.

**The conflict.** The first fit used the minute data only (H = 0.208 kW/K, ground 0.042 kW/K).
It needs too much heat in deep cold:

- **Hourly season:** 17-38 % more heat than supplied in every week from 9 January to 20 February.
  A 14-day free run through the January holdout drifts 2.7 K cold (RMSE 3.0 K).
- **Measured minute heat agrees.** On 9-10 February (-15 and -12 °C, unit data complete) it
  needed 26-34 % more than the measured loop heat.

**Simple daily balances agree that the loss is less than proportional to indoor-outdoor
difference.** These are regressions of daily heat on (T_in - T_out) and solar, independent of the
dynamic model:

| days | H free | constant term (kW) | H with internal gain fixed at 0.31 kW |
|---|---|---|---|
| measured-heat days (mostly mild) | 0.164 | +0.32 (a gain) | 0.164 (90 % CI 0.153-0.175) |
| daily mean below 0 °C | 0.112 | -1.20 (a fixed loss) | 0.160 (0.155-0.167) |

**The reconciliation.** The central model is the joint fit (section 3). It reaches the cold-season
balance by moving part of the loss onto the slab-to-ground path:

- A fixed-temperature sink grows with slab temperature rather than with outdoor coldness.
- The outdoor coefficient falls to 0.111 kW/K, and the ground path rises to 0.092 kW/K from the
  slab (0.076 kW/K seen from the room).
- The minute-data errors grow only a little (24 h: 0.41 -> 0.49 K in A, 0.41 -> 0.44 K in C). The
  held-out C block improves (0.49 -> 0.42 K).

| hourly season, central (joint) | value |
|---|---|
| held-out Jan 12-26 (mean -8 to -16 °C): room RMSE 1 h / 6 h / 24 h | 0.23 / 0.33 / 0.38 K (bias -0.05 K) |
| held-out Jan 12-26, 14-day free run from one observer state | RMSE 0.42 K, bias -0.10 K, worst 1.7 K |
| days with mean below -5 °C (38): room 24 h RMSE | 0.39 K |
| daily energy error, mean below -5 °C (38 days) | -1.1 % (mean absolute 6 %) |
| daily energy error, -5..0 °C (11 days) | +0.5 % (mean absolute 10 %) |
| weekly energy error, Jan 9 - Feb 27 (cold weeks) | -3.4 % to +3.2 % |
| weekly energy error, Mar 6 - Apr 30 (spring, +4..+8 °C) | +2 % to **+34 %** (model needs less heat than supplied) |

The energy error is minus the residual heat that makes the model follow the recorded room, over
the heat supplied (section 7). Positive means the model needs less heat.

**Interpretation, and what is not settled:**

- **The big ground path is a proxy.** Physically, an insulated slab on ground loses perhaps
  0.02-0.04 kW/K. The fitted path also stands for any loss that does not scale with the outdoor
  temperature, and for any extra heat source in deep cold that was not metered (for example a
  fireplace, if there is one; the data cannot tell). A controller that lowers the slab
  temperature saves about 2.2 kWh/day per K of slab in this model, against about 1 kWh/day in
  `minute_only`. Rank controllers that win mainly through lower slab temperature against both.
- **Spring (March-April) needs 17-21 % less heat than was supplied.** The residual is negative in
  daytime (section 7). Likely causes are more airing in mild sunny weather, or solar gain that does
  not scale like the facade irradiance. The October-November season is close (-3 to -7 %), and so
  is the deep cold.
- **The deep-cold heat estimate depends on the COP extrapolation.** The cold-end ratio rests on 2
  measured days. A 10 % error there moves the cold-season balance by 10 %. The `minute_only` and
  `loss_*` variants bracket it.

## 7. Disturbances (residual heat)

`.local/lab-data/disturbance_minute.csv` holds, per minute, the residual heat into the room-air node
that makes the central model follow the recorded room exactly:

- `dist_w` per minute and `dist_w_60min` (centred hourly mean);
- `room_recon` and `model_sensor`;
- `q_loop_w`;
- `in_season` (1 in the heating blocks A0/A/F/C and the holdouts);
- `flags`: 1 = AC active, 2 = loop heat estimated from electricity, 4 = no room reading.

How it is computed:

- **Room reconstruction:** the report-on-change sensor is rebuilt by anchoring each change at the
  midpoint of the old and new value, interpolating linearly, and smoothing over 31 minutes.
- **Tracking:** the model's glow term is removed. Each minute, the heat needed to put the air node
  on the target is injected (deadbeat), clipped at ±8 kW.
- **What it holds:** everything the model does not explain. That includes people, cooking, airing
  and doors, as well as model error such as solar misfit. It is the honest disturbance for this
  model.

Characterisation over 112 clean heating-season days (`.local/lab-results/house/disturbance_stats.json`):

- **Per minute:** median -0.14 kW; 5-95 % range -2.2 to +1.7 kW; 1-99 % range -4.1 to +3.5 kW.
  Most of the minute-scale spread is the deadbeat amplifying sensor steps, so use hourly values.
- **Daily mean:** -0.08 kW (SD 0.66 kW; p10 -0.71, p90 +0.76). By block: spring (A) about
  -0.33 kW, October-November (C) +0.06 to +0.15 kW, the cold week near 0.
- **Typical profile by local hour, kW (all days):**

  | 00 | 02 | 04 | 06 | 08 | 10 | 12 | 14 | 16 | 18 | 20 | 22 |
  |---|---|---|---|---|---|---|---|---|---|---|---|
  | -0.15 | +0.01 | +0.15 | -0.09 | -0.18 | -0.51 | -0.22 | -0.45 | -0.37 | +0.17 | -0.09 | -0.14 |

  - It is negative through the day (10-16 h), when airing, absence or solar misfit act.
  - It is positive at 17-18 h, which is cooking time.
  - It is slightly positive before dawn. That is most likely the model's internal-gain profile
    offsetting the daytime mean.
  - Weekends have a deeper late-morning dip (-0.8 to -0.9 kW at 10-11 h).
- **Hourly residual after the profile:** SD 1.1 kW. It is AR(1) with phi = 0.69 per hour, so a
  disturbance lasts a few hours.
- **Events** (15-minute mean beyond ±1 kW for at least 15 min):

  | events | count | duration p50 / p90 | energy p50 / p90 | when (local) |
  |---|---|---|---|---|
  | positive | 1.7 per day | 63 / 209 min | 1.8 / 6.9 kWh | mostly 06-21 h |
  | negative | 2.1 per day | 63 / 210 min | 1.9 / 8.0 kWh | mostly 06-12 h |

**For synthetic scenarios:** heat into the air node = the hourly profile + an hourly AR(1) (phi
0.69, SD 1.1 kW) + Poisson events. Event sizes are lognormal with the p50/p90 above, and the times
of day follow the histogram in the stats file. Optionally add a seasonal offset (-0.3 kW in
spring). Or replay `disturbance_minute.csv` through `House.step(q_air=...)`.

## 8. Uncertainty variants (`lab/sim/house.py: VARIANTS`)

Each variant fixes one aspect and refits everything else on the joint criterion. Each is therefore
a model that explains the data almost as well. The cost increase is the joint fit cost.

| variant | fixed | H kW/K | steady heat for 22 °C at -20 / -10 / 0 / +10 °C, kW | cost | room 24 h RMSE hold A / C |
|---|---|---|---|---|---|
| central | - | 0.187 | 6.40 / 5.05 / 3.70 / 2.35 | - | 0.41 / 0.42 |
| heavy_slab | slab x1.3 (5.7 kWh/K) | 0.194 | 6.41 / 5.03 / 3.65 / 2.26 | +1.0 % | 0.40 / 0.43 |
| light_slab | slab x0.7 (3.1 kWh/K) | 0.180 | 6.39 / 5.07 / 3.76 / 2.44 | +3.0 % | 0.43 / 0.41 |
| loss_plus20 | loss conductances x1.2 | 0.224 | 6.86 / 5.23 / 3.61 / 1.98 | +5.9 % | 0.41 / 0.45 |
| loss_minus20 | loss conductances x0.8 | 0.147 | 6.00 / 4.87 / 3.75 / 2.63 | +10.9 % | 0.39 / 0.36 |
| sun_plus30 | apertures x1.3 | 0.178 | 6.59 / 5.24 / 3.88 / 2.53 | +2.7 % | 0.47 / 0.46 |
| sun_minus30 | apertures x0.7 | 0.167 | 6.31 / 4.94 / 3.57 / 2.20 | +2.2 % | 0.36 / 0.38 |
| minute_only | minute data only | 0.208 | 7.74 / 5.92 / 4.11 / 2.29 | (other criterion) | 0.39 / 0.49 |

Because the gains refit along with the losses, "±20 % heat loss" moves the cold-weather load by
only ±7 %. It moves the mild-weather net load by ±16 %, which is what the data allow. The slab
mass is weakly identified (+1 % cost at 1.3x). Pair the house variants with the unit variants, and
use `flow_scaled()` with `low_flow` and `high_flow`.

## 9. Implementation (`lab/sim/house.py`)

- **The model:** `House(params).step(t_out, q_loop=... | t_supply=..., flow_lpm=..., poa_s, poa_e,
  poa_w, ghi, hour_local, q_air, q_slab, i_glow, dt_min=1)` returns `HouseStep`:
  - `t_return`, `t_air`, `t_sensor_true`, `t_sensor` (0.1 K, report-on-change with a 0.075 K
    hysteresis), `t_slab`, `t_envelope`;
  - `q_loop`, `q_floor` (slab to air), `q_loss`, `q_solar`, `q_internal`.
- **Heat input is energy-exact** and is the recommended coupling: `q_loop` from the unit model,
  0 while the valve is on the tank. Supply-temperature input also works, including flow 0 for a
  stopped loop.
- **Exact discretization:** the matrix exponential, cached per (input mode, flow, step), at about
  3 µs per step (180 days in 0.8 s).
- **Helpers:**
  - `matrices()` and `discretize()` (the identification uses the same physics);
  - `steady_state()` and `steady_heat()`;
  - `facade_irradiance()` (same transposition as the data);
  - `House.reset()` (quasi-steady start) and `set_state()`;
  - `flow_scaled()`.
- **Self-check:** `.local/lab-venv/bin/python -m lab.sim.house` checks:
  - the steady energy balance (to 1e-14 kW);
  - monotone decay to outdoors with no gains;
  - that supply-temperature and heat inputs agree;
  - return between slab and supply, and no heat at zero flow;
  - sensor quantization and glow;
  - stability and loads of every variant, and the flow scaling;
  - speed.

## 10. Limits and what would tighten the model

- **One thermometer.** The "room" is the living-room sensor. The rest of the house is folded into
  the air and envelope nodes.
- **Flow is assumed.** The unit stage's 29 L/min sets the scale of every heat number. A flow
  reading would fix both stages.
- **Mild-weather return temperatures run about 0.3-0.45 K cold** at 3 h horizons. **Spring
  needs less heat** than supplied.
- **The ground path is a proxy** (section 6).
- **The cold end rests on few measured days.** A cold week with clean unit data would test the
  reconciliation directly.
- **Useful additions:**
  - a floor-surface or screed temperature sensor, which would separate slab-to-room from the
    ground path;
  - a second room thermometer away from windows (glow);
  - window-open contacts (airing is the largest disturbance).

## 11. Review fixes (round 1)

The closed-loop review (SIMULATOR.md section 9) changed how the simulator uses this model. The
house model itself (structure and parameters) is unchanged.

- **Return anchoring on the weather, not on delivered heat.** The measured-minus-model return
  offset (SIMULATOR.md section 3) is now tabulated against the weather-driven steady load: the
  steady heat demand at 22 °C (`steady_heat`, 3.70 kW at 0 °C, 5.05 kW at -10 °C central) for the
  24-hour exponential mean of the outdoor temperature. Offsets run from +1.7 K at 1.3-1.8 kW to
  -1.8 K above 5 kW (central). A controller can no longer change the offset by delivering more
  heat. The knots above 4.5 kW (the cold regime) rest on 1-3 days each; the floor-sensor and
  two-zone-floor suggestions of section 10 remain the proper fix.
- **Stagnant loop.** With space heating switched off the simulator stops the pump: the loop
  segments then use the same matrices with zero flow (`matrices(p, "heat", flow_lpm=0)`), so the
  water exchanges heat only with the slab. This pump behaviour is ASSUMED (2 mode changes in the
  record).
- **Stored heat.** Every run reports the heat stored in loop water, slab, air and envelope
  (C_w + C_s + C_a + C_e = 83 kWh/K central, 74 of it the envelope) at the start and end of the
  window. Week energies are compared with a common 3-day run-out after the window, and the rest of
  the storage difference is bought back at the run's COP.
- **Comfort normalisation.** The ranking energy is normalised to the target mean air with
  `h_total` (0.187 kW/K central, 0.208 `minute_only`, 0.147 `loss_minus20`). After the run-out it
  leaves 1.5-6.5 %/K of mean air in the weeks and 3.1 %/K over the season: the COP effect of
  warmer water, which this normalisation deliberately does not remove.
- **Local weather.** In archive scenarios the house is driven by ERA5 plus a local departure
  (AR(1), SD 1.1 K, 6 h), measured as the night-time covariance of the unit's and the
  ventilation unit's outdoor sensors against ERA5 (1.34 K²). At `h_total` 0.19 kW/K that is
  about 0.2 kW of extra load variation, small next to the 1.1 kW hourly disturbance. Recorded
  scenarios keep ERA5, because their tracked disturbance already contains the departure.
- **Disturbance for archive scenarios.** Instead of the parametric generator of section 7, archive
  scenarios now bootstrap whole recorded days of the tracked residual for the chosen house
  parameters (heating on, ≥ 97 % unit data, room data present), with the next recorded day kept
  with probability 0.72 (the lag-1 correlation of daily means over 109 day pairs). That keeps the
  recorded minute, hourly (SD 1.0-1.15 kW) and day-to-day statistics. Recorded month offsets are
  swapped for the target month's. The parametric generator remains as the flag `synthetic_dist`;
  it now has a daily AR(1) part (SD 0.35 kW) and event edges ramped over 30 minutes, because
  without them its daily-mean SD was 0.36-0.40 kW against 0.52 recorded and its minute-to-minute
  variation about three times the recorded one.

## 12. Review fixes (round 2)

The second closed-loop review (SIMULATOR.md section 10) looked at what the closed-loop replay can
and cannot say about this model. The house model itself (structure and parameters) is unchanged.

- **The replay's room agreement is by construction (N5).** The recorded disturbance (section 7)
  is the residual heat that makes the model follow the recorded room under the recorded heat. In a
  closed-loop replay whose heat matches the recorded heat, the room therefore matches too; the
  replay's 0.19 K says the heat matched, not that the house dynamics are right. Its hourly SD is
  1.0-1.2 kW in the replay windows against a load of 2-4 kW.
- **House test without the recorded room** (`validate_sim house`): the replay with the residual
  replaced by something that does not use the recorded room. Room thermometer RMS against the
  recorded room over 4 weeks (current season) / 10 weeks (spring):

  | residual | current season | spring |
  |---|---|---|
  | recorded (by construction) | 0.19 K | 0.38 K |
  | daily means of the recorded residual | 0.35 | 0.53 |
  | window mean | 0.49 | 0.72 |
  | zero | 0.48 | 1.13 (bias +0.89 K) |
  | recorded days drawn from elsewhere in the record (3 draws) | 0.68-0.82 | 0.91-0.97 |

  So the slow part of the residual (its daily means) carries most of what the model needs; the
  intra-day part is worth about 0.15-0.35 K RMS. With someone else's days (what archive scenarios
  use), the room wanders by 0.7-1.0 K RMS, mostly through airing, cooking and solar misfit that
  the controller then has to correct. Electricity stays within 0-5 % in every case.
- **Out-of-pattern behaviour is extrapolated.** All training data come from two controllers that
  wrote a setpoint every 30 minutes within 25-39 °C. Pulses, deep setbacks and long low-output
  runs rest on the 24-hour held-out forecast (0.41 K RMS, section 5). Proposed test on the real
  house: a 2-day night setback (setpoint 25 °C from 22 to 05 h) and a 2-day fixed low-output
  pattern, each predicted beforehand with the residual's daily means.
- **Slab and sun variants are mandatory ranking variants (N7):** `light_slab`, `heavy_slab`,
  `sun_plus30` and `sun_minus30` (section 8) moved timing strategies by more than their 90 %
  intervals in the review (for example a weather curve in the cold week: score +1.6 % nominal,
  +6.0 % with `sun_minus30`).
- **Cache race fixed (N7).** The tracked house state and residual per parameter set
  (`exogenous.recorded_house_track`) is now built under an exclusive file lock and published with
  an atomic rename, so parallel workers no longer read a half-written cache file. The same applies
  to the tuned-baseline cache. Orphan cache files from the round-1 anchoring were removed.
- **Variants do not combine.** Two house variants joined with '+' keep only the last one (as
  before); unit and house variants combine freely.
