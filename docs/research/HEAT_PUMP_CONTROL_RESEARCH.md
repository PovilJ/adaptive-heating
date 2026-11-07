# Heat Pump Control Research: what decides efficiency, and how this house should be controlled

> Master document of the 2026-11-06 research sweep. Written for the owner of a detached Lithuanian house with a Gree Versati air-to-water heat pump (9 kW class), wet underfloor heating in a concrete slab, Komfovent MVHR, 15 kWp PV and a hybrid battery. Room target 22.0 °C.
>
> **Basis.** 46 research notes in `docs/research/notes/`: 15 topic notes, 15 gap notes (two rounds) and 16 adversarial verification notes. Where a verification note corrected a claim, the corrected version is used here. The underlying notes carry the full source lists (about 633 distinct web sources, see §12), plus several new analyses of public heatpumpmonitor.org (HPM) field data, HP Keymark certified test data, Vilnius weather and Nord Pool prices.
>
> **How to read it.** §1 is the one-page answer. §2-§6 are the engineering background. §7 is the diagnosis of this house. §8 lists eleven control strategies to build and test in a simulator. §9 lists settings and hardware checks that need no code. §10-§12 cover evidence quality, a glossary and the index of notes.
>
> **Labels.** Confidence is High (several independent measured sources agree), Medium (mechanism documented, magnitude from other hardware or from arithmetic), Low (plausible, untested). "[calc]" means arithmetic done by a researcher on cited numbers or on the house figures; it is not independent evidence.

---

## 1. Plain-language summary

**What decides how efficient a heat pump is, ranked by impact for this house:**

| Rank | Lever | Typical size | Applies to this house? |
|---|---|---|---|
| 1 | **Water (flow) temperature.** Every extra kelvin of leaving water makes the compressor lift heat further. | **3-4 % more electricity per K in mild weather** (+5…+12 °C), about 2.5 % per K near 0 °C, about 2 % per K below −5 °C. Running 36 °C where 30 °C would do costs about 18-20 % at +7 °C. | Yes. Today's 31-36 °C setpoints (39 °C peaks) are 3-8 K above what the slab needs. This is the biggest lever. |
| 2 | **How hard the compressor runs.** A fast compressor needs bigger temperature differences inside its heat exchangers. | Flat-out vs mid speed: 15-25 % more electricity per kWh in lab and declared data; only a few % in field data once water temperature is held equal. Most of the real-world penalty comes from the **higher water temperature** that a high output forces into the slab. | Yes. The ~3 kW catch-up runs at +2 °C are the expensive episodes. |
| 3 | **Weather and time (air temperature, humidity, defrost).** | Defrost costs about 5-8 % of heating electricity in a Lithuanian winter (range 4-12 %). Each kelvin warmer air is worth ~3.5 % COP. Moving heat from a humid +1 °C night to a +4 °C afternoon cuts defrosts per kWh 2-5×. | Partly. Worth a few % from October-November and March-April; almost nothing in December-February. |
| 4 | **Hot water.** | Each kelvin of tank temperature costs ~1.5-2 % of hot-water COP. The weekly 70 °C electric legionella cycle costs ~150-190 kWh/yr net and blocks space heating for ~1.5 h. | Yes, moderately. |
| 5 | **Parasitic and hidden electric heat.** Standby, pumps, backup heaters, the ventilation unit's own heater. | Standby ~20-25 W is small. A mis-set backup heater can cost 500-1,300 kWh in a cold winter. The Komfovent's electric heater may run 3-4 kWh/day. | Unknown until checked. Cheap to check, potentially large. |
| 6 | **On/off cycling itself.** | Each start costs about 2-5 minutes of output (0.1-0.2 kWh of heat). With runs of 1-4 h the whole effect is **1-3 %**. Only runs under ~20-30 min are clearly costly. | Small. Runs of 0.5-4 h are already in the harmless zone. |

**What this means for the complaint.** The owner is right that the system uses too much high-temperature water. He is mostly wrong that the on/off cycling is itself the waste. The two are linked, though, and the link is the key finding of this research:

1. **The house cannot avoid cycling in mild weather.** The Versati's smallest steady output (~3.7-3.8 kW of heat) is more than the house needs above roughly −5…+3 °C outdoors (about 1.7 kW at +10 °C). So the unit must run in blocks and rest. With a 6.6 kWh/K slab that is fine: three to six runs of 1-4 h a day cost almost nothing.
2. **The way starts are triggered today makes every run hot and fast.** The Versati only restarts when its flow setpoint is at least ~4 K above the outlet temperature, and its firmware sets compressor speed in proportion to the gap between setpoint and outlet. So each restart begins with a large error, which the firmware answers with high speed and hot water. Home Assistant then writes setpoints every 30 minutes that sit several kelvin above what the slab needs. Hot water and catch-up runs follow from the trigger mechanism, not from the slab needing them.
3. **The fix is to separate *when* to run from *how hot* to run.** Decide run timing from the house's daily energy need. Start each run gently. Keep the water only as warm as needed to push the minimum output into the slab (about 28-31 °C in mild weather, depending on floor covering). Cap the compressor's power so starts cannot sprint.
4. **Expected gain:** roughly **10-25 % less space-heating electricity in 0…+10 °C weather**, mostly from 3-6 K lower water and the end of catch-up bursts (Medium confidence; magnitude depends on how much heat currently goes out in bursts, which logging will show). Smarter timing adds 1-3 % (more in cost if the tariff varies). Fixing hot water, the legionella cycle and any mis-set electric heaters may add several hundred kWh a year.
5. **Not worth doing:** adding a buffer tank, raising water temperature to reduce starts, night setbacks, quiet mode on humid days, chasing room temperature hour by hour, or building price-chasing logic before knowing the tariff (on Lithuanian net metering with a summer surplus, the clock barely matters).

**Before building anything, measure three things on the unit:** compressor frequency (Modbus Words 142/143) against setpoint error and electrical power during starts; whether the internal pump runs while the compressor is off (coil 175); and whether the ~3 kW draws coincide with any heater coil (171/172/173) or with the C/P power limit. Those three logs decide which of the strategies in §8 is safe and how big the prize is.

---

## 2. How a modern inverter air-to-water heat pump works

### 2.1 Refrigerant cycle, lift and COP

A heat pump moves heat from outdoor air to the heating water by circulating refrigerant (R32 in the Versati III/IV) through four parts:
- the **evaporator** (outdoor coil), where refrigerant boils at a temperature a few kelvin below the air and absorbs heat;
- the **compressor**, which raises the refrigerant's pressure and temperature, using electricity;
- the **condenser** (a plate heat exchanger), where the hot refrigerant condenses and gives heat to the water;
- the **expansion valve**, which drops the pressure again.

The thermodynamic ceiling is the Carnot COP: COP_Carnot = T_cond / (T_cond − T_evap), in kelvin. Real units reach a fixed fraction of that, called **η** or **%-Carnot**. With the usual convention T_cond = leaving water + 2 K and T_evap = outdoor − 6 K:
- Gree's certified EN 14825 points give **η ≈ 0.50 ± 0.05** across the map; about 10-15 % lower near maximum speed (verify R2-C5).
- Healthy field systems run at 0.45-0.55; poor ones 0.25-0.42 (notes 02, 13).
- Rule: **COP ≈ 0.50 × (LWT + 275.15) / (LWT + 2 − T_out + 6)**, then about ×0.85-0.9 for defrost and field effects.

**Lift** is the temperature distance the compressor must bridge: roughly (flow temperature + condensing approach) − (outdoor temperature − evaporating approach). Every kelvin of lift costs COP. The percentage cost per kelvin is larger when the total lift is small, which is why mild weather is where water temperature matters most:

| Outdoor | Water compared | Loss per +1 K (median, ~1,600 certified models) | Gree Versati III |
|---|---|---|---|
| −7 °C | W34 → W52 | 1.8-1.9 %/K | 1.7-1.8 %/K |
| +2 °C | W30 → W42 | 2.4-2.5 %/K | 2.9 %/K |
| +7 °C | W27 → W36 | 3.1-3.3 %/K | 3.4 %/K |
| +12 °C | W24 → W30 | ~3.9 %/K | 4.4-5.6 %/K |

A compact approximation: **%/K ≈ 100 / (T_flow − T_out + 8)** (verify R1-C2, from the [HP Keymark](https://www.heatpumpkeymark.com/uploads/tx_ehpakeymark/Cert_041-K004-31.pdf) data). For whole-system seasonal performance including hot water and pumps the effect is diluted to about half.

### 2.2 Compressor modulation and minimum output

An inverter varies compressor speed (Hz) and therefore heat output. The Versati's compressor is catalogued at **20-120 Hz** (marketing also claims "down to 10 Hz", which no certified point reflects). Real-world facts:
- **Turndown is about 3:1, not 10:1.** Community-measured minimum continuous outputs for 45 model sizes span 19-76 % of nominal, median ~34 % (note 01).
- **This Versati's measured floor is ~3.7-3.8 kW of heat**, about 40 % of its 9.5 kW rating. Certified data suggest the floor **rises in warm air**: for first/second-generation units roughly P_min ≈ 3.2 kW + 0.12 kW/K × (T_out − 2), floor 3.1 kW; third-generation (NhH3) units certify points down to 2.4-2.8 kW (gap G1).
- **Minimum electrical input** at the floor is best modelled as P_min / COP(LWT, T_out): about **0.52 kW at W24, 0.65 kW at W30, 0.78 kW at W35** in +7…+12 °C weather, and ~0.9-1.0 kW at +2 °C/W35 (verify R2-C5).
- **Efficiency is not best at minimum speed by default.** Lab tests put peak compressor efficiency near mid speed (40-60 Hz on a 120 Hz machine). Field data show %-Carnot flat between ~30 % and ~100 % of rated output and collapsing only below ~20-25 % of rated output or ~300 W electrical (verify R1-C5, R2-C3). The Versati's floor (~40 %) sits on the plateau, so running at its floor is not penalised; its real advantage is the **lower water temperature** it allows.
- **Maximum output falls in cold air.** Versati III 10 kW at W35: 9.50 kW at +7 °C, 8.08 kW at +2 °C, 6.65 kW at −7 °C, 4.56 kW at −20 °C ([Versati III service manual](https://gree-bulgaria.com/manuals/service/Versati_III_Monoblock_04_06_08_10_12_14_16_service.pdf), note 08, gap G6).

### 2.3 What the firmware does with a flow setpoint

All brands use the same three layers (note 04):
1. **A target flow temperature**, from a weather curve or written from outside (here: Home Assistant writes Modbus Word 10 every ~30 min).
2. **An on/off decision**, either from an integral of flow error ("degree-minutes", NIBE; "energy integral", Vaillant) or, on Gree, Daikin, Panasonic, Mitsubishi, LG and Samsung, from plain temperature bands.
3. **A speed loop.** On the Versati, compressor frequency rises with (setpoint − leaving water). Gree states this in every generation's manual but publishes no gain (gap G2).

Gree's start/stop logic, as documented:
- **Restart** only when setpoint − outlet ≥ **ΔT-Heat** (Modbus Word 30, range 2-10 K, factory default 10 K; this house uses 4 K). Gree Poland's official guide recommends 2-4 K for floor heating.
- **Stop** when the compressor is already at minimum frequency and the water is still above setpoint by an undocumented "standby zone" margin. A normal stop first ramps down to minimum. On Versati III firmware with **Heat run time** (Word 34, 1-10 min, default 3 or 5 min), the stop happens only after the error has stayed in the standby zone for that time. It is a **conditional stop delay, not a minimum run time**, and it has been removed from the newest Modbus map (V1.7) and the Versati IV (gap G2).
- **Fixed timers:** a 3-minute minimum off-time. The 6-minute post-start capacity hold and 3-minute valve freeze appear only in pre-2014 manuals (gap G2).
- **Writes** take effect immediately and are stored to memory 30 minutes later, so frequent setpoint writes do not wear the memory on every write.

**Consequence:** a setpoint is not a temperature request but a **power request**. A 4 K start gap commands roughly twice the minimum output on a slab. Unless output is capped or the setpoint is lowered after the start, every restart sprints.

### 2.4 Start and stop costs

- On start, refrigerant that migrated during the off-period must be redistributed. With an electronic expansion valve (which the Versati has) the loss is about **1-2 minutes of full output**; older thermostatic-valve units lose 4-5 minutes; units with bad migration up to 12 minutes (verify R1-C4, gap G4).
- Field estimate (HPM, within-system): about 3 lost full-output minutes per start, i.e. **0.1-0.2 kWh of heat per start at mild temperatures, up to ~0.3 kWh after a long cold off-period**.
- As a share of the run: ~3-15 % of a 10-min run, 1-6 % of 30 min, 0.5-3 % of 60 min, 0.2-1 % of 3 h.
- Wear: compressor makers set only rate limits (Copeland scroll ≤10 starts/h, Danfoss ≤12/h, Bitzer 6-12/h with inverters) and minimum runs for oil return. No maker publishes a start-count life. The "100,000 starts" figure is an unsourced trade rule; the "12 % more cycles = 15 % less life" citation is untraceable (gap R2-G6). A planning weight of **~0.15 kWh-electric-equivalent per start** (range 0.05-0.3) covers energy plus a pessimistic wear allowance.

### 2.5 Defrost

Below about +5 °C in humid air, frost grows on the outdoor coil. The unit reverses the cycle for a few minutes, pulling heat back out of the water (and therefore out of the slab), then recovers.
- **Gree trigger:** accumulated compressor run time ≥ ~50 min (Versati I/II default; III undocumented, field 50-60 min) **and** coil temperature below a threshold (−4 °C on old units; −2 to −8 °C depending on outdoor temperature on newer Gree logic). The run-time counter **does not reset when the compressor stops** (gap G7). On the one Gree in the HPM data, 93-99 % of defrosts at 0…+5 °C came within 20 min of a restart once the clock was full (gap R2-G4).
- **Cost per event:** ~0.15-0.2 kWh of electricity; 0.15-0.8 kWh of heat drawn back from the water (0.05-0.1 K of slab: harmless).
- **Frequency:** a Vilnius Panasonic logged 1.17 defrosts/h at −2…+3.7 °C, 0.52/h at +4 °C and 86 % RH ([Kropas thesis](https://cris.vilniustech.lt/cris/handle/20.500.14911/160074)).
- **Season share:** reversed heat ~4.2-4.6 % of seasonal heat in Vilnius weather; electricity attributable ~**5-8 % central, 4-12 % across units** (verify R1-C6, gap G7).

### 2.6 Hot water priority

On the all-in-one, hot water (DHW) has priority by default: the 3-way valve diverts the compressor to the 185 L tank. Gree sets DHW compressor speed from the gap between tank setpoint and tank temperature, so a cold tank means a fast, hot run. The tank's 3 kW-class electric heater is used for disinfection (default **70 °C, Saturday 23:00**, when enabled) and whenever the tank target exceeds **T-HP max** (default 50 °C). Under **tank-heater Logic 1** (default) the compressor never runs while the tank heater runs, so a disinfection finish blocks space heating for ~1.5 h (gap G5, verify R2-C8). The Versati has **no maximum-DHW-run or anti-recycle timer** (Daikin and Mitsubishi do); those must come from Home Assistant.

---

## 3. Efficiency levers, with evidence

Each table: claim | number | conditions | evidence type | sources | confidence. Verified figures replace the original claims where a verify note disagreed.

### 3.1 Flow temperature

| Claim | Number | Conditions | Evidence type | Sources | Confidence |
|---|---|---|---|---|---|
| COP loss per +1 K leaving water, unit level | 1.8 %/K at A−7; 2.4-2.9 at A+2; 3.1-3.4 at A+7; 3.9-5.6 at A+12 | Same outdoor temp, same part-load ratio | Certified lab data (1,600+ models; Versati III) | [HP Keymark](https://www.heatpumpkeymark.com/uploads/tx_ehpakeymark/Cert_041-K004-31.pdf); verify R1-C2; gap G1 | High |
| Within-system field penalty | 3.6 %/K; 1/2/3 K hotter = −3.6/−6.6/−10.3 % | HPM, same system, same 2 K outdoor band | Field data (own analysis) | [heatpumpmonitor.org](https://heatpumpmonitor.org); note 13 | High |
| Fleet SPF vs flow | −0.10 SPF per K (≈2.3-2.9 %/K), R² 0.52 | Cross-section, H4 boundary | Field data | [OEM low-temperature guidance](https://docs.openenergymonitor.org/heatpumpmonitor/low_temperature.html) | High |
| Top-quartile UFH systems run cooler | Space-heating flow 29.3 °C vs 33.0 °C; SPF 4.61 vs 3.28 | HPM UFH-only systems | Field data | note 13 | High (selection bias possible) |
| Benchmarks for good UFH | ~29 °C at −5…+2 °C; 28.5 °C at 2-6 °C; 27 °C at 6-10 °C | Coolest quarter of HPM UFH fleet | Field data | note 07 | Medium-High |
| Slab needs little water | Lowest outlet to absorb 3.75 kW: ~28-29 °C at +10 °C, 30-31 °C at +2 °C (laminate/parquet, 45 mm screed, 150 mm pitch); tile 1.5-2.5 K lower | 130 m² active floor | EN 1264 method + certified Uponor chart + calc | [Uponor planning](https://brandportal.uponor.com/m/7187327a41365ace/original/TI-planning-principles-UFHC-EN-1186660-v1.pdf); gap G3 | Medium |
| Identifying the floor pays off | Model-guided supply cut by 8.6 K without comfort loss | DTU field study, floor heating | Field data (abstract) | gap G3 (Sarran et al.) | Medium |
| Whole-system dilution | System SPF moves ~1.1 %/K (GSHP+DHW simulation) | Seasonal, includes DHW | Simulation | note 02 | Medium |

### 3.2 Cycling and starts

| Claim | Number | Conditions | Evidence type | Sources | Confidence |
|---|---|---|---|---|---|
| Cost per start | 1-2 min full output (EEV lab); ~3 min field median; 0.1-0.2 kWh heat at mild temps, ≤0.3 after long cold off | Modern inverter ASHP | Lab + field (own fit) | [Uhlmann & Bertsch](https://iifiir.org/en/fridoc/theoretical-and-experimental-investigation-of-startup-and-shutdown-135447); gap G4; verify R1-C4 | Medium |
| Run-length curve (relative %-Carnot) | 15-20 min −1.8/−5.0 %; 30-45 −1.2/−1.5; 45-60 −0.7/−0.9; 60-90 ≈0; 90-180 +0.8; >300 +1.4 | 66 UFH systems, 9,113 days, same outdoor band | Field data (own re-analysis) | verify R1-C4 | Medium-High |
| Per extra start per day | −0.24 % (all), −0.31 % (runs ≥60 min) at 0-8 °C; −0.05…−0.12 % at 8-14 °C | Within system | Field data | verify R1-C4 | Medium |
| Flow beats starts | +1 K flow saves only 0.5-0.7 starts/day but costs 15-25× more | Within system, UFH | Field data | note 07 | High |
| Hysteresis changes starts more than SCOP | UFH SCOP 3.14-3.25 across hysteresis; inner-loop PI settings ±18.5 % | HiL + simulation | Lab | [Göbel et al. ECOS 2023](https://proceedings.com/content/069/069564-0075open.pdf) | Medium |
| Buffers do not help in the field | Buffered: −7 % raw COP, +1.1 K flow, shorter runs (74 vs 95 min) | HPM cross-section | Field data | notes 03, 15 | Medium (confounded) |
| Low daily duty penalty | rtf < 0.1: −22 %; 0.1-0.2: −6 %; 0.2-0.3: ≈−1 %; about half is off-time electricity (~22 W) | Mild days, no DHW | Field data | verify R1-C5; gap G4 | Medium |
| Start limits | ≤10/h Copeland, ≤12/h Danfoss, 6-12/h Bitzer; Gree 3-min lockout | Manufacturer guidance | Manufacturer | [Copeland XHV AGL](https://media.copeland.com/6937539b-0c9e-41d6-8a97-b16b0107724a/C060239_1218_E_AGL_HPScroll_XHV_VS_FULL.pdf); gap R2-G6 | High (as limits) |
| Start wear price | ~€0.015-0.05 per start on pessimistic linear wear → 0.1-0.25 kWh_el-equivalent | 100k-start rule (unsourced) | Calculation | gap R2-G6 | Low |

### 3.3 Compressor speed and part load

| Claim | Number | Conditions | Evidence type | Sources | Confidence |
|---|---|---|---|---|---|
| Max vs ~half capacity, same water & air | 5-30 % more electricity per kWh, median ~20 % (Vaillant 4 kW −3 %, 15 kW +29 %) | +2 °C, W35, declared data | Manufacturer-declared | [Vaillant UNI/TS data](https://Vaillant.it/downloads/vgoa-vaillant-it-doc/specifiche-tecniche/dati-uni-ts/arotherm-plus-uni-ts11300-220713-2490727.pdf); verify R1-C1, R2-C2 | Medium-High |
| Lab sweep 30→90 Hz | COP −30…−40 % | Inlet water fixed (so outlet rises) | Lab | [KTH Awan thesis](https://www.diva-portal.org/smash/get/diva2:565195/FULLTEXT01.pdf) | Medium (overstates same-LWT effect) |
| Field pure-speed term | Mid→flat-out costs ~1-3 % at same flow & outdoor temp (~1 %/kW; range 0-4 %/kW); steep collapse below 0.2-0.3 of rated | 26 systems, 1-min steady data | Field data (own analysis) | verify R2-C3 | Medium |
| Versati η by speed band | Max-capacity points 0.41-0.50; mid 0.47-0.56; lowest-capacity 0.45-0.61 (no consistent min-speed penalty) | Certified EN 14825 points, G1-G3 | Certified lab | gap G1; verify R2-C5 | Medium-High |
| Extra kW into the slab forces hotter water | 0.5-0.9 K per extra kW above P_min (1/K_ws) ≈ 1.2-2.7 % COP per kW | Bursts of 0.5-4 h | Physics + 2-D conduction sim | verify R2-C4 | Medium |
| Versati at +2 °C: full vs mid | 9.55 kW at ≈W35, COP 3.39 vs 4.90 kW at ≈W30, COP 4.59 → ~35 % more electricity per kWh (≈12 % from water, ≈20 % from speed) | Certified G3 points | Certified lab + calc | gap G1; verify R2-C2 | Medium (whether the house's 3 kW draw is full speed is unconfirmed) |
| MPC that lowered speed | −11 % electricity, +3 % SCOP, 5 K lower supply, 46 vs 63 Hz mean | HiL, perfect forecast | Lab | [HPT Magazine 2025](https://heatpumpingtechnologies.org/articles/heat-pumping-technologies-magazine-vol-43-no-2-2025/outperforming-the-heating-curve-with-data-driven-model-predictive-control/) | Medium |
| Real-house example | Supply 33 → 26 °C: compressor input 2.7 → 1.7 kW, daily 33 → 22 kWh at −5 °C | Belgian UFH house (Volta) | Field case study | notes 02, 07 | Low-Medium (single case) |

### 3.4 Defrost

| Claim | Number | Conditions | Evidence type | Sources | Confidence |
|---|---|---|---|---|---|
| Reversed heat by outdoor temp | ~1 % at +6…+8 °C; 4.4 % at +2…+3; 5.2-5.9 % at −2…+2; 6.3-6.7 % at −10…−2 | 113 systems, heat-weighted | Field data | note 09; verify R1-C6 | High (as lower bound) |
| Defrosts per 100 kWh, RH ≥ 90 % | 12.9 at 0 °C; 11.8 at +1; 7.6 at +2; 5.4 at +3; 2.6 at +4; 2.0 at +5 | 27 systems, 6-h windows | Field data (own analysis) | gap R2-G4 | Medium |
| Season electricity attributable to defrost | ~5-8 % central (range 4-12 %) | Lithuanian weather weighting | Field + inference | verify R1-C6; gap G7 | Low-Medium |
| Run structure (few long vs many short runs) | Rate ratio 1.05 defrosts/kWh; COP 0.99× | 0…+5 °C, RH ≥ 80 %, stratified | Field data | gap R2-G4 | Medium |
| Low compressor speed + full fan | 22 → 9 defrosts/day (−59 %) at 2 °C/84 %; delays frost, does not avoid it at ≥84 % RH | Lab, variable-speed ASHP | Lab | [Liu PolyU thesis](https://theses.lib.polyu.edu.hk/bitstream/200/12447/3/6895.pdf); gap G7 | Medium |
| Quiet mode (slower fan) | Defrost every 52-56 min at +2…+5 °C on a Versati III 16 kW | One field report | Field anecdote | note 08; gap G7 | Medium |
| Lower water temp | 50 → 35 °C water: −26 % modelled defrosts in Vilnius | Validated simulation | Thesis | [Kropas thesis](https://cris.vilniustech.lt/cris/handle/20.500.14911/160074) | Medium |
| Timer defrost wastes events | ~37 % unnecessary; Dutch model 1,900 vs ~900 needed/yr | Time-temperature logic | Field / model | gap G7 | Medium |
| Deep-cold timer behaviour | Factory defrost every 55 min with no frost; 4-h minimum gave 65-85 % less defrost time | Alaska, cold-climate unit | Lab + field | [NREL 2024](https://www.energy.gov/sites/default/files/2024-11/bto-peer-2024_32264-detailed-air-source-hp-evaluation-for-very-cold-climates-munk.pdf) | Medium |

### 3.5 Timing over the day

| Claim | Number | Conditions | Evidence type | Sources | Confidence |
|---|---|---|---|---|---|
| Warmest 6 h above daily mean | 1.0/1.4/1.9 K (Dec/Jan/Feb) with perfect forecast; 0.4/0.5/1.3 K fixed 10-16 h; 3.7 K in March | Vilnius ERA5 2022-25 | Data analysis | verify R1-C7 | High |
| Saving from "warmest hours first" | ≤0.6 % Dec-Feb; 1.5-1.8 % Oct-Apr vs even; ~3-3.5 % vs night-heavy baseline | Fixed W35, no comfort limit (upper bound) | Calculation | verify R1-C7 | Medium-High |
| Kuboth twin-rig MPC | −4.1 % electricity, COP +5.4 %, PV self-use +107.7 %, cost −9 % (not a timing-only effect) | 125 days, 500 L buffer, Bayreuth | Lab (HiL) | [Kuboth et al. 2020](https://epub.uni-bayreuth.de/5598/1/energies-13-06016.pdf) | High (for that rig) |
| Defrost timing bonus | Production at +4 °C vs +1 °C (RH ≥ 90 %): defrost heat 1.1 % vs 5.8 %; COP 3.69 vs 3.00 | Field, pooled | Field data | gap R2-G4 | Medium |
| Price-aware scheduling value (spot plan) | ±0.5 K band: −1…−6 % cost (−3…−11 % with PV); ±1 K: −8…−14 % (−13…−22 % with PV) | Perfect-foresight DP, three winters | Calculation | verify R2-C6 | Medium |
| Price-aware scheduling value (net metering) | ≈0 % (−0.6…+2.6 %) | ESO returned-energy 0.0726 €/kWh any hour | Calculation | verify R2-C6; gap R2-G2 | Medium-High |
| Price-driven MPC on concrete UFH | Cost −12.4 %, electricity +9.5 %; losses below 0 °C | Danish occupied house, 97 days | Field data | [Thorsteinsson et al.](https://ar5iv.labs.arxiv.org/html/2303.16289) | High (for that case) |

### 3.6 Domestic hot water

| Claim | Number | Conditions | Evidence type | Sources | Confidence |
|---|---|---|---|---|---|
| COP vs leaving water (DHW) | Factors 1.00/0.87/0.74/0.61 at 45/50/55/60 °C (+7 °C) ≈ 2.6-3.3 %/K | Gree Versati III AIO table | Manufacturer | gap G5; verify R2-C8 | High |
| COP vs tank setpoint (field) | ~1.6-1.8 %/K; median DHW COP 3.32 (40-45 °C), 3.09 (46-48), 3.00 (49-50), 2.82 (51-55) | 409 HPM systems | Field data | verify R2-C8 | Medium |
| 47 vs 52 °C tank | Saves ~8-15 % DHW electricity ≈ 50-90 kWh/yr | ~1,800 kWh/yr DHW heat | Calculation | verify R2-C8 | Medium |
| Weekly 70 °C legionella from T-HP max 50 °C | ~4.3 kWh resistive/event, ~225 kWh/yr; net extra ~150-190 kWh/yr | 185 L tank | Calculation | verify R2-C8 | Medium |
| Logic 1 blocking | ~1.4-1.5 h without space heating per 50 → 70 °C finish (if 3 kW heater) | Tank heater rating unverified | Manufacturer text + calc | verify R2-C8 | Medium |
| Lithuanian rule | HN 136:2023: ≥50 °C at tap after 1 min; binds designers/operators, only recommended for self-managed private homes; no periodic disinfection frequency found | Law summary (full text blocked) | Regulation | [NVSC summary](https://suduvosgidas.lt/naujoje-lietuvos-higienos-normoje-nustatyti-karsto-vandens-sveikatos-saugos-reikalavimai); gap G5 | Medium |
| Afternoon DHW | +2.4 % COP per K outdoor; 13-15 h is 15-20 % better than night in shoulder months, 2-4 % in mid-winter | Gree table + Vilnius weather | Manufacturer + calc | gap G5 | Medium |
| DHW-heavy days | >40 % DHW share → ~15 % lower daily COP | HPM, mild weather | Field data | note 13 | Medium |

### 3.7 Pumps and hydraulics

| Claim | Number | Conditions | Evidence type | Sources | Confidence |
|---|---|---|---|---|---|
| Versati pump draw | Rated **4-75 W** (RS25/7.5 class), ΔT-modulated; the "75-85 W continuously in standby" claim is **refuted** | Catalogue + manual text | Manufacturer | verify R2-C1; gap R2-G1 | Medium-High |
| Pump in standby | Manuals: pump stops after the compressor in normal shutdown; the "runs in standby" sentence belonged to the backup-boiler logic | Versati III/IV manuals | Manufacturer text | gap R2-G1 | Medium (unmeasured) |
| Whole-unit idle draw, modern monoblocs | Median ~20 W (IQR 14-32, p90 ~50 W); Versati declares P_TO = P_SB = 25 W | −5…+14 °C days | Field + certified | verify R2-C1; gap G1 | High |
| Delta-T at minimum output | ~1.9-2.1 K at ~26-27 L/min; normal | Fixed flow | Physics | note 15 | High |
| Lowering ΔT (more flow) | Outlet −1.5 K (≈+2-4 % COP) vs steeply rising pump power: near wash | — | Physics + field cross-section | note 15 | Medium |
| Manifold mixing group | Would force the unit hotter than the floor receives; check outlet vs manifold supply (>1 K gap = mixing) | Common in Baltic manifolds | Inference | note 15 | High value, presence unknown |
| Zone actuators | Closing loops raises supply temperature and causes short cycling; one owner went 4,000-4,200 → 2,800-3,000 kWh/yr and 8-10 → ≤3 starts/day after removing room control | UFH | Simulation + anecdote | notes 03, 05, 11 | Medium |
| Minimum volume | Gree 20 L; flow-switch trip needs a power cycle | Versati III | Manufacturer | note 08 | High |

### 3.8 Setback

| Claim | Number | Conditions | Evidence type | Sources | Confidence |
|---|---|---|---|---|---|
| 2 K, 8 h setback on this house | Saves 2.0-3.3 kWh heat at 0 °C (2-3 % of the day); 13.2 kWh must be re-delivered | Lumped RC, C 6.6 kWh/K, H 0.14-0.20 | Calculation | verify R1-C8 | Medium |
| Break-even | Net electricity loss if recovery runs 4.5-10 K hotter (≈7 K at mid H, 0 °C) | 2-3 %/K | Calculation | verify R1-C8 | Medium |
| Mild weather | A "setback" is just a long off-period plus one long run at minimum output: no flow penalty, saves ~3-4 % of the day's heat | Load < P_min | Calculation | verify R1-C8 | Medium |
| Owner regression | Setback-period COP 5.5-8.3 % lower; recovery used ~38 % more electricity than the loss avoided | Midea radiator house | Field anecdote | note 11 | Low-Medium |
| Field analysis | Narrow band (e.g. 18-20 °C) beats large setbacks; setbacks force hotter recovery | HPM + Electrification of Heat | Peer-reviewed field | [Rosenow, Lea & Boni (CIBSE summary)](https://www.cibsejournal.com/technical/bridging-the-heat-pump-efficiency-divide/) | Medium-High |
| Comfort band beats setback | Lowering the band's lower edge 22 → 21 °C cut TABS heating 5-15 %; dead band ≤ 2 K | Simulation | Simulation | [Olesen, REHVA](https://rehva.eu/rehva-journal/chapter/operation-and-control-of-thermally-activated-building-systems-tabs) | Medium |
| Lowering the mean instead | −1 K average ≈ −4.1 kWh/day (~5 % at 0 °C, ~10 % at +10 °C) | This house | Calculation | note 11 | High (arithmetic) |
| Storage loss when pre-charging | ≈ (hold time) / τ: 4-5 % for 2 h, 6-10 % for 4 h, 12-14 % for 8 h charges (+1 K) | τ = C/H ≈ 33-47 h | Calculation + simulation | verify R1-C8; [van Leeuwen 2014](https://www.scitepress.org/Papers/2014/49163/49163.pdf) | Medium |


---

## 4. How the industry controls heating

### 4.1 Weather compensation (curves)

The flow target is a function of outdoor temperature, nearly always with two parameters (slope and offset or two endpoints). Factory defaults are radiator-steep (note 04):

| Brand | Curve form | Defaults / ranges |
|---|---|---|
| Vaillant | Curve 0.1-4.0; community fit T_flow ≈ T_set + 2.55·(HC·(T_set − T_out))^0.78 | HP default 0.60; min flow 15 °C; max 55 °C; switch-off at 16 °C outdoor |
| Viessmann | Slope/level on a heavily low-pass-filtered outdoor temperature | UFH slopes in German practice 0.2-0.5 |
| NIBE | Curve 0-15 | Default 9; min supply 20 °C |
| Daikin | Two points | −10 °C → 35 °C, +15 °C → 25 °C; outdoor averaging 0/12/24/48/72 h |
| Samsung | Two points ("water law") | −10 °C → 40 °C, +15 °C → 25 °C |
| Gree Versati | Two-point line (coil 22 "Weather depend", Words 21/22 endpoints) | R32 Modbus doc: Upper WT 46-60 °C, Lower WT 20-45 °C (defaults 55/40); Versati II "Normal temp" 30-55 / 25-29 (defaults 35/29). **While on, Word 10 writes are ignored.** |

**What a slab house needs:** around 26 °C at 0 °C outdoor and 30-34 °C at −20 °C (Olesen's best TABS winter rule: supply = 0.45·(18 − T_out) + 18 °C, with no room input; [Olesen REHVA](https://rehva.eu/rehva-journal/chapter/operation-and-control-of-thermally-activated-building-systems-tabs)). Feed the curve a 24-48 h mean outdoor temperature. The house's own curve should be fitted from the lowest steady flow that held 22 °C on calm, overcast days.

**Field evidence:** pure weather compensation is the most common control among top-quartile HPM systems (54 % vs 24 % in the bottom quartile), median SPF 4.11-4.14 vs 3.57-3.79 for "significant room influence" (notes 07, 13). Probably partly selection bias (owners who choose pure WC also tune hard).

### 4.2 Room influence

Room feedback must be slow, bounded and integral-only:
- Daikin: modulates LWT target by ≤ ±3 K (0-10 K) from room error; an emitter setting "slow" for floor loops.
- NIBE room factor 0-6, default 2.
- Viessmann: on/off plus strength.
- Vaillant "Expanded": switches the zone off at +2/16 K over target. Owners report it bypasses the energy integral; one log shows a 4.5 h stop followed by a −180 °min catch-up (note 07).
- Gree "T-room" mode: uses the remote room sensor with a 1-5 K band (default 2 K); flow behaviour undocumented.

TABS research (Gwerder/Tödtli at Siemens/Empa) concluded that only **day-to-day** room compensation is worthwhile on slow slabs: feed-forward supply from the 24 h mean outdoor temperature, plus a once-a-day correction from the 24 h mean (and minimum) room temperature ([Gwerder et al. 2009](https://www.sysecol2.ethz.ch/OptiControl/LiteratureOC/Gwer_09_AE_86_1606.pdf)). Raftery's slab loop with a daily reset cut energy up to 35 % against common US practice in simulation (note 05).

### 4.3 Integral start/stop: NIBE degree-minutes, Vaillant energy integral

- **NIBE degree-minutes (DM):** DM accumulates (actual supply − calculated supply) × minutes. Compressor starts at **−60 DM** (range −1000…−30), stops at 0 (owner reports) or when supply exceeds target by **"max diff compressor" 1-25 K, default 10 K**, which forces DM to +1/+2. Additional heat steps at a further offset (Thermia/Danfoss-type: A1 = −60 start, auxiliary at A1+A2 with A2 = −600). Since firmware 2.3.3 (2021) NIBE air units **run at minimum speed after a start** until DM recovers or a timer expires, and the default compressor step difference rose from 60 to 200 DM. S-series 4.0.10 (2025) added "Smart Room Comfort" (ML, no heat curve) and 4.9.4 (2026) an "Auto degree minute" mode to reduce short runs ([NIBE F1145 manual](https://www.manualslib.com/manual/1146229/Nibe-F1145.html); note 04).
- **Vaillant energy integral:** starts at **−60 °min** by default (VWZ AI range −999…+9); stops when delivered heat equals the deficit, or when flow exceeds target + compressor hysteresis (default 7 K, range 0/3-15 K). Owners move the start to −100…−240 for fewer, longer cycles; COP "barely affected", room swings larger ([Vaillant VWZ AI](https://professional.vaillant.co.uk/downloads/aproducts/renewables-1/arotherm-plus/monoblock-heat-pump-system-vwz-ai-heat-pump-appliance-interface-2685948.pdf); [energy-stats.uk](https://energy-stats.uk/vaillant-arotherm-firmware-351-06-07-problems-energy-integral)).
- **Bosch/Nefit:** 150-250 K·min hysteresis.
- **Scaling to this house:** with the loop 3 K below target, −60 is reached in ~20 min. A slab-equivalent threshold is **−300 to −700 °C·min** [calc, note 04], or, in energy terms, a deficit of **≈2.5-6 kWh** (0.4-0.9 K of slab).

### 4.4 Model-based adaptive controls

- **Mitsubishi Ecodan Auto Adaptation** (FTC factory default): estimates required capacity from room and outdoor temperature, predicts the room trajectory, and lowers/holds/raises flow; interval 10 min (manual). One owner's rolling SCOP rose 3.4 → 3.6; others report days of learning and overshoot ([Ecodan product guide](https://renewableheatinghub.co.uk/wp-content/uploads/wpforo/attachments/5124/4908-EcodanFullProduct.pdf); [OEM thread](https://community.openenergymonitor.org/t/mitsubishi-ecodan-performance-using-room-auto-adapt/25558)).
- **Open-source ESPHome Ecodan auto-adaptive controller:** flow target = **return + target ΔT**; never lets the target fall more than **1.0 °C below actual feed** (the compressor cuts out soon after); changes the target by at most **0.5 °C per 30 s** while running ([gekkekoe/esphome-ecodan-hp](https://github.com/gekkekoe/esphome-ecodan-hp/blob/main/docs/auto-adaptive.md)). A Home Assistant FTC6 user fakes the target so target − flow stays < 11 K at cold starts, which stopped 104 Hz sprints.
- **NIBE Smart Room Comfort, Vaillant adaptive curve:** undocumented.

### 4.5 Brand start/stop specifics

| Brand | Stop | Restart | Other |
|---|---|---|---|
| Gree Versati | At min Hz and above setpoint by an undocumented margin, after Heat run time (1-10 min, III only) | setpoint − outlet ≥ ΔT-Heat (2-10 K, default 10) | 3-min lockout; frequency ∝ error; C/P limit (power 0-10 kW / current 0-50 A) |
| Daikin | LWT overshoot 1-4 K (default 1 K) | As soon as LWT < target | Power-consumption limit in kW/A (≥ ~3.6 kW to guarantee defrost on 11-16 kW); DHW max run 5-95 min (default 30), anti-recycle 0-10 h (min 0.5 h); pump modes Continuous / Sample (every 5 min) / Request |
| Panasonic | Outlet > target + 2 K for 3 min | ≥ 3 min later, once outlet < inlet-at-stop − 3 K | Optional-PCB demand control 5-100 %; 2013 quiet mode = fan only |
| Mitsubishi | Thermo-diff upper +3…+5 K (default +5) | Lower −1…−9 K (default −5) | Auto Adaptation; DHW max operation ~30-120 min |
| LG | Temp off +2 K (0…+4) | Temp on −2 K (0…−9) | — |
| Vaillant | Energy integral = 0 or hysteresis 7 K | −60 °min | Noise reduction ≈ rps cap (33 % → ~80 rps on 5 kW) |
| NIBE | DM 0 or max diff 10 K | −60 DM | Soft start since 2.3.3; max frequency in silent mode |

Every brand also caps compressor output under some name (Gree power/current limit; Daikin power-consumption control; Panasonic demand control; Vaillant current limit/noise reduction; NIBE max frequency). Quiet modes are **three different things** (fan-only, compressor+fan, or compressor cap); on Gree it lowers both and makes defrost worse (note 12).

### 4.6 Model predictive control (MPC)

**Academic and lab results** (notes 06, 14; verify R1-C7, R1-C8, R2-C6):
- **Against a well-tuned low curve, measured gains are small:** 125-day twin real ASHP rigs: −4.1 % electricity, COP 4.46 → 4.70, cost −9 % (mostly PV self-use), comfort slightly worse ([Kuboth 2020](https://epub.uni-bayreuth.de/5598/1/energies-13-06016.pdf)). Near-optimal reference in semi-virtual lab: MPC ~5 % cost, rule-based 0 % (Péan).
- **Against poor baselines, large:** field reviews average 22 % energy / 16 % cost for residential tests ≥ 7 days; tests < 1 week average 57 % (short tests exaggerate). Purdue occupied houses −18…−20 %, mostly from avoiding resistance backup.
- **Most "MPC" efficiency is simply the lowest workable flow temperature.** Chalmers: forecast control ~7-9 %, mostly from fitting supply temperature to demand; Aalborg: forecast improved comfort 55 % but COP unchanged; DTI OPSYS: MPC −9…−13 % electricity with COP only +2.1-2.3 % (the rest is heat not delivered: avoided overheating, used gains).
- **Price objectives raise kWh:** Danish 7 kW AWHP, concrete floor, 97 days: cost −12.4 %, electricity +9.5 %, heat +3.7 %, losses on days below ~0 °C ([Thorsteinsson](https://ar5iv.labs.arxiv.org/html/2303.16289)). Glasgow UFH pre-charging ran mostly on the immersion heater.
- **Interface matters:** HiL UFH: MPC writing flow setpoint gave lowest energy but many starts; MPC setting compressor speed gave fewer cycles; both up to −20 % vs a heating curve (Göbel 2023).
- **Load below minimum output needs explicit on/off (mixed-integer)** decisions with minimum up/down times; continuous MPC asking for sub-minimum output produces short bursts (Lee et al. 2019).
- **Closest architecture to this house:** EPFL 2026: Home Assistant + Mitsubishi Ecodan + UFH. MPC plans heat power every 15 min over 8 h with a 2-state (room, floor) ARX model refitted hourly; an **inner loop updates the flow setpoint every minute in bounded steps so delivered energy tracks the plan**; comfort as a user-set Kelvin-hour budget ([Shi & Jones, arXiv 2609.06698](https://arxiv.org/pdf/2609.06698)).
- **Models:** 1-2 states (room + slab) suffice; validate on 6-24 h multi-step error, not one-step; refit weekly on 3-5 weeks; COP models need refits when operating style changes (IEA Annex 58/71, note 14).

**Commercial optimisers (independent evidence thin):** Homely −22 % cost in a Salford lab (53 % with PV+battery); Passiv +17 % space-heating COP (EST trial); Ngenic 20-23 % vendor before/after; Neogrid 5-15 % claim; tado 4/7/11 % for lower curve presets; NIBE Smart Price Adaption and Viessmann features only shift timing; Havenwise and Quatt: no published results.

### 4.7 DIY community practice

From HPM, OpenEnergyMonitor, Home Assistant, Renewable Heating Hub, BuildHub (note 07):
- **Lower the curve 1 K every 2-3 days** until the room cannot hold target on the coldest day, then step back (Energy Stats UK method).
- **Degree-minute / energy-deficit triggers** in Home Assistant; deeper thresholds for fewer, longer runs.
- **Fake targets / ride the flow** to avoid sprint starts (Ecodan < 11 K error; Daikin owners raise overshoot to 3-4 K and keep min LWT ~29-30 °C, which the field data say helps only if runs are under 10-20 min).
- **PumpSteer:** PI loop on a fake outdoor temperature (Kp 2.4, Ki 0.035, clamp ±12 K); **TrueTemp:** learns a per-outdoor correction; HA blueprints shift the curve +1…+3 K on PV and −4 K in evenings. None publish measured results.
- **Only measured case:** Volta (Flanders) retuned curve 33 → 26 °C supply: compressor 2.7 → 1.7 kW; daytime-biased EMS saved 476 kWh over a winter (not weather-normalised); warns that chasing quarter-hour prices multiplies starts.
- **Typical enthusiast operation:** median 0.25 starts/h (~6/day), 93-min runs; best 25 systems 0.23 starts/h, 102-min runs, 30.8 °C heat-weighted flow; worst 25: 0.44/h, 52 min, 39.3 °C.
- **Gree Versati community knowledge is thin:** HA register maps exist (Word 10 setpoint, 30 ΔT-Heat, 43 power limit, coil 17 control source, coil 22 weather mode); nobody has published Versati cycling or COP results ([HA Versati thread](https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916)).

---

## 5. Underfloor heating in a slab

### 5.1 Storage and time constants

- **Storage:** 6.6 kWh per K of slab mean temperature ≈ 5,700 L of water per kelvin; ~38× a 150 L water circuit (notes 03, 15).
- **House time constant** τ = C/H ≈ 6.6/(0.14-0.20) ≈ **33-47 h**.
- **Slab response:** median τ95 for screed UFH (ISO 11855 type A) ≈ 4.9 h; pipe-to-surface delay ~3 h; ~3.2 days to a new room steady state in a Swedish low-energy house ([Karlsson 2010](https://publications.lib.chalmers.se/records/fulltext/111900.pdf)); Gwerder's TABS: 9.9 h with pump on, 100 h with pump off.
- **But the room follows a pulse quickly.** In 29 HPM UFH houses (2,118 multi-hour cycles), the detrended room maximum came 0.1-0.7 h after the compressor stopped (gap R2-G5). Multi-hour lags describe the bulk slab, not the room's response to a pulse.
- **Room swing per kWh carried through an off-period:** median **~0.07 K/kWh** (0.04-0.12) in the HPM houses, i.e. an apparent capacity of ~14-20 kWh/K seen by the room. The lumped 6.6 kWh/K implies 0.15 K/kWh. **This is the key parameter to identify from the house's own logs** (gap R2-G5).

**Cycle arithmetic for this house** (H = 0.14, P_min 3.75 kW, lumped):

| Outdoor | Load | Duty at P_min | 1 K slab swing | 0.5 K slab swing |
|---|---|---|---|---|
| +15 °C | 1.0 kW | 0.26 | 2.4 h on / 6.7 h off, ~2.6 starts/day | ~5.3/day |
| +10 °C | 1.7 kW | 0.45 | 3.2 h / 3.9 h, ~3.4/day | 1.6 h / 1.9 h, ~7/day |
| +5 °C | 2.4 kW | 0.63 | 4.8 h / 2.8 h, ~3.2/day | ~6.3/day |
| 0 °C | 3.1 kW | 0.82 | 9.9 h / 2.1 h, ~2/day | ~4/day |
| ≤ −5 °C | ≥ 3.8 kW | ≥ 1 | continuous | continuous |

### 5.2 Emitter conductance (how warm the water must be)

- **EN 1264 base:** q = 8.92·(θ_floor − θ_room)^1.1 W/m², surface coefficient ~11 W/m²K. At this house's loads (~15-35 W/m²) the floor surface is only 1.5-3.3 K above the room.
- **Water-to-room K_H** (16 mm pipe, cement screed): tile 4.3-4.9 W/m²K at 45 mm cover; laminate 3.0-3.3; floating parquet 2.7-3.0; R 0.15 limit 2.5-2.8. Covering is the largest factor (tile → timber: +1.5…+3 K flow at +2 °C, +4…+7 K at −20 °C). Lithuanian practice ~45-50 mm cover over the pipe (gap G3).
- **Whole-floor UA (130 m² active):** tile ~490-640 W/K; laminate/parquet ~320-470 W/K; prior **U(320, 650), centre 450 W/K**. HPM field quartiles 421/566/752 W/K; the Vilnius HPM system 887 shows ~500-550 W/K.
- **Two-node split:** during a burst of 0.5-4 h, extra heat only has to cross the **water-to-screed conductance K_ws ≈ 1.5 kW/K (1.0-2.2)**, not the full water-to-room UA. Screed-to-room K_sr = 1/(1/UA − 1/K_ws) ≈ 0.65 kW/K. So the forced-cycling lift penalty is only **+1.4-2.3 K at +10 °C (3.5-7 % COP) and +0.4-0.65 K at +2 °C (1-1.6 %)**, not the 3-7 K first estimated (verify R2-C4). Pushing pulses above P_min costs **0.5-0.9 K per extra kW**.

### 5.3 Self-regulation

At fixed water temperature, a room that warms by sun or people automatically draws less from the floor: at +10 °C a 0.5 K room rise cuts floor output ~44 %, 1 K ~84 % [calc]; Karlsson computes that 64-77 % of an unexpected gain is compensated, but **only with supply temperature as the controlled variable and continuous circulation**. Heat-based pulse control (fixed kWh per cycle) partly removes this effect, so a pulse controller must anticipate gains itself.

### 5.4 Reaction speed and intra-day control

With a 3-5 h pipe-to-room delay and τ ≈ 1.5-2 days, any hourly room-temperature feedback without prediction oscillates. Correct the daily energy plan from today's mean room error; within the day act only on hard guards (e.g. start below 21.3 °C, stop above 23.0 °C).

### 5.5 Sun gains

- A low-energy UK house logged > 1 kW of winter solar gain (more than its heat need); 2 h of winter sun raised a room ~0.5 K; sunlit floor patches run ~8 K warmer; overheating can persist 8-12 h after the sun leaves (note 05).
- Skip or shorten morning/midday charges when a sunny day is forecast; on sunny days a pulse ending at 15:00 peaks around 15-16 h and stacks on the solar peak (gap R2-G5).
- Use the PV array's output as the solar sensor in the house model; it beats raw GHI (IEA Annex 58).
- On mild sunny afternoons the MVHR bypass can dump ~0.4-0.9 kW at 5-15 °C outdoor (200 m³/h) instead of a heat-pump off-then-catch-up cycle (gap G8).

### 5.6 Setback and comfort

- No scheduled night setbacks (see §3.8). In mild weather the "off-period" is unavoidable anyway and is simply how the house duty-cycles.
- **Comfort band:** treat **1.0 K detrended peak-to-peak** as the cyclic limit (ISO 7730), room never below 21.5 °C. Plan ~0.5-0.7 K of heat-pump-induced swing; sun and people add 0.5-1 K. Daily room max-min in HPM UFH houses is 0.8-0.9 K even at > 90 % duty. A **±0.25 K band is below the measured noise floor** (0.1 K median, 0.4 K p90 detrended swing) and would multiply starts (gap R2-G5).
- **Energy per pulse:** start trials at ≈4 kWh carried per off-period and step up to 6-8 kWh while watching measured swing (6-10 kWh pulses kept 63 % of HPM cycles under 0.5 K and 91 % under 1.0 K).
- **Undershoot is worse than overshoot:** Kuboth used 0.5 €/Kh for undershoot vs 0.1 €/Kh overshoot; EPFL used Kelvin-hour budgets.

### 5.7 Hydraulic rules for the slab

Keep every loop open (no room actuators, or set them as high limits ≥ 24 °C); no buffer, no low-loss header; balance once (loop flows proportional to area; floor surfaces within 1-2 K by IR thermometer), then lower the curve; avoid large rugs (an R 0.15 rug on 30 % of floor ≈ +1 K at +2 °C).

---

## 6. The Gree Versati specifically

### 6.1 Identify the generation first

Versati III all-in-one 10 kW is the likeliest unit (185 L tank). Nameplate suffix decides the certified data: **NhH (G1), NhH2 (G2), NhH3 (G3)** (HP Keymark certificates 041-K004-09/-17, -11/-16, -31/-26). Minimum output and part-load COP differ by generation (gap G1).

### 6.2 Capacity and COP data

**EN 14825 part-load, 35 °C application, average climate, 10 kW AIO** (certified, gap G1):

| Point | G2 (NhH2) | G3 (NhH3) |
|---|---|---|
| A −7 / ≈W34 | 7.70 kW, COP 2.87 | 7.76 kW, COP 3.15 |
| B +2 / ≈W30 | 4.80 kW, 4.34 | 4.90 kW, 4.59 |
| C +7 / ≈W27 | 3.10 kW, 6.58 | 3.04 kW, 5.67 |
| D +12 / ≈W24 | 3.70 kW, 8.37 | 3.28 kW, 7.34 |

55 °C application (G3): 7.65 kW / 2.29; 4.66 / 3.24; 3.08 / 4.17; 3.21 / 5.24. Cdh 0.93-0.99 everywhere: it equals 1 − P_off/P_el and **contains only the 25 W standby, not start losses**. Off/thermostat-off/standby 25 W; crankcase 25 W (G1/G2) or 0 W (G3). Near-full at +2 °C: 9.55 kW at ≈W35 for 2.82 kW electric (COP 3.39).

**Nominal and full-load tables:** Versati III 10 kW split COP 4.61/3.60/2.59 at A7 W35/45/55 and 2.81/2.23/1.58 at A−7; Versati IV 10 kW monobloc 5.05/4.04/3.18 at A7. Maximum capacity at W35: 9.50 kW (+7), 8.08 (+2), 6.65 (−7), 4.56 kW (−20 °C); W30 at −10/−15/−20 °C: 6.56/5.70/4.85 kW, COP 2.88/2.23/1.87. Capacity is flat from W35 to W45 in deep cold (compressor-limited). Versati IV ~20 % stronger at −20 °C. Colder-climate TOL −22 °C: G2 5.6 kW at COP 1.67; G3 declares 3.15 kW (anomalous). **Balance point for maximum capacity ≈ −10 to −17 °C** (gap G6). Leaving-water envelope tops out at 45 °C at −20 °C.

### 6.3 Relevant settings and Modbus registers

Protocol: RS485, 9600 8N1, RTU on the wired controller; function codes 01/03/0F/10; last command wins; mode changes only with the unit off; writes act immediately and are stored after 30 min ([Modbus V1.5](https://man.kievclimate.com/man/Gree/Versati/Versati%20III/R32_Versati%20Modbus%20V1.5.pdf); V1.7 marks 33/34 read-only). Register maps differ by protocol version (1.0-2.2). Temperatures read ×0.1 in working HA configs although the document says 1 °C.

| Item | Register | Notes |
|---|---|---|
| Flow setpoint (WOT-Heat) | Word 10 | Ignored while weather-dependent mode (coil 22) is on |
| Tank setpoint | Word 13 | 40-80 °C, default 50 |
| T-Eheater (backup heater outdoor threshold) | Word 14 | −20…18 °C, default −15 (R32 doc); Versati II+ manual −7 °C |
| T-HP max | Word 16 | 40-55 °C, default 50 |
| Curve endpoints | Words 21/22 | Ranges vary by generation; test acceptance |
| ΔT-Heat (restart hysteresis) | **Word 30** | 2-10 K, factory 10 K; house 4 K; Gree Poland recommends 2-4 K |
| Heat run time | Word 34 | 1-10 min; conditional stop delay; absent in V1.7 and Versati IV |
| Optional E-heater sets / logic; tank-heater logic | Words 3, 37, 36 | Logic 1 = heater replaces compressor (no simultaneous running); Logic 2 = together |
| Current limit / power limit values | Words 38 / **43** | 0-50 A (16 A) / 0-10 kW ×10 (3.0 kW). **Mode selector (Off/Current/Power) is panel-only, factory Off.** Gree frames it as a supply-current (input) cap; scope over heaters, DHW, defrost undocumented |
| Max frequency | Word 72 (+ coil 40) | From V2.2 map; **reads 0 on Versati III**; not usable there |
| Status | Word 117 | 6 = hot water |
| Coil/defrost temperature | Word 120 | |
| Economiser in/out | Words 122/123 | Two-stage gas injection |
| Discharge pressure (as sat. temp) | Word 124 | |
| LWT at plate exchanger / after heater / return | Words 125 / 126 / 127 | Which one the restart uses is unknown |
| Set / running compressor Hz | **Words 142 / 143** | 0-100 Hz, 1 Hz steps; the most important log |
| Control source / weather mode / quiet mode | Coils 17 / 22 / 21 | |
| Compressor / defrost / oil return / crankcase heater | Coils 80 / 86 / 87 / 84 | |
| Flow switch / backup heaters / tank heater / pump / 3-way valve | Coils 170 / 171-172 / 173 / 175 / 178 | |
| **Not available** | — | No water flow, heat output, capacity, electrical power or suction pressure register (gap R2-G7) |

### 6.4 Known behaviours

- Compressor frequency ∝ (setpoint − LWT); gain unpublished (all generations).
- Restart on setpoint − outlet ≥ ΔT-Heat; observed 4-5 K with Word 30 = 4 (perhaps the plate outlet vs the post-heater sensor).
- Stop at minimum Hz plus standby-zone margin (unpublished) for Heat run time; a lower setpoint mid-run should ramp down, not stop instantly (gap G2).
- 3-min restart lockout; no documented 6-min hold on III/IV.
- **Pump:** ΔT-modulated, 4-75 W; manuals say it stops after the compressor in normal shutdown. If so, **the outlet sensor reads stagnant water during off-periods** that cools toward plant-room (AIO/split) or outdoor (monobloc) temperature, and the 4 K restart becomes a timer set by cabinet cooling rather than slab cooling (gap R2-G1). No pump-mode setting exists.
- **Defrost:** accumulated run counter not reset on stop; coil threshold; suction pressure used; fan follows suction pressure; quiet mode shortens intervals to the ~50-56 min clock floor.
- **Backup heater:** switches on outdoor temperature alone (no water/room/run-time condition). Logic 1 below T-Eheater *replaces* the compressor. A "1 set, Logic 1, −7 °C" configuration costs ~1,170 kWh/season; at −10 °C ~500, −15 °C ~100, −20 °C ~17 kWh (H 0.17; 2025/26-type winters 1.5-2.5× worse below −10 °C) (gap G6).
- **Hot water:** priority default; 185 L tank, 0.215 kWh/K; ΔT-hot water 2-8 K (default 5; 2-25 on newer panels); no max-run or anti-recycle timer; "Hot water control mode = Manual" fixed frequency only on second-generation monoblocs.
- **Memory:** values memorised after 30 min; endurance unpublished; write only on change.

### 6.5 Levers available to us

| Lever | What it can do | Caveats |
|---|---|---|
| Flow setpoint (Word 10) | Power request and temperature target; start and stop runs | Start needs ≥ ΔT-Heat gap; large gaps = sprint |
| ΔT-Heat (Word 30) | 2-4 K: gentler self-restarts at lower setpoints. 8-10 K: firmware cannot restart itself during planned off-periods | 4 K + 30-min rewrites combines large start steps and unplanned restarts |
| C/P power limit (Word 43 after panel mode = Power) | Input cap, e.g. 1.2-1.6 kW above ~0 °C, 2.5-3 kW at −5…−10 °C, off/5+ kW below −15 °C | Effect on defrost and DHW untested; Daikin needs ≥ 3.6 kW for defrost on larger units |
| Heat run time (Word 34) | 10 min widens the window to rescue a run with a corrective write | Not a minimum run; may not exist on the unit |
| Built-in curve (coil 22, Words 21/22) | Fully native weather compensation, no external writes | Floor ranges may refuse low endpoints; ignores Word 10 |
| Quiet mode (coil 21) | Noise | Avoid at −5…+5 °C humid; raises defrost frequency |
| Thermostat input (dry contact) | Home Assistant calls heat on/off with no Modbus writes | Terminal and voltage unverified on AIO |
| Tank setpoint (Word 13), T-HP max, ΔT-hot water, heater logic | Planned single daily DHW reheat, compressor-only DHW, Logic 2 for disinfection | Mode changes need unit off |
| Pump | None | No setting; do not interfere (flow-switch trip needs power cycle) |

---

## 7. Diagnosis: why this house may run hot water and cycle a lot

Each hypothesis with the measurement that would confirm or refute it. Log at 10-30 s for at least a week covering a +5…+10 °C spell and a humid −2…+3 °C spell: Words 10, 13, 117, 120, 124, 125, 126, 127, 142, 143; coils 21, 22, 80, 84, 86, 87, 170, 171, 172, 173, 175, 178; electrical power from a true-RMS meter (the unit has no power register); room temperature from two or more sensors; outdoor T and RH.

| # | Hypothesis | Mechanism | Confirming measurement | Likelihood |
|---|---|---|---|---|
| H1 | **Start-kick sprints.** Every restart begins with setpoint ≥ outlet + 4 K, so the firmware runs fast and hot. | Proportional-on-LWT frequency law + ΔT-Heat 4 K | Word 142/143 near max for the first 10-30 min of runs; power ~3 kW; Hz falls as outlet approaches setpoint. Step test: setpoint at outlet +1/+2/+3/+5 K for 10 min each, plot steady Hz and power vs error | High |
| H2 | **30-min setpoint writes sit above what the slab needs.** Setpoints of 31-36 °C vs a slab needing ~28-31 °C (laminate) or ~26-28 °C (tile) | Controller targets "start-able" setpoints and holds them | Compare realised mean LWT while running with the floor's minimum outlet from identified K_ws and UA (§5.2). A gap > 3 K is avoidable lift | High |
| H3 | **Stagnant outlet sensor times the restarts.** With the pump stopped, the outlet cools toward cabinet/plant-room temperature, so the setpoint must sit 4-5 K above stagnant water, not slab water | Pump stops after compressor (manual text) | Coil 175 = 0 during off-periods; outlet decays exponentially toward plant-room temperature with a time constant unrelated to outdoor temperature; first stable return after restart differs from the off-period outlet | Medium |
| H4 | **Catch-up after deficits.** DHW cycles, room-feedback reactions, solar overshoot followed by evening deficit, or any setback make the controller raise the setpoint | Deficit → high setpoint → sprint | Correlate high-setpoint episodes with preceding DHW (status 6), room-error excursions and sunny afternoons | High |
| H5 | **The ~3 kW draw may not be the compressor at all.** Alternatives: C/P power limit already set to Power at its 3.0 kW preset (flat-topped draw), backup heater (coils 171/172), tank heater (coil 173, 3 kW, disinfection or tank target > T-HP max), meter scope, different model | Verify R1-C3 | Draw that flat-tops at exactly ~3.0 kW → C/P limit set; heater coils = 1 → heater logic; Hz near max with heaters off → H1 | Open |
| H6 | **Manifold mixing group or buffer** makes the unit run hotter than the floor receives | Thermostatic mixer with its own pump | Unit outlet vs manifold supply during a steady 30-min run (> 1 K gap = mixing); return jumping within 1-2 min of start = bypass | Unknown, high value |
| H7 | **Floor is weaker than assumed** (thick screed, wide pitch, floating parquet on foam, rugs, closed loops) | Low UA forces higher water | Identify UA from long cold-weather runs (not mild short runs, which overstate UA ~1.6×); check all loops open; read coverings | Medium |
| H8 | **Hot-water slug restarts.** After DHW, 45-55 °C water returns to the loop; outlet reads above space-heating setpoint, unit stops/waits, then restarts with a deficit | DHW priority + 3-way valve | Minutes from DHW end to next SH start; outlet trace after status 6 → SH | Medium |
| H9 | **Cycling is structural, not a fault.** P_min (3.7-3.8 kW, possibly rising to ~4.4 kW at +12 °C) exceeds load above roughly −5…+3 °C | Turndown limit | Steady minimum heat output (Hz floor) at three or more outdoor temperatures; count starts per day vs outdoor temperature | High (as fact) |
| H10 | **Komfovent fights the slab or adds resistive heat.** AHU supply/extract target 20 °C cools the house on mild afternoons; its integrated electric heater runs at COP 1 (one owner measured 3-4 kWh/day at +1…+10 °C) | Default AHU settings | Komfovent registers: heat-exchanger type 955, heater power 922 and energy 937-938, setpoints, ECO settings | Medium, cheap to check |
| H11 | **Cold-weather heater misconfiguration** (Logic 1 with T-Eheater −7…−10 °C replaces the compressor) | Outdoor-only heater switching | Read Words 3, 14, 37; on the first night below T-Eheater check coil 80 drops while 171 rises | Unknown; largest cold-weather loss if present |
| H12 | **Defrost stops and restarts amplify catch-ups** on humid 0…+4 °C days | Post-defrost LWT dip read as a deficit by external logic | Coil 86 timeline vs setpoint raises and stops within 15 min after defrost | Medium |

**What the logs will show if the main diagnosis is right:** mild-weather runs with Hz near maximum for tens of minutes after each start, mean running LWT 3-8 K above the floor's need, electrical input ~2.5-3 kW instead of ~0.7-1.0 kW, and catch-ups clustered after DHW and after room-error excursions. A healthy target looks like: input 0.7-1.2 kW at +2…+10 °C, mean running LWT ≈ floor need + 0-1 K, 2-6 starts/day in mild weather with runs ≥ 60 min.

---

## 8. Candidate control strategies to build and test in a simulator

Eleven strategies, from "change settings only" to an economic MPC. They differ in **who decides when to run** (firmware, a curve, an integral, a daily budget, an optimiser, a room model), **how starts are executed** (setpoint kick, ride, cap, thermostat contact) and **what is optimised** (lift, starts, cost, PV). Several share modules (§8.12). Default parameters are starting points for simulation, not tuned values.

Common notation: T_out24 = 24 h mean (or forecast mean of the next 24 h) outdoor temperature; LWT = Word 125; RWT = Word 127; P_min(T_out) = minimum heat output; L̂ = estimated load = Ĥ·(22 − T_out) − gains; floor-need temperature T_need = T_slab_est + P_min/K_ws + ΔT_loop/2.

### S1. Unit settings only ("let the Gree do it")

- **Idea.** No external control in normal operation. Tune the Versati's own curve, restart hysteresis and power cap so the firmware cycles gently around a low line.
- **Algorithm.**
  - Weather-dependent mode on (coil 22 = 1). Line: Lower AT −20 °C → Upper WT 33 °C; Upper AT +15 °C → Lower WT 25 °C (test whether the firmware accepts endpoints this low; if not, use the lowest accepted and a fixed Word 10 instead).
  - ΔT-Heat (Word 30) = 8 K (variant: 3 K).
  - C/P limit = Power (panel), Word 43 = 1.5 kW year-round (variant: 1.5 kW above −3 °C, 3.0 kW below, switched by one daily write).
  - Heat run time = 10 min if present. Quiet mode off. Weather mode supplies T_out (unit's own sensor, no damping).
  - DHW: tank 47 °C, ΔT-hot water 8 K, disinfection 60 °C fortnightly at 13:00 with Logic 2.
  - Home Assistant only monitors; optional ≤ 6 endpoint writes per day (+1 K in PV surplus, −1 K at night).
- **Mechanism and evidence.** Pure weather compensation is the most common control among top HPM systems (median SPF 4.11 vs 3.57-3.79 for room-influenced; notes 07, 13). A large ΔT-Heat lengthens off-periods (the Mitsubishi −9 K / Vaillant −100 °min lever). The cap removes sprint starts.
- **Expected effect.** Electricity −5…−15 % vs today in 0…+10 °C weather (from lower curve and no sprints; Low-Medium). Starts: fewer (long off-periods, 2-5/day). Water: ≤ curve + start overshoot. Comfort: no feedback, so ±0.3-0.5 K extra drift; sunny-day overshoot.
- **Risks.** Firmware may refuse low endpoints (R32 map lists Upper WT ≥ 46 °C); no T_out damping (curve follows night lows); with ΔT-Heat 8 K and a stagnant outlet the restart timing is cabinet-driven; cap effect on defrost/DHW unknown; no learning.
- **Simulator must model.** Firmware weather mode with unit's own instantaneous T_out; restart/stop rules incl. ΔT-Heat and standby zone; outlet-sensor stagnation during pump-off; power cap on input; firmware DHW priority and reheat hysteresis.

### S2. Pure weather compensation, "low and slow" (external curve, firmware cycles)

- **Idea.** Home Assistant computes a low curve from damped outdoor temperature and writes it only when it changes; the firmware's own hysteresis does the cycling around that low target.
- **Algorithm.**
  - T_set = clamp(26 + 0.4·(0 − T_out24), 24, 35) °C (≈ 26 °C at 0 °C, 30 °C at −10 °C, 34 °C at −20 °C; Olesen-like).
  - Round to the register resolution; write Word 10 only on change, at most hourly.
  - ΔT-Heat = 2-3 K (so restarts happen near slab temperature, not 4-5 K below the target). Power cap 1.5 kW above −3 °C.
  - Below the balance point the firmware runs continuously at the curve; above it, it cycles itself.
- **Mechanism and evidence.** Lift is the dominant lever (§3.1). Gree Poland recommends ΔT-Heat 2-4 K and 30-35 °C for UFH. HiL UFH work found an optimum near 3 K hysteresis with SCOP flat within a few % (Göbel).
- **Expected effect.** Electricity −8…−18 % vs today in mild weather (mean running LWT down 3-6 K; Medium-Low). Starts: more than S1 (perhaps 6-15/day in mild weather) but runs mostly ≥ 30 min. Comfort: feed-forward only; risk of slow drift.
- **Risks.** Small ΔT-Heat with stagnant-outlet behaviour may create many short self-restarts; curve error is never corrected; solar overshoot.
- **Simulator must model.** Same firmware details as S1; start counts and short-run penalties; damped-outdoor input; curve-error sensitivity (house H uncertain ±20 %).

### S3. Weather compensation with slow room-feedback integral trim ("TABS classic")

- **Idea.** S2 plus a once-a-day parallel shift of the curve from the 24 h mean room error (Gwerder/Raftery day-to-day compensation).
- **Algorithm.**
  - Base: S2 curve.
  - At 06:00: e = 22.0 − mean(T_room over last 24 h, ≥ 2 sensors, DHW periods and 60 min after excluded).
  - Offset Δ ← clamp(Δ + k·e, −3, +3) K with k = 1.5 K per K of error, deadband ±0.1 K; apply the change in ≤ 0.5 K steps over ~12 h.
  - Low-side guard: if the 24 h minimum room < 21.4 °C, add +0.3 K extra.
  - Never react to instantaneous room error; freeze the integral during defrost and DHW.
- **Mechanism and evidence.** TABS research says only day-to-day room compensation is worthwhile on slow slabs; feed-forward does the heavy lifting ([Gwerder 2009](https://www.sysecol2.ethz.ch/OptiControl/LiteratureOC/Gwer_09_AE_86_1606.pdf); [Olesen](https://rehva.eu/rehva-journal/chapter/operation-and-control-of-thermally-activated-building-systems-tabs); Raftery up to −35 % vs US practice). Aalborg: feedback ~13 % better than pure curve in simulation.
- **Expected effect.** Like S2 on electricity (−8…−18 %), better mean comfort (24 h mean within ±0.15 K after convergence), converges in 3-7 days. Starts as S2.
- **Risks.** Slow to respond to sunny/cloudy sequences; integral wind-up after holidays or open windows; needs good room sensing.
- **Simulator must model.** Two-node house with sun and internal gains; realistic room-sensor lag and noise; multi-day weather sequences; DHW masking.

### S4. Slab-scaled degree-minute controller (NIBE/Vaillant logic, rescaled)

- **Idea.** Replace the firmware's 4 K restart rule with an integral of flow-temperature deficit against the curve, sized for a 6.6 kWh/K slab, and execute starts and stops explicitly.
- **Algorithm.**
  - Target: S3 curve T_c.
  - Every minute while circulating (or from a slab-state estimate when the pump is off): DM += (T_meas − T_c)·Δt, where T_meas = return after ≥ 10 min of circulation, else model estimate.
  - **Start** when DM ≤ −400 °C·min (tune −300…−700 toward 4-6 starts/day at +5 °C): write setpoint = LWT + ΔT-Heat + 0.5 K, then hand over to the soft-start module (§S6) within 2 min.
  - **Running target** = max(T_c, RWT + 2.5 K), raised ≤ 0.5 K per 10-15 min.
  - **Stop** when DM ≥ 0 (or ≥ +100 for longer runs) or LWT > T_c + 5 K: write setpoint = LWT − 2 K; then **park** at min(LWT − ΔT-Heat − 1 K, …) above anti-freeze limits so the firmware cannot self-restart. With park, ΔT-Heat can be 2-4 K.
  - Constraints: min run 30 min, min off 20 min, ≤ 3 starts/h.
- **Mechanism and evidence.** Industry standard for unavoidable cycling; NIBE's own 2021 change added soft starts and larger step differences (note 04). −60 defaults would give ~20-min off-times here; the slab-scaled threshold yields multi-hour cycles.
- **Expected effect.** Electricity −10…−20 % vs today in mild weather (lower running LWT and no sprints; Medium-Low). Starts 3-6/day mild, runs 1-4 h. Comfort similar to S3 with daily trim on T_c.
- **Risks.** DM needs a meaningful flow measurement; if the pump stops, the integral runs on a model; park setpoint semantics must be verified (does a below-outlet setpoint keep the unit off without side effects?); defrost dips must be masked.
- **Simulator must model.** Pump on/off behaviour and sensor stagnation; the parking and stop semantics; defrost dips; start transient.

### S5. Energy-budget block scheduler: long runs at minimum output, slab as storage

- **Idea.** Decide each day's heat in kWh, deliver it as a few long blocks at (near) minimum output and the lowest workable water temperature, sized by the allowed slab/room swing. The concrete-core pulse-width modulation idea moved from the pump to the compressor.
- **Algorithm.**
  - Rolling every 30-60 min: E_need(next 24 h) = Ĥ·Σ(22 − T_out,fc)·Δt − ĝ_sol·Σ PV_fc·Δt − Q_int + Ĉ·(22 − T_room_est) + DHW deficits.
  - Regime: if mean load ≥ P_min(T_out): continuous mode (see §8.12 cold branch).
  - Else: per-block energy E_blk = swing_allow / b, with b = room swing per kWh (prior 0.10 K/kWh, identify 0.04-0.15) and swing_allow = 0.55 K → ~4-5 kWh to start, raise to 6-8 kWh if measured swing allows. N = ceil(E_need / E_blk), 2-6 blocks; block length = E_blk / (P_min − L̂) ≥ 90 min (hard floor 45 min).
  - Placement: default evenly spaced; with S8 timing, in warm/PV hours.
  - Execution: start kick (LWT + ΔT-Heat + 0.5 K) → within 2 min ride at T_run = max(T_need, LWT + 1…1.5 K), ≤ 0.5 K/5 min upward, never below LWT − 1 K; power cap ~1.3-1.5 kW. End when delivered heat (P_min × time, or metered) reaches E_blk, or room ≥ 22.6 °C; then park.
  - Guards: start if room < 21.4 °C; stop if > 23.0 °C (23.3 °C with PV surplus).
  - Daily correction of Ĥ from the 24 h room error (as S3).
- **Mechanism and evidence.** Removes catch-ups by never falling behind; keeps water at floor need; runs 1.5-4 h are on the field plateau (start costs < 1-3 %). Field: best UFH systems cycle ~7×/day with 1-2 h runs at ~27-29 °C (note 07). EPFL's energy-tracking inner loop is the field-proven analogue.
- **Expected effect.** Electricity −10…−25 % vs today in 0…+10 °C weather (Medium-Low). Starts 2-6/day mild. Mean running LWT ≈ floor need + 0-1 K (28-31 °C at +2 °C on laminate). Comfort: detrended swing 0.3-0.7 K by design.
- **Risks.** Load model error (H ±20-50 %), sun; riding stability on Gree (standby-zone stop, oscillation); Modbus write cadence 2-5 min during transitions; floor-need estimate wrong if K_ws misidentified.
- **Simulator must model.** Two-node slab/room with identified b; K_ws vs run length; P_min(T_out); firmware frequency law and stop rule; forecast errors; heat-delivered estimation error (±10-25 % without meter).

### S6. Soft-start / setpoint riding with compressor-power limiting (inner loop)

- **Idea.** A minutes-scale inner loop that turns any outer decision ("run now at ~P_min") into a gentle compressor trajectory. Can be used alone with the current outer logic, or under S4/S5/S8/S9/S11.
- **Algorithm (three variants to compare).**
  - **6a Cap-and-step:** power cap on (Word 43 = 1.4 kW above −3 °C; 2.5-3.0 kW at −5…−10 °C; off/5 kW below −15 °C). Start with LWT + ΔT-Heat + 0.5 K; once running write the slab-based T_run (27-31 °C) and leave it. Stop with LWT − 2 K.
  - **6b Glide:** as 6a, but within 1-2 min of start set target = LWT + 1…2 K and follow LWT upward ≤ 0.5 K per 1-5 min, never below LWT − 1 K. Ceiling T_need + 2 K.
  - **6c Return + ΔT (Ecodan auto-adaptive style):** while running, target = RWT + ΔT_tgt, ΔT_tgt 2-4 K chosen from the outer loop's requested power (ΔT_tgt ≈ P_req / ṁc_p), clamp 25-35 °C, step ≤ 0.5 K / 30 s-1 min, floor LWT − 1 K.
  - All: ignore samples during defrost and 15 min after; write only on change (register resolution); verify that writes are not EEPROM-stored per write (stored after 30 min).
- **Mechanism and evidence.** Gree frequency ∝ error (all manuals); NIBE soft-start since 2021; Ecodan open-source riding with −1 K floor and 0.5 K/30 s; HA Ecodan fake target < 11 K stopped 104 Hz starts (note 12). Removing near-max operation is worth 15-25 % on the burst kWh (verify R1-C1, R2-C2), mostly through lower LWT.
- **Expected effect.** On burst hours −15…−25 % electricity; whole-day −2…−6 % (low case) to −11…−13 % (catch-up-dominated days) until the burst share is measured. No 3 kW draws. Starts unchanged by itself.
- **Risks.** Hunting/zig-zag (Samsung ~400 W oscillation); unintended stop if the error sits in the standby zone; cap may stretch defrost or DHW; on Versati III no frequency cap register works, so the cap is the only hard limit.
- **Simulator must model.** Frequency law with gain and time constant as parameters (unknown: sweep 0.5-3 kW per K of error); power cap semantics (input); minimum Hz; standby-zone width and Heat run time; condensing approach vs output (COP vs speed); write latency.

### S7. Thermostat-contact control (no Modbus writes in normal operation)

- **Idea.** Cleanly separate "when" (Home Assistant) from "how" (Gree): HA closes the unit's thermostat input for long calls; the unit runs to a fixed low WOT-Heat or its own low curve.
- **Algorithm.**
  - Thermostat = Air (panel). Fixed WOT-Heat 29 °C (or native low curve as S1). ΔT-Heat 8-10 K (no self-restarts during a call). Power cap 1.5 kW.
  - Call logic: an energy-budget or degree-minute decision (S4/S5 timing) → relay on for 2-6 h; off otherwise; min on 60 min, min off 45 min.
- **Mechanism and evidence.** Documented Gree thermostat function (note 08 C3). Removes EEPROM questions and Modbus failure modes. Thermostat on/off with a *room* trigger is the classic failure mode, so the trigger must be energy-based, not room-band.
- **Expected effect.** Electricity −8…−18 % (similar to S2/S4 if the fixed WOT is near floor need). Starts 2-5/day. Water fixed (no per-run optimisation; higher than needed in mild weather, lower than needed below about −10 °C unless a curve is used).
- **Risks.** Wiring and voltage (some Gree inputs are 230 VAC); start still kicks (gap between stagnant outlet and WOT); no riding possible; pump behaviour at call end.
- **Simulator must model.** Firmware behaviour with thermostat input (start when call + water below WOT − ΔT-Heat?); fixed WOT vs need; long-call comfort swing.

### S8. Forecast timing: put the unavoidable runs in warmer, drier, sunnier hours

- **Idea.** Keep S5's daily energy budget and low water, but choose *when* blocks run to buy COP (warmer air), fewer defrosts (lower RH, warmer coil) and free PV, without raising water temperature.
- **Algorithm.**
  - Hourly forecast (Open-Meteo-like): T_out, RH, GHI/PV, (optional price).
  - Score each hour h: cost_h = 1/COP(T_out,h, T_run) × (1 + d(T_out,h, RH_h)) × p_h, with defrost multiplier d ≈ 0.006 per K below +5 °C at RH ≥ 90 % (half at 80-90 %), plus a defrost table (§8.13); p_h = 1 (efficiency mode) or price/PV value.
  - Place the N blocks (from S5) into the cheapest feasible hours subject to: block ≥ 90 min, ≤ 1 K slab drift between blocks, ≤ 6 h coast, comfort guards, no block start within 10 min of tariff/PV transitions.
  - Solar anticipation: if tomorrow's GHI ≥ 1.5 kWh/m² and room ≥ 22.0 °C, no overnight pre-charge; if room ≥ 22.3 °C by 10:00 on a sunny forecast, skip the midday block.
  - Regime rule: below ~0 °C daily mean, no shifting (continuous).
  - Storage allowance: pre-charge up to +0.5 K only when the forecast benefit exceeds storage loss (~5-10 % for 2-4 h, 12-15 % for 8 h) plus any flow penalty.
- **Mechanism and evidence.** Warmest 6 h: +1.0-1.9 K Dec-Feb, +3.7 K March; defrost per kWh falls 2-5× from +1 °C to +4 °C at RH ≥ 90 % (gap R2-G4); Kuboth's PV shift doubled self-consumption.
- **Expected effect.** On top of S5: −0.5 % Dec-Feb, −1.5…−3.5 % over Oct-Apr (larger vs a night-heavy baseline); defrost −1…−3 % of heating electricity; PV self-use up strongly Oct-Nov and Feb-Apr. Starts unchanged. Comfort: room peaks ~0.5 h after block end, can stack on sun.
- **Risks.** Forecast error (cloud), solar overheating, larger daily swing; gains small in mid-winter; on net metering the cost value is small.
- **Simulator must model.** Hourly diurnal T and RH (ERA5 Vilnius), defrost dependence on T, RH and load; PV/solar gain with forecast noise; storage losses; comfort with sun.

### S9. Economic optimiser / MPC with a COP map and start costs

- **Idea.** A mixed-integer optimiser plans on/off and heat rate per 15-30 min over 24-36 h, minimising electricity (or cost) with an explicit COP(T_out, T_flow, Q) map, start cost, defrost cost, DHW events and PV/tariff values; an inner loop (S6) executes the plan.
- **Algorithm.**
  - Model: 2 states (T_room, T_slab), parameters Ĉ_s ≈ 6.6, C_i 0.5-2 kWh/K, K_sr, Ĥ, ĝ_sol (PV proxy), fitted weekly on 3-5 weeks; Kalman filter for T_slab; validated on 6/12/24 h RMSE ≤ 0.3-0.5 K.
  - Decision per step k: u_k ∈ {0,1}, Q_k ∈ [P_min(T_out,k), P_max(T_out,k)]·u_k, DHW block d_k (mutually exclusive with SH).
  - Flow needed: T_flow,k = T_slab,k + Q_k/K_ws + Q_k/(2ṁc_p).
  - Electricity: E_k = Q_k/COP(T_out,k, T_flow,k, Q_k) · (1 + defrost(T_out,k, RH_k, Q_k)) + standby.
  - Objective: Σ price_k·E_k (price = 1 in efficiency mode; PV surplus at export value) + c_start·Σ starts (0.15 kWh_el-eq) + comfort penalty (undershoot 5× overshoot, or Kh budget ≤ 1 Kh/day below 21.6 °C) − terminal slab-energy value.
  - Constraints: min up 30-60 min, min down 20-60 min, ≤ 3 starts/h, room 21.5-22.8 °C hard, T_flow ≤ 35 °C (38 °C below −15 °C).
  - Re-solve every 15-30 min; horizon 24-36 h; fallback to S3 if stale > 30-60 min or model RMSE degrades.
- **Mechanism and evidence.** MPC's documented gains vs a tuned curve are ~4-5 % energy (more in cost); most efficiency comes from low flow temperature; mixed-integer form is required when load < P_min; EPFL's HA+Ecodan architecture is the closest proven analogue.
- **Expected effect.** vs S5/S8: 0-5 % kWh; vs today: −10…−25 %; cost −3…−15 % on a variable tariff, ~0 on net metering. Starts 2-6/day. Comfort best of all if the model holds.
- **Risks.** Model upkeep (COP model refits; negative solar coefficients from online learning); forecast errors (overheating on sunny days); price objective raising kWh; Gree interface (flow-setpoint actuation can cause many starts in HiL); complexity.
- **Simulator must model.** Everything in §8.13; plant-model mismatch (simulate with a richer truth model than the optimiser's); forecast noise; sensor noise; tariff schemes.

### S10. PV- and battery-aware surplus dispatcher (rule-based)

- **Idea.** No optimiser: a fixed priority order for each kWh of PV surplus and a regime-aware battery rule, layered on S5.
- **Algorithm.**
  - Classify day: mild (mean load < P_min) vs cold.
  - Mild days: start the first SH block when forecast surplus ≥ 1.0-1.3 kW (≈ input at P_min) for 15 min; allow room to +0.5 K (≈ 1.5-2 kWh electric stored) by mid-afternoon; flow ≤ curve + 2 K.
  - Cold days: never speed up for PV; let the battery charge; discharge into the heat pump 17-24 h; keep 10-20 % reserve.
  - Surplus priority: (1) SH at minimum speed if due; (2) DHW top-up if due within 24 h (compressor, ≤ 47 °C); (3) battery to the level needed until next PV; (4) slab +0.5…+1 K at minimum speed; (5) legionella electric finish; (6) export.
  - On ESO returned-energy (0.0726 €/kWh) put export ahead of battery if measured round trip < 0.85 or > 250 cycles/yr. Never grid-charge the battery for the heat pump on a flat tariff.
  - evcc-style hysteresis: enable at 1.3 kW surplus held 5 min, disable at 150 W import held 20 min; ≥ 10-min holds.
- **Mechanism and evidence.** Slab stores only ~1.5-2 kWh electric per K; absorbing surplus by speeding up costs ~25-35 % per kWh (speed + flow + storage) vs ~8-13 % battery loss (HTW Berlin 2026 tests); Langer & Volling optimiser behaves the same way (gap R2-G3).
- **Expected effect.** Electricity unchanged to −2 %; grid import and cost down in Oct-Nov and Feb-Apr (value depends on settlement scheme; near zero in Dec-Jan). Starts unchanged.
- **Risks.** Battery standby (4-64 W) in winter; LFP charging derated near 0 °C if unheated; battery metering rules under net metering undocumented; tariff assumptions wrong by 3-4× on net metering.
- **Simulator must model.** PV yield (PVGIS-like, snow), house base load, battery round-trip efficiency by power (lower below 300 W), standby, tariff/settlement schemes.

### S11. Room-trajectory adaptive control (Auto-Adaptation style)

- **Idea.** Instead of a curve or an energy budget, continuously estimate the capacity the house needs from the room temperature's recent trajectory and predicted path, and nudge the flow target accordingly (Mitsubishi Auto Adaptation; NIBE Smart Room Comfort).
- **Algorithm.**
  - Every 30-60 min: fit room slope over the last 3-6 h (detrended for DHW/defrost); predict T_room(t+6 h) with the 2-state model and current flow.
  - If predicted < 22.0 − 0.2: raise target 0.5 K (cap +3 K over a slab-safe floor); if > 22.0 + 0.2: lower 0.5 K; within band: hold.
  - Learned per-outdoor-bin correction table (TrueTemp idea) updated nightly so the "hold" value converges to the house's own curve.
  - Starts and stops via firmware hysteresis (ΔT-Heat 3 K) or via S6 riding.
- **Mechanism and evidence.** Factory default on Ecodan FTC; one owner +6 % rolling SCOP; others report learning-phase overshoot; NIBE abandoned curves in S-series 4.0.10. No independent measured comparison.
- **Expected effect.** Electricity −5…−15 % vs today (Low). Starts as firmware dictates (4-10/day mild). Comfort good in steady weather, poorer in sun transitions.
- **Risks.** Slab lag (3-5 h pipe-to-room) can cause oscillation unless the prediction model is good; tends to run higher flows with larger over/undershoot (owner reports); learning time days-weeks.
- **Simulator must model.** Realistic room/slab lag; sensor noise; sun; adaptation over multi-week weather sequences.

### 8.12 Shared modules (used by several strategies)

- **Cold-weather branch** (daily mean load ≥ P_min, roughly below −5…+3 °C, or −1…+5 °C if P_min rises in warm air): run continuously; target = curve value or return + 2-3 K; change ≤ 0.5 K per 30-60 min; stop only on slab-energy surplus. Below the capacity balance point (−10…−17 °C) write the lowest LWT that keeps the compressor at maximum (≈ return + 5-7 K); never 39 °C "to catch up".
- **Backup-heater gate:** heater Logic 2, T-Eheater −20 °C (or Off); enable only if T_out < −12 °C AND compressor ≥ max Hz for ≥ 60-180 min AND room < target − 0.7 K and falling, outside defrost + 15 min; disable at target − 0.3 K or T_out > −10 °C; ≥ 30 min on/off.
- **DHW scheduler:** tank 47 °C (52 °C if HN 136 compliance or vulnerable occupants); one planned reheat per day by holding Word 13 at 40 °C outside the window and 47 °C inside it; window 12:30-14:00 Mar-Oct, end of the main SH block Nov-Feb; ΔT-hot water 8 K; T-HP max 55 °C; HA timers: max DHW run 40 min (> 0 °C) / 60 min (< 0 °C), anti-recycle 4 h unless top tank < 38 °C, 45-60 min of SH priority after DHW with no flow-setpoint increase; log DHW minutes × load as a deficit repaid over 3-6 h at normal flow; legionella 60 °C every 14 days at ~13:00 with Logic 2 (or PV surplus), skip below −10 °C forecast minimum; post-absence cycle after > 7 days away. Test gentler DHW (power cap 2.0-2.5 kW or stepped tank setpoint) aiming at LWT ≤ tank + 8 K.
- **Defrost masking:** coil 86 plus 10-15 min: exclude from learning, freeze integrators, never raise setpoint on post-defrost dips.
- **Anti-short-cycle guard:** min run 30 min (hard 20), min off 15-20 min, ≤ 3 starts/h, soft cap 12 starts/day; start cost 0.15 kWh_el-eq in optimisers.
- **Fallback:** if HA or the planner is stale > 30-60 min, revert to the unit's own low curve (S1 settings).
- **Ventilation:** treat Komfovent supply heat as a measured disturbance; heater off; AHU target ≥ 22 °C; optional shoulder-season bypass as an overheating valve.

### 8.13 What the simulator must model to judge these fairly

**House (thermal):**
- 2-node (room/internal mass C_i 0.5-2 kWh/K; slab C_s ≈ 6.6 kWh/K, or 4-6 kWh/K screed plus deep mass) with optional 3rd envelope node; H 0.14-0.20 kW/K (fabric + ventilation term separately); K_sr ≈ 0.65 kW/K (from UA ~450 W/K and K_ws ~1.5 kW/K); water node with K_ws ≈ 1.5 kW/K (prior 1.0-2.2, falling with run length), loop flow ~1.7 m³/h (≈2.0 kW/K, ΔT ≈ 1.9 K at P_min).
- Room-swing gain calibrated so swing per kWh carried = 0.07-0.15 K/kWh; room peak 0.1-0.7 h after a run ends.
- Self-regulation emerges from the coupled nodes (floor output falls as room warms at fixed water).
- Solar gains via a PV-proxy aperture with time-of-day bins; internal gains from household electricity; ventilation Φ_vent = 0.335·V·(T_sup − T_room) with recovery 0.75-0.80, fan heat ~60 W, optional AHU heater; disturbance noise (detrended room noise ≈ 0.1 K median, 0.4 K p90).
- Comfort metrics: detrended per-cycle peak-to-peak; Kh below 21.6 °C and above 22.8 °C; minimum room; drift rates (≤ 2 K/h).

**Heat pump (Versati III AIO 10 kW, generation parameterised):**
- P_max(T_out, LWT) from the Gree tables; P_min(T_out) = 3.2 + 0.12·(T_out − 2) kW, floor 3.1 (G1/G2) or ≈ 2.5-2.8 flat (G3); sensitivity to the owner's 3.7-3.8 kW.
- COP = η·(LWT + 2 + 273.15)/((LWT + 2) − (T_out − 6)), η = 0.50 at mid load; near max output η −8 % (sensitivity 0…−15 %); no penalty at the floor (sensitivity −10 %); collapse only below ~0.2-0.25 of rated (not reached); field derate × 0.85-0.9; check against Keymark points (B: 4.9 kW/COP 4.59 at +2/W30; C: 3.0 kW/5.67 at +7/W27; D: 3.3 kW/7.34 at +12/W24; near-full +2/W35 COP 3.39).
- Pel_min ≈ P_min/COP: 0.52 kW at W24, 0.65 at W30, 0.78 at W35 (+7…+12 °C); 0.9-1.0 at +2/W35.
- **Firmware emulation:** frequency/output ∝ (setpoint − LWT) with unknown gain (sweep) and first-order lag; restart when setpoint − outlet ≥ ΔT-Heat; stop at minimum output when LWT > setpoint + standby margin (sweep 0.5-3 K) for Heat run time (1-10 min; or immediate if absent); 3-min lockout; power cap on input power; weather-dependent mode overriding Word 10; quiet mode lowering output and fan.
- **Sensor and pump:** pump off after compressor stop (default) with outlet/return decaying toward plant-room temperature (AIO) or outdoor (monobloc) with a cabinet time constant; option pump on at 5-30 W; sensor resolution 0.1 K (option 1 K); Modbus write latency; 30-min memorisation.
- **Start transient:** 1-3 min of lost full output per start (0.1-0.2 kWh heat; up to 0.3 after > 3 h off below +8 °C); crankcase heater 0-25 W below +8 °C after > 3 h off; standby 20-25 W.
- **Defrost:** accumulated-run clock 50-60 min, not reset by stops; coil-temperature gate as function of T_out, RH and compressor load (coil warmer at lower load/higher fan); calibrate rates to the table in §3.4 (12.9/11.8/7.6/5.4/2.6/2.0 per 100 kWh at 0…+5 °C, RH ≥ 90 %; ×0.6-0.9 for 80-90 %; roughly halved below 80 %); per event 2-5 min reversed, 0.15-0.3 kWh heat drawn from water, ~0.16-0.2 kWh_el, +18 % power for ~10 min recovery; defrost tends to fire 10-15 min after a restart when the clock is full; quiet mode → interval ≈ clock floor.
- **DHW:** 185 L, 0.215 kWh/K, UA 2-2.5 W/K; draws ~4.9 kWh/day (calibrate); reheat flow ≈ tank + 6 K (higher when the gap is large); COP_DHW from Gree table × 0.85; priority over SH; ΔT-hot water hysteresis; tank heater 3 kW, Logic 1 blocks compressor; disinfection schedule; T-HP max.
- **Backup heater:** outdoor-threshold logic, Logic 1 vs 2.

**Environment and economics:**
- Hourly Vilnius weather incl. RH and irradiance for several winters (include a 2025/26-type cold spell: 27 days < −10 °C, 14-day spell, −27 °C minimum); diurnal swings (Dec 1.0 K, Mar 3.7 K warmest-6 h excess); forecasts with realistic error.
- PV 15 kWp (PVGIS: Dec 235 kWh, Nov 328, Jan 416; snow), house base load, hybrid battery (round trip 0.73-0.92 at 1-3 kW; < 0.66-0.86 at 100 W; standby 4-64 W).
- Tariffs: ESO net metering (0.0726 €/kWh any hour, 2-year bank), net billing, spot (15-min Nord Pool LT) + two/four-zone network, flat retail.

**Outputs to compare:** kWh_el per heating degree-day (SH and DHW separated); heat delivered; seasonal and per-outdoor-bin COP; mean running LWT (heat-weighted); share of heat above 75 % of max output; starts/day and run-length histogram; runs < 20 min; defrosts/day and reversed heat; DHW collisions; backup/tank-heater kWh; comfort metrics; PV self-consumption; cost under each tariff; Modbus writes/day; robustness to parameter error (H ±30 %, K_ws ±40 %, firmware gain ×0.5-×2, forecast noise).

### 8.14 Key numbers the simulator must reproduce (calibration targets)

1. Balance point (load = P_min): −5 °C (H 0.14) to +3.5 °C (H 0.20) without gains; duty at P_min ≈ 0.45 at +10 °C, ≈ 0.82 at 0 °C (H 0.14).
2. Slab: +0.30 K/h charging and −0.26 K/h coasting at +10 °C; τ = C/H ≈ 33-47 h.
3. Lowest outlet to absorb 3.75 kW: ~28-29 °C at +10 °C, ~30-31 °C at +2 °C (laminate 45/150), tile 1.5-2.5 K lower.
4. Forced-cycling lift penalty: +1.4-2.3 K at +10 °C, +0.4-0.65 K at +2 °C; +0.5-0.9 K per extra kW above P_min.
5. COP vs LWT: 3.4 %/K at A7, 2.9 %/K at A2, 1.8 %/K at A−7 (Versati certified).
6. Keymark points (G3): +2/W30 4.90 kW COP 4.59; +7/W27 3.04 kW COP 5.67; +12/W24 3.28 kW COP 7.34; −7/W34 7.76 kW COP 3.15; full at +2/≈W35 9.55 kW for 2.82 kW (COP 3.39).
7. Speed term: mid → flat-out 15-25 % (declared) vs 1-3 % (field, same LWT); total catch-up penalty reproduces mostly via LWT.
8. Start cost 0.1-0.2 kWh heat; run-length curve −1.8 %/−1.2 %/−0.7 %/0/+0.8 %/+1.4 % (15-20/30-45/45-60/60-90/90-180/> 300 min).
9. Idle: 20-25 W (+0-25 W crankcase below +8 °C).
10. Defrost: rates in §3.4; season ≈ 4.2-4.6 % of heat reversed, 5-8 % of SH electricity; no run-structure effect (×1.05).
11. Room swing 0.07-0.15 K per kWh carried; peak 0.1-0.7 h after run end; daily range ~0.8-0.9 K even in continuous operation.
12. Warmest-hour gain ≤ 0.6 % Dec-Feb, 1.5-1.8 % Oct-Apr.
13. DHW: COP factors 1.00/0.87/0.74/0.61 at 45/50/55/60 °C; legionella 50 → 70 °C ≈ 4.3 kWh; Logic 1 blocks ~1.5 h.
14. Today's behaviour (baseline replica): setpoints 31-36 °C (peaks 39), ~3 kW electric catch-ups at +2 °C, runs 0.5-4 h, DHW interruptions — the simulator should reproduce these under the current 30-min write logic with ΔT-Heat 4 K before judging alternatives.

---

## 9. Unit settings and hardware checks worth trying (no code)

Ordered by value per effort. Read and record every current value before changing anything; change one thing at a time; compare on matched-weather days over weeks, not days.

**Reads and logs first (no risk):**
1. Nameplate: exact model and suffix (NhH/NhH2/NhH3; AIO vs split vs monobloc).
2. Panel commissioning page: C/P limit mode (Off/Current/Power), Heat run time present?, Optional E-heater sets/logic, T-Eheater, tank-heater logic, T-HP max, ΔT-Heat, ΔT-hot water, disinfection settings, weather-dependent mode and its endpoints, quiet mode schedule.
3. One week of 10-30 s logging (§7 list) plus a true-RMS meter on the unit supply; note the meter's scope (does it include the tank heater?).
4. Komfovent: heat-exchanger type (reg. 955), heater power/energy (922, 937-938), per-mode setpoints and heater enable, ECO settings, flows.
5. Prosumer settlement in the ESO portal (net metering method a/c/d or net billing) and bank balance on 1 November. This decides whether timing has any cost value.

**Settings to change (reversible):**
6. **Backup heater:** Logic 2 and T-Eheater −20 °C (or Off if an external gate is built). Largest cold-weather risk if currently Logic 1 at −7…−10 °C.
7. **C/P power limit:** set mode = Power on the panel; Word 43 ≈ 1.4-1.5 kW for days above ~−3 °C; raise to 3 kW for cold spells. Then test one DHW reheat and one defrost under the cap.
8. **Quiet mode off** at −5…+5 °C on humid days (use the power cap for night noise).
9. **ΔT-Heat:** choose with the strategy: 2-4 K (Gree's recommendation) if starts happen at the natural flow temperature or an external controller parks the setpoint; 8-10 K if the external controller decides all starts and the firmware must not self-restart. Avoid 4 K combined with 30-min rewrites.
10. **Heat run time = 10 min** if the parameter exists.
11. **Hot water:** tank 47 °C, ΔT-hot water 8 K (more if allowed), T-HP max 55 °C, Fast hot water off, tank-heater Logic 2; disinfection 60 °C fortnightly at ~13:00 (or as legal advice dictates), never Saturday 23:00 at 70 °C in winter.
12. **Komfovent:** integrated heater off in routine modes; supply setpoint ≥ extract (or ECO with heat recovery = Maximum and a low ECO minimum supply so flows are not cut); AHU target never below 22 °C; keep flows constant in winter; use bypass deliberately on sunny shoulder afternoons.
13. **Curve test (if staying on firmware control):** lower the flow target 1 K every 2-3 days until the room cannot hold 22.0 °C on the coldest day of the step, then go back one step.

**Hardware checks:**
14. **Manifold:** is there a thermostatic mixing group, second pump, buffer or low-loss header? Compare unit outlet vs manifold supply during a steady run. If a mixer exists, set it to pass-through.
15. **Loops:** all open; actuators removed or set as high limits ≥ 24 °C; balance once (IR camera: floor surfaces within 1-2 K during a long run).
16. **Heat meter:** a class-2 ultrasonic meter with M-Bus/Modbus, immersion pockets, q_p 1.5 m³/h, on the space-heating branch after the DHW valve. The single most valuable hardware addition: register-based heat estimates are only ±10-25 %.
17. **Room sensing:** two or more sensors away from sun and kitchen; optional floor-surface probe.
18. **Pump wattage:** with the unit off, enable "Air removal" and read the power difference (upper bound on pump draw).
19. **Battery:** location (unheated room derates LFP near 0 °C), real round-trip efficiency at > 800 W and < 300 W from inverter logs, standby with empty battery.
20. **Outdoor unit:** coil clean, free airflow, condensate drainage, no snow drift; ducts of the MVHR insulated if in a cold attic.

---

## 10. Evidence quality and open questions

### 10.1 How strong is the evidence?

- **Strong (High):** flow temperature as the dominant lever and its size (certified Keymark data for 1,600 models plus the Versati itself; within-system HPM field data; Fraunhofer and DTI agree). Small cost of starts when runs are ≥ 60 min. No buffer, all loops open. No deep setbacks. Defrost rising steeply below +5 °C in humid air. Documented Gree register meanings.
- **Medium:** magnitude of the speed penalty (declared and lab data say 15-25 % mid→max; field same-LWT data say 1-3 %; the house's own Hz logs must settle it); defrost share for Lithuania (5-8 % central, wide unit spread); emitter conductances (EN 1264 plus certified charts; not measured on this floor); value of timing and prices (perfect-foresight simulations); MPC vs tuned curve (~4-5 %).
- **Weak (Low):** exact Gree firmware dynamics (gain, standby-zone width, power-limit scope, start profile); whether the internal pump runs at idle; whether a power cap reduces defrosts on a unit whose fan follows suction pressure; start-wear cost; occupant acceptance of pulse-induced swings.
- **Method caveats.** The shared web-search budget ran out early in the sweep, so many notes relied on direct fetches, sibling notes and their own data analysis; non-English community sources are thin (one German query in note 01; second-round gap notes G2, G5, G6, G7, G8 ran 20-27 searches each). Much "field data" is heatpumpmonitor.org: enthusiast-biased, UK-maritime, mostly Vaillant/Daikin/Ecodan, no Versati and only one Gree, no Baltic air-source system. Several numbers are researchers' own analyses (not peer reviewed). This master document relies on each note's summary, conclusions and contradictions sections, and on the verification verdicts, which supersede earlier figures.

### 10.2 Corrections made by verification (use these, not the originals)

| Original claim | Corrected |
|---|---|
| High speed costs 15-40 % more per kWh | 5-30 % (median ~20 %) max vs half capacity at same LWT; efficiency peaks at mid, not minimum speed (R1-C1) |
| 2.2-3 % COP per K of flow | 3-4 %/K in mild weather, ~2.5 near 0 °C, ~2 below −5 °C (R1-C2) |
| ~3 kW at +2 °C is a high-frequency catch-up (high confidence) | Most plausible but unverified; C/P limit default is Off (3.0 kW is a preset); tank heater (3 kW) is a missing alternative (R1-C3) |
| No cycling cost above 45-60 min runs | Small but non-zero (~0.2-0.3 % per extra start/day; multi-hour runs +1-2 % better than 45-60 min) (R1-C4) |
| Runtime fraction < 0.3 costs 6-8 % | Threshold ~0.2; half is standby; not caused by starts; not a control lever (R1-C5) |
| Defrost 3-8 % of electricity; low load prevents frost at 0 °C/80 % | ~5-12 % (central ~8 %); low load delays but does not prevent frost at Lithuanian 85-90 % RH; MPC "halving" is 4 vs 7 days (R1-C6) |
| Warmest hours save ~1.5 % in Dec-Feb | ≤ 0.6 % Dec-Feb; 1.5-1.8 % is Oct-Apr; Kuboth's +5.4 % is not timing-only (R1-C7) |
| Slab storage costs 6 %; 2 K setback is a net loss | 4-14 % depending on hold time; setback net loss only if recovery is hot/fast; in mild weather a setback is just a long off-period (R1-C8) |
| Pump draws 75-85 W continuously in standby | Refuted: 4-75 W modulating; probably stops; whole-unit idle ~20-25 W (R2-C1) |
| Ride-down/cap saves 11-13 %; 26 % more per kWh at 3 kW | 26 % is a COP drop = ~35 % more electricity; whole-day saving 2-13 % depending on burst share (R2-C2) |
| Field speed penalty 0.55-0.75 %-Carnot points per kW | Holds only on cold days; use ~1 %/kW pure speed (0-4), steep collapse below 0.2-0.3 of rated; LWT carries the catch-up cost (R2-C3) |
| K_ws 0.8-1.8 kW/K; lift penalty 1.5-3.5 K at +10 °C | K_ws 1.1-2.0 (use 1.5); penalty 1.4-2.3 K at +10 °C, 0.4-0.65 K at +2 °C (R2-C4) |
| Min electrical input 0.45 kW + 0.03 kW/K; min-speed η penalty | Model as P_min/COP (≈0.52 kW at W24 +0.026 kW/K); no consistent min-speed penalty in certified data (R2-C5) |
| DP saves ~1 %/10 %; 17-21 block captures 66 % | Ranges −0.6…−6 % / −8…−14 % on spot plans; ≈0 on net metering; 17-21 block captures 0-54 % (R2-C6) |
| Komfovent heater 3.3-4 kWh/day ≈ 14 %; recovery really 79 % | Single owner reading; net 8-14 % at +2 °C if similar; 79 % is one PHI-tested model; use 0.75-0.80 (R2-C7) |
| DHW 2.5-3 %/K; legionella 260-290 kWh/yr; Logic 1 blocks 1.5 h | 1.5-2 %/K of tank setpoint; ~225 kWh resistive, 150-190 net; blocking correct in mechanism (R2-C8) |

### 10.3 Open questions (to be answered by this house's own data)

1. Versati frequency response: gain (Hz or kW per K of error), time constant, start profile, standby-zone width, Heat run time semantics on this firmware.
2. C/P power limit: accepted over Modbus once the panel mode is Power? Input or output? Does it cap DHW, defrost, heaters?
3. Real minimum output vs outdoor and water temperature (Word 143 at its floor).
4. Pump behaviour in off-periods (coil 175) and what the outlet sensor reads then.
5. Source of the ~3 kW draws (Hz vs heater coils vs flat-top at the C/P preset).
6. Emitter UA and K_ws; active floor area; coverings; mixing group present?
7. Room-side swing per kWh (b, 0.04-0.15 K/kWh) and occupant tolerance of 0.5-1 K swings.
8. Defrost map of this unit (entry coil temperature; does a power cap lengthen intervals; do defrosts fire right after restarts?).
9. Off-time electricity and crankcase-heater behaviour.
10. Backup-heater configuration and behaviour below T-Eheater; deep-cold capacity and defrost (no Versati field data below −10 °C exists publicly).
11. Settlement scheme and bank balance; battery efficiency and location.
12. Whether HN 136:2023 binds a private homeowner (one email to NVSC); tank-heater rating; disinfection hold time.
13. Gree warranty terms for Lithuania (no start or hour limits found for other brands).

---

## 11. Glossary

- **AIO (all-in-one):** indoor hydro unit with built-in DHW tank (185 L on Versati III AIO).
- **Balance point:** outdoor temperature at which the house's heat loss equals a given heat-pump output (here: minimum output for cycling; maximum output for backup need).
- **Carnot COP / %-Carnot / η:** the ideal COP between condensing and evaporating temperatures; η is the real COP divided by it (≈0.45-0.55 for good units).
- **Cdh / Cc:** EN 14825 cycling degradation coefficient; on the Versati it reflects only standby power.
- **C/P limit:** Gree's current/power limit; mode chosen on the panel; value in Words 38/43.
- **COP / SCOP / SPF:** instantaneous efficiency (heat ÷ electricity); seasonal values (declared or measured). H4 boundary includes pumps and backup.
- **Defrost / reverse heat:** reversing the cycle to melt coil ice; heat drawn back from the water.
- **Degree-minutes (DM) / energy integral:** time-integral of flow-temperature error used to decide compressor starts (NIBE, Vaillant).
- **DHW:** domestic hot water.
- **Duty / runtime fraction (rtf):** share of time the compressor runs.
- **EEV:** electronic expansion valve (closes at shutdown; limits refrigerant migration).
- **EN 1264 / K_H:** standard for embedded floor heating; water-to-room conductance per m².
- **EN 14825 / HP Keymark:** part-load test standard and the certification database holding declared points A-D (−7/+2/+7/+12 °C).
- **H (UA of the house):** heat loss coefficient, kW per K of indoor-outdoor difference (0.14-0.20 kW/K here).
- **HPM:** heatpumpmonitor.org, the open database of metered heat pumps.
- **K_ws / K_sr / UA (floor):** water-to-screed, screed-to-room and water-to-room conductances.
- **Lift:** temperature distance the compressor bridges (≈ condensing − evaporating).
- **LWT / RWT:** leaving (flow) and return water temperatures.
- **MPC:** model predictive control: repeatedly optimise a plan over a forecast horizon using a model, apply the first step.
- **MVHR:** mechanical ventilation with heat recovery (Komfovent Domekt).
- **Net metering / net billing:** Lithuanian prosumer settlement in kWh (2-year bank, 0.0726 €/kWh returned-energy fee) or in euros at spot minus a fee.
- **P_min / P_max:** minimum steady and maximum heat output at given conditions.
- **Park setpoint:** a setpoint held low enough that the firmware cannot restart on its own.
- **Riding / glide:** keeping the setpoint just above the actual LWT during a run so the compressor stays slow.
- **Standby zone / Heat run time:** Gree's stop margin above setpoint and the delay before stopping in it.
- **TABS:** thermally activated building systems (pipes in concrete slabs); source of slab-control literature.
- **T-Eheater / Logic 1/2:** outdoor threshold and interlock mode for the Gree backup heater (Logic 1: never with compressor).
- **T-HP max:** the highest tank temperature the compressor heats to before the tank heater takes over.
- **τ (time constant):** C/H; how long the house takes to lose ~63 % of a temperature difference (33-47 h here).
- **ΔT-Heat (Word 30):** Gree restart hysteresis: restart when setpoint − outlet ≥ ΔT-Heat.
- **Weather compensation (WC):** flow temperature from outdoor temperature via a curve.

---

## 12. Index of notes

All files are in `docs/research/notes/`. Verification notes override the claims they test.

**Topic notes (round 0)**
- `01-inverter-part-load.md` — inverter modulation, part-load COP, minimum outputs, HPM within-system flow vs starts analysis, power-limit and start-trim rules.
- `02-flow-temperature-cop.md` — lift and COP, Carnot fractions, emitter physics, two-node slab emulation of catch-ups and setpoint walk-down.
- `03-cycling.md` — start costs, field run-length knee, wear limits, forced-cycling regime map, start-then-glide and pulse planning.
- `04-manufacturer-control-logic.md` — curves, room influence, degree-minutes/energy integral, brand start/stop parameters, slab-scaled DM controller.
- `05-ufh-slab-control.md` — slab time constants, self-regulation, TABS control canon, three control logics with starting parameters.
- `06-mpc-academic.md` — MPC field/lab evidence, baselines, interfaces, commercial optimisers, recommended architectures.
- `07-community-diy-controllers.md` — HPM fleet analysis, DIY/HA practice, degree-minute and riding hacks, community architectures.
- `08-gree-versati.md` — Versati parameters, Modbus registers, curve, quiet mode, power limit, defrost, DHW, control approaches C1-C4.
- `09-defrost.md` — frost physics, Lithuanian frosting zone, HPM reverse-heat analysis, Gree defrost logic, control implications.
- `10-scheduling-pv-tariffs.md` — diurnal temperature value, PV yield in Vilnius winters, Nord Pool prices, DP scheduling, operating modes.
- `11-setback-and-comfort.md` — setback evidence, comfort standards, band vs setback, comfort constraints for controllers.
- `12-compressor-speed-setpoint-dynamics.md` — how setpoint error drives speed, soft starts, power/demand caps, quiet-mode semantics, riding.
- `13-field-evidence-top-systems.md` — what top field systems do; drivers of SPF; controls share of the gap; cold tail; DHW.
- `14-grey-box-house-models.md` — RC model structures, identification, solar/gains/ventilation inputs, heat-output estimation.
- `15-hydraulics-pumps-deltaT.md` — flow and ΔT, buffers and headers, mixing, pumps in standby, balancing, owner checks.

**Gap notes, round 1**
- `gap-r1-G1.md` — certified Keymark part-load map of Versati 8/10 kW (G1-G3), Cdh, minimum output and input, η by speed.
- `gap-r1-G2.md` — Versati III/IV firmware behaviour: Heat run time meaning, removed timers, C/P limit, frequency law, test plan.
- `gap-r1-G3.md` — emitter conductance (K_H, UA, K_ws) for Lithuanian build-ups, field anchors, identification method.
- `gap-r1-G4.md` — cost per start vs off-time and volume; low-duty penalty decomposed into standby vs running effects.
- `gap-r1-G5.md` — DHW on the Versati AIO: tank temperature vs COP, legionella law and practice, timers, slab interaction.
- `gap-r1-G6.md` — Versati from −10 to −20 °C: capacity, COP, backup and tank heater logic, deep-cold defrost, Vilnius cold tail.
- `gap-r1-G7.md` — Gree defrost initiation (counter not reset on stop), speed/fan effects on frost, Lithuanian defrost cost.
- `gap-r1-G8.md` — Komfovent MVHR: ventilation share of H, integrated heater, frost protection, bypass, modelling as a disturbance.

**Gap notes, round 2**
- `gap-r2-R2-G1.md` — Versati internal pump behaviour in compressor-off periods, wattage and settings; implications for sensing.
- `gap-r2-R2-G2.md` — Lithuanian prosumer settlement (net metering, methods a-d, net billing), ESO zones and 2026 prices.
- `gap-r2-R2-G3.md` — PV surplus: battery vs slab; battery efficiency, standby, wear; regime-dependent decision rule.
- `gap-r2-R2-G4.md` — run-block structure vs defrost at 0…+4 °C, off-time frost melting, Gree post-restart defrosts.
- `gap-r2-R2-G5.md` — measured room swing in pulse-operated UFH houses vs energy carried; acceptable comfort bands.
- `gap-r2-R2-G6.md` — compressor wear per start, manufacturer limits, warranties, field start counts, start-price weight.
- `gap-r2-R2-G7.md` — accuracy of refrigerant-side heat estimation; Versati exposes no flow/power; heat meter recommendation.

**Verification notes, round 1**
- `verify-r1-C1.md` — speed penalty: partly supported; 5-30 % max vs half capacity, mid-speed optimum.
- `verify-r1-C2.md` — COP per K of LWT: partly supported; 3-4 %/K in mild weather from Keymark analysis.
- `verify-r1-C3.md` — the ~3 kW draw: mechanism plausible, not established; C/P default Off; tank heater alternative.
- `verify-r1-C4.md` — cycling knee and per-start cost: partly supported; small non-zero cost above 60 min.
- `verify-r1-C5.md` — low runtime fraction penalty: threshold ~0.2, half standby, not a control lever.
- `verify-r1-C6.md` — defrost cost: ~5-12 % of electricity; low-load frost prevention overstated.
- `verify-r1-C7.md` — warmest-hours value: ≤ 0.6 % Dec-Feb, 1.5-1.8 % Oct-Apr.
- `verify-r1-C8.md` — slab storage cost and setback: 4-14 % storage loss; setback net loss only with hot/fast recovery.

**Verification notes, round 2**
- `verify-r2-R2-C1.md` — pump 75-85 W idle: refuted as quantified; idle ~20-25 W whole unit.
- `verify-r2-R2-C2.md` — ride-down/power-cap savings: partly supported; 26 % COP drop = 35 % more electricity; burst share decides.
- `verify-r2-R2-C3.md` — field speed penalty: pure speed ~1-3 % mid→max at same LWT; LWT carries the catch-up cost.
- `verify-r2-R2-C4.md` — K_ws and forced-cycling lift penalty: K_ws ≈ 1.5 kW/K; 1.4-2.3 K at +10 °C.
- `verify-r2-R2-C5.md` — Versati minimum input and η by speed: model P_min/COP; no consistent min-speed penalty.
- `verify-r2-R2-C6.md` — price/PV scheduling value: tariff-dependent; ≈ 0 on net metering; 17-21 block 0-54 %.
- `verify-r2-R2-C7.md` — Komfovent heater energy and rotary recovery: single-owner data; use η 0.75-0.80.
- `verify-r2-R2-C8.md` — DHW temperature vs COP and legionella cost: 1.5-2 %/K setpoint; ~150-190 kWh/yr net.

**Total distinct sources.** Across all 46 notes there are **667 distinct URL strings, which normalise to about 633 distinct web sources** (after merging http/https, "www." and query-string variants). A small number of further items have no URL (researchers' own analyses of public datasets, sibling-note cross-references and a few print citations); heatpumpmonitor.org, HP Keymark, Open-Meteo/ERA5, PVGIS and Elering/Nord Pool datasets were each re-analysed by several researchers and count once each in the URL total.
