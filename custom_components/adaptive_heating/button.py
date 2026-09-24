"""Explicit calculation and release-check controls."""

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory

from .entity import HeatingEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([HeatingButton(entry.runtime_data, "evaluate", "Evaluate now"),
                        HeatingButton(entry.runtime_data, "check_release", "Check for updates"),
                        HeatingButton(entry.runtime_data, "disinfection_run", "Run disinfection"),
                        HeatingButton(entry.runtime_data, "disinfection_cancel", "Cancel disinfection and restore")])


class HeatingButton(HeatingEntity, ButtonEntity):
    def __init__(self, coordinator, key, name):
        super().__init__(coordinator, key, name)
        self.key = key
        if key == "check_release":
            self._attr_entity_category = EntityCategory.CONFIG

    async def async_press(self):
        if self.key == "check_release":
            await self.coordinator.releases.async_check()
        elif self.key == "disinfection_run":
            await self.coordinator.async_disinfection_run()
        elif self.key == "disinfection_cancel":
            await self.coordinator.async_disinfection_cancel()
        else:
            await self.coordinator.async_request_refresh()
