# Heating dashboard

The first-house dashboard was rebuilt on **2026-09-24**, then refreshed live on
**2026-09-25** for integration 0.3.0 with cold-night planning and AC assistance.
The decision and floor/recovery cards were updated live on **2026-10-08** with
integration 0.3.1; the other live layout and controls were preserved.
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
  efficiency sensors, manual water adjustment, settings, and the installed HACS update entity.

The overview's Room target and Control mode belong to the new integration.
Evaluate now uses the new integration button. It evaluates without writing in
Observe; in Automatic it can send a command only when the existing guards and
command interval permit it.

The October 8 correction distinguishes heating mode from compressor
activity. An OFF activity reading can be a normal compressor pause while heating
mode remains enabled. A separate integration mode mapping permits calculations
and bounded commands during that pause; it is not a heat-pump power control.
Valid heating/cooling observations retain the estimated floor heat over hours.
The status entity exposes floor-response duration, estimated floor heat state and
accepted heating/cooling hours. The previous waiting message now directs users
to check mode mapping instead of asserting that the entire heat pump is off.
The correction is installed and verified live: heating register `4.0` with
compressor activity OFF now permits Automatic evaluation instead of pausing.

The 0.3.1 dashboard also identifies confirmed heating enablement separately from
compressor activity. **Floor response & recovery** in Activity & trends reports
the configured response allowance, measured half-hour room trend, gradual
recovery assistance, accepted heating/cooling hours and an active AC learning
exclusion. Missing attributes produce waiting text. Forecast preparation and
room feedback operate before a model prediction becomes available. These
template branches pass isolated real-HA rendering checks. The two updated live
cards were saved, re-read and rendered through HA after restart. At the first
evaluation the recommendation was 31.68 °C and the allowed/current water target
was 25 °C because startup rate limits had not yet allowed a device step. This
verifies the recommendation and UI, not a completed hardware command or room
recovery. The three-hour floor response remains a configured estimate.

The October 8 backup is in the ignored `.local/deployment-0.3.1/` directory:
`dashboard-before.json` restores the previous UI through `lovelace/config/save`;
`dashboard-proposed.json` is the verified replacement. Source and options
backups are separate and must be restored together for a controller rollback.

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
solar/battery, daily electricity, hot-water, and AC cards. Use the actual
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

- Check recommendations and device acknowledgment during representative
  heating, hot-water and defrost operation. Automatic was already selected
  before the October 8 installation and was explicitly restored afterward.
- Correct or verify the existing electrical-power helper's units/formula. Its
  value is inconsistent with the phase meters. The Equipment view flags this;
  neither that helper nor dependent efficiency calculations were changed.
- Tank entities are configured in the live 0.3.1 installation, with scheduling
  Off. Verify an explicitly requested first real cycle before enabling it.
  No tank cycle was run by these dashboard updates.

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

### First-house live refresh, September 25

Applied the cold-night and AC panels to the existing three views. Removed the
retired-controller card, migration notes, old-model explanations and obsolete
upgrade text. Corrected disinfection mappings to the actual `boiler_room_`
entity IDs assigned by Home Assistant. AC metering cards are omitted because
this installation has no AC power meter configured; the status explains the
runtime-only limit.

The supplied dashboard matched the live configuration before editing. All 47
referenced entities were verified, all 27 Markdown templates rendered through
Home Assistant, and the saved dashboard matched its read-back. All five dashboard
tests passed. The three views were inspected in Chrome. Control modes and
equipment settings were not changed.

The previous dashboard, actual entity mapping, proposed/saved dashboard and
rendered templates are kept in the Git-ignored directory
`.local/ha-dashboard-backups/2026-09-25T074020Z-cold-night/`.
To undo only this dashboard change, send its `dashboard-before.json` through
`lovelace/config/save` for `dashboard-heating`.
