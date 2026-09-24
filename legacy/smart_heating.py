"""
Adaptive Heat Pump Controller (MPC) for Home Assistant
Uses Physics-Based Modeling and Predictive Control to optimize heating.

Features:
1.  **Self-Learning:** Continuously updates heat loss/gain parameters based on actual performance.
2.  **Predictive Control:** Simulates future indoor temperature to find the optimal water temp.
3.  **Solar Awareness:** Detects sunny conditions and adjusts heating accordingly.
4.  **Disturbance Rejection:** Ignores learning when internal heat sources are active.
5.  **Strategic Thermal Management:** Pre-heat before cold, coast during extreme cold.
6.  **Trend Correction:** Reacts when predictions fail (temp dropping unexpectedly).
7.  **Hot Water Mode Detection:** Prevents setpoint jumps when system is making domestic hot water.

Version: 0.3.2 (Hot Water Mode Fix + Fixed Rate Limiting + Floating Point)
"""

log.info("Adaptive Heating: Script file is being loaded by PyScript...")

# ============================================
# CONFIGURATION
# ============================================

CONFIG = {
    # Devices
    "thermostat": "number.versati_modbus_esp32_versati_10_wot_heat_temp_set",
    "indoor_sensor": "sensor.salionas_temperature",
    "weather_entity": "weather.forecast_home",
    "enable_switch": "input_boolean.smart_heating_enabled",
    "water_in_sensor": "sensor.versati_modbus_esp32_versati_127_water_in_pe_temp",
    "water_out_sensor": "sensor.versati_modbus_esp32_versati_125_water_out_pe_temp",
    "unit_status_sensor": "sensor.versati_modbus_esp32_versati_117_unit_status",
    
    # Helpers (You need to create these in HA)
    "k_loss_entity": "input_number.heating_k_loss",
    "k_gain_entity": "input_number.heating_k_gain",
    "target_temp_entity": "input_number.heating_target_temp",
    
    # Limits
    "min_water_temp": 25.0,
    "max_water_temp": 40.0,
    
    # Settings
    "prediction_horizon": 12,
    "max_temp_change": 2.0,
    
    # Learning Settings
    "learning_night_start": 22,  # 22:00 - Start learning window
    "learning_night_end": 6,     # 06:00 - End learning window
    
    # Solar/Weather Settings
    "sunny_conditions": ["sunny", "partlycloudy", "clear"],  # Removed "clear-night" - that's nighttime!
    "solar_day_start": 9,   # 09:00 - sun is high enough to provide heat
    "solar_day_end": 16,    # 16:00 - sun sets early in winter (Lithuania)
}

# ============================================
# STATE STORAGE
# ============================================
history_buffer = []
decision_log = []
MAX_LOG_ENTRIES = 20
last_water_temp = None

# ============================================
# HELPER FUNCTIONS
# ============================================

def is_learning_window():
    """Check if we are in the night learning window (no solar interference)."""
    from datetime import datetime
    hour = datetime.now().hour
    # Night window: 22:00 to 06:00
    return hour >= CONFIG["learning_night_start"] or hour < CONFIG["learning_night_end"]

def is_sunny_now():
    """Check if current weather condition indicates sun (solar gain possible)."""
    try:
        condition = state.get(CONFIG["weather_entity"])
        if condition:
            # Normalize condition string
            normalized = condition.lower().replace("-", "").replace("_", "")
            sunny_normalized = [c.lower().replace("-", "").replace("_", "") for c in CONFIG["sunny_conditions"]]
            return normalized in sunny_normalized
    except Exception as e:
        log.warning(f"Adaptive Heating: Error checking weather condition: {e}")
    return False

def is_solar_hours():
    """Check if sun is up and high enough to provide heat.
    
    Uses sun.sun entity if available, otherwise falls back to fixed hours.
    """
    try:
        # Try to use sun.sun entity (built-in to Home Assistant)
        sun_state = state.get("sun.sun")
        if sun_state and sun_state != "unknown":
            # sun.sun state is "above_horizon" or "below_horizon"
            if sun_state == "below_horizon":
                return False
            
            # Sun is up, but check elevation - need at least 10° for meaningful heat
            sun_attrs = state.getattr("sun.sun")
            if sun_attrs:
                elevation = sun_attrs.get("elevation", 0)
                if elevation < 10:
                    return False  # Sun too low, no real heat
                return True
        
        # Fallback to fixed hours if sun.sun not available
        from datetime import datetime
        hour = datetime.now().hour
        return CONFIG["solar_day_start"] <= hour < CONFIG["solar_day_end"]
    except Exception as e:
        log.warning(f"Adaptive Heating: Error checking sun state: {e}")
        # Fallback to fixed hours
        from datetime import datetime
        hour = datetime.now().hour
        return CONFIG["solar_day_start"] <= hour < CONFIG["solar_day_end"]

def get_sensor_value(entity_id, default=None):
    """Safely get a sensor value, returning default if unavailable.
    
    Rounds to 2 decimal places to avoid floating point precision issues.
    """
    try:
        value = state.get(entity_id)
        if value in [None, "unknown", "unavailable", ""]:
            return default
        # Round to 2 decimal places to eliminate floating point errors
        return round(float(value), 2)
    except (ValueError, TypeError):
        return default


def is_sun_up():
    """Check if sun is above horizon using sun.sun entity."""
    try:
        sun_state = state.get("sun.sun")
        return sun_state == "above_horizon"
    except Exception:
        from datetime import datetime
        hour = datetime.now().hour
        return 7 <= hour < 18


def get_hours_until_sunset():
    """Get hours until sunset from sun.sun entity."""
    try:
        sun_attrs = state.getattr("sun.sun")
        if sun_attrs and "next_setting" in sun_attrs:
            from datetime import datetime
            next_setting_str = sun_attrs["next_setting"]
            # Parse ISO format: 2024-01-29T16:45:00+00:00
            if "+" in next_setting_str:
                next_setting_str = next_setting_str.split("+")[0]
            if "." in next_setting_str:
                next_setting_str = next_setting_str.split(".")[0]
            next_setting = datetime.fromisoformat(next_setting_str)
            now = datetime.utcnow()
            diff = (next_setting - now).total_seconds() / 3600
            return max(0, diff)
    except Exception as e:
        log.warning(f"Adaptive Heating: Error getting sunset time: {e}")
    return 12  # Default if can't determine


def get_strategy(current_data, forecasts):
    """Determine the heating strategy based on conditions.
    
    Strategies:
    - SOLAR_COAST: Sunny, warm enough, let solar help
    - PRE_SUNSET: Sun setting soon, cold night coming - pre-heat
    - COLD_PREP: Cold weather coming - add buffer
    - COAST: At/above target with buffer, can coast
    - NIGHT_HOLD: Too late to pre-heat tonight, just maintain
    - MAINTAIN: Normal operation
    - RECOVERY: Below target, need to recover
    """
    if not forecasts:
        return "MAINTAIN", 0.0, "No forecast data"
    
    indoor = current_data["indoor"]
    outdoor = current_data["outdoor"]
    target = current_data["base_target"]  # Use user's target, not adjusted
    is_sunny = current_data.get("is_sunny", False)
    
    min_forecast_12h = min(forecasts[:12]) if len(forecasts) >= 12 else min(forecasts)
    min_forecast_6h = min(forecasts[:6]) if len(forecasts) >= 6 else min(forecasts)
    
    hours_to_sunset = get_hours_until_sunset()
    sun_up = is_sun_up()
    
    # Get current hour
    from datetime import datetime
    current_hour = datetime.now().hour
    # Late night/evening: from 20:00 onwards or before 06:00
    # After 20:00, it's too late to start pre-heating (takes 3+ hours to see effect)
    is_late_night = current_hour >= 20 or current_hour < 6
    
    # Morning grace period: 06:00-10:00
    # After surviving the night, don't immediately apply buffer
    # Wait until afternoon to start pre-heating for next night
    is_morning = 6 <= current_hour < 10
    
    # Pre-heat window: 14:00-19:00 (afternoon, before evening)
    # This is when we should build buffer for upcoming cold night
    is_preheat_window = 14 <= current_hour < 20
    
    # Calculate forecast trend (is it getting colder or warmer?)
    if len(forecasts) >= 6:
        trend_start = sum(forecasts[:3]) / 3
        trend_end = sum(forecasts[3:6]) / 3
        forecast_trend = trend_end - trend_start  # Negative = getting colder
    else:
        forecast_trend = 0
    
    # Calculate buffer based on forecast severity
    # More conservative values to avoid big temperature jumps
    cold_buffer = 0.0
    if min_forecast_12h <= -25:
        cold_buffer = 0.7
    elif min_forecast_12h <= -20:
        cold_buffer = 0.5
    elif min_forecast_12h <= -15:
        cold_buffer = 0.3
    elif min_forecast_12h <= -10:
        cold_buffer = 0.2
    
    # NIGHT_HOLD: If it's late night (22:00-06:00) and we haven't built buffer,
    # don't try to pre-heat now - it takes ~3h and by then it'll be morning.
    # Just maintain current target without buffer.
    if is_late_night and indoor < target + 0.2:
        # Too late to pre-heat tonight, just maintain base target
        return "NIGHT_HOLD", 0.0, f"Late night - missed pre-heat window, maintaining {target}°C until morning"
    
    # Strategy 1: RECOVERY - Below target (significantly)
    if indoor < target - 0.5:
        return "RECOVERY", 0.0, f"Indoor {indoor:.1f}°C below target {target}°C - recovering"
    
    # Strategy 2a: SOLAR_TRICKLE - Sunny day, above target, before pre-heat time
    # Trigger conditions (any of):
    # a) Morning (before 14:00): indoor >= target AND >3h to sunset
    # b) Midday: indoor >= target + 0.5°C AND >3h to sunset (ends when PRE_SUNSET starts)
    # c) Anytime: indoor >= target + 2.0°C AND >3h to sunset (well above target)
    # Note: Ends 3h before sunset so PRE_SUNSET can kick in (heating takes ~3h to show effect)
    morning_trickle = current_hour < 14 and indoor >= target and hours_to_sunset > 3
    midday_trickle = indoor >= target + 0.5 and hours_to_sunset > 3  # Changed from >2 to >3
    well_above_trickle = indoor >= target + 2.0 and hours_to_sunset > 3  # Changed from >2 to >3
    
    if is_sunny and sun_up and (morning_trickle or midday_trickle or well_above_trickle):
        return "SOLAR_TRICKLE", -99, f"Solar gain - {indoor:.1f}°C (target {target}°C), pre-heat in {hours_to_sunset:.1f}h"
    
    # Strategy 2b: SOLAR_COAST - Sunny day, slightly above target, coast on solar
    # BUT NOT if cold night is coming (need to transition to PRE_SUNSET)
    if is_sunny and sun_up and indoor >= target and min_forecast_12h > -10:  # Changed from 6h to 12h
        return "SOLAR_COAST", -0.3, f"Solar coasting - sun up, {indoor:.1f}°C above target"
    
    # Strategy 3: PRE_SUNSET - Sun setting within 3h AND cold night coming
    # Only triggers during daytime when there's still time to pre-heat
    if sun_up and hours_to_sunset <= 3 and min_forecast_12h < -10 and not is_late_night:
        buffer = cold_buffer + 0.3  # Extra buffer before sunset
        return "PRE_SUNSET", buffer, f"Pre-sunset charge - {hours_to_sunset:.1f}h to sunset, {min_forecast_12h:.0f}°C tonight"
    
    # Strategy 4: COLD_PREP - Cold is coming (within 6h), not yet at coldest
    # Only triggers during daytime/evening when there's time to build buffer
    if outdoor > min_forecast_6h + 3 and min_forecast_12h < -10 and not is_late_night:
        return "COLD_PREP", cold_buffer, f"Preparing for cold - {outdoor:.0f}°C now, {min_forecast_12h:.0f}°C coming"
    
    # Strategy 5: COAST - Have buffer, at coldest point or warming up
    # BUT NOT if cold night coming and we're in pre-heat window (need to build more buffer!)
    if indoor >= target + 0.3 and (forecast_trend >= 0 or outdoor <= min_forecast_6h + 2):
        # Don't coast if cold night coming and we should be pre-heating instead
        if min_forecast_12h < -10 and is_preheat_window:
            pass  # Skip COAST, let MAINTAIN with buffer handle it
        else:
            return "COAST", 0.0, f"Coasting - {indoor:.1f}°C with buffer, {'warming' if forecast_trend >= 0 else 'at coldest'}"
    
    # Default: MAINTAIN (no buffer at night or morning, buffer only during preheat window)
    if is_late_night:
        return "MAINTAIN", 0.0, f"Night mode - maintaining {target}°C"
    elif is_morning:
        # Morning grace period: just survived the night, don't add buffer yet
        return "MAINTAIN", 0.0, f"Morning - maintaining {target}°C (pre-heat starts at 14:00)"
    elif is_preheat_window and min_forecast_12h < -10:
        # Afternoon pre-heat window: apply cold buffer
        return "MAINTAIN", cold_buffer, f"Afternoon pre-heat - building buffer for {min_forecast_12h:.0f}°C tonight"
    else:
        # Midday (10:00-14:00): small buffer only if very cold coming
        if min_forecast_12h <= -20:
            return "MAINTAIN", cold_buffer * 0.5, f"Midday - light buffer for extreme cold {min_forecast_12h:.0f}°C"
        else:
            return "MAINTAIN", 0.0, f"Maintaining target {target}°C"

# ============================================
# CORE LOGIC
# ============================================

@time_trigger("cron(*/30 * * * *)")
@state_trigger("input_button.run_adaptive_heating")
def adaptive_heating_cycle():
    """Main control loop running every 30 minutes."""
    if state.get(CONFIG["enable_switch"]) != "on":
        return

    log.info("=" * 60)
    log.info("Adaptive Heating: Starting cycle...")
    
    # 1. Gather Data
    current = gather_data()
    if not current:
        return

    # 2. Learn (Update Model) - Only during night hours
    update_model(current)
    
    # 3. Predict & Optimize
    optimal_water_temp, plan, predicted_min = optimize_heating(current)
    
    # 4. Act
    execute_decision(optimal_water_temp, plan, predicted_min)


def gather_data():
    """Collect all necessary sensor data."""
    try:
        base_target = round(float(state.get(CONFIG["target_temp_entity"]) or 22.0), 1)
        
        # Get outdoor temp from weather entity attributes
        weather_attrs = state.getattr(CONFIG["weather_entity"])
        outdoor = round(float(weather_attrs.get("temperature", 0)), 1) if weather_attrs else 0.0
        
        from datetime import datetime
        hour = datetime.now().hour
        is_night = hour < 8 or hour >= 22
        
        # Smart Coasting Logic
        should_coast = False
        if is_night:
            forecasts = get_forecast_data()
            if forecasts:
                min_night_temp = min(forecasts[:12]) if forecasts else outdoor
                drop = outdoor - min_night_temp
                if drop > 8.0:
                    should_coast = True
        
        # Target Logic
        if is_night and should_coast:
            target = base_target - 1.0
        else:
            target = base_target
        
        # Get water temps safely
        water_in = get_sensor_value(CONFIG["water_in_sensor"])
        water_out = get_sensor_value(CONFIG["water_out_sensor"])
        indoor = get_sensor_value(CONFIG["indoor_sensor"])
        
        if indoor is None:
            log.error("Adaptive Heating: Indoor sensor unavailable")
            return None
        
        # Check for sunny conditions
        sunny = is_sunny_now() and is_solar_hours()
        
        return {
            "indoor": indoor,
            "outdoor": outdoor,
            "water_in": water_in,
            "water_out": water_out,
            "target": target,
            "base_target": base_target,
            "is_night": is_night,
            "should_coast": should_coast,
            "is_sunny": sunny,
            "k_loss": round(float(state.get(CONFIG["k_loss_entity"]) or 0.007), 5),
            "k_gain": round(float(state.get(CONFIG["k_gain_entity"]) or 0.04), 5),
        }
    except Exception as e:
        log.error(f"Adaptive Heating: Error gathering data: {e}")
        return None


def update_model(current):
    """Learn from the past to update k_loss and k_gain.
    
    Key improvements:
    1. Only learn during night hours (no solar interference)
    2. Reject disturbances (temp rising while heating off = oven/guests)
    3. Slower, more stable learning
    """
    global history_buffer
    
    from datetime import datetime
    now = datetime.now()
    
    # Check if we should learn
    if not is_learning_window():
        log.info("Adaptive Heating: Outside learning window (daytime) - skipping model update")
        return
    
    # Build snapshot
    water_avg = None
    if current["water_in"] is not None and current["water_out"] is not None:
        water_avg = (current["water_in"] + current["water_out"]) / 2
    
    heating_active = False
    if current["water_in"] is not None and current["water_out"] is not None:
        heating_active = (current["water_out"] - current["water_in"]) > 1.0
    
    snapshot = {
        "time": now,
        "indoor": current["indoor"],
        "outdoor": current["outdoor"],
        "water_avg": water_avg,
        "heating_active": heating_active
    }
    
    history_buffer.append(snapshot)
    
    # Keep last 4 hours of history
    history_buffer = [s for s in history_buffer if (now - s["time"]).total_seconds() < 14400]
    
    if len(history_buffer) < 2:
        return

    # Find a comparison point ~2-3 hours ago
    prev = history_buffer[0]
    for s in history_buffer:
        age_hours = (now - s["time"]).total_seconds() / 3600
        if 1.5 <= age_hours <= 3.5:
            prev = s
            break
    
    dt_hours = (now - prev["time"]).total_seconds() / 3600
    if dt_hours < 0.5:
        return
        
    actual_change = current["indoor"] - prev["indoor"]
    rate_per_hour = actual_change / dt_hours
    
    avg_indoor = (current["indoor"] + prev["indoor"]) / 2
    avg_outdoor = (current["outdoor"] + prev["outdoor"]) / 2
    outdoor_delta = avg_indoor - avg_outdoor
    
    # Prevent division by zero
    if abs(outdoor_delta) < 1.0:
        log.info("Adaptive Heating: Outdoor delta too small for learning")
        return
    
    water_indoor_delta = (snapshot["water_avg"] - avg_indoor) if snapshot["water_avg"] else 0
    
    # Case 1: Heating is OFF -> Calibrate Loss
    if not snapshot["heating_active"] and water_indoor_delta < 3.0:
        # DISTURBANCE REJECTION: If temp is RISING while heating is off,
        # something else is heating the house (oven, guests, etc.)
        # Skip learning in this case!
        if rate_per_hour > 0.05:  # Rising more than 0.05°C/h
            log.info(f"Adaptive Heating: DISTURBANCE DETECTED - Temp rising ({rate_per_hour:.3f}°C/h) while heating off. Skipping learning.")
            return
        
        expected_rate = -1 * (current["k_loss"] * outdoor_delta)
        error = rate_per_hour - expected_rate
        
        # Very slow learning (0.5% per cycle)
        calculated_change = -1 * (error * 0.005 / outdoor_delta)
        clamped_change = max(-0.0003, min(0.0003, calculated_change))
        
        new_k_loss = current["k_loss"] + clamped_change
        new_k_loss = max(0.001, min(0.03, new_k_loss))
        
        if abs(new_k_loss - current["k_loss"]) > 0.00005:
            log.info(f"Adaptive Learning: Updating k_loss {current['k_loss']:.5f} -> {new_k_loss:.5f} (Error: {error:.4f}°C/h)")
            service.call("input_number", "set_value", entity_id=CONFIG["k_loss_entity"], value=round(new_k_loss, 5))

    # Case 2: Heating is ON -> Calibrate Gain
    elif snapshot["heating_active"] and snapshot["water_avg"]:
        avg_water = (snapshot["water_avg"] + prev["water_avg"]) / 2 if prev.get("water_avg") else snapshot["water_avg"]
        water_delta = avg_water - avg_indoor
        
        if abs(water_delta) < 1.0:
            log.info("Adaptive Heating: Water delta too small for learning")
            return
        
        loss_component = current["k_loss"] * outdoor_delta
        expected_rate = (current["k_gain"] * water_delta) - loss_component
        
        error = rate_per_hour - expected_rate
        
        # Very slow learning (0.5% per cycle)
        calculated_change = error * 0.005 / water_delta
        clamped_change = max(-0.0005, min(0.0005, calculated_change))
        
        new_k_gain = current["k_gain"] + clamped_change
        new_k_gain = max(0.01, min(0.1, new_k_gain))
        
        if abs(new_k_gain - current["k_gain"]) > 0.00005:
            log.info(f"Adaptive Learning: Updating k_gain {current['k_gain']:.5f} -> {new_k_gain:.5f} (Error: {error:.4f}°C/h)")
            service.call("input_number", "set_value", entity_id=CONFIG["k_gain_entity"], value=round(new_k_gain, 5))


def optimize_heating(current):
    """Simulate future scenarios to find optimal water temp.
    
    Uses strategic thermal management:
    1. SOLAR_COAST: Reduce heating when sun provides heat
    2. PRE_SUNSET: Pre-heat before sunset when cold night coming
    3. COLD_PREP: Build thermal buffer before cold weather
    4. COAST: Use stored heat during inefficient periods
    5. MAINTAIN: Normal operation
    6. RECOVERY: Below target, need to catch up
    """
    forecasts = get_forecast_data()
    if not forecasts:
        return 30.0, "No forecast data", current["target"]
    
    # Get strategy and target buffer
    strategy, target_buffer, strategy_reason = get_strategy(current, forecasts)
    
    # SOLAR_TRICKLE: Special case - just keep system warm (water_in + 1°C)
    # Don't waste energy when sun is heating the house
    # Use ceiling to ensure we're always slightly above water_in
    if strategy == "SOLAR_TRICKLE" and current["water_in"] is not None:
        import math
        trickle_temp = int(math.ceil(current["water_in"] + 1.0))
        trickle_temp = max(CONFIG["min_water_temp"], min(CONFIG["max_water_temp"], trickle_temp))
        log.info(f"Adaptive Heating: SOLAR_TRICKLE - Setting to water_in + 1 (ceil) = {trickle_temp}°C (water_in={current['water_in']:.1f})")
        plan = f"SOLAR_TRICKLE: {trickle_temp}°C (water_in + 1°C) | {strategy_reason}"
        return trickle_temp, plan, current["indoor"]
    
    # Effective target includes strategy buffer
    effective_target = current["base_target"] + target_buffer
    
    log.info(f"Adaptive Heating: Strategy = {strategy} (buffer: {target_buffer:+.1f}°C)")
    log.info(f"Adaptive Heating: Reason = {strategy_reason}")
    log.info(f"Adaptive Heating: Effective target = {effective_target:.1f}°C")
        
    horizon = CONFIG["prediction_horizon"]
    sim_steps = forecasts[:horizon]
    
    # Calculate Current Trend (for reality check)
    current_trend = 0.0
    if len(history_buffer) >= 2:
        last = history_buffer[-1]
        prev = history_buffer[-2]
        dt = (last["time"] - prev["time"]).total_seconds() / 3600
        if dt > 0.1:
            current_trend = (last["indoor"] - prev["indoor"]) / dt
    
    # TREND CORRECTION: If temp dropping when it shouldn't, boost
    trend_correction = 0
    if current_trend < -0.2 and current["indoor"] < effective_target:
        # Temp dropping fast while below target - prediction failing!
        trend_correction = 2
        log.warning(f"Adaptive Heating: TREND CORRECTION - Temp dropping {current_trend:.2f}°C/h while below target. Adding +{trend_correction}°C")
    
    # Candidate Water Temps
    min_w = int(CONFIG["min_water_temp"])
    max_w = int(CONFIG["max_water_temp"])
    candidates = list(range(min_w, max_w + 1))
    
    # Calculate Steady State Water Temp based on WORST case in forecast
    avg_outdoor = sum(sim_steps) / len(sim_steps)
    min_outdoor = min(sim_steps)
    
    # Use the colder of: average or (min + 3°C buffer)
    planning_outdoor = min(avg_outdoor, min_outdoor + 3.0)
    
    if current["k_gain"] > 0:
        steady_state_water = effective_target + (current["k_loss"] / current["k_gain"]) * (effective_target - planning_outdoor)
    else:
        steady_state_water = 30.0
    
    is_recovery = strategy == "RECOVERY"
    
    # Cap the max water temp based on strategy
    if is_recovery:
        max_allowed_water = steady_state_water + 6.0
    elif strategy == "SOLAR_COAST":
        max_allowed_water = steady_state_water + 1.0  # Very conservative
    elif strategy in ["PRE_SUNSET", "COLD_PREP"]:
        max_allowed_water = steady_state_water + 4.0  # Allow higher for pre-heating
    else:
        max_allowed_water = steady_state_water + 3.0
    
    # Apply trend correction
    max_allowed_water += trend_correction
    
    best_temp = max(CONFIG["min_water_temp"], min(CONFIG["max_water_temp"], max_allowed_water))
    best_score = 9999
    best_min_indoor = effective_target
    
    for water_temp in candidates:
        if water_temp > max_allowed_water:
            continue

        # Simulate
        sim_indoor = current["indoor"] + (current_trend * 0.5)
        min_indoor_during_sim = 99
        sum_deviation = 0.0
        
        for hour, f_outdoor in enumerate(sim_steps):
            outdoor_delta = sim_indoor - f_outdoor
            loss = current["k_loss"] * outdoor_delta
            
            water_delta = water_temp - sim_indoor
            gain = current["k_gain"] * water_delta
            
            # Add solar gain estimate if sunny
            if current.get("is_sunny") and hour < 6:
                gain += 0.1
            
            net_change = gain - loss
            sim_indoor += net_change
            
            if sim_indoor < min_indoor_during_sim:
                min_indoor_during_sim = sim_indoor
            
            deviation = abs(sim_indoor - effective_target)
            sum_deviation += deviation
        
        # Hard constraint: Must stay above effective target
        # Strategy determines tolerance
        if strategy in ["COLD_PREP", "PRE_SUNSET", "RECOVERY"]:
            min_allowed = effective_target - 0.1  # Very tight
        elif strategy == "COAST":
            min_allowed = current["base_target"] - 0.3  # Allow some drop
        else:
            min_allowed = effective_target - 0.2
        
        if min_indoor_during_sim < min_allowed:
            continue
        
        # Scoring
        avg_deviation = sum_deviation / len(sim_steps)
        deviation_penalty = avg_deviation * 2.0
        
        final_temp = sim_indoor
        if final_temp > effective_target + 0.5:
            overshoot_penalty = (final_temp - effective_target - 0.5) * 3.0
        else:
            overshoot_penalty = 0
        
        score = water_temp + deviation_penalty + overshoot_penalty
        
        if score < best_score:
            best_score = score
            best_temp = water_temp
            best_min_indoor = min_indoor_during_sim

    final_temp = int(round(best_temp))
    
    # Build plan message
    plan = f"{strategy}: {final_temp}°C → {effective_target:.1f}°C target (predicted min: {best_min_indoor:.1f}°C) | {strategy_reason}"
    
    return final_temp, plan, best_min_indoor


def get_forecast_data():
    """Helper to get hourly forecast temperatures."""
    try:
        result = service.call(
            "weather", "get_forecasts",
            entity_id=CONFIG["weather_entity"],
            type="hourly",
            blocking=True,
            return_response=True
        )
        raw = result.get(CONFIG["weather_entity"], {}).get("forecast", [])
        return [float(x["temperature"]) for x in raw]
    except Exception as e:
        log.warning(f"Adaptive Heating: Error getting forecast: {e}")
        return []


def execute_decision(water_temp, plan, predicted_min):
    """Apply the decision or log it."""
    is_enabled = state.get(CONFIG["enable_switch"]) == "on"
    mode = "active" if is_enabled else "shadow"
    
    log.info(f"Adaptive Heating: Optimal Water Temp = {water_temp}°C")
    log.info(f"Adaptive Heating: Plan = {plan}")
    log.info(f"Adaptive Heating: Predicted Min Indoor = {predicted_min:.1f}°C")
    
    current = gather_data()
    if not current:
        return
    
    update_dashboard_sensors(current, water_temp, plan, mode, predicted_min)
    log_decision(current, water_temp, plan, mode)
    
    if is_enabled:
        try:
            current_setpoint_state = state.get(CONFIG["thermostat"])
            if current_setpoint_state in [None, "unknown", "unavailable"]:
                current_setpoint = water_temp
            else:
                current_setpoint = float(current_setpoint_state)
            
            # Store the ORIGINAL optimal temperature calculated by optimize_heating
            # This is critical for rate limiting to work correctly
            original_water_temp = round(water_temp, 1)
            
            # MOMENTUM MODE: Never reduce water temp when below target
            is_below_target = current["indoor"] < (current["target"] - 0.3)
            if is_below_target and water_temp < current_setpoint:
                log.info(f"Adaptive Heating: MOMENTUM MODE - Keeping {current_setpoint}°C (not reducing while below target)")
                water_temp = round(current_setpoint, 1)
            
            # MINIMUM DELTA PROTECTION: Ensure setpoint is above water_in in cold weather
            # BUT ONLY during space heating mode (not hot water mode!)
            # Only applies when:
            # 1. System is in HEAT mode (not HOT WATER mode)
            # 2. Outdoor temp is below 0°C (need continuous heating), OR
            # 3. A cold drop is coming (need to build thermal reserve)
            # At mild temps (+5°C), we can let the compressor cycle naturally
            if current["water_in"] is not None:
                # Check if system is in heating mode (not hot water)
                unit_status = state.get(CONFIG["unit_status_sensor"])
                is_heating_mode = (unit_status == "HEAT")
                
                if not is_heating_mode:
                    log.info(f"Adaptive Heating: System in {unit_status} mode - skipping MINIMUM DELTA (water_in={current['water_in']:.1f}°C)")
                else:
                    forecasts = get_forecast_data()
                    min_forecast = min(forecasts[:12]) if forecasts else current["outdoor"]
                    cold_drop_coming = (current["outdoor"] - min_forecast) > 3.0
                    
                    need_continuous_heating = current["outdoor"] < 0 or min_forecast < -5 or cold_drop_coming
                    
                    if need_continuous_heating:
                        min_delta = 1.0  # Minimum degrees above water_in
                        min_floor = current["water_in"] + min_delta
                        
                        if water_temp < min_floor:
                            reason = "cold" if current["outdoor"] < 0 else "cold drop coming"
                            log.info(f"Adaptive Heating: MINIMUM DELTA ({reason}) - Raising from {water_temp}°C to {min_floor:.0f}°C (water_in={current['water_in']:.1f}°C)")
                            water_temp = int(round(min_floor))
            
            # ====================================================================
            # FIXED RATE LIMITING - Compare ORIGINAL optimal vs current setpoint
            # ====================================================================
            # This is the KEY FIX: We compare original_water_temp (the pure
            # calculation from optimize_heating) against current_setpoint.
            # NOT the adjusted water_temp which includes momentum/min_delta changes.
            diff = round(original_water_temp - current_setpoint, 2)
            
            # Start with the adjusted temperature (after momentum/min_delta)
            final_temp = round(water_temp, 1)
            
            if diff > 0:
                # Increasing - allow up to 2°C per cycle
                max_increase = 2.0
                if diff > max_increase:
                    final_temp = round(current_setpoint + max_increase, 1)
                    log.info(f"Adaptive Heating: Rate Limited (increase)! Optimal was {original_water_temp}°C, limiting to {final_temp}°C")
            elif diff < 0:
                # Decreasing - only allow 1°C per cycle (slower)
                max_decrease = 1.0
                if abs(diff) > max_decrease:
                    final_temp = round(current_setpoint - max_decrease, 1)
                    log.info(f"Adaptive Heating: Rate Limited (decrease)! Optimal was {original_water_temp}°C, limiting to {final_temp}°C")
            
            # ====================================================================
            # ENFORCE MAXIMUM LIMIT - This was missing before!
            # ====================================================================
            final_temp = min(final_temp, CONFIG["max_water_temp"])
            
            # Hysteresis - only change if difference is significant
            if abs(current_setpoint - final_temp) > 0.5:
                log.info(f"Adaptive Heating: Setting thermostat to {final_temp}°C")
                service.call("number", "set_value", entity_id=CONFIG["thermostat"], value=final_temp)
            else:
                log.info(f"Adaptive Heating: Setpoint stable at {current_setpoint}°C (target {final_temp}°C within hysteresis)")
        except Exception as e:
            log.error(f"Adaptive Heating: Error setting thermostat: {e}")
    else:
        log.info("Adaptive Heating: SHADOW MODE - No action taken.")


def update_dashboard_sensors(current, water_temp, plan, mode, predicted_min=None):
    """Update sensors for Lovelace dashboard compatibility."""
    
    # Extract strategy from plan (format: "STRATEGY: ...")
    if ": " in plan:
        strategy_name = plan.split(":")[0]
    else:
        strategy_name = "UNKNOWN"
            
    if mode != "active":
        strategy_name = f"SHADOW ({strategy_name})"

    # Get forecasts for additional info
    forecasts = get_forecast_data()
    min_forecast = min(forecasts[:12]) if forecasts and len(forecasts) >= 12 else current["outdoor"]
    hours_to_sunset = get_hours_until_sunset()

    state.set(
        "sensor.heating_strategy",
        strategy_name,
        {
            "friendly_name": "Heating Strategy",
            "icon": "mdi:brain",
            "indoor_temp": current["indoor"],
            "outdoor_temp": current["outdoor"],
            "target_temp": current["target"],
            "is_sunny": current.get("is_sunny", False),
        }
    )
    
    state.set(
        "sensor.heating_decision_reason",
        plan[:255],
        {
            "friendly_name": "Heating Decision Reason",
            "icon": "mdi:head-lightbulb",
            "full_reason": plan,
        }
    )
    
    predicted_value = round(predicted_min, 1) if predicted_min and predicted_min < 50 else current["target"]
    state.set(
        "sensor.predicted_indoor_temp",
        predicted_value,
        {
            "friendly_name": "Predicted Indoor Temperature (12h)",
            "unit_of_measurement": "°C",
            "icon": "mdi:home-thermometer",
        }
    )
    
    forecasts = get_forecast_data()
    if forecasts:
        min_f = min(forecasts[:24]) if len(forecasts) >= 24 else min(forecasts)
        max_f = max(forecasts[:24]) if len(forecasts) >= 24 else max(forecasts)
        summary = f"Next 24h: {min_f:.0f}°C to {max_f:.0f}°C"
    else:
        summary = "No forecast data"
        
    state.set(
        "sensor.forecast_summary",
        summary,
        {
            "friendly_name": "Weather Forecast Summary",
            "icon": "mdi:weather-partly-cloudy",
        }
    )


def log_decision(current, water_temp, plan, mode):
    """Log decision to history sensor for dashboard table."""
    global decision_log
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Extract strategy from plan (format: "STRATEGY: ...")
    if ": " in plan:
        strategy_name = plan.split(":")[0]
    else:
        strategy_name = "UNKNOWN"
            
    if mode != "active":
        strategy_name = f"SHADOW ({strategy_name})"

    entry = {
        "timestamp": timestamp,
        "strategy": strategy_name,
        "water_temp": water_temp,
        "indoor_temp": current["indoor"],
        "outdoor_temp": current["outdoor"],
        "reason": plan,
    }
    
    decision_log.insert(0, entry)
    decision_log = decision_log[:MAX_LOG_ENTRIES]
    
    state.set(
        "sensor.heating_log",
        f"{len(decision_log)} entries",
        {
            "friendly_name": "Heating Decision Log",
            "icon": "mdi:clipboard-list",
            "entries": decision_log,
        }
    )


# ============================================
# INITIALIZATION
# ============================================
@time_trigger("startup")
def adaptive_startup():
    log.info("Adaptive Heating: Controller loaded (v0.3.2 - Hot Water Mode Fix + Fixed Rate Limiting + Floating Point)")