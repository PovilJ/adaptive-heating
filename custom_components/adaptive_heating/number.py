"""Room target owned and persisted by the integration."""

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode

from .entity import HeatingEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([TargetTemperature(entry.runtime_data)])


class TargetTemperature(HeatingEntity, NumberEntity):
    _attr_native_min_value = 10.0
    _attr_native_max_value = 30.0
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = "°C"
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator):
        super().__init__(coordinator, "target", "Room target")

    @property
    def native_value(self):
        return self.coordinator.settings.target

    async def async_set_native_value(self, value):
        await self.coordinator.async_target(value)
