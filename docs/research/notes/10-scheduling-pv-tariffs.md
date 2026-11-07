# When to run: time of day, PV self-consumption and dynamic tariffs

Researcher topic 10. Scope: moving heat production into warmer hours, PV-surplus heating (SG-Ready, excess-solar control), how much PV a Baltic winter actually gives for space heating, dynamic spot tariffs (Nord Pool LT, Lithuanian network zones and prosumer rules), published load-shifting results for floor-heating heat pumps, and the pitfalls. The house's own controller code was deliberately not read.

**Method note.** The shared web-search budget was already used up by other researchers when this sweep started; all 4 searches I tried were refused. Instead, this note uses:
- direct reads of known primary sources (papers, manufacturer and tariff pages, forum threads, PDFs parsed locally);
- three **public raw datasets that I analysed myself**: hourly Vilnius weather for 2021-10 to 2025-04 (Open-Meteo/ERA5) [1], PVGIS monthly yield for a 15 kWp array at Vilnius [2], and Lithuanian Nord Pool day-ahead prices for four winters, 2022-23 to 2025-26 [3];
- the heatpumpmonitor.org public statistics for 553 metered systems [4].

Numbers marked **[C]** are my own calculations on those datasets. Their scripts are in the session scratchpad and are not part of the repo. The house model used in [C] is the owner's: H = 0.17 kW/K (mid of 0.14-0.20), slab storage 6.6 kWh/K, minimum heat output P_min = 3.8 kW, internal gains about 0.35 kW, and Gree Versati W35 COP points of 2.81 at A−7, 3.85 at A2 and 4.61 at A7 [33][36].

---

## Summary

1. **Running in the warmest hours buys very little in a Lithuanian winter.** From December to February, the warmest 6-hour window (starting about 10:00) is only **1.1-1.9 K** above the daily mean. The average hourly profile runs from −1.8 °C at 07:00 to 0.0 °C at 13-14:00 [1][C]. The swing is larger in October (+2.5 K) and March (+3.7 K) [1][C]. At the Versati's roughly 2.5-4 %/K COP sensitivity at W35 [33][21], that is worth 3-6 % COP *for the hours inside that window*. But the house must run 12-21 h/day from November to March anyway (table in §1.3).
   - Scheduling a fixed-W35 heat pump "warmest hours first" saves only **≈1.5 % of seasonal electricity**, as an upper bound with no comfort limit (Oct-Apr, 2 winters) [C].
   - With a 1-2 K comfort band, the saving is **≈0-1 %** [C].

2. **Flow temperature beats time of day by a wide margin.** Each +1 K of leaving water costs **2-3 % COP** [21][33]. So a time shift that needs even +1-2 K of extra flow to "charge" the slab wipes out the whole December-February warm-hour gain [C].
   - Rule: never raise the flow setpoint just to store heat, unless the price or PV value difference is well above ~3 % per K of extra flow.

3. **In Lithuania the price signal is roughly 10× the COP signal, and it points the other way (night).**
   - Over four winters (Nov-Mar), LT spot prices at 00-06 were **34-53 €/MWh below the daily mean**. Prices at 10-16 were **6-22 €/MWh above** it, and 17-21 was **25-45 €/MWh above** it [3][C].
   - On a spot-indexed supply plan plus the ESO two-zone network tariff (day 0.129, night/weekend 0.071 €/kWh incl. VAT [22]), I estimate night retail at **≈0.15-0.19 €/kWh** and weekday daytime at **≈0.27-0.33 €/kWh** [3][22][24][C].
   - So night electricity is ~40-45 % cheaper, while daytime air gives only ~3-6 % better COP.

4. **What cost-optimal scheduling earns depends almost entirely on the comfort band and the tariff, not on COP** [C]. I simulated hourly dynamic programming over two winters, with comfort as a slab-energy band, P_min = 3.8 kW, a start penalty, and a hysteresis-at-P_min baseline:
   - **±0.5 K band (1 K total):** cost −1 % without PV, −3 % with PV.
   - **2 K band:** cost **−10 %** without PV, **−16 %** with PV.
   - Electricity changes by 0 to +4 %, and starts per day rise slightly (about 2 to 3-4).
   - Minimising energy instead gives only −0.9 % kWh.

5. **Simplest high-value rule: avoid the 17:00-21:00 evening peak.** It was the most expensive window every winter [3][C]. In a 97-day occupied-house test with a 7 kW air-to-water heat pump and a concrete floor, simply blocking the heat pump at 17-21 would have captured **≈66 % of all MPC savings** [13].

6. **Field results warn that price-chasing raises energy use and overheats on sunny days.**
   - Danish occupied house (7 kW AWHP, concrete UFH): cost **−12.4 %**, but electricity **+9.5 %** (+23.6 % at one comfort level). Savings concentrated at **0.7-4 °C outdoor**, there were consistent losses at −5-0 °C, and night boosting plus wrong cloud forecasts caused overheating [13].
   - Glasgow (ASHP + UFH, 4 weeks): pre-charging made the **immersion heater supply most of the heat** [14].

7. **The best rigorous long test of shifting to midday + PV gave modest gains** (125-day twin rigs, real ASHP, 500 L buffer): electricity **−4.1 %**, COP **+5.4 %**, heat-pump PV self-consumption **+107.7 %**, cost **−9.0 %** [12].
   - The controller moved operation to after 10:00 [12].
   - From December to February the cost saving was only **8.2 %**, because irradiance and daily temperature spread were small [12].
   - Short spring tests on the same rig had shown 34 % cost savings, so short tests overstate the gain [12].

8. **PV in a Vilnius winter is small next to heat-pump demand.** PVGIS (snow-free) gives a 15 kWp, 35° south array **235 kWh in December, 328 in November and 416 in January**, against **14.45 MWh/yr** [2]. Heat-pump electricity in the model is ~19-26 kWh/day from November to February [C].
   - The median December day yields **6.7 kWh** of PV, with ~2 h/day of ≥1 kW surplus [1][2][C].
   - Upper bound on the share of heat-pump electricity PV can cover: **Oct 85 %, Nov 31 %, Dec 16 %, Jan 36 % (optimistic, snow), Feb 63 %, Mar 90 %** [C].

9. **No special logic is needed to use winter PV.** In December the average load (3.6 kW) is about P_min, so a heat pump that simply runs through the day absorbs all the PV [C].
   - PV-surplus logic matters in **October and February-April**. Then the unit must duty-cycle anyway (on 11-16 h/day at +5 to +10 °C), and putting the forced ON block at 10:00-16:00 costs nothing [C].

10. **Lithuanian prosumer rules may make PV timing almost worthless as a cost lever.**
    - Under ESO's "returned energy" settlement, exported kWh can be drawn back later for **0.0726 €/kWh** (low voltage, 2026) [23].
    - If the owner is on that scheme with an annual surplus, a self-consumed PV kWh saves only about 0.07 €/kWh more than export and draw-back.
    - Check this before building PV-chasing logic.

11. **Storing heat in the slab costs heat.**
    - About **6 % extra loss** of the charged energy (Dutch low-energy living room, 1.6 kWh pulses) [19].
    - **+3.3 % to +6.3 %** annual heating energy for 24 h set-point-raise strategies, with flexibility **saturating beyond ~6 h**, because cheap windows rarely last longer [18].
    - Solar gains shrink the room for charging: one simulated sunny day reached 21.3 °C against a 20-21 °C band [19].

12. **The metered fleet shows the same small penalty from load shifting.** Across 553 heatpumpmonitor.org systems with ≥ 80 % of a year of data [4][C]:
    - the quartile with the cheapest effective Agile price (21.1 p/kWh vs 22.2 p median) had **lower SPF: 3.76 vs 3.92-3.95**;
    - half-hourly-tariff users had SPF **3.74** vs **3.97** on a single rate.
    - These figures are confounded, but they are consistent with a small (~3-5 %) efficiency cost from shifting, and the effective-price spread is only ~10 %.

13. **SG-Ready "boost" is just a setpoint raise, with guard rails** [5][6]:
    - minimum signal time 10 min;
    - hard block at most 2 h and 3 times per day;
    - evcc's example thresholds: enable at **1.3 kW** surplus held 5 min, disable at **150 W** import held 20 min.
    - Vendor features (Viessmann Dynamic Assistant, NIBE Smart Price Adaption) **only move consumption in time and do not raise efficiency** [15][30].

14. **Bottom line for this house (medium confidence).** Timing is a cost lever, not an efficiency lever:
    - Expect **0-2 % less electricity** from smarter timing.
    - Expect **3-15 % lower cost**, depending on the tariff, the prosumer scheme and how wide a comfort band the owner accepts.
    - The efficiency levers are low flow temperature and long, low-power runs (notes 01/02/05). Timing should only decide *where* those unavoidable runs go.

---

## Detailed findings

### 1. How much COP does the daily outdoor swing offer in Lithuania?

#### 1.1 Measured diurnal swing, Vilnius, Oct 2021 - Apr 2025 [1][C]

| Month | Days | Daily mean °C | Warmest-6h minus daily mean (K) | Warmest-6h minus 00-06 (K) | Start of warmest 6 h | Daily GHI kWh/m² | Mean RH % |
|---|---|---|---|---|---|---|---|
| Oct | 124 | 8.3 | 2.5 | 3.9 | ~11:00 | 1.64 | 83 |
| Nov | 120 | 2.6 | 1.3 | 1.7 | ~10:00 | 0.62 | 88 |
| Dec | 124 | −1.5 | 1.1 | 1.5 | ~09:00 | 0.37 | 90 |
| Jan | 124 | −1.3 | 1.4 | 1.6 | ~10:00 | 0.51 | 88 |
| Feb | 113 | −0.7 | 1.9 | 2.9 | ~11:00 | 1.23 | 84 |
| Mar | 124 | 2.9 | 3.7 | 6.1 | ~12:00 | 2.85 | 72 |
| Apr | 120 | 7.7 | 3.9 | 6.9 | ~12:00 | 3.91 | 71 |

- The **average hourly profile, December-February,** runs from about −1.8 °C at 06-07:00 to 0.0 °C at 13-14:00, a 1.8 K peak-to-trough swing. In November it is 1.9 → 3.9 °C (2.0 K). In March it is −0.1 → 7.0 °C (7.1 K) [1][C].
- Days with a daily mean between −5 and +5 °C, the owner's "humid days", average only **+1.9 K** for the warmest 6 h over the daily mean. Days below −5 °C average +2.0 K, and days above +5 °C average +3.7 K [1][C].
- The "daily range" (max − min) of 3.6-5.0 K in winter is mostly **synoptic**: fronts pass at random times. It is not a reliable diurnal cycle. Only about 1.5 K of it can be predicted from clock time in December-January [1][C].

#### 1.2 Humidity and frost: a second, partly hidden reason to prefer the afternoon

- Mean RH from November to February barely moves: 89-91 % at night and 81-83 % at 12-14:00. In March it falls to 55 % at 14:00 [1][C].
- A crude frost-risk indicator, the share of hours with −7 ≤ T ≤ +5 °C and RH ≥ 80 % (November-March), falls from **0.70 at 04-06:00 to 0.44 at 14:00** [1][C].
- Sibling note 02 cites defrost costs of about 0.15 SCOP (UK simulation) up to 0.35-0.45 COP (measured Scottish case) [35].
- So afternoon runs gain a bit more than the dry-bulb COP curve suggests, but the EN 14511 A2 rating point already includes average defrost. Treat this as a +1-3 % bonus, not a separate large effect (low confidence; no direct measurement found).

#### 1.3 How much freedom to choose "when" does the house actually have? [C]

Model: load = 0.17 × (22 − T_out) − 0.35 kW. Slab energy band 6.6 kWh per K. The heat pump at P_min = 3.8 kW.

| Daily mean T_out | Load kW | ON hours/day at P_min | OFF hours per 1 K slab drift | Hours at P_min to recharge 1 K |
|---|---|---|---|---|
| −10 | 5.1 | 24 (modulating above P_min) | 1.3 | never at P_min |
| −5 | 4.2 | 24 | 1.6 | never at P_min |
| 0 | 3.4 | 21.4 | 1.9 | 16 |
| +2 | 3.05 | 19.3 | 2.2 | 8.8 |
| +5 | 2.5 | 16.0 | 2.6 | 5.2 |
| +8 | 2.0 | 12.8 | 3.3 | 3.7 |
| +10 | 1.7 | 10.7 | 3.9 | 3.1 |
| +12 | 1.35 | 8.5 | 4.9 | 2.7 |

What this means:
- **Below about 0 °C there is nothing to schedule.** The unit should simply run continuously at whatever modulation matches the load. Any "concentrate production in the afternoon" plan would need above-minimum power (higher flow temperature and lower COP) plus slab over-charging.
- **From 0 to +5 °C the scheduling freedom is a few hours of OFF time.** With a 1 K band, one OFF block of 2-2.6 h can be placed. With a 2 K band, ~4-5 h. That is just enough to skip the 17-21 peak.
- **From +5 to +12 °C the unit must cycle anyway.** It is OFF 8-15 h/day, so choosing *which* hours are ON is free, apart from comfort-band drift. This is where timing and PV logic belong.

#### 1.4 Simulated value of "warmest hours first" [C]

Hourly simulation over Oct-Apr of 2023-24 and 2024-25. ON-hours per day = heat need ÷ P_min, Versati W35 COP curve, no comfort constraint (upper bound):

| Month | ON h/day | kWh_el/day, spread evenly | kWh_el/day, warmest hours | Δ |
|---|---|---|---|---|
| Oct | 12.7 | 10.67 | 10.33 | −3.2 % |
| Nov | 18.5 | 18.60 | 18.38 | −1.2 % |
| Dec | 20.6 | 21.87 | 21.74 | −0.6 % |
| Jan | 21.5 | 24.54 | 24.43 | −0.4 % |
| Feb | 21.2 | 23.57 | 23.43 | −0.6 % |
| Mar | 17.0 | 16.11 | 15.57 | −3.4 % |
| Apr | 11.8 | 10.34 | 9.91 | −4.2 % |
| **Season** | | | | **−1.5 %** |

- With the comfort band enforced (±0.5 K and ±1 K), the energy-optimal schedule beat a plain hysteresis controller at P_min by **only 0-0.9 %** of electricity [C].
- **Conclusion:** at a constant low flow temperature, timing for COP is a rounding error in December-February. It is worth a few percent in October, March and April.

#### 1.5 Field and lab evidence on the warm-hours effect

- **Kuboth et al. 2020** [12], 125-day twin test bench in Bayreuth, December 2019 to April 2020: real ASHP (W35/A2 rating), 500 L storage tank, single-family-house load emulated from real weather, 4.8 kWp PV modelled.
  - The reference heating-curve controller produced mostly at night and in the morning. The MPC moved the main operation to after 10:00.
  - Result: COP +5.4 %, electricity −4.1 %, heat-pump PV self-consumption +107.7 %, PV curtailment −73.5 %, cost −9.0 %. The cost saving was 8.2 % from December to February and only 4.9 % in March, because of excess heat generation.
  - The authors say the weak December-February months, with low irradiance and a small daily temperature spread, limited both PV use and MPC value.
  - Comfort: more excursions outside the comfort limits with MPC than with the reference.
  - The 500 L buffer means the slab did not need over-charging, which flatters the result compared with a buffer-less slab house.
- **Danish field test** [13], 230 m² BR2020 house, Bosch 7 kW AWHP (0.2-2.5 kW electric), 15-circuit concrete floor, 4-5.5 kW PV, 97 days:
  - Savings were best at 0.7-4 °C outdoor, very small at 6-13 °C and negative at −5-0 °C.
  - Heat output rose 3.7 % while electricity rose 9.5 %. The authors blame lower COP from higher loads and dynamic operation, an over-optimistic COP model (refitted four times in 97 days), and night shifting.

### 2. PV self-consumption for space heating in a Baltic winter

#### 2.1 What the array produces (PVGIS v5.2, 15 kWp, 35° tilt, south, 14 % losses) [2]

| Month | kWh/month | kWh/day | In-plane irradiation kWh/m² |
|---|---|---|---|
| Jan | 416 | 13.4 | 31 |
| Feb | 681 | 24.3 | 51 |
| Mar | 1187 | 38.3 | 93 |
| Apr | 1737 | 57.9 | 141 |
| Oct | 868 | 28.0 | 69 |
| Nov | 328 | 10.9 | 26 |
| Dec | 235 | 7.6 | 20 |
| Year | 14 453 | | 1195 |

PVGIS does not model snow on the panels. January and February are therefore optimistic for a 35° roof in Lithuania (low confidence on those two months).

#### 2.2 Day-by-day distribution and usable surplus [1][2][C]

Hourly irradiance from [1], scaled per month to PVGIS totals. Household base load assumed 0.35 kW. "Usable" means surplus ≥ 1 kW, roughly what the compressor draws at P_min.

| Month | Median PV kWh/day | 90th-percentile day | Share of days > 10 kWh | Mean hours/day with ≥ 1 kW surplus | Heat-pump kWh_el need/day | Max share of heat-pump kWh PV could cover |
|---|---|---|---|---|---|---|
| Oct | 27.8 | 46.4 | 0.90 | 6.6 | 11.4 | 0.85 |
| Nov | 8.9 | 19.6 | 0.45 | 3.0 | 19.1 | 0.31 |
| Dec | 6.7 | 13.6 | 0.29 | 2.1 | 25.8 | 0.16 |
| Jan | 11.6 | 24.6 | 0.60 | 3.7 | 25.6 | 0.36 |
| Feb | 20.3 | 38.7 | 0.85 | 5.6 | 24.2 | 0.63 |
| Mar | 41.5 | 57.0 | 0.98 | 8.5 | 18.5 | 0.90 |
| Apr | 62.8 | 86.2 | 0.99 | 10.3 | 12.4 | 0.94 |

- The "max share" assumes perfect shifting into PV hours. From November to February it is not a shifting problem: the heat pump runs 18-21 h/day anyway, so PV is absorbed if the unit simply keeps running through the middle of the day [C].
- The hybrid battery's capacity is unknown. Any battery size moves these numbers up, because evening and night heat-pump use can be served from stored PV. Fraunhofer ISE measured six heat-pump + PV houses: 25-40 % self-sufficiency and 22-37 % self-consumption without a battery, rising to **32-62 %** and **40-83 %** with one [11]. Those are German sites, with more winter sun than Vilnius.

#### 2.3 How PV-surplus control is done in practice

- **SG-Ready (BWP label)** [5]. Two contacts give states:
  - state 1: block or limit (aligned with the §14a EnWG 4.2 kW limit);
  - state 2: normal;
  - state 3: "boost recommendation", i.e. raise buffer or DHW setpoints to store surplus;
  - state 4 (in the one-contact variant): definite start command, optionally with electric heaters.
  - Signals must hold at least 10 minutes. A full block lasts at most 2 h, at most 3 times a day.
  - A room thermostat that blocks the unit on room temperature alone does not count as compliant [5].
  - In SG Ready the heat pump keeps the final say [5][6].
- **evcc** [6] drives SG-Ready relays or vendor APIs from measured surplus. Example thresholds: enable at 1300 W surplus held 5 min, disable at 150 W import held 20 min. The docs warn that heat pumps need minimum runtimes and that longer delays avoid short cycling. The "boost requested" state can sit unanswered while the unit is in a minimum-off time.
- **Fraunhofer ISE (WP-QS im Bestand)** [11] describes the classic method: raise target temperatures when PV surplus exists. It reports the self-sufficiency figures above. The field report also lists **oversizing and very high switching frequencies** as common faults [11].
- **Viessmann Vitocal** [15]: PV-surplus priority, plus a "Dynamic Assistant" that shifts DHW and heating phases to cheap hours on a dynamic tariff. A trade review says this changes timing, not kWh, and that without a dynamic tariff the cost benefit "largely disappears" [15].
- **NIBE Smart Price Adaption** [30]: shifts use into the cheapest of the next 24 hourly prices. Separate "degree of effect" settings for room (1-10, default 5) and hot water (1-4, default 2). Higher settings bring bigger savings and more comfort risk.
- **EMHASS** (Home Assistant optimiser) [27] models a slab as one concrete lump with a Carnot-fraction COP (e.g. 0.4 × Carnot gives COP ≈ 4.1 at W35/A5). The docs show **no minimum-power or minimum-runtime constraint** for thermal loads. A naïve optimiser of this kind can therefore plan sub-minimum or very short runs that a real unit like the Versati turns into on/off cycling.

#### 2.4 Value of a self-consumed PV kWh in Lithuania (2026)

- **ESO prosumer settlement** [23]. For returned energy, the prosumer pays **0.0726 €/kWh** (low voltage) for each exported kWh drawn back later. Alternatives:
  - a fixed fee of 5.03 €/kW of permitted capacity per month, or
  - the operator keeps 37 % or 21 % of exported kWh (recommended only if output exceeds about 140 % of annual consumption at low voltage).
- On the per-kWh scheme, the value of using PV *now* rather than exporting it equals the 0.0726 €/kWh fee plus any difference in the supply price. On a fixed supply tariff that difference is roughly zero. It is not a 0.25 €/kWh saving as in Germany or the UK.
- I could not confirm from ESO's page whether storage is balanced annually or monthly, nor which scheme this owner has. **This single fact decides whether PV-chasing logic is worth building** (open question 1).

### 3. Dynamic tariffs: what the Lithuanian price curve looks like in winter

#### 3.1 Nord Pool LT day-ahead, November-March [3][C]

| Winter | Days | Mean €/MWh | Mean daily max−min | 00-06 vs mean | 10-16 vs mean | 17-21 vs mean | Share of hours ≤ 0 |
|---|---|---|---|---|---|---|---|
| 2022-23 | 151 | 160 | 143 | −53 | +22 | +40 | 0.1 % |
| 2023-24 | 152 | 91 | 110 | −34 | +10 | +25 | 0.1 % |
| 2024-25 | 151 | 102 | 159 | −45 | +6 | +45 | 1.1 % |
| 2025-26 (15-min MTU, averaged hourly) | 151 | 116 | 150 | −44 | +14 | +34 | 0.4 % |

- The shape is the same every winter: cheapest 01-05:00, a morning peak at 08-09, a **midday shoulder (12-14:00) that is cheaper than the morning but still above the daily mean**, and the main peak at **17-19:00** [3][C].
- The cheapest 6 hours of each day average **38-59 €/MWh below the daily mean** [3][C].
- Since 1 October 2025, LT prices come in **15-minute** steps (the data source switched from 3600 s to 900 s spacing) [3]. Ignitis' "Išmanus-15" plan bills the 15-min exchange price plus a supplier share, regulated components and VAT. Next-day prices are published after 15:00 [24].

#### 3.2 Retail price by time on a dynamic plan [22][24][C]

My estimate: spot price + an assumed ~10 €/MWh supplier share, × 1.21 VAT, plus the ESO "Standartinis" two-zone network price (day 0.129, night/weekend 0.071 €/kWh incl. VAT). The "day" zone is weekdays 07-23; ESO's page gives exact hours only for medium voltage, so household zone hours are to be confirmed [22].

| Winter | Two-zone "day" window | Night + weekend | Weekdays 10-16 | 00-06 |
|---|---|---|---|---|
| 2024-25 | 0.307 | 0.169 | 0.271 | 0.152 |
| 2025-26 | 0.325 | 0.185 | 0.299 | 0.172 |

- ESO also offers a **four-zone** plan for households (Standartinis: night 0.063, morning 0.083, day 0.104, **evening 0.146** €/kWh) [22]. That network price alone makes the evening 2.3× the night.
- Compare the COP gain from running at 13:00 instead of 03:00 in December-February (~1.7 K, ~4-6 %) with the price drop from 0.27-0.30 to 0.15-0.17 €/kWh (~43 %). **On a dynamic or zoned tariff, cheap night hours win clearly, unless PV is available or the shift needs more flow temperature or more heat.** A UK owner on the OpenEnergyMonitor forum put it this way: "no amount of COP can outrun off peak electricity" [26].

#### 3.3 Simulated cost-optimal scheduling for this house [C]

Hourly dynamic programming per day, two winters (Oct-Apr 2023-24 and 2024-25):
- Actions: OFF, or ON at max(P_min, 1.3 × load).
- Comfort: slab energy kept inside a band, 1 K = 6.6 kWh.
- End-of-day state valued back.
- Start penalty: 0.3 kWh (energy objective) or 0.08 € (cost objective).
- Baseline: a hysteresis controller at P_min inside the same band, i.e. *already* "ride the minimum", not today's behaviour.

| Comfort band | PV valued? | Baseline kWh/day, starts/day | Energy-optimal: Δ kWh, Δ cost | Cost-optimal: Δ kWh, Δ cost, starts/day |
|---|---|---|---|---|
| 1 K (±0.5) | no | 18.8, 2.9 | +0.3 %, +3.9 % | +1.4 %, **−1.0 %**, 4.3 |
| 1 K | yes (export value) | 18.8, 2.9 | +0.3 %, +4.3 % | +3.9 %, **−3.2 %**, 4.2 |
| 2 K (±1.0) | no | 18.8, 1.9 | −0.9 %, −2.3 % | +0.2 %, **−9.6 %**, 2.8 |
| 2 K | yes | 18.8, 1.9 | −0.9 %, −4.5 % | +0.9 %, **−15.6 %**, 2.8 |

A simpler, unconstrained "sort the hours" bound gave cost −7.2 % without PV and −12 % with PV, at +0.1 % kWh [C].

Caveats:
- 1-hour resolution.
- No solar gains in the room model.
- COP depends only on air temperature at a fixed W35. In reality, charging a slab 1-2 K warmer needs slightly higher flow; at 2-3 %/K that adds ~+1-3 % kWh to the cost-optimal columns.
- Perfect foresight.
- The 0.5 K band case was numerically unreliable and is omitted.

Treat these as *order of magnitude*: a ±1 K band and a spot-plus-zone tariff are worth about 10 %. A ±0.5 K band is worth almost nothing.

#### 3.4 Published load-shifting results with floor heating or ASHPs

| Study | Setup | Signal | Result | Evidence |
|---|---|---|---|---|
| Thorsteinsson et al. 2023 [13] | DK, 7 kW AWHP, concrete UFH, PV, 97 days, occupied | DK network tariff (0.027 / 0.081 / 0.26 €/kWh at night / day / 17-21) + spot | Cost −12.4 % (−2.3 % to −32.8 % by comfort level); kWh +9.5 %; €0.29/day; ~66 % of savings from avoiding 17-21; overheating on sunny days after night boosts; savings unconverged after 55 days | Field |
| Kuboth et al. 2020 [12] | DE twin rigs, real ASHP, 500 L, 125 days | PV + fixed price (0.293 €/kWh, feed-in 0.122) | kWh −4.1 %, COP +5.4 %, PV self-consumption +108 %, cost −9 %; short tests had shown −34 % | Lab, real weather |
| Allison et al. 2017 [14] | Glasgow low-carbon house, ASHP + UFH, 4 weeks | Off-peak pre-charge | Comfort 18-23 °C for 87 % of 07-22 h; heat pump performance "very poor", immersion supplied most heat | Field |
| van Leeuwen et al. 2014 [19] | NL low-energy living room, floor storage | 2 h pulses | 1.6 kWh per pulse; extra loss 479 Wh = 6 % of 8 kWh charged; storage pays only if its price ≤ normal price − 6 % | Simulation |
| Johra et al. 2019 [18] | DK houses, UFH vs radiators | Set-point 20/22/24 °C by price | +3.3 % / +6.3 % annual heat (24 h activation); flexibility saturates beyond 6 h; insulated houses can coast > 24 h | Simulation |
| Le Dréau & Heiselberg 2016 [17] | DK houses | "Storage" (set-point up) vs "conservation" (set-point down) | Abstract only: emitter type and activation time matter | Simulation |
| Langer & Volling 2020 [16] | DE house, modulating ASHP, UFH, DHW, PV, battery (MILP) | Fixed tariffs | Maximising self-consumption is *not* economical under the tariffs studied; battery essential for self-sufficiency; 24 h horizons cause end effects | Simulation |
| HSLU Solarhaus 2017 [20] | CH house, slow floor heating, 3 months | Weather forecast | Throttles floor heating before sun to avoid overheating; up to +20 % renewable use (simulated) | Field (press) |
| UK Heat Pump Ready programme [25] | Several UK vendors | ToU tariffs + WC (+ PV + battery) | ≥ 20 % bill reduction with WC + ToU; 53 % with PV + battery (Salford lab); 15-40 % vs fixed controls | Mixed, vendor-led |
| heatpumpmonitor.org [4][C] | 553 UK-centred systems, ≥ 80 % of last 365 days | Owners' own scheduling | Cheapest-Agile-rate quartile SPF 3.76 vs 3.92-3.95; half-hourly tariff users 3.74 vs single rate 3.97; effective Agile rate p10-p90 only 20.9-23.4 p/kWh | Field, confounded |
| Octopus Cosy guidance [7][8] | UK | 3 cheap windows (04-07, 13-16, 22-24), peak 16-19 at +50 % | Advises +1-2 °C in cheap windows, −2-3 °C in peaks; DHW at 04:00; fleet SCOP ~3.6 | Manufacturer |

How the evidence lines up:
- Savings reported against **near-optimal baselines** are single digits (Kuboth −9 % cost [12]; Thorsteinsson −2.3 % at the strict comfort level [13]).
- Double-digit figures come from cost-only objectives with wide comfort bands, or from vendor and lab tests against poor baselines [25].
- Every field test that optimised price saw electricity use **rise** [13][14] or efficiency fall [4].

### 4. Pitfalls

1. **Charging at higher flow temperature.** At 2-3 % COP per K [21][33], a +3 K "boost" setpoint costs 6-9 % COP on the stored heat. The ~6 % storage loss [19] then comes on top. Net, a shifted kWh costs ~12-15 % more heat-pump electricity, so the price must be at least ~15 % lower to break even [C].
   - For this unit there is a second problem. The firmware restarts only when the setpoint is ≥ ~4 K above the outlet temperature (owner measurement [36]). A *writing-setpoint-to-start* controller therefore tends to request flow temperatures well above what the slab needs. That leads to catch-up runs at high power: the owner's 3 kW electric draw and 36-39 °C setpoints.
2. **Overheating on sunny days.** In the Danish field test, night boosting plus unreliable cloud forecasts caused overheating, and loss days clustered on high-sun days [13]. The Swiss Solarhaus throttled the floor ahead of the sun on purpose [20]. In the Dutch simulation, absorbed sun closed the storage window [19]. A slab that is still charged when the sun arrives cannot shed heat (sibling note 05 [34]: floor output collapses once the room is ~1 K warm).
3. **Auxiliary heaters taking over.** Pre-charge windows that ask for more power than the compressor can give pull in the immersion or backup heater (Glasgow: most heat from the immersion [14]). Thorsteinsson recommends blocking only the *compressor* for space heating, so that DHW is never taken over by the 10 kW rod [13].
4. **COP model drift.** The Danish team had to refit the heat-pump model 4 times in 97 days; dynamic operation was less efficient than the model predicted [13].
5. **Short tests overstate gains.** Kuboth's 120-hour tests showed −34 % cost against −9 % over 125 days [12]. The Danish savings had not converged after 55 days, with day-to-day noise of ±€3 [13].
6. **Signal chatter and starts.** SG-Ready demands ≥ 10 min signal holds and ≤ 3 blocks per day [5]. evcc uses 5-20 min delays [6]. The cost-optimal DP schedule raised starts from ~2-3 to ~3-4 per day [C]. An optimiser without a minimum-run constraint (e.g. EMHASS [27]) can plan fragments shorter than the unit's minimum run.
7. **PV value can be lower than it looks.** Under Lithuanian net settlement the marginal value of self-consumption may be only ~0.07 €/kWh [23]. Under a pure-feed-in model, Langer & Volling found that maximising self-consumption was not cost-optimal [16].
8. **The tariff can make "efficient" look expensive.** The owner's goal is efficiency (kWh), not money. On a flat tariff, the cost-optimal and energy-optimal schedules are the same (midday + PV). On a dynamic or zoned tariff they diverge: night vs day [12][13][C]. The controller needs an explicit objective setting.

---

## What this means for controlling this house

Confidence labels: **High** = several independent sources plus physics. **Medium** = physics plus one field study, or my own simulation. **Low** = inference.

### A. Decide the objective first (prerequisite, High)

1. Find out:
   - the supply plan: fixed, monthly average, or 15-min spot (e.g. Ignitis Išmanus-15 [24]);
   - the ESO network plan: one, two or four zones [22];
   - the prosumer scheme: per returned kWh, per kW, or percentage [23];
   - the battery's usable capacity.
2. Then pick one of three operating modes. The controller should carry this as a single setting:
   - **Mode E (efficiency / flat tariff, or net-metered with annual surplus):** minimise kWh. Put the unavoidable ON hours in the warmest and sunniest part of the day. Expect −1.5 % kWh at best from timing [C].
   - **Mode C (cost / spot + zoned tariff):** minimise Σ price_h × kWh_h, with an efficiency guard (rule B4). Expect −1 % to −10 % cost without PV and up to −16 % with PV, depending on the band, at 0 to +4 % kWh [C].
   - **Mode P (PV-surplus first):** only worth it if a self-consumed kWh is worth much more than export, i.e. not on the 0.0726 €/kWh returned-energy scheme [23].

### B. Rules that hold in every mode

1. **Below a daily mean of about 0 °C: do not schedule. Run continuously at the lowest flow temperature that holds 22 °C** (High). The house needs ≥ P_min all day ([C] table in §1.3), so shifting needs more power and more flow temperature, and Danish field data show losses at −5-0 °C [13].
2. **From 0 to +12 °C: plan the day as a few long ON blocks at P_min and decide where they go** (Medium).
   - Number of blocks: 1-3 per day. Minimum block length ≥ 2.5-3 h.
   - Block length ≈ (forecast 24 h heat need − forecast solar gain) ÷ P_min.
   - Drift budget per OFF block: ≤ 1 K of slab energy (6.6 kWh), which is ~2-4 h OFF depending on load (§1.3).
3. **Never use a higher flow temperature as the storage mechanism** (High).
   - Charge the slab by running *longer* at the normal low flow temperature (the weather-curve value + 0-1 K), not hotter.
   - Cap any "boost" at **+2 K** over the curve value, and allow it only when the energy price is ≥ ~15 % below the alternative hour, or PV is otherwise exported [19][21][C].
4. **Efficiency guard for Mode C** (Medium). Accept a shifted hour only if price_shift / COP_shift < price_alt / COP_alt × 0.9. The 10 % margin covers the storage loss and model error [13][19]. In practice:
   - In November-February, moving 03:00 → 13:00 is worth it only with PV.
   - Moving 18:00 → 02:00 is always worth it.
5. **Do not run space heating at 17:00-21:00 when the daily mean is above ~0 °C, unless the room is below 21.5 °C** (High for cost, neutral for kWh). This window carries the evening network rate (0.146 €/kWh on the four-zone plan [22]) and +25-45 €/MWh spot [3]. It produced ~66 % of the Danish MPC savings [13].
   - On a flat tariff this rule costs nothing: the evening is no colder than the night.
6. **Solar anticipation** (Medium). If tomorrow's forecast gives ≥ ~1.5 kWh/m² daily GHI (most March-April days, ~half of February, few December days [1]) and the room is already ≥ 22.0 °C:
   - do not pre-charge overnight;
   - let the sun and the midday PV block do it.
   - If the room is ≥ 22.3 °C by 10:00 on a sunny forecast, skip the midday block entirely [13][19][20].

### C. Mode-specific placement (Medium)

| Daily mean T_out | Mode E (kWh) | Mode C (spot + zones) | Mode P (PV first) |
|---|---|---|---|
| < 0 °C | continuous | continuous; keep 17-21 at minimum modulation (do not stop) | continuous |
| 0 to +5 °C | one OFF block ~03-06:00 (coldest, most humid hours) | one OFF block 17-21 (+ morning 08-09 if the band allows) | OFF at night if the battery is empty; ON 10-16 |
| +5 to +12 °C | ON block(s) centred on 13:00 (e.g. 09-17), second block evening if needed | ON 00-06 + ON 11-15 (midday shoulder), OFF 06-10 and 16-22 | ON from first sustained surplus (≥ 1.3 kW for 15 min [6]) to ~16:00; top up 00-05 only if room < 21.7 °C at 22:00 |
| > 12 °C | 1 block 11-16 or none | 1 block in the cheapest 3-4 h | 1 block in PV hours |

### D. Hot water and the legionella heater (Medium-High)

- **DHW once a day, as a tail on a space-heating block.** This avoids an extra compressor start and a separate high-temperature cycle. In Mode E/P, put it in the warmest or PV hour (13-15:00). In Mode C on a spot tariff, put it at 01-05:00, like Havenwise (01:00) [26] and Octopus' Cosy advice (04:00) [8].
- **Legionella disinfection with the electric heater should run only on PV surplus.** A resistive heater has COP 1, so grid electricity spent on it is the most expensive heat in the house; PV that would otherwise be exported is the cheapest.
  - Trigger: forecast surplus ≥ 3 kW for ≥ 1 h.
  - Use a weekly window that slides to the sunniest forecast day.
  - In December-January, fall back to the cheapest night hour on a spot tariff [5][23][C].

### E. How to implement "start/stop at a chosen time" on a Versati driven only by flow setpoint (Medium-Low; check against note 08)

- **To start a block:** write the *target* low flow temperature (the curve value, e.g. 29-31 °C at +5 °C), not a high number. This only starts the compressor if setpoint − outlet ≥ ΔT-Heat.
  - With the register at 4 K, an idle outlet at ~25-26 °C allows starts at ~30 °C setpoints. That is fine.
  - Lowering ΔT-Heat to **2 K** (the documented minimum per note 08 [36]) would let the planner start at the natural flow temperature without "overshoot to start" requests.
- **To end a block:** write a setpoint at or below the current outlet temperature. Per the owner's observation, the unit stops on overshoot.
- **Avoid 30-minute writes that keep moving the target.** Write at block boundaries and on comfort-guard trips only. SG-Ready practice uses ≥ 10 min holds and ≤ 3 hard blocks per day [5].
- **Expected effect:** fewer, longer runs at 3.7-4 kW and 28-32 °C flow. That replaces 3 kW-electric catch-ups at 36-39 °C, which the COP tables put at ~15-25 % worse COP (2-3 %/K × 6-8 K) [21][33].

### F. What to measure to confirm (testable)

1. **A/B by alternating weeks, matched on outdoor temperature and irradiance** (Thorsteinsson matched days on ±0.5 °C ambient and ±2 kWh PV [13]). Run ≥ 6 weeks per arm; savings had not converged after 55 days in [13]. Compare:
   - heat (kWh_th) and electricity (kWh_el);
   - starts per day and mean run length;
   - mean leaving-water temperature while running;
   - cost at the actual tariff;
   - minutes outside 21.5-22.5 °C.
2. **Hour-of-day COP map from the house's own history.** Bin running COP by hour and outdoor temperature (and RH) to check the ~1.5 K / 4-6 % midday advantage and the afternoon defrost benefit.
3. **PV absorption test on 5 sunny shoulder days.** How much surplus does a 10-16 ON block absorb, and does the room exceed 22.5 °C by evening?
4. **Expected outcome (my forecast):**
   - Timing alone: ≤ 2 % kWh.
   - Switching from high-setpoint catch-ups to long low-flow blocks (rules B3 and E): 10-20 % kWh, in line with notes 01/02/06.
   - Mode C on a spot plus two- or four-zone tariff with a ±1 K band: ~5-10 % cost.

---

## Contradictions and open questions

**Contradictions (not averaged away):**

1. **Kuboth's +5.4 % COP from timing [12] vs my ≤ 1.5 % [C].**
   - Kuboth had a 500 L buffer, a German climate with larger daily spreads (December-April, including sunny March), and an MPC that also lowered supply temperatures. Its reference ran mostly at night.
   - My bound assumes a fixed W35 with only the air temperature changing.
   - Both can be right: most of Kuboth's gain is probably flow-temperature and part-load related, not clock-time.
2. **Price vs efficiency direction.**
   - Kuboth (PV, flat price) shifted to daytime and *saved* kWh [12].
   - Thorsteinsson (spot + steep network tariff) shifted to night and *used +9.5 %* kWh [13].
   - The Aalborg simulation flagged the same conflict (cheap night vs warm day; via note 06 [35]).
   - For Lithuania, the price curve (§3.1) says night unless there is PV. The owner's efficiency goal says midday. The controller must expose this choice.
3. **COP-per-K slopes.**
   - Energy Stats UK's single-system daily data show ~0.13-0.20 COP per K of daily mean (≈ 4-5 %/K) [9]. That includes weather-compensation flow reduction as the outdoor temperature rises.
   - Gree's datasheet at a fixed W35 gives ~3.5-3.9 %/K [33][36].
   - Pure clock-time shifting at constant flow only gets the datasheet slope. Using the daily-data slope would overstate the warm-hour value by ~30 %.
4. **heatpumpmonitor penalty vs vendor claims.** Vendors and HPR report ≥ 20 % bill savings [25]. The fleet data show half-hourly-tariff users with *lower* SPF (3.74 vs 3.97) and only ~10 % spread in effective price [4][C]. The fleet data are confounded by self-selection: tariff choice correlates with PV, batteries and EVs.
5. **PVGIS January and February** yield is likely overstated because snow cover on the panels is not modelled. My "Jan 36 %" PV-coverage bound is therefore optimistic.

**Open questions:**

1. Which prosumer settlement and supply plan does the owner have, and is the returned-energy balance annual? This decides whether Mode P or Mode C is worth building [23][24].
2. What is the battery's usable capacity, and is its discharge allowed to feed the heat pump at night?
3. Does the Versati's minimum electrical input fall at warmer air (higher COP at the same 3.7-3.8 kW heat)? If the unit's minimum is a compressor frequency, the minimum *heat* output rises in warm air. That would *increase* forced cycling in midday blocks (unverified; check Word 142/143 per note 08 [36]).
4. The real hour-of-day defrost frequency in Lithuanian humid weather. The frost-risk indicator falls from 0.70 to 0.44 by 14:00 [1][C], but no measured Versati defrost-energy data were found.
5. Which comfort band will the owner accept: ±0.5 K or ±1 K? The value of Mode C differs ~10× between them [C].
6. How large is the house's winter solar aperture? This is needed for rule B6 thresholds. Sibling note 05 [34] lists it as unknown.
7. Exact household zone hours for the ESO two- and four-zone plans: the page gives medium-voltage hours only [22].
8. The 15-min MTU [3][24]. Does sub-hour price structure matter for a slab? Probably not, since blocks are ≥ 2.5 h, but it does matter for DHW and legionella placement.

---

## Sources

1. Historical Weather API, hourly temperature_2m, relative_humidity_2m, shortwave_radiation for Vilnius, 2021-10-01 to 2025-04-30 - Open-Meteo (ERA5-based reanalysis) - accessed 2026-11-06 - https://archive-api.open-meteo.com/v1/archive?latitude=<site>&longitude=<site>&start_date=2021-10-01&end_date=2025-04-30&hourly=temperature_2m,relative_humidity_2m,shortwave_radiation&timezone=Europe%2FVilnius - field data (reanalysis) - Diurnal swing, warmest-window, RH/frost-risk and irradiance statistics (my analysis).
2. PVGIS v5.2 PVcalc, 15 kWp, 35° south, 14 % loss, Vilnius - European Commission JRC - accessed 2026-11-06 - https://re.jrc.ec.europa.eu/api/v5_2/PVcalc?lat=<site>&lon=<site>&peakpower=15&loss=14&angle=35&aspect=0&outputformat=json - lab/model (satellite-based) - Monthly PV yield (Dec 235, Nov 328, Jan 416 kWh; 14 453 kWh/yr).
3. Nord Pool day-ahead prices, LT bidding zone, via Elering NPS price API, Oct-Apr of 2022-23 through 2025-26 - Elering AS - accessed 2026-11-06 - https://dashboard.elering.ee/api/nps/price?start=2025-10-01T00:00:00.000Z&end=2026-04-30T23:59:59.999Z - field data (market) - Hourly/15-min price profiles, night/midday/peak differentials, 15-min MTU since Oct 2025 (my analysis).
4. heatpumpmonitor.org public system list and last-365-day statistics - OpenEnergyMonitor - accessed 2026-11-06 - https://heatpumpmonitor.org/system/stats/last365 (and /system/list/public.json) - field data - SPF by tariff type and by effective Agile price quartile across 553 metered systems (my analysis; confounded).
5. SG Ready label - operating states and signal rules - Bundesverband Wärmepumpe (BWP) - 2025/26 - https://www.waermepumpe.de/normen-technik/sg-ready/ - manufacturer/standard - States 1-4, boost = raised storage setpoints, 10-min holds, ≤ 2 h blocks, ≤ 3 per day, §14a 4.2 kW.
6. Heating / heat pumps (SG Ready, surplus control) - evcc documentation - 2026 - https://docs.evcc.io/en/heating - blog (open-source docs) - Enable/disable thresholds (1300 W/5 min, 150 W/20 min), heat pump keeps the final say, runtime warnings.
7. Cosy Octopus tariff page - Octopus Energy - 2026 - https://octopus.energy/smart/cosy-octopus/ - manufacturer (tariff) - Cheap windows 04-07, 13-16, 22-24 (−51 %), peak 16-19 (+50 %).
8. Cosy controls (blog) - Octopus Energy - n.d. - https://octopus.energy/blog/cosy-controls/ - manufacturer - +1-2 °C in cheap windows, −2-3 °C in peaks, DHW at 04:00, fleet SCOP ~3.6.
9. Real World UK Winter Heat Pump COP Performance - Energy Stats UK - 2024 - https://energy-stats.uk/uk-winter-heat-pump-cop/ - field data (single system, blog) - COP by daily-mean outdoor band (3.1 at −1.5 °C to 5.4 at 11.5 °C); slope ~0.13-0.20 COP/K incl. weather compensation.
10. Havenwise Review: My Experience with a Vaillant Heat Pump - Energy Stats UK - 2025/26 - https://energy-stats.uk/havenwise-review-vaillant-heat-pump/ - blog - Optimiser with tariff optimisation off; no measured savings; flow overshoot needed capping; comfort steadier.
11. Wärmepumpen heizen auch im Altbau klimafreundlich (WP-QS im Bestand, press release) - Fraunhofer ISE - 3 Nov 2025 - https://www.ise.fraunhofer.de/content/dam/ise/de/documents/presseinformationen/2025/3025_ISE_PI_Waermepumpen-heizen-auch-im-Altbau-klimafreundlich.pdf - field data - 77 systems; ASHP JAZ 3.4; 6 HP+PV houses: 25-40 % autarky without a battery, 32-62 % with one; oversizing and high switching frequency.
12. Experimental Long-Term Investigation of Model Predictive Heat Pump Control in Residential Buildings with Photovoltaic Power Generation - Kuboth, Weith, Heberle, Welzl, Brüggemann, Energies 13:6016 - 2020 - https://epub.uni-bayreuth.de/5598/1/energies-13-06016.pdf - lab (twin rigs, real ASHP, real weather) - Shift to after 10:00; −4.1 % kWh, +5.4 % COP, +107.7 % PV self-consumption, −9 % cost; weak December-February.
13. Long-term experimental study of price responsive predictive control in a real occupied single-family house with heat pump - Thorsteinsson et al., Applied Energy 347 (arXiv 2303.16289) - 2023 - https://ar5iv.labs.arxiv.org/html/2303.16289 - field data - DK concrete-floor AWHP; cost −12.4 %, kWh +9.5 %; savings best at 0.7-4 °C; 17-21 block = 66 % of savings; sunny-day overheating; 4 model refits; recommendations.
14. Simulation, implementation and monitoring of heat pump load shifting using a predictive controller - Allison, Cowie, Galloway, Hand, Kelly, Stephen, Energy Conversion and Management 150 - 2017 - https://strathprints.strath.ac.uk/60566/ - field data (abstract) - UFH pre-charging; comfort OK; immersion supplied most heat.
15. Schlaue Wärmepumpe (Viessmann Vitocal smart features review) - 42watt - 2026 - https://42watt.de/magazin/schlaue-warmepumpe - blog (trade press) - Dynamic Assistant shifts time, not kWh; cost benefit largely gone without a dynamic tariff; PV priority; §14a.
16. An optimal home energy management system for modulating heat pumps and photovoltaic systems - Langer and Volling, Applied Energy (arXiv 2009.02349) - 2020 - https://arxiv.org/abs/2009.02349 - paper (simulation) - Maximising self-consumption not economical under the tariffs studied; battery essential; 24 h horizon end effects.
17. Energy flexibility of residential buildings using short term heat storage in the thermal mass - Le Dréau and Heiselberg, Energy 111:991-1002 - 2016 - https://ideas.repec.org/a/eee/energy/v111y2016icp991-1002.html - paper (simulation; abstract only) - Storage (set-point up) vs conservation (set-point down); emitter type and activation time matter.
18. Influence of envelope, structural thermal mass and indoor content on the building heating energy flexibility - Johra, Heiselberg, Le Dréau, Energy and Buildings 183 - 2019 - https://vbn.aau.dk/ws/files/290247579/Influence_of_envelope_structural_thermal_mass_and_indoor_content_on_the_building_heating_energy_flexibility_accepted_manuscript.pdf - paper (simulation) - +3.3 %/+6.3 % heating use for 24 h storage; saturation beyond 6 h; cheap windows rarely > 6 h; coasting > 24 h in insulated houses.
19. Thermal Storage in a Heat Pump Heated Living Room Floor for Urban District Power Balancing - van Leeuwen, de Wit, Fink, Smit, SMARTGREENS 2014 - 2014 - https://www.scitepress.org/Papers/2014/49163/49163.pdf - paper (simulation) - 1.6 kWh per 2 h pulse; 6 % extra loss; storage price must be ≥ 6 % below normal; solar absorption limits storage (21.3 °C vs a 20-21 band).
20. Dank Wetterbericht Energie und Heizkosten sparen (press release) - Hochschule Luzern - 2017 - https://www.hslu.ch/en/lucerne-university-of-applied-sciences-and-arts/about-us/media/medienmitteilungen/2017/10/25/dank-wetterbericht-energie-und-heizkosten-sparen - field data (press) - Forecast-based throttling of a slow floor before sun; up to +20 % renewable use (simulated).
21. Combined optimization of heat pumps and heat emitting systems (OPSYS) - S. Ø. Jensen, Danish Technological Institute - 2018 - https://www.teknologisk.dk/_/media/72043_OPSYS%20main%20report.pdf - paper/test rig - +1 K forward temperature ≈ −2-3 % COP; only ~15 % of 160 Danish heat pumps perform as expected; up to 25 % combined savings potential.
22. Tarifų planai ir kainos 2026 metais (distribution tariff plans and prices 2026) - ESO (Energijos skirstymo operatorius) - 2026 - https://www.eso.lt/namams/elektra/tarifu-planai-kainos-atsiskaitymas/tarifu-planai-ir-kainos-2026-metais/4801 - tariff (regulated) - One-, two- and four-zone household network prices (two-zone Standartinis: day 0.129 / night 0.071; four-zone evening 0.146 €/kWh).
23. Gaminančių vartotojų atsiskaitymo būdai 2026 metais (prosumer settlement methods 2026) - ESO - 2026 - https://www.eso.lt/namams/elektra/tarifu-planai-kainos-atsiskaitymas/gaminanciu-vartotoju-atsiskaitymo-budai-2026-metais/4829 - tariff (regulated) - 0.0726 €/kWh for returned energy (LV), 5.03 €/kW/month, or 37 %/21 % retention.
24. Išmanus-15 elektros tiekimo planas - Ignitis - 2026 - https://ignitis.lt/ismanus-15-elektros-tiekimo-planas - manufacturer (supplier) - 15-min Nord Pool price + supplier share + regulated part + VAT; prices published after 15:00; smart meter required.
25. Smart and Flexible Heat Pumps: Learnings from the Heat Pump Ready programme - DESNZ / Carbon Trust - 2025 - https://assets.publishing.service.gov.uk/media/6978d7f1d6ab92f1d3a4d6cd/thematic-report-smart-innovative-heat-pumps-hpr.pdf - mixed (vendor-led field/lab) - ≥ 20 % bill reductions with WC + ToU; 53 % with PV + battery; 15-40 % vs fixed controls.
26. Display optimisers in heatpumpmonitor.org - OpenEnergyMonitor community - 2025 - https://community.openenergymonitor.org/t/display-optimisers-in-heatpumpmonitor-org/29013 - forum - Havenwise DHW at ~01:00, skips small top-ups; "no amount of COP can outrun off peak electricity"; oversizing limits optimiser gains.
27. Thermal battery for heat pump optimization - EMHASS documentation - 2025/26 - https://emhass.readthedocs.io/en/latest/thermal_battery.html - blog (open-source docs) - Slab as a lumped battery, Carnot-fraction COP, no minimum-power or minimum-runtime constraint.
28. On heat pumps in smart grids: A review - Fischer and Madani, Renewable and Sustainable Energy Reviews 70:342-357 - 2017 - https://ideas.repec.org/a/eee/rensus/v70y2017icp342-357.html - paper (review; abstract) - Three application classes; most studies use predictive control under idealised assumptions; calls for field trials.
29. Comparison of control approaches for variable speed air source heat pumps considering time variable electricity prices and PV - Fischer, Bernhardt, Madani, Wittwer, Applied Energy 204:93-105 - 2017 - https://ideas.repec.org/a/eee/appene/v204y2017icp93-105.html - paper (simulation; abstract) - Four rule-based controllers vs convex MPC across flat, time-variable and PV cases; complexity vs benefit (no numbers in the abstract).
30. NIBE F370 installer manual, Smart price adaption (p. 51) - NIBE (via manualslib) - n.d. - https://www.manualslib.com/manual/1590978/Nibe-F370.html?page=51 - manufacturer - Cheapest-hours shifting; room effect 1-10 (default 5), hot water 1-4 (default 2).
31. The Holy Trinity and Renewable Quintessentials - Energy Stats UK - n.d. - https://energy-stats.uk/the-holy-trinity-and-renewable-quintessentials/ - blog - Qualitative: winter PV does not line up with heating demand; batteries move surplus to the evening (no numbers; minor).
32. WP-QS im Bestand project page - Fraunhofer ISE - 2025 - https://www.ise.fraunhofer.de/de/forschungsprojekte/wp-qs-im-bestand.html - field data (project page) - Project aims on PV + battery self-consumption; full results in the final report (not read; 19 MB).
33. Versati III Split datasheet (Spanish), capacity/COP at A7/A−7 × W35/45/55 - Gree Products Spain (via remle.com), cited through sibling note 08 - ~2023 - https://cdn01.remle.com/IMATGES/F557/7017011.pdf - manufacturer - 10 kW split: COP 4.61/3.60/2.59 at A7 and 2.81/2.23/1.58 at A−7 (W35/45/55); 2.1-2.9 %/K flow penalty. Not re-read by me; values taken from note 08.
34. Researcher note 05: UFH slab control - this project, docs/research/notes/05-ufh-slab-control.md - 2026 - (local file) - internal research note - Coast-time arithmetic, solar-gain/overheating evidence, floor self-regulation.
35. Researcher notes 02 (flow temperature and COP) and 06 (MPC academic) - this project, docs/research/notes/02-flow-temperature-cop.md, 06-mpc-academic.md - 2026 - (local files) - internal research notes - Defrost cost range, COP per K, Aalborg price-vs-COP conflict, MPC field summaries.
36. Researcher note 08: Gree Versati - this project, docs/research/notes/08-gree-versati.md - 2026 - (local file) - internal research note - Versati COP table, ΔT-Heat restart behaviour (2-10 K), Word 142/143 compressor Hz registers.
