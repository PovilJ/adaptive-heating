# Gap R2-G7: How accurate is refrigerant-side (internal) heat output estimation for a residential air-to-water heat pump, using discharge and suction pressure, temperatures, compressor Hz and power, compared with a heat meter? Is the Versati's own reported water flow or capacity readable and trustworthy over Modbus?

**Method note (read first).** The shared web-search budget for this workflow run was already used up when this researcher started. Both search attempts returned "budget used up", so no search-engine results were used. All sources were reached by other routes:
- direct fetches of known stable URLs (manufacturer PDFs, forum threads cited in sibling notes);
- DOI and ID lookups in scholarly metadata services (Crossref, OpenAlex, the HAL API). These were used only to resolve known papers and their citing papers, not as keyword search;
- PDFs that other researchers in this sweep had already downloaded to the shared scratchpad (Gree manuals, Daikin guide, RHPP and Fraunhofer reports).

HAL/theses.fr full texts sit behind an anti-bot wall, and MDPI and ScienceDirect returned 403. For the French "internal method" papers, the findings therefore rest on abstracts from HAL and OpenAlex, not full texts. No non-English forum material could be reached without search. The French theses' abstracts were read in French and English.

I also did two analyses of my own:
1. A CoolProp R32 sensitivity and Monte-Carlo calculation of the compressor-energy-balance method for this unit's sensor set.
2. A cross-sectional comparison of heatpumpmonitor.org systems by metering type (internal integration versus class-2 heat meter).

The repository code was not read.

## Summary

1. **The Versati exposes no water flow, no heat output or capacity, no electrical power and no suction pressure over Modbus.**
   - The full analog map (Words 0–166) in both Modbus V1.5 and V1.7 has temperatures, discharge pressure (given as a saturation temperature), set and running Hz (142/143) and nothing else of this kind. Words 138–141 and 144–166 are "Reserved" [1][2].
   - The 2025 control panel's "Parameter" view lists 17 values, also with no flow, power or capacity [5].
   - The only flow-related signals are binary: coil 170 (flow switch state), bit 108 (flow switch protection) and bit 188 (water flow protection) [1][2].
   - **Confidence: high.** So the question "is the Versati's flow trustworthy?" has a simple answer: there is no flow reading to trust.
2. **The water pump is variable speed and controlled to the water ΔT, so assuming a constant flow is unsafe.** Gree's service manual says the pump starts at an initial speed and then adjusts to the entering/leaving water temperature difference [3]. A rated or once-measured flow (for example the 1.72 m³/h used in gap-r1-G3) is valid only at that pump speed. Confidence: medium; the manual text is brief and copy-pasted ("fan" written for "pump").
3. **On a laboratory bench, the refrigerant-side "internal" (compressor energy balance) method is good.**
   - Tran et al. (EDF / Mines ParisTech) validated it in steady state against a reference measurement. It came within **4 %** of the reference heating capacity, against 10 % for an air-side method [16].
   - A long-term test including start-ups and defrosts came within **1 %** of an intrusive Coriolis reference for integrated performance. Errors in individual dynamic phases were "large" but rare and partly cancelled [21].
   - Instrumentation in those tests: a real condensing-pressure transducer, surface thermocouples, a compressor power meter and an explicit compressor heat-loss model [16][20].
4. **The compressor heat-loss term dominates the internal method's uncertainty.** Tran et al. found it contributes about **40 %** of the final heating-capacity uncertainty. A whole PhD (Goossens 2017) was spent on in-situ protocols to estimate rotary and scroll shell losses [20]. Nothing on the Versati measures shell losses.
5. **Vapour-injection (economiser) cycles break the simple single-mass-flow balance.** Singer, Tran & Rivière showed the injection-cycle version depends on assuming single-phase refrigerant at the compressor inlet, injection port and condenser/flash-tank outlets. Two-phase states there add a separate COP error [18]. Goossens et al. later validated an IHX/vapour-injection air-to-water prototype "in good agreement", but only in steady state [19].
   - The Versati III is a two-stage gas-injection (economiser) unit with economiser in/out sensors (Words 122/123) and two expansion valves [3][1].
6. **Instrument grade matters about 3×.** On a residential air-to-water test rig, commercial-grade sensors gave about **10 %** uncertainty on capacity, efficiency and refrigerant mass flow, against about **3 %** with laboratory-grade sensors [23]. A strain-gauge plus thermocouple non-intrusive method held real-time cycle-COP deviation to **3 %**, but only after calibration [22].
7. **My sensitivity analysis gives about ±10–12 % (1σ) for register-grade internal estimation on this unit** (calc, R32, +2 °C outdoor, minimum output, injection ignored):
   - 1 K error in discharge temperature gives 1.2 % error in heat; 3 K of pipe-surface bias gives 3.6 %.
   - 1 K in suction temperature gives 1.6 %; using the coil temperature as evaporating temperature with a 2 K error gives 2.5 %.
   - **±5 points in the compressor heat-loss fraction gives ±5.6 %.** Drive or auxiliary-power misallocation of 4 % gives 4.3 %.
   - Combined: register-grade about ±10 % (5–95 % band), instrumented about ±4.5 %.
   - This **excludes** vapour-injection effects and transients, so it is a lower bound for the Versati.
8. **ΔT × assumed flow is worse at this house's minimum output.** At ΔT ≈ 1.9 K with 0.1 K register resolution, 0.3 K sensor noise per sensor and a ±10 % flow assumption, my Monte Carlo gives **±25 % (1σ)** (−39 to +42 %, 5–95 %). At ΔT 5 K the same sensors give ±13 %. With whole-degree registers at 1.9 K it is ±33 %. This confirms note 14's "about 25 %".
9. **The temperature registers are tenths of a degree in practice, but the document says 1 °C.** Gree's map states "1 ℃" accuracy and transmission = actual value [1]. A working Home Assistant configuration reads Words 118 and 125–129 with a ×0.1 scale [6]. Treat the resolution as 0.1 K, but the absolute accuracy as unknown and uncalibrated.
10. **Even dedicated heat meters fail in the field more often than their class suggests.**
    - In the UK RHPP trial, **99 of 699 sites (14 %)** were excluded at the outset for heat-meter temperature-sensor installation problems [11].
    - Other problems in that trial: missing glycol correction (SPF over-estimated by **4–7 %**), sensor offsets that showed "heat" with no electricity input, and a median **1.5 %/year flow decay** [11].
    - Fraunhofer ISE's error budget for a correctly installed class-2/3 ultrasonic meter at ΔT 5 K was **±2.3 % (ΔT pair) + ±3 % (flow) → ±4.4 % on the work ratio** [10]. The temperature-pair error grows as 0.5 + 3·Δθmin/Δθ, so the same formula gives 5 % at 2 K [10].
11. **Manufacturer "internal" heat figures on other brands drift in both directions against meters.**
    - A Samsung unit's own Modbus flow and temperatures implied about **2 kW (≈40 %) more heat** than an external Axioma meter at one moment. The internal flow sensor also under-read the meter, and the gap grew at low flow [12].
    - Daikin, which does have a water flow sensor, calls its own produced-heat figure "an estimation, the accuracy cannot be guaranteed" [8].
12. **Cross-sectional field hint: internal "integration" metering reads higher than heat meters.** On heatpumpmonitor.org, Daikin systems using the unit's internal data (ESPAltherma etc.) have median SPF **3.75 (n=52)** against **3.34 (n=32)** for Daikin systems with class-2 heat meters, i.e. +12 %. Median %Carnot is 46.6 against 44.4 (+5 %) [14] (own analysis). This is confounded by house and installer, so it is suggestive only.
13. **For model identification, a consistent scale bias matters much less than a condition-dependent bias** (my reasoning, medium confidence).
    - A constant ×k error in heat input scales identified UA and C together. The time constants C/UA and predicted temperature trajectories are unchanged, so control predictions survive.
    - What hurts is bias that varies with operating point: low-ΔT water error at minimum output, or a heat-loss fraction that shifts with Hz and ambient temperature. That kind of bias distorts the slope of COP against flow temperature and the apparent K_ws.
14. **Bottom line for the owner (high confidence):** neither the Versati's own data nor a refrigerant-side reconstruction from its registers can provide heat input better than about ±10–15 %, with unknown bias. **A class-2 ultrasonic heat meter with M-Bus or Modbus is the decisive fix.** Use it at least for a calibration campaign, after which the internal estimators can be fitted against it.

## Detailed findings

### 1. What the Versati actually exposes

**Modbus analog map (V1.5, R32 Versati; identical in V1.7)** [1][2]:
- Temperatures:
  - Words 118 outdoor, 119 discharge, 120 defrost/coil, 121 suction.
  - 122/123 economiser in/out.
  - 125 water out at the plate heat exchanger (PHE), 126 optional water sensor, 127 water in at the PHE.
  - 128 tank, 129 remote room, 130/131 gas/liquid pipe.
  - All documented as "1 ℃" resolution with range −30…150 °C.
- Word 124 "Dis. pressure" is given as a temperature, −40…70 °C at 1 °C. It is the condensing saturation temperature from the high-pressure transducer.
- Words 142/143: set and running compressor frequency, 0–100 Hz in 1 Hz steps.
- Words 138–141 and 144–166: Reserved.
- **No register exists for:** water flow, pump speed, suction or low pressure, compressor current or power, unit power, energy, or heating capacity.
- Status bits:
  - Error/protection bits only: 93 high-pressure sensor error, 94 high-pressure protection, 95 low-pressure protection, 97 capacity DIP-setting error.
  - Flow: coil 170 flow switch state, bit 108 flow switch protection, bit 188 water flow protection.
  - Coil 175 indoor pump on/off.

**The panel view matches.** The 2025 Versati control panel shows 17 viewable parameters, with no flow, power or energy [5]. This fits the forum remark in note 08 that the panel lacks consumption data.

**Pressure sensors: the hardware and the text disagree.**
- The all-in-one and monoblock service manuals' general descriptions mention a high-pressure sensor, a low-pressure sensor and an injection ("enthalpy-adding") pressure sensor. The first-stage electronic expansion valve is said to be controlled on their ratio [3][4].
- But the component tables list a high-pressure sensor plus low-pressure *switches* (heating 0.1/0.2 MPa). The exploded parts lists show only one pressure sensor per unit [3][4].
- The text appears to be copied from the split Versati II manual. **Inference:** this unit probably has only a high-side transducer. Even if a low-side sensor exists, it is not exposed over Modbus [1][2].
- The evaporating temperature therefore has to be inferred from the coil ("defrost") temperature, Word 120. In heating this sits in the two-phase part of the outdoor coil, so it is a reasonable but uncalibrated proxy.

**Register resolution in practice.**
- A Home Assistant configuration that works on a Versati III reads 118 and 125–129 with scale 0.1, one decimal, and 118 as signed int16 [6]. The values are therefore tenths of a degree, despite the "1 ℃" statement in [1].
- Words 119–121 and 124 were not shown in that post, so their resolution is unconfirmed.
- No user in the long Home Assistant Versati thread reports any flow, power or COP register [7].

**The pump law.** The pump "will firstly run at the initialized speed and then adjust the speed according to the entering/leaving water temperature difference" [3]. No pump-speed register and no ΔT target are documented [1][3].
- Consequence: flow changes with operating point, so a once-measured flow cannot be reused blindly.
- If the pump really holds a ΔT target, the measured ΔT carries little information about heat. Nearly all of the heat signal would sit in the unmeasured flow.
- The owner's observed ~1.9 K ΔT at minimum output (gap-r1-G3) suggests the pump sits at a floor speed in mild weather. That is untested.

**Other brands, for contrast.**
- Daikin Altherma 3 has a real water flow sensor. Its produced heat is computed from leaving and entering water temperature and flow, and the sensors "are calibrated automatically". Daikin still states the figures are an estimate with no accuracy guarantee, and recommends external power meters over its calculated consumption [8].
- ESPAltherma exposes "Flow sensor (l/min)" and documents computing heat as flow × 0.06 × 1.16 × ΔT [9].

### 2. Accuracy of the refrigerant-side (internal) method in the literature

**The method family** (EDF R&D, Mines ParisTech CES):
- **Reference intrusive method** [15]: two Coriolis meters measure refrigerant flow and the vapour quality at the indoor heat-exchanger outlet. It was validated on an air-to-water heat pump against the water-enthalpy method, and stayed reliable in dynamic conditions including defrost.
- **Non-intrusive compressor energy balance** [16][17]:
  - Refrigerant mass flow = (compressor electrical power − shell heat loss) / (h_discharge − h_suction).
  - Evaporating pressure comes from a saturation-temperature measurement.
  - Condensing pressure comes from a transducer on the charging port.
  - Shell losses are estimated from heat exchange with the surroundings.
  - **Steady-state laboratory deviation was 4 %** against the reference, against 10 % for the air-enthalpy method [16].
- **Extension to dynamics** [21]:
  - An algorithm classifies operating modes (steady heating, stop, start-up, defrost), with modelling assumptions for each.
  - Over a long-term test, integrated performance was **within 1 %** of the intrusive reference.
  - "Large errors" occur in dynamic phases, but they are infrequent and partly compensate.
  - The authors explicitly say that units with liquid injection at compressor suction still need adaptation.
- **Compressor heat loss** [20]: about 40 % of the method's uncertainty. Goossens built calibrated thermal models of rotary and scroll shells, with data from Mitsubishi Heavy Industries, to define simplified in-situ measurement protocols. The rotary-compressor protocol was integrated and checked against an EDF test bench. The abstract gives no headline percentage.
- **Vapour injection or internal heat exchanger** [18][19]:
  - Injection cycles need extra energy and mass balances.
  - Their accuracy hinges on single-phase assumptions at several points. A parametric analysis quantified the COP deviation when those points are two-phase [18].
  - Validation on an air-to-water IHX/injection prototype agreed well, in steady state only [19].
- **Other routes:**
  - The outdoor-air enthalpy method differed by a mean **8 %** from an in-situ refrigerant-enthalpy method on a field air-source heat pump [24].
  - A 2025 strain-gauge method recovered pressure and compressor speed non-intrusively. It used a compressor-curve (map) method for mass flow and achieved **3 %** real-time cycle-COP deviation after calibration [22].
  - Sensor grade: on a residential air-to-water rig, commercial-grade sensors gave **about 10 %** uncertainty on capacity, efficiency and mass flow, against **about 3 %** for laboratory grade [23].

**What is missing.** I found no published field comparison of a manufacturer's own register-only refrigerant estimate against a heat meter on a residential air-to-water unit. Every validation above used added, calibrated instruments: a pressure transducer, contact thermocouples bonded and insulated on the pipes, and a compressor-only power meter.

### 3. Sensitivity of an internal estimate built from Versati registers (own calculation)

**Set-up.**
- R32 via CoolProp.
- Operating point: outdoor +2 °C, evaporating −4 °C, condensing 34 °C (flow about 32 °C), 4 K superheat, 3 K subcooling, isentropic efficiency 0.62. This gives discharge 91.9 °C, Δh_comp 73 kJ/kg and Δh_cond 335 kJ/kg.
- Electrical input 1 kW, drive efficiency 0.94, shell loss 10 %.
- Heat = (W·η_drive·(1 − f_loss)) · Δh_cond / Δh_comp, giving 3.87 kW, a plausible minimum-output point.
- Script: `scratchpad/r2g7_sens.py`, not kept in the repo.

**One-at-a-time effect on heat output:**

| Perturbation | Error in Q |
|---|---|
| Discharge temperature +1 K | −1.2 % |
| Discharge temperature +3 K (pipe-surface sensor reading low or high) | −3.6 % |
| Suction temperature +1 K | +1.6 % |
| Condensing temperature +0.5 K (1 °C quantisation of Word 124) | +0.1 % |
| Condensing temperature +2 K | +0.6 % |
| Evaporating temperature +2 K (coil Word 120 as proxy) | −2.5 % |
| Subcooling +3 K (liquid enthalpy unknown) | +1.8 % |
| Shell loss 5 % instead of 10 % | +5.6 % |
| Shell loss 15 % | −5.6 % |
| Drive efficiency 0.90 instead of 0.94 | −4.3 % |

**Monte Carlo, 20 000 draws:**
- Register-grade inputs: 1 °C quantisation plus 0.7–2 K bias on pipe sensors, ±1.5 K on the coil-as-evaporator, ±4 points on loss fraction, ±2 % on drive efficiency. Result: **5–95 % band −10.5 to +10.5 %**.
- Laboratory-grade inputs: **±4.5 %**, consistent with [16][23].

**What the calculation leaves out**, all of which push the real error higher:
1. **Vapour injection.** When the economiser valve is open, part of the condenser flow bypasses the evaporator and the compressor balance needs a second mass flow [18]. Economiser in/out (122/123) show whether injection is active. Restrict any internal estimate to periods when they read nearly the same.
2. **Auxiliary power.** A unit-level electricity meter includes the outdoor fan, the internal pump (about 75 W, note 08), controls and the crankcase/chassis heaters. At about 1 kW total, 150–250 W of auxiliaries is 15–25 % of the input. Each ±50 W misallocated is about ±5 % in heat.
3. **Transients.** The first minutes after start-up and the defrost cycles are where [21] saw large errors. This house cycles often and defrosts often in humid weather near 0 °C (note 09), so the transient share is higher than in [21].

**Discharge sensor.** The insensitivity to condensing temperature is good news: Word 124's 1 °C steps hardly matter. The discharge-temperature sensor is the critical one, and it is a strap-on thermistor whose bias against the true gas temperature is unknown.

### 4. Water-side ΔT × flow at this house's operating point (own calculation)

Assumptions: 1.72 m³/h, so ρ·c_p·V̇ ≈ 2.0 kW/K. Sensor noise 0.3 K per sensor, independent between the two sensors. Flow known to ±10 %.

| Case | 1σ error | 5–95 % band |
|---|---|---|
| ΔT 1.9 K, whole-degree registers | 33 % | −51 … +61 % |
| ΔT 1.9 K, 0.1 K registers | 25 % | −39 … +42 % |
| ΔT 5 K, 0.1 K registers | 13 % | −21 … +22 % |

The error is dominated by systematic offsets between the two thermistors, not by noise. Noise averages out over a run; offset does not.

**Cheap offset calibration.** Whenever the pump runs with the compressor off (anti-freeze, pump over-run, a hot-water changeover), the true PHE ΔT is close to zero. Its observed mean is the offset. RHPP saw exactly this failure in heat meters: "heat" recorded with no electricity input, attributed to temperature-sensor offsets made worse by pump over-run [11].

### 5. How good are real heat meters?

**Error formulas (EN 1434 as applied by Fraunhofer ISE)** [10]:
- Calculator: E_c = 0.5 + Δθmin/Δθ (%).
- Temperature pair: E_t = 0.5 + 3·Δθmin/Δθ (%).
- Flow sensor: E_v = 3 + 0.05·q_p/q (%) (class 3; class 2 is 2 + 0.02·q_p/q, standard value, not shown in [10]).
- For the Elster F96+ (Δθmin 3 K, q_p 2.5 m³/h) at ΔT 5 K and 1.05 m³/h, Fraunhofer's propagated SPF error was **4.4 %** [10].
- The same formula at Δθ = 2 K gives E_t = 5 %. That is below the 3 K Δθmin, so it is outside the meter's rated range. Mild-weather minimum-output running in this house sits there.

**Field reality from RHPP** (418 analysed sites) [11]:
- 99 of 699 sites were excluded at the outset for heat-meter temperature-sensor installation problems.
- Strap-on sensors gave systematic under-reading.
- No glycol correction gave SPF over-estimates of 4–7 %.
- An 18 kW meter limit was hit on up to 16 sites.
- Heat was recorded with no electricity input (offsets).
- Space-heating and hot-water sensors were transposed on some sites.
- Median flow-sensor decay was 1.5 % over a year.

**Uncertainty on a carefully instrumented GSHP site:** the Stockholm student centre achieved SPF H2 3.7 ± 0.2, about ±5 % [25].

**Community practice.** heatpumpmonitor.org lists 859 systems. Metering types: 435 Axioma Qalcosonic class 2, 169 Sontex class 2, 88 Kamstrup class 2, 130 "heat pump integration" and 7 Sika/Grundfos VFS flow sensors [14]. Headline statistics are restricted to MID-metered systems.

### 6. Internal versus metered: what the field shows

**Samsung (OpenEnergyMonitor)** [12]:
- At one moment, the unit's Modbus flow and ΔT gave about 7.1 kW against 5.1 kW from an Axioma meter on the same system.
- The internal flow sensor under-read the meter, more so at low flow.
- Contributing causes discussed:
  - Modbus values update at different times, so flow and return readings can be 10 s apart.
  - About 10 m of pipe between the unit and the meter.
  - A possible mistyped value.
- A second thread shows internal flow and heat oscillating together while flow temperature and input power stay flat. It reached no conclusion on whether that was real or sensor noise [13].

**heatpumpmonitor.org, own cross-section** (last 365 days, systems with at least 300 days of data) [14]:

| Group | n | Median SPF | Median %Carnot |
|---|---|---|---|
| Daikin, internal integration | 52 | 3.75 (IQR 3.30–3.90) | 46.6 |
| Daikin, class-2 heat meter | 32 | 3.34 (IQR 3.06–3.76) | 44.4 |
| Vaillant, internal integration | 8 | 3.90 | 45.8 |
| Vaillant, class-2 heat meter | 223 | 4.03 | 48.4 |

- Daikin's internally derived heat therefore reads about 5–12 % "better" than metered Daikin systems.
- For Vaillant the sign is reversed, but n = 8.
- Different houses, installers, emitters and electricity-metering choices confound both comparisons. Use them as a warning that internal figures can be biased by ±10 %, not as a correction factor.

## What this means for controlling this house

1. **Do not wait for a Versati flow or capacity register; none exists** (confidence high) [1][2][5]. Also do not hunt for one in Words 144–166. They are reserved in both protocol versions, and undocumented reads add nothing reliable.

2. **Install a heat meter. It is the highest-value hardware change for model identification** (confidence high).
   - Hardware: a class-2 ultrasonic meter (Axioma Qalcosonic, Sontex, Kamstrup class) with M-Bus or Modbus output and immersion pockets, not strap-on sensors [11].
   - Size: q_p 1.5 m³/h. The house runs at about 1.7 m³/h, and E_v = 2 + 0.02·q_p/q stays near 2 %.
   - Location: on the space-heating branch after the hot-water diverter valve, so tank cycles and the legionella immersion are excluded [10][11] (and note 14, Annex 71).
   - Check Δθmin in the datasheet. At about 2 K the meter is near or below its rated Δθmin [10], so expect ±5–8 % per sample at minimum output. That is still 3–5× better than any register method.
   - Logging: at least 30 s, written as integrated kWh per compressor run.
   - Testable: after 2–4 weeks, the identified UA should be repeatable within about 5 % between consecutive two-week windows.

3. **If a meter is impossible, rank the fallbacks like this** (confidence medium):
   a. **Water ΔT × flow, with one-off flow calibration and offset calibration.**
      - Calibrate flow once with a rented clamp-on ultrasonic flowmeter at the pump speeds actually used: minimum-output space heating, catch-up, and hot water.
      - Calibrate the 125/127 offset during pump-on, compressor-off periods.
      - Use only run-integrated energy, not instantaneous kW.
      - Expected accuracy: about ±10–15 % per run at 2 K ΔT, better on cold days.
   b. **Compressor energy balance from registers plus an external power meter**, used as a cross-check.
      - Use only steady periods: at least 10 min after start-up, no defrost (coil 86 = 0), economiser in ≈ out (no injection), Word 143 steady.
      - Subtract a fixed auxiliary power, about 150–200 W. Fit it once against a. or a heat meter.
      - Expected accuracy: ±10–15 %, with bias that depends on Hz through the shell-loss fraction.
   c. **Carnot-fraction model** (note 14): COP = η·T_cond/(T_cond − T_evap) with η about 0.45, multiplied by measured electricity. It shares the inputs of b. but hides the physics in one fudge factor, which varies 0.35–0.55 with frost and humidity (note 14). Use it only for sanity checks.

4. **Identify on whole runs or whole days, not instantaneous samples** (confidence medium-high).
   - Random sensor error and the effect of asynchronous Modbus updates [12] average out over integrated runs.
   - Systematic scale bias does not average out. But a constant scale bias on heat input leaves the time constant τ = C/UA and the predicted room trajectories unchanged; only absolute UA, C and COP are scaled.
   - **Rule:** use the same heat estimator for identification and for control-time prediction, and never mix a meter in some periods with an internal estimate in others.

5. **Treat COP-versus-flow-temperature conclusions from internal estimates with care** (confidence medium). The biases depend on the operating point:
   - The water method is worst at low ΔT, which here means low output in mild weather.
   - The refrigerant method varies with the shell-loss share at low Hz, and with injection.

   Such biases can create or erase an apparent 2–3 %/K flow-temperature penalty (note 08). Validate any COP-map decision, for example "run at 30 °C instead of 33 °C", against a metered A/B test, or at least against the electricity meter over matched-weather days.

6. **Log the inputs needed for any future reconstruction** (cheap, confidence high):
   - Words 119, 120, 121, 122, 123, 124, 125, 127, 143.
   - Coils 80, 86, 175, 178.
   - Unit electrical power.
   - All at 30–60 s with timestamps.

   Then a heat meter added later can calibrate the historical data retrospectively, by regressing meter heat on the register-based estimators over the overlap period.

7. **What to avoid:**
   - Using a nominal or once-measured flow at all pump speeds. The pump is ΔT-controlled [3].
   - Treating instantaneous heat at start-up or during defrost as meaningful.
   - Strap-on heat-meter sensors [11].
   - Including hot-water cycles in the space-heating heat input (note 14).

## Contradictions and open questions

1. **Register resolution.** Gree's map says "1 ℃" with transmission = actual value [1][2], yet a working Home Assistant configuration reads water and outdoor words at ×0.1 [6]. Owner check: are raw Word 125 values like 312 (31.2 °C) or 31? The resolution of 119–121 and 124 is unconfirmed.
2. **Low-pressure sensor or switch?** The service-manual text describes a low-pressure *sensor* used for defrost and expansion-valve control. The component tables and parts lists show low-pressure *switches* and a single pressure sensor [3][4]. Either way, Modbus exposes no suction pressure.
3. **Pump law.** "Adjust speed according to the entering/leaving water temperature difference" [3] gives no target ΔT and no limits. The owner's ~1.9 K at minimum output suggests a speed floor or a small target. A one-off clamp-on flow measurement at several outputs would settle it.
4. **Internal-method accuracy with injection and real-world dynamics.** The 1 % long-term figure [21] comes from an air-to-air unit *without* injection, with added sensors. The Versati has injection, frequent cycling and humid-climate defrost. No published validation covers that combination. The full texts of [16][18][19][20] could not be read (blocked), so the per-condition numbers are not available here.
5. **Direction of bias in manufacturer estimates is inconsistent.** Samsung internal data read high against a meter [12]. Daikin integration systems show higher SPF than metered ones [14]. Vaillant integration systems (n=8) show lower [14]. There is no general correction factor.
6. **Compressor-map method on the Versati.** A displacement × speed × suction-density map using Word 143 is physically possible. But Gree publishes neither displacement, nor a volumetric-efficiency map, nor the injection split, and suction density needs evaporating pressure (only the coil temperature is available). No validation is known. Accuracy is probably no better than ±15 % without calibration.
7. **Is the heat meter itself good enough at 2 K?** Most class-2 meters are rated from Δθmin = 3 K (F96+ example [10]). Whether a specific meter has a lower Δθmin, and how it behaves below it, should be checked in the datasheet before buying.

## Sources

1. Modbus Protocol (V1.5) for the Versati Heat Pump Water Heater (R32) - Gree Electric Appliances (hosted by kievclimate) - c. 2020 - https://man.kievclimate.com/man/Gree/Versati/Versati%20III/R32_Versati%20Modbus%20V1.5.pdf - manufacturer - Full analog map: Words 118–137 temperatures (1 ℃ stated), Word 124 discharge pressure as °C, 142/143 Hz, 138–141 and 144–166 reserved; no flow, power or capacity; flow-switch and protection bits.
2. Modbus Protocol (V1.7) for the Versati Heat Pump Water Heater - Gree (hosted by Gree Italia) - c. 2022 - https://www.greeitalia.it/WebDocTec/Documents/MDB//Modbus%20Protocol%20VERSATI%20III%20(V1.7).pdf - manufacturer - Confirms the same read-only map in the newest version; still no flow, power or capacity register.
3. Versati III All-in-one Air To Water Heat Pump, Service Manual - Gree (hosted by Gree Hungary) - c. 2020 - https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iii/versati%20iii%20all%20in%20one%20%E2%80%93%20service%20manual.pdf - manufacturer - Pump speed adjusted to water ΔT; pressure-sensor descriptions versus component table (HP sensor, LP switches); single pressure sensor in the parts list; two-stage expansion valve and injection control.
4. Versati III Monoblock Service Manual - Gree (hosted by Gree Bulgaria) - c. 2020 - https://gree-bulgaria.com/manuals/service/Versati_III_Monoblock_04_06_08_10_12_14_16_service.pdf - manufacturer - Same sensor text and the same HP-sensor/LP-switch component table; parts lists with one pressure sensor.
5. Control Panel for the Versati Air-to-water Heat Pump, Owner's Manual (2025) - Gree (hosted by gree.gr) - 2025 - https://gree.gr/wp-content/uploads/2025/07/600005064437-Users-manual-for-the-rest.pdf - manufacturer - The 17 viewable parameters include no flow, power or energy; flow switch only as a status.
6. Gree Versati III air to water heat pump, post #38 (Modbus configuration) - Home Assistant Community - c. 2023 - https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916/38 - forum - Working config reads Words 118, 125–129 with ×0.1 scale (tenths of a degree); no flow, power or COP registers.
7. Same thread, page 7 - Home Assistant Community - 2026 - https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916?page=7 - forum - No user reports any flow, heat or power register; discussion limited to temperatures, Hz, quiet mode, defrost.
8. Daikin Altherma 3 M Installer reference guide (4P685228-1, 2022.04) - Daikin Europe - 2022 - https://daikintechnicaldatahub.eu (document 4P685228-1) - manufacturer - Produced heat computed from leaving/entering water temperature and a flow sensor with automatic calibration, but "an estimation, the accuracy cannot be guaranteed"; external power meters preferred.
9. ESPAltherma README - raomin (GitHub) - 2025 - https://raw.githubusercontent.com/raomin/ESPAltherma/main/README.md - blog/open source - Daikin exposes "Flow sensor (l/min)"; community heat formula flow × 0.06 × 1.16 × ΔT.
10. WPsmart im Bestand, Abschlussbericht - Fraunhofer ISE (Günther, Wapler, Miara et al.) - 2020 - https://www.ise.fraunhofer.de/content/dam/ise/de/downloads/pdf/Forschungsprojekte/BMWi-03ET1272A-WPsmart_im_Bestand-Schlussbericht.pdf - field data (method section) - EN 1434 component error formulas; F96+ Δθmin 3 K, q_p 2.5 m³/h; ±2.3 % ΔT, ±3 % flow, ±4.4 % work-ratio error at 5 K.
11. Investigating variations in performance of heat pumps installed via the RHPP scheme - J. Love, A. Summerfield, P. Biddulph et al. (RAPID-HPC for BEIS) - 2017 - https://www.gov.uk/government/publications/detailed-analysis-of-data-from-heat-pumps-installed-via-the-renewable-heat-premium-payment-scheme-rhpp - field data - Heat-meter error catalogue: 99/699 sites excluded for sensor installation, glycol over-read 4–7 %, offsets giving heat without electricity, 1.5 %/year flow decay, transposed sensors.
12. Samsung HT Quiet R32 8kW: emoncms COP vs simulated COP and zigzag pattern - OpenEnergyMonitor community - 2024–25 - https://community.openenergymonitor.org/t/samsung-ht-quiet-r32-8kw-emoncms-cop-vs-simulated-cop-and-zigzag-pattern/27385 - forum (owner data) - Internal Modbus heat about 2 kW (≈40 %) above an Axioma meter at one instant; internal flow under-reads more at low flow; asynchronous Modbus updates.
13. Fluctuating flow and heat output - OpenEnergyMonitor community - 2025 - https://community.openenergymonitor.org/t/fluctuating-flow-and-heat-output/29313 - forum - Internal flow and heat oscillate while flow temperature and input stay flat; no consensus whether real or sensor noise; advice to cross-check with an independent meter.
14. heatpumpmonitor.org public system list and last-365-day statistics API - OpenEnergyMonitor - accessed 2026-11-06 - https://heatpumpmonitor.org/system/stats/last365 (and system list) - field data (own analysis) - Metering-type census (130 internal "integration" against about 700 class-2 meters); Daikin integration SPF 3.75 against metered 3.34; %Carnot 46.6 against 44.4.
15. Refrigerant-based measurement method of heat pump seasonal performances - C.T. Tran, P. Rivière, D. Marchio, C. Arzano-Daurelle, Int. J. Refrigeration 35:1583–1594 - 2012 - https://doi.org/10.1016/j.ijrefrig.2012.03.010 (abstract: https://minesparis-psl.hal.science/hal-00769729) - lab - Intrusive Coriolis reference method validated on an air-to-water heat pump against the water-enthalpy method, including defrost.
16. In situ measurement methods of air to air heat pump performance - C.T. Tran, P. Rivière, D. Marchio, C. Arzano-Daurelle, Int. J. Refrigeration 36 - 2013 - https://doi.org/10.1016/j.ijrefrig.2013.03.021 (abstract: HAL hal-00880157) - lab - Compressor-energy-balance method: 4 % deviation from reference in steady state (air method 10 %); condensing-pressure transducer at the charging port; shell losses from heat exchange.
17. Méthodes de mesure in situ des performances annuelles des pompes à chaleur air/air résidentielles - C.T. Tran, PhD thesis, Mines ParisTech - 2012 - https://pastel.hal.science/pastel-00765206 - paper (thesis, abstract only) - Origin of the non-intrusive refrigerant method; aims at on-board real-time performance display.
18. On-field measurement method of vapor injection heat pump system - E. Singer, C.T. Tran, P. Rivière, Int. J. Refrigeration - 2014 - https://doi.org/10.1016/j.ijrefrig.2014.01.008 (abstract: HAL hal-01497634) - paper (analysis) - Injection cycles need extra balances; accuracy depends on single-phase assumptions at four points; quantified COP deviation from two-phase states.
19. Experimental Validation of On-Field Measurement Method for a Heat Pump System with Internal Heat Exchanger - M. Goossens, P. Rivière, C. Teuillières, C.T. Tran, O. Cauret, Int. J. Air-Conditioning and Refrigeration - 2016 - https://doi.org/10.1142/S2010132516500115 (abstract: HAL hal-01461745) - lab - Method validated on an air-to-water IHX/injection prototype in steady state, "good agreement".
20. Improvement and integration of the in-situ heat pump performance assessment method - M. Goossens, PhD thesis, PSL/Mines ParisTech - 2017 - https://pastel.hal.science/tel-01753394 - paper (thesis, abstract only) - Compressor heat losses about 40 % of the method's uncertainty; shell-temperature models (MHI data) and in-situ loss protocols for rotary and scroll.
21. In-situ method for air-to-air heat pump seasonal performance determination including steady-state and dynamic operations - C.T. Tran, D. Noël, P. Rivière, C. Arzano-Daurelle, D. Marchio, Int. J. Refrigeration - 2021 - https://doi.org/10.1016/j.ijrefrig.2021.03.001 - lab (long-term) - Integrated performance within 1 % of the intrusive reference; large errors in start-up/defrost phases but rare; liquid-injection units need adaptation.
22. Non-intrusive performance monitoring method for air conditioners - N. Giannetti, J. Yin, Y. Miyaoka, L. Talluri, A. Milazzo, Int. J. Refrigeration - 2025 - https://doi.org/10.1016/j.ijrefrig.2025.10.003 - lab - Strain gauges plus thermocouples give pressures and compressor speed; compressor-curve mass flow; real-time cycle-COP deviation ≤3 % after calibration.
23. Impact of Sensor Accuracy and Model Calibration on Simulation of Heat Pumps with Refrigerant Leakage Faults - F. Pelella, A.F. Passarelli, R. Cilento, B. Llopis-Mengual, L. Viscito, J. Experimental and Theoretical Analyses 4(2):18 - 2026 - https://doi.org/10.3390/jeta4020018 - lab - Residential air-to-water rig: commercial-grade sensors about 10 % uncertainty on capacity, efficiency and refrigerant mass flow; laboratory grade about 3 %.
24. An Experimental Study of the Applicability of the Outdoor Air Enthalpy Difference Method for Air Source Heat Pumps in Operation through In Situ Measurements - J. Son, J.-H. Hong, T.-Y. Aum, Buildings 13(2):448 - 2023 - https://doi.org/10.3390/buildings13020448 - field data - Outdoor-air method averages 8 % off the in-situ refrigerant-enthalpy method.
25. Measured Performance of a Mixed-Use Commercial-Building Ground Source Heat Pump System in Sweden - J.D. Spitler, S.E.A. Gehlin, Energies 12(10):2020 - 2019 - https://doi.org/10.3390/en12102020 - field data - Carefully metered system: SPF H2 3.7 ± 0.2 (about ±5 %), a benchmark for best-case field uncertainty.
26. Own calculation - CoolProp R32 sensitivity and Monte Carlo of the compressor energy balance and water-ΔT methods at this house's operating point - 2026 - (scratchpad script r2g7_sens.py) - calc - One-at-a-time sensitivities and combined error bands quoted in Summary 7–8 and sections 3–4.
