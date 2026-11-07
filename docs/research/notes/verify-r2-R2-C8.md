# Verify R2-C8: DHW tank temperature against COP, and the cost and blocking of the legionella cycle

Method note: the shared web-search budget for this run was already used up before this check started (0 searches were possible). The check therefore rests on:
- direct reads of the primary Gree service manuals (all-in-one and split) and the Gree Modbus protocol;
- my own re-analysis of the heatpumpmonitor.org public dataset (last-365-day stats joined to system metadata, air-source systems only);
- two OpenEnergyMonitor forum threads fetched directly;
- first-principles calculations.

This is fewer independent sources than the brief asks for. The weakest item, the tank-heater kW rating, could not be checked.

## Claim

Claim R2-C8 (from the gap-r1-G5 summary) has three parts:
1. Running the DHW tank at 46-48 °C instead of 50-55 °C costs about 2.5-3 % of DHW COP per K.
2. The weekly 70 °C tank-heater legionella cycle costs about 260-290 kWh/yr of resistive heat.
3. Under tank-heater Logic 1, that cycle blocks the compressor for about 1.5 h.

## Verdict

**partly_supported**

- **Part 1 holds only as a steady-state figure.** 2.5-3 %/K is right per K of *leaving-water* temperature in Gree's own table. Per K of *tank setpoint*, field data show a smaller effect, about 1.5-2 %/K on DHW COP.
- **Part 2 is overstated and does not match the G5 note's own working.** It assumes the tank heater does the whole lift from 47 to 70 °C. Gree's logic lets the compressor heat to T-HP max (default 50 °C) first. "Resistive heat" is also not the same as "extra electricity", because the stored heat is later used by hot-water draws.
- **Part 3 is right in mechanism.** The 1.5 h figure depends on a 3 kW tank heater, which I could not verify.

## Corrected claim

**(a) COP against temperature.**
- *Gree table.* At fixed leaving-water temperature, Gree's COP correction table for the Versati III all-in-one 8 kW gives these factors [1]:

  | Outdoor | 45 °C | 50 °C | 55 °C | 60 °C |
  |---|---|---|---|---|
  | +7 °C | 1.00 | 0.87 | 0.74 | 0.61 |
  | +2 °C | 0.88 | 0.74 | 0.64 | – |
  | −7 °C | 0.78 | 0.67 | 0.56 | 0.46 |

  That is **2.6-3.3 % of COP per K** of leaving water between 45 and 55 °C, with the 6/10 kW tables similar [1].
- *Field data.* Across 409 air-source systems on heatpumpmonitor.org (last 365 days, ≥500 kWh/yr DHW heat), the measured DHW COP falls **about 2.5 % per K of measured mean DHW flow temperature** (log-linear fit, controlling for outdoor temperature) [2].
- *Per K of setpoint.* The same systems' mean DHW flow rises only **about 0.46 K per K of stated tank target**. DHW COP falls only **about 1.6 % per K of target** [2]. Median DHW COP by target band [2]:

  | Target | Systems | Median DHW COP |
  |---|---|---|
  | 40-45 °C | 67 | 3.32 |
  | 46-48 °C | 85 | 3.09 |
  | 49-50 °C | 217 | 3.00 |
  | 51-55 °C | 35 | 2.82 |

  From 46-48 to 51-55 °C the drop is about 9 % over about 5 K, or **about 1.8 %/K**. This is cross-sectional data, so regression dilution and confounders (cylinder coil size, reheat start temperature) affect it in both directions.
- *Standby losses.* A higher tank also loses more heat. Going from 47 to 52 °C with a room at about 20 °C raises the temperature difference from 27 to 32 K, about **+18 % standby loss** (calculation).
- **Corrected statement:** 47 °C instead of 52 °C saves roughly **8-15 % of DHW electricity**. That is about 1.5-3 %/K, with the upper end only if the leaving water really tracks the setpoint 1:1. On about 1800 kWh/yr of DHW heat at COP ~3 this is **about 50-90 kWh/yr**.

**(b) Legionella energy.**
- *Gree defaults.* Disinfection is a separate function, **Off by default**. When enabled it defaults to **70 °C (range 40-70 °C), Saturday 23:00**, and it takes priority over hot-water mode [1][3][4].
- *Who heats when.* The water-heating logic says the main unit heats until the tank reaches the top of the unit's water-heating range. Only then does the **tank heater** take over. The auxiliary heater and the tank heater never run together [1][3]. The manual describes this for a setpoint above the heat pump's range, and I infer that disinfection follows the same path. Check this on the unit.
- *Per event.* On the 185 L tank [1], the resistive finish from T-HP max is:
  - from 50 °C (default) to 70 °C: 185 × 4.186 × 20 / 3600 ≈ **4.3 kWh**, or **≈225 kWh/yr** weekly;
  - from 55 °C (T-HP max set to 55): ≈3.2 kWh, ≈170 kWh/yr.

  The 260-290 kWh/yr figure only holds if the heater lifts the whole tank from about 47 °C, for example with the outdoor temperature outside the compressor's range, plus some extra standby loss.
- *Net extra electricity.* Much of that resistive heat is not wasted. The tank stays hot, and the next draws use that heat instead of heat-pump heat at COP ≈3. The net extra electricity is about resistive kWh × (1 − 1/COP_DHW) plus the extra standby loss at high temperature: **≈150-190 kWh/yr** for the 50 → 70 °C weekly default (calculation).
- *Field check.* UK systems with a weekly or fortnightly immersion-heater legionella cycle, mostly at 60 °C on 180-300 L cylinders, metered **2-490 kWh/yr of immersion energy, median about 90 kWh/yr** (n = 22 with data) [2].

**(c) Logic 1 blocking.**
- The manual states that under Logic 1 the compressor and the tank heater (or optional E-heater) are **never** allowed to run at the same time [1][3].
- The heater phase therefore blocks space heating for **(heat to be added) / (tank-heater kW)**: about 4.3 kWh / 3 kW ≈ **1.4-1.5 h** if the heater is 3 kW, or about 2.2 h if it is 2 kW. Add any thermostat-limited tail.
- Before that comes the compressor DHW phase (tank to T-HP max), which also interrupts space heating.
- I could not confirm the tank-heater rating for this model.
- Logic 2 lets the compressor return to space heating, but only under three conditions:
  - Heat + Hot-water mode with **hot-water priority**;
  - Tset ≥ T-HP max + ΔT-hot water + 2;
  - the setting is changed with the unit off.

  Whether the disinfection routine honours Logic 2 is not stated [1][3].

## Evidence for

- The Gree COP correction tables give a 2.6-3.3 %/K steady-state slope between 45 and 55 °C leaving water, at all outdoor temperatures from −7 to +7 °C [1]. This is the claim's own primary source, and it checks out numerically.
- heatpumpmonitor shows a 2.5 %/K slope against the *measured* mean DHW flow temperature, independent field data that agrees with [1] [2].
- The disinfection defaults (70 °C, Saturday, 23:00, Off unless enabled) are confirmed in the Gree service manual and the Modbus protocol [1][3][4].
- The Logic 1 wording ("NEVER allowed" compressor and tank heater together) is confirmed verbatim in two Gree manuals [1][3].
- Physics: 185 L × 20 K = 4.3 kWh, which at 3 kW is about 1.45 h, consistent with the claim's blocking estimate.

## Evidence against / corrections

- **Per-K of setpoint ≠ per-K of leaving water.** In the field, the mean DHW flow temperature moves only about 0.46 K per K of target. The COP sensitivity per K of target is about 1.6 %/K, and about 1.8 %/K between the 46-48 and 51-55 °C bands [2]. The claim's 2.5-3 %/K is the upper bound.
- **The 260-290 kWh/yr does not match the same G5 note's working.** G5 itself says the heater does 50 → 70 °C, 4.3 kWh, which gives about 225 kWh/yr, not 260-290. The larger number assumes a 47 → 70 °C resistive lift, which Gree's documented logic does not do when the compressor is within its range [1].
- **Resistive kWh is not net extra kWh.** Displaced heat-pump heat cuts the net cost to about 150-190 kWh/yr (calculation).
- **UK field data show much smaller immersion-heater legionella energy** (median about 90 kWh/yr) [2]. This is mainly because those cycles target 60-65 °C, not 70 °C, and some immersion heaters heat only the upper part of the cylinder.
- **The tank-heater rating is unverified.** The blocking time scales inversely with it.
- One forum thread shows Ecodan legionella cycles failing or stalling at 50 °C for 2-3 h when the booster heater tripped [5]. A stalled cycle can block for much longer than the nominal estimate, so a controller should time out.
- One owner-reported Ecodan case gives DHW COP 1.6-1.9 at a 50 °C target, which shows how wide real DHW COP spreads beyond setpoint effects [6] (anecdote).

## Applicability to this house

- **Tank setpoint.** Moving the tank from about 52 to about 47 °C is worth roughly 50-90 kWh/yr of electricity. This is real but smaller than the claim implies. The controller should treat the per-K slope as about 2 %/K, not 3 %/K.
- **Legionella cycle.** The weekly 70 °C cycle is the larger lever, about 150-190 kWh/yr net (225 kWh resistive):
  - lowering it to 60 °C and/or fortnightly roughly halves to quarters this;
  - raising T-HP max to 55 °C cuts the resistive share about 25 %;
  - running the heater finish on PV surplus makes it nearly free in spring and autumn.

  Whether the 70 °C weekly cycle is legally needed for a single-family house in Lithuania is outside this claim. See G5.
- **Slab protection in cold spells.** Under Logic 1 a 50 → 70 °C finish blocks space heating for about 1.5 h (if 3 kW), on top of the compressor DHW phase.
  - At −20 °C the house loses about 6-8 kW (0.14-0.20 kW/K × 42 K). Missing 1.5-2 h of heat removes about 9-16 kWh in total, which is about 1.5-2.5 K of slab mean temperature given the 6.6 kWh/K storage.
  - The room itself drifts much less, but the catch-up run that follows is at high flow temperature.
  - So in cold spells: either schedule disinfection at the warmest and sunniest hours, or skip or defer it, or use Logic 2 if the unit honours it in disinfection mode. Never run it at the default Saturday 23:00.
- **Check on the unit:**
  - the tank-heater rating (nameplate);
  - whether disinfection first uses the compressor to T-HP max;
  - whether Logic 2 applies during disinfection, by logging compressor frequency and tank temperature during one cycle.

## Sources

1. Gree, VERSATI III all-in-one (split, 185 L tank, GRS-CQ4.0-10PdG/NhH-E) service manual - https://gree-bulgaria.com/manuals/service/Versati_III_Split_All_In_One_04_08_10_service.pdf - manufacturer data. Covers: COP and capacity correction tables; 185 L tank; water-heating logic; Logic 1/2; T-HP max 40-55 °C (default 50 °C); disinfection default Off, Saturday 23:00.
2. heatpumpmonitor.org public dataset (system list plus last-365-day stats), re-analysed for this check - https://heatpumpmonitor.org/system/list/public.json and https://heatpumpmonitor.org (stats API) - measured field data, n = 409 ASHP systems with ≥500 kWh/yr DHW. Gives:
   - log-linear DHW COP slopes (−2.5 %/K of flow, −1.6 %/K of target);
   - median DHW COP by target band;
   - metered immersion energy for systems with immersion legionella cycles (median about 90 kWh/yr, n = 22).
3. Gree, VERSATI III split-type air-to-water heat pump service manual - gree-bulgaria.com (same manual series) - manufacturer. Covers: §3.2.4.17 Logic 1 and 2 wording; §2.3.1 water heating by main unit then tank heater; disinfection notes.
4. Gree Versati Modbus communication protocol - manufacturer. Disinfection temperature register range 40-70 °C, default 70 °C.
5. OpenEnergyMonitor forum, "Monitoring Legionella Cycle on Ecodan" - https://community.openenergymonitor.org/t/monitoring-legionella-cycle-on-ecodan/22885 - forum anecdote. Cycles stalled at 50 °C for 2-3 h when the booster or immersion did not engage.
6. OpenEnergyMonitor forum, "Poor DHW COP on an 8.5kW EcoDan?" - https://community.openenergymonitor.org/t/poor-dhw-cop-on-an-8-5kw-ecodan/27415 - forum anecdote. DHW COP 1.6-1.9 to 50 °C on a 250 L tank, roughly 3 kW in.
7. Own calculations: water heat capacity 4.186 kJ/kg·K; Carnot sensitivity; standby-loss scaling with tank-to-room ΔT - first-principles.
