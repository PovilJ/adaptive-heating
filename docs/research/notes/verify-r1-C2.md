# Verify r1 – C2: COP cost per +1 K of leaving-water temperature

## Claim

Each +1 K of leaving-water temperature costs about 2.2–3 % of COP, measured within systems at matched outdoor temperature. Supporting figures: a median of 2.24 %/K across 26 systems, and 2.3–2.7 %/K from the Versati full-load table. Note 13 adds that running 1/2/3 K hotter than usual costs 3.6/6.6/10.3 %.

Sources of the claim: notes 01, 02, 13 and 07.

## Verdict: partly_supported

- **The direction and rough size hold.** COP falls with leaving-water temperature by roughly 2–4 % per K at matched outdoor temperature.
- **The 2.2–3 % headline is too low for the conditions where this house spends most of its hours.** Those conditions are A7–A12, W24–36, at part load near minimum compressor speed.
- **The independent check is the EN 14825 part-load certification data.**
  - It covers 1,615 distinct air-to-water models from the HP Keymark database, as mirrored by FZJ hplib [1][2].
  - The median at A7 (W27→W36) is about **3.1–3.3 %/K**.
  - At A12 (W24→W30) it is about **3.9 %/K**.
  - The Versati III itself gives **3.4 %/K at A7** and **4.4–5.6 %/K at A12**.
- **The claim's range fits colder conditions.** At A2 (W30→W42) the median is 2.4–2.7 %/K, and at A−7 it is 1.8–2.1 %/K.
- **Note 13's within-system field figure of 3.6 %/K is therefore not an outlier.** It matches the part-load certification data for mild weather. The 2.24 %/K median from note 01 under-states the mild-weather penalty.
- **Process caveat.** The shared web-search budget ran out after 9 searches, below the 12 requested. The verdict rests mainly on my own analysis of the raw Keymark data, plus 9 pages actually read.

## Corrected claim

At matched outdoor temperature and similar heat output, unit COP falls per +1 K of leaving water by approximately the amounts below.

**EN 14825 part-load points**, median across about 1,600 certified air-to-water models, with the interquartile range (IQR) in brackets [1][2]:

| Outdoor (Tj) | Water compared | Median | IQR |
|---|---|---|---|
| A−7 | W34→W52 | 1.8–1.9 %/K | 1.6–2.1 |
| A+2 | W30→W42 | 2.4–2.5 %/K | 2.1–2.8 |
| A+7 | W27→W36 | 3.1–3.3 %/K | 2.5–3.8 |
| A+12 | W24→W30 | about 3.9 %/K | 2.7–4.9 |

**Colder-climate set** (outlet temperatures as I recall them from the standard; less certain):

| Outdoor (Tj) | Median |
|---|---|
| A−7 | about 2.0–2.1 %/K |
| A+2 | 2.5–2.7 %/K |
| A+7 | 3.2–3.3 %/K |
| A+12 | about 4.1 %/K |

**Gree Versati III** (GRS-CQ8/10Pd/NhH3, average climate, Keymark) [3]:

| Outdoor | Water compared | Loss |
|---|---|---|
| A−7 | W34→W52 | 1.7–1.8 %/K |
| A+2 | W30→W42 | 2.9 %/K |
| A+7 | W27→W36 | 3.4 %/K |
| A+12 | W24→W30 | 4.4–5.6 %/K |

The A+7 and A+12 Versati points are at about 3.0–3.3 kW, which is at or near its minimum capacity.

- **The rule therefore depends on lift.** The loss per K is roughly 1/(lift) or somewhat steeper, so each kelvin costs more in mild weather.
- **Suggested exchange rate for this controller:**
  - about **2 %/K below −5 °C**;
  - about **2.5 %/K around 0 to +3 °C**;
  - about **3–3.5 %/K at +5 to +10 °C**;
  - about **4 %/K above +10 °C**, with wide uncertainty there (IQR 2.7–4.9).
- **Over a few kelvin the loss compounds roughly log-linearly.** At A7, +1/+2/+3 K costs about 3/6/9 %. This is consistent with note 13's 3.6/6.6/10.3 %.
- **For whole-system SPF, including DHW, pumps and standby, the effect is diluted.**
  - The cross-system HeatpumpMonitor fit is −0.10 SPF per K, which is about 2.5 %/K at SPF 4 [4].
  - Simulated ground-source systems with DHW give about 1.1 %/K (sibling note 02; not re-verified).
- **Validity limits.**
  - These figures compare leaving-water temperatures at the same outdoor temperature and similar load.
  - They do not price what a higher setpoint does to compressor speed. Higher speed is a separate and often larger penalty (Vaillant example: COP 4.6 at 40 rps vs 3.3 at 110 rps at 35/30 [5]).
  - Nor do they price the indirect effect of cycling on mean flow temperature.

## Evidence for

- **[1] Võsa, Simson, Mikola, Kurnitski (TalTech/Aalto, 2026), Keymark population dataset.**
  - Mixed-effects fit to 53,551 EN 14825 part-load points from 3,395 heat-pump groups: COP = 7.26 − 1.853·ln ΔT + 18.05/√ΔT, where ΔT is lift.
  - My derivative of that fit:

    | Lift | Loss |
    |---|---|
    | 20 K | 3.4 %/K |
    | 25 K | 3.0 %/K |
    | 30 K | 2.75 %/K |
    | 40 K | 2.5 %/K |

  - The cold-only model gives about 2.6 %/K at 30 K.
  - The page does not define ΔT. I assume it means supply minus outdoor.
  - Out-of-sample validation against WPZ Buchs lab data: R² 0.84. However, part-load points carried a −0.22 COP bias.
  - Evidence type: certified lab data, statistical model.
- **[2] Own analysis of the raw HP Keymark CSVs mirrored in FZJ hplib** (2,634 files, 1,731 unique models with EN 14825 data).
  - For each model and Tj, I took ln(COP at 35 °C application / COP at 55 °C application) divided by the outlet-temperature difference.
  - EN 14825 variable-outlet temperatures, average climate:
    - 35 °C application: 34/30/27/24 °C at Tj −7/+2/+7/+12.
    - 55 °C application: 52/42/36/30 °C.
  - Both applications use the same part-load ratio at each Tj. This is exactly the "same outdoor, similar load, different leaving water" comparison.
  - Results are in the corrected-claim tables above.
  - Restricting to models whose declared capacity differs by less than 10 % between the two applications barely moves the medians. That subset is less confounded by cycling or speed differences:

    | Tj | Median (similar-capacity subset) |
    |---|---|
    | A−7 | 1.81 |
    | A+2 | 2.42 |
    | A+7 | 3.10 |
    | A+12 | 3.85 %/K |

  - Evidence type: certified lab data, my calculation.
- **[3] Gree Versati III Keymark entries** (split/AIO GRS-CQ8.0/10Pd/NhH3, from the same data). Average-climate COP at 35 vs 55 °C application:

  | Tj | COP (35 / 55 application) | Loss |
  |---|---|---|
  | A−7 | 3.15 / 2.29 | 1.8 %/K |
  | A+2 | 4.59 / 3.24 | 2.9 %/K |
  | A+7 | 5.67 / 4.17 | 3.4 %/K |
  | A+12 | 7.34 / 5.24 (E variant) | 5.6 %/K |
  | A+12 | 6.83 / 5.24 (M variant) | 4.4 %/K |

  - The capacity at A7/A12 is about 3.0–3.3 kW in both applications.
  - Evidence type: certified lab data, manufacturer-declared.
- **[4] HeatpumpMonitor.org low-temperature guidance** (field, across systems).
  - SPF H4 = 7.42 − 0.101·T_flow, with R² 0.52. That gives 4.4 at 30 °C, 3.9 at 35 °C and 3.4 at 40 °C, or −2.3 to −2.9 %/K.
  - Against flow minus outside: −0.105 SPF per K, R² 0.55.
  - Evidence type: field data, cross-sectional.
- **[7] Danish Technological Institute, OPSYS main report (2018).**
  - Typical value: "an increase of 1°C ... leads to a decrease of 2-3%" in COP.
  - On their ground-source UFH test rig, MPC lowered the forward temperature 0.3–0.9 K and system COP rose 2.1–2.3 %. That is ≥2.5 %/K, but it is confounded with mass-flow changes.
  - Evidence type: lab rig, plus a rule of thumb.
- **[8] Fraunhofer ISE, WPsmart im Bestand (Chillventa 2020).** SPF correlated only with heating-circuit temperature. The design-point temperature was not decisive; the heating curve was. This is qualitative support that operating flow temperature is the dominant lever.
  - Evidence type: field monitoring.
- **Constant-efficiency Carnot model** (my calculation; condensing 2 K above flow, evaporating 6 K below air). It predicts 1.4/2.1/2.8/4.0 %/K at the four Keymark comparisons.
  - Certified data are about 20–30 % steeper than that at −7 to +7 and match it at +12.
  - So constant-Carnot is, if anything, a slight under-estimate.

## Evidence against / contradictions

- **The claim's own 2.24 %/K (note 01) and the Versati full-load table (2.3–2.7 %/K, note 02) are lower than the part-load certification data at A7–A12.**
  - The likely reasons:
    - pooling across all outdoor bands;
    - full-load rather than part-load conditions;
    - higher-flow radiator systems in the UK fleet, where lift is larger and the percentage per K smaller.
  - These figures are not wrong. They describe colder or higher-lift operation.
- **Datasheet averages give smaller values.** Averages of R290 models (reduco.ai, from datasheets and Stiftung Warentest) give only 1.9–2.2 %/K between W35 and W45 at A2–A7, and 1.4–2.0 %/K at W45→55 [6].
  - This is full-load nominal data at higher water temperatures, so lift is larger.
  - It shows the per-K figure shrinks at higher flow and colder air.
- **The spread at mild conditions is wide.**
  - At A12 the p10–p90 range is 1.6–5.8 %/K.
  - Some models declare near-flat COP because they cycle at minimum capacity in both applications, and Cdh dominates.
  - The A12 figure should not be taken as precise.
- **Certification points may not reflect real operation.**
  - Keymark points are tested with manufacturer-fixed compressor settings.
  - Part-load points under-predicted lab hold-out COP by 0.22 on average [1].
  - The BAM/EVPG dynamic-testing initiative exists partly because fixed-setting tests may not reflect real controller behaviour.
  - This weakens the absolute values but not obviously the 35-vs-55 ratio.
- **Colder-climate outlet temperatures could not be confirmed.** I used the colder-climate values from memory. Some individual models, including the Versati at colder-climate A7 (about 1 %/K), give implausible results, so treat the colder-climate rows as indicative only.
- **Unit COP does not equal bill impact.** DHW, pumps, defrost and standby dilute the per-K effect on seasonal SPF to roughly half [4], and see note 02.

## Applicability to this house

- **The house's mild-weather regime is the high-penalty regime.** That regime is +2 to +12 °C outdoors, with the unit at or near its 3.7–3.8 kW minimum and water at 25–36 °C. Use **3–4 %/K** there, not 2.2 %/K.
  - Example: 36 °C instead of 30 °C at +7 °C costs roughly 18–20 % of unit COP.
- **The Versati III's own certified points cover exactly this regime and are steep.** They show 3.4 %/K at A7 and 4.4–5.6 %/K at A12, at about 3 kW.
  - The installed unit may be a different generation. The owner should confirm the model so the matching Keymark entry can be used.
- **In cold spells (−5 °C and below), 2 %/K is adequate.** Each kelvin matters less there, and capacity and comfort dominate.
- **For controller trade-offs** (starts vs flow temperature vs PV time-shifting), use an outdoor-dependent exchange rate rather than a constant. A simple form is %/K ≈ 100/(T_flow − T_out + 8), which tracks the Keymark medians within about 0.5 %/K from A−7 to A7 (my fit, approximate).
- **Account for compressor speed as well.** A higher setpoint usually also means a faster compressor during catch-up. That costs additional COP not captured in these per-K figures [5].

## Sources

1. Võsa K.-V., Simson R., Mikola A., Kurnitski J. "European Heat Pump Keymark Population Dataset and COP Models for Cold-Climate Building Simulation", v2.0, Zenodo, Aug 2026. https://zenodo.org/records/22029915 (also https://research.aalto.fi/en/datasets/european-heat-pump-keymark-population-dataset-and-cop-models-for-/). Certified lab data, statistical model.
2. FZJ-IEK3-VSA, hplib. The repository mirrors HP Keymark datasheets (downloaded from keymark.eu, 2023-04) as CSV in input/csv. Variable map in input/README.md. https://github.com/FZJ-IEK3-VSA/hplib. Certified lab data; the analysis of 1,731 models is my own calculation.
3. HP Keymark entries for Gree Versati III (GRS-CQ8.0/10Pd/NhH3-E/M + SXTVD300LC/B), via [2]: input/csv/_Gree_Electric_Appliances,_Inc._of_ZhuhaiVersati_monobloc_G3_G4_8_10k.csv and related files. Manufacturer-declared certified data.
4. OpenEnergyMonitor. "HeatpumpMonitor: low temperature / design flow." https://docs.openenergymonitor.org/heatpumpmonitor/low_temperature.html. Field data, cross-sectional regression.
5. OpenEnergyMonitor. "% of ideal Carnot COP." https://docs.openenergymonitor.org/heatpumpmonitor/prc_carnot.html. Field data plus a manufacturer table: 45–55 % of Carnot typical, and COP 4.6 at 40 rps vs 3.3 at 110 rps.
6. reduco.ai. "COP, JAZ & SCOP: Wärmepumpen-Effizienz einfach erklärt" (2026). https://reduco.ai/blog/heizung/waermepumpe-cop-jaz-wirkungsgrad. Secondary: averages of manufacturer datasheets and Stiftung Warentest. Search snippets also gave the Bosch "up to 2.5 % per degree" and 42watt "2.5–3 % COP" rules of thumb (manufacturer/blog claims).
7. Danish Technological Institute (Jensen S. Ø. et al.). "Combined optimization of heat pumps and heat emitting systems (OPSYS) – main report", 2018. https://www.teknologisk.dk/_/media/72043_OPSYS%20main%20report.pdf. Lab rig plus a rule of thumb.
8. Fraunhofer ISE. "Effizienzanalyse von Wärmepumpen im Bestand" (Chillventa 2020). https://www.ise.fraunhofer.de/content/dam/ise/de/documents/publications/conference-paper/091_Fraunhofer-ISE_Chillventa-2020_1015_EFFIZIENZANALYSE%20VON%20WÄRMEPUMPEN%20IM%20BESTAND.pdf. Field monitoring; qualitative.
9. CIBSE Journal. "Bridging the heat pump efficiency divide." https://www.cibsejournal.com/technical/bridging-the-heat-pump-efficiency-divide/. Field data summary. The flow-minus-outside correlation (R² 0.55) is the strongest predictor.
10. Heat Pumping Technologies (IEA HPT). "O.1.4.5 High efficiency heat pumps for low temperature lift applications." https://heatpumpingtechnologies.org/publications/o-1-4-5-high-efficiency-heat-pumps-for-low-temperature-lift-applications/. Lab: Carnot efficiency of about 60 % held roughly constant over 10–30 K lift for an optimised turbo unit. This supports a constant-efficiency approximation at low lift.
11. Heat pump test report to EN 14825:2013 (Heat Pumps Ireland, AQ-13AQ). https://heatpumpsireland.ie/wpcms/wp-content/uploads/2018/06/4P01457-02-Report-AQ-13AQ.pdf. Lab test. It confirms that the variable-outlet test temperatures differ by Tj, with the 55 °C application at 52.0 °C at Tj −7.
