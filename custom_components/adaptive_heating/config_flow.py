"""UI setup and editable entity mappings for each installation."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DEFAULTS, DOMAIN, OPTIONAL_ENTITIES, REQUIRED_ENTITIES
from .engine import Settings


def settings_schema(values):
    fields = {}
    for key, domains in REQUIRED_ENTITIES.items():
        marker = vol.Required(key, default=values[key]) if key in values else vol.Required(key)
        fields[marker] = selector.EntitySelector(selector.EntitySelectorConfig(domain=domains))
    for key, domains in OPTIONAL_ENTITIES.items():
        marker = vol.Optional(key, description={"suggested_value": values.get(key)})
        fields[marker] = selector.EntitySelector(selector.EntitySelectorConfig(domain=domains))
    for key, default in DEFAULTS.items():
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
    try:
        Settings(**{key: values[key] for key in Settings.__dataclass_fields__ if key in values})
    except (ValueError, TypeError):
        errors["base"] = "invalid_limits"
    for key, domains in (REQUIRED_ENTITIES | OPTIONAL_ENTITIES).items():
        entity_id = values.get(key)
        if not entity_id:
            continue
        if entity_id.split(".")[0] not in domains or hass.states.get(entity_id) is None:
            errors[key] = "entity_missing"
    # Do not silently allow two controllers to command the same water setpoint.
    for entry in hass.config_entries.async_entries(DOMAIN):
        existing = dict(entry.data) | dict(entry.options)
        if entry.entry_id != current_entry_id and existing.get("output_entity") == values.get("output_entity"):
            errors["output_entity"] = "already_controlled"
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
                values = {key: "" for key in OPTIONAL_ENTITIES} | user_input
                return self.async_create_entry(title="", data=values)
        values = dict(self.config_entry.data) | dict(self.config_entry.options)
        return self.async_show_form(step_id="init", data_schema=settings_schema(user_input or values), errors=errors)
