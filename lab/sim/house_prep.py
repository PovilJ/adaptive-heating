"""Identification inputs for the house model, built from the lab minute grid (private output).

Builds one 1-minute array set over the raw window and caches it in
`.local/lab-results/house/prep.npz`:

- `q_loop` (kW): heat into the space-heating loop. Measured as cp * flow * (outlet + 0.30 - inlet)
  while the Versati data is valid (the 0.30 K is the idle sensor offset from the unit stage, flow
  29 L/min). While the 3-way valve is on the tank side (HOT WATER and the 7 minutes after) the loop
  gets nothing. In Versati link gaps the heat is estimated from the metered electricity with the
  unit model's steady COP and the minute is flagged `q_est`.
- `ret` (degC): loop return (inlet sensor) where it is a loop reading: valid data, not during or
  within 15 minutes after hot water, and only while the circulation pump serves the floor (heating
  mode 4; in the summer DHW-only mode the inlet reads plant-room water).
- `room` (degC): the controllers' living-room sensor (old 0.2 K device until 2026-10-22, new 0.1 K
  device after), `room_res` its resolution.
- weather and sun: `t_out` (ERA5 2 m), `rh`, `ghi`, `dni`, `dhi`, `poa_s/e/w/n`, `sun_elev`,
  `sun_az`; `hour_local` (Europe/Vilnius) for internal-gain profiles.
- `ac_heat`: any air conditioner in heat mode that plausibly heats the living area (living room or
  bedroom units; the third unit sat in 'heat' all of Oct-Nov with no extra electricity and is
  ignored), `other_kw` = whole-house electricity minus the heat pump (from 2026-07-07).
- `ok_unit`, `heating_on` (mode register 4), `elec_kw`.

Run: .local/lab-venv/bin/python -m lab.sim.house_prep
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from lab.data.common import RESULTS, load_minute  # noqa: E402
from lab.sim import unit as U  # noqa: E402

OUT = RESULTS / "house"
PREP = OUT / "prep.npz"
FLOW_LPM = 29.0
K_FLOW = U.CP_WATER * FLOW_LPM / 60.0  # kW/K
OUTLET_OFFSET = 0.30  # true supply = outlet + 0.30 on the inlet scale (unit stage)
DHW_POST_MIN = 7  # valve on the tank side after DHW (no loop heat)
RET_DHW_EXCL_MIN = 15  # inlet shows tank-coil water after DHW


def _since(flag: np.ndarray) -> np.ndarray:
    """Minutes since flag was last true (large before the first)."""
    idx = np.where(flag, np.arange(len(flag)), -10**9)
    last = np.maximum.accumulate(idx)
    return np.arange(len(flag)) - last


def _elec_heat(elec_kw, t_amb, t_sup):
    """Steady heat output whose outdoor-unit electricity equals elec_kw (unit model, central)."""
    p = U.central()
    out = np.zeros(len(elec_kw))
    for i, (e, ta, ts) in enumerate(zip(elec_kw, t_amb, t_sup)):
        if not e > 0.3:
            continue
        lo, hi = 0.0, 14.0
        for _ in range(30):
            mid = 0.5 * (lo + hi)
            if U.p_running(p, ts, ta, mid) < e:
                lo = mid
            else:
                hi = mid
        out[i] = 0.5 * (lo + hi)
    return out


def build():
    d = load_minute()
    t = d["time_epoch_s"].astype(np.int64)
    n = len(t)
    f = lambda k: d[k].astype(np.float64)  # noqa: E731
    st = d["unit_status"]
    ok = np.nan_to_num(f("versati_ok")) == 1
    outlet, inlet = f("outlet"), f("inlet")
    ok &= ~np.isnan(outlet) & ~np.isnan(inlet)
    mode = f("heating_mode")
    # heating mode register: carry the last known value through link gaps
    mk = np.where(~np.isnan(mode), np.arange(n), -1)
    mk = np.maximum.accumulate(mk)
    mode_ff = np.where(mk >= 0, mode[np.maximum(mk, 0)], 4.0)  # before the first read: winter
    heating_on = mode_ff == 4
    dhw = st == "HOT WATER"
    since_dhw = _since(dhw)
    valve_tank = dhw | (since_dhw <= DHW_POST_MIN)

    q = np.where(ok, K_FLOW * (outlet + OUTLET_OFFSET - inlet), np.nan)
    q[ok & valve_tank] = 0.0
    q[ok & ~heating_on] = 0.0  # summer: only DHW
    # link gaps: electricity -> heat (unit steady model), flagged
    elec = f("elec_w") / 1000.0
    gap = ~ok
    sp = f("setpoint")
    sk = np.where(~np.isnan(sp), np.arange(n), -1)
    sk = np.maximum.accumulate(sk)
    sp_ff = np.where(sk >= 0, sp[np.maximum(sk, 0)], 30.0)
    t_out = f("wx_t")
    gi = np.where(gap & heating_on)[0]
    qe = _elec_heat(np.nan_to_num(elec[gi]), t_out[gi], np.clip(sp_ff[gi], 25, 40))
    q[gap] = 0.0
    q[gi] = qe
    q_est = gap & heating_on & (np.nan_to_num(elec) > 0.3)
    q_est |= gap & heating_on & np.isnan(elec)

    ret = np.where(ok & heating_on & (since_dhw > RET_DHW_EXCL_MIN), inlet, np.nan)
    sup = np.where(ok & heating_on & ~valve_tank, outlet + OUTLET_OFFSET, np.nan)

    room = f("room")
    room_res = np.where(f("room_src") == 2, 0.1, 0.2)
    tz = ZoneInfo("Europe/Vilnius")
    hl = np.empty(n)
    # local hour: offset changes only at DST switches -> compute per hour block
    for i0 in range(0, n, 60):
        ts = dt.datetime.fromtimestamp(int(t[i0]), tz)
        off = ts.utcoffset().total_seconds()
        hl[i0:i0 + 60] = ((t[i0:i0 + 60] + off) % 86400) / 3600.0
    ac_heat = (d["ac_living_mode"] == "heat") | (d["ac_bed_mode"] == "heat")
    busy = ("heat", "cool", "dry", "fan_only", "auto")
    ac_any = np.isin(d["ac_living_mode"], busy) | np.isin(d["ac_bed_mode"], busy)
    other = f("house_load_kw") - np.nan_to_num(elec)
    arrays = dict(
        t=t, q_loop=q, q_est=q_est, ret=ret, sup=sup, room=room, room_res=room_res,
        room_age=f("room_age_min"), t_out=t_out, rh=f("wx_rh"), ghi=f("wx_ghi"), dni=f("wx_dni"),
        dhi=f("wx_dhi"), poa_s=f("poa_s"), poa_e=f("poa_e"), poa_w=f("poa_w"), poa_n=f("poa_n"),
        sun_elev=f("sun_elev"), sun_az=f("sun_az"), snow=f("wx_snow_depth"), wind=f("wx_wind"),
        hour_local=hl, ac_heat=ac_heat, ac_any=ac_any, other_kw=other, ok_unit=ok, heating_on=heating_on,
        elec_kw=elec, dhw=dhw, valve_tank=valve_tank, compressor=np.nan_to_num(f("compressor")),
        t_bedroom=f("t_bedroom"), t_storage=f("t_storage"), t_room_c=f("t_room_c"),
        t_tstat_main=f("t_tstat_main"), t_aux1=f("t_aux1"), legacy_on=f("legacy_on"),
        vent_m3h=f("vent_supply_m3h"), pv_kw=f("pv_kw"),
    )
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(PREP, **arrays)
    return arrays


def load():
    if not PREP.exists():
        return build()
    with np.load(PREP) as z:
        return {k: z[k] for k in z.files}


if __name__ == "__main__":
    a = build()
    ok = a["ok_unit"] & a["heating_on"]
    print("minutes", len(a["t"]), "heating minutes with unit data", int(ok.sum()),
          "estimated-heat minutes", int(a["q_est"].sum()))
