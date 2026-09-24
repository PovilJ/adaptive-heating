"""Observe is the initial mode; Automatic must be selected explicitly."""

from homeassistant.components.select import SelectEntity

from .const import MODES
from .entity import HeatingEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ControlMode(entry.runtime_data), DisinfectionMode(entry.runtime_data)])


class ControlMode(HeatingEntity, SelectEntity):
    _attr_options = MODES
    _attr_icon = "mdi:thermostat-auto"

    def __init__(self, coordinator):
        super().__init__(coordinator, "mode", "Control mode")

    @property
    def current_option(self):
        return self.coordinator.mode

    async def async_select_option(self, option):
        await self.coordinator.async_mode(option)


class DisinfectionMode(HeatingEntity, SelectEntity):
    _attr_options = MODES
    _attr_icon = "mdi:water-check"

    def __init__(self, coordinator):
        super().__init__(coordinator, "disinfection_mode", "Disinfection mode")

    @property
    def current_option(self):
        return self.coordinator.disinfection.mode

    async def async_select_option(self, option):
        await self.coordinator.async_disinfection_mode(option)
