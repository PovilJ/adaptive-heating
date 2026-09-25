"""Cold-window planning, conservative recovery and empirical cooldown behavior."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math
import unittest
from zoneinfo import ZoneInfo

from common import module

planner = module("planner")
PlannerSettings = planner.PlannerSettings
ForecastPoint = planner.ForecastPoint
CooldownModel = planner.CooldownModel


def forecast(now, hours=24, temperature=-30, condition="cloudy"):
    start = now.replace(minute=0, second=0, microsecond=0)
    points = []
    for hour in range(hours + 1):
        at = start + timedelta(hours=hour)
        temp = temperature(at) if callable(temperature) else temperature
        label = condition(at) if callable(condition) else condition
        points.append(ForecastPoint(at, temp, label))
    return points


class ColdNightPlanning(unittest.TestCase):
    def setUp(self):
        self.settings = PlannerSettings(cold_night_enabled=True)
        self.now = datetime(2026, 1, 15, 15, tzinfo=timezone.utc)

    def plan(self, now=None, indoor=22.5, model=None, **kwargs):
        now = now or self.now
        options = {"now": now, "indoor": indoor, "outdoor": -20, "room_target": 22,
                   "forecasts": forecast(now), "coast_water_target": 25}
        options.update(kwargs)
        return planner.decide_plan(self.settings, model or CooldownModel(), **options)

    def test_disabled_planning_preserves_existing_target_without_forecast(self):
        result = planner.decide_plan(PlannerSettings(), CooldownModel(), now=self.now,
                                     indoor=22, outdoor=-20, room_target=24, forecasts=[])
        self.assertEqual(result.phase, "disabled")
        self.assertEqual(result.effective_target, 24)
        self.assertIsNone(result.floor_water_target)
        self.assertFalse(result.ac_requested)

    def test_cold_drop_prepares_even_while_sun_has_warmed_room_above_target(self):
        result = self.plan(indoor=22.8, next_sunset=self.now + timedelta(hours=1))
        self.assertEqual(result.phase, "prepare")
        self.assertEqual(result.effective_target, 23)
        self.assertGreater(result.floor_water_delta, 0)
        self.assertTrue(result.ac_requested)
        self.assertFalse(result.diagnostics["calibrated"])
        self.assertIn("uncalibrated", result.diagnostics["cooling_model"])

    def test_preparation_continues_after_sunset_until_quiet_window(self):
        now = self.now.replace(hour=18)
        result = self.plan(now, next_sunset=now.replace(hour=16))
        self.assertEqual(result.phase, "prepare")
        self.assertEqual(datetime.fromisoformat(result.diagnostics["prepare_at"]).hour, 13)

    def test_early_cold_drop_can_start_preparation_before_fallback_clock(self):
        now = self.now.replace(hour=12)
        result = self.plan(now, forecasts=forecast(now, temperature=lambda at: -20 if at.hour < 15 else -30))
        self.assertEqual(result.phase, "prepare")
        self.assertEqual(datetime.fromisoformat(result.diagnostics["prepare_at"]).hour, 12)

    def test_actual_sunset_is_converted_to_the_local_schedule_date(self):
        local = ZoneInfo("America/Los_Angeles")
        now = self.now.replace(hour=14, minute=30, tzinfo=local)
        sunset = now.replace(hour=17, minute=0).astimezone(timezone.utc)
        result = self.plan(now, outdoor=-30, next_sunset=sunset)
        self.assertEqual(result.phase, "prepare")
        self.assertEqual(datetime.fromisoformat(result.diagnostics["prepare_at"]).hour, 14)

    def test_ceiling_stops_both_boosts_and_requests_low_water(self):
        result = self.plan(indoor=23)
        self.assertEqual(result.phase, "ceiling_hold")
        self.assertEqual(result.floor_water_delta, 0)
        self.assertEqual(result.floor_water_target, 25)
        self.assertFalse(result.ac_requested)

    def test_sufficient_existing_reserve_does_not_request_extra_heating(self):
        slow = CooldownModel(loss=0.001, samples=20, hours=4)
        result = self.plan(indoor=22.8, outdoor=-30, model=slow)
        self.assertTrue(result.diagnostics["reserve_sufficient"])
        self.assertEqual(result.phase, "scheduled")
        self.assertEqual(result.effective_target, 22)
        self.assertEqual(result.floor_water_delta, 0)
        self.assertFalse(result.ac_requested)

    def test_coasting_spans_midnight_but_is_not_a_promise_to_last_all_night(self):
        for hour in (20, 23, 0, 2):
            now = self.now.replace(hour=hour)
            if hour < 3:
                now += timedelta(days=1)
            result = self.plan(now, indoor=23, outdoor=-30)
            self.assertEqual(result.phase, "coast", (now, result))
            self.assertEqual(result.floor_water_target, 25)
            self.assertGreater(result.effective_target, self.settings.night_minimum)
            self.assertFalse(result.ac_requested)
            recovery = datetime.fromisoformat(result.diagnostics["recovery_at"])
            self.assertGreater(recovery, now)

    def test_autumn_clock_change_includes_the_extra_hour_of_cooling(self):
        local = ZoneInfo("Europe/Vilnius")
        now = datetime(2026, 10, 25, 0, tzinfo=local)
        points = forecast(now.astimezone(timezone.utc), temperature=-27)
        result = self.plan(now, indoor=23, outdoor=-27, forecasts=points, measured_cooling_rate=0.5)
        # Midnight to 09:00 spans ten elapsed hours on this date, not nine.
        self.assertAlmostEqual(result.diagnostics["predicted_minimum"], 18)

    def test_cooling_margin_restarts_floor_before_room_reaches_night_minimum(self):
        now = self.now.replace(hour=1) + timedelta(days=1)
        result = self.plan(now, indoor=21.2, outdoor=-30)
        self.assertEqual(result.phase, "recovery")
        self.assertEqual(result.effective_target, 22)
        self.assertIsNone(result.floor_water_target)

    def test_water_ramp_forces_earlier_recovery_than_floor_delay_alone(self):
        now = self.now.replace(hour=23)
        original = self.plan(now, indoor=23, outdoor=-30)
        zero_ramp = self.plan(now, indoor=23, outdoor=-30, recovery_ramp_hours=0)
        long_ramp = self.plan(now, indoor=23, outdoor=-30, recovery_ramp_hours=4)
        self.assertEqual(original, zero_ramp)
        self.assertEqual(original.phase, "coast")
        self.assertEqual(long_ramp.phase, "recovery")
        self.assertEqual(long_ramp.diagnostics["floor_lead_hours"], 3)
        self.assertEqual(long_ramp.diagnostics["recovery_ramp_hours"], 4)
        self.assertEqual(long_ramp.diagnostics["effective_recovery_lead_hours"], 7)

    def test_seven_and_half_hour_recovery_crosses_deadline_in_elapsed_time(self):
        slow = CooldownModel(loss=0.001, samples=20, hours=4)
        vilnius = ZoneInfo("Europe/Vilnius")
        deadlines = (
            datetime(2026, 1, 16, 1, 30, tzinfo=timezone.utc),
            # Autumn adds a night hour; spring removes one. Both still allow
            # exactly 7.5 elapsed hours before the 09:00 morning target.
            datetime(2026, 10, 25, 2, 30, tzinfo=vilnius),
            datetime(2026, 3, 29, 0, 30, tzinfo=vilnius),
        )
        for deadline in deadlines:
            before = (deadline.astimezone(timezone.utc) - timedelta(minutes=1)).astimezone(deadline.tzinfo)
            for now, phase in ((before, "coast"), (deadline, "recovery")):
                result = self.plan(now, indoor=23, outdoor=-30, model=slow,
                                   forecasts=forecast(now.astimezone(timezone.utc)), recovery_ramp_hours=4.5)
                self.assertEqual(result.phase, phase, (now, result))
                self.assertEqual(datetime.fromisoformat(result.diagnostics["recovery_at"]), deadline)

    def test_ramp_does_not_shift_sunset_preparation_or_extend_morning_window(self):
        now = self.now.replace(hour=15)
        sunset = now.replace(hour=17)
        original = self.plan(now, outdoor=-30, next_sunset=sunset)
        delayed = self.plan(now, outdoor=-30, next_sunset=sunset, recovery_ramp_hours=6)
        self.assertEqual(original.diagnostics["prepare_at"], delayed.diagnostics["prepare_at"])
        afternoon = self.plan(now.replace(hour=13), outdoor=-30, recovery_ramp_hours=6)
        self.assertEqual(afternoon.phase, "scheduled")
        self.assertEqual(datetime.fromisoformat(afternoon.diagnostics["night_start"]).day, now.day)

    def test_invalid_or_beyond_horizon_ramps_fall_back_without_lowering_water(self):
        now = self.now.replace(hour=23)
        for ramp in (None, math.nan, math.inf, -1, True, "4", 25):
            result = self.plan(now, recovery_ramp_hours=ramp)
            self.assertEqual(result.phase, "baseline", ramp)
            self.assertIsNone(result.floor_water_target)
            self.assertEqual(result.effective_target, 22)
            self.assertFalse(result.ac_requested)

    def test_measured_rapid_cooling_overrides_slow_learned_behavior(self):
        now = self.now.replace(hour=23)
        slow = CooldownModel(loss=0.001, samples=20, hours=4)
        normal = self.plan(now, model=slow, outdoor=-30)
        rapid = self.plan(now, model=slow, outdoor=-30, measured_cooling_rate=0.9)
        self.assertEqual(normal.phase, "coast")
        self.assertEqual(rapid.phase, "recovery")
        self.assertIn("rapid cooling", rapid.reason)
        self.assertEqual(rapid.diagnostics["cooling_rate"], 0.9)

    def test_cloudy_morning_recovers_earlier_than_clear_morning(self):
        now = self.now.replace(hour=6) + timedelta(days=1)
        cloudy = self.plan(now, indoor=23, outdoor=-30)
        sunny = self.plan(now, indoor=23, outdoor=-30, forecasts=forecast(now, condition="sunny"))
        self.assertEqual(cloudy.phase, "recovery")
        self.assertEqual(sunny.phase, "coast")
        self.assertLess(datetime.fromisoformat(cloudy.diagnostics["recovery_at"]),
                        datetime.fromisoformat(sunny.diagnostics["recovery_at"]))

    def test_sunny_forecast_never_overrides_a_threatened_night_minimum(self):
        now = self.now.replace(hour=6) + timedelta(days=1)
        result = self.plan(now, indoor=21.2, outdoor=-30, forecasts=forecast(now, condition="sunny"))
        self.assertEqual(result.phase, "recovery")
        self.assertFalse(result.ac_requested)

    def test_partly_cloudy_and_short_sunny_coverage_get_no_delayed_recovery(self):
        now = self.now.replace(hour=6) + timedelta(days=1)
        for points in (forecast(now, condition="partlycloudy"), forecast(now, hours=4, condition="sunny")):
            result = self.plan(now, indoor=23, outdoor=-30, forecasts=points)
            self.assertEqual(result.phase, "recovery")
            self.assertFalse(result.diagnostics["sunny_morning"])

    def test_sunny_morning_requires_forecast_through_ramp_and_floor_response(self):
        now = self.now.replace(hour=6) + timedelta(days=1)
        points = forecast(now, hours=6, condition="sunny")
        physical_only = self.plan(now, indoor=23, outdoor=-30, forecasts=points)
        slow_actuator = self.plan(now, indoor=23, outdoor=-30, forecasts=points, recovery_ramp_hours=4)
        self.assertTrue(physical_only.diagnostics["sunny_morning"])
        self.assertFalse(slow_actuator.diagnostics["sunny_morning"])
        self.assertEqual(slow_actuator.phase, "recovery")

    def test_sunny_delay_cannot_use_forecasts_beyond_the_24_hour_horizon(self):
        points = forecast(self.now, hours=36, condition="sunny")
        slow = CooldownModel(loss=0.001, samples=20, hours=4)
        result = self.plan(outdoor=-30, forecasts=points, model=slow, recovery_ramp_hours=4.5)
        # At 15:00, tomorrow's 09:00 + 7.5-hour response is outside the
        # supported horizon even when the provider supplies 36 hours of data.
        self.assertEqual(result.diagnostics["forecast_hours"], 24)
        self.assertFalse(result.diagnostics["sunny_morning"])
        self.assertEqual(datetime.fromisoformat(result.diagnostics["recovery_at"]),
                         self.now.replace(hour=1, minute=30) + timedelta(days=1))

    def test_solar_wait_needs_complete_coverage_of_the_effective_recovery_delay(self):
        now = self.now.replace(hour=9, minute=30) + timedelta(days=1)
        options = {"outdoor": -5, "forecasts": forecast(now, hours=5, temperature=-5, condition="sunny"),
                   "measured_cooling_rate": -0.2}
        self.assertEqual(self.plan(now, **options).phase, "solar_wait")
        self.assertEqual(self.plan(now, recovery_ramp_hours=4, **options).phase, "baseline")

    def test_solar_wait_requires_actual_warming_and_not_tomorrows_cold_night(self):
        now = self.now.replace(hour=9, minute=30) + timedelta(days=1)
        points = forecast(now, hours=5, temperature=-5, condition="sunny")
        common = {"outdoor": -5, "forecasts": points}
        forecast_only = self.plan(now, **common)
        actual_rise = self.plan(now, measured_cooling_rate=-0.2, **common)
        self.assertEqual(forecast_only.phase, "recovery")
        self.assertEqual(actual_rise.phase, "solar_wait")
        self.assertEqual(actual_rise.floor_water_target, 25)
        self.assertLessEqual(actual_rise.diagnostics["predicted_minimum"], 22.5)

    def test_missing_stale_gapped_duplicate_and_short_forecasts_use_baseline(self):
        full = forecast(self.now)
        cases = (None, [], forecast(self.now, hours=12), full[2:],
                 full[:7] + full[8:], full[:7] + [full[6]] + full[7:],
                 forecast(self.now - timedelta(days=2)))
        for points in cases:
            result = self.plan(forecasts=points)
            self.assertEqual(result.phase, "baseline", points)
            self.assertFalse(result.ac_requested)
            self.assertIsNone(result.floor_water_target)
            self.assertEqual(result.effective_target, 22)

    def test_missing_readings_and_unknown_low_water_target_do_not_coast(self):
        for reading in (None, math.nan, math.inf):
            self.assertEqual(self.plan(indoor=reading).phase, "baseline")
        now = self.now.replace(hour=23)
        self.assertEqual(self.plan(now, coast_water_target=None).phase, "baseline")

    def test_one_cold_hour_does_not_trigger_preparation(self):
        points = forecast(self.now, temperature=lambda at: -30 if at.hour == 0 else 3)
        result = self.plan(outdoor=3, forecasts=points)
        self.assertEqual(result.phase, "baseline")

    def test_invalid_settings_are_rejected(self):
        for changed in ({"night_minimum": 23}, {"floor_lead_hours": 0},
                        {"morning_hour": 22}, {"prepare_hour": 15.5},
                        {"cold_threshold": math.nan}, {"cold_night_enabled": "yes"}):
            with self.assertRaises(ValueError):
                replace(self.settings, **changed)


class EmpiricalCooldown(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 1, 15, 23, tzinfo=timezone.utc)

    def test_prior_is_labelled_uncalibrated_and_never_initially_assumes_slow_cooling(self):
        model = CooldownModel()
        self.assertFalse(model.calibrated)
        self.assertAlmostEqual(model.cooling_rate(22, -28), 0.4)
        for i in range(5):
            model.observe(self.now + timedelta(minutes=10 * i), 22, -28, eligible=True)
        self.assertGreaterEqual(model.cooling_rate(22, -28), 0.4)

    def test_eligible_night_cooldown_learns_and_persists_without_previous_sample(self):
        model = CooldownModel()
        for i in range(25):
            model.observe(self.now + timedelta(minutes=10 * i), 22 - i * 0.025, -28, eligible=True)
        self.assertTrue(model.calibrated)
        self.assertLess(model.cooling_rate(22, -28), 0.4)
        restored = CooldownModel.restore(model.to_dict())
        self.assertEqual(restored.to_dict(), model.to_dict())
        restored.observe(self.now + timedelta(days=1), 21, -28, eligible=True)
        self.assertEqual(restored.samples, model.samples)

    def test_ineligible_ac_tank_daylight_or_active_heating_breaks_both_endpoints(self):
        model = CooldownModel()
        model.observe(self.now, 22, -28, eligible=True)
        model.observe(self.now + timedelta(minutes=10), 21.9, -28, eligible=False)
        model.observe(self.now + timedelta(minutes=20), 21.8, -28, eligible=True)
        self.assertEqual(model.samples, 0)
        model.observe(self.now + timedelta(minutes=30), 21.7, -28, eligible=True)
        self.assertEqual(model.samples, 1)

    def test_gaps_invalid_readings_warming_and_sensor_jumps_are_not_learning(self):
        for elapsed, indoor, outdoor in ((120, 21, -28), (10, math.nan, -28),
                                         (10, 23, -28), (10, 20, -28), (10, 21.9, 21)):
            model = CooldownModel()
            model.observe(self.now, 22, outdoor, eligible=True)
            model.observe(self.now + timedelta(minutes=elapsed), indoor, outdoor, eligible=True)
            self.assertEqual(model.samples, 0)

    def test_bad_storage_is_bounded(self):
        model = CooldownModel.restore({"loss": 100, "samples": -3, "hours": math.inf,
                                       "error": math.nan, "_previous": [0, 22, -28]})
        self.assertEqual(model.loss, 0.04)
        self.assertEqual(model.samples, 0)
        self.assertEqual(model.hours, 0)
        self.assertIsNone(model._previous)


if __name__ == "__main__":
    unittest.main()
