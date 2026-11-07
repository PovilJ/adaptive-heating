# Gap G6: How does the Versati behave from −10 to −20 °C: capacity at W30-35, COP, when the backup heater (IBH) or tank heater switches on and how it is controlled, and how defrost behaves in that range?

> Research date: 2026-11-06. Follow-up researcher for gap G6, second pass.
> **Method.**
> - Pass 1 (same day) had no web-search budget. It relied on Gree service and Modbus manuals already downloaded in this sweep, on my own analysis of heatpumpmonitor.org daily data, and on 35 winters of Vilnius ERA5 temperatures. Those findings are kept here as sources [1]–[20].
> - Pass 2 ran **20 web searches**: English, Polish, Lithuanian, German and Swedish. I read **15 more sources** [21]–[35]. They include:
>   - a Swiss field-measurement report and Fraunhofer cold-wave data;
>   - NREL chamber and field tests in Alaska and a Purdue MPC cold-snap paper;
>   - the Versati II+ manual, the Swedish Versati Nordic sheet and the Polish Gree operating guide;
>   - the Lithuanian heat association's January 2026 note;
>   - OpenEnergyMonitor and Renewable Heating Hub cold-snap threads, and the HA Versati thread;
>   - an Aalborg thermal-mass flexibility paper.
> - I also recomputed Vilnius cold-day statistics for the **2025/26 season**, which pass 1 had not included [16].
> - **Not found:** any measured field data for a *Versati* below −10 °C. Polish forum threads (elektroda, murator) timed out or were blocked (HTTP 403). The Keymark/EPREL Versati data sheet could not be retrieved. The Gree Hungary server refused connections this time.
> - **Labels.** **[calc]** marks my arithmetic on cited data and **[model]** a simple daily energy balance. Neither is independent evidence.
> - I did not read this repository's code or non-research docs.

## Summary

1. **Gree's maximum-output tables (Versati III 10 kW, single-phase)** [1]:
   - Capacity: **W30 gives 6.56 / 5.70 / 4.85 kW at −10 / −15 / −20 °C. W35 gives 6.18 / 5.32 / 4.56 kW.**
   - COP: W30 gives 2.88 / 2.23 / 1.87, and W35 gives 2.41 / 1.84 / 1.55.
   - Capacity is flat from W35 to W45, so the compressor is the limit. Each 5 K lower flow is worth about 20 % COP at −20 °C.
   - The Versati IV 10 kW is about 20 % stronger (W30, −20 °C: 5.81 kW, COP 2.02) [4].

2. **Independent field data matches these COPs when the flow temperature is low.**
   - A Gree Flexx in Ottawa ran almost non-stop at −13…−18 °C and measured daily COP 1.6–2.0 [14].
   - On Switzerland's coldest day of 2020/21 (14 Feb 2021), inverter air-to-water units at daily means of −5.6…−8.7 °C reached:
     - daily COP **2.7–2.8 with flow at 32–33 °C**;
     - only **1.8–2.0 with flow at 52–54 °C** [31].
   - Fraunhofer's 17 air-to-water units averaged **2.3** over the first two weeks of February 2021 (mean outdoor −3.6 °C, spread about 1.6–2.8) [30].

3. **The balance point for this house is about −10 to −17 °C.**
   - Below that point the Versati runs flat out, and a higher water setpoint adds no heat, only lower COP [1] [calc].
   - 2025/26 showed this is not rare. Vilnius had **27 days with a daily mean below −10 °C, a 14-day spell, January averaging −10.0 °C**, and a minimum of −27.3 °C [16] [calc].
   - Pass 1 had said the cold tail was shrinking, based on 1991–2024 (last-decade average 5.6 days). One season has nearly matched the 34-year worst (28 days).

4. **Gree's backup heater (the "Optional E-Heater") switches on outdoor temperature alone.**
   - With Logic 1 (the default), below T-Eheater it **replaces** the compressor: the compressor stops and only the heater runs. With Logic 2 the two run together [1][3][7].
   - No Gree manual mentions a water-temperature, room-temperature or run-time condition [1][2][5][23].

5. **Defaults conflict, so read them from the unit.**
   - Versati II+ manual (gree.at) [23]: heater **Off**, T-Eheater **−7 °C**, second stage ("T-Extraheater") **−15 °C**.
   - Versati II (kievclimate copy) [5]: "1 group".
   - Versati III/IV panel tables: Off [1][2][6].
   - R32 Modbus map [7]: **1 set, −15 °C, Logic 1**.
   - Nordic variant: a built-in **9 kW (3+6)** heater [21].
   - If an installer set "1 set, Logic 1, −7 °C", it costs about **1,000+ kWh/season**. On 2025/26-type winters it is more [model].

6. **Field evidence says demand-blind heater logic wastes energy, and a slab makes it unnecessary.**
   - In the Swiss field programme [31], heaters ran in Feb 2021 only through comfort-oriented logic:
     - one unit switched its heater on after early-morning defrosts;
     - another added stage 1 after **5 min** and stage 2 after **10 more min** of compressor run.
   - The authors judged both unnecessary, partly because of the **sluggish underfloor slab**.
   - Fraunhofer: about half of 117 air-source systems logged *no* heater energy at all. The heater share averaged about 1.2–2 % of electricity [10][30].

7. **Good practice is demand gating.** Panasonic and Daikin gate the heater on demand [8][9]. A Polish guide gives a typical rule: below −10 °C, **compressor already running ≥ 3 h**, and water **≥ 5 K below setpoint** [34]. An external controller should impose this on the Versati, because the firmware has no such logic.

8. **Defrost in deep cold is probably timer-driven, so frequent even when the coil is barely frosted.**
   - NREL tested a cold-climate unit in Alaska [28]. Its factory software defrosted **every 55 min, 8 min each, with no significant frost seen**, and spent about **60 % of time in defrost or recovering from it**.
   - Chamber tests showed defrosts became *more* frequent as it got colder, despite dry air.
   - Software with a 4 h minimum between defrosts gave **65–85 % less defrost runtime**, about **50 % higher COP below −4 °C**, and met load at 11 K (20 °F) colder temperatures [28].
   - A Daikin owner saw defrosts every **30–42 min below about −6 °C** with no visible frost. Settings did not change it [26].
   - Gree's documented (first-generation) rule is 50 min accumulated run plus coil below −4 °C [19]. In deep cold that condition is always met, so the rule acts as a ~50-min timer.

9. **Frost does form in Lithuanian cold.**
   - Median RH on days below −12 °C was **80 % in 2025/26** (79 % over 1991–2024) [16].
   - Critical RH for frosting falls only to about 63 % at −26.5 °C [17].
   - Measured on a Vilnius air-to-water unit [25]: COP 1.98–3.05 at −7…+5 °C. Ignoring frost overstated seasonal performance by about 15 %.

10. **The tank heater can block space heating in deep cold.**
    - Tank-heater Logic 1 (default) never runs the compressor together with a heater [1][6].
    - The leaving-water envelope tops out at **45 °C at −20 °C**, 50 °C at −15 °C and 55 °C at −10 °C [1].
    - So a hot tank or legionella cycle during a cold spell takes the compressor off the slab, or is done by resistance.
    - Gree Poland recommends a tank target of only **43–48 °C** [22].

11. **The one Lithuanian monitored system shows the risk** [13]:
    - Vilnius, Nibe, slab underfloor heating. Days below −12 °C took about 31 % of annual electricity for about 11 % of heat.
    - At −21.9 °C the compressor ran only 7 h, and 140 kWh of electricity went in against 20 kWh of metered heat. That points to resistance taking over.
    - The Lithuanian heat association reported owner complaints that many heat pumps "stopped" near −20 °C in January 2026 and fell back to resistance at 20–25 ct/kWh [24]. It is a district-heating lobby and gave no data, so treat it as anecdote.

12. **Pre-charging the slab helps across a night, not across a cold spell** [calc].
    - 1 K of slab is 6.6 kWh. At −20 °C the shortfall is about 1.0–3.5 kW, so 1 K covers about 2–7 h.
    - Aalborg simulations agree: poorly insulated houses coast **1–5 h**, high-performance houses **>24 h**, and underfloor heating stores more than radiators [33].
    - In the Purdue cold-snap field test (to −20 °C), the MPC **preheated in the warmer afternoon and let the setpoint drop overnight**, specifically to cut resistance heat [29].
    - Purdue's earlier test cut backup energy by 38 % [15].

13. **The biggest cold-weather lever is configuration, not pre-charging** [model, 0.17 kW/K]:
    - heater-replaces-compressor at −7 °C: about 1,170 kWh/season;
    - at −10 °C: about 500 kWh;
    - at −15 °C: about 100 kWh;
    - at −20 °C: about 17 kWh;
    - pre-charging is worth a few tens of kWh per season.
    - These bounds use 1991–2024 day counts. 2025/26 would have been roughly 1.5–2.5 times worse below −10 °C [calc].

14. **A newer Modbus map exposes a maximum compressor frequency (address 72, range 65–85, with "Heat Control Mode" coil 40)** [32]. In deep cold it must be at its maximum or disabled, or it will move the balance point warmer. The same thread had **no owner cold-weather reports** (negative result) [32].

## Detailed findings

### 1. Capacity and COP of the Versati III/IV between −10 and −25 °C (manufacturer tables)

The Versati III split "correction" tables are absolute kW and COP. They agree with the datasheet point A−7/W35 = 6.65 kW, COP 2.81 [1].

**Versati III 10 kW, single-phase (GRS-CQ10Pd/NhH-E)** [1]:

| LWT \ outdoor | −25 | −20 | −15 | −10 | −7 | −2 | +2 |
|---|---|---|---|---|---|---|---|
| W25 kW / COP | 4.09 / 1.80 | 4.94 / 2.27 | 5.89 / 2.70 | 6.75 / 3.42 | 7.22 / 3.96 | 8.08 / 4.68 | 8.93 / 5.40 |
| W30 kW / COP | 3.99 / 1.44 | 4.85 / 1.87 | 5.70 / 2.23 | 6.56 / 2.88 | 7.03 / 3.35 | 7.79 / 3.96 | 8.65 / 4.61 |
| W35 kW / COP | 3.90 / 1.22 | 4.56 / 1.55 | 5.32 / 1.84 | 6.18 / 2.41 | 6.65 / 2.81 | 7.41 / 3.35 | 8.08 / 3.85 |
| W40 kW / COP | 3.90 / 1.04 | 4.56 / 1.40 | 5.32 / 1.69 | 6.18 / 2.20 | 6.65 / 2.52 | 7.41 / 3.06 | 8.08 / 3.60 |
| W45 kW / COP | n/a | 4.56 / 1.22 | 5.32 / 1.48 | 6.18 / 1.98 | 6.65 / 2.23 | 7.41 / 2.70 | 8.08 / 3.17 |

- **8 kW single-phase**, W30, at −10 / −15 / −20 °C: 5.52 / 4.80 / 4.08 kW, COP 2.92 / 2.26 / 1.92 [1].
- **10 kW three-phase**: about 7 % more capacity [1].
- **Versati IV 10 kW**, W30: 7.65 / 6.63 / 5.81 kW, COP 3.13 / 2.47 / 2.02 [4].
- **Envelope** [1]. Heating runs at −25…35 °C ambient. The maximum leaving water falls with ambient:
  - 60 °C at −7 °C or warmer;
  - 55 °C at −10 °C;
  - 50 °C at −15 °C;
  - 45 °C at −20 °C;
  - 40 °C at −25 °C.
- **Nordic variant** [21]:
  - Operating range −25…+35 °C, SCOP 4.70 (10 kW, A+++), built-in **9 kW (3+6) heater**.
  - The listed "min–max" heat output for the 8 and 10 kW is **1.45–14.08 kW**. The test conditions are not stated, and 14 kW is surely at mild ambient with a high frequency limit.
  - That 1.45 kW minimum clashes with this house's measured minimum of about 3.7 kW (see Contradictions).
- **Derate.** The tables do not say whether defrost losses are included. Field "maximum output" tests of other brands found 7–25 % below datasheet, defrost included [12]. I plan with 15 % (assumption).
- **[calc]** From −10 to −20 °C at W30, capacity falls 26 % and COP 35 %. At −20 °C, W30 versus W35 gives +6 % kW and +21 % COP.

### 2. Field evidence in deep cold

**Swiss EnergieSchweiz field programme, coldest day, 14 Feb 2021 (daily means)** [31]:

| System (air-to-water) | T out | Flow | Heating COP (WNG) | Compressor h | Heater kWh |
|---|---|---|---|---|---|
| 15, retrofit, inverter | −5.6 | 32.0 | 2.8 | 16.2 | – |
| 17, retrofit, inverter | −8.7 | 32.9 | 2.7 | 20.2 | – |
| 20, retrofit, fixed speed | −6.0 | 37.8 | 2.6 | 17.7 | – |
| 23, retrofit, inverter | −6.0 | 40.6 | 2.5 | 18.2 (24 h continuous on the cold day) | – |
| 16, retrofit, inverter | −6.3 | 44.2 | 2.1 | 15.4 | 0.5 |
| 12, unrenovated, inverter | −5.4 | 54.1 | 2.0 | 24.0 | – |
| 24, retrofit, inverter | −5.6 | 52.8 | 1.8 | 15.1 | – |
| 8, retrofit, fixed speed | −0.9 | 35.8 | 2.7 | 22.4 | 9.1 |

- The flow-temperature effect at the same cold is large: **32–33 °C gives 2.7–2.8, and 52–54 °C gives 1.8–2.0** [31].
- Heater events were control artefacts:
  - System 8 used its heater after morning defrosts "for comfort", while the unit was cycling again by afternoon.
  - System 16 ran its heater about 10 min.
  - A ground-source unit added heater stage 1 after 5 min and stage 2 after 15 min, then the compressor stopped after 40 min at about −11 °C.
  - The report says neither was needed, and credits the inert floor heating [31].
- Well-sized inverters **ran 24 h continuously** without cycling on that day. Oversized units ran only 8–11 h [31].

**Fraunhofer ISE** [30][10]:
- First two weeks of Feb 2021, 17 air-to-water units (the 3 best, in deep-retrofit houses, excluded): mean efficiency **2.3** at −3.6 °C mean outdoor.
- The slide also shows 2.8 and 1.6 (probably the spread) and −10.2 °C (probably the coldest operating mean). **5 systems** used their heater.
- Long-term: about 50 % of 117 air-to-water systems showed zero heater energy. The average heater share was about 1.2 % of heat (1.3–1.6 % of electricity).
- In WPsmart, high heater use came from wrong parameters, faults and legionella programmes [10].

**Ottawa Gree Flexx** [14] (pass-1 analysis): near-continuous running below −8 °C, about 7 kW at −18 °C, daily COP 1.6–2.0 at −13…−18 °C. Its boundary includes the backup heater.

**Vilnius Nibe** [13] (pass-1 analysis):
- At −10…−15 °C: 20–22 compressor-hours a day and COP about 2 on normal days. Some days reached COP 0.9–1.0, which suggests a resistance supplement.
- At −17…−22 °C: the compressor ran 7–16 h/day, with 72–140 kWh electricity against 20–49 kWh heat.
- The pattern looks like a firmware hand-over to resistance, not a capacity collapse.

**Renewable Heating Hub cold snap, Jan 2024 (forum)** [27]:
- Samsung 16 kW at −7 °C: 166 kWh heat for 69 kWh electricity (COP about 2.4) at about 40 °C flow. It recovered LWT within about 10 min after each defrost.
- Midea 14 kW at −4 °C: 60-min COP 1.69, with **13 defrosts in 12 h** overnight.

**Purdue cold-snap field test (to −20 °C), air-to-air with 9.6 / 14.4 / 19.2 kW resistance stages** [29]:
- Defrost resistance staging was by outdoor temperature: stage I above −9.4 °C, stage II between −9.4 and −15 °C, stage III below −15 °C.
- MPC **lowered the overnight setpoint and preheated in the warmer afternoon** to avoid resistance heat. It kept whole-house current under 90 A on the hardest day.
- Two other observations:
  - During defrost recovery, the setpoint was briefly dropped by about 5 min.
  - A Wi-Fi delay coinciding with a defrost caused the single limit breach.

### 3. How the Gree backup heater is controlled

- **Hardware.**
  - One or two resistance groups after the plate exchanger: 3+3 kW (NhH-E 8/10 kW) or 1.5+1.5 kW (NhH5-E) [1]. Nordic models have 3+6 kW [21].
  - The sensor after the heater ("T-optional water", Word 126) is the main leaving-water control sensor [1][19].
- **Switching.** The manuals say only that the heater runs according to outdoor temperature, compared against T-Eheater [1][2][5][23].
  - Versati II+: T-Eheater −22…18 °C, default −7 °C. T-Extraheater (second group), default −15 °C. T-HP max (the heat pump's maximum water-out without the heater) 40–50 °C, default 50 °C [23].
  - R32 Modbus map: Word 14, −20…18 °C, default −15 °C [7].
  - No delay, hysteresis, demand or run-time condition is documented in any of the five Gree manuals read [1][2][3][5][23].
- **Logic (Word 37)** [1][3][7]:
  - **Logic 1**: the heat pump and the heater never run together. The Versati IV example says that below T-Eheater the compressor stops and the heater runs [3].
  - **Logic 2**: both run together below T-Eheater.
- **Defaults** [1][2][5][6][7][23]: Off (III/IV panel tables; II+ manual), "1 group" (II, kievclimate copy), "1 set" (R32 Modbus map). An HA user's ESPHome map lists a 2 °C default for register 14, which looks misaligned [32]. **Only a register read settles it.**
- **Exclusions** [1][2]: the optional heater and the tank heater are never on together. The optional heater and "other thermal" (T-Other, default −20 °C) are mutually exclusive.
- **Emergency mode** [1][23]:
  - Heating by heater only, after a compressor fault.
  - It quits on a flow-switch fault, heater weld protection or a leaving-water sensor fault.
  - On II+ it is memorized after a power cut. On III it is not [1][6][23].
- **How others gate it:**
  - **Panasonic** [9]: all of these must hold:
    - outdoor temperature below its setpoint;
    - the heat pump has run 30 min;
    - LWT at least 8 K below setpoint;
    - at least 20 min since the last heater stop.
    - It stops when LWT is within 2 K of setpoint.
  - **Daikin** [8]: only below the "equilibrium temperature" (default 0 °C, settable to −15 °C), plus during defrost and on failure.
  - **Polish guide example** [34]: below −10 °C, compressor running ≥ 3 h, water ≥ 5 K below setpoint. It adds that building inertia can delay heater need by hours after the bivalent point, which designers put at about −8 to −13 °C.

### 4. Tank heater in cold weather

- **T-HP max** (40–55 °C, default 50 °C) is the most the heat pump attempts for the tank. Any setpoint above it is finished by the tank heater [1][7][23].
- **Tank-heater Logic 1 (default):** the compressor and any heater are never on together [1][6]. **Logic 2:** the tank heater may finish the tank while the compressor returns to space heating. It needs DHW priority and Tset ≥ T-HP max + ΔT + 2 [1][6].
- **Envelope collision [calc from 1].** At −15…−20 °C the heat pump can make only 45–50 °C LWT. A coil tank needs LWT 5–8 K above tank temperature, so the realistic tank ceiling is **about 38–42 °C**. What the firmware does with a 48 °C target at −20 °C (long run, protection or heater take-over) is undocumented.
- **Gree Poland's recommended settings** [22]:
  - tank 43–48 °C;
  - UFH water 30–35 °C;
  - "ΔT-heating" 2–4 °C. This is the restart hysteresis; this house uses 4.
  - "Fast hot water" runs the coil and the tank heater together.
- **Field echo.** In Vilnius, DHW electricity doubled to 17–20 kWh/day on −17…−22 °C days [13]. One Swiss system with daily heater legionella had the worst DHW efficiency (1.4) [31].

### 5. Defrost between −10 and −20 °C

- **Physics.** Frost forms whenever the coil is below 0 °C and below the dew point.
  - Critical RH falls from 80.6 % at +1 °C to 62.75 % at −26.5 °C (variable-speed unit, load-dependent). Frosting is fastest near −10 °C [17].
  - In Vilnius, days below −12 °C average **79–80 % RH** [16]. So frost still forms, but slowly, because absolute humidity at −15 °C is about a quarter of that at 0 °C [calc].
  - A Lithuanian measurement found frost from below +3.5 °C at 88 % RH, with defrosts lasting about 5 min [18].
- **What firmware actually does in deep cold is often timer-like.**
  - NREL found defrosts every 55 min, 8 min each, with no significant frost. Together with recovery (about 25 min for the indoor coil to stabilize) that is about 60 % of the time. A 260 W drain-pan heater ran 33–50 % of the time.
  - A software change (minimum 4 h between defrosts; pan heater only during defrost plus 5 min) gave 65–85 % less defrost runtime and 72–112 W less average power. COP rose about 50 % below −4 °C [28].
  - Chamber: defrost frequency *rose* at colder temperatures despite dry air [28].
  - The Daikin owner [26] reported defrosts every 30–42 min below −6/−7 °C. He saw no frost, and setting changes had no effect. Other users suggested only that running gently helps.
- **Gree implementation** [1][19]:
  - "Smart" defrost is claimed: less when frost is light. Entry uses the coil "defrost" sensor and suction pressure.
  - During defrost the fan stops and the 4-way valve reverses. Manual defrost ends at a coil temperature of 20 °C or after 10 min.
  - The first-generation rule (≥ 50 min accumulated run **and** coil < −4 °C; exit after 10 min / coil > 15 °C) behaves as a 50-min timer in deep cold [calc]. Whether the III's "smart" logic avoids that is unverified.
  - On a 16 kW Versati III, quiet mode alone gave defrost about every 52–56 min at +2…+5 °C [32].
  - Gree requires ≥ 5 L/kW of water for defrost reliability [1].
- **Cost [calc, low confidence].** If the Versati also defrosts about every 50–55 min of run for about 5–10 min at −10…−20 °C, deep-cold output drops about 10–15 %. That is consistent with the 7–25 % field shortfall [12].
- **Backup during defrost.** Daikin, Panasonic and the Purdue unit all use resistance in defrost [8][9][29]. No Gree document says the optional heater does. The Swiss "after-defrost heater" case shows how a comfort rule can make that expensive [31].

### 6. How often the cold tail occurs (Vilnius, ERA5 via Open-Meteo) [16] [calc]

| Metric (days/season) | 1991–2024 avg | 2015–2024 avg | Worst 1991–2024 | **2025/26** |
|---|---|---|---|---|
| Daily mean < −10 °C | 10.2 | 5.6 | 28 | **27** |
| Daily mean < −15 °C | 3.3 | 1.9 | 13 | **6** |
| Daily mean < −20 °C | 0.9 | 0.4 | 6 | **1** |
| Daily min < −15 °C | 7.8 | — | — | **19** |
| Daily min < −20 °C | 2.5 | 1.5 | — | **4** |
| Longest spell, mean < −10 °C | median 2, p90 7, max 18 | — | — | **14** |

- In 2025/26, January averaged −10.0 °C and February −7.6 °C. The coldest daily mean was −21.7 °C and the absolute minimum −27.3 °C.
- The Lithuanian heat association gives January 2026 as −9 °C against +2 °C in January 2025, which means about 61 % more heating demand. Wholesale electricity averaged 152 €/MWh against 89 €/MWh a year earlier [24].
- **Diurnal range** on days below −12 °C: median 6.6 K. Afternoons are about 3 K warmer than the daily mean, worth about +0.4 kW capacity and +8–10 % COP at W30 [1][16] [calc].
- **Caveat.** ERA5 grid values smooth extremes. Rural clear nights run 1–3 K colder.

### 7. Energy at stake [model]

**Model:** load = UA × (22 − Tmean). Heat-pump supply = min(load, W35 table × derate). The remainder is resistance. Day counts are 1991–2024.

| Quantity | 0.14 kW/K | 0.17 kW/K | 0.20 kW/K |
|---|---|---|---|
| Balance point (table / 15 % derate) | −17 / −14 °C | −13 / −10 °C | −10.5 / ≈ −8 °C |
| Heat deficit, avg / worst, kWh/season (table capacity) | 50 / 333 | 149 / 729 | 348 / 1227 |
| Same with 15 % derate | 107 / 553 | 296 / 1043 | 630 / 1691 |

**Heater-replaces-compressor threshold, 0.17 kW/K:**

| Threshold | Extra electricity |
|---|---|
| −7 °C | 1,170 kWh/season (worst 2,850) |
| −10 °C | 500 kWh |
| −15 °C | 100 kWh |
| −20 °C | 17 kWh |

These are lower bounds, since the heater reacts to instantaneous temperature. With 2025/26's 27 days below −10 °C (against an average of 10.2), the −10 °C row would have been about 1,000–1,300 kWh [calc].

**Slab pre-charge (6.6 kWh/K):**
- Heating 1 K at −5 °C (COP about 3.4) instead of at −20 °C (COP about 1.9, or 1.0 with resistance) saves about 1.6–4.7 kWh gross.
- The warmer house loses about 0.5–1 kWh more.
- **Net: about 1–4 kWh per event.** It bridges about 2–7 h of deficit, not a 14-day spell.

## What this means for controlling this house

Confidence: H = high, M = medium, L = low.

1. **Read the heater configuration first (H that it matters).**
   - Poll Word 3 (sets), Word 14 (T-Eheater), Word 37 (heater logic), Word 36 (tank-heater logic), Word 16 (T-HP max) and, if present, address 72 / coil 40 (frequency limit) [7][32].
   - Log coils 171/172 (backup heaters), 173 (tank heater), 80 (compressor) and 86 (defrost), plus Word 143 (Hz).
   - Test on the first night below T-Eheater: does coil 80 drop while 171 rises? If yes, Logic 1 is replacing the compressor. That is the largest single cold-weather loss (500–1,300 kWh in a winter like 2025/26).

2. **Static settings (M):**
   - **Logic 2** (the heater can only add to a running compressor).
   - **T-Eheater at its minimum (−20 °C)**, or heater **Off** (Word 3 = 3) if the external gate in item 3 is built.
   - Set any compressor frequency cap to its maximum, or disable it, whenever outdoor temperature is below about −5 °C.
   - Keep quiet mode off in cold weather; it cuts fan speed and raises defrost frequency [32].
   - Write these once, not repeatedly (EEPROM).

3. **External demand gate for the heater (M), modelled on Panasonic, Daikin and the Swiss lessons [8][9][31][34].**
   - Enable 1 set (Logic 2) only when **all** hold:
     - outdoor temperature below about −12 °C;
     - compressor at or near its maximum Hz for ≥ 60–180 min;
     - room below target − 0.7 K and still falling;
     - the deficit persists outside defrost and its 15-min recovery window.
   - Disable when the room is back to target − 0.3 K or outdoor temperature rises above −10 °C. Use a minimum 30 min on/off.
   - **Never trigger the heater on post-defrost LWT dips**; the slab buffers those.
   - Test: zero heater minutes on any day above −15 °C. On colder days, heater kWh should be at most the modelled deficit.

4. **In deep cold, minimum useful flow and continuous running (H).**
   - Below the balance point the compressor is at full output anyway. W35, W40 and W45 give the same kW [1], while 32 °C versus 52 °C flow is COP 2.8 versus 1.9 in the field [31].
   - Write the lowest LWT that keeps the compressor at maximum, roughly return + 5–7 K.
   - Expect 0–3 starts a day and up to 24 h of running. That is the *desired* state [14][31].
   - Do not write 39 °C at −15 °C "to catch up".

5. **DHW in cold spells (M-H):**
   - Before a forecast spell (daily mean below −10 °C), heat the tank to about 48–50 °C in the warmest afternoon hour [22].
   - During the spell, set the tank to about 40–42 °C, at most one cycle a day, in the afternoon.
   - **Block legionella runs** when the forecast minimum is below about −10 °C. Under Logic 1 they stop space heating [1][6].

6. **Slab pre-charge before cold *nights* (M direction, L value).**
   - When the next 24 h will be below the balance point, raise the room target +0.5 K in the preceding afternoon, while it is 3–8 K warmer. Then let the room slide to about 21.5 °C overnight before any heater is allowed. This is what the Purdue MPC did [29].
   - Worth a few kWh per event. It does not help across multi-day spells like the 14-day spell of 2025/26.
   - Cap pre-charge flow at about 35 °C.

7. **Defrost (M):**
   - Mask coil 86 plus about 15 min from model fitting and from any heater or setpoint logic.
   - Keep every UFH loop open (≥ 50 L in circuit) [1].
   - Log defrost interval against outdoor temperature and RH at −10…−20 °C.
   - If intervals sit at about 50–55 min whatever the humidity, the unit is timer-driven, as NREL found [28]. That is a firmware issue to raise with the distributor, not something Modbus can fix.

8. **Priority (M).**
   - In an average winter, a correctly configured heater makes days below −15 °C a small slice of annual electricity (about 100–450 kWh).
   - Fix mild-weather cycling and flow temperature first.
   - **The exception is the heater configuration.** If it is wrong, it outranks almost everything else in a 2025/26-type winter.

## Contradictions and open questions

- **Heater default:** Off [1][2][6][23], "1 group" [5], "1 set / −15 °C" [7], and an ESPHome map with a 2 °C default [32]. Unresolved without a register read.
- **Logic 1 on Versati III:** "cannot start at the same time" [1]. The IV says explicitly that the compressor stops below T-Eheater [3]. Whether III's Logic 1 merely interlocks (heater only while the compressor is off) is untested.
- **Second-group staging, hysteresis and minimum times** are undocumented for III/IV. II+ had a separate T-Extraheater threshold, default −15 °C [23].
- **Minimum output:** the Nordic sheet lists a 1.45 kW minimum [21], while this house measured about 3.7 kW. Possible reasons:
  - the sheet's minimum is at a different rating point;
  - the firmware's minimum frequency is higher in heating;
  - the measurement includes start-up overshoot.
  - This matters for mild-weather cycling, not for G6.
- **Table versus field capacity.** The Ottawa Gree was 5–15 % below the table [14]. Other brands were 7–25 % below datasheet [12]. NREL showed the defrost algorithm alone can swing capacity by about 50 % at extreme cold [28]. The Versati balance point is therefore uncertain by about ±3 K.
- **Defrost rule on the Versati III "smart" logic at −10…−20 °C:** undocumented. Gree markets it as frost-adaptive [1]. The NREL and Daikin evidence says many firmwares become timer-like when cold [26][28]. Needs logging.
- **Does the Versati use the backup heater in defrost?** No Gree source says so. Daikin, Panasonic and others do [8][9][29].
- **The Lithuanian "heat pumps stopped at −20 °C" claim** [24] comes from a district-heating association and gives no data. The Vilnius Nibe [13] is consistent with it, but its metadata says no backup heater is metered.
- **The cold tail is not shrinking reliably.** 1991–2024 trends suggested fewer cold days, but 2025/26 nearly equalled the worst season [16]. Plan control for a 2025/26-type winter.
- **No Versati field data below −10 °C was found.** The HA thread has none [32], and the Polish forums were unreachable. The owner's own logging this winter will be the first.

## Sources

1. Air-to-water Heat Pump Split Versati (Versati III, R32) Service Manual - Gree Electric Appliances (via Gree Hungary) - c. 2020-22 - https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iii/versati%20iii%20split%20%E2%80%93%20service%20manual.pdf - manufacturer - Full capacity/COP tables −25…35 °C × W25–60; operating envelope; optional heater by outdoor temperature; Logic 1/2; tank-heater logic; T-HP max; defrost hardware; 5 L/kW for defrost; heater sizes.
2. Versati III All-in-One Service Manual - Gree (via Gree Hungary) - c. 2020-22 - https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iii/versati%20iii%20all%20in%20one%20%E2%80%93%20service%20manual.pdf - manufacturer - Same heater and tank logic text and defaults as [1]; 8 kW capacity table.
3. VERSATI IV Split Type Air-to-Water Heat Pump Service Manual - Gree - c. 2023 - https://gree-climat.com.ua/pdf/manual_versatti_4.pdf - manufacturer - Worked example: below T-Eheater, Logic 1 stops the compressor and runs the heater; Logic 2 runs both.
4. Versati IV Monobloc Service Manual - Gree (via Gree Hungary) - c. 2023 - https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iv/versati%20iv%20monoblokk%20%E2%80%93%20service%20manual.pdf - manufacturer - Versati IV 10 kW capacity/COP at −25…−10 °C; "smart defrost" claim; manual defrost exit 20 °C / 10 min.
5. Versati II (2016) service manual, Unit Control chapter - Gree (hosted by kievclimate) - 2016 - https://man.kievclimate.com/man/Gree/Versati/Versati%20II/Versati%202016%202-f/4.Unit%20Control.pdf - manufacturer - Assistant heater "1 group"; T-Eheater −22…18, default −7 °C; T-Extraheater −15 °C.
6. Control Panel for the Versati Heat Pump (CopMax High Power rebadge) - Gree / NH Bioservice - 2024 - https://www.nhbioservice.dk/wp-content/uploads/2024/09/Panel-manual-CopMax-High-Power-engelsk.pdf - manufacturer - Commissioning defaults (heater Off; tank Logic 1; T-HP max 50 °C); emergency-mode conditions.
7. Modbus Protocol V1.5 for the Versati (R32) - Gree (hosted by kievclimate) - c. 2020 - https://man.kievclimate.com/man/Gree/Versati/Versati%20III/R32_Versati%20Modbus%20V1.5.pdf - manufacturer - Words 3/14/15/16/35–37 with defaults (1 set, −15 °C, Logic 1); heater, tank-heater and defrost status bits.
8. Daikin Altherma LT split Installer Reference Guide - Daikin Europe - c. 2017 - https://www.daikin.eu/content/dam/document-library/Installer-reference-guide/heat/air-to-water-heat-pump-low-temperature/ERQH011-016BV3-BW1,%20ERLQ011-016CV3-CW1,%20EHVZ-CB3V_4PEN401677-1A_Installer%20reference%20guide_English.pdf - manufacturer - Backup only below the equilibrium temperature (default 0 °C), during defrost and on failure.
9. Aquarea WH-SXC09/12F service manual - Panasonic - 2013 - https://www.panasonicproclub.com/uploads/CZ/catalogues/aquarea/service-manual/SXC9,12_F_E8_service%20manual_PAPAMY1311028CE.pdf - manufacturer - Demand-gated heater: 30 min run, LWT ≥ 8 K below setpoint, 20 min re-arm; heater during de-ice.
10. WPsmart im Bestand – Schlussbericht - Fraunhofer ISE - 2020 - https://wp-monitoring.ise.fraunhofer.de/wpqs-im-bestand/download/Berichte/BMWi-03ET1272A-WPsmart_im_Bestand-Schlussbericht.pdf - field data - Heater energy about 2 % of compressor energy; high use only from wrong parameters, faults, legionella.
11. Electrification of Heat: Interim Heat Pump Performance Data Analysis - Energy Systems Catapult - 2023 - https://es.catapult.org.uk/wp-content/uploads/2023/03/EoH-Interim-Heat-Pump-Performance-Data-Analysis-Report-1.pdf - field data - Coldest-day median COP 2.44 at −0.4 °C (context).
12. Max output testing - OpenEnergyMonitor - c. 2024-25 - https://docs.openenergymonitor.org/heatpumpmonitor/max_output_testing.html - field data - Sustained output across defrosts 7–25 % below datasheet.
13. HeatpumpMonitor.org system 887 (Vilnius, Nibe AMS 20-6, slab UFH) - OpenEnergyMonitor / owner - 2025-26 - https://heatpumpmonitor.org/system/stats/daily?id=887 - field data (own analysis) - Cold-day electricity/heat shares; 7 compressor-hours at −21.9 °C; 140 kWh electricity versus 20 kWh heat.
14. HeatpumpMonitor.org systems 251 (Ottawa, Gree Flexx), 644, 938, 1096 - OpenEnergyMonitor / owners - 2024-26 - https://heatpumpmonitor.org/system/stats/daily?id=251 - field data (own analysis) - Gree compressor-based unit at COP 1.6–2.0 at −13…−18 °C, near-continuous running.
15. Field demonstration of predictive heating control for an all-electric house in a cold climate - Pergantis et al. - 2024 - https://arxiv.org/abs/2402.07032 - field data - MPC cut backup energy 38 %; preheating ahead of high loads; fewer defrosts.
16. Historical weather API (ERA5), Vilnius, daily 1991-01-01 to 2026-04-30 - Open-Meteo - accessed 2026-11-06 - https://archive-api.open-meteo.com/v1/archive?latitude=<site>&longitude=<site>&start_date=2025-10-01&end_date=2026-04-30&daily=temperature_2m_mean,temperature_2m_min,relative_humidity_2m_mean&timezone=Europe%2FVilnius - field data (reanalysis, own analysis) - Cold-day counts, spell lengths, RH on cold days, including the 2025/26 season.
17. A new frosting map of variable-frequency ASHP in severe cold region considering heating load - Wei et al., Renewable Energy 161 - 2020 - https://ideas.repec.org/a/eee/renene/v161y2020icp184-199.html - lab/field rig (abstract) - Critical RH 80.6 → 62.75 % from +1 to −26.5 °C; fastest frosting near −10 °C.
18. Experimental Investigation of Frost Formation Influence on an ASHP Evaporator - Kropas, Streckienė, Bielskus, Energies 14(18) - 2021 - https://ideas.repec.org/a/gam/jeners/v14y2021i18p5737-d633785.html - lab/field (abstract) - Lithuanian test: frost below +3.5 °C at 88 % RH; defrost about 5 min.
19. Internal sweep notes 01, 08, 09, 13 - this project, docs/research/notes/ - 2026 - local files - secondary - First-generation Gree defrost parameters; Modbus coil and word numbers; house parameters.
20. Gree Versati III air to water heat pump (thread, page 3) - Home Assistant Community - 2022-26 - https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916?page=3 - forum - Owners map Optional E-Heater and tank-heater registers; no cold-weather reports.
21. Versati Nordic product sheet (Swedish) - Scanmont AB (Gree distributor) - 2024 - https://cdn.abicart.com/shop/18368/art95/203737395-bb4351-Versati_svenska_240618_till_hemsidan.pdf - manufacturer/distributor - Nordic Versati: operation to −25 °C; built-in 9 kW (3+6) electric backup; min–max output 1.45–14.08 kW (10 kW); SCOP 4.70.
22. Skrócona instrukcja eksploatacji pompy ciepła Gree Versati - Free Polska (Gree Poland) - 2024 - https://gree.pl/content/uploads/2024/04/skrocona-instrukcja-eksploatacji-pompy-ciepla-gree-versati.pdf - manufacturer - Recommended UFH water 30–35 °C, tank 43–48 °C, heating ΔT (restart hysteresis) 2–4 °C; "fast hot water" uses coil + tank heater together.
23. Air-to-water Heat Pump Split Versati II+ Service Manual - Gree (hosted by gree.at) - c. 2017 - http://gree.at/uploads/servisni/servisni%20manual%20gree%20en%20versati%20ii+.pdf - manufacturer - Assistant heater options 1 group / 2 groups / Off, default Off; T-Eheater default −7 °C; T-Extraheater −15 °C; T-HP max 40–50 °C; emergency mode quits on flow, weld or sensor faults.
24. Šaltojo sausio šildymo pamokos (LŠTA pranešimas) - V. Lukoševičius / Lithuanian District Heating Association - 2026 - https://lsta.lt/wp-content/uploads/2026/02/260204_LSTA-pranesimas-Sildymo-pamokos-saltaji-sausi.pdf - industry note (interested party) - January 2026 −9 °C mean against +2 °C in 2025; electricity 152 against 89 €/MWh; anecdotal reports of heat pumps stopping near −20 °C and falling back to resistance.
25. Analysis of air-to-water heat pump in cold climate: comparison between experiment and simulation - Januševičius & Streckienė (VGTU), Mokslas – Lietuvos ateitis - 2015 - https://journals.vilniustech.lt/index.php/MLA/article/view/2743 - field data + simulation (abstract) - Vilnius unit COP 1.98–3.05 at −7…+5 °C; ignoring frost overstates seasonal performance by about 15 %.
26. Daikin Altherma 3 R 8kW frequent defrosts when below ~-6C-7C - OpenEnergyMonitor community - 2024-25 - https://community.openenergymonitor.org/t/daikin-altherma-3-r-8kw-frequent-defrosts-when-below-6c-7c/27913 - forum (field observation) - Defrosts every 30–42 min below about −6 °C at 70–90 % RH with no visible frost; settings had no effect.
27. Performance in the current cold snap (page 2) - Renewable Heating Hub forum - 2024 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/performance-in-the-current-cold-snap/paged/2/ - forum (owner data) - Samsung 16 kW COP about 2.4 at −7 °C, 40 °C flow, fast defrost recovery; Midea 14 kW COP 1.69 at −4 °C, 13 defrosts in 12 h.
28. Detailed Air-Source Heat Pump Evaluation for Very Cold Climates (BTO Peer Review) - J. Munk, NREL - 2024 - https://www.energy.gov/sites/default/files/2024-11/bto-peer-2024_32264-detailed-air-source-hp-evaluation-for-very-cold-climates-munk.pdf - lab + field data - Factory defrost every 55 min, 8 min each, with no frost; about 60 % of time in defrost or recovery; more defrosts when colder despite dry air; 4 h minimum interval gave 65–85 % less defrost runtime and about 50 % higher COP below −4 °C.
29. Protecting residential electrical panels and service through model predictive control: a field study - Pergantis et al. (Purdue) - 2024 - https://arxiv.org/html/2409.04884v2 - field data - Cold snap to −20 °C; resistance defrost stages by outdoor temperature; MPC preheated in afternoon and lowered night setpoint to limit resistance; defrost-recovery handling.
30. Wärmepumpen – Potenziale und Hindernisse (presentation) - M. Miara, Fraunhofer ISE - 2022 - https://www.gebaeudeforum.de/fileadmin/gebaeudeforum/Downloads/Netzwerk/2022_Netzwerktagung/Marek_Miara.pdf - field data (summary slides) - Feb 2021 cold wave: 17 air-to-water units at mean efficiency 2.3 at −3.6 °C, 5 used heaters; about 50 % of 117 systems with zero heater energy.
31. Feldmessungen von Wärmepumpen-Anlagen, Heizsaison 2020/21 - Prinzing, Berthold, Bertsch, Eschmann (OST) for EnergieSchweiz/BFE - 2021 - https://pubdb.bfe.admin.ch/de/publication/download/10654 - field data - Coldest-day table: COP 2.7–2.8 at 32–33 °C flow against 1.8–2.0 at 52–54 °C, at −5…−9 °C; unnecessary comfort-driven heater use (5 min / 15 min staging; after defrost); slab inertia; continuous 24 h inverter running.
32. Gree Versati III Air to water heat pump (thread, pages 5 and 7) - Home Assistant Community - 2026 - https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916?page=7 - forum - Modbus v2.2 max compressor frequency (address 72, 65–85, coil 40); quiet mode gives defrost every 52–56 min at +2…+5 °C; no owner cold-weather reports (negative result).
33. Influence of envelope, structural thermal mass and indoor content on the building heating energy flexibility - Johra, Heiselberg, Le Dréau, Energy and Buildings - 2019 - https://vbn.aau.dk/ws/files/290247579/Influence_of_envelope_structural_thermal_mass_and_indoor_content_on_the_building_heating_energy_flexibility_accepted_manuscript.pdf - paper (simulation) - Low-insulation houses coast 1–5 h without heat, high-performance houses >24 h; UFH gives more flexibility than radiators.
34. Przy jakiej temperaturze w pompie ciepła włącza się grzałka elektryczna? - Muratordom - c. 2023 - https://muratordom.pl/instalacje/pompy-ciepla/przy-jakiej-temperaturze-w-pompie-ciepla-wlacza-sie-grzalka-elektryczna-czy-mozna-ja-wylaczyc-jak-dziala-grzalka-w-pompie-ciepla-aa-DLrf-BgTG-vkbQ.html - blog (trade press) - Example demand gate: below −10 °C, compressor ≥ 3 h, water ≥ 5 K below setpoint; bivalent point typically −8…−13 °C; inertia delays heater need by hours.
35. Combining an air-to-water heat pump with a heated floor slab - J. Siegenthaler, PM Engineer - c. 2023 - https://www.pmmag.com/articles/104195-john-siegenthaler-combining-an-air-to-water-heat-pump-with-a-heated-floor-slab - blog (engineer) - Slab as the buffer, with constant floor circulation; nothing on cold-weather backup or defrost (negative for G6).
