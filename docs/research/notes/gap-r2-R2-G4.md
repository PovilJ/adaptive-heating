# Gap R2-G4: At 0 to +4 °C and 85-95% RH, how does run-block structure change defrost count and energy per kWh of heat: few long runs versus many short ones? Does frost melt or sublimate during compressor-off periods (fan stopped), and does the Gree accumulated-run counter (which does not reset on stop) then trigger defrosts on lightly frosted coils?

> Follow-up to Gap G7 (open question 6). Written 2026-11-06.
>
> **How this note was produced.**
> - **Web search was not available.** The shared per-turn web-search budget was already used up when this pass started. All 3 attempted searches were refused.
> - **Sources.** I read 17 sources by direct URL instead: manuals, a thesis, abstracts, forum threads and blogs. Several were PDFs that I parsed locally.
> - **New evidence.** The main new evidence is my own analysis of **minute-level heatpumpmonitor.org data**:
>   - **29 air-to-water systems** from 13 brands, winter 2025-26 (1 Nov - 31 Mar). Of these, 27 are UK, 1 is Croatia and 1 is Netherlands. The Gree unit is in Ottawa.
>   - A **replication on 4 systems** for winter 2024-25, including the only Gree on the platform.
>   - Humidity from the **ERA5 reanalysis** (via Open-Meteo) at each site [1][2][3].
> - **Physics.** The frost-melting physics is my own heat and mass balance (Magnus psychrometrics). It is labelled as such.
> - **Scope.** I did not read the repository's code or docs outside docs/research/notes/.

## Summary

1. **Run structure barely changes how many defrosts you get per kWh of heat at 0…+5 °C and RH ≥ 80 %** [1].
   - **Method.** I compared 6-hour windows in which the unit ran almost continuously (duty ≥ 85 %) with windows in which it cycled (duty ≤ 70 %, at least 1 start per 2 run-hours). The comparison was stratified by 1 K of outdoor temperature and by RH class (80-90 % and ≥ 90 %).
   - **Result.** Cycling windows had a Mantel-Haenszel rate ratio of **1.05 defrosts per kWh of heat** and 1.07 per run-hour. That is no material difference. Data: 18 systems, about 75,000 kWh of heat, 4,400 defrosts.
   - **Spread between systems is large:** 0.22× to 2.25×.
   - **The confound matters.** A naive comparison showed cycling had 20-35 % fewer defrosts, but that came almost entirely from cycling windows being about 0.8 K warmer.
2. **COP was the same in cycling and steady windows.** Within temperature/RH strata, COP was 0.99× (0…+5 °C) and 0.96× (+5…+9 °C) [1]. As far as defrost is concerned, "few long runs vs many short runs" is a wash at 0…+5 °C.
3. **Defrosts in cycling windows were lighter.** Reversed heat (heat pulled back out of the water during defrost) was **2.5 % of delivered heat when cycling, against 3.7 % when steady** (0…+5 °C, stratified) [1]. That is about one-third less defrost heat at the same defrost count.
4. **Outdoor temperature and humidity at the time the heat is made matter far more than run structure** [1]. Steady and cycling windows were pooled here. The data cover 27 systems and about 8,000 six-hour windows.

   | Outdoor temp, RH ≥ 90 % | Defrosts per 100 kWh of heat | Reversed heat (% of heat) | COP |
   |---|---|---|---|
   | 0 °C | 12.9 | 6.6 % | 2.79 |
   | +1 °C | 11.8 | 5.8 % | 3.00 |
   | +2 °C | 7.6 | 3.7 % | 3.20 |
   | +3 °C | 5.4 | 2.4 % | 3.47 |
   | +4 °C | 2.6 | 1.1 % | 3.69 |
   | +5 °C | 2.0 | 0.7 % | 3.84 |

   - Moving from 80-90 % to ≥ 90 % RH raises defrosts by 1.1-1.75× at −2…+3 °C.
   - Below 80 % RH, defrost counts roughly halve.
   - So moving heat output 2-3 K warmer (from night into early afternoon) cuts defrost count and defrost heat per kWh **by 2-5×**. That is far more than any run-structure effect.
5. **There is some evidence that off-time partly "un-frosts" the coil at +1.5…+5 °C, but it is weak and inconsistent** [1][2].
   - **Method.** For each running minute I computed the defrost hazard, matched on run-minutes since the last defrost and minutes since restart.
   - **2025-26 pooled result.** After an off-gap of 10-180 min, the hazard was about **0.70-0.72×** that of no-gap runs (27 systems).
   - **Cold control.** In the −6…−1 °C control band the same ratio was **1.0×**, as physics predicts: no melting below 0 °C.
   - **Caveats.**
     - Off-gaps longer than 3 h showed no benefit (1.04×).
     - Only 10 of 17 systems pointed the same way.
     - The 2024-25 replication on 3 systems gave 0.94-1.09×.
   - **Confidence: low-medium.**
6. **Defrosts that follow an off-gap are about 14 % smaller** [1][2].
   - Median ratio of reversed heat per defrost after a gap of 20 min or more: **0.86×** at +1.5…+5 °C (9 systems), 0.90× at 0…+1.5 °C, 0.93× at −6…−1 °C.
   - The 2024-25 replication gave 0.75-0.89×.
   - Samsung Gen 7 units showed 0.08-0.5×. Their demand logic apparently defrosts lightly frosted coils after restarts.
   - This is the clearest sign that frost partly melts while the unit is off and that some logic still defrosts the lightened coil.
7. **In the target regime, sublimation is physically negligible. Off-cycle frost loss is melting, and its rate is very uncertain** (own calc).
   - **Why no sublimation.** At +2 °C / 90 % the air's vapour pressure (635 Pa) is above that of ice at 0 °C (611 Pa). The same holds at +3…+4 °C at every RH ≥ 85 %. Water vapour keeps condensing on the coil, which *adds* about 15-60 % to the melting heat.
   - **When sublimation is possible.** Only at about 0…+1 °C and RH ≤ 90 %, and then only at a rate of about 0.05 kg/h or less.
   - **Melting rate.** With the fan stopped, melting depends on how much heat the still air delivers to the coil, i.e. on its heat-transfer conductance UA, which I estimate at 10-90 W/K. That gives roughly 0.1-1.0 kg of frost melted per hour for each K of air temperature above 0 °C.
   - **Compare with frost load.** A frosted coil at the defrost trigger carries about 1-2.6 kg [4][G7].
   - **So:** a 1-h stop at +3 °C may remove anything from about 15 % to all of the frost. This matches the weak, scattered field signal.
8. **Melt water does not all leave the coil.** Retained droplets on fins refreeze at restart [4]. Manufacturers allow 3 min of "drip time" after a defrost for this reason [8]. So off-cycle melting is worth less than its gram count suggests.
9. **The Versati's fan stops with the compressor.** Normal shutdown on the Versati III:
   - the compressor ramps down to minimum and stops;
   - the electronic expansion valve opens fully;
   - then the fan stops. No post-run fan is documented [5].

   Fan-on "compressor-shutdown defrost" is the textbook passive method [6]. The Versati does not do it, so passive melting relies on still air and wind. That is the lower half of the UA range above.
10. **On Gree firmware, defrosts cluster just after a restart** [1][2]. This is the Ottawa Gree, a split unit, the only Gree on the platform.
    - At 0…+5 °C, **93-99 % of defrosts came within 20 min of a restart** (median 12-13 min into the run).
    - Accumulated run between defrosts: median 81-88 min (p5: 70-71 min) at 0…+5 °C, and 72-74 min at −6…−1 °C.
    - Intervals that contained off-gaps of 30 min or more needed a median 137-155 run-minutes.
    - **Interpretation.** The clock does not reset, but the coil-temperature gate often holds a defrost off on a warm, lightly frosted coil. When the clock is full, the restart transient (a cold coil before the fan and valve settle) appears to satisfy the gate. A defrost then fires early in the next run.
    - Reversed heat per Gree defrost was the same at 0…+5 °C as at −6…−1 °C (about 0.23 vs 0.19-0.26 kWh). So these early-run defrosts are not obviously "empty", but they are short (about 2 min).
11. **Other brands differ.**
    - Fujitsu forces a defrost after **40 short runs of < 10 min**, so short-cycling can itself trigger a defrost [7].
    - Samsung starts on evaporator temperature below a line for 3 min [9].
    - M-TEC uses a 10 K air-minus-suction difference [10].
    - Nibe S2125 owners report defrosts on clear coils ("designed for the worst case") [10].
    - Per-event cost spans 0.07-0.87 kWh of reversed heat across 29 systems [1]. Examples: 570 Wh drawn from the house on a Samsung [9]; 0.6 kWh_el from a pre-heated internal buffer on a Viessmann [11].
12. **For this house, run-block structure is not a defrost lever; timing is** (medium confidence).
    - At 0…+4 °C the house needs about 2.5-4.4 kW, close to the Versati's 3.7 kW minimum. The real choice is "near-continuous at minimum" vs "blocks with 0.5-3 h gaps". The data say these give the same defrost count per kWh and the same COP [1].
    - With 6.6 kWh/K of slab storage, shift production into the warmest 6-8 h of the day. Avoid running the humid, cold pre-dawn hours. This cuts defrost count per kWh by 2-5× at about +2…+5 °C daytime [1].

## Detailed findings

### 1. Data and method (own field analysis [1][2][3])

- **Systems.** Air-source systems on heatpumpmonitor.org with 1-minute electricity, heat and outdoor temperature data over winter 2025-26:
  - 31 qualified; 2 were too sparse, leaving 29;
  - brands: Vaillant, Viessmann, Mitsubishi ×4, Daikin ×4, Kronoterm ×2, Ideal ×2, Panasonic ×3, Samsung ×4, Stiebel Eltron, Nibe, Octopus Cosy, Bosch, LG, Midea ×2, Gree.
  - Replication for winter 2024-25 on Gree 251, Mitsubishi 2 and Samsung 116/382. The other 4 requested systems were too sparse that winter.
- **Weather.** Hourly ERA5 temperature and RH per site from Open-Meteo [3]. All temperature bands below use the ERA5 temperature, not the unit's own sensor.
- **Running.** A minute counts as running when electricity is above the system's 10th percentile + 150 W.
- **Defrost.**
  - A defrost is at least 2 consecutive minutes of negative heat (heat < −150 W) while powered, merged across gaps of ≤ 3 min.
  - It must reverse at least 0.05 kWh of heat. This filter removes run-end blips. It cut, for example, Viessmann 1163 from 550 events to 107.
  - Median durations after filtering: 2-7 min. Gree about 2 min; Vaillant 5; Samsung 4-5; LG 6.
- **Off-gap.** At least 3 consecutive non-running minutes. Gaps of 1-2 min are filled in.
- **Hot water.** Space heating and domestic hot water are not separated. Hot-water runs are included, which is fine for frost physics.
- **Main limitations.**
  - Units differ in defrost logic, and pooling dilutes brand-specific effects.
  - Cycling windows at 0…+5 °C are a minority: 1,950 of about 14,400 run-hours.
  - ERA5 RH is a grid-cell value, not a measurement at the coil.
  - No coil temperature or frost mass is measured. Frost is inferred from defrost count and reversed heat.

### 2. Few long runs vs many short runs at 0…+5 °C [1]

- **Window classes.** 6-h windows with ≥ 30 run-min and > 0.3 kWh of heat, RH ≥ 80 %:
  - "steady" = duty ≥ 0.85;
  - "cycling" = duty ≤ 0.70 and ≥ 0.5 starts per run-hour.
- **Crude pooled result, 0…+5 °C, Gree excluded:**

  | | Defrosts per run-hour | Defrosts per 100 kWh | COP |
  |---|---|---|---|
  | Steady | 0.32 | 6.1 | 3.27 |
  | Cycling | 0.23 | 4.2 | 3.17 |

- **Stratified result** (1 K × RH class; Mantel-Haenszel):

  | Band | Rate ratio, cycling / steady (per run-h; per kWh) | Systems |
  |---|---|---|
  | −2…0 °C | 1.15; 1.23 | 5 |
  | 0…+2 °C | 1.03; 1.00 | 14 |
  | +2…+5 °C | 1.09; 1.07 | 17 |
  | 0…+5 °C | **1.07; 1.05** | 18 |
  | +5…+9 °C | 1.83; 1.69 | 16 |

- **The crude "cycling has fewer defrosts" result is a temperature confound.**
  - Cycling windows averaged about 3.5 °C; steady windows about 2.7 °C.
  - At 0…+5 °C, that 0.8 K is worth about 25-40 % in defrost rate (see section 4).
- **Spread between systems at 0…+5 °C.**
  - Vaillant 1497 0.26×, Panasonic 229 0.22×, LG 895 0.26×, Midea 118 0.37×.
  - Samsung 723 2.25×, Ideal 999 2.02×, Samsung 116 1.6×.

  The answer is brand-specific. A pooled "no difference" does not mean "no difference on a Gree".
- **COP and defrost heat, stratified.**
  - COP ratio cycling/steady, weighted by stratum: 0.99 (0…+5 °C), 0.97 (0…+2 °C), 1.00 (+2…+5 °C), 0.96 (+5…+9 °C).
  - Reversed heat per kWh: 0.025 cycling vs 0.037 steady at 0…+5 °C; 0.040 vs 0.060 at 0…+2 °C.

  So cycling at the same defrost count shows less defrost heat per kWh, but the COP is no better overall. Restart losses roughly cancel the lighter defrosts.
- **+5…+9 °C.** Cycling raises defrosts per kWh 1.7×, but from a tiny base: about 1.1-1.3 per 100 kWh, 0.3 % reversed heat. Restart transients are the likely cause: the coil dips below 0 °C right after a start. Irrelevant in energy terms.

### 3. Does frost melt or sublimate while the compressor and fan are off?

**3a. Physics (own calculation, Magnus formulas)**

- **Sublimation needs the air to be drier than ice at the frost surface.** The frost surface warms towards 0 °C after a stop. At 0 °C, saturation over ice is 611 Pa.

  | Air | 85 % RH | 90 % RH | 95 % RH |
  |---|---|---|---|
  | +2 °C | 600 Pa | 635 Pa | 670 Pa |
  | +3 °C | 644 Pa | 682 Pa | 720 Pa |
  | +4 °C | 691 Pa | 732 Pa | 772 Pa |

  Above 611 Pa, vapour keeps condensing onto the 0 °C surface instead of leaving it. In the asked regime (0…+4 °C, 85-95 %), net sublimation is only possible at about 0…+1.5 °C with RH ≤ 90 %. Even there:
  - the driving difference is ≤ 90 Pa;
  - sublimation cools the frost below air temperature, so it stalls;
  - the rate for a 9 kW coil is about 0.05 kg/h or less. Negligible.
- **Melting.** Once the frost surface is at 0 °C, heat from air above 0 °C melts it. Liu calls this frost "ageing": crystals melt once the surface exceeds 0 °C [4].
- **Heat-balance estimate.**
  - Per m² and per W/m²K of conductance, the heat flow is about 3 W at +1 °C, 6 W at +2 °C, 12 W at +4 °C.
  - Condensation adds latent heat: about +1 W/m² at +2 °C / 90 %, +5.6 W/m² at +4 °C / 90 %, +7.5 W/m² at +4 °C / 95 %. At 0…+1 °C / ≤ 90 % it is slightly negative.
- **Conductance with the fan stopped is the big unknown.**
  - Low end: coil treated as a 2-3 m² block with natural convection plus some wind, about 10-30 W/K.
  - High end: the full finned area (about 30-45 m² for a 9 kW coil at 1.7 mm fin pitch) at about 2-3 W/m²K, about 90 W/K.
  - Result: about **0.1-1.0 kg of frost melted per hour per K of air above 0 °C**, plus the condensation bonus.
- **Warming up first.** The coil's own mass (about 15-20 kg of aluminium and copper, about 12-15 kJ/K) must warm about 5-8 K before melting starts. That costs about 70-120 kJ, the equivalent of 0.2-0.35 kg of melt.
- **Possible extra heat source.** At shutdown the Versati opens the expansion valve fully [5]. Pressure equalisation and the off-cycle migration of refrigerant from the warm plate exchanger (about 30 °C water) to the cold coil carry some heat into the coil. This is the same migration that causes up to 11 % cycling COP loss [12][13]. It acts as a small free "heat pipe" defrost. It is not quantified for any unit (hypothesis).
- **Frost load to compare against.**
  - Liu's lab ASHP melted **1.95 kg in a 402-s defrost** after an extended run at 2 °C / 84 % RH [4].
  - G7 estimated about 2.6 kg per cycle (0.37 kg/kW).
  - My psychrometric estimate for the Versati at minimum output and +2 °C / 90 %: about 0.5-1.5 kg of frost per run-hour, depending on fan airflow.
- **Conclusion.**
  - A 30-60 min stop at +2…+4 °C can remove somewhere between about 10 % and all of the frost from 30-60 min of running.
  - At 0…+1 °C it removes little.
  - Below 0 °C it removes nothing.
  - The range is wide because no source measures fan-off melting on an outdoor coil. The ORNL review lists "compressor-shutdown defrost" only in its fan-ON form, using ambient air, with a "low" defrost effect [6]. 42watt says frost often melts by ambient heat alone above about +5 °C [8].

**3b. Field signal [1][2]**

- **Hazard test (2025-26).** Defrost risk per running minute, matched on run-minutes since the last defrost (10-min bins) and minutes since restart (< 10, 10-30, ≥ 30). Gree excluded.

  | Band | Ratio after gap vs no gap | Events after gap | Systems |
  |---|---|---|---|
  | −6…−1 °C, 10-60 min gap | **1.01** | 45 | 15 |
  | 0…+1.5 °C, 10-60 min | 0.67 | 50 | 20 |
  | 0…+1.5 °C, 60-180 min | 0.80 | 29 | 16 |
  | 0…+1.5 °C, > 180 min | 1.95 | 11 | 11 |
  | +1.5…+5 °C, 10-60 min | **0.72** | 186 | 27 |
  | +1.5…+5 °C, 60-180 min | **0.70** | 100 | 25 |
  | +1.5…+5 °C, > 180 min | 1.04 | 102 | 24 |
  | +5…+9 °C, 10-60 min | 0.74 | n/a | 26 |
  | +5…+9 °C, 60-180 min | 0.92 | n/a | 26 |
  | +5…+9 °C, > 180 min | 0.84 | n/a | 23 |

  This is consistent with partial melting at above-zero temperatures and none below zero. But:
  - the "> 3 h" gaps show no benefit;
  - per system at +1.5…+5 °C, 10 of 17 systems were below 1 and 6 above (e.g. Daikin 627 at 1.98, Mitsubishi 912 at 2.35);
  - the 2024-25 replication (3 systems) was 0.94 / 1.09 / 1.55 at +1.5…+5 °C. Only Mitsubishi 2 was stable at about 0.63-0.69 in both winters.
- **Defrost size after a gap.** Median per-system ratio of reversed heat per defrost, gap ≥ 20 min vs no gap, at matched accumulated run time:

  | Winter | +1.5…+5 °C | 0…+1.5 °C | −6…−1 °C |
  |---|---|---|---|
  | 2025-26 | 0.86 (9 systems) | 0.90 (5) | 0.93 (2) |
  | 2024-25 | 0.75 (3) | 0.89 (2) | Gree 0.83 |

  - Durations were unchanged at 1-min resolution.
  - Samsung 382 (0.22 vs 0.44 kWh; 0.12 vs 0.48 kWh in 2024-25) and Samsung 723 (0.07 vs 0.87 kWh) stand out: after stops they run a defrost on a lightly frosted coil.
- **Reading.** Off-periods do take some frost off at +1.5…+5 °C. The effect is mostly seen as lighter defrosts, not fewer defrosts, because most controllers' run-time or temperature triggers do not "know" the coil got lighter. That is exactly the Gree concern.

### 4. Temperature and humidity dominate (own analysis [1])

- **Data.** 27 non-Gree systems, 2025-26, all 6-h windows with ≥ 30 run-min, by 1 K bin and RH class. Values are defrosts per 100 kWh of heat / reversed heat as % of heat / COP.

  | Temp | RH < 80 % | RH 80-90 % | RH ≥ 90 % |
  |---|---|---|---|
  | −2 °C | 5.5 / 3.1 % | 11.5 / 5.5 % | 20.2 / 8.6 % |
  | 0 °C | 5.2 / 2.3 % | 11.6 / 5.5 % | 12.9 / 6.6 % / COP 2.79 |
  | +1 °C | 4.2 / 2.0 % | 7.3 / 3.9 % | 11.8 / 5.8 % / COP 3.00 |
  | +2 °C | 3.4 / 1.8 % | 5.9 / 3.3 % | 7.6 / 3.7 % / COP 3.20 |
  | +3 °C | 3.0 / 1.8 % | 4.0 / 2.2 % | 5.4 / 2.4 % / COP 3.47 |
  | +4 °C | 2.2 / 1.1 % | 2.7 / 1.4 % | 2.6 / 1.1 % / COP 3.69 |
  | +5 °C | 1.8 / 0.7 % | 2.0 / 1.0 % | 2.0 / 0.7 % / COP 3.84 |
  | +7 °C | 0.8 / 0.2 % | 0.6 / 0.2 % | 0.9 / 0.3 % |

- **Reading.**
  - Each +1 K between 0 and +4 °C cuts defrosts per kWh by roughly 25-50 % at high RH.
  - At 0…+3 °C, RH ≥ 90 % roughly doubles defrosts compared with RH < 80 %.
  - The defrost penalty mostly ends by +4…+5 °C, consistent with Kropas' onset of < 3.5 °C / > 85 % RH in Vilnius (cited in G7).
- **Field anecdote.** One UK owner saw a defrost every 90-120 min at −0.9…+1.9 °C. In noise-reduction (low-output) mode this became about every 40 min. Frost was seen at +3 °C [14].
- **Versati III.** In quiet mode (slow fan) it defrosted every 52-56 min at +2…+5 °C [15].

### 5. The Gree accumulated counter and lightly frosted coils

- **Documented logic** (Gree family; Versati I/II and the Neo split, see G7). Defrost needs:
  - accumulated compressor time over about 45-90 min, which is **not cleared by setpoint stops**; and
  - a coil-sensor temperature gate, e.g. ≤ −6 °C coil at −2…+5 °C outdoor on the Neo.
- **Versati III.** It claims adaptive "smart defrost": defrost when necessary, more when frosting is heavy, less when light [5]. It gives no numbers.
- **What the Ottawa Gree split shows** [1][2]:
  - **Where defrosts fall in a run.** At 0…+5 °C, 99 % (2025-26, 110 intervals) and 93 % (2024-25, 107 intervals) of defrosts came within 20 min of a compressor restart, a median 12-13 min in. At −6…−1 °C the shares were 63-71 %, with a median 19-21 min.
  - **Accumulated run between defrosts.** At 0…+5 °C: p5 70-71 min, median 81-88 min, p95 244-493 min. Nearly all intervals contain stops: this unit sits on a 300 L buffer and cycles.
  - **Intervals with off-gaps of 30 min or more** needed 137-155 accumulated run-minutes at 0…+5 °C, against 90-137 at −6…−1 °C.
- **Interpretation (medium confidence).**
  - The clock alone does not fire defrosts. On a warm, lightly frosted coil the coil gate defers them, often for a whole additional clock period.
  - Once the clock has passed, the next restart's suction-pressure dip brings the coil sensor below the gate within about 10-15 min. The defrost then fires early in the run whether or not off-time melted frost.
  - So the answer to "does the counter trigger defrosts on lightly frosted coils?" is **probably yes, sometimes**: via the restart transient, not purely on the clock.
  - The cost is bounded. Gree defrosts here reversed about 0.2-0.25 kWh and lasted about 2 min, the same at 0…+5 °C as at −6…−1 °C. That suggests the coil-temperature exit ends them quickly when there is little ice.
  - **Caveat.** This is a split unit with a different outdoor coil and fan, and it does not use the Versati III firmware.
- **Other brands.** Fujitsu counts short runs: 40 runs of < 10 min force a defrost, and the count clears only at a defrost [7]. Other firmwares can therefore make many short pulses *add* defrosts.

## What this means for controlling this house

Confidence: H high, M medium, L low.

1. **Do not choose run-block structure to manage defrost at 0…+4 °C (M).**
   - Across 18 systems, cycling vs steady changed defrosts per kWh by ×1.05 and COP by ×0.99 once temperature and RH were controlled [1].
   - Choose block structure for other reasons: flow temperature, start losses, PV and battery timing, and comfort.
   - At 0…+4 °C the house needs about 2.5-4.4 kW, close to the 3.7 kW minimum. Near-continuous minimum-output running is natural and fine.
2. **Shift heat production into the warmest hours (H for direction, M for size).**
   - With 6.6 kWh/K of slab storage, storing 0.5-1 K of slab temperature (3-7 kWh) during the warmest 6-8 h can be enough to skip or shorten the coldest, most humid hours (typically 02:00-08:00).
   - Expected effect at RH ≥ 90 %, per kWh made at +4 °C instead of +1 °C: defrosts 2.6 vs 11.8 per 100 kWh, reversed heat 1.1 % vs 5.8 %, COP 3.69 vs 3.00 [1].
   - Rule of thumb for a planner: penalise each kWh by about 0.6 % of defrost heat per K below +5 °C at RH ≥ 90 %, and about half that at 80-90 %.
3. **On humid nights, prefer an off-gap at night and a long minimum-output block by day over the reverse (M).**
   - An off-gap of 0.5-3 h at +2…+5 °C appears to take some frost off: defrosts after a gap are about 14 % lighter, and the hazard is about 0.7× in one winter.
   - A gap below 0 °C does nothing.
   - Do not rely on gaps to avoid a defrost. The Gree clock survives stops [G7], and restart dips can trigger the defrost the clock is "owed".
4. **Do not use many short pulses (< 10-15 min) at 0…+4 °C (M).**
   - On Gree firmware, a defrost tends to fire 10-15 min into a restart after the clock is full [1]. Short pulses mean a larger share of each pulse is lost to a defrost plus a restart transient.
   - Some brands count short runs towards a forced defrost [7].
   - Where cycling is unavoidable, aim for runs of at least 30-60 min of compressor time. The house allows this easily via the slab.
5. **Run a cheap test on this Versati (M).** Over 2-3 humid days at +1…+4 °C, alternate:
   - (A) continuous minimum-output days, and
   - (B) days of 2-3 blocks with 1-3 h night gaps.

   Log:
   - defrost events (from the defrost status or mode register if exposed; otherwise flow below return while the compressor runs);
   - minutes from restart to defrost;
   - reversed heat per event (flow-rate × ΔT);
   - kWh of electricity per kWh of heat.

   Decision rule: if (B) shows defrosts mostly 10-15 min after restarts and reversed heat per event less than 70 % of (A), the Versati is defrosting partly melted coils and gaps are wasted. Prefer (A) or daytime blocks.
6. **Fan and quiet mode (H, from G7 and [15]).** Never use quiet or low-fan modes at 0…+5 °C. A fast fan is what keeps the coil warm. There is no evidence a fan-off stop helps as much as a fan-on run.
7. **Keep the size of the issue in mind.**
   - At 0…+4 °C and RH ≥ 90 %, defrost reverses about 1-6 % of heat [1]. For this house that is about 10-30 kWh of heat a month in humid shoulder months.
   - Moving production 2-3 K warmer is worth about 3-5 % of electricity in those weeks. Run structure is worth about 0 ± 3 %.

## Contradictions and open questions

- **Cycling vs steady in pooled data vs per system.**
  - Pooled and stratified: no difference (1.05×).
  - Per system: from 0.22× to 2.25×. Brand logic dominates.
  - A crude analysis without temperature stratification shows "cycling = 25-35 % fewer defrosts", which is a temperature confound.
  - A forum claim that continuous running "may produce more defrosts per day" [16] is true per day but not per kWh.
- **Hazard after gaps is inconsistent.** It was 0.70-0.72 for 10-180 min gaps (2025-26, 27 systems) but about 1.0-1.5 in the 2024-25 3-system replication, and 1.04-1.95 for gaps over 3 h. Possible reasons:
  - long gaps coincide with weather changes or hot-water priority;
  - restart-triggered defrosts;
  - sampling noise (10-50 events per cell).
- **Melting rate.** A 10× uncertainty (0.1-1.0 kg/h/K) because conductance with the fan off is unmeasured. No source measures melting on an outdoor coil with the fan stopped. ORNL [6] and BFE/42watt [8] cover the fan-on case or "above +5 °C" only.
- **Does melt water help or hurt?** Retained water refreezes on restart [4] and may make the next frosting faster. This could explain why longer gaps do not help more. Not quantified.
- **Gree evidence is from a different product.** The Gree Flexx split in Ottawa has a 300 L buffer. The Versati III monoblock's coil gate, suction-pressure use and "smart defrost" adaptivity are undocumented [5]. The early-run defrost pattern may differ.
- **Open questions**
  1. Does the Versati III also fire defrosts 10-15 min after restarts once its clock is full? Test as in implication 5.
  2. Does the Versati III expose a defrost status or flag over Modbus? Detection from flow and return would still work.
  3. Real off-cycle melting rate on a monobloc coil with the fan stopped. It could be measured by weighing drip water, or by comparing restart COP after gaps at +3 °C with gaps at −3 °C.
  4. Does a short fan-only run after the compressor stops (if any firmware option exists) speed up melting at +2…+5 °C, as in BFE "natural defrost"?
  5. A replication with more systems in 2024-25 data. Four of 8 requested systems were sparse that winter.

## Sources

1. HeatpumpMonitor.org: 29 air-to-water systems, 1-min electricity, heat and outdoor temperature, 1 Nov 2025 - 31 Mar 2026 (system ids 1497, 1163, 2, 888, 450, 627, 883, 999, 1001, 745, 7, 15, 276, 70, 116, 912, 382, 533, 167, 685, 723, 441, 229, 920, 895, 881, 444, 118, 251) - OpenEnergyMonitor / system owners - 2026 - https://heatpumpmonitor.org/ (API: https://heatpumpmonitor.org/timeseries/data) - field data (own analysis) - Stratified cycling vs steady defrost and COP ratios; defrost hazard after off-gaps; defrost size after gaps; defrosts and reversed heat per kWh by temperature and RH; Gree restart-timing pattern.
2. HeatpumpMonitor.org: Gree Flexx 251 (Ottawa), Mitsubishi Ecodan 2, Samsung Gen 6 116, Samsung Gen 7 382, 1-min data, 1 Nov 2024 - 31 Mar 2025 - OpenEnergyMonitor / owners - 2025 - https://heatpumpmonitor.org/timeseries/available?id=251 - field data (own analysis) - Replication. Hazard ratios not replicated (0.94-1.55); lighter defrosts after gaps replicated (0.75-0.89); Gree 93 % of 0…+5 °C defrosts within 20 min of restart.
3. Historical Weather API (ERA5 reanalysis), hourly temperature and RH per site - Open-Meteo - 2026 - https://archive-api.open-meteo.com/v1/archive - data - Humidity and temperature stratification for [1][2].
4. Experimental and modeling studies on developing a condensing-frosting performance map for a variable speed ASHP unit for frosting suppression (PhD thesis) - Liu Shengnan, Hong Kong PolyU - 2023 - https://theses.lib.polyu.edu.hk/bitstream/200/12447/3/6895.pdf - lab - Frost "ageing" (melts when surface > 0 °C); 1.95 kg frost melted in a 402-s defrost; first defrost reached at 2430 s in a fixed-speed case; retained droplets on hydrophilic coils after defrost.
5. VERSATI III Air-to-Water Heat Pump service manual (Monoblock 4-16 kW, R32) - Gree (hosted by Gree Bulgaria) - about 2020 - https://gree-bulgaria.com/manuals/service/Versati_III_Monoblock_04_06_08_10_12_14_16_service.pdf - manufacturer - Normal shutdown: compressor ramps to minimum, expansion valve fully open, fan stops after the compressor; fan follows low-side pressure; fan stops in defrost; "defrost more when it frosts heavily, less when lightly".
6. A Critical Literature Review of Defrost Technologies for Heat Pumps and Refrigeration Systems (ORNL/TM-2018/1007) - Nawaz, Elatar, Fricke / Oak Ridge National Laboratory - 2018 - https://info.ornl.gov/sites/publications/Files/Pub117976.pdf - paper (review) - Compressor-shutdown defrost defined with outdoor fan ON using ambient air; rated low defrost effect and low complexity in its method table.
7. ARTG45/60LDTA defrost operation control - Fujitsu General (AU) - about 2020 - https://assist.generalairstage.com.au/support/solutions/articles/6000134775-artg45-60ldta-defrost-operation-control - manufacturer (other brand) - Integrating timer with coil gates (22/35/62 min; −9/−10/−5 °C); 240-min long-run defrost at −3 °C; 40 short runs (< 10 min) force a defrost; count clears only after a defrost.
8. Wärmepumpe abtauen (magazine article) - 42watt - about 2024 - https://42watt.de/magazin/warmepumpe-abtauen - blog - Frost often melts from ambient heat alone above about +5 °C; icing worst at −5…+5 °C and high RH; 5-15 min cycles; about 30-min lockouts; BFE example with 25-min maximum defrost and 3-min drip time; about 80 % reverse-cycle; heavy icing −25 % COP.
9. Samsung ASHPs - anatomy of a defrost - OpenEnergyMonitor forum (Sarah Hanson et al.) - 2024 - https://community.openenergymonitor.org/t/samsung-ashps-anatomy-of-a-defrost/27767 - forum (logged data) - Trigger on evaporator temperature below a line for 3 min (inferred); defrost < 5 min; 570 Wh taken from the house; post-defrost output peak above 10.6 kW.
10. LWP wegen Abtauen am Leistungslimit (thread, page 4) - energiesparhaus.at forum - 2024-25 - https://www.energiesparhaus.at/forum-lwp-wegen-abtauen-am-leistungslimit/81571_4 - forum - M-TEC: start when air-minus-suction ΔT > 10 K, about every 3 h in humid weather; Nibe S2125 defrosts without ice (worst-case design, no humidity input).
11. Viessmann defrost - OpenEnergyMonitor forum - 2024 - https://community.openenergymonitor.org/t/viessmann-defrost/27441 - forum (logged data) - Internal buffer pre-heated (35 → 54 °C, COP about 1.3) before defrost; at 0.6 °C, 0.6 kWh_el per defrost, 14 min to recover, no heat drawn from the house.
12. Transient response and cycling losses of air-to-water heat pump systems - Tassou & Votsis / Heat Recovery Systems and CHP 12(2):123-129 - 1992 - https://www.osti.gov/etdeweb/biblio/7041177 - lab (abstract) - Off-cycle refrigerant migration up to 11 % COP loss, about 6 % with migration control (evidence that migration carries heat and refrigerant into the cold coil).
13. The laboratory evaluation of the heating mode part-load operation of an air-to-air heat pump - W. A. Miller (ORNL) / ASHRAE Transactions 91(2B) - 1985 - https://www.osti.gov/biblio/5505181 - lab (abstract) - Cycling losses dominated by off-cycle refrigerant migration; the abstract says nothing on frost during off-cycles (a gap in the classic literature).
14. Heat pump defrost - Energy Stats UK - about 2024 - https://energy-stats.uk/heat-pump-defrost/ - blog (owner data) - Defrost every 90-120 min at −0.9…+1.9 °C; about 40 min in noise-reduction mode; frost seen at +3 °C; UK winter RH 80-90 %.
15. Gree Versati III air to water heat pump (thread, page 7) - Home Assistant Community (JKF1, pranelio) - 2026 - https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916?page=7 - forum (owner observation) - Versati III quiet mode: defrost every 52-56 min at +2…+5 °C, much less often without quiet mode; fan-speed register reads 0.
16. The cost of defrost (thread) - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/the-cost-of-defrost/28429 - forum - Samsung HTQ defrosts rare and < 5 min; claim that continuous running gives more defrosts per day; no cost figures.
17. Own psychrometric and heat-balance calculation (Magnus formulas over water and ice; Lewis analogy; coil conductance with fan off assumed 10-90 W/K) - this note - 2026 - n/a - own calculation - No net sublimation at +2…+4 °C and RH ≥ 85 %; melt about 0.1-1.0 kg/h/K; condensation adds 15-60 % to melting heat.
- [G7] Gap G7 note (docs/research/notes/gap-r1-G7.md) - internal - Gree clock-reset rule (Neo manual), Versati I/II entry and exit, Kropas Vilnius onset, BFE natural defrost, 0.37 kg/kW frost estimate.
