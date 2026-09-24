# Legacy source archive

These are the original, house-specific PyScript controllers supplied by the
owner as the background to the Adaptive Heating rewrite. They are preserved
unchanged so future work can trace decisions back to the implementation it
replaced. This directory is historical reference, not an installation package.

| Snapshot | Version declared in the file | Relationship to the new integration |
| --- | --- | --- |
| [smart_heating.py](smart_heating.py) | `0.3.2` — Hot Water Mode Fix + Fixed Rate Limiting + Floating Point | Predecessor of the space-heating controller in `custom_components/adaptive_heating/`. The rewrite changes the model and several behaviors; it is not a direct port. |
| [water_disinfection.py](water_disinfection.py) | `1.0.0` | Companion domestic-hot-water controller. Its setpoint-based approach is rewritten in integration **0.2.0**; this original PyScript is not installed. See the [replacement](../docs/DISINFECTION.md). |

The files were supplied in this working tree on **2026-09-24**. Their original
creation dates, deployment dates, earlier revisions and author history were not
supplied. Version labels come from the source headers; example dates in comments
are not evidence of when the scripts were written. The integration starts a
separate version series at `0.1.0`.

See the [project timeline and current status](../docs/HISTORY.md) and the
[behavior comparison and migration guide](../docs/MIGRATION.md).

## Original operating environment

Both files depend on PyScript-provided `state`, `service`, `log`, `task` and
trigger decorators inside Home Assistant. They are not standalone Python programs.
They contain the original Versati/Modbus entity IDs, room/weather entities and HA
helper names. Some trigger decorators also contain literal entity IDs, so editing
only the configuration dictionaries would not fully adapt them to another house.

- **Space heating:** a scheduled 30-minute cycle and a manual button, helper-backed
  room target and loss/gain coefficients, forecast simulation, night learning,
  sun/time-based strategies, water-setpoint writes and dashboard sensors.
- **Hot water:** a 30-minute opportunity check, a one-minute temperature watcher,
  manual triggering, helper-backed state and two-way synchronization between the
  normal tank-setpoint helper and device setpoint.
- **Shared dependency:** both scripts read `input_number.heating_target_temp`.
  Replacing space heating does not remove the disinfection script's dependency on
  that helper. Its target will not follow the new integration automatically.

Only these two Python files were supplied. Helper definitions, Lovelace dashboards,
automations, PyScript configuration, learned helper values and operating history
are not included. This archive cannot reconstruct the full old installation.

## Source caveats retained with the snapshots

These observations describe the archived code, not a validation of its operation.
The integration's tests do not execute these scripts.

- The heating cycle returns immediately when its enable helper is off. Although
  `execute_decision()` contains a shadow branch, disabling the script is not a
  continuously evaluating Observe mode.
- The legacy hot-water-mode check only skips the heating script's minimum-delta
  adjustment. It does not block all space-heating setpoint writes or model fitting
  during hot water. The new coordinator has a separate operating-state gate.
- Legacy dashboard/log values are recorded before final command adjustments;
  they are not necessarily the values sent to the device.
- The disinfection header says it forces a run after seven days, but the supplied
  configuration uses a **12-day minimum and 16-day maximum**. These are recorded
  historical values, not installation recommendations.
- The disinfection minute watcher accumulates threshold samples, but
  `handle_active_disinfection()` can also complete on a single qualifying reading
  in the 30-minute cycle. Its configured `required_minutes` is therefore not
  enforced by every completion path.
- `max_runtime_hours` is configured and `abort_disinfection()` exists, but the
  supplied script does not enforce that timeout or call the abort function.

The 0.2.0 rewrite corrects these completion/timeout paths and adds restart recovery.
Its [requirements and validation](../docs/DISINFECTION.md) are separate from this
archive; field validation remains pending.

## Preserving provenance

[SHA256SUMS](SHA256SUMS) records the bytes supplied on 2026-09-24. From this
directory, verify them with:

```sh
shasum -a 256 -c SHA256SUMS
```

Keep these snapshots unchanged, including their old comments and entity IDs.
Document corrections here or implement them in maintained code. If another
historical revision is recovered, preserve it separately with its source,
declared version, known date and checksum; add it to the project timeline.

The [release builder](../scripts/build_release.py) packages only
`custom_components/adaptive_heating/`, so neither legacy script enters an
installable release. Installing the new integration does not remove or disable
PyScript files already present in a house.
