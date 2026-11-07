# Gap R2-G2: For a household with a 15 kW PV array and a hybrid battery in Lithuania in 2026, what are the actual settlement options and prices: net-metering or 'returned energy' fee per kWh, whether the settlement is annual or monthly, spot-indexed versus fixed plans, ESO zone hours for households, and any capacity or power-based network charge?

**Method note.** The shared WebSearch budget for this run was already used up when this gap started: all 3 searches I tried were refused. So this note is built from:
- direct fetches of primary pages: ESO (the distribution operator), Ignitis (the largest supplier), and VERT (the regulator);
- my own analysis of **all 15-minute Nord Pool LT day-ahead prices from January to October 2026**, downloaded from Elering's public API [19].

Figures marked **[C]** are my own calculations. Elektrum and Enefit pages were blocked (HTTP 451/403), so I have no competitor price quotes. That gap is listed below.

## Summary

1. **Under net metering the house is settled in kWh, not euros, and the bank lasts 2 years.**
   - The meter nets monthly: export minus import. Any surplus carries into later months [3][4][8].
   - The current period runs from **1 April 2026 to 31 March 2028**. The previous one ran from 1 April 2024 to 31 March 2026 [8][10].
   - At the end of a period, leftover kWh are not carried over. The supplier compensates them under its contract terms [8][9].
   - A 15 kWp array (~14.5 MWh/yr per PVGIS, note 10) almost certainly builds a summer bank larger than the winter shortfall. So **winter heat-pump kWh are probably drawn back from the bank, not bought** [C].

2. **The returned-energy fee is 0.0726 €/kWh at low voltage in 2026** [1][8].
   - It applies to every banked kWh drawn back. There is no monthly fee.
   - Ignitis states the prices include VAT, so this is 0.060 €/kWh before VAT [8][C].
   - A drawn-back kWh pays no energy component and no public-interest (VIAP) component [4].

3. **ESO offers four prosumer settlement methods; one can be changed once every 12 months** [1][8]:
   - (a) 0.0726 €/kWh for returned energy;
   - (b) **5.0336 €/kW of permitted generation power per month**. For 15 kW that is about 906 €/yr, clearly bad here [C];
   - (c) the operator keeps **37 %** of exported kWh at low voltage (21 % at medium voltage), with no fee. ESO recommends this when generation exceeds **140 %** of annual consumption [1];
   - (d) pay the network tariff of your own plan for each returned kWh. Ignitis quotes 0.10527 €/kWh for one-zone Standartinis and recommends it for rooftop systems above 13 kW [8].
   - A change takes effect on the 1st of the next month [1].

4. **What a winter grid kWh really costs depends on the scheme, not the clock** [C]:
   - On net metering with an annual surplus, the marginal cost is about **0.07 €/kWh (method a)**, or about **0.00-0.04 €/kWh (method c)**, at any hour.
   - For method (c), the cost is the lost end-of-period compensation of a banked kWh. ESO's published weighted price of fed-in energy in April-September 2026 was **0.038-0.047 €/kWh** [4], and compensation sits at or below that.
   - On a plain spot or fixed retail plan without a bank, a kWh costs **0.19-0.38 €/kWh**, so time of day matters a lot (point 9).

5. **Net billing is the euro-based alternative and is clearly worse for this house** [9][19][C].
   - Export is valued at the Nord Pool LT price minus an Ignitis admin fee of **0.0247 €/kWh** (from 1 April 2026). Imports are paid at full retail.
   - Midday LT prices from April to August 2026 averaged **19-46 €/MWh** [19]. So a summer export is worth only about **0-0.02 €/kWh**.
   - It is mandatory only for wind; solar owners may choose it [10]. It can be switched once per accounting period [9].

6. **Time zones on net metering barely matter.**
   - Surplus is banked as one zone [3].
   - Any shortfall is split across zones in the same proportion as that month's consumption [3][4].
   - So moving load from day to night only changes the price of the *non-banked* shortfall.

7. **ESO household time zones (local time)** [12]:
   - **Two-zone:** day rate on workdays 07:00-23:00 in winter time and 08:00-24:00 in summer time. Night rate covers all other hours plus whole weekends.
   - **Four-zone (same all year):** night 22-05, morning 05-07, day 07-17, evening 17-22. On weekends and public holidays: day 07-22, night 22-07.
   - Public holidays include 1 Jan, 16 Feb, 11 Mar, 1 May, 24 Jun, 6 Jul, 15 Aug, 1 Nov and 24-26 Dec [12].

8. **ESO 2026 network prices (low voltage, incl. VAT)** [2]:

   | Plan | One-zone | Two-zone (day / night) | Four-zone (night / morning / day / evening) | Fixed fee |
   |---|---|---|---|---|
   | Standartinis | 0.11132 | 0.12947 / 0.07139 | 0.06292 / 0.08349 / 0.10406 / 0.14641 | none |
   | Namai | 0.09559 | 0.11011 / 0.06171 | not offered | 3 €/month |
   | Efektyvus | 0.08833 | 0.10164 / 0.05687 | 0.05082 / 0.06534 / 0.08228 / 0.11374 | 1 €/kW/month |

9. **2026 LT spot prices** (my analysis of 15-minute data [19]):
   - **January-February:** mean **152-155 €/MWh**. 00-06 was **56-62 €/MWh below** the mean, and the daily max-min spread was about 190 €/MWh.
   - **March-September:** **midday (11-16) was the cheapest time of day**, at 19-60 €/MWh, below the night. The peak was at 19-21.
   - **October:** night was cheapest (~82-90 €/MWh), midday ~94, peak 165 at 18:00.
   - Note 10 assumed "night always cheapest". That holds only from about November to February.

10. **There is no measured-peak (kW demand) network charge for households** [2][13].
    - The only power-based item is the optional **Efektyvus** plan: 1 €/kW/month of the site's *permitted connection power* (example: 3 kW → 3 €/month) [13]. In exchange, energy rates are about 0.023 €/kWh lower [2].
    - Since it is not a measured peak, no peak-shaving rule follows from it.

11. **Retail supply options in 2026:**
    - **Ignitis "Išmanus-15":** 15-minute Nord Pool price plus a supplier fee fixed until 31 December. Billed as the month's 15-minute consumption-weighted average. For prosumers only the shortfall is billed [7][11].
    - **"Išmanus-Mėnesinis":** monthly-average Nord Pool price [7][21].
    - **Fixed "Optimalus" (new customers, start 1 Dec 2026, fixed for 18 months):** one-zone **0.269 €/kWh**, two-zone **0.317 / 0.199 €/kWh** day / night, plus 2 €/month, all incl. VAT and the Namai network part [14].
    - **Public supply** is limited to vulnerable customers and households using under 1,000 kWh/yr. Second-half 2026 Standartinis one-zone is 0.240 €/kWh [13][17]. Not relevant for this house.

12. **New charges for prosumers are coming.** On 8 October 2026 VERT set a method for charging prosumers part of the suppliers' public-interest (VIAP) cost, capped at **1 ct/kWh** for prosumers versus 0.3 ct/kWh for other consumers [15]. The date and the base it applies to are not yet published. Expect drawn-back kWh to cost roughly 0.07-0.08 €/kWh.

13. **Battery rules are not documented online.** ESO's battery pages give no settlement rules for batteries [5]. Grid-charging a battery to arbitrage, or exporting from it, is unclear under net metering. Treat it as not allowed until ESO confirms.

## Detailed findings

### 1. Net metering ("dvipusė apskaita"): how the bank works

- **Monthly netting [3][4][8].**
  - ESO reads smart meters remotely every month.
  - If export exceeds consumption, the excess is added to the bank ("sukauptas kiekis") and carried forward.
  - If consumption exceeds export, the deficit is drawn from the bank first. Only what the bank cannot cover (the "trūkstamas kiekis") is bought from the supplier.
- **Accounting period.**
  - ESO's calculator page and Ignitis both give two-year periods running 1 April to 31 March. The current one is **1 April 2026 to 31 March 2028** [3][8][10].
  - Kilowatt-hours left at 31 March 2026 were cancelled from the bank and compensated by the supplier "under contract terms". Ignitis offered a bill discount by default, or a payout [8][9]. An earlier cancellation happened on 31 March 2024 [4].
  - ESO publishes an "average weighted price of fed-in energy": **0.03808-0.04742 €/kWh** for April-September 2026. It adds that suppliers are *not obliged* to compensate at that price [4].
- **The ESO fee per drawn-back kWh** (the "atgautas kiekis") **is 0.0726 €/kWh at low voltage** [1][8].
  - ESO says drawn-back energy carries no energy component and no VIAP component [4], so the network fee is the whole cost.
  - Ignitis labels its numbers "with VAT, from 1 January 2026" [8]. 0.0726 / 1.21 = 0.0600, which supports a VAT-inclusive reading [C].
- **Time zones [3][4].** Banked energy is stored as one zone. The shortfall is split by the month's own consumption split. ESO's example: 100 kWh shortfall with 60/90 day/night consumption becomes 40 kWh day and 60 kWh night [4].
- **Spot plan plus net metering [11].** On Išmanus-15 the bill uses the same 15-minute weighted price, applied only to the shortfall.
  - Ignitis does not say which 15-minute profile weights the shortfall. Most likely it is the whole month's consumption profile, which would dilute any time-shifting benefit. Flagged as open.
- **Rough annual balance for this house [C]** (low-medium confidence; actual meter data would settle it):
  - PV is ~14.5 MWh/yr (note 10, PVGIS, snow-free).
  - Heat-pump space heating is ~4.1 MWh_el for October-April, from the daily figures in note 10.
  - DHW plus household use is assumed at 4-5 MWh.
  - If ~40 % of PV is self-consumed, export is ~8.5 MWh and grid draw ~4-5 MWh, mostly November-February.
  - So the bank should cover all of winter with ~4 MWh to spare per year. In that regime **the winter marginal price is flat across the day**.

### 2. The four ESO settlement methods compared for this house [1][8][C]

| Method | 2026 price | Annual cost if 4.5 MWh is drawn back and 8.5 MWh exported [C] | Marginal cost of 1 extra winter grid kWh |
|---|---|---|---|
| (a) per returned kWh | 0.0726 €/kWh | ≈ 327 € | 0.0726 € + lost compensation of 1 banked kWh (~0.02-0.04) ≈ **0.09-0.11 €** |
| (b) per kW of permitted generation | 5.0336 €/kW/month | 15 kW → ≈ 906 € | ≈ 0 network, but a large fixed fee |
| (c) 37 % kept by operator | 63 % of export banked | bank 5.36 MWh ≥ 4.5 MWh → **≈ 0 €** | only lost compensation ≈ **0-0.04 €** |
| (d) at own network tariff | e.g. 0.10527 €/kWh (one-zone Standartinis) | ≈ 474 € | ≈ 0.11-0.13 € |

- **Eligibility for (c).** ESO recommends (c) above 140 % generation/consumption at low voltage [1]. Ignitis's own text gives inconsistent thresholds (40 % vs 130 %) [8].
- With ~14.5 MWh of generation against ~8.5-9.5 MWh of consumption, the ratio is about 150-170 %. That is close enough that **(c) may beat (a) by up to ~300 €/yr** [C]. It must be checked against the owner's real meter data.
- **Changing method [1].** Allowed once per 12 months, or within one month after VERT publishes new prices (that triggers a new 12-month period). It takes effect on the 1st of the following month.

### 3. Net billing ("grynasis atsiskaitymas") [9][10]

- Each kWh exported is credited in euros: Nord Pool LT price for the period minus **0.02470 €/kWh** (Ignitis, valid from 1 April 2026). The credit goes into a "virtual wallet".
- Consumption is paid from the wallet, and Ignitis says that part carries no VAT.
- Periods: 1 January 2024 to 31 March 2026, then 1 April 2026 to 31 March 2028.
- A cash payout counts as personal income; the page mentions income tax from 2,500 € [9].
- With 2026 midday spot at 19-46 €/MWh in April-August [19], a summer export earns **≈ 0-0.02 €/kWh**, while a winter import costs 0.19-0.38 €/kWh [C].
- Under net billing, both self-consumption and timing would be worth a lot. Under net metering they are worth little.
- Switching scheme is allowed once per accounting period [9].

### 4. ESO household tariff structure and hours [2][6][12][13]

- **Network prices** are in Summary point 8.
- Tiny extra items: VIAP is −0.00053 €/kWh incl. VAT and the household distribution supplement is +0.00027 €/kWh [2][14].
- **Changing plan:** the network plan or zone count can be changed once per month, effective the 1st of the next month. A zone change can take up to 5 days, because the meter is reprogrammed [6].
- **Four-zone plans** need a smart meter set up for four zones [13].
- **Zone hours** are in Summary point 7 [12]. ESO's own tariff page lists the same windows, but only under medium voltage [2]. Ignitis states they apply to households all year [12]. Two-zone uses clock-shifted hours in summer time.
- **Capacity or power charges:**
  - Households pay no measured-demand charge [2].
  - Efektyvus charges 1 €/kW/month on the property's *permitted/connection power* [13].
  - The prosumer method (b) charges per kW of *permitted generation power* [1].
  - Neither depends on how the heat pump behaves.
- **Efektyvus versus Standartinis (one-zone):**
  - It saves 0.023 €/kWh, so the break-even is about 43 kWh/month per kW of permitted power [C].
  - For a site with, say, 20 kW permitted, that is ~870 kWh/month of *network-billed* kWh.
  - On net metering, banked kWh do not pay the plan's network rate, so Efektyvus is probably not worth it [C].

### 5. Spot prices in 2026 and what they imply [19][C]

15-minute LT day-ahead data, Vilnius local time, January-October 2026.

| Month | Mean €/MWh | 00-06 vs mean | 10-16 vs mean | 17-21 vs mean | Cheapest hour (mean) | Dearest hour | Mean daily max−min |
|---|---|---|---|---|---|---|---|
| Jan | 152 | −62 | +38 | +33 | 03 (87) | 16-17 (203) | 191 |
| Feb | 155 | −56 | +26 | +35 | 04 (92) | 09 (211) | 194 |
| Mar | 82 | −14 | −41 | +46 | 14 (30) | 19 (146) | 198 |
| Apr | 58 | −2 | −30 | +13 | 14 (19) | 20 (107) | 125 |
| May-Aug | 75-94 | −4 to +17 | −33 to −48 | +2 to +22 | 14-15 (22-39) | 20-21 (139-184) | 135-197 |
| Sep | 108 | −19 | −38 | +42 | 14 (56) | 20 (181) | 196 |
| Oct | 114 | −27 | −13 | +46 | 03 (82) | 18 (165) | 173 |

- **Two-zone split of spot alone.** Weekday-day versus night-and-weekend averaged 201 vs 109-114 €/MWh in January-February, but only 94 vs 72 in March [C].
- **Retail on Išmanus-15 plus two-zone Standartinis, January 2026 [C].** Assumes a supplier fee of ~10 €/MWh (margin not published) and spot × 1.21 VAT:
  - night ≈ (0.090 + 0.010) × 1.21 + 0.071 ≈ **0.19 €/kWh**;
  - weekday day ≈ (0.19 + 0.01) × 1.21 + 0.129 ≈ **0.37 €/kWh**.
  - That is a factor of about 2. It applies **only to non-banked kWh**.
- **Change from note 10's winter data.** Winter 2025-26 (mean 116 €/MWh) understated January-February 2026 (152-155). So in a deficit regime the night advantage is larger than note 10 assumed.
- **Shoulder months.** In March-April and September 2026, midday was *cheaper than night* because of solar oversupply. A "night-first" rule would be wrong then.
- **Negative prices.** Hours at or below 0 €/MWh were rare: 0-3.8 % of intervals per month, at most in April-May.

### 6. Battery

- ESO's storage page is guidance only. It needs an extra smart meter in the distribution board, and the battery's charge and discharge power must stay within the site's permitted power. It gives no settlement rule for batteries [5].
- ESO pages for new batteries (with LGG 0 kW, or with LGG raised up to 100 kW) exist, but render client-side; I could not read them.
- VERT's April 2026 flexible-connection rules can restrict generation during daytime windows (February-March and September-October 07-17; April-August 07-19) for *newly* connected users on constrained grids. Whether they touch batteries is not stated [16].
- **Implication [C].**
  - On net metering with a surplus, a battery cycle that moves PV from noon to evening avoids one returned-energy fee (0.0726 €/kWh) but loses ~10 % in round-trip losses. Worth ~0.06 €/kWh shifted.
  - Under net billing, the same shift is worth ~0.2-0.3 €/kWh.

## What this means for controlling this house

Confidence: **High** on the scheme rules and prices (primary pages). **Medium** on which regime this house is in, because it depends on the owner's meter balance and chosen method, which I could not see.

1. **First action: identify the regime.** Before fixing the controller objective, read three things from the ESO and supplier self-service portals:
   - (i) net metering or net billing;
   - (ii) ESO method (a), (b), (c) or (d);
   - (iii) bank balance through the winter.
   This single fact decides between objective E (minimise kWh) and objective C (minimise €).
   - **Test:** if the bank on 1 November is larger than expected November-March grid draw (~4-5 MWh), use objective E all winter.

2. **Net metering with a positive bank (the probable case): minimise kWh, ignore the clock.**
   - The marginal cost is a flat ~0.07-0.11 €/kWh (method a) or ~0-0.04 €/kWh (method c) at all hours.
   - Any night pre-charging that raises flow temperature, or adds slab losses, *increases* cost.
   - Rules:
     - schedule unavoidable ON blocks in the warmest and sunniest hours;
     - use the lowest flow temperature that holds 22.0 °C;
     - prefer long runs at minimum modulation over short high-temperature catch-ups.
   - This matches the owner's efficiency goal exactly. Confidence medium-high.

3. **Keep a small PV and battery preference, sized to the fee.**
   - With method (a), a PV kWh used directly (or via the battery) saves 0.0726 €/kWh compared with exporting and drawing back. That is equal to about **25-30 % of the electricity cost of a winter kWh at COP ≈ 3.5-4**, so not trivial in October-November and February-April.
   - Rule: from October to April, place the forced ON block where expected PV surplus is at least 1 kW, if the comfort band allows.
   - Do not raise flow by more than ~2 K for it: 2-3 %/K COP loss (note 02) against a ≤ 0.07 €/kWh benefit.
   - Under method (c), drop this preference to near zero.

4. **Without a bank (net billing, or bank exhausted): switch to objective C with season-aware price windows.**
   - **November-February:** night 00-06 is about 0.18 €/kWh cheaper on a spot plus two-zone plan. Shifting is worth it within a ±1 K slab band (note 10: −5 to −10 % cost).
   - **March-April and September:** midday 11-16 is the cheapest *and* warmest window. Never apply a fixed "night-first" rule.
   - **All months:** avoid 17-21 (spot +13 to +46 €/MWh; four-zone evening network 0.146 €/kWh).
   - Use the published day-ahead 15-minute prices (out by 15:00 for the next day [7]) instead of hard-coded windows.

5. **DHW timing.**
   - On net metering with a bank: run DHW in the warmest or PV hours (13-15).
   - Without a bank, in November-February: at 01-05.
   - The legionella immersion cycle (resistive, COP 1) should run at the PV peak in any regime. The kWh saving dominates, and in the no-bank case it also avoids a 2× price.

6. **No peak-power rule is needed.** No measured kW demand charge exists for households [2]. Do not add logic to cap heat-pump power for tariff reasons. The only power limits are the site's permitted import and generation powers, which also bound the battery [5].

7. **Network plan suggestion (to verify on the bill).**
   - With net metering and a winter bank, the network plan only prices the shortfall. Standartinis with no fixed fee is likely best, and two-zone or four-zone adds nothing.
   - If the house is in deficit or on net billing, **two-zone Namai or Standartinis** captures the night discount. Four-zone adds the costly 17-22 window (0.146) and only helps if evenings are avoided.
   - Low confidence; this is a billing choice, not a control choice.

8. **Things to avoid.**
   - Building PV-chasing or price-chasing logic that raises flow temperature on the assumption that grid kWh cost ~0.25-0.30 €/kWh. Under net metering with a bank, that assumption is wrong by a factor of 3-4.
   - Grid-charging the battery at night for arbitrage until ESO confirms how a battery is metered under net metering.

## Contradictions and open questions

1. **Bank expiry wording conflicts.**
   - ESO's calculator says surplus accumulates "for two years, 1 April-31 March" [3].
   - Ignitis gives net metering a 2024-04-01 to 2026-03-31 period, but net billing a 2024-01-01 start [9][10].
   - The same Ignitis page also says unused energy "until 31 March 2026 is cancelled" [8].
   - My reading: two-year periods, the first ending on 31 March 2026, the current one ending on **31 March 2028**. Confirm in the ESO self-service portal.
2. **Price of method (d).** Ignitis quotes 0.10527 €/kWh for one-zone Standartinis [8]. ESO's tariff table shows 0.11132 €/kWh [2]. The 0.006 gap is unexplained; perhaps a component is excluded.
3. **VAT on 0.0726.** ESO's prosumer page does not say [1]. Ignitis says prices include VAT [8]. The round 0.0600 before VAT supports VAT-inclusive.
4. **Compensation price for leftover kWh.** No supplier published a rate. ESO's weighted fed-in price (0.038-0.047 €/kWh in April-September 2026) is "not binding" [4]. This sets the marginal value of exporting under net metering with a surplus.
5. **Shortfall weighting on Išmanus-15.** Ignitis does not say whether the shortfall uses the whole-month profile or only the deficit intervals [11]. This decides whether time-shifting helps a prosumer in deficit at all.
6. **Battery metering and grid charging under net metering** are undocumented in readable pages [5].
7. **The new prosumer VIAP charge** (≤ 1 ct/kWh [15]): start date, and whether it applies to export, drawn-back or all kWh, are unknown.
8. **Competitor offers** (Elektrum, Enefit, others): spot margins and prosumer buy-back rates were not reachable (HTTP 451/403), and the VERT comparison calculator renders client-side.
9. **The 140 % rule for method (c) and the actual annual balance.** Ignitis's own example thresholds (40 % vs 130 %) are inconsistent [8]. The owner's real 12-month generation and consumption are needed.
10. **Note 10 versus 2026 data.** Note 10's "night cheapest, midday above mean" held for November-February but not for March-September 2026, when midday was below the night price [19]. Note 10's day and night retail estimates are also about 20-25 % low for January-February 2026, because spot means were higher.

## Sources

1. Gaminančių vartotojų atsiskaitymo būdai 2026 metais - ESO - 2026 - https://www.eso.lt/namams/elektra/tarifu-planai-kainos-atsiskaitymas/gaminanciu-vartotoju-atsiskaitymo-budai-2026-metais/4829 - regulated tariff - The four prosumer methods and 2026 prices (0.0726 €/kWh; 5.0336 €/kW/month; 37 %/21 %; own tariff), the 140 % rule, and change rules.
2. Tarifų planai ir kainos 2026 metais - ESO - 2026 - https://www.eso.lt/namams/elektra/tarifu-planai-kainos-atsiskaitymas/tarifu-planai-ir-kainos-2026-metais/4801 - regulated tariff - One-, two- and four-zone household network prices for Standartinis, Efektyvus and Namai incl. VAT; VIAP and supplement items; zone hours listed only under medium voltage.
3. Atsiskaitymo būdo skaičiuoklė - ESO - 2026 - https://www.eso.lt/namams/gaminantis-vartotojas/atsiskaitymo-budo-skaiciuokle/3969 - regulated operator guidance - Monthly netting, two-year 1 April-31 March bank, and shortfall split across zones by the month's consumption.
4. Gaminančių vartotojų atsiskaitymo būdai (business page) - ESO - 2026 - https://www.eso.lt/web/verslui/elektra/tarifai-kainos-atsiskaitymai-ir-skolos/gaminanciu-vartotoju-atsiskaitymo-budai/3885 - regulated operator guidance - Drawn-back kWh free of energy and VIAP components; worked zone-split example; weighted fed-in price 0.038-0.047 €/kWh for April-September 2026.
5. Elektros energijos kaupikliai - ESO - 2025/26 - https://www.eso.lt/namams/gaminantis-vartotojas/elektros-energijos-kaupikliai/3288 - operator guidance - Battery guidance (extra meter, power limits); no settlement rules.
6. DUK: Tarifų planas - ESO - 2026 - https://www.eso.lt/duk/tarifu-planas-177 - operator FAQ - Plan changeable once a month, effective the 1st; a zone change needs meter reprogramming (up to 5 days).
7. Išmanus-15 elektros tiekimo planas - Ignitis - 2026 - https://ignitis.lt/ismanus-15-elektros-tiekimo-planas - supplier - 15-minute Nord Pool pricing, prices published by 15:00, smart meter required, Mėnesinis variant.
8. Dvipusė apskaita (net metering) - Ignitis - 2026 - https://ignitis.lt/dvipuse-apskaita-net-metering - supplier - kWh banking, monthly netting, two-year period, compensation of leftovers, four ESO methods with VAT-inclusive prices incl. 0.10527 €/kWh for method (d).
9. Grynasis atsiskaitymas (net billing) - Ignitis - 2026 - https://ignitis.lt/grynasis-atsiskaitymas-net-billing - supplier - Spot minus 0.0247 €/kWh admin fee, euro wallet, periods, income-tax note, switching rules.
10. Gaminantiems vartotojams - Ignitis - 2026 - https://ignitis.lt/gaminantiems-vartotojams - supplier - Net metering vs net billing availability, period dates, cancellation at 31 March 2026.
11. DUK: Nepriklausomas elektros tiekimas - Ignitis - 2026 - https://ignitis.lt/duk/nepriklausomas-elektros-tiekimas - supplier FAQ - 15-minute weighted-price method, supplier fee fixed to year end, prosumers billed only for the shortfall.
12. DUK: Planai, tarifai, kainos, laiko zonos - Ignitis - 2026 - https://ignitis.lt/duk/planai-tarifai-kainos-laiko-zonos - supplier FAQ - Exact household two-zone and four-zone hours and the public holiday list.
13. Elektra namams (public supply) - Ignitis - 2026 - https://ignitis.lt/elektra-namams - supplier (regulated public supply) - Second-half 2026 public prices, Efektyvus 1 €/kW/month on connection power, eligibility (vulnerable or < 1,000 kWh/yr).
14. Speciali elektros kaina naujiems klientams - Ignitis - 2026 - https://ignitis.lt/speciali-elektros-kaina-naujiems-klientams - supplier - Fixed "Optimalus" 18-month offer: 0.269 one-zone, 0.317/0.199 two-zone, 2 €/month, with component split.
15. VERT nustatė, kaip bus vertinamas gaminančių vartotojų poveikis - VERT - 2026-10-08 - https://www.vert.lt/Puslapiai/naujienos/2026-metai/2026-10-08/VERT-nustate-kaip-bus-vertinamas-gaminanciu-vartotoju-poveikis-elektros-rinkai-ir-tiekejams.aspx - regulator - New prosumer VIAP charge capped at 1 ct/kWh (0.3 ct for others).
16. VERT: lankstesnės sąlygos prisijungti prie elektros tinklų - VERT - 2026-04-30 - https://www.vert.lt/Puslapiai/naujienos/2026-metai/2026-04-30/VERT-sudarytos-lankstesnes-salygos-prisijungti-prie-elektros-tinklu.aspx - regulator - Flexible connection with seasonal daytime generation limits for new users.
17. Patvirtinti 2026 m. II pusmečio visuomeninio tiekimo tarifai - VERT - 2026-05-27 - https://www.vert.lt/Puslapiai/naujienos/2026-metai/2026-05-27/patvirtinti-2026-m--antrojo-pusmecio-visuomeninio-elektros-tiekimo-tarifai.aspx - regulator - +2 ct/kWh from 1 July 2026; 24 ct one-zone; public supply eligibility.
18. Elektros energijos kainos - VERT - 2026 - https://www.vert.lt/elektra/Puslapiai/tarifai/elektros-energijos-kainos.aspx - regulator - Average second-half 2026 public price 23.562 ct/kWh incl. VAT (low voltage).
19. Nord Pool day-ahead prices, LT area, January-October 2026 (15-minute) - Elering public API (dashboard.elering.ee/api/nps/price) - 2026 - https://dashboard.elering.ee/api/nps/price - market data (field data, own analysis [C]) - Monthly means, hour-of-day profiles, day/night splits and spreads in §5.
20. Dėl elektros energiją gaminančių buitinių vartotojų naudojimosi elektros tinklais paslaugų kainų nustatymo 2026 metams (Nr. O5E-1413, 2025-11-27) - VERT - 2025 - https://vert.lt/SiteAssets/posedziai/2025-11-28/pap_buitiniu_vartotoju_paslaugu_kainu_nustatymas.pdf - regulator decision - Confirms the legal basis and date of the 2026 prosumer prices; the body text was not extractable (embedded container).
21. Elektra (independent supply plans) - Ignitis - 2026 - https://ignitis.lt/elektra - supplier - Plan line-up: Minimalus, Optimalus, Išmanus-15 and Išmanus-Mėnesinis.
