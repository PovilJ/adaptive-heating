# Lab unit model: the Versati seen from the water side

`lab/sim/unit.py` simulates the heat pump at a 1-minute step. A controller writes the leaving-water
setpoint and the restart hysteresis. The house model supplies the return temperature. The unit
model returns the supply temperature, the heat into the loop, the electricity and the status.

Everything later in the lab is ranked on this model. So this page gives the evidence, the counts
and the uncertainty for each rule and number. All of them are recomputed by
`lab/sim/unit_analysis.py` (private output: `.local/lab-results/unit/analysis.json`). The open-loop
validation is `lab/sim/validate_unit.py`. The model was built from the measured data and physics only. It
does not use the Home Assistant integration's controller code or its model documents.

Data: the 1-minute grid described in [data.md](data.md), February to November 2026. Three periods
matter here:

- **A**: legacy controller, late winter and spring, outdoor temperatures down to about -19 °C.
- **C1**: current season with the old Modbus bridge, which dropped out often.
- **C2**: current season with the new bridge (clean data).

The steady-state fits use about 37 000 "steady" heating minutes: at least 20 minutes into a run, no
defrost within 15 minutes, and electricity stable within 8 % over 5 minutes. Since review round 1
the COP fit uses the 33 478 of them whose 5-minute neighbourhood is also steady, smoothed over 5
minutes (section 7.1). The changes made after review round 1 are listed in section 13, those after
review round 2 in section 14.

## 1. Summary

| item | value | evidence |
|---|---|---|
| Control sensor | the "optional water sensor" (after the backup heater), not the plate-HX outlet | start and stop thresholds are exact on it (sections 3.1, 3.2) |
| Start rule | setpoint - t_ctrl >= restart_delta, acted on within about 1 minute | 56 drift starts, 0.0-0.2 K spread; no idle minute violates it except before DHW |
| Stop rule | t_ctrl >= setpoint + 2.0 K for 3 minutes; at once when a setpoint write makes it true | 58 of 62 writes at >= 2.0 K stopped, 1 of 351 below 1.8 K |
| Minimum run | 6 minutes (2 cases) | |
| Minimum off | not observable: the shortest heat-to-heat gap was 5 min. The model uses 3 min (manual, ASSUMED); runs that wait for it are flagged `min_off` | |
| 120-minute surge | at multiples of 120 min of running, 62 of 194 marks show +1.4 kW for about 4 min. 56 of those 62 runs then stop. The model's probability follows the mean electricity of the 30 minutes before the mark (logistic, 0.63 at 0.8 kW to 0.14 above 1.6 kW); outdoor temperature adds nothing once power is known | probably oil return; section 3.3 |
| Hot water | priority. A running heat cycle stops, then the DHW compressor starts after 7 min (33 of 36 cases). Heating can restart 7 min after DHW ends | |
| Circulation pump | runs all the time (about 0.10 kWh/h whether the compressor runs or not) | 2025 indoor-unit meter, idle sensor offsets |
| Loop flow | **29 L/min** (plausible 25-33) | four methods, section 5 |
| Minimum heat output | 1.8 K + 0.05 K/K x outdoor of loop delta-T, so about 3.6 kW at 0 °C and 4.3 kW at +7 °C | 76 runs at their floor |
| Maximum | manufacturer correction table x 9.5 kW (for example 10.8 kW at +7 °C/W35). Observed up to 12.7 kW momentarily | |
| Steady COP (measured at 29 L/min, supply about 30 °C) | 2.7 below -5 °C; 3.1 at -5..0; 3.7 at 0..3; 4.2 at 3..6; 5.3-5.4 above +6 °C | |
| COP model | smooth Carnot fraction of outdoor temperature (1-6 %/K, no steps), a regularised output-correction surface, a coil-frost term (-13 % just before a defrost), held constant above the measured 95th percentile of output; part-load slope bounded by `partload_lo` / `partload_hi` (x0.5 / x1.5, refitted) | sections 7.1, 7.2 |
| COP vs supply temperature | central **-3.2 to -3.7 %/K** (variants -2.4 to -3.9 %/K) | section 7.3 |
| COP vs output | rises steeply from minimum to about 6 kW, then flat (peak 7-9 kW at +7 °C); measured: 4.7 at 3-4 kW, 5.5 at 5-7 kW, 4.9 at 10-13 kW (+6..+9 °C, supply rising with output) | section 7.2 |
| Energy per start | 0.02-0.04 kWh of electricity whatever the preceding off time (6 min to days); 0.06 kWh in the model | section 7.4 |
| Defrost | the trigger state builds per kWh drawn from the outdoor air (a defrost every 7.0-7.5 kWh of air heat below -1 °C, 9.9 at +1, 17 at +3, 25 at +5 °C; x (output / 5 kW)^0.28) and **loses up to 40 % of itself over each compressor-off block** (time constant 15 min); no defrost within 50 compressor minutes of the last. Each one draws about 0.9 kWh from the loop and uses 0.13 kWh | 186 inter-defrost segments, first-passage and count fits (review round 2), section 8 |
| Validation (open loop, 79 days) | starts/day 0.98 (A), 0.94 (C1), **0.83 (C2)**; electricity +3.0 %, +2.2 %, -0.8 %; daily electricity error (mean absolute) 10.2 %, 8.8 %, 4.9 %; defrosts 156 / 6 / 14 vs 119 / 4 / 5 (127 / - / 12 on the recorded running pattern) | section 11 |

## 2. Sensors and conventions

- **Sensor offsets while water circulates without heating** (idle, more than 10 min after a stop,
  medians):
  - outlet - inlet = -0.30 K;
  - t_ctrl (optional water sensor) - inlet = -0.70 K.
  - While running, t_ctrl - outlet = -0.50 K at 4-6 kW. Review round 2: it depends a little on
    the output (-0.44 K below 4 kW, -0.48 at 4-6, -0.52 at 6-8, -0.60 above 8 kW; 44 000
    running minutes), so the model uses -0.80 - 0.025 x (Q - 5 kW) K against the true supply.
  - The offsets hold at every idle age from 2 to 600 minutes. The mean idle offset drifts by
    about -0.04 K per K of water temperature between 23 and 29 °C (unexplained, so not modelled).
- **True loop delta-T** = outlet - inlet + 0.30 K. The model's `t_supply` is on the inlet-sensor
  scale. The outlet sensor reads 0.30 K below it and t_ctrl 0.80 K below it.
- **Resolution.** Water and refrigerant temperatures report in 0.1 K steps, only on change. The
  condensing-pressure temperature and the setpoint report in whole degrees.
- **Outdoor temperature.** The model input is an ERA5-like 2 m air temperature (`wx_t`). The
  unit's own sensor reads 1-3 K warm while idle and in sun.

## 3. Firmware on/off logic

### 3.1 Start

The start gaps below are setpoint (new value) minus each sensor, measured in the minute before the
compressor flag. Starts counted are those from idle (off at least 10 min, no DHW in the previous
30 min).

| restart_delta | start type | n | gap to t_ctrl, min / median / max | gap to outlet, median | gap to inlet, median |
|---|---|---|---|---|---|
| 5 K | drift (no write within 5 min) | 41 | 4.8 / 4.9 / 5.0 | 4.5 | 4.2 |
| 4 K | drift | 15 | 3.8 / 3.9 / 4.0 | 3.6 | 3.2 |
| 5 K | after a write | 127 | 4.9 / 5.6 / 10.9 | 5.3 | 5.0 |
| 4 K | after a write | 41 | 4.0 (5th pct) / 4.7 / 6.9 | 4.2 | 4.0 |

- **The rule is setpoint - t_ctrl >= restart_delta.** The 0.1-0.2 K shortfall in the minute before
  a drift start is just the sample lead: the sensor crosses during the following minute.
- **Counter-test:** 141 idle minutes in heating mode had a gap >= delta. Only 27 of them were not
  followed by a start within 2 minutes, and they form 8 clusters:
  - 5 clusters were a heat run pre-empted by hot water: the unit waits about 7 min and then
    starts on DHW;
  - 3 clusters are link glitches (partial Modbus frames).
- **A setpoint write that opens the gap** starts the compressor within the same or the next minute.
  No extra delay after a write was found.
- **Pre-start:** in the minute before the compressor flag the outdoor unit draws about 0.22 kW (fan,
  valves). After a stop it draws about 0.1-0.3 kW for a minute. Both are tiny (about 0.005 kWh).
- **restart_delta values:** only 4 and 5 K were ever used. Other values (register range 2-10) are
  assumed to act the same way (ASSUMED).

### 3.2 Stop

Of 246 heat runs with clean data:

- 35 were stopped for hot water;
- 25 ended within 8 minutes of a defrost;
- 87 stopped with no setpoint write in the last 7 minutes;
- 99 stopped shortly after a setpoint write.

- **No-write stops:**
  - The run ended once t_ctrl had been >= setpoint + 2.0 K for 3 sampled minutes (44 runs) or 4
    (35 runs).
  - Electricity in the last 3 minutes was 2.4 kW (median), not the minimum. Almost every
    no-write stop follows a capacity surge: 66 of 87 came 0-12 min after a 120-minute mark of
    continuous running (run lengths cluster at 122-126 and 242-245 min).
  - At minimum output the unit almost never coasts up to +2 K on its own. It keeps running until
    something (a write, a surge, a defrost, hot water) ends the run.
- **Writes during a run (threshold test):** setpoint decreases during heat runs, outcome within 2
  minutes, binned by t_ctrl - new setpoint.

  | t_ctrl - new setpoint | n | stopped |
  |---|---|---|
  | < 1.0 K | 224 | 0 |
  | 1.0-1.8 K | 127 | 1 |
  | 1.8-2.0 K | 6 | 1 |
  | 2.0-2.5 K | 15 | 13 |
  | >= 2.5 K | 47 | 45 |

  So the stop threshold is t_ctrl >= setpoint + 2.0 K, and a write that crosses it stops the
  compressor at once rather than after 3 minutes. The same test on the outlet sensor is fuzzy (the
  1.5-2.3 K bins stop 1 of 123), which confirms t_ctrl as the control sensor.
- **Raising the setpoint during a run** does not restart anything. Capacity ramps up when
  setpoint - t_ctrl >= 1 K (section 4).
- **Minimum run time:**
  - A write 1 minute after a start (t_ctrl 2-5 K above the new setpoint) still ran 7 minutes.
  - A heat run pre-empted by DHW stopped after 6 minutes.
  - The model uses 6 minutes, which matches the manufacturer's 6-minute capacity hold.
- **Minimum off time:**
  - The shortest heat-to-heat gap was 5 min (1st percentile 6.6 min).
  - No case was found where the start condition held without a start inside a heat-to-heat gap.
  - The model uses the manual's 3 minutes (ASSUMED, never binding in the data).
- **Overshoot streaks:** t_ctrl >= setpoint + 2 K for 3-4 minutes without an immediate stop
  happened 20 times. All were surges followed by a short reverse-cycle dip, and the run ended a
  few minutes later. The model's 3-minute hold has a range of 3-4.
- **Register "heat run time"** (Word 34) reads 0 here. Its documented role (time in a "standby
  zone" before stopping) is not visible beyond the 3-minute hold.

### 3.3 The 120-minute surge

At multiples of 120 minutes of continuous running (194 clean marks), electricity jumps from about
1.0 to 2.5 kW for about 4 minutes in 62 cases. t_ctrl rises 2-4 K, and 56 of the 62 runs stop within
12 minutes. The likely cause is an oil-return cycle (inference).

A surge is more likely when the compressor has been running slowly. The rate by outdoor
temperature (mild weather means low speed):

| outdoor | < 0 °C | 0..3 | 3..6 | 6..9 | > 9 |
|---|---|---|---|---|---|
| surge rate | 0.11 | 0.32 | 0.33 | 0.40 | 0.57 |

The rate by power in the 30 minutes before the mark:

| power before the mark | < 0.9 kW | 0.9-1.1 | 1.1-1.3 | 1.3-1.6 | > 1.6 kW |
|---|---|---|---|---|---|
| surge rate | 0.63 | 0.44 | 0.33 | 0.14 | 0.11 |

Since review round 1 the model uses the power, not the outdoor temperature. A logistic fit on the
191 marks with complete power data gives P(surge) = 1 / (1 + exp(-(2.01 - 2.22 x P30))), with P30
the mean outdoor-unit electricity (kW) of the 30 minutes before the mark. Adding the outdoor
temperature to the fit changes nothing (coefficient -0.003 per K, same likelihood); outdoor
temperature alone fits worse (negative log-likelihood 113.3 vs 108.3). So a low-and-slow run in
cold weather now gets forced stops as often as one in mild weather at the same power, and a
high-output run in mild weather rarely does. The probability still fires deterministically
through an accumulator, so runs are reproducible. The old table is the variant `legacy_surge`.

**The timer restarts after a defrost** (review round 2, N6). In the 72 recorded runs that
contain a defrost, power surges (+0.4 kW for a few minutes, no write, no defrost nearby; 125
found) sit within -5..+10 min of a 120-minute multiple of the last defrost's end in 49 % of cases
and of the run start in 24 %. Of the 17 no-write stops at surges away from a 120-minute mark of
the run start (spring and autumn), most came 245-260 min after the last defrost. The model now
counts the 120-minute marks from the end of the last defrost inside a run (`surge_from_start`
keeps the round-1 clock). In open loop this shortens the long runs of period A (75th percentile
304 against 329 min; recorded 265).

**Is another stop mechanism missing?** Classifying all clean recorded heat-run ends (review round
2): in spring 121 runs ended 37 at a 120-minute mark, 12 at a surge away from a mark (above), 21
at or right after a defrost, 29 after a setpoint write, 20 for hot water and 2 otherwise; in
autumn 110 runs ended 18 / 5 / 0 / 72 / 12 and 3 otherwise; the cold week A0 10 runs ended 2 / 1 /
4 / 0 / 3 and none otherwise. So natural stops away from surges, defrosts, writes and hot water are
5 of 231 (about one per 300 run hours): there is no further firmware stop rule to find. The share
of runs that end near a 120-minute mark differs between the recorded data and archive weeks under
the reference mainly because the recorded controllers ended most autumn runs with setpoint writes.
In replay, the runs the model keeps going are writes that land at t_ctrl = setpoint + 2.0 K (the
recorded controller wrote exactly at the threshold) while the model's t_ctrl is 0.3-0.5 K lower
(15 of 16 misses in C1/C2); a controller that reads the simulated sensors does not meet that
case. No stochastic stop hazard was added: the residual natural-stop rate is too small to change
run lengths.

### 3.4 Hot water and defrost interplay

- **DHW pre-emption:** a running heat cycle stops, then the hot-water compressor starts after 7
  minutes (33 of 36; others 6, 9 and 18 min).
- **After DHW:**
  - The valve stays on the tank side for about 5-7 min; the inlet sensor shows tank-coil water
    at about 46 °C, then drops to loop temperature.
  - Heating can restart at the earliest 7 min after the DHW compressor stops (69 cases, 10th
    percentile 8 min).
- **The DHW tank heater** runs about 23 min right after nearly every DHW run (144 runs, IQR 15-24
  min). It is not in the metered electricity, and its rating is unknown. The model assumes 2 kW (ASSUMED) and reports
  it separately.
- **After a defrost:**
  - The unit recovers at high output (about 2.2 kW electrical).
  - If t_ctrl was already at or above setpoint + 0.5 K before the defrost, the run usually ends
    about 2 minutes later (20 of 28 such defrosts). Otherwise the run continues (7 of 127).
  - The model reproduces this with a recovery capacity of 4.3 K delta-T held for 3 minutes, and a
    2-minute stop hold during recovery.

### 3.5 Circulation pump

The pump runs continuously at fixed speed:

- **2025 indoor-unit meter:** it drew 0.09-0.10 kWh per hour in hours with no compressor at all and
  0.10 kWh/h with the compressor running (0.13 above 2 kWh/h outdoor, probably relays or the
  backup-heater contactor). That is a pump of about 75-85 W plus controls, the full rating of
  the Versati's pump.
- **Idle temperatures:** while idle, outlet, inlet and t_ctrl hold fixed offsets from each other.
  The inlet decays smoothly at about 0.33 K/h and ends about 1 K above the room after 3-10 h. That
  is water circulating through the slab, not standing in the unit.
- **No sign of modulation:** delta-T scales with output (2.0 K at minimum, 4-6 K at high output),
  which points to a constant flow.

The model's `p_total` adds 0.10 kW for the indoor unit around the clock.

## 4. Capacity control (modulation)

**Start-up** (131 clean starts from idle, no write or defrost in the first 40 min; medians; heat at
29 L/min):

| minute | -1 | 0 | 1 | 2 | 3 | 5 | 7 | 9-11 | 13 | 17 | 22-37 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| electricity kW | 0.22 | 1.47 | 1.57 | 1.57 | 1.60 | 1.74 | 1.80 | 1.84 | 1.57 | 1.28 | 1.27-1.22 |
| heat kW (end of minute) | 0 | 5.7 | 6.9 | 7.5 | 7.9 | 8.3 | 8.7 | 8.7 | 8.5 | 6.1 | 5.9-5.7 |
| t_ctrl - setpoint K | -5.1 | -3.1 | -2.0 | -1.8 | -1.5 | -1.2 | -0.5 | -0.2 | -0.3 | -0.5 | -0.6 |

- The compressor starts at about 1.5 kW. Heat reaches the water within the first minute.
- Output climbs for about 10 minutes, holds, then drops over minutes 11-17 to the steady level.
- The model:
  - starts at 3.6 K of delta-T (7.3 kW);
  - delivers 40 %, 85 % and 97 % of it in the first three minutes;
  - holds without ramping down for 10 minutes;
  - then follows the dead band below.

**Steady state:** the rate of change against the error e = setpoint - t_ctrl, over 4 minutes (more than
14 min into runs, no write, defrost or surge window).

| e (K) | < -1.5 | -1.5..-0.6 | -0.6..-0.3 | -0.3..0 | 0..0.6 | 0.6..1.0 | 1.0..1.5 | 1.5..2.5 |
|---|---|---|---|---|---|---|---|---|
| minutes | 199 | 1289 | 4931 | 3624 | 13926 | 10899 | 932 | 487 |
| electricity W/min (mean) | -21 | -7 | -13 | -5 | -4 | 0 | +12 | +43 |

The unit holds its output while t_ctrl is 0.6-1.0 K below the setpoint. It drifts down slowly
just above that and ramps up at about +45 W/min (+0.07-0.10 K of delta-T per minute) once it is
more than 1.5 K short.

The model uses a dead band of +0.1..+1.0 K:

- above 1.0 K: up 0.10 K/min;
- below 0.1 K: down 0.03 K/min plus 0.6 K/min per K of extra overshoot (capped at 0.35 K/min).

Moving the lower edge from -0.3 to +0.1 K removed a +0.3 K outlet bias in validation.

**Setpoint jumps:**

- A raise of more than 1 K above t_ctrl ramps the output up at about 45 W/min (about 1 kW of heat
  per 5 minutes) until the error is back in the band.
- A cut to below t_ctrl - 2 K stops the compressor (section 3.2).
- Smaller cuts ramp the output down slowly. The current controller often writes the setpoint 1-1.5 K
  below t_ctrl (106 writes), which slows the unit without stopping it.

**Minimum output** (each run's lowest 10-minute mean delta-T while still above setpoint, 76 runs):
1.83 K + 0.049 K per K outdoor, residual SD about 0.5 K.

| outdoor | -5..0 | 0..3 | 3..6 | 6..9 | 9..16 |
|---|---|---|---|---|---|
| floor delta-T (median of run minima) | 1.6 | 1.9 | 2.0 | 2.2 | 2.1 |
| heat at 29 L/min | 3.3 kW | 3.9 kW | 4.1 kW | 4.5 kW | 4.3 kW |
| electricity at the floor | 1.29 kW | 1.19 | 1.07 | 0.84 | 0.80 kW |

The model: 1.8 + 0.05 x T_out K, clamped to 1.4-2.4.

**Maximum:**

- The model uses the manufacturer's maximum-capacity correction table x 9.5 kW: 9.8 kW at 0 °C/W35,
  10.8 kW at +7 °C, 7.0 kW at -15 °C.
- Observed 99th percentiles: 4.2 kW electrical and a 5.2 K delta-T at -20..-12 °C. Mild weather
  gave short peaks to a 6.3 K delta-T (12.7 kW at 29 L/min) in surges and start-ups.
- Quiet mode was never used. The model cuts maximum output to 70 % (ASSUMED from the manual).
  Since review round 1 frost follows the air heat, so quiet mode's lower output sets its frost;
  the old extra x1.5 (one field report) is the variant `quiet_frost`.

## 5. Loop flow rate

There is no flow meter, so each method below has its own assumption.

| method | assumption | flow, L/min |
|---|---|---|
| (a) refrigerant cycle: R32 cycle COP from measured evaporating (outdoor-coil sensor) and condensing (outlet + 0.5-2 K) temperatures, x overall compressor efficiency, x measured electricity | overall efficiency 0.5 / 0.6 / 0.7 (the datasheet points imply 0.48-0.72) | 31 / 35 / 41 |
| (b) design flow | 9.5 kW nominal at 5 K spread | 27.2 |
| (b') datasheet COP applied to hot-water runs (near full load; datasheet COP interpolated by outdoor and outlet) | rating COP = outdoor-unit COP + pump | 29.4 (IQR 27.9-31.8, 93 runs) |
| (b') same, heat runs at 1.8-3.2 kW | near full load at 0 °C | 30.6-32.0 |
| (b'') maximum-capacity table at -17 °C (3.5 kW in, 4.3 K delta-T) | unit at its table maximum | 23.4 (an upper bound only if the table is exact) |
| (c) house energy | daily heat vs indoor-outdoor difference gives UA 0.084 / 0.097 / 0.111 kW/K at 25 / 29 / 33 L/min | not identifiable without an independent heat-loss figure |
| (d) DHW tank | the loop delta-T integral over the tank-sensor rise gives V_tank / F = 9.6 min (IQR 8.9-10.2) | 20 / 26 / 31 for a 190 / 250 / 300 L tank |
| cross-check: fitted model (29 L/min) vs datasheet at its rating points, which lie outside our data (W35-W45) | | A7/W35 4.86 vs 4.80; A7/W45 3.57 vs 3.72; A-7/W35 2.79 vs 2.93; A-7/W45 2.13 vs 2.29 (all within 5 %) |

**Reconciled: 29 L/min**, with variants at 25 and 33 L/min:

- About 14 % either way covers methods (b), (b') and the cold-weather table.
- Method (a) points higher (about 35). It is the weakest: the measured discharge temperature is
  15-25 K below an isentropic discharge. Gas injection and a wet suction (suction = coil temperature
  to 0.0 K) make a direct refrigerant enthalpy balance impossible.
- The datasheet cross-check is the strongest single argument. A 25 or 33 L/min model would sit
  about 14 % below or above all four datasheet points.
- Two facts would pin the flow down: the tank volume from the nameplate (method (d)), or a reading
  of the unit's flow or compressor frequency registers (Words 142/143).

Every heat number in the model scales with the flow, and the COP fit was redone for each flow. So
the variants all match the measured electricity equally well. They differ in how much heat that
electricity buys, which the data cannot show without a flow measurement.

## 6. Refrigerant temperatures (what the sensors say)

- **The "discharge pressure temperature" is not a usable condensing temperature.** It reads
  1.0 K *below* the outlet water (1.58 K at zero load, +0.10 K per kW), and it is reported in whole
  degrees. A condenser cannot run colder than the water it heats, so it is biased low by at least
  1.5-2 K. Its slope (+0.10 K/kW) is used for the condensing approach. The level (supply + 1.0 K) is
  ASSUMED.
- The liquid line leaves the condenser at the outlet temperature (+0.7 K at zero load, -0.15 K/kW):
  little subcooling.
- **The outdoor coil (evaporating) temperature:**
  - It is outdoor - 1.35 K - 0.42 K per kW of heat (RMSE 2.6 K) below about +5 °C outdoor.
  - It never rises above about +2.5 °C. From +5 to +16 °C outdoor it stays at +2.1..+3.3 °C.
  - So the unit does not take the extra Carnot benefit of mild air. The fan or valve control
    limits the evaporating temperature.
  - The model caps the evaporating temperature at +2.5 °C. The measured COP is flat above about
    +6 °C (5.3 at +6..+9, 5.4 at +9..+16).
- Suction = coil temperature (median difference 0.0 K): no measurable suction superheat at that
  sensor. Economizer outlet - inlet is +4.3 K (median), so vapour injection is active in normal
  heating. The discharge temperature is 40 °C (median; 36-49 °C).
- **Refrigerant: R32**, inferred. It fits the Versati III generation (2019+): the Modbus map with
  economizer sensors, a two-stage injection compressor, 9.5 kW at A7/W35. Not confirmed from the
  nameplate. Only analysis uses the property routines (`lab/sim/r32.py`, Peng-Robinson; saturation
  pressure within 1 % of reference, latent heat within 1.5 %).

## 7. COP model

### 7.1 Form and fit (review round 1)

```
P_outdoor = p0 + Q / COP_core                          (Q <= q95(T_out))
P_outdoor = P_outdoor(q95) x Q / q95                    (Q >  q95: COP held constant)
COP_core  = eta(T_out) x (1 - d x frost) x exp(G(T_out, Q)) x (Tc + 273.15) / (Tc - Te) x exp(-x (T_supply - 30))
eta(T)    = e0 + e1 tanh((T - tm) / sc) + e2 T
Tc = T_supply + 1.0 + 0.10 Q          (condensing; slope from the pressure sensor)
Te = min(T_out - 1.35 - 0.42 Q, 2.5)  (evaporating; outdoor-coil sensor)
```

- **eta** is a smooth, monotone Carnot fraction (5 parameters) instead of the old 10 free knots.
  The old knots made COP a staircase in outdoor temperature (+9-10 %/K across 0..+2 and +4..+6 °C,
  +1 %/K elsewhere).
- **G** is a correction surface on 5 x 5 knots (outdoor -12, -4, +2, +6, +12 °C; output 3, 5, 7,
  9, 11 kW), bilinear and flat outside. It is penalised towards zero and towards smoothness, much
  more strongly along the outdoor axis than along the output axis. It lets COP peak at mid
  output where the data say so.
- **frost** is the unit's own frost level (0 just after a defrost, 1 just before the next; section
  8). In the fit it is the share of the air heat drawn since the last defrost, relative to the
  total before the next one. **d = 0.13**: the coil loses 13 % of COP over a defrost cycle. This
  is the explicit coil-degradation term; humidity left no further residual (ratio 0.98-1.00 in
  four RH bins).
- **q95(T)** is the 95th percentile of measured steady output per outdoor band: 9.9 kW below
  -5 °C, 7.0 at -5..0, 7.5 at 0..3, 9.2 at 3..6, 10.3 at 6..9 and 8.7 above +9 °C (29 L/min).
  Above it the model does not let COP rise further.
- **Fit:** least squares on 33 478 steady minutes, each smoothed over 5 minutes (sensor noise in
  the output axis otherwise dilutes the output dependence), weight per day 1/sqrt(minutes).
  RMSE 0.119 kW (the old 10-knot form gives 0.143 on unsmoothed minutes).
- **Defrost is separate:** it is an explicit event in the dynamic model (section 8).

| fit (flow, x) | eta(T): e0 / e1 / tm / sc / e2 | p0 kW | d | RMSE kW | role |
|---|---|---|---|---|---|
| 29 L/min, x = 0.015 | 0.762 / 0.326 / 5.73 / 5.09 / 0.0039 | 0.25 | 0.13 | 0.119 | **central** |
| 25, 0.015 | 0.678 / 0.294 / 5.79 / 4.99 / 0.0034 | 0.34 | 0.14 | 0.121 | `low_flow` |
| 33, 0.015 | 0.853 / 0.365 / 5.64 / 5.04 / 0.0043 | 0.25 | 0.13 | 0.119 | `high_flow` |
| 29, 0 | 0.559 / 0.196 / 5.55 / 5.22 / 0.0028 | 0.02 | 0.12 | 0.120 | `shallow_outlet` |
| 29, 0.030 | 0.877 / 0.388 / 5.67 / 4.82 / 0.0034 | 0.43 | 0.15 | 0.120 | `steep_outlet` |
| 29, 0.015, output dependence of the surface x 0.5, refitted (review round 2) | 0.795 / 0.350 / 5.55 / 5.21 / 0.0025 | 0.31 | 0.14 | 0.125 | `partload_lo` (mandatory) |
| 29, 0.015, output dependence of the surface x 1.5, refitted (review round 2) | 0.737 / 0.306 / 5.94 / 4.97 / 0.0053 | 0.21 | 0.12 | 0.121 | `partload_hi` (mandatory) |
| 29, 0.015, p0 = 0.15, no surface | 0.595 / 0.163 / 4.43 / 4.97 / -0.0086 | 0.15 | 0.13 | 0.166 | `flat_load` (diagnostic only since review round 2) |
| old 10-knot form, p0 0.37 | knots | 0.37 | - | 0.143 | `legacy_cop` |

**Residual, model / measured electricity, by outdoor band and output bin (central):**

| outdoor | 3-4 kW | 4-5 | 5-6 | 6-7 | 7-8 | 8-9 | 9-10 | 10-13 |
|---|---|---|---|---|---|---|---|---|
| < -5 °C | 1.08 | 1.02 | 1.02 | 1.01 | 1.03 | 1.02 | 1.00 | 1.01 |
| -5..0 | 1.01 | 1.00 | 1.00 | 1.02 | 1.01 | | | |
| 0..+3 | 1.02 | 1.00 | 1.02 | 1.03 | 1.04 | 1.13 | | 1.12 |
| +3..+6 | 0.94 | 0.97 | 0.98 | 1.00 | 0.97 | 1.00 | 1.02 | 0.99 |
| +6..+9 | 1.05 | 1.03 | 1.01 | 1.02 | 1.00 | 0.99 | 0.99 | 0.98 |
| > +9 | 1.00 | 1.00 | 1.02 | 1.02 | 0.98 | 0.99 | 0.99 | |

The old model was 4-8 % high at 3-7 kW and 4-10 % low at 9-13 kW above +6 °C, and 8 % low at 3-4 kW
and 19 % high at 10-13 kW at 0..+3 °C (review round 1, C1). The new one is within ±3 % in every
well-populated bin. The two 0..+3 °C bins above 8 kW hold 315 minutes. The `flat_load` fit leaves
0.71-0.94 at low output and 1.07-1.25 at high output: it is a deliberate counter-hypothesis, not a
fit.

**COP per +1 K of outdoor temperature** (central, W30, 5 kW), -15..+14 °C: +1 to +3 %/K below
0 °C, rising smoothly to +6 %/K at +2..+6 °C (frosting coil and lift), then falling to 0 once the
evaporating temperature reaches its +2.5 °C cap (+7 °C and above). Neighbouring kelvins differ by
at most 1.9 %/K; the self-check asserts < 3.5.

### 7.2 COP at minimum, mid and maximum output (central, steady, no frost)

| outdoor | output | COP at W30 | COP at W35 | COP change, +1 K supply (30 -> 31) |
|---|---|---|---|---|
| -7 °C | min 2.9 kW | 2.30 | 2.00 | -2.8 % |
| -7 °C | 6 kW | 3.33 | 2.88 | -3.0 % |
| -7 °C | q95 8.0 kW and max 8.5 kW | 3.53 | 3.04 | -3.0 % |
| 0 °C | min 3.6 kW | 3.06 | 2.61 | -3.2 % |
| 0 °C | 6 kW | 3.81 | 3.24 | **-3.3 %** |
| 0 °C | q95 7.3 kW and max 9.8 kW | 3.95 | 3.35 | -3.3 % |
| +7 °C | min 4.3 kW | 4.89 | 4.17 | -3.2 % |
| +7 °C | 6 kW | 5.47 | 4.61 | **-3.5 %** |
| +7 °C | q95 10.1 kW and max 10.8 kW | 5.71 | 4.75 | -3.7 % |

- **COP against output:** the minimum is 20-30 % below 6 kW, as measured (4.7 at 3-4 kW against
  5.5 at 5-7 kW, both at a 29.7-29.9 °C supply, +6..+9 °C). Above about 7 kW COP is flat at a
  fixed supply. In the data it falls at high output because the supply rises with output (33.7 °C
  at 10-13 kW). The old model rose +24 % from minimum to maximum at +7 °C; between 6 kW and the
  maximum it now rises 4 % (was 11 %).
- **Variants:** `flat_load` keeps COP within 2-6 % of its 6-kW value over the whole output range;
  `legacy_cop` reproduces the old rise.
- **Part-load bounds (review round 2, N3).** `flat_load` is rejected by the data (RMSE 0.166 vs
  0.119 kW; model/measured 0.71-0.94 at low output, 1.07-1.25 at high output), so a strategy
  that exploits the measured part-load curve could never pass it, and one that moves towards
  minimum output was penalised by the nominal model alone. It is now a diagnostic. The mandatory
  pair scales the output dependence of the central surface (relative to its value at 5 kW per
  outdoor knot) by 0.5 and 1.5 and refits eta, p0 and d. Both fit the data almost as well (RMSE
  0.125 / 0.121; minimum-output bins within -8..+6 % and -3..+18 %). COP at 6 kW over COP at
  minimum output, W30:

  | | -7 °C | 0 °C | +7 °C |
  |---|---|---|---|
  | `partload_lo` | 1.29 | 1.18 | 1.12 |
  | central | 1.45 | 1.25 | 1.12 |
  | `partload_hi` | 1.65 | 1.34 | 1.12 |
  | `flat_load` | 1.05 | 1.03 | 1.05 |
  | measured, 3-4 kW vs 5-6 kW at equal supply | | 1.22 (-5..0 °C) | 1.18 (+6..+9 °C) |

  At +7 °C the minimum output (4.3 kW) sits close to the surface's 5-kW knot and the ratio
  comes mostly from the fixed overhead p0, which every refit keeps near 0.2-0.3 kW: the data pin
  the mild-weather part-load penalty down better than the cold one. Fixing p0 at the central
  value instead gives 1.10 / 1.14 at +7 °C (RMSE 0.128 / 0.121).
- **Measure it on the real unit** to narrow the band: two 3-hour holds at the same supply
  temperature (for example 30 °C), one at minimum output and one at about 6 kW, at +5..+8 °C
  outdoor (setpoint held, restart hysteresis unchanged; the 6-kW hold needs a setpoint a few K
  above the return).
- **Practical consequence:** running at the minimum output is less efficient than mid output, but
  pulsing at high output gains nothing over mid output.

### 7.3 How much COP each +1 K of supply temperature costs

| source | %/K |
|---|---|
| Manufacturer datasheet, full load (A7 and A-7, W35->W45) | -2.1 to -2.2 |
| Pure Carnot structure + overhead (`shallow_outlet`), 0 / +7 °C | -1.9 / -2.0 to -2.2 |
| **Central model** (x = 0.015), 0 / +7 °C, min to max output | **-3.2 to -3.3 / -3.2 to -3.7** |
| `steep_outlet` (x = 0.030), 0 / +7 °C at 6 kW | -3.9 / -3.7 |
| `shallow_outlet` (x = 0), 0 / +7 °C at 6 kW | -2.4 / -2.9 |
| Direct regression of ln COP on supply, outdoor and ln Q, by outdoor band (day-bootstrap 90 % CI) | -4.2 (-5.2..-3.1) at -3..+3 °C; -4.1 (-4.9..-3.4) at 3..6; -4.6 (-5.3..-3.8) at 6..16 |

- **The data say about -4 %/K.** This survives:
  - controls for humidity, wind, run age, hour of day, sun and the coil temperature (-3.9 to -4.7);
  - between-run comparisons (-4.2) and within-run ones (-6);
  - the frost-free band above +6 °C (-4.25 between runs).
- **Physics and the datasheet say about -2 %/K at full load.** A steeper slope at part load is
  physically possible (more compressor speed for the same heat at higher pressure) but has not been
  verified.
- **A known small bias:** if the idle sensor offset really drifts with temperature (section 2), it
  makes the data slope about 0.8 %/K too steep.
- **The central model takes the middle (-3.2 to -3.7 %/K),** and both ends are variants. A controller whose
  advantage depends on the slope should be checked against `shallow_outlet` and `steep_outlet`.

### 7.4 Cost of a start

The circulation pump never stops, so heat left in the unit after a stop still reaches the floor.
What a start costs is electricity.

- **Measured:** the first 20 minutes of 174 runs used 0.02 kWh more than the steady model predicts
  for the heat they delivered (IQR -0.01..+0.04). The same comparison over minutes 20-45 gives
  -0.02 (model bias), so a start costs about **0.04 kWh** net.
- **Pre-start and post-stop minutes** add about 0.005 kWh.
- **Against the preceding off time** (review round 1, 218 runs with clean data, against the
  smooth steady model): median excess 0.04 kWh after 0-15 min off (20 runs), 0.01 after 15-30
  (14), 0.02 after 30-60 (13), 0.03 after 1-2 h (29), 0.04 after 2-4 h (53) and 0.04 after
  longer (89). A restart after a short pause does not cost more energy than one after a night.
  The shortest gap in the record is 6 minutes, and no day had more than about 8 starts.
- **The model** (start ramp, pre-start minute, post-stop minute) costs 0.06 kWh per start against a
  steady run of the same heat. The `high_start_loss` variant adds 0.15 kWh per start (0.21 in total).
- **This is small.** At about 4 starts a day it is about 0.2 kWh/day, about 2 % of mild-weather
  electricity. Wear is not in it: since review round 2 a ranking must hold for any start cost
  from 0.05 to 0.3 kWh (SIMULATOR.md section 5); before, it added an ASSUMED 0.2 kWh per start
  (`lab/sim/ranking.py`), and runs beyond 8 starts a day or with more than 5 % of runs under
  15 minutes are flagged as extrapolated.
- **The real cost of cycling here is indirect:**
  - each start overshoots the outlet (supply climbs to the setpoint quickly at high output);
  - minimum output runs at a worse COP (section 7.2);
  - surges and post-defrost stops add starts.

## 8. Defrost

193 flagged events (100 % precision, about 95 % recall against the reverse-cycle signature).

**Frost builds per kWh drawn from the outdoor air** (review round 1, C2) **and the trigger state
partly resets while the compressor is off** (review round 2, N1). The round-1 model built frost
per run-minute regardless of output until review round 1; the 158 intervals between defrosts said
otherwise (run hours between defrosts scale with mean output to the power -1.34, 90 % CI
-1.64..-1.05). The second review then showed that the air heat drawn per defrost depends on how
much the unit was idle in between: at -2..+1 °C, intervals with under 2 h of idle above +1 °C drew
8.1 kWh per defrost (60 intervals), those with 4 h or more 36.7 (5).

The model now adds, each running minute (heat or hot water),

```
frost += (Q - P) / 60 / K(T_out) x (Q / 5 kW)^0.28          (no frost above +10 °C)
```

keeps `1 - rmax (1 - exp(-L / 15 min))` of it over a compressor-off block of L minutes, and
defrosts when frost reaches 1, after at least 10 run minutes and at least 50 compressor minutes
since the last defrost (169 recorded intervals: minimum 32, 5th percentile 52). Hot-water runs
supply air heat P x (COP at a 45 °C supply - 1). K is log-linear between knots at -15, -7, -3,
-1, +1, +3, +5 and +8 °C (ERA5, per minute).

**How it was fitted** (`unit_analysis.frost_stop_fit` and `frost_count_fit`, `python -m
lab.sim.unit_analysis review2`): all 186 inter-defrost segments of the record (169 end in a
defrost; 17 end in a data gap and are censored).

1. **Timing (decides rmax).** From the end of every recorded defrost the model's frost runs along
   the recorded running pattern until it would defrost. The loss is the squared log ratio of the
   air heat the model draws to its defrost against what the unit drew; a censored segment counts
   only if the model defrosts inside it. Profile over rmax (K and the humidity gain refitted at
   each):

   | rmax | 0 (kept while off) | 0.2 | 0.3 | **0.4** | 0.5 | 0.6 | 0.75 |
   |---|---|---|---|---|---|---|---|
   | loss | 65.99 | 59.16 | 57.90 | **57.40** | 58.25 | 59.50 | 64.72 |

   The residual SD is 0.58 in log, so the 90 % profile threshold is a loss rise of 0.92: rmax
   0.3-0.5 is inside, 0.2 and 0.6 just outside, and 'kept while off' (the round-1 structure) is
   8.6 worse. The time constant is not identified beyond 'minutes' (5, 15, 30, 60 min give
   similar fits; 15 used). Removal does not depend on the outdoor temperature during the off
   block (fits with separate shares below and above 0, +2 and +4 °C gave 0.46-0.52 for both):
   it looks more like the firmware's trigger state than melting.
2. **Counts (sets K).** At each rmax, K is set so that the model's defrosts on the recorded
   running pattern of the whole record (reset only where the model defrosts) match the 176
   recorded ones by outdoor band and by class (an off block of 4 h or more ended within the 12 h
   before the defrost, or not): Poisson deviance plus a smoothness penalty on log K. The
   humidity gain is 0: once K is per minute, neither fit finds one (the round-1 +2.15 %/% RH came
   from bins confounded with temperature). `more_frost` covers a humid winter.

| outdoor (ERA5) | -15 | -7 | -3 | -1 | +1 | +3 | +5 | +8 °C |
|---|---|---|---|---|---|---|---|---|
| K, kWh of air heat per defrost, **central (rmax 0.4)** | 7.1 | 7.2 | 7.0 | 7.5 | 9.9 | 17.3 | 25.2 | 31.6 |
| `frost_melt_lo` (rmax 0.2) | 7.0 | 7.4 | 7.6 | 8.0 | 10.9 | 20.4 | 32.9 | 50.4 |
| `frost_melt_hi` (rmax 0.6) | 7.0 | 6.7 | 6.5 | 6.9 | 9.8 | 16.8 | 25.8 | 25.2 |
| `frost_no_melt` (rmax 0, diagnostic) | 7.4 | 9.2 | 9.9 | 9.7 | 14.8 | 20.3 | 56.7 | 192.5 |
| round 1 (`legacy_frost_r1`), band of the defrost start | 3.9 (< -10) | 6.4 | 7.2 | 9.6 | 13.0 | 24.4 | 84 | 120 |

Defrosts by outdoor band (recorded / central model on the recorded running pattern), without and
with a long off block in the 12 h before: below -8 °C 11 / 11 and 5 / 5; -8..-4 9 / 9 and 1 / 1;
-4..-2 14 / 14 and 9 / 8; -2..0 14 / 16 and 28 / 30; 0..+2 12 / 12 and 33 / 36; +2..+4 5 / 5 and
21 / 23; +4..+6 0 / 1 and 8 / 13; above +6 0 / 0 and 6 / 6. Total 176 recorded, 190 model.

**The two interval classes of the second review** (median recorded / model air heat to the
defrost, 1 = unbiased; short = under 2 h of idle above +1 °C, long = 4 h or more):

| running-mean outdoor | -2..+1 °C | +1..+3 | +3..+6 | +6..+12 |
|---|---|---|---|---|
| intervals short / long | 57 / 5 | 13 / 13 | 3 / 15 | 2 / 9 |
| central (rmax 0.4), short / long | 1.04 / 2.96 | 0.78 / 1.23 | 0.49 / 1.03 | 0.35 / 1.14 |
| kept while off (rmax 0), short / long | 0.97 / 3.37 | 0.64 / 1.57 | 0.41 / 0.91 | 0.31 / 2.07 |

The removal closes most of the class gap where both classes have data (+1..+3 °C: 0.78 / 1.23
against 0.64 / 1.57). The five long-idle intervals at -2..+1 °C still drew about three times
more air than the model before their defrost: there the idle was mostly near 0 °C and short
runs at 1 °C drew 10-18 kWh without a defrost, which no smooth rule in this data reproduces.

**The coil frost seen by the COP is a separate state.** The COP's coil-frost term (section 7.1,
d = 0.13) was fitted on 'share of the air drawn since the last defrost'. Refitting it on the new
trigger state fits worse (RMSE 0.122 against 0.119 kW, d 0.06), so the model keeps two states:
the defrost trigger (above, with the off-time removal) and the coil frost for the COP (the round-1
accumulation, reset only by a defrost, capped at 1).

- **Implied continuous run hours between defrosts** at 6 kW, 90 % RH: 1.7 h at -10 °C, 1.6 at
  -2, 1.9 at 0, 2.7 at +2, 5.0 at +5 °C (round 1: 1.3 / 1.8 / 2.3 / 3.7 / 15.8). On/off
  operation now defrosts less often than continuous running at the same air heat.
- **Open-loop check** (section 11): the unit model replaying period A defrosts 156 times against
  119. On the recorded running pattern the same frost model gives 127: the rest comes from the
  unit model's runs being longer than the real ones (fewer stops, so less removal; section 11).
  `frost_no_melt` gives 126 in the open-loop replay. Treat absolute defrost counts as about
  +20-30 % high in closed loop; rank on the variants.
- **Quiet mode** does not multiply frost by 1.5. Its lower output changes the air heat and so
  the frost by itself; the old factor is the variant `quiet_frost`.
- **Other flows:** K scales with the assumed flow, so `low_flow` / `high_flow` keep the measured
  count.
- **Each event:** 5 min below +3 °C, 2 min above. It draws about 0.85-0.92 kWh from the loop
  (median draw 4.9-5.2 K of delta-T, so 5.2 K in the model) and uses 0.12-0.14 kWh of electricity
  (0.06 above +3 °C). The outlet falls 9-11 K.
- **The window has cold, humid weather:** 205 run hours below 0 °C at RH about 89 %. Defrost is
  therefore measured, not assumed. Below -10 °C there are only 23 events.
- **Penalty on top of steady COP** (central, 6 kW, W31, half-frosted coil): 16 % at -10 °C, 13 % at
  -3, 10 % at 0, 6 % at +2, under 1 % above +4 °C. The coil-frost COP term (section 7.1) comes on
  top between defrosts.

## 9. Hot water

109 DHW compressor runs:

- **Duration:** 19-24 min (IQR), median 22, 10th-90th percentile 10-29.
- **Electricity:** 1.23 kWh per run (median; 10th-90th percentile 0.24-1.58), about 1.46 - 0.038
  kWh per K of outdoor temperature.
- **Power** ramps from 1.4 kW to 4.8-4.9 kW over 15-18 min. The model: 1.5 kW + 0.26 kW/min,
  capped at 4.9 kW, +1.2 % per K below +7 °C.
- **Temperatures:** the tank goes from 37 to 46 °C (median); the heat pump limit is 45 °C. The
  unmetered tank heater then lifts it to about 52 °C.
- **Frequency:** about 0.9 runs a day. Starts cluster at 07-09 local time with a second group in
  the afternoon.
- Legionella runs (target 67-75 °C) happen about every 2 weeks.
- **In simulation, DHW is exogenous:** replay the recorded demand intervals or sample these
  statistics. The unit model handles the pauses, the stopped heating and the tank heater.

## 10. Implementation (`lab/sim/unit.py`)

- `VersatiUnit(params).step(setpoint, restart_delta, t_return, t_amb, rh, flow_lpm, quiet,
  heating_enabled, dhw_demand)` returns `StepResult`:
  - temperatures: `t_supply`, `t_outlet`, `t_ctrl`;
  - flows and power: `q_loop`, `loop_flow_lpm`, `p_outdoor`, `p_total`, `p_tank_heater`;
  - state: `status` (heat / dhw / defrost / idle / off), `compressor`, `started`.
- **State:**
  - mode (idle / prestart / heat / pre_dhw / dhw / post_dhw);
  - run and off timers, stop-hold counter, capacity;
  - frost and defrost timers, surge accumulator, DHW pauses, tank-heater timer.
- **Inputs are clamped:**
  - setpoint to 20-55 °C in whole degrees;
  - restart_delta to 2-10 K (ASSUMED to act like 4/5).
- **Speed:** about 1.6 µs per step on this machine. A 180-day run takes 0.4 s.
- `UnitParams` holds every number above, with an uncertainty dict (`ranges`).
- **Steady helpers** for controllers and analysis: `q_min`, `q_max`, `cop_core`, `p_running`,
  `cop_steady`, `q_p95`, `eta_smooth`, `p_idle`, `frost_per_min`, `frost_rate_per_min`.
- **Variants:** `central`, `low_flow`, `high_flow`, `shallow_outlet`, `steep_outlet`, `flat_load`
  (COP almost flat with output), `legacy_cop` (the old 10-knot, rising-with-output COP),
  `legacy_frost` (frost per run-minute, quiet x1.5), `legacy_surge` (surge by outdoor
  temperature), `high_start_loss`, `sluggish` (slower ramps, 5-min minimum off, 4-min stop hold,
  7-min minimum run), `more_frost` (x1.4), `less_frost` (melts while idle), `quiet_frost` (quiet
  x1.5 frost), `pump_always_on` (space heating off keeps the loop circulating).
- **Assumptions with no data behind them**, flagged ASSUMED in the code:
  - quiet mode (capacity x 0.7);
  - space heating switched off: the pump stops (indoor unit 0.02 kW), and after it is switched on
    again the pump purges the loop for 3 minutes before a start can happen;
  - restart_delta other than 4 or 5 K;
  - the minimum off time;
  - frost melting while idle;
  - the tank-heater rating;
  - the condensing-approach level.
- **Not modelled:**
  - backup heaters (never on);
  - anti-freeze;
  - the unit's own weather curve (its registers are constant and unused while the setpoint is
    written directly);
  - Modbus link drops.
- **Self-check:** `.local/lab-venv/bin/python -m lab.sim.unit` asserts that:
  - COP falls with supply temperature and rises with outdoor temperature, for every variant;
  - there is no heat when the unit is off or idle;
  - the start and stop rules (pre-start, write-stop after the minimum run, no start below the gap)
    hold;
  - COP does not rise past its 95th-percentile output, its outdoor slope stays below 7 %/K and
    changes by less than 3.5 %/K between neighbouring kelvins;
  - frost per minute roughly doubles with output (it follows the air heat);
  - heat equals cp x flow x (supply - return);
  - COP stays sane;
  - a 180-day run takes under 30 s.

## 11. Validation (open loop)

`lab/sim/validate_unit.py` drives the unit model with the recorded inputs:

- setpoint, restart_delta and heating mode;
- ERA5 outdoor temperature and humidity;
- recorded hot-water demand;
- the recorded inlet temperature as return.

A simulated run that outlasts the real one would see the real return fall after the real stop. To
handle that, a fitted first-order loop response feeds the simulated-minus-recorded supply
difference back into the return:

- dT_ret/dt = 0.0266 (T_sup(t-3) - T_ret) + 0.0117 (T_room + 1 - T_ret);
- fitted on 127 000 heating minutes, R² 0.20 on 1-minute changes.

Only days with at least 97 % Versati and meter data count.

| period | good days | starts/day rec -> sim | ratio | daily start error (mean absolute) | electricity kWh/day rec -> sim | ratio | daily electricity error (mean absolute / p90) | median run min rec -> sim | defrosts rec -> sim | outlet bias / RMSE while both run |
|---|---|---|---|---|---|---|---|---|---|---|
| A (legacy, Feb-May) | 52 | 2.00 -> 1.96 | 0.98 | 0.31 | 13.51 -> 13.92 | 1.030 | 10.2 % / 19.8 % | 198 -> 238 | 119 -> 156 | +0.11 / 0.70 K |
| C1 (Oct, old bridge) | 14 | 3.79 -> 3.57 | 0.94 | 0.79 | 11.45 -> 11.71 | 1.022 | 8.8 % / 16.6 % | 119 -> 119 | 4 -> 6 | +0.10 / 0.72 K |
| C2 (Oct-Nov, new bridge) | 13 | 4.08 -> 3.38 | **0.83** | 0.69 | 12.21 -> 12.11 | 0.992 | 4.9 % / 10.6 % | 115 -> 123 | 5 -> 14 | +0.09 / 0.63 K |

(Review round 2 numbers. Round 1: starts 1.00 / 0.93 / 0.83, electricity 1.044 / 1.013 / 1.004,
defrosts 115 / 5 / 7.) The 75th percentile of run length is now 304 vs 265 min in A (329 in round 1,
363 before) and 190 vs 137 in C2 (205): the surge timer that restarts after a defrost shortens the
long cold-weather runs; mild-weather runs are still too long. The new frost model defrosts more
often in this replay than the unit did (A 156 vs 119), because the model's runs are longer and so
lose less of the trigger state to stops; on the recorded running pattern it gives 127 (section 8).
Variants on A (electricity ratio / defrosts): `frost_melt_lo` 1.028 / 149, `frost_melt_hi` 1.058 /
154, `frost_no_melt` 1.049 / 126, `partload_lo` 1.040, `partload_hi` 1.047.

Per-run electricity (runs of at least 15 min) is within 5-8 % at the median; mean absolute error is
9-17 %.

**What still differs, and why:**

1. **Too few starts in C2 (-19 %), and the simulated runs are too long** (75th percentile 207 vs
   137 min in C2, 363 vs 265 in A). Simulated stop causes in C2: 33 writes and 11 surges. Recorded:
   39 writes, 11 at 120-minute marks, 3 other.
   - Most misses are writes that cut the setpoint by exactly 2 K: the real t_ctrl sat at or above
     the new setpoint + 2.0 K, while the simulated one was 0.3-0.7 K lower (still ramping up).
   - The stop threshold is sharp (section 3.2), and the current controller writes right at it, so a
     few tenths of a kelvin decide the stop.
   - This is a weakness of open-loop replay. A controller that reacts to the simulated state will
     not aim its writes at the real unit's temperature.
   - It is still a warning: when a write lands within about 0.5 K of the stop threshold, the model
     cannot be trusted to call the outcome.
2. **Electricity in A is 4 % high**, mostly on cold days. The daily error is 10.4 % (mean
   absolute), because individual days with long runs and surges land differently. Totals over 52
   days are within 5 %.
3. **Start timing on slow drift** depends on the return temperature to 0.1 K. The inlet cools
   about 0.3 K/h, so a 0.1 K offset moves a start by about 20 minutes. `ctrl_offset_idle` = -0.80 K
   (mean idle offset -0.69) reproduces the median drift-start threshold.
4. **The variants match the electricity equally well** (within ±1-3 % of central). Validation
   cannot tell the flow rate or the outlet slope apart: they change heat per kWh, not electricity
   at a given setpoint history. Those ranges stay as robustness variants.

## 12. What would tighten the model

- **The nameplate:** model, refrigerant, tank volume. The tank volume would fix the flow through
  method (d).
- **Compressor set and actual frequency** (Words 142/143) and the pump state (coil 175), read-only.
  They would turn the capacity controller and the surges from inference into measurement.
- **A week of quiet mode, or another restart_delta (for example 3 or 6 K)**, at the owner's choice.
  Both are currently ASSUMED.
- **A clamp-on or ultrasonic flow reading**, even once.

## 13. Review fixes (round 1)

An adversarial review of the closed-loop lab found that several unit-model shortcuts could decide a
ranking. What changed (all recomputed by `python -m lab.sim.unit_analysis review`):

| finding | change | evidence |
|---|---|---|
| C1: COP rose steadily with output up to the maximum (fixed 0.37 kW overhead extrapolated), so high-output pulsing beat long low-power runs | smooth Carnot fraction + regularised output surface + COP held constant above the measured 95th percentile of output per outdoor band; `flat_load` refitted and made a mandatory ranking variant; the old model is `legacy_cop` | residual within ±3 % in every well-populated outdoor x output bin (was up to -10 %/+19 %), section 7.1 |
| C4: COP against outdoor temperature was a staircase (eta knots, +10 %/K at 0..+2 and +4..+6 °C, +1 %/K between) | monotone 5-parameter eta; coil degradation between defrosts is an explicit frost term (-13 % at full frost) | slope 1-6 %/K, smooth (max 1.9 %/K change between kelvins) |
| C2: frost per run-minute regardless of output, so high-output short runs got half the defrosts | frost per kWh of air heat x (Q / 5 kW)^0.28, table refitted from 193 defrosts; quiet mode's x1.5 dropped (`quiet_frost` keeps it) | period A 115 vs 119 defrosts; run hours between defrosts now fall with output as in the 158 intervals |
| M7: the 120-minute surge depended on outdoor temperature only | logistic in the mean power of the 30 minutes before the mark; `legacy_surge` keeps the table | outdoor temperature adds nothing once power is in the fit |
| m1: a setpoint flapped every minute never started the compressor but billed pre-start power | a begun pre-start finishes unless the gap stays closed for 2 minutes | the self-check flapper starts and heats |
| M4: heating_enabled off kept the loop circulating | pump stops (0.02 kW indoor unit), loop water stagnant, 3-minute purge on re-enable (all ASSUMED; `pump_always_on` keeps the old behaviour) | 2 mode changes in the record only; runs that switch it are flagged `heating_off` |
| M1: start cost unvalidated beyond a few starts a day | start energy measured against the preceding off time (0.01-0.04 kWh, no trend); runs that wait for the ASSUMED minimum off time are counted | section 7.4 |

## 14. Review fixes (round 2)

A second adversarial review found that the frost model, the part-load variant set and a few
firmware details could still decide a ranking. What changed (`python -m lab.sim.unit_analysis
review2` recomputes the frost and part-load fits; `frost_counts` the K levels alone):

| finding | change | evidence |
|---|---|---|
| N1: frost kept while idle, so continuous runners got too few defrosts and on/off strategies too many | the defrost-trigger state loses up to rmax = 0.4 of itself over each compressor-off block (time constant 15 min); no defrost within 50 compressor minutes of the last; K refitted per minute temperature from all 186 inter-defrost segments: rmax from the timing (first passage), K from the counts by outdoor band and on/off class; no humidity gain; the COP's coil-frost term keeps its own (round-1) state | 'kept while off' 8.6 units of squared log error worse (90 % threshold 0.92); counts by band x class reproduced (deviance 5.2 on 16 cells); class gap at +1..+3 °C 0.78 / 1.23 (was 0.64 / 1.57) (section 8) |
| N1: `less_frost` was an unfitted melt, not a coherent alternative | `frost_melt_lo` / `frost_melt_hi` (rmax 0.2 / 0.6, K refitted) are mandatory ranking variants; `frost_no_melt` (rmax 0, K refitted) and `legacy_frost_r1` (the exact round-1 model) are diagnostics; `less_frost` is now frost x 0.7 | section 8 |
| N3: `flat_load` is rejected by the data, so output-level strategies could not be decided | mandatory `partload_lo` / `partload_hi`: the output dependence of the COP surface x0.5 / x1.5 with eta, p0 and d refitted; `flat_load` diagnostic only; a two-hold field test proposed | RMSE 0.125 / 0.121 vs 0.119 central (flat 0.166); COP(6 kW) / COP(minimum) 1.18 / 1.25 / 1.34 at 0 °C (section 7.2) |
| N6: runs too long, a stop mechanism missing | the 120-minute surge timer restarts after a defrost; t_ctrl - outlet depends on output (-0.025 K/kW); all clean recorded stops classified: 5 of 231 natural stops have no surge, defrost, write or hot water behind them, so no further rule or hazard was added | 125 surges in runs with a defrost: 49 % near 120-min multiples of the defrost end vs 24 % of the start; A run p75 304 vs 265 min (was 329) (section 3.3) |
| N4 (unit side) | the measured start energy (0.02-0.04 kWh, section 7.4) is unchanged; the ranking no longer folds an assumed start cost into the energy (SIMULATOR.md section 10) | |

Open-loop electricity is now +3.0 / +2.2 / -0.8 % in A / C1 / C2 (round 1 +4.4 / +1.3 / +0.4 %);
starts 0.98 / 0.94 / 0.83; defrosts 156 / 6 / 14 against 119 / 4 / 5 (section 11).
