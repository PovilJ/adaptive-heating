# The 0.6 heating controller: a thermostat on the floor slab

From 0.6.0 the integration heats with the controller that won the lab race
([research/CONTROLLER_COMPARISON.md](research/CONTROLLER_COMPARISON.md)): the lab's
`hybrid`, made into production code. It replaces the 36-hour planner (`mpc.py`), the nightly
house refit (`learn.py`), the cold-night planner (`planner.py`) and the heating curve with its
guard layers. In the lab it used about 6–7 % less metered electricity than a faithful port of
0.5.3 and held the room on target instead of 0.3 °C warm. These are simulated numbers: the
electricity half rests on the unit's fitted part-load efficiency, and field results are pending
(see [Evidence](#evidence) and [Known limits](#known-limits)).

**It needs a heat pump that behaves like the Gree Versati:** a circulation pump that keeps
running while the compressor rests, a compressor start when setpoint − control sensor reaches
the restart hysteresis, and a stop when the control sensor is 2 °C over the setpoint, with
modulation in between. On other units use Observe only, or stay on 0.5.x.

The controller is one standard-library file, `custom_components/adaptive_heating/slab.py`.
Home Assistant never appears in it. The coordinator turns entity states into its inputs every
minute; the lab drives the very same file through `lab/controllers/production.py`.

## How it works, in plain words

**1. It reads the floor from the water.** The Versati's circulation pump never stops, so the
water coming back from the floor (the return) has the floor's temperature whenever the
compressor rests. While the compressor runs the return is warmer than the floor, so the
estimate subtracts a share (0.29) of the supply: floor = (return − 0.29 × supply) / 0.71. The
estimate is held still during hot water (and 20 minutes after it, while the loop still carries
tank water) and after a defrost. It does not need to be the true slab temperature, only a
consistent index; the learned level absorbs any offset.

**2. It gives the floor a target.** The floor target moves with:

| part | what it does |
| --- | --- |
| room target | the number you set |
| forecast cold | +0.2 °C per °C the next 1–9 hours are colder than the room target (the floor needs about that long to reach the room) |
| base offset | +1.0 °C; a starting point, the learned level below does the real work |
| forecast sun | −0.03 °C per W/m² of sun forecast for the next 1–9 hours: a sunny afternoon needs less floor this morning |
| room now | +3 °C per °C the room is under target (and less when it is over). The room value is corrected for sun shining on the thermometer |
| learned level | the room error added up over time (0.15 °C per °C·hour, ±6 °C): what this house needs in this season |
| learned time of day | a 24-hour pattern learned over days: the room error at each hour moves the floor target five hours earlier, so regular evening drops or sunny late mornings are met in advance |
| warmer hours ahead | +0.3 °C per °C the next three hours are warmer than the next day: heat a little more while the air is mild and the heat pump efficient |

**3. It decides when to run.** A run starts when the floor is 1.4 °C under its target, and ends
when it is 1.4 °C over. A run lasts at least an hour and the compressor rests at least 45
minutes. That gives about two long runs a day (median about five hours in the lab).

**4. It decides how hard to run.** The Versati starts its compressor when setpoint − its control
sensor reaches the restart hysteresis, and stops it when the control sensor is 2 °C over the
setpoint. Between those it modulates. The controller uses that:

- **Kick:** to start, it writes the smallest setpoint the restart rule accepts (return − 0.8 +
  hysteresis, rounded up), one degree more after six minutes without a start (twice at most).
  A start is a gentle one, not a hot burst.
- **Ride:** while running it sets the setpoint just above the water the unit is making, so the
  firmware holds about 6.5 kW: the unit's measured efficiency is clearly better at mid output
  than at its 3.6–4.4 kW minimum. When the floor falls behind (deep cold) it asks for more, up
  to 9 kW. It rewrites only when the ideal setpoint moved 1.3 °C, at most every eight minutes.
- **Stop:** one write 2 °C under the control sensor ends the run at once (the firmware rule),
  instead of waiting for the unit's own two-hourly surge or defrost to end it.
- **Park:** while resting, the setpoint sits just under the unit's own restart point for the
  floor's start threshold. If Home Assistant or the link dies, the unit itself still restarts
  when the floor gets cold. *Minimum water* is the lowest park, except that the park never
  reaches the unit's restart point for the water there now: a parked setpoint must not start
  the compressor. A small lowering of the park waits two hours, like a small raise, so the
  park does not flip between two values.

A start the unit makes by itself while the floor wants heat is adopted as a run, but not in
the five minutes after the controller's own stop (the unit is still reporting the run it was
told to end) and not with the floor already over its stop point. A run nobody needs (for
example left over from manual operation) is ended.

Writes: about 15–20 a day, never more than 46 in any 24 hours (40 for routine trims); the same
value is not rewritten within five minutes. A write counts only once the device has taken it.
All writes go to the heating-water setpoint. **Nothing else on the unit is ever written** — not
the restart hysteresis, not the mode.

## Fail-safes

| situation | what happens |
| --- | --- |
| heat-pump values unavailable (link drop, defrost or mode sensor missing) | no writes; the last setpoint stays; the controller keeps learning from the room |
| hot water, defrost, an operating state no mapping names | the floor estimate is held, the run waits; a stop waits until the defrost ends. Without a defrost sensor, a state that contains "defrost" counts as one |
| room value briefly `unavailable`/`unknown` | the last valid value is used with its true age (no jump of the floor target) |
| room value jumps (a sensor next to the oven, a sunny-morning report) | the controller's room moves at most 0.05 °C a minute, and the daily pattern takes at most 1.5 °C of room error |
| room thermometer unavailable, silent for 4 h, or stuck on one value for 12 h | learning stops, the room terms drop out, and the learned level relaxes (over about 6 hours) to what the house needed at this outdoor temperature while the room was known (a four-point curve learned at −15, −5, +5 and +15 °C). Heating continues. After an hour in Automatic, a Home Assistant notification asks you to check the sensor; it clears itself when the sensor is back |
| no forecast, or a failed fetch | the previous forecast is kept (retried after 5 min), then the hours of the last forecast still ahead; when those run out, the day-mean outdoor temperature and no sun |
| Home Assistant restart or reload | the learned level, daily pattern, fallback curve, 24-hour write log, the room-thermometer bookkeeping and (if under an hour old) the floor estimate are kept. Automatic resumes on the same version and options; an update or options change starts in Observe |
| Automatic ends (Observe, Off, reload, options change, an update's restart) | the controller's idle (park) setpoint is written once, so the unit keeps the floor near its start point itself and never keeps riding a run nobody watches. Not while an inhibit is on, a tank cycle runs, or after a value set by hand. If Home Assistant stops and does not come back, the unit keeps the last setpoint |
| manual change of the setpoint | manual hold until you select Observe then Automatic; a notification says why |
| a write the unit does not show within five minutes | asked once more; a second unconfirmed write, or three failed calls, give a manual hold with a notification |
| the unit keeps starting runs the floor does not need (3 in 24 h) | a notification: the restart hysteresis in use is probably larger than the unit's |
| another controller's inhibit, heating mode off on the unit, tank disinfection | no writes; learning pauses for the first two (the room is not ours then) |
| AC assistance session | the room's AC warmth cannot lower the floor target and does not train anything |

## Modes

- **Automatic:** the controller writes the setpoint and learns. When Automatic is selected while
  the compressor is running, it takes over the run instead of stopping it.
- **Observe:** it decides every minute and shows what it would write (status `observing`, the
  reason starts with "Observe:"), but writes nothing and learns nothing. Learning in Observe
  would measure whatever else runs the heat pump. The one write: when Observe follows
  Automatic, the idle setpoint that hands the unit back (above).
- **Off:** nothing is computed.

Automatic resumes after a Home Assistant restart or a reload when the version and every option
are unchanged and no manual hold was active. 0.1–0.5 always restarted in Observe; with a
controller that owns the runs, that left the unit on a ride setpoint until someone selected
Automatic again (in the lab, a 24-hour gap every four days cost 4 points of the season gain).
Tank disinfection and AC assistance still start in Observe.

Automatic needs the return- and supply-water sensors and the **heating-mode entity** (the
value that means space heating is enabled, `4` on the Versati): the controller starts and
stops the compressor itself, so it must tell "resting with heating on" from "heating off".
Without them the status explains what to map.

## Inputs from Home Assistant

| controller input | from |
| --- | --- |
| floor (water) | return- and supply-water sensors (required) |
| unit setpoint | the heating-water number |
| compressor running / hot water / idle | the operating-state sensor with its configured state values; defrost from the defrost sensor |
| heating enabled | the heating-mode entity |
| restart hysteresis | the unit's register, if mapped (read only, 2–10 K); else the *Restart hysteresis* option, 4 K by default (the first house's value since 21 Oct 2026). The Status sensor's `restart_hysteresis_source` says which |
| room | the room sensor as reported (no averaging; the last valid value through `unavailable`; at most 0.05 °C a minute of change) |
| outdoor now | the outdoor sensor, else the weather entity, else the forecast hour within 90 minutes |
| forecast temperature | the weather entity's hourly forecast, fetched every 30 minutes. Each row is labelled by its own time: the temperature is the forecast for that instant and the sun is the mean over the hour ending there, as in the lab's rows |
| forecast sun | rebuilt from the forecast's cloud cover (below) |

### Sun

Home Assistant forecasts give cloud cover, not irradiance, and the lab tuned the sun term on
irradiance. Each forecast hour's sun is the clear-sky irradiance at the house's location
(Haurwitz) times a cloud factor, `1 − 0.36 c − 0.16 c²⁰` (c = cloud cover 0–1). The factor was
fitted on the site's archived hourly irradiance and forecast-model cloud cover outside the
lab's ranking season (April–November 2026). Forecast models call a lot of thin cloud
"overcast", which still passes about half the clear-sky sun. On the held-out heating season it
gives a mean of 163 W/m² against 165 measured, with an hourly error of 61 W/m²; the textbook
Kasten–Czeplak law gives 131 W/m² and 85 W/m². A row without cloud cover uses its condition
(sunny 0 %, partly cloudy 50 %, otherwise overcast). Without a location in Home Assistant no
sun is credited. PV output is not used: it only measures the present hour, and the controller's
sun term looks 1–9 hours ahead.

Limits of the fit: it was made on Open-Meteo's model cloud. Home Assistant's default provider
(met.no) reported more cloud over 8 Oct – 6 Nov 2026 (mean 90 % against 81 %), and in late
autumn the estimate reads high against the lab's reference irradiance (145–157 W/m² against
126 by daylight; in March–April it is about right, 281 against 295). The learned level absorbs
the mean; the morning and evening shape is not corrected. A fit by sun elevation or on met.no
cloud would be the next step.

### Why the room is no longer averaged

0.4.5–0.5.3 averaged the room over 30 minutes so an oven could not start or stop the
compressor. With the slab thermostat that delay cost comfort in the lab (−9.77 % against
−10.03 % adjusted energy, season seeds 5–9, before the review rules) and runs already last at least an hour. Instead
the controller's room may move at most 0.05 °C a minute (3 °C an hour): a one-report spike
moves the floor target by at most 3 × 0.05 °C, while real changes pass within minutes. In
recorded data (8 Oct – 6 Nov 2026) one room sensor read up to 27.5 °C for an hour while two
others read 21.5–22.2 °C; the daily pattern now takes at most 1.5 °C of error from such an
hour.

## Options

New in 0.6.0, with first-house defaults. **Only errors on the target side are learned.** The
learned level moves the floor target, so it absorbs an offset in the floor estimate (the
supply share) and in the sun and weather terms. It does not correct the execution constants:
loop heat per °C sets the ride setpoint and so the actual output; the control-sensor offset and
the restart hysteresis place the kick, park and stop setpoints against the firmware's own
thresholds. A wrong value there can make the park start the compressor or a stop write miss.
Another house must measure them ([commissioning](#commissioning-another-house)).

| option | default | meaning |
| --- | --- | --- |
| Heat output while running | 6.5 kW | the ride output. 0 = the unit's minimum output ("low and slow"). The energy half of the lab gain rests on the measured part-load efficiency; if a field test shows flat efficiency, set 0 |
| Restart hysteresis | 4 K | used only when no hysteresis register is mapped. A value larger than the unit's makes the parked setpoint start the unit |
| Loop heat per °C | 2.02 kW/°C | flow × heat capacity (29 L/min) |
| Supply share in the floor estimate | 0.29 | how much of the supply the running return carries |
| Control sensor offset | −0.8 °C | the unit's control sensor minus the return (idle) or true supply (running) |
| Supply sensor offset | +0.3 °C | true supply minus the supply sensor |
| AC help below target | 1.0 °C | AC assistance is asked for only while the floor is heating and the room is this far under target |

Kept: room target, minimum water (the lowest park and ride setpoint, but a park never reaches
the restart point; a stop write may go lower, never under the device minimum, nor under 20 °C
unless minimum water is lower), maximum water (no write above it; rides stay ≤ 39 °C; the
setpoint number's own min/max narrow both further). The lab ranked Minimum water 25 °C and
Maximum water 40 °C (device 20–55 °C); other values run outside what was ranked, and 0.5
selections are kept by the migration, so check them.
comfort band (now only for tank-disinfection scheduling), stale minutes (outdoor and power
readings), solar preheat (a sustained PV surplus raises the room target by the preheat degrees
and pauses learning meanwhile), all mappings and the disinfection and AC options.

Removed (migration 1.2 deletes them from the entry; every other selection is kept): heating
curve slope/offset, room feedback, floor response hours, rise/fall per hour, control minutes,
predictive planner switch, and all cold-night planning options and mappings (sun entity,
protection room).

Fixed parameters (lab values, `slab.Params`): weather 0.2 °C/°C, offset 1.0 °C, sun
0.03 °C per W/m², forecast window hours 1–9, room 3 °C/°C, learning 0.15 °C/(°C·h) within ±6 °C,
thermometer sun 0.0008 °C per W/m², warm hours 0.3, daily pattern 1 °C/(°C·h·day), five hours
ahead, ±2 °C, 30-day memory; band 1.4 °C, minimum run 60 min, rest 45 min; extra output 2 kW per
°C behind, at most 9 kW; ride rewrite after 8 min and 1.3 °C; room lost after 4 h silent or
12 h unchanged; fallback curve follows over 72 h. Production rules: room slew 0.05 °C/min,
daily-pattern error cap 1.5 °C. The sun gain, the thermometer-sun term and the cloud factor
were fitted on this house and site.

### Commissioning another house

1. **Restart hysteresis:** map the unit's register (read only), or read it on the unit and set
   the option to it. If the status ever shows repeated "Stopping a run the floor does not
   need" (and the notification), the value in use is larger than the unit's.
2. **Sensor offsets:** with the compressor idle for an hour and the pump running, *Supply
   sensor offset* ≈ return − supply sensor; *Control sensor offset* = the unit's control
   (leaving-water) sensor − return, where the unit shows it.
3. **Loop heat per °C:** flow (L/min) × 0.0697 kW per (L/min·°C); the flow from the unit's
   display or flow meter, or from a known output: kW ÷ (supply − return) at a steady run.
4. **Supply share:** keep 0.29 unless the floor estimate jumps at each start and stop; the
   learned level absorbs a steady offset.
5. **Heat output while running:** keep 6.5 kW on a 6–10 kW Versati; on another unit, the
   output where its measured efficiency peaks, or 0 for the unit's minimum.
6. Run **Observe** for a few days: the proposed setpoints should be a kick a little above
   return − offset + hysteresis, a ride a few degrees above the return, and a park that never
   starts the compressor.

## Status

Sensors: **Heating cycle** (`idle`, `kick`, `ride`, `stop`, `wait`, `hold`), **Floor estimate**,
**Floor target**, **Proposed water temperature** (what this phase wants on the unit), **Limited
water temperature** (that value within the device and water limits), **Last commanded**,
**Actual water setpoint**, **Setpoint writes in 24 h**, **Status**, **Decision reason**.

The Heating cycle sensor's attributes are the controller's own view:

| attribute | meaning |
| --- | --- |
| `phase`, `reason` | what it is doing, in words |
| `slab_estimate`, `slab_target`, `start_below`, `stop_above` | the floor and its thresholds (°C) |
| `target_parts` | the floor target split into the parts in the table above |
| `running`, `minutes_in_phase` | its own run state |
| `room_error`, `room_sensor` | target − room (sun-corrected); `ok`, `missing`, `stale` or `frozen` |
| `forecast`, `forecast_outdoor_1_9h`, `forecast_sun_1_9h_wm2`, `sun_now_wm2`, `warmer_next_3h` | `fresh`, `held` (last forecast) or `none`, and the values used |
| `run_output_kw`, `wanted_setpoint`, `restart_hysteresis`, `writes_24h`, `unowned_stops_24h` | execution |
| `learned_integral`, `daily_pattern` (24 values, from 00 h), `fallback_curve` | what it has learned |

`slab_target` (and its thresholds) is shown within room target − 2 °C … 39 °C; a warm, sunny
room can push the computed target far lower (`target_parts` show it), which changes no
decision. The **Decision reason** carries no values that change every minute; the floor
estimate and target are their own sensors. Attributes that change nearly every minute are not
written to the recorder. The dashboard generator (`scripts/build_dashboard.py`) draws them on
its **Floor** tab.

The 0.5 sensors *Predicted minimum room temperature*, *Learning samples*, *Model prediction
error*, *Cold-night plan* and *Planned room target* are removed from the entity registry at
setup.

## Stored state

One store per entry, `adaptive_heating.<entry_id>`, schema 2: the room target, and the
controller's learned level, daily pattern, fallback curve, write log and runtime bookkeeping
(room-thermometer reference, last write, day-mean outdoor and floor estimate with their time),
plus the mode to resume with the version and options it was selected on. It is saved every ten
minutes, when the mode or target changes, and when Home Assistant stops. It belongs to the
room sensor, water sensors, setpoint and operating-state mapping; changing any of those starts
learning again (the target is kept). The 0.5 store is read once: its room target is kept, the
planner's estimates are dropped, and the four-week learning log
(`adaptive_heating.<entry_id>.learning`) is deleted. A fresh controller holds the room with the
room terms from the first minute; the daily pattern needs one to two weeks.

## What changed from 0.5.x

| 0.5.x | 0.6.0 |
| --- | --- |
| a 36-hour plan of half-hour water levels from a fitted house model, refitted nightly | a thermostat on the floor estimate; the level is learned from the room error |
| the firmware started and stopped runs; the plan only chose setpoints | the controller starts (smallest restart setpoint), rides (about 6.5 kW) and stops (one write) |
| comfort floor, Guard +1 °C, night minimum, too-warm stop, keep-running and start lifts, rise/fall limits | none of these: the lab showed they kept the room 0.3 °C warm and saved nothing |
| cold-night preparation and coasting | the forecast and learned daily pattern anticipate cold and sun every day |
| AC assistance requested by the cold-night plan | requested only while the floor heats and the room is clearly under target |
| room averaged over 30 min | room as reported, at most 0.05 °C/min of change |
| restart → Observe | restart or reload → Automatic again on the same version and options; leaving Automatic writes the idle setpoint |
| evaluated every 30 min (2 min while paused) | every minute |
| room sensor lost → paused | room sensor lost → keeps heating on a learned outdoor curve, with a notification |

## Evidence

All numbers are from the lab simulator, paired against `reference_tuned` (a plain room-holding
PI controller) on held-out seeds; "adjusted" is normalised electricity plus comfort priced at
0.54 kWh per °C·hour of |air − target| (see `lab/README.md`).

Every number here is from the simulator. It reproduces the metered electricity within about
2 % in normal weather, reads about 11 % high in the coldest recorded week and under-counts
starts by about 15 % ([SIMULATOR.md](research/lab/SIMULATOR.md)). The 0.5.3 port it is compared
with ran a mean outlet of 32.0 °C in the replay against 30.7 °C recorded, so the real 0.5.3 may
be a little cooler and cheaper than the port.

### Differences from the lab hybrid

The production core is the hybrid plus safety rules found by review against recorded house
data and Home Assistant behaviour. `Params(lab_hybrid=True)` switches them off: then, fed the
lab's own sun forecast and the unit's 4 K hysteresis, `production[lab_hybrid=1,ghi=forecast,
write_max=45]` reproduces `hybrid[delta=4]` bit for bit (all 75 season metrics identical, seed
5; `tests/test_slab.py` replays random minute streams through both).

| rule | why |
| --- | --- |
| the park never reaches the restart point, even when Minimum water is higher | the hybrid parked at 25 °C even when the return was so cool that 25 °C started the compressor; the start was then adopted and run for an hour. Production parks lower instead (6 % of the season under 25 °C; the unit took 20–24 °C stop writes in the record) |
| a small park lowering waits two hours | recorded data showed park pairs (26 then 25) minutes apart at whole-degree edges |
| no adoption within 5 min of the controller's own stop, nor with the floor over its stop point | the unit can report HEAT for a few minutes after a stop write; re-adopting forced another hour |
| an adopted run (handover, restart) has no minimum | a run left by the firmware is ended at once when the floor does not need it |
| room input at most 0.05 °C/min; daily pattern takes at most 1.5 °C of error | sensor spikes (one sensor read 27.5 °C for an hour) |
| a room report briefly `unavailable` keeps the last value (coordinator) | one missing minute moved the floor target by 3 × the room error and could start a run in a warm room |
| forecast rows labelled by their own time (coordinator) | Home Assistant rows carry the temperature at the hour's start |
| writes counted only once the device took them (coordinator) | refused writes no longer spend the budget |

Replay of 8 Oct – 6 Nov 2026 recorded minutes, open loop: setpoint writes 473 → 317,
one-minute floor-target jumps over 1.5 °C 71 → 27, park pairs within 15 minutes 3 → 0, and the
start at 24.1 °C room on 17 Oct (a one-minute dropout) is gone.

### Rankings

Paired against `reference_tuned` on held-out seeds.

**Season, Oct–Apr, seeds 5–9** (`lab/run.py --rank -c reference_tuned,hybrid,production -s season --seeds 5-9`):

| controller | adjusted | metered electricity | comfort K·h | mean air | mean abs error | starts/day |
| --- | --- | --- | --- | --- | --- | --- |
| hybrid (writes a 5 K hysteresis) | −10.56 ± 0.58 % | −5.13 % | −485 | 22.00 | 0.41 | 2.0 |
| hybrid at the unit's 4 K | −10.23 ± 0.55 % | −5.06 % | −466 | 22.00 | 0.41 | 2.1 |
| **production (0.6.0)** | **−10.27 ± 0.60 %** | **−5.04 %** | −462 | 22.01 | 0.41 | 2.0 |
| current_port (0.5.3), from the comparison | +0.4 % | +1.8 % | | 22.33 | 0.53 | 2.6 |

Against 0.5.3 that is about 6.8 % less metered electricity and a room 0.3 °C closer to target.
Production trails the default hybrid by a consistent 0.2–0.6 points, not noise: production
reads the unit's restart hysteresis and never writes it (the simulated unit sits at 4 K like
the real one; the hybrid writes 5 K), and it rebuilds sun from cloud cover instead of the lab's
irradiance forecast. The safety rules above gain about 0.25 points back (production with
`lab_hybrid=1`: −10.03 %).

**Robust variants, seeds 5–6:** production is `better` on all 20 mandatory variants, −7.8 %
(`legacy_cop`) to −11.2 % (`loss_minus20`, `partload_hi`), 0.2–0.55 points behind the default
hybrid on every one (mean 0.38). Mean air stays within 21.99–22.02 °C on all of them.

**Weeks, seeds 5–9 (diagnostic, fresh start each week):** adjusted oct −31.5, nov −11.4, dec
−3.0, jan −4.8, feb −10.5, mar −33.1, apr −46.3 % (hybrid at 4 K: −32.0, −10.6, −2.8, −5.1,
−11.1, −30.3, −35.9; the default hybrid: −35.7, −11.8, −2.1, −5.2, −12.0, −33.2, −46.9).
**In mild weeks the gain is comfort, not electricity:** metered electricity oct +2.1 %, mar
−0.7 %, apr −10.3 % against the baseline, against −5.4 % (nov) to −2.3 % (feb) in colder
weeks. Every controller starts a week with nothing learned and runs warm in the mild weeks
(mean air 22.11–22.22); a freshly updated 0.6 install starts the same way.

**Faults, season seeds 5–7 (scratch wrapper):** restarts every 2 days or every 6 hours with
3 minutes down (the resume path): −10.05 / −10.06 % against −10.07 % without. A 24-hour Observe
gap every four days with the unit left as it was (0.6 before this review): −5.92 %, mean air
22.09; with the idle setpoint written when Automatic ends: −7.15 %, mean air 22.04. Room sensor
dead or frozen for 10 days: −9.4 / −9.5 %.

Reproduce (results in `.local/`, private): the commands above with `--robust` or `-s weeks`;
`production[ghi=forecast]` uses the lab's irradiance, `production[smooth=1]` the 0.5 room
average, `production[lab_hybrid=1]` the hybrid's rules, and any `slab.Params` field can be set
as `production[q_run=0]`.

## Two things worth trying on the real unit

1. **Restart hysteresis 5 K.** The lab prefers 5 K (it was the unit's value until 21 Oct 2026):
   0.3 points over the season and most of the gap in mild weeks. The integration only reads
   it; set it on the unit once, and map the register so the controller follows it.
2. **The two-hold test** (UNIT_MODEL 7.2): over 4–6 similar mild days alternate whole runs at
   *Heat output while running* 0 and 6.5 kW and compare metered efficiency. If it is flat, set
   0; the comfort half of the gain does not depend on it.

## Known limits

- The energy half of the gain rests on the fitted part-load efficiency of this unit
  (`flat_load` in the lab: −1.4 % energy instead of −5 %).
- The house constants are the first house's and are not learned; another house must measure
  them ([commissioning](#commissioning-another-house)). The sun gain, thermometer-sun term and
  cloud factor are this site's.
- Paths only Home Assistant has (Observe, manual holds, AC shielding, learning paused during
  preheat) are covered by tests, not by the lab ranking; the lab wrapper drives the core as
  Automatic does.
- Parking under 25 °C (6 % of the season) assumes the restart rule holds there as above it.
- Without a room thermometer the comfort constraints break in the lab (mean air 22.16 °C);
  hence the notification.
- The daily pattern needs one to two weeks; a fresh controller in mild weather runs a little
  warm until the learned level settles (the first days after the update).
- Firmware behaviour the controller relies on: the immediate stop on a write 2 °C under the
  control sensor, the dead-band hold while riding, the restart rule. Soft-start effects and
  quiet mode cannot be measured in the lab.
