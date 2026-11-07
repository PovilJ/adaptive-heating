# Hydraulics: flow rate, delta-T, pumps, buffers and their effect on efficiency and cycling

> **Research gap, read first.** The web-search budget shared by all 15 researchers was used up before this topic started. All 4 searches I tried were refused, so I ran **0 of the planned 25+ searches**. That includes the German, Polish, Swedish, Dutch and Lithuanian queries.
>
> To make up for it, I read **39 sources** another way:
> - pages and PDFs at URLs I already knew;
> - URLs listed in the other researchers' notes under `docs/research/notes/`;
> - primary documents other researchers had already downloaded to the shared scratchpad.
>
> I also ran my own analysis of the public **heatpumpmonitor.org dataset**: 576 systems, last 365 days, filtered for data quality.
>
> Non-English coverage therefore comes from documents rather than forum searches: German (Fraunhofer ISE, Viessmann, Wikipedia), Swedish (SBUF/KTH) and Lithuanian (VGTU, ENA). Heat Geek, Kensa and Heat Pump Monkey pages were mostly unreachable without search (404s and redirects). Hydraulics material from those sources is therefore missing.

## Summary

1. **This house already has a very large "buffer": the slab.** The slab stores about 6.6 kWh/K. A 150 L water circuit stores about 0.17 kWh/K, so the slab is roughly 38 times larger.
   - At minimum output (3.75 kW) against a 1.7 kW load, raising the slab by 1 K takes about 3.2 h. Losing that 1 K takes about 3.9 h.
   - That matches the observed 0.5–4 h runs. Water volume is not what limits run length here.
   - Lab and simulation work shows extra volume helps systems with **small, low-mass** circuits: a 50 L buffer took ASHP runs from 2.7 to 12.5 min and COP from 1.78 to 2.42 [21]. Simulation found 4–9 L/kW optimal [26].
   - This house is far beyond those volumes. **Do not add a buffer or volumiser.** High confidence.

2. **Buffers and low-loss headers do not raise COP in field data; they go with slightly hotter water and more starts.** heatpumpmonitor.org, last 365 days, my analysis [1]:

   | Hydraulics | Systems | Median combined COP | Weighted flow temperature | Starts per hour |
   |---|---|---|---|---|
   | No separation | 453 | 3.94 | 35.1 °C | 0.25 |
   | Buffer | 74 | 3.75 | 35.8 °C | 0.28 |
   | Low-loss header | 17 | 3.24 | 36.7 °C | 0.38 |

   - Within UFH systems only, buffers ran about 1.3 K hotter than direct systems (35.4 vs 34.2 °C), with a space-heating COP of 4.25 vs 4.46.
   - These are confounded observational data, not a controlled test. An engineer estimated that removing a buffer from a UFH design lowers the flow temperature by about 3–4 K [6]. That is an opinion, not a measurement.

3. **Mixing is the mechanism to check for.** If a header, buffer or **manifold mixing group** sits between the unit and the floor, the unit must make water hotter than the floor actually receives [12][29].
   - Many UFH manifolds in the Baltics come with a thermostatic mixing valve and their own pump. Such a group would by itself explain setpoints of 31–39 °C.
   - **Check:** compare manifold supply temperature with unit outlet during a steady run. A gap of more than about 1 K means mixing. High priority, cheap.

4. **Delta-T follows the load when flow is fixed. A small delta-T in mild weather is normal, not a fault.**
   - Heat = flow × 4.18 × ΔT [2][18]. The design spread for a 9 kW unit is 5 K, which needs about 26 L/min.
   - At that flow, the unit's 3.75 kW minimum gives a ΔT of only **about 2.1 K**.
   - Field reports put a normal ΔT at 2–6 K. DT5 is a design point, not a target [18][17].
   - EN 1264 UFH design uses a 5 K spread in the design room [34]. Fraunhofer measured mean spreads of 5.5 K and 6.8 K in older German homes [25].

5. **Lower ΔT means lower outlet temperature at the same mean water temperature.** That is worth about 1–2.5% COP per K of outlet:
   - 1.1%/K for a whole GSHP system [36];
   - 15–20% per 10 K of flow temperature [37];
   - about 0.10 SPF per K, roughly 2.5%/K at an SPF of 4, in field data [4];
   - "2–3% per degree" as a forum rule of thumb [12].

   Going from 5 K to 2 K ΔT lowers the outlet by about 1.5 K, roughly 2–4%. Doubling the flow costs pump power that grows steeply (theoretically by up to 8 times). For a pump of about 75 W [33] the net gain is close to zero.

   **Conclusion:** leave flow at the unit's automatic or default setting. Do not chase a low ΔT. Medium confidence.

6. **Cross-sectional field data does not show that high ΔT hurts COP.** In my regression across 387 systems [1]:
   - COP rises 0.08 per K of ΔT once lift and starts are held constant;
   - COP falls 0.085 per K of flow-minus-outdoor lift;
   - COP falls 0.25 per extra start per hour.

   In other words, lift and starts matter, and ΔT itself barely does. This contradicts simple theory (see Contradictions).

7. **Cycling penalty: what actually costs efficiency.**
   - heatpumpmonitor systems by average cycle length [1]:

     | Average cycle | Systems | Median space COP | % of Carnot |
     |---|---|---|---|
     | Under 30 min | 99 | 3.94 | 46% |
     | 30–60 min | 239 | 4.21 | 49% |
     | 1–2 h | 187 | 4.29 | 50% |
     | 2–4 h | 40 | 4.46 | 50% |

   - Systems starting **0.7 or more times per hour** had a median space COP of 3.5–3.8, against 4.3 below 0.4 per hour.
   - The lab found that runs under about 6 min hurt an ASHP badly. Runs of about 8 min came close to catalogue COP [21].
   - RHPP found 10-minute on-to-on cycling in 49% of ASHP sites but could not resolve a COP effect through metering noise [22][23].
   - **This house's runs of 0.5–4 h are in the "fine" band.** The bigger loss is likely the *temperature* of each run, not the number of starts.

8. **The 4 K restart hysteresis combined with proportional frequency control is a likely source of "hot" runs.** This is my inference, not tested.
   - Gree raises compressor frequency in proportion to (setpoint − outlet) [32].
   - With the pump running, outlet ≈ return ≈ slab water temperature while the compressor is off. To get a start, the setpoint must be at least 4 K above that.
   - So every start begins with a ≥4 K error, which pushes the compressor above minimum. Above minimum, condensing and outlet temperatures are higher and COP is lower: about 4.6 at 40 rps vs 3.3 at 110–120 rps for one Vaillant [6].
   - **Test:** set Word 30 to 2 K (the documented minimum) and trim the setpoint to outlet + about 1 K once the compressor is running.

9. **Keep the circulation pump running between compressor runs, but measure what it costs.**
   - Benefits: in standby the outlet/return reading becomes a live **slab-temperature sensor**, and slab heat is evened out between loops.
   - Gree appears to run the pump in standby [33], and its pump control varies speed with ΔT [32].
   - Cost: up to about 75 W [33]. Running at full speed for 24 h on a +10 °C day is 1.8 kWh, about **20% of that day's compressor electricity** (about 9 kWh).
   - The UK EoH trial measured an average of only **146.5 kWh/yr** for circulation pumps, which moved SPF by only 0.01–0.02 [24]. RHPP still flagged always-on pumps as a parasitic fault [23].
   - Daikin offers continuous, sampling (pump every 5 min) and request modes. It says continuous uses the most energy [27].
   - **Measure pump power in standby before deciding.**

10. **UFH balancing has a small direct effect. Its value is in allowing a lower flow temperature.**
    - Balancing alone saves little. Savings of about 7–11% come only when the flow temperature is then lowered [35].
    - Pumps were found to be about 3 times larger than needed on average (OPTIMUS, 92 buildings) [35].
    - Gree's own guidance: loops of 100–120 m or less, of equal length, at most 8 loops per manifold, loop velocity 0.25–0.5 m/s [32]. Danfoss: no more than 250 mbar loss, loop length 100 m (110 m maximum) [34].
    - In a single-zone slab with a weather-led or planned setpoint, the aim is "every loop open and roughly equal". Room-by-room precision does not matter.

11. **Minimum volume and minimum flow are safety constraints, not efficiency levers.**

    | Brand | Minimum volume | Minimum flow |
    |---|---|---|
    | Gree Versati III mono | 20 L | — [33] |
    | Daikin LT split | 10–20 L | 12–15 L/min during defrost [27] |
    | Samsung Gen 6 | 30 L | over 16 L/min [29] |
    | Panasonic SXC | 50 L | — [30] |
    | Viessmann 250-A | (own 16 L buffer) | at least 1000 l/h during defrost [28] |
    | Vaillant | — | at least 35% of nominal [31] |

    A slab UFH circuit with all loops open far exceeds all of these. **Never let actuators close all loops.** On the Gree, a flow-switch trip needs a power cycle to clear [33].

12. **Defrost draws heat from the water.** Slab UFH supplies plenty of it, as long as flow is not throttled [27][28][16].

13. **Cheap checks using only outlet and return temperatures.** Details are in the implications section.
    - (a) ΔT during a steady run at minimum output, which gives the flow rate;
    - (b) how quickly return rises after a start, which reveals any short-circuit or mixing;
    - (c) the rate of return rise over hours, which gives slab capacity;
    - (d) outlet minus manifold supply, which reveals mixing;
    - (e) return in standby, which gives slab temperature.

## Detailed findings

### 1. Basic hydraulics: flow, ΔT and heat

- **Equation.** Heat (W) = 4180 J/kg·K × flow (kg/s) × ΔT (K) [2][18].
  - Worked examples: 15 L/min at 5 K gives 5.25 kW. An 8.5 kW unit at 5 K needs 24 L/min [2].
  - Glycol has a specific heat of about 3.8 instead of 4.2. It needs more flow or a wider ΔT and is "always slightly less efficient" [18].
- **ΔT is not a fixed target.**
  - Energy Stats calls DT5-everywhere a myth. They describe 2–6 K as normal, narrower on mild days and wider in cold weather [18].
  - Vaillant aroTHERM nominal fixed flows are about 860 L/h (3.5/5 kW), 1200 L/h (7 kW) and 2000 L/h (10/12 kW). A measured mild-weather example ran 34.4/31.0 °C, ΔT 3.4 K, delivering 3.4 kW [18].
  - Vaillant sets the available pump head so that "nominal flow" is achieved at ΔT 5 K. Head is adjustable between 20 and 90 kPa, and pump output between 50% and 100% or Auto [31][18].
- **Pumps that control ΔT.**
  - Daikin's pump speed holds a set entering/leaving difference: 3–10 K, default 5 K [27]. A separate pump-speed limit applies "when no heating output", and the manual says not to change it [27].
  - Gree: the inverter pump "first runs at initialized speed then adjusts" to the entering/leaving difference, faster when the difference is larger [32]. The target ΔT is not documented. No pump-mode setting was found in any Versati panel manual [33].
- **Mild-weather field table** (forum, users' own graphs) [17]:

  | Unit | Flow behaviour | ΔT | Behaviour at low load |
  |---|---|---|---|
  | 8 kW Daikin | modulates 24 → 7 L/min | 3.5–5 K | ran down to about 1.6 kW without cycling |
  | 10 kW Viessmann | 28 → 15 L/min | about 3.3 K | about 3.8 kW minimum, cycled regularly |
  | Grant Aerona | about 34 L/min fixed | 1.6 K at 5 °C outdoor | 3.8 kW, "large peaks, short runs" |

  - A 12 kW Samsung ran continuously below 5 °C outdoor and switched on and off above that, with 40–60 min cycles.
  - **Interpretation.** The low-cycling units are the ones with a lower *minimum output*. Flow modulation is a symptom of good part-load design, not the cause [16][17].
- **Minimum output scales with minimum flow on Vaillant.** Measured minimum output roughly equals minimum flow × 5 K × 4150 J/kg·K on Vaillant units, but not on a 9 kW Grant R290 [9].
  - Measured minimum for a 10 kW Vaillant: about 5.9 kW [9]. Energy Stats lists 2.2 kW (3.5/5 kW), 3.2 kW (7 kW) and 5.8 kW (10/12 kW) [19].

### 2. Delta-T, outlet temperature and COP

- **What the compressor sees is the outlet temperature.** For a given room load, the emitter needs a certain *mean* water temperature. Outlet = mean + ΔT/2. A larger ΔT therefore raises outlet and condensing temperature for the same heat delivered.
- **Sensitivity of COP to flow temperature:**
  - field regression: SPF falls about 0.10 per K of weighted flow temperature (R² 0.52), and about 0.105 per K of flow-minus-outdoor (R² 0.55) [4]. At SPF 4 that is about 2.5%/K;
  - Swedish simulation for a GSHP system: system SPF improves about **1.1% per K** of lower flow temperature between 50 and 35 °C [36];
  - SBUF/Bengt Dahlgren 2024: each 10 K reduction cuts purchased electricity by about **15–20%** [37];
  - forum rule of thumb: 2–3% per K [12], marked as informal.
- **Trading ΔT against pump energy (my calculation).**
  - For a 9 kW unit at its 3.75 kW minimum: 26 L/min gives ΔT 2.1 K; 13 L/min gives 4.1 K; 10 L/min gives 5.4 K.
  - Halving the flow from 26 to 13 L/min raises the outlet by only about 1 K at the same mean temperature, roughly 1.5–2.5% of COP.
  - On about 0.8 kW of compressor input, 2% is about 16–20 W. Pump power at half flow could fall by tens of watts (the affinity laws give about one eighth of the hydraulic power, though real pump curves fall less).
  - **The two effects roughly cancel.** Neither "max flow" nor "min flow" is clearly better at minimum output. At high output in cold weather a wider ΔT costs more, because 9 kW at 13 L/min means a 10 K spread.
- **Cross-sectional field data does not show a ΔT penalty.** Median combined COP by weighted ΔT bin, with weighted flow temperature in brackets [1]:

  | ΔT bin | Systems | Median COP (flow temperature) |
  |---|---|---|
  | under 3 K | 75 | 4.21 (31.7 °C) |
  | 3–4 K | 226 | 4.07 (34.2 °C) |
  | 4–5 K | 175 | 3.73 (36.5 °C) |
  | 5–6 K | 68 | 3.66 (37.6 °C) |
  | 6–8 K | 18 | 3.55 (38.5 °C) |

  - Raw, this looks like "small ΔT is good". But the small-ΔT systems also run much cooler.
  - A multiple regression on 387 systems: space COP = 6.36 − 0.085 × (flow − outdoor) − 0.25 × starts/h + 0.08 × ΔT.
  - With temperatures held constant, ΔT has a small *positive* coefficient. Low-ΔT systems do well because they are low-temperature systems, not because of ΔT itself.
  - % of Carnot was flat across ΔT bins at 47–49%.
- **Lithuanian field data point.** VGTU measured a 15.9 kW unit near Vilnius: UFH, 100 L buffer, heat-recovery ventilation, 175 m² [38].
  - It cycled 3–4 times per hour with 4–6 min runs in the mildest period, 2–3 per hour and 2 per hour in colder periods.
  - The prevailing momentary COP was 3.7–3.9, excluding the circulation pump and controls.
  - The buffer did not stop short runs: the unit was heavily oversized for the house.

### 3. Low-loss headers, buffers and mixing

- **How mixing works** [12]:
  - If secondary flow exceeds primary flow, cooler secondary return mixes into the flow. The emitters see colder water than the unit makes, so the unit must run hotter.
  - If primary flow exceeds secondary flow, hot primary flow short-circuits into the unit's return. The return rises and the unit's ΔT shrinks. An outlet-controlled unit then reaches setpoint sooner and stops, which means more cycling.
  - Either way a header adds a pump, controls and a place for mismatch.
  - The forum article accepts headers or buffers for small low-mass radiator circuits, multiple heat sources, very small secondary circuits and legacy systems. Otherwise they should "follow from a calculation" [12].
- **Field evidence, heatpumpmonitor** (my analysis, n = 576, last 365 days, data-quality filtered) [1]:

  | Hydraulic separation | Systems | Combined COP | Space COP | % Carnot | Weighted flow temp | ΔT | Starts/h |
  |---|---|---|---|---|---|---|---|
  | None | 453 | 3.94 | 4.25 | 48.9 | 35.1 °C | 3.85 | 0.25 |
  | Buffer | 74 | 3.75 | 4.17 | 50.6 | 35.8 °C | 3.96 | 0.28 |
  | Low-loss header | 17 | 3.24 | 4.01 | 47.9 | 36.7 °C | 4.27 | 0.38 |
  | Volumiser fitted | 137 | 3.76 | 4.12 | 47.5 | 35.9 °C | 4.10 | 0.21 |

  - UFH systems only: no separation (n = 159) space COP 4.46, lift 26.1 K, flow 34.2 °C. Buffer (n = 34): COP 4.25, lift 27.8 K, flow 35.4 °C. Low-loss header (n = 9): COP 4.51, lift 28.8 K, flow 35.3 °C, **0.54 starts/h**.
  - Caveats: self-reported metadata, mostly UK, heat meters on the unit side (so buffer standing losses are partly *outside* the metered COP), confounding by installer quality, and small header samples.
- **Lab.** EA Technology, for the UK government (DECC), 2012 [21]:
  - Setup: a 4-pipe, 50 L buffer, sized for an 8 min worst-case run at about 8 L/kW.
  - One radiator open, ASHP: COP 1.78 at 2.7 min runs without buffer, 2.42–2.62 at 10.8–12.5 min runs with buffer.
  - Two radiators open: runs were already about 6 min without buffer, and the buffer gave little or no gain (2.29–2.69 vs 2.45–2.60). The authors called this case inconclusive.
  - Recommendation: design for at least about 6 min runs, with an optimum around 10–15 min (GSHP). About 8 min gave near-catalogue COP for the ASHP.
  - On warm days the buffer's own heat loss caused cycling with no heating demand. A thermostat interlock was needed.
- **Simulation.** Dongellini, PhD thesis, Bologna 2017 [26]:
  - A buffer in the return line minimises cycling.
  - Optimal stored-water to rated-capacity ratio: **7–9 L/kW** for an on-off unit, **4–7 L/kW** for a modulating unit, and **about 15 L/kW** for an indirect, variable-secondary-flow layout.
  - A 120 L tank raised an on-off system's SCOP by about 11%.
  - An indirect (separated) layout with *constant* secondary flow gave **no** energy saving over a direct connection.
  - For two of the four layouts, the pipe inertia alone kept starts under 6 per hour.
- **Field.** Fraunhofer ISE "WPsmart im Bestand" [25]:
  - 21 of 29 ASHPs (and 9 of 12 GSHPs) had a heating buffer, averaging 249 L.
  - Estimated standing loss: about 4.1% of space-heating heat, at a 37.2 °C mean store and 13 °C ambient.
  - Mean space-heating spreads were 5.5 K (3.0–7.8) and 6.8 K (3.2–9.8) in two sub-groups.
  - In several systems, a change in flow rate shifted the flow temperature, because the unit was controlled on return temperature. A flow rate below one tenth of normal produced a very large spread. **Flow rate and control sensor interact.**
- **Manufacturers.**
  - Samsung Gen 6 (UK distributor manual) requires a primary *and* a secondary pump to guarantee flow, unless a header or buffer is used. It bans mixing sets on UFH manifolds unless a boiler or backup is present [29].
  - Viessmann 250-A uses an integrated 16 L buffer plus a 4/3-way valve, which guarantees more than 300 l/h through the unit (more than 1000 l/h during defrost). An *external* buffer of at least 200 L is only required for radiator-only systems with utility lockout [28].
  - Gree does not require a buffer [33].
- **Volumisers lengthen cycles but do not change the on/off ratio** when minimum output exceeds load [15][16].
  - Example: an 8 kW Midea with about 40–50 L of UFH water had 5–17 min runs. Adding an 80 L series tank and pump gave 40–50 min. Switching the stop condition to a tank sensor gave 2–3 h runs [15].
  - Forum figure: 40 L for 8 kW (about 5 L/kW) is low, compared with about 200 L on a 7 kW system [15].

### 4. Minimum system volume, defrost and minimum flow

- **Calculation.** Minimum volume = minimum output × minimum on-time / (c × target ΔT). The OpenEnergyMonitor simulator uses this, with a 5–10 K target ΔT [3].
  - Example (EA Technology): 6.7 kW output, 0.7 kW load, 10 K band, 22 L open circuit plus 50 L buffer gives about 8 min [21].
- **Manufacturer minimums** (all far below a slab UFH system's water content):

  | Unit | Minimum volume | Other requirement |
  |---|---|---|
  | Gree Versati III monobloc | 20 L (default design volume 44–66 L) | — [33] |
  | Daikin LT split | 10 L (04/08), 20 L (16), excluding indoor unit | 12–15 L/min during defrost or backup heater; keep 1 UFH loop never closed [27] |
  | Samsung Gen 6 | 30 L | above 16 L/min [29] |
  | Panasonic SXC9/12 | 50 L | otherwise add a buffer [30] |
  | Vaillant | — | flow at least 35% of nominal, else fault S.275 [31] |
  | Viessmann | — | at least 1000 l/h through the unit during defrost [28] |

- **Water content of UFH.** About 0.113 L per metre of pipe [34]. 1000 m of loops holds about 113 L, before counting the slab.
- **Defrost.** Volume "carries the unit through defrost" [16]. Sufficient flow is required on each zone, even with valves closed [27]. With an open slab circuit, defrost cools the return by a few K and nothing more.

### 5. Circulation pumps: speed, electricity and running between compressor runs

- **Pump electricity, measured:**
  - EoH (UK, 353 ASHP/hybrid systems): average circulation-pump use **146.5 kWh/yr**. Adding it to sites with missing readings moved average SPF H2 by +0.021 and H3 by +0.011 [24];
  - Gree all-in-one integrated pump: about 75 W, 85 W on larger units [33];
  - Daikin, one user: about 180 W when the pump runs only to sample flow temperature [5];
  - radiator system with a K2 store: about 200 W, so the owner switched the pump off between cycles [8].
- **Pump oversizing.** The OPTIMUS study (92 buildings) found pumps on average about 3 times larger than needed [35].
- **Continuous or intermittent.**
  - Daikin lists three modes for when no heating is called. Continuous costs the most energy; sample runs the pump every 5 min to check water temperature; request is the default [27].
  - RHPP found sites with the pump on all year and called it high parasitic consumption, possibly a commissioning fault [23]. Pump over-run also inflated heat-meter readings at some sites [22].
  - Energy Stats notes that Vaillant keeps water circulating at lower speed during off periods [18].
  - The Gree manuals suggest the pump runs in standby (the "other thermal" logic). After a compressor stop the pump runs 120 s longer in some shutdown sequences [32][33].
- **Why keep circulating in a slab house (reasoning plus [8][27]):**
  1. The outlet/return sensors then read *slab water temperature*. That is the best state signal the controller has.
  2. Heat moves from warmer areas (sunny rooms, freshly heated loops) to cooler ones.
  3. In a monobloc with outdoor water pipes, still water cools quickly. The outlet reading falls, which can trigger a restart (Gree restarts on setpoint − outlet ≥ ΔT-heat). In frost it triggers anti-freeze runs: below 3 °C water the pump starts and the compressor follows 30 s later [33].
  - Cost: up to 1.8 kWh/day at 75 W (see Summary 9). The real standby speed is unknown.
- **Sampling compromise.** Running the pump for a few minutes every 15–30 min gives the same state information at a fraction of the energy. Gree exposes no pump-mode setting [33]. The only way to get this would be external control of the pump supply, which risks flow-switch errors. Not recommended without testing.

### 6. UFH design and balancing

- **EN 1264 practice (Danfoss handbook)** [34]:
  - design spread σ = 5 K in the room with the highest load;
  - other rooms have a different spread at the same flow temperature;
  - circuits of 100 m (110 m maximum);
  - pressure drop of 250 mbar or less per circuit;
  - flow set at the return valve in l/min;
  - maximum 55 °C for cement screed.
- **Gree UFH guidance** [32]: loops of 100–120 m or less and equal in length; at most 8 loops per manifold (two manifolds above 12); manifold velocity below 0.8 m/s; loop velocity 0.25–0.5 m/s.
- **Balancing** [35]:
  - On its own it mostly improves comfort.
  - Energy savings (7–11%, ITG Dresden meta-study; about 7% across 555 church buildings) appear when the flow temperature is lowered afterwards.
  - Unbalanced systems need a higher flow temperature or a bigger pump to satisfy the worst room. In low-temperature systems, emitter self-regulation reduces, but does not remove, the need to balance.
- **UFH flow example** (Mitsubishi, forum) [14]:
  - design 7.2 L/min (1 L/min per room); measured 9.8 L/min with uneven loops of 1.5 to over 2 L/min;
  - pump speed 5 gave about 14 L/min and speed 2 about 9 L/min, against a unit optimum of 9 L/min (range 6–14);
  - return rose through each run until the outlet hit the 30 °C target, then the unit stopped.
- **Swedish study** [36]: UFH with a 5 K spread delivers the same heat as panel radiators (10 K spread) at **about 15 K lower** flow temperature. Flow temperature is set mainly by the building's heat demand, not by how efficient the emitter is.
- **Manufacturer tip** (eco+Logic, NZ, a weak source): with slab UFH, staggering zone switch-on times reduces peak load. Setbacks should be small, about 2 K on floor sensing.

### 7. How hydraulics drive high flow temperatures and short cycling

Mechanisms, in rough order of how often they show up in the sources:

1. **Mixing between unit and emitter:** a header, buffer, manifold mixing group, or primary/secondary flow mismatch [12][29][6].
2. **Emitter cannot shed the minimum output.** Return rises, ΔT collapses, outlet reaches setpoint plus overshoot, and the unit stops [16][14][10]. One forum member: at 30 °C flow, restart came with return about 26 °C after a 3–5 min off period [16].
3. **Too little open volume or flow:** zone valves or TRVs closing [21][27][29].
4. **High weather curve or setpoint with an on/off room thermostat** ("demand cycling", for example an hour on and an hour off). This is the main efficiency loss according to [7]. Brief "load cycling" at minimum modulation is acceptable [7].
5. **Fixed high pump speed in mild weather** gives a ΔT of about 1.6–2 K and quick stops [17]. The evidence is mixed: it is confounded with the minimum output.
6. **Return-temperature control combined with variable flow** shifts the flow temperature unpredictably [25].
7. **Buffer heat loss** causes cycling with no demand [21].

### 8. Cycling costs (for context; covered in more depth by other notes)

- **Lab** [21]: ASHP COP 1.78 at about 2.7 min runs vs 2.42–2.62 at 11–12.5 min (one radiator open, about 48 °C flow). For a GSHP the worst-case loss was about 16%.
- **Field, RHPP** [22][23]:
  - A median on-to-on period of 10 min was common: 49% of ASHP sites had at least one month like that. 25% of ASHPs had at least 10% of cycles under 12 min all year.
  - No monthly-COP correlation could be shown, possibly hidden by metering error.
- **heatpumpmonitor** [1]: COP falls with shorter cycles and more starts (Summary 7). The same regression gives −0.25 COP per start/h.
- **Forum measurements:**
  - a 14 kW Ecodan in mild weather showed *higher* COP while cycling (4.4–4.5 vs 3.9). This was not like-for-like [13];
  - stopping a radiator system's pump and compressor between runs raised COP from 2.58 to 3.32 at a 9 °C average [8].
  - Both show that **long low-temperature runs plus genuine off periods can beat continuous running at above-minimum output**.

### 9. Lithuanian context

- **ENA (Lithuanian Energy Agency) 2025** buyer guide (listed under "Additional material" at the end of Sources): generic. It mentions buffer tanks and correct sizing without numbers. I skimmed it only and do not cite it in detail.
- **VGTU 2009 Vilnius field study** [38]: underfloor heating, heat-recovery ventilation and a 100 L buffer behind an oversized 15.9 kW unit. Result: 3–4 starts per hour of 4–6 min each in mild periods.
  - It shows that a buffer does not cure oversizing.
  - It also shows the classic Lithuanian installation (buffer plus UFH) still short-cycles.

## What this means for controlling this house

The house: 9 kW Gree Versati, minimum output about 3.75 kW, 0.14–0.20 kW/K heat loss, a 6.6 kWh/K slab, one zone, Modbus flow setpoint, and a restart when setpoint − outlet ≥ 4 K (Word 30 = 4).

**A. Hydraulic layout. Find out what is there first.** High priority, low effort.
1. **Look for a mixing group or second pump at the UFH manifold**: a thermostatic or motorised 3-way valve with its own circulator, or a header or buffer anywhere between the unit and the manifold.
   - **Test:** during a steady run of at least 30 min, log unit outlet and manifold supply. Clip-on probes under insulation are enough.
   - If manifold supply is more than about 1 K below unit outlet, there is mixing or pipe loss.
   - If a mixer exists, set it fully open (pass-through) and let the heat-pump setpoint do the job. Expect 2–5 K lower setpoints for the same comfort [6][12]. Confidence that this matters *if present*: high. Whether it is present: unknown.
2. **Do not add a buffer, volumiser or low-loss header.** The slab already provides hours of run time (Summary 1). A tank adds standing losses of about 4% [25], mixing and more starts [1][21]. Confidence: high.
3. **Keep every UFH loop permanently open.** No room actuators. Minimum flow and volume need it for defrost [27][33], and a Gree flow-switch trip needs a power cycle [33].
4. **Balance once.** Set loop flows roughly in proportion to loop area or length. Then check floor surface temperatures with an IR thermometer during a long run: aim for every room within about 1–2 K.
   - Then lower the setpoint until the coolest room just holds 22 °C. That is where balancing pays [35].

**B. Flow rate and ΔT.** Medium confidence.

5. **Leave the Gree pump on its automatic ΔT-based speed.** There is no setting to change anyway [33].
   - Expect a ΔT of about 2–3 K at minimum output and 4–6 K at full output in cold weather. Both are normal [18][17][25].
   - Do not treat a small ΔT in mild weather as a fault.
6. **Use ΔT to estimate the real flow once.** At minimum output (about 3.75 kW, low compressor Hz, steady):
   - flow (L/min) ≈ 3.75 × 60 / (4.18 × ΔT): ΔT 2 K ≈ 27 L/min, 3 K ≈ 18 L/min, 4 K ≈ 13 L/min, 5 K ≈ 11 L/min.
   - Below about 12 L/min, check filters and air: the Gree catalogue hints at a 12 L/min limit [33], and Daikin and Samsung need 12–16 L/min [27][29].
   - Better still, use the unit's power or Hz registers with an estimated COP to get heat output.
7. **Do not raise pump speed to "fix" cycling.** It cannot change minimum output against load [15][16].

**C. Pump in compressor-off periods.**

8. **First measure pump power in standby.** Use coil 175 (pump on) together with whole-unit power at 0 Hz [33]. Decision rule:
   - 20 W or less: leave it continuous. It costs about 0.5 kWh/day, and the outlet/return reading becomes a live slab sensor.
   - 50 W or more: it costs over 1.2 kWh/day, which is 10–20% of mild-day consumption. The saving would come from fewer standby hours (longer, rarer runs; see D), not from cutting the pump's supply.
9. **Use the standby outlet/return reading as the controller's slab-temperature state.** Wait about 10–15 min after a stop for the water to cycle through the loops: at about 18–27 L/min, 113–150 L takes about 4–8 min per pass.

**D. Start and run behaviour.** This is where hydraulics meets control. It is the most promising lever but **unverified**.

10. **Why the setpoints are high.** With the pump running in standby, outlet ≈ slab water temperature (about 26–28 °C on a mild day). With Word 30 = 4, the unit only starts once the setpoint is at least slab + 4 K, so roughly 30–32 °C.
    - Gree's proportional frequency control [32] then sees a ≥4 K error and runs the compressor above minimum. That raises outlet temperature and electrical draw (the observed catch-ups of about 3 kW at +2 °C).
    - Once running at minimum, the slab only needs about return + 2 K.
11. **Test 1: Word 30 = 2 K** (the documented minimum of the 2–10 K range [33]).
    - This lowers the starting error and therefore the start burst.
    - Risk: the unit may restart on its own between planned runs.
12. **Test 2: lower the setpoint after the start.** Write the start setpoint; once the compressor is confirmed running (Hz above 0 for 6 min or more, past Gree's capacity hold [33]), drop the setpoint to about current outlet + 0.5–1 K. Then track the rising return.
    - Expected result: the compressor settles near minimum Hz, outlet about 1–3 K lower, COP about 3–8% higher.
    - Stop condition: Gree stops when outlet overshoots setpoint. Hold the setpoint at least about 1 K above outlet to avoid an unintended stop.
    - Measure: Hz, electrical power, outlet, return and run length. Compare A/B days at similar outdoor temperature.
13. **Plan fewer, longer runs at minimum output; let the slab carry the off periods.**
    - At +10 °C the house needs about 41 kWh of heat per day, which is about 11 h at 3.75 kW. One or two runs per day (for example, sized to the PV window) give a slab swing of about (3.75 − 1.7) × 5.5 h / 6.6 ≈ 1.7 K per run.
    - Whether that slab swing is acceptable as a room swing has to be measured. The room probably swings much less. Other notes cover this.
    - From a hydraulic point of view this is ideal: no volume problem, runs of 4 hours or more [1][21].
14. **Hot-water interruptions.** After a hot-water cycle, primary water at about 45–55 °C returns to the floor loop. The outlet then reads high, so the unit will not restart until it has cooled.
    - Schedule hot water at the *end* of a heating run, or in the PV window, not in the middle of one.
    - Do not count the hot-water slug as "slab temperature".

**E. Owner checks using only outlet and return temperatures** (with Hz and power if available):

| Check | How | What it tells you |
|---|---|---|
| Flow rate | ΔT at steady minimum output; flow ≈ Q / (4.18 × ΔT) | Pump and flow health (expect about 13–27 L/min) |
| Short-circuit or mixing | After a start, how fast return follows outlet. In a direct slab circuit, return should lag by about one water transit (≈5–10 min) and then rise only slowly | A return that jumps within 1–2 min points to a bypass, header or few open loops |
| Slab capacity | Return rise rate over a long run (K/h) × 6.6 kWh/K should ≈ heat input − house load | Confirms the 6.6 kWh/K model; a much faster rise suggests closed loops |
| Mixing at the manifold | Unit outlet vs manifold supply | More than 1 K means mixing or losses |
| Emitter conductance | In a steady long run: K_em ≈ Q / (mean water temp − room) | Lowest feasible outlet ≈ 22 + 3.75 / K_em + ΔT/2 for running at minimum |
| Slab state | Return 10–15 min into standby | Controller input |
| Start burst | Hz and power in the first 10–20 min vs set error | Tests the proportional-control effect (D10–12) |

**Confidence summary:**
- no buffer: high;
- check for a manifold mixer: high value, unknown presence;
- leave pump speed alone: medium;
- pump-standby cost: unknown until measured;
- start-burst mechanism and setpoint trimming: plausible but untested, medium-low;
- slab as buffer and run-length arithmetic: high, since it follows from measured house parameters.

## Contradictions and open questions

1. **Does a small ΔT help or not?**
   - Theory and forum: lower ΔT means lower outlet, which means better COP (2–3%/K [12]).
   - My cross-section of 387 systems: ΔT has a slightly *positive* coefficient on COP once lift and starts are held constant [1].
   - Field reports: well-behaved units modulate flow *down* in mild weather, which widens ΔT [17].
   - Resolution offered: the effect is small (about 1.5 K of outlet) and offset by pump power and plate-heat-exchanger effects. Not settled.
2. **Buffers: helpful or harmful?**
   - Lab and simulation: helpful for low-volume circuits. COP 1.78 → 2.42 [21]; SCOP +11% with 120 L [26].
   - Field cross-section: slightly worse, with hotter water and more starts [1]. Forum: often installed by default and harmful [12].
   - Both can be true: buffers fix very small circuits and hurt circuits that are already large. This house has a very large circuit.
3. **The 120 L buffer in [26] gave +11%, yet indirect layouts with constant secondary flow gave no saving.** The gain came from volume, not from separation.
4. **Measured 15–16% COP gains from cycling** [13][8] versus 25% COP losses from short cycling [21]. Both are compatible: what matters is cycle length *and* the temperature at which the unit runs. Short sub-6 min cycles are bad. Long cycles at minimum output with real off periods can beat continuous running at above-minimum output.
5. **Is the Gree pump really continuous in standby, and at what speed and wattage?**
   - The manuals imply it runs in standby [33]; in a shutdown the pump stops 120 s after the compressor [32].
   - These may describe different modes. Measure coil 175 and power.
6. **Gree's pump ΔT target and true flow.** Neither is documented. The catalogue's "limit LPM 12" is unverified [33].
7. **Does the Gree frequency law really push the compressor above minimum at start with a 4 K error?**
   - [32] says frequency is proportional to the temperature difference, but gives no gain and no ramp. There is also a ~6 min capacity hold at start [33].
   - Needs Hz logging around starts, comparing Word 30 = 4 against 2.
8. **Slab-to-water heat transfer.** How much higher than slab temperature must the outlet be for the slab to accept 3.75 kW? This is the emitter conductance, which is unknown and sets the lowest efficient setpoint. Measure it (check E5).
9. **Is there a manifold mixing group?** This could be the single biggest hydraulic issue. It is unknown from this desk research.
10. **Search gap.** No web searches could run, so these went unread:
    - German forum material on hydraulic balancing and continuous pump running (haustechnikdialog, photovoltaikforum);
    - Polish material on buffer cycling (elektroda, muratordom);
    - Swedish/Norwegian material on pump "always on" settings (NIBE/Thermia pump-speed menus);
    - Heat Geek and Kensa guidance on headers and buffers.

    A follow-up session with search budget should fill these.

## Sources

1. heatpumpmonitor.org public system list and last-365-day statistics. OpenEnergyMonitor, 2026. https://heatpumpmonitor.org/system/list/public.json and https://heatpumpmonitor.org/system/stats/last365. **Field data (my analysis).** 576 quality-filtered systems with at least 2000 kWh of heat: COP, flow temperature, ΔT and starts/h by hydraulic separation, volumiser, UFH, ΔT bin and cycle length; OLS regressions.
2. "Useful equations". OpenEnergyMonitor docs. Undated (accessed 2026). https://docs.openenergymonitor.org/heatpumps/basics.html. **Blog/reference.** Heat = c × flow × ΔT, worked examples (15 L/min at 5 K = 5.25 kW; 8.5 kW at 5 K = 24 L/min).
3. "Heat pump volume / cycling COP simulator". OpenEnergyMonitor. Undated. https://openenergymonitor.org/tools/volume_sim_cop. **Tool/model.** Minimum-volume formula (minimum output × minimum on-time / (c × ΔT)), 5–10 K target ΔT.
4. "HeatpumpMonitor.org: low temperature". OpenEnergyMonitor docs. About 2024–2025. https://docs.openenergymonitor.org/heatpumpmonitor/low_temperature.html. **Field data.** SPF vs flow temperature (−0.10/K) and vs flow-minus-outdoor (−0.105/K) regressions.
5. "HeatpumpMonitor.org: starts / starts per hour" thread. OpenEnergyMonitor forum. 2024. https://community.openenergymonitor.org/t/heatpumpmonitor-org-starts-starts-per-hour/26246. **Forum/field.** Start-detection method; Vaillant 1.29 starts/h lifetime; Daikin pump about 180 W during sampling runs.
6. "HeatpumpMonitor.org findings" thread. OpenEnergyMonitor forum. 2025. https://community.openenergymonitor.org/t/heatpumpmonitor-org-findings/28164. **Forum/field.** Estimate that removing a buffer lowers UFH flow temperature by 3–4 K (opinion); COP 4.6 at 40 rps vs 3.3 at 110–120 rps example.
7. "Heat pump demand cycling vs compressor load cycling". OpenEnergyMonitor forum. 2025. https://community.openenergymonitor.org/t/heat-pump-demand-cycling-vs-compressor-load-cycling/29277. **Forum.** Demand-cycling vs load-cycling distinction; Samsung pause mechanics; 30 min/3 min pause pattern.
8. "Improve efficiency – turn the heat pump off". OpenEnergyMonitor forum. 2020–2022. https://community.openenergymonitor.org/t/improve-efficiency-turn-the-heat-pump-off/13381. **Forum/field.** Forced off-periods with the pump (about 200 W) stopped: space COP 2.58 → 3.32 at 9 °C average.
9. "Heat pump database: minimum modulation tests". OpenEnergyMonitor forum. 2025. https://community.openenergymonitor.org/t/heatpumpmonitor-org-heat-pump-database-minimum-modulation-tests/29132. **Field.** 10 kW Vaillant minimum about 5.9 kW; minimum output ≈ minimum flow × 5 K × c on Vaillant.
10. "Heatpump turning on and off, is this normal?" OpenEnergyMonitor forum. 2022. https://community.openenergymonitor.org/t/heatpump-turning-on-and-off-is-this-normal/22149. **Forum.** UFH at 48 °C cycling; 40 °C setpoint cut daily kWh from 60 to 45; a slow-accepting slab raises return.
11. "Weather compensation ASHP duty cycle". OpenEnergyMonitor forum. 2023. https://community.openenergymonitor.org/t/weather-compensation-ashp-duty-cycle/24793. **Forum.** Duty cycles of 50–70% at 12 °C; fixed 3 min 15 s off periods; a buffer cooling overnight.
12. "Avoid the heat pump villain: why low loss headers and buffers can sabotage your heat pump's efficiency". Renewable Heating Hub forum (admin article plus discussion). 2025. https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/avoid-the-heat-pump-villain-why-low-loss-headers-and-buffers-can-sabotage-your-heat-pumps-efficiency/. **Blog/forum.** Header and buffer mixing mechanisms, valid use cases, "2–3% per degree" rule of thumb, test method.
13. "Heat pump truth or myth 2: cycling uses a lot of power and ruins your COP". Renewable Heating Hub. 2023. https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/heat-pump-truth-or-myth2-cycling-uses-a-lot-of-power-and-ruins-your-cop/. **Forum/field.** 14 kW Ecodan cycling COP 4.4–4.5 vs 3.9 steady (not like-for-like).
14. "Running ASHP efficiently, general thought process (low and slow)", page 2. Renewable Heating Hub. 2024. https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/runing-ashp-efficiently-general-thought-process-low-and-slow/paged/2. **Forum/field.** UFH loop flows, pump speed vs L/min, return rising until stop.
15. "Inventor (Midea) heat pump short cycling advice". Renewable Heating Hub. 2025. https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/inventor-midea-heat-pump-short-cycling-advice. **Forum/field.** Volume lengthens cycles but not the on/off ratio; 5–17 min runs → 40–50 min with an 80 L tank → 2–3 h on a tank sensor.
16. "Ecodan: is there actually such a thing as a minimum flow temp to avoid cycling?", page 2. Renewable Heating Hub. 2024–2025. https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/ecodan-is-there-actually-such-a-thing-as-a-minimum-flow-temp-to-avoid-cycling-and-why-if-so/paged/2/. **Forum.** Emitter must shed minimum output; return rise; restart at about 26 °C return; volume and defrost.
17. "Performance of heat pumps in mild weather". Renewable Heating Hub. 2024–2025. https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/performance-of-heat-pumps-in-mild-weather. **Forum/field.** Table of flow rates, ΔT, minimum outputs and cycling for Vaillant, Samsung, Viessmann, Daikin, Grant and Ecodan units.
18. "DT and mass flow rate". Energy Stats UK. About 2024–2025. https://energy-stats.uk/mass-flow-rate/. **Blog.** 2–6 K ΔT is normal; DT5 is a myth; aroTHERM nominal flows; pump 50–100%/Auto settings; glycol effect.
19. "Heat pump cycling". Energy Stats UK. About 2024–2025. https://energy-stats.uk/heat-pump-cycling/. **Blog.** Minimum-output table, cycle-point calculation, cycles-per-hour rule of thumb; volume and buffers mentioned without numbers.
20. "Vaillant aroTHERM heat pump guide". Energy Stats UK. 2025. https://energy-stats.uk/vaillant-arotherm-heat-pump-guide/. **Blog.** Context: SCOP vs flow temperature, firmware cycling bug, links to sources 18 and 19.
21. Green, R. "The Effects of Cycling on Heat Pump Performance". EA Technology for DECC. November 2012. https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/65695/7389-effects-cycling-heat-pump-performance.pdf. **Lab.** COP vs run time; 50 L 4-pipe buffer (about 8 L/kW); 6 min minimum run recommendation; buffer heat loss causing cycling.
22. RHPP final report (DECC_RHPP_161214_Final_Report_v1-13). UCL/RAPID-HPC for BEIS. 2016/2017. https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/606818/DECC_RHPP_161214_Final_Report_v1-13.pdf. **Field data.** 10 min on-to-on cycling common; no COP correlation through metering noise; pump over-run inflating heat meters.
23. "On performance variations" (RHPP). UCL/RAPID-HPC. April 2016. https://assets.publishing.service.gov.uk/media/5a81fa0e40f0b62305b91d1a/DECC_RHPP_160428_On_performance_variations_v20.pdf. **Field data.** 49% of ASHPs with a 10 min median cycle month; under-12-min cycle statistics; circulation pump running continuously all year flagged as parasitic.
24. Electrification of Heat Demonstration: Interim heat pump performance data analysis report. Energy Systems Catapult. March 2023. https://es.catapult.org.uk/wp-content/uploads/2023/03/EoH-Interim-Heat-Pump-Performance-Data-Analysis-Report-1.pdf. **Field data.** Circulation pump energy averaging 146.5 kWh/yr; SPF effect +0.01 to +0.02.
25. "WPsmart im Bestand" final report (BMWi 03ET1272A). Fraunhofer ISE. About 2020. https://wp-monitoring.ise.fraunhofer.de/wpqs-im-bestand/download/Berichte/BMWi-03ET1272A-WPsmart_im_Bestand-Schlussbericht.pdf. **Field data.** 21 of 29 ASHPs with a buffer (about 249 L); 4.1% buffer loss; space-heating spreads 5.5 and 6.8 K; flow-rate changes shifting flow temperature in return-controlled units.
26. Dongellini, M. "Dynamic modeling and seasonal performance evaluation of air-to-water heat pump systems". PhD thesis, University of Bologna. 2017. https://amsdottorato.unibo.it/id/eprint/7901/1/Dynamic%20modeling%20and%20seasonal%20performance%20evaluation%20of%20air-to-water%20heat%20pump%20systems.pdf. **Paper (simulation).** Optimal volume of 4–7 / 7–9 / 15 L/kW; +11% SCOP with 120 L for an on-off unit; buffer in the return line best; no saving from indirect constant-flow layouts.
27. Daikin Altherma Low Temperature Split installer reference guide (ERLQ011-016CV3, EHVZ16S18CB, 4P401677-1A). Daikin Europe. 2016. https://www.daikin.eu/content/dam/document-library/Installer-reference-guide/heat/air-to-water-heat-pump-low-temperature/ERQH011-016BV3-BW1,%20ERLQ011-016CV3-CW1,%20EHVZ-CB3V_4PEN401677-1A_Installer%20reference%20guide_English.pdf. **Manufacturer.** Minimum volume 10/20 L, minimum flow 12/15 L/min, ΔT setting 3–10 K (default 5), pump modes continuous/sample/request, pump speed limit, emitter-type setting.
28. Viessmann Vitocal 250-A/252-A Planungsanleitung (monoblock, 2.6–18.5 kW). Viessmann (via heima24). About 2023–2024. https://www.heima24.de/shop/images/products/media/pa-viessmann-Vitocal-250-A-252-A-Monoblock-2,6-bis-18,5kW.pdf. **Manufacturer.** Hydro AutoControl with 16 L integrated buffer and 4/3-way valve; unit flow above 300 l/h; at least 1000 l/h during defrost; external buffer of at least 200 L only for radiators plus utility lockout; external buffer reduces cycling.
29. Samsung Generation 6 Heat Pump installation manual (UK/IE, ENG-0013-11). Joule / Samsung, via SNH Trade Centre. 2024. https://www.snhtradecentre.co.uk/wp-content/uploads/2024/02/Samsung-Gen-6-ASHP-Installation.pdf. **Manufacturer.** Primary and secondary pumps or a header required; no UFH mixing sets; minimum 30 L; flow above 16 L/min.
30. Panasonic Aquarea WH-SXC09/12F service manual (PAPAMY1311028CE). Panasonic. 2013. https://www.panasonicproclub.com/uploads/CZ/catalogues/aquarea/service-manual/SXC9,12_F_E8_service%20manual_PAPAMY1311028CE.pdf. **Manufacturer.** Minimum 50 L of system water, else add a buffer; selectable pump speed.
31. Vaillant VWZ AI heat pump appliance interface, operating and installation instructions (0020291573_01). Vaillant. December 2022. https://professional.vaillant.co.uk/downloads/aproducts/renewables-1/arotherm-plus/monoblock-heat-pump-system-vwz-ai-heat-pump-appliance-interface-2685948.pdf. **Manufacturer.** Remaining head 20–90 kPa set for nominal flow at ΔT 5 K; pump 50–100% PWM/Auto; flow at least 35% of nominal (S.275); compressor hysteresis description.
32. VERSATI III All-in-one Type Air To Water Heat Pump service manual. Gree. About 2020–2021. https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iii/versati%20iii%20all%20in%20one%20%E2%80%93%20service%20manual.pdf. **Manufacturer.** Inverter pump speed follows the entering/leaving ΔT; compressor frequency proportional to (setpoint − outlet); UFH loop and manifold design rules (100–120 m, 8 loops, 0.25–0.5 m/s); pump stops 120 s after the compressor in some sequences.
33. Gree Versati notes compiled in `docs/research/notes/08-gree-versati.md`, from that note's primary sources [1][2][3][4][5][10][12] (Modbus V1.5, Versati II/III service manuals, Versati III monobloc service manual with 20 L minimum volume, EU catalogue with pump about 75 W). Various Gree documents. 2012–2025. URLs listed in that note, e.g. https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iii/versati%20iii%20monoblokk%20–%20service%20manual.pdf. **Manufacturer.** Minimum volume 20 L; pump about 75–85 W; pump in standby; no pump-mode setting; flow-switch lockout; Word 30 range 2–10 K; 3 min lockout and about 6 min capacity hold; anti-freeze logic.
34. "Planning Underfloor Heat" handbook (VGCTC202). Danfoss Heating Solutions. 2009. https://assets.danfoss.com/documents/100650/AG000086464394en-010201.pdf. **Manufacturer/engineering guide.** EN 1264 design spread σ = 5 K; loop length 100–110 m; 250 mbar maximum; 0.113 L/m pipe content; flow set per loop in l/min.
35. "Hydraulischer Abgleich". Wikipedia (German). Accessed 2026. https://de.wikipedia.org/wiki/Hydraulischer_Abgleich. **Reference (citing studies).** OPTIMUS: pumps about 3 times oversized; 7–11% savings (ITG Dresden) only with flow-temperature reduction; about 7% across 555 buildings.
36. Ploskic, A. "Framledningstemperaturen bestäms av värmebehovet". Energi & Miljö no. 9 (SBUF 13122), KTH/Bravida. 2016. https://vpp.sbuf.se/Public/Documents/ProjectDocuments/3214fb17-4e36-45c3-b83b-614a8222ffad/FinalReport/SBUF%2013122%20Vetenskaplig%20artikel%20Ploskic%20A.%20Framledningstemperaturen%20best%C3%A4ms%20av%20v%C3%A4rmebehovet.pdf. **Paper (simulation).** UFH at a 5 K spread needs about 15 K lower flow than panel radiators; system SPF +1.1% per K of lower flow temperature (50 → 35 °C).
37. Arghand, T. and Svensson, J. "Hur lågt kan vi gå? Optimerade lågtemperatursvärmesystem med bergvärme" (SBUF 14234). Bengt Dahlgren / PEAB. 2024. https://vpp.sbuf.se/Public/Documents/ProjectDocuments/fb3440a8-b138-476a-8f61-344a27e2cf28/FinalReport/SBUF%2014234%20Slutrp%20Hur%20l%C3%A5gt%20kan%20vi%20g%C3%A5%20Optimerade%20l%C3%A5gtempsystem.pdf. **Paper/report (simulation).** Each 10 K lower flow temperature cuts purchased electricity by about 15–20%.
38. Žėkas, V. and Martinaitis, V. "Realiai veikiančio šilumos siurblio efektyvumo tyrimas" (Analysis of efficiency for a current heat pump). Mokslas – Lietuvos ateitis 1(1):68–71, Vilnius Gediminas Technical University. 2009. Journal site http://www.vgtu.lt/leidiniai (exact article URL not recorded; PDF obtained from the shared research cache). **Field data (Lithuania).** Vilnius house with UFH, heat-recovery ventilation and a 100 L buffer behind a 15.9 kW unit: 3–4 starts per hour of 4–6 min each in mild weather; momentary COP 3.7–3.9.
39. "3 steps to maximise your heat pump (or boiler) efficiency". Heat Geek. 2025–2026. https://www.heatgeek.com/articles/3-steps-to-maximise-your-heat-pump-or-boiler-efficiency. **Blog.** Weather-curve tuning near 0 °C; 2–3 K UFH setback to keep slab mass fed; zoning raises the curve; balancing masked by high flow temperature.

Additional material skimmed but not cited for numbers:
- Lithuanian Energy Agency (ENA) buyer guide 2025, https://www.ena.lt/uploads/PDF-EVE/2025-12/Silumos-siurbliu-parinkimas-2025.pdf (generic);
- eco+Logic "Using your heat pump underfloor heating system" (NZ, 2022, Shopify CDN), floor-sensing and setback tips;
- de Podesta, Protons for Breakfast blog index (no hydraulics post found without search).
