"""Bounded cold-night preparation using empirical low-water room cooldown.

This is a comfort policy, not an electricity optimiser or an estimate of stored
thermal energy. Forecast sunshine never adds heat to a temperature projection.
The HA adapter must provide fresh readings, local aware times, and the eligibility
gate for cooldown fitting (dark, settled low-water operation, no AC or tank heat).
All water recommendations still pass the existing actuator and slew limits.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import math


DEFAULTS = {
    "cold_night_enabled": False,
    "preheat_ceiling": 23.0,
    "night_minimum": 20.0,
    "floor_lead_hours": 3.0,
    "prepare_hour": 15,
    "quiet_start_hour": 20,
    "morning_hour": 9,
    "cold_threshold": -15.0,
    "cold_drop": 3.0,
}
ENTITIES = {}
HORIZON_HOURS = 24
COMFORT_MARGIN = 0.3
PRIOR_LOSS = 0.4 / 50.0  # Conservative seed: 0.4 °C/h at a 50 °C air difference.


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _aware(value):
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _shift(value, duration):
    """Add elapsed time without losing/repeating an hour at a DST change."""
    return (value.astimezone(timezone.utc) + duration).astimezone(value.tzinfo)


@dataclass(frozen=True)
class PlannerSettings:
    cold_night_enabled: bool = False
    preheat_ceiling: float = 23.0
    night_minimum: float = 20.0
    floor_lead_hours: float = 3.0
    prepare_hour: int = 15
    quiet_start_hour: int = 20
    morning_hour: int = 9
    cold_threshold: float = -15.0
    cold_drop: float = 3.0

    def __post_init__(self):
        if not isinstance(self.cold_night_enabled, bool):
            raise ValueError("Cold-night enable must be boolean")
        if any(not _finite(v) for k, v in asdict(self).items() if k != "cold_night_enabled"):
            raise ValueError("Planner settings must be finite")
        if not 10 <= self.night_minimum < self.preheat_ceiling <= 30:
            raise ValueError("Invalid planning comfort limits")
        if self.preheat_ceiling - self.night_minimum < 0.5:
            raise ValueError("Planning comfort limits need at least 0.5 Celsius separation")
        if not 0.5 <= self.floor_lead_hours <= 8:
            raise ValueError("Floor lead must be between 0.5 and 8 hours")
        hours = (self.morning_hour, self.prepare_hour, self.quiet_start_hour)
        if any(int(h) != h for h in hours) or not 0 <= hours[0] < hours[1] < hours[2] <= 23:
            raise ValueError("Require morning < preparation < quiet-start hours")
        if not -40 <= self.cold_threshold <= 0 or not 1 <= self.cold_drop <= 20:
            raise ValueError("Invalid cold forecast thresholds")


@dataclass(frozen=True)
class ForecastPoint:
    at: datetime
    temperature: float
    condition: str | None = None


@dataclass
class CooldownModel:
    """Bounded empirical room cooldown per degree indoor/outdoor difference.

    The owner's roughly two-degree overnight drop is only an initial qualitative
    observation. The deliberately higher 0.4 °C/h prior is labelled uncalibrated.
    Low-water operation may still provide heat: this is not a measured unheated
    building heat-loss coefficient. Stored samples never restore an in-flight
    observation across a restart.
    """

    loss: float = PRIOR_LOSS
    samples: int = 0
    hours: float = 0.0
    error: float = 0.0
    _previous: tuple | None = field(default=None, repr=False)

    @classmethod
    def restore(cls, data):
        model = cls()
        if isinstance(data, dict):
            for name, lower, upper in (("loss", 0.001, 0.04), ("hours", 0, 100000),
                                       ("error", 0, 2), ("samples", 0, 1000000)):
                value = data.get(name)
                if _finite(value):
                    setattr(model, name, min(upper, max(lower, value)))
            model.samples = int(model.samples)
        return model

    def to_dict(self):
        return {key: getattr(self, key) for key in ("loss", "samples", "hours", "error")}

    @property
    def calibrated(self):
        return self.samples >= 12 and self.hours >= 2 - 1e-6

    def observe(self, at, indoor, outdoor, *, eligible):
        """Fit only consecutive eligible endpoints; the caller owns physical gates."""
        if (not eligible or not _aware(at) or not _finite(indoor) or not 0 <= indoor <= 45
                or not _finite(outdoor) or not -70 <= outdoor <= 60):
            self._previous = None
            return
        previous = self._previous
        self._previous = (at.timestamp(), indoor, outdoor)
        if previous is None:
            return
        dt = (at.timestamp() - previous[0]) / 3600
        if not 5 / 60 <= dt <= 1:
            return
        difference = (previous[1] + indoor - previous[2] - outdoor) / 2
        rate = (previous[1] - indoor) / dt
        # Warming/disturbances, near-zero air differences, and abrupt sensor
        # jumps cannot establish the low-water cooldown coefficient.
        if difference < 5 or not 0 <= rate <= 2:
            return
        observed = rate / difference
        self.error = 0.9 * self.error + 0.1 * abs(rate - self.loss * difference)
        self.loss = min(0.04, max(0.001, 0.9 * self.loss + 0.1 * observed))
        self.samples += 1
        self.hours += dt

    def cooling_rate(self, indoor, outdoor):
        # An uncertainty allowance remains after calibration. An immature fit
        # may increase the conservative prior, but cannot reduce it.
        loss = max(self.loss * 1.2, self.loss + self.error / 50) if self.calibrated else max(PRIOR_LOSS, self.loss + self.error / 50)
        return max(0.0, indoor - outdoor) * loss


@dataclass(frozen=True)
class Plan:
    phase: str
    reason: str
    effective_target: float
    floor_water_delta: float = 0.0
    floor_water_target: float | None = None
    ac_requested: bool = False
    diagnostics: dict = field(default_factory=dict)


def _validated_forecast(forecasts, now, required_until):
    if not isinstance(forecasts, (list, tuple)):
        return []
    now_utc = now.astimezone(timezone.utc)
    points = []
    for point in forecasts:
        if not isinstance(point, ForecastPoint) or not _aware(point.at):
            return []
        point_at = point.at.astimezone(timezone.utc)
        if now_utc - timedelta(minutes=90) <= point_at <= now_utc + timedelta(hours=HORIZON_HOURS):
            if not _finite(point.temperature) or not -70 <= point.temperature <= 60:
                return []
            points.append(ForecastPoint(point_at, point.temperature, point.condition))
    points.sort(key=lambda p: p.at)
    if len(points) < 2 or points[0].at > now_utc + timedelta(hours=1):
        return []
    if points[-1].at < required_until:
        return []
    if any(not 1800 <= (b.at - a.at).total_seconds() <= 5400 for a, b in zip(points, points[1:])):
        return []
    return points


def _outdoor_at(points, at, current_outdoor, now):
    previous_time, previous_temp = now, current_outdoor
    for point in points:
        if point.at <= now:
            continue
        if point.at >= at:
            span = (point.at - previous_time).total_seconds()
            fraction = (at - previous_time).total_seconds() / span if span else 0
            return previous_temp + fraction * (point.temperature - previous_temp)
        previous_time, previous_temp = point.at, point.temperature
    return previous_temp


def _project(model, points, now, indoor, outdoor, end, observed_rate):
    """Low-water 15-minute projection: no sun gain or thermal-energy estimate."""
    now = now.astimezone(timezone.utc)
    end = end.astimezone(timezone.utc)
    at, room = now, indoor
    path = [(at, room)]
    while at < end:
        next_at = min(end, at + timedelta(minutes=15))
        outside = _outdoor_at(points, at, outdoor, now)
        rate = max(model.cooling_rate(room, outside), observed_rate)
        room -= rate * (next_at - at).total_seconds() / 3600
        at = next_at
        path.append((at, room))
    return path


def decide_plan(settings, model, *, now, indoor, outdoor, room_target, forecasts,
                next_sunset=None, measured_cooling_rate=None, coast_water_target=None,
                recovery_ramp_hours=0.0):
    """Return a comfort plan; positive measured_cooling_rate means room cooling.

    A supplied trend must represent a reliable recent interval, not one noisy
    sensor change. The adapter also supplies a commissioned low-water setpoint
    for coasting; without that setpoint this policy never claims to coast.
    recovery_ramp_hours includes the adapter's conservative actuator ramp and
    command delay, in addition to the configured physical floor response time.
    """
    target = room_target if _finite(room_target) else 22.0
    diagnostic = {"calibrated": model.calibrated, "cooling_samples": model.samples,
                  "cooling_rate": None, "predicted_minimum": None, "forecast_hours": 0,
                  "reserve_sufficient": None, "cooling_model": "empirical low-water cooldown" if model.calibrated else "uncalibrated conservative prior",
                  "floor_lead_hours": settings.floor_lead_hours,
                  "recovery_ramp_hours": recovery_ramp_hours if _finite(recovery_ramp_hours) else None,
                  "effective_recovery_lead_hours": None}

    def result(phase, reason, effective=target, delta=0.0, water=None, ac=False):
        return Plan(phase, reason, effective, delta, water, ac, dict(diagnostic))

    if not settings.cold_night_enabled:
        return result("disabled", "Cold-night planning disabled; using the normal heating curve")
    if not _finite(recovery_ramp_hours) or recovery_ramp_hours < 0:
        return result("baseline", "A finite nonnegative recovery ramp is required; using the normal heating curve")
    recovery_hours = settings.floor_lead_hours + recovery_ramp_hours
    diagnostic["effective_recovery_lead_hours"] = recovery_hours
    if recovery_hours > HORIZON_HOURS:
        return result("baseline", "Recovery delay exceeds the 24-hour planning horizon; using the normal heating curve")
    if (not _aware(now) or not _finite(indoor) or not 0 <= indoor <= 45
            or not _finite(outdoor) or not -70 <= outdoor <= 60
            or not _finite(room_target) or not settings.night_minimum <= target <= settings.preheat_ceiling):
        return result("baseline", "Fresh temperatures and compatible comfort limits required; using the normal heating curve")

    today_morning = now.replace(hour=int(settings.morning_hour), minute=0, second=0, microsecond=0)
    night_start = now.replace(hour=int(settings.quiet_start_hour), minute=0, second=0, microsecond=0)
    lead = timedelta(hours=settings.floor_lead_hours)
    recovery_lead = timedelta(hours=recovery_hours)
    morning_window = today_morning <= now < _shift(today_morning, lead)
    if now < _shift(today_morning, lead):
        night_start -= timedelta(days=1)
    morning = night_start.replace(hour=int(settings.morning_hour)) + timedelta(days=1)
    required_until = max(morning, _shift(now, recovery_lead)) if morning_window else morning
    points = _validated_forecast(forecasts, now, required_until)
    if not points:
        return result("baseline", "A continuous hourly forecast through the morning is required; using the normal heating curve")

    future = [p for p in points if p.at >= now]
    overnight = [p for p in points if max(now, night_start) <= p.at <= required_until]
    diagnostic.update(forecast_hours=round((points[-1].at - now).total_seconds() / 3600, 2),
                      night_start=night_start.isoformat(), morning_at=morning.isoformat())
    # Two consecutive hours of cold or a substantial drop are needed; a lone
    # implausible cold point does not request a heat-storage cycle.
    sustained = any(
        b.at - a.at >= timedelta(minutes=30)
        and (max(a.temperature, b.temperature) <= settings.cold_threshold
             or max(a.temperature, b.temperature) <= min(0, outdoor - settings.cold_drop))
        for a, b in zip(overnight, overnight[1:])
    )
    if not sustained and not morning_window:
        return result("baseline", "No sustained cold night or substantial cold drop forecast; using the normal heating curve")

    observed_rate = max(0.0, measured_cooling_rate) if _finite(measured_cooling_rate) else 0.0
    diagnostic["cooling_rate"] = round(max(model.cooling_rate(indoor, outdoor), observed_rate), 3)
    sunny_rows = [p for p in future if morning <= p.at <= _shift(morning, timedelta(hours=3))]
    sunny_morning = (points[-1].at >= _shift(morning, recovery_lead)
                     and any(a.condition == b.condition == "sunny" for a, b in zip(sunny_rows, sunny_rows[1:])))
    projection_end = max(required_until, _shift(morning, recovery_lead)) if sunny_morning else required_until
    path = _project(model, points, now, indoor, outdoor, projection_end, observed_rate)
    diagnostic["predicted_minimum"] = round(min(value for _, value in path), 2)
    diagnostic["reserve_sufficient"] = min(value for _, value in path) >= settings.night_minimum + COMFORT_MARGIN
    # Recovery starts before both the actuator ramp and physical floor delay.
    danger_at = next((at for at, value in path if value <= settings.night_minimum + COMFORT_MARGIN), None)
    cloudy_recovery = _shift(morning, -recovery_lead)
    # Sunshine changes the preferred recovery time only. The no-solar cooling
    # projection can always force an earlier restart, including on clear days.
    scheduled_recovery = morning if sunny_morning else cloudy_recovery
    recovery = min(scheduled_recovery, danger_at - recovery_lead) if danger_at else scheduled_recovery
    diagnostic.update(recovery_at=recovery.isoformat(), sunny_morning=sunny_morning)

    prepare = night_start.replace(hour=int(settings.prepare_hour))
    if _aware(next_sunset):
        local_sunset = next_sunset.astimezone(now.tzinfo)
        if local_sunset.date() == night_start.date() and local_sunset <= night_start:
            prepare = _shift(local_sunset, -lead)
    drop_at = next((p.at for p in future if p.at < night_start and p.temperature <= outdoor - settings.cold_drop), None)
    if drop_at is not None:
        prepare = min(prepare, drop_at - lead)
    diagnostic["prepare_at"] = prepare.isoformat()
    low_water = coast_water_target if _finite(coast_water_target) and 10 <= coast_water_target <= 65 else None

    if night_start <= now < morning:
        if now >= recovery:
            reason = "Restarting the floor before the night minimum is threatened" if danger_at else "Morning recovery starts early enough for the water ramp and floor delay"
            if observed_rate > model.cooling_rate(indoor, outdoor):
                reason += "; measured rapid cooling overrides the learned estimate"
            return result("recovery", reason)
        if low_water is None:
            return result("baseline", "A valid low-water setpoint is required for coasting; using the normal heating curve")
        return result("coast", "Using the measured comfort reserve; floor recovery remains scheduled before the minimum", settings.night_minimum + COMFORT_MARGIN, water=low_water)

    # After a sunny morning, only actual warming can justify waiting. Forecast
    # sunshine by itself is never treated as a temperature rise or stored heat.
    if morning_window and _finite(measured_cooling_rate) and measured_cooling_rate < -0.05:
        day_sun = [p for p in future if now <= p.at <= _shift(now, timedelta(hours=3))]
        rising_sun = any(a.condition == b.condition == "sunny" for a, b in zip(day_sun, day_sun[1:]))
        safe_path = _project(model, points, now, indoor, outdoor, _shift(now, recovery_lead), 0)
        if rising_sun and low_water is not None and min(v for _, v in safe_path) > settings.night_minimum + COMFORT_MARGIN:
            return result("solar_wait", "Room temperature is actually rising in sunshine; watching the minimum before adding floor heat", settings.night_minimum + COMFORT_MARGIN, water=low_water)

    if morning_window:
        return result("recovery", "Morning recovery uses measured temperature; forecast sunshine does not supply heat")

    if now < prepare:
        return result("scheduled", "Cold-night preparation is scheduled using sunset, the forecast drop and floor delay")
    if indoor >= settings.preheat_ceiling:
        return result("ceiling_hold", "Preparation paused at the room comfort ceiling", target, water=low_water)
    if diagnostic["reserve_sufficient"]:
        return result("scheduled", "The estimated room reserve already covers the cold window; no additional preheat requested")
    # Air reserve is capped and is not described as slab charge or thermal kWh.
    # A warm sunny room below the ceiling does not cancel deliberate floor prep.
    preparation_target = min(settings.preheat_ceiling, max(target, indoor + settings.night_minimum + COMFORT_MARGIN - diagnostic["predicted_minimum"]))
    return result("prepare", "Preparing the floor and room reserve before the cold night; no future solar heat is assumed",
                  round(preparation_target, 2), delta=2.0, ac=indoor < preparation_target - 0.1)
