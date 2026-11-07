# Model predictive control for residential heat pumps: academic and commercial evidence

Researcher note 06. Scope: field, lab and simulation evidence for model predictive control (MPC) and "smart optimiser" products on residential heat pumps, and what it implies for a slab-UFH house with a 9 kW Gree Versati whose minimum output (~3.7-3.8 kW) exceeds the mild-weather load (~1.7 kW at +10 °C), controlled by writing the leaving-water setpoint over Modbus, with a firmware restart rule of setpoint - outlet >= ~4 K.

Method note: 38 web searches (English, German, Polish, Swedish, Dutch; Lithuanian not done because the shared search budget ran out), 46 sources read (papers, field reports, HiL lab papers, a government programme report, manufacturer pages, forums, open-source docs). PDFs were read as full text where possible. Evidence ranking used throughout: measured field data > controlled lab / hardware-in-the-loop (HiL) > peer-reviewed simulation > manufacturer claim > forum anecdote. Where I only saw an abstract or a search snippet, this is said explicitly.

## Summary

- **Compared with a well-tuned, low weather-compensation (WC) curve, measured MPC gains are small: about 4-5 % electricity, more in cost.** A 125-day twin-rig test with a real 6 kW air-source heat pump (ASHP) used a baseline curve set as low as comfort allowed (38 °C flow at -20 °C). Against it, MPC cut electricity by 4.1 % (1032 to 990 kWh) and raised COP from 4.46 to 4.70 (+5.4 %). Cost fell 9.0 %, mostly through PV self-consumption, and comfort was slightly worse [5]. In lab and simulation tests where the reference was already near-optimal, MPC gave about 5 % cost saving in heating and rule-based control gave none [14].
- **The big headline savings come from poor baselines.** Field reviews report average residential savings of 22 % energy and 16 % cost (25 filtered tests, each at least 7 days) [1], and 25-30 % across all building field studies [2]. The Purdue occupied-house tests saved 18-20 % [6][7], but most of that came from avoiding resistance backup heat and fixed setpoints. Those baselines are not a tuned WC curve.
- **Most of the "MPC" efficiency gain is simply running the lowest flow temperature the house needs.** In the Chalmers simulation, forecast control saved about 7-9 % (about 10 kWh/m²), and most of that came from fitting the supply temperature to actual demand, not from the weather forecast [13]. In the Aalborg simulation, feedback control saved about 13 % against a pure outdoor-temperature curve. Adding a forecast improved comfort tracking by about 55 % but left mean COP unchanged (7.24 vs 7.25) [12]. Each +1 K of flow temperature costs roughly 2-3 % COP [27].
- **When MPC optimises price, electricity use often rises.** The closest analogue to this house is a Danish 7 kW air-to-water heat pump (AWHP) heating an occupied concrete-floor house over 97 days. Mixed-integer MPC cut cost by 2-17 % (12.4 % overall) but raised electricity by 9.5 % and heat by 3.7 %. Dynamic operation was less efficient than the factory heating curve, savings peaked at 0.7-4 °C outdoor, and days below about 0 °C lost money [4]. In other cases COP fell from 7.6 to 6.0 while cost dropped 40 % [18], and slab pre-charging ended up running mostly on the immersion heater [17].
- **The control interface decides whether MPC causes cycling.** In HiL tests on underfloor heating (UFH), MPC that wrote the flow setpoint gave the lowest energy but many compressor starts and comfort losses. MPC that set compressor speed directly gave fewer on/off cycles. Both saved up to 20 % against a heating curve [9]. In the Danish field test, overriding the outdoor sensor and blocking the compressor worked but was described as "a functional but inefficient way". Starts lagged 60-120 min, and one compressor block made the unit heat DHW on its 10 kW electric rod [4].
- **One field-proven architecture matches this house almost exactly.** EPFL (2026) ran MPC on a Home Assistant hub controlling a Mitsubishi Ecodan with UFH. The MPC plans heat power every 15 min, and an inner loop updates the flow setpoint every minute in bounded steps so that delivered energy tracks the plan. It used a 2-state (room, floor) ARX model refitted hourly and an 8 h horizon [8].
- **Long runs make on/off cycling cheap in energy terms; it matters more for wear and for how each run is executed.** Start/stop losses stay below 2 % when runs last at least 15 min, and at least 20 min is recommended [11].
  - In annual UFH simulations, the hysteresis setting moved SCOP by only about 3.6 % (3.14 to 3.25), even though 2 K hysteresis often reached 240 cycles per day. In the radiator case, cycles rose about 250 % while SCOP stayed within about 2 % [11].
  - Inner-loop PI settings changed UFH SCOP by up to 18.5 %, and poor settings caused 300 % more avoidable starts in HiL tests [11].
  - About 12 % more cycles can cost up to 15 % of compressor life (cited in [11]).
- **When load is below the compressor's minimum output, the controller must decide on/off explicitly** (mixed-integer). A continuous model that asks for sub-minimum output produces short bursts and cycling [25]. The Danish field MPC therefore modelled minimum load, minimum off-time and start delay [4]. The German twin-rig MPC rounded requests of 10 % or less to zero [5].
- **Most of the energy MPC saves is heat it no longer delivers, not better COP.** In HiL tests, MPC used 11 % less electricity but SCOP rose only 3 %, with 5 K lower mean supply temperature and 46 Hz vs 63 Hz mean compressor speed, under perfect forecasts [10]. In a Danish UFH simulation, MPC used 9-13 % less electricity while COP rose only 2.1-2.3 % [27]. The rest comes from avoiding overheating and using solar and internal gains.
- **Simple models are enough, but they must be refitted and checked.** A 1-state RC model (C ≈ 6.5 kWh/K, one-step RMSE 0.41 °C) ran an occupied house [6], and a 2-state single-zone model was adequate in the Danish AWHP field test [4]. The Danish COP model had to be refitted four times in 97 days [4], and online black-box learning produced a physically impossible negative solar coefficient [7].
- **Forecast errors mainly hurt comfort and PV use.** Imperfect forecasts reduced MPC's PV self-consumption gain by 4.6-11.1 % against perfect foresight, but MPC still beat the heating curve [16]. Unreliable cloud forecasts caused overheating on sunny days in the Danish concrete-floor house [4]. In a glazed slab house, irradiance (GHI) forecasting was critical and only about 71 % of 182 days ran well [20].
- **Short tests exaggerate savings.** Residential cost savings averaged 57 % in tests shorter than a week, against 22 % in longer tests [1]. The same rig saved 19.7 % electricity in a short test and 4.1 % over 125 days [5]. Any A/B test on this house therefore needs weeks, not days.
- **Independent evidence for commercial optimisers is thin.** Products: Homely, Havenwise, Passiv, tado, Ngenic, Neogrid, NIBE SPA, Viessmann, Octopus, Quatt.
  - Homely saved 22 % of annual heating cost in a Salford twin-house lab test, rising to 53 % with PV and battery [28][29].
  - Passiv raised space-heating COP by 17 % on standalone heat pumps (EST field trial, Oct-Dec 2021) [30].
  - Ngenic reports 20-23 % kWh saving from its own before/after data on 50 of 500 customers, not weather-normalised [36].
  - Neogrid claims 5-15 % [37], and tado claims 4/7/11 % for progressively lower curve presets [32].
  - NIBE and Viessmann features shift consumption in time and do not raise efficiency [31][38].
  - Havenwise and Quatt have no published measured results that I found [35][39][41].
- **Bottom line for this house (medium confidence):** MPC is worth it here mainly as a scheduler. It should place long minimum-output runs in the warmest or PV-surplus hours, keep DHW out of the way, and avoid high-power catch-up runs. It should not replace a correct low flow-temperature law. Against a well-tuned WC curve plus a sensible cycle governor, expect about 3-10 % less electricity. Against the current high-setpoint catch-up behaviour the upside may be 10-25 %, but that is an inference from COP sensitivity [27][10] and needs measurement.

## Detailed findings

### 1. What the field evidence says overall (reviews)

- **Khabbazi et al. 2025 review [1]** covers 104 papers and 206 field tests (24 residential papers with 52 tests). After filtering for measured baselines, whole-building control and at least 7 days, 25 residential tests from 9 papers remained.
  - Duration-weighted average residential savings were 22 % energy and 16 % cost. Commercial savings were 15 % energy and 13 % cost.
  - Energy savings ranged from -0.4 % to 60.4 %, and cost savings from 1.3 % to 39 %.
  - Only 9 % of papers reported confidence intervals, and about 71 % used protocols that may give unreliable estimates.
  - Thermal-mass bias: an advanced controller can "inherit" a charged building mass from the baseline period and leave it depleted, so tests shorter than a week show systematically higher savings (57 % vs 22 % cost, residential).
  - Model error is often comparable to the 10-20 % savings being measured, which makes savings hard to detect.
  - About two-thirds of MPC papers used linear models, mostly RC networks with 1-3 states per zone.
  - 75 % of residential tests changed only high-level setpoints (thermostat or room setpoint). 25 % actuated low-level devices such as valves or compressors.
  - Costs were reported in only 13 of 104 papers.
- **Heat-pump and hydronic entries in that review's table [1]** (secondary summary; I did not read each original):
  - Pedersen et al. 2013, Denmark: 4 single-family houses with radiant floor and ground-to-water heat pumps; 9.2 % cost saving vs measured baseline over 152 days.
  - Bünning et al., NEST, Switzerland: AWHP with radiant ceilings; 24.9 % energy saving over 6 days.
  - Vivian et al. 2022, Italy: AWHP with fan coils; 10-17 % cost saving.
  - Finck et al., Netherlands: hydronic floor heating fed by a heat pump; 12-15 % cost saving over 1 day.
  - Knudsen et al. 2021, Norway: 22.5 % cost saving vs a simulated baseline.
  - Brown & Beausoleil-Morrison, Ottawa: hydronic floor; 40.6 % energy saving over 13 days.
  - Thorsteinsson et al. 2023, Denmark: variable-speed AWHP for space heating and DHW; 2.3-32.8 % cost saving over 10-50 days.
- **Saloux et al. 2025 review [2]:**
  - Average reported savings were 30 % thermal energy, 25 % electricity, 25 % cost, 26 % peak power and 17 % GHG.
  - The average field test lasted 41 days, and most buildings were under 10,000 m².
  - These are raw averages of reported results, not filtered for baseline quality.
- **Drgoňa et al. 2020 [3]:** a widely cited methodological review. Its conclusion is that practical MPC applications are still at an early stage and that standardised performance assessment is missing.
- **Cost-benefit [1]:**
  - Sturzenegger et al. (7-month Swiss office MPC) warned that engineering cost may outweigh savings. Added instrumentation cost 3,000-6,000 CHF and the weather-forecast subscription 100-600 CHF/yr.
  - The Purdue residential deployment took about 190 engineer-days: about 150 one-off and about 40 per additional home [6].

### 2. Heat-pump-specific field and lab tests (closest analogues first)

| Study | System | Baseline | Duration | Result | Evidence |
|---|---|---|---|---|---|
| Thorsteinsson et al. 2023 [4] | 230 m² BR2020 house, Zealand DK; Bosch Compress 6000AW 7 kW AWHP; UFH embedded in concrete, 11 zones; PV 4-5.5 kW | Factory WC heat curve, 193 benchmark days matched on ambient ±0.5 °C and PV ±2 kWh | 97 days, 4 comfort levels | Cost -12.4 % overall (-2.3 % to -29.1 % by level); electricity **+9.5 %** (743 to 813 kWh); heat +3.7 % | Field |
| Kuboth et al. 2020 [5] | Twin rigs, real 6 kW ASHP (W35/A2), 500 L store, emulated SFH, real weather, 4.8 kWp PV model | Heating curve at the lowest comfortable setting (38 °C at -20 °C) | 125 days, Dec-Apr | Electricity -4.1 %, COP +5.4 % (4.46 to 4.70), HP PV self-consumption +107.7 %, cost -9.0 %; slightly worse comfort | Lab (twin, real weather) |
| Pergantis et al. 2024 [6] | 208 m² occupied house, Indiana; variable-speed air-to-air HP + 19.2 kW resistance backup | Manufacturer control with fixed setpoints | 33 MPC days of 59 | Heating energy -19 % (95 % CI 13-24 %); backup heat -38 %; winter cost -28 % | Field |
| Purdue RL vs MPC 2025 [7] | Same house | Constant setpoint (21 °C) | about 1 month each | MPC about -18 to -20 %, RL about -21 to -22 %; RL worse comfort (PPD 14 % vs 9.3 %) | Field |
| Shi & Jones 2026 [8] | Swiss single-family house, Mitsubishi Ecodan + UFH, Home Assistant | Ecodan built-in WC | 6-day runs | Discomfort budgets met; energy not weather-matched, so authors claim no field saving. Simulation: -31.9 % energy vs BOPTEST default | Field + sim |
| Göbel et al. 2023 [9] | HiL: real inverter HP + simulated UFH house | Heating curve | test days | Up to -20.25 % power; flow-setpoint MPC = many starts | Lab (HiL) |
| Will et al. 2025 [10] | HiL, inverter ASHP, Potsdam winter day | Heating curve + PI | 1 typical day | Electricity -11 %, SCOP +3 %, supply -5 K, compressor 46 vs 63 Hz (perfect forecasts) | Lab (HiL) |
| Hummel et al. 2022 [16] | HiL, ground-source HP + storage | Heat-controlled rule-based control | 4 days | PV self-consumption +38.9 % (MPC) vs +6.2 % (PV rule) | Lab (HiL) |
| Allison et al. 2017 [17] | Low-carbon house near Glasgow; ASHP + UFH + immersion | n/a | 4 weeks | Comfort 18-23 °C about 87 % of 07-22 h; heat pump performance under load shifting extremely poor, most heat from the immersion | Field |
| Hochschule Offenburg [18] | Low-energy non-residential building, heat pump + storage | Conventional control | 7 days | Cost -40 % (procurement 0.36 to 0.12 €/kWh); COP **7.6 to 6.0** | Field |
| Péan 2020 [14] | Real AWHP on thermal benches + TRNSYS | Near-optimal vs improvable reference | lab campaigns | Near-optimal reference: MPC about 5 % cost (heating), rule-based 0 | Lab + sim |
| DTI OPSYS 2017 [27] | Simulation and test rig, UFH with on/off telestats | PI on/off telestat control | 2-day period | MPC: electricity -9 to -13 %, forward temp -0.3 to -0.9 K, COP +2.1-2.3 %, telestat moves up to 5x | Sim + rig |

Thorsteinsson et al. [4], details relevant to this house:
- The supervisory mixed-integer MPC (CasADi + Bonmin) computed an hourly heat budget. A middle layer tracked it by feeding an artificial outdoor temperature into the heat pump's own WC curve, with a relay to block the compressor.
- The model was a 2-state RC (room air, floor) with a Kalman filter every 5 min. Constraints covered on/off state, minimum load, ramp rate, minimum off-time and a start delay of about 1.5 h.
- Tariff: Danish distribution tariff 0.027 €/kWh (00-06), 0.081 €/kWh (06-17 and 21-24) and 0.26 €/kWh (17-21), plus spot price and 25 % VAT. Blocking the heat pump during the 17-21 peak produced about 66 % of all savings.
- Average saving was €0.29 per day, so €1,200 of hardware would take about 34 years to repay.
- Problems: the COP fit overestimated efficiency and needed 4 refits; cloud forecasts were unreliable, leading to sunny-day overheating; defrost reverses heat flow; the heat pump sometimes shut down unexpectedly (high ambient, low flow); and model updates were manual and costly.
- The authors recommend a standard, dedicated reference-control input on heat pumps.

Kuboth et al. [5] showed the strongest seasonal pattern:
- Cost savings averaged 8.2 % in December-February, 4.9 % in March (MPC over-produced heat) and 42.1 % in April (high irradiance).
- The extra COP came from moving operation to daytime from about 10:00, when air is warmer and PV is available.
- An earlier short-term test on the same rig gave -19.7 % electricity, +22 % COP and -34 % cost, roughly 4x the long-term result.

Pergantis et al. [6] identified three saving mechanisms:
- Lower overnight setpoints in the coldest, lowest-COP hours (00-03).
- Gradual morning warm-up instead of a 2 K setpoint step, which had triggered backup elements: -27 % on one comparison day.
- Pre-heating ahead of high loads.

Defrosts were 1.3 per day with MPC vs 2.7 without, but the sample was too small to conclude.

### 3. Baseline matters: MPC vs a well-tuned weather-compensation curve

This is the key question for a slab-UFH house. The evidence lines up as follows:

1. **Well-tuned curve as baseline:**
   - The 125-day twin-rig test is the most rigorous long test against a deliberately minimised heating curve. Electricity fell 4.1 %, COP rose 5.4 % and cost fell 9 % with PV [5].
   - In the lab and simulation thesis, a near-optimal reference left MPC about 5 % (cost, heating) and rule-based control 0 % [14].
   - A one-year closed-loop simulation study cited in [8] found white-, grey- and black-box MPC saved 4.9-8.4 % energy against a well-tuned rule-based controller. This is secondary: I read the citing paper, not the original.
2. **Forecasts vs supply-temperature adaptation:**
   - Swedish forecast-control products claim 10-15 % savings (over 10 million m² installed, mostly multifamily). Simulation finds about 7-9 %, and attributes most of it to demand-adapted supply temperature rather than the forecast [13].
   - The Aalborg UFH simulation reached the same split: about 13 % from feedback vs pure feed-forward, and essentially zero COP benefit from forecasts [12].
3. **Poor or typical baselines:**
   - Poor baselines produce the 15-30 % figures: field reviews [1][2], Purdue [6][7], and the UK Heat Pump Ready (HPR) programme, where fixed settings on a flat tariff were compared with dynamic WC on a time-of-use tariff [28].
   - A Danish study cited in [27] found only about 15 % of heat pumps perform as expected. It estimated that optimised flow and forward temperature could improve a SPF-3 installation by up to 25 %.
4. **Community simulation [43]** (OpenEnergyMonitor dynamic simulator, 5 kW Vaillant model, 3.4 kW heat-loss house):
   - Poorly configured systems (WC too high, or fixed around 60 °C) used about 37 % more electricity than well-optimised continuous heating.
   - Load-compensated continuous heating reached an SPF of about 4.1.
   - On a fixed tariff, a 17 °C setback with a gradual warm-up was cheapest (£468 vs £550). The author's conclusion: lower flow temperatures and good modulation matter most, and well-implemented WC with a parallel shift can perform similarly to load compensation.
5. **heatpumpmonitor.org data (search snippet only; page blocked, 403):** across 282 monitored systems, pure WC without room influence had a median SCOP of 3.97, against 3.48 with significant room influence [48]. Treat this as unverified and correlational.

**Synthesis:** MPC's unique, robust value over a good WC curve is around 5 % in energy. It grows when one or more of the following applies:
- There is a price signal or PV surplus to exploit [4][5][16].
- Solar or internal gains are large relative to load, which favours forecast-aware control in mild, sunny shoulder months [5][10][27].
- Hardware constraints need explicit scheduling, such as minimum output above load, DHW priority or backup heaters [6][25].

### 4. Energy vs cost: when MPC uses more kWh

- **Price-chasing increases energy:**
  - Danish AWHP: +9.5 % electricity for -12.4 % cost [4].
  - Non-residential building: COP 7.6 to 6.0 for -40 % cost [18].
  - Aalborg simulation: the price-driven variant cut cost about 10 % but raised mean water temperature about 2.2 %. The authors note the conflict directly: night power is cheap, but daytime air is warmer and gives a higher COP [12].
  - Lab and simulation thesis: cost-optimal and CO₂-optimal operation contradict each other [14].
- **Load-shift pre-charging of a slab** can push heat pumps into regimes where auxiliary heaters take over (Glasgow field test, most heat from the immersion [17]). It can also overshoot comfort on sunny days (Danish test [4]; Swiss Solarhaus press report [40]).
- **Energy-objective MPCs reduce kWh,** but mostly by delivering less heat:
  - HiL: -11 % electricity but only +3 % SCOP [10].
  - Danish UFH simulation: -9 to -13 % electricity but only +2.1-2.3 % COP [27].
  - Twin rig: heat +1.1 % yet electricity -4.1 %, because operation moved to warmer hours [5].
- **Trade press view of a manufacturer feature:** the 42watt review of Viessmann's "Dynamic Assistant" and PV-surplus features says the software does not raise efficiency. It only moves the time of consumption, so savings come from the price, and there is little benefit without a dynamic tariff [38].

### 5. Which ingredients matter most

#### 5.1 Flow temperature and COP modelling

- Each 1 K of forward temperature costs about 2-3 % COP. Forward temperatures are commonly set too high to guarantee heat, and the further above the minimum needed, the larger the flow-temperature fluctuations become [27].
- COP must be modelled as a function of outdoor temperature and flow temperature (or temperature lift). In the field, a Carnot-fraction COP fit that looked good offline overestimated efficiency under MPC operation and needed 4 refits [4].
- Making COP depend on supply temperature (which itself depends on delivered power) turns the optimal-control problem non-convex. Convex approximations fix the supply temperature or use a COP profile driven only by ambient temperature (abstract-level, Verhelst/Helsen; full text unavailable, 429).
- Practical tools commonly use Carnot × 0.4 (EMHASS default [45]) or a quadratic in outdoor temperature (Purdue, R² = 0.98 on manufacturer data [6]).
- Where COP depends strongly on outdoor temperature, the optimiser is encouraged to shift load to warmer hours [6][5]. For an air-source unit in a humid climate, defrost also matters; one forum user hypothesised a defrost spiral from ramp-ups, but it was disputed and unmeasured [42].

#### 5.2 Weather forecasts

- Forecasts mainly buy comfort (about 55 % better temperature tracking in the Aalborg UFH simulation) and PV self-consumption. They do little for COP [12][16].
- Forecast errors cause the typical field failures: unpredicted temperature drops broke the lower comfort limit by up to about 1 K [5]; cloud and irradiance mis-forecasts caused overheating on slab floors [4][20].
- Even low-quality forecasts beat a heating curve for PV self-consumption [16].
- Horizon guidance:
  - Simulation: a 24 h horizon creates end-of-horizon artefacts unless a terminal value or longer prediction is used [23].
  - BOPTEST: for a building with a 3.03-day time constant, 6 h was the shortest horizon that still performed well [15].
  - Field practice: 24 h [5][6], 8 h at 15 min with hourly refits [8], hourly budget planning [4].

#### 5.3 On/off, minimum output, minimum run time: mixed-integer formulations

- Variable-speed heat pumps have a "dead zone" below minimum speed. A continuous MPC that asks for output there drives short bursts at minimum speed and more cycling. Adding a binary on/off decision lets the unit switch off instead (Lee et al. 2019; abstract-level [25]).
- The Danish field MPC was mixed-integer (Bonmin) with an on/off indicator, minimum load, minimum off-time and a start delay [4]. The lab thesis also used a mixed-integer MPC [14].
- The twin-rig MPC zeroed requests of 10 % or less because the heat pump cannot deliver very low part load [5]. Many simulation studies simply omit minimum run time, part load and cycling losses; Langer & Volling say so explicitly [23].
- Controller-level evidence from Göbel et al. 2023 [11]:
  - Start/stop losses are below 2 % if a run lasts at least 15 min (Uhlmann), and at least 20 min is recommended to avoid degradation.
  - In annual UFH simulation, hysteresis bandwidth moved SCOP only from 3.14 to 3.25 (3.6 %) but changed cycles a lot. At 2 K hysteresis, cycles often hit 240 per day below 10 °C.
  - PI integral time moved UFH SCOP by up to 18.5 %.
  - On the real heat pump there was a tipping point: 6 K hysteresis cycled, 8 K ran continuously.
  - Poor settings caused 300 % more avoidable starts.
  - Without a buffer tank, midday sun cut the required output. In their hydraulic model an overflow valve then reduced the flow, causing large supply-temperature amplitudes and cycling. A WC curve cannot see solar gain.
- **Implication:** cycling is not mainly a thermodynamic loss if runs are long. It is a wear issue, and a symptom of the controller and setpoint fighting each other.

#### 5.4 Model complexity and identification

- **Simple models suffice:**
  - Purdue occupied house: a 1-state RC (C ≈ 6.5 kWh/K, one-step RMSE 0.41 °C) fitted on one month of data was adequate [6].
  - Danish AWHP field test: a 2-state single-zone model, with averaged room temperatures, did not degrade comfort; the very well insulated shell probably helped [4].
  - EPFL: adaptive ARX (6/6 orders) on [room, floor] states, fitted on 5 days and refitted hourly [8].
  - Norway: a minimal black-box E-MPC (heat meter, two temperature sensors, a weather web service) realised the demand-response potential of the building mass [21].
- **Refitting is unavoidable:**
  - The Danish team refitted models several times by hand and called it too costly without automation [4].
  - Periodic recalibration and continuous commissioning are recurring lessons [1].
  - Online learning without enough excitation produced a negative solar-aperture coefficient, implying the sun cools the house [7].
- **Grey-box vs data-driven:**
  - BOPTEST: a 5th-order grey-box with an unscented Kalman filter and perfect forecasts gave up to 27.2 % cost and 90.8 % discomfort savings vs a PI baseline (48 h horizon, 15 min step, dynamic prices).
  - In the same study, model-free reinforcement learning (RL) failed comfort, and the authors concluded classical model-free RL is not valid for direct building control [15].
  - In the Purdue field test, RL saved slightly more energy than MPC but with worse comfort and higher variance [7].
  - The data-driven MPC in [10] used a neural network, with only HiL evidence.

#### 5.5 Interface level: room setpoint vs flow setpoint vs compressor

- 75 % of residential field tests acted only on high-level setpoints [1].
- The HiL comparison [9] is the most direct test of interface level. Flow-setpoint MPC gave the lowest energy but many starts and comfort losses. Compressor-speed MPC gave the best comfort and the least cycling.
- In the field, manipulating an outdoor sensor or blocking the compressor was fragile [4]. The lab thesis reports "control conflicts" with the heat pump's local controller [14].
- **Working pattern:** plan heat energy, and let a fast inner loop translate it into bounded flow-setpoint changes [8]. The supply-temperature rate was limited to 1 °C per 6-min step in [12].

### 6. Robustness and failure modes seen in real deployments

| Failure mode | Where seen | Mitigation used or recommended |
|---|---|---|
| Model drift, COP overestimation | [4] (4 COP refits), [1] (periodic recalibration) | Scheduled refits on recent data; residual monitoring; conformal or quantile margins [8] |
| Forecast error (cold snaps, clouds) | [5], [4], [20] | Conservative solar gain; comfort-violation budget [8]; soft constraints [19] |
| Fighting the unit's own controller | [4], [14], [9] | Plan energy, not setpoints; inner tracking loop; respect firmware start rules |
| Unexpected unit behaviour (start delay 60-120 min, shutdowns, DHW on 10 kW rod after compressor block) | [4] | Model start delay; never block the compressor while DHW may be called |
| Communication or optimiser outage | [19], [44] | Local fallback to the unit's own WC curve; detect stale data |
| Over-claiming from short tests | [1], [5] | At least 7 days per arm, ideally a month or more; weather normalisation; equal mass state at boundaries |
| Infeasibility under tight bounds | [19], [45] | Soft constraints with penalties |
| Comfort issues unrelated to control (air balance, sensors) | [6] | Fix hydraulics and sensors before blaming the controller |
| Bad identifiability in online learning | [7] | Physical parameter bounds; offline fits; excitation tests |
| Engineering effort | [6] (190 engineer-days), [1] | Reuse tools; keep model minimal |

The Ngenic CEO's slide [36] lists the practical enemies of residential MPC: a signal-to-noise ratio that is too small, non-linearities, forecast errors, physical-system limits, power tariffs, unplanned outages and human behaviour.

### 7. Slab and underfloor-specific evidence

- **Concrete floors make MPC both more useful and more dangerous.**
  - Useful: the floor stores heat, which allows load shifting [4][12][17].
  - Dangerous: slow response means a mistake made at noon shows up hours later.
  - The Danish concrete-floor house overheated on sunny days because of forecast errors [4]. The Ottawa glazed slab house overheated in January-February and over-cooled in March-May, and only about 71 % of days ran successfully [20].
  - The Swiss Solarhaus MPC throttled floor heating ahead of sunny spells; it reported better efficiency qualitatively, and simulated up to 20 % more renewable use [40].
- **Floor heating with an AWHP in Denmark:** savings peaked at 0.7-4 °C outdoor and turned into losses below about 0 °C [4]. That is the regime where heat pump capacity, COP and the lack of spare heat meet.
- **Hydronic UFH optimisation (DTI) [27]:**
  - MPC on telestat-controlled UFH lowered the required forward temperature by only 0.3-0.9 K but cut electricity 9-13 % in a 2-day simulation.
  - An ANN controller cut forward temperature by 0.7-1.5 K.
  - The authors estimate up to 25 % savings for poorly controlled installations with an SPF around 3.
- **Hierarchy for UFH:** the Aalborg design keeps local room PI loops and adds a top-level MPC that minimises supply temperature, letting room setpoints float inside a tolerance band [12]. For a single-zone slab with no room valves, this reduces to choosing the lowest flow temperature that keeps the room inside its band.

### 8. Domestic hot water (DHW) scheduling

- DHW priority interrupts space heating. In the Danish test, a compressor block made the unit heat DHW on its 10 kW rod, which is expensive even for a few minutes [4].
- MPC for a heat-pump water heater (Purdue, 20 MPC days) used a 2-node tank model, a constant COP of 3.5, a 24 h horizon at 5-min steps, and a solve time of about 0.06 s [22].
  - It pre-heated before forecast draws, which kept heat-pump-only mode comfortable; default heat-pump-only control produced cold showers.
  - Cost was about 23-28 % lower on time-of-use and hourly prices vs a standard heat-pump water heater.
  - On a flat rate it used about 5 % more energy than the hybrid baseline.
- Commercial practice: Havenwise heats DHW in the 01:00 cheap slot and only reheats after baths [41]. NIBE SPA has a separate "degree of impact" for hot water, 1-4 with default 2 [31]. Viessmann shifts DHW phases using forecast and price [38].

### 9. Commercial products: claims vs evidence

| Product | What it does (as documented) | Numbers | Evidence quality |
|---|---|---|---|
| Homely (GenGame) | Cloud thermal model; plans 24 h of flow-temperature blocks over Modbus, bypassing the unit's own WC (forum description) | Salford twin homes: 22 % annual heating-cost saving (fixed settings + flat tariff vs dynamic WC + time-of-use), 53 % with PV + battery [28]; two 24 h tests at 5-10 °C: about 20 % cost [29]; marketing up to 31 % | Lab, vendor-led; not in-situ |
| Havenwise | App/cloud optimiser on Vaillant/Mitsubishi; load-shifts to off-peak; OVO trial Oct 2025-Mar 2026 [35] | No published results found. Users report it skips starts when water is only a few K below target [41]; COP about 2.8 at ≤5 °C and about 2.1 at -2 to -4 °C on one Arotherm [42] | Forum anecdote |
| Passiv | ML heat-loss model + local forecast to hold the lowest workable flow temperature; tariff option | EST field trial Oct-Dec 2021: space-heating COP +17 % standalone, +25 % hybrid [30]; sample size not reported | Field, vendor-reported |
| tado Heat Pump Optimizer X | Manual heat-curve presets (Comfort, Standard, Moderate, Eco, Eco Plus) | Claimed about 4 %, 7 % and 11 % savings for Moderate, Eco and Eco Plus, with slower warm-up [32]; no learning or forecast described [33] | Manufacturer claim |
| NIBE Smart Price Adaption | Shifts consumption into the cheapest of the next 24 h prices via myUplink; separate impact settings for heating (1-10) and DHW (1-4) | No savings figures [31] | Manufacturer |
| Viessmann (ViCare) | Dynamic Assistant (forecast + price), PV-surplus priority, SG-Ready | Trade review: no efficiency gain, savings only from price; little benefit without a dynamic tariff [38] | Trade press |
| Octopus Cosy | Room "pods", 6 schedule slots per day, user-set boosts before cheap periods; WC | Fleet SCOP about 3.6; no predictive features described [34] | Manufacturer |
| Ngenic Tune (SE) | Self-learning, forecast + price | 50 of 500 customers, 12 months before/after: 23 % kWh (20 % without, 24 % with price control); no weather correction [36] | Vendor data |
| Neogrid PreHEAT (DK) | Cloud MPC; control via relay or outdoor-sensor manipulation; swarm aggregator respecting run-time limits | Claims 5-15 % heat pump energy saving; about 400 buildings [37] | Vendor claim |
| Quatt (NL) | Hybrid / all-electric; no control description on the website | "Up to 80 % lower bill" (hybrid), up to €2,300/yr; indicative, from real users [39] | Marketing |
| Mixergy (HPR) | ML demand prediction + combined DHW/buffer store; schedules runtime to cut short cycling | 15-40 % energy savings in simulations and a 20-home field trial vs fixed control [28] | Programme summary of vendor results |

The UK HPR programme flagged the lack of common integration standards as a key barrier: each third-party integration was bespoke and slow [28]. It also found that 43 % of 40 monitored Daikin systems had a fault within four weeks, including failed sterilisation cycles [28].

### 10. Open-source projects and tools

- **EMHASS thermal battery [45]:**
  - Linear-program/MILP scheduler. It treats a slab or water store as a battery with a Carnot COP (efficiency 0.4) at a given supply temperature, which affects COP only.
  - Soft comfort constraints; typically 30-min steps over a 24 h horizon.
  - Minimum modulation and cycling are not documented, so it would need extension for a heat pump whose minimum output exceeds load.
- **EPFL Kh-budget MPC on Home Assistant [8]:**
  - Python (CVXPY + PIQP quadratic program), adaptive ARX model, Open-Meteo forecast, Home Assistant as the I/O hub, minute-level flow-setpoint tracking.
  - The closest published blueprint to this house.
  - A "Kelvin-hour budget" lets the user set allowed discomfort in advance rather than tuning penalty weights.
- **RWTH DDMPC (Python, CasADi/Ipopt) [10]:** data-driven MPC framework used on the HiL bench.
- **Predheat [46]:** Home Assistant AppDaemon predictor of indoor temperature and energy for wet systems. Prediction only, no optimisation; the repo is archived and folded into Predbat.
- **Smart NIBE blueprint [47]:**
  - Supervisory heat-curve offset control over MQTT/Modbus with slew-rate limits and a degree-minutes guard; leaves the compressor to NIBE.
  - Look-ahead pre-heat before price spikes.
  - No results published.
- **OpenEnergyMonitor dynamic heat pump simulator [43]:** physics-based house, heat pump, minimum modulation and defrost model, useful for testing control ideas before deploying them.
- **BOPTEST** (used in [15][8]): its "bestest_hydronic_heat_pump" case is a 192 m² Brussels house with floor heating and a 15 kW modulating AWHP. It is a free, standard emulator for comparing candidate controllers.
- **Forum practice [44]:** a rolling 24 h energy budget split into chunks, delivered mostly in cheap slots with carry-over, with a WC thermostat as fallback.

### 11. Synthesis: when is MPC worth it vs a well-tuned WC curve?

MPC adds clear value when:
- the plant has hard discrete constraints the curve cannot handle (minimum output above load, DHW priority, backup heaters) [4][6][25];
- there is something to arbitrage, such as dynamic prices, a peak tariff or PV surplus [4][5][16];
- solar and internal gains are large relative to load (shoulder seasons, glazing) [5][10][20];
- the existing curve is set too high and nobody will tune it, in which case MPC or "dynamic WC" mostly acts as an automatic curve tuner [13][27][30].

MPC adds little (about 0-5 % energy) when the reference is already a low, well-tuned WC curve with a continuously modulating compressor and a flat tariff [5][14][12].

MPC can make things worse when:
- it optimises price on a flat-ish tariff [4][18];
- it pre-charges a slab aggressively in mild sunny weather [4][17][20];
- it fights firmware logic [4][9][14];
- it is judged on short tests [1][5].

## What this means for controlling this house

Confidence key: **H** = high (multiple consistent measured sources), **M** = medium (consistent lab/field evidence but different hardware, or my own physics inference from the owner's measured parameters), **L** = low (plausible, needs testing).

### A. The house's operating regimes (my arithmetic from the owner's measurements; M)

Inputs: heat loss coefficient H ≈ 0.14-0.20 kW/K, slab storage C ≈ 6.6 kWh/K, minimum output ≈ 3.75 kW, room at 22 °C. Load ≈ H × (22 - T_out), before solar and internal gains.

| T_out | Load (H = 0.14-0.20 kW/K) | Regime |
|---|---|---|
| +10 °C | 1.7-2.4 kW | Duty ≈ 45-65 % |
| +5 °C | 2.4-3.4 kW | Duty ≈ 65-90 % |
| 0 °C | 3.1-4.4 kW | Near continuous |
| -10 °C | 4.5-6.4 kW | Continuous, modulating |
| -20 °C | 5.9-8.4 kW | Near the top of a 9 kW unit |

- **Cycling regime.** The cycling regime runs from about 0 °C upwards, and higher when there is sun. In Lithuania that covers much of autumn, spring and the many humid -5 to +5 °C days, on the warm side of that band.
- **Time constant.** τ ≈ C/H ≈ 33-47 h, so a 24-48 h planning horizon is physically meaningful. This is comparable to the BOPTEST house (3 days), where 6 h was the shortest workable horizon [15].
- **Cycle length.** It depends on how much mass-temperature swing is allowed. Stored energy per run is E = 6.6 kWh × swing (K); on-time = E / (3.75 - load); off-time = E / load.

| Conditions | Allowed swing | On | Off | Starts/day |
|---|---|---|---|---|
| +10 °C, load 1.7 kW | 0.5 K | 1.6 h | 1.9 h | ~7 |
| +10 °C, load 1.7 kW | 1.0 K | 3.2 h | 3.9 h | ~3.4 |
| +5 °C, load 2.9 kW | 0.5 K | 3.9 h | 1.1 h | ~4.8 |
| +5 °C, load 2.9 kW | 1.0 K | 7.8 h | 2.3 h | ~2.4 |

These figures ignore solar gains and the room-slab lag. The room air will swing less than the slab mass.

Conclusion: with ±0.5 K of allowed mass swing (1 K total), mild-weather operation needs only about 2.5-3.5 runs per day. With ±0.25 K it needs about 5-7. Either way each run is far longer than the 15-20 min threshold where start losses become negligible [11]. Cycling itself need not be the efficiency problem.

### B. Where the losses probably are (M for mechanism, L for size)

- **High-power catch-up runs are probably the main efficiency loss.** At +2 °C the unit draws up to about 3 kW electric, which means it is running well above minimum output and at a 36-39 °C setpoint. The literature points to lower flow temperature and lower compressor speed as the main efficiency levers: 2-3 % COP per K [27]; -11 % electricity at -5 K supply and 46 vs 63 Hz [10].
  - Rough size: if mild-weather runs could be held near minimum output at about 4-6 K lower flow temperature, COP during those runs could improve by about 8-18 %.
  - This is an inference and must be measured.
- **The restart rule (setpoint ≥ outlet + 4 K) works against "gentle" control.** To start the unit, the setpoint must jump at least 4 K above the outlet temperature. If it stays there, the inverter's internal PI sees a large error and may ramp the compressor up. The HiL work shows this inner loop alone can move UFH SCOP by up to 18.5 % [11]. How the Gree firmware actually ramps is unknown; testing it is open question #1.
- **Interruptions and short runs (0.5 h) add wear.** Their energy cost is small if runs are at least 15-20 min [11], but the pattern indicates the setpoint layer and firmware are fighting each other.

### C. Candidate control architectures (in order of evidence and simplicity)

1. **A. Well-tuned WC curve + slow room trim + cycle governor** (baseline to beat; H for "good baseline", M for the governor).
   - The flow setpoint follows a low curve fitted to the house (lowest that holds 22 °C in steady state). Add a slow integral parallel shift on room error (time constant of hours, since τ ≈ 40 h).
   - In the cycling regime, a governor enforces minimum on and off times by setpoint manipulation.
   - Evidence that this captures most of the efficiency: [13][12][5][14][43].
2. **B. Predictive energy-budget scheduler ("slab as battery")** (M).
   - Every 15-60 min, forecast the next 24-36 h heat need: H × degree-hours, minus forecast solar and internal gains, minus or plus the current slab energy relative to target.
   - Deliver it as a few long blocks at or near minimum output, placed in the warmest hours (higher COP, fewer defrosts) and in PV surplus hours.
   - Each block has a minimum length (≥ 1.5-2 h) and a minimum gap (≥ 1 h). Comfort guards override the plan (start if room < 21.6 °C, stop if > 22.6 °C).
   - Evidence: the hierarchical hourly heat budget [4], energy-tracking inner loop [8], forum energy budget [44], daytime COP gain [5].
3. **C. Full economic mixed-integer MPC + inner energy-tracking loop** (M for feasibility, L for extra benefit over B).
   - State: [T_room, T_slab]. Decisions: on/off and heat rate per 15-30 min step over 24-36 h. Re-solve every 15-30 min.
   - Constraints: on/off binary; heat between minimum output and maximum available at T_out; minimum up and down times; a cost per start; DHW blocks as mutually exclusive events.
   - COP(T_out, T_flow) as a piecewise-linear table fitted from the house's own data.
   - Objective: electricity at the import price, with PV surplus valued at the export price; plus a soft comfort penalty or Kh budget [8]; plus a terminal value on slab energy [23].
   - Inner loop as in [8]: when "on", kick the setpoint to outlet + ≥4 K to start, then step it to the flow temperature needed for the planned heat rate; when "off", hold the setpoint below the outlet.
   - Expected extra over B: a few percent in kWh, more in cost if prices vary. Risk: model upkeep and firmware interaction [4][14].

**My recommendation:** build A and B first, compare them over several weeks, and add C only if B's schedule is visibly sub-optimal (for example, PV surplus wasted, or DHW collisions). The literature gives C over a good A/B about 0-5 % in energy [5][14], while its failure modes are well documented [4][9][14].

### D. Concrete rules and parameter values to test

| # | Rule | Starting value | Confidence | Evidence |
|---|---|---|---|---|
| 1 | Objective | Minimise electricity kWh, not price, unless a real dynamic or peak tariff exists. Value PV surplus at its export price, not zero. | H | [4][18][12][38] |
| 2 | Comfort band | 22.0 ± 0.5 °C normally; allow up to +1 K only when PV surplus and the forecast justify it; cap with a Kh budget rather than a weight. | M | [8][5] |
| 3 | Minimum run | ≥ 60 min, aim for 2-4 h blocks in mild weather. | M | [11] (≥15-20 min to remove start losses); 60 min+ and the 2-4 h aim are my wear margin |
| 4 | Minimum off-time | ≥ 60 min. | M/L | [4] (min off-time); exact value is a choice |
| 5 | Starts per day | Target ≤ 3-6 in mild weather; log and alarm above about 8. | M | [11]; arithmetic in section A |
| 6 | Flow setpoint while running | The lowest that delivers about minimum output into the slab; never request catch-up power above about 1.5× minimum output unless the room is below its band. | M | [10][27] |
| 7 | Setpoint ramps | ≤ 1 K per 5-10 min after a start kick; bounded steps. | M | [8][12] |
| 8 | Block placement | Warmest hours of the day (typically 11:00-17:00) and PV surplus. Avoid 00:00-06:00 in mild humid weather unless needed. | M | [5][6] |
| 9 | Forecast use | Outdoor temperature and GHI, 24-48 h ahead (e.g. Open-Meteo). Use a conservative solar-gain coefficient on cloudy-forecast days so a missing sun is not a surprise. | M | [8][4][20][16] |
| 10 | Model | 2-state RC (room, slab), fitted on the last 2-4 weeks and refitted weekly. Watch one-step error (target RMSE ≤ about 0.3-0.5 K). Physical bounds on parameters. | M | [6][4][8][7] |
| 11 | COP model | COP(T_out, T_flow) table from the house's own kWh_el and kWh_th per run (or a Carnot fraction fitted to them). Refit monthly or when error drifts. | M | [4][45][27] |
| 12 | Horizon and step | 24-36 h with a terminal slab-energy value; 15-30 min plan step; 1-5 min inner loop. | M | [15][23][8] |
| 13 | DHW | Schedule in the warmest or PV hours, not in the first hour of a space-heating block. Run legionella with the electric heater only in PV surplus. Never block the compressor at times when DHW could be requested. | M | [4][22] |
| 14 | Fallback | If Home Assistant or the planner is stale for more than 30-60 min, revert to the Versati's internal WC curve (set low). | H | [44][19][4] |
| 15 | Continuous regime (T_out ≲ 0 °C) | Plain low WC with slow trim; let the inverter modulate continuously; MPC only pre-charges ahead of cold snaps. | M | [5][12][4] (losses below 0 °C) |

### E. Unit settings to investigate (L: needs testing on the Versati)

- **Restart hysteresis (delta_heat_temp_set, currently 4).** It mainly changes start counts, not SCOP [11]. With an external planner that kicks starts on purpose, two designs are possible:
  - keep about 4 K and use explicit kick-then-lower;
  - raise it (6-8 K) so the firmware cannot restart on its own during planned off-blocks.
  - On the real heat pump in [11], 6 K vs 8 K was the tipping point between cycling and continuous running. Test both settings for a week each.
- **Capacity or frequency limits.** Check whether the unit exposes a Modbus register to cap compressor frequency or power. Direct capacity control beat flow-setpoint control on cycling and comfort [9]. If it exists, the inner loop could request "minimum output" directly instead of inferring it from the flow setpoint.
- **Water-pump mode during off-blocks.** Check whether outlet temperature reads meaningfully when the compressor is off. This decides whether the "outlet + 4 K" kick is predictable.

### F. What to avoid (H/M)

- Price-only optimisation on a flat tariff, which raises kWh [4][18].
- Aggressive midday slab pre-charging stacked on sun, which overheats the room [4][20][40].
- Blocking the compressor or spoofing sensors as the primary actuator [4].
- Large, long-held setpoint steps that drive the inverter to high power (hypothesis, test) [10][11].
- Judging any new controller on 1-3 days of data [1][5].
- Model-free RL or unconstrained online learning [15][7].
- Assuming forecasts deliver energy savings; they mostly deliver comfort and PV use [12][13][16].

### G. How to test (M)

- **Arms.** Run A vs B (and later C) in alternating blocks of at least 7 days across one heating season. Ideally pair blocks with similar outdoor temperatures (±1-2 K mean) and similar irradiance [1][4][5].
- **Metrics:**
  - kWh_el per heating degree-day;
  - kWh_th / kWh_el per run and per day;
  - starts per day and the run-length histogram;
  - mean flow temperature while running;
  - share of runs above about 1.5× minimum output;
  - comfort in Kh outside 21.5-22.5 °C;
  - DHW collisions per week;
  - PV self-consumption by the heat pump.
- **Expected outcome:**
  - B vs current: fewer starts and lower running flow temperature. Size unknown, plausibly 5-20 % kWh in mild months (L).
  - B vs A: a few percent, mostly from PV and warmest-hour placement (L-M).
  - C vs B: about 0-5 % kWh (L) [5][14].
- **Before deploying:** fit the house model and try candidates in simulation first (BOPTEST-style or the OpenEnergyMonitor simulator [43][15]).

## Contradictions and open questions

### Contradictions in the evidence

1. **Size of MPC savings.** Reviews of field tests report 22-30 % energy and 16-25 % cost savings [1][2]. Long tests against a well-tuned curve report about 4-5 % energy [5][14]. The gap is mostly baseline quality and test length [1][5], not a real disagreement; both are reported here, not averaged.
2. **Energy vs cost.** Energy-objective MPCs cut kWh [5][10][27]. Price-objective MPCs raised kWh: +9.5 % [4], COP 7.6 to 6.0 [18], and higher mean water temperature [12]. Which one this house gets depends on the objective chosen.
3. **Flow-setpoint actuation.** HiL tests found it produces many starts [9]. The EPFL field system writes flow setpoints every minute and reports no such issue, but it published no start counts [8]. How the Versati's firmware reacts is the deciding unknown.
4. **Weather forecasts.** They are credited for MPC savings in HiL work [10][16]. Simulations show little or no energy benefit from forecasts, only comfort [12][13].
5. **Cycling vs efficiency.** The owner's intuition is that on/off cycling is inefficient. The evidence says start losses are small for runs of at least 15 min, and that hysteresis changes cycles far more than SCOP [11]. Cycling still matters for wear (12 % more cycles ≈ up to 15 % less life, cited in [11]) and as a symptom of poor run execution.
6. **Setback vs continuous.** A community simulation found a gentle setback cheapest on a fixed tariff (radiator house) [43]. The Purdue field MPC lowered night setpoints to save energy [6]. The thermal-mass bias argument [1] favours steady operation. My expectation (not a finding) is that with a slab time constant of about 40 h, setbacks mostly shift energy rather than save it. This is unresolved for this house.
7. **Commercial claims vs independent data.**
   - Homely: 20-31 % (vendor), against a lab-only 22 % [28][29].
   - Ngenic: 20-23 % (vendor before/after) [36].
   - Neogrid: 5-15 % (claim) [37].
   - Havenwise: no results; anecdotes conflict [41][42].
   - Passiv: COP +17 % (EST, sample not stated) [30].
   - None is a weather-normalised, controlled, long field comparison against a tuned WC curve.
8. **Purdue applicability.** Purdue's savings came largely from avoiding resistance backup [6], which does not apply to a Versati that does not use its backup heater for space heating.

### Open questions for this house

1. How does the Gree Versati's inverter respond to setpoint - outlet error after a start: does a larger error push frequency and power up, and how fast? This decides whether "kick then lower" works.
2. Is there a Modbus capacity or frequency limit, a minimum-run/anti-short-cycle timer, or a fixed stop overshoot in the Versati firmware? (Not researched here; see the manual-focused notes.)
3. What is the measured COP map of this unit, COP(T_out, T_flow, output), including defrost losses in humid 0 to +5 °C weather at minimum vs high output?
4. What flow temperature does the slab need to absorb about 3.75 kW at typical slab temperatures? This sets the floor for "low flow temperature" in cycling blocks.
5. What is the effective storage accessible within the comfort band: is 6.6 kWh/K per K of slab mean temperature, and how much does the room swing per K of slab swing?
6. What tariff does the owner actually have (flat, two-zone or spot), and what is the export price? This decides objective 1 in table D.
7. How large are solar gains through the glazing relative to load in March-April and September-October? These are the months where MPC/PV gains were largest in [5] and overheating risks largest in [4][20].
8. Unverified items:
   - the heatpumpmonitor 282-system SCOP comparison by control type [48] (page blocked);
   - exact numbers of Lee et al. 2019 [25] and Fischer et al. 2017 [24] (abstract or snippet level only);
   - the BOPTEST white/grey/black-box vs well-tuned rule-based figures (4.9-8.4 %), seen only as a citation in [8].
9. Quatt's control algorithm and Havenwise's published trial outcomes were not found. Lithuanian-language sources were not searched because the shared search budget was exhausted.

## Sources

1. Lessons learned from field demonstrations of model predictive control and reinforcement learning for residential and commercial HVAC: A review - Khabbazi, Pergantis, Reyes Premer, Papageorgiou, Lee, Braun, Henze, Kircher (arXiv 2503.05022v6) - 2025 - https://arxiv.org/html/2503.05022v6 - paper (review of field data) - Filtered field-test averages (22 % energy, 16 % cost residential), short-test bias, model and interface statistics, heat pump study table, cost and labour data.
2. From theory to practice: A critical review of model predictive control field implementations in the built environment - Saloux et al., Applied Energy 393:126091 (summary page) - 2025 - https://kuzha.github.io/publication/2025-05-20-paper - paper (review) - Raw average savings across field MPC (30/25/25/26/17 %), mean test length 41 days.
3. All you need to know about model predictive control for buildings - Drgoňa et al., Annual Reviews in Control 50 (LBL record) - 2020 - https://eta-publications.lbl.gov/bibcite/reference/34370 - paper (review) - MPC still early in practice; need for standardised assessment.
4. Long-term experimental study of price responsive predictive control in a real occupied single-family house with heat pump - Thorsteinsson, Kalaee, Vogler-Finck, Stærmose, Katic, Bendtsen, Applied Energy 347 (arXiv 2303.16289) - 2023 - https://ar5iv.labs.arxiv.org/html/2303.16289 - field data - Closest analogue (7 kW AWHP, concrete UFH); mixed-integer MPC; cost -2 to -17 % but electricity +9.5 %; failure modes of input manipulation; model refits.
5. Experimental Long-Term Investigation of Model Predictive Heat Pump Control in Residential Buildings with Photovoltaic Power Generation - Kuboth, Weith, Heberle, Welzl, Brüggemann, Energies 13:6016 - 2020 - https://epub.uni-bayreuth.de/5598/1/energies-13-06016.pdf - lab (twin rigs, real ASHP, real weather) - 125-day result vs a minimised heating curve: -4.1 % el, +5.4 % COP, -9 % cost; short vs long test contrast; monthly pattern.
6. Field demonstration of predictive heating control for an all-electric house in a cold climate - Pergantis et al. (arXiv 2402.07032) - 2024 - https://ar5iv.labs.arxiv.org/html/2402.07032 - field data - Occupied-house MPC: -19 % heating energy, -38 % backup; 1-state model adequate; mechanisms; 190 engineer-days.
7. Comparative Field Deployment of Reinforcement Learning and Model Predictive Control for Residential HVAC - Purdue team (arXiv 2510.01475) - 2025 - https://arxiv.org/html/2510.01475v1 - field data - MPC about 20 %, RL about 22 % vs constant setpoint; RL comfort worse; negative solar coefficient from online learning.
8. User-specified Kelvin-hour budgets within model predictive control for energy-efficient buildings: Simulation and field demonstration - Shi and Jones, EPFL (arXiv 2609.06698) - 2026 - https://arxiv.org/pdf/2609.06698 - field data + simulation - Home Assistant + Mitsubishi Ecodan UFH architecture; heat-power plan with a minute-level flow-setpoint tracking loop; ARX refit hourly; Kh budget; -31.9 % energy in simulation.
9. Maximizing operational efficiency of heat pumps with Model Predictive Control: An experimental case study for residential application - Göbel, Stoffel, Will, Vering, Müller (14th IEA Heat Pump Conference, paper 805) - 2023 - https://heatpumpingtechnologies.org/?p=58995 - lab (HiL, abstract) - Flow-setpoint MPC lowest energy but many starts; compressor-speed MPC fewer cycles; up to -20.25 %.
10. Outperforming the Heating Curve with Data-Driven Model Predictive Control - Will, Beckschulte, Göbel, Mersch, Vering, Müller, HPT Magazine 43(2) - 2025 - https://heatpumpingtechnologies.org/articles/heat-pumping-technologies-magazine-vol-43-no-2-2025/outperforming-the-heating-curve-with-data-driven-model-predictive-control/ - lab (HiL) - -11 % el, +3 % SCOP, -5 K supply, 46 vs 63 Hz, perfect-forecast caveat.
11. The impact of controller settings in heat pumps: Numerical findings and experimental verification - Göbel, Waiz, Vering, Müller (ECOS 2023) - 2023 - https://proceedings.com/content/069/069564-0075open.pdf - lab (HiL) + simulation - Inner-loop PI and hysteresis effects (SCOP up to 18.5 % UFH; +300 % avoidable starts); start-loss thresholds (≥15-20 min); 6 K vs 8 K tipping point; compressor-life citation.
12. Economic COP Optimization of a Heat Pump with Hierarchical Model Predictive Control - Tahersima, Stoustrup, Rasmussen, Meybodi (IEEE CDC) - 2012 - https://vbn.aau.dk/ws/files/73867242/cdc_2012.pdf - paper (simulation) - UFH hierarchy; about 13 % from feedback vs feed-forward; forecasts improve comfort about 55 % but not COP; price shifting vs efficiency conflict.
13. Modellbaserad styrning av värmesystem baserat på prognostiserat väder (Model-based control of heating systems based on weather forecasts) - Daniel Olsson, Chalmers licentiate thesis - 2014 - https://publications.lib.chalmers.se/records/fulltext/209907/209907.pdf - paper (simulation) - Forecast control about 7-9 % (about 10 kWh/m²), mostly from supply-temperature adaptation, not forecasts.
14. Heat pump controls to exploit the energy flexibility of building thermal loads - Thibault Péan, PhD thesis UPC (portal record) - 2020 - https://portalinvestigacio.uib.es/documentos/6381691318a84b178fea9bc4 - lab (semi-virtual) + simulation - Near-optimal reference: MPC about 5 %, rule-based 0; mixed-integer MPC; conflicts with the local controller.
15. Comparison of Optimal Control Techniques for Building Energy Management - Arroyo, Spiessens, Helsen, Frontiers in Built Environment - 2022 - https://frontiersin.org/articles/10.3389/fbuil.2022.849754/full - paper (simulation, BOPTEST) - Floor-heated AWHP house; MPC up to 27.2 % cost and 90.8 % discomfort savings; 6 h minimum horizon; RL failures.
16. Impact of the Weather Forecast Quality on a MPC-driven Heat Pump Heating System - Hummel, Betzold, Dentel, TH Nürnberg (CLIMA 2022) - 2022 - https://proceedings.open.tudelft.nl/clima2022/article/view/152 - lab (HiL) - PV self-consumption +38.9 % MPC vs heating curve; forecast-quality penalty 4.6-11.1 %.
17. Simulation, implementation and monitoring of heat pump load shifting using a predictive controller - Allison, Cowie, Galloway, Hand, Kelly, Stephen, Energy Conversion and Management 150 - 2017 - https://strathprints.strath.ac.uk/60566/ - field data - UFH pre-charging; comfort OK, but heat pump performance under load shifting was poor and the immersion supplied most heat.
18. MPC of a heat pump in a low-energy non-residential building (Hochschule Offenburg repository record, docId 10493; year not captured) - Hochschule Offenburg - n.d. (about 2024-25) - https://opus.hs-offenburg.de/frontdoor/index/index/docId/10493 - field data - Cost -40 % but COP 7.6 to 6.0; no standard heat pump interface.
19. Challenges of implementing economic model predictive control strategy for buildings interacting with smart energy systems - Zong, Böning, Santos, You, Hu, Han, Applied Thermal Engineering 114 - 2017 - https://backend.orbit.dtu.dk/ws/files/127571167/1_s2.0_S1359431116334871_main.pdf - field data (electric radiators) - Practical challenges: data, communication failures, soft constraints, Kalman state estimation.
20. Long-term implementation of a model predictive controller for a hydronic floor heating and cooling system in a highly glazed house in Canada - Brown and Beausoleil-Morrison, Applied Energy 349 (abstract) - 2023 - https://ideas.repec.org/a/eee/appene/v349y2023ics0306261923010413.html - field data - 182 days; about 71 % of days successful; GHI forecasting critical; seasonal over- and under-heating.
21. Experimental test of a black-box economic model predictive control for residential space heating - Knudsen, Georges, Skeie, Petersen, Applied Energy 298 (abstract) - 2021 - https://ideas.repec.org/a/eee/appene/v298y2021ics0306261921006498.html - field data - Minimal sensors and black-box model sufficient for demand response with thermal mass.
22. Model predictive control lowers barriers to adoption of heat-pump water heaters: A field study - Reyes Premer et al. (arXiv 2510.12955) - 2025 - https://arxiv.org/html/2510.12955 - field data - DHW MPC: forecast pre-heating, simple tank model, 24 h horizon, 0.06 s solves; cost -23 to -28 % on TOU and hourly prices.
23. An optimal home energy management system for modulating heat pumps and photovoltaic systems - Langer and Volling, TU Berlin (arXiv 2009.02349) - 2020 - https://arxiv.org/pdf/2009.02349 - paper (simulation) - Mixed-integer scheduling with UFH, DHW, PV and battery; 24 h horizon end effects; omits minimum run time, part load and cycling losses.
24. Comparison of control approaches for variable speed air source heat pumps considering time variable electricity prices and PV - Fischer, Bernhardt, Madani, Wittwer, Applied Energy 204 (abstract) - 2017 - https://ideas.repec.org/a/eee/appene/v204y2017icp93-105.html - paper (simulation) - Four rule-based controllers vs convex MPC. Savings numbers (MPC 6-16 %, rule-based 2-4 %) seen only in a search snippet.
25. Mixed-Integer Model Predictive Control of Variable-Speed Heat Pumps - Lee, Gupta, Kircher, Zhang, Energy and Buildings 198 (citation page; content via abstract snippet) - 2019 - https://energy.mae.cornell.edu/2019/07/23/mixed-integer-model-predictive-control-of-variable-speed-heat-pumps - paper (simulation) - Dead zone below minimum speed; binary on/off to avoid short bursts and cycling.
26. Model predictive control of heating in a low energy single-family house - Nielsen, Larsen, Thorsteinsson, Bendtsen (AAU) - 2023 - https://vbn.aau.dk/da/publications/model-predictive-control-of-heating-in-a-low-energy-single-family - paper (simulation) - Zone-level MPC under a higher-level heat reference for an 11-zone UFH house with AWHP.
27. OPSYS / Under floor heating and heat pump optimization, main report - Danish Technological Institute et al. - 2017 - https://www.teknologisk.dk/_/media/72043_OPSYS%20main%20report.pdf - paper (simulation + test rig) - 1 K forward temperature ≈ 2-3 % COP; only about 15 % of heat pumps perform as expected; MPC -9 to -13 % el with COP only +2.1-2.3 %.
28. Smart and Flexible Heat Pumps: Learnings from the Heat Pump Ready programme - DESNZ / Carbon Trust - 2025 - https://assets.publishing.service.gov.uk/media/6978d7f1d6ab92f1d3a4d6cd/thematic-report-smart-innovative-heat-pumps-hpr.pdf - field data / lab (mixed, programme summary) - Homely 22 % (53 % with PV + battery, lab), Mixergy 15-40 %, Kensa ≤20 % (HiL), Wondrwall 61 % (7 homes); integration-standards barrier; 43 % fault rate (Switchee).
29. Homely Energy test (Energy House 2.0, Smart Meters > Smart Homes lab) - University of Salford Energy House Labs - n.d. - https://energyhouselabs.salford.ac.uk/?p=9241 - lab (vendor-commissioned) - Two 24 h periods at 5-10 °C; about 20 % cost saving on a dynamic tariff.
30. Passiv smart controls improve heat pump performance by up to 25 %, finds assessment - Solar Power Portal - 2023 - https://www.solarpowerportal.co.uk/solar-projects/passiv-smart-controls-improve-heat-pump-performance-by-up-to-25-finds-assessment - field data (vendor-reported EST trial) - Space-heating COP +17 % standalone, +25 % hybrid; lowest-workable flow temperature via ML and forecasts.
31. NIBE F370 installer manual, Smart price adaption (menu 4.1) - NIBE (via manualslib) - n.d. - https://www.manualslib.com/manual/1590978/Nibe-F370.html?page=51 - manufacturer - Shifts consumption to the cheapest hours of the next 24 h; impact settings; requirements.
32. Heat curve / Heating Optimization (help article) - tado - n.d. - https://help.tado.com/en/articles/10248018 - manufacturer - Preset savings claims about 4, 7 and 11 %.
33. tado heat curve optimisation feature launch (press release) - tado - n.d. - https://www.tado.com/en/press/heat-curve-optimisation-feature-launch - manufacturer - Manual presets; supported brands; no learning or forecast described.
34. Cosy controls (blog) - Octopus Energy - n.d. - https://octopus.energy/blog/cosy-controls/ - manufacturer - Schedules and manual boosts; fleet SCOP about 3.6; no predictive features described.
35. OVO and Havenwise launch heat pump trial - The Eco Experts - 2025 - https://www.theecoexperts.co.uk/news/ovo-havenwise-heat-pump-trial - blog/press - Trial scope (Oct 2025-Mar 2026, Vaillant/Mitsubishi); no savings data.
36. Ngenic presentation (Björn Berg, CEO), Energiforsk - Ngenic - n.d. (about 2023) - https://energiforsk.se/media/33868/7-bjo-rn-berg-ngenic.pdf - manufacturer - 50 of 500 customers before/after: 23 % kWh (20 % without price control); list of practical obstacles.
37. PreHEAT for Heat Pumps (IEA HPT Annex 56 case sheet) - Neogrid Technologies / DTI - n.d. - https://www.dti.dk/_/media/87788%5F1%5F2%20IoT%20Annex%2056%20case%20DK%20%2D%20Neogrid.pdf - manufacturer - Cloud MPC via relay or outdoor-sensor spoofing; 5-15 % claim; about 400 buildings; run-time-aware aggregation.
38. Schlaue Wärmepumpe (Viessmann Vitocal smart features review) - 42watt - 2026 - https://42watt.de/magazin/schlaue-warmepumpe - blog (trade press) - Viessmann Dynamic Assistant and PV-surplus features shift timing only; savings from price, not efficiency.
39. Quatt homepage - Quatt - n.d. - https://www.quatt.io/ - manufacturer - Savings marketing claims; no control description.
40. Dank Wetterbericht Energie und Heizkosten sparen (press release) - Hochschule Luzern - 2017 - https://www.hslu.ch/en/lucerne-university-of-applied-sciences-and-arts/about-us/media/medienmitteilungen/2017/10/25/dank-wetterbericht-energie-und-heizkosten-sparen - field data (press) - 3-month MPC in Solarhaus; throttles slow floor heating ahead of sun; simulated up to +20 % renewables.
41. Display optimisers in heatpumpmonitor.org - OpenEnergyMonitor community - 2025 - https://community.openenergymonitor.org/t/display-optimisers-in-heatpumpmonitor-org/29013 - forum - Homely and Havenwise user experiences; start-cost-aware behaviour; oversized heat pumps limit gains.
42. Experience with a 7kW Vaillant Arotherm - OpenEnergyMonitor community - 2025 - https://community.openenergymonitor.org/t/experience-with-a-7kw-vaillant-arotherm/27714 - forum - Havenwise user COP figures; disputed defrost hypothesis.
43. Dynamic heat pump simulator (discussion) - OpenEnergyMonitor community (Trystan Lea et al.) - 2025 - https://community.openenergymonitor.org/t/dynamic-heat-pump-simulator/28315?page=2 - forum / simulation - +37 % electricity for poorly configured vs optimised continuous; setback vs continuous results; minimum-modulation modelling.
44. Predictive heating control or monitoring - BuildHub forum - n.d. - https://forum.buildhub.org.uk/topic/46136-predictive-heating-control-or-monitoring - forum - DIY energy-budget control for thick-screed UFH with WC fallback.
45. Thermal battery for heat pump optimization - EMHASS documentation - n.d. - https://emhass.readthedocs.io/en/latest/thermal_battery.html - blog (open-source docs) - Slab-as-battery formulation; Carnot COP; no documented minimum modulation or cycling constraints.
46. Predheat - springfall2008 (GitHub) - n.d. - https://github.com/springfall2008/predheat - blog (open-source) - Prediction-only Home Assistant tool; archived; merged into Predbat.
47. Smart NIBE - Ultra Adaptive Heat Curve Control (MQTT, Spot Prices) - Home Assistant community - 2026 - https://community.home-assistant.io/t/smart-nibe-ultra-adaptive-heat-curve-control-mqtt-spot-prices/975863 - forum (open-source) - Supervisory offset control with slew limits and degree-minutes guard; no results.
48. Thesis on heatpumpmonitor.org dataset (282 systems) - University of Padua (page blocked, 403; search snippet only) - n.d. - https://thesis.unipd.it/handle/20.500.12608/107878 - paper (unverified) - Median SCOP 3.97 (pure WC) vs 3.48 (significant room influence); oversizing 1.56-1.65. Not read in full; treat as unverified.
