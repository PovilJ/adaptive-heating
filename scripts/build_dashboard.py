#!/usr/bin/env python3
"""Build the tabbed Lovelace heating dashboard from explicitly mapped entities.

This only writes JSON. It never connects to Home Assistant or changes equipment.
The destination needs the Mushroom, Stack In Card and card-mod resources; charts use the\nintegration's own card (custom:adaptive-heating-chart), which the integration loads itself.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REQUIRED = ("indoor", "weather", "operating", "output", "status", "reason", "proposed",
            "limited", "mode", "target", "evaluate")
ACTIVE_DISINFECTION = ("starting", "heating", "holding", "restoring", "blocked",
                       "recovery_required", "attention_required")
ACTIVE_AC = ("starting", "running", "stopping", "manual", "blocked",
             "recovery_required", "attention_required")
SLAB_BAND = 1.4  # K: the controller's start/stop band around the floor target (slab.Params.band)
RUN_CONFIRMATION = ("Start a tank disinfection cycle now? Disinfection must be in Automatic. "
                    "The current tank target is saved and restored afterwards.")


def build(mapping):
    e = mapping["entities"]
    url = "/" + mapping.get("url_path", "dashboard-heating") + "/"
    missing = [key for key in REQUIRED if not e.get(key)]
    if missing:
        raise ValueError("Missing entity mappings: " + ", ".join(missing))

    def need(key):
        # An unmapped key raises KeyError; card builders turn that into "omit this card".
        if not e.get(key):
            raise KeyError(key)
        return e[key]

    def fill(text):
        return re.sub(r"@(\w+)@", lambda match: need(match.group(1)), text)

    def val(key, digits=1, unit=" °C", attr=None):
        """Jinja for a formatted reading; missing readings show a dash, never zero."""
        source = f"state_attr('@{key}@','{attr}')" if attr else f"states('@{key}@')"
        return ("{% set v = " + source + " %}{{ '%." + str(digits) + "f' | format(v | float) ~ '"
                + unit + "' if is_number(v) else '—' }}")

    def when(key, attr, fmt="%d %b %H:%M"):
        return ("{% set d = as_datetime(state_attr('@" + key + "@','" + attr + "'), default=none) %}"
                "{{ as_local(d).strftime('" + fmt + "') if d else '—' }}")

    def card(primary, secondary="", icon="mdi:circle", color="grey", cols=6, entity=None, nav=None, tap=None):
        """Mushroom template card: coloured icon, value on top, label underneath."""
        try:
            action = tap or ({"action": "navigate", "navigation_path": url + nav} if nav
                             else {"action": "more-info"} if entity else {"action": "none"})
            built = {"type": "custom:mushroom-template-card", "primary": fill(primary),
                     "secondary": fill(secondary), "icon": icon, "icon_color": fill(color),
                     "color": fill(color), "multiline_secondary": True, "tap_action": action,
                     "grid_options": {"columns": cols}}
            if entity:
                built["entity"] = need(entity)
            return built
        except KeyError:
            return None

    def stat(key, label, icon, color, digits=1, unit=" °C", attr=None, cols=6):
        return card(val(key, digits, unit, attr), label, icon, color, cols, entity=key)

    def with_control(info, key, kind="number"):
        """Reading and its real control on one surface, as in the original dashboard."""
        if not e.get(key):
            return info
        if kind == "select":
            # Mushroom's select card draws HA's dropdown, which HA loads lazily: about half the
            # page loads showed an empty box with the options as loose text. The tile card's own
            # dropdown ships with the tile, so it is always ready.
            control = {"type": "tile", "entity": e[key], "name": "Control mode", "icon": "mdi:tune-variant",
                       "hide_state": True, "features": [{"type": "select-options"}], "features_position": "inline",
                       "grid_options": {"columns": 12}}
            return {"type": "vertical-stack", "cards": [info, control], "grid_options": {"columns": 12}} if info else control
        control = {"type": f"custom:mushroom-{kind}-card", "entity": e[key], "layout": "horizontal",
                   "grid_options": {"columns": 12}}
        if kind == "number":
            control["display_mode"] = "buttons"
        if not info:
            return control
        control.update(primary_info="none", secondary_info="none", icon_type="none", fill_container=True)
        # Stack In Card leaves each inner card's own border, which shows as a seam in the middle.
        seamless = {"style": "ha-card { border: none !important; box-shadow: none !important; background: none !important; }"}
        info, control = {**info, "card_mod": seamless}, {**control, "card_mod": seamless}
        return {"type": "custom:stack-in-card", "mode": "horizontal", "cards": [info, control],
                "grid_options": {"columns": 12}}

    def press(key, label, hint, icon, color, confirmation=None, cols=6):
        if not e.get(key):
            return None
        action = {"action": "perform-action", "perform_action": "button.press",
                  "target": {"entity_id": e[key]}}
        if confirmation:
            action["confirmation"] = {"text": confirmation}
        return card(label, hint, icon, color, cols, tap=action)

    def tile(key, name, icon, color, cols=6, **extra):
        if not e.get(key):
            return None
        return {"type": "tile", "entity": e[key], "name": name, "icon": icon, "color": color,
                "grid_options": {"columns": cols}, **extra}

    def graph(name, series, hours=24, bars=False, shade=True):
        """The integration's own chart card: values sit in a row above the plot (at the cursor,
        or live), never in a tooltip under the finger. Series: (key, label, colour, options) with
        options step, dashed, fill, offset, attribute, unit, digits. Bars plot one day per bar
        from the long-term statistics of a total meter. While the unit heats, the plot is shaded."""
        entities = [{"entity": e[key], "name": label, "color": color, **(more[0] if more else {})}
                    for key, label, color, *more in series if e.get(key)]
        if not entities:
            return None
        built = {"type": "custom:adaptive-heating-chart", "title": name, "hours": hours, "series": entities,
                 "grid_options": {"columns": 12}}
        if bars:
            built["bars"] = True
        elif shade and e.get("operating"):
            states, label, color = (["HOT WATER", "HOT_WATER", "DHW"], "Hot water", "#e57373") if shade == "dhw" \
                else (["HEAT"], "Heating", "#ff9800")
            built["shade"] = {"entity": e["operating"], "states": states, "name": label, "color": color}
        return built

    def markdown(content):
        try:
            return {"type": "markdown", "content": fill(content), "grid_options": {"columns": 12}}
        except KeyError:
            return None

    def only(built, key, states=None):
        """Show a card only for the listed states, or while the entity is available."""
        if not built or not e.get(key):
            return None
        conditions = ([{"condition": "or", "conditions": [
            {"condition": "state", "entity": e[key], "state": state} for state in states]}] if states else
            [{"condition": "state", "entity": e[key], "state_not": state} for state in ("unknown", "unavailable")])
        return {"type": "conditional", "conditions": conditions, "card": built,
                "grid_options": built.get("grid_options", {"columns": 12})}

    def section(title, icon, cards):
        cards = [item for item in cards if item]
        return {"type": "grid", "cards": [{"type": "heading", "heading": title, "icon": icon,
                                           "heading_style": "title"}] + cards} if cards else None

    def view(title, path, icon, sections):
        return {"title": title, "path": path, "icon": icon, "type": "sections", "max_columns": 2,
                "sections": [item for item in sections if item]}

    def activity(defrost, heat, hot_water, resting, idle, other):
        """Choose by what the heat pump is doing; OFF with heating enabled is a rest, not idle."""
        first = ("{% if is_state('@defrost@','on') %}" + defrost + "{% elif " if e.get("defrost") else "{% if ")
        return ("{% set u = states('@operating@') | upper %}" + first + "u == 'HEAT' %}" + heat
                + "{% elif u in ['HOT WATER','HOT_WATER','DHW'] %}" + hot_water
                + "{% elif u == 'OFF' and state_attr('@status@','heating_enabled') == true %}" + resting
                + "{% elif u == 'OFF' %}" + idle + "{% else %}" + other + "{% endif %}")

    mode_color = "{{ {'automatic':'green','observe':'amber'}.get(states('@KEY@'),'grey') }}"
    cop_color = ("{% set c = states('@KEY@') | float(-1) %}{{ 'green' if c >= 4 else 'light-green' if c >= 3 "
                 "else 'orange' if c >= 2 else 'red' if c > 0 else 'grey' }}")

    # ---------------------------------------------------------------- Home
    chips = [{"type": "weather", "entity": e["weather"], "show_conditions": True, "show_temperature": True}]
    chip_row = {"type": "custom:mushroom-chips-card", "chips": chips, "grid_options": {"columns": 12}}

    room = with_control(card(
        val("indoor"),
        "{% set r = states('@indoor@') %}{% set t = states('@target@') %}"
        "{% if is_number(r) and is_number(t) %}{% set g = (r | float - t | float) | round(1) %}"
        "Target {{ t | float | round(1) }}° · {{ (-g) ~ '° below' if g < 0 else g ~ '° above' if g > 0 else 'on target' }}"
        "{% else %}Room target{% endif %}",
        "mdi:home-thermometer",
        "{% set r = states('@indoor@') %}{% set t = states('@target@') %}"
        "{% if is_number(r) and is_number(t) %}{% set g = r | float - t | float %}"
        "{{ 'blue' if g < -0.5 else 'deep-orange' if g > 0.5 else 'green' }}{% else %}grey{% endif %}",
        12, entity="indoor"), "target")

    labels = ("{{ {'waiting':'Waiting','command_sent':'Adjusted','maintaining':'Holding',"
              "'observing':'Watching','paused':'Paused','off':'Control off'}"
              ".get(states('@status@'),'Unavailable') }}")
    heat_pump = with_control(card(
        activity("Defrost", "Heating", "Hot water", "Resting", "Off",
                 "{{ u | replace('_',' ') | capitalize }}"),
        "{% if is_state('@status@','paused') %}{{ states('@reason@') | truncate(40, true) }}{% else %}" + labels
        + "{% set d = state_attr('@status@','recent_decisions') or [] %}"
        "{% if d %} · {{ as_local(as_datetime(d[0].checked_at)).strftime('%H:%M') }}{% endif %}{% endif %}",
        "mdi:heat-pump", activity("indigo", "orange", "red", "blue", "grey", "grey"), 12, entity="operating"),
        "mode", "select")

    power_key = "live_power" if e.get("live_power") else "power" if e.get("power") else None
    power = card(
        "{% set p = states('@P@') %}{% set u = state_attr('@P@','unit_of_measurement') or '' %}"
        "{{ ('%.0f' if u == 'W' else '%.2f') | format(p | float) ~ ' ' ~ u if is_number(p) else '—' }}".replace("P@", (power_key or "") + "@"),
        ("Power · today " + val("energy_daily", 1, " kWh")) if e.get("energy_daily") else "Power now",
        "mdi:lightning-bolt",
        "{% set u = state_attr('@P@','unit_of_measurement') %}{% set w = states('@P@') | float(0) * (1000 if u == 'kW' else 1) %}"
        "{{ 'grey' if w < 100 else 'green' if w < 1500 else 'amber' if w < 3000 else 'red' }}".replace("P@", (power_key or "") + "@"),
        entity=power_key) if power_key else None
    cop = card("COP " + val("cop", 1, ""), ("Heat out " + val("thermal", 1, " kW")) if e.get("thermal") else "Efficiency now",
               "mdi:speedometer", cop_color.replace("KEY", "cop"), entity="cop", nav="system")
    supply = stat("outlet", "Water out", "mdi:waves-arrow-right", "orange")
    returned = card(val("inlet"), "Water in" + (
        "{% set o = states('@outlet@') %}{% set i = states('@inlet@') %}"
        "{% if is_number(o) and is_number(i) %} · Δ {{ (o | float - i | float) | round(1) }}°{% endif %}" if e.get("outlet") else ""),
        "mdi:waves-arrow-left", "blue", entity="inlet")
    water_target = card(
        val("output"),
        "{% set c = states('@output@') %}{% set a = states('@limited@') %}{% set m = states('@mode@') %}{% set s = states('@status@') %}"
        "Water target · {% if m == 'off' %}control off{% elif m not in ['observe','automatic'] or s in ['unknown','unavailable',''] %}controller unavailable"
        "{% elif s == 'paused' %}paused{% elif is_number(c) and is_number(a) and (c | float - a | float) | abs >= 0.1 %}"
        "{{ 'suggests' if m == 'observe' else 'next' }} {{ a | float | round(1) }}°{% else %}holding{% endif %}",
        "mdi:thermometer-water", "teal", entity="output", nav="trends")
    tank_color = ("{% set t = states('@tank@') | float(0) %}{{ 'red' if t >= 45 else 'orange' if t >= 38 else 'blue' }}")
    tank_secondary = "Hot water" + (" · target " + val("tank_target", 0, "°") if e.get("tank_target") else "")
    tank_small = card(val("tank"), tank_secondary, "mdi:water-boiler", tank_color, entity="tank", nav="water")

    def alert(key, title, states, color, icon, nav):
        return only(card(title + " · {{ states('@" + key + "@') | replace('_',' ') }}",
                         "{{ state_attr('@" + key + "@','reason') or 'Tap for details' }}",
                         icon, color, 12, nav=nav), key, states)

    cycle_names = ("{{ {'idle':'Floor resting','kick':'Starting the compressor','ride':'Heating the floor',"
                   "'stop':'Ending the run','wait':'Waiting for hot water or defrost','hold':'Holding: no heat-pump data'}"
                   ".get(p, 'Controller unavailable' if p in ['unknown','unavailable'] else p | capitalize) }}")
    floor = card(
        "{% set p = states('@cycle@') %}" + cycle_names,
        "{% set m = states('@mode@') %}"
        "{% if m != 'automatic' %}{{ 'Suggestion only · ' if m == 'observe' else 'Not applied · ' }}{% endif %}"
        "{% set s = state_attr('@cycle@','slab_estimate') %}{% set t = state_attr('@cycle@','slab_target') %}"
        "{% if is_number(s) and is_number(t) %}Floor {{ s | float | round(1) }}° · target {{ t | float | round(1) }}°"
        "{% else %}Tap for floor details{% endif %}",
        "mdi:heating-coil",
        "{% set p = states('@cycle@') %}{{ 'orange' if p in ['kick','ride'] else 'indigo' if p == 'stop' "
        "else 'grey' if p in ['hold','unknown','unavailable'] else 'blue' }}",
        12, nav="floor")
    why = card("Why",
               "{% set r = states('@reason@') %}{% if is_state('@mode@','off') %}Floor control is off."
               "{% elif r in ['unknown','unavailable',''] %}Waiting for the first evaluation.{% else %}{{ r }}{% endif %}",
               "mdi:head-lightbulb-outline", "amber", 12, entity="reason")
    # The controller in one picture: the floor estimate between its start and stop points
    # (floor target -/+ SLAB_BAND), with the heat pump's heating runs shaded.
    floor_graph = graph("Floor · 24 h", [
        ("slab_estimate", "Floor", "#ff8a65"),
        ("slab_target", "Target", "#4db6ac", {"step": True}),
        ("slab_target", "Start", "#64b5f6", {"step": True, "dashed": True, "offset": -SLAB_BAND}),
        ("slab_target", "Stop", "#9575cd", {"step": True, "dashed": True, "offset": SLAB_BAND})])
    room_series = [("indoor", "Room", "#f5a646", {"fill": True}), ("target", "Target", "#4db6ac", {"step": True})]

    home = view("Home", "home", "mdi:home-thermometer", [
        section("Heating", "mdi:fire", [chip_row, room, heat_pump, power, cop, supply, returned, water_target, tank_small,
            alert("disinfection_status", "Disinfection", ACTIVE_DISINFECTION, "red", "mdi:water-check", "water"),
            alert("ac_status", "AC assistance", ACTIVE_AC, "indigo", "mdi:air-conditioner", "floor")]),
        section("Next & why", "mdi:clock-outline", [floor, why, floor_graph, graph("Room · 24 h", room_series, shade=False)]),
    ])

    # -------------------------------------------------------------- Trends
    decisions = markdown(
        "{% macro t(v) %}{{ (v | round(1) | string) + '°' if v is not none else '—' }}{% endmacro %}"
        "{% set rows = state_attr('@status@','recent_decisions') or [] %}\n"
        "| Time | Status | Want | Sent | Now |\n| :-- | :-- | --: | --: | --: |\n"
        "{% for i in rows[:10] %}| {{ as_local(as_datetime(i.checked_at)).strftime('%H:%M') }} | "
        "{{ {'command_sent':'✅','waiting':'⏳','maintaining':'🟢','observing':'👁️','paused':'⏸️'}.get(i.status,'▫️') }} "
        "{{ i.status | replace('_',' ') }} | {{ t(i.proposed) }} | "
        "{{ t(i.commanded) if i.status == 'command_sent' else '—' }} | {{ t(i.actual) }} |\n"
        "{% else %}| — | ⏳ waiting for the first evaluation | — | — | — |\n{% endfor %}")
    states_history = {"type": "history-graph", "hours_to_show": 24, "grid_options": {"columns": 12},
                      "entities": [{"entity": e[key], "name": name} for key, name in (
                          ("operating", "Heat pump"), ("status", "Control"), ("cycle", "Cycle"),
                          ("ac_status", "AC")) if e.get(key)]}
    trends = view("Trends", "trends", "mdi:chart-line", [
        section("Comfort", "mdi:home-thermometer", [
            graph("Room · 24 h", room_series, shade=False),
            graph("Outdoor · 48 h", [("weather", "Outdoor", "#64b5f6", {"attribute": "temperature", "unit": "°C", "fill": True})], 48, shade=False)]),
        section("Water", "mdi:waves", [
            graph("Heating water · 24 h", [("output", "Target", "#4db6ac", {"step": True}),
                                           ("outlet", "Out", "#ff8a65"), ("inlet", "In", "#64b5f6")]),
            graph("Hot-water tank · 48 h", [("tank", "Tank", "#e57373"),
                                            ("tank_target", "Target", "#9e9e9e", {"step": True})], 48, shade="dhw")]),
        section("Electricity", "mdi:lightning-bolt", [
            stat("energy_daily", "Today", "mdi:calendar-today", "amber", 1, " kWh", cols=4),
            stat("energy_monthly", "This month", "mdi:calendar-month", "orange", 0, " kWh", cols=4),
            stat("energy", "Total", "mdi:counter", "brown", 0, " kWh", cols=4),
            graph("Power · 24 h", [(power_key, "Power", "#ffb300", {"fill": True, "digits": 0})], shade=False) if power_key else None,
            graph("Daily energy · 7 days", [("energy", "Energy", "#ff8a65", {"unit": "kWh"})], 168, bars=True),
            graph("COP · 24 h", [("cop", "COP", "#81c784", {"digits": 2})])]),
        section("Activity", "mdi:timeline-clock-outline", [states_history, decisions]),
    ])

    # --------------------------------------------------------------- Floor
    parts = markdown(
        "{% set p = state_attr('@cycle@','target_parts') or {} %}"
        "{% set names = {'target':'Room target','weather':'Forecast cold (1-9 h)','offset':'Base offset',"
        "'sun':'Forecast sun (1-9 h)','room':'Room now','integral':'Learned level','daily':'Learned time of day',"
        "'warm_hours':'Warmer hours ahead'} %}\n"
        "| Floor target part | °C |\n| :-- | --: |\n"
        "{% for k, label in names.items() %}{% if k in p %}| {{ label }} | {{ '%+.2f' | format(p[k]) if k != 'target' "
        "else '%.1f' | format(p[k]) }} |\n{% endif %}{% endfor %}"
        "{% if not p %}| Waiting for the controller | — |\n{% endif %}")
    pattern = markdown(
        "{% set d = state_attr('@cycle@','daily_pattern') or [] %}{% set f = state_attr('@cycle@','fallback_curve') or {} %}"
        "**Learned time of day** (°C on the floor target, by hour)\n\n"
        "{% for v in d %}{{ '%02d' | format(loop.index0) }}h {{ '%+.1f' | format(v) }}{{ ' · ' if not loop.last }}{% else %}Still learning.{% endfor %}"
        "\n\n**Without a room thermometer** the learned level by outdoor temperature: "
        "{% for k, v in f.items() %}{{ k }} °C → {{ '%+.1f' | format(v) }}{{ ' · ' if not loop.last }}{% else %}—{% endfor %}")
    floor_view = view("Floor", "floor", "mdi:heating-coil", [
        section("Floor & forecast", "mdi:weather-partly-cloudy", [
            {"type": "weather-forecast", "entity": e["weather"], "forecast_type": "hourly", "show_current": True,
             "show_forecast": True, "forecast_slots": 6, "grid_options": {"columns": 12}},
            floor,
            card("Controller reason", "{{ state_attr('@cycle@','reason') or 'Waiting for the controller.' }}",
                 "mdi:comment-text-outline", "indigo", 12, entity="cycle"),
            stat("slab_estimate", "Floor estimate", "mdi:texture-box", "deep-orange"),
            stat("slab_target", "Floor target", "mdi:target", "green"),
            card("Start below " + val("cycle", 1, "°", "start_below"),
                 "Stop above " + val("cycle", 1, "°", "stop_above"), "mdi:arrow-up-down", "blue", 12, entity="cycle"),
            parts,
            floor_graph]),
        section("AC assistance", "mdi:air-conditioner", [
            with_control(card("{{ states('@ac_status@') | replace('_',' ') | capitalize }}",
                              "AC unit {{ state_attr('@ac_status@','actual_mode') or 'unknown' }}",
                              "mdi:air-conditioner", mode_color.replace("KEY", "ac_mode") if e.get("ac_mode") else "indigo",
                              12, entity="ac_status"), "ac_mode", "select"),
            card("AC reason", "{{ state_attr('@ac_status@','reason') or 'Waiting for the AC controller.' }}",
                 "mdi:comment-text-outline", "indigo", 12, entity="ac_status"),
            tile("ac_climate", "AC unit", "mdi:air-conditioner", "indigo", 12),
            only(stat("ac_power", "AC power", "mdi:lightning-bolt", "amber", 0, " W"), "ac_power"),
            only(stat("ac_energy", "This session", "mdi:counter", "amber", 2, " kWh"), "ac_energy")]),
        section("Learning", "mdi:brain", [
            stat("cycle", "Learned level", "mdi:school-outline", "purple", 2, " °C", "learned_integral"),
            card("{{ {'ok':'Room sensor OK','missing':'Room sensor unavailable','stale':'Room sensor silent',"
                 "'frozen':'Room sensor stuck'}.get(state_attr('@cycle@','room_sensor'), 'Room sensor —') }}",
                 "{{ 'Learning paused: AC influence' if state_attr('@status@','learning_excluded_by_ac') else "
                 "'Learning while Automatic' }}", "mdi:thermometer-check", "purple", entity="cycle"),
            stat("proposed", "Wanted water", "mdi:thermometer-auto", "teal"),
            stat("writes", "Setpoint writes · 24 h", "mdi:pencil-outline", "brown", 0, ""),
            pattern]),
    ])

    # --------------------------------------------------------------- Water
    disinfection_color = ("{% set s = states('@disinfection_status@') %}{{ 'red' if s in ['heating','holding','starting'] else "
                          "'orange' if s in ['blocked','recovery_required','attention_required','restoring'] else "
                          "'grey' if s in ['off','unknown','unavailable'] else 'green' }}")
    water = view("Hot water", "water", "mdi:water-boiler", [
        section("Hot water", "mdi:water-boiler", [
            with_control(card(val("tank"), "Tank temperature", "mdi:water-boiler", tank_color, 12, entity="tank"), "tank_target"),
            tile("water_heater", "Tank heater", "mdi:heating-coil", "orange", 12),
            graph("Tank · 48 h", [("tank", "Tank", "#e57373"), ("tank_target", "Target", "#9e9e9e", {"step": True})], 48, shade="dhw")]),
        section("Disinfection", "mdi:water-check", [
            with_control(card("{{ states('@disinfection_status@') | replace('_',' ') | capitalize }}",
                              "{{ state_attr('@disinfection_status@','reason') or 'Tank disinfection' }}",
                              "mdi:water-check", disinfection_color, 12, entity="disinfection_status"),
                         "disinfection_mode", "select"),
            stat("disinfection_status", "Cycle target", "mdi:thermometer-high", "red", 0, " °C", "target_temperature"),
            card("{{ ((state_attr('@disinfection_status@','hold_seconds') or 0) / 60) | round(1) }} / "
                 "{{ state_attr('@disinfection_status@','hold_minutes') or '—' }} min",
                 "Hold at " + val("disinfection_status", 0, " °C", "hold_threshold") + " or above",
                 "mdi:timer-outline", "orange", entity="disinfection_status"),
            card(when("disinfection_status", "last_success"), "Last verified cycle", "mdi:check-decagram", "green",
                 entity="disinfection_status"),
            card(when("disinfection_status", "due_by"), "Next due by", "mdi:calendar-clock", "blue",
                 entity="disinfection_status"),
            only(press("disinfection_run", "Run cycle", "Asks to confirm", "mdi:play", "red", RUN_CONFIRMATION), "disinfection_status"),
            only(press("disinfection_cancel", "Cancel", "Restores tank target", "mdi:stop-circle-outline", "grey"), "disinfection_status"),
            markdown("{% for i in (state_attr('@disinfection_status@','recent_cycles') or [])[:8] %}"
                     "**{{ as_local(as_datetime(i.time)).strftime('%d %b %H:%M') }}** · {{ i.status | replace('_',' ') }} — {{ i.reason }}\n\n"
                     "{% else %}No disinfection cycles recorded yet.{% endfor %}")]),
    ])

    # -------------------------------------------------------------- System
    system = view("System", "system", "mdi:cog", [
        section("Efficiency", "mdi:speedometer", [
            card("COP " + val("cop", 2, ""), "Measured now", "mdi:speedometer", cop_color.replace("KEY", "cop"), entity="cop"),
            card("COP " + val("carnot", 1, ""), "Theoretical limit", "mdi:chart-bell-curve",
                 "{% set c = states('@carnot@') | float(0) %}{{ 'green' if c > 5 else 'orange' if c >= 3 else 'red' }}", entity="carnot"),
            stat("thermal", "Heat output", "mdi:radiator", "deep-orange", 1, " kW"),
            card("Lift " + val("lift", 0),
                 "{% set l = states('@lift@') | float(0) %}{{ 'Easy · high efficiency' if l < 50 else 'Normal' if l < 65 else 'Working hard' if l < 80 else 'Struggling' }}",
                 "mdi:thermometer-chevron-up",
                 "{% set l = states('@lift@') | float(0) %}{{ 'green' if l < 50 else 'light-green' if l < 65 else 'orange' if l < 80 else 'red' }}",
                 entity="lift"),
            card("Economizer " + val("economizer"),
                 "{% set d = states('@economizer@') | float(0) %}{{ 'Max boost' if d > 15 else 'Active boost' if d > 10 else 'Some boost' if d > 5 else 'Minimal boost' if d > 0 else 'Inactive' }}",
                 "mdi:thermometer-lines",
                 "{% set d = states('@economizer@') | float(0) %}{{ 'green' if d > 15 else 'light-green' if d > 10 else 'orange' if d > 5 else 'amber' if d > 0 else 'grey' }}",
                 12, entity="economizer")]),
        section("Equipment", "mdi:heat-pump", [
            tile("operating", "Heat pump", "mdi:heat-pump", "orange"),
            tile("defrost", "Defrost", "mdi:snowflake-melt", "indigo"),
            tile("heater1", "Backup heater 1", "mdi:radiator", "red"),
            tile("heater2", "Backup heater 2", "mdi:radiator", "red"),
            tile("quiet", "Quiet mode", "mdi:volume-low", "indigo", 12, features=[{"type": "toggle"}],
                 features_position="inline")]),
        section("Controls", "mdi:tune", [
            with_control(card(val("output"), "Manual water target · can pause automatic control",
                              "mdi:thermometer-water", "teal", 12, entity="output"), "output"),
            press("evaluate", "Evaluate now", "Re-run the controller", "mdi:refresh", "teal"),
            card("Settings", "Integration options", "mdi:cog-outline", "blue-grey",
                 tap={"action": "navigate", "navigation_path": "/config/integrations/integration/adaptive_heating"}),
            tile("hacs_update", "Integration update", "mdi:package-up", "blue", 12)]),
    ])

    return {"views": [item for item in (home, trends, floor_view, water, system) if item["sections"]]}


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
