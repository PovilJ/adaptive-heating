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
            storage={}, services=types.SimpleNamespace(async_call=service))
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

    async def test_hot_water_state_blocks_commands_and_learning(self):
        self.set_state("sensor.operating", "HOT WATER")
        await self.controller.async_mode("automatic")
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.controller.data["status"], "paused")
        self.assertEqual(self.controller.model.samples, 0)

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
