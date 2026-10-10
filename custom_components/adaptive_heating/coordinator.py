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
from .engine import Energy, Model, Recovery, Settings, clamp, cooling_trend, decide, finite, limited_output, power_watts, surplus_available, temperature
from .planner import DEFAULTS as PLAN_DEFAULTS, CooldownModel, ForecastPoint, PlannerSettings, decide_plan
from . import mpc

_LOGGER = logging.getLogger(__name__)
# Revision 3: night-window learning. Older stored counts are not comparable.
MODEL_REVISION = 3
LEGACY_LOSS_GAIN = ("input_number.heating_k_loss", "input_number.heating_k_gain")


def state_matches(state, expected):
    """Match numeric mode registers (4 / 4.0) as well as text states."""
    actual_number, expected_number = finite(state), finite(expected)
    if actual_number is not None and expected_number is not None:
        return actual_number == expected_number
    return str(state).strip().casefold() == str(expected).strip().casefold()


class HeatingCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, releases):
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry, update_interval=timedelta(minutes=5))
        self.entry = entry
        self.releases = releases
        self.config = DEFAULTS | DHW_DEFAULTS | PLAN_DEFAULTS | AC_DEFAULTS | dict(entry.data) | dict(entry.options)
        self.settings = Settings(**{k: self.config[k] for k in Settings.__dataclass_fields__ if k in self.config})
        # Like the PyScript: one evaluation and one command opportunity per control interval.
        self.update_interval = timedelta(minutes=self.settings.control_minutes)
        self.planner_settings = PlannerSettings(**{k: self.config[k] for k in PlannerSettings.__dataclass_fields__})
        self.cooldown = CooldownModel()
        self.dark = False
        self.legacy_seed_pending = False
        self.plan = None
        self.planner_data = {}
        self.forecast_details = []
        self.room_history = []
        self.recovery = Recovery()
        self.coast_water_history = []
        self.coast_since = None
        self.store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self.model = Model(lag_hours=self.settings.thermal_response_hours)
        self.mode = "observe"
        self.lock = asyncio.Lock()
        self.previous = None
        self.operating_events = []
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
        self.forecast_rows = []
        self.house = mpc.House()
        self.estimate = mpc.Estimate()
        self.guard = mpc.Guard()
        self.plan_seed = None
        self.events = []
        self.started = dt_util.utcnow()
        self.disinfection = DisinfectionController(self)
        self.shutting_down = False
        self.ac = ACController(self)

    def identity(self):
        keys = ("indoor_entity", "outdoor_entity", "weather_entity", "output_entity", "inlet_entity", "outlet_entity", "operating_entity", "heating_state")
        # Preserve the old fingerprint for entries without additional mappings.
        keys += tuple(k for k in ("ac_entity", "ac_room_entity", "protection_entity") if self.config.get(k))
        if self.config.get("heating_mode_entity"):
            keys += ("heating_mode_entity", "heating_mode_state", "heating_idle_state")
        if self.settings.thermal_response_hours != DEFAULTS["thermal_response_hours"]:
            keys += ("thermal_response_hours",)
        raw = json.dumps({k: self.config.get(k) for k in keys}, sort_keys=True).encode()
        return hashlib.sha256(raw).hexdigest()

    async def async_load(self):
        data = await self.store.async_load() or {}
        if data.get("identity") == self.identity():
            if data.get("model_revision") == MODEL_REVISION:
                self.model = Model.restore(data.get("model"))
                self.model.lag_hours = self.settings.thermal_response_hours
            if data.get("cooldown_regime") == self.cooldown_regime():
                self.cooldown = CooldownModel.restore(data.get("cooldown"))
            target = finite(data.get("target"))
            compatible = (not self.planner_settings.cold_night_enabled or target is not None
                          and self.planner_settings.night_minimum <= target <= self.planner_settings.preheat_ceiling)
            if compatible and target is not None and 10 <= target <= 30 and data.get("configured_target") == self.config["target"]:
                self.settings.target = target
        # Earlier revisions counted five-minute fits; those counts and errors do
        # not mean the same thing, so start again from the PyScript's values.
        self.legacy_seed_pending = data.get("model_revision") != MODEL_REVISION
        try:
            self.estimate = mpc.Estimate(**data.get("estimate", {}))
        except TypeError:
            self.estimate = mpc.Estimate()
        # Observe on every restart/reconfiguration, regardless of stored mode.
        await self.disinfection.async_load()
        await self.ac.async_load()

    async def async_save(self):
        await self.store.async_save({"identity": self.identity(), "model_revision": MODEL_REVISION,
                                    "model": asdict(self.model), "target": self.settings.target,
                                    "configured_target": self.config["target"], "cooldown": self.cooldown.to_dict(),
                                    "cooldown_regime": self.cooldown_regime(), "estimate": asdict(self.estimate)})

    def seed_from_legacy(self):
        """Start once from the loss/gain the original PyScript learned, if its helpers remain."""
        if not self.legacy_seed_pending or not self.hass.is_running:
            return
        self.legacy_seed_pending = False
        values = [finite(state.state) if state else None
                  for state in map(self.hass.states.get, LEGACY_LOSS_GAIN)]
        if self.model.samples == 0 and None not in values:
            self.model.loss, self.model.gain = clamp(values[0], 0.001, 0.08), clamp(values[1], 0.005, 0.15)

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
        if key in ("output_entity", "operating_entity", "heating_mode_entity", "defrost_entity", "inhibit_entity", "sun_entity", "ac_entity"):
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
        active_heating = operating is not None and state_matches(operating.state, self.config["heating_state"])
        idle = operating is not None and state_matches(operating.state, self.config["heating_idle_state"])
        hot_water = operating is not None and state_matches(operating.state, self.config["disinfection_hot_water_state"])
        mode_mapped = bool(self.config.get("heating_mode_entity"))
        heating_mode = self.fresh_state("heating_mode_entity", now) if mode_mapped else None
        mode_enabled = heating_mode is not None and state_matches(heating_mode.state, self.config["heating_mode_state"])
        idle_heating = (mode_mapped and mode_enabled and operating is not None
                        and state_matches(operating.state, self.config["heating_idle_state"])
                        and not state_matches(operating.state, self.config["disinfection_hot_water_state"]))
        compressor_active = True if active_heating or hot_water else False if idle else None
        floor_active = True if active_heating else False if idle or hot_water else None
        defrost = self.fresh_state("defrost_entity", now) if self.config.get("defrost_entity") else None
        if defrost is not None and defrost.state == "on":
            floor_active = False
        elif self.config.get("defrost_entity") and defrost is None:
            floor_active = None
        duty, uninterrupted = self.compressor_interval(now, floor_active)
        reason = ""
        if indoor is None or not 0 <= indoor <= 45:
            reason = "Indoor temperature unavailable, stale, or invalid"
        elif outdoor is None or not -70 <= outdoor <= 60:
            reason = "Outdoor temperature unavailable, stale, or invalid"
        elif output is None:
            reason = "Water setpoint unavailable, stale, or invalid"
        elif mode_mapped and not mode_enabled:
            reason = "Space-heating mode disabled or unavailable"
        elif not active_heating and not idle_heating:
            reason = "Space-heating state not confirmed (including hot water, off, or unknown)"
        for key, label in (("defrost_entity", "Defrost"), ("inhibit_entity", "Another controller or inhibit")):
            if self.config.get(key):
                flag = self.fresh_state(key, now)
                if flag is None or flag.state != "off":
                    reason = f"{label} active or unavailable"
        if self.disinfection.blocks_heating:
            reason = "Tank disinfection or target restoration in progress; space-heating writes paused"
        if inlet is not None and not 0 <= inlet <= 85:
            water = None
        if outlet is not None and not 0 <= outlet <= 85:
            water = None
        valid_temperatures = (indoor is not None and 0 <= indoor <= 45
                              and outdoor is not None and -70 <= outdoor <= 60)
        return {"time": now.timestamp(), "indoor": indoor, "outdoor": outdoor, "water": water,
                "output": output, "blocked": reason,
                "heating_enabled": (mode_enabled if heating_mode is not None else None) if mode_mapped
                                    else True if active_heating else None,
                "compressor_active": compressor_active, "floor_heating_active": floor_active,
                "compressor_on_fraction": duty,
                "thermal_valid": valid_temperatures and floor_active is not None and (not floor_active or water is not None),
                "eligible": valid_temperatures and floor_active is not None and uninterrupted and (not floor_active or water is not None)}

    def note_operating_event(self, entity_id, state, now):
        """Capture short cycles and interruptions between five-minute samples."""
        def phase_for(value):
            if value is not None and state_matches(value, self.config["heating_state"]):
                return True
            if value is not None and any(state_matches(value, self.config[key]) for key in
                                         ("heating_idle_state", "disinfection_hot_water_state")):
                return False
            return None
        phase = phase_for(state)
        if entity_id == self.config.get("defrost_entity"):
            if state == "on":
                phase = False
            elif state == "off":
                operating = self.fresh_state("operating_entity", now)
                phase = phase_for(operating.state if operating else None)
            else:
                phase = None
        elif self.config.get("defrost_entity"):
            defrost = self.fresh_state("defrost_entity", now)
            if defrost is None:
                phase = None
            elif defrost.state == "on":
                phase = False
        self.operating_events.append((now.timestamp(), phase))
        self.operating_events = [(t, p) for t, p in self.operating_events if t >= now.timestamp() - 3600]
        if phase is None and self.previous is not None:
            self.previous["eligible"] = False

    def compressor_interval(self, now, active):
        if self.previous is None or not isinstance(self.previous.get("floor_heating_active"), bool):
            return None, True
        start, end = self.previous["time"], now.timestamp()
        if end <= start:
            return None, True
        events = [(t, p) for t, p in self.operating_events if start < t <= end]
        if not events:
            return ((float(self.previous["floor_heating_active"]) + float(active)) / 2
                    if isinstance(active, bool) else None), isinstance(active, bool)
        phase, cursor, on_seconds = self.previous["floor_heating_active"], start, 0.0
        for at, new_phase in events + [(end, active)]:
            if phase is None or new_phase is None:
                return None, False
            on_seconds += (at - cursor) * phase
            cursor, phase = at, new_phase
        return on_seconds / (end - start), True

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
            self.forecast_rows = []
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
                        self.forecast_rows.append((when, value, finite(row.get("cloud_coverage"))))
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
        dark = self.dark = sun.state == "below_horizon" if sun else local_now.hour >= self.planner_settings.quiet_start_hour or local_now.hour < self.planner_settings.morning_hour
        ac_active = self.ac.blocks_learning(now)
        if (snapshot["thermal_valid"] and self.mode != "off" and not ac_active):
            self.room_history = [(t, v) for t, v in self.room_history if 0 <= (now - t).total_seconds() <= 3600]
            if self.room_history and (now - self.room_history[-1][0]).total_seconds() > 600:
                self.room_history = []
            if not self.room_history or (now - self.room_history[-1][0]).total_seconds() >= 240:
                self.room_history.append((now, indoor))
        else:
            self.room_history = []
        rate = cooling_trend([(t.timestamp(), v) for t, v in self.room_history])
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
        planning_settings = replace(self.planner_settings,
            floor_lead_hours=max(self.planner_settings.floor_lead_hours, self.settings.thermal_response_hours))
        self.plan = decide_plan(planning_settings, self.cooldown, now=local_now,
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
            snapshot["eligible"] = snapshot["eligible"] and not ac_active and self.mode != "off"
            snapshot["night"] = self.dark
            self.seed_from_legacy()
            if snapshot["thermal_valid"]:
                self.model.observe(self.previous, snapshot, eligible=snapshot["eligible"])
                self.previous = snapshot
            else:
                self.previous = None
                self.model.emitter = None
            self.observe_house(now, snapshot)
            result.update(floor_estimate=self.estimate.slab, sun_glow=self.estimate.glow, model_bias=self.estimate.bias,
                          predicted_room=self.estimate.predicted)
            result.update(indoor=snapshot["indoor"], outdoor=snapshot["outdoor"], actual=snapshot["output"],
                heating_enabled=snapshot["heating_enabled"], compressor_active=snapshot["compressor_active"],
                floor_heating_active=snapshot["floor_heating_active"], learning_excluded_by_ac=ac_active,
                model_samples=self.model.samples, model_error=self.model.error,
                planner_status=self.planner_data.get("phase"), planner_target=self.planner_data.get("effective_target"))
            phase = self.planner_data.get("phase")
            rate = self.planner_data.get("observed_cooling_rate")
            recovery_allowed = (self.mode != "off" and not blocked and not ac_active
                                and phase not in ("coast", "ceiling_hold", "solar_wait"))
            recovery_boost = self.recovery.update(now.timestamp(), snapshot["indoor"], self.settings.target,
                rate, self.settings, enabled=recovery_allowed)
            result.update(observed_cooling_rate=rate, recovery_boost=recovery_boost)
            if self.mode == "off":
                result.update(status="off", reason="Automatic control and learning disabled")
            elif blocked:
                result.update(status="paused", reason=blocked)
            else:
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
                    indoor, snapshot["outdoor"], forecasts, sustained,
                    actual_water=snapshot["water"] if snapshot["water"] is not None else snapshot["output"],
                    actual_setpoint=snapshot["output"],
                    measured_cooling_rate=rate if recovery_allowed else None,
                    recovery_boost=recovery_boost)
                if planned:
                    proposed = decision.proposed
                    if phase != "recovery":
                        proposed = (self.plan.floor_water_target if self.plan.floor_water_target is not None
                                    else proposed + self.plan.floor_water_delta)
                    decision = replace(decision,
                        proposed=max(self.settings.minimum_water, min(self.settings.maximum_water, proposed)),
                        predicted_minimum=None, reason=self.planner_data["reason"])
                # Keep slow floor delivery while a cold room is still falling.
                # Deliberate night coasting/ceiling reductions retain their own
                # comfort policy. The final limiter remains authoritative.
                if (recovery_allowed and rate is not None and rate > 0.05
                        and snapshot["indoor"] < effective_settings.target - self.settings.comfort_band
                        and decision.proposed < snapshot["output"]):
                    decision = replace(decision, proposed=snapshot["output"], predicted_minimum=None,
                        reason=decision.reason + "; holding floor heat while the below-target room is cooling")
                # Actual room overheating overrides every phase, including a
                # missing forecast or recovery. AC attribution must never hide
                # the comfort ceiling; water slew limits still apply below.
                if self.planner_settings.cold_night_enabled and snapshot["indoor"] >= self.planner_settings.preheat_ceiling:
                    decision = replace(decision, proposed=self.settings.minimum_water, predicted_minimum=None,
                                       reason="Room reached the preheat ceiling; reducing floor heat within water limits")
                predictive = None if ac_active else await self.predictive_plan(now, snapshot)
                if predictive is not None:
                    decision = replace(decision, proposed=predictive[0], predicted_minimum=predictive[1], reason=predictive[2])
                    result.update(plan=predictive[3], plan_energy_kwh=predictive[4])
                result.update(proposed=decision.proposed, prediction=decision.predicted_minimum, reason=decision.reason)
                result.update(planning_outdoor=decision.planning_outdoor,
                              cooling_compensation=decision.cooling_compensation)
                limited = self.output_limit(decision.proposed, snapshot["output"], now)
                result["limited"] = limited
                if limited is None:
                    result.update(status="paused", reason="Setpoint or device limits invalid; check output entity and water limits")
                elif self.mode == "automatic":
                    # Evaluation buttons cannot bypass the time-based command limits.
                    # A minute of slack: timer jitter must not postpone a command by a whole interval.
                    due = self.last_cycle is None or (now - self.last_cycle).total_seconds() >= self.settings.control_minutes * 60 - 60
                    if due:
                        self.last_cycle = now
                        await self.apply(limited, snapshot["output"], result)
                    else:
                        result["status"] = "waiting"
            result["commanded"] = self.last_commanded
            self.events = ([{k: result[k] for k in ("checked_at", "status", "reason", "proposed", "limited", "commanded", "actual", "planner_status")}] + self.events)[:20]
            await self.async_save()
            return result

    def location(self):
        config = getattr(self.hass, "config", None)
        place = (finite(getattr(config, "latitude", None)), finite(getattr(config, "longitude", None)))
        return None if None in place else place

    def observe_house(self, now, snapshot):
        """Keep the planner's slab and sun estimates current, including while control is paused."""
        place = self.location()
        if place is None or not snapshot["thermal_valid"]:
            return
        cloud = next((c for t, _, c in sorted(self.forecast_rows) if t >= now - timedelta(hours=1)), None)
        duty = snapshot["compressor_on_fraction"]
        if duty is None:
            duty = 1.0 if snapshot["floor_heating_active"] else 0.0
        self.estimate.update(self.house, now.timestamp(), snapshot["indoor"], snapshot["outdoor"],
                             snapshot["output"], duty, mpc.sunshine(now, *place, cloud))

    async def predictive_plan(self, now, snapshot):
        """Cheapest water schedule that keeps the room in its band; None falls back to the heating curve."""
        place = self.location()
        rows = [row for row in self.forecast_rows if row[0] >= now - timedelta(hours=1)]
        if (not self.config.get("predictive", True) or place is None or self.estimate.slab is None
                or self.estimate.room is None or len(rows) < 12):
            return None
        state = self.hass.states.get(self.config["output_entity"])
        step = finite(state.attributes.get("step")) if state else None
        comfort = mpc.Comfort(target=self.settings.target,
            night_floor=min(self.settings.target, self.planner_settings.night_minimum),
            night_start=int(self.planner_settings.quiet_start_hour), warm_by=int(self.planner_settings.morning_hour),
            minimum_water=self.settings.minimum_water, maximum_water=self.settings.maximum_water,
            water_step=step if step and 0.5 <= step <= 2 else 1.0)
        offset = dt_util.as_local(now).utcoffset()
        steps = mpc.horizon(now, rows, comfort, *place, snapshot["outdoor"], offset.total_seconds() / 3600 if offset else 0.0)
        arguments = (self.house, comfort, steps, self.estimate.state(self.house), self.estimate.bias,
                     bool(snapshot["floor_heating_active"]), self.plan_seed)
        job = getattr(self.hass, "async_add_executor_job", None)
        plan = await job(mpc.plan, *arguments) if job else mpc.plan(*arguments)
        self.plan_seed = plan.levels
        boost = self.guard.update(snapshot["indoor"], steps[0].floor)
        water = min(comfort.maximum_water, plan.water + boost)
        day = plan.rooms[:48]
        reason = (f"Predictive plan: {water:.0f} °C water now; room {min(day):.1f}–{max(day):.1f} °C "
                  f"over 24 h for about {plan.energy_kwh * 48 / len(plan.rooms):.1f} kWh")
        if boost:
            reason += f"; +{boost:.0f} °C because the room is under its band"
        hourly = [{"at": (now + timedelta(hours=i / 2 + 0.5)).isoformat(timespec="minutes"),
                   "water": plan.waters[i], "room": round(plan.rooms[i], 2), "floor": steps[i].floor}
                  for i in range(1, 48, 2)]
        return water, round(min(day), 2), reason, hourly, round(plan.energy_kwh * 48 / len(plan.rooms), 2)

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
        interval = self.settings.control_minutes / 60
        # The command is stamped after the service call, so the next cycle is a
        # moment short of a full interval; that must still allow a full step.
        elapsed = interval if elapsed >= interval - 1 / 60 else elapsed
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
