# Heating dashboard

The first-house dashboard was rebuilt on **2026-09-24** for integration 0.1.0, then extended for the 0.2.0 disinfection rewrite.
It uses native Home Assistant cards. The already-installed card-mod resource
adds rounded corners and subtle accent backgrounds; control and data cards do
not depend on that styling resource. No additional frontend resource was installed.

## Views

- **Heating** (`/dashboard-heating/0`): measured room temperature against the new
  room target, control mode, reason for the current decision, actual and allowed
  water targets, last command, recent evaluations, room history, hot water,
  electricity and weather.
- **Activity & trends** (`/dashboard-heating/adaptive-heating`): temperature and
  operating history, the latest 20 evaluations, model readiness, and live solar,
  grid and battery readings. Narrow screens use a readable decision list in
  place of the wider table.
- **Equipment** (`/dashboard-heating/equipment`): hardware readings, existing
  efficiency sensors, manual water adjustment and migration references, and the installed HACS update entity.

The overview's Room target and Control mode belong to the new integration.
Evaluate now uses the new integration button. It evaluates without writing in
Observe; in Automatic it can send a command only when the existing guards and
command interval permit it.

## What the history means

The timeline distinguishes **Proposed**, **Allowed**, **Sent**, and **Device**.
The coordinator's `commanded` field retains the previous command even during a
later paused evaluation. Therefore the Sent column/list shows it only when that
row's status is `command_sent`. It does not turn a repeated last-command value
into a new action. Device is the observed setpoint at evaluation time; it is not
proof of immediate acknowledgment of a command in the same row.

The recent-decision list is limited to 20 evaluations and resets when the
controller is restarted/reloaded. Native graphs use Home Assistant's recorder
history. The raw device target and temperature sensors retain their earlier
history; the new integration's entities begin at installation. Legacy strategy
labels, forecasts, and log entries were not imported.

## Reuse in another house

[`scripts/build_dashboard.py`](../scripts/build_dashboard.py) is an offline
generator: it reads an entity mapping and writes dashboard JSON. It never reads
credentials, contacts Home Assistant, or operates equipment.

Start with [`dashboard-mapping.example.json`](dashboard-mapping.example.json),
replace the example IDs with entities from the new installation, and run:

```sh
python3 scripts/build_dashboard.py \
  --mapping /path/to/house-entities.json \
  --output /path/to/heating-dashboard.json
```

Required keys are listed in the generator. Optional mappings add equipment,
solar/battery, daily electricity, hot-water, and migration cards. Use the actual
entity IDs assigned by HA, including any suffixes. The example is a starting
point, not a set of assumed IDs for another house.

Back up the destination dashboard, then apply the generated JSON with the
Lovelace WebSocket API (`lovelace/config/save`) using its `url_path`. Re-read it
with `lovelace/config` and inspect all views. Never write HA `.storage` files
directly. These are standard [tile](https://www.home-assistant.io/dashboards/tile/),
[history graph](https://www.home-assistant.io/dashboards/history-graph/) and
[Markdown](https://www.home-assistant.io/dashboards/markdown/) cards.

## First-house backup and remaining work

The local, Git-ignored directory `.local/ha-dashboard-backups/2026-09-24/` holds
the original dashboard, the house entity mapping, and the verified replacement.
To roll back the UI, send `heating-before-rewrite.json` through
`lovelace/config/save` for `dashboard-heating`. This only restores dashboard
cards; it does not change operating mode or restore any heat-pump setpoint.

The live rewrite was saved and re-read successfully, and its entities/templates
were checked against HA. The overview and detail views were inspected in Chrome
at desktop and phone widths. No heating service was called during verification.

Still pending:

- Check recommendations during representative heating, hot-water and defrost
  operation before an intentional Automatic cutover.
- Correct or verify the existing electrical-power helper's units/formula. Its
  value is inconsistent with the phase meters. The Equipment view flags this;
  neither that helper nor dependent efficiency calculations were changed.
- Install 0.2.0 and configure its tank entities, then verify a real cycle. The
  owner's PyScript was removed; old helper state is historical, not evidence of
  a running scheduler. The corrected dashboard uses the actual tank number,
  removes disconnected legacy controls, and shows Update required while the new
  disinfection status entity is absent. No live tank cycle was run by this change.

## Disinfection panel (0.2.0)

Map `disinfection_status`, `disinfection_mode`, `disinfection_run`, and
`disinfection_cancel` to the integration's new entities. `tank` is the measured
sensor and `tank_target` is the actual normal tank number. The example mapping
includes all six. The retired `tank_helper`, `disinfection_active`,
`last_disinfection`, and `legacy_target` mappings are no longer used.

The overview shows cycle state/reason, target, threshold, continuous hold
progress, last verified completion, next deadline and active timeout. Run and
Cancel are native button actions; Run asks for confirmation in the dashboard.
Mode/buttons are hidden until the new status entity is available. Activity &
trends adds the persisted cycle-event history. Normal tank-target adjustment
writes directly to the heat pump, so a manual edit during a cycle is detected.

The pre-correction dashboard is saved locally as
`heating-before-disinfection.json`; `heating-after-disinfection.json` is the
read-back-verified replacement. Restore either through the Lovelace API. The
original `heating-before-rewrite.json` remains the pre-migration backup.

## Cold-night and AC panel (0.3.0)

The offline generator accepts five additional optional mappings:

| Mapping | Entity | Display |
| --- | --- | --- |
| `planner_status` | Cold-night plan sensor | Phase, reason, planned room target, conservative predicted minimum, cooling rate and calibration, forecast coverage, and available preparation/night/recovery/morning times. |
| `ac_status` | AC assistance sensor | State and reason, commanded target, external room temperature, session deadline, and metering note. |
| `ac_mode` | AC assistance mode select | Independent Off / Observe / Automatic control. |
| `ac_power` | AC electrical power sensor | Current electrical watts and history. |
| `ac_energy` | AC session electricity sensor | Current session kWh and history. |

Any combination can be mapped. With none of these mappings, the existing three
views and sections remain unchanged. Partial mappings omit the corresponding
cards and graphs. Use the entity IDs actually assigned by Home Assistant; the
updated example contains generic starting IDs.

The Heating view adds **Cold-night preparation**. Activity & trends adds
**Preparation & AC history** when status or meter mappings are supplied. Missing
entities or attributes display waiting text or omit a value instead of inventing
zero consumption. Times are displayed in Home Assistant's local time.

The AC energy graph shows sampled consumption for each assistance session. It
is not a lifetime meter or a savings calculation. Compare both systems across the
full afternoon, night, and morning when assessing preparation. See
[COLD_NIGHTS.md](COLD_NIGHTS.md) for control behavior and commissioning.

The new cards use native Markdown, tiles, and history graphs. Existing optional
card-mod decoration is cosmetic. Generating this panel writes a local JSON file;
it does not change the installed dashboard, select Automatic, or operate the AC.
