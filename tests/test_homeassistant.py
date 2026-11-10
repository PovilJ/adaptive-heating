"""Optional smoke checks using real HA classes, skipped in the add-on worker.

Run in a development venv with requirements-dev.txt installed. These do not
replace loading the integration in an isolated HA instance before deployment.
"""

import importlib
import importlib.util
import json
from pathlib import Path
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

    async def test_separate_numeric_heating_mode_selector_and_validation(self):
        from homeassistant.config_entries import ConfigEntries
        self.hass.config_entries = ConfigEntries(self.hass, {})
        flow = module("config_flow")
        config = {"indoor_entity": "sensor.room", "weather_entity": "weather.house",
                  "output_entity": "number.water", "operating_entity": "sensor.activity",
                  "inlet_entity": "sensor.return", "outlet_entity": "sensor.supply",
                  "heating_mode_entity": "number.mode", "heating_mode_state": "4", "heating_state": "HEAT"}
        for entity in config.values():
            if isinstance(entity, str) and "." in entity:
                self.hass.states.async_set(entity, "4.0" if entity == "number.mode" else "OFF")
        for entity in ("number.water", "sensor.return", "sensor.supply"):
            self.hass.states.async_set(entity, 30, {"unit_of_measurement": "°C"})
        schema = flow.settings_schema(config)
        self.assertEqual(schema(config)["heating_mode_entity"], "number.mode")
        self.assertEqual(flow.validate(self.hass, config), {})
        for key in ("heating_mode_state", "heating_idle_state"):
            self.assertEqual(flow.validate(self.hass, config | {key: " "})[key], "state_required")
        self.assertEqual(flow.validate(self.hass, config | {"heating_idle_state": "HOT WATER"})["heating_idle_state"],
                         "idle_hot_water_conflict")
        # The controller reads the floor from the water sensors: the form requires them.
        without = {k: v for k, v in config.items() if k != "inlet_entity"}
        with self.assertRaises(Exception):
            flow.settings_schema(without)(without)
        self.assertEqual(flow.validate(self.hass, config | {"run_output_kw": -1})["base"], "invalid_limits")
        self.assertEqual(flow.validate(self.hass, config | {"ac_assist_below": 9})["base"], "invalid_ac_limits")

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
        from homeassistant.helpers import entity_registry as er
        config = {"indoor_entity": "sensor.room", "weather_entity": "weather.house",
                  "output_entity": "number.water", "operating_entity": "sensor.operating",
                  "inlet_entity": "sensor.return", "outlet_entity": "sensor.supply",
                  "heating_mode_entity": "number.mode", "heating_mode_state": "4",
                  "tank_temperature_entity": "sensor.tank", "tank_target_entity": "number.tank"}
        retired = {"curve_slope": 0.5, "cold_night_enabled": True, "predictive": True, "sun_entity": "sun.sun"}
        self.hass.states.async_set("sensor.room", 22, {"unit_of_measurement": "°C"})
        self.hass.states.async_set("sensor.return", 27, {"unit_of_measurement": "°C"})
        self.hass.states.async_set("sensor.supply", 30, {"unit_of_measurement": "°C"})
        self.hass.states.async_set("number.mode", "4.0")
        self.hass.states.async_set("weather.house", "cloudy", {"temperature": 10, "temperature_unit": "°C"})
        self.hass.states.async_set("sensor.operating", "HEAT")
        self.hass.states.async_set("sensor.tank", 40, {"unit_of_measurement": "°C"})
        attrs = {"unit_of_measurement": "°C", "min": 20, "max": 80, "step": 1}
        self.hass.states.async_set("number.water", 30, attrs)
        self.hass.states.async_set("number.tank", 52, attrs)
        # A 0.5 entry (config 1.1) with retired options, a retired sensor and a 0.5 learning store.
        entry = ConfigEntry(domain=domain, data=config | retired, options={"rise_per_hour": 4.0, "target": 21.5},
                            source="user", title="Test heating", version=1, minor_version=1, discovery_keys={},
                            subentries_data=[], unique_id=None)
        registry = er.async_get(self.hass)
        old = registry.async_get_or_create("sensor", domain, f"{entry.entry_id}_planner_status")
        from homeassistant.helpers.storage import Store
        await Store(self.hass, 1, f"{domain}.{entry.entry_id}.learning").async_save({"identity": "x", "log": {}})
        await Store(self.hass, 1, f"{domain}.{entry.entry_id}").async_save(
            {"identity": "x", "model_revision": 3, "target": 21.8, "configured_target": 21.5})
        await self.hass.config_entries.async_add(entry)
        self.assertEqual(entry.state, ConfigEntryState.LOADED)
        await self.hass.async_block_till_done()
        self.assertEqual(entry.minor_version, 2)
        self.assertFalse(set(retired) & set(entry.data))
        self.assertEqual(entry.options, {"target": 21.5})
        self.assertEqual({k: entry.data[k] for k in config}, config)
        self.assertIsNone(registry.async_get(old.entity_id))
        self.assertIsNone(await Store(self.hass, 1, f"{domain}.{entry.entry_id}.learning").async_load())
        coordinator = entry.runtime_data
        self.assertEqual(coordinator.settings.target, 21.8)
        self.assertEqual(coordinator.disinfection.mode, "observe")
        self.assertEqual(coordinator.data["status"], "observing")
        cycle = self.hass.states.get("sensor.test_heating_heating_cycle")
        self.assertIsNotNone(cycle)
        self.assertIn("slab_target", cycle.attributes)
        self.assertIsNotNone(self.hass.states.get("sensor.test_heating_floor_estimate"))
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

        # The persisted journal is clear, and reloading never restores tank Automatic.
        self.assertTrue(await self.hass.config_entries.async_setup(entry.entry_id))
        self.assertEqual(entry.runtime_data.disinfection.mode, "observe")
        self.assertIsNone(entry.runtime_data.disinfection.cycle)
        # Heating Automatic resumes after a plain reload; the unit is handed back on the way.
        await entry.runtime_data.async_mode("automatic")
        await self.hass.async_block_till_done()
        self.assertTrue(entry.runtime_data.in_charge)
        self.assertTrue(await self.hass.config_entries.async_reload(entry.entry_id))
        await self.hass.async_block_till_done()
        water = [w["value"] for w in writes if w["entity_id"] == "number.water"]
        self.assertTrue(water)
        self.assertLess(water[-1], 30)
        self.assertEqual(entry.runtime_data.mode, "automatic")
        self.assertEqual(entry.runtime_data.disinfection.mode, "observe")
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
                  "inlet_entity": "sensor.return", "outlet_entity": "sensor.supply",
                  "heating_mode_entity": "number.mode", "heating_mode_state": "4",
                  "ac_entity": "climate.living", "ac_room_entity": "sensor.room"}
        for entity, state, attrs in (
            ("number.mode", "4.0", {}),
            ("sensor.room", 22, {"unit_of_measurement": "°C"}),
            ("sensor.return", 27, {"unit_of_measurement": "°C"}),
            ("sensor.supply", 30, {"unit_of_measurement": "°C"}),
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
        self.assertIsNotNone(self.hass.states.get("sensor.ac_test_heating_cycle"))

        # Ordinary thermometer events do not keep the room out of learning while the AC
        # remains Off; an AC operation does.
        c.ac.blocked_until = 0
        self.hass.states.async_set("sensor.room", 22.1, {"unit_of_measurement": "°C"})
        await self.hass.async_block_till_done()
        self.assertFalse(c.ac.blocks_learning(dt_util.utcnow()))

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
        self.assertTrue(c.ac.blocks_learning(dt_util.utcnow()))
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


@unittest.skipUnless(HAS_HA, "Home Assistant runtime is not installed in this worker")
class ChartCard(unittest.IsolatedAsyncioTestCase):
    async def test_the_chart_card_is_served_and_loaded_on_every_dashboard(self):
        import sys
        import types
        from unittest.mock import AsyncMock, MagicMock

        integration = importlib.import_module("custom_components.adaptive_heating")
        loaded = []
        frontend = types.ModuleType("homeassistant.components.frontend")
        frontend.add_extra_js_url = lambda hass, url: loaded.append(url)
        hass = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()
        previous = sys.modules.get("homeassistant.components.frontend")
        sys.modules["homeassistant.components.frontend"] = frontend  # the real one needs hass_frontend
        try:
            await integration.register_chart_card(hass)
        finally:
            if previous is None:
                sys.modules.pop("homeassistant.components.frontend")
            else:
                sys.modules["homeassistant.components.frontend"] = previous
        (config,), = hass.http.async_register_static_paths.call_args.args
        self.assertEqual(config.url_path, integration.CHART_URL)
        self.assertTrue(Path(config.path).is_file())
        self.assertEqual(loaded, [f"{integration.CHART_URL}?v={integration.VERSION}"])


if __name__ == "__main__":
    unittest.main()
