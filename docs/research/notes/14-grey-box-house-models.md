# Grey-box thermal models and system identification for houses with UFH

Research note 14 of the heat pump efficiency sweep. Scope: RC (grey-box) model structures for houses with slab underfloor heating (UFH), how to identify them from ordinary operating data, how to model sun, internal gains and ventilation, sensor pitfalls, what model order to use for control, how to validate, and how to estimate heat pump heat output without a flow meter. It ends with what this means for the Lithuanian house: slab UFH, 9 kW Gree Versati, minimum output above the mild-weather load, flow setpoint written over Modbus, and a restart only when setpoint minus outlet is at least about 4 K.

**Method note (read first).** The shared web-search budget for this workflow run was used up before this researcher started: all 4 search attempts returned "budget used up". No search engine results were used. All sources below were fetched directly from URLs that are known stable addresses (DOI landing pages, IEA EBC report PDFs, arXiv IDs, DTU and Chalmers repositories), or that were listed in sibling notes 05, 06 and 08 in `docs/research/notes/`. 36 sources were read, most in full text: PDFs were downloaded and their text extracted locally. Non-English coverage is thinner than requested: one Swedish thesis [15] and one Lithuanian thesis [35]. No German, Polish or Dutch forum threads on this narrow topic could be reached without search. The repository code was not read. Notes 05, 06 and 08 were read only for source URLs and for the Versati Modbus register list.

---

## Summary

1. **Use a 2-state model (room + slab) for control, maybe 3 states. Do not use 4-5.** In the IEA EBC Annex 58 simulation study, 1st and 2nd order models were adequate for short-term prediction (minutes to about a day) in floor-heated houses. For floor heating, overfitting already appeared at 3rd order when the only measured output was indoor air temperature [3]. Field MPC papers mostly use 1-3 states per zone [10]. The closest field analogue (7 kW air-to-water heat pump, concrete UFH, Denmark) used exactly 2 states, room and floor [7]. Confidence: high.
2. **Choose and validate models on multi-step prediction error, not one-step.** In Annex 71's MPC exercise on a UFH house with an air-to-water heat pump, the ANN and one ARX model had the best one-step R² but the worst 12-step-ahead accuracy. MPCs built on them had the highest electricity cost. The spread between models was about 7 % in cost, or about 24 % of the achievable MPC saving [4]. Validate at 6-24 h horizons.
3. **Forward selection with likelihood-ratio tests is the standard way to choose model order.** Bacher & Madsen grew models from Ti to TiTeThTsAe (5 states) on 6 days of 5-min PRBS data from a 120 m² test house [1]. Most of the gain came in the first two steps: log-likelihood rose from 2483 (Ti) to 3911 (TiTh) and 5517 (TiTeTh), then to 5612 (TiTeThTs) [1]. Their data had deliberately excited heating (PRBS). A house under normal thermostat control carries far less information, so the defensible order is lower [3][5].
4. **Typical parameters for small houses, as measured:**
   - FlexHouse, 120 m², light timber [1]: total C about 4.4 kWh/K; envelope R about 5.3 K/kW (H about 0.19 kW/K); slow time constant 18-20 h, fast ones 0.01-0.8 h.
   - Purdue all-electric house [8]: 1-state C about 6.5 kWh/K, R_out 2.04 K/kW.
   - BOPTEST 192 m² floor-heated heat pump house [13]: building time constant about 3 days.
   - This house (6.6 kWh/K slab, H 0.14-0.20 kW/K): slab-only time constant C/H of about 33-47 h. The real slow time constant is longer once walls and furniture are counted.
5. **Heat input is the term most worth getting right.** Annex 71 found discrepancies of up to 100 % in derived heat loss when simplified heat-input assumptions are used, such as rated efficiency or gross electricity before the generator. Including domestic hot water (DHW) in the heat input overestimates the heat loss coefficient (HTC). Best results came from heat measured after the generator and after the space-heating/DHW split [5]. Tank cycles and the legionella immersion heater must be removed from the space-heating heat input.
6. **Internal gains and ventilation shift identified parameters by tens of percent.** Including appliance and lighting electricity changed estimated HTC by up to 55 %, and modelling mechanical ventilation explicitly changed it by up to 30 % [5]. Measured household electricity used as a gains input improved model accuracy [3]. Occupant metabolic gains were negligible [5].
7. **Use the PV array as the solar sensor.** Global horizontal irradiance used directly gave clearly higher RMSE than irradiance converted to vertical façades. Annex 58 explicitly suggests PV output as a cheap local solar input [3]. A constant solar aperture (gA) is usually enough for HTC estimation. Spline or time-of-day gA curves improve prediction in houses with large glazing [5][2]. Bünning et al. used 9 time-of-day solar bins in a physics-informed ARMAX [11].
8. **The slab self-regulates, so heat input is not exogenous.** With a fixed supply temperature, an extra gain in the room (sun, people) reduces the heat the pipes deliver. In Karlsson's reference floor this cut the steady-state temperature rise by about 70 % (γ = -0.73) [14]. The model must therefore couple slab and room both ways and take water temperature or delivered heat as input. It should not assume a fixed heat flux.
9. **Data length and refits.** Low-order models trained on 3-5 weeks of data perform well enough for control (cited by [8]). Thorsteinsson et al. refit their 2-state UFH model on 35 days, and later 10 days [7]. Shi & Jones refit an ARX model hourly in a Home Assistant + Ecodan UFH deployment [9]. The heat pump COP model also had to be refit when the operating style changed [7].
10. **Physics structure beats generic machine learning on small data.** A physics-informed ARMAX (30-min step, 3-7 lags, coefficients constrained positive) had lower 1-h prediction error than random forests and input-convex neural networks at every training size from 1 week up [11]. The neural network needed about 4 weeks before it was usable [11].
11. **Estimating heat output without a flow meter:**
    - Delta-T with an assumed flow is fragile at minimum output. At about 27 L/min (the flow implied by the 9.5 kW rating at a 5 K ΔT [29]), 3.7 kW gives only about 2 K ΔT. A 0.5 K sensor error then means about 25 % error in heat [25].
    - A Carnot-fraction model using measured condensing and evaporating temperatures, multiplied by measured electricity, is more robust. Practical Carnot fractions are 0.45-0.55 on good units and can drop to about 0.35 in frosty weather [26][27]. Typical offsets are condensing about 1-3 K above flow and evaporating about 5-8 K below outdoor air, growing with load [25].
    - The Versati exposes discharge pressure (as °C), suction, coil, water in/out and compressor Hz over Modbus (register list via note 08 [30]). These are enough for this method.
12. **Sensor pitfalls named by the guidelines:** sun striking thermometers, shading of solar sensors, low resolution, point-sampled power instead of energy counters, time-zone and synchronisation errors, and averaging across on/off transitions [2]. Room sensors in housings have 10-30 min time constants, against under 1 min for duct sensors [15]. Treat the room sensor as a filtered state, not ground truth.
13. **Even good statistical methods on in-use houses miss.** In Annex 71's blind test of five occupied UK homes, HTC estimates deviated from co-heating reference values by up to almost 50 %. Methods agreed with each other more than with the truth, and dynamic methods varied more between analysts than static ones [5]. Use identified parameters for control, where errors are corrected online, rather than trusting them as physical truth.

---

## Detailed findings

### 1. What a grey-box model is and why it suits control

- A grey-box model is a continuous-time stochastic state-space model: dT = (A·T + B·U)dt + dW, observed as Y(tk) = C·T(tk) + e(tk). The states are lumped temperatures, A and B are built from physical R and C values, and dW is process noise [2]. Parameters are estimated by maximum likelihood, with a Kalman filter computing the likelihood. CTSM-R is the DTU reference tool [1][2][33].
- Because it is formulated in continuous time, sampling can be irregular. This matters for Home Assistant data, which is logged on change rather than on a fixed clock [2].
- For linear time-invariant models the number of states equals the number of time constants. It also equals the autoregressive order of the equivalent ARX model [2]. A 2-state RC model and an ARX(2) model therefore carry the same dynamics. The RC version keeps physical meaning and lets you add priors.
- An RC network is one important special case of a linear grey-box model [2]. Nonlinear terms such as wind × ΔT, radiative T⁴ or a COP that depends on temperature can be added in the same framework [2].
- For model comparison [2]:
  - Nested models are compared with likelihood-ratio tests.
  - Non-nested models are compared with AIC when the model is for forecasting or control.
  - BIC is preferred when the goal is the physical parameters.

### 2. Model structures: the Bacher & Madsen family

Bacher & Madsen (2011) is the reference paper on model selection [1]. Facts from the full text:

- **Building:** FlexHouse at Risø DTU, single storey of about 7.5 × 16 m (about 120 m²), timber walls, on piles [1].
- **Data:** February-April 2009. Six days of 5-min averages: indoor temperature (first principal component of several room sensors), outdoor air, global horizontal irradiance, and electric heater power driven by a PRBS sequence to excite the relevant time constants [1].
- **Candidate states** [1]:
  - Ti: room air plus fast mass.
  - Tm: interior thermal medium.
  - Th: heater.
  - Ts: a sensor state, because thermometers have their own lag.
  - Te: building envelope.
  - Ae: solar absorbed directly in the envelope.
  - Ria: an extra resistance from interior to ambient.
- **Forward selection path** (log-likelihood, number of parameters) [1]:
  - Ti: 2482.6, 6 parameters.
  - Iteration 1, best of TiTe, TiTm, TiTs, TiTh: TiTh, 3911.1, 10 parameters.
  - Iteration 2: TiTeTh, 5517.1, 14 parameters.
  - Iteration 3: TiTeThTs, 5612.4, 18 parameters.
  - Iteration 4: TiTeThTsAe, 5614.6, 19 parameters (p = 0.011).
  - Iteration 5: no significant extension (p = 0.68).
  - Final model: TiTeThTsAe [1].
- **Residual evidence** [1]:
  - Ti and TiTh left clearly autocorrelated residuals.
  - TiTeTh was already "close to white noise".
  - Later steps gave only slight improvements.
  - The largest remaining errors came at high solar irradiance, so the authors point at the solar input path as the place to improve [1].
- **Parameters** [1]:
  - Total C was 3.99-4.36 kWh/K for the three larger models, 1.67-2.07 kWh/K for the two small ones.
  - Envelope R was 5.28-5.40 K/kW for every model, so H ≈ 0.19 kW/K. HLC is robust to model order even when C is not.
  - Effective window area Aw was 5.6-7.9 m².
  - Time constants for TiTeThTsAe: 0.010, 0.105, 0.79 and 19.3 h.
  - The authors warn that the small capacities (Ci, Ch, Cs) cannot be given exact physical meaning. Only their sum (about 1.03-1.08 kWh/K) was stable [1].
- **Lesson for a slab-UFH house:** the "heater" state Th in FlexHouse was a set of electric heaters. In a UFH house the analogous state is the slab or screed, and it holds most of the active mass. Annex 58 says explicitly that for a house with concrete floors and light walls the main mass should be placed "inside" (coupled to the room), not in the walls [2].

### 3. Model order versus purpose: the Annex 58 and 71 evidence

- **Annex 58 ST4b** forward-selected 1st to 4th order models on detailed simulations of insulated and uninsulated houses with radiators and with floor heating [3]:
  - 1st order: everything in one capacity.
  - 2nd: separates air/furniture from heavy structure.
  - 3rd: adds interior walls.
  - 4th: adds the ground floor coupled to the ground.
- **Its conclusions** [3]:
  - (a) For short-term prediction (minutes to a day, the control use case), 1st and 2nd order models are adequate for floor heating, and 2nd order for radiators.
  - (b) Long-term simulation needs higher order.
  - (c) With indoor temperature as the only observation, overfitting begins at 4th order for radiators and already at 3rd order for floor heating. Adding heat-flux sensors fixes it.
  - Without such sensors, the advice is to limit complexity or fix parameters from physical priors [3].
- **Annex 71 ST2** repeats this. Robust 3rd-4th order identification needed heat-flux sensors and PRBS excitation, while for predictions up to a day "less stringent requirements" apply. ARX and grey-box models both predicted day-ahead indoor temperature acceptably, but may drift in long simulations [4].
- **Annex 71 MPC common exercise** (Holzkirchen twin house O5: UFH with air-to-water heat pump, emulated in Modelica) [4]:
  - Models compared: 7-state state-space, ARX, a 2-state grey-box, a 1-state state-space, and an ANN.
  - The best MPC (7-state SS) cut cost 22.7 % against a tuned rule-based controller.
  - The rule-based controller switched the heat pump on 2 h before the end of night setback to compensate for UFH inertia.
  - The ranking by 12-step-ahead error matched the ranking of MPC cost. The ranking by one-step error did not [4].
- **Arroyo et al. (BOPTEST)**, on a 192 m² single-zone floor-heated house with a 15 kW modulating air-to-water heat pump, forward-selected a 5-state RC model with 20 parameters [13]:
  - Trained on 2 weeks and validated on 2 weeks of emulator data.
  - Fitted outputs: operative temperature, condenser heat and electrical power.
  - Estimated building time constant about 3.03 days.
  - Emulator data is noise-free and richer than real data, which is why 5 states were identifiable there.
- **Khabbazi et al.**, reviewing field MPC demos: two-thirds used linear models, mostly RC networks with 1-3 states per zone, at 5-60 min steps and 2-24 h horizons [10]. The authors note that model prediction errors are often of the same size as the 10-20 % savings being claimed [10].
- **Pergantis et al.** deliberately used a 1-state model with a constant deep-mass temperature in a Purdue house (forced air) [8]:
  - Trained on 30 days of hourly data.
  - One-step RMSE 0.41 °C.
  - The authors say a Kalman filter and more states would be needed for "more active thermal mass, such as radiant floors" [8].

### 4. UFH-specific structure

- **Thorsteinsson et al.** (Danish single-family house, about 7 kW air-to-water heat pump, concrete UFH, 2-year field MPC) used [7]:
  - C_r·dT_r/dt = U_r(T_f − T_r) + U_a(T_a − T_r) + Q_s
  - C_f·dT_f/dt = U_r(T_r − T_f) + Q_HP
  - Q_s = g1·I_global + g2·I_direct, using a cloud-adjusted forecast. Household and occupant gains are deliberately left out.
  - Floor temperature is unmeasured and estimated by a linear Kalman filter every 5 min. Observability holds for any U_r, U_a > 0.
  - Heat input Q_HP came from a central heat meter.
  - The model was refit in January 2023 using 35 days and later 10 days of history.
  - Sunny-day overheating was traced to unreliable cloud forecasts [7].
- **Tahersima et al.** (AAU) used 3 masses per room (air, concrete floor, water in pipes), with supply temperature and flow as inputs [16]:
  - The water node is driven by c_w·q·(T_s − T_f).
  - The water and floor states are Kalman-estimated [16].
  - This is the natural structure when the controlled variable is water temperature rather than heat.
- **Kuboth et al.** (Bayreuth twin test rigs with real air-to-water heat pumps) used a 4-equation state-space model (heating water, floor heating system, zone) with an explicit-Euler 300 s step and no state observer [20].
- **Shi & Jones** (EPFL; Home Assistant + Mitsubishi Ecodan UFH, occupied house) [9]:
  - Used an adaptive ARX with n_a = n_b = 6, refit hourly, output operative temperature, input total UFH heat Q.
  - The predictor state was [T_room, T_floor] from Z-Wave air and floor sensors.
  - Heat came from the Ecodan's own delivered-heat estimate via its interface, not from a heat meter.
  - Heat pump electricity could not be used as the input because it also contained DHW [9].
  - A supervisory loop updates the flow setpoint every minute so that cumulative heat over each 15-min slot tracks the MPC's heat target [9].
- **Floor-to-room coupling magnitude** [17]:
  - The combined convective and radiative coefficient for a heated floor is about 11 W/m²K.
  - EN 1264 gives q = 8.92·(θ_floor − θ_room)^1.1 W/m².
  - Floor surface limits are 29 °C in occupied zones and 35 °C at the perimeter. Maximum output is about 99 W/m² (occupied zone) and 165 W/m² (perimeter) at 20 °C room [17].
  - For 150 m² of active floor, the floor-to-room conductance is therefore roughly 1.6-1.7 kW/K. This is about 10× the house's envelope H. Room temperature will track the slab surface closely.
- **Self-regulation** [14]:
  - Karlsson's Chalmers thesis shows that under feed-forward (fixed) supply temperature, a gain in the room shifts pipe heat flux the other way.
  - The self-regulation factor γ was -0.73 for the reference floor, cutting the steady-state temperature rise from a gain by about 70 %.
  - The effect is stronger with low building losses, thin floor covering, pipes near the surface, tight spacing and high flow [14].
  - Karlsson also stresses a real initial delay: the heat front takes time to conduct from the pipe depth to the surface. This limits how short the control period can be [14].
- **TABS laboratory data** (Gwerder et al.): thick-slab time constants of 9.9 h (charging side) and 100 h (slow) [21]. Residential screeds are thinner and faster, but slower than air.
- **Thermal mass magnitudes** [18][19]:
  - Johra et al. classify whole-building effective inertia as light 30-45, medium 50-70 and heavy 90-110 Wh/K per m² of floor. Furniture and indoor content add a non-negligible share, and should be included in light-structure models [18].
  - van Leeuwen et al. model a Dutch low-energy living room with a floor of about 514 kg/m² (hollow-core concrete plus screed) [19].
- **Lithuanian evidence** [35]:
  - Valionis (KTU MSc, 2022) simulated wet UFH with 65 mm screed in COMSOL.
  - Pulsed flow raised heat flux density by about 5.8 % but output by only about 1.2 %, because screed mass and conductivity dominate.
  - Pipe spacing was the strongest lever on UFH inertia [35].

### 5. Solar gain modelling

- **Basic form:** Φ_sol = gA·I, where gA = g-value × effective collecting area. In Bacher & Madsen it is called Aw, the effective window area, about 5.6-7.9 m² for FlexHouse [1][2].
- **The four approaches Annex 71 compared** [5]:
  - (1) Ignore solar gains.
  - (2) Constant gA on global irradiance.
  - (3) Constant gA per cardinal direction on vertical irradiance.
  - (4) B-spline gA as a function of sun position.
- **Annex 71 results** [5]:
  - Including solar in any form clearly beats ignoring it for HTC.
  - Approach 2 is "in most cases sufficient" for HTC.
  - For prediction, spline gA was better in two of four houses (Gainsborough and Loughborough). Constant gA was enough for the others [5].
- **Decomposition and transposition:**
  - When only global horizontal irradiance (GHI) is available, a separation model (Erbs, Perez) splits GHI into beam and diffuse using the clearness index kt (GHI over extraterrestrial irradiance) and solar position. Perez transposition then gives irradiance per façade [5][31].
  - Annex 71 used Perez per ISO 52010-1, ERA5 reanalysis for missing variables, and a ground albedo of about 0.14 in winter, rising with snow cover from ERA5-Land [5].
  - Snow albedo matters in Lithuania. Fresh snow can multiply the reflected component several times (inference from the albedo formula in [5]; not measured here).
- **Using global horizontal directly costs accuracy.** RMSE clearly rises with GHI as input, and pre-processing to vertical façades ("solar processor") recovers most of it. PV output is suggested as a cost-effective local solar signal [3].
- **Time-of-day solar bins** are a cheap alternative to geometry: 9 one-hot periods with positive coefficients [11]. A caveat: if training data has no summer, the bins for summer sun positions are unidentifiable and variance rises [11].
- **Lags differ by path.** Olsson cites a Swedish evaluation in which a model with a single building time constant for everything overstated inertia. Solar through windows reaches the air on a different, faster path than outdoor temperature does through the envelope [15]. Bacher & Madsen's Ae state (solar absorbed in the envelope) and their observation that residuals peak in sunshine point the same way [1].
- **Sol-air temperature** folds radiation on opaque surfaces into an equivalent outdoor temperature: T_sol-air = T_o + (a·I − ΔQ_ir)/h_o [32]. Annex 71 suggests sky temperature from ERA5 for the long-wave term [5]. For a well-insulated house this is second order.

### 6. Internal gains and occupants

- Including lighting and appliance electricity changed HTC by up to 55 %. Occupant metabolic gains had negligible effect [5].
- Measured household electricity as an input improved model accuracy compared with no occupant information (Annex 58 scenarios D vs F) [3].
- Thorsteinsson et al. left appliances out for technical and privacy reasons. Their model then absorbs those gains into other parameters [7].
- Pergantis et al. did not model gains physically. They inferred a lumped exogenous heat Q_e by inverting the dynamics and predicted it with a support vector machine from outdoor temperature, irradiance, wind, hour and weekday [8].
- A practical rule from Annex 71: if only one room sensor exists, it is usually the living room. Night zones are typically about 2 K colder, so a synthetic second temperature can be built [5]. A UFH house showed much less stratification than a radiator house in the Holzkirchen twin houses [5].

### 7. Ventilation with heat recovery

- **Heat loss formula** [5]: Φ_vent = c_a·G_a·(1 − η_HR)·(θ_e − θ_i), or directly c_a·G_a·(θ_sup − θ_i) when supply temperature is measured.
- **Details that change the effective η** [5]:
  - Fans add about 0.5-1 °C to supply air.
  - Duct losses and short-circuiting at the façade.
  - Electric pre- and post-heaters for frost protection must be counted in the energy balance.
  - Units in unheated spaces behave differently.
- **Size of the effect:** modelling ventilation explicitly changed HTC by up to 30 % in the case studies [5]. One MVHR there had a theoretical efficiency of 84 % [5].
- **Implication:** an MVHR whose bypass, frost-protection or boost mode changes over time makes the "constant H" assumption non-stationary. Its supply temperature or mode should be logged as an input.

### 8. Sensors, quantization and data handling

- **Annex 58 checklist** of phenomena that bias identification [2]:
  - Overheating from sun in thermostat-controlled periods.
  - Sun hitting temperature sensors.
  - Shading of irradiance sensors at low sun.
  - Saturation and low resolution.
  - Power measured as point samples instead of energy counters.
  - Cumulative counters with poor resolution after differencing.
  - Time synchronisation and time zone. Check by plotting measured irradiance against computed sun elevation.
  - Averaging across a switching signal. Average only within on or within off periods [2].
  - Subsampling and aliasing.
  - Use the same filter for all signals [2].
- **Sampling interval** [2]: grey-box models of buildings should sample under 1 hour because room air has high-frequency variation. When the goal is control, pick the interval so that a 2nd-order model fits [2]. Field MPC used 5-60 min [10].
- **Sensor lag** [15]: room thermostat sensors in housings have time constants of about 10-30 min, against under 1 min for duct sensors. Bacher & Madsen gave the sensor its own state (Ts) because it significantly improved likelihood (+95 in log-likelihood) [1].
- **Sensor resolution in heat pump data:**
  - LG R32 pressure-derived temperatures have about 0.5 °C resolution, and one outdoor sensor read about 2 °C high [25].
  - The Gree Versati Modbus document states 1 °C accuracy, while community configs scale to 0.1 °C (via note 08 [30]).
  - Quantization of 0.1-0.5 K in room temperature is comparable to the 1-step change in a well-insulated house. This favours fitting on multi-step error and on longer horizons [4].
- **Quality checklist** for an estimated model [2]:
  - Parameters significant (t-tests).
  - No parameter correlations near ±1. If found, fix one parameter or tie two together.
  - White residuals (ACF and cumulated periodogram).
  - No cross-correlation between residuals and any input; if there is, add that input.
  - Physically plausible values.

### 9. Identification data from normal operation

- **Excitation:**
  - PRBS heat inputs are ideal [1][2] but not acceptable in an occupied house.
  - The Annex 71 MPC exercise used a random on/off sequence with 70 % / 30 % bias halves to widen the temperature range [4].
  - In normal operation the heat pump's own cycling at mild outdoor temperatures (runs and pauses of hours) is a natural square-wave excitation of the slab. Mild weather data is therefore informative for the slab dynamics.
- **Feedback problem:** under thermostatic control the heating power is itself a controller output. It is correlated with gains and weather, which biases open-loop identification [4]. Annex 71 notes that for a well-insulated house the heating profile is "highly intermittent and highly sensitive" to occupants [4].
- **Data length:**
  - 3-5 weeks for low-order control models (cited in [8]).
  - 2 weeks of training (emulator) for a 5-state model [13].
  - 10-35 days in the field [7].
  - 5 days initial plus hourly refit in an adaptive ARX [9].
  - Winter data identifies better because of the large indoor-outdoor ΔT and strong heating excitation [3].
- **DHW separation:** if one generator serves space heating and DHW, DHW must be removed from the heat input. Wrong split assumptions push HTC either way [5]. Bacher et al. (2016) give a non-parametric method to separate DHW spikes (cited in [5]).

### 10. Multi-step validation practice

- One-step-ahead fit is easy to achieve and misleading. The Annex 71 exercise showed that the model with the best one-step R² produced the worst MPC [4]. Its recommendation: train and evaluate on multi-step prediction error (MSPE) over the control horizon [4].
- Shi & Jones calibrated constraint-tightening margins per horizon step from the 98 % quantile of open-loop residuals computed with forecast weather [9]. This bakes forecast error into validation.
- **Practical validation set:**
  - Simulate open loop for 6, 12 and 24 h from many start times, using forecast and actual weather.
  - Report RMSE and bias per horizon, separately for sunny and overcast days and for mild and cold days.
  - Bacher & Madsen saw errors concentrated at high irradiance [1].
  - Thorsteinsson et al. saw sunny-day overheating [7].

### 11. Heat pump heat output without a flow meter

Options, from most to least robust for this house:

**A. Carnot-fraction model with measured refrigerant temperatures and measured electricity.**
- Q = COP·P_el, with COP = η_C·T_cond/(T_cond − T_evap) (kelvin).
- Practical η_C:
  - Rule of thumb 0.5 [26].
  - Measured 0.45-0.55 on a Samsung 8 kW at 40 °C flow and 1-2 °C outdoor. It fell to about 0.35 at -1.5 °C, sensitive to humidity and frost [27].
  - EMHASS default range 0.40-0.50, and 0.41 back-calculated from COP 4.5 at A7/W35 [24].
  - The Modelica library defaults to 0.3 when the leaving water and source temperatures are used rather than refrigerant temperatures [23].
- If refrigerant temperatures are not measured, use offsets [25]:
  - Condensing ≈ flow + 1-3 K (Arotherm 1.1 K at 30 rps, 5.5 K at 50 rps in DHW).
  - Evaporating ≈ outdoor − 5-8 K.
  - Both offsets grow with load.
- Thorsteinsson et al. fitted a richer form, COP = k/P + (k0/P + k1 + k2·P)·COP_Carnot (R² 0.92). It overestimated efficiency once the MPC changed the operating pattern, and had to be refit [7]. Dynamic operation (starts, defrost) is not captured by steady maps [7].
- The Versati exposes discharge pressure (saturation °C ≈ condensing), suction temperature, defrost-coil temperature, gas and liquid pipe temperatures, outdoor temperature and set/actual compressor Hz (words 117-143, via note 08 [30]). That is enough to compute T_cond directly and approximate T_evap.

**B. Compressor-map (refrigerant mass flow) method.**
- Refrigerant-side models compute refrigerant mass flow from displacement × speed × suction density, then condenser heat from the enthalpy difference [23].
- These need compressor displacement, volumetric and isentropic efficiency, and suction pressure. Gree does not publish these. Calibration "to manufacturer performance data" is the usual route [23][22].
- Polynomial or bilinear maps of capacity and COP against outdoor and supply temperature, per inverter frequency, are standard in seasonal models [22].
- For this unit the map would have to be built from the Gree catalogue points (9.5 kW, 2.07 kW input at A7/W35; 9.5 kW, 2.64 kW at A7/W45 [29]) plus self-measured points. It is weaker than option A.

**C. Delta-T × assumed flow.**
- 9.5 kW rated with the standard 5 K test ΔT implies about 0.45 kg/s, or about 27 L/min (assumption: EN 14511 standard rating ΔT of 5 K; [29] gives capacity only).
- At the 3.7 kW minimum the ΔT is only about 2 K. A 0.5 K error in either sensor is then ±25 % in heat.
- Users comparing Modbus-derived heat to an external flow meter saw about 2 kW instantaneous discrepancies, partly from non-simultaneous Modbus updates, and estimated ±10 % overall [27].
- The Versati pump is variable speed (note 08), so flow is not constant.
- Use this only after calibrating flow once against A, or with a clip-on ultrasonic meter.

**D. Building energy balance as a cross-check.**
- Over days, delivered heat ≈ H·(T_i − T_e) − gains + C·ΔT_i.
- Regressing daily electricity on degree-days gives H/COP_mean.
- Annex 71 shows gross input before the generator and rated-efficiency assumptions bias HTC upward [5]. Use this only as a sanity check on A.

**What practitioners actually have.** Mitsubishi exposes a delivered-heat estimate [9]. heatpumpmonitor.org sorts systems by metering quality ("MID metered" heat meters) because manufacturer estimates are not trusted for headline numbers [36].

### 12. Tooling seen

- CTSM-R (DTU): maximum-likelihood continuous-time stochastic models with an R interface [33].
- RC_BuildingSimulator: a Python 5R1C model citing Madsen & Holst, Bacher & Madsen and Sonderegger [34].
- Grey-Box Toolbox: KU Leuven, used in [13].
- EMHASS: Home Assistant optimizer with a 1-node slab "thermal battery" [24]:
  - Default capacity: 2400 kg/m³ × 0.88 kJ/kgK × volume. For example, 18 m³ ≈ 10.6 kWh/K.
  - Optional first-order lag of 1-3 h between heat pump output and slab.
  - Carnot-fraction COP.
  - Calibration target: under 20 % deviation over a past week [24].
  - It has no explicit room state, so room comfort is only proxied.
- OpenEnergyMonitor dynamic heat pump simulator: a 3-stage RC building plus a Carnot COP model. The author reproduced a monitored system visually, with no error metric published [28].
- Physics-constrained neural networks (Drgoňa et al.): trained on 10 days, generalised over 20 days in a 20-zone office [12]. This is a research-grade alternative, not needed for one zone.

---

## What this means for controlling this house

The house numbers used below come from the task brief: H = 0.14-0.20 kW/K, slab C ≈ 6.6 kWh/K, minimum output 3.7-3.8 kW, mild-weather load about 1.7 kW at +10 °C, and a restart only when setpoint − outlet ≥ 4 K. The steady loads below are envelope only, before solar and internal gains.

### A. Recommended model (confidence: high for structure, medium for numbers)

**States**
- T_i: room air, furniture and light internal mass. Expect C_i ≈ 0.5-2 kWh/K. Bacher & Madsen's small capacities summed to about 1 kWh/K for 120 m² [1].
- T_s: slab or screed with pipes. Fix C_s as a prior near 6.6 kWh/K, or estimate it with a tight prior.
- Optional T_e: envelope or deep structure. Add it only if residuals at 12-24 h horizons show slow drift.
- Do not add a 4th state: with room temperature as the only observation it overfits for floor heating [3].

**Couplings**
- K_si (slab to room): prior from EN 1264, about 11 W/m²K × active floor area (≈ 1.5-2 kW/K for 140-180 m²) [17].
- H (room to outdoor): 0.14-0.20 kW/K, including MVHR losses.
- K_ws (water to slab): unknown. It is the key parameter for choosing flow temperature; see C below.

**Inputs**
- Heat into the slab while the compressor runs, Q_HP, estimated by method A in section 11.
- Outdoor temperature.
- Solar: PV production as the irradiance proxy [3], plus time-of-day bins [11]; or Perez transposition onto the actual window façades [5].
- Internal gains: household electricity minus heat pump, immersion heater and any EV charging [3][5].
- MVHR supply temperature or mode, when it changes.

**Observation and estimation**
- Room temperature, with a sensor lag state if the thermostat sits in a housing [1][15].
- Kalman filter for T_s, as in [7].

**Method**
- Fit on 3-5 weeks of winter data [8][7], at a 5-15 min step.
- Choose structure by forward selection with likelihood-ratio tests [1][2].
- Judge the model on 6/12/24 h open-loop RMSE [4].
- Refit weekly on a rolling 3-5 week window.
- Freeze C_s near its prior if it correlates near ±1 with K_si or H [2].

### B. Numbers the model already implies (confidence: medium; arithmetic on the owner's measured values)

- **Slab-only time constant:** C_s/H ≈ 6.6/0.17 ≈ 39 h (range 33-47 h). The house stores about a day and a half of loss per kelvin of slab.
- **Steady envelope loss at 22 °C:**
  - About 1.7-2.4 kW at +10 °C.
  - About 2.8-4.0 kW at +2 °C.
  - About 5.9-8.4 kW at -20 °C.
  - So the 3.7 kW minimum output only matches the load continuously around +2 to -5 °C, depending on gains.
- **Slab warming rate:** at +10 °C, running at 3.7 kW charges a net ≈ 2 kW into 6.6 kWh/K, about 0.30 K/h. Off, the slab falls at about 1.7/6.6 ≈ 0.26 K/h (matches note 08).
- **Cycle sizing from a comfort band** (worked example, not validated):
  - If room temperature tracks slab temperature closely (K_si ≈ 10 × H), a ±0.3 K room band allows about 0.6-0.7 K of slab swing.
  - That swing stores 0.65 × 6.6 ≈ 4.3 kWh per cycle.
  - At +10 °C this means about a 2.1 h run and about 2.5 h off: roughly 5 starts/day, each run ≥ 2 h.
  - At +5 °C (≈ 2.9 kW load) the run lasts about 5.5 h and the pause about 1.5 h: about 3 starts/day.
  - This is the "energy packet" logic: decide kWh per cycle from the allowed band, not from a flow setpoint.
- **Self-regulation** [14]: with T_s around 23-24 °C and the room at 22 °C, a sunny afternoon raising the room 1 K roughly halves floor output on its own. Pre-emptively skipping a run on sunny forecast days is worth more in a slab house than in a radiator house. Late catch-up runs after a sunny day are what produce the high-flow-temperature episodes.

### C. Using the model to pick the lowest workable flow temperature (confidence: medium)

- **Estimate K_ws.** During steady minimum-output runs, K_ws ≈ Q_HP/(T_w,mean − T_s), where T_w,mean = (flow + return)/2 from words 125/127 and T_s comes from the Kalman filter. Repeat over many runs and look at the scatter.
- **Compute the minimum flow.** The flow temperature needed to deliver the 3.7 kW minimum is then T_s + 3.7/K_ws + ΔT_water/2.
- **Example** (hypothetical K_ws = 1 kW/K, slab at 24 °C): about 24 + 3.7 + 1 ≈ 28.7 °C.
- **The test:** if the identified K_ws gives needed flow temperatures near 29-31 °C in mild weather, the observed 31-36 °C setpoints (peaks 39 °C) are higher than physics requires. That would put the excess temperature down to catch-up behaviour and the 4 K restart margin, not to the slab. Each 1 K of flow temperature costs about 2-3 % COP (cited in note 06 from the DTI OPSYS report).
- **Restart margin:** the unit restarts only when setpoint − outlet ≥ 4 K. With the outlet sensor cooling toward plant-room temperature while idle, a model of outlet temperature during idle is needed to know when a start command can be issued at a low setpoint. Log word 125 during off periods and fit a 1-state decay.
- **Power cap:** a start triggered by a +4 K setpoint step makes the firmware's proportional-on-LWT logic choose high compressor frequency (note 08). Pair model-chosen starts with the power-limit register (word 43, note 08), so the model's assumed 3.7-4 kW actually happens.

### D. Heat output estimation for this unit (confidence: medium-high on method, low on accuracy until checked)

- **Primary: method A.** Use T_cond from discharge pressure (word 124) and T_evap from the defrost-coil or suction reading plus offset, then Q = η_C·COP_Carnot·P_el. Start with η_C = 0.45, then fit η_C as a function of compressor Hz and outdoor humidity.
- **Cross-check with method C** only after one flow calibration. Note that ΔT at minimum output is about 2 K [29][27].
- **Exclude** DHW cycles (word 117 = 6, 3-way valve coil 178), defrost (coil 86) and immersion heating (coil 173) from the space-heating heat input [5].

### E. What to avoid

- Calling a 4-5 state model "better" because it fits 1-step better [4][3].
- Using global horizontal irradiance unprocessed, or ignoring sun, in a house with 15 kW of PV and likely large south glazing [3][5].
- Using total heat pump electricity, which includes DHW and legionella runs, as heating input [5][9].
- Identifying only on cold-weather data. Mild-weather cycling carries the slab dynamics, and cold data carries H [3].
- Trusting an identified H to better than ±20-50 % as a physical number [5]. For control it only needs to predict well over 24 h.

### Testable predictions

1. A 2-state (T_i, T_s) model fitted on 4 winter weeks predicts room temperature 12 h ahead with RMSE ≤ 0.3-0.4 K. A 3rd state reduces 24 h RMSE by less than 0.1 K.
2. Adding PV power as a solar input cuts sunny-day 12 h error by more than adding a 3rd state does.
3. Identified K_ws implies a required flow of 28-32 °C at minimum output in +5…+10 °C weather. Supply setpoints above that are avoidable.
4. Energy-packet control (kWh per cycle from the allowed slab swing, delivered at minimum power and lowest workable flow) yields at most about 5 starts/day at +10 °C, with runs of at least 2 h, and lower mean run flow temperature than today.

---

## Contradictions and open questions

- **Model order:**
  - Bacher & Madsen selected 5 states [1], and Arroyo et al. 5 states [13].
  - Annex 58 says 1-2 states for floor heating and warns about overfitting at 3 [3]. Pergantis used 1 [8]. Thorsteinsson used 2 [7].
  - The resolution is data richness. PRBS-excited test houses [1] and noise-free emulators [13] support more states than an occupied house under normal control [3][5]. Not a real contradiction, but do not copy 5-state structures to field data.
- **Annex 71 MPC exercise:** a 7-state black-box state-space model gave the best MPC [4], which seems to contradict the "low order is enough" message. It was identified on emulator data with a designed random excitation, and black-box states are not physically constrained.
- **Carnot fraction:** forum values of 0.45-0.55 [26][27] and the EMHASS value of 0.41 [24] against the Modelica default of 0.3 [23]. These are partly different definitions: refrigerant temperatures versus water and air temperatures. Always state which temperatures you use.
- **Solar sophistication:** Annex 71 found no clear HTC gain from spline gA in most cases [5], yet spline gA helped prediction in 2 of 4 houses [5], and Bacher & Madsen's main residual was solar [1]. For control (prediction), solar detail matters more than for HTC.
- **Self-regulation vs controlled heat input:** Karlsson's 70 % self-regulation assumes a fixed supply temperature [14]. Under heat-based control (fixed kWh per cycle), the slab's self-regulation partly disappears. The model must say which input is fixed.
- **Open questions:**
  - The Versati's real water flow rate and pump control. Is the flow fixed per mode? (Note 08 suggests a variable-speed pump, and a minimum of about 12 L/min, unverified.)
  - Whether word 124 (discharge pressure as °C) is a true saturation temperature and at what resolution.
  - K_ws for this slab (pipe depth, spacing, covering) is unknown and has to be identified.
  - Whether the Komfovent unit's bypass or frost modes change effective H during the season.
  - No source found that quantifies refrigerant-side heat estimation error against a heat meter for a residential air-to-water heat pump. The forum thread asking for exactly this has no answer [25].
  - Not reached without search: Madsen & Holst (1995), Reynders et al. (2014), Brastein et al. (2018), Lee & Zhang (2021, minimal-hardware identification of residential heat pumps), Blum et al. (2019, envelope model setup for MPC), and the "internal method" refrigerant-side field measurement literature (Tran, Rivière et al.). These are worth reading in a follow-up with a search budget.

---

## Sources

1. Identifying suitable models for the heat dynamics of buildings - P. Bacher, H. Madsen (DTU), Energy and Buildings 43(7):1511-1522 - 2011 - https://orbit.dtu.dk/en/publications/identifying-suitable-models-for-the-heat-dynamics-of-buildings (accepted manuscript PDF: https://backend.orbit.dtu.dk/ws/files/126769045/modelselection09.pdf) - paper (field test building, PRBS) - Forward-selection/likelihood-ratio procedure, TiTeThTsAe result, log-likelihood table, R/C/Aw estimates and time constants.
2. IEA EBC Annex 58 Subtask 3 part 2: Thermal performance characterisation using time series data - statistical guidelines - H. Madsen, P. Bacher, G. Bauwens, A.-H. Deconinck, G. Reynders, S. Roels, E. Himpe, G. Lethé - 2016 - https://www.iea-ebc.org/Data/publications/EBC_Annex_58_Final_Report_ST3b.pdf - paper (guideline) - Grey-box formulation, data pitfalls (sun on sensors, resolution, sync, averaging), sampling-time rules, validation checklist, AIC/BIC/LR tests, gA-curve options, where to place mass.
3. IEA EBC Annex 58 Subtask 4b: Towards a characterisation of buildings based on in situ testing and smart meter readings - Annex 58 participants (KU Leuven et al.) - 2016 - https://www.iea-ebc.org/Data/publications/EBC_Annex_58_Final_Report_ST4b.pdf - paper (simulation study) - 1st/2nd order adequate for floor heating short-term; overfitting from 3rd order with Ti only; GHI vs vertical solar RMSE; PV output as solar proxy; household electricity as gains input.
4. IEA EBC Annex 71 Subtask 2: Building behaviour identification - Annex 71 participants (KU Leuven et al.) - 2021 - https://www.iea-ebc.org/Data/publications/EBC_Annex71-ST2-Building_behaviour_identification.pdf - paper (common exercises, emulator) - One-step vs multi-step error ranking, MPC on UFH + air-to-water heat pump twin house, 22.7 % vs rule-based, 7 % cost spread between models, intermittency of heating in efficient houses.
5. IEA EBC Annex 71 Subtask 3: Physical parameter identification - Annex 71 participants - 2021 - https://www.iea-ebc.org/Data/publications/EBC_Annex71-ST3-Physical_parameter_identification.pdf - paper (field case studies + blind test) - Four solar approaches; heat input errors up to 100 %; ventilation ±30 %; appliance gains ±55 %; MVHR formula; Perez/ERA5/albedo; deviations up to almost 50 % in the blind test.
6. IEA EBC Annex 58 and Annex 71 project pages - IEA EBC - 2016/2022 - https://www.iea-ebc.org/projects/project?AnnexID=58 and https://www.iea-ebc.org/projects/project?AnnexID=71 - paper (project summaries) - Scope, report index.
7. Long-term experimental study of price responsive predictive control in a real occupied single-family house with heat pump - S. Thorsteinsson et al., Applied Energy 347 (arXiv 2303.16289) - 2023 - https://ar5iv.labs.arxiv.org/html/2303.16289 - field data - 2-state room/floor model, Kalman filter, solar g1/g2 terms, heat meter input, 35/10-day refits, COP model refits, sunny-day overheating.
8. Field demonstration of predictive heating control for an all-electric house in a cold climate - E. Pergantis et al. (Purdue) (arXiv 2402.07032) - 2024 - https://ar5iv.labs.arxiv.org/html/2402.07032 - field data - 1-state model (C ≈ 6.5 kWh/K, R_out 2.04 K/kW), 30 days training, 0.41 °C 1-step RMSE, lumped exogenous gain via SVM, 3-5 week rule.
9. User-specified Kelvin-hour budgets within model predictive control for energy-efficient buildings - J. Shi, C. N. Jones (EPFL) (arXiv 2609.06698) - 2026 - https://arxiv.org/html/2609.06698v1 - field data + simulation - Home Assistant + Ecodan UFH; ARX(6,6) refit hourly; heat from Ecodan interface; DHW contamination of electricity; minute-level flow-setpoint loop tracking a heat target; residual-quantile tightening.
10. Lessons learned from field demonstrations of MPC and RL for residential and commercial HVAC: a review - Khabbazi et al. (arXiv 2503.05022v6) - 2025 - https://arxiv.org/html/2503.05022v6 - paper (review of field data) - Two-thirds linear models; RC 1-3 states per zone; 5-60 min steps; model error comparable to claimed savings.
11. Physics-informed linear regression is competitive with two Machine Learning methods in residential building MPC - F. Bünning et al. (ETH/Empa), Applied Energy 310 (arXiv 2110.15911) - 2022 - https://ar5iv.labs.arxiv.org/html/2110.15911 - field data + simulation - ARMAX with positive coefficients, 9 time-of-day solar bins, 30 min step; lowest error at all training sizes; NN needs ~4 weeks; 26-49 % savings in NEST UMAR.
12. Physics-constrained deep learning of multi-zone building thermal dynamics - J. Drgoňa, A. Tuor, V. Chandan, D. Vrabie (arXiv 2011.05987) - 2020 - https://arxiv.org/abs/2011.05987 - paper (abstract only) - 10 days training, 20 days generalisation, 20-zone office.
13. Comparison of optimal control techniques for building energy management - J. Arroyo, F. Spiessens, L. Helsen, Frontiers in Built Environment - 2022 - https://frontiersin.org/articles/10.3389/fbuil.2022.849754/full - paper (simulation, BOPTEST) - 5-state, 20-parameter RC from forward selection; 2+2 weeks data; 192 m² floor-heated, 15 kW air-to-water heat pump; τ ≈ 3.03 days.
14. Thermal Modelling of Water-Based Floor Heating Systems - supply temperature optimisation and self-regulating effects - H. Karlsson, Chalmers PhD thesis - 2010 - https://publications.lib.chalmers.se/records/fulltext/111900.pdf - paper (simulation + verification) - Self-regulation factor γ = -0.73, 70 % reduction of gain-induced rise; initial delay limits control period.
15. Modellbaserad styrning av värmesystem baserat på prognostiserat väder - D. Olsson, Chalmers licentiate thesis (Swedish) - 2014 - https://publications.lib.chalmers.se/records/fulltext/209907/209907.pdf - paper - Room sensor time constant 10-30 min vs duct under 1 min; single building time constant overstates solar inertia; "fictive outdoor temperature" with time coefficient.
16. Economic COP optimization of a heat pump with hierarchical model predictive control - F. Tahersima, J. Stoustrup, H. Rasmussen, S. Meybodi (AAU), IEEE CDC - 2012 - https://vbn.aau.dk/ws/files/73867242/cdc_2012.pdf - paper (simulation, verified on low-energy house) - 3-mass room/floor/water RC with supply temperature and flow inputs; Kalman-estimated states.
17. New European standards for design, dimensioning and testing embedded radiant heating and cooling systems - B. W. Olesen (DTU), Clima 2007 / CIB - c. 2007 - https://www.irbnet.de/daten/iconda/CIB8359.pdf - paper (standards summary) - 11 W/m²K floor heat exchange, q = 8.92·Δθ^1.1, surface limits and maximum outputs.
18. Influence of envelope, structural thermal mass and indoor content on the building heating energy flexibility - H. Johra, P. Heiselberg, J. Le Dréau, Energy and Buildings 183 (accepted manuscript) - 2019 - https://vbn.aau.dk/ws/files/290247579/Influence_of_envelope_structural_thermal_mass_and_indoor_content_on_the_building_heating_energy_flexibility_accepted_manuscript.pdf - paper (simulation) - Inertia classes 30-110 Wh/K·m²; furniture should be modelled.
19. Thermal storage in a heat pump heated living room floor for urban district power balancing - R. P. van Leeuwen, J. B. de Wit, J. Fink, G. J. M. Smit, SMARTGREENS - 2014 - https://www.scitepress.org/Papers/2014/49163/49163.pdf - paper (simulation) - Thermal-network living room model for MPC, floor ≈ 514 kg/m², cites Bacher & Madsen.
20. Experimental long-term investigation of model predictive heat pump control in residential buildings with photovoltaic power generation - S. Kuboth et al., Energies 13:6016 - 2020 - https://epub.uni-bayreuth.de/5598/1/energies-13-06016.pdf - lab (twin rigs, real air-to-water heat pumps) - 4-equation water/floor/zone state-space, 300 s Euler step, no observer.
21. Control of thermally activated building systems (TABS) in intermittent operation with pulse width modulation - M. Gwerder et al., Applied Energy 86 - 2009 - https://www.sysecol2.ethz.ch/OptiControl/LiteratureOC/Gwer_09_AE_86_1606.pdf - lab + paper - Slab time constants 9.9 h and 100 h; resistances.
22. Dynamic modeling and seasonal performance evaluation of air-to-water heat pump systems - M. Dongellini, Università di Bologna PhD thesis - 2017 - https://amsdottorato.unibo.it/id/eprint/7901/1/Dynamic%20modeling%20and%20seasonal%20performance%20evaluation%20of%20air-to-water%20heat%20pump%20systems.pdf - paper (simulation) - Capacity/COP polynomial maps per inverter frequency; EN 14825 cycling degradation Cc = 0.9 default, which underestimates real losses.
23. Buildings.Fluid.HeatPumps package documentation - Lawrence Berkeley National Laboratory, Modelica Buildings Library - current - https://simulationresearch.lbl.gov/modelica/releases/latest/help/Buildings_Fluid_HeatPumps.html - manufacturer-neutral model documentation - Carnot effectiveness (default 0.3) and refrigerant-side scroll/reciprocating models calibrated to manufacturer data.
24. Thermal battery for heat pump optimization - EMHASS documentation - current - https://emhass.readthedocs.io/en/latest/thermal_battery.html - blog (open-source docs) - 1-node slab model, capacity defaults, Carnot fraction 0.40-0.50, 1-3 h lag, under 20 % calibration target.
25. Is anyone monitoring condenser and evaporator temperatures? - OpenEnergyMonitor community - 2025 - https://community.openenergymonitor.org/t/is-anyone-monitoring-condenser-and-evaporator-temperatures/29204 - forum - Condensing about 1-3 K above flow (up to 5.5 K at high speed), evaporating about 5-8 K below air; 0.5 °C pressure-derived resolution; no heat-meter validation.
26. Carnot theoretical COP - from which values? - OpenEnergyMonitor community - 2025 - https://community.openenergymonitor.org/t/carnot-theoretical-cop-from-which-values/29201 - forum - Use flow and ambient; 50 % default Carnot fraction.
27. Samsung HT Quiet R32 8kW: emoncms COP vs simulated COP and zigzag pattern - OpenEnergyMonitor community - 2024-25 - https://community.openenergymonitor.org/t/samsung-ht-quiet-r32-8kw-emoncms-cop-vs-simulated-cop-and-zigzag-pattern/27385 - forum (owner data) - Carnot fraction 0.46 at 40 °C/1-2 °C, about 0.35 at -1.5 °C; Modbus-derived heat ±10 %; 2 kW instantaneous mismatch vs external flow meter.
28. Dynamic heat pump simulator - OpenEnergyMonitor community (T. Lea et al.) - 2025 - https://community.openenergymonitor.org/t/dynamic-heat-pump-simulator/28315 - forum / simulation - 3-stage RC building + Carnot COP, 30 s steps, visual validation only.
29. Air to Water Heat Pump catalogue GC-2101-06 (Versati III) - Gree - 2021 - https://germany-gree.de/wp-content/uploads/2021/06/GREE_Air_to_water.pdf - manufacturer - GRS-CQ10Pd/NhH-E: 9.5 kW, 2.07 kW input (COP 4.59) at A7/W35; 9.5 kW / 2.64 kW at the second rating point; leaving water 25-60 °C.
30. Modbus Protocol V1.5 for the Versati (R32) - Gree, via project note 08 (docs/research/notes/08-gree-versati.md, which cites https://man.kievclimate.com/man/Gree/Versati/Versati%20III/R32_Versati%20Modbus%20V1.5.pdf) - c. 2020 - manufacturer (secondary, not re-read here) - Read-only words 117-143 (discharge pressure as °C, suction, coil, water in/out, Hz), power-limit word 43, 1 °C accuracy statement.
31. pvlib.irradiance.erbs - pvlib python documentation - current - https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.irradiance.erbs.html - blog (open-source docs) - GHI to DNI/DHI decomposition via clearness index (Erbs, Klein, Duffie 1982).
32. Sol-air temperature - Wikipedia - current - https://en.wikipedia.org/wiki/Sol-air_temperature - blog (encyclopedia) - Sol-air formula with long-wave sky term.
33. CTSM-R - DTU Compute - current - https://ctsm.info/ - paper/tool page - Continuous-time stochastic grey-box estimation tool in R.
34. RC_BuildingSimulator - Architecture and Building Systems group (ETH) on GitHub - current - https://github.com/architecture-building-systems/RC_BuildingSimulator - blog (open-source) - 5R1C Python model; cites Madsen & Holst 1995, Bacher & Madsen 2011.
35. Grindinio šildymo sistemos techninių parametrų įtaka sistemos veikimo rodikliams (Influence of UFH technical parameters on system performance) - T. Valionis, KTU MSc thesis (Lithuanian) - 2022 - https://epubl.ktu.edu/object/elaba:116465061/116465061.pdf - paper (simulation) - Screed mass dominates; pipe spacing strongest inertia lever; pulsed flow +1.2 % output, about 3 % energy.
36. heatpumpmonitor.org introduction - OpenEnergyMonitor - current - https://docs.openenergymonitor.org/heatpumpmonitor/introduction.html - field data (platform docs) - Systems classed by metering quality (MID heat meters).
