# Setback, constant temperature and comfort bands

Researcher topic 11. Scope: night setback and eco modes with heat pumps and slab underfloor heating (UFH), what recovery boosts cost, comfort perception with radiant floors, acceptable room-temperature bands, manufacturers' "set and forget" advice, and how a controller should express comfort constraints. The house's own controller code was deliberately not read.

**Method note (read this first).** This session's shared web-search budget (200 searches across all 15 researchers) was already spent when this topic started. All three of my search attempts were refused, so **no new web searches were run for this note**. Instead I:
- fetched 36 web pages directly, from URLs I already knew or that sibling notes cited (01-08 in `docs/research/notes/`);
- read the full text of 13 PDFs that sibling researchers had downloaded in this session (field reports, papers, manuals) and searched them for setback and comfort content.

The sources lean UK/German/Danish. No Lithuanian- or Polish-language setback sources could be found without search. I did no non-English searching. The few non-English sources (German, Dutch) are ones I could reach directly. "[calc]" marks my own arithmetic on the house figures from the brief (H ≈ 0.14-0.20 kW/K, C ≈ 6.6 kWh/K, minimum output P_min ≈ 3.7 kW, target 22.0 °C).

## Summary

- **For air-source heat pumps, the measured evidence does not support night setbacks; the only setback "savings" come from simulations or from radiator houses with a confounded baseline.**
  - One owner's hourly regression (Midea 14 kW, radiators) put setback-period COP 5.5 % lower at 8 °C outdoor and 8.3 % lower at 12 °C than in continuous operation [3].
  - The same owner's balance: about 4.1 kWh of heat "saved" during a 6 h setback, versus about 4.5 kWh re-delivered at COP 3.54 instead of 5.21. That is about 38 % more electricity for the recovery than the loss it avoided [3].
  - A setback day vs a continuous day showed −4 % input energy, but the room was 1.5 K cooler and the curve 3-4 K hotter (COP 3.9 vs 5.1). This is not like-for-like [2].
- **The large peer-reviewed field analysis (HeatPumpMonitor.org vs UK Electrification of Heat) recommends a narrow room band (e.g. 18-20 °C) over large setbacks [1].**
  - Large setbacks force higher recovery flow temperatures and lower SPF.
  - Stop-start, full-capacity operation is less efficient than modulating to demand [1].
- **Every +1 K of flow temperature costs about 2-3 % COP, so a "catch-up" at 36-39 °C instead of about 29 °C costs roughly 15-25 % more electricity for every kWh delivered that way.**
  - The per-K figure comes from Mitsubishi (2 %/K) [27], Danish Technological Institute (2-3 %/K) [39][40] and HPM field data (SPF ≈ 4.4 at 30 °C average flow, 3.9 at 35 °C, 3.4 at 40 °C) [28].
- **Simulations that do find setback savings are for ground-source units or radiator houses, and savings fall to zero or turn negative once realistic constraints are added.**
  - Mimer/DECC TRNSYS, ground-source heat pump (GSHP) with UFH, January: a 20 → 16 °C night setback (22:00-03:00) saved more than 6 % running cost; a 12 °C setback saved more than 10 %, with internal gains ignored [7].
  - OpenEnergyMonitor (OEM) dynamic simulator, 3.4 kW radiator house: 12-15 % saving from a 17 °C setback. When the setback was required to undershoot less, intermittent heating used 3.6 % *more* electricity [5].
  - A GSHP does not lose COP at night; an air-source unit does, because night air is colder.
- **Installer and manufacturer guidance for heat pumps converges on "no setback, or at most 2-3 K", with ≤ 2 K for heavy screed or slab floors.**
  - At most 2 K: NRCan [24], Viessmann via Selectra [22], eco+Logic for floor-sensing zones [26].
  - At most 2-3 K: Heat Geek [18] and Octopus [21]; 1-3 K "rather than off" [21].
  - Two outliers: Nu-Heat suggests 4-6 K for new builds with a fast low-mass floor and says screed > 65 mm reaches comfort faster with a *smaller* setback [25]. Grant claims setback raises efficiency but gives no numbers [23].
- **A comfort *band* beats a scheduled setback.**
  - TABS simulation: lowering the lower band limit from 22 to 21 °C cut winter heating energy by about 5 % (Würzburg) to about 15 % (Venice). The authors cap the dead band at 2 K [11].
  - The saving comes from letting the slab "coast" inside the band, not from scheduled cold periods.
- **Comfort limits relevant to a controller:**
  - ISO 7730 cyclic swings ≤ 1 K peak-to-peak and drift < 2 K/h [8].
  - ASHRAE 55 drift ≤ 1.1 K in 15 min and ≤ 2.2 K in 1 h [14].
  - Floor surface 19-29 °C [14] (ISO 7730 dissatisfaction model gives 19-28 °C [8]; EN 1264 occupied-zone cap 29 °C [22]).
  - People detect about 0.38 K differences between rooms at 24 °C, while individual preferences differ by 2-5 K [15].
- **For this house, the ISO 1 K peak-to-peak limit sets the minimum number of compressor starts per day in mild weather [calc].**
  - With P_min = 3.7 kW, load 1.7 kW and C = 6.6 kWh/K, a 1 K allowed swing gives about 3.3 starts/day with 3.3 h runs. A ±0.25 K band (0.5 K) forces about 6.7 starts/day; a ±0.15 K band forces about 11.
  - The comfort-band width is the main knob for mild-weather cycling.
- **Slab storage costs little in heat loss.** In a Dutch low-energy-house simulation, short floor "charges" of 1.6 kWh each lost only 6 % of the charged energy and stayed inside the comfort limits; the room rose < 0.5 K/h [8].
  - So moving heat to the warm or PV hours is cheap. Cooling the slab overnight and reheating it later is what costs.
- **Comfort constraints are best expressed as soft limits with an explicit budget, plus a few hard guards.**
  - Kuboth's 125-day twin-rig MPC used a 20-24 °C band, penalising undershoot at 0.5 €/Kh and overshoot at 0.1 €/Kh [12].
  - EPFL's Kelvin-hour (Kh) budget MPC lets the user state allowed violation severity in advance. The field deployment stayed close to or below its budgets [13].
- **Owners report that the simplest strategy wins on slab floors.**
  - Two BuildHub slab-UFH homes: one runs 24/7; the other uses a room stat at 0.1 K hysteresis with flow ≤ 25-26 °C. A 12 h timer "noticeably" lowered COP [30].
  - A German owner (200 m², air-to-water heat pump): after balancing and removing room-by-room control, use fell from 4000-4200 to 2800-3000 kWh/yr and starts fell from 8-10 to ≤ 3/day, at a warmer 22.5 °C [31].
  - An RHPP householder "settled on the simplest strategy, of continuous heating" [37].
- **Daytime, not night-time, is when an air-source heat pump should do its mild-weather heating.** Belgian advice is to run in the daytime for PV and the higher COP of warmer air, with night running only as a comfort guard [38]. In the OEM simulator, moving the heating window into the warmer midday raised the schedule's saving [5].
- **The setback arithmetic for this house is unfavourable [calc].** A 2 K, 8 h setback at 0 °C outdoor:
  - saves only about 2.1 kWh of heat loss, about 2.4 % of the 89 kWh day;
  - leaves 13.2 kWh to re-deliver into the slab;
  - turns into a net electricity loss if that 13.2 kWh is delivered about 7 K hotter (COP 4.0 → 3.3).
- **Lowering the *average* room temperature is the real saver.** Each 1 K saves about 4.1 kWh of heat per day: about 4.6 % of demand at 0 °C and about 10 % at +10 °C outdoor [calc]. This matches the owner rule of about 10 %/K [2] and German advice of about 6 %/K [41].

## Detailed findings

### 1. Setback with heat pumps: field and owner data

**Rosenow, Lea & Boni (Energy and Buildings 352, 2026), as reported by CIBSE Journal [1]** — peer-reviewed analysis of HeatPumpMonitor.org (HPM), Electrification of Heat (EoH) and RHPP data.
- Average SPF: 3.86 (HPM), 2.81 (EoH), 2.36 (RHPP).
- 55 % of 165 EoH Vaillant aroTHERM systems had curves set too high and cycled on room thermostats.
- Case EOH2578 ramped to unnecessarily high flows and then switched off for about 1.5 h.
- Simulated optimisation of that system (lower curve, modulation enabled, schedule start moved from 5:00 to 1:45) raised COP from 2.86 to 4.61. Electricity fell by about a third and the 6:00 peak fell from 5.1 to 1.2 kW.
- Large setbacks are named as a cause of high flow temperatures; the recommendation is a narrow band (e.g. 18-20 °C).
- Evidence type: field data plus simulation. It is the strongest source here, but none of it is slab-specific.

**cathodeRay et al., Renewable Heating Hub "Setback savings - fact or fiction?" [2][3]** — Midea 14 kW, radiators, owner-logged.
- Day pair [2]: setback day 20.38 kWh in and 78.7 kWh out (COP 3.9); continuous day 21.22 kWh in and 108.3 kWh out (COP 5.1).
  - Outdoor 10.2 vs 9.9 °C. Indoor mean 18.7 vs 20.2 °C.
  - The setback day ran a curve 3-4 K hotter (LWT 39-41 vs 37-38 °C) with throttled lockshields.
  - The owners agree n = 2 is not evidence. JamesPa notes that coasting down captures only about 1/8, not 1/4, of the naive "6 h off" saving, because the house cools gradually.
- Later regression on hourly data [3]:
  - No setback: COP = 0.346·T_out + 1.738. Setback periods: COP = 0.284·T_out + 1.988.
  - That is −5.5 % at 8 °C and −8.3 % at 12 °C. The range-binned comparison gives −1.4 % and −6.4 %.
  - Binned COP: 3.54 vs 3.77 at 5-6 °C, and 5.0 vs 5.21 at 10-11 °C.
- Energy balance of one event [3]: about 6 h setback at about 10 °C outdoor, indoor 19.9 → 18.5 °C, loss ≈ 4.12 kWh. Recovery took about 9 h at about 5.9 °C outdoor and supplied ≈ 4.54 kWh.
- Conclusion offered: little or no net saving; continuous operation probably uses less. The members' explanation is that in mild weather the unit already cycles, so a setback removes slack and forces a higher curve.

**Creative trials on night-time setbacks [4]**
- SUNandAIR (Ecodan 8.5, 180 m² low-mass cottage, 16 radiators) ran 50+ trial days. Setback days showed lower kWh at similar outdoor temperature, but no percentage was given. He later switched to Auto-Adaptation, which tightened the consumption scatter.
- cathodeRay switched off 21:00-03:00 for a week; comfort was "fine".
- On one night, outdoor air fell from 6 to 2 °C across the restart. Defrosts started at about 4-5 °C and COP dropped from about 4 to about 2 during them.
- This matters for Lithuania: a morning recovery on a humid −2 to +3 °C morning lands in the worst defrost window.

**MyForest, OEM "Improve efficiency: turn the heat pump off" [6]** — the counter-example.
- Two days at 9 °C average outdoor: COP 2.58 with continuous pumping and antifreeze flipping, versus COP 3.32 with algorithmic off-periods.
- The house has oversized K2 radiators; the restart is at about 26 °C return.
- Single-day comparisons only. Circulating water when idle cost about 200 W.
- Lesson: when continuous operation means poor low-load operation (pumps, antifreeze, mis-set curve), *planned* off-periods can beat it. This is a statement about cycling quality, not about a cold-house setback.

**RHPP final report (Lowe et al., 2017) [37]**
- Householders' setpoints ranged from 18 to 23 °C.
- The report notes that a good part-load heat pump can shift a household from intermittent to continuous heating, raising heat demand while still cutting electricity and CO2.
- One householder experimented and settled on continuous heating.

**BuildHub slab-UFH owners [30]** — anecdotal, two homes.
- JSHarris: control schemes driven by slab temperature failed. A plain room stat with 0.1 K hysteresis worked "very well" provided flow stayed ≤ 25-26 °C. The room held about 20.5-21.5 °C.
  - The heat meter lagged the room by 10-15 h, while solar and incidental gains act within tens of minutes. Vacuuming on a cold day added "a couple of degrees".
- ragg987 runs 24/7 on weather compensation: 29/26 °C flow/return, about 17 W/m² over 220 m², about 750 W electrical input. A 12 h timer lowered COP noticeably.
- Visitors add about 80-100 W each; five people raise air temperature by about 1 K in 15-30 min. Winter sun adds about +0.5 K.

**German HA community (simon42) [31]**
- Ex-manufacturer planner's advice: hydraulic balancing, heating curve, no room-by-room control, temperatures as constant as possible.
- MelleD's numbers (200 m², air-to-water): 4000-4200 kWh/yr with 8-10 starts/day at 21.5 °C before; 2800-3000 kWh/yr with ≤ 3 starts/day at 22.5 °C after balancing and removing per-room control.
  - He uses a small night reduction and a 09-19 h raise.
- Another owner limits runs to about 4 h in the day plus 03-07 h; with longer windows the unit starts cycling.
- This is anecdotal and confounded (balancing changed too), but it shows that a warmer, steadier house can use *less* energy.

**Ecodan Auto-Adaptation owners [35][36]**
- RHH trial [35]: after changing thermo-diff from +5/−5 to +3/−9 and enabling auto-adapt, flow settled at about 29 °C and the unit ran about 20 h with one cycle. Before, it cycled above 9 °C outdoor. The UFH zone overshoots from 21.5 to about 22.5 °C, which the owner likes.
- OEM [36]: on two different days, COP was 3.5 with the owner's custom controller (peak flow 40 °C) vs 4.0 on auto-adapt (peak 38 °C); rolling SCOP rose from 3.4 to 3.6. Not side-by-side.

### 2. Setback in simulation and lab work

**Mimer GeoEnergy for DECC/EA Technology, report C207-R2 (2012) [7]**
- TRNSYS single-zone house with UFH and a GSHP, January weather, 20 °C by day, free-floating 22:00-03:00.
- A 16 °C setback limit kept daytime comfort and saved more than 6 % running cost; 12 °C saved more than 10 %. No internal gains were modelled.
- Caveats: a ground source has no night COP penalty; the floor model was a generic UFH; the setback is only 5 h.

**OEM dynamic heat-pump simulator discussion (Trystan Lea et al., 2025) [5]**
- 3.4 kW radiator house, 5 kW Vaillant model:
  - setback to 17 °C with 20 °C held 13:00-22:00 saved 12-15 %;
  - a gradual warm-up from 17 °C starting 10:00 used 1,801 vs 2,117 kWh (−15 %);
  - intermittent on/off saved 8 %.
- Sensitivity: cutting the intermittent case's undershoot (from about 4,000 to about 2,200 degree-hours below setpoint) removed the saving; it then used 3.6 % more than continuous.
  - **Most "setback savings" in simulation are paid for in degree-hours of discomfort.**
- Poorly configured systems (curve too high, or fixed 50-60 °C flow at 80 % compressor speed) used 37 % more than optimised continuous heating, and 24 % more even with a setback schedule.
- On the UK Agile tariff, the cheapest case was off 16:00-19:00 with a 21 °C pre-boost at 13:00. That is price shifting, not setback.

**van Leeuwen et al., SMARTGREENS 2014 [8]**
- Dutch low-energy living room with concrete floor heating and a heat pump at a fixed COP of 4.5.
- A constant 20 °C setpoint puts most heating demand at night. A 19.5 night / 20.5 day setpoint shifts demand into the daytime at about equal total energy.
- Two-hour "storage" boosts of 1.6 kWh each lost 479 Wh of an 8 kWh charge (6 %); operative temperature rose < 0.5 K/h.
- Comfort constraints derived from ISO 7730 / ASHRAE 55: operative temperature 20-24 °C (if outdoor < 10 °C); periodic swings < 1 K peak-to-bottom; drift < 2 K/h; floor surface 19-28 °C.
- Solar absorption on a sunny day pushed the room to 21.3 °C. That is just outside the 1 K band, so it is the sun, not the heat pump, that first uses up the band.

**Raftery et al. (UC Berkeley CBE, 2017) [9]**
- High-mass radiant systems have time constants of about 4-8 h or more.
- The proposed controller *locks out* the radiant system for set hours. It cascades a zone loop onto a slab loop and uses previous-day feedback.
- It cut electricity cost by up to 40 % and energy by up to 35 % vs common US practice, with similar comfort (simulation, office, cooling-dominated).
- The authors endorse Gwerder's point that with TABS "only day-to-day room temperature compensation is promising" [9][10].

**Gwerder et al. 2009 (Applied Energy 86) [10]**
- TABS pump pulse-width modulation (PWM) with a 5 h period.
- Room setpoint range 21-25 °C, with a 1.5 K setpoint shift applied during PWM; typical shifts are 1-3 K.
- The "switched-on" phase was placed at night (22:00) for energy-cost reasons. Long off-phases worsen room-temperature control.

**REHVA Journal, TABS operation and control (Olesen) [11]**
- Comfort ranges 20-24 °C in winter (1.0 clo) and 23-26 °C in summer.
- Dead bands of 22-23, 21-23 and 21-24 °C were tested. In winter, lowering the lower limit from 22 to 21 °C cut heating by about 15 % (Venice, 842 → 713 kWh) and about 5 % (Würzburg, 1194 → 1138 kWh).
- The authors' conclusion: the dead band "should not be larger than 2 K".
- A constant average water temperature (case 1201) performed worst. An outdoor-reset supply temperature with a room-feedback term (−1.6·(T_o − 22)) performed well.

**Kuboth et al. 2020 (Energies 13, 6016) [12]** — 125-day twin test rigs, real 6 kW air-source heat pump.
- Comfort band 20-24 °C as a soft constraint: 0.5 €/Kh below the band, 0.1 €/Kh above it.
- The MPC rig showed more limit exceedance, from unforecast cold snaps, but rarely more than 1 K below the band.

### 3. What a recovery boost costs

- **COP vs flow temperature**:
  - Mitsubishi's Auto-Adaptation is built on "1 °C lower flow → +2 % COP" [27].
  - Danish Technological Institute: 2-3 % per K for a well-sized heat pump [39]; OPSYS repeats 2-3 % per K [40].
  - HPM field regression: SPF = −0.1054·(flow − outside) + 6.88, i.e. about 2.5 %/K around SPF 4 [28].
  - Swedish GSHP work finds 1-2 %/K [via sibling notes; not re-read here].
- **Fluctuating flow adds a further penalty**: Danish TI found up to 10 % COP spread at 6 K above the minimum supply temperature [39].
- **Recovery at an outdoor-temperature disadvantage**: an air-source heat pump recovering in the early morning works at the day's lowest outdoor temperature. On humid days near 0 °C it also works in the defrost-heavy zone [4].
- **Stop-start full-capacity runs** are less efficient than modulating at demand [1]. EOH2578's 5.1 kW 6:00 peak is the archetype.
- **This house [calc]**:
  - At 0 °C, the steady load (≈ 3.7 kW at H = 0.17) needs only a low flow temperature. Sibling note 05 estimates a mean water temperature of about 25-28.5 °C.
  - A 2 K recovery needs 13.2 kWh of extra heat. At the 9 kW class's mid-range output (≈ 6-7 kW at 0 °C), that is about 4-5 h of running at roughly 34-38 °C flow.
  - At −20 % COP on 13.2 kWh, the penalty is about 0.7 kWh_e, vs about 0.5 kWh_e saved by the cooler night. Break-even at best, a loss in practice, and the room spends the morning below its band.

### 4. Comfort perception with radiant floors

- **Operative temperature.** Operative temperature (t_o) is roughly the mean of air temperature and mean radiant temperature (t_mr) for sedentary people with air speed ≤ 0.1 m/s [16]. A warm floor raises t_mr, so an occupant over a 24-25 °C floor at 21.5 °C air feels close to 22 °C operative. This is an inference, not a measured figure for this house.
  - UFH delivers about 50 % of its heat convectively [47]. Air temperature alone under-reports comfort on radiant floors, and an air sensor in sunlight over-reports it [26].
- **Floor surface limits.**
  - ASHRAE 55: 19-29 °C where feet touch the floor [14].
  - ISO 7730 dissatisfaction model: 19-28 °C [8].
  - EN 1264 (BS EN 1264 via Selectra): 29 °C occupied zone, 35 °C perimeter strip; bathrooms are often allowed about 33 °C [22].
  - A Chinese study (Wu et al.) found 29-32 °C floors preferred; the PDF text was not extractable here, so this is taken from sibling note 05.
  - This house's floor never needs to exceed about 27 °C, so the floor cap is not a binding constraint.
- **Dynamic limits.**
  - ISO 7730: ≤ 1 K peak-to-peak for cyclic variation and < 2 K/h drift [8].
  - ASHRAE 55: ≤ 1.1 K in 15 min and ≤ 2.2 K in 1 h [14].
  - A slab system physically cannot breach the drift limits; only the sun or occupants can.
- **What people notice.**
  - About 0.38 K difference between two rooms is detectable at 24 °C [15].
  - Individual preferences span the equivalent of 2-5 K [15].
  - The ASHRAE comfort zone is −0.5 < PMV < +0.5, i.e. at least 80 % satisfied [15]. Roughly speaking, ±0.5 PMV corresponds to about ±1-1.5 K of operative temperature for typical clothing; this is an inference, not read from a source.
  - In practice, people complain about a *trend* (a cold morning) more than about a ±0.3 K oscillation. This is anecdotal: the Ecodan owner happily accepts 21.5 → 22.5 °C swings [35].
- **Sleep.** eco+Logic recommends the setback only in bedrooms during sleep [26]. Zukunft Altbau allows bedrooms 16-20 °C [41]. Neither applies to a single-zone slab, where the whole house would cool.

### 5. Manufacturers' and installers' "set and forget" advice

| Source | Advice | Numbers |
|---|---|---|
| Octopus Cosy [21] | Drop 1-3 °C rather than switching off; "Off" only for 24 h+ absences | Raise 1-2 °C in cheap windows; drop 2-3 °C in peak windows |
| Heat Geek [17][18] | Steady low output; setback ≤ 2-3 °C; 21/16 °C "effectively turns the heat pump off" | Room stats/TRVs only as high limiters |
| Viessmann (via Selectra) [22] | With heavy floors, setbacks > 2 °C lose most of the saving in recovery | Setback ≤ 2 °C; restart in autumn +1 °C/day |
| NRCan [24] | Setback ≤ 2 °C; deeper setbacks trigger backup heat; use smart early start | Variable-speed units may run slower after a moderate setback |
| eco+Logic UFH guide [26] | Floor-sensing zones; setback ≤ 2 K on floor control, ≤ 3 K on air control; switch 1 h before leaving and 1.5 h before return | "Consistent slab temperature" is more efficient than air-controlled fluctuation |
| Nu-Heat UFH guide [25] | New build: setback 4-6 °C (experiment); screed > 65 mm reaches comfort faster with a smaller setback | Generic UFH, not heat-pump specific |
| Grant [23] | Setback keeps the floor warm and "increases efficiency" | No numbers |
| Energy Stats UK [19][20][45] | Vaillant "Active" room modulation by default; "Expanded" (on/off) gives rollercoaster swings; avoid third-party on/off stats | Expanded: stopped 4.5 h, room 20.2 → 18.4 °C, "less efficient and less comfortable" recovery |
| Mitsubishi [27] | Auto-Adaptation: flow tracks the room trend and avoids unnecessary rises and falls | 1 K lower flow = +2 % COP |
| tado [29] | Heat-curve presets with a slower warm-up | Moderate 4 %, Eco 7 %, Eco Plus 11 % savings claimed |
| Zukunft Altbau (DE) [41][42] | Night ≥ 16 °C (mould); suspend setback while testing a house for heat pump suitability | 1 K lower ≈ 6 % saving |

Two patterns stand out:
- Nobody who sells heat pumps recommends a deep setback. The 4-6 K advice comes from a UFH supplier writing about low-mass floors [25].
- Energy Stats explicitly says even a good system is not truly set-and-forget: the owner moves the curve between 0.45 and 0.5 with the seasons [19].

### 6. Mild weather: when minimum output exceeds the load

- Energy Stats' cycling arithmetic [20]:
  - Vaillant 10/12 kW has about 5.8 kW minimum output; a 9 kW house cycles above about 5 °C outdoor.
  - Mild-weather cycling is "system-defined"; run times grow from 20 min at 14 °C to 1 h 20 min at 8 °C (4 kW house).
  - Rule of thumb: < 1 start/h good, 1-2/h fine, > 2/h investigate. The author's lifetime average is 0.64/h.
- OEM: one owner went from about 150 starts/day (COP about 2.5) to 1-2 starts/day (COP about 4) at 600-900 W [34]. Another found about 3 cycles per 2 h at 50-70 % duty acceptable [33].
- RHH mild-weather thread [32]:
  - One owner runs continuously below about 5 °C outdoor.
  - Above that, a room stat with 0.5 K hysteresis gives 40-60 min cycles; on mild days the house reaches temperature in about an hour and stays off the rest of the day.
  - Owners report minimum outputs of about 1.6 kW (Daikin 8 kW) to about 3.8 kW (Viessmann 10 kW).
- Low-and-slow UFH on an Ecodan [48]: cycling increased after the floor had heated for a few hours ("saturation"); minimum output about 1.9-2.4 kW.
- Belgian advice (Volta, 2026) [38]: run the heat pump in the daytime for PV and higher COP, with night operation only as a comfort guard. A tuned curve dropped the supply temperature from 33 to 26 °C at −5 °C with comfort kept, and cut the monthly peak by about 3 kW by avoiding the 2 kW backup heater.

### 7. How to express comfort for a controller

- **Hard limits** (never violate):
  - a minimum room temperature (frost, health, mould: Zukunft Altbau's 16 °C floor [41]);
  - a maximum floor surface temperature of 29 °C [14][22];
  - a maximum flow temperature.
  - Hard limits on the *comfort* band itself make MPC infeasible under forecast error. Every MPC paper softens them [12][13].
- **Soft band with asymmetric penalty.** Kuboth: undershoot 5× more expensive than overshoot (0.5 vs 0.1 €/Kh) [12]. This fits the owner's own priorities: cold mornings are noticed, while 0.5 K warm is barely noticed [15][35].
- **Budget form.** Shi & Jones [13]:
  - Kelvin-hours combine depth and duration of a violation, which violation-rate metrics do not.
  - A running-average Kh budget is fed back each step to tighten or relax the bounds.
  - In a one-zone BOPTEST case, a 0.005 Kh/step budget saved 31.9 % energy and reduced Kh violations by 36.2 % vs the default controller.
  - The field deployment stayed close to or below the prescribed budgets.
  - Slack-weight tuning, by contrast, gives outcomes that shift with the model and the season [13].
- **Rate and amplitude constraints**: ≤ 1 K peak-to-peak per cycle and < 2 K/h [8][14]. These are useful as *design* constraints when choosing the band width.
- **Sensor.** Use an operative or averaged room temperature, not a single air sensor near sun or kitchen [17][26]. BuildHub data show transients of up to 2 K from guests or cooking within 15-30 min [30]. A slab controller must filter these, which is the "day-to-day compensation" principle [9][10].

## What this means for controlling this house

The house: slab UFH (τ = C/H ≈ 33-47 h [calc]), Gree Versati 9 kW, minimum output ≈ 3.7 kW, flow setpoint written over Modbus, restart only when setpoint − outlet ≥ ~4 K, PV 15 kW, target 22.0 °C.

**Balance point [calc].** The load equals minimum output at an outdoor temperature of about −4.4 °C (H = 0.14), +0.2 °C (H = 0.17) or +3.5 °C (H = 0.20). Above that, the unit *must* cycle, and the only questions are how many starts, at what flow temperature, and at what time of day. A good share of the Lithuanian heating season lies above it.

### Recommended rules (with confidence)

1. **No scheduled night setback. Keep the slab's stored heat roughly constant from day to day** (confidence: high).
   - Every heat-pump-specific source caps setbacks at 2-3 K or advises none [17][18][21][22][24][26].
   - Owner data show lower COP around setback periods [3], and the field analysis links setbacks to higher flow temperatures [1].
   - The house arithmetic shows a 2 K setback saves about 2 % of heat but forces 13 kWh of hotter recovery.
   - The GSHP simulation saving [7] does not transfer: an air-source unit pays a night and defrost penalty, and a 33-47 h slab cannot "coast and recover" within one night.
2. **Replace "setpoint schedules" with a comfort band plus a daily energy plan** (high on direction, medium on numbers).
   - Suggested band: 22.0 °C target, soft limits 21.6-22.6 °C, so one swing is about 1 K, meeting ISO 7730's ≤ 1 K peak-to-peak [8].
   - Hard guards: start below 21.3 °C; stop above 23.0 °C (23.3 °C when there is PV surplus).
   - A ±0.25 K band forces about 6-7 starts/day at +10 °C; a 1 K band forces about 3 [calc].
   - Owners tolerate about 1 K; Olesen caps the dead band at 2 K [11].
3. **In mild weather, run fewer, longer blocks at minimum output and the lowest workable flow, timed for the warmest or PV hours** (medium-high).
   - With P_min 3.7 kW and load 1.7 kW: about 3.3 h on / 3.9 h off for a 1 K swing [calc].
   - At load 2.5 kW (about +5 °C): about 5.5 h on / 2.6 h off.
   - Put the on-blocks at midday and afternoon, when outdoor air is warmest and PV is free [5][38]. Do *not* use the night as a recovery period.
   - The slab charge loses only about 6 % of the stored heat [8].
   - Fold DHW into the same block or put it at the warmest hour, so it does not chop space-heating runs.
4. **Treat flow setpoint as an on/off-plus-level command, not a thermostat** (medium; check against the Versati firmware notes, topic 08).
   - Start a block: write setpoint = max(outlet + 4.5 K, lowest flow that carries P_min into the slab). The latter is probably about 28-30 °C at +5 to +10 °C outdoor (sibling note 05: mean water 24-26 °C at +10 °C).
   - Hold that setpoint and let the inverter sit at minimum.
   - End the block: write a low setpoint (e.g. 20 °C) when the room reaches the top of the band or the planned energy is delivered. Do not wait for an outlet overshoot at a raised setpoint.
   - **Avoid** the pattern "room fell → write 36-39 °C". Each +1 K costs about 2-3 % COP [27][28][39], so a 36 °C catch-up costs about 15-20 % more than 29 °C, and 39 °C about 20-25 % more. A catch-up should raise the block *duration*, not the water temperature.
   - Cap catch-up flow at about "normal block flow + 2-3 K" unless the room is below the hard guard.
5. **Use the band asymmetrically and express it as soft costs or a Kh budget** (medium).
   - Undershoot is about 5× worse than overshoot (pattern from [12]).
   - Allow the upper side to rise to about 22.6-23.0 °C during PV surplus to pre-charge the slab. Each +0.5 K of "lumped" house temperature stores about 3.3 kWh of heat.
   - Budget idea: ≤ 1 Kh/day below 21.6 °C; zero tolerance below 21.3 °C.
6. **Feedback on the day scale, not the 30-minute scale** (high on principle [9][10][30]).
   - Correct tomorrow's energy plan from today's average room temperature.
   - Within the day, only the hard guards act.
   - Short-term spikes from people and cooking (up to 2 K in 15-30 min [30]) and sun (+0.5 K [30]) must not trigger stops that cost a restart.
7. **If saving energy is wanted, lower the average target, e.g. to 21.5 °C, instead of setting back at night** (high for the arithmetic, low on whether the owner accepts it).
   - That saves about 2 kWh of heat per day (5 % at 0 °C, about 10 % at +10 °C) with zero recovery penalty [calc][2][41].
8. **Comfort measurement** (medium): average two or more room sensors in occupied areas, away from sun and kitchen. Optionally add a floor-surface sensor to estimate operative temperature [16][26].

### Tests the owner can run (each over at least 7 days, binned by outdoor temperature)
- A/B: current controller vs "band 21.6-22.6 °C, block control, flow ≤ 30 °C". Measure:
  - starts/day;
  - average flow while running;
  - COP per outdoor-temperature bin;
  - Kh below 21.6 °C.
- A/B: block timing night vs midday at the same daily heat. Expect a few % COP difference from outdoor temperature, plus the PV share.
- One deliberate 2 K night setback week vs a constant week at matched outdoor temperatures, to replicate [3] on a slab. Expect higher morning flow and lower COP; the prediction is a net loss.

## Contradictions and open questions

- **Setback saves vs loses.**
  - Saves: GSHP UFH simulation >6-10 % [7]; OEM simulator 8-15 % in a radiator house [5]; owners' lower-kWh setback days [4]; NRCan's "variable-speed may benefit" [24]; Grant's efficiency claim [23]; Nu-Heat's 4-6 K for new builds [25].
  - Loses: owner regressions [3]; a confounded day pair [2]; peer-reviewed field analysis [1]; manufacturers' ≤ 2-3 K caps.
  - Resolution offered: savings appear where heat-loss reduction dominates, i.e. leaky or low-mass houses, ground source, or modellers who accept undershoot. Losses appear in air-source, mild-weather, high-mass cases. Even [5] flips to +3.6 % once undershoot is limited. **No measured slab-UFH air-source setback study was found** (search was unavailable).
- **"Off-periods help" [6] vs "continuous is best" [30][37].** These agree once "continuous" means truly modulating at low flow. With a minimum output above the load (this house in mild weather), off-periods are unavoidable, and the question becomes how few.
- **Floor comfort.** ISO 7730's 19-28/29 °C [8][14] vs a Chinese study preferring 29-32 °C (via note 05). Irrelevant here, as the floor stays < 27 °C.
- **Band width.** ISO 7730 asks ≤ 1 K peak-to-peak [8]; TABS work tolerates a 2 K dead band [11]; owners tolerate about 1 K [35]. The detectability figure of 0.38 K [15] comes from a comparison between rooms, not from a slow swing over time.
- **The ~2-3 %/K COP rule** is a field and catalogue average. Versati-specific part-load COP vs flow and compressor frequency is unverified here (see topic 08).
- **Lumped-model caveat.** The cycles/day and setback arithmetic uses one capacitance (6.6 kWh/K). The room air reacts faster than the slab (lags of 3 h to 10-15 h are reported [30]). Real room swings per block may be smaller or larger than [calc]. Calibrate from logs.
- **Open:**
  - Does the Versati accept a setpoint write that lowers the outlet target mid-run without odd defrost or anti-short-cycle side effects?
  - What is its minimum off-time?
  - How large is Lithuania's typical diurnal swing on overcast winter days? If it is only 2-4 K, timing gains are small and PV is the main reason to shift.

## Sources

1. Bridging the heat pump efficiency divide (reporting Rosenow, Lea & Boni, Energy and Buildings 352:116785) - A. Smith, CIBSE Journal - 2026 - https://www.cibsejournal.com/technical/bridging-the-heat-pump-efficiency-divide-2/ - paper (field data + simulation) - SPF 3.86/2.81/2.36; setbacks raise flow temperatures; narrow band advised; EOH2578 COP 2.86 → 4.61.
2. Setback savings - fact or fiction? (page 5) - Renewable Heating Hub (cathodeRay, JamesPa, BobTSkutter) - 2024/25 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/setback-savings-fact-or-fiction/paged/5 - forum with owner data - setback vs continuous day pair (−4 % input, COP 3.9 vs 5.1, confounded); ~10 %/K rule.
3. Setback savings - fact or fiction? (page 10) - Renewable Heating Hub - 2025 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/setback-savings-fact-or-fiction/paged/10/ - forum with owner data - COP regressions (−5.5 % / −8.3 %); recovery energy balance (+38 % electricity).
4. Creative trials on night time setbacks… - Renewable Heating Hub (SUNandAIR, cathodeRay) - 2024 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/creative-trials-on-night-time-setbacks-to-faster-recovery-improved-comfort-and-even-greater-energy-reductions - forum - 50+ setback days; recovery during defrost COP ~4 → ~2.
5. Dynamic heat pump simulator (page 2) - OpenEnergyMonitor community (T. Lea et al.) - 2025 - https://community.openenergymonitor.org/t/dynamic-heat-pump-simulator/28315?page=2 - simulation - setback 8-15 % saving; saving vanishes (+3.6 %) when undershoot is limited; mis-configured +37 %.
6. Improve efficiency - turn the heat pump off - OpenEnergyMonitor community (MyForest) - 2020 - https://community.openenergymonitor.org/t/improve-efficiency-turn-the-heat-pump-off/13381 - forum with owner data - COP 2.58 continuous vs 3.32 with planned off-periods at 9 °C.
7. Effects of cycling on domestic GSHPs - supporting analysis (Report C207-R2) - R. Curtis, T. Pine, Mimer GeoEnergy for EA Technology/DECC - 2012 - https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/198854/mimer_report_on_modelling_cycling_of_heat_pumps.pdf - simulation (TRNSYS) - UFH+GSHP night setback 16 °C >6 %, 12 °C >10 % saving.
8. Thermal Storage in a Heat Pump Heated Living Room Floor for Urban District Power Balancing - R.P. van Leeuwen, J.B. de Wit, J. Fink, G.J.M. Smit (SMARTGREENS) - 2014 - https://www.scitepress.org/Papers/2014/49163/49163.pdf - paper (simulation) - ISO 7730-derived constraints (20-24 °C, ≤ 1 K p-p, < 2 K/h, floor 19-28 °C); floor storage loss 6 %.
9. A new control strategy for high thermal mass radiant systems - P. Raftery, C. Duarte, S. Schiavon, F. Bauman (UC Berkeley CBE) - 2017 - https://escholarship.org/uc/item/5tz4n92b - paper (simulation) - lockout hours + previous-day feedback; time constants 4-8 h+; up to −40 % cost.
10. Control of TABS in intermittent operation with pulse width modulation - M. Gwerder, J. Tödtli, B. Lehmann, V. Dorer et al., Applied Energy 86 - 2009 - https://www.sysecol2.ethz.ch/OptiControl/LiteratureOC/Gwer_09_AE_86_1606.pdf - paper (simulation) - 21-25 °C band; 1-3 K PWM setpoint shifts; day-to-day compensation only.
11. Operation and control of thermally activated building systems (TABS) - B.W. Olesen, REHVA Journal - ~2012 - https://rehva.eu/rehva-journal/chapter/operation-and-control-of-thermally-activated-building-systems-tabs - paper (simulation) - lower band limit 22 → 21 °C saved 5-15 %; dead band ≤ 2 K.
12. Experimental Long-Term Investigation of Model Predictive Heat Pump Control in Residential Buildings with PV - S. Kuboth, T. Weith et al., Energies 13:6016 - 2020 - https://epub.uni-bayreuth.de/5598/1/energies-13-06016.pdf - lab (twin rigs, real weather) - 20-24 °C soft band, 0.5 €/Kh under vs 0.1 €/Kh over; undershoot ≤ 1 K.
13. User-specified Kelvin-hour budgets within MPC for energy-efficient buildings - J. Shi, C.N. Jones (EPFL), arXiv 2609.06698 - 2026 - https://arxiv.org/pdf/2609.06698 - paper (simulation + field) - Kh budget formulation; −31.9 % energy at 0.005 Kh/step; field budgets met.
14. ASHRAE 55 (article) - Wikipedia - accessed 2026 - https://en.wikipedia.org/wiki/ASHRAE_55 - standard summary - drift 1.1 K/15 min, 2.2 K/h; floor 19-29 °C; vertical gradient 3/4 K.
15. Thermal comfort (article) - Wikipedia - accessed 2026 - https://en.wikipedia.org/wiki/Thermal_comfort - standard/literature summary - 0.38 K detectable at 24 °C; 2-5 K interpersonal spread; PMV ±0.5, 80 % satisfied.
16. Operative temperature (article) - Wikipedia - accessed 2026 - https://en.wikipedia.org/wiki/Operative_temperature - reference - t_o ≈ (t_a + t_mr)/2 for v ≤ 0.1 m/s.
17. Weather compensation or load compensation? - Heat Geek - ~2024 - https://www.heatgeek.com/weather-compensation-or-load-compensation - blog (installer) - setbacks 2-3 °C max; self-regulation example; room influence.
18. Vaillant sensoCOMFORT heat pump controller guide - Heat Geek - ~2025 - https://www.heatgeek.com/vaillant-sensocomfort-heat-pump-controller - blog (installer) - 21/16 °C "effectively turns the heat pump off"; night setback 2-3 °C max; not set-and-forget.
19. SensoCOMFORT Room Temp Mod: Inactive, Active or Expanded - M. Wall, Energy Stats UK - 2024/2026 - https://energy-stats.uk/sensocomfort-room-temp-mod-inactive-active-or-expanded/ - blog with measured data - Expanded off 4.5 h, 20.2 → 18.4 °C, worse recovery; Active −1 K at night holds lower flow; −180 °min catch-up.
20. Heat Pump Cycling and Minimum Modulation - Energy Stats UK - 2025 - https://energy-stats.uk/heat-pump-cycling/ - blog with data - cycle points vs minimum output; < 1 start/h good; 0.64/h lifetime.
21. Cosy heat pump controls - Octopus Energy - 2024/25 - https://octopus.energy/blog/cosy-controls/ - manufacturer - drop 1-3 °C instead of off; tariff-window raises/drops.
22. Underfloor heating: restart before the first cold snap - Selectra UK (citing Viessmann, BS EN 1264) - 2025 - https://selectra.co.uk/energy/news/underfloor-heating-restart-before-first-cold-snap - blog citing manufacturer - setbacks > 2 °C lose most of the saving with heavy floors; 29/35 °C floor caps.
23. Underfloor heating setback controls (FAQ) - Grant UK - n.d. - https://www.grantuk.com/knowledge-hub/faqs/underfloor-heating-setback-controls/ - manufacturer - claims setback raises efficiency; no numbers.
24. Heating and Cooling With a Heat Pump - Natural Resources Canada - n.d. - https://natural-resources.canada.ca/energy-efficiency/energy-star-canada/about/energy-star-announcements/publications/heating-and-cooling-heat-pump/6817 - government guidance - setbacks ≤ 2 °C; backup heat erodes savings; smart early start.
25. Underfloor heating user guide - TSL thermostats (v12) - Nu-Heat - 2015 - URL not recorded (PDF retrieved earlier in this research session; no search available to re-locate it) - manufacturer - setback 4-6 °C for new builds; thicker screed favours a smaller setback.
26. Using your Heat Pump Under-floor Heating System - eco+Logic HP/UFH (installer handout) - n.d. - https://cdn.shopify.com/s/files/1/0236/4093/2416/files/Using_your_Heat_Pump_UFH_9f39da3c-2753-4415-b942-65edb8f1dfe0.pdf - manufacturer/installer - floor sensing; setback ≤ 2 K (floor) / ≤ 3 K (air); consistent slab temperature more efficient.
27. Ecodan full product guide (Auto Adaptation page) - Mitsubishi Electric - n.d. - https://renewableheatinghub.co.uk/wp-content/uploads/wpforo/attachments/5124/4908-EcodanFullProduct.pdf - manufacturer - 1 °C lower flow = +2 % COP; flow tracks room trend.
28. Low temperature performance (HeatPumpMonitor.org analysis) - OpenEnergyMonitor docs - 2024/25 - https://docs.openenergymonitor.org/heatpumpmonitor/low_temperature.html - field data - SPF vs flow (4.4 @ 30 °C, 3.9 @ 35, 3.4 @ 40); coldest-day flow 36.6 °C for SPF 4.
29. Heat curve optimisation (help article) - tado - 2025 - https://help.tado.com/en/articles/10248018 - manufacturer - Moderate/Eco/Eco Plus 4/7/11 % with slower warm-up.
30. Do low energy houses really need heating controls? - BuildHub forum (JSHarris, ragg987, pdf27) - 2017 - https://forum.buildhub.org.uk/topic/4375-do-low-energy-houses-really-need-heating-controls - forum with owner data - slab UFH 24/7 at 29/26 °C; 12 h timer cut COP; 10-15 h lag; 2 K occupant transients.
31. Fußbodenheizung bei Wärmepumpe steuern (page 2) - simon42 community - 2024/25 - https://community.simon42.com/t/fussbodenheizung-bei-waermepumpe-steuern/34105?page=2 - forum with owner data - 4000 → 2800 kWh/yr and 8-10 → ≤ 3 starts/day after removing per-room control.
32. Performance of heat pumps in mild weather - Renewable Heating Hub - 2024/25 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/performance-of-heat-pumps-in-mild-weather - forum - minimum outputs 1.6-3.8 kW; 0.5 K hysteresis gives 40-60 min cycles; continuous below ~5 °C.
33. Weather Compensation & ASHP Duty Cycle - OpenEnergyMonitor community - 2023 - https://community.openenergymonitor.org/t/weather-compensation-ashp-duty-cycle/24793/4 - forum - 50-70 % duty, ~1.5 cycles/h acceptable; "low and slow with small setback".
34. How to reduce cycling (page 6) - OpenEnergyMonitor community - 2025 - https://community.openenergymonitor.org/t/how-to-reduce-cycling/25251?page=6 - forum with owner data - 150 → 1-2 starts/day, COP 2.5 → 4; 2 h stops cooled rooms quickly.
35. Mitsubishi Ecodan auto adaption trial to stop cycling - Renewable Heating Hub - 2025 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/mitsubishi-ecodan-auto-adaption-trial-to-stop-cycling - forum - flow ~29 °C, ~20 h run; UFH zone 21.5 → 22.5 °C accepted.
36. Mitsubishi Ecodan performance using room auto adapt - OpenEnergyMonitor community - 2024 - https://community.openenergymonitor.org/t/mitsubishi-ecodan-performance-using-room-auto-adapt/25558 - forum with owner data - COP 3.5 → 4.0; SCOP 3.4 → 3.6 (different days).
37. Final report on analysis of heat pump data from the RHPP scheme - R. Lowe, A. Summerfield et al. (UCL/RAPID-HPC for DECC) - 2017 - https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/606818/DECC_RHPP_161214_Final_Report_v1-13.pdf - field data - setpoints 18-23 °C; continuous heating can raise heat and still cut electricity; owner settled on continuous.
38. Sturing van warmtepompen: waar de echte winst zit - B. Vannoppen, Volta (BE) - 2026 - https://volta-org.be/media/amrbnnjj/sturen-van-warmtepompen-waar-de-echte-winst-zit.pdf - technical advisory - run in the day for PV/COP, night only as a comfort guard; curve 33 → 26 °C at −5 °C.
39. Lette gulvvarmesystemer og deres indflydelse på varmepumpers effektivitet - S.Ø. Jensen, O. Paulsen, M.F. Olesen, Teknologisk Institut - 2014 - https://www.teknologisk.dk/_/media/69871%5FLette%20gulvarmesystemer%20og%20deres%20indflydelse%20p%E5%20varmepumpers%20effektivitet.pdf - lab/simulation report - 2-3 % COP per K of floor flow; up to 10 % COP spread from fluctuating flow.
40. OPSYS - Combined optimization of heat pumps and heat emitting systems - S.Ø. Jensen, Teknologisk Institut - ~2019 - https://www.teknologisk.dk/_/media/72043_OPSYS%20main%20report.pdf - lab/simulation report - 2-3 %/K; preheat/setback for flexibility tested; better control cut forward temperature 0.3-0.9 K.
41. Richtig heizen und lüften - Zukunft Altbau (Baden-Württemberg) - n.d. - https://www.zukunftaltbau.de/eigentuemer/heizung-erneuerbare-energie/richtig-heizen-und-lueften/ - government advice - 1 K ≈ 6 % saving; night ≥ 16 °C.
42. Wärmepumpe - Zukunft Altbau - n.d. - https://www.zukunftaltbau.de/eigentuemer/heizung-erneuerbare-energie/waermepumpe/ - government advice - suspend setback when testing heat pump suitability; inverters keep flow constant.
43. Nachtabsenkung (article) - Wikipedia DE - accessed 2026 - https://de.wikipedia.org/wiki/Nachtabsenkung - reference - boiler-era framing; no heat pump/UFH data (shows the gap).
44. Der Freund aller Wärmepumpen (flyer) - Homematic IP (eQ-3) - n.d. - https://homematic-ip.com/sites/default/files/downloads/170173_HmIP_Flyer_Freund-aller-Waermepumpen.pdf - manufacturer - flows often set ~10 K too high; "up to 25 %" for 10 K lower.
45. Heat Pump Myths Busted - Energy Stats UK - 2025 - https://energy-stats.uk/heat-pump-myths/ - blog - steady background running; avoid third-party on/off thermostats.
46. Vloerverwarming weersafhankelijke regeling oncomfortabel - Klusidee forum (NL) - 2009 - https://www.klusidee.nl/Forum/topic/vloerverwarming-weersafhankelijke-regeling-onconfortabel.44190/latest - forum - room stat as a maximum limiter over weather compensation; minor.
47. Underfloor heating (article) - Wikipedia - accessed 2026 - https://en.wikipedia.org/wiki/Underfloor_heating - reference - ~50 % convective share in heating.
48. Running ASHP efficiently, general thought process (low and slow), page 2 - Renewable Heating Hub - 2024 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/runing-ashp-efficiently-general-thought-process-low-and-slow/paged/2 - forum - UFH ~30 °C flow; cycling rises as floor "saturates"; minimum output ~1.9-2.4 kW.
