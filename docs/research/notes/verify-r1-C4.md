# Verify r1 – C4: cycling cost, run-length knee, per-start cost

## Claim

C4: Cycling has no measurable efficiency cost once the average run exceeds about 45–60 min (the "field knee"). Within a system, it costs about 0.15–0.35 % per extra start per day. Runs of 0.5–4 h are therefore harmless.

## Verdict: partly_supported

- **The direction and magnitude are right.** At 0.5–4 h runs, start-up transients cost a few percent at most, and usually less. That is far smaller than the cost of 1 K of extra flow temperature (about 2–3 % of COP per K).
- **"No measurable cost above 45–60 min" is too strong.** In my independent within-system re-analysis of heatpumpmonitor daily data [3], efficiency keeps rising slowly beyond 60 min. A multi-hour run beats a 45–60 min run by about 1–2 % of %-Carnot. A first-principles simulation finds a 3.4 % COP penalty inside a single 1-hour on-cycle [5].
- **The per-start cost does not vanish above the knee.** Days whose average run is ≥ 60 min still show about −0.24 to −0.31 % per extra start per day in the 0–8 °C band [3].
- **The "45–60 min knee" is not a physical threshold.** It is where a cross-sectional curve flattens. The cross-sectional field figure (about −19 % below 15 min) is heavily confounded. Within-system the penalty for 10–20 min runs is only about −3 to −6 % [3].
- **Lab knees are much shorter.** Lab knees (about 6–8 min, fixed-speed ASHP [1]) and simulation knees (about 15–20 min [2]) are much shorter than the field knee. They measure the start-up transient only, not the other problems that come with short runs.

## Corrected claim

- **Per start, a start-up transient costs about 0.4–2 minutes of full output.** For an EEV unit the measured heat deficit is about 100–130 s at 75–85 % capacity. The electricity deficit is about 60–90 s at 95–100 %. TEV units are worse: 240–300 s at 55–65 % [4]. Units with refrigerant migration can take about 12 min to reach 90 % capacity [5].
- **As a share of the run, that is:**
  - 10 min run: about 3–15 %
  - 30 min run: about 1–6 %
  - 60 min run: about 0.5–3 %
  - 3 h run: about 0.2–1 %

  These figures are my arithmetic from [4][5].
- **Field data, within the same system, same 3 K outdoor band, mostly space-heating days, %-Carnot relative to that system's band mean** [3] (66 underfloor-heating systems, 9,113 days). Runs here are the day's average run, and starts are counted with a 100 W threshold.

  | Average run | Relative %-Carnot |
  |---|---|
  | 15–20 min | −1.8 % (median) / −5.0 % (mean) |
  | 30–45 min | −1.2 / −1.5 % |
  | 45–60 min | −0.7 / −0.9 % |
  | 60–90 min | −0.1 / −0.3 % |
  | 90–180 min | +0.8 % |
  | > 300 min | +1.4 % |

  So the whole spread between 0.5 h runs and multi-hour runs is about 2–3 %.
- **Per extra start per day, within system** [3]:
  - 0–8 °C outdoor: about −0.24 % (all days), −0.31 % (days with run ≥ 60 min) and −0.38 % (≤ 24 starts/day).
  - 8–14 °C outdoor: about −0.05 to −0.12 %.
  - Below 0 °C: too few days to tell, and the sign is unstable.

  The claimed 0.15–0.35 % is a fair summary for 0–8 °C. It holds as a cost per start at any run length, not only below the knee.
- **Conditions.** These figures hold for UK and EU inverter ASHPs with mostly low flow temperatures. Start counts use a 100 W power threshold [6], and %-Carnot is computed by heatpumpmonitor (defrost included). They do not cover compressor wear, oil return or warranty limits, which are separate constraints (max about 6–12 starts/h, minimum runs for oil return; Gree imposes a 3-min restart delay).

## Evidence for

- **EA Technology lab tests** on a test house with a fixed-speed 6 kW ASHP and radiators [1]: run-time effects were small beyond about 3.5–8.3 min, and most of the gain was reached at about 6 min. The recommended design minimum was about 6 min. The worst-case COP loss was about 16 % (GSHP, 1.6-min runs). Runs above 30 min would be far above this knee.
- **RHPP field trial** (about 700 UK sites, 2-min data) [7]: no correlation between median cycle length and monthly COP, even though the ASHP median cycle was 10 min. The authors caveat heat-metering error and the definition of a cycle.
- **Brudermueller et al.** (503 Swiss heat pumps, smart-meter data) [2]: some units cycle atypically without being inefficient. The paper cites minimum-run recommendations of 15 min (Uhlmann & Bertsch) and 20 min (Waddicor et al.). Neither is anywhere near 45–60 min.
- **My within-system re-analysis** [3] confirms the per-start magnitude (0.1–0.4 %/start/day). It also confirms that the curve is essentially flat (within about ±1 %) from 60 min to 5 h.
- **Energy Stats UK** (owner data, 5 kW Vaillant) [8]: mild-weather cycling of 20 min on / 60 min off at 14 °C, and 80/30 min at 8 °C, has only a "small effect". Under 1–2 cycles per running hour is considered fine.

## Evidence against / contradictions

- **The cost continues past the "knee".** In the data in [3], days with runs ≥ 60 min still pay about 0.24–0.31 % per extra start per day (0–8 °C). The long-run plateau rises about 1.5–2 % from 45–60 min to more than 5 h. "No measurable cost" is therefore wrong in the strict sense. Above 60 min the cost is small, not zero.
- **MERL simulation** (ASHP, refrigerant migration, ICR 2023) [5]: after a 20-min off period, the average COP over the following 1-hour on-cycle was 3.4 % lower than with no migration. Capacity rise time was 723 s, or 168 s with a regenerative accumulator. For such a unit, even a 60-min run carries a 3 % penalty.
- **Dongellini** (air-to-water, manufacturer test data) [4]: each start loses about 31 % of heat over the first 250 s (EEV case study). At a minimum output of 3.75 kW that is about 0.08 kWh per start, about 2 % of a 60-min run and about 0.7 % of a 3-h run. This is consistent with a small but non-zero cost at 0.5–4 h.
- **Fuentes / Waddicor et al.** (lab, water-to-water) [9]: start-up losses are "non-negligible" and grow strongly as system inertia falls (1.23 → 24.7 L/kW tested). The knee depends on the hydraulic system, not on a universal number of minutes.
- **The size of the field knee is itself an artefact.** The −19 % cross-sectional figure below 15 min shrinks to about −3 to −6 % (UFH means) within a system [3]. Short-run systems are also oversized, run hotter or have zoning problems.
- **Start counting is imperfect.** The 100 W threshold can count circulation-pump activity as starts (one Daikin draws about 180 W with the pump only). One Vaillant comparison undercounted by about 4 % [6]. DHW switches also create "starts".

## Applicability to this house

- **Gree Versati, inverter, minimum output about 3.7–3.8 kW, mild-weather load about 1.7 kW.** At 0.5–4 h runs, transients cost roughly 0.2–6 % per run. The realistic band is about 0.5–3 % for 1–3 h runs. Over a mild day with 4–8 starts, that is about 1–2 % of daily energy.
- **Going from about 6 to about 12 starts/day in the 0–8 °C band** costs about 1.5–2 % (field slope [3]). Lowering the mean flow temperature by 1 K is worth about 2–3 %. Trading a few extra starts for 2–4 K lower water is therefore clearly favourable, provided runs stay well above about 20–30 min and stay within the unit's start limits (3-min restart).
- **The real cycling cost in this house is probably not the transient.** The firmware restarts only when the setpoint is 4–5 K above the outlet temperature, and it stops on overshoot. Each cycle therefore forces higher water temperatures than continuous low-output running would. EA Technology noted that cooler short runs can beat hotter long runs [1]. A controller should target low lift first and run length second.
- **Design guidance:**
  - Minimum run about 30 min as a soft target and about 20 min as a hard floor.
  - Prefer 1–3 h pulses in mild weather.
  - Do not chase runs longer than 60–90 min at the cost of higher flow temperature.
  - Measure this unit's own start-up deficit, i.e. the heat over the first 15 min compared with steady state.
  - Count starts from the compressor-frequency register, not from a power threshold.
- **Wear** (starts per year, oil return) is a separate constraint that efficiency data does not capture.

## Sources

1. R. Green, "The Effects of Cycling on Heat Pump Performance" (Project 46640), EA Technology for DECC, 2012. https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/65695/7389-effects-cycling-heat-pump-performance.pdf. Lab (test house). Full text read.
2. T. Brudermueller et al., "Large-scale monitoring of residential heat pump cycling using smart meter data", Applied Energy 350 (2023) 121734. https://www.Uni-Bamberg.de/fileadmin/eesys/Publications/1-s2.0-S030626192301098X-main.pdf. Field data (503 heat pumps) plus literature review. Full text read.
3. heatpumpmonitor.org daily system data (public), my independent within-system re-analysis, 2026-11-06. https://heatpumpmonitor.org/system/list/public.json and https://heatpumpmonitor.org/system/stats/last365. Measured field data. Filters: quality ≥ 95 %, DHW heat < 10 % of space heat, ≥ 5 kWh/day; fixed effects for system × 3 K outdoor band; 117 systems / 12,749 days, of which 66 UFH systems / 9,113 days. Script(analysis script, not committed)
4. M. Dongellini, "Dynamic modeling and seasonal performance evaluation of air-to-water heat pump systems", PhD thesis, University of Bologna, 2017. https://amsdottorato.unibo.it/id/eprint/7901/. Simulation with manufacturer transient measurements (Table 4.1: start-up penalty factors for TEV and EEV).
5. H. Qiao, C. R. Laughman, "Theoretical analysis of cycling losses in air source heat pump systems", MERL TR2023-127 (ICR 2023). https://www.merl.com/publications/docs/TR2023-127.pdf. Peer-reviewed simulation.
6. "HeatpumpMonitor.org starts & starts per hour", OpenEnergyMonitor forum, 2024. https://community.openenergymonitor.org/t/heatpumpmonitor-org-starts-starts-per-hour/26246. Forum / method description.
7. J. Love et al., "Investigating variations in performance of heat pumps installed via the RHPP scheme", UCL/RAPID-HPC for BEIS, 2017. https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/606829/DECC_RHPP_160428_On_performance_variations_v20.pdf. Field data (2-min). Cycling section read.
8. "Heat pump cycling", Energy Stats UK. https://energy-stats.uk/heat-pump-cycling/. Owner blog with measured data.
9. E. Fuentes, D. A. Waddicor, J. Salom, "Improvements in the characterization of the efficiency degradation of water-to-water heat pumps under cyclic conditions", Applied Energy 179 (2016) 778–789. https://ideas.repec.org/a/eee/appene/v179y2016icp778-789.html. Lab (abstract only).

Note: the web-search budget ran out after 7 searches; the shared per-turn limit had been used up by other agents. The Swedish, Dutch, Lithuanian and further Polish/German queries were therefore not run. Evidence from those communities is not represented here, beyond the earlier German and Polish snippets, which offered only unsourced rules of thumb: for example, 15–20 % loss below 6 min, and 30–60 min "ideal" runs according to alpha innotec, via a German advice site.
