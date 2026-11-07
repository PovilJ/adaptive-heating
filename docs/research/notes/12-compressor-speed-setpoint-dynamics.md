# How setpoint changes drive compressor speed: soft start, ramps, power limits, quiet mode

> Research note 12 of the heat-pump control sweep. Written 2026-11-06.
> Scope: how inverter air-to-water units turn the error between flow setpoint and leaving water temperature (LWT) into compressor speed; why big setpoint jumps cost COP; what soft-start, ramp, power-limit, demand-limit and quiet-mode features exist; what "setpoint riding" can and cannot do.
> Method caveat: the shared web-search budget for this workflow ran out before this note started (all 3 search attempts were refused). Everything here comes from direct page fetches (forum threads, manufacturer PDFs, papers, blogs) and from public PDFs that sibling researchers had downloaded. I re-read those PDFs myself and checked their public URLs in sibling notes 01, 04 and 08. No current controller code was read.

## Summary

1. **On a Gree Versati, compressor speed is set by how far the LWT setpoint is above the actual LWT.** Gree's own manuals say: "frequency... increases as the temperature difference goes up and decreases as it goes down." A normal stop first ramps down to minimum frequency. If the unit is at minimum frequency and still overshooting, it shuts down [1][2][3].
   - So every restart that needs setpoint ≥ LWT + ΔT-Heat (today 4 K) begins with a ≥4 K error, which by design means high frequency.
   - That is the mechanism behind the ~3 kW electrical "catch-up" runs at +2 °C. Confidence: high. It is documented in three Gree manuals; the exact gain is not published.
2. **Lower compressor speed gives clearly better COP at the same source and sink temperatures. The best point is low-to-mid speed, not maximum.** Measured evidence:
   - KTH lab: heating COP fell **32%** going from 30 to 90 Hz [48].
   - Bologna PhD (manufacturer data): COP peaks at **40–60 Hz** on a 120 Hz compressor, up to **+20%** against 120 Hz [49].
   - Vaillant 5 kW in the field, same tank, +3.5…+5.5 °C outdoor: COP **3.55–3.85 at 50 rps** against **2.85 at 120 rps** (−20…−26%) [7].
   - REHVA/Fahlén: COP keeps rising down to ~10–20% capacity, but only if pumps and fans also slow down [50].
3. **The very bottom of the range is not automatically best.**
   - A 2026 OST analysis of Swiss field data found the Carnot efficiency of inverter units stays flat over most of the range, then **collapses below a unit-specific low electrical load** that standard test points miss [51].
   - Field part-load degradation is worse than the standards assume: measured Cc ≈ **0.80**, against 0.9 by default in EN 14825 and 0.96–0.99 in manufacturer tests [52].
   - For this Versati, minimum output is ~3.7–3.8 kW, about 40% of nominal. That probably sits inside the efficient plateau, not below it (inference).
4. **Start-up is where high speed hides.**
   - Owners report a Vaillant 7 kW running near maximum speed for several minutes after each start [14]. Samsung and Viessmann units show a high-power spike at every start [41].
   - NIBE changed this in firmware 2.3.3 (2021): outdoor-air units now run at **minimum speed after a start until degree minutes drop or a timer runs out**. The same release raised the default compressor step difference from **60 to 200 DM** [29].
   - The old Versati (I) manual states timers: no capacity adjustment for **6 min** after a start, **3 min** minimum off time, expansion valve fixed for 3 min [2].
5. **Every major brand has a cap that keeps the compressor low, under a different name:**
   - Gree: power limit 0–10 kW (default 3.0 kW), current limit 0–50 A, maximum-frequency register (65–85 Hz suggested) [4][5].
   - Daikin: power-consumption control in kW or A, permanent or by digital input [17].
   - Panasonic: optional-PCB demand control, 5–100% [25].
   - Vaillant: compressor current limit, plus "noise reduction" that maps directly to an rps cap (33% → ~80 rps; 60% → ~50 rps on a 5 kW) [7][13].
   - NIBE: maximum frequency in silent mode, and blocked frequencies [29].
6. **A permanent power cap is the cleanest way to stop catch-up bursts on this unit. Set it too low and defrost or hot water can break.**
   - Daikin warns that its system-level limit must stay at **≥ ~3.6 kW to guarantee defrost** on its 11–16 kW units [17].
   - Gree does not document whether its power limit applies during defrost or hot water. Test this before relying on it.
7. **Quiet mode is not the same as a compressor cap. On some brands it hurts COP.**
   - Panasonic's 2013 service manual describes quiet mode as fan-speed reduction only (−80 rpm, minimum 200 rpm) [27]. A slower fan lowers evaporating temperature and COP.
   - Gree quiet mode lowers both compressor and fan frequency [1]. A Versati III field report (note 08) saw defrost every ~52–56 min at +2…+5 °C with quiet mode on.
   - Vaillant's noise reduction is effectively an rps cap and was used successfully as one [7][14].
8. **"Setpoint riding" works in practice on Mitsubishi Ecodan, with guard rails.**
   - The open-source ESPHome Ecodan auto-adaptive controller sets flow target = **return + target ΔT**. It never lets the target fall more than **1.0 °C below the actual feed**, because the compressor cuts out soon after. While running, it changes the target by at most **0.5 °C per 30 s** [35].
   - A Home Assistant Ecodan FTC6 user fakes the target so that target − flow stays **< 11 K** at cold starts. That stopped the compressor climbing to **104 Hz** [37].
9. **Setpoint riding has documented failure modes:**
   - Hunting when the target moves often (Daikin "moving goalposts") [18].
   - Zig-zag power oscillation of ~400 W on Samsung [43].
   - NIBE running 50–60 Hz in mild weather when supply sits above target and degree minutes collapse [32].
   - On Gree, the stop rule makes it riskier: if the error stays in the "standby zone" for the heat run time (1–10 min, default 5 min with a 2-way valve), the unit stops [3]. Riding below LWT ends the run.
10. **Restart hysteresis and speed are linked.**
    - Degree-minute and energy-integral schemes (NIBE DM, Vaillant −60 °min, Bosch 150–250 K·min) integrate flow error over time [9][30][33]. Gree and Panasonic use plain temperature thresholds (Panasonic: stop at +2 K for 3 min, restart 3 K below the stop temperature after a 3-min wait) [27].
    - A wide restart band means fewer starts, but each start begins with a large error. Unless output is capped, a large error means a high-speed burst.
11. **Short runs cost far more than modulation.**
    - EA Technology tests: runs under **6 min** hurt COP clearly. Runs of **~8 min** reached catalogue COP on an ASHP. The worst-case loss measured was ~16% (GSHP) [54].
    - MERL simulation: refrigerant migration during the off-time causes most of the cycling loss [56].
    - With a 6.6 kWh/K slab, this house can easily make runs of 1–4 h. The problem is the speed and water temperature during runs, not their length.
12. **Flow temperature matters too.** The fleet regression on heatpumpmonitor.org gives about **−0.10 SPF per K** of average flow temperature (≈2.3–3%/K) [58]. Mitsubishi uses **2% COP per 1 K** [34]. A high-speed catch-up raises LWT by several K for the same delivered heat (higher heat flux across the plate heat exchanger), so it pays twice: compressor efficiency and lift.
13. **Bottom line for this house (medium confidence):**
    - Never start the compressor with a big error unless output is capped.
    - Use a permanent power cap (~1.3–1.6 kW electrical above about −3 °C) so starts stay near minimum speed.
    - Deliver heat in long, low-frequency, low-LWT blocks.
    - If riding the setpoint, stay within +1…+2 K of LWT once running, never below LWT − 1 K, with small steps.
    - Expected gain on catch-up runs: roughly 15–30% better COP for the same kWh delivered (estimate built from [7][48][49][58]).

## Detailed findings

### 1. How inverter air-to-water units decide compressor speed

**Generic architecture.** Inverter air-to-water units run a PID-type loop (often effectively PI or P) on supply or return water temperature against an internal setpoint. Start/stop sits on top as a separate, slower layer. Dongellini's thesis describes this split explicitly: the PID adjusts frequency on supply or return temperature. Below minimum frequency the unit falls back to on/off cycling with a hysteresis [49]. Compressor minimum speeds are typically 15–30 Hz on a ~120 Hz design. Below that, volumetric efficiency and oil return suffer [49].

**Gree Versati: proportional on LWT error.**
- Versati II service manual, heating: frequency rises with the temperature difference and falls as it shrinks. When the compressor is at minimum frequency and the difference is "still quite large" (LWT above setpoint), the unit shuts down [1].
- The Versati III all-in-one manual repeats this word for word, including room-temperature mode, where the same logic runs on room error [3].
- Normal shutdown first ramps to minimum frequency. Error and protection shutdowns stop immediately [1][3].
- **Heat run time** is 1–10 min, default 3 min (2-way valve off) or 5 min (2-way valve on). The unit stops once the heat run time has expired while the temperature difference stays in the "standby zone" [3]. The width of the standby zone is not given numerically.
- The first-generation Versati manual adds timers: no capacity adjustment for 6 min after a start, no restart for at least 3 min after a stop, expansion valve not adjusted for 3 min after start [2]. Whether Versati III firmware keeps the 6-min hold is unknown.
- The Versati III manual's application note says it directly. If the load is too small the unit "would start/stop frequently, which is adverse for oil return." If too large it "would always run under high frequency," which wastes energy [3]. It recommends sizing the load at 70–120% of unit capacity. Minimum system water volume is 20 L [3].

**Panasonic Aquarea (2013 SXC service manual).**
- The indoor microcomputer sets compressor frequency by comparing an internal water set temperature, after "shifting", with the outlet temperature [27].
- Thermostat logic: compressor off when outlet − internal setting > **2 °C for 3 min continuously**. It restarts after a **3-min** wait, once outlet minus the temperature at thermo-off falls below **−3 °C** [27].
- Restart is therefore referenced to the stop temperature, not the setpoint. This differs from Gree.

**Daikin Altherma (installer reference guide 4P401677-1A).**
- Overshoot [9-04] is 1–4 °C, default 1 °C. The compressor stops when LWT exceeds the desired value by this much, and restarts when LWT drops below the desired value [17].
- With room-thermostat control and "modulated LWT" on, the desired LWT moves up or down with room error. Daikin claims this gives fewer on/off cycles and the lowest possible water temperatures [17].
- An emitter-type setting [9-0B] (Quick or Slow) changes the maximum modulation of the LWT target for slow systems such as floor loops [17].
- Owners report the Madoka room controller moves the flow target in **3 °C steps** at 0.5 °C and 1 °C room error, and switches off at +1.5 °C [21]. That is coarse.

**Vaillant aroTHERM (VWZ AI manual and owners).**
- Start/stop uses an **energy integral**: the flow-temperature error, summed every minute. The unit starts at the set heat deficit, default **−60 °min**, adjustable to −100 [9][13]. It stops when delivered heat has balanced the deficit (0 °min) [9][13].
- A separate compressor hysteresis (default **7 K** per owners) acts as a backstop [14].
- A firmware bug (351.06.07) made the integral count about twice as fast. Fixing it lengthened cycles from ~35 to ~55 min and raised COP from 4.82 to 5.02 on comparable 3-hour windows (one owner, ~10 °C outdoor, 7 kW) [9].
- Modulation itself is not documented. Owners see near-maximum speed for several minutes after start on a 7 kW unit, and "never above minimum" except the first minutes on an oversized 10 kW [14].

**NIBE (degree minutes, DM).**
- Starts at a DM threshold: −1000 to −30 DM, lower meaning fewer starts [30]. Stops when DM returns to 0 [31].
- Forum users say NIBE does not document how frequency is chosen [32]. Observations: F2120 minimum ~25 Hz at ≥ +8 °C outdoor and ~35 Hz below. One owner saw **50–60 Hz at 10–16 °C** because supply ran ~5 K above the calculated value and DM hit 0 quickly [32].
- Firmware 2.3.3 introduced minimum speed after start for air-source units "to give a more stable regulation." Ground-source units already did this [29].

**Bosch/Nefit.** Hysteresis is in K·min: 150 K·min default on split units (adjustable). Monoblocs appear fixed at ~200 K·min on and ~250 K·min off [33]. Worked example (mine): a 2 K deficit takes ~100 min to reach 200 K·min.

**Samsung.**
- Owners describe the LWT band: the compressor stops at target + 2 °C. The target is also the lower bound, so restart can be almost immediate. FSV#1061 widens the lower bound, for example to a 5.5 K total band [44].
- FSV#6022 sets a minimum compressor run time [44].
- At start, Samsung units show high power for a while, then step down (Heat Geek observation on a 5 kW: high turn-on power "sustained for a period before turning down to 2 kW") [41].

**Mitsubishi Ecodan.**
- Officially, Auto Adaptation estimates required capacity from room and outdoor temperatures. It predicts room temperature a few points ahead to "prevent unnecessary increases and decreases in the flow temperature" [34].
- Owners report thermo-diff hysteresis of +5/−3 K letting flow climb from a 32 °C target to 37 °C before stopping [38], and 2–3 cycles/h at 3.7 kW minimum against ~2–3 kW emitter output [39].
- An 11 kW Ecodan in Bulgaria logged **6,500 starts in 8,345 running hours**. 77% of running hours contained a stop-start, mostly between 0 and 10 °C outdoor, with minimum output 4.3–5 kW [40].

### 2. Why big setpoint jumps give high frequency and poor COP

**Control mechanism.** In a P or PI loop on (setpoint − LWT), a step of +4 to +8 K saturates the output at or near maximum frequency. This is what Gree describes [1][3]. It is also what owners see at start-up on Vaillant, Samsung and Ecodan [14][37][41].

The Ecodan FTC6 Home Assistant user is the clearest single field data point. Capping the cold-start error below 11 K by faking the target stopped the compressor reaching **104 Hz** and let it "modulate smoothly" [37]. No COP numbers were given.

**Thermodynamic penalty, measured.**

| Source | Setup | Low speed | High speed | Change |
|---|---|---|---|---|
| Awan, KTH [48] | Lab, brine/water, VI scroll, R410A | COP_heat at 30 Hz | at 90 Hz | **−32%** heating COP; compressor power ~1 → ~4 kW |
| Dongellini, Bologna [49] | Manufacturer-data model, A/W inverter, W35 | max COP at 40–60 Hz | 120 Hz | up to **+20%** at ~50 Hz vs 120 Hz |
| Energy Stats UK, Vaillant 5 kW DHW [7] | Field, same 250 L tank, +3.5…+5.5 °C | 50 rps: COP 3.55–3.85, ~3.3 kW heat | 120 rps: COP 2.85, 6.9 kW | **−20…−26%** |
| Energy Stats UK [7] | Field, same conditions | 50 rps 3.55 | 80 rps 3.26 | −8% (the "Sweet Spot" trade-off) |
| Fahlén, REHVA [50] | Analysis/lab | f = 0.5: COP 4.1–5.5 | f = 1.0: COP 3.1–3.3 | +30…+70%, *only* with fans/pumps slowed |
| Hokkaido lab (via note 01) [64] | Inverter W/W | best at 45 Hz (lowest tested) | 90 Hz | — |

Three mechanisms make high speed expensive:
- **Larger lift.** Condensing temperature rises above the water temperature and evaporating temperature drops below air temperature, because heat flux per unit of heat-exchanger area goes up. KTH shows Carnot COP highest at 30 Hz and lowest at 90 Hz [48].
- **Compressor internal efficiency** peaks mid-range. Isentropic and Carnot efficiency peaked at **60 Hz** in KTH's rig, 61% at 5/25 °C [48].
- **Inverter losses** rise in watts (~95 W at 30 Hz to ~225 W at 90 Hz) but fall as a share of input (10% → 6%) [48].

At fixed external temperatures, the first effect dominates. Whole-unit COP was highest at the lowest speed in the KTH rig [48], and at about half speed in Dongellini's data [49].

**Counter-evidence: the very bottom.**
- Fahlén's Table 1 shows that with constant fan and pump power, COP at f = 0.2 can fall below f = 0.5. Example: 2.8 vs 3.5 for the "base" motor [50].
- The Repke OST thesis finds field Carnot efficiency "stable over wide operating ranges" but "breaks down significantly below unit-specific power limits" [51].
- Practical reading: the efficient plateau runs from about 25–30% up to 60% of maximum speed. For this Versati, a minimum of ~3.75 kW (~40% of 9.5 kW nominal) likely sits on that plateau. Verify by logging Words 142/143 (set and actual Hz) with electrical power.

**Lab vs field flow-temperature effect.**
- Fleet regression on heatpumpmonitor.org: SPF = −0.1008 × flowT + 7.42 (R² 0.52), roughly 30 °C → 4.4, 35 °C → 3.9, 40 °C → 3.4 [58].
- Mitsubishi markets 2% COP per 1 K of flow temperature [34].
- A high-frequency catch-up raises LWT for the same return temperature. Higher output at fixed flow means a larger flow-return ΔT, so it pays the flow-temperature penalty on top of the speed penalty.

### 3. Soft-start and ramp features by manufacturer

| Brand | Feature | What it does | Source | Evidence |
|---|---|---|---|---|
| NIBE S-series / SMO S40 | Soft start (fw 2.3.3, 2021) | Air-source compressor held at min speed after start until DM drops or a timer runs out | [29] | Manufacturer changelog |
| NIBE | Step difference default 60 → 200 DM | Fewer speed steps / slower escalation | [29] | Manufacturer |
| NIBE | "Improved compressor regulation in heating mode during startup"; fixes for short operation times with PV/SPA demand shifting and Auto DM (2025–26) | Shows raising setpoints on top of hysteresis caused short runs | [29] | Manufacturer |
| Gree Versati (I) | 6-min capacity hold after start, 3-min restart lockout, 3-min EEV hold | Speed fixed early in a run | [2] | Manufacturer |
| Gree Versati II/III | Ramp to min frequency before a normal stop; heat run time 1–10 min | Soft stop; delayed stop in standby zone | [1][3] | Manufacturer |
| Vaillant aroTHERM | None documented; owners see near-max speed for minutes after start | — | [14] | Forum |
| Samsung | High power at start, then ramps to minimum Hz once water-law target is reached (mode 1) | — | [41][44] | Forum/blog |
| Daikin Altherma | Short high-output spike, then modulates; circulation pump starts high for ~20–25 min | — | [19][21][41] | Forum |
| Mitsubishi Ecodan | Auto Adaptation predicts room temperature to avoid unnecessary flow-temperature jumps | — | [34] | Manufacturer |
| Ecodan (DIY) | Target − flow < 11 K at cold start; target ≤ 0.5 K change per 30 s while running | Keeps compressor off 104 Hz | [35][37] | Open-source / forum |

**Interpretation.** NIBE, the most control-sophisticated maker in this set, chose "start at minimum, escalate slowly." This is a vendor admitting that the plain "big error = big speed" response was wrong for air-source units in mild weather. Gree's behaviour is the old style. The external controller has to emulate soft start, either with a cap (sections 4–5) or by shaping the setpoint (section 6).

### 4. Power, current and demand limits

**Gree Versati.**
- C/P limit: Off / Current limit (0–50 A, default 16 A) / Power limit (**0.0–10.0 kW, default 3.0 kW**), set via Modbus Word 43 (value × 10) [4] (register details in note 08).
- A forum user saw Word 43 as the only register suited to grid optimisation. Nobody published observed behaviour under the limit [4].
- Maximum compressor frequency is set at Address/Word 72 ("should be between 65 and 85"). It is written with the unit off and coil 40 ("Heat Control Mode") enabled, and the poster warns you "must understand what you're doing" [5]. Note 08 reports Words 56/57 (quiet compressor frequency) and 72 reading 0 on one Versati III, so firmware support varies.
- Set and actual compressor frequency are readable (Words 142/143) [5].

**Daikin Altherma.**
- Power consumption control limits the whole system (outdoor unit + indoor + backup heater) in A or kW. It can be permanent or switched by up to four digital inputs [17].
- Order of action: backup heater off first, then limit the outdoor unit, then switch it off [17].
- Daikin warns: set at least **~3.6 kW to guarantee defrost**, otherwise repeated interrupted defrosts can freeze the heat exchanger, and at least ~3 kW to allow backup-heater step 1 [17]. This applies to the 11–16 kW split family in that guide.
- P1P2MQTT can drive quiet levels 1–3 and notes quiet "can be used as power limiter" [23].

**Panasonic Aquarea.**
- Demand control through the optional PCB, 5% → 100% (decimal 43 → 234/235) [25].
- Smart-grid modes: normal / off / capacity 1 / capacity 2 [25].
- HeishaMon must keep sending the optional-PCB command or the unit raises H74 after ~40 s and goes to standby [25]. External control has to be continuous, not fire-and-forget.

**Vaillant.**
- Compressor current limit set at commissioning. Status S.289 "current limit active": the compressor speed is reduced when current exceeds the set limit (<16 A for 3–7 kW, <25 A for 10–12 kW) [13].
- Noise reduction % maps to an rps cap: 30% → 84, 33% → ~80, 40% → 72, 50% → 60, 60% → 50 rps on a 5 kW [7].

**NIBE.** "Maximum frequency" in silent mode (menu 7.3.2.x on S2125) and blocked frequency bands [29].

**Why a cap works on a proportional controller.** With a power cap, a large start error still asks for maximum frequency. The inverter clips it at the cap, so the unit runs at a moderate speed and the error decays more slowly. Delivered heat per start is the same; it simply arrives over a longer, cooler, more efficient run. The cost is slower recovery after hot water or after a long off period. In a slab house with 6.6 kWh/K of storage, slower recovery is almost free.

### 5. Quiet mode is three different things

| Brand / doc | Quiet mode effect | Source |
|---|---|---|
| Gree Versati II | Compressor **and** fan frequency down, capacity down | [1] |
| Gree Versati III (field, via note 08) | Strong fan reduction; defrost every ~52–56 min at +2…+5 °C | note 08 |
| Panasonic 2013 SXC | Fan only: target fan speed −80 rpm, minimum 200 rpm | [27] |
| Panasonic (HeishaMon) | Levels 0–3 ("less power" to "least power"); sound or capacity priority | [24] |
| Vaillant | Noise reduction % = rps cap; used by owners to stop max-speed starts | [7][14] |
| Daikin | Levels 1–3; usable as power limiter | [23] |
| Samsung | Reduces output; can be scheduled | Samsung Gen6 manual (not cited) |

If quiet mode works mainly through fan speed, it lowers evaporating temperature. At the same compressor speed that means lower COP, and in humid near-zero weather more frost. Use quiet mode as a compressor cap only where it is documented or measured to cap the compressor (Vaillant). On this Gree, prefer the power limit or the maximum-frequency register.

### 6. "Setpoint riding": keeping the setpoint just above actual flow

**Idea.** On a unit whose speed is proportional to (setpoint − LWT), an external controller can choose the speed by choosing the gap. A gap of +1 K gives a slow compressor and a gap of +5 K a fast one. The unit then behaves like a modulating heat source driven by the house controller.

**Working example (Ecodan, open source) [35]:**
- Flow target = measured return + target ΔT. Target ΔT is interpolated between a minimum and a profile maximum by room error, using a smoothstep curve.
- Guard: if the target is ≥ 1.0 °C **below** the measured feed, it is raised to feed − 1.0 °C. The doc says a setpoint that far below a running feed stops the compressor.
- Step limit: while running, adjustments are at most **0.5 °C** every **30 s**. Paused during hot water, defrost and similar.
- "Smart boost" after stagnation: floor profile waits 60 min, then raises ΔT in steps every 30 min, up to 1.5×.
- Defaults: heating flow limited to 25–38 °C. The unit must be in fixed-flow mode.

**Other attempts.**
- Timbones reports an "offset above return" ramp on a Mitsubishi worked "kinda okay" [14].
- Andre_K proposes starting with a low target and walking it up so a Vaillant stays at minimum. Untested [14].
- The HA Ecodan user caps start error at < 11 K [37].
- A HeishaMon example rule, the opposite tool: after any compressor stop with outdoor ≥ 2 °C, apply a −5 K curve offset for 45 min to stop an immediate restart [26].

**Failure modes:**
- **Hunting / moving goalposts:** Daikin owners say frequent target changes make the unit chase a moving LWT target and lose efficiency [18].
- **Oscillation:** Samsung "zig-zag" power swings of ~400 W while modulating. Causes debated (firmware, volume) [43].
- **Unit ignores small differences:** many controllers have deadbands or only act on integrated error (DM, °min, K·min) [9][30][33]. A +1 K gap on a DM machine takes ~60 min to reach −60 DM, so the start is delayed, not modulated.
- **Stop on small overshoot:** Gree stops after the heat run time in the standby zone [3]. Panasonic stops at +2 K for 3 min [27]. Daikin stops at the overshoot setting (default only 1 K) [17]. If the ride drifts below LWT, the run ends.
- **Restart hysteresis interaction:** riding only works *during* a run. The start still needs setpoint ≥ LWT + ΔT-Heat on Gree. The start kick therefore cannot be avoided by riding alone; it needs a cap, a lower ΔT-Heat, or both.
- **Early-run lockout:** if the 6-min capacity hold [2] still exists, the first minutes run at whatever speed the unit picked at start, regardless of the ride.
- **Bus write load:** the Ecodan controller writes up to every 30 s. On Gree, note 08 says changes take effect immediately but are stored after 30 min. Frequent writes probably do not wear EEPROM, but this is unverified.

### 7. Cycling: how bad are starts, really?

- **EA Technology (DECC 2012), test house, fixed-speed units [54]:**
  - Runs < 6 min clearly hurt COP.
  - ASHP runs of ~8 min reached catalogue COP.
  - GSHP optimum was 10–15 min; worst-case reduction was ~16% (1.6-min runs).
  - Recommendation: minimum run ~6 min, longer is better. Buffer tanks lengthened runs from 1.6 to ~8 min.
- **Mimer Energy modelling for the same project [55]:** start-up inefficiency on two time scales. First the refrigerant cycle has to establish itself; then the heavy components (compressor, heat exchangers) have to warm up. Inverters remove the electrical and mechanical start shock but not the thermal losses.
- **MERL (Qiao & Laughman 2023), simulation [56]:** stopping off-cycle refrigerant migration cuts cycling loss by > 95%. A faster capacity rise time (−75%) cuts it ~60%.
- **Piechurski et al. 2018 (field data, air-to-water) [52]:** operational degradation coefficient Cc 0.79–0.81. The standard default is 0.9, and test values are 0.96–0.99. Real part-load and cycling losses are underestimated by standard ratings.
- **Keymark aroTHERM plus 7 kW [53]:** declared Cdh at part-load points 0.94–0.99.
- **UK Home Energy Model (HEM-TP-12) [57]:** below the minimum modulation ratio, on/off inertia losses are added with the EN 15316-4-2 formula ∝ LR·(1 − LR), using emitter-dependent time constants.
- **Rules of thumb from field monitors:**
  - Energy Stats: under 1 start per running hour is good, 1–2 fine, over 2 worth investigating [8][9].
  - OEM moderators: a couple of cycles per hour at minimum modulation in mild weather is acceptable ("type 2" load cycling). Room-thermostat cycling with a curve set too high ("type 1") is where efficiency is lost [44][22].
- **Before/after (forum, self-reported):** 150+ starts/day → 1–2/day with near-continuous running took COP from ~2.5 to ~4 [45]. Another owner's cycling algorithm at 9 °C average gave COP 3.32 vs 2.58 continuous. Different dates, so confounded [47].

**For this house.** Cycle length is not the main problem: observed runs are 0.5–4 h. The losses come from:
- **how** each run starts (large error, high speed, high LWT);
- hot-water interruptions that restart space heating with a large error;
- the 4 K restart band, which forces every start to be a step.

### 8. Minimum output vs load: the core constraint

**Turndown of other units.**
- Energy Stats lists minimum heat output: Vaillant 5 kW ~2.2, 7 kW ~3.2, 10/12 kW ~5.8 kW; Grant R290 9.4 kW ~2.5 kW [8].
- OEM tests: Vaillant 10 kW ~5.9 kW min [62].
- A Daikin 9 kW ~3–3.5 kW, or "just over 5 kW" per another owner (contradiction) [22].
- The Versati's ~3.75 kW (owner-measured) is a poor turndown for a 9 kW class unit.

**Cycle point.** Energy Stats' formula: cycle point = T_in − P_min / (heat loss per K) [8]. This house: 22 − 3.75 / (0.14…0.20) = **−4.8 to +3.3 °C**. Below that the unit can in principle run continuously at minimum. Above it, it must cycle.
- So at +2 °C (load ≈ 2.8–4.0 kW) continuous minimum-speed running is roughly possible.
- That makes the observed ~3 kW-electric catch-up runs at +2 °C (likely 6–8 kW heat) a control artefact, not a physical necessity.

**Sizing slab-buffered blocks (my calculation).** At +10 °C (load 1.7 kW), a minimum-output run adds 3.75 − 1.7 ≈ 2.05 kW to the slab.
- A 2 h run stores ~4.1 kWh, ≈ +0.6 K of slab temperature with 6.6 kWh/K.
- That is followed by ~2.4 h off.
- Result: about 5 starts/day and room swing well under 0.5 K, if the slab-to-room coupling is slow (see note 05).

## What this means for controlling this house

The house: slab UFH, one zone, 6.6 kWh/K storage, heat loss 0.14–0.20 kW/K. Gree Versati 9 kW class, minimum output ~3.75 kW. Flow setpoint written over Modbus every ~30 min. The unit restarts only when setpoint − LWT ≥ ~4 K (ΔT-Heat = 4).

Confidence labels: **H** = documented mechanism plus field data; **M** = documented mechanism, plausible magnitude, not verified on this unit; **L** = hypothesis.

### A. Measure first (cheap, decisive)

1. Log Words 142/143 (set and actual Hz), electrical power, LWT, return, setpoint and outdoor temperature at 10–30 s for a week. Answers:
   - the real minimum Hz and minimum output vs outdoor temperature;
   - the start profile: is there a 6-min hold [2], and how fast does Hz climb after a +4 K start?
   - Hz vs power vs COP during catch-up.

   **H** that this is the right first step. Nobody has published Versati frequency-response data.
2. From those logs, compute COP binned by Hz at similar outdoor and LWT. Expect the 50–80% of max-Hz bins to be 15–30% worse than the minimum bins [7][48][49]. **M**

### B. Unit settings

3. **Turn on the power limit (C/P limit = Power limit, Word 43) and leave it on.** Starting value about **1.4 kW electrical** above −3 °C outdoor. That is ~1.4–1.6× the expected minimum-speed input (~0.8–1.0 kW at +2…+10 °C, assuming COP 4–4.5 at minimum). It leaves room for the unit to work but removes 3 kW bursts. Raise to 2.5–3.5 kW below −5 °C, or keep 3.0 kW (Gree default) as a cold-weather value.
   - **Test defrost under the cap on a humid 0…+3 °C day.** Daikin requires ≥ 3.6 kW for defrost on its larger units [17]. Gree is silent.
   - Test hot-water reheat time under the cap. Switching the cap per mode is one Modbus write.
   - **M**: mechanism documented; behaviour of Gree's cap during defrost and hot water unknown.
4. **Alternatively or additionally, cap maximum frequency** (Address 72) at the low end of the suggested 65–85 Hz [5], if the firmware accepts it. A frequency cap is less direct than a power cap for COP, because Hz at a given power varies with lift. Use it only if Word 43 is unavailable or ignored. **L/M**
5. **Do not use quiet mode as the speed cap** in humid weather around 0 °C. Gree quiet also lowers fan speed, and a sister unit saw ~hourly defrosts [1] (note 08). **M**
6. **ΔT-Heat (restart band):** consider lowering from 4 K to 2–3 K *together with* the power cap. A smaller band makes start steps smaller. The cap makes whatever step remains harmless. With the slab's long time constant, more frequent starts are not a comfort problem. The trade-off is more starts per day; aim for ≤ 6–8 starts/day and runs ≥ 30 min. **M**
7. **Heat run time:** at least the default (3–5 min) or longer, so brief LWT overshoot at minimum frequency does not stop a run [3]. **M**

### C. Control rules for the external controller (three candidate logics to test)

8. **Logic 1: "Cap and step" (simplest; recommended first).** Power cap as above. Write setpoint = LWT + ΔT-Heat + 0.5 K only to *start* a heating block. Once running, write a modest target (the slab-based flow temperature, typically 27–31 °C) and leave it. Stop by dropping the setpoint ≥ 1–2 K below LWT. Heat delivered per block is set by block length, not by water temperature.
   - Expected: no 3 kW draws, lower LWT during runs, same or fewer starts.
   - **M/H**: mechanism documented, impact plausible.
9. **Logic 2: "Glide / setpoint riding."** Same start kick, but within 1–2 min of start (or after the 6-min hold, if it exists) set the target to **LWT + 1…2 K**. Follow LWT upward in steps of **≤ 0.5 K per 1–5 min**, never below **LWT − 1 K** while the block should continue. Ecodan practice is ≤ 0.5 K / 30 s and a −1 K floor [35]. End the block by dropping the target well below LWT.
   - Keep the power cap as a backstop.
   - Risks: oscillation [43], a stop if the error sits in the standby zone too long [3], more Modbus writes.
   - **M** that it works on Gree (proportional control documented); **L** on how stable it is.
10. **Logic 3: "Return + ΔT" (Ecodan auto-adaptive style).** While running, target = return + ΔT_target, with ΔT_target 3–5 K chosen by room/slab error, clamped to 25–35 °C. The unit's heat output then follows the floor's acceptance instead of a fixed water temperature [35]. Same guards as Logic 2. **L/M**
11. **Never** write a large setpoint jump (> ~4–5 K above LWT) without the cap active. That is the documented path to near-maximum frequency [1][3][37]. **H**
12. **After hot water**, return to space heating with a low target and let the cap or ride bring it up. Panasonic owners hit the 2 K overshoot stop on the hot-water-to-heating switch and ramp the target down by rule [27] (note 04). Expect the same sensitivity on Gree. **M**
13. **Write cadence:** the current 30-min write interval is too slow for Logics 2–3. For Logic 1 it is fine as long as each block starts and stops on time. Note 08: Gree stores changes after 30 min, so faster writes probably do not wear EEPROM, but this is unverified. **L/M**

### D. What to avoid

- Starting blocks with big errors or using high water temperature to "catch up". Slow recovery costs little in a slab house. High-speed recovery costs 15–30% COP on that energy [7][48][49].
- Quiet mode as a substitute for a cap [1][27].
- Very low caps that might interrupt defrost [17].
- Riding the setpoint below LWT, which ends the run [3][35].
- Frequent target "nudges" that make the unit hunt [18].

### E. Expected size of the prize

Catch-up runs at +2 °C reportedly draw ~3 kW. Say they deliver 30–40% of daily heat on cold, humid days. Moving that energy to minimum-speed runs at 2–4 K lower LWT is worth:
- 15–30% on those kWh from speed [7][48][49];
- about 5–10% from lower flow temperature [34][58].

That is roughly **5–15% of daily heating electricity** on such days (estimate, **L/M**). Fewer starts add a little more; most of the cycling loss is already avoided by long runs.

## Contradictions and open questions

1. **Where is COP highest: minimum speed or mid speed?**
   - KTH: whole-unit COP highest at the lowest tested speed (30 Hz), compressor efficiency peaking at 60 Hz [48].
   - Dongellini: COP peak at ~half speed (40–60 Hz of 120) [49].
   - Fahlén: rising COP down to 10–20% capacity only if fans and pumps also scale down; otherwise COP falls at f = 0.2 [50].
   - OST field: Carnot efficiency collapses below a unit-specific low load [51].
   - Consistent reading: COP falls with speed down to about 25–40% of maximum, then drops off as fixed losses dominate. Where the Versati's minimum sits on that curve is unknown. Log it.
2. **Gree compressor range:** 20–120 Hz (catalogue, note 08) vs "down to 10 Hz" (Czech catalogue, note 01) vs a measured ~3.75 kW minimum output. Unresolved.
3. **Does the Gree power limit cap only the compressor, or the whole unit including backup heater, and does it apply during defrost and hot water?** Not documented [4]. Daikin's equivalent includes the backup heater and needs ≥3.6 kW for defrost on bigger units [17]. Do not assume Gree behaves the same.
4. **Is the 6-min post-start capacity hold [2] present in Versati III firmware?** If yes, the start speed is locked for 6 min regardless of setpoint riding, and only a cap can lower it.
5. **Quiet mode semantics differ:** fan-only (Panasonic 2013 [27]) vs compressor+fan (Gree [1]) vs compressor cap (Vaillant [7]). Brand claims of "quiet = efficient" do not transfer.
6. **Ecodan forum disagreement:** Auto Adapt is better because of lower average target (John Cantor) vs it runs higher flows with larger over- and undershoots (another owner) [39]. Small samples, no metering in the thread.
7. **Samsung zig-zag cause:** firmware vs system volume vs measurement artefact. Unresolved [43].
8. **Daikin 9 kW minimum output:** ~3–3.5 kW vs "just over 5 kW" from two owners [22]. Minimum output depends on outdoor temperature and flow temperature, so single numbers mislead.
9. **Cycling penalty size:** EA Technology worst case ~16% for 1.6-min runs on fixed-speed units [54], vs field Cc ≈ 0.80 [52], vs manufacturer Cdh 0.94–0.99 [53]. These measure different things (short-run penalty vs all part-load degradation vs a standby-only test).
10. **No published frequency-response data (gain, time constant, start profile) for any Versati.** The control design in section C depends on it.
11. **Ecodan "flow temperature increment" and FTC6 maximum-frequency settings:** the brief listed them, but I could not read the FTC6 service manual (search budget exhausted). The only Ecodan evidence here is the 104 Hz observation and the open-source controller [35][37]. **Unverified.**
12. **Is "setpoint riding" stable on a proportional-only loop with a standby-zone stop rule?** No published Gree example. Test with logging (A1) before relying on it.

## Sources

1. Air-to-water Heat Pump Split Versati (Versati II, NaE) service manual - Gree - 2016 - https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-ii-e-szeria/service%20manual%20gree%20en%20versati%20ii%20nae.pdf - manufacturer - Frequency proportional to LWT error; stop at min frequency; ramp-down stop; quiet lowers compressor and fan frequency.
2. Air-to-Water Heat Pump Service Manual, Versati (first generation, T1) - Gree - c. 2012 - https://gree-bulgaria.com/manuals/archive/5_Versati-TSM.pdf - manufacturer - 6-min no-adjust after start, 3-min restart lockout, 3-min EEV hold; frequency follows LWT error.
3. VERSATI III All-in-one service manual - Gree - c. 2020 - https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iii/versati%20iii%20all%20in%20one%20%E2%80%93%20service%20manual.pdf - manufacturer - Same proportional logic; heat run time 1–10 min with standby-zone stop; load 70–120% advice (oil return / high frequency); 20 L minimum volume.
4. "Gree Versati III Air to water heat pump", page 3 - Home Assistant Community - 2023 - https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916?page=3 - forum - Power limit Word 43, 0–10 kW, default 3 kW, ×10 encoding.
5. Same thread, page 5 - Home Assistant Community - 2026 - https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916?page=5 - forum - Set vs actual frequency; max-frequency Address 72 (65–85) with unit off and coil 40 on.
6. (Sibling note) 08-gree-versati.md - this project - 2026 - docs/research/notes/08-gree-versati.md - internal cross-reference - Register map, quiet-mode defrost field report, EEPROM memorisation after 30 min. Not counted as a read source.
7. Vaillant Arotherm Sweet Spot Hot Water Mode - M. Wall, Energy Stats UK - 2024/25 - https://energy-stats.uk/vaillant-arotherm-sweet-spot-hot-water-mode/ - blog with measured field data - COP 3.55–3.85 at 50 rps vs 3.26 at 80 vs 2.85 at 120 rps; noise-reduction % → rps map.
8. Heat Pump Cycling and Minimum Modulation - M. Wall, Energy Stats UK - 2024/25 - https://energy-stats.uk/heat-pump-cycling/ - blog with field data - Minimum outputs by model; cycle-point formula; starts-per-hour guidance; on/off times vs outdoor temperature.
9. Vaillant Arotherm Firmware 351.06.07 Problems (Energy Integral) - M. Wall, Energy Stats UK - 2024 - https://energy-stats.uk/vaillant-arotherm-firmware-351-06-07-problems-energy-integral/ - blog with field data - −60/0 °min logic; bug doubled the count; 35 → 55 min cycles, COP 4.82 → 5.02.
10. Vaillant Arotherm Heat Pump Guide - M. Wall, Energy Stats UK - 2025/26 - https://energy-stats.uk/vaillant-arotherm-heat-pump-guide/ - blog - Eco DHW ~50% compressor, Sweet Spot ~80 rps; SCOP vs flow examples.
11. SensoCOMFORT Room Temp Mod: Inactive, Active or Expanded? - M. Wall, Energy Stats UK - 2024/26 - https://energy-stats.uk/sensocomfort-room-temp-mod-inactive-active-or-expanded/ - blog with measured data - Active cuts flow ~2.2–3.0 K at +1.5 K room error; Expanded on/off band ~0.31 K.
12. Vaillant Arotherm Performance Tables - Energy Stats UK - 2025 - https://energy-stats.uk/vaillant-arotherm-performance-data/ - blog (manufacturer tables) - 5 kW A7/W35 at 40 rps ~2.9 kW, COP 4.6; A2/W35 at 60 rps ~3.7 kW, COP 3.7.
13. aroTHERM / VWZ AI installation and operating manual - Vaillant - n.d. - https://professional.vaillant.co.uk/downloads/aproducts/renewables-1/arotherm-plus/monoblock-heat-pump-system-vwz-ai-heat-pump-appliance-interface-2685948.pdf - manufacturer - Energy balance integral; compressor hysteresis; current-limit status S.289 reduces compressor speed (16 A / 25 A); speed 0–120 rps.
14. Vaillant Arotherm Owners Thread, page 30 - OpenEnergyMonitor forum - c. 2024 - https://community.openenergymonitor.org/t/vaillant-arotherm-owners-thread/21891?page=30 - forum - Near-max speed for minutes after start; quiet mode as cap; target-walking idea; Mitsubishi offset-above-return ramp "kinda okay".
15. Vaillant Energy Integral "Compr. start heat. from" - OpenEnergyMonitor forum - 2024 - https://community.openenergymonitor.org/t/vaillant-energy-integral-compr-start-heat-from/26876 - forum - ~1 °min per minute per K; hour-long runs at +1 K.
16. Help Interpreting ASHP Data and Cycling Behavior - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/help-interpreting-ashp-data-and-cycling-behavior/27849 - forum - Slab UFH ~25 °C flow at 7 °C, COP > 6; −60 → −100 °min advice and overheating caveat.
17. Daikin Altherma LT split installer reference guide 4P401677-1A - Daikin - 2016 - https://www.daikin.eu/content/dam/document-library/Installer-reference-guide/heat/air-to-water-heat-pump-low-temperature/ERQH011-016BV3-BW1,%20ERLQ011-016CV3-CW1,%20EHVZ-CB3V_4PEN401677-1A_Installer%20reference%20guide_English.pdf - manufacturer - Power consumption control (kW/A, permanent/DI, order of limiting, ≥3.6 kW for defrost); overshoot [9-04] 1–4 K; modulated LWT; emitter type.
18. Having to adjust Daikin WD curve daily, page 3 - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/having-to-adjust-daikin-wd-curve-daily-cant-be-right/27857?page=3 - forum - Overshoot 1–4 K; "moving goalposts" hunting when targets change often.
19. Daikin Altherma cycling every 5 mins - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/daikin-altherma-cycling-every-5-mins/28065 - forum - 4–5 min cycles; overshoot 4 K fix; each cycle starts at max pump flow ~20 min.
20. Beyond Weather compensation (Daikin) - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/beyond-weather-compensation-daikin/29152 - forum - ±1 K HA offsets; WC + load + PID with < 0.4 °C error (anecdotal).
21. Two months of learning with Octopus Daikin - OpenEnergyMonitor forum - 2024–25 - https://community.openenergymonitor.org/t/two-months-of-learning-with-octopus-daikin/27379 - forum with owner data - Madoka 3 °C target steps at 0.5/1.0 K room error, off at +1.5 K; pump high for ~25 min after start.
22. Concerned about Daikin modulation - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/concerned-about-daikin-modulation/29340 - forum - 9 kW minimum ~3–3.5 vs >5 kW (contradiction); min input 600–810 W; "couple of cycles per hour" acceptable.
23. P1P2Serial / P1P2MQTT - A. Nijenhuis, GitHub - 2024–26 - https://github.com/Arnold-n/P1P2Serial - project docs - Quiet levels usable as power limiter; LWT setpoint control; write-count limits.
24. HeishaMon MQTT topics - HeishaMon, GitHub - current - https://github.com/Egyras/HeishaMon/blob/master/MQTT-Topics.md - project docs - Quiet levels 0–3 and priority, powerful mode, max pump duty, heat deltas.
25. HeishaMon Optional PCB - HeishaMon, GitHub - current - https://github.com/Egyras/HeishaMon/blob/master/OptionalPCB.md - project docs - SetDemandControl 5–100% (43–234/235), SG modes, H74 after ~40 s without commands.
26. Compressor-Short-Cycle-Guard rules - HeishaMon, GitHub - 2026 - https://github.com/heishamon/HeishaMon/tree/main/Examples/Rules/Compressor-Short-Cycle-Guard - project code - −5 K offset for 45 min after stop at ≥ 2 °C outdoor.
27. Aquarea WH-SXC09/12F service manual PAPAMY1311028CE - Panasonic - 2013 - https://www.panasonicproclub.com/uploads/CZ/catalogues/aquarea/service-manual/SXC9,12_F_E8_service%20manual_PAPAMY1311028CE.pdf - manufacturer - Frequency from internal setpoint vs outlet; off at +2 K for 3 min; restart −3 K after 3 min; quiet = fan −80 rpm.
28. Panasonic Aquarea heat pump configuration - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/panasonic-aquarea-heat-pump-configuration/28349 - forum - Curve and ΔT settings; cycling at ΔT ≈ 0; little on frequency (weak).
29. NIBE S-series firmware changelog (myUplink) - NIBE - 2021–26 - https://www.nibe.eu/webdav/files/myuplink_changelog/nibe-n.pdf - manufacturer - Air-source soft start at min speed; step difference 60 → 200 DM; start-up regulation and short-operation fixes; silent-mode max frequency.
30. NIBE S1256 installer manual, menu 7.1.10.3 degree minutes - NIBE via ManualsLib - n.d. - https://www.manualslib.com/manual/3348937/Nibe-S1256pc.html?page=54 - manufacturer - Start compressor −1000…−30 DM; step settings.
31. Nibe 2040/12 thread - ByggeBolig (Norway) - 2019 - https://byggebolig.no/luft-vann-varmepumpe/nibe-204012/10 - forum - Stop at DM 0; start at ~−125 DM; 25 Hz minimum bursts.
32. SMO40 / F2120 compressor frequency - Värmepumpsforum (Sweden) - 2023–24 - https://www.varmepumpsforum.com/vpforum/index.php?topic=81226.0 - forum - ~25 Hz ≥ +8 °C, ~35 Hz below; 50–60 Hz at 10–16 °C when supply above target; start DM −120/−180.
33. Visualize the on/off hysteresis for Nefit/Bosch heat pump - Home Assistant Community - 2023 - https://community.home-assistant.io/t/visualize-the-on-off-hysteresis-for-nefit-bosch-heat-pump/634160 - forum - 150 K·min split default; ~200/250 K·min monobloc.
34. Ecodan product guide, Auto Adaptation page - Mitsubishi Electric - c. 2023 - https://renewableheatinghub.co.uk/wp-content/uploads/wpforo/attachments/5124/4908-EcodanFullProduct.pdf - manufacturer - 2% COP per 1 K flow; room prediction to avoid unnecessary flow changes.
35. esphome-ecodan-hp, Auto-Adaptive documentation - gekkekoe, GitHub - 2025–26 - https://github.com/gekkekoe/esphome-ecodan-hp/blob/main/docs/auto-adaptive.md - project docs - Target = return + ΔT; −1 K feed floor; ≤ 0.5 °C per 30 s; floor-profile boost timings; 25–38 °C defaults.
36. esphome-ecodan-hp, short-cycle mitigation - gekkekoe, GitHub - 2025–26 - https://github.com/gekkekoe/esphome-ecodan-hp/blob/main/docs/short-cycle-mitigation.md - project docs - Min-on-time lockout via server control.
37. Advanced PV-Boost & Anti-Short-Cycling Logic for Mitsubishi Ecodan (FTC6) - Home Assistant Community - 2026 - https://community.home-assistant.io/t/advanced-pv-boost-anti-short-cycling-logic-for-mitsubishi-ecodan-ftc6-anyone-with-a-similar-setup/1007019 - forum - Fake target keeps start ΔT < 11 K, preventing 104 Hz; 10-point SOC hysteresis.
38. Reasons for Ecodan overshooting target fixed flow temperature - OpenEnergyMonitor forum - 2024–25 - https://community.openenergymonitor.org/t/reasons-for-ecodan-overshooting-target-fixed-flow-temperature/25489 - forum - +5/−3 thermo-diff letting 32 → 37 °C; "heat pumps don't control flow temperature".
39. Anyone monitoring a new R32 Ecodan? page 14 - OpenEnergyMonitor forum - 2024 - https://community.openenergymonitor.org/t/anyone-monitoring-a-new-r32-ecodan/19577?page=14 - forum - 3.7 kW min vs emitter output; ~3 cycles/h at COP 3.16; Auto Adapt disagreement.
40. Getting our Ecodan heat pump into Home Assistant, third attempt - M. Harizanov - 2026 - https://harizanov.com/2026/09/getting-our-ecodan-heat-pump-into-home-assistant-third-attempt/ - blog with owner data - 6,500 starts / 8,345 h; 77% of hours with a stop; min 4.3–5 kW; SCOP 3.14.
41. Performance of Heat Pumps in Mild Weather - Renewable Heating Hub - 2025 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/performance-of-heat-pumps-in-mild-weather - forum - High-power starts (Samsung, Viessmann, Daikin); turndown ~3:1 typical.
42. Running ASHP efficiently, low and slow, page 2 - Renewable Heating Hub - 2024 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/runing-ashp-efficiently-general-thought-process-low-and-slow/paged/2 - forum - Slab "saturation" leading to rising return and cycling; Ecodan 5 kW minimum ~1.9–2.4 kW.
43. Samsung HT Quiet R32 8kW: COP vs simulated COP and zigzag pattern - OpenEnergyMonitor forum - 2024–25 - https://community.openenergymonitor.org/t/samsung-ht-quiet-r32-8kw-emoncms-cop-vs-simulated-cop-and-zigzag-pattern/27385 - forum - ~400 W modulation oscillation; ~25 Hz at 5 kW; Carnot factor 0.46–0.47.
44. Heat pump demand cycling vs compressor load cycling - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/heat-pump-demand-cycling-vs-compressor-load-cycling/29277 - forum - Type 1 vs type 2 cycling; Samsung +2 K stop, FSV#1061/#6022; flash cooling after stops.
45. How to reduce cycling? page 6 - OpenEnergyMonitor forum - 2024 - https://community.openenergymonitor.org/t/how-to-reduce-cycling/25251?page=6 - forum - 150+ → 1–2 starts/day; COP ~2.5 → ~4 (self-reported).
46. Weather Compensation & ASHP Duty Cycle - OpenEnergyMonitor forum - 2023 - https://community.openenergymonitor.org/t/weather-compensation-ashp-duty-cycle/24793/4 - forum - 50–70% duty; Samsung 8 kW < 800 W for 3 kW at 35 °C.
47. Improve efficiency: Turn the heat pump off - OpenEnergyMonitor forum - 2020–23 - https://community.openenergymonitor.org/t/improve-efficiency-turn-the-heat-pump-off/13381 - forum with owner data - COP 3.32 cycling vs 2.58 continuous at 9 °C (confounded).
48. Awan U.K., Experimental Analysis of Variable Capacity Heat Pump System Equipped with Vapour Injection and Permanent Magnet Motor - KTH MSc thesis - 2012 - https://www.diva-portal.org/smash/get/diva2:565195/FULLTEXT01.pdf - lab - COP_heat −32% from 30 to 90 Hz; Carnot/isentropic peak at 60 Hz; inverter loss 95 → 225 W (10% → 6%).
49. Dongellini M., Dynamic modeling and seasonal performance evaluation of air-to-water heat pump systems - University of Bologna PhD - 2017 - https://amsdottorato.unibo.it/id/eprint/7901/1/Dynamic%20modeling%20and%20seasonal%20performance%20evaluation%20of%20air-to-water%20heat%20pump%20systems.pdf - paper (model on manufacturer data) - PID on supply/return; COP max at 40–60 Hz, +20% vs 120 Hz; 15–30 Hz minimum and oil-return limits.
50. Fahlén P., Capacity control of heat pumps - REHVA Journal - 2012 - https://www.rehva.eu/rehva-journal/chapter/capacity-control-of-heat-pumps - paper (analysis/lab) - System COP by capacity fraction and motor type; COP rises to 7.1–7.4 at low capacity only if fans and pumps scale.
51. Repke T. (supervised by Bertsch S.), Teillastverhalten von invertergeregelten Wärmepumpen - OST thesis abstract - 2026 - https://www.ost.ch/files/daten/abstracts/pdf/990f3d2f-cae1-4a03-a95e-8e279b8902f2.pdf - field data (abstract) - Carnot efficiency stable over range but collapses below unit-specific low load.
52. Piechurski K. et al., Quasi-dynamic model of the energy efficiency degradation coefficient for an air-to-water heat pump - E3S Web of Conferences 44, 00139 - 2018 - https://doi.org/10.1051/e3sconf/20184400139 - field data + paper - Operational Cc 0.79–0.81 vs 0.9 default vs 0.96–0.99 test; PLR 0.17–0.80.
53. HP KEYMARK certificate, Vaillant aroTHERM plus VWL 75/6 A 230V - Vaillant / Keymark - 2022 - https://downloads.vaillant.cz/downloads/certifik-ty/certifikat-hp-keymark-arotherm-plus-svt24748-vwl-75-6-a-230v-2585793.pdf - lab (certified) - Part-load Pdh/COP/Cdh (e.g. colder climate W35 Tj +12 °C 3.73 kW COP 7.71, Cdh 0.94–0.99).
54. The Effects of Cycling on Heat Pump Performance - EA Technology for DECC - 2012 - https://assets.publishing.service.gov.uk/media/5a78e0d9e5274a2acd18a7c6/7389-effects-cycling-heat-pump-performance.pdf - lab (test house) - < 6 min runs detrimental; ~8 min ASHP ≈ catalogue COP; worst ~16% loss.
55. Effects of cycling on domestic GSHPs, simulation/modelling (C207-R2) - Mimer Energy for DECC - 2012 - https://assets.publishing.service.gov.uk/media/5a7a37f9e5274a319e778b1d/mimer_report_on_modelling_cycling_of_heat_pumps.pdf - paper (model calibrated on lab) - Two-time-scale start-up penalty; inverters avoid electrical shocks but not thermal start losses.
56. Qiao H., Laughman C., Theoretical analysis of cycling losses in air source heat pump systems (TR2023-127) - MERL - 2023 - https://merl.com/publications/TR2023-127 - paper (simulation) - Refrigerant migration dominates; > 95% loss reduction if prevented; rise time −75% → −60% loss.
57. HEM-TP-12 Heat pump methodology - UK DESNZ - 2025/26 - https://assets.publishing.service.gov.uk/media/6583f139ed3c34000d3bfcc6/hem-tp-12-heat-pump-methodology.pdf - standard methodology - Minimum modulation ratio and EN 15316-4-2 on/off inertia term.
58. Low flow temperature = High performance - OpenEnergyMonitor docs (T. Lea) - 2025 - https://docs.openenergymonitor.org/heatpumpmonitor/low_temperature.html - field data (fleet regression) - SPF −0.10 per K flow; −0.105 per K (flow − outdoor).
59. Wärmepumpen in Bestandsgebäuden (WPsmart im Bestand) final report - Fraunhofer ISE - 2020 - https://wp-monitoring.ise.fraunhofer.de/wpqs-im-bestand/download/Berichte/BMWi-03ET1272A-WPsmart_im_Bestand-Schlussbericht.pdf - field data - Modulation brings larger efficiency gains for air-source than ground-source units, plus fewer starts (qualitative passage read).
60. Eurovent certificate GRS-CQ22Pd/NhA-M (Versati MAX) - Eurovent Certita - n.d. - https://www.eurovent-certification.com/en/catalog/program/certificate/participant/model/show/202131606 - lab (certified) - A7/W35 COP 4.50, W45 3.50, W55 2.75 (flow-temperature sensitivity of a Gree unit).
61. Weather Compensation or Load Compensation? - Heat Geek - 2018 - https://www.heatgeek.com/weather-compensation-or-load-compensation - blog - Load compensation reacts late and runs hotter; WC cycles less (qualitative).
62. HeatpumpMonitor.org heat pump database: minimum modulation tests - OpenEnergyMonitor forum - 2025 - https://community.openenergymonitor.org/t/heatpumpmonitor-org-heat-pump-database-minimum-modulation-tests/29132 - field data - Vaillant 10 kW min ~5.9 kW; Ecodan R290 8 kW < 2 kW for hours.
63. Monitoring results from a 5kW Ecodan heat pump - OpenEnergyMonitor forum (T. Lea) - 2022 - https://community.openenergymonitor.org/t/monitoring-results-from-a-5kw-ecodan-heat-pump/20764 - field data - Pi-controlled flow target, SCOP 3.9–4.0 (context only).
64. Blanco D.L., Nagano K., Morimoto M., Experimental study on a monovalent inverter-driven water-to-water heat pump with a desuperheater - Applied Thermal Engineering 50 - 2013 - https://eprints.lib.hokudai.ac.jp/repo/huscap/all/52254/ATE50-1_826-836.pdf - lab - Highest COP at 45 Hz (lowest tested) across most conditions.
