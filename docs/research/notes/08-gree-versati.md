# Gree Versati specifics

> Research date: 2026-11-06. Topic owner: researcher 08 of 15.
> Method: I read full manufacturer manuals (service manuals, control-panel manuals, the Modbus protocol, distributor datasheets), extracting the PDF text locally, plus Home Assistant, GitHub and installer-forum threads. I read 34 distinct sources ([1]–[34]).
> **Gap:** the web-search budget shared by all 15 researchers ran out after **13 searches**, short of the planned 25 or more. I ran the Polish and German Versati-specific searches. I could not run the Lithuanian, Swedish, Dutch or extra UK forum searches. Most depth here comes from primary Gree documents, so the evidence is **manufacturer-heavy**. Versati-specific field data barely exists online: heatpumpmonitor.org showed no Gree system in the part I checked [34].
> I did not read this repository's code or docs.

## Summary

1. **The "restart delta" is Gree's ΔT-Heat ("Δt2", called "temperature difference" or "temperature deviation for heating").** It is Modbus holding Word 30, range 2–10 K in 1 K steps, factory default **10 K** [1][2][3][10].
   - The owner sees the unit restart only when the setpoint is about 4–5 K above the outlet temperature, with the register set to 4. That matches a restart-hysteresis meaning.
   - The lowest allowed value is **2 K**.
   - "T-water ctrl" is a different setting. It only selects the High-temp or Normal-temp leaving-water range, and floor heating forces Normal-temp [2].

2. **The firmware controls the compressor like a proportional controller on leaving water** [2][3]:
   - Compressor frequency rises with (setpoint − leaving water temperature, LWT).
   - If the compressor is at minimum frequency and LWT is still above setpoint, the unit shuts down. A normal shutdown first ramps down to minimum frequency.
   - **Heat run time** (Word 34, 1–10 min, default 3 min, or 5 min with the heating 2-way valve enabled) sets how long the temperature difference must stay in the "standby zone" before the unit stops [3][4][1].
   - Fixed timers: a **3-minute restart lockout** [5][2]. The first-generation manual also states **no capacity adjustment for 6 min after start** and an expansion valve frozen for 3 min [5].
   - Consequence: every "start kick" the owner writes over Modbus is also a high-frequency command, unless output is capped.

3. **No Gree document gives the minimum heating capacity** [3][12][13][14]. The compressor modulates stepless between **20 and 120 Hz (900–6600 rpm)** [12]. The 10 kW split and all-in-one is rated **9.5 kW at A7/W35** [12][13]. The owner's measured 3.7–3.8 kW minimum is about 40% of nominal, which is plausible. It can be checked from Word 142/143 (set and actual Hz) [1][23].

4. **Gree's own data put the flow-temperature penalty at about 2–3% COP per 1 K of leaving water.**
   - 10 kW Versati III split: COP **4.61 / 3.60 / 2.59** at A7 with W35/45/55, and **2.81 / 2.23 / 1.58** at A−7 [13].
   - Versati IV 10 kW monobloc: 5.05 / 4.04 / 3.18 at A7 [14].
   - Lowering the average leaving water by 4 K is therefore worth roughly 8–11% of electricity at equal heat (full-load data).

5. **Outdoor temperature has a large effect.** The same 10 kW split gives COP 4.61 at A7/W35 and 2.81 at A−7/W35 [13]. The Versati III maximum-capacity factor at W35 rises from **0.74 at −15 °C to 1.19 at +10 °C** [3]. Heating in the warmest hours of the day pays twice: better COP and more PV.

6. **The built-in weather curve is a two-point straight line** (Lower AT ↔ Upper WT, Upper AT ↔ Lower WT) [22][2].
   - Its ranges depend on generation and on the floor setting. The R32 Modbus document lists Upper WT 46–60 °C and Lower WT 20–45 °C (defaults 55/40) [1]. Versati II "Normal temp" allows Upper WT 30–55 °C and Lower WT 25–29 °C (defaults 35/29) [2].
   - **While weather-dependent mode is on, the manual water setpoint is ignored** [2]. Writing Word 10 does nothing while coil 22 = 1.

7. **Quiet mode lowers compressor and fan frequency, and therefore capacity** [2][7], by at least 3 dB(A) [12]. One field report on a 16 kW Versati III: quiet mode cut fan speed sharply and **defrosts came every ~52–56 min at +2…+5 °C**, much less often without quiet mode [24]. Avoid it on humid days near 0 °C.

8. **A power or current limit exists** ("C/P limit": Off / Current limit / Power limit) [1][9][10]:
   - Current limit 0–50 A, default 16 A (Word 38).
   - Power limit 0.0–10.0 kW, default 3.0 kW (Word 43).
   - A one-time power cap stops the ~3 kW "catch-up" bursts without any frequent writes.

9. **Defrost.** First-generation defaults [5]:
   - Start after at least 50 min of accumulated compressor running with the coil below −4 °C.
   - End after 10 min or when the coil passes 15 °C.
   - Later generations advertise adaptive "smart defrost" [2][3]. Manual defrost ends at a coil temperature of 20 °C [8][9].

10. **Modbus basics** [1][19][21]:
    - RS485 at 9600 baud 8N1, RTU, on the wired controller's port. Function codes 01/03/0F/10. At most 127 words per read.
    - The last command wins between the panel and the building-management system.
    - Mode can only be changed while the unit is off.
    - **Changes take effect immediately but are "memorized" (stored) after 30 minutes.**
    - Register maps differ between protocol versions (1.0, 1.1, 1.5, 1.7, 2.2) [19][22][24].

11. **Memory wear (EEPROM) from frequent writes.** Gree publishes no endurance figure.
    - Worst case is about 48 stores per day (17.5k per year) if every 30-minute write changes the value.
    - Typical endurance is about 1M cycles for modern EEPROM but only about 10k for flash [33]. That is fine for a true EEPROM and risky for flash without wear levelling.
    - Write only when the value changes. The register resolution is 1 °C anyway.

12. **Pump.** The inverter pump modulates on the entering/leaving temperature difference [2][3]. The manuals imply it **keeps running in standby** [4][10]. It draws up to 75–85 W [12]. In this house that could be 5–10% of mild-weather electricity. Measure it (coil 175).

13. **Hot water on the all-in-one** [3][9][10]:
    - Tank setpoint 40–80 °C, default 50 °C.
    - ΔT-hot water 2–8 K, default 5 K (2–25 K on newer panels).
    - T-HP max 40–55 °C, default 50 °C.
    - In Heat + hot water mode, hot water has priority by default.
    - Disinfection runs weekly at 70 °C, by default Saturday 23:00.
    - Tank-heater Logic 1 never runs the compressor and the tank heater together.
    - Hot-water SCOP is 2.95 (average climate) for the 8 and 10 kW split [13].

14. **Hydraulics.** Versati III monoblock: minimum system water volume **20 L**. Default design volume is 66 L for 10–16 kW units, with a 3 L expansion vessel at 1.5 bar [4]. Gree does not require a buffer. The **flow-switch trip cannot be cleared without a power cycle** [2][3]. Closing UFH loops can trip it [20].

15. **Field context.**
    - Fraunhofer ISE monitored 77 systems for 4 years. Air-source heat pumps reached an average seasonal efficiency of **3.4 (range 2.6–4.9)**. Many units were oversized for their consumption, and some had very high switching frequencies [31].
    - An installer forum makes the same point: extra water volume lengthens cycles but cannot change the on/off ratio when minimum output exceeds the load [29].

## Detailed findings

### 1. Generations, model codes, refrigerant and compressor

| Generation | Refrigerant | Key hardware | Notes | Src |
|---|---|---|---|---|
| Versati (I), about 2012 | R410A | Inverter twin rotary | Only manual found that states the timers explicitly: 3-min restart lockout, 6-min capacity hold, valve fixed 3 min. Has defrost and anti-freeze defaults | [5] |
| Versati II (NaE), 2013–2016 | R410A | Inverter with gas injection ("enthalpy-adding") and two expansion valves (two-stage throttling) | 8 / 10 / 12 / 14 / 16 kW split, e.g. GRS-CQ10Pd/NaE-K (10 kW) | [2][6] |
| Versati III (Nh…), about 2019+ | **R32** (GWP 675) | **Gree two-stage rotary compressor with gas injection**. Inverter fan and pump | NhG = monobloc, NhH = split, PdG/NhH = all-in-one indoor unit. Heating at outdoor −25…+35 °C, leaving water 25–60 °C | [3][12][16] |
| Versati IV (NhG3), about 2022+ | R32 | Gree says: its own patented two-stage injection compressor [14]. A German blog says: Panasonic twin-rotary EVI [32] | Leaving water up to 65 °C. MB10: 10.2 kW at A7/W35, COP 5.05, SCOP(35) 4.48, seasonal efficiency ηs 136% | [14][32] |
| Versati V, 2025/26 | **R290** | Monobloc | Up to 80 °C. Adds a "compensation mode" with a water-temperature offset, an SG/EVU input, energy histograms and flow feedback | [11][32] |

**Versati III all-in-one hardware** [12]:
- Indoor units GRS-CQ8.0PdG/NhH-E(I) and **GRS-CQ10PdG/NhH-E(I)**, 600×600×1750 mm.
- Inverter circulation pump of about 75 W.
- Backup heater in two steps of 3 kW. The table extraction was partly garbled.

**Matching outdoor unit GRS-CQ10Pd/NhH-E(O)** [12][13]:
- **9.5 kW at A7/W35**, COP 4.59–4.61.
- 9.5 kW at A7/W45, COP 3.60.
- 1.6 kg R32. Air flow 3512 m³/h.

**Which unit the owner most likely has (inference, medium confidence).** A "9 kW class Versati with tank" is most likely the **Versati III All-in-One 10 kW**: 9.5 kW nominal, R32, two-stage compressor. A Versati II 10 kW would be R410A [2]. Check the nameplate. The register map and limits differ by generation and protocol version [19][24].

### 2. Capacity and COP data for the 8–10 kW units

Distributor datasheet for the Versati III split (NHH2-E), heating values [13]:

| Condition | SP8 capacity (kW) | SP8 COP | SP10 capacity (kW) | SP10 COP |
|---|---|---|---|---|
| A7 / W35 | 8.00 | 4.66 | 9.50 | 4.61 |
| A7 / W45 | 8.00 | 3.70 | 9.50 | 3.60 |
| A7 / W55 | 7.36 | 2.74 | 8.74 | 2.59 |
| A−7 / W35 | 5.60 | 2.85 | 6.65 | 2.81 |
| A−7 / W45 | 5.60 | 2.29 | 6.65 | 2.23 |
| A−7 / W55 | 5.12 | 1.67 | 6.08 | 1.58 |

Other data from the same sheet: hot-water SCOP (average climate) 2.95 for both sizes. Backup heater 3+3 kW. Outdoor sound pressure 55 dB(A).

Versati IV monobloc MB10 (NhG3-E) [14]:
- A7/W35 10.2 kW, COP 5.05. A7/W45 COP 4.04. A7/W55 COP 3.18.
- A−7/W35 8.16 kW, COP 2.98.
- SCOP(35) 4.48, SCOP(55) 3.45. Seasonal efficiency ηs 136% (average climate).

**Derived sensitivity (my arithmetic).**
- Leaving water, from [13] SP10: 2.2%/K from W35 to W45 and 2.8%/K from W45 to W55 at A7. At A−7: 2.1%/K and 2.9%/K.
- Versati IV gives 1.9–2.3%/K [14].
- These are full-load rating points. Part-load slopes may differ (evidence type: manufacturer).

**Versati III monobloc maximum-capacity correction factors** (multiply the nominal heating capacity) [3]:

| LWT \ outdoor | −15 | −10 | −5 | 0 | +5 | +10 | +15 | +20 | +25 |
|---|---|---|---|---|---|---|---|---|---|
| 30 °C | 0.81 | 0.91 | 1.00 | 1.10 | 1.18 | 1.26 | 1.35 | 1.41 | 1.45 |
| 35 °C | 0.74 | 0.84 | 0.93 | 1.03 | 1.11 | 1.19 | 1.28 | 1.36 | 1.41 |
| 45 °C | 0.60 | 0.70 | 0.80 | 0.89 | 0.97 | 1.05 | 1.13 | 1.19 | 1.25 |
| 55 °C | 0.46 | 0.56 | 0.66 | 0.74 | 0.83 | 0.90 | 0.98 | 1.05 | 1.10 |

At +5 °C and W35 this gives 1.11 × nominal. So the nominal rating is not the compressor maximum.

The datasheet ratings do not agree with this table. The A−7/W35 rating of 6.65 kW [13] is lower than the table's implied ~9 kW at −5 °C. The two documents describe different units and probably different test points (declared capacity versus maximum). Treat these numbers as indicative only.

- **Minimum capacity: not published** in any Gree document I read [3][12][13][14][35].
- **Compressor range:** 20–120 Hz, 900–6600 rpm, "stepless" [12].
- **Modbus frequency registers:** Word 142 (set) and Word 143 (actual) are scaled 0–100 Hz [1]. A forum post describes Word 142 as the commanded and Word 143 as the actual compressor frequency [23].

### 3. How the firmware runs the compressor (start, stop, modulation)

From the Versati II and III service manuals [2][3][4]:

- **Modulation.** In leaving-water control mode, compressor frequency rises with the temperature difference and falls as it shrinks. This is effectively proportional control on (setpoint − LWT). In room control mode the same logic runs on room-temperature error [2][3].
- **Stop.**
  - If the compressor is already at minimum frequency and LWT is still well above setpoint, the unit shuts down [2][3].
  - A normal shutdown ramps the compressor to minimum frequency first. The fan and water pump stop after the compressor. The expansion valve parks fully open, then at a fixed opening [2][3].
  - **Heat run time** (Word 34) is 1–10 min, default 3 min with the heating 2-way valve off or 5 min with it on. The manual says the unit stops once this time has expired while the temperature difference stays in the "standby zone" [3][4][1]. In practice it is a minimum on-time or stop delay. The "standby zone" is not defined numerically in any text I could extract.
- **Restart.** From owner data plus the parameter definition, the unit restarts once LWT ≤ setpoint − ΔT-Heat. ΔT-Heat (Δt2) is 2–10 K, default 10 K [1][2][3][10]. Gree's own tables label it inconsistently: the Versati III and CopMax tables describe the ΔT-Heat row as a leaving-water difference for *cooling*, which looks like a copy error [3][10].
- **Timers.** The first-generation manual states that capacity is not adjusted for 6 min after start, the compressor cannot restart within at least 3 min of stopping, and the expansion valve is fixed for 3 min after start [5]. The Versati II/III manuals repeat the "stopped for three minutes" restart condition [2][3].
- **Which sensor controls.** The Versati II manual says the sensor after the auxiliary (backup) heater "mainly" controls leaving water [2]. In the R32 Modbus map this appears to be Word 126 ("T-optional water sen."), separate from the plate heat-exchanger outlet, Word 125 [1]. A 0.5–1 K offset between them could explain a measured restart at 4–5 K with ΔT-Heat = 4. Not verified.
- **Pump.** The inverter pump starts at an initial speed, then adjusts to the entering/leaving temperature difference: faster when the difference is large [2][3]. The pump stops after the compressor on shutdown [2][3]. The "Other thermal" logic text says the heat pump's pump runs during "standby status" [4][10], which suggests it circulates while the compressor is idle. Not stated outright for normal heating. Measure coil 175.

### 4. Parameter reference (user and commissioning), with Modbus words from protocol V1.5 [1]

| Parameter | Range | Default | Modbus | Notes / source |
|---|---|---|---|---|
| WOT-Heat (leaving-water setpoint, heating) | 20–60 °C (high-temp), 20–55 °C (low-temp) | 45 °C | Word 10, 1 °C resolution | Versati II: 25–55 (High) / 25–45 (Normal), default 45/35 [2]. Newer panel: up to 65 °C [9] |
| RT-Heat (room setpoint) | 18–30 °C | 20 °C | Word 12 | [1][3] |
| T-water tank | 40–80 °C | 50 °C | Word 13 | [1][3] |
| T-Eheater (outdoor temp that enables backup heater) | −20…18 °C | −15 °C (R32 doc). −7 °C on Versati II | Word 14 | [1][2] |
| T-Other switch on | −20…18 °C | −20 °C | Word 15 | [1] |
| T-HP max (heat-pump max water-out for hot water) | 40–55 °C | 50 °C | Word 16 | Commissioning setting [1][3] |
| Upper / Lower AT-Heat (curve outdoor endpoints) | 10–37 / −20…9 °C | 25 / −20 °C | Words 17 / 18 | Versati II: −22…5 for the lower point [2] |
| Upper / Lower RT-Heat (room curve) | 22–30 / 18–21 °C | 24 / 18 °C | Words 19 / 20 | [1] |
| Upper / Lower WT-Heat (curve water endpoints) | 46–60 / 20–45 °C | 55 / 40 °C | Words 21 / 22 | Versati II Normal: 30–55 / 25–29, default 35/29 [2]. NA manual with floor: 30–35 / 25–29 [7] |
| ΔT-Cool (Δt1) | 2–10 K | 5 K | Word 29 | [1] |
| **ΔT-Heat (Δt2)** | **2–10 K** | **10 K** | **Word 30** | Restart hysteresis below setpoint (owner-verified) [1][2][3] |
| ΔT-hot water (Δt3) | 2–8 K (2–25 K on newer panels) | 5 K | Word 31 | [1][3][9][10] |
| ΔT-Room temp (Δt4) | 1–5 K | 2 K | Word 32 | Room-control hysteresis [1][3] |
| Cool / Heat run time | 1–10 min | 3 (valve off) / 5 (valve on) min | Words 33 / 34 | "Standby zone" stop timer [1][3][4] |
| Other thermal logic | 1–3 | 1 | Word 35 | [1][10] |
| Tank heater logic | 1–2 | 1 | Word 36 | Logic 1: never compressor + tank heater together. Logic 2: allowed if Tset ≥ T-HP max + ΔT-hot water + 2 [8][9] |
| Optional E-heater logic | 1–2 | 1 | Word 37 | Logic 2: heat pump and backup heater together below T-Eheater [10] |
| Current limit | 0–50 A | 16 A | Word 38 | Commissioning "C/P limit" [9][10] |
| Thermostat | 0 Without / 1 Air / 2 Air+hot water | Without | Word 39 | Panels also offer "Air+hot water2" [10] |
| On/Off | 0xAA = on, 0x55 = off | off | Word 42 | [1]. Some configs see the opposite mapping [19][25] |
| **Power limit** | 0–10 kW, sent as ×10 | 3.0 kW | **Word 43** | Needs C/P limit set to "Power limit" [1][9][10][21] |
| Mode | 1 Heat, 2 hot water, 3 Cool+hot water, 4 Heat+hot water, 5 Cool | Heat | Word 2 | Changeable only when the unit is off [1] |
| Optional E-heater sets | 1 / 2 / 3 = off | 1 | Word 3 | [1] |
| Disinfection temperature | 40–70 °C | 70 °C | Word 4 | Default Saturday 23:00 [3][10] |

Read-only status words [1]:

| Word | Meaning |
|---|---|
| 117 | Unit status: 1 cool, 2 heat, 6 hot water, 8 off |
| 118 | Outdoor temperature |
| 119 | Discharge temperature |
| 120 | Defrost (coil) temperature |
| 121 | Suction temperature |
| 122, 123 | Economizer in / out |
| 124 | Discharge pressure, as °C |
| 125 | Water out at plate heat exchanger |
| 126 | Optional water sensor |
| 127 | Water in |
| 128 | Tank |
| 129 | Remote room sensor |
| 130, 131 | Gas / liquid pipe |
| 132 | Thermostat |
| 133, 134 | Floor-debug temperature / time |
| 135 | Disinfection status |
| 137 | Weather-dependent target |
| 142, 143 | Set / actual compressor frequency, Hz |

The document states "1 °C" accuracy, but community configs scale temperatures by ×0.1 and use signed values for outdoor temperature [26][25][20].

Coils (read/write state) [1]:

| Coil | Meaning |
|---|---|
| 8, 9, 10 | Weekly / clock / temperature timers |
| 17 | Control state: 0 = water-out, 1 = room |
| 18 | Fast hot water |
| 20 | Heat + hot water priority |
| 21 | Quiet mode |
| 22 | Weather-dependent mode |
| 23 | Disinfection |
| 24, 25 | Floor debug / start |
| 26 | Emergency |
| 33 | Remote sensor |
| 34 | Holiday |
| 36 | Manual defrost |

Coils (read-only states) [1]:

| Coil | Meaning |
|---|---|
| 67 | Heat-pump anti-freeze |
| 80 | Compressor |
| 81 | Outdoor fan |
| 83 | 4-way valve |
| 84 | Crankcase heater |
| 85 | Underpan heater |
| 86 | Defrosting |
| 87 | Oil return |
| 170 | Flow switch |
| 171, 172 | Indoor backup heaters 1 / 2 |
| 173 | Tank heater |
| 175 | Indoor water pump |
| 177 | Plate heater |
| 178 | 3-way valve |

**Other notes on settings:**
- The commissioning menu password on a rebadged Gree panel is **000048** [10].
- Commissioning changes are saved automatically and survive power loss [3][10].
- On Versati II, quiet mode is **not** remembered after a power failure and turns off when the unit is switched off [2].
- On Versati III, "Timer" quiet mode persists [3].

### 5. Weather-dependent ("Weather depend") curve

- **Shape.** A straight line between two endpoints: (Lower AT-Heat, Upper WT-Heat) and (Upper AT-Heat, Lower WT-Heat). An equivalent room-temperature line exists for room control [22][2][7]. The computed target is visible in Word 137 [1].
- **Behaviour.** The mode only takes effect when the unit is on, applies only to space heating and cooling (not hot water), and stays on until switched off manually. **While it is active the manual setpoint is ignored**, though the panel still accepts it [2][3].
- **Ranges differ by generation and floor setting:**

| Source | Upper WT | Lower WT | Lower AT | Upper AT | Defaults |
|---|---|---|---|---|---|
| R32 Modbus document [1] | 46–60 (high-temp) / 46–55 (low-temp) | 20–45 | −20…9 | 10–37 | 55 / 40 / −20 / 25 |
| Versati II, Normal temp (floor) [2] | 30–55 | 25–29 | −22…5 | 10–37 | 35 / 29 / −20 / 25 |
| North American Versati manual, curve figure [7] (probably floor configuration; the labels were partly lost in extraction) | 30–35 | 25–29 | −20…5 | 10–20 | — |

  One Home Assistant user runs Upper/Lower WT at **43/33 °C** with AT at 12/−12 °C [22]. That is below the R32 document's 46 °C minimum for Upper WT, so the firmware evidently accepts lower values in some configurations.
- **Implication for a slab.** The native curve has 1 °C resolution and only two points, with no room feedback. It is coarse but write-free.

### 6. Room-temperature control, remote sensor and thermostat input

- **Room control.** Control state = "T-room" is only available with Remote sensor = With, meaning Gree's wired remote room sensor [2][3][10].
  - The compressor then modulates on room error, with ΔT-Room temp (1–5 K, default 2 K) as the hysteresis [2][3][1].
  - The room temperature is a **read-only** register (Word 129) [1]. Home Assistant cannot inject a room temperature over Modbus.
  - If the remote sensor fails in room mode, the unit stops [2].
- **Holiday mode** targets 10 °C room (room control) or 30 °C water (water control) [2][3][10].
- **External thermostat** options: Without / Air / Air+hot water / Air+hot water2 [10]. In "Air+hot water" the unit can still heat hot water while the thermostat is off. "Air+hot water2" gives hot water priority when terminal CN26 sees an "OFF" dry-contact signal [10]. While the thermostat function is active, the panel's mode and on/off keys stop working, and changing the thermostat setting requires the unit to be off [2][10].
- **Implication.** A relay-driven thermostat input could give Home Assistant on/off authority **without any memory writes**. The wiring voltage and terminal for the all-in-one were not confirmed (open question).

### 7. Quiet mode, power and current limit, maximum frequency

- **Quiet mode:** lowers compressor and fan frequency, and capacity "correspondingly decreases" [2][7]. Noise falls by more than 3 dB(A) [12]. Settings are On / Off / Timer (start and end times) [3].
- **Field observation:** on a 16 kW Versati III (GRS-CQ16Pd/NhH-M, firmware V5.0.0.0), quiet mode sharply reduced fan speed, and **defrost ran about every 52 min at +2…+5 °C (about every 56 min overnight)**. Defrosts were far less frequent without quiet mode [24].
  - Mechanism (inference): less air flow means a colder evaporator, so frost builds faster in humid near-zero air.
- **Registers seen only in protocol V2.2** (forum, unverified on this unit) [23][24]:
  - Words 56/57: compressor frequency in quiet mode.
  - Words 58/59: fan speed in quiet mode.
  - Word 72: maximum compressor frequency (suggested 65–85 Hz), written with the unit off and coil 40 enabled.
  - These read 0 on at least one Versati III.
- **C/P limit:** Off / Current limit (0–50 A, default 16 A) / Power limit (0.0–10.0 kW, default 3.0 kW) [9][10][1].
  - One forum user saw Word 43 as the only register suited to grid optimization [21].
  - A cap on input power indirectly caps compressor frequency during large-error "catch-up" runs. It is a single persistent write rather than a stream.
  - Effects on hot water and defrost are undocumented (open question).

### 8. Defrost, anti-freeze and auxiliary heaters

**Defrost, first generation** [5]:
- Start: at least 50 min accumulated compressor run time **and** coil below −4 °C.
- During defrost: 4-way valve reverses, outdoor fan stops.
- End: after 10 min or when the coil exceeds 15 °C.

**Defrost, later generations** [2][3][12]:
- Marketed as "smart defrost": defrost when necessary and more when frosting is heavy.
- During defrost the 4-way valve is energized and the fan stops.

**Manual defrost:** commissioning menu, unit off, ends when the coil reaches 20 °C [8][9][10].

**Water-side anti-freeze, first generation** [5]:
- With the compressor stopped at low temperature, if the water temperature falls below 3 °C, the pump starts and the compressor follows **30 s** later. The unit runs until the outlet water is about 20 °C.
- If the heat pump has faulted, the indoor backup heaters do the anti-freeze heating.

**Anti-freeze, Versati II/III:**
- Freeze protection mainly in cooling: the compressor drops to minimum, then stops while the pump keeps running [2][3].
- The heat-pump anti-freeze state is visible as coil 67 [1].

**Other heaters:**
- Chassis heater (first generation): on when outdoor is below 0 °C and the compressor runs; off above 2 °C or when the compressor stops [5].
- Plate-heater anti-freeze heater: Gree suggests enabling it when the pump is stopped and outdoor is below 2 °C [2].
- The crankcase heater's state is visible (coil 84), but its logic and power are not documented [1].

### 9. Pump and hydraulics

**Pump:**
- An A-class inverter pump that adjusts to the entering/leaving water temperature difference [2][3].
- All-in-one indoor unit pump input about 75 W (85 W on larger sizes). The catalogue shows a "limit LPM 12", likely a minimum flow of 12 L/min (garbled table, unverified) [12].
- **No user-selectable continuous/intermittent pump mode** appears in any Versati II, III, CopMax or 2025 panel manual I read [2][3][9][10].

**Water volume (Versati III monoblock)** [4]:
- Expansion vessel 2 L for 4–8 kW, 3 L for 10–16 kW, pre-charged to 1.5 bar.
- Default total water volume 44 L or 66 L.
- **Minimum total water volume 20 L.**

**Flow switch:**
- The flow-switch trip cannot be cleared without a power cycle [2][3].
- One Home Assistant user tripped flow errors by closing 3–4 smart TRV heads. The unit uses a reed-type flow switch [20].
- For UFH, keep enough loops permanently open.

### 10. Hot water and all-in-one specifics

- **Priority.** In "Heat + hot water" mode, priority defaults to hot water on Versati III panels [3][10].
- **Fast hot water** runs the heat pump and the tank heater together. Avoid it for efficiency [2][7].
- **Setpoints and limits** [3][10][9]:
  - Tank 40–80 °C, default 50 °C.
  - ΔT-hot water 2–8 K, default 5 K (2–25 K on newer panels).
  - T-HP max 40–55 °C, default 50 °C. Above this, the electric heater finishes the job under the tank-heater logic.
- **Disinfection** [3][10]:
  - 40–70 °C, default 70 °C.
  - Weekly, by default **Saturday 23:00**.
  - Fails if the tank-heater or indoor-unit communication has an error.
  - Gives up after 10 h of accumulated operation on Versati V [11].
- **Hot-water control mode** Auto / Manual: Manual fixes the compressor frequency in hot-water mode. Only valid on "second generation Monobloc" units [9][10].
- **Efficiency.** Gree rates hot-water SCOP at 2.95 for the 8 and 10 kW split (average climate) [13]. That is well below space-heating COPs, so each hot-water cycle is expensive heat.

### 11. Floor debug (screed drying), holiday, emergency, timers and ECO

- **Floor debug** [3][9][10]:
  - 1–10 segments. First segment temperature 25–35 °C. Each segment 12–72 h. ΔT per segment 2–10 K, default 5 K.
  - The unit must be off to start it. It disables timers and other modes, and a power failure cancels it and resets the elapsed time.
  - The Versati II table has the time and ΔT columns swapped (a document error) [2].
  - Not suitable as a normal control mode.
- **Holiday** [2][3][10]:
  - Forces Heat mode at 30 °C water (or 10 °C room).
  - Disables timers and the mode/on-off keys. Needs the unit off to activate.
  - "Holiday release" is a weekly-timer day type for skipping days.
- **Emergency mode:** heating by backup heaters only, used when the compressor has failed [2][3].
- **Timers:**
  - Weekly timer: 5 periods/day on Versati II [2], 3 periods/day on Versati III [3].
  - Clock timer and Temp timer: a time-of-day water setpoint schedule, which a manual setpoint overrides [2][3][9].
  - "Preset mode" [9][10].
  - These are a native, write-free way to schedule hot-water and heating windows.
- **ECO / energy-saving / sleep modes** are claimed in Spanish distributor sheets [13][14]. **They are not documented in any Versati control-panel manual I read.** Unverified.

### 12. Modbus integration practicalities

- **Physical link.** Modbus attaches at the **wired controller (panel)**, port 1 on the back of the panel [19][22]:
  - RS485 at 9600 baud, 8N1, RTU. Slave address 1–255, but not 0 or 126 [1][19][21].
  - Use shielded cable and a 120 Ω termination to avoid CRC errors [21].
  - The panel's 12 V can power an ESP board through a converter [22][23].
- **Function codes.** Read 01/03, write 0F/10 [1]. Single-register writes (FC 06) and single-coil writes (FC 05) also work in practice [20].
- **Panel versus BMS.** BMS control is equivalent to the panel's, and the later command wins [1]. Mode changes only work while the unit is off [1].
- **Protocol versions.** At least 5–6 protocol variants exist (1.0, 1.1, 1.5, 1.7, 2.2), so addresses differ between units:
  - Early Versati II maps put outdoor temperature at 45 and water out at 50 [19][25].
  - Protocol 1.5 puts outdoor temperature at Word 118 and water out at Word 125 [1].
  - Users report 1.5 matching their Versati III and IV [26][27]. Others report mismatches [19][22][24].
  - A scanning debug mode exists in other Gree Modbus projects [search result only, not read].
- **Wi-Fi JSON alternative.** The UDP JSON protocol exposes HeWatOutTemSet (20–60 °C), WatBoxTemSet, Quiet and others, with 30 s polling in a community integration. Its parameter set does not match Modbus [23][28].
- **Reference examples:**
  - A working Versati III ESPHome configuration polls every 30 s. It exposes Words 10/12/17–22/43 as writable and 30/32/38/117–143 as sensors, plus coils 17/21/22/80/84 [26].
  - One owner's automation writes 30/34/38/42 °C water setpoints by outdoor-temperature band and turns quiet mode on 21:00–09:00 [22].

### 13. Memory wear and reaction speed

**Write handling:**
- Gree's protocol says changes to parameters with "memory function" **work immediately but will be memorized in 30 minutes** [1].
- Panel manuals say function and parameter settings are saved automatically and survive power loss [2][3][10].
- Gree publishes no endurance figure. Unknown whether the 30-min delay merges repeated writes or is a periodic save. Either way, at most about **48 stores/day (about 17.5k/year)** if each 30-min write changes the value.

**Endurance arithmetic (illustrative):**

| Memory type | Rated cycles [33] | Life at 17.5k stores/year |
|---|---|---|
| Modern EEPROM | ~1M | about 57 years |
| Flash, no wear levelling | ~10k | under 1 year |

I found no forum report of a Versati panel failing from Modbus writes. The user base is small, so this is weak evidence of absence.

**Reaction to a setpoint change:**
- The panel applies it immediately [1].
- A start still waits for the 3-min restart lockout. In the anti-freeze case the pump runs about 30 s before the compressor [5].
- The first generation holds capacity for **6 min after start** and fixes the expansion valve for 3 min [5]. Not confirmed for Versati III.
- Stopping requires the compressor to ramp to minimum frequency, plus the 1–10 min "heat run time" in the standby zone [3][2].
- One Home Assistant user reported **no response delays** to setpoint writes [20].
- Nobody has published measured frequency-response time constants. Log Words 142/143 at 5–10 s intervals to get them.

### 14. Versati-specific community and field evidence

- **Defrost under quiet mode:** described in section 7 [24].
- **Flow-switch trips** when TRV heads close; the flow switch is a reed type [20].
- **Panel register gaps:** a 12 kW Versati III split (software V6.04) shows no consumption or COP data on the panel [23]. Versati V adds energy histograms [11].
- **Distributor review (blog)** [32]:
  - Manufacturer SCOP for R32 Versati: 4.17–4.83 at 35 °C and 3.20–3.70 at 55 °C.
  - Unverified user complaints about louder defrost and "rougher" control.
  - Real-world efficiency is extrapolated from Fraunhofer's general ASHP average, not measured on a Versati.
- **heatpumpmonitor.org:** no Gree or Versati system in the first 100k characters of the public list (partial check). No public Versati field monitoring found [34].

### 15. Non-Gree context used

- **Fraunhofer ISE "WP-QS im Bestand"** (Nov 2025) [31]:
  - 61 air-source and 16 ground-source systems, measured for 4 years.
  - Air-source seasonal efficiency (JAZ) averaged **3.4 (2.6–4.9)**. Ground-source averaged 4.3 (3.6–5.4).
  - Backup heaters used only **1.3%** of air-source electricity.
  - Many units were oversized for their consumption, and some had very high switching frequencies.
  - Six PV + heat pump homes reached 25–40% self-sufficiency without a battery and **32–62% with one**.
- **Renewable Heating Hub, Midea case** [29]:
  - When output cannot modulate below the load, extra water volume lengthens cycles but does not change the on/off ratio.
  - In one 8 kW case, adding an 80 L tank plus a tank sensor turned 5–17 min runs into 2–3 h runs at 4–6 cycles/day (forum anecdote).
- **Renewable Heating Hub, 5 kW Mitsubishi UFH slab** [30]:
  - Advice: raise the flow temperature 1 K at a time to find the cycling threshold.
  - Return water rising after hours of slab heating pushes the flow to target and shuts the unit down.
  - The posters estimated that unit's minimum output at 1.9–2.4 kW.

## What this means for controlling this house

### A. The physics of the mismatch (numbers)

**Inputs:**
- Heat-loss coefficient UA ≈ 0.14 kW/K (the owner's 1.7 kW at +10 °C) up to 0.20 kW/K. Room at 22 °C.
- Minimum heat-pump output Qmin ≈ 3.75 kW.

**Where cycling is unavoidable.** Load equals Qmin at about −4.8 °C (UA 0.14) to +3.2 °C (UA 0.20). Above roughly −5…+3 °C the unit **must** cycle. That covers much of a Lithuanian heating season (autumn, spring, and the many −5…+5 °C days).

**Duty cycle:**

| Outdoor | Load | Duty (load ÷ Qmin) |
|---|---|---|
| +10 °C | 1.7 kW | ≈ 45% |
| +5 °C | 2.4–3.4 kW | ≈ 64–91% |

**What the slab can buffer.** The slab stores 6.6 kWh per K.
- At +10 °C a run charges a net 2.05 kW, a rise of 0.31 K/h. The off phase discharges 1.7 kW, a fall of 0.26 K/h.
- A 0.5 K slab swing gives about 1.6 h on + 1.9 h off, roughly **7 starts/day**.
- A 1.0 K swing gives about 3.2 h + 3.9 h, roughly **3–4 starts/day**.
- This matches the observed 0.5–4 h runs.
- **Conclusion: a few long cycles per day are physically unavoidable, and they are acceptable.** The cost does not come from the slab cycling itself.

**Where the efficiency loss actually comes from (inference from [2][3][5] plus the owner's observations):**
- (a) The start trigger must be "setpoint ≥ LWT + ΔT-Heat". With ΔT-Heat = 4, each start begins with an error of at least 4 K.
- (b) Gree's proportional-on-LWT logic turns that error into **high compressor frequency**: the ~3 kW draws at +2 °C.
- (c) High frequency raises condensing temperature and LWT, and deposits heat in a short, hot burst.
- (d) Each start pays the fixed start-up overheads: 3-min expansion-valve hold, ~6-min capacity hold [5], pump pre-run.
- (e) Hot-water cycles reach 50 °C, and space-heating flow pays 2–3% per K for the extra degrees [13].
- **Lowering average flow during runs by 4 K is worth about 8–11% of electricity** (Gree full-load data [13][14]). Avoiding high-frequency bursts likely adds more. Not quantified for Gree.

**Possible hidden cost: the pump in standby.** If the about 75 W inverter pump runs continuously while the compressor is off [4][10][12]:
- At +10 °C (≈55% off-time) it uses about 1 kWh/day.
- Total use at +10 °C is about 10 kWh/day (1.7 kW × 24 h ÷ COP 4).
- That is about 5–10% of electricity. Unverified; measure it first.

### B. Unit settings to change (one-time, persistent)

1. **Power limit.** Set C/P limit = Power limit with Word 43 ≈ 1.2–1.8 kW for days above about −3 °C. Raise it to 3–5 kW for cold spells and long hot-water reheats.
   - It caps the catch-up bursts without a stream of writes [1][9][10]. The goal is input near the minimum-modulation band, so heat output stays around 3.7–5 kW.
   - Test whether the cap slows hot water or interferes with defrost.
   - Confidence: medium (mechanism documented, effect on this unit untested).
2. **ΔT-Heat (Word 30).** Choose it together with the control approach (section C):
   - "Kick-and-ride" and thermostat or curve approaches: set it **high (6–10 K)**. The unit then never restarts itself mid-off-period, and one low write holds it off for hours. In a slab the water temperature cannot fall that far within a planned off period.
   - Continuing to drive starts purely by setpoint: drop it to **2 K** (minimum) to shrink the start kick, but then actively hold the setpoint at least 3 K below LWT during off periods.
   - Do **not** stay at 4 K by default. It has the drawbacks of both options.
   - Confidence: medium.
3. **Heat run time (Word 34): 10 min (maximum).** This gives the controller time to raise the setpoint before the unit times out in the standby zone. It also enforces at least 10-minute runs [3]. Confidence: medium. Little downside, since the observed runs are 0.5–4 h.
4. **Weather-dependent mode (coil 22).** **Off** if Home Assistant writes Word 10, because the manual setpoint is ignored while it is on [2]. **On** only for the "native curve" approach (C2). Confidence: high. This is documented behaviour.
5. **Quiet mode (coil 21): off** between −5 and +5 °C on humid days, because of the faster frosting seen on a sister unit [24]. Use the power cap for night noise instead. Confidence: medium (one well-documented field report).
6. **Backup heater.** T-Eheater (Word 14) at −20 °C, or Optional E-heater = Off (Word 3 = 3) during mild seasons. Keep Logic 1 so the heater never runs alongside the compressor [1][10].
   - Check cold-weather capacity first. The extrapolated maximum at −15 °C/W35 is 0.74 × nominal, about 7 kW [3].
   - The house needs 5.2–7.4 kW at −15 °C and 5.9–8.4 kW at −20 °C, so the backup heater or the slab must bridge the coldest days at the high-UA estimate.
   - Confidence: medium.
7. **Hot water.**
   - Tank 45–48 °C, at or below T-HP max, so the tank heater only does disinfection.
   - ΔT-hot water 8 K (or more on newer panels), giving fewer and larger reheats.
   - Schedule hot water in the warm, sunny part of the day with the weekly or clock timer, not by Modbus mode changes. Mode changes require the unit off [1].
   - Move disinfection from the Saturday 23:00 default to a sunny midday, at 60–65 °C if local rules allow.
   - Never use "Fast hot water".
   - Confidence: medium.

### C. Control approaches worth testing (the owner asked for alternatives)

All four use the same KPIs:
- kWh electric per heating degree-hour (base 22 °C, or base 18 °C with gains).
- Compressor starts/day (coil 80 transitions).
- Mean LWT while the compressor is on.
- Defrosts/day (coil 86).
- Standby electric power.
- Room temperature deviation from 22.0 °C (RMS and maximum).

Compare blocks of **2–3 days per variant** with similar mean outdoor temperature (±2 K), discarding the first day of each block because of slab carry-over.

**C1. "Kick-and-ride" setpoint control (an evolution of the current architecture).**
- Rules:
  - ΔT-Heat 6–8 K. Heat run time 10 min. Power cap as in B1.
  - Home Assistant decides **when** to run from a slab/house model, aiming for runs of at least 2–3 h and at most about 4–6 starts/day. Prefer the warmest and sunniest hours.
  - **Start:** write setpoint = round(LWT) + ΔT-Heat.
  - **Within ~1–2 min of compressor-on:** write setpoint = LWT + 1 °C ("ride").
  - **Each time LWT reaches setpoint − 0.5:** setpoint +1 °C, capped at the slab-safe ceiling.
  - **End:** setpoint = LWT − 1 °C. The unit stops after the run time, and the large ΔT-Heat keeps it off.
- Writes: about 4–8 per run, roughly 20–40/day.
- Expected: lower mean run LWT and frequency. Starts/day similar or lower.
- Risks: the 6-min capacity hold after start makes the first minutes insensitive to the ride [5]. Writes every ~10–20 min during runs (see EEPROM, section D).
- Confidence: medium.

**C2. Native curve plus power cap ("let the Gree do it").**
- Weather depend on, with a slab-appropriate line, e.g. Upper WT ≈ 32–34 °C at −20 °C and Lower WT ≈ 25–26 °C at +15 °C. Floor ranges permit this on Versati II [2] and the NA manual [7]. The R32 document may refuse Upper WT below 46 °C [1], so test acceptance.
- ΔT-Heat 4–6 K. Power cap. Heat run time 10.
- Home Assistant only shifts the two water endpoints a few times per day, e.g. +1–2 K during PV surplus and −1 K at night. At most about 6 writes/day.
- Expected: simplest and most robust. No room feedback, so expect ±0.3–0.5 K more room drift.
- Confidence: medium-low (depends on accepted ranges).

**C3. Home Assistant as thermostat (dry contact), no Modbus writes in normal operation.**
- Thermostat = Air (or Air+hot water) [10]. A relay switches the thermostat input on long calls (2–6 h).
- Fixed low WOT-Heat or a curve. ΔT-Heat 8–10 K so there are no self-restarts during a call. Power cap.
- Expected: removes the EEPROM question entirely. Cleanly separates "when" (Home Assistant) from "how" (Gree).
- Needs wiring: confirm the terminal and voltage on the all-in-one indoor board.
- Confidence: medium (documented function; electrical details unverified).

**C4. Room-control mode (T-room) with Gree's remote sensor.**
- Only possible if the Gree remote room sensor is fitted [2][10]. Home Assistant cannot feed room temperature over Modbus (Word 129 is read-only) [1].
- The unit modulates on room error with a 1–5 K hysteresis. LWT behaviour in this mode is undocumented, so it could push water hot.
- Treat it as a low-priority experiment.
- Confidence: low.

### D. What to avoid

- Writing Word 10 while weather-dependent mode is on: the write is silently ignored [2].
- Large setpoint jumps above LWT without a power cap: they command high frequency, which is the ~3 kW, high-LWT catch-up [2][3].
- Frequent Mode (Word 2) or On/Off (Word 42) toggling. Mode needs the unit off [1]. On/off memory may persist state. Each on/off adds pump and start overheads.
- Writing unchanged values, or writing more often than every 10–15 min.
  - The 1 °C register resolution makes sub-degree writes pointless.
  - Keep total memory-stored changes to roughly 48/day or fewer.
  - Ask Gree or the distributor what memory the panel uses and its rated endurance.
- Quiet mode in humid near-zero weather [24].
- Closing UFH loops through room actuators. The flow switch trips and needs a power cycle [2][3][20].
- Disinfection at night outside PV hours. Fast hot water. Tank setpoints above T-HP max [3][10].

### E. Measurements to add before and after any change (all available over Modbus [1])

- **Word 142/143** (set/actual Hz) together with electricity and heat. Gives the real minimum frequency and minimum output against outdoor temperature, and the start-up profile (is there a 6-min hold?).
- **Coils 80/86/87/175/84** (compressor / defrost / oil return / pump / crankcase heater). Give start counts, defrost intervals, oil-return events, whether the pump runs in standby, and crankcase-heater duty.
- **Words 125, 126 and 127** together (water out at plate exchanger, water after backup heater, water in). Shows which sensor the restart hysteresis uses, and the water-to-slab temperature difference at minimum output. That difference is the floor's "minimum useful LWT".
- **Word 137** if the native curve is tested. **Word 117** (status) to separate hot-water periods from space heating.

**Overall confidence:**
- High: that ΔT-Heat is the restart hysteresis (documented, owner-confirmed), that weather-dependent mode overrides manual setpoints (documented), and the direction of the LWT effect on COP (manufacturer data).
- Medium: the benefit of a power cap and of kick-and-ride.
- Low: the size of the pump-standby and memory-wear risks until measured.

## Contradictions and open questions

1. **ΔT-Heat label.** Gree's Versati III and CopMax tables call Δt2 "leaving water temperature difference **for cooling** … ΔT-Heat" [3][10]. Versati II calls it "temperature deviation for heating" [2]. The owner's data supports restart-hysteresis behaviour. Gree never states the formula in the extracted text.
2. **Default ΔT-Heat 10 K in every document versus an unexplained "standby zone".** The stop threshold above setpoint is not given numerically anywhere [3][4]. Measure it.
3. **Water ranges for the weather curve conflict:**
   - R32 Modbus document: Upper WT 46–60 °C [1].
   - Versati II Normal temp: 30–55 °C [2].
   - NA manual with floor: 30–35 °C [7].
   - A user running 43/33 °C [22].
   - Which applies to the owner's firmware has to be tested by reading and writing Words 21/22.
4. **Scaling.** The V1.5 document says 1 °C accuracy for temperature words. Community configs use ×0.1 scaling and signed outdoor temperature [1][26][25].
5. **Protocol versions.** Some users say V1.5 matches the Versati III [26][27], others say it does not [19][22]. V2.2 adds quiet-frequency and maximum-frequency registers that read 0 on a Versati III [24].
6. **Versati IV compressor.** Gree Spain says Gree's own two-stage injection compressor [14]. A German blog says Panasonic twin-rotary EVI [32].
7. **Capacity data.** The Versati III correction table implies about 9 kW maximum at −5 °C/W35 for a 10 kW unit [3]. The 10 kW split datasheet gives 6.65 kW at A−7/W35 [13]. These are different products, and the data is probably declared versus maximum.
8. **Minimum capacity and minimum frequency in heating** are unpublished. 20 Hz is the catalogue's compressor floor [12]. The real heating minimum may be higher (oil return, discharge-temperature control) and may vary with outdoor temperature.
9. **Is the 6-min post-start capacity hold [5] still present in Versati III firmware?** Unknown.
10. **Pump.** Does the internal pump run continuously in compressor-off standby during normal heating, at what speed, and can it be set to intermittent? No Versati II/III/2025 panel manual shows a pump-mode setting [2][3][9][10].
11. **The 30-min memorization rule** [1]. Debounce or periodic save? EEPROM or flash? Rated cycles? Ask the Gree distributor.
12. **Power-limit side effects.** Does the C/P power limit apply to hot water and defrost, and how fast does it act? Not documented.
13. **Thermostat input on the all-in-one** (C3). Terminal, signal voltage (some Gree inputs are 230 VAC), and whether pump behaviour changes when the call ends. Not verified.
14. **ECO / energy-saving / sleep modes** appear in distributor marketing [13][14] but in no manual I read.
15. **Missing evidence because of the search budget.** Lithuanian forums (e.g. šilumos siurblys Gree Versati), Swedish, Norwegian and Dutch forums, and UK installer blogs were not searched for Versati experiences. A follow-up search could look for Versati-specific complaints and fixes there.

## Sources

1. Modbus Protocol (V1.5) for the Versati Heat Pump Water Heater (R32). Gree Electric Appliances, hosted by kievclimate. About 2020. https://man.kievclimate.com/man/Gree/Versati/Versati%20III/R32_Versati%20Modbus%20V1.5.pdf. **Manufacturer.** Full register and coil map with ranges and defaults (ΔT-Heat Word 30, power limit Word 43, Hz Words 142/143). Notes that changes take effect immediately but are memorized after 30 min, that the last command wins, and that mode can only be changed while off.
2. Air-to-water Heat Pump Split Versati (Versati II, NaE, R410A) service manual. Gree Commercial AC R&D Dept I. March 2016. https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-ii-e-szeria/service%20manual%20gree%20en%20versati%20ii%20nae.pdf. **Manufacturer.** Proportional frequency control and shutdown at minimum frequency. Parameter tables (ΔT-Heat 2–10 K, default 10 K; run time). T-water ctrl and floor-config ranges, quiet mode, weather curve (setpoint ignored while active), holiday, floor debug, sensor roles, flow-switch lockout.
3. VERSATI III Air To Water Heat Pump service manual (compact monobloc, R32, NhG). Gree, hosted by Klimakoncept. About 2019–2020. https://www.klimakoncept.hr/upload/2-pdf-klimakoncept/4-dizalice-topline/6-gree-versati/Service-Manual-Versati-III-Compact-Mono-BlockR32-klimakoncept.pdf. **Manufacturer.** Versati III ratings and capacity-correction table, two-stage gas-injection compressor, Δt1–Δt4 table, heat-run-time and standby-zone stop rule, hot-water defaults, holiday and disinfection details.
4. VERSATI III Air To Water Heat Pump service manual (monobloc NhG/NhG1/NhG2, 139 pp). Gree, hosted by Gree Hungary. About 2021. https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iii/versati%20iii%20monoblokk%20–%20service%20manual.pdf. **Manufacturer.** Minimum water volume 20 L, expansion vessel sizes, sensor ranges, heat-run-time wording, pump running in standby ("other thermal" logic).
5. Air-to-Water Heat Pump Service Manual, Versati (T1/R410A/50Hz), first generation. Gree. About 2012. https://gree-bulgaria.com/manuals/archive/5_Versati-TSM.pdf. **Manufacturer.** Explicit timers (3-min restart lockout, 6-min capacity hold, expansion valve fixed 3 min). Defrost defaults (50 min / −4 °C / 10 min / 15 °C), anti-freeze (<3 °C, pump then compressor 30 s later), chassis-heater thresholds.
6. Versati II (2016), Unit Control chapter. Gree, hosted by kievclimate. 2016. https://man.kievclimate.com/man/Gree/Versati/Versati%20II/Versati%202016%202-f/4.Unit%20Control.pdf. **Manufacturer.** Confirms the Versati II control text and ΔT and run-time ranges.
7. GREE User Manual Versati (EN). Gree, via a North American distributor's Shopify CDN. About 2019. https://cdn.shopify.com/s/files/1/0253/4775/2018/files/GREE-USER-MANUAL-VERSATI-EN-WEB.pdf. **Manufacturer.** Weather-curve ranges with floor configured (Upper WT 30–35, Lower WT 25–29 °C), quiet mode reduces capacity, holiday setpoints, floor-debug limits.
8. Control Panel for the Compact Type Versati III, owner's manual. Gree, hosted by gree-climat.com.ua. About 2020. https://gree-climat.com.ua/pdf/Versati%20III%20%20WiFi%20eng.pdf. **Manufacturer.** Δt1–Δt4 naming, manual defrost ends at 20 °C, tank-heater Logic 2 condition. Text only partly extractable.
9. Control Panel for the Versati Air-to-water Heat Pump, owner's manual (2025 edition). Gree, hosted by gree.gr. 2025. https://gree.gr/wp-content/uploads/2025/07/600005064437-Users-manual-for-the-rest.pdf. **Manufacturer.** Newer ranges (ΔT-hot water 2–25 K, WOT-Heat up to 65 °C), C/P limit ranges, hot-water control mode (fixed compressor frequency), floor debug, quiet timer.
10. Control Panel for the Versati Air-to-water Heat Pump (CopMax High Power, EN). Gree / NH Bioservice (Danish rebadge). 2024. https://www.nhbioservice.dk/wp-content/uploads/2024/09/Panel-manual-CopMax-High-Power-engelsk.pdf. **Manufacturer.** Full function and commissioning tables (password 000048, C/P limit default 3.0 kW and 16 A), thermostat modes including Air+hot water2, other-thermal logic with pump in standby, holiday 10/30 °C.
11. Owner's manual for Versati V (wired controller, R290 monobloc). Gree, via Gree NZ. About 2025. https://www.greeac.co.nz/storage/Downloads/VersatiV/User%20Manual%20for%20Versati%20V(Wired%20Controller)%201.pdf. **Manufacturer.** Newest-generation features: compensation mode with ΔWT offset, SG/EVU input, energy histograms, water-flow feedback, disinfection 10 h cap.
12. Air to Water Heat Pump EU catalogue GC-2101-06. Gree. 2021. https://germany-gree.de/wp-content/uploads/2021/06/GREE_Air_to_water.pdf. **Manufacturer.** Versati III split and all-in-one model data (GRS-CQ10Pd/NhH-E: 9.5 kW, COP 4.59 at A7/W35), compressor 20–120 Hz (900–6600 rpm), quiet mode over 3 dB(A), pump ~75 W, backup heater.
13. Versati III Split datasheet (Spanish). Gree Products Spain, via remle.com. About 2023. https://cdn01.remle.com/IMATGES/F557/7017011.pdf. **Manufacturer.** Capacity and COP at A7/A−7 × W35/45/55 for the 8 and 10 kW units, hot-water SCOP 2.95, R32 charge, air flow.
14. Versati IV Monobloc datasheet (Spanish). Gree Products Spain, via remle.com. About 2023. https://cdn01.remle.com/IMATGES/F559/7017025.pdf. **Manufacturer.** Versati IV capacities and COPs, SCOP 35/55, seasonal efficiency ηs, two-stage injection compressor claim, outdoor range −25…+35 °C.
15. Gree Versati III Series service manual (ManualsLib preview). Gree / ManualsLib. Undated. https://www.manualslib.com/manual/1561334/Gree-Versati-Iii-Series.html. **Manufacturer.** Model codes and table of contents, other-thermal and backup-heater logic (p. 59). Limited extraction.
16. Gree Versati GRS-CQ…PdG/NhH-E owner's manual (all-in-one, ManualsLib preview). Gree / ManualsLib. Undated. https://www.manualslib.com/manual/3213163/Gree-Versati-Grs-Cq4-0pdg-Nhh-E.html. **Manufacturer.** Confirms the all-in-one 8 and 10 kW models, variable-frequency pump and water ranges.
17. Versati III split owner's manual (EN). Gree, hosted by taloon.com. About 2020. https://www.taloon.com/media/attachments/gree/OWNER_S_MANUAL_VERSATI_III_SPLIT_EN_WEB.pdf. **Manufacturer.** R32 safety and context. Most text sits in images, so it contributed little.
18. Eurovent certificate, GRS-CQ22Pd/NhA-M (Versati MAX). Eurovent Certita. Undated. https://www.eurovent-certification.com/en/catalog/program/certificate/participant/model/show/202131606. **Lab (certified).** Shows Gree's certified points (A7/W35 COP 4.50, SCOP W55 3.25) contain no minimum-capacity data. Marginal relevance.
19. "Gree Versati III Air to water heat pump", page 1. Home Assistant Community. 2022. https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916. **Forum.** At least 5–6 protocol versions, early register maps, panel port 1 wiring.
20. Same thread, page 2. Home Assistant Community. 2022–2023. https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916?page=2. **Forum.** Register list including Word 30 "delta T heat", FC 05/06 writes, no response delays, flow-switch trips with TRVs.
21. Same thread, page 3. Home Assistant Community. 2023. https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916?page=3. **Forum.** Power-limit Word 43 (×10), room setpoint Word 12, 9600 8N1, termination advice.
22. Same thread, page 4. Home Assistant Community. 2024–2025. https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916?page=4. **Forum.** Full user register table (delta heat default 10, user's WT 43/33 °C), weather curve as a two-point line, setpoint automation (30/34/38/42 °C) and night quiet mode.
23. Same thread, page 5. Home Assistant Community. 2025–2026. https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916?page=5. **Forum.** Meaning of the set/actual Hz registers, maximum-frequency register 72 (65–85), coils 22 and 86, UDP JSON integration, panel lacks consumption data.
24. Same thread, page 6. Home Assistant Community. 2026 (posts up to 6 Nov 2026). https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916?page=6. **Forum (field observation).** Quiet mode cuts fan speed and defrost occurs every ~52–56 min at +2…+5 °C. V2.2 registers 56–59 and 72 read 0 on a Versati III.
25. "ESPHome Modbus integration to GREE Thermo pump". Home Assistant Community. 2021–2024. https://community.home-assistant.io/t/esphome-modbus-integration-to-gree-thermo-pump/358997. **Forum.** Early register addresses, on/off quirks, signed-value fix.
26. koelec/EspHome-Gree, including versati_III_modbus_part.yaml. koelec, GitHub. About 2023. https://github.com/koelec/EspHome-Gree. **GitHub.** Working Versati III ESPHome register set with 30 s polling and ×0.1 temperature scaling.
27. "Gree Versati IV heat pump - Modbus connection". LogicMachine forum. 2025. https://forum.logicmachine.net/printthread.php?tid=5843. **Forum.** Versati IV answers V1.5 registers (tank Word 13, priority bit 20).
28. tomikaa87/gree-remote, issue #59. GitHub. 2023–2025. https://github.com/tomikaa87/gree-remote/issues/59. **GitHub.** Versati Wi-Fi JSON parameter names (HeWatOutTemSet, Quiet, AnFrzzRunSta, …). No curve or delta parameters.
29. "Inventor (Midea) heat pump short cycling advice". Renewable Heating Hub. 2025. https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/inventor-midea-heat-pump-short-cycling-advice. **Forum.** Volume lengthens cycles but not the on/off ratio. Example of 5–17 min runs becoming 2–3 h runs.
30. "Running ASHP efficiently, general thought process (Low and slow)", page 2. Renewable Heating Hub. 2024. https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/runing-ashp-efficiently-general-thought-process-low-and-slow/paged/2. **Forum.** Cycling diagnosis on a UFH slab, raising flow 1 K at a time, rising return water ending runs.
31. "Wärmepumpen heizen auch im Altbau klimafreundlich" (WP-QS im Bestand, press release). Fraunhofer ISE. 3 Nov 2025. https://www.ise.fraunhofer.de/content/dam/ise/de/documents/presseinformationen/2025/3025_ISE_PI_Waermepumpen-heizen-auch-im-Altbau-klimafreundlich.pdf. **Field data.** 77 systems over 4 years. Air-source seasonal efficiency 3.4 (2.6–4.9), backup heater 1.3%, oversizing and high switching frequencies, PV self-sufficiency figures.
32. "Gree Versati Wärmepumpe Test 2026". reduco.ai blog. 2026. https://reduco.ai/blog/heizung/gree-versati-waermepumpe-test. **Blog.** Manufacturer SCOP ranges for R32 Versati, generation and compressor claims, anecdotal control and defrost complaints.
33. "EEPROM". Wikipedia. Accessed 2026. https://en.wikipedia.org/wiki/EEPROM. **Reference.** Endurance about 1M cycles for modern EEPROM, about 10k for flash, retention of 10 years or more.
34. heatpumpmonitor.org public system list (JSON). OpenEnergyMonitor. 2026. https://heatpumpmonitor.org/system/list/public.json. **Field-data index.** No Gree or Versati system in the first ~100k characters checked (partial). No public Versati field monitoring found.
35. Gree Versati III hydro-box product page. Airgreen (Canada). Undated. https://airgreen.ca/en/products/thermopompe-air-eau-avec-hydro-box-gree-versati-iii-montreal-laval-longueuil-rive-sud-et-rive-nord. **Retailer.** Confirms that no minimum-capacity or turndown figure is published even in North American listings.
