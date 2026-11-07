# Verify r1 – C5: low runtime fraction and low-load Carnot collapse

## Claim

C5: "On mild days, a compressor runtime fraction below 0.3 coincides with 6-8 % lower COP than days at 0.3-0.9, and inverter Carnot efficiency collapses below a unit-specific low electrical load (OST/Bertsch)."
(From 13-field-evidence-top-systems.md Summary bullet 6, 01 Summary 7, 12 Summary 3.)

Method note: the web-search budget for this session ran out after 2 searches, well short of the 12 planned. Non-English community searches were therefore **not** run. To make up for this, I did an independent re-analysis of the raw heatpumpmonitor.org daily data, which is the primary source behind the first half of the claim. I also read 7 further primary or secondary documents by direct fetch.

## Verdict

**partly_supported.**

- **The direction is right.** Very low daily runtime fraction does go with lower daily COP, and running %-Carnot does collapse at very low running output.
- **The threshold and the mechanism are wrong in ways that matter for control:**
  1. The penalty sits below a runtime fraction of about **0.2**, not 0.3. Days at 0.2-0.3 are within about 1-3 % of days at 0.3-0.9.
  2. The penalty is **not** caused by low electrical load while running. Low-duty days actually run at a *higher* output fraction.
  3. The penalty is **not** caused by short runs or many starts. Days with runs of 90 minutes or more show the same penalty.
  4. About half the penalty is off-time electricity: standby, controls and pumps, typically 22 W. The other half is a lower running COP that starts and run length do not explain.
- **The OST half rests on a bachelor-thesis poster abstract** with no numbers. "Low electrical load" there means low compressor power during steady running, not low duty.

## Corrected claim (with numbers and conditions)

The figures below are from my re-analysis [1]. Data: heatpumpmonitor.org daily data for 296 air-source systems with underfloor heating, 139,395 days. Filters: heat and electricity data quality of at least 95 %, at least 80,000 s of data per day, no immersion or cooling use, daily COP between 1 and 9. Each day is compared with the median of the same system in the same 2 K outdoor band.

- **Mild days (8-14 °C outdoor), DHW at most 5 % of heat.** Daily COP deviation by runtime fraction (rtf):

  | rtf | < 0.1 | 0.1-0.2 | 0.2-0.3 | 0.3-0.4 | 0.4-0.6 | 0.6-0.9 | > 0.9 |
  |---|---|---|---|---|---|---|---|
  | Daily COP vs band median | **-22 %** | **-5.9 %** | -0.6 % | +0.3 % | +1.2 % | +2.1 % | +1.8 % |
  | Number of days | 2,617 | 3,258 | 4,462 | 4,671 | 8,259 | 6,801 | 2,706 |

  - Against days at 0.3-0.9, the 0.1-0.2 bin is about 6-8 % lower. That matches the claimed size, but only for this bin.
  - The 0.2-0.3 bin is only about 1-3 % lower.
  - Including DHW days gives the same pattern: -24 %, -5.6 %, -0.1 %, +0.4 % ... +2.2 %.
- **At 2-8 °C** the curve is a little wider: 0.2-0.3 gives -3.6 % and 0.3-0.4 gives -1.4 %. This band has few days, since low rtf is rare there.
- **At 14-18 °C** the band median is itself a low-rtf day, so the comparison against the median flips sign. That shows band-median comparisons are fragile at the shoulder.
- **Mechanism, mild no-DHW days [1]:**
  - *Off-time electricity.* Its share of daily electricity is 1.4 % at rtf 0.6-0.9, 3.1 % at 0.4-0.6, 7.2 % at 0.1-0.2 and 11.9 % below 0.1. Median off-time power is **22 W** (interquartile range 14-35 W). This term alone explains roughly half of the 0.1-0.2 penalty.
  - *Running COP.* It is also lower: -3.7 % at 0.1-0.2 and -17 % below 0.1. Yet running %-Carnot moves only -0.4 points and running flow only +0.5 K at 0.1-0.2. Start count and run length do not account for this.
  - *Run length.* At rtf below 0.2, the COP deviation is -10 % with runs under 20 minutes, -12.7 % at 20-40 minutes, -12.2 % at 40-90 minutes and **-9.2 % with runs of 90 minutes or more**. The penalty is about how little heat is delivered per day, not about cycling.
  - *Output while running.* Low-rtf days run at a **higher** heat output relative to rated: 0.61 at 0.1-0.2 against 0.50 at 0.4-0.6 and 0.48 at 0.6-0.9.
- **Carnot collapse at low running load (OST-type effect).** Within system and outdoor band, all temperatures, DHW at most 5 % [1]:
  - By running heat output as a fraction of rated: below 0.1 gives **-12 points**, 0.1-0.2 gives **-2.6 points**, 0.2-0.3 gives -0.3 points, and 0.3-1.0 stays within ±0.2 points.
  - By mean running electrical power: below 200 W gives -17 to -32 points (few days), 200-300 W gives -5.8 points, and **300 W and above is flat (±0.3 points)**.
  - This supports the qualitative OST statement [2], which is stable over wide ranges with a collapse below a unit-specific limit. The thresholds are about 0.2 of rated heat and about 300 W electrical, as daily averages. Daily averages at such low power also mix in start-up transients.

## Evidence for

- My re-analysis [1] reproduces about -6 % (vs band median) and about -7 to -8 % (vs rtf 0.3-0.9) for rtf 0.1-0.2 on mild no-DHW days. Below 0.1 the penalty is much larger (-22 %).
- OST/Bertsch thesis abstract [2]. Swiss federal-energy-office field data, air/water and brine/water, stationary points extracted from time series. Its conclusion: inverter units often show a pronounced efficiency collapse at low electrical part load, with %-Carnot stable over wide ranges. No numbers are given.
- Lab work on on/off units shows COP degradation growing as the part-load ratio falls:
  - Corberán et al. [3]: standby consumption during the off period was the *only* non-negligible factor, and it grows sharply at low load ratios. Water-to-water unit.
  - Bensafi, Mondot and Rivière [4]: 8 kW on/off air-to-water unit tested at 25-90 % load and -7 to +12 °C outdoor. The drop was attributed mainly to standby losses.
  - Fuentes et al. [5]: 40.5 kW water-to-water unit. Part-load factor PLF = 1 - 0.22 (1 - PLR) with a 50 L store. Degradation was much smaller with 1000 L of inertia. Start-up losses dominated, and the 15 W standby was negligible above PLR 0.2.
- The EU regulation [6] counts off, thermostat-off, standby and crankcase-heater energy on top of active-mode SCOP, and applies a default cycling degradation Cdh of 0.9. The regulator thus treats both mechanisms as real.
- Field case [6b] (Dimchev): an oversized 16 kW unit (minimum 8.5 kW at 36 Hz) serving 8 kW of design load, with a buffer, at 45 °C flow. Measured COP rose much more slowly with outdoor temperature than declared (slope 0.049 vs 0.083 per K), and SCOP was 30 % below declared. The author attributes this to cycling.

## Evidence against / qualifications

- **Threshold.** The 0.2-0.3 bin carries almost no penalty on mild days [1]. "Below 0.3" overstates the zone by lumping in 0.2-0.3.
- **Mechanism is not "low electrical load."** Low-duty days run harder, not softer [1]. The OST collapse [2] is a separate effect: steady running at very low compressor power. Combining the two in one sentence implies a causal link the data do not show.
- **Not a cycling penalty.** The penalty barely depends on run length [1]. Lab start-up losses [5] shrink with inertia, and the slab here is far larger than a 1000 L store. The old on/off lab results [3][4][5] are fixed-speed or water-to-water units with small stores, so they transfer only loosely.
- **Partly a ratio artefact.** About 22 W of off-time power over a day is about 0.4-0.5 kWh [1]. That is a large share of a small day and a small share of a large one. In absolute terms it does not depend on how the heat is scheduled within the day.
- **The OST source is weak.** It is a bachelor-thesis poster abstract with no thresholds, sample size or effect size [2]. "Unit-specific" means the limit cannot be carried across models.
- **Possible metering bias at very low heat.** Heat meters have low-flow and low-ΔT errors, and pumps may run outside the metering boundary. Some of the <0.1 penalty may be measurement. This is unverified; the boundary flags vary per system in [1].
- **Association, not causation.** Low-rtf days within a band differ in other ways too: sunnier days, DHW timing, occupant behaviour.

## Applicability to this house

- **OST-type collapse: not applicable.**
  - The Versati's minimum running output of about 3.7-3.8 kW is about 0.41 of its 9 kW rating. Its running electrical power is likely around 0.8-1 kW.
  - Both are well above the roughly 0.2-of-rated and roughly 300 W region where running %-Carnot collapses in the field data [1].
  - Running at minimum frequency is therefore not penalised by this effect.
- **Runtime-fraction penalty: relevant only at the warm shoulder.**
  - Daily rtf at minimum output is about load / 3.75 kW. At 0.14-0.20 kW/K (taken here as about 0.17) and a 22 °C target, without gains:
    - +10 °C outdoor gives about 0.45-0.55.
    - rtf falls below 0.2 only when the net load drops below about 0.75 kW. That is roughly +17 °C without gains, and probably +12-15 °C with solar and internal gains.
  - So in Lithuania the penalty applies to a minority of shoulder-season days that carry little heat. Its annual cost in kWh is small: about 0.4-0.5 kWh/day of off-time electricity at typical standby.
- **Runtime fraction is an outcome, not a control lever.**
  - For a given daily heat demand and a fixed minimum output, the daily rtf is fixed. Splitting it into one long window or several short runs does not change it.
  - The off-time power is drawn either way. Advice such as "keep rtf at or above 0.3" (note 13, recommendation 4) cannot be acted on and should be removed.
  - The real levers are lowering off-time parasitic power and not raising flow temperature.
  - Parasitic power to check:
    - whether the UFH circulator and the Versati's internal pump run during compressor-off periods;
    - the controller and Modbus gateway;
    - crankcase heating at low ambient;
    - the Komfovent is outside the boundary.
  - On flow temperature: concentrating heat into short windows only costs efficiency if it pushes compressor output above minimum, and therefore flow temperature up. That cost is the 2.5-3 %/K flow-temperature effect, not a duty effect.
- **For daily heating windows,** low duty gives no reason to favour or avoid them. Decide on flow temperature, defrost conditions (humid -5 to +5 °C hours) and PV/tariff instead.
- **Measure:**
  - off-time electrical power from the house meter or a CT on the outdoor unit and pumps;
  - whether pumps run between runs;
  - daily COP against rtf on days above +10 °C.

  If off-time power is well above about 30 W, cutting it beats any scheduling change.

## Sources

1. heatpumpmonitor.org public daily statistics, independently re-analysed for this check (296 air-source UFH systems, 139,395 qualifying days; endpoints `/system/list/public.json` and `/system/stats/daily?id=N`). https://heatpumpmonitor.org/ — measured field data (own analysis, not peer reviewed).
2. Repke T., supervisor Bertsch S. "Teillastverhalten von invertergeregelten Wärmepumpen – Analyse des Carnot-Gütegrads im Feldbetrieb und Vergleich mit Normmesspunkten." OST Bachelor thesis abstract, 2026. https://www.ost.ch/files/daten/abstracts/pdf/990f3d2f-cae1-4a03-a95e-8e279b8902f2.pdf — field data, student thesis abstract, no numbers.
3. Corberán J.M., Donadello D., Martínez-Galván I., Montagud C. "Partialization losses of ON/OFF operation of water-to-water refrigeration/heat-pump units." Int. J. Refrigeration 36(8), 2251-2261, 2013. https://riunet.upv.es/entities/publication/82932ef6-01fa-4adb-9c00-fbf4bb2ee5fc and https://iifiir.org/fr/fridoc/pertes-de-partialisation-lors-du-fonctionnement-quot-tout-ou-rien-quot-des-28039 — lab, peer reviewed (abstract read).
4. Bensafi A., Mondot M., Rivière P. "Seasonal performance of on-off air-to-water heat pumps." ICR 2007. https://iifiir.org/en/fridoc/seasonal-performance-of-on-off-air-to-water-heat-pumps-24935 — lab (abstract read).
5. Fuentes E., Waddicor D., Fannan M.O., Salom J. "Improved methodology for testing the part load performance of water-to-water heat pumps." 12th IEA Heat Pump Conference, 2017. https://etkhpcorderapi.extweb.sp.se/api/file/1584 — lab, conference paper (full text read).
6. Commission Regulation (EU) No 813/2013, ecodesign requirements for space heaters (definitions of P_SB, P_TO, P_CK, P_OFF; Cdh default 0.9). https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32013R0813 — standard/regulation.
6b. Dimchev I. "Comparison between calculated and measured seasonal coefficient of performance of an air-to-water heat pump." Univ. of Ruse 64th Annual Scientific Conference, 2025. https://conf.uni-ruse.bg/bg/docs/cp25/bp/bp-7.pdf — single-system field data, conference paper (full text read).
7. Origin notes, for traceability only (not independent): docs/research/notes/13-field-evidence-top-systems.md and 01-inverter-part-load.md.
