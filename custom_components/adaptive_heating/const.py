"""Shared settings. No installation-specific entity IDs belong here."""

DOMAIN = "adaptive_heating"
VERSION = "0.6.1"
MIN_HA_VERSION = "2026.7.0"
REPOSITORY = "PovilJ/adaptive-heating"
MODES = ["off", "observe", "automatic"]
PLATFORMS = ["sensor", "number", "select", "button", "update"]

DEFAULTS = {
    "target": 22.0,
    "minimum_water": 25.0,
    "maximum_water": 40.0,
    "comfort_band": 0.3,
    "stale_minutes": 120,
    "heating_state": "HEAT",
    "heating_mode_state": "heat",
    "heating_idle_state": "OFF",
    "solar_preheat": False,
    "surplus_watts": 1000.0,
    "battery_ready_soc": 95.0,
    "preheat_degrees": 0.3,
    # Slab controller (0.6.0); first-house values. See docs/CONTROLLER.md.
    "run_output_kw": 6.5,
    "restart_hysteresis": 4.0,
    "loop_kw_per_celsius": 2.02,
    "slab_supply_share": 0.29,
    "control_sensor_offset": -0.8,
    "outlet_sensor_offset": 0.3,
}

REQUIRED_ENTITIES = {
    "indoor_entity": ["sensor"],
    "weather_entity": ["weather"],
    "output_entity": ["number"],
    "operating_entity": ["sensor", "binary_sensor", "select"],
    "inlet_entity": ["sensor"],
    "outlet_entity": ["sensor"],
}
OPTIONAL_ENTITIES = {
    "heating_mode_entity": ["number", "select", "sensor", "binary_sensor", "switch", "input_boolean"],
    "restart_hysteresis_entity": ["number", "sensor"],
    "outdoor_entity": ["sensor"],
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

# Options and mappings of the 0.3-0.5 heating curve, cold-night planner and predictive
# planner. Config entries of minor version 1 still carry them; migration 1.2 removes them.
RETIRED_OPTIONS = (
    "curve_slope", "curve_offset", "room_feedback", "thermal_response_hours", "rise_per_hour",
    "fall_per_hour", "control_minutes", "predictive", "cold_night_enabled", "preheat_ceiling",
    "night_minimum", "floor_lead_hours", "prepare_hour", "quiet_start_hour", "morning_hour",
    "cold_threshold", "cold_drop", "sun_entity", "protection_entity",
)
# Sensors of 0.5 with no meaning in 0.6; their registry entries are removed at setup.
RETIRED_SENSORS = ("prediction", "model_samples", "model_error", "planner_status", "planner_target")
