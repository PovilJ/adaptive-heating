# Verify R2-C7: Komfovent integrated heater energy and the true rotary recovery

## Claim

"The Komfovent's integrated electric heater uses about 3.3-4 kWh/day at +1 to +10 °C, which is about 14 % of heating electricity. Rotary recovery is really about 79 % (PHI), not 86-89 %." (gap-r1-G8.md, summary items 2 and 4)

**Limits of this check.** The shared web-search budget for this run was used up before this check started, so no new searches could be run. That falls short of the 12 searches the brief asked for. Instead, primary documents were fetched directly and decoded locally where needed:
- the PHI certificate;
- two Komfovent data sheets;
- the EU ecodesign regulation;
- the OpenEnergyMonitor (OEM) thread.

Two independent field papers could not be fetched (a TLS error and an encrypted PDF). Treat this note as a check of the claim's own primary sources plus arithmetic, not as a broad search for contradicting evidence.

## Verdict

**partly_supported**

- **79 % (PHI):** a correct quote of an independent lab certificate for one model, the Domekt R 450 V C6M.
- **86-89 % (data sheets):** correct as quoted, but measured under a different and more generous definition. "Really 79 %" overstates how universal that number is.
- **3.3-4 kWh/day:** a single UK owner's reading. It depends entirely on his setpoint and heater settings, and part of it comes from a partial-day chart.
- **14 %:** my own calculation for one operating point of this house, not a measurement. It is also stated as gross electricity, not net extra cost.
- **This house:** nothing has been measured. Even the unit type (rotary or plate) is unknown.

## Corrected claim

1. **Heater energy.** One UK owner's Komfovent Domekt R 450 V drew about 3-4 kWh/day of electric-heater energy at +1 to +10 °C outdoors in Feb-Mar 2022 [3].
   - His settings: supply setpoint equal to extract temperature, house at 17-20 °C, fans normally at about 20 %.
   - The 3.28 kWh figure was read from a chart posted at 16:44, so it covers less than a full day [3].
   - Whether this house's unit does anything similar depends on three things: whether the heater is enabled for the active mode, the supply setpoint, and the airflow.
   - None of these is known, and the unit's own heater energy and power registers can answer directly.
2. **Share of heating electricity.** If such a heater ran at 3.3 kWh/day in this house, the share depends strongly on outdoor temperature [calc]:
   - **At +2 °C** (H 0.14-0.20 kW/K, COP 3-4): about 10-19 % of heat-pump heating electricity.
   - **At +10 °C:** potentially 25 % or more, if the heater still ran that much.
   - **Net cost is lower:** the heater's heat displaces heat-pump heat, so the extra electricity is about E_heater × (1 − 1/COP), roughly 2.3-2.5 kWh/day, about 8-14 % at +2 °C.
3. **Recovery efficiency.**
   - **PHI lab result for the R 450 V C6M** [1]: heat recovery rate 79 %, efficiency ratio ε_L 0.65, internal leakage 2.3 %.
     - Measured on the exhaust side with balanced flows, a fan-heat correction and 135-320 m³/h.
   - **Komfovent data sheets:**
     - R 450 V: 89 % at 346 m³/h reference flow [2].
     - R 400 V: 86 % at 263 m³/h [4].
   - **The data-sheet figures use the EU ecodesign definition** [5]: supply side, dry, balanced, reference flow, 13 K difference, no fan-heat correction.
   - **Use 0.75-0.80 as the lab ceiling for a rotary Domekt.** In-situ values can be lower when flows are unbalanced or the rotor slows.
   - **79 % is not established for other models**, and not for a plate (CF) unit at all.

## Evidence for

- **PHI certificate** [1] (independent lab), for the Domekt R 450 V C6M, ID 1737vs03, valid to 31 Dec 2026:
  - Heat recovery rate 79 %, ε_L 0.65, specific power 0.30 Wh/m³, internal leakage 2.30 %, external leakage 0.34 %.
  - The aluminium rotor works "without the need to use frost protection" down to the −15 °C design condition.
  - The internal electric *supply* heater is what meets the 16.5 °C supply criterion at −10 °C. The heater is part of normal cold-weather operation, not only an emergency device.
- **Komfovent R 450 V data sheet** [2] (manufacturer):
  - Thermal efficiency 89 % at 0.096 m³/s (346 m³/h) and 50 Pa. Electric heater 1 kW / 8.5 K.
  - Air after the wheel is 17.1 / 18.0 / 18.5 / 19.1 / 19.6 °C at −23 / −15 / −10 / −5 / 0 °C, with indoor air at 22 °C and 20 % RH.
  - So with full recovery, supply air is 2.4-4.9 K below a 22 °C setpoint. Any supply setpoint near room temperature leaves the 1 kW heater a residual job all winter [calc].
- **Komfovent R 400 V data sheet** [4] (manufacturer):
  - Thermal efficiency 86 % at 263 m³/h.
  - Air after the wheel is 15.6 / 16.7 / 17.4 / 18.1 / 18.9 °C at −23 / −15 / −10 / −5 / 0 °C.
- **EU 1253/2014 definition** [5] (regulation): thermal efficiency is the supply-side temperature gain over the exhaust-side loss. It is measured dry, with balanced flow at the reference flow rate and a 13 K difference, and with no correction for fan heat.
  - That explains part of the gap to PHI, which measures on the exhaust side with a fan-heat correction.
  - Fan heat alone accounts for only about 3-4 points [calc]: supply fan about 0.15 Wh/m³ ≈ 0.46 K out of 13 K.
  - The rest comes from the different measurement side, leakage and carry-over, and test conditions.
- **OEM thread** [3] (owner measurement):
  - Heater "3-4 kWh per 24 h" at 1-10 °C with supply set equal to extract.
  - A second member read 3.28 kWh heater and 4.85 kWh total for 4 March 2022, which leaves about 65 W for fans.
  - The heater is about 1 kW. The owner automated lowering the supply setpoint whenever the heater switched on.

## Evidence against / caveats

- **The heater figure comes from one forum owner, not this house** [3]:
  - The 3.28 kWh figure is from a chart posted at 16:44, which covers less than 24 h. A full day could be higher.
  - There is no documented meter type and no flow measurement. The roughly 180-200 m³/h estimate was disputed in the thread.
  - That house ran at 17-20 °C. This house runs at 22 °C, so a supply = extract setting would leave a larger shortfall below the wheel's output [calc from 2].
  - The figure can therefore be either higher or lower here.
- **The 14 % is a calculation, not a measurement.** It uses H = 0.17 kW/K, +2 °C and COP 3.5.
  - With H at 0.14-0.20 kW/K and COP 3-4, the range is about 10-19 %.
  - The claim also does not separate gross from net: the heater's heat is not lost, it replaces heat-pump heat. The net penalty is about 70 % of the heater energy.
- **"Really 79 %" overgeneralises:**
  - It holds for one certified model (R 450 V C6M) at PHI test conditions.
  - The 86-89 % figures belong to a different, standardised definition, so they are not false. They are just not comparable.
  - Field recovery depends on balance, rotor speed and duct losses. The secondary field figures cited in G8 (Luxembourg, a mean of 59 % ± 25 %; Norwegian schools, up to 14 % loss from imbalance) could not be re-fetched for this check.
- **The unit type is unknown.** G8 itself says the house's unit may be a Domekt CF plate unit. In that case:
  - the rotor efficiency point does not apply;
  - a −4 °C electric preheater adds a different electric load.
- **The H shift has a different source.** The "30-45 % H shift" in the claim's rationale comes from rotor or bypass state, not from the heater.
  - The heater does not change H. It adds a heat input of about 140 W average that hides part of the load from the heat-pump model.
  - When the heater is switched off, the house loses that input, and the heat pump must supply roughly 140 W more.

## Applicability to this house

- **Decision value is high if confirmed.** Switching the heater off per mode, with the supply setpoint at or above extract (or "Heat recovery control = Maximum" in ECO), costs nothing.
  - At a 100-150 W average it would save about 300-450 kWh/yr net, after the heat pump covers the heat at COP about 3.5 [calc].
- **Read the unit before acting on any of it:**
  - heat-exchanger type (register 955);
  - heater power and energy counters (922 and 937-938);
  - the per-mode heater enable setting and the supply setpoint.
  Register numbers are as cited in G8; this check did not re-verify them.
- **Model the heater correctly.** In the grey-box model, treat it as a measured heat input (a disturbance), not as part of H.
- **Recovery value for modelling.** If the unit is an R 450 V-class rotary, use η ≈ 0.75-0.80 as the upper value.

## Sources

1. PHI Certified Passive House Component, Komfovent Domekt R 450 V C6M, ID 1737vs03. https://database.passivehouse.com/de/components/certificate/download/1808/en. Independent lab certification. Read in full; the PDF was decoded locally.
2. Komfovent, Domekt R 450 V C6M technical data sheet. https://www.komfovent.com/en/downloads/DOMEKT_R_450_V_C6M_EN.pdf. Manufacturer data table. Read; decoded locally.
3. OpenEnergyMonitor community, "Komfovent Domekt R-450-V Heat Recovery Unit" thread (2022). https://community.openenergymonitor.org/t/komfovent-domekt-r-450-v-heat-recovery-unit/19873. Forum, owner measurements. Read.
4. Komfovent, Domekt R 400 V C6M technical data sheet. https://www.komfovent.com/en/downloads/DOMEKT_R_400_V_C6M_EN.pdf. Manufacturer data table. Read; decoded locally.
5. Commission Regulation (EU) No 1253/2014, Annex I, definition of thermal efficiency. https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32014R1253. Regulation/standard. Read.
6. Merzkirch et al., "Field tests of centralized and decentralized ventilation units in residential buildings", Energy and Buildings 116 (2016). https://orbilu.uni.lu/bitstream/10993/27775/1/Paper_%20Field%20Tests.pdf. Field data. **Not re-read:** TLS error and publisher 403; cited only via G8.
7. Schild, Pedersen and Bryn, AIVC AIR newsletter 30(2), 2009, on rotary exchangers. https://inive.org/sites/default/files/air0903_web_ed.pdf. Field data. **Not re-read:** the PDF is encrypted.
8. Komfovent DOMEKT C6M user manual. https://www.komfovent.com/en/downloads/DOMEKT_C6M_user_manual_EN.pdf. Manufacturer manual. **Not re-read:** the file is over 10 MB; per-mode heater off is cited via G8.
