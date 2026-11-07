# Verify r1 - C7: value of "heat in the warmest hours" in a Vilnius winter

## Claim

From December to February in Vilnius, the warmest 6 h window is only 1.1-1.9 K above the daily mean. Scheduling heat into the warmest hours therefore saves at most about 1.5 % of seasonal electricity, and 0-1 % with a 1-2 K comfort band. Kuboth's twin-rig trial reports +5.4 % COP from timing. (Notes 10, 08, 03.)

## Verdict

**partly_supported**

- The weather numbers reproduce.
- The size of the saving holds as an upper bound against an "even" baseline.
- The claim is weaker or wrong in three places:
  1. The 1.1-1.9 K figure needs a perfect daily forecast. Clock-time scheduling gets about half of it.
  2. The 1.5 % is an October-April figure, not December-February. December-February alone is only about 0.4-0.6 %.
  3. Kuboth's +5.4 % is not a timing-only effect. It mixes timing with a buffer, lower night flow temperatures and a much larger daily temperature swing.
- A night-heavy baseline roughly doubles the gap.

Limitation: the shared web-search budget for this run was already used up when this check started. No new searches could be made. The evidence comes from re-reading the primary paper, re-analysing reanalysis data independently, the LHMT/WMO normals, the Gree datasheet and one field blog. Breadth is thinner than intended.

## Corrected claim

Vilnius, ERA5-based hourly data for 2022-2025 (independent re-run [2]):

| | Dec | Jan | Feb | Nov | Mar |
|---|---|---|---|---|---|
| Warmest 6 h of *each day* (perfect forecast) minus daily mean, K | 1.0 | 1.4 | 1.9 | 1.3 | 3.7 |
| Fixed 10-16 h clock window minus daily mean, K | 0.4 | 0.5 | 1.3 | 0.9 | 2.9 |
| Fixed 10-16 h minus 00-06 h, K | 0.6 | 0.8 | 2.4 | 1.3 | 5.2 |
| Daily max-min range, K (ERA5) | 3.3 | 4.2 | 5.0 | 3.7 | 8.2 |
| Daily max-min range, K (LHMT 1991-2020 normals [3]) | 4.0 | 4.5 | 4.8 | 4.0 | 7.2 |

Electricity saving from putting the needed ON hours (heat need ÷ 3.8 kW P_min) into the warmest hours. Same load model as note 10. Fixed W35 flow. COP slope 3.5-5 %/K. No comfort constraint, so these are upper bounds:

| Period | vs spread evenly, perfect forecast | vs spread evenly, clock-time only | Gap between warmest-first and coldest-first |
|---|---|---|---|
| Dec-Feb | −0.5 to −0.6 % | −0.15 % | ≈1.0-1.1 % |
| Nov | −1.0 to −1.3 % | −0.5 to −0.6 % | ≈2-2.5 % |
| Mar | −2.7 to −3.6 % | −2.3 to −3.0 % | ≈5.4-7 % |
| Oct-Apr season | −1.5 to −1.8 % | −1.1 to −1.3 % | ≈3.0-3.6 % |

Corrected statement:
- In December-February, the warmest 6 h is 1.0-1.9 K above the daily mean with a perfect forecast, and only 0.4-1.3 K with fixed clock hours.
- Timing for COP is worth ≤0.6 % of December-February electricity at a fixed W35 flow. The house runs 20-22 h/day then, so there is little to move.
- Over October-April the bound is about 1.5-1.8 % against an even baseline. Most of it comes from October, March and April.
- Against a controller that habitually runs at night (catch-up runs after a cold night), the gap is about 3-3.5 % of seasonal electricity.
- The "0-1 % with a comfort band" figure is plausible for December-February. With only 2-4 OFF hours per day, the band hardly binds. That figure is note 10's own simulation and was not independently re-run here.
- Kuboth measured +5.4 % COP (4.46 → 4.70) for an MPC against a heating-curve controller, December 2019 to April 2020. That is not a timing-only result.

## Evidence for

- **Weather amplitude reproduces.** An independent re-computation on 2022-2025 ERA5 hourly data gives per-day warmest-6 h excess over the mean of 1.04 / 1.41 / 1.88 K for December / January / February. That matches note 10's 1.1 / 1.4 / 1.9 K, computed on a different date span [2].
- **Station normals confirm a small winter swing.** LHMT 1991-2020 normals give mean daily max-min of only 4.0-4.8 K in December-February, against 7.2 K in March and 10.1 K in April [3]. Much of that range is synoptic, not diurnal: fronts arrive at random times.
- **COP slope at fixed W35 is 3.5-4 %/K.**
  - Gree Versati datasheet, W35: COP 4.61 at A7 and 2.81 at A−7 for the 10 kW unit. That is a log-slope of about 3.5 %/K [4].
  - Other sizes: 4.5-5.3 at A7 and 2.7-3.2 at A−7, a similar slope [4].
  - With ≤1.9 K of shiftable temperature and 20+ ON hours/day, the arithmetic leaves ≤1 % in December-February.
- **Kuboth points the same way.** The authors say December-February had low cost-saving potential, because of low irradiance and a small daily temperature spread. Their gains were concentrated in March-April (42 % relative cost saving in April) [1].

## Evidence against / corrections

- **The 1.1-1.9 K figure is an oracle value.** It assumes the controller knows each day's warmest window. With a fixed clock window, the December-January excess is only 0.4-0.5 K [2]. A forecast-driven controller gets somewhere between the two.
- **The claim mixes periods.** "December to February … saves at most about 1.5 % of seasonal electricity" joins a December-February amplitude to an October-April saving. The December-February saving is only about 0.5 %. The 1.5 % comes mostly from the shoulder months [2; note 10 table 1.4].
- **The baseline matters.** "Spread evenly" is a soft baseline. If the current controller does its catch-up runs at night or in the morning (as Kuboth's reference did [1]), the difference to warmest-first is roughly double: about 1 % in December-February and 3-3.5 % over the season.
- **Kuboth's +5.4 % COP is not "from timing".**
  - It is MPC against a heating curve. The rig had a buffer (water storage; the flow temperature was measured at the top of the store) and a Bosch WPL AR 6 kW ASHP (A2/W35 rating).
  - The authors say the MPC also avoided high flow temperatures and "unnecessary heating" by running constant low output at night. Timing and flow-temperature effects are confounded [1].
  - The Bayreuth winter of 2019-20 was mild, mostly above 0 °C. Daily max-min spreads in the paper's weather table average about 5.4 / 5.7 / 6.8 K for December / January / February, roughly 1.3-1.6× Vilnius [1][2][3].
  - So +5.4 % is not a Vilnius timing number in either direction.
- **The COP slope near 0 °C may be steeper in the field than the datasheet shows.**
  - Energy Stats UK (one Vaillant 5 kW, Sheffield): COP rose from 3.1 at −2 to −1 °C daily mean to 3.9 at 2-3 °C, roughly 6 %/K [5].
  - That figure is confounded by weather compensation and by defrost, which is worst in the humid −2 to +5 °C band.
  - Using 5 %/K instead of 3.5 %/K raises the bounds only slightly: season −1.8 % instead of −1.5 %, December-February −0.6 % [2].
  - Lower afternoon humidity could add a small defrost bonus that no source here quantifies.
- **ERA5 understates the range slightly.** The ERA5 December range (3.3 K) is about 0.7 K below the station normal (4.0 K) [2][3]. Station-based amplitudes may be 10-20 % larger, which does not change the conclusion.

## Applicability to this house

- **December-February:** the load is about 3-3.4 kW against a 3.8 kW minimum, so the unit needs 20-22 h/day. "Warmest hours" scheduling is a rounding error (≤0.6 %). In this period it is not worth building for COP alone.
- **What matters more:**
  - Flow temperature and part-load lift. Note 03 estimates 7-16 % COP from the forced-cycling lift penalty.
  - Avoiding night catch-up bursts at 36-39 °C. Note 03's "timing matters more than start count" holds only in the shoulder months (October-November, March-April). There the unit cycles anyway, and warmest-hour placement is worth 1-3.6 %, comparable to the 1-3 % start penalty.
- **Where timing logic earns its place:** PV self-consumption on the 15 kWp array, which is mostly a March-October matter, and the spot price. Kuboth's 107.7 % PV self-consumption gain came with a 9 % cost saving, not from COP. Build timing as a PV/price feature with a small COP tie-breaker, not as a December-February efficiency feature.
- **Forecast quality:** with a fixed clock window instead of a forecast, the December-January benefit falls to about 0.15 %. Only use a temperature forecast for this if it is already available, for example for PV.

## Sources

1. Kuboth S., Weith T., Heberle F., Welzl M., Brüggemann D., "Experimental Long-Term Investigation of Model Predictive Heat Pump Control in Residential Buildings with Photovoltaic Power Generation", Energies 13:6016, 2020. https://epub.uni-bayreuth.de/5598/1/energies-13-06016.pdf. Controlled lab test (twin rigs, real ASHP, real weather, emulated building), re-read here.
   - Table 1: COP 4.46 → 4.70 (+5.4 %), electricity 1032 → 990 kWh (−4.1 %), cost −9.0 %.
   - MPC shifted operation to 10:00-17:00 and kept low constant night output to avoid high flow temperatures.
   - The daily weather table was used to compute the December-February spreads.
2. Open-Meteo Historical Weather API (ERA5-based reanalysis), Vilnius, hourly temperature_2m for 2022-01-01 to 2025-12-31. https://archive-api.open-meteo.com/v1/archive. Field data (reanalysis), re-analysed independently by this check with its own script: per-day oracle window, fixed clock window, and placement simulation with COP slope 3.5 and 5 %/K.
3. Vilnius climate table, 1991-2020 normals (Lithuanian Hydrometeorological Service / WMO), via Wikipedia "Vilnius". https://en.wikipedia.org/wiki/Vilnius. Station climatology: mean daily max/min for December -0.1/-4.1, January -1.5/-6.0, February -0.4/-5.6, March 4.5/-2.7 °C.
4. Gree Versati III datasheet (Spanish, Gree Products Spain via Remle). https://cdn01.remle.com/IMATGES/F557/7017011.pdf. Manufacturer data, re-read here: COP at W35 4.5-5.3 (A7) and 2.7-3.2 (A−7) across sizes; 10 kW split 4.61 / 2.81.
5. Energy Stats UK, "Real World UK Winter Heat Pump COP Performance", 2024. https://energy-stats.uk/uk-winter-heat-pump-cop/. Field data, single system (Vaillant Arotherm 5 kW, Sheffield): COP by daily-mean band, 3.1 (−2 to −1 °C) to 5.4 (11-12 °C).
