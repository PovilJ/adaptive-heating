"""Slab thermostat: the heating controller of Adaptive Heating 0.6 (standard library only).

This is the lab's `hybrid` controller (lab/controllers/hybrid.py, evidence in
docs/research/CONTROLLER_COMPARISON.md) made into the production core. It never imports
Home Assistant: the coordinator maps entity states into `Inputs`, the lab wrapper
(lab/controllers/production.py) maps the simulator's Observation into the same `Inputs`, so
both run this exact file.

How it works, in short (docs/CONTROLLER.md has the long version):

1. **The floor slab is read from the water.** The circulation pump never stops, so while the
   compressor is idle the return water is the slab; while it runs, slab = (return -
   share x supply) / (1 - share). Frozen during and after hot water and defrost.
2. **The slab has a target** = room target + weather term (forecast hours 1-9) + offset - sun
   (forecast hours 1-9) + kp x room error + learned integral + learned daily pattern + a small
   "the next three hours are warmer than the day" term. The room error is corrected for sun
   shining on the thermometer.
3. **When to run:** start when the slab is `band` under its target, stop when it is `band`
   over (minimum run and rest times).
4. **How to run:** kick a start with the smallest setpoint the unit's restart rule accepts,
   ride the setpoint inside the firmware's dead band so the unit delivers about `q_run` kW
   (more when the slab falls behind), end the run with one write under the stop threshold,
   and park the idle setpoint just under the unit's own restart point.

Fail-safes: no writes while the unit's values are unavailable; hot water, defrost and an
operating state nobody mapped freeze the slab estimate and the run waits; a missing, stale (4 h)
or frozen (12 h unchanged) room thermometer stops learning, drops the room terms and lets the
integral relax to the value it needed at this outdoor temperature; a missing forecast uses the
hours of the last one still ahead, else the day-mean outdoor temperature; a rolling write budget
(40 trims, 46 writes of any kind per 24 h). The learned integral, daily pattern, fallback curve,
write log and the room/clock bookkeeping survive restarts through `state()` / `restore()`;
`release()` gives the setpoint to leave on the unit when control ends.

Production safety rules on top of the lab hybrid (docs/CONTROLLER.md, "Differences from the lab
hybrid"; `Params.lab_hybrid=True` switches them off for the bit-for-bit equivalence check):
the room input may move at most `room_slew` K a minute and the learners take at most
`learn_cap` K of room error (sensor spikes); the parked setpoint never reaches the restart point,
even when Minimum water is higher; a small lowering of the park waits like a small raise; a start
right after the controller's own stop, or with the floor over its stop point, is not adopted;
a run adopted at a handover can end at once.

Time: `Inputs.minute` is any monotonic minute clock (epoch minutes in Home Assistant, the
simulator's minute index in the lab). Steps may come at any spacing; at exactly one minute
the arithmetic is the lab hybrid's, bit for bit.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, fields, replace
from datetime import datetime, timedelta, timezone
import math

KNOTS = (-15.0, -5.0, 5.0, 15.0)  # outdoor knots of the room-lost fallback curve
STATE_VERSION = 1
MAX_STEP_MINUTES = 60.0           # a longer gap (Home Assistant busy or stopped) counts as this
RUNTIME_MAX_AGE = 60.0            # min: a saved floor estimate older than this is not reused


@dataclass(frozen=True)
class Params:
    """Controller parameters. Defaults are the lab hybrid's final values (hybrid.md section 5)."""
    # slab target
    b: float = 0.20             # K slab per K (target - forecast outdoor)
    ts0: float = 1.0            # K offset of the prior (the integral learns the level)
    aim: float = 0.0            # K added to the room target
    s: float = 0.030            # K slab per W/m2 of forecast sun (hours lead0..lead1)
    lead0: int = 1
    lead1: int = 9
    kp: float = 3.0             # K slab per K room error
    ki: float = 0.15            # K slab per K-hour of room error
    i_lim: float = 6.0
    glow: float = 0.0008        # K per W/m2: sun on the thermometer
    kw: float = 0.3             # K slab per K the next 3 h are warmer than the next 24 h
    d_g: float = 1.0            # daily pattern: K slab per K-hour per day
    d_lead: float = 5.0         # h, slab -> room lag
    d_lim: float = 2.0
    d_leak: float = 30.0        # days
    # duty cycle
    band: float = 1.4
    min_run: float = 60.0
    min_off: float = 45.0
    # execution
    q_run: float = 6.5          # kW while riding; 0 = the unit's floor output
    kq: float = 2.0             # extra kW per K of slab deficit beyond the band
    q_hi: float = 9.0
    ride_every: float = 8.0     # min between ride writes
    ride_hyst: float = 1.3      # K the ideal ride setpoint must move before a rewrite
    budget: float = 40.0        # writes per rolling 24 h for trims
    hard_cap: int = 46          # writes per rolling 24 h, everything included
    stale_min: float = 240.0    # room value older than this is lost
    frozen_h: float = 12.0      # room value unchanged this long is lost
    tau_fb: float = 72.0        # h: the fallback curve follows the integral
    # house and unit constants (first-house values; options in Home Assistant)
    loop_kw_per_k: float = 2.02     # loop heat per K of water delta-T (flow x heat capacity)
    supply_share: float = 0.29      # running: slab = (return - share x supply) / (1 - share)
    ctrl_offset: float = -0.80      # control sensor minus return (idle) / true supply (running)
    outlet_offset: float = 0.30     # true supply minus the outlet sensor
    # setpoint limits
    sp_floor: float = 25.0      # lowest park / ride setpoint (Minimum water)
    sp_ceil: float = 39.0       # highest ride setpoint
    write_min: float = 20.0     # absolute write range (a stop may go under sp_floor)
    write_max: float = 45.0
    # production safety rules (docs/CONTROLLER.md, "Differences from the lab hybrid")
    room_slew: float = 0.05     # K per minute the room input may move; 0 = off
    learn_cap: float = 1.5      # K of room error the daily pattern takes at most; 0 = off
    lab_hybrid: bool = False    # True: exactly the lab hybrid's rules (equivalence checks only)

    @classmethod
    def from_mapping(cls, values: dict) -> "Params":
        known = {f.name: f.type for f in fields(cls)}
        out = {}
        for key, value in values.items():
            if key == "lab_hybrid":
                out[key] = value if isinstance(value, bool) else str(value).strip().lower() in ("1", "1.0", "true", "yes")
            elif key in known:
                out[key] = int(value) if key in ("lead0", "lead1", "hard_cap") else float(value)
        return cls(**out)


@dataclass(frozen=True)
class Hour:
    """One forecast hour: `minute` is the END of the hour on the controller's clock."""
    minute: float
    outdoor: float
    ghi: float | None = None    # W/m2, mean over the hour


@dataclass(frozen=True)
class Inputs:
    minute: float               # monotonic minute clock
    local_hour: float           # local clock hour 0-24
    target: float               # room target, degC
    outdoor: float              # outdoor temperature now, degC
    outlet: float               # leaving-water sensor, degC
    inlet: float                # return-water sensor, degC
    setpoint: float             # leaving-water setpoint active on the unit, degC
    restart_delta: float        # unit's restart hysteresis, K
    compressor_on: bool
    mode: str                   # 'heat' | 'dhw' | 'defrost' | 'idle' | 'off' | 'other' (unmapped state)
    room: float | None = None   # room thermometer
    room_age_min: float = 0.0
    forecast: tuple = ()        # Hour, starting with the hour now running
    link_ok: bool = True        # False: unit values are the last known ones; never write
    act: bool = True            # False: decide but do not count writes (Observe; Home Assistant
                                #        counts a write with commit() once the device took it)
    learn: bool = True          # False: keep the integral, daily pattern and curve as they are
    shield: bool = False        # an assistance heater owns the room: room above target counts as on target


@dataclass(frozen=True)
class Decision:
    setpoint: float | None      # write this (whole degC) now, or None
    phase: str                  # idle | kick | ride | stop | wait | hold
    want: float | None          # the setpoint this phase wants on the unit


# ---------------------------------------------------------------------- sun
# Home Assistant forecasts carry cloud cover, not irradiance. The lab tuned the sun term on
# Open-Meteo's hourly global horizontal irradiance (GHI); production rebuilds it as a clear-sky
# GHI (Haurwitz) times a cloud factor, averaged over the hour. The cloud factor
# 1 - 0.36 c - 0.16 c^20 was fitted on the site's archived hourly irradiance and forecast-model
# total cloud cover outside the lab's ranking season (Apr-Nov 2026): model "overcast" still
# passes about half the clear-sky sun. On the held-out season it gives a mean of 163 W/m2
# against 165 measured (the textbook Kasten-Czeplak law, 1 - 0.75 c^3.4, gives 131) and an
# hourly error of 61 W/m2 (KC 85). docs/CONTROLLER.md, "Sun".


def sun_elevation(when: datetime, latitude: float, longitude: float) -> float:
    """Solar elevation in degrees (NOAA low-accuracy formulas)."""
    u = when.astimezone(timezone.utc)
    g = 2 * math.pi / 365 * (u.timetuple().tm_yday - 1 + (u.hour - 12) / 24)
    eq = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                   - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    dec = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
           + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    hour_angle = math.radians((u.hour * 60 + u.minute + u.second / 60 + eq + 4 * longitude) / 4 - 180)
    lat = math.radians(latitude)
    sin_el = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(hour_angle)
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_el))))


def clear_sky_ghi(when: datetime, latitude: float, longitude: float) -> float:
    """Clear-sky global horizontal irradiance, W/m2 (Haurwitz 1945)."""
    c = math.sin(math.radians(sun_elevation(when, latitude, longitude)))
    return 0.0 if c <= 0.01 else 1098.0 * c * math.exp(-0.057 / c)


def cloud_factor(cloud_percent: float | None) -> float:
    """Share of the clear-sky sun that reaches the ground under a forecast total cloud cover.
    Unknown cloud counts as overcast: no sun is credited that the forecast does not promise."""
    c = 1.0 if cloud_percent is None or not _finite(cloud_percent) else min(max(cloud_percent / 100.0, 0.0), 1.0)
    return 1.0 - 0.36 * c - 0.16 * c ** 20


def hour_ghi(end: datetime, latitude: float, longitude: float, cloud_percent: float | None) -> float:
    """Mean GHI over the hour ending at `end`, W/m2, for a forecast cloud cover (0-100 %)."""
    clear = sum(clear_sky_ghi(end - timedelta(minutes=55 - 10 * i), latitude, longitude) for i in range(6)) / 6
    return clear * cloud_factor(cloud_percent)


def _near(cur: float, new: float, n: float, dt: float) -> float:
    """Move cur toward new by 1/n per minute (exact lab arithmetic at dt == 1)."""
    if dt == 1.0:
        return cur + (new - cur) / n
    return cur + (new - cur) * (1.0 - (1.0 - 1.0 / n) ** dt)


def _mix(cur: float, new: float, r: float, dt: float) -> float:
    """Move cur toward new by the fraction r per minute (exact lab arithmetic at dt == 1)."""
    if dt == 1.0:
        return cur + r * (new - cur)
    return cur + (1.0 - (1.0 - r) ** dt) * (new - cur)


def _finite(*values) -> bool:
    return all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values)


class SlabController:
    def __init__(self, params: Params | None = None) -> None:
        self.p = params or Params()
        p = self.p
        self.eff = 1.0 - p.supply_share
        # learned state (persisted)
        self.integ = 0.0
        self.daily = [0.0] * 24
        self.fb = [self.integ] * len(KNOTS)
        self.wlog: deque = deque()
        # runtime
        self.t_avg = None
        self.fc_last = None
        self.ts = None
        self.run = False
        self.t_state = 999.0
        self.since_dhw = 999.0
        self.since_def = 999.0
        self.comp_min = 0.0
        self.comp_prev = 0.0
        self.kick_min = 0.0
        self.q_f = None
        self.last_write = -999.0
        self.last_sp = None
        self.room_ref = None
        self.room_since = 0.0
        self.room_f = None          # slew-limited room value
        self.frozen = False
        self.last_minute = None
        self.saved_minute = None    # clock of a restored runtime state
        self.stop_minute = -999.0   # last stop decision (no adoption right after it)
        self.unowned: deque = deque()  # minutes of stops of runs the unit started by itself
        self.dt = 1.0
        self.target = None
        # diagnostics of the last step
        self.phase = "hold"
        self.note = "start"
        self.want = None
        self.ts_star = None
        self.parts = {}
        self.e = None
        self.room_state = "missing"
        self.forecast_state = "none"
        self.weather = (None, 0.0, 0.0, 0.0)
        self.q_now = None
        self.restart_delta = None

    # ------------------------------------------------------------------ persistence
    def state(self) -> dict:
        """Learned state to persist across restarts (hand it to restore()). `runtime` keeps the
        room bookkeeping and the last write on the same clock, so a restart neither resets the
        frozen-thermometer detector nor the write guards; the floor estimate is reused only
        when the restart took under an hour."""
        return {"version": STATE_VERSION, "integ": self.integ, "daily": list(self.daily),
                "fb": list(self.fb), "writes": list(self.wlog),
                "runtime": {"minute": self.last_minute, "room_ref": self.room_ref, "room_since": self.room_since,
                            "last_write": self.last_write, "last_sp": self.last_sp, "t_avg": self.t_avg,
                            "ts": self.ts}}

    def restore(self, st: dict | None) -> bool:
        """Take a stored state; invalid parts are ignored. True when the integral was restored."""
        if not isinstance(st, dict) or st.get("version", STATE_VERSION) != STATE_VERSION:
            return False
        ok = False
        v = st.get("integ")
        if _finite(v):
            self.integ = min(max(float(v), -self.p.i_lim), self.p.i_lim)
            ok = True
        for key, n, lim in (("daily", 24, self.p.d_lim), ("fb", len(KNOTS), self.p.i_lim)):
            d = st.get(key)
            if isinstance(d, (list, tuple)) and len(d) == n and all(_finite(x) for x in d):
                setattr(self, key, [min(max(float(x), -lim), lim) for x in d])
        w = st.get("writes")
        if isinstance(w, (list, tuple)) and all(_finite(x) for x in w):
            self.wlog = deque(sorted(float(x) for x in w)[-self.p.hard_cap:])
        rt = st.get("runtime")
        if isinstance(rt, dict) and _finite(rt.get("minute")):
            self.saved_minute = float(rt["minute"])
            if _finite(rt.get("room_ref"), rt.get("room_since")):
                self.room_ref, self.room_since = float(rt["room_ref"]), float(rt["room_since"])
            if _finite(rt.get("last_write")):
                self.last_write = float(rt["last_write"])
                self.last_sp = float(rt["last_sp"]) if _finite(rt.get("last_sp")) else None
            for key in ("t_avg", "ts"):
                if _finite(rt.get(key)):
                    setattr(self, key, float(rt[key]))
        return ok

    def commit(self, minute: float, sp: float) -> None:
        """Count a write the caller made (Home Assistant steps with act=False and commits a
        write only once the device took it, so a refused or failed write is not counted)."""
        while self.wlog and minute - self.wlog[0] >= 1440:
            self.wlog.popleft()
        self.last_sp, self.last_write = float(sp), float(minute)
        self.wlog.append(float(minute))

    def release(self, x: Inputs) -> float | None:
        """Control ends (Observe, Off, an unload or an update): the setpoint to leave on the
        unit, or None when the one there is right. It is the idle park for the last floor
        target, so the unit's own restart rule keeps the floor near its start point and a
        ride or kick setpoint is never left to run the unit on its own. The caller writes it
        and commits it."""
        p = self.p
        if self.ts_star is None or not _finite(x.inlet, x.setpoint, x.restart_delta):
            return None
        # While running the return water is warmer than the floor; the park must stay under the
        # restart point once the unit idles, when the return water is the floor.
        base = x.inlet if not x.compressor_on or self.ts is None else min(x.inlet, self.ts)
        cap = math.floor(base + p.ctrl_offset + x.restart_delta - 0.6)
        want = math.floor(self.ts_star - p.band - 0.3 + x.restart_delta + p.ctrl_offset)
        park = float(min(max(min(max(want, p.sp_floor), cap), p.write_min), p.write_max))
        self.run, self.kick_min, self.q_f = False, 0.0, None
        return None if park == x.setpoint else park

    def adopt(self, running: bool) -> None:
        """Control was handed to the controller (Automatic selected, a restart, a pause ended):
        take the unit as it is. A run in progress is ridden instead of being stopped as a run
        nobody started, but without a minimum run: the next step ends it at once when the floor
        is already over its stop point."""
        if running and not self.run:
            self.run, self.t_state = True, self.p.min_run
        elif not running:
            # Nobody knows when the unit last stopped; allow a start as soon as the floor needs one.
            self.run, self.t_state = False, max(self.t_state, self.p.min_off)
        self.kick_min, self.q_f = 0.0, None

    # ------------------------------------------------------------------ inputs
    @staticmethod
    def _w(t: float) -> list:
        if t <= KNOTS[0]:
            return [(0, 1.0)]
        if t >= KNOTS[-1]:
            return [(len(KNOTS) - 1, 1.0)]
        i = 0
        while t > KNOTS[i + 1]:
            i += 1
        f = (t - KNOTS[i]) / (KNOTS[i + 1] - KNOTS[i])
        return [(i, 1.0 - f), (i + 1, f)]

    def _forecast(self, x: Inputs):
        fc = x.forecast
        self.forecast_state = "fresh"
        if fc and len(fc) >= 24:
            self.fc_last = fc
        elif self.fc_last is not None:
            fc = tuple(h for h in self.fc_last if h.minute > x.minute)
            self.forecast_state = "held"
        if not fc or len(fc) < max(self.p.lead1, 12):
            self.forecast_state = "none"
            return None
        return fc

    def _weather(self, x: Inputs, fc, dt: float):
        a = 1.0 / 1440.0
        if self.t_avg is None:
            self.t_avg = x.outdoor
        elif dt == 1.0:
            self.t_avg = self.t_avg + a * (x.outdoor - self.t_avg)
        else:
            self.t_avg = _mix(self.t_avg, x.outdoor, a, dt)
        if fc is None:
            return self.t_avg, 0.0, 0.0, 0.0
        hs = fc[self.p.lead0:self.p.lead1]
        t_fc = sum(h.outdoor for h in hs) / len(hs)
        ghi = sum((h.ghi or 0.0) for h in hs) / len(hs)
        n = min(len(fc), 24)
        warm = sum(h.outdoor for h in fc[:3]) / 3 - sum(h.outdoor for h in fc[:n]) / n
        return t_fc, ghi, warm, (fc[0].ghi or 0.0)

    def _slab(self, x: Inputs, dt: float) -> None:
        m = x.mode
        self.since_dhw = 0.0 if m == "dhw" else self.since_dhw + dt
        self.since_def = 0.0 if m in ("defrost", "other") else self.since_def + dt
        self.comp_prev = self.comp_min
        if x.compressor_on and m == "heat":
            self.comp_min += dt
        elif not x.compressor_on:
            self.comp_min = 0.0
        if not x.link_ok or self.since_dhw < 20 or self.since_def < 10:
            return
        if m == "heat" and x.compressor_on and self.comp_min >= 8:
            v = (x.inlet - (1.0 - self.eff) * (x.outlet + self.p.outlet_offset)) / self.eff
        elif m == "idle" and not x.compressor_on and self.t_state >= 15 and not self.run:
            v = x.inlet
        else:
            return
        self.ts = v if self.ts is None else _mix(self.ts, v, 0.2, dt)

    def _room_ok(self, x: Inputs) -> bool:
        if x.room is None or x.room_age_min >= self.p.stale_min:
            self.room_ref, self.frozen, self.room_f = None, False, None
            self.room_state = "missing" if x.room is None else "stale"
            return False
        if self.room_ref is None or abs(x.room - self.room_ref) >= 0.05:
            self.room_ref, self.room_since, self.frozen = x.room, x.minute, False
        elif self.p.frozen_h > 0 and x.minute - self.room_since >= self.p.frozen_h * 60:
            self.frozen = True
        self.room_state = "frozen" if self.frozen else "ok"
        return not self.frozen

    def _room(self, room: float, dt: float) -> float:
        """The room value the controller uses: as reported, but moving at most `room_slew` K a
        minute, so a one-report spike (a sensor next to the oven, a sunny-morning report) cannot
        swing the floor target by kp x the spike."""
        p = self.p
        if p.lab_hybrid or p.room_slew <= 0 or self.room_f is None:
            self.room_f = room
        else:
            lim = p.room_slew * dt
            self.room_f += min(max(room - self.room_f, -lim), lim)
        return self.room_f

    def _daily_at(self, hour: float) -> float:
        h = hour - 0.5
        i = int(math.floor(h)) % 24
        f = h - math.floor(h)
        return self.daily[i] * (1.0 - f) + self.daily[(i + 1) % 24] * f

    # ------------------------------------------------------------------ writes
    def unowned_24h(self) -> int:
        """Runs the unit started by itself that the controller had to stop, last 24 h. More
        than a couple a day suggests the restart hysteresis in use is larger than the unit's."""
        now = self.last_minute
        return 0 if now is None else sum(1 for m in self.unowned if now - m < 1440)

    def writes_24h(self, minute: float | None = None) -> int:
        now = minute if minute is not None else self.last_minute
        if now is None:
            return len(self.wlog)
        return sum(1 for m in self.wlog if now - m < 1440)

    def _write(self, x: Inputs, sp: float, critical: bool = True):
        sp = float(min(max(round(sp), self.p.write_min), self.p.write_max))
        self.want = sp
        if sp == x.setpoint:
            return None
        while self.wlog and x.minute - self.wlog[0] >= 1440:
            self.wlog.popleft()
        if len(self.wlog) >= self.p.hard_cap or (not critical and len(self.wlog) >= self.p.budget):
            self.note = "budget"
            return None
        if sp == self.last_sp and x.minute - self.last_write < 5:
            return None
        if x.act:
            self.last_sp, self.last_write = sp, x.minute
            self.wlog.append(x.minute)
        return sp

    def _stop(self, x: Inputs):
        self.stop_minute = x.minute
        sp = self.p.sp_floor
        if x.compressor_on:
            sp = min(sp, math.floor(x.outlet + self.p.outlet_offset + self.p.ctrl_offset - 2.1))
        return self._write(x, sp)

    def _park(self, x: Inputs, ts_star: float):
        """Idle setpoint: just under the unit's own restart point for the slab start threshold
        (outage fail-safe), never high enough to start the unit now, never under sp_floor -
        except that the restart point wins over a high Minimum water (production rule)."""
        p = self.p
        cap = math.floor(x.inlet + p.ctrl_offset + x.restart_delta - 0.6)
        want = math.floor(ts_star - p.band - 0.3 + x.restart_delta + p.ctrl_offset)
        if p.lab_hybrid:
            park = max(min(cap, want), p.sp_floor)
        else:
            park = max(min(max(want, p.sp_floor), cap), p.write_min)
        self.want = float(park)
        if park == x.setpoint:
            return None
        recent = x.minute - self.last_write < 120
        if park > x.setpoint >= p.sp_floor and park - x.setpoint < 2 and recent:
            return None
        if not p.lab_hybrid and park < x.setpoint <= cap and x.setpoint - park < 2 and recent:
            return None   # a small lowering waits too while the setpoint there cannot start the unit
        return self._write(x, park, critical=park < x.setpoint or x.setpoint < p.sp_floor)

    # ------------------------------------------------------------------ reporting
    def reason(self) -> str:
        """The last step in plain words. It is a sensor state, so it carries no values that
        change every minute; the floor estimate and target are their own sensors."""
        n = self.note
        if n == "values":
            return "Heat-pump or outdoor values unavailable; nothing written"
        if n == "link":
            return "Heat-pump link down; waiting with the last setpoint"
        if self.ts_star is None:
            return "Waiting for the first readings"
        text = {
            "start": "Starting a run: the floor is under its start point",
            "adopt": "The heat pump started a run itself while the floor needs heat; riding it",
            "unowned": "Stopping a run the floor does not need",
            "dhw": "Hot water has priority; the run continues after it",
            "defrost": "Defrost; the run continues after it",
            "other": "The heat pump reports an operating state that is not mapped; waiting",
            "off": "Space heating is off on the heat pump",
            "after_dhw": "Hot water just ended; letting the loop settle",
            "rest": "Resting for the minimum time before the next run; the floor is under its start point",
            "park": "Idle: the floor is warm enough; the next run starts when it cools to its start point",
            "warm": "Ending the run: the floor is over its stop point",
            "warm_wait": "The run ends after the defrost or hot water",
            "kick": "Starting the compressor with the lowest setpoint it restarts on",
            "kick_wait": "Waiting for the compressor to start",
            "ride_settle": "Run started; letting the output settle",
            "ride": "Running at a steady mid output until the floor passes its stop point",
            "budget": "Setpoint write budget for 24 h used; holding",
        }.get(n, "Following the floor")
        if self.room_state != "ok":
            text += {"missing": "; room temperature unavailable, using the learned outdoor curve",
                     "stale": "; room temperature stale, using the learned outdoor curve",
                     "frozen": "; room temperature unchanged for 12 h, using the learned outdoor curve"}[self.room_state]
        if self.forecast_state == "none":
            text += "; no forecast, using the day-mean outdoor temperature"
        return text

    def attributes(self) -> dict:
        """Diagnostics of the last step, rounded for display."""
        p = self.p
        r = lambda v, n=2: None if v is None else round(v, n)  # noqa: E731
        t_fc, ghi, warm, ghi_now = self.weather
        star = self.ts_star
        if star is not None and self.target is not None:
            # Shown within a physical range (a warm or sunny room can push the target itself far
            # down; nothing below room target - 2 changes a decision). target_parts are unclamped.
            star = min(max(star, self.target - 2.0), p.sp_ceil)
        return {
            "phase": self.phase,
            "reason": self.reason(),
            "slab_estimate": r(self.ts),
            "slab_target": r(star),
            "start_below": r(None if star is None else star - p.band),
            "stop_above": r(None if star is None else star + p.band),
            "target_parts": {k: round(v, 2) for k, v in self.parts.items()},
            "running": self.run,
            "minutes_in_phase": None if self.t_state >= 999 else round(self.t_state),
            "room_error": r(self.e),
            "room_sensor": self.room_state,
            "forecast": self.forecast_state,
            "forecast_outdoor_1_9h": r(t_fc, 1),
            "forecast_sun_1_9h_wm2": round(ghi),
            "sun_now_wm2": round(ghi_now),
            "warmer_next_3h": r(warm),
            "run_output_kw": r(self.q_now, 1) if self.phase == "ride" else None,
            "wanted_setpoint": self.want,
            "restart_hysteresis": self.restart_delta,
            "writes_24h": self.writes_24h(),
            "unowned_stops_24h": self.unowned_24h(),
            "learned_integral": r(self.integ),
            "daily_pattern": [round(v, 2) for v in self.daily],
            "fallback_curve": {f"{k:+.0f}": round(v, 2) for k, v in zip(KNOTS, self.fb)},
        }

    # ------------------------------------------------------------------ step
    def step(self, x: Inputs) -> Decision:
        if not _finite(x.outdoor, x.outlet, x.inlet, x.setpoint, x.restart_delta, x.minute):
            self.phase, self.note, self.want = "hold", "values", None
            return Decision(None, "hold", None)
        if x.room is not None and not _finite(x.room):
            x = replace(x, room=None)
        if self.last_minute is None and self.saved_minute is not None:
            # first step after a restore: an old floor estimate or day mean is not reused
            gap = x.minute - self.saved_minute
            if not 0 <= gap <= RUNTIME_MAX_AGE:
                self.ts = None
            if not 0 <= gap <= 360:
                self.t_avg = None
            self.saved_minute = None
        dt = 1.0 if self.last_minute is None else min(max(x.minute - self.last_minute, 0.0), MAX_STEP_MINUTES)
        prev_minute, self.last_minute, self.dt = self.last_minute, x.minute, dt
        self.restart_delta = x.restart_delta
        self.target = x.target
        p = self.p
        fc = self._forecast(x)
        t_fc, ghi, warm, ghi_now = self.weather = self._weather(x, fc, dt)
        self._slab(x, dt)
        self.t_state += dt

        e = 0.0
        if self._room_ok(x):
            e = x.target + p.aim - (self._room(x.room, dt) - p.glow * ghi_now)
            self.e = e
            if x.learn:
                el = e if p.lab_hybrid or p.learn_cap <= 0 else min(max(e, -p.learn_cap), p.learn_cap)
                self.integ = min(max(self.integ + p.ki * e / 60.0 * dt, -p.i_lim), p.i_lim)
                if p.d_g > 0:
                    k = int((x.local_hour - p.d_lead) % 24)
                    self.daily[k] = min(max(self.daily[k] + p.d_g * el / 60.0 * dt, -p.d_lim), p.d_lim)
                if p.tau_fb > 0:
                    for k, w in self._w(t_fc):
                        self.fb[k] += w * (self.integ - self.fb[k]) / (p.tau_fb * 60.0) * dt
            if x.shield and e < 0:
                e = 0.0
        else:
            self.e = None
            if x.learn:
                # room lost: the integral relaxes (6 h) to what it was in this weather when the room was known
                ref = sum(self.fb[k] * w for k, w in self._w(t_fc))
                self.integ += (ref - self.integ) / 360.0 * dt
        new_hour = (x.minute % 60 == 0) if prev_minute is None else (x.minute // 60 != prev_minute // 60)
        if x.learn and p.d_g > 0 and new_hour:
            mu = sum(self.daily) / 24.0
            f = 1.0 - 1.0 / (24.0 * p.d_leak)
            self.daily = [(c - mu) * f for c in self.daily]

        daily = self._daily_at(x.local_hour)
        ts_star = (x.target + p.b * (x.target - t_fc) + p.ts0 - p.s * ghi
                   + p.kp * e + self.integ + daily + p.kw * warm)
        self.ts_star = ts_star
        self.parts = {"target": x.target, "weather": p.b * (x.target - t_fc), "offset": p.ts0, "sun": -p.s * ghi,
                      "room": p.kp * e, "integral": self.integ, "daily": daily, "warm_hours": p.kw * warm}
        if not x.link_ok:
            self.phase, self.note, self.want = "hold", "link", None
            return Decision(None, "hold", None)
        ts = self.ts
        if ts is None:
            ts = x.inlet
            if not p.lab_hybrid and x.compressor_on and x.mode == "heat":
                # first step during a run (a restart): the return water overstates the floor
                ts = (x.inlet - (1.0 - self.eff) * (x.outlet + p.outlet_offset)) / self.eff
        self.want = x.setpoint
        sp = self._decide(x, ts, ts_star, t_fc)
        return Decision(sp, self.phase, self.want)

    def _decide(self, x: Inputs, ts: float, ts_star: float, t_fc: float):
        p = self.p
        kf = p.loop_kw_per_k
        q_min = kf * min(max(1.8 + 0.05 * t_fc, 1.4), 2.4)
        if not self.run:
            if ts < ts_star - p.band and self.t_state >= p.min_off and x.mode != "dhw":
                self.run, self.t_state, self.kick_min = True, 0.0, 0.0
                self.note = "start"
            elif x.compressor_on and x.mode == "heat" and self.comp_min <= 2 and (
                    ts < ts_star or (x.setpoint <= p.sp_floor and (p.lab_hybrid or (
                        ts < ts_star + p.band and x.minute - self.stop_minute >= 5)))):
                # The unit started by itself (an outage park doing its job, or a firmware start
                # while the floor needs heat): adopt it. Not right after the controller's own
                # stop, while the unit is still reporting the run it was told to end.
                self.run, self.t_state = True, 0.0
                self.note = "adopt"
            else:
                if x.compressor_on:
                    if x.mode == "heat" and self.since_def >= 3:
                        if self.note != "unowned" and x.minute - self.stop_minute >= 5:
                            self.unowned.append(x.minute)
                            while self.unowned and x.minute - self.unowned[0] >= 1440:
                                self.unowned.popleft()
                        self.phase, self.note = "stop", "unowned"
                        return self._stop(x)
                    self.phase, self.note = "wait", x.mode
                    return None
                self.phase = "idle"
                self.note = "rest" if ts < ts_star - p.band else "park"
                return self._park(x, ts_star)
        if ts > ts_star + p.band and self.t_state >= p.min_run:
            self.run, self.t_state = False, 0.0
            self.phase, self.note = "stop", "warm"
            if x.compressor_on and (x.mode != "heat" or self.since_def < 3):
                self.note = "warm_wait"
                return None
            return self._stop(x)
        if x.mode in ("dhw", "defrost", "off", "other") or self.since_dhw < 8:
            self.phase, self.note = "wait", x.mode if x.mode in ("dhw", "defrost", "off", "other") else "after_dhw"
            return None
        if not x.compressor_on:
            self.phase = "kick"
            prev = self.kick_min
            self.kick_min += self.dt
            self.q_f = None
            sp = math.ceil(x.inlet + p.ctrl_offset + x.restart_delta + 0.15) + min(int(self.kick_min // 6), 2)
            self.want = float(sp)
            if x.setpoint >= sp - 0.5 and int(self.kick_min // 6) == int(prev // 6):
                self.note = "kick_wait"
                return None
            self.note = "kick"
            return self._write(x, sp)
        self.kick_min = 0.0
        self.phase = "ride"
        if self.comp_min < 2:
            self.note = "ride_settle"
            return None
        deficit = max(0.0, ts_star - p.band - ts)
        q_raw = min(max(p.q_run, q_min) + p.kq * deficit, p.q_hi)
        self.q_f = q_raw if self.q_f is None else _near(self.q_f, q_raw, 30.0, self.dt)
        q = self.q_now = self.q_f
        sp = x.inlet + q / kf + p.ctrl_offset - 0.025 * (q - 5.0) + 0.55
        t_ctrl = x.outlet + p.outlet_offset + p.ctrl_offset
        sp = min(max(sp, math.ceil(t_ctrl - 1.5), p.sp_floor), p.sp_ceil)
        self.want = float(round(sp))
        self.note = "ride"
        first = self.comp_prev < 2 <= self.comp_min
        if x.minute - self.last_write >= p.ride_every or first:
            if abs(sp - x.setpoint) >= p.ride_hyst and round(sp) != x.setpoint:
                return self._write(x, sp, critical=first)
        return None
