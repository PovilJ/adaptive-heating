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
        if key in ("model_samples", "model_error"):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        value = (self.coordinator.data or {}).get(self.key)
        return value[:255] if isinstance(value, str) else value

    @property
    def extra_state_attributes(self):
        if self.key == "status":
            return {"recent_decisions": self.coordinator.events, "mode": self.coordinator.mode,
                    "sustained_solar_surplus": (self.coordinator.data or {}).get("surplus"),
                    "restart_required": self.coordinator.releases.restart_pending}
        return None
