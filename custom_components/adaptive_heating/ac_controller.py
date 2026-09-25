"""Optional, journaled climate assistance. All lifecycle calls use the owner's lock.

The controller only borrows a verified OFF unit. It never changes fan/swing or
claims COP/savings from temperature or electric power. A service response is not
an acknowledgment: subsequent climate state must match the requested settings.
"""

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MODES
from .engine import finite, power_watts, temperature

DEFAULTS = {
    "ac_min_outdoor": -10.0,
    "ac_max_session_minutes": 120.0,
    "ac_min_on_minutes": 20.0,
    "ac_min_off_minutes": 20.0,
    "ac_settle_minutes": 60.0,
    "ac_max_session_kwh": 2.0,
    "ac_sample_seconds": 600.0,
    "ac_preheat_max": 23.0,
}
ENTITIES = {"ac_entity": ["climate"], "ac_room_entity": ["sensor"], "ac_power_entity": ["sensor"]}
ACK_SECONDS = 120
RESTORE_ATTEMPTS = 3


@dataclass(frozen=True)
class ACSettings:
    ac_min_outdoor: float = -10
    ac_max_session_minutes: float = 120
    ac_min_on_minutes: float = 20
    ac_min_off_minutes: float = 20
    ac_settle_minutes: float = 60
    ac_max_session_kwh: float = 2
    ac_sample_seconds: float = 600
    ac_preheat_max: float = 23

    def __post_init__(self):
        if any(finite(v) is None for v in asdict(self).values()):
            raise ValueError("Non-finite AC setting")
        if not -30 <= self.ac_min_outdoor <= 15 or not 18 <= self.ac_preheat_max <= 26:
            raise ValueError("Invalid AC outdoor limit or preheat ceiling")
        if not 10 <= self.ac_min_on_minutes <= self.ac_max_session_minutes <= 180:
            raise ValueError("AC minimum run must be 10 minutes or more and fit within the maximum session")
        if not 10 <= self.ac_min_off_minutes <= 120 or not 30 <= self.ac_settle_minutes <= 180:
            raise ValueError("Invalid AC rest or learning settling period")
        if not 0.1 <= self.ac_max_session_kwh <= 10 or not 60 <= self.ac_sample_seconds <= 900:
            raise ValueError("Invalid AC energy budget or maximum sensor age")


def climate_unit(hass, state):
    """HA climate state temperatures and service inputs use HA's display unit."""
    unit = getattr(getattr(getattr(hass, "config", None), "units", None), "temperature_unit", None)
    unit = unit or state.attributes.get("temperature_unit")
    if unit not in ("°C", "°F"):
        raise ValueError("AC temperature unit unavailable or unsupported")
    return unit


def climate_entity(hass, entity_id):
    component = getattr(hass, "data", {}).get("climate")
    return component.get_entity(entity_id) if component is not None and hasattr(component, "get_entity") else None


def reported_target(hass, entity_id, state, celsius):
    """Predict HA display rounding without broadening manual-change tolerance."""
    entity = climate_entity(hass, entity_id)
    precision = getattr(entity, "precision", None)
    if precision is None:
        return celsius
    unit = climate_unit(hass, state)
    value = celsius * 1.8 + 32 if unit == "°F" else celsius
    if precision == 0.5:
        value = round(value * 2) / 2
    elif precision == 0.1:
        value = round(value, 1)
    else:
        value = round(value)
    return temperature(value, unit)


def target_for_device(hass, entity_id, state, celsius):
    """Round DOWN on the advertised grid and return (HA service value, Celsius).

HA converts min/max/targets to the display unit, but passes target_temp_step
through from the native entity. Read its native unit when that entity is local.
"""
    if state is None or state.state in ("unknown", "unavailable", ""):
        raise ValueError("AC unavailable")
    attrs = state.attributes
    modes = attrs.get("hvac_modes", [])
    features = finite(attrs.get("supported_features"))
    if not isinstance(modes, (list, tuple)) or not all(m in modes for m in ("heat", "off")):
        raise ValueError("AC must support explicit Heat and Off modes")
    if features is None or features != int(features) or not int(features) & 1:
        raise ValueError("AC must support a single target temperature")
    unit = climate_unit(hass, state)
    native_unit = unit
    entity = climate_entity(hass, entity_id)
    if entity is not None:
        native_unit = entity.temperature_unit
    if native_unit not in ("°C", "°F") or finite(celsius) is None:
        raise ValueError("Invalid AC target or native temperature unit")
    low, high = (temperature(attrs.get(k), unit) for k in ("min_temp", "max_temp"))
    step = finite(attrs.get("target_temp_step"))
    if entity is not None:
        # Displayed Fahrenheit bounds can be rounded to whole degrees; their
        # rounded values must not become the origin of a native Celsius grid.
        native_low = temperature(getattr(entity, "min_temp", None), native_unit)
        native_high = temperature(getattr(entity, "max_temp", None), native_unit)
        if native_low is not None and native_high is not None:
            low, high = native_low, native_high
    if low is None or high is None or step is None or step <= 0 or not low <= celsius <= high:
        raise ValueError("AC target outside device limits or temperature step unavailable")
    step_c = step / 1.8 if native_unit == "°F" else step
    rounded = low + math.floor((celsius - low) / step_c + 1e-7) * step_c
    if not low <= rounded <= high or rounded > celsius + 1e-6:
        raise ValueError("AC target cannot be represented within its limits")
    return round(rounded * 1.8 + 32 if unit == "°F" else rounded, 6), round(rounded, 6)


class ACController:
    def __init__(self, owner):
        self.owner, self.hass = owner, owner.hass
        self.settings = ACSettings(**{k: owner.config.get(k, v) for k, v in DEFAULTS.items()})
        self.store = Store(self.hass, 1, f"{DOMAIN}.{owner.entry.entry_id}.ac")
        self.mode = "observe"
        self.status, self.reason = "not_configured", "Select an AC and external room thermometer in Configure"
        self.session = None
        self.latched = self.corrupt_journal = False
        self.storage_fault = False
        self.requested = False
        self.requested_target = None
        self.stopped_at = self.now()
        self.blocked_until = self.now() + self.settings.ac_settle_minutes * 60
        self.last_mode = None
        self.last_energy_kwh = None

    @property
    def configured(self):
        return all(self.owner.config.get(k) for k in ("ac_entity", "ac_room_entity"))

    @property
    def recovery_pending(self):
        return self.corrupt_journal or self.storage_fault or bool(self.session and self.session["phase"] in ("stopping", "recovery_required"))

    def now(self):
        return dt_util.utcnow().timestamp()

    def state(self, entity=None):
        return self.hass.states.get(entity or self.owner.config.get("ac_entity", ""))

    def current_target(self, state):
        if state is None:
            return None
        try:
            return temperature(state.attributes.get("temperature"), climate_unit(self.hass, state))
        except ValueError:
            return None

    def matches(self, state):
        target = self.current_target(state)
        expected = (reported_target(self.hass, self.session["entity"], state, self.session["target"])
                    if self.session and state and target is not None else None)
        return bool(self.session and state and state.state == "heat" and target is not None
                    and abs(target - expected) < 0.05)

    def blocks_learning(self, now):
        """Conservative across both interval endpoints, even for manual operation."""
        if not self.owner.config.get("ac_entity") and self.session is None and not self.corrupt_journal:
            return False
        stamp = now.timestamp() if hasattr(now, "timestamp") else float(now)
        state = self.state(self.session["entity"] if self.session else None)
        current = state.state if state else "unknown"
        if self.last_mode not in (None, "off", "fan_only") and current == "off":
            self.stopped_at = stamp
        self.last_mode = current
        if self.session or self.corrupt_journal or current not in ("off", "fan_only"):
            self.blocked_until = max(self.blocked_until, stamp + self.settings.ac_settle_minutes * 60)
            return True
        return stamp <= self.blocked_until

    def sample(self, key, now, kind="temperature"):
        state = self.hass.states.get(self.owner.config.get(key, ""))
        if state is None:
            return None, None
        reported = getattr(state, "last_reported", None) or state.last_updated
        stamp = reported.timestamp()
        if not 0 <= now - stamp <= self.settings.ac_sample_seconds:
            return None, stamp
        unit = state.attributes.get("unit_of_measurement")
        value = power_watts(state.state, unit) if kind == "power" else temperature(state.state, unit)
        if value is None or (kind == "power" and not 0 <= value <= 30000) or (kind != "power" and not 0 <= value <= 45):
            return None, stamp
        return value, stamp

    def guard(self, now, target, *, starting=False):
        if not self.configured:
            return "AC and external room thermometer are not configured"
        if self.owner.shutting_down or self.owner.releases.restart_pending:
            return "Controller unloading or restart required"
        instant = datetime.fromtimestamp(now, timezone.utc)
        snapshot = self.owner.snapshot(instant)
        if hasattr(self.owner, "track_output"):
            self.owner.track_output(snapshot, instant)
        if self.owner.manual_hold:
            return "Main heating is on manual hold"
        if snapshot["blocked"]:
            return snapshot["blocked"]
        outdoor = finite(snapshot.get("outdoor"))
        if outdoor is None or outdoor < self.settings.ac_min_outdoor:
            return "Outdoor temperature below the configured AC limit or unavailable"
        room = self.sample("ac_room_entity", now)[0]
        if room is None:
            return "External AC room temperature unavailable, stale, or invalid"
        ceiling = min(self.settings.ac_preheat_max, self.owner.config.get("preheat_ceiling", self.settings.ac_preheat_max))
        if room >= ceiling:
            return "AC room reached the preheat ceiling"
        if finite(target) is None or not 10 <= target <= ceiling:
            return "AC target unavailable or outside the preheat ceiling"
        try:
            _, target = target_for_device(self.hass, self.owner.config["ac_entity"], self.state(), target)
        except ValueError as error:
            return str(error)
        if starting and room >= target - 0.3:
            return "AC room already near the preparation target"
        if self.owner.config.get("ac_power_entity") and self.sample("ac_power_entity", now, "power")[0] is None:
            return "Configured AC power meter unavailable, stale, or invalid"
        return ""

    async def save(self):
        await self.store.async_save({"session": self.session, "latched": self.latched,
                                    "stopped_at": self.stopped_at, "blocked_until": self.blocked_until,
                                    "last_energy_kwh": self.last_energy_kwh})

    async def save_recovery(self):
        """A previously journaled owner can still send Off if storage is full.

        The existing journal survives failed writes. If clearing it fails after
        confirmed Off, block new sessions/unload and retry the clear on ticks.
        Starting a session never uses this best-effort persistence path.
        """
        try:
            await self.save()
        except (OSError, HomeAssistantError):
            first_failure = not self.storage_fault
            self.storage_fault = self.latched = True
            if first_failure:
                await self.notify("AC recovery storage failed; owned Off is still attempted, and the recovery journal remains pending")
            return False
        self.storage_fault = False
        return True

    async def async_load(self):
        data = await self.store.async_load() or {}
        if not isinstance(data, dict):
            data = {"session": "invalid"}
        self.latched = bool(data.get("latched"))
        self.last_energy_kwh = finite(data.get("last_energy_kwh"))
        self.stopped_at = self.now()  # A restart cannot erase the minimum rest period.
        self.blocked_until = self.now() + self.settings.ac_settle_minutes * 60
        saved = data.get("session")
        if saved is not None:
            valid = (isinstance(saved, dict) and str(saved.get("entity", "")).startswith("climate.")
                     and saved.get("original") == "off"
                     and all(finite(saved.get(k)) is not None for k in ("target", "started", "command_at", "deadline"))
                     and 10 <= finite(saved["target"]) <= 26
                     and saved.get("phase") in ("starting", "running", "stopping", "recovery_required"))
            if not valid:
                self.corrupt_journal = True
                self.status, self.reason = "recovery_required", "Invalid AC recovery journal; inspect the AC and recovery data"
                await self.notify(self.reason)
                return
            self.session = dict(saved)
            for key in ("target", "started", "command_at", "deadline"):
                self.session[key] = float(saved[key])
            self.session.update(phase="stopping", outcome="interrupted", reason="Session interrupted by restart or reload",
                                stop_attempts=0, stop_sent_at=None, command_at=min(float(saved["command_at"]), self.now()))
            self.status, self.reason = "stopping", self.session["reason"]
            await self.save_recovery()
        # Every restart remains Observe, including after successful restoration.

    async def write(self, service, data):
        async with asyncio.timeout(10):
            await self.hass.services.async_call("climate", service, data, blocking=True)

    async def finish(self, outcome, reason, *, latch=False):
        if self.session:
            self.last_energy_kwh = self.session.get("energy_kwh") if self.session.get("metered") else None
        self.session = None
        self.stopped_at = self.now()
        self.blocked_until = self.now() + self.settings.ac_settle_minutes * 60
        self.latched = self.latched or latch
        self.status, self.reason = outcome, reason
        if not await self.save_recovery():
            self.status = "recovery_required"
            self.reason = reason + "; recovery journal could not be cleared, new sessions blocked"

    async def async_stop(self, reason="AC assistance cancelled"):
        if not self.session:
            return
        if self.session["phase"] not in ("stopping", "recovery_required"):
            self.session.update(phase="stopping", outcome="stopped", reason=reason, stop_attempts=0, stop_sent_at=None)
            await self.save_recovery()
        await self.restore(self.now())

    async def restore(self, now):
        session = self.session
        self.status, self.reason = session["phase"], session["reason"]
        state = self.state(session["entity"])
        if state and state.state == "off":
            if session.get("acknowledged") or now >= session["command_at"] + ACK_SECONDS:
                await self.finish(session.get("outcome", "stopped"), session["reason"] + "; Off confirmed")
            return
        if state and state.state not in ("unknown", "unavailable", "") and not self.matches(state):
            if not session.get("acknowledged") and now < session["command_at"] + ACK_SECONDS:
                # Mode and target may report separately. A pending command must
                # not lose its journal while it can still change the device.
                return
            await self.finish("manual_override", "AC mode or target changed externally; user's settings left untouched", latch=True)
            return
        if session["phase"] == "recovery_required":
            return
        sent = session.get("stop_sent_at")
        if sent is not None and now - sent < ACK_SECONDS:
            return
        if session.get("stop_attempts", 0) >= RESTORE_ATTEMPTS:
            session["phase"] = self.status = "recovery_required"
            session["reason"] = self.reason = "AC Off could not be confirmed; inspect the unit and retry with AC mode Off"
            self.latched = True
            await self.save_recovery()
            await self.notify(self.reason)
            return
        session["stop_attempts"] = session.get("stop_attempts", 0) + 1
        session["stop_sent_at"] = now
        await self.save_recovery()
        # Never send Off without observed ownership, including after an await.
        if not self.matches(self.state(session["entity"])):
            return
        session["acknowledged"] = True
        try:
            await self.write("set_hvac_mode", {"entity_id": session["entity"], "hvac_mode": "off"})
        except (HomeAssistantError, TimeoutError, ValueError):
            pass

    async def start(self, target, reason):
        now = self.now()
        state = self.state()
        native, rounded = target_for_device(self.hass, self.owner.config["ac_entity"], state, target)
        self.session = {"entity": self.owner.config["ac_entity"], "original": "off", "phase": "starting",
                        "original_target": self.current_target(state),
                        "target": rounded, "started": now, "command_at": now, "acknowledged": False,
                        "deadline": now + self.settings.ac_max_session_minutes * 60,
                        "metered": bool(self.owner.config.get("ac_power_entity")), "energy_kwh": 0.0,
                        "power_at": None, "power_w": None, "reason": reason}
        self.blocks_learning(now)
        self.status, self.reason = "starting", reason
        try:
            await self.save()  # Ownership MUST survive before submitting a command.
        except (OSError, HomeAssistantError):
            self.session = None
            self.storage_fault = self.latched = True
            self.status, self.reason = "attention_required", "AC recovery journal could not be saved; no start command sent"
            await self.notify(self.reason)
            return
        error = self.guard(self.now(), rounded, starting=True)
        state = self.state()
        if (self.mode != "automatic" or self.owner.mode != "automatic" or error or state is None or state.state != "off"
                or self.current_target(state) != self.session["original_target"]):
            await self.finish("cancelled", error or "Mode or AC changed before command submission")
            return
        # Record the baseline meter sample; old samples never contribute runtime.
        watts, stamp = self.sample("ac_power_entity", now, "power")
        if watts is not None:
            self.session.update(power_at=now, power_w=watts)
        try:
            await self.write("set_temperature", {"entity_id": self.session["entity"], "temperature": native, "hvac_mode": "heat"})
        except (HomeAssistantError, TimeoutError, ValueError):
            self.latched = True
            await self.async_stop("AC start failed or timed out; verifying Off")

    def measure(self, now):
        session = self.session
        if not session.get("metered"):
            return ""
        watts, stamp = self.sample("ac_power_entity", now, "power")
        if watts is None:
            return "AC power telemetry lost; measured session budget cannot be verified"
        prior = finite(session.get("power_at"))
        if prior is not None:
            if now < prior or now - prior > self.settings.ac_sample_seconds:
                return "AC power sampling gap; measured session budget cannot be verified"
            # Repeated polling does not extrapolate stale power reports.
            if stamp <= prior:
                if now - prior >= self.settings.ac_sample_seconds:
                    return "AC power meter stopped reporting; measured budget cannot be verified"
                return ""
            elapsed = stamp - prior
            if elapsed > self.settings.ac_sample_seconds:
                return "AC power sampling gap; measured session budget cannot be verified"
            session["energy_kwh"] += (session["power_w"] + watts) * 0.5 * elapsed / 3600000
        session.update(power_at=stamp, power_w=watts)
        if session["energy_kwh"] >= self.settings.ac_max_session_kwh:
            return "Measured AC session energy budget reached"
        return ""

    async def async_tick(self, requested=False, target=None, reason=""):
        now = self.now()
        self.requested, self.requested_target = bool(requested), target
        self.blocks_learning(now)
        if self.corrupt_journal:
            return
        if self.storage_fault and self.session is None:
            await self.save_recovery()
            if self.storage_fault:
                self.status, self.reason = "recovery_required", "AC recovery journal could not be cleared; new sessions blocked"
                return
        if self.session:
            session = self.session
            if session["phase"] in ("stopping", "recovery_required"):
                await self.restore(now)
                return
            state = self.state(session["entity"])
            if self.mode != "automatic" or self.owner.mode != "automatic":
                await self.async_stop("AC or main control left Automatic")
                return
            if now < session["started"] or now >= session["deadline"]:
                self.latched = True
                await self.async_stop("AC maximum session duration reached or clock moved backwards")
                return
            error = self.guard(now, session["target"])
            if error:
                await self.async_stop(error)
                return
            if not self.matches(state):
                if not session.get("acknowledged") and now < session["command_at"] + ACK_SECONDS:
                    self.reason = "Waiting for the AC to confirm both Heat and the requested target"
                elif state.state != "off" or session.get("acknowledged"):
                    await self.finish("manual_override", "AC changed externally; automatic commands suspended", latch=True)
                elif now >= session["command_at"] + ACK_SECONDS:
                    self.latched = True
                    await self.async_stop("AC did not acknowledge Heat and target within two minutes")
                return
            session["acknowledged"] = True
            error = self.measure(now)
            if error:
                self.latched = True
                await self.async_stop(error)
                return
            room = self.sample("ac_room_entity", now)[0]
            if room >= session["target"]:
                await self.async_stop("AC room reached the preparation target")
                return
            if (not requested or target is None or target < session["target"] - 0.05) and now - session["started"] >= self.settings.ac_min_on_minutes * 60:
                await self.async_stop(reason or "Forecast preparation no longer needs AC assistance")
                return
            session["phase"] = self.status = "running"
            self.reason = reason or "Bounded preparation session running"
            await self.save()
            return
        if not self.configured:
            self.status, self.reason = "not_configured", "Select an AC and external room thermometer in Configure"
            return
        error = self.guard(now, target, starting=True) if requested else ""
        state = self.state()
        if self.latched:
            self.status, self.reason = "attention_required", "Previous AC session needs review; select Observe then Automatic to resume"
        elif self.mode == "off":
            self.status, self.reason = "off", "AC assistance disabled"
        elif error:
            self.status, self.reason = "blocked", error
        elif state is None or state.state != "off":
            self.status, self.reason = "manual", "AC is not Off; existing user operation left untouched"
        elif self.mode == "observe" or self.owner.mode != "automatic":
            self.status, self.reason = "observe", ("Would assist: " if requested else "") + reason
        elif requested and now - self.stopped_at < self.settings.ac_min_off_minutes * 60:
            self.status, self.reason = "resting", "Minimum AC rest period has not elapsed"
        elif requested:
            await self.start(target, reason)
        else:
            self.status, self.reason = "waiting", reason or "Forecast preparation does not request AC assistance"

    async def async_mode(self, mode):
        if mode not in MODES:
            raise HomeAssistantError("Invalid AC mode")
        if mode == "automatic" and (self.corrupt_journal or self.recovery_pending):
            self.mode = "observe"
            raise HomeAssistantError("Resolve AC recovery before enabling Automatic")
        if mode == "automatic" and (self.owner.shutting_down or self.owner.releases.restart_pending):
            self.mode = "observe"
            raise HomeAssistantError("Restart or reload must finish before enabling AC Automatic")
        self.mode = mode
        if mode != "automatic":
            if self.session and self.session["phase"] == "recovery_required":
                self.session.update(phase="stopping", stop_attempts=0, stop_sent_at=None)
            await self.async_stop("AC control left Automatic")
        else:
            self.latched = False
            await self.save()

    async def notify(self, message):
        try:
            async with asyncio.timeout(10):
                await self.hass.services.async_call("persistent_notification", "create",
                    {"title": "Adaptive Heating: AC needs attention", "message": message,
                     "notification_id": f"{DOMAIN}_{self.owner.entry.entry_id}_ac"}, blocking=True)
        except (HomeAssistantError, TimeoutError):
            pass

    async def async_prepare_unload(self):
        await self.async_stop("Controller unloading; restoring AC Off")
        if self.session:
            await self.restore(self.now())
        elif self.storage_fault:
            await self.save_recovery()
        return self.session is None and not self.corrupt_journal and not self.storage_fault

    def attributes(self):
        session = self.session or {}
        state = self.state(session.get("entity"))
        return {"mode": self.mode, "reason": self.reason, "requested": self.requested,
                "requested_target": self.requested_target, "commanded_target": session.get("target"),
                "actual_mode": state.state if state else None, "actual_target": self.current_target(state),
                "external_room_temperature": self.sample("ac_room_entity", self.now())[0],
                "minimum_outdoor_temperature": self.settings.ac_min_outdoor,
                "started_at": session.get("started"), "deadline": session.get("deadline"),
                "power_w": self.sample("ac_power_entity", self.now(), "power")[0],
                "session_energy_kwh": session.get("energy_kwh") if session.get("metered") else None,
                "energy_measurement": "Trapezoidal integration of fresh AC power samples; no COP or savings estimate",
                "last_session_energy_kwh": self.last_energy_kwh,
                "energy_budget_enforced": bool(self.owner.config.get("ac_power_entity")),
                "energy_budget_note": "Measured session budget" if self.owner.config.get("ac_power_entity") else "No AC meter configured; runtime cap only, no energy or savings estimate",
                "learning_blocked_until": self.blocked_until if self.owner.config.get("ac_entity") else None,
                "recovery_storage_failed": self.storage_fault,
                "requires_attention": self.latched or self.corrupt_journal or self.recovery_pending}
