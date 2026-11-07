"""Expose the recommendation, bounded command, and actual device state separately."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory

from .entity import HeatingEntity

SENSORS = [
    ("status", "Status", None, None),
    ("reason", "Decision reason", None, None),
    ("cycle", "Heating cycle", None, None),
    ("slab_estimate", "Floor estimate", "°C", SensorDeviceClass.TEMPERATURE),
    ("slab_target", "Floor target", "°C", SensorDeviceClass.TEMPERATURE),
    ("proposed", "Proposed water temperature", "°C", SensorDeviceClass.TEMPERATURE),
    ("limited", "Limited water temperature", "°C", SensorDeviceClass.TEMPERATURE),
    ("commanded", "Last commanded water temperature", "°C", SensorDeviceClass.TEMPERATURE),
    ("actual", "Actual water setpoint", "°C", SensorDeviceClass.TEMPERATURE),
    ("writes_24h", "Setpoint writes in 24 h", None, None),
    ("electric_power", "Electrical power", "W", SensorDeviceClass.POWER),
    ("electric_energy", "Electrical energy", "kWh", SensorDeviceClass.ENERGY),
    ("disinfection_status", "Disinfection status", None, None),
    ("disinfection_hold", "Disinfection hold progress", "min", SensorDeviceClass.DURATION),
    ("ac_status", "AC assistance", None, None),
    ("ac_power", "AC electrical power", "W", SensorDeviceClass.POWER),
    ("ac_energy", "AC session electricity", "kWh", SensorDeviceClass.ENERGY),
]


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(HeatingSensor(entry.runtime_data, *description) for description in SENSORS)


class HeatingSensor(HeatingEntity, SensorEntity):
    # The controller steps every minute; keep its diagnostics, which change nearly every step,
    # out of the recorder (the floor estimate and target are recorded as their own sensors).
    _unrecorded_attributes = frozenset({
        "recent_decisions", "daily_pattern", "fallback_curve", "target_parts", "reason", "slab_estimate",
        "slab_target", "start_below", "stop_above", "minutes_in_phase", "room_error", "forecast_outdoor_1_9h",
        "forecast_sun_1_9h_wm2", "sun_now_wm2", "warmer_next_3h", "run_output_kw", "wanted_setpoint",
        "writes_24h", "unowned_stops_24h", "learned_integral"})

    def __init__(self, coordinator, key, name, unit, device_class):
        super().__init__(coordinator, key, name)
        self.key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        if unit is not None:
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING if key == "electric_energy" else SensorStateClass.MEASUREMENT
        if key == "ac_energy":
            # A session counter resets per borrowed AC session; it is not a
            # lifetime meter and must not enter HA's cumulative energy totals.
            self._attr_state_class = None
        if key == "writes_24h":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        if self.key == "ac_status":
            return self.coordinator.ac.status
        if self.key in ("ac_power", "ac_energy"):
            attrs = self.coordinator.ac.attributes()
            return attrs.get("power_w" if self.key == "ac_power" else "session_energy_kwh")
        if self.key == "disinfection_status":
            return self.coordinator.disinfection.status
        if self.key == "disinfection_hold":
            return round(self.coordinator.disinfection.hold.seconds / 60, 2)
        value = (self.coordinator.data or {}).get(self.key)
        return value[:255] if isinstance(value, str) else value

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        if self.key == "cycle":
            # The controller's own view: floor estimate and target with its parts, learned state.
            return self.coordinator.core.attributes()
        if self.key == "ac_status":
            return self.coordinator.ac.attributes()
        if self.key == "disinfection_status":
            return self.coordinator.disinfection.attributes()
        if self.key == "status":
            return {"recent_decisions": self.coordinator.events, "mode": self.coordinator.mode,
                    "sustained_solar_surplus": data.get("surplus"),
                    "heating_enabled": data.get("heating_enabled"),
                    "compressor_active": data.get("compressor_active"),
                    "floor_heating_active": data.get("floor_heating_active"),
                    "learning_excluded_by_ac": data.get("learning_excluded_by_ac"),
                    "room_sensor": self.coordinator.core.room_state,
                    "restart_hysteresis_source": "unit register" if self.coordinator.config.get(
                        "restart_hysteresis_entity") else "option",
                    "restart_required": self.coordinator.releases.restart_pending}
        return None
