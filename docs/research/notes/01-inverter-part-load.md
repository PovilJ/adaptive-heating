# Inverter compressor modulation and part-load efficiency

> Research date: 2026-11-06. Topic owner: researcher 01 of 15.
> Question: how do inverter air-to-water compressors modulate, where is their efficiency best, what does running below minimum capacity (on/off cycling) really cost, and what does that mean for a 9 kW-class Gree Versati on a slab underfloor system whose minimum output is above the mild-weather load?
>
> Method:
> - I read 35 distinct sources: manufacturer manuals and certified EN 14825 data, lab papers and theses, field studies, installer forums.
> - I extracted PDF text locally, using OCR for scanned PDFs and reading the charts off rendered pages.
> - **New field evidence.** I analysed public HeatpumpMonitor.org data myself [1]:
>   - a cross-section of 482 air-source systems over their last 365 days;
>   - a day-by-day comparison inside 62 systems, about 14,500 mild days between −5 and +15 °C.
>
> Evidence ranking: measured field data > controlled lab test > peer-reviewed simulation > manufacturer claim > forum anecdote.
>
> **Gap:** the web-search budget shared by all 15 researchers ran out after **19 searches**, short of the 25 or more planned. Only one non-English query ran (German). I made up for this by reading German and Czech primary documents, by following links inside sources, and with the raw-data analysis.
>
> I did not read this repository's code or docs. I read only the sibling note `08-gree-versati.md` in this folder, and only to avoid contradicting its Versati register details.

## Summary

1. **The biggest avoidable loss in this house is probably the high-frequency "catch-up" run, not the number of starts.**
   - The Versati sets compressor frequency in proportion to (setpoint − leaving water) and stops only once it is at minimum frequency and the water has overshot [4].
   - With a 4 K restart gap, every restart opens with a ≥4 K error, so the compressor starts fast. That fits the observed ~3 kW draw at +2 °C. At best ~8 kW of heat [4] that is a COP of only about 2.7–3.
   - Certified part-load COPs of comparable 7–10 kW units near minimum speed at A2/W30 are **4.35–4.76** [8][9][10][11][12].
   - Every kWh of heat delivered in a burst therefore costs roughly 30–40% more electricity than the same kWh at minimum speed. This estimate is derived from these sources, not measured on this unit.

2. **Flow temperature matters about 15 times more than starts per day** (own analysis of HeatpumpMonitor data [1]).
   - Inside the same system, at the same outdoor temperature, space-heating COP falls by a median **2.24% per +1 K of flow temperature** (IQR 1.36–3.35%; 26 systems with a separate space-heating meter).
   - It falls by only **0.15% per extra compressor start per day** (IQR 0.03–0.35%).
   - Across 482 systems:
     - running flow temperature tracks COP strongly (Spearman ρ = −0.60);
     - starts per day barely relate to efficiency (ρ = −0.04 against % of Carnot, −0.13 against COP).

3. **Direct cycling losses only appear with short cycles.**
   - Inside each of 62 systems, at matched outdoor temperature, % of Carnot (efficiency relative to an ideal heat pump) changes by:
     - about 0 (±1%) at 1–15 starts/day;
     - −0.2% to −0.9% at 16–40 starts/day;
     - **−2.0% to −3.7%** above 40 starts/day, i.e. cycles of roughly 20–30 min or less [1].
   - The owner's runs of 0.5–4 h sit in the harmless range for direct losses.

4. **The real price of on/off operation is indirect: hotter water during the on-time.** A FHNW model validated on Vaillant lab data found [20]:
   - average flow temperature weighted by run time was **31.0 °C with variable speed versus 35.2 °C with fixed speed**, for the same building and heat;
   - that 4.2 K is worth about 9–10% of COP at the 2.2%/K above.

5. **The unit's minimum output exceeds the load over most of the Lithuanian heating season.**
   - With H = 0.14–0.20 kW/K and P_min = 3.7–3.8 kW, load equals P_min at outdoor **−5 to +3.5 °C** (about −2 °C at H = 0.155).
   - Above that the unit must cycle. Duty at minimum output is about 84% at +2 °C, about 50% at +10 °C and about 29% at +15 °C (my calculation from the owner's figures, ignoring internal and solar gains).
   - At +2 °C the house needs only ~3.1 kW, so near-continuous minimum-speed running (~20 h/day) is possible. Full-speed bursts there are pure loss.

6. **For this unit, minimum frequency is probably the most efficient operating point.**
   - At fixed water and air temperatures, whole-unit COP rises as speed falls, with a broad optimum around **30–50% of maximum capacity**:
     - Viessmann datasheet: COP at 29% load is 1.27× the full-load COP; at 15% load it is 1.22× [20];
     - Carel chart (DC inverter): peak about 4.9 at 40–45% load against 3.1 at full load [20];
     - KTH lab: COP −32% going from 30 to 90 Hz [16]; another KTH test: up to −30% [17];
     - Hokkaido lab: best COP at 45 Hz [18]; Chinese lab: COP rises linearly from 90 Hz down to 40 Hz [19].
   - The Versati's ~3.7 kW minimum is ≈39% of its 9.5 kW rating [6], inside that window.

7. **Field data show efficiency collapsing only at the very bottom of the range.** Inside each system, running % of Carnot is flat (±0.7 points) between **30% and 90% of rated output**. It drops 0.8–4 points below 30% [1]. A Swiss study of field-monitored units (OST/Bertsch) reports the same sharp drop below a unit-specific output, and notes that standard tests do not capture it [21].

8. **Typical turndown is about 3:1, not the 5:1 to 10:1 that marketing implies.**
   - Community-measured minimum continuous outputs across 45 model sizes: **19–76% of nominal, median about 34%** [2].
   - 8–10 kW class:
     | Unit | Minimum output |
     |---|---|
     | Daikin Altherma 3 8 kW | 1.96 kW |
     | Viessmann 150-A 8 kW | 1.99 kW |
     | Ecodan R290 8 kW | 2.04 kW |
     | Grant 9 kW | 2.60 kW |
     | Samsung 8 kW | 2.47–2.93 kW |
     | Octopus Cosy 9 kW | 3.05 kW |
     | Vaillant aroTHERM plus 7 kW | 3.29 kW |
     | Daikin 9 kW (9–16 kW frame) | 4.02 kW |
     | Riello 8 kW | 4.17 kW |
     | Ecodan R32 8.5 kW | 4.41 kW |
   - Gree advertises compressor control down to 10 Hz [7], but the owner measures ~3.7–3.8 kW.

9. **Minimum and maximum capacity both move with the weather, against you in mild weather.**
   - Versati III 10 kW maximum at W35: **9.50 kW at +7 °C, 8.08 kW at +2 °C, 6.65 kW at −7 °C, 4.56 kW at −20 °C** [4].
   - Minimum capacity rises as it gets warmer. The aroTHERM plus 7 kW certified minimum is 2.80 → 3.25 → 3.73 kW at +2/+7/+12 °C [8]; the aroTHERM split 10.5 kW goes 5.66 → 6.52 kW from +7 to +12 °C [9].

10. **The standard cycling penalty in EN 14825 does not match field data.**
    - The rating formula is COP_PL = COPd × CR / (Cc × CR + 1 − Cc), with a default Cc of 0.9 [13].
    - Manufacturers declare Cdh = **0.94–1.0** (Vaillant 0.94–0.99; Daikin 1.0); Hisense/Hitachi used the 0.9 default [8][9][10][11][12].
    - A field fit on a 10.6 kW inverter air-to-water unit (minimum 5.0 kW) gave an effective **Cc ≈ 0.80**. That implies a part-load factor of 0.83 at 50% load and 0.56 at 20% load [13].
    - A lab study showed that start-up losses dominate with small water volume (50 L) and become negligible with 1000 L of storage [14].

11. **Off-mode power is small, but check Gree's crankcase heater.**
    - Certified off, standby and thermostat-off power: **8–29 W**; crankcase heater 0 W on the units checked [8][9][10][11][12].
    - Field off-time draw: median **14.6 W** (p90 31.5 W), or **2.4%** of annual electricity (p90 5.2%) [1].
    - The Versati has a crankcase heater with no published power [4].
    - The internal pump draws up to 75–85 W and may run during standby (see `08-gree-versati.md`). Running round the clock that would be ~7–20% of mild-weather electricity, likely the largest low-load parasitic in this house (my arithmetic).

12. **Comparable units reach high COPs in mild weather when flow is low.** Certified EN 14825 average-climate, low-temperature points for 7–10 kW units [8][9][10][11][12]:

    | Point | COP |
    |---|---|
    | A2/W≈30 | 4.35–4.76 |
    | A7/W≈27 | 5.8–6.8 |
    | A12/W≈24 | 7.3–9.6 |

    The owner's 31–36 °C setpoints (peaks 39 °C) are roughly 4–10 K above those points. At 2.2%/K that is about 9–22% of COP.

13. **The Versati already has the levers needed** [4]:
    - a **power limit** of 0–10 kW (default 3.0 kW), or a current limit;
    - a **minimum "Heat run time"** of 1–10 min;
    - a room-temperature control mode with a 1–5 K band;
    - quiet mode;
    - a built-in weather curve.

    A single power-limit write can remove the 3 kW bursts. Quiet mode is a worse cap: it may multiply defrosts in humid weather (see `08-gree-versati.md`).

14. **The slab makes long cycles almost free and short corrections pointless.**
    - Time constant τ = C/H ≈ 6.6/(0.14–0.20) ≈ **33–47 h**.
    - A 3-hour block at minimum output raises the slab's mean temperature by only ~0.5 K at +5 °C and ~0.8 K at +10 °C (my calculation).
    - Three to six long runs per day therefore cost under 1% [1], while catch-up bursts and high water temperatures cost 10–40% [1][20].

15. **Degree-minute ("energy integral") start logic is the industry answer to fixed restart hysteresis.**
    - Vaillant starts the compressor at a heat deficit of −60 K·min (default, adjustable to −120) and stops when the integral reaches 0 or flow exceeds target + 7 K [30].
    - NIBE and Viessmann use the same concept [32].
    - A forum user reported that moving the start threshold from −60 to −120 mainly cut cycling, with little COP change [30].

## Detailed findings

### 1. How inverter air-to-water units modulate

**Compressor and drive.** Two technologies dominate:
- Small units mostly use **rotary** (single or twin-rotor) compressors. Some are two-stage with vapour injection between stages, as in the Gree Versati III [7].
- Others use **scroll** compressors.

The motor is a permanent-magnet DC or synchronous motor fed by an inverter.
- Older induction motors keep drawing a magnetising current that does no useful work. That loss is proportionally worse at part load and in small motors [15][16].
- Permanent-magnet motors removed most of that penalty [15].

**Frequency ranges.**
- KTH lab, Copeland ZHW16K1P vapour-injection scroll (R410A): **30–90 Hz**. Above 90 Hz it tripped on discharge temperature [16].
- Gree markets "G10" control, claiming compressor speed down to **10 Hz** [7]. The sibling note 08 cites a Gree document giving **20–120 Hz (900–6600 rpm)**. See Contradictions.
- In the KTH test the pressure ratio rose from **2.7 to 5.8** across the speed range. The heat-exchanger temperature differences grow with speed and drive this rise [17].

**Where the losses sit** (lab, KTH) [16]:
- **Inverter losses** rose from ~95 W at 30 Hz to ~225 W at 90 Hz, but fell as a share of compressor power, from about 10% to 6%.
- **Electromechanical losses** (motor plus non-ideal compression) were 345 → 740 W. Total compressor losses were 440 → 970 W.
- **Isentropic and Carnot efficiency peaked at 60 Hz.** Its best Carnot efficiency was 61%, at 5/25 °C.
- **Built-in pressure ratio.** Every displacement compressor is most efficient at one pressure ratio (3.48 for this one). Over- or under-compression away from it costs work.
- **Literature cited in [16]:**
  - inverters measured at 95–98% efficiency between 1.5 and 6.5 kW input (Cuevas and Lebrun);
  - one Swedish study found variable-speed ground-source units no better over a year than on/off units, because of inverter, motor and pump losses (Karlsson and Fahlén);
  - another modelled a 10% gain in seasonal performance factor (Madani).

**Why low speed still usually wins at the system level.**
- Heat-exchanger temperature differences shrink with load. In a fixed-NTU model the condenser difference falls from 5.0 K at 100% capacity to **2.5 K at 50%**. Refrigerant condensing temperature drops from 37.5 to 36.3 °C for the same 35 °C water [20]. The evaporator behaves the same way, so the true lift falls and COP rises even though the compressor itself is past its best speed.
- Lower capacity also means less frosting and noise, fewer starts, and the chance to overspeed when it is very cold [15].

**Turndown, measured.** HeatpumpMonitor.org collects community "minimum modulation tests", the lowest steady output seen [2][3]:

| Model (nominal) | Minimum output, kW (n tests) | % of nominal | Maximum seen, kW |
|---|---|---|---|
| Daikin Altherma 3, 8 kW (R32) | 1.96 (6) | 24% | – |
| Viessmann Vitocal 150-A, 8 kW (R290) | 1.99 (4) | 25% | 5.58 |
| Mitsubishi Ecodan, 8 kW (R290) | 2.04 (3) | 25% | – |
| Viessmann Vitocal 151-A, 8 kW | 2.19 (3) | 27% | – |
| Nibe S2125, 12 kW (R290) | 2.26 (5) | 19% | – |
| Samsung Gen 6, 8 kW (R32) | 2.47 (1) | 31% | 6.51 |
| Grant Aerona HP290, 9 kW | 2.60 (6) | 29% | 8.62 |
| Samsung Gen 7, 8 kW (R290) | 2.73 (4) | 34% | 7.48 |
| Samsung HTQ, 8 kW (R32) | 2.93 (1) | 37% | – |
| Panasonic Aquarea J, 7 kW | 2.96 (2) | 42% | 5.22 |
| Octopus Cosy, 9 kW (R290) | 3.05 (3) | 34% | 7.47 |
| Vaillant aroTHERM plus, 7 kW | 3.29 (5) | 47% | 6.70 |
| Viessmann Vitocal 150-A, 10 kW | 3.77 (5) | 38% | – |
| Daikin Altherma 3, 9 kW (9–16 kW frame) | 4.02 (9) | 45% | – |
| Riello NXHM, 8 / 10 kW | 4.17 / 4.52 | 52% / 45% | 6.44 / 6.62 |
| Mitsubishi Ecodan, 8.5 kW (R32) | 4.41 (3) | 52% | 7.77 |
| Vaillant aroTHERM plus, 10 / 12 kW | 5.94 / 5.77 | 59% / 48% | 9.55 / 11.13 |

Notes on the table:
- Over all 45 model sizes with a test, the median is about 34% of nominal and the range 19–76% [2].
- Test conditions are not standardised. They are mostly mild outdoor temperatures, often at or above 10 °C [3].
- For Vaillant, Trystan Lea notes the minimum output tracks the minimum pump flow × 5 K × 4150 J/kg·K [3].
- The Versati's 3.7–3.8 kW (≈39% of 9.5 kW) sits mid-to-high in this field.

Other claims:
- An installer claims minimum outputs are typically 15–20% of nameplate in units he has tested [31]. Another found no manufacturer table showing a range above 3:1 [31].
- Hitachi Yutaki 3HP: 2.1–11 kW (19%), as quoted by an installer [31].
- Interquartile range of the 45 tested model sizes: 29–45% of nominal [2].

**How the limits move with conditions.**
- *Maximum* capacity falls hard in the cold. Versati III 10 kW single-phase at W35 [4]:

  | Outdoor (°C) | −20 | −15 | −10 | −7 | −2 | +2 | +7 | +10 | +15 |
  |---|---|---|---|---|---|---|---|---|---|
  | Capacity (kW) | 4.56 | 5.32 | 6.18 | 6.65 | 7.41 | 8.08 | 9.50 | 9.79 | 10.36 |

  - At W55 it is 5.70 kW at −10 °C and 8.74 kW at +7 °C.
  - The three-phase 10 kW is about 7% higher.
- Daikin's integrated maximum curves dip between −7 and +2 °C because they include defrost. For example, the EBLA08 holds a flat ~7.3 kW from −7 to +2 °C, then jumps to ~9 kW at +7 °C [11][12].
- *Minimum* capacity rises with outdoor temperature. More source heat means more refrigerant mass flow at the same minimum speed. EN 14825 declared capacities where the unit is already at its floor:
  - aroTHERM plus 7 kW: **2.80 kW at +2, 3.25 kW at +7, 3.73 kW at +12 °C** [8];
  - aroTHERM split 10.5 kW: **5.66 kW at +7, 6.52 kW at +12 °C** [9];
  - Daikin 9–16 kW frame: about 4.6–4.7 kW at +7 and 5.4–5.5 kW at +12 °C [12]. An 11 kW owner reports a minimum of a little over 5 kW at any outdoor temperature above +5 °C [26].
- The UK Home Energy Model accordingly takes minimum modulation as an input at 35 and 55 °C flow and interpolates between them [23].

### 2. COP versus speed and part-load ratio

**Lab and model curves at fixed source and sink temperatures:**

| Source | Machine | Finding |
|---|---|---|
| KTH lab [16] | Brine/water rig, VI scroll, 30–90 Hz | Heating COP −32% from 30 to 90 Hz; compressor power 1 → 4 kW; isentropic efficiency peaks at 60 Hz, but whole-unit COP is highest at the lowest speed |
| KTH lab [17] | Variable-capacity rig, 2010 | COP falls up to 30% as speed rises; isentropic efficiency best near 50 Hz |
| Hokkaido lab [18] | Inverter water/water with desuperheater, 45–90 Hz | Highest COP at 45 Hz (lowest tested) in most conditions; COP tracks pressure ratio and volumetric efficiency |
| Shunde lab [19] | R290 variable-frequency water heater | COP rises linearly as frequency falls from 90 to 40 Hz |
| Viessmann Vitocal 300-A datasheet, via FHNW [20] | Air/water | COP ratio vs full load: 1.09 at 56%, **1.27 at 29%**, 1.22 at 15% |
| Carel chart, via FHNW [20] | DC inverter | COP 3.1 at 100% → **~4.9 at 40–45%** → 4.7 at 25% → 4.35 at 10% |
| Carel chart, via FHNW [20] | AC inverter | Peak ~3.7 at 45–50%; 2.05 at 10% |
| Carel chart, via FHNW [20] | On/off | 3.4 at 100% → 1.05 at 10% |
| Fahlén simulation [15] | Rotating air-to-air, three motor types | With constant fan power: COP peaks at f ≈ 0.3 (new motor, ~4.9) or ≈ 0.55–0.6 (standard motor, ~3.5). With fan power scaled down with load: the new motor keeps rising to 7.4 at f = 0.1 |
| ETCC lab [24] | Variable-speed air-to-air, 8 °C outdoor | COP 4.90 at 3.83 kW (intermediate) vs 3.96 at 7.28 kW (full) |

Fahlén's table at f = 1.0 / 0.5 / 0.2 [15]:
- **Fixed condensing and evaporating temperatures** (no heat-exchanger benefit): 3.1 / 2.4 / 1.4 with a standard motor.
- **Adapted flows and fan power**: 3.1 / 4.1 / 3.2 (standard motor) and 3.3 / 5.5 / 7.1 (new design).
- The part-load gain is therefore not automatic. It depends on letting the heat-exchanger temperature differences shrink, scaling fan and pump power with load, and a motor that stays efficient at low torque.

**Field evidence.**
- *Own within-system analysis* [1]. Inside each system, I binned days by outdoor temperature (2 K bins). I compared running % of Carnot with average output while running as a fraction of rated output:

  | Output fraction | 0.1–0.2 | 0.2–0.3 | 0.3–0.4 | 0.4–0.5 | 0.5–0.6 | 0.6–0.7 | 0.7–0.8 | 0.8–0.9 | 0.9–1.0 |
  |---|---|---|---|---|---|---|---|---|---|
  | Mean deviation (points) | **−4.1** | −0.8 | −0.3 | −0.1 | +0.2 | +0.3 | +0.7 | +0.3 | −0.6 |

  - About 15,000 days across 62 systems; the median system runs at 0.52 of rated while on.
  - % of Carnot here uses water and air temperatures. Its flatness therefore means COP at a given flow and outdoor temperature barely depends on speed between 30% and 90%. The practical benefit of low speed is that it lets the same heat go in at a lower flow temperature.
- *OST/Bertsch field study* (Swiss federal energy office monitoring, air/water and brine/water) [21]:
  - Carnot efficiency is stable over wide ranges but collapses below unit-specific output limits.
  - Standard rating points miss this, and fit badly at low temperature lifts.
- *Forum:* one owner says efficiency peaks near 40% of the modulation range, from a chart of unclear origin [30].

**Conclusion for the speed question.**
- Most modern units are most efficient somewhere between about 30% and 50% of their *maximum* capacity under the given conditions.
- Below about 25–30% (only reachable on very wide-range units), fixed fan, pump and electronics loads plus compressor leakage pull COP down.
- The Versati cannot go below ~39% of rating. Its minimum speed is therefore its best speed for space heating in mild weather. High speed is only justified when the house needs the capacity.

### 3. Cycling below minimum capacity: standard rating versus measurement

**How the rating handles it.**
- EN 14825 measures COP at four part-load points:
  - average climate, design −10 °C;
  - load ratios of about 88% at −7 °C, 54% at +2 °C, 35% at +7 °C and 15% at +12 °C (from (Tj − 16)/(−10 − 16)).
- If the unit cannot modulate down to the load, the declared COP at that point is degraded with COP_PL = COPd × CR / (Cc × CR + 1 − Cc) [13].
- Cc (written Cdh in the EU data sheets) is defined from the power drawn with the compressor off. The default when not measured is 0.9 [13].
- Measured values on new units are typically 0.96–0.99 [13]. Declared values seen here:
  - Vaillant aroTHERM plus: 0.94–0.99 [8];
  - aroTHERM split: 0.98–1.0 [9];
  - Daikin EBLA04–16: 1.0 [11][12];
  - Hisense/Hitachi Hi-Therma: default 0.90 [10].
- A Cc of 1.0 means the rating assumes *no* cycling penalty at all.
- The UK Home Energy Model, using EN 15316-4-2, adds an "inertia" penalty instead. It is proportional to P_min × LR × (1 − LR) × τ_eq / τ_emitter, which is largest at 50% load, with default time constants for "light embedded" floor systems [23].

**What measurements show:**

- **Field fit, Wrocław** [13]:
  - Setup: 10.6 kW (A2/W35) split inverter air-to-water unit with a 5.0 kW minimum, no buffer, low-temperature office installation of about 300 m². Hourly data for October 2013 to March 2014; load ratio 0.17–0.80, source 0–10 °C.
  - Result: fitted **Cc = 0.80** (0.79–0.81 over six data sets), far below the declared 0.96–0.99.
  - The authors propose PLF = 1 + a·ln(PLR + e^(−1/a)) with a ≈ 0.28.
  - Caveat: this lumps every part-load effect together (standby, start-up, controls, defrost) on a 2013-era unit.
- **Lab, IREC Barcelona** [14]:
  - Setup: 40.5 kW fixed-speed water/water unit.
  - Start-up timing: electrical power reached full value in under 20 s, but heat output only after **42–60 s**.
  - Standby: 15 W (0.2% of nominal), negligible above 20% load.
  - With 50 L of system volume, the measured ARI-style Cd was ~0.22. EN 14825 correlations missed by up to ~12%.
  - With 1000 L, EN 14825 with Cc = 0.998 was within 3.5%.
  - Conclusion: start-up losses matter, and their size depends on thermal inertia.
- **Own HeatpumpMonitor analysis** [1]:
  - The per-start effect is small and nonlinear (summary item 3).
  - Within systems, a regression controlling for outdoor temperature and output fraction gives:
    - running % of Carnot: −0.15% relative per extra start/day (IQR −0.32 to −0.04%; negative in 79% of systems);
    - all-in (including off-time draw): −0.09% (IQR −0.27 to +0.04%; negative in 69%).
  - Cross-section, 482 systems, split by average cycle length:

    | Average cycle length | 0.69 h (shortest quarter) | 1.25 h | 1.85 h | 3.58 h (longest quarter) |
    |---|---|---|---|---|
    | Median COP | 3.51 | 3.95 | 3.92 | 4.01 |
    | % of Carnot | 46.7 | 48.5 | 48.2 | 48.3 |
    | Running flow temperature (°C) | 35.2 | 34.5 | 34.2 | 33.5 |

  - So short-cycling systems also run hotter.
  - Within the same flow band, the most-cycling third (~9–21 starts/day) and least-cycling third (~3–4/day) differ in COP with no consistent sign:

    | Running flow band (°C) | COP, most-cycling vs least-cycling third | Difference |
    |---|---|---|
    | 25–32 | 4.29 vs 4.23 | +1.4% |
    | 32–36 | 3.85 vs 4.02 | −4.2% |
    | 36–40 | 3.56 vs 3.60 | −1.1% |
    | 40–50 (n = 30) | 3.13 vs 3.04 | +3.0% |
- **Anecdotes** (confounded; direction only):
  - One owner opened all radiators to force continuous running with an oversized minimum output. Power rose 28% and space-heating COP fell from 3.27 to 3.04 [27].
  - Another reports going from ~8 cycles/h at COP ~2.5 to near-continuous running at COP ~4 [28].
  - A Mitsubishi owner saw 3–4 starts per hour with 5–10 min pauses at 33–34 °C flow [33].
  - Experienced contributors [25]:
    - About two short pauses per hour on a modulating unit ("type 2" cycling) is fine.
    - The real losses come from thermostat on/off over long periods ("type 1" cycling) caused by a weather curve set too high.
    - On one Samsung unit, residual refrigerant flash-cools the condenser just after every stop, briefly reversing heat flow.

**Mechanisms, ranked by likely size for an inverter on a slab:**
1. Higher water temperature during the on-time, needed to push minimum output into the emitters, about 4 K in the FHNW example [20].
2. Fast restarts after a large error (firmware-specific: Gree [4], Samsung [25]).
3. Start-up transients: pressures and heat-exchanger mass must be re-established, about 1 min even on simple units [14]; the Versati manual describes a ramp-down before stops [4].
4. Off-time draw: pumps, controls, crankcase heater [1][8–12].
5. Defrost interaction (see Open questions).

### 4. Auxiliary power at low load

| Unit (EN 14825 declared) | P_off | P_TO (thermostat off) | P_SB (standby) | P_CK (crankcase heater) |
|---|---|---|---|---|
| Vaillant aroTHERM plus VWL 65/75/85/6 [8] | 8 W | 29 W | 29 W | 0 W |
| Vaillant aroTHERM split VWL 105/5 [9] | 11–17 W | 11–17 W | 11–17 W | 0 W |
| Hisense/Hitachi Hi-Therma 8 kW [10] | 10 W | 11 W | 10 W | 0 W |
| Daikin EBLA04–08 [11] | 10 W | 10 W | 10 W | 0 W |
| Daikin EBLA09–16 [12] | 23 W | 23 W | 23 W | 0 W |

**Field draw.** HeatpumpMonitor systems draw a median **14.6 W** while the compressor is off (p10 7.8, p90 31.5 W). That is 0.9–5.2% of annual electricity, median 2.4% [1].

**Rating boundaries.** EN 14511 COP includes outdoor fan power and the share of pump power needed for the unit's internal pressure drop. Separately metered external pumps are extra [23].

**The Versati** [4]:
- Outdoor fan speed in heating follows the low-side pressure, so it scales with load.
- The internal pump is variable-speed and adjusts its output to the load.
- A compressor crankcase heater exists; the manual requires 8 h of preheat before the first start, but gives no wattage.
- Sibling note 08: the pump draws up to 75–85 W and may keep running in standby. My arithmetic:
  - At +10 °C the compressor runs ~12 h at ~0.8–0.9 kW, about 10 kWh/day.
  - A pump drawing 30–85 W around the clock adds 0.7–2.0 kWh/day, i.e. **~7–20%**.
  - Off-time pump and crankcase draw is therefore worth measuring before any fine-tuning of cycles.

**Why fixed auxiliaries erode the part-load gain** (Fahlén [15]). If fan and pump power stay constant as compressor power falls, they become a growing share. The COP optimum then moves up from f ≈ 0.1 to f ≈ 0.3–0.6.

### 5. Comparable 8–10 kW units: certified part-load data

EN 14825, average climate, low-temperature (35 °C) application; capacity Pdh in kW / COP:

| Unit | Prated | +2 °C (≈W30) | +7 °C (≈W27) | +12 °C (≈W24) | Cdh at +12 °C |
|---|---|---|---|---|---|
| Vaillant aroTHERM plus 7 kW (R290) [8] | 7.21 | 3.83 / 4.73 | 3.21 / 6.33 | 3.72 / 7.79 | 0.94 |
| Vaillant aroTHERM split 10.5 kW (R410A) [9] | 11.5 | 6.53 / 4.57 | 5.66 / 5.78 | 6.52 / 7.35 | 0.99 |
| Daikin EBLA08 (R32) [11] | 8.0 | 4.2 / 4.35 | 3.2–3.3 / 6.2–6.5 | 3.3–3.9 / 7.8–8.5 | 1.0 |
| Daikin EBLA09, 9–16 kW frame (R32) [12] | 9.0 | ~5.5 / 4.52 | ~4.7 / 6.78 | ~5.5 / 8.75 | 1.0 |
| Hisense/Hitachi Hi-Therma 8 kW (R32) [10] | 6.52 | 3.47 / 4.76 | 2.44 / 6.65 | 1.48 / 9.58 | 0.9 (default) |

Notes:
- The ≈W30/27/24 water temperatures are the variable-outlet points of the EN 14825 low-temperature curve as I recall them from the standard. Please verify.
- Daikin's PDF tables lost some columns in text extraction, so its 08 and 09 cells show the range across the 04–08 and 09–16 families.
- Where Pdh (declared capacity) is well above the load at that point, Pdh is the unit's *minimum* capacity:
  - at +12 °C the load is 15% of Prated, i.e. 1.0–1.4 kW;
  - aroTHERM 7 kW: 3.7 kW; Daikin 9–16 frame: ~5.5 kW; aroTHERM split: 6.5 kW;
  - only the Hi-Therma gets close to the real load, at 1.48 kW.
- For reference, the Versati III 10 kW full-load ratings are COP 4.6 at A7/W35 (9.5 kW, 2.07 kW input) and 3.6 at A7/W45 [6]. Sibling note 08 adds 2.81 at A−7/W35. The Versati's own EN 14825 Pdh and Cdh values were not found. They would be on its HP Keymark certificate.

### 6. Control concepts used by manufacturers at low load

- **Proportional control on leaving water (Gree)** [4]:
  - frequency scales with (setpoint − outlet);
  - at minimum frequency with outlet above setpoint, the unit ramps down and stops;
  - restart when the error reaches ΔT-Heat (2–10 K, default 10 K; owner uses 4);
  - "Heat run time" of 1–10 min acts as a minimum run or stop delay in the standby zone;
  - an optional room-temperature mode modulates on room error with a 1–5 K band.
- **Degree-minute / energy-integral control** (Vaillant, NIBE, Viessmann) [30][32]:
  - the controller integrates (flow target − actual) over time;
  - it starts the compressor at a set deficit (Vaillant default −60 K·min) and stops when the integral returns to 0 or flow exceeds target + hysteresis (Vaillant default 7 K, range 0–15);
  - each run then delivers a defined amount of energy instead of reacting to an instantaneous error.
- **Fixed flow-temperature hysteresis with minimum run time** (Samsung): LWT hysteresis about 2 K above target, plus optional minimum compressor run and stop-on-ambient settings [25].
- **Research proposal** (OST simulation, UFH net-zero house) [22]:
  - estimate the floor's current heat output from its return temperature;
  - run the heat pump at the operating point that delivers that output most efficiently;
  - keep the UFH pump flow constant so lower output gives lower flow temperature;
  - variable speed gained up to 30% COP over the simulation;
  - deliberately PV-led heating raised indoor temperatures and *reduced* system efficiency.

### 7. Own HeatpumpMonitor.org analysis: method (for reproduction)

**Data.** Public endpoints [1]:
- `/system/list/public.json` (metadata, 859 systems);
- `/system/stats/last365` (per-system annual aggregates, including `combined_starts` and `running_*`);
- `/system/stats/daily?id=N` (daily CSV per system).

**Cross-section filter.** Air source; at least 300 days of data; elec/heat/flow/outdoor data quality ≥ 90%; COP between 1.5 and 8. That leaves 482 systems. Median outdoor temperature 7.7 °C, median running flow temperature 34.4 °C, median COP 3.88, median 47.9% of Carnot.

**Within-system filter.**
- Systems: the first 170 IDs, air source, at least 60 qualifying days. 62 systems.
- Days: at least 90% data, quality ≥ 90%, outdoor temperature −5 to +15 °C, ≥ 3 kWh of heat, at least one start, no immersion heater, no cooling, no data errors.
- Model: linear regression per system of % of Carnot on starts/day, outdoor temperature and output fraction. Plus deviations from each system's own mean within 2 K outdoor bins.
- The COP-versus-flow-temperature regression used the 26 systems that report space heating separately (space-heating COP on flow, outdoor temperature and starts).

**Caveats.**
- Observational data: hot days and cycling days are not randomised.
- Mostly UK, mostly radiators, enthusiast owners.
- The starts definition and the HPM Carnot reference are HPM's own; I did not verify them.
- Mean outdoor temperature is milder than in Lithuania.

## What this means for controlling this house

Context:
- Slab underfloor heating with a time constant of ~33–47 h.
- 9.5 kW-rated Versati, minimum ~3.7–3.8 kW against a 1.7 kW load at +10 °C.
- Flow setpoint written over Modbus.
- Restart when setpoint − outlet ≥ ~4 K.
- Firmware frequency is proportional to the leaving-water error.

**A. Treat the flow setpoint as a power command, and stop sending large ones. Confidence: high on direction, medium on size.**
- Writing a setpoint 4–6 K above the outlet tells the firmware to run fast [4]. That is where the ~3 kW, COP ~2.7–3 bursts come from.
- **Rule A1: enable the power limit (unit setting).** Set C/P limit = Power limit at **~1.2–1.6 kW** whenever outdoor is above about −3 °C. Raise it to 3–5 kW, or switch it off, in cold spells and for hot-water reheats if needed. See `08-gree-versati.md` for the register (Word 43).
  - Expect electrical draw during space heating ≤ the cap.
  - Expect COP during formerly-burst hours to rise from ~2.7–3 to ~4–4.5 at +2 °C (from comparable units' A2/W30 COPs [8–12]).
  - Test: alternate days with cap and without cap at matched outdoor temperatures, and compare daily heat ÷ electricity.
- **Rule A2: "start then trim" if a cap is not enough.** After a start is detected (compressor frequency or electrical draw), within 1–2 min rewrite the setpoint to the current outlet + 1–1.5 K. Then raise it by ≤ 0.5 K per 10–15 min as the return warms, so the error stays small and frequency stays near minimum.
  - This needs a loop of about 1–5 min, not 30 min.
  - First log the frequency-versus-error mapping (Words 142/143 per note 08) to confirm the gain and the stop threshold.
  - Confidence: medium. It relies on the documented proportional behaviour [4], not on tests of this unit.
- **Avoid:** large setpoint jumps without a cap, and quiet mode as a substitute. Quiet mode lowers capacity but reportedly causes frequent defrosts in humid weather (note 08).

**B. In mild weather, control energy (run time), not water temperature. Confidence: medium-high.**
- Above the balance temperature (~−2 °C ± 3 K, where P_min ≥ load), the unit cannot run continuously. Its flow temperature during a run is then set by how hard it must push ~3.7 kW into the slab, not by the weather.
- **Rule B1: fixed, minimal run setpoint.** During a run, use one fixed, minimal setpoint: T_set ≈ T_room + P_min / K_em + ΔT_water/2.
  - K_em is the floor's measured heat-transfer conductance, kW/K.
  - Measure it from steady runs as K_em = Q / (mean water temperature − T_room).
  - Tune empirically: lower the run setpoint by 1 K a day until runs start ending by overshoot within 60–90 min, then go back up 1 K.
  - Because the slab absorbs heat near the pipes, the usable value may be lower than a steady-state estimate suggests.
- **Rule B2: deliver the day's heat as a number of minimum-speed hours.** Hours = Q_day ÷ P_min: about 20 h at +2 °C, 17 h at +5 °C, 12 h at +10 °C, 7 h at +15 °C (my calculation).
  - Split them into **2–5 runs of ≥ 2–3 h**.
  - Slab mean temperature then moves only ~0.5–1 K per run (6.6 kWh/K storage).
  - Expected direct cycling penalty: under 1% at fewer than ~15 starts/day [1].
- **Rule B3: correct slowly.** Correct room-temperature error over 12–24 h, not 1–2 h. With τ ≈ 40 h, short corrections cannot improve comfort and only create bursts.
- **Rule B4: place runs well.** Where possible, put runs in the warmer hours and the PV window. This is outside my topic, but it fits naturally with run-time control: a warmer source gives higher COP and higher minimum output [8], so fewer hours are needed.

**C. In cold weather, modulate continuously on a low curve. Confidence: high.**
- Below the balance temperature, run continuously.
- Use a gently sloped weather curve at the lowest flow temperature that holds 22 °C. Typical slab values are about 30–34 °C at −20 °C, depending on K_em.
- Change the setpoint in ≤ 0.5 K steps, at most every 30–60 min, so the inverter settles near the needed frequency instead of oscillating between stop and fast restart.

**D. Restart hysteresis and minimum run time. Confidence: medium-low; test.**
- Once rules A and B are in place, HA decides starts anyway.
- A **small ΔT-Heat (2–3 K)** reduces the opening error and therefore the start frequency.
- A large ΔT-Heat (6–10 K) prevents self-restarts between HA's planned runs.
- Pick the variant matching the controller (see the options in note 08). Both are acceptable *if the power cap is active*.
- Set **Heat run time to 10 min**, the maximum [4]. This removes sub-10-minute runs, the only regime with clearly measurable direct losses [1][14].

**E. Hot water. Confidence: medium.**
- Hot-water runs need higher condensing temperatures and probably high frequency. After a hot-water run, space heating restarts with a big error.
- Schedule hot water once a day in the warmest or PV hour.
- Return to space heating with a trimmed setpoint (rule A2) or under the power cap.
- Keep legionella disinfection on the electric heater, weekly.

**F. What to measure before and after. All cheap from Modbus plus the existing meters.**
1. Compressor frequency (set and actual) against setpoint − outlet: confirms the proportional gain and the stop margin.
2. Minimum steady output against outdoor temperature over a season. Expect ~3 kW near 0 °C, rising to ~4 kW at +10…+15 °C, by analogy with [8][9].
3. Off-time draw split into pump and crankcase heater (coils listed in note 08). If the pump runs continuously in standby, stopping it between runs may be worth more than any cycling tweak.
4. Daily COP against (a) average flow temperature during runs, (b) starts per day and (c) the share of heat delivered above 2 kW of electrical input. My prediction:
   - (a) about −2%/K [1];
   - (b) roughly zero below 15 starts/day [1];
   - (c) strongly negative.

**Expected gain (rough).** If runs average 4 K cooler (≈ +9.5% COP [1]) and the bursts disappear (+5–20%, depending on their current share of heat), mild-weather electricity could fall by about **10–25%**.
- Confidence: medium-low. The burst share is unknown, and comparable-unit COPs stand in for Versati data.

## Contradictions and open questions

1. **How large is the real cycling penalty?** Four answers conflict:
   - EN 14825 declarations (Cdh 0.94–1.0) say almost nothing [8–12];
   - a field fit says Cc ≈ 0.80, i.e. large losses at low load [13];
   - HeatpumpMonitor within-system data say small, except below ~30-minute cycles [1];
   - lab work says it depends on water volume and inertia [14].

   Likely reconciliation:
   - the 0.80 fit mixes cycling with standby, controls and defrost on a 2013 unit in an office;
   - the HPM sample is well-tuned modern units;
   - Cdh in the standard is defined from off-power only [13].

   Not resolved. For this house the slab's large inertia argues for the small end, but only if runs are long.

2. **Where is the COP optimum?**
   - Monotonic improvement down to the lowest speed: KTH, Hokkaido, Shunde labs [16][18][19]; Fahlén with scaled fans [15].
   - A mid-range peak at 30–50%: Carel chart and Viessmann datasheet [20]; Fahlén with fixed fans [15]; forum [30].
   - Field: flat 30–90%, falling below 30% [1][21].

   Reconciliation: auxiliary power and motor efficiency at low load decide the answer. That is why the field picture is flat-then-dropping. For the Versati, minimum (~39%) is inside the good band either way. Not tested on a Versati.

3. **Gree's compressor range.** "Down to 10 Hz" (Czech catalogue [7]) versus 20–120 Hz (another Gree document cited in note 08). The measured minimum output (~3.7 kW) suggests the space-heating floor is well above 10 Hz, or that displacement per revolution is large. Log Words 142/143.

4. **Typical minimum outputs.** An installer's "15–20% of nameplate" [31] contradicts the community median of ~34% [2]. Marketing claims such as aroTHERM plus "25–100%" [30] sit beside a measured 47% for the 7 kW [2]. Test conditions in [2] are not standardised.

5. **What the Versati's ΔT-Heat and "standby zone" really are.** The manual labels the parameter inconsistently and gives a 10 K default [4][5]. The stop margin above setpoint is undocumented. The owner's data imply restart hysteresis.

6. **Does the power limit also cap hot water, defrost recovery or oil return?** If it caps hot water, reheats get slower, which may be acceptable or not. Unknown.

7. **Low speed and defrost in humid 0–5 °C weather.**
   - Lower capacity reduces evaporator temperature difference and frosting [15].
   - Daikin's capacity data show a defrost dip at −7…+2 °C [11][12].
   - Quiet mode reportedly *increased* defrosts on a Versati (note 08). That is probably a fan-speed effect, not a compressor-speed effect.
   - Whether a power cap changes defrost frequency is unknown. Measure it.

8. **No Versati-specific EN 14825 or field data.** Its Keymark certificate (Pdh at +12 °C, Cdh, P_SB, P_CK) was not retrieved. HeatpumpMonitor has one Gree system, a 7 kW Flexx, and no Versati [1].

9. **The HPM sample may not transfer.** It is UK-centred and radiator-heavy, with a mean outdoor temperature of 7.7 °C. The Lithuanian climate is colder and more humid, and this house has a slab.

10. **Not covered because the search budget ran out:**
    - Uhlmann and Bertsch's measured start-up and shut-down losses;
    - Dongellini and Morini's air-to-water cycling losses as a function of modulation range;
    - the EN 14825 2023 amendment on the degradation coefficient;
    - ISO 21978 Cd determination;
    - Polish, Swedish, Dutch and Lithuanian community sources.

## Sources

1. HeatpumpMonitor.org public data. My analysis of the system list, last-365-day stats and daily stats; 482 systems cross-section, 62 within-system. OpenEnergyMonitor community, 2026. https://heatpumpmonitor.org/ (endpoints `/system/list/public.json`, `/system/stats/last365`, `/system/stats/daily?id=N`). Field data. Contributed starts-versus-efficiency, flow-temperature sensitivity, output-fraction versus % of Carnot, and off-time power.
2. HeatpumpMonitor.org heat pump model database with minimum and maximum output tests. OpenEnergyMonitor, 2026. https://heatpumpmonitor.org/heatpump/list. Field data (community tests). Contributed measured minimum and maximum outputs for 45 model sizes.
3. "HeatpumpMonitor.org heat pump database: minimum modulation tests." Trystan Lea et al., OpenEnergyMonitor forum, c. 2025. https://community.openenergymonitor.org/t/heatpumpmonitor-org-heat-pump-database-minimum-modulation-tests/29132. Forum / field. Contributed test context, Vaillant 10 kW range of 5.9–9.6 kW, and the minimum-flow × 5 K rule.
4. "Air-to-water Heat Pump Split Versati (Versati III) Service Manual." Gree Electric Appliances, c. 2022. https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iii/versati%20iii%20split%20%E2%80%93%20service%20manual.pdf. Manufacturer. Contributed proportional frequency control and stop logic, ΔT-Heat, heat run time, power/current limit, quiet mode, room control mode, capacity correction tables, ratings, and crankcase preheat.
5. "Versati III All-in-one Service Manual." Gree, c. 2022. https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iii/versati%20iii%20all%20in%20one%20%E2%80%93%20service%20manual.pdf. Manufacturer. Confirmed the same parameter set (ΔT-Heat default 10 K, C/P limit, heat run time).
6. "Versati III Split" product sheet (Gree Poland catalogue pages). Gree, 2022. https://cdn.shopify.com/s/files/1/0586/0347/0948/files/Gree_Warmepumpe_Versati_III_Split_VO8S3_8_kW_3PH.pdf. Manufacturer. Contributed ratings: 10 kW is 9.5 kW at A7/W35, COP 4.6 (W35) and 3.6 (W45); working ranges.
7. "GREE Versati III katalog 2023/2024" (Czech). Slovklima, Gree distributor, 2023. https://www.slovklima.sk/wp-content/uploads/2023/05/Slovklima_gree-katalog-versatiii-2023_2024-cz.pdf. Manufacturer claim. Contributed the "down to 10 Hz" (G10) claim, the two-stage rotary compressor with interstage injection, and the EC fan.
8. HP KEYMARK summary, Vaillant aroTHERM plus VWL 65/75/85/6 A 230V. EHPA / VDE, 2022. https://downloads.vaillant.cz/downloads/certifik-ty/certifikat-hp-keymark-arotherm-plus-svt24748-vwl-75-6-a-230v-2585793.pdf. Lab (certified EN 14825). Contributed Pdh/COP/Cdh at +2/+7/+12 °C, minimum capacity versus outdoor temperature, and P_off/P_TO/P_SB/P_CK.
9. HP KEYMARK summary, Vaillant aroTHERM split VWL 105/5 AS + 127/5 IS. EHPA, 2022. https://downloads.vaillant.cz/downloads/certifik-ty/certifikat-hp-keymark-arotherm-split-svt23663236642366723668-vwl-105-5-as-230vvwl-125-5-as-230vvwl-105-5-asvwl-125-5-as-2585797.pdf. Lab (certified). Contributed a 10 kW-class minimum of 5.7–6.5 kW, Cdh 0.98–0.99, and standby power.
10. HP KEYMARK report, Hi-Therma Monobloc 8kW (AHZ-080HCDS1). Hisense Hitachi / BRE, 2022. https://merkur.si/datoteke/katalogi/energija/certifikati/Keymark_Report-Hi-Therma_Monobloc_8kW.pdf. Lab (certified). Contributed a wide-turndown example (1.48 kW at +12 °C, COP 9.58) and default Cdh 0.9.
11. "Daikin Altherma low temperature monobloc EBLA04-08E(3)V3 Technical Data" (EEDEN22). Daikin, 2022. https://community.openenergymonitor.org/uploads/short-url/8pHE4EhJOnY9d2zlF6RjBtjYQXs.pdf. Manufacturer (certified data). Contributed EN 14825 points, Cdh 1.0, standby 10 W, and maximum-capacity graphs with the defrost dip.
12. "Daikin Altherma low temperature monobloc EBLA09-16D Technical data book" (EEDEN20). Daikin, 2020. https://community.openenergymonitor.org/uploads/short-url/s2W769V1TIXQmvyxCHY26QE1725.pdf. Manufacturer. Contributed the 9–16 kW frame's minimum capacity (~4.7–5.5 kW in mild weather), COPs and standby 23 W.
13. Piechurski K., Szulgowska-Zgrzywa M., Danielewicz J. "Quasi-dynamic model of the energy efficiency degradation coefficient for an air-to-water heat pump." E3S Web of Conferences 44, 00139, 2018. https://www.e3s-conferences.org/articles/e3sconf/pdf/2018/19/e3sconf_eko-dok2018_00139.pdf. Field data / paper. Contributed the EN 14825 Cc definition and formula, measured Cc 0.96–0.99 versus default 0.9, and a field-fitted Cc of 0.80.
14. Fuentes E., Waddicor D.A., Salom J. "Improved characterization of water-to-water heat pumps' part load performance." REHVA Journal summary of Applied Energy 179 (2016) 778–789. https://rehva.eu/rehva-journal/chapter/improved-characterization-of-water-to-water-heat-pumps-part-load-performance. Lab. Contributed start-up timing (heat 42–60 s, power < 20 s), the inertia dependence, Cd ≈ 0.22, and EN 14825 errors up to 12%.
15. Fahlén P. "Capacity control of heat pumps." REHVA Journal 49(5), October 2012. https://www.rehva.eu/rehva-journal/chapter/capacity-control-of-heat-pumps. Paper (simulation of a rotating air-to-air heat pump). Contributed COP at f = 1/0.5/0.2 for three system designs, motor-loss mechanisms, the 80–90% of hours below half load figure, and reduced frosting.
16. Awan U.K. "Experimental Analysis of Variable Capacity Heat Pump System Equipped with Vapour Injection and Permanent Magnet Motor." MSc thesis, KTH, 2012. https://www.diva-portal.org/smash/get/diva2:565195/FULLTEXT01.pdf. Lab. Contributed COP −32% from 30 to 90 Hz, inverter and electromechanical losses, efficiency peak at 60 Hz, and the literature review.
17. Madani H., Ahmadi N., Claesson J. et al. "Experimental analysis of a variable capacity heat pump system focusing on the compressor and inverter loss behavior." Purdue Refrigeration and Air-Conditioning Conference, 2010 (IIR FRIDOC record). https://iifiir.org/en/fridoc/experimental-analysis-of-a-variable-capacity-heat-pump-system-focusing-27509. Lab (abstract). Contributed COP down up to 30% with speed, isentropic optimum near 50 Hz, and pressure ratio 2.7–5.8.
18. Blanco D.L., Nagano K., Morimoto M. "Experimental study on a monovalent inverter-driven water-to-water heat pump with a desuperheater for low energy houses." Applied Thermal Engineering 50(1) 826–836, 2013. https://eprints.lib.hokudai.ac.jp/repo/huscap/all/52254/ATE50-1_826-836.pdf. Lab. Contributed best COP at 45 Hz and the COP link to pressure ratio and volumetric efficiency.
19. Wu Z., Xu Y., Zhang X. "Study on Performance Factors of Variable Frequency Heat Pump Water Heater." AEECE-2015, Atlantis Press, 2015. https://www.atlantis-press.com/article/25839456.pdf. Lab. Contributed: R290 COP rises linearly as frequency falls 90 → 40 Hz.
20. Afjei T. (FHNW). "Messung und Bewertung von drehzahlgeregelten Wärmepumpen" (talk, Uni Innsbruck), 2018. Includes EFKOS project results, a Viessmann Vitocal 300-A datasheet ratio and a Carel (Lamanna) chart. https://uibk.ac.at/media/filer_public/4d/8e/4d8e0863-d8c6-47a6-a016-6b623af5cc0c/afjei_simulationsmodelle.pdf. Paper (simulation validated on Vaillant lab data) plus manufacturer charts. Contributed condenser difference versus load, COP ratio versus part load, the 31.0 versus 35.2 °C flow temperatures, and inverter-versus-on/off COP curves.
21. Repke T., supervised by Bertsch S. "Teillastverhalten von invertergeregelten Wärmepumpen – Analyse des Carnot-Gütegrads im Feldbetrieb" (thesis abstract). OST, 2026. https://www.ost.ch/files/daten/abstracts/pdf/990f3d2f-cae1-4a03-a95e-8e279b8902f2.pdf. Field data (abstract only). Contributed the Carnot-efficiency collapse at low part load that standard points miss.
22. Rominger L., supervised by Wemhöner C. "Auslegung von drehzahlgeregelten Wärmepumpen für Netto-Nullenergiegebäude" (MSc abstract). OST, 2019. https://www.ost.ch/fileadmin/dateiliste/97_daten/abstracts/475ab600-c293-4efd-82a2-f3e86b5a4aef.pdf. Simulation. Contributed up to 30% COP gain from variable speed, the oversizing-to-cycling trade-off, PV-led heating lowering efficiency, and the return-temperature-based efficient-point control.
23. "HEM-TP-12 Heat pump methodology" (Home Energy Model technical paper). UK DESNZ, 2025–26. https://assets.publishing.service.gov.uk/media/6583f139ed3c34000d3bfcc6/hem-tp-12-heat-pump-methodology.pdf. Standards-based methodology. Contributed minimum-modulation handling, the EN 15316-4-2 on/off inertia formula, off/standby/crankcase accounting and system boundaries.
24. "Lab Test of a Variable Speed Air-to-Air Multi-Function Heat Pump." ETCC (California). https://www.etcc-ca.com/reports/lab-test-variable-speed-air-air-multi-function-heat-pump. Lab (summary page). Contributed COP 4.90 at intermediate versus 3.96 at full speed, heating at 8 °C.
25. "Heat pump demand cycling vs compressor load cycling." OpenEnergyMonitor forum, c. 2025. https://community.openenergymonitor.org/t/heat-pump-demand-cycling-vs-compressor-load-cycling/29277. Forum. Contributed type 1 versus type 2 cycling, Samsung hysteresis and minimum-run settings, and flash-cooling losses after stops.
26. "Concerned about Daikin modulation." OpenEnergyMonitor forum, c. 2025. https://community.openenergymonitor.org/t/concerned-about-daikin-modulation/29340. Forum. Contributed Daikin 9/11 kW minimum input of ~810–825 W, minimum output of 3–5 kW, and cycling at 15 °C.
27. "Improve efficiency: Turn the heat pump off" (post 26). OpenEnergyMonitor forum, 2022. https://community.openenergymonitor.org/t/improve-efficiency-turn-the-heat-pump-off/13381/26. Forum anecdote. Contributed: forced continuous running gave +28% power, COP 3.27 → 3.04.
28. "How to reduce cycling?" (page 6). OpenEnergyMonitor forum, 2024–25. https://community.openenergymonitor.org/t/how-to-reduce-cycling/25251?page=6. Forum anecdote. Contributed: 8 cycles/h at COP ~2.5 versus near-continuous at COP ~4.
29. "Volume simulator with heat pump COP." OpenEnergyMonitor. https://openenergymonitor.org/tools/volume_sim_cop. Tool / blog. Contributed the minimum-volume formula: minimum output × minimum on-time ÷ (c × ΔT).
30. "What is energy integral?" (page 2). BuildHub forum. https://forum.buildhub.org.uk/topic/17899-what-is-energy-integral/page/2. Forum. Contributed Vaillant's energy integral (−60 K·min default, 7 K hysteresis, 0–15 K range), the −120 experience, and the "25–100%" modulation claim.
31. "Performance of heat pumps in mild weather" (page 2). Renewable Heating Hub forum. https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/performance-of-heat-pumps-in-mild-weather/paged/2/. Forum. Contributed the 15–20% installer claim, "no range above 3:1", and Hitachi 2.1–11 kW.
32. "Which 6kW to 8kW ASHP can modulate down the lowest?" Renewable Heating Hub forum. https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/which-6kw-to-8kw-ashp-can-modulate-down-the-lowest/. Forum. Contributed: degree-minute control (Vaillant, Viessmann, Nibe) matters more than the minimum figure.
33. "Minimum ASHP outputs?" (page 3). Renewable Heating Hub forum. https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/minimum-asph-outputs/paged/3. Forum. Contributed a Mitsubishi example of 3–4 starts/h at 33–34 °C flow.
34. "Samsung HT Quiet R32 8kW emoncms COP vs simulated COP and zigzag pattern." OpenEnergyMonitor forum, 2024–25. https://community.openenergymonitor.org/t/samsung-ht-quiet-r32-8kw-emoncms-cop-vs-simulated-cop-and-zigzag-pattern/27385. Forum. Contributed ~25 Hz giving ~5 kW, Carnot factors of 0.35–0.46, and control oscillation.
35. "Reasons for Ecodan overshooting target fixed flow temperature" (post 7). OpenEnergyMonitor forum. https://community.openenergymonitor.org/t/reasons-for-ecodan-overshooting-target-fixed-flow-temperature/25489/7. Forum. Contributed: an 11.2 kW Ecodan has a 5–6 kW minimum; 2–3 cycles/h considered acceptable; emitters must absorb the minimum output.
