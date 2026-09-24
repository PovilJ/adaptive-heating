"""HA state adapter and single serialized path for actuator writes."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import timedelta
import hashlib
import json
import logging

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DEFAULTS, DOMAIN, MODES
from .engine import Energy, Model, Settings, decide, finite, limited_output, power_watts, surplus_available, temperature

_LOGGER = logging.getLogger(__name__)


class HeatingCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, releases):
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry, update_interval=timedelta(minutes=5))
        self.entry = entry
        self.releases = releases
        self.config = DEFAULTS | dict(entry.data) | dict(entry.options)
        self.settings = Settings(**{k: self.config[k] for k in Settings.__dataclass_fields__ if k in self.config})
        self.store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self.model = Model()
        self.mode = "observe"
        self.lock = asyncio.Lock()
        self.previous = None
        self.last_commanded = None
        self.last_command_time = None
        self.last_seen_output = None
        self.pending_deadline = None
        self.manual_hold = False
        self.surplus_since = None
        self.last_energy_sample = None
        self.last_cycle = None
        self.forecast_checked = None
        self.forecast_cache = []
        self.events = []
        self.started = dt_util.utcnow()

    def identity(self):
        keys = ("indoor_entity", "outdoor_entity", "weather_entity", "output_entity", "inlet_entity", "outlet_entity", "operating_entity", "heating_state")
        raw = json.dumps({k: self.config.get(k) for k in keys}, sort_keys=True).encode()
        return hashlib.sha256(raw).hexdigest()

    async def async_load(self):
        data = await self.store.async_load() or {}
        if data.get("identity") == self.identity():
            self.model = Model.restore(data.get("model"))
            target = finite(data.get("target"))
            if target is not None and 10 <= target <= 30 and data.get("configured_target") == self.config["target"]:
                self.settings.target = target
        # Observe on every restart/reconfiguration, regardless of stored mode.

    async def async_save(self):
        await self.store.async_save({"identity": self.identity(), "model": asdict(self.model), "target": self.settings.target,
                                    "configured_target": self.config["target"]})

    def fresh_state(self, key, now):
        entity_id = self.config.get(key)
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", ""):
            return None
        # Helpers and actuator/status entities can correctly remain unchanged for
        # months. Their integration's availability governs them, not value age.
        if key in ("output_entity", "operating_entity", "defrost_entity", "inhibit_entity"):
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
        return temperature(state.state, unit)

    def snapshot(self, now):
        indoor = self.reading("indoor_entity", now)
        weather = self.fresh_state("weather_entity", now)
        outdoor = self.reading("outdoor_entity", now) if self.config.get("outdoor_entity") else None
        if outdoor is None and not self.config.get("outdoor_entity") and weather:
            outdoor = temperature(weather.attributes.get("temperature"), weather.attributes.get("temperature_unit"))
        inlet = self.reading("inlet_entity", now)
        outlet = self.reading("outlet_entity", now)
        water = (inlet + outlet) / 2 if inlet is not None and outlet is not None else None
        output = self.reading("output_entity", now)
        operating = self.fresh_state("operating_entity", now)
        reason = ""
        if indoor is None or not 0 <= indoor <= 45:
            reason = "Indoor temperature unavailable, stale, or invalid"
        elif outdoor is None or not -70 <= outdoor <= 60:
            reason = "Outdoor temperature unavailable, stale, or invalid"
        elif output is None:
            reason = "Water setpoint unavailable, stale, or invalid"
        elif operating is None or operating.state.casefold() != self.config["heating_state"].strip().casefold():
            reason = "Space-heating state not confirmed (including hot water, off, or unknown)"
        for key, label in (("defrost_entity", "Defrost"), ("inhibit_entity", "Another controller or inhibit")):
            if self.config.get(key):
                flag = self.fresh_state(key, now)
                if flag is None or flag.state != "off":
                    reason = f"{label} active or unavailable"
        if inlet is not None and not 0 <= inlet <= 85:
            water = None
        if outlet is not None and not 0 <= outlet <= 85:
            water = None
        sunny = bool(weather and weather.state in ("sunny", "partlycloudy"))
        return {"time": now.timestamp(), "indoor": indoor, "outdoor": outdoor, "water": water,
                "output": output, "blocked": reason, "eligible": not reason and not sunny and water is not None}

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

    async def forecasts(self, now):
        if self.forecast_checked is None or (now - self.forecast_checked).total_seconds() >= 1800:
            self.forecast_checked = now
            self.forecast_cache = []
            try:
                async with asyncio.timeout(10):
                    result = await self.hass.services.async_call("weather", "get_forecasts",
                        {"entity_id": self.config["weather_entity"], "type": "hourly"},
                        blocking=True, return_response=True)
                state = self.fresh_state("weather_entity", now)
                unit = state.attributes.get("temperature_unit") if state else None
                for row in (result or {}).get(self.config["weather_entity"], {}).get("forecast", []):
                    when = dt_util.parse_datetime(row.get("datetime", ""))
                    value = temperature(row.get("temperature"), unit)
                    if when is not None and when.tzinfo is not None and value is not None and -70 <= value <= 60:
                        self.forecast_cache.append((when, value))
            except (HomeAssistantError, TimeoutError, ValueError, TypeError, AttributeError):
                _LOGGER.debug("Hourly weather forecast unavailable; using heating curve")
        future = sorted((t, v) for t, v in self.forecast_cache if now - timedelta(minutes=30) <= t <= now + timedelta(hours=12))
        # Reject daily, duplicated, or gapped data advertised as hourly.
        if len(future) < 2 or (future[0][0] - now).total_seconds() > 5400:
            return []
        if any(not 1800 <= (b[0] - a[0]).total_seconds() <= 5400 for a, b in zip(future, future[1:])):
            return []
        return [v for _, v in future[:12]]

    async def _async_update_data(self):
        async with self.lock:
            now = dt_util.utcnow()
            snapshot = self.snapshot(now)
            energy = self.energy(now)
            valid_surplus = surplus_available(energy, self.settings)
            if self.last_energy_sample is not None and (now - self.last_energy_sample).total_seconds() > 600:
                self.surplus_since = None
            self.last_energy_sample = now
            if valid_surplus:
                self.surplus_since = self.surplus_since or now
            else:
                self.surplus_since = None
            sustained = self.surplus_since is not None and (now - self.surplus_since).total_seconds() >= 900
            if snapshot["output"] is not None:
                output = snapshot["output"]
                if self.last_seen_output is not None and abs(output - self.last_seen_output) > 0.05:
                    if self.last_commanded is None or abs(output - self.last_commanded) > 0.05:
                        if self.mode == "automatic":
                            self.manual_hold = True
                if self.pending_deadline:
                    if abs(output - self.last_commanded) <= 0.05:
                        self.pending_deadline = None
                    elif now >= self.pending_deadline:
                        self.manual_hold = True
                        self.pending_deadline = None
                self.last_seen_output = output
            if snapshot["indoor"] is not None:
                self.model.observe(self.previous, snapshot, eligible=snapshot["eligible"] and self.mode != "off")
                self.previous = snapshot
            else:
                self.previous = None
            result = {"status": "observing", "reason": "Collecting measurements", "proposed": None,
                      "limited": None, "commanded": self.last_commanded, "actual": snapshot["output"],
                      "prediction": None, "indoor": snapshot["indoor"], "outdoor": snapshot["outdoor"],
                      "model_samples": self.model.samples, "model_error": self.model.error,
                      "surplus": sustained, "electric_power": self.reading("electric_power_entity", now, "power"),
                      "electric_energy": self.reading("electric_energy_entity", now, "energy"),
                      "checked_at": now.isoformat()}
            forecasts = await self.forecasts(now) if self.mode != "off" else []
            blocked = snapshot["blocked"]
            if self.releases.restart_pending:
                blocked = "Update installed; restart Home Assistant to activate it"
            elif self.manual_hold:
                blocked = "Manual change or unconfirmed command; select Observe then Automatic to resume"
            if self.mode == "off":
                result.update(status="off", reason="Automatic control and learning disabled")
            elif blocked:
                result.update(status="paused", reason=blocked)
            else:
                decision = decide(self.settings, self.model, snapshot["indoor"], snapshot["outdoor"], forecasts, sustained)
                result.update(proposed=decision.proposed, prediction=decision.predicted_minimum, reason=decision.reason)
                limited = self.output_limit(decision.proposed, snapshot["output"], now)
                result["limited"] = limited
                if limited is None:
                    result.update(status="paused", reason="Setpoint or device limits invalid; check output entity and water limits")
                elif self.mode == "automatic":
                    # Evaluation buttons cannot bypass the time-based command limits.
                    due = self.last_cycle is None or (now - self.last_cycle).total_seconds() >= self.settings.control_minutes * 60
                    if due:
                        self.last_cycle = now
                        await self.apply(limited, snapshot["output"], result)
                    else:
                        result["status"] = "waiting"
            result["commanded"] = self.last_commanded
            self.events = ([{k: result[k] for k in ("checked_at", "status", "reason", "proposed", "limited", "commanded", "actual")}] + self.events)[:20]
            await self.async_save()
            return result

    def output_limit(self, proposed, current, now):
        state = self.hass.states.get(self.config["output_entity"])
        if state is None:
            return None
        unit = state.attributes.get("unit_of_measurement")
        lo = temperature(state.attributes.get("min"), unit)
        hi = temperature(state.attributes.get("max"), unit)
        step = finite(state.attributes.get("step"))
        if lo is None or hi is None or step is None:
            return None
        if unit == "°F":
            step /= 1.8
        elapsed = (now - (self.last_command_time or self.started)).total_seconds() / 3600
        elapsed = min(elapsed, self.settings.control_minutes / 60)
        return limited_output(proposed, current, max(lo, self.settings.minimum_water),
                              min(hi, self.settings.maximum_water), step, lo, elapsed,
                              self.settings.rise_per_hour, self.settings.fall_per_hour)

    async def apply(self, value, observed, result):
        # All external awaits happen before a fresh final gate. Mode changes can
        # stop writes even if an earlier forecast request was still in flight.
        fresh = self.snapshot(dt_util.utcnow())
        if self.mode != "automatic" or self.releases.restart_pending or fresh["blocked"]:
            result.update(status="paused", reason=fresh["blocked"] or "Automatic control disabled")
            return
        if fresh["output"] is None or abs(fresh["output"] - observed) > 0.05:
            self.manual_hold = True
            result.update(status="paused", reason="Setpoint changed during calculation")
            return
        if abs(value - observed) < 0.05:
            result["status"] = "maintaining"
            return
        state = self.hass.states.get(self.config["output_entity"])
        native_value = value * 1.8 + 32 if state.attributes.get("unit_of_measurement") == "°F" else value
        try:
            async with asyncio.timeout(10):
                await self.hass.services.async_call("number", "set_value",
                    {"entity_id": self.config["output_entity"], "value": round(native_value, 6)}, blocking=True)
            self.last_commanded = value
            self.last_command_time = dt_util.utcnow()
            self.pending_deadline = self.last_command_time + timedelta(minutes=2)
            result["status"] = "command_sent"
        except (HomeAssistantError, TimeoutError):
            self.manual_hold = True
            result.update(status="paused", reason="Setpoint command failed; manual review required")

    async def async_mode(self, mode):
        if mode not in MODES:
            raise HomeAssistantError("Invalid controller mode")
        if mode == "automatic" and self.releases.restart_pending:
            raise HomeAssistantError("Restart Home Assistant after installing the update")
        if mode != "automatic":
            # Disable immediately; do not wait behind a network operation.
            self.mode = mode
        async with self.lock:
            self.mode = mode
            self.manual_hold = False
            self.pending_deadline = None
        await self.async_request_refresh()

    async def async_target(self, target):
        if finite(target) is None or not 10 <= target <= 30:
            raise HomeAssistantError("Target must be 10–30 Celsius")
        async with self.lock:
            self.settings.target = round(target, 1)
            await self.async_save()
        await self.async_request_refresh()
