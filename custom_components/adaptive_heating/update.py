"""Native HA update card backed by our manual release installer."""

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from .const import VERSION
from .entity import HeatingEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([IntegrationUpdate(entry.runtime_data)])


class IntegrationUpdate(HeatingEntity, UpdateEntity):
    _attr_supported_features = UpdateEntityFeature.INSTALL | UpdateEntityFeature.RELEASE_NOTES
    _attr_entity_category = EntityCategory.CONFIG
    _attr_auto_update = False
    _attr_title = "Adaptive Heating"

    def __init__(self, coordinator):
        super().__init__(coordinator, "integration_update", "Integration update")

    @property
    def installed_version(self):
        return VERSION

    @property
    def latest_version(self):
        return (self.coordinator.releases.info or {}).get("version")

    @property
    def release_url(self):
        return (self.coordinator.releases.info or {}).get("release_url")

    @property
    def in_progress(self):
        return self.coordinator.releases.in_progress

    @property
    def release_summary(self):
        manager = self.coordinator.releases
        if manager.restart_pending:
            return "Update installed. Restart Home Assistant when convenient, then select Automatic to resume control."
        if manager.last_error:
            return manager.last_error[:255]
        return ((manager.info or {}).get("notes") or "Use Check for updates to query the latest stable release.")[:255]

    async def async_release_notes(self):
        return (self.coordinator.releases.info or {}).get("notes", "")

    async def async_install(self, version=None, backup=False, **kwargs):
        if version is not None and version != self.latest_version:
            raise HomeAssistantError("Only the checked stable release can be installed")
        await self.coordinator.releases.async_install()
