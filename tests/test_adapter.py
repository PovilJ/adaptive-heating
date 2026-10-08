"""Run the actual HA adapter against an in-memory HA boundary (no device I/O)."""

import asyncio
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

from common import PACKAGE, SOURCE


class HAError(Exception):
    pass


class FakeStore:
    def __init__(self, hass, version, key):
        self.hass, self.key = hass, key
    async def async_load(self):
        return self.hass.storage.get(self.key)
    async def async_save(self, data):
        self.hass.storage[self.key] = data


class FakeCoordinator:
    def __init__(self, hass, *args, **kwargs):
        self.hass = hass
        self.data = None
    async def async_request_refresh(self):
        self.data = await self._async_update_data()
    def async_update_listeners(self):
        pass


def load_adapter():
    modules = {name: types.ModuleType(name) for name in (
        "homeassistant", "homeassistant.exceptions", "homeassistant.helpers", "homeassistant.helpers.storage",
        "homeassistant.helpers.update_coordinator", "homeassistant.util", "homeassistant.util.dt")}
    modules["homeassistant.exceptions"].HomeAssistantError = HAError
    modules["homeassistant.helpers.storage"].Store = FakeStore
    modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = FakeCoordinator
    modules["homeassistant.util.dt"].utcnow = lambda: datetime.now(timezone.utc)
    modules["homeassistant.util.dt"].parse_datetime = lambda value: datetime.fromisoformat(value)
    modules["homeassistant.util.dt"].as_local = lambda value: value
    modules["homeassistant.util"].dt = modules["homeassistant.util.dt"]
    name = PACKAGE + ".coordinator_harness"
    spec = importlib.util.spec_from_file_location(name, SOURCE / "coordinator.py")
    adapter = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules | {name: adapter}):
        spec.loader.exec_module(adapter)
    return adapter


adapter = load_adapter()


class State:
    def __init__(self, value, now, **attrs):
        self.state = str(value)
        self.attributes = attrs
        self.last_updated = self.last_reported = now


class ControllerBoundary(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = datetime(2026, 9, 24, 12, tzinfo=timezone.utc)
        self.clock_patch = patch.object(adapter.dt_util, "utcnow", side_effect=lambda: self.now)
        self.clock_patch.start()
        self.states = {}
        self.calls = []
        self.config = {"indoor_entity": "sensor.room", "weather_entity": "weather.house",
                       "output_entity": "number.water", "operating_entity": "sensor.operating",
                       "inlet_entity": "sensor.return_water", "outlet_entity": "sensor.supply_water"}
        self.set_state("sensor.room", 22, unit_of_measurement="°C")
        self.set_state("weather.house", "cloudy", temperature=0, temperature_unit="°C")
        self.set_state("number.water", 30, unit_of_measurement="°C", min=20, max=50, step=1)
        self.set_state("sensor.operating", "HEAT")
        self.set_state("sensor.return_water", 28, unit_of_measurement="°C")
        self.set_state("sensor.supply_water", 32, unit_of_measurement="°C")
        async def service(domain, name, data, **kwargs):
            self.calls.append((domain, name, data))
            if domain == "number":
                self.set_state("number.water", data["value"], **self.states["number.water"].attributes)
                return None
            return {"weather.house": {"forecast": [{"datetime": (self.now + timedelta(hours=i)).isoformat(), "temperature": 0} for i in range(12)]}}
        self.hass = types.SimpleNamespace(states=types.SimpleNamespace(get=self.states.get),
            storage={}, is_running=True, services=types.SimpleNamespace(async_call=service))
        self.entry = types.SimpleNamespace(data=self.config, options={}, entry_id="test", title="Test heating")
        self.releases = types.SimpleNamespace(restart_pending=False)
        self.controller = adapter.HeatingCoordinator(self.hass, self.entry, self.releases)
        self.controller.started = self.now - timedelta(hours=1)
        await self.controller.async_load()

    async def asyncTearDown(self):
        self.clock_patch.stop()

    def set_state(self, entity, value, **attrs):
        self.states[entity] = State(value, self.now, **attrs)

    def writes(self):
        return [call for call in self.calls if call[0] == "number"]

    async def test_observe_calculates_without_actuation(self):
        await self.controller.async_request_refresh()
        self.assertIsNotNone(self.controller.data["proposed"])
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.controller.mode, "observe")

    def falling_history(self, start=21.9, end=21.5):
        self.controller.room_history = [(self.now - timedelta(minutes=30 - 5 * i),
            start + (end - start) * i / 6) for i in range(7)]
        self.set_state("sensor.room", end, unit_of_measurement="°C")

    async def test_falling_cold_room_holds_floor_water_through_final_limits(self):
        self.set_state("weather.house", "cloudy", temperature=16.5, temperature_unit="°C")
        self.set_state("number.water", 35, unit_of_measurement="°C", min=20, max=50, step=1)
        self.falling_history(21.6, 21.4)
        self.controller.forecast_cache = [(self.now + timedelta(hours=i), 16.5) for i in range(12)]
        self.controller.forecast_checked = self.now
        await self.controller.async_mode("automatic")
        self.assertEqual(self.controller.data["proposed"], 35)
        self.assertEqual(self.controller.data["limited"], 35)
        self.assertEqual(self.writes(), [])
        self.assertIn("holding floor heat", self.controller.data["reason"])

    async def test_day_one_forecast_preparation_keeps_final_command_rate_limited(self):
        self.set_state("weather.house", "cloudy", temperature=5, temperature_unit="°C")
        self.controller.forecast_cache = [(self.now + timedelta(hours=i), -20) for i in range(12)]
        self.controller.forecast_checked = self.now
        await self.controller.async_mode("automatic")
        self.assertEqual(self.controller.data["proposed"], 40)
        self.assertEqual(self.writes()[-1][2]["value"], 32)
        self.assertIn("preparing before", self.controller.data["reason"])
        self.assertIsNone(self.controller.data["prediction"])

    async def test_one_sensor_step_does_not_trigger_room_trend_recovery(self):
        await self.controller.async_request_refresh()
        self.now += timedelta(minutes=5)
        self.set_state("sensor.room", 21.9, unit_of_measurement="°C")
        await self.controller.async_request_refresh()
        self.assertIsNone(self.controller.data["observed_cooling_rate"])
        self.assertEqual(self.controller.data["cooling_compensation"], 0)

    async def test_tank_pause_preserves_room_trend_without_sending_floor_command(self):
        self.falling_history()
        self.set_state("sensor.operating", "HOT WATER")
        await self.controller.async_mode("automatic")
        self.assertGreater(self.controller.data["observed_cooling_rate"], 0)
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.controller.data["recovery_boost"], 0)

    async def test_manual_ac_clears_room_trend_and_recovery_assistance(self):
        self.controller.config["ac_entity"] = "climate.living"
        self.set_state("climate.living", "heat", temperature=22, hvac_action="heating")
        self.falling_history()
        self.controller.recovery.boost = 2
        await self.controller.async_request_refresh()
        self.assertEqual(self.controller.room_history, [])
        self.assertIsNone(self.controller.data["observed_cooling_rate"])
        self.assertEqual(self.controller.data["recovery_boost"], 0)

    async def test_stalled_recovery_adds_bounded_help_only_after_floor_response(self):
        self.set_state("sensor.room", 21.5, unit_of_measurement="°C")
        for _ in range(43):
            self.set_state("sensor.room", 21.5, unit_of_measurement="°C")
            self.set_state("weather.house", "cloudy", temperature=0, temperature_unit="°C")
            self.set_state("sensor.return_water", 28, unit_of_measurement="°C")
            self.set_state("sensor.supply_water", 32, unit_of_measurement="°C")
            await self.controller.async_request_refresh()
            self.now += timedelta(minutes=5)
        self.assertEqual(self.controller.data["recovery_boost"], .5)
        self.assertIn("gradual assistance", self.controller.data["reason"])
        self.assertEqual(self.writes(), [])

    async def test_automatic_logs_actual_bounded_command(self):
        await self.controller.async_mode("automatic")
        self.assertEqual(self.writes()[0][2]["value"], 32)
        self.assertEqual(self.controller.data["commanded"], 32)
        self.assertGreater(self.controller.data["proposed"], 32)

    async def test_run_now_does_not_bypass_rate_or_time_limits(self):
        await self.controller.async_mode("automatic")
        for _ in range(5):
            await self.controller.async_request_refresh()
        self.assertEqual(len(self.writes()), 1)

    async def test_hot_water_state_blocks_commands(self):
        self.set_state("sensor.operating", "HOT WATER")
        await self.controller.async_mode("automatic")
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.controller.data["status"], "paused")
        self.assertEqual(self.controller.model.samples, 0)

    def map_heating_mode(self, value="4.0"):
        self.controller.config.update(heating_mode_entity="number.heating_mode", heating_mode_state="4")
        self.set_state("number.heating_mode", value)

    async def test_enabled_heating_adjusts_water_while_compressor_is_idle(self):
        self.map_heating_mode()
        self.set_state("sensor.operating", "OFF")
        self.set_state("sensor.room", 21.7, unit_of_measurement="°C")
        self.states["number.heating_mode"].last_reported = self.now - timedelta(days=30)
        await self.controller.async_mode("automatic")
        self.assertEqual(len(self.writes()), 1)
        self.assertGreater(self.controller.data["proposed"], 30)
        self.assertEqual(self.controller.data["status"], "command_sent")
        self.assertTrue(self.controller.snapshot(self.now)["eligible"])
        for _ in range(3):
            self.now += timedelta(minutes=5)
            await self.controller.async_request_refresh()
        # Three five-minute intervals are far too short to say anything about a slab.
        self.assertEqual(self.controller.model.samples, 0)

    async def night_of_refreshes(self, hours):
        for _ in range(int(hours * 12)):
            self.now += timedelta(minutes=5)
            for entity, state in list(self.states.items()):
                self.set_state(entity, state.state, **state.attributes)
            await self.controller.async_request_refresh()

    async def test_response_learning_needs_hours_of_night_and_stops_in_daylight(self):
        self.now = self.now.replace(hour=22, minute=0)
        await self.controller.async_request_refresh()
        await self.night_of_refreshes(1.9)
        self.assertEqual(self.controller.model.samples, 0)
        await self.night_of_refreshes(1.3)
        learned = self.controller.model.samples
        self.assertIn(learned, (2, 3))
        self.assertAlmostEqual(self.controller.model.heating_hours, learned / 2)
        self.now = self.now.replace(hour=12)
        await self.controller.async_request_refresh()
        await self.night_of_refreshes(3)
        self.assertEqual(self.controller.model.samples, learned)

    async def test_first_run_starts_from_the_original_scripts_learned_values(self):
        self.set_state("input_number.heating_k_loss", "0.01567")
        self.set_state("input_number.heating_k_gain", "0.03318")
        await self.controller.async_load()
        await self.controller.async_request_refresh()
        self.assertEqual((self.controller.model.loss, self.controller.model.gain), (0.01567, 0.03318))
        self.set_state("input_number.heating_k_loss", "0.03")
        await self.controller.async_request_refresh()
        self.assertEqual(self.controller.model.loss, 0.01567)

    async def test_tank_heating_still_observes_floor_cooling(self):
        await self.controller.async_request_refresh()
        stored = self.controller.model.emitter
        self.now += timedelta(minutes=5)
        self.set_state("sensor.operating", "HOT WATER")
        self.set_state("sensor.return_water", 60, unit_of_measurement="°C")
        self.set_state("sensor.supply_water", 65, unit_of_measurement="°C")
        self.controller.note_operating_event("sensor.operating", "HOT WATER", self.now - timedelta(minutes=5))
        await self.controller.async_request_refresh()
        self.now += timedelta(minutes=5)
        await self.controller.async_request_refresh()
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.controller.data["status"], "paused")
        self.assertTrue(self.controller.previous["compressor_active"])
        self.assertFalse(self.controller.previous["floor_heating_active"])
        self.assertLess(self.controller.model.emitter, stored)

    async def test_short_compressor_cycle_is_measured_between_polls(self):
        self.map_heating_mode()
        self.set_state("sensor.operating", "OFF")
        await self.controller.async_request_refresh()
        self.controller.note_operating_event("sensor.operating", "HEAT", self.now + timedelta(seconds=60))
        self.controller.note_operating_event("sensor.operating", "OFF", self.now + timedelta(seconds=180))
        self.now += timedelta(minutes=5)
        await self.controller.async_request_refresh()
        self.assertAlmostEqual(self.controller.previous["compressor_on_fraction"], .4)

    async def test_short_unavailable_activity_interval_does_not_fit(self):
        await self.controller.async_request_refresh()
        self.controller.note_operating_event("sensor.operating", None, self.now + timedelta(seconds=60))
        self.controller.note_operating_event("sensor.operating", "HEAT", self.now + timedelta(seconds=180))
        self.now += timedelta(minutes=5)
        await self.controller.async_request_refresh()
        self.assertEqual(self.controller.model.samples, 0)

    async def test_configured_floor_response_time_survives_reload(self):
        self.entry.options = {"thermal_response_hours": 6}
        other = adapter.HeatingCoordinator(self.hass, self.entry, self.releases)
        self.assertEqual(other.model.lag_hours, 6)
        await other.async_save()
        restored = adapter.HeatingCoordinator(self.hass, self.entry, self.releases)
        await restored.async_load()
        self.assertEqual(restored.model.lag_hours, 6)

    async def test_idle_without_heating_mode_confirmation_stays_blocked(self):
        self.set_state("sensor.operating", "OFF")
        await self.controller.async_mode("automatic")
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.controller.data["status"], "paused")

    async def test_disabled_or_unavailable_heating_mode_blocks_even_running_compressor(self):
        for value in ("3", "unknown", "unavailable", "invalid"):
            with self.subTest(value=value):
                self.map_heating_mode(value)
                await self.controller.async_mode("automatic")
                self.assertEqual(self.writes(), [])
                self.assertEqual(self.controller.data["status"], "paused")
        del self.states["number.heating_mode"]
        await self.controller.async_request_refresh()
        self.assertEqual(self.writes(), [])

    async def test_enabled_mode_keeps_hot_water_unknown_and_defrost_blocked(self):
        self.map_heating_mode()
        for value in ("HOT WATER", "unknown", "unavailable", "COOL"):
            self.set_state("sensor.operating", value)
            await self.controller.async_mode("automatic")
            self.assertEqual(self.writes(), [])
        self.controller.config["heating_idle_state"] = "HOT WATER"
        self.set_state("sensor.operating", "HOT WATER")
        await self.controller.async_request_refresh()
        self.assertEqual(self.writes(), [])
        self.controller.config["heating_idle_state"] = "OFF"
        self.controller.config["defrost_entity"] = "binary_sensor.defrost"
        self.set_state("sensor.operating", "OFF")
        self.set_state("binary_sensor.defrost", "on")
        await self.controller.async_request_refresh()
        self.assertEqual(self.writes(), [])

    async def test_heating_mode_change_during_calculation_blocks_command(self):
        self.map_heating_mode()
        self.set_state("sensor.operating", "OFF")
        original = self.hass.services.async_call
        async def change_mode(domain, name, data, **kwargs):
            if domain == "weather":
                self.set_state("number.heating_mode", 3)
            return await original(domain, name, data, **kwargs)
        self.hass.services.async_call = change_mode
        await self.controller.async_mode("automatic")
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.controller.data["status"], "paused")

    async def test_new_mode_mapping_resets_heating_model(self):
        self.controller.model.samples = 100
        await self.controller.async_save()
        self.entry.options = {"heating_mode_entity": "number.heating_mode", "heating_mode_state": "4"}
        other = adapter.HeatingCoordinator(self.hass, self.entry, self.releases)
        await other.async_load()
        self.assertEqual(other.model.samples, 0)

    async def test_defrost_and_other_controller_gate(self):
        for key, entity in (("defrost_entity", "binary_sensor.defrost"), ("inhibit_entity", "input_boolean.old_controller")):
            self.controller.config[key] = entity
            self.set_state(entity, "on")
            await self.controller.async_mode("automatic")
            self.assertEqual(self.writes(), [])
            self.set_state(entity, "off")

    async def test_stale_indoor_temperature_blocks_writes(self):
        self.states["sensor.room"].last_reported = self.now - timedelta(hours=3)
        await self.controller.async_mode("automatic")
        self.assertEqual(self.writes(), [])
        self.assertIn("stale", self.controller.data["reason"])

    async def test_unchanged_output_and_helper_do_not_become_stale(self):
        self.states["number.water"].last_reported = self.now - timedelta(days=30)
        self.controller.config["inhibit_entity"] = "input_boolean.old_controller"
        self.set_state("input_boolean.old_controller", "off")
        self.states["input_boolean.old_controller"].last_reported = self.now - timedelta(days=30)
        await self.controller.async_mode("automatic")
        self.assertEqual(len(self.writes()), 1)

    async def test_disabled_while_forecast_in_flight_cannot_write(self):
        entered, proceed = asyncio.Event(), asyncio.Event()
        original = self.hass.services.async_call
        async def service(domain, name, data, **kwargs):
            if domain == "weather":
                entered.set()
                await proceed.wait()
            return await original(domain, name, data, **kwargs)
        self.hass.services.async_call = service
        automatic = asyncio.create_task(self.controller.async_mode("automatic"))
        await entered.wait()
        observe = asyncio.create_task(self.controller.async_mode("observe"))
        await asyncio.sleep(0)
        proceed.set()
        await asyncio.gather(automatic, observe)
        self.assertEqual(self.writes(), [])

    async def test_manual_change_holds_until_explicit_resume(self):
        await self.controller.async_mode("automatic")
        self.now += timedelta(minutes=31)
        self.set_state("number.water", 35, unit_of_measurement="°C", min=20, max=50, step=1)
        await self.controller.async_request_refresh()
        self.assertTrue(self.controller.manual_hold)
        self.assertEqual(len(self.writes()), 1)

    async def test_command_not_confirmed_stops_further_writes(self):
        await self.controller.async_mode("automatic")
        self.set_state("number.water", 30, unit_of_measurement="°C", min=20, max=50, step=1)
        self.now += timedelta(minutes=5)
        await self.controller.async_request_refresh()
        self.assertTrue(self.controller.manual_hold)
        self.assertEqual(len(self.writes()), 1)

    async def test_restart_restores_target_but_does_not_enable_writes(self):
        await self.controller.async_target(23)
        await self.controller.async_mode("automatic")
        other = adapter.HeatingCoordinator(self.hass, self.entry, self.releases)
        await other.async_load()
        self.assertEqual(other.settings.target, 23)
        self.assertEqual(other.mode, "observe")

    async def test_changed_house_mapping_resets_learned_model(self):
        self.controller.model.samples = 100
        await self.controller.async_save()
        self.entry.options = {"indoor_entity": "sensor.another_room"}
        other = adapter.HeatingCoordinator(self.hass, self.entry, self.releases)
        await other.async_load()
        self.assertEqual(other.model.samples, 0)

    async def test_missing_forecast_keeps_normal_temperature_control(self):
        async def no_weather(domain, name, data, **kwargs):
            if domain == "weather":
                raise HAError("Weather unavailable")
            self.calls.append((domain, name, data))
        self.hass.services.async_call = no_weather
        await self.controller.async_mode("automatic")
        self.assertEqual(len(self.writes()), 1)
        self.assertIn("forecast unavailable", self.controller.data["reason"])

    async def test_restart_required_prevents_automatic_mode(self):
        self.releases.restart_pending = True
        with self.assertRaises(HAError):
            await self.controller.async_mode("automatic")

    async def test_fahrenheit_output_is_written_in_its_own_unit(self):
        self.set_state("number.water", 86, unit_of_measurement="°F", min=68, max=122, step=1.8)
        await self.controller.async_mode("automatic")
        self.assertAlmostEqual(self.writes()[0][2]["value"], 89.6)
        self.assertEqual(self.controller.data["commanded"], 32)

    async def test_dhw_transition_during_forecast_blocks_final_write(self):
        original = self.hass.services.async_call
        async def change_mode(domain, name, data, **kwargs):
            if domain == "weather":
                self.set_state("sensor.operating", "HOT WATER")
            return await original(domain, name, data, **kwargs)
        self.hass.services.async_call = change_mode
        await self.controller.async_mode("automatic")
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.controller.data["status"], "paused")

    async def test_surplus_needs_multiple_samples_and_a_gap_resets_it(self):
        for key, entity, value in (("pv_entity", "sensor.pv", 4000), ("import_entity", "sensor.import", 0),
                                   ("export_entity", "sensor.export", 1800)):
            self.controller.config[key] = entity
            self.set_state(entity, value, unit_of_measurement="W")
        self.controller.settings.solar_preheat = True
        for index in range(4):
            await self.controller.async_request_refresh()
            self.assertEqual(self.controller.data["surplus"], index == 3)
            if index != 3:
                self.now += timedelta(minutes=5)
        self.now += timedelta(minutes=20)
        await self.controller.async_request_refresh()
        self.assertFalse(self.controller.data["surplus"])


if __name__ == "__main__":
    unittest.main()
