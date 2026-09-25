"""AC ownership, device guards, recovery and learning isolation without device I/O."""

import asyncio
from datetime import datetime, timedelta, timezone
import importlib.util
import sys
import types
import unittest
from unittest.mock import patch

from common import PACKAGE, SOURCE
from test_adapter import FakeStore, HAError, State


def load_ac():
    modules = {name: types.ModuleType(name) for name in (
        "homeassistant", "homeassistant.exceptions", "homeassistant.helpers", "homeassistant.helpers.storage",
        "homeassistant.util", "homeassistant.util.dt")}
    modules["homeassistant.exceptions"].HomeAssistantError = HAError
    modules["homeassistant.helpers.storage"].Store = FakeStore
    modules["homeassistant.util.dt"].utcnow = lambda: datetime.now(timezone.utc)
    modules["homeassistant.util"].dt = modules["homeassistant.util.dt"]
    name = PACKAGE + ".ac_harness"
    spec = importlib.util.spec_from_file_location(name, SOURCE / "ac_controller.py")
    adapter = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules | {name: adapter}):
        spec.loader.exec_module(adapter)
    return adapter


ac = load_ac()


class ACSettingsTest(unittest.TestCase):
    def test_invalid_settings(self):
        for values in ({"ac_min_outdoor": -99}, {"ac_preheat_max": 30}, {"ac_max_session_kwh": 0},
                       {"ac_min_on_minutes": 1}, {"ac_min_off_minutes": 0}, {"ac_sample_seconds": float("nan")},
                       {"ac_min_on_minutes": 130}):
            with self.assertRaises(ValueError):
                ac.ACSettings(**values)


class ACBoundary(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = datetime(2026, 9, 25, 15, tzinfo=timezone.utc)
        self.clock_patch = patch.object(ac.dt_util, "utcnow", side_effect=lambda: self.now)
        self.clock_patch.start()
        self.states, self.calls = {}, []
        self.hass = types.SimpleNamespace(states=types.SimpleNamespace(get=self.states.get), storage={},
            config=types.SimpleNamespace(units=types.SimpleNamespace(temperature_unit="°C")),
            services=types.SimpleNamespace(async_call=self.service), data={})
        self.config = ac.DEFAULTS | {"ac_entity": "climate.living", "ac_room_entity": "sensor.room", "preheat_ceiling": 23}
        self.blocked, self.outdoor = "", -5
        self.owner = types.SimpleNamespace(hass=self.hass, config=self.config, entry=types.SimpleNamespace(entry_id="test"),
            mode="automatic", manual_hold=False, shutting_down=False, releases=types.SimpleNamespace(restart_pending=False),
            settings=types.SimpleNamespace(target=22), snapshot=lambda now: {"blocked": self.blocked, "outdoor": self.outdoor})
        self.set_state("climate.living", "off", hvac_modes=["heat", "off", "cool"], supported_features=1,
                       min_temp=16, max_temp=30, target_temp_step=0.5, temperature=21)
        self.set_state("sensor.room", 21.5, unit_of_measurement="°C")
        self.controller = ac.ACController(self.owner)
        await self.controller.async_load()
        self.advance(minutes=21)

    async def asyncTearDown(self):
        self.clock_patch.stop()

    def set_state(self, entity, value, **attrs):
        self.states[entity] = State(value, self.now, **attrs)

    def advance(self, *, minutes=0, seconds=0, reports=True):
        self.now += timedelta(minutes=minutes, seconds=seconds)
        if reports:
            for state in self.states.values():
                state.last_reported = self.now

    async def service(self, domain, name, data, **kwargs):
        if domain == "persistent_notification":
            return
        self.calls.append((domain, name, data))
        self.assertIsNotNone(self.hass.storage["adaptive_heating.test.ac"]["session"])
        state = self.states[data["entity_id"]]
        attrs = dict(state.attributes)
        if name == "set_temperature":
            attrs["temperature"] = data["temperature"]
        self.set_state(data["entity_id"], data["hvac_mode"], **attrs)

    async def start(self, target=23):
        await self.controller.async_mode("automatic")
        await self.controller.async_tick(True, target, "Cold-night preparation")

    async def acknowledge(self):
        self.advance(seconds=10)
        await self.controller.async_tick(True, 23, "Cold-night preparation")

    async def test_observe_never_actuates_and_restart_defaults_observe(self):
        await self.controller.async_tick(True, 23, "Cold tonight")
        self.assertEqual(self.calls, [])
        self.assertEqual(self.controller.status, "observe")
        await self.start()
        replacement = ac.ACController(self.owner)
        await replacement.async_load()
        self.assertEqual(replacement.mode, "observe")
        await replacement.async_tick(True, 23)
        self.assertEqual(self.calls[-1][1], "set_hvac_mode")
        self.assertEqual(self.states["climate.living"].state, "off")

    async def test_start_uses_normal_heat_only_and_acknowledges_later(self):
        await self.start()
        self.assertEqual(self.calls, [("climate", "set_temperature", {"entity_id": "climate.living", "temperature": 23, "hvac_mode": "heat"})])
        self.assertEqual(self.controller.status, "starting")
        self.assertFalse(self.controller.session["acknowledged"])
        await self.acknowledge()
        self.assertEqual(self.controller.status, "running")

    async def test_existing_manual_heat_or_cool_never_taken_over(self):
        for mode in ("heat", "cool", "auto"):
            self.states["climate.living"].state = mode
            await self.start()
            self.assertEqual(self.calls, [])
            self.assertIsNone(self.controller.session)
            self.assertTrue(self.controller.blocks_learning(self.now))

    async def test_learning_excludes_unknown_heat_and_settling_including_endpoint(self):
        self.advance(minutes=61)
        self.assertFalse(self.controller.blocks_learning(self.now))
        self.states["climate.living"].state = "heat"
        self.assertTrue(self.controller.blocks_learning(self.now))
        self.states["climate.living"].state = "off"
        self.advance(minutes=60)
        self.assertTrue(self.controller.blocks_learning(self.now))
        self.advance(seconds=1)
        self.assertFalse(self.controller.blocks_learning(self.now))
        self.states["climate.living"].state = "unavailable"
        self.assertTrue(self.controller.blocks_learning(self.now))

    async def test_unconfigured_ac_does_not_block_legacy_learning(self):
        self.config.pop("ac_entity")
        self.assertFalse(self.controller.blocks_learning(self.now))

    async def test_main_observe_off_hold_and_inhibit_prevent_start(self):
        for mode in ("observe", "off"):
            self.owner.mode = mode
            await self.start()
            self.assertEqual(self.calls, [])
        self.owner.mode = "automatic"
        self.owner.manual_hold = True
        await self.start()
        self.assertEqual(self.calls, [])
        self.owner.manual_hold = False
        for blocked in ("Defrost", "Hot water", "Other controller"):
            self.blocked = blocked
            await self.start()
            self.assertEqual(self.calls, [])

    async def test_cold_outdoor_stale_room_and_missing_heat_support_prevent_start(self):
        self.outdoor = -11
        await self.start()
        self.assertEqual(self.calls, [])
        self.outdoor = -5
        self.advance(minutes=11, reports=False)
        await self.start()
        self.assertIn("stale", self.controller.reason)
        self.advance(seconds=1)
        self.states["climate.living"].attributes["hvac_modes"] = ["cool", "off"]
        await self.start()
        self.assertIn("Heat", self.controller.reason)
        self.assertEqual(self.calls, [])

    async def test_room_headroom_and_device_grid_limit(self):
        self.states["sensor.room"].state = "22.8"
        await self.start()
        self.assertEqual(self.calls, [])
        self.states["sensor.room"].state = "21.5"
        await self.start(22.8)
        self.assertEqual(self.calls[0][2]["temperature"], 22.5)
        self.assertEqual(self.controller.session["target"], 22.5)

    async def test_fahrenheit_uses_system_unit_without_climate_unit_attribute(self):
        self.hass.config.units.temperature_unit = "°F"
        self.states["climate.living"].attributes.update(min_temp=60.8, max_temp=86, target_temp_step=.9, temperature=69.8)
        await self.start()
        self.assertEqual(self.calls[0][2]["temperature"], 73.4)
        await self.acknowledge()
        self.assertEqual(self.controller.status, "running")

    async def test_native_celsius_step_in_fahrenheit_home(self):
        self.hass.config.units.temperature_unit = "°F"
        self.hass.data["climate"] = types.SimpleNamespace(get_entity=lambda entity: types.SimpleNamespace(temperature_unit="°C"))
        self.states["climate.living"].attributes.update(min_temp=60.8, max_temp=86, target_temp_step=.5, temperature=69.8)
        await self.start(22.8)
        self.assertEqual(self.calls[0][2]["temperature"], 72.5)
        self.assertEqual(self.controller.session["target"], 22.5)

    async def test_rounded_fahrenheit_state_is_acknowledged_on_native_celsius_grid(self):
        self.hass.config.units.temperature_unit = "°F"
        self.hass.data["climate"] = types.SimpleNamespace(get_entity=lambda entity: types.SimpleNamespace(
            temperature_unit="°C", precision=1, min_temp=16, max_temp=30))
        self.states["climate.living"].attributes.update(min_temp=61, max_temp=86, target_temp_step=.5, temperature=70)
        await self.start(22.8)
        self.assertEqual(self.calls[0][2]["temperature"], 72.5)
        self.assertEqual(self.controller.session["target"], 22.5)
        self.states["climate.living"].attributes["temperature"] = 72
        await self.acknowledge()
        self.assertEqual(self.controller.status, "running")
        self.states["climate.living"].attributes["temperature"] = 74
        await self.controller.async_tick(True, 23)
        self.assertEqual(self.controller.status, "manual_override")

    async def test_manual_target_change_is_never_stopped_or_restored(self):
        await self.start()
        await self.acknowledge()
        self.states["climate.living"].attributes["temperature"] = 24
        await self.controller.async_tick(True, 23)
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(self.controller.latched)
        self.assertIsNone(self.controller.session)

    async def test_restart_retains_manual_target_and_recovers_previous_entity(self):
        await self.start()
        self.config["ac_entity"] = "climate.another"
        replacement = ac.ACController(self.owner)
        await replacement.async_load()
        self.states["climate.living"].attributes["temperature"] = 24
        self.advance(minutes=3)
        await replacement.async_tick()
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(replacement.latched)
        self.assertIsNone(replacement.session)

    async def test_minimum_run_but_upper_ceiling_stops_immediately(self):
        await self.start()
        await self.acknowledge()
        await self.controller.async_tick(False, None)
        self.assertEqual(len(self.calls), 1)
        self.states["sensor.room"].state = "23"
        await self.controller.async_tick(False, None)
        self.assertEqual(self.calls[-1][1], "set_hvac_mode")
        await self.controller.async_tick()
        self.assertIsNone(self.controller.session)

    async def test_cancel_and_main_mode_stop_bypass_minimum_run(self):
        await self.start()
        self.owner.mode = "observe"
        await self.controller.async_tick(True, 23)
        self.assertEqual(self.calls[-1][2]["hvac_mode"], "off")
        await self.controller.async_tick()
        self.assertIsNone(self.controller.session)

    async def test_runtime_limit_latches_to_avoid_repeated_sessions(self):
        await self.start()
        self.advance(minutes=121)
        await self.controller.async_tick(True, 23)
        await self.controller.async_tick(True, 23)
        self.assertTrue(self.controller.latched)
        self.advance(minutes=21)
        await self.controller.async_tick(True, 23)
        self.assertEqual(len(self.calls), 2)

    async def test_minimum_rest_prevents_immediate_restart(self):
        await self.start()
        await self.acknowledge()
        await self.controller.async_stop()
        await self.controller.async_tick()
        await self.controller.async_tick(True, 23)
        self.assertEqual(self.controller.status, "resting")
        self.assertEqual(len(self.calls), 2)

    async def test_unconfirmed_start_times_out_without_repeated_heat(self):
        async def ignored(domain, name, data, **kwargs):
            self.calls.append((domain, name, data))
        self.hass.services.async_call = ignored
        await self.start()
        self.advance(minutes=3)
        await self.controller.async_tick(True, 23)
        await self.controller.async_tick(True, 23)
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(self.controller.latched)
        self.assertIsNone(self.controller.session)

    async def test_heat_mode_before_target_is_pending_not_manual_override(self):
        async def partial(domain, name, data, **kwargs):
            self.calls.append((domain, name, data))
            self.states["climate.living"].state = "heat"
        self.hass.services.async_call = partial
        await self.start()
        self.advance(seconds=30)
        await self.controller.async_tick(True, 23)
        self.assertIsNotNone(self.controller.session)
        self.assertEqual(self.controller.session["phase"], "starting")
        self.assertFalse(self.controller.latched)
        self.states["climate.living"].attributes["temperature"] = 23
        await self.controller.async_tick(True, 23)
        self.assertEqual(self.controller.status, "running")

    async def test_cancel_during_partial_ack_keeps_journal_until_target_arrives(self):
        async def partial(domain, name, data, **kwargs):
            self.calls.append((domain, name, data))
            self.states["climate.living"].state = "heat"
        self.hass.services.async_call = partial
        await self.start()
        await self.controller.async_mode("off")
        self.assertIsNotNone(self.controller.session)
        self.assertEqual(len(self.calls), 1)
        self.states["climate.living"].attributes["temperature"] = 23
        self.hass.services.async_call = self.service
        await self.controller.async_tick()
        self.assertEqual(self.calls[-1][2]["hvac_mode"], "off")

    async def test_stop_retries_are_bounded_and_unload_waits_for_confirmation(self):
        await self.start()
        await self.acknowledge()
        async def ignored(domain, name, data, **kwargs):
            if domain == "climate":
                self.calls.append((domain, name, data))
        self.hass.services.async_call = ignored
        self.assertFalse(await self.controller.async_prepare_unload())
        for _ in range(4):
            self.advance(minutes=3)
            await self.controller.async_tick()
        self.assertEqual(len(self.calls), 4)
        self.assertEqual(self.controller.status, "recovery_required")
        self.assertFalse(await self.controller.async_prepare_unload())

    async def test_unload_can_confirm_immediate_off(self):
        await self.start()
        await self.acknowledge()
        self.assertTrue(await self.controller.async_prepare_unload())
        self.assertIsNone(self.controller.session)

    async def test_cancel_while_journal_save_pending_cannot_start(self):
        entered, proceed = asyncio.Event(), asyncio.Event()
        original = self.controller.store.async_save
        async def paused(data):
            if data.get("session") and data["session"]["phase"] == "starting":
                entered.set()
                await proceed.wait()
            await original(data)
        self.controller.store.async_save = paused
        task = asyncio.create_task(self.start())
        await entered.wait()
        self.controller.mode = "off"
        proceed.set()
        await task
        self.assertEqual(self.calls, [])
        self.assertIsNone(self.controller.session)

    async def test_water_manual_change_discovered_after_journal_save_blocks_start(self):
        changed = False
        original = self.controller.store.async_save
        async def save(data):
            nonlocal changed
            await original(data)
            if data.get("session"):
                changed = True
        def track(snapshot, now):
            if changed:
                self.owner.manual_hold = True
        self.owner.track_output = track
        self.controller.store.async_save = save
        await self.start()
        self.assertEqual(self.calls, [])
        self.assertIsNone(self.controller.session)
        self.assertTrue(self.owner.manual_hold)

    async def test_restart_cannot_forget_inflight_heat_until_ack_window_expires(self):
        async def ignored(domain, name, data, **kwargs):
            self.calls.append((domain, name, data))
        self.hass.services.async_call = ignored
        await self.start()
        replacement = ac.ACController(self.owner)
        await replacement.async_load()
        await replacement.async_tick()
        self.assertIsNotNone(replacement.session)
        self.assertFalse(await replacement.async_prepare_unload())
        self.states["climate.living"].state = "heat"
        self.states["climate.living"].attributes["temperature"] = 23
        self.hass.services.async_call = self.service
        await replacement.async_tick()
        self.assertEqual(self.calls[-1][2]["hvac_mode"], "off")

    async def test_meter_budget_counts_fresh_samples_and_stops_session(self):
        self.config["ac_power_entity"] = "sensor.ac_power"
        self.config["ac_max_session_kwh"] = 0.1
        self.set_state("sensor.ac_power", 1200, unit_of_measurement="W")
        self.controller = ac.ACController(self.owner)
        self.advance(minutes=21)
        await self.start()
        self.advance(minutes=5)
        await self.controller.async_tick(True, 23)
        self.assertEqual(self.calls[-1][2]["hvac_mode"], "off")
        self.assertTrue(self.controller.latched)
        self.assertAlmostEqual(self.controller.session["energy_kwh"], .1)

    async def test_missing_meter_or_gap_stops_but_no_meter_claims_no_budget(self):
        self.assertFalse(self.controller.attributes()["energy_budget_enforced"])
        self.assertIsNone(self.controller.attributes()["session_energy_kwh"])
        self.config["ac_power_entity"] = "sensor.ac_power"
        await self.start()
        self.assertEqual(self.calls, [])
        self.set_state("sensor.ac_power", 1000, unit_of_measurement="W")
        await self.start()
        self.advance(minutes=11)
        await self.controller.async_tick(True, 23)
        self.assertEqual(self.calls[-1][2]["hvac_mode"], "off")
        self.assertIn("gap", self.controller.reason)

    async def test_corrupt_journal_fails_closed(self):
        self.hass.storage["adaptive_heating.test.ac"] = {"session": {"entity": "climate.living"}}
        replacement = ac.ACController(self.owner)
        await replacement.async_load()
        self.assertTrue(replacement.corrupt_journal)
        with self.assertRaises(HAError):
            await replacement.async_mode("automatic")
        self.assertEqual(replacement.mode, "observe")
        await replacement.async_tick(True, 23)
        self.assertEqual(self.calls, [])
        self.assertFalse(await replacement.async_prepare_unload())

    async def test_restart_pending_rejects_automatic_mode(self):
        self.owner.releases.restart_pending = True
        with self.assertRaises(HAError):
            await self.controller.async_mode("automatic")
        self.assertEqual(self.controller.mode, "observe")
        self.assertEqual(self.calls, [])

    async def test_start_storage_failure_never_sends_heat(self):
        original = self.controller.store.async_save
        async def failed(data):
            if data.get("session"):
                raise OSError("Disk full")
            await original(data)
        self.controller.store.async_save = failed
        await self.start()
        self.assertEqual(self.calls, [])
        self.assertIsNone(self.controller.session)
        self.assertTrue(self.controller.latched)
        self.assertIn("no start", self.controller.reason)

    async def test_runtime_off_survives_storage_failure_and_retains_pending_journal(self):
        await self.start()
        await self.acknowledge()
        original = self.controller.store.async_save
        async def failed(data):
            raise OSError("Disk full")
        self.controller.store.async_save = failed
        self.advance(minutes=121)
        await self.controller.async_tick(True, 23)
        self.assertEqual(self.calls[-1][2]["hvac_mode"], "off")
        await self.controller.async_tick(True, 23)
        self.assertIsNone(self.controller.session)
        self.assertIsNotNone(self.hass.storage["adaptive_heating.test.ac"]["session"])
        self.assertTrue(self.controller.recovery_pending)
        self.assertFalse(await self.controller.async_prepare_unload())
        with self.assertRaises(HAError):
            await self.controller.async_mode("automatic")
        self.controller.store.async_save = original
        await self.controller.async_tick(True, 23)
        self.assertIsNone(self.hass.storage["adaptive_heating.test.ac"]["session"])
        self.assertFalse(self.controller.recovery_pending)
        self.assertTrue(self.controller.latched)
        self.assertEqual(len(self.calls), 2)

    async def test_restart_recovery_still_sends_owned_off_when_storage_fails(self):
        await self.start()
        await self.acknowledge()
        replacement = ac.ACController(self.owner)
        async def failed(data):
            raise OSError("Disk full")
        replacement.store.async_save = failed
        await replacement.async_load()
        await replacement.async_tick()
        self.assertEqual(self.calls[-1][2]["hvac_mode"], "off")
        self.assertEqual(replacement.mode, "observe")
        self.assertTrue(replacement.recovery_pending)


if __name__ == "__main__":
    unittest.main()
