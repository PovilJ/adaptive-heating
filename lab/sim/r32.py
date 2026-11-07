"""R32 (difluoromethane) properties from the Peng-Robinson equation of state (numpy only).

Used only to analyse the measured refrigerant temperatures of the heat pump (condensing,
suction, discharge, liquid line) - not inside the 1-minute simulator.

- Vapour (saturated and superheated): Peng-Robinson departure functions on an ideal-gas heat
  capacity. PR is good for the vapour phase; its saturation pressure is within ~1 % of the
  reference values (self_check()).
- Liquid: PR liquid enthalpies are poor (latent heat ~4 % high), so the saturated-liquid
  enthalpy is h_vapour - latent heat, with the latent heat from the Watson correlation anchored
  at the normal boiling point (-51.65 degC, 381.9 kJ/kg). This gives 315 kJ/kg at 0 degC and
  ~240 kJ/kg at 40 degC, matching published R32 tables to ~1-2 %. Subcooled liquid uses
  cp_liquid = 1.9 kJ/(kg K).

Only enthalpy DIFFERENCES are used (the zero point is arbitrary: saturated vapour at 0 degC is
set to 515 kJ/kg, close to the IIR convention). The resulting uncertainty (~2-3 % on the
heat/work ratio) is far below the other uncertainties of the refrigerant-side heat estimate
(sensor placement, injection flow, drive losses).
"""
import math

import numpy as np

R = 8.314462618  # J/(mol K)
M = 0.052024  # kg/mol
TC = 351.255  # K
PC = 5.782e6  # Pa
OMEGA = 0.2769
_KAPPA = 0.37464 + 1.54226 * OMEGA - 0.26992 * OMEGA**2
_A0 = 0.45724 * R**2 * TC**2 / PC
_B = 0.07780 * R * TC / PC
_S2 = math.sqrt(2.0)


def _cp0(T):
    """Ideal-gas heat capacity, J/(mol K). Linear fit to tabulated ideal-gas values for
    difluoromethane (42.9 J/mol/K at 298 K, ~51 at 400 K)."""
    return 42.9 + 0.081 * (T - 298.15)


def _h_ig(T):
    """Ideal-gas enthalpy relative to 273.15 K, J/mol (integral of _cp0)."""
    T0 = 273.15
    return 42.9 * (T - T0) + 0.081 * 0.5 * ((T - 298.15) ** 2 - (T0 - 298.15) ** 2)


def _a(T):
    sq = 1.0 + _KAPPA * (1.0 - math.sqrt(T / TC))
    return _A0 * sq * sq


def _dadT(T):
    sq = 1.0 + _KAPPA * (1.0 - math.sqrt(T / TC))
    return -_A0 * sq * _KAPPA / math.sqrt(T * TC)


def _roots(T, P):
    A = _a(T) * P / (R * T) ** 2
    B = _B * P / (R * T)
    c = [1.0, -(1.0 - B), A - 3 * B * B - 2 * B, -(A * B - B * B - B**3)]
    z = np.roots(c)
    z = np.real(z[np.abs(np.imag(z)) < 1e-9])
    z = z[z > B]
    return np.sort(z), A, B


def _lnphi(Z, A, B):
    return (Z - 1 - math.log(Z - B)
            - A / (2 * _S2 * B) * math.log((Z + (1 + _S2) * B) / (Z + (1 - _S2) * B)))


def _h_dep(T, P, Z):
    B = _B * P / (R * T)
    return (R * T * (Z - 1)
            + (T * _dadT(T) - _a(T)) / (2 * _S2 * _B) * math.log((Z + (1 + _S2) * B) / (Z + (1 - _S2) * B)))


def psat(T):
    """Saturation pressure (Pa) at temperature T (K) from the PR fugacity balance."""
    # start from a Lee-Kesler style estimate and iterate on the fugacity ratio
    P = PC * math.exp(5.373 * (1 + OMEGA) * (1 - TC / T))
    for _ in range(100):
        z, A, B = _roots(T, P)
        if len(z) < 2:
            P *= 1.02 if len(z) and z[0] > 0.3 else 0.98
            continue
        zl, zv = z[0], z[-1]
        r = math.exp(_lnphi(zl, A, B) - _lnphi(zv, A, B))
        P *= r
        if abs(r - 1) < 1e-10:
            break
    return P


def _h_raw(T, P, phase):
    z, A, B = _roots(T, P)
    Z = z[0] if phase == "liquid" else z[-1]
    return _h_ig(T) + _h_dep(T, P, Z)


_T0 = 273.15
_H_OFF = None


def _offset():
    global _H_OFF
    if _H_OFF is None:
        _H_OFF = 515.0 - _h_raw(_T0, psat(_T0), "vapour") / M / 1000.0
    return _H_OFF


TB = 273.15 - 51.65  # normal boiling point, K
LB = 381.9  # latent heat at the normal boiling point, kJ/kg
CP_LIQ = 1.9  # kJ/(kg K), subcooled liquid


def latent(T_c):
    """Latent heat kJ/kg (Watson correlation, exponent 0.38)."""
    return LB * ((TC - (T_c + 273.15)) / (TC - TB)) ** 0.38


def h_vap(T_c, P_pa):
    """Specific enthalpy kJ/kg of (superheated or saturated) vapour at T_c degC and P_pa."""
    return _h_raw(T_c + 273.15, P_pa, "vapour") / M / 1000.0 + _offset()


def sat(T_c):
    """(P_pa, h_liquid, h_vapour) on the saturation line at T_c degC."""
    P = psat(T_c + 273.15)
    hv = h_vap(T_c, P)
    return P, hv - latent(T_c), hv


def h_liq(T_sat_c, T_c):
    """Liquid at T_c degC below a saturation temperature T_sat_c (subcooled)."""
    return sat(T_sat_c)[1] - CP_LIQ * max(T_sat_c - T_c, 0.0)


def _s_raw(T, P):
    """Vapour molar entropy J/(mol K) up to a constant (ideal gas at 298.15 K, 1 bar + PR departure)."""
    z, A, B = _roots(T, P)
    Z = z[-1]
    s_ig = 42.9 * math.log(T / 298.15) + 0.081 * (T - 298.15 - 298.15 * math.log(T / 298.15)) - R * math.log(P / 1e5)
    s_dep = R * math.log(Z - B) + _dadT(T) / (2 * _S2 * _B) * math.log((Z + (1 + _S2) * B) / (Z + (1 - _S2) * B))
    return s_ig + s_dep


def h_isentropic(T1_c, P1_pa, P2_pa):
    """Enthalpy kJ/kg after isentropic compression of vapour at (T1_c, P1_pa) to P2_pa, and its temperature."""
    s1 = _s_raw(T1_c + 273.15, P1_pa)
    lo, hi = T1_c + 273.15, T1_c + 273.15 + 150.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if _s_raw(mid, P2_pa) < s1:
            lo = mid
        else:
            hi = mid
    T2 = 0.5 * (lo + hi) - 273.15
    return h_vap(T2, P2_pa), T2


def cycle(t_evap_c, t_cond_c, superheat=3.0, subcool=2.0, eta_overall=0.62, shell_loss=0.05):
    """Simple single-stage vapour-compression heating cycle (no injection).

    eta_overall = isentropic work / electrical compressor input (compressor x motor x drive).
    shell_loss = fraction of the electrical input lost from the compressor shell to ambient.
    Returns (heating COP of the compressor, isentropic discharge temperature degC)."""
    p_e = psat(t_evap_c + 273.15)
    p_c = psat(t_cond_c + 273.15)
    h1 = h_vap(t_evap_c + superheat, p_e)
    h2s, t2s = h_isentropic(t_evap_c + superheat, p_e, p_c)
    h3 = h_liq(t_cond_c, t_cond_c - subcool)
    w_el = (h2s - h1) / eta_overall  # electrical input per kg
    q_evap = h1 - h3
    q_cond = q_evap + w_el * (1 - shell_loss)
    return q_cond / w_el, t2s


def self_check():
    # Reference values (NIST/REFPROP R32 saturation tables, rounded): Psat MPa, latent kJ/kg
    ref = {-20: (0.4052, 343.0), 0: (0.8131, 315.6), 20: (1.4746, 281.6), 40: (2.4783, 238.9)}
    print(" T   Psat MPa (ref)   latent kJ/kg (ref)  h_v")
    for T, (p, L) in ref.items():
        P, l, v = sat(T)
        print(f"{T:4d} {P/1e6:7.4f} ({p:.4f})  {v-l:6.1f} ({L:.1f})  {v:6.1f}")


if __name__ == "__main__":
    self_check()
