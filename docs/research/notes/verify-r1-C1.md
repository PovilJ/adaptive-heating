# Verify r1 C1: Does high compressor speed cost 15-40 % more electricity per kWh of heat?

## Claim

Running the compressor at high frequency costs roughly 15-40 % more electricity per kWh of heat than running it at minimum or low speed, at the same water and air temperatures. The claim cites three figures: Vaillant COP 4.6 at 40 rps against 3.3 at 110-120 rps; a KTH result of −32 % from 30 to 90 Hz; and Vaillant 5 kW COP 3.55-3.85 at 50 rps against 2.85 at 120 rps. The claim appears in notes 01, 02, 11 and 12, and it is the main argument for ranking a power cap or soft start above lowering the flow temperature.

## Verdict: partly_supported

- **The direction is right.** At fixed outdoor air and leaving-water temperature, COP falls as compressor speed rises. Lab tests [1][2][3], Vaillant's own declared part-load data [4][5] and modelling [6] all agree on this.
- **The range is too wide and the wording is wrong in three ways:**
  1. **The penalty depends on the model.** The 40 % upper end only appears in min-vs-max lab sweeps (30 to 90 Hz), and one of those tests let the leaving water get warmer at high speed [2]. Vaillant's declared data compares full load with about 45-50 % load at the same 35 °C flow. That comparison gives a range from −3 % (the full-load run is actually cheaper) to +29 %, depending on the model [4].
  2. **Minimum speed is not where efficiency peaks.** Compressor efficiency and Carnot efficiency peak at mid speed, around 50-60 Hz [1][2]. Field data show efficiency collapsing below a unit-specific low-power limit [7]. Declared COP at very low load (10-12 % capacity) falls back to 0.82-1.03 times the full-load COP [4]. So "minimum or low speed" should read "mid or low-mid speed".
  3. **The model behind this argument has not been characterized.** I found no Gree Versati COP-vs-frequency data, so the size of the penalty for this house is not known.

## Corrected claim

At the same outdoor air temperature and the same leaving-water temperature, a variable-speed air-to-water heat pump uses typically 5-30 % more electricity per kWh of heat at maximum compressor speed than at about half capacity (median about 20 %).

- **Source of the 5-30 %:** Vaillant aroTHERM plus declared data (UNI/TS 11300 / EN 14825 basis) at +2 °C air and 35 °C flow, with capacity ratio 0.45-0.52 against full load. By model: 4 kW −3 %, 6 kW +5 %, 12 kW +15 %, 5 kW +21 %, 8 kW +28 %, 15 kW +29 % [4].
- **Wider sweeps:** Across a full 30→90 Hz sweep in the lab the gap reaches about 30-40 % [1][2][3]. Part of that comes from rising condensing temperature when only the water inlet temperature is held fixed [2].
- **The gain does not keep growing as speed falls.** It flattens below mid speed and reverses near minimum output, from inverter and motor losses and from cycling once load drops below the minimum [1][2][7][8].
- **Why it happens:** Nearly all of the effect comes from larger heat-exchanger temperature approaches, meaning a higher pressure ratio at high mass flow [1][2][6], not from the compressor itself.
- **Proposed planning figures:** about 15-25 % between "flat out" and "mid modulation"; about 0-10 % between mid and minimum; and a likely loss when running at the minimum forces on/off cycling.

## Evidence for

- **[1] Madani et al. (KTH), Purdue 2010.** Lab test of a variable-speed brine-to-water heat pump, source and sink temperatures held fixed.
  - Raising compressor speed cut COP by up to 30 %.
  - Pressure ratio rose from 2.7 to 5.8 across the speed range.
  - Total isentropic efficiency peaked close to 50 Hz.
- **[2] Awan, KTH MSc thesis 2012 (supervisor Madani).** Same test rig. R410A scroll compressor, 30-90 Hz, source and load temperatures held fixed.
  - COP_cool fell from about 5 at 30 Hz to 2.56-3 at 90 Hz. Since COP_heat ≈ COP_cool + 1, that is roughly 6 → 3.6-4, a 33-40 % drop.
  - Heating capacity went from 5.6 to 12.9 kW.
  - Inverter losses rose from 95 to 225 W but fell as a share of input, from about 10 % to 6 %.
  - Condition: the load-side setpoint was the condenser **inlet** water (25/30/35 °C) with a fixed-speed water pump. At high speed the leaving water was therefore warmer, which inflates the drop compared with a "same leaving-water temperature" comparison.
  - This is the likely origin of the "KTH −32 %" figure.
- **[3] Air-source DHW unit, Warsaw (Sustainability 2020, 12:10521).** Abstract and snippets only; the full text was blocked (HTTP 403).
  - Inverter unit at 30-90 Hz, COP 4.2-5.7, best at 30 Hz and worst at 90 Hz.
  - A snippet cites 4.65 at 30 Hz against 3.0 at 90 Hz, about −30 %.
  - Caveat: during tank heat-up the water temperature rises, so the comparison is not cleanly at constant temperatures.
- **[4] Vaillant Italia, aroTHERM plus UNI/TS 11300 datasheet (2022).** Gives full-load COP (COP(DC)) and declared part-load COP (COP(P)) at the same outdoor point. COP(DC) equals the 35 °C full-load column.
  - fCOP is the ratio COP(P)/COP(DC). At +2 °C, CR about 0.5, it is 0.97 (4 kW), 1.21 (5 kW), 1.05 (6 kW), 1.28 (8 kW), 1.15 (12 kW) and 1.29 (15 kW).
  - At +7 °C, CR 0.26-0.30, it is 0.97-1.22.
  - Example, 5 kW model at +2 °C/35 °C: full load 6.94 kW at COP 3.1, against COP 3.7 at about 52 % load.
- **[5] Energy-stats.uk, reading Vaillant's per-rps charts for the 5 kW model.**
  - 40 rps at 7 °C/35 °C gives about 2.9 kW at COP 4.6.
  - 60 rps at 2 °C/35 °C gives about 3.7 kW at COP 3.7.
  - Against the full-load values in [4] (COP 3.5 at 7 °C, 3.1 at 2 °C), max speed costs about 31 % and 19 % more electricity per kWh respectively.
  - So the claim's Vaillant 5 kW numbers are consistent with the full-load tables. I could not independently read the "3.3 at 110-120 rps" and "2.85 at 120 rps" points: the per-rps charts are images in a Czech catalogue I downloaded [9] and the text layer has no values.
- **[6] oemof/TESPy part-load dissection (open-source model).** At part load, smaller evaporator and condenser approach temperatures lower the pressure ratio and raise COP. Compressor part-load efficiency pulls the other way.
- **Other support (direction only, no clean numbers):** [10] Martinaitis et al. (Lithuanian), citing Dongellini 2017: continuous modulation gave 8.3 % / 15.4 % higher seasonal efficiency than staged / on-off operation (seasonal simulation, not a per-speed comparison).

## Evidence against / qualifications

- **The penalty is model-specific and can be near zero.** In Vaillant's own declared data the 4 kW and 6 kW units gain only −3 % to +5 % at half load [4]. A single 15-40 % band hides this spread.
- **Efficiency peaks at mid speed, not minimum.**
  - Total isentropic efficiency peaks at 50-60 Hz [1][2], and Carnot efficiency peaks at 60 Hz for every setpoint in [2].
  - The extra COP at low speed comes only from smaller heat-exchanger approaches, and it shrinks as fixed losses (inverter, fan, pump, controls) take a larger share.
- **Low-load collapse in the field.** OST (Repke, 2026) analysed Swiss Federal Office of Energy monitoring of real air-to-water and brine-to-water units. Inverter units often show a pronounced efficiency drop at low electrical part load. Carnot efficiency stays stable over a wide range, then falls sharply below unit-specific power limits, and standard test points do not capture this [7].
- **Vaillant's own data shows the same reversal.** At very low capacity ratio (CR 0.10-0.12, +12 °C) fCOP is 0.82-1.03 [4], so running near or below the minimum is no better than full load.
- **Older Chalmers lab work.** A variable-speed brine-to-water unit was *less* efficient than on/off control, attributed to frequency-converter and motor losses [8]. That is older hardware (a piston compressor), but it shows the "variable speed is always better" premise is not universal.
- **NEEA (2023-24).** Many variable-speed units perform poorly at low load because of their control algorithms. Changed controls reached COP above 4.5 in mild weather [11]. So low-speed efficiency depends on the firmware, not just the physics.
- **The cited sources mix different comparisons.** The "15-40 %" band combines:
  - max vs half capacity (about 15-30 %);
  - max vs minimum in a lab sweep (about 30-40 %);
  - sweeps where the water temperature was not held constant [2][3].

  These are different comparisons and should not be averaged.
- **The 40 % upper end is not supported for "same water and air temperature".** The 33-40 % figures come from setups where water inlet or tank temperature was fixed rather than leaving water [2][3]. The cleanest same-temperature data, Vaillant declared [4], tops out at about 29 %.

## Applicability to this house

- **No Gree data found.** I found no COP-vs-frequency or part-load table for the Gree Versati 9 kW (the Gree service manual host refused connection). For this specific unit the size of the penalty is unknown. The Vaillant data shows two different families of the same brand ranging from −3 % to +29 %.
- **The relevant comparison here is not max vs min.**
  - Minimum output (about 3.7 kW) is above the load at +10 °C (about 1.7 kW). In mild weather the real choice is therefore cycling at about minimum output vs fewer, harder catch-up runs, and the field data say low-load and cycling losses eat into the minimum-speed advantage [4][7].
  - The catch-up runs draw up to about 3 kW electric at +2 °C. That is probably near the top of the speed range, where the penalty is largest. Capping those runs toward mid modulation is where the 15-25 % per-kWh figure plausibly applies, but only to the heat delivered during those runs, not to all heat.
- **Speed and flow temperature are linked in a slab.** On a fixed emitter, higher output also needs a higher water temperature (the observed 36-39 °C peaks). In practice the speed penalty and the flow-temperature penalty stack.
  - Smoothing output (lower peak power) automatically lowers the flow temperature needed.
  - The two levers are therefore not independent alternatives, and ranking "power cap vs lower flow temperature" as rivals is a false choice.
  - The claim's framing ("at the same water temperature") understates the benefit of steady low-mid output in this house, and overstates the benefit of pushing all the way down to minimum speed.
- **Recommendation for the design.** Use about 15-25 % as the per-kWh penalty of near-max operation compared with mid modulation, and about 0 % or worse for operation at or below minimum (cycling). Then measure the Gree's own curve from logged power, flow and ΔT data at similar outdoor and flow temperatures before committing to a ranking.

## Sources

1. Madani H., Ahmadi N., Claesson J. et al., "Experimental analysis of a variable capacity heat pump system focusing on the compressor and inverter loss behavior", 13th Int. Refrigeration and Air Conditioning Conf., Purdue, 2010. Abstract via IIR FRIDOC: https://iifiir.org/en/fridoc/experimental-analysis-of-a-variable-capacity-heat-pump-system-focusing-27509. Controlled lab test (abstract read; the Purdue PDF returned HTTP 403).
2. Awan U.K., "Experimental Analysis of Variable Capacity Heat Pump System Equipped with Vapour Injection and Permanent Magnet Motor", MSc thesis, KTH Stockholm, 2012 (supervisor H. Madani): https://www.diva-portal.org/smash/get/diva2:565195/FULLTEXT01.pdf. Controlled lab test (full text read).
3. "Impact of Compressor Drive System Efficiency on Air Source Heat Pump Performance for Heating Hot Water", Sustainability 12(24):10521, 2020: https://www.mdpi.com/2071-1050/12/24/10521. Lab and real-condition test (abstract and search snippets only; full text blocked).
4. Vaillant Group Italia, "aroTHERM plus: Dati prestazionali a pieno carico e nelle condizioni di parzializzazione secondo UNI/TS 11300", July 2022: https://Vaillant.it/downloads/vgoa-vaillant-it-doc/specifiche-tecniche/dati-uni-ts/arotherm-plus-uni-ts11300-220713-2490727.pdf. Manufacturer declared data from standard tests (full text read).
5. Energy Stats UK, "Vaillant Arotherm Performance Tables & Interactive Widget": https://energy-stats.uk/vaillant-arotherm-performance-data/. Secondary reading of manufacturer per-rps charts.
6. oemof heat-pump tutorial, "Dissection of the part-load efficiency" (TESPy model): https://oemof.github.io/heat-pump-tutorial/excursion/partload-analysis.html. Simulation.
7. Repke T. (supervisor S. Bertsch), "Teillastverhalten von invertergeregelten Wärmepumpen: Analyse des Carnot-Gütegrads im Feldbetrieb und Vergleich mit Normmesspunkten", OST Ostschweizer Fachhochschule, BSc abstract, 2026: https://www.ost.ch/files/daten/abstracts/pdf/990f3d2f-cae1-4a03-a95e-8e279b8902f2.pdf. Analysis of field monitoring data (abstract read).
8. Karlsson F., "Integrated Control of Heat Pumps" (licentiate thesis), Chalmers, 2003: https://research.chalmers.se/en/publication/20110. Controlled lab test (abstract read).
9. Vaillant CZ, "aroTHERM plus VWL katalogový list 06-E2" (uploaded to OpenEnergyMonitor forum): https://community.openenergymonitor.org/uploads/short-url/7ZejjuSXiBNHkuCNB9XBiw3veSU.pdf. Manufacturer catalogue; the per-rps charts are images, so the values were not extractable. Thread: https://community.openenergymonitor.org/t/vaillant-arotherm-owners-thread/21891 (forum).
10. Martinaitis V. et al., Mokslas – Lietuvos ateitis (VGTU journals), citing Dongellini et al. 2017: https://journals.vgtu.lt/index.php/MLA/article/view/4603. Peer-reviewed simulation and review (search snippets).
11. NEEA, "Low-Load Efficiency Heat Pump Performance", product council document, 2023-24: https://neea.org/product-council-documents/low-load-efficiency-heat-pump-performance. Utility research summary (read).
12. Dongellini M., Naldi C., Morini G.L., cycling losses of on-off, multi-stage and inverter air-to-water heat pumps, Energy Conversion and Management 2019 (bibliography entry): https://www.earth.org.uk/bibliography/dongellini2019cycling.html. Peer-reviewed simulation (summary only).
