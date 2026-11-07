"""Shared helpers: unit parsing, option validation and the solar-surplus rule."""

from dataclasses import replace
import math
import unittest

from common import module

engine = module("engine")
Settings, Energy = engine.Settings, engine.Energy


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
                       {"preheat_degrees": 2}, {"restart_hysteresis": 1}, {"run_output_kw": -1},
                       {"slab_supply_share": 0.9}, {"loop_kw_per_celsius": 0}, {"control_sensor_offset": 5}):
            with self.assertRaises(ValueError):
                Settings(**change)


    def test_first_house_defaults_are_valid(self):
        settings = Settings()
        self.assertEqual((settings.run_output_kw, settings.restart_hysteresis, settings.slab_supply_share), (6.5, 4.0, 0.29))


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


if __name__ == "__main__":
    unittest.main()
