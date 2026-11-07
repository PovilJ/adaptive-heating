"""Water-side model of the Gree Versati air-to-water heat pump, 1-minute step.

Built from the measured minute data of this house plus physics and manufacturer data where the
data has nothing; docs/research/lab/UNIT_MODEL.md gives the evidence behind every number and
lab/sim/unit_analysis.py recomputes it. It does not reuse any code or model of the Home
Assistant integration.

Conventions
-----------
- Temperatures in degC, heat and electricity in kW, flow in L/min, time step 1 minute.
- `t_return` (input) is the water entering the unit (on the scale of the unit's inlet sensor).
- `t_supply` (output) is the true water leaving the unit = t_return + q_loop / (cp * flow); the
  plant (floor/house) model should use this one.
- `t_outlet` is what the unit's outlet sensor reads (0.30 K below the true supply: outlet and
  inlet sensors disagree by 0.30 K whenever water circulates without heating).
- `t_ctrl` is the firmware's control sensor (the "optional water sensor" after the backup
  heater): 0.70 K below t_return while idle (0.80 K at the moment it triggers a start), 0.80 K below t_supply while running.
- `q_loop` is heat into the space-heating water (negative during defrost); `p_outdoor` is the
  metered outdoor-unit electricity; `p_total` adds the unmetered indoor unit (circulation pump
  and controls, ~0.10 kW, running all the time); `p_tank_heater` is the unmetered DHW element.

Firmware rules (measured): start when setpoint - t_ctrl >= restart_delta (one pre-start minute
at ~0.2 kW, then the compressor); stop when t_ctrl >= setpoint + 2 K for 3 minutes, or at once
when a setpoint write makes that true (but not before a 6-minute minimum run); capacity holds
inside a dead band (+0.1..+1.0 K of setpoint - t_ctrl) and ramps outside it; every 120 minutes
of continuous running the compressor may surge for ~4 minutes (more likely at low output), which
usually ends the run; hot water has priority, with 7-minute pauses either side.

Electricity (review round 1): a smooth Carnot fraction of outdoor temperature, a regularised
output-correction surface (COP peaks at mid output, held constant above the measured 95th
percentile of output) and a coil-frost term. Frost builds per kWh drawn from the outdoor air.
The 120-minute surge probability follows the mean power of the preceding 30 minutes.

Review round 2: the defrost-trigger state loses up to 40 % over each compressor-off block and no
defrost comes within 50 compressor minutes of the last (fitted on all inter-defrost segments);
the coil frost seen by the COP is a separate state; the 120-minute timer restarts after a defrost;
the control-sensor offset depends a little on output; part-load bounds partload_lo/partload_hi.

Effects with no data behind them are marked ASSUMED (quiet mode, restart_delta other than 4/5,
tank-heater rating, minimum off time, the pump stopping while space heating is switched off).

Run `python -m lab.sim.unit` for the physics self-check.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

CP_WATER = 4.186  # kJ/(kg K); 1 L ~ 1 kg at loop temperatures (0.4 % error ignored)

# Versati III maximum-capacity correction factors (manufacturer service manual) x nominal 9.5 kW.
# Rows: leaving water 30/35/45/55 degC; columns: outdoor -15..25 degC in 5 K steps.
_QMAX_TA = (-15.0, -10.0, -5.0, 0.0, 5.0, 10.0, 15.0, 20.0, 25.0)
_QMAX_TW = (30.0, 35.0, 45.0, 55.0)
_QMAX_F = (
    (0.81, 0.91, 1.00, 1.10, 1.18, 1.26, 1.35, 1.41, 1.45),
    (0.74, 0.84, 0.93, 1.03, 1.11, 1.19, 1.28, 1.36, 1.41),
    (0.60, 0.70, 0.80, 0.89, 0.97, 1.05, 1.13, 1.19, 1.25),
    (0.46, 0.56, 0.66, 0.74, 0.83, 0.90, 0.98, 1.05, 1.10),
)

# --- COP model (review round 1): smooth Carnot fraction + output-correction surface ---------
# P_outdoor = p0 + Q / COP_core, COP_core = eta(T) * (1 - d * frost) * exp(G(T, Q)) * Carnot * exp(-x (Ts - 30))
# eta(T) = e0 + e1 tanh((T - tm) / sc) + e2 T. Fitted by lab/sim/unit_analysis.py (fit_cop_smooth)
# on ~33 000 5-minute-smoothed steady minutes; key = f"F{flow}_x{penalty}". G is bilinear on
# SMOOTH_TK x SMOOTH_QK (outdoor degC x heat kW), flat outside. Above the 95th percentile of the
# measured output per outdoor band (COP_Q95_K, in K of loop delta-T) COP is held constant.
SMOOTH_TK = (-12.0, -4.0, 2.0, 6.0, 12.0)
SMOOTH_QK = (3.0, 5.0, 7.0, 9.0, 11.0)
COP_Q95_T = (-15.0, -2.5, 1.5, 4.5, 7.5, 14.5)       # outdoor band centres
COP_Q95_K = (4.92, 3.44, 3.70, 4.52, 5.08, 4.28)      # p95 of measured output, K of delta-T
SMOOTH_FITS = {
    # key: (eta (e0, e1, tm, sc, e2), p0 kW, frost d, x_pen, G rows (outdoor knots) x cols (output knots))
    "F29_x0.015": ((0.76175, 0.3263, 5.72624, 5.08764, 0.0039), 0.2546, 0.1323, 0.015,
        ((0.0282, 0.348, 0.4416, 0.4634, 0.5), (-0.1246, 0.1638, 0.2307, 0.2437, 0.287), (-0.2542, -0.0205, 0.0097, 0.0358, 0.0556), (-0.3622, -0.2188, -0.2098, -0.2092, -0.224), (-0.4536, -0.3857, -0.4261, -0.4754, -0.5))),
    "F25_x0.015": ((0.67826, 0.29414, 5.79411, 4.98992, 0.00339), 0.3417, 0.1427, 0.015,
        ((0.176, 0.4239, 0.453, 0.4816, 0.5), (0.026, 0.2483, 0.2309, 0.2839, 0.261), (-0.0931, 0.0645, 0.0216, 0.0699, 0.013), (-0.1828, -0.1293, -0.1928, -0.2082, -0.2482), (-0.2504, -0.3019, -0.4223, -0.4878, -0.5))),
    "F33_x0.015": ((0.8529, 0.36502, 5.64183, 5.04323, 0.00431), 0.2483, 0.1287, 0.015,
        ((-0.029, 0.2889, 0.4428, 0.4677, 0.5), (-0.1727, 0.107, 0.2495, 0.2287, 0.3035), (-0.3017, -0.0635, 0.0398, 0.009, 0.0907), (-0.4099, -0.2433, -0.1831, -0.2077, -0.1911), (-0.5, -0.3967, -0.3903, -0.4435, -0.4768))),
    "F29_x0.0": ((0.55882, 0.19588, 5.55358, 5.2228, 0.0028), 0.0229, 0.1164, 0.0,
        ((0.0121, 0.3437, 0.4296, 0.4609, 0.5), (-0.148, 0.1773, 0.2585, 0.2815, 0.3287), (-0.2842, 0.0103, 0.0766, 0.1164, 0.1464), (-0.4037, -0.1801, -0.1072, -0.0884, -0.0777), (-0.5, -0.3325, -0.2911, -0.3069, -0.2992))),
    "F29_x0.03": ((0.87683, 0.38775, 5.66535, 4.81614, 0.00337), 0.4275, 0.1466, 0.03,
        ((0.0106, 0.3398, 0.4389, 0.4547, 0.5), (-0.0664, 0.1883, 0.242, 0.2489, 0.2942), (-0.1175, 0.043, 0.0357, 0.0505, 0.0641), (-0.1381, -0.1021, -0.166, -0.1856, -0.2207), (-0.1415, -0.218, -0.3615, -0.448, -0.5))),
    # review round 2 (N3): the output dependence of the central surface x0.5, eta/p0/d refitted (RMSE 0.1251)
    "F29_x0.015_pl0.5": ((0.79472, 0.35028, 5.54936, 5.20623, 0.00254), 0.3064, 0.1443, 0.015,
        ((0.1881, 0.348, 0.3948, 0.4057, 0.424), (0.0196, 0.1638, 0.1972, 0.2037, 0.2254), (-0.1373, -0.0205, -0.0054, 0.0077, 0.0175), (-0.2905, -0.2188, -0.2143, -0.214, -0.2214), (-0.4196, -0.3857, -0.4059, -0.4305, -0.4428))),
    # review round 2 (N3): the output dependence of the central surface x1.5, eta/p0/d refitted (RMSE 0.1209)
    "F29_x0.015_pl1.5": ((0.73664, 0.3061, 5.94147, 4.9735, 0.0053), 0.2077, 0.1206, 0.015,
        ((-0.1317, 0.348, 0.4884, 0.5211, 0.576), (-0.2688, 0.1638, 0.2641, 0.2837, 0.3486), (-0.371, -0.0205, 0.0248, 0.0639, 0.0936), (-0.4339, -0.2188, -0.2053, -0.2044, -0.2266), (-0.4876, -0.3857, -0.4463, -0.5202, -0.5572))),
    # small overhead, no output surface: COP almost flat with output (fit clearly worse, RMSE 0.166 vs 0.119)
    "F29_x0.015_flat": ((0.59507, 0.16288, 4.43408, 4.97441, -0.00863), 0.15, 0.128, 0.015,
        tuple((0.0,) * 5 for _ in range(5))),
}

# --- legacy COP model (before review round 1; variant `legacy_cop`) ---------------------------
# Carnot fraction at 10 outdoor knots + a fixed running overhead: COP rises with output up to
# the maximum and steps between knots. Kept only to show how much a result depends on it.
ETA_KNOTS = (-10.0, -5.0, -2.0, 0.0, 2.0, 4.0, 6.0, 8.0, 12.0, 16.0)
COP_FITS = {
    "F29_x0.015": ((0.5631, 0.5372, 0.4956, 0.5004, 0.6002, 0.5783, 0.706, 0.7614, 0.8224, 0.8107), 0.367, 0.015),
}

# --- frost per kWh drawn from the outdoor air (review rounds 1 and 2) ------------------------
# K(T): kWh of air heat (heat - electricity, x (Q / 5 kW)^0.28) per defrost, log-linear between the
# knots, flat outside, no frost above +10 degC. Review round 2 (N1): every compressor-off block of
# L minutes keeps 1 - rmax (1 - exp(-L / 15 min)) of the defrost-trigger state, and no defrost comes
# before 50 compressor minutes since the last one. Two steps (unit_analysis.frost_stop_fit and
# frost_count_fit): rmax from the timing of all 186 recorded inter-defrost segments, simulated as
# first passage on the recorded running pattern (optimum 0.4; 'kept while off', the round-1
# structure, is 8.6 units of squared log error worse, ~9 x the 90 % threshold of 0.92); then K at
# that rmax so that the model's defrosts on the recorded running pattern match the 176 recorded
# ones by outdoor band and on/off class (Poisson deviance 5.2 on 16 cells). The humidity gain is
# 0: neither fit finds one once K is per minute. Variants refit K at rmax 0.2 / 0.6
# (frost_melt_lo / frost_melt_hi) and 0 (frost_no_melt).
FROST_KWH_T = (-15.0, -7.0, -3.0, -1.0, 1.0, 3.0, 5.0, 8.0)
FROST_FITS = {
    # rmax: (K at the knots, RH gain per %)
    0.4: ((7.11, 7.16, 6.97, 7.52, 9.87, 17.26, 25.2, 31.64), 0.0),
    0.2: ((6.98, 7.42, 7.59, 7.96, 10.92, 20.39, 32.93, 50.35), 0.0),
    0.6: ((6.96, 6.72, 6.47, 6.89, 9.81, 16.81, 25.81, 25.16), 0.0),
    0.0: ((7.41, 9.24, 9.93, 9.74, 14.79, 20.28, 56.74, 192.53), 0.0),
}
FROST_KWH = FROST_FITS[0.4][0]
# the round-1 table (frost kept while idle, linear interpolation), variant legacy_frost_r1
FROST_KWH_T_R1 = (-17.5, -7.5, -3.5, -1.0, 1.0, 3.0, 5.0, 7.0, 14.0)
FROST_KWH_R1 = (3.9, 6.4, 7.2, 9.6, 13.0, 24.4, 84.0, 120.2, 968.5)


def _interp(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            f = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + f * (ys[i] - ys[i - 1])
    return ys[-1]


@dataclass
class UnitParams:
    """All model parameters. Values are the central fit; `ranges` documents the uncertainty.

    Capacity parameters (`*_k`) are in kelvin of loop delta-T, because that is what the data
    measures; heat = k * cp * flow. Changing the flow therefore scales every heat number, and the
    COP fit (`eta`, `p0_kw`) must come from the same flow (use the variant factories)."""

    # --- hydraulics -------------------------------------------------------------------------
    flow_lpm: float = 29.0  # constant loop flow (no flow meter; four methods reconcile 25-33)

    # --- setpoint interface -----------------------------------------------------------------
    sp_min: float = 20.0  # leaving-water setpoint clamp (registers accept 20-55; data: 25-39 written)
    sp_max: float = 55.0
    sp_step: float = 1.0  # the register takes whole degrees
    delta_min: float = 2.0  # restart hysteresis register range (manufacturer); only 4 and 5 observed
    delta_max: float = 10.0

    # --- firmware on/off logic (measured) ---------------------------------------------------
    stop_over_k: float = 2.0  # stop when t_ctrl >= setpoint + this ...
    stop_hold_min: int = 3  # ... for this many minutes; a setpoint write that makes it true stops at once
    min_run_min: int = 6  # minimum compressor run (2 observed cases + manufacturer 6-min capacity hold)
    min_off_min: int = 3  # ASSUMED from the manual (never binding in the data: shortest heat->heat off 5 min)
    prestart_min: int = 1  # pre-start minute (fan/valves) before the compressor, ~0.2 kW
    p_prestart_kw: float = 0.22
    p_poststop_kw: float = 0.15  # the minute after a stop (ramp-down tail)
    dhw_pre_pause_min: int = 7  # heat run stopped for hot water: 7 min before the DHW compressor start
    dhw_post_pause_min: int = 7  # after DHW: 7 min with the valve still on the tank (no loop heat)
    ctrl_offset_idle: float = -0.80  # effective t_ctrl - t_return at idle starts (mean idle offset -0.69;
    # starts fire on the downward 0.1-K flicker: sp - inlet - delta = -0.8 at the median drift start)
    ctrl_offset_run: float = -0.80  # t_ctrl - t_supply while running, at 5 kW ...
    ctrl_offset_slope: float = -0.025  # ... per kW of heat (review round 2: t_ctrl - outlet -0.44 K below
    # 4 kW, -0.48 at 4-6, -0.52 at 6-8, -0.60 above 8 kW; 44 000 running minutes)
    outlet_sensor_offset: float = -0.30  # outlet sensor - true supply

    # --- capacity control (measured, in K of loop delta-T) ----------------------------------
    dead_up_k: float = 1.0  # ramp up while setpoint - t_ctrl >= this
    dead_dn_k: float = 0.1  # ramp down while setpoint - t_ctrl <= this (data drift -5 W/min at 0..0.6)
    ramp_up_k: float = 0.10  # K/min of loop delta-T (~ +45 W/min electrical)
    ramp_dn_k: float = 0.03  # K/min at the dead-band edge ...
    ramp_dn_gain: float = 0.60  # ... plus this per K of extra overshoot (capped at ramp_dn_max)
    ramp_dn_max: float = 0.35
    start_k: float = 3.6  # capacity at compressor start (K of delta-T, ~7.3 kW at 29 L/min)
    start_factors: tuple = (0.40, 0.85, 0.97)  # minute-mean share reaching the water in run minutes 1-3
    hold_after_start_min: int = 10  # no ramp-down for this long after a start (data: peak at 6-11 min)
    qmin_a_k: float = 1.8  # minimum capacity delta-T at 0 degC outdoor (fit 1.83 + 0.049/K, 76 runs) ...
    qmin_b_k: float = 0.05  # ... rising this much per K outdoor
    qmin_lo_k: float = 1.4  # clamp (below -5 degC there is little data at minimum output)
    qmin_hi_k: float = 2.4
    qmax_nominal_kw: float = 9.5  # manufacturer nominal at A7/W35, times the correction table
    qmax_scale: float = 1.0

    # --- COP / electricity ------------------------------------------------------------------
    cop_form: str = "smooth"  # 'smooth' (review round 1) or 'knots' (legacy, variant legacy_cop)
    eta_s: tuple = SMOOTH_FITS["F29_x0.015"][0]  # smooth Carnot fraction (e0, e1, tm, sc, e2)
    p0_kw: float = SMOOTH_FITS["F29_x0.015"][1]  # running overhead (fan, drive, controls)
    frost_cop_d: float = SMOOTH_FITS["F29_x0.015"][2]  # COP loss at full frost (just before a defrost)
    x_pen: float = SMOOTH_FITS["F29_x0.015"][3]  # extra COP penalty per K of supply beyond Carnot
    cop_g: tuple = SMOOTH_FITS["F29_x0.015"][4]  # output-correction surface (ln), SMOOTH_TK x SMOOTH_QK
    q95_clamp: bool = True  # hold COP constant above the measured 95th percentile of output
    eta: tuple = COP_FITS["F29_x0.015"][0]  # legacy knots (cop_form 'knots' only)
    cond_approach_k: float = 1.0  # condensing = supply + this + cond_slope * Q (level ASSUMED,
    cond_slope_k_per_kw: float = 0.10  # slope from the condensing-pressure sensor)
    evap_offset_k: float = -1.35  # evaporating = min(outdoor + offset - slope * Q, cap) (coil sensor)
    evap_slope_k_per_kw: float = 0.42
    evap_cap_c: float = 2.5  # the coil never runs warmer than ~+2.5 degC (measured plateau)
    min_lift_k: float = 5.0
    p_idle_t: tuple = (-5.0, 0.0, 1.0, 2.0, 4.0, 8.0)  # outdoor-unit standby vs outdoor temperature
    p_idle_kw: tuple = (0.047, 0.040, 0.030, 0.022, 0.013, 0.011)  # (crankcase/base heater when cold)
    p_indoor_kw: float = 0.10  # indoor unit (pump + controls), 2025 indoor meter, not metered now
    start_loss_kwh: float = 0.0  # EXTRA electricity per start beyond the modelled ramp (variant)

    # --- defrost (measured frequency/duration/heat; melting while idle is ASSUMED) ----------
    frost_mode: str = "air_kwh"  # 'air_kwh' (per kWh drawn from the air) or 'run_min' (legacy)
    frost_kwh_t: tuple = FROST_KWH_T
    frost_kwh: tuple = FROST_KWH  # kWh of air heat between defrosts (at the knots)
    frost_log_interp: bool = True  # log-linear K between knots (review round 2); False: linear (round 1)
    frost_q_exp: float = 0.28  # frost per kWh rises as (Q / 5 kW)^this (colder coil at high output)
    frost_hours_t: tuple = (-15.0, -7.5, -3.5, -1.0, 1.0, 3.0, 5.0, 7.0, 9.0)  # legacy (run_min)
    frost_hours: tuple = (0.8, 1.6, 2.1, 2.5, 3.1, 5.6, 15.6, 21.0, 80.0)  # run hours between defrosts
    frost_off_above_c: float = 10.0  # no frost accumulation above this outdoor temperature
    frost_rh_ref: float = 87.0  # humidity at which the tables were measured
    frost_rh_gain: float = FROST_FITS[0.4][1]  # frost per % RH above reference (joint fit)
    frost_scale: float = 1.0  # multiplier (variants more_frost / less_frost)
    # review round 2 (N1): share of the defrost-trigger state lost over a compressor-off block,
    # 1 - exp(-L / tau) of it after L minutes (measured: the trigger state, not the coil frost that
    # costs COP; that one follows the air drawn since the last defrost, see UNIT_MODEL.md 8)
    frost_stop_rmax: float = 0.4
    frost_stop_tau_min: float = 15.0
    defrost_min_run_min: int = 10
    defrost_min_interval_min: int = 50  # review round 2: no defrost before 50 compressor minutes since the
    # last one (169 recorded intervals: minimum 32, 5th percentile 52)
    defrost_min_cold: int = 5  # defrost duration below +3 degC outdoor
    defrost_min_mild: int = 2
    defrost_draw_k: float = 5.2  # heat drawn from the loop during defrost, K of delta-T
    defrost_p_kw: float = 1.55  # electricity during defrost
    after_defrost_factors: tuple = (0.6, 1.0)  # minute-mean share of capacity reaching the water
    post_defrost_k: float = 4.3  # recovery capacity after a defrost (K of delta-T; ~2.2 kW measured)
    post_defrost_hold_min: int = 3  # no ramp-down while recovering
    post_defrost_stop_hold_min: int = 2  # stop needs t_ctrl >= setpoint + 2 K for only 2 min here
    # (measured: 20 of 28 defrosts that began with t_ctrl >= setpoint + 0.5 ended the run ~2 min later)

    # --- 120-minute surge, probably oil return (measured: 62 of 194 marks). P(surge) rises in mild
    # weather, i.e. at low compressor speed (0.11 below 0 degC -> 0.57 above 9 degC); it fires
    # deterministically via an accumulator so runs are reproducible
    oil_every_min: int = 120
    oil_mode: str = "power"  # 'power' (review round 1) or 'outdoor' (legacy table)
    oil_logit: tuple = (2.01, -2.223)  # P(surge) = 1 / (1 + exp(-(a + b * mean kW of the last 30 min)))
    oil_prob_t: tuple = (-5.0, 1.5, 4.5, 7.5, 11.0)  # legacy: outdoor temperature, degC
    oil_prob: tuple = (0.11, 0.32, 0.33, 0.40, 0.57)
    oil_len_min: int = 4
    oil_k: float = 5.0  # capacity during the surge, K of loop delta-T (~2.5 kW electrical)
    oil_from_defrost: bool = True  # review round 2 (N6): the 120-min timer restarts at the end of a defrost
    # (surges in runs with a defrost sit near 120-min multiples of the defrost end, 49 %, not of the start, 24 %)

    # --- hot water (exogenous demand, measured statistics) ----------------------------------
    dhw_p0_kw: float = 1.5  # DHW electricity ramps from this ...
    dhw_slope_kw_per_min: float = 0.26  # ... at this rate (outlet climbs ~30 -> 50 degC)
    dhw_p_max_kw: float = 4.9  # measured plateau (median of runs)
    dhw_cold_gain: float = 0.012  # +1.2 % DHW electricity per K below +7 degC
    tank_heater_kw: float = 2.0  # ASSUMED rating; runs ~23 min after each DHW run; NOT metered
    tank_heater_min: int = 23

    # --- quiet mode (NO DATA: never used in this house) -------------------------------------
    quiet_qmax_factor: float = 0.70  # ASSUMED (manual: "capacity decreases correspondingly")
    quiet_frost_factor: float = 1.0  # extra frost factor in quiet mode; 1.0 since review round 1
    # (frost now follows the air heat, so the lower output already changes it; 1.5 = old ASSUMED)

    # --- space heating switched off (heating_enabled False): ASSUMED, never logged ------------
    pump_off_when_disabled: bool = True  # False: old behaviour, loop keeps circulating (variant)
    p_indoor_off_kw: float = 0.02  # pump stops, controls stay (ASSUMED)
    purge_min: int = 3  # after re-enabling: pump purges the loop before a start can happen (ASSUMED)
    prestart_abort_min: int = 2  # a begun pre-start is aborted only if the gap stays closed this long

    ranges: dict = field(default_factory=lambda: {
        "flow_lpm": (25.0, 33.0),
        "x_pen (1/K)": (0.0, 0.03),
        "stop_hold_min": (3, 4),
        "min_run_min": (6, 7),
        "min_off_min": (3, 5),
        "ramp_up_k": (0.07, 0.13),
        "start_k": (3.2, 4.0),
        "qmin_a_k": (1.55, 1.95),
        "p0_kw": (0.15, 0.43),
        "start_loss_kwh": (0.0, 0.15),
        "defrost_draw_k": (4.0, 6.5),
        "frost x": (0.7, 1.4),
        "frost_stop_rmax": (0.2, 0.6),
    })

    @property
    def k_flow(self) -> float:
        """kW per K of loop delta-T at the assumed flow."""
        return CP_WATER * self.flow_lpm / 60.0


# ------------------------------------------------------------------------------------------
# steady-state physics (also usable by controllers / analysis)
# ------------------------------------------------------------------------------------------

def q_max(p: UnitParams, t_amb: float, t_supply: float) -> float:
    """Maximum heat output kW (manufacturer correction table, bilinear, clamped)."""
    tw = min(max(t_supply, _QMAX_TW[0]), _QMAX_TW[-1])
    rows = [_interp(t_amb, _QMAX_TA, r) for r in _QMAX_F]
    return p.qmax_nominal_kw * p.qmax_scale * _interp(tw, _QMAX_TW, rows)


def q_min(p: UnitParams, t_amb: float) -> float:
    """Minimum heat output kW while the compressor runs (measured, see report)."""
    dt = min(max(p.qmin_a_k + p.qmin_b_k * t_amb, p.qmin_lo_k), p.qmin_hi_k)
    return dt * p.k_flow


def t_evap(p: UnitParams, t_amb: float, q: float) -> float:
    return min(t_amb + p.evap_offset_k - p.evap_slope_k_per_kw * q, p.evap_cap_c)


def _bilinear(t, q, G):
    tk, qk = SMOOTH_TK, SMOOTH_QK
    if t <= tk[0]:
        i, ft = 0, 0.0
    elif t >= tk[-1]:
        i, ft = len(tk) - 2, 1.0
    else:
        i = 0
        while t > tk[i + 1]:
            i += 1
        ft = (t - tk[i]) / (tk[i + 1] - tk[i])
    if q <= qk[0]:
        j, fq = 0, 0.0
    elif q >= qk[-1]:
        j, fq = len(qk) - 2, 1.0
    else:
        j = 0
        while q > qk[j + 1]:
            j += 1
        fq = (q - qk[j]) / (qk[j + 1] - qk[j])
    return (G[i][j] * (1 - ft) * (1 - fq) + G[i + 1][j] * ft * (1 - fq) + G[i][j + 1] * (1 - ft) * fq
            + G[i + 1][j + 1] * ft * fq)


def eta_smooth(p: UnitParams, t_amb: float) -> float:
    e0, e1, tm, sc, e2 = p.eta_s
    return e0 + e1 * math.tanh((t_amb - tm) / sc) + e2 * t_amb


def cop_core(p: UnitParams, t_supply: float, t_amb: float, q: float, frost: float = 0.0) -> float:
    """Heat / (electricity above the running overhead): Carnot fraction x Carnot."""
    tc = t_supply + p.cond_approach_k + p.cond_slope_k_per_kw * q
    lift = max(tc - t_evap(p, t_amb, q), p.min_lift_k)
    carnot = (tc + 273.15) / lift * math.exp(-p.x_pen * (t_supply - 30.0))
    if p.cop_form == "knots":
        return _interp(t_amb, ETA_KNOTS, p.eta) * carnot
    eta = eta_smooth(p, t_amb) * (1.0 - p.frost_cop_d * min(max(frost, 0.0), 1.0))
    return eta * math.exp(_bilinear(t_amb, q, p.cop_g)) * carnot


def q_p95(p: UnitParams, t_amb: float) -> float:
    """95th percentile of the measured steady output at this outdoor temperature, kW."""
    return _interp(t_amb, COP_Q95_T, COP_Q95_K) * p.k_flow


def p_running(p: UnitParams, t_supply: float, t_amb: float, q: float, frost: float = 0.0) -> float:
    """Outdoor-unit electricity kW at steady heat output q (compressor running, no defrost).
    Above the measured 95th percentile of output the COP is held at its value there."""
    if p.cop_form != "knots" and p.q95_clamp:
        q95 = q_p95(p, t_amb)
        if q > q95:
            return (p.p0_kw + q95 / cop_core(p, t_supply, t_amb, q95, frost)) * q / q95
    return p.p0_kw + q / cop_core(p, t_supply, t_amb, q, frost)


def cop_steady(p: UnitParams, t_supply: float, t_amb: float, q: float, frost: float = 0.0) -> float:
    """Steady COP of the outdoor unit (heat to water / metered electricity), no defrost."""
    return q / p_running(p, t_supply, t_amb, q, frost)


def p_idle(p: UnitParams, t_amb: float) -> float:
    return _interp(t_amb, p.p_idle_t, p.p_idle_kw)


_LOG_CACHE = {}


def _logs(vals):
    v = _LOG_CACHE.get(vals)
    if v is None:
        v = _LOG_CACHE[vals] = tuple(math.log(max(x, 1e-9)) for x in vals)
    return v


def frost_cop_per_min(p: UnitParams, t_amb: float, rh: float, q: float, pe: float) -> float:
    """Coil frost seen by the COP (review round 2): the round-1 accumulation (round-1 table, linear
    interpolation, +2.15 %/% RH, kept while off), which is the proxy the COP's frost term d was
    fitted on (UNIT_MODEL.md 7.1); refitting d on the new trigger state fits worse (RMSE 0.122 vs
    0.119 kW, d 0.06)."""
    if t_amb >= p.frost_off_above_c or p.frost_mode == "run_min":
        return 0.0
    rhf = max(0.3, 1.0 + 0.0215 * (rh - p.frost_rh_ref))
    air = max(q - pe, 0.0)
    kwh = _interp(t_amb, FROST_KWH_T_R1, FROST_KWH_R1) * p.flow_lpm / 29.0
    return air / 60.0 / kwh * rhf * (max(q, 1.0) / 5.0) ** p.frost_q_exp


def frost_per_min(p: UnitParams, t_amb: float, rh: float, quiet: bool, q: float, pe: float) -> float:
    """Frost added in one running minute, as a share of what triggers a defrost. `q` is the heat
    to water (kW) and `pe` the electricity (kW); the air supplies q - pe."""
    if t_amb >= p.frost_off_above_c:
        return 0.0
    rhf = max(0.3, 1.0 + p.frost_rh_gain * (rh - p.frost_rh_ref))
    if p.frost_mode == "run_min":
        hours = _interp(t_amb, p.frost_hours_t, p.frost_hours)
        rate = rhf / (hours * 60.0)
    else:
        air = max(q - pe, 0.0)
        if p.frost_log_interp:
            kwh = math.exp(_interp(t_amb, p.frost_kwh_t, _logs(p.frost_kwh)))
        else:
            kwh = _interp(t_amb, p.frost_kwh_t, p.frost_kwh)
        rate = air / 60.0 / kwh * rhf * (max(q, 1.0) / 5.0) ** p.frost_q_exp
    if quiet:
        rate *= p.quiet_frost_factor
    return rate * p.frost_scale


def frost_rate_per_min(p: UnitParams, t_amb: float, rh: float, quiet: bool, q: float = 6.0,
                       t_supply: float = 31.0) -> float:
    """Frost per running minute at a steady output q (for analysis and reports)."""
    return frost_per_min(p, t_amb, rh, quiet, q, p_running(p, t_supply, t_amb, q))


# ------------------------------------------------------------------------------------------
# dynamic unit
# ------------------------------------------------------------------------------------------

@dataclass
class StepResult:
    t_supply: float  # true water leaving the unit (degC)
    t_outlet: float  # outlet sensor reading
    t_ctrl: float  # firmware control sensor
    q_loop: float  # heat into the space-heating water, kW (negative in defrost)
    loop_flow_lpm: float  # flow through the unit on the space-heating side (0 while the valve is on the tank)
    p_outdoor: float  # metered outdoor-unit electricity, kW
    p_total: float  # + unmetered indoor unit (pump, controls)
    p_tank_heater: float  # unmetered DHW tank heater (ASSUMED rating)
    status: str  # 'heat' | 'dhw' | 'defrost' | 'idle' | 'off'
    compressor: bool
    started: bool  # a space-heating compressor start happened in this step
    pump: bool = True  # loop circulation pump running (off only while space heating is disabled)


class VersatiUnit:
    """Stateful 1-minute model. Create with parameters, call step() once per minute."""

    def __init__(self, params: UnitParams | None = None):
        self.p = params or UnitParams()
        self.mode = "idle"  # idle | prestart | heat | pre_dhw | dhw | post_dhw
        self.comp = False
        self.run_min = 0
        self.off_min = 10_000
        self.over_min = 0
        self.q = 0.0
        self.frost = 0.0  # defrost-trigger state (1 = defrost due)
        self.frost_cop = 0.0  # coil frost seen by the COP (round-1 accumulation since the last defrost, capped at 1)
        self.off_len = 0  # minutes since the compressor stopped (review round 2, N1)
        self.run_since_defrost = 10_000  # compressor minutes since the last defrost
        self.frost_at_stop = 0.0
        self.defrost_left = 0
        self.after_defrost = 99
        self.pause_left = 0
        self.dhw_min = 0
        self.heater_left = 0
        self.last_sp = None
        self.pending_start_loss = 0.0
        self.oil_left = 0
        self.q_before_oil = 0.0
        self.oil_acc = 0.5
        self.oil_post = 99
        self.p_hist = []  # electricity of the last 30 running minutes (surge probability)
        self.pre_closed = 0
        self.enabled_prev = True
        self.purge_left = 0
        self.stop_reason = ""
        self.last_p = 0.0
        self.just_stopped = False
        # counters
        self.n_starts = 0
        self.n_dhw = 0
        self.n_defrost = 0
        self.n_oil = 0
        self.n_minoff_wait = 0  # minutes a start waited only for the (ASSUMED) minimum off time
        self.n_prestart_abort = 0

    # ---- helpers ------------------------------------------------------------------------
    def _clamp_sp(self, sp):
        p = self.p
        sp = min(max(sp, p.sp_min), p.sp_max)
        return round(sp / p.sp_step) * p.sp_step

    def _stop(self):
        self.comp = False
        self.mode = "idle"
        self.run_min = 0
        self.off_min = 0
        self.over_min = 0
        self.defrost_left = 0
        self.oil_left = 0
        self.just_stopped = True

    def _res(self, t_sup, t_ret, q, flow, pe, p_indoor, p_heater, status, comp, started, running, pump=True):
        p = self.p
        ctrl = (t_sup + p.ctrl_offset_run + p.ctrl_offset_slope * (q - 5.0)) if running else t_ret + p.ctrl_offset_idle
        self.last_p = pe
        return StepResult(t_sup, t_sup + p.outlet_sensor_offset, ctrl, q, flow, pe, pe + p_indoor,
                          p_heater, status, comp, started, pump)

    # ---- main step ----------------------------------------------------------------------
    def step(self, setpoint, restart_delta, t_return, t_amb, rh=85.0, flow_lpm=None,
             quiet=False, heating_enabled=True, dhw_demand=False) -> StepResult:
        p = self.p
        sp = self._clamp_sp(setpoint)
        # ASSUMED: the register range is 2-10 K; only 4 and 5 were ever observed
        delta = round(min(max(restart_delta, p.delta_min), p.delta_max))
        wrote = self.last_sp is not None and sp != self.last_sp
        self.last_sp = sp
        flow = p.flow_lpm if flow_lpm is None else flow_lpm
        kf = CP_WATER * max(flow, 1e-6) / 60.0
        if self.heater_left > 0:
            self.heater_left -= 1
            p_heater = p.tank_heater_kw
        else:
            p_heater = 0.0
        pid = p_idle(p, t_amb)
        if self.just_stopped:
            pid = max(pid, p.p_poststop_kw)
            self.just_stopped = False
        p_in = p.p_indoor_kw
        # space heating switched on again: the pump purges the loop before a start (ASSUMED)
        if heating_enabled and not self.enabled_prev:
            self.purge_left = p.purge_min
        self.enabled_prev = heating_enabled

        # ---------------- hot water has priority ----------------
        if dhw_demand and self.mode in ("idle", "prestart", "heat"):
            if self.comp:
                self._stop()
            self.mode = "pre_dhw"
            self.pause_left = max(0, p.dhw_pre_pause_min - self.off_min)
        if self.mode == "pre_dhw":
            if not dhw_demand:
                self.mode = "idle"
            elif self.pause_left > 0:
                self.pause_left -= 1
                self.off_min += 1
                self._off_minute()
                return self._res(t_return, t_return, 0.0, flow, pid, p_in, p_heater, "off", False, False, False)
            else:
                self.mode = "dhw"
                self.comp = True
                self.dhw_min = 0
                self.n_dhw += 1
        if self.mode == "dhw":
            if dhw_demand:
                self.dhw_min += 1
                pd = min(p.dhw_p0_kw + p.dhw_slope_kw_per_min * (self.dhw_min - 1), p.dhw_p_max_kw)
                pd *= 1.0 + p.dhw_cold_gain * max(0.0, 7.0 - t_amb)
                # air heat of a tank run: electricity x (COP at a 45 degC supply - 1)
                c45 = cop_steady(p, 45.0, t_amb, 6.0, self.frost_cop)
                self._add_frost(frost_per_min(p, t_amb, rh, quiet, pd * c45, pd),
                                frost_cop_per_min(p, t_amb, rh, pd * c45, pd))
                return self._res(t_return, t_return, 0.0, 0.0, pd, p_in, p_heater, "dhw", True, False, False)
            # demand satisfied: stop; the valve stays on the tank for the post pause
            self.comp = False
            self.mode = "post_dhw"
            self.pause_left = p.dhw_post_pause_min
            self.off_min = 0
            self.run_min = 0
            self.heater_left = p.tank_heater_min
            pid = max(pid, p.p_poststop_kw)
        if self.mode == "post_dhw":
            if self.pause_left > 0:
                self.pause_left -= 1
                self.off_min += 1
                self._off_minute()
                return self._res(t_return, t_return, 0.0, 0.0, pid, p_in, p_heater, "off", False, False, False)
            self.mode = "idle"

        # ---------------- space heating: compressor running ----------------
        if self.comp:
            self.run_min += 1
            self.off_len = 0
            if self.defrost_left > 0:  # defrost in progress
                self.defrost_left -= 1
                if self.defrost_left == 0:
                    self._end_defrost()
                q_loop = -p.defrost_draw_k * p.k_flow
                t_sup = t_return + q_loop / kf
                return self._res(t_sup, t_return, q_loop, flow, p.defrost_p_kw, p_in, p_heater, "defrost", True, False, True)
            # control sensor with the capacity of the previous minute
            q_prev = self._q_eff()
            t_sup_prev = t_return + q_prev / kf
            t_ctrl = t_sup_prev + p.ctrl_offset_run + p.ctrl_offset_slope * (q_prev - 5.0)
            if t_ctrl - sp >= p.stop_over_k:
                self.over_min = max(self.over_min + 1, p.stop_hold_min if wrote else 0)
            else:
                self.over_min = 0
            hold = p.post_defrost_stop_hold_min if self.after_defrost <= 4 else p.stop_hold_min
            stop = (self.over_min >= hold) or (not heating_enabled)
            if stop and self.run_min > p.min_run_min:
                self.stop_reason = ("disabled" if not heating_enabled else "write" if wrote
                                    else "post_defrost" if self.after_defrost <= 4 else "surge" if self.oil_left > 0
                                    or self.oil_post <= 6 else "overshoot")
                self._stop()
                self.off_min = 0
                return self._res(t_return, t_return, 0.0, flow, max(pid, p.p_poststop_kw), p_in, p_heater,
                                 "idle", False, False, False)
            if (self.frost >= 1.0 and self.run_min >= p.defrost_min_run_min
                    and self.run_since_defrost >= p.defrost_min_interval_min):  # start a defrost
                self.defrost_left = (p.defrost_min_cold if t_amb < 3.0 else p.defrost_min_mild) - 1
                self.n_defrost += 1
                if self.defrost_left == 0:
                    self._end_defrost()
                q_loop = -p.defrost_draw_k * p.k_flow
                t_sup = t_return + q_loop / kf
                return self._res(t_sup, t_return, q_loop, flow, p.defrost_p_kw, p_in, p_heater, "defrost", True, False, True)
            # 120-minute surge
            self.oil_post += 1
            if self.oil_left > 0:
                self.oil_left -= 1
                if self.oil_left == 0:
                    self.q = self.q_before_oil
                    self.oil_post = 0
            elif p.oil_every_min and self.run_min > 1 and (self._oil_clock() - 1) % p.oil_every_min == 0:
                if p.oil_mode == "power" and self.p_hist:
                    h = self.p_hist[:26] if len(self.p_hist) >= 30 else self.p_hist
                    z = p.oil_logit[0] + p.oil_logit[1] * (sum(h) / len(h))
                    self.oil_acc += 1.0 / (1.0 + math.exp(-z))
                else:
                    self.oil_acc += _interp(t_amb, p.oil_prob_t, p.oil_prob)
                if self.oil_acc >= 1.0:
                    self.oil_acc -= 1.0
                    self.oil_left = p.oil_len_min
                    self.q_before_oil = self.q
                    self.n_oil += 1
            # capacity control on the error setpoint - t_ctrl
            e = sp - t_ctrl
            qmax = q_max(p, t_amb, t_sup_prev) * (p.quiet_qmax_factor if quiet else 1.0)
            qmin = min(q_min(p, t_amb), qmax)
            if self.run_min > 1:
                if e >= p.dead_up_k:
                    self.q += p.ramp_up_k * p.k_flow
                elif (e <= p.dead_dn_k and self.run_min > p.hold_after_start_min
                      and self.after_defrost >= p.post_defrost_hold_min):
                    self.q -= min(p.ramp_dn_k + p.ramp_dn_gain * (p.dead_dn_k - e), p.ramp_dn_max) * p.k_flow
            self.q = min(max(self.q, qmin), qmax)
            if self.oil_left > 0:
                self.q = min(max(self.q, p.oil_k * p.k_flow), qmax)
            self.after_defrost += 1
            q_eff = self._q_eff()
            t_sup = t_return + q_eff / kf
            pe = p_running(p, t_sup, t_amb, self.q, self.frost_cop)
            self._add_frost(frost_per_min(p, t_amb, rh, quiet, q_eff, pe), frost_cop_per_min(p, t_amb, rh, q_eff, pe))
            self.p_hist.append(pe)
            if len(self.p_hist) > 30:
                del self.p_hist[0]
            pe += self._start_loss_share()
            return self._res(t_sup, t_return, q_eff, flow, pe, p_in, p_heater, "heat", True, False, True)

        # ---------------- space heating: idle / pre-start ----------------
        self.off_min += 1
        self._off_minute()
        t_ctrl = t_return + p.ctrl_offset_idle
        if not heating_enabled and not p.pump_off_when_disabled:
            if self.mode == "prestart":
                self.mode = "idle"
            return self._res(t_return, t_return, 0.0, flow, pid, p_in, p_heater, "off", False, False, False)
        if not heating_enabled:
            # pump stopped, loop water stagnant (ASSUMED behaviour; see SIMULATOR.md, review fixes)
            if self.mode == "prestart":
                self.mode = "idle"
            return self._res(t_return, t_return, 0.0, 0.0, pid, p.p_indoor_off_kw, p_heater, "off", False, False,
                             False, pump=False)
        if self.purge_left > 0:
            self.purge_left -= 1
            return self._res(t_return, t_return, 0.0, flow, pid, p_in, p_heater, "idle", False, False, False)
        want = sp - t_ctrl >= delta
        if self.mode == "prestart":
            # a begun pre-start finishes unless the gap stays closed for prestart_abort_min minutes
            self.pre_closed = 0 if want else self.pre_closed + 1
            if self.pre_closed >= p.prestart_abort_min:
                self.mode = "idle"
                self.n_prestart_abort += 1
            elif self.pause_left > 0:
                self.pause_left -= 1
                return self._res(t_return, t_return, 0.0, flow, max(pid, p.p_prestart_kw), p_in, p_heater,
                                 "idle", False, False, False)
            else:
                return self._start(t_return, t_amb, rh, quiet, kf, flow, p_in, p_heater)
        if want and self.off_min <= p.min_off_min:
            self.n_minoff_wait += 1
        if want and self.off_min > p.min_off_min:
            self.pre_closed = 0
            if p.prestart_min > 0:
                self.mode = "prestart"
                self.pause_left = p.prestart_min - 1
                return self._res(t_return, t_return, 0.0, flow, max(pid, p.p_prestart_kw), p_in, p_heater,
                                 "idle", False, False, False)
            return self._start(t_return, t_amb, rh, quiet, kf, flow, p_in, p_heater)
        return self._res(t_return, t_return, 0.0, flow, pid, p_in, p_heater,
                         "idle" if heating_enabled else "off", False, False, False)

    def _oil_clock(self):
        """Minutes counted by the 120-minute surge timer: since the start, or since the end of the
        last defrost when oil_from_defrost."""
        if self.p.oil_from_defrost and self.after_defrost < self.run_min:
            return self.after_defrost + 1
        return self.run_min

    def _add_frost(self, rate, rate_cop):
        self.run_since_defrost += 1
        self.frost += rate
        self.frost_cop = min(1.0, self.frost_cop + rate_cop)
        self.off_len = 0

    def _off_minute(self):
        """Compressor off for one more minute: the defrost-trigger state decays towards
        (1 - rmax) of its value at the stop (review round 2, N1)."""
        p = self.p
        if self.off_len == 0:
            self.frost_at_stop = self.frost
        self.off_len += 1
        if p.frost_stop_rmax > 0 and self.frost_at_stop > 0:
            self.frost = self.frost_at_stop * (1.0 - p.frost_stop_rmax
                                               * (1.0 - math.exp(-self.off_len / p.frost_stop_tau_min)))

    def _end_defrost(self):
        self.frost = 0.0
        self.frost_cop = 0.0
        self.run_since_defrost = 0
        self.after_defrost = 0
        self.over_min = 0
        self.q = max(self.q, self.p.post_defrost_k * self.p.k_flow)

    def _start(self, t_return, t_amb, rh, quiet, kf, flow, p_in, p_heater):
        p = self.p
        self.comp = True
        self.mode = "heat"
        self.run_min = 1
        self.over_min = 0
        self.after_defrost = 99
        self.n_starts += 1
        qmax = q_max(p, t_amb, t_return) * (p.quiet_qmax_factor if quiet else 1.0)
        self.q = min(max(p.start_k * p.k_flow, min(q_min(p, t_amb), qmax)), qmax)
        self.pending_start_loss = p.start_loss_kwh
        self.p_hist = []
        q_eff = self._q_eff()
        t_sup = t_return + q_eff / kf
        pe = p_running(p, t_sup, t_amb, self.q, self.frost_cop)
        self._add_frost(frost_per_min(p, t_amb, rh, quiet, q_eff, pe), frost_cop_per_min(p, t_amb, rh, q_eff, pe))
        self.p_hist.append(pe)
        pe += self._start_loss_share()
        return self._res(t_sup, t_return, q_eff, flow, pe, p_in, p_heater, "heat", True, True, True)

    def _start_loss_share(self):
        """Extra start electricity (variant), spread over the first 10 minutes."""
        if self.pending_start_loss <= 0:
            return 0.0
        add = min(self.pending_start_loss * 60.0, self.p.start_loss_kwh * 6.0)
        self.pending_start_loss -= add / 60.0
        return add

    def _q_eff(self):
        """Capacity that reaches the water (start-up and post-defrost ramps)."""
        if not self.comp:
            return 0.0
        f = 1.0
        sf = self.p.start_factors
        if 1 <= self.run_min <= len(sf):
            f = sf[self.run_min - 1]
        af = self.p.after_defrost_factors
        if 0 <= self.after_defrost < len(af):
            f = min(f, af[self.after_defrost])
        return self.q * f


# ------------------------------------------------------------------------------------------
# variants for robustness testing
# ------------------------------------------------------------------------------------------

def _fit(key: str, **kw) -> UnitParams:
    eta, p0, d, x, g = SMOOTH_FITS[key]
    flow = float(key.split("_")[0][1:])
    # the air heat per defrost was measured at 29 L/min; another assumed flow scales every heat
    # number, so the table scales with it (keeps the measured defrost count)
    fk = tuple(v * flow / 29.0 for v in kw.pop("frost_kwh", FROST_KWH))
    return UnitParams(flow_lpm=flow, eta_s=eta, p0_kw=p0, frost_cop_d=d, x_pen=x, cop_g=g, frost_kwh=fk, **kw)


def central() -> UnitParams:
    return UnitParams()


def low_flow() -> UnitParams:
    """Loop flow 25 L/min: every heat number and the COP level ~14 % lower (pessimistic level)."""
    return _fit("F25_x0.015")


def high_flow() -> UnitParams:
    """Loop flow 33 L/min: heat and COP ~14 % higher (optimistic level)."""
    return _fit("F33_x0.015")


def shallow_outlet() -> UnitParams:
    """Pure Carnot structure (no extra outlet penalty): ~-2 %/K, close to the datasheet slope.
    Use to check that a controller does not depend on a steep outlet penalty."""
    return _fit("F29_x0.0")


def steep_outlet() -> UnitParams:
    """The free fit of this house's data: ~-4 %/K per K of supply temperature."""
    return _fit("F29_x0.03")


def flat_load() -> UnitParams:
    """Small running overhead (0.15 kW) and no output surface: COP almost flat with output, a
    little higher at minimum output than the data say. Use to check that a ranking does not
    depend on the shape of COP against output (mandatory ranking variant)."""
    return _fit("F29_x0.015_flat")


def partload_lo() -> UnitParams:
    """Half the fitted part-load slope: the output dependence of the central COP surface x0.5,
    eta, p0 and d refitted (RMSE 0.125 vs 0.119; minimum-output bins within -8..+6 %). COP at
    minimum output closer to mid output. Mandatory ranking variant (review round 2, N3)."""
    return _fit("F29_x0.015_pl0.5")


def partload_hi() -> UnitParams:
    """1.5 x the fitted part-load slope, refitted likewise (RMSE 0.121; minimum-output bins
    -3..+18 %). Minimum output relatively worse. Mandatory ranking variant (review round 2, N3)."""
    return _fit("F29_x0.015_pl1.5")


def legacy_cop() -> UnitParams:
    """The COP model before review round 1: 10-knot Carnot fraction (steps between knots) and a
    0.37 kW fixed overhead (COP rises with output up to the maximum), no frost term."""
    eta, p0, x = COP_FITS["F29_x0.015"]
    return UnitParams(cop_form="knots", eta=eta, p0_kw=p0, x_pen=x)


def legacy_frost() -> UnitParams:
    """Frost per compressor run-minute regardless of output, quiet mode x1.5 (before review round 1)."""
    return UnitParams(frost_mode="run_min", frost_rh_gain=0.035, quiet_frost_factor=1.5, frost_stop_rmax=0.0)


def legacy_surge() -> UnitParams:
    """120-minute surge probability from the outdoor-temperature table (before review round 1)."""
    return UnitParams(oil_mode="outdoor", oil_from_defrost=False)


def surge_from_start() -> UnitParams:
    """The 120-minute timer counts from the compressor start only (round 1; review round 2 restarts
    it after a defrost)."""
    return UnitParams(oil_from_defrost=False)


def high_start_loss() -> UnitParams:
    """Each start costs 0.15 kWh more electricity than measured (upper bound of literature)."""
    return UnitParams(start_loss_kwh=0.15)


def sluggish() -> UnitParams:
    """Slower capacity ramps, longer minimum run/off and stop hold (firmware uncertainty)."""
    return UnitParams(ramp_up_k=0.07, start_k=3.2, min_off_min=5, stop_hold_min=4, min_run_min=7)


def more_frost() -> UnitParams:
    """40 % more frost per kWh (a humid winter, or a dirtier coil)."""
    return UnitParams(frost_scale=1.4)


def less_frost() -> UnitParams:
    """30 % less frost per kWh (review round 2: was an unfitted idle melt, now the mirror of
    more_frost; the off-time removal is fitted and has its own bounds)."""
    return UnitParams(frost_scale=0.7)


def _frost_fit(rmax: float, **kw) -> UnitParams:
    k, g = FROST_FITS[rmax]
    return UnitParams(frost_kwh=k, frost_rh_gain=g, frost_stop_rmax=rmax, **kw)


def frost_melt_lo() -> UnitParams:
    """Less of the defrost-trigger state lost while off (rmax 0.2 instead of 0.4), K refitted
    (just outside the 90 % profile interval): continuous runs defrost a little later, on/off ones
    earlier. Mandatory ranking variant (review round 2, N1)."""
    return _frost_fit(0.2)


def frost_melt_hi() -> UnitParams:
    """More lost while off (rmax 0.6), K refitted (just outside the 90 % profile interval):
    continuous runs defrost earlier, on/off ones later. Mandatory ranking variant (review round 2)."""
    return _frost_fit(0.6)


def frost_no_melt() -> UnitParams:
    """Frost kept while off (the round-1 structure) with K refitted on the same segments: a
    diagnostic, rejected by the data."""
    return _frost_fit(0.0)


def legacy_frost_r1() -> UnitParams:
    """The exact round-1 frost model: round-1 table, linear interpolation, +2.15 %/% RH, nothing
    lost while off."""
    return UnitParams(frost_kwh_t=FROST_KWH_T_R1, frost_kwh=FROST_KWH_R1, frost_log_interp=False,
                      frost_rh_gain=0.0215, frost_stop_rmax=0.0)


def quiet_frost() -> UnitParams:
    """Quiet mode adds x1.5 frost on top of the lower output (the old ASSUMED factor)."""
    return UnitParams(quiet_frost_factor=1.5)


def pump_always_on() -> UnitParams:
    """Space heating off keeps the loop circulating (the behaviour before review round 1)."""
    return UnitParams(pump_off_when_disabled=False)


VARIANTS = {
    "central": central,
    "low_flow": low_flow,
    "high_flow": high_flow,
    "shallow_outlet": shallow_outlet,
    "steep_outlet": steep_outlet,
    "flat_load": flat_load,
    "partload_lo": partload_lo,
    "partload_hi": partload_hi,
    "legacy_cop": legacy_cop,
    "legacy_frost": legacy_frost,
    "legacy_surge": legacy_surge,
    "surge_from_start": surge_from_start,
    "high_start_loss": high_start_loss,
    "sluggish": sluggish,
    "more_frost": more_frost,
    "less_frost": less_frost,
    "frost_melt_lo": frost_melt_lo,
    "frost_melt_hi": frost_melt_hi,
    "frost_no_melt": frost_no_melt,
    "legacy_frost_r1": legacy_frost_r1,
    "quiet_frost": quiet_frost,
    "pump_always_on": pump_always_on,
}


# ------------------------------------------------------------------------------------------
# self-check
# ------------------------------------------------------------------------------------------

def sensitivities(p: UnitParams):
    """%COP per +1 K supply and COP at min/mid/max output (used by the report)."""
    out = {}
    for ta in (-7.0, 0.0, 7.0):
        for q in (q_min(p, ta), 6.0, q_max(p, ta, 35.0)):
            c30 = cop_steady(p, 30.0, ta, q)
            c31 = cop_steady(p, 31.0, ta, q)
            out[(ta, round(q, 1))] = (round(c30, 2), round(100 * (c31 / c30 - 1), 2))
    return out


def _self_check():
    import time

    p = UnitParams()
    # 1) more lift -> lower COP; colder -> lower COP; every variant
    for ta in (-7.0, 0.0, 7.0):
        c30, c35, c45 = (cop_steady(p, tw, ta, 5.0) for tw in (30.0, 35.0, 45.0))
        assert c30 > c35 > c45 > 1.0, (ta, c30, c35, c45)
        print(f"T_amb {ta:+.0f}: COP at 5 kW W30 {c30:.2f}  W35 {c35:.2f}  W45 {c45:.2f}  "
              f"dCOP/K at W30 {100 * (cop_steady(p, 31, ta, 5) / c30 - 1):+.2f} %")
    assert cop_steady(p, 35, -7, 5) < cop_steady(p, 35, 0, 5) < cop_steady(p, 35, 7, 5)
    for name, fn in VARIANTS.items():
        v = fn()
        for ta in (-10.0, 0.0, 7.0, 15.0):
            assert cop_steady(v, 30, ta, 5) > cop_steady(v, 40, ta, 5) > 1.0, (name, ta)
    print("sensitivities (central):", sensitivities(p))
    # review round 1: COP does not keep rising to the maximum, and its outdoor slope is smooth
    for ta in (0.0, 7.0):
        qs = [3.0 + 0.25 * i for i in range(int((q_max(p, ta, 30.0) - 3.0) / 0.25) + 1)]
        cops = [cop_steady(p, 30.0, ta, q) for q in qs]
        assert cops[-1] <= max(cops) + 1e-9 and cops[-1] < 1.02 * cop_steady(p, 30.0, ta, q_p95(p, ta))
    slopes = [100 * (cop_steady(p, 30.0, t + 1, 5.0) / cop_steady(p, 30.0, t, 5.0) - 1) for t in range(-15, 15)]
    assert max(slopes) < 7.0 and min(slopes) > -1.0, slopes
    assert max(abs(a - b) for a, b in zip(slopes[1:], slopes[:-1])) < 3.5, slopes
    print("COP per +1 K outdoor at W30/5 kW, -15..+14 degC:", " ".join(f"{v:+.1f}" for v in slopes))
    # frost follows the air heat: twice the output, about twice (x 2^0.28 more) the frost per minute
    f1 = frost_rate_per_min(p, 0.0, 90.0, False, q=4.0)
    f2 = frost_rate_per_min(p, 0.0, 90.0, False, q=8.0)
    assert 1.9 < f2 / f1 < 2.8, f2 / f1

    # 2) no heat when off, start/stop rules
    u = VersatiUnit(p)
    r = u.step(setpoint=25, restart_delta=4, t_return=24.0, t_amb=5.0)
    assert not r.compressor and r.q_loop == 0.0 and r.p_outdoor < 0.1
    # gap = 28 - (24 - 0.70) = 4.70 >= 4 -> pre-start minute, then start
    r = u.step(setpoint=28, restart_delta=4, t_return=24.0, t_amb=5.0)
    assert not r.compressor and r.q_loop == 0.0 and r.p_outdoor > 0.1
    r = u.step(setpoint=28, restart_delta=4, t_return=24.0, t_amb=5.0)
    assert r.compressor and r.started and r.q_loop > 0
    # setpoint written > 2 K below t_ctrl -> stops once the minimum run is over
    n_on = 0
    for _ in range(10):
        r = u.step(setpoint=20, restart_delta=4, t_return=26.0, t_amb=5.0)
        n_on += r.compressor
    assert not r.compressor and n_on == p.min_run_min - 1, n_on
    u2 = VersatiUnit(p)
    for _ in range(5):
        r = u2.step(setpoint=27, restart_delta=4, t_return=23.9, t_amb=5.0)  # gap 3.8 < 4
        assert not r.compressor
    u3 = VersatiUnit(p)
    for _ in range(5):
        r = u3.step(setpoint=27, restart_delta=4, t_return=24.0, t_amb=5.0, heating_enabled=False)
        assert not r.compressor and r.status == "off"

    # 3) energy bookkeeping: q_loop integral = flow * cp * (t_supply - t_return); COP sane
    u4 = VersatiUnit(p)
    e_heat = e_water = e_el = 0.0
    t_ret = 24.0
    for i in range(900):
        r = u4.step(setpoint=31, restart_delta=4, t_return=t_ret, t_amb=2.0, dhw_demand=(300 <= i < 322))
        e_heat += r.q_loop / 60.0
        e_water += CP_WATER * r.loop_flow_lpm / 60.0 * (r.t_supply - t_ret) / 60.0
        e_el += r.p_outdoor / 60.0
        assert r.p_total >= r.p_outdoor >= 0.0
        if r.status in ("idle", "off", "dhw"):
            assert r.q_loop == 0.0
        if r.loop_flow_lpm > 0:  # crude loop: return follows supply slowly towards a 22 degC floor
            t_ret += (r.t_supply - t_ret) * 0.04 + (22.0 - t_ret) * 0.01
    assert abs(e_heat - e_water) < 1e-6 * max(1.0, abs(e_heat)), (e_heat, e_water)
    assert 1.5 < e_heat / e_el < 7.0, e_heat / e_el
    print(f"900-min loop test: heat {e_heat:.2f} kWh, electricity {e_el:.2f} kWh, COP {e_heat / e_el:.2f}, "
          f"starts {u4.n_starts}, dhw {u4.n_dhw}, defrosts {u4.n_defrost}, surges {u4.n_oil}")

    # 4) speed: 180 days
    u5 = VersatiUnit(p)
    t0 = time.perf_counter()
    t_ret = 25.0
    n = 180 * 1440
    for i in range(n):
        r = u5.step(30, 4, t_ret, 3.0 + 6.0 * math.sin(i / 1440 * 6.283), 85.0, dhw_demand=(i % 1440) < 20)
        if r.loop_flow_lpm > 0:
            t_ret += (r.t_supply - t_ret) * 0.03 + (23.0 - t_ret) * 0.004
    dt = time.perf_counter() - t0
    print(f"180-day run: {dt:.1f} s ({1e6 * dt / n:.1f} us/step), starts {u5.n_starts}, defrosts {u5.n_defrost}")
    assert dt < 30
    print("self-check OK")


if __name__ == "__main__":
    _self_check()
