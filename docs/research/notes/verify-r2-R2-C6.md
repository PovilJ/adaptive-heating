# Verify R2-C6: value of price/PV-aware scheduling (DP savings and the 17-21 block)

**Method note.** The shared WebSearch budget for this run was already used up when this check started: all 3 searches I tried were refused. So I could not run the requested 12+ searches or the non-English queries. Instead, this check uses:
- direct reads of primary papers (arXiv HTML, university repository PDFs extracted locally with PDFKit);
- OpenAlex metadata lookups by DOI (abstracts only) where the publisher blocked access;
- the regulator and operator pages for Lithuanian prosumer settlement;
- an **independent re-implementation** of the hourly dynamic program on public data, written from scratch without reading the note's scripts. It uses Elering LT day-ahead prices and Open-Meteo Vilnius weather for three winters (Oct-Apr 2023-24, 2024-25 and 2025-26). Results from it are marked **[V]**.

Caveat on [V]: it uses the same simplified house model as the note (H = 0.17 kW/K, C = 6.6 kWh/K, P_min = 3.8 kW, ON power = max(P_min, 1.3 × load), Versati W35 COP vs air temperature, perfect foresight, no solar gains in the room). It therefore checks the arithmetic and the tariff sensitivity, not the physics.

## Claim

R2-C6, from 10-scheduling-pv-tariffs.md, summary points 4-5:
- Hourly dynamic programming over two Lithuanian winters gives a cost cut of about **1 %** (3 % with PV) with a **±0.5 K** comfort band, and about **10 %** (16 % with PV) with a **2 K** band, at 0 to +4 % electricity.
- Blocking 17-21 h alone captures about **66 %** of MPC savings.

## Verdict: partly_supported

1. **The DP figures reproduce in order of magnitude, but they are not stable point values.**
   - The −1 %/−3 % figure for a 1 K band is the low end of a −0.6 % to −6 % range (no PV), or −3 % to −11 % (with PV), depending on the winter.
   - With PV and a 1 K band, electricity rose by about +6 %. That is above the claimed 0 to +4 %.
2. **The figures hold only on a time-varying retail tariff.** On net metering, which is likely for a 15 kWp prosumer, the marginal kWh costs a flat 0.0726 €/kWh at any hour. Under that scheme the cost value of scheduling is roughly **zero**.
3. **The 66 % is quoted correctly from the Danish paper but does not transfer.**
   - In the paper it is a back-of-envelope estimate. It assumes a COP of 4.2 and a Danish 17-21 network rate about 10× the night rate.
   - Under Lithuanian tariffs, a 17-21 block captured about **0-54 %** of DP savings in [V]. The typical share was 30-50 % with a 2 K band and at most about 30 % with a 1 K band.

## Corrected claim

> In a simplified, perfect-foresight hourly DP of this house (fixed W35 COP, no room solar gains), the cost saving of price-aware ON/OFF scheduling against a hysteresis-at-P_min controller in the same comfort band depends on three things: the tariff, the band, and the winter.
>
> **On a spot-indexed retail plan plus the ESO two- or four-zone network tariff:**
> - **1 K total band (±0.5 K):** cost −1 % to −6 % without PV, −3 % to −11 % with PV valued at export price. Electricity changes by +1 % to +2.5 % without PV and about +6 % with PV.
> - **2 K band (±1 K):** cost −8 % to −14 % without PV, −13 % to −22 % with PV. Electricity changes by about −0.3 % to +1.5 %.
>
> **On ESO net metering ("returned energy", 0.0726 €/kWh at any hour):** the cost saving is about 0 % (−0.6 % to +2.6 %). Only the small COP-timing effect remains.
>
> **The 17-21 block:** a simple "no space heating 17-21, pre-charge before 17" rule captures about 30-50 % of the DP saving with a 2 K band and about 0-30 % with a 1 K band, on a retail time-of-use tariff. It captures nothing on net metering. The Danish "66 %" figure belongs to a tariff whose evening network rate was 0.26 €/kWh against 0.027 €/kWh at night (plus 25 % VAT).
>
> These are upper bounds. They assume perfect forecasts, ignore the extra flow temperature needed to charge the slab, and ignore sunny-day overheating. Measured long tests on real systems show single-digit to low-double-digit cost savings, with electricity often rising [1][2].

## Evidence for

- **The DP magnitudes reproduce [V].** Comfort was a slab-energy band (1 K = 6.6 kWh), with a start penalty of 0.08 € and a hysteresis-at-P_min baseline. Spot + VAT + 0.012 €/kWh supplier fee + ESO Standartinis network tariff [6][8][9]:

  | Winter | Tariff | 1 K, no PV | 1 K, PV | 2 K, no PV | 2 K, PV | Δ kWh (range) |
  |---|---|---|---|---|---|---|
  | 2023-24 | two-zone | −2.6 % | −6.2 % | −8.7 % | −16.3 % | −0.3 to +5.8 % |
  | 2024-25 | two-zone | −5.7 % | −10.4 % | −12.6 % | −20.5 % | −0.1 to +5.9 % |
  | 2025-26 | two-zone | −0.6 % | −2.8 % | −8.1 % | −13.5 % | −0.2 to +6.1 % |
  | 2023-24 | four-zone | −3.1 % | −7.0 % | −9.8 % | −17.3 % | −0.2 to +5.8 % |
  | 2024-25 | four-zone | −6.2 % | −10.9 % | −13.7 % | −21.8 % | −0.1 to +6.0 % |
  | 2025-26 | four-zone | −0.9 % | −3.0 % | −8.9 % | −14.2 % | −0.3 to +6.6 % |

  The note's 2-K figures (−10 %/−16 %) sit in the middle of this range. Its 1-K figures (−1 %/−3 %) sit at the low end.
- **Starts per day [V].** DP starts per day were 2.2-2.6 (2 K band) and 3.9-4.5 (1 K band). Both are close to the baseline, consistent with the note's "starts rise slightly or stay similar".
- **The price profile is confirmed [8][V].** Over Nov-Mar, LT spot at 00-06 was 34-45 €/MWh below the daily mean, and 17-21 was 24-45 €/MWh above it (2023-24 to 2025-26). The 17-21 window is the most expensive every winter.
- **The 66 % figure is genuine in its source.**
  - Thorsteinsson et al. conclude that roughly two thirds of the MPC savings could be had just by blocking the heat pump in the evening peak [1].
  - The overall saving was 12.4 % on a 97-day occupied-house test, with electricity +9.5 % [1].
- **Long real-hardware tests stay in single to low double digits.**
  - Kuboth et al., 125 days on twin rigs with a real air-source heat pump, a 500 L buffer and PV [2]: cost −9.0 %, electricity −4.1 %. This was with a **4 K wide** comfort band (20-24 °C) and a flat price plus feed-in. So ~10 % needs a wide band, which matches the note's band sensitivity.
  - Le Dréau & Heiselberg used ±2 K set-point moves on price quartiles and got 3-10 % cost savings (as summarised in [3]).

## Evidence against

- **Tariff assumption (the biggest issue).**
  - Under ESO net metering, surplus is netted monthly, banked for two years and stored "in one zone". A shortfall is split across zones in proportion to that month's consumption [7].
  - Drawn-back energy costs a flat **0.0726 €/kWh** at low voltage [6].
  - A 15 kWp array makes ~14.5 MWh/yr, so winter heat-pump kWh are likely drawn from the bank. In that case time of use barely changes the bill.
  - In [V] with a flat 0.0726 €/kWh, DP cost changed by **−0.6 % to +2.6 %**. The positive values arise because the start penalty dominates at a low price, so the DP trades kWh for fewer starts.
  - The claim's 1-16 % applies only if the owner is on a spot or zone retail plan without a kWh bank, or on net billing.
- **The 66 % does not transfer to Lithuania.**
  - The Danish tariff behind it had network rates of 0.027 / 0.081 / 0.26 €/kWh (night / day / 17-21), excluding 25 % VAT. The authors warn that this peak price gives price-aware control an "unfair advantage" [1].
  - The 66 % itself is an estimate: postponed consumption priced at the 21-01 average, with an assumed COP of 4.2 [1]. It was not a measured counterfactual.
  - The Lithuanian four-zone evening network rate is 0.146 €/kWh against 0.104 day and 0.063 night [6 via note R2-G2]. The evening premium is therefore roughly a quarter of Denmark's.
  - In [V], the share of DP savings captured by a 17-21 block was 34-54 % (2 K band, no PV), 23-44 % (2 K band, PV) and −5 % to 31 % (1 K band).
- **The claimed electricity range is too narrow.** With PV valued and a 1 K band, [V] electricity rose by **+5.8 % to +6.6 %**, against the claimed 0 to +4 %. The note's own table shows +3.9 % for that case.
  - Field data show larger rises: Thorsteinsson +9.5 % overall and +23.6 % at one comfort level [1].
- **Year-to-year spread is large.** The 1 K band saving ranged from −0.6 % (2025-26) to −6.2 % (2024-25) [V]. Two winters are not enough for a point estimate.
- **Much larger figures exist in other simulations, but against weaker baselines.**
  - Economic MPC on a floor-heated ground-source house: 25-35 % cost reduction against constant-price operation [4].
  - The Péan review reports up to 40 % (30-40 % in one experimental study against rule-based control) [3].
  - Ideal multi-zone MPC: >39 % cost reduction against two-point hysteresis, for a high-capacitance building [5].
  - Fixed peak blocking in a Portuguese ground-source study: 17-34 % [3].
  - These do not refute the claim, because they use heating-curve or hysteresis baselines, wider bands and larger price spreads. They do show that the result is dominated by tariff spread and baseline choice.
- **Systematic optimism shared by the note and [V].**
  - Perfect foresight: the Péan review cites only a 31 % → 27 % drop without forecasts [3], but field tests saw model drift and forecast errors [1].
  - No extra flow temperature for charging.
  - No room solar gains. Overheating on sunny days after night charging was observed in the Danish field test [1], and comfort excursions were higher under MPC in [2].

## Applicability to this house

- **First establish the settlement scheme** (net metering method (a)/(c), net billing, or plain retail).
  - On net metering with an annual surplus, a price-aware planner has close to zero cost value in winter.
  - The objective should then be kWh, i.e. efficiency: low flow temperature, fewer catch-up runs. On that objective, the DP finds only about 0-1 % (note and [V]).
- **The planner's own value is small compared with the bigger issue.** The owner's concern (high flow temperatures, on/off cycling) is about efficiency. That is set by flow temperature (≈2-3 % COP per K) and by the restart hysteresis forcing high setpoints, not by timing.
  - None of the DP figures above account for the current controller's 31-39 °C catch-up behaviour. Against that real baseline, savings from a lower and steadier flow could exceed any timing gain. That is a different lever from the one this claim measures.
- **If the owner is on a time-varying retail plan:**
  - A 17-21 space-heating block with pre-charge before 17 is a reasonable low-complexity first step. Expect about 1/3-1/2 of the full DP value with a ±1 K band, not 2/3.
  - It is worth roughly 3-9 % of space-heating cost with a ±1 K band, and ~0-1 % with ±0.5 K [V].
- **Comfort band choice dominates.** The value differs about 3-10× between ±0.5 K and ±1 K. The owner's 22.0 °C target with a ±0.5 K tolerance leaves little to optimise.

## Sources

1. Thorsteinsson et al., "Long-term experimental study of price responsive predictive control in a real occupied single-family house with heat pump", Applied Energy 347 (2023), arXiv 2303.16289 - https://ar5iv.labs.arxiv.org/html/2303.16289 - **field data** (97 days, occupied DK house, Bosch 7 kW AWHP, concrete UFH). Cost −12.4 % overall (2.3-32.8 % by comfort level); electricity +9.5 %; Danish tariff 0.027 / 0.081 / 0.26 €/kWh; 66 % estimate (COP 4.2 assumption, consumption moved to 21-01); savings at 0-6 °C, losses at −5-0 °C; model recalibrations.
2. Kuboth et al., "Experimental Long-Term Investigation of Model Predictive Heat Pump Control in Residential Buildings with Photovoltaic Power Generation", Energies 13:6016 (2020) - https://epub.uni-bayreuth.de/5598/1/energies-13-06016.pdf - **controlled lab test, real weather** (125 days, twin rigs, 500 L buffer). Comfort band 20-24 °C; cost −9.0 %, electricity −4.1 %; short tests gave −34 %; more comfort violations under MPC.
3. Péan, Salom, Costa-Castelló, "Review of control strategies for improving the energy flexibility provided by heat pump systems in buildings", J. Process Control (2019) - https://upcommons.upc.edu/bitstream/2117/133051/1/JPC_Submitted%20version.pdf - **peer-reviewed review**. Economic MPC up to 40 % cost cut against heating-curve control; peak blocking 17-34 % (Carvalho); ±2 K price set-points 3-10 % (Le Dréau & Heiselberg); 31 % vs 27 % with perfect vs no forecast.
4. Halvgaard, Poulsen, Madsen, Jørgensen, "Economic Model Predictive Control for building climate control in a Smart Grid", IEEE ISGT 2012 - https://doi.org/10.1109/ISGT.2012.6175631 (abstract via https://api.openalex.org/works/doi:10.1109/ISGT.2012.6175631) - **peer-reviewed simulation**. Ground-source heat pump with floor heating; 25-35 % cost saving against constant-price operation.
5. "Occupant-oriented demand response with multi-zone thermal building control", Applied Energy (2023) - https://doi.org/10.1016/j.apenergy.2023.121454 (abstract via OpenAlex) - **peer-reviewed simulation**. Ideal MPC >39 % and a model-free price-storage controller 22 % cost cut against two-point hysteresis, for a high-capacitance building with wider permitted temperatures.
6. ESO, "Gaminančių vartotojų atsiskaitymo būdai 2026 metais" - https://www.eso.lt/namams/elektra/tarifu-planai-kainos-atsiskaitymas/gaminanciu-vartotoju-atsiskaitymo-budai-2026-metais/4829 - **regulated tariff**. Returned energy 0.0726 €/kWh (low voltage), no time-of-day differentiation; alternative methods (5.0336 €/kW/month; 37 % retention).
7. ESO, "Atsiskaitymo būdo skaičiuoklė" - https://www.eso.lt/namams/gaminantis-vartotojas/atsiskaitymo-budo-skaiciuokle/3969 - **operator guidance**. Monthly netting, two-year bank (1 Apr-31 Mar), fed-in energy stored in one zone, shortfall split across zones by the month's consumption.
8. Elering Nord Pool price API, LT area, Oct-Apr 2023-24, 2024-25 and 2025-26 - https://dashboard.elering.ee/api/nps/price - **market field data, own analysis [V]**. Nov-Mar: 00-06 at −34 to −45 €/MWh vs mean; 17-21 at +24 to +45 €/MWh.
9. Open-Meteo historical weather (ERA5), Vilnius hourly temperature and shortwave radiation, 2023-10-01 to 2026-04-30 - https://archive-api.open-meteo.com/v1/archive?latitude=<site>&longitude=<site>&start_date=2023-10-01&end_date=2026-04-30&hourly=temperature_2m,shortwave_radiation&timezone=Europe%2FVilnius - **reanalysis data, own analysis [V]**. Load and PV inputs for the re-implemented DP. PV was crudely modelled as 15 kWp × GHI × 0.75 × 1.6 tilt factor.
10. Clauß & Georges, "Model complexity of heat pump systems to investigate the building energy flexibility and guidelines for model implementation", Applied Energy 255 (2019) - https://doi.org/10.1016/j.apenergy.2019.113847 (abstract via OpenAlex) - **peer-reviewed simulation**. Simplified heat pump control models change demand-response key figures significantly, and domestic hot water priority can pull in auxiliary heaters. This supports treating simplified-model DP results as order-of-magnitude only.

The re-implementation script and the downloaded data are in the session scratchpad (`sim/dp.py`, `data/`), not in the repo.
