"""Run the actual HA adapter (coordinator.py) against an in-memory HA boundary (no device I/O)."""

import asyncio
from datetime import datetime, timedelta, timezone
import importlib.util
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
    def async_delay_save(self, data_func, delay=0):
        self.hass.storage[self.key] = data_func()
    async def async_remove(self):
        self.hass.storage.pop(self.key, None)


class FakeCoordinator:
    def __init__(self, hass, *args, **kwargs):
        self.hass = hass
        self.data = None
        self.update_interval = kwargs.get("update_interval")
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
        self.now = datetime(2026, 1, 15, 2, tzinfo=timezone.utc)
        self.clock_patch = patch.object(adapter.dt_util, "utcnow", side_effect=lambda: self.now)
        self.clock_patch.start()
        self.states = {}
        self.calls = []
        self.forecast_outdoor = 0.0
        self.forecast_extra = {}
        self.config = {"indoor_entity": "sensor.room", "weather_entity": "weather.house",
                       "output_entity": "number.water", "operating_entity": "sensor.operating",
                       "inlet_entity": "sensor.return_water", "outlet_entity": "sensor.supply_water",
                       "heating_mode_entity": "number.heating_mode", "heating_mode_state": "4"}
        self.set_state("sensor.room", 21.5, unit_of_measurement="°C")
        self.set_state("weather.house", "cloudy", temperature=0, temperature_unit="°C")
        self.set_state("number.water", 25, unit_of_measurement="°C", min=20, max=50, step=1)
        self.set_state("number.heating_mode", "4.0")
        self.set_state("sensor.operating", "OFF")
        self.set_state("sensor.return_water", 24.3, unit_of_measurement="°C")
        self.set_state("sensor.supply_water", 24.0, unit_of_measurement="°C")

        async def service(domain, name, data, **kwargs):
            self.calls.append((domain, name, data))
            if domain == "number":
                self.set_state(data["entity_id"], data["value"], **self.states[data["entity_id"]].attributes)
                return None
            if domain == "weather":
                return {"weather.house": {"forecast": [
                    {"datetime": (self.now.replace(minute=0) + timedelta(hours=i)).isoformat(),
                     "temperature": self.forecast_outdoor, "cloud_coverage": 100} | self.forecast_extra
                    for i in range(48)]}}
            return None
        self.echo = True   # the device shows a written value
        self.fail_writes = False

        async def service_with_device(domain, name, data, **kwargs):
            if domain == "number" and self.fail_writes:
                self.calls.append((domain, name, data))
                raise HAError("device unreachable")
            if domain == "number" and not self.echo:
                self.calls.append((domain, name, data))
                return None
            return await service(domain, name, data, **kwargs)
        self.hass = types.SimpleNamespace(states=types.SimpleNamespace(get=self.states.get),
            storage={}, is_running=True, services=types.SimpleNamespace(async_call=service_with_device))
        self.entry = types.SimpleNamespace(data=self.config, options={}, entry_id="test", title="Test heating")
        self.releases = types.SimpleNamespace(restart_pending=False)
        self.controller = await self.new_controller()

    async def new_controller(self):
        controller = adapter.HeatingCoordinator(self.hass, self.entry, self.releases)
        await controller.async_load()
        return controller

    async def asyncTearDown(self):
        self.clock_patch.stop()

    def set_state(self, entity, value, **attrs):
        self.states[entity] = State(value, self.now, **attrs)

    def writes(self):
        return [call for call in self.calls if call[0] == "number"]

    async def minutes(self, n, **changes):
        for _ in range(n):
            self.now += timedelta(minutes=1)
            for entity, value in changes.items():
                state = self.states[entity]
                self.set_state(entity, value, **state.attributes)
            await self.controller.async_request_refresh()

    # ------------------------------------------------------------------ modes
    async def test_observe_decides_without_actuation(self):
        await self.controller.async_request_refresh()
        data = self.controller.data
        self.assertEqual(self.controller.mode, "observe")
        self.assertEqual(data["status"], "observing")
        self.assertTrue(data["reason"].startswith("Observe: Starting the compressor"))
        self.assertEqual(data["proposed"], 28.0)
        self.assertEqual(data["cycle"], "kick")
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.controller.core.integ, 0.0)  # Observe does not learn

    async def test_one_minute_cadence_and_ten_minute_saves(self):
        self.assertEqual(self.controller.update_interval, timedelta(minutes=1))
        saves = []
        self.controller.store.async_delay_save = lambda func, delay=0: saves.append(self.now)
        await self.minutes(25)
        self.assertEqual(len(saves), 3)

    async def test_off_does_not_step_the_controller(self):
        await self.controller.async_mode("off")
        self.assertEqual(self.controller.data["status"], "off")
        self.assertIsNone(self.controller.core.last_minute)

    async def test_automatic_kicks_a_cold_floor_with_the_smallest_restart_setpoint(self):
        await self.controller.async_mode("automatic")
        # ceil(return 24.3 - 0.8 + restart hysteresis 4 (option default) + 0.15) = 28
        self.assertEqual(self.writes()[-1][2]["value"], 28)
        self.assertEqual(self.controller.data["status"], "command_sent")
        self.assertEqual(self.controller.data["commanded"], 28)
        self.assertEqual(self.controller.data["cycle"], "kick")

    async def test_the_restart_hysteresis_register_is_read_when_mapped(self):
        self.config["restart_hysteresis_entity"] = "number.restart_delta"
        self.set_state("number.restart_delta", 5)
        self.controller = await self.new_controller()
        await self.controller.async_mode("automatic")
        self.assertEqual(self.writes()[-1][2]["value"], 29)
        self.assertNotIn(("number", "set_value", {"entity_id": "number.restart_delta"}), self.calls)
        self.assertTrue(all(call[2]["entity_id"] == "number.water" for call in self.writes()))
        self.set_state("number.restart_delta", "unavailable")
        await self.minutes(1)
        self.assertEqual(self.controller.data["status"], "paused")

    async def test_a_run_rides_then_stops_with_one_write(self):
        await self.controller.async_mode("automatic")
        self.set_state("sensor.operating", "HEAT")
        await self.minutes(2, **{"sensor.return_water": 26.0, "sensor.supply_water": 29.5})
        self.assertEqual(self.controller.data["cycle"], "ride")
        rides = len(self.writes())
        self.assertGreaterEqual(rides, 2)
        # the floor warms far past its target; after the hour minimum the run ends with one write
        await self.minutes(70, **{"sensor.room": 22.6, "sensor.return_water": 34.0, "sensor.supply_water": 37.0})
        stop = self.writes()[-1][2]["value"]
        self.assertLessEqual(stop, 37.0 + 0.3 - 0.8 - 2.1)  # the park value, low enough to stop at once
        self.assertFalse(self.controller.core.run)
        self.assertLess(len(self.writes()) - rides, 6)
        stopped = len(self.writes())
        self.set_state("sensor.operating", "OFF")
        await self.minutes(3, **{"sensor.return_water": 33.5, "sensor.supply_water": 33.7})
        self.assertEqual(len(self.writes()), stopped, "no second write to raise the stop to the park")

    async def test_a_restart_with_unavailable_values_rides_the_run_it_finds(self):
        self.set_state("sensor.operating", "unavailable")
        self.set_state("sensor.return_water", "unavailable")
        await self.controller.async_mode("automatic")
        self.assertFalse(self.controller.in_charge, "no handover on a minute without the unit's values")
        self.set_state("sensor.operating", "HEAT")
        self.set_state("number.water", 29, unit_of_measurement="°C", min=20, max=50, step=1)
        self.set_state("sensor.return_water", 26.0, unit_of_measurement="°C")
        self.set_state("sensor.supply_water", 29.5, unit_of_measurement="°C")
        await self.minutes(1)
        self.assertTrue(self.controller.core.run)
        self.assertNotEqual(self.controller.core.note, "unowned")

    async def test_running_unit_is_adopted_when_automatic_is_selected(self):
        self.set_state("sensor.operating", "HEAT")
        self.set_state("number.water", 30, unit_of_measurement="°C", min=20, max=50, step=1)
        self.set_state("sensor.room", 22.6, unit_of_measurement="°C")
        self.set_state("sensor.return_water", 27.0, unit_of_measurement="°C")
        self.set_state("sensor.supply_water", 30.0, unit_of_measurement="°C")
        await self.minutes(30)   # Observe: the controller's own view says no run is needed
        self.assertFalse(self.controller.core.run)
        await self.controller.async_mode("automatic")
        self.assertTrue(self.controller.core.run)
        self.assertNotEqual(self.controller.core.note, "unowned")

    # ------------------------------------------------------------------ gates
    async def test_hot_water_waits_without_writing(self):
        self.set_state("sensor.operating", "HOT WATER")
        await self.controller.async_mode("automatic")
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.controller.data["cycle"], "wait")

    async def test_disabled_or_unavailable_heating_mode_writes_nothing(self):
        for value in ("3", "unavailable"):
            with self.subTest(value=value):
                self.set_state("number.heating_mode", value)
                await self.controller.async_mode("automatic")
                self.assertEqual(self.writes(), [])
                self.assertEqual(self.controller.data["status"], "paused")

    async def test_without_a_heating_mode_mapping_automatic_explains_itself(self):
        del self.config["heating_mode_entity"]
        self.controller = await self.new_controller()
        await self.controller.async_mode("automatic")
        self.assertEqual(self.writes(), [])
        self.assertIn("heating-mode entity", self.controller.data["reason"])

    async def test_inhibit_and_defrost(self):
        self.controller.config["inhibit_entity"] = "input_boolean.old_controller"
        self.set_state("input_boolean.old_controller", "on")
        await self.controller.async_mode("automatic")
        self.assertEqual(self.writes(), [])
        self.assertIn("Another controller", self.controller.data["reason"])
        self.set_state("input_boolean.old_controller", "off")
        self.controller.config["defrost_entity"] = "binary_sensor.defrost"
        self.set_state("binary_sensor.defrost", "on")
        await self.minutes(1)
        self.assertEqual(self.writes(), [])
        self.set_state("binary_sensor.defrost", "unavailable")
        await self.minutes(1)
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.controller.data["status"], "paused")

    async def test_unit_link_down_holds_and_keeps_the_learning(self):
        await self.controller.async_mode("automatic")
        self.assertTrue(self.controller.core.run)
        count = len(self.writes())
        self.set_state("sensor.return_water", "unavailable")
        await self.minutes(10)
        self.assertEqual(len(self.writes()), count)
        self.assertEqual(self.controller.data["status"], "paused")
        self.assertEqual(self.controller.data["cycle"], "hold")
        self.assertGreater(self.controller.core.integ, 0.0)  # the room is still known: learning goes on
        self.set_state("sensor.return_water", 24.3, unit_of_measurement="°C")
        await self.minutes(1)
        self.assertTrue(self.controller.core.run, "a link drop is not a handover: the run continues")

    async def test_disinfection_pauses_writes(self):
        with patch.object(type(self.controller.disinfection), "blocks_heating", new=True):
            await self.controller.async_mode("automatic")
        self.assertEqual(self.writes(), [])
        self.assertIn("disinfection", self.controller.data["reason"])

    async def test_a_lost_room_sensor_keeps_heating_on_the_fallback_curve_and_alerts(self):
        self.states["sensor.room"].last_reported = self.now - timedelta(hours=5)
        await self.controller.async_mode("automatic")
        self.assertEqual(self.controller.core.room_state, "stale")
        self.assertEqual(self.writes()[-1][2]["value"], 28)
        self.assertIn("learned outdoor curve", self.controller.data["reason"])
        await self.minutes(61)
        notices = [c for c in self.calls if c[0] == "persistent_notification"]
        self.assertEqual([c[1] for c in notices], ["create"])
        await self.minutes(1, **{"sensor.room": 21.6})
        notices = [c for c in self.calls if c[0] == "persistent_notification"]
        self.assertEqual([c[1] for c in notices], ["create", "dismiss"])

    async def test_manual_change_holds_until_explicit_resume(self):
        await self.controller.async_mode("automatic")
        self.set_state("number.water", 35, unit_of_measurement="°C", min=20, max=50, step=1)
        await self.minutes(1)
        self.assertTrue(self.controller.manual_hold)
        self.assertEqual(self.notices("hold"), [("create", "hold")])
        self.assertIn("changed outside", self.controller.data["reason"])
        count = len(self.writes())
        await self.minutes(10)
        self.assertEqual(len(self.writes()), count)
        await self.controller.async_mode("observe")
        self.assertEqual(len(self.writes()), count, "a value set by hand is not replaced when Automatic ends")
        await self.controller.async_mode("automatic")
        self.assertFalse(self.controller.manual_hold)

    def notices(self, kind=None):
        return [(c[1], c[2]["notification_id"].rsplit("_", 1)[-1]) for c in self.calls
                if c[0] == "persistent_notification" and (kind is None or c[2]["notification_id"].endswith(kind))]

    async def test_an_unconfirmed_command_is_asked_again_then_pauses_and_notifies(self):
        self.echo = False
        await self.controller.async_mode("automatic")
        self.assertEqual([c[2]["value"] for c in self.writes()], [28])
        await self.minutes(4)
        self.assertFalse(self.controller.manual_hold, "the device gets five minutes to show the value")
        self.assertEqual(len(self.writes()), 1)
        await self.minutes(2)
        self.assertEqual(len(self.writes()), 2, "the same setpoint is asked once more")
        self.assertFalse(self.controller.manual_hold)
        await self.minutes(6)
        self.assertTrue(self.controller.manual_hold)
        self.assertEqual(self.controller.hold_kind, "unconfirmed")
        self.assertEqual(self.notices("hold"), [("create", "hold")])
        count = len(self.writes())
        await self.minutes(10)
        self.assertEqual(len(self.writes()), count)
        self.echo = True
        await self.controller.async_mode("automatic")
        self.assertFalse(self.controller.manual_hold)
        self.assertEqual(self.notices("hold"), [("create", "hold"), ("dismiss", "hold")])

    async def test_a_late_echo_confirms_the_command(self):
        self.echo = False
        await self.controller.async_mode("automatic")
        await self.minutes(3)
        self.set_state("number.water", 28, unit_of_measurement="°C", min=20, max=50, step=1)
        await self.minutes(10)
        self.assertFalse(self.controller.manual_hold)

    async def test_failed_commands_are_not_counted_and_pause_after_three(self):
        self.fail_writes = True
        await self.controller.async_mode("automatic")
        self.assertEqual(self.controller.data["status"], "paused")
        self.assertIn("trying again", self.controller.data["reason"])
        self.assertEqual(len(self.controller.core.wlog), 0, "a failed write does not spend the budget")
        await self.minutes(2)
        self.assertEqual(len(self.writes()), 3)
        self.assertTrue(self.controller.manual_hold)
        self.assertEqual(self.controller.hold_kind, "failed")
        await self.minutes(5)
        self.assertEqual(len(self.writes()), 3)

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

    async def test_heating_mode_change_during_forecast_blocks_the_write(self):
        original = self.hass.services.async_call
        async def change_mode(domain, name, data, **kwargs):
            if domain == "weather":
                self.set_state("number.heating_mode", 3)
            return await original(domain, name, data, **kwargs)
        self.hass.services.async_call = change_mode
        await self.controller.async_mode("automatic")
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.controller.data["status"], "paused")

    async def test_restart_required_prevents_automatic_mode(self):
        self.releases.restart_pending = True
        with self.assertRaises(HAError):
            await self.controller.async_mode("automatic")

    async def test_fahrenheit_output_is_written_in_its_own_unit(self):
        self.set_state("number.water", 77, unit_of_measurement="°F", min=68, max=122, step=1.8)
        await self.controller.async_mode("automatic")
        self.assertAlmostEqual(self.writes()[0][2]["value"], 82.4)
        self.assertEqual(self.controller.data["commanded"], 28)

    async def test_device_range_bounds_the_controller(self):
        self.set_state("number.water", 25, unit_of_measurement="°C", min=25, max=27, step=1)
        await self.controller.async_mode("automatic")
        self.assertEqual(self.writes()[-1][2]["value"], 27)
        await self.minutes(30)
        self.assertEqual(len(self.writes()), 1, "a value the device cannot take is not written again")
        self.assertEqual((self.controller.core.p.write_min, self.controller.core.p.write_max), (25, 27))

    async def test_maximum_water_caps_every_write(self):
        self.entry.options = {"maximum_water": 27.0}
        self.controller = await self.new_controller()
        await self.controller.async_mode("automatic")
        self.assertEqual(self.writes()[-1][2]["value"], 27)

    # ------------------------------------------------------------------ inputs
    async def test_forecast_hours_carry_sun_from_cloud_cover(self):
        self.hass.config = types.SimpleNamespace(latitude=52.5, longitude=13.4)
        self.now = datetime(2026, 3, 20, 8, tzinfo=timezone.utc)
        self.forecast_extra = {"cloud_coverage": None, "condition": "sunny"}
        await self.controller.async_request_refresh()
        hours = self.controller.forecast_hours
        self.assertEqual(len(hours), 48)
        self.assertGreater(max(h.ghi for h in hours), 300)
        self.assertEqual(self.controller.core.forecast_state, "fresh")
        self.forecast_extra = {"cloud_coverage": None, "condition": "rainy"}
        self.controller.forecast_checked = None
        await self.controller.async_request_refresh()
        cloudy = max(h.ghi for h in self.controller.forecast_hours)
        self.assertLess(cloudy, 0.5 * max(h.ghi for h in hours))

    async def test_forecast_rows_are_labelled_by_their_own_time(self):
        await self.controller.async_request_refresh()
        first = self.controller.forecast_hours[0]
        self.assertEqual(first.minute, self.now.replace(minute=0).timestamp() / 60)

    async def test_a_failed_forecast_fetch_keeps_the_previous_one(self):
        await self.controller.async_request_refresh()
        hours, cache = self.controller.forecast_hours, list(self.controller.forecast_cache)
        original = self.hass.services.async_call
        async def broken(domain, name, data, **kwargs):
            if domain == "weather":
                raise HAError("provider down")
            return await original(domain, name, data, **kwargs)
        self.hass.services.async_call = broken
        self.now += timedelta(minutes=31)
        await self.controller.async_request_refresh()
        self.assertEqual(self.controller.forecast_hours, hours)
        self.assertEqual(self.controller.forecast_cache, cache)
        self.assertEqual(self.controller.core.forecast_state, "fresh")
        self.hass.services.async_call = original
        self.now += timedelta(minutes=5)
        checked = self.controller.forecast_checked
        await self.controller.async_request_refresh()
        self.assertGreater(self.controller.forecast_checked, checked, "a failed fetch is retried after 5 minutes")

    async def test_a_one_minute_room_dropout_keeps_the_last_value(self):
        # warm room, floor at 24.9: no run is wanted
        self.set_state("sensor.room", 24.1, unit_of_measurement="°C")
        self.set_state("sensor.return_water", 24.9, unit_of_measurement="°C")
        self.set_state("sensor.supply_water", 24.6, unit_of_measurement="°C")
        await self.controller.async_mode("automatic")
        await self.minutes(5)
        target = self.controller.core.ts_star
        count = len(self.writes())
        self.set_state("sensor.room", "unavailable")
        await self.minutes(1)
        self.assertEqual(self.controller.core.room_state, "ok")
        self.assertAlmostEqual(self.controller.core.ts_star, target, delta=0.1)
        self.assertFalse(self.controller.core.run)
        self.assertEqual(len(self.writes()), count)
        self.states["sensor.room"] = State(24.1, self.now - timedelta(hours=5), unit_of_measurement="°C")
        self.states["sensor.room"].state = "unavailable"
        self.controller.room_last = (24.1, self.now - timedelta(hours=5))
        await self.minutes(1)
        self.assertEqual(self.controller.core.room_state, "stale", "a value lost for hours is not used")

    async def test_an_unmapped_operating_state_waits_and_a_defrost_label_is_a_defrost(self):
        self.set_state("sensor.operating", "ANTIFREEZE")
        await self.controller.async_mode("automatic")
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.controller.data["cycle"], "wait")
        self.assertIn("not mapped", self.controller.data["reason"])
        self.assertEqual(self.controller.core.since_def, 0.0)
        self.set_state("sensor.operating", "Defrosting")
        await self.minutes(1)
        self.assertEqual(self.controller.data["cycle"], "wait")
        self.assertEqual(self.controller.core.note, "defrost")

    async def test_daily_forecast_is_rejected(self):
        original = self.hass.services.async_call
        async def daily(domain, name, data, **kwargs):
            if domain == "weather":
                return {"weather.house": {"forecast": [
                    {"datetime": (self.now + timedelta(days=i)).isoformat(), "temperature": 0} for i in range(7)]}}
            return await original(domain, name, data, **kwargs)
        self.hass.services.async_call = daily
        await self.controller.async_request_refresh()
        self.assertEqual(self.controller.forecast_hours, ())
        self.assertEqual(self.controller.core.forecast_state, "none")

    async def test_solar_surplus_raises_the_target_and_pauses_learning(self):
        for key, entity, value in (("pv_entity", "sensor.pv", 4000), ("import_entity", "sensor.import", 0),
                                   ("export_entity", "sensor.export", 1800)):
            self.controller.config[key] = entity
            self.set_state(entity, value, unit_of_measurement="W")
        self.controller.settings.solar_preheat = True
        await self.controller.async_mode("automatic")
        for index in range(16):
            await self.minutes(1, **{"sensor.pv": 4000, "sensor.import": 0, "sensor.export": 1800})
        self.assertTrue(self.controller.data["surplus"])
        integ = self.controller.core.integ
        await self.minutes(5, **{"sensor.pv": 4000, "sensor.import": 0, "sensor.export": 1800})
        self.assertEqual(self.controller.core.integ, integ)
        self.assertEqual(self.controller.core.parts["target"], 22.3)
        self.assertIn("solar surplus", self.controller.data["reason"])

    def test_ac_is_asked_only_while_the_floor_heats_and_the_room_is_clearly_cold(self):
        c = self.controller
        c.mode = "automatic"
        c.core.run, c.core.e = True, 1.2
        self.assertTrue(c.ac_request()[0])
        c.core.e = 0.5
        self.assertFalse(c.ac_request()[0])
        c.core.run, c.core.e = False, 2.0
        self.assertFalse(c.ac_request()[0])
        c.core.run, c.core.e = True, None   # room unknown: never borrow the AC
        self.assertFalse(c.ac_request()[0])
        c.mode, c.core.e = "observe", 2.0
        self.assertFalse(c.ac_request()[0])

    async def test_an_assistance_session_shields_the_floor_and_stops_learning(self):
        self.controller.ac.session = {"phase": "running", "entity": "climate.living"}
        self.set_state("sensor.room", 23.0, unit_of_measurement="°C")
        with patch.object(type(self.controller.ac), "blocks_learning", return_value=True):
            await self.controller.async_mode("automatic")
        self.assertEqual(self.controller.core.parts["room"], 0.0)
        self.assertEqual(self.controller.core.integ, 0.0)

    # ------------------------------------------------------------------ storage
    async def test_restart_keeps_target_learning_and_automatic(self):
        await self.controller.async_target(23)
        await self.controller.async_mode("automatic")
        await self.minutes(30)
        integ, writes = self.controller.core.integ, len(self.controller.core.wlog)
        self.assertGreater(integ, 0)
        before = len(self.writes())
        await self.controller.async_stop()   # Home Assistant stops: saved, nothing written
        self.assertEqual(len(self.writes()), before)
        other = await self.new_controller()
        self.assertEqual(other.settings.target, 23)
        self.assertEqual(other.mode, "automatic")
        self.assertFalse(other.release_pending)
        self.assertEqual(other.core.integ, integ)
        self.assertEqual(len(other.core.wlog), writes)
        self.assertEqual(other.core.room_since, self.controller.core.room_since)

    async def test_a_new_version_or_changed_options_start_in_observe_and_hand_back(self):
        for change in ("version", "options"):
            with self.subTest(change=change):
                self.hass.storage, self.calls[:] = {}, []
                self.entry.options = {}
                self.controller = await self.new_controller()
                await self.controller.async_mode("automatic")
                self.assertEqual(self.writes()[-1][2]["value"], 28)   # a kick is on the unit
                await self.controller.async_save()
                if change == "version":
                    self.hass.storage["adaptive_heating.test"]["version"] = "0.5.9"
                else:
                    self.entry.options = {"maximum_water": 45.0}
                other = await self.new_controller()
                self.assertEqual(other.mode, "observe")
                self.assertTrue(other.release_pending)
                self.controller = other
                await self.minutes(1)
                self.assertEqual(self.controller.data["status"], "observing")
                left = self.writes()[-1][2]["value"]
                self.assertLess(left - (24.3 - 0.8), 4.0, "the kick is replaced by an idle setpoint")
                await self.minutes(5)
                self.assertEqual(self.writes()[-1][2]["value"], left)

    async def test_a_manual_hold_does_not_resume_after_a_restart(self):
        await self.controller.async_mode("automatic")
        self.set_state("number.water", 35, unit_of_measurement="°C", min=20, max=50, step=1)
        await self.minutes(1)
        await self.controller.async_stop()
        other = await self.new_controller()
        self.assertEqual(other.mode, "observe")

    async def test_leaving_automatic_hands_back_the_idle_setpoint(self):
        await self.controller.async_mode("automatic")
        self.assertEqual(self.writes()[-1][2]["value"], 28)   # kick
        await self.controller.async_mode("observe")
        left = self.writes()[-1][2]["value"]
        self.assertLess(left, 28)
        self.assertLess(left - (24.3 - 0.8), 4.0, "the unit must not start on the setpoint left behind")
        self.assertFalse(self.controller.manual_hold)
        count = len(self.writes())
        await self.minutes(10)
        await self.controller.async_mode("off")
        self.assertEqual(len(self.writes()), count, "Observe and Off write nothing more")

    async def test_unload_hands_back_but_not_under_another_controller(self):
        await self.controller.async_mode("automatic")
        self.set_state("sensor.operating", "HEAT")
        await self.minutes(5, **{"sensor.return_water": 27.0, "sensor.supply_water": 31.0})
        riding = self.writes()[-1][2]["value"]
        self.assertTrue(await self.controller.async_prepare_unload())
        left = self.writes()[-1][2]["value"]
        self.assertLess(left, riding)
        self.assertEqual(self.hass.storage["adaptive_heating.test"]["resume"], "automatic")
        self.controller = await self.new_controller()
        await self.controller.async_mode("automatic")
        self.controller.config["inhibit_entity"] = "input_boolean.old_controller"
        self.set_state("input_boolean.old_controller", "on")
        count = len(self.writes())
        await self.controller.async_mode("observe")
        self.assertEqual(len(self.writes()), count)

    async def test_an_update_restart_hands_back_at_stop(self):
        await self.controller.async_mode("automatic")
        count = len(self.writes())
        self.releases.restart_pending = True
        await self.controller.async_stop()
        self.assertEqual(len(self.writes()), count + 1)
        self.assertLess(self.writes()[-1][2]["value"], 28)

    async def test_another_room_sensor_starts_learning_again(self):
        self.controller.core.integ = 2.0
        await self.controller.async_save()
        self.entry.options = {"indoor_entity": "sensor.another_room"}
        other = await self.new_controller()
        self.assertEqual(other.core.integ, 0.0)

    async def test_a_0_5_store_is_migrated(self):
        self.hass.storage = {
            "adaptive_heating.test": {"identity": "old", "model_revision": 3, "model": {"loss": 0.02},
                                      "target": 22.4, "configured_target": 22.0, "cooldown": {}, "estimate2": {"slab": 23}},
            "adaptive_heating.test.learning": {"identity": "old", "house": {}, "log": {"rows": []}},
        }
        controller = await self.new_controller()
        self.assertEqual(controller.settings.target, 22.4)
        self.assertNotIn("adaptive_heating.test.learning", self.hass.storage)
        stored = self.hass.storage["adaptive_heating.test"]
        self.assertEqual(stored["schema"], 2)
        self.assertEqual(stored["target"], 22.4)
        self.assertEqual(stored["controller"]["integ"], 0.0)
        self.assertNotIn("model", stored)

    async def test_a_target_from_another_configured_default_is_not_restored(self):
        self.hass.storage = {"adaptive_heating.test": {"target": 24.0, "configured_target": 21.0}}
        controller = await self.new_controller()
        self.assertEqual(controller.settings.target, 22.0)

    def test_upgrade_stored_handles_any_shape(self):
        self.assertEqual(adapter.upgrade_stored(None, 22.0), (None, None))
        self.assertEqual(adapter.upgrade_stored({"schema": 2, "target": 50, "configured_target": 22.0,
                                                 "controller": {"integ": 1}}, 22.0), (None, {"integ": 1}))
        self.assertEqual(adapter.upgrade_stored({"target": 21.5, "configured_target": 22.0, "controller": {"x": 1}}, 22.0),
                         (21.5, None))


if __name__ == "__main__":
    unittest.main()
