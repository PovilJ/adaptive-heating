# Gap R2-G3: When is it better to store PV surplus in the hybrid battery and run the heat pump from it later, and when is it better to put the surplus into the slab immediately? This needs battery round-trip efficiency at heat-pump-sized loads (0.8-3 kW), inverter idle losses, the degradation cost per cycled kWh, and the battery's capacity relative to winter PV.

> Research date: 2026-11-06. Follow-up researcher for gap R2-G3.
>
> **Method limits (read first).** The shared web-search budget for this run was already used up when I started. Both searches I tried were refused, so **0 searches actually ran** and none of the non-English queries could be run. I worked only from direct fetches of primary sources whose URLs I already knew or found by following links inside them. I read 15 sources (listed below); the most important one, the 66-page HTW Berlin *Stromspeicher-Inspektion 2026* report, I downloaded and text-extracted locally so its numbers come from the text, not from a summary.
>
> I did not read this repository's code or docs. I read only sibling notes in this folder (01, 05, 10, gap-r1-G5, verify-r1-C8) to avoid repeating them. References to them are written [N01], [N05], [N10], [NG5], [NC8].
>
> Numbers marked **[C]** are my own arithmetic on the cited figures and the house data in the brief (H ≈ 0.17 kW/K, slab C ≈ 6.6 kWh/K, P_min ≈ 3.75 kW thermal). The owner's battery brand, usable capacity, inverter model and battery location are **unknown**, so every battery number below is a range across tested products.

## Summary

1. **Electrically, the slab is a small battery.** Each 1 K of room/slab swing the owner accepts stores about 6.6 kWh of heat. At a COP of 3.3-4.5 that is only **≈1.5-2 kWh of electricity per K** [N05][C]. A typical 10-15 kWh home battery can shift **5-10 times more electricity** than a ±0.5 K comfort band. On sunny days from February to April the two are not rivals: the slab fills in an hour or two, and the battery takes what is left.
2. **The real rival of the battery is pushing the compressor harder, not the slab.** Absorbing PV surplus fast by running the Versati at high speed costs about **30-40 % more electricity per kWh of heat** than running it at minimum speed [N01]. A slab top-up also adds about 2.2 % COP loss per K of extra flow [N01] and 4-14 % storage loss [NC8]. Together that is a **≈25-35 % penalty**, about three times the battery's loss [C].
3. **A good hybrid battery returns ≈87-92 % of PV energy to a 1-3 kW load. A poor one returns ≈73-80 %.** In lab tests of 12 current systems [1], the averages are:
   - PV-to-battery charging: 92-98.2 %;
   - battery (cell plus BMS) efficiency: 87.9-97.1 %;
   - battery-to-AC discharge: 91.2-97.8 %.

   The product of the three gives the range above [C]. A heat pump drawing 0.8-3 kW sits in the efficient part of the inverter curve: at 500 W one inverter already reaches 90 %, and at its 10 kW rating it reaches 97.8 % [1].
4. **The battery is inefficient for the house's night base load, not for the heat pump.** At 100 W output, discharge efficiency ranges from **54-66 % to 86 %**, depending on the inverter [1][3]. At 300 W, 6-21 % of the battery's output is still lost [1]. 72 % of night-time power flows in German homes are below 300 W [1]. When the heat pump runs at night, the inverter works at higher power and becomes more efficient. Draining the battery into a 150 W base load is the costly use.
5. **Idle losses are a fixed winter tax.** Standby draw with an empty battery ranged from **4 to 64 W** in the 2026 test [1][2], and 2-64 W in earlier years (mean 13 W across 20 systems in 2024) [5][6]. The battery's BMS adds up to **37 W**, and this is not counted in the lab ratings [1]. At 30 W, that is **0.7 kWh/day** [C]. In December, when the battery cycles little, this can eat a large share of what it stores.
6. **Wear cost per cycled kWh is about 0.02-0.10 €/kWh for an LFP pack used ≤250 cycles/year, and up to ≈0.25 €/kWh in the worst case** [C]. Inputs:
   - installed price 400-1000 €/kWh (Germany 2024) [10];
   - warranty throughput 2.4-8.5 MWh per kWh of capacity, or 3,500-10,000 cycles, to 60-85 % remaining capacity [1];
   - LFP cell life 2,500-9,000 equivalent full cycles in the lab [8];
   - measured field fade of about **2-3 percentage points per year** at about 200 cycles/year [7].

   If calendar ageing ends the battery's life first, extra cycles cost close to nothing. That is likely at ≤200 cycles/year over 10-15 years.
7. **Winter PV hardly needs storing at all.** From November to January the median PV yield is 6.7-11.6 kWh/day. The heat pump alone needs 19-26 kWh of electricity per day [N10]. Field batteries do "almost no" cycling in winter [7]. The battery-versus-slab question matters on **sunny days in February-April and October-November**.
8. **Decision rule by regime [C]:**
   - **Mild weather (heat load below P_min, so the unit must cycle):** put the unit's on-blocks into the PV window at minimum output. Heat out per PV kWh is about **1.0-1.1×** the night value. Through the battery it is about **0.75-0.9×**.
     → **Slab first.**
   - **Cold weather (heat load ≥ P_min, so the unit runs continuously):** there is no off-time to move. Absorbing surplus means speeding up, which gives about **0.7×**. Battery to the heat pump at night gives about **0.87×**.
     → **Battery first. Never speed up for PV.**
9. **The optimisation literature lands on the same split.** A mixed-integer optimiser of a German house with a modulating air-source heat pump, underfloor heating, hot-water tank, PV and battery [9]:
   - heated the floor on PV at peak-COP hours in October and November;
   - otherwise kept the floor at the lower comfort bound just before PV started;
   - charged the battery only to what was needed until the next PV, and exported the rest.

   Maximising self-consumption raised energy use by 2 % and cut profit by 9 %, because of extra storage losses [9].
10. **Lithuanian net settlement makes the grid a third "battery".** Under ESO's returned-energy scheme, a kWh drawn back costs **0.0726 €/kWh** and loses no energy [N10]. That is in the same range as the physical battery's wear plus loss: about 0.03-0.12 €/kWh [C]. Under that scheme, filling the battery to run the heat pump later is roughly break-even. It is worth it only with an efficient inverter and a pack that is limited by calendar ageing rather than cycles.
11. **Do not grid-charge the battery to run the heat pump unless the price spread clearly beats the losses.** For an example 25 → 35 ct/kWh spread, HTW calculates that the system efficiency must be **≥ 71 %**, and not every tested system reaches it [1][2]. Lithuanian night-to-evening spreads of about 0.12-0.15 €/kWh [N10] pass that bar only after wear. Shifting heat in the slab (blocking 17-21 h) does the same job with no wear.
12. **Treat any battery figure as unverified until it is measured on this house.** The HTW lab tests show a factor of 3.5 in total losses between the best and worst tested systems (SPI losses 3.0 % vs 10.7 %) [1]. Datasheet peak efficiencies are not comparable between products [1]. The owner's own inverter logs (PV in, battery in/out, house load, grid) can give his real round-trip efficiency within a week.

## Detailed findings

### 1. Battery round-trip efficiency at heat-pump-sized loads

**Lab data from HTW Berlin / KIT / AIT / ZHAW, tested to the "Efficiency Guideline for PV Storage Systems" [1][4].**

Battery efficiency (cell plus internal DC/DC, measured over 6 full cycles):
- 87.9 % (worst, system I1) to 97.1 % (best, Fox ESS EQ3300).
- 6 of 12 systems are above 95.7 %.
- Built-in DC/DC converters reduce it [1].
- Earlier years ranged from 92.9 % to 97.8 % [6], and the worst system in 2024 was 87.9 % [5].

Mean conversion efficiencies along each power path [1]:

| Path | Best | Worst | Comment |
|---|---|---|---|
| PV → battery (PV2BAT, DC-coupled) | 98.2 % (Kostal G3) | 92 % (anonymous H1) | |
| AC → battery (AC2BAT, grid charging) | > 97.4 % (SAX, Fox, RCT) | 94.8 % (Kostal 4.6 kW) | |
| Battery → AC (BAT2AC) | 97.8 % (RCT) | 91.2 % (H1) | Widest spread: 6.6 percentage points |
| PV → AC (PV2AC, direct use) | 98.2 % (Fox) | — | 5 of 9 hybrids above 96.9 % |

**Round trip for "store now, run the heat pump tonight" [C].** Multiply PV2BAT × battery × BAT2AC:
- best case: 0.982 × 0.971 × 0.978 ≈ **0.93**;
- typical class-A system: about 0.96 × 0.955 × 0.965 ≈ **0.885**;
- worst tested: 0.92 × 0.879 × 0.912 ≈ **0.74**.

Using PV directly costs only the PV2AC step (about 0.97-0.98). So, relative to direct use, the battery path loses about **5-10 %** with a good system and up to **24 %** with a poor one.

The often-quoted round-trip figures are AC-to-AC:
- Tesla Powerwall 2 is rated 90 % at 3.3 kW and 25 °C. One measured value was 88 %, with ±2-3 % seasonal variation [13].
- Fraunhofer ISE's cost study assumes 90 % [10].

These agree with the HTW product range.

**Part-load efficiency: where heat-pump loads sit.** Inverter losses split into a constant idle part and a part that grows with load [1]:
- **One 10 kW hybrid (Kostal G3, B4):** the constant idle part is about **50 W**. So 100 W out needs 150 W in from the battery (66 %); at 500 W it is already **90 %**; at 10 kW the loss is 228 W (97.8 %) [1].
- **10 kW hybrids at 100 W output:** RCT 86 %, Fronius GEN24 74 %, Fox 73 %, Kostal 66 %, the worst anonymous unit about 54 % [1][3].
- **At 300 W output,** 6-21 % of battery power is still lost [1].
- **Small (4.6 kW) systems** pass 90 % at 167 W (SAX), 280 W (SMA) and 351 W (Kostal) [1].

**What this means for this house [C].**
- The Versati draws about 0.8-1.3 kW at minimum speed in mild-to-cold weather, and up to about 3 kW in catch-up runs. Battery discharge into the heat pump therefore runs at about **93-97 %** inverter efficiency on a class-A hybrid, close to the path mean.
- The circulation pump and controls draw a few tens of watts when the compressor is off. A battery serving only that plus the household base load (100-300 W) at night runs at **66-90 %**.
- **Corollary:** if the battery must cover night load anyway, a night with the heat pump running is the *efficient* way to drain it. Stretching the battery over a whole night of 150 W base load is the inefficient way.

### 2. Idle and standby losses

**Standby with an empty battery, 2026 test: 4-64 W** [1][2].
- Fox ESS and SAX draw 4 W. Some inverters step down after a few minutes (Kostal MP G3 4.6: 29 → 5 W after 4 min; SMA SBSE 5.0: 22 → 12 W after 5 min) [1].
- A 63 W standby alone cost one system **2.8 percentage points** of its SPI [1].
- **Earlier years:** mean 13 W across 20 systems; Varta 2 W; worst 64 W, about 10× its datasheet value [5]. Another year's worst was 51 W [6].

**The BMS is extra and is not in the SPI rating.**
- It draws up to 37 W [1].
- Example from the report: RCT Battery Master 5.5 W plus 0.6 W per module, about 9 W in total, which takes **≈1 kWh from the cells in 5 winter days** [1].

**Annual scale [C].**
- 10 W ≈ 88 kWh/yr; 30 W ≈ 260 kWh/yr; 64 W ≈ 560 kWh/yr.
- In a Lithuanian December the battery may cycle only 0-5 kWh/day (see §4). A 30 W total idle draw (0.72 kWh/day) is then a 15-100 % overhead on what it actually shifts.
- For comparison, a stand-alone battery inverter of this class (Victron MultiPlus-II 48/5000) draws **18 W** at zero load, 12 W in its AES mode and 3 W in search mode [12].

**Loss shares in the annual simulation (SPI, German reference house with heat pump and EV, 9,363 kWh/yr) [1]:**
- best system E1: conversion 2.7 %, control 0.1 %, standby 0.2 %, total **3.0 %**;
- worst system I1: conversion 6.6 %, control 0.9 %, standby 2.8 %, total **10.7 %**.
- Each 1 percentage point of SPI was worth about 26 €/yr at 40/8 ct [1].

### 3. Degradation cost per cycled kWh

**Field data.** Figgener et al., *Nature Energy* 2024 [7]:
- 21 German home batteries, up to 8 years (about 106 system-years).
- Usable capacity falls about **2-3 percentage points per year**. The LFP system fell about 2.0-2.2 pp/yr, or about 0.7 pp per 100 equivalent full cycles.
- About **200 equivalent full cycles per year**, concentrated in spring and autumn, with "almost none in winter".
- Some systems reached 80 % after 4.5-7 years; others were still healthy.
- The study does not separate calendar from cycle ageing.
- HTW repeats the 2-3 pp/yr figure and gives 150-300 cycles/yr as typical [1].

**Lab cell data.** Preger et al., Sandia, 2020 [8]:
- Commercial LFP cells: **2,500-9,000 cycles** to 80 %, against 200-2,500 for NMC and 250-1,500 for NCA.
- Depth of discharge had "little effect" on LFP; 40-60 % SOC was best.
- Ageing rose with temperature (15 °C best, 35 °C worst).
- LFP had the highest round-trip efficiency of the three chemistries.

**Warranties** (20 manufacturers reviewed by HTW) [1]:
- 10-15 years.
- Energy throughput 2.4-8.5 MWh per kWh of capacity, or 3,500-10,000 cycles.
- 60-85 % remaining capacity at the end.
- One 10 kWh product caps output at 26 MWh over 10 years (2,600 kWh/yr). Above that rate, the warranty ends early [1].
- Powerwall 2: unlimited cycles for self-consumption [13].

**Price** [10][14]:
- Fraunhofer ISE uses 500-1,000 €/kWh installed (small PV + battery, 2024), a 15-year life, 90 % efficiency and 100-300 cycles/yr [10].
- LFP cells cost about $56-100/kWh in 2023-24, and assembled consumer packs about $115/kWh [14]. Lithuanian installed prices for low-voltage LFP with a hybrid inverter are likely lower than the German figure; this was not verified.

**Wear per kWh delivered [C]:** capex ÷ (life cycles × mean usable fraction ≈ 0.9).

| Installed €/kWh | Cycles to end of life | Wear €/kWh |
|---|---|---|
| 300 | 6,000 | 0.056 |
| 500 | 6,000 | 0.093 |
| 500 | 3,000 | 0.19 |
| 700 | 3,000 | 0.26 |

**When wear is nearly free.** At 200 cycles/yr over a 15-year life, a pack reaches only about 3,000 cycles. If the pack is rated at 6,000+ cycles, calendar ageing ends its life first, and the *marginal* wear of one extra cycle is far below the averages above. Under that condition the practical marginal wear is about **0.02-0.06 €/kWh**.

**Rule of thumb [C]:** add about **0.03-0.10 €/kWh** of wear to every kWh routed through the battery, on top of 8-25 % energy loss.

### 4. Battery capacity versus winter PV in Vilnius

The monthly figures below are from [N10], from PVGIS and hourly Vilnius weather for a 15 kWp array:

| Month | Median PV kWh/day | Heat-pump electricity need, kWh/day |
|---|---|---|
| Nov | 8.9 | 19.1 |
| Dec | 6.7 | 25.8 |
| Jan | 11.6 | 25.6 |
| Feb | 20.3 | 24.2 |
| Mar | 41.5 | 18.5 |
| Oct | 27.8 | 11.4 |
| Apr | 62.8 | 12.4 |

**What the table shows [C]:**
- **November to January:** daily PV is below heat-pump plus base load on most days. Surplus appears only in midday hours on clear days, when 15 kWp can deliver more than 5-8 kW while the heat pump draws 1-3 kW. A battery absorbs that midday excess, and the heat pump consumes it in the evening. The battery shifts typically **0-8 kWh/day**, matching the field finding of very little winter cycling [7].
- **February and March** are the months where battery and slab compete. Clear-day PV of 30-57 kWh exceeds heat-pump and house demand during daylight.
- **October and April:** PV of 28-63 kWh/day easily fills both the slab band and a 10-15 kWh battery. The competition is only about **order within the day**, not about which store gets used.

**Storage capacity in electricity terms:**

| Store | Electricity it can shift |
|---|---|
| Slab, ±0.5 K band (6.6 kWh heat) | ≈1.5-2 kWh |
| Slab, 2 K band (13.2 kWh heat) | ≈3-4 kWh |
| Battery, typical 10-15 kWh usable | 10-15 kWh |

Sources: [N05], and [1] for typical German new-build batteries of 8.6 kWh average in 2023 [5].

**How much of a battery to plan around.** In the HTW reference house with a heat pump and an EV:
- an ideal 8 kWh battery saved 2,465 €/yr;
- adding 4 kWh added 164 €/yr;
- adding a further 4 kWh (12 → 16 kWh) added only 108 €/yr [1].

Marginal battery capacity saturates fast, so the planner should not count on the battery to take the heat pump's whole night load in winter.

### 5. Head-to-head: heat delivered per kWh of PV surplus [C]

Reference: the same heat produced at night, at night-time air temperature. COP sensitivity is about 2.5-4 % per K of outdoor air [N10] and 2.24 % per K of flow temperature [N01]. Running the compressor hard costs about 30-40 % more electricity per kWh of heat than minimum speed [N01]. Slab storage loss is 4-14 % depending on how long the heat is held [NC8].

Daytime air is warmer than night-time air by:
- about 2-3 K from December to February [N10];
- about 5-7 K in October and March [N10];
- assumed similar in April.

| Path | Mild day (load < P_min, Oct/Mar-Apr) | Cold day (load ≥ P_min, Dec-Feb) |
|---|---|---|
| **S1: shift the minimum-speed on-block into the PV window, no extra flow** | COP gain +15-20 %, storage loss −6-12 % → **≈1.0-1.1×** | Not available: the unit runs continuously, so there is no off-time to shift |
| **S2: absorb surplus by speeding up or raising flow 2-3 K** | ≈0.7-0.8× | 1.07 × 0.70 × 0.92 × 0.95 ≈ **≈0.65-0.75×** |
| **B: battery, then heat pump at night (class-A system)** | 0.87-0.93 × 1.0 = **≈0.87-0.93×**, plus wear | **≈0.87-0.93×**, plus wear |
| **B, poor battery** | ≈0.74× | ≈0.74× |
| **Export, draw back later (ESO scheme)** | 1.0×, plus 0.0726 €/kWh fee | 1.0×, plus 0.0726 €/kWh fee |

**Reading the table:**
- **On mild days, shifting minimum-speed runs into the sun beats the battery by about 10-30 %** and causes no wear. Use the battery for the evening household load, and keep the heat pump off it at night.
- **On cold days, never speed up to swallow PV.** Let the battery take the surplus and feed the continuously running heat pump at night. Battery wear (0.03-0.10 €/kWh) is the only argument against this, and under Lithuanian net settlement exporting is roughly equal.
- **The table ignores hot water.** A DHW reheat at 45-50 °C has a much lower COP than space heating at 28-32 °C. Hot water also has its own storage loss. The legionella heater is COP 1 and should run only on surplus [N10].

### 6. What the optimisation and system literature does

**Langer & Volling 2020 [9]** (German house, modulating dual-mode air-source heat pump, floor heating, DHW tank, PV, battery; mixed-integer optimisation over a year):
- The battery's target state of charge follows a U-shape: high in winter, about a quarter of capacity in summer.
- The battery was charged only for the demand "until the next PV generation", as late as possible, and the rest was exported.
- The floor was heated on PV at peak-COP hours almost daily from October to mid-November.
- In deep winter the floor sat at the lower comfort bound just before PV started.
- With constant prices, charging the battery from the grid was not viable because of its losses.
- A pure self-consumption objective raised energy use by 2 % and cut profit by 9 % [9].

**Fraunhofer ISE** says thermal storage capacity is far cheaper than electricity-to-electricity storage, and that heat pumps with floor heating should be charged in the core of the day or by price signal [11]. These are statements, not measurements.

**HTW** suggests heat pumps profit from dynamic tariffs if the building is well insulated or has a buffer tank, so that the heat pump "can work in cheap periods" [1].

**Community.** A Home Assistant blueprint applies a −4 K setpoint cutoff when the sun is below 25° and house load exceeds PV. Its stated purpose is to stop floor heating from draining the battery. No results are reported [15].

## What this means for controlling this house

The rules are ordered by confidence. "Surplus" means PV minus house base load minus the heat pump's current draw.

1. **Measure the battery first (high value, 1 week).** From the inverter's Modbus registers or cloud logs, record PV energy into the battery, battery energy to AC, grid import, and house load. Compute:
   - the real round-trip efficiency at night loads above 800 W and below 300 W;
   - the standby draw with an empty battery.

   **Decision thresholds:**

   | Measured round trip into heat-pump-sized loads | What to do |
   |---|---|
   | Below 0.80 | Drop battery-to-heat-pump shifting |
   | Above 0.88 | Use the rules below |

2. **Classify each day by load against P_min** (this already exists in the planner's terms). Above roughly +2 to +4 °C outdoor the daily mean load is below about 3.75 kW, and the unit must cycle [N05]. *Confidence: high on the mechanism; medium on where the threshold sits.*

3. **Mild days: heat the slab first.** *Confidence: medium-high.*
   - Plan the day's on-blocks at minimum compressor speed and the lowest flow that absorbs P_min.
   - Start the first block when the forecast surplus is at least about 1.0-1.3 kW. That is the electrical draw at P_min.
   - Let the battery charge in parallel from the rest.
   - Allow the room to rise to about +0.5 K above target (≈1.5-2 kWh of electricity) by mid-afternoon.
   - Do **not** raise the flow more than about 2 K for storage [N10]. Do **not** let the unit run its fast catch-up mode to "use" PV.
   - At night, keep the heat pump off the battery if the slab carries the house to the next PV window. Leave the battery for evening household loads.

4. **Cold days (unit runs continuously): battery first, steady compressor.** *Confidence: medium.*
   - Keep the heat pump at its weather-compensated modulated output through the day. Do not boost it for PV.
   - Let surplus charge the battery.
   - Allow the battery to discharge into the heat pump in the evening and night (17-24 h first, where grid prices are highest [N10]).
   - Set a battery reserve (for example 10-20 %) so it is not left empty just before a cheap night window.
   - The one exception: if the battery is full and surplus remains, raise the setpoint by +1 K for the slab, at minimum speed only, before exporting.

5. **Order of use for any surplus kWh [C]:**
   1. heat pump running at minimum speed (it is needed anyway);
   2. DHW tank top-up when the tank is due within about 24 h (minimum speed, no immersion heater);
   3. battery up to the level needed until the next PV (high in Feb-Mar and Nov, about half in Oct/Apr, after Langer & Volling [9]);
   4. slab +0.5 to +1 K at minimum speed;
   5. legionella immersion cycle (COP 1, so only on surplus that would otherwise be exported);
   6. export.

   On the ESO 0.0726 €/kWh returned-energy scheme, steps 3 and 6 are close in value. Put export ahead of the battery when the battery's measured round trip is below about 0.85 or when it is above about 250 cycles/yr.

6. **Never grid-charge the battery to feed the heat pump** on a flat tariff [9]. On a spot tariff, do it only when (evening price × round-trip efficiency) minus wear (≈0.05 €/kWh) exceeds the night price. Prefer the zero-wear alternative: preheat the slab at night, then block 17-21 h [N10]. *Confidence: medium.*

7. **Watch the idle tax in December and January.** If the hybrid allows a winter sleep or "battery hibernate" mode when the expected daily surplus is below about 2 kWh, use it. Otherwise standby (4-64 W, plus a BMS of up to 37 W) can exceed what the battery shifts [1]. *Confidence: medium. It depends on the unknown product.*

8. **Battery location.** If the pack sits in an unheated garage or technical room, LFP charge power is usually derated or blocked near 0 °C. That would remove the battery option exactly in the cold-day regime of rule 4. Check before relying on rule 4 (not verified here; product-specific).

**Test to confirm rule 3 against rule 4.** On a pair of similar sunny February-March days, alternate the two policies and log the heat pump's electricity and heat (if a heat meter or flow and ΔT are available), the battery's in/out flows, and grid import.

| Expected result | Policy that wins |
|---|---|
| Next-morning room at least as high, with lower grid import | S1 on mild days |
| Lower grid import, at equal comfort | B on cold days |

## Contradictions and open questions

- **"Battery losses 10-20 %" (brief) against the lab data.** Good class-A hybrids lose about 7-12 % on the full PV → battery → AC path at 1-3 kW. Poor ones lose 20-26 % [1]. The brief's range is fair as an envelope, but the spread between products is larger than the spread between operating points, except at very low loads (below 300 W).
- **Datasheets against the lab.** 15 of 22 systems delivered less usable capacity than their datasheets state, one by 11 percentage points [4]. One system's measured standby was 10× its datasheet value [5]. Do not use datasheet values in the planner.
- **Wear cost depends on assumptions that are not settled.** Field ageing data do not separate calendar from cycle fade [7]. Lab LFP cycle life spans 2,500-9,000 cycles [8]. Whether one extra cycle costs about 0.02 or 0.2 €/kWh depends on which ageing mechanism ends this pack's life, and that is unknown.
- **Slab COP gain in the shoulder months rests on a day-night temperature difference of 5-7 K,** derived from [N10]'s warmest-window figures. The night side was inferred, not tabulated. If the real difference is about 4 K, S1's advantage shrinks to about 0-10 %, roughly equal to the battery.
- **The 30-40 % high-speed penalty** [N01] is derived from certified part-load COPs and an inferred catch-up COP. It was not measured on this Versati. It is the single most decisive number in the cold-day verdict.
- **Not verified:**
  - the owner's prosumer scheme (annual or monthly balancing) [N10];
  - battery brand and usable capacity;
  - inverter model and its part-load curve;
  - battery location and temperature;
  - whether the hybrid lets the battery discharge into the heat pump's circuit at all (some installs put the heat pump on a non-backup circuit that the inverter's export limit does not cover).
- **No measured field study compares "PV → battery → heat pump at night" with "PV → slab now" on a slab-UFH air-to-water house.** The only rigorous comparison found is a simulation [9]. A measured twin-rig PV-shifting study used a 500 L buffer and had no battery [N10].
- **0 web searches ran** (budget exhausted). No non-English community sources (German, Polish, Swedish, Lithuanian forums) were consulted. Searches worth running in a later round:
  - German: "Wärmepumpe Batteriespeicher entladen nachts sinnvoll";
  - Lithuanian: "kaupiklis šilumos siurblys naktį";
  - the HTW Berlin "Solarisator" heat-pump studies;
  - SPF Rapperswil work comparing thermal and electrical storage with PV.

## Sources

1. Stromspeicher-Inspektion 2026 (full report, 66 pp.) - HTW Berlin / aquu (Weniger, Orth et al.) - 2026 - https://solar.htw-berlin.de/wp-content/uploads/HTW-aquu-Stromspeicher-Inspektion-2026.pdf - lab (independent test institutes AIT/KIT/ZHAW) + simulation - Path efficiencies, 100-500 W part-load curves, 4-64 W standby, BMS up to 37 W, SPI loss breakdown, warranty table, 71 % grid-charging threshold, capacity saturation.
2. Stromspeicher-Inspektion 2026 (study page) - HTW Berlin - 2026 - https://solar.htw-berlin.de/studien/stromspeicher-inspektion-2026/ - lab summary - Battery efficiency 97.1 % vs 9 points lower, SPI 97.0 vs 89.3 %, 4 vs 64 W standby, 60-85 % warranty capacity.
3. Stromspeicher-Inspektion 2025 (study page) - HTW Berlin - 2025 - https://solar.htw-berlin.de/studien/stromspeicher-inspektion-2025/ - lab summary - Worst hybrid 54 % at 100 W; 14 % (RCT) and 24 % (Fronius) loss at 100 W; household night load 100-150 W.
4. Energy Storage Inspection 2025 (English slides) - HTW Berlin - 2025 - https://solar.htw-berlin.de/wp-content/uploads/HTW-Energy-Storage-Inspection-2025.pdf - lab - 15 of 22 systems below datasheet usable capacity; SPI class thresholds; standby excludes BMS.
5. Stromspeicher-Inspektion 2024 (study page) - HTW Berlin - 2024 - https://solar.htw-berlin.de/studien/stromspeicher-inspektion-2024/ - lab summary - 200 W part-load 92 % vs 71 %; mean standby 13 W (2-64 W); 8.6 kWh average new battery.
6. Stromspeicher-Inspektion 2023 (study page) - HTW Berlin - 2023 - https://solar.htw-berlin.de/studien/stromspeicher-inspektion-2023/ - lab summary - Battery efficiency 92.9-97.8 %; standby 2 vs 51 W.
7. Multi-year field measurements of home storage systems and their use in capacity estimation - Figgener et al., Nature Energy - 2024 - https://www.nature.com/articles/s41560-024-01620-9 - field data - 21 systems, 8 years: 2-3 pp/yr fade, about 200 EFC/yr, almost no winter cycling, some systems at 80 % after 4.5-7 years.
8. Degradation of Commercial Lithium-Ion Cells as a Function of Chemistry and Cycling Conditions - Preger et al. (Sandia), J. Electrochem. Soc. 167 - 2020 - https://iopscience.iop.org/article/10.1149/1945-7111/abae37 - lab - LFP 2,500-9,000 EFC to 80 %; depth of discharge has little effect; worse at higher temperature; highest round-trip efficiency.
9. An optimal home energy management system for modulating heat pumps and photovoltaic systems - Langer & Volling, Applied Energy (arXiv 2009.02349) - 2020 - https://arxiv.org/abs/2009.02349 - paper (simulation) - Optimal split: floor heated on PV at peak COP, battery charged only to next-PV need, self-consumption maximisation +2 % energy and −9 % profit, no grid-charging on a flat price.
10. Levelized Cost of Electricity - Renewable Energy Technologies (2024) - Fraunhofer ISE - 2024 - https://www.ise.fraunhofer.de/content/dam/ise/en/documents/publications/studies/EN2024_ISE_Study_Levelized_Cost_of_Electricity_Renewable_Energy_Technologies.pdf - paper (techno-economic study) - 500-1,000 €/kWh installed small battery, 15-year life, 90 % efficiency, 100-300 cycles/yr.
11. Recent Facts about Photovoltaics in Germany - Fraunhofer ISE - 2026 - https://www.ise.fraunhofer.de/content/dam/ise/en/documents/publications/studies/recent-facts-about-photovoltaics-in-germany.pdf - paper (review) - Thermal storage capacity is much cheaper than electricity-to-electricity storage; charge heat pump stores by residual load (qualitative).
12. MultiPlus-II inverter/charger datasheet - Victron Energy - n.d. - https://www.victronenergy.com/upload/documents/Datasheet-MultiPlus-II-inverter-charger-EN.pdf - manufacturer - Zero-load power 11-55 W by size (18 W for 48/5000), 3-6 W in search mode; illustrates the idle floor.
13. Tesla Powerwall - Wikipedia - 2026 - https://en.wikipedia.org/wiki/Tesla_Powerwall - secondary (manufacturer spec + one measurement) - Powerwall 2 90 % round trip at 3.3 kW / 25 °C; 88 % measured, ±2-3 % seasonal; unlimited self-consumption cycles.
14. Lithium iron phosphate battery - Wikipedia - 2026 - https://en.wikipedia.org/wiki/Lithium_iron_phosphate_battery - secondary - LFP 2,500-9,000 cycles; cell prices $56-100/kWh (2023-24), packs about $115/kWh.
15. Advanced Heat Pump Optimization (PV or w/o PV, Battery & Weather Aware) - Home Assistant Community (djm193) - 2026 - https://community.home-assistant.io/t/advanced-heat-pump-optimization-pv-or-w-o-pv-battery-weather-aware/992049 - forum - −4 K cutoff at low sun when load exceeds PV, to keep floor heating from draining the battery; no results.

Sibling notes used for house-specific inputs (not new sources): [N01] 01-inverter-part-load.md (2.24 %/K flow, 30-40 % burst penalty); [N05] 05-ufh-slab-control.md (≈1.5 kWh_el per ±0.5 K band, P_min regime); [N10] 10-scheduling-pv-tariffs.md (Vilnius PV by month, day-night temperature, ESO 0.0726 €/kWh, LT price spreads); [NC8] verify-r1-C8.md (slab storage loss 4-14 %); [NG5] gap-r1-G5.md.
