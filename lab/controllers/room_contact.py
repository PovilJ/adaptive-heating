"""Room-thermostat on/off with low water (strategy S7), stdlib only.

See docs/research/lab/controllers/room_contact.md.

The room decides WHEN the heat pump runs, the water side decides HOW:

- a call for heat starts when the room, projected `look_h` hours ahead with its observed slope,
  falls below the switching centre minus `h_dn`, and ends when the projection rises above the
  centre plus `h_up` (minimum on and off times keep runs long and starts few);
- the projection also adds the forecast sun of the next `sun_h` hours (`k_sun` K per kWh/m2 of
  global irradiation): a call is not started, or is ended earlier, when the sun is about to heat
  the house anyway;
- during a call the leaving-water setpoint follows a fixed weather curve (about 29 degC at
  +7 degC outdoor, 31.3 at 0, 34.6 at -10), never lower than a "ride floor" 0.8 K under the
  control sensor, so the firmware never stops a call's run on its own (stop rule: control
  sensor >= setpoint + 2 K). The curve sets the output (about 5-6 kW in mild weather, the
  unit's best part-load COP in the model) and so the water temperature;
- the compressor is started on a call with one setpoint write that opens the firmware's start gap
  (setpoint - control sensor >= restart_delta) and stopped at the end of the call with one write
  to 25 degC (control sensor >= setpoint + 2 K stops it at once). Space heating stays enabled the
  whole time, so the circulation pump keeps running as it does on the real unit;
- one slow integrator adapts the switching centre so that the long-run mean room sits on target;
  a warm room long after the last call (sun, occupants) counts only half (anti-windup).

Fail-safe: with no room reading for `stale_min` minutes the controller falls back to a learned
weather curve (the continuous-equivalent water the house needed while the room was known, plus an
offset, minus a forecast-sun term) with the firmware's own restart hysteresis; while the Modbus
link is down it writes nothing; during hot water, defrost and the 15 minutes after them it writes
only the end of a call.

Review fixes (docs section 9): no cold park into a warm room and no min_on lock on a parked start
(R1); a learned ceiling on the call setpoint (R2); learned, sun-aware no-room fallback (R4);
owner's heating switch respected, restart_delta not forced (R7).

Review round 2 (docs section 10): the call setpoint ceiling is need + 3.5 K at T_eff <= 0 degC
(need + 5 K at >= +5), so the register a lost link freezes mid-call is one the house can take
continuously (I1); the 10 K restart_delta of round 1 is off by default (`call_delta` = 0), so
only the 5 K value ever used on the real unit is written (I4); the cold park steps down to 27 degC
just before the water would restart the compressor into a room that does not need heat (I3, I8);
None/NaN unit sensors are replaced by their last good value (I7).
"""
from __future__ import annotations

from lab.sim.interface import Command, Observation

# sensor offsets of the Versati (UNIT_MODEL.md section 2): the firmware's control sensor reads
# about 0.7 K below the inlet sensor while idle and about 0.5 K below the outlet while running
CTRL_IDLE = -0.7
CTRL_RUN = -0.5
SP_LOW = 25.0     # lowest setpoint ever written to the real unit (no assumption flag)
SP_HIGH = 39.0    # highest setpoint ever written to the real unit


def _f(params, key, default):
    return float(params.get(key, default))


class RoomContact:
    name = "room_contact"

    def reset(self, params: dict) -> None:
        p = params
        # room call
        self.h_dn = _f(p, "h_dn", 0.25)          # call below centre - h_dn (projected room)
        self.h_up = _f(p, "h_up", 0.25)          # end above centre + h_up (projected room)
        self.look_h = _f(p, "look_h", 2.0)       # projection horizon, h
        self.slope_win = int(_f(p, "slope_win", 120))  # minutes of room history for the slope
        self.slope_cap = _f(p, "slope_cap", 0.4)       # K/h
        self.k_sun = _f(p, "k_sun", 0.6)         # K of projected room per kWh/m2 of forecast sun
        self.sun_h = _f(p, "sun_h", 10.0)         # hours of forecast sun counted
        self.min_on = int(_f(p, "min_on", 90))
        self.min_off = int(_f(p, "min_off", 60))
        self.min_run = int(_f(p, "min_run", 30))  # a (re)started compressor runs at least this long
        self.ki_bias = _f(p, "ki_bias", 0.02)    # K of centre per K-hour of room error
        self.bias_lim = _f(p, "bias_lim", 1.5)
        self.aw_min = int(_f(p, "aw_min", 480))   # minutes after a call during which a warm room counts in full
        self.w_unctl = _f(p, "w_unctl", 0.5)     # weight of a warm room later than that
        # water
        self.curve_slope = _f(p, "curve_slope", 0.33)  # K of water per K of (22 - outdoor)
        self.curve_base = _f(p, "curve_base", 24.0)    # water at 22 degC outdoor
        self.ride_gap = _f(p, "ride_gap", 1.6)   # raise the ride floor when t_ctrl - sp reaches this
        self.ride_to = _f(p, "ride_to", 0.8)     # new ride floor = t_ctrl - ride_to
        self.delta = _f(p, "delta", 5.0)         # restart hysteresis register (4-5 K were used)
        self.stale_min = int(_f(p, "stale_min", 360))  # no room report for this long -> fail-safe curve
        self.park = _f(p, "park", 26.0)          # idle setpoint between calls (0: stay at 25)
        self.park_after = int(_f(p, "park_after", 10))  # minutes after a stop before parking
        self.park_cold = _f(p, "park_cold", 28.0)       # idle setpoint in cold weather, room not warm (review R1)
        self.park_cold_below = _f(p, "park_cold_below", -5.0)  # degC of T_eff
        self.park_hold = int(_f(p, "park_hold", 60))    # minutes a park choice is held
        self.park_warm = _f(p, "park_warm", 0.6)        # no cold park while room >= centre + this
        self.park_pre = _f(p, "park_pre", 1.0)          # K before a cold-park restart (0: off)
        self.park_pre_k = _f(p, "park_pre_k", 0.5)      # ... only while the projection is this far above the centre
        self.park_pre_to = _f(p, "park_pre_to", 27.0)   # park after that step (0: the mild park)
        self.park_run = int(_f(p, "park_run", 60))      # minimum run of a parked start into a warm room
        # review R2: never write a call setpoint above what the house could take continuously
        # (learned need + cap_margin), so a link lost in the middle of a call cannot hold a hot
        # setpoint for days
        self.cap_margin = _f(p, "cap_margin", 5.0)
        # review round 2 (I1): where the house can absorb the unit's minimum output (cold weather),
        # a run on a frozen setpoint never stops by itself, so the call setpoint must stay close to
        # the need: ceiling need + cap_cold at T_eff <= cc_lo, need + cap_margin at T_eff >= cc_hi
        self.cap_cold = _f(p, "cap_cold", 3.5)
        self.cc_lo = _f(p, "cc_lo", 0.0)
        self.cap_warm = _f(p, "cap_warm", 0.0)        # ceiling need + this while the room >= centre + cap_warm_at (0: off)
        self.cap_warm_at = _f(p, "cap_warm_at", 0.0)
        self.cc_hi = _f(p, "cc_hi", 5.0)
        self.call_delta = _f(p, "call_delta", 0.0)    # restart_delta while a call runs (0: off; round 2)
        self.cd_at = int(_f(p, "cd_at", 0))           # run minute at which call_delta is written
        self.kick_over = _f(p, "kick_over", 99.0)   # K a start kick may exceed the cap (99: no limit)
        self.cap_pause = int(_f(p, "cap_pause", 60))   # minutes before a re-kick after a stop at the cap
        # review R4: learned continuous-equivalent water (mean of outlet and inlet over all
        # non-tank minutes) = target + s_need x (22 - outdoor); used by the no-room fallback
        self.s_need = _f(p, "s_need0", 0.27)
        self.s_gain = _f(p, "s_gain", 0.3)        # EWMA weight of one day's estimate
        self.fb_off = _f(p, "fb_off", 1.7)        # fallback setpoint above the needed mean water
        self.fb_sun = _f(p, "fb_sun", 3.0)        # K of fallback setpoint per kWh/m2 of forecast sun
        # review round 2 (I3): start budget; with st_budget starts in the last 24 h the minimum off
        # time grows to min_off_b (0: off)
        self.st_budget = int(_f(p, "st_budget", 0))
        self.min_off_b = int(_f(p, "min_off_b", 150))
        self.renew_kick = int(_f(p, "renew_kick", 4))   # minutes before a kick that did not start is redone
        self.natural_ends = int(_f(p, "natural_ends", 1))  # a firmware stop ends the call unless still cold
        # state
        self.call = True
        self.since = 10_000
        self.bias = 0.0
        self.t_avg = None
        self.hist = []
        self.last_busy = -10_000      # last minute of DHW or defrost
        self.kick_at = -10_000
        self.was_on = False
        self.run_start = -10_000
        self.was_on_run = False
        self.stop_at = -10_000
        self.stop_mode_heat = False
        self.park_val = None
        self.park_at = -10_000
        self._cap_last = SP_HIGH
        self.starts = []
        self.delta_set = False        # restart_delta written once (review R7)
        self.acc = [0, 0.0, 0.0]      # minutes, water sum, outdoor sum (need learning)
        self._good = {"outdoor": 0.0, "outlet": 25.0, "inlet": 25.0, "setpoint": SP_LOW, "restart_delta": 5.0}
        self._seen = set()

    def _clean(self, obs):
        """Review round 2 (I7): an unavailable sensor (None/NaN in Home Assistant) is replaced by its
        last good value (outdoor: the forecast's first hour if never seen); returns (obs, all_ok)."""
        fix = {}
        for k in self._good:
            v = getattr(obs, k)
            try:
                v = float(v)
                ok = v == v and abs(v) < 1e6
            except (TypeError, ValueError):
                ok = False
            if ok:
                self._good[k] = v
                self._seen.add(k)
            else:
                if k == "outdoor" and k not in self._seen:
                    try:
                        self._good[k] = float(obs.forecast[0]["outdoor"])
                    except (TypeError, ValueError, KeyError, IndexError, AttributeError):
                        pass
                fix[k] = self._good[k]
        room = obs.room
        try:
            if room is not None and not (float(room) == float(room)):
                fix["room"] = None
        except (TypeError, ValueError):
            fix["room"] = None
        if not fix:
            return obs, True
        import dataclasses
        return dataclasses.replace(obs, **fix), False

    # ------------------------------------------------------------------
    def _t_eff(self, obs):
        a = 1.0 / (12 * 60)
        self.t_avg = obs.outdoor if self.t_avg is None else self.t_avg + a * (obs.outdoor - self.t_avg)
        fc = obs.forecast or ()
        try:
            if len(fc) >= 6:
                t_fc = sum(float(h["outdoor"]) for h in fc[:6]) / 6
                return 0.5 * self.t_avg + 0.5 * t_fc
        except (KeyError, TypeError, ValueError):
            pass
        return self.t_avg

    def _sun_kwh(self, obs):
        """Forecast global irradiation over the next `sun_h` hours, kWh/m2 (0 without a forecast)."""
        if not self.k_sun:
            return 0.0
        tot = 0.0
        try:
            for h in (obs.forecast or ())[: int(self.sun_h)]:
                tot += max(float(h.get("ghi") or 0.0), 0.0) / 1000.0
        except (TypeError, ValueError, AttributeError):
            return 0.0
        return tot

    def _slope(self):
        h = self.hist
        if len(h) < 6:
            return 0.0
        n = len(h)
        mx = sum(m for m, _ in h) / n
        my = sum(r for _, r in h) / n
        sxx = sum((m - mx) ** 2 for m, _ in h)
        sxy = sum((m - mx) * (r - my) for m, r in h)
        return 60.0 * sxy / sxx if sxx > 0 else 0.0   # K/h

    def need_water(self, target, t_eff):
        """Continuous-equivalent mean water the house needs at this outdoor temperature (learned)."""
        return target + self.s_need * max(22.0 - t_eff, 0.0)

    def _learn(self, obs, room_ok):
        """Daily estimate of s_need from the mean water while the room is on target (review R4)."""
        if not room_ok or obs.mode in ("dhw", "defrost") or obs.minute - self.last_busy < 15:
            return
        a = self.acc
        a[0] += 1
        a[1] += 0.5 * (obs.outlet + obs.inlet)
        a[2] += obs.outdoor
        if a[0] >= 1440:
            w, t = a[1] / a[0], a[2] / a[0]
            if 22.0 - t >= 8.0:
                est = (w - obs.target) / (22.0 - t)
                self.s_need += self.s_gain * (min(max(est, 0.1), 0.6) - self.s_need)
            self.acc = [0, 0.0, 0.0]

    def curve(self, t_eff):
        return self.curve_base + self.curve_slope * (22.0 - t_eff)

    # ------------------------------------------------------------------
    def step(self, obs: Observation) -> Command:
        obs, sensors_ok = self._clean(obs)
        t_eff = self._t_eff(obs)
        m = obs.minute
        if obs.mode in ("dhw", "defrost"):
            self.last_busy = m
        try:
            age = float(obs.room_age_min)
        except (TypeError, ValueError):
            age = 1e9
        room_ok = obs.room is not None and age <= self.stale_min
        if room_ok:
            if m % 5 == 0:
                self.hist.append((m, obs.room))
                while self.hist and self.hist[0][0] < m - self.slope_win:
                    self.hist.pop(0)
            err = obs.target - obs.room
            # anti-windup: a room that is warm long after the last call (sun, gains) is not the
            # controller's doing, so it does not move the switching centre
            w = 1.0 if (err >= 0 or self.call or self.since <= self.aw_min) else self.w_unctl
            self.bias = min(max(self.bias + w * self.ki_bias * err / 60.0, -self.bias_lim), self.bias_lim)
        else:
            self.hist.clear()
        self.since += 1
        if not obs.link_ok:
            return Command()
        if sensors_ok:
            self._learn(obs, room_ok)
        if not obs.heating_enabled:
            # review R7: space heating switched off by the owner (summer, service): pause, write nothing
            self.call, self.since = False, 0
            return Command()

        cmd = {}
        want_delta = None
        if not self.delta_set:                  # restart_delta is set once; afterwards only the
            want_delta = self.delta             # controller's own call_delta is undone (review R7)
            self.delta_set = True
        delta = self.delta
        need = self.need_water(obs.target, t_eff)
        x = min(max((t_eff - self.cc_lo) / max(self.cc_hi - self.cc_lo, 0.1), 0.0), 1.0)
        margin = self.cap_cold + x * (self.cap_margin - self.cap_cold)
        cap = min(max(need + margin, SP_LOW), SP_HIGH)
        self._cap_last = float(int(cap))
        curve = min(max(self.curve(t_eff), SP_LOW), cap)

        if not room_ok:                         # fail-safe: learned need curve, firmware cycles
            self.call = True
            fb = need + self.fb_off - self.fb_sun * self._sun_kwh(obs)
            sp = float(round(min(max(fb, SP_LOW), SP_HIGH)))
            if obs.mode not in ("dhw", "defrost") and sp != obs.setpoint:
                cmd["setpoint"] = sp
            if obs.restart_delta == self.call_delta != self.delta:
                cmd["restart_delta"] = self.delta
            return Command(**cmd)

        busy = obs.mode in ("dhw", "defrost") or m - self.last_busy < 15
        slope = min(max(self._slope(), -self.slope_cap), self.slope_cap)
        pred = obs.room + slope * self.look_h + self.k_sun * self._sun_kwh(obs)
        centre = obs.target + self.bias
        if self.cap_warm and obs.room >= centre + self.cap_warm_at:
            # review round 2 (I1): once the room is back at the centre the call is nearly done; a
            # lower ceiling now costs little and bounds what a register frozen now would do
            cap = min(cap, max(need + self.cap_warm, SP_LOW))
            self._cap_last = float(int(cap))

        # a firmware stop (surge, defrost end) during a call: end the call unless still cold
        if self.was_on and not obs.compressor_on and not busy and self.call and self.natural_ends:
            if pred >= centre and self.since >= self.min_on // 2:
                self.call, self.since = False, 0
        self.was_on = obs.compressor_on

        if obs.compressor_on and not self.was_on_run:
            self.run_start = m
            if obs.mode == "heat":
                self.starts.append(m)
            # the firmware started on its own from the parked setpoint (the water has cooled to
            # the backstop): accept it as a call; if the room does not need heat, it ends after
            # min_run (no min_on lock, review R1)
            if not self.call and self.park and obs.mode == "heat" and obs.setpoint >= min(self.park, self.park_cold):
                self.call = True
                self.since = 0 if pred < centre else max(self.min_on - self.park_run, 0)
        elif self.was_on_run and not obs.compressor_on:
            self.stop_at = m
            # a stop at the setpoint cap (the house would not take more water): pause before a re-kick
            self.stop_mode_heat = (obs.mode not in ("dhw", "defrost") and m - self.last_busy >= 15
                                   and obs.setpoint >= self._cap_last - 0.5)
        self.was_on_run = obs.compressor_on
        # a run that was just kicked or just started is not cut short (a begun pre-start runs
        # the compressor's minimum run anyway)
        run_young = (obs.compressor_on and m - self.run_start < self.min_run) or m - self.kick_at < 10
        while self.starts and self.starts[0] <= m - 1440:
            self.starts.pop(0)
        min_off = self.min_off
        if self.st_budget and len(self.starts) >= self.st_budget:
            min_off = max(min_off, self.min_off_b)
        if self.call and self.since >= self.min_on and not run_young and pred >= centre + self.h_up:
            self.call, self.since = False, 0
        elif not self.call and self.since >= min_off and pred <= centre - self.h_dn:
            self.call, self.since = True, 0

        sp = obs.setpoint
        if not self.call:
            # stop at once (also during hot water: no firmware restart after it); once the
            # compressor has been off a while, park the setpoint where the firmware restarts by
            # itself only if the water falls to about room + 1 K: a backstop for a lost link
            if self.park and not obs.compressor_on and m - self.stop_at >= self.park_after:
                # the warmer cold-weather backstop only while the room does not project warm, so
                # it cannot start the compressor into a sun-warmed room (review R1); the choice is
                # held for park_hold minutes to save writes
                if m - self.park_at >= self.park_hold or self.park_val is None:
                    cold = t_eff < self.park_cold_below and obs.room < centre + self.park_warm
                    self.park_val = self.park_cold if cold else self.park
                    self.park_at = m
                # review round 2 (I8): the water is about to fall to the cold park's restart point
                # while the room does not need heat: step down to the mild park before the
                # firmware starts a run nobody asked for
                if (self.park_pre and self.park_val == self.park_cold > (self.park_pre_to or self.park) and pred >= centre + self.park_pre_k
                        and obs.inlet + CTRL_IDLE <= self.park_cold - obs.restart_delta + self.park_pre):
                    self.park_val = self.park_pre_to or self.park
                    self.park_at = m
                sp = self.park_val
            else:
                sp = SP_LOW
                self.park_val = None
            if self.call_delta and obs.restart_delta == self.call_delta:
                want_delta = self.delta
        elif busy:
            pass                                # sensors show tank water or a defrost: hold
        else:
            if obs.compressor_on:
                # setpoint = the curve, but never so far below the control sensor that the
                # firmware stops the run (t_ctrl >= setpoint + 2 K): the "ride floor"
                t_ctrl = obs.outlet + CTRL_RUN
                target_sp = float(round(curve))
                floor_ = float(round(t_ctrl - self.ride_to))
                cur = obs.setpoint
                if t_ctrl - cur >= self.ride_gap or cur >= max(target_sp, floor_) + 1.0:
                    sp = max(target_sp, floor_)
                else:
                    sp = max(cur, target_sp)
                # the cap: above it the firmware ends the run itself (a natural end)
                sp = min(sp, float(int(cap)), SP_HIGH)
                # review R2: once the run is established, widen the restart hysteresis, so that a
                # link lost now cannot make the firmware restart on the hot call setpoint for days:
                # after its next stop it restarts only when the water has fallen call_delta K
                if self.call_delta and obs.mode == "heat" and m - self.run_start >= self.cd_at:
                    want_delta = self.call_delta
            elif self.stop_mode_heat and m - self.stop_at < self.cap_pause:
                pass                            # the firmware stopped a call's run at the cap: pause
            elif m - self.kick_at >= self.renew_kick or obs.setpoint < obs.inlet + CTRL_IDLE + delta:
                t_ctrl = obs.inlet + CTRL_IDLE
                kick = float(int(t_ctrl + delta + 0.4 + 0.999))
                sp = min(max(kick, float(round(curve))), SP_HIGH)
                if kick > float(int(cap)) + self.kick_over:
                    sp = obs.setpoint            # water still warm: a kick would exceed the cap, wait
                elif sp != obs.setpoint:
                    self.kick_at = m
                if self.call_delta and obs.restart_delta == self.call_delta:
                    want_delta = self.delta
        if sp != obs.setpoint:
            cmd["setpoint"] = sp
        if want_delta is not None and want_delta != obs.restart_delta:
            cmd["restart_delta"] = want_delta
        return Command(**cmd)


CONTROLLER = RoomContact


if __name__ == "__main__":
    from datetime import datetime, timezone

    def ob(**kw):
        base = dict(time=datetime(2026, 1, 1, tzinfo=timezone.utc), local_hour=2.0, room=21.6,
                    room_age_min=10, outdoor=5.0, outlet=26.0, inlet=26.3, setpoint=25.0,
                    restart_delta=5.0, quiet=False, heating_enabled=True, compressor_on=False,
                    mode="idle", electric_kw=0.0, energy_kwh=0.0, target=22.0, forecast=(),
                    pv_kw=None, minute=0, link_ok=True)
        base.update(kw)
        return Observation(**base)

    c = RoomContact()
    c.reset({})
    cmd = c.step(ob())
    assert cmd.setpoint is not None and cmd.setpoint - (26.3 - 0.7) >= 5.0, cmd   # cold room: kick
    cmd = c.step(ob(minute=1, link_ok=False, room=None))
    assert cmd == Command()                                                         # link down: nothing
    c2 = RoomContact()
    c2.reset({})
    c2.call, c2.since = True, 500
    c2.was_on_run, c2.run_start = True, -500
    cmd = c2.step(ob(room=22.6, compressor_on=True, mode="heat", outlet=30.0, inlet=28.0, setpoint=30.0))
    assert cmd.setpoint == SP_LOW, cmd                                              # warm room: stop
    c3 = RoomContact()
    c3.reset({})
    c3.call, c3.since, c3.stop_at = False, 30, -30
    cmd = c3.step(ob(room=22.4, setpoint=25.0, outlet=27.0, inlet=27.3))
    assert cmd.setpoint == 26.0, cmd                                                # parked backstop
    cmd = c2.step(ob(minute=2, room=None, setpoint=25.0))
    assert cmd.setpoint is not None and cmd.setpoint >= 25.0                        # no room: curve
    cmd = c2.step(ob(minute=3, mode="dhw", room=21.0, setpoint=25.0))
    assert cmd.setpoint is None                                                     # no writes in DHW
    c4 = RoomContact()
    c4.reset({})
    c4.call, c4.since, c4.delta_set = True, 10, True
    c4.was_on_run, c4.run_start = True, -30
    cmd = c4.step(ob(room=21.0, compressor_on=True, mode="heat", outlet=38.0, inlet=33.0, setpoint=38.0,
                     outdoor=-10.0))
    need = c4.need_water(22.0, c4.t_avg)
    assert cmd.setpoint is not None and cmd.setpoint <= need + 3.5, (cmd, need)    # cold-weather cap (round 2)
    cmd = c4.step(ob(minute=1, heating_enabled=False))
    assert cmd == Command()                                                         # owner switched heating off
    c5 = RoomContact()
    c5.reset({})
    c5.step(ob(outdoor=float("nan"), forecast=({"outdoor": 3.0},)))
    c5.step(ob(minute=1, outdoor=None, outlet=None, inlet=float("nan"), room=float("nan")))
    assert c5.t_avg == c5.t_avg                                                     # unavailable sensors (round 2)
    print("room_contact self-check ok")
