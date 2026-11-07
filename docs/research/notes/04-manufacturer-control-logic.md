# How manufacturers control space heating

Researcher topic 04. Scope: the actual algorithms and factory parameters that heat-pump makers use for space heating. That covers the weather-compensation curve, room influence, self-adapting curves, compressor start/stop (degree minutes, energy integral, hysteresis, overshoot), inverter speed control, and how each maker handles mild-weather cycling and minimum run time. Brands covered: NIBE, Danfoss/Thermia-type, Vaillant, Viessmann, Daikin, Panasonic, Mitsubishi, Samsung, LG and Gree.

Notation: `[n]` = source number (see Sources). `[calc]` = my own arithmetic from the house data in the brief, using the stated assumptions. Treat it as order-of-magnitude, not measurement. Evidence ranking used: measured field data > controlled lab > peer-reviewed simulation > manufacturer documentation/claim > forum anecdote. Most of this topic lives in manufacturer manuals, so most facts are tagged "manufacturer". The forum evidence is the only field evidence on what the settings do in practice, and it is anecdotal.

Method note: 22 web searches were run (English, German and a Swedish forum) before the search budget, shared by all 15 parallel researchers, ran out. Two more searches, on the Gree curve and Modbus, were refused. After that, only pages already found or linked were fetched. 44 sources were read: manufacturer PDFs were downloaded and text-extracted, and forum and manual pages were read directly. Polish, Dutch and Lithuanian queries were planned but could not be run.

House data used (from the brief): heat-loss coefficient H = 0.14–0.20 kW/K, slab storage C = 6.6 kWh/K, compressor minimum heat output P_min ≈ 3.75 kW, load ≈ 1.7 kW at +10 °C (implies H ≈ 0.14 net of gains), room target 22.0 °C. The unit is a Gree Versati 9 kW with no buffer. Its flow setpoint is written over Modbus about every 30 min, and it restarts only when setpoint − outlet ≥ ~4 K.

## Summary

- **Every brand uses the same three-layer structure, and the Gree uses the simplest variant.** (1) A flow-temperature target comes from an outdoor-temperature curve, optionally corrected by room temperature. (2) An on/off decision is made either by an *integral* of flow-temperature error or by a plain hysteresis/overshoot band. NIBE/Danfoss call the integral "degree minutes" (DM), Vaillant calls it the "energy integral"; Daikin, Panasonic, Mitsubishi, LG, Samsung and Gree use the band. (3) An inverter loop sets compressor speed from the flow error [1][10][11][27][31][42]. The Gree raises frequency as (actual − set) leaving-water error grows. It stops only when it is already at minimum frequency and still too warm [42][43]. So a big setpoint step produces a fast, hot, inefficient start.
- **Integral start/stop defaults are sized for radiators, not a 6.6 kWh/K slab.** NIBE starts the compressor at −60 DM (range −1000…−30) and stops at 0 [1][2][6]. Thermia/Danfoss-type controls start at A1 = −60 and add the auxiliary heater at A1+A2 (A2 = −600) [10]. Vaillant starts at −60 °min (VWZ AI range −999…+9) and stops when the delivered heat equals the deficit [11]. With the circulating loop 3 K below target, −60 is reached in ~20 min [calc]. Owners report about 0.5–3 cycles/h in mild weather: ~1 h on/1 h off [7], 2–3/h [8], and 1.4–1.9 per operating hour [18]. They lengthen cycles with −100 to −240 [7][19][20]. A slab-equivalent threshold for this house is roughly −300 to −700 °C·min [calc].
- **Every maker adds a hard backstop that ends a run regardless of the integral**:
  - NIBE "max diff compressor": 1–25 K, default 10 K. Above it, DM is forced to +1 or +2 and the compressor stops [3][4].
  - Vaillant compressor hysteresis: default 7 K, range 0/3–15 K [11].
  - Daikin LWT overshoot [9-04]: 1–4 K, default 1 K. The unit restarts as soon as LWT falls below target [27].
  - Panasonic: off after outlet > target + 2 K for 3 min. Restart ≥ 3 min later, once outlet < (inlet at stop − 3 K) [31].
  - Mitsubishi thermo-diff: upper +3…+5 K (default +5), lower −1…−9 K (default −5) [36].
  - LG: Temp On −2 K (0…−9), Temp Off +2 K (0…+4) [41].
- **Start-up behaviour drives efficiency in mild weather, and the leading makers now soft-start.** Since firmware 2.3.3 (2021), NIBE runs an air-source compressor at minimum speed after a start until the DM deficit drops or a timer expires. The same release raised the default compressor step difference from 60 to 200 DM [5]. Owners report Vaillant running near full speed for "several minutes" after each start [20], and NIBE F2040 runs of 15–20 min at high frequency [8]. In the Gree, frequency follows the setpoint error [42]. The house's "~3 kW electric catch-up runs" are therefore what a large setpoint step produces.
- **Mild-weather cycling is treated as unavoidable when load < minimum output; makers manage it rather than eliminate it.** Viessmann's planning guide states that oversizing causes extra cycling in the transition season and that the *lower* modulation limit matters as much as the maximum. It suggests more buffer volume [26]. For this house the balance point (load = 3.75 kW) is about −5 °C if H = 0.14 and about +3 °C if H = 0.20 [calc]. Most Lithuanian heating hours fall above it.
- **Modern turndown is 2–3× better than this Versati's.** A Vitocal 250-A 10 kW modulates 2.6–12.0 kW at A7/W35 and 2.2–11.0 kW at A2/W35; the 4–8 kW sizes go down to 1.8–2.1 kW [26]. A Vaillant 7 kW reaches about 25 % (~1.75 kW) [19]. An F2120 bottoms out at about 25 Hz above +8 °C (forum) [9]. A 3.75 kW minimum is ~40 % of a 9 kW class, so this unit must cycle across a wide outdoor range.
- **Curves are two-parameter almost everywhere, and the factory defaults are radiator-steep:**
  - Vaillant curve 0.1–4.0. Heat-pump default 0.60, min target flow 15 °C, max 55 °C, outdoor switch-off 16 °C [12][14]. A forum fit, Tflow ≈ Tset + 2.55·(HC·(Tset − Tout))^0.78, matches eBUS values within ~0.07 K [16].
  - Viessmann slope/level. A community formula reproduces the controller [24].
  - NIBE curve 0–15, default 9, min supply 20 °C [1].
  - Daikin two-point curve, default −10 °C → 35 °C and +15 °C → 25 °C [27].
  - Samsung "water law" default −10 °C → 40 °C and +15 °C → 25 °C [39].
  - Underfloor-heating slopes in German practice are 0.2–0.5 [44].
- **Room influence is bounded and meant to be slow; on/off room logic causes cycling.** Daikin modulates the LWT target by at most ±[8-06] (0–10 K, default 3 K) from room error, and has an emitter setting "slow" for floor loops [27]. The NIBE room factor is 0.0–6.0, default 2.0 [1]. Viessmann's room influence is on/off plus a strength setting [25]. Vaillant "Expanded" adds zone on/off at +2/16 K and −3/16 K room error [13]. Owners report it bypasses the integral and brings cycling back at 4–5 °C outdoor [18].
- **The newest controls replace the curve with a room model.** Mitsubishi Auto Adaptation is the factory default on FTC controllers. It estimates required capacity from room and outdoor temperature and predicts where the room is heading. It then lowers, holds or raises flow temperature [35][36]. NIBE S-series firmware 4.0.10 (March 2025) added machine-learning "Smart Room Comfort", which stops using heat curves and offset in normal operation. Version 4.9.4 (March 2026) added an "Auto degree minute" mode that reduces short run times [5]. Field evidence is thin: one Ecodan owner's rolling SCOP went from 3.4 to 3.6 with Auto Adapt [37].
- **Outdoor-temperature damping and heating limits are standard, and they suit a slab.**
  - Daikin averages outdoor temperature over 0/12/24/48/72 h, default none [27].
  - Viessmann computes the curve from a heavily low-pass-filtered outdoor temperature [24]. Its heating-limit pump logic uses a fixed ±1 K band on the damped value [25].
  - Panasonic stops heating at the setting + 3 K and resumes at the setting + 1 K [31].
  - The Vaillant switch-off default is 16 °C for heat pumps [12].
  - Daikin also offers a +2…+4 K LWT bump around 0 °C to offset snow and ice losses [27].
- **Hot water is handled with explicit timers so it does not starve or chop space heating.** Daikin: max DHW run 5–95 min (default 30), anti-recycle 0–10 h (default 0.5 h, never below 0.5 h) [27]. Samsung FSV 3025: max DHW time 5–95 min, default 30 [39]. NIBE economy DHW: start 42 °C, stop 48 °C [4]. On Panasonic, the target drop after switching from hot water to heating trips the 2 K overshoot stop (owners) [33].
- **PV and smart-grid functions are just setpoint raises.** On an SG signal, Viessmann One Base raises the room, DHW or buffer setpoint by a set number of kelvin [25]. NIBE has had to fix "short operation times" caused by PV-driven demand shifting [5]. A naive PV boost on top of a hysteresis controller can cause short cycles.
- **What the Gree offers natively:**
  - Control state T-water out (default) or T-room. T-room needs the remote sensor and uses ΔT-Room temp 1–5 K, default 2 K [42][43].
  - ΔT-Heat (the restart hysteresis): 2–10 K. The printed factory default is 10 K, so the house's 4 K was presumably set by an installer or the owner [42].
  - An optional power limit 0–10 kW (default 3.0 kW) or current limit 0–50 A (default 16 A) [43].
  - A "Weather depend" mode with its own curve [42].
  - These match the Gree-specific note 08-gree-versati.md.

## Detailed findings

### 1. The common control architecture

Every manual read here describes the same layers. Only the names differ.

| Layer | NIBE | Vaillant | Daikin | Panasonic | Mitsubishi | Samsung | LG | Gree |
|---|---|---|---|---|---|---|---|---|
| Flow target | Curve number + offset → "calculated supply" S1 [1][6] | Heat curve + room setpoint [12][14] | 2-point or slope-offset curve; or fixed [27][28] | 2-point compensation curve, or direct [32] | Compensation curve, flow-temp mode, or room auto-adaptation [36] | Water law (2-point) [39] | Seasonal auto curve [41] | Fixed WOT-Heat or "Weather depend" [42] |
| Room correction | Factor 0–6 (default 2) [1]; ML "Smart Room Comfort" (2025+) [5] | Room temp mod. Inactive/Active/Expanded [13] | Modulated LWT ±0–10 K (default 3) [27] | Room sensor / thermostat options [32] | Auto Adaptation (room model) [35] | FSV 2091/2093 thermostat modes [40] | Room hysteresis setting (p.223, not read) | T-room control, ΔT-Room 1–5 K [42] |
| On/off decision | Degree-minute integral [1][2] | Energy integral + 7 K hysteresis [11] | Overshoot 1–4 K, restart below target [27] | +2 K for 3 min off; restart −3 K vs inlet [31] | Thermo diff +5/−5 K default [36] | Water-law or room-stat stop [40] | +2/−2 K [41] | ΔT-Heat restart band; stop at min freq when overshooting [42][43] |
| Speed control | Driven by DM, "max diff compressor" cap, soft start [3][5][9] | Modulation 25–100 % (owners) [19][21] | Not documented; reduces pump flow first, contested [30] | Microcomputer sets frequency from internal setpoint vs outlet [31] | Not documented | Ramps to min Hz near target [40] | Not read | Frequency ∝ LWT error [42][43] |

Gree's description is the most explicit about speed. In leaving-water mode, frequency goes up as the leaving-water error grows and down as it shrinks. A normal stop first ramps to minimum frequency. If the compressor is at minimum and the temperature difference is still large, the unit shuts down [42][43]. In "T-room" mode the same logic runs on room temperature error [42]. Panasonic's service manual says the same thing. The indoor microcomputer compares the internal water setpoint with the outlet temperature and orders a compressor frequency [31].

### 2. Weather-compensation curves: parameterisation and defaults

| Brand | Form | Range / factory defaults | Notes |
|---|---|---|---|
| Vaillant sensoCOMFORT VRC 720 | Single "heat curve" number, shifted with room setpoint | 0.1–4.0; default **0.60 for heat pump / mixed circuit** (1.20 for a boiler) [12][14]. Min target flow default 15 °C. Max 55 °C for a heat pump (90 °C boiler). OT switch-off threshold 16 °C for a heat pump (21 °C boiler) [12] | Manual example: curve 0.4 gives 40 °C flow at −15 °C with 20 °C room [14]. Forum fit Tflow = Tset + 2.55·(HC·(Tset − Tout))^0.78 matched eBUS values within ~0.07 K [16]. Curves converge at Tout = Tset, so a room-setpoint change mostly moves the cold end [16] |
| Viessmann Vitotronic / One Base | Slope (Neigung) and level (Niveau, a vertical shift) | Community formula VT = RT + Ni − Ne·D·(1.4347 + 0.021·D + 247.9·10⁻⁶·D²), with D = AT_damped − RT. AT_damped is a heavily low-pass-filtered outdoor temperature [24]. Check: Ne 1.4, Ni 0, RT 17 °C, AT −5 °C → 50.65 °C, matching the document's worked example [calc][24] | At slope 1, a 1 K room-setpoint change moves the flow ≈ 2 K [24]. One Base adds min/max flow limits per circuit (1192.0/.1) and a room-temperature-led mode that works from room setpoint − actual [25] |
| NIBE (F/S-series) | Curve number + offset; "own curve"; point offset | Curve 0–15, F1145 default 9. Min flow line 5–70 °C, default 20 °C. External adjustment ±10 steps [1]. +2 offset steps ≈ +5 K supply at all outdoor temps (S1155) [3] | Max and min limits flatten the curve [3]. The S-series DOT settings (design outdoor temp −40…+20 °C, ΔT at DOT 0–25 K, power at DOT 1–100 kW) feed the pump and compressor sizing logic [3] |
| Daikin Altherma | 2-point curve or slope-offset curve | [1-00] low ambient −40…+5 °C (default −10). [1-01] high ambient 10–25 °C (default 15). [1-02] LWT at low ambient (default 35 °C). [1-03] LWT at high ambient (default 25 °C). LWT range [9-01] min 15–37 (default 25), [9-00] max 37–55 (default 55) [27]. User shift ±10 K [28] | Outdoor average timer [1-0A]: none (default) / 12 / 24 / 48 / 72 h [27]. "Compensation around 0 °C" [D-03] adds +2 or +4 K over −2…+2 °C or −4…+4 °C [27]. Radiator emitter type fixes ΔT at 8 K; underfloor uses variable ΔT, max 55 °C [28] |
| Samsung EHS | 2-point "water law" | FSV 2011 outdoor low −20…+5 (default −10). 2012 outdoor high 10…20 (default 15). 2021 water at low 17–65 (default 40). 2022 water at high 17–65 (default 25). A UK distributor pre-sets 2 °C/15 °C and 45/35 °C [39] | ±5 K user offset in thermostat modes [40] |
| Panasonic Aquarea | 2-point compensation curve | Zone target high/low and outside high/low temperatures. Shift −5…+5. Heating-off outdoor 5–35 °C [32] | Owners start from 35 °C @ −20 °C and 23 °C @ +15 °C for well-insulated UFH [34] |
| Mitsubishi Ecodan | Compensation curve or room auto-adaptation | Flow range min 25–45 °C (default 30), max default 50 °C. Heat-pump operation is blocked below a fixed 20 °C flow [36] | Example owner curve 41 °C @ −4 °C / 30 °C @ +7 °C [38] |
| Gree Versati | "Weather depend" on/off with its own curve temperatures | Endpoints and ranges are in the Gree note 08. In the service manual, the weather-dependent target is viewable and room setpoint changes take effect only after the mode is switched off [42] | |

German installer guidance for heat pumps: underfloor slope 0.2–0.5, radiators 0.8–1.6. Adjust the level in 1 K steps in the 5–15 °C transition period, and wait ≥ 48 h between changes. Each 1 K lower flow saves roughly 2.5–3 % of electricity (German heat pump association BWP rule of thumb) [44]. Mitsubishi's own figure is 2 % COP per 1 K [35].

Curve values for 22 °C room at −20 / −10 / 0 / +10 °C outdoor [calc]:

| Curve | −20 °C | −10 °C | 0 °C | +10 °C |
|---|---|---|---|---|
| Vaillant HC 0.15 (fit [16]) | 32.7 | 30.7 | 28.5 | 26.0 |
| Vaillant HC 0.20 | 35.4 | 32.8 | 30.1 | 27.0 |
| Vaillant HC 0.60 (factory) | 53.6 | 47.6 | 41.1 | 33.9 |
| Viessmann Ne 0.3, Ni 0 (formula [24]) | 34.5 | 31.8 | 29.2 | 26.4 |
| Viessmann Ne 0.4 | 38.6 | 35.0 | 31.6 | 27.8 |
| Daikin factory 2-point | 35.0 | 35.0 | 31.0 | 27.0 |
| Samsung factory WL1 | 40.0 | 40.0 | 34.0 | 28.0 |

The factory curves give 27–34 °C at +10 °C and 31–41 °C at 0 °C. That is the same band as the setpoints this house sees (31–36 °C). Slab-appropriate curves sit 3–8 K lower.

### 3. Room influence and room compensation

- **Daikin.** Room-thermostat control with "Modulated LWT" [8-05]. The unit raises or lowers the curve's LWT by up to [8-06] (0–10 K, default 3 K) from the room error. Daikin claims this gives steadier room temperature, fewer on/off cycles and lower water temperatures [27]. The weather curve must sit at least [8-06] above the minimum LWT that holds the room. Emitter type [9-0B] quick/slow tells the controller the system's reaction time and limits the maximum modulation. "Slow" is the example for large water volume and floor loops [27]. Target ΔT [9-09] is 3–10 K, default 5 K [27]. Owners report the room-thermostat (Madoka) band as start at −0.5 K and stop at +1.5 K, and LWT stepped down after the room has been above target for ~20 min [29]. These are forum figures, not documentation.
- **Vaillant.** "Room temp. mod." has three modes [13]:
  - Inactive.
  - Active: continuous flow-target adjustment from measured room temperature.
  - Expanded: as Active, plus zone switch-off when room + 2/16 K > setpoint and switch-on when room < setpoint − 3/16 K. Heat pump only.
  - Owners on firmware 351.06.07 report that in Expanded the unit stops at +0.125 K and restarts at −0.1875 K regardless of the energy integral. One saw cycling return at 4–5 °C outdoor [18].
  - Active mode reacts to solar gain on the sensor [19].
- **NIBE.** Room sensor "factor system" 0.0–6.0, default 2.0. A higher value moves the curve offset more for a given room error [1]. The SMO S40 only offers on/off room control. One owner stabilised the system by disabling the room sensor [7].
- **Viessmann One Base.** Parameter 933.6 switches room influence on/off (needs a room sensor and weather-compensated mode). 933.7 sets its strength [25].
- **Samsung.** FSV 2091/2092 (third-party thermostat) and 2093 (Samsung thermostat), values 0–4, as transcribed by owners [40]:
  - 1: water law sets the target, and after reaching it the compressor keeps running at minimum Hz until the room stat is satisfied. LWT can then drift up.
  - 2–4: stop at the water-law target or room stat, whichever comes first, with pump off, on or cycling respectively.
  - 0: owners disagree whether water law stays active [40].
- **Panasonic.** Zone sensor options: water, external thermostat, internal thermostat, thermistor [32]. Owners report that switching from internal thermostat to water control cut room variation below 1 °C. They recommend pure weather compensation without room stats for UFH [34].
- **Gree.** Ctrl state = T-room requires the remote room sensor. The compressor then modulates on room error with ΔT-Room temp 1–5 K, default 2 K [42][43].

### 4. Self-adapting and model-based control

- **Mitsubishi Auto Adaptation** (official description [35]):
  - Measures room and outdoor temperature and estimates the room's required heating capacity.
  - Sets flow temperature from that capacity, not from a fixed curve.
  - Estimates future room temperature from recent points and compares it with the target. It then lowers, holds or raises the flow temperature, which avoids needless flow swings.
  - Motivation: Mitsubishi says 1 K lower flow is worth ~2 % COP [35].
  - On the FTC, room auto-adaptation is the factory space-heating mode. Settings are flow range limits, a "Normal/Fast" mode and an interval (default 10 min). Thermo-diff limits apply on top [36].
  - Owner experience: SCOP 3.4 → 3.6 after adding a room controller and running Auto Adapt [37]. Another owner on an oversized 11.2 kW with UFH plus radiators set a 60-min interval and thermo-diff +3/−9 K. He got a single run lasting ~20 h in mild weather, but recorded no COP [38]. A third owner, quoted in [37], says Auto Adapt did not at first run longer at lower flow temperatures, but its slow ramp-up helped COP. Over time it matched full weather compensation with less cycling [37]. Search snippets of other owner threads (not opened) mention a learning period of several days and overshoot. Treat that as unverified.
- **NIBE Smart Room Comfort** (S-series 4.0.10, 2025-03-03): an "AI" (machine-learning) room controller that is enabled automatically when a room sensor controls heating. It removes the use of heat curve and offset in normal conditions. Firmware 4.9.4 (2026-03-12) added logic to reduce short operation times in heating when "Auto degree minute" mode is selected. 4.14.6 (2026-10-19) adds automatic DM adjustment against short cycles in cooling [5]. NIBE does not publish the algorithms.
- **Vaillant adaptive heat curve.** Retailer listings advertise an "adaptive heating curve" on the VRC 720 (search results only). I could not find its description in the manual pages I read, so how it adapts is unverified.

### 5. Start/stop logic, brand by brand

**NIBE degree minutes (DM)** [1][2][3][4][5][6][7]:
- Every minute, DM changes by (measured supply BT25 − calculated supply S1). Below target lowers DM, above target raises it. The owner's example: 3 K low for 2 min gives −6 [6].
- Compressor starts at "start compressor": F1145 default −60, range −1000…−30 [1]. S1256PC range −1000…−30 [2]. It stops when DM returns to 0 [6][7].
- Additional heat starts at −400 on the F-series (range −2000…−30) [1]. The S-series uses a relative offset 100–2000 DM below the compressor start, and the step difference between compressors is 10–2000 DM [2]. Firmware 2.3.3 (2021-03-10) raised the default step difference from 60 to 200 DM [5].
- The DM value is clamped at −3000…+3000 (F1145) and −3000…+100 (S1256PC) [1][2].
- Backstop "max diff compressor": 1–25 K, default 10 K [4]. If supply exceeds the calculated value by this much, DM is set to +1 (S1155) or +2 (SMO 40) and the compressor stops when only heating is demanded [3][4]. "Max diff addition" is 1–24 K (SMO 40 default 7 K) and can never exceed the compressor value [3][4].
- NIBE's own warning: a higher (less negative) start value gives more starts and more wear. A too-low value gives uneven indoor temperature [1][2].
- Practice [7]:
  - If the charge pump runs "intermittent", BT25 reads stale water while the compressor is off and DM behaves badly. "Auto" with 10–30 % idle speed fixes it.
  - After a hot-water run DM can sit near −500, which produces a hot catch-up at 40–45 °C against a 35 °C target.

**Danfoss / Thermia-type "integral"** [10]:
- Integral = area of (supply − calculated supply) over time, in degree minutes.
- Compressor at A1 (default −60). Auxiliary heater at A1+A2 (A2 default −600) if the integral keeps falling.
- When |supply − calculated| ≥ the HYSTERESIS setting, the integral is forced to A1 (demand appears fast) or to 0 (surplus appears fast).
- Integration pauses during heat stop and resumes 2 min after a hot-water run.

**Vaillant energy integral** [11][17][18][19][20][21][22]:
- Official: the integral of (actual − target flow) is summed every minute. The heat pump starts when the set heat deficit is reached ("Compr.start heat. from": default −60 °min, range −999…+9 on the VWZ AI interface). It switches off when the heat supplied equals the deficit [11]. A Vaillant hydraulic-station manual (VWZ MEH, aroTHERM split) lists a narrower −100…−30 °min range. I saw that only as a search snippet and did not open the PDF.
- Compressor hysteresis, heating: default 7 K, range 0–15 K. Cooling: default 5 K. It is the second switch-off criterion when flow exceeds target by the hysteresis [11].
- The interface shows a live "compressor anti-cycling time" (minutes). This implies an internal minimum-off timer, but it is not settable. "Max. anti-cycl. time" (0–9 h, default 5 h) is the utility-blocking limit, not a short-cycle timer [11].
- Owner observations:
  - The pump pre-run starts at −60 and the compressor follows. With −100 set, a start was seen at −66 °min because of the flow ramp-up [19].
  - Firmware 0351.06.06/07 counted the integral double and ignored the setting. 0351.09.02 honours −100 [19][21]. On 06.07, owners measured 1.41–1.9 compressor cycles per operating hour over 594–6927 h [18].
  - With integral −200 and hysteresis raised from 7 to 8 K, one brine unit made ~20 cycles/day in the shoulder season against 10–14 in winter. Raising the hysteresis lets the integral recover less per run, so the next start comes sooner [22].
  - Owners report a floor of about −180 °min [21] (unverified).

**Daikin** [27][29][30]:
- LWT overshoot [9-04], 1–4 K, default 1 K. The compressor stops when LWT exceeds target by this amount and restarts as soon as LWT drops below target [27].
- On 9–16 kW monoblocs, owners report 4 K overshoot and a stop at about target + 0.5 + 4 K. Hybrids are said to be fixed at 1 K [29].
- An 8 kW Altherma 3 cycles about hourly at sustained ≥ 14 °C outdoor. The 9–16 kW units draw ~900 W minimum electrical [29][30].
- Owners dispute how the unit holds ΔT. One view is that it reduces flow first and then lets LWT rise up to the overshoot. The other is that the compressor targets LWT while the pump sets ΔT [30].

**Panasonic** (Aquarea F generation service manual, 2013) [31]:
- Compressor off when outlet − internal setpoint > 2 °C for 3 min continuously.
- Restart only after 3 min, and only when outlet < (inlet temperature recorded at thermo-off) − 3 °C.
- Outdoor thermo-off: heating and pump stop when outdoor > setting + 3 °C (setting 5–35 °C) and resume when outdoor < setting + 1 °C.
- Owners on newer units describe the same 2 K / 3 min stop. They see it fire on every hot-water → heating switch, because the target drops below the hot outlet. Their workaround is a HeishaMon rule that sets the target to max(floor(outlet) − 1, curve target) every minute until the loop has cooled [33].

**Mitsubishi Ecodan FTC** [36]:
- "Heat pump thermo diff adjust": on (default). Lower limit −9…−1 K (default −5). Upper limit +3…+5 K (default +5).
- In practice this is a ±5 K hysteresis around the flow target. Owners widen it to +3/−9 K to stretch off-periods [38].

**LG Therma V** [41]: "Hysteresis heating water" Temp On default −2 K (range 0…−9), Temp Off default +2 K (0…+4). The page does not say what these are relative to; presumably the target LWT.

**Samsung EHS**: see the FSV 2091/2093 modes in §3 [40]. Mode 1 is the only one, among the brands read, that documents "keep running at minimum speed instead of stopping" as an explicit control choice.

**Gree Versati** [42][43] (detail in note 08):
- Frequency is proportional to the LWT error.
- It stops when at minimum frequency and still above target.
- Restart is governed by ΔT-Heat (range 2–10 K).
- "Heat run time" 1–10 min (defaults 3/5 min depending on 2-way valve) appears in the commissioning table. Its meaning is unclear from the scrambled text [42][43].

### 6. Compressor speed control and start-up behaviour

- **NIBE soft start:** since 2.3.3 (2021), an outdoor-air heat pump in a single system runs at minimum speed after start until DM has dropped or a time has passed. Ground-source units already worked this way [5].
- **NIBE frequency floors (owners):** F2120 minimum ~25 Hz at ≥ +8 °C outdoor and ~35 Hz below, against ~20 Hz for the S-series. At 10–16 °C outdoor one owner still saw 50–60 Hz, because supply ran above target and DM hit 0 quickly. Users say NIBE does not document how frequency is chosen [9].
- **Vaillant (owners):** after start, a 7 kW unit runs near maximum compressor speed for several minutes. Owners use quiet mode to cap it. An oversized 10 kW unit "never goes above minimum" except for the first minutes of a cycle [20]. Owners have proposed walking the target up gradually to stay at minimum speed (untested on Vaillant). A Mitsubishi owner reported it worked "kinda okay" [20].
- **Samsung:** in thermostat mode 1 the compressor ramps down to minimum Hz once the water-law target is reached. The pump runs a PWM loop on ΔT using #4052 (target ΔT) and #4053 (gain) [40].
- **Gree:** frequency follows the LWT error; there are also current/power limits [42][43].
- **Viessmann turndown (A7/W35, EN 14511):**

| Model | Modulation range (kW) |
|---|---|
| 251.A04 | 2.1–4.0 |
| 251.A06 | 2.1–6.0 |
| 251.A08 | 2.1–8.0 |
| 251.A10 | 2.6–12.0 |

  At A2/W35 the same sizes modulate 1.8–4.5 / 1.8–6.0 / 1.8–6.8 / 2.2–11.0 kW [26].

### 7. Mild weather, minimum run time and heating limits

- **No brand read here exposes a "minimum compressor run time" for space heating.** Run length comes from the integral thresholds or hysteresis bands. Fixed internal lockouts follow a stop: Panasonic waits 3 min before restart [31]. Vaillant shows an internal anti-cycling counter [11]. Gree has a 3-min restart lockout (note 08). The Daikin and Samsung timers govern hot water balancing, not space heating [27][39].
- **Viessmann's design answer is hydraulic plus sizing** [26]:
  - The "Hydro AutoControl" integrated buffer and 4/3-way valve keep ≥ 300 l/h through the outdoor unit at all times, while circuit flow may drop below 300 l/h.
  - Defrost needs > 1000 l/h, and the heating circuits get no heat during defrost.
  - An external parallel buffer "considerably" lengthens run time and avoids cycling.
  - The planning text lists the lower modulation limit as a sizing criterion against transition-season cycling.
- **Heating limits ("summer switch"):**
  - Vaillant OT switch-off: 16 °C default for heat pumps [12].
  - Viessmann: circuit pump off when outdoor is 1 K above the heating limit, on when the damped outdoor temperature is 1 K below. The ±1 K is fixed. An economy function turns the pump off when outdoor > room setpoint + an adjustable hysteresis [25].
  - Daikin [4-02]: space-heating OFF when the *averaged* outdoor temperature exceeds 14–35 °C (default 25 °C for the 04/08 class) [27].
  - Panasonic: +3 K off, +1 K resume around the 5–35 °C setting [31].
- **Outdoor damping:** Daikin [1-0A] offers 12/24/48/72 h averaging (default none) [27]. Viessmann uses a strongly filtered outdoor temperature in the curve [24].
- **Circulation during compressor-off:** the NIBE "auto" pump mode idles at 10–30 % so the supply sensor sees moving water. "Intermittent" mode causes stale readings and erratic DM [6][7].

### 8. Hot water versus space heating

- **Daikin "balancing"** [27][28]:
  - Max DHW run [8-01]: 5–95 min (default 30).
  - Anti-recycle [8-02]: minimum time between two DHW cycles, 0–10 h (default 0.5 h; 0.5 h enforced even at 0).
  - Extra run time [8-04]: 0–95 min (default 95) at low outdoor temperature.
  - Also a space-heating priority temperature, a minimum running timer and an additional timer [28].
- **Samsung:** FSV 3025 max DHW time 5–95 min (default 30; distributor values 50–90 by tank size). FSV 3032 booster delay 20–95 min. Disinfection target 40–70 °C, default 70 °C [39].
- **NIBE hot-water start/stop** [4]:

| Mode | Start (default) | Stop (default) |
|---|---|---|
| Economy | 42 °C | 48 °C |
| Normal | 46 °C | 50 °C |
| Luxury | 49 °C | 53 °C |

  Periodic increase stop 55 °C [4].
- **Vaillant:** cylinder-charging hysteresis 3–20 K. The installer manual advises a 50–55 °C cylinder setpoint for efficient compressor-only DHW [11].
- **Panasonic:** a hot-water → heating switch typically trips the 2 K overshoot stop. Owners ramp the heating target down by rule to avoid it [33].

### 9. PV, smart grid, price signals

- **Viessmann One Base:** 2543.0/2543.2/2543.3 raise the room, DHW or buffer setpoint by a set value while the SG contacts are switched, with DHW given priority [25]. In practice this is a "store into mass" command.
- **NIBE:** Smart Price Adaption, Smart Energy Source and PV integrations. NIBE has had to fix "short operation times" with PV demand shifting and Smart Price Adaption on the SMO S40 [5]. Raising a setpoint briefly on top of a hysteresis controller causes short cycles unless it is coordinated with the start/stop logic.

### 10. What the settings do in practice (field and forum evidence)

| Observation | Unit / conditions | Source |
|---|---|---|
| 1.41–1.9 compressor cycles per operating hour; owners blamed doubled integral counting | Vaillant aroTHERM plus, fw 351.06.07, 594–6927 h of operation | [18] |
| Integral −100 °min gave "fewer and longer cycles" with larger room swings. Not a halving, because flow temperature drops within each cycle | Vaillant, fw 0351.09.02 | [19] |
| COP "barely affected" by −60 vs −100 °min (opinion); −30 felt worse | Vaillant, owner with oversized 10 kW | [20] |
| 16 → 6 cycles overnight after lengthening the integral | Vaillant, second-hand from a German forum | [19] |
| Off-times > 1 h; integral at −146 without restarting | Vaillant 7 kW, no buffer, mild weather | [20] |
| ~20 cycles/day in shoulder season vs 10–14 in winter; shutdown at 35.5 °C flow vs 25.5 °C target | Vaillant flexoTHERM brine, integral −200, hysteresis 7→8 K | [22] |
| 2–3 cycles/h, 15–20 min runs at high frequency | NIBE F2040-16 + SMO 20 | [8] |
| ~1 h on / 1 h off; start threshold moved to −240 DM; DM ≈ −500 after hot water caused 40–45 °C catch-up flow | NIBE F2040 12/16 kW + SMO S40 | [7] |
| Minimum electrical draw ~900 W (9–16 kW); hourly cycling ≥ 14 °C (8 kW) | Daikin Altherma 3 monobloc | [29][30] |
| Rolling SCOP 3.4 → 3.6 after Auto Adapt (other changes too) | Mitsubishi Ecodan | [37] |
| Cycling begins when load < minimum modulation, typically ~10–13 °C outdoor for a well-sized unit; "little experimental evidence" that cycling costs efficiency (forum moderator opinion) | General, NIBE thread | [8] |

### 11. How degree minutes translate to energy in a slab house [calc]

- **One degree minute** at the loop flow ṁ is worth ṁ·c_p·60 s. That is 0.017 / 0.023 / 0.030 kWh at 15 / 20 / 26 l/min. So the default −60 DM ≈ 1.0–1.8 kWh, about 0.15–0.27 K of slab temperature at 6.6 kWh/K.
- **While the compressor is off,** DM accrues at (target flow − circulating loop temperature) per minute, not at the house's true heat loss. With the loop 2 / 3 / 5 K below target, −60 is reached in 30 / 20 / 12 min.
- **The house drains the slab much more slowly.** At 1.7 kW load (+10 °C), a 0.5 K slab drift takes ~1.9 h and a 1 K drift ~3.9 h.
- **Thresholds that would give a 0.5–1 K slab swing** are therefore about −350 to −700 °C·min, 6–12× the factory value, when the loop sits ~3 K below target. NIBE allows down to −1000 [1]. Vaillant's VWZ AI allows −999 [11]. A Vaillant hydraulic-station manual seen only as a search snippet caps it at −100.
- **Loop ΔT at minimum output** P_min = 3.75 kW is 3.6 / 2.7 / 2.1 K at 15 / 20 / 26 l/min. At the unit's 9 kW maximum it is 8.6 / 6.5 / 5.0 K. So at minimum output the outlet sits only ~2–3.5 K above the return. Any setpoint more than ~3 K above the return forces the inverter above minimum speed.

## What this means for controlling this house

### A. The physics the controller has to respect [calc]

| Outdoor (24 h mean) | Load at H = 0.14 / 0.17 / 0.20 kW/K | Duty at P_min 3.75 kW (H = 0.14) | 1 K slab swing: on h / off h / starts per day | 0.5 K swing: starts per day |
|---|---|---|---|---|
| +15 °C | 1.0 / 1.2 / 1.4 kW | 0.26 | 2.4 / 6.7 / 2.6 | 5.3 |
| +10 °C | 1.7 / 2.0 / 2.4 kW | 0.45 | 3.2 / 3.9 / 3.4 | 6.7 |
| +5 °C | 2.4 / 2.9 / 3.4 kW | 0.63 | 4.8 / 2.8 / 3.2 | 6.3 |
| +2 °C | 2.8 / 3.4 / 4.0 kW | 0.75 | 6.9 / 2.4 / 2.6 | 5.2 |
| 0 °C | 3.1 / 3.7 / 4.4 kW | 0.82 | 9.9 / 2.1 / 2.0 | 4.0 |
| −5 °C and colder | ≥ 3.8 kW | ≥ 1 | continuous | continuous |

- The storage time constant C/H is 33–47 h. Heat-balance decisions belong on a scale of hours to a day, not 30-min reactions. The floor-surface response is faster (hours; see note 05).
- If the brief's 1.7 kW at +10 °C is right (H ≈ 0.14), the unit must cycle at every outdoor temperature above about −5 °C. That covers most heating-season hours.
- A well-designed cycle in this house lasts hours, about 2–7 starts/day, not 1–3 per hour. Manufacturer defaults, tuned for radiators, would produce the latter.

### B. Concrete control rules (with confidence)

1. **Plan cycles; do not fight them** (high confidence; physics plus Viessmann's design guidance [26]).
   - Above the balance point, run the compressor in blocks at or near minimum output.
   - Choose the block size so the slab swings ~0.5–1 K. That gives ~2–7 starts/day and ≥ 1.5–3 h per run at +5…+10 °C.
   - Below the balance point, do not stop the compressor deliberately. Run continuously at the lowest speed that covers the load.
2. **Decide start/stop on an energy budget or a slab-scaled integral, not on the 30-min setpoint tick** (medium confidence). Two equivalent options:
   - *Energy budget.* Deficit += (estimated load − delivered heat)·dt. Start when the deficit reaches ≈ +2.5–3.5 kWh (≈ 0.4–0.5 K slab). Stop at ≈ −2.5–3.5 kWh. This is the NIBE/Vaillant idea counted in kWh.
   - *DM integral against the curve.* Use start thresholds of about −300…−700 °C·min instead of −60, with continuous circulation so the measured supply temperature is meaningful (§11; [6][7]). The −60 defaults [1][10][11] would give ~20-min off-times here.
3. **Separate the start trigger from the running target. This is the "glide".** It is the most direct fix for the hot, high-power catch-up runs (medium confidence; the Gree mechanism is documented [42][43], NIBE does the same internally [5], and owners ramp targets this way [20][33]).
   - To start, briefly write setpoint ≈ outlet + ΔT-Heat + 0.5 K.
   - Once the compressor is confirmed running (frequency > 0 or input power above standby), write a running target of max(curve value, return + ~2–3.5 K). That is the loop ΔT at P_min from §11.
   - Then raise it no faster than ~0.5 K per 10–15 min, and only as the return warms.
   - Expected result: input near minimum, roughly 0.8–1.2 kW electric at mild outdoor temperatures [inference], instead of ~3 kW. Check it with power and frequency logs.
4. **End blocks deliberately and park the unit** (medium confidence; needs a Gree test).
   - Stop by writing a target below the outlet. Gree stops when it is at minimum frequency and above target [42].
   - Then hold a *park* setpoint low enough (outlet − ΔT-Heat − 1 K, but above any anti-freeze or minimum limit) that the firmware cannot restart on its own. Only the supervisor starts the next block.
   - This replaces the firmware's hysteresis restart, the source of the unplanned on/offs, with a planned decision.
5. **Choose ΔT-Heat to match the strategy; avoid 4 K combined with periodic rewrites** (medium confidence).
   - With a supervisor-driven start (rules 3–4), set ΔT-Heat to its 2 K minimum [42]. The start "kick" then needs only ~2 K of error, so the first minutes are gentler.
   - If the firmware is left to cycle on its own (the baseline candidate C below), use 8–10 K. That is the same lever as Mitsubishi's −9 K thermo-diff [36][38] and Vaillant's −100 °min [19][20]: longer off-periods, which suit the slab.
   - The current 4 K with 30-min setpoint rewrites gives large start steps *and* frequent self-restarts.
6. **Make the curve low and slow** (medium confidence; curve shapes from [16][24][27][44]).
   - Start around Vaillant-equivalent HC 0.15–0.20 or Viessmann slope ≈ 0.3. That gives ≈ 26–27 °C at +10 °C, 28.5–30 °C at 0 °C and 33–35 °C at −20 °C.
   - Feed it a 24–48 h mean outdoor temperature, as Daikin's [1-0A] and Viessmann's damped temperature do [24][27].
   - The curve then only governs the continuous-run regime and caps the target. In the cycling regime, the energy budget decides *how much* heat and the loop decides *at what temperature* (rule 3).
   - Fit the slope from the house's own data: the steady-state flow that held 22 °C on calm, overcast days.
7. **Room feedback should be integral-only, slow and bounded** (medium confidence; Daikin's ±3 K default and "slow emitter" [27], NIBE factor 2 [1], Mitsubishi prediction [35]).
   - Trim the energy budget or curve offset once or twice a day from the 24 h mean room error. Use a deadband of ±0.1–0.2 K and a step of ~0.1–0.3 K equivalent per 0.1 K error.
   - Cap the total trim at about ±3 K of flow.
   - Never boost flow from the instantaneous room error. Do not use on/off room switching like Vaillant "Expanded" [13][18] or Gree "T-room" [42]; with a slab they cause overshoot and cycling.
8. **Limit catch-up** (medium-high confidence).
   - Flow target ≤ curve + 2–3 K.
   - If the Gree "C/P limit = power limit" is reachable, cap input power at ~1.2–1.8 kW above about −3 °C outdoor. Gree's own default is 3.0 kW [43]; see note 08 for registers.
   - Spread any recovery over 6–12 h. At ~1 kW net surplus, a 0.5 K slab deficit (3.3 kWh) takes ~3.5 h to repay at minimum output [calc]. A faster boost buys little comfort and costs COP. Each 1 K of flow is ~2–3 % [35][44].
9. **Put hot-water runs on a timetable that protects the heating blocks** (medium confidence; Daikin/Samsung timers [27][39], NIBE economy band [4], Panasonic DHW→heating stop [33]).
   - One or two fixed windows, preferably the PV peak. Use a wide band, e.g. start 42 °C / stop 48 °C like NIBE Economy.
   - Max run ~45–60 min and an anti-recycle of ≥ 4–6 h.
   - Place hot water at the *end* of a heating block or in an off-period.
   - After hot water, keep heating parked until the loop has cooled to about return + 1 K. This avoids the "hot loop → immediate overshoot stop → restart" pattern seen on Panasonic [33].
   - Run legionella cycles on the immersion heater at the PV peak.
10. **Use PV by moving blocks, not by bumping setpoints** (medium confidence; [5][25]).
    - Schedule the next heating block into the surplus window and allow +0.5–1.0 K of slab over-charge. That stores ≈ 3.3–6.6 kWh of heat, roughly 1–2 kWh of electricity at COP 3.5–4.5 [calc].
    - Raising a setpoint on top of the firmware's hysteresis produces the short runs NIBE had to patch [5].
11. **Circulate during off-periods only if the sensor needs it** (low-medium confidence; NIBE evidence [6][7]).
    - If the outdoor unit's water stagnates and the outlet sensor drifts, the firmware may restart on a false reading, or the supervisor may misjudge the slab.
    - A low idle pump speed fixes this at a cost of pump watts. Measure both.
12. **Write over Modbus only on change, with spacing** (inference, low-medium confidence). Gree commissioning values survive power loss [42][43], so they are stored in non-volatile memory. Write-endurance limits are unknown. Avoid per-minute rewrites of persistent registers; check whether the flow setpoint register is volatile.

### C. Candidate control logics worth A/B testing

These are deliberately different and map to manufacturer strategies. Compare them on similar-weather days by alternating days or weeks. Metrics:
- starts/day and median run length;
- mean outlet temperature while the compressor runs;
- electricity per heating degree-day, with hot water separated;
- 24 h room mean and range;
- number of hot-water interruptions of heating blocks.

- **A. Slab-scaled degree-minute controller (NIBE/Vaillant style).** Curve target on the 24 h mean outdoor temperature. DM integrated every minute against measured supply with continuous circulation. Start at about −400 °C·min, stop at 0, then park. Glide on start. Backstop: stop when supply > target + 5 K. Tune the start threshold toward 4–6 starts/day at +5 °C.
- **B. Energy-budget block scheduler (Mitsubishi/NIBE model-based style).** Daily heat demand from H·(22 − T_out forecast) − gains, corrected by the room-error integral. Delivered as N blocks at minimum output, placed in PV or cheap hours. The flow target in each block is set by the return + ΔT_min rule. No per-block reaction to room temperature.
- **C. Firmware-only baseline ("let the Gree cycle").** Fixed low curve in Gree "Weather depend" or a once-daily HA setpoint. ΔT-Heat 8–10 K, power cap on, no intra-day writes. Shows how much of the problem comes from today's 30-min writes.
- **D. Continuous minimum-modulation tracker for the cold regime (Samsung mode-1 style).** Below the balance point, keep the compressor running. Hold the target at return + small margin so speed stays near minimum. Stop only on a slab-energy surplus. Use it with A or B as the cold-weather branch.

### D. What to avoid (high confidence unless noted)

- Setpoint steps of ≥ 4 K above outlet while the compressor is running. The Gree speeds up in proportion [42].
- Radiator-tuned thresholds: −60 DM/°min, ±2 K bands with a fixed setpoint, or Vaillant/Samsung/Daikin factory curves (31–41 °C at 0 °C).
- Fast room-based on/off or proportional boosts with a 33–47 h storage time constant.
- Hot water whenever the tank drops a few kelvin, and hot water in the middle of a planned heating block.
- Night setbacks that force morning catch-ups (see note 05 on setback penalties).

### E. Confidence summary

- **High:** the documented manufacturer parameters and defaults in §§2–8.
- **Medium:**
  - That slab-scaled thresholds and the glide will cut starts and mean flow temperature. This follows from documented mechanisms and arithmetic, but has not been measured in this house.
  - The suggested curve range.
- **Low-medium:**
  - Exact Gree behaviour of the park, glide and power-limit ideas. The Gree manuals read are partly scrambled, so the specifics need a logged test.
  - Any efficiency gain in percent. Forum owners disagree on how much cycling itself costs [8][20].

## Contradictions and open questions

1. **Does cycling itself cost efficiency?** Makers treat it as a wear and comfort issue: NIBE warns about compressor wear from more starts [1][2], and Viessmann designs against it [26]. An owner moderator says there is "little experimental evidence" of an efficiency penalty [8]. A Vaillant power user found COP "barely affected" by −60 vs −100 °min [20]. These are different metrics, and none is a controlled measurement. The bigger lever is probably flow temperature (2–3 %/K [35][44]) and avoiding high-speed starts.
2. **Vaillant energy-integral semantics:**
   - The setting range is −999…+9 on the VWZ AI [11]. A hydraulic-station manual seen only as a search snippet gives −100…−30.
   - Firmware 06.07 ignored or double-counted the setting; 09.02 honours it [19][21].
   - The −180 floor is an owner claim [21].
   - Whether "Expanded" bypasses the integral comes from owner observation only [18].
3. **Vaillant room-setpoint shift:** the manual's example has the curve shifting along a 45° axis, so a 1 K setpoint change moves the cold-end flow by several kelvin [14]. The eBUS fit shows the curves converging at Tout = Tset instead, ≈ +1.5 K flow per K of room setpoint at 8.6 °C outdoor [16]. Both may be right at different outdoor temperatures.
4. **Daikin overshoot:** the 2016 split guide documents 1–4 K, default 1 K [27]. Monobloc owners run 4 K and describe stopping at target + 0.5 + 4 K [29]. Whether newer firmware changed the default is unknown [30]. Owners also dispute whether Daikin raises LWT to defend ΔT [30].
5. **Samsung FSV 2091/2093 = 0:** owners disagree whether water law stays active [40].
6. **NIBE stop rule:** owners say the compressor stops at DM 0 [6][7], while the manuals only document the forced +1/+2 backstop [3][4]. The S-series "Auto DM" and Smart Room Comfort algorithms are undocumented [5].
7. **Panasonic restart rule** (outlet < inlet-at-stop − 3 K) comes from a 2013 F-generation manual [31]. The H/J/K/L generations may differ. Owners confirm only the 2 K / 3 min stop [33].
8. **Mitsubishi Auto Adaptation:**
   - The brochure says no complicated settings are needed [35]. Owners report days of learning, overshoot, and tuning of interval and thermo-diff [37][38].
   - Default interval: 10 min in the manual [36]; 60 min in one owner's trial [38].
9. **Gree ΔT-Heat:** the factory default is printed as 10 K, but the scrambled tables also attach "cooling" labels to it [42]. The house's 4 K may be installer-set.
   - Open: which outlet sensor the restart compares against. Note 08 suggests the plate outlet vs the sensor after the backup heater, which could explain "4–5 K" with a setting of 4.
   - Open: the meaning of "heat run time" 1–10 min [42][43].
10. **Gree power limit:** documented in the commissioning tables [43]. Not verified in the read pages: whether it is exposed and accepted on this unit's Modbus map, and whether it limits input or output power.
11. **Real minimum output against outdoor temperature** for this Versati is not in any manual read. The 3.7–3.8 kW figure should be logged against outdoor temperature and flow temperature; minimum capacity rises in mild air. The balance point and duty table in A depend on it.
12. **Vaillant "adaptive heat curve"** on the VRC 720: advertised, but its algorithm was not found in the manual pages read.
13. **Write endurance** of Gree Modbus holding registers is unknown (rule 12).

## Sources

1. NIBE F1145 Installer manual: menus 1.9.1–1.9.5 (pp. 40–42) and 4.9.3 degree-minute settings (p. 49) - NIBE - undated (F-series) - https://www.manualslib.com/manual/1146229/Nibe-F1145.html - manufacturer - Curve 0–15 (default 9), min flow 20 °C, room factor 0–6 (default 2), DM start −60 (−1000…−30), addition −400, step 100.
2. NIBE S1256PC Installer manual, menu 7.1.10.3 Degree minute settings (p. 54) - NIBE - c. 2023–24 - https://www.manualslib.com/manual/3348937/Nibe-S1256pc.html?page=54 - manufacturer - S-series DM ranges (start −1000…−30, relative addition 100–2000, compressor step 10–2000, clamp −3000…+100) and the wear warning.
3. NIBE S1155 Installer manual: heating curve (p. 31) and menu 7.1.6 max difference supply (p. 53) - NIBE - c. 2019–21 - https://www.manualslib.com/manual/1829606/Nibe-S1155.html - manufacturer - Max diff compressor 1–25 K forcing DM = +1; +2 offset steps ≈ +5 K; DOT and power-at-DOT settings.
4. NIBE SMO 40 Installer manual, menus 5.1.1–5.1.3 (p. 45) - NIBE - undated - https://www.manualslib.com/manual/1612921/Nibe-Smo-40.html?page=45 - manufacturer - Max diff compressor default 10 K / addition 7 K (DM forced to +2); DHW economy/normal/luxury start and stop temperatures.
5. NIBE S-series firmware version history (myUplink changelog), document revision 2026-10-19 - NIBE - 2021–2026 - https://www.nibe.eu/webdav/files/myuplink_changelog/nibe-n.pdf - manufacturer - Soft start at minimum speed (2.3.3, 2021); step-difference default 60→200 DM; Smart Room Comfort ML replacing curves (4.0.10, 2025); Auto-DM short-run fix (4.9.4, 2026); PV/SPA short-operation fixes.
6. "Understanding operation of NIBE F2040" - OpenEnergyMonitor forum - c. 2025 - https://community.openenergymonitor.org/t/understanding-operation-of-nibe-f2040/29506/3 - forum - Owner explanation of per-minute DM accumulation, start at −60 and stop at 0, idle pump 10–30 %.
7. "NIBE F2040 12kW with SMO S40 controls not following WC" - OpenEnergyMonitor forum - c. 2024 - https://community.openenergymonitor.org/t/nibe-f2040-12kw-with-smo-s40-controls-not-following-wc/25590 - forum - Intermittent pump → stale BT25 and erratic DM; −240 DM start; post-DHW DM −500 causing 40–45 °C catch-up; ~1 h on/1 h off.
8. "Running my new NIBE ASHP efficiently" - Renewable Heating Hub forum - c. 2023–24 - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/running-my-new-nibe-ashp-efficiently/ - forum - 2–3 cycles/h with 15–20 min high-frequency runs (F2040-16); cycling onset ≈ 10–13 °C; "little experimental evidence" on cycling penalty.
9. "SMO40 / F2120 Compressor Frequency" - Värmepumpsforum (Sweden) - undated - https://www.varmepumpsforum.com/vpforum/index.php?topic=81226.0 - forum - F2120 minimum ~25 Hz ≥ +8 °C / ~35 Hz below; 50–60 Hz in mild weather when DM collapses; start DM moved to −120/−180.
10. Danfoss DHP-AX/DHP-H installation and service manual, integral value and hysteresis (pp. 14, 27) - Danfoss (Thermia platform) - undated - https://www.manualslib.com/manual/897936/Danfoss-Dhp-Ax.html?page=27 and https://www.manualslib.com/manual/601372/Danfoss-Dhp-Ax.html?page=14 - manufacturer - Integral A1 −60 / A2 −600, hysteresis forcing, integral paused during DHW (+2 min).
11. VWZ AI heat pump appliance interface - Operating and installation instructions 0020291573_01 - Vaillant - c. 2019–20 - https://professional.vaillant.co.uk/downloads/aproducts/renewables-1/arotherm-plus/monoblock-heat-pump-system-vwz-ai-heat-pump-appliance-interface-2685948.pdf - manufacturer - Official energy-balance definition; Compr.start heat −60 °min (−999…9); compressor hysteresis 7 K heat / 5 K cool; anti-cycling and utility-block semantics; DHW hysteresis.
12. sensoCOMFORT VRC 720/3 operating and installation instructions, heating-circuit settings (p. 71) - Vaillant (manualslib.mx copy) - c. 2020+ - https://manualslib.mx/manual/744302/Vaillant-Sensocomfort-Vrc-720-3.html?page=71 - manufacturer - Heat curve default 0.60 (HP), min flow 15 °C, max 55 °C, OT switch-off 16 °C (HP).
13. sensoCOMFORT VRC 720 instructions, room temp modulation and OT threshold (p. 13) - Vaillant (manualslib.mx copy) - c. 2019+ - https://manualslib.mx/manual/72503/Vaillant-Sensocomfort-Vrc-720.html?page=13 - manufacturer - Inactive/Active/Expanded definitions and the 2/16 K and 3/16 K switching thresholds.
14. sensoCOMFORT VRC 720f instructions, setting the heat curve (p. 63) - Vaillant (manualslib.mx copy) - c. 2020+ - https://manualslib.mx/manual/590868/Vaillant-Sensocomfort-Vrc-720F.html?page=63 - manufacturer - Curve family 0.1–4.0, example 0.4 → 40 °C at −15 °C, 45° shift with room setpoint.
15. VR 92 remote control operating and installation instructions 0020287935_02 - Vaillant - 2022 - https://professional.vaillant.co.uk/downloads/aproducts/controls/sensocomfort/0020287935-02-2655190.pdf - manufacturer - Room temp. mod. must be Active/Expanded to use a remote room sensor (minor).
16. "Vaillant Arotherm Owners Thread", post #281 (heat-curve equation fit) - OpenEnergyMonitor forum - c. 2023 - https://community.openenergymonitor.org/t/vaillant-arotherm-owners-thread/21891/281 - forum (community analysis checked against eBUS data) - Tflow = Tset + 2.55·(HC·ΔT)^0.78 within ~0.07 K; curves converge at Tout = Tset.
17. "Vaillant Energy Integral (Compr start heat from)" - OpenEnergyMonitor forum - 2024 - https://community.openenergymonitor.org/t/vaillant-energy-integral-compr-start-heat-from/26876 - forum - Owner confirmation of per-minute integral; mild-weather off ~30 min / on ~1 h at ~27 °C flow.
18. "Vaillant Arotherm Firmware 351.06.07 Problems (Energy Integral)", page 2 - OpenEnergyMonitor forum - 2024 - https://community.openenergymonitor.org/t/vaillant-arotherm-firmware-351-06-07-problems-energy-integral/26186?page=2 - forum (owner field logs) - 1.41–1.9 cycles/operating hour; Expanded mode switching at +0.125/−0.1875 K ignoring the integral.
19. "Vaillant Arotherm Owners Thread", page 15 - OpenEnergyMonitor forum - Feb 2024 - https://community.openenergymonitor.org/t/vaillant-arotherm-owners-thread/21891?page=15 - forum - Pre-run at −60, compressor start at −66 with −100 set; firmware 09.02 honours −100; 7 kW modulates to ~25 % (~1.75 kW); 16→6 cycles report.
20. "Vaillant Arotherm Owners Thread", page 30 - OpenEnergyMonitor forum - Dec (c. 2024) - https://community.openenergymonitor.org/t/vaillant-arotherm-owners-thread/21891?page=30 - forum - −30/−60/−100 °min trade-offs; hysteresis 10 K "to be safe"; near-max speed at start; target-walking idea; oversized-unit limits.
21. "What is energy integral" - BuildHub forum - undated - https://forum.buildhub.org.uk/topic/17899-what-is-energy-integral/ - forum - Start −60 / stop 0; claimed −180 floor; firmware double-counting; thick-slab UFH "chasing its tail" comment.
22. "EnergieIntegral vs. Kompressorhysterese" - Bauexpertenforum (German) - 2026 - https://www.bauexpertenforum.de/goto/post?id=1498309 - forum - flexoTHERM: ~20 cycles/day shoulder vs 10–14 winter; how hysteresis cut-offs leave the integral un-recovered and shorten off times.
23. "Vaillant sensoCOMFORT heat pump controller" - Heat Geek - undated - https://www.heatgeek.com/vaillant-sensocomfort-heat-pump-controller - blog - Installer starting points (curve 0.6–0.8 for radiators, min flow 20–25 °C, setback ≤ 2–3 K); little on algorithms.
24. "ReadMe Heizkurven" (heating-curve equations) - Viessmann Community user document - undated - https://community.viessmann.de/viessmann/attachments/viessmann/customers-gas/89775/1/ReadMeHeizkurven.pdf - forum/community analysis - Viessmann curve formula with damped outdoor temperature, worked example (verified by calculation), ~2 K flow per K room setpoint at slope 1.
25. Viessmann One Base service instructions (Vitocal 150-A/151-A/250-A family), parameter descriptions 6200042 - Viessmann - c. 2023–24 - https://www.emax-haustechnik.de/shop/images/products/media/2731604_Serviceanleitung__anl-de.pdf - manufacturer - Room influence 933.6/933.7, min/max flow 1192.x, heating limit with fixed ±1 K on damped outdoor temp, economy function, Smart Grid setpoint raises 2543.x.
26. Vitocal 250-A/252-A Planungsanleitung 6175107 (monoblock 2.6–18.5 kW) - Viessmann - 2024 - https://www.heima24.de/shop/images/products/media/pa-viessmann-Vitocal-250-A-252-A-Monoblock-2,6-bis-18,5kW.pdf - manufacturer - Modulation ranges (e.g. 2.6–12.0 kW at A7/W35), oversizing → transition-season cycling, buffer advice, Hydro AutoControl ≥ 300 l/h, defrost > 1000 l/h.
27. Daikin Altherma low-temperature split installer reference guide 4P401677-1A - Daikin - 2016 - https://www.daikin.eu/content/dam/document-library/Installer-reference-guide/heat/air-to-water-heat-pump-low-temperature/ERQH011-016BV3-BW1,%20ERLQ011-016CV3-CW1,%20EHVZ-CB3V_4PEN401677-1A_Installer%20reference%20guide_English.pdf - manufacturer - Curve defaults, overshoot [9-04], modulated LWT [8-05]/[8-06], emitter type, ΔT [9-09], outdoor averaging [1-0A], 0 °C compensation [D-03], heating-off [4-02], DHW timers.
28. Daikin Altherma 3 M (EBLA09D) installation manual 4P765229-1 - Daikin - 2024 - https://www.daikin.co.uk/content/dam/dauk/document-library/installation-manuals/heat/air-to-water-heat-pump-low-temperature/ebla09dv3u/EBLA09DV3U.EBLA09D3V3U_Installation%20manual_4PEN765229-1_English%20UK.pdf - manufacturer - Current-generation control modes (LWT / external / room thermostat), 2-point vs slope-offset curves, ±10 K user shift, emitter-type ΔT rules, balancing timers menu.
29. "Why is my 9kW Daikin continuing to heat beyond target room temperature?" - OpenEnergyMonitor forum - c. 2024 - https://community.openenergymonitor.org/t/why-is-my-9kw-daikin-continuing-to-heat-beyond-target-room-temperature/27079 - forum - Owner-reported room-stat band −0.5/+1.5 K, overshoot 4 K stop logic, ~900 W minimum draw on 9–16 kW.
30. "Daikin Altherma - post engineer firmware update" - OpenEnergyMonitor forum - c. 2025 - https://community.openenergymonitor.org/t/daikin-altherma-post-engineer-firmware-update/29767 - forum - Hourly cycling ≥ 14 °C (8 kW); disputed ΔT/LWT logic; minimum flow 11 l/min.
31. Aquarea WH-SXC09/12F service manual, PAPAMY1311028CE (section 12 Operation and Control) - Panasonic - 2013 - https://www.panasonicproclub.com/uploads/CZ/catalogues/aquarea/service-manual/SXC9,12_F_E8_service%20manual_PAPAMY1311028CE.pdf - manufacturer - Thermo-off +2 K for 3 min, 3-min wait and −3 K restart rule, outdoor thermo-off +3/+1 K, tank thermo rules.
32. HeishaMon MQTT topics documentation - HeishaMon project (GitHub) - current - https://github.com/Egyras/HeishaMon/blob/master/MQTT-Topics.md - open-source documentation (forum-grade) - Panasonic curve parameters, shift −5…+5, heating-off 5–35 °C, sensor/control options, pump and quiet settings.
33. HeishaMon discussion #620 (compressor stops on 3-way-valve switching) - GitHub - c. 2023–24 - https://github.com/Egyras/HeishaMon/discussions/620 - forum - Owner confirmation of 2 K / 3 min stop; target-follows-outlet workaround rule; ~2.5 h average runs.
34. "Panasonic Aquarea heat pump configuration" - OpenEnergyMonitor forum - c. 2025 - https://community.openenergymonitor.org/t/panasonic-aquarea-heat-pump-configuration/28349 - forum - Starting curve 35 °C @ −20 / 23 °C @ +15; water-sensor control reducing room variation < 1 °C; heating-off 8–12 °C advice.
35. Ecodan product guide, "Auto Adaptation" page (p. 125) - Mitsubishi Electric - c. 2023 - https://renewableheatinghub.co.uk/wp-content/uploads/wpforo/attachments/5124/4908-EcodanFullProduct.pdf - manufacturer - Official Auto Adaptation principle (capacity estimate + room-temperature prediction → lower/keep/raise flow); 2 % COP per 1 K flow claim.
36. Ecodan FTC installation manual (EHSC-VM6D), pp. 44 and 49 - Mitsubishi Electric - undated - https://manualslib.com/manual/2548942/Mitsubishi-Electric-Ecodan-Ehsc-Vm6d-Cn.html - manufacturer - Room auto-adaptation is the factory default; flow range 25–45 (30) / max 50; interval 10 min; thermo-diff −9…−1 (−5) / +3…+5 (+5); 20 °C fixed minimum.
37. "Mitsubishi Ecodan Performance using Room Auto Adapt" - OpenEnergyMonitor forum - Feb 2024 - https://community.openenergymonitor.org/t/mitsubishi-ecodan-performance-using-room-auto-adapt/25558 - forum (owner field data) - SCOP 3.4 → 3.6; daily COP 3.5 vs 4.0 examples; less cycling than weather compensation (owner view).
38. "Mitsubishi Ecodan auto adaption trial to stop cycling" - Renewable Heating Hub forum - undated - https://renewableheatinghub.co.uk/forums/renewable-heating-air-source-heap-pumps-ashps/mitsubishi-ecodan-auto-adaption-trial-to-stop-cycling - forum - 11.2 kW oversized: thermo-diff +3/−9 and 60-min interval → one ~20 h run; curve 39 °C @ −2 / 27 °C @ +10.
39. Samsung Gen 6 ASHP installation pack incl. FSV review (26 May 2021) - SNH Trade Centre / Samsung - 2024 - https://www.snhtradecentre.co.uk/wp-content/uploads/2024/02/Samsung-Gen-6-ASHP-Installation.pdf - manufacturer/distributor - Water-law FSV ranges and defaults (−10/15 °C, 40/25 °C), DHW max time and booster delay, disinfection defaults.
40. "I want to punch my Samsung controller FSV #2091" - OpenEnergyMonitor forum - c. 2024 - https://community.openenergymonitor.org/t/i-want-to-punch-my-samsung-controller-fsv-2091/27143 - forum - FSV 2091/2093 mode semantics (mode 1 = keep running at min Hz), ±5 K water-law offset, pump PWM formula (#4052/#4053).
41. LG Therma V installation manual, "Hysteresis heating water" (p. 224) - LG Electronics - undated - https://www.manualslib.com/manual/2050610/Lg-Therma-V.html?page=224 - manufacturer - Temp On −2 K (0…−9), Temp Off +2 K (0…+4).
42. Gree Versati III Series service manual (unit control pp. 37–39, functions pp. 46–48, commissioning pp. 54–56, 61) - Gree - c. 2016–18 - https://www.manualslib.com/manual/1561334/Gree-Versati-Iii-Series.html - manufacturer - Frequency ∝ LWT error, stop at min frequency, T-water/T-room control, ΔT-Heat 2–10 K (default printed 10), ΔT-Room 1–5 K, Weather depend behaviour, floor-debug segments.
43. Gree VERSATI III service manual (heating control p. 50, commissioning pp. 68–69) - Gree - c. 2019–20 - https://www.manualslib.com/manual/3549054/Gree-Versati-Iii.html - manufacturer - Compressor control from water or room error; C/P limit (current 0–50 A def 16 A; power 0–10 kW def 3.0 kW); T-HP max 40–55 (50); heat run time 1–10 min.
44. "Wärmepumpe Heizkurve richtig einstellen: Steilheit, Niveau und Praxisbeispiel" - 42watt (German) - c. 2025 - https://42watt.de/magazin/heizkurve-warmepumpe - blog - UFH slope 0.2–0.5 vs radiators 0.8–1.6; ≥ 48 h between changes; 2.5–3 % electricity per 1 K (BWP rule of thumb).
