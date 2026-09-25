"""UI setup and editable entity mappings for each installation."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DEFAULTS, DOMAIN, OPTIONAL_ENTITIES, REQUIRED_ENTITIES
from .disinfection import DEFAULTS as DHW_DEFAULTS, ENTITIES as DHW_ENTITIES, DisinfectionSettings
from .disinfection_controller import native_target
from .engine import Settings
from .planner import DEFAULTS as PLAN_DEFAULTS, PlannerSettings
from .ac_controller import DEFAULTS as AC_DEFAULTS, ENTITIES as AC_ENTITIES, ACSettings

PLAN_ENTITIES = {"sun_entity": ["sun"], "protection_entity": ["sensor"]}
ALL_OPTIONAL = OPTIONAL_ENTITIES | DHW_ENTITIES | PLAN_ENTITIES | AC_ENTITIES
ALL_DEFAULTS = DEFAULTS | DHW_DEFAULTS | PLAN_DEFAULTS | AC_DEFAULTS


def settings_schema(values):
    fields = {}
    for key, domains in REQUIRED_ENTITIES.items():
        marker = vol.Required(key, default=values[key]) if key in values else vol.Required(key)
        fields[marker] = selector.EntitySelector(selector.EntitySelectorConfig(domain=domains))
    for key, domains in ALL_OPTIONAL.items():
        marker = vol.Optional(key, description={"suggested_value": values.get(key)})
        fields[marker] = selector.EntitySelector(selector.EntitySelectorConfig(domain=domains))
    for key, default in ALL_DEFAULTS.items():
        value = values.get(key, default)
        marker = vol.Required(key, default=value)
        if isinstance(default, bool):
            fields[marker] = selector.BooleanSelector()
        elif isinstance(default, str):
            fields[marker] = selector.TextSelector()
        else:
            fields[marker] = vol.Coerce(int if isinstance(default, int) else float)
    return vol.Schema(fields)


def validate(hass, values, current_entry_id=None):
    errors = {}
    merged = ALL_DEFAULTS | values
    try:
        plan = PlannerSettings(**{key: merged[key] for key in PlannerSettings.__dataclass_fields__})
        if plan.cold_night_enabled and not plan.night_minimum <= merged["target"] <= plan.preheat_ceiling:
            raise ValueError("Target outside planned comfort range")
    except (ValueError, TypeError):
        errors["base"] = "invalid_planning_limits"
    try:
        ACSettings(**{key: merged[key] for key in ACSettings.__dataclass_fields__})
    except (ValueError, TypeError):
        errors["base"] = "invalid_ac_limits"
    try:
        Settings(**{key: values[key] for key in Settings.__dataclass_fields__ if key in values})
    except (ValueError, TypeError):
        errors["base"] = "invalid_limits"
    try:
        dhw = DisinfectionSettings(**{key: values[key] for key in DisinfectionSettings.__dataclass_fields__ if key in values})
    except (ValueError, TypeError):
        errors["base"] = "invalid_disinfection_limits"
        dhw = None
    for key, domains in (REQUIRED_ENTITIES | ALL_OPTIONAL).items():
        entity_id = values.get(key)
        if not entity_id:
            continue
        if entity_id.split(".")[0] not in domains or hass.states.get(entity_id) is None:
            errors[key] = "entity_missing"
    # Do not silently allow two controllers to command the same water setpoint.
    for entry in hass.config_entries.async_entries(DOMAIN):
        existing = dict(entry.data) | dict(entry.options)
        if entry.entry_id == current_entry_id:
            runtime = getattr(entry, "runtime_data", None)
            if runtime and runtime.disinfection.blocks_heating:
                errors["base"] = "disinfection_active"
            if runtime and (runtime.ac.session or runtime.ac.recovery_pending):
                errors["base"] = "ac_active"
        else:
            owned = {existing.get("output_entity"), existing.get("tank_target_entity")} - {None, ""}
            for key in ("output_entity", "tank_target_entity"):
                if values.get(key) in owned:
                    errors[key] = "already_controlled"
            if values.get("ac_entity") and values["ac_entity"] == existing.get("ac_entity"):
                errors["ac_entity"] = "already_controlled"
    if not values.get("heating_state", "").strip():
        errors["heating_state"] = "state_required"
    battery = [values.get(key) for key in ("battery_soc_entity", "battery_charge_entity", "battery_discharge_entity")]
    if any(battery) and not all(battery):
        errors["base"] = "battery_incomplete"
    if values.get("solar_preheat") and not all(values.get(key) for key in ("pv_entity", "import_entity", "export_entity")):
        errors["base"] = "solar_incomplete"
    output = hass.states.get(values.get("output_entity", ""))
    if output and output.attributes.get("unit_of_measurement") not in ("°C", "°F"):
        errors["output_entity"] = "temperature_required"
    if bool(values.get("ac_entity")) != bool(values.get("ac_room_entity")):
        errors["base"] = "ac_incomplete"
    ac = hass.states.get(values.get("ac_entity", ""))
    if ac:
        modes = ac.attributes.get("hvac_modes")
        if not isinstance(modes, (list, tuple)) or not all(mode in modes for mode in ("heat", "off")):
            errors["ac_entity"] = "ac_heat_required"
    for key in ("ac_room_entity", "protection_entity"):
        state = hass.states.get(values.get(key, ""))
        if state and state.attributes.get("unit_of_measurement") not in ("°C", "°F"):
            errors[key] = "temperature_required"
    if values.get("ac_power_entity") and not values.get("ac_entity"):
        errors["base"] = "ac_incomplete"
    tank = [values.get(key) for key in DHW_ENTITIES]
    if any(tank) and not all(tank):
        errors["base"] = "tank_incomplete"
    if all(tank):
        if values["tank_target_entity"] == values.get("output_entity"):
            errors["tank_target_entity"] = "separate_tank_target"
        if dhw:
            try:
                native_target(hass.states.get(values["tank_target_entity"]), dhw.disinfection_target)
            except ValueError:
                errors["tank_target_entity"] = "invalid_tank_target"
        sensor = hass.states.get(values["tank_temperature_entity"])
        if sensor and sensor.attributes.get("unit_of_measurement") not in ("°C", "°F"):
            errors["tank_temperature_entity"] = "temperature_required"
    for key in ("disinfection_hot_water_state", "disinfection_idle_state"):
        if not str(values.get(key, DHW_DEFAULTS[key])).strip():
            errors[key] = "state_required"
    return errors


class AdaptiveHeatingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            errors = validate(self.hass, user_input)
            if not errors:
                return self.async_create_entry(title="Adaptive Heating", data=user_input)
        return self.async_show_form(step_id="user", data_schema=settings_schema(user_input or {}), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AdaptiveHeatingOptionsFlow()


class AdaptiveHeatingOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            errors = validate(self.hass, user_input, self.config_entry.entry_id)
            if not errors:
                # Store explicit empty mappings so clearing an optional selector
                # does not resurrect its original config-entry value.
                values = {key: "" for key in ALL_OPTIONAL} | user_input
                return self.async_create_entry(title="", data=values)
        values = dict(self.config_entry.data) | dict(self.config_entry.options)
        return self.async_show_form(step_id="init", data_schema=settings_schema(user_input or values), errors=errors)
