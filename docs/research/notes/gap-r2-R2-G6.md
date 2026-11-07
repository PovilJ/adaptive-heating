# Gap R2-G6: What is the quantitative compressor wear or lifetime cost per start for modern inverter rotary or scroll compressors in residential air-to-water units? Do manufacturers (including Gree) specify start-count design lives or warranty conditions?

Research note, round 2, gap G6. Written 2026-11-06.

**Process caveat:** the shared web-search budget for this workflow ran out before this agent started. All three search attempts were refused. This note is therefore built only from directly fetched pages and documents at known URLs: manufacturer guidelines, warranty terms, field reports, a 549-system field dataset and blogs. That has two consequences:
- There are no Chinese or Japanese compressor reliability standards or test protocols, and no peer-reviewed accelerated-life papers. These are the places a true "starts to failure" curve would live.
- Gree's warranty terms could not be retrieved (DNS and TLS failures on the guessed distributor URLs).

A follow-up with search budget should target those two gaps first. See Open questions.

## Summary

- **No primary, quantitative "life lost per start" figure exists in anything I could read.** No compressor maker gives a start-count design life in its application guidelines, for scroll (Copeland XHV variable-speed, ZR) or for Bitzer's inverter guidance. Copeland, Danfoss and Bitzer give only rate limits: at most 10 starts/h for Copeland scroll, 12/h for Danfoss, and 6–12/h for Bitzer with an inverter. They also require a minimum run long enough for oil return [3][2][4].
- **The "12 % more cycles costs up to 15 % of life" figure cannot be traced.** Göbel et al. (ECOS 2023) attribute it to "Perrin [22]". Reference [22] in that paper is actually Huchtemann et al., a CLIMA 2016 paper on typical test days. No Perrin appears anywhere in the reference list [1]. Treat the number as unverified folklore. Do not use it to set a weight.
- **The only "life in starts" number found is a ~100,000-start rule of thumb.** The German installer blog 42watt gives it as a refrigeration-trade guideline, together with 70,000–80,000 operating hours. It names no primary source [5]. The same blog sets bands of under 2,000 starts/yr "optimal", 2,000–3,000 "acceptable" and over 4,000 "critical". These bands are also unsourced [5].
- **Copeland states that extra starts are within design limits.** It recommends stopping and restarting its variable-speed heat-pump scroll around every defrost reversal, which adds 2 starts per defrost. It says the additional start-stop cycles "do not exceed the compressor design limits" [3]. A maker that tells you to add two starts per defrost does not price individual starts as expensive.
- **Copeland: failures come from system faults, not start counts.** Its service guidance says most in-warranty electrical failures stem from mechanical problems. It names particles in the oil and liquid refrigerant in the oil. Most mechanical problems, in turn, come from system problems [3]. Start-related damage occurs through oil pump-out and short runs, and through flooded starts after refrigerant migrates during long off periods. The count of starts as such is not the mechanism named [2][3].
- **Field start counts are far below any 100k budget.**
  - In my analysis of 549 heatpumpmonitor.org systems with ≥300 days of data, the median is 2,168 starts/yr. The quartiles are 1,419 and 3,055, p90 is 5,212, and 2 % exceed 10,000 [9].
  - Fraunhofer ISE's WP-QS study (77 existing-building heat pumps, 4 years) found 550–15,800 starts/yr, with 90 % below 5,500/yr. This is reported second-hand by 42watt [6].
  - At the median, 20 years is about 43,000 starts.
- **Running hours are also well inside 70–80k.** On the same 549 systems, the median is 3,488 compressor h/yr (IQR 2,761–4,163) [9]. That gives about 70,000 h in 20 years. Running hours, not starts, are the first "budget" to approach a guideline value.
- **Starts per running hour:** median 0.66 and p90 1.69 across the same systems [9]. In 2012–2015, UK RHPP found "a very large proportion" of ASHPs cycling on 10-minute on-to-on patterns, about 6 starts/h [13]. The RHPP report lists faults but does not report a wave of compressor failures attributable to this cycling [13]. That is weak evidence that even heavy cycling does not destroy inverter compressors within a few years.
- **Warranties do not limit start counts.**
  - Vaillant's 10-year compressor warranty (flexoTHERM/flexoCOMPACT/geoTHERM) covers material cost only. It requires proper installation, operation per the manual and maintenance per plan. It excludes "unusual stress" (unübliche Beanspruchung) but sets no start or hour limit [15].
  - Vaillant's 5-year digital guarantee requires annual maintenance and a permanent internet link with remote fault monitoring [16].
  - Viessmann ties 5 years to a ViCare connection and annual maintenance [17].
  - Of the manufacturers surveyed, only Alpha Innotec is reported to cap warranty by operating hours. This is second-hand, and the exact cap was not retrieved [5].
- **Gree:** no start-count design life or warranty start/hour condition found. Gree's documented protections are a 3-min restart lockout, an adjustable "heat run time" of 1–10 min (default 3/5 min), an oil-return routine (Modbus coil 87) and a crankcase heater (coil 84) [19][20]. The Gree warranty text for Lithuania was not retrieved.
- **Rough monetary bound per start, my arithmetic, low confidence.** Assume 100k starts per life, linear wear and a €1,500–5,000 compressor replacement (42watt gives €2,000–5,000 in Germany [5]). That gives about €0.015–0.05 per start. The energy cost of a start is about 0.19 kWh of heat, or about 0.05 kWh of electricity at COP 4 (from verify-C4/gap-G4), which is about €0.01. So **on the most pessimistic linear-wear assumption, wear is worth roughly 1–5× the energy cost of a start. That is about 0.1–0.25 kWh-electric-equivalent per start.**
- **Practical consequence:** a start-penalty weight of about 0.1–0.3 kWh-electric-equivalent per start is defensible. Above that, you are paying real efficiency (higher flow temperature, longer high-speed catch-ups) to protect a budget the house will not exhaust. This house's 700–3,500 starts/yr is near the field median and well under 100k over 20+ years. **Hard limits matter more than the per-start price:** no runs under about 10–20 min, at most about 3 starts/h, and no starts that are likely to be "flooded" in cold weather.

## Detailed findings

### 1. The "12 % → 15 %" citation is broken

- Göbel, Waiz, Vering and Müller (ECOS 2023) argue that controller studies should consider service life as well as SCOP. In their HiL tests, bad PI or hysteresis settings raised starts by up to 300 % [1].
- They write that "Perrin [22]" found a 12 % increase in cycles can reduce compressor life by up to 15 % [1].
- In the extracted reference list, [22] is Huchtemann, Engel, Mehrfeld, Nürenberg and Müller, a CLIMA 2016 paper on a testing method using typical days. "Perrin" does not appear anywhere else in the paper [1].
- The original study therefore cannot be identified from the paper. Its claim implies an elasticity of about 1.25 (life lost % per cycles added %), i.e. super-linear wear. There is no way to check its conditions: compressor type, fixed or variable speed, failure definition.
- **Status: unverified. Do not use it quantitatively.** Earlier notes (06-mpc-academic [11]) carried it forward as "cited in [11]", and that remains its only provenance.

### 2. What compressor makers actually specify

| Maker / document | Start limit | Off-time | Minimum run / other | Start-count life? |
|---|---|---|---|---|
| Copeland XHV variable-speed heat-pump scroll (with ED3 drive) [3] | ≤ 10 starts/h | ≥ 1 min since last stop | Minimum run is set by oil return to the sump, measured with a sight-tube sample compressor. Below 1,800 rpm an oil-circulation routine is required. Reach the envelope fast at start: the ramp diagram shows ramp-up then a hold of ≥ 30 s. Soft start comes from the drive ramp | No. The extra starts from a stop/restart at each defrost reversal "do not exceed the compressor design limits", but piping and contactor life should be checked |
| Copeland ZH/ZR scroll (quoted in Mimer report) [2] | ≤ 10 starts/h | none (scroll starts unloaded) | Same oil-return minimum-run rule | No |
| Danfoss (quoted in Mimer report) [2] | ≤ 12 starts/h; "a higher number reduces the service life" | 3 min recommended | Minimum run for motor cooling and oil return | No (qualitative only) |
| Bitzer KT-420 (reciprocating, with frequency inverter) [4] | 6/h (R290, R1270, R744, H-series); 12/h others | not stated | Longer minimum runs at low speed (oil return) | No |
| Hartford Steam Boiler, insurer (quoted in Mimer) [2] | — | start-delay timers advised | Rapid short-cycling "will significantly shorten motor/compressor life" | No |
| Gree Versati (I–III) [19][20] | not stated | 3-min restart lockout | "Heat run time" 1–10 min (default 3 min, or 5 min with 2-way valve). Oil-return routine and crankcase heater exist. First-generation manual: 6-min capacity hold after start | No |

Key observations:
- **The design variable is oil, not a counter.** Copeland's mechanism, quoted in Mimer [2]: at start, the crankcase pressure drops, the oil-refrigerant mix foams, and a large share of the oil is pumped out. If the run is too short, the oil is still in the circuit when the compressor stops. Repeated short runs give "progressive loss of oil" and bearing failure.
- **So the damage per start is roughly zero if the run is long enough to return the oil, and large if it is not.** Per-start damage is a strong function of run length, not a constant.
- **Flooded starts are the other mechanism.** Copeland's XHV guide says to test reliability under "compressor start after long off time with migration" and under frequent start/stop. Liquid dilutes the oil and damages bearings. The drive can use the motor windings as a crankcase heater, up to about 50 W [3].
- **So a start after a long, cold off period costs more than a start after a short warm one.** No maker quantifies the difference.
- **Inverter starts are electrically gentle.** The drive ramps from low speed (Copeland: "soft start ... with a defined ramp-up speed" [3]), so there is no locked-rotor inrush and no contactor arcing per start. 42watt's claim that each restart produces a current surge applies to fixed-speed units [8]. Copeland flags contactor life only for fixed-speed-style switching around defrost [3].
- No manufacturer document read gives a quantitative stress figure per start for inverter starts.

### 3. The "100,000 starts" rule of thumb

- 42watt (German installer and marketplace blog, 2026) gives "70,000–80,000 operating hours and about 100,000 switching cycles" as a refrigeration and AC guideline. It derives a remaining-life formula: (100,000 − starts so far) ÷ starts per year [5].
- It names sources for other figures (BWP, Bosch, ZHAW, VDI 2067, Fraunhofer ISE), but **none for the 100k starts or 70–80k hours** [5].
- Its sibling article on cycling says claims of "half the lifetime" from cycling are not substantiated. It quotes Fraunhofer ISE that very short runs of only a few minutes can cause direct damage [6].
- The blog's thresholds (under 2,000/yr optimal, over 4,000/yr critical) are also unsourced [5].
- Over 20 years, 4,000/yr is 80,000 starts, so "critical" is just the 100k budget spread over a typical life. It is circular, not independent evidence.
- **Assessment:** the figure is plausible as an order of magnitude for older fixed-speed hermetics with contactors. It is not evidence about modern inverter rotary or scroll units. Confidence: low.

### 4. Field start and run-hour distributions (measured)

My analysis of the heatpumpmonitor.org last-365-day statistics [9] used 549 systems with ≥ 300 days of data, with starts scaled to a year:

| Metric | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|
| Compressor starts/yr | 943 | 1,419 | 2,168 | 3,055 | 5,212 |
| Compressor running h/yr | 2,153 | 2,761 | 3,488 | 4,163 | 4,714 |
| Starts per running hour | 0.26 | 0.41 | 0.66 | 1.05 | 1.69 |

- 15 % of systems exceed 4,000 starts/yr and 2 % exceed 10,000; the maximum is about 74,000, an outlier or artefact.
- Starts are detected by a power threshold of about 100 W, which can overcount pump-only activity. The method was validated within about 4 % against a Vaillant internal counter [10].
- One long-run Vaillant shows 9,292 starts in 7,194 compressor hours (1.29 starts per running hour) [10]. Energy Stats UK's 5 kW Vaillant shows 2,575 starts in 4,040 h (0.64 per hour) [11].
- Fraunhofer ISE WP-QS (77 heat pumps in existing buildings, 4 years) gives 550–15,800 starts/yr. 90 % are under 5,500 and about a third are at or under 2,000 [6]. This is second-hand via 42watt; the primary report was not retrieved.
- **Implication:** with any start budget of 100k or more, typical systems reach end-of-life by hours (70–80k h at about 3,500 h/yr is about 20–23 years) before they reach it by starts (100k at 2,200/yr is about 45 years).

### 5. Field reliability versus cycling (indirect)

- UK RHPP, about 700 monitored sites: "a very large proportion of ASHPs have 10 minute on-to-on cycling patterns" (GSHP median 18 min). No single factor explained good or poor performance [13].
- The deep-dive of 21 case studies reports at least 10 households with a "significant problem". The listed problems were faulty units or sub-systems, installation, antifreeze, condensate, blockages and unintended resistance heating. The report does not attribute compressor failures to cycling [13].
- This is not a reliability study, but a fleet cycling at about 6/h did not produce a reported compressor-failure signal.
- Energy Stats UK (owner-engineer, Vaillant): compressors are "as tough as old boots", and short cycling adds wear but is unlikely to break the unit [11]. This is opinion, not data.
- The Energy Stats UK myths page gives a typical heat-pump life of 15–20 years [12].
- 42watt says compressors typically last 15–20 years and modern inverter units 20–25 years, citing Bosch, BWP and ZHAW [5][8].
- **There is no field dataset linking start counts to compressor failure.** Trystan Lea noted that a heatpumpmonitor contributor was building a lifespan model from system volume and oversizing, but no results are published in the thread [10].

### 6. Warranty conditions

- **Vaillant compressor warranty (10 years; flexoTHERM, flexoCOMPACT, geoTHERM)** [15], dated January 2019:
  - It covers material and manufacturing defects of the compressor, material costs only.
  - Conditions are installation by a recognised contractor per the instructions, operation per the operating manual, and regular maintenance.
  - Exclusions include wear parts, errors from ignoring the manual, external influences and "unusual stress".
  - **There is no start-count or run-hour cap.**
- **Vaillant general and digital guarantee** [14][16]:
  - The base guarantee is 2 years.
  - It extends to 5 years with myVAILLANT registration within 180 days, a permanent internet connection and annual maintenance.
  - Vaillant monitors fault messages remotely.
  - No start-count condition is stated on the page.
- **Viessmann** [17]: 5 years with a ViCare connection kept for the whole period, plus annual inspection and maintenance. No start or hour condition is stated.
- **Second-hand (42watt table)** [5]:
  - Bosch: 5 years, or 7 with HomeCom Pro; it falls back to 5 after more than 12 weeks offline.
  - NIBE: 5 years with myUplink.
  - Panasonic Aquarea: 2/3/5 years depending on commissioning and maintenance.
  - Mitsubishi Ecodan: 5 years.
  - **Alpha Innotec: 5 or 10 years, "limited by operating hours"**, the only hours-based limit seen. The cap value was not retrieved.
- **Pattern:** warranties require connectivity, maintenance and correct installation. Several makers can read compressor start and hour counters remotely (Vaillant, Viessmann, NIBE show them in service menus [5]), yet none publishes a start cap. This suggests makers do not expect start counts in normal operation to drive failures within 5–10 years.
- **Gree:** not found (see Open questions). Gree's own manuals contain only the protective timers above [19][20].

### 7. Per-start wear cost: bounding calculation (my arithmetic)

Assumptions (low confidence):
- The life budget is L starts, with linear wear.
- Compressor replacement costs C, including refrigerant work.
- Electricity costs €0.20/kWh.
- The energy cost of a start is about 0.19 kWh of heat, about 0.05 kWh of electricity at COP about 4 (verify-C4 / gap-G4 notes).

| L (starts) | C = €1,500 | C = €3,000 | C = €5,000 |
|---|---|---|---|
| 50,000 | €0.030 (0.15 kWh-e) | €0.060 (0.30 kWh-e) | €0.100 (0.50 kWh-e) |
| 100,000 | €0.015 (0.075 kWh-e) | €0.030 (0.15 kWh-e) | €0.050 (0.25 kWh-e) |
| 300,000 | €0.005 (0.025 kWh-e) | €0.010 (0.05 kWh-e) | €0.017 (0.08 kWh-e) |

Two corrections apply to this table:
1. **Lower:** if the compressor reaches end of life by hours or age first, the marginal wear cost of an extra start is about zero. In this house, starts would need to exceed about 4,000–5,000/yr before they become the binding budget over a 20-year life.
2. **Higher, per bad start only:** a run too short to return oil, or a flooded start, costs far more than the average. That is a cliff, not a price, and it is handled with constraints.

**Result:** a reasonable optimiser start weight is 0.05–0.3 kWh-electric-equivalent per start, with a central value of about 0.15. That is 1–5× the energy cost of a start. Even at 0.3 kWh-e, it equals only about 18 min of running at 1 kW electrical. It should never justify a higher flow temperature or a high-speed catch-up: 1 K of flow temperature costs about 2–3 % of COP over every running hour.

## What this means for controlling this house

1. **Price starts moderately and enforce hard limits** (confidence: medium).
   - In an MPC or planner, use a start cost of about 0.15 kWh-electric-equivalent, with sensitivity range 0.05–0.3.
   - Add hard constraints:
     - minimum compressor run of 20 min, 30 min preferred in heating; the oil-return argument [2][3] plus energy notes;
     - at most 3 starts per rolling hour, safely below Copeland's 10/h, Danfoss's 12/h and Bitzer's 6/h;
     - the firmware's 3-min lockout, plus your own minimum off time of 10–15 min.
   - Test: log coil 80 transitions and coil 87 (oil return) events. If oil-return events become more frequent after short runs or at low frequency, lengthen the minimum run.
2. **Do not raise flow temperature or compressor speed to avoid starts** (confidence: medium-high).
   - The house's start rate is 2–8/day in mild weather plus DHW, about 1,000–3,500/yr. That is at or below the field median of 2,168/yr [9], and roughly 20–70k starts over 20 years, below even the pessimistic 100k rule [5].
   - Trading 1 K of flow temperature (about 2–3 % COP) for fewer starts is a bad deal on every assumption in section 7.
3. **Treat a daily start budget as a soft target, not an objective** (confidence: medium).
   - A cap of about 12 starts/day (about 4,400/yr) keeps the house inside even 42watt's conservative band and below the p90 of the field fleet.
   - In mild weather, aim for 3–6 runs/day, each of 1–4 h. The budget then never binds, and the planner can place runs for PV and warm hours.
4. **Avoid "bad" starts more than starts in general** (confidence: low-medium; mechanism documented, magnitude unknown).
   - Avoid runs that end before oil return, i.e. under about 10–20 min, especially at minimum frequency.
   - Avoid restarts in very cold weather after long off periods without the crankcase heater. The Gree crankcase heater is visible on coil 84; check it is energised during long cold off periods.
   - Avoid DHW-triggered interruptions that create two short space-heating fragments.
   - Test: count runs under 20 min per week. The target is about zero, apart from DHW and defrost.
5. **Defrost transitions may dwarf control starts on humid 0 °C days** (confidence: low; unverified for Gree).
   - Copeland recommends a stop and restart at each defrost reversal on its variable-speed scroll [3].
   - If the Versati also stops the compressor around reversal, a day with 10–15 defrosts adds 20–30 compressor starts the controller does not choose.
   - Check coil 80 against coil 86 on a humid +1 °C day. If true, the marginal start from your controller is even less significant against the total.
6. **Warranty: keep evidence of correct operation, not a low start count** (confidence: medium for the industry pattern, unknown for Gree).
   - Warranties seen require maintenance, correct installation and use per the manual. None caps starts [15][16][17].
   - Do not run the unit outside its documented limits, e.g. writing setpoints that force rapid toggles or Mode/On-Off cycling.
   - Keep the Modbus writes and the maintenance record.
   - Ask the Lithuanian installer or distributor for the written Gree warranty text, and whether it covers the compressor separately.

## Contradictions and open questions

- **Rate limits disagree.** Copeland allows 10/h, Danfoss 12/h and Bitzer 6/h with natural refrigerants and inverters. Forum lore says 3/h. They are all hourly limits and say nothing about lifetime totals.
- **100k starts versus "starts barely matter".** 42watt gives an unsourced 100k-start life [5]. Copeland says extra defrost starts are within design limits [3], and field fleets cycling about 6/h show no reported failure wave [13]. These cannot be reconciled without manufacturer qualification data.
- **The Göbel "12 %/15 %" claim cannot be traced** [1]. It would imply super-linear wear. If the original (possibly a fixed-speed or refrigeration study) is found, check the compressor type and failure mode.
- **Open:**
  - Do Chinese or Japanese rotary-compressor makers (GMCC, Highly, Landa (Gree's own), Panasonic, Mitsubishi) publish start/stop endurance test counts? Reliability standards for room-AC compressors reportedly include on/off cycling tests, but I could not search for them in this pass.
  - Gree's warranty terms for the Versati in Lithuania or the EU: duration, compressor coverage, conditions.
  - The primary Fraunhofer ISE WP-QS report: does it relate start counts to failures or service calls?
  - The Swiss FAWA / BFE long-term field studies (Hubacher), which tracked failures in hundreds of heat pumps. Do they report compressor failure rates against cycling?
  - Whether the Versati stops the compressor during defrost reversal, and how often its oil-return routine (coil 87) runs as a function of run length and frequency.
- **Unknown cost basis:** the price of a Gree two-stage rotary compressor replacement in Lithuania, including R32 recovery and recharge. Section 7 uses €1,500–5,000.

## Sources

1. The Impact of Controller Settings in Heat Pumps: Numerical Findings and Experimental Verification - S. Göbel, K. Waiz, C. Vering, D. Müller (ECOS 2023) - 2023 - https://proceedings.com/content/069/069564-0075open.pdf - paper (HiL lab + simulation) - Origin of the "12 % more cycles → up to 15 % life" claim; the citation points to an unrelated reference and no "Perrin" is listed; bad settings raise starts up to 300 %.
2. Effects of cycling on domestic GSHPs: simulation/modelling, Report C207-R2 (Appendix A: manufacturer and insurer notes) - R. Curtis, T. Pine, Mimer Energy for EA Technology/DECC - 2012 - https://assets.publishing.service.gov.uk/media/5a7a37f9e5274a319e778b1d/mimer_report_on_modelling_cycling_of_heat_pumps.pdf - report quoting manufacturers - Danfoss ≤ 12 starts/h, 3-min delay, more starts reduce service life; Copeland oil pump-out mechanism and 10 starts/h; Hartford Steam Boiler on short-cycling shortening life.
3. Application Guidelines: Copeland variable-speed heat-pump scroll XHV with ED3 drive - Copeland - c. 2018-2024 - https://media.copeland.com/6937539b-0c9e-41d6-8a97-b16b0107724a/C060239_1218_E_AGL_HPScroll_XHV_VS_FULL.pdf - manufacturer - ≤ 10 starts/h, ≥ 1 min off, minimum run set by oil return, oil routine below 1,800 rpm, soft-start ramp with ≥ 30 s hold, extra defrost starts within design limits, failures stem from system problems, flooded-start and migration testing.
4. KT-420 Cycling rate and minimum running times - BITZER - n.d. - https://bitzer.de/shared_media/html/kt-420/en-GB/242642187242698891.html - manufacturer - with inverters 6 starts/h (R290/R1270/R744/H-series), 12/h others; longer minimum runs at low speed for oil return; no life figure.
5. Lebensdauer Wärmepumpe (compressor starts, hours, warranty table) - 42watt - 2026 - https://42watt.de/magazin/lebensdauer-waermepumpe - blog (German; key figures unsourced) - 100,000-start and 70–80k-hour rule of thumb, start bands, compressor replacement €2–5k, manufacturer warranty table (Alpha Innotec hour-limited).
6. Taktung Wärmepumpe - 42watt - 2026 - https://42watt.de/magazin/taktung-warmepumpe - blog citing Fraunhofer ISE WP-QS 2025 - 550–15,800 starts/yr in 77 heat pumps, 90 % < 5,500; "half the lifetime" claims unsubstantiated; Fraunhofer quote on direct damage from very short runs.
7. Verdichter Wärmepumpe - 42watt - 2026 - https://42watt.de/magazin/verdichter-warmepumpe - blog - start wear mechanisms (oil carry-over, liquid slugging, crankcase heater), lower flow temperature protects oil; no rotary vs scroll life data.
8. Inverter Wärmepumpe - 42watt - 2026 - https://42watt.de/magazin/inverter-warmepumpe - blog - qualitative only: inverter lifetime 20–25 years (unsourced); restart current surges apply to on/off units.
9. heatpumpmonitor.org last-365-day system statistics (own analysis, n = 549 with ≥ 300 days) - OpenEnergyMonitor community - retrieved 2026-11-06 - https://heatpumpmonitor.org/system/stats/last365 - field data - starts/yr, running h/yr, starts per running hour distributions.
10. HeatpumpMonitor.org starts & starts per hour (thread) - T. Lea, M. Wall and others - 2024 - https://community.openenergymonitor.org/t/heatpumpmonitor-org-starts-starts-per-hour/26246 - forum - Vaillant 9,292 starts / 7,194 h; start detection validated within 4 %; a lifespan model in progress, no results.
11. Heat pump cycling - M. Wall, Energy Stats UK - 2024-2025 - https://energy-stats.uk/heat-pump-cycling/ - blog with owner data - 2,575 starts / 4,040 h (0.64/h); author's view that compressor wear from normal cycling is minor; rules of thumb for cycles per hour.
12. Heat pump myths - M. Wall, Energy Stats UK - 2024-2025 - https://energy-stats.uk/heat-pump-myths/ - blog - typical heat-pump life 15–20 years; no start or lifetime data.
13. Final report on analysis of heat pump data from the RHPP scheme - R. Lowe et al., UCL RAPID-HPC for BEIS - 2017 - https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/606818/DECC_RHPP_161214_Final_Report_v1-13.pdf - field data - most ASHPs on about 10-min on-to-on cycles; 10 of 21 case studies had significant problems, none attributed to compressor cycling.
14. Garantie (Vaillant Deutschland) - Vaillant - 2025/26 - https://www.vaillant.de/heizung/service/garantie/ - manufacturer - 2-year base, 5-year GarantiePLUS, 10-year compressor terms document.
15. Herstellergarantie für Wärmepumpen-Kompressoren (flexoTHERM, flexoCOMPACT, geoTHERM) - Vaillant - January 2019 - https://www.vaillant.de/api/download/document/de/download_garantiebedingungen-waermepumpen-kompressoren_1457328.pdf - manufacturer - 10-year compressor warranty, material cost only; conditions are installation, operation per manual and maintenance; no start or hour cap.
16. Digitale Garantie - Vaillant - 2025/26 - https://www.vaillant.de/service/garantie/digitale-garantie/ - manufacturer - 5 years with permanent internet connection, annual maintenance, remote fault monitoring.
17. Garantie (Viessmann Deutschland) - Viessmann - 2025/26 - https://www.viessmann.de/de/services/garantie.html - manufacturer - 5 years tied to ViCare connection plus annual maintenance; no start or hour limit stated.
18. Scroll compressor - Wikipedia - accessed 2026 - https://en.wikipedia.org/wiki/Scroll_compressor - reference - fewer moving parts (maker claim about 70 % fewer than reciprocating); "wear-in" axial compliance; no start-life data.
19. Gree Versati user manual (EN) - Gree - c. 2019+ - https://cdn.shopify.com/s/files/1/0253/4775/2018/files/GREE-USER-MANUAL-VERSATI-EN-WEB.pdf - manufacturer - "Run time" parameter 1–10 min (default 3 min, or 5 min with 2-way valve); no warranty or start-life text found in the extractable text.
20. Gree Versati service manuals and Modbus map (as compiled in note 08-gree-versati, sources [1][2][3][5] there; e.g. https://gree-bulgaria.com/manuals/archive/5_Versati-TSM.pdf) - Gree - 2012-2024 - manufacturer - 3-min restart lockout, 6-min capacity hold (first generation), oil-return state (coil 87), crankcase heater state (coil 84); no start-count design life.
