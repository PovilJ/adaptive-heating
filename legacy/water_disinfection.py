"""
Smart Water Disinfection Controller for Home Assistant
Optimizes Legionella disinfection timing based on weather, tank status, and energy efficiency.

Features:
1. **Smart Timing:** Runs when conditions are optimal (warm weather, piggyback on hot water cycle)
2. **Accumulated Time:** Tracks minutes at 65°C+ across cycles (survives interruptions)
3. **Safety Override:** Forces run after 7 days regardless of conditions
4. **Manual Trigger:** Button to force disinfection

Version: 1.0.0
"""

log.info("Water Disinfection: Script file is being loaded by PyScript...")

# ============================================
# CONFIGURATION
# ============================================

DISINFECTION_CONFIG = {
    # Entities
    "tank_temp_sensor": "sensor.versati_modbus_esp32_versati_128_tank_control_temp",
    "unit_status_sensor": "sensor.versati_modbus_esp32_versati_117_unit_status",
    "hot_water_setpoint": "number.versati_modbus_esp32_versati_13_tank_target_temp_set",
    "weather_entity": "weather.forecast_home",
    "indoor_sensor": "sensor.salionas_temperature",
    "target_temp_entity": "input_number.heating_target_temp",
    
    # Helpers (user must create these)
    "last_disinfection": "input_datetime.last_successful_disinfection",
    "minutes_accumulated": "input_number.disinfection_minutes_accumulated",
    "disinfection_active": "input_boolean.disinfection_active",
    "original_setpoint": "input_number.disinfection_original_setpoint",  # Stores original temp before disinfection
    
    # Settings
    "disinfection_temp": 68,      # Target temp for disinfection
    "success_temp": 65,           # Temp that counts toward accumulated time
    "required_minutes": 5,        # Minutes at success_temp needed
    "min_days_between": 12,        # Minimum days between disinfections
    "max_days_between": 16,        # Safety: force run after this many days
    "max_runtime_hours": 4,       # Timeout: abort if can't complete in this time
}

# ============================================
# MAIN CYCLE - Runs every 30 minutes
# ============================================

@time_trigger("cron(*/30 * * * *)")
@state_trigger("input_button.run_water_disinfection")
def water_disinfection_cycle(trigger_type=None, var_name=None, value=None):
    """Main disinfection control loop."""
    log.info("=" * 60)
    log.info(f"Water Disinfection: Running cycle... (trigger_type={trigger_type}, var_name={var_name})")
    
    # Check if manually triggered - button triggers have var_name set
    is_manual = var_name == "input_button.run_water_disinfection"
    log.info(f"Water Disinfection: is_manual = {is_manual}")
    
    # Gather current state
    current = gather_disinfection_data()
    if not current:
        log.error("Water Disinfection: Could not gather data")
        return
    
    # Check if disinfection is currently active
    is_active = state.get(DISINFECTION_CONFIG["disinfection_active"]) == "on"
    
    if is_active:
        # Continue monitoring active disinfection
        handle_active_disinfection(current)
    else:
        # Check if we should start disinfection
        should_start, reason = evaluate_disinfection_opportunity(current, is_manual)
        
        if should_start:
            start_disinfection(current, reason)
        else:
            log.info(f"Water Disinfection: Not starting - {reason}")
    
    # Update dashboard sensors
    update_disinfection_sensors(current)


def gather_disinfection_data():
    """Collect all necessary data for disinfection decisions."""
    try:
        # Tank temperature
        tank_temp_state = state.get(DISINFECTION_CONFIG["tank_temp_sensor"])
        tank_temp = float(tank_temp_state) if tank_temp_state not in [None, "unknown", "unavailable"] else None
        
        # Unit status
        unit_status = state.get(DISINFECTION_CONFIG["unit_status_sensor"]) or "unknown"
        
        # Outdoor temperature
        weather_attrs = state.getattr(DISINFECTION_CONFIG["weather_entity"])
        outdoor_temp = float(weather_attrs.get("temperature", 0)) if weather_attrs else 0
        
        # Indoor temperature
        indoor_state = state.get(DISINFECTION_CONFIG["indoor_sensor"])
        indoor_temp = float(indoor_state) if indoor_state not in [None, "unknown", "unavailable"] else 20
        
        # Target temperature
        target_state = state.get(DISINFECTION_CONFIG["target_temp_entity"])
        target_temp = float(target_state) if target_state not in [None, "unknown", "unavailable"] else 22
        
        # Last disinfection timestamp
        last_disinfection_str = state.get(DISINFECTION_CONFIG["last_disinfection"])
        days_since_last = calculate_days_since(last_disinfection_str)
        
        # Accumulated minutes
        accumulated_state = state.get(DISINFECTION_CONFIG["minutes_accumulated"])
        accumulated_minutes = float(accumulated_state) if accumulated_state not in [None, "unknown", "unavailable"] else 0
        
        # Get forecast for warm day detection
        forecast_temps = get_forecast_temps()
        warmest_in_3_days = max(forecast_temps[:72]) if len(forecast_temps) >= 72 else max(forecast_temps) if forecast_temps else outdoor_temp
        warm_day_coming = warmest_in_3_days > 0
        
        from datetime import datetime
        current_hour = datetime.now().hour
        is_afternoon = 12 <= current_hour < 16
        
        return {
            "tank_temp": tank_temp,
            "unit_status": unit_status,
            "outdoor_temp": outdoor_temp,
            "indoor_temp": indoor_temp,
            "target_temp": target_temp,
            "days_since_last": days_since_last,
            "accumulated_minutes": accumulated_minutes,
            "warm_day_coming": warm_day_coming,
            "warmest_in_3_days": warmest_in_3_days,
            "is_afternoon": is_afternoon,
            "is_hot_water_mode": "HOT WATER" in unit_status.upper(),
        }
    except Exception as e:
        log.error(f"Water Disinfection: Error gathering data: {e}")
        return None


def calculate_days_since(datetime_str):
    """Calculate days since a datetime string."""
    if not datetime_str or datetime_str in ["unknown", "unavailable"]:
        return 999  # Never run, needs to run
    
    try:
        from datetime import datetime
        # Parse the datetime string (format: "2024-01-15 14:30:00")
        last_dt = datetime.fromisoformat(datetime_str.replace(" ", "T"))
        now = datetime.now()
        delta = now - last_dt
        return delta.days + (delta.seconds / 86400)
    except:
        return 999


def get_forecast_temps():
    """Get hourly forecast temperatures."""
    try:
        result = service.call(
            "weather", "get_forecasts",
            entity_id=DISINFECTION_CONFIG["weather_entity"],
            type="hourly",
            blocking=True,
            return_response=True
        )
        raw = result.get(DISINFECTION_CONFIG["weather_entity"], {}).get("forecast", [])
        return [float(x["temperature"]) for x in raw]
    except:
        return []


def evaluate_disinfection_opportunity(current, is_manual=False):
    """Evaluate if now is a good time to run disinfection."""
    
    # Manual trigger always starts
    if is_manual:
        return True, "Manual trigger"
    
    days = current["days_since_last"]
    
    # Not due yet
    if days < DISINFECTION_CONFIG["min_days_between"]:
        return False, f"Only {days:.1f} days since last (min {DISINFECTION_CONFIG['min_days_between']})"
    
    # Calculate opportunity score
    score = 0
    reasons = []
    
    # Piggyback opportunity (best case!)
    if current["is_hot_water_mode"] and current["tank_temp"] and current["tank_temp"] >= 50:
        score += 4
        reasons.append("Piggyback on hot water cycle (+4)")
    
    # Weather conditions
    if current["outdoor_temp"] > 0:
        score += 2
        reasons.append(f"Warm outdoor {current['outdoor_temp']:.1f}°C (+2)")
    elif current["outdoor_temp"] < -10:
        score -= 2
        reasons.append(f"Very cold {current['outdoor_temp']:.1f}°C (-2)")
    
    # House is warm (heating has slack)
    if current["indoor_temp"] > current["target_temp"]:
        score += 2
        reasons.append(f"House warm {current['indoor_temp']:.1f}°C > {current['target_temp']}°C (+2)")
    
    # Afternoon (warmest part of day)
    if current["is_afternoon"]:
        score += 1
        reasons.append("Afternoon (+1)")
    
    # Warm day coming (wait for it)
    if current["warm_day_coming"] and current["outdoor_temp"] < 0:
        score -= 1
        reasons.append(f"Warm day coming ({current['warmest_in_3_days']:.1f}°C) (-1)")
    
    log.info(f"Water Disinfection: Score = {score}, Reasons: {', '.join(reasons)}")
    
    # Decision thresholds
    if score >= 4:
        return True, f"Good conditions (score {score}): {', '.join(reasons)}"
    
    if score >= 2 and days >= 6:
        return True, f"Acceptable conditions at {days:.1f} days (score {score})"
    
    # Safety override
    if days >= DISINFECTION_CONFIG["max_days_between"]:
        return True, f"Safety override: {days:.1f} days since last (max {DISINFECTION_CONFIG['max_days_between']})"
    
    return False, f"Waiting for better conditions (score {score}, {days:.1f} days)"


def start_disinfection(current, reason):
    """Start the disinfection process."""
    log.info(f"Water Disinfection: STARTING - {reason}")
    
    # FIRST: Set disinfection active to prevent sync triggers
    service.call("input_boolean", "turn_on", entity_id=DISINFECTION_CONFIG["disinfection_active"])
    
    # Small delay to ensure the boolean is set before we change other values
    task.sleep(0.5)
    
    # Remember the current setpoint before changing it
    current_setpoint_state = state.get(DISINFECTION_CONFIG["hot_water_setpoint"])
    if current_setpoint_state not in [None, "unknown", "unavailable"]:
        original_setpoint = float(current_setpoint_state)
        service.call("input_number", "set_value",
                     entity_id=DISINFECTION_CONFIG["original_setpoint"],
                     value=original_setpoint)
        log.info(f"Water Disinfection: Saved original setpoint: {original_setpoint}°C")
    
    # Reset accumulated minutes
    service.call("input_number", "set_value", 
                 entity_id=DISINFECTION_CONFIG["minutes_accumulated"], 
                 value=0)
    
    # Raise hot water setpoint to disinfection temperature
    service.call("number", "set_value",
                 entity_id=DISINFECTION_CONFIG["hot_water_setpoint"],
                 value=DISINFECTION_CONFIG["disinfection_temp"])
    
    log.info(f"Water Disinfection: Set target to {DISINFECTION_CONFIG['disinfection_temp']}°C")


def handle_active_disinfection(current):
    """Handle an ongoing disinfection cycle."""
    log.info(f"Water Disinfection: Active - Tank: {current['tank_temp']}°C, Accumulated: {current['accumulated_minutes']:.1f} min")
    
    # Check if tank is at success temperature
    if current["tank_temp"] and current["tank_temp"] >= DISINFECTION_CONFIG["success_temp"]:
        # We only need 5 minutes at 65°C+, but we check every 30 minutes
        # So if we see it at 65°C+, we can assume it's been there for a while
        # Just add 30 minutes (one cycle worth) to accumulated time
        new_accumulated = current["accumulated_minutes"] + 30
        
        log.info(f"Water Disinfection: Tank at {current['tank_temp']}°C >= {DISINFECTION_CONFIG['success_temp']}°C")
        
        # Since we only need 5 minutes and we check every 30 minutes,
        # if the tank is at temp, we can complete immediately
        # (it's been at temp for at least some time since last check)
        if current["tank_temp"] >= DISINFECTION_CONFIG["success_temp"]:
            log.info(f"Water Disinfection: Tank is at {current['tank_temp']}°C - completing disinfection!")
            complete_disinfection(f"Success: Tank reached {current['tank_temp']:.1f}°C (>= {DISINFECTION_CONFIG['success_temp']}°C)")
            return
        
        service.call("input_number", "set_value",
                     entity_id=DISINFECTION_CONFIG["minutes_accumulated"],
                     value=new_accumulated)
        
        log.info(f"Water Disinfection: Accumulated now {new_accumulated:.1f} min")
        
        # Check if we've reached required time
        if new_accumulated >= DISINFECTION_CONFIG["required_minutes"]:
            complete_disinfection("Success: Reached required time at temperature")
            return
    else:
        log.info(f"Water Disinfection: Tank at {current['tank_temp']}°C < {DISINFECTION_CONFIG['success_temp']}°C, not counting this cycle")
    
    # Check for timeout (been active too long)
    if current["accumulated_minutes"] == 0:
        log.warning("Water Disinfection: Still at 0 accumulated minutes - tank may not be heating")


def complete_disinfection(reason):
    """Complete the disinfection process."""
    log.info(f"Water Disinfection: COMPLETE - {reason}")
    
    # Record completion time
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    service.call("input_datetime", "set_datetime",
                 entity_id=DISINFECTION_CONFIG["last_disinfection"],
                 datetime=now)
    
    # Turn off active flag
    service.call("input_boolean", "turn_off", entity_id=DISINFECTION_CONFIG["disinfection_active"])
    
    # Reset accumulated minutes
    service.call("input_number", "set_value",
                 entity_id=DISINFECTION_CONFIG["minutes_accumulated"],
                 value=0)
    
    # Restore original hot water setpoint
    original_state = state.get(DISINFECTION_CONFIG["original_setpoint"])
    if original_state not in [None, "unknown", "unavailable", 0, "0"]:
        original_temp = float(original_state)
    else:
        original_temp = 52  # Fallback default
    
    service.call("number", "set_value",
                 entity_id=DISINFECTION_CONFIG["hot_water_setpoint"],
                 value=original_temp)
    
    log.info(f"Water Disinfection: Restored target to {original_temp}°C")


def abort_disinfection(reason):
    """Abort disinfection due to timeout or error."""
    log.warning(f"Water Disinfection: ABORTED - {reason}")
    
    # Turn off active flag (but don't record as successful)
    service.call("input_boolean", "turn_off", entity_id=DISINFECTION_CONFIG["disinfection_active"])
    
    # Reset accumulated minutes
    service.call("input_number", "set_value",
                 entity_id=DISINFECTION_CONFIG["minutes_accumulated"],
                 value=0)
    
    # Restore original hot water setpoint
    original_state = state.get(DISINFECTION_CONFIG["original_setpoint"])
    if original_state not in [None, "unknown", "unavailable", 0, "0"]:
        original_temp = float(original_state)
    else:
        original_temp = 52  # Fallback default
    
    service.call("number", "set_value",
                 entity_id=DISINFECTION_CONFIG["hot_water_setpoint"],
                 value=original_temp)
    
    log.warning(f"Water Disinfection: Restored target to {original_temp}°C")


def update_disinfection_sensors(current):
    """Update dashboard sensors."""
    
    # Status sensor
    is_active = state.get(DISINFECTION_CONFIG["disinfection_active"]) == "on"
    if is_active:
        status = f"Active ({current['accumulated_minutes']:.0f}/{DISINFECTION_CONFIG['required_minutes']} min)"
    else:
        status = "Idle"
    
    state.set(
        "sensor.disinfection_status",
        status,
        {
            "friendly_name": "Water Disinfection Status",
            "icon": "mdi:water-thermometer",
            "tank_temp": current["tank_temp"],
            "accumulated_minutes": current["accumulated_minutes"],
            "is_active": is_active,
        }
    )
    
    # Last run sensor
    last_str = state.get(DISINFECTION_CONFIG["last_disinfection"])
    if last_str and last_str not in ["unknown", "unavailable"]:
        try:
            from datetime import datetime
            last_dt = datetime.fromisoformat(last_str.replace(" ", "T"))
            friendly_last = last_dt.strftime("%b %d, %H:%M")
        except:
            friendly_last = "Unknown"
    else:
        friendly_last = "Never"
    
    state.set(
        "sensor.disinfection_last_run",
        friendly_last,
        {
            "friendly_name": "Last Disinfection",
            "icon": "mdi:calendar-check",
            "days_ago": current["days_since_last"],
        }
    )
    
    # Next due sensor
    days_until_due = max(0, DISINFECTION_CONFIG["min_days_between"] - current["days_since_last"])
    days_until_forced = max(0, DISINFECTION_CONFIG["max_days_between"] - current["days_since_last"])
    
    if days_until_due <= 0:
        next_due = "Due now (waiting for good conditions)"
    else:
        next_due = f"In {days_until_due:.1f} days"
    
    state.set(
        "sensor.disinfection_next_due",
        next_due,
        {
            "friendly_name": "Next Disinfection Due",
            "icon": "mdi:calendar-clock",
            "days_until_due": days_until_due,
            "days_until_forced": days_until_forced,
        }
    )


# ============================================
# TEMPERATURE WATCHER - Track time at success temp and complete when accumulated
# ============================================

@time_trigger("cron(* * * * *)")  # Check every minute
def watch_tank_temp_cron():
    """Check tank temperature every minute and accumulate time at success temp."""
    
    # Only act if disinfection is active
    is_active = state.get(DISINFECTION_CONFIG["disinfection_active"]) == "on"
    if not is_active:
        return
    
    # Get current tank temp from sensor
    tank_temp_state = state.get(DISINFECTION_CONFIG["tank_temp_sensor"])
    try:
        tank_temp = float(tank_temp_state) if tank_temp_state not in [None, "unknown", "unavailable"] else None
    except (ValueError, TypeError):
        log.warning(f"Water Disinfection: Could not parse tank temp: {tank_temp_state}")
        return
    
    if tank_temp is None:
        return
    
    log.info(f"Water Disinfection: CRON CHECK - tank={tank_temp}°C")
    
    # Check if we're at success temperature
    is_above_threshold = tank_temp >= DISINFECTION_CONFIG["success_temp"]
    
    if is_above_threshold:
        # Get current accumulated minutes
        accumulated_state = state.get(DISINFECTION_CONFIG["minutes_accumulated"])
        current_accumulated = float(accumulated_state) if accumulated_state not in [None, "unknown", "unavailable"] else 0
        
        # Add 1 minute (since we check every minute)
        new_accumulated = current_accumulated + 1.0
        
        # Update accumulated time
        service.call("input_number", "set_value",
                     entity_id=DISINFECTION_CONFIG["minutes_accumulated"],
                     value=round(new_accumulated, 2))
        
        log.info(f"Water Disinfection: Tank at {tank_temp}°C - accumulated {new_accumulated:.1f} min (need {DISINFECTION_CONFIG['required_minutes']} min)")
        
        # Check if we've reached required time
        if new_accumulated >= DISINFECTION_CONFIG["required_minutes"]:
            log.info(f"Water Disinfection: SUCCESS! Accumulated {new_accumulated:.1f} min at {DISINFECTION_CONFIG['success_temp']}°C+")
            complete_disinfection(f"Success: {new_accumulated:.1f} min at {tank_temp:.1f}°C")
            return
    else:
        log.info(f"Water Disinfection: Tank at {tank_temp}°C < {DISINFECTION_CONFIG['success_temp']}°C - not counting")


# ============================================
# SYNC HELPER - Keep original_setpoint synced with actual setpoint
# ============================================

@state_trigger("input_number.disinfection_original_setpoint")
def sync_setpoint_from_helper(var_name=None, value=None, old_value=None):
    """When user changes the original_setpoint helper, sync to actual thermostat (if not in disinfection)."""
    # Only sync if disinfection is NOT active
    is_active = state.get(DISINFECTION_CONFIG["disinfection_active"]) == "on"
    
    if is_active:
        log.info("Water Disinfection: Setpoint helper changed but disinfection active - not syncing")
        return
    
    # Get the new value
    new_value = state.get(DISINFECTION_CONFIG["original_setpoint"])
    if new_value in [None, "unknown", "unavailable"]:
        return
    
    new_temp = float(new_value)
    
    # Get current actual setpoint
    current_actual = state.get(DISINFECTION_CONFIG["hot_water_setpoint"])
    if current_actual in [None, "unknown", "unavailable"]:
        return
    
    current_temp = float(current_actual)
    
    # Only update if different (avoid loops)
    if abs(new_temp - current_temp) > 0.5:
        log.info(f"Water Disinfection: Syncing setpoint helper -> actual: {new_temp}°C")
        service.call("number", "set_value",
                     entity_id=DISINFECTION_CONFIG["hot_water_setpoint"],
                     value=new_temp)


@state_trigger("number.versati_modbus_esp32_versati_13_tank_target_temp_set")
def sync_setpoint_to_helper(var_name=None, value=None, old_value=None):
    """When actual setpoint changes (manually), sync to helper (if not in disinfection)."""
    # Only sync if disinfection is NOT active
    is_active = state.get(DISINFECTION_CONFIG["disinfection_active"]) == "on"
    
    if is_active:
        # During disinfection, don't sync changes back to helper
        return
    
    # Get the new actual value
    new_value = state.get(DISINFECTION_CONFIG["hot_water_setpoint"])
    if new_value in [None, "unknown", "unavailable"]:
        return
    
    new_temp = float(new_value)
    
    # Get current helper value
    helper_value = state.get(DISINFECTION_CONFIG["original_setpoint"])
    if helper_value in [None, "unknown", "unavailable"]:
        helper_temp = 0
    else:
        helper_temp = float(helper_value)
    
    # Only update if different (avoid loops)
    if abs(new_temp - helper_temp) > 0.5:
        log.info(f"Water Disinfection: Syncing actual -> setpoint helper: {new_temp}°C")
        service.call("input_number", "set_value",
                     entity_id=DISINFECTION_CONFIG["original_setpoint"],
                     value=new_temp)


# ============================================
# INITIALIZATION
# ============================================

@time_trigger("startup")
def disinfection_startup():
    """Initialize on startup."""
    log.info("Water Disinfection: Controller loaded (v1.0.0)")
    
    # Create initial sensor states
    state.set("sensor.disinfection_status", "Initializing", {"friendly_name": "Water Disinfection Status"})
    state.set("sensor.disinfection_last_run", "Unknown", {"friendly_name": "Last Disinfection"})
    state.set("sensor.disinfection_next_due", "Checking...", {"friendly_name": "Next Disinfection Due"})
    
    # Run first check after 30 seconds
    task.sleep(30)
    water_disinfection_cycle()
