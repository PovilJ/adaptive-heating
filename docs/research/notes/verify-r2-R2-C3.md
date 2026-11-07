# Verify R2-C3: the field speed penalty is 0.55-0.75 %-Carnot points per kW

## Claim

> In the field, each extra 1 kW of average heat output costs only 0.55-0.75 points of %-Carnot (about 1.5 % relative) at the same flow temperature.

Source: 07-community-diy-controllers.md ("Starting too hard is common"). There it is attributed to "HPM daily data ... on cold days". This figure is several times smaller than the 15-25 % "flat-out against mid" planning figure, so it decides how strong the COP(speed) term in the simulator should be.

**Method note.** The session's shared web-search budget was used up before this check began, so I could run no new searches, including the required non-English ones. Instead I:
- fetched known primary pages directly: Energy Stats UK, the KTH thesis, the Madani abstract, the OST abstract and the OEM forum;
- extracted PDF text with a small zlib parser;
- ran two **new, independent analyses of the raw heatpumpmonitor.org (HPM) data** [1][2]:
  - a re-run of the daily within-system regression the claim came from;
  - a different, sharper test: 1-minute steady-state data at matched flow and outdoor temperature.

I did not read the repository code, lab/ or Home Assistant.

## Verdict: partly_supported

- **Supported in spirit.** In real installations, at a given flow and outdoor temperature, the pure compressor-speed penalty is small: low single-digit percent between about 30 % and 100-120 % of rated output. It is much smaller than lab and datasheet curves suggest. Below about 20-30 % of rated output it reverses sharply.
- **Not supported as a stable linear coefficient.** The "0.55-0.75 points per kW, about 1.5 %" number reproduces only on cold days (< 5 °C) and with large scatter between systems.
  - Across all weather, the same daily regression gives a **median of +0.73 points per kW**: more output means *higher* %-Carnot. That is the same magnitude with the opposite sign.
  - In minute-level steady-state data the linear slope is also positive. It is dominated by the low-load collapse.
  - The number therefore depends on method and weather, and should not be quoted as "the" field speed penalty.

## Corrected claim (numbers and conditions)

1. **Daily within-system data** [1]: 66 single-zone UFH air-source systems without hydraulic separation, 27,000 full days. Outcome: space-heating %-Carnot, demeaned within system × 2 K outdoor bin.
   - **Cold days (< 5 °C, 61 systems, 5,900 days):**
     - median −0.84 points per kW (−1.8 % relative), IQR −2.5 to +0.2;
     - −1.08 points per kW (−2.3 %) after controlling for flow temperature and starts;
     - negative in 67-74 % of systems.
   - **Mild days (5-12 °C):** median +0.94 points per kW raw, and 0.0 after controls.
   - **All days:** median +0.73 points per kW raw (+1.5 %); −0.24 points per kW (−0.5 %) after controls. IQR about ±1.5-2 points per kW, so most of the variation is between systems.
2. **Steady-state, 1-minute data** [2]: 26 systems, November 2025 to March 2026. Conditions:
   - runs at least 20 min old, 15 min clear of defrost, flow 20-45 °C;
   - stable 10-minute blocks, compared within 1 K flow × 1 K outdoor cells.

   Relative COP deviation by load fraction (output ÷ nameplate):

   | Load fraction | < 0.2 | 0.2-0.3 | 0.3-0.6 | 0.6-0.9 | 0.9-1.2 |
   |---|---|---|---|---|---|
   | All weather | −5 % (−43 % below 0.1) | −0.5 % | +0.3 to +0.8 % | −0.4 to −1.9 % | −0.3 to −1.6 % |
   | −10 to +4 °C | −18 % | −4 % | −0.4 to +1.1 % | −0.3 to −0.8 % | 0 to −2 % |

   - **Mid-range (about 0.4-0.5) to flat-out (about 1.0) costs about 1-3 % relative at the same flow and outdoor temperature.**
   - Equivalent to about 0.2-0.6 %/kW for a 5-9 kW unit. That is the same order as the claim, or smaller.
   - Per-system linear slopes are positive (median +3.7 %/kW) because the low-load collapse dominates a straight-line fit.
3. **Controlled lab and matched-field tests show a much larger speed penalty**, about 4-6 % relative per kW:
   - KTH brine/water rig, fixed source temperature and condenser *inlet* temperature: 30→90 Hz, capacity 5.6→12.9 kW, heating COP falls (about −32 % per the earlier note; the chart values could not be re-read) [4].
   - Purdue/KTH abstract: COP falls up to 30 % as speed rises, with pressure ratio going from 2.7 to 5.8 [5].
   - Vaillant 5 kW DHW reheats with the same cylinder start state at about 5 °C outdoor [3]:
     - 50 rps (3.3 kW): COP 3.55;
     - 80 rps (4.8 kW): COP 3.26, which is −8 % for +1.5 kW;
     - 120 rps (6.9 kW): COP 2.85, about −20-25 %.

   In these tests the water temperature was *not* held at the same flow temperature. Part of the penalty is the higher flow and condensing temperature that high output creates.
4. **For the simulator, the two figures measure different things, and both are roughly right:**
   - **Pure speed term at fixed flow and outdoor temperature:** use about 1 %/kW, or 0-3 % mid→max; sensitivity range 0-4 %/kW. Add a steep penalty below about 25-30 % of rated output.
   - **Total catch-up penalty:** the 15-25 % mainly comes from the higher flow temperature that high output forces. Each extra kW into the slab raises flow by roughly output ÷ UA of the emitter plus the extra flow-return ΔT. Model that explicitly through the flow-temperature term (about 2-3 %/K), not through the speed term.

## Evidence for

- **The cold-day daily regression reproduces the sign and order of the claim** [1]:
  - −0.84 points per kW raw (−1.8 %), negative in 74 % of systems;
  - −1.08 points per kW (−2.3 %) after controlling for flow temperature and starts.

  The claim's 0.55-0.75 points is within that spread, slightly smaller.
- **Minute-level steady state also shows a flat plateau** [2]. Between 0.3 and 1.2 of rated output, at the same 1 K flow and outdoor cell, relative COP stays within about ±2 % (worst −3.2 % at 0.7-0.8 in mild weather). No large high-speed penalty is visible.
- **Swiss federal monitoring (OST/Bertsch) agrees** [6]. Steady-state field points from air/water and brine/water units show the Carnot quality grade stable over wide operating ranges, collapsing only below unit-specific low-power limits. Standard rating points miss this.
- **Fleet-level annual data also show no load effect** [8]. An analysis of the HPM fleet found the annual SPF/H_fixed ratio flat against a load-severity index (slope +0.05 ± 0.10; Arotherm-only −0.01 ± 0.14). The Arotherm datasheet predicts +0.77. This is low weight because its provenance is unclear.

## Evidence against

- **Sign instability** [1]. In the same daily dataset the coefficient is positive on mild days (+0.94 points per kW) and across all days (+0.73).
  - The claim's "0.55-0.75" is suspiciously close to the all-weather magnitude with the sign reversed.
  - At best it is a cold-day-only figure.
  - Between-system IQRs (about ±2 points per kW) are 3-4 times the median. A single coefficient is not robust.
- **Confounding makes field "same flow temperature" slopes biased toward zero or positive:**
  - Frosting lowers both output and COP, which creates a positive correlation.
  - At a fixed flow temperature, high output usually means a colder return. A colder return helps subcooling and COP.
  - Heat-meter error is relatively larger at low flow-return ΔT.
  - Low-output days have more start-up transients.
  - Daily averaging and measurement noise attenuate any slope.
  - None of these can be removed with HPM data, which has no compressor-speed channel.
- **Lab and matched-field tests consistently show a 20-30 % COP drop from low to high speed** [3][4][5]:
  - KTH: Carnot COP is highest at 30 Hz and lowest at 90 Hz. Carnot efficiency (on refrigerant temperatures) peaks at 60 Hz, at 61 % [4].
  - Energy Stats: −8 % for +1.5 kW at a matched cylinder state [3].
  - The HPM author expects COP of about 4.6 at 40 rps against about 3.3 at 110-120 rps at 35/7 [7]. This is a datasheet-based expectation, not a measurement.

  Even if part of each drop is the higher sink temperature, the refrigerant-side lift rises with heat flux at any given water temperature (KTH condenser heat flux went from 2.3 to 5.5 kW/m²). A true fixed-flow speed penalty of zero is physically implausible. The field estimate is probably a lower bound.

## Applicability to this house

- **The Versati's 3.7-3.8 kW minimum is about 40 % of nominal.** That is on the field plateau [2][6], not in the low-end collapse.
  - Going from 3.8 kW to full output (about 8-9 kW at mild-to-cold conditions) at the *same* flow temperature should cost roughly **3-10 %** of COP: about 1-2 %/kW × 5 kW, using a blend of field and lab weighting.
  - That is not 0 %, and not the 25 % of lab speed curves.
- **The main cost of the observed 3 kW-electric catch-ups is the extra water temperature they need** (setpoints 36-39 °C instead of about 29-31 °C). At 2-3 %/K that is 15-25 %, and it dominates the speed term.
- **A power cap is therefore worth most for what it enables:** it keeps the flow setpoint low and stops the firmware's large-error high-frequency starts. The direct compressor-speed saving at fixed water temperature is secondary.
- **Evidence gaps:**
  - No Gree, and no Baltic climate, in the minute-level sample.
  - Frost-zone humidity (−5 to +5 °C) makes the frosting confounder stronger here.
- **Verify locally:** log Modbus set/actual frequency with electrical power, heat output, flow and outdoor temperature. Compare COP at matched flow and outdoor temperature between minimum-frequency runs and capped versus uncapped catch-ups.

## Sources

1. heatpumpmonitor.org public daily stats, own new re-analysis: 66 UFH single-zone air-source systems, 27,000 days, within-system × 2 K bins, with and without flow and starts controls. https://heatpumpmonitor.org/system/stats/daily?id=N and https://heatpumpmonitor.org/system/list/public.json. Field data (own analysis).
2. heatpumpmonitor.org 1-minute timeseries, own new steady-state analysis: 26 systems, November 2025 to March 2026, matched 1 K flow × 1 K outdoor cells. https://heatpumpmonitor.org/timeseries/data?id=N&feeds=heatpump_elec,heatpump_heat,heatpump_flowT,heatpump_returnT,heatpump_outsideT. Field data (own analysis).
3. M. Wall, "Vaillant Arotherm Sweet Spot Hot Water Mode", Energy Stats UK. https://energy-stats.uk/vaillant-arotherm-sweet-spot-hot-water-mode/. Field measurement, single system, cylinder state matched but flow temperature not.
4. Awan U.K., "Experimental Analysis of Variable Capacity Heat Pump System Equipped with Vapour Injection and Permanent Magnet Motor", KTH MSc thesis, 2012. https://www.diva-portal.org/smash/get/diva2:565195/FULLTEXT01.pdf. Controlled lab test; brine/water; source and condenser-inlet temperatures fixed.
5. Madani, Ahmadi, Claesson et al., "Experimental analysis of a variable capacity heat pump system focusing on the compressor and inverter loss behavior", Purdue Conference 2010 (abstract). https://iifiir.org/en/fridoc/experimental-analysis-of-a-variable-capacity-heat-pump-system-focusing-27509. Lab (abstract only).
6. Repke T. (supervisor S. Bertsch), "Teillastverhalten von invertergeregelten Wärmepumpen – Analyse des Carnot-Gütegrads im Feldbetrieb", OST, 2026 (abstract). https://www.ost.ch/files/daten/abstracts/pdf/990f3d2f-cae1-4a03-a95e-8e279b8902f2.pdf. Field monitoring (Swiss BFE), steady-state points; abstract only.
7. T. Lea et al., "HeatpumpMonitor.org: Findings", OpenEnergyMonitor forum, April 2025. https://community.openenergymonitor.org/t/heatpumpmonitor-org-findings/28164. Forum, datasheet-based expectation (40 rps vs 110-120 rps).
8. Unattributed analysis note on load ratio against annual SPF in the HPM fleet (P test; Arotherm datasheet twins), found in this session's working files; provenance unverified. Low weight; secondary field analysis.
