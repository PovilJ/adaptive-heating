# Gap G3: What water temperature does this slab need to absorb a given heat output, i.e. its emitter conductance (water-to-room W/K, or EN 1264 K_H) for typical Lithuanian screed thickness, pipe spacing (150-200 mm) and floor covering (tile, laminate, parquet)? How should it be identified from the owner's logs?

This is a follow-up note for gap G3. It replaces an earlier draft written without web access. That draft's EN 1264 numbers came from memory. This version checks them against a manufacturer's certified design chart [1], an independent EN 1264-2:2021 calculator [3] and a FEM validation paper [2]. It also re-runs the field-data analysis on heatpumpmonitor.org [12][13].

Notes 02, 03, 05 and 15 were skimmed first. No repository code or docs outside `docs/research/notes/` were read.

Abbreviations:
- **UFH**: underfloor heating.
- **HPM**: heatpumpmonitor.org.
- **K_H**: water-to-room conductance per m² of active floor, in W/(m²K), referred to the log-mean water temperature (practically the arithmetic mean at these small temperature differences).
- **UA**: K_H × active floor area A, in W/K.
- **K_ws**: water-to-screed conductance for the whole floor, in kW/K.
- **K_sr**: screed-to-room conductance for the whole floor, in kW/K. The two are in series: 1/UA = 1/K_ws + 1/K_sr.
- **R_λ,B**: thermal resistance of the floor covering, in m²K/W.

Assumed loads ([calc] rows): L = 0.17·(22 − T_out) − 0.34 kW. This gives 1.7 kW at +10 °C, 3.1 kW at +2 °C, 4.25 kW at −5 °C and 6.8 kW at −20 °C. P_min is 3.75 kW. The water flow is 1.72 m³/h, about 2.0 kW/K, so the loop ΔT is about 1.9 K at P_min.

## Summary

- **The certified data confirms the EN 1264 K_H values to within about 3 %.**
  - Uponor's chart is for 16×2 mm pipe under 45 mm of cement screed (λ 1.2) with no covering. At the comfort limit curve it gives 97.7 / 94.6 / 90.3 / 84.1 / 76.5 W/m² at excess temperatures of 15.0 / 16.8 / 18.5 / 19.8 / 20.7 K, for spacings of 100 / 150 / 200 / 250 / 300 mm [1].
  - That means K_H(R 0) = **6.5 / 5.6 / 4.9 / 4.2 / 3.7 W/(m²K)**.
  - Uponor's worked example (R 0.10, 150 mm spacing, 40 W/m² at 12 K excess) gives **3.33** [1]. An independent EN 1264-2:2021 calculation (150 mm, about 45 mm cover) gives 3.33 at R 0.10 and 2.76 at R 0.15 [3].
- **The EN 1264 method itself is accurate.** A FEM check of type-A floors found EN 1264 within a mean ratio of 0.99 (SD 0.04) of FEM. The output exponent is 1.00-1.05, so a linear conductance model is adequate [2].
- **K_H for plausible Lithuanian build-ups** (16 mm pipe, cement screed, model anchored to [1][3]):

  | Build-up | Tile (R 0.02) | Glued 14 mm parquet (R 0.08) | Laminate + underlay (R 0.10) | Floating parquet (R 0.13) | R 0.15 limit |
  |---|---|---|---|---|---|
  | 150 mm spacing / 45 mm cover | 4.9 | 3.6 | 3.3 | 3.0 | 2.8 |
  | 200 mm spacing / 45 mm cover | 4.3 | 3.3 | 3.0 | 2.7 | 2.5 |
  | 150 mm spacing / 65 mm cover | 4.3 | 3.3 | 3.0 | 2.7 | 2.5 |
  | 200 mm spacing / 65 mm cover | 3.8 | 2.9 | 2.7 | 2.5 | 2.3 |

  The 65 mm rows carry ±8 % extra uncertainty (see section 1.3).
- **Whole-floor UA at 130 m² active area:**
  - Tile: about **490-640 W/K**.
  - Laminate or parquet: about **320-470 W/K**.
  - Worst plausible case (200 mm spacing, 65 mm cover, R 0.15): about 300 W/K.
  - Scale linearly with the real active area.
- **Covering is the largest single factor.**
  - Going from tile to laminate or parquet lowers K_H by 25-35 %. At this house's loads that costs **+1.5 to +3 K of flow temperature at +2 °C** and +4 to +7 K at −20 °C [calc].
  - Measured covering resistances:
    - Laminate + underlay + vapour barrier: 0.115 [5].
    - Junckers solid boards: 0.08 at 14 mm, 0.12 at 20.5 mm, 0.13 at 22 mm. Adding foam or PolyFoam underlay brings these to 0.12-0.20 [6].
    - Tile: 0.01-0.02 [1].
  - Floating wood on foam can therefore exceed the R 0.15 design limit [1][5][6].
- **Lithuanian practice:** screeds are about 6.5 cm (at least 5-6 cm), i.e. about 45-50 mm over a 16 mm pipe [11]. That is the same as the EN/DIN 45 mm reference [1]. The "45/150" and "45/200" rows are the most likely ones for this house. "65/200" is the pessimistic case.
- **Field data from 25 public UFH-only systems without hydraulic separation** (cold days ≤ 3 °C with ≥ 12 h of space heating per day) [13]:
  - Running conductance quartiles: **421 / 566 / 752 W/K**.
  - Mean water minus room: **6.0 / 7.2 / 11.2 K**, at 3.3-5.6 kW.
  - Per m² of *gross* floor area: 2.1 / 3.1 / 3.7 W/(m²K).
  - These figures match the EN 1264 bands above for R 0.08-0.15 floors.
- **Lithuanian field anchor: HPM system 887, Vilnius** (150 m², 6 kW Nibe, no separation) [12].
  - At about 0 °C: flow / return 28.6 / 24.7 °C, room 22.6 °C, 2.2 kW. Mean water is 4.2 K above the room, which is **about 550 W/K**.
  - At −10 to −15 °C: 31 / 27 °C at 2.8 kW, about 500 W/K.
  - This matches the 150 m² glued-parquet or laminate rows (500-540 W/K).
- **Lowest outlet temperature at which the floor can absorb P_min = 3.75 kW**, with the screed at its normal level (130 m², [calc]):

  | Build-up | +10 °C | +2 °C |
  |---|---|---|
  | Tile 45/150 | about 26.7 °C | about 28.1 °C |
  | Laminate 45/150 | about 28.3 °C | about 30.5 °C |
  | Floating parquet 45/150 | about 28.9 °C | about 31.4 °C |
  | Laminate 65/200 | about 30.1 °C | about 32.4 °C |

  Below these values the return rises and the unit stops on overshoot. Notes 02 and 05 ("27 °C tile / 30 °C timber at +2 °C") match the 45/150 rows. The thick-screed, wide-spacing case is 2-3 K worse.
- **The forced-cycling penalty is about 1.5-3.5 K at +10 °C and 0.5-1 K at +2 °C** [calc].
  - This compares running at P_min against continuous matched delivery. It is roughly 3-8 % COP at +10 °C and 1-2.5 % at +2 °C.
  - Note 03 estimated 3-7 K. Its range applies only if a run lasts long enough for the screed to reach a new steady state. Within a 1-4 h burst, the extra heat crosses only the water-to-screed resistance. That resistance (K_ws ≈ 0.8-1.8 kW/K for 130 m²) is 2-3× larger in conductance than the full water-to-room UA.
- **Mild-weather apparent conductance overstates the floor by about 1.6× (median).**
  - On HPM systems, the "running heat ÷ (mean water − room)" ratio on mild days with short runs is 1.13-1.93× (quartiles) the cold-day value [13].
  - The heat is going into screed storage, not into the room.
  - So the floor UA must be identified from **long cold-weather runs**, or with an explicit two-node model. Mild-day ratios would make the floor look stronger than it is.
- **Hot-water cycles and single-room sensors bias the identification.**
  - In the Vilnius data, the "space" statistics on warm days include 50 °C flows, so the space/hot-water split was mislabelled [12].
  - Room readings 1-2 K above the floor-weighted mean make UA look about 2× too large in mild weather [12].
  - Mask hot-water periods plus 30-60 min after each. Use a whole-house mean room temperature.
- **A DTU field study fitted a grey-box floor-heating model** from thermostats, a heat meter and pump data. It found the supply setpoint was too high, and lowering it to the model's minimum cut the energy-weighted supply temperature by **8.6 K** and the return by **6.5 K** without loss of comfort [9]. That is direct evidence that identifying the floor pays off.

## Detailed findings

### 1. What K_H is and how solid the numbers are

#### 1.1 Definitions and the standard

- **Water side.** EN 1264 writes the output as q = K_H·Δθ_H, where Δθ_H is the log-mean excess of flow and return over the room [1][4].
  - At this house's 3-8 K excess and 2-4 K spread, the log-mean is within 0.1-0.2 K of (mean water − room).
  - K_H is the product B·Π(a_i^m_i). It depends on:
    - spacing T;
    - cover thickness and conductivity s_u/λ_u;
    - covering resistance R_λ,B;
    - pipe diameter and material [2].
- **Surface side.**
  - The total surface coefficient is 10.8 W/(m²K) for floors in heating [2]. The base curve gives about 100 W/m² at 9 K surface excess.
  - Surface limits are 29 °C in occupied zones, 33 °C in bathrooms and 35 °C at the perimeter [1][4].
  - Wood-floor makers cap the surface at 27 °C [6]. None of these limits binds here: at −20 °C this house needs only about 45-60 W/m².
- **Accuracy.** Boldrin et al. compared the EN 1264 simplified method with FEM for type-A floors. They used 20 mm pipe, 60-80 mm concrete, spacing 50-375 mm and R 0.015-0.20.
  - The ratio of EN 1264 output to FEM output had a mean of 0.99 and an SD of 0.04 [2].
  - The output-vs-excess relation has an exponent of 1.00-1.05 [2], so one K_H per build-up is enough. No exponent needs fitting.

#### 1.2 Anchors (manufacturer certified chart and EN 1264-2:2021 calculator)

- **Uponor Klett, 16×2 mm pipe, 45 mm cement screed, λ 1.2 [1].**
  - The limit-curve points for R 0 (q, Δθ_H,N) are (97.7, 15.0), (94.6, 16.8), (90.3, 18.5), (84.1, 19.8) and (76.5, 20.7) W/m² and K, for T = 100, 150, 200, 250 and 300 mm.
  - So K_H(R 0) = 6.51 / 5.63 / 4.88 / 4.25 / 3.70 W/(m²K).
  - The same booklet's second chart, for another 16 mm system, gives 5.32 at 150 mm and 4.58 at 200 mm. That is the system-to-system spread of about ±5 %.
- **Uponor reading example [1].** 40 W/m², R 0.10, 150 mm spacing gives Δθ_H = 12 K. So K_H = 3.33.
  - Uponor computes flow as room + Δθ_H + spread/2. In that example: 20 + 12 + 2.5 = 34.5 °C.
- **HeatAlgo EN 1264-2:2021 tables [3].** These are for 150 mm spacing, 5/8" tube, 1.8" (46 mm) concrete and a 20 °C room.
  - At 30/25 °C flow/return (Δθ_H = 7.2 K): tile treated as R 0.10 gives 24.0 W/m² (K 3.33); wood at R 0.12 gives 23.0 (K 3.19); carpet at R 0.15 gives 19.9 (K 2.76).
  - At 35/30 °C: 42 W/m² at R 0.10, again K 3.40.
- **The covering adds about 1.23·R to 1/K_H at 150 mm, not 1.0·R.**
  - From the anchors: 1/3.33 − 1/5.63 = 0.123 per 0.10, and 1/2.76 − 1/5.63 = 0.185 per 0.15.
  - The extra 23 % is the EN 1264 spacing factor a_T falling as R rises. A resistive covering also cuts lateral spreading. I used 1.28 at 200 mm [calc, extrapolated].
- **UK practice data points [10].**
  - These come from the CIBSE guide via OpenEnergyMonitor members.
  - 150 → 200 mm spacing costs 4.9 W/m² at 30 °C mean water, 11.6 at 35 °C and 19.4 at 45 °C.
  - At 30 °C mean water and a 20 °C room, 4.9 W/m² out of about 33-50 W/m² is a 10-15 % loss. That matches the 13 % K_H drop from 150 to 200 mm in [1].

#### 1.3 Cover thickness (the least certain factor)

- From 45 to 65 mm cover, a pure 1-D estimate adds 0.02/1.2 = 0.017 m²K/W. That lowers K_H(R 0) by about 9 %.
- The EN 1264 factor structure (a_B together with a_u^m_u) implies about 21 % [calc; Annex A factor values recalled, not re-read].
- I used the midpoint, about −15 %, and flag ±8 %.
- No manufacturer chart for 65 mm cover was found. One unverified UK quoting-app table (65 mm sand-cement, 16 mm pipe) gives 50 W/m² at 35 °C mean water at 150 mm and 40 W/m² at 200 mm. Assuming a 20 °C room and R about 0.10, that is K 3.3 and 2.7. It sits between the 45 mm and 65 mm rows above.
- For Lithuania the question is less important. Local practice is a 6.5 cm total screed, at least 5-6 cm in houses [11], i.e. about 45-50 mm over the pipe. That is the same as the DIN 18560 45 mm minimum for cement screed at ≤ 2 kN/m² [1].
- Anhydrite (CAF) needs only 35 mm cover [1] and has higher λ, so it would be 5-10 % better.

#### 1.4 Floor coverings (R_λ,B)

| Covering | R_λ,B (m²K/W) | Source |
|---|---|---|
| Tile, marble | 0.01-0.02 | [1] |
| PVC / vinyl | about 0.025 | [1] |
| Parquet (generic) | 0.04-0.11 | [1] |
| Junckers 14 mm board | 0.08 | [6] |
| Junckers 20.5 mm board | 0.12 | [6] |
| Junckers 22 mm board | 0.13 | [6] |
| Junckers Foam underlay | 0.04 | [6] |
| Junckers PolyFoam + PE underlay | 0.07 | [6] |
| Floor cardboard | 0.01 | [6] |
| Example laminate system: 0.07 laminate + 0.04 underlay + 0.005 vapour barrier | 0.115 | [5] |
| Carpet | 0.06-0.15 | [1] |

- The design limit is R ≤ 0.15 for the *whole* covering system (BVF and EN 1264-3). Uponor designs living rooms at 0.15, so that a later change of covering never under-heats the room [1][5]. ITAP recommends designing at 0.10 [4].
- Partial rugs are area-weighted. Uponor's example of 25 m² tile with 8 m² of carpet gives R 0.07 [1].
- A common forum rule of thumb is about 2-3 K extra supply per +0.05 m²K/W [14]. It is weak evidence, but consistent with the calculation: at 3 kW over 130 m², +0.05 R raises the required mean water by about 1-1.5 K. At 6.8 kW it is about 3 K.

### 2. The two-node split: why bursts cost less than note 03 assumed

- **Physics model.** The Koschenz/Lehmann TABS model links the mean water temperature to the slab temperature in the plane of the pipes through a resistance R_t = R_w + R_p + R_x + R_z [7]:
  - R_w: water-side convection, small.
  - R_p = T·ln(d/(d − 2s))/(2πλ_p): pipe wall.
  - R_x = T·ln(T/(πd))/(2πλ_s): conduction from pipe to plane.
  - R_z: the supply-vs-mean term.
- **Values for 16×2 PE-X (λ 0.35) in cement screed (λ 1.2), without R_z:**
  - 150 mm: R_p ≈ 0.020 and R_x ≈ 0.022, so ≈ 0.043 m²K/W.
  - 200 mm: about 0.065 m²K/W [calc from 7].
- **Cross-check against EN 1264.** The certified 1/K_H minus the 1-D path above the pipe (0.093 + 0.045/1.2) is 0.047 at 150 mm and 0.074 at 200 mm [1]. That is almost the same residual. The Koschenz form is a consistent way to split K_H.
- **The split I used** [calc]:
  - K_sr per m² = 1/(0.093 + R_λ,B + s_u/(2λ)): surface resistance + covering + upper half of the screed.
  - K_ws per m² = 1/(1/K_H − 1/K_sr).
  - Whole floor at 130 m²:
    - Tile 45/150: K_ws ≈ 1.8, K_sr ≈ 1.0 kW/K.
    - Laminate 45/150: about 1.5 and 0.6 kW/K.
    - Laminate 65/200: about 0.9 and 0.6 kW/K.
  - An Aalborg simulation used priors of 6-12 W/(m²K) water-to-floor and 3.5-4.5 W/(m²K) floor-to-room [8]. That is the same order, somewhat lower on the water side.
- **Consequence.** During a run of 1-4 h, the screed (about 5 kWh/K for 130 m² × 65 mm) moves by only about 1 K. So:
  - mean water − room ≈ L/K_sr + P/K_ws, plus the slab swing;
  - not P/UA.

Outlet needed, continuous matched delivery vs running at ≥ P_min (130 m²) [calc]:

| Build-up | +10 °C | +2 °C | −5 °C | −20 °C |
|---|---|---|---|---|
| Tile 45/150 | 25.1 / 26.7 | 27.5 / 28.1 | 29.7 | 34.3 |
| Glued parquet 45/150 | 26.0 / 27.9 | 29.3 / 29.9 | 32.1 | 38.1 |
| Laminate 45/150 | 26.4 / 28.3 | 29.8 / 30.5 | 32.9 | 39.4 |
| Floating parquet 45/150 | 26.8 / 28.9 | 30.7 / 31.4 | 34.1 | 41.4 |
| Tile 65/200 | 25.9 / 28.4 | 29.0 / 29.8 | 31.7 | 37.5 |
| Laminate 65/200 | 27.2 / 30.1 | 31.4 / 32.4 | 35.1 | 42.9 |
| R 0.15, 65/200 | 28.1 / 31.1 | 32.9 / 33.9 | 37.2 | 46.2 |

- At −5 and −20 °C the load exceeds P_min, so the two values coincide.
- The loads are 1.7 / 3.1 / 4.25 / 6.8 kW. With H = 0.14 instead of 0.17, the −20 °C values fall by 2-4 K.
- Area sensitivity, 110 → 150 m²:
  - About ±1-1.5 K at +2 °C.
  - About ±2-4 K at −20 °C.
  - Example: laminate 45/150 at +2 °C running is 31.9 / 30.5 / 29.5 °C at 110 / 130 / 150 m².
- **Burst penalty** (running minus continuous): +1.6 to +3.4 K at +10 °C and +0.6 to +1.1 K at +2 °C. At 2.3-2.5 %/K (note 03) that is about 4-8 % and 1.5-2.5 % COP.

### 3. Field evidence

#### 3.1 HPM cross-section (re-run in this session) [13]

- **Selection.**
  - 84 public systems marked UFH-only (no radiators or fan coils) with hydraulic separation "None".
  - Days with outdoor ≤ 3 °C, ≥ 12 h of space heating, running space heat > 500 W, room sensor 15-26 °C and running flow ≤ 45 °C.
  - Systems with ≥ 10 such days: **25**.
- **Results (quartiles):**
  - K_run = space_heat_mean / (mean water − room): 421 / 566 / 752 W/K.
  - Mean water − room: 6.0 / 7.2 / 11.2 K.
  - Heat: 3.3 / 4.1 / 5.6 kW.
  - Flow − return: 3.1 / 3.6 / 4.2 K.
  - Per m² of gross floor area: 2.09 / 3.06 / 3.73 W/(m²K). Gross area exceeds active area, so these underestimate K_H.
- **Best systems:**
  - Co Antrim: 1339 W/K, 4.9 K at 6.2 kW, 356 m².
  - Great Missenden: 1123 W/K.
  - Rotselaar (Belgium): 878 W/K, 4.8 K at 4.2 kW.
  - Derrygonnelly: 752 W/K.
- **Worst system:** Beauly, 174 W/K at 17 K excess. It is typical of a wide-spaced or high-R floor, or of loops shut by zone valves.
- **Mild-weather bias.** The same systems on mild days (≥ 7 °C, < 8 h of space heating) show K_run 1.13 / 1.59 / 1.93 × their cold-day value. This is the storage effect of section 2 showing up in field data.
- An earlier no-web draft of this note ran a looser selection on 44 systems and got 401 / 595 / 720 W/K. That agrees with this re-run.

#### 3.2 Vilnius anchor (HPM 887) [12]

Outdoor bins, medians of daily space-heating running means:

| Outdoor | Flow / return | Room | Heat | Mean water − room | Conductance | Starts per day | Space-heating hours | COP |
|---|---|---|---|---|---|---|---|---|
| −15 °C | 31.4 / 27.2 °C | 23.4 °C | 2.86 kW | 5.7 K | 500 W/K | 14 | 19.4 | — |
| −5 °C | 29.5 / 25.6 °C | 22.9 °C | 2.42 kW | 4.7 K | 506 W/K | — | — | 3.0 |
| 0 °C | 28.6 / 24.7 °C | 22.6 °C | 2.21 kW | 4.2 K | 550 W/K | 19 | 19 | 3.9 |
| +5 °C | 27.6 / 24.1 °C | — | 2.15 kW | 2.1 K | "997 W/K" | 15 | 12.8 | 4.85 |
| +10 °C | — | — | — | — | "1388 W/K" | — | — | — |

- At +5 and +10 °C the apparent conductance is inflated by storage and by the room sensor, as above.
- Bins ≥ +20 °C showed "space" flows of 52 °C. The space/hot-water split in the daily statistics is mislabelled on warm days.
- **For this house:** a similar Lithuanian slab of 150 m² delivers about 2.2 kW with mean water about 4 K above the room, i.e. a flow of about 28.5 °C.
  - At P_min = 3.75 kW it would need roughly 22 + 3.75/0.53 + 1 ≈ **30 °C outlet** in steady state.
  - It would need less in a short burst, because K_ws > UA.

#### 3.3 Field proof that identification lowers supply temperature [9]

Sarran et al. (DTU, 2022) worked with a low-energy Danish apartment with floor heating. Using only thermostats, a heat meter and pump data, they identified a grey-box model that acted as virtual per-loop sensors. With it they diagnosed poor balancing and too high a supply setpoint and pump setting. Moving to the model's minimum comfortable supply lowered the energy-weighted supply by 8.6 K and the return by 6.5 K. This is the abstract only; the full-text model details were not accessible.

### 4. How to identify UA, K_ws and K_sr from the owner's logs

**Signals.**
- Unit outlet and return temperatures.
- Compressor on/off or frequency.
- Three-way valve state (space heating vs hot water).
- Electricity.
- Heat, if the Versati exposes water flow; otherwise rated flow × ΔT, flagged as uncertain.
- Several room temperatures averaged.
- Outdoor temperature.

**Clean the data first.**
- Mask hot-water cycles plus 30-60 min after each [12].
- Mask defrosts plus about 10 min.
- Mask sunny afternoons.
- Use a floor-area-weighted mean room temperature. A single warm room inflates UA (section 3.2).

**Step A: steady UA, the primary number.**
- Take cold overcast periods (≤ −3 °C) where load ≥ P_min, so the unit runs for many hours.
- After ≥ 6-12 h at a constant setpoint with the return drifting < 0.1 K/h: UA = Q / (mean water − mean room).
- Expect 300-650 W/K for 130 m² (section 1) or about 500-550 W/K by the Vilnius analogue [12].
- Report UA together with the outdoor temperature and run length.
- Do not average in mild-weather days. They read 1.1-1.9× high [13].

**Step B: screed temperature from stagnation.**
- If the circulator keeps running after a compressor stop, the outlet and return converge to the screed temperature near the pipes within one or two loop transits.
- Measured round-trip times in a Danish house were 4-9 min per loop [8]. So average outlet and return over minutes 10-20 after the stop and call it T_slab.
- **Check first whether the Versati stops its pump with the compressor.** If it does, use the first 3-5 min after the next pump start, before the compressor ramps.

**Step C: water-to-screed conductance.**
- K_ws ≈ Q_run / ((T_out + T_ret)/2 − T_slab), using the middle of a run with T_slab interpolated between stagnation points.
- Expect 0.8-1.8 kW/K for 130 m².
- K_sr then follows from 1/K_sr = 1/UA − 1/K_ws, or directly over 24-72 h windows as Q_avg / (T_slab − T_room).

**Step D: grey-box fit.** Use a 2-state model (screed, room) with K_ws, K_sr, C_screed, H and a solar aperture. Fit it on 5-15 min data with the masks applied (note 14). Steps A-C give the priors. This is the approach that produced the 8.6 K reduction in [9].

**Plausibility gates.**
- UA < about 250 W/K or K_H < 2 W/(m²K) of active area fits no plausible build-up in section 1. Suspect closed loops, a mixing valve or thermostatic group, or a bypass (note 15).
- UA > about 800 W/K for ≤ 150 m² suggests overstated heat (rated vs real flow) or a warm-biased room sensor.

**Without a heat meter.**
- Over multi-day windows, Q ≈ H·(T_room − T_out) − gains, with the owner's H of 0.14-0.20. This gives UA to only ±20-30 %.
- A clamp-on or MID heat meter is the single best upgrade for this question.

## What this means for controlling this house

1. **Setpoint floor, until measured. Confidence: medium.**
   - Assume UA ≈ 450 W/K and K_ws ≈ 1.4 kW/K for the whole floor (laminate or parquet, 45/150, 130 m²).
   - The lowest *outlet* at which the floor can take P_min with the screed near equilibrium is about **28-29 °C at +10 °C, 30-31 °C at +2 °C, 33 °C at −5 °C and 39-40 °C at −20 °C**.
   - A tiled floor is about 1.5-2.5 K lower. A 65 mm / 200 mm floor with timber is about 2 K higher.
   - The setpoint *command* also needs the firmware's start headroom (delta_heat_temp_set = 4). The table values are outlets, not commands. Any sustained outlet above them is the controllable loss.
2. **Compare with what is observed.**
   - Setpoints of 31-36 °C with peaks of 39 °C imply outlets of roughly 27-35 °C, given the 4 K start gap.
   - At +2 °C this is about 0-4 K above what a 45/150 timber floor needs. At milder temperatures it is more.
   - So the excess is real but moderate. It is mostly a start-hysteresis and catch-up artefact, not a floor that needs hot water. That holds unless step A finds UA < 300 W/K.
3. **Do not chase continuous matching in mild weather.**
   - Running at P_min costs only about 1.5-3.5 K of outlet at +10 °C and about 1 K at +2 °C [calc].
   - Fewer, longer runs at the lowest outlet the floor accepts beat any attempt to throttle below P_min.
   - Runs longer than about 5-8 h in mild weather lose this advantage: the screed then rises and water-to-room UA governs again.
4. **Simulator parameters (priors):**
   - UA ~ U(320, 650) W/K, centre 450.
   - K_ws ~ U(0.8, 1.8) kW/K.
   - K_sr = 1/(1/UA − 1/K_ws).
   - C_screed ≈ 4-6 kWh/K, which is part of the 6.6 kWh/K whole-house figure.
   - Output linear in the excess (exponent 1.00-1.05 [2]).
   - Loop ΔT = Q/2.0 kW/K.
5. **Identify before tuning.** Run steps A and B this winter, and record the active floor area, covering per room and screed thickness. Each sets the floor by 1-4 K. Re-fit each season.
6. **Hardware and use.**
   - Keep all loops open. Any closed loop or zone actuator cuts UA in proportion to its area [13] (note 15).
   - Avoid large rugs. An R 0.15 rug over 30 % of the floor adds about 0.05 to the area-weighted R [1], or about 1 K at +2 °C.
   - If timber is ever relaid, glued engineered boards (R ≤ 0.09) beat floating boards on foam (0.12-0.20) [5][6].

## Contradictions and open questions

- **Note 03 vs this note on the cycling penalty.** 3-7 K (7-16 % COP) vs 1.5-3.5 K at +10 °C and about 1 K at +2 °C here.
  - The difference is whether water-to-room UA or water-to-screed K_ws governs a burst.
  - HPM shows the storage effect directly: mild short-run apparent conductance is about 1.6× the cold-day value [13].
  - The owner's stagnation data (step B) would settle the magnitude.
- **Note 02's tile K_ws of 3.5 kW/K vs about 1.8 kW/K here (130 m², 45/150).** The EN-residual / Koschenz split [1][7] supports the lower value. If the real value is higher, the penalty shrinks further.
- **The 65 mm cover factor is uncertain.**
  - A 1-D estimate gives −9 % and the EN 1264 factor form −21 %. The Annex A tables were not accessible.
  - The UK 65 mm table (unverified) sits in between.
  - It matters only if the screed is thicker than local practice [11].
- **HPM per-m² values (median 3.1 on gross area) are below EN tile values (4.3-4.9).** This is expected: gross area exceeds active area, UK floors often have R ≥ 0.1, and room sensors are single-point. It was not verified system by system.
- **Versati pump behaviour after a compressor stop is unknown.** It decides whether stagnation-based T_slab works. It is also a control question in its own right.
- **Unknowns for this house:**
  - Active area per storey.
  - Pipe diameter and spacing.
  - Covering per room.
  - Anhydrite vs cement screed.
  - Whether a manifold mixing or thermostatic group exists.
  - Whether the unit's flow reading is real.
- **Sarran et al. [9] full text was not readable.** Only the abstract-level result (−8.6 K supply) is used.

## Sources

1. Uponor underfloor heating/cooling, Planning information (1186660 v1) - Uponor GmbH - 2025 - https://brandportal.uponor.com/m/7187327a41365ace/original/TI-planning-principles-UFHC-EN-1186660-v1.pdf - manufacturer (EN 1264-certified design data) - Limit-curve q/Δθ_H table for 16×2 pipe in 45 mm cement screed (K_H(R 0) by spacing); worked example K_H 3.33 at R 0.10 / 150 mm; covering R values; 45 mm DIN 18560 cover; design at R 0.15; spread 2-5 K.
2. New correlations for the standard EN 1264 (Clima 2007) - Boldrin, De Carli, Ruaro, University of Padova - 2007 - https://www.irbnet.de/daten/iconda/CIB8034.pdf - paper (FEM/FDM vs standard) - EN 1264 type-A output within 0.99 ± 0.04 of FEM; exponent 1.00-1.05; floor heating surface coefficient 10.8 W/(m²K).
3. Radiant floor heating water temperature with a heat pump - HeatAlgo - 2025 - https://heatalgo.com/en-us/blog/radiant-floor-heating-water-temperature - vendor blog (EN 1264-2:2021 calculations) - Output tables by covering and spacing at 30/25 and 35/30 °C for 150 mm / 46 mm cover, giving K_H 3.33 (R 0.10), 3.19 (R 0.12), 2.76 (R 0.15).
4. Sizing radiant floor systems - ITAP S.p.A. - 2017 - https://www.itap.it/wp-content/uploads/Sizing_EN.pdf - manufacturer - Δθ_H definition; flow = room + Δθ_H + σ/2; recommends designing at R 0.10; σ ≤ 5 K; R_o/R_u formulas.
5. Technical Bulletin: Underlay materials under laminate floor coverings - EPLF - 2022 - https://eplf.com/storage/files/eplf-tb-underlay-materials-final-122022-v2_1.pdf - industry association - Whole-system R ≤ 0.15; example laminate 0.07 + underlay 0.04 + barrier 0.005 = 0.115 m²K/W.
6. Underfloor heating - general information (data sheet E-4.0) - Junckers - undated (current) - https://www.junckers.com/wood-flooring/guidance/technical-advice/product-data-sheets/e-underfloor-heating-sound/underfloor-heating-general-information-e-4-0 - manufacturer - R of 14 / 20.5 / 22 mm solid boards 0.08 / 0.12 / 0.13 and of underlays 0.01-0.07; 27 °C surface cap; ΔT through boards 4-6 K at 50 W/m².
7. Control of thermally-activated building systems (TABS) - Gwerder, Lehmann, Tödtli, Dorer, Renggli, Applied Energy 85:565-581 - 2008 - https://www.sysecol2.ethz.ch/OptiControl/LiteratureOC/Gwer_08_AE_85_565.pdf - paper - Koschenz/Lehmann resistance formulas R_w, R_p, R_x, R_z used for the water-to-screed split; example R_t 0.102 m²K/W at 200 mm; daily (not hourly) supply adaptation for slabs.
8. Transient analysis of individual return temperatures in hydronic floor heating systems (CLIMA 2022) - Thorsteinsson, Stærmose, Bendtsen, Aalborg University / Neogrid - 2022 - https://proceedings.open.tudelft.nl/clima2022/article/download/140/111/119 - paper with field data - Loop round-trip times 4-9 min and 87-184 l/h per loop in a BR2020 house with an ASHP; RC priors of 6-12 (water-to-floor) and 3.5-4.5 (floor-to-room) W/(m²K).
9. Grey-box modelling and virtual sensors enabling continuous commissioning of hydronic floor heating - Sarran, Smith, Hviid, Rode, Energy 261 - 2022 - https://ideas.repec.org/a/eee/energy/v261y2022ipbs0360544222021673.html - paper with field data (abstract only) - Identification from thermostats, heat meter and pump data; supply −8.6 K and return −6.5 K after setting the minimum comfortable supply.
10. Calculating underfloor heating output for 200 mm pipe spacing - OpenEnergyMonitor community - 2025 - https://community.openenergymonitor.org/t/calculating-underfloor-heating-output-for-200mm-pipe-spacing/29490 - forum (quoting CIBSE) - 150 → 200 mm costs 4.9 / 11.6 / 19.4 W/m² at 30 / 35 / 45 °C mean water.
11. Grindų betonavimo technologija, etapai (Vilnius) - paslaugos.lt - undated - https://paslaugos.lt/grindu-betonavimas/vilniuje - Lithuanian installer guidance - Heated floors are normally screeded with 6.5 cm of concrete (minimum 5 cm, houses ≥ 6 cm), on two insulation layers.
12. HeatpumpMonitor.org system 887 (Vilnius, Nibe AMS 20-6, 150 m², UFH) daily statistics, Sep 2025 - Sep 2026 - OpenEnergyMonitor; analysis in this note - 2026 - https://heatpumpmonitor.org/system/stats/daily?id=887 - field data - About 500-550 W/K running conductance at −15 to 0 °C; 28.6 / 24.7 °C at 2.2 kW near 0 °C; mild-weather inflation; mislabelled space/hot-water days.
13. HeatpumpMonitor.org public system list and daily statistics for 25 UFH-only, unseparated systems - OpenEnergyMonitor; analysis in this note - 2026 - https://heatpumpmonitor.org/system/list/public.json (plus /system/stats/daily?id=…) - field data - Cold long-run conductance 421 / 566 / 752 W/K; excess 6.0 / 7.2 / 11.2 K; mild short-run inflation 1.13-1.93×.
14. Energieverbrauch Fußbodenheizung: Parkett vs. Fliesen (forum thread) - bau.de - undated - https://bau.de/forum/fussbodenheizung/11246.php - forum (search snippet only, partly AI-generated) - Rule of thumb of about 2-3 K more supply per +0.05 m²K/W covering resistance. Weak evidence, used only as a cross-check.
15. Planning Underfloor Heat, handbook VGCTC202 - Danfoss - 2009 - https://assets.danfoss.com/documents/100650/AG000086464394en-010201.pdf - manufacturer (via notes 02 and 15, not re-read here) - Base curve 8.92·Δθ^1.1; R 0.10 living-room design; σ 5 K.
