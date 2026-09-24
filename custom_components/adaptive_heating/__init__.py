"""Adaptive Heating: local control using existing Home Assistant entities."""

from datetime import timedelta

from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

from .const import DOMAIN, PLATFORMS
from .coordinator import HeatingCoordinator
from .engine import temperature
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
    if coordinator.disinfection.configured or coordinator.disinfection.blocks_heating:
        # The tank watcher has its own cadence; heating/model fitting stay at 5 min.
        entry.async_on_unload(async_track_time_interval(hass, coordinator.async_disinfection_tick, timedelta(seconds=30)))

        @callback
        def tank_changed(event):
            dhw = coordinator.disinfection
            state = event.data.get("new_state")
            if dhw.cycle:
                if event.data["entity_id"] == coordinator.config.get("tank_temperature_entity"):
                    value = temperature(state.state, state.attributes.get("unit_of_measurement")) if state else None
                    if value is None or value < dhw.settings.disinfection_threshold:
                        # Capture even a short dip while a service/store await holds the lock.
                        dhw.hold.reset()
                elif dhw.cycle["phase"] in ("heating", "holding"):
                    value = temperature(state.state, state.attributes.get("unit_of_measurement")) if state else None
                    if value is not None and abs(value - dhw.cycle["boost"]) >= 0.05:
                        dhw.manual_override = True
            hass.async_create_task(coordinator.async_disinfection_tick())

        watched = [coordinator.config.get(k) for k in ("tank_temperature_entity", "tank_target_entity")]
        entry.async_on_unload(async_track_state_change_event(hass, [e for e in watched if e], tank_changed))
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    shared["releases"].controllers.add(coordinator)
    return True


async def async_reload_entry(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    coordinator = entry.runtime_data
    if not await coordinator.async_prepare_unload():
        return False
    result = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if result:
        coordinator.releases.controllers.discard(coordinator)
        await coordinator.async_save()
    else:
        coordinator.shutting_down = False
    return result


async def async_remove_entry(hass, entry):
    from homeassistant.helpers.storage import Store
    await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}").async_remove()
    store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.disinfection")
    saved = await store.async_load()
    # Even a failed-to-load entry must not erase its outstanding recovery journal.
    if not saved or (isinstance(saved, dict) and saved.get("cycle") is None):
        await store.async_remove()
