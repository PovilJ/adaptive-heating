# Flow temperature, lift and COP

Research note 02 of the heat-pump deep sweep. Scope: how COP depends on leaving-water (flow) temperature, lift, approach temperatures, compressor speed, emitter ΔT and UFH physics, what field trials show, and whether a short high-temperature boost beats slow low-temperature delivery. Written without reading this repository's controller code.

Method note: 29 distinct web searches were run (English, German, Polish, Swedish, Dutch, Lithuanian), after which the shared search budget for this workflow ran out. 42 sources were read in full or in substantial part (PDF manuals, theses, trial reports, forum threads with measured data), plus 6 search-snippet-only sources, which are flagged. Numbers marked **[calc]** are my own arithmetic on a cited source's data. Numbers marked **[model]** come from a small simulation described in section 10. Neither is independent evidence.

## Summary

- **Each 1 K of flow temperature costs about 2–3 % of COP at the unit level.** The Gree Versati III 10 kW full-capacity table gives 2.3–2.7 %/K (geometric mean, W30→W45) at every ambient from −15 to +15 °C. Local 5 K steps range from 1.3 to 3.5 %/K [11; calc]. The nominal A7 rating drops 22 % from W35 to W45 for both the Versati III and the Versati IV 10 kW (4.6→3.6 and 5.00→3.90) [11][12]. A lab inverter water-to-water unit lost 29 % between 35 and 45 °C [17]. Field data: −0.069 SCOP per °C of coldest-day flow, about 1.9 %/K [2]. Whole-system SPF including DHW and auxiliaries moves only about 1.1 %/K [23].
- **Compressor speed is a second lever and is often larger than flow temperature.** At the same 35 °C flow and 7 °C air, a monitored Vaillant ran at COP ≈4.6 at 40 rps but ≈3.3 at 110–120 rps (−28 %) [5]. In the lab, COP fell up to 30 % as speed rose, with pressure ratio going from 2.7 to 5.8 [18]. In a Belgian UFH house at −5 °C, lowering the supply setpoint from 33 to 26 °C cut compressor input from 2.7 to 1.7 kW and daily use from 33 to 22 kWh. The author attributes the cut to the smaller setpoint gap, which let the compressor run slower [22].
- **Approach temperatures shrink at part load.** One measured Vaillant 10 kW condensed 1.1 K above flow at 30 rps but 5.5 K above at 50 rps, with evaporation about 5 K below air [13]. The usual rule of thumb is +2 K condensing and −6 K evaporating [4][13]. Every kelvin of approach is a kelvin of lift, so a slow compressor sees about 5–8 K less lift than a fast one at the same water and air temperatures [13; calc].
- **Real units deliver about 40–55 % of Carnot, using the +2/−6 K convention.** HeatpumpMonitor case systems reach 42–59 % on coldest days, and the best annual figure is 55 % [1]. EoH top-10 ASHPs ran at 45–57 % and the bottom-10 at 24–42 %, partly due to metering faults [4]. The Versati full-capacity table works out to 42–54 % (+2/−6, W30–W45) between −7 and +10 °C, but only 31–39 % at −15 °C [11; calc]. Rule: COP ≈ 0.45–0.5 × T_cond/(T_cond−T_evap) for a healthy system.
- **Field trials confirm "lower is better", but flow temperature explains only about half the spread.** Heat-weighted (flow − outside) explains about half the variance in SPF (R² ≈ 0.5–0.55). The rest is controls, cycling and product quality (% of Carnot) [1][3]. SPF ≥ 4 systems mostly run below 40 °C, typically about 35 °C, on the coldest day, and the published target is 36.6 ± 5.5 °C [1][3]. EoH: median ASHP SPF_H4 2.80 at a mean operating flow of 38.3 °C [6]. RHPP: 2.44 [10]. Fraunhofer, existing German houses: air-source JAZ mean 3.1, and UFH homes ran at a mean 33.2 °C with mean maxima of 38.5 °C [7].
- **A slab needs very little water temperature.** The EN 1264 base curve is about 8.92·Δθ_surface^1.1 W/m² (≈100 W/m² at 9 K, 175 W/m² at 15 K; surface coefficient ≈11.1 W/m²K) [25]. This house needs only about 15–35 W/m² between +10 and −5 °C (assuming ~140 m² of heated floor), so the floor surface sits just 1.5–3.3 K above the room [25; calc]. Steady-state flow at +2 °C should be about 27 °C on a tiled slab and about 30 °C on a timber-covered slab [model].
- **The observed setpoints look like "needed flow + restart gap".** Setpoints of 31–36 °C (peaks 39 °C) are 3–8 K above that steady-state need. This is consistent with a 4 K restart condition added on top of roughly 27–31 °C of real need (inference, needs checking).
- **The same daily heat in shorter, higher-power runs costs more electricity.** In a two-node slab model with the Versati map, a catch-up at about 90 % capacity used 16–22 % more electricity than long minimum-output runs between 0 and +10 °C. Counting only the flow-temperature effect, without the part-load gain, the penalty is 4–7 %. With a weaker (timber) floor it is 17–24 % [model]. A 6-on/4-off minute cycling pattern added 4–13 %. Squeezing the day's heat into an 8 h daytime window cannot hold comfort below about +10 °C (room swings of 4 K or more). Even at +10 °C it costs 9–16 % more, with a 3–3.6 K room swing [model].
- **In this firmware, the setpoint gap sets compressor power.** With a PI loop on leaving water, the steady compressor output is roughly (setpoint − slab-water temperature)/R. For a tiled slab R ≈ 0.5 K/kW, so 3.7 kW needs only about 2 K of gap and 7.4 kW about 4 K [model]. A restart rule of setpoint − outlet ≥ 4 K therefore commands about twice the minimum output at every start, unless the setpoint is walked back down after the compressor starts. In the emulation, an overshoot-safe walk-down saved 11–13 % with part-load gain, 2–6 % without it, and 0–5 % on a weak floor [model; firmware behaviour assumed, must be measured].
- **Cycling itself is cheap when runs are long; the indirect costs are the problem.** With an electronic expansion valve, a start loses about 15–25 % of capacity for about 100–130 s [16]. That is under 1 % for 1 h runs but 5–10 % for 6–10 min runs [calc]. Literature puts continuous versus cyclic operation at 5–25 % [16]. On/off units with small storage lose more than 12 % [21]. A 5 kW unit cycling every 9 min lost about 3 % [30]. The bigger hidden cost is that cycling forces a higher flow temperature and compressor speed during the on-phase [16][22].
- **Setbacks are a poor fit for a slab.** Manufacturers and installers cap setbacks at 2–3 K [26][27][28]. Large setbacks force high recovery flow temperatures and reduce SPF [3]. Counter-evidence exists: a low-mass radiator house saved 2.4–9 kWh/day with night setbacks [31]. That result does not transfer to a 6.6 kWh/K slab.
- **Outdoor temperature matters, but chasing it costs power.** COP rises about 2–4 % per K of air temperature (Versati W35: A2 3.85 → A7 4.61, about 3.9 %/K) [11; calc]. Shifting runs to warmer hours only pays if it does not require higher power. Frost forms when RH > 50 % and T < 6 °C [16]. Defrost costs about 0.15 SCOP in a UK simulation and 0.35–0.45 COP in a measured Scottish case [2]. Slow compressor operation keeps the evaporator warmer. One on/off unit had a better part-load than full-load COP between 1 and 6 °C [19].
- **The ~3 kW electrical draws at +2 °C are suspicious.** That exceeds what the Versati III 10 kW table implies at W35–40 and full capacity (2.1–2.2 kW). It matches W45–50 at full capacity (2.6–3.0 kW), a backup heater, or a different/larger model [11; calc]. Worth checking before anything else.

## Detailed findings

### 1. The thermodynamics that sets COP

- **Carnot limit.** For heating, COP_Carnot = T_cond / (T_cond − T_evap), in kelvin. Real COP = η·COP_Carnot, where η is the "practical efficiency" or % of Carnot.
- **Community convention.** HeatpumpMonitor.org and the OpenEnergyMonitor (OEM) EoH re-analysis estimate T_cond = flow + 2 K and T_evap = outside − 6 K. They integrate ideal electricity per 2-minute interval [4][14].
- **Modelica form.** The LBL Buildings library uses the same structure: COP = η_Carnot,0·COP_Carnot·η_PL. Approach temperatures are added to the condenser leaving temperature and subtracted from the evaporator side, and a polynomial part-load factor η_PL is applied [35].
- **Sensitivity to flow temperature** follows from the Carnot form: d ln COP / dT_flow = 1/T_c − 1/(T_c − T_e) ≈ −1/lift. With constant η and the +2/−6 K convention, the predicted COP loss per K of flow is [calc]:

| Outdoor air | Lift at W30–45 (K) | Carnot-predicted COP loss per K of flow |
|---|---|---|
| −15 °C | 53–68 | 1.3 %/K |
| −7 °C | 45–60 | 1.6 %/K |
| −2 °C | 40–55 | 1.8 %/K |
| +2 °C | 36–51 | 2.0 %/K |
| +7 °C | 31–46 | 2.3 %/K |
| +10 °C | 28–43 | 2.5 %/K |
| +15 °C | 23–38 | 3.0 %/K |

- **Theory versus real units.** In relative terms, the theory says flow temperature matters most in mild weather. That is exactly where this house spends most of its heating hours. Real units deviate from this at cold ambient (section 2).
- **Sensitivity to outdoor air.** Carnot with offsets gives +1.8 to +3.7 % COP per K warmer air (W30–W40, −10..+10 °C) [calc]. The Versati table shows about +3.8–3.9 %/K between A−7 and A−2, and between A2 and A7, at W35 [11; calc]. This includes the frost and defrost penalty that EN 14511 builds into the A2 test point.

### 2. Measured and declared COP versus flow temperature

**Gree Versati III 10 kW (split, 1-phase), manufacturer COP table at full capacity [11]** (extract):

| Flow \ Air | −15 °C | −7 °C | −2 °C | +2 °C | +7 °C | +10 °C |
|---|---|---|---|---|---|---|
| 25 °C | 2.70 | 3.96 | 4.68 | 5.40 | 5.62 | 5.87 |
| 30 °C | 2.23 | 3.35 | 3.96 | 4.61 | 5.11 | 5.44 |
| 35 °C | 1.84 | 2.81 | 3.35 | 3.85 | 4.61 | 4.86 |
| 40 °C | 1.69 | 2.52 | 3.06 | 3.60 | 4.10 | 4.32 |
| 45 °C | 1.48 | 2.23 | 2.70 | 3.17 | 3.60 | 3.78 |
| 50 °C | 1.26 | 1.91 | 2.27 | 2.63 | 3.10 | 3.24 |
| Max capacity at W35 (kW) | 5.32 | 6.65 | 7.41 | 8.08 | 9.50 | 9.79 |

- **What the table means.** The "COP correction" table reproduces the nominal 4.6 at A7/W35 and 9.5 kW, so its values are absolute COPs at the corresponding maximum capacity.
- **Per-K sensitivity [calc].** The geometric mean from W30 to W45 is 2.70 %/K at −15 °C, 2.68 at −7, 2.52 at −2, 2.47 at +2, 2.31 at +7, 2.40 at +10 and 2.29 at +15 °C. Individual 5 K steps range from 1.3 to 3.5 %/K.
- **Cold ambient is steeper than Carnot predicts.** This is because % of Carnot falls with pressure ratio at cold ambient. In the same table, % of Carnot with offsets drops from 39 % at W30 to 28 % at W50 at −15 °C [calc].
- **Caveat: the table looks partly interpolated.** The W35→W40 step is oddly flat at cold ambient (1.3–2.1 %/K). Capacities at W35, W40 and W45 are identical. Treat the table as a manufacturer model, not measured points.

**Other sources:**

| Source | Conditions | Sensitivity | Evidence |
|---|---|---|---|
| Versati III 10 kW nominal [11] | A7, W35 vs W45 (30/35 vs 40/45), rated capacity | 4.6 → 3.6 (−22 %), about 2.2 %/K | manufacturer |
| Versati IV 10 kW nominal [12] | Same | 5.00 → 3.90 (−22 %) | manufacturer |
| Blanco et al. 2013 [17] | Inverter water-to-water heat pump, lab, SH target 35 vs 45 °C | Average 29 % COP difference (about 2.5–2.9 %/K); best COP near 45 Hz | lab |
| Heat Geek [28] | 45 vs 55 °C flow | 20–30 % or more COP | installer |
| HeatpumpMonitor fit [2] | Heat-weighted coldest-day flow, ASHP fleet | −0.0688 SCOP/°C ±0.61 (about 1.9 %/K at SCOP 3.7); predicted SCOP 4.0 / 3.7 / 3.3 / 3.0 at 35 / 40 / 45 / 50 °C | field |
| HeatpumpMonitor refit [2] | x = heat-weighted (flow − outside) | SCOP = 6.86 − 0.104·x (about 2.8 % per K of lift at x = 30) | field |
| Ploskic, SBUF [23] | Ground-source system SPF, 50→35 °C design supply, simulation | +1.1 %/K; about 2.2 %/K if DHW and auxiliary electricity were halved | simulation |
| SBUF 14234 [24] | Ground-source, Swedish, simulation | 15–20 % less purchased electricity per 10 K lower supply; literature cited at 1–2 % COP per K | simulation |
| Rules of thumb [43][44][48][42] | — | Bosch 2.5 %/K; Dutch installers 2 %/K; Polish portals 2.5 %/K; CIBSE CPD answer option 1.5–3 %/K | snippet / weak |

- **Takeaway: use 2.5 %/K for unit COP in mild weather, 2–3 %/K generally.** Use roughly half that for whole-system SPF, because DHW, pumps and defrost dilute it.

### 3. Real units as a fraction of Carnot

- **HeatpumpMonitor case studies, coldest day, +2/−6 convention [1].**
  - Viessmann Vitocal 10 kW: 58.8 % (flow 32.7 °C, −3 °C).
  - Vaillant 7 kW (Heat Geek): 44.7 %.
  - Ecodan 11.2 kW: 47.2 %.
  - Arotherm 5 kW: 41.9 %.
  - Arotherm 7 kW: 49.5 %.
  - The best annual figure was 55 % (Vitocal 150A).
- **% of Carnot and system temperature are independent drivers.** "% Carnot while running" correlated with SCOP at R² 0.54, about as strongly as weighted (flow − outside) at R² 0.50. The two were only weakly correlated with each other, so roughly half of performance comes from temperatures and half from everything else [1].
- **EoH re-analysis [4].**
  - Top-10 ASHPs: 45–57 % Carnot at weighted flows of 30.7–45.3 °C.
  - Bottom-10: 24–42 %, some of it heat-meter error.
  - Removing systems below 40 % raised the mean SPF from 2.79 to 2.97.
  - A 35 % floor was called "possibly on the low side".
- **Practical factor of 0.45–0.55** is the community's working range [15]; "50 % if not known" [14].
  - A Samsung 8 kW owner fitted 0.46 over 6 h, but only about 35 % at −1.5 °C overnight.
  - The factor improved by about 0.1 on a similar day with lower humidity, consistent with frost loss [15].
- **Versati III table at full capacity [11; calc].**
  - Simple (flow/air): 36–44 % for W30–W45 between −7 and +10 °C.
  - With +2/−6 K offsets: 42–54 % in the same range; at W50 this falls to 38–49 %.
  - At −15 °C: 28–33 % simple and 31–39 % with offsets (W30–W45).
- **Lithuanian humid-cold test (snippet only, not verified) [45].** At 0 °C and 95 % RH, an air-to-water unit had mean exergy efficiency 0.21 and COP 1.49.

### 4. Condenser and evaporator approach temperatures, and why part load helps

- **Measured (one unit, OEM forum) [13].** Vaillant aroTHERM plus 10 kW: condensing about 1.1 K above flow at 30 rps (space heating) and about 5.5 K above at 50 rps (DHW). Evaporating about 5 K below intake air at both speeds. The author warns the sensor alignment is approximate.
- **Rules of thumb [13].**
  - John Cantor: condensing about 2 K above flow, evaporating about 6 K below intake air. The air outlet is much closer to evaporating temperature than the intake is.
  - A community simulator uses +3 K and −8 K at full load, scaled linearly with load.
- **Why approaches shrink.** At fixed heat-exchanger area (fixed UA), approach is roughly proportional to heat flow. Halving the output roughly halves the condenser and evaporator temperature differences.
- **Size of the effect [calc, modelled assumption +1+5·PLR K and −(3+6·PLR) K].** Between full load and 40 % load, lift falls by about 6–7 K. That is worth about 15–20 % in Carnot COP at mild conditions.
- **Not all of that gain is realised.**
  - Compressor isentropic efficiency peaks near 50 Hz [18]. In a lab inverter unit, the best COP occurred near 45 Hz, not at the lowest frequency [17].
  - Below a minimum speed (typically 15–30 Hz on a 120 Hz-rated compressor), volumetric efficiency collapses. Motor efficiency also falls at low frequency [16].
  - A Swedish study (snippet only) found part-load COP improved with variable speed, but annual efficiency did not, mainly because of inverter and motor losses [47].
- **Practical conclusion: low speed is good, the absolute minimum is not guaranteed optimal.** For this Versati, the owner-measured minimum of 3.7–3.8 kW is about 40 % of nominal and about 45 % of A2 maximum capacity. That is plausibly near the efficiency sweet spot (inference).
- **Optimum condensing temperature.** For a capacity-controlled unit there is a condensing temperature that minimises compressor plus circulation-pump power. Going below it costs more than going above it, so the penalty is asymmetric [20].

### 5. Compressor speed at fixed water and air temperatures: the hidden catch-up penalty

- **HeatpumpMonitor analysis [5]:** at 35 °C flow and 7 °C air, COP ≈4.6 at 40 rps versus ≈3.3 at 110–120 rps, a 28 % drop. The author suggests this explains part of the low % Carnot seen across many systems.
- **Lab [18]:** COP fell by up to 30 % as compressor speed rose, with pressure ratio going from 2.7 to 5.8. Absolute inverter losses grew with speed.
- **Field case, Belgium, UFH, frost days [22].** Lowering the heating-curve supply from 33 to 26 °C at −5 °C kept comfort. Compressor input fell from 2.7 to 1.7 kW, the 2 kW backup heater stopped engaging, and daily use fell from 33 to 22 kWh. The author's explanation is that a smaller gap between actual and requested supply temperature lets the compressor run slower.
- **EoH case EOH2578, simulated in a peer-reviewed paper [3].** Fixing the weather curve and allowing modulation lifted COP from 2.86 to 4.61. Electricity fell by about a third, and the 6 am peak fell from 5.1 to 1.2 kW. 55 % of 165 inspected Vaillant systems had weather curves set too high and were cycling on room thermostats instead of modulating.
- **This house [11; calc].** At +2 °C the Versati III 10 kW table implies full-capacity electrical input of:
  - 8.08/3.85 = 2.1 kW at W35
  - 2.2 kW at W40
  - 2.55 kW at W45
  - 2.96 kW at W50

  Observed draws of about 3 kW at +2 °C therefore mean either very high water temperatures during catch-ups, a backup or tank heater, or a different or larger model than the Versati III 10 kW.

### 6. Flow versus return versus mean water temperature, and emitter ΔT

- **Which temperature matters for what.**
  - The refrigerant condenses at roughly constant temperature. In a counter-flow plate condenser the water leaves just below the condensing temperature, so **leaving-water (flow) temperature sets the lift** [13][35].
  - The emitter's output depends on the **(log-)mean water temperature** relative to the room. EN 1264 defines ΔθH = (θV − θR)/ln[(θV − θi)/(θR − θi)] [25].
  - Return temperature mainly affects refrigerant subcooling, a second-order gain for R32/R410A at small ΔT.
- **ΔT arithmetic.** At a fixed mean water temperature, flow = mean + ΔT/2.

| Emitter ΔT | Flow above mean | Relative COP (2.5 %/K) | Water flow for same heat |
|---|---|---|---|
| 3 K | +1.5 K | 1.00 | 2.33× |
| 5 K | +2.5 K | ≈0.975 | 1.4× |
| 7 K | +3.5 K | ≈0.95 | 1.0× |

  On the Versati A2 table slope, 2 K vs 7 K ΔT at a 26.4 °C mean gives COP 5.02 vs 4.63 (−8 %) [11; calc].
- **This unit's actual ΔT.**
  - The Versati IV 10 kW rated water flow is 1.72 m³/h (about 2.0 kW/K) and the minimum is 0.75 m³/h [12].
  - At the 3.7 kW minimum output and rated flow, ΔT ≈ 1.9 K. At 8 kW it is about 4 K. At minimum flow and 3.7 kW it is about 4.2 K [calc].
  - In mild weather, ΔT is already small. Pushing more flow gains almost nothing, while cutting pump speed raises flow temperature only about 1 K and may save more pump power than it costs in COP.
  - A single circulator in a monitored UK system drew 47 W [31]. Against 0.6–0.8 kW of compressor input at minimum output, that is 6–8 %. This is the "compressor + pump" optimum of [20].
- **Field spreads.** Fraunhofer measured space-heating spreads averaging 5.5 K (3.0–7.8 K), and 5.8 K for DHW [7].
- **Danish UFH/heat-pump project [34].** It estimated a theoretical 15 % COP improvement from optimising and stabilising volume flow, and noted that supply temperatures are often set higher than needed.
- **Contradiction.** One prominent installer argues ΔT does not directly affect COP as long as the heat is carried away, and that what matters is the ΔT range available without cycling. Others counter that a lower ΔT means a lower flow temperature for the same emitter output [29]. Both are right in their own frames: at fixed flow temperature ΔT barely matters, but at fixed emitter output a smaller ΔT lowers the flow temperature.

### 7. UFH output versus mean water minus room temperature, and the slab

- **EN 1264 numbers via the Danfoss handbook [25].**
  - Floor-to-room total coefficient about 11.1 W/m²K.
  - About 100 W/m² at 9 K surface excess and about 175 W/m² at 15 K, which equals the EN 1264 base curve 8.92·Δθ^1.1.
  - Surface temperature limits: 29 °C in occupied zones, 35 °C at edges, 33 °C in bathrooms.
  - The water-side output q = K_H·ΔθH depends on screed, pipe spacing and covering, via the equivalent coefficient K_H.
- **This house [calc, assuming about 140 m² heated floor, H = 0.17 kW/K].**

| Outdoor | Load | q | Floor surface above room |
|---|---|---|---|
| +10 °C | 2.0 kW | 15 W/m² | 1.6 K |
| +2 °C | 3.4 kW | 24 W/m² | 2.5 K |
| −5 °C | 4.6 kW | 33 W/m² | 3.3 K |
| −20 °C | 7.1 kW | 51 W/m² | 4.9 K |

  The floor works far below its limits. Mean water temperature only needs to be a few kelvin above the room.
- **Two-node approximation used in the model (section 10).** Water→slab conductance K_ws and slab→room conductance K_sr.
  - Tiled slab: K_ws ≈ 3.5 kW/K, K_sr ≈ 1.0 kW/K, so mean water − room ≈ 1.29 K/kW.
  - Timber/carpet "weak" floor: K_ws ≈ 2.0 kW/K, K_sr ≈ 0.6 kW/K, so about 2.17 K/kW.
  - These are assumptions, not measurements. The owner can calibrate them (see the last section).
- **Resulting steady-state flow temperatures at rated pump flow [calc/model].**

| Outdoor | Tiled slab | Weak floor |
|---|---|---|
| +10 °C | ≈25.1 °C | ≈26.9 °C |
| +2 °C | ≈27.2 °C | ≈30.2 °C |
| −5 °C | ≈29.1 °C | ≈33.1 °C |
| −20 °C | ≈33.0 °C | ≈39.3 °C |

- **Field comparators.**
  - Fraunhofer, existing houses with UFH: mean heating-circuit temperature 33.2 °C, mean of daily maxima 38.5 °C, above new-build norms [7].
  - Belgian UFH house: ran comfortably on 26 °C at −5 °C [22].
  - HeatpumpMonitor UFH homes with SCOP > 4 all ran below about 35 °C [5].
  - Lithuanian and Polish guidance quotes about 35 °C for UFH [37].
- **Slab as storage.**
  - In the Belgian case the concrete floor stored 8–10× more energy than an 800 L buffer heated to 50 °C [22].
  - This house's measured 6.6 kWh/K is equivalent to about 5,700 L of water per kelvin [calc].
  - Slab time constant C_s/K_sr is about 6.6 h (tiled) to 11 h (weak) in the model [model].
  - Installers recommend keeping slab temperature steady: setback no more than 3 K on air sensing and 2 K on floor sensing [26].

### 8. Field evidence in one place

| Programme | Sample | Headline numbers | What it says about flow temperature |
|---|---|---|---|
| HeatpumpMonitor.org [1][2][3][5] | 59 → 594 systems (413 MID-metered, Nov 2025) | Mean SPF 3.86 (H4) [3]; coldest-day mean flow ≈36 °C, about 7 K below entered design flow; peak 2 h flow ≈ day mean + 2.5 K [1] | SPF ≥ 4 mostly < 40 °C (typically ~35 °C); slope −0.069 SCOP/°C; R² ≈ 0.5 for (flow − outside) |
| UK EoH [3][4][6] | 291 ASHPs in interim SPF analysis | Median ASHP SPF_H2 2.94, SPF_H4 2.80; coldest day (−0.4 °C) COP_H4 2.44 [6] | Lower mean operating flow (38.3 °C average) gives higher SPF, significant but scattered; high-temperature units performed like low-temperature ones because weather compensation kept them low [6] |
| UK RHPP [9][10] | Cropped sample B2: 292 ASHP + 92 GSHP | Median ASHP SPF_H2 2.65, SPF_H4 2.44; design flow mean 40–45 °C; weather compensation used on 64 % [10] | Only weak inverse COP–flow relation (metering noise); ~10-minute on-to-on cycling very common in ASHPs; immersion heaters averaged 12 % of electricity [9] |
| Fraunhofer WPsmart im Bestand [7] | 29 ASHPs, 2018/19, existing houses | JAZ 2.5–3.8, mean 3.1; mean SH temperature 36.9 °C, mean max 43.6 °C (at −3 °C); heating rod 1.9 % of compressor work | Heating-circuit temperature is the only factor whose link to JAZ clearly stood out; UFH systems ranked higher |
| Fraunhofer, 4-year follow-up [8] | 77 HPs | ASHP mean 3.4 (vs 3.1 in 2019); GSHP 4.3 | Some units showed excessively high switching frequencies; some oversized |
| Lithuania, 2009 [38] | 1 UFH + MVHR house, 175 m², near Vilnius | COP ≈3.7–3.9 (narrow boundary, no pumps or DHW) | Local example only |

- **Interpretation.** Every large dataset agrees on direction. None shows a clean single slope, because metering error, DHW share, cycling, defrost and product quality add scatter of ±0.5–0.6 SPF [2][9].

### 9. Cycling, start-up losses and mild weather

- **Start-up physics [16].**
  - When a compressor stops, refrigerant migrates and pressures equalise. Each start must rebuild the pressure difference.
  - Measured penalties: with an electronic expansion valve (EEV), capacity is 75–85 % for 100–130 s and power is 95–100 % for 60–90 s. With a thermostatic valve (TEV), capacity is 55–65 % for 240–300 s.
  - A typical compressor limit is 6 starts per hour.
  - Literature quoted: continuous versus cyclic operation differ by 5–25 % in efficiency.
  - A modulating unit can supply water at a significantly lower average temperature than the same unit cycling, which raises average COP.
- **Annual impact.** For on/off units sized to cover a large share of peak load with small storage, cycling losses can exceed 12 % of electricity [21]. At load factors below 10 % with a TEV, losses of up to 13 % were reported (snippet, [21]).
- **Part load beats full load near freezing.** In an 8 kW on/off air-to-water unit tested between −7 and +12 °C, part-load COP exceeded full-load COP between about 1 and 6 °C despite cycling. Outside that band, performance degraded mainly through standby losses [19].
- **Small measured penalties when runs are reasonable.**
  - John Cantor's example: a 5 kW Samsung cycling every 9 min lost about 3 % of COP [30].
  - A 14 kW Ecodan cycling about 3 times per hour on a mild day showed no visible penalty (COP 4.4–4.5 vs 3.9 non-cycling, confounded by ambient) [30].
  - Counter-example: one owner went from 150+ starts per day (about 8 per hour) at COP ≈2.5 to near-continuous running at 600–900 W at COP ≈4 [32].
- **Mild weather is unavoidable cycling territory.**
  - Compressors typically modulate only about 3:1 [29].
  - Measured minimums: Vaillant 10 kW 5.9 kW [33]; Arotherm 5 kW 2.5 kW [40]; this Versati 3.7–3.8 kW (owner).
  - A well-sized unit cycles above roughly 10–12 °C outdoor [29].
  - Fraunhofer notes manufacturers usually set minimum compressor run times of 6–20 min [7].
- **Versati manual guidance [11][12].**
  - Load "too small" makes the unit start and stop frequently, which is bad for oil return. The recommended fan-coil load is 70–120 % of unit capacity.
  - Minimum system water: 5 L/kW for defrost reliability (Versati III); 8–10 L/kW primary (Versati IV).
  - After a stop, the compressor waits at least 3 minutes before restarting.
  - ΔT-Heat ("leaving water temperature difference for heating", Δt2) has a 2–10 °C range and a 10 °C default. This matches the owner's restart hysteresis register (now 4).
  - A "Quiet mode" exists; its effect on maximum frequency is not documented.

### 10. Worked numbers: short high-temperature boost versus slow low-temperature delivery

**(a) Closed-form example at +2 °C** (H = 0.17 kW/K, load 3.4 kW, 81.6 kWh/day; Versati III table [11]; part-load factor from section 4) [calc]:

| Way of delivering 81.6 kWh | Flow during runs | COP (table / with part-load gain) | Electricity per day |
|---|---|---|---|
| Near-continuous at minimum output (3.7 kW, 22 h) | ≈27.2 °C | 5.05 / 5.79 | 16.2 / 14.1 kWh |
| Catch-up at ~90 % capacity (≈7.3 kW, ~11 h) | ≈29.3 °C | 4.72 / 4.82 | 17.3 / 16.9 kWh (+7 % / +20 %) |
| High-speed runs at 33 °C flow (setpoint-gap scenario) | 33 °C | 4.15 | 19.7 kWh (+22 % / +39 %) |
| High-speed runs at 36 °C flow | 36 °C | 3.80 | 21.5 kWh (+33 % / +52 %) |

- Even a "pure" boost on a well-coupled slab raises flow by only about 2 K. Most of the penalty comes from losing the part-load advantage. Penalties become large once the realised flow is several kelvin above need, as the setpoint pattern suggests may happen here.

**(b) Two-node slab model with the Versati map [model].**

- **Nodes.** Water loop mean temperature (C_w 0.25 kWh/K), slab (C_s 6.6 kWh/K), room (C_r 1.5 kWh/K).
- **House.** H = 0.17 kW/K, room target 22 °C, 1-minute step, results from steady periodic days.
- **Heat pump.** Output 0 or between 3.7 kW and the Versati maximum capacity at the current flow and air temperature. Flow = water mean + Q/(2·ṁc_p) with ṁc_p = 2.0 kW/K.
- **COP.** Versati table × part-load factor, with approaches +1+5·PLR K and −(3+6·PLR) K and compressor efficiency 0.93→1.0 between 30 % and 50 % load. Run with and without the part-load factor.
- **Start penalty.** EEV values from [16].
- **Not modelled.** Defrost, pump power, DHW. Absolute COPs are optimistic; compare the relative columns.

Strategies, all held to comfort (room 21.4–22.5 °C) unless noted:

- **lowslow:** minimum output with ±0.15 K room hysteresis, or modulate when load is above minimum.
- **boost:** off until the room reaches 21.7 °C, then run at 90 % of maximum capacity until 22.2 °C.
- **shortcycle:** like lowslow, but chopped 6 min on / 4 min off with higher on-power.
- **dayblock:** the whole day's heat in a 09:00–17:00 window.

| Air | lowslow kWh_el (COP, flow) | boost Δ | shortcycle Δ | dayblock |
|---|---|---|---|---|
| 0 °C | 17.1 (5.25, 27.7 °C) | +16 % | +13 % | fails comfort (room 15–20 °C) |
| +2 °C | 14.2 (5.78, 27.2 °C, 1 start/day) | +18 % | +10 % | fails comfort (17–22 °C) |
| +5 °C | 10.9 (6.19, 26.7 °C, 2.5 starts, 8 h runs) | +19 % | +6 % | +21 %, room 19.2–23.4 °C |
| +10 °C | 7.0 (7.01, 26.0 °C, 3 starts, 4 h runs) | +22 % | +4 % | +16 %, room 20.3–23.4 °C |

Sensitivities:

- **Without the part-load factor:** boost is only +4–5 %, shortcycle +5–8 %.
- **Weak floor:** boost +17–24 % at 0..+10 °C. The lowslow flow rises to 28–31 °C.
- **±3 K diurnal swing peaking at 14:00:** boost +14–22 %. Dayblock still fails comfort at +5 °C and below, and costs +9 % at +10 °C with a 3.6 K room swing.
- **H = 0.20 kW/K:** same pattern, boost +13–22 %.
- **At −10 °C** the load (5.4 kW) is above minimum output, everything runs continuously, and "boost" cannot even hold comfort.

**(c) Setpoint-writing emulation against an assumed firmware** [model; firmware behaviour unverified].

Assumed firmware:
- PI on leaving water (Kp 2 kW/K, Ki 4 kW/(K·h); also tested 4 and 12).
- Starts only when setpoint − outlet ≥ 4 K.
- Stops when outlet > setpoint + 1 K.

Policies compared:
- **current-like:** at start the controller writes outlet + 4.5 K and holds it until the room is satisfied.
- **ride-down:** start the same way. Then every 5 min write max(return + Q_min/ṁc_p + 0.4 K, outlet − 0.7 K), lowering the setpoint without ever triggering the overshoot stop.

Results:

- **current-like spends 7–16 h/day above 75 % of capacity** at −5..+5 °C (tiled slab).
- **Ride-down uses 11–13 % less electricity** at 0..+10 °C (e.g., +2 °C: 14.0 vs 16.1 kWh). It gives 2–6 % less without the part-load factor, and 0–5 % less on a weak floor, with similar comfort and fewer, longer runs.
- **A naive ride-down fails.** Writing return + Q_min/ṁc_p immediately after the start, without the overshoot guard, made the unit trip on overshoot every 6 minutes (48 starts/day) and lose comfort. The size and timing of setpoint changes matter as much as their level.

**Conclusion for the boost question.** On a slab, delivering the same heat in fewer, higher-power hours is less efficient:
- About 4–8 % from flow temperature alone on a well-coupled floor, more on a weak floor.
- About 15–25 % when the lost low-speed advantage is included.
- Up to 30–40 % if catch-ups push flow 5–8 K above need, as in [5][18][22].

It only pays when the electricity is cheaper or free (PV surplus) by more than that penalty, or when the boost runs at a markedly warmer air temperature (each K of air is worth about 2–4 %).

### 11. Outdoor temperature, time of day, humidity and defrost

- **Time of day.** COP gains about 2–4 % per K of warmer air [11; calc]. A Belgian EMS that moved heating to daytime cut November–February use by 476 kWh against the previous year, also using PV [22].
- **Lithuanian winter.** Diurnal swings are small on overcast humid days, so most of the timing gain comes in spring and autumn. In the model, a ±3 K swing did not overturn the low-and-slow advantage [model].
- **Frosting.** Frost forms when outdoor RH > 50 % and T < 6 °C [16].
- **Measured defrost cost.**
  - Simulated defrost of 1.6 % of heat ≈ 0.15 SCOP [2].
  - A 12 kW aroTHERM plus in Highland Perthshire showed a 0.35–0.45 COP penalty against modelled non-defrost COP [2].
  - A Samsung owner's % of Carnot was about 0.1 lower on a humid night than on a drier day [15].
- **Slow running should frost less (plausible, unproven here).** Lower compressor speed means a smaller evaporator approach and a higher evaporating temperature, so frost grows more slowly. The on/off test where part-load COP beat full-load between 1 and 6 °C is consistent with this [19].
- **Lithuanian generic COP guide [37].** Typical COP:

| Outdoor | Typical COP |
|---|---|
| +10 °C | 4.0–5.0 |
| +5 °C | 3.5–4.5 |
| 0 °C | 3.0–3.5 |
| −5 °C | 2.9–3.3 |
| −7 °C | 2.3–2.9 |
| −10 °C | 2.0–2.5 |
| −15 °C | ~2.0 |

### 12. DHW: the high-lift part of the year

- **Fraunhofer [7].** Mean DHW operating temperature 47.1 °C (41.2–53.2 °C), spread 5.8 K. DHW share of heat ranged from 4 to 42 %. Significant heating-rod use appeared only with misconfiguration, defects or legionella routines.
- **RHPP [9][10].** DHW SPF_H2 2.3 versus space heating 2.72 (ASHP medians). Immersion heaters averaged 12 % of electricity, and over 20 % in half of the sites with SPF_H4 < 2.
- **Versati table [11; calc].** At A2, COP is about 3.2 at W45 and about 2.6 at W50, versus 5+ for slab heating. Each DHW kWh costs roughly twice the electricity of a slab kWh.

## What this means for controlling this house

Context:
- Slab UFH with 6.6 kWh/K of storage.
- Versati with a minimum output of 3.7–3.8 kW, larger than the 1.7–3.4 kW mild-weather load.
- Flow setpoint written over Modbus about every 30 min.
- Firmware starts only when setpoint − outlet ≥ ΔT-Heat (now 4 K) and stops on outlet overshoot.

Confidence tags: **H** = consistent across physics, lab and field; **M** = physics plus model, direction likely, magnitude uncertain; **L** = depends on unverified firmware behaviour.

1. **Treat the setpoint as a power command, not a temperature target. (M/L)**
   - If the inverter runs a PI loop on leaving water, steady output is roughly (setpoint − slab-water temperature)/R.
   - R is about 0.5 K/kW on a tiled slab and about 0.75 K/kW on a timber floor [model].
   - Minimum output (3.7 kW) therefore needs only about 2 K (tiled) to 2.8 K (timber) of headroom above the slab-water temperature. Every extra kelvin asks for about 1.3–1.9 kW more heat output.
   - Setpoints of 31–36 °C over a slab at about 25–28 °C ask for near-maximum power.
   - **Test:** log compressor frequency (if readable over Modbus), electrical power, outlet and return for setpoint gaps of +1, +2, +3, +4, +6 K above outlet.

2. **The restart hysteresis makes every start a boost unless the setpoint is walked down afterwards. (L)**
   - With setpoint − outlet ≥ 4 K required to start, the start command already equals about 2× minimum output on a tiled slab.
   - Proposed rule to test:
     - (a) Start with setpoint = outlet + ΔT-Heat + 0.2 K.
     - (b) After the compressor is confirmed running (and any minimum-run lock-out), lower the setpoint every 2–5 min towards return + Q_min/(ṁ·c_p) + 0.3–0.5 K. At rated flow that is return + about 2.2–2.4 K.
     - (c) Never set it more than (stop margin − 0.3 K) below the current outlet.
   - First measure the real stop margin (how far outlet must exceed setpoint before the unit stops), any minimum run time, and whether "Quiet mode" caps frequency.
   - Expected gain if the firmware behaves as modelled: about 11–13 % of electricity in 0..+10 °C weather on a tiled slab with part-load gain. It falls to 0–6 % if the unit's part-load COP gain is small or the floor is weak [model].

3. **Lower ΔT-Heat from 4 to 2 K (the allowed minimum is 2 K) only together with rule 2. (L)**
   - A smaller restart gap reduces the start overshoot.
   - Home Assistant then has to guard against too-frequent restarts itself: at least 3 min off is firmware-enforced; aim for runs of 60 min or more.
   - Do not go back to the 10 K default; it would force even larger start commands.

4. **In mild weather, aim for few, long runs at minimum output. (H direction, M magnitude)**
   - At +10 °C a 4 h run at 3.7 kW stores about 7–8 kWh, raising the slab about 1.0–1.2 K, followed by about 3–5 h off. That gives about 3 starts per day [model].
   - Target 1–4 starts per day above 0 °C, never more than 2–3 per hour, and mean runs of 1 h or more.
   - Start losses are then under 1 % [16; calc]. Whatever is gained, keep the realised flow low during runs.

5. **Reference flow temperatures, to calibrate, not to impose. (M)**
   - Expected realised flow at minimum output or matched load: tiled slab about 25–26 °C at +10 °C, 27 °C at +2 °C, 29 °C at −5 °C, 33 °C at −20 °C. A timber floor is about 2–6 K higher [model].
   - If observed realised flows sit more than 3 K above these at the same outdoor temperature and output, the controller is buying lift it does not need. Expect about 2.5 % COP per K in mild weather [11][2].
   - **Calibrate this house's emitter:**
     - During a stable run of 6 h or more at known output Q (from heat meter or electricity × COP estimate), record mean water temperature, return, room and outdoor.
     - Fit (T_mean_water − T_room) ≈ Q·R_total. R_total is about 1.3 K/kW (tiled) to 2.2 K/kW (timber) in the model.
     - The owner's 0.14–0.20 kW/K and 6.6 kWh/K already cover the house side.

6. **Avoid catch-ups by not falling behind. (H)**
   - Keep room setbacks at or below 0.5–1 K. Literature allows 2–3 K [26][27][28], but this slab plus the restart rule turns any deficit into a high-power recovery.
   - Start runs earlier and slower rather than later and harder.
   - A boost is justified only when energy is cheaper or free by more than the penalty: about 15–25 %, up to 40 % if catch-ups run at high flow [section 10]. PV surplus qualifies.

7. **Use PV by extending or advancing minimum-output runs, not by raising power. (M)**
   - Shifting a run into PV hours at the same low power keeps the efficiency. Raising the setpoint to absorb PV (as in [22]) trades efficiency for self-consumption.
   - That is fine when the extra electricity is surplus that would otherwise be exported at a low price. It is a cost-optimisation decision, not an efficiency one.
   - Do not compress a whole day's heat into a short window below about +10 °C. With about 8 kW of capacity it cannot deliver the heat, and the room swing exceeds 3 K [model].

8. **Emitter ΔT and pump. (M)**
   - At minimum output and rated flow, ΔT is about 1.9 K. Do not raise flow rate. Test a lower pump speed (ΔT 3–4 K at minimum output).
   - Expected outcome: flow rises about 1 K (−2.5 % COP), while pump savings of 20–40 W are about 3–6 % of compressor input. It is a near-wash, so decide by measurement [20][31][calc].

9. **DHW. (H)**
   - Heat DHW to the lowest acceptable temperature (about 45–48 °C), with legionella handled by the tank's electric heater as now.
   - Schedule DHW at the warmest or PV hours and away from the start of a space-heating run.
   - After a DHW cycle, restart space heating from a setpoint referenced to slab and return temperature, not the residual hot water.

10. **Defrost on humid −5..+5 °C days. (M/L)**
    - Expect long low-speed runs to need fewer defrosts per kWh than high-speed catch-ups [16][19].
    - **Test:** count defrosts per day and per kWh of heat versus mean compressor power on comparable humid days.

11. **Monitoring KPIs to add. (H)**
    - Instantaneous and daily % of Carnot: η = COP / [(T_flow + 2 + 273.15)/((T_flow + 2) − (T_out − 6))], following [4]. Healthy is about 45–55 %. Watch for dips during catch-ups and high-frequency periods.
    - Heat-weighted mean flow temperature per outdoor bin.
    - Starts per day and mean run length.
    - Fraction of run time above 75 % of maximum capacity.
    - DHW share of electricity.
    - Electrical power at +2 °C, to check the ~3 kW anomaly. If it holds at W35–40, check backup or tank heater use, sensor scaling and the exact model.

12. **What not to do.** Do not raise the flow setpoint just to stop mild-weather cycling. Do not use deep night setbacks. Do not write large setpoint steps that the PI will chase at high frequency. Do not shorten the restart hysteresis without the ride-down logic and an anti-short-cycle guard.

**Overall confidence.**
- High that lower realised flow temperature and lower compressor speed both raise COP, by about 2–3 %/K and up to about 30 % respectively.
- Medium that this house can save on the order of 10–25 % of space-heating electricity in 0..+10 °C weather by removing high-speed catch-ups and excess flow temperature.
- Low on the exact firmware mechanics (PI gains, stop margin, minimum run times); these need a few days of instrumented tests before any control rewrite relies on them.

## Contradictions and open questions

**Contradictions:**

1. **How much per kelvin?**
   - Unit-level: about 2.5 %/K [11][12][17][43].
   - Field fleet slope: about 1.9 %/K [2].
   - Whole-system SPF, Nordic simulation: 1.1 %/K [23].
   - Carnot with constant η predicts 1.3 %/K at −15 °C rising to 3 %/K at +15 °C. The Versati table is instead slightly steeper at cold ambient (2.7 %/K) than mild (2.3 %/K), because % of Carnot falls with pressure ratio [11; calc].
   - These measure different things (unit COP, fleet regression, system SPF) and should not be averaged.
2. **Is the minimum speed the most efficient?** Approach-temperature physics says lower is better [13]. Compressor and inverter data put the efficiency peak near 45–50 Hz, not at the minimum [17][18]. One Swedish study found variable speed gave no annual gain once inverter and motor losses were counted (snippet) [47]. For the Versati the minimum (about 40–45 % of capacity) is probably near the optimum, but this is unmeasured.
3. **Does ΔT affect COP?** Installer view: not directly. Physics at fixed emitter output: yes, through flow temperature, against pump power [29][20][34]. Both hold in their own frames (section 6).
4. **Is cycling costly?** Small measured penalties of about 3 % or none [30] versus 5–25 % in literature [16], more than 12 % for on/off with small storage [21], and anecdotes of COP 2.5→4 [32]. Resolution: the per-start loss is small. The large costs come from short runs, standby losses, and the higher flow and speed that cycling induces.
5. **Setbacks.** Measured savings in a low-mass radiator house [31] versus manufacturer and peer-reviewed warnings [3][27][28]. For a heavy slab, the reduced-heat-loss benefit is small and the recovery penalty larger. Untested in this house.
6. **Field correlation strength.** EoH: significant [6]. RHPP: weak [9]. HeatpumpMonitor: R² about 0.5 [1]. Metering quality and filtering explain much of the difference.
7. **Part load in frost conditions.** Common wisdom says cycling always hurts, but an on/off unit showed part-load COP above full-load at 1–6 °C [19], probably because of less frosting.

**Open questions (need data from this unit):**

- Does the Versati control compressor frequency with a PI/PID on leaving water? What are its gains, overshoot stop margin, minimum run time, and start ramp? Does "Quiet mode" cap frequency [11]?
- Can compressor frequency or current be read over Modbus? Community register maps exist but are inconsistent across Versati generations (HA community thread, not read in detail).
- What is the real part-load COP map? EN 14825 declared COPs at points A–D (Keymark) would quantify the part-load gain directly. Not retrieved because the search budget ran out.
- What is this slab's actual water→room characteristic? It decides whether realised flow should be about 27 °C or about 31 °C at +2 °C.
- Does the circulation pump run while the compressor is off? This affects outlet-sensor readings and the restart condition. What does the pump draw at each speed?
- Do slow runs reduce defrost frequency on humid −5..+5 °C days?
- Why does the unit draw about 3 kW at +2 °C (high flow, backup or tank heater, metering, or model)?
- How large are the DHW share and the electricity per DHW cycle, and does DHW interrupt space-heating runs at bad moments?

## Sources

1. HeatpumpMonitor.org: SCOP (Annual) vs "design" flow temperature - Trystan Lea et al., OpenEnergyMonitor forum - 2024 - https://community.openenergymonitor.org/t/heatpumpmonitor-org-scop-annual-vs-design-flow-temperature/26653 - field data (community monitoring) - 59-system analysis: coldest-day flow about 36 °C, measured about 7 K below design, SPF ≥ 4 mostly below 40 °C, % Carnot case table, R² 0.54 vs 0.50, peak 2 h flow about +2.5 K.
2. What SCOP can you expect from a system that runs at 55C and 50C flow temperatures on the coldest days? - Trystan Lea et al., OpenEnergyMonitor forum - 2026 - https://community.openenergymonitor.org/t/what-scop-can-you-expect-from-a-system-that-runs-at-55c-and-50c-flow-temperatures-on-the-coldest-days/29547 - field data analysis - SCOP slope −0.0688/°C ±0.61; refit −0.104 per K of flow − outside; defrost cost estimates (0.15 SCOP; 0.35–0.45 COP real case).
3. Bridging the heat pump efficiency divide (on Rosenow, Lea & Boni, Energy and Buildings 352, 116785) - CIBSE Journal - 2026 - https://www.cibsejournal.com/technical/bridging-the-heat-pump-efficiency-divide/ - paper (peer-reviewed, summarised) - HeatpumpMonitor 3.86 vs EoH 2.81 vs RHPP 2.36; R² 0.55; coldest-day flow 36.6 °C for SPF ≥ 4; EOH2578 COP 2.86→4.61; 55 % of 165 systems with weather curve too high; setbacks force higher recovery flows.
4. Electrification of Heat trial data (page 5) - Trystan Lea et al., OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/electrification-of-heat-trial-data/27445?page=5 - field data analysis - Carnot method (+2/−6 K), filtering effects on SPF, top and bottom 10 ASHPs with % Carnot and flows.
5. HeatpumpMonitor.org: Findings - OpenEnergyMonitor forum (T. Lea, F. Smith et al.) - 2025 - https://community.openenergymonitor.org/t/heatpumpmonitor-org-findings/28164 - field data / forum - COP about 4.6 at 40 rps vs about 3.3 at 110–120 rps (35/7); UFH SCOP > 4 systems below about 35 °C.
6. EoH Interim Heat Pump Performance Data Analysis Report - Energy Systems Catapult - 2023 - https://es.catapult.org.uk/wp-content/uploads/2023/03/EoH-Interim-Heat-Pump-Performance-Data-Analysis-Report-1.pdf - field data - Median ASHP SPF_H2 2.94 / SPF_H4 2.80 (n=291); mean operating flow 38.3 °C; SPF higher at lower flow; coldest day COP 2.44.
7. WPsmart im Bestand – Schlussbericht (BMWi 03ET1272A) - Fraunhofer ISE (Günther et al.) - 2020 - https://wp-monitoring.ise.fraunhofer.de/wpqs-im-bestand/download/Berichte/BMWi-03ET1272A-WPsmart_im_Bestand-Schlussbericht.pdf - field data - ASHP JAZ 2.5–3.8 (mean 3.1); heating-circuit temperatures (UFH 33.2/38.5 °C); spreads 5.5 K; DHW 47.1 °C; heating rod 1.9 %; minimum compressor run times 6–20 min.
8. Four-year testing finds heat pumps run efficiently even in older homes - pv magazine (on Fraunhofer ISE) - 2025 - http://www.pv-magazine.com/2025/11/04/four-year-testings-finds-heat-pumps-run-efficiently-even-in-older-homes/ - field data (news report) - 77 heat pumps, ASHP mean 3.4, excessive switching in some units.
9. RHPP: On performance variations (v20) - Love, Lowe et al. (RAPID-HPC) for DECC - 2016/2017 - https://assets.publishing.service.gov.uk/media/5a81fa0e40f0b62305b91d1a/DECC_RHPP_160428_On_performance_variations_v20.pdf - field data - Weak inverse COP–flow relation; 10-minute cycling common; immersion 12 %; UFH sometimes run above 55 °C.
10. RHPP Final Report (v1-13) - Lowe, Summerfield et al. for DECC - 2017 - https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/606818/DECC_RHPP_161214_Final_Report_v1-13.pdf - field data - Median ASHP SPF_H2 2.65, SPF_H4 2.44; design flows 40–45 °C mean; weather compensation 64 %; DHW SPF 2.3.
11. VERSATI III Split Type Air-to-Water Heat Pump Service Manual - Gree Electric Appliances - n.d. (c. 2020) - https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iii/versati%20iii%20split%20%E2%80%93%20service%20manual.pdf - manufacturer - Full COP and capacity tables by flow (25–60 °C) and ambient (−25..35 °C); nominal ratings; ΔT-Heat 2–10 °C default 10; minimum water 5 L/kW; start/stop warning; Quiet mode; 3 min restart delay.
12. VERSATI IV Split Type Air-to-Water Heat Pump Service Manual - Gree Electric Appliances - n.d. (c. 2023) - https://gree-climat.com.ua/pdf/manual_versatti_4.pdf - manufacturer - 10 kW: 10.2 kW at A7W35 COP 5.00, A7W45 COP 3.90; rated water flow 1.72 m³/h, minimum 0.75 m³/h; minimum water 8–10 L/kW; same ΔT-Heat parameter.
13. Is anyone monitoring condenser and evaporator temperatures? - OpenEnergyMonitor forum (A. Kühne et al.) - 2025 - https://community.openenergymonitor.org/t/is-anyone-monitoring-condenser-and-evaporator-temperatures/29204 - field data (single unit) / forum - Measured approach temperatures vs compressor speed (Vaillant 10 kW); Cantor +2/−6 K rule; simulator assumptions.
14. Carnot "theoretical COP" from which values? - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/carnot-theoretical-cop-from-which-values/29201 - forum - Practical Carnot factor (50 % default), which temperatures to use.
15. Samsung HT Quiet R32 8kW emoncms COP vs simulated COP and zigzag pattern - OpenEnergyMonitor forum - 2024 - https://community.openenergymonitor.org/t/samsung-ht-quiet-r32-8kw-emoncms-cop-vs-simulated-cop-and-zigzag-pattern/27385 - forum / field - Practical factor 0.45–0.55; 0.46 fit; about 35 % at −1.5 °C humid; humidity effect about 0.1.
16. Dynamic modeling and seasonal performance evaluation of air-to-water heat pump systems (PhD thesis) - Matteo Dongellini, University of Bologna - 2017 - https://amsdottorato.unibo.it/id/eprint/7901/1/Dynamic%20modeling%20and%20seasonal%20performance%20evaluation%20of%20air-to-water%20heat%20pump%20systems.pdf - paper (thesis, models with manufacturer test data) - 6 starts/h limit; 5–25 % continuous vs cyclic; minimum frequency 15–30 Hz; start penalties TEV/EEV; lower supply temperature with modulation; frosting conditions.
17. Experimental study on a monovalent inverter-driven water-to-water heat pump with a desuperheater for low energy houses - Blanco, Nagano, Morimoto, Applied Thermal Engineering 50(1) 826–836 - 2013 - https://eprints.lib.hokudai.ac.jp/repo/huscap/all/52254/ATE50-1_826-836.pdf - lab - 29 % COP difference 35 vs 45 °C; highest COP near 45 Hz; pressure ratio as key variable.
18. Experimental analysis of a variable capacity heat pump system focusing on the compressor and inverter loss behavior - Madani, Ahmadi, Claesson et al., Purdue Conference R23/2241 - 2010 - https://iifiir.org/en/fridoc/experimental-analysis-of-a-variable-capacity-heat-pump-system-focusing-27509 - lab (abstract) - COP falls up to 30 % with speed; pressure ratio 2.7→5.8; isentropic efficiency peak near 50 Hz.
19. Seasonal performance of on-off air-to-water heat pumps - Bensafi, Mondot, Rivière, ICR 2007 - 2007 - https://iifiir.org/en/fridoc/seasonal-performance-of-on-off-air-to-water-heat-pumps-24935 - lab (abstract) - 8 kW unit, part-load COP higher than full-load between 1 and 6 °C despite cycling; standby losses dominate elsewhere.
20. Parametric study of energy saving potential for capacity controlled heat pumps – optimal condensation temperature - Karlsson & Fahlén - 2002 - https://heatpumpingtechnologies.org/?p=53098 - paper (abstract) - Optimum condensing temperature minimising compressor + circulation-pump power; asymmetric penalty.
21. Sizing strategy of on-off and modulating heat pump systems based on annual energy analysis (Int. J. Refrigeration 65:183–193) - Bagarella, Lazzarin, Noro (via Earth Notes bibliography) - 2016 - https://www.earth.org.uk/bibliography/bagarella2016modulating.html - paper (summary note) - Cycling losses can exceed 12 % of electricity with small storage; SPF alone not decisive.
22. Sturing van warmtepompen: waar de echte winst zit - Bart Vannoppen, Volta (Belgium) - 2026 - https://volta-org.be/media/amrbnnjj/sturen-van-warmtepompen-waar-de-echte-winst-zit.pdf - field case / technical blog - UFH house at −5 °C: 33→26 °C supply, compressor 2.7→1.7 kW, 33→22 kWh/day; slab stores 8–10× an 800 L buffer; daytime shifting saved 476 kWh/season; +1 K setpoint to absorb PV.
23. Framledningstemperaturen bestäms av värmebehovet (SBUF 13122) - A. Ploskic, Energi & Miljö no. 9 - 2016 - https://vpp.sbuf.se/Public/Documents/ProjectDocuments/3214fb17-4e36-45c3-b83b-614a8222ffad/FinalReport/SBUF%2013122%20Vetenskaplig%20artikel%20Ploskic%20A.%20Framledningstemperaturen%20best%C3%A4ms%20av%20v%C3%A4rmebehovet.pdf - simulation (trade journal) - System SPF +1.1 %/K (50→35 °C), about 2.2 %/K if DHW and auxiliaries halved; UFH meets the same load at 15 K lower supply than panel radiators.
24. Hur lågt kan vi gå? Optimerade lågtempsystem (SBUF 14234 final report) - SBUF - n.d. (c. 2023) - https://vpp.sbuf.se/Public/Documents/ProjectDocuments/fb3440a8-b138-476a-8f61-344a27e2cf28/FinalReport/SBUF%2014234%20Slutrp%20Hur%20l%C3%A5gt%20kan%20vi%20g%C3%A5%20Optimerade%20l%C3%A5gtempsystem.pdf - simulation report - 15–20 % less purchased electricity per 10 K lower supply (ground source); 1–2 %/K COP literature value.
25. Handbook Planning Underfloor Heating (VGCTC202) - Danfoss - 2009 - https://assets.danfoss.com/documents/100650/AG000086464394en-010201.pdf - manufacturer - EN 1264 base curve values (100 W/m² at 9 K, 175 W/m² at 15 K), α ≈ 11.1 W/m²K, surface limits, log-mean excess temperature definition.
26. Using your Heat Pump Under-floor Heating System - eco+Logic HP/UFH - n.d. - https://cdn.shopify.com/s/files/1/0236/4093/2416/files/Using_your_Heat_Pump_UFH_9f39da3c-2753-4415-b942-65edb8f1dfe0.pdf - manufacturer / installer guide - Setback ≤ 3 K air, ≤ 2 K floor; steady slab temperature more efficient; stagger zone transitions.
27. Is it a good idea to use both weather compensation and setback at the same time? - Grant UK - n.d. - https://www.grantuk.com/professional/support/product-support/air-source-heat-pumps/faqs/is-it-a-good-idea-to-use-both-weather-compensation-and-setback-at-the-same-time/ - manufacturer - Prefer continuous weather compensation; setback no more than 2 °C including hysteresis.
28. Vaillant sensoCOMFORT heat pump controller guide - Heat Geek - n.d. (c. 2024–25) - https://www.heatgeek.com/vaillant-sensocomfort-heat-pump-controller - installer blog - 45 vs 55 °C = 20–30 % COP; setbacks 2–3 °C maximum; continuous low output preferred.
29. Performance of Heat Pumps in Mild Weather - Renewable Heating Hub forum - 2025 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/performance-of-heat-pumps-in-mild-weather - forum (with monitored graphs) - Minimum outputs and flow/ΔT data for several units; about 3:1 modulation; ΔT-and-COP debate.
30. Heat pump truth or myth #2: cycling uses a lot of power and ruins your COP - Renewable Heating Hub forum - 2022–2024 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/heat-pump-truth-or-myth2-cycling-uses-a-lot-of-power-and-ruins-your-cop/ - forum (one measured system) - Ecodan 14 kW cycling vs non-cycling COP; Cantor's 9-minute-cycling ≈3 % penalty.
31. Creative trials on night-time setbacks to faster recovery, improved comfort and even greater energy reductions (page 2) - Renewable Heating Hub forum - 2024 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/creative-trials-on-night-time-setbacks-to-faster-recovery-improved-comfort-and-even-greater-energy-reductions/paged/2 - forum (one measured system, radiators, low mass) - Setback saved 2.4–9 kWh/day vs continuous; pump 47 W.
32. How to reduce cycling? (page 6) - OpenEnergyMonitor forum - 2024 - https://community.openenergymonitor.org/t/how-to-reduce-cycling/25251?page=6 - forum - 150+ starts/day at COP about 2.5 vs near-continuous 600–900 W at COP about 4.
33. HeatpumpMonitor.org heat pump database: minimum modulation tests - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/heatpumpmonitor-org-heat-pump-database-minimum-modulation-tests/29132 - field data / forum - Vaillant 10/12 kW minimum about 5.9 kW; minimum output ≈ minimum flow × 5 K rule for Vaillant.
34. Under floor heating and heat pump optimization (64014-0548) - Teknologisk Institut, Bosch, Caverion, Aalborg University (EUDP) - 2015–2017 - https://energiforskning.dk/en/node/15159 - project page - Theoretical 15 % COP potential by optimising volume flow; supply temperatures often set too high.
35. Buildings.Fluid.HeatPumps (Carnot_TCon, Carnot_y) documentation - Lawrence Berkeley National Laboratory, Modelica Buildings Library - current - https://simulationresearch.lbl.gov/modelica/releases/latest/help/Buildings_Fluid_HeatPumps.html - model documentation - Carnot-effectiveness COP structure with approach temperatures and part-load polynomial.
36. Flow rates, efficiency and COP - Renewable Heating Hub (site editor) - 2021/2022 - https://renewableheatinghub.co.uk/?p=14490 - blog / owner data - 45→35 °C flow lifted measured COP from 2.7 to 2.88, then above 3 with longer runs.
37. Šilumos siurblių parinkimas 2025 - Lietuvos energetikos agentūra (ENA) - 2025 - https://www.ena.lt/uploads/PDF-EVE/2025-12/Silumos-siurbliu-parinkimas-2025.pdf - government guide - Typical COP by outdoor temperature for Lithuania; about 35 °C for UFH.
38. Realiai veikiančio šilumos siurblio efektyvumo tyrimas - V. Žėkas, V. Martinaitis, Mokslas – Lietuvos ateitis 1(1) - 2009 - https://journals.vilniustech.lt/index.php/MLA/article/download/10782/9137 - field data (Lithuania, one house) - UFH + MVHR house near Vilnius, COP about 3.7–3.9 within a narrow boundary.
39. Prestandaanalys av värmepumpar – I olika byggnadstyper och driftsfall - E. Kapetanovic, Lund University (LTH) - 2025 - https://lup.lub.lu.se/student-papers/record/9215887 - thesis (simulation, abstract read) - Declared SCOP not representative in Swedish climate; 35/45/55 °C scenarios.
40. Improve efficiency: Turn the heat pump off (page 3) - OpenEnergyMonitor forum - 2022 - https://community.openenergymonitor.org/t/improve-efficiency-turn-the-heat-pump-off/13381?page=3 - forum - Arotherm 5 kW minimum 2.5 kW; mild-weather cycling observations; no controlled data.
41. Heat pumps and on/off working – starting to quantify it (page 10) - Renewable Heating Hub forum - 2023 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/heat-pumps-and-on-off-working-starting-to-quantify-it/paged/10 - forum - 7 kW Vaillant at 26 °C flow, daily COP 5.05; 2–3 cycles/h at 23 °C flow.
42. CPD Module 219: Air source heat pumps - CIBSE Journal - 2023 - https://www.cibsejournal.com/cibsejournal-magazine/202308/50/page.html - weak (quiz options only) - Lists "1 K lower flow = 1.5–3 % efficiency" as an answer option (not confirmed as correct).
43. Vorlauftemperatur Wärmepumpe - Bosch Home Comfort (DE) - n.d. - https://www.bosch-homecomfort.com/de/de/wohngebaeude/wissen/heizungsratgeber/waermepumpe/vorlauftemperatur-waermepumpe/ - manufacturer (search snippet only, not read) - Up to 2.5 % less electricity per degree lower flow.
44. Het verbruik van de warmtepomp, zelfs als het buiten vriest - id.nl - n.d. - https://id.nl/energie-en-klimaat/elektriciteit/energiezuinigheid/het-verbruik-van-de-warmtepomp-zelfs-als-het-buiten-vriest - blog (search snippet only) - Dutch installer rule: COP −2 % per K of water temperature.
45. Exergy analysis of an air-to-water heat pump (Journal of Environmental Engineering and Landscape Management) - VilniusTech - 2024 - https://btp.vilniustech.lt/index.php/JEELM/article/download/20771/12109 - paper (search snippet only; full text fetch failed) - 0 °C / 95 % RH: mean exergy efficiency 0.21, COP 1.49; actual COP 3.5–4.7× below Carnot.
46. GSHPA webinar: Electrification of Heat efficiencies - Ground Source Heat Pump Association - n.d. - https://mail.gshp.org.uk/pdf/GSHPA_Webinar_Series_Electrification_of_Heat_Efficiencies.pdf - slides (search snippet only; certificate error) - A0/W45: Carnot 7.1 vs typical ASHP 2.8 = 39 %.
47. Karlsson & Fahlén, variable-speed capacity control studies (Chalmers / SP) - Chalmers research portal - 2006 - https://research.chalmers.se/publication/152207 - paper (search snippet only) - Part-load COP improved but annual efficiency did not, because of inverter and motor losses.
48. Ten błąd przy ogrzewaniu podłogowym podnosi rachunki nawet o 20% - kb.pl - n.d. - https://kb.pl/aktualnosci/ogrzewanie/blad-przy-ogrzewaniu-podlogowym-a-rachunki/ - blog (search snippet only) - Polish rule of thumb: 1 K lower supply ≈ +2.5 % COP.
