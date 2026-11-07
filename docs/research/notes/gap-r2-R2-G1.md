# Gap R2-G1: Does the Versati III/IV internal circulation pump keep running while the compressor is off in space-heating mode? If so, at what speed and wattage (pump model, PWM curve, minimum speed), and can it be set to intermittent or sampling mode?

> Method note. The shared web-search budget for this workflow was used up before this gap began. All three searches I tried returned nothing, so no new forum or non-English material could be found. This note is therefore built from:
> - full-text reading of eleven Gree documents (service manuals for Versati II, III and IV and the R290 generation, panel manuals, the Modbus map and the EU catalogue), cached locally and searched for every "pump" sentence;
> - direct fetches of the Home Assistant Versati threads and of the EU Ecodesign regulation;
> - Daikin and Panasonic manuals, for comparison;
> - my own analysis of the heatpumpmonitor.org daily data (499 systems).
>
> I found no measured Versati pump trace, so the core answer still rests on manufacturer text plus inference.

## Summary

- **Gree's own control text says the pump stops when the unit stops on temperature. It does not say the pump keeps circulating.** The Versati III and IV service manuals (monobloc, split, all-in-one and compact, all with identical wording) describe heating like this: the compressor ramps down, and once it is at minimum frequency and the outlet is still above setpoint, "the unit will shut down". Under "normal shutdown", the pump "stops after the compressor has stopped" [1][2][3][4][5]. No Versati document describes continuous circulation in compressor-off heating. Confidence that the firmware *intends* the pump to stop: medium-high. Measured confirmation: none.
- **The "pump runs in standby" reading in notes 08 and 15 was a misreading.** That sentence belongs only to the "Other thermal" (backup boiler) logic. While the *other* heat source heats, the heat pump's pump is stopped. In that mode's standby state the heat pump's pump starts and the boiler stops [1][4][9][10]. It says nothing about normal heat-pump heating.
- **The "120 s pump stop after compressor" rule is also out of context.** It appears only in the fault rule for the high-, low- or intermediate-pressure sensors: all loads stop, and the pump stops 120 s after the compressor [1][2][3][4][5][6]. The normal shutdown sequence gives no delay figure, only "after". The 120 s rule does not conflict with continuous running because neither describes normal heating.
- **Indirect firmware evidence also points to "pump off in standby".**
  - The Versati II/T1 anti-freeze rule only means something if the pump is normally off: when the compressor stops, the pump starts if water is below 3 °C, and the compressor starts 30 s later [7].
  - The Versati II manual tells installers to enable the plate-heat-exchanger heater "when the water pump has stopped" and outdoor is below 2 °C [6].
- **The pump is a variable-speed (PWM-driven) wet-rotor circulator, not a 75-85 W constant load.**
  - The "75 W / 85 W" in the catalogue is the pump's rated maximum input (4-10 kW units: 75 W; larger: 85 W). The catalogue lists "10" speed steps and a "limit LPM 12" [8].
  - The Versati II hydro box's pump is listed as type "RS25/7.5", 800-4770 rpm, **4-75 W** input [8]. The minimum electrical draw of this class of pump is single-digit watts.
  - The board has a "built-in water pump signal (PWM)" connector (CN18/CN30) [11]. One owner asked whether two Modbus words are "the iPWM signals of the inside pump" (unanswered) [13].
- **The speed rule is ΔT-based**: start at an "initialized speed", then run faster when the entering/leaving difference is large and slower when it is small [1][3][4][5]. The target ΔT, the initial speed and the minimum duty are not documented anywhere. If the pump did run with the compressor off (ΔT ≈ 0), this rule would drive it toward minimum speed, not 75 W.
- **The pump model is not identified for Versati III/IV.** The spare part is the same code, 812007000002, across Versati III monobloc and all-in-one [1][2][4]. The G2 sub-series "use a bigger water pump" [1]. "RS25/7.5" (Versati II) matches Wilo-style naming. Whether Versati III uses a Wilo Para, a Grundfos UPM3 or a Chinese equivalent is unverified.
- **No pump-mode setting exists in any Versati panel generation I could read**: Versati II, Versati III (normal and compact), the CopMax rebadge, the 2025 panel and the R290 Versati. There is no continuous, sampling or interval option [6][9][10][12]. The only pump-related functions are:
  - "Air removal": pump only, unit off;
  - pump status (HP-pump On/Off) in the View menu;
  - from the R290 generation onward, a "water flow feedback" read-out [12].
- **Compare with other makers.** Daikin offers Continuous, Sample (pump every 5 min during thermo-off) and Request [15]. Panasonic lets the installer pick one of 7 pump speeds [16]. Gree exposes neither choice.
- **Field data: idle draw is about 20 W, even where pumps can run.** On 4-14 °C heating days with at least 4 h compressor-off (my analysis of heatpumpmonitor.org, 499 systems), the non-running electricity was:
  - median 21 W, p90 45 W;
  - by model: Arotherm+ 23 W (n = 232), Daikin Altherma 3 15 W (n = 71), Ecodan 20 W (n = 31), Samsung Gen 6 10 W (n = 10), Vitocal 150-A 54 W (n = 28) [19].
  - No Gree Versati is in the dataset. The data show that a steady 75-85 W idle load would sit far above the 90th percentile of modern installed units.
- **Gree's own EN 14825 declaration is consistent with a stopped pump.** Thermostat-off power P_TO = standby P_SB = off-mode P_off = 25 W on the Versati AIO and split (Keymark, via note gap-r1-G1 [20]).
  - The EU definition of thermostat-off mode (heating function active, no load) does not mention pumps [18], so this is suggestive only.
  - A pump idling inside the declared 25 W would have to draw under about 10-15 W.
- **Revised cost estimate for this house** (my arithmetic, mild day, duty 0.25, about 18 h off, about 4.5 kWh/day electricity):

  | Pump state during off-time | Extra electricity | Share of the day's electricity |
  |---|---|---|
  | Off (the documented behaviour) | 0 | 0 % |
  | Idling at minimum PWM, about 4-10 W | 0.07-0.18 kWh | 2-4 % |
  | Held at a flow-switch-safe speed, about 15-25 W | 0.27-0.45 kWh | 6-10 % |
  | Full speed, 75 W (very unlikely) | 1.35 kWh | 30 % |

  The 20-30 % figure in notes 08, 15 and gap-r1-G4 assumed the worst row.
- **If the pump stops, standby return temperature is not a slab sensor.** The outlet and return sensors then read stagnant water in the indoor unit. That water cools toward plant-room temperature (all-in-one or split) or outdoor temperature (monobloc).
  - On this unit the restart rule (setpoint − outlet ≥ Word 30 = 4 K) is then partly timed by how fast the indoor unit cools, not by the slab. This is directly testable from existing Modbus logs (see below).

## Detailed findings

### 1. What the Versati III/IV firmware text says about the pump

**Normal heating stop.** The text is identical in the Versati III monobloc (139 pp), Versati III compact monobloc, Versati III split, Versati III all-in-one and Versati IV monobloc manuals [1][2][3][4][5]:

- §2.2.1, heating: compressor frequency follows (actual leaving water − setpoint). "When the compressor reaches the minimum frequency but the temperature [difference] is still quite large, the unit will shut down."
- §2.4, shutdown, has three kinds: normal, error and protection.
  - Normal shutdown sequence: the compressor ramps to minimum, then stops; the EXV opens fully; the fan stops after the compressor; **"the water pump of the main unit stops after the compressor has stopped"**; the EXV goes to its fixed opening.
  - No overrun time is given for a normal stop.
- §2.8, pump control: initial speed, then speed rises with a large entering/leaving ΔT and falls with a small one. The manual says "fan" in this paragraph, an evident copy-paste slip.
- Panel parameter "Heat run time", 1-10 min (default 3 min, or 5 min with the 2-way valve on). Once the timer has expired "and temperature difference keeps at the standby zone, the unit will stop" [1][4].
  - So the "standby zone" timer ends in a unit stop, which per §2.4 includes the pump.
  - Note 08's reading of this parameter as a minimum on-time or stop delay is unchanged.

**Where the pump is explicitly kept running**, the manuals say so case by case. That makes the silence about normal compressor-off heating meaningful:

- Freeze protection in cooling: the compressor stops, but "the water pump keeps normal operation" [1][4][5].
- Over-temperature protection of the backup heater (heating and DHW): all loads stop *except* the main-unit pump and the 4-way valve [1][4][5].
- Pressure-sensor faults: all loads stop, and the pump stops 120 s after the compressor [1][2][3][4][5][6]. **This is the only place "120 s" appears.**
- Flow-switch protection: all loads stop except the solar pump and tank heater. The lock-out is unrecoverable until power-cycled [1][4][6].

**"Other thermal" (backup boiler) logic.** This is the source of the earlier "pump runs in standby" claim [1][4][9][10]:

- Logics 1 and 2, Heat mode: "the water pump for other thermal must be always active".
- During heating operation [by the other thermal], the heat pump's pump is stopped. "During standby status, the water pump will start but the other thermal will stop."
- In "Hot water" mode, the heat pump's pump "will always stop" while the other thermal runs.
- This describes a hybrid layout with an external heat source and its own pump. It is not evidence about normal heat-pump heating. Notes 08 [4][10] and 15 [33] generalised it.

**Versati IV split manual** [5b]: control-logic text is not present in the extractable layer. Its parts list shows one "Water Pump" and a flow switch. The fault tree for "EC" (flow-switch protection) asks "Does the water pump run properly?" and ends in "Replace the water pump."

**R290 Versati (NpG4, "Versati V")** [12]: the View menu lists HP-pump, tank pump, backup pump, zone pump and reserved pump states, plus a new "Water pump water flow feedback". Still no pump-mode parameter.

### 2. Evidence from older Gree firmware (Versati II and T1)

- **Anti-freeze** (T1/R410A, Versati II era) [7]: "When the compressor stops (including normal or abnormal stop of the unit), if [water] is lower than 3 °C, water pump will automatically operate and 30 s later the compressor operates." It then runs until outlet water exceeds 20 °C.
  - This rule presumes the pump is off whenever the compressor is off.
- **Plate heater** (Versati II 2016) [6]: activating it is suggested "when the water pump has stopped and the environment temperature is lower than 2 °C". Again this presumes off-periods with the pump stopped.
- **T1 pump** [7]: a three-speed AC pump (maximum, medium, minimum). The manual recommends maximum and warns that "Min" can trip the flow error "EC". This is the generation before inverter pumps, and it shows Gree's flow switch needs a substantial minimum flow.
- **Versati II pump protection** [6]: the pump has an overload input. Three trips in 60 minutes give an unrecoverable error.

### 3. Pump hardware, speed range and wattage

| Item | Value | Source |
|---|---|---|
| Versati II hydro box (GRS-CQ8-16Pd/NaE-K/M(I)) pump type | RS25/7.5 | [8] |
| Speed range | 800 / 4770 rpm | [8] |
| Power input | **4-75 W** | [8] |
| Versati III split/AIO (NhH) pump | "Inverter", 10 speed steps | [8] |
| Max input | 75 W (4-10 kW), 85 W (12-16 kW) | [8] |
| "limit LPM" | 12 (likely the minimum flow for the flow switch) | [8] |
| Versati III (G-series) pump | ErP "A-class high-efficiency inverter water pump"; G2 uses a bigger pump | [1] |
| Part code (Versati III monobloc and AIO) | 812007000002 | [1][2][4] |
| Drive signal | "Build-in water pump signal (PWM)" on CN18/CN30; backup pump PWM on CN19/CN31 | [11] |
| Installer note | "The water pump is of variable frequency… will adjust its output based on the actual load" | [1][11] |

- **What is not documented:** the pump brand and model for Versati III/IV, the PWM profile (heating profile with stop above about 90 % duty, or solar profile), the minimum duty Gree sends, the target ΔT and the "initialized speed".
- The Modbus map exposes only coil 175 "IDU Water Pump State" and coil 170 "Flow Switch State" (plus the error bits 108 and 188). There is no speed or power register [14].
- **Inference (low-medium confidence).**
  - Single-pipe ErP circulators of this size (25/7.5 class) draw roughly 3-5 W at minimum speed and 60-75 W at maximum.
  - Gree's own 4-75 W figure for the Versati II pump fits that.
  - At the 12 L/min flow-switch limit in a UFH circuit, a realistic floor is probably 10-25 W.
  - Pump power at the speeds actually used in heating (ΔT-controlled, 15-27 L/min for 3.7-9 kW at ΔT 5 K) is probably 20-50 W while the compressor runs. That counts as running electricity, not idle.

### 4. Settings: can it be made intermittent or sampling?

- **No.** None of the Versati II, III, IV or R290 panel manuals [6][9][10][12], nor the CopMax rebadge [10], lists a pump-mode, pump-speed or interval parameter.
- Commissioning parameters relevant to the pump are only:
  - Heat/Cool run time (1-10 min);
  - Air removal (pump only, settable only with the unit off);
  - Floor debug (screed drying).
- **Compare: Daikin Altherma** [15] has three modes:
  - 0 Continuous, regardless of thermo state, with an energy warning;
  - 1 Sample: pump on while the LWT is below target; in thermo-OFF it runs every 5 min to check water temperature;
  - 2 Request (default): pump follows the room-thermostat demand.
- **Compare: Panasonic Aquarea** [16]: pump speed is chosen from 7 software steps. In tank mode, "THERMO ON TEMP = water inlet during thermo OFF time − 3 °C", which implies the inlet is sampled during thermo-off.
- External control is the only lever on a Gree: cutting pump power, or overriding PWM on CN18. It risks the unrecoverable flow-switch lock-out [1][6] and warranty problems. It is pointless if the pump already stops.

### 5. Field data: what idle draw looks like when pumps can circulate

My own analysis [19] used the heatpumpmonitor.org daily statistics cached in this workflow. Filters:
- full days only (≥ 86,000 s), electricity quality ≥ 99 %;
- no immersion, no cooling;
- outdoor 4-14 °C;
- compressor-off time ≥ 4 h and duty ≥ 0.05;
- ≥ 10 such days per system.

Non-running W is (combined − running electricity) / off-hours. Results:

| Model | Systems | Median of system medians (W) | IQR (W) |
|---|---|---|---|
| All | 499 | 21 | — (p90 45) |
| Vaillant Arotherm+ | 232 | 23 | 18-31 |
| Daikin Altherma 3 | 71 | 15 | 13-20 |
| Mitsubishi Ecodan | 31 | 20 | 16-30 |
| Viessmann Vitocal 150-A | 28 | 54 | 38-75 |
| Samsung Gen 6 | 10 | 10 | 7-14 |
| Cosy | 8 | 1 | 1-8 |

- Systems that declare their meter includes central-heating pumps (n = 459): median 22 W. Systems that do not (n = 40): 12 W. The difference, about 10 W, is the size of a typical idling circulator plus controls.
- Even the worst model family (Vitocal 150-A, about 54 W) is below the 75-85 W assumed in notes 08 and 15 for the Versati.
- Caveats:
  - "Non-running" is set by heatpumpmonitor's power threshold, so it includes controls, crankcase heaters and any pump overrun.
  - No Versati is in the dataset.
  - Model-level pump behaviour (which units circulate in thermo-off) is not recorded, so this bounds the effect but does not identify Gree's behaviour.

### 6. Regulatory declaration as a cross-check

- Gree's Keymark data for the Versati AIO and split declare P_off = P_TO = P_SB = 25 W, with Cdh exactly 1 − P_off/P_el (note gap-r1-G1 [20]).
- EU 813/2013 defines thermostat-off mode as "no heating load and activated heating function" and says nothing about pumps [18].
- Under EN 14825 practice, a pump that runs during thermostat-off is normally included in P_TO. Several makers whose pumps idle declare P_TO well above P_SB. I could not re-verify the standard's text in this pass.
- Gree's identical 25 W for both states fits a pump that stops in thermostat-off, or one idling at a few watts. Weak evidence, since the values may be declared rather than measured.

### 7. Consequences for sensing

- **Pump stopped while the compressor is off (documented behaviour):**
  - The leaving-water and return sensors sit in still water inside the indoor unit (all-in-one) or monobloc.
  - Their readings decay from the last flow temperature toward the surrounding air: plant room (about 15-22 °C) for an AIO or split, outdoor for a monobloc.
  - They say nothing reliable about slab temperature after the first few minutes.
  - The Gree restart test (setpoint − outlet ≥ ΔT-heat, Word 30) then fires when the *indoor unit's water* has cooled enough. This is a cabinet-cooling clock, not a slab-demand signal.
- **Pump running during off-time:** outlet ≈ return ≈ mixed UFH water within one loop transit (roughly 5-10 min for 100-150 L at 15-25 L/min). Return would then track slab water temperature, which is what notes 08 and 15 assumed.

## What this means for controlling this house

1. **Stop budgeting 75-85 W of idle pump load.** Use a prior of "pump off when compressor off". The off-time electricity budget should be the declared about 25 W (controls) plus a crankcase heater in cold weather (0-25 W, note gap-r1-G4). Treat a residual 0-25 W pump term as uncertain until measured.
   - Confidence: medium-high that the pump is not at 75 W in standby; medium that it is fully off.
   - Consequence: idle time is cheap, about 0.5 W per kW of rated capacity per hour. The case for merging runs into fewer, longer blocks rests on start costs and COP at minimum frequency, not on pump parasitics.
2. **Verify with a 1-day log before changing anything.** Log at 10-30 s resolution:
   - coil 80 (compressor), coil 175 (pump state), coil 170 (flow switch);
   - leaving and return water temperatures;
   - the house meter or a smart plug on the unit's supply, if separable.

   Decision rule:
   - **(a)** Coil 175 = 0 within 0-3 min of coil 80 = 0, and whole-unit draw falls to about 20-30 W: pump stops. Note the overrun time; Gree gives none [1].
   - **(b)** Coil 175 stays 1 for the whole off-period: pump circulates. Its draw is (off-period W − about 25 W). If above 15 W, the 6-10 % tier in the Summary applies, and block structure should weigh longer, rarer runs.
   - **(c)** Intermittent 175 pulses (for example every 5-30 min): undocumented sampling. Measure pulse length and period.
3. **One-off pump wattage test, about 5 minutes, panel only.**
   - With the unit switched off on the panel, enable "Air removal" (pump only) [1][6]. Read whole-unit power with it on and off.
   - This gives pump draw at the air-removal speed, probably high or maximum. That is an upper bound, not the idle speed.
4. **Do not use standby return or outlet temperature as a slab sensor unless case (b) is confirmed.**
   - In case (a), estimate slab state from a model (the 6.6 kWh/K storage and 0.14-0.20 kW/K loss) or from a room or floor probe.
   - Alternatively, use the outlet value in the first 2-5 min after a run starts, once the loop has turned over. Compare the first stable return temperature after start-up with the model's slab estimate.
5. **Expect the restart trigger to be cabinet cooling, not slab cooling, in case (a).**
   - Check in the logs: plot outlet temperature during off-periods. An exponential decay toward plant-room temperature with a time constant unrelated to outdoor temperature means the Word 30 = 4 restart is a timer set by cabinet heat loss.
   - If so, the controller should decide restarts itself, by raising the setpoint deliberately when the model says the slab needs heat. The firmware's own restart should be kept from firing early, by holding the setpoint below (stagnant outlet + 4 K) during planned off-periods.
   - This also explains why setpoints have to sit 4-5 K above a *stagnant*, not slab, temperature.
6. **Do not try to make the pump intermittent or continuous from outside the unit.** There is no setting [6][9][10][12]. Cutting supply or overriding the PWM risks the unrecoverable flow-switch fault [1][6] and gains little if the pump already stops.
7. **If the UFH manifold has its own pump or mixing group** (an open question in note 15): that pump, not the Gree internal pump, is the likely parasitic that runs 24 h. A typical 25/6 ErP circulator draws 5-45 W. Check the manifold, and if present, put it on its lowest constant-speed setting or under control.
8. **Pump speed in running mode is out of reach.** It is ΔT-controlled with an undocumented target [1]. Don't plan around it. Log return − outlet ΔT during steady runs as a flow-health metric. Implied flow = Q / (4.18 × ΔT); about 12 L/min is the floor [8].

## Contradictions and open questions

- **Earlier notes against the manual text.**
  - Notes 08 (item 12) and 15 (Summary 9, §5) say the manuals imply continuous standby running and a 120 s stop rule.
  - Re-reading the full text: the "standby" pump sentence is in the Other-thermal (boiler) logic only. The 120 s rule is in the pressure-sensor-fault rule only. The normal shutdown says the pump stops after the compressor [1][3][4][5].
  - I could not find a Gree sentence supporting continuous circulation in normal heating. Both readings are manufacturer text, but mine is the literal one.
- **Text against behaviour.** Gree manuals are machine-translated and generic across generations. Firmware may still circulate periodically, for example a hidden anti-stagnation or sampling routine, without saying so. Only the coil 175 log settles this.
- **Overrun length.** "After the compressor has stopped" might mean seconds or minutes. Many units overrun 1-3 min to clear heat from the plate exchanger. Unknown for Gree.
- **Pump identity and PWM profile.** RS25/7.5 (800-4770 rpm, 4-75 W) is documented only for the Versati II hydro box [8]. Versati III/IV share one part code [1][4] but the model is unnamed. One HA user's "iPWM" remark [13] hints at a Wilo-type interface; unverified. Minimum commanded duty and the resulting minimum flow are unknown.
- **"limit LPM 12".** I read it as the flow-switch minimum, from a garbled catalogue table [8]. Unconfirmed.
- **EN 14825 P_TO.** Whether Gree's declared 25 W P_TO was measured with the pump idle or stopped is unknown. I could not re-check the standard's treatment of integrated pumps in thermostat-off in this pass.
- **Which variant the owner has.** This matters for how fast stagnant water cools: monobloc outdoors versus AIO or split indoors. Note 08 infers a Versati III all-in-one, unconfirmed.
- **Searches not run.** Because the shared search budget was exhausted, none of these were checked:
  - Polish, German, Lithuanian or Swedish owner reports (elektroda.pl, forum.muratordom.pl, photovoltaikforum, haustechnikdialog);
  - OpenEnergyMonitor threads on Gree pump behaviour;
  - Wilo or Grundfos PWM datasheets.

  A follow-up with search budget should target "Gree Versati pompa obiegowa po wyłączeniu sprężarki", "Versati Umwälzpumpe läuft dauernd" and "Versati pump 812007000002".

## Sources

1. VERSATI III Air To Water Heat Pump service manual (monobloc NhG/NhG1/NhG2, 139 pp) - Gree (hosted by Gree Hungary) - c. 2021 - https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iii/versati%20iii%20monoblokk%20–%20service%20manual.pdf - manufacturer - §2.2 heating stop rule, §2.4 normal shutdown (pump stops after compressor), §2.8 ΔT-based pump speed, 120 s only in the pressure-sensor fault rule, Other-thermal pump logic, Heat run time "standby zone" remark, G2 "bigger water pump", part 812007000002, Air removal.
2. VERSATI III Compact Mono-Block R32 service manual - Gree (hosted by Klimakoncept) - c. 2020 - https://www.klimakoncept.hr/upload/2-pdf-klimakoncept/4-dizalice-topline/6-gree-versati/Service-Manual-Versati-III-Compact-Mono-BlockR32-klimakoncept.pdf - manufacturer - Same shutdown, pump and 120 s fault wording; same part code; confirms the text is shared across Versati III variants.
3. VERSATI III Split Type service manual - Gree (hosted by Gree Hungary) - c. 2021 - https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iii/versati%20iii%20split%20%E2%80%93%20service%20manual.pdf - manufacturer (read from a copy cached earlier in this workflow) - Identical §2.4 and §2.8 text; control flowchart lists "Water Pump Control" per mode.
4. VERSATI III All-in-one service manual - Gree (hosted by Gree Hungary) - c. 2021 - https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iii/versati%20iii%20all%20in%20one%20%E2%80%93%20service%20manual.pdf - manufacturer - Identical pump and shutdown text for the most likely variant in this house; freeze and over-temperature exceptions where the pump keeps running.
5. VERSATI IV Monobloc service manual - Gree (hosted by Gree Hungary) - c. 2023 - https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iv/versati%20iv%20monoblokk%20%E2%80%93%20service%20manual.pdf - manufacturer - Versati IV keeps the same §2.2, §2.4 and §2.8 wording, including the 120 s fault rule; the pump logic is unchanged across generations.
   5b. VERSATI IV Split (NhH3) service manual - Gree - c. 2023 - https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iv/ (directory; exact file not recorded) - manufacturer - Parts list (one pump, flow switch); EC fault tree; Other-thermal text; no extractable pump-control text.
6. Air-to-water Heat Pump Split Versati (Versati II, NaE) service manual - Gree Commercial AC R&D Dept I - March 2016 - https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-ii-e-szeria/service%20manual%20gree%20en%20versati%20ii%20nae.pdf - manufacturer - Plate heater advice "when the water pump has stopped"; pump overload protection (3 trips in 60 min); Air removal only with the unit off; same 120 s fault rule.
7. Air-to-Water Heat Pump Service Manual (T1/R410A/50Hz) - Gree - c. 2013 - https://gree-bulgaria.com/manuals/archive/140_VERSATI_II_TSM_%202013_8.pdf - manufacturer (cached copy; URL as recorded in note gap-r1-G4) - Anti-freeze: pump starts when the compressor has stopped and water < 3 °C, compressor 30 s later; three-speed pump, "Min" may trip EC.
8. Air to Water Heat Pump EU catalogue GC-2101-06 - Gree - 2021 - https://germany-gree.de/wp-content/uploads/2021/06/GREE_Air_to_water.pdf - manufacturer - Versati II hydro pump RS25/7.5, 800/4770 rpm, 4-75 W; Versati III NhH pump inverter, 10 steps, 75/85 W, "limit LPM 12".
9. Control Panel for the Versati Air-to-water Heat Pump, owner's manuals (standard and Compact Type Versati III) - Gree - c. 2020-2023 - https://cooperhunter.pl/storage/files/2022/01/9ngzKL6RLfDgPbn70V15urY6f/instrukcja-obslugi-sterownika-r32-en.pdf (OEM copy; Gree editions read from cached copies) - manufacturer - Other-thermal pump text; HP-pump status view; no pump-mode parameter.
10. Control Panel for the Versati Air-to-water Heat Pump (CopMax High Power) and the 2025 panel manual - Gree / NH Bioservice - 2024-2025 - https://www.nhbioservice.dk/wp-content/uploads/2024/09/Panel-manual-CopMax-High-Power-engelsk.pdf - manufacturer - Same Other-thermal text; HP-pump and tank-pump status only; no pump interval or speed setting in the newest panel firmware.
11. Versati III Split Type (GRS-CQ…Pd/NhH-E) installation and owner's manual - Gree - c. 2021 - URL not recorded (cached copy from an earlier fetch in this workflow) - manufacturer - "Build-in water pump signal (PWM)" on CN18/CN30, backup pump PWM CN19/CN31; variable-frequency pump note.
12. Versati Air-to-water Monobloc Heat Pump GRS-CQ…Pd/NpG4 (R290) owner's manual - Gree - c. 2025 - URL not recorded (cached copy) - manufacturer - View menu: HP-pump, tank, backup, zone and reserved pump states, new "water pump water flow feedback"; no pump-mode setting.
13. "Gree Versati III Air to water heat pump" thread, pages 1-7 - Home Assistant Community - 2022-2026 - https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916 (and ?page=2…7) - forum - No owner reports pump behaviour in compressor-off heating; coil 175 is listed without observations; one user asks whether Words 142/143 are the inside pump's "iPWM" signals (unanswered); flow-switch trips when TRV heads close.
14. Modbus Protocol (V1.5) for the Versati Heat Pump Water Heater - Gree - c. 2020 - URL as in note 08 [1] (cached copy) - manufacturer - Coil 175 "IDU Water Pump State", coil 170 "Flow Switch State", bits 108 and 188 flow errors; no pump speed or power register.
15. Daikin Altherma Low temperature split, installer reference guide (ERLQ011-016CA / EH…) - Daikin - c. 2016 - URL as in note 15 [27] (cached copy) - manufacturer - Pump operation modes: Continuous (most energy), Sample (pump every 5 min in thermo-OFF), Request (default).
16. Panasonic Aquarea WH-SXC09/12F, WH-UX09/12FE8 service manual (PAPAMY1311028CE) - Panasonic - 2013 - URL not recorded (cached copy) - manufacturer - 7 software-selectable pump speeds; thermo-ON threshold uses water inlet "during thermo OFF time".
17. "Gree Versati 3 integration" and "ESPHome Modbus integration to Gree thermo pump" threads; koelec/EspHome-Gree repository - Home Assistant Community / GitHub - 2021-2026 - https://community.home-assistant.io/t/gree-versati-3-integration/991745 ; https://community.home-assistant.io/t/esphome-modbus-integration-to-gree-thermo-pump/358997 ; https://github.com/koelec/EspHome-Gree - forum / GitHub - Checked for pump-state observations; none found.
18. Commission Regulation (EU) No 813/2013 (Ecodesign, space and combination heaters) - European Commission - 2013 - https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32013R0813 - regulation - Definitions of thermostat-off, standby, off and crankcase-heater modes; pumps are not mentioned in the thermostat-off definition.
19. heatpumpmonitor.org per-system daily statistics, own analysis - OpenEnergyMonitor community data (cached in this workflow) - retrieved 2026-11 - https://heatpumpmonitor.org - field data (499 systems) - Non-running W on 4-14 °C heating days by model (median 21 W, p90 45 W; Vitocal 150-A 54 W; Altherma 3 15 W; Arotherm+ 23 W); pump-in-meter flag 22 W vs 12 W. Script(analysis script, not committed)
20. Sibling notes in this repository: 08-gree-versati.md, 15-hydraulics-pumps-deltaT.md, gap-r1-G4.md, gap-r1-G1.md (HP Keymark: Versati P_off = P_TO = P_SB = 25 W) - internal - Context and the claims re-examined here; Keymark values not re-fetched.
