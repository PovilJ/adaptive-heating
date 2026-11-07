# Verify r1 / C6: defrost cost and whether low compressor load reduces frost

Method note: the shared web-search budget for this run was already used up when this check started (the first WebSearch call was refused). So this check relies on (a) primary sources fetched directly by URL, and (b) a fresh re-analysis of the open heatpumpmonitor.org data. The re-analysis covers 415 annual system records, daily data for 8 cold or humid-climate systems (including the only Lithuanian one), and 10 years of Vilnius weather. Several paywalled papers (MDPI full text of Kropas et al., Vocale et al. on ScienceDirect) returned HTTP 403. The non-English community queries the brief asked for could not be run.

## Claim

C6: "Defrost costs about 3-8 % of seasonal heating electricity in Lithuania (field reverse heat 4.4-6.7 % of delivered heat below +3 °C). Low compressor load can prevent frost at 0 °C/80 % RH, and an MPC halved defrosts (1.3 against 2.7 per day)."

## Verdict

**partly_supported**

- **The field reverse-heat numbers reproduce.** The Lithuanian season weighting also reproduces: about 4.2-4.6 % of seasonal heat is reversed.
- **The "3-8 % of electricity" range is probably too low at the bottom end.** Two things drive this:
  - Reverse heat costs electricity twice: once to re-supply it, and once for the compressor running during defrost.
  - Individual humid-climate systems reverse up to about 12 % of heat at −4…+2 °C.
- **The 0 °C / 80 % RH "no frost at low load" result is overstated.** The abstract shows a critical RH of about 81 % near +1 °C. It does not say that low load prevented frost. Typical Lithuanian 0…+3 °C days average 87 % RH, which is above that threshold.
- **The MPC numbers are quoted correctly but cannot carry weight.** They come from 4 MPC days against 7 baseline days, on an air-to-air unit, and the authors call the sample too small.
- **New observational support for the load mechanism.** At matched daily temperature, days with higher compressor power show more reverse heat in 8 of 8 systems. This is confounded, so it is not proof.

## Corrected claim with numbers and conditions

1. **Reverse heat by temperature (field, heat-meter "negative heat").** Aggregate over 113 mostly UK systems, heat-weighted [4]:
   - about 1 % at +6…+8 °C daily mean;
   - 4.4 % at +2…+3 °C;
   - 5.2-5.9 % at −2…+2 °C;
   - 6.3-6.7 % at −10…−2 °C.

   Individual humid-climate systems at −4…+2 °C daily mean, from my re-analysis [5]:
   - Silkeborg DK (NIBE S2125): 12.4-12.5 %;
   - Huntly and Grantown, Scotland (Panasonic Aquarea): 8-10 %;
   - Vilnius LT (NIBE AMS 20-6): 7.9-8.9 %, but with an artefact floor of about 4.5-8 % even on warm days;
   - Faaborg DK, Altlandsberg DE, Frederikssund DK, Sheffield UK: 4-7 %.

   **The spread between units (about ×3) is larger than the spread between temperature bins.**
2. **Season share for this climate.** I weighted the aggregate bin shares by Vilnius daily mean temperatures for 2015-2025 (heat ∝ 15-16 °C minus outdoor temperature) [7]. The result is **4.2-4.6 % of seasonal space heat reversed**. The answer barely depends on what is assumed below −10 °C. About 54 % of seasonal heat falls on days between −4 and +4 °C daily mean, and those days average 82-87 % RH [7].

   For context, across 415 systems with a full year of data [4], annual reverse heat is:
   - median 1.5 %;
   - 90th percentile 3.4 %;
   - about 3 % (median) for sites with a cold annual mean.

   A whole-season figure of 2-9 % of heat covers the realistic range of units.
3. **Electricity attributable to defrost.** This is inference, not measured.
   - Reverse heat must be re-supplied at the running COP. That alone costs about the same fraction (f) of electricity.
   - The compressor also runs during defrost. If about 28 % of defrost energy comes from the compressor (the ORNL review figure cited in note 09; not independently re-checked here), that adds about 0.4 × COP × f.
   - At COP 3-3.5 the total is about **2-2.4 × f**. That is higher than note 09's 1.5-2×, and it still excludes the capacity and COP lost while frost is building up.
   - With f ≈ 4.5 % (central), defrost-attributable electricity comes out at about **7-11 % of space-heating electricity**. Across good-to-poor units the plausible range is about 4-20 %.
   - **Corrected statement:** defrost probably costs **about 5-12 % of seasonal space-heating electricity in Lithuania, central about 8 %**. It is not 3-8 %. Confidence: low-medium; the multiplier is not measured.
4. **The frosting map at low load.** Wei et al. 2020 [2] is an abstract only, on a vapour-injection variable-speed unit in a severe-cold region (a unit sized for very cold design days, so it runs at deep part-load at 0 °C).
   - Once heating load was accounted for, the unit was frost-free at 0 °C / 80 % RH.
   - The critical RH was 80.6 % at +1 °C, falling to 62.75 % at −26.5 °C.
   - The fastest frosting was near −10 °C.

   So "low load can prevent frost" holds only **below about 80 % RH near 0 °C, on that unit**. It does not cover the typical humid Lithuanian day at 85-90 % RH.
5. **MPC defrost result** [1]. Air-to-air heat pump (4.5 kW electric) with 19.2 kW resistance backup, in Indiana, January-March 2023.
   - **1.3 defrosts/day over 4 MPC days, against 2.7/day over 7 comparable baseline days.** Days were below 0 °C at 70-80 % RH.
   - The authors say the sample is too small for robust conclusions. The cause (lower demand in cold, humid hours) is only hypothesised.
   - Read it as "consistent with fewer defrosts under lower load", not as "halved".
6. **New field signal, from my analysis [5].** Within each system I compared days in the same 1 K outdoor bin (−3…+4 °C daily mean), splitting them by median running electrical power.
   - Above-median power days reversed **+0.7 to +3.7 percentage points more heat**.
   - The sign was positive in **8 of 8 systems and 43 of 51 bins**.
   - Confounders: post-defrost recovery itself raises mean running power (reverse causation), and colder or more humid nights within the same daily mean. Direction supports the load mechanism; the size is not causal.

## Evidence for

- The aggregate field shares reproduce exactly, and the Lithuanian-weighted season share is about 4.4 % of heat [4][7].
- In the Vilnius system, reverse heat is highest at −4…+2 °C (7.9-8.9 %) [5]. Its COP drops from 3.98 at +2…+4 °C to 1.44 at −16…−10 °C, but that drop is mostly not defrost.
- Lithuanian experiment: frost from below +3.5 °C at 88 % RH; defrost about 5 min on average [3]. This matches the observed onset of reverse heat at +4…+6 °C daily mean.
- MPC defrost numbers confirmed verbatim, with the conditions above [1].
- Temperature-matched within-system data: more compressor power goes with more reverse heat in 8/8 systems [5].
- Fraunhofer ISE's field method counts heat taken back from the heating circuit during reverse-cycle defrost as an input to the performance factor [8]. That confirms reverse heat is a real, metered SPF loss and not an artefact.

## Evidence against / corrections

- **The low end of 3-8 % is too optimistic.** A reverse-heat share of about 4.5 % already implies at least about 4.5 % of electricity just to re-supply it. Adding compressor energy during defrost roughly doubles that. Unit-to-unit spread is large: Silkeborg NIBE 10-12.5 % against Frederikssund Vaillant 4-5 % in similar Danish weather [5].
- **The Wei result is overstated.** The abstract's "frost-free at 0 °C/80 %" is a statement about the critical-RH line, which sits at about 81 % near +1 °C. It is not a demonstrated effect of turning load down [2]. Vilnius days at 0…+3 °C average 87 % RH [7], above that line.
- **The MPC sample is 4 against 7 days, on an air-to-air system with resistance backup** [1]. The authors explicitly disclaim robustness. Transferability to a 9 kW air-to-water unit is unknown.
- **Metering artefacts.** In the Vilnius system's internal metering, "reverse heat" is 4.4-8 % even above +6 °C [5]. So part of the cold-weather number is not defrost. Some integrations exclude defrost entirely; one Stavanger system shows 0 % [6]. Daily means also hide the colder, humid nights.
- **The cross-system frost peak sits at −4…+2 °C, not "below +3 °C" uniformly.** Two Danish systems show lower shares below −4 °C (2.5-3.9 %) than at 0…+2 °C (5.1-7.3 %), consistent with drier cold air [5]. Scottish systems do not show this drop.

## Applicability to this house

- About half of this house's seasonal heat falls on −4…+4 °C days at 82-87 % RH [7]. That is exactly the band where reverse heat is 4-12 % per unit. So humid 0…+4 °C hours deserve special treatment in the controller.
- The levers that plausibly help are the same ones that help COP anyway:
  - lowest sustained compressor power;
  - placing bulk heat in warmer, drier afternoon hours (the 6.6 kWh/K slab allows this);
  - never using quiet/low-fan mode in this band;
  - pausing control logic during defrost.
- The expected gain from load placement alone is probably a few percent of electricity, not tens. That is an inference; no controlled test exists.
- **Measure it on this unit.** Log the Versati defrost status bit and negative-ΔT heat. Then compare defrost count and reverse kWh per day at matched outdoor temperature and humidity, between low-power and high-power days. That would turn the 2-12 % uncertainty into a house-specific number within one winter.
- At this house's 3.7 kW minimum output, defrost recovery is not capacity-limited; only efficiency matters.

## Sources

1. Pergantis et al., "Field demonstration of predictive heating control for an all-electric house in a cold climate", arXiv 2402.07032 (2024). Full text read: §5.5 defrost cycles and §6.4 limitations. https://ar5iv.labs.arxiv.org/html/2402.07032. Evidence type: field measurement (single house, small sample).
2. Wei, Ni, Li, Wang, Yao, Xu, Yang, "A new frosting map of variable-frequency air source heat pump in severe cold region considering the variation of heating load", Renewable Energy 161 (2020) 184-199. Abstract only. https://ideas.repec.org/a/eee/renene/v161y2020icp184-199.html. Evidence type: experimental (abstract).
3. Kropas, Streckienė, Bielskus, "Experimental Investigation of Frost Formation Influence on an Air Source Heat Pump Evaporator", Energies 14(18):5737 (2021). Abstract; MDPI full text returned 403. https://ideas.repec.org/a/gam/jeners/v14y2021i18p5737-d633785.html. Evidence type: experimental, Lithuania (abstract).
4. heatpumpmonitor.org annual stats for 860 systems (415 with a full year of heat data and no cooling), own analysis, plus the binned aggregate in note 09 (re-checked against the same dataset). https://heatpumpmonitor.org/system/stats/last365. Evidence type: field measurement (open data).
5. heatpumpmonitor.org daily stats for systems 887 (Vilnius), 252 (Silkeborg), 215 (Faaborg), 644 (Altlandsberg), 159 (Grantown-on-Spey), 405 (Huntly), 462 (Frederikssund) and 144 (Sheffield), own analysis. https://heatpumpmonitor.org/system/stats/daily?id=887 (same pattern for the other ids). Evidence type: field measurement.
6. heatpumpmonitor.org system metadata (location, model, metering type). https://heatpumpmonitor.org (system list; github.com/openenergymonitor/heatpumpmonitor.org). Evidence type: metadata.
7. Open-Meteo historical archive, Vilnius, daily mean temperature and RH, July 2015 to June 2025. https://archive-api.open-meteo.com/v1/archive?latitude=<site>&longitude=<site>&start_date=2015-07-01&end_date=2025-06-30&daily=temperature_2m_mean,relative_humidity_2m_mean. Evidence type: reanalysis weather data.
8. Fraunhofer ISE, "WPsmart im Bestand" final report (BMWi 03ET1272A): §5.1 on how reverse-cycle defrost heat is metered and charged as an SPF input. https://www.ise.fraunhofer.de/content/dam/ise/de/downloads/pdf/Forschungsprojekte/BMWi-03ET1272A-WPsmart_im_Bestand-Schlussbericht.pdf. Evidence type: field-trial report (method; no headline defrost share found).
9. Dongellini, "Dynamic modeling and seasonal performance evaluation of air-to-water heat pump systems", PhD thesis, University of Bologna (2017): §4.4.5 defrost model (1-10 min cycles, 1-2 per hour in critical conditions, trigger 0-6 °C and RH above 50 %). Evidence type: simulation/thesis.
10. Love et al., "Investigating variations in performance of heat pumps installed via the RHPP scheme", UCL/BEIS (2017). Read for defrost content; defrost appears only as an operating-mode boundary, with no share given. Evidence type: field-trial report (negative finding).
