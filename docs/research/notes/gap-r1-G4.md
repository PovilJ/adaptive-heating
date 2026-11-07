# Gap G4: What does one start/stop cost on a modern inverter air-to-water unit, as a function of off-time and water volume, and why does very low daily duty (runtime fraction <0.3) lower COP: standby power, crankcase heater, pump, or a start-transient effect?

Scope and method. This note follows up note 03 (cycling) and note 13 (field evidence). It does not repeat their per-start table. It adds:
- the full text of Uhlmann & Bertsch's 2011 paper, which earlier notes saw only as an abstract;
- the full abstract of Dongellini & Morini 2019, and a re-read of the start-up model in Dongellini's thesis;
- a hardware-in-the-loop study of controller settings;
- standby and crankcase-heater evidence from manuals, forums and EN 14825 declarations;
- **my own decomposition of the heatpumpmonitor.org daily dataset** (94 systems, 10,375 full days), which splits the low-duty COP penalty into its non-running (standby) part and its running part [9].

The web-search budget for this session ran out after 11 searches. The German, Polish, English and patent/manual queries ran; the Swedish, Dutch and Lithuanian ones did not. After that I read pages directly and parsed the PDFs locally. I read about 20 sources. Where a source was seen only as an abstract or search snippet, I say so.

## Summary

- **The low-duty COP drop is standby electricity, not start transients.** I took mild days (6-14 °C) with no hot-water heating and compared each system with its own days at duty 0.3-0.9 in the same outdoor band:
  - At duty 0.2-0.3, whole-day COP is 2.1 % lower, but COP while running is 3.5 % *higher* and %-Carnot is 1.7 % higher.
  - The whole penalty is the electricity used while the compressor is off: 9 % of the day's electricity at a median of only about 21 W [9].
  - At duty 0.1-0.2: whole-day −6.7 %, running +5.9 %. The standby share is 12 % [9].
- **The 6-8 % figure in note 13 mixes in hot water.** When hot-water days are included, the lowest-duty days are nearly all hot-water days (99 % of heat below duty 0.1). Their *running* COP is 15-20 % lower because the water is hotter, not because of starts [9].
- **Median standby draw is small, but the spread is wide.** Non-running electricity per system: median 19 W, IQR 12-33 W, p90 53 W (n = 68 systems) [9]. Declared EN 14825 standby for the Versati is 25 W, plus a 25 W crankcase allowance on G1/G2 (note gap-r1-G1).
- **A pump that keeps running in standby would be the largest idle load in this house.** Note 08 says it may draw 75-85 W. At duty 0.25 on a shoulder day (about 22 kWh of heat, about 4.5 kWh of electricity), running that pump through 18 off-hours adds 1.0-1.5 kWh. That is 20-30 % of the day's electricity, against about 2-4 % for all the starts (my arithmetic). Whether the Versati pump runs in standby is still unmeasured.
- **Crankcase heaters run only in cold weather and only after long off-periods on some units.** One Midea-built unit switches its heater on only when outdoor ≤ 8 °C *and* the compressor has been off for more than 3 h [13]. Typical heater power is 33-70 W [14][15][16], and some inverter units heat the motor windings instead (about 50 W) [23]. The Gree manuals give no wattage, only a status bit and a rule of 8 h preheat before first start [20].
- **Measured start costs on modern units are small.** Uhlmann & Bertsch measured two air-to-water units at Q3/S25 and Q-10/S45:
  - COP over the first 5 min was within 2-6 % of the 40-min value. On one unit it was the same (5.3 versus 5.3) [1].
  - Their validated model found a COP penalty of about 5 % at 10 % duty in a 120-min cycle, and "insignificant" losses for runs of 10-15 min or more [1].
  - The 2012 journal version says 1-2 % for short cycles [2].
- **The start-up data behind note 03 are for a thermostatic expansion valve unit.** Dongellini's manufacturer data (electric input −4 % for 75 s, heat output −42 % or −31 % for 150-250 s) are for thermostatic-valve units [4].
  - The same thesis says an electronic valve that closes at shutdown prevents most refrigerant migration, which it calls "the main cause" of start losses [4].
  - The Versati has an electronic valve, so 0.07-0.11 kWh of heat per start is more likely an upper-middle than a lower bound.
- **The field data give a somewhat larger, confounded per-start cost.** Within a system and a 3 K outdoor band, on days without hot water, %-Carnot falls as mean run length shortens:
  - Relative to days with runs of 180 min or more: −1 % at 90-180 min, −3 % at 60-90 min, −6 % at 45-60 min, −10 % at 30-45 min [9].
  - A per-system fit gives a median of about 3 lost full-output minutes per start (IQR 1.5-4.5, n = 21 systems). At 3.75 kW that is about 0.1-0.3 kWh of heat per start [9].
  - Treat this as an upper bound: days with short runs also differ in other ways.
- **Per-start cost depends on off-time, but rises to a plateau.** Refrigerant migration and cooling of the outdoor unit grow with off-time:
  - The first run after a complete cool-down had lower COP than later runs [1].
  - Cold starts have 10-20 % longer capacity time constants than warm starts (snippet) [11].
  - Beyond a few hours the extra cost is mainly crankcase-heater energy, which grows linearly with off-time below about 8 °C (25-50 W × hours) [13][14].
- **Water volume changes how many starts there are, not what each start costs.** In a test of a 40.5 kW unit, start-up losses were "consistent across all inertia levels" from 50 L to 1,000 L; small storage only meant more cycles [7].
  - Heat stored in indoor water and pipes stays in the house.
  - The only volume-dependent loss is water and metal in the *outdoor* monobloc and outdoor pipes cooling towards ambient while off. My estimate is up to about 0.1-0.35 kWh per long off-period for 5-10 L at 30 K, less if insulated.
- **More starts does not have to mean lower efficiency.** In hardware-in-the-loop tests, changing the hysteresis gave about 250 % more cycles but SCOP moved only about 2 % (radiator case). The underfloor case was optimal at a 3 K hysteresis with 123 cycles/day [5].
  - A forum owner's Ecodan 14 kW at about 10 °C gave COP 4.4-4.5 while cycling about 3 times an hour, against 3.9 running continuously at higher output [18].
- **Seasonal start-up losses matter mainly for single-stage units.** Dongellini & Morini put them at up to 12 % of the seasonal performance factor for single-stage units, and small for inverters that avoid cycling most of the season [3].
  - An inverter study of Alpine homes put start-up alone at 4-6 % of SCOP, rising to 11 % with defrost. Its "start-up" covers up to 20 min of low-efficiency ramp, 40-70 h/month [12].
- **Field %-Carnot collapses at very low electrical power for reasons other than starts.** The OST/Bertsch field study extracted *steady-state* points and still found %-Carnot breaking down below a unit-specific electrical power [8]. Fixed drive, fan, pump and control losses are the likely cause; start transients are not.
- **Bottom line for control:** at this house's loads, total start cost on a typical mild day (4-10 starts) is about 1-4 % of heat. Standby and pump draw while off can be 10-30 % on low-duty days, and flow temperature is worth about 2-2.5 %/K (note 13).
  - So "a few long blocks" helps only modestly through fewer starts.
  - It helps more if the off-time is truly idle (pump off, no heater), and it hurts if the blocks need hotter water.

## Detailed findings

### 1. What one start costs: direct measurements and models

**Uhlmann & Bertsch (NTB Buchs; Swiss Federal Office of Energy project), full text of the 2011 IEA HP Conference paper [1]**
- Lab validation: two residential air-to-water units in a psychrometric chamber, held within ±1 °C. Humidity was kept low, so there was no frost.
  - At Q3/S25 (air 3 °C, supply 25 °C), heat pump 1 measured 9.6 kW over the first 5 min versus 9.7 kW over 40 min. Electric input was 1.83 kW in both windows. Measured COP was 5.3 in both [1].
  - So for these units, almost the whole start loss falls in the first minute or two. Model-versus-measurement differences for the first 5 min were 1.8-5.6 % [1].
- Parametric study 1: fixed 120-min cycle, duty varied from 10 % to 100 %.
  - At low duty, COP fell by about 5 % compared with steady state.
  - The stated causes are heat lost to the surroundings during the off-time, and refrigerant moving from condenser to evaporator, which "then has to be recompressed".
  - COP at 90 % duty was slightly *higher* than at 100 %. Brief stops let the heat exchangers' stored heat lower the pressure ratio [1].
- Parametric study 2: duty fixed at 40 %, cycle length varied from 30 to 270 min. Short cycles lost "a few percentage points", and runs of 10-15 min or more made the loss small [1].
- **The first run after a complete cool-down** had clearly lower COP than runs 2 and 3, which were similar [1]. This is the off-time effect: a long off-period costs more than a short one, but only up to the point where the unit is fully cold.
- **Pump overrun:** the models stopped the water pump together with the compressor. Running it for about one more minute recovers heat that would otherwise be lost from the unit [1].
- The 2012 journal version (abstract only) gives 1-2 % for short cycles on air-source units [2]. A later citing paper paraphrases it as under 2 % with a minimum run of 15 min [5].

**Dongellini thesis, start-up model re-read [4]**
- The model is a fixed penalty per start, independent of off-time:
  - electric input × 0.96 for 75 s;
  - heat × 0.58 for 150 s or 250 s (text and Table 4.8 disagree). A later case uses 31 % for 250 s.
- The source is a manufacturer's measurements on thermostatic-valve units. The thesis says the penalty parameters depend on valve type, and that an electronic valve can close fully at shutdown and stop migration [4]. It names restoring the high-to-low pressure difference as the main start-up loss [4].
- Implication: note 03's 0.07-0.11 kWh per start comes from a thermostatic-valve unit. An electronic-valve unit such as the Versati probably sits at or below it.

**Other transient evidence**
- Variable-speed 14 kW R-410A air-source unit, IJR 2026 (snippet only) [11]:
  - start-up and shut-down transients are driven by refrigerant migration and valve actions;
  - cold starts have 10-20 % longer capacity time constants than warm starts.
- Fuentes et al., 40.5 kW water-to-water unit [7]: capacity peaked 42-60 s after start; electric power reached full value in under 20 s.
- Göbel et al. HIL test bench [5]: the controller's safety rules allowed at most 10 starts/h with 180 s minimum run and 180 s minimum off. Poor parameters increased avoidable starts by 300 %.
- Gree Versati II service manual [19]:
  - the compressor cannot restart within 3 min of stopping;
  - output "will not be adjusted within 6 min" after a start.
  - So every start includes a fixed-frequency phase of about 6 min that the outside controller cannot shape. The Versati III/IV manuals I checked list 3-min timers but I could not extract the same sentence.

**Field estimate from heatpumpmonitor.org daily data (my analysis) [9]**

Method:
- 94 systems with daily records.
- Kept only full days with at least 99 % data quality, no cooling, no immersion or boiler use, and hot water under 5 % of heat.
- Compared each day's running %-Carnot with the same system's median on days with mean run length of 180 min or more, in the same 3 K outdoor band.

| Mean run per start | n days | Δ %-Carnot vs ≥180-min days | Δ mean electric power |
|---|---|---|---|
| 0-20 min | 33 | −8 % | −11 % |
| 20-30 min | 50 | −13 % | −3 % |
| 30-45 min | 189 | −10 % | 0 % |
| 45-60 min | 238 | −6 % | −3 % |
| 60-90 min | 368 | −3 % | −3 % |
| 90-180 min | 601 | −1 % | −3 % |

- A per-system fit of %-Carnot = 1 − k / (run minutes) gives median k ≈ 3.1 full-output minutes lost per start. IQR is 1.5-4.5 and p90 is 6.4 (n = 21 systems with at least 30 usable days).
- At this house's 3.75 kW minimum, that is about 0.19 kWh of heat per start (IQR 0.09-0.28). That is about twice Dongellini's 0.07-0.11 kWh.
- Caveats:
  - Days with short runs are not random. They have lower load, more solar gain and possibly flow-temperature overshoot. %-Carnot corrects for temperature lift, not for those.
  - The fit is noisy; p10 is negative.
  - Read the field number as an upper bound, and the lab and manufacturer figure as a lower bound.
- Practical conclusion: **runs of 90 min or more cost at most about 1-2 %, and runs under 45 min start to cost 5-10 %**, consistent with note 03's field knee.

### 2. How cost per start depends on off-time

The direct evidence on off-time is thin, but these mechanisms are clear:
1. **Refrigerant migration and pressure equalisation.** This grows with off-time until the pressures are equal. With an open thermostatic valve that takes minutes. With a closed electronic valve it is slower and partial [4].
   - The MERL simulation in note 03 (723 s to rise after a 20-min off) is a thermostatic-valve-style upper bound.
2. **Thermal soak.** The compressor shell, heat exchangers and water in the outdoor unit cool towards ambient.
   - The first-run penalty after full cool-down [1] and longer cold-start time constants [11] show this cost saturates once the unit is cold, probably within 1-3 h for an outdoor monobloc (my estimate, not measured).
3. **Crankcase heating.** This is the only cost that keeps growing with off-time.
   - Midea/Kaisai logic: heater on only when outdoor ≤ 8 °C and the compressor has been off for more than 3 h, or after power-up; off above 8 °C or while running [13].
   - Other units heat continuously while off [14][16]. Ecodan examples: 54 W "on", 15 W "off", averaging 35 W, or 28 W above 21 °C [16].
   - Samsung Gen 7 R32: about 1 kWh/day idle, including about 50 W of oil heating even at +20 °C (single user) [17].
   - Gree: status bit only (coil 84 per note 08), 8-h preheat rule, no wattage [20]. EN 14825 declaration: P_CK 25 W on G1/G2 and 0 W on G3 (note gap-r1-G1).
   - Caveat: clamp meters overstate this load because the power factor in standby is low. Use a true energy meter [15][16].

Working model for this house (my synthesis; low-medium confidence):

```
start cost ≈ C0 + C1·(1 − e^(−t_off/τ)) + P_ck·max(0, t_off − t_ck)   [only if T_out ≤ ~8 °C]
C0 ≈ 0.05–0.1 kWh_heat (pressure build-up, EEV)
C1 ≈ 0.05–0.2 kWh_heat (soak of outdoor unit and its water)
τ ≈ 1–2 h
P_ck ≈ 0–50 W, t_ck ≈ 0–3 h (unknown for Gree)
```

So a 6-h off-period at 0 °C could cost about 0.2-0.3 kWh of heat plus up to 0.15 kWh of electricity for the heater. A 1-h off-period costs about 0.1-0.15 kWh of heat.

### 3. How cost per start depends on water volume

- Fuentes et al. [7] tested 50 L, 100 L and 1,000 L of storage:
  - start-up losses did not change with inertia;
  - part-load degradation was worse at small volume only because there were more cycles;
  - standby was 15 W (0.2 % of rated power) and negligible above 20 % part load;
  - the EN 14825 method was off by up to 12 % depending on inertia.
- Dongellini [4] sized a 200 L tank only to keep starts under 6/h.
- Göbel [5] found that with no buffer, solar gain at midday drove bypass-valve trips and supply-temperature swings. This is a "no buffer plus solar" cycling mechanism, not a per-start cost.
- For this house:
  - The slab (about 5,700 L-equivalent per kelvin) sets the number of cycles.
  - The *cost* per start depends only on the water and metal outside the heated envelope: the monobloc plate exchanger, the unit's internal water and the outdoor pipe run.
  - At 5-10 L and a 30 K difference to outdoor air, fully cooled, that is 0.17-0.35 kWh. Good pipe insulation and short off-times reduce it (my arithmetic).
  - If the pump keeps circulating while the compressor is off, the outdoor water stays near return temperature. The one-off soak loss becomes a continuous loss of perhaps 10-30 W, plus the pump's own draw.

### 4. Why very low duty lowers COP: the decomposition

**heatpumpmonitor.org daily data [9]** (each system against itself at duty 0.3-0.9 in the same 4 K outdoor band):

| Mild 6-14 °C, all days | n | Δ whole-day COP | Δ running COP | Δ %-Carnot | Non-running W | Non-running share of elec | Hot-water share of heat |
|---|---|---|---|---|---|---|---|
| duty 0-0.1 | 299 | −32 % | −20 % | −9 % | 15 | 17.5 % | 99 % |
| 0.1-0.2 | 193 | −12 % | −2 % | +1 % | 20 | 12.6 % | 0 % |
| 0.2-0.3 | 382 | −4 % | 0 % | +1 % | 19 | 8.5 % | 8 % |
| 0.3-0.5 | 1,257 | −1.5 % | −0.7 % | 0 % | 22 | 5.1 % | 0 % |
| 0.7-0.9 | 826 | +2.3 % | +1.0 % | +1.3 % | 26 | 1.1 % | 0 % |

| Mild 6-14 °C, hot water <5 % of heat | n | Δ whole-day COP | Δ running COP | Δ %-Carnot | Non-running share |
|---|---|---|---|---|---|
| 0.1-0.2 | 102 | −6.7 % | +5.9 % | +2.6 % | 12.4 % |
| 0.2-0.3 | 187 | −2.1 % | +3.5 % | +1.7 % | 9.0 % |
| 0.3-0.5 | 657 | −0.8 % | 0 % | −0.1 % | 5.5 % |
| 0.9-1.0 | 458 | +5.7 % | +3.5 % | +3.1 % | 0.1 % |

Reading:
- (a) **Standby is the whole effect** on heating-only days. Running efficiency actually improves at low duty, because the compressor runs at lower mean power and the water is cooler. The fixed off-time draw, spread over less heat, is what drags the day down.
- (b) **The worst-looking days are hot-water days**, where running COP falls because the water is hot. The "6-8 %" in note 13 is mostly these two effects mixed.
- (c) **Start transients are invisible at day level** in this sample. Runs at duty 0.2-0.5 average 70-100 min, where by section 1 starts cost about 1-3 %.
- Caveats:
  - heatpumpmonitor systems are mostly UK, well-commissioned units with heat meters.
  - What counts as "non-running" depends on each meter's boundary: some include the circulation pump, some the controller, few the immersion heater.
  - The "running" flag is set by the site's own threshold.

**Other evidence on the mechanisms**
- Corberán et al. (water-to-water, lab; abstract only) [6]: the "only non-negligible factor" in ON/OFF degradation was standby consumption during the OFF period, especially at low load ratio.
- Fuentes et al. [7]: measured Cc from standby was 0.998, against the EN 14825 default of 0.9. With a 15 W standby, the default greatly overstates cycling loss.
- OST/Repke/Bertsch 2026 (abstract) [8]: field %-Carnot is stable over wide ranges but "collapses" below a unit-specific *electrical* part load, which standard test points miss. The analysis used extracted steady-state points, so the collapse is a low-power steady-state effect (fixed drive, fan and pump losses), not a start effect. A unit forced to minimum frequency for long periods can sit in this zone.
- Defrost (note 09) is per running hour, not per start, so it does not explain a low-duty penalty. Hot-water tank standby loss does: 36-132 W in EN 16147 tests (note gap-r1-G1).

**This house, worked example (my arithmetic; parameters from the brief and notes 08 and gap-r1-G1)**

Shoulder day at duty 0.25: 6 h × 3.75 kW ≈ 22.5 kWh of heat. At running COP about 5, that is about 4.5 kWh of electricity.

| Off-time load (18 h) | kWh/day | Share of electricity |
|---|---|---|
| Controller standby 25 W | 0.45 | +10 % |
| Crankcase heater 25 W (only if ≤8 °C and long off; likely 0 on a shoulder day) | 0-0.45 | 0-10 % |
| Internal pump 40-80 W, *if* it runs while the compressor is off | 0.7-1.4 | +16-32 % |
| 4 starts × 0.1-0.2 kWh heat ÷ COP 5 | 0.08-0.16 | +2-4 % |

Standby and the pump dominate. Starts are a minor term.

## What this means for controlling this house

1. **First measure the off-time draw** (high value, cheap).
   - Log unit electricity during compressor-off periods. Split it by pump state (coil 175), crankcase-heater state (coil 84) and outdoor temperature.
   - Expected result: controller about 10-25 W; heater 0 W above about 8 °C and 25-50 W below; pump either 0 W or 40-85 W.
   - If the pump runs continuously, stopping it between heating blocks is worth more than any change to the cycling pattern (confidence: high that it would dominate if present).
   - If the Versati cannot be told to stop the pump, check whether a heat-pump "off" command or Gree's thermostat mode stops it. Keep a pump overrun of about 1-3 min after the compressor stops [1].
2. **Treat a start as costing about 0.1-0.2 kWh of heat at mild temperatures, up to about 0.3 kWh after a long cold off-period** (medium confidence).
   - At 3.75 kW that is 2-5 minutes of output.
   - Use this as the start penalty in any optimiser. It makes runs of 90 min or more cost about 1-3 %, and runs under 45 min cost 5-10 %.
3. **Aim for runs of 60-90 min or more, but do not make blocks longer if it raises flow temperature.**
   - Going from 8 starts/day to 3 saves about 5 × 0.15 = 0.75 kWh of heat, about 2 % on a 35 kWh day.
   - Raising the mean flow temperature by 1 K costs about 2-2.5 %.
   - So consolidation pays only if the longer blocks need no hotter water, roughly no more than 1 K hotter (medium confidence).
4. **Keep the duty fraction up on shoulder days by running at minimum output with the lowest flow temperature, not by idling and then catching up.**
   - Low duty is not inefficient while running. It is inefficient because of the fixed off-time draw.
   - So the rule is to cut idle draw and keep each run at low lift. Do not force extra running.
   - Duty below 0.3 is acceptable *if* off-time draw is under about 20 W (medium-high confidence, from [9]).
5. **Prefer short off-periods to long ones in cold weather** (≤ 8 °C) if the Gree heater behaves like the Midea logic (on after about 3 h off).
   - Below about 0 °C, gaps of no more than 2-3 h avoid heater energy and most of the soak cost (low-medium confidence, until coil 84 is logged).
6. **Do not let hot-water heating fragment the space-heating blocks.**
   - Each interruption adds a start and runs at hot-water lift.
   - Schedule hot water so it runs straight into, or straight after, a space-heating block (the unit is already warm), ideally at PV midday. The legionella cycle uses the electric heater anyway.
7. **Do not lower the restart hysteresis (register 4 K) to get "smoother" control.** Göbel found the efficiency optimum for underfloor heating at about 3 K hysteresis, with SCOP flat within a few percent [5]. At 4 K this house is in the flat region. Changing it buys little.
8. **Testable metric:** log per-run heat, electricity and length, plus per-day off-time electricity. Then fit the per-start penalty k (minutes) by regressing run COP on 1/run-length within outdoor bands, as in section 1. If k is about 2-3 min and off-time draw is about 25 W, the plan above holds. If k is over 6 min, starts matter more and consolidation deserves more weight.

## Contradictions and open questions

- **Lab versus field start cost.**
  - Lab and manufacturer: about 1-1.75 full-output minutes per start, or near zero for Uhlmann's units [1][4].
  - Field (my fit): about 3 min median, with a wide spread [9].
  - The field figure is confounded and probably high, but it is close to the Alpine study's 4-6 % SCOP loss from start-up on an inverter unit [12].
  - Uhlmann's own numbers vary by version: 5-30 % (2010), 2-5 % (2011), 1-2 % (2012) [1][2].
- **6-8 % (note 13) versus 2 % (this note) for low-duty days.** Both are right for their populations. Note 13's figure includes hot-water-dominated days and possibly different binning. On heating-only days the penalty is 2-7 %, and all of it is standby [9].
- **Is low duty good or bad while running?**
  - Running COP is *higher* at duty 0.1-0.3 in the heatpumpmonitor data [9].
  - %-Carnot collapses at very low electrical power in the Swiss field data [8].
  - These fit together if most heatpumpmonitor systems at low duty still run above their collapse point. The Versati's floor (about 3.7 kW of heat, about 0.8-1 kW of electricity at mild temperatures) is unknown relative to its own collapse point.
- **Gree crankcase heater:** wattage and on/off rule are unpublished. EN 14825 declares 25 W (G1/G2) or 0 W (G3), which suggests G3 may heat the windings or have no heater. Log coil 84 against outdoor temperature and off-time.
- **Gree pump in standby:** the manuals imply it runs (note 08). This is the single biggest uncertainty in this note.
- **Off-time dependence** has never been measured directly on an electronic-valve air-to-water inverter in any open source I found. The 2026 IJR paper [11] (cold versus warm start) is the closest, and I saw only a snippet. Measuring it on this unit is easy: compare the first-15-min heat output after 0.5-h, 2-h and 6-h off-periods at similar outdoor temperatures.
- **Searches I could not run** (budget exhausted): Swedish, Dutch and Lithuanian forums; Heat Geek and Energy Stats UK cycling write-ups; full texts of the Dongellini & Morini 2019 and Uhlmann & Bertsch 2012 journal papers (paywalled).

## Sources

1. Dynamic modeling of heat pumps (10th IEA Heat Pump Conference, Tokyo) - M. Uhlmann, S.S. Bertsch, NTB Buchs - 2011 - https://etkhpcorderapi.extweb.sp.se/api/file/773 - paper (lab-validated physical model; full text read) - Lab start-up data (first-5-min COP equal to 40-min COP on HP1 at Q3/S25); about 5 % COP loss at 10 % duty; first-run cool-down penalty; pump-overrun advice; runs of 10-15 min or more make losses insignificant.
2. Theoretical and experimental investigation of startup and shutdown behavior of residential heat pumps - M. Uhlmann, S.S. Bertsch, Int. J. Refrigeration 35(8) - 2012 - https://iifiir.org/en/fridoc/theoretical-and-experimental-investigation-of-startup-and-shutdown-135447 - paper (abstract/snippets only) - 1-2 % loss for short cycles on air-source units; EN 14511 data represent part load well.
3. On-off cycling losses of reversible air-to-water heat pump systems as a function of the unit power modulation capacity - M. Dongellini, G.L. Morini, Energy Conversion and Management 196 - 2019 - https://doi.org/10.1016/j.enconman.2019.06.022 (abstract via api.semanticscholar.org) - paper (TRNSYS simulation; full abstract read) - Start-up losses significant only for single-stage units (seasonal performance factor up to −12 %); inverters avoid cycling much of the season.
4. Dynamic modeling and seasonal performance evaluation of air-to-water heat pump systems (PhD thesis) - M. Dongellini, Univ. Bologna - 2017 - https://amsdottorato.unibo.it/id/eprint/7901/ - paper (simulation with manufacturer transient data; sections re-read) - Fixed per-start penalty (electric −4 %/75 s, heat −42 %/150-250 s or −31 %/250 s) measured on thermostatic-valve units; electronic valve closing prevents migration; pressure restoration is the main loss.
5. The impact of controller settings in heat pumps: numerical findings and experimental verification - S. Göbel, K. Waiz, C. Vering, D. Müller (RWTH EBC) - 2023 - https://proceedings.com/content/069/069564-0075open.pdf - lab (hardware-in-the-loop) + simulation - Hysteresis changes cycles by about 250 % but SCOP by about 2 %; underfloor optimum 3 K; PI integral time dominates SCOP (up to 18.5 %); 300 % more avoidable starts with poor settings.
6. Partialization losses of ON/OFF operation of water-to-water refrigeration/heat-pump units - J.M. Corberán et al., Int. J. Refrigeration 36(8) - 2013 - https://riunet.upv.es/entities/publication/82932ef6-01fa-4adb-9c00-fbf4bb2ee5fc - lab (abstract read) - Standby consumption during OFF is the only non-negligible ON/OFF degradation factor, especially at low load ratio.
7. Improved characterization of water-to-water heat pumps part load performance - E. Fuentes et al., REHVA Journal - c. 2016 - https://www.rehva.eu/rehva-journal/chapter/improved-characterization-of-water-to-water-heat-pumps-part-load-performance - lab (semi-virtual test, 40.5 kW) - Capacity peaks 42-60 s after start; start-up loss independent of storage (50-1,000 L); standby 15 W; measured Cc 0.998 versus default 0.9; EN 14825 off by up to 12 %.
8. Teillastverhalten von invertergeregelten Wärmepumpen - Analyse des Carnot-Gütegrads im Feldbetrieb (student thesis, supervisor Prof. S. Bertsch) - T. Repke, OST - 2026 - https://www.ost.ch/files/daten/abstracts/pdf/990f3d2f-cae1-4a03-a95e-8e279b8902f2.pdf - field data (abstract read) - %-Carnot stable but collapses below unit-specific electrical part load, using steady-state points from the Swiss federal monitoring.
9. heatpumpmonitor.org per-system daily statistics, own analysis - OpenEnergyMonitor community data, cached in this session - retrieved 2026-11 - https://heatpumpmonitor.org (daily stats per system) - field data (94 systems, 10,375 full days) - Splits the low-duty penalty into non-running (standby) and running parts; non-running W distribution; within-system %-Carnot versus run length; per-start k fit. Scripts (not committed)(analysis script, not committed) and starts.py.
10. Cost optimal renewable electricity-based HVAC system: application of air to water or water to water heat pump - B. Delač et al., Energies 15:1658 - 2022 - https://doi.org/10.3390/en15051658 - paper (literature review section read) - Waddicor et al.: 15-20 min minimum run to avoid efficiency loss; low hysteresis drives degradation (Rivière).
11. Experimental investigation of steady and transient heating performance of a variable-speed air-source heat pump - S. Yousaf, M. Mohsin Tanveer, C.R. Bradshaw, Int. J. Refrigeration (doi 10.1016/j.ijrefrig.2026.106988) - 2026 - https://www.sciencedirect.com/science/article/pii/S0140700726001878 - lab (search snippet only; full text 403) - Transients driven by migration and valve actions; cold-start time constants 10-20 % longer than warm-start.
12. Performance assessment of air-to-water heat pumps in Alpine regions under present and future climate: impacts of start-up and defrosting cycles - Energy (doi 10.1016/j.energy.2026.141016; preprint SSRN 6183984) - 2026 - abstract via api.crossref.org - paper (simulation with experimental degradation correlations) - Inverter air-to-water unit: start-up alone −4-6 % SCOP, −11 % with defrost; 40-70 start-up hours per month.
13. M thermal Mono service/installation manual (Kaisai, Midea platform), crankcase heater logic - Kaisai - c. 2020 - https://www.manualslib.com/manual/2999445/Kaisai-06ry1.html?page=18 - manufacturer - Heater on only if outdoor ≤ 8 °C and compressor off for more than 3 h (or at power-up); off when running or above 8 °C.
14. Watch out for cranky heaters - Build Equinox - 2019 - https://buildequinox.com/news/featured-article-watch-out-for-cranky-heaters - blog - Residential crankcase heaters 40-70 W; some always on when the compressor is off, others temperature-controlled.
15. Reducing heat pump standby power (thread) - OpenEnergyMonitor community - 2020 - https://community.openenergymonitor.org/t/reducing-heat-pump-standby-power/14982 - forum - 33 W per Daikin crankcase heater (spec); inverter winding heating gives a low power factor, so clamp meters overstate the draw.
16. Ecodan standby power consumption (thread, pages 3 and 10) - BuildHub forum - 2022-2023 - https://forum.buildhub.org.uk/topic/26840-ecodan-standby-power-consumption/page/10 - forum (owner meters plus datasheet quotes) - Ecodan 54 W on / 15 W off, averaging 35 W (28 W above 21 °C); PUZ-WM 15 W standby; summer 0.4-1.8 kWh/day; a TÜV report gives 9 W standby plus 33 W crankcase on one unit; 200-300 W clamp readings disputed.
17. Samsung HT Quiet Mono Gen 7 R32 low power consumption when idle - OpenEnergyMonitor community - 2025 - https://community.openenergymonitor.org/t/samusng-ht-quiet-mono-gen-7-r32-heatpump-low-power-consumption-when-idle/28491 - forum - About 1 kWh/day idle including about 50 W oil heating even at +20 °C; advice on 24-h preheat after isolation.
18. Heat Pump Truth or Myth #2 - cycling uses a lot of power and ruins your COP - Renewable Heating Hub forum - 2022-2024 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/heat-pump-truth-or-myth2-cycling-uses-a-lot-of-power-and-ruins-your-cop/ - forum (owner field data) - Ecodan 14 kW at about 9-10 °C: COP 4.4-4.5 while cycling about 3/h against 3.9 running continuously at higher output.
19. Versati II air-to-water heat pump service manual (T1/R410A) - Gree - 2013 - https://gree-bulgaria.com/manuals/archive/140_VERSATI_II_TSM_%202013_8.pdf - manufacturer - No restart within 3 min; no output adjustment for 6 min after start; chassis heater only with compressor on below 0 °C; crankcase heater status only.
20. Versati III monoblock service manual (4-16 kW) - Gree - c. 2019-2021 - https://gree-bulgaria.com/manuals/service/Versati_III_Monoblock_04_06_08_10_12_14_16_service.pdf - manufacturer - 8-h compressor preheat before first start; "heating tape of compressor"; crankcase heater status in the display list; no wattage.
21. Taktung bei der Wärmepumpe - 42watt magazine - 2026 - https://42watt.de/magazin/taktung-warmepumpe - blog (German) - Fraunhofer WP-QS: 550-15,800 starts/year across 77 systems, 90 % under 5,500; BWP target of 10-20 min per start; model starts/day versus hysteresis and volume.
22. Daikin Altherma 3 standby / Standby-Verbrauch Wärmepumpe threads - haustechnikdialog.de, energiesparhaus.at - 2020-2025 - https://www.haustechnikdialog.de/Forum/t/292917/Daikin-Altherma-3-R-MT-F-Standby-Stromverbrauch - forum (search summaries only) - Idle about 17-20 W, rising to 50-100 W on cold nights, attributed to the oil-sump heater 1-3 h after the compressor stops.
23. US5230222A Compressor crankcase heater control - patent - 1993 - https://patents.google.com/patent/US5230222A - manufacturer/patent (snippet) - Inverter winding used as crankcase heater (example 50 W), enabled at low outdoor and discharge temperature.
24. Sibling notes in this repository: 03-cycling.md (per-start table, Dongellini, MERL, Tassou), 08-gree-versati.md (pump in standby, coils 84 and 175, heat run time), 13-field-evidence-top-systems.md (6-8 % low-duty penalty), gap-r1-G1.md (Versati EN 14825 standby 25 W, P_CK 25 W/0 W, hot-water standby 36-132 W) - internal - used for context only, not re-verified.
