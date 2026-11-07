# Defrost: when it happens, what it costs, how control influences it

> Research note 09 of the heat-pump efficiency sweep. Written 2026-11-06.
>
> **How this note was produced.** The shared web-search budget for this run was already used up when this topic started. All three searches attempted were refused, so **no new web searches were run**. Sources were found instead by:
> - fetching URLs known in advance;
> - following reference and "related items" lists on IDEAS/RePEc (which gave abstracts of the main Elsevier frost/defrost papers; full text was paywalled, HTTP 403);
> - following Wikipedia's reference list;
> - reading manufacturer PDFs, with text extracted locally;
> - running my own analysis of the open heatpumpmonitor.org daily dataset (113 systems, 65,187 system-days).
>
> MDPI and ScienceDirect full texts returned 403, so for most academic papers only abstracts were read; each such case is marked "(abstract)". Per the brief, this note does not read or build on the repository's control code.

## Summary

1. **Field-measured defrost "reverse heat" rises steeply below about +5 °C daily mean.** I analysed 113 monitored heat pumps (65,187 days, 2023-2026) [39]. Heat pulled back out of the water during defrost, as a share of delivered heat (heat-weighted):
   - about **0.7-1 %** at +6…+12 °C;
   - **2.7 %** at +4…+5 °C;
   - **4.4 %** at +2…+3 °C;
   - **5.6 %** at 0…+1 °C;
   - **5.9-6.7 %** below 0 °C.

   Per running hour, the median was 20 Wh at +6…+8 °C, 73 Wh at +4…+6 °C, 148 Wh at +2…+4 °C and 213-291 Wh below +2 °C. This is a **lower bound** on the true defrost penalty, because it leaves out compressor electricity during defrost, lost heating time and the recovery ramp.
2. **The worst frosting zone in the literature is about −7…+5 °C with RH > 65 %** [1]. In Lithuania, an experiment on an air-to-water heat pump saw frost start **below +3.5 °C at 88 % RH**, with defrosts lasting **about 5 min on average** [4]. UK owner data put frost at about +3…+4 °C [28][30]. A Lithuanian winter sits largely inside this zone.
3. **Load (compressor speed) changes the frosting map.** For a variable-speed vapour-injection unit, taking heating load into account [3]:
   - the unit did **not frost at 0 °C / 80 % RH** at low load;
   - the critical RH fell from 80.6 % at +1 °C to 62.75 % at −26.5 °C;
   - the fastest frosting was near **−10 °C**, not 0 °C.

   Mechanism: at low compressor speed the evaporator runs warmer (closer to air temperature), so it frosts more slowly or not at all. Evidence: lab/field rig (abstract). Confidence: medium.
4. **Cutting airflow has the opposite effect, and it dominates.** On a sister Gree Versati III (16 kW), quiet mode cut fan speed and **defrost ran every about 52-56 min at +2…+5 °C**, much less often without quiet mode [36]. A Vaillant owner saw **defrost every about 40 min** in noise-reduction mode, against every 90-120 min normally at −0.9…+1.9 °C [28]. Higher air velocity suppresses frost [1][9].
5. **Reverse-cycle defrost takes its heat mostly from the heating side.** In one study the indoor side supplied **71.8 %** of the defrost energy, only **about 59 %** of the energy actually melted frost, and defrosting efficiency was at most about 60 % [1]. Measured defrosting efficiencies were 34.5-53 % [1][10]. On this house the heat comes from the UFH water and slab. The amount per event (about 0.15-0.3 kWh, estimated from [39]) is trivial against 6.6 kWh/K of slab storage. It does matter for a small isolated water volume: Gree's minimum is 20 L [37].
6. **Gree Versati defrost logic is mainly time-and-temperature with "smart" adjustments.**
   - First generation [38]: defrost after at least **50 min accumulated compressor run time** (settable 30-60) **and** coil below **−4 °C** (settable −10…0). It lasts up to **10 min** (settable 1-15) or until the coil reaches **15 °C** (settable 5-30).
   - Versati III [37]: defrost uses a coil "defrost temperature" sensor and the suction (low) pressure. In heating, fan speed follows the low-side pressure. The fan stops and the 4-way valve reverses during defrost. Gree markets "defrost less when frost is light".
7. **Badly timed defrost is expensive, and the losses are measured.** Field tests [5][6]:
   - Defrost started more than 1 h late cost **17.4 % COP and 29 % capacity**.
   - Three defrosts with almost no frost cost **4.2 %**.
   - A "mal-defrost" in mild weather cut **COP by up to 40.4 %** (COP 2.3 at +7.9 °C, against 5.0 after a manual defrost).

   Timer-based initiation has about **±50 % timing error** [7].
8. **Better defrost initiation is worth about 5-10 % in the lab.** Reinforcement-learning initiation beat time-based defrost by **up to 7.1 % SCOP** and demand-based by **up to 9.1 %** [13]. Image-based on-demand control cut defrost frequency by **31.7-75 %** and defrost energy by **43-88 %** against fixed-interval control [16][17]. Defrost-cycle optimisation of fan and compressor speeds gave **1.5-7.9 %** per cycle [15].

   These live inside the unit's firmware: an external controller **cannot** implement them on a Versati. It can only change the conditions the firmware sees.
9. **Defrost cuts usable output.** Sustained maximum output measured across several defrosts near −5…+1 °C was **7-25 % below datasheet** [32]. Datasheet ratings for the Versati are at **7 °C DB / 6 °C WB** [37], which is outside the frost zone. Nominal COP figures therefore say nothing about defrost.
10. **Field COP falls fastest exactly where defrost starts.** In the same 113-system dataset [39], median daily COP was:
    - 4.47 at +6…+8 °C;
    - 3.93 at +4…+5 °C;
    - 3.52 at +2…+3 °C;
    - 3.18 at 0…+1 °C;
    - 2.98 at −2…0 °C.

    The defrost share rises from about 1 % to about 6 % over the same span. Defrost is one of several causes of the slope; the Carnot lift is the larger one.
11. **Lower demand in cold, humid weather appears to reduce defrosts.** In a field MPC house, there were **1.3 defrosts/day with MPC vs 2.7/day without**, on days below 0 °C at 70-80 % RH. The authors stress that the sample was too small [26].
12. **Defrost breaks naive controllers.** Heat flow reverses and water temperatures dip. Field MPC studies handled this by detecting defrost and putting the controller on standby [26][27]. The Versati exposes a defrost status bit (coil 86 in the Modbus map, see note 08) that can be used for this.
13. **For this house (estimate, medium-low confidence):** defrost probably costs **about 3-8 % of seasonal heating electricity** in Lithuania. That is the 3-4 % of heat reversed in the field data, plus lost runtime and the recovery ramp. It is second-order compared with flow temperature (about 2-3 % COP per K) and compressor speed (COP about 4.6 at 40 rps vs 3.3 at 110 rps [33]). But it is pushed by the **same levers**: low-power, long, warm-hour runs reduce both.

## Detailed findings

### 1. Physics: why frost forms and what it does

- **Conditions.** Frost forms when the outdoor coil surface is below both 0 °C and the air's dew point. The ORNL review gives the operating band where frost forms and accumulates on ASHP outdoor coils as **about −7 °C to +5 °C with RH above about 65 %** [1].
  - Below about −7…−10 °C, air holds so little water that frost grows slowly; how slowly depends on the unit and the load (see §3).
  - Above about +5 °C, the coil normally stays above 0 °C.
- **Effects.** Frost adds thermal resistance and, more importantly, blocks airflow between the fins. Airflow falls, evaporating temperature drops further, capacity and COP drop, and the process feeds itself [1][22].
  - In one fin study, about 90 % of the total thermal resistance was the air-side convective term [1].
  - Increasing face velocity from 0.8 to 1.6 m/s raised fin capacity by up to 53 % [1].
- **Time split.** Frosting takes up **more than 80 %** of a frosting-defrosting cycle [1], so retarding frost matters more than speeding up defrost.
- **Uneven frosting.** Multi-circuit coils frost unevenly. The inlet segment can stay frost-free while the outlet segment frosts [9]. Melt water running down vertically stacked circuits lowers defrost efficiency, and horizontal coils defrost more efficiently (43.5 % → 53.3 %) [1].
- **Experimental frost-accumulation data are scarce.** Frosting and defrost durations and termination criteria vary widely with system design and test set-up [20]. Numbers from one unit do not transfer cleanly to another.

### 2. Where Lithuania sits on the frosting map

- **Kropas, Streckienė and Bielskus (VGTU, Vilnius), 2021** [4], tested an air-to-water heat pump in the transitional and cold season (abstract):
  - frost formation began when outdoor air was **below 3.5 °C and RH reached 88 %**;
  - the average defrost cycle was **5 min**.

  This is the only Lithuanian measurement found. Unit size and control details were not available (paywall).
- **UK owner data (similar maritime humidity):**
  - Frost has been seen at about +3 °C. Defrosts every 45-120 min are typical in cold, humid weather. One unit defrosted every 90-120 min at −0.9…+1.9 °C [28].
  - The same author notes UK winters often sit at 80-90 % RH [28].
  - Another blog post notes defrost "below around 4C", with a roughly 7-minute defrost every about 90 min [30].
- **Implication.** Lithuanian winter days at −5…+5 °C with high RH are the heart of the frost zone. Days at −10…−20 °C are drier and frost more slowly per hour. But the unit runs at high load then, which itself raises frosting (see §3), so defrost does not vanish.

### 3. Compressor speed, fan speed and the frosting map

- **Load-aware frosting map** (Wei et al. 2020, Renewable Energy) [3], abstract. Two heating seasons on a variable-frequency vapour-injection ASHP serving a lab in a severe-cold region.
  - At **0 °C / 80 % RH**, traditionally a "severe frosting" point, **the unit did not frost**.
  - With heating load included, the critical RH fell from **80.60 % (+1.0 °C)** to **62.75 % (−26.5 °C)**. That is the opposite trend to earlier, load-blind maps.
  - The fastest frosting occurred near **−10 °C**.
  - Interpretation (mine): at mild temperatures the house load is small, so the compressor runs slowly. The evaporator then sits only a few kelvin below air temperature and may stay above the frost point. At −10 °C the compressor runs hard and the coil is much colder, so frost grows fast even in drier air.
  - Direct consequence: **frosting is partly a control outcome, not only a weather outcome**.
- **Defrost cycle optimisation** (Ikram et al. 2025, Energy) [15], abstract.
  - Defrosting depends mainly on outdoor conditions and **component speeds**.
  - The coil approach temperature difference was a reliable defrost-initiation indicator.
  - Optimising indoor fan, outdoor fan and compressor speeds through the cycle gave **+1.5 %, +7.9 %, +7.9 %, +7.4 %** over four consecutive frost/defrost cycles, against superheat-based initiation.
- **Fan speed.**
  - More air velocity suppresses frosting and uneven frosting [9]. Fewer fins per inch and higher airflow delay frost at a fan-power and noise cost [1].
  - Field reports on quiet mode or noise-reduction mode show **more frequent defrosts**:
    - Gree Versati III 16 kW: every about 52-56 min at +2…+5 °C [36];
    - Vaillant: every about 40 min, and the unit could not reach room temperature [28].
  - Quiet mode lowers **both** compressor and fan speed. The net effect is more frost, so in these units the fan reduction dominates.
- **How Gree couples the fan to pressure.** The Versati III service manual says that in heating, **outdoor fan speed follows the low-pressure (suction) side**, and the suction pressure is also an input to defrost control [37].
  - Inference: when the compressor slows, suction pressure rises and the fan may slow too. That would give back part of the "warmer coil" benefit of low compressor speed.
  - How much is unknown. This is an important open question for this unit.
- **Field hint from MPC.** In a cold-climate house (air-to-air, 14 kW), defrosts were **1.3/day with MPC vs 2.7/day without**, on below-zero days at 70-80 % RH [26].
  - The authors hypothesise that MPC's lower demand in cold, humid hours reduced frost formation.
  - The sample was explicitly too small for robust conclusions.
- **Forum hypothesis, disputed.** One OpenEnergyMonitor user proposed a "defrost death spiral": aggressive ramp-ups during cheap-tariff hours cause more defrosts, which force more ramp-ups [34]. Another user's COP-vs-temperature data showed a steady linear decline with no spiral [34]. No defrost counts were presented. Treat it as an unproven hypothesis.
- **Own dataset check, exploratory** [39]. Within each of 111 systems, on days at 0…+4 °C, I compared days with above-median vs below-median **running heat output**, after removing the within-system temperature trend.
  - Higher-output days had defrost shares **0.16 percentage points higher on average**, and **62 %** of systems showed the same sign.
  - Days with a higher **duty cycle** had slightly lower shares; only 39 % of systems showed higher.
  - Flow temperature showed no clear effect (53 %).
  - These effects are **weak**. Humidity is unobserved and certainly dominates, and the daily aggregates are coarse. Directionally consistent with "harder running → more defrost", but **not proof**.

### 4. What defrost costs: measured numbers

**4a. Field data: heatpumpmonitor.org (own analysis) [39]**

Data:
- Daily records for 113 systems (UK-dominated, open data, 2023-04 to 2026-11), downloaded by the shared sweep.
- Metric: `combined_cooling_kwh`, the heat-meter energy recorded as **negative heat**. On systems not in cooling mode, this is essentially defrost.
- Filters: days with ≥5 kWh heat, ≥90 % data coverage and no cooling-mode heat.

| Daily mean outdoor | System-days | Systems | Median reverse-heat share | Heat-weighted share | Median daily COP |
|---|---|---|---|---|---|
| −10 … −4 °C | 66 | 13 | 7.0 % | 6.7 % | 2.59 |
| −4 … −2 °C | 220 | 56 | 6.1 % | 6.3 % | 2.80 |
| −2 … 0 °C | 805 | 108 | 5.5 % | 5.9 % | 2.98 |
| 0 … +1 °C | 740 | 111 | 5.3 % | 5.6 % | 3.18 |
| +1 … +2 °C | 994 | 107 | 5.0 % | 5.2 % | 3.29 |
| +2 … +3 °C | 1569 | 113 | 4.0 % | 4.4 % | 3.52 |
| +3 … +4 °C | 2332 | 113 | 3.3 % | 3.7 % | 3.70 |
| +4 … +5 °C | 2739 | 112 | 2.3 % | 2.7 % | 3.93 |
| +5 … +6 °C | 3086 | 113 | 1.4 % | 1.9 % | 4.16 |
| +6 … +8 °C | 7934 | 113 | 0.5 % | 1.1 % | 4.47 |
| +8 … +10 °C | 10463 | 113 | 0.4 % | 0.7 % | 4.66 |

- **Absolute reverse heat**, median per system-day:
  - 6.5 kWh/day below −2 °C;
  - 4.6 kWh/day at 0…+2 °C;
  - 2.9 kWh/day at +2…+4 °C;
  - 1.3 kWh/day at +4…+6 °C;
  - 0.3 kWh/day at +6…+8 °C.

  Per running hour: 291 / 242 / 213 / 148 / 73 / 20 Wh for −10…−2 / −2…0 / 0…+2 / +2…+4 / +4…+6 / +6…+8 °C.
- **Whole dataset:** reverse heat is **2.0 %** of delivered heat. On days below +6 °C it is **3.7 %**; those days carry 37 % of all heat in this mostly-UK dataset. A Lithuanian heating season would put a much larger fraction of heat on sub-+6 °C days.
- **Noise floor:** about 0.4-1 % on mild days. This is probably meter or hydraulic artefacts, DHW transients and rare mild-weather defrosts. The 12-16 °C bin even shows 1.2 %.
- **What this metric misses:**
  - compressor and fan electricity *during* defrost (the compressor runs in reverse);
  - the heat not produced while defrosting, typically 5-10 min per event [4][30][38];
  - the post-defrost recovery ramp, often at high power.

  A defrost at least doubles its direct cost once re-heating at COP and the lost run time are counted. So the true SPF penalty is plausibly **about 1.5-2× the reverse-heat share**. That multiplier is my inference, not measured.
- **Caveats:**
  - Some integrations exclude defrost energy. For example, heatpumpmonitor flags some Mitsubishi setups where "Defrost energy not included".
  - Daily mean temperature hides colder, more humid nights.
  - UK climate, not Lithuanian.

**4b. Maximum output with defrost [32]**

Measured sustained output across several defrosts, against datasheet:

| Unit | Conditions | Shortfall vs datasheet |
|---|---|---|
| Vaillant Arotherm+ 5 kW | just below 0 °C, 45 °C flow (5 defrosts averaged) | 5.2 kW vs 6.6 kW (−21 %) |
| Vaillant Arotherm+ fleet, 35 tests | — | −14 % to −25 % by size |
| Mitsubishi Ecodan 5 kW | −2.1…+0.8 °C | −7 % to −15 % |
| Daikin Altherma 11 kW | −5…+1.3 °C | −14 % to −17 % |

OpenEnergyMonitor recommends a 20-30 % sizing margin for this reason [32]. For this house, which is heavily oversized (minimum output 3.7 kW against about 1.7 kW load at +10 °C), capacity loss to defrost is irrelevant. Only the efficiency cost matters.

**4c. Lab and field: mis-timed defrost**

| Source | What happened | Measured loss |
|---|---|---|
| Wang et al. 2011 field test [5] | Defrost started more than 1 h after critical frost | **COP −17.4 %, capacity −29 %** |
| Same study [5] | 3 defrosts in 6 h with almost no frost | **−4.2 %** efficiency |
| Wang et al. 2013, 8-day field test, Beijing [6] | Mild-weather "mal-defrost": more than 60 % of the coil frosted after 5 days | COP 2.3 at +7.9 °C (vs 5.0 after defrost); **COP −40.4 %, capacity −43.4 %** |

- The mild-weather mal-defrost is relevant here. Coil-temperature-triggered logic **can fail to trigger in mild humid weather**, when the coil frosts but stays warmer than the −4 °C threshold. That is the Versati's first-generation logic [38].
- Timer initiation erred by **±50 %** against **±10 %** for a temperature-only "effective mass-flow fraction" method [7].
- Optimal initiation time shortens as RH rises at fixed temperature. At fixed RH it is non-monotonic in temperature [8].

**4d. Where defrost energy goes (reverse cycle)**

- Indoor-side heat supplied **71.8 %** of the defrost energy in one study, and **59.4 %** of the supplied energy melted frost. Maximum defrosting efficiency was about 60 % [1].
- Other measured defrosting efficiencies: **34.5 %** for a four-circuit coil, and **42-48 %** depending on coil size [1][10].
- The rest heats coil metal, re-evaporates retained water and is lost to ambient.
- In a slab house, **roughly half of each defrost's energy is wasted**, and most of it is taken from the water loop and re-supplied afterwards by the compressor.

**4e. Alternative defrost methods (for context; not available on the Versati)**

- Hot-gas bypass vs reverse cycle on a 55 kW air-to-water unit: hot-gas bypass took **much longer** but avoided the heating-side reversal [11].
- "Continuous heating" hot-gas bypass: **+17 % heating capacity** and **+8 % cumulative efficiency** vs reverse-cycle over 4 h with 2 defrosts [12].
- Choi et al.: hot-gas bypass about 13 % better than reverse cycle [1].
- Frost-free (desiccant, solution-spray) ASHP concepts claim **30-64 % higher total COP** under frosting conditions [22]. Not a retrofit option.

### 5. Defrost control strategies (inside the unit)

- **Time-temperature** (the most common; what the first-generation Versati documents) [1][38]:
  - start after a minimum accumulated run time when the coil temperature is below a threshold;
  - stop on coil temperature or a time cap.

  It is simple and robust, but can start defrost with little frost or miss frost [1][5][7].
- **Demand defrost** uses air-side ΔP, coil-to-air approach temperature, refrigerant flow or capacity decay, optical or image sensors, or ML [1][14][15][16][17][18][41].
  - Reported improvements: defrost frequency −31.7 % / time −65.8 % / energy −42.9 % in a commercial field test [17].
  - Frequency −75 %, defrost energy −88 %, COP +11.8 % vs "traditional methods" in a lab [16].
  - Deep-learning prediction of capacity, power and COP loss under frost from existing sensors, with RMS errors of 2.4-3.4 % [18].
- **Self-learning initiation** [13]:
  - near-optimal timing, with at most 1.9 % loss;
  - **+7.1 % SCOP vs time-based, +9.1 % vs demand-based** over three typical days;
  - **+16.6 %** when the coil was partly blocked (leaves).
  - The same group studied how much conventional controllers fall short of optimal initiation [14] (abstract only, no numbers).
- **Gree "smart defrost"** (Versati II/III) claims adaptive defrost: less when frosting is light, more when heavy [37]. The algorithm is undocumented.
  - The first-generation parameters (interval 30-60 min, entry coil temperature −10…0 °C, duration 1-15 min, exit 5-30 °C) were **user/installer parameters** [38].
  - Whether Versati III exposes them is unknown. The Modbus map exposes a **manual defrost** command, a **defrost status** bit and a **coil (defrost) temperature** reading (see note 08).
- **Simulation tooling.** First-principles frost/defrost dynamic models exist and are validated on residential units [25]. OpenEnergyMonitor's dynamic simulator does **not yet** model defrost; its author lists it as a needed feature [35].

### 6. The water side: heat drawn from the loop, minimum volume, controller interactions

- **Mechanism.** In reverse cycle the plate heat exchanger becomes the evaporator. The circulating water is chilled and the outdoor fan stops [37][38]. Owner monitoring shows flow and return dropping and reversing during defrost [28][30]. Wikipedia, citing an installer, calls the water temperature drop "small and probably undetectable" [40]. That fits a large system, but not the multi-kWh-per-day reverse heat measured in cold weather [39].
- **Minimum volume.**
  - Versati III monobloc: minimum total water volume **20 L**; default design volumes 44 L (4-8 kW) and 66 L (10-16 kW) [37].
  - An electric heater on the plate exchanger protects it from freezing when water gets too cold [37].
  - First generation: water-side anti-freeze starts the pump at <3 °C and the compressor 30 s later [38].
  - One owner blog suggests a volumiser on the return if defrosts are excessive or disruptive [28].
- **Slab context (this house).** At 0…+2 °C one defrost reverses roughly 0.15-0.3 kWh. That is my estimate: 213 Wh per running hour from [39], with defrosts every 45-90 min [28][30].
  - Against 6.6 kWh/K of slab, this is **< 0.05 K** of slab temperature: negligible for comfort.
  - The **UFH water** (perhaps 100-200 L in pipes) takes the hit first, falling several kelvin for a few minutes. This only matters if loops can close. Closing UFH loops has tripped flow faults on Versatis (see note 08).
- **Controller interactions.**
  - In field MPC studies, defrost reversed the measured heat flow. Controllers had to detect defrost and go to standby [26][27].
  - Any external logic that reads outlet temperature, ΔT or heat power must **mask defrost periods and the recovery after them**. Otherwise it will "see" a cold loop and raise the setpoint.

### 7. Timing: warm afternoons vs humid nights

- **Direct evidence that time-of-day shifting reduces defrost is thin.**
  - The Bayreuth MPC rig moved operation to daytime from about 10:00, for warmer air and PV. It reported +5.4 % COP over 125 days but did not separate defrost (note 06 [5]; I re-read the PDF and found no defrost content).
  - Pergantis et al. observed fewer defrosts with MPC but did not attribute it to timing [26].
- **Indirect evidence is strong.** Reverse-heat share falls by about **1-1.5 percentage points per +1 K** between 0 and +6 °C in the field table above [39]. The steepest part is +2…+6 °C. Higher RH shortens the optimal interval between defrosts [8] and raises frost formation [1].
- **Diurnal pattern.** Nights are colder with higher RH; afternoons are warmer with lower RH, especially on clear days. In the shoulder seasons (October-November, March-April) a +3…+6 K day-night swing can move a day **across the frost threshold**: frosting at night, frost-free in the afternoon. In cloudy midwinter (December-January in Lithuania) the swing is often only 1-3 K, so the benefit is smaller. This is climatological reasoning; I did not fetch Lithuanian diurnal climatology in this sweep.
- **DHW.** Hot-water heating runs at high condensing temperature, and often at high compressor speed. Owner data show DHW COP about **2.0 at 0 °C** vs 3.8 at 18 °C [30]. DHW also frosts the coil, so putting DHW in the warmest hours helps COP and defrost both.

### 8. Cycling and defrost

- Mild-weather cycling is driven by minimum output exceeding load [31]. Cycling and defrost interact in three ways:
  1. **Accumulated-run-time timers** (first-generation Versati: 50 min accumulated [38]) can fire **early in a new run** once enough runtime has accumulated across earlier cycles. That gives a defrost soon after a start, with frost possibly light. Whether the counter resets at stop is not documented. Open question.
  2. **Off periods above about +1 °C can passively melt light frost** (compressor-shutdown defrost uses ambient air [1]). This works best with the outdoor fan on. The Versati stops its fan with the compressor, so passive melting is slower. Not quantified for this unit.
  3. **Post-defrost recovery** runs at elevated speed to recover water temperature. In an oversized, low-load house this can push the outlet above setpoint and trigger a stop: defrost, then recovery, then overshoot stop. Hypothesis to check with logs.
- The field dataset gives no clean signal that more starts mean more defrost at the same temperature (0…+5 °C days) [39]:
  - 0-5 starts/day: median 3.4 %;
  - 5-10: 2.7 %;
  - 10-20: 3.1 %;
  - 20+: 5.2 %.

  Only very heavy cycling coincides with more defrost, and that is confounded by system quality.

## What this means for controlling this house

The house: slab UFH, 9 kW Versati, minimum output (about 3.7 kW) above the mild-weather load, flow setpoint written over Modbus, and a restart only when setpoint minus outlet is at least about 4 K.

Confidence tags: **H** = high (multiple measured sources agree), **M** = medium (mechanism plus some field data), **L** = low (inference, needs testing on this unit).

1. **Size of the prize (M).** Expect defrost to cost about **3-8 % of heating electricity** over a Lithuanian season, concentrated on −5…+5 °C humid days. It is worth managing but is not the main loss. Flow temperature and compressor speed matter more:
   - about 2-3 % COP per K of flow temperature (note 06);
   - COP 4.6 at 40 rps vs 3.3 at 110 rps on one manufacturer's table [33].

   The good news: the same actions help all three.
2. **No high-power catch-up runs in the frost band (M).** Between about −5 and +5 °C with RH above about 80 %, avoid requests that drive the compressor to high frequency, such as 36-39 °C setpoints after a temperature deficit.
   - High speed means a colder evaporator: faster frost, and the coil drops below the −4 °C defrost-entry threshold sooner [3][15][38].
   - Prefer **long runs near minimum output at the lowest flow temperature that delivers the day's heat**.
   - Practical tool: the Versati **power limit** (C/P limit, Word 43 per note 08). Test a cap of about **1.5-2.0 kW electric** on frost-band days against no cap, at matched temperature and RH.
   - Caveat: the Gree fan follows suction pressure [37], so lower compressor speed may slow the fan and erode the benefit (L).
3. **Never use quiet mode at −5…+5 °C on humid days (H for direction).** Two independent field reports show defrost every 40-56 min with quiet/noise modes [28][36]. If night noise is a concern, use the power cap, not quiet mode.
4. **Shift bulk heat to the warmest hours (M for direction, L for size).** The slab (6.6 kWh/K, about 0.14-0.20 kW/K loss) can coast through 6-12 h with a 0.5-1 K swing.
   - When the forecast shows night lows in the frost band and an afternoon at least 2-3 K warmer, deliver most of the day's heat between about **11:00 and 17:00**. That is also when PV is available.
   - Expected effect from the field table: about 1-1.5 percentage points less reverse heat per +1 K in the 0…+6 °C band [39]. On top of that, the Carnot COP gain of about 2-3 % per K of lift reduction.
   - In clear-sky shoulder seasons this can avoid defrost entirely on some days. In cloudy midwinter, expect little.
5. **Run DHW in the warmest hours, ideally on PV (M).** DHW is the highest-lift, highest-speed duty [30]. Avoid it during cold, humid nights. Legionella cycles that use the tank's electric heater are unaffected.
6. **Mask defrost in all external logic (H).** Read the defrost status (coil 86) and the defrost/coil temperature (register 120) via Modbus.
   - During defrost and for about **10-15 min after**, do not log the outlet or ΔT as a heating sample.
   - Do not raise the setpoint in response to post-defrost low outlet temperature.
   - Freeze any integrators or learning updates [26][27].
   - Count defrosts and estimate reverse heat if the unit's heat calculation allows. Pure heat-meter COP must include negative heat to be honest [39].
7. **Keep water volume available during defrost (M).** Keep enough UFH loops permanently open so the 20 L minimum [37] is far exceeded and the plate exchanger never sees a small, isolated volume. Do not add zone valves that can all close at once.
8. **Don't tune the defrost parameters blindly (M).** If the installer menu exposes interval, entry temperature or duration (as on the first generation [38]), **leave the defaults** until you have logs.
   - Lengthening the interval or lowering the entry temperature can cut unnecessary defrosts (worth about 4 % [5]).
   - The opposite error, defrosting too late, costs 17-40 % [5][6].
   - The asymmetry favours the default.
9. **Watch for mild-weather mal-defrost (M).** At +3…+8 °C in fog or drizzle, a coil-temperature-triggered unit can frost without reaching the entry threshold [6]. Two signs:
   - COP falls for hours, and outlet temperature struggles at modest power;
   - visible frost on the coil.

   A **manual defrost** command exists on the Versati (see note 08). Use it as an operator tool, not an automatic routine, until behaviour is understood.
10. **Restart-hysteresis interaction (L).** Restart requires setpoint − outlet ≥ about 4 K. Defrost does not stop the compressor in the usual sense, so it should not need a restart. But if a run ends right after a defrost and its recovery (overshoot), the next restart is delayed until the loop cools by 4 K.
    - Log whether stops cluster within about 15 min after a defrost.
    - If they do, a slightly lower setpoint during frost-band runs (less overshoot) may lengthen runs.
11. **Build this unit's own frost map (H value, low cost).** Log every defrost with:
    - outdoor temperature;
    - outdoor RH (a local sensor or forecast);
    - compressor frequency and power for the preceding 30-60 min;
    - setpoint and outlet;
    - time since the last defrost.

    After one winter month, fit the defrost interval against temperature, RH and power. Use the map in the scheduler to price defrost into the cost of each hour.
12. **Experiments to run (concrete).**
    - **A/B, paired days at matched outdoor temperature and RH in −3…+4 °C:**
      - (a) normal control vs (b) power cap of 1.5-2.0 kW;
      - compare defrosts/day, kWh electric per kWh heat (incl. reverse heat), starts/day.
    - **Timing test, on days with a ≥3 K afternoon rise:** deliver the same daily kWh night-weighted vs afternoon-weighted. Compare defrosts and COP.
    - **Quiet-mode sanity check, one night at +1…+4 °C, high RH:** confirm the defrost interval shortens on this 9 kW unit, as on the 16 kW sister [36].

## Contradictions and open questions

**Contradictions**

- **Where frosting is worst.**
  - Classic maps and reviews put the severe zone near 0 °C at high RH [1][22].
  - The load-aware map puts the fastest frosting near **−10 °C** and found **no frost at 0 °C / 80 % RH** at low load [3].
  - Reconciliation: frosting depends on coil temperature, which depends on compressor load. Mild days frost little *if* the unit runs slowly, and cold days frost a lot because it runs hard. Not averaged; both are kept.
- **Frost onset temperature.**
  - ORNL: up to +5 °C [1]; Kropas (Lithuania): below +3.5 °C at 88 % RH [4]; UK owners: about +3…+4 °C [28][30].
  - My field table shows reverse heat rising from about **+6 °C daily mean** [39].
  - Probably consistent: a daily mean of +5…+6 °C contains colder night hours.
- **Lower compressor speed should reduce frost, but quiet mode increases it** [28][36]. Quiet mode cuts fan speed too, and airflow matters a lot [1][9]. Gree also links fan speed to suction pressure [37]. Whether a *power cap* (compressor only) reduces defrost on the Versati is **untested**.
- **"Defrost water dip is negligible"** [40] vs **4-6 kWh/day of reverse heat** at 0 °C [39]. Both can be true: per event it is small (minutes, a few tenths of a kWh); per day in cold, humid weather it adds up to about 5 % of heat.
- **Demand vs timed defrost savings.** Lab and commercial studies show large reductions: 31-88 % of defrost energy [16][17], 7-9 % SCOP [13]. Real residential units already use hybrid time-temperature logic with "smart" claims [37], so the remaining headroom on a modern unit is unknown. Not something an external controller can capture anyway.
- **MPC reduces defrost** (1.3 vs 2.7/day [26]) vs **the "defrost death spiral" from load shifting** [34]. Neither is statistically established. The direction depends on whether the optimiser concentrates heat into cold, humid hours (bad) or warm hours at low power (good).

**Open questions**

1. What exactly is the Versati III defrost initiation logic? Time plus coil temperature plus suction pressure, with what thresholds? Does the accumulated-runtime counter reset on stop?
2. Does a power cap (Word 43) lower compressor speed without proportionally lowering fan speed? Does it reduce defrost frequency at +1…+4 °C, high RH?
3. How much heat does one defrost reverse on this unit, and how long does it last? Kropas measured a 5 min average on another unit [4]; Gree allows up to 10 min [38].
4. Do compressor stops cluster after defrost recovery (overshoot)?
5. What is the realistic day-night temperature and RH swing in this location in November-March? It determines how much timing can avoid frost.
6. Does the electric backup or plate-exchanger heater switch on during defrost on this installation? If so, defrost cost includes direct resistive heat.
7. Full texts not read (paywalled): Milev et al. 2023 (UK defrost electricity demand) [40]; Carroll et al. 2020 (field-study review with a defrost-management focus) [23]; Klingebiel et al. 2025 (gap between conventional and optimal initiation) [14]; Kropas et al. 2021 (Lithuanian measurement details) [4]. These would sharpen the numbers above.
8. The heatpumpmonitor reverse-heat metric is a heat-meter quantity. I assumed `combined_cooling_kwh` on non-cooling systems ≈ defrost, from the data and the dashboard code treating negative heat as cooling [39]. The emoncms post-processing that computes it was not inspected.

## Sources

1. A Critical Literature Review of Defrost Technologies for Heat Pumps and Refrigeration Systems (ORNL/TM-2018/1007) - Nawaz, Elatar, Fricke / Oak Ridge National Laboratory - 2018 - https://info.ornl.gov/sites/publications/Files/Pub117976.pdf - paper (review; cites lab and field) - Frost band −7…+5 °C at RH > 65 %; frosting > 80 % of cycle time; reverse-cycle energy sources (71.8 % from the indoor side, 59.4 % to melting, max efficiency about 60 %); defrost efficiencies 34.5-53 %; control strategy taxonomy; airflow and fin effects.
2. Review on improvement for air source heat pump units during frosting and defrosting - Song, Deng, Dang, Mao, Wang / Applied Energy 211 - 2018 - https://ideas.repec.org/a/eee/appene/v211y2018icp1150-1170.html - paper (review, abstract) - Scope: 12 frost-retarding measures, 5 defrost methods, control strategies; used to trace primary studies.
3. A new frosting map of variable-frequency air source heat pump in severe cold region considering the variation of heating load - Wei, Ni, Li, Wang, Yao, Xu, Yang / Renewable Energy 161 - 2020 - https://ideas.repec.org/a/eee/renene/v161y2020icp184-199.html - lab/field rig (abstract) - No frost at 0 °C/80 % RH at low load; critical RH 80.6 % → 62.75 % (+1 → −26.5 °C); fastest frosting near −10 °C. Load and speed shape frosting.
4. Experimental Investigation of Frost Formation Influence on an Air Source Heat Pump Evaporator - Kropas, Streckienė, Bielskus (VGTU, Lithuania) / Energies 14(18):5737 - 2021 - https://ideas.repec.org/a/gam/jeners/v14y2021i18p5737-d633785.html - field/lab measurement (abstract; MDPI full text 403) - Lithuanian data: frost from < 3.5 °C at 88 % RH; defrost about 5 min average.
5. Field test investigation of the characteristics for the air source heat pump under two typical mal-defrost phenomena - Wang, Xiao, Guo, Lu, Feng / Applied Energy 88 - 2011 - https://ideas.repec.org/a/eee/appene/v88y2011i12p4470-4480.html - field data (abstract) - Late defrost: COP −17.4 %, capacity −29 %; needless defrosts: −4.2 %.
6. Performances of air source heat pump system for a kind of mal-defrost phenomenon appearing in moderate climate conditions - Wang, Feng, Zhu, Li, Guo, Lu / Applied Energy 112 - 2013 - https://ideas.repec.org/a/eee/appene/v112y2013icp1138-1145.html - field data (abstract) - Mild-weather mal-defrost: > 60 % coil frosted after 5 days; COP 2.3 at +7.9 °C; COP −40.4 %, capacity −43.4 %; COP 5.0 after manual defrost.
7. Determination method of defrosting start-time based on temperature measurements - Kim, Lee / Applied Energy 146 - 2015 - https://ideas.repec.org/a/eee/appene/v146y2015icp263-269.html - lab (abstract) - Timer initiation error ±50 % vs ±10 % for a temperature-based method.
8. Determination of the optimal defrosting initiating time point for an ASHP unit based on the minimum loss coefficient in the nominal output heating energy - Wang, Zhang, Li, Sun, Deng, Wu / Energy 191 - 2020 - https://ideas.repec.org/a/eee/energy/v191y2020ics0360544219322005.html - field + model (abstract) - An optimal initiation point exists; it decreases with RH and is non-monotonic in temperature.
9. A semi-experimental method for evaluating frosting performance of air source heat pumps - Pu, Shen, Zhang, Liu / Renewable Energy 173 - 2021 - https://ideas.repec.org/a/eee/renene/v173y2021icp913-925.html - lab (abstract) - System-specific frosting plots; uneven frosting; higher air velocity suppresses frosting.
10. Energy transfer procession in an air source heat pump unit during defrosting - Song, Xu, Mao, Deng, Xu / Applied Energy 204 - 2017 - https://ideas.repec.org/a/eee/appene/v204y2017icp679-689.html - lab (abstract) - Defrost efficiency 42.26 % → 48.34 % with a 50 % larger coil; metal heat-storage effects.
11. Comparison between hot-gas bypass defrosting and reverse-cycle defrosting methods on an air-to-water heat pump - Huang, Li, Yuan / Applied Energy 86 - 2009 - https://ideas.repec.org/a/eee/appene/v86y2009i9p1697-1703.html - lab (abstract) - 55 kW air-to-water unit; hot-gas bypass slower but gentler on the heating side.
12. Continuous heating of an air-source heat pump during defrosting and improvement of energy efficiency - Jang, Bae, Lee, Ha / Applied Energy 110 - 2013 - https://ideas.repec.org/a/eee/appene/v110y2013icp9-16.html - lab (abstract) - Continuous heating during defrost: +17 % capacity, +8 % efficiency vs reverse cycle over 4 h / 2 defrosts.
13. A self-optimizing defrost initiation controller for air-source heat pumps: Experimental validation of deep reinforcement learning - Klingebiel, Höges, Horst, Nießen, Venzik, Vering, Müller (RWTH) / Applied Energy 398 - 2025 - https://ideas.repec.org/a/eee/appene/v398y2025ics0306261925011304.html - lab HiL (abstract) - ≤ 1.9 % from optimal; +7.1 % SCOP vs time-based, +9.1 % vs demand-based; +16.6 % with a partly blocked coil.
14. Optimal defrost initiation for air-source heat pumps: Evaluating the improvement potential of common defrosting controllers - Klingebiel et al. / Energy 324 - 2025 - https://ideas.repec.org/a/eee/energy/v324y2025ics0360544225015130.html - lab/simulation (abstract, no numbers) - Gap between conventional and optimal initiation is uncertain and parameter-dependent.
15. Optimal heat pump defrosting strategies for full-cycle capacity and COP maximization - Ikram, Ali, Alexander, Bach / Energy 336 - 2025 - https://ideas.repec.org/a/eee/energy/v336y2025ics0360544225039441.html - lab (abstract) - Defrost depends on component speeds; approach-temperature initiation; +1.5…+7.9 % per cycle with optimised fan and compressor speeds.
16. Applying neural network model to real-time frosting detection and intelligent defrosting control for air source heat pump - Zhao et al. / Applied Energy 377 - 2025 - https://ideas.repec.org/a/eee/appene/v377y2025ipas0306261924018270.html - lab (abstract) - Image-based defrost: COP +11.83 %, defrost frequency −75 %, defrost energy −88 %.
17. Deep learning-based image recognition method for on-demand defrosting control to save energy in commercial energy systems - Chen, Chen, Zhu, Jin, Du / Applied Energy 324 - 2022 - https://ideas.repec.org/a/eee/appene/v324y2022ics0306261922009965.html - field (commercial; abstract) - vs fixed-interval: frequency −31.68 %, defrost time −65.83 %, energy −42.92 %.
18. Deep learning-based prediction method on performance change of air source heat pump system under frosting conditions - Eom, Chung, Park, Hong, Kim / Energy 228 - 2021 - https://ideas.repec.org/a/eee/energy/v228y2021ics036054422100791x.html - lab (abstract) - Predicts capacity, power and COP decay under frost from existing sensors (RMS 2.4-3.4 %).
19. Advancements in anti-frosting and defrosting techniques for air source heat pumps: A comprehensive review of recent progress - Ma, Sun, Wang, Wang, Zhang, Wang / Applied Energy 377 - 2025 - https://ideas.repec.org/a/eee/appene/v377y2025ipas0306261924017410.html - paper (review, abstract) - 2018-2023 landscape; operational optimisation as an anti-frost lever; ML, model and image-based defrost control.
20. Advanced defrosting techniques in air source heat pumps: A review of vapor injection, thermal energy storage, and experimental frost accumulation data - Yang, Lee, Muehlbauer, Hwang / Energy 340 - 2025 - https://ideas.repec.org/a/eee/energy/v340y2025ics0360544225049047.html - paper (review, abstract) - Frost-accumulation data scarce; durations and termination criteria vary widely by design.
21. Review on research status and prospect of frost suppression methods for air source heat pump system in last decade - Si, Lin, Ni / Renewable and Sustainable Energy Reviews 239 - 2026 - https://ideas.repec.org/a/eee/rensus/v239y2026ics1364032126004508.html - paper (review, abstract) - Adjusting operation strategy to raise evaporator surface temperature is a recognised frost-suppression category.
22. Frosting Phenomenon and Frost-Free Technology of Outdoor Air Heat Exchanger for an Air-Source Heat Pump System in China: An Analysis and Review - Zhang et al. / Energies 11(10):2642 - 2018 - https://ideas.repec.org/a/gam/jeners/v11y2018i10p2642-d173548.html - paper (review, abstract) - Frosting maps need improvement; frost-free ASHP total COP 30-64 % higher under frosting.
23. Air Source Heat Pumps field studies: A systematic literature review - Carroll, Chesser, Lyons / Renewable and Sustainable Energy Reviews 134 - 2020 - https://ideas.repec.org/a/eee/rensus/v134y2020ics1364032120305621.html - paper (review, abstract) - Defrost management is one of three main field-study focus areas; points to public datasets.
24. Cold climate air source heat pumps: Industry progress and thermodynamic analysis of market-available residential units - Konrad, MacDonald / Renewable and Sustainable Energy Reviews 188 - 2023 - https://ideas.repec.org/a/eee/rensus/v188y2023ics1364032123005968.html - paper (review, abstract) - All surveyed cold-climate units use reverse-cycle defrost and variable-speed compressors.
25. Development and validation of a dynamic modeling framework for air-source heat pumps under cycling of frosting and reverse-cycle defrosting - Ma, Kim, Braun, Horton (Purdue) / Energy 272 - 2023 - https://ideas.repec.org/a/eee/energy/v272y2023ics0360544223004243.html - paper (model validated on lab data, abstract) - Simulation tooling exists for frost/defrost cycling.
26. Field demonstration of predictive heating control for an all-electric house in a cold climate - Pergantis et al. (arXiv 2402.07032) - 2024 - https://ar5iv.labs.arxiv.org/html/2402.07032 - field data - 1.3 vs 2.7 defrosts/day (MPC vs not) below 0 °C at 70-80 % RH; small sample; backup heat during defrost.
27. Long-term experimental study of price responsive predictive control in a real occupied single-family house with heat pump - Thorsteinsson et al. (arXiv 2303.16289) - 2023 - https://ar5iv.labs.arxiv.org/html/2303.16289 - field data - Defrost treated as a random priority event; controller put on standby during defrost and DHW.
28. Heat pump defrost: why it happens in UK winters - Energy Stats UK - n.d. (about 2024-25) - https://energy-stats.uk/heat-pump-defrost/ - blog (owner's monitored data) - Frost at about +3 °C; defrosts every 90-120 min at −0.9…+1.9 °C; every about 40 min in noise-reduction mode; UK RH 80-90 %; volumiser suggestion.
29. UK winter heat pump COP - Energy Stats UK - n.d. - https://energy-stats.uk/uk-winter-heat-pump-cop/ - blog (owner data, 5 kW Vaillant) - Heating COP by daily temperature: 3.1 at −2…−1 °C up to 5.4 at 11-12 °C; SCOP 4.19.
30. First winter with my air source heat pump - Energy Stats UK - n.d. - https://energy-stats.uk/first-winter-with-my-air-source-heat-pump/ - blog (owner data) - Defrost below about +4 °C; about 7 min defrost about every 90 min; DHW COP 2.0 at 0 °C vs 3.8 at 18 °C.
31. Heat pump cycling - Energy Stats UK - n.d. - https://energy-stats.uk/heat-pump-cycling/ - blog - Cycling when load is below minimum output; cycle-length examples; no defrost link.
32. Max output testing (HeatpumpMonitor.org results) - OpenEnergyMonitor docs - n.d. (about 2024-25) - https://docs.openenergymonitor.org/heatpumpmonitor/max_output_testing.html - field data - Sustained output across defrosts 7-25 % below datasheet at −5…+1 °C; 20-30 % sizing margin.
33. % of ideal Carnot COP (HeatpumpMonitor.org results) - OpenEnergyMonitor docs - n.d. - https://docs.openenergymonitor.org/heatpumpmonitor/prc_carnot.html - field data + manufacturer table - COP 4.6 at 40 rps vs 3.3 at 110 rps (Vaillant tables); causes of %-Carnot spread.
34. Experience with a 7kW Vaillant Arotherm - OpenEnergyMonitor community - 2025 - https://community.openenergymonitor.org/t/experience-with-a-7kw-vaillant-arotherm/27714 - forum - "Defrost death spiral" hypothesis from tariff-driven ramp-ups, disputed; no defrost data.
35. Dynamic heat pump simulator - OpenEnergyMonitor community - 2025-26 - https://community.openenergymonitor.org/t/dynamic-heat-pump-simulator/28315 - forum - Simulator lacks a defrost model (author lists it as needed).
36. Gree Versati III air to water heat pump (thread, page 6) - Home Assistant Community - 2026 - https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916?page=6 - forum (field observation) - 16 kW Versati III: quiet mode cuts fan speed; defrost every about 52 min at +2…+5 °C, about 56 min overnight; much rarer without quiet mode.
37. VERSATI III Compact Monoblock (R32) service manual - Gree (hosted by Klimakoncept) - about 2021 - https://www.klimakoncept.hr/upload/2-pdf-klimakoncept/4-dizalice-topline/6-gree-versati/Service-Manual-Versati-III-Compact-Mono-BlockR32-klimakoncept.pdf - manufacturer - "Smart" defrost claim; coil defrost sensor and suction pressure used for defrost; fan speed follows low-side pressure in heating; fan stops and 4-way valve reverses in defrost; minimum water volume 20 L; plate-exchanger heater; ratings at 7 °C DB / 6 °C WB.
38. Air-to-Water Heat Pump Service Manual, Versati (first generation, R410A) - Gree (hosted by Gree Bulgaria) - about 2012 - https://gree-bulgaria.com/manuals/archive/5_Versati-TSM.pdf - manufacturer - Defrost entry: ≥ 50 min accumulated run (30-60) and coil < −4 °C (−10…0). Exit: 10 min (1-15) / coil > 15 °C (5-30). Fan stops. Water anti-freeze at < 3 °C. Chassis heater < 0 °C.
39. HeatpumpMonitor.org open dataset (daily stats for 113 systems, 2023-04 to 2026-11; system stats API; dashboard code) - OpenEnergyMonitor - 2026 - https://heatpumpmonitor.org/system/stats/last365 and https://github.com/openenergymonitor/heatpumpmonitor.org - field data (own analysis) - Reverse-heat share and kWh by outdoor-temperature bin; COP by bin; within-system load, duty and flow tests; starts vs defrost.
40. Air source heat pump (article and reference list) - Wikipedia - 2026 revision - https://en.wikipedia.org/wiki/Air_source_heat_pump - blog/encyclopedic (secondary) - Defrost mechanism; installer claim of a negligible water dip; pointed to ORNL [1], NREL and Milev et al. 2023 (Energy and Buildings 300:113656, not readable).
41. Applying image recognition to frost built-up detection in air source heat pumps - Li, Wang, Sun, Wang, Deng, Lin / Energy 233 - 2021 - https://ideas.repec.org/a/eee/energy/v233y2021ics0360544221012524.html - lab (abstract) - Camera-based frost detection robust to lighting; basis for on-demand defrost.
42. Running ASHP efficiently - general thought process "low and slow" (page 2) - Renewable Heating Hub forum - 2024 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/runing-ashp-efficiently-general-thought-process-low-and-slow/paged/2 - forum - Low-and-slow UFH practice on a 5 kW Ecodan; minimum output 1.9-2.4 kW; no defrost data (checked, little contribution).
43. Final report on analysis of heat pump data from the RHPP scheme - Lowe et al. / RAPID-HPC for BEIS - 2017 - https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/606818/DECC_RHPP_161214_Final_Report_v1-13.pdf - field data - Checked: no defrost analysis found in the extracted text (negative result).
44. Internal sweep notes 06 (MPC academic) and 08 (Gree Versati) - this project, docs/research/notes/ - 2026 - local files - secondary - Modbus coils and registers for defrost status, coil temperature and manual defrost; C/P power limit; Kuboth et al. daytime-shift result; Versati III volume data.
