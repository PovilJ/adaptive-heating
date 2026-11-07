# Gap G8: How does the Komfovent heat-recovery ventilation change the house's effective heat loss and gains: the bypass in mild or sunny weather, frost protection (electric preheater power, imbalance mode), and the supply air temperature? Should the ventilation be scheduled or modelled as a disturbance?

Follow-up note for gap G8 of the heat pump efficiency sweep. Other notes touch ventilation only briefly: note 14 §7 gives the MVHR formula and the ±30 % HTC effect, and note 05 says ventilation "cannot dump much" solar heat.

**Method note (read first).** This is the second pass on G8.
- **First pass.** It had no web search, so it relied on Komfovent's own downloads, standards and a few forum threads. Its sources are [1]-[21].
- **This pass.** Web search was available:
  - 21 searches, in English, German, Polish, Swedish, Finnish and Lithuanian.
  - 11 further sources read in full: an independent Passive House Institute lab certificate for a Komfovent rotary unit, Danish smart-ventilation field data, a Norwegian field study of rotary units, an owner's measured Komfovent heater energy, Home Assistant Modbus write-ups, a Swegon frost note, an NTNU study and forum threads.
  - A few more sources were reached only as abstracts or search snippets. These are marked "(abstract only)".
- **What changed.** This pass **corrects one first-pass recommendation**. The first pass said to lower the AHU supply setpoint to 16-17 °C. On a rotary unit that throttles the wheel for most of the winter and throws away recovered heat (see §2 and §8).
- **Unit model still unknown.** The exact Komfovent model in the house is not known: it could be a Domekt R (rotary) or a Domekt CF (counter-flow plate). Both are covered. The first practical step is to read Modbus register 955 (heat exchanger type).
- **Register numbering.** Register numbers below follow Komfovent's document, which counts from 1. Home Assistant's Modbus integration counts from 0, so subtract 1 when configuring it [25][26].

`[calc]` marks my own arithmetic from sourced numbers. In the calculations, air heat capacity is taken as 0.335 Wh/(m³·K), so 200 m³/h ≈ 67 W/K before any heat recovery.

## Summary

1. **The ventilation term is a large and switchable share of H.**
   - At an assumed 200 m³/h, raw ventilation conductance is about 67 W/K [calc].
   - With about 80 % recovery the residual is about 13 W/K, which is 7-10 % of the measured H of 0.14-0.20 kW/K [calc].
   - With the rotor stopped or slowed, or the bypass open, up to the full 67 W/K appears: an increase of **up to +30 to +45 % in H** [calc].
   - The Annex 71 twin houses saw an HTC shift of about 30 % from modelling ventilation explicitly [11].
2. **The biggest hidden inefficiency is probably the AHU's own electric heater, not frost protection.**
   - Every Domekt has an integrated electric heater, assigned as heating Stage 1 [1]. It switches on whenever the heat exchanger alone cannot reach the supply setpoint, which is 20 °C by default in every mode [1].
   - A Domekt R 450 V owner measured **3.3-4 kWh/day of heater energy (about 140 W average) at +1 to +10 °C outdoors** with supply set to match extract [24].
   - For this house at about +2 °C that is roughly 4 % of the heat but **about 14 % of the heating electricity**, because it runs at COP 1 instead of about 3.5 [calc].
3. **Do not fix this by lowering the supply setpoint on a rotary unit. Switch the heater off instead (this corrects the first pass).**
   - In supply-temperature control the rotor *slows* whenever full recovery would overshoot the setpoint [1][10].
   - The R 400 V wheel delivers 17.4 °C at −10 °C and 18.9 °C at 0 °C [5]. A 17 °C setpoint therefore throttles recovery at any outdoor temperature above about −13 °C [calc].
   - At 0 °C and 200 m³/h that wastes about 130 W of free recovered heat [calc].
   - NTNU found that cutting a one-zone MVHR supply setpoint from 20 °C to 10 °C "substantially" reduces heat-recovery efficiency [30].
   - In Denmark, units with low supply setpoints opened their bypass excessively during the heating season [27].
   - The right setting is the per-mode "electric heater off" option [1], with a setpoint at or above extract temperature (or ECO with "Heat recovery control = Maximum"). The wheel then always runs at full recovery and the heat pump covers the small remainder.
4. **Independent lab data: a Komfovent rotary needs no frost protection down to −15 °C, and its true recovery is about 79 %, not 86-89 %.**
   - The PHI certificate for the Domekt R 450 V C6M gives heat recovery rate 79 %, efficiency ratio 0.65 and internal leakage 2.3 % [22].
   - It states that the aluminium rotor operates at low temperatures "without the need to use frost protection" [22].
   - The data sheets claim 86-89 % [5][6][7]. They are tested dry, balanced and without fan-heat correction [16].
   - For modelling, use η ≈ 0.70-0.80 for a well-balanced rotary [13][22][28].
5. **Rotor frost is humidity-driven, and the defence is to slow the wheel, which temporarily raises H.**
   - Swegon (a rotor maker) says plain aluminium rotors begin to freeze at about −8 °C at normal indoor humidity, and only below about −12 °C when indoor RH is under 30 % [29].
   - Komfovent claims −25/−30 °C [8][9][10][12].
   - Komfovent's R units handle humidity by *reducing airflow* ("condensate prevention") [1][3]. That lowers H and supply flow without warning; Modbus status bit 8 "FlowDown" flags it [4].
   - Expect H to wobble on the coldest, most humid days. The size is unmeasured for this house.
6. **A counter-flow Domekt CF has a modulated electric preheater from −4 °C** [1][9]. It is rated 0.5 kW, Δt 4.9 K on the CF 400 V [6].
   - Applying the EU "cold climate" default (1,003 h/yr below −4 °C, mean 5.2 K below) [16] gives roughly 300-400 kWh/yr of electricity for a 130-170 m² house [calc].
   - That preheat largely ends up as indoor heat, but at COP 1.
   - Comparable plate units need external preheaters of 1.2-1.7 kW to meet the PHI comfort test at −10/−15 °C [23].
7. **Imbalance frost mode ("Special") exists only on C8 CF units, and Komfovent advises against it in airtight A+ houses** [3].
   - Field studies show that imbalance itself cuts real recovery: by up to 14 % in Norwegian schools [28], and to about 50-57 % instead of 70-80 % in three of eleven Luxembourg dwellings [13].
   - Most of 100 Danish apartment units were poorly balanced [27].
8. **Real-world recovery is well below the data sheet.**
   - Luxembourg central units averaged 59 % ± 25 % [13].
   - A rotary AHU in a Katowice passive building averaged only 47 % annual temperature efficiency, against 80 % for a cross-flow unit in the same building (BMS data, 2015-16) [31, abstract only].
   - UK SAP applies an in-use factor of 0.70 by default and 0.25 for uninsulated ducts [15].
   - Norway's building code assumes 70 % *annual* recovery for rotary units [28].
9. **Fan heat lifts supply air by 0.5-1 K** [11]. The R 450 V draws about 0.30 Wh/m³ [22], roughly 60 W at 200 m³/h [calc]. An owner measured about 65 W average for fans and electronics [24]. That heat enters the house and belongs in the gains term.
10. **Bypass in shoulder seasons is a real heat-dump lever, contrary to a simple reading of note 05.**
    - At 200 m³/h, 22 °C inside and 5-15 °C outside, stopping recovery removes an extra 0.4-0.9 kW [calc]. That is enough to absorb much of a 1 kW sunny-afternoon gain.
    - It must be commanded on purpose. If the AHU's target sits below the heat pump's 22 °C, it will cool the house towards 20 °C by itself [1].
11. **Everything needed to treat ventilation as a measured input is on Modbus** [4][25].
    - Temperatures: supply 902, extract 903, outdoor 904.
    - Flows: 906-909.
    - Recovery and heating levels: heat-exchanger level 912, heater level 913, heater power 922 W, recovered power 923 W.
    - Status: bitmask 900.
    - Settings are writable: mode 5, setpoints, ECO 3, heat recovery control 217 [25].
12. **Recommendation, with medium-high confidence: make ventilation steady by configuration, then feed it to the house model as a measured disturbance.**
    - Use Φ_vent = ṁc·(T_supply − T_room), plus fan heat [11].
    - Keep it steady in winter: heater off, wheel at full recovery, constant flow.
    - Use it as a control lever only for deliberate shoulder-season bypass.
    - Night or away flow schedules change H by tens of W/K and must be read from Modbus, not assumed [calc][1].
13. **Lithuanian code context.** STR 2.01.02 requires a recuperator efficiency of at least 0.65 for mechanically ventilated buildings, with higher values in other items [35, snippet]. Many installers will therefore have tuned for compliance, not for heat-pump interaction.

## Detailed findings

### 1. How the ventilation term enters the heat balance

**Annex 71 framework** [11]. Controlled ventilation is kept out of the HTC and treated as its own term.
- Φ_vent = c_a·G_a·(1 − η_HR)·(θ_e − θ_i). When supply temperature is measured, use Φ_vent = c_a·G_a·(θ_sup − θ_i) instead.
- Supply-side heaters and frost preheaters must be in the energy balance, together with the supply setpoint and operating strategy.
- Fan heat: about 90 % of fan power becomes heat, giving a 0.5-1 K rise across the supply fan.
- When flow is not metered, mass flow can be taken as proportional to fan power^(1/3). Komfovent units meter flow directly (CAV), so this is not needed here [1][4].
- In the Twin Houses, including ventilation explicitly cut the HTC estimates by about 30 %.

**Senave et al.** [37, abstract only] found on-board-monitoring HLC estimates shift by up to 26.9 % depending mainly on input-data choices, especially the definition of interior temperature. The ventilation term is one more input whose omission biases H.

**Rating definitions differ, and the differences matter for modelling:**
- **EU 1253/2014 / EN 13141-7** [16]: dry, balanced, ΔT 13 K, no fan-heat correction.
- **PHI** [22][23]: η_HR = ((θ_ETA − θ_EHA) + P_el/(ṁ·c_p)) / (θ_ETA − θ_ODA). That is, PHI measures on the *exhaust* side and **subtracts fan heat**, so it is a lower and more honest number.
  - Domekt R 450 V: data-sheet class 86-89 % → PHI 79 % [22].
  - PHI's "efficiency ratio" ε_L, the reduction in ventilation heat loss versus no recovery, is only 0.65 for the R 450 V [22] and 0.66 for a comparable plate unit [23].
- **SAP** [15]: in-use factor 0.70 by default, 0.25 for uninsulated ducts.

**House numbers** [calc]. The ventilation flow is unknown, so three flows are shown:

| Flow (m³/h) | Raw ṁc (W/K) | Residual at η=0.80 | Residual at η=0.65 | Rotor stopped / bypass |
|---|---|---|---|---|
| 150 | 50 | 10 W/K | 18 W/K | 50 W/K |
| 200 | 67 | 13 W/K | 23 W/K | 67 W/K |
| 250 | 84 | 17 W/K | 29 W/K | 84 W/K |

- Against H = 140-200 W/K, switching from recovery to no recovery adds 25-60 % to H.
- A forum self-builder's design load dropped from 8 to 6.5 kW once MVHR was included [38]. Another builder estimated that ventilation would be about 70 % of winter heat loss without recovery [38]. These are forum estimates, but they show how big the term is in airtight houses.

### 2. Komfovent control logic that matters (C6/C6M; C8 similar)

**Temperature control modes** [1]:
- **Supply:** holds a fixed supply temperature.
- **Extract:** chooses the supply temperature needed to bring extract air to the setpoint.
- **Room:** the same, using the control-panel sensor.
- **Balance:** supply = extract, with no user setpoint.

**Defaults** [1]:
- The setpoint is **20 °C** in all standard modes.
- Intensities: AWAY 20 %, NORMAL 50 %, INTENSIVE 70 %, BOOST 100 %.
- The heat exchanger is used first, then the heaters.

**Electric heater per mode** [1]:
- The heater can be turned on or off separately for each ventilation mode.
- "If turned off, the heater will not turn on even when the desired temperature is not reached."
- Stage 1 can also be set to "None" globally.

**ECO mode** [1]:
- The electric heater is blocked.
- Free heating/cooling bypasses recovery when outdoor air is within the band (default supply minimum 15 °C, maximum 25 °C).
- If supply air falls below the minimum, the unit **reduces ventilation intensity** instead of heating.
- "Heat recovery control" settings: Auto; **Maximum**, which recovers "regardless of the desired temperature" except during free cooling/heating; and Non stop, intended for enthalpy exchangers.
- These settings are writable over Modbus. A Home Assistant user maps ECO to zero-based address 2 and constant heat recovery to address 216, which is 3 and 217 in the document [25].

**Rotor modulation:**
- On R units the rotor slows or stops "if recuperation is not required" [2]. Newer drives modulate rotor speed for "more accurate supply air temperature" [10].
- Rotor efficiency falls steeply at low speed: one study found 75.5 % at 5 rpm against 84 % at 12 rpm, with a plateau above about 10 rpm [39, snippet].

**Why lowering the supply setpoint is the wrong fix on a rotary unit** [calc, from R 400 V after-wheel data [5]]:

| Outdoor | After-wheel (full recovery) | Setpoint 17 °C | Setpoint 20 °C, heater on | Setpoint ≥ 22 °C, heater off |
|---|---|---|---|---|
| −15 °C | 16.7 °C | full recovery, no heater | heater ≈ 3.3 K × 67 ≈ 220 W | full recovery, 0 W |
| −5 °C | 18.1 °C | rotor throttled, ≈ 75 W of recovery wasted | heater ≈ 130 W | full recovery, 0 W |
| 0 °C | 18.9 °C | ≈ 130 W wasted | heater ≈ 75 W | full recovery, 0 W |
| +8 °C | ≈ 20 °C | ≈ 200 W wasted | rotor starts throttling | full recovery, 0 W |

With the heater off and the setpoint at or above extract temperature, the wheel never throttles in heating season. The heat pump supplies the remaining ventilation load at COP about 3-4.

**Fifth branch (R units)** [2]:
- Most rotary Domekts have an extra extract inlet (E) that bypasses the rotor. Komfovent says it lowers recovery and should not be used continuously.
- Warning W6 "low heat exchanger efficiency" flags it [1].

**Komfovent's own advice** [1]:
- Do not use the AHU as the main heater.
- Never switch it off; keep at least 20 % intensity to avoid condensation inside the unit.

### 3. Measured cost of the integrated heater (owner data)

A Komfovent Domekt R 450 V owner in the UK (OpenEnergyMonitor, Feb-May 2022) [24]:
- **Heater energy:** about 3-4 kWh per 24 h at 1-10 °C outdoor, with supply set to match extract temperature. The house was at 17-20 °C. Another member's reading of the same chart gave 3.28 kWh heater and 4.85 kWh total, leaving about 65 W average for fans and electronics.
- **The heater is about 1 kW.** The owner then automated the setup: whenever the heater switches on, Home Assistant lowers the supply setpoint until it stops.
  - This avoids resistance heat, but on a rotary unit it also throttles recovery, as shown in §2.
  - Switching the heater off per mode does the same job without throttling [1].
- **Normal flow:** the fan normally runs at 20 %, rising with extract CO₂.

**Scale for this house** [calc]:
- At +2 °C the house load is about 20 K × 0.17 kW/K ≈ 3.4 kW, or about 82 kWh/day. At COP about 3.5 that is about 23 kWh/day of heat pump electricity.
- A 3.3 kWh/day resistive heater is therefore about 4 % of heat but about 14 % of heating electricity.
- Over a Lithuanian heating season of roughly 180 days at 100-150 W average, that is about **430-650 kWh/yr**. The same heat from the heat pump would cost about 120-190 kWh.
- **Verification:** registers 937-938 (heater energy counters) or 922 (instant heater power) answer this directly [4].

Generic Polish consumer guidance quotes 300 W-2 kW preheaters running about 4 h/day in frost, about 4 kWh/day [34]. That is low-quality evidence, but the order of magnitude matches.

### 4. Frost protection: rotary vs counter-flow

**Rotary (Domekt R)**
- **Independent lab result (PHI)** [22]:
  - The R 450 V aluminium rotor works at low outdoor temperatures without frost protection. The certification test is at −15 °C.
  - The integrated electric *supply* heater (not a preheater) is what holds supply air at or above 16.5 °C at −10 °C.
  - The unit stops both fans if supply air falls to about 5 °C. That protects a downstream water coil, if one is fitted.
- **Komfovent claims** frost-free operation to −25 °C [9][12] or −30 °C [8][10] (manufacturer).
- **Swegon** (a rotor manufacturer, not Komfovent) [29]:
  - With extract air at 21 °C, aluminium rotors start excess-water formation from about 0 °C and freezing at about −8 °C.
  - With extract RH below 30 %, freezing starts only below about −12 °C.
  - Control is by measuring pressure drop and slowing, not stopping, the rotor. Temperature efficiency "drops significantly" at slow speed.
  - Sorption (hygroscopic) rotors resist frost much better.
- **Reconciling the claims.** The difference is mostly indoor humidity. Lithuanian winter air at −20 °C holds almost no water, so indoor RH in a ventilated house is often 20-35 %. Lab tests at moderate humidity pass at −15 °C [22].
  - The risk rises in a new, still-drying house, or with high occupancy and drying laundry. That is exactly when Komfovent's "condensate prevention" **cuts airflow** [1].
  - Status bit 8 "FlowDown" flags it [4].
- **Moisture carry-over is a side benefit that limits the frost problem.**
  - A SINTEF model of a Norwegian house estimated wheel moisture recovery up to 68 %, with a 19 % yearly average and limited effect on indoor RH [33, abstract only].
  - A Polish single-house in-situ test reported 32 % moisture recovery with 75 % temperature efficiency [36, snippet].
  - Swedish RISE lab work shows that rotor speed and airflow control can hold indoor moisture down in airtight houses. Swedish guidance keeps winter indoor moisture supply at or below about 3 g/m³ [36, abstract only].
- **EU ecodesign** sets defrost energy to zero for regenerative units [16].
- **Norwegian code** assumes 70 % annual recovery, which favours rotary units because "plate exchangers incur considerable defrosting energy in winter" [28].

**Counter-flow plate (Domekt CF)**
- Freezing is possible from −4 °C outdoor. The integrated or external preheater is modulated "based on the outdoor air temperature, airflow and the amount of moisture in the extracted air". A humidity sensor or control panel is required [1].
  - "Off" stops the AHU below −4 °C.
  - If the preheater is too weak, both fans slow gradually [1].
- **C8 options** [3]:
  - "Standard" stops the unit after 1 h below −4 °C.
  - "Special" imbalances the flows, is good to about −10 °C, and is not for A+ airtight houses or houses with a fireplace.
  - External heater or integrated preheater.
- **Preheater size:**
  - CF 400 V: 0.5 kW, Δt 4.9 K, plus a 1 kW post-heater [6].
  - Comparable PHI-certified plate units need an external electric preheater of about 1.2 kW (Vortice, controlled on exhaust and supply temperature) [23]. PHI search snippets show 1.5-1.7 kW for others.
  - PHI recommends exhaust air at or below +5 °C on average during frost protection, and excludes frost-protection power from the rated electric efficiency [23].
- **EU defrost method** [16]: Q_defr = t_defr × ΔT_defr × c_air × q_net × pef.

| Climate | Hours below −4 °C | Mean ΔT below −4 °C | Q_defr (primary) |
|---|---|---|---|
| Cold | 1,003 h | 5.2 K | 5.82 kWh/m²·a |
| Average | 168 h | 2.4 K | 0.45 kWh/m²·a |

  - With pef 2.5 and the cold value, this is about 2.3 kWh/m²·a of electricity [calc].
  - Lithuania lies between "average" and "cold". Vilnius January lows average about −6 °C [40]. No sourced figure for hours below −4 °C was found; it can be computed from the house's own outdoor sensor history.

### 5. Imbalance, leakage and shortcuts (field data)

- **Merzkirch et al., Luxembourg** [13]: 20 central units at 0-4 °C outdoor.
  - Mean temperature change rate 59 % (σ 25 %); good units reached 70-80 %.
  - Low values were due to excess extract flow and one broken exchanger.
  - Shortcut (short-circuit air) averaged 6.5 %; 7 of 20 units had more than 10 % imbalance.
  - Specific fan power about 0.475 Wh/m³, about twice the advertised figure.
- **Schild/Pedersen/Bryn, Norway** [28]: 5 rotary AHUs in schools, measured with tracer gas, temperatures and pressures.
  - Manufacturer efficiency documentation was "credible" but assumes balanced flow. Imbalance reduced true recovery by up to 14 %.
  - The purge sector was often not accounted for in balancing.
  - Internal recirculation was 0.2-1.4 %; one case had 8.3 % outside recirculation from the exhaust outlet back to the fresh-air inlet.
- **Smith & Kolarik, DTU** [27]: 100 Danish apartments with Modbus-connected MVHR.
  - A flow-ratio indicator (T_sup − T_out)/(T_in − T_exh) was computed, valid only with the bypass closed, outdoor below 10 °C, no boost and no condensation.
  - Most units were poorly balanced. Several had excessive bypass opening in heating season, attributed to low supply setpoints or sensor faults.
  - **This indicator can be computed from the Komfovent's own sensors** [calc].
- **Komfovent** [12] lists the causes of drift: filters clogging unevenly, wind, stack effect, and air density changes (about one fifth from −25 to +25 °C). CAV mode holds each fan's measured flow [1].
- **Imbalance and infiltration** [11]: imbalance is sub-additive with infiltration (Kiel-Wilson). Any extract surplus, for example from "Special" frost mode or an open fifth branch, draws cold air through the envelope at the full ΔT.

### 6. Supply air temperature, fan heat and ducts

- **Fan heat:** 0.5-1 K across the supply fan [11]. The R 450 V specific power is 0.30 Wh/m³ [22]. An owner measured about 65 W average for fans and electronics [24].
- **Bypass warming:** a UK Zehnder Q350 owner on 100 % bypass measured supply 2.5 K above outdoor at 230 m³/h [17].
- **Sensor error:** a Buildhub user estimated MVHR supply sensors reading about 1.5 K low [38b]. Cross-check register 902 against an independent probe before trusting the Φ_vent term.
- **Duct losses:**
  - A UK owner found 9-10 °C supply in one wing against 19-20 °C elsewhere, traced to a poorly insulated attic duct [18].
  - SAP's 0.25 factor reflects the same effect [15].
- **Warm supply air barely heats rooms.** NTNU (simulation, one-zone row-house bedroom) found that a 20 °C supply kept the coldest room at about 19 °C, while 10 °C supply gave just under 18 °C [30].
- **Where the supply sensor sits:** register 902 on a Komfovent is measured **after the heater** [4]. To separate wheel and heater contributions, use the heater power (922) or heater level (913).

### 7. Bypass and free cooling in mild and sunny weather

- **How it works.** ECO free heating/cooling runs without recovery when outdoor air is in the band [1]. In Supply control the wheel throttles automatically whenever full recovery would overshoot the setpoint [1][10].
  - With a 20 °C setpoint, R 400 V-class wheels reach 20 °C at roughly +7 to +8 °C outdoor [5][calc].
  - **Above about +8 °C, a 20 °C setpoint makes the unit discard recoverable heat continuously**: about 95 W at 12 °C and 200 m³/h [calc]. That falls exactly in the mild weather where the heat pump already cycles.
- **Possible field evidence.** The rotary unit's 47 % *annual* efficiency in Katowice [31, abstract only] fits a wheel that throttles for much of the year. The cause was not confirmed from the full text.
- **Heat-dump capacity** [calc], from 200 m³/h at 22 °C indoor with the rotor stopped:

| Outdoor | Extra heat removed (beyond the η=0.8 residual) |
|---|---|
| 5 °C | 0.9 kW |
| 10 °C | 0.64 kW |
| 15 °C | 0.37 kW |

  At 250 m³/h these scale up by 25 %.
- **Owner practice.** One owner opens the bypass at 24 °C room and closes it at 22.5 °C (1.5 K hysteresis) [24]. Another uses a 25 °C outdoor switch with 5 K hysteresis [24].
- **Danish field data** [27] shows that bypass opening during the heating season is usually a setpoint error, not a benefit.

### 8. Should ventilation be scheduled or treated as a disturbance?

- **Annex 71** [11]: without explicit ventilation, the HTC is biased by up to about 30 %. Supply temperature, flow and supply-side heating should be inputs. Annex 71 does not address scheduling.
- **Komfovent** [1]: run continuously, at 20 % or more. Weekly schedules are offered. Home Assistant users already script mode and setpoint writes by CO₂ and time of day [25].
- **Synthesis** (my view, medium-high confidence):
  - **Configure for steadiness in winter:**
    - heater off in all routine modes;
    - wheel at full recovery, either Balance or Supply with setpoint at or above extract temperature, or ECO with "Maximum";
    - constant or slowly varying flow.
  - **Measure, don't predict:** feed Φ_vent = 0.335·V_sup·(T_sup − T_room) + fan heat into the house model as a measured disturbance at each step.
  - **Use bypass as a deliberate lever** only on mild, sunny shoulder days when the room is forecast to overshoot.
  - **Model, don't fight, CO₂ or humidity-driven boosts** (KITCHEN, condensate prevention). They are short and visible on Modbus.
  - **Day/night flow schedules** (for example AWAY 20 % against NORMAL 50 %) change raw conductance by about 40 W/K at 400 m³/h nominal, but the residual H by only about 8 W/K at η 0.8 [calc]. That is acceptable if flow is read, harmful if it is assumed.

## What this means for controlling this house

Confidence is shown per item. All AHU changes are reversible from the C6/C8 panel, the app or Modbus.

1. **Identify the unit and its current configuration before anything else** (high confidence that it matters).
   - Read register 955 (0 = plate, 1 = rotary).
   - Read the temperature-control mode and the per-mode setpoints, flows and heater on/off.
   - Read the ECO settings (200-204, 217) and icing protection (40) [4].
   - Read the heater energy counters (937-938) for last winter.
   - **Test:** if last winter's heater energy exceeds about 200 kWh, item 2 is worth doing immediately.
2. **Switch the integrated electric heater off in NORMAL, AWAY and the other routine modes. Do not lower the supply setpoint instead** (high confidence on direction, medium on size: about 300-600 kWh/yr resistive saved, replaced by about 100-190 kWh of heat pump electricity [calc]).
   - Then set the mode setpoint to about 22 °C in Supply control, or use Balance, so the wheel never throttles in the heating season.
   - An alternative is permanent ECO with heat recovery control "Maximum" and free cooling off in winter. Also lower ECO's minimum supply temperature, or ECO will **cut airflow** when supply falls below 15 °C [1].
   - **Comfort check:** supply air will be about 15.5-19 °C at −23 to 0 °C [5]. That is fine with slab UFH, but check for draughts at bedroom diffusers. The PHI comfort limit is 16.5 °C at −10 °C, which the R 450 V meets only *with* the heater [22]; below about −12 °C supply will drop a little under it.
   - **Rollback trigger:** occupants notice cold draughts.
3. **Never let the AHU's target sit below the heat pump's room target** (high confidence).
   - With Extract or Room control, set 22-22.5 °C.
   - With Supply control, use the 22 °C plus heater-off setting from item 2.
   - A 20 °C default target turns the AHU into a cooler that fights the slab on every mild afternoon [1][27].
4. **On a CF unit, keep icing protection "On" (integrated preheater) and never use "Special" imbalance mode** (medium-high confidence) [3][13][28].
   - Log heater power (922). Count it as electricity used and as an in-house gain, but not twice.
   - Consider whether a few hours of reduced flow below −15 °C are preferable to preheater energy. That is the owner's comfort call.
5. **On an R unit, watch condensate-prevention flow cuts and rotor slowdowns** (medium confidence).
   - Read status bit 8 FlowDown, the actual flows (906-909) and the heat-exchanger level (912).
   - Both lower or raise H for hours, and the slab controller should see this through the measured Φ_vent term rather than as unexplained error.
6. **Model ventilation explicitly as a measured disturbance** (high confidence).
   - Φ_vent = 0.335 × V_sup (m³/h) × (T_sup − T_room) W, from registers 902 and 906-907.
   - Fan heat (about 60 W) is already in T_sup if the sensor is after the fan; otherwise add it.
   - Fit fabric plus infiltration H on top. Expect the fabric H to come out below the current lumped 0.14-0.20 kW/K, by up to about 30 % [11].
   - **Test:** refit H on two months of data with and without the term, then compare residual variance and the day-to-day spread of fitted H.
   - **Balance check:** compute the Danish flow-ratio indicator [27] from 902-904 and the exhaust temperature, if exposed. A ratio far from 1 means imbalance, so rebalance.
7. **Use bypass as an overheating valve on mild sunny days, instead of a heat-pump off-then-catch-up cycle** (medium confidence).
   - When the forecast or the room says the house will exceed about 22.5 °C, enable free cooling or raise intensity for a few hours (Modbus mode and ECO writes [25]).
   - Disable it again before evening.
   - The expected removal is about 0.4-0.9 kW at 5-15 °C outdoor [calc].
   - **Test:** on matched sunny shoulder days, compare peak room temperature and the next morning's flow-temperature demand with and without bypass.
8. **Keep night flow constant in the heating season, or read it** (medium confidence). Never switch the AHU off; Komfovent says keep at least 20 % [1].
9. **Seal or close the fifth branch, check duct insulation, and cross-check the supply sensor against an independent probe** (medium confidence) [2][15][18][38b].
10. **What to avoid:**
    - the AHU heater as a hidden top-up heater [24];
    - a low supply setpoint as a "fix" on a rotary unit [30][27];
    - ECO free heating/cooling with a 20 °C target in winter;
    - imbalance frost mode [3];
    - using the data-sheet 86-89 % in the model. Use about 0.75 for a rotary until measured, per PHI's 79 % [22] and the field 70-80 % [13][28].

## Contradictions and open questions

- **Rotary frost-free temperature.**
  - Komfovent claims −25/−30 °C [8][9][10][12]. PHI confirms operation without frost protection in a −15 °C test [22]. Swegon says aluminium rotors freeze from about −8 °C at normal humidity, or −12 °C below 30 % RH [29].
  - These are compatible only if indoor RH is low, which it usually is in Lithuanian deep cold. In a humid house the R unit protects itself by cutting airflow [1].
  - Still open: no measured Komfovent rotor behaviour below −15 °C was found.
- **Rated vs real efficiency.**
  - Data sheets: 86-89 % [5][6][7].
  - PHI lab: 79 %, ε_L 0.65 [22].
  - Field: 59 % mean, 70-80 % for good units [13]; up to 14 % lost to imbalance [28]; 47 % annual for one rotary in Poland [31, abstract only].
  - Not averaged here: the model should estimate η from this house's own data.
- **First pass vs this pass on the supply setpoint.** The first pass recommended a 16-17 °C setpoint. This pass shows that would throttle the rotor above about −13 °C [calc][5][30]. Heater-off is the better setting.
  - **For a CF unit** a lower setpoint also opens the bypass. The same correction applies.
- **Is a preheater a loss or a gain?** Its heat mostly ends up indoors, at COP 1, but it reduces the plate's effective recovery. No measured split was found.
- **Note 05 vs this note on ventilation as a heat dump.** Note 05's "3,000 m³/h to move 500 W" assumes a 2 K inside-outside difference, which is summer. At 5-15 K, in the shoulder season, 200 m³/h removes 0.4-0.9 kW [calc]. Both hold, at different conditions.
- **Open:**
  - the actual model (R or CF) and controller;
  - the configured flows and modes;
  - whether the heater is on and what it used last winter;
  - whether ducts run through a cold attic;
  - indoor winter RH;
  - hours below −4 °C at the house;
  - the Home Assistant Modbus path to the AHU (TCP on the C6 is documented [25]).
- **Not reached in full text:**
  - Michalak 2019 (Katowice rotary 47 %);
  - Senave 2019;
  - RISE 2025 Roomvent;
  - SINTEF 2022 wheel-moisture paper;
  - the Rafati Nasr 2014 and Alonso 2015 frost reviews;
  - Swedish Energy Agency FTX tests.

## Sources

1. DOMEKT C6M user's manual (C6M_user manual_26-10) - UAB Komfovent - 2026 - https://www.komfovent.com/en/downloads/DOMEKT_C6M_user_manual_EN.pdf - manufacturer - Control modes; 20 °C defaults; per-mode heater on/off; ECO (heater blocked, free heating/cooling 15-25 °C, flow cut below minimum, recovery Auto/Maximum/Non stop); CF preheater from −4 °C; R condensate prevention cuts flow; keep at least 20 %. (Re-read in full this pass.)
2. DOMEKT C6M installation manual (26-10) - UAB Komfovent - 2026 - https://www.komfovent.com/en/downloads/DOMEKT_C6M_installation_manual_EN.pdf - manufacturer - Rotor stop vs CF bypass; fifth extract branch; external preheater on 0-10 V.
3. DOMEKT C8 user's manual (26-09) - UAB Komfovent - 2026 - https://www.komfovent.com/en/downloads/DOMEKT_C8_user_manual_EN.pdf - manufacturer - CF frost modes Standard / Special (imbalance, to −10 °C, not for A+ houses) / external / integrated.
4. MODBUS connection description C6/C6M (M-C6/C6M_26-07) - UAB Komfovent - 2026 - https://www.komfovent.com/en/downloads/MODBUS_connection_C6_EN.pdf - manufacturer - Register map: 900 status, 902-911 temperatures and flows, 912-913 levels, 922-924 heater W, recovered W, efficiency; 937-944 counters; 955 HX type.
5. Domekt R 400 V C6M technical data - UAB Komfovent - 2026 - https://www.komfovent.com/en/downloads/DOMEKT_R_400_V_C6M_EN.pdf - manufacturer - 86 %; 1 kW heater; after-wheel 15.6-18.9 °C at −23…0 °C.
6. Domekt CF 400 V C6M technical data - UAB Komfovent - 2026 - https://www.komfovent.com/en/downloads/Domekt_CF_400_V_C6M_EN.pdf - manufacturer - 89 %; preheater 0.5 kW / 4.9 K; heater 1 kW.
7. Domekt R 350 V C8 technical data - UAB Komfovent - 2026 - https://www.komfovent.com/en/downloads/Domekt_R_350_V_C8_EN.pdf - manufacturer - 89 % rotary; 17.1-19.6 °C after wheel.
8. Rotary heat exchanger - the best solution for homes in cold climates - Komfovent blog - 2026 - https://www.komfovent.com/en/news/blog/rotary-heat-exchanger-the-best-solution-for-homes-in-cold-climates-why-231 - manufacturer - Rotary 90 % to −30 °C, no preheater.
9. How does a preheater work… - Komfovent blog - 2025 - https://www.komfovent.com/en/news/blog/how-does-a-preheater-work-and-why-is-it-necessary-for-a-residential-ventilation-unit-185 - manufacturer - CF preheater from −4 °C, pulsed; rotary to −25 °C.
10. Komfovent rotary heat exchangers / variable rotor speed control - Komfovent - c. 2019-2021 - https://komfovent.com/en/news/products/komfovent-rotary-heat-exchangers-59 - manufacturer - Rotor up to 85 %, −30 °C; rotor speed modulates supply temperature.
11. IEA EBC Annex 71 Subtask 3: Physical parameter identification - Annex 71 participants - 2021 - https://www.iea-ebc.org/Data/publications/EBC_Annex71-ST3-Physical_parameter_identification.pdf - paper (field cases) - Φ_vent formulas, fan heat 0.5-1 K, preheaters in the balance, about 30 % HTC shift.
12. Komfovent frost-prevention and ventilation close-up posts - Komfovent - 2020-2025 - https://www.komfovent.com/en/news/products/smart-multi-level-frost-prevention-32 - manufacturer - Plates freeze below −4 °C; CAV; density drift.
13. Field tests of centralized and decentralized ventilation units in residential buildings - Merzkirch, Maas, Scholzen, Waldmann, Energy and Buildings 116 - 2016 - https://orbilu.uni.lu/bitstream/10993/27775/1/Paper_%20Field%20Tests.pdf - field data - Central units 59 % ± 25 %; 6.5 % shortcuts; imbalance; SFP 0.475 Wh/m³.
14. Heat recovery ventilation operation traded off against natural and simple exhaust ventilation in Europe - Laverge, Janssens, Energy and Buildings 50 - 2012 - https://biblio.ugent.be/publication/2141670 - paper (simulation) - Ventilation plus infiltration about half of loss in insulated houses.
15. SAP 10.2 - BRE / UK Government - 2021 - https://files.bregroup.com/SAP/SAP%2010.2%20-%2017-12-2021.pdf - standard - MVHR in-use factor 0.70; 0.25 for uninsulated ducts.
16. Commission Regulation (EU) No 1253/2014 - European Commission - 2014 - https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32014R1253 - regulation - Test conditions; defrost energy only for recuperative units; cold climate 1,003 h below −4 °C.
17. MVHR warming incoming air on 100 % bypass (Zehnder Q350) - Buildhub forum - 2024-25 - https://forum.buildhub.org.uk/topic/47281-mvhr-warming-incoming-air-on-100-bypass-zehnder-q350/ - forum - +2.5 K on full bypass.
18. Cold air - Buildhub forum - 2025 - https://forum.buildhub.org.uk/topic/43416-cold-air/ - forum - 9-10 °C vs 19-20 °C supply from an attic duct.
19. Thermal wheel - Wikipedia - accessed 2026 - https://en.wikipedia.org/wiki/Thermal_wheel - encyclopedia - Wheel frost control by speed, preheat or jogging.
20. Running MVHR in the summer - Buildhub forum - 2024 - https://forum.buildhub.org.uk/topic/43429-running-mvhr-in-the-summer/ - forum - Run year-round (minor).
21. Komfovent downloads index (JSON) - UAB Komfovent - 2026 - https://www.komfovent.com/en/ajax/downloads/filter?taxon[]=ahud - manufacturer - Locates [1]-[7].
22. Certified Passive House Component: Komfovent Domekt R 450 V C6M (ID 1737vs03) - Passive House Institute - certified 2021, certificate valid to end 2026 - https://database.passivehouse.com/de/components/certificate/download/1808/en - lab (independent) - η_HR 79 % (fan-heat corrected), ε_L 0.65, 0.30 Wh/m³, internal leakage 2.3 %, rotor needs no frost protection, heater needed for 16.5 °C at −10 °C, fans stop at 5 °C supply.
23. Certified Passive House Component: Vortice VORT HR 300 NETI IoT (ID 2162vs03) - Passive House Institute - valid to 2026 - https://database.passivehouse.com/es/components/certificate/download/2233/en - lab (independent) - Plate unit: 86 % but ε_L 0.66; needs about 1.2 kW external preheater; frost power excluded from the efficiency rating.
24. Komfovent Domekt R-450-V Heat Recovery Unit (thread) - OpenEnergyMonitor community (borpin, djh and others) - 2022 - https://community.openenergymonitor.org/t/komfovent-domekt-r-450-v-heat-recovery-unit/19873 - forum (owner measurements) - Heater 3.3-4 kWh/day at 1-10 °C with supply = extract; about 65 W fans; setpoint-lowering automation; bypass 24/22.5 °C.
25. Komfovent C6 in Home Assistant - Cavelab blog - c. 2021-23 - https://www.cavelab.dev/posts/komfovent-c6-in-home-assistant/ - blog - Zero-based register map (901 supply, 921 heater W, 922 recovery W, 923 efficiency), writes for mode (4), setpoints (109/115/134), ECO (2), constant heat recovery (216).
26. Modbus Sensor TCP for Komfovent - Home Assistant community - 2020-2024 - https://community.home-assistant.io/t/modbus-sensor-tcp-for-komfovent/173215?page=3 - forum - Register configs, data-type (uint16) and off-by-one pitfalls; no winter data.
27. Evaluation of supply temperature set-points and airflow imbalance using smart ventilation data - K.M. Smith, J. Kolarik (DTU), AIVC conference paper - c. 2023-24 - https://www.aivc.org/sites/default/files/036.pdf - field data (100 apartments) - Flow-ratio indicator from unit sensors; most units unbalanced; low supply setpoints cause heating-season bypass.
28. New report on hygiene and energy performance of rotary heat exchangers - P.G. Schild (SINTEF), A.J. Pedersen, I.H. Bryn - AIVC AIR newsletter 30(2) - 2009 - https://inive.org/sites/default/files/air0903_web_ed.pdf - field data (5 school AHUs) - Norwegian code assumes 70 % annual recovery; plates need considerable defrost energy; imbalance costs up to 14 %; 0.2-1.4 % recirculation.
29. Condensation and frosting in rotary heat exchangers - Swegon blog - n.d. - https://blog.swegon.com/en/condensation-and-frosting-in-rotary-heat-exchangers - manufacturer (non-Komfovent) - Aluminium rotor freezing from about −8 °C, −12 °C if RH below 30 %; slow, don't stop, the rotor; efficiency drops at low speed.
30. Check the supply air temperature! - M. Berge, NTNU/HiB, ZEB Annual Report 2014 p. 34 - 2014 - https://ntnu.no/trykk/publikasjoner/ZEB_Annual_Report_2014/files/assets/basic-html/page-34.html - paper (simulation) - Supply 20 → 10 °C: coldest room 19 → about 18 °C; substantially reduced recovery.
31. Temperature efficiency of heat exchangers in air handling units - P. Michalak, J. Mech. Energy Eng. 3(3) - 2019 - https://jmee.tu.koszalin.pl/ojs/index.php/jmee/article/view/133 - field data (BMS), abstract only - Rotary 47.2 % vs cross-flow 80.1 % annual, Katowice passive building, Aug 2015-Jul 2016.
32. MVHR ASHP post heater control - Buildhub forum - 2020 - https://forum.buildhub.org.uk/topic/18141-mvhr-ashp-post-heater-control - forum - Post-heaters overheat non-calling rooms; MVHR supply a little below room temperature; a 475 W electric duct heater lifts 14 → 27 °C.
33. The use of machine learning to determine moisture recovery in a heat wheel and its impact on indoor moisture - SINTEF - 2022 - https://sintef.brage.unit.no/sintef-xmlui/handle/11250/2995414 - paper (model), abstract only - Moisture recovery up to 68 %, 19 % yearly average; limited RH effect in an airtight house.
34. Ile prądu zużywa rekuperator? - kb.pl - c. 2024 - https://kb.pl/ogrzewanie/rekuperacja/ile-pradu-zuzywa-rekuperator-sprawdzamy-koszty-uzytkowania/ - blog (low weight) - Preheaters 300 W-2 kW, about 4 kWh/day in frost; 300-500 kWh/yr typical total.
35. STR 2.01.02:2016 amendment (Energy performance of buildings) - LR Aplinkos ministerija, e-Seimas - 2020 - https://e-seimas.lrs.lt/rs/legalact/TAD/84007dc001c211ebbedbd456d2fb030d/ - regulation, snippet only - Recuperator efficiency at least 0.65 (other items 0.75/0.80); fan electricity 0.75 Wh/m³.
36. RISE Roomvent 2025 paper on rotary exchangers in airtight Swedish houses; Kostka & Kołodko 2025 in-situ test (Poland) - 2025 - https://www.e3s-conferences.org/articles/e3sconf/abs/2025/72/e3sconf_roomvent2025_03024/e3sconf_roomvent2025_03024.html ; https://journals.pcz.pl/instal/en/article/view/103 - lab / field, abstracts only - Rotor speed and flow control limit indoor moisture; 3 g/m³ guidance; 32 % moisture and 75 % temperature efficiency in situ.
37. Senave, Roels et al., sensitivity of on-board-monitoring HLC characterisation - Energies 12(17):3322 - 2019 - https://ideas.repec.org/a/gam/jeners/v12y2019i17p3322-d261819.html - paper (field case), abstract only - HLC shifts up to 26.9 % from input-data choices.
38. Does MVHR affect heat loss calculations much? / Impact of MVHR on heat demand calcs - Buildhub forum - 2022-23 - https://forum.buildhub.org.uk/topic/28687-does-mvhr-affect-heat-loss-calculations-much/ - forum - Design load 8 → 6.5 kW with MVHR; ventilation about 70 % of loss without recovery (estimates). 38b. Air temperature uplift even on bypass - Buildhub - https://forum.buildhub.org.uk/topic/11000-air-temperature-uplift-even-on-bypass - forum - Supply sensor about 1.5 K low.
39. Rotary regenerator rpm-efficiency data (Buyukalaca & Yilmaz 2002 and a 2025 study) - via search snippets - https://avesis.cu.edu.tr/yayin/61ae926d-8edb-48fe-93fa-699184806aa4/influence-of-rotational-speed-on-effectiveness-of-rotary-type-heat-exchanger - paper, snippet only - Efficiency plateau above about 10 rpm; 75.5 % at 5 rpm vs 84 % at 12 rpm.
40. Average weather in Vilnius - WeatherSpark - accessed 2026 - https://weatherspark.com/y/92695/Average-Weather-in-Vilnius-Lithuania-Year-Round - climate data (secondary), snippet - Cold season 18 Nov-13 Mar; January mean low about −6 °C.
