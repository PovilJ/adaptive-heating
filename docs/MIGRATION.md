# From the legacy scripts to Adaptive Heating

This guide compares the supplied PyScript snapshots with local integration **0.3.1**.
It describes source behavior and the intended cutover. The first-house
installation and dashboard migration are recorded. The October 8 live read showed
Automatic selected but paused during normal compressor idle; field validation
remains pending. See [history and current status](HISTORY.md)
and [legacy provenance](../legacy/README.md) for the evidence and original files.

The rewrite replaces the space-heating water-setpoint controller. The installer
does not import PyScript configuration, helpers, learned coefficients, dashboards
or history, and does not disable existing scripts. Each house gets its own UI
configuration and new learning. Version 0.2.0 adds the optional [disinfection replacement](DISINFECTION.md); it
requires tank mappings and an explicit first run before repeat scheduling.
Version 0.3.0 adds optional [cold-night planning and AC assistance](COLD_NIGHTS.md).
The September 24 installation began with 0.1.0 in Observe. Later live reads are
recorded separately in the history; building the pending correction does not
update the running installation.

## Behavior and feature disposition

| Capability | Supplied legacy heating script | Integration 0.3.0 / disposition |
| --- | --- | --- |
| Installation and house mappings | Copy/edit PyScript source with literal entity IDs and separately created helpers. | **Replaced:** a reusable component release with UI selectors and per-entry settings. No PyScript dependency for either controller. |
| Operating modes | Enable helper gates the whole cycle; the shadow branch is not a normal continuous mode. | **Expanded:** Observe calculates/learns without writes when inputs and operating gates permit; Automatic permits writes; Off disables writes and fitting. Startup/reconfiguration returns to Observe. |
| Target and learning storage | `input_number` helpers for the room target, `k_loss` and `k_gain`. | **Replaced:** integration-owned Room target and stored model. Legacy coefficients are not imported; the model structure and bounds differ. |
| Learning | Night-only window, short in-memory history and heating-on/off inference from water temperatures. | **Reworked:** valid heating and idle observations with explicit activity events, return/supply measurements during floor charging, retained floor heat and a configurable response time (initially three hours). AC operation/settling exclude fitting. A separate night-policy model still calibrates comparable settled low-water dark intervals. Neither model measures COP or unheated-house loss. |
| Prediction | Up to 12 hourly steps, integer water candidates, direct loss/gain response. | **Reworked:** up to 12 forecast hours with 15-minute simulation steps; prediction can adjust the curve by at most 2 °C after sample/error gates pass. In 0.3.1, sustained cold forecasts also prepare the baseline before model calibration, using the floor and water-ramp lead. |
| Cold/sunset/coasting strategy names | `SOLAR_TRICKLE`, `SOLAR_COAST`, `PRE_SUNSET`, `COLD_PREP`, `COAST`, `NIGHT_HOLD`, `MAINTAIN`, `RECOVERY`, fixed time windows and target buffers. | **Reimplemented optionally in 0.3.0:** up to 24-hour weather, sunset/floor lead and empirical cooldown inform preparation, ceiling hold, coasting and early recovery. Targets are capped by comfort limits; water slew still applies. Exact legacy rules, buffers and names are not preserved. Default disabled. |
| Passive sunshine | Weather/sun/time heuristics and an added simulated solar gain for the first six forecast hours when sunny. | **Changed:** no assumed solar heat enters a prediction. Consecutive sunny forecasts can influence preferred morning recovery only with adequate coverage and a safe projection; post-morning waiting also requires actual room warming. Weather labels no longer stop response learning; fitted loss can include unmeasured solar/internal gains. |
| AC assistance | Not present. | **Added in 0.3.0:** optional climate and external room sensor, independent Observe/Automatic/Off, outdoor-temperature limit, bounded owned sessions, manual-change/recovery handling, and sampled kWh budget only when metered. Both main and AC modes must be Automatic to start. |
| PV and batteries | No measured PV/grid/battery surplus policy. | **Added:** optional, default-off preheating after sustained measured surplus, with household/battery priority checks. Passive sunshine and electrical surplus are separate. |
| Trend/momentum/minimum-delta rules | Falling-temperature trend raises the candidate ceiling; an intended hold below target and a cold-weather floor above return temperature are subsequently subject to inconsistent limiting. | **Reworked in 0.3.1:** continuous half-hour room trends support earlier recovery; gradual stalled-recovery assistance and a cold/falling-room hold pass through the same final command limits. The return-water minimum-delta rule is not copied. See the dated review below for reproduced legacy differences. |
| Hot water and defrost | `HEAT` check protects only the minimum-delta adjustment; no complete hot-water write/fitting gate or dedicated defrost input. | **Expanded:** writes require confirmed space heating; an optional mode mapping permits normal idle cycles. Hot water, defrost and inhibits block floor commands while valid room/floor cooling observations continue. |
| Missing forecasts | Fixed 30 °C recommendation and target-based predicted minimum. | **Replaced:** curve/room-feedback fallback and an unavailable prediction rather than an invented forecast result. |
| Command cadence and limits | 30-minute trigger and manual button; per-cycle limits compare the original recommendation before some adjustments. | **Reworked:** five-minute evaluation, configurable command interval (default 30 minutes), elapsed-time rise/fall limits on the final output, hardware min/max/step, and holds for manual edits or unconfirmed commands. |
| Diagnostics | Fixed `sensor.heating_*`/forecast/prediction entities; recommendations logged before final adjustments; 20 recent entries. | **Replaced:** entry-owned entities expose proposed, limited, commanded and actual values, model diagnostics and 20 recent decisions. Additional plan/AC sensors report timing, effective target, cooldown/coverage and session ownership/metering. Old IDs and log schemas are not retained. |
| Distribution and updates | Manually copy updated source. | **Added:** HACS custom-repository installation without manual file handling, or the component-only ZIP/checksum installer and built-in release updater. The built-in installer keeps code backups; HACS manages its own downloads. Restart is explicit. |
| Water disinfection | Separate companion script controls the tank target and maintains its own helpers. | **Rewritten in 0.2.0:** normal tank-target boost, continuous fresh-temperature hold, enforced timeout, acknowledged restoration, persistent recovery/history, and shared room/solar/battery scheduling. Native Gree disinfection is not used. |

Implementation references: [engine.py](../custom_components/adaptive_heating/engine.py),
[coordinator.py](../custom_components/adaptive_heating/coordinator.py),
[configuration](../custom_components/adaptive_heating/config_flow.py), and
[design rationale](DESIGN.md). These changes are implemented improvements in
structure and controls; comfort and efficiency improvements need field evidence.

## Review against the working controller — October 8, 2026

The owner reports that the legacy controller worked well last winter. That is
the comfort baseline to preserve; passing isolated tests does not establish that
the rewrite performs better in the house. This review used the unchanged archive,
the local integration, read-only HA helper values, and an offline harness with
fake state/services. It did not change the running controller or equipment.

The following comparison was made before implementing the additional 0.3.1
forecast/recovery policy. The measured legacy cases remain valid; references to
the new untrained baseline here describe the pre-improvement implementation.

The most consequential differences are:

- **Idle compressor:** the legacy main cycle runs learning, optimization and
  actuation when its enable helper is On even if unit activity is `OFF`. The
  rewrite's activity gate stopped all recommendations in that situation. The
  pending mode-mapping fix distinguishes heating enabled (this house's mode
  value `4`) from compressor activity, and permits normal idle control.
- **Early forecast response:** legacy optimization uses forecast temperatures
  immediately, including its learned helper coefficients. The new basic curve
  only uses forecast simulation after its model acceptance gate; separate
  cold-night planning can still prepare before a qualifying cold event.
  With a 22 °C room/target, 5 °C outside, an afternoon clock, no sunshine and
  constant hourly forecasts, the offline legacy recommendation was 30 °C for
  a 5 °C forecast and 40 °C for a −20 °C forecast. The new *untrained basic
  controller* recommended 32.65 °C in both cases. These are proposals, before
  final command limits, and this comparison does not run the optional planner
  or demonstrate comfort/energy performance.
- **House-specific calibration:** the existing helpers currently read
  `k_loss=0.01567` and `k_gain=0.03318`; their original calibration date is
  unknown. Preserve these for comparison, rather than treating the new defaults
  as an established house baseline. They cannot be copied directly into the
  revised floor-state model, whose coefficients have different meaning.
- **Slow floor response:** legacy learning compares room readings roughly
  2–3 hours apart, with nighttime-only fitting. Strategy timing allows about
  three hours before sunset, but its optimizer applies water heat directly
  every hour; it does not track a concrete-floor state. The pending model retains
  estimated floor heat through compressor pauses and learns heating/idle
  intervals outside AC operation/settling. Its response duration is still a
  configured estimate, initially three hours, rather than automatically learned.
- **Trend and reduction protection:** legacy trends can widen the candidate
  ceiling by 2 °C when the room falls faster than 0.2 °C/hour below target.
  This is not an unconditional 2 °C command boost, and its history stops updating
  during daytime. The intended below-target hold also fails in some paths:
  at room 21.4 °C, target 22 °C, current water target 30 °C and proposal 26 °C,
  the archived actuation function ultimately commands 29 °C. Its later limiter
  overwrites the earlier hold. Conversely, with current/proposed water 30 °C,
  return 35 °C, outdoor −5 °C and activity `HEAT`, its return-water adjustment
  commands 36 °C, bypassing the nominal 2 °C rise limit. Preserve the purpose
  of these controls only through consistent final limits.

Priority work after the idle gate is to validate ordinary daytime/overnight
anticipation, sustained falling-temperature recovery, and commissioned baseline
water recommendations against the old controller. Compare predicted and measured
temperatures over the actual floor response window; a small five-minute residual
alone is insufficient evidence of a good multi-hour prediction. Improvements in
comfort and electrical consumption still require measured operating history.

### External comparison supplied by the owner

[ESPHome Ecodan](https://github.com/gekkekoe/esphome-ecodan-hp) is relevant as a
control-design reference, although its CN105 interface and Mitsubishi-specific
controls do not install on this Versati. Its
[adaptive-control documentation](https://github.com/gekkekoe/esphome-ecodan-hp/blob/main/docs/auto-adaptive.md)
describes return-water-based demand, floor-specific response profiles and staged
assistance when room temperature remains below target. The inspected
[zone calculation](https://github.com/gekkekoe/esphome-ecodan-hp/blob/a64d1b05cd3b53b708df675e010bfa0404f2c410/components/optimizer/auto_adaptive.cpp)
distinguishes enabled heating from an active compressor. Its
[boost implementation](https://github.com/gekkekoe/esphome-ecodan-hp/blob/a64d1b05cd3b53b708df675e010bfa0404f2c410/components/optimizer/smart_boost.cpp)
waits 60 minutes for UFH, increases in stages, and gradually decays when the room
error improves; the documentation's immediate-reset description is less precise.
These are feedback/heuristic controls, not identification of a slab response model.

Its linked [ODIN optimizer guide](https://github.com/gekkekoe/heatpump-optimizer#17-how-the-optimizer-works)
describes a separate predictive layer, including cooldown and passive-solar
learning and comparisons of expected versus actual room temperature. Those are
useful design ideas. The guide's supported installation requires its Asgard/ODIN
hardware, and this review did not inspect or validate the solver implementation.
No external controller code was copied and no new control rule was deployed.

The subsequent local 0.3.1 implementation addresses the forecast/trend gaps with
bounded policies described in [the design](DESIGN.md). Its stalled-recovery
timing uses the configured floor response rather than copying Ecodan's one-hour
wait or its return-water delta values. It retains AC exclusions and a single
final output limiter. Automatic floor-lag identification and field comparison
remain open.

## Mapping the original house

The legacy `CONFIG` dictionary is an inventory for selecting the original house's
entities in the new UI. For another house, select its equivalent entities instead.

| Legacy setting/helper | New setting or action |
| --- | --- |
| `thermostat` | Heating-water setpoint (`output_entity`); this must be the space-heating number, not the tank target. |
| `indoor_sensor` | Room temperature (`indoor_entity`). |
| `weather_entity` | Weather/forecast (`weather_entity`); an optional separate outdoor sensor is also supported. |
| `unit_status_sensor` | Operating state (`operating_entity`); set `heating_state` to the actual space-heating label (`HEAT` in the supplied script). |
| `water_in_sensor` / `water_out_sensor` | Return/supply (`inlet_entity` / `outlet_entity`); both are needed for fitting. |
| `input_boolean.smart_heating_enabled` | Optional external-controller inhibit (`inhibit_entity`) during migration. **On means blocked**, not enable Automatic. Use the new Control mode entity to select a mode. |
| `input_number.heating_target_temp` | Manually set the desired value on the new Room target. The new disinfection scheduler also uses the integration target. Only a still-running legacy script depends on the old helper. |
| `input_number.heating_k_loss` / `input_number.heating_k_gain` | Keep old values for reference/rollback; let the new model learn independently. |
| `input_button.run_adaptive_heating` | Replace dashboard/automation calls with the new Evaluate now button. It cannot bypass command intervals or rate limits. |
| `min_water_temp` / `max_water_temp` | Configure and commission the new minimum/maximum for the actual equipment. Legacy 25–40 °C values are historical settings, not universal defaults for a house. |

For dashboards, find the entities under the new Adaptive Heating device. HA
assigns their entity IDs; do not assume fixed replacements for the legacy IDs.
The [dashboard guide](DASHBOARD.md) records the first-house rewrite and provides
an offline generator for other houses.

| Old dashboard reference | New reference / gap |
| --- | --- |
| `sensor.heating_strategy` | Status and Decision reason; Cold-night plan adds the new planner's phase/reason when enabled. Old strategy labels are not emitted. |
| `sensor.heating_decision_reason` | Decision reason. |
| `sensor.predicted_indoor_temp` | Predicted minimum room temperature; may be unavailable until the model is usable. |
| `sensor.heating_log` and its `entries` attribute | Status entity's `recent_decisions` attribute; update cards/templates for the changed fields. History is not imported and the recent list is in memory. |
| `sensor.forecast_summary` | No identical replacement. Use the weather entity for the forecast; Cold-night plan exposes the horizon and timing used by the new policy. |

## Cutover checklist for the existing house

1. Preserve the live scripts, helpers, dashboards and current values in a backup;
   this source archive contains only the two Python snapshots. Identify every
   automation or controller writing the space-heating setpoint.
2. Complete isolated-HA checks from [the design](DESIGN.md#tests-before-field-use),
   then follow the [installation instructions](../README.md#first-installation-through-hacs)
   (HACS or the alternative package installer).
   Select local entities, operating-state label and commissioned limits. Keep
   **Observe** selected.
3. If mapping the old enable helper as an inhibit, expect **Paused** while it is
   on; that gate suppresses recommendations as well as commands. After disabling
   the old heating writer, Observe can calculate and learn when space heating is
   confirmed. Space-heating Observe never sends a heating setpoint. Tank control
   has its own mode; even in Observe/Off it may restore an interrupted boosted
   target. AC assistance also has its own mode and may restore an interrupted
   owned session to Off. The main mode does not turn off the heat pump.
4. Reconnect dashboards/automations to the new controls. Resolve the shared target
   helper separately if the old disinfection script is still running. With 0.2.0,
   disable that script before configuring the new tank controller; it uses the
   new Room target directly. The original tank helper and manual run button no
   longer control anything once PyScript is removed. Follow the
   [disinfection setup and first-run procedure](DISINFECTION.md).
5. Observe representative heating, hot-water, defrost, forecast/input failure and
   manual-change cases. Compare proposed/limited values and predictions with
   actual readings; record outcomes in [the project history](HISTORY.md).
6. Verify the legacy heating writer and all other competing writers are disabled,
   then select **Automatic** deliberately. The inhibit checks a helper's state;
   it does not stop scripts or detect every other writer. Restart and settings
   reload return to Observe and require this deliberate re-enable step.

## Adding 0.3.0 to an existing integration entry

Existing entity selections, room target and water-model storage are retained when
the mappings are unchanged. New settings receive defaults; cold-night planning
is disabled, and AC begins in Observe. No new `input_*` helpers are needed and no
legacy helper values are automatically copied.

1. Before replacing code, put main heating, tank disinfection and AC assistance
   in Observe where those selectors exist. Wait for any boosted tank target or
   owned AC session to finish restoration. HACS does not run the integration's
   guarded update procedure; follow the [update instructions](../README.md#manual-updates).
2. Install the chosen artifact and restart HA. This local 0.3.0 source must be
   built or made available through the chosen distribution route first; an
   unpublished working-tree change cannot be downloaded through HACS.
3. Open Configure. Start with cold-night planning disabled and confirm ordinary
   heating recommendations. Review the 23 °C preheat ceiling, 20 °C night minimum,
   floor delay, local planning hours, water limits and slew settings before opting in.
4. Optionally select the Sun entity and a protection thermometer outside the main
   room. Return/supply thermometers support actual-water cooldown calibration.
   AC needs its climate entity and an external thermometer in the served room;
   a power meter enables sampled session-kWh limits. Commission the AC outdoor
   limit for the actual model rather than assuming −30 °C operation is useful.
5. Observe several representative nights and inspect planned phases, recovery
   timing and measured temperatures. Enable main Automatic deliberately; enable
   AC Automatic separately when its proposed sessions are understood. Setting
   AC Automatic while main heating stays Observe cannot start assistance.

The planner never raises its authority above the configured water slew limits.
At the defaults, a 10 °C reduction takes at least five hours, and rebuilding that
water target takes at least 2.5 hours before allowing for floor response. Planning
accounts for the recovery ramp, but this may leave little useful coasting time
on a severe night. Observe evidence should guide commissioning; do not assume the
old manual schedule and new bounded commands have identical timing.

See [COLD_NIGHTS.md](COLD_NIGHTS.md) for the full configuration and limits.

To return control to the previous arrangement, first select **Off** on all
Adaptive Heating control modes, let owned tank/AC restoration finish, and confirm
it has stopped writing. Then restore the previously recorded
configuration/setpoint and enable the previous writer. Off does not restore the
old setpoint or undo helper/dashboard changes. Keep the controllers mutually
exclusive. The installer's code backup covers prior integration files, not the
legacy PyScript system or all HA data.

## Installation at another house

Add the same repository in HACS and download the same version using the
[README procedure](../README.md#first-installation-through-hacs), or use the
package installer. Before numbered releases exist, record the `main` commit
shown by HACS for comparisons between houses. Select that house's entities and
settings and repeat Observe/commissioning there.
Do not copy legacy scripts, helper coefficients or another installation's
`.storage` data. The new integration owns its learning and target locally.

HACS handles first installation and later downloads without manually copying
source or handling archives. A completed second-house trial has not yet been
recorded.
