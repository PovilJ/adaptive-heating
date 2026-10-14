# Predictive planner (0.4.0)

Written 2026-10-10 after two days of the 0.3.2 curve controller in the first
house. This is the record of why the planner exists, how it works, how its
numbers were obtained and what to check next.

## Why

Measured 8–10 October 2026 (35 hours of Automatic, target 22.5 °C):

- the room was above target 88 % of the time once reached and peaked at 23.7 °C
  with the compressor still running;
- water averaged 30.2 °C where the archived PyScript, replayed on the same
  readings, asked for 28.2 °C (5 °C apart on the sunny morning of the 10th);
- 12.4 of 20.6 compressor hours ran with the room already 0.2 °C over target;
- the controller paused 7 times (7.3 h) because a stable room made the
  change-only thermometer look stale.

Causes in 0.3.2: a fixed +3 °C curve offset, corrections that only add heat,
no use of sunshine, and a rate limiter that lost a step to command timing. The
owner asked for something better than both it and the hand-written PyScript:
comfortable, weather-aware and frugal with electricity.

## How it works

Every control interval (30 minutes, evaluation and command together):

1. **Estimate** ([`mpc.Estimate`](../custom_components/adaptive_heating/mpc.py)).
   Advance a three-store model of the house with what the heat pump and sky did
   since the last cycle, compare with the thermometer, and correct: a warm
   surprise is attributed to sun on the room only as far as the sky allows
   (0.4.4), the rest to the slab, and a persistent miss becomes a slow drift
   term.
2. **Forecast.** 36 hours of half-hour steps from the weather entity's hourly
   temperature and cloud cover, plus sun position for east, south and west walls.
3. **Plan** (`mpc.plan`). Search water temperatures for 13 blocks (half-hours
   first, six-hour blocks last) minimising electricity plus comfort penalties.
   Electricity uses a Carnot-fraction COP, so cooler water and warmer outdoor
   air are cheaper; compressor starts and running below minimum output cost
   extra; daylight electricity is discounted 30 % for own solar.
4. **Command** the first block through the existing limiter and safety checks.
5. **Guard** (`mpc.Guard`). If the room is more than 0.2 °C under its band, add
   1 °C of water per cycle (up to 6) until it is back. This covers a wrong model.

Comfort band: target (no lower by day), `night_minimum` from `quiet_start_hour`
to `morning_hour`, and 0.3 °C of free headroom above target for storing heat
(0.5 °C before 0.4.4).

The planner is skipped, and the old heating curve used, when `predictive` is
off, Home Assistant has no location, fewer than 12 forecast hours exist, or AC
assistance is active. The cold-night planner still computes its diagnostics and
AC requests but no longer sets the water temperature while the planner runs.

## The house model

State: slab, building, sun glow. Room = building + glow (+ `mix` × slab excess).

| Quantity | First-house value | Meaning |
| --- | --- | --- |
| heat loss | 0.139 kW/°C | whole house to outdoors |
| slab | 6.6 kWh/°C | fast store the water heats |
| slab → building | 4.2 kW/°C | |
| building | 21.2 kWh/°C | walls, furniture, air |
| sun, east / south / west | 2.25 / 1.35 / 0 °C/h per kW/m² | glow on the thermometer |
| glow fade / kept | 0.27 per hour / 21 % | |
| emitter | 0.8 kW/°C above slab + 1.8 °C | from measured outlet temperatures |
| minimum output | about 3 kW | lowest heat seen while running |
| COP | 0.42 × Carnot, 8 °C exchanger lift | |

These are the defaults in `mpc.House`. They belong to the first house; another
house needs its own fit until the values become stored per installation.

### How they were fitted

- Data: HA hourly statistics for room temperature and heat-pump electricity
  (10 January–10 May 2026, outdoor −22 to +12 °C), Open-Meteo hourly temperature
  and cloud cover for the location, and ten-minute raw history for 8–10 October.
- Heat is electricity × modelled COP. `sensor.versati_thermal_power_output` was
  rejected: it has days of zeros and COPs above 8.
- `scripts/fit_house.py` fits winter 24-hour roll-outs. Alone that cannot
  separate slab from building (three different answers, same error) because the
  PyScript held the room nearly constant. A joint fit with the October cold
  start (room 19.3 → 22.7 °C, real on/off cycles) pins the fast response.
- Result: October 60-hour open roll-out median error 0.13 °C, 90 % under
  0.33 °C. Winter 24-hour roll-outs median 0.35 °C (0.24 °C in the dark). The
  thermometer steps in 0.2 °C. Daytime error is mostly cloud cover being a poor
  measure of sunshine.
- Exports and the joint-fit script are in the ignored
  `.local/analysis-2026-10-10/` (`stage2.py`); the long-term fit is repeatable
  with `python3 scripts/fit_house.py <folder>`.

## Replay results

`python3 scripts/backtest.py <folder> START END [--mismatch]` runs each
controller against the fitted house over recorded weather. The house is the
model itself, so this ranks controllers; it does not predict the bill.

| Period | Predictive | Curve +3 (0.3.2) | PyScript |
| --- | --- | --- | --- |
| 2–10 Oct (mild) | 4.5 kWh/day | 7.4 | 5.3 |
| 10–20 Mar (sunny spring) | 6.4 | 11.3 | 8.6 |
| 22 Jan–1 Feb (to −22 °C) | 39.6 | 49.5 | 47.1 |

Room minimum stayed at or above 21.97 °C in all three. With a deliberately
wrong house (25 % more loss, 20 % weaker emitter, different sun) the planner
still used less than the PyScript in spring (15.4 vs 16.0 kWh/day) and, in the
cold spell, held a 22.0 °C mean with dips to 20.9 °C — the Guard at work, and the
case to watch in real frost.

Findings worth remembering:

- A night setback saves almost nothing here (4.2 vs 4.3 kWh/day in October,
  39.5 vs 39.2 in winter): the building is heavy and regaining the setback needs
  hotter, less efficient water. The planner is allowed to drift at night and
  does so only when it is cheaper.
- At 10 °C outdoors the house needs about 1.7 kW and the compressor's minimum
  is about 3 kW, so cycling in autumn is unavoidable; the plan aims for few,
  long runs.

## First-house settings applied with 0.4.0

`predictive` on, `curve_offset` 0.5 (fallback curve), `stale_minutes` 360,
`rise_per_hour` 6, `fall_per_hour` 10, `night_minimum` 21.5,
`quiet_start_hour` 22, `morning_hour` 7. Target stays 22.5 °C.

## What to check after a few days live

1. Status sensor attributes: `plan` (24 hourly rows of water, predicted room
   and band), `predicted_room_last_cycle` against the measured room,
   `model_bias_celsius_per_hour` (should stay near 0; ±0.3 is the clamp),
   `estimated_slab_celsius`, `estimated_sun_glow_celsius`.
2. Room against the band: time above target + 0.5 that is not sunshine, time
   under target by day, whether it is back by 07:00.
3. Any "+N °C because the room is under its band" in the decision reasons: the
   Guard firing means the model under-predicts the heat needed.
4. kWh/day against outdoor temperature, and compressor starts per day.
5. Sunny mornings: does it hold back before the sun arrives?
6. Refit `mpc.House` with the new days included.

## 0.4.1, same day

The first live plan (one hour after the 0.4.0 restart) proposed minimum water
now but 36–38 °C through the night, 23.5 kWh for the day. Cause: the drift term
learned at 0.2 per cycle with a ±0.3 °C/h clamp, and a daylight surprise the sun
glow could not absorb (glow cannot be negative) went nowhere. Three cycles of
start-up mismatch became −0.19 °C/h, about 4 kW of imaginary heat loss. Fixed:
the remainder now corrects the slab, the drift learns at 0.02 per cycle and is
clamped to ±0.05 °C/h, and the stored estimate was reset. The Guard remains the
fast defence against a wrong model. Lesson: check the first live plan, not only
replays — the replay starts from a state consistent with the model.

## 0.4.2, same day: the compressor cannot trickle

The owner pointed out that a setpoint within about 1 °C of the return water
stops the compressor, and that the PyScript lowered water gently and kept it
above the return while heat was still wanted. 0.4.1 ignored this: its first
confirmed plan asked for 26–27 °C overnight, which the model counted as 0.4–1 kW
but which the real unit would have delivered as nothing.

- `House.heat_kw` now returns zero below half the minimum output, so the plan
  chooses real runs or none.
- `mpc.keep_running`: when the first block wants heat, the commanded setpoint is
  at least return water + 1.5 °C (rounded up). When no heat is wanted the
  setpoint is left low so the compressor does stop.

Replays with the stricter house: 4.7 / 38.8 / 6.6 kWh/day (October, cold spell,
spring) against 5.2 / 47.1 / 8.4 for the PyScript; compressor starts rise to
4–6 per day in mild weather, similar to the PyScript's 4–8 on the same house.
The emitter's `dead` band is still measured from the modelled slab, not from the
return sensor; compare the two in the live data.

## Known limits

- Model values are code defaults for one house, not learned online. Only the
  slab, glow and drift are estimated live.
- Sunshine comes from forecast cloud cover; measured PV output is not yet used
  as a nowcast, and export pricing is unknown, so the solar discount is a guess.
- No tariff input: electricity is one price apart from the daylight discount.
- Hot water electricity is inside the fitted heat (a few percent).
- The planner's coarse far blocks are imprecise; only the first step is acted on.
- With 30-minute evaluation the 0.3.x cooling trend, stalled-recovery boost,
  `solar_wait` and cooldown learning receive no data and are dormant.
- The dashboard does not chart the plan yet.

## 0.4.3: a paused controller looks again in two minutes

After a restart the Zigbee room thermometer is unknown until its next report.
With one evaluation per half hour, the first check found no room temperature
and the status read "Indoor temperature unavailable" for up to 30 minutes
although the sensor had returned within six. While the status is paused the
coordinator now re-evaluates every 2 minutes; otherwise every control interval.
On October 10 the owner updated to 0.4.2 through HACS himself (HACS reported
`444c875` installed and latest), so HACS updates do work from the HA UI.

## 0.4.4: stop heating a room that is already warm

On 13 October (100 % cloud all day, 7–11 °C outside) the compressor ran from
13:53 to after 17:00 while the room climbed from 22.5 to 23.1 °C against a
22.1 °C target; the owner lowered the setpoint by hand. On the 11th it had also
run at 18:30 with the room at 23.3–23.5 °C (target 22.5).

Two causes, both in `mpc.py`:

- **Estimator.** In daylight every warm surprise became sun glow, and the
  daylight test passed even under full cloud. Glow fades in the plan, so the
  planner believed the house itself was still at 22.1 °C and would fall under
  target without more heat. Now the glow takes at most half as much again as
  the modelled sun delivered in that interval; the rest is slab and building
  heat, which stays. A cold surprise still shrinks the glow first.
- **Comfort cost.** 0.5 °C over target was free and the penalty beyond it was
  1.5 per °C² hour, so a room 1 °C over target cost almost nothing, while a
  dip under target cost 20. Now: 0.3 °C of headroom, 4 per °C hour above it
  (linear), 60 per °C² hour below.

- **No stop on the warm side.** The Guard covered a wrong model only when the
  room was cold. Now a measured room more than 0.2 °C over its band
  (target + 0.5) gets minimum water whatever the plan says (`mpc.too_warm`),
  and the keep-running lift is not applied.

A squared penalty of 10 above the band was tried first. It stopped the
afternoon heating but, with the floor still at 20, the plan let sunny days
begin 0.6–0.9 °C under target (07:00–09:00, 0.6–1.3 h/day in replay) to offset
solar warmth nobody can prevent, and the Guard then heated just before the sun
arrived. Linear above, firm below removes that.

Evidence:

- Planner re-run from each recorded estimator state, 10–13 October
  (`.local/analysis-2026-10-13/replay.py`, `plans.py`): half-hours where the
  plan wants heat with the room 0.5 °C or more over target fall from 9.5 h to
  1.5 h from the estimator and cost alone; the stop removes the rest. On the
  13th the plan alone still wants heat until 15:30 (room 22.7 °C); the stop
  acts at the first cycle after 14:37, more than two hours before the owner
  did. On the 11th the 18:00–19:00 run at 23.3–23.5 °C is not requested.
- Replays (`scripts/backtest.py`, which now also holds the setpoint above the
  return water as the live unit does), old → new:

| Period | kWh/day | hours/day over target + 0.5 | daytime hours/day 0.3 under |
| --- | --- | --- | --- |
| 2–10 Oct | 4.6 → 4.7 | 11.3 → 6.8 | 0.2 → 0.0 |
| 10–20 Mar | 6.7 → 6.9 | 13.2 → 11.6 | 0.3 → 0.0 |
| 22 Jan–1 Feb | 39.0 → 39.6 | 3.2 → 1.1 | 0.0 → 0.3 |
| 2–10 Oct, wrong house | 10.2 → 10.3 | 8.8 → 6.5 | 0.5 → 0.4 |
| 10–20 Mar, wrong house | 14.6 → 15.2 | 11.3 → 10.9 | 1.9 → 1.8 |

  Most remaining hours over the band are sunshine. The replay house is the
  model, so it cannot show the electricity wasted by a wrong estimate such as
  the 13th; no saving is claimed, and in replay electricity is level to 4 %
  higher. To watch in frost: on clear days the stop withholds heat while the
  sun warms the thermometer (the 0.3 h/day and +0.5 kWh/day in the January row;
  room minimum 22.08 °C against a 22.5 °C target).

Also learned from the five days of live cycles:

- A joint refit including 8–13 October found a different house (weak slab
  coupling, room reading 27 % of the slab) with the same fit error, and it
  forecast worse from live states (6 h daytime bias −0.22 °C against −0.10).
  `mpc.House` is unchanged.
- Fed measured heat (electricity × COP) instead of the emitter model, the
  estimator's 6 h forecasts are unbiased to 0.1 °C. Using the power sensor in
  the live estimator is a candidate.
- Return water sits 4.7 °C above the slab estimate while running and 2.8 °C
  idle (medians).
- Forecast cloud is a poor sunshine measure: on the 12th it said 66–100 % while
  PV made 5 kW and the room gained 1.4 °C with the compressor off. PV as a
  nowcast is still not used.

## 0.4.5: a compressor run lasts at least an hour

On 14 October, the first day of 0.4.4, the compressor ran 06:27–06:56,
13:39–14:14 and 14:39–15:09: three runs of about half an hour, two of them 25
minutes apart. The owner pointed out that a start costs electricity before the
unit runs efficiently, and that a floor-heated room cannot jump 0.6 °C in five
minutes, so such a reading is something else (an oven) and must not start or
stop the compressor. The half-hour runs came from the plan's half-hour first
blocks (and once a 40 °C burst for the 07:00 floor), and from lowering the
setpoint mid-run: at 14:08 it went from 30 to 29 °C and the unit stopped at
14:14.

- **Minimum run.** `mpc.MIN_RUN_STEPS = 2`: in the plan a start heats for at
  least two half hours, so the planner weighs a start as the hour it really is.
  The coordinator keeps the run it sees start (the operating state entering
  heating; a defrost pause or a lost reading inside a run is not a new start)
  going for its first hour: the setpoint stays clear of the return water and is
  never lowered during that hour. The over-band stop still overrides it.
- **Room averaging.** Control uses the room averaged over the last 30 minutes
  of sensor changes, not the latest reading. A slow change passes with at most
  15 minutes of lag; a short excursion is diluted.
- `start_cost` stays 0.15: at 0.5 replay showed fewer starts in frost but more
  hours over the band in mild weather.

Replay (`scripts/backtest.py`, which now models the hour hold and counts runs
under an hour), 0.4.4 → 0.4.5:

| Period | kWh/day | starts/day | runs under 1 h per day | hours/day over target + 0.5 |
| --- | --- | --- | --- | --- |
| 2–10 Oct | 4.7 → 4.6 | 4.8 → 3.0 | 2.2 → 0.0 | 6.8 → 7.8 |
| 10–20 Mar | 6.9 → 7.0 | 2.6 → 2.1 | 0.4 → 0.0 | 11.6 → 12.2 |
| 22 Jan–1 Feb | 39.6 → 39.7 | 2.8 → 3.6 | 0.3 → 0.0 | 1.1 → 1.7 |

The replay charges no electricity for a start itself, so it cannot show what
fewer starts save; it shows the comfort and kWh cost of holding runs is small.
The room minimum is unchanged (22.1–22.3 °C for a 22.5 °C target).

## 0.4.6: the plan knows how fast the setpoint may move

The owner noticed requests like 25 → 32 → 33 → 25 °C and recalled that the
PyScript changed the setpoint in small steps. It did: every 30 minutes at most
+2 °C up and −1 °C down (`execute_decision` in `legacy/smart_heating.py`). The
integration has the same limiter (`rise_per_hour`, `fall_per_hour`; defaults 4
and 2 °C per hour, the PyScript's values), but the first house was set to 6 and
10 with 0.4.0, and the planner ignored the limiter altogether: it planned jumps
the limiter then cut, so what ran was not what was planned.

- `mpc.simulate` and `mpc.plan` take the current setpoint and follow the
  requested levels only as fast as `Comfort.rise_step` / `fall_step` allow; the
  coordinator fills these from the options. A plan now knows that a ramp down
  keeps heating, and that a ramp up takes time.
- The over-band stop (`too_warm`) is not slowed by the fall limit.

Replay, by setpoint steps per half hour (rise / fall), with planning that knows them:

| Steps | Oct kWh/day | Oct hours over target + 0.5 | Oct starts/day | setpoint moves over 2 °C per day (Oct / Jan) | Mar kWh/day | Jan kWh/day |
| --- | --- | --- | --- | --- | --- | --- |
| +3 / −5 (first house since 0.4.0) | 4.7 | 6.2 | 3.4 | 5.8 / 12.3 | 6.8 | 39.5 |
| **+2 / −5** | 4.7 | 7.6 | 3.6 | 3.5 / 4.3 | 6.7 | 39.4 |
| +2 / −1 (PyScript) | 5.5 | 14.4 | 0.8 | 0.6 / 0.6 | 7.6 | 39.7 |

The PyScript's slow fall gives very few starts but keeps delivering heat after
it is needed: 12–17 % more electricity in mild weather and twice the hours over
the band in replay. The replay charges nothing for a start, so the true balance
is closer than that; at 0.3 kWh per start the October difference would roughly
cancel. Recommended for the first house: rise 4 °C/h (+2 per half hour, as the
PyScript), fall unchanged at 10 °C/h.
