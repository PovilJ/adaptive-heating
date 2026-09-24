# Heating dashboard

The first-house dashboard was rebuilt on **2026-09-24** for integration 0.1.0.
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
  efficiency sensors, manual water adjustment, retained hot-water controls and
  migration references, and the installed HACS update entity.

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
- The separate disinfection routine still uses its old room-reference helper.
  It is retained and labelled on Equipment, and is not synchronized to the new
  Room target. Its end-to-end operation was not tested by this dashboard change.
