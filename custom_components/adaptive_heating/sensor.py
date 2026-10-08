"""Expose the recommendation, bounded command, and actual device state separately."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory

from .entity import HeatingEntity

SENSORS = [
    ("status", "Status", None, None),
    ("reason", "Decision reason", None, None),
    ("proposed", "Proposed water temperature", "°C", SensorDeviceClass.TEMPERATURE),
    ("limited", "Limited water temperature", "°C", SensorDeviceClass.TEMPERATURE),
    ("commanded", "Last commanded water temperature", "°C", SensorDeviceClass.TEMPERATURE),
    ("actual", "Actual water setpoint", "°C", SensorDeviceClass.TEMPERATURE),
    ("prediction", "Predicted minimum room temperature", "°C", SensorDeviceClass.TEMPERATURE),
    ("model_samples", "Learning samples", None, None),
    ("model_error", "Model prediction error", "°C", None),
    ("electric_power", "Electrical power", "W", SensorDeviceClass.POWER),
    ("electric_energy", "Electrical energy", "kWh", SensorDeviceClass.ENERGY),
    ("disinfection_status", "Disinfection status", None, None),
    ("disinfection_hold", "Disinfection hold progress", "min", SensorDeviceClass.DURATION),
    ("planner_status", "Cold-night plan", None, None),
    ("planner_target", "Planned room target", "°C", SensorDeviceClass.TEMPERATURE),
    ("ac_status", "AC assistance", None, None),
    ("ac_power", "AC electrical power", "W", SensorDeviceClass.POWER),
    ("ac_energy", "AC session electricity", "kWh", SensorDeviceClass.ENERGY),
]


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(HeatingSensor(entry.runtime_data, *description) for description in SENSORS)


class HeatingSensor(HeatingEntity, SensorEntity):
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
        if key in ("model_samples", "model_error"):
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
        if self.key == "planner_status":
            return self.coordinator.planner_data
        if self.key == "ac_status":
            return self.coordinator.ac.attributes()
        if self.key == "disinfection_status":
            return self.coordinator.disinfection.attributes()
        if self.key == "status":
            return {"recent_decisions": self.coordinator.events, "mode": self.coordinator.mode,
                    "sustained_solar_surplus": (self.coordinator.data or {}).get("surplus"),
                    "heating_enabled": (self.coordinator.data or {}).get("heating_enabled"),
                    "compressor_active": (self.coordinator.data or {}).get("compressor_active"),
                    "floor_heating_active": (self.coordinator.data or {}).get("floor_heating_active"),
                    "learning_excluded_by_ac": (self.coordinator.data or {}).get("learning_excluded_by_ac"),
                    "floor_response_hours": self.coordinator.model.lag_hours,
                    "estimated_floor_heat_state_celsius": self.coordinator.model.emitter,
                    "learning_heating_hours": self.coordinator.model.heating_hours,
                    "learning_idle_hours": self.coordinator.model.idle_hours,
                    "observed_room_cooling_celsius_per_hour": (self.coordinator.data or {}).get("observed_cooling_rate"),
                    "forecast_planning_outdoor_celsius": (self.coordinator.data or {}).get("planning_outdoor"),
                    "water_cooling_compensation_celsius": (self.coordinator.data or {}).get("cooling_compensation"),
                    "water_recovery_assistance_celsius": (self.coordinator.data or {}).get("recovery_boost"),
                    "restart_required": self.coordinator.releases.restart_pending}
        return None
