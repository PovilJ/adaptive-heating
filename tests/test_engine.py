"""Behavioral regressions for energy scenarios and final command constraints."""

from dataclasses import replace
import math
import unittest

from common import module

engine = module("engine")
Settings, Model, Energy = engine.Settings, engine.Model, engine.Energy


class Measurements(unittest.TestCase):
    def test_unit_normalization(self):
        self.assertEqual(engine.temperature("68", "°F"), 20)
        self.assertEqual(engine.power_watts("1.8", "kW"), 1800)
        self.assertEqual(engine.power_watts("1800", "W"), 1800)
        self.assertIsNone(engine.power_watts(1800, None))

    def test_unknown_nan_and_infinity_are_unusable(self):
        for value in (None, "unavailable", "unknown", "nan", math.inf, -math.inf):
            self.assertIsNone(engine.finite(value))

    def test_invalid_settings_are_rejected(self):
        for change in ({"minimum_water": 40, "maximum_water": 25}, {"target": math.nan},
                       {"preheat_degrees": 2}, {"rise_per_hour": 0}, {"control_minutes": 0},
                       {"thermal_response_hours": 0.25}, {"thermal_response_hours": 13}):
            with self.assertRaises(ValueError):
                Settings(**change)


class EnergyScenarios(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(solar_preheat=True)
        self.surplus = Energy(4000, 0, 1800, 98, 0, 0, True)

    def test_snow_on_panels_is_not_surplus(self):
        self.assertFalse(engine.surplus_available(replace(self.surplus, pv_w=0), self.settings))

    def test_zero_grid_import_with_battery_discharge_is_not_surplus(self):
        self.assertFalse(engine.surplus_available(replace(self.surplus, discharge_w=1200), self.settings))

    def test_battery_charging_keeps_priority(self):
        self.assertFalse(engine.surplus_available(replace(self.surplus, charge_w=2000), self.settings))

    def test_battery_needed_for_household_is_not_spare_energy(self):
        self.assertFalse(engine.surplus_available(replace(self.surplus, battery_soc=70), self.settings))

    def test_high_soc_alone_is_insufficient(self):
        self.assertFalse(engine.surplus_available(replace(self.surplus, export_w=0), self.settings))

    def test_missing_is_distinct_from_zero(self):
        self.assertFalse(engine.surplus_available(replace(self.surplus, import_w=None), self.settings))
        self.assertFalse(engine.surplus_available(replace(self.surplus, discharge_w=None), self.settings))
        self.assertTrue(engine.surplus_available(self.surplus, self.settings))

    def test_no_battery_is_supported(self):
        self.assertTrue(engine.surplus_available(Energy(4000, 0, 1800), self.settings))

    def test_negative_or_unknown_power_is_not_accepted(self):
        self.assertFalse(engine.surplus_available(replace(self.surplus, export_w=-1800), self.settings))


class Commands(unittest.TestCase):
    def limit(self, proposed, current=30, elapsed=0.5, step=1):
        return engine.limited_output(proposed, current, 25, 40, step, 20, elapsed, 4, 2)

    def test_final_increase_and_decrease_are_bounded(self):
        self.assertEqual(self.limit(39), 32)
        self.assertEqual(self.limit(25), 29)

    def test_immediate_repeated_request_cannot_jump_again(self):
        self.assertEqual(self.limit(40, current=32, elapsed=0), 32)

    def test_coarse_steps_do_not_break_slew_limit(self):
        self.assertEqual(self.limit(40, elapsed=0.1, step=1), 30)

    def test_manual_value_outside_limits_is_not_overwritten(self):
        self.assertIsNone(self.limit(30, current=45))

    def test_no_supported_value_returns_none(self):
        self.assertIsNone(engine.limited_output(31, 30.4, 25, 40, 1, 20, 0.01, 4, 2))

    def test_all_outputs_obey_both_bounds_and_device_grid(self):
        for current in range(25, 41):
            for proposed in range(15, 51):
                value = self.limit(proposed, current)
                self.assertGreaterEqual(value, max(25, current - 1))
                self.assertLessEqual(value, min(40, current + 2))
                self.assertAlmostEqual(value % 1, 0)


class Predictions(unittest.TestCase):
    def test_sustained_cold_forecast_prepares_before_model_is_trained(self):
        mild = engine.decide(Settings(), Model(), 22, 5, [5] * 12, actual_setpoint=30)
        cold = engine.decide(Settings(), Model(), 22, 5, [-20] * 12, actual_setpoint=30)
        self.assertGreater(cold.proposed, mild.proposed)
        self.assertEqual(cold.proposed, 40)
        self.assertFalse(cold.model_used)
        self.assertIsNone(cold.predicted_minimum)
        self.assertIn("preparing before", cold.reason)

    def test_distant_cold_outside_floor_and_water_lead_does_not_preheat_now(self):
        mild = engine.decide(Settings(), Model(), 22, 5, [5] * 12, actual_setpoint=33)
        distant = engine.decide(Settings(), Model(), 22, 5, [5] * 9 + [-20] * 3, actual_setpoint=33)
        self.assertEqual(distant.proposed, mild.proposed)

    def test_single_cold_spike_or_future_warming_does_not_shift_curve(self):
        mild = engine.decide(Settings(), Model(), 22, 5, [5] * 12)
        spike = engine.decide(Settings(), Model(), 22, 5, [5, -40] + [5] * 10)
        warmer = engine.decide(Settings(), Model(), 22, 5, [15] * 12)
        self.assertEqual(spike.proposed, mild.proposed)
        self.assertEqual(warmer.proposed, mild.proposed)

    def test_slow_water_ramp_starts_preparation_earlier(self):
        forecast = [5] * 5 + [-20] * 7
        high = engine.decide(Settings(), Model(), 22, 5, forecast, actual_setpoint=40)
        low = engine.decide(Settings(), Model(), 22, 5, forecast, actual_setpoint=25)
        self.assertGreater(low.proposed, high.proposed)

    def test_observed_cooling_prepares_before_room_falls_below_target(self):
        steady = engine.decide(Settings(), Model(), 22.1, 5, [])
        falling = engine.decide(Settings(), Model(), 22.1, 5, [], measured_cooling_rate=.2)
        self.assertAlmostEqual(falling.proposed - steady.proposed, 1.2)
        self.assertIsNone(falling.predicted_minimum)
        warm = engine.decide(Settings(), Model(), 22.1, 5, [], measured_cooling_rate=-.2)
        self.assertEqual(warm.proposed, steady.proposed)

    def test_recovery_compensation_is_bounded_and_model_cannot_cancel_it(self):
        model = Model(samples=100, emitter=40)
        decision = engine.decide(Settings(), model, 21.5, 5, [5] * 12,
                                 measured_cooling_rate=10, recovery_boost=10)
        self.assertEqual(decision.cooling_compensation, 2)
        self.assertEqual(decision.recovery_boost, 2)
        self.assertGreaterEqual(decision.proposed, 37.65)
        self.assertLessEqual(decision.proposed, 40)

    def test_invalid_forecast_hour_does_not_join_cold_points_across_gap(self):
        decision = engine.decide(Settings(), Model(), 22, 5, [-20, math.nan, -20])
        self.assertEqual(decision.planning_outdoor, 5)
        self.assertIn("forecast unavailable", decision.reason)

    def test_forecast_outage_uses_room_feedback_not_fixed_30(self):
        cool = engine.decide(Settings(), Model(), 21, 0, [])
        warm = engine.decide(Settings(), Model(), 24, 0, [])
        self.assertGreater(cool.proposed, warm.proposed)
        self.assertIn("forecast unavailable", warm.reason)
        self.assertIsNone(warm.predicted_minimum)

    def test_untrained_model_does_not_supply_a_model_projection(self):
        decision = engine.decide(Settings(), Model(), 21, 0, [-10] * 12)
        self.assertFalse(decision.model_used)

    def test_no_fake_comfort_prediction_when_house_is_cold(self):
        model = Model(samples=100, emitter=25)
        decision = engine.decide(Settings(), model, 18, -15, [-15] * 12)
        self.assertTrue(decision.model_used)
        self.assertLess(decision.predicted_minimum, 21.7)

    def test_stored_heat_changes_future_response(self):
        cold = Model(emitter=22).predict(22, 30, [0] * 6)
        warm = Model(emitter=35).predict(22, 30, [0] * 6)
        self.assertGreater(warm[0], cold[0])

    def test_invalid_forecasts_fall_back(self):
        result = engine.decide(Settings(), Model(samples=100, emitter=30), 22, 0, [math.nan, math.inf])
        self.assertFalse(result.model_used)

    def test_solar_boost_requires_opt_in_and_no_overheating(self):
        disabled = engine.decide(Settings(), Model(), 22, 0, [], True)
        enabled = engine.decide(Settings(solar_preheat=True), Model(), 22, 0, [], True)
        warm = engine.decide(Settings(solar_preheat=True), Model(), 24, 0, [], True)
        self.assertEqual(disabled.effective_target, 22)
        self.assertEqual(enabled.effective_target, 22.3)
        self.assertEqual(warm.effective_target, 22)

    def test_restart_discards_stored_emitter_estimate(self):
        model = Model.restore({"samples": 100, "emitter": 70, "loss": math.nan, "gain": -100})
        self.assertIsNone(model.emitter)
        self.assertEqual(model.loss, 0.012)
        self.assertEqual(model.gain, 0.005)

    def test_ineligible_intervals_do_not_fit(self):
        model = Model()
        previous = {"time": 0, "indoor": 22, "outdoor": 0, "water": 30, "eligible": False}
        current = dict(previous, time=300, indoor=22.1, eligible=True)
        model.observe(previous, current, eligible=True)
        self.assertEqual(model.samples, 0)

    def test_long_gap_resets_emitter_without_learning(self):
        model = Model(emitter=30)
        previous = {"time": 0, "indoor": 22, "outdoor": 0, "water": 30, "eligible": True}
        model.observe(previous, dict(previous, time=7200, water=25), eligible=True)
        self.assertEqual(model.samples, 0)
        self.assertEqual(model.emitter, 25)

    def test_compressor_stop_retains_floor_heat_and_learns_idle_response(self):
        model = Model(emitter=32)
        previous = {"time": 0, "indoor": 22, "outdoor": 5, "water": 32,
                    "eligible": True, "floor_heating_active": True}
        current = dict(previous, time=300, indoor=21.99, water=22,
                       floor_heating_active=False, compressor_on_fraction=0)
        model.observe(previous, current, eligible=True)
        self.assertGreater(model.emitter, 31)
        self.assertLess(model.emitter, 32)
        self.assertEqual(model.samples, 1)
        self.assertAlmostEqual(model.idle_hours, 1 / 12)
        self.assertEqual(model.heating_hours, 0)

    def test_idle_learning_survives_missing_circuit_water(self):
        model = Model(emitter=30)
        previous = {"time": 0, "indoor": 22, "outdoor": 5, "water": None,
                    "eligible": True, "floor_heating_active": False}
        model.observe(previous, dict(previous, time=300, indoor=21.99), eligible=True)
        self.assertEqual(model.samples, 1)
        self.assertGreater(model.emitter, 29)

    def test_floor_response_time_changes_stored_heat_release(self):
        previous = {"time": 0, "indoor": 22, "outdoor": 5, "water": 22,
                    "eligible": True, "floor_heating_active": False}
        slow, fast = Model(lag_hours=6, emitter=32), Model(lag_hours=1, emitter=32)
        current = dict(previous, time=3600, indoor=21.9)
        for model in (slow, fast):
            model.observe(previous, current, eligible=True)
        self.assertGreater(slow.emitter, fast.emitter)
        self.assertGreater(slow.emitter, 30)

    def test_cold_floor_room_keeps_cooling_before_new_heat_arrives(self):
        path = Model(emitter=22, lag_hours=6).predict(22, 35, [-10] * 12)
        self.assertLess(path[0], 22)
        self.assertLess(min(path), path[-1])

    def test_prediction_allows_for_water_recovery_before_floor_warming(self):
        model = Model(emitter=22, samples=100)
        instant = model.predict(22, 35, [-10] * 6)
        gradual = model.predict(22, 35, [-10] * 6, start_water=25, settings=Settings())
        self.assertLess(min(gradual), min(instant))
        self.assertLess(gradual[0], instant[0])

    def test_learning_coverage_is_restored_but_floor_state_is_not(self):
        model = Model.restore({"samples": 100, "heating_hours": 4, "idle_hours": 8, "emitter": 32})
        self.assertEqual(model.heating_hours, 4)
        self.assertEqual(model.idle_hours, 8)
        self.assertIsNone(model.emitter)


class RecoveryFeedback(unittest.TestCase):
    def test_room_trend_uses_half_hour_and_rejects_short_or_gapped_history(self):
        history = [(i * 300, 22 - .2 * i / 12) for i in range(7)]
        self.assertAlmostEqual(engine.cooling_trend(history), .2)
        self.assertIsNone(engine.cooling_trend(history[:2]))
        self.assertIsNone(engine.cooling_trend([(i * 700, value) for i, (_, value) in enumerate(history)]))
        rising = [(time, 44 - value) for time, value in history]
        self.assertAlmostEqual(engine.cooling_trend(rising), -.2)

    def test_stagnant_recovery_waits_for_floor_response_then_rises_in_stages(self):
        recovery, settings = engine.Recovery(), Settings()
        for time in range(0, 180 * 60, 300):
            self.assertEqual(recovery.update(time, 21.5, 22, 0, settings, enabled=True), 0)
        self.assertEqual(recovery.update(180 * 60, 21.5, 22, 0, settings, enabled=True), .5)
        for time in range(185 * 60, 210 * 60, 300):
            self.assertEqual(recovery.update(time, 21.5, 22, 0, settings, enabled=True), .5)
        self.assertEqual(recovery.update(210 * 60, 21.5, 22, 0, settings, enabled=True), 1)
        for time in range(215 * 60, 360 * 60 + 1, 300):
            recovery.update(time, 21.5, 22, 0, settings, enabled=True)
        self.assertEqual(recovery.boost, 2)

    def test_improving_room_decays_assistance_before_target_and_clears_at_target(self):
        recovery = engine.Recovery(since=0, last_time=10800, boost=1.5)
        boost = recovery.update(11100, 21.8, 22, -.2, Settings(), enabled=True)
        self.assertAlmostEqual(boost, 1.5 - 1 / 12)
        self.assertIsNone(recovery.since)
        self.assertEqual(recovery.update(11400, 22, 22, -.2, Settings(), enabled=True), 0)

    def test_ac_invalid_trend_or_sampling_gap_clears_recovery(self):
        for enabled, rate, now in ((False, .2, 300), (True, None, 300), (True, .2, 1200)):
            recovery = engine.Recovery(since=0, last_time=0, boost=2)
            self.assertEqual(recovery.update(now, 21.5, 22, rate, Settings(), enabled=enabled), 0)
            self.assertIsNone(recovery.since)


if __name__ == "__main__":
    unittest.main()
