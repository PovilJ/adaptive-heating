# On/off cycling: causes, costs, cures

Research note 03 of the heat-pump efficiency sweep. Scope: what a compressor start costs, how long a run must be before the cost stops mattering, what wears the compressor, why mild weather forces cycling, and which cures have evidence behind them. It ends with what all this means for this house: a Gree Versati 9 kW-class unit, a concrete-slab UFH system, minimum output above the mild-weather load, and a flow setpoint written over Modbus.

Method and limits. I ran 24 web searches in English, German, Polish, Swedish, Dutch and Lithuanian before the shared search budget ran out. I then fetched pages directly (papers, manufacturer manuals, field-trial reports, forums and blogs) and parsed the PDFs locally. I also ran my own cross-sectional analysis of the public heatpumpmonitor.org 365-day dataset (n = 513 systems after quality filters). That analysis is the main new field evidence in this note. Several key papers (Uhlmann & Bertsch, Dongellini & Morini 2019, Madonna) were paywalled or blocked. Where only an abstract or search snippet was available, I say so.

Evidence ranking used: measured field data > controlled lab test > peer-reviewed simulation > manufacturer claim > forum anecdote.

## Summary

- **For this house, cycling itself is probably not the main efficiency leak. The main leaks are high water temperature and high compressor speed during catch-up runs.** In 513 monitored homes, each extra 1 K of mean flow temperature cost about 0.09 COP (about 2.3 %/K) [4]. Going from 4 to 8 starts per day with runs of an hour or more costs about 1 %, by my per-start estimate built on [5][4]. Confidence: medium-high.
- **Penalty by run length (field data).** Systems whose average run (run hours ÷ starts) was under 15 min had about 19 % lower COP than their flow and outdoor temperatures predict. At 15–30 min the shortfall was 6–8 %, and at 30–45 min it was 4–6 %. From about 45–60 min upward there was no penalty, with a plateau of 0 to +5 % [4]. Normalised to % of Carnot for space heating only, the same shape appears: −4.9 % at 15–30 min, −3.9 % at 30–45 min, about 0 from 60 min up [4].
- **Lab thresholds are much shorter than the field knee.** EA Technology's test-house work on fixed-speed ASHPs found runs over about 6 min avoid the worst losses, and about 8 min gave close to catalogue COP [1][2]. Uhlmann & Bertsch report 2–5 % penalties only for very short cycles and none above about 15 min (abstract only) [11]. The field knee at 45–60 min is longer than any lab threshold, which suggests short average runs also signal other system problems.
- **Physics of a start.** Off-cycle refrigerant migration and redistribution is the dominant start-up loss. It can cost up to about 11 % COP in an air-to-water lab rig, or about 6 % with migration control [8]. Manufacturer transient data for one air-to-water unit: heat output is on average 42 % low for the first 150–250 s, while electric input is only 4 % low for 75 s [5]. In MERL's simulation, capacity took 723 s to rise after a 20-min off period, and removing migration cut cycling losses by more than 95 % [7].
- **Per-start cost for a 3.75 kW minimum-output unit.** Using [5]'s transient data, the heat deficit is about 0.07–0.11 kWh per start. That is 10–18 % of a 10-min run, 3.5–6 % of a 30-min run, 1.8–2.9 % of a 60-min run, and under 1 % of a 3-h run (my calculation). This shape matches the field curve in [4].
- **Wear limits are far above what this house needs.**
  - Copeland scroll: at most 10 starts per hour, no minimum off time, and a minimum run time set by oil return [15].
  - Copeland variable-speed scroll: at least 1 min off before a restart, plus an oil-circulation routine below 1800 rpm [16].
  - Bitzer: at most 6 starts per hour with R290 and frequency inverters, 12 for others [17]. EA Technology says most manufacturers cap at 6 per hour [2].
  - Gree: the compressor can restart only after at least 3 min stopped, and Gree says frequent start/stop is bad for oil return [19].
  - At 2–8 starts per day (about 700–3,000 per year), wear is not the binding constraint.
- **Why mild-weather cycling is unavoidable here.** Minimum output (3.7–3.8 kW) equals the house load only at roughly −5 °C (if H = 0.14 kW/K) to +3 °C (if H = 0.20 kW/K). Above that, the unit must cycle. At +10 °C it needs about 10.8 h of running per day at minimum output (my calculation).
- **The real cost of forced cycling is extra lift.** Pushing 3.75 kW into a slab that needs 1.7 kW raises the water-to-room temperature difference by an estimated 3–7 K, or about 7–16 % COP, depending on the unknown floor UA (my physics estimate, low-medium confidence). Starts add only about 1–3 % on top. This is why timing pulses to the warmest hours and PV matters more than start count.
- **The slab is a huge buffer.** 6.6 kWh/K is about 5,700 L of water per kelvin. At +10 °C, 3–6 pulses per day of 1.8–3.6 h each move the slab only about 0.6–1.1 K (lumped estimate). Siemens/HSLU work on concrete-core systems shows multi-hour pulse-width operation (5-h period in their example) is a standard control method [33].
- **Buffer tanks and low-loss headers do not fix cycling in practice.** In the field set, buffered systems had about 7 % lower raw COP and ran 1.1 K hotter (residual −3.8 %), with *shorter* median runs than unbuffered systems (74 vs 95 min) [4]. A small 4-pipe buffer (about 8 L/kW) did help where runs would otherwise be 2–4 min [1]. Simulation puts the optimum for direct systems at 4–9 L/kW [5]. A slab house needs neither.
- **Zoning and closing loops cause short cycling.** Closing TRVs and zones shrinks emitter capacity and water volume and drives runs down to 1.6–4 min [1][2]. Owners fixed cycling by opening loops and removing zone control [22][23][30]. Keep every UFH loop open, with no room actuators.
- **Gree firmware facts that matter for control.**
  - Compressor frequency is set from leaving-water temperature minus setpoint: a bigger gap means a higher frequency [19].
  - The unit stops when it is already at minimum frequency and the water is still well above setpoint [19].
  - The leaving-water ΔT for heating (Δt2) ranges 2–10 K, and the default in the Versati III and II+ manuals is **10 K**. The house uses 4 K [19][20].
  - "Heat run time" (1–10 min, default 3 or 5 min) sets how long the unit idles in the standby zone before it stops [19].
  - Consequence: big setpoint steps to force a restart also force high frequency. That probably explains the ~3 kW catch-up draw at +2 °C.
- **Rule-of-thumb targets.** Mean run of at least 60 min, preferably 90–240 min, in mild weather. Under 1 start per running hour (field penalty above 1.5 per hour [4]). No runs under 20–30 min except for protection. About 2–6 starts per day in mild weather and about 1–3 below the balance point. These targets also match blog and forum guidance: under 1 cycle/h is "good" [26], and runs of 20+ min with at most 3 starts per hour are commonly advised (forum) [29][31].
- **The standard's correction is weak and probably optimistic.** EN 14825's default cycling coefficient for water-based units (Cdh = 0.9) implies an 11 % penalty at 45 % capacity ratio and 29 % at 20 % [5]. Madonna et al. are quoted as finding that 0.9 tends to understate real losses [5]. Field evidence suggests the real cost depends far more on run length than on capacity ratio [4][24].

## Detailed findings

### 1. What a start costs: mechanisms and lab/simulation numbers

**Mechanisms, in order of importance**

1. *Refrigerant migration during the off period, then redistribution at restart.* When the compressor stops, refrigerant flows from the high-pressure side into the evaporator. At restart it must be pumped back before the condenser works properly [7][9][18].
   - Tassou & Votsis measured up to **11 % COP loss** from migration in a domestic air-to-water heat pump. Controlling migration cut the loss to about **6 %** [8].
   - An ORNL lab study on an air-to-air unit got the best cycling COP by isolating refrigerant in the indoor coil during the off period. Refrigerant dynamics caused noticeable delays before steady COP was reached [9].
2. *Thermal mass warm-up.* The plate heat exchanger, the water in the unit and the pipes, and the compressor shell cool during the off period and must be reheated. Dongellini models this with two penalty factors at start-up: one on delivered heat and one on electric input [5].
3. *Oil logistics.* Each start drops crankcase pressure. Oil foams and is pumped into the circuit and must come back before the next stop. Hence the minimum-run-time rules [15][16][18], and Gree's note that frequent start/stop is bad for oil return [19].
4. *Parasitic energy around the start.* Pump pre- and post-run, controls, and in some units boost heaters that fire at every start. RHPP found one ASHP whose boost heater came on at every space-heating start [3].
5. *The lift penalty of delivering heat in bursts.* To deliver an average load L while running at output P > L, the emitters must take P during the on-time. That needs a higher water temperature than continuous operation at L would. This is a thermodynamic penalty, not a start penalty. John Cantor is cited on forums as making this point [24], and it is the mechanism behind section 5 below.

**Transient magnitudes**

- Manufacturer data for a thermostatic-expansion-valve air-to-water unit [5]:
  - Electric input runs 4 % below steady state for 75 s.
  - Delivered heat runs on average 42 % below steady state for 150 s (in the text) or 250 s (in Table 4.8). This internal inconsistency is flagged under Contradictions.
- MERL first-principles simulation of an ASHP, 20-min off then 60-min on [7]:
  - Heating-capacity rise time was **723 s** with a conventional accumulator and 168 s with a regenerative accumulator.
  - Preventing migration cut cycling losses by more than **95 %**. The regenerative accumulator cut them by 60 %.
  - Average COP over the 1-h on-cycle improved by 2.5 %.
- Uhlmann & Bertsch (Purdue conferences; I only saw abstracts and snippets, the full text returned 403) [11]:
  - Very short cycles cost about **2–5 %**.
  - The loss becomes insignificant when runs last **15 min or longer**.
  - A separate 2010 paper gives a wider 5–30 % range for capacity reduction due to cycling.
- Fuentes, Waddicor & Salom tested a 40.5 kW water-to-water unit with system inertia between 1.23 and 24.7 L/kW [10]:
  - Part-load degradation depended strongly on inertia.
  - Start-up losses were "non-negligible", especially at low inertia.
  - They argue EN 14825 should account for inertia and start-up loss explicitly.
- A GreenBuildingAdvisor installer anecdote (Rheem system): the first minute is almost wasted and it takes about 15 min to reach peak performance [27]. This is anecdotal and for an air-to-air ducted system.

**My per-start arithmetic for this unit (Pmin = 3.75 kW)**

| Assumed transient | Heat deficit per start | 10 min | 20 min | 30 min | 45 min | 60 min | 90 min | 120 min | 180 min | 240 min |
|---|---|---|---|---|---|---|---|---|---|---|
| 42 % × 150 s [5] | 0.066 kWh | 10.5 % | 5.2 % | 3.5 % | 2.3 % | 1.8 % | 1.2 % | 0.9 % | 0.6 % | 0.4 % |
| 42 % × 250 s [5] | 0.109 kWh | 17.5 % | 8.8 % | 5.8 % | 3.9 % | 2.9 % | 1.9 % | 1.5 % | 1.0 % | 0.7 % |
| ~50 % × 723 s (MERL sim, upper bound) [7] | 0.377 kWh | 60 % | 30 % | 20 % | 13 % | 10 % | 6.7 % | 5.0 % | 3.3 % | 2.5 % |

- The first two rows fit the field curve in section 2 well. The MERL row is an upper bound: a conventional design, 20 min off, no migration control.
- **Takeaway:** above about 90 min, the start cost is at most about 2 % even with pessimistic transients.

### 2. Field data: does cycling show up in real seasonal performance?

**heatpumpmonitor.org: own analysis (field data, cross-sectional, n = 513) [4]**

*Data and method*
- Data: public `system/stats/last365` (856 systems) joined with `system/list/public.json`, retrieved 2026-11-06. 792 records were transcribed through page reads and cross-checked against the raw JSON with 0 mismatches.
- Filters: at least 292 days of data, heat and electricity data quality of at least 90 %, combined COP between 1.5 and 7, at least 50 starts.
- Starts are counted from electricity crossing about 100 W. Pump power can distort the count [21].
- Mean run length = running time ÷ starts.

*Distribution*
- Median 6.0 starts/day (IQR 4.0–8.4).
- Median mean run 91 min (IQR 57–145).
- 7 % of systems average under 30 min per run. 72 % average 60 min or more.

*COP against flow temperature*
- Combined COP falls **−0.091 per K of mean running flow temperature**, about −2.3 %/K. The regression also includes outdoor temperature (R² 0.33).

*COP shortfall against that regression, by mean run length*

| Mean run | n | Mean residual | Median residual | Median starts/day |
|---|---|---|---|---|
| < 15 min | 7 | −19 % | −19 % | 68 |
| 15–30 min | 30 | −6 % | −8 % | 20 |
| 30–45 min | 49 | −4 % | −6 % | 12 |
| 45–60 min | 58 | 0 % | +2 % | 8.7 |
| 60–90 min | 108 | 0 % | +1 % | 7.0 |
| 90–120 min | 95 | +2 % | +2 % | 5.7 |
| 120–180 min | 79 | 0 % | +2 % | 4.2 |
| 180–300 min | 55 | +5 % | +4.5 % | 3.0 |
| > 300 min | 32 | 0 % | −1 % | 1.8 |

*Other cuts of the same data*
- **Space heating, % of Carnot.** This metric removes the temperature-lift effect, using space-heating data only (n = 345).
  - +0.84 percentage points of Carnot per doubling of run length (95 % CI about 0.33–1.3 pp), on a median of 49.1 %.
  - By bin against the median: 15–30 min −4.9 %, 30–45 min −3.9 %, 45–60 min −1.2 %, 60–180 min about 0, 180–300 min +4 %.
- **Starts per day.** 20–40 per day: −8 %. Over 40 per day: −16 %. Up to 12 per day: within ±2 %.
- **Starts per running hour.** Under 1: +1 to +2 %. 1.5–3: −6 to −7 %. Over 4: −19 %.
- **UFH systems (n = 178).**
  - Median 5.5 starts/day and a 98-min mean run.
  - Runs under 30 min: −9 %. 30–60 min: −3 %. 60 min or more: +1 to +2 %.
  - UFH systems had lower flow temperature (33 vs 35 °C) and higher COP (4.0 vs 3.8) than radiator systems.
- **Duty (share of the year running).**
  - Under 20 %: −9 %. 20–30 %: −2 %. 50–60 %: +2.4 %. Above 60 % (n = 20): −1.4 %. A unit that runs long and slow is the efficient one; the very-high-duty group is probably undersized or cold-climate.
  - Oversizing (nameplate over 2× design heat loss, n = 10): −8.8 %.
- **Manufacturer firmware matters.**
  - Samsung (n = 24): median 13.7 starts/day, 39-min runs, −6.8 %.
  - Viessmann (n = 42): 3.7 starts/day, 200-min runs, +0.3 %.
  - Grant (n = 27): 2.9 starts/day, 198-min runs, +2.8 %.

*Caveats*
- The data is cross-sectional and mostly from UK homes.
- Short average runs correlate with other faults: poor emitter sizing, zoning and controls.
- Combined COP includes hot water, although a %-of-Carnot space-only check shows the same shape.
- So the penalty in the 15–45 min bins is an upper bound on the pure start cost. The near-zero penalty from about 60 min upward is the robust part.

**RHPP (UK government-funded monitoring, ~700 heat pumps, 2-min data) [3]**
- The most common median on-to-on cycle per site-month was **10 min for ASHPs** and 18 min for GSHPs.
- 49 % of ASHP sites had at least one month where this was the median.
- In 25 % of ASHP sites, every month had more than 10 % of cycles shorter than 12 min.
- Short cycling occurred in both space heating and DHW mode, in any season. One ASHP on UFH swung its flow temperature on about a 6-min period in winter.
- They found **no clear relationship** between median cycle length and monthly COP, and blamed heat-meter noise.
- Load factor showed only a weak association with COP, and only below about 20 % load factor.
- One ASHP at 5 % load factor ran a few long hours per day at reasonable COP. So low utilisation is fine if runs are long.
- Well-performing fixed-speed GSHPs cycled at about 30 min on, 30 min off with COP around 3.

**Owner measurements**
- Kev M, 14 kW Ecodan, about 9–10 °C ambient, about 36 °C flow, forum [24]:
  - Cycling at about 2 starts per hour (15 starts in 7 h) gave COP 4.5.
  - Continuous running gave COP 3.9.
  - In another comparison, up to 3 starts per hour gave COP 4.4.
  - Conclusion: mild cycling was not measurably harmful there. Others pointed out these were not controlled tests.
- Arne Madsen, Samsung 8 kW, oversized for a 4–5 kW load [22]:
  - Before: about 150–180 starts/day, 7–8 per hour, COP about 2.5.
  - After: 1–2 starts/day with near-continuous running at 600–900 W input, COP about 4.
  - Starts and setpoint behaviour changed together, so the cause is mixed.
- Energy Stats UK, 5 kW Vaillant [26]: annual average 0.64 starts per running hour (2,575 starts over 4,040 h). Mild days at 7–9 °C showed 4–5 cycles in 5–7 h. Firmware 351.06.07 double-counted the energy integral and caused extra cycling until fixed.

**Lab evidence on minimum run time (EA Technology, fixed-speed 6 kW ASHP and GSHP in a 200 W/K test house)**

*Findings*
- Runs under 6 min cut COP for both, much more for the ASHP. Above 4–8 min, cycling had little visible effect [1][2].
- 2-radiator reference zone: runs of 5–7 min with COP below the long-run line.
- 1 radiator: 2–4 min runs and a much larger COP drop [1].
- GSHP with 1.6–2.4 min runs: worst-case COP loss of about **16 %** [1].

*Recommendations* [1]
- Design for at least 6 min.
- About 8 min gave the ASHP near-catalogue COP.
- The GSHP had a performance optimum at 10–15 min.

*Important twist* [1]
- Short runs caused by the **room thermostat** had better COP than longer runs caused by return-temperature cut-out. In the ASHP case this was a 2.9-min run with notably higher COP than other runs of similar length.
- The reason was lower flow and return temperatures: *temperature beat run length*.
- The authors still advise against this, because short runs are bad for oil circulation and reliability.

### 3. Compressor wear and manufacturer limits

| Source | Starts limit | Off-time rule | Run-time rule |
|---|---|---|---|
| Copeland ZR*KRE scroll guidelines [15] | ≤ 10 starts/h | no minimum off time (scroll starts unloaded) | minimum run = time for start-up oil loss to return to sump; shorter cycling "will result in progressive loss of oil" |
| Copeland XHV variable-speed HP scroll [16] | ≤ 10 starts/h | ≥ 1 min since last stop; pressure difference < 10 bar at start | oil-return test required; below 1800 rpm an oil-circulation routine must run; reach the envelope fast at start |
| Bitzer KT-420 (reciprocating, FI) [17] | ≤ 6/h (R290, R1270, R744, H-series); ≤ 12/h others | — | longer minimum run times at low motor speed (oil return) |
| Danfoss guidance as compiled by Mimer/DECC [18] | about 10–12 starts/h; extra starts shorten service life | anti-short-cycle timer; a 3-min delay between starts recommended | must guarantee minimum run for motor cooling and oil return |
| Gree Versati III [19] | — | restart only after the compressor has been stopped ≥ 3 min | "Heat run time" 1–10 min; frequent start/stop is bad for oil return |
| EA Technology on the market at the time [2] | most manufacturers cap at about 6 starts/h | — | — |
| Dongellini thesis [5] | 6 on/off per hour treated as the manufacturer maximum | — | — |
| 42watt (German blog, unsourced) [28] | about 100,000-start "rule of thumb" life; < 2,000/yr optimal, > 4,000/yr critical | — | runs ≥ 20 min good, < 10 min critical |

- **Contradiction:** the limits range from 3 to 12 starts per hour. Swedish and Dutch forum lore says at most 3 per hour and at least 20–30 min [31][30]. Compressor makers allow 6–12 per hour.
- **For this house:** the starts budget is not the binding constraint. Efficiency and oil management (the case for long runs at low speed) are.

### 4. Why cycling happens (and why mild weather is the problem)

- **Minimum output above the load.** Every inverter has a minimum compressor speed. Below the outdoor temperature where load equals minimum output, the unit can only cycle [5][35].
  - In Dongellini's simulation the inverter unit did no on/off cycling at all on days averaging below 5 °C, which is 45 % of the season.
  - It peaked at about 90 starts per day on 16 °C days with a low-inertia fan-coil system and a 200 L tank [5].
  - NEEP/PNNL list little overlap between the modulation range and the house load line as a sizing error that causes excessive short cycling [35].
- **Oversizing.** In the field, units over 2× the design heat loss scored −8.8 % [4]. Madani et al. found an on/off GSHP sized for 65 % or more of peak load gives an SPF about equal to a variable-speed unit. Sizing for only 55 % pushes about 10 % of annual heat onto the electric backup and lowers SPF [13].
- **Hysteresis that is too tight.**
  - With a multi-stage unit in simulation, Dongellini found halved dead bands produced *more* cycles than the single-stage unit.
  - Doubling the dead band from 2.5 to 5 K above the modulation range cut seasonal starts by 60 % (10,335 to 4,272) and raised SCOP from 2.93 to 2.99 [5].
  - Owners and installers in German and Swedish communities widen hysteresis or degree-minute start thresholds to lengthen runs. NIBE's default compressor start is −60 degree-minutes, and more negative values mean fewer, longer runs [29][31].
  - Vaillant's equivalent is the energy-integral start threshold, default −60, sometimes moved to −100 [23].
- **Shrinking the hydraulic circuit.** TRVs, zone valves and UFH actuators reduce emitter capacity and water volume, so runs collapse [1][2][22][30]. The Dutch Evohome/Itho UFH case: the relay ran 5–10 min at a time with all zones on. Replies said Itho reportedly requires at least a 30-min run command [30].
- **External on/off controls fighting the heat pump's own modulation.** Room thermostats and smart thermostats act as on/off switches [26][30].
- **DHW.** RHPP found DHW cycles that ran too long or re-triggered repeatedly, with the cylinder thermostat re-calling heat within minutes [3]. Every DHW cycle that interrupts space heating adds at least one start.
- **Firmware bugs and counters.** Example: the Vaillant energy-integral double-count [26].

### 5. The "lift" cost of forced cycling (the bigger hidden cost)

- To deliver average load L with a compressor that cannot go below P, the emitter must reject P during the on-time.
- For an emitter with conductance UA (water to room), the extra mean water-to-room temperature difference is roughly (P − L)/UA. Each kelvin of extra condensing temperature costs about 2.3 % COP [4].
- Estimates for P = 3.75 kW (my calculation; UA for this floor is unknown, so measure it):

| Floor UA (kW/K) | L = 1.0 kW | L = 1.7 kW (+10 °C) | L = 2.5 kW |
|---|---|---|---|
| 0.3 | +9.2 K (≈21 %) | +6.8 K (≈16 %) | +4.2 K (≈10 %) |
| 0.4 | +6.9 K (≈16 %) | +5.1 K (≈12 %) | +3.1 K (≈7 %) |
| 0.5 | +5.5 K (≈13 %) | +4.1 K (≈9 %) | +2.5 K (≈6 %) |
| 0.7 | +3.9 K (≈9 %) | +2.9 K (≈7 %) | +1.8 K (≈4 %) |

- This explains why "cycling" looks expensive in many anecdotes: the high water temperature during the burst is the cost, not the start [1][24].
- It also explains EN 14825's capacity-ratio formula, which penalises low capacity ratios steeply: Cdh = 0.9 gives a factor of 0.89 at CR 0.45 and 0.71 at CR 0.2 [5].
- What reduces it: a larger effective UA (all loops open, higher flow rate), letting the slab float (lower water temperature at pulse start), and running pulses when outdoor air is warmest. A warmer source offsets the higher sink temperature, by the same Carnot logic.

### 6. Cures and their evidence

**6.1 Lower flow temperature (and a lower curve)**
- Strongest lever: about −2.3 % COP per +1 K of flow temperature, cross-sectionally [4].
- EA Technology: short runs at low flow temperature beat longer runs at high flow temperature [1].
- Polish guidance on curve shaping treats it as a two-end adjustment and an iterative, often season-long process [32].
- Caveat: lowering the curve *does* lengthen off-times, but cannot remove cycling when minimum output is above the load (German forum consensus [29]).

**6.2 Larger restart hysteresis or start thresholds**
- Simulation: 2.5 → 5 K dead band gave −60 % starts and +2 % SCOP [5].
- Community practice is to widen it (NIBE degree minutes −60 → −100 to −120; Vaillant −60 → −100) [23][29][31]. Forum users warn that longer runs overshoot more [31].
- Gree's own default for leaving-water ΔT in heating (Δt2) is **10 K** (range 2–10) [19][20]. The 4 K used in this house is far tighter than factory.

**6.3 Buffer tanks and volumisers (and their mixing penalty)**
- *For:*
  - A 4-pipe buffer at about 8 L/kW lengthened runs and raised COP where runs would otherwise be 2–4 min. It made no difference where runs were already about 6 min [1].
  - Simulation optimum for direct systems: 6.7–9.3 L/kW (single-stage) and 4–7 L/kW. Over 15 L/kW is only worthwhile with indirect, variable-flow secondary circuits [5].
- *Against:*
  - Field buffer systems ran 1.1 K hotter, scored 7 % lower raw COP (−3.8 % after adjusting for temperature) and had *shorter* median runs [4]. Low-loss-header systems ran at 37.6 °C average flow with 11.5 starts/day [4].
  - Forum moderators estimate 2–3 % efficiency lost per 1 K drop across a header (unsourced) [25].
  - A volumiser adds volume but does not stop cycling unless heat is drawn from it (installer comment) [22].
- *For a slab house:* irrelevant. 6.6 kWh/K of slab is about 5,700 L of water per kelvin. Gree's own minimum water volume is only 20 L [19].

**6.4 Open all loops and remove zoning**
- Strong lab support [1][2]. Strong practitioner consensus [22][25][26][30].

**6.5 Pump settings**
- The Gree pump modulates speed on the inlet/outlet temperature difference [19].
- Too little flow raises the water temperature for a given output. Arne's system ran 13 l/min at the installer's 70 % pump speed and 18.5 l/min at 100 %; low flow gave poor COP and cold far ends [22].
- RHPP flags pumps running continuously as a parasitic load [3].
- For the slab: aim for a modest temperature difference (about 3–5 K) at minimum output, and confirm pump behaviour in standby.

**6.6 Use the slab as the buffer: few, long pulses at minimum output**
- Concrete-core systems are routinely run with pulse-width modulation (example period 5 h). The energy per period is matched to what continuous operation would deliver, against a 24-h moving-average outdoor temperature [33].
- Long low-load runs are not inherently inefficient: RHPP's 5 % load-factor site ran a few long hours per day at reasonable COP [3].
- In the field data, mean runs of 3–5 h scored best (+4–5 %) [4].
- Dongellini's MSHP case, with a wider dead band, shows the same direction [5].

**6.7 Run time versus start count**
- Moving from about 2 to about 6 starts per day (runs 4 h → 1.5 h) costs about 1–2 % by the per-start arithmetic in section 1.
- It is worth about 0.5 K less slab swing (section 7). Comfort, PV timing and outdoor-temperature timing should decide, not fear of starts.

## What this means for controlling this house

Inputs, as given in the brief:
- Heat loss 0.14–0.20 kW/K. The measured 1.7 kW at +10 °C implies an effective 0.14 kW/K including gains.
- Slab 6.6 kWh/K. Minimum output Pmin about 3.75 kW. Room target 22 °C.
- The Versati starts only when setpoint − outlet ≥ about 4 K (register `delta_heat_temp_set` = 4, which most likely corresponds to the manual's Δt2 "ΔT-Heat"; please verify).

**Regime map (my calculation, lumped slab)**

| Outdoor T | Load (H = 0.14) | Run time needed at Pmin | Example plan | Slab swing |
|---|---|---|---|---|
| +12 °C | 1.4 kW | 9.0 h/day | 3 × 3.0 h | ≈1.1 K |
| | | | 6 × 1.5 h | ≈0.5 K |
| +10 °C | 1.7 kW | 10.8 h/day | 3 × 3.6 h | ≈1.1 K |
| | | | 4 × 2.7 h | ≈0.8 K |
| | | | 6 × 1.8 h | ≈0.6 K |
| +5 °C | 2.4 kW | 15.2 h/day | 4 × 3.8 h | ≈0.8 K |
| | | | 6 × 2.5 h | ≈0.5 K |
| 0 °C | 3.1 kW | 19.7 h/day | 3 × 6.6 h with 1.4 h off | ≈0.7 K |
| about −5 °C (H = 0.14) to +3 °C (H = 0.20) | ≥ Pmin | continuous | modulate, no on/off needed | — |

- Most of the Lithuanian heating season (many humid days between −5 and +5 °C, mild shoulders) sits in the forced-cycling regime or near its edge. So the controller is mostly a **pulse scheduler**, not a continuous modulator.

**Concrete rules (testable)**

1. **Stop treating starts as the main enemy; treat water temperature and compressor speed as the enemy.**
   - Target: a mild-weather pulse runs at or near minimum frequency (electric input around 0.8–1.2 kW, to be checked on this unit). The leaving water should be only as warm as needed to push about 3.75 kW into the slab.
   - Catch-up runs drawing about 3 kW at +2 °C are the thing to eliminate.
   - Confidence: medium-high, based on [4][19] plus physics.
2. **Start-then-glide setpoint handling.** Gree sets frequency from the setpoint gap [19], and the house needs about 4 K of gap to start. So:
   - (a) Start a pulse by writing setpoint = LWT + restart ΔT + about 0.5 K.
   - (b) Within 3–6 min of the compressor running, lower it to LWT + about 1–2 K, and re-write every few minutes so the gap stays small while the slab warms.
   - (c) End the pulse deliberately by dropping the setpoint below LWT by more than the stop margin, or by switching the mode off.
   - This needs writes every 2–5 min during transitions, not every 30 min.
   - Test: compare compressor frequency, input power and COP per run, against today's logic, at similar outdoor temperatures.
   - Confidence: medium. The mechanism is documented [19], but the exact stop margin and how fast frequency responds on this unit are unknown.
3. **Pulse length and count.** In mild weather:
   - Plan 2–6 pulses per day, each at least 90 min (ideally 2–4 h). Hard floor of 45–60 min except for protection or defrost.
   - Keep starts per running hour under 1.
   - The field penalty is near zero from 60 min upward and about 4–8 % for 15–45 min averages [4]. Starts cost about 1–2 % at 90 min and under 1 % at 3 h (section 1).
   - Confidence: medium-high.
4. **Size and time pulses from a daily energy budget, not a room-temperature trigger.**
   - Daily heat ≈ H_eff × (22 − forecast mean outdoor T) minus gains. Run hours ≈ that ÷ 3.75 kW. Split into N pulses so that the slab swing ((Pmin − L) × t_on / 6.6 K) stays within comfort, say ≤ 0.6–0.8 K.
   - Place pulses in the warmest hours and in PV surplus. That buys COP through a warmer source, which partly offsets the forced-lift penalty in section 5.
   - This is the concrete-core PWM idea [33] applied to an air-to-water unit. Confidence: medium.
5. **Restart hysteresis setting.**
   - If HA takes over start decisions (rule 2), set ΔT-Heat high (8–10 K, the factory default is 10 K [19][20]). The firmware then cannot restart by itself on small water-temperature drops, and HA alone decides when pulses start.
   - If HA cannot write quickly, about 5–6 K is a compromise.
   - Do **not** go to 2 K: that would hand the firmware many short restarts.
   - Test on site: confirm the register maps to Δt2 and check how a large value interacts with stop behaviour. Confidence: medium.
6. **"Heat run time" (1–10 min).** Set it to the maximum of 10 min, if accessible, so the unit lingers in the standby zone instead of stopping immediately on a brief overshoot. This removes very short runs [19]. Confidence: low-medium; check the semantics on the unit.
7. **Cold regime (load ≥ Pmin, roughly below −5 to +3 °C depending on H).**
   - Run continuously with a low weather-compensated setpoint and let the inverter modulate. Avoid on/off entirely.
   - Use the room/slab error as a slow trim (hours), not as an on/off trigger.
   - Confidence: high.
8. **Hot water.**
   - Heat DHW once a day in the warmest or PV hours, ideally straight after a space-heating pulse so the compressor does not need an extra start (check whether the Versati keeps the compressor running across the 3-way valve switch).
   - Use a wide DHW reheat band (ΔT-hot water 5–8 K) so small draws do not trigger cycles. Keep legionella on the electric heater, weekly.
   - Evidence: RHPP DHW cycling cases [3]; Gree DHW ΔT range 2–8 K [19]. Confidence: medium.
9. **Hydraulics.**
   - No buffer tank, no low-loss header [4][25]. Keep every UFH loop fully open with no room actuators [1][2].
   - Set the pump so the water temperature difference at minimum output is about 3–5 K. Confirm the pump does not run needlessly at high speed in standby [3].
   - Confidence: high (no buffer, open loops); medium (pump).
10. **What to log** so this can be verified on this unit:
    - Per run: start and stop time, duration, mean compressor frequency, kWh in, kWh out (heat meter or flow × ΔT), mean LWT and return temperature, outdoor temperature.
    - Per day: starts, mean run, share of runs under 30 min, starts per running hour.
    - Plot run COP against duration to find this unit's own knee. Expect 20–60 min. Also measure the first-15-minute heat deficit directly.
    - Count starts from a compressor-frequency register if Modbus exposes one, not from a power threshold [21].

**What to avoid**

- Large setpoint steps held for long periods. They force high frequency and high water temperature.
- 30-minute polling that ends pulses at arbitrary points.
- Letting the slab sag and then "catching up" hard.
- Room-thermostat on/off control of the heat pump.
- Lowering the restart hysteresis to 2 K.
- Buffers.
- DHW triggered by small tank drops.

**Overall confidence**

| Claim | Confidence |
|---|---|
| Runs under about 30 min cost several percent and runs over 60–90 min cost almost nothing per start | high (lab + field) |
| The forced-lift penalty is the bigger lever for this house | medium (physics + field temperature sensitivity; this floor's UA unknown) |
| Gree-specific tactics (start-then-glide, hysteresis value) | low-medium until tested on this unit |

## Contradictions and open questions

**Contradictions**

- **Where the knee is.**
  - Lab: about 6–8 min for fixed-speed ASHPs [1][2]; about 15 min by Uhlmann & Bertsch's model [11].
  - Field: no penalty only from about 45–60 min average runs [4].
  - Likely explanations:
    - Field averages hide distributions: many 5-min runs plus a few long ones can average 30 min.
    - Short-cycling systems also tend to have other faults.
    - The lab tests used older fixed-speed units.
    - The field penalty includes the lift penalty of bursty delivery.
  - I did not average these. The field knee is the safer design target.
- **RHPP found no relationship between cycle length and COP [3]; my heatpumpmonitor analysis finds a clear one [4].**
  - RHPP had 2-min data, large heat-meter errors and used median cycle length.
  - heatpumpmonitor has higher-quality metering, but its start counts come from a power threshold [21].
- **Inverter versus on/off.**
  - Dongellini's simulation: inverter 18 % better seasonally than single-stage, with 76 % fewer starts [5]. MERL cites Dongellini & Morini 2019 as up to 12 % seasonal loss from start-up transients [7].
  - Karlsson & Fahlén's lab-based seasonal performance factors: variable speed did *not* improve annual efficiency over intermittent operation, because of inverter and motor losses and pump control [14].
  - Madani et al.: on/off sized for 65 % or more of peak load is about equal to variable speed [13].
  - These are different systems (fan-coil ASHP vs GSHP with storage). Storage plus sensible sizing narrows the gap.
- **Buffers.** Lab and simulation say they help when runs would be very short [1][5]. Field data says buffered systems run hotter and score lower, with no longer runs [4]. Both can be true: buffers are often fitted to complex or zoned systems.
- **Starts-per-hour limits** range from about 3 (forum) through 6 (Bitzer for R290, EA Technology market survey, Dongellini) to 10–12 (Copeland, Danfoss) [2][5][15][17][18][31].
- **Dongellini thesis internal inconsistency:** heat-transient duration given as 150 s in the text and 250 s in Table 4.8 [5]. Both are carried in the per-start table.
- **EN 14825 Cdh = 0.9 for water units** [5] versus reports that it understates real losses (Madonna et al., cited in [5]) versus owner data showing no penalty at 2–3 starts per hour [24]. The standard ties the penalty to capacity ratio, while measurements tie it to run length and water temperature.
- **Uhlmann & Bertsch's own numbers differ by paper:** 2–5 % in 2011 versus 5–30 % in 2010 [11]. I could only see the abstracts.

**Open questions for this house (to measure, not guess)**

1. The Versati's real start transient: heat output and electric input over the first 15 min after a start, after a typical 1–4 h off period.
2. The exact semantics of `delta_heat_temp_set` (is it Δt2?), the stop margin above setpoint, and the "Heat run time" behaviour on this firmware.
3. Does the compressor keep running when switching between space heating and hot water? Does the unit run oil-return boosts during long minimum-frequency runs?
4. Floor UA (water to room) and the actual leaving-water temperature needed to deliver 3.75 kW at different slab temperatures. This sets the size of the lift penalty in section 5.
5. Minimum output and COP at −10 °C to +12 °C (minimum capacity drifts with outdoor temperature), which sets the true balance point.
6. Comfort tolerance: does a 0.6–1.0 K slab swing translate into an acceptable room swing (≤ ±0.3 K?) given the ventilation and heat recovery?
7. Defrost interaction on humid days around 0 °C: does running at minimum output reduce defrost frequency or energy? Defrosts also take heat from the water loop and slab. Not studied here; see the defrost note.
8. Standby pump power and whether the pump needs to run between pulses (it is the slab-temperature "sensor" via return water).

## Sources

1. The Effects of Cycling on Heat Pump Performance (Project 46640) - R. Green, EA Technology for DECC - 2012 - https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/65695/7389-effects-cycling-heat-pump-performance.pdf - lab (test house, fixed-speed 6 kW ASHP and GSHP) - minimum ~6 min run, ~8 min near-catalogue COP, GSHP worst case −16 %, small 4-pipe buffer (~8 L/kW) helps, lower-temperature short runs beat high-temperature runs.
2. The effect of Thermostatic Radiator Valves on heat pump performance (Report 6507) - R. Green, T. Knowles, EA Technology for EST - 2011 - https://assets.publishing.service.gov.uk/media/5a78de7840f0b62b22cbd718/3531-effect-radiator-valves-heat-pump-perf.pdf - lab - runs over 4–8 min show little COP effect; TRVs shrink circuits and cause cycling; most manufacturers cap at ~6 starts/h.
3. Investigating variations in performance of heat pumps installed via the RHPP scheme - J. Love, A. Summerfield, P. Biddulph et al. (RAPID-HPC/UCL for BEIS) - 2017 - https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/606829/DECC_RHPP_160428_On_performance_variations_v20.pdf - field data (~700 sites, 2-min) - ASHP median cycle 10 min; no clear cycle-length–COP link; long low-load runs fine; DHW cycling, continuous pumps, boost-at-start cases.
4. heatpumpmonitor.org public 365-day statistics and system metadata (own analysis) - OpenEnergyMonitor community - retrieved 2026-11-06 - https://heatpumpmonitor.org/system/stats/last365 and https://heatpumpmonitor.org/system/list/public.json - field data (cross-sectional, n = 513 after filters) - COP versus mean run length, starts/day, starts per running hour; flow-temperature sensitivity −0.091 COP/K; UFH, buffer, low-loss-header and duty breakdowns. Analysis scripts (not committed) were in the session scratchpad(analysis script, not committed) and house_pulses.py.
5. Dynamic modeling and seasonal performance evaluation of air-to-water heat pump systems (PhD thesis) - M. Dongellini, University of Bologna - 2017 - https://amsdottorato.unibo.it/id/eprint/7901/1/Dynamic%20modeling%20and%20seasonal%20performance%20evaluation%20of%20air-to-water%20heat%20pump%20systems.pdf - paper (simulation with manufacturer transient data) - start-up penalty factors (4 %/75 s electric, 42 %/150–250 s heat); EN 14825 Cdh default 0.9; SCOP and start counts for on/off, multi-stage and inverter units; dead-band doubling −60 % starts; buffer optimum 4–9 L/kW (>15 L/kW indirect).
6. On-off cycling losses of reversible air-to-water heat pump systems as a function of the unit power modulation capacity - M. Dongellini, G.L. Morini, Energy Conversion and Management 196:966–978 - 2019 - https://doi.org/10.1016/j.enconman.2019.06.022 (record: https://www.earth.org.uk/bibliography/dongellini2019cycling.html) - paper (simulation; full text not accessible) - cycling losses matter mainly for single-stage units; cited elsewhere as up to 12 % seasonal loss from start-up transients.
7. Theoretical analysis of cycling losses in air source heat pump systems (TR2023-127, ICR 2023) - H. Qiao, C.R. Laughman, MERL - 2023 - https://www.merl.com/publications/docs/TR2023-127.pdf - paper (first-principles simulation) - migration/redistribution dominate; capacity rise time 723 s (vs 168 s with regenerative accumulator); >95 % loss reduction with no migration.
8. Transient response and cycling losses of air-to-water heat pump systems - S.A. Tassou, P. Votsis, Heat Recovery Systems & CHP 12(2):123–129 - 1992 - https://www.osti.gov/etdeweb/biblio/7041177 - lab (abstract read) - up to 11 % COP loss from off-cycle migration; ~6 % with migration control.
9. The laboratory evaluation of the heating mode part-load operation of an air-to-air heat pump - ORNL, ASHRAE Trans. 91(2B) - 1985 - https://www.osti.gov/biblio/5505181 - lab (abstract read) - cycling losses tied to refrigerant migration; best result with refrigerant isolation in the indoor coil and 2-min fan overrun.
10. Improvements in the characterization of the efficiency degradation of water-to-water heat pumps under cyclic conditions - E. Fuentes, D.A. Waddicor, J. Salom, Applied Energy 179:778–789 - 2016 - https://ideas.repec.org/a/eee/appene/v179y2016icp778-789.html - lab (abstract read) - degradation strongly dependent on inertia (1.23–24.7 L/kW tested); non-negligible start-up losses; EN 14825 should be revised.
11. Measurement and simulation of startup and shut down of heat pumps; on/off cycling papers - M. Uhlmann, S.S. Bertsch, Purdue IRACC - 2010/2011 - https://docs.lib.purdue.edu/cgi/viewcontent.cgi?article=2007&context=iracc and https://www.semanticscholar.org/paper/Measurement-and-Simulation-of-Startup-and-Shut-Down-Uhlmann-Bertsch/f9707423a56be182f02b4240ae288333e48bac5a - paper (lab and field validated model; full text blocked, abstracts/snippets only) - 2–5 % penalty for very short cycles, insignificant at ≥15 min (2011); 5–30 % range (2010).
12. Methods for Testing and Rating the Performance of Heating and Air Conditioning Systems (NIST SP 958, history chapter) - NIST - 2001 - https://nvlpubs.nist.gov/nistpubs/sp958-lide/html/270-274.html - paper (history) - origin of the cyclic degradation coefficient; dry-coil cycling tests; separate heating-mode cycling test; migration and warm-up as loss causes.
13. Capacity control in ground source heat pump systems, Part II: comparative analysis between on/off controlled and variable capacity systems - H. Madani, J. Claesson, P. Lundqvist, Int. J. Refrigeration 34(8):1934–1942 - 2011 - https://iifiir.org/en/fridoc/capacity-control-in-ground-source-heat-pump-systems-ii-comparative-133959 - paper (simulation; abstract read) - on/off sized ≥65 % of peak ≈ variable-speed SPF; 55 % sizing makes on/off worse (10 % auxiliary).
14. Capacity-controlled ground source heat pumps in hydronic heating systems - F. Karlsson, P. Fahlén, Int. J. Refrigeration 30(2):221–229 - 2007 - https://iifiir.org/en/fridoc/capacity-controlled-ground-source-heat-pumps-in-hydronic-heating-systems-127539 - lab (abstract read) - variable speed better at part load but no annual SPF gain over intermittent operation (inverter and motor losses, pump control).
15. Application Guidelines, Copeland Scroll ZR24KRE–ZR190KRE - Copeland - rev. 2020s - https://media.copeland.com/0cfb235b-7155-4885-b009-b16b0107a750/AGL_AC_ST_ZRKRE_E_Rev02_FULL.pdf - manufacturer - max 10 starts/h; no minimum off time; minimum run set by oil return; short cycling progressively loses oil.
16. Application Guidelines, Copeland variable-speed heat pump scroll XHV with ED3 drive - Copeland - 2018+ - https://media.copeland.com/6937539b-0c9e-41d6-8a97-b16b0107724a/C060239_1218_E_AGL_HPScroll_XHV_VS_FULL.pdf - manufacturer - max 10 starts/h; ≥1 min off before start; oil-circulation routine below 1800 rpm; reach envelope fast at start.
17. KT-420 Cycling rate and minimum running times - BITZER - n.d. - https://bitzer.de/shared_media/html/kt-420/en-GB/242642187242698891.html - manufacturer - with frequency inverters max 6 starts/h (R290/R1270/R744/H-series), 12 otherwise; longer minimum runs at low speed for oil return.
18. Effects of cycling on domestic GSHPs: simulation/modelling (Report C207-R2) - R. Curtis, T. Pine, Mimer Energy for DECC - 2012 - https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/198854/mimer_report_on_modelling_cycling_of_heat_pumps.pdf - paper/report (simulation plus compiled manufacturer guidance; text partially garbled in extraction) - oil foaming and pump-out at start, need for minimum runs and anti-short-cycle timers (~3 min), start-count limits.
19. VERSATI III Air to Water Heat Pump (monobloc, R32, 4–16 kW) Service Manual - Gree - c. 2020–2024 - https://gree-bulgaria.com/manuals/service/Versati_III_Monoblock_04_06_08_10_12_14_16_service.pdf - manufacturer - frequency set by (LWT − setpoint); stop at min frequency when still far above setpoint; Δt2 heating 2–10 K default 10 K; DHW ΔT 2–8 K default 5 K; "Heat run time" 1–10 min (3/5 min); 3-min restart after stop; min water volume 20 L; frequent start/stop bad for oil return.
20. Air-to-Water Heat Pump Split Versati II+ Service Manual - Gree - c. 2016 - http://gree.at/uploads/servisni/servisni%20manual%20gree%20en%20versati%20ii+.pdf - manufacturer (text partly garbled in extraction) - confirms "temperature deviation for heating" ΔT-Heat default 10 °C and the run-time parameter in the earlier generation.
21. HeatpumpMonitor.org starts & starts per hour (thread) - T. Lea and others, OpenEnergyMonitor community - 2024 - https://community.openenergymonitor.org/t/heatpumpmonitor-org-starts-starts-per-hour/26246 - forum - start detection by ~100 W threshold; pump-power artefacts; Vaillant 9,292 starts / 7,194 h ≈ 1.29 starts per running hour example.
22. How to reduce cycling? (thread, pages 1 and 6) - A. Madsen, M. Gregory, S. Hanson et al., OpenEnergyMonitor community - 2024 - https://community.openenergymonitor.org/t/how-to-reduce-cycling/25251 and https://community.openenergymonitor.org/t/how-to-reduce-cycling/25251?page=6 - forum (owner data) - 150–180 starts/day → 1–2/day with COP ~2.5 → ~4; zoning/TRV removal; volumiser does not cure cycling by itself; pump speed effects.
23. Help Interpreting ASHP Data and Cycling Behavior (thread) - OpenEnergyMonitor community - 2025 - https://community.openenergymonitor.org/t/help-interpreting-ashp-data-and-cycling-behavior/27849 - forum - continuous running is the design ideal; Vaillant energy-integral start threshold −60 → −100; oversized Daikin replaced → SCOP ~5.
24. Heat pump truth or myth 2: cycling uses a lot of power and ruins your COP (thread) - Renewable Heating Hub - 2022–2024 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/heat-pump-truth-or-myth2-cycling-uses-a-lot-of-power-and-ruins-your-cop/ - forum (owner measurements) - 14 kW Ecodan cycling at ~2–3 starts/h showed COP 4.4–4.5 vs 3.9 continuous; "a few percent" cycling cost cited from John Cantor.
25. Avoid the heat pump villain: why low loss headers and buffers can sabotage your heat pump's efficiency (article + thread) - "Mars", JamesPa et al., Renewable Heating Hub - 2025 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/avoid-the-heat-pump-villain-why-low-loss-headers-and-buffers-can-sabotage-your-heat-pumps-efficiency/ - blog/forum - mixing raises flow and return temperatures; ~2–3 % per K across a header (unsourced); legitimate uses of separation.
26. Heat pump cycling - Energy Stats UK - c. 2024–2025 - https://energy-stats.uk/heat-pump-cycling/ - blog (owner data, 5 kW Vaillant) - <1 cycle per running hour "good"; 2,575 starts / 4,040 h = 0.64/h; causes and fixes; firmware energy-integral bug.
27. How much efficiency does a short cycling heat pump lose? (Q&A) - GreenBuildingAdvisor - 2024–2025 - https://www.greenbuildingadvisor.com/question/how-much-efficiency-does-a-short-cycling-heat-pump-lose - forum - anecdote: first minute nearly wasted, ~15 min to peak (air-to-air); 3-min anti-short-cycle protection.
28. Lebensdauer Wärmepumpe: Verdichterstarts & Wartung - 42watt - 2026 - https://42watt.de/magazin/lebensdauer-waermepumpe - blog (German, unsourced figures) - ~100,000-start rule of thumb; <2,000 starts/yr optimal; runs ≥20 min good, <10 min critical.
29. Regelung Vorlauftemperatur bei Wärmepumpe (thread) - energiesparhaus.at forum - 2015 - https://www.energiesparhaus.at/forum/37770 - forum (German) - duty-cycle control; hysteresis sets cycle count (±1.5 K example); degree-minute (energy-integral) control; 20–30 t screed stores far more than a 1,000 L buffer.
30. Evohome & Itho warmtepomp inefficiënt gedrag (thread) - klusidee.nl - c. 2023 - https://www.klusidee.nl/Forum/topic/evohome-itho-warmtepomp-inefficient-gedrag.169865/ - forum (Dutch) - UFH heat pump short-cycling 5–10 min under multizone room control; manufacturer reportedly wants ≥30-min run command; open zones to test.
31. Byggahus.se threads on NIBE degree minutes and compressor starts (e.g. "Finjusteringar av värmepumpen") - byggahus.se community - various - https://www.byggahus.se/forum/threads/finjusteringar-av-varmepumpen.227624/ - forum (Swedish; search-snippet level only, page fetch returned 403) - default compressor start −60 DM causes many starts; more negative (−120) gives fewer, longer runs with more overshoot; "max 3 starts/h, ≥20 min" folk rule.
32. Krzywa grzewcza – jak poprawnie ją ustawić? Typowe problemy i ich rozwiązania - GLOBEnergia - n.d. - https://globenergia.pl/krzywa-grzewcza-jak-poprawnie-ja-ustawic-typowe-problemy-i-ich-rozwiazania/ - blog (Polish) - two-end curve shaping, ±5 K parallel shift, iterative season-long tuning, outdoor-sensor placement errors.
33. Control of thermally activated building systems (TABS) in intermittent operation with pulse width modulation - M. Gwerder, J. Tödtli, B. Lehmann, V. Dorer, W. Güntensperger, F. Renggli, Applied Energy 86:1606–1616 - 2009 - https://doi.org/10.1016/j.apenergy.2009.01.008 - paper (simulation and lab) - concrete-core heating run in multi-hour PWM periods (5-h example) with energy per period matched to continuous operation and a 24-h moving-average outdoor temperature.
34. Wärmepumpen Monitor – Feldmessung von Wärmepumpenanlagen (final report) - D. Günther, M. Miara, R. Langner, S. Helmling, J. Wapler, Fraunhofer ISE - 2014 - https://wp-monitoring.ise.fraunhofer.de/wp-monitor-plus/download/endbericht_wp_monitor.pdf - field data (only partially extractable) - has a chapter on operating hours and cycle frequency; average annual compressor running time of the air-source systems ≈ 2,242 h; the detailed cycle statistics could not be extracted reliably, so no further numbers are used.
35. "Wrong sized approach 3: minimal overlap between heat pump's modulating zone and home's heating load line" (figure) - NEEP / PNNL Building America Solution Center - 2024 - https://basc.pnnl.gov/images/wrong-sized-approach-3there-minimal-overlap-between-heat-pumps-modulating-zone-and-homes - guidance - poor overlap between modulation range and load line causes excessive short cycling; select units whose modulation range covers the load line.
