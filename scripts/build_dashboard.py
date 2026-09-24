#!/usr/bin/env python3
"""Build a portable Lovelace dashboard from explicitly mapped house entities.

This only writes JSON. It never connects to Home Assistant or changes equipment.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def build(mapping):
    e = mapping["entities"]
    url = mapping.get("url_path", "dashboard-heating")
    notes = mapping.get("notes", {})
    required = ("indoor", "weather", "operating", "output", "status", "reason",
                "proposed", "limited", "commanded", "actual", "prediction", "samples",
                "error", "mode", "target", "evaluate", "energy")
    missing = [key for key in required if not e.get(key)]
    if missing:
        raise ValueError("Missing entity mappings: " + ", ".join(missing))

    def render(text):
        for key, entity_id in e.items():
            text = text.replace("@" + key + "@", entity_id)
        return text

    def styled(card, accent=None):
        style = "ha-card { border-radius: 20px; box-shadow: none; overflow: hidden; }"
        if accent:
            style += ("\nha-card { background: linear-gradient(135deg, rgba(" + accent + ", .13), "
                      "var(--ha-card-background, var(--card-background-color))) ; }")
        card["card_mod"] = {"style": style}
        return card

    def heading(title, icon):
        return {"type": "heading", "heading": title, "icon": icon, "heading_style": "title"}

    def markdown(content, columns=12, accent=None, **kwargs):
        return styled({"type": "markdown", "content": render(content),
                       "grid_options": {"columns": columns, "rows": "auto"}, **kwargs}, accent)

    def tile(key, name, icon=None, columns=6, color="teal", features=None, **kwargs):
        if not e.get(key):
            return None
        card = {"type": "tile", "entity": e[key], "name": name, "color": color,
                "tap_action": {"action": "more-info"}, "icon_tap_action": {"action": "more-info"},
                "grid_options": {"columns": columns, "rows": 2 if features else 1}, **kwargs}
        if icon:
            card["icon"] = icon
        if features:
            card["features"] = features
        return styled(card)

    def graph(title, series, hours=24, columns=12):
        return styled({"type": "history-graph", "title": title, "hours_to_show": hours,
                       "entities": [{"entity": e[key], "name": name, "color": color}
                                    for key, name, color in series if e.get(key)],
                       "grid_options": {"columns": columns, "rows": 5}})

    def section(title, icon, cards, span=1):
        return {"type": "grid", "column_span": span,
                "cards": [heading(title, icon)] + [c for c in cards if c is not None]}

    def temperature(key, label, icon, color="teal"):
        # Native markdown handles unavailable values without inventing a zero.
        return markdown(f'<ha-icon icon="{icon}"></ha-icon> **{label}**\n\n'
                        + "{% set value = states('@" + key + "@') %}\n"
                        + "## {{ (value | float | round(1) | string) + ' °C' if is_number(value) else 'Waiting' }}",
                        columns=6)

    mode_help = """{% set mode = states('@mode@') %}
{% if mode == 'observe' %}**Observe · watching only**

Recommendations and learning are active when heating conditions allow. No water-temperature commands are sent.
{% elif mode == 'automatic' %}**Automatic · control enabled**

The controller can adjust the heating-water target within its configured limits when all checks pass.
{% else %}**Controller off**

Automatic writes and learning are stopped. The heat pump keeps its own operating mode and water target.
{% endif %}"""

    comfort = markdown("""<ha-icon icon="mdi:home-thermometer-outline"></ha-icon> **LIVING SPACE**

{% set room = states('@indoor@') %}{% set target = states('@target@') %}
# {{ (room | float | round(1) | string) + ' °C' if is_number(room) else 'Waiting for room sensor' }}

{% if is_number(room) and is_number(target) %}
{% set delta = (room | float - target | float) | round(1) %}
Target **{{ target | float | round(1) }} °C** · {% if delta < 0 %}{{ -delta }} °C below target{% elif delta > 0 %}{{ delta }} °C above target{% else %}At target{% endif %}
{% endif %}""", accent="245, 166, 70")

    explanation = markdown("""{% set mode = states('@mode@') %}{% set state = states('@status@') %}
{% set reason = states('@reason@') %}{% set unit = states('@operating@') %}
{% if mode == 'off' %}## Controller off
{% elif state == 'paused' and unit | upper == 'OFF' and reason.startswith('Space-heating state') %}## Waiting for heating
{% elif state == 'paused' %}## Control paused
{% elif state == 'command_sent' %}## Water target updated
{% elif state == 'maintaining' %}## Holding steady
{% elif state == 'waiting' %}## Waiting for next cycle
{% elif mode == 'observe' %}## Watching & learning
{% else %}## {{ state | replace('_', ' ') | capitalize }}
{% endif %}

{% if state == 'paused' and unit | upper == 'OFF' and reason.startswith('Space-heating state') %}
The heat pump reports **OFF**. A new recommendation will appear when space heating is confirmed.
{% elif reason not in ['unknown', 'unavailable', ''] %}{{ reason }}
{% endif %}

{% set entries = state_attr('@status@', 'recent_decisions') or [] %}
{% if entries %}Last checked **{{ as_local(as_datetime(entries[0].checked_at)).strftime('%H:%M') }}**{% endif %}""", accent="54, 187, 169")

    recent_command = markdown("""**LAST COMMAND**

{% set value = states('@commanded@') %}
{% if is_number(value) %}### {{ value | float | round(1) }} °C
Most recent target sent by Adaptive Heating since this restart. See the water history for earlier changes.
{% else %}### No command sent
Adaptive Heating has not sent a water target since this restart.
{% endif %}""")

    preview = markdown("""**LATEST DECISIONS**

{% set entries = state_attr('@status@', 'recent_decisions') or [] %}
{% for item in entries[:3] %}
**{{ as_local(as_datetime(item.checked_at)).strftime('%H:%M') }} · {{ item.status | replace('_', ' ') | capitalize }}**

{{ item.reason }}

{% if item.commanded is not none %}Last command {{ item.commanded | round(1) }} °C · {% endif %}Device target {{ item.actual | round(1) if item.actual is not none else '—' }} °C

{% if not loop.last %}---{% endif %}
{% else %}Waiting for the first evaluation.{% endfor %}

[Open activity & trends](/""" + url + "/adaptive-heating)")

    overview_sections = [
        section("Room comfort", "mdi:home-thermometer", [comfort,
            tile("target", "Room target", "mdi:thermometer", 12, "amber", [{"type": "numeric-input", "style": "buttons"}]),
            tile("mode", "Control mode", "mdi:thermostat-auto", 12, "teal", [{"type": "select-options", "style": "dropdown"}]),
            markdown(mode_help),
            graph("Room · last 24 hours", [("indoor", "Measured", "#f5a646"), ("target", "Target", "#70c1b3")]),
        ]),
        section("What is happening", "mdi:transit-connection-variant", [explanation,
            temperature("actual", "Device water target", "mdi:thermometer-water"),
            temperature("limited", "Next allowed target", "mdi:arrow-decision-outline"),
            recent_command,
            tile("evaluate", "Evaluate now", "mdi:refresh", 12, hide_state=True,
                 tap_action={"action": "perform-action", "perform_action": "button.press", "target": {"entity_id": e["evaluate"]}},
                 icon_tap_action={"action": "perform-action", "perform_action": "button.press", "target": {"entity_id": e["evaluate"]}}),
            preview,
        ]),
        section("Hot water & energy", "mdi:water-boiler", [
            temperature("tank", "Tank temperature", "mdi:water-thermometer") if e.get("tank") else None,
            temperature("tank_target", "Tank target", "mdi:water-boiler") if e.get("tank_target") else None,
            tile("tank_helper", "Hot-water target", "mdi:water-boiler", 12, "blue", [{"type": "numeric-input", "style": "buttons"}]),
            tile("disinfection_active", "Disinfection", "mdi:shield-check-outline", 6, "blue", tap_action={"action": "none"}, icon_tap_action={"action": "none"}),
            tile("last_disinfection", "Last completed", "mdi:calendar-check", 6, "blue", tap_action={"action": "none"}, icon_tap_action={"action": "none"}),
            tile("energy_daily", "Electricity today", "mdi:lightning-bolt-outline", 6, "amber"),
            tile("energy", "Total electricity", "mdi:counter", 6, "amber"),
            styled({"type": "weather-forecast", "entity": e["weather"], "forecast_type": "hourly",
                    "show_current": True, "show_forecast": True, "forecast_slots": 6,
                    "grid_options": {"columns": 12, "rows": 4}}),
            markdown("Hot-water controls use the existing tank routine. Adaptive Heating controls space heating.") if e.get("tank_helper") else None,
        ]),
    ]

    decision_table = markdown("""{% macro temp(value) %}{{ (value | round(1) | string) + '°' if value is not none else '—' }}{% endmacro %}
{% set entries = state_attr('@status@', 'recent_decisions') or [] %}
| Time | Status | Proposed | Allowed | Sent | Device |
| :--- | :--- | ---: | ---: | ---: | ---: |
{% for item in entries %}| {{ as_local(as_datetime(item.checked_at)).strftime('%H:%M') }} | {{ item.status | replace('_', ' ') }} | {{ temp(item.proposed) }} | {{ temp(item.limited) }} | {{ temp(item.commanded) if item.status == 'command_sent' else '—' }} | {{ temp(item.actual) }} |
{% endfor %}

Latest 20 evaluations since startup. **Proposed** is the calculation; **Allowed** includes command limits; **Sent** records an actual write; **Device** is the measured setpoint. A blank Sent cell means that evaluation sent no command.

### Latest explanation
{{ states('@reason@') }}""", columns="full")
    decision_table["visibility"] = [{"condition": "screen", "media_query": "(min-width: 600px)"}]
    decision_mobile = markdown("""{% macro temp(value) %}{{ (value | round(1) | string) + ' °C' if value is not none else '—' }}{% endmacro %}
{% set entries = state_attr('@status@', 'recent_decisions') or [] %}
{% for item in entries %}
**{{ as_local(as_datetime(item.checked_at)).strftime('%H:%M') }} · {{ item.status | replace('_', ' ') | capitalize }}**

Proposed {{ temp(item.proposed) }} · Allowed {{ temp(item.limited) }}

Sent {{ temp(item.commanded) if item.status == 'command_sent' else '—' }} · Device {{ temp(item.actual) }}

{{ item.reason }}

{% if not loop.last %}---{% endif %}
{% else %}Waiting for the first evaluation.{% endfor %}

Latest 20 evaluations since startup. Sent records a new command in that evaluation; — means no command.""")
    decision_mobile["visibility"] = [{"condition": "screen", "media_query": "(max-width: 599px)"}]

    activity_sections = [
        section("Temperatures over time", "mdi:chart-line", [
            graph("Room comfort · 24 hours", [("indoor", "Room", "#f5a646"), ("target", "Target", "#70c1b3"), ("prediction", "Predicted minimum", "#a89fe8")]),
            graph("Heating water · 24 hours", [("output", "Device target", "#f5a646"), ("inlet", "Return", "#64b5f6"), ("outlet", "Supply", "#e87979"), ("limited", "Allowed target", "#70c1b3")]),
            markdown("The device target and measured-temperature graphs include Home Assistant's saved history from before this migration. New controller entities begin recording at installation."),
        ]),
        section("Decision history", "mdi:timeline-clock-outline", [decision_table, decision_mobile,
            graph("Controller activity · 24 hours", [("mode", "Mode", "#70c1b3"), ("status", "Status", "#f5a646"), ("operating", "Heat pump", "#64b5f6")]),
        ]),
        section("Learning & solar", "mdi:brain", [
            tile("samples", "Learning samples", "mdi:school-outline"),
            markdown("**Model error**\n\n{% if states('@samples@') | int(0) > 0 %}{{ states('@error@') }} °C{% else %}Not learned yet{% endif %}", columns=6),
            temperature("prediction", "Predicted minimum", "mdi:chart-timeline-variant"),
            temperature("proposed", "Proposed water target", "mdi:thermometer-auto"),
            markdown("A prediction appears after enough suitable heating observations and a usable forecast. Learning starts fresh; values from the legacy model are not imported."),
            tile("pv", "Solar generation", "mdi:solar-power", color="amber"),
            tile("battery_soc", "Battery charge", "mdi:battery", color="green"),
            tile("grid_import", "Grid import", "mdi:transmission-tower-import", color="blue"),
            tile("grid_export", "Grid export", "mdi:transmission-tower-export", color="teal"),
            tile("battery_charge", "Battery charging", "mdi:battery-arrow-up", color="green"),
            tile("battery_discharge", "Battery discharging", "mdi:battery-arrow-down", color="orange"),
            markdown("**Sustained solar surplus:** {{ 'Detected' if state_attr('@status@', 'sustained_solar_surplus') else 'Not detected' }}\n\nSolar preheating also needs to be enabled in the integration settings."),
        ]),
    ]

    equipment_sections = [
        section("Heat pump", "mdi:heat-pump-outline", [
            tile("operating", "Operating state", "mdi:heat-pump", 12),
            tile("inlet", "Return water", "mdi:waves-arrow-left", color="blue"),
            tile("outlet", "Supply water", "mdi:waves-arrow-right", color="orange"),
            tile("defrost", "Defrost", "mdi:snowflake-melt", 12, "blue"),
            tile("quiet", "Quiet mode", "mdi:volume-low", 12, "indigo", [{"type": "toggle"}]),
            tile("heater1", "Backup heater 1", "mdi:radiator", color="orange"),
            tile("heater2", "Backup heater 2", "mdi:radiator", color="orange"),
            tile("water_heater", "Tank heater", "mdi:water-boiler", 12, "orange"),
        ]),
        section("Efficiency & meters", "mdi:lightning-bolt-circle", [
            tile("cop", "Reported COP", "mdi:heat-pump", color="green"),
            tile("carnot", "Theoretical COP", "mdi:chart-bell-curve", color="grey"),
            tile("thermal", "Thermal power", "mdi:radiator", color="orange"),
            tile("power", "Reported electrical power", "mdi:lightning-bolt", color="amber"),
            tile("lift", "Compressor lift", "mdi:thermometer-chevron-up", color="orange"),
            tile("economizer", "Economizer difference", "mdi:thermometer-lines", color="blue"),
            markdown("**Power reading needs correction**\n\nThe existing electrical-power helper reports a different scale from the phase meters. Treat its power and any dependent COP calculation as unverified until the helper's units/formula are checked.", accent="245, 166, 70") if notes.get("power_units_unverified") else None,
            markdown("These efficiency readings come from the existing equipment sensors. They are not calculated or validated by Adaptive Heating."),
        ]),
        section("Manual controls & migration", "mdi:tune", [
            markdown("**Manual water adjustment**\n\nChanging the device water target can pause automatic control. Review the cause before selecting Observe and then Automatic again."),
            tile("output", "Manual heating-water target", "mdi:thermometer-water", 12, "orange", [{"type": "numeric-input", "style": "buttons"}]),
            tile("legacy_enabled", "Legacy controller enabled", "mdi:history", 12, "grey", tap_action={"action": "none"}, icon_tap_action={"action": "none"}),
            markdown("Keep the legacy space-heating controller off while using Adaptive Heating. The hot-water routine remains separate.") if e.get("legacy_enabled") else None,
            tile("legacy_target", "Disinfection room reference", "mdi:home-thermometer", 12, "blue", [{"type": "numeric-input", "style": "buttons"}]),
            markdown("The existing disinfection routine uses this separate room reference. It is not automatically synchronized with the new Room target.") if e.get("legacy_target") else None,
            tile("disinfection_run", "Run existing disinfection routine", "mdi:water-check", 12, "blue", hide_state=True),
            tile("hacs_update", "Integration update · HACS", "mdi:package-up", 12, "blue"),
            {"type": "button", "name": "Integration settings", "icon": "mdi:cog-outline", "show_state": False,
             "tap_action": {"action": "navigate", "navigation_path": "/config/integrations/integration/adaptive_heating"},
             "grid_options": {"columns": 12, "rows": 2}},
        ]),
    ]

    views = []
    for title, view_path, icon, subtitle, sections in [
        ("Heating", "0", "mdi:home-thermometer", "Room comfort, live decisions and hot water", overview_sections),
        ("Activity & trends", "adaptive-heating", "mdi:chart-timeline-variant", "What changed, what was proposed, and what the house did", activity_sections),
        ("Equipment", "equipment", "mdi:heat-pump-outline", "Device readings, manual controls and migration details", equipment_sections),
    ]:
        views.append({"title": title, "path": view_path, "type": "sections", "max_columns": 3,
                      "header": {"layout": "responsive", "badges_position": "bottom", "badges_wrap": "wrap",
                                 "card": {"type": "markdown", "content": "# " + title + "\n" + subtitle, "text_only": True}},
                      "sections": sections})
    return {"views": views}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    config = build(json.loads(args.mapping.read_text()))
    args.output.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    print(f"Built {len(config['views'])} views: {args.output}")


if __name__ == "__main__":
    main()
