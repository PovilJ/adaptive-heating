"""HA state adapter and the single serialized path for actuator writes.

Every minute the coordinator reads the mapped entities, hands them to the slab controller
(slab.py, no Home Assistant inside) and, in Automatic, writes the setpoint it asks for.
When Automatic ends (Observe, Off, a reload, an update) it leaves the controller's idle
setpoint on the unit, so the unit never keeps riding a run nobody watches.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
import logging
import math

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .ac_controller import ACController, DEFAULTS as AC_DEFAULTS
from .const import DEFAULTS, DOMAIN, MODES, VERSION
from .disinfection import DEFAULTS as DHW_DEFAULTS
from .disinfection_controller import DisinfectionController
from .engine import Energy, Settings, clamp, finite, power_watts, surplus_available, temperature
from . import slab

_LOGGER = logging.getLogger(__name__)
STORE_SCHEMA = 2          # 0.6: room target + slab controller state; 0.5 stores carry no schema
SAVE_EVERY = 600          # seconds between saves of the learned state (it changes every minute)
ROOM_ALERT_MINUTES = 60   # a lost room thermometer in Automatic raises a notification after this
CONFIRM_MINUTES = 5       # the device must show a written setpoint within this
UNCONFIRMED_LIMIT = 2     # consecutive unconfirmed writes before Automatic pauses
FAILED_LIMIT = 3          # consecutive failed write calls before Automatic pauses
UNOWNED_ALERT = 3         # unit-started runs stopped in 24 h before the hysteresis notice
FORECAST_EVERY = 1800     # s between forecast fetches; 300 after a failure
# Cloud cover for a forecast row that has none, by HA weather condition.
CONDITION_CLOUD = {"sunny": 0.0, "clear-night": 0.0, "windy": 30.0, "partlycloudy": 50.0, "windy-variant": 60.0}


def state_matches(state, expected):
    """Match numeric mode registers (4 / 4.0) as well as text states."""
    actual_number, expected_number = finite(state), finite(expected)
    if actual_number is not None and expected_number is not None:
        return actual_number == expected_number
    return str(state).strip().casefold() == str(expected).strip().casefold()


def controller_params(settings: Settings) -> slab.Params:
    """Map the main options onto the slab controller's parameters."""
    return slab.Params(
        q_run=settings.run_output_kw, loop_kw_per_k=settings.loop_kw_per_celsius,
        supply_share=settings.slab_supply_share, ctrl_offset=settings.control_sensor_offset,
        outlet_offset=settings.outlet_sensor_offset, sp_floor=settings.minimum_water,
        sp_ceil=min(39.0, settings.maximum_water), write_min=min(20.0, settings.minimum_water),
        write_max=settings.maximum_water)


def upgrade_stored(data, configured_target):
    """Read the main store of any version: (room target or None, controller state or None).

    0.5 stores (no schema) carried the room target and the planner's estimates; only the
    target is kept. The controller state needs the same entity mapping (identity)."""
    if not isinstance(data, dict):
        return None, None
    target = finite(data.get("target"))
    if target is None or not 10 <= target <= 30 or data.get("configured_target") != configured_target:
        target = None
    controller = data.get("controller") if data.get("schema") == STORE_SCHEMA else None
    return target, controller if isinstance(controller, dict) else None


class HeatingCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, releases):
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry, update_interval=timedelta(minutes=1))
        self.entry = entry
        self.releases = releases
        self.config = DEFAULTS | DHW_DEFAULTS | AC_DEFAULTS | dict(entry.data) | dict(entry.options)
        self.settings = Settings(**{k: self.config[k] for k in Settings.__dataclass_fields__ if k in self.config})
        self.core = slab.SlabController(controller_params(self.settings))
        self.store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self.mode = "observe"
        self.resume = "observe"        # the mode the owner selected; Automatic resumes after a restart
        self.release_pending = False   # the last run before this start may have left a ride setpoint
        self.lock = asyncio.Lock()
        self.in_charge = False         # the controller owned the unit at its last step
        self.saved_at = None
        self.unit_last = None          # last complete set of unit values (repeated while the link is down)
        self.room_last = None          # (°C, reported at): the last valid room value
        self.last_commanded = None
        self.last_seen_output = None
        self.pending_deadline = None
        self.unconfirmed = 0
        self.write_failures = 0
        self.manual_hold = False
        self.hold_kind = None          # manual | unconfirmed | failed
        self.surplus_since = None
        self.last_energy_sample = None
        self.forecast_checked = None
        self.forecast_ok = False
        self.forecast_cache = []       # (time, °C): hourly outdoor temperatures (also used by disinfection)
        self.forecast_hours = ()       # slab.Hour rows: the hour's end instant, outdoor there, sun over the hour
        self.room_lost_since = None
        self.alerts = set()            # persistent notifications currently shown
        self.events = []
        self.last_event_key = None
        self.disinfection = DisinfectionController(self)
        self.shutting_down = False
        self.ac = ACController(self)

    # ------------------------------------------------------------------ storage
    def identity(self):
        """The learned state belongs to this room thermometer, these water sensors and this unit."""
        keys = ("indoor_entity", "inlet_entity", "outlet_entity", "output_entity", "operating_entity")
        raw = json.dumps({k: self.config.get(k) for k in keys}, sort_keys=True).encode()
        return hashlib.sha256(raw).hexdigest()

    def options_hash(self):
        """Every mapping and option; Automatic resumes only on the configuration it was selected on."""
        raw = json.dumps(self.config, sort_keys=True, default=str).encode()
        return hashlib.sha256(raw).hexdigest()

    async def async_load(self):
        data = await self.store.async_load()
        target, controller = upgrade_stored(data, self.config["target"])
        if target is not None:
            self.settings.target = target
        if controller is not None and data.get("identity") == self.identity():
            self.core.restore(controller)
        if not isinstance(data, dict) or data.get("schema") != STORE_SCHEMA:
            # 0.5 kept a four-week log for its nightly house refit; 0.6 has no use for it.
            await Store(self.hass, 1, f"{DOMAIN}.{self.entry.entry_id}.learning").async_remove()
            await self.store.async_save(self.stored())
        elif data.get("resume") == "automatic":
            # A plain restart or reload resumes Automatic: a thermostat that stops at every restart
            # leaves the floor to the unit. A new version or changed options start in Observe, as
            # before, and the setpoint the last run may have left is handed back at the first step.
            if (data.get("version") == VERSION and data.get("options") == self.options_hash()
                    and not self.releases.restart_pending):
                self.mode = self.resume = "automatic"
            else:
                self.release_pending = True
        await self.disinfection.async_load()
        await self.ac.async_load()

    def stored(self):
        resume = "automatic" if self.resume == "automatic" and not self.manual_hold else "observe"
        return {"schema": STORE_SCHEMA, "identity": self.identity(), "target": self.settings.target,
                "configured_target": self.config["target"], "controller": self.core.state(),
                "resume": resume, "version": VERSION, "options": self.options_hash()}

    async def async_save(self):
        await self.store.async_save(self.stored())

    # ------------------------------------------------------------------ readings
    def fresh_state(self, key, now):
        entity_id = self.config.get(key)
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", ""):
            return None
        # Unit registers, water sensors and helpers report only on change and can rightly stay
        # unchanged for hours. Their integration's availability governs them, not value age.
        if key in ("output_entity", "operating_entity", "heating_mode_entity", "defrost_entity", "inhibit_entity",
                   "ac_entity", "inlet_entity", "outlet_entity", "restart_hysteresis_entity"):
            return state
        stamp = getattr(state, "last_reported", None) or state.last_updated
        age = (now - stamp).total_seconds()
        if age < -60 or age > self.settings.stale_minutes * 60:
            return None
        return state

    def reading(self, key, now, kind="temperature"):
        state = self.fresh_state(key, now)
        if state is None:
            return None
        unit = state.attributes.get("unit_of_measurement")
        if kind == "power":
            result = power_watts(state.state, unit)
            return result if result is not None and result >= 0 else None
        if kind == "soc":
            result = finite(state.state) if unit == "%" else None
            return result if result is not None and 0 <= result <= 100 else None
        if kind == "energy":
            value = finite(state.state)
            if value is None or value < 0 or unit not in ("Wh", "kWh"):
                return None
            return value / 1000 if unit == "Wh" else value
        if kind == "number":
            return finite(state.state)
        return temperature(state.state, unit)

    def room_input(self, now):
        """Room value and its age for the controller, however old: the controller decides when
        a value is too old (4 h) or frozen (12 h unchanged) and switches to its fallback.

        An 'unavailable' or 'unknown' state (a Zigbee report missed for a minute) keeps the last
        valid value with its true age: dropping the room terms for one minute would swing the
        floor target by kp x the room error and could start a run in a warm room. The value is
        not averaged (0.4.5-0.5.3 averaged 30 minutes; that delay cost comfort); the controller
        limits how fast it may move instead (slab.Params.room_slew)."""
        entity_id = self.config.get("indoor_entity")
        state = self.hass.states.get(entity_id) if entity_id else None
        value = None
        if state is not None and state.state not in ("unknown", "unavailable", ""):
            value = temperature(state.state, state.attributes.get("unit_of_measurement"))
            if value is not None and not 0 <= value <= 45:
                value = None
        if value is not None:
            self.room_last = (value, getattr(state, "last_reported", None) or state.last_updated)
        if self.room_last is None:
            return None, 0.0
        value, stamp = self.room_last
        return value, max(0.0, (now - stamp).total_seconds() / 60)

    def outdoor(self, now):
        outdoor = self.reading("outdoor_entity", now) if self.config.get("outdoor_entity") else None
        if outdoor is None:
            weather = self.fresh_state("weather_entity", now)
            if weather:
                outdoor = temperature(weather.attributes.get("temperature"), weather.attributes.get("temperature_unit"))
        if outdoor is None and self.forecast_cache:
            when, value = min(self.forecast_cache, key=lambda row: abs((row[0] - now).total_seconds()))
            outdoor = value if abs((when - now).total_seconds()) <= 5400 else None
        return outdoor if outdoor is not None and -70 <= outdoor <= 60 else None

    def snapshot(self, now):
        """What the unit and the house show now, and why the controller may not write."""
        indoor = self.reading("indoor_entity", now)
        if indoor is not None and not 0 <= indoor <= 45:
            indoor = None
        outdoor = self.outdoor(now)
        inlet = self.reading("inlet_entity", now)
        outlet = self.reading("outlet_entity", now)
        output = self.reading("output_entity", now)
        operating = self.fresh_state("operating_entity", now)
        state = operating.state if operating is not None else None
        heat = state is not None and state_matches(state, self.config["heating_state"])
        hot_water = state is not None and state_matches(state, self.config["disinfection_hot_water_state"])
        idle = state is not None and state_matches(state, self.config["heating_idle_state"]) and not hot_water
        mode_mapped = bool(self.config.get("heating_mode_entity"))
        heating_mode = self.fresh_state("heating_mode_entity", now) if mode_mapped else None
        mode_enabled = heating_mode is not None and state_matches(heating_mode.state, self.config["heating_mode_state"])
        defrost = None
        if self.config.get("defrost_entity"):
            flag = self.fresh_state("defrost_entity", now)
            defrost = None if flag is None else flag.state == "on"
        if self.config.get("restart_hysteresis_entity"):
            delta = self.reading("restart_hysteresis_entity", now, "number")
            delta = delta if delta is not None and 2 <= delta <= 10 else None
        else:
            delta = self.settings.restart_hysteresis
        # Without a defrost flag, an operating state that names defrost is one.
        defrost_label = (state is not None and not self.config.get("defrost_entity")
                         and "defrost" in str(state).casefold())
        mode, compressor = None, None
        if defrost or defrost_label:
            mode, compressor = "defrost", True
        elif hot_water:
            mode, compressor = "dhw", True
        elif heat:
            mode, compressor = "heat", True
        elif idle:
            mode, compressor = "idle", False
        elif state is not None:
            # A state none of the mappings name: the unit is there but doing something else.
            # The controller freezes its floor estimate and waits, as for a defrost.
            mode, compressor = "other", True
        if mode_mapped and heating_mode is not None and not mode_enabled and mode in ("heat", "idle"):
            mode = "off"
        water_ok = (inlet is not None and 0 <= inlet <= 85 and outlet is not None and 0 <= outlet <= 85)
        link_ok = (water_ok and output is not None and mode is not None and delta is not None
                   and (defrost is not None or not self.config.get("defrost_entity"))
                   and (heating_mode is not None or not mode_mapped))
        # Reasons the controller is not in charge: no writes and no learning.
        control = ""
        if not self.config.get("inlet_entity") or not self.config.get("outlet_entity"):
            control = "Map the return- and supply-water sensors: the controller reads the floor from them"
        elif not mode_mapped:
            control = ("Map the heating-mode entity: the controller starts and stops the compressor itself "
                       "and must know space heating is enabled while the compressor is idle")
        elif heating_mode is not None and not mode_enabled:
            control = "Space-heating mode is off on the heat pump"
        if self.config.get("inhibit_entity"):
            flag = self.fresh_state("inhibit_entity", now)
            if flag is None or flag.state != "off":
                control = "Another controller or inhibit active or unavailable"
        # Reasons this minute cannot write, while the controller stays in charge.
        hold = ""
        if not link_ok:
            hold = "Heat-pump values unavailable (link, defrost or mode sensor); waiting"
        elif outdoor is None:
            hold = "Outdoor temperature unavailable, stale, or invalid"
        if self.disinfection.blocks_heating:
            hold = "Tank disinfection or target restoration in progress; space-heating writes paused"
        return {"time": now.timestamp(), "indoor": indoor, "outdoor": outdoor, "inlet": inlet, "outlet": outlet,
                "output": output, "restart_delta": delta, "mode": mode, "compressor_on": compressor,
                "link_ok": link_ok, "control": control, "hold": hold, "blocked": control or hold,
                "heating_enabled": mode_enabled if mode_mapped and heating_mode is not None else None,
                "compressor_active": compressor, "floor_heating_active": mode == "heat" if mode else None}

    def energy(self, now):
        return Energy(
            pv_w=self.reading("pv_entity", now, "power"),
            import_w=self.reading("import_entity", now, "power"),
            export_w=self.reading("export_entity", now, "power"),
            battery_soc=self.reading("battery_soc_entity", now, "soc"),
            charge_w=self.reading("battery_charge_entity", now, "power"),
            discharge_w=self.reading("battery_discharge_entity", now, "power"),
            battery_configured=any(self.config.get(k) for k in ("battery_soc_entity", "battery_charge_entity", "battery_discharge_entity")),
        )

    def location(self):
        config = getattr(self.hass, "config", None)
        place = (finite(getattr(config, "latitude", None)), finite(getattr(config, "longitude", None)))
        return None if None in place else place

    async def forecasts(self, now):
        """Fetch the hourly forecast every 30 minutes (5 after a failure); rebuild each hour's
        sun from its cloud cover. A failed fetch keeps the previous forecast."""
        every = FORECAST_EVERY if self.forecast_ok else 300
        if self.forecast_checked is not None and (now - self.forecast_checked).total_seconds() < every:
            return
        self.forecast_checked = now
        self.forecast_ok = False
        rows = []
        try:
            async with asyncio.timeout(10):
                result = await self.hass.services.async_call("weather", "get_forecasts",
                    {"entity_id": self.config["weather_entity"], "type": "hourly"},
                    blocking=True, return_response=True)
            state = self.hass.states.get(self.config["weather_entity"])
            unit = state.attributes.get("temperature_unit") if state else None
            for row in (result or {}).get(self.config["weather_entity"], {}).get("forecast", []):
                when = dt_util.parse_datetime(row.get("datetime", ""))
                value = temperature(row.get("temperature"), unit)
                if when is not None and when.tzinfo is not None and value is not None and -70 <= value <= 60:
                    cloud = finite(row.get("cloud_coverage"))
                    if cloud is None:
                        cloud = CONDITION_CLOUD.get(row.get("condition"), 100.0)
                    rows.append((when, value, cloud))
        except (HomeAssistantError, TimeoutError, ValueError, TypeError, AttributeError):
            _LOGGER.debug("Hourly weather forecast unavailable; keeping the previous one")
            return
        rows.sort(key=lambda row: row[0])
        # Reject daily, duplicated or gapped data advertised as hourly.
        if len(rows) < 2 or any(not 1800 <= (b[0] - a[0]).total_seconds() <= 5400 for a, b in zip(rows, rows[1:])):
            return
        self.forecast_ok = True
        self.forecast_cache = [(t, v) for t, v, _ in rows]
        place = self.location()
        # A row is labelled by its own time: the temperature is the forecast for that instant,
        # and the sun is the mean over the hour ending there, as in the lab's forecast rows.
        self.forecast_hours = tuple(
            slab.Hour(when.timestamp() / 60, value, slab.hour_ghi(when, *place, cloud) if place else None)
            for when, value, cloud in rows)

    def forecast_now(self, minute):
        return tuple(h for h in self.forecast_hours if h.minute > minute)

    # ------------------------------------------------------------------ control
    def update_surplus(self, now):
        valid = surplus_available(self.energy(now), self.settings)
        if self.last_energy_sample is not None and (now - self.last_energy_sample).total_seconds() > 600:
            self.surplus_since = None
        self.last_energy_sample = now
        self.surplus_since = (self.surplus_since or now) if valid else None
        return self.surplus_since is not None and (now - self.surplus_since).total_seconds() >= 900

    def track_output(self, snapshot, now):
        output = snapshot["output"]
        if output is None:
            return
        if self.last_seen_output is not None and abs(output - self.last_seen_output) > 0.05:
            if self.last_commanded is None or abs(output - self.last_commanded) > 0.05:
                if self.mode == "automatic":
                    self.hold("manual")
        if self.pending_deadline:
            if abs(output - self.last_commanded) <= 0.05:
                self.pending_deadline, self.unconfirmed = None, 0
            elif now >= self.pending_deadline:
                # Not shown yet: the controller asks again (its own 5-minute rule); a second
                # unconfirmed write pauses Automatic and tells the owner.
                self.pending_deadline = None
                self.unconfirmed += 1
                if self.unconfirmed >= UNCONFIRMED_LIMIT and self.mode == "automatic":
                    self.hold("unconfirmed")
        self.last_seen_output = output

    def hold(self, kind):
        if not self.manual_hold:
            self.manual_hold, self.hold_kind = True, kind

    def ac_request(self):
        """AC assistance is wanted only while the floor is already heating and the room is
        clearly under its target; AC is optional help, the floor never relies on it."""
        e = self.core.e
        if self.mode != "automatic" or self.manual_hold or e is None or not self.core.run:
            return False, "The floor heating covers the room"
        if e >= self.ac.settings.ac_assist_below or (self.ac.session and e > 0):
            return True, f"Room {e:.1f} °C under its target while the floor heats; AC helps"
        return False, "The floor heating covers the room"

    HOLD_TEXT = {
        "manual": "The water setpoint was changed outside Adaptive Heating",
        "unconfirmed": "The heat pump did not show the written setpoint twice",
        "failed": "Setpoint commands failed three times",
    }

    def hold_text(self):
        return (self.HOLD_TEXT.get(self.hold_kind, "Manual change or unconfirmed command")
                + "; select Observe then Automatic to resume")

    def blocked_reason(self, snapshot):
        if self.releases.restart_pending:
            return "Update installed; restart Home Assistant to activate it"
        if self.manual_hold:
            return self.hold_text()
        return snapshot["blocked"]

    async def _async_update_data(self):
        async with self.lock:
            now = dt_util.utcnow()
            sustained = self.update_surplus(now)
            await self.disinfection.async_tick()
            if self.mode != "off":
                await self.forecasts(now)
            requested, ac_reason = self.ac_request()
            await self.ac.async_tick(requested and not self.blocked_reason(self.snapshot(dt_util.utcnow())),
                                     self.settings.target, ac_reason)
            # Forecast, tank and AC calls await I/O: decide and write on a fresh observation.
            now = dt_util.utcnow()
            snapshot = self.snapshot(now)
            self.track_output(snapshot, now)
            result = {"status": "off", "reason": "Control mode is Off", "proposed": None, "limited": None,
                      "commanded": self.last_commanded, "actual": snapshot["output"], "indoor": snapshot["indoor"],
                      "outdoor": snapshot["outdoor"], "surplus": sustained,
                      "electric_power": self.reading("electric_power_entity", now, "power"),
                      "electric_energy": self.reading("electric_energy_entity", now, "energy"),
                      "heating_enabled": snapshot["heating_enabled"], "compressor_active": snapshot["compressor_active"],
                      "floor_heating_active": snapshot["floor_heating_active"],
                      "learning_excluded_by_ac": self.ac.blocks_learning(now), "checked_at": now.isoformat(),
                      "cycle": None, "slab_estimate": None, "slab_target": None, "writes_24h": self.core.writes_24h()}
            if self.mode != "off":
                await self.control(now, snapshot, sustained, result)
            result["commanded"] = self.last_commanded
            key = (result["status"], result.get("note"), result["commanded"])
            if key != self.last_event_key:
                self.last_event_key = key
                self.events = ([{k: result.get(k) for k in ("checked_at", "status", "reason", "proposed", "limited",
                                                            "commanded", "actual", "cycle")}] + self.events)[:20]
            await self.alert_checks(now)
            # A delayed save re-armed every minute would never fire; save on a schedule instead.
            if self.saved_at is None or not 0 <= (now - self.saved_at).total_seconds() < SAVE_EVERY:
                self.saved_at = now
                self.store.async_delay_save(self.stored, 1)
            return result

    def inputs(self, now, snapshot, target, **kw):
        """The controller's view of this minute (unit values repeated while the link is down)."""
        unit = None
        if snapshot["link_ok"]:
            unit = {k: snapshot[k] for k in ("outlet", "inlet", "output", "restart_delta", "compressor_on", "mode")}
            self.unit_last = unit
        last = unit or self.unit_last or {"outlet": math.nan, "inlet": math.nan, "output": math.nan,
                                         "restart_delta": math.nan, "compressor_on": False, "mode": "idle"}
        room, age = self.room_input(now)
        minute = now.timestamp() / 60
        local = dt_util.as_local(now)
        return slab.Inputs(
            minute=minute, local_hour=local.hour + local.minute / 60 + local.second / 3600, target=target,
            outdoor=snapshot["outdoor"] if snapshot["outdoor"] is not None else math.nan,
            outlet=last["outlet"], inlet=last["inlet"], setpoint=last["output"], restart_delta=last["restart_delta"],
            compressor_on=bool(last["compressor_on"]), mode=last["mode"], room=room, room_age_min=age,
            forecast=self.forecast_now(minute), link_ok=unit is not None, **kw)

    async def control(self, now, snapshot, sustained, result):
        """One controller step; in Automatic, the write it asks for."""
        blocked = self.blocked_reason(snapshot)
        in_charge = (self.mode == "automatic" and not self.releases.restart_pending and not self.manual_hold
                     and not snapshot["control"] and not self.shutting_down)
        act = in_charge and not snapshot["hold"]
        if in_charge and not self.in_charge:
            # Handover (Automatic selected or resumed after a restart, a manual hold or inhibit
            # cleared): take the unit as it is. A link drop or tank cycle is not a handover; the
            # controller rides those out.
            self.core.adopt(bool(snapshot["compressor_on"]) and snapshot["mode"] == "heat")
            self.release_pending = False
        self.in_charge = in_charge
        ac_influence = self.ac.blocks_learning(now)
        target = self.settings.target
        room, _ = self.room_input(now)
        preheat = (self.settings.solar_preheat and sustained and room is not None
                   and room < target + self.settings.preheat_degrees)
        if preheat:
            target += self.settings.preheat_degrees
        self.sync_limits()
        # The core never counts a write itself here (act=False): commit() counts it once the
        # device took it, so a refused or failed write does not spend the write budget.
        x = self.inputs(now, snapshot, target, act=False,
                        learn=in_charge and not ac_influence and not preheat, shield=bool(self.ac.session))
        decision = self.core.step(x)
        attributes = self.core.attributes()
        reason = attributes["reason"]
        if preheat:
            reason += "; sustained solar surplus raises the room target a little"
        one = lambda v: None if v is None else round(v, 1)  # noqa: E731 - sensor states, not diagnostics
        result.update(cycle=decision.phase, note=self.core.note, slab_estimate=one(attributes["slab_estimate"]),
                      slab_target=one(attributes["slab_target"]), writes_24h=attributes["writes_24h"],
                      proposed=decision.want, limited=self.device_value(decision.want), reason=reason)
        if self.release_pending and self.mode != "automatic":
            # The previous run ended without handing the unit back (a new version, changed options).
            self.release_pending = False
            await self.release()
        if self.mode == "observe":
            result.update(status="observing", reason="Observe: " + reason)
        elif blocked:
            result.update(status="paused", reason=blocked)
        elif decision.setpoint is None:
            result["status"] = "maintaining"
        elif not act:
            result.update(status="paused", reason=snapshot["hold"] or "Automatic control disabled")
        else:
            value = self.device_value(decision.setpoint)
            if value is None:
                result.update(status="paused", reason="Setpoint or device limits invalid; check the output entity")
            elif await self.apply(value, snapshot["output"], result):
                self.core.commit(x.minute, decision.setpoint)

    def sync_limits(self):
        """Keep the controller's setpoint limits inside the device's own range, so it never
        counts a write the device would clamp away."""
        state = self.hass.states.get(self.config["output_entity"])
        unit = state.attributes.get("unit_of_measurement") if state else None
        lo = temperature(state.attributes.get("min"), unit) if state else None
        hi = temperature(state.attributes.get("max"), unit) if state else None
        base = controller_params(self.settings)
        if lo is not None and hi is not None and lo < hi:
            write_min, write_max = max(base.write_min, lo), min(base.write_max, hi)
            if write_min < write_max:
                base = replace(base, write_min=write_min, write_max=write_max,
                               sp_floor=min(max(base.sp_floor, lo), write_max),
                               sp_ceil=max(min(base.sp_ceil, hi), write_min))
        if base != self.core.p:
            self.core.p = base

    def device_value(self, value):
        """A setpoint (°C) inside the device's range and the configured maximum, on its step grid."""
        state = self.hass.states.get(self.config["output_entity"])
        if value is None or state is None:
            return None
        unit = state.attributes.get("unit_of_measurement")
        lo = temperature(state.attributes.get("min"), unit)
        hi = temperature(state.attributes.get("max"), unit)
        step = finite(state.attributes.get("step"))
        if lo is None or hi is None or step is None or step <= 0:
            return None
        if unit == "°F":
            step /= 1.8
        hi = min(hi, self.settings.maximum_water)
        if lo > hi:
            return None
        index = round((clamp(value, lo, hi) - lo) / step)
        index = min(index, math.floor((hi - lo) / step + 1e-8))
        return round(lo + index * step, 6)

    async def apply(self, value, observed, result):
        """Write one setpoint after a fresh final gate; True when the command was sent."""
        # A fresh final gate: a mode change or manual edit during this cycle stops the write.
        fresh = self.snapshot(dt_util.utcnow())
        if self.shutting_down or self.mode != "automatic" or self.manual_hold or self.releases.restart_pending or fresh["blocked"]:
            reason = self.hold_text() if self.manual_hold else "Automatic control disabled"
            result.update(status="paused", reason=fresh["blocked"] or reason)
            return False
        if fresh["output"] is None or abs(fresh["output"] - observed) > 0.05:
            self.hold("manual")
            result.update(status="paused", reason="Setpoint changed during calculation")
            return False
        if abs(value - observed) < 0.05:
            result["status"] = "maintaining"
            return False
        if await self.send(value):
            result["status"] = "command_sent"
            return True
        if self.manual_hold:
            result.update(status="paused", reason=self.hold_text())
        else:
            result.update(status="paused", reason="Setpoint command failed; trying again next minute")
        return False

    async def send(self, value):
        """The single number.set_value call (°C in, the entity's own unit out)."""
        state = self.hass.states.get(self.config["output_entity"])
        native_value = value * 1.8 + 32 if state.attributes.get("unit_of_measurement") == "°F" else value
        try:
            async with asyncio.timeout(10):
                await self.hass.services.async_call("number", "set_value",
                    {"entity_id": self.config["output_entity"], "value": round(native_value, 6)}, blocking=True)
        except (HomeAssistantError, TimeoutError):
            self.write_failures += 1
            if self.write_failures >= FAILED_LIMIT and self.mode == "automatic":
                self.hold("failed")
            return False
        self.write_failures = 0
        self.last_commanded = value
        self.pending_deadline = dt_util.utcnow() + timedelta(minutes=CONFIRM_MINUTES)
        return True

    async def release(self):
        """Hand the unit back: leave the controller's idle setpoint (slab.release), so the unit's
        own restart rule keeps the floor near its start point instead of riding a run or staying
        stopped with nobody watching. Not while another controller or an inhibit owns the unit,
        a tank cycle runs, the link is down, or the owner set the value by hand."""
        now = dt_util.utcnow()
        snapshot = self.snapshot(now)
        if (snapshot["control"] or not snapshot["link_ok"] or self.manual_hold
                or self.disinfection.blocks_heating or self.core.ts_star is None):
            return False
        x = self.inputs(now, snapshot, self.settings.target, act=False, learn=False)
        sp = self.core.release(x)
        value = self.device_value(sp)
        if sp is None or value is None or abs(value - snapshot["output"]) < 0.05:
            return False
        if not await self.send(value):
            return False
        self.core.commit(x.minute, sp)
        self.events = ([{"checked_at": now.isoformat(), "status": "released", "commanded": value,
                         "reason": "Automatic ended; idle setpoint left on the heat pump"}] + self.events)[:20]
        return True

    async def alert_checks(self, now):
        """Persistent notifications: a lost room thermometer (after an hour), a paused Automatic,
        and runs the unit keeps starting by itself. Each is cleared when its cause is gone."""
        lost = self.mode == "automatic" and self.core.room_state != "ok" and self.core.last_minute is not None
        self.room_lost_since = (self.room_lost_since or now) if lost else None
        room = lost and (now - self.room_lost_since).total_seconds() >= ROOM_ALERT_MINUTES * 60
        await self.alert("room", room, "Adaptive Heating: room sensor", "The room temperature sensor is "
                         + {"missing": "unavailable", "stale": "not reporting",
                            "frozen": "stuck on one value"}.get(self.core.room_state, "unusable")
                         + ". Heating continues on the learned outdoor curve, which cannot follow the season. Check the sensor.")
        await self.alert("hold", self.mode == "automatic" and self.manual_hold, "Adaptive Heating: Automatic paused",
                         self.hold_text() + ". The heat pump keeps the setpoint it has now.")
        unowned = self.mode == "automatic" and self.core.unowned_24h() >= UNOWNED_ALERT
        delta = self.core.restart_delta
        await self.alert("unowned", unowned, "Adaptive Heating: unexpected starts",
                         "The heat pump started runs by itself that the floor did not need "
                         f"{self.core.unowned_24h()} times in 24 h. Its restart hysteresis may be smaller than the "
                         f"{delta if delta is not None else '?'} K in use: map its register or set the option to the unit's value.")

    async def alert(self, kind, active, title, message):
        if active == (kind in self.alerts):
            return
        data = {"notification_id": f"{DOMAIN}_{self.entry.entry_id}_{kind}"}
        if active:
            self.alerts.add(kind)
            data |= {"title": title, "message": message}
        else:
            self.alerts.discard(kind)
        try:
            async with asyncio.timeout(10):
                await self.hass.services.async_call("persistent_notification", "create" if active else "dismiss",
                                                    data, blocking=True)
        except (HomeAssistantError, TimeoutError):
            pass

    # ------------------------------------------------------------------ commands
    async def async_mode(self, mode):
        if mode not in MODES:
            raise HomeAssistantError("Invalid controller mode")
        if mode == "automatic" and self.releases.restart_pending:
            raise HomeAssistantError("Restart Home Assistant after installing the update")
        if mode != "automatic":
            # Disable immediately; do not wait behind a network operation.
            self.mode = mode
        async with self.lock:
            if mode != "automatic" and self.in_charge:
                # Automatic ends: hand the unit back with the idle setpoint.
                await self.release()
            self.in_charge = self.in_charge and mode == "automatic"
            self.mode = self.resume = mode
            self.manual_hold, self.hold_kind = False, None
            self.pending_deadline, self.unconfirmed, self.write_failures = None, 0, 0
            if mode == "automatic":
                self.release_pending = False
            await self.async_save()
        await self.async_request_refresh()

    async def async_target(self, target):
        if finite(target) is None or not 10 <= target <= 30:
            raise HomeAssistantError("Target must be 10–30 Celsius")
        async with self.lock:
            self.settings.target = round(target, 1)
            await self.async_save()
        await self.async_request_refresh()

    async def async_ac_mode(self, mode):
        if mode not in MODES:
            raise HomeAssistantError("Invalid AC mode")
        if mode != "automatic":
            self.ac.mode = mode
        async with self.lock:
            await self.ac.async_mode(mode)
        await self.async_request_refresh()

    async def async_ac_tick(self, _event=None):
        """Frequent ownership, temperature and timeout checks between controller steps."""
        async with self.lock:
            requested, reason = self.ac_request()
            await self.ac.async_tick(requested and not self.shutting_down, self.settings.target, reason)
        self.async_update_listeners()

    async def async_disinfection_tick(self, _event=None):
        async with self.lock:
            await self.disinfection.async_tick()
        self.async_update_listeners()

    async def async_disinfection_mode(self, mode):
        if mode not in MODES:
            raise HomeAssistantError("Invalid disinfection mode")
        if mode == "automatic" and (self.shutting_down or self.releases.restart_pending):
            raise HomeAssistantError("Restart or reload must finish before enabling disinfection")
        if mode != "automatic":
            self.disinfection.mode = mode
        async with self.lock:
            self.disinfection.mode = mode
            await self.disinfection.async_tick()
        self.async_update_listeners()

    async def async_disinfection_run(self):
        async with self.lock:
            if self.shutting_down:
                raise HomeAssistantError("Controller is unloading")
            await self.disinfection.async_start()
        self.async_update_listeners()

    async def async_disinfection_cancel(self):
        async with self.lock:
            await self.disinfection.async_cancel()
        self.async_update_listeners()

    async def async_stop(self, _event=None):
        """Home Assistant stops (entries are not unloaded): keep the learned state. Automatic
        resumes after the restart, so the unit keeps its setpoint for those minutes - unless an
        installed update means the next start is a new version in Observe: then hand it back."""
        async with self.lock:
            if self.releases.restart_pending and self.in_charge:
                await self.release()
            await self.async_save()

    async def async_prepare_unload(self):
        in_charge = self.in_charge and self.mode == "automatic"
        self.shutting_down = True
        self.mode = self.disinfection.mode = "off"
        self.ac.mode = "off"
        async with self.lock:
            if in_charge:
                # A reload, an options change or removal: hand the unit back first.
                await self.release()
            self.in_charge = False
            ac_restored = await self.ac.async_prepare_unload()
            if self.disinfection.cycle and self.disinfection.cycle["phase"] not in ("restoring", "recovery_required"):
                await self.disinfection.abort("interrupted", "Controller unloading; restoring normal tank target")
            await self.disinfection.async_tick()
        # Keep listeners alive if restoration still needs acknowledgment/retry.
        if self.disinfection.blocks_heating or not ac_restored:
            self.shutting_down = False
            self.async_update_listeners()
            return False
        return True
