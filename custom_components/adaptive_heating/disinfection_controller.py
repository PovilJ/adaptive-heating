"""Journaled tank-setpoint controller, serialized by the heating coordinator.

Only the normal tank number is written. No native disinfection, compressor,
operating-mode, heater, or battery control is used.
"""

import asyncio
from datetime import datetime, timezone
import math

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MODES
from .disinfection import DisinfectionSettings, TemperatureHold, schedule
from .engine import finite, surplus_available, temperature

ACK_SECONDS = 120
RESTORE_ATTEMPTS = 3


def native_target(state, celsius):
    """Reject impossible targets instead of silently changing a hold policy."""
    if state is None or state.state in ("unknown", "unavailable", ""):
        raise ValueError("Tank target unavailable")
    attrs = state.attributes
    unit = attrs.get("unit_of_measurement")
    if unit not in ("°C", "°F") or finite(celsius) is None:
        raise ValueError("Tank target must use Celsius or Fahrenheit")
    value = celsius * 1.8 + 32 if unit == "°F" else celsius
    lo, hi, step = (finite(attrs.get(k)) for k in ("min", "max", "step"))
    if lo is None or hi is None or step is None or step <= 0 or not lo <= value <= hi:
        raise ValueError("Tank target outside device limits or invalid limits")
    steps = (value - lo) / step
    if not math.isclose(steps, round(steps), abs_tol=0.00001):
        raise ValueError("Tank target does not match the device step")
    return round(value, 6)


class DisinfectionController:
    def __init__(self, owner):
        self.owner = owner
        self.hass = owner.hass
        self.settings = DisinfectionSettings(**{k: owner.config[k] for k in DisinfectionSettings.__dataclass_fields__})
        self.store = Store(self.hass, 1, f"{DOMAIN}.{owner.entry.entry_id}.disinfection")
        self.mode = "observe"
        self.cycle = None
        self.hold = TemperatureHold()
        self.last_success = None
        self.events = []
        self.latched = False
        self.status = "not_configured"
        self.reason = "Select a tank temperature sensor and normal tank target in Configure"
        self.eligible = False
        self.manual_override = False
        self.corrupt_journal = False

    @property
    def configured(self):
        return all(self.owner.config.get(k) for k in ("tank_temperature_entity", "tank_target_entity"))

    @property
    def blocks_heating(self):
        return self.cycle is not None or self.corrupt_journal

    def identity(self):
        return {k: self.owner.config.get(k) for k in ("tank_temperature_entity", "tank_target_entity")}

    def now(self):
        return dt_util.utcnow().timestamp()

    def event(self, kind, reason):
        self.events = [{"time": datetime.fromtimestamp(self.now(), timezone.utc).isoformat(),
                        "status": kind, "reason": reason}] + self.events[:19]

    async def save(self):
        await self.store.async_save({"identity": self.identity(), "last_success": self.last_success,
                                    "cycle": self.cycle, "events": self.events, "latched": self.latched})

    async def async_load(self):
        data = await self.store.async_load() or {}
        if not isinstance(data, dict):
            data = {"cycle": "invalid"}
        self.events = data.get("events", [])[:20] if isinstance(data.get("events"), list) else []
        if data.get("identity") == self.identity():
            self.last_success = finite(data.get("last_success"))
            if self.last_success is not None and self.last_success < 0:
                self.last_success = None
            self.latched = bool(data.get("latched"))
        saved = data.get("cycle")
        if saved is not None:
            valid = (isinstance(saved, dict)
                     and str(saved.get("target_entity", "")).startswith("number.")
                     and all(finite(saved.get(k)) is not None for k in
                             ("original", "boost", "started", "deadline", "command_at"))
                     and 0 <= finite(saved["original"]) <= 90 and 40 <= finite(saved["boost"]) <= 80)
            if not valid:
                self.corrupt_journal = True
                self.status = "recovery_required"
                self.reason = "Invalid saved cycle; inspect the physical tank target and saved recovery data"
                await self.notify(self.reason)
                return
            self.cycle = saved
            for key in ("original", "boost", "started", "deadline", "command_at"):
                self.cycle[key] = float(saved[key])
            # A clock correction must not leave restoration waiting indefinitely.
            self.cycle["command_at"] = min(self.cycle["command_at"], self.now())
            self.cycle.update(phase="restoring", outcome="interrupted", outcome_reason="Cycle interrupted by restart or reload",
                              restore_attempts=0, restore_sent_at=None)
            self.hold.reset()
            self.event("interrupted", self.cycle["outcome_reason"])
            await self.save()
        # A restart never resumes boosting or counts unobserved hold time.

    def target_state(self, entity=None):
        return self.hass.states.get(entity or self.owner.config.get("tank_target_entity", ""))

    def target_value(self, entity=None):
        state = self.target_state(entity)
        return temperature(state.state, state.attributes.get("unit_of_measurement")) if state else None

    def tank_reading(self, now):
        state = self.hass.states.get(self.owner.config.get("tank_temperature_entity", ""))
        if state is None:
            return None, None
        stamp = (getattr(state, "last_reported", None) or state.last_updated).timestamp()
        value = temperature(state.state, state.attributes.get("unit_of_measurement"))
        if value is None or not 0 <= value <= 90 or not 0 <= now - stamp <= self.settings.disinfection_sample_seconds:
            return None, stamp
        return value, stamp

    def guard(self, now, *, starting=False):
        if starting and self.owner.shutting_down:
            return "Controller is unloading"
        if not self.configured:
            return "Tank entities are not configured"
        if self.owner.config["tank_target_entity"] == self.owner.config["output_entity"]:
            return "Tank and space-heating setpoints must be different entities"
        if self.owner.releases.restart_pending:
            return "An update is installed; restart Home Assistant before starting a cycle"
        instant = datetime.fromtimestamp(now, timezone.utc)
        for key, label in (("inhibit_entity", "Other controller/inhibit"), ("defrost_entity", "Defrost")):
            if key == "defrost_entity" and not starting:
                continue
            if self.owner.config.get(key):
                flag = self.owner.fresh_state(key, instant)
                if flag is None or flag.state != "off":
                    return f"{label} active or unavailable"
        operating = self.owner.fresh_state("operating_entity", instant)
        states = [self.owner.config[k].strip().casefold() for k in
                  ("heating_state", "disinfection_hot_water_state", "disinfection_idle_state")]
        if operating is None or operating.state.casefold() not in states:
            return "Heat-pump operating state is unavailable or outside the configured heating/hot-water/idle states"
        if self.tank_reading(now)[0] is None:
            return "Tank temperature unavailable, stale, or invalid"
        try:
            native_target(self.target_state(), self.settings.disinfection_target)
            original = self.target_value()
            native_target(self.target_state(), original)
        except ValueError as err:
            return str(err)
        return ""

    def opportunity(self, now):
        instant = datetime.fromtimestamp(now, timezone.utc)
        snapshot = self.owner.snapshot(instant)
        energy = self.owner.energy(instant)
        sustained = (self.owner.surplus_since is not None and self.owner.last_energy_sample is not None
                     and 0 <= (instant - self.owner.last_energy_sample).total_seconds() <= 600
                     and (instant - self.owner.surplus_since).total_seconds() >= 900
                     and surplus_available(energy, self.owner.settings))
        battery_ready = (not energy.battery_configured or
                         (all(v is not None for v in (energy.battery_soc, energy.charge_w, energy.discharge_w))
                          and energy.battery_soc >= self.owner.settings.battery_ready_soc
                          and energy.charge_w <= 100 and energy.discharge_w <= 50))
        operating = self.owner.fresh_state("operating_entity", instant)
        forecast = [v for t, v in sorted(self.owner.forecast_cache) if 0 <= (t - instant).total_seconds() <= 21600]
        return schedule(self.settings, now=now, last_success=self.last_success,
                        indoor=snapshot["indoor"], room_target=self.owner.settings.target,
                        comfort_band=self.owner.settings.comfort_band, tank=self.tank_reading(now)[0],
                        hot_water=bool(operating and operating.state.casefold() == self.owner.config["disinfection_hot_water_state"].strip().casefold()),
                        outdoor=snapshot["outdoor"], forecast=forecast, local_hour=dt_util.as_local(instant).hour,
                        surplus=sustained, battery_ready=battery_ready)

    async def async_start(self, reason="Manually requested cycle"):
        if self.cycle or self.corrupt_journal:
            raise HomeAssistantError("Resolve the active cycle or restoration before starting another")
        if self.mode != "automatic":
            raise HomeAssistantError("Select Automatic in Disinfection mode before running a cycle")
        now = self.now()
        error = self.guard(now, starting=True)
        if error:
            raise HomeAssistantError(error)
        original = self.target_value()
        if original >= self.settings.disinfection_target:
            raise HomeAssistantError("Normal tank target must be below the disinfection target")
        self.cycle = {"phase": "starting", "target_entity": self.owner.config["tank_target_entity"],
                      "original": original, "boost": self.settings.disinfection_target,
                      "started": now, "command_at": now, "acknowledged": False,
                      "deadline": now + self.settings.disinfection_timeout_hours * 3600,
                      "restore_attempts": 0, "restore_sent_at": None}
        self.hold.reset()
        self.latched = self.manual_override = False
        self.owner.previous = None
        self.owner.model.emitter = None
        self.event("starting", reason)
        # Persist ownership and the original target BEFORE any device write.
        await self.save()
        error = self.guard(self.now(), starting=True)
        if self.mode != "automatic" or error or self.target_value() != original:
            # No write has been submitted, so nothing needs restoring.
            await self.finish("cancelled", error or "Mode or tank target changed before the command")
            return
        self.status, self.reason = "starting", reason
        try:
            await self.write(self.cycle["target_entity"], self.cycle["boost"])
        except (HomeAssistantError, TimeoutError, ValueError):
            # The device might still receive a timed-out service command.
            await self.abort("failed", "Boost command failed or timed out; verifying restoration")

    async def write(self, entity, value):
        native = native_target(self.target_state(entity), value)
        async with asyncio.timeout(10):
            await self.hass.services.async_call("number", "set_value", {"entity_id": entity, "value": native}, blocking=True)

    async def abort(self, outcome, reason):
        if self.cycle is None:
            return
        self.cycle.update(phase="restoring", outcome=outcome, outcome_reason=reason)
        self.hold.reset()
        await self.save()
        await self.restore(self.now())

    async def finish(self, outcome, reason):
        if outcome == "completed":
            self.last_success = self.cycle["hold_completed_at"]
        self.latched = outcome != "completed"
        self.cycle = None
        self.hold.reset()
        self.owner.previous = None
        self.owner.model.emitter = None
        self.status, self.reason = outcome, reason
        self.event(outcome, reason)
        await self.save()
        if self.latched:
            await self.notify(reason + ". Inspect Disinfection status; a new manual run is required before scheduling resumes.")

    async def restore(self, now):
        cycle = self.cycle
        self.status, self.reason = cycle["phase"], cycle.get("recovery_reason", cycle.get("outcome_reason", "Restoring normal tank target"))
        current = self.target_value(cycle["target_entity"])
        if current is not None and abs(current - cycle["original"]) < 0.05:
            # An early cancel must not forget a boost command still in flight.
            if cycle.get("acknowledged") or now >= cycle["command_at"] + ACK_SECONDS:
                await self.finish(cycle["outcome"], cycle["outcome_reason"] + "; normal tank target confirmed")
            return
        if current is not None and abs(current - cycle["boost"]) >= 0.05:
            await self.finish("manual_override", "Tank target changed externally; left the user's target untouched")
            return
        if cycle["phase"] == "recovery_required":
            return
        sent = cycle.get("restore_sent_at")
        if sent is not None and now - sent < ACK_SECONDS:
            return
        if cycle.get("restore_attempts", 0) >= RESTORE_ATTEMPTS:
            cycle["phase"] = self.status = "recovery_required"
            self.reason = "Normal tank target could not be confirmed; check the device, then press Cancel / restore"
            cycle["recovery_reason"] = self.reason
            self.event("recovery_required", self.reason)
            await self.save()
            await self.notify(self.reason)
            return
        cycle["restore_attempts"] = cycle.get("restore_attempts", 0) + 1
        cycle["restore_sent_at"] = now
        await self.save()
        if current is None:
            return
        cycle["acknowledged"] = True
        # Re-read after storage/network awaits. Never overwrite a manual change.
        fresh = self.target_value(cycle["target_entity"])
        if fresh is None or abs(fresh - cycle["boost"]) >= 0.05:
            return
        try:
            await self.write(cycle["target_entity"], cycle["original"])
        except (HomeAssistantError, TimeoutError, ValueError):
            return
        # A service response is not device acknowledgment; a later tick verifies it.

    async def async_tick(self):
        now = self.now()
        if self.corrupt_journal:
            return
        if self.cycle:
            cycle = self.cycle
            self.status = cycle["phase"]
            if cycle["phase"] in ("restoring", "recovery_required"):
                await self.restore(now)
                return
            if self.mode != "automatic":
                await self.abort("cancelled", "Disinfection control left Automatic")
                return
            if now < cycle["started"] or now >= cycle["deadline"]:
                await self.abort("timed_out", "Cycle runtime expired or the clock moved backwards")
                return
            error = self.guard(now)
            if error:
                await self.abort("failed", error)
                return
            current = self.target_value(cycle["target_entity"])
            if self.manual_override or (abs(current - cycle["boost"]) >= 0.05 and cycle.get("acknowledged")):
                await self.finish("manual_override", "Tank target changed externally; automatic restoration skipped")
                return
            if abs(current - cycle["boost"]) >= 0.05:
                if abs(current - cycle["original"]) >= 0.05:
                    await self.finish("manual_override", "Tank target changed while boost was awaiting acknowledgment")
                elif now >= cycle["command_at"] + ACK_SECONDS:
                    await self.abort("failed", "Tank boost was not acknowledged within two minutes")
                else:
                    self.reason = "Waiting for the device to confirm the boosted tank target"
                return
            if not cycle.get("acknowledged"):
                cycle["acknowledged"] = True
                await self.save()
            defrost = self.owner.fresh_state("defrost_entity", datetime.fromtimestamp(now, timezone.utc))
            if self.owner.config.get("defrost_entity") and (defrost is None or defrost.state != "off"):
                self.hold.reset()
                cycle["phase"] = self.status = "heating"
                self.reason = "Defrost active or unavailable; hold reset, overall timeout still running"
                return
            value, stamp = self.tank_reading(now)
            complete = self.hold.observe(now, stamp, value, self.settings) if stamp >= cycle["command_at"] else False
            cycle["phase"] = self.status = "holding" if self.hold.since is not None else "heating"
            self.reason = ("Maintaining the configured continuous temperature hold" if self.status == "holding"
                           else "Heating the tank to the configured hold threshold")
            if complete:
                cycle["hold_completed_at"] = now
                self.event("hold_complete", "Continuous temperature hold met; restoring normal target")
                await self.abort("completed", "Temperature hold completed")
            return
        if not self.configured:
            self.status, self.reason = "not_configured", "Select the tank temperature and normal tank target in Configure"
            return
        self.eligible, reason = self.opportunity(now)
        error = self.guard(now, starting=True)
        if self.latched:
            self.status, self.reason = "attention_required", "Previous cycle did not complete; inspect history and start a new manual run"
        elif self.mode == "off":
            self.status, self.reason = "off", "Disinfection scheduling is off"
        elif error:
            self.status, self.reason = "blocked", error
        elif self.mode == "observe":
            self.status, self.reason = "observe", ("Would start: " if self.eligible else "") + reason
        elif self.eligible:
            try:
                await self.async_start(reason)
            except HomeAssistantError as err:
                self.status, self.reason = "blocked", str(err)
        else:
            self.status, self.reason = "waiting", reason

    async def async_cancel(self):
        if self.corrupt_journal:
            raise HomeAssistantError(self.reason)
        if self.cycle:
            self.cycle.update(restore_attempts=0, restore_sent_at=None)
            self.cycle.pop("recovery_reason", None)
            await self.abort("cancelled", "Cycle cancelled; restoring normal target")

    async def notify(self, message):
        try:
            async with asyncio.timeout(10):
                await self.hass.services.async_call("persistent_notification", "create",
                    {"title": "Adaptive Heating: disinfection needs attention", "message": message,
                     "notification_id": f"{DOMAIN}_{self.owner.entry.entry_id}_disinfection"}, blocking=True)
        except (HomeAssistantError, TimeoutError):
            pass

    def attributes(self):
        cycle = self.cycle or {}
        return {"mode": self.mode, "reason": self.reason, "recent_cycles": self.events,
                "target_temperature": self.settings.disinfection_target,
                "hold_threshold": self.settings.disinfection_threshold,
                "hold_minutes": self.settings.disinfection_hold_minutes,
                "hold_seconds": self.hold.seconds,
                "original_target": cycle.get("original"), "started_at": cycle.get("started"),
                "timeout_at": cycle.get("deadline"), "last_success": self.last_success,
                "next_eligible": self.last_success + self.settings.disinfection_min_days * 86400 if self.last_success else None,
                "due_by": self.last_success + self.settings.disinfection_max_days * 86400 if self.last_success else None,
                "requires_attention": self.latched or self.corrupt_journal or cycle.get("phase") == "recovery_required"}
