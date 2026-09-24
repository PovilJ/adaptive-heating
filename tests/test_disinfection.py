"""Exercise tank-cycle policy and recovery without any physical device I/O."""

import asyncio
from datetime import timedelta
import unittest

from common import module
import test_adapter as boundary

adapter = boundary.adapter
HAError = boundary.HAError

policy = module("disinfection")


class HoldPolicy(unittest.TestCase):
    def test_five_minutes_requires_elapsed_fresh_reports(self):
        hold, settings = policy.TemperatureHold(), policy.DisinfectionSettings()
        self.assertFalse(hold.observe(1000, 1000, 65, settings))
        for _ in range(50):
            self.assertFalse(hold.observe(1010, 1000, 65, settings))
        for seconds in range(30, 300, 30):
            self.assertFalse(hold.observe(1000 + seconds, 1000 + seconds, 65, settings))
        self.assertTrue(hold.observe(1300, 1300, 65, settings))

    def test_dip_missing_data_and_gap_reset_continuity(self):
        for interruption in ((1120, 1120, 64.9), (1120, 1120, None), (1250, 1250, 66), (1250, 1060, 66)):
            hold, settings = policy.TemperatureHold(), policy.DisinfectionSettings()
            hold.observe(1000, 1000, 66, settings)
            hold.observe(1060, 1060, 66, settings)
            self.assertFalse(hold.observe(*interruption, settings))
            self.assertEqual(hold.seconds, 0)

    def test_invalid_settings_rejected(self):
        for values in ({"disinfection_target": 64}, {"disinfection_hold_minutes": 0},
                       {"disinfection_min_days": 17}, {"disinfection_timeout_hours": float("nan")},
                       {"disinfection_sample_seconds": 1000},
                       {"disinfection_timeout_hours": .25, "disinfection_hold_minutes": 20}):
            with self.assertRaises(ValueError):
                policy.DisinfectionSettings(**values)

    def test_deadline_overrides_preferences_but_first_cycle_needs_baseline(self):
        args = dict(now=20 * 86400, last_success=None, indoor=18, room_target=22, comfort_band=.3,
                    tank=40, hot_water=False, outdoor=-5, forecast=[], local_hour=2,
                    surplus=False, battery_ready=False)
        settings = policy.DisinfectionSettings()
        self.assertFalse(policy.schedule(settings, **args)[0])
        args["last_success"] = 86400
        self.assertTrue(policy.schedule(settings, **args)[0])
        args["last_success"] = 8 * 86400
        self.assertFalse(policy.schedule(settings, **args)[0])
        args.update(indoor=22, surplus=True, battery_ready=True)
        self.assertTrue(policy.schedule(settings, **args)[0])
        args["last_success"] = 21 * 86400
        self.assertFalse(policy.schedule(settings, **args)[0])

    def test_existing_hot_water_and_warmer_forecast_windows(self):
        args = dict(now=13 * 86400, last_success=0, indoor=22, room_target=22, comfort_band=.3,
                    tank=52, hot_water=True, outdoor=5, forecast=[], local_hour=3,
                    surplus=False, battery_ready=True)
        settings = policy.DisinfectionSettings()
        self.assertTrue(policy.schedule(settings, **args)[0])
        args.update(hot_water=False, local_hour=13, forecast=[9])
        self.assertFalse(policy.schedule(settings, **args)[0])
        args["forecast"] = [6]
        self.assertTrue(policy.schedule(settings, **args)[0])


class TankBoundary(unittest.IsolatedAsyncioTestCase):
    set_state = boundary.ControllerBoundary.set_state
    writes = boundary.ControllerBoundary.writes

    async def asyncSetUp(self):
        await boundary.ControllerBoundary.asyncSetUp(self)
        self.config.update(tank_temperature_entity="sensor.tank", tank_target_entity="number.tank")
        self.set_state("sensor.tank", 40, unit_of_measurement="°C")
        self.set_state("number.tank", 52, unit_of_measurement="°C", min=40, max=80, step=1)
        original_service = self.hass.services.async_call

        async def service(domain, name, data, **kwargs):
            if domain == "number" and data["entity_id"] == "number.tank":
                # The recovery journal must exist before both boost and restoration.
                self.assertIsNotNone(self.hass.storage["adaptive_heating.test.disinfection"]["cycle"])
                self.calls.append((domain, name, data))
                self.set_state("number.tank", data["value"], **self.states["number.tank"].attributes)
                return
            if domain == "persistent_notification":
                self.calls.append((domain, name, data))
                return
            return await original_service(domain, name, data, **kwargs)

        self.hass.services.async_call = service
        self.controller = adapter.HeatingCoordinator(self.hass, self.entry, self.releases)
        await self.controller.async_load()
        self.dhw = self.controller.disinfection

    async def asyncTearDown(self):
        await boundary.ControllerBoundary.asyncTearDown(self)

    async def start(self):
        await self.controller.async_disinfection_mode("automatic")
        await self.controller.async_disinfection_run()
        await self.controller.async_disinfection_tick()

    async def sample(self, value=65, seconds=30):
        self.now += timedelta(seconds=seconds)
        self.set_state("sensor.tank", value, unit_of_measurement="°C")
        await self.controller.async_disinfection_tick()

    async def test_observe_and_unconfigured_never_boost(self):
        await self.controller.async_request_refresh()
        self.assertEqual(self.writes(), [])
        with self.assertRaises(HAError):
            await self.controller.async_disinfection_run()
        self.controller.config["tank_target_entity"] = ""
        await self.controller.async_disinfection_mode("automatic")
        self.assertEqual(self.writes(), [])

    async def test_complete_hold_and_confirm_restoration(self):
        await self.start()
        self.assertEqual(self.writes()[0][2], {"entity_id": "number.tank", "value": 68})
        await self.sample()
        for _ in range(9):
            await self.sample()
            self.assertIsNone(self.dhw.last_success)
        await self.sample()
        self.assertEqual(self.dhw.status, "restoring")
        self.assertIsNone(self.dhw.last_success)
        self.assertEqual(self.writes()[-1][2]["value"], 52)
        await self.controller.async_disinfection_tick()
        self.assertEqual(self.dhw.status, "completed")
        self.assertIsNotNone(self.dhw.last_success)
        self.assertIsNone(self.dhw.cycle)

    async def test_hold_dip_restarts_full_duration(self):
        await self.start()
        for _ in range(8):
            await self.sample()
        await self.sample(64)
        self.assertEqual(self.dhw.hold.seconds, 0)
        for _ in range(10):
            await self.sample()
        self.assertEqual(self.dhw.status, "holding")
        self.assertIsNone(self.dhw.last_success)
        await self.sample()
        self.assertEqual(self.dhw.status, "restoring")

    async def test_stale_sensor_aborts_and_restores_without_success(self):
        await self.start()
        await self.sample()
        self.now += timedelta(seconds=100)
        await self.controller.async_disinfection_tick()
        await self.controller.async_disinfection_tick()
        self.assertIsNone(self.dhw.last_success)
        self.assertEqual(self.dhw.status, "failed")
        self.assertEqual(self.states["number.tank"].state, "52.0")

    async def test_timeout_restores_and_latches_failure(self):
        await self.start()
        await self.sample(40, seconds=4 * 3600)
        await self.controller.async_disinfection_tick()
        self.assertEqual(self.dhw.status, "timed_out")
        self.assertTrue(self.dhw.latched)
        await self.controller.async_disinfection_tick()
        self.assertEqual(self.dhw.status, "attention_required")
        self.assertEqual(len(self.writes()), 2)

    async def test_restart_recovers_target_and_never_resumes_hold(self):
        await self.start()
        await self.sample()
        await self.sample()
        other = adapter.HeatingCoordinator(self.hass, self.entry, self.releases)
        await other.async_load()
        self.assertEqual(other.disinfection.mode, "observe")
        self.assertEqual(other.disinfection.hold.seconds, 0)
        await other.async_disinfection_tick()
        await other.async_disinfection_tick()
        self.assertEqual(other.disinfection.status, "interrupted")
        self.assertEqual(self.states["number.tank"].state, "52.0")
        self.assertIsNone(other.disinfection.last_success)

    async def test_manual_tank_change_is_never_overwritten(self):
        await self.start()
        self.set_state("number.tank", 54, unit_of_measurement="°C", min=40, max=80, step=1)
        await self.controller.async_disinfection_tick()
        self.assertEqual(self.dhw.status, "manual_override")
        self.assertEqual(len(self.writes()), 1)
        self.assertIsNone(self.dhw.last_success)

    async def test_duplicate_run_and_space_heating_are_blocked(self):
        await self.start()
        with self.assertRaises(HAError):
            await self.controller.async_disinfection_run()
        await self.controller.async_mode("automatic")
        self.assertEqual(self.controller.data["status"], "paused")
        self.assertIsNone(self.controller.model.emitter)
        self.assertEqual(self.controller.model.samples, 0)
        self.assertEqual(len(self.writes()), 1)

    async def test_fahrenheit_and_out_of_bounds(self):
        self.set_state("number.tank", 125.6, unit_of_measurement="°F", min=104, max=176, step=1.8)
        await self.start()
        self.assertAlmostEqual(self.writes()[0][2]["value"], 154.4)
        await self.controller.async_disinfection_cancel()
        await self.controller.async_disinfection_tick()
        self.assertAlmostEqual(float(self.states["number.tank"].state), 125.6)

    async def test_invalid_hardware_step_and_limits_prevent_writes(self):
        self.dhw.mode = "automatic"
        for attrs in ({"min": 40, "max": 60, "step": 1}, {"min": 40, "max": 80, "step": 3}):
            self.set_state("number.tank", 52, unit_of_measurement="°C", **attrs)
            with self.assertRaises(HAError):
                await self.controller.async_disinfection_run()
        self.assertEqual(self.writes(), [])

    async def test_failed_restore_is_bounded_and_manual_retry_works(self):
        await self.start()
        working_service = self.hass.services.async_call
        async def fail(domain, name, data, **kwargs):
            if domain == "number":
                self.calls.append((domain, name, data))
                raise HAError("offline")
            return await working_service(domain, name, data, **kwargs)
        self.hass.services.async_call = fail
        await self.controller.async_disinfection_cancel()
        for _ in range(3):
            self.now += timedelta(seconds=121)
            await self.controller.async_disinfection_tick()
        self.assertEqual(self.dhw.status, "recovery_required")
        self.assertTrue(self.dhw.blocks_heating)
        self.assertEqual(len(self.writes()), 4)
        await self.controller.async_disinfection_tick()
        self.assertEqual(len(self.writes()), 4)
        self.hass.services.async_call = working_service
        await self.controller.async_disinfection_cancel()
        await self.controller.async_disinfection_tick()
        self.assertIsNone(self.dhw.cycle)

    async def test_unacknowledged_boost_and_cancel_wait_out_inflight_window(self):
        working_service = self.hass.services.async_call
        async def no_ack(domain, name, data, **kwargs):
            if domain == "number":
                self.calls.append((domain, name, data))
                return
            return await working_service(domain, name, data, **kwargs)
        self.hass.services.async_call = no_ack
        await self.start()
        await self.controller.async_disinfection_cancel()
        self.assertIsNotNone(self.dhw.cycle)
        self.now += timedelta(seconds=121)
        await self.controller.async_disinfection_tick()
        self.assertEqual(self.dhw.status, "cancelled")
        self.assertIsNone(self.dhw.last_success)

    async def test_mapping_change_recovery_uses_old_target_not_new_house(self):
        await self.start()
        self.entry.options = {"tank_target_entity": "number.another_tank"}
        self.set_state("number.another_tank", 45, unit_of_measurement="°C", min=40, max=80, step=1)
        other = adapter.HeatingCoordinator(self.hass, self.entry, self.releases)
        await other.async_load()
        await other.async_disinfection_tick()
        self.assertEqual(self.writes()[-1][2]["entity_id"], "number.tank")
        self.assertEqual(self.states["number.another_tank"].state, "45")

    async def test_mode_change_while_journal_saves_cancels_before_boost(self):
        entered, proceed = asyncio.Event(), asyncio.Event()
        original_save = self.dhw.store.async_save
        async def delayed(data):
            if data["cycle"]:
                entered.set()
                await proceed.wait()
            await original_save(data)
        self.dhw.store.async_save = delayed
        self.dhw.mode = "automatic"
        running = asyncio.create_task(self.controller.async_disinfection_run())
        await entered.wait()
        cancelling = asyncio.create_task(self.controller.async_disinfection_mode("observe"))
        await asyncio.sleep(0)
        proceed.set()
        await asyncio.gather(running, cancelling)
        self.assertEqual(self.writes(), [])

    async def test_deadline_cannot_bypass_inhibit_or_defrost(self):
        self.dhw.last_success = self.now.timestamp() - 17 * 86400
        for key in ("inhibit_entity", "defrost_entity"):
            self.controller.config[key] = "binary_sensor.block"
            self.set_state("binary_sensor.block", "on")
            await self.controller.async_disinfection_mode("automatic")
            self.assertEqual(self.dhw.status, "blocked")
            self.assertEqual(self.writes(), [])
            self.controller.config[key] = ""

    async def test_unload_restores_and_old_store_does_not_require_new_mappings(self):
        await self.start()
        self.assertTrue(await self.controller.async_prepare_unload())
        self.assertEqual(self.states["number.tank"].state, "52.0")
        self.assertIsNone(self.dhw.cycle)


if __name__ == "__main__":
    unittest.main()
