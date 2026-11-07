# Gap G5: How should hot water be run on the Versati all-in-one so that it costs least and disturbs space heating least? This covers tank setpoint against COP, the T-HP max and tank-heater split, time of day, the maximum DHW run and anti-recycle timers, how often legionella disinfection is legally or practically needed in Lithuania, and what a DHW cycle does to the slab run that follows.

Method note: this is the second pass on G5. The first pass had no web search, so it worked only from fetched manuals and its own analysis of heatpumpmonitor.org data. That pass also could not read any Lithuanian law. This pass ran about 25 web searches (EN, LT, DE, NL, SV, PL) and read about 24 sources. New in this pass:
- the Lithuanian hot-water hygiene norm HN 136:2023;
- Lithuanian legionellosis data from ECDC;
- the Versati III **all-in-one** service manual, including its COP correction tables, tank size and timers;
- Daikin and Mitsubishi DHW timer designs;
- Swiss, Dutch and Swedish rules;
- a UK government lab test of DHW;
- a Fraunhofer field case of a legionella heating rod;
- a legionella growth simulation.

Results from the first pass's heatpumpmonitor and Open-Meteo analyses are carried over and marked "(first pass)".

## Summary

- **Every 1 K of tank temperature costs about 2.5-3 % of DHW COP.** Gree's own correction table for the Versati III all-in-one at 7 °C outdoor gives these COP factors against leaving-water temperature [7]:
  - 45 °C: 1.00
  - 50 °C: 0.87
  - 55 °C: 0.74
  - 60 °C: 0.58-0.61

  With the 8 kW unit's rated 3.7 at 45 °C, that is a steady-state COP of about 3.7 / 3.2 / 2.7 / 2.2. Field data agree:
  - heatpumpmonitor DHW COP falls 3.30 → 3.09 → 3.00 → 2.78 as targets go ≤45 → 46-48 → 49-50 → 51-55 °C (first pass, n = 280 air-source systems) [25];
  - one UK system measured about +0.25 COP for a 45 °C against a 55 °C target [11].

  **Run the tank at 46-48 °C** unless the legal or vulnerability considerations below push it to about 52 °C.
- **The tank is 185 L, so one reheat holds only about 1.7-2.6 kWh.** The Versati III all-in-one has a 185 L tank, about 0.215 kWh per K [7][8]. The tank reheat hysteresis (ΔT-hot water) is limited to 2-8 K on this generation, default 5 K [7]. So a firmware-triggered reheat is at most about 1.7 kWh of heat: a 15-25 min run at 5-7 kW. That makes many small reheats the natural behaviour. **To get fewer, bigger reheats, Home Assistant must hold the tank setpoint low (40 °C) outside a DHW window and raise it inside the window.**
- **Afternoon DHW is worth about +2.4 % COP per K of outdoor temperature.** Gree's table at a 50 °C outflow goes from 0.72 at −2 °C to 1.00 at 15 °C outdoor [7].
  - Vilnius afternoons are 6-8.6 K warmer than 03:00 from March to September, 3-4 K warmer in February and October, and only 0.8-1.8 K warmer from November to January (first pass) [27].
  - So 13:00-15:00 DHW is about 15-20 % better than night DHW in the shoulder months, and only about 2-4 % better in mid-winter.
  - A UK user measured +0.23 COP on average for 13:00 against 01:00 over a year [11]. One reheat at −2 °C with two defrosts gave COP 1.8, against 3.0 at 7 °C [13].
- **The legionella cycle is the biggest avoidable DHW cost, and on this unit it can also block space heating.** Disinfection defaults to 70 °C, Saturday 23:00, by the tank heater [7] (note 08). From a 47 °C tank that is about 5 kWh of resistive heat a week, about 260-290 kWh a year (my calculation, 185 L).
  - In Fraunhofer's field test, one air-source system's weekly legionella rod heating alone cut its seasonal performance factor (SPF) by 0.15 [15].
  - With tank-heater **Logic 1** (the default), the compressor may not run while the tank heater runs. A heater finish from 50 to 70 °C (about 4.3 kWh, roughly 1.5 h at 3 kW) is therefore also about 1.5 h with no space heating [7].
- **Lithuanian law: HN 136:2023 (in force 1 Jul 2023) sets ≥50 °C at the tap after 1 min of running**, and requires the system to be able to deliver ≥65 °C at the tap [1][2].
  - It binds designers, builders, installers and operators of building water systems and hot-water suppliers.
  - For private houses and flats where residents set their own temperature, the Health Ministry only *recommends* following it [1][2][3].
  - It requires Legionella testing after a break in use of more than one month, after repair, or after a diagnosed case. Above 10,000 CFU/L the system must also be cleaned.
  - I found **no periodic thermal-disinfection frequency** in any summary of the norm. The full text was blocked (HTTP 403), so this is medium confidence.
- **Lithuania's risk context changed in 2023.** Notified Legionnaires' disease went from 4-21 cases a year (0.1-0.7 per 100k, 2019-2022) to 71 cases (2.5 per 100k) in 2023 [5]. That followed a spring 2023 Kaunas outbreak with more than two dozen cases and 7 deaths [4]. There were 16 cases and 3 deaths in January-April 2024 [4]. None of these was tied to a single-family heat-pump tank in what I read.
- **Neighbouring rules range from none to strict.**
  - EU Directive 2020/2184 targets "priority premises", not private houses (first pass) [29].
  - Switzerland's SIA 385/1:2020 requires ≥55 °C everywhere and **dropped** its 2011 low-temperature heat-pump exception, which had been read as "60 °C for 1 h daily is enough" [20].
  - The Netherlands' NEN 1006 requires at least weekly disinfection above 60 °C if the store is not ≥55 °C everywhere [21].
  - Sweden's Boverket requires the ability to reach ≥50 °C at the tap and advises storage ≥60 °C, typically reached by an immersion heater [22].
  - Polish installer practice is a 14-day cycle, often only after holidays in houses with daily turnover [23].
- **The microbiology supports a sparse, cooler cycle when turnover is daily.** Kill times:
  - 50 °C: 90 % in 80-124 min.
  - 55 °C: 90 % in about 20 min.
  - 60 °C: 90 % in about 2 min, 100 % in about 30 min [19].

  In a German simulation of single-family systems, storage at about 42 °C needed no disinfection with ≥150 L/day of draw, up to a 400 L tank [16]. Disinfection on demand plus a heat pump cut DHW energy by 62 % against standard practice [16]. Against this, a Quebec review found about 40 % of electric tanks contaminated even with 60 °C thermostats, because the bottom stays at 30-40 °C [18]. **Stratification, not the setpoint, is the real risk.**
- **The Versati has no maximum-DHW-run, anti-recycle or DHW-restriction timer.** The only related settings are:
  - "Heat run time" (1-10 min; 3 min, or 5 min with the 2-way valve on), a minimum run before a standby stop;
  - priority (Heat or Hot water, default Hot water);
  - Fast hot water;
  - Tank heater Logic 1 or 2;
  - T-HP max (40-55 °C, default 50) [7].

  Other brands do have these timers. Daikin has a DHW maximum run of 5-95 min (not below 10), an anti-recycle of 0-10 h (minimum 0.5 h), extra time by outdoor temperature, and an outdoor "priority temperature" below which only the booster heater does DHW [9]. Mitsubishi has a DHW maximum operation time of about 30-120 min (default about 60) and a DHW restriction of about 30 min (search-level evidence) [10]. **Home Assistant must supply these timers.**
- **High compressor frequency during DHW makes the flow far hotter than the tank.** Gree sets the DHW compressor frequency from the gap between the tank setpoint and the tank temperature [7]. A big gap means high frequency and a hot flow.
  - On a Daikin with a 150 L tank and a 50 °C target, the flow peaked at 64 °C and cycle COP was 1.6-1.9.
  - Splitting the run into two bursts gave COP of about 2.9 for the first burst (51 °C flow) and about 2.15 for the second (60 °C flow) [12].
  - A 4 kW unit in quiet mode taking a 185 L tank from 26.6 to 43 °C reached COP 4.7 [12].
  - **Smaller tank gaps, lower compressor output, or a capped power** should all help (untested on the Versati).
- **What a DHW cycle does to the slab: a small, predictable energy deficit, plus probably one extra start.**
  - A 25-35 min reheat at 0 °C outdoor takes about 1.3-2.6 kWh from the slab (house loss 0.14-0.20 kW/K). That is 0.2-0.4 K of slab at 6.6 kWh/K. At −15 °C and 45 min it is 0.6-0.85 K (my calculation).
  - Within-system daily data show no lower space-heating COP and no extra starts on DHW days (median +2.5 % COP, −0.08 starts/day; first pass) [26].
  - Forum reports of 15-20 min of "piggy-backing" or waiting after DHW fit the hot-slug mechanism: the outlet sensor sees 45-55 °C water above the space-heating setpoint, so the unit stops [13][31]. This is not measured on this house.
  - **The real damage comes from a controller that "catches up" with hotter water after DHW.** Prevent that in software.
- **In mild weather DHW should never interrupt space heating at all.** Near +10 °C the house needs about 1.7 kW, the compressor's minimum is about 3.7 kW, and the unit runs less than half the time. A 20-30 min DHW block fits in an idle gap or right after a slab run (my reasoning). Interruption only matters below about −5 °C, where the unit runs most of the time.

## Detailed findings

### 1. The Versati III all-in-one: what the hardware and firmware actually do

**Hardware** [7][8]:
- Indoor unit = hydro module + **185 L DHW tank** (model code letter G = 185 L), 1800 × 600 × 650 mm, 195 kg.
- Auxiliary (backup) heater in the hydro module: 3 kW (1.5+1.5) on 6 kW, 6 kW (3+3) on 8/10 kW models.
- The tank has its own electric heater (power not stated for the all-in-one; Gree's separate 200/300 L tanks use 3 kW).
- Sanitary water 40-60 °C by heat pump, 80 °C with the heater.
- DHW operating range −25 to +45 °C outdoor.
- Nominal DHW rating point: 53 °C leaving water at 7 °C outdoor.
- A Polish trade article says the tank is "loaded in layers" (stratified). This is marketing, not tested [ref only in search results].

**COP correction tables** (service manual, ratio to nominal COP at 45 °C leaving water and 7 °C outdoor; 8 kW nominal COP 3.7 at 45 °C, 4.7 at 35 °C) [7]:

| Outdoor °C | 35 °C | 45 °C | 50 °C | 55 °C | 60 °C |
|---|---|---|---|---|---|
| −7 | 0.96 | 0.78 | 0.67 | 0.56 | 0.46 |
| −2 | 1.02 | 0.83 | 0.72 | 0.61 | 0.48 |
| 2 | 1.05 | 0.88 | 0.74 | 0.64 | 0.51 |
| 7 | 1.26 | 1.00 | 0.87 | 0.74 | 0.61 |
| 10 | 1.33 | 1.05 | 0.91 | 0.78 | 0.62 |
| 15 | 1.44 | 1.14 | 1.00 | 0.85 | 0.67 |

- Reading:
  - Each K of leaving water costs about 2.6-3 % of COP between 45 and 55 °C.
  - Each K of outdoor temperature gives about 2-3 % at a 50 °C flow.
  - 50 °C leaving water is not available below −15 °C, and 55 °C not below −10 °C (blank cells). In deep cold the compressor alone cannot heat the tank above about 45-50 °C.
  - Heating capacity at a 50 °C flow is 0.54-0.63 × nominal at −15/−10 °C [7].
- These are steady-state ratings. Field DHW COP is lower (defrost, start-up, standing loss, pumps): the median field DHW COP is 3.08 at a mean outdoor temperature of about 11 °C during DHW (first pass) [25].

**Water-heating logic** [7]:
- Inside the outdoor range, the compressor heats the tank, and its **frequency follows (tank setpoint − tank temperature)**. Outside the range, the tank heater does it.
- Tank setpoint below the unit's water-heating maximum: the **auxiliary heater of the main unit runs "depending on the temperature difference"** and the tank heater stays off.
- Setpoint above the maximum: the compressor (plus possibly the auxiliary heater) heats to the maximum, then the tank heater takes over. The auxiliary heater and the tank heater never run together.
- **T-HP max**: 40-55 °C, default 50 °C. The Logic 2 text treats it as a *tank* temperature ("when water tank temperature reach THPmax").
- **Tank heater Logic 1** (default): compressor and tank heater (or optional E-heater) NEVER run together.
- **Logic 2**: in Heat/Cool + Hot water with hot-water priority, if Tset ≥ T-HP max + ΔT-hot water + 2, then once the tank reaches T-HP max the tank heater finishes the job while the compressor returns to space heating. Changeable only with the unit off.
- **Optional E-heater**: Off/1/2, default Off. Its Logic 2 allows it together with the heat pump below T-Eheater. It never runs together with the tank heater.
- **Defaults**:
  - T-water tank 50 °C (range 40-80).
  - ΔT-hot water 5 K (range 2-8).
  - Heat + hot water priority = Hot water.
  - Disinfection Off by default; when enabled, Saturday 23:00. It has priority over Hot water mode, runs even with the unit off, and aborts on a tank-heater fault or a link error.
- **Clock timer**: can set Mode, WOT-Heat and T-water tank for a period.
- **Timer priority**: Temp timer > Clock timer > Preset > Weekly [7].
- **"Heat run time"** (commissioning): 1-10 min. When it expires and the temperature difference is still in the standby zone, the unit stops [7]. This is a minimum-run guard, not a maximum-DHW guard.
- **Fast hot water**: runs the heat pump and heater together; keep it off (note 08).
- Newer panels add "Hot water control mode: Manual" (fixed compressor frequency during DHW, second-generation monobloc only) and ΔT-hot water up to 25 K (first pass) [32].
- Sources disagree: the Versati III **monobloc** manual lists the disinfection default temperature as 70 °C (note 08). The all-in-one manual shows the setting but no default in the extracted text.

**Other brands' DHW timers, for design reference**:
- Daikin Altherma 3 M [9]:
  - [8-01] maximum DHW running time: 5-95 min, never below 10 min. It is applied only when there is a simultaneous space-heating request if the control is a room thermostat.
  - [8-02] anti-recycle: 0-10 h, actual minimum 0.5 h.
  - [8-04] extra running time at low outdoor temperatures: 0-95 min.
  - [5-02]/[5-03] space-heating priority: below an outdoor "priority temperature", DHW is heated **by the booster heater only**, with [5-04] raising the setpoint up to 20 K to compensate.
  - Disinfection: [2-03] 55-75 °C with a 5-60 min hold [2-04].
- Mitsubishi Ecodan FTC [10] (garbled manual tables plus forum posts, low confidence):
  - DHW max operation time 30-120 min (default about 60).
  - DHW mode restriction (space heating has priority afterwards) about 30 min.
  - Legionella prevention defaults of about 65 °C, every 15 days, 03:00, hold about 30 min, max 3 h.

### 2. Tank temperature against COP and energy

- Lab ratings: see the table above. 45 → 50 °C leaving water is −13 % at 7 °C outdoor and −16 % at 2 °C [7].
- Field data (first pass) [25]:
  - Median DHW COP by target: ≤45 °C 3.30 (n = 59), 46-48 °C 3.09, 49-50 °C 3.00 (n = 129), 51-55 °C 2.78, >55 °C 2.34.
  - % Carnot is flat (40-43 %), so the loss is lift, not machine quality.
  - Within-system: −0.052 COP per K of DHW flow (IQR −0.082 to −0.016) and +0.050 COP per K of outdoor temperature [26].
- Single system (Vaillant 5 kW, 250 L Mixergy, Sheffield) [11]:
  - 55 °C target at 8.4 °C outdoor gave COP 2.97 (flow rising from 22 to above 67 °C); a 45 °C target would give about 3.25.
  - Starting at 20 % state of charge rather than 60 % gave about +0.5 COP (246 runs at 10-14.9 °C outdoor). Starts at 75-90 % were "significantly worse".
  - Typical hysteresis by sensor position: top ≈ 5 K, middle ≈ 10 K, bottom ≈ 20 K.
- UK government lab test (DESNZ HEM-VAL-06, one monobloc, 150/210 L cylinders, EN 16147-style 24 h tests at 2, 7 and 14 °C outdoor) [14]:
  - 24 h DHW COP including standing and cycling losses was only about 1.2-2.5.
  - It rose with outdoor temperature, was lower with the 150 L than the 210 L cylinder, and was lower when the thermostat sat lower in the tank, because of more cycling.
  - Small tapping patterns came out near COP 1.
  - Lesson: **with a small tank and modest draws, standing loss and frequent short reheats dominate**, so fewer, larger reheats matter as much as the setpoint.
- Daikin owners [12]:
  - 150 L at a 50 °C target: flow peaked at 64.4 °C and cycle COP was 1.6-1.9.
  - Two bursts gave about 2.9 (51 °C flow) and 2.15 (60 °C flow).
  - A 4 kW unit in quiet mode took a 185 L tank from 26.6 to 43 °C at COP 4.7 overnight in mild weather.
  - Samsung: two 15 min bursts with a 5 min gap kept the leaving water at about 55 °C instead of above 60 °C for the same heat.
- Vaillant Eco mode (compressor at about 50 %): 3.74 against 3.38 annual DHW COP (first pass) [28].
- Standing loss: Heat Geek claims about 20 % less loss at 50 °C than at 60 °C and about 40 % less at 45 °C (author's estimate) [19]. One owner measured 5 K lost in 16 h [13].
- Heat per K of this tank: 185 L × 1.163 Wh/(L·K) ≈ 0.215 kWh/K.
  - Usable 40 °C water from a 47 °C tank with 10 °C mains: 185 × 37 / 30 ≈ 228 L.
  - From 52 °C: about 259 L.
  - From 60 °C: about 308 L (my calculation).
  - The tank is small for 3-4 people at 46-48 °C, so check whether one daily reheat is enough.

### 3. Legionella: law, epidemiology and practice

**Lithuania**
- **HN 136:2023 "Karšto vandens visuomenės sveikatos saugos reikalavimai"**, approved 20 Jun 2023 (V-710), in force 1 Jul 2023 [1][2]. It took the hot-water rules out of HN 24:2023.
- Scope: people who design, build, reconstruct, repair, install or operate building water systems, plus hot-water suppliers and maintainers of heating and hot-water systems.
- Content:
  - Hot water must be made from drinking water that meets HN 24:2023.
  - **≥50 °C at users' taps after 1 min of running.**
  - The system must allow raising the temperature to **≥65 °C at the taps**.
  - Legionella testing after more than one month without use, after reconstruction or repair, or when residents are diagnosed.
  - **>10,000 Legionella/L → cleaning**, then re-testing.
  - Chemical disinfection needs 2 days' written notice to users [1][2].
- Private houses: the ministry and NVSC say residents who regulate their own water temperature *should* follow the temperature requirements, and owners of their own house should raise the heater temperature themselves [2][3]. That is advice, not an obligation in any text I could read.
- I found no thermal-shock frequency in the norm's summaries. "Termošokas" appears in Lithuanian advice for apartment blocks, not houses [search only].
- Older pages still quote HN 24:2003's 50-60 °C system range and a heater able to reach 66 °C [search results]. Treat these as superseded.
- Epidemiology [4][5]:

| Year | Cases | Rate per 100k | Notes |
|---|---|---|---|
| 2019 | 17 | 0.6 | |
| 2020 | 12 | 0.4 | |
| 2021 | 4 | 0.1 | |
| 2022 | 21 | 0.7 | |
| 2023 | 71 | 2.5 (age-standardised rate 2.3) | Spring 2023 Kaunas outbreak: >24 cases, 7 deaths. Lithuania was one of 7 EU/EEA countries reporting outbreaks |
| 2024 (Jan-Apr) | 16 | — | 3 deaths |

  The EU/EEA rate in 2023 was 3.2 per 100k, the highest of the decade [5]. One 2023 Dutch outbreak (23 cases, 4 deaths) was linked to a newly installed flow-through water heater brand in private homes; the suspected cause was factory test water left inside the heaters [5][24]. **Domestic sources are not zero-risk**, but that mechanism is unrelated to storage temperature.

**Other jurisdictions (for calibration)**
- EU 2020/2184: Legionella <1000 CFU/L parametric value, risk assessment for priority premises, no temperature rule for private homes (first pass) [29].
- Switzerland, SIA 385/1:2020 [20]:
  - ≥55 °C at every point of the system; store 55 °C without circulation, 60 °C with circulation; 50 °C at the tap.
  - The 2011 exception for low-temperature systems such as heat pumps was removed. It had been read as "daily 60 °C for 1 h is enough".
- Netherlands, NEN 1006:2018 (via a branch presentation) [21]:
  - 55 or 60 °C at taps.
  - If the store is not ≥55 °C everywhere, at least weekly preventive disinfection above 60 °C. Many heat-pump boilers cannot prove this, because the disinfection temperature is often not measured at the coldest point.
- Sweden, Boverket [22]: the installation must be able to reach ≥50 °C at the tap; storage should not fall below 60 °C (general advice), with an immersion heater as the usual way for heat pumps; ≤60 °C at the tap for scald safety.
- IEA HPT Annex 46 [17]:
  - Below 60 °C storage does not raise risk if the distribution volume is under 3 L.
  - Single-family systems with less than 3 L in the distribution "are known not to be affected".
  - Legionella cycles are excluded from heat-pump test standards, so rated DHW COP ignores them.
- Germany: the 3 L / 400 L "large system" rule exempts typical single-family houses from strict testing (first pass, via DVGW W551).

**Evidence on domestic tanks**
- Quebec (INSPQ review) [18]:
  - About 40 % of electric water heaters were contaminated even when set to 60 °C, because the bottom sits at 30-40 °C.
  - Electric tanks were more often contaminated than oil or gas tanks (39 % against 0 % in one 211-home study, per search results).
  - The institute calls the risk low at 49 °C and probably non-existent at 60 °C, and still recommends 60 °C plus anti-scald mixing.
- German study of 452 samples: water below 46 °C was most often colonised; temperature was the main determinant (abstract via search results).
- Simulation (Kaschewski et al., REHVA Journal) [16]:
  - Single-family system with less than 3 L of pipe.
  - With 50 L/day of draw, no disinfection was needed up to about 100-150 L of tank. With 150-300 L/day, none up to 400 L.
  - About 42 °C storage was enough with disinfection on demand.
  - 62 % DHW energy saving against an electric tank with standard 55 °C / 60 °C practice.
  - Each shower released about 65 % of pipe biofilm cells after 14 days of stagnation, so **stagnation (holidays) is the trigger to act on**.
- Practice:
  - About 43 % of heatpumpmonitor systems have the cycle disabled. Their median DHW COP is 3.18, against 3.04 for weekly cycles (first pass) [25].
  - Fraunhofer ISE (WPsmart im Bestand): heating-rod energy averaged 1.9 % of compressor energy. Significant rod use came only from wrong settings, defects or **legionella mode**. One system lost 0.15 SPF purely to a weekly legionella rod cycle [15].
  - NIBE practice in Poland: a 14-day cycle mainly for rarely used large tanks; in houses, usually only after holidays, because 200-300 L is turned over daily [23].
  - Heat Geek: with about 100 % daily turnover, a 45 °C store without cycles; 50 °C for most homes; more caution with vulnerable occupants. Its domestic-risk figure (about 1 in 620,000 a year) is an upper-bound assumption, not data [19].

### 4. Time of day

- Outdoor temperature effect: +2-3 % COP per K from Gree's table [7]; field data +0.05 COP per K (first pass) [26].
- Vilnius 2022-2025 hourly means, 03:00 against 14:00 (first pass) [27]:

| Months | Afternoon warmer by |
|---|---|
| Dec | 0.8 K |
| Jan | 1.1 K |
| Nov | 1.8 K |
| Feb | 3.1 K |
| Oct | 4.1 K |
| Mar-Sep | 6.3-8.6 K |

  - Afternoon relative humidity is 25-30 points lower in March-September, so fewer defrosts.
  - Solar is 2.9-6 kWh/m²·day in March-September and 0.35-0.6 in November-January.
- Energy Stats UK, 2024, 13:00 against 01:00 [11]:
  - COP 3.86 against 3.63 (outdoor 12.9 against 9.1 °C).
  - Monthly gaps +0.03 to +0.44, largest in March-April and October-December.
- Defrost during DHW: reheats at −2 °C with two defrosts gave COP 1.8, against 3.0 at 7 °C (Samsung, 300 L, 55 °C) [13]. One defrost took 6 K from a 180 L tank (first pass).
- Tariffs: UK users often choose night for price despite lower COP [11][13]. With 15 kWp of PV and a battery, the midday electricity is mostly self-produced, so the afternoon wins on both COP and price for most of the year. From November to January the COP gain is only 2-4 %, and a night-tariff discount (if the owner's plan has one; not checked) could outweigh it.

### 5. Reheat size, run length and the missing timers

- Natural firmware behaviour: tank setpoint Ts with ΔT-hot water d (≤8 K) means a reheat starts at Ts − d and adds ≤ d × 0.215 kWh: 1.1 kWh at 5 K, 1.7 kWh at 8 K.
  - At 5-7 kW (the frequency driven by a large tank-setpoint gap [7]), that is 10-20 min of compressor time, plus start-up.
  - Several such starts a day, each with the 3-way valve switching away from the slab, is likely what the owner sees as "DHW interrupting space heating".
- Forced big reheat: hold Ts = 40 °C (the minimum) outside the window, so the reheat start is 32-38 °C. In the window, raise Ts to 46-48 °C.
  - From about 34 °C to 47 °C: 13 K × 0.215 ≈ 2.8 kWh, about 30-40 min.
  - This copies the "start from low state of charge" advice (+0.5 COP from 20 % against 60 % [11]).
- A maximum-run guard is needed, because nothing in the firmware stops a long DHW run in deep cold. At −15 °C the heating capacity at a 45-50 °C flow is only about 0.54-0.56 × nominal [7], so a 2.8 kWh reheat on an 8 kW unit takes about 40 min, and the slab gets nothing.
  - Daikin's design (maximum run, plus extra time in cold weather, plus anti-recycle) is the template [9].
  - Mitsubishi's defaults (about 60 min maximum, about 30 min forced space-heating period) are a second reference point [10].

### 6. What a DHW cycle does to the slab and the run after it

- **Energy deficit** (my calculation; house loss 0.14-0.20 kW/K; slab 6.6 kWh/K):

| Outdoor | House load | DHW length | Deficit | Slab cooling |
|---|---|---|---|---|
| +10 °C | 1.7 kW | 30 min | 0.85 kWh | ≈0.13 K |
| 0 °C | 3.1-4.4 kW | 30 min | 1.5-2.2 kWh | ≈0.23-0.33 K |
| −15 °C | 5.2-7.4 kW | 45 min | 3.9-5.6 kWh | ≈0.6-0.85 K |

  - At +10 °C the unit is idle more than half the time anyway, so the deficit is zero if DHW is placed in an idle gap.
  - At −15 °C the deficit is noticeable, and the unit may have no spare capacity to repay it.
- **Field check**: within-system daily heatpumpmonitor data, DHW days against no-DHW days at the same outdoor temperature (first pass) [26]:
  - space-heating COP median +2.5 % (IQR −2.5 to +9.5 %);
  - starts per day −0.08;
  - space-heating kWh +0.2 %.
  - Daily data cannot see intraday effects.
- **Thermal mass rides through interruptions**:
  - A simulation of run-time limits found heavyweight construction kept comfort largely unchanged, while lightweight construction lost comfort (Hall & Geissler, CISBAT 2015, via search abstract).
  - A trade column reports a heated slab riding through 1-2 h of interrupted input [search abstract].
  - A ground-source simulation found room temperatures dipped during DHW priority but stayed in the comfort band [search abstract].
- **Handover mechanism**:
  - Forum reports describe space heating pausing 15-20 min after DHW, carried by the residual DHW heat, and flow and return returning to target within minutes after the valve swaps [31].
  - Kensa's application notes describe the same thing: after DHW the 3-port valve returns, the temperature falls to the space-heating design value, and the heat pump resumes or stops [search result].
  - On the Versati, the unit stops when the outlet exceeds the setpoint and restarts only below setpoint − Δ (4 K here) [7] (note 08). A post-DHW slug of 45-55 °C water therefore probably costs one extra stop/start and a 10-30 min gap. That gap is harmless to a slab, but it counts as a cycle (inferred, medium-low confidence).
- **Defrost**: a defrost during DHW takes heat from the tank; a defrost during space heating takes it from the slab. Afternoon DHW reduces both.
- **The controller trap**: if the room or slab error built up during DHW is answered by raising the flow setpoint, the repayment happens at 3-4 % per K worse COP (note 13). Repaying 2 kWh over the next 2-4 h at the normal curve costs nothing extra.

## What this means for controlling this house

Confidence: H = high, M = medium, L = low.

1. **Unit settings (one-off, unit off)** (H for the direction, M for the exact values):
   - **T-HP max = 55 °C** (the maximum), so the compressor can cover any routine setpoint up to about 53 °C and the 50 → 55 °C step of a disinfection.
   - **ΔT-hot water = 8 K** (the maximum on Versati III; up to 15-20 K if the panel allows 2-25 K).
   - **Fast hot water = Off.**
   - **Optional E-heater = Off**, or with T-Eheater at about −15 °C or lower and its Logic 1, so the hydro-module backup cannot "help" DHW in mild weather [7].
   - **Tank heater Logic 2**, so a disinfection finish by the tank heater runs *while* the compressor goes back to space heating, instead of blocking it [7].
   - Expect: routine DHW is 100 % compressor; resistive heat only in disinfection.
2. **Routine tank target 47 °C** (46-48). Consider **52 °C** only if:
   - (a) the owner wants literal HN 136 compliance (≥50 °C at the tap after 1 min);
   - (b) anyone in the house is elderly, a smoker or immunocompromised; or
   - (c) the tank is not turned over daily.

   The 47 → 52 °C cost is about 12-15 % DHW COP, roughly +60-90 kWh/yr of electricity, assuming about 1800 kWh/yr of DHW heat (my calculation) [7][25]. (M)
3. **Legionella schedule: replace "70 °C weekly at Saturday 23:00" with "60 °C every 14 days at about 12:30-13:00 on a mild or sunny day"**, with Logic 2. Add an **extra 60 °C cycle plus a flush of all hot taps for a few minutes after any absence of more than about 7 days**, the stagnation case [16]. This mirrors HN 136's "after a break of more than one month" trigger, made stricter [1].
   - Cost: about 2.2 kWh per event from 50 to 60 °C by heater, or about 1.1 kWh if T-HP max 55 lets the compressor take it to 55 °C. That is about 30-60 kWh/yr, against about 260-290 kWh/yr for the default.
   - If the household is healthy, under 50, and uses at least one tank a day, disabling it entirely and keeping only the post-absence cycle is defensible: Heat Geek, Kaschewski, Annex 46 and NIBE practice support it [16][17][19][23]. Swiss and Dutch rules would not allow it [20][21].
   - (M; the legal reading is M, the energy numbers H)
4. **One planned reheat a day, by tank setpoint (Modbus Word 13), not by mode changes** (mode changes need the unit off [7]) (M-H):
   - Outside the window: Ts = 40 °C. The reheat then starts only below 32 °C (with d = 8), which works as a safety floor.
   - In the window: Ts = 47 °C (or 52 °C).
   - **Window: start 12:30-14:00 from March to October.** From November to February, start when the house controller's slab-charging block ends (the timing is close to neutral in mid-winter), preferring the warmest hour.
   - **Add a conditional second window** (for example 05:00-06:00 or 18:00) only if the tank is below about 40 °C at the decision time.
   - Write Word 13 at most 2-4 times a day (flash wear, note 08).
5. **Placement against the slab** (M for mild weather, L-M for cold):
   - When outdoor > 0 °C (unit idling more than 30 % of the time): put DHW in an idle gap, ideally **straight after a space-heating run ends**, when the slab is charged and there is no space-heating demand. No space-heating time is lost, and the hot slug lands when nothing is asking for heat.
   - Never start DHW just before a planned slab charge.
   - When outdoor < −5 °C: keep exactly one reheat a day, in the warmest hour, at 45-47 °C. Do not raise the target to "bank" hot water.
6. **Home Assistant DHW guards (the timers the Versati lacks)** (M as a design; values are judgement, calibrated on Daikin and Mitsubishi defaults [9][10]):
   - **Maximum DHW run 40 min** at > 0 °C outdoor, **60 min** at < 0 °C. On expiry, set Ts = 40 °C.
   - **Anti-recycle 4 h** between DHW starts, unless the top tank temperature is below 38 °C.
   - **After any DHW end, 45-60 min of space-heating priority**: no DHW, and no flow-setpoint increase triggered by the DHW-period error.
7. **Compensate for DHW instead of reacting to it** (M):
   - Log each DHW event's minutes × current house load as a known heat deficit (kWh).
   - Let the slab planner repay it over the next 3-6 h at the *normal* curve flow temperature.
   - Freeze the room-error integral during DHW and for 60 min after.
   - This directly targets the owner's "lots of high-temperature water" complaint.
8. **Test gentler DHW** (L until measured):
   - (a) "Hot water control mode = Manual" (fixed frequency) if the panel offers it [32].
   - (b) Modbus power limit at about 2.0-2.5 kW of electricity during the window only.
   - (c) A stepped Ts (tank + 6 K, raised every 10-15 min).

   Goal: leaving water ≤ tank + 8 K, against the 64 °C peaks seen on other brands [12]. Compare 10-20 cycles each way at similar outdoor temperatures. Expected gain +0.2-0.5 COP [12][28].
9. **What to avoid**:
   - Tank setpoint above T-HP max (heater finishes, compressor blocked under Logic 1).
   - 70 °C disinfection at night in winter.
   - Fast hot water.
   - ΔT-hot water 2-5 K with an always-high setpoint (many small reheats and valve swaps).
   - DHW in humid nights between −5 and +5 °C.
   - Raising the space-heating flow to recover from DHW.
   (H)
10. **Simulator DHW model** (M):
    - Tank: one node, 185 L, C = 0.215 kWh/K, UA ≈ 2-2.5 W/K to a 20 °C room (≈1.2-1.4 kWh/day at 47 °C; to be calibrated).
    - Draw profile from this house's data; default 4.9 kWh/day (median 1777 kWh/yr [25]).
    - Reheat: Q = min(Pcap(Tout, Tflow), 6 kW); Tflow_mean ≈ T_tank_mean + 6 K.
    - COP_DHW = 3.7 × f(Tout, Tflow) from the Gree table [7] × 0.85 field derate (defrost, start-up, pumps; calibrated so the result ≈ 3.0 at 11 °C outdoor and 47 °C [25]).
    - During a reheat, space-heating heat = 0. Add one compressor start after each DHW event when space-heating demand > 0.
    - Disinfection: electric block = (T_dis − T_HPmax) × 0.215 kWh at COP 1.
11. **Measure on this house** (from HA history; unit status 6 = hot water, tank-heater coil, note 08):
    - DHW events per day, kWh per event, start and end tank temperature.
    - Peak leaving water during DHW.
    - Minutes from DHW end to the next space-heating start.
    - Starts attributable to DHW.
    - Tank-heater hours.
    - Room and slab dip per DHW minute.

    Success looks like: ≤1.3 DHW events per day, DHW COP ≥3.3 from March to October, zero routine tank-heater hours, and no post-DHW flow rise above the curve.

## Contradictions and open questions

- **Does HN 136:2023 bind a private house owner?** The summaries say the norm applies to designers, installers, operators and suppliers, and only *recommends* it to residents who set their own temperature [1][2][3]. The full text (e-seimas, e-tar, infolex) returned 403. If "operator" (eksploatuotojas) were read to include a homeowner, a 47 °C tank would breach the ≥50 °C tap rule. Worth one email to NVSC, or reading the full text.
- **Setpoint advice conflicts by source**:
  - Quebec: 60 °C store plus mixing valve, but "low risk at 49 °C" [18].
  - Swiss and Dutch codes: ≥55 °C or weekly >60 °C [20][21].
  - Swedish code: storage ≥60 °C advised [22].
  - UK and engineer practice: 45-50 °C with no cycle at daily turnover [19].
  - Simulation: 42 °C with on-demand disinfection [16].

  The disagreement is mostly about large or managed systems against small, high-turnover ones. This house is the second kind, but the evidence base for "45-48 °C is safe" is modelling and expert judgement, not domestic sampling.
- **T-HP max meaning.** The all-in-one Logic 2 text treats it as a tank temperature [7]; note 08 calls it a maximum water-out. Check it on the unit.
- **Auxiliary heater during DHW.** The manual says the main unit's auxiliary heater runs "depending on the temperature difference" during water heating [7]. It is unclear whether "Optional E-heater = Off" fully blocks this on the all-in-one, where the hydro module has a built-in 2-stage heater [8]. Check the heater status during a cold-day reheat.
- **Tank-heater power and sensor positions** on this specific all-in-one were not found. The service manual mentions two tank-sensor groups (one for control, one for display) [7]. Where the control sensor sits sets how "empty" the tank really is when a reheat starts.
- **Disinfection hold time.** The Versati panel offers temperature, day and hour, but no hold time like Daikin's 5-60 min [9]. If the cycle stops the moment the sensor reaches 60 °C, the bottom of the tank may never get there (the Dutch concern [21]). Measure the time above 60 °C at the sensor.
- **Gentler DHW benefit.** Vaillant Eco and Daikin bursts show +0.2-0.7 COP [12][28]. Daikin quiet mode gave mixed results. None of this has been tested on Gree.
- **Is the hot-slug restart real here?** It is inferred from the stop/restart logic plus forum reports [7][31]. Daily data show no penalty [26]. Verify with 1-minute HA data.
- **Night against afternoon in mid-winter** depends on the tariff (not checked) and on PV in December-January.
- **Survivor bias** in the heatpumpmonitor target bins: low-target systems may also be better installed (first pass). % Carnot is flat, which suggests lift explains most of the difference.

## Sources

1. Naujoje Lietuvos higienos normoje nustatyti karšto vandens sveikatos saugos reikalavimai (NVSC press release, republished) - Sūduvos gidas / NVSC - 2023 - https://suduvosgidas.lt/naujoje-lietuvos-higienos-normoje-nustatyti-karsto-vandens-sveikatos-saugos-reikalavimai - official summary (regulator) - HN 136:2023 scope, ≥50 °C at tap after 1 min, ≥65 °C capability, testing triggers, 10,000 CFU/L cleaning.
2. Po legioneliozės protrūkio – nauji karšto vandens reikalavimai - LRT - 2023 - https://www.lrt.lt/naujienos/sveikata/682/2034624/po-legioneliozes-protrukio-nauji-karsto-vandens-reikalavimai - news citing the ministry - who is bound; private homes only advised; 48 cases by June 2023.
3. Maintenance of an adequate temperature helps prevent Legionnaires' disease - NVSC (National Public Health Centre) - 2024? - https://nvsc.lrv.lt/en/naujienos/maintenance-of-an-adequate-temperature-helps-prevent-legionnaires-disease - regulator advice - ≥50 °C at taps, cold ≤20 °C; house owners advised to raise heater temperature; 59 cases January-September.
4. Lithuania records 16 legionellosis cases, three deaths in four months - LRT English - 2024 - https://www.lrt.lt/en/news-in-english/19/2272756/lithuania-records-16-legionellosis-cases-three-deaths-in-four-months - news - 2024 cases; 2023 Kaunas outbreak (>24 cases, 7 deaths).
5. Legionnaires' disease, Annual Epidemiological Report for 2023 - ECDC - 2025 - https://www.ecdc.europa.eu/sites/default/files/documents/LEGI_AER_2023_Report.pdf - surveillance data - Lithuania 4-21 cases a year in 2019-22, 71 (2.5 per 100k) in 2023; EU 3.2 per 100k; Dutch water-heater outbreak.
6. Search-result abstracts used only for context, not read in full - various - 2015-2026 - Hall & Geissler CISBAT 2015 (https://irf.fhnw.ch/entities/publication/0b9c7ff1-faf5-4e63-a9d4-89cb86cc9a2c/full), MDPI Energies 12(11):2120 GSHP DHW-priority simulation (https://mdpi.com/1996-1073/12/11/2120), PM Engineer Hydronics Workshop March 2026, Kensa application notes, Quebec 211-home study and German 452-sample study abstracts (PubMed 1768104, 17409022) - mixed, low weight - thermal mass rides through interruptions; electric-tank and <46 °C colonisation findings.
7. VERSATI III All-in-one Type Air To Water Heat Pump, service manual (4/6/8/10 kW) - Gree, hosted by Gree Bulgaria - about 2019 - https://gree-bulgaria.com/manuals/service/Versati_III_Split_All_In_One_04_08_10_service.pdf - manufacturer - 185 L tank, COP and capacity correction tables against leaving water and outdoor temperature, water-heating logic, T-HP max, tank-heater Logic 1/2, optional E-heater logic, ΔT-hot water 2-8 K, disinfection defaults, Heat run time, timer priorities.
8. Katalogový list GREE VERSATI III Split All In One - Slovklima - 2023 - https://www.slovklima.sk/wp-content/uploads/2024/05/Katalogovy-list_GREE_VERSATI_All_In_One.pdf - manufacturer catalogue - 185 L tank; 2-stage backup heater 3 or 6 kW; DHW 40-60 °C (80 °C with heater); DHW range −25…+45 °C; floor COP 5.0 and radiator COP 3.7-3.9.
9. Daikin Altherma 3 M (EBLA/EDLA04-08E) installer reference guide 4P685228-1 - Daikin (via Renewable Heating Hub) - 2022 - https://renewableheatinghub.co.uk/wp-content/uploads/wpforo/attachments/6/7596-Daikin-EBLA04-08E3V3EDLA04-08E3V3Installer-reference-guide4PEN685228-1English.pdf - manufacturer - DHW maximum run [8-01] 5-95 min, anti-recycle [8-02] 0-10 h (≥0.5 h), [8-04] cold extra time, space-heating priority temperature with booster-only DHW, disinfection 55-75 °C with 5-60 min hold.
10. Mitsubishi Ecodan FTC DHW and legionella settings (manual tables and forum threads, search-level only) - Mitsubishi Electric / Renewable Heating Hub - various - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/ecodan-legionella-operation-time - manufacturer and forum (low confidence) - DHW max operation about 30-120 min (default about 60), DHW restriction about 30 min, legionella about 65 °C every 15 days, hold about 30 min.
11. Best heat pump hot water settings - Energy Stats UK - 2025 - https://energy-stats.uk/best-heat-pump-hot-water-settings/ - blog with field data - 45 against 55 °C (+0.25 COP), state-of-charge effect (+0.5), 01:00 against 13:00 monthly COP table, hysteresis by sensor position.
12. Daikin Altherma 3 sub-2 DHW COP - OpenEnergyMonitor forum - 2024 - https://community.openenergymonitor.org/t/daikon-altherma-3-sub-2-dhw-cop/27453 - forum with measured cycles - 64 °C flow peaks for a 50 °C target; split bursts COP 2.9 against 2.15; 4 kW quiet mode COP 4.7 on 185 L.
13. Improve efficiency: heat the hot water when it's cold - OpenEnergyMonitor forum (page 2) - 2023 - https://community.openenergymonitor.org/t/improve-efficiency-heat-the-hot-water-when-its-cold/13383?page=2 - forum with measured cycles - COP 1.8 at −2 °C with two defrosts against 3.0 at 7 °C; reheat only below 25 °C bottom sensor; 5 K loss in 16 h (from a linked thread).
14. HEM-VAL-06: Lab testing of heat pumps providing DHW - UK DESNZ / BRE - 2023 - https://assets.publishing.service.gov.uk/media/65785a15254aaa0010050b25/hem-val-06-lab-testing-heat-pumps.pdf - lab - 24 h DHW COP about 1.2-2.5 including losses; worse with smaller cylinder, lower thermostat and more cycling; better at warmer air.
15. WPsmart im Bestand, final report - Fraunhofer ISE - 2020 - https://wp-monitoring.ise.fraunhofer.de/wpqs-im-bestand/download/Berichte/BMWi-03ET1272A-WPsmart_im_Bestand-Schlussbericht.pdf - field data - rod energy 1.9 % on average; significant only with wrong settings, defects or legionella mode; weekly legionella rod cut one system's SPF by 0.15.
16. Energy savings in hot water supply by Legionella modelling - Kaschewski et al., REHVA Journal - about 2023 - https://www.rehva.eu/rehva-journal/chapter/energy-savings-in-hot-water-supply-by-legionella-modelling - peer-reviewed-style simulation - critical tank volumes against draw, 42 °C storage with on-demand disinfection, −62 % DHW energy, stagnation effect.
17. Annex 46: Legionella - IEA Heat Pumping Technologies - about 2019 - https://heatpumpingtechnologies.org/annex46/legionella/ - international review - <3 L distribution rule, single-family systems unaffected, cycles excluded from test standards.
18. Prevention of scalding and legionellosis (domestic water heaters) - INSPQ (Quebec public health institute) - about 2006 - https://www.inspq.qc.ca/sites/default/files/publications/197_prevscaldingandlegionellosis.pdf - public-health review - about 40 % of electric tanks contaminated even at 60 °C because of cold bottoms; low risk at 49 °C; recommends 60 °C plus mixer.
19. Hot water temperature, scalding and legionella - Heat Geek - about 2024 - https://www.heatgeek.com/articles/hot-water-temperature-scalding-and-legionella - engineer blog - kill times; turnover rule (about 100 %/day means no cycle); 45-50 °C practice; loss reduction claims; risk estimate.
20. Trinkwasserinstallationen: minimale Warmwassertemperatur von 55 °C - suissetec - 2020 - https://suissetec.ch/files/PDFs/Ueber_uns/Deutsch/Wassertemperatur%20Trinkwasserinstallationen_Information_DE.pdf - trade body on SIA 385/1:2020 - 55 °C everywhere; storage 55 or 60 °C; heat-pump exception (daily 60 °C for 1 h) removed.
21. Warmtepompen en legionella (NEN 1006 from the sanitary installer's view) - Techniek Nederland (E. van der Blom) - 2024 - https://technieknederland.nl/media/gvnna1cz/warmtepompen-en-legionella-20-maart-2024pdf-1.pdf - trade body - 55 or 60 °C at taps; weekly >60 °C disinfection if the store is not ≥55 °C everywhere; measurement-point problem.
22. Legionella i vatten / Om legionella - Boverket - current - https://www.boverket.se/sv/pbl-kunskapsbanken/regler-om-byggande/boverkets-byggregler/vatten-och-avlopp/legionella-i-vatten - regulator (read via search extract; page body not retrieved) - ≥50 °C at tap capability, storage ≥60 °C advised, immersion for heat pumps, ≤60 °C at tap.
23. Tryby podgrzewania wody użytkowej w pompie ciepła - Globenergia - about 2021 - https://globenergia.pl/tryby-podgrzewania-wody-uzytkowej-w-pompie-ciepla-jakie-sa-mozliwosci-i-ktora-z-nich-wybrac/ - trade magazine - NIBE 46/50 °C hysteresis example; legionella usually every 14 days, in houses mostly after holidays; 200-300 L turned over daily.
24. Outbreak of Legionnaires' disease linked to newly installed residential water heaters, the Netherlands - Emerging Infectious Diseases (CDC), RIVM co-authors - 2026 - https://wwwnc.cdc.gov/eid/article/32/7/26-0171_article - peer-reviewed field investigation - 23 cases, 4 deaths, flow-through heaters, suspected factory test water; taps above 55 °C; Eco mode questioned.
25. heatpumpmonitor.org public system list and stats (analysis carried over from the first pass, n = 280 air-source systems) - OpenEnergyMonitor - 2026 - https://heatpumpmonitor.org/system/list/public.json - field data - DHW COP by target and legionella setting, median DHW heat 1777 kWh/yr, % Carnot.
26. heatpumpmonitor.org daily data, 114 UFH systems (within-system analysis carried over from the first pass) - OpenEnergyMonitor - 2026 - https://heatpumpmonitor.org - field data - DHW COP slopes against outdoor and flow temperature; DHW-day against no-DHW-day space-heating COP and starts.
27. Open-Meteo archive, Vilnius hourly 2022-2025 (analysis carried over from the first pass) - Open-Meteo - 2026 - https://archive-api.open-meteo.com/v1/archive - climate data - night against afternoon temperature, humidity and solar by month.
28. Vaillant aroTHERM hot water modes performance (carried over from the first pass) - Energy Stats UK - 2026 - https://energy-stats.uk/vaillant-arotherm-hot-water-modes-performance/ - blog with field data - Eco 3.74 against 3.38 DHW COP.
29. Directive (EU) 2020/2184 (carried over from the first pass) - EU - 2020 - https://eur-lex.europa.eu/eli/dir/2020/2184/oj - legal - Legionella parametric value, priority-premises risk assessment, no private-home temperature rule.
30. Internal notes 08 (Gree Versati) and 13 (field evidence) - this sweep - 2026 - docs/research/notes/ - mixed - register map, disinfection 70 °C default on monobloc, DHW as second-largest fixable item (not counted as new sources).
31. Space heating / hot water heating breakdown and related threads - OpenEnergyMonitor forum - 2024 - https://community.openenergymonitor.org/t/space-heating-hot-water-heating-breakdown/26664 - forum - post-DHW flow and return behaviour; the "piggy-back" pause after DHW was seen only in search extracts of related threads (low confidence).
32. Control Panel for the Versati Air-to-water Heat Pump, owner's manual (carried over from the first pass) - Gree / gree.gr - 2025 - https://gree.gr/wp-content/uploads/2025/07/600005064437-Users-manual-for-the-rest.pdf - manufacturer - Hot water control mode Manual (fixed frequency), ΔT-hot water 2-25 K on newer panels.
