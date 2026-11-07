# Verify r1 C8: What does storing heat in the slab cost, and does a 2 K setback pay?

## Claim

Storing heat in the slab costs about 6 % of the charged energy, or 3.3-6.3 % for 24 h set-point-raise strategies. On this slab, a 2 K, 8 h setback saves only about 2 kWh of losses but must re-deliver about 13 kWh. That makes it a net loss if the recovery runs about 7 K hotter.

Found in notes 05, 10 (summary 11) and 11. The claim decides how far a price- or PV-driven planner should pre-charge the slab, and whether setbacks belong in any strategy.

**Method limits.** The web-search budget for this turn was already used up by sibling agents, so none of my searches ran (0 of the 12 asked for, and no non-English queries). I worked only from direct fetches of primary sources I already knew the URLs for, plus URLs listed in the other research notes. I read 13 sources (see Sources). Several are abstract-only, and two PDFs were read by extracting their raw text. I also checked the setback and storage arithmetic with a one-capacity (lumped RC) model of the house figures from the brief [14]. I found no measured setback study on a slab-UFH air-to-water house, so that gap remains.

## Verdict: partly_supported

- **The storage-loss order of magnitude is right.** Storage losses are small, in the single-digit to low-teens percent range. The source behind "6 %" says what the claim says [1]. But:
  - **(a) 6 % is not a constant.** It is one simulated case: a Dutch low-energy living room, five 2 h pulses of 1.6 kWh, and a constant COP of 4.5 [1]. The loss scales with how long the extra heat is held, divided by the house time constant. For this house that gives about 4-14 % [14].
  - **(b) The "3.3-6.3 %" figure uses a different denominator.** It is the increase in *annual heating use* from a ±2 K price-driven set-point modulation (20/22/24 °C, up to 24 h of activation), not a share of the *charged* energy [2]. Quoting it as "3.3-6.3 % of charged energy" is wrong.
  - **(c) Neither figure includes the COP penalty** of charging at a higher flow temperature [1] (constant COP assumed).
- **The setback arithmetic is right in shape and about right in size for cold weather.** It is slightly off in its numbers, and it misleads in two ways:
  - **The 13 kWh is not an extra cost.** It is heat that was not delivered during the setback. Only the COP difference on that heat costs anything.
  - **The net loss holds only when the recovery is fast and hot.** In mild weather (load below the 3.7 kW minimum output), a slow recovery at minimum output needs no hotter flow. The setback then becomes a long off-period with a long run, which this house is doing anyway.
- **No independent measured slab-UFH data confirms or refutes either part.** The independent measured and lab data that does exist [3][4] shows storage-driven control changing *total heat* by +1 % to +15 %. Those results are confounded by comfort level and by modelling errors.

## Corrected claim

### Storage cost

Raising a slab-heated, well-insulated house above its target and letting it coast back loses extra heat. The loss is roughly (mean time the extra heat is held) ÷ (house time constant C/H).

- **For this house**, with C ≈ 6.6 kWh/K and H ≈ 0.14-0.20 kW/K, τ is about 33-47 h. A +1 K charge then loses about:
  - 6-10 % of the charged heat for a 4 h charge (−10 to +10 °C outdoor);
  - about 4-5 % for a 2 h charge;
  - about 12-14 % for an 8 h charge.
- **The loss is larger in mild weather,** because the stored heat takes longer to be used up [14].
- **Nearby cases fit this range.** The Dutch low-energy living room loses 6 % with 2 h pulses [1]. Over a whole season, price-driven ±2 K modulation adds +3.3 % or +6.3 % to annual heating use, depending on the house group, in Danish simulations [2].
- **Add the COP penalty** of the higher flow needed to charge: about 2-3 % per K of extra flow, from the sibling notes rather than verified here. That penalty does not apply to free PV surplus.

### Setback

A 2 K, 8 h setback (heat off until the room reaches 20 °C, then held there, then recovered at about 8 kW) saves:

| Outdoor | Heat saved | Share of daily demand |
|---|---|---|
| 0 °C | 2.0-3.3 kWh | 2-3 % |
| +10 °C | 1.3-2.5 kWh | 3-4 % |
| −10 °C | 2.3-4.2 kWh | 2-3 % |

- **The slab then needs about 13.2 kWh re-delivered** (2 K × 6.6 kWh/K) [14].
- **Break-even:** the setback becomes a net *electricity* loss once the recovery heat is made at a COP about 13-20 % worse at 0 °C (10-16 % at +10 °C, 15-24 % at −10 °C) than the heat it replaced. At 2-3 % COP per K, that is about 4.5-8 K hotter flow at 0 °C.
- **"Net loss at about 7 K hotter" is correct for mid-range H at 0 °C.** But break-even can come as early as about 4.5-5 K (H = 0.14, or mild weather) or as late as about 8-10 K (H = 0.20, cold weather) [14].
- **A fast recovery at about 8 kW plausibly does need about 5-7 K hotter water.** Emitter output must roughly double from the base load of about 3.7 kW at 0 °C [14].
- **In mild weather the picture changes.** When the load (about 2 kW) is below the minimum output (3.7 kW), recovering at minimum output takes about 7-8 h with no flow penalty. The setback then saves about 3-4 % of the day's heat, at the price of about 16 h below 22 °C.

## Evidence for

- **[1] van Leeuwen et al. 2014 (simulation, the original source).**
  - Setup: Dutch low-energy living room (hollow-core concrete floor, 514 kg/m²), February week, PI floor control, constant COP 4.5.
  - Result: five 2 h storage pulses of 1.6 kWh (8 kWh in total) added 479 Wh of loss, which is 6 %. Weekly demand was "almost not influenced".
  - Operative temperature stayed in the 20-21 °C band and rose by less than 0.5 K/h.
  - The authors explain the low loss by good insulation and by the stored heat being used up quickly.
  - They suggest pricing storage at the normal rate minus 6 %.
- **[2] Johra, Heiselberg, Le Dréau 2019 (simulation, the original source).**
  - A ±2 K price-driven modulation (20/22/24 °C) with up to 24 h of activation raised *yearly heating use* by 3.3 % and 6.3 % on average for two house groups. The group labels were lost in text extraction.
  - Flexibility saturates beyond about 6 h, because cheap-price windows rarely last longer.
  - UFH in medium and heavy houses stores more than radiators do.
  - This confirms the numbers, but they are annual-use percentages, not a share of the charged energy.
- **[4] Kuboth et al. 2020 (hardware-in-the-loop lab).**
  - Setup: two identical real heat pumps with emulated floor-heating houses and real weather, run for 125 days.
  - A PV-shifting MPC made **1.1 % more heat** than the reference but used **4.1 % less electricity** (COP +5.4 %). It more than doubled PV self-consumption and cut costs by 9 %.
  - Kuboth also cites Péan et al.: heat **+3.8 %**, electricity **−8.5 %**.
  - This independently supports "storage losses are small (1-4 % of the season's heat)" and shows that efficiency gains can outweigh them.
- **[14] Own lumped-RC check on the brief's parameters.**
  - At H = 0.17 and 0 °C, the setback saved 2.6 kWh, which is close to the claim's 2.1 kWh. The claim leaves out the savings during the recovery window.
  - The re-delivery came to 13.2 kWh.
  - Break-even penalty: 16.5 % COP (about 6.6 K at 2.5 %/K).
- **Agreement from guidance and field analysis.**
  - The Rosenow/Lea/Boni analysis of HeatPumpMonitor.org and Electrification of Heat recommends a narrow 18-20 °C band over large setbacks, because recovery forces higher flow temperatures [8].
  - A slab-UFH owner on BuildHub found that a 12 h timer gave a "massive hit" to COP compared with 24/7 running [12].
  - Rutz & Moran found that night setback can *increase* heat-pump running cost unless the controller accounts for the heat pump and the building [9].

## Evidence against / complications

- **[3] Thorsteinsson et al. 2023 (field data; the closest match to this house).**
  - Setup: Danish occupied house, 230 m², low-energy, Bosch 7 kW air-to-water heat pump, concrete UFH, 97 days of price-responsive MPC.
  - At comfort levels 3-4, **heat rose +6.5 % and electricity +13.6 %**.
  - Level 3: heat +15.1 % and electricity +23.6 %, with the average room only 0.2 K warmer.
  - Level 2: heat −15.2 %.
  - Cause: the authors blame lower COP at high load and in dynamic operation, plus a COP model they had to refit. They do not separate out a storage loss.
  - Takeaway: real load-shifting on a concrete-floor air-to-water heat pump can cost much more than "6 %" once COP and modelling errors are counted. The result is confounded, so it neither confirms nor refutes the 6 % storage-loss figure.
- **[6] Owner data from a low-mass *radiator* house (Ecodan; Renewable Heating Hub, SUNandAIR).**
  - A 21 → 17 °C night setback used *less* energy than continuous running on 17 of 18 matched-ambient comparisons: 2.4-3.5 kWh/day less at 5-12 °C, and about 9 kWh/day less below 3 °C.
  - Caveats: comfort was not matched (continuous held 19.5 °C, setback 20.5 °C by day), the baseline came from clustered days, and the house has low mass.
  - Even so, this contradicts the claim's general message that setbacks always lose. A fast-cooling house gets a deeper effective setback for the same hours.
- **[5] OpenEnergyMonitor dynamic simulator (simulation; 3.4 kW radiator house, Vaillant 5 kW model).**
  - Morning and evening schedules with a 17 °C setback saved 8-15 % against continuous heating.
  - The saving vanished (+3.6 %) once the undershoot was limited.
  - A gradual daytime heat-up was best.
  - Setback savings depend strongly on the time constant and on how hard the recovery is pushed.
- **[11] Pergantis et al. 2024 (field data; air-to-air heat pump, −15 °C).**
  - The *recovery profile* decided the outcome. An abrupt +2 K at 06:00 triggered resistance backup, while a gradual MPC ramp avoided most of it.
  - This supports the claim's mechanism (a hot or hard recovery costs), and shows that a slow recovery changes the sign.
- **Arithmetic caveats [14].**
  - The 13 kWh re-delivery is a *shift*, not an extra cost, and the claim's wording invites misreading it as a cost.
  - "2 kWh saved" under-counts the recovery window by about 0.5 kWh.
  - A single lumped capacity overstates how much slab energy must be removed to drop the *room* 2 K. A two-node model would make both the saving and the re-delivery somewhat smaller. This has not been checked against measured data from the house.
  - The 7 K break-even is a point inside a 4.5-10 K range.

## Applicability to this house

- **Time constant.** τ = C/H ≈ 33-47 h, which is a long time constant for a heavy slab house with MVHR. An 8 h setback drops the room only about 0.3-0.6 K/h, so most of the setback time is spent above the floor.
  - Setbacks save little heat: 2-4 % of the day at best.
  - Any hot or fast recovery wipes that out.
- **Cold weather (load ≥ the 3.7 kW minimum output).** The claim's conclusion holds: no setbacks.
- **Mild weather (load below the minimum output).**
  - A "setback" is just a long off-period followed by one long run at minimum output. It costs no extra flow temperature and needs fewer starts.
  - The planner should treat this as how it duty-cycles, not as a forbidden setback.
  - It saves heat only to the extent that the room's average temperature falls.
- **Pre-charging for PV or cheap hours.**
  - Budget about 5-10 % extra heat on the charged amount for 1 K, 2-4 h charges, and about 12-15 % for 8 h charges or mild-weather charges.
  - Add the flow-temperature COP penalty unless the electricity is surplus PV.
  - Flexibility gains saturate beyond about 6 h [2].
  - With surplus PV, the shifted kWh is close to free, so even 15 % loss is acceptable.
  - On a grid tariff, the price gap needs to exceed about 10-20 %.
- **What would settle it.** A measured A/B on this house: alternate days at matched outdoor temperature, comparing heat-meter kWh and electricity for pre-charge or setback days against flat days. The literature cannot answer this for a slab-UFH air-to-water heat pump.

## Sources

1. van Leeuwen, de Wit, Fink, Smit, "Thermal Storage in a Heat Pump Heated Living Room Floor for Urban District Power Balancing", SMARTGREENS 2014 - https://www.scitepress.org/Papers/2014/49163/49163.pdf - peer-reviewed simulation (original source of the claim; text extracted and read)
2. Johra, Heiselberg, Le Dréau, "Influence of envelope, structural thermal mass and indoor content on the building heating energy flexibility", Energy and Buildings 183 (2019) - https://vbn.aau.dk/ws/files/290247579/Influence_of_envelope_structural_thermal_mass_and_indoor_content_on_the_building_heating_energy_flexibility_accepted_manuscript.pdf - peer-reviewed simulation (original source; text extracted, group labels for 3.3/6.3 % lost in extraction)
3. Thorsteinsson et al., "Long-term experimental study of price responsive predictive control in a real occupied single-family house with heat pump", Applied Energy 347 (2023), arXiv 2303.16289 - https://ar5iv.labs.arxiv.org/html/2303.16289 - field measurement
4. Kuboth, Weith et al., "Experimental Long-Term Investigation of Model Predictive Heat Pump Control in Residential Buildings with PV", Energies 13:6016 (2020) - https://epub.uni-bayreuth.de/5598/1/energies-13-06016.pdf - controlled lab test (hardware-in-the-loop twin rigs, real weather)
5. OpenEnergyMonitor community, "Dynamic heat pump simulator" (page 2), 2025-26 - https://community.openenergymonitor.org/t/dynamic-heat-pump-simulator/28315?page=2 - simulation (community tool, calibrated to HeatPumpMonitor annual statistics)
6. Renewable Heating Hub, "Creative trials on night-time setbacks" (SUNandAIR), 2024 - https://renewableheatinghub.co.uk/forums/postid/28542 - forum with owner measurements
7. M. Wall, Energy Stats UK, "SensoCOMFORT Room Temp Mod: Inactive, Active or Expanded" - https://energy-stats.uk/sensocomfort-room-temp-mod-inactive-active-or-expanded/ - blog with measured data (cool-down 20.2 → 18.4 °C over about 5 h; no kWh comparison)
8. CIBSE Journal, "Bridging the heat pump efficiency divide" (reporting Rosenow, Lea & Boni 2026) - https://www.cibsejournal.com/technical/bridging-the-heat-pump-efficiency-divide-2/ - field-data analysis summary (no setback penalty quantified)
9. Rutz & Moran, "Night setback with residential heat pumps", Energy 15(11) 1990 - https://ideas.repec.org/a/eee/energy/v15y1990i11p935-941.html - peer-reviewed simulation (abstract only)
10. Le Dréau & Heiselberg, "Energy flexibility of residential buildings using short term heat storage in the thermal mass", Energy 111 (2016) - https://econpapers.repec.org/RePEc:eee:energy:v:111:y:2016:i:c:p:991-1002 - peer-reviewed simulation (abstract only, no numbers available)
11. Pergantis et al., "Field demonstration of predictive heating control for an all-electric house in a cold climate", arXiv 2402.07032 (2024) - https://ar5iv.labs.arxiv.org/html/2402.07032 - field measurement (air-to-air heat pump)
12. BuildHub forum, "Do low energy houses really need heating controls?" (ragg987, JSHarris) - https://forum.buildhub.org.uk/topic/4375-do-low-energy-houses-really-need-heating-controls - forum with owner data (slab UFH + air-source heat pump)
13. Teknologisk Institut, OPSYS main report (~2019) - https://www.teknologisk.dk/_/media/72043_OPSYS%20main%20report.pdf - lab/simulation report (preheat/setback flexibility tested; no energy-penalty numbers in the main report)
14. [calc] Own lumped one-capacity model with the brief's parameters (C = 6.6 kWh/K, H = 0.14-0.20 kW/K, target 22 °C, 8 kW recovery, setback = off until 20 °C then hold; storage = +1 K linear charge over 2/4/8 h, then coast) - derived arithmetic, not evidence
