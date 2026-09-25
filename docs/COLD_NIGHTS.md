# Cold-night preparation and optional AC assistance

Version 0.3.0 adds an optional planner for homes that can build warmth before a
cold night, coast within an agreed comfort range, and resume floor heating before
the room becomes too cool. It extends the existing weather curve and room
feedback. The normal actuator limits, command confirmation, manual hold,
operating-state checks, and tank-disinfection coordination still apply.

This is a bounded adaptive comfort policy. It learns an empirical cooling rate
and updates its plan from room measurements and hourly weather. It does not
estimate stored thermal kWh, optimize electricity prices or COP, or establish
that preheating saves electricity. Evaluate the full afternoon, night, and morning,
including both heat pumps when AC is used.

The defaults reflect the owner's experience of approximately 22–23 °C before bed
and 20 °C by morning. Those observations are not imported as training data and do
not establish an unheated-house heat-loss coefficient.

## Planning a night

The planner uses up to 24 hours of timestamped hourly weather. It requires
continuous coverage through the configured morning boundary; missing, duplicated,
gapped, or insufficient weather data falls back to normal heating control.
Two consecutive cold forecast periods must establish a cold night or a
substantial temperature drop. Preparation is timed using the configured
afternoon start, floor lead time, forecast drop, and sunset when a Sun entity is
configured.

| Phase | Behavior |
| --- | --- |
| Disabled / baseline | Use normal heating control. Baseline explains why a cold-night plan is not usable or needed. |
| Scheduled | Preparation has a future start time, or the estimated room reserve already covers the cold window and no extra heating is requested. |
| Prepare | Raise the planned room target by the estimated shortfall, capped at the preheat ceiling, and add a bounded 2 °C water recommendation before existing device and rate limits. AC assistance may be requested. |
| Ceiling hold | Stop extra preparation at the room ceiling and recommend the configured minimum water target. |
| Coast | Recommend the configured minimum water target while the projected comfort margin permits waiting. |
| Recovery | Return to the normal room target early enough for the water-target ramp and configured floor delay. |
| Solar wait | Briefly defer additional floor heat only when actual room warming and consecutive sunny forecasts support it and the conservative projection remains above the minimum. |

The prediction projects room cooling without credit for future sunshine or
stored floor heat. A 0.3 °C margin sits above the configured night minimum. When
the projection threatens this boundary, recovery starts before the predicted
crossing with time for the water-target ramp and floor response. A measured
cooling trend faster than the learned estimate can move recovery earlier.

Consecutive sunny morning forecasts with coverage through the full recovery
lead time can move the preferred recovery time later, but the comfort projection
can always require an earlier restart. Sunshine
through the windows and electrical PV surplus are separate inputs. This version
does not learn window orientation or when sunlight first reaches the rooms;
the morning boundary is configured explicitly.

Lowering the water target does not disconnect the heat pump. The unit retains
its own defrost, hot-water, protection, and compressor behavior. The configured
minimum water target must be suitable for that installation.

The existing water-command slew limits remain authoritative. At the default
2 °C/hour fall, reducing a 35 °C target to 25 °C takes at least five hours. Raising
it again at the default 4 °C/hour takes at least 2.5 hours, in addition to the
floor response delay. Planning includes recovery ramp time but never bypasses
these limits; a severe cold night may allow only a short coast or none at all.
The recovery budget also accounts for device steps and command cadence, using
the lower of the current and planned minimum target as its starting point. For
example, a 25→40 °C recovery with 4 °C/hour rise, 30-minute cadence and 1 °C device
steps budgets 4.5 hours for water recovery plus the default 3 hours for the floor.
This deliberately conservative 7.5-hour lead can trigger early recovery even
when the current room temperature still looks comfortable.

The configured preheat ceiling remains effective during recovery or a forecast
outage while cold-night planning is enabled. An inadequate forecast or an
unusable recovery budget never authorizes a coast.

## Cooling observations

The separate cooldown model starts with a conservative, explicitly uncalibrated
prior. It learns from continuous dark periods with fresh room and outdoor
measurements, actual water near the minimum water setting, and no AC influence,
tank cycle, or other control block. It needs return and supply thermometers,
rather than relying solely on a lowered setpoint. The adapter requires at least
60 minutes at the minimum requested target before accepting samples. Measured
average return/supply water must be within 2 °C above that minimum; the rolling
hour must contain at least seven readings, no gaps over ten minutes, no more than
1 °C water variation, and at most 0.5 °C net change. A model needs at least
12 eligible samples totaling two hours before it reports calibrated.

These measure the house under low-water operation. Residual slab heat and any
remaining heat-pump output can still affect them; they are not a measurement
with every heat source disconnected. An uncertainty allowance remains in
predictions after calibration.

Room trend history resets on missing data or gaps. Learned cooldown parameters
survive restart, while in-progress sample intervals do not. Changing relevant
room, equipment, or AC mappings resets affected learning. Changes to the minimum
water setting or Sun mapping also reset cooldown calibration because they change
the conditions it describes. Existing entries with no new mappings retain their
previous water-model identity.

An optional **Protection room temperature** sensor can represent a room outside
the AC-heated space. If that configured sensor becomes unavailable or approaches
the night minimum, it vetoes coasting and requests normal recovery. One sensor
cannot establish the comfort of every room.

## Optional AC sessions

Configure an AC climate entity and an external thermometer in its room. The
climate entity must support explicit Heat and Off with a single temperature
target and usable temperature limits and step. The controller borrows only a
unit observed to be Off. Existing manual operation is left untouched.

AC has its own **Off / Observe / Automatic** selector. A session can start only
when both main control and AC assistance are in Automatic, the planner requests
preparation, the outdoor temperature meets the configured AC limit, the external
thermometer shows room headroom, and the ordinary control guards pass. Every
restart and reconfiguration begins in Observe.

The controller sets Heat with a bounded target and leaves fan and swing settings
alone. It confirms the reported mode and target, tracks ownership, and returns
its session to Off when preparation no longer needs assistance. A manual mode
or target change surrenders ownership instead of overwriting that change.
The minimum run time applies to ordinary changes in the plan; temperature limits,
lost inputs, a mode change, and duration or energy limits can stop sooner.

There is a maximum session duration and minimum rest between sessions. With an
optional fresh AC electrical-power sensor, successive reports are integrated to
estimate that session's electrical kWh and enforce its budget. A missing or stale
configured meter stops a metered session. With no AC meter, the duration cap still
applies, and session energy remains unknown. This is sampled electrical energy,
not delivered heat or COP; the budget can be crossed between samples and while
a stop command is being confirmed.

Ownership is saved before starting. Interrupted sessions recover toward Off on
restart or unload only while reported AC settings still match the owned session.
Unconfirmed restoration retains the journal and reports that attention is
required. Observe or Off prevents new starts but can still finish recovery of an
owned session. Review a failed or limited session before re-enabling Automatic.
Options cannot change mappings while a session or recovery is active.

Both manual and automatic AC operation exclude the water-heating model and
cooldown model from fitting affected intervals, continuing through the settling
period after AC stops. When cold-night planning is enabled, room feedback does
not immediately reduce floor heat just because local air warmed under AC
influence; the preheat ceiling remains a limit. With planning disabled, ordinary
room feedback remains active while affected model fitting is still excluded.

## Configuration and initial use

Use **Settings → Devices & services → Adaptive Heating → Configure**. No entity
ID is built into the integration. Cold-night planning is disabled by default;
AC assistance defaults to Observe and remains optional.

For the first house, the owner supplied `climate.580d0df87d50` as the AC entity.
Select that entity in Configure and pair it with a thermometer in the served
living/kitchen space. The thermometer may also be the primary room sensor when
its location is suitable; the AC's internal temperature is not the external
feedback input. The exact installed model's useful outdoor range still needs
commissioning. For another house, choose its own entities.

| Setting | Default | Purpose |
| --- | --- | --- |
| Cold-night planning | Off | Opt into preparation and coasting. |
| Preheat ceiling | 23 °C | Highest planned room target. |
| Night minimum | 20 °C | Overnight comfort boundary, with an additional prediction margin. |
| Floor lead time | 3 hours | Allow time for the floor to respond. |
| Preparation hour | 15:00 | Local fallback start; sunset or a forecast drop can move it earlier. |
| Quiet-start hour | 20:00 | Local start of the overnight planning period. |
| Morning hour | 09:00 | Local morning planning boundary. |
| Cold threshold / drop | −15 °C / 3 °C | Require sustained cold conditions or a substantial fall. |
| AC minimum outdoor temperature | −10 °C | Conservative software default; commission from the installed unit's documented operating range. |
| AC maximum session / minimum run / minimum rest | 120 / 20 / 20 minutes | Bound individual sessions and ordinary cycling. |
| AC settling period | 60 minutes | Exclude recent AC influence from learning. |
| AC maximum session electricity | 2 kWh | Enforced only with a configured fresh power meter. |
| AC sample age/gap limit | 600 seconds | Maximum age and interval for room/power telemetry. |
| AC room ceiling | 23 °C | AC also respects the lower of this and the main preheat ceiling. |

Keep the normal room target between the night minimum and preheat ceiling.
Check sensor locations, low-water behavior, temperature limits, AC outdoor limit,
and meters before enabling commands. Use Observe first to inspect proposed
phases and recovery times during representative weather. Enable main control and
AC control independently when their behavior is understood.
No additional `input_*` helpers are required. A Sun entity, another-room protection
thermometer, and AC power meter are optional. With no return/supply thermometers,
the cooldown model retains its uncalibrated prior. With no Sun entity, the local
planning hours provide the fallback schedule.

The **Cold-night plan** sensor includes the reason, effective target, conservative
predicted minimum, cooling rate, calibration state, forecast coverage, preparation
and recovery times, the separate water-ramp/floor/combined recovery lead times,
and protection-room reading. **AC assistance** reports its
reason, requested and actual settings, room reading, session deadline, metering
status, and recovery attention. The optional generated dashboard panel is
described in [DASHBOARD.md](DASHBOARD.md).

This repository change does not deploy code to Home Assistant or enable either
system. Performance and electricity savings require observations in the house
after commissioning.
