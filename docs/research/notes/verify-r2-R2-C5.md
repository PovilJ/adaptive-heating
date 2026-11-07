# Verify R2-C5: Versati minimum electrical input and Carnot efficiency by speed

> Adversarial check, 2026-11-06.
>
> **Method limits.** The shared web-search budget was already used up when this check started: all 3 WebSearch calls were refused, so **0 searches ran** and the non-English queries were not possible. I did not route around the limit. Instead I:
> - fetched known primary URLs directly (HP KEYMARK subtype pages for Versati G1, G2 and G3, the EUR-Lex Communication, the UK Home Energy Model heat-pump methodology, the Dongellini PhD thesis, OpenEnergyMonitor docs and threads, the heatpumpmonitor.org public JSON and the hplib README);
> - recomputed every number from the raw certified tables with my own scripts, instead of reusing the gap note's arithmetic.
>
> 13 sources were read. I did not read repository code or docs outside `docs/research/notes/`.

## Claim

R2-C5 (from gap-r1-G1.md, summary items 6–7) has two parts:

1. The Versati's minimum electrical input is about **0.45 kW + 0.03 kW per K** of leaving water above about 24 °C.
2. Carnot efficiency is **0.42–0.49 at both minimum and maximum speed**, against **0.50–0.54 at mid speed**.

Carnot efficiency (η) is COP divided by the Carnot COP, using T_cond = LWT + 2 K and T_evap = T_out − 6 K.

## Verdict: partly_supported

- **Supported:** the maximum-speed penalty, and the rough size of the minimum-input number for G3.
- **Not supported:** the minimum-speed penalty. On the certified data, the low-capacity points are on average as efficient as the mid points, and on G2 they are the most efficient points of all.
- The source note's own detailed table already shows this. It gives the "min" points as 0.45–0.56, but its summary narrowed that to 0.42–0.49.
- The 0.45 kW + 0.03 kW/K rule is an artefact of pooling generations whose test capacities differ. It mixes up a capacity effect with a water-temperature effect.

## Corrected claim

**A. Minimum electrical input.** Pel = Pdh / COPd at the lowest-capacity EN 14825 points (+7 and +12 °C outdoor), recomputed by me.

| Generation | Fit over low-capacity points | rms error | Comment |
|---|---|---|---|
| G3 (NhH3, 2.4–3.3 kW points) | 0.45 kW + **0.017 kW/K** × (LWT − 24) | 0.065 kW | W32 at 2.43 kW draws 0.49 kW, against 0.69 kW from the claim's rule |
| G2 (NhH2, 3.1–5.2 kW points) | 0.57 kW + 0.038 kW/K | 0.094 kW | Slope inflated: the warmer-water points were also tested at higher output (4.2–5.2 kW) |
| G1-M (NhH, 3.7–4.4 kW points) | ≈0.60–0.65 kW at W24–27; 0.75–0.93 kW at W30–36 | – | **Base is about 0.6 kW, not 0.45 kW** |
| G2 + G3 pooled, controlling for output and outdoor temperature | ≈0.02–0.027 kW/K **plus ≈0.16–0.22 kW per kW of heat** | 0.02–0.04 kW | Output matters as much as LWT |

The physically cleaner form is **Pel_min = Q_min(T_out) / COP(LWT, T_out)**:
- Across all three generations' low-capacity points, 1/COP ≈ 0.140 + 0.0069 × (LWT − 24), with outdoor temperature at +7…+12 °C.
- At the owner's measured 3.7–3.8 kW floor this gives about **0.52 kW at W24, rising about 0.026 kW/K**. That is ≈0.65 kW at W30 and ≈0.78 kW at W35, for +7…+12 °C outdoor.
- Expect roughly 0.9–1.0 kW at +2 °C and W35 (calc from COP ≈4 at B points).

The same structure, minimum compressor power = full-load power at the same temperatures × minimum load ratio, is what EN 15316-4-2 and the UK Home Energy Model use [9].

**B. Carnot efficiency by speed band.** Same convention (LWT + 2, T_out − 6). These are my recomputed values.

| Band | G3 (2025 cert) | G2 | G1-M |
|---|---|---|---|
| Max-capacity points (A, TOL, warmer B, G) | 0.45–0.50 | 0.41–0.46 | 0.38–0.47 (one anomalous 0.55) |
| Mid points (average B, warmer C) | 0.49–0.54 | 0.47–0.52 | 0.49–0.56 |
| Lowest-capacity points (C/D, 2.4–4.4 kW) | 0.45–0.55 (the 2.78 kW point = 0.55, the 2.43 kW point = 0.53) | **0.49–0.61** (3.1 kW = 0.61, 3.7 kW = 0.56) | 0.42–0.60 |
| EN 14511 A7/W35 full rating | 0.58 | 0.55 | – |

Corrected statement:
- η is about 0.50 ± 0.05 across the map.
- Near maximum speed, η is reliably about 10–15% lower: 0.41–0.50.
- At the lowest tested capacity there is **no consistent penalty**. The spread is −15% to +15% around mid speed.
- The lab "min" points are capacity steps the manufacturer chose. They are not a frequency sweep, so the true minimum frequency is untested.
- These η values depend on the assumed approach offsets (see below), so η is a fitting constant, not a physical property.

## Evidence for

- **Maximum-speed penalty: measured, and consistent with theory.**
  - On every generation the A/TOL/warmer-B points sit at 0.38–0.50, below the mid points [1][2][3].
  - Manufacturer-data analysis of a commercial inverter air-to-water unit (30–120 Hz) shows COP lowest at full speed. COP is highest around 40–60 Hz, up to 20% higher than at 120 Hz [6].
  - The thesis attributes the high-speed loss to suction and discharge pressure drops [6].
- **Some loss at very low speed is physically expected.**
  - Isentropic efficiency falls at low frequency because the oil seal between the high- and low-pressure chambers weakens, and inverter losses vary with frequency [6].
  - This argues for a hump-shaped efficiency curve, not a flat one.
- **G3's minimum input is near the claim's base.**
  - 0.45 kW at A12/W24 (3.28 kW).
  - 0.37 kW at A12/W26 (2.78 kW).
  - 0.48 kW at A7/W25 (2.53 kW) [1].
- **η ≈ 0.45–0.55 as a whole-map constant is a common practitioner default.**
  - OpenEnergyMonitor users treat 0.45–0.55 (or "50%") as a typical factor with the +2/−6 K convention [7][8][10].

## Evidence against

- **No minimum-speed penalty in the certified data.**
  - G2's lowest-capacity points are its best: 0.61 at A7/W27 (3.1 kW) and 0.56 at A12/W24 (3.7 kW) [2].
  - G3's two lowest-output points (2.43 and 2.78 kW) score 0.53 and 0.55, above or equal to its mid points [1].
  - The source note's own table lists the "min" points as 0.45–0.56. The summary's 0.42–0.49 range for "minimum and maximum speed" holds only for maximum speed.
- **The 0.03 kW/K slope mixes output with water temperature.**
  - For G3 the slope is 0.017 kW/K, and its W32 point draws 0.49 kW, not 0.69 kW [1].
  - G2's apparent 0.038 kW/K arises because its warmer-water low points were tested at 4.2–5.2 kW, against 3.1–3.7 kW at W24–27 [2].
  - With output held constant the slope is about 0.02–0.027 kW/K.
- **The 0.45 kW base does not hold for G1.**
  - The certified G1-M floor points draw 0.60–0.65 kW at W24–27 (3.8–4.4 kW) [3].
  - Note 08 identifies the owner's unit as G1 (NhH), and his measured floor of 3.7–3.8 kW also matches G1/G2 rather than G3.
- **η is sensitive to the assumed approach temperatures.**
  - Measured on a Vaillant aroTHERM, the condensing approach was about 1.1 K at 30 rps but about 5.5 K at 50 rps, while the evaporator stayed about 5 K below air [11].
  - With fixed offsets, η is therefore inflated at low load and deflated at high load.
  - Using zero offsets (the EN 15316-4-2 / HEM Carnot definition [9]), my recomputation gives 0.28–0.35 at the +12 °C low-load points against 0.40–0.45 at the max points. That reverses the ranking.
  - So "minimum speed sits inside the efficient plateau" is a statement about a fitting convention, not about the compressor.
- **The lab points are not a frequency sweep.**
  - EN 14825 C/D points are run at whatever capacity step the manufacturer declares.
  - G3's average-climate D point was run at 3.28 kW, although the same unit ran at 2.78 kW at the same +12 °C in the warmer climate [1].
  - G2 at +7 °C was 4.3 kW in the colder climate against 3.1 kW in the average one [2].
  - The true minimum frequency's efficiency is unknown.
- **Field η is lower than lab η.**
  - On a Samsung R32 8 kW, steady 6-hour periods fitted 0.46, and later analysis showed about 35% of Carnot at 40 °C flow around 0 °C outdoor. Humidity moved the factor by about 0.1 [10].
  - heatpumpmonitor.org seasonal SPFs (≈3.5–4.1) against "ideal Carnot" values of ≈8–10.4 (no offsets) imply roughly 0.40–0.45 on that convention [5].
  - The lab values of 0.50–0.61 are optimistic for the field.
- **The water temperatures used for the test points are unverified.** The EN 14825 leaving-water temperatures (W34/30/27/24, W52/42/36/30, colder and warmer variants) are recalled, not read. EUR-Lex only references the tables [4]. A 2–3 K error moves η by about 0.03–0.05 at the low-lift points.

## Applicability to this house

- **Simulator COP law.** Use η ≈ 0.50 (+2/−6 offsets) for lab-like behaviour. Apply about −10–15% near maximum output, which matches the observed ~3 kW catch-up runs at +2 °C.
- **Minimum speed.** Do **not** hard-code a 10% minimum-speed penalty from these data. Either:
  - use no penalty, or
  - fit it from the house's own Modbus logs (compressor frequency, power and flow ΔT), which are the only real frequency-sweep data available.
- **Field derate.** Consider an overall field derate of 0.85–0.9 against Keymark, because of defrost on humid days and sensor and pump effects [5][10].
- **Minimum electrical input.** Model it as Q_min(T_out) / COP(LWT, T_out), not as a fixed intercept.
  - For the owner's unit (likely G1, floor 3.7–3.8 kW), expect **≈0.55–0.65 kW at W24–30 in mild weather, rising ≈0.025 kW/K**.
  - That is not 0.45 kW.
- **Control conclusion.** The direction of the control conclusion survives the corrections: long, low-output, low-LWT runs are the efficient regime, and catch-up bursts at high output are penalised by both speed and water temperature. But:
  - the claim that minimum speed is "inside the plateau" cannot be relied on from certified data;
  - the real argument for running at the floor is the LWT reduction it enables, not a proven η plateau.

## Sources

1. HP KEYMARK, VERSATI AIO G3 8/10 kW (GRS-CQ10PdG/NhH3-E/-M, reg. 041-K004-31), EN 14825 tables, all climates - https://www.heatpumpkeymark.com/en/?type=109126&tx_pskeymark_frontend%5Bsubtype%5D=6328&tx_pskeymark_frontend%5Baction%5D=showSubtype&tx_pskeymark_frontend%5Bcontroller%5D=Frontend&cHash=d0b2a44de2160baf2f6b68e451d10d28 - certified lab data (re-read and recomputed here).
2. HP KEYMARK, VERSATI AIO G2 8-10 kW (GRS-CQ10PdG/NhH2-E, reg. 041-K004-11) - https://www.heatpumpkeymark.com/en/?type=109126&tx_pskeymark_frontend%5Bsubtype%5D=2854&tx_pskeymark_frontend%5Baction%5D=showSubtype&tx_pskeymark_frontend%5Bcontroller%5D=Frontend&cHash=2efe1ec6e62fa6ebea92d25de28523a0 - certified lab data.
3. HP KEYMARK, Versati split G1 8/10 kW (GRS-CQ10Pd/NhH-M, reg. 041-K004-17) - https://www.heatpumpkeymark.com/en/?type=109126&tx_pskeymark_frontend%5Bsubtype%5D=3340&tx_pskeymark_frontend%5Baction%5D=showSubtype&tx_pskeymark_frontend%5Bcontroller%5D=Frontend&cHash=89e8c64ac726c21d458bda49a8f36ae7 - certified lab data.
4. Commission Communication 2014/C 207/02 - https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52014XC0703(01) - regulation. It refers to EN 14825 tables 11–13 / 18–20 but does not print the water temperatures.
5. heatpumpmonitor.org public system list (JSON) - https://heatpumpmonitor.org/system/list/public.json - measured field data. Only the first part was read: weighted_average_ideal_carnot ≈8.0–10.4, SPF ≈3.5–4.1.
6. Dongellini M., "Dynamic modelling and seasonal performance evaluation of air-to-water heat pump systems", PhD thesis, Univ. Bologna - https://amsdottorato.unibo.it/id/eprint/7901/1/Dynamic%20modeling%20and%20seasonal%20performance%20evaluation%20of%20air-to-water%20heat%20pump%20systems.pdf - academic analysis of manufacturer data: COP maximum at 40–60 Hz (range to 120 Hz), up to +20% against nominal; reasons for low- and high-speed isentropic losses.
7. OpenEnergyMonitor forum, "Carnot theoretical COP from which values" - https://community.openenergymonitor.org/t/carnot-theoretical-cop-from-which-values/29201 - forum. A 50% default factor; condensing ≈ flow + 2 K.
8. OpenEnergyMonitor forum, "heatpumpmonitor.org heat pump database minimum modulation tests" - https://community.openenergymonitor.org/t/heatpumpmonitor-org-heat-pump-database-minimum-modulation-tests/29132 - forum/field. Minimum outputs only, no electrical or COP data at minimum, so no support either way.
9. DESNZ, "Modelling Heat Pumps within the Home Energy Model" (HEM-TP-12), Jan 2026 - https://assets.publishing.service.gov.uk/media/6583f139ed3c34000d3bfcc6/hem-tp-12-heat-pump-methodology.pdf - government methodology based on EN 15316-4-2. COP is the exergetic efficiency interpolated between EN 14825 points × Carnot (no offsets); minimum compressor power = full-load power × minimum load ratio.
10. OpenEnergyMonitor forum, "Samsung HT Quiet R32 8 kW emoncms COP vs simulated COP" - https://community.openenergymonitor.org/t/samsung-ht-quiet-r32-8kw-emoncms-cop-vs-simulated-cop-and-zigzag-pattern/27385 - field measurement (single system). Factor 0.46 fitted; ≈35% of Carnot in steady state; typical range 0.45–0.55.
11. OpenEnergyMonitor forum, "Is anyone monitoring condenser and evaporator temperatures" - https://community.openenergymonitor.org/t/is-anyone-monitoring-condenser-and-evaporator-temperatures/29204 - field measurement (indicative, uncalibrated). aroTHERM condensing approach ≈1.1 K at 30 rps against ≈5.5 K at 50 rps.
12. OpenEnergyMonitor docs, "Low temperature" (heatpumpmonitor analysis) - https://docs.openenergymonitor.org/heatpumpmonitor/low_temperature.html - field data across many systems: SPF falls ≈0.10 per K of flow temperature.
13. FZJ hplib README - https://github.com/FZJ-IEK3-VSA/hplib - peer-reviewed tool documentation. Linear regression on Keymark data gives a COP MAPE of ≈10%; it does not model minimum speed, showing Keymark data are commonly used without a speed term.
