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
   since the last cycle, compare with the thermometer, and correct: at night the
   surprise is attributed to the slab, in daylight to sun on the room, and a
   persistent miss becomes a slow drift term.
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
to `morning_hour`, and 0.5 °C of free headroom above target for storing heat.

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
