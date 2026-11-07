# Gap G2: How does the Versati III/IV firmware actually behave? Specifically: the frequency gain against (setpoint − LWT); whether the 6-min post-start capacity hold and 3-min valve freeze still apply; the stop margin ('standby zone') above setpoint; what 'Heat run time' (Word 34) means; whether a lower setpoint written mid-run stops the compressor; and what the C/P power limit (Word 43) caps (input or output power, compressor only or also the backup heater, DHW and defrost) and whether it is accepted over Modbus.

> **Method note (second pass).** An earlier pass on this gap could not run any web searches; it worked only from Gree manuals already cited in notes 01–15. This pass ran 24 searches: English, Polish, German, Russian, Lithuanian, Dutch, Danish and Chinese queries, plus the suggested elektroda, HA and "standby zone" phrasings. It read 21 sources, 13 of them new to this sweep. The most useful new ones are:
> - the newest Gree Modbus map (V1.7);
> - the November 2024 revision of the Versati III monobloc service manual;
> - the Versati III R32 split service manual;
> - the Versati IV monobloc service manual (read in full for the first time);
> - a Gree Versati III training deck;
> - Gree Poland's official settings guide;
> - a Gree modular-chiller service manual, for the "standby" stop rule;
> - Cooper&Hunter (Gree OEM) controller manuals.
>
> No elektroda.pl, haustechnikdialog, Tweakers, Reddit, OpenEnergyMonitor or Lithuanian thread about Versati control internals turned up. The forum evidence is still the HA community thread and nothing else.
>
> **Bottom line:** the documents now answer *structural* questions: which parameters exist in which firmware generation, what Heat run time is, and what the power limit is meant to protect. They still give **no numbers** for the gain or the standby-zone width, and nobody publishes what Word 43 includes. Those three must be measured.

## Summary

1. **Heat run time (Word 34) has been removed from the newest Gree firmware and documents.**
   - In **Modbus V1.7**, Words 33 and 34 have no name, range or default and are marked read-only ("R / / / /"). V1.5 had them as R/W, 1–10 min, defaults 3 and 5 [1][2].
   - The **Versati IV monobloc** service manual and the **2024 CopMax/Versati panel** list only "T-HP max" in the commissioning-parameter table. Cool and Heat run time are gone [3][11].
   - **Versati III** manuals, including the **Nov 2024 revision**, still have it [4][5][6].
   - So on a newer controller, writing Word 34 may do nothing. Read it back before relying on it. Confidence: high (documents); medium on what the firmware does.
2. **What Heat run time means: it is a conditional stop delay, not a minimum run time.** Every Gree and Gree-OEM text with this parameter uses the same remark: when the time has expired "and temperature difference keeps at the standby zone, the unit will stop" [4][5][6][7][15].
   - Range 1–10 min. Default 3 min with the heating 2-way valve off, 5 min with it on.
   - No text says the compressor must run at least this long after a start.
   - The notes that call it a "minimum on-time" (01, 08) overstate the source. Confidence: high on the wording, medium on the mechanism.
3. **No Gree document gives a number for the frequency gain or the standby-zone width.** That covers Versati I 2012, II 2013/2015/2016, III 2019–2024, IV 2023 and V 2025 [3][4][5][8][9].
   - The newest texts say cooling frequency changes "in direct proportion" to (LWT − setpoint). That is a plain proportional law [3][4].
   - The heating text says frequency rises with the difference, and the unit shuts down when it is at **minimum frequency** while the difference "is still quite large" [3][4][5].
   - The gain and the zone width are firmware constants that must be measured.
4. **The 6-min post-start capacity hold and the 3-min valve freeze appear only in pre-2014 manuals.**
   - They are in the 2012 Versati I manual [8] and the **Aug 2013 Versati II (T1, GC201308)** manual. That manual still says the output capacity "will not be adjusted within 6 min" [9].
   - They are absent from every text from Oct 2015 onward: Versati II+, III monobloc 2019 and 2024, III split R32, IV monobloc [3][4][5].
   - Only the **3-min minimum off time** ("stopped for three minutes") survives, in the Versati IV text too [3].
   - Treat the 6-min hold as *not documented* for III/IV. Confidence: medium. Absence in later manuals is suggestive, not proof.
5. **The C/P limit with a "Power limit" option is a Versati III feature, not only a 2024+ one.** This corrects the earlier pass.
   - It appears as item 17 "C/P limit: Off / Current limit / Power limit" in the **Compact Versati III panel manual**, the **Versati III R32 split** service manual, the **Versati III monobloc Nov 2024** revision and the **Versati IV monobloc** manual. Current limit is 0–50 A (default 16 A) and power limit 0.0–10.0 kW (default 3.0 kW) [3][4][5][6].
   - Only the earliest Versati III panel (Dec 2019 Thermosite edition) offers just "Current Limit On/Off" [7].
6. **Gree's own training deck says what the limit is for: the electrical supply.** The deck (2020) says supply-current rules differ by country. The limit lets the unit's "maximum current" stay within the local limit [12].
   - It is therefore an **electrical input cap**, aimed at the grid connection or fuse. It is not an output (heat) cap.
   - Whether it counts the backup and tank heaters, DHW runs and defrost is still **not documented anywhere** [3][4][5][6][12]. Confidence: medium-high on input, low on scope.
7. **Word 43 (power limit, 0–10 kW, ×10, default 3 kW, R/W) is in both V1.5 and V1.7 maps. Neither map has a register or coil that selects the C/P mode** [1][2].
   - The panel text says the value can be set only when the mode is Current or Power [4][5][6].
   - So the mode must be set once on the panel (commissioning menu). After that, Word 43 should act as the runtime value.
   - No owner report of a measured effect was found in any language [16][17][18][19][20]. Confidence: medium (inferred).
8. **A lower setpoint written mid-run should cause a ramp-down, not an immediate stop.** Gree's shutdown rule is that a *normal* stop first lowers frequency to minimum. Only error or protection stops are immediate [3][4][5].
   - The heating rule stops the unit only at minimum frequency with a large error. With Heat run time present, it also needs the error to stay in the standby zone for that time [4][5].
   - Gree's modular chiller uses the same pattern with a fixed 1-min timer: it stops only after running at lowest frequency above setpoint for 1 minute [14].
   - Confidence: medium. Documented logic, never logged on a Versati.
9. **Modbus writes "work immediately but will be memorized in 30 minutes"** (V1.5 and V1.7) [1][2]. Frequent setpoint writes act at once and do not wear the EEPROM on every write.
10. **Gree Poland's official guide recommends ΔT-Heat ("permissible flow-water temperature difference") of 2–4 K.** The factory default is 10 K (range 2–10 K). The guide also suggests a 30–35 °C flow setpoint for underfloor heating and DHW ΔT 3–6 K [13].
    - So running ΔT-Heat at 2–4 K is manufacturer-sanctioned, not a hack.
11. **The backup-heater interaction with ΔT-Heat depends on the manual generation.**
    - Older Versati III monobloc and compact texts: in E-heater Logic 2 the heater may join "after the compressor has run for four minutes" when the water is ≤ WOT-Heat − Δt2 [10].
    - Newer texts (III split R32, III monobloc 2024, IV monobloc): Logic 2 lets them run together **when ambient is below T-Eheater** [3][4][5]. T-Eheater is Word 14, range −20…18 °C, **default −15 °C** [1].
    - So a small ΔT-Heat can bring in the heater only if an optional heater is wired, Logic 2 is set, and (on newer firmware) it is colder than T-Eheater.
12. **There is no usable Modbus frequency cap on Versati III.**
    - One HA user describes setting a maximum frequency (Word 72, 65–85 Hz, after enabling coil 40) from a Gree "V2.2" map [16].
    - Another user reports that the V2.2 registers (56–59, 72) always read 0 on a Versati III with firmware V5.0.0.0 [17]. V1.7 lists 45–116 as reserved [1].
    - Quiet mode remains the only documented frequency or fan cap. It brought defrosts every 52–56 min at +2…+5 °C on one 16 kW unit [17].
13. **DHW-only fixed frequency.** "Hot water control mode = Manual", with a "Running Frequency Setting", fixes the compressor frequency in DHW mode. It is valid only on "second generation Monobloc" units [3][11]. It is not in the Versati III split or compact panels [5][6].
14. **No public field log anywhere shows Word 142/143 (set and running Hz) against the setpoint error.** The registers read fine (0–100 Hz, 1 Hz steps) [1][16]. The gain, stop margin and Heat-run-time behaviour can only be settled by a logged test on this unit (plan below).

## Detailed findings

### 1. Parameter inventory by firmware generation (what exists where)

| Item | Versati I 2012 [8] | Versati II T1 Aug 2013 [9] | Versati III monobloc panel Dec 2019 [7] | Versati III compact / split R32 / monobloc Nov 2024 [4][5][6] | Versati IV monobloc [3] | CopMax / Versati panel 2024 [11] | Modbus V1.5 [2] | Modbus V1.7 [1] |
|---|---|---|---|---|---|---|---|---|
| 6-min capacity hold after start | stated | stated | — | not stated | not stated | — | — | — |
| 3-min EEV freeze after start | stated | (EEV text present) | — | not stated | not stated | — | — | — |
| 3-min minimum off | stated | stated | — | stated (freeze-protection text) | stated | — | — | — |
| Cool / Heat run time 1–10 min | — | — | yes | yes | **absent** | **absent** | Words 33/34 R/W | **Words 33/34 blank, R only** |
| ΔT-Heat 2–10 K, default 10 | — | — | yes | yes | yes | yes | Word 30 | Word 30 |
| C/P limit | — | — | Current only (On/Off) | **Off / Current / Power** | **Off / Current / Power** | Off / Current / Power | Words 38, 43 | Words 38, 43 |
| Hot water control mode (manual Hz) | — | — | — | not in split/compact | yes ("2nd-gen monobloc") | yes (same caveat) | — | — |

Read across, the firmware dropped the explicit start-up timers around 2014–2015. It added the power option to the current limit during the Versati III life cycle (2020–2022). It dropped the run-time parameters with Versati IV and the V1.7 map. **Which column this house's unit belongs to must be checked on the panel**:
- Does the commissioning page show Cool and Heat run time?
- Does C/P limit offer "Power limit"?
- What is the controller and main-board firmware (View → version)?

### 2. Compressor frequency law

- **Cooling (Versati III 2024, IV):** frequency "adjusted according to the temperature difference in direct proportion", with difference = actual LWT − setpoint [3][4]. That is a proportional law, which presumably runs between minimum and maximum frequency and inside protection limits.
- **Heating (III split, III 2024, IV):** frequency rises when the difference "goes up" and falls when it goes down. At minimum frequency with the difference "still quite large", the unit shuts down [3][4][5].
  - The sign convention is copied from cooling. Read literally, frequency would rise as the water gets *hotter* than setpoint.
  - The physical reading is: frequency rises with (setpoint − LWT), and the unit stops when (LWT − setpoint) is large while already at minimum.
  - Gree also misprints "temperature frequency" for "temperature difference" in the same sentence [3][4][5]. Do not treat the text as a precise spec.
- **Room-temperature control:** frequency follows (room − room setpoint) [3][4][5]. This house uses water control.
- **DHW:** frequency follows (tank setpoint − tank temperature) [3][4].
- **Gain:** no number in any source. The only quantitative anchor is this house: a restart at about 4–5 K error draws about 3 kW electrical at +2 °C.
  - The rated input of an 8–10 kW Versati III at A7W35 is 1.6–2.2 kW [13]. 3 kW at +2 °C is therefore near the unit's upper range.
  - So a 4–5 K error already commands high frequency: the proportional band is a few K wide (inference, low-medium confidence).

### 3. Stop logic, "standby zone" and Heat run time

- Exact remark, identical in Gree and Cooper&Hunter manuals: Heat run time is "1~10min, 3min [2-way valve Off] / 5min [2-way valve On]". When it "has expired and temperature difference keeps at the standby zone, the unit will stop". Defaults switch automatically when the 2-way-valve setting changes [4][5][6][7][15].
- **"Standby zone" is never defined numerically**, in any language version searched: English, Spanish (*zona de espera*) [7], Polish, Russian and Chinese.
- **Analogue from Gree's modular chiller** (different product, same company): in heating over-temperature protection, frequency is lowered. Compressors stop one by one "if the operation frequency has been recorded the lowest and the leaving temperature remains above the setpoint for 1 minute" [14]. That is the same two-condition pattern (minimum frequency + timer above setpoint) with a fixed 1-min timer. It suggests the Versati's Heat run time is the user-adjustable form of that timer.
- **Reading consistent with all texts:**
  1. The error axis has a zone above setpoint (LWT > setpoint by some margin) where the compressor is already at minimum frequency.
  2. A timer runs while the error stays in that zone.
  3. When the timer reaches Heat run time, the unit stops.
  4. If the error leaves the zone, the timer probably resets (undocumented).
- **Versati IV / V1.7 firmware:** with the parameter gone, the stop delay is either fixed internally or removed. Unknown.

### 4. Start / restart side

- ΔT-Heat (Δt2, Word 30): range 2–10 K, default 10 K in all generations [1][2][3][4]. Gree Poland recommends 2–4 K [13].
- Owner data (task brief): restart at setpoint − LWT ≈ 4–5 K with Word 30 = 4. This is consistent with "restart when LWT ≤ setpoint − ΔT-Heat" plus about 0.5–1 K of sensor or sampling lag.
- 3-min minimum off time: documented in all generations [3][8][9].
- 6-min hold and 3-min EEV freeze: last documented Aug 2013 [9]. Absent from 2015+ texts [3][4][5].
- Newer EEV logic (Versati III/IV): two valves for vapour injection. One is set by the ratio of high, low and injection pressures, the other by suction superheat. No start-up freeze is stated [3][4][5].

### 5. Shutdown sequence

"Normal shutdown": the compressor first lowers frequency to minimum, then stops. The EEV goes to maximum opening, then the fan stops, then the pump stops, then the EEV returns to a fixed opening. Error or protection shutdowns stop the compressor directly [3][4]. A setpoint cut is not an error, so it should take the ramp-down path.

### 6. C/P (current/power) limit

- **Panel text (III compact, III split, III monobloc 2024, IV monobloc):**
  - Item 17 "C/P limit" can be set to Off, Current limit or Power limit.
  - With Off, neither limit can be set. With Current or Power, the value can be set.
  - The setting is memorized on power failure [3][4][5][6].
- **Purpose (Gree training deck, 2020):** country rules limit the household supply current. The unit's "maximum current" can therefore be capped on the panel to stay within the local limit. The deck lists "Current/power limit" as a feature to set "according to local current limiting conditions" [12].
  - That frames it as a **supply-side (electrical input) limit**.
  - A heat-output cap would not serve that purpose.
- **Scope (heaters, DHW, defrost):** undocumented in every Gree and OEM text read [3][4][5][6][12][15].
  - The supply-current purpose implies the limit should cover everything the unit draws, i.e. including heaters it controls. But Gree's tank and optional heaters are switched by separate contactors with their own logic, and nothing says the limit sheds them.
  - Protection routines (defrost, oil return, freeze protection) usually override soft caps on such controllers.
  - Treat scope as unknown.
- **Modbus:** Word 43 power limit, R/W, 0–10 kW, ×10, default 3 kW. Word 38 current limit, R/W, 0–50 A, default 16 A. Both are in V1.5 and V1.7 [1][2]. No word or coil for the Off/Current/Power selector in either map.
- **Field evidence:** none.
  - Searched: HA (4 threads), LogicMachine (Versati IV), GitHub ESPHome projects, Polish/German/Russian/Danish/Lithuanian/Dutch forums. No one reports writing Word 43 and measuring the effect [16][17][18][19][20].

### 7. Other caps and frequency controls

- **Quiet mode** limits compressor frequency and fan speed [3][17]. On one 16 kW Versati III it brought defrost every 52–56 min at +2…+5 °C [17].
- **Max-frequency register (Word 72 + coil 40, 65–85 Hz):** from a Gree "V2.2" protocol, per one HA user [16]. It reads 0 on a Versati III (V5.0.0.0) [17], and V1.7 marks Word 72 as reserved [1]. Not usable on Versati III unless this unit's firmware differs.
- **DHW manual frequency:** second-generation monobloc only [3][11].

### 8. Write semantics and protocol versions

- Writes act immediately and are stored after 30 min [1][2]. Mode changes only with the unit off [2].
- At least 5–6 Gree Modbus protocol variants exist (V1.0 for NaE/NaD, V1.1, V1.5, V1.7, V2.2). Register meanings differ between them: a Versati II "almost nothing matches" V1.5 [19].
- Even the V1.7 file carries "V1.1" page headers [1].
- Confirm which map this unit follows. Words 33/34 returning sensible values (1–10) means V1.5-style firmware.

## What this means for controlling this house

Confidence tags: **H** = documented and consistent across generations; **M** = documented logic, not measured on a Versati; **L** = inference.

1. **First, identify the firmware column (30 min, no risk).**
   - On the panel: does the commissioning page show Heat run time, and does C/P limit offer Power?
   - Over Modbus: read Words 33, 34, 38 and 43. Write Word 34 = 10, read it back, and check it on the panel.
   - If Word 34 is blank or won't change, every rule below that relies on Heat run time is void (**H** that the parameter was removed in V1.7 and Versati IV).
2. **Keep using ΔT-Heat (Word 30) as the start-threshold knob, at 2–4 K.** This is Gree's own recommendation [13]. A smaller ΔT-Heat means a smaller error at restart, so a lower start frequency and a smaller catch-up burst (**M**).
   - Before going to 2 K, read Word 3 (optional E-heater) and Word 37 (its logic). If a heater is fitted and Logic = 2, either set Logic 1 or confirm that T-Eheater (Word 14) is at or below −15 °C [1][3][4][5] (**M-H**).
3. **When riding the setpoint during a run, keep it at or just above the current LWT (+0.5…+1 K).**
   - The documented response is: lower frequency → minimum → stop only after time in the standby zone (**M**).
   - Do not drop the setpoint more than about 1 K below LWT unless you want to end the run.
   - Do not command errors above about 3 K mid-run unless you want near-full speed (**L**, from owner data).
4. **Heat run time: if Word 34 exists, set it to 10 min.** This widens the window in which a corrective write can save a run, at a cost of ≤ 10 min × ~3.8 kW ≈ 0.6 kWh per stop. In a 6.6 kWh/K slab that is < 0.1 K (**M**).
   - Do not count it as a minimum run time. Nothing says it guarantees one (**H** on wording).
5. **Do not budget a 6-min start-up hold into the control logic** until the log (T1 below) shows one (**M**).
6. **The power limit is the most promising lever, but prove it first.**
   - Set C/P limit = Power on the panel once (installer menu).
   - Write Word 43 = 15 (1.5 kW). Measure with the hybrid inverter's CT or a DIN meter.
   - If it holds on input power, use a cap ladder: about 1.2–1.8 kW above about 0 °C, 2.5–3 kW at −5…−10 °C, and off or 5+ kW below −15 °C. The figures are illustrative and to be tuned.
   - Before leaving a low cap on permanently, test it through a DHW reheat and a defrost (**L** on scope).
   - Because it is meant as a supply-current limit [12], a cap set below what defrost needs could stretch defrosts or trip protection. Watch for errors.
7. **Avoid quiet mode as a capacity cap on humid days near 0 °C.** It is the only documented frequency cap on Versati III, but it brought ~52–56-min defrost cycles in the one field report [17] (**M**).
8. **Write cadence.** Writes act immediately and are stored after 30 min [1][2]. A 5–10 min write cadence during runs is safe for memory (**M**).

### Test plan (one quiet day; water-control heat mode; DHW off; log every 10 s)

Log Word 10 (setpoint), 125 (LWT, PHE outlet), 126 (optional sensor), 127 (return), 142 and 143 (set and running Hz), 117 (status), electrical power (external CT). Keep Word 30 = 4 unless stated.

- **T0, identification:** read Words 33, 34, 38, 43 and firmware versions. Write Word 34 = 10 and read it back.
- **T1, start profile / 6-min hold:**
  - Start with setpoint = LWT + 5. At minute 2, set the setpoint to LWT + 1.
  - If Word 142 falls within 1–2 min, there is no hold. If it stays flat to minute ~6, the hold exists.
- **T2, gain map:**
  - At steady minimum Hz, step the setpoint to LWT + 1, +2, +3 and +5 K, 10 min each.
  - Plot steady Word 142 and power against the error, and fit Hz/K and the time constant.
- **T3, Heat run time meaning (only if Word 34 exists):**
  - Word 34 = 10. At minute 15 of a run, set the setpoint to LWT − 3 K.
  - A stop about 10 min after the compressor reaches minimum Hz means a stop delay. A stop within 1–2 min means something else.
  - Repeat with Word 34 = 1.
- **T4, standby-zone edge:**
  - At minimum Hz with Word 34 = 1, lower the setpoint in 0.5 K steps below LWT, 3 min each.
  - The first step that leads to a stop marks the zone edge (expected 1–3 K; unknown).
- **T5, power limit:**
  - Set C/P = Power and Word 43 = 15, then repeat T1. Compare power and Word 143 with T1.
  - Then run a DHW reheat and wait for a defrost with the cap on. Note whether the tank or backup heater power appears above the cap.

## Contradictions and open questions

1. **Heat run time removed or not?**
   - Present: Versati III manuals up to the Nov 2024 revision [4][5][6], and V1.5 [2].
   - Absent: Versati IV monobloc [3], the 2024 panel manual [11], and V1.7 (blank) [1].
   - Open: what replaced it (a fixed internal timer?), and which firmware this unit runs.
2. **Heat run time meaning.**
   - Notes 01 and 08 say "minimum on-time or stop delay". Note 12 says "stop timer". All primary texts support only a conditional stop delay [4][5][6][7][15].
   - Open: does the timer reset when the error leaves the zone, and does it start only at minimum Hz?
3. **Heat run time default.** The panel says 3 min (2-way valve off) or 5 min (on) [4][5][6]. V1.5 says 5 min [2]. A 2016 Versati II table says 3 min with FCU/radiator and 5 min without (from the earlier pass). Read the actual value.
4. **When the power limit arrived.** The earlier pass dated it to 2024–25 panels. This pass finds it in Versati III compact, split R32 and monobloc manuals [4][5][6], but not in the Dec 2019 III panel [7]. Earlier Versati III units may have current limit only.
5. **Power limit scope** (input vs output; heaters, DHW, defrost, oil return; how fast it acts). Gree frames it as a supply-current protection [12], which points to input. Nothing states the scope. **Unresolved.**
6. **Is Word 43 honoured when only the value is written over Modbus?** Presumably yes once the panel mode is Power. No one has reported it [16]–[20].
7. **Optional E-heater Logic 2 trigger.** The older compact and monobloc texts say after 4 min of compressor run with water ≤ WOT − Δt2 [10]. Newer texts say when ambient < T-Eheater [3][4][5]. Different firmware likely behaves differently. Check which applies before shrinking ΔT-Heat.
8. **Gain and standby-zone width.** Unpublished in every generation and language searched. Must be measured (T2, T4).
9. **Sensor used for the start and stop logic:** Word 125 (PHE outlet) vs Word 126 (after the optional heater). Over-temperature protection explicitly uses the heater-outlet sensor [3][4]. The compressor law says only "leaving water temperature".
10. **Max-frequency register (Word 72).** Reported from a V2.2 map [16] but reads 0 on Versati III [17]. Possibly valid on Versati IV or newer boards. Untested.
11. **Search coverage.** No independent installer write-up on Versati control internals exists in any language searched. Some Danish and Dutch distributor PDFs were reachable only as HTML stubs. The kievclimate folder "Versati III split" (updated Aug 2025) and Gree "Modbus V2.2" were not obtained.

## Sources

1. Modbus Protocol (V1.7) for the Versati Heat Pump Water Heater - Gree Electric Appliances (hosted by Gree Italia/Argo) - c. 2022 - https://www.greeitalia.it/WebDocTec/Documents/MDB//Modbus%20Protocol%20VERSATI%20III%20(V1.7).pdf - manufacturer - Newest map: Words 33/34 (run times) blank and read-only; Words 38/43 current and power limit R/W; Word 14 T-Eheater −20…18 °C default −15 °C; Words 142/143 Hz; "work immediately, memorized in 30 minutes"; no C/P-mode register.
2. Modbus Protocol (V1.5) for the Versati Heat Pump Water Heater (R32) - Gree (hosted by kievclimate) - 2020 - https://man.kievclimate.com/man/Gree/Versati/Versati%20III/R32_Versati%20Modbus%20V1.5.pdf - manufacturer - Words 33/34 Cool/Heat run time 1–10 min (defaults 3/5); Word 43 power limit; write semantics; mode only when off.
3. Versati IV Monobloc Type Air-to-water Heat Pump Service Manual - Gree - c. 2023 - copy obtained earlier in this research sweep; also listed at https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iv/ - manufacturer - Proportional compressor law; shutdown ramp to minimum; 3-min off; commissioning table without run times; C/P limit with Power option; Logic 2 heater tied to T-Eheater; DHW manual frequency on 2nd-gen monobloc.
4. VERSATI III Monobloc Type Air-to-water Heat Pump Service Manual (revision 2024-11) - Gree (hosted by klima-gree.hu) - 2024 - https://klima-gree.hu/product_images/5398/versati-iii--monoblokk---service-manual---aktualis--2024-11-.pdf - manufacturer - Still has Heat run time and "standby zone" remark; C/P limit with Power option; "direct proportion" wording; Logic 2 tied to T-Eheater.
5. Service Manual VERSATI III Split Type Air To Water Heat Pump (R32) - Gree (hosted by Argo) - c. 2021–2023 - https://service.argoonline.it/area_riservata/WebDocTec/Documents/SER/Service%20Manual%20for%20VERSATI%20R32%20SPLIT.pdf - manufacturer - Same heating law and stop rule; Heat run time; C/P limit with Power option; no 6-min hold.
6. Control Panel for the Compact Type Versati III, Owner's Manual - Gree (hosted by Gree Climat UA) - c. 2020 - https://gree-climat.com.ua/pdf/Versati%20III%20%20WiFi%20eng.pdf - manufacturer - Item 17 C/P limit Off/Current/Power with ranges; §2.4.14 setting rules; Heat run time "standby zone" remark.
7. Operation Instructions for Versati III (control panel, EN/ES) - Gree via Thermosite - Dec 2019 - https://thermosite.com/docs/manual-utilizador/20191216_MU_VERSATI_MB.pdf - manufacturer - Earliest Versati III panel: "Current Limit On/Off" only; Heat run time remark in English and Spanish (*zona de espera*).
8. Air-to-Water Heat Pump Service Manual, Versati (T1/R410A/50Hz) - Gree - c. 2012 - https://gree-bulgaria.com/manuals/archive/5_Versati-TSM.pdf - manufacturer - Original source of the 6-min capacity hold, 3-min restart, 3-min EEV freeze (from the earlier pass).
9. Air to Water Heat Pump Service Manual Versati T1/R410A/50Hz (GC201308-II), Versati II - Gree - Aug 2013 - https://gree-bulgaria.com/manuals/archive/140_VERSATI_II_TSM_%202013_8.pdf - manufacturer - Shows the 6-min hold and 3-min restart still stated in 2013, dating the removal to 2014–2015.
10. Service Manual Versati III Compact Mono-Block R32 - Gree (hosted by Klimakoncept) - c. 2021 - https://www.klimakoncept.hr/upload/2-pdf-klimakoncept/4-dizalice-topline/6-gree-versati/Service-Manual-Versati-III-Compact-Mono-BlockR32-klimakoncept.pdf - manufacturer - Older Logic 2 rule: heater joins after 4 min of compressor run if water ≤ WOT-Heat − Δt2.
11. Control Panel for the Versati Air-to-water Heat Pump (CopMax High Power, EN) - Gree / NH Bioservice - 2024 - https://www.nhbioservice.dk/wp-content/uploads/2024/09/Panel-manual-CopMax-High-Power-engelsk.pdf - manufacturer - Commissioning table lists only T-HP max (no run times); C/P limit; Hot water control mode Manual (2nd-gen monobloc only).
12. PPT for VERSATI 3 (training presentation) - Gree (hosted by kievclimate) - 2020 - https://man.kievclimate.com/man/Gree/Versati/Versati%20III/PPT%20for%20VERSATI%203.ppt - manufacturer - States the current/power limit exists to keep the unit's maximum current within local supply regulations, i.e. an input-side limit.
13. Skrócona instrukcja eksploatacji pompy ciepła GREE Versati - Gree Polska - 2024 - https://gree.pl/content/uploads/2024/04/skrocona-instrukcja-eksploatacji-pompy-ciepla-gree-versati.pdf - manufacturer (distributor) - Recommended ΔT-Heat 2–4 K, DHW ΔT 3–6 K, UFH flow 30–35 °C; rated inputs of Versati III (1.6–2.2 kW for 8–10 kW at A7W35).
14. Service Manual, A-series modular air-cooled chiller (heat pump), R32 - Gree (hosted by Gree Italia) - 2022 - https://greeitalia.it/WebDocTec/Documents/SER//service%20manual%20R32%20modular%20chiller_2022.pdf - manufacturer (analogous product) - Gree stop pattern: at lowest frequency with LWT above setpoint for 1 min, compressors stop one by one.
15. Owner's manual, Air-to-water Heat Pump controller (R32), Cooper&Hunter (Gree OEM) - Cooper&Hunter Poland - c. 2021 - https://cooperhunter.pl/storage/files/2022/01/9ngzKL6RLfDgPbn70V15urY6f/instrukcja-obslugi-sterownika-r32-en.pdf - manufacturer (OEM) - Identical Heat run time "standby zone" remark and defaults; confirms the text is generic Gree controller firmware.
16. Gree Versati III Air to water heat pump, post #96 and page 5 - Home Assistant Community (pranelio, palos, Cayman) - Jan 2026 - https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916/96 - forum - Word 142 = commanded Hz, 143 = running Hz; claimed Word 72 max-frequency cap (65–85 Hz) via coil 40 from a V2.2 map; no test results.
17. Gree Versati III Air to water heat pump, page 6 - Home Assistant Community (JKF1, pranelio) - Nov 2026 - https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916?page=6 - forum (field observation) - V2.2 registers 56–59/72 read 0 on Versati III V5.0.0.0; quiet-mode defrost every 52–56 min at +2…+5 °C.
18. Gree versati 3 integration - Home Assistant Community (sarunasr, FabioPace) - 2026 - https://community.home-assistant.io/t/gree-versati-3-integration/991745 - forum - WiFi/UDP setpoint writes ignored in room control or weather-curve mode; work in water control; no limit or Hz access.
19. Gree Versati III Air to water heat pump, page 1 - Home Assistant Community (pug, agisofttm, Gerwazy) - 2022 - https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916 - forum - 5–6 Gree Modbus protocol variants; register maps differ by generation.
20. Gree Versati IV heat pump - Modbus connection - LogicMachine Forum - 2025 - https://forum.logicmachine.net/printthread.php?tid=5843 - forum - Versati IV reads with the V1.5 map (holding register 13, coils as bits); no limit or Hz data.
21. Versati Air-to-water Split Heat Pump Owner's Manual (Versati IV, NhH3) - Gree via Vėdinimo ekspertai (LT) - 2024 - https://vedinimoekspertai.lt/wp-content/uploads/2024/09/Gree-Versati-IV-NAUDOTOJO-INSTRUKCIJA-anglu-kalba.pdf - manufacturer - Commissioning parameters are installer-only ("contact the equipment manufacturer"); oil-return status shown; no control constants.
