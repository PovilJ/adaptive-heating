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


if __name__ == "__main__":
    unittest.main()
