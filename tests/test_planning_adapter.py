"""Cold-night and AC coordination at the real controller's fake HA boundary."""

import asyncio
from datetime import datetime, timedelta, timezone
import types
import unittest

import test_adapter as boundary

adapter = boundary.adapter


class PlanningBoundary(unittest.IsolatedAsyncioTestCase):
    set_state = boundary.ControllerBoundary.set_state
    writes = boundary.ControllerBoundary.writes

    async def asyncSetUp(self):
        await boundary.ControllerBoundary.asyncSetUp(self)
        self.now = datetime(2026, 1, 15, 15, tzinfo=timezone.utc)
        self.config.update(cold_night_enabled=True)
        self.forecast_length = 25
        self.cloud = "sunny"
        self.refresh_inputs()
        self.hass.config = types.SimpleNamespace(units=types.SimpleNamespace(temperature_unit="°C"))
        async def service(domain, name, data, **kwargs):
            self.calls.append((domain, name, data))
            if domain == "number":
                self.set_state(data["entity_id"], data["value"], **self.states[data["entity_id"]].attributes)
            elif domain == "climate":
                attrs = dict(self.states[data["entity_id"]].attributes)
                attrs.update({k: v for k, v in data.items() if k == "temperature"})
                self.set_state(data["entity_id"], data["hvac_mode"], **attrs)
            else:
                return {"weather.house": {"forecast": [
                    {"datetime": (self.now + timedelta(hours=i)).isoformat(),
                     "temperature": -30 if (self.now + timedelta(hours=i)).hour < 9 or (self.now + timedelta(hours=i)).hour >= 20 else -20,
                     "condition": self.cloud if 9 <= (self.now + timedelta(hours=i)).hour < 16 else "clear-night"}
                    for i in range(self.forecast_length)]}}
        self.hass.services.async_call = service
        await self.make_controller()

    async def asyncTearDown(self):
        await boundary.ControllerBoundary.asyncTearDown(self)

    def refresh_inputs(self, indoor=22.0, outdoor=-20.0):
        self.set_state("sensor.room", indoor, unit_of_measurement="°C")
        self.set_state("weather.house", "cloudy", temperature=outdoor, temperature_unit="°C")
        self.set_state("sensor.operating", "HEAT")
        self.set_state("number.water", 30, unit_of_measurement="°C", min=20, max=50, step=1)
        self.set_state("sensor.return_water", 28, unit_of_measurement="°C")
        self.set_state("sensor.supply_water", 32, unit_of_measurement="°C")

    async def make_controller(self):
        self.controller = adapter.HeatingCoordinator(self.hass, self.entry, self.releases)
        self.controller.started = self.now - timedelta(hours=1)
        await self.controller.async_load()

    async def configure_ac(self):
        self.config.update(ac_entity="climate.living", ac_room_entity="sensor.room", ac_min_outdoor=-25.0)
        self.set_state("climate.living", "off", temperature=22, hvac_modes=["off", "heat", "cool"],
                       supported_features=1, min_temp=16, max_temp=30, target_temp_step=1)
        await self.make_controller()
        self.controller.ac.stopped_at = self.now.timestamp() - 3600
        self.controller.ac.blocked_until = 0

    async def test_cold_forecast_prepares_in_observe_without_commands(self):
        await self.controller.async_request_refresh()
        self.assertEqual(self.controller.planner_data["phase"], "prepare")
        self.assertEqual(self.controller.planner_data["effective_target"], 23)
        self.assertGreaterEqual(self.controller.planner_data["forecast_hours"], 18)
        self.assertFalse(self.writes())
        self.assertFalse(self.controller.planner_data["calibrated"])

    async def test_short_forecast_cannot_authorize_preparation_or_ac(self):
        await self.configure_ac()
        self.forecast_length = 12
        await self.controller.async_ac_mode("automatic")
        await self.controller.async_mode("automatic")
        self.assertEqual(self.controller.planner_data["phase"], "baseline")
        self.assertFalse(any(call[0] == "climate" for call in self.calls))
        self.assertTrue(self.writes())

    async def test_coasting_is_bounded_by_existing_slew_and_observed_reserve(self):
        self.now = self.now.replace(hour=22)
        self.refresh_inputs(indoor=22.8, outdoor=-30)
        await self.make_controller()
        self.controller.cooldown = adapter.CooldownModel(loss=.002, samples=40, hours=4)
        await self.controller.async_mode("automatic")
        self.assertEqual(self.controller.planner_data["phase"], "coast")
        self.assertEqual(self.controller.data["proposed"], 25)
        self.assertEqual(self.writes()[-1][2]["value"], 29)  # 2°C/h, 30-minute limit.

    async def test_rapid_measured_cooling_requires_early_recovery(self):
        self.now = self.now.replace(hour=22)
        self.refresh_inputs(indoor=21.3, outdoor=-30)
        await self.make_controller()
        self.controller.cooldown = adapter.CooldownModel(loss=.002, samples=40, hours=4)
        self.controller.room_history = [(self.now - timedelta(minutes=30), 21.9), (self.now - timedelta(minutes=5), 21.4)]
        await self.controller.async_request_refresh()
        self.assertEqual(self.controller.planner_data["phase"], "recovery")
        self.assertIn("rapid cooling", self.controller.data["reason"])
        self.assertGreater(self.controller.data["proposed"], 25)

    async def test_other_room_or_missing_protection_prevents_coasting(self):
        self.now = self.now.replace(hour=22)
        self.refresh_inputs(indoor=22.8, outdoor=-30)
        self.config["protection_entity"] = "sensor.bedroom"
        await self.make_controller()
        self.controller.cooldown = adapter.CooldownModel(loss=.002, samples=40, hours=4)
        for reading in ("unavailable", 20.1):
            self.set_state("sensor.bedroom", reading, unit_of_measurement="°C")
            await self.controller.async_request_refresh()
            self.assertEqual(self.controller.planner_data["phase"], "recovery")
            self.assertGreater(self.controller.data["proposed"], 25)

    async def test_manual_ac_prevents_coasting_and_hydronic_fitting(self):
        await self.configure_ac()
        self.now = self.now.replace(hour=22)
        self.refresh_inputs(indoor=22.8, outdoor=-30)
        attrs = self.states["climate.living"].attributes
        self.set_state("climate.living", "heat", **attrs)
        self.controller.cooldown = adapter.CooldownModel(loss=.002, samples=40, hours=4)
        self.controller.model.samples = 40
        self.controller.previous = dict(time=(self.now - timedelta(minutes=5)).timestamp(),
            indoor=22.79, outdoor=-30, water=30, eligible=True)
        await self.controller.async_request_refresh()
        self.assertEqual(self.controller.planner_data["phase"], "baseline")
        self.assertEqual(self.controller.model.samples, 40)
        self.assertFalse(any(call[0] == "climate" for call in self.calls))
        self.assertFalse(self.controller.previous["eligible"])

    async def test_ac_needs_both_automatic_modes_and_stops_with_main_observe(self):
        await self.configure_ac()
        await self.controller.async_ac_mode("automatic")
        self.assertFalse(any(call[0] == "climate" for call in self.calls))
        await self.controller.async_mode("automatic")
        self.assertEqual(self.states["climate.living"].state, "heat")
        await self.controller.async_ac_tick()  # Confirm the commanded state.
        await self.controller.async_mode("observe")
        self.assertEqual(self.states["climate.living"].state, "off")
        await self.controller.async_ac_tick()
        self.assertIsNone(self.controller.ac.session)

    async def test_inhibit_arriving_during_forecast_prevents_both_writers(self):
        await self.configure_ac()
        self.controller.ac.mode = "automatic"
        self.controller.config["inhibit_entity"] = "input_boolean.inhibit"
        self.set_state("input_boolean.inhibit", "off")
        original = self.hass.services.async_call
        async def service(domain, name, data, **kwargs):
            result = await original(domain, name, data, **kwargs)
            if domain == "weather":
                self.set_state("input_boolean.inhibit", "on")
            return result
        self.hass.services.async_call = service
        await self.controller.async_mode("automatic")
        self.assertFalse(self.writes())
        self.assertFalse(any(call[0] == "climate" for call in self.calls))

    async def test_manual_water_edit_during_forecast_stops_both_writers(self):
        await self.configure_ac()
        self.controller.ac.mode = "automatic"
        await self.controller.async_request_refresh()
        self.controller.forecast_checked = None
        original = self.hass.services.async_call
        async def service(domain, name, data, **kwargs):
            result = await original(domain, name, data, **kwargs)
            if domain == "weather":
                self.set_state("number.water", 25, **self.states["number.water"].attributes)
            return result
        self.hass.services.async_call = service
        await self.controller.async_mode("automatic")
        self.assertTrue(self.controller.manual_hold)
        self.assertFalse(self.writes())
        self.assertFalse(any(call[0] == "climate" for call in self.calls))

    async def test_mapping_changes_reset_both_models_and_restart_is_observe(self):
        self.controller.cooldown = adapter.CooldownModel(loss=.002, samples=40, hours=4)
        self.controller.model.samples = 40
        await self.controller.async_save()
        await self.make_controller()
        self.assertEqual(self.controller.cooldown.samples, 40)
        self.assertEqual(self.controller.mode, "observe")
        self.entry.options = {"ac_entity": "climate.new", "ac_room_entity": "sensor.room"}
        await self.make_controller()
        self.assertEqual(self.controller.cooldown.samples, 0)
        self.assertEqual(self.controller.model.samples, 0)
        self.assertEqual(self.controller.ac.mode, "observe")

    async def test_room_target_cannot_escape_commissioned_planning_bounds(self):
        with self.assertRaises(boundary.HAError):
            await self.controller.async_target(24)

    async def test_manual_hold_set_during_ac_await_prevents_water_write(self):
        async def interrupted(*args):
            self.controller.manual_hold = True
        self.controller.ac.async_tick = interrupted
        await self.controller.async_mode("automatic")
        self.assertFalse(self.writes())
        self.assertEqual(self.controller.data["status"], "paused")

    async def test_room_reaching_ceiling_during_ac_await_reduces_water(self):
        async def changed_room(*args):
            self.set_state("sensor.room", 23.1, unit_of_measurement="°C")
        self.controller.ac.async_tick = changed_room
        await self.controller.async_mode("automatic")
        self.assertEqual(self.controller.data["proposed"], 25)
        self.assertEqual(self.writes()[-1][2]["value"], 29)

    async def test_manual_ac_and_missing_forecast_cannot_hide_overheating(self):
        await self.configure_ac()
        self.forecast_length = 0
        self.set_state("sensor.room", 26, unit_of_measurement="°C")
        self.set_state("climate.living", "heat", **self.states["climate.living"].attributes)
        await self.controller.async_request_refresh()
        self.assertEqual(self.controller.data["proposed"], 25)
        self.assertIn("ceiling", self.controller.data["reason"])
        # With planning disabled, ordinary room feedback still sees actual heat.
        self.config["cold_night_enabled"] = False
        await self.make_controller()
        self.set_state("weather.house", "cloudy", temperature=0, temperature_unit="°C")
        await self.controller.async_request_refresh()
        self.assertAlmostEqual(self.controller.data["proposed"], 26.9)

    async def test_new_comfort_bounds_reject_old_runtime_target(self):
        self.config["cold_night_enabled"] = False
        await self.make_controller()
        await self.controller.async_target(24)
        self.config["cold_night_enabled"] = True
        await self.make_controller()
        self.assertEqual(self.controller.settings.target, 22)

    async def test_changed_coast_water_invalidates_only_cooldown_calibration(self):
        self.controller.cooldown = adapter.CooldownModel(loss=.002, samples=40, hours=4)
        self.controller.model.samples = 40
        await self.controller.async_save()
        self.entry.options = {"minimum_water": 20}
        await self.make_controller()
        self.assertEqual(self.controller.cooldown.samples, 0)
        self.assertEqual(self.controller.model.samples, 40)

    async def test_recovery_budget_covers_coast_level_and_quantized_commands(self):
        self.assertEqual(self.controller.recovery_ramp_hours(self.controller.snapshot(self.now)), 4.5)
        self.set_state("number.water", 40, **self.states["number.water"].attributes)
        # Currently hot water must not hide how long a later25°C coast takes.
        self.assertEqual(self.controller.recovery_ramp_hours(self.controller.snapshot(self.now)), 4.5)
        self.states["number.water"].attributes["step"] = 3
        await self.controller.async_request_refresh()
        self.assertEqual(self.controller.planner_data["phase"], "baseline")
        self.assertIn("recovery", self.controller.planner_data["reason"].lower())

    async def test_cooldown_requires_settled_actual_water_and_restarts_after_off(self):
        self.now = self.now.replace(hour=20)
        self.set_state("number.water", 25, **self.states["number.water"].attributes)
        start = self.now
        # Low requested water with a still-hot floor circuit is insufficient.
        for i in range(25):
            self.now = start + timedelta(minutes=5 * i)
            self.set_state("sensor.room", 22.8 - i * .01, unit_of_measurement="°C")
            self.set_state("sensor.return_water", 30, unit_of_measurement="°C")
            self.set_state("sensor.supply_water", 32, unit_of_measurement="°C")
            self.controller.planning_inputs(self.now, self.controller.snapshot(self.now))
        self.assertEqual(self.controller.cooldown.samples, 0)
        start = self.now
        for i in range(40):
            self.now = start + timedelta(minutes=5 * i)
            self.set_state("sensor.room", 22.5 - i * .015, unit_of_measurement="°C")
            self.set_state("weather.house", "cloudy", temperature=-30, temperature_unit="°C")
            self.set_state("sensor.return_water", 25, unit_of_measurement="°C")
            self.set_state("sensor.supply_water", 26, unit_of_measurement="°C")
            self.controller.planning_inputs(self.now, self.controller.snapshot(self.now))
        self.assertTrue(self.controller.cooldown.calibrated)
        self.assertTrue(self.controller.planner_data["cooldown_learning_eligible"])
        samples = self.controller.cooldown.samples
        await self.controller.async_mode("off")
        self.now += timedelta(minutes=5)
        await self.controller.async_mode("observe")
        self.assertEqual(self.controller.cooldown.samples, samples)
        self.assertFalse(self.controller.planner_data["cooldown_learning_eligible"])


if __name__ == "__main__":
    unittest.main()
