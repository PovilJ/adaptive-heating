"""Pure hot-water policy and sampled, continuous temperature-hold tracking.

The defaults preserve the owner's historical settings. Completion means the
configured sensor/time criterion was met, not verification of water hygiene.
"""

from dataclasses import asdict, dataclass

from .engine import finite


DEFAULTS = {
    "disinfection_target": 68.0,
    "disinfection_threshold": 65.0,
    "disinfection_hold_minutes": 5,
    "disinfection_min_days": 12,
    "disinfection_max_days": 16,
    "disinfection_timeout_hours": 4.0,
    "disinfection_sample_seconds": 90,
    "disinfection_hot_water_state": "HOT WATER",
    "disinfection_idle_state": "OFF",
}
ENTITIES = {
    "tank_temperature_entity": ["sensor"],
    "tank_target_entity": ["number"],
}


@dataclass(frozen=True)
class DisinfectionSettings:
    disinfection_target: float = 68
    disinfection_threshold: float = 65
    disinfection_hold_minutes: int = 5
    disinfection_min_days: int = 12
    disinfection_max_days: int = 16
    disinfection_timeout_hours: float = 4
    disinfection_sample_seconds: int = 90

    def __post_init__(self):
        if any(finite(v) is None for v in asdict(self).values()):
            raise ValueError("Non-finite disinfection setting")
        if not 40 <= self.disinfection_threshold <= self.disinfection_target <= 80:
            raise ValueError("Require 40 <= hold threshold <= tank target <= 80 Celsius")
        if not 1 <= self.disinfection_hold_minutes <= 60:
            raise ValueError("Hold must be 1–60 minutes")
        if not 1 <= self.disinfection_min_days <= self.disinfection_max_days <= 60:
            raise ValueError("Invalid scheduling window")
        if not 0.25 <= self.disinfection_timeout_hours <= 8:
            raise ValueError("Timeout must be 0.25–8 hours")
        if self.disinfection_hold_minutes * 60 >= self.disinfection_timeout_hours * 3600:
            raise ValueError("Timeout must exceed the hold duration")
        if not 30 <= self.disinfection_sample_seconds <= 300:
            raise ValueError("Maximum sample age/gap must be 30–300 seconds")


@dataclass
class TemperatureHold:
    """Count elapsed sensor-report time, never repeated polls or missing time."""
    since: float | None = None
    previous: float | None = None
    seconds: float = 0

    def reset(self):
        self.since = self.previous = None
        self.seconds = 0

    def observe(self, now, reported, value, settings):
        gap = settings.disinfection_sample_seconds
        if (finite(value) is None or finite(reported) is None
                or not 0 <= now - reported <= gap
                or value < settings.disinfection_threshold):
            self.reset()
            return False
        if self.previous is not None and reported == self.previous:
            return False
        if self.previous is None or not 0 < reported - self.previous <= gap:
            self.since = reported
        self.previous = reported
        self.seconds = max(0, reported - self.since)
        return self.seconds >= settings.disinfection_hold_minutes * 60


def schedule(settings, *, now, last_success, indoor, room_target, comfort_band,
             tank, hot_water, outdoor, forecast, local_hour, surplus, battery_ready):
    """Return eligibility and explanation; equipment guards always run separately."""
    if last_success is None:
        return False, "No verified cycle yet; use Run disinfection to establish the first completion"
    if last_success > now:
        return False, "Last completion is in the future; check the Home Assistant clock"
    days = (now - last_success) / 86400
    if days < settings.disinfection_min_days:
        return False, "Not due; waiting for the scheduling window"
    if days >= settings.disinfection_max_days:
        return True, "Scheduling deadline reached; energy and comfort preferences no longer defer the cycle"
    if indoor is None or indoor < room_target - comfort_band:
        return False, "Waiting for room comfort before interrupting space heating"
    if not battery_ready:
        return False, "Waiting for battery priority: charge level and charge/discharge power"
    if surplus:
        return True, "Room comfortable and measured solar surplus sustained for at least 15 minutes"
    if hot_water and tank is not None and tank >= 50:
        return True, "Room comfortable; extending an existing warm-tank hot-water run"
    warmer_later = outdoor is not None and any(v > outdoor + 2 for v in forecast[:6])
    if (12 <= local_hour < 16 and outdoor is not None and outdoor > 0
            and tank is not None and tank >= 50 and not warmer_later):
        return True, "Room comfortable; warm tank and suitable afternoon weather"
    return False, "Waiting for solar surplus, an existing hot-water run, or a warmer afternoon window"
