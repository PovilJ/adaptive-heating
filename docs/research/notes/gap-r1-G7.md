# Gap G7: For the Versati III, what starts a defrost (time, coil temperature, suction pressure, and whether the runtime counter resets on stop)? Does a lower compressor speed or a power cap, with the fan unchanged, reduce defrost frequency at 0 to +4 °C and RH above 85 %? What does a defrost cost in Lithuanian conditions?

> Follow-up to note 09 (defrost). Written 2026-11-06.
>
> **How this note was produced.** This version adds a web research pass to an earlier offline version of this note. The offline version had no web access; it analysed minute-level heatpumpmonitor.org data and Kaunas climate data, and its quantitative results are kept here as sources [20]-[22].
>
> **New in this pass:**
> - 27 web searches (English, German, Polish, Swedish, Dutch, Lithuanian);
> - 18 sources read in full or at page level;
> - two primary documents read in full text: **Kropas' 2026 VILNIUS TECH PhD thesis** [5] (the full Lithuanian frost/defrost study) and **Liu's 2023 PolyU PhD thesis** [7] (compressor-speed × fan-speed frosting maps);
> - a Gree service manual that spells out the timer-reset rule [3].
>
> I did not read the repository's code or docs outside docs/research/notes/.

## Summary

1. **On Gree firmware, a compressor stop does not reset the defrost run-time counter (high confidence).**
   - A Gree inverter service manual spells it out [3]: the accumulated heating time is cleared only when outdoor air rises above +5 °C (41 °F), on a switch to cooling/dry, or when a defrost ends. It is explicitly **not** cleared when the unit stops at setpoint, on a protection stop, or in fan mode.
   - Gree's Versati I and II manuals use the same "accumulative running time of compressor" wording [2].
   - Measured on a Gree outdoor unit: defrosts came a median **16 min after a restart**, and 99 % of intervals contained stops [20].
2. **What Gree documents as the Versati defrost entry and exit, and how the Versati III differs.**
   - Entry (Versati I and II): accumulated compressor run time > **50 min** (settable 30-60) **and** coil ("defrost") sensor < **−4 °C** (settable −10…0).
   - Exit: **10 min** or coil > **15 °C** [2].
   - The Versati III manual gives no numbers [1]. It says the coil sensor "mainly" controls defrost, and the **suction-pressure sensor** is also used "to control defrosting". It describes the logic as adaptive: "defrost more when it frosts heavily; defrost less when it frosts lightly".
   - None of these parameters are in the Versati III menus.
3. **Gree's newer logic has two clocks and a coil threshold that depends on outdoor temperature** [3]. Defrost is allowed after **45 min of continuous heating or 90 min of accumulated heating**, and only if the coil is cold enough:
   - **≤ −6 °C** coil at −2…+5 °C outdoor;
   - **≤ −2 °C** above +5 °C;
   - **≤ −8 °C** at −5…−2 °C;
   - below −5 °C, **coil ≤ outdoor − 3 K** (with a 3 K compensation after a "cold" defrost exit).

   This is a sister Gree product (a split), not the Versati III. Note the gap between this and the measured ~55-60 min Gree floor [20].
4. **The coil threshold, not the clock, is the lever an external controller can move (medium confidence).**
   - Every Gree variant needs the clock **and** a cold coil [2][3].
   - On a Versati III in quiet mode (slow fan), defrost fired every **52-56 min at +2…+5 °C**, which is the clock floor. Without quiet mode, defrosts were far less frequent [4].
5. **Lower compressor speed at a FIXED fan speed does warm the coil, but at 0…+2 °C and RH ≥ 84 % this delays frost rather than avoiding it** [7]. Lab measurements on a variable-speed ASHP (20-80 Hz × 25-100 % fan):
   - Coil temperature rises as compressor speed falls **or** fan speed rises.
   - At **7 °C / 87 % RH**, the same 9.1 kW of output was delivered three ways:
     - 50 Hz + 100 % fan: coil **+2.4 °C**, no frost for 4 h, COP **4.36**;
     - 60 Hz + 55 % fan: frost after about 1 h, coil fully blocked at 2.7 h, COP 4.09;
     - 65 Hz + 25 % fan: blocked in **58 min**, COP **3.58**.
   - At the standard frosting point **2 °C / 84 % RH**, the dew point is below 0 °C and **almost every speed combination frosted** [7].
6. **The best lab evidence for "low power at 0…+4 °C" is about 2.4× fewer defrosts, not zero, and it needed a faster fan too** [7].
   - Test: 2 °C / 84 % RH, a 5.5 kW load held for 24 h.
   - Baseline 50 Hz + 70 % fan: **22 defrosts per day**.
   - 40 Hz + 100 % fan: **9 per day** (−59 %). Daily defrost energy fell 32 % and daily COP was unchanged (3.32).
   - Wei et al. report the same direction: no frost at 0 °C / 80 % RH at low load [23]. But Lithuanian 0…+4 °C hours have a median RH of 88-90 % [22], which is above Wei's 80.6 % critical RH at +1 °C.
7. **No source tested a compressor-only cap with the fan held constant on a unit whose fan follows suction pressure, as the Versati III's does** [1].
   - A lower compressor speed raises suction pressure. The Gree fan law may then slow the fan, which gives back part of the coil-warming effect.
   - Field data (15 UK/Canadian systems, −3…+5 °C): the lower-power half of runs had a median **0.91×** the defrosts per kWh of heat, with a best case of 0.67×. The Gree unit was **1.10×**: no benefit, because its clock dominates [21].
8. **Lithuanian field data: defrost about every 51 min at about 0 °C and 90 % RH** [5]. A Panasonic 7 kW unit at VILNIUS TECH, run at 50/45 °C water, Oct 2020 to Mar 2021, 1-min logging:
   - 15-17 Dec 2020 (−2…+3.7 °C): **54 defrosts in about 46 h = 1.17 per hour**;
   - 11-12 Nov 2020 (mean +4.0 °C, 85.8 % RH): **0.52 per hour**;
   - frost onset **below 3.5 °C and above 85 % RH**;
   - defrost length a constant **5 min**;
   - about **2.59 kg of frost (0.37 kg per kW)** builds up per cycle.
9. **Measured cost of defrosting in Vilnius** [5]. Hours that contained defrosts had **12 % lower average hourly COP** than frost-free hours, and up to 21 % lower between periods.
   - Simulation of a typical Vilnius year: **1,364 defrosts per season (0.27 per heating-season hour)** at 50 °C water, against **1,006 (−26 %)** at 35 °C water.
   - Defrost cut seasonal performance factor (SPF) by **up to 3.9 %** in that model. The model assumed COP = 1 for the 5 min of defrost and ignored the recovery ramp, so this is a floor.
10. **Per-event cost, measured** [14][15][20][21]: median **about 0.16 kWh_el** per defrost on 15 field systems; 0.18 kWh_el on the Gree; about 0.11 kWh_el on a Samsung; 0.4-0.6 kWh_el on 12-16 kW R290 units with 14-min defrosts. A defrost on a UFH slab draws about 0.3-0.8 kWh of heat back out of the water.
11. **Best estimate for this house: about 4-8 % of heating electricity (central about 5-6 %), roughly 1,000-2,000 defrosts and 150-400 kWh_el per season, about €30-100.**
    - Evidence: the thesis SPF hit of at least 3.9 % [5], the 6-7 % from field-data mapping [21][22], the Dutch 1,900 events per year for a 60-min timer [11], and per-event costs [10].
    - This slightly narrows the earlier 3-8 % / 4-11 % ranges. Confidence: medium-low.
12. **Timer defrost wastes events: about a third or more fire when frost does not need it.**
    - In field tests, a time-temperature method fired **31 defrosts in 24 h under non-frosting conditions**, and **37 %** of its defrosts were unnecessary in variable weather. A humidity-aware method fired none [8].
    - A Dutch study [11]: with a 60-min timer, about **1,900** defrosts per year are expected; a frost-mass model says about **900** are actually needed. This is the room an external controller can only reach by keeping the coil above Gree's entry threshold.
13. **Water temperature matters too.** Lowering supply water from 50 to 35 °C cut modelled defrosts by **26 %** in Vilnius [5]. UK owners report fewer defrosts after cutting flow temperature and compressor rate (anecdote) [16].
14. **Quiet mode is the one setting known to make Versati III defrost worse** [4], consistent with fan-speed physics [7]. On Versati III firmware, the max-frequency register (word 72) and the quiet-mode compressor and fan registers (words 56-59) read 0. The C/P power limit is the only power lever (note 08).

## Detailed findings

### 1. What starts a Gree defrost

**1a. Documented Gree logic, by generation**

| Item | Versati I/II (R410A) [2] | Gree inverter split ("Neo", sister firmware) [3] | Versati III Monoblock R32 [1] |
|---|---|---|---|
| Clock | Accumulated compressor run > 50 min (30-60) | Continuous heating > 45 min **or** accumulated heating > 90 min; separately, 3 h accumulated + coil < −17.8 °C for 1 min | Not stated |
| Coil gate | Coil < −4 °C (−10…0) | −2…+5 °C: coil ≤ −6 °C; > +5 °C: ≤ −2 °C; −5…−2 °C: ≤ −8 °C; < −5 °C: coil ≤ T_out − 3 K (− compensation) | Coil sensor "mainly used to control defrosting" |
| Pressure | No | No | Low-pressure sensor used "to control defrosting, freeze protection and superheat" |
| Clock reset | Not stated ("accumulative") | Cleared only by: T_out > +5 °C, cooling/dry start, end of defrost. **Not** cleared by setpoint stops, protection stops or fan mode | Not stated |
| Other | — | Defrost lockout of 2 h if the compressor ran < 3 min; defrost at 85 Hz; ends at 7.5 min or coil ≥ +10 °C; compensation +3 K if the last exit was at coil ≤ +2 °C | Manual defrost ends at coil 20 °C or 10 min; fan follows suction pressure |
| Exit | 10 min (1-15) or coil > 15 °C (5-30) | 450 s or coil ≥ 10 °C | Not stated (manual: 20 °C / 10 min) |

- **Reading across generations.** The Versati III wording ("smart", "defrost less when it frosts lightly") and the field signature below fit a logic in which:
  - a run-time clock sets a floor;
  - a coil gate (perhaps backed up by suction pressure) decides whether to defrost when the floor is reached;
  - the exit temperature or duration of the last defrost lengthens or shortens the next interval (as in the 3 K compensation in [3]).

  This is inference from sister products. Gree has published no Versati III table.
- **Other brands use the same pattern, which supports the "stop does not reset" reading.**
  - Fujitsu [13]: an integrating compressor timer (22/35/62 min windows with coil gates of −9/−5/−10 °C), plus an "integrating defrost" after 240 min of running at coil < −3 °C. Repeated runs under 10 min add to an **OFF count; 40 short runs force a defrost**. The count resets only after a defrost.
  - Generic US time-temperature boards accumulate run time **only while the coil sensor is cold**, and reset after a defrost (search-level evidence, not read in full).
  - So short-cycling can even *trigger* defrost on some brands.

**1b. Field evidence that Gree's counter survives stops** (from the offline analysis [20])

- Unit and data: Gree Flexx 7 kW outdoor unit, Ottawa, 679 defrosts, Dec 2024 to Mar 2025, 15-s data.
- Accumulated compressor run time between defrosts:
  - **never < 55 min**;
  - peak at 60-70 min;
  - second peak at about 120 min.
- At −7…+5 °C:
  - median continuous run before a defrost: **16 min**;
  - 63 % of defrosts came within 20 min of a restart;
  - 99 % of intervals contained stops.
- The empty first about 10 min of each run matches the Neo's "≥ 3 min run / coil cold for 1 min" style of gating [3].
- Versati III cross-check: 52-56-min cadence in quiet mode [4], the same floor.
- **Answer.** The counter is cumulative across thermostat stops. Expect the first defrost of a new run 10-20 min after the start if the previous runs already used up the floor. Whether the clock only accumulates while the coil is cold (Trane-style) is not documented for Gree.

**1c. Role of suction pressure**

- On the Versati III, suction pressure sets the outdoor fan speed in heating [1] and is "used to control defrosting".
- Frost blocks airflow, which lowers suction pressure. That is a standard demand signal; the review in [8] uses a ~20 % rise in suction-discharge temperature difference at defrost start.
- No Gree threshold is published. An external controller cannot read the fan speed on Versati III [4], so it cannot reconstruct this loop.

### 2. Does lower compressor speed or a power cap reduce defrosts at 0…+4 °C, RH > 85 %?

**2a. Lab: compressor × fan maps** (Liu, PolyU PhD 2023 [7])

- **Rig.** Variable-speed ASHP in an environmental chamber; compressor 20-80 Hz; fan 25-100 % (0.53-1.57 m³/s); 42 combinations at each of three conditions:
  - 7 °C / 86.8 % RH;
  - 4.5 °C / 78.4 % RH;
  - 2 °C / 83.9 % RH.
- **Coil temperature rises when compressor speed falls (fan fixed) or fan speed rises.** The fan effect is stronger at high compressor speed.
- Frost-free operation was possible at 7 °C only on the low-speed / high-fan side of the map. At 4.5 °C / 78 % the dew point is +1.1 °C, so the "wet but not frosting" band is tiny.
- At 2 °C / 84 % there is no condensing region at all: most operating points frost.
- **Same output, different frost** (7 °C, 9.1 kW):

| Compressor + fan | Frost-free time | COP |
|---|---|---|
| 50 Hz + 100 % fan | > 4 h (stopped manually; coil steady at +2.4 °C) | 4.36 |
| 60 Hz + 55 % fan | about 1 h; blocked at 2.7 h | 4.09 |
| 65 Hz + 25 % fan | coil −2…−3 °C at once; blocked at 58 min | 3.58 |

- **Frost-suppression control at 2 °C / 84 %, 24 h, 5.5 kW load:**
  - baseline 50 Hz + 70 % fan: 22 defrosts, 119.6 min defrosting, 8.61 MJ (2.4 kWh) defrost energy;
  - map-based 40 Hz + 100 % fan: **9 defrosts, 76.2 min, 5.89 MJ**;
  - same daily COP (3.32), heat output within 1.4 %.

  Defrost was started at a coil temperature of −15 °C, which is demand-like. So fewer, larger frost loads per event; that is how a coil-gated Gree would also respond.
- **Implication.** At 0…+4 °C and humid air, slowing the compressor *and* keeping the fan fast stretches frost-free time by up to 2.6× (+158 % heating time per cycle). It does not remove defrost. Fan speed is at least as important as compressor speed.

**2b. Field and lab: variable frequency vs fixed speed** (Wu et al. 2023, JOBE, abstract-level [9])

- Two near-identical ASHPs in North China, one variable-frequency, one fixed-speed.
- Over a season, the variable-frequency unit had longer frost-free periods. Its defrost time at −10…+12 °C was **26 %** of the fixed unit's, and overall performance was about 4 % higher (about 9 % including frost-free benefits).
- This supports "modulate down rather than cycle at full speed". It does not isolate a cap at fixed fan speed.

**2c. Field: power split in UK/Canadian data** (offline analysis [21])

- Defrosts per kWh of heat, low vs high power half, within 1 K bins at −3…+5 °C:
  - median **0.91×**; 11 of 15 systems below 1;
  - strongest at +2…+4 °C (Aquarea J: 0.55-0.75 vs 1.7-2.1 defrosts per 10 kWh);
  - the **Gree Flexx 1.10×** (clock-bound).
- Upper bound, because frost itself pushes power up (reverse causation). RH is not observed.

**2d. Literature and community**

- Wei et al. [23]: load-aware frosting map; no frost at 0 °C / 80 % at low load; critical RH 80.6 % at +1 °C.
- Owners report fewer defrosts after lowering flow temperature or compressor rate (Grant Aerona 3, Samsung Gen6) [16]. No counts.
- Swiss and Austrian forums: "quiet mode slows the fan and ices the fins" [18]. One brand starts defrost only when air-in to suction ΔT > 10 K [18], which is exactly the approach a cap shrinks.
- The Dutch HPLaunch model puts evaporator temperature at about **1.16·T_out − 6.4 °C** [11]. That is about −4 °C at +2 °C outdoor, right at Gree's −4 °C default gate. So a modest rise in coil temperature (+1…+3 K from a lower load) could keep the gate shut for longer.

**2e. Answer for the Versati III**

- Physics and lab data say yes: lower compressor speed at the same fan speed warms the coil. At 0…+4 °C, RH > 85 %, it **delays** frost; it does not avoid it. On a coil-gated unit this should stretch intervals beyond the 50-60-min clock floor.
- Two unknowns could cancel it on Gree:
  1. the fan may slow with suction pressure;
  2. the clock floor may dominate.

  The one Gree dataset [21] showed no benefit.
- Net: **plausible 0-40 % fewer defrosts per kWh at +1…+4 °C, unproven on this unit; little effect below 0 °C.** Must be measured.

### 3. What a defrost costs in Lithuanian conditions

**3a. Lithuanian measurements and model** (Kropas, VILNIUS TECH PhD 2026 [5]; Energies 2021 [6])

- **Unit.** Panasonic WH-UD07HE5-1 (7 kW at A7/W35; 6.55 kW, COP 3.34 at A2/W35; R410A; 46 m³/min airflow), with a buffer tank, run at 50/45 °C, Oct 2020 to Mar 2021.
- **Measured:**
  - frost onset below 3.5 °C and above 85 % RH;
  - defrost length a constant 5 min;
  - highest defrost frequency at about 0 °C and > 90 % RH;
  - 1.17 defrosts per hour at −2…+3.7 °C;
  - 0.52 per hour at +4 °C / 86 %;
  - during frost-defrost periods: average 0.06 °C and 91.7 % RH;
  - hours with defrost had 12 % lower COP; exergy efficiency fell 14 %;
  - fan airflow rose as the coil iced, to hold output.
- **Model** (TRNSYS, typical-year data, 5,088-h season, frost-mass trigger 0.37 kg per kW, COP 1 during defrost):

| | Vilnius | Kajaani | Berlin |
|---|---|---|---|
| Season mean T / RH | 0.45 °C / 85.8 % | −3.7 °C / 85.7 % | 5.3 °C / 80.9 % |
| Defrosts per season | 1,364 | 1,484 | 808 |
| Defrosts per hour | 0.27 | 0.29 | 0.16 |

  - In Vilnius, 35 °C water instead of 50 °C gave 1,006 defrosts (−26 %) and +32 % SPF.
  - SPF loss from defrost: up to 3.9 %.
- **Caveats** (stated by the author): one product, buffered system, high water temperature. The mass criterion needs validation for other units.

**3b. Per-event energy**

| Source | Unit | Per event |
|---|---|---|
| Field, 15 systems, −3…+5 °C [21] | various 5-12 kW | median 0.16 kWh_el (0.05-0.41) |
| Gree Flexx [20] | 7 kW | 0.30 kWh heat back + 0.08 kWh_el = 0.18 kWh_el |
| Samsung [15] | 8 kW | 0.57 kWh heat from house; under 5 min; compressor 50 Hz during defrost |
| Vaillant Arotherm+ 12 kW [14] | 0.6 °C, 36 °C flow, 14 min | 0.14 kWh_el + 0.76 kWh heat back → about 0.39 kWh_el |
| Viessmann 150-A 16 kW [14] | internal buffer | about 0.6 kWh_el |
| PolyU lab [7] | 2 °C / 84 % | about 0.11 kWh per event (2.4 kWh / 22) |
| Kropas model [5] | 5 min at COP 1 | about 0.15-0.3 kWh_el for a 7 kW unit |

- Plus recovery: on the Gree, electric input was +18 % for about 10 min after a defrost [20].

**3c. Seasonal estimate for this house**

- **Count:** thesis 0.20-0.27 per heating-season hour → 1,000-1,400 per season [5]; HPLaunch NL 60-min timer 1,912 per year, physical need about 900 [11]; offline Gree-clock model 1,300-2,000 [21][22].
- **Cost:** × 0.13-0.2 kWh_el → **about 150-400 kWh_el**. Against roughly 3,700-5,500 kWh of heating electricity, that is **about 4-8 %**; central about 5-6 %.
- **Cross-checks:**
  - Kropas SPF floor 3.9 % [5];
  - field reverse-heat mapping 6-7 % [21][22];
  - Trystan Lea's UK estimate of about 2-3 % of heat [17], for a milder climate;
  - Heat Geek's 9.2 % over a 36-h cold, humid window [17].
- **Climate:** Kaunas has about 1,040 h per season at 0…+4 °C with RH > 85 %, which is about 31 % of heat demand [22]. This is where most of the cost sits.
- **Money:** €30-100 per season at €0.20-0.25 per kWh.
- **Milev et al.** [10]: simulation over 10 cities; strong negative correlation of defrost count with temperature (r = −0.94). Season totals from 56 (Vancouver) to 1,070 (Harbin). Full text not read; per-city kWh not available.

### 4. Context: timer defrost wastes events

- Zhu et al. (field, 2 seasons) [8]: at non-frosting conditions, time-temperature control started **31 defrosts in 24 h**, and humidity-aware control none. In variable weather, **37 %** of time-temperature defrosts were unnecessary. Correct initiation happened at about 90 % coil coverage, a 20 % rise in suction-discharge ΔT and a 30 % capacity drop.
- EnergieSchweiz [12]:
  - fixed "1 h run → 10 min defrost" timers defrost even when the coil is clear;
  - a "natural defrost" (compressor off, fan on) works up to about +5 °C ambient;
  - correctly tuned defrost saves CHF 500-1,000 per year on larger plants.
- The Versati III fan stops when the compressor stops, as far as the documents show [1]. Passive melting during off-time therefore relies on still air above 0 °C. This is consistent with the r = 0.75 off-time / interval correlation in [20], but not proven.

## What this means for controlling this house

Confidence: **H** high, **M** medium, **L** low.

1. **Do not use short runs or stops to "dodge" defrost (H).**
   - The Gree clock accumulates across thermostat stops [3][20]. Other brands even count short runs towards a forced defrost [13].
   - Rule: never schedule a stop just to avoid a defrost.
   - When a run starts in the frost band, assume a defrost may come within 10-20 min if 50-60 run-minutes have built up since the last one.
2. **Plan on frost-band run-hours, not on starts (M).**
   - Frost band: T_out ≤ +3.5 °C with RH ≥ 85 %, or T_out ≤ 0 °C at any RH above about 75 % [5][22].
   - Budget about **0.8-1.2 defrosts per run-hour** in that band [5][20]. Use about 0.5 per run-hour at +3.5…+5 °C with RH > 85 %, and about 0.5 per run-hour below −12 °C.
   - Cost per defrost: **0.15-0.2 kWh_el**. That is about a **10-15 % penalty on frost-band electricity**, enough to make the planner prefer warmer, drier hours when the slab can coast (6.6 kWh/K, 6-12 h).
3. **Prefer long, minimum-power runs at the lowest flow temperature in the frost band (M for COP, L-M for defrost).**
   - Avoid catch-up bursts (36-39 °C setpoints, 3 kW electric) at 0…+4 °C. Lab and field data show 0-60 % fewer defrosts per kWh at low compressor speed with full fan [7][21].
   - Lower water temperature alone cut modelled Vilnius defrosts by 26 % [5].
   - Even with no defrost benefit, the COP gain from lower lift and speed justifies this.
4. **Never enable quiet mode in the frost band (H).** It slows the fan and pins defrost at the timer floor on Versati III [4][7]. If night quiet mode is wanted, apply it only above +5 °C, or below −5 °C where the air is dry.
5. **Test whether the C/P power limit helps on this unit (H value, low cost).**
   - Log at 10-30 s: defrost bit (coil 86), coil/defrost temperature (register 120), outdoor T and RH (local sensor), compressor Hz, electric power and outlet temperature.
   - A/B nights at +1…+4 °C, RH ≥ 85 %:
     - (a) normal control;
     - (b) power cap at about the minimum-output draw plus the lowest flow setpoint that holds the slab.
   - Success criterion: run-minutes between defrosts **> 90** in (b), against about 55-60 in (a). Also check that coil temperature at the same outdoor T and RH sits about 1-3 K warmer.
   - If intervals stay at about 55-60 min, the unit is clock-bound (the fan probably slows with suction pressure). Then stop chasing defrost with caps and keep them only for COP.
6. **Find this unit's entry threshold from the logs (H).** Read the coil temperature in the minute before each defrost bit rises. Expect about −4…−6 °C [2][3]. Then compute, for each (T_out, RH, power), whether the coil reaches that threshold. This gives a unit-specific frost map, a cheap version of [7].
7. **Mask defrosts in control and learning (H).**
   - Exclude the defrost plus 10-15 min of recovery (reverse flow 1.5-5 min [5][20], +18 % power for about 10 min [20]).
   - Never raise the flow setpoint because of a post-defrost dip.
   - On a UFH slab, the 0.3-0.8 kWh drawn back per event is about 0.05-0.1 K of slab temperature: harmless.
8. **Move heat to milder afternoons mainly in Oct-Nov and Mar-Apr (M).** The day-night swing is about +4.2 K and RH falls 89 → 68 % then, against only +1.4 K in Dec-Feb [22]. Gains in mid-winter will be small.
9. **Be realistic about the size of the prize (M-L).** Defrost is about 5 % of heating electricity (range 4-8 %). Maybe a quarter to a half is avoidable through power, fan-safe settings and timing, so about 1-3 % of heating electricity, €10-50 per season. That is second-order next to flow temperature (2-3 % COP per K) and avoiding catch-up bursts, but it pushes the same way.

## Contradictions and open questions

**Contradictions**

- **Gree clock floor.**
  - The Versati I/II default is 50 min [2], and Versati III and Flexx show 52-60 min [4][20].
  - The Neo split [3] uses 45 min continuous or 90 min accumulated.
  - So the Versati III value is between 50 and 60 min, but its coil threshold and adaptive steps are unknown. The 120-min peak on the Flexx [20] may be the "light frost" branch.
- **Does low load prevent frost at 0 °C?**
  - Wei [23] says no frost at 0 °C / 80 % at low load.
  - Liu [7] says frost at almost all speeds at 2 °C / 84 %. Kropas [5] sees onset at 85 % RH.
  - Reconciliation: RH is decisive. At Lithuanian 88-90 % RH, low load delays frost but does not avoid it.
- **Field share of energy.**
  - 2-3 % of heat (UK, Lea [17]);
  - 3.9 % SPF floor (Vilnius model [5]);
  - 6-7 % (field mapping to Kaunas [21][22]);
  - 9.2 % in a 36-h cold, humid window [17].

  These are different metrics: heat reversed, electricity, and a worst-case window.
- **Zhu et al. unnecessary-defrost share.** Secondary summaries say 63 %; the IIR abstract says 37 % [8]. I used 37 %.
- **Defrost duration.** About 1.5-2 min of reversed flow on Gree [20], 5 min on Panasonic [5], under 5 min on Samsung [15], 14 min on R290 Vaillant and Viessmann [14]. Brand logic varies, so per-event cost does not transfer cleanly.

**Open questions**

1. Versati III entry coil temperature, any suction-pressure threshold, and the adaptive rule. Ask Gree service for the Versati III/IV control specification. The Versati IV service manual (Gree Hungary) exists but could not be retrieved.
2. Does the Versati III fan slow when the compressor is capped (suction-pressure fan law)? Fan speed is not readable [4]; infer it from coil-minus-air temperature at constant output.
3. Does the clock count only while the coil is cold (as Trane boards do)? Test: compare accumulated run-minutes between defrosts on cold-coil and warm-coil runs.
4. Is there a short-run OFF counter (as on Fujitsu [13]) that could force a defrost after many short cycles?
5. Milev et al. [10] per-city energy results, and the Kropas 2021 article full text [6]. The thesis [5] supersedes it.
6. Does off-time with the fan stopped melt frost at +1…+4 °C? If so, cycling partly self-defrosts. The field correlation [20] is confounded.

## Sources

1. VERSATI III Air-to-Water Heat Pump service manual (Monoblock 4-16 kW, R32) - Gree (hosted by Gree Bulgaria) - about 2020 - https://gree-bulgaria.com/manuals/service/Versati_III_Monoblock_04_06_08_10_12_14_16_service.pdf - manufacturer - Coil "defrost" sensor mainly controls defrost; suction pressure used for defrost, freeze protection and superheat; fan follows low-side pressure and stops in defrost; "smart defrost" claim; manual defrost ends at 20 °C or 10 min.
2. Air-to-Water Heat Pump Service Manual Versati II (T1/R410A/50Hz, 2013) - Gree (hosted by Gree Bulgaria) - 2013 - https://gree-bulgaria.com/manuals/archive/140_VERSATI_II_TSM_%202013_8.pdf (same logic as Versati I, https://gree-bulgaria.com/manuals/archive/5_Versati-TSM.pdf) - manufacturer - Entry: accumulative compressor run > 50 min and coil < −4 °C; exit 10 min or coil > 15 °C.
3. Neo Ductless System Installation, Service & Troubleshooting (heat pump, rev. A) - Gree Comfort - about 2018 - https://www.greecomfort.com/assets/documents/archive/neo-heat-pump-revision-a/service-manual.pdf - manufacturer (sister product) - Explicit clock-reset rule (not cleared by setpoint or protection stops); 45-min continuous / 90-min accumulated entry; coil thresholds by outdoor band; 3 K compensation; 2-h lockout; 450 s / +10 °C exit.
4. Gree Versati III air to water heat pump, thread page 7 - Home Assistant Community (JKF1, pranelio) - Nov 2026 - https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916?page=7 - forum (owner observation) - Quiet mode: defrost every 52-56 min at +2…+5 °C on a 16 kW Versati III; quiet-mode, max-frequency and fan registers read 0 on this firmware.
5. Research on freezing processes of aerothermal heat pump evaporator under dynamic environmental conditions (PhD thesis) - Tomas Kropas, VILNIUS TECH - 2026 - https://doi.org/10.20334/2026-008-M (https://cris.vilniustech.lt/cris/handle/20.500.14911/160074) - field data + validated simulation - Vilnius Panasonic 7 kW: onset < 3.5 °C / > 85 % RH; 5-min defrosts; 1.17/h at −2…+3.7 °C; 12 % lower COP in defrost hours; typical year 1,364 defrosts (0.27/h), −26 % at 35 °C water; SPF −3.9 %.
6. Experimental Investigation of Frost Formation Influence on an Air Source Heat Pump Evaporator - Kropas, Streckienė, Bielskus / Energies 14(18):5737 - 2021 - https://ideas.repec.org/a/gam/jeners/v14y2021i18p5737-d633785.html - paper (abstract) - Onset below 3.5 °C at 88 % RH; 5-min average defrost.
7. Experimental and modeling studies on developing a condensing-frosting performance map for a variable speed ASHP unit for frosting suppression (PhD thesis) - Liu Shengnan, Hong Kong PolyU - 2023 - https://theses.lib.polyu.edu.hk/bitstream/200/12447/3/6895.pdf - controlled lab - Coil temperature vs compressor Hz × fan %; same 9.1 kW: no frost (50 Hz / 100 % fan, COP 4.36) vs blocked in 58 min (65 Hz / 25 %, COP 3.58); at 2 °C / 84 %, 22 → 9 defrosts per day.
8. A novel Temperature-Humidity-Time defrosting control method based on a frosting map for ASHPs - Zhu, Sun, Wang, Ge, Li / Int. J. Refrigeration 54:45-54 - 2015 - https://iifiir.org/en/fridoc/a-novel-temperature-humidity-time-defrosting-control-method-based-on-a-138394 - field test (abstract) - T-T fired 31 defrosts per 24 h with no frost; 37 % unnecessary in variable weather; correct start at about 90 % coverage, +20 % suction-discharge ΔT, −30 % capacity.
9. Field experimental research on retarding frosting and improving defrosting performance of ASHPs through variable frequency technology - Wu et al. / J. Building Engineering 64 - 2023 - https://peeref.com/works/27853570 (DOI 10.1016/j.jobe.2022.105628) - field (abstract via search only) - Variable-frequency unit: longer frost-free periods; defrost time 26 % of fixed-speed at −10…+12 °C; +4 to 9 % performance.
10. Investigating the effect of the defrost cycles of air-source heat pumps on their electricity demand in residential buildings - Milev, Al-Habaibeh, Fanshawe, Siena / Energy and Buildings 300:113656 (summary by pv magazine) - 2023 - https://www.pv-magazine.com/2023/12/05/new-model-to-predict-defrost-cycles-behavior-of-air-sourced-heat-pumps-in-cold-weather/ - simulation (secondary summary) - 10 cities; defrost count vs temperature r = −0.94; 56 (Vancouver) to 1,070 (Harbin) per Dec-Feb.
11. Aanvriezen van de verdamper (HPLaunch WP4) - Maarten van den Berg, HAN University of Applied Sciences - 2020 - https://www.han.nl/projecten/2020/hplaunch/artikelen-en-documenten/Aanvriezen-van-de-verdamper.pdf - simulation - NL climate: time-temperature 30/60/90 min → 3,824 / 1,912 / 1,226 defrosts per year; frost-mass model about 900; evaporator ≈ 1.16·T − 6.4 °C; frost spells often ≥ 8 h.
12. Betriebsoptimierung Heizung: Abtauung Luft-Wasser-Wärmepumpen - EnergieSchweiz / BFE - 2021 - https://pubdb.bfe.admin.ch/de/publication/download/9977 - government guidance - Fixed vs demand defrost; natural (fan-only) defrost up to +5 °C; CHF 500-1,000 per year from correct tuning; 80 % of units reverse-cycle.
13. ARTG45/60LDTA defrost operation control - Fujitsu General (AU) - about 2020 - https://assist.generalairstage.com.au/support/solutions/articles/6000134775-artg45-60ldta-defrost-operation-control - manufacturer (other brand) - Integrating timer with coil gates; 40 short runs (< 10 min) force a defrost; counts reset only after a defrost.
14. Viessmann Defrost - Glyn Hudson, OpenEnergyMonitor forum - 2024 - https://community.openenergymonitor.org/t/viessmann-defrost/27441 - field data - At 0.6 °C / 36 °C flow, 14-min defrosts: Vaillant 12 kW 0.14 kWh_el + 0.76 kWh heat back (about 0.39 kWh_el); Viessmann 16 kW about 0.6 kWh_el.
15. Samsung ASHPs: Anatomy of a Defrost - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/samsung-ashps-anatomy-of-a-defrost/27767 - field data - Coil-below-line for 3 min trigger; defrost under 5 min; 570 Wh heat from house; compressor 50 Hz in defrost; post-defrost peak above nameplate.
16. Defrost Cycles - How Common Are They? (page 4) - Renewable Heating Hub forum - 2024-25 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/defrost-cycles-how-common-are-they/paged/4/ - forum - Grant Aerona3 every 37-40 min at 0-2 °C, wet; owners report fewer defrosts after lowering flow temperature and compressor rate.
17. Heat Pumps and Defrost Cycles: The Missing Piece in Performance Data? - Renewable Heating Hub - 2025 - https://renewableheatinghub.co.uk/heat-pump-defrost-performance-issues/ - blog (quotes field experts) - Lea: 2-3 % of heat across UK systems; Heat Geek: 9.2 % in a 36-h window; Havenwise: about 15 % output loss.
18. LWP wegen Abtauen am Leistungslimit (thread) - energiesparhaus.at forum - 2025 - https://www.energiesparhaus.at/forum-lwp-wegen-abtauen-am-leistungslimit/81571_4 - forum - Nibe S2125 defrosts on temperature/frequency without RH; M-TEC starts at air-in to suction ΔT > 10 K; quiet mode ices the fins.
19. Wärmepumpe abtauen - 42watt magazine - 2025 - https://42watt.de/magazin/warmepumpe-abtauen - blog - Defrost 5-15 min; peak icing −5…+5 °C; condensate 5-40 L per day; BFE savings claim.
20. HeatpumpMonitor.org system #251 (Gree Flexx 7 kW, Ottawa), 15-s/1-min data Dec 2024-Mar 2025 - OpenEnergyMonitor / owner - 2025 - https://heatpumpmonitor.org/timeseries/available?id=251 - field data (own offline analysis, earlier version of this note) - 679 defrosts; 55-60 min accumulated floor; defrosts 16 min after restarts; 0.18 kWh_el per event; no low-power benefit.
21. HeatpumpMonitor.org, 15 systems, 1-min data Dec 2024-Mar 2025 (index: https://heatpumpmonitor.org/system/list/public.json) - OpenEnergyMonitor / owners - 2025 - field data (own offline analysis) - Low/high power defrost-per-kWh ratio median 0.91; per-event about 0.16 kWh_el; reverse-heat mapping gives about 6-7 % of electricity.
22. Open-Meteo archive (ERA5), Kaunas, hourly T and RH, 2015-2026 - Open-Meteo - 2026 - https://archive-api.open-meteo.com/v1/archive - reanalysis data (own analysis) - About 1,040 h per season at 0…+4 °C with RH > 85 % (31 % of heat demand); median RH 88-90 % at 0…+4 °C; seasonal day-night swings.
23. A new frosting map of variable-frequency ASHP in severe cold region considering heating load - Wei et al. / Renewable Energy 161:184-199 - 2020 - https://ideas.repec.org/a/eee/renene/v161y2020icp184-199.html - lab/field rig (abstract, via note 09) - No frost at 0 °C / 80 % at low load; critical RH 80.6 % at +1 °C.
24. The cost of defrost (thread) - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/the-cost-of-defrost/28429 - forum - Samsung HTQ owners see few, short (< 5 min) defrosts; cost depends on reheat of the water and the house; no figures.
25. Internal sweep notes 08 (Gree Versati) and 09 (defrost) - this project, docs/research/notes/ - 2026 - local files - secondary - Modbus coil 86 and register 120; C/P power limit; 113-system daily defrost table.
