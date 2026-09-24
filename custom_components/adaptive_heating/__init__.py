"""Adaptive Heating: local control using existing Home Assistant entities."""

from .const import DOMAIN, PLATFORMS
from .coordinator import HeatingCoordinator
from .updater import ReleaseManager


async def async_setup_entry(hass, entry):
    shared = hass.data.setdefault(DOMAIN, {})
    if "releases" not in shared:
        shared["releases"] = ReleaseManager(hass)
    coordinator = HeatingCoordinator(hass, entry, shared["releases"])
    entry.runtime_data = coordinator
    await coordinator.async_load()
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    shared["releases"].controllers.add(coordinator)
    return True


async def async_reload_entry(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    coordinator = entry.runtime_data
    coordinator.mode = "off"
    result = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if result:
        coordinator.releases.controllers.discard(coordinator)
        await coordinator.async_save()
    return result


async def async_remove_entry(hass, entry):
    from homeassistant.helpers.storage import Store
    await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}").async_remove()
