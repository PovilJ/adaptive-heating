# Field evidence: what the best-performing real installations do

Scope: measured field data on air-to-water heat pumps. Sources are heatpumpmonitor.org (my own statistics on the public dataset), the UK RHPP and Electrification of Heat trials, Fraunhofer ISE (WPsmart im Bestand, WP-QS im Bestand), Danish Technological Institute, Swedish SBUF, Swiss OST/HSLU work, vendor results from Nordic optimisers, and the OpenEnergyMonitor community. The question: which drivers of seasonal performance are statistically strongest, how large are they, how much of the gap between average and top systems is controls, and what follows for this house (slab UFH, Gree Versati 9 kW, minimum output about 3.7 kW, flow setpoint written over Modbus, restart only once setpoint minus outlet is at least about 4 K).

Process note: this session's shared web-search budget ran out before my first query, so all three search attempts were refused. To make up for it I (a) fetched known primary-source URLs directly and extracted the PDF text locally, and (b) ran my own statistics on the full heatpumpmonitor.org public dataset: 856 systems with annual stats and about 69,000 system-days of daily data from 113 UFH systems. That analysis is labelled "own analysis [1]". It is field data, but the analysis is mine and has not been peer reviewed. Swiss FAWA, Polish and Finnish field reports could not be reached without search. They are listed as gaps.

---

## Summary

- **Flow temperature is by far the strongest measured driver.** Across 470 well-metered air-source systems with at least 300 days of data, combined SPF falls 0.084 per K of mean running flow temperature (t = -15). For space heating alone the fall is 0.12 per K (n = 312), which is about 2.5-3 % per K [1]. Within the same system and the same 2 K outdoor band, days running 1 K hotter than usual have 3.6 % lower COP. At 2 K hotter it is -6.6 %, at 3 K -10.3 % [1]. The Danish and Polish rules of thumb (2-3 %/K) agree [16][17][39]. For ground source the figure is 1-2 %/K [18].
- **Top-quartile systems run 5-6 K cooler water than bottom-quartile ones**: weighted mean flow 32.6 vs 38.2 °C, temperature lift 25 vs 31 K, SPF 4.50 vs 3.25 [1]. Among UFH-only systems, the top quartile's median space-heating flow is **29.3 °C** (bottom quartile 33.0 °C), with SPF 4.61 vs 3.28 [1]. The best UFH systems (SPF 5.0-5.4) average **25-30 °C** over the year and only about 27-33 °C on the coldest day [1][3].
- **Top systems do not avoid cycling.** Median compressor starts per day: top quartile 5.9, middle 5.5, bottom 6.7. Median run per start is about 97 min in the top quartile and 66 min in the bottom [1]. Several SPF 5+ systems start 7-15 times a day (for example SPF 5.23 at 14.7 starts/day, mean run 36 min) [1].
- **Starts cost little; hot water costs a lot.** Cross-sectionally, each extra start per day costs about 0.009 SPF, so going from 6 to 24 starts/day costs about 0.16 SPF (about 4 %) [1]. Within a system (same outdoor band, flow temperature held constant), the start count has almost no effect: -0.001 to -0.008 COP per start [1]. RHPP found no correlation between cycle length and monthly COP [10]. Lab tests do show a real penalty, but only once runs fall **below about 6 minutes** [12][11].
- **Avoiding cycling by raising the flow temperature loses energy.** On mild days (6-14 °C, no hot water) in UFH systems, days with 10-25 starts had 3-4 % higher COP than the system's average for that weather. Days with 0-2 starts were 2-5 % lower [1]. The days that cycle more are the ones running cooler water.
- **Very low duty is the real mild-weather penalty.** On mild days, a compressor runtime fraction below 0.3 coincides with 6-8 % lower COP than days at 0.3-0.9 [1]. Inverter field data show %-Carnot is stable over most of the range but collapses below a unit-specific minimum electrical power [21]. Standby and parasitic loads also weigh more when little heat is delivered [10].
- **About 60 % of the top-vs-bottom gap is temperature lift and about 40 % is %-Carnot** (machine quality, modulation, cycling, defrost, pumps) [1]. In a multivariate fit (flow, outdoor temperature, starts/day, DHW share, sizing; R² = 0.42), flow temperature explains about 0.40 of the 1.25 SPF quartile gap, sizing about 0.08, starts/day about 0.01 and DHW share about 0.01. The rest is unexplained (model, metering, installation) [1]. Fraunhofer ISE also found that flow temperature was the *only* variable correlated with SPF [15].
- **Controls share of the gap: my estimate is 30-50 %**, mainly via the heating curve and flow temperature, plus DHW and immersion misuse. The Danish survey of more than 160 heat pumps found only about 15 % performing as expected. Too high a heating curve and wrong flow rates gave combined savings potential of up to 25 % [16]. Optimiser vendors report 5-15 % (Neogrid, Denmark) [20] and 20-23 % (Ngenic, Sweden, 50 homes, 12 months before/after) [19]. These are vendor numbers.
- **Field SPF is improving, but the spread is not shrinking.** UK EoH median ASHP SPF H4 is 2.80 (IQR 2.53-3.09, n = 291), against 2.44 under RHPP; the interquartile spread is similar [8]. Fraunhofer WP-QS: air-to-water mean JAZ 3.4 (range 2.6-4.9, n = 49) [13][14]. heatpumpmonitor.org median 3.89 (p10 3.15, p90 4.54) [1]. This is an enthusiast sample, but it shows what good control can reach.
- **Sizing matters moderately and is non-linear.** Rated output / heat loss of 1.0-1.5 gives median SPF 4.0. A ratio of 2-3 gives 3.46 and above 3 gives 3.16 [1]. An average load below 15 % of rated output gives median SPF 3.45, against 4.0 at 20-30 % [1]. This house (9 kW against about 6-8 kW at -20 °C) is in the good band by the design-load criterion. Its problem is the 3.7 kW minimum.
- **The cold tail is the hidden lever in a Lithuanian climate.** The only Lithuanian system in the dataset (Vilnius, 6 kW Nibe, slab UFH, about 30 °C flow) spent **31 % of its annual electricity on days below -16 °C, for 11 % of its heat**. Daily COP was 0.14-1.26, clearly backup resistance heat and/or defrost. From +4 to +8 °C its COP was 4.2 [1]. An Ottawa system shows the same shape [1].
- **Hot water is the second-largest fixable item.** Median DHW COP is 3.08, against 4.19 for space heating [1]. Days on which DHW is more than 40 % of the heat have about 15 % lower COP in mild weather [1]. In RHPP, more than half of the sites with SPF H4 below 2 used the immersion heater for over 20 % of their electricity [10].
- **Room-influence and cloud optimisers have no measured SPF advantage yet.** Pure weather compensation is the most common control among the top quartile (54 % of top-quartile systems vs 24 % of the bottom quartile). Its median SPF is 4.11, against 3.57-3.79 for "significant room influence" or simple setpoint control [1]. Community reports on Havenwise and Homely optimisers have no before/after numbers [33][34].
- **Defrost typically costs about 1.6 % of heat (about 0.15 COP)** in UK data. In Scotland one user measured 0.35-0.45 COP [7]. In humid -5 to +5 °C Lithuanian winters, expect the upper end.

---

## Detailed findings

### 1. The datasets and how much to trust them

| Dataset | n (ASHP) | Boundary | Strength | Weakness |
|---|---|---|---|---|
| heatpumpmonitor.org [1][2] | 470 after my filters (856 published) | about H4 (unit + pumps) | MID-class metering on many, 10 s data, daily and annual stats, metadata on controls | Self-selected enthusiasts, mostly UK (mean outdoor about 7.7 °C), so it is not representative and is biased towards good systems |
| UK Electrification of Heat (EoH) [8][9] | 291 ASHP (interim) | H2/H4 | Representative installs in 742 homes | Heat-meter errors, coarse data, R410a confound |
| UK RHPP [10] | 292 ASHP | H2/H4 | Large, 2013-15 | Heavy metering error, 2-min data, older units |
| Fraunhofer ISE WPsmart (2014-19) [15] | 29 ASHP / 12 GSHP | BG3 | Detailed instrumentation, German existing homes | Small n |
| Fraunhofer ISE WP-QS (2019-24) [13][14] | 49-61 ASHP | BG3 | Same, newer units | Small n; mild 2023-24 winters |
| DTI Denmark (Poulsen 2017, cited in [16]) | >160 | - | Nordic | Only secondary summary accessible |

My filters on [1]: air source, at least 300 days of data, heat and electricity data quality at least 90 %, no data flag, 1.5 < SPF < 7. That leaves 470 systems. Medians: SPF 3.89, space-heating COP 4.19, DHW COP 3.08, running flow 34.3 °C, space-heating flow 32.8 °C, starts 5.95/day, run per start 92 min, flow-return ΔT 3.9 K, DHW share of heat 8 %, rated output / heat loss 1.49 [1].

Distribution (SPF): p10 3.15, p25 3.50, median 3.89, p75 4.25, p90 4.54 [1].

### 2. Flow temperature: magnitude, consistency and what top systems run

**Cross-sectional (between systems)**

- OpenEnergyMonitor regression on heatpumpmonitor data: SPF H4 = -0.1008 × weighted flow + 7.42 (R² 0.52, ±0.55 prediction interval). That predicts 4.4 at 30 °C, 3.9 at 35 °C and 3.4 at 40 °C [3]. Using flow minus outside instead: SPF = -0.1054 × ΔT + 6.88 (R² 0.55) [3].
- My multivariate fit (n = 465): SPF = 6.64 - 0.0786·flow + 0.041·T_out - 0.0085·starts/day - 0.22·DHW share - 0.18·oversize ratio, with R² 0.42 [1]. For space heating only: COP = 7.96 - 0.12·flow_space + 0.036·T_out - 0.012·starts/day (R² 0.46, n = 312) [1].
- Binned by space-heating flow [1]:

| Mean SH flow | n | Median SH COP | Median SPF |
|---|---|---|---|
| < 30 °C | 56 | 4.83 | 4.34 |
| 30-32 | 68 | 4.61 | 4.28 |
| 32-34 | 81 | 4.15 | 3.82 |
| 34-36 | 56 | 4.04 | 3.72 |
| 36-38 | 28 | 3.73 | 3.42 |
| 38-40 | 17 | 3.50 | 3.36 |
| > 40 | 9 | 3.15 | 3.11 |

- EoH: mean flow across ASHPs was 38.3 °C. SPF falls with flow temperature, and the relationship is statistically significant despite the scatter [8]. High-temperature units performed like low-temperature ones because 81 of 94 HT units ran above 65 °C for under 1 % of the time [8].
- Fraunhofer WPsmart: average circuit temperatures were 34.6-52.4 °C at a mean outdoor -3 °C. SPF correlated *only* with circuit temperature, not with building age. The design-point temperature mattered less than the heating curve [15].
- RHPP: no single factor explained good or bad performance. Average winter SH flows were mostly below 45 °C [10].
- Coldest-day behaviour [3][4]: the mean flow on the coldest day across heatpumpmonitor systems is about 36 °C, about 7 K below the stated design flow. Systems reaching SPF 4 or more mostly ran below 40 °C on the coldest day, typically about 35 °C [4]. Fit: coldest-day flow = -5.7·SPF + 59.4, so SPF 4 means about 36.6 °C [3].

**Within-system (same house, same weather band; my own fixed-effects analysis [1])**

Using about 69,000 daily records from 113 UFH systems, demeaned within each system × 2 K outdoor band:

| Day's flow vs. that system's usual flow at that outdoor temperature | n days | COP vs. usual |
|---|---|---|
| -4 K | 3,980 | +16.8 % |
| -3 K | 2,655 | +8.9 % |
| -2 K | 4,560 | +6.6 % |
| -1 K | 8,557 | +3.5 % |
| 0 | 12,018 | +0.2 % |
| +1 K | 7,236 | -3.6 % |
| +2 K | 3,252 | -6.6 % |
| +3 K | 1,454 | -10.3 % |
| +4 K | 3,817 | -23.8 % |

The ±4 K bins are capped and contaminated by DHW-heavy days, so read the ±1-3 K rows as about 3-3.5 %/K. Fixed-effects slope: -0.093 to -0.12 COP per K, depending on outdoor band [1].

Supporting lab and engineering numbers: DTI says each +1 °C of flow costs 2-3 % COP [16][17]. An under-performing lightweight UFH floor needing 45 °C instead of 35 °C raises electricity 20-30 % [17]. A Polish example: 28 °C vs 35 °C flow at 0 °C source gives COP 5.38 vs 4.40, about 22 % more electricity at 35 °C [39]. Swedish GSHP: 1-2 % per K, 15-20 % per 10 K [18].

**What the top UFH systems actually run** [1]:

| Rank (SPF) | System | Unit | SPF | Mean running flow | Space-heating flow | Coldest-day mean flow | Starts/day | Run per start |
|---|---|---|---|---|---|---|---|---|
| 1 | 777 | Vaillant Arotherm+ 10 kW, UFH | 5.37 | 26.8 | 25.1 | 27.5 | 4.1 | 102 min |
| 3 | 479 | Arotherm+ 10, UFH | 5.26 | 25.3 | 29.1 | 31.6 | 6.3 | 103 min |
| 4 | 802 | Arotherm+ 10, UFH | 5.23 | 30.2 | 29.1 | 32.7 | 14.7 | 36 min |
| 8 | 568 | Arotherm+ 10, UFH | 5.11 | 28.1 | 27.1 | 29.1 | 5.6 | 110 min |
| 10 | 477 | Arotherm+ 12, UFH | 5.01 | 29.8 | 31.6 | 37.3 | 7.2 | 115 min |
| 14 | 584 | Arotherm+ 5, UFH | 4.87 | 31.1 | - | 33.4 | 4.2 | 195 min |
| 15 | 889 | Arotherm+ 7, UFH | 4.85 | 29.8 | 28.5 | 32.4 | 5.5 | 83 min |
| 18 | 591 | Viessmann 151A 8, UFH | 4.83 | 27.8 | 27.8 | 26.2 | 0.9 | 737 min |

Common pattern: single zone (92-96 % of the top decile are one zone), no buffer (91 % of the top decile have no hydraulic separation), pure weather compensation, coldest-day flow at or below about 33 °C, and space flow mostly 25-30 °C [1]. Most are UK houses, so their design outdoor temperature is about -2 to -4 °C, not -20.

UFH-only quartiles [1]: top 25 % (n = 41) have SPF 4.61, SH flow 29.3, flow-return ΔT 3.3 K, oversize ratio 1.33, 5.6 starts/day, 103 min/run. Bottom 25 % (n = 40) have SPF 3.28, SH flow 33.0, ΔT 4.6 K, oversize 1.89, 6.0 starts/day, 61 min/run.

### 3. Cycling: what the field data actually say

**Cross-sectional** [1]:

| Starts/day | n | Median SPF | Median flow | Oversize |
|---|---|---|---|---|
| 0-3 | 67 | 4.01 | 33.5 | 1.59 |
| 3-6 | 174 | 3.92 | 34.2 | 1.42 |
| 6-10 | 153 | 3.95 | 34.1 | 1.47 |
| 10-15 | 35 | 3.59 | 34.7 | 1.57 |
| 15-25 | 31 | 3.44 | 36.6 | 1.62 |
| > 25 | 9 | 3.43 | 35.5 | 1.70 |

SPF is flat up to about 10 starts/day and then falls about 0.4-0.5. The high-cycling group also runs hotter and is more oversized, so part of that fall is confounding. The regression coefficient is -0.0085 SPF per start/day when flow and sizing are controlled [1]. By manufacturer, Samsung and Midea have the highest median starts (13.4-13.7/day) and lower SPF (3.5 and 3.2). Viessmann and Grant have about 3/day and SPF 4.13 and 3.94 [1]. Unit-level control strategy shows up in the data.

**Within-system (daily, UFH systems)** [1]: with flow temperature held constant, the start-count coefficient is -0.0013 (mild 8-14 °C), -0.0078 (0-8 °C) and -0.005 (below 0 °C) COP per start. In mild weather, 10 extra starts in a day cost under 0.1 COP. %-Carnot efficiency is flat across start-count bins (within ±0.5 %) except at 25 or more starts/day (-0.6 to -1.4 %) [1].

**Lab** (EA Technology for DECC, fixed-speed units) [11][12]: run times of 2-4 min (one radiator open) gave large COP losses, and 5-7 min gave a smaller drop below the long-run line. "The bulk of the improvement is achieved with run times of around 6 minutes." The worst-case GSHP loss was about 16 %. Room-thermostat-induced cycling at *lower* flow temperature could actually give better COP than continuous running at higher flow. The authors still recommended a minimum run of about 6 min for compressor oil return and reliability [12].

**RHPP field** [10]: 49 % of ASHP sites had at least one month with a median on-to-on cycle of 10 min. 25 % had at least 10 % of cycles shorter than 12 min all year. No correlation was found between median cycle length and monthly COP, possibly masked by metering error [10].

**Community** [25][28][29]: "Demand cycling" (thermostat on/off with a too-high curve) is where people lose efficiency. Short "compressor load cycling" at minimum modulation with low flow is acceptable [25]. One anecdote: 8 cycles/h at COP about 2.5, changed to near-continuous 0.6-0.9 kW running at COP about 4 [29]. That improvement came from leaving 5-10 minute cycling, not from going from 10 to 2 starts a day.

**Synthesis:** cycling hurts when cycles are minutes long (fewer than about 6-10 min on) or when the controller raises flow temperature to suppress it. Ten to fifteen cycles a day of 30-120 min each are not measurably harmful in field data.

### 4. Mild weather and minimum modulation

- In 113 UFH systems (heatpumpmonitor daily data [1]), median daily COP peaks at outdoor 9-12 °C (4.70) and %-Carnot peaks at 6-9 °C (49.9 %). Starts/day peak at 7 in the 9-12 °C band and runtime fraction is 0.45. Mild-weather cycling does not crater efficiency in these systems.

| Outdoor | Starts/day (median) | Runtime fraction | COP | Flow | %-Carnot |
|---|---|---|---|---|---|
| -3..0 °C | 1 | 0.99 | 2.97 | 34.2 | 45.9 |
| 0..3 | 2 | 0.98 | 3.36 | 33.2 | 47.5 |
| 3..6 | 3 | 0.88 | 3.94 | 32.5 | 49.3 |
| 6..9 | 6 | 0.67 | 4.53 | 31.5 | 49.9 |
| 9..12 | 7 | 0.45 | 4.70 | 31.3 | 48.5 |
| 12..15 | 5 | 0.21 | 4.36 | 33.1 | 46.4 |
| 15..18 (DHW-dominated) | 2 | 0.07 | 3.51 | 42.5 | 44.1 |

- Above about 12 °C outdoors the runtime fraction drops below 0.2, and COP falls because DHW dominates and fixed and standby loads weigh more [1].
- On mild no-DHW days, a runtime fraction below 0.3 gives -6 to -8 % COP against the same system's typical day, while 0.3 to above 0.9 are all about equal (+2 to +3 %) [1]. A Swiss field analysis of inverter units (BFE monitoring) found %-Carnot stable over wide ranges but collapsing below unit-specific low electrical part-load limits. Lab rating points do not capture this [21].
- Example, Danish Nibe S2125 (Silkeborg, UFH, 7.6 kW) [1]: runs continuously below +8 °C (0-2 starts/day). Its best COP, 5.63, comes at 8-12 °C with 11 starts/day and a 0.74 runtime fraction. At 12-16 °C it gives COP 4.98 at a 0.22 runtime fraction.
- Example, Swiss Daikin 12.7 kW UFH (Lucens) [1]: 13 starts/day at 8-12 °C with COP 4.09, the same as or better than 3 starts/day at 0-4 °C (COP 3.29). Mild weather is still the efficient part of the year, despite cycling.
- Measured minimum outputs: Vaillant Arotherm 10/12 kW about 5.9 kW minimum, but it still ranks among the best systems. The analyst credits well-controlled degree-minute cycling for compensating a narrow modulation range [26]. That is directly analogous to a 9 kW Versati with a 3.7 kW minimum.
- Simulation for a Swiss net-zero UFH house: an inverter gives up to 30 % COP gain from part-load efficiency. Strong oversizing pushes the unit into cycling at colder temperatures, where the part-load gain trades against cycling losses [22]. The same study found that running the heat pump on PV surplus raised total energy use, because it needs higher indoor and water temperatures exactly when solar gains would have warmed the house anyway [22].

### 5. Sizing

Binned on heatpumpmonitor (rated output / stated heat loss) [1]:

| Ratio | n | SPF | Starts/day |
|---|---|---|---|
| < 1.0 | 46 | 3.98 | 4.4 |
| 1.0-1.25 | 82 | 3.99 | 5.1 |
| 1.25-1.5 | 113 | 4.03 | 6.8 |
| 1.5-2.0 | 153 | 3.85 | 6.2 |
| 2.0-3.0 | 62 | 3.46 | 6.0 |
| > 3.0 | 14 | 3.16 | 5.9 |

Average heat load / rated output: below 0.15 gives SPF 3.45, 0.15-0.2 gives 3.84, 0.2-0.3 gives 4.00 and above 0.3 gives 4.07 [1]. Oversizing costs efficiency, but mostly *not* via more starts: starts/day is flat across sizing bins. It acts through low part-load efficiency, standby share and possibly higher flow setpoints. EoH top-10 systems include oversizing factors of 1.56-2.4 at SPF 4.0-4.68 [9]. Fraunhofer WP-QS found many units oversized relative to measured consumption and some with very high switching frequencies [13].

### 6. Domestic hot water, immersion and legionella

- DHW COP median 3.08 (p10 2.28, p90 3.70) against SH COP 4.19 [1]. EoH, RHPP and Fraunhofer also find DHW less efficient [8][10][13].
- Within-system [1], with outdoor at 6-14 °C: days with a DHW share of heat of 0-40 % have about normal COP, while above 40 % gives -15 %. At 0-6 °C outdoor, above 40 % gives -8.7 %.
- RHPP [10]: immersion averaged 12 % of electricity where it was monitored. More than half of the sites with SPF H4 below 2 had immersion above 20 % of electricity. Typical misuse: immersion after every heat-pump DHW cycle, or immersion instead of the heat pump.
- Fraunhofer WP-QS [13]: some combi-store systems mixed the SH and DHW temperature levels, delivering space heat at DHW temperature. Heating-rod energy was only 1.3 % of electricity in mild 2023-24. Significant heating-rod use was found only with a defect, wrong parameters or legionella mode [15].
- Vaillant field practice: an "Eco" DHW mode capping compressor power at about 50 % often gives DHW SCOP above 3.8 [37].
- Legionella: 42 % of top-quartile systems on heatpumpmonitor have legionella cycles disabled, against 36 % in the bottom quartile [1]. The difference is weak. Weekly disinfection is common in both groups.

### 7. Control type

| Control (heatpumpmonitor self-reported) | n | SPF | SH COP | SH flow | Starts/day |
|---|---|---|---|---|---|
| Pure weather compensation, no room influence | 178 | 4.11 | 4.39 | 31.8 | 5.9 |
| WC + a little room influence | 82 | 3.79 | 4.18 | 32.8 | 5.7 |
| WC + simple set-point (on/off) | 35 | 3.79 | 4.10 | 33.5 | 5.5 |
| WC + significant room influence | 25 | 3.57 | 3.93 | 34.4 | 5.3 |
| Custom controller | 9 | 3.94 | 4.26 | 35.0 | 6.9 |
| Room influence only (Auto-adapt) | 9 | 3.84 | 3.89 | 35.8 | 4.4 |

Source: [1]. The ordering follows flow temperature: more room influence goes with hotter water and fewer starts. This is association, not causation. Owners who tune pure weather compensation are probably also the ones who lower curves. EoH attributes the similar performance of HT units to weather compensation keeping them low most of the time [8]. Heat Geek argues weather compensation avoids catch-up at elevated flow temperature, while room/load compensation "may need to run hotter to replace heat that has already left the building" [36]. Mitsubishi Auto-Adapt users report it can match weather compensation with less cycling: 3.4 rose to 3.6 rolling SCOP, a peak of 38 °C vs 40 °C, and COP 4.0 vs 3.5 on two days [31]. That is anecdotal. Vaillant's energy integral starts at -60 K·min and lets slow UFH run past target before cut-off, giving 1 h on / 30 min off cycles in mild weather [30]. Cloud optimisers (Havenwise, Homely) have no measured SPF uplift in community data. One user found the optimiser "too aggressive", alternating full power and idle [33][34].

### 8. What fraction of the gap is controls?

1. **Physics split** (my analysis [1]): ln(SPF) = ln(%-Carnot) + ln(Carnot COP). Top-quartile vs bottom-quartile mean ln(SPF) differs by 0.358. Of that, 0.210 (59 %) is lift (weighted flow minus outside: 25.0 vs 31.1 K) and 0.146 (41 %) is %-Carnot (51.5 vs 44.8 %). Correlation of SPF with lift: r = -0.62; with %-Carnot: r = +0.72. OpenEnergyMonitor's earlier analysis: %-Carnot R² 0.54, lift R² 0.5, so "system temperatures explain roughly half" [4].
2. **Attribution** (multivariate [1]): of the 1.25 SPF gap between quartiles, flow temperature explains about 0.40 (32 %), sizing about 0.08 (6 %), outdoor climate about 0.02, and starts and DHW share about 0.01 each. About 55-60 % is unexplained by these observable variables (unit model and generation, metering, pumps, defrost, installation quality).
3. **How much of that is controls?** The lift share is set by emitters (fixed for this house) *and* by the heating curve and setpoint strategy (pure controls). Field evidence shows that most systems' emitters could run lower than they do: the coldest-day flow is on average 7 K below design [4], and the Danish survey points to curves "set too high" as a main cause [16]. Part of %-Carnot is controls too (compressor speed and modulation choice, DHW mode, avoiding sub-6-minute cycles, avoiding catch-up bursts at high compressor speed). One example: 35 °C flow at 7 °C outdoors gives COP 4.6 at 40 rps but 3.3 at 110-120 rps [6].
   **Estimate: 30-50 % of the average-to-top gap is attributable to controls and settings.** The rest is hardware, emitters and installation. Independent corroboration: DTI up to 25 % savings potential from curve and flow-rate fixes [16]; OPSYS MPC 13 % in a test rig on an already-efficient installation (COP 3.9), with a hypothesised 25 % for typical SPF-3 installs [16]; Ngenic 20-23 % [19]; Neogrid 5-15 % [20]. Confidence: medium.

### 9. Cold climate and defrost

- Vilnius, Lithuania (system 887; 6 kW Nibe AMS 20-6, slab UFH, design -24 °C, measured heat loss 3.76 kW, single zone, pure weather compensation, Aug 2025-Sep 2026) [1]:

| Outdoor band | Days | COP | Share of annual elec | Share of annual heat | Median flow |
|---|---|---|---|---|---|
| < -16 °C | 19 | 0.14-1.26 | 31 % | 11 % | about 34 |
| -12..-8 | 17 | 2.10 | 14 % | 12 % | 32.6 |
| -8..-4 | 12 | 2.62 | 7 % | 8 % | 31.6 |
| -4..0 | 25 | 3.21 | 12 % | 15 % | 30.3 |
| 0..+4 | 42 | 3.80 | 14 % | 21 % | 30.2 |
| +4..+8 | 48 | 4.16 | 10 % | 17 % | 30.0 |
| +8..+12 | 14 | 4.67 | 2 % | 3 % | 30.4 |

  Annual combined SPF is 2.5. %-Carnot falls from about 51 % above -4 °C to 30 % at -16 °C and 5-13 % below -20 °C. That points to resistance backup heat and/or heavy defrost, not to flow temperature, which stayed at about 34 °C. Starts/day were 14-19 all winter (11.7 average). This was an undersized 6 kW unit, and the backup heater is likely inside the metered boundary. Single system, so low confidence for generalising.
- Ottawa (Gree Flexx 7 kW, UFH via 300 L buffer) [1]: COP 1.4 at -20..-16 °C, 1.95 at -12..-8 °C and 3.37 at +4..+8 °C. Days below -8 °C were 45 % of annual electricity. Flow was only 35-37 °C, so the losses again come from the cold tail, not water temperature.
- Defrost: median about 1.6 % of net heat (about 0.15 COP) across heatpumpmonitor. A Scottish 12 kW user measured 0.35-0.45 COP loss, possibly 0.5-0.6 including frost build-up [7]. EA Tech lab: long-run COP at low ambient drops "significantly" once defrost energy is included [12].
- Swiss/Czech/Danish/German UFH systems with design temperatures of -5 to -13 °C (Lucens, Ricany, Silkeborg, Frederikssund, Altlandsberg) reach annual SPF 3.0-3.7 at mean outdoor 3-5 °C, with COP 2.7-2.9 at -8..-4 °C [1].

### 10. Nordic and German control practice (secondary)

- Fraunhofer WPsmart conclusion: the heating curve matters, the design-point temperature less so. Only circuit temperature correlates with SPF. Sanierung to new-build standard is not required [15].
- Ngenic (Sweden) "Tune": 50 of 500 customers evaluated 12 months before/after gave -23 % kWh total and -21 % mean. With price control it was -24 %, without -20 % [19]. This is a vendor slide, probably confounded by weather and including comfort setbacks.
- Neogrid PreHEAT (Denmark, more than 400 buildings): 5-15 % energy savings by MPC on heat-pump schedules, via relay or by manipulating the outdoor sensor [20].
- DTI OPSYS: up to 13 % savings with MPC on an already-efficient installation (COP 3.9 with PI control). An ANN controller cut forward temperature by up to 1.5 K [16].
- HSLU (Switzerland): a weather-forecast MPC trial in one building over 3 winter months improved efficiency, with no overall % published [23]. DTU EMPC pilot: energy savings and load shifting versus PID, with practical problems in forecasts and model fidelity [24].

---

## What this means for controlling this house

House facts used: heat loss about 0.14-0.20 kW/K, so about 6-8 kW at -20 °C, about 3-4.4 kW at 0 °C and about 1.7 kW at +10 °C. Slab storage about 6.6 kWh/K. Versati minimum about 3.7-3.8 kW. Rated 9 kW, giving a ratio of about 1.1-1.5 to design load, which is the best bin in the field data. Single zone, no buffer: also the field-best configuration [1]. Current practice is setpoints of 31-36 °C (peaks 39), catch-up draws up to about 3 kW at +2 °C, runs of 0.5-4 h, and DHW interrupting space heating.

**Main conclusion.** The field evidence says the biggest available gain is in **water temperature**, not in the number of starts. The owner's two worries are linked. The on/off pattern isn't costly in itself (runs of 0.5-4 h are long by field standards). The costly part is the **elevated-setpoint catch-up runs** used to trigger restarts or recover temperature. Each extra kelvin costs about 3 %, so a catch-up at 39 °C where 31 °C would do costs about 20-25 % on that energy [1][16].

Concrete, testable rules (confidence in brackets):

1. **Target the lowest steady flow that holds 22 °C, then never exceed it by more than about 2 K for recovery** (high). Benchmarks for slab UFH: top systems average 25-30 °C space flow and about 27-33 °C on their coldest days [1]. Their coldest days are about -3 °C, so expect this house to need more at -20 °C, but at -5..+5 °C it should be about 26-31 °C if the slab emitter is adequate. Test: hold a constant setpoint for 48-72 h at a given outdoor band and step it down 1 K at a time until room temperature drifts below 21.8 °C. That gives the house's real "curve". Measure COP for each step: expect about +3 % per K saved.
2. **Prefer many moderate cycles at low flow over few cycles at high flow** (high). Field data show no measurable penalty from 10-15 starts/day with runs of 30 min or more [1][10]. The lab threshold for real harm is runs under about 6 min [12]. Practical rule: accept 6-15 starts/day in mild weather provided each run is at least 20-30 min. Do not raise the setpoint just to suppress cycling.
3. **Work with the restart hysteresis instead of fighting it** (medium). The unit restarts only once setpoint minus outlet is at least about 4 K. In mild weather, set the setpoint at the steady-state flow requirement (for example 29-30 °C at +10 °C). When idle, the outlet sensor decays towards slab return (about 25-26 °C), which triggers the restart naturally. Do not write setpoint = outlet + 4-5 to force a start, because that drives the leaving water hot. Test lowering `delta_heat_temp_set` from 4 to 2-3 K. That restarts the unit at a warmer slab and lower peak flow. Check that runs stay 20 min or more and starts stay at about 20/day or fewer. Evidence that this pays off: within-system, start count has about zero effect on COP when flow is constant [1].
4. **Let the slab do the modulation the inverter cannot** (medium-high). At +10 °C the load is 1.7 kW against a 3.7 kW minimum, so the duty cycle is about 46 %. With 6.6 kWh/K storage, a 1 h run at 3.7 kW (net +2 kWh) raises the slab only about 0.3 K. Equal on/off blocks of about 1-2 h each (about 6-12 starts/day) are fine. Keep the runtime fraction at or above about 0.3: mild days below that cost 6-8 % [1]. In practice that means not stretching off periods for many hours, then recovering hot.
5. **Do not "boost on PV" by raising water temperature substantially** (medium). A Swiss UFH simulation shows PV-driven overheating increases total consumption [22]. If PV surplus is used, prefer (a) DHW heating at moderate tank setpoints in the warm afternoon and (b) a small (+1-2 K) flow raise on a slab that would need heat anyway within hours. That trades cost, not efficiency. A few % lower COP on free PV energy can still be cheaper. Measure both.
6. **Fix DHW scheduling** (high). Days with DHW above 40 % of heat lose about 15 % [1]. Heat the tank once a day in the warmest hours (with PV), at the lowest acceptable temperature (about 45-48 °C). Use a reduced-compressor or "eco"-style DHW mode if the Versati offers one, and avoid DHW interrupting a space-heating run in cold weather. Keep the electric heater for weekly legionella only, and confirm it never runs after normal DHW cycles. RHPP's worst sites spent more than 20 % of electricity on immersion [10].
7. **Protect the cold tail** (high relevance, medium confidence). In the Lithuanian data, 31 % of annual electricity went on days below -16 °C at COP about 1 [1]. For this house, check whether the Versati's backup heater (if fitted) is enabled and at what outdoor and flow conditions it engages. At 0.17 kW/K, -20 °C needs about 7 kW, which a 9 kW Versati may or may not deliver after cold-climate derating and defrost. Pre-charge the slab by 0.5-1 K during the milder, drier hours before a cold snap rather than letting the backup cover. Never let the backup engage simply because a high setpoint cannot be reached (keep setpoints low in deep cold too).
8. **Expect defrost costs on humid -5..+5 °C days** (medium). That costs about 0.15-0.45 COP [7]. Avoid needless running in the coldest, most humid night hours when slab inertia allows shifting heat to the afternoon. Benefit: slightly higher air temperature, lower humidity, PV. Gains are probably a few %; measure them.
9. **A simple controller structure is enough** (medium). Top field systems use plain weather compensation with no or little room influence [1]. For this house, a weather-compensated base flow plus a slow room-temperature trim (±1-2 K, integral over hours, given the slab's time constant) is the field-proven shape. Field data do not show that elaborate predictive optimisers beat a well-tuned curve [33][34]. Vendor MPC claims are 5-23 % over typical untuned baselines [19][20][16].
10. **What to measure to know whether it works** (high): daily COP (heat-meter based if available), the day's mean leaving temperature, starts/day, run minutes per start, runtime fraction, DHW share and backup-heater kWh, binned by outdoor temperature as in Sections 4 and 9. Success: about 30 °C or lower mean flow at 0 °C outdoor, mild-day runtime fraction at or above 0.3, runs of at least 20 min, DHW share below 25 % on winter days, and zero backup kWh above -15 °C.

Overall confidence: high that flow temperature dominates and that moderate cycling is not the main loss. Medium on the exact hysteresis tweak (Versati firmware behaviour not verified here). Medium-low on cold-tail magnitudes (one Lithuanian system).

---

## Contradictions and open questions

- **Does cycling matter?** Lab tests (EA Tech) show clear losses for runs under about 6 min [12]. Forum anecdotes report large gains from stopping 5-10-minute cycling [29]. RHPP found no correlation [10], and my within-system analysis finds near-zero effect [1]. Resolution: the losses are concentrated in very short cycles. Most heatpumpmonitor systems (median 92 min/run) and this house (0.5-4 h) are far from that regime. Open: compressor wear per start is not captured by efficiency data.
- **Mild-day COP vs. starts goes the "wrong" way** within systems: more starts mean higher COP [1]. Likely confounders are that low-start mild days are DHW-dominated or run at low duty with fixed standby loads, and that high-start days run cooler water. Not causal in either direction.
- **The room-influence penalty is probably selection bias.** Pure weather compensation scores best on heatpumpmonitor [1], but Ecodan Auto-Adapt users report parity [31]. Owners who choose pure weather compensation may be the same ones who tune curves aggressively.
- **Start detection uses a 100 W threshold** on heatpumpmonitor [5]. Circulation-pump draw (about 180 W on some Daikins) can inflate counts, and compressor pauses shorter than 2 min may be missed (RHPP 2-min data [10]). Treat starts/day as approximate. One Vaillant validation was within 4 % [5].
- **Sizing:** EoH top-10 includes 2.4× oversized units at SPF 4.0 [9]. heatpumpmonitor shows the >2× group at -0.5 SPF [1]. Which minimum-output behaviour (degree-minute logic, minimum flow) makes oversizing harmless is model-specific [26].
- **The Lithuanian system's collapse below -16 °C** could be the metering boundary (internal backup on the same meter), undersizing (6 kW), or defrost. %-Carnot of 5-13 % strongly suggests resistance heat. Unknown whether the Versati 9 kW would see the same. Gree-specific field data at -20 °C are missing.
- **Gaps not covered because the search budget was exhausted:** Swiss FAWA long-term field results, Polish and Finnish monitoring programmes, the Danish Poulsen 2017 primary report (only the secondary summary in [16] was read), the Fraunhofer WPsmart and WP-QS full reports (19-MB PDFs; only the press release, project page and conference slides were read), and the EoH final report (only the 2023 interim was read).
- **Open for this house:** (a) the actual slab emitter capacity, i.e. the minimum flow that holds 22 °C at each outdoor band; (b) whether `delta_heat_temp_set` below 4 is accepted by the Versati and how its minimum run time and anti-short-cycle timers behave; (c) whether a backup heater exists and when it fires; (d) the Versati's DHW compressor-limit options.

---

## Sources

1. heatpumpmonitor.org public dataset: system metadata (system/list/public.json), annual stats (system/stats/last365) and daily stats (system/stats/daily?id=N, e.g. id=887, 251, 252, 193, 644, 938) - OpenEnergyMonitor / contributors - accessed 2026-11-06 - https://heatpumpmonitor.org/system/list/public.json ; https://heatpumpmonitor.org/system/stats/last365 ; https://heatpumpmonitor.org/system/stats/daily?id=887 - field data (my own statistical analysis) - quartile profiles, regressions, within-system fixed effects, cold-climate case studies.
2. HeatpumpMonitor.org home page - OpenEnergyMonitor - 2026 - https://heatpumpmonitor.org/ - field data portal - dataset size (669+ systems) and fields.
3. HeatpumpMonitor: low temperature / design flow guidance - OpenEnergyMonitor docs - 2024-25 - https://docs.openenergymonitor.org/heatpumpmonitor/low_temperature.html - field data analysis - SPF vs flow and vs flow-minus-outside regressions, coldest-day flow fit, top-system examples.
4. "HeatpumpMonitor.org SCOP annual vs design flow temperature" - T. Lea et al., OpenEnergyMonitor forum - 2024 - https://community.openenergymonitor.org/t/heatpumpmonitor-org-scop-annual-vs-design-flow-temperature/26653 - field data / forum - coldest-day flow about 7 K below design; %-Carnot vs lift R².
5. "HeatpumpMonitor.org starts & starts per hour" - OpenEnergyMonitor forum - 2024 - https://community.openenergymonitor.org/t/heatpumpmonitor-org-starts-starts-per-hour/26246 - forum / method - start detection threshold 100 W; 4 % validation vs Vaillant counter.
6. "HeatpumpMonitor.org findings" - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/heatpumpmonitor-org-findings/28164 - forum / field data - UFH and radiator SPF thresholds; COP vs compressor speed example.
7. "What SCOP can you expect from a system that runs at 55 °C and 50 °C..." - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/what-scop-can-you-expect-from-a-system-that-runs-at-55c-and-50c-flow-temperatures-on-the-coldest-days/29547 - field data / forum - SPF vs coldest-day flow fits; defrost about 1.6 % of heat, 0.35-0.45 COP in Scotland.
8. Electrification of Heat Demonstration Project: Interim Heat Pump Performance Data Analysis Report - Energy Systems Catapult for DESNZ - 2023 - https://es.catapult.org.uk/wp-content/uploads/2023/03/EoH-Interim-Heat-Pump-Performance-Data-Analysis-Report-1.pdf - field data - SPF H2/H4 medians and IQR vs RHPP, flow-temperature relationship, refrigerant split, HT units rarely above 65 °C, coldest-day COP.
9. "Electrification of Heat trial data" thread, page 5 - OpenEnergyMonitor forum - 2024-25 - https://community.openenergymonitor.org/t/electrification-of-heat-trial-data/27445?page=5 - field data reanalysis / forum - EoH top-10 / bottom-10 SPF, %-Carnot, oversizing factors.
10. Investigating variations in performance of heat pumps installed via the RHPP scheme - Love, Summerfield, Biddulph et al., RAPID-HPC for BEIS - 2017 - https://assets.publishing.service.gov.uk/media/5a81fa0e40f0b62305b91d1a/DECC_RHPP_160428_On_performance_variations_v20.pdf - field data - no single driver; 10-min cycling prevalence and no COP correlation; immersion share in poor sites; UFH flows.
11. Heat pump performance: effects of cycling (landing page) - DECC / GOV.UK - 2013 - https://www.gov.uk/government/publications/heat-pump-performance-effects-of-cycling - government summary - recommendation of cycle period > about 6 min.
12. The Effects of Cycling on Heat Pump Performance (Project 46640) - R. Green, EA Technology for DECC - 2012 - https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/65695/7389-effects-cycling-heat-pump-performance.pdf - lab (test house) - COP loss for 2-7 min runs, about 6 min threshold, GSHP worst case -16 %, buffer effects.
13. Press release "Wärmepumpen heizen auch im Altbau klimafreundlich" - Fraunhofer ISE - 2025-11-03 - https://www.ise.fraunhofer.de/content/dam/ise/de/documents/presseinformationen/2025/3025_ISE_PI_Waermepumpen-heizen-auch-im-Altbau-klimafreundlich.pdf - field data - 77 systems, ASHP JAZ 3.4 (2.6-4.9), heating rod 1.3 %, oversizing and high switching noted, combi-store temperature mixing, PV self-consumption figures.
14. WP-QS im Bestand project page - Fraunhofer ISE - 2025 - https://www.ise.fraunhofer.de/de/forschungsprojekte/wp-qs-im-bestand.html - field data - JAZ ranges, sizing-ratio figure description, final report link.
15. Effizienzanalyse von Wärmepumpen im EFH-Bestand auf Basis von Feldtestdaten (Chillventa 2020) - Günther, Wapler, Langner, Helmling, Miara, Fraunhofer ISE - 2020 - https://www.ise.fraunhofer.de/content/dam/ise/de/documents/publications/conference-paper/091_Fraunhofer-ISE_Chillventa-2020_1015_EFFIZIENZANALYSE%20VON%20W%C3%84RMEPUMPEN%20IM%20BESTAND.pdf - field data - JAZ correlates only with circuit temperature; heating curve over design point; heating rod only in faults or legionella.
16. Combined optimization of heat pumps and heat emitting systems (OPSYS main report) - S. Ø. Jensen et al., Danish Technological Institute - 2018 - https://www.teknologisk.dk/_/media/72043_OPSYS%20main%20report.pdf - lab rig + simulation + cites Danish field survey - 2-3 %/K; >160 Danish HPs, about 15 % perform as expected, up to 25 % savings; MPC up to 13 %.
17. Lette gulvvarmesystemer og deres indflydelse på varmepumpers effektivitet - Jensen, Paulsen, Olesen, Teknologisk Institut - 2014 - https://www.teknologisk.dk/_/media/69871%5FLette%20gulvarmesystemer%20og%20deres%20indflydelse%20p%E5%20varmepumpers%20effektivitet.pdf - engineering study / simulation - 2-3 % COP per K; 35 vs 45 °C floor means +20-30 % electricity.
18. Hur lågt kan vi gå? Optimerade lågtemperatursvärmesystem med bergvärme (SBUF 14234) - Arghand, Svensson, Bengt Dahlgren / PEAB - 2024 - https://vpp.sbuf.se/Public/Documents/ProjectDocuments/fb3440a8-b138-476a-8f61-344a27e2cf28/FinalReport/SBUF%2014234%20Slutrp%20Hur%20l%C3%A5gt%20kan%20vi%20g%C3%A5%20Optimerade%20l%C3%A5gtempsystem.pdf - simulation / LCC (Sweden) - GSHP 1-2 %/K, 15-20 % per 10 K.
19. Ngenic presentation (Energiforsk) - B. Berg, Ngenic - about 2023 - https://energiforsk.se/media/33868/7-bjo-rn-berg-ngenic.pdf - manufacturer claim (field before/after) - 50 homes, -21 to -23 % kWh.
20. PreHEAT for Heat Pumps by Neogrid (IEA HPT Annex 56 case) - Neogrid / DTI - about 2021 - https://www.dti.dk/_/media/87788%5F1%5F2%20IoT%20Annex%2056%20case%20DK%20%2D%20Neogrid.pdf - manufacturer claim - 5-15 % savings, more than 400 buildings, outdoor-sensor manipulation.
21. Teillastverhalten von invertergeregelten Wärmepumpen - Analyse des Carnot-Gütegrads im Feldbetrieb (student project, Prof. S. Bertsch) - T. Repke, OST - 2026 - https://www.ost.ch/files/daten/abstracts/pdf/990f3d2f-cae1-4a03-a95e-8e279b8902f2.pdf - field data analysis (BFE monitoring) - %-Carnot stable but collapses below unit-specific low part load.
22. Auslegung von drehzahlgeregelten Wärmepumpen für Netto-Nullenergiegebäude (MSc) - L. Rominger, OST/FHO - 2019 - https://www.ost.ch/fileadmin/dateiliste/97_daten/abstracts/475ab600-c293-4efd-82a2-f3e86b5a4aef.pdf - simulation - inverter up to +30 % COP; oversizing leads to cycling; PV-driven heating increases total consumption; return-temperature-based control best.
23. "Dank Wetterbericht Energie und Heizkosten sparen" - Hochschule Luzern - 2017 - https://www.hslu.ch/en/lucerne-university-of-applied-sciences-and-arts/about-us/media/medienmitteilungen/2017/10/25/dank-wetterbericht-energie-und-heizkosten-sparen - field demo (1 building) - forecast MPC, +20 % renewables in simulation, cost barrier.
24. Challenges of implementing economic model predictive control strategy for buildings interacting with smart energy systems - Zong, Böning, Santos, You, Hu, Han - 2016/17 (Applied Thermal Engineering 114) - https://backend.orbit.dtu.dk/ws/files/127571167/1_s2.0_S1359431116334871_main.pdf - paper (pilot) - EMPC beats PID; practical forecast and model issues.
25. "Heat pump demand cycling vs compressor load cycling" - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/heat-pump-demand-cycling-vs-compressor-load-cycling/29277 - forum - taxonomy of cycling; demand cycling is the costly one.
26. "HeatpumpMonitor.org heat pump database: minimum modulation tests" - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/heatpumpmonitor-org-heat-pump-database-minimum-modulation-tests/29132 - field data / forum - Arotherm 10/12 min about 5.9 kW, still top performer via degree-minute cycling.
27. "Weather compensation ASHP duty cycle" - OpenEnergyMonitor forum - 2023 - https://community.openenergymonitor.org/t/weather-compensation-ashp-duty-cycle/24793/4 - forum - duty-cycle 50-70 % practice; cycling at 6 °C is a sizing or emitter sign.
28. "Improve efficiency - turn the heat pump off?" page 3 - OpenEnergyMonitor forum - 2020-24 - https://community.openenergymonitor.org/t/improve-efficiency-turn-the-heat-pump-off/13381?page=3 - forum - no measured setback benefit; COP about 5 at 13 °C despite minimum-output cycling.
29. "How to reduce cycling" page 6 - OpenEnergyMonitor forum - 2024 - https://community.openenergymonitor.org/t/how-to-reduce-cycling/25251?page=6 - forum anecdote - 8 cycles/h at COP 2.5 changed to continuous low output at COP about 4.
30. "Vaillant energy integral - compr. start heat from" - OpenEnergyMonitor forum - 2024 - https://community.openenergymonitor.org/t/vaillant-energy-integral-compr-start-heat-from/26876 - forum - degree-minute logic (-60 start), 1 h on / 30 min off in UFH.
31. "Mitsubishi Ecodan performance using room Auto Adapt" - OpenEnergyMonitor forum - 2024 - https://community.openenergymonitor.org/t/mitsubishi-ecodan-performance-using-room-auto-adapt/25558 - forum - Auto-Adapt about the same as weather compensation; rolling SCOP 3.4 rose to 3.6.
32. "Experience with a 7kW Vaillant Arotherm" - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/experience-with-a-7kw-vaillant-arotherm/27714 - forum - COP about 2.1 at -2..-4 °C in a leaky house; 1.3 h cycles.
33. "Display optimisers in heatpumpmonitor.org" - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/display-optimisers-in-heatpumpmonitor-org/29013 - forum - no SCOP evidence for optimisers; Homely retrofits "not increased much".
34. "Experiences with Havenwise and other cloud-based control options" - OpenEnergyMonitor forum - 2025-26 - https://community.openenergymonitor.org/t/experiences-with-havenwise-and-other-cloud-based-control-options/29786 - forum - no numbers; one user found the optimiser caused full-power/idle behaviour.
35. "Beyond weather compensation (Daikin)" - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/beyond-weather-compensation-daikin/29152 - forum - Home Assistant ±1 K offset on a tuned curve; room-temperature mode caused more starts.
36. "Weather compensation or load compensation?" - Heat Geek - about 2024 - https://www.heatgeek.com/weather-compensation-or-load-compensation - installer blog - mechanism: room/load compensation needs hotter catch-up; recommends weather compensation with modest room influence.
37. "Vaillant Arotherm heat pump guide" - Energy Stats UK - 2025 - https://energy-stats.uk/vaillant-arotherm-heat-pump-guide/ - blog with field data - curve tuning method; DHW Eco mode above 3.8 DHW SCOP; 5 kW winter SCOP 4.0.
38. "Krzywa grzewcza - jak poprawnie ją ustawić" - Globenergia - about 2023 - https://globenergia.pl/krzywa-grzewcza-jak-poprawnie-ja-ustawic-typowe-problemy-i-ich-rozwiazania/ - trade magazine (Poland) - heating-curve tuning procedure, outdoor sensor sun bias.
39. "Błąd przy ogrzewaniu podłogowym a rachunki" - kb.pl - about 2024 - https://kb.pl/aktualnosci/ogrzewanie/blad-przy-ogrzewaniu-podlogowym-a-rachunki/ - trade article (Poland) - UFH flow 27-29 °C typical; COP 5.38 at 28 °C vs 4.40 at 35 °C.
