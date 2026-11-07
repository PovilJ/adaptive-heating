# Verify R2-C1: Versati pump draws 75-85 W continuously while the compressor idles

## Claim

> The Versati's internal pump draws 75-85 W and runs continuously while the compressor is idle in heating. On a shoulder day at duty 0.25 that is 1.0-1.5 kWh, or 20-30 % of the day's electricity.

The claim appears in 08-gree-versati.md (summary 12), gap-r1-G4.md and 15-hydraulics (summary 9).

**Method note.** This session's shared web-search budget was used up before this check started, so no new searches could be run. I checked the claim against:
- the primary Gree documents, re-read from text extracted earlier in this session (the Hungarian Gree host refused connections today);
- the Gree EU catalogue, re-fetched today;
- a Panasonic service manual, as an independent manufacturer reference;
- EU Regulation 622/2012;
- my own new analysis of the heatpumpmonitor.org daily dataset (806 systems).

I tried manufacturer pump pages for Wilo and Grundfos, but they returned 404. Per the brief, I did not read or run the repository's lab code or house data.

## Verdict: refuted (as quantified)

The claim has two parts, and they fare differently.

1. **"Draws 75-85 W": refuted as an idle figure.** 75 W is the top of a modulating pump's range, not what it draws while idling:
   - Gree's own catalogue lists the Versati pump (RS25/7.5, 800-4,770 rpm) at **4-75 W** power input [2].
   - The Versati III manual says the pump is variable-frequency. Its speed follows the entering-to-leaving temperature difference: high when the difference is large, low when it is small [1].
   - With the compressor off, that difference is near 0 K. A ΔT-following pump should therefore sit near its low-speed end, which is single-digit to low tens of watts, not 75-85 W.
2. **"Runs continuously while idle": plausible but not shown by the cited sources.**
   - The manual passage cited for it ("during standby status, the water pump will start") belongs to the *other thermal* logic, which switches between an external boiler and the heat pump. It is not about normal heating thermo-off [1][3].
   - The manual's normal shutdown sequence says the pump stops after the compressor stops [1].
   - However, an independent manufacturer of the same design lineage (Panasonic Aquarea) does keep the pump ON at thermo-off [4]. Gree may well do the same, and the house's outlet reading tracking the slab hints at it. This part is unresolved without the pump-state coil and a power log.
3. **"1.0-1.5 kWh, 20-30 %": not supported.**
   - The arithmetic is also internally loose: 75-85 W × 18 h is 1.35-1.53 kWh, and 1.0 kWh would need 55 W.
   - Field data on 806 metered systems (743 with the central-heating pump inside the meter) give a total non-running draw in the -5 to +14 °C band of: **median 20 W, p90 50 W, max 99 W**, with only 3.6 % of systems above 75 W [5].
   - That total includes controller, pump and crankcase heater. A pump alone at 75-85 W during idle would be an extreme outlier.

## Corrected claim

- The Versati's inverter pump is rated **4-75 W** (catalogue, RS25/7.5) [2]. It modulates on flow-return ΔT [1].
- Whether it keeps running during heating thermo-off is **not documented for normal heating**. Panasonic's equivalent design does keep it running [4].
- If it runs at idle at a low ΔT-driven speed:
  - expect roughly **5-30 W** (an estimate from the 4 W floor and field totals);
  - over 18 idle hours that is **0.1-0.55 kWh**, or **about 2-12 %** of a 4.5 kWh shoulder day.
- Whole-unit idle draw (controller + pump + crankcase heater) on comparable modern monoblocs in -5 to +14 °C weather:
  - **median about 20 W, IQR 14-32 W, p90 about 50 W** [5];
  - so about 0.35-0.9 kWh over 18 h, **8-20 %** of the day.
- Units with known continuous circulation are higher:
  - Viessmann Vitocal 150A/151A: median 47-56 W total [5];
  - Panasonic Aquarea (pump stays ON at thermo-off per its manual): median 23-24 W total [4][5].
- **Upper bound:** if Gree held the pump at a fixed medium or high speed in standby (not documented), 40-75 W, which gives 0.7-1.35 kWh and 15-30 %. That is the claim's scenario. Neither the documents nor the field population support it as the default.

## Evidence for

- Gree catalogue: the pump's maximum input is 75 W (RS25/7.5). The note-08 figure of "75 W, 85 W on larger sizes" is a nameplate maximum [2].
- The pump continuing to circulate at thermo-off is real industry practice. Panasonic states that the pump stays ON when the compressor stops because the thermostat setpoint is reached [4]. Viessmann 150A systems show idle totals about 2.5× the population median [5], consistent with continuous circulation.
- The Gree manuals do contain text in which the heat pump's pump starts in "standby status" [1][3]. In context, though, it is the other-thermal logic.
- Some individual systems do reach 75-99 W idle. One example is a Gree-branded Flexx split with a third-party hydronic module and a 300 L buffer, metered with secondary pumps included: 75-86 W at -5 to +5 °C, falling to 22-37 W at +5 to +15 °C [6]. That system is not hydraulically comparable, and its cold-weather idle load is likely heaters and secondary pumps.

## Evidence against

- **The pump modulates (4-75 W) [2] and follows ΔT [1].** At idle, ΔT is about 0 K, so it should run near its low end. EU Regulation 622/2012 has required product-integrated circulators to carry their EEI on the nameplate from August 2015. It gives EEI ≤ 0.20 as the benchmark for the most efficient circulators [7], and on such units part-speed draw is a small fraction of the maximum.
- **Normal shutdown sequence:** "the water pump of the main unit stops after the compressor has stopped" [1]. In an error shutdown the pump stops 120 s after the compressor [1]. The "standby status, the water pump will start" wording appears only under the other-thermal Logic 1/2 headings [1][3]. That part of the claim's sourcing is a misreading.
- **Field population (my analysis, heatpumpmonitor.org daily stats) [5]:**
  - Scope: 806 systems with at least 10 days that have at least 4 non-running hours, -5 to +14 °C mean outdoor, no immersion or boiler use.
  - Per-system median non-running draw: p10 8 W, p25 14 W, **median 20 W**, p75 31 W, p90 50 W, max 99 W.
  - Systems metering the central-heating pump: median 21 W, p90 53 W (n = 743). Systems not metering it: median 15 W, p90 30 W (n = 63).
  - So pumps add only about 5-20 W at the median, and the *whole* idle draw sits far below 75-85 W.
- **The claimed kWh range doesn't fit its own wattage:** 75-85 W over 18 h is 1.35-1.53 kWh. The 1.0 kWh lower bound implies about 55 W.

## Applicability to this house

- The house's Versati is most likely the Versati III (R32) family. The exact pump fitted, and its minimum power, are not in the extracted Versati III tables (garbled). The Versati II 8-12 kW tables show RS25/7.5 at 4-75 W [2].
- The slab is a single zone with no buffer, so idle circulation only moves slab water. Because the pump follows ΔT, idle speed should be low.
- The decision-relevant consequence:
  - The standby penalty is likely **about 20-50 W in total**, not 100 W or more.
  - Long idle blocks cost roughly 0.4-0.9 kWh/day on a shoulder day.
  - That is real (8-20 %) but does not by itself overturn a "few long blocks" strategy. Lower lift and fewer starts can outweigh it.
  - The pump-specific share that a "pump-off mode" could save is probably 0.1-0.5 kWh/day.
- **Decisive and cheap check:** log the unit's electricity at compressor 0 Hz against the pump-state coil (175) and the crankcase-heater coil (84), split by outdoor temperature.
  - If idle draw with the pump on is ≤ 40 W, treat idle hours as nearly free.
  - If it is ≥ 60 W, the claim's ranking concern returns, and a pump-off or intermittent mode is worth pursuing. (No Versati panel manual shows such a setting [1][3].)
  - Use a true-RMS energy meter, not a clamp, because standby power factor is low.

## Sources

1. Gree, VERSATI III Air To Water Heat Pump service manual (monobloc NhG/NhG1/NhG2, 139 pp), about 2021. https://download.gree-magyarorszag.hu/gree-nyomtatvanyok/szereloknek/versati-iii/versati%20iii%20monoblokk%20–%20service%20manual.pdf. Manufacturer. Re-read today from this session's earlier text extraction (the host refused connection today). Used: §2.4 shutdown sequence (pump stops after compressor; 120 s delay in error shutdown), §2.8 pump speed follows entering/leaving ΔT, §4.6.1 variable-frequency pump, other-thermal Logic 1/2 "standby" wording.
2. Gree, Air to Water Heat Pump EU catalogue GC-2101-06, 2021. https://germany-gree.de/wp-content/uploads/2021/06/GREE_Air_to_water.pdf. Manufacturer data table, fetched today. Versati (NaE) 8/10/12 kW and 12-16 kW indoor units: pump RS25/7.5, speed 800/4,770 rpm, **power input 4-75 W**, 25 L/min at max lift.
3. Gree/NH Bioservice, Control Panel for the Versati Air-to-water Heat Pump (CopMax High Power), 2024. https://www.nhbioservice.dk/wp-content/uploads/2024/09/Panel-manual-CopMax-High-Power-engelsk.pdf. Manufacturer, read from session extraction. The same other-thermal wording, and the Gree 2025 panel manual has it too. No pump-mode parameter.
4. Panasonic, Aquarea SXC9/12 F/E8 service manual, Order No. PAPAMY1311028CE, 2013. https://www.panasonicproclub.com/uploads/CZ/catalogues/aquarea/service-manual/SXC9,12_F_E8_service%20manual_PAPAMY1311028CE.pdf. Manufacturer (independent of Gree), read from session extraction. States that the water pump remains ON when the compressor stops at thermostat OFF.
5. heatpumpmonitor.org public system list and per-system daily statistics, own analysis today (analysis script, not committed). https://heatpumpmonitor.org. Measured field data, 806 systems, -5 to +14 °C days. Non-running W distribution, split by whether central-heating pumps are metered and by model (Vaillant Arotherm+ 21 W, Daikin Altherma 3 18 W, Ecodan 22 W, Vitocal 150A 56 W, Aquarea L/J/T-Cap 23-24 W medians).
6. heatpumpmonitor.org system 251 (Gree Flexx 7 kW split + ThermAtlantic DX2W, 300 L buffer, Ottawa), daily stats, own analysis. https://heatpumpmonitor.org/system/view?id=251. Measured field data, one system, not comparable hydraulically. Idle 75-86 W at -5 to +5 °C, 22-37 W at +5 to +15 °C.
7. Commission Regulation (EU) No 622/2012 (circulators), EUR-Lex. https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32012R0622. Standard/regulation, fetched today. From 2015, product-integrated circulators must state their EEI; EEI ≤ 0.20 is the efficiency benchmark.
