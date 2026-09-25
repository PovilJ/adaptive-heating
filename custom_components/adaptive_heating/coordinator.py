"""HA state adapter and single serialized path for actuator writes."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, replace
from datetime import timedelta
import hashlib
import json
import logging
import math

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DEFAULTS, DOMAIN, MODES
from .disinfection import DEFAULTS as DHW_DEFAULTS
from .disinfection_controller import DisinfectionController
from .ac_controller import ACController, DEFAULTS as AC_DEFAULTS
from .engine import Energy, Model, Settings, decide, finite, limited_output, power_watts, surplus_available, temperature
from .planner import DEFAULTS as PLAN_DEFAULTS, CooldownModel, ForecastPoint, PlannerSettings, decide_plan

_LOGGER = logging.getLogger(__name__)


class HeatingCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, releases):
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry, update_interval=timedelta(minutes=5))
        self.entry = entry
        self.releases = releases
        self.config = DEFAULTS | DHW_DEFAULTS | PLAN_DEFAULTS | AC_DEFAULTS | dict(entry.data) | dict(entry.options)
        self.settings = Settings(**{k: self.config[k] for k in Settings.__dataclass_fields__ if k in self.config})
        self.planner_settings = PlannerSettings(**{k: self.config[k] for k in PlannerSettings.__dataclass_fields__})
        self.cooldown = CooldownModel()
        self.plan = None
        self.planner_data = {}
        self.forecast_details = []
        self.room_history = []
        self.coast_water_history = []
        self.coast_since = None
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
        self.disinfection = DisinfectionController(self)
        self.shutting_down = False
        self.ac = ACController(self)

    def identity(self):
        keys = ("indoor_entity", "outdoor_entity", "weather_entity", "output_entity", "inlet_entity", "outlet_entity", "operating_entity", "heating_state")
        # Preserve the old fingerprint for entries without additional mappings.
        keys += tuple(k for k in ("ac_entity", "ac_room_entity", "protection_entity") if self.config.get(k))
        raw = json.dumps({k: self.config.get(k) for k in keys}, sort_keys=True).encode()
        return hashlib.sha256(raw).hexdigest()

    async def async_load(self):
        data = await self.store.async_load() or {}
        if data.get("identity") == self.identity():
            self.model = Model.restore(data.get("model"))
            if data.get("cooldown_regime") == self.cooldown_regime():
                self.cooldown = CooldownModel.restore(data.get("cooldown"))
            target = finite(data.get("target"))
            compatible = (not self.planner_settings.cold_night_enabled or target is not None
                          and self.planner_settings.night_minimum <= target <= self.planner_settings.preheat_ceiling)
            if compatible and target is not None and 10 <= target <= 30 and data.get("configured_target") == self.config["target"]:
                self.settings.target = target
        # Observe on every restart/reconfiguration, regardless of stored mode.
        await self.disinfection.async_load()
        await self.ac.async_load()

    async def async_save(self):
        await self.store.async_save({"identity": self.identity(), "model": asdict(self.model), "target": self.settings.target,
                                    "configured_target": self.config["target"], "cooldown": self.cooldown.to_dict(),
                                    "cooldown_regime": self.cooldown_regime()})

    def cooldown_regime(self):
        return {"minimum_water": self.settings.minimum_water, "sun_entity": self.config.get("sun_entity")}

    def fresh_state(self, key, now):
        entity_id = self.config.get(key)
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", ""):
            return None
        # Helpers and actuator/status entities can correctly remain unchanged for
        # months. Their integration's availability governs them, not value age.
        if key in ("output_entity", "operating_entity", "defrost_entity", "inhibit_entity", "sun_entity", "ac_entity"):
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
        if self.disinfection.blocks_heating:
            reason = "Tank disinfection or target restoration in progress; space heating and learning paused"
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
            self.forecast_details = []
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
                        self.forecast_details.append(ForecastPoint(when, value, row.get("condition")))
            except (HomeAssistantError, TimeoutError, ValueError, TypeError, AttributeError):
                _LOGGER.debug("Hourly weather forecast unavailable; using heating curve")
        future = sorted((t, v) for t, v in self.forecast_cache if now - timedelta(minutes=30) <= t <= now + timedelta(hours=24))
        # Reject daily, duplicated, or gapped data advertised as hourly.
        future = future[:12]
        if len(future) < 2 or (future[0][0] - now).total_seconds() > 5400:
            return []
        if any(not 1800 <= (b[0] - a[0]).total_seconds() <= 5400 for a, b in zip(future, future[1:])):
            return []
        return [v for _, v in future[:12]]

    def recovery_ramp_hours(self, snapshot):
        """Reserve enough time to leave the *planned* minimum-water level.

        Quantized per-cycle commands can be slower than a nominal degrees/hour
        rate. Include a full command opportunity; never relax actuator limits.
        Budgeting from the lower of actual/planned water avoids entering a coast
        that would become impossible to recover from after later reductions.
        """
        if snapshot["indoor"] is None or snapshot["outdoor"] is None or snapshot["output"] is None:
            return 0.0
        recovery_settings = replace(self.settings, solar_preheat=False)
        future_cold = [p.temperature for p in self.forecast_details
                       if 0 <= p.at.timestamp() - snapshot["time"] <= 24 * 3600]
        outdoor = min([snapshot["outdoor"]] + future_cold)
        needed = decide(recovery_settings, Model(), self.planner_settings.night_minimum,
                        outdoor, []).proposed
        current = min(snapshot["output"], self.settings.minimum_water)
        if needed <= current:
            return 0.0
        state = self.hass.states.get(self.config["output_entity"])
        step = finite(state.attributes.get("step")) if state else None
        if step is None or step <= 0:
            return 25.0  # Planner rejects an unachievable recovery horizon.
        if state.attributes.get("unit_of_measurement") == "°F":
            step /= 1.8
        interval = self.settings.control_minutes / 60
        increment = math.floor((self.settings.rise_per_hour * interval + 1e-8) / step) * step
        if increment <= 0:
            return 25.0
        return math.ceil((needed - current) / increment) * interval + interval

    def planning_inputs(self, now, snapshot, *, observe=True):
        """Keep passive solar, observed cooldown, and electrical surplus distinct."""
        indoor = snapshot["indoor"]
        protection = self.reading("protection_entity", now) if self.config.get("protection_entity") else None
        sun = self.fresh_state("sun_entity", now)
        sunset = None
        if sun:
            try:
                sunset = dt_util.parse_datetime(sun.attributes.get("next_setting", ""))
            except (ValueError, TypeError):
                pass
        local_now = dt_util.as_local(now)
        dark = sun.state == "below_horizon" if sun else local_now.hour >= self.planner_settings.quiet_start_hour or local_now.hour < self.planner_settings.morning_hour
        ac_active = self.ac.blocks_learning(now)
        if indoor is not None and not snapshot["blocked"] and not ac_active:
            self.room_history = [(t, v) for t, v in self.room_history if 0 <= (now - t).total_seconds() <= 3600]
            if self.room_history and (now - self.room_history[-1][0]).total_seconds() > 600:
                self.room_history = []
            if not self.room_history or (now - self.room_history[-1][0]).total_seconds() >= 240:
                self.room_history.append((now, indoor))
        else:
            self.room_history = []
        rate = None
        if len(self.room_history) > 1:
            age = (now - self.room_history[0][0]).total_seconds() / 3600
            if age >= 0.25:
                rate = (self.room_history[0][1] - indoor) / age
        # An observed rate is an empirical result of *low-water operation*, not
        # an assertion that the heat pump or the house was unheated.
        low_water = (snapshot["output"] is not None and snapshot["output"] <= self.settings.minimum_water + 0.1
                     and snapshot["water"] is not None and snapshot["water"] <= self.settings.minimum_water + 2)
        if low_water and not snapshot["blocked"] and not ac_active and dark and not self.manual_hold:
            self.coast_since = self.coast_since or now
            self.coast_water_history = [(t, v) for t, v in self.coast_water_history
                                        if 0 <= (now - t).total_seconds() <= 3600]
            if self.coast_water_history and (now - self.coast_water_history[-1][0]).total_seconds() > 600:
                self.coast_water_history = []
                self.coast_since = now
            if not self.coast_water_history or (now - self.coast_water_history[-1][0]).total_seconds() >= 240:
                self.coast_water_history.append((now, snapshot["water"]))
        else:
            self.coast_since = None
            self.coast_water_history = []
        # Require an hour of settled measured water, not merely a low requested
        # target. Samples describe that operating regime, including residual
        # floor warmth; they do not measure unheated building heat loss.
        values = [v for _, v in self.coast_water_history]
        stable_water = (len(values) >= 7 and (now - self.coast_water_history[0][0]).total_seconds() >= 3300
                        and max(values) - min(values) <= 1 and abs(values[-1] - values[0]) <= 0.5)
        eligible = (self.mode != "off" and self.coast_since is not None
                    and (now - self.coast_since).total_seconds() >= 3600 and stable_water)
        if observe:
            self.cooldown.observe(now, indoor, snapshot["outdoor"], eligible=eligible)
        self.plan = decide_plan(self.planner_settings, self.cooldown, now=local_now,
            indoor=indoor, outdoor=snapshot["outdoor"], room_target=self.settings.target,
            forecasts=self.forecast_details, next_sunset=sunset,
            measured_cooling_rate=rate, coast_water_target=self.settings.minimum_water,
            recovery_ramp_hours=self.recovery_ramp_hours(snapshot))
        self.planner_data = dict(self.plan.diagnostics) | {
            "phase": self.plan.phase, "reason": self.plan.reason, "effective_target": self.plan.effective_target,
            "floor_water_target": self.plan.floor_water_target, "ac_requested": self.plan.ac_requested,
            "protection_temperature": protection, "observed_cooling_rate": rate,
            "cooldown_learning_eligible": eligible,
        }
        if ac_active and self.plan.phase in ("coast", "solar_wait"):
            self.planner_data.update(phase="baseline", ac_requested=False, effective_target=self.settings.target,
                reason="AC operation or settling makes the room reserve uncertain; maintaining the normal water curve")
        # A separate room can veto coasting. Missing configured protection data
        # cannot silently authorize a reduced whole-house target.
        if self.planner_settings.cold_night_enabled and self.config.get("protection_entity"):
            if protection is None or protection < self.planner_settings.night_minimum + 0.3:
                self.planner_data.update(phase="recovery", reason="Another room is near its minimum or its sensor is unavailable",
                                         ac_requested=False, effective_target=self.settings.target)
        return self.plan

    def track_output(self, snapshot, now):
        output = snapshot["output"]
        if output is None:
            return
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
            await self.disinfection.async_tick()
            snapshot = self.snapshot(dt_util.utcnow())
            self.track_output(snapshot, now)
            result = {"status": "observing", "reason": "Collecting measurements", "proposed": None,
                      "limited": None, "commanded": self.last_commanded, "actual": snapshot["output"],
                      "prediction": None, "indoor": snapshot["indoor"], "outdoor": snapshot["outdoor"],
                      "model_samples": self.model.samples, "model_error": self.model.error,
                      "surplus": sustained, "electric_power": self.reading("electric_power_entity", now, "power"),
                      "electric_energy": self.reading("electric_energy_entity", now, "energy"),
                      "checked_at": now.isoformat()}
            forecasts = await self.forecasts(now) if self.mode != "off" else []
            # Forecast requests can await external I/O: all planning and writes
            # use a new observation after that await.
            now = dt_util.utcnow()
            snapshot = self.snapshot(now)
            self.track_output(snapshot, now)
            if self.mode == "off":
                self.plan = None
                self.planner_data = {"phase": "off", "reason": "Control mode is Off", "ac_requested": False}
                self.room_history = []
                self.coast_water_history = []
                self.coast_since = None
                self.cooldown.observe(now, None, None, eligible=False)
            else:
                self.planning_inputs(now, snapshot)
            blocked = snapshot["blocked"]
            if self.releases.restart_pending:
                blocked = "Update installed; restart Home Assistant to activate it"
            elif self.manual_hold:
                blocked = "Manual change or unconfirmed command; select Observe then Automatic to resume"
            ac_requested = bool(not blocked and self.mode != "off" and self.planner_data.get("ac_requested"))
            await self.ac.async_tick(ac_requested,
                min(self.planner_settings.preheat_ceiling, self.planner_data.get("effective_target") or self.settings.target),
                self.planner_data.get("reason", ""))
            # AC ownership journaling and services can await I/O as well. A
            # manual edit, inhibit or comfort ceiling reached meanwhile must
            # affect this same water decision, not the next five-minute poll.
            now = dt_util.utcnow()
            fresh = self.snapshot(now)
            self.track_output(fresh, now)
            ac_active = self.ac.blocks_learning(now)
            changed = any(fresh[key] != snapshot[key] for key in ("indoor", "outdoor", "output", "water", "blocked"))
            if self.mode != "off" and (changed or ac_active):
                self.planning_inputs(now, fresh, observe=False)
            snapshot = fresh
            blocked = snapshot["blocked"]
            if self.releases.restart_pending:
                blocked = "Update installed; restart Home Assistant to activate it"
            elif self.manual_hold:
                blocked = "Manual change or unconfirmed command; select Observe then Automatic to resume"
            snapshot["eligible"] = snapshot["eligible"] and not ac_active and self.mode != "off" and not blocked
            if snapshot["indoor"] is not None and not snapshot["blocked"]:
                self.model.observe(self.previous, snapshot, eligible=snapshot["eligible"])
                self.previous = snapshot
            else:
                self.previous = None
                self.model.emitter = None
            result.update(indoor=snapshot["indoor"], outdoor=snapshot["outdoor"], actual=snapshot["output"],
                model_samples=self.model.samples, model_error=self.model.error,
                planner_status=self.planner_data.get("phase"), planner_target=self.planner_data.get("effective_target"))
            if self.mode == "off":
                result.update(status="off", reason="Automatic control and learning disabled")
            elif blocked:
                result.update(status="paused", reason=blocked)
            else:
                phase = self.planner_data.get("phase")
                planned = self.plan is not None and phase in ("prepare", "coast", "recovery", "ceiling_hold", "solar_wait")
                effective_settings = replace(self.settings,
                    target=self.plan.effective_target if planned and phase != "recovery" else self.settings.target,
                    solar_preheat=False if planned else self.settings.solar_preheat)
                # AC heat must neither train the water model nor immediately
                # make room feedback cut the slow heating beneath it.
                shield_ac = (ac_active and self.planner_settings.cold_night_enabled
                             and snapshot["indoor"] < self.planner_settings.preheat_ceiling)
                indoor = min(snapshot["indoor"], effective_settings.target) if shield_ac else snapshot["indoor"]
                decision = decide(effective_settings, Model() if ac_active else self.model,
                    indoor, snapshot["outdoor"], forecasts, sustained)
                if planned:
                    proposed = decision.proposed
                    if phase != "recovery":
                        proposed = (self.plan.floor_water_target if self.plan.floor_water_target is not None
                                    else proposed + self.plan.floor_water_delta)
                    decision = replace(decision,
                        proposed=max(self.settings.minimum_water, min(self.settings.maximum_water, proposed)),
                        predicted_minimum=None, reason=self.planner_data["reason"])
                # Actual room overheating overrides every phase, including a
                # missing forecast or recovery. AC attribution must never hide
                # the comfort ceiling; water slew limits still apply below.
                if self.planner_settings.cold_night_enabled and snapshot["indoor"] >= self.planner_settings.preheat_ceiling:
                    decision = replace(decision, proposed=self.settings.minimum_water, predicted_minimum=None,
                                       reason="Room reached the preheat ceiling; reducing floor heat within water limits")
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
            self.events = ([{k: result[k] for k in ("checked_at", "status", "reason", "proposed", "limited", "commanded", "actual", "planner_status")}] + self.events)[:20]
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
        if self.shutting_down or self.mode != "automatic" or self.manual_hold or self.releases.restart_pending or fresh["blocked"]:
            reason = "Manual change or unconfirmed command; select Observe then Automatic to resume" if self.manual_hold else "Automatic control disabled"
            result.update(status="paused", reason=fresh["blocked"] or reason)
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
        if self.planner_settings.cold_night_enabled and not self.planner_settings.night_minimum <= target <= self.planner_settings.preheat_ceiling:
            raise HomeAssistantError("Room target must stay between the configured night minimum and preheat ceiling")
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
        """Frequent ownership, temperature and timeout checks between plans."""
        async with self.lock:
            requested = bool(self.planner_data.get("ac_requested") and self.mode == "automatic"
                             and not self.manual_hold and not self.shutting_down)
            await self.ac.async_tick(requested,
                min(self.planner_settings.preheat_ceiling, self.planner_data.get("effective_target") or self.settings.target),
                self.planner_data.get("reason", ""))
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

    async def async_prepare_unload(self):
        self.shutting_down = True
        self.mode = self.disinfection.mode = "off"
        self.ac.mode = "off"
        async with self.lock:
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
