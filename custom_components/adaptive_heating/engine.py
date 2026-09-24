"""Deterministic, HA-independent controller. Temperatures are Celsius internally.

No COP, guessed flow, tariff assumptions, or battery dispatch. A bounded lag model
predicts comfort; water temperature is an explicitly documented efficiency proxy.
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
    target: float = 22.0
    minimum_water: float = 25.0
    maximum_water: float = 40.0
    comfort_band: float = 0.3
    curve_slope: float = 0.45
    curve_offset: float = 3.0
    room_feedback: float = 2.0
    rise_per_hour: float = 4.0
    fall_per_hour: float = 2.0
    control_minutes: int = 30
    stale_minutes: int = 120
    solar_preheat: bool = False
    surplus_watts: float = 1000.0
    battery_ready_soc: float = 95.0
    preheat_degrees: float = 0.3

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
        if not 0 <= self.curve_slope <= 2 or not -10 <= self.curve_offset <= 20:
            raise ValueError("Invalid heating curve")
        if not 0 <= self.room_feedback <= 10:
            raise ValueError("Invalid room feedback")
        if not 0.1 <= self.rise_per_hour <= 10 or not 0.1 <= self.fall_per_hour <= 10:
            raise ValueError("Invalid slew limits")
        if not 5 <= self.control_minutes <= 60 or not 10 <= self.stale_minutes <= 1440:
            raise ValueError("Invalid time settings")
        if not 100 <= self.surplus_watts <= 20000:
            raise ValueError("Invalid solar surplus threshold")
        if not 50 <= self.battery_ready_soc <= 100:
            raise ValueError("Invalid battery threshold")
        if not 0 <= self.preheat_degrees <= self.comfort_band:
            raise ValueError("Preheat must fit within the comfort band")


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


@dataclass
class Model:
    """Empirical temperature response, not a physical heat/energy meter."""
    loss: float = 0.012
    gain: float = 0.035
    lag_hours: float = 3.0
    emitter: float | None = None
    samples: int = 0
    error: float = 0.0

    @classmethod
    def restore(cls, data: dict | None) -> Model:
        model = cls()
        if not isinstance(data, dict):
            return model
        for name, bounds in {"loss": (0.001, 0.08), "gain": (0.005, 0.15),
                             "lag_hours": (0.5, 12), "error": (0, 10)}.items():
            value = finite(data.get(name))
            if value is not None:
                setattr(model, name, clamp(value, *bounds))
        samples = finite(data.get("samples"))
        if samples is not None:
            model.samples = int(clamp(samples, 0, 1000000))
        # Stored emitter temperature is deliberately not trusted after a restart.
        return model

    @property
    def usable(self) -> bool:
        return self.samples >= 24 and self.error <= 0.3

    def observe(self, previous: dict | None, current: dict, *, eligible: bool) -> None:
        """Bounded fitting using consecutive fresh measurements, actual elapsed time.

        Both ends of an interval must be ordinary heating and not sunny. Unknown
        disturbances are rejected by a residual limit. Samples still advance in
        the HA adapter even when fitting is rejected, avoiding stale night trends.
        """
        water = current.get("water")
        if finite(water) is None:
            self.emitter = None
            return
        if not previous or previous.get("water") is None:
            self.emitter = water
            return
        dt = (current["time"] - previous["time"]) / 3600
        if not 1 / 60 <= dt <= 1:
            self.emitter = water
            return
        start_emitter = self.emitter if self.emitter is not None else previous["water"]
        self.emitter = start_emitter + (water - start_emitter) * (1 - math.exp(-dt / self.lag_hours))
        if not eligible or not previous.get("eligible", False):
            return
        if previous.get("outdoor") is None or current.get("outdoor") is None:
            return
        air = previous["indoor"]
        delta_outdoor = air - previous["outdoor"]
        delta_water = max(0, start_emitter - air)
        rate = self.gain * delta_water - self.loss * delta_outdoor
        residual = current["indoor"] - (air + rate * dt)
        self.error = 0.9 * self.error + 0.1 * abs(residual)
        if abs(residual) > 0.3 or dt < 4 / 60:
            return
        norm = 1 + delta_outdoor**2 + delta_water**2
        correction = 0.015 * residual / dt / norm
        self.loss = clamp(self.loss - correction * delta_outdoor, 0.001, 0.08)
        self.gain = clamp(self.gain + correction * delta_water, 0.005, 0.15)
        self.samples += 1

    def predict(self, indoor: float, water: float, forecasts: list[float]) -> list[float]:
        emitter = self.emitter if self.emitter is not None else water
        result = []
        # 15-minute integration steps retain thermal inertia across forecast hours.
        for outdoor in forecasts[:12]:
            for _ in range(4):
                emitter += (water - emitter) * (1 - math.exp(-0.25 / self.lag_hours))
                indoor += 0.25 * (self.gain * max(0, emitter - indoor) - self.loss * (indoor - outdoor))
                result.append(indoor)
        return result


@dataclass(frozen=True)
class Decision:
    proposed: float
    predicted_minimum: float | None
    reason: str
    effective_target: float
    model_used: bool


def decide(settings: Settings, model: Model, indoor: float, outdoor: float,
           forecasts: list[float], solar_surplus: bool = False) -> Decision:
    if any(finite(v) is None for v in (indoor, outdoor)):
        raise ValueError("Essential temperature unavailable")
    forecasts = [v for v in forecasts[:12] if finite(v) is not None and -70 <= v <= 60]
    target = settings.target
    # PV only shifts a small amount of useful heating, never estimates solar warmth.
    preheat = settings.solar_preheat and solar_surplus and indoor < target + settings.preheat_degrees
    if preheat:
        target += settings.preheat_degrees
    weather_curve = target + settings.curve_offset + settings.curve_slope * max(0, target - outdoor)
    base = clamp(weather_curve + settings.room_feedback * (target - indoor),
                 settings.minimum_water, settings.maximum_water)
    reason = "Weather compensation with room feedback"
    prediction = None
    used = False
    if forecasts and model.usable and model.emitter is not None:
        # Prediction can move a proven baseline at most 2 C. No fabricated feasible
        # solution or fixed fallback temperature when the forecast disappears.
        candidates = [clamp(base + delta / 2, settings.minimum_water, settings.maximum_water)
                      for delta in range(-4, 5)]
        evaluated = []
        for water in candidates:
            path = model.predict(indoor, water, forecasts)
            score = sum(max(0, abs(t - target) - settings.comfort_band) ** 2 for t in path)
            score += 0.03 * (water - settings.minimum_water)
            evaluated.append((score, water, min(path)))
        _, base, prediction = min(evaluated)
        reason = "Forecast and measured response adjust the heating curve"
        used = True
    elif not forecasts:
        reason += "; forecast unavailable"
    else:
        reason += "; collecting reliable model observations"
    if preheat:
        reason += "; sustained PV surplus permits limited preheating"
    # No extra solar-gain term based on weather labels or generation. Indoor
    # feedback responds to actual warming, including sunshine with snow-covered PV.
    return Decision(round(base, 2), prediction, reason, target, used)


def limited_output(proposed: float, current: float, minimum: float, maximum: float,
                   step: float, device_origin: float, elapsed_hours: float,
                   rise_per_hour: float, fall_per_hour: float) -> float | None:
    """Apply *all* final bounds once, then select a supported value inside them.

    A coarse device step can mean no change is currently possible. An externally
    selected out-of-range setpoint must be corrected manually, not chased by this
    controller. This keeps rate and equipment constraints non-conflicting.
    """
    values = (proposed, current, minimum, maximum, step, device_origin,
              elapsed_hours, rise_per_hour, fall_per_hour)
    if any(finite(v) is None for v in values) or step <= 0 or minimum > maximum:
        return None
    if not minimum <= current <= maximum or elapsed_hours < 0:
        return None
    lower = max(minimum, current - fall_per_hour * elapsed_hours)
    upper = min(maximum, current + rise_per_hour * elapsed_hours)
    first = math.ceil((lower - device_origin) / step - 1e-8)
    last = math.floor((upper - device_origin) / step + 1e-8)
    if first > last:
        return None
    index = int(clamp(round((proposed - device_origin) / step), first, last))
    return round(device_origin + index * step, 6)
