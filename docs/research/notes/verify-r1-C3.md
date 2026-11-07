# Verify r1 – C3: what the ~3 kW electrical draw at +2 °C really is

> Process caveat: the shared web-search budget for this workflow ran out after 4 searches (the limit is shared by all agents in the run), so I fell short of the 12 searches asked for. To compensate, I fetched and text-extracted 9 primary documents directly, 5 of them Gree manufacturer PDFs: two current panel manuals, the Modbus map, the Versati IV service manual and the first-generation Versati service manual. I could not reach the Versati III service manual server (connection refused), so I could not re-check its capacity and power table.

## Claim

The ~3 kW electrical draw at +2 °C is a high-frequency catch-up. It happens because the ΔT-Heat restart rule (≥4 K) forces every restart to begin with a large setpoint error. Note 12 rates this "high confidence". The alternatives listed are:
- a high leaving-water temperature (W45–50);
- the backup heater;
- a different model;
- the C/P power limit, already active at its 3.0 kW default.

## Verdict: partly_supported

- **Supported: the mechanism.** Gree documents that compressor frequency follows the gap between actual and target leaving-water temperature [5]. A restart that needs an error of 4 K or more will therefore tend to begin at high frequency. The draw is also physically possible from the compressor alone: a 10 kW Versati allows 19 A maximum heating current, which is about 4.4 kW at 230 V [4].
- **Not established: that the 3 kW *is* this mechanism, and certainly not at high confidence.** No Hz log (Words 142/143) has been set against power. Two of the listed alternatives are framed wrongly, and one strong alternative is missing.
- **Wrong premise in the alternatives.** The C/P limit is **not** "already active at its 3.0 kW default". Its factory default is **Off**. The 3.0 kW (and 16 A) are only the preset values the limit uses *if* an installer selects it [1][2].
  - The setting can still have been changed at commissioning.
  - Read the panel, not Modbus. The published Modbus map exposes the limit *values* (Word 38 current, Word 43 power) but not the Off/Current/Power selector [3]. Word 38 will read 16 and Word 43 will read 30 whether or not the limit is active.
- **Backup heater.** Its factory default is Off, and it is only enabled below T-Eheater (default −15 °C in the R32 Modbus document [3]; the Versati IV manual's text gives a 15–20 °C range, which looks like a typo [4]).
  - Logic 1 (the default) never runs the heater together with the compressor [1][2][4].
  - At +2 °C it is therefore unlikely, unless an installer raised T-Eheater or chose Logic 2.
  - It can be read directly: coils 171/172 show IDU E-heater 1/2 state [3].
- **Missing alternative: the tank's electric heater.** It is rated 3000 W on Gree tanks [5] and has its own status coil (173) [3]. It runs:
  - for disinfection;
  - when the tank setpoint is above T-HP max;
  - under tank-heater Logic 2;
  - in "fast hot water" mode;
  - in Heat + hot water with heating priority, where the tank is heated by its e-heater alone [5].

  A 3 kW draw whose metering includes the tank heater would look exactly like the reported number. The current-generation default priority is hot water [1], which makes this less likely in normal running, but it is not excluded.

## Corrected claim

"Gree firmware sets compressor frequency from the error between target and actual leaving-water temperature [5]. A restart forced by ΔT-Heat = 4 K therefore probably starts at elevated frequency. This is the **most plausible** explanation of ~3 kW draws at +2 °C. It is **not yet verified (medium confidence)**. The unit can draw this much from the compressor alone: a 10 kW unit allows up to 19 A in heating, about 4.4 kW [4].

Before designing the controller, rule out the alternatives:
1. **C/P limit.** Check the commissioning panel to see whether it is set to Power limit. The factory default is Off. If it is set to Power limit with the 3.0 kW preset, a draw that flat-tops at ~3.0 kW would be the *signature* of that cap, not a catch-up [1][2].
2. **Backup heater and tank heater.** Log coils 171, 172 and 173. The backup heater is Off by default and only allowed below T-Eheater, default −15 °C [1][3]. The tank heater is 3 kW [5].
3. **Model.** Confirm the model plate.
4. **Meter scope.** Confirm what the meter actually covers.

Then log Words 142/143 (set and actual Hz) together with electrical power and LWT. If the 3 kW coincides with Hz near maximum, LWT 31–39 °C and all heater coils at 0, the claim holds. A 'power cap' fix is then worth having."

Conditions:
- The frequency-follows-error logic is documented for Versati generation 1 [5]. Later generations are assumed to use the same scheme, as sibling notes report, but this was not independently re-read here.
- The 19 A, ~4.4 kW limit is the Versati IV 10 kW single-phase maximum heating current [4]. Versati III will be similar but this is not verified.

## Evidence for

- Gree's first-generation service manual says that in operation the compressor frequency is adjusted according to the difference between the actual leaving-water temperature and the target set temperature [5].
  - This is a manufacturer statement of the proportional mechanism, but no gain is given.
- The Versati IV 10 kW (single-phase) data [4]:
  - Rated at A7/W35: 10.2 kW heat for 2.04 kW input (COP 5.0).
  - Rated at A7/W45: 10.0 kW heat for 2.56 kW input.
  - Rated operating current in heating: 9.7 A.
  - **Maximum current in heating: 19 A.**
  - So the compressor envelope reaches well above 3 kW. A ~3 kW draw at +2 °C, where COP is lower than at A7 and defrost adds load, is reachable by the compressor alone at high frequency, even at moderate LWT. This weakens note 02's argument that 3 kW "exceeds" what W35–40 allows: rated points are not maximum-frequency points.
- The backup heater is factory-Off and limited to below T-Eheater, and Logic 1 forbids it running with the compressor [1][2][4]. At +2 °C on a default-commissioned unit it should not run, which makes the compressor the default suspect.
- General field evidence agrees that inverter controllers integrate flow-temperature error, and that a larger gap drives the unit harder. Vaillant's "energy integral" counter, for example, moves faster with a bigger gap between actual and target flow [9]. This is a different brand, so it shows the mechanism is common, not that Gree's gain is large.

## Evidence against / not established

- **C/P limit default is Off, not active** [1][2]. The claim's alternative "already active at its 3.0 kW default" misreads the manual. The 3.0 kW is the preset value shown once "Power limit" is selected.
  - Conversely, if an installer *did* select Power limit and left the preset, a ceiling at ~3.0 kW is exactly what would be seen. The coincidence between the observed "up to ~3 kW" and the 3.0 kW preset is worth checking, not dismissing.
  - The Modbus map has no register for the Off/Current/Power selector [3]. Reading Words 38 and 43 (as the claim suggests) cannot settle this, because they hold preset values either way. The commissioning panel must be inspected.
  - It is also undocumented whether Gree's power limit counts only the compressor or total unit input.
- **Missing alternative: the 3 kW tank heater** [5]. It runs for disinfection (default Saturday 23:00 [2]) and when the tank target is above T-HP max. In older generations it also covered hot water whenever heating had priority [5]. Status coil 173 [3]. If the "~3 kW" figure comes from a meter that includes the tank heater, it could be this.
- **No unit-level power register.** The Modbus map has no electrical power word [3], and HA forum users report the unit shows no consumption data [7]. The ~3 kW must come from an external meter. Its scope (heat pump only? heat pump plus tank heater? whole circuit?) decides which alternatives are possible.
- **"High confidence" is overstated.** The Gree text is a single-sentence description, given in the context of a test mode, with no gain, start ramp or maximum-frequency profile [5]. No Hz-vs-power measurement from this house is cited. The first-generation manual also describes a hold of about 6 min after start (per sibling notes). How fast frequency rises after a restart on this firmware is unknown.
- **Contradiction left open.** Note 02 cites the Versati III table as giving 2.1–2.2 kW at W35–40 "full capacity" at A2. I could not reach that PDF to check whether those rows are at maximum frequency or at a nominal/rated frequency.
  - If they are true maximum-frequency values, a 3 kW compressor-only draw at LWT 31–39 °C would be hard to explain. That would point back to heaters, meter scope or a different model.
  - The Versati IV 19 A maximum-current figure [4] suggests the table is not the maximum.

## Applicability to this house

- **Before any controller redesign, collect:**
  - one or two cold, humid days (−2 to +4 °C) at 10–30 s resolution;
  - the logged values: Words 142/143, 125/126 (LWT), 127 (return) and 117 (status);
  - coils 80 (compressor), 86 (defrost), 171/172 (backup heaters) and 173 (tank heater);
  - the electrical power from the existing meter.
- **Interpreting the log:**
  - **3 kW with set Hz near maximum and heaters off:** the claim holds. A power or frequency cap plus smaller start steps addresses it.
  - **3 kW that flat-tops exactly at ~3.0 kW for long periods:** check the panel. C/P limit may be on, and a "power cap fix" is then partly already in place. The catch-up penalty would then be bounded at 3 kW input, and the efficiency question becomes LWT and run strategy.
  - **3 kW with coil 173 or 171/172 = 1:** the issue is heater logic (disinfection timing, tank setpoint above T-HP max, T-Eheater or E-heater logic), not compressor speed.
- **Commissioning-panel check (password-protected commissioning page):** read C/P limit, Optional E-Heater (Off/1/2) with T-Eheater and logic, Tank heater logic, T-HP max and the tank setpoint. None of the selectors is in the published Modbus map, except Word 37 (E-heater logic) and Word 36 (tank heater logic) [3].

## Sources

1. Control Panel for the Versati Air-to-water Heat Pump (CopMax High Power, EN). Gree / NH Bioservice. 2024. https://www.nhbioservice.dk/wp-content/uploads/2024/09/Panel-manual-CopMax-High-Power-engelsk.pdf. **Manufacturer manual.**
   - Commissioning table: C/P limit options Off/Current limit/Power limit, **default Off**. Current limit 0–50 A, preset 16 A. Power limit 0–10 kW, preset 3.0 kW. The values can only be set when the limit is enabled.
   - Optional E-Heater default Off. Logic 1/2. The optional E-heater and tank heater never start together. Heat + hot water default priority is hot water.
2. Control Panel for the Versati Air-to-water Heat Pump, owner's manual (2025). Gree, hosted by gree.gr. https://gree.gr/wp-content/uploads/2025/07/600005064437-Users-manual-for-the-rest.pdf. **Manufacturer manual.** Same C/P limit table (default Off, presets 16 A and 3.0 kW), Optional E-Heater default Off, and the same logic description.
3. Modbus Protocol for the Versati Heat Pump Water Heater (R32). The file is named V1.5; the extracted header reads V1.1. Gree, hosted by kievclimate. https://man.kievclimate.com/man/Gree/Versati/Versati%20III/R32_Versati%20Modbus%20V1.5.pdf. **Manufacturer protocol.**
   - Word 38: current limit value, default 16 A. Word 43: power limit, 0–10 kW ×10, default 3. Words 36/37: tank heater and E-heater logic.
   - Words 142/143: set and running frequency, 0–100 Hz.
   - Coils 171/172: IDU E-heater 1/2 state. Coil 173: water tank heater state. Coil 80: compressor. Coil 86: defrost.
   - There is no register for the C/P limit selector and no electrical power register.
4. Air-to-water Heat Pump Split Versati IV (R32) service manual. Gree. c. 2023. https://gree-climat.com.ua/pdf/manual_versatti_4.pdf. **Manufacturer data table.**
   - GRS-CQ10Pd/NhH3-E: 10.2 kW / 2.04 kW at A7W35. 10.0 kW / 2.56 kW at A7W45.
   - Operating current 9.7 A, **maximum heating current 19 A**.
   - Optional E-heater logic: example below −15 °C ambient. The heater cannot run with the compressor under Logic 1.
5. Air-to-Water Heat Pump Service Manual, Versati (first generation). Gree. c. 2012. https://gree-bulgaria.com/manuals/archive/5_Versati-TSM.pdf. **Manufacturer manual.**
   - Compressor frequency is adjusted according to the difference between actual and target leaving-water temperature.
   - Tank electric heater 3000 W.
   - With heating priority in Heat + hot water, the tank is heated by its e-heater. In fast hot-water mode the tank e-heater runs alongside the heat pump.
6. Gree Versati III owner's manual, page 27 (Current limit). Manualslib. https://manualslib.es/manual/148459/Gree-Versati-Iii.html?page=27. **Manufacturer manual (mirror).** An older panel with a Current limit On/Off setting that is kept through power failure; no default stated.
7. Gree Versati III air-to-water heat pump thread, page 5. Home Assistant Community. 2025–2026. https://community.home-assistant.io/t/gree-versati-iii-air-to-water-heat-pump/377916?page=5. **Forum.** Words 142/143 are commanded and actual compressor frequency; max frequency via address 72 (65–85); the unit shows no consumption data.
8. Weather Compensation & ASHP Duty Cycle. OpenEnergyMonitor forum. 2023. https://community.openenergymonitor.org/t/weather-compensation-ashp-duty-cycle/24793. **Forum.** Samsung 8 kW: under 800 W input for ~3 kW heat at 35 °C flow; frequent cycling below ~2 kW load. Gives scale for what steady low-speed draw should look like.
9. Heat pump cycling. Energy Stats UK. https://energy-stats.uk/heat-pump-cycling/. **Field monitoring blog.** Vaillant energy-integral logic, where a larger flow-temperature gap drives the counter faster. Measured cycle lengths versus outdoor temperature on a 5 kW unit. Minimum outputs by model.

Searches run (4, budget then exhausted):
- Versati III A2/W35 performance table
- Gree "C/P limit" default
- German search on inverter Takten and Sollwertsprung
- Versati III 3 kW power consumption in Home Assistant
