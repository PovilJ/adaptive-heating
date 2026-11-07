# Verify R2-C4: water-to-screed conductance and the forced-cycling lift penalty

## Claim

The water-to-screed conductance K_ws is about 0.8-1.8 kW/K for 130 m². The forced-cycling lift penalty at P_min is therefore only 1.5-3.5 K at +10 °C and 0.5-1 K at +2 °C, which is 3-8 % and 1-2.5 % COP, not 3-7 K. (Source: gap-r1-G3.md. It contradicts 03-cycling.md section 5, which uses the full water-to-room UA, and note 02, which uses K_ws = 3.5 kW/K.)

## Verdict: partly_supported

The mechanism is right. During a burst that is short compared with the slab time constant, the extra heat (P − L) only has to cross the water-to-screed resistance, not the full water-to-room resistance. A peer-reviewed, lab-tested TABS pulse-width-modulation method has this structure [1], and my own 2-D transient conduction model of the screed reproduces it [7]. So note 03's 3-7 K, which divides (P − L) by the whole floor UA, overstates the penalty by about 2-3×.

The numbers are about right but slightly too wide.
- **K_ws.** The effective pulse conductance is about **1.1-2.0 kW/K**, not 0.8-1.8.
- **Penalty at +10 °C.** The mean on-time penalty in leaving-water temperature is about **1.4-2.3 K**. Up to about 3 K is reached only at the end of a 4 h run on a 200 mm / 65 mm floor.
- **Penalty at +2 °C.** About **0.4-0.65 K** mean, with an end-of-run peak of 0.6-1.0 K.

No field measurement isolates this quantity, so the evidence is physics plus a calibrated simulation, not measured data.

The search budget for this run was used up before any query ran: all 3 attempted WebSearch calls were refused. The planned 12+ searches, including the German, Polish, Swedish, Dutch and Lithuanian queries, were therefore not done. Evidence comes from 8 documents I fetched and read directly, plus my own simulation.

## Corrected claim

For a 130 m² wet UFH slab (16×2 PE-X, cement screed λ ≈ 1.2 W/(m·K), 45-65 mm cover, 150-200 mm pitch), P_min = 3.75 kW, about 2.0 kW/K water flow and a room held at 22 °C:

**Effective water-to-screed conductance for bursts of 0.5-4 h.** Defined as ΔP / Δ(mean water temperature): about 2.0 kW/K for tile or laminate at 150 mm / 45 mm, and about 1.1-1.5 kW/K at 200 mm / 65 mm. It falls as the run gets longer, because the screed warms.
- The steady water-to-screed-mean conductance is 1.0-1.5 kW/K.
- The conductance from water to the pipe plane only is about 3-4 kW/K. This is note 02's 3.5 kW/K. That value is too high for a node that represents the screed's mean temperature and heat capacity [1][7].

**Lift penalty of delivering the load in P_min pulses**, as leaving water averaged over the on-time, compared with hypothetical continuous delivery at L (simulation [7] + loop ΔT correction):

| Outdoor (load) | 150 mm / 45 mm, tile to laminate | 200 mm / 65 mm, laminate to parquet | End-of-run peak |
|---|---|---|---|
| +10 °C (1.7 kW, duty 45 %) | +1.4-1.9 K | +1.7-2.3 K | +1.8-3.1 K |
| +2 °C (3.1 kW, duty 83 %) | +0.4-0.5 K | +0.5-0.65 K | +0.6-1.0 K |

- In COP terms this is about 3.5-7 % at +10 °C and 1-1.6 % at +2 °C. That uses 2.4 %/K from Gree's own 10 kW rating points [5]. The Carnot sensitivity is about 3 %/K at the low lift of +10 °C weather.
- The penalty scales with 1/(active floor area). If thermostat actuators close loops, or only about 100 m² is really active, multiply by about 1.3.
- A laminar water side (low velocity per loop) adds up to about +0.3 K.

**What a controller should take from this.** The penalty for raising pulse power above P_min is about **0.5-0.9 K per extra kW** (1/K_ws). That is roughly **1.2-2.7 % COP per kW**, before any inverter part-load effect. Keeping pulses near P_min is therefore worth a few percent, not 10-20 %.

## Evidence for

- **Gwerder et al. 2009, lab-tested TABS pulse-width modulation [1].** The method links supply temperature, core temperature and room through a pipe resistance R_t (water to the pipe/core plane) and a core-to-room resistance R̃.
  - The supply-temperature shift needed for pulsed operation depends only on the ratio R_t/(R_t + R̃).
  - Working through the paper's equation 20: shift = q·R_t·(1/duty − 1), i.e. (P − L)·R_t per m². That is the claim's (P − L)/K_ws, not (P − L)/UA.
  - Typical ratios are 20-50 %, so the water-to-room-UA approach overstates the shift 2-5×.
  - Lab values: R_t = 0.060 m²K/W (supply water to core, 150 mm pitch, 20/15 mm pipe, 15 kg/(h·m²), 250 mm concrete slab) and R̃ = 0.16 m²K/W. A 1st-order model was adequate for PWM periods of 5-24 h. The recommended supply shift for PWM is 1-3 K.
- **My 2-D transient finite-difference model of the screed [7].**
  - Set-up: 2.5 mm mesh, half pipe pitch, insulated bottom, top through the covering + 1/10.8 m²K/W to a 22 °C room, pipe wall 0.0196 m²K/W, water side 0.005 m²K/W.
  - Steady-state check: it reproduces EN 1264 K_H. It gives 4.47 W/(m²K) at 150 mm with R_λ = 0.02 and **3.29 W/(m²K) at 150 mm with R_λ = 0.10, against the certified 3.33** [3]; and 2.82 at 200 mm / 65 mm with R_λ = 0.10.
  - Pulsed runs at 28.8 W/m² (3.75 kW / 130 m²) against continuous delivery at 13.1 W/m² (+10 °C):
    - mean water temperature during the on-time rises +0.88 / +1.04 / +1.35 K for 0.5 / 1 / 4 h runs at 150 mm / 45 mm, and +1.15 / +1.39 / +1.78 K at 200 mm / 65 mm.
  - At +2 °C (23.8 W/m²): +0.26-0.48 K.
  - Screed-mean swing per cycle: 0.2-1.9 K.
  - Adding the loop-ΔT effect at leaving water, (P − L)/(2 × 2.0 kW/K) = +0.51 K at +10 °C and +0.16 K at +2 °C, gives the table above.
- **Karlsson (Chalmers), measured and simulated [2].** Surface heat flux reaches only about 6 % of its steady value 22 min after a step in fluid temperature. Points near the pipe swing with a larger amplitude than points between pipes. Within short runs, the heat goes into the screed near the pipe and does not reach the room directly. This supports the "storage first" premise.
- **Gree catalogue [5]** (GRS-CQ10Pd/NhH-E, A7):
  - COP 4.59 at W30/35 (9.5 kW, 2.07 kW input);
  - COP 3.60 at the fan-coil point (9.5 kW, 2.64 kW input; presumably 40/45);
  - that is about 2.4 %/K, consistent with the claim's 2-2.3 %/K conversion.
- **EN 1264 base curve, about 11 W/(m²K) surface-to-room [3].** This confirms that the surface and covering side (K_sr) dominates the series resistance, so K_ws must be several times K_H.

## Evidence against / weaknesses

- **The claim's low end (0.8 kW/K) and high end (3.5 K) are too pessimistic.** My model's effective pulse conductance does not go below about 1.1 kW/K, even at 200 mm / 65 mm / R_λ 0.15 with 4 h runs. The 3.5 K figure appears only as an end-of-run peak, or with a smaller active area or a laminar water side.
- **The conductance depends on run length.** It is not a constant. It is about 2 kW/K for 0.5-1 h runs and about 1.2-1.5 kW/K for 4 h runs, because the screed warms during the run. A single K_ws in a two-node simulator is an approximation. Fit it on run-length-matched data.
- **G3 misreads one of its corroborating sources.** It cites the Aalborg CLIMA 2022 paper's priors of "6-12 W/(m²K) water-to-floor" as the same order of magnitude [4]. In that paper u_w is defined per m² of *pipe surface*: R_w = N/(2π·r_p·u_w·g_p·A_r). It is also used for a light floor with only 24-36 kJ/(m²K) of capacity. It is not a per-floor-area screed conductance and does not corroborate the claim.
- **There is no direct field measurement.** No source I read measures the "P_min pulse vs continuous" lift on a real slab. Gwerder's lab test [1] measured room-temperature control under PWM, not the COP penalty.
- **The baseline is hypothetical.** Continuous delivery at L is impossible for this unit, because L < P_min above roughly −5 to +3 °C. The claim quantifies an unavoidable loss, not an achievable saving. The actionable comparison is P_min pulses against higher-power pulses (about 0.5-0.9 K per extra kW), or against catch-up runs.
- **This house's real excess comes mostly from elsewhere.** The physics needs leaving water of about 26-31 °C at +10/+2 °C, but the house runs setpoints of 31-36 °C (peaks 39 °C). The gap is several kelvin larger than the 0.4-2.3 K pulse penalty. It comes from the setpoint policy and the 4 K restart hysteresis, which forces the setpoint well above the outlet. It does not come from P_min pulse physics.
- **Model limits [7].** The room is held fixed (in reality a small rise in room temperature during the pulse slightly reduces emission). Downward losses are ignored. The pipe is a 16-cell region on a 2.5 mm mesh. Defrost interruptions are not modelled; on humid days at +2 °C they add restarts. Screed properties (λ 1.2, ρc 2.0 MJ/(m³K)) are assumed, not measured.

## Applicability to this house

- **For the two-node simulator,** use **K_ws ≈ 1.5 kW/K (prior range 1.0-2.2)** for the whole floor. Do not use 3.5 kW/K: that is the water-to-pipe-plane value and it understates the burst penalty by about 2×.
- **K_sr** follows from the identified water-to-room UA: 1/K_sr = 1/UA − 1/K_ws. With UA ≈ 0.45 kW/K, K_sr ≈ 0.65 kW/K, and the resistance ratio UA/K_ws ≈ 0.3 sits inside Gwerder's typical 20-50 % range [1].
- **Pulse power.** Minimising pulse power above P_min is worth roughly 1-3 % COP per kW avoided. It matters in catch-up runs (for example 5-6 kW at +2 °C costs about 1-2 K more lift than running at P_min). In mild weather the unit is already at P_min.
- **The bigger lever is the setpoint and restart policy.** With the 4 K restart hysteresis, the setpoint sits several kelvin above the 26-31 °C outlet the slab actually needs. That is where most of the "high-temperature water" cost lies.
- **Identifying K_ws from the owner's logs.** Use mid-run (mean water − interpolated screed or room) against heat output, binned by run length. Expect an apparent value of about 2 kW/K for short runs and 1.2-1.5 kW/K for long runs. If the logs show much lower values, suspect closed loops (a smaller active area) or a low per-loop flow.

## Sources

1. Gwerder M., Tödtli J., Lehmann B., Dorer V., Güntensperger W., Renggli F., "Control of thermally activated building systems (TABS) in intermittent operation with pulse width modulation", Applied Energy 86:1606-1616 (2009) - https://www.sysecol2.ethz.ch/OptiControl/LiteratureOC/Gwer_09_AE_86_1606.pdf - peer-reviewed paper + lab test (Siemens HVAC lab, Zug). R_t 0.060 / R̃ 0.16 m²K/W; resistance ratio 20-50 %; PWM supply-shift equation; 1-3 K recommended shift; τ 9.9 h / 100 h.
2. Karlsson H., "Thermal Modelling of Water-Based Floor Heating Systems", Chalmers PhD thesis (2010) - https://publications.lib.chalmers.se/records/fulltext/111900.pdf - simulation validated against measured (Caccavelli) test-cell data. 22 min → 6 % of steady surface flux; near-pipe points swing more; the model underestimated fluid-to-element exchange by 16 %.
3. Olesen B. W., "New European standards for design, dimensioning and testing embedded radiant heating and cooling systems", Clima 2007 - https://www.irbnet.de/daten/iconda/CIB8359.pdf - standards summary (EN 1264 / EN 15377). q = 8.92·Δθ^1.1, about 11 W/(m²K) floor-heating surface coefficient; equivalent-resistance method. The K_H 3.33 W/(m²K) at 150 mm / R 0.10 benchmark is as tabulated in G3's EN 1264 sources (Uponor/HeatAlgo); I did not re-read it.
4. Thorsteinsson S. et al., "Transient analysis of individual return temperatures in hydronic floor heating systems", CLIMA 2022 - https://proceedings.open.tudelft.nl/clima2022/article/download/140/111/119 - paper (simulation + test house). u_w 6-12 W/(m²K) defined per pipe-surface area (R_w = N/(2π r_p u_w g_p A_r)); floor capacity 24-36 kJ/(m²K). Read to check G3's use of it.
5. Gree, "Air to Water Heat Pump" catalogue (Versati III) (2021) - https://germany-gree.de/wp-content/uploads/2021/06/GREE_Air_to_water.pdf - manufacturer data. GRS-CQ10Pd/NhH-E: 9.5 kW / 2.07 kW (COP 4.59) at A7 W30/35 (floor heating); 9.5 kW / 2.64 kW (COP 3.60) at the fan-coil point.
6. Olesen B. W., "Operation and control of thermally activated building systems (TABS)", REHVA Journal (2011) - https://rehva.eu/rehva-journal/chapter/operation-and-control-of-thermally-activated-building-systems-tabs - simulation. Intermittent pump operation feasible; dead band ≤ 2 K; about 20 % saving from 21-23 °C vs 22-23 °C. No resistance values (context only).
7. This verification's 2-D transient finite-difference screed model (Swift; half-pitch cross-section, 2.5 mm mesh, explicit time stepping, 6-8 day spin-up, 3 periodic cycles averaged). Steady state calibrated against EN 1264 K_H (3.29 vs 3.33 W/(m²K)). Script at(analysis script, not committed) - own simulation (evidence rank: simulation).
8. van Leeuwen R. P. et al., "Thermal storage in a heat pump heated living room floor for urban district power balancing", SMARTGREENS 2014 - https://www.scitepress.org/Papers/2014/49163/49163.pdf - simulation. Floor modelled as one thermal node with heat input at the floor node; 1.6 kWh stored per 2 h shift. Context only, no water-to-floor value.
