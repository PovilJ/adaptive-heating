"""Offline checks for the tabbed dashboard generator."""

import importlib.util
import itertools
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dashboard_builder", ROOT / "scripts" / "build_dashboard.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
EXAMPLE = json.loads((ROOT / "docs" / "dashboard-mapping.example.json").read_text())
E = EXAMPLE["entities"]
OPTIONAL = ("planner_status", "ac_status", "ac_mode", "ac_power", "ac_energy")
TEMPLATE_KEYS = ("primary", "secondary", "content", "icon_color")
HAS_HA = importlib.util.find_spec("homeassistant") is not None


def mapping_with(*keys):
    return {**EXAMPLE, "entities": {key: value for key, value in E.items()
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
    def test_tabs_have_stable_paths_and_icons(self):
        views = builder.build(EXAMPLE)["views"]
        self.assertEqual([view["path"] for view in views], ["home", "trends", "plan", "water", "system"])
        self.assertTrue(all(view["icon"].startswith("mdi:") for view in views))

    def test_missing_required_mapping_is_reported(self):
        with self.assertRaisesRegex(ValueError, "target"):
            builder.build({"entities": {key: value for key, value in E.items() if key != "target"}})

    def test_each_optional_mapping_can_be_used_independently(self):
        # Partial mappings are useful during upgrades and for homes without AC
        # metering. No subset may leave a placeholder or an empty card behind.
        for count in range(len(OPTIONAL) + 1):
            for keys in itertools.combinations(OPTIONAL, count):
                with self.subTest(keys=keys):
                    dashboard = builder.build(mapping_with(*keys))
                    text = json.dumps(dashboard)
                    self.assertNotRegex(text, r"@[a-z_]+@")
                    for key in OPTIONAL:
                        (self.assertIn if key in keys else self.assertNotIn)(E[key], text)
                    for card in walk(dashboard):
                        if "cards" in card or "entities" in card:
                            self.assertTrue(all(card.get("cards", [1])) and card.get("entities", [1]))

    def test_home_never_operates_equipment_and_disinfection_asks_first(self):
        home, _, _, water, _ = builder.build(EXAMPLE)["views"]
        self.assertNotIn("perform-action", json.dumps(home))
        run = next(card["tap_action"] for card in walk(water)
                   if card.get("tap_action", {}).get("target", {}).get("entity_id") == E["disinfection_run"])
        self.assertIn("confirmation", run)


@unittest.skipUnless(HAS_HA, "Home Assistant runtime is not installed in this worker")
class DashboardTemplates(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from homeassistant.core import HomeAssistant
        self.temp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.temp.name)

    async def asyncTearDown(self):
        await self.hass.async_stop()
        self.temp.cleanup()

    def render(self):
        from homeassistant.helpers.template import Template
        return "\n".join(str(Template(value, self.hass).async_render(parse_result=False))
                         for card in walk(builder.build(EXAMPLE))
                         for key, value in card.items() if key in TEMPLATE_KEYS and isinstance(value, str))

    async def test_missing_entities_do_not_invent_measurements(self):
        content = self.render()
        self.assertNotIn("None", content)
        self.assertNotIn("0.0 °C", content)
        self.assertIn("Controller unavailable", content)

    async def test_live_values_render(self):
        set_state = self.hass.states.async_set
        set_state(E["indoor"], "21.3")
        set_state(E["target"], "22.5")
        set_state(E["mode"], "automatic")
        set_state(E["output"], "27")
        set_state(E["limited"], "29")
        set_state(E["operating"], "OFF")
        set_state(E["status"], "command_sent", {"heating_enabled": True, "observed_room_cooling_celsius_per_hour": .2})
        set_state(E["planner_status"], "prepare", {"effective_target": 22.8, "prepare_at": "invalid"})
        content = self.render()
        for expected in ("21.3 °C", "Target 22.5° · 1.2° below ↘", "blue", "Compressor resting",
                         "Water target · next 29.0°", "Preheating the floor", "22.8 °C"):
            self.assertIn(expected, content)
        self.assertNotIn("None", content)
        set_state(E["mode"], "observe")
        self.assertIn("suggests 29.0°", self.render())
        set_state(E["status"], "unavailable")
        self.assertIn("Water target · controller unavailable", self.render())


if __name__ == "__main__":
    unittest.main()
