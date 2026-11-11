"""The slab controller core (slab.py): start, ride and stop decisions, fail-safes, the write
budget, persistence and the sun estimate. Pure Python, no Home Assistant."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import random
import sys
import unittest

from common import ROOT, module

slab = module("slab")
Inputs, Hour, Params = slab.Inputs, slab.Hour, slab.Params


def hours(start_minute, outdoor=0.0, ghi=0.0, n=48):
    """A flat forecast whose first row is the hour now running."""
    first = (start_minute // 60 + 1) * 60
    return tuple(Hour(first + 60 * i, outdoor, ghi) for i in range(n))


def idle(minute=0.0, **kw):
    base = dict(minute=minute, local_hour=(minute / 60) % 24, target=22.0, outdoor=0.0, outlet=24.0, inlet=24.3,
                setpoint=25.0, restart_delta=5.0, compressor_on=False, mode="idle", room=21.5, room_age_min=5.0,
                forecast=hours(minute))
    base.update(kw)
    return Inputs(**base)


def running(minute, **kw):
    return idle(minute, **{"compressor_on": True, "mode": "heat", "outlet": 30.0, "inlet": 27.0, **kw})


class StartRideStop(unittest.TestCase):
    def test_cold_floor_kicks_with_the_smallest_restart_setpoint(self):
        c = slab.SlabController()
        d = c.step(idle())
        self.assertEqual(d.phase, "kick")
        # ceil(return 24.3 - 0.8 + hysteresis 5 + 0.15) = 29: the unit starts at setpoint - control >= 5
        self.assertEqual(d.setpoint, 29.0)
        self.assertTrue(c.run)

    def test_kick_rises_one_degree_every_six_minutes_at_most_twice(self):
        c = slab.SlabController()
        written = []
        for m in range(30):
            d = c.step(idle(m, setpoint=written[-1] if written else 25.0))
            if d.setpoint is not None:
                written.append(d.setpoint)
        self.assertEqual(written, [29.0, 30.0, 31.0])

    def test_kick_setpoint_does_not_chase_warming_loop_water(self):
        c = slab.SlabController()
        d = c.step(idle(0, inlet=27.2, outlet=28.0))
        self.assertEqual(d.setpoint, 32.0)  # ceil(27.2 - 0.8 + 5 + 0.15), the test unit has a 5 K restart delta
        for m in range(1, 5):  # the unit sits out its restart pause while the loop warms
            self.assertIsNone(c.step(idle(m, inlet=27.2 + 0.15 * m, outlet=28.0, setpoint=32.0)).setpoint)

    def test_ride_holds_mid_output_inside_the_dead_band(self):
        c = slab.SlabController()
        c.step(idle(0))
        c.step(running(1, setpoint=29.0))
        d = c.step(running(2, setpoint=29.0))  # second running minute: the first ride write
        deficit = max(0.0, c.ts_star - 1.4 - c.ts)  # a floor behind its target asks for more output
        q = min(max(6.5, 2.02 * min(max(1.8, 1.4), 2.4)) + 2.0 * deficit, 9.0)
        expected = round(27.0 + q / 2.02 - 0.8 - 0.025 * (q - 5) + 0.55)
        self.assertEqual(d.phase, "ride")
        self.assertEqual(d.setpoint, float(expected))
        # no rewrite within the next eight minutes, and only for a 1.3 K move after that
        self.assertIsNone(c.step(running(3, setpoint=d.setpoint, inlet=27.5)).setpoint)
        self.assertIsNone(c.step(running(12, setpoint=d.setpoint, inlet=27.6)).setpoint)

    def test_warm_floor_ends_the_run_with_one_write_after_the_minimum_run(self):
        c = slab.SlabController()
        c.step(idle(0))
        warm = dict(setpoint=34.0, inlet=33.0, outlet=36.0, room=22.5)  # the floor is now far over target
        for m in range(1, 59):
            c.step(running(m, **warm))
        self.assertTrue(c.run, "no stop inside the 60-minute minimum run")
        self.assertGreater(c.ts, c.ts_star + 1.4)
        stops = [c.step(running(m, **warm)) for m in range(59, 63)]
        stop = next(d for d in stops if d.setpoint is not None)
        self.assertEqual(stop.phase, "stop")
        # the stop writes the idle park itself, at least 2.1 K under the control sensor: the unit
        # stops at once and the next idle minute has nothing to rewrite
        self.assertLessEqual(stop.setpoint, 36.0 + 0.3 - 0.8 - 2.1)
        self.assertFalse(c.run)
        after = c.step(idle(63, setpoint=stop.setpoint, inlet=33.0, outlet=33.2, room=22.5))
        self.assertEqual(after.phase, "idle")
        self.assertEqual(after.want, stop.setpoint)
        self.assertIsNone(after.setpoint)

    def test_ride_lifts_the_setpoint_before_the_firmware_stops_the_run(self):
        c = slab.SlabController()
        c.step(idle(0))
        sp = 29.0
        for m in range(1, 30):
            d = c.step(running(m, setpoint=sp, inlet=27.0, outlet=30.0))
            sp = d.setpoint or sp
        sp = 29.0
        c.last_write, c.last_sp = 29.0, 29.0  # a write of 29 a minute ago: ride spacing and hysteresis would hold
        # control = outlet + 0.3 - 0.8; the firmware stops at control >= setpoint + 2 K
        self.assertIsNone(c.step(running(30, setpoint=sp, inlet=27.1, outlet=30.9)).setpoint)  # control 30.4
        d = c.step(running(31, setpoint=sp, inlet=27.1, outlet=31.2))                          # control 30.7
        self.assertEqual(d.phase, "ride")
        self.assertGreaterEqual(d.setpoint, 30.0)

    def test_rest_time_before_the_next_start(self):
        c = slab.SlabController()
        c.run, c.t_state, c.ts = False, 0.0, 20.0  # just stopped, floor already cold again
        phases = [c.step(idle(m, inlet=20.0, outlet=19.7)).phase for m in range(1, 50)]
        self.assertEqual(phases[:40], ["idle"] * 40)
        self.assertIn("kick", phases[43:])

    def test_parked_setpoint_never_reaches_the_restart_point(self):
        c = slab.SlabController()
        c.ts, c.t_state = 30.0, 999.0  # warm floor: no start wanted
        for inlet in (25.0, 28.0, 31.0):
            d = c.step(idle(c.last_minute + 1 if c.last_minute is not None else 0, inlet=inlet, outlet=inlet - 0.3,
                            room=22.5, setpoint=25.0))
            self.assertEqual(d.phase, "idle")
            want = d.want
            self.assertLess(want - (inlet - 0.8), 5.0, "a parked setpoint must not start the unit")
            self.assertGreaterEqual(want, 25.0)

    def test_a_start_the_unit_made_itself_is_adopted_when_heat_is_wanted(self):
        c = slab.SlabController()
        c.t_state, c.ts = 10.0, 25.0  # inside the rest time, floor under target
        c.step(idle(0, inlet=25.0))
        d = c.step(running(1, inlet=25.0, outlet=29.0, setpoint=30.0))
        self.assertTrue(c.run)
        self.assertEqual(d.phase, "ride")

    def test_a_run_nobody_wants_is_stopped(self):
        c = slab.SlabController()
        c.ts, c.t_state, c.comp_min = 32.0, 999.0, 30.0
        d = c.step(running(0, inlet=31.0, outlet=34.0, setpoint=36.0, room=22.6))
        self.assertEqual((d.phase, c.note), ("stop", "unowned"))
        self.assertIsNotNone(d.setpoint)


class FailSafes(unittest.TestCase):
    def test_no_writes_while_the_link_is_down_or_values_are_missing(self):
        c = slab.SlabController()
        self.assertEqual(c.step(idle(0, link_ok=False)), slab.Decision(None, "hold", None))
        self.assertEqual(c.step(idle(1, inlet=math.nan)).setpoint, None)
        self.assertEqual(c.note, "values")

    def test_hot_water_freezes_the_floor_estimate_and_pauses_the_run(self):
        c = slab.SlabController()
        c.step(idle(0))
        before = c.ts
        for m in range(1, 15):
            d = c.step(idle(m, mode="dhw", compressor_on=True, inlet=46.0, outlet=50.0, setpoint=29.0))
            self.assertIsNone(d.setpoint)
            self.assertEqual(d.phase, "wait")
        self.assertEqual(c.ts, before)
        for m in range(15, 30):  # 20 minutes after hot water the loop is still tank water
            c.step(idle(m, inlet=40.0, outlet=39.7, setpoint=29.0))
        self.assertEqual(c.ts, before)

    def test_a_stop_waits_out_a_defrost(self):
        c = slab.SlabController()
        c.run, c.t_state, c.ts, c.comp_min = True, 100.0, 35.0, 50.0
        d = c.step(running(0, mode="defrost", inlet=31.0, outlet=29.0, setpoint=30.0, room=22.8))
        self.assertIsNone(d.setpoint)
        self.assertEqual(c.note, "warm_wait")

    def test_room_lost_stops_learning_and_relaxes_to_the_fallback_curve(self):
        c = slab.SlabController()
        c.fb = [2.0] * len(slab.KNOTS)
        c.integ = -1.0
        for m in range(360):
            c.step(idle(m, room=None))
        self.assertEqual(c.room_state, "missing")
        self.assertGreater(c.integ, 0.0)  # moved most of the way toward the fallback value 2
        self.assertIn("learned outdoor curve", c.reason())
        c2 = slab.SlabController()
        c2.step(idle(0, room=21.0, room_age_min=300))
        self.assertEqual(c2.room_state, "stale")

    def test_a_frozen_room_value_stops_learning_after_twelve_hours(self):
        c = slab.SlabController()
        for m in range(13 * 60):
            c.step(idle(m, room=23.0, inlet=27.0, outlet=26.7))
        self.assertEqual(c.room_state, "frozen")
        c.fb = [c.integ] * len(slab.KNOTS)
        before = c.integ
        c.step(idle(13 * 60, room=23.0, inlet=27.0, outlet=26.7))
        self.assertAlmostEqual(c.integ, before, places=6)

    def test_missing_forecast_uses_the_last_one_then_the_day_mean(self):
        c = slab.SlabController()
        c.step(idle(0, forecast=hours(0, outdoor=-10.0)))
        c.step(idle(1, forecast=()))
        self.assertEqual(c.forecast_state, "held")
        self.assertAlmostEqual(c.weather[0], -10.0)
        c.step(idle(40 * 60, forecast=()))  # the held forecast has fewer than 12 hours left
        self.assertEqual(c.forecast_state, "none")
        self.assertIn("no forecast", c.reason())

    def test_forecast_sun_lowers_the_floor_target(self):
        c, sunny = slab.SlabController(), slab.SlabController()
        c.step(idle(0, room=22.0))
        sunny.step(idle(0, room=22.0, forecast=hours(0, ghi=300.0)))
        # 0.03 K per W/m2 of forecast sun, less the room term for sun on the thermometer
        self.assertAlmostEqual(c.ts_star - sunny.ts_star, 0.03 * 300 - 3.0 * 0.0008 * 300, places=2)

    def test_assistance_heat_cannot_push_the_floor_down(self):
        c = slab.SlabController()
        c.step(idle(0, room=23.0, shield=True, learn=False))
        self.assertEqual(c.parts["room"], 0.0)
        self.assertEqual(c.integ, 0.0)


class WritesAndState(unittest.TestCase):
    def test_hard_cap_and_soft_budget(self):
        p = Params()
        c = slab.SlabController(p)
        x = idle(2000)
        c.wlog.extend(float(m) for m in range(1990 - int(p.hard_cap), 1990))
        self.assertIsNone(c._write(x, 33.0))
        self.assertEqual(c.note, "budget")
        c.wlog = type(c.wlog)(float(m) for m in range(1990 - int(p.budget), 1990))
        self.assertIsNone(c._write(x, 33.0, critical=False))
        self.assertEqual(c._write(x, 33.0, critical=True), 33.0)
        self.assertEqual(c.writes_24h(2000), p.budget + 1)
        # writes older than 24 h leave the budget
        self.assertEqual(c.writes_24h(2000 + 1440), 0)

    def test_observe_decides_without_counting_writes(self):
        c = slab.SlabController()
        d = c.step(idle(0, act=False, learn=False))
        self.assertEqual(d.setpoint, 29.0)
        self.assertEqual(len(c.wlog), 0)
        self.assertEqual(c.integ, 0.0)

    def test_learning_follows_the_room_error(self):
        c = slab.SlabController()
        for m in range(60):
            c.step(idle(m, room=21.0, inlet=40.0, outlet=39.7, setpoint=25.0))  # warm floor, cold room
        self.assertAlmostEqual(c.integ, 0.15 * 1.0, places=2)  # 0.15 K per K-hour
        self.assertGreater(max(c.daily), 0.0)

    def test_state_round_trip_and_invalid_parts_ignored(self):
        c = slab.SlabController()
        c.integ, c.daily, c.fb = 1.25, [0.1 * i - 1.2 for i in range(24)], [0.5, 1.0, 1.5, 2.0]
        c.wlog.extend([10.0, 20.0])
        again = slab.SlabController()
        self.assertTrue(again.restore(c.state()))
        self.assertEqual(again.state(), c.state())
        broken = slab.SlabController()
        self.assertFalse(broken.restore({"integ": "x", "daily": [1, 2], "fb": [math.nan] * 4, "writes": "?"}))
        self.assertEqual(broken.state(), slab.SlabController().state())
        self.assertFalse(broken.restore({"version": 99, "integ": 3.0}))
        self.assertEqual(broken.integ, 0.0)
        clamped = slab.SlabController()
        clamped.restore({"integ": 50.0, "daily": [9.0] * 24})
        self.assertEqual((clamped.integ, max(clamped.daily)), (6.0, 2.0))

    def test_adopting_a_running_unit_rides_it_without_a_minimum_run(self):
        c = slab.SlabController()
        c.adopt(True)
        self.assertTrue(c.run)
        self.assertEqual(c.t_state, 60.0)
        c.adopt(False)
        self.assertFalse(c.run)
        self.assertGreaterEqual(c.t_state, 45.0)  # a cold floor may start at once after a handover
        # a run adopted while the floor is already over its stop point ends at once
        warm = slab.SlabController()
        warm.ts = 33.0
        warm.adopt(True)
        d = warm.step(running(0, inlet=33.0, outlet=36.0, setpoint=36.0, room=22.6))
        self.assertEqual((d.phase, warm.note), ("stop", "warm"))
        # a first step during a run reads the floor from the water, not the warmer return
        fresh = slab.SlabController()
        fresh.adopt(True)
        fresh.step(running(0, inlet=27.0, outlet=31.0, setpoint=31.0))
        self.assertTrue(fresh.run)

    def test_uneven_steps_integrate_by_time(self):
        a, b = slab.SlabController(), slab.SlabController()
        for m in range(0, 120):
            a.step(idle(float(m), room=21.0, inlet=40.0, outlet=39.7))
        for m in range(0, 120, 2):
            b.step(idle(float(m), room=21.0, inlet=40.0, outlet=39.7))
        self.assertAlmostEqual(a.integ, b.integ, places=2)
        self.assertAlmostEqual(a.t_avg, b.t_avg, places=6)

    def test_reason_and_attributes_are_plain_and_complete(self):
        c = slab.SlabController()
        c.step(idle(0))
        attributes = c.attributes()
        for key in ("phase", "reason", "slab_estimate", "slab_target", "target_parts", "writes_24h",
                    "learned_integral", "daily_pattern", "fallback_curve", "room_sensor", "forecast"):
            self.assertIn(key, attributes)
        self.assertEqual(len(attributes["daily_pattern"]), 24)
        self.assertIn("Starting", attributes["reason"])


class ProductionRules(unittest.TestCase):
    """Safety rules production adds to the lab hybrid (docs/CONTROLLER.md)."""

    def test_a_high_minimum_water_never_parks_at_the_restart_point(self):
        c = slab.SlabController(Params(sp_floor=30.0))
        c.ts, c.t_state = 25.0, 999.0
        d = c.step(idle(0, inlet=25.0, outlet=24.7, room=22.6, setpoint=25.0, restart_delta=4.0))
        self.assertEqual(d.phase, "idle")
        self.assertLess(d.want - (25.0 - 0.8), 4.0)
        lab = slab.SlabController(Params(sp_floor=30.0, lab_hybrid=True))
        lab.ts, lab.t_state = 25.0, 999.0
        self.assertEqual(lab.step(idle(0, inlet=25.0, outlet=24.7, room=22.6, setpoint=25.0, restart_delta=4.0)).want, 30.0)

    def test_a_small_park_lowering_waits_like_a_raise(self):
        c = slab.SlabController()
        c.ts, c.t_state, c.last_write = 27.0, 999.0, 0.0
        x = idle(10, inlet=27.0, outlet=26.7, room=22.6, setpoint=25.0)
        want = c.step(x).want     # restart point: floor(27 - 0.8 + 5 - 0.6) = 30
        self.assertLess(want + 1, 30)
        x = replace(x, setpoint=want + 1)
        self.assertIsNone(c.step(replace(x, minute=11.0)).setpoint, "one degree lower waits 2 h")
        self.assertEqual(c.step(replace(x, minute=131.0)).setpoint, want)  # 2 h after the write at 10
        # a setpoint that could start the unit is lowered at once
        risky = slab.SlabController()
        risky.ts, risky.t_state, risky.last_write = 27.0, 999.0, 0.0
        self.assertIsNotNone(risky.step(idle(10, inlet=25.0, outlet=24.7, room=22.6, setpoint=29.0)).setpoint)

    def test_no_adoption_right_after_the_controllers_own_stop(self):
        c = slab.SlabController()
        c.ts, c.run, c.t_state, c.comp_min = 30.0, True, 70.0, 0.0
        d = c.step(running(0, inlet=29.0, outlet=33.0, setpoint=33.0, room=22.6))
        self.assertEqual(d.phase, "stop")
        for m in (1, 2):
            d = c.step(running(m, inlet=29.0, outlet=33.0, setpoint=d.setpoint or 25.0, room=22.6))
            self.assertFalse(c.run, "the unit still reports the run it was told to end")
        self.assertEqual(c.unowned_24h(), 0)

    def test_room_spikes_are_slew_limited_and_learning_is_capped(self):
        c = slab.SlabController()
        c.ts, c.t_state = 30.0, 999.0
        c.step(idle(0, room=22.0, inlet=30.0, outlet=29.7))
        c.step(idle(1, room=27.5, inlet=30.0, outlet=29.7))
        self.assertAlmostEqual(c.e, -0.05, places=6)
        for m in range(2, 62):
            c.step(idle(m, room=27.5, inlet=30.0, outlet=29.7))
        self.assertGreaterEqual(min(c.daily), -1.5 - 1e-9, "one bad hour moves a daily bin at most 1.5 K")
        self.assertGreaterEqual(c.integ, -0.15 * 3.1, "the slew limit bounds what the integral takes")
        lab = slab.SlabController(Params(lab_hybrid=True))
        lab.ts, lab.t_state = 30.0, 999.0
        lab.step(idle(0, room=22.0, inlet=30.0, outlet=29.7))
        lab.step(idle(1, room=27.5, inlet=30.0, outlet=29.7))
        self.assertAlmostEqual(lab.e, -5.5, places=6)

    def test_an_unmapped_operating_state_freezes_the_floor_and_waits(self):
        c = slab.SlabController()
        c.step(idle(0))
        ts = c.ts
        d = c.step(idle(1, mode="other", compressor_on=True, inlet=40.0, outlet=45.0))
        self.assertEqual((d.phase, d.setpoint), ("wait", None))
        self.assertEqual(c.ts, ts)
        self.assertIn("not mapped", c.reason())

    def test_release_leaves_the_idle_park_and_ends_the_run(self):
        c = slab.SlabController()
        self.assertIsNone(c.release(idle(0)), "nothing to hand back before the first step")
        c.step(idle(0))
        self.assertTrue(c.run)
        sp = c.release(running(1, inlet=27.0, outlet=31.0, setpoint=31.0))
        self.assertIsNotNone(sp)
        self.assertLess(sp, 31.0)
        self.assertFalse(c.run)
        self.assertLess(sp - (c.ts - 0.8), 5.0, "once idle the unit only restarts when the floor runs low")
        self.assertIsNone(c.release(idle(2, setpoint=sp, inlet=c.ts, outlet=c.ts - 0.3)))

    def test_restarts_keep_the_room_bookkeeping_and_a_recent_floor_estimate(self):
        c = slab.SlabController()
        for m in range(30):
            c.step(idle(m, room=21.5))
        again = slab.SlabController()
        again.restore(c.state())
        self.assertEqual((again.room_ref, again.room_since, again.last_write), (c.room_ref, c.room_since, c.last_write))
        again.step(idle(40, room=21.5))
        self.assertIsNotNone(again.ts)
        late = slab.SlabController()
        late.restore(c.state())
        late.step(idle(29 + 90, room=21.5, mode="heat", compressor_on=True, outlet=30.0, inlet=27.0))
        self.assertIsNone(late.ts, "a floor estimate from before a long stop is not reused")


class Sun(unittest.TestCase):
    def test_clear_sky_and_cloud(self):
        noon = datetime(2026, 6, 21, 11, tzinfo=timezone.utc)
        night = datetime(2026, 12, 21, 23, tzinfo=timezone.utc)
        self.assertGreater(slab.hour_ghi(noon, 52.5, 13.4, 0), 700)
        self.assertEqual(slab.hour_ghi(night, 52.5, 13.4, 0), 0.0)
        self.assertAlmostEqual(slab.cloud_factor(0), 1.0)
        self.assertAlmostEqual(slab.cloud_factor(100), 0.25)
        self.assertGreater(slab.cloud_factor(50), 0.9, "broken cloud keeps most of the sun")
        self.assertEqual(slab.cloud_factor(None), slab.cloud_factor(100))
        self.assertTrue(all(slab.cloud_factor(a) >= slab.cloud_factor(b) for a, b in zip(range(0, 100), range(1, 101))))


class SameAsTheLabHybrid(unittest.TestCase):
    """Fed the same minutes, the production core with `lab_hybrid=True` makes the lab hybrid's
    decisions exactly (the production safety rules are the only difference)."""

    def test_random_streams_match_bit_for_bit(self):
        try:
            sys.path.insert(0, str(ROOT))
            from lab.controllers.hybrid import Hybrid
            from lab.sim.interface import Observation
        except ImportError:
            self.skipTest("lab/ not present")
        finally:
            sys.path.remove(str(ROOT))
        t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for seed in range(4):
            rng = random.Random(seed)
            lab, core = Hybrid(), slab.SlabController(Params(lab_hybrid=True))
            lab.reset({})
            room, inlet, outlet, sp, on, mode, fc = 21.6, 25.0, 24.7, 25.0, False, "idle", None
            for m in range(3 * 1440):
                t = t0 + timedelta(minutes=m)
                if fc is None or m % 360 == 0:
                    out = rng.uniform(-12, 8)
                    fc = tuple({"time": t.replace(minute=0) + timedelta(hours=h + 1), "outdoor": out + rng.gauss(0, 2),
                                "ghi": max(0.0, rng.gauss(80, 120)), "cloud": 50} for h in range(48))
                    fc = tuple(h for h in fc)
                if fc and fc[0]["time"] <= t:
                    fc = tuple(h for h in fc if h["time"] > t)
                # a crude unit: follow the controller's setpoint with the restart and stop rules
                ctrl = (outlet + 0.3 - 0.8) if on else (inlet - 0.8)
                if not on and sp - ctrl >= 5.0:
                    on, mode = True, "heat"
                elif on and ctrl >= sp + 2.0:
                    on, mode = False, "idle"
                if rng.random() < 0.002:
                    mode, on = "dhw", True
                elif mode == "dhw" and rng.random() < 0.05:
                    mode, on = "idle", False
                inlet += (0.05 if on else -0.006) + rng.gauss(0, 0.01)
                outlet = inlet + (3.0 if on else -0.3)
                room += rng.gauss(0, 0.02) + (0.002 if on else -0.002)
                link = rng.random() > 0.01
                obs = Observation(time=t, local_hour=(m / 60) % 24, room=round(room, 1), room_age_min=rng.uniform(0, 30),
                                  outdoor=fc[0]["outdoor"], outlet=round(outlet, 1), inlet=round(inlet, 1), setpoint=sp,
                                  restart_delta=5.0, quiet=False, heating_enabled=True, compressor_on=on, mode=mode,
                                  electric_kw=1.0, energy_kwh=0.0, target=22.0, forecast=fc, pv_kw=None, minute=m,
                                  link_ok=link)
                x = Inputs(minute=float(m), local_hour=obs.local_hour, target=22.0, outdoor=obs.outdoor,
                           outlet=obs.outlet, inlet=obs.inlet, setpoint=sp, restart_delta=5.0, compressor_on=on,
                           mode=mode, room=obs.room, room_age_min=obs.room_age_min, link_ok=link,
                           forecast=tuple(Hour(m + (h["time"] - t).total_seconds() / 60, h["outdoor"], h["ghi"]) for h in fc))
                a, b = lab.step(obs).setpoint, core.step(x).setpoint
                self.assertEqual(a, b, f"seed {seed} minute {m}")
                if b is not None and link:
                    sp = b
            self.assertEqual((lab.integ, lab.daily, lab.fb), (core.integ, core.daily, core.fb))


if __name__ == "__main__":
    unittest.main()
