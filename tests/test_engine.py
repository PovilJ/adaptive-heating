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
                       {"preheat_degrees": 2}, {"rise_per_hour": 0}, {"control_minutes": 0}):
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
    def test_forecast_outage_uses_room_feedback_not_fixed_30(self):
        cool = engine.decide(Settings(), Model(), 21, 0, [])
        warm = engine.decide(Settings(), Model(), 24, 0, [])
        self.assertGreater(cool.proposed, warm.proposed)
        self.assertIn("forecast unavailable", warm.reason)
        self.assertIsNone(warm.predicted_minimum)

    def test_untrained_model_does_not_change_the_curve(self):
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

    def test_hot_water_or_sun_intervals_do_not_fit(self):
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


if __name__ == "__main__":
    unittest.main()
