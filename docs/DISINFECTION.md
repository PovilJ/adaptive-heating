# Tank disinfection

Implemented in **0.2.0** as an optional part of Adaptive Heating. This replaces
the setpoint-based approach in `legacy/water_disinfection.py`. It does not invoke
Gree's native disinfection function. No additional PyScript, helpers, or YAML are
required, and all entity mappings are selected separately for each house.

## Setup and operation

1. Update the integration through HACS (or the package installer) and restart HA
   to load the new Python code. Keep the old disinfection PyScript disabled.
2. In **Adaptive Heating → Configure**, select the measured **tank temperature**
   sensor and the **normal hot-water tank target** number. The tank target must
   differ from the space-heating water target. Check the device's exact states
   for heating, hot water, and idle/off.
3. Review the cycle settings. The editable defaults below preserve the supplied
   legacy configuration; they are not equipment-independent recommendations.
4. The new **Disinfection mode** starts in **Observe**, independently of the
   space-heating Control mode. Observe shows why a cycle would run or wait.
5. Select Disinfection **Automatic**, then **Run disinfection** for the first
   cycle. Scheduling needs a verified completion from this controller; the old
   helper's timestamp is not imported because the legacy completion path could
   skip the required hold. Manual Run bypasses scheduling preferences, but never
   equipment, sensor, inhibit, or defrost checks.
6. After a verified cycle, Automatic evaluates repeat opportunities within the
   configured window. **Cancel disinfection and restore** requests restoration
   of the saved normal tank target. It also retries a restoration needing attention.

| Setting | Historical default | New meaning |
| --- | --- | --- |
| Boosted tank target | 68 °C | Temporary normal tank setpoint, validated against the device's min/max/step. |
| Hold threshold | 65 °C | Measured tank temperature must stay at or above this value. |
| Hold duration | 5 minutes | Continuous elapsed time between fresh sensor reports; polls do not count as new reports. |
| Scheduling window | 12–16 days | Opportunities begin after day 12; day 16 removes energy/comfort deferrals. |
| Maximum cycle duration | 4 hours | Absolute deadline including heating and holding; never extended by dips or defrost. |
| Maximum sample age/gap | 90 seconds | A stale reading aborts; a gap between otherwise fresh reports resets the hold. |

The device must report tank temperature frequently enough for the chosen sample
limit. The 30-second watcher also listens for temperature changes, so a reported
dip resets the hold even between timer checks. Repeated identical *reports* may
count when HA's `last_reported` advances; repeatedly reading the same report does
not. A single sensor cannot establish conditions between measurements or elsewhere
in the tank/plumbing. “Completed” describes this configured sensor/time criterion
and confirmed setpoint restoration, not a certification of water hygiene.

## Coordination with heating, solar and batteries

Both controllers share a command lock. From the start journal through confirmed
restoration, space-heating writes and model updates are paused, even if the heat
pump still reports HEAT. The model's previous observation and emitter estimate
are cleared across the interruption so tank temperatures do not train the room
model. Heating retains its five-minute cadence; tank monitoring runs separately.

Before the scheduling deadline, the room must be within its configured comfort
band using the integration's **Room target**, not the retired helper. With a
battery configured, its charge level must meet the existing readiness threshold,
charging power must be at most 100 W, and discharge at most 50 W. Missing battery
measurements defer optional starts.

The scheduler prefers sustained measured PV/export surplus using the existing
15-minute qualification and grid/battery checks. Otherwise it may extend an
existing hot-water run with an already warm tank (at least 50 °C), or use a
12:00–16:00 local-time window with a warm tank, outdoor temperature above 0 °C,
and no forecast hour more than 2 °C warmer in the next six hours. An unavailable
forecast removes that forecast preference; it does not invent one. These are
scheduling heuristics, not learned tank-energy or tariff optimization.

At the deadline, comfort, weather, solar and battery preferences no longer defer
the cycle. Availability, device bounds, inhibit and defrost checks still apply;
blocked deadlines remain visible. Once started, loss of solar does not cancel a
cycle. The integration never dispatches the battery or promises solar-only
operation. It raises only the tank target; the heat pump must already be set up
to heat domestic water. It does not power on or change the pump's operating mode.

## Completion and recovery

- The original target and active-cycle journal are saved **before** the boost
  command. The device must acknowledge the target within two minutes.
- A dip below the threshold resets the entire hold. Defrost also resets it and
  pauses counting while leaving the absolute runtime deadline in effect.
- Missing/stale tank data, an inhibit, invalid operating state, timeout, or a
  failed command interrupts the cycle and initiates restoration.
- A manual tank-target change ends the cycle without overwriting that value.
- Completion is recorded only after the hold and observed return to the saved
  target. Restoration retries are bounded (three attempts, two-minute spacing).
  Unresolved restoration blocks space-heating control and raises a persistent
  HA notification; Cancel / restore retries after the device is checked.
- An interrupted/failed cycle requires a new manual run before automatic repeat
  scheduling resumes. There is no retry storm of repeated boosted cycles.
- Restart returns both modes to Observe. An interrupted cycle is restored from
  its journal, never resumed with time credited during downtime. Observe and Off
  prevent new boosts but still permit restoration of an already-owned target.
- Config changes are rejected during an active/recovering cycle. Unload waits
  for restoration to be confirmed; if it returns false, wait and retry the reload.
  The built-in updater likewise refuses file replacement during recovery. HACS
  operates separately: cancel and confirm restoration before updating through it.

The journal survives a crash but cannot operate the physical device while HA or
the network is offline. A raised target can remain in effect until recovery or
manual intervention. The runtime timeout is enforced while HA is running; it is
not a heat-pump firmware timer.

## Dashboard and history

The [dashboard generator](DASHBOARD.md) maps the new disinfection mode, status,
Run and Cancel buttons. Status includes the current reason, continuous hold
progress, original target, timeout, last verified completion, next eligibility,
deadline and latest 20 cycle events. Cycle events and last completion survive
restarts; the separate space-heating evaluation list remains in memory.

The normal hot-water dashboard control now addresses the real tank number.
The old helper synchronizer and run button are not used. Until the new component
is installed and configured, the dashboard explicitly shows that an update or
configuration is needed instead of treating retained helpers as a working cycle.

## Validation and field work

Automated tests exercise continuous holds, dips/gaps/staleness, scheduling,
bounded writes, acknowledgment, timeout, restart restoration, manual overrides,
unit conversion, hardware limits, concurrent mode changes, and heating exclusion.
They never call the real heat pump. See [history](HISTORY.md) for the recorded
test environment and live deployment status.

A monitored real cycle still needs to establish temperature reporting cadence,
actual device response, time to reach the threshold, restoration, and what happens
to room comfort while tank heating runs. No completed legacy-helper timestamp is
treated as evidence of that field validation.
