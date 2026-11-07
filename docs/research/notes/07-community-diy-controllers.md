# What DIY and Home Assistant owners do to optimise heat pumps

Researcher topic 07 of 15. Written 2026-11-06. Scope: Home Assistant (HA) community, OpenEnergyMonitor (OEM) forum and HeatpumpMonitor.org (HPM), Renewable Heating Hub (RHH), BuildHub, GitHub projects (HeishaMon, PumpSteer, TrueTemp/ClimateOptimizer, CompCurve, SAT, Octopus-Energy HA), Energy Stats UK, Heat Geek, plus Scandinavian, German, Polish, Dutch and Belgian material.

Method note. Forum before/after claims are mostly unmeasured, so the strongest evidence here is an analysis I ran on HeatpumpMonitor.org's public field data [1] (856 monitored systems, full-year and per-day statistics; method in section 1). Evidence ranking used throughout: measured field data > controlled lab test > peer-reviewed simulation > manufacturer claim > forum anecdote. The repository's own controller code and docs were deliberately not read.

Budget note. 24 web searches completed. Three more were refused because the session-wide search cap (shared by all agents) was hit. After that I read sources found by earlier searches and known project URLs directly. 55 sources were read in full or in part (including the HeatpumpMonitor.org data API), and 2 more are cited from search snippets only (marked "snippet only").

---

## Summary

- **Flow temperature matters far more than cycling.** Across 377 full-year, H4-boundary air-source systems on HeatpumpMonitor.org, COP falls by 0.083 for every 1 K of heat-weighted (flow − outdoor) temperature (R² 0.41). Adding starts per hour to the model only raises R² to 0.43, with a coefficient of −0.16 COP per extra start per hour. Efficiency relative to the ideal (Carnot) cycle shows essentially no link to starts across systems (Spearman −0.02) [1]. OpenEnergyMonitor's own regression gives −0.10 SPF per °C of weighted flow temperature (R² 0.52) [2].
- **Inside a single house, extra starts cost little, while extra flow temperature costs a lot.** Data: 66–67 underfloor-heating (UFH) systems with one zone and no buffer, 27,190 days. Each additional start per day costs 0.009–0.014 COP (about 0.2–0.35%). Each extra 1 K of space-heating flow temperature costs 0.07–0.15 COP (about 2–3%) and saves only 0.5–0.7 starts per day. **Raising water temperature to avoid on/off cycles therefore loses roughly 15–25 times more than it saves**, unless the runs are very short [1].
- **The cycling penalty only shows up when runs are short.** On mild days (6–15 °C outdoor), days whose average run was under 20 min sat 4.2% below the same system's median efficiency. 20–40 min runs: −2.5%. 40–60 min: −0.6%. Runs of 60 min or more: +0.3% to +1.9% [1]. This matches the 2012 DECC/EA Technology test-house finding on fixed-speed units: runs under about 6 min hurt performance, and systems should be designed for at least about 6 min [8], with runs of about 8 min approaching catalogue steady-state COP [33].
- **Good UFH benchmarks: low flow, long runs, a handful of starts.** Comparing the coolest-flow quarter of UFH systems with the warmest-flow quarter [1]:
  - 2–6 °C outdoor: 28.5 °C vs 35.5 °C flow, COP 4.62 vs 3.71.
  - 6–10 °C: 27.2 °C vs 33.9 °C, COP 5.66 vs 4.28.
  - −5 to 2 °C: 29.1 °C vs 38.0 °C, COP 3.50 vs 2.90.
  - The best systems run about 20–22 h/day near 0 °C. In mild weather they cycle about 7 times a day with 1–2 h runs.
  - This house's setpoints (31–36 °C, peaks 39 °C) sit in the *warmest* quarter.
- **Typical cycling among enthusiasts.** Median is 0.25 starts per hour (about 6 a day, IQR 4.0–8.4) with a 93-min average run. The 25 best systems: 0.23 starts/h, 102-min runs, 30.8 °C heat-weighted flow. The 25 worst: 0.44 starts/h, 52-min runs, 39.3 °C flow [1].
- **Room-thermostat on/off control is the classic failure mode.** It produces long off periods followed by hot catch-up runs:
  - Vaillant's "Expanded" mode cuts heating at +0.125 K above target. It held the unit off for about 4.5 h, then let the energy integral fall to about −180 °min, forcing a long catch-up run [26].
  - In the UK Electrification of Heat trial, a room-thermostat-driven system ramped to high flow temperature and then stopped for 1.5-hour periods [4].
  - On HPM, "significant room influence" systems have the lowest median COP (3.69, flow 37.2 °C, −0.20 below what their temperature lift predicts). Pure weather compensation has the highest (4.14, +0.10) [1].
- **Degree-minute (energy-integral) logic is how most brands and DIY owners manage unavoidable cycling.**
  - NIBE: start compressor configurable from −1000 to −30 degree-minutes (default −60 per owners). Higher values mean more starts; lower values risk uneven room temperatures [54, 52].
  - Vaillant: compressor start at −60 °min by default. Owners move it to −100 for fewer, longer cycles. They report COP is "barely affected" but room swings get larger [22, 23, 26].
  - Bosch/Nefit: 150 K·min hysteresis on split units [39].
  - Trystan Lea (OpenEnergyMonitor): well-controlled degree-minute cycling compensates well for a narrow modulation range [6].
- **Buffers, low-loss headers and multiple zones make things worse in the field data.** Buffer systems: 0.30 starts/h, 72-min runs, −0.22 COP versus lift-predicted. Low-loss header: 0.50 starts/h, 41-min runs, −0.25. Two or more zones: −0.27 [1]. Forum consensus: multiple thermostats and valves are a common cause of cycling [24], and smart TRVs on a Gree caused flow-switch errors [35].
- **Overnight setbacks did not clearly pay in owners' own measurements.** At the same outdoor temperature, COP during setback periods was 5.5–8.3% lower in one owner's regression [29]. A 6-hour setback day used only about 4% less input energy than a continuous day, in a confounded comparison [29]. A peer-reviewed analysis of HPM data links large setbacks to higher flow temperatures [4].
- **Most popular HA controllers have published no measured results.**
  - PumpSteer is a PI loop on a fake outdoor temperature (defaults Kp 2.4, Ki 0.035, output clamp ±12 K) [44].
  - TrueTemp learns a per-outdoor-temperature correction [45].
  - An HA blueprint shifts the curve +1 to +3 K under PV and −4 K in the evening [36].
  - Havenwise (commercial) users report "more even" temperatures, but also behaviour that was "full power or idling" [25].
- **Only one case study has measured numbers.** Volta (Flanders):
  - Retuning the heating curve dropped compressor input from about 2.7 kW to 1.7 kW (supply 26 °C instead of 33 °C), and daily use from 33 to 22 kWh on a freezing day.
  - Daytime-biased EMS control saved 476 kWh over Nov–Feb compared with the previous year (not weather-normalised).
  - The authors warn against chasing every quarter-hour price because it multiplies compressor starts [49].
- **Starting too hard is common.** Many firmwares sprint at start-up to reach the flow target.
  - Ecodan owners in HA feed a "fake" target so the start-up error stays below 11 K, which avoids 104 Hz starts [37].
  - Daikin owners raise "overshoot" from 1 K to 3–4 K and keep the minimum flow around 29–30 °C [15, 16].
  - HPM daily data: every extra 1 kW of average heat output costs 0.55–0.75 Carnot-percentage points (about 1.5% relative) on cold days, even at the same flow temperature [1].
- **Gree Versati community knowledge is thin.** HA users have mapped Modbus registers for the leaving-water setpoint (10), "ΔT heat" (30, range 2–10 K), power limit (word 43, 0–10 kW, default 3 kW), room-vs-water control source (coil 17) and weather-dependent mode (coil 22). Register maps differ between protocol versions. Nobody has published Versati cycling or COP results [35].
- **Confidence and transfer.** The core finding (lift beats cycling; avoid very short runs) is **high** confidence. Per-start and per-kelvin magnitudes are **medium** for this house: the HPM fleet is UK-maritime (mean outdoor 5–7 °C), enthusiast-biased, mostly Vaillant, and contains no Baltic air-source systems and only one Gree [1]. Gree-specific levers are **low to medium** until tested.

---

## Detailed findings

### 1. What measured field data says (my analysis of HeatpumpMonitor.org) [1]

**How I did it (reproducible).**
- **Data:**
  - `https://heatpumpmonitor.org/system/list/public.json`: 859 system records with metadata (make, model, nameplate kW, measured design heat loss, UFH flag, zones, hydraulic separation, control type, metering boundary).
  - `https://heatpumpmonitor.org/system/stats/last365`: per-system 365-day stats, including combined/space/water COP, flow temperatures, Carnot fraction, starts and starts per hour.
  - `https://heatpumpmonitor.org/system/stats/daily?id=N`: one CSV row per day with the same fields.
- **Filters:**
  - Air source only, no data flag.
  - Combined data covering at least 90% of the year.
  - Electricity, heat and flow-temperature data quality of at least 90%.
  - Combined COP between 1.5 and 7, and at least one start.
  - Result: 451 systems, 382 of them H4 boundary (COP comparisons use H4).
- **Derived metrics:**
  - Average run length = compressor running time ÷ starts.
  - HPM detects a start when electrical input crosses 100 W; starts per hour is over all hours, not running hours [7].
- **Daily within-system analysis:**
  - 113 UFH systems with at most one zone and no hydraulic separation. 67 had enough clean days: full day, data quality ≥95%, at least 3 kWh of space heat.
  - Efficiency was compared against each system's *own* days in the same outdoor-temperature band, using system fixed effects (demeaned regressions). Space-heating COP and space-heating % of Carnot are the outcomes.
- **Limitations:**
  - Annual starts-per-hour figures hide mild-weather bursts.
  - Days with many starts are often also low-load days, so the per-start cost below is an upper-bound mix of start losses and part-load/standby effects.
  - Daily starts include hot-water cycles.
  - The fleet is UK-dominated and enthusiast-run.

**1a. Cross-section (whole year, one point per system)**

| Quantity | Result |
|---|---|
| Starts/hour, all systems (n=451) | median 0.25, IQR 0.16–0.35 (≈6.0/day, IQR 4.0–8.4) |
| Mean run per start | median 93 min, IQR 59–144 |
| Combined COP (H4, n=382) | median 3.94, IQR 3.55–4.27 |
| COP vs heat-weighted (flow − outdoor) | −0.083 COP/K, R² 0.41 (n=377) |
| + starts/hour as second variable | −0.16 ± 0.05 COP per start/h; R² 0.43 |
| + ln(starts/hour) instead | −0.10 ± 0.03 per ln-unit; R² 0.43 |
| Spearman: %Carnot vs starts/h | −0.02 (no relation) |
| Spearman: COP vs starts/h | −0.14 |
| Spearman: COP vs (flow − outdoor) | −0.69 |

Quintiles of starts per hour (H4 systems):

| Quintile | starts/h (per day) | mean run | COP | %Carnot | flow−out | weighted flow |
|---|---|---|---|---|---|---|
| Q1 | 0.11 (2.6) | 227 min | 4.00 | 48.0 | 27.7 K | 35.0 °C |
| Q2 | 0.17 (4.1) | 147 min | 4.00 | 48.3 | 26.7 K | 34.5 °C |
| Q3 | 0.24 (5.9) | 98 min | 3.99 | 48.8 | 27.5 K | 34.4 °C |
| Q4 | 0.31 (7.4) | 81 min | 4.08 | 48.7 | 26.2 K | 33.8 °C |
| Q5 | 0.54 (12.9) | 41 min | 3.57 | 48.3 | 29.0 K | 36.1 °C |

COP left unexplained by temperature lift, grouped by starts per hour:

| Starts/hour | Systems | Median residual COP |
|---|---|---|
| 0–0.5 | 335 | +0.05 |
| 0.5–0.75 | 21 | −0.26 |
| 0.75–1.0 | 14 | −0.16 |

So COP only drops measurably once a system averages more than about 12 starts a day across the year (small n).

Other groupings (median COP; residual = COP minus what the system's temperature lift predicts):
- **Control type (H4):**

  | Control type | Systems | COP | Residual | Flow |
  |---|---|---|---|---|
  | Pure weather compensation | 151 | 4.14 | +0.10 | 34.3 °C |
  | WC + a little room influence | 71 | 3.84 | −0.01 | |
  | WC + simple set-point control | 27 | 3.79 | −0.01 | |
  | WC + significant room influence | 22 | 3.69 | −0.20 | 37.2 °C |
  | Room influence only (Auto Adapt etc.) | 7 | 3.84 | +0.14 | |
  | Custom controller | 6 | 3.85 | +0.10 | |
  | Manual flow control | 5 | 4.06 | +0.17 | |

  Median starts/h differ little between control types (0.18–0.31).
- **Hydraulic separation:**

  | Separation | COP | Residual | Starts/h | Mean run |
  |---|---|---|---|---|
  | None | 3.98 | +0.04 | 0.23 | 97 min |
  | Buffer | 3.59 | −0.22 | 0.30 | 72 min |
  | Low-loss header | 3.24 | −0.25 | 0.50 | 41 min |

- **Zones:** one zone 3.96 (+0.05) vs two or more zones 3.72 (−0.27, 0.32 starts/h).
- **Oversizing** (nameplate ÷ measured design heat loss): median ratio 1.48 (IQR 1.20–1.80). It barely predicts starts (Spearman 0.08) but does predict COP (Spearman −0.19). Ratio ≤1.2: COP 4.00. Ratio >2.5: COP 3.45.
- **Make** (shows how firmware strategy differs):
  - Viessmann: 0.15 starts/h, 200-min runs.
  - Grant: 0.12/h, 227 min.
  - Vaillant: 0.26/h, 94 min.
  - Daikin: 0.20/h, 112 min.
  - Mitsubishi: 0.33/h.
  - Panasonic: 0.37/h.
  - NIBE: 0.33/h.
  - Samsung: 0.56/h, 40 min, COP 3.53, residual −0.15.
- **UFH, single zone, no separation** (the closest analogue to this house, n=113): 0.22 starts/h; flow 33.6 °C (IQR 31.5–35.8); H4 COP 4.14 (IQR 3.82–4.52, n=106).
  - The top analogues reach COP 4.7–5.4 with heat-weighted flow of 26–31 °C and 0.17–0.31 starts/h. Most are Vaillant aroTHERM+ 5–10 kW on pure weather compensation; one Viessmann averages 0.04 starts/h with 737-min runs.

**1b. Within-system daily analysis (UFH single-zone, no buffer; 66–67 systems)**

| Outdoor band | Systems / days | Starts/day, median (IQR) | Space COP, median | Space flow | COP per extra start/day | COP per +1 K flow | Starts/day per +1 K flow |
|---|---|---|---|---|---|---|---|
| −5 to 2 °C | 44 / 1,422 | 2 (0–12) | 3.21 | 32.5 °C | −0.011 ± 0.001 | −0.069 | −0.17 ± 0.11 |
| 2 to 6 °C | 64 / 5,100 | 4 (1–9) | 4.04 | 31.6 °C | −0.014 ± 0.001 | −0.106 | −0.54 ± 0.05 |
| 6 to 10 °C | 66 / 9,223 | 7 (3–12) | 5.02 | 30.1 °C | −0.009 ± 0.001 | −0.136 | −0.67 ± 0.04 |
| 10 to 15 °C | 67 / 9,149 | 6 (3–11) | 5.67 | 29.0 °C | −0.010 ± 0.001 | −0.146 | −0.63 ± 0.03 |

The per-start and per-kelvin coefficients come from fixed-effects regressions controlling for outdoor temperature. The COP-per-start regression also controls for flow temperature.

Carnot-relative efficiency by starts per day, versus the same system's median in that band:

| Starts/day | −5 to 2 °C | 2 to 6 °C | 6 to 10 °C | 10 to 15 °C |
|---|---|---|---|---|
| 0–3 | +0.1% | +0.2% | +0.9% | +0.7% |
| 4–7 | +1.7% | +0.6% | +0.3% | 0.0% |
| 8–11 | +3.1% | +0.2% | −0.6% | −0.4% |
| 12–17 | +1.4% | −1.0% | −0.7% | −0.2% |
| 18–29 | −3.5% | −2.8% | −0.8% | +0.5% |
| ≥30 | −3.6% | −3.1% | −1.9% | −9.5% |

Interpretation: up to about 12–17 starts a day there is no detectable efficiency penalty. From about 18 a day there is a 3–4% penalty in cold bands. At 30 or more a day it reaches 2–10%.

Average run length (6–15 °C days), versus the system's own median %Carnot:

| Mean run | Days | vs own median |
|---|---|---|
| < 20 min | 1,188 | −4.2% |
| 20–40 min | 3,425 | −2.5% |
| 40–60 min | 3,066 | −0.6% |
| 60–90 min | 3,085 | +0.3% |
| 90–150 min | 2,910 | +0.8% |
| > 150 min | 4,108 | +1.9% |

Other within-system results:
- **Cost of running hard** (catch-up runs): each extra 1 kW of average heat output while running changes Carnot efficiency, at the same outdoor temperature, by:
  - −0.55 ± 0.18 percentage points at −5 to 2 °C,
  - −0.75 ± 0.07 at 2–6 °C,
  - −0.18 ± 0.06 at 6–10 °C,
  - +0.38 ± 0.06 at 10–15 °C.

  This is on top of the flow-temperature penalty, which %Carnot already accounts for. At mild temperatures, running harder is neutral-to-positive because it means fewer, longer runs.
- **Low-load days** (3–15 kWh/day of space heat) run at 46.2% of Carnot, versus 49.0–50.7% on days above 15 kWh/day. Cycling, standby and part-load losses concentrate at very low loads.
- **Best vs worst flow quarter, by weather band:**

  | Outdoor | Coolest-flow quarter | Warmest-flow quarter |
  |---|---|---|
  | −5 to 2 °C | 29.1 °C, COP 3.50, 1 start/d, 21.7 h/d | 38.0 °C, COP 2.90, 1 start/d, 21.3 h/d |
  | 2 to 6 °C | 28.5 °C, COP 4.62, 4 starts/d, 19.5 h/d | 35.5 °C, COP 3.71, 6 starts/d, 17.6 h/d |
  | 6 to 10 °C | 27.2 °C, COP 5.66, 7 starts/d, 13.9 h/d | 33.9 °C, COP 4.28, 6 starts/d, 10.6 h/d |
  | 10 to 15 °C | 26.5 °C, COP 6.41, 7 starts/d, 7.0 h/d | 31.7 °C, COP 5.06, 4 starts/d, 5.5 h/d |

- **Day-to-day noise, for planning A/B tests:** within a system, daily space COP varies by about 9.9% (SD) after fitting outdoor temperature, and daily %Carnot by about 6.4%. Detecting a 5% improvement in %Carnot therefore needs about 26 days per test arm (α 0.05, power 0.8). A 10% improvement needs about 7 days.

### 2. Temperature lift beats cycling — community consensus and its documented basis

- **OpenEnergyMonitor's HPM analysis** [2]:
  - Strongest single predictor of SPF (H4): heat-output-weighted (flow − outdoor), R² 0.547; SPF = −0.1054 × ΔT + 6.876 (±0.53 PI). 25 K → 4.24; 30 K → 3.71; 35 K → 3.19.
  - Weighted flow alone: −0.10 SPF per °C (R² 0.515). 30 °C → 4.4; 35 °C → 3.9; 40 °C → 3.4.
  - Coldest-day flow for SPF 4.0: 36.6 ± 5.5 °C.
  - Example coldest days: Viessmann 10 kW, SPF 5.0, averaging 33 °C flow at −3.2 °C outdoor; Vaillant 10 kW, SPF 4.8, at 33 °C.
- **Peer-reviewed version** (Rosenow, Lea & Boni 2026, *Energy and Buildings* 352:116785, via CIBSE Journal) [4]:
  - HPM fleet SPF 3.86 vs 2.81 in the UK Electrification of Heat trial and 2.36 in RHPP.
  - 55% of 165 inspected EoH Vaillant systems had weather-compensation settings that were too high.
  - Room-thermostat-driven cycling and large setbacks are named as drivers of high flow temperatures.
  - A dynamic simulation found that fixing the curve, allowing modulation and starting the schedule earlier (01:45 instead of 05:00) raised COP from 2.86 to 4.61 and cut 6 am demand from 5.1 to 1.2 kW.
- **Annual SCOP vs design flow temperature** [5]:
  - Systems ran on average about 7 K below their design flow temperature on the coldest day.
  - Carnot fraction (R² 0.54 vs SCOP) and system temperatures (R² 0.5) were only weakly correlated with each other, so "about half is temperatures, half is everything else".
  - Lea's rule of thumb: about 50% of Carnot practical efficiency and about 40% minimum modulation set how low flow can go in mild weather, *for systems without sophisticated mild-weather cycling control*.
- **What DIY owners say**:
  - Heat Geek's long-standing argument: weather compensation is gentler on the machine and causes less cycling than load (room) compensation. Room influence should be a tuneable trim, reduced in larger houses [28].
  - Energy Stats UK (Vaillant): Active room modulation ran 2.2–3.0 K cooler than Inactive when the room was above target. With curve 0.6 the flow was 26 °C at 15 °C outdoor, 31 at 10, 35 at 5, 38 at 0 and 40 at −3 [26].
  - Volta case study: retuning the curve on a freezing day lowered supply from 33 to 26 °C, compressor input from about 2.7 to 1.7 kW, and daily use from 33 to 22 kWh, while also avoiding a 2 kW backup heater [49].
- **Very low flow can work on a slab.** An OEM owner with Vaillant, a 125 mm slab and 100 mm pipe centres ran about 25 °C flow at 7 °C outdoor with COP above 6 (sub-metered; sensor accuracy not verified) [23]. HPM case-study systems hold 31–33 °C on their coldest days [2].

### 3. How much does cycling actually cost?

- **Lab, fixed-speed units (DECC/EA Technology 2012)** [8]:
  - Test house with fixed-speed air- and ground-source units.
  - Runs under about 6 min degraded performance, more so for air source.
  - Recommendation: design for runs of more than about 6 min under all conditions.
  - Buffer tanks generally improved performance in conditions that would otherwise have short-cycled.
  - Forum readers of the report cite runs of about 8 min as giving COP close to catalogue steady state, and note its controls and COPs are dated [33].
- **Theory (Qiao & Laughman, MERL/ICR 2023)** [9]:
  - In first-principles simulations, cycling losses come mainly from refrigerant migration during the off period and slow capacity rise after start.
  - Preventing migration cut losses by more than 95%.
  - A regenerative accumulator cut capacity rise time by more than 75%, giving about 60% lower cycling losses.
  - Implication: modern inverter units with good start logic should lose much less per start than 2012-era units. That is consistent with section 1's small per-start coefficients.
- **Field data (section 1)** [1]: about 0.2–0.35% of COP per extra daily start. Runs under 20 min are about 4% worse than the system's median; runs under 40 min about 2.5% worse. No detectable penalty with runs of 60 min or more.
- **Forum anecdotes with numbers** (low confidence: single systems, rarely weather-matched):
  - Madsen68 went from 150+ starts per 24 h (8 cycles/h, COP about 2.5) to near-continuous running at 600–900 W, COP about 4 [12].
  - MyForest (David Bowen) measured space-heating COP at 9 °C average outdoor: 2.58 with the unit "always on", flipping between heating and anti-freeze circulation, vs 3.32 with his own on/off algorithm. His algorithm used a minimum run time at target flow and restarted when the return water fell to about 26 °C [11].
  - Timbones (Ecodan): steady running needed 37 °C flow, while cycling 40 min on / 20 min off allowed 33 °C flow [11].
  - Heat Geek's mild-weather comparison: each Samsung start produced a power spike that "destroys" COP. Other brands also showed short start spikes [31].
  - Owner reports on start-up: an Ecodan raised flow above setpoint, ran 6–8 min and shut down [32]; Daikin cycles start at maximum flow for about 20 min [15].
- **What counts as "acceptable"**:
  - Timbones (OEM): 2–3 cycles per hour in mild weather is normal [19], and manufacturers deem up to 3 per hour acceptable [24].
  - Others cite fewer than 6 per hour.
  - The HPM median is about 0.25 per hour averaged over a year [1].
  - NIBE owners quote 4,000–10,000 starts per year as normal (second-hand) [52].
  - No source quantifies compressor wear per start for modern inverter scroll/rotary compressors.

### 4. Degree-minute / energy-integral control — the workhorse for unavoidable cycling

- **NIBE** [54, 52]:
  - Degree minutes (DM) measure current heating demand and decide when the compressor and auxiliary heat start and stop. In practice DM accumulates (actual flow − calculated flow) × minutes.
  - The compressor starts at a configurable negative value (range −1000 to −30 DM; −60 is the commonly quoted default) and stops when DM climbs back to 0 [52]. "Current value" can range from −3000 to +100 DM.
  - Manual trade-off: a higher (less negative) start value gives more starts and more wear; too low a value gives uneven indoor temperatures [54].
  - Auxiliary heat has its own relative DM threshold (100–2000 DM) [54].
  - A Norwegian owner reports far fewer starts after moving to −240; Swedish owners advise lowering (more negative) values for longer autumn/spring runs (snippet only) [57].
- **Vaillant aroTHERM**:
  - Energy integral: start at −60 °min by default, stop at 0 [26]. The manual allows −999 to +9 °min (snippet only) [56].
  - The heating "compressor hysteresis" (default 7 K, range 0–15 K) is secondary; the energy integral governs cycling [22, 56].
  - Owner advice: −100 °min gives fewer, longer cycles with stronger room swings, and "COP is barely affected". −30 gives shorter cycles and, in one owner's impression, worse COP. For the longest cycles combine −100 with 10 K hysteresis [22].
  - Mick Wall (Energy Stats UK): about 7 °C outdoor is roughly where well-designed systems start cycling [23].
  - Firmware 351.06.07 double-counted the energy integral and caused extra cycling; fixed in 351.09.01/.02 [26, 27].
  - One owner sat at −146 °min with no restart. Another owner recalled a similar fault caused by a pump-speed setting left at "lowest" instead of Auto [22].
- **Bosch/Nefit** [39]: on/off hysteresis expressed in K·min — adjustable on split units (default 150 K·min), roughly 200 to start / 250 to stop on monoblocs (not adjustable). The value cannot be read over the EMS bus, so an HA user rebuilt it with template and integration sensors to predict on/off timing.
- **Lea's view** [6]: well-controlled degree-minute cycling compensates very well for a narrow modulation range. Example: Vaillant 10 kW modulates only about 5.9–9.6 kW, yet performs well when the house's heat loss is near the minimum.
- **Why this matters for a plain ΔT-restart machine.** A degree-minute controller restarts when the *accumulated* heat deficit is large enough. A ΔT-hysteresis restart (restart when the water has cooled ΔT below setpoint) fires on *local water cooling* instead. That depends on pipe losses, circulation and sensor placement, not on house demand. NIBE owners stress that the external supply sensor and circulation past it are critical for degree-minute logic [52].

### 5. Room feedback: useful as a slow trim, harmful as on/off

- **Vaillant modes** (Energy Stats UK) [26]:
  - **Inactive**: pure weather compensation.
  - **Active**: weather compensation plus small (about 1–2 K) room nudges. Recommended for most homes.
  - **Expanded**: thermostat on/off at +0.125 K / −0.1875 K. Measured examples: off over an hour until the room fell from 20.2 to 19.8 °C; off from 21:09 to 02:30 overnight with the room falling from 20.2 to 18.4 °C. On restart, the integral can sit at about −180, forcing a long catch-up run.
  - The sensoCOMFORT read about 0.3 K higher than three other sensors in the same room.
- **Daikin Madoka "modulation"** [17]: drops the flow target by 3 K at +0.5 K room error and another 3 K at +1.0 K, and switches off at +1.5 K. Owners find the roughly 2 K start/stop swing too wide. Chris Hill uses pure weather compensation plus ±1 K leaving-water offsets from HA only for events WC can't see (guests, sun, wind); room-thermostat modulation gave "too many starts and stops" [14].
  - A respondent's "WC + load compensation + PID" controller reports average room error below 0.4 °C [14].
  - Another owner prefers averaging several room sensors [14].
- **Ecodan Auto Adapt (room-model mode)** [20]:
  - Owners report Auto Adapt cycles less than WC but often runs hotter. Example: WC at night gave COP 3.16 with about 3 cycles/h.
  - Timbones calculated that one circuit cannot run smoothly below 43 °C, because the radiators emit only about 2 kW at 35 °C while the unit's minimum output is 3.7 kW.
  - Evidence is anecdotal and contradictory, and Ecodan's built-in meters are considered unreliable [20].
- **HPM grouping** [1]: significant room influence → lowest median COP (3.69) and highest flow (37.2 °C). Auto Adapt (n=7) and custom controllers (n=6) are positive but tiny samples.
- **HA generic_thermostat as heat-pump on/off** [55]: its `min_cycle_duration`/minimum run time is not enforced in time. It reacts to sensor events, so setpoint changes end cycles early. A time-based fix was accepted as PR #136298 but not yet released at the time of the thread.

### 6. Anti-short-cycling and "flow ramping" hacks people actually run

- **HeishaMon "Compressor-Short-Cycle-Guard"** (Panasonic; runs on the device) [43]:
  - When the compressor stops (no defrost, outdoor ≥2 °C), it writes a −5 K heat-curve offset for 45 min, then restores 0.
  - Below 2 °C it releases early: cold weather takes priority over cycle reduction.
  - No measured results.
  - HeishaMon's README warns that settings may be written to EEPROM with limited write life, so send only a few commands per hour per setting, and re-send dropped commands after about 10 s [42].
- **Ecodan "anti-panic starts" (HA, FTC6)** [37]: a template sensor reports a fake target temperature so the start-up delta stays below 11 K, which stops the compressor sprinting to 104 Hz. Restart-safe triggers use 5-min delays. A watchdog writes the Modbus target *before* toggling a relay to avoid the FTC's roughly 3-min autonomous routines. Owner reports smooth modulation; no numbers.
- **Daikin overshoot and minimum flow** [15, 16]:
  - Raising "overshoot" [9-04] from 1 K to 3–4 K stopped short-cycling for several owners.
  - Owners keep the lowest leaving-water temperature at about 29–30 °C because few Altherma units sustain under 29 °C.
  - Lower the curve when raising overshoot to keep total heat the same.
  - Changing emitter type to UFH / ΔT to 5 K with 4 K overshoot "settled" one system (qualitative).
- **Run-time and start blocking around tariff slots** [41]: block starts within about 10 min of an Agile price-slot boundary to avoid very short runs. Volta warns that an EMS following 15-min prices must enforce minimum run times [49].
- **Flow rate / ΔT:** Heat Geek argues mild-weather ΔT is often far too low (1.6 K at 34 l/min) and suggests flow rates giving about 8 K at peak load [31]. Daikin owners went the other way (smaller emitter ΔT) to lengthen runs [15]. Contradiction — see the Contradictions section.
- **System volume:** OEM's simulator uses minimum volume = minimum output × minimum on-time ÷ (c_p × ΔT), with typical ΔT 5–10 K [10]. Example: 3.7 kW × 10 min ÷ (4.19 kJ/kg·K × 5 K) ≈ 106 l. A concrete slab is many times this, which is why slab UFH systems run long cycles without buffers [1, 32].

### 7. Setbacks, "low and slow", scheduling and tariffs

- **Measured owner comparisons:**
  - **cathodeRay (Midea 14 kW)** [29]:
    - 6-h overnight setback day vs continuous day at about 10 °C outdoor: input energy 20.38 vs 21.22 kWh (−4%). But the setback day was 1.5 K cooler indoors, ran a hotter curve (LWT 39–41 vs 37–38 °C, throttled lockshields), and had COP 3.9 vs 5.1. Not like-for-like.
    - Later regression at the same outdoor temperature: setback-period COP 5.5% lower at 8 °C and 8.3% lower at 12 °C.
    - Reheat after a 4.12 kWh deficit needed about 0.49 kWh *more* input than continuous running would have (RobS's estimate: COP 3.54 vs 5.21).
    - JamesPa's explanation: in mild weather the unit already cycles, so a setback removes the off-time slack and forces a higher flow temperature.
  - **Night-setback trials** [30]: SUNandAIR ran 50+ trial days with a low-mass Ecodan; cathodeRay switched off 21:00–03:00. They report lower energy at similar mean outdoor temperature on setback days, but no percentage. Defrost-heavy reheats (outdoor 6 → 2 °C) dropped COP from about 4 to about 2.
- **Light, warm-hour-biased scheduling:**
  - Octopus-Daikin owners found a −2 K overnight leaving-water offset worked [17].
  - The peer-reviewed analysis recommends keeping rooms in a narrow band (e.g., 18–20 °C) instead of large setbacks [4].
- **Energy-budget control** (BuildHub, JohnMo, HA) [50]:
  - Sets a rolling 24-h heat-energy target, spends about 8 h' worth in the cheap Cosy window down to about 5 °C outdoor, carries any shortfall forward, and falls back to thermostat + WC on failure.
  - A companion helper predicts room temperature 1 h and 4 h ahead to handle screed inertia.
  - No measured outcomes yet.
- **Daytime / PV-biased EMS (Volta, Flanders)** [49]:
  - Running space heating in daylight and stopping at sunset saved 476 kWh over Nov–Feb year-on-year (not weather-normalised).
  - Lower compressor power raises PV coverage: at 2 kW PV, the original curve still imported 700 W while the optimised curve left 300 W spare.
  - A 1 kW lower compressor draw plus avoiding the 2 kW backup cut the monthly capacity-tariff peak by 3 kW.
- **Price-following controllers** [44, 45, 36]:
  - PumpSteer brakes by raising the fake outdoor temperature by up to 10 K in expensive (P80+) periods. It preheats by up to 4 K within a 6-h look-ahead, bridges gaps under 30 min, and allows comfort drops of 0–3 K depending on saving level.
  - TrueTemp moves heating away from the most expensive hours.
  - The HA blueprint applies +1 to +3 K at noon under PV and −4 K in the evening when consumption exceeds PV.
  - None publish measured results.
- **Commercial optimisers** [25]: Havenwise owners report more even comfort and "no vast saving" where Vaillant's native controls were already good. One found it too aggressive (full power or idle) and badly timed hot water. An Ecodan ESPHome developer's "Odin" optimiser is in beta with planned-vs-actual buffering charts and no efficiency data [40]. Vaillant claims "up to 15%" for its cloud optimisation (manufacturer claim, second-hand) [53].

### 8. Hot water and PV coupling (as practised by owners)

- Ecodan PV boost: raise DHW to 55 °C only between 10:00 and 14:00 when PV ≥3.5 kW and battery ≥60%, aborting below 50% (10% hysteresis) [37].
- mjr (Ecodan, Pi): heat the tank a bit hotter on warm late afternoons to avoid an evening reheat. After a tank cycle, run space heating for about an hour unless the house is already warm. Temporarily drop the target 3 K when overheating to avoid frequent cycling [34].
- Vaillant DHW modes: "Eco" caps the compressor at about 50% (DHW SCOP often above 3.8 but slow); "Sweet Spot" caps at about 80 rps [27]. The same capping idea applied to space heating is what a power-limit register enables.
- Octopus-Daikin owner: switched off the unit's legionella cycle and triggers "powerful" mode manually without the resistive heater [17].
- TerryE (BuildHub): heats DHW with the heat pump at a fixed low flow of about 35 °C, and runs legionella cycles on the immersion when the Agile price goes negative [50].

### 9. Monitoring practices that made the difference

- **Meter heat and electricity, then compute daily COP, starts, mean run length and run-weighted flow temperature** (the HPM model) [1, 7]:
  - HPM counts a start when input crosses 100 W.
  - A Daikin whose circulation pump alone draws about 180 W gave false starts, so that site uses 111 W [7].
- **Normalise for weather with % of Carnot.** It separates "temperatures" from "everything else" and correlates with SCOP at R² 0.54 [5].
- **Check sensors**: compare flow and return readings with the compressor off and pumps running [24]. Ecodan's built-in energy figures are considered unreliable [20]. A sensoCOMFORT read 0.3 K high [26]. Martin Harizanov now graphs flow rate after a post-service fault went unnoticed for a year [48].
- **Case data from Harizanov's blog** [48]: an oversized 11 kW Ecodan (minimum 4.3–5 kW) made about 6,500 starts in 8,345 running hours (77% of running hours included a stop-start, mostly at 0–10 °C). Seasonal heating COP 3.14 (January 2.75), DHW COP 2.0–2.4.

### 10. Failure-mode catalogue (what DIY owners repeatedly report)

1. **On/off room-thermostat control layered on WC** causes catch-up runs at high flow and high compressor speed, then long off-times [26, 4, 14, 1].
2. **Multiple zones, TRVs, actuators and smart heads** shrink the active emitter area, raise flow temperatures and increase cycling. On a Gree, closing smart heads tripped the flow switch [24, 35, 16].
3. **Oversizing relative to mild-weather load** (minimum output > load): unavoidable cycling, and a COP penalty in the data for ratios above 2.5× [1, 48, 17].
4. **Hydraulic separation** (buffer, low-loss header) or an open automatic bypass valve, which in one case starved the loop [1, 17, 33].
5. **Hunting setpoints**: frequent writes "move the goalposts" and the unit keeps re-targeting [16]. Write wear on EEPROM-backed settings [42].
6. **Aggressive start-up ramp** (firmware sprint to reach target), and power spikes at each start [31, 37, 15].
7. **Sensor placement and calibration**: controller on a landing reacts late [34]; room sensor 0.3 K off [26]; degree-minute logic depends on circulation past the supply sensor [52].
8. **Protocol and register drift**: Gree has at least 5–6 Modbus protocol variants with different maps, and one setup had an off-by-one address [35].
9. **Firmware bugs** in cycling logic (Vaillant energy-integral double counting) [26, 27].
10. **DHW interference**: tank cycles at high flow temperature interrupting space heating. Mitigations: schedule DHW in warm/PV hours and follow it with a planned heating run if needed [34, 37].

---

## What this means for controlling this house

The house: slab UFH (about 6.6 kWh/K storage), heat loss 0.14–0.20 kW/K, 9 kW Gree Versati with a compressor minimum of about 3.7–3.8 kW heat, 22.0 °C target, flow setpoint written over Modbus every ~30 min, and a unit that restarts only when setpoint − outlet ≥ about 4 K.

**A. The physics of this house** (my own arithmetic from the stated parameters, not from a source)
- **Mild-weather balance point.** Load equals minimum output when 22 − T_out = 3.7 / H. That gives T_out ≈ −4.4 °C (H = 0.14), +0.2 °C (H = 0.17) or +3.5 °C (H = 0.20), before free gains. Gains shift these 1–3 K lower.
- So the Versati *must* cycle on most heating-season days. Cycling is the normal regime here, not an edge case, and it should be **designed**, not fought.
- **Duty at minimum output:** about 46% at +10 °C (1.7 / 3.7 kW, about 11 h/day of running) and about 78% at +5 °C (H 0.17). Near 0 °C it can run almost continuously at minimum output.
- **Slab buffer:**
  - At +10 °C the surplus is 3.7 − 1.7 = 2.0 kW, so the slab gains about 0.3 K/h. A 2-h run stores about 4 kWh (≈0.6 K) and then supplies the house for about 2.3 h. That is roughly 5–6 starts a day with 2-h runs.
  - At +5 °C, a 4-h run gains about 0.5 K and coasts about 1.1 h, so roughly 4–5 starts a day.
  - Both regimes sit where the HPM data shows **no measurable cycling penalty** (runs ≥60 min, fewer than 12 starts/day) [1].
- **Catch-up runs are the expensive behaviour.** Drawing about 3 kW at +2 °C means the unit is producing about 2–2.5× its minimum output, at a flow temperature high enough to push that heat into the slab. At +2 °C the house needs only about 3.4 kW (H 0.17), so it could run almost continuously at minimum output and low flow.
  - Field data says a hot catch-up costs on two counts: about 2–3% per extra kelvin of flow [1, 2], plus about 1.5% per extra kW of output at the same flow on cold days [1].

**B. Concrete rules the community evidence supports** (each testable; confidence in brackets)

1. **Make low flow temperature the primary objective and accept cycling** *(high)*.
   - Target the run-weighted outlet temperature, not the number of starts.
   - Benchmarks from the best UFH systems: about 29 °C at −5 to 2 °C outdoor, about 28.5 °C at 2–6 °C, about 27 °C at 6–10 °C, about 26.5 °C at 10–15 °C [1].
   - Today's 31–36 °C setpoints (39 °C peaks) are in the worst quarter of that fleet.
   - Expected value: 0.07–0.15 COP per kelvin removed (2–3% per K) [1, 2].
   - Test: lower the curve or flow target in 1 K steps every 2–3 days until the room can't hold 22.0 °C on the coldest day of the step, then go back one step (the Energy Stats UK method [27]).
2. **Do not raise water temperature to reduce starts** *(high)*. Within a system, +1 K of flow saves only 0.5–0.7 starts a day but costs 15–25× more in COP than those starts [1]. The community "raise minimum LWT to 30 °C" fix [15, 16] is only rational where runs are under about 10–20 min.
3. **Enforce a minimum run of about 60 min (hard floor about 30 min) and a soft cap of about 8–12 space-heating starts a day in mild weather** *(medium)*. Runs under 20 min cost about 4% and 20–40 min about 2.5%; at 60 min or more there is no penalty [1]. The 6-min DECC floor is a fixed-speed-era minimum, not a target [8]. Count starts with an input-power threshold just above pump standby (~100 W, checked against the Versati's own idle draw) [7].
4. **Replace "restart by setting the setpoint ≥ outlet + 4 K" with a demand-integral (degree-minute) trigger in HA** *(medium)*.
   - Accumulate either (WC-target flow − actual flow) × minutes, as NIBE does [54, 52], or, better for a slab, a heat-energy deficit: estimated demand from H × (22 − T_out) minus gains minus heat delivered.
   - Start a run when the deficit reaches about 3–6 kWh (≈0.5–0.9 K of slab, ≈1–1.5 h at minimum output). End it when the planned energy is delivered or the slab or room target is met.
   - Tune the threshold like Vaillant owners tune −60 → −100 °min: a deeper threshold means fewer, longer runs and larger room swings [22]. With a 6.6 kWh/K slab those swings should stay small.
   - This also replaces the Gree's ΔT restart, which reacts to local water cooling, not house demand.
5. **Start gently: "ride" the outlet instead of opening a 4–5 K gap** *(medium-low; inferred from Ecodan/Daikin practice [37, 15])*.
   - Once a run starts, rewrite the setpoint to about outlet + 1–2 K every few minutes as the slab warms. A small error keeps the inverter near minimum frequency; a 4–5 K gap invites a sprint.
   - To end a run, park the setpoint low (e.g., the unit's minimum, 20 °C [35]).
   - This needs writes every 2–5 min during runs instead of every 30 min. Find out whether Gree setpoint writes are volatile or EEPROM-backed before doing this [42].
6. **Cap compressor power instead of letting catch-up runs draw about 3 kW** *(medium-low; register semantics unverified)*.
   - HA users report a Versati power-limit register (word 43, 0–10 kW, default 3 kW, 0.1 kW steps) used for PV-surplus following [35].
   - Test a cap of about 1.3–1.6 kW electrical whenever outdoor temperature is above about −5 °C, and release it in cold snaps.
   - Expected effect: lower compressor speed and lower flow per run. Watch compressor frequency (read registers 142/143 in one map) and input power to confirm the cap acts on the compressor in heating mode.
7. **Check ΔT heat ("delta_heat_temp_set") after HA owns the start decision** *(low-medium)*. With HA parking the setpoint below the outlet during planned off periods, a smaller restart ΔT (2–3 K; register 30 in one map, range 2–10 K [35]) lets HA start runs at lower setpoints, i.e., lower flow. With today's passive 30-min writes, a smaller ΔT would simply add autonomous restarts, so change it only together with rule 4.
8. **Room feedback only as a slow trim** *(high for "not on/off"; medium for the gains)*.
   - Use pure weather compensation (or a heat-loss model) as the base. The HPM median-COP leader is "pure WC" [1].
   - Add a room-error correction of about ±1 K, rate-limited and with an hours-long integral time, because a slab responds over hours [14, 26, 44].
   - Use a deadband of about ±0.2–0.3 K around 22.0 °C, and average two or more room sensors [14].
   - Never let room overshoot cut the unit off and then demand a catch-up; that is the Vaillant-Expanded failure (−180 °min catch-up) [26] and matches what this house shows.
9. **Move the energy, don't take it away: no deep setbacks** *(medium-high)*. Owner data shows setback recovery at 5.5–8% lower COP and at best marginal net savings [29, 30], and the peer-reviewed analysis advises narrow bands [4]. With a 6.6 kWh/K slab, shift *when* the planned daily energy is delivered (warmest hours, PV hours) rather than letting the slab cool [49, 50].
10. **Schedule runs in the warmest / PV hours of mild days, but never chop runs for price** *(medium)*. Volta: daytime-biased control saved 476 kWh over a winter (not normalised) and raised PV self-use [49]. Keep a minimum run length and block starts just before tariff or PV transitions [41, 49]. The 15 kW PV and battery make the "energy budget per day, delivered in 1–3 long low-flow blocks" pattern [50] natural for this house in autumn and spring.
11. **Decouple DHW from space heating** *(medium)*. Run DHW in the warmest or PV hours, separate from space-heating runs. Cap DHW compressor speed where the unit allows (the equivalent of Vaillant "Eco" [27]). Use the electric heater for legionella only on PV surplus [50]. Don't let a DHW cycle trigger a hot space-heating restart [34].
12. **Don't add a buffer tank or low-loss header** *(high)*: buffer and low-loss-header systems are worse in COP and starts [1]. The slab is the buffer [32].
13. **Measure before believing** *(high)*. Log daily space-heating COP from a heat meter, starts, mean run length, run-weighted flow, %Carnot and room RMS error. Because daily COP is noisy (about 10% SD after outdoor-temperature correction; about 6.4% for %Carnot), compare strategies over about 3–4 weeks per arm, alternating arms and binning by outdoor temperature, to detect about 5% effects [1].

**C. Candidate control architectures the community uses, mapped to this house** (the owner asked for alternative code logics)

| # | Logic | Who uses it | Field evidence | Fit for this house |
|---|---|---|---|---|
| A | Unit's own weather curve (coil 22) + slow ±1 K room trim from HA | Most top HPM systems; Chris Hill [14]; Energy Stats "Active" [26] | Best median COP on HPM (4.14) [1] | Good baseline. But the Versati restarts on ΔT, not degree-minutes, so cycle quality depends on its firmware. Test first: cheapest. |
| B | HA degree-minute / energy-deficit trigger + low flow target | NIBE/Vaillant firmware logic [54, 22]; Bosch emulation [39] | Firmware logic proven fleet-wide; no DIY before/after | Strong fit: slab plus minimum output > load. Controls run length directly. |
| C | Daily energy-budget planner (forecast × heat-loss model) delivering N long low-flow blocks in warm/PV hours | BuildHub JohnMo [50]; Volta EMS [49]; SAT duty-cycle idea for boilers (15–30 min blocks) [47] | Volta 476 kWh (unnormalised) [49] | Strong fit: 6.6 kWh/K slab and PV. Needs the heat-loss model and a forecast. Combine with B as the in-day trigger. |
| D | PI controller on a fake outdoor temperature or curve offset (PumpSteer, TrueTemp) | Nordic/Swedish HA users [44, 45] | None published | Few writes, robust. Inherits the unit's on/off behaviour, so it can't fix catch-up sprints. |
| E | Direct flow-setpoint "riding" + power cap | MyForest manual control [11]; Ecodan fake-target [37] | Anecdotal (COP 2.58 → 3.32 at 9 °C, one site [11]) | Best potential for low flow and speed, highest risk (write wear, firmware surprises). Use as a layer within B/C runs. |

**Confidence overall:**
- Rules 1, 2, 8 (no on/off), 12 and 13: **high**. Strong field data and consistent with physics.
- Rules 3, 4, 9, 10 and 11: **medium**. Supported by field data or firmware practice; magnitudes from UK-climate data.
- Rules 5, 6 and 7: **low-medium**. Mechanism plausible and used by owners of other brands; Gree register semantics and EEPROM behaviour unverified.

---

## Contradictions and open questions

1. **Raise the minimum flow to stop cycling, or lower the flow and accept cycling?**
   - Daikin owners raise the minimum leaving-water temperature to 29–30 °C and the overshoot to 3–4 K [15, 16]. Timbones says one Ecodan circuit won't run smoothly below 43 °C [20].
   - The within-system field data says +1 K costs 15–25× more than the starts it removes [1].
   - Possible reconciliation: raising helps only when runs are under about 10–20 min, or the emitter can't absorb the minimum output at all. A slab can.
2. **Emitter ΔT:** Heat Geek wants larger ΔT (about 8 K at peak; mild-weather 1.6 K is "too low") [31]. Daikin owners lowered ΔT to 3–5 K to lengthen runs [15]. Unresolved; system-specific.
3. **Is cycling harmful at all for modern inverters?**
   - Some forum posters see no evidence it matters, and COP is barely affected by Vaillant start-threshold changes [22].
   - DECC fixed-speed tests show losses under 6 min [8]. HPM shows about 4% loss for runs under 20 min and 3–10% at 18 or more starts a day [1].
   - Wear per start is unquantified everywhere.
   - Cross-sectional %Carnot shows no link to starts (−0.02), while within-system data shows a small negative link. Confounding (low-load days, DHW starts) likely explains part of the within-system effect.
4. **Setbacks:** cathodeRay's early data suggested savings. His later regressions and other moderators' estimates suggest none or losses at mild temperatures [29, 30]. Thermal-mass-specific (slab) setback data is absent from the community record.
5. **Auto Adapt / room-model control vs pure WC:** owners split (less cycling but hotter flow) [20]; HPM samples are too small (n=7) [1].
6. **Buffers:** reduce cycling in theory and in the DECC tests [8, 33], but are associated with lower COP and *more* starts in HPM field data [1]. Likely selection: buffers are fitted to awkward systems.
7. **Vaillant energy-integral range:** the manual allows −999 °min (snippet only) [56], while one guide says installers can go to −100 [26]. One of the two is incomplete.
8. **NIBE degree-minute sign conventions** confuse owners ("lower" meaning more negative); the advice to "decrease" the value is ambiguous [57, 54].
9. **Open questions for the Gree Versati** (none answered by the community) [35]:
   - Exact semantics of "ΔT heat" (register 30): is it purely the restart hysteresis?
   - Does "heat run time set" (register 34, 1–10 min, default 5 per one HA config) mean a minimum run or minimum off time?
   - Does the power limit (word 43) cap compressor input in heating mode?
   - Are Modbus setpoint writes stored in EEPROM?
   - Does the circulation pump keep running when the compressor is off, and where is the outlet sensor?
   - What compressor frequency does the firmware choose at restart for a given setpoint error?
   - Does the built-in weather-dependent mode (coil 22, register 137) restart any differently?
10. **Climate transfer:** no Baltic or continental air-source systems in HPM, and only one Gree (COP 2.22, with its own issues) [1]. Defrost-heavy humid days at −5 to +5 °C (common in Lithuania) may change the run-length and cycling trade-offs. In HPM, cold-band (−5 to 2 °C) days at 18 or more starts/day lost about 3.5% [1].
11. **Missing evidence:** no DIY project published a weather-normalised before/after for an HA controller on slab UFH. The owner's own A/B logs could be the first.

---

## Sources

1. HeatpumpMonitor.org public data API — system list `https://heatpumpmonitor.org/system/list/public.json`, 365-day stats `https://heatpumpmonitor.org/system/stats/last365`, daily stats `https://heatpumpmonitor.org/system/stats/daily?id=N` - OpenEnergyMonitor / system owners - accessed 2026-11-06 - **field data** - my own analysis: 451 full-year air-source systems and 67 UFH single-zone systems (27,190 days). Cycling vs COP, run-length bins, flow quartiles, control-type/buffer/zone/oversizing groupings, test-noise estimates.
2. Low flow temperature = High performance - OpenEnergyMonitor docs (T. Lea) - 2025 - https://docs.openenergymonitor.org/heatpumpmonitor/low_temperature.html - **field data (analysis)** - SPF regressions vs flow and (flow − outdoor); coldest-day flow benchmarks; case systems.
3. HeatpumpMonitor.org Introduction - OpenEnergyMonitor docs - 2025 - https://docs.openenergymonitor.org/heatpumpmonitor/introduction.html - **field data (summary)** - fleet SPF 3.83–3.86; note that some controls achieve high performance through controlled mild-weather cycling.
4. Bridging the heat pump efficiency divide - A. Smith, CIBSE Journal (reporting Rosenow, Lea & Boni, Energy and Buildings 352:116785) - 2026 - https://www.cibsejournal.com/technical/bridging-the-heat-pump-efficiency-divide-2/ - **paper (field data + simulation)** - HPM 3.86 vs EoH 2.81 vs RHPP 2.36; 55% of EoH Vaillant curves too high; room-stat cycling and setback findings; simulated COP 2.86 → 4.61.
5. HeatpumpMonitor.org: SCOP (Annual) vs "design" flow temperature - OEM forum (T. Lea et al.) - 2024 - https://community.openenergymonitor.org/t/heatpumpmonitor-org-scop-annual-vs-design-flow-temperature/26653 - **field data / forum** - systems run ~7 K below design; %Carnot R² 0.54; "50% Carnot / 40% modulation" heuristic.
6. HeatpumpMonitor.org heat pump database: minimum modulation tests - OEM forum (T. Lea) - 2025 - https://community.openenergymonitor.org/t/heatpumpmonitor-org-heat-pump-database-minimum-modulation-tests/29132 - **field data / forum** - Vaillant 10 kW range 5.9–9.6 kW; degree-minute cycling compensates for a narrow range.
7. HeatpumpMonitor.org starts & starts per hour - OEM forum - 2024 - https://community.openenergymonitor.org/t/heatpumpmonitor-org-starts-starts-per-hour/26246 - **forum (method)** - 100 W start detection; Daikin pump false starts (111 W threshold); Vaillant ~1.29 starts per compressor hour.
8. The effects of cycling on heat pump performance - EA Technology for DECC - 2012 - https://www.gov.uk/government/publications/heat-pump-performance-effects-of-cycling (PDF: https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/65695/7389-effects-cycling-heat-pump-performance.pdf) - **lab (test house)** - fixed-speed units; runs under ~6 min detrimental; buffer helped in short-cycling conditions.
9. Theoretical analysis of cycling losses in air source heat pump systems - H. Qiao, C. Laughman (MERL), ICR 2023 - 2023 - https://merl.com/publications/TR2023-127 - **paper (simulation)** - refrigerant migration and capacity rise time dominate cycling loss; mitigation −60% to −95%.
10. Volume simulator with heat pump COP - OpenEnergyMonitor tools - n.d. - https://openenergymonitor.org/tools/volume_sim_cop - **tool / model** - minimum-volume formula; simplified cycling model.
11. Improve efficiency: Turn the heat pump off (pages 1 and 6) - OEM forum (D. Bowen "MyForest", Timbones, Dan_Nichols) - 2020–2023 - https://community.openenergymonitor.org/t/improve-efficiency-turn-the-heat-pump-off/13381 - **forum with owner data** - COP 2.58 vs 3.32 at 9 °C with a custom on/off algorithm; 37 °C steady vs 33 °C cycling.
12. How to reduce cycling? (page 6) - OEM forum - 2024 - https://community.openenergymonitor.org/t/how-to-reduce-cycling/25251?page=6 - **forum** - 150+ starts/day → 1–2/day, COP ~2.5 → ~4 (self-reported); Samsung FSV#6022 question.
13. Weather Compensation & ASHP Duty Cycle - OEM forum - 2023 - https://community.openenergymonitor.org/t/weather-compensation-ashp-duty-cycle/24793/4 - **forum** - 50–70% duty, ~3 cycles/2 h judged reasonable; "low and slow 24/7 with small setback" school of thought.
14. Beyond Weather compensation (Daikin) - OEM forum (C. Hill, critictidier, tiger_cook) - 2025 - https://community.openenergymonitor.org/t/beyond-weather-compensation-daikin/29152 - **forum** - WC + ±1 K HA offsets; WC+load+PID with <0.4 °C error; Madoka RT modulation causes many starts.
15. Daikin Altherma cycling every 5 mins - OEM forum - 2025 - https://community.openenergymonitor.org/t/daikin-altherma-cycling-every-5-mins/28065 - **forum** - mild-weather 4–5 min cycles; overshoot 4 K, ΔT 5 K, UFH setting; system volume advice.
16. Having to adjust Daikin WD curve daily, can't be right? (page 3) - OEM forum - 2025 - https://community.openenergymonitor.org/t/having-to-adjust-daikin-wd-curve-daily-cant-be-right/27857?page=3 - **forum** - "moving goalposts" hunting; overshoot 3–4 K; few Altherma units sustain under 29 °C.
17. Two months of learning with Octopus Daikin - OEM forum (chrisg et al.) - 2024–2025 - https://community.openenergymonitor.org/t/two-months-of-learning-with-octopus-daikin/27379 - **forum with owner data** - balancing/ABV fault; curve 45/27; Madoka modulation steps; −2 K night offset; HA cut-off.
18. HomeAssistant LWT monitoring <30C bad? - OEM forum - 2025 - https://community.openenergymonitor.org/t/homeassistant-lwt-monitoring-30c-bad/28317/3 - **forum** - some non-rapid cycling below 30 °C; proposed 30 min on / 2 h off pattern (untested).
19. Reasons for Ecodan overshooting target fixed flow temperature - OEM forum (Timbones) - 2025 - https://community.openenergymonitor.org/t/reasons-for-ecodan-overshooting-target-fixed-flow-temperature/25489/7 - **forum** - heat pumps don't control flow temperature directly; 2–3 cycles/h acceptable; Ecodan 11.2 kW minimum ~5–6 kW.
20. Anyone monitoring a new R32 Ecodan? (page 14) - OEM forum - 2024 - https://community.openenergymonitor.org/t/anyone-monitoring-a-new-r32-ecodan/19577?page=14 - **forum** - Auto Adapt vs WC anecdotes; COP 3.16 at ~3 cycles/h; 3.7 kW minimum vs radiator output.
21. Monitoring results from a 5kW Ecodan heat pump - OEM forum (T. Lea) - 2022 - https://community.openenergymonitor.org/t/monitoring-results-from-a-5kw-ecodan-heat-pump/20764 - **field data** - Pi-controlled flow temperature, no buffer or low-loss header; SCOP 3.91–4.04 (2019–2021).
22. Vaillant Arotherm Owners Thread (page 30) - OEM forum (Andre_K, jamespa) - 2024 - https://community.openenergymonitor.org/t/vaillant-arotherm-owners-thread/21891?page=30 - **forum** - energy integral −60/−100/−30 effects; hysteresis 7 K secondary; pump-speed fault.
23. Help Interpreting ASHP Data and Cycling Behavior - OEM forum (Zarch, Andre_K) - 2025 - https://community.openenergymonitor.org/t/help-interpreting-ashp-data-and-cycling-behavior/27849 - **forum** - slab UFH at ~25 °C flow at 7 °C, COP above 6; energy integral advice; cycling from ~7 °C.
24. Short cycling, third party thermostat help - OEM forum - 2026 - https://community.openenergymonitor.org/t/short-cycling-third-party-thermostat-help/29595 - **forum with owner data** - 919 cycles in 40 days with multi-zone stats; up to 3 cycles/h "acceptable"; sensor check method.
25. Experiences with Havenwise and other cloud-based control options - OEM forum - 2026 - https://community.openenergymonitor.org/t/experiences-with-havenwise-and-other-cloud-based-control-options/29786 - **forum** - mixed optimiser experiences; no measured savings.
26. Vaillant Arotherm Room Temp Mod: Which Setting Is Best? - M. Wall, Energy Stats UK - 2024 (updated 2026) - https://energy-stats.uk/sensocomfort-room-temp-mod-inactive-active-or-expanded/ - **blog with measured data** - Inactive/Active/Expanded behaviour; −180 °min catch-up; curve flow values; firmware bug. Note: promotes Havenwise (affiliate).
27. Vaillant Arotherm Heat Pump Guide & User Manual - M. Wall, Energy Stats UK - 2025/2026 - https://energy-stats.uk/vaillant-arotherm-heat-pump-guide/ - **blog** - curve tuning method; DHW Eco ~50% compressor cap, SCOP above 3.8; 5 kW unit SCOP 4.0.
28. Weather Compensation or Load Compensation? - Heat Geek - 2018 (written 2016) - https://www.heatgeek.com/weather-compensation-or-load-compensation - **blog** - WC is proactive with less cycling; room influence as a tuneable trim; zoning raises flow temperatures.
29. Setback savings - fact or fiction? (pages 5 and 10) - Renewable Heating Hub (cathodeRay, JamesPa, RobS) - 2024–2025 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/setback-savings-fact-or-fiction/paged/5 and …/paged/10/ - **forum with owner data** - setback vs continuous: −4% input but confounded; setback COP 5.5–8.3% lower; reheat costs more input.
30. Creative trials on night time setbacks… - Renewable Heating Hub - 2024 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/creative-trials-on-night-time-setbacks-to-faster-recovery-improved-comfort-and-even-greater-energy-reductions - **forum** - 50+ setback trial days; DIY Modbus auto-adapt script (±3 K curve shifts); defrost-heavy reheat COP ~2.
31. Performance of Heat Pumps in Mild Weather - Renewable Heating Hub (Heatgeek, RobS, Old_Scientist) - 2025 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/performance-of-heat-pumps-in-mild-weather - **forum** - start spikes per brand; flow rate / ΔT advice (~8 K at peak); 40–60 min cycles with a 0.5 K room-stat hysteresis.
32. Ecodan – is there actually such a thing as a minimum flow temp to avoid cycling? (page 2) - Renewable Heating Hub (JamesPa, SUNandAIR) - 2025 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/ecodan-is-there-actually-such-a-thing-as-a-minimum-flow-temp-to-avoid-cycling-and-why-if-so/paged/2/ - **forum** - cycling = demand < minimum output; volume changes frequency not ratio; Ecodan minimum outputs; 6–8 min Ecodan overshoot runs.
33. Avoid the heat pump villain: why low loss headers and buffers can sabotage… (page 11) - Renewable Heating Hub - 2024 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/avoid-the-heat-pump-villain-why-low-loss-headers-and-buffers-can-sabotage-your-heat-pumps-efficiency/paged/11/ - **forum** - DECC 6-min / ~8-min run-time interpretation; buffer run-time measurements (~4–5 min); disputes.
34. Mitsubishi Ecodan Raspberry Pi automations - Renewable Heating Hub (mjr) - 2023 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/mitsubishi-ecodan-raspberry-pi-automations - **forum** - wind/sun target nudges, −3 K overheat drop, DHW timing, post-DHW heating run.
35. Gree Versati III Air to water heat pump (pages 1–4) - Home Assistant Community - 2022–2025 - https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916 - **forum (register maps)** - Versati registers (10 LWT setpoint, 30 ΔT heat 2–10 K, 43 power limit, coils 17/22); protocol variants; smart-TRV flow errors; example HA setpoint automation.
36. Advanced Heat Pump Optimization (PV or w/o PV, Battery & Weather Aware) - Home Assistant Community (djm193) - 2026 - https://community.home-assistant.io/t/advanced-heat-pump-optimization-pv-or-w-o-pv-battery-weather-aware/992049 - **forum / blueprint** - curve-shift rules (+1 to +3 K PV, −4 K cut-off, 5-min filters); no results.
37. Advanced PV-Boost & Anti-Short-Cycling Logic for Mitsubishi Ecodan (FTC6) - Home Assistant Community - 2026 - https://community.home-assistant.io/t/advanced-pv-boost-anti-short-cycling-logic-for-mitsubishi-ecodan-ftc6-anyone-with-a-similar-setup/1007019 - **forum** - fake-target start delta under 11 K to avoid 104 Hz starts; PV DHW boost rules.
38. Weather compensation heating automation - Home Assistant Community - 2024–2025 - https://community.home-assistant.io/t/weather-compensation-heating-automation/735997 - **forum** - DIY curve + relay hysteresis (restart 4 °C below target) running 24/7 for ~4 years (boiler); heat pump UFH at 29 °C flow.
39. Visualize the on/off hysteresis for Nefit/Bosch heat pump - Home Assistant Community - 2023 - https://community.home-assistant.io/t/visualize-the-on-off-hysteresis-for-nefit-bosch-heat-pump/634160 - **forum** - K·min hysteresis values (150 split; ~200/250 monobloc); HA integral-sensor emulation.
40. ESPHome Mitsubishi Ecodan and remote thermostat integrations (page 11) - Home Assistant Community (gekkekoe) - 2026 - https://community.home-assistant.io/t/esphome-mitsubishi-ecodan-and-remote-thermostat-integrations/866580?page=11 - **forum** - auto-adaptive and virtual-thermostat hysteresis features; Odin optimiser beta; CNRF ~1 °C overshoot.
41. Short Cycle protection for heat pumps (#824) - GitHub discussion, BottlecapDave/HomeAssistant-OctopusEnergy - 2024 - https://www.github.com/BottlecapDave/HomeAssistant-OctopusEnergy/discussions/824 - **forum** - block starts within ~10 min of price-slot transitions.
42. HeishaMon README (rules engine) - Egyras/HeishaMon, GitHub - 2025/2026 - https://github.com/Egyras/HeishaMon - **project docs** - on-device rules, WAR curve example, EEPROM write-wear caution, command retry.
43. Compressor-Short-Cycle-Guard example ruleset - heishamon/HeishaMon, GitHub - 2026 - https://github.com/heishamon/HeishaMon/tree/main/Examples/Rules/Compressor-Short-Cycle-Guard - **project code** - −5 K offset for 45 min after a stop, outdoor ≥2 °C; no measured results.
44. PumpSteer Configuration Reference - J. Alvedal - 2025/2026 - https://johanalvedal.github.io/PumpSteer/Configuration - **project docs** - PI on fake outdoor temperature (Kp 2.4, Ki 0.035, clamps); price braking/preheat; comfort floors.
45. TrueTemp (ClimateOptimizer) - smefa, GitHub - 2026 - https://github.com/smefa/ClimateOptimizer - **project docs** - learned per-outdoor-temperature compensation; forecast and price awareness; dry-run mode; minimal writes.
46. CompCurve - rawnsley, GitHub - 2024/2025 - https://github.com/rawnsley/CompCurve - **project docs** - WC formula with wind/solar/demand terms; output table (−10 °C → 50.2 °C … 10 °C → 32.5 °C).
47. SAT – Smart Autotune Thermostat - Alexwijn, GitHub - 2025/2026 - https://github.com/Alexwijn/SAT - **project docs** - curve + PID + overshoot protection + automatic duty cycle (15–30 min) for boilers; ideas transferable.
48. Getting our Ecodan heat pump into Home Assistant, third attempt - M. Harizanov - 2026 - https://harizanov.com/2026/09/getting-our-ecodan-heat-pump-into-home-assistant-third-attempt/ - **blog with owner data** - 6,500 starts in 8,345 h; 77% of running hours with a stop-start; SCOP 3.14; oversizing.
49. Sturen van warmtepompen: waar de echte winst zit - Volta (Flemish electrotechnical knowledge centre) - c. 2025/2026 - https://volta-org.be/media/amrbnnjj/sturen-van-warmtepompen-waar-de-echte-winst-zit.pdf - **field data (case study)** - curve retune 2.7 → 1.7 kW, 33 → 22 kWh/day; EMS daytime steering −476 kWh/winter; minimum run times with dynamic prices.
50. Predictive heating control or monitoring - BuildHub forum (JohnMo, TerryE) - 2025–2026 - https://forum.buildhub.org.uk/topic/46136-predictive-heating-control-or-monitoring - **forum** - 24-h energy-budget controller; 1 h / 4 h temperature prediction for screed UFH; DHW at ~35 °C fixed flow.
51. How much efficiency does a short cycling heat pump lose? - GreenBuildingAdvisor Q&A - n.d. - https://www.greenbuildingadvisor.com/question/how-much-efficiency-does-a-short-cycling-heat-pump-lose - **forum** - no measured loss figure; start-up takes minutes; EnergyPlus-type cycling-degradation modelling suggested.
52. Nibe 2040/12 - ByggeBolig forum (Norway) - 2019 - https://byggebolig.no/luft-vann-varmepumpe/nibe-204012/10 - **forum** - NIBE rep: compressor stops when DM returns to 0; restart at ~−125 DM; 25 Hz minimum; circulation past the supply sensor matters.
53. Vaillant Luftwärmepumpe direkt über eBUS steuern - simon42 community (German HA) - 2025–2026 - https://community.simon42.com/t/vaillant-luftwaermepumpe-direkt-ueber-ebus-steuern/47369 - **forum** - limits of direct eBUS control; Vaillant cloud "up to 15%" claim (second-hand); SG-Ready via Shelly.
54. NIBE S1256 installer manual, menu 7.1.10.3 Degree minute settings - NIBE (via ManualsLib) - n.d. - https://www.manualslib.com/manual/3348937/Nibe-S1256pc.html?page=54 - **manufacturer** - start compressor range −1000 to −30 DM; trade-off (more starts vs uneven temperatures); auxiliary heat DM steps.
55. Generic Thermostat – minimal on time not followed - Home Assistant Community - 2025 - https://community.home-assistant.io/t/generic-thermostat-minimal-on-time-not-followed/1008144 - **forum** - generic_thermostat minimum run time is event-based and not enforced; PR #136298 adds time-based minimums.
56. Vaillant aroTHERM / VWZ AI installation manual - Vaillant - n.d. - https://professional.vaillant.co.uk/downloads/aproducts/renewables-1/arotherm-plus/monoblock-heat-pump-system-vwz-ai-heat-pump-appliance-interface-2685948.pdf - **manufacturer (snippet only; PDF text not extractable)** - "Compr. start heating from" −999 to +9 °min, factory −60; heating hysteresis 0–15 K, factory 7 K.
57. Byggahus.se threads on degree-minute settings (e.g., "Gradminut-inställning på Thermia Calibra…", NIBE fine-tuning) - byggahus.se - various - https://www.byggahus.se/forum/threads/gradminut-installning-pa-thermia-calibra-dampa-start-stopp-frekvens.568104/ - **forum (snippet only; 403 on fetch)** - owners lower DM start values for longer spring/autumn runs; sign-convention confusion; a Norwegian report of far fewer starts at −240.
