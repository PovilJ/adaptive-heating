# From the legacy scripts to Adaptive Heating

This guide compares the supplied PyScript snapshots with integration **0.1.0**.
It describes source behavior and the intended cutover; it is not a record of a
completed live migration. See [history and current status](HISTORY.md) for that
distinction and [legacy provenance](../legacy/README.md) for the original files.

The rewrite replaces the space-heating water-setpoint controller. The installer
does not import PyScript configuration, helpers, learned coefficients, dashboards
or history, and does not disable existing scripts. Each house gets its own UI
configuration and new learning. Hot-water disinfection is outside this migration.

## Behavior and feature disposition

| Capability | Supplied legacy heating script | Integration 0.1.0 / disposition |
| --- | --- | --- |
| Installation and house mappings | Copy/edit PyScript source with literal entity IDs and separately created helpers. | **Replaced:** a reusable component release with UI selectors and per-entry settings. No PyScript dependency for space heating. |
| Operating modes | Enable helper gates the whole cycle; the shadow branch is not a normal continuous mode. | **Expanded:** Observe calculates/learns without writes when inputs and operating gates permit; Automatic permits writes; Off disables writes and fitting. Startup/reconfiguration returns to Observe. |
| Target and learning storage | `input_number` helpers for the room target, `k_loss` and `k_gain`. | **Replaced:** integration-owned Room target and stored model. Legacy coefficients are not imported; the model structure and bounds differ. |
| Learning | Night-only window, short in-memory history and heating-on/off inference from water temperatures. | **Reworked:** consecutive eligible ordinary-heating observations, return/supply measurements, fixed three-hour emitter lag and bounded residual-based fitting. Sunny/partly-cloudy intervals are excluded; it is no longer tied to fixed night hours. |
| Prediction | Up to 12 hourly steps, integer water candidates, direct loss/gain response. | **Reworked:** up to 12 forecast hours with 15-minute simulation steps; prediction can adjust the curve by at most 2 °C after sample/error gates pass. Without a usable model, curve and room feedback still work. |
| Cold/sunset/coasting strategy names | `SOLAR_TRICKLE`, `SOLAR_COAST`, `PRE_SUNSET`, `COLD_PREP`, `COAST`, `NIGHT_HOLD`, `MAINTAIN`, `RECOVERY`, fixed time windows and target buffers. | **Not ported as strategies:** forecast correction and room feedback replace the decision structure. Exact timing, buffers and named strategy transitions are not preserved. |
| Passive sunshine | Weather/sun/time heuristics and an added simulated solar gain for the first six forecast hours when sunny. | **Changed:** room feedback responds to measured warming; no assumed solar heat is injected into the prediction. Weather labels still filter learning. |
| PV and batteries | No measured PV/grid/battery surplus policy. | **Added:** optional, default-off preheating after sustained measured surplus, with household/battery priority checks. Passive sunshine and electrical surplus are separate. |
| Trend/momentum/minimum-delta rules | Trend boost, hold reductions while below target, and a cold-weather floor above return temperature. | **Not ported as individual overrides:** curve/feedback, lagged prediction and final command limits determine the output. Equivalent behavior is not guaranteed. |
| Hot water and defrost | `HEAT` check protects only the minimum-delta adjustment; no complete hot-water write/fitting gate or dedicated defrost input. | **Expanded:** writes require the configured space-heating state; optional defrost/inhibit inputs also gate control. Blocked intervals do not fit the model. |
| Missing forecasts | Fixed 30 °C recommendation and target-based predicted minimum. | **Replaced:** curve/room-feedback fallback and an unavailable prediction rather than an invented forecast result. |
| Command cadence and limits | 30-minute trigger and manual button; per-cycle limits compare the original recommendation before some adjustments. | **Reworked:** five-minute evaluation, configurable command interval (default 30 minutes), elapsed-time rise/fall limits on the final output, hardware min/max/step, and holds for manual edits or unconfirmed commands. |
| Diagnostics | Fixed `sensor.heating_*`/forecast/prediction entities; recommendations logged before final adjustments; 20 recent entries. | **Replaced:** entry-owned entities expose proposed, limited, commanded and actual values plus model diagnostics and 20 recent decisions. Old IDs and log schemas are not retained. |
| Distribution and updates | Manually copy updated source. | **Added:** component-only ZIP/checksum, installer and manual GitHub update controls with code backup; restart is explicit. |
| Water disinfection | Separate companion script controls the tank target and maintains its own helpers. | **Outside scope:** source is archived unchanged and excluded from releases. No replacement has been built. |

Implementation references: [engine.py](../custom_components/adaptive_heating/engine.py),
[coordinator.py](../custom_components/adaptive_heating/coordinator.py),
[configuration](../custom_components/adaptive_heating/config_flow.py), and
[design rationale](DESIGN.md). These changes are implemented improvements in
structure and controls; comfort and efficiency improvements need field evidence.

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
| `input_number.heating_target_temp` | Manually set the desired value on the new Room target. There is no ongoing synchronization; the disinfection script still reads the old helper. |
| `input_number.heating_k_loss` / `input_number.heating_k_gain` | Keep old values for reference/rollback; let the new model learn independently. |
| `input_button.run_adaptive_heating` | Replace dashboard/automation calls with the new Evaluate now button. It cannot bypass command intervals or rate limits. |
| `min_water_temp` / `max_water_temp` | Configure and commission the new minimum/maximum for the actual equipment. Legacy 25–40 °C values are historical settings, not universal defaults for a house. |

For dashboards, find the entities under the new Adaptive Heating device. HA
assigns their entity IDs; do not assume fixed replacements for the legacy IDs.

| Old dashboard reference | New reference / gap |
| --- | --- |
| `sensor.heating_strategy` | Status and Decision reason; old strategy labels are not emitted. |
| `sensor.heating_decision_reason` | Decision reason. |
| `sensor.predicted_indoor_temp` | Predicted minimum room temperature; may be unavailable until the model is usable. |
| `sensor.heating_log` and its `entries` attribute | Status entity's `recent_decisions` attribute; update cards/templates for the changed fields. History is not imported and the recent list is in memory. |
| `sensor.forecast_summary` | No direct replacement entity in 0.1.0; use the weather entity or maintain a separate dashboard/template. |

## Cutover checklist for the existing house

1. Preserve the live scripts, helpers, dashboards and current values in a backup;
   this source archive contains only the two Python snapshots. Identify every
   automation or controller writing the space-heating setpoint.
2. Complete isolated-HA checks from [the design](DESIGN.md#tests-before-field-use),
   then follow the [installation instructions](../README.md#first-installation-manual-once-per-house).
   Select local entities, operating-state label and commissioned limits. Keep
   **Observe** selected.
3. If mapping the old enable helper as an inhibit, expect **Paused** while it is
   on; that gate suppresses recommendations as well as commands. After disabling
   the old heating writer, Observe can calculate and learn when space heating is
   confirmed. Observe itself never sends a setpoint. Disabling a controller does
   not turn off the heat pump; it leaves the device's existing setpoint in place.
4. Reconnect dashboards/automations to the new controls. Resolve the shared target
   helper separately: disinfection still uses `input_number.heating_target_temp`,
   and changing the integration's Room target does not update it. Retain the
   disinfection helpers and PyScript runtime if that separate script remains in
   use. Record any future change to it separately.
5. Observe representative heating, hot-water, defrost, forecast/input failure and
   manual-change cases. Compare proposed/limited values and predictions with
   actual readings; record outcomes in [the project history](HISTORY.md).
6. Verify the legacy heating writer and all other competing writers are disabled,
   then select **Automatic** deliberately. The inhibit checks a helper's state;
   it does not stop scripts or detect every other writer. Restart and settings
   reload return to Observe and require this deliberate re-enable step.

To return control to the previous arrangement, first select **Off** on Adaptive
Heating and confirm it has stopped writing, then restore the previously recorded
configuration/setpoint and enable the previous writer. Off does not restore the
old setpoint or undo helper/dashboard changes. Keep the controllers mutually
exclusive. The installer's code backup covers prior integration files, not the
legacy PyScript system or all HA data.

## Installation at another house

Install the same numbered integration archive using the README procedure and
select that house's entities and settings. Repeat Observe/commissioning there.
Do not copy legacy scripts, helper coefficients or another installation's
`.storage` data. The new integration owns its learning and target locally.

This removes source editing and copying for normal configuration and later
manual updates. First installation still requires placing the packaged component
in Home Assistant once; a completed second-house trial has not yet been recorded.
