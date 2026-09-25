"""Offline dashboard compatibility and optional cold-night/AC presentation."""

import importlib.util
import itertools
import json
from pathlib import Path
import re
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dashboard_builder", ROOT / "scripts" / "build_dashboard.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
EXAMPLE = json.loads((ROOT / "docs" / "dashboard-mapping.example.json").read_text())
OPTIONAL = ("planner_status", "ac_status", "ac_mode", "ac_power", "ac_energy")
HAS_HA = importlib.util.find_spec("homeassistant") is not None


def mapping_with(*keys):
    return {**EXAMPLE, "entities": {key: value for key, value in EXAMPLE["entities"].items()
                                  if key not in OPTIONAL or key in keys}}


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


class DashboardMappings(unittest.TestCase):
    def test_existing_mapping_keeps_existing_views_without_new_references(self):
        dashboard = builder.build(mapping_with())
        self.assertEqual([view["path"] for view in dashboard["views"]], ["0", "adaptive-heating", "equipment"])
        self.assertEqual([len(view["sections"]) for view in dashboard["views"]], [3, 3, 3])
        text = json.dumps(dashboard)
        self.assertNotRegex(text, r"@[a-z_]+@")
        for key in OPTIONAL:
            self.assertNotIn(EXAMPLE["entities"][key], text)

    def test_each_optional_mapping_can_be_used_independently(self):
        # Partial mappings are useful during upgrades and for homes without AC
        # metering. No subset may leave a placeholder or an empty graph behind.
        for count in range(len(OPTIONAL) + 1):
            for keys in itertools.combinations(OPTIONAL, count):
                with self.subTest(keys=keys):
                    dashboard = builder.build(mapping_with(*keys))
                    text = json.dumps(dashboard)
                    self.assertNotRegex(text, r"@[a-z_]+@")
                    self.assertNotIn("custom:", text)
                    for key in OPTIONAL:
                        if key in keys:
                            self.assertIn(EXAMPLE["entities"][key], text)
                        else:
                            self.assertNotIn(EXAMPLE["entities"][key], text)
                    for card in walk(dashboard):
                        if card.get("type") == "history-graph":
                            self.assertTrue(card["entities"])

    def test_new_panel_controls_only_the_integration_mode(self):
        dashboard = builder.build(mapping_with(*OPTIONAL))
        panel = dashboard["views"][0]["sections"][-1]
        self.assertEqual(panel["cards"][0]["heading"], "Cold-night preparation")
        mode = next(card for card in panel["cards"] if card.get("entity") == EXAMPLE["entities"]["ac_mode"])
        self.assertEqual(mode["features"], [{"type": "select-options", "style": "dropdown"}])
        self.assertNotIn("perform-action", json.dumps(panel))
        self.assertIn("full afternoon-and-night consumption", json.dumps(panel))


@unittest.skipUnless(HAS_HA, "Home Assistant runtime is not installed in this worker")
class DashboardTemplates(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from homeassistant.core import HomeAssistant
        self.temp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.temp.name)
        dashboard = builder.build(mapping_with(*OPTIONAL))
        panel = dashboard["views"][0]["sections"][-1]
        self.templates = [card["content"] for card in panel["cards"] if card["type"] == "markdown"]

    async def asyncTearDown(self):
        await self.hass.async_stop()
        self.temp.cleanup()

    def render(self):
        from homeassistant.helpers.template import Template
        return "\n".join(str(Template(content, self.hass).async_render(parse_result=False)) for content in self.templates)

    async def test_missing_entities_and_attributes_do_not_invent_measurements(self):
        content = self.render()
        self.assertIn("Waiting for planner", content)
        self.assertIn("Waiting for AC controller", content)
        self.assertNotIn("None", content)
        self.assertNotIn("0.0 °C", content)
        self.hass.states.async_set(EXAMPLE["entities"]["planner_status"], "observing", {"prepare_at": "invalid"})
        self.hass.states.async_set(EXAMPLE["entities"]["ac_status"], "observe")
        content = self.render()
        self.assertIn("Waiting for an explanation", content)
        self.assertNotIn("None", content)

    async def test_planner_values_and_optional_times_render_with_real_ha(self):
        self.hass.states.async_set(EXAMPLE["entities"]["planner_status"], "preparing", {
            "reason": "Preparing before a cold night", "effective_target": 22.8,
            "predicted_minimum": 20.4, "cooling_rate": 0.2, "calibrated": True,
            "forecast_hours": 24, "prepare_at": "2026-01-15T13:00:00+00:00",
            "night_start": "2026-01-15T21:00:00+00:00",
            "recovery_at": "2026-01-16T06:00:00+00:00",
            "morning_at": "2026-01-16T09:00:00+00:00",
        })
        self.hass.states.async_set(EXAMPLE["entities"]["ac_status"], "heating", {
            "reason": "Assisting preparation", "commanded_target": 23,
            "external_room_temperature": 21.5, "deadline": 1768503600,
            "energy_budget_note": "Measured session budget",
        })
        content = self.render()
        for value in ("22.8 °C", "20.4 °C", "0.2 °C/h", "24.0 hours", "calibrated from observations",
                      "Preparation from", "Night begins", "Recovery from", "Morning planning boundary", "Assisting preparation",
                      "23.0 °C", "21.5 °C", "Session ends by", "Measured session budget"):
            self.assertIn(value, content)
        self.assertNotIn("None", content)
        self.assertIsNone(re.search(r"@[a-z_]+@", content))


if __name__ == "__main__":
    unittest.main()
