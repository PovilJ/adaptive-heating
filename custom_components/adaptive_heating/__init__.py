"""Adaptive Heating: local control using existing Home Assistant entities."""

from datetime import timedelta

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import DOMAIN, PLATFORMS, RETIRED_OPTIONS, RETIRED_SENSORS
from .coordinator import HeatingCoordinator
from .engine import temperature
from .updater import ReleaseManager

CONFIG_MINOR_VERSION = 2


def migrate_values(values):
    """Entry data/options of 1.1 -> 1.2: drop the retired curve and planner options; every
    other selection is kept exactly. New options are not written, so they follow their
    defaults until the owner saves the options form."""
    return {k: v for k, v in dict(values).items() if k not in RETIRED_OPTIONS}


async def async_migrate_entry(hass, entry):
    if entry.version > 1:
        return False  # written by a newer major version; refuse rather than guess
    if entry.version == 1 and entry.minor_version < CONFIG_MINOR_VERSION:
        hass.config_entries.async_update_entry(entry, data=migrate_values(entry.data),
                                               options=migrate_values(entry.options),
                                               minor_version=CONFIG_MINOR_VERSION)
    return True


def remove_retired_entities(hass, entry):
    """Sensors of the 0.5 planner have no meaning in 0.6; remove them instead of leaving
    'no longer provided' entries in the registry."""
    registry = er.async_get(hass)
    for key in RETIRED_SENSORS:
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_{key}")
        if entity_id:
            registry.async_remove(entity_id)


async def async_setup_entry(hass, entry):
    shared = hass.data.setdefault(DOMAIN, {})
    if "releases" not in shared:
        shared["releases"] = ReleaseManager(hass)
    remove_retired_entities(hass, entry)
    coordinator = HeatingCoordinator(hass, entry, shared["releases"])
    entry.runtime_data = coordinator
    await coordinator.async_load()
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if coordinator.ac.configured or coordinator.ac.session or coordinator.ac.recovery_pending:
        entry.async_on_unload(async_track_time_interval(hass, coordinator.async_ac_tick, timedelta(seconds=30)))

        @callback
        def ac_changed(event):
            # Keep a transient AC operation out of learning even when it starts and stops
            # between two controller steps.
            if event.data["entity_id"] == coordinator.config.get("ac_entity"):
                changed = (event.data.get("old_state"), event.data.get("new_state"))
                if any(state is None or state.state not in ("off", "fan_only") for state in changed):
                    coordinator.ac.blocked_until = max(coordinator.ac.blocked_until,
                        dt_util.utcnow().timestamp() + coordinator.ac.settings.ac_settle_minutes * 60)
            hass.async_create_task(coordinator.async_ac_tick())

        watched = [coordinator.config.get(k) for k in ("ac_entity", "ac_room_entity")]
        entry.async_on_unload(async_track_state_change_event(hass, [e for e in watched if e], ac_changed))
    if coordinator.disinfection.configured or coordinator.disinfection.blocks_heating:
        # The tank watcher has its own cadence.
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
    # Entries are not unloaded when Home Assistant stops: save the learned state then.
    entry.async_on_unload(hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, coordinator.async_stop))
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
    # The 0.5 learning log; 0.6 removes it at first load, this covers an entry never loaded by 0.6.
    await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.learning").async_remove()
    store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.disinfection")
    saved = await store.async_load()
    # Even a failed-to-load entry must not erase its outstanding recovery journal.
    if not saved or (isinstance(saved, dict) and saved.get("cycle") is None):
        await store.async_remove()
    store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.ac")
    saved = await store.async_load()
    if not saved or (isinstance(saved, dict) and saved.get("session") is None):
        await store.async_remove()
