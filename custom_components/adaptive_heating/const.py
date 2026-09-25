"""Shared settings. No installation-specific entity IDs belong here."""

DOMAIN = "adaptive_heating"
VERSION = "0.3.0"
MIN_HA_VERSION = "2026.7.0"
REPOSITORY = "PovilJ/adaptive-heating"
MODES = ["off", "observe", "automatic"]
PLATFORMS = ["sensor", "number", "select", "button", "update"]

DEFAULTS = {
    "target": 22.0,
    "minimum_water": 25.0,
    "maximum_water": 40.0,
    "comfort_band": 0.3,
    "curve_slope": 0.45,
    "curve_offset": 3.0,
    "room_feedback": 2.0,
    "rise_per_hour": 4.0,
    "fall_per_hour": 2.0,
    "control_minutes": 30,
    "stale_minutes": 120,
    "heating_state": "HEAT",
    "solar_preheat": False,
    "surplus_watts": 1000.0,
    "battery_ready_soc": 95.0,
    "preheat_degrees": 0.3,
}

REQUIRED_ENTITIES = {
    "indoor_entity": ["sensor"],
    "weather_entity": ["weather"],
    "output_entity": ["number"],
    "operating_entity": ["sensor", "binary_sensor", "select"],
}
OPTIONAL_ENTITIES = {
    "outdoor_entity": ["sensor"],
    "inlet_entity": ["sensor"],
    "outlet_entity": ["sensor"],
    "defrost_entity": ["binary_sensor"],
    "inhibit_entity": ["input_boolean", "binary_sensor", "switch"],
    "electric_power_entity": ["sensor"],
    "electric_energy_entity": ["sensor"],
    "pv_entity": ["sensor"],
    "import_entity": ["sensor"],
    "export_entity": ["sensor"],
    "battery_soc_entity": ["sensor"],
    "battery_charge_entity": ["sensor"],
    "battery_discharge_entity": ["sensor"],
}
