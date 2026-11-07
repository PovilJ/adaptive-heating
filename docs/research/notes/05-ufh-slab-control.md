# Underfloor heating in a concrete slab with a heat pump

Researcher topic 05. Scope: thermal mass and time constants of screed/slab underfloor heating (UFH), the self-regulating effect, why continuous low-temperature operation is recommended, setback/recovery and optimal start, slab heat storage and load shifting, floor-surface comfort limits, loop flow and delta-T, zone actuators, the TABS (thermally activated building systems) control literature (Gwerder/Tödtli unknown-but-bounded + pump PWM, Olesen), and solar gains vs a slow slab. The house's own controller code was deliberately not read.

Notation: `[n]` = source number (see Sources). `[calc]` = my own arithmetic using the house data in the brief plus stated assumptions; treat as order-of-magnitude, not measurement. Evidence ranking used: measured field data > controlled lab > peer-reviewed simulation > manufacturer claim > forum anecdote.

House data used in `[calc]` (from the brief): heat-loss coefficient H = 0.14-0.20 kW/K, slab storage C = 6.6 kWh/K, compressor minimum heat output P_min = 3.7-3.8 kW (3.75 used), room target 22.0 °C, load ~1.7 kW at +10 °C. **Assumption:** active heated floor area A = 150 m² (unknown; I also show 120/180 m² where it matters). Assumed floor build-up heat-transfer coefficient water-to-room K_H ≈ 6.5 W/(m²K) (tiles/stone) to 4.5 W/(m²K) (parquet/carpet), typical orders of magnitude for wet screed systems, not measured here.

## Summary

- **The slab needs only lukewarm water; the observed 31-36 °C (peaks 39 °C) is roughly 5-10 K more than the physics requires in mild weather.** The EN 1264 floor-heating curve is q = 8.92·(θ_floor − θ_room)^1.1 W/m² with ~11 W/(m²K) total surface coefficient [5]. For this house that means a floor surface only ~1.2-1.7 K above the room at +10 °C and ~3.8-5.3 K at −20 °C, i.e. mean water ≈ 24-26 °C at +10 °C, ≈ 25-28.5 °C at 0 °C and ≈ 28-34 °C at −20 °C [calc, A = 150 m²]. Each extra K of water costs ~2-3 % COP [28][30]; a Carnot-based estimate gives −14 to −18 % for 35 instead of 28 °C supply [calc], consistent with COP 4.9 vs 3.5 for 35 vs 55 °C supply [6].
- **In mild weather cycling is unavoidable (P_min ≈ 3.75 kW > load 1.7 kW at +10 °C); the slab makes cycling cheap if runs are long and cool.** Air-source start/stop losses are ~1-2 % for short cycles [16] (2-5 % for very short ones, insignificant for runs ≥15 min, per the same group's conference work as summarised in search results). With C = 6.6 kWh/K, a ±0.5 K swing at +10 °C gives ~3.4 starts/day with ~3.2 h runs; ±0.25 K gives ~7 starts/day with ~1.6 h runs [calc]. The waste is not the number of starts but high water temperature and short, hard catch-up runs.
- **Slab response is hours, so intra-day room-temperature chasing is futile.** Median τ95 for screed UFH (ISO 11855 type A) ≈ 4.9 h, TABS 9-19 h [8]; high-mass radiant time constants are typically 4-8 h [7]; heat-front delay pipe→surface ≈ 3 h and ~3.2 days to reach a new room steady state in a Swedish low-energy house [6]; Gwerder's lab TABS had τ = 9.9 h with the pump on and 100 h with it off [1]. Whole-house C/H for this house ≈ 33-47 h [calc]. TABS researchers state only day-to-day room compensation is promising [1][2].
- **The self-regulating effect is very strong in a low-load house, but only with continuous circulation at a low, steady water temperature.** At +10 °C a 0.5 K room rise (floor surface unchanged) cuts floor output ~44 % and a 1 K rise ~84 % [calc from 5]; at design conditions Danish TI reports 5-20 % per K [13]; Karlsson computes that 64-77 % of an unexpected heat gain is compensated automatically, but only when supply temperature is the controlled variable [6]. Intermittent pulses at higher temperature weaken it: Gwerder's PWM simulation cut pump on-time to 47 % but raised heating and cooling energy unless daily room feedback was added [2].
- **The TABS control canon transfers well to a single-zone slab house:** feed-forward supply (or mean-water) temperature from the 24 h mean outdoor temperature, constant flow, plus slow day-to-day room feedback [1][2][3][7]. Olesen's best winter rule in simulation was supply = 0.45·(18 − t_out) + 18 °C (≈ 26 °C at 0 °C, ≈ 31 °C at −10 °C) with no room-temperature input [4]; Raftery's slab-temperature loop with a once-per-day reset cut energy up to 35 % and cost up to 40 % vs common US practice (simulation, office) [7].
- **A comfort band beats a setback.** Widening the allowed range from 22-23 °C to 21-23 °C cut TABS heating energy by ~20 % (simulation), with a recommended dead-band of at most 2 K [4]. Night setbacks should stay ≤ 2-3 K [21][33]; naive setback can raise heat-pump operating cost [20]. In this house a 2 K night setback saves only ~2 kWh_th of losses per night (~5 % of a mild day) but must re-deliver ~13 kWh_th of slab heat next morning, either at higher water temperature/power or with hours of comfort lag [calc]. (Owner trials in a low-mass radiator house did show setback savings [23]; that does not transfer directly to a slab.)
- **Storage/load shifting:** the house stores ~6.6 kWh of heat per K of slab temperature; at 1.7 kW load each K of allowed drift carries the house ~3.9 h without the heat pump (~1.65 h at 4 kW, ~6.6 h at 1 kW) [calc]. Well-insulated houses can coast > 24 h after charging, flexibility saturates beyond ~6 h activation, and storage strategies add 3.3-6.3 % heating energy (simulation, 20/22/24 °C set-points) [10]; 2 h charging pulses of 1.6 kWh cost ~6 % extra loss in a Dutch low-energy living room [9].
- **Comfort limits:** EN 1264 caps floor surfaces at 29 °C (occupied) and 35 °C (perimeter), ≈ 99 and 165 W/m² at 20 °C room [5]; ISO 7730 asks for ≤ 1 K peak-to-peak cyclic swing and < 2 K/h drift [9][10]. This house never needs more than ~27.5 °C floor surface even at −20 °C [calc], so the binding limit for charging the slab is room over-temperature, not the floor. (Chinese subjects preferred 29-32 °C floors [12], so 29 °C is a conservative design cap, not a comfort optimum.)
- **Zone actuators that close loops hurt heat pumps:** uncoordinated on/off manifold valves make flow fluctuate, push the supply temperature up and lower COP (a part-load case ~12 % worse [13]; ~15 % theoretical COP potential from optimising flow [14]). Keep all loops open and use any thermostats only as high limits [21][29]. A German owner reported 4,000-4,200 → 2,800-3,000 kWh/yr and 8-10 → ≤ 3 starts/day after removing single-room control and balancing (anecdote) [28].
- **Solar gains + slow slab = overheating risk that must be handled before the sun arrives.** A low-energy UK house logged > 1 kW of winter solar gain, exceeding its whole heat need; 2 h of winter sun raised a room ~0.5 K [26]; sunlit floor patches run ~8-8.5 K warmer [19][36] and overheating can persist ~8-12 h after the sun leaves [37]; solar absorption limits slab-charging options [9]. Ventilation cannot dump much: removing 500 W at 2 K needs ~3,000 m³/h [26].
- **Predictive control is the state of the art for slow slabs, but simple daily logic captures much of it.** Predictive control of intermittent radiant floors saved 10-12 % in cold months and more in mild weather vs conventional control (simulation + experiment, abstract) [40]; OptiControl reported 16-41 % theoretical potential for predictive vs 1-15 % for improved non-predictive control (snippet) [41]; with a ~3 h lag, control can only follow the daily trend [6].
- **Flow and delta-T:** TABS designs run constant flow (~15 kg/(h·m²)) [1][2]; the Danish 5-10 K design spread is a poor fit for heat pumps, which want high, steady flow [13]. At 3.75 kW and 1.0-1.2 m³/h the loop ΔT is only ~2.7-3.2 K [calc]; a low-energy UK house runs 1,050 l/h with return rarely > 1 K below flow [26].
- **Gree setting worth testing:** the Versati III manual lists "ΔT-Heat" (leaving-water temperature difference, heating) as adjustable 2-10 K [15]. Lowering the restart hysteresis from 4 to 2 K would let the unit restart with a setpoint only ~2 K above the slab-temperature water, removing the main reason high setpoints are needed today (hypothesis; model-specific, verify on this unit).

## Detailed findings

### 1. Time constants and lags of slab/screed UFH

**Classification by response time.** Ning, Schiavon and Bauman ran 56,874 simulations and classified radiant systems by τ95 (time for the surface temperature to complete 95 % of a step change) [8]:

| Class | ISO 11855 types | τ95 range | Median τ95 |
|---|---|---|---|
| Fast (radiant ceiling panels) | - | < 10 min | 4 min |
| Medium (embedded surface systems, ESS) | G / D / B / A | 1-9 h | 1.5 / 2.5 / 3.3 / 4.9 h |
| Slow (TABS) | F / E | 9-19 h | 12.4 / 13.8 h |

Type A (pipes inside a wet screed on insulation) is the most likely construction for "wet UFH in a concrete slab"; type E (pipes in a massive structural slab, no insulation between pipes and mass) would sit in the slow class. Concrete thickness, pipe spacing and concrete properties dominate TABS response; pipe diameter, water temperature and flow regime matter little [8]. A Lithuanian MSc study likewise found pipe spacing to be the parameter with the largest effect on floor inertia [17].

**Time constant vs. 24 h loads.** CBE (UC Berkeley) defines "high thermal mass" radiant systems as TABS or ESS with a 63 % response time of several hours and cites a typical time constant of 4-8 h, long relative to the 24 h load cycle; zone-air on/off control of such systems "leads to large zone air temperature overshoots" and heating/cooling in the same day [7] (paraphrased).

**Two-time-scale behaviour.** Karlsson's lumped 2-node model of a Swedish low-energy house (wooden floor over 300 mm cc pipes in concrete) gave an initial delay t_c,fh ≈ 3.0 h (heat front travelling from pipe plane to the interior) and a characteristic time t_c,i ≈ 3.23 days to reach a new indoor steady state [6]. Discrete predictive control with a period shorter than the ~3 h delay produced unstable, oscillating heat-flux solutions unless a comfort interval and prognosis were used. Practical control can therefore only follow the daily trend [6].

**Measured TABS lab constants.** In Siemens' Zug test room (250 mm slab, 150 mm pipe spacing, 15 kg/(h·m²) flow, raised floor + carpet R = 0.5 m²K/W) the first-order model had τ1 = 9.9 h with the pump running and τ0 = 100 h with the pump off; R_t (water→core) = 0.060, R~ (core→room) = 0.16, façade 0.39 m²K/W [1]. Typical R_t/(R_t + R~) ratios for TABS are 20-50 % [1]. The asymmetry (10 h charging vs 100 h coasting) is the essence of a slab: it charges quickly when water flows and coasts for days when it doesn't.

**Field/forum observations (lower weight).** A UK self-builder logged a 10-15 h lag between heat-meter energy and room demand in a 220 m² slab-UFH house, while solar and internal gains hit the room within tens of minutes [26]. An openHAB user estimated ~1 h before a concrete-slab kitchen floor showed any room effect and saw room temperature keep rising for "a few hours" after heat stopped [27].

**This house [calc].** 6.6 kWh/K ≈ 23.8 MJ/K. At ~2.0 MJ/(m³K) for concrete that is ~11.9 m³, i.e. ~99 / 79 / 66 mm of concrete over 120 / 150 / 180 m², which matches a typical 65-100 mm wet screed (cf. 100 mm × 75 m² ≈ 4 kWh/K in [26]). Whole-house time constant C/H = 6.6/0.20-0.14 ≈ 33-47 h (larger if the rest of the building mass is counted). Expect pipe→surface delay of ~2-5 h and a room settling time of 1-3 days after any change in the daily energy delivered.

### 2. Heat output physics, surface-temperature limits and what this house needs

**Basic characteristic.** EN 1264 / EN 15377: floor heating (and ceiling cooling) q = 8.92·(θ_S,m − θ_i)^1.1 W/m²; total floor heat-exchange coefficient ~11 W/(m²K) in heating; maximum surface 29 °C in the occupied zone and 35 °C in the perimeter zone, giving ~99 W/m² and ~165 W/m² at 20 °C room [5]. The water-side output follows q = B·Π(a_i^m_i)·Δθ_H with Δθ_H the log-mean water-to-room difference [5]. National rules may lower the 29 °C cap; bathrooms are often allowed ~33 °C (secondary sources, not verified against the 2021 text).

**Comfort research.** ISO 7730-derived floor limits used by van Leeuwen et al. are ~19-28/29 °C; operative temperature should vary ≤ 1 K peak-to-peak (periodic) and < 2 K/h [9]. Johra et al. kept drift < 2.1 K/h in their flexibility studies [10]. A 45-subject study in Chongqing found a neutral floor temperature of ~28 °C for long stays and preferred 29-32 °C (33-35 °C for short stays), arguing standards (~25-29 °C) are conservative for that population and climate [12]. Contradiction noted, but irrelevant here because this house never approaches those floor temperatures.

**This house [calc] (A = 150 m², H band 0.14-0.20 kW/K):**

| Outdoor | Load (kW) | q (W/m²) | Floor surface − room (K) | Mean water (tiles … parquet, °C) |
|---|---|---|---|---|
| +15 °C | 1.0-1.4 | 6.5-9.3 | 0.75-1.04 | ~23 … ~24 |
| +10 °C | 1.7-2.4 | 11-16 | 1.23-1.70 | 23.7-24.5 … 24.5-25.6 |
| +2 °C | 2.8-4.0 | 19-27 | 1.96-2.71 | 24.9-26.1 … 26.1-27.9 |
| 0 °C | 3.1-4.4 | 21-29 | 2.13-2.95 | 25.2-26.5 … 26.6-28.5 |
| −10 °C | 4.5-6.4 | 30-43 | 3.00-4.15 | 26.6-28.6 … 28.6-31.5 |
| −20 °C | 5.9-8.4 | 39-56 | 3.84-5.31 | 28.0-30.6 … 30.7-34.4 |

Add ~half the loop ΔT (1.5-3 K) to get supply temperature. With 120 m² instead of 150 m², q rises 25 % and the water temperatures rise accordingly (~+0.5 K at +10 °C, ~+2 K at −20 °C). Even with pessimistic assumptions, steady-state supply in the −5…+10 °C band, where the brief says most humid days fall, is ~26-31 °C, not 31-36 °C. Floor surface stays ≤ ~27.5 °C at −20 °C, far from 29 °C.

**Cross-check with independent rules.** Olesen's best TABS winter curve gives 26.1 °C at 0 °C, 30.6 °C at −10 °C and 35.1 °C at −20 °C [4]. A UK slab house runs ~29 °C flow at 0 °C [26]; another UFH owner ran 30 °C at −5 °C and 25 °C at +20 °C with daily COP ~5 in October [25]. Swedish forum practice for cast slabs is NIBE curve 4-5 with offset −1 (snippet) [47]. Lithuanian guidance quotes 25-38 °C supply for floors (snippet) [48]. All point to mid-20s to low-30s °C supply for a well-insulated slab house. Field context: in Fraunhofer ISE's monitoring of existing German single-family houses, air-source units ran mean flow temperatures of 34.6-52.4 °C at −3 °C mean outdoor [35]. A well-insulated slab house should operate well below that whole range.

### 3. The self-regulating effect

**Mechanism.** Because the floor-to-room temperature difference is small, a small change in room temperature is a large relative change in the driving difference, so output drops sharply as the room warms [4]. Olesen describes this as a significant self-control effect for small surface-room differences [4]. Karlsson's 2008 conference paper found the same for an inexpensive floor system in a low-energy detached house: pipe heat flux rises as indoor air cools and can be fully blocked when indoor temperatures are high [46]. Oventrop's technical document gives an example where a fully open circuit's floor flux falls from 30 to 20 W/m² as the room warms, and notes the effect does not work when other heat sources warm the room (search summary; PDF blocked) [49].

**Quantified in a low-energy house.** Karlsson (Chalmers PhD) shows that with feed-forward (outdoor-based) supply temperature, the floor responds to any non-periodic disturbance by shifting supplied heat flux the opposite way [6]. His self-regulation utilisation factor ψ (accumulated shift in supplied heat divided by the energy of the disturbance) was −0.64 to −0.77 across cases (reference −0.73; lower flow −0.65; no heat recovery −0.64; stone floor −0.77; pipes higher in slab −0.75; 150 mm instead of 300 mm spacing −0.77) [6]. So roughly two-thirds to three-quarters of an unexpected convective gain is "given back" by reduced floor output. Self-regulation is strongest with low envelope losses, low floor-covering resistance, tight pipe spacing near the surface and high flow; and it is "only achievable if the supply fluid temperature is the controlled variable" (paraphrased) [6]. Its effect on room temperature becomes visible only after a few hours [6]. For periodic disturbances, short periods see an inert response, intermediate periods slightly amplify swings, long periods damp them [6].

**Design-condition sensitivity.** Danish TI: each +1 K of room temperature lowers floor output 5-20 % while raising space-heating power need 5-100 % (depending on outdoor temperature, internal gains and habits) [13].

**This house [calc].** At +10 °C (H = 0.14, q = 11.2 W/m², surface 23.23 °C): room 22.25 °C → −22 % output; 22.5 °C → −44 %; 22.75 °C → −64 %; 23.0 °C → −84 %. In mild weather the floor almost stops emitting once the room is ~1 K warm. That is why a low-temperature, continuously circulated slab is hard to overheat with water alone, and why overheating in such houses comes mainly from solar/internal gains plus water temperatures far above the slab.

**In practice.** A UK low-energy self-builder concluded that open-loop "self-regulation" failed in his house because incidental gains (sun, showers, cooking, guests) needed room feedback: "Sadly this doesn't happen in the real world." What worked was a room thermostat with 0.1 °C hysteresis while UFH flow stayed ≤ 25-26 °C [26]. Five people (~500 W) raised a room ~1 K in 15-30 min; a shower can add ~2 kWh [26]. Self-regulation limits overheating from the water but cannot remove heat that arrives from elsewhere.

**Intermittent operation weakens it.** Gwerder et al.: with PWM (intermittent pump), off-times must be compensated by higher supply temperatures during on-times, which "reduces the self-regulating effect" (paraphrased). In whole-year simulations (Zurich, 250 mm slab, 21-26 °C band), PWM alone cut pump on-time to 47 % but increased heating and cooling energy; adding room-temperature feedback restored energy use to the level of continuous operation with feedback [2]. They therefore recommend keeping the PWM supply-temperature shift small, typically 1-3 K [1].

### 4. Why continuous low-temperature operation is recommended, and its limit here

**COP vs water temperature.** Karlsson's example: COP 3.5 for a 0→55 °C lift vs 4.9 for 0→35 °C [6]. Rules of thumb: ~2-3 % COP per K of supply [30], 2.5-3 %/K [28]; Heat Geek: 45 instead of 55 °C gives 20-30 %+ better COP [21]. Carnot-based estimate for this house (η = 0.45, T_cond = supply + 3 K, T_evap = air − 7 K) [calc]:

| Air | Supply 26 °C | 28 °C | 31 °C | 35 °C | 39 °C |
|---|---|---|---|---|---|
| +10 °C | 5.2 | 4.9 | 4.5 | 4.0 | 3.6 |
| +2 °C | 4.0 | 3.8 | 3.5 | 3.3 | 3.0 |
| −10 °C | 3.0 | 2.9 | 2.7 | 2.6 | 2.4 |

Moving mild-weather runs from ~35 °C to ~28 °C is worth ~15-20 % [calc]. Field anecdote, UFH-only house: lowering flow from 48 to 40 °C cut electricity from ~60 to ~45 kWh/day (−25 %) [22]. Polish case: lowering the curve 3 K saved ~70 kWh/month; 10-20 % savings typical at positive outdoor temperatures (journalistic, single case) [30].

**Low temperature also steadies hydraulics.** Danish TI showed that running ~3 K above the minimum needed supply temperature makes on/off room valves close more, increasing flow spread and lowering mean flow, which degrades heat-pump operation [13]. The EUDP follow-up project framed the gap between rated and real heat-pump efficiency as supply temperatures set too high plus fluctuating UFH flow; it estimated ~15 % theoretical COP potential from optimised volume flow (project page, no final results) [14].

**But minimum modulation forces cycling.** Forum data show inverter minimum outputs of ~2.9-3.2 kW for an Ecodan at 35 °C flow and 4-7 °C outdoor, rising as flow temperature falls [24], and 4.4 kW for a Daikin Altherma 3 HHT [34]. When load < minimum output the unit must cycle; flow and return converge and it stops until the water cools [25]. Thresholds cited by owners: ≤ 6 cycles/h as an old rule of thumb, runs ≤ 10 min as the real concern [25]; 2-3 cycles/h deemed acceptable by some OEM users [22]. Research: Uhlmann & Bertsch (lab-validated transient model) found air-source cycling losses of only ~1-2 % for short cycles and that EN 14511 ratings remain representative [16]. Conference work by the same group (via search summary) gives 2-5 % for very short cycles and calls the penalty insignificant for runs ≥ 15 min [16].

**Interpretation.** With a slab, the choice is not "continuous vs cycling" but "short cycles at whatever temperature vs long cycles at minimum frequency and the lowest water temperature that can absorb minimum output." John Cantor's argument, as relayed on a forum, is that gentle cycling can lower the average water temperature [25]; owner data claim COP ~5-6 at ~23-25 °C average water with a couple of cycles per hour (estimates, not metered) [25]. One owner deliberately lengthened runs by toggling a thermostat between 18.5 and 19.5 °C to get ~2 h on / 1 h off [34].

### 5. TABS control literature: what transfers to a house

**Conventional practice** (Tödtli et al., as summarised in [1]): outdoor-compensated supply temperature without considering heat gains; no zone feedback; relies on self-regulation; heat/cold generation enabled by season/outdoor temperature.

**Unknown-but-bounded (UBB) design** (Gwerder et al. 2008) [3]: heat gains are unknown during design and operation, but lower and upper bounds can be specified. The heating/cooling curves are then derived so that comfort is guaranteed as long as real gains stay within the bounds. The method includes automatic heating/cooling switching. The modular zone control [2] has four parts:
1. **Mandatory:** supply-water setpoint range from heating/cooling curves driven by the **mean outdoor temperature of the last 24 h** (moving window). The outdoor signal is smoothed on purpose: the slab cannot follow hourly weather.
2. **Optional room feedback:** two PID controllers whose P and I act on the **minimum (heating) / maximum (cooling) room temperature of the last 24 h** and whose D acts on the **24 h mean**. Outputs are limited (e.g. ±5 K) and shift the room setpoints feeding part 1. They emphasise that "only day-to-day room temperature compensation is promising" [1] and that sensor placement is critical [2].
3. **Optional PWM** of the zone pump (intermittent operation) [1][2].
4. **Mandatory** sequence control of supply temperature.

UBB design for their Zurich example produced a heating limit of 13.1 °C (24 h mean outdoor) [2].

**PWM details (Gwerder 2009)** [1]:
- Physics: 1st-order slab model, core node with capacitance C_s, R_t to supply water (only when pump runs) and R~ to the room.
- Simplified PWM law (energy balance, valid for typical TABS and periods up to 24 h): on-ratio Δt_on/Δt = 1 / [1 + (θ_sw,PWM − θ_sw,cont) / (R_t/(R_t+R~)·(θ_sw,cont − θ_r,SpH))]. The only physical parameter is the resistance ratio R_t/(R_t+R~) (lab: 28 %; typical 20-50 %).
- Variant for non-constant supply temperature: switch off when the integral of supply temperature over the on-time exceeds the energy the continuous case would have delivered (switch-off criterion based on ∫θ_sw dt).
- Practical parameters in lab tests: heating PWM period 5 h, setpoint shift ΔSpH = 1.5 K (recommended 1-3 K to protect self-regulation), cooling period 24 h with on-time starting 22:00, minimum **purge phase of 30 min** at the start of each period: circulate without heating, then measure supply temperature; if it is already within range, extend the purge (no heating needed).
- Trade-off on period length: long periods give slightly worse room control; short periods add unproductive purge phases. For typical TABS, room-temperature amplitudes from PWM stay small for periods up to 24 h. A 24 h period allows placing on-times in a chosen daily window (cheap or efficient energy).

**Olesen (DTU/REHVA)** [4]: TRNSYS study of an 18 cm slab with 20 mm pipes at 150 mm and 350 kg/h constant flow, office occupancy, Würzburg and Venice:
- Running the pump only 18:00-06:00 kept the rooms comfortable.
- Controlling the mean water temperature lets a rising return be compensated automatically by a lower supply. Supply vs mean control differed little.
- Best: supply (or mean) temperature as a function of outdoor temperature. Case 1401 (winter supply = 0.45·(18 − t_out) + 18) gave ~10 % less energy in Würzburg.
- "There is no need to take into account the room temperature" (in that simulation) [4].
- Room dead-band with the pump stopped inside it: lowering the lower limit 22 → 21 °C cut heating energy by roughly 20 % while staying above 20 °C. The dead-band should be at most 2 K [4].
- Night-only operation (18:00-06:00) kept comfort in both climates, as Raftery et al. also note when reviewing this work [7].
- Constant water temperature year-round performed poorly.

**Raftery et al. (CBE, 2017)** [7]: on/off or P-only control on zone air or slab temperature is the most common practice. A US survey of radiant buildings found 43 % used zone temperature as the sole control variable and 26 % slab temperature. Air-based control causes large overshoots and same-day heating/cooling. The best comfort-oriented strategies in the literature are constant flow + variable (outdoor-based) temperature, but these are feed-forward and do not exploit the inertia. Their controller:
- Primary on/off loop on a slab sensor near the surface.
- Secondary P loop, run once a day at the end of occupancy, moves the slab setpoint based on yesterday's min/max zone air temperature; the change is applied gradually over 12 h.
- One mode per day (heating, off or cooling).
- A designer-chosen 12 h lockout window.
- EnergyPlus results (Sacramento office): up to 35 % less energy and 40 % lower cost than typical US control at comparable comfort.

**Pulsed / intermittent flow results:**
- Tang, Raftery et al. (2018, abstract via search): pulsed two-position-valve control needed 27 % less water flow than prior intermittent control and 24 % less than variable-temperature control at 50 % part load [38].
- A KTU MSc study (COMSOL + IDA-ICE) found pulsed flow in a 65 mm screed raised pipe heat flux 5.8 % but floor output only 1.17 %, with ≤ 3 % energy savings; the screed's conduction-dominated mass damps the pulses [17].

Takeaway: pulsing the slab does not unlock new physics; it changes when energy is delivered.

**MPC and predictive control:**
- Karlsson's response-factor MPC kept operative temperature in a 20-22 °C band with supply flux bounded to 0-35 W/m² and a 2 h period [6].
- Hu et al. (DTU/PolyU, 2019): price-responsive MPC of floor heating shifted use to low-price periods and improved comfort at the start of occupancy vs on/off. Preheating start time and duration depended on weather and prices (simulation; abstract) [18].
- Cho & Zaheer-uddin (2003): predictive control of intermittently operated radiant floors saved 10-12 % in cold months and more in mild weather (simulation + experiment; abstract) [40].
- OptiControl (ETH/Siemens/MeteoSwiss, Clima 2010): improved non-predictive control 1-15 %, predictive control 16-41 % theoretical potential (snippet) [41]. A related seven-month real-building MPC trial found the investment hard to justify on savings alone (search snippet).
- Široký et al. ran a two-month MPC field experiment in a Prague building; its savings figure was not verified in this sweep [45].

Real-house measured MPC savings for slab UFH with heat pumps did not turn up in this sweep (gap).

### 6. Setback, recovery and optimal start

- **Installer/manufacturer guidance:** Heat Geek recommends overnight setbacks of ≤ 2-3 °C, because larger ones (e.g. 21 → 16 °C) create a morning recovery penalty. It treats weather compensation as the biggest driver of running cost and says stats/TRVs should be limiters, not the main control [21]. Selectra relays Viessmann's advice of ≤ 2 °C setback, since larger setbacks need much energy for a rapid morning recovery; ~35 °C flow typically holds 19-20 °C and a higher curve does not warm screed faster [33]. Grant UK argues a setback (rather than switching off) keeps screed warm and reduces overall demand (manufacturer, no numbers) [32].
- **Research:** Rutz & Moran (1990, simulation): night setback lowers heat-pump costs only if the controller accounts for the heat pump's and the building's characteristics; otherwise it can increase operating cost. A rule-based (AI) controller saved consistently [20]. Le Dréau & Heiselberg (2016) studied both heat storage (set-point up) and conservation (set-point down) and found flexibility depends on insulation, emitter and season (abstract) [11].
- **Owner evidence (low thermal mass, radiators, Ecodan):** in 18 setback trials, continuous days used more energy in all but one case: +2.4 to +8.2 kWh/day at 5-12 °C ambient, ~24 vs ~33 kWh/day below 3 °C ambient (defrost-heavy) [23]. This shows setback can pay in light, leaky houses; it is not evidence for slabs.
- **UK slab owner:** a 12 h timer "reduced COP significantly" under high load vs 24/7 weather compensation (anecdote) [26].
- **Physics for this house [calc]:** with C ≈ 6.6 kWh/K and H ≈ 0.14-0.20 kW/K (C/H ≈ 33-47 h), an unheated night cools the house noticeably. At 0 °C outdoor the initial drift is ~0.45-0.65 K/h (~4 K in 8 h); at +10 °C it is ~0.25-0.35 K/h. So a 2 K setback is reached within ~3-7 h. The only saving is the reduced loss, ≈ H × (average reduction) × hours: 0.17 kW/K × 1.5 K × 8 h ≈ 2 kWh_th per night, about 5 % of a 40 kWh_th mild day. Meanwhile 2 K × 6.6 kWh/K ≈ 13 kWh_th must be put back next morning. Delivered fast, that needs near-maximum compressor speed and hotter water (~2-3 % COP per K); delivered slowly, the house stays cool for hours. The net is roughly zero or negative, unless the re-delivery lands in hours with clearly better COP (warmer afternoon air) or free PV. That is load shifting, not setback, and belongs in §7.
- **Optimal start** (pre-heat timing to reach comfort at a given time) mainly matters when there is a setback. For a slab, the useful generalisation is optimal timing of energy delivery inside a comfort band, which is what the predictive and MPC papers do [6][18][40].

### 7. How much heat a slab can store, and for how long

- **Danish house study (Johra et al. 2019)** [10]: price-signal set-point modulation 20/22/24 °C with drift < 2.1 K/h.
  - Envelope insulation is the dominant parameter; thermal inertia is second.
  - Poorly insulated houses can coast only 1-5 h after charging; high-performance envelopes can turn heaters off > 24 h.
  - Flexibility rises quickly then saturates above ~6 h maximum activation time (average effective activation plateaued at 4.7 h).
  - Yearly heating use rose 3.3 % (1980s house) and 6.3 % (passive house) with 24 h activation.
  - UFH in a concrete screed increased flexibility vs convective radiators by up to 44 % (low insulation) and 8 % (high insulation) for medium/heavy structures. A radiant floor gives the same comfort at lower air temperature, cutting ventilation losses.
  - Mass classes: light 30, medium 50, heavy 100 Wh/(K·m²).
- **Dutch low-energy living room (van Leeuwen et al. 2014)** [9]: hollow-core floor plus screed, 514 kg/m², COP assumed 4.5.
  - Storage pulses of 2 h stored 1.6 kWh each; total extra loss 479 Wh = 6 % of 8 kWh charged.
  - Operative temperature rose < 0.5 K/h.
  - Average room need was 475 W; a single storage pulse was 168 % of average electric demand, so floors are well suited to short-term balancing.
  - Solar absorption on one day pushed the room to 21.3 °C (above a 20-21 °C band), limiting storage.
- **Other studies (snippets only):** a 2025 Politecnico di Milano study reports a floor-heated case recovers 50 % of stored heat after one day vs three days with radiators [44]. Reynders et al. (2013) found structural mass can strongly shift heating electricity to off-peak hours and that the emitter-mass interaction matters, while PV cover factors changed little [39].
- **This house [calc]:** coast time per K of allowed slab/room drift = 6.6 kWh/K ÷ load. At 1.0 kW → 6.6 h/K; 1.7 kW → 3.9 h/K; 2.5 kW → 2.6 h/K; 4 kW → 1.65 h/K; 7 kW (−15 °C) → ~0.9 h/K. A ±0.5 K band (1 K drift) therefore shifts ~6.6 kWh_th ≈ 1.5 kWh_el at COP 4.5. Delivering a whole mild-day load (1.7 kW × 24 h = 41 kWh_th) in one block would need ~11 h at P_min and would swing the slab ~3.4 K, which is too much for comfort. At +10 °C, 2-4 runs per day is the practical minimum without solar help.

### 8. Loop flow rates, delta-T and zone actuators

- **Flow:** TABS research uses constant zone flow of ~15 kg/(h·m²) [1][2]; Olesen's room model used 350 kg/h for one slab room [4]. A UK slab house moves 3.7 kW (~17 W/m² over 220 m²) at 1,050 l/h, with return rarely > 1 K below flow [26]. This house at P_min 3.75 kW: ΔT ≈ 4.0 / 3.2 / 2.7 / 2.1 K at 0.8 / 1.0 / 1.2 / 1.5 m³/h; at 8.4 kW (−20 °C, H = 0.20): 9.0 / 7.2 / 6.0 / 4.8 K [calc]. Check the Versati's own minimum water flow in its installation manual.
- **Design ΔT:** Danish TI notes common balancing practice of 5-10 K per loop conflicts with heat pumps that have little condenser volume. When an on/off heat pump stops, supply ≈ return; when it runs, supply = return + capacity/flow, so as much flow as possible is wanted. Small rooms may need flows well above their load-based value [13].
- **Zone on/off valves:**
  - Simulated random phasing of room valves with a 2 h cycle showed large flow swings, worse when supply was 3 K above the minimum. Coordinating valve on-times smooths flow without comfort loss, but needs the lowest possible supply temperature, e.g. reference-room control [13].
  - In a part-load scenario that needed on/off correction, COP at low flow fluctuation was ~12 % below the best case. The authors conclude flow should be optimised to avoid on/off operation of the heat pump, not merely to reduce fluctuation [13].
  - Kensa advises leaving ~25 % of UFH zones hydraulically open (bathrooms, halls) to avoid short cycling, or fitting a buffer; remove manifold mixing valves (snippet) [42].
  - Homematic's flyer says on/off floor valves leave the heat pump unable to shed heat so it starts cycling (snippet) [43].
  - Heat Geek: closing zones cuts emitter area and forces higher flow temperatures [21].
  - Lithuanian guidance: thermostats only regulate flow, and frequent closing lowers heat-pump efficiency (snippet) [48].
  - German owner: 4,000-4,200 → 2,800-3,000 kWh/yr and 8-10 → ≤ 3 cycles/day after removing single-room control and balancing (room 21.5 → 22.5 °C) [28].
  - Dutch forum consensus: weather compensation plus a living-room thermostat as a maximum limiter [29].

### 9. Solar gains and the slow slab

- A UK low-energy slab house saw > 1 kW of solar gain on bright winter days, more than the whole house's heat need, mostly from low late-autumn and early-spring sun; sunlit stone sills reached ~35 °C and spots by a door near 30 °C before IR film was fitted [26]. Another owner: 2 h of winter sun raised an open-plan room ~0.5 K; cooking/guests up to 2 K [26].
- Athienitis & Chen (Concordia, outdoor test room; abstract via search): beam sun made the irradiated floor patch ~8 °C warmer than shaded floor (up to ~15 °C with partial carpet), and heat stored in the floor mass cut heating energy by ≥ 30 % [36].
- Sun-patch experiments (Reims, 2020, snippet): overheating of ~4 °C above the recommended maximum lasted ~11.5 h after the sun patch disappeared (~8.5 h in a related case); water-based cooling of the floor helped dump it [37].
- Lhasa office simulation (validated model): sunlit floor near a south window reached 35.6 °C, ~8.5 K above the north zone; irradiated-zone heat flux 171 W/m² vs 79 W/m² shaded [19].
- Van Leeuwen: absorbed solar energy reduces the room for heat-pump charging of the slab [9]. Raftery deliberately removed shading to show feed-forward controllers fail under real intra-day load variation [7]. Gwerder's UBB handles gains as bounds: comfort is guaranteed only if actual gains stay within design bounds [3].
- An openHAB user proposed cutting heat ~1 h before low sun floods the room (not tested) [27]; UK owners suggested boosting ventilation and running the UFH pump in daylight to spread sun-patch heat [26]. Ventilation capacity is tiny compared with solar gains (~3,000 m³/h to move 500 W at 2 K) [26].
- Implication: the decision not to charge the slab must be taken roughly one slab delay (3-5 h) before the sun arrives, using an irradiance forecast.

### 10. Regional practice (DE, PL, SE, NL, LT, DK)

- **Germany (HA community):** the consensus is no single-room control, careful hydraulic balancing, heating curve/parallel shift to produce only the needed heat, and ~2.5-3 % efficiency per K of flow temperature. Fixed runtime schedules were criticised because outdoor temperature varies ("fixed runtimes are never good") [28].
- **Poland:** each +1 K of supply costs up to 2-3 %; a lowered curve saves 10-20 % in positive temperatures [30]. Curve tuning: shift the mild-weather end if too warm in thaw and the cold end if wrong in frost; allow a whole season; site the outdoor sensor out of the sun [31].
- **Sweden (forum snippet):** let the indoor sensor display only, not control, because of slab inertia; concrete slabs commonly run NIBE curve 4-5, offset −1 [47].
- **Netherlands:** weather compensation without room override overheats the living room; use a room thermostat as maximum limiter [29].
- **Lithuania:** UFH water 25-38 °C set by the heat-pump curve; thermostats regulate only flow, and frequent closing reduces heat-pump efficiency (snippet) [48]. The KTU thesis shows pulsed flow is ineffective in 65 mm screed [17].
- **Denmark:** Teknologisk Institut experience from EnergyFlexHouse: real heat-pump + UFH systems underperform calculations, largely because rooms run above design temperature and supply temperatures end up higher [13].

## What this means for controlling this house

### A. Diagnosis: why the house sees hot water and many hard restarts (confidence: medium-high)

1. **The restart rule pulls setpoints up.** The Versati restarts only when setpoint − outlet ≥ ΔT-Heat (4 K now). In off-periods the circulating water converges on the slab/return temperature, ~23-25 °C in mild weather [calc]. To trigger a restart the setpoint must be ≥ 27-29 °C. If it is also meant to last a 30 min control cycle, it gets set higher still, and the inverter, seeing a large error, ramps far above minimum. That fits catch-up runs drawing ~3 kW at +2 °C with 31-36 °C setpoints, while steady-state need at +2 °C is ~26-30 °C supply [calc]. The "high temperature" is largely a by-product of how starts are triggered, not a need of the slab.
2. **A 30 min setpoint cadence cannot "ride" minimum output.** To keep the inverter at minimum frequency, the setpoint has to track the slowly rising outlet within ~1-2 K during a run. That is a minutes-scale loop.
3. **Chasing room temperature within the day is fighting physics.** With a 3-5 h pipe→room delay [6][8] and C/H ≈ 1.5-2 days, any intra-day feedback without prediction oscillates [6][7][27].
4. **Hot-water cycles break space-heating runs.** Each interruption creates an extra space-heating start, often at a moment when the circuit holds hot water. This is a scheduling problem, not a slab problem.

### B. Three control logics worth implementing and A/B-testing

All three share these rules:
- No room-by-room valves closing (all loops open, constant pump speed).
- An outdoor signal smoothed over 24 h, or a forecast mean of the next 12-24 h [1][2].
- A daily room-temperature trim, not an hourly one [1][2][7].
- Water temperature during any run kept just high enough to absorb the heat at minimum compressor speed.

**Logic 1 - "TABS classic" (feed-forward curve + daily trim; simplest; confidence medium-high)**
- Supply setpoint = 26 + 0.4·(0 − T_out,24h) °C, clamped to 24-35 °C. That is ≈ 26 °C at 0 °C, 30 °C at −10 °C and 34 °C at −20 °C, close to Olesen's best TABS curve [4] and the §2 table.
- In mild weather the Versati's own hysteresis then acts as the slab thermostat: it restarts when the circulating water (≈ slab temperature) falls ΔT-Heat below the setpoint. The setpoint therefore has to sit ≈ ΔT-Heat above the lowest acceptable slab-water temperature; the daily trim below finds that offset automatically.
- Daily trim: at 06:00 compute e = 22.0 − mean(T_room over the last 24 h). Shift the curve by Δ = clamp(Δ_prev + k·e, ±3 K) with k ≈ 1.5-2 K per K of error, and apply the change in steps over ~12 h [2][7]. Optionally also use the 24 h minimum for a low-side guard as in Gwerder [2].
- Set ΔT-Heat to its minimum (2 K, if this model accepts it [15]) so the unit cycles itself around a low setpoint.
- Expected behaviour: in mild weather the unit cycles at low water temperature with self-regulation intact; in cold weather it runs continuously.
- Risk: solar overshoot, because it is feed-forward only.

**Logic 2 - "Energy budget + PWM at minimum output" (slab as battery; confidence medium)**
- Each morning (or rolling), compute the heat to deliver over the next 24 h:
  E = Ĥ·Σ(22.0 − T_out,forecast)·Δt − Ĝ_solar·Σ irradiance·Δt − internal gains + C·(22.0 − T_room,now).
  This is Gwerder's PWM idea moved from the pump to the compressor [1].
- Deliver E in N runs, with N chosen so that each run swings the room ≤ ±0.4-0.5 K. At +10 °C that is ~3 runs of ~3 h [calc]. Never run < 60 min; aim ≥ 2 h.
- During a run, update the setpoint every 1-5 min to setpoint = max(outlet + 1.0-1.5 K, return + loop ΔT + 0.5 K) so the inverter stays at minimum frequency. The setpoint follows the slab up slowly rather than leading it.
- End a run by dropping the setpoint well below outlet once the run's energy quota is delivered (heat meter, or P_min × time), or if room ≥ 22.5 °C.
- Start a run by setting setpoint = outlet + ΔT-Heat + 0.5 K, then hand over to the riding rule once the compressor is confirmed on. **Test** whether lowering the setpoint mid-run stops the compressor on this firmware (unknown).
- Prefer runs in the warmest hours of the day (higher COP: +2 °C → +8 °C air is worth ~10-20 % [calc], at the upper end per Carnot scaling) and in PV-surplus hours. Append DHW to the end of the midday run.
- Use the return temperature after ≥ 20-30 min of pump-only circulation as the slab-state sensor. This is Gwerder's "purge phase": circulate, measure, then decide [1].

**Logic 3 - "Forecast / MPC-lite" (confidence medium-low until the model is validated)**
- Grey-box model with 2 states (slab, room), parameters C ≈ 6.6 kWh/K, H ≈ 0.14-0.20 kW/K, a pipe→room delay of ~3 h, and a fitted solar aperture. Fit on the house's own history.
- Hourly re-plan over 24-48 h. Minimise electricity cost using COP(T_air, T_water) and the value of PV surplus (or simply minimise kWh_el).
- Constraints: room 21.6-22.6 °C, ≤ 0.5 K/h drift, runs ≥ 2 h, ≤ 4 starts/day in mild weather, supply ≤ slab + 5 K in mild weather.
- Fall back to Logic 1 if the forecast or model fails.
- Literature supports the direction (MPC: [6][18][40][41]); gains vs a well-tuned Logic 1 are uncertain (likely single-digit to low-teens %).

**Below the balance point all three converge.** Load equals P_min at T_out ≈ 22 − 3.75/H ≈ −5 °C (H = 0.14), ≈ 0 °C (H = 0.17), ≈ +3 °C (H = 0.20) [calc], somewhat lower with internal gains. Colder than that, run continuously on a low curve and let the inverter modulate; this is where weather compensation shines [21].

### C. Starting parameter values (to be tuned; confidence medium)

| Item | Start value | Why |
|---|---|---|
| Room band (mild weather) | 21.6-22.6 °C around 22.0 | ±0.5 K → ~3 starts/day at +10 °C [calc]; ≤ 1 K p-p and < 2 K/h per ISO 7730 [9] |
| Minimum run / minimum off | 60 min / 45-60 min (aim runs ≥ 2 h) | start losses negligible above ~15 min [16]; slab tolerates long runs |
| Max starts per day | 4-6 (mild weather) | [calc] for ±0.4-0.5 K band |
| Supply during mild-weather runs | ≈ return/slab + 3-5 K; typically 26-30 °C | §2 table; COP +15-20 % vs 35 °C [calc] |
| Continuous-regime curve | ~26 °C @ 0 °C, ~30 °C @ −10 °C, ~33-35 °C @ −20 °C | [4], §2 table |
| Absolute supply cap | 35 °C (allow 38 °C only below −15 °C if room falls) | surface stays ≤ 27.5 °C [calc] |
| Outdoor input | 24 h moving mean, or forecast mean of next 12-24 h | [1][2] |
| Daily trim | gain 1.5-2 K/K, limit ±3 K, applied over ~12 h | [2][7] |
| ΔT-Heat (Gree) | 2 K (test), else keep 4 K and use start-then-ride logic | [15]; lets starts happen near slab temperature |
| UFH loops | all open, actuators removed or set ≥ 24 °C as limiters | [13][14][21][28] |
| Flow | fixed, ≥ 1.0-1.2 m³/h if the hydraulics allow (ΔT ≈ 3 K at P_min) | [1][13][26] |
| DHW | once a day, after or at the end of a space-heating run, in the PV/warm window | avoid extra starts (§A.4) |
| Solar rule | if tomorrow's forecast irradiance > threshold, skip or shorten the morning/midday charge; deliver in the evening/night before instead | [9][26][36][37] |

### D. What to avoid (confidence high)

- Triggering starts by writing large setpoint jumps and leaving them for 30 min. This produces 31-39 °C water and kW-level catch-up power [calc].
- Hourly room-temperature PID on the supply setpoint. The slab lag guarantees overshoot [6][7][27].
- Deep night setbacks (> 2 K) and "off" periods longer than the band allows. They save little in a slab and buy recovery at high water temperature [21][33][calc].
- Room actuators closing loops, or a curve that is "too high, and stats cut it". Both raise water temperature and destabilise flow [13][21][28].
- Charging the slab in the morning of a sunny day [9][26].
- Judging a change in less than 2-3 days. One owner suggests a whole season for curve tuning [25][31]; the room settles over ~1-3 days [6][calc].

### E. How to test (concrete, cheap)

1. **Characterise the slab.** Do a step test in mild, overcast weather. Hold a fixed 28 °C setpoint for 6 h, then off for 12 h. Log supply, return, room, outdoor and electricity (and heat if metered). Fit C, H, the pipe→room delay, and the effective K_H·A from return temperature vs room. Read the actual floor area and covering.
2. **Validate the restart behaviour.** At ΔT-Heat 4 vs 2 K, find the lowest setpoint that reliably restarts after an off-phase, and whether lowering the setpoint mid-run stops the compressor.
3. **Find the minimum-output water temperature.** At +5…+10 °C outdoor, ride the setpoint ~1 K above the outlet and record outlet/return, compressor frequency and power. This gives the lowest feasible run temperature.
4. **A/B on paired days** with similar 24 h mean outdoor temperature and irradiance: current controller vs Logic 1 vs Logic 2. Metrics:
   - kWh_el per degree-day;
   - delivered heat / kWh_el;
   - starts/day and runs < 30 min;
   - mean supply temperature while the compressor runs;
   - room min/max/mean and time outside 21.5-22.7 °C.
   Expected (hypothesis): Logic 1 or 2 cuts mean run supply temperature by 4-8 K and raises daily COP by ~10-20 % in the 0…+10 °C band, with ≤ 4-6 starts/day.

### F. Confidence summary

- **High:** low water temperature, all loops open, no deep setbacks, daily rather than hourly feedback, and a 24 h-smoothed or forecast outdoor input. Strong agreement across peer-reviewed TABS work, standards physics and field anecdotes [1][2][4][5][6][7][13][21].
- **Medium:** "ride the minimum" PWM with long runs, timing runs to warm/PV hours, ΔT-Heat = 2 K. Physics is sound, but it depends on undocumented Gree firmware behaviour and this house's real K_H·A.
- **Medium-low:** exact parameter numbers in §C. They rest on an assumed floor area and covering; the step test in §E fixes them.

## Contradictions and open questions

- **Room feedback or not?** Olesen's simulation says room temperature input is unnecessary when supply follows outdoor temperature [4]. Gwerder and Raftery add day-to-day room feedback for robustness and energy [2][7]. A real low-energy house needed a room thermostat because of incidental gains [26]. Reconciliation: feed-forward does the heavy lifting, slow (daily) feedback corrects model error, and fast thermostat action only works at very low flow temperatures (≤ 25-26 °C) where the slab cannot overshoot much [26].
- **Intermittent vs continuous:** TABS PWM saves pump energy and enables time-shifting but costs heating energy through lost self-regulation unless combined with room feedback [2]. In this house intermittency is forced by P_min > load, so the question is how to cycle, not whether.
- **Response time numbers differ by definition and construction:** τ95 4.9 h type-A median [8] vs τ63 4-8 h [7] vs 3 h delay + 3.2 days settling [6] vs 9.9 h (charging) / 100 h (coasting) [1] vs ~1 h anecdote [27] vs 10-15 h heat-meter lag [26]. These are not contradictory physics; they measure different things (surface vs room, 63 % vs 95 %, pump on vs off). This house's own step test is the only number that matters.
- **Cycling penalty size:** ~1-2 % (Uhlmann & Bertsch abstract) vs 2-5 % for very short cycles (same group, conference) [16] vs owners' "≤ 6 cycles/h OK" and "≤ 10 min runs bad" rules [25]. Defrost, oil return and wear are not captured by COP-only studies.
- **Setback:** owner data from a low-mass radiator house show savings [23]; Rutz & Moran show setback can increase heat-pump cost [20]; installers cap it at 2-3 K [21][33]. Slab-specific measured data were not found in this sweep.
- **Floor comfort limit:** EN 1264's 29 °C [5] vs Chinese subjects preferring 29-32 °C [12]. Not binding here.
- **Pulsed flow:** −24 to −27 % required flow in radiant slabs (simulation abstract) [38] vs ≤ 3 % energy effect in 65 mm screed [17]. Different metrics; for this house flow pulsing is not a priority.
- **Lower flow temperature increases minimum output on some units** [24]. Lowering the water temperature may raise cycling frequency even as COP improves. Net effect for the Versati: unknown, so measure.

Open questions specific to this house:
1. Actual active floor area, screed thickness and covering (K_H), and whether the 6.6 kWh/K figure is slab-only or whole-house effective capacity.
2. Versati firmware: exact stop rule (outlet ≥ setpoint + ? K), minimum on/off timers, whether a mid-run setpoint decrease stops the compressor, whether ΔT-Heat = 2 K is accepted over Modbus on this model, and minimum output vs outdoor and water temperature.
3. Does the circulation pump run during compressor-off periods? If not, the outlet sensor reads stale water, the restart logic misbehaves, and the slab-state estimate must come from the room or return after a purge.
4. Window orientation and solar aperture: how many kWh of solar gain arrive on clear winter/spring days?
5. Are there manifold actuators/thermostats, and do they close?
6. Comfort tolerance of the occupants: is a 21.6-22.6 °C band acceptable, or must it be 21.8-22.2 (more starts)?
7. Real-house measured comparisons of MPC vs good feed-forward for slab-UFH heat pumps did not appear in this sweep; the search budget ran out before targeted searches (Verhelst/Helsen, Halvgaard, PV-self-consumption field studies) could be run.

## Sources

1. Control of thermally activated building systems (TABS) in intermittent operation with pulse width modulation - M. Gwerder, J. Tödtli, B. Lehmann, V. Dorer, W. Güntensperger, F. Renggli (Siemens/Empa), Applied Energy 86:1606-1616 - 2009 - https://www.sysecol2.ethz.ch/OptiControl/LiteratureOC/Gwer_09_AE_86_1606.pdf - lab + paper - PWM law, purge phase, 5 h heating period, 1-3 K shift, τ = 9.9 h on / 100 h off, resistance ratios.
2. Control of thermally activated building systems (CLIMA 2007) - M. Gwerder, J. Tödtli, B. Lehmann, F. Renggli, V. Dorer (Siemens/Empa) - 2007 - https://sid.siemens.com/api/khub/documents/nqXZtSuC0od3uV1aZJ5VhA/content - paper (simulation) - modular control; 24 h mean outdoor; day-to-day room PID on 24 h min/mean; PWM 47 % pump time but more heating energy without feedback.
3. Control of thermally-activated building systems (TABS) - Gwerder, Lehmann, Tödtli, Dorer, Renggli, Applied Energy 85(7):565-581 - 2008 - https://ideas.repec.org/a/eee/appene/v85y2008i7p565-581.html - paper (abstract read) - unknown-but-bounded method and comfort guarantee within gain bounds.
4. Operation and control of thermally activated building systems (TABS) - B. W. Olesen, REHVA Journal - 2011 - https://rehva.eu/rehva-journal/chapter/operation-and-control-of-thermally-activated-building-systems-tabs - paper (simulation) - night-only operation, mean vs supply control, best winter curve, 2 K dead-band, ~20 % saving from 21-23 °C band.
5. New European standards for design, dimensioning and testing embedded radiant heating and cooling systems - B. W. Olesen (DTU), CIB/IRBnet - c. 2007 - https://www.irbnet.de/daten/iconda/CIB8359.pdf - paper (standards summary) - q = 8.92·Δθ^1.1, ~11 W/m²K, 29/35 °C limits, 99/165 W/m², EN 15377-3 TABS diagrams.
6. Thermal Modelling of Water-Based Floor Heating Systems - supply temperature optimisation and self-regulating effects - H. Karlsson, Chalmers PhD thesis - 2010 - https://publications.lib.chalmers.se/records/fulltext/111900.pdf - paper (simulation + lab validation) - 3 h delay, 3.23 days settling, self-regulation factor −0.64…−0.77, MPC only follows daily trend, COP 3.5 vs 4.9.
7. A new control strategy for high thermal mass radiant systems - P. Raftery, C. Duarte, S. Schiavon, F. Bauman (CBE UC Berkeley) - 2017 - https://escholarship.org/uc/item/5tz4n92b - paper (simulation) - 4-8 h time constants, US practice survey, slab loop + daily reset, up to 35 % energy / 40 % cost.
8. A novel classification scheme for design and control of radiant system based on thermal response time - B. Ning, S. Schiavon, F. Bauman, Energy and Buildings 137 - 2017 - https://escholarship.org/uc/item/2j75g92w (summary read at https://www.ingenio-web.it/articoli/dagli-usa-un-nuovo-metodo-di-classificazione-per-i-sistemi-radianti/) - paper (simulation; secondary summary read) - τ95 classes and medians by ISO 11855 type.
9. Thermal Storage in a Heat Pump Heated Living Room Floor for Urban District Power Balancing - R. P. van Leeuwen, J. B. de Wit, J. Fink, G. J. M. Smit, SMARTGREENS 2014 - 2014 - https://www.scitepress.org/Papers/2014/49163/49163.pdf - paper (simulation) - ISO 7730 limits, 1.6 kWh per 2 h pulse, 6 % storage loss, solar limits storage.
10. Influence of envelope, structural thermal mass and indoor content on the building heating energy flexibility - H. Johra, P. Heiselberg, J. Le Dréau, Energy and Buildings 183:325-339 - 2019 - https://vbn.aau.dk/ws/files/290247579/Influence_of_envelope_structural_thermal_mass_and_indoor_content_on_the_building_heating_energy_flexibility_accepted_manuscript.pdf - paper (simulation) - >24 h coasting in insulated houses, saturation beyond 6 h, +3.3-6.3 % energy, UFH +8-44 % flexibility.
11. Energy flexibility of residential buildings using short term heat storage in the thermal mass - J. Le Dréau, P. Heiselberg, Energy 111:991-1002 - 2016 - https://econpapers.repec.org/RePEc:eee:energy:v:111:y:2016:i:c:p:991-1002 - paper (abstract read) - storage vs conservation strategies, emitter dependence.
12. Comfortable floor temperatures for radiant floor heating in Southern China - Y. Wu, H. Liu, B. Li, X. Lu, L. Chen, R. Kosonen, Chinese Science Bulletin 66(19) - 2021 - https://acris.aalto.fi/ws/portalfiles/portal/66233514/ENG_Wu_et_al_Comfortable_floor_temperatures_for_radiant_Chinese_Science_Bulletin.pdf - field/human-subject study - neutral ~28 °C, preferred 29-32 °C.
13. Lette gulvarmesystemer og deres indflydelse på varmepumpers effektivitet - O. Paulsen, M. F. Olesen, S. Ø. Jensen (Teknologisk Institut) - 2014 - https://www.teknologisk.dk/_/media/69871%5FLette%20gulvarmesystemer%20og%20deres%20indflydelse%20p%E5%20varmepumpers%20effektivitet.pdf - report (simulation + EnergyFlexHouse experience) - 5-20 % output per K, zone-valve flow fluctuation, 3 K excess supply, ~12 % part-load COP penalty.
14. Under floor heating and heat pump optimization (EUDP 64014-0548) - Teknologisk Institut, Caverion, Bosch, Halicon, Aalborg University - 2015-2017 - https://energiforskning.dk/en/node/15159 - project summary - supply set too high + fluctuating flow; ~15 % theoretical COP potential.
15. Gree Versati III owner's manual, commissioning parameter page - Gree - n.d. - https://www.manualslib.fr/manual/387287/Gree-Versati-Iii.html?page=19 - manufacturer - ΔT-Heat 2-10 K, ΔT-Room 1-5 K, WOT-Heat range.
16. Theoretical and experimental investigation of startup and shutdown behavior of residential heat pumps - M. Uhlmann, S. S. Bertsch, Int. J. Refrigeration 35(8):2138-2149 - 2012 - https://iifiir.org/en/fridoc/theoretical-and-experimental-investigation-of-startup-and-shutdown-135447 - lab + field (abstract read; conference figures via search summary) - 1-2 % cycling loss for air-source, insignificant above ~15 min runs.
17. Grindinio šildymo sistemos techninių parametrų įtaka sistemos veikimo rodikliams (Influence of underfloor heating system technical parameters on system performance) - T. Valionis, KTU MSc thesis - 2022 - https://epubl.ktu.edu/object/elaba:116465061/116465061.pdf - paper (simulation) - pulsed flow ≤ 3 % saving in 65 mm screed; pipe spacing dominates inertia.
18. Price-responsive model predictive control of floor heating systems for demand response using building thermal mass - M. Hu, F. Xiao, J. B. Jørgensen, R. Li, Applied Thermal Engineering 153:316-329 - 2019 - https://orbit.dtu.dk/en/publications/price-responsive-model-predictive-control-of-floor-heating-system/ - paper (simulation; abstract) - MPC shifts load, preheat timing depends on weather and price.
19. Thermal performance of radiant floor under non-uniform solar radiation (Lhasa office) - Building Simulation 16(1):105-120 - 2023 - https://www.sciopen.com/article/10.1007/s12273-022-0928-6 - paper (validated simulation; abstract) - 35.6 °C sunlit floor, +8.5 K, 171 vs 79 W/m².
20. Night setback with residential heat pumps (control strategies) - Rutz & Moran, Energy 15(11):935-941 - 1990 - https://ideas.repec.org/a/eee/energy/v15y1990i11p935-941.html - paper (simulation; abstract) - setback can increase heat-pump cost unless the control is building/HP-aware.
21. Vaillant sensoCOMFORT heat pump controller guide - Heat Geek - n.d. (2020s) - https://www.heatgeek.com/vaillant-sensocomfort-heat-pump-controller - blog (installer) - weather compensation first, ≤ 2-3 °C setback, stats/zones as limiters, 45 vs 55 °C = 20-30 % COP.
22. Heatpump turning on and off - is this normal? - OpenEnergyMonitor forum - 2022 - https://community.openenergymonitor.org/t/heatpump-turning-on-and-off-is-this-normal/22149 - forum (owner data) - UFH-only house 48 → 40 °C flow cut ~60 → ~45 kWh/day.
23. Setback vs continuous trials (Ecodan, low-mass radiator house) - Renewable Heating Hub forum - 2024 - https://renewableheatinghub.co.uk/forums/postid/28542 - forum (owner measurements) - setback saved 2.4-8.2 kWh/day; ~9 kWh/day below 3 °C.
24. Ecodan: is there actually such a thing as a minimum flow temp to avoid cycling? (p. 3) - Renewable Heating Hub forum - 2024-25 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/ecodan-is-there-actually-such-a-thing-as-a-minimum-flow-temp-to-avoid-cycling-and-why-if-so/paged/3/ - forum - minimum output 2.9-3.2 kW at 35 °C and 4-7 °C outdoor, rising at lower flow temperature; 6-8 min cycles at 25-28 °C.
25. Heat pumps and on/off working: starting to quantify it (p. 10) - Renewable Heating Hub forum - 2024 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/heat-pumps-and-on-off-working-starting-to-quantify-it/paged/10 - forum - Cantor argument, slab coasting, curve 30 °C @ −5 / 25 °C @ +20, COP ~5, cycling thresholds.
26. Do low energy houses really need heating controls? - Buildhub forum (JSHarris, pdf27, ragg987 and others) - 2017-18 - https://forum.buildhub.org.uk/topic/4375-do-low-energy-houses-really-need-heating-controls - forum (owner measurements) - self-regulation fails without room feedback, 10-15 h lag, > 1 kW solar gain, 1,050 l/h, 12 h timer hurt COP, ventilation cannot dump heat.
27. Underfloor heating control - openHAB community - 2021 - https://community.openhab.org/t/underfloor-heating-control/128904 - forum - ~1 h slab time constant, overshoot with on/off, predictive extrapolation helps, solar pre-emption idea.
28. Fußbodenheizung bei Wärmepumpe steuern (p. 2) - simon42 Home Assistant community - 2024 - https://community.simon42.com/t/fussbodenheizung-bei-waermepumpe-steuern/34105?page=2 - forum (DE) - removing single-room control: −30 % kWh, ≤ 3 cycles/day; 2.5-3 %/K.
29. Vloerverwarming + weersafhankelijke regeling onconfortabel?? - Klusidee forum - 2009 - https://www.klusidee.nl/Forum/topic/vloerverwarming-weersafhankelijke-regeling-onconfortabel.44190/latest - forum (NL) - weather compensation plus room thermostat as maximum limiter.
30. Jedno ustawienie i nawet 20% oszczędności (krzywa grzewcza w pompie ciepła) - KB.pl - 2024-25 - https://kb.pl/aktualnosci/ogrzewanie/co-to-jest-krzywa-grzewcza-w-pompie-ciepla/ - blog/news (PL) - 2-3 %/K, 10-20 % from lowering the curve, single case −70 kWh/month.
31. Krzywa grzewcza - jak poprawnie ją ustawić? Typowe problemy i ich rozwiązania - Globenergia - n.d. - https://globenergia.pl/krzywa-grzewcza-jak-poprawnie-ja-ustawic-typowe-problemy-i-ich-rozwiazania/ - blog (PL) - curve-end adjustment rules, ±5 K shift, season-long tuning, outdoor-sensor siting.
32. Underfloor heating setback controls (FAQ) - Grant UK - n.d. - https://www.grantuk.com/knowledge-hub/faqs/underfloor-heating-setback-controls/ - manufacturer - setback rather than off keeps screed warm.
33. Underfloor heating: restart before the first cold snap - Selectra UK - 2025 - https://selectra.co.uk/energy/news/underfloor-heating-restart-before-first-cold-snap - blog - Viessmann ≤ 2 °C setback, ~35 °C flow, hours-scale response.
34. Puzzling Heat Pump Efficiency Data (Daikin Altherma 3 HHT) p. 2 - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/puzzling-heat-pump-efficiency-data-daikin-altherma-3-hht/29678?page=2 - forum (owner data) - 4.4 kW minimum, +0.43 K/h on / −0.26 K/h off, deliberate long-run thermostat banding.
35. Effizienzanalyse von Wärmepumpen im EFH-Bestand auf Basis von Feldtestdaten (WPsmart im Bestand) - D. Günther, J. Wapler et al., Fraunhofer ISE (Chillventa slides) - 2020 - https://www.ise.fraunhofer.de/content/dam/ise/de/documents/publications/conference-paper/091_Fraunhofer-ISE_Chillventa-2020_1015_EFFIZIENZANALYSE%20VON%20W%C3%84RMEPUMPEN%20IM%20BESTAND.pdf - field data (slides) - context: 41 comparable monitored systems; mean ASHP flow 34.6-52.4 °C at −3 °C mean outdoor in existing houses.
36. The effect of solar radiation on dynamic thermal performance of floor heating systems - A. K. Athienitis, Y. Chen, Solar Energy 69:229-237 - 2000 - https://data.zhenzhi.com/details/1/911475063 - lab/outdoor test room (abstract via search summary only) - sunlit patch ~8 °C warmer, ≥ 30 % energy reduction from floor storage.
37. Experimental study on the effects of direct sun radiation on the dynamic thermal behavior of a floor-heating system - Université de Reims (HAL) - 2020 - https://hal.univ-reims.fr/hal-02877179v1 - lab (search snippet only; page bot-blocked) - ~4 °C overheating persisting ~8.5-11.5 h after the sun patch.
38. Performance analysis of pulsed flow control method for radiant slab system - H. Tang, P. Raftery, X. Liu et al., Building and Environment - 2018 - https://escholarship.org/uc/item/31s4x6jr - paper (simulation; abstract via search, PDF not text-extractable) - −27 %/−24 % required flow at 50 % part load.
39. Potential of structural thermal mass for demand-side management in dwellings - G. Reynders, T. Nuytten, D. Saelens, Building and Environment 64:187-199 - 2013 - https://www.researchportal.be/nl/publicatie/potential-structural-thermal-mass-demand-side-management-dwellings - paper (abstract via search only) - strong peak-shifting potential; emitter-mass interaction matters.
40. Predictive control of intermittently operated radiant floor heating systems - S. H. Cho, M. Zaheer-uddin, Energy Conversion and Management 44:1333-1342 - 2003 - https://data.zhenzhi.com/details/1/907636914 - simulation + experiment (abstract via search only) - 10-12 % savings in cold months, more in mild weather.
41. OptiControl results (Clima 2010) - D. Gyalistras et al. (ETH/Siemens/MeteoSwiss) - 2010 - https://infoscience.epfl.ch/record/169732/files/Gyal_10_Proc-Clima2010.pdf - paper (simulation; search snippet only, fetch failed) - 1-15 % improved rule-based vs 16-41 % theoretical predictive.
42. AIS Space Heating and DHW - Kensa Heat Pumps - 2019 - https://www.kensaheatpumps.com/wp-content/uploads/2019/12/AIS-Space-Heating-and-DHW-V1.pdf - manufacturer (search snippet only; now redirects) - leave ~25 % of UFH zones open or fit buffer; remove manifold mixing valves.
43. Freund aller Wärmepumpen (flyer) - Homematic IP / eQ-3 - n.d. - https://homematic-ip.com/sites/default/files/downloads/170173_HmIP_Flyer_Freund-aller-Waermepumpen.pdf - manufacturer (search snippet; PDF had no extractable text) - on/off floor valves make heat pumps cycle.
44. Thermal mass heat recovery, floor heating vs radiators (Politecnico di Milano) - 2025 - https://re.public.polimi.it/handle/11311/1299832 - paper (search snippet only; 403) - 50 % of stored heat recovered after 1 day (floor) vs 3 days (radiator).
45. Experimental analysis of model predictive control for an energy efficient building heating system - J. Široký, F. Oldewurtel, J. Cigler, S. Prívara, Applied Energy 88(9):3079-3087 - 2011 - https://ideas.repec.org/a/eee/appene/v88y2011i9p3079-3087.html - field experiment (search snippet only) - two-month MPC trial in a Prague building; a related paper reports ~10 % vs weather-compensated control (figure not confirmed for this paper).
46. Self-Regulating Floor Heating Systems in Low Energy Buildings - H. Karlsson, 8th Nordic Building Physics Symposium - 2008 - https://research.chalmers.se/en/publication/73021 - paper (abstract via search) - floor heat flux rises when indoor air cools and can be fully blocked when it is warm.
47. Värmekurva NIBE F750 and related threads - byggahus.se forum - 2020s - https://www.byggahus.se/forum/threads/varmekurva-nibe-f750.506413/ - forum (SE; search snippet only, 403) - slab curve 4-5 offset −1; room sensor for display, not control.
48. Optimali temperatūra šildymo sistemoje: grindinis ir radiatorinis šildymas (and related pages) - finonamai.lt - n.d. - https://finonamai.lt/informacija/kokia-turi-buti-sildymo-sistemoje/ - blog (LT; search snippet only) - UFH 25-38 °C, thermostats regulate flow only, frequent loop closing lowers heat-pump efficiency.

49. Selbstregeleffekt der Fußbodenheizung (technical document) - Oventrop - n.d. - https://www.oventrop.com/de-DE/file/i/be8841db-053e-4f4f-a8af-4aa6f84d9d2c?Download=1 - manufacturer (search snippet only; 403) - self-regulation example 30 → 20 W/m² with an open circuit; fails when other heat sources warm the room.

Search budget note: 34 web searches were run before the shared search budget was exhausted. Further targeted searches (Verhelst/Helsen modulating ASHP + floor heating optimal control; Halvgaard economic MPC; measured PV self-consumption with UFH) could not be run; they are listed as open gaps above.
