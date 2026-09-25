"""Optional smoke checks using real HA classes, skipped in the add-on worker.

Run in a development venv with requirements-dev.txt installed. These do not
replace loading the integration in an isolated HA instance before deployment.
"""

import importlib
import importlib.util
import json
import tempfile
import unittest

from common import SOURCE, module

HAS_HA = importlib.util.find_spec("homeassistant") is not None


@unittest.skipUnless(HAS_HA, "Home Assistant runtime is not installed in this worker")
class HomeAssistantSmoke(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from homeassistant.core import HomeAssistant
        self.temp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.temp.name)

    async def asyncTearDown(self):
        await self.hass.async_stop()
        self.temp.cleanup()

    async def test_platforms_import_against_real_homeassistant(self):
        for name in ("config_flow", "coordinator", "sensor", "number", "select", "button", "update", "updater"):
            self.assertIsNotNone(module(name))

    async def test_selector_form_uses_real_ha_schemas(self):
        flow_module = module("config_flow")
        flow = flow_module.AdaptiveHeatingConfigFlow()
        flow.hass = self.hass
        form = await flow.async_step_user()
        self.assertEqual(form["type"], "form")
        self.assertEqual(form["step_id"], "user")
        self.assertIsNotNone(form["data_schema"])

    async def test_full_entry_setup_options_and_unload_restore_tank(self):
        from homeassistant import bootstrap, loader
        from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState

        domain = "adaptive_heating"
        loader.async_setup(self.hass)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await bootstrap.async_load_base_functionality(self.hass)
        manifest = json.loads((SOURCE / "manifest.json").read_text())
        self.hass.data[loader.DATA_CUSTOM_COMPONENTS] = {
            domain: loader.Integration(self.hass, "custom_components.adaptive_heating", SOURCE, manifest,
                                       {path.name for path in SOURCE.iterdir()})
        }
        config = {"indoor_entity": "sensor.room", "weather_entity": "weather.house",
                  "output_entity": "number.water", "operating_entity": "sensor.operating",
                  "tank_temperature_entity": "sensor.tank", "tank_target_entity": "number.tank"}
        self.hass.states.async_set("sensor.room", 22, {"unit_of_measurement": "°C"})
        self.hass.states.async_set("weather.house", "cloudy", {"temperature": 10, "temperature_unit": "°C"})
        self.hass.states.async_set("sensor.operating", "HEAT")
        self.hass.states.async_set("sensor.tank", 40, {"unit_of_measurement": "°C"})
        attrs = {"unit_of_measurement": "°C", "min": 20, "max": 80, "step": 1}
        self.hass.states.async_set("number.water", 30, attrs)
        self.hass.states.async_set("number.tank", 52, attrs)
        entry = ConfigEntry(domain=domain, data=config, options={}, source="user", title="Test heating",
                            version=1, minor_version=1, discovery_keys={}, subentries_data=[], unique_id=None)
        await self.hass.config_entries.async_add(entry)
        self.assertEqual(entry.state, ConfigEntryState.LOADED)
        await self.hass.async_block_till_done()
        coordinator = entry.runtime_data
        self.assertEqual(coordinator.disinfection.mode, "observe")
        self.assertIsNotNone(self.hass.states.get("sensor.test_heating_disinfection_status"))
        form = await self.hass.config_entries.options.async_init(entry.entry_id)
        self.assertEqual(form["type"], "form")
        self.assertIn("tank_target_entity", {str(key) for key in form["data_schema"].schema})
        constants = importlib.import_module("custom_components.adaptive_heating.const")
        dhw_policy = importlib.import_module("custom_components.adaptive_heating.disinfection")
        options = constants.DEFAULTS | dhw_policy.DEFAULTS | config
        result = await self.hass.config_entries.options.async_configure(form["flow_id"], options)
        self.assertEqual(result["type"], "create_entry")
        await self.hass.async_block_till_done()
        coordinator = entry.runtime_data
        self.assertEqual(coordinator.disinfection.mode, "observe")

        writes = []
        async def set_number(call):
            writes.append(dict(call.data))
            self.hass.states.async_set(call.data["entity_id"], call.data["value"], attrs)
        self.hass.services.async_register("number", "set_value", set_number)
        await coordinator.async_disinfection_mode("automatic")
        await coordinator.async_disinfection_run()
        await self.hass.async_block_till_done()
        self.assertEqual(float(self.hass.states.get("number.tank").state), 68)
        # Options cannot change mappings under an active cycle.
        flow = importlib.import_module("custom_components.adaptive_heating.config_flow")
        self.assertEqual(flow.validate(self.hass, config | {"heating_state": "HEAT"}, entry.entry_id)["base"], "disinfection_active")
        self.assertTrue(await self.hass.config_entries.async_unload(entry.entry_id))
        await self.hass.async_block_till_done()
        self.assertEqual(float(self.hass.states.get("number.tank").state), 52)
        self.assertEqual([item["value"] for item in writes], [68, 52])
        self.assertIsNone(coordinator.disinfection.last_success)
        self.assertEqual(self.hass.states.get("sensor.test_heating_disinfection_status").state, "unavailable")

        # The persisted journal is clear, and reloading never restores Automatic.
        self.assertTrue(await self.hass.config_entries.async_setup(entry.entry_id))
        self.assertEqual(entry.runtime_data.disinfection.mode, "observe")
        self.assertIsNone(entry.runtime_data.disinfection.cycle)
        self.assertTrue(await self.hass.config_entries.async_unload(entry.entry_id))

    async def test_ac_entities_options_events_and_unload_recovery(self):
        from homeassistant import bootstrap, loader
        from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
        from homeassistant.util import dt as dt_util

        domain = "adaptive_heating"
        loader.async_setup(self.hass)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await bootstrap.async_load_base_functionality(self.hass)
        manifest = json.loads((SOURCE / "manifest.json").read_text())
        self.hass.data[loader.DATA_CUSTOM_COMPONENTS] = {
            domain: loader.Integration(self.hass, "custom_components.adaptive_heating", SOURCE, manifest,
                                       {path.name for path in SOURCE.iterdir()})}
        config = {"indoor_entity": "sensor.room", "weather_entity": "weather.house",
                  "output_entity": "number.water", "operating_entity": "sensor.operating",
                  "ac_entity": "climate.living", "ac_room_entity": "sensor.room"}
        for entity, state, attrs in (
            ("sensor.room", 22, {"unit_of_measurement": "°C"}),
            ("weather.house", "cloudy", {"temperature": 0, "temperature_unit": "°C"}),
            ("sensor.operating", "HEAT", {}),
            ("number.water", 30, {"unit_of_measurement": "°C", "min": 20, "max": 50, "step": 1}),
            ("climate.living", "off", {"temperature": 22, "hvac_modes": ["off", "heat", "cool"],
                                       "supported_features": 1, "min_temp": 16, "max_temp": 30, "target_temp_step": 1}),
        ):
            self.hass.states.async_set(entity, state, attrs)
        entry = ConfigEntry(domain=domain, data=config, options={}, source="user", title="AC test",
                            version=1, minor_version=1, discovery_keys={}, subentries_data=[], unique_id=None)
        await self.hass.config_entries.async_add(entry)
        await self.hass.async_block_till_done()
        self.assertEqual(entry.state, ConfigEntryState.LOADED)
        c = entry.runtime_data
        self.assertEqual(c.ac.mode, "observe")
        self.assertIsNotNone(self.hass.states.get("select.ac_test_ac_assistance_mode"))
        self.assertIsNotNone(self.hass.states.get("sensor.ac_test_cold_night_plan"))

        # Ordinary thermometer events must not erase model observations while
        # the AC remains Off. A transient AC operation does invalidate them.
        stamp = dt_util.utcnow()
        c.previous = {"marker": True}
        c.room_history = [(stamp, 22)]
        c.coast_since = stamp
        self.hass.states.async_set("sensor.room", 22.1, {"unit_of_measurement": "°C"})
        await self.hass.async_block_till_done()
        self.assertEqual(c.previous, {"marker": True})
        self.assertEqual(c.coast_since, stamp)

        flow_module = importlib.import_module("custom_components.adaptive_heating.config_flow")
        duplicate = config | {"output_entity": "number.other", "heating_state": "HEAT"}
        self.assertEqual(flow_module.validate(self.hass, duplicate)["ac_entity"], "already_controlled")
        writes = []
        async def climate_command(call):
            writes.append(dict(call.data))
            entity = call.data["entity_id"]
            attrs = dict(self.hass.states.get(entity).attributes)
            if "temperature" in call.data:
                attrs["temperature"] = call.data["temperature"]
            self.hass.states.async_set(entity, call.data["hvac_mode"], attrs)
        self.hass.services.async_register("climate", "set_temperature", climate_command)
        self.hass.services.async_register("climate", "set_hvac_mode", climate_command)
        c.mode = c.ac.mode = "automatic"
        c.ac.stopped_at = dt_util.utcnow().timestamp() - 3600
        async with c.lock:
            await c.ac.async_tick(True, 23, "Test preparation")
        await self.hass.async_block_till_done()
        self.assertEqual(self.hass.states.get("climate.living").state, "heat")
        self.assertIsNone(c.previous)
        self.assertEqual(flow_module.validate(self.hass, config | {"heating_state": "HEAT"}, entry.entry_id)["base"], "ac_active")
        self.assertTrue(await self.hass.config_entries.async_unload(entry.entry_id))
        await self.hass.async_block_till_done()
        self.assertEqual(self.hass.states.get("climate.living").state, "off")
        self.assertEqual([v["hvac_mode"] for v in writes], ["heat", "off"])
        self.assertIsNone(c.ac.session)
        self.assertTrue(await self.hass.config_entries.async_setup(entry.entry_id))
        self.assertEqual(entry.runtime_data.ac.mode, "observe")

        # Clearing optional AC mappings must survive merging entry.data/options.
        options = flow_module.ALL_DEFAULTS | {k: v for k, v in config.items() if not k.startswith("ac_")}
        form = await self.hass.config_entries.options.async_init(entry.entry_id)
        result = await self.hass.config_entries.options.async_configure(form["flow_id"], options)
        self.assertEqual(result["type"], "create_entry")
        await self.hass.async_block_till_done()
        self.assertFalse(entry.runtime_data.ac.configured)
        self.assertEqual(entry.options["ac_entity"], "")
        self.assertTrue(await self.hass.config_entries.async_unload(entry.entry_id))


if __name__ == "__main__":
    unittest.main()
