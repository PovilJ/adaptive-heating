# Verify R2-C2: how much does setpoint ride-down or a power cap save on catch-up runs?

## Claim

Walking the setpoint back down after a start, or capping power, saves 11–13 % of electricity on catch-up runs (note 02 emulation), or improves catch-up COP by 15–30 % (note 12). The ~3 kW draw at +2 °C costs about 26 % more per kWh than mid-speed: about 10 % from flow temperature and 15 % from speed (gap-G1).

## Verdict: partly_supported

- **The direction is right.** Independent manufacturer data agree that the top of the speed range costs efficiency. So does a thesis built on manufacturer test data [1][2][3].
- **The "26 % more per kWh" figure is mislabelled.** The underlying numbers (COP 4.59 → 3.39) are a 26 % drop in COP. That equals about 35 % more electricity per kWh of heat. The split is also mislabelled: about 11 % of COP (≈12 % more electricity) comes from the 5 K of extra water, and about 17 % of COP (≈20 % more electricity) from speed.
- **The 15–30 % range for catch-up COP leans high.** Across six sizes of a second brand, the gain ranges from −3 % to +29 %, with a median of about +18 % [1].
- **The 11–13 % saving is a model result only.** It rests on an assumed Gree firmware law, which no independent source confirms or measures. Its own sensitivity range (0–6 % without the part-load gain) is just as consistent with the evidence.

**Process caveat.** The web-search tool was out of budget for this session, so no searches (English or other languages) could be run. Sources were fetched directly from known URLs. The Keymark certificate, the Gree Versati III service manual and the Blanco lab paper could not be read (fetch errors or encrypted PDF). The evidence is therefore thinner than the brief asked for.

## Corrected claim

- **Speed penalty at a fixed water temperature.** Going from about half speed to maximum speed lowers COP by roughly 0–22 %, typically 15–20 %. Put another way, it raises electricity per kWh of heat by 0–29 %, typically 15–25 %.
  - This holds for inverter air-to-water units at +2…+7 °C outdoor and W35 [1][2][3].
  - The penalty is near zero on units whose maximum is already firmware-capped. Vaillant's 4 kW and 6 kW models show fCOP 0.97–1.05 at +2 °C [1].
- **The minimum speed is not the optimum.** At about 10–15 % of capacity, COP is 0–18 % worse than at full load (Vaillant D point, +12 °C) [1]. Peak COP is around 40–60 Hz on a 120 Hz compressor [2][3].
  - A cap should therefore aim for mid-speed, not the floor.
- **This house at +2 °C.** If the ~3 kW draw really is near full speed at about W35, then on EN 14825 data from the Versati family (gap-G1) it costs about 35 % more electricity per kWh than running at about 50 % capacity at W30.
  - About 12 % of that is flow temperature and about 20 % is speed (combined multiplicatively).
  - Whether the draw really is near full speed is unconfirmed. Note 02's reading of the Versati III table puts full-capacity input at W35–40 at only 2.1–2.2 kW. That would mean a 3 kW draw reflects hotter water or a backup heater, not speed.
- **Whole-day saving.** Removing high-speed bursts would cut total daily electricity by:

  share of heat delivered above ~75 % speed × (15–25 %) + any flow-temperature reduction that comes with it.

  The saving cannot be stated until that share is measured on this unit. The 11–13 % emulation is a plausible upper case for days dominated by catch-up. 2–6 % is a plausible lower case.

## Evidence for

- **Vaillant aroTHERM plus, UNI/TS 11300-4 part-load tables** [1] (manufacturer data derived from EN 14825 points).
  - At +2 °C, with a capacity ratio (CR) of 0.45–0.52, the ratio COP(part load)/COP(full load) (fCOP) is:

    | Model | fCOP |
    |---|---|
    | 4 kW | 0.97 |
    | 5 kW | 1.21 |
    | 6 kW | 1.05 |
    | 8 kW | 1.28 |
    | 12 kW | 1.15 |
    | 15 kW | 1.29 |

  - At +7 °C (CR 0.26–0.30) the values are 0.97, 1.22, 1.03, 1.20, 1.17 and 1.22.
  - For the 8 kW model at +2 °C, full-load COP is 3.3 and part-load COP is 4.3.
  - Conclusion: a near-full-speed unit loses about 17–22 % of COP compared with half speed.
- **Dongellini PhD thesis, Bologna 2017** [2] (simulation tuned with manufacturer data). For an inverter unit with a 30–120 Hz compressor, COP at fixed outdoor and water temperature peaks at 40–60 Hz. COP rises "up to 20 %" going from 120 Hz to 50 Hz. Full load gives the lowest COP at every outdoor temperature.
- **Madani et al., Purdue 2010** [3] (lab, abstract only). COP falls by up to 30 % as compressor speed rises. The pressure ratio rises from 2.7 to 5.8, and isentropic efficiency peaks near 50 Hz. This figure includes lift growth at higher speed, so it overstates a pure speed effect.
- **The gap-G1 numbers check out arithmetically.** The Carnot ratio for W30 vs W35 at +2 °C (T_c = LWT + 2, T_e = T_out − 6) is 0.892, and the η ratio 0.45/0.54 is 0.833. Their product is 0.743, i.e. 26 % lower COP.

## Evidence against / corrections

- **Mislabelled metric.** "26 % more per kWh" should read "26 % lower COP", which is 35 % more electricity per kWh (calc). The underlying 10 %/15 % split is in COP terms. In electricity terms it is about 12 %/20 %.
- **The gain is not universal.** Two of six Vaillant sizes show essentially no penalty between half and full speed at +2 °C (fCOP 0.97 and 1.05) [1]. Capped-maximum models gain little from a further cap.
- **The minimum is also inefficient.** At CR 0.10–0.12 (+12 °C), fCOP is 0.82–1.03 [1]. In gap-G1's own EN 14825 table, the low-capacity points are η 0.45–0.49, below the mid-load 0.50–0.54. So "15–30 %" applies only between maximum and mid-speed, not between maximum and minimum.
- **Ambiguity in the Vaillant tables.** It is not clear whether COP(P) in [1] is at the same 35 °C water temperature or at the EN 14825 variable outlet (about W30 at point B). If it is the variable outlet, then the combined speed-plus-flow penalty there is only 0–22 % of COP, smaller than G1's 26 %. That would make G1's 15 % speed share an upper value.
- **Counter-anecdote** [4] (single user, not controlled). One owner measured space-heating COP of 3.32 on a cycling-control day against 2.58 on a continuous-running day, both at 9 °C average outdoor. The comparison is confounded (the continuous day flipped to anti-freeze, and pump power differed). It is a reminder that "long low-power running" is not automatically better in practice.
- **No independent source** describes the Gree Versati control law (setpoint gap → compressor power), which the 11–13 % emulation depends on. Forum threads with measured data [5][8][9] give minimum outputs and daily COPs, but no capped-versus-uncapped comparison.
- **Internal contradiction.** Note 02 says the Versati III table implies a full-capacity input of 2.1–2.2 kW at +2 °C and W35–40. Gap-G1 cites a Keymark full-load input of 2.82 kW at about W35. The "3 kW = full speed" premise rests on which of these is right.

## Applicability to this house

- **Load versus capacity.** At +2 °C the house needs about 2.8–4.0 kW (0.14–0.20 kW/K × 20 K). That is around the 3.7–3.8 kW floor.
  - The real alternative to a catch-up burst is near-minimum output at low water temperature, not "mid-speed".
  - Near the floor, the speed gain flattens out or reverses [1][2]. Most of the remaining benefit then comes from the lower flow temperature that a smaller output allows: about 3 %/K (gap-G1).
- **What a cap or ride-down can deliver.** It is worth the most on days with large deficits after hot-water cycles or setbacks, when the unit would otherwise run near maximum.
  - Expected: about 15–25 % less electricity during those burst hours.
  - The daily total falls only in proportion to the share of heat delivered during bursts.
- **Priority.** Lowering the requested flow temperature (31–39 °C at mild ambient) is better evidenced, from certified data, and applies to every hour, not only bursts. It should rank at least equal to the cap.
  - A power cap aimed at about 50 % of capacity is cheap to test, and is backed by [1][2].
- **Measure before you rely on it.** Log compressor frequency, input and output for a week, binned by Hz at similar outdoor temperature and flow. This answers both the speed-penalty size on this Gree and the burst share, which together set the real saving.

## Sources

1. Vaillant Italia - "aroTHERM plus: dati prestazionali a pieno carico e in parzializzazione secondo UNI/TS 11300" (July 2022) - https://Vaillant.it/downloads/vgoa-vaillant-it-doc/specifiche-tecniche/dati-uni-ts/arotherm-plus-uni-ts11300-220713-2490727.pdf - manufacturer data tables (derived from EN 14825 test points). Full-load COP and capacity at 35/45/55 °C; COP(DC), COP(P), CR and fCOP at −7/2/7/12 °C for the 4–15 kW models.
2. M. Dongellini - "Dynamic modeling and seasonal performance evaluation of air-to-water heat pump systems", PhD thesis, University of Bologna (2017) - https://amsdottorato.unibo.it/id/eprint/7901/1/Dynamic%20modeling%20and%20seasonal%20performance%20evaluation%20of%20air-to-water%20heat%20pump%20systems.pdf - peer-reviewed thesis (simulation tuned to manufacturer data). COP peaks at 40–60 Hz, up to +20 % from 120 to 50 Hz; full load gives the lowest COP; minimum 20–30 Hz.
3. H. Madani, N. Ahmadi, J. Claesson et al. - "Experimental analysis of a variable capacity heat pump system focusing on the compressor and inverter loss behavior", Purdue Compressor Conf. 2010 - https://iifiir.org/en/fridoc/experimental-analysis-of-a-variable-capacity-heat-pump-system-focusing-27509 - lab test (abstract only). COP down by up to 30 % with speed; pressure ratio 2.7→5.8; isentropic efficiency peak near 50 Hz.
4. OpenEnergyMonitor forum - "Improve efficiency: turn the heat pump off" - https://community.openenergymonitor.org/t/improve-efficiency-turn-the-heat-pump-off/13381 - forum, owner measurement. COP 3.32 (cycling) vs 2.58 (continuous) at 9 °C; confounded.
5. OpenEnergyMonitor forum - "HeatpumpMonitor.org heat pump database: minimum modulation tests" - https://community.openenergymonitor.org/t/heatpumpmonitor-org-heat-pump-database-minimum-modulation-tests/29132 - forum or field data. Minimum and maximum outputs (aroTHERM 10 kW about 5.9/9.6 kW); no COP by speed.
6. Energy Stats UK - "Heat pump cycling" - https://energy-stats.uk/heat-pump-cycling/ - installer or owner blog. Minimum outputs by model; mild-weather on/off patterns; no COP-versus-speed data.
7. Energy Stats UK - "UK winter heat pump COP" - https://energy-stats.uk/uk-winter-heat-pump-cop/ - owner field data (5 kW aroTHERM). COP by outdoor band: 4.1 at 3–4 °C, 4.8 at 7–8 °C; no speed split.
8. OpenEnergyMonitor forum - "Concerned about Daikin modulation" - https://community.openenergymonitor.org/t/concerned-about-daikin-modulation/29340 - forum. Minimum outputs (9 kW Daikin about 3–3.5 kW); daily COP 4.0 vs 5.1 (42 % vs >60 % of Carnot); no cap test.
9. OpenEnergyMonitor forum - "Heat pump demand cycling vs compressor load cycling" - https://community.openenergymonitor.org/t/heat-pump-demand-cycling-vs-compressor-load-cycling/29277 - forum. No quantified cap or speed effect.
10. Chalmers research portal, publication 152207 (capacity-controlled heat pump project) - https://research.chalmers.se/publication/152207 - research report (landing page). Design targets of full-load COP 3.0 vs 50 %-load COP 4.7 at A7; no measured annual comparison on the page.
11. Sibling notes, used only for the claim's own figures: docs/research/notes/gap-r1-G1.md (section 7), 02-flow-temperature-cop.md, 12-compressor-speed-setpoint-dynamics.md.
