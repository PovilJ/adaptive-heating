# Gap G1: What is the part-load performance map of this exact Versati model: EN 14825/Keymark declared Pdh and COPd at points A-D (−7/+2/+7/+12 °C) for the 35 °C and 55 °C applications, the Cdh value, and how minimum heat output and minimum electrical input change with outdoor and water temperature?

> Research date: 2026-11-06. Follow-up researcher for gap G1.
>
> **Method.** The shared web-search budget was already used up when this task started: the first WebSearch call was refused, so **0 searches were run**. I did not route around the limit. Instead I fetched primary sources directly:
> - the HP KEYMARK database, which holds the BRE-certified EN 14825 data sets. I downloaded every Versati 8/10 kW subtype page (15 subtype pages, 8 of them relevant) and parsed the raw tables locally;
> - one BRE certificate PDF;
> - the Eurovent certificate page;
> - the EUR-Lex transitional-methods Communication;
> - a Gree distributor catalogue (Czech).
>
> **Evidence quality.** All Pdh/COPd/Cdh numbers below are **certified lab data** (EN 14825 tests by Intertek, certified by BRE). Two kinds of number are *not* certified:
> - The EN 14825 leaving-water temperatures I attach to each point (W34/30/27/24 and so on) are recalled from the standard. Neither the database nor EUR-Lex prints them. Treat them as medium confidence.
> - Everything labelled "calc" is my own arithmetic.
>
> I did not read the repository's code or docs, and did not touch Home Assistant.

## Summary

1. **The Versati's EN 14825 data now exist for every 8/10 kW generation** [2–9].
   - The all-in-one (AIO) and split units with the same outdoor unit share identical data. The 10 kW AIO G2 (GRS-CQ10PdG/NhH2-E) and the split G2 + tank have the same certified numbers [2][7].
   - Likeliest owner unit: Versati III AIO 10 kW. Depending on the nameplate suffix (NhH / NhH2 / NhH3), its data are in certificates 041-K004-09/-17 (G1), -11/-16 (G2) or -31/-26 (G3).

2. **Part-load COP at the low-temperature (35 °C) application, average climate, 10 kW AIO** [2][4]:

   | Point | G2 (NhH2-E) | G3 (NhH3-E) |
   |---|---|---|
   | A −7 / ≈W34 | 7.70 kW, COP 2.87 | 7.76 kW, COP 3.15 |
   | B +2 / ≈W30 | 4.80 kW, 4.34 | 4.90 kW, 4.59 |
   | C +7 / ≈W27 | 3.10 kW, 6.58 | 3.04 kW, 5.67 |
   | D +12 / ≈W24 | 3.70 kW, 8.37 | 3.28 kW, 7.34 |

   These are lab steady-state values. They are far above anything measured in the field, mainly because the water is very cold (W24–30).

3. **Same points at the 55 °C application (G3)** [4]: −7/≈W52 7.65 kW at COP 2.29 · +2/≈W42 4.66 kW at 3.24 · +7/≈W36 3.08 kW at 4.17 · +12/≈W30 3.21 kW at 5.24.

4. **Cdh is 0.93–0.99 on every Versati certificate** [2–9]:
   - −7 °C: 0.99. +2 °C: 0.97–0.98. +7 °C: 0.95–0.97. +12 °C: 0.93–0.97.
   - The declared value matches **1 − P_off / P_el** to two decimals (calc). Example: 25 W off-power on 0.45 kW gives 0.944, and 0.94 is declared.
   - So Cdh only accounts for the 25 W standby draw. It **does not include start-up losses**, and cannot be used to price cycling.

5. **The minimum heat output rises with outdoor temperature**, as on the aroTHERM [2][4][6]. The lab uses the lowest step where Pdh is far above the load. Lowest declared capacity:

   | Generation | ≈+2 °C | ≈+7 °C | ≈+12 °C |
   |---|---|---|---|
   | G2 | ≤ 3.1–3.2 kW | 3.1–4.3 kW | 3.7–5.1 kW |
   | G1 (3-phase) | 3.2 kW | 3.7–3.9 kW | 4.1–4.4 kW |
   | G3 | 3.2–3.3 kW (near the load) | 2.4–2.5 kW | 2.8–3.3 kW |

   The owner's measured 3.7–3.8 kW sits inside the G1/G2 band for +7…+12 °C.

6. **The minimum electrical input mostly tracks water temperature, not outdoor temperature** (calc from the low-capacity points) [2][4]:
   - **≈0.44–0.49 kW** at W24–25;
   - ≈0.6–0.7 kW at W28–30;
   - ≈0.75–1.0 kW at W32–37;
   - same pattern at +7 and +12 °C.

   The compressor draws roughly 0.45 kW at its floor, plus about 0.03 kW for every kelvin of extra water temperature.

7. **Across all 60+ certified points, the unit runs at a Carnot efficiency of ≈0.45–0.55** (calc, using T_cond = LWT+2 and T_evap = T_out−6) [2][4][14].
   - Mid-speed points: 0.50–0.54.
   - Maximum-speed and minimum-speed points: 0.42–0.49.
   - Simulator rule: **COP ≈ 0.50 × T_cond/(T_cond − T_evap)**, minus about 10% at either end of the speed range.

8. **Water temperature is the dominant lever, and it matters more in mild weather.** Same unit, same output, only LWT changed (G3, average climate) [4]:

   | Outdoor | LWT change | COP change | Penalty |
   |---|---|---|---|
   | −7 °C | 34→52 °C | 3.15 → 2.29 | ≈1.7%/K |
   | +2 °C | 30→42 °C | 4.59 → 3.24 | ≈2.9%/K |
   | +7 °C | 27→36 °C | 5.67 → 4.17 | ≈3.3%/K |
   | +12 °C | 24→30 °C | 7.34 → 5.24 | ≈4.8%/K |

   The owner's 31–39 °C setpoints in +5…+10 °C weather therefore cost about 3–4% of electricity per kelvin.

9. **Running hard costs efficiency** [4][7]:
   - At +2 °C, G3 makes 9.55 kW at ≈W35 for 2.82 kW electric (COP 3.39). At ≈W30 it makes 4.90 kW for 1.07 kW (COP 4.59).
   - The owner's ~3 kW "catch-up" draw at +2 °C is therefore near full speed. It costs ≈26% more electricity per kWh than mid-speed: ~10% from flow temperature and ~15% from speed (calc).

10. **Standby and auxiliary declarations are small** [2–9]:
    - Off-mode, thermostat-off and standby power (P_off, P_TO, P_SB): 25 W each.
    - Crankcase heater (P_CK): 25 W (G1/G2) or 0 W (G3).
    - Hot-water standby is much larger, at 36–132 W depending on tank and test [2][4][5][7].

11. **Cold end** [2][4]:
    - Average-climate design point (Tbiv −7 °C) is 7.7 kW. At TOL −10 °C: 7.1 kW, COP 2.6–2.8 (W35).
    - Colder climate (TOL −22 °C): G2 gives 5.6 kW at COP 1.67 (W35). G3 declares only 3.15 kW at COP 1.43 (W35, low-temperature application).
    - At Lithuanian −20 °C lows, expect ≤4–6 kW from the compressor. The backup heater will cover the rest.

12. **EN 14511 nominal ratings** [2–4]:
    - 10 kW AIO at A7/W35: 10.0–10.2 kW, COP 4.76–5.0.
    - At the 55 °C application: 8.6–9.5 kW, COP 2.18–3.04, depending on generation.
    - The G3 COP of 2.18 at the 55 °C rating point is notably low.

13. **The marketing claim of "down to 10 Hz" (G10 technology) [13] does not show up** in any declared capacity. No Versati 8/10 certificate declares less than 2.4 kW of heat.

## Detailed findings

### 1. Which certificates belong to this house

The HP KEYMARK database lists Gree as certificate holder 2441. It has about 40 subtypes, of which 15 are Versati 8–22 kW [1]. Relevant 8/10 kW ones (models / registration / date):

| Generation (Keymark name) | Models (10 kW) | Reg. no. | Date | Data |
|---|---|---|---|---|
| Split G1 8-10kW | GRS-CQ10Pd/NhH-E (+tank) | 041-K004-09 | 2021-01 | **55 °C only** (average climate) [5] |
| Split G1 8/10kW | GRS-CQ10Pd/NhH-M (+tank), 3-phase | 041-K004-17 | 2022-11 | 35+55, 3 climates [6] |
| AIO G2 8-10kW | GRS-CQ10PdG/NhH2-E | 041-K004-11 | 2022-01 | 35+55, 3 climates [2] |
| AIO G2 8/10kW | GRS-CQ10PdG/NhH2-M | 041-K004-20 | 2022-11 | 35+55, 3 climates [3] |
| Split G2 8/10kW | GRS-CQ10Pd/NhH2-E + SXTVD300LC/B-E | 041-K004-16 | 2022-10 | identical to [2] [7] |
| AIO G3 8/10kW | GRS-CQ10PdG/NhH3-E/-M | 041-K004-31 | 2025-06 | 35+55, 3 climates [4][10] |
| Split G3 8/10kW | GRS-CQ10Pd/NhH3-E/-M (+tank) | 041-K004-26 | 2025-09 | identical to [4] [8] |
| Monobloc G3/G4 8/10k | GRS-CQ10Pd/NhG3/NhG4 (+tank) | 041-K004-13 | 2022-10 | 35+55 [9] |

- All are R32. The G3 AIO holds 1.75 kg [4].
- Testing basis for G3 is EN 14511:2022 and EN 14825:2022. The test lab is Intertek Guangzhou [4][10].
- The 2023/24 Czech catalogue sells the AIO as **NhH2**, rated 10.0 kW at COP 4.8 at A7/W35 [13].
- Note 08 named the indoor unit GRS-CQ10PdG/NhH-E(I), which is G1. The G1 single-phase certificate has **no 35 °C data**. If the nameplate says NhH (no digit), use the G1 3-phase [6] or G2 [2] numbers as the nearest proxy (inference).

### 2. Certified part-load tables (10 kW, Pdh kW / COPd / Cdh)

Water temperatures are the EN 14825 variable-outlet values as I recall them. Load = Prated × part-load ratio (PLR, calc). "**min**" marks points where Pdh is more than 5% above the load, so the unit is cycling and Pdh is the lowest capacity step tested.

**G3 AIO GRS-CQ10PdG/NhH3-E [4]**

| Climate / application | −7 °C | +2 °C | +7 °C | +12 °C |
|---|---|---|---|---|
| Average, 35 (Prated 9) | W34: 7.76 / 3.15 / 0.99 | W30: 4.90 / 4.59 / 0.98 | W27: 3.04 / 5.67 / 0.95 | W24: 3.28 / 7.34 / 0.94 **min** (load 1.38) |
| Average, 55 (Prated 9) | W52: 7.65 / 2.29 / 0.99 | W42: 4.66 / 3.24 / 0.98 | W36: 3.08 / 4.17 / 0.97 | W30: 3.21 / 5.24 / 0.96 **min** |
| Colder, 35 (Prated 8) | W30: 5.22 / 3.62 / 0.98 | W27: 3.27 / 4.29 / 0.97 (load 2.95) | W25: 2.53 / 5.31 / 0.95 **min** (load 1.89) | W24: 3.33 / 6.84 / 0.95 **min** (load 0.84) |
| Colder, 55 (Prated 8) | W44: 5.25 / 2.39 / 0.99 | W37: 3.19 / 3.39 / 0.97 | W32: 2.43 / 4.94 / 0.95 **min** | W28: 3.26 / 5.61 / 0.96 **min** |
| Warmer, 35 (Prated 10) | – | W35: 9.55 / 3.39 / 0.99 (full) | W31: 5.83 / 5.18 / 0.98 | W26: 2.78 / 7.48 / 0.93 (load 2.86) |
| Warmer, 55 (Prated 10) | – | W55: 9.51 / 2.47 / 0.99 | W46: 5.84 / 3.56 / 0.98 | W34: 2.76 / 5.15 / 0.95 |

Other G3 data [4]:
- SCOP is 4.63 (35) / 3.33 (55) in average climate, 3.8 / 2.85 in colder and 5.95 / 4.13 in warmer.
- Tbiv: −7 (average), −15 (colder), +2 (warmer). TOL: −10 / −22 / +2. WTOL 65 °C.
- P_off = P_TO = P_SB = 25 W, P_CK = 0 W.
- The 3-phase -M variant is the same within ±0.2 COP [4].

**G2 AIO GRS-CQ10PdG/NhH2-E [2]** (same values for split G2 + tank [7])

| Climate / application | −7 °C | +2 °C | +7 °C | +12 °C |
|---|---|---|---|---|
| Average, 35 (Prated 9) | 7.70 / 2.87 / 0.99 | 4.80 / 4.34 / 0.98 | 3.10 / 6.58 / 0.95 | 3.70 / 8.37 / 0.94 **min** |
| Average, 55 (Prated 8) | 6.90 / 2.12 / 0.99 | 4.20 / 3.09 / 0.98 | 4.30 / 4.34 / 0.97 **min** | 4.90 / 5.91 / 0.97 **min** |
| Colder, 35 (Prated 8) | 5.20 / 3.25 / 0.98 | 3.20 / 4.31 / 0.97 | 4.30 / 6.11 / 0.96 **min** | 4.90 / 7.30 / 0.96 **min** |
| Colder, 55 | 5.30 / 2.42 / 0.99 | 3.10 / 3.23 / 0.97 | 4.20 / 4.78 / 0.97 **min** | 4.80 / 5.91 / 0.97 **min** |
| Warmer, 35 (Prated 9) | – | 8.80 / 3.15 / 0.99 | 5.80 / 4.86 / 0.98 | 5.10 / 7.18 / 0.96 **min** |
| Warmer, 55 | – | 9.00 / 2.48 / 0.99 | 5.90 / 3.56 / 0.98 | 5.20 / 5.30 / 0.97 **min** |

- SCOP 4.60 / 3.25 (average), 3.80 / 2.82 (colder), 5.50 / 4.10 (warmer).
- P_off = P_TO = P_SB = P_CK = 25 W.
- Colder-climate TOL −22 °C: 5.6 kW at COP 1.67 (35) and 3.3 kW at COP 1.22 (55).

**G1 3-phase split GRS-CQ10Pd/NhH-M [6]** (same values as AIO G2 -M [3])

- Average, 35 (Prated 9): 7.7 / 2.69 · 5.0 / 4.71 · 3.9 / 6.52 **min** · 4.4 / 7.03 **min**.
- Average, 55 (Prated 10): 8.6 / 2.25 · 5.2 / 3.36 · 4.2 / 4.71 **min** · 4.1 / 5.36 **min**.
- Colder, 35: 5.1 / 2.65 · 4.0 / 3.68 **min** · 3.8 / 4.84 **min** · 4.1 / 6.26 **min**.
- Cdh 0.95–0.99. SCOP 4.7 / 3.48.

**G1 single-phase split GRS-CQ10Pd/NhH-E [5]**, 55 °C application only:
- 6.91 / 2.12 · 4.22 / 3.09 · 4.27 / 4.34 **min** · 4.91 / 5.91 **min**.
- SCOP 3.25. P_CK 25 W. WTOL 60 °C.
- EN 14511 rating at the 55 °C application: 9.47 kW, 3.12 kW electric, COP 3.04.

**Monobloc G3 GRS-CQ10Pd/NhG3-E [9]**, for comparison: average 35 gives 8.0 / 2.90 · 4.6 / 4.41 · 4.8 / 5.89 · 3.2 / 6.97. Colder 35 at +7 gives **2.7 kW min** (COP 5.59).

**R290 monobloc 10 kW (NpG4) [11]**, for comparison:
- Average 35 gives 7.86 / 2.84 · 4.45 / 4.71 · 3.01 / 7.11 · **2.31 / 8.88** with Cdh 0.90.
- So the newer R290 platform turns down to about 2.3 kW.

### 3. What Cdh actually is on these units

- EN 14825 uses Cdh to scale COPd when the load ratio CR < 1. The bin COP is reduced by roughly CR / (Cdh·CR + 1 − Cdh) (standard formulation; see note 03).
- Gree's declared values match **Cdh = 1 − P_off / P_el(at Pdh)** at every point I checked (calc):
  - +12 °C: 0.025/0.44 → 0.943; declared 0.94 [2].
  - +7 °C: 0.025/0.47 → 0.947; declared 0.95 [2].
  - +2 °C: 0.025/1.11 → 0.978; declared 0.98 [2].
  - −7 °C: 0.025/2.68 → 0.991; declared 0.99 [2].
  - G3 gives the same pattern [4].
- Implication: the certified cycling penalty at +12 °C (CR = 1.38/3.28 = 0.42) is only ~8%, and it is purely the 25 W idle draw.
  - Start-up losses are invisible in the certificate: refrigerant redistribution, warming the heat-exchanger mass, and the 3–6 min firmware ramp described in note 08.
  - Their real size must come from field data (notes 03 and 12: field Cc ≈ 0.80) or from the owner's own logs.

### 4. Minimum heat output versus outdoor and water temperature

Lowest declared capacity at "min" points, and points close to the load, for 10 kW units (kW) [2][4][6][9]:

| Outdoor | G1-M (3φ) | G2 | G3 | Water |
|---|---|---|---|---|
| +2 °C | 3.2 (W37, ≈load) – 4.0 (W27) | 3.1–3.2 (≈load) | 3.19–3.27 (≈load) | W27–37 |
| +7 °C | 3.7–3.9 | 3.1 (≈load, W27) – 4.3 | **2.43–2.53** | W25–36 |
| +12 °C | 4.1–4.4 | 3.7–5.1 | 2.76–3.33 | W24–34 |

Interpretation, at medium confidence:
- **Older generations (G1/G2):** the floor climbs by ≈0.1–0.17 kW per K of outdoor temperature between +2 and +12 °C (3.2 → 3.7–4.9 kW).
  - This fits the physics: at a fixed minimum compressor speed, refrigerant mass flow scales with suction-gas density, which rises with evaporating temperature.
  - It is the same direction and size as the aroTHERM (2.80 → 3.73 kW).
- **G3** has a lower floor: ~2.4–2.8 kW at +7…+12 °C.
  - G3's warmer-climate +12 °C point ran continuously at 2.78 kW. Its own average-climate +12 °C point was tested at 3.28 kW, so the true floor is at or below 2.78 kW.
- **Caveat:** for cycling points the lab tests at a capacity step the manufacturer chooses. It is not necessarily the absolute minimum frequency. Declared "min" values are upper bounds on the true floor.
  - Example of the inconsistency: G2 colder +7 °C is 4.30 kW, while G2 average +7 °C ran continuously at 3.10 kW.
- **Water temperature hardly moves the floor:** at +12 °C, G3 gives 3.28 kW at W24 and 3.21 kW at W30 [4].

### 5. Minimum electrical input

P_el = Pdh / COPd at the low-capacity points (calc):

| Water | G3 | G2 | G1-M |
|---|---|---|---|
| W24–26 | 0.37 (2.78 kW, +12 warmer), 0.45 (+12), 0.48 (+7) | 0.44 (+12), 0.47 (+7) | 0.60–0.65 |
| W28–30 | 0.58–0.61 | 0.67–0.83 | 0.75–0.79 |
| W32–37 | 0.49 (W32, 2.43 kW) – 0.74 (W36) | 0.70–0.99 | 0.89–0.93 |

- The compressor floor is ~0.4–0.5 kW of electricity at cold water. It rises by roughly 0.02–0.04 kW per K of LWT at similar output.
- No certificate gives fan or pump power separately. EN 14511 includes only the internal pump's share needed to overcome internal pressure drop.

### 6. A portable COP model fitted to these data

Carnot efficiency η = COP / (T_c/(T_c − T_e)), with T_c = LWT + 2 K and T_e = T_out − 6 K (calc) [2][4][14]:

| Load band | η range |
|---|---|
| Mid-load continuous points (Pdh 3–6 kW) | 0.50–0.54 (G2 A7/W27: 0.61) |
| Low-capacity "min" points | 0.45–0.56 (G3: 0.45–0.49) |
| Near-maximum points: warmer +2 °C, TOL, Tbiv | 0.42–0.49 |
| Datasheet full-capacity points [14] | 0.54 (A7/W35), 0.45 (A−7/W35), 0.33 (A−7/W55) |

Suggested simulator law (medium confidence): **COP = 0.50 × (LWT + 275.15) / (LWT + 8 − T_out)**, multiplied by 0.9 at the speed floor and by 0.85–0.9 at maximum speed.

Spot checks:
- A2/W30: predicted 4.24, certified 4.34–4.59.
- A7/W36 → 4.60 predicted vs 4.17 certified.
- A12/W24 → 8.1 × 0.9 = 7.3 predicted vs 7.34 certified.

### 7. Speed penalty versus flow-temperature penalty at +2 °C

| Unit | Point | Output | Electric | COP | η |
|---|---|---|---|---|---|
| G3 [4] | ≈W30 (average) | 4.90 kW | 1.07 kW | 4.59 | 0.54 |
| G3 [4] | ≈W35 (warmer, full) | 9.55 kW | 2.82 kW | 3.39 | 0.45 |
| G2 [2] | ≈W30 | 4.80 kW | – | 4.34 | 0.51 |
| G2 [2] | ≈W35 | 8.80 kW | – | 3.15 | 0.42 |

- About 10% of the COP gap is the 5 K of extra water. About 15–17% is compressor speed (calc).
- An owner-observed ~3 kW electric draw at +2 °C means ~9–10 kW of heat at COP ≈3.2–3.4, or less if the water is hotter.

### 8. EN 14825 points include defrost; EN 14511 ratings do not

- The +2 °C and −7 °C points are integrated over defrost cycles under the standard's humid conditions (standard knowledge, not re-read here).
- So the B-point COPs (4.34–4.59 at ≈W30) already contain frosting losses at roughly 2 °C dry bulb / 1 °C wet bulb. That makes them the best available anchor for Lithuania's humid −5…+5 °C days.
- The EN 14511 A7/W35 rating (10.2 kW at COP 5.0, G3) is a steady, frost-free point [4].

## What this means for controlling this house

Confidence is given per item.

1. **Treat leaving-water temperature as the first-order cost driver in mild weather** (high confidence, certified data [2][4]).
   - Between +5 and +12 °C each kelvin of LWT costs ≈3–5% of electricity.
   - Rule: never request more than about **28–30 °C at +7…+12 °C**, or about 30–32 °C at 0…+5 °C, unless the room is measurably below target.
   - A 36–39 °C request in mild weather costs 25–40% more electricity for the same heat than W27–30 (calc from [4]).

2. **Do not drive the compressor to maximum speed for catch-up** (high confidence).
   - At +2 °C, full speed costs ~15% more electricity than mid-speed at the same water temperature, and more once the higher water temperature it creates is added.
   - Use the unit's power limit (note 08: Word 43, C/P limit = Power limit). Try **≈1.2–1.5 kW electric** at T_out ≥ −3 °C. At +2 °C that caps output near 4–5 kW, inside the η ≈ 0.51–0.54 band.
   - Testable: log COP for one week with the cap and one week without, at similar outdoor temperatures.

3. **Expect the cycling floor to rise in warm air** (medium confidence; generation-dependent).
   - For G1/G2-type behaviour, model **P_min(T_out) ≈ 3.2 kW + 0.12 kW/K × (T_out − 2)**, with a 3.1 kW floor. That gives about 3.8 kW at +7 °C and 4.4 kW at +12 °C. For G3, use a flat ≈2.5–2.8 kW.
   - The owner's 3.7–3.8 kW measurement fits the G1/G2 curve at about +6…+8 °C.
   - **Action:** read the nameplate suffix, then log heat output at the steady minimum frequency (Word 143 at its floor) at three or more outdoor temperatures to fit the slope.

4. **Balance point** (calc; H = 0.14–0.20 kW/K, target 22 °C, ignoring internal and solar gains):
   - With G1/G2 floor behaviour, the load meets P_min at about **−1…+5 °C**. Below that the unit can run continuously. Above it, it must cycle.
   - At +10 °C the duty cycle is ≈1.7/4.1 ≈ 40%.
   - With a G3 floor, continuous running extends up to about +7 °C.
   - The power cap in item 2 does not change the floor. Only longer, fewer cycles help above the balance point.

5. **Midday and PV blocks are attractive at mild temperatures, but only at low water temperature** (medium-high confidence).
   - At A12/W24 the certified minimum-speed COP is 7.3–8.4 [2][4], against ~4.3–4.6 at A2/W30. Heating at the warmest hour is worth ~40% less electricity per kWh of heat, before counting PV.
   - The slab (6.6 kWh/K) can store a 3–4 h block of 3.3–4.4 kW output, about 11–17 kWh, for ≈1.7–2.5 K of slab rise.
   - Keep LWT ≤ 30 °C during these blocks. Otherwise the benefit is halved (each kelvin ≈ 4–5% at +12 °C).

6. **Do not use Cdh to tune cycling** (high confidence). The certified 0.93–0.99 contains only the 25 W idle draw. Cycling cost has to be measured:
   - per-start electricity overhead;
   - the time the outlet takes to reach steady temperature after a start;
   - COP in the first 10 min versus steady state.
   Notes 03 and 12 suggest field Cc ≈ 0.8.

7. **Idle parasitics are small on paper** (medium confidence).
   - 25 W standby, plus 0–25 W crankcase, is about 0.6–1.2 kWh/day.
   - The circulating pump (75–85 W, note 08) and tank standby (36–132 W in EN 16147 tests [2][4][5][7]) are the larger idle loads. Measure both.

8. **Cold-spell planning** (medium confidence).
   - The compressor declares 7.1–7.8 kW at −7…−10 °C (W35).
   - It declares only 3.2–5.6 kW at −22 °C, with COP 1.4–1.7 [2][4].
   - For H = 0.14–0.20 the design load at −20 °C is 5.9–8.4 kW, so expect backup-heater help below roughly −12…−15 °C. Pre-charge the slab ahead of forecast cold snaps rather than asking for high LWT during them.

9. **Simulator inputs** (medium confidence):
   - COP = 0.50 × Carnot(LWT+2, T_out−6), × 0.9 at the floor, × 0.85–0.9 near maximum;
   - P_min(T_out) as in item 3;
   - minimum electric ≈ 0.45 kW + 0.03 kW/K × (LWT − 25);
   - standby 25 W;
   - add a start-up penalty separately, from logs.

## Contradictions and open questions

1. **The declared "min" capacities are not consistent.**
   - G2 average-climate +7 °C ran continuously at 3.10 kW, yet the colder-climate +7 °C point was tested at 4.30 kW [2].
   - G3 average +12 °C was tested at 3.28 kW, but warmer-climate +12 °C ran continuously at 2.78 kW [4].
   - The lab tests at manufacturer-chosen frequencies, so the true floor is at or below the lowest of these. The certificates bound the floor; they do not pin it down.
2. **Is the minimum floor really outdoor-dependent on this unit?**
   - G1/G2 data say yes (+0.1–0.17 kW/K). G3 shows no clear trend: 2.5 kW at +7 °C and 2.8–3.3 kW at +12 °C.
   - Only owner logs of steady minimum-frequency output at several outdoor temperatures can settle it.
3. **The EN 14825 water temperatures are recalled, not read.** The 2014 EUR-Lex Communication cites the tables without reproducing them [12]. If the colder-climate values differ (for example +7 °C at W25 versus W27), the per-K sensitivities shift by about 10–20% relative.
4. **Carnot efficiency at full capacity versus EN 14511.**
   - The EN 14511 A7/W35 rating gives η ≈ 0.55–0.58 at ~10 kW [2][4].
   - The near-full EN 14825 points (warmer +2 °C) give 0.42–0.45.
   - Possible causes: defrost included at +2 °C, compressor speed, or the T_e approximation. Unresolved.
5. **Which generation does the owner have?** Note 08 says AIO NhH (G1). The 2023/24 catalogue sells NhH2 (G2) [13].
   - The G1 single-phase certificate has 55 °C data only [5].
   - Minimum output (G1/G2 ~3.1–4.9 kW versus G3 ~2.4–3.3 kW) and part-load COP differ by generation.
6. **The "down to 10 Hz" claim [13] versus a ≥2.4 kW declared floor** (and note 08's 20–120 Hz service-manual range). Unresolved. Read Word 142/143 at the floor.
7. **Anomalous G3 colder-climate TOL point:** 3.15 kW at COP 1.43 (35 °C) but 5.19 kW at the 55 °C application [4]. It may be a data-entry or test artefact. Do not rely on it.
8. **Search budget:** zero web searches were possible, so non-English, forum and field sources were not added in this gap round. All new evidence is certified lab data plus distributor material.

## Sources

1. HP KEYMARK database, certificate holder "Gree Electric Appliances, Inc. of Zhuhai" (holder 2441, subtype list) - EHPA/HP KEYMARK - 2026 - https://www.heatpumpkeymark.com/en/?type=109126&tx_pskeymark_frontend%5Bholder%5D=2441&tx_pskeymark_frontend%5Baction%5D=certificateHolder&tx_pskeymark_frontend%5Bcontroller%5D=Frontend&cHash=68eb48c2303108b14294a418a54d1000 - manufacturer/lab registry - inventory of all Versati subtypes and registration numbers.
2. HP KEYMARK subtype "VERSATI AIO G2 8-10kW" (GRS-CQ10PdG/NhH2-E, reg. 041-K004-11) - Gree / BRE - 2022 - https://www.heatpumpkeymark.com/en/?type=109126&tx_pskeymark_frontend%5Bsubtype%5D=2854&tx_pskeymark_frontend%5Baction%5D=showSubtype&tx_pskeymark_frontend%5Bcontroller%5D=Frontend&cHash=2efe1ec6e62fa6ebea92d25de28523a0 - lab (certified EN 14825) - full Pdh/COPd/Cdh table for G2 AIO, 3 climates; standby; DHW.
3. HP KEYMARK subtype "VERSATI AIO G2 8/10kW" (GRS-CQ10PdG/NhH2-M, reg. 041-K004-20) - Gree / BRE - 2022 - https://www.heatpumpkeymark.com/en/?type=109126&tx_pskeymark_frontend%5Bsubtype%5D=3352&tx_pskeymark_frontend%5Baction%5D=showSubtype&tx_pskeymark_frontend%5Bcontroller%5D=Frontend&cHash=f5cdf3f091f9e459b841d63b0532c37b - lab - 3-phase G2 table (identical to G1-M), EN 14511 ratings.
4. HP KEYMARK subtype "VERSATI AIO G3 8/10kW" (GRS-CQ10PdG/NhH3-E/-M, reg. 041-K004-31) - Gree / BRE, tested by Intertek - 2025 - https://www.heatpumpkeymark.com/en/?type=109126&tx_pskeymark_frontend%5Bsubtype%5D=6328&tx_pskeymark_frontend%5Baction%5D=showSubtype&tx_pskeymark_frontend%5Bcontroller%5D=Frontend&cHash=d0b2a44de2160baf2f6b68e451d10d28 - lab - G3 part-load map, lower floor (2.4–2.8 kW), P_CK 0 W, TOL anomaly.
5. HP KEYMARK subtype "Versati Split G1 8-10kW" (GRS-CQ10Pd/NhH-E, reg. 041-K004-09) - Gree / BRE - 2021 - https://www.heatpumpkeymark.com/en/?type=109126&tx_pskeymark_frontend%5Bsubtype%5D=2225&tx_pskeymark_frontend%5Baction%5D=showSubtype&tx_pskeymark_frontend%5Bcontroller%5D=Frontend&cHash=28e233266f4f2a68d872c25809e9e7e9 - lab - G1 single-phase, 55 °C only; DHW XL COP 2.76, 54.5 W standby.
6. HP KEYMARK subtype "Versati split G1 8/10kW" (GRS-CQ10Pd/NhH-M, reg. 041-K004-17) - Gree / BRE - 2022 - https://www.heatpumpkeymark.com/en/?type=109126&tx_pskeymark_frontend%5Bsubtype%5D=3340&tx_pskeymark_frontend%5Baction%5D=showSubtype&tx_pskeymark_frontend%5Bcontroller%5D=Frontend&cHash=89e8c64ac726c21d458bda49a8f36ae7 - lab - G1 3-phase 35/55 table; floor 3.2–4.4 kW rising with outdoor temperature.
7. HP KEYMARK subtype "Versati Split G2 8/10kW" (GRS-CQ10Pd/NhH2-E + SXTVD300LC/B-E, reg. 041-K004-16) - Gree / BRE - 2022 - https://www.heatpumpkeymark.com/en/?type=109126&tx_pskeymark_frontend%5Bsubtype%5D=3358&tx_pskeymark_frontend%5Baction%5D=showSubtype&tx_pskeymark_frontend%5Bcontroller%5D=Frontend&cHash=6eb0cd4caa7e0495513651d6b8edc64a - lab - confirms split and AIO share data; 300 L tank standby 132 W.
8. HP KEYMARK subtype "Versati Split G3 8/10kW" (reg. 041-K004-26) - Gree / BRE - 2025 - https://www.heatpumpkeymark.com/en/?type=109126&tx_pskeymark_frontend%5Bsubtype%5D=5343&tx_pskeymark_frontend%5Baction%5D=showSubtype&tx_pskeymark_frontend%5Bcontroller%5D=Frontend&cHash=a4285a87fbb86d5a298ce0b69f842d08 - lab - G3 split equals G3 AIO.
9. HP KEYMARK subtype "Versati monobloc G3/G4 8/10k" (GRS-CQ10Pd/NhG3/NhG4, reg. 041-K004-13) - Gree / BRE - 2022 - https://www.heatpumpkeymark.com/en/?type=109126&tx_pskeymark_frontend%5Bsubtype%5D=3320&tx_pskeymark_frontend%5Baction%5D=showSubtype&tx_pskeymark_frontend%5Bcontroller%5D=Frontend&cHash=e080a441fab450103d1ea900a66d9835 - lab - monobloc comparison; colder +7 °C floor 2.7 kW.
10. BRE Certificate of Conformity 041-K004-31, VERSATI AIO G3 8/10kW - BRE Global - 2025 - https://www.heatpumpkeymark.com/uploads/tx_ehpakeymark/Cert_041-K004-31.pdf - certification document - test lab (Intertek Guangzhou), standard editions (EN 14825:2022), validity 2025–2035.
11. HP KEYMARK subtypes "Versati monobloc G3/G4 R290 8/10kW" (reg. 041-K004-34) and "VERSATI V Monobloc 8/10" (reg. 011-1W1086) - Gree - 2025 - https://www.heatpumpkeymark.com/en/?type=109126&tx_pskeymark_frontend%5Bsubtype%5D=6590&tx_pskeymark_frontend%5Baction%5D=showSubtype&tx_pskeymark_frontend%5Bcontroller%5D=Frontend&cHash=5523af455a70b239c5d860d7d752f88c and https://www.heatpumpkeymark.com/en/?type=109126&tx_pskeymark_frontend%5Bsubtype%5D=6771&tx_pskeymark_frontend%5Baction%5D=showSubtype&tx_pskeymark_frontend%5Bcontroller%5D=Frontend&cHash=44538f6d9a58fb0be19d291157827e05 - lab - R290 platform turns down to 2.3 kW (COP 8.9 at +12 °C).
12. Commission Communication 2014/C 207/02 (transitional methods for Reg. 811/813/2013) - European Commission - 2014 - https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52014XC0703(01) - regulation - confirms EN 14825 tables 11–13 / 18–20 define the test points and adds point G (−15 °C); does not print the water temperatures.
13. "GREE Versati III katalog 2023/2024" (CZ) - Slovklima (Gree distributor) - 2023 - https://www.slovklima.sk/wp-content/uploads/2023/05/Slovklima_gree-katalog-versatiii-2023_2024-cz.pdf - manufacturer - "G10, down to 10 Hz" claim; AIO sold as NhH2; 10.0 kW at COP 4.8 (UFH rating).
14. Sibling note 08-gree-versati.md (Versati III split datasheet table: A7/W35 9.5 kW at COP 4.61, A−7/W35 6.65 kW at 2.81, etc.) - this research sweep - 2026 - docs/research/notes/08-gree-versati.md - manufacturer (secondary) - full-capacity points used for the Carnot comparison.
15. Eurovent certificate, Gree VERSATI MAX GRS-CQ22Pd/NhA-M - Eurovent Certita - 2025 - https://www.eurovent-certification.com/en/catalog/program/certificate/participant/model/show/202131606 - certification - checked as a source of part-load data; it has none (rating points only). Psb 25 W matches Keymark.
