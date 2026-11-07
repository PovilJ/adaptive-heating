"""Shared, HA-independent helpers: unit parsing, the main options and the solar-surplus rule.

Temperatures are Celsius internally. The heating controller itself is slab.py.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math


def finite(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def temperature(value: object, unit: str | None) -> float | None:
    number = finite(value)
    if number is None:
        return None
    if unit == "°C":
        return number
    if unit == "°F":
        return (number - 32.0) / 1.8
    return None


def power_watts(value: object, unit: str | None) -> float | None:
    number = finite(value)
    if number is None or unit not in ("W", "kW"):
        return None
    return number * (1000 if unit == "kW" else 1)


def clamp(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


@dataclass
class Settings:
    """Main heating options (validated). The slab controller's own parameters live in slab.py."""
    target: float = 22.0
    minimum_water: float = 25.0
    maximum_water: float = 40.0
    comfort_band: float = 0.3
    stale_minutes: int = 120
    solar_preheat: bool = False
    surplus_watts: float = 1000.0
    battery_ready_soc: float = 95.0
    preheat_degrees: float = 0.3
    run_output_kw: float = 6.5
    restart_hysteresis: float = 4.0
    loop_kw_per_celsius: float = 2.02
    slab_supply_share: float = 0.29
    control_sensor_offset: float = -0.8
    outlet_sensor_offset: float = 0.3

    def __post_init__(self):
        for key, value in asdict(self).items():
            if key != "solar_preheat" and finite(value) is None:
                raise ValueError(f"Non-finite setting: {key}")
        if not 10 <= self.target <= 30:
            raise ValueError("Target must be between 10 and 30 Celsius")
        if not 10 <= self.minimum_water < self.maximum_water <= 65:
            raise ValueError("Invalid water temperature limits")
        if not 0.1 <= self.comfort_band <= 2:
            raise ValueError("Invalid comfort band")
        if not 10 <= self.stale_minutes <= 1440:
            raise ValueError("Invalid time settings")
        if not 100 <= self.surplus_watts <= 20000:
            raise ValueError("Invalid solar surplus threshold")
        if not 50 <= self.battery_ready_soc <= 100:
            raise ValueError("Invalid battery threshold")
        if not 0 <= self.preheat_degrees <= self.comfort_band:
            raise ValueError("Preheat must fit within the comfort band")
        if not 0 <= self.run_output_kw <= 15 or not 2 <= self.restart_hysteresis <= 10:
            raise ValueError("Invalid run output or restart hysteresis")
        if not 0.5 <= self.loop_kw_per_celsius <= 10 or not 0 <= self.slab_supply_share <= 0.6:
            raise ValueError("Invalid loop flow or slab estimate share")
        if not -3 <= self.control_sensor_offset <= 3 or not -3 <= self.outlet_sensor_offset <= 3:
            raise ValueError("Invalid water sensor offsets")


@dataclass(frozen=True)
class Energy:
    pv_w: float | None = None
    import_w: float | None = None
    export_w: float | None = None
    battery_soc: float | None = None
    charge_w: float | None = None
    discharge_w: float | None = None
    battery_configured: bool = False


def surplus_available(energy: Energy, settings: Settings) -> bool:
    """All evidence must agree; zero imports and a high SoC are insufficient."""
    fields = [energy.pv_w, energy.import_w, energy.export_w]
    if any(finite(v) is None or v < 0 for v in fields):
        return False
    if energy.pv_w < settings.surplus_watts or energy.export_w < settings.surplus_watts:
        return False
    if energy.import_w > 100:
        return False
    if energy.battery_configured:
        fields = [energy.battery_soc, energy.charge_w, energy.discharge_w]
        if any(finite(v) is None or v < 0 for v in fields):
            return False
        if not settings.battery_ready_soc <= energy.battery_soc <= 100:
            return False
        if energy.discharge_w > 50 or energy.charge_w > 100:
            return False
    return True
