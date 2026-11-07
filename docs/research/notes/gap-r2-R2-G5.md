# Gap R2-G5: Measured room-air temperature swing in real slab or screed UFH houses run as multi-hour heat-pump pulses (1-4 h on, 2-8 h off) at various slab energy swings. How does the room's peak-to-peak swing relate to the slab mean swing, and what bands do occupants actually accept?

> Follow-up researcher, 2026-11-06.
>
> **Method note.** The shared web-search budget for this workflow was already used up when this pass started, so none of the WebSearch calls ran (0 of 3 attempted). The suggested queries and the non-English queries were therefore not run. To make up for it, this pass relies on:
> 1. **New field-data analysis.** I pulled 5-minute heat, electricity, flow-temperature, room-temperature and outdoor-temperature series for winter 2025-26 (1 Nov 2025 to 31 Mar 2026) from the public heatpumpmonitor.org timeseries API [1]. This covered every system flagged UFH-only (no radiators or fan coils) that publishes a room-temperature feed: 81 systems, of which 29 produced usable multi-hour pulse cycles. For each cycle I measured the room peak-to-peak and the energy the floor had to carry through the off-time. Nobody seems to have published this relationship for residential UFH, so it is the main new contribution here.
> 2. Full-text re-reads of papers already downloaded in this research session (Gwerder 2008/2009, Karlsson, van Leeuwen, Tang/Raftery, Johra, Olsson, Dongellini), read for room-swing content this time.
> 3. Direct fetches of known pages: forums, REHVA, DTU Orbit and Wikipedia.
>
> "[calc]" marks my own arithmetic. "[HPM-analysis]" marks results of the analysis in item 1. Scripts and cached data are in the session scratchpad; they are not committed.

## Summary

- **Measured: in real UFH houses, the room's cycle-scale swing scales with the heat the floor must carry through the off-period.** I analysed 2,118 multi-hour cycles from 29 UFH-only heat pump houses (median 1.4 h on, 1.75 h off, 8.8 °C outdoor, 29 °C mean flow). "Swing" here is the detrended room peak-to-peak in a cycle, with the cycle's start-to-end drift removed:
  - ≈0.10 K median when the floor carries < 20 Wh per m² of floor area per cycle;
  - 0.22 K at 20-30 Wh/m²;
  - 0.42 K at 30-45 Wh/m²;
  - 0.58 K above 45 Wh/m² (p90 1.15 K) [1][HPM-analysis].
- **Rule of thumb: about 0.04-0.12 K of room swing per kWh carried, median ≈ 0.07 K/kWh.** Within individual systems this is a clean linear relation (r = 0.55-0.89 in 11 systems). Expressed as an "apparent capacity" seen by the room, it is ≈ 8-35 kWh/K per house, median ≈ 14-20 kWh/K. Normalised by floor area that is ≈ 40-135 Wh/(m²·K), median ≈ 55 [1][HPM-analysis].
- **This house sits at the stiff end of that range only if its 6.6 kWh/K is really the room-side capacity.** Room swing ≈ carried kWh ÷ 6.6, i.e. 0.15 K/kWh. The HPM median is about half that. If this house behaves like the median HPM house, its room swings only about half as much as the lumped model predicts [calc]. **This is the single most important parameter to identify from the owner's own logs** (test in §"What this means").
- **The room follows the floor quickly; it does not lag by hours.** The detrended room maximum came a median 0.1-0.7 h after the compressor stopped (all 18 systems with enough cycles: −0.2 to +1.7 h). The minimum came just before the next start [1][HPM-analysis]. For simulation, the room is effectively a fast node on top of the floor surface. The multi-hour lags in the literature (τ95 ≈ 5 h screed, 10-100 h TABS) describe the bulk slab and the pipe-to-surface front, not the room's response to a pulse [5][7].
- **How room swing relates to slab mean swing, from theory and the TABS lab:** a quasi-static room sits between slab and outdoors. Room swing / slab-core swing ≈ (1/R_slab→room) ÷ (1/R_slab→room + 1/R_envelope). In Gwerder's measured TABS test room that is 0.71 (R~ = 0.16, façade 0.39 m²K/W) [2][calc]. In a well-insulated house with 100-200 m² of active floor, the floor-room conductance (~1-2 kW/K) is 5-10 × H (0.14-0.20 kW/K), so the ratio is 0.85-0.95 [calc]. Room swing is therefore **at most about the slab-mean swing, and somewhat less once walls, furniture and the slab's own core–surface gradient soak up part of it.** The HPM apparent capacities, 1-3 × the heat capacity of a 65-100 mm screed (≈ 35-50 Wh/(m²·K)), are consistent with a measured room swing of about **0.35-1.0 × the screed-mean swing** [1][calc].
- **Short pulses are almost invisible; period matters more than on-time.** Swing per kWh changed little with off-time in most systems (apparent capacity roughly constant from 1-2 h to 4-10 h off-time). Some systems (458, 568, 969, 1062) swing 20-60 % more per kWh at 4-10 h off-times than at 1-2 h [1][HPM-analysis]. That fits Karlsson's frequency analysis: floor self-regulation is inert below a ~12 h period and slightly *amplifies* room amplitude between 12 h and 100 h periods [5]. Lab pulses of 4 min on / 26 min off moved the slab surface < 0.1 K [6].
- **Disturbances, not the heat pump, set the floor of achievable room steadiness.** Daily room max-min in these UFH houses had a median of 0.82-0.90 K even on days the heat pump ran > 90 % of the time. On low-duty cycling days (15-60 % duty) it was 1.26-1.40 K; p90 was about 2.6 K in every duty bin [1][HPM-analysis]. Even the shortest, smallest cycles show ≈ 0.10 K median and 0.4 K p90 detrended swing from noise, sun and people. **A ±0.25 K controller band sits inside the disturbance noise.**
- **Proportion of cycles crossing thresholds** [1][HPM-analysis]:

  | Energy carried per cycle | Cycles > 0.5 K | Cycles > 1.0 K |
  |---|---|---|
  | < 4 kWh | 6-7 % | 1-2 % |
  | 4-6 kWh | 21 % | 2 % |
  | 6-10 kWh | 37 % | 9 % |
  | > 10 kWh | 54 % | 12 % |

- **What occupants accept: there is no residential occupant survey of pulse-operated UFH; the evidence is indirect.**
  - Standards: ISO 7730 cyclic ≤ 1 K peak-to-peak; ASHRAE 55 drift ≤ 1.1 K/15 min and ≤ 2.2 K/h [8][9].
  - Climate-chamber drift studies tested ramps of 0.6 K/h sustained for 8 h (≈ 4.8 K in total). Subjects sensed moderate drifts only after more than 4 h of exposure [10].
  - Design practice for TABS buildings uses 3.5-4 K floating bands (21-24.5 °C SIA 382/1; 21-25 °C lab; 20-24 °C "< 10 % dissatisfied") [2][3][11]. But a TABS-control expert caps the dead band at 2 K [4].
  - A UK slab-UFH self-builder lived happily with 20.5-21.5 °C (≈ 1 K peak-to-peak) [12]. HPM owners live with ≈ 0.9-1.4 K daily ranges [1].
- **Perception is not only air temperature.** One owner said a 2 h emitter-off period "feels a bit cold pretty fast" although the room thermometer did not move [13]. With a slab, the floor surface cools slowly, so this effect should be much weaker than with radiators, but it has not been measured.
- **A narrower swing lets the mean be lower.** Olsson's Swedish thesis concludes that a steadier indoor temperature lets the mean be lowered without breaching the minimum. Swing costs energy only through the mean you must hold to protect the lower limit [14].
- **Recommended band for this house (medium confidence):** treat 1.0 K detrended peak-to-peak as the hard comfort limit. Plan for ≈ 0.5-0.7 K of heat-pump-induced swing. Keep the rest for sun and occupancy, which add about 0.5-1 K on their own [1][8][12]. Asymmetric use (21.6-22.4 °C nominal, soft overshoot to 22.8 °C on PV days) is defensible. A ±0.25 K band is not: it is below the measured noise floor and would multiply starts.

## Detailed findings

### 1. New field analysis: heatpumpmonitor.org UFH-only houses, winter 2025-26 [1]

**Data and method.**
- **Selection.** heatpumpmonitor.org lists 864 public systems. 115 are flagged UFH with no radiators; 81 of these publish a room-temperature feed through the public API (`/timeseries/available`, `/timeseries/data.json`). Five monthly chunks at 300 s resolution were pulled for each.
- **Run detection.**
  - A "run" is a period with heat output > 300 W; gaps ≤ 15 min (defrosts) are merged.
  - DHW runs were removed using the `heatpump_dhw` flag where present, otherwise peak flow > 45 °C.
  - A cycle runs from one space-heating run start to the next. Cycles containing a DHW run were dropped.
- **Per-cycle quantities.**
  - Energy carried through the off-period: ΔE ≈ mean cycle heat rate × t_off. In periodic steady state this equals the surplus stored during the run, (P_run − P_load)·t_on.
  - Detrended room peak-to-peak: the cycle's linear start-to-end drift is subtracted, so slow weather and schedule trends are not counted. Raw peak-to-peak is also reported.
- **Filters.** On-time 0.75-6 h, off-time 1-10 h, at least 15 cycles per system. A stricter 1-4 h on / 2-8 h off filter left 13 systems and gave similar numbers.
- **Result:** 2,118 cycles from 29 houses. Medians: 1.4 h on, 1.75 h off, outdoor 8.8 °C, mean run flow 29 °C.

**Pooled results by energy carried per m² floor area** (floor area as declared; may include non-UFH floors):

| ΔE/A (Wh/m²) | cycles | houses | detrended p-p median | p75 | p90 | raw p-p median | raw p90 |
|---|---|---|---|---|---|---|---|
| 0-10 | 353 | 23 | 0.10 K | 0.20 | 0.45 | 0.15 | 0.60 |
| 10-20 | 779 | 27 | 0.11 K | 0.19 | 0.41 | 0.20 | 0.60 |
| 20-30 | 269 | 24 | 0.22 K | 0.34 | 0.48 | 0.35 | 0.93 |
| 30-45 | 445 | 18 | 0.42 K | 0.52 | 0.64 | 0.50 | 1.00 |
| > 45 | 272 | 19 | 0.58 K | 0.73 | 1.15 | 0.65 | 1.50 |

- Pooled OLS: detrended p-p ≈ 0.08 K + 0.0096 K per Wh/m² (r = 0.48).
- **Night-only cycles** (start 17:00-01:00, so little sun) are cleaner: 0.10 K at < 15 Wh/m², 0.17 K at 15-30, 0.47 K at > 30 Wh/m², with p90 0.25 / 0.42 / 0.77 K.

**By off-time** (all energies): 1-2 h off 0.15 K median (p90 0.50); 2-4 h 0.28 K (0.61); 4-6 h 0.37 K (0.86); 6-10 h 0.49 K (1.11). Raw p-p at 6-10 h off was 0.84 K median and 1.64 K p90.

**Per-house slopes** (detrended p-p vs ΔE in kWh, systems with r ≥ 0.5):

| HPM id | Notes | Slope K/kWh | r | Apparent capacity (kWh/K, median over cycles) |
|---|---|---|---|---|
| 628 | 1930s detached, 125 m², 5.5 kW HL | 0.120 | 0.57 | 11 |
| 1062 | 1930s London, 168 m² | 0.117 | 0.55 | 19 |
| 174 | London end-terrace, 170 m² | 0.116 | 0.77 | 9 |
| 345 | 1960s detached, open loop, 250 m² | 0.095 | 0.67 | 9 |
| 1082 | 1930s London, 166 m² | 0.092 | 0.64 | 26-34 |
| 743 | post-2012 detached, 210 m² | 0.083 | 0.48 | 11-16 |
| 568 | post-2012 detached NI, 356 m² | 0.076 | 0.71 | 13-25 |
| 441 | Thurso, 300 m² | 0.068 | 0.89 | 19-24 |
| 969 | post-2012 Jersey, 350 m², fixed 25 °C flow | 0.056 | 0.59 | 9-34 |
| 864 | Italy, 180 m² | 0.054 | 0.69 | 17-22 |
| 571 | post-2012 GSHP, 100 mm pipe centres, 224 m² | 0.041 | 0.81 | 24-30 |
| 768 | post-2012 terrace, 225 m² | 0.040 | 0.70 | 18-26 |
| 458 | 1930s, buffer, 200 m² | 0.037 | 0.76 | 20-28 |

- Per m² of declared floor area these are ≈ 37-135 Wh/(m²·K), median ≈ 55 [calc].
- For comparison, 70 mm sand-cement screed is ≈ 39 Wh/(m²·K) (0.07 m × 2,000 kg/m³ × 1.0 kJ/(kg·K)) and 100 mm ≈ 55 [calc].
- So the room "sees" roughly 1-3 × the screed's own capacity. Walls, furniture, the subfloor and upstairs mass all participate over a few hours.

**Timing.** Median time of the detrended room maximum after the run ends, per house: −0.2 to +1.7 h, most 0.2-0.7 h (628: 0.2 h, IQR 0.1-0.3; 777: 0.4 h; 458: 0.4 h; 743: 1.1 h; 768: 1.7 h). The room peaks at, or shortly after, the end of the heat pulse and then decays through the off-time. For a simulator, a two-node model is enough: a slab node plus a room node coupled at roughly the 0.3-1 h scale. Pulse-scale room dynamics do not need multi-hour delay terms [1][HPM-analysis][calc].

**Daily range vs duty** (all 81 houses, days with ≥ 90 % data):

| Daily duty | Days | Houses | Median of house medians | Pooled median | p90 |
|---|---|---|---|---|---|
| < 15 % | 245 | 12 | 1.33 K | 1.20 | 2.50 |
| 15-35 % | 577 | 27 | 1.40 K | 1.40 | 2.70 |
| 35-60 % | 1,402 | 47 | 1.30 K | 1.26 | 2.62 |
| 60-90 % | 2,165 | 52 | 1.14 K | 1.10 | 2.78 |
| > 90 % | 2,350 | 41 | 0.82 K | 0.90 | 2.60 |

Low duty also means milder, often sunnier days and possibly schedules, so the extra ≈ 0.4-0.5 K for cycling days is an upper bound on the pulsing contribution.

**Caveats.**
- The "UFH" flag does not say screed thickness. Some older houses may have low-mass overlay or joisted UFH, and these would swing *more* per kWh (likely some of the 0.1 K/kWh group).
- Room feeds are one sensor or an average; their resolution (often 0.1 K) sets the ≈ 0.1 K floor.
- ΔE uses mean cycle power × off-time, which assumes periodic steady state.
- Data are UK/Ireland-dominated, outdoor 5-12 °C.
- I used declared floor area, not UFH area.

### 2. Room vs slab: theory and the TABS lab

- **Gwerder et al. 2009 (Siemens Zug test room, 250 mm TABS slab)** [2]:
  - Measured operative temperature at 1.2 m height.
  - R_t (water→core) = 0.060, R~ (core→room) = 0.16, façade 0.39 m²K/W.
  - With a quasi-static room, ∂θ_room/∂θ_core = (1/0.16)/(1/0.16 + 1/0.39) = 0.71 [calc].
  - Lab PWM periods of 5 h (heating) and 24 h (cooling). The authors state that room amplitudes from PWM periods up to 24 h are small, and the comfort band can be met regardless of period.
  - Comfort band used: 21-25 °C.
  - They keep the supply shift during PWM at 1-3 K to protect self-regulation.
  - The paper gives no numeric amplitude; only figures.
- **Gwerder et al. 2008 (UBB design)** [3]:
  - Comfort range 21.0-24.5 °C (SIA 382/1).
  - The authors stress that a narrow comfort range stops the TABS floating, which kills the storage benefit.
  - The whole-year simulation stayed "to a very great extent" inside that band.
- **Karlsson (Chalmers PhD), reference Swedish floor** [5]:
  - The floor heating's characteristic time scale is ≈ 3 h. Heat-supply plans with a step shorter than this produce erratic, even negative, required heat.
  - Self-regulation is inert for periodic disturbances shorter than ~12 h, slightly amplifies room amplitude at 12-100 h, and damps only above ~100 h.
  - In lab short- and long-cycle tests, surface temperatures were predicted well. Points nearer the pipe fluctuate more.
  - Implication: pulse-scale (≤ 12 h) room swings are governed by stored energy and capacity, not by self-regulation.
- **Tang/Raftery pulsed-flow lab (Berkeley)** [6]: with 4 min on / 26 min off pulses at 11 % of design flow, the slab's average surface temperature varied < 0.1 °C per cycle. Sub-hour pulses are fully smoothed by a slab.
- **van Leeuwen et al. 2014 (Dutch low-energy living room, 514 kg/m² floor, simulation)** [7]: 2 h storage pulses of 1.6 kWh raised operative temperature towards a 1 K-wide band (20-21 °C) at < 0.5 K/h. Sun alone pushed it to 21.3 °C. That is 1.6 kWh for ~0.5-1 K in a single room, i.e. a room-scale capacity of ~2-3 kWh/K [calc from 7].

### 3. Acceptable bands: standards, lab drift studies, practice

- **ISO 7730 / van Leeuwen's reading of it** [7]: operative temperature 20-24 °C (outdoor < 10 °C), periodic variation < 1 K peak-to-bottom, rate < 2 K/h, floor 19.2-28 °C.
- **ASHRAE 55** [9]: when occupants do not control the cycling, ≤ 1.1 °C change within 15 min and ≤ 2.2 °C within 1 h. Floors 19-29 °C. (The fuller 2 h and 4 h drift table was not reachable without search.)
- **Kolarik et al. (DTU/ASHRAE RP-1269), climate-chamber drifts** [10]:
  - Ramps of 0.6 K/h for 8 h, 1.2 K/h for 4 h, 2.4 K/h for 2 h and 4.8 K/h for 1 h (22-26.8 °C).
  - Also ±0.6 and ±1.2 K/h in a 17.8-25 °C range.
  - Sedentary subjects sensed moderate drifts once exposure exceeded 4 h. Some well-being measures were affected.
  - Read: drifts of ~0.1-0.2 K/h, as produced by slab pulses, are far below what was tested.
- **Johra et al. (Aalborg) flexibility study** [11]: a 20-24 °C band (4 K) is a "normal" comfort level with < 10 % dissatisfied, with transients kept below 2.1 K/h.
- **Olesen, REHVA (TABS simulation)** [4]: dead bands of 22-23, 21-23 and 21-24 °C. Lowering the lower limit 22 → 21 °C cut heating 5-15 %. The author recommends a dead band ≤ 2 K. Simulated daily drifts in TABS offices were mostly 1-4 K per day in summer.
- **Practice, slab houses.**
  - BuildHub (JSHarris, UFH in a ~100 mm slab, pipes ~30 mm deep): room 20.5-21.5 °C with a 0.1 K-hysteresis stat and ≤ 25-26 °C UFH flow.
  - In that house two hours of winter sun added ~0.5 K; cooking or guests up to 2 K; five visitors ~1 K in 15-30 min.
  - The ASHP ran ~1-2 h every couple of days when heating only [12].
- **Practice, owners generally.**
  - HPM UFH owners: median daily range 0.9-1.4 K, p90 ≈ 2.6 K [1].
  - German owners (simon42) talk in terms of a 21.5-22.5 °C target window and accept 1-3 runs per day with floor heating [15]. No measured swing was given.
  - A Dutch new-build owner pre-emptively wanted to avoid on/off cycling of a weather-compensated floor [16]. This is anticipation, not a measurement.
- **Perception.** An OEM owner trialling 2 h stops per day reported the house "feels a bit cold pretty fast" when emitters stop, with room temperature unchanged. The emitter type was not clear [13]. Nobody measured this for slabs.

### 4. Swing–mean trade-off

Olsson (Chalmers licentiate, Swedish forecast control) concludes that most of the saving comes from better-adapted supply temperature. A steadier indoor temperature allows a lower mean without falling below the acceptable minimum [14]. For this house, each 1 K of mean is ≈ 4 kWh/day of heat (note 11).

So for a lower-limit-protected controller, a pulse that produces 0.5 K of peak-to-peak raises the required mean by ≈ 0.25 K, roughly 1 kWh_th/day ≈ 2.5 % at 0 °C outdoor. This cost has to be weighed against the start savings and PV/tariff shifting [calc].

## What this means for controlling this house

1. **Identify the room-side apparent capacity from the owner's own logs before trusting the 6.6 kWh/K for comfort limits** (confidence: high that this matters).
   - Take mild-weather cycles (no DHW inside, preferably at night).
   - For each, compute ΔE = mean heat rate × off-time and the detrended room peak-to-peak.
   - Fit p-p = a + b·ΔE.
   - Expect b between 0.04 and 0.15 K/kWh. b ≈ 0.15 confirms the lumped model. b ≈ 0.07 (HPM median) means each cycle can carry about twice the energy for the same comfort.
2. **Comfort budget** (confidence: medium):
   - Hard limit: 1.0 K detrended peak-to-peak, with the room never below 21.5 °C for a 22.0 °C target.
   - Heat-pump-induced swing allowance: ≈ 0.5-0.6 K. Sun and occupants routinely add 0.5-1 K on top [1][12].
   - Do not use a ±0.25 K band. The measured noise floor alone is 0.1 K median and 0.4 K p90 [1].
3. **Energy per pulse.**
   - With b = 0.15 K/kWh (C = 6.6), 0.55 K allows ≈ 3.7 kWh per cycle. At +10 °C (load 1.7 kW, P_min 3.75 kW) that is ≈ 1.8 h on and 2.2 h off, so ≈ 6 starts/day [calc].
   - With b = 0.07 K/kWh, it allows ≈ 7.9 kWh: ≈ 3.8 h on, 4.6 h off, ≈ 2.9 starts/day [calc].
   - The HPM data say 6-10 kWh pulses keep 63 % of cycles under 0.5 K and 91 % under 1.0 K [1]. **Start the trial at ≈ 4 kWh per pulse and step up to 6-8 kWh while watching the measured detrended swing.**
4. **Simulator structure** (confidence: medium-high):
   - Use a slab node (bulk, hours) feeding a room node with a sub-hour coupling.
   - The room peak should come ≈ 0.2-1 h after the run ends, not hours later.
   - Calibrate the room-node gain on item 1. Do not rely on a single-capacity model for comfort, only for energy.
5. **Schedule pulses so the peak lands where it is wanted.**
   - The room peaks within ~1 h of run end, so a PV-afternoon pulse that ends at 15:00 peaks around 15-16 h. That stacks on solar gain (≈ +0.5 K) [12].
   - On sunny days either shorten the PV pulse or let the band's top float to ≈ 22.8 °C (soft cost). Otherwise the sun consumes the band.
6. **Measure comfort sensibly.** Average two or more room sensors away from sun and kitchen, and detrend per cycle before judging pulses. Daily max-min is dominated by non-heat-pump effects (≈ 0.8-0.9 K even at > 90 % duty) [1].
7. **Avoid:**
   - judging success by daily range;
   - shortening off-times to chase a 0.1 K target;
   - very long single pulses (> 10 kWh carried). Above 10 kWh, 54 % of cycles exceed 0.5 K and 12 % exceed 1.0 K [1].

## Contradictions and open questions

- **Band width: 2 K vs 3.5-4 K.** TABS design literature floats rooms over 3.5-4 K (21-24.5/25 °C, 20-24 °C) [2][3][11]. Olesen caps the dead band at 2 K [4]. ISO 7730 asks ≤ 1 K for cyclic variation [7][8].
  - My reading: the wide bands are for slow day-to-day or seasonal drift in offices; the 1 K limit is for repeating cycles.
  - For a home with one owner who is sensitive to it, 1 K cyclic inside a ~1.5-2 K overall band is the defensible combination. This is unproven for this occupant.
- **Lumped 6.6 kWh/K vs HPM apparent capacities 8-35 kWh/K.**
  - The owner's 6.6 may be low because it was identified from room data that include disturbances.
  - Or the house may have a thinner screed and less internal mass.
  - Only the test in item 1 above resolves this.
- **Off-time dependence.** Most HPM houses show swing per kWh nearly independent of off-time. Four houses swing 20-60 % more per kWh at 4-10 h off-times. Karlsson predicts slight amplification at 12-100 h periods [5]. For the 8-12 h periods relevant to PV shifting, the per-kWh gain may be 20-50 % higher than from short-cycle data.
- **Floor type unknown in the HPM sample.** Low-mass UFH in older houses inflates the swing per kWh. A screed-only subset (post-2012 builds: 568, 571, 743, 768, 969) gives 0.04-0.08 K/kWh, at the stiff, favourable end.
- **No occupant survey of residential pulse-operated slabs exists in what I could reach.** Acceptance is inferred from standards, chamber studies, owner tolerance and absence of complaints. Nobody measured the "feels cold when emitters stop" effect [13] for slabs, or compared floor-surface temperature swing with air swing.
- **Not done because search was unavailable:**
  - the German, Polish, Scandinavian, Dutch and Lithuanian queries;
  - the Fraunhofer, Swiss and Danish monitoring reports with room traces;
  - Kolarik's full acceptability results;
  - the ASHRAE 55 drift table beyond 1 h.

  A follow-up pass with search should target "Raumtemperaturschwankung Fußbodenheizung Taktbetrieb Messung", Swedish "golvvärme rumstemperatur variation intermittent", and the IEA Annex / TABS field monitoring (e.g. Lehmann/Dorer Empa).

## Sources

1. heatpumpmonitor.org public timeseries API (systems 163-1124, UFH-only with room feed; winter 2025-26, 5-min data) - OpenEnergyMonitor community - 2025-26 - https://heatpumpmonitor.org/timeseries/data.json (system list: https://heatpumpmonitor.org/system/list/public.json) - field data - my analysis of 2,118 cycles in 29 houses (and daily ranges in 81): room swing vs energy carried, timing, noise floor, daily range vs duty.
2. Control of thermally activated building systems (TABS) in intermittent operation with pulse width modulation - M. Gwerder, J. Tödtli, B. Lehmann, V. Dorer, W. Güntensperger, F. Renggli, Applied Energy 86:1606-1616 - 2009 - https://www.sysecol2.ethz.ch/OptiControl/LiteratureOC/Gwer_09_AE_86_1606.pdf - lab + paper - TABS resistances giving the room/core ratio ≈ 0.71, PWM 5 h/24 h periods, "small amplitudes" up to 24 h, 21-25 °C band.
3. Control of thermally-activated building systems (TABS) - M. Gwerder, B. Lehmann, J. Tödtli, V. Dorer, F. Renggli, Applied Energy 85:565-581 - 2008 - (PDF from earlier session download) - paper (simulation) - comfort range 21.0-24.5 °C (SIA 382/1); narrow bands defeat storage.
4. Operation and control of thermally activated building systems (TABS) - B.W. Olesen et al., REHVA Journal - ~2012 - https://rehva.eu/rehva-journal/chapter/operation-and-control-of-thermally-activated-building-systems-tabs - paper (simulation) - dead band ≤ 2 K; daily drift distribution 1-4 K/day; 5-15 % saving from a 1 K lower limit.
5. Thermal Modelling of Water-Based Floor Heating Systems - H. Karlsson, Chalmers PhD - 2010 - https://publications.lib.chalmers.se/records/fulltext/111900.pdf - paper + lab verification - floor characteristic time ≈ 3 h; self-regulation inert < 12 h period, amplifying 12-100 h.
6. Performance analysis of pulsed flow control method for radiant slab system - H. Tang, P. Raftery, X. Liu, S. Schiavon et al., UC Berkeley CBE - 2018 - https://escholarship.org/uc/item/31s4x6jr - lab - slab surface variation < 0.1 °C under 4/26 min pulses.
7. Thermal Storage in a Heat Pump Heated Living Room Floor for Urban District Power Balancing - R.P. van Leeuwen, J.B. de Wit, J. Fink, G.J.M. Smit, SMARTGREENS - 2014 - (PDF from earlier session download) - paper (simulation) - 1 K periodic limit, < 2 K/h, 1.6 kWh 2 h pulses at < 0.5 K/h, sun 21.3 °C.
8. ISO 7730 comfort criteria as cited in [7] and note 11 - ISO - 2005 - (via [7]) - standard - ≤ 1 K peak-to-bottom periodic variation, < 2 K/h.
9. ASHRAE 55 (article) - Wikipedia - accessed 2026 - https://en.wikipedia.org/wiki/ASHRAE_55 - standard summary - 1.1 °C/15 min, 2.2 °C/1 h, floor 19-29 °C.
10. Occupant responses and office work performance in environments with moderately drifting operative temperatures (RP-1269) - J. Kolarik, J. Toftum, B.W. Olesen, A. Shitzer, HVAC&R Research - 2009 - https://orbit.dtu.dk/en/publications/occupant-responses-and-office-work-performance-in-environments-wi - lab (climate chamber) - drift ramps 0.6-4.8 K/h tested; drifts sensed after > 4 h exposure.
11. Influence of envelope, structural thermal mass and indoor content on the building heating energy flexibility - H. Johra, P. Heiselberg, J. Le Dréau, Energy and Buildings (Aalborg Univ. repository) - 2019 - (PDF from earlier session download) - paper (simulation) - 20-24 °C band = < 10 % dissatisfied; transients < 2.1 K/h.
12. Do low energy houses really need heating controls? - BuildHub forum (JSHarris, ragg987, pdf27) - 2017 - https://forum.buildhub.org.uk/topic/4375-do-low-energy-houses-really-need-heating-controls - forum (owner measurements) - slab-UFH room 20.5-21.5 °C; sun +0.5 K; guests +1 K in 15-30 min; cooking up to +2 K.
13. How to reduce cycling (page 6) - OpenEnergyMonitor community - 2025 - https://community.openenergymonitor.org/t/how-to-reduce-cycling/25251?page=6 - forum - 2 h stops "feel cold pretty fast" with unchanged room temperature.
14. Modellbaserad styrning av värmesystem baserat på prognostiserat väder - D. Olsson, Chalmers licentiate - ~2003 - (PDF from earlier session download) - paper - steadier indoor temperature allows a lower mean; most saving from supply-temperature adaptation.
15. Fußbodenheizung bei Wärmepumpe steuern (page 2) - simon42 community - 2024/25 - https://community.simon42.com/t/fussbodenheizung-bei-waermepumpe-steuern/34105?page=2 - forum (DE) - 21.5-22.5 °C target window; 1-3 runs/day with FBH; no measured swing.
16. Vloerverwarming weersafhankelijke regeling oncomfortabel - Klusidee forum - 2009 - https://www.klusidee.nl/Forum/topic/vloerverwarming-weersafhankelijke-regeling-onconfortabel.44190/latest - forum (NL) - occupant aversion to on/off floor heating; no numbers.
17. Heat Pump Cycling and Minimum Modulation - Energy Stats UK - 2025 - https://energy-stats.uk/heat-pump-cycling/ - blog with data - typical mild-weather on/off durations (20-80 min); no room swing data (shows the gap).
18. Dynamic modeling and seasonal performance evaluation of air-to-water heat pump systems - M. Dongellini, Univ. Bologna PhD - 2017 - (PDF from earlier session download) - paper (simulation) - larger thermal inertia slows oscillations and reduces their amplitude; dead band sets switching frequency.
