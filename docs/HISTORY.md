# Project history and status

Last reviewed: **2026-10-08**. Current local source version: **0.3.1, experimental**.
Version 0.3.1 is installed and restarted in the first house. Live checks on Home
Assistant 2026.9.3 confirm Automatic evaluates while heating mode is enabled
(`4.0`) and compressor activity is OFF. The first recommendation was 31.68 °C;
the allowed/current water target remained 25 °C under startup rate limits and
the 30-minute command interval. Tank scheduling Off, AC Observe and the 22 °C
room target were restored. Device acknowledgment and room recovery over hours
remain field-validation work.

Adaptive Heating began as house-specific PyScript code. The rewrite keeps the
goal of adaptive, anticipatory water-temperature control and makes it a standalone
Home Assistant integration: install the same release at each house, select local
entities in the UI, and keep each house's settings and learning in its HA instance.
The space-heating rewrite is implemented; commissioning and field validation
remain open. Version 0.2.0 adds a coordinated tank disinfection controller, now
installed and mapped; a monitored tank cycle remains pending.
Version 0.3.0 adds optional cold-night preparation, empirical cooldown learning,
coasting/recovery and bounded AC sessions. These are local implementation and
test results, not evidence of comfort or electricity savings in the house.

## Timeline

| Date / stage | What happened | Evidence and limits |
| --- | --- | --- |
| Before the repository rewrite; exact dates unknown | House-specific heating and disinfection scripts formed the original system described by the owner. | [Archived source and provenance](../legacy/README.md). Only one snapshot of each script is available; earlier versions and operating results cannot be reconstructed from their headers. |
| 2026-09-24 — initial rewrite | Integration `0.1.0`: UI configuration, Observe/Automatic/Off, empirical prediction, per-installation storage, command guards, diagnostics, installer, manual updater and tests. | Commit [`1e788e3`](https://github.com/PovilJ/adaptive-heating/commit/1e788e33bc3e428fd6d3a4978ba847189d91b4f6). First commit in the available repository history. |
| 2026-09-24 — validation record | Documentation recorded 59 passing tests, including platform imports and the setup form against Home Assistant 2026.7.4; repository access instructions were expanded. | Commit [`d7aedad`](https://github.com/PovilJ/adaptive-heating/commit/d7aedad41c2a38ccb6e891e14d0c9f1017328dbd). These smoke checks do not establish full integration setup/unload or field performance. |
| 2026-09-24 — legacy archive and documentation | Owner-supplied scripts preserved, checksums recorded, behavior differences and migration dependencies documented, and this status record added. Package installation clarified after the Apps repository error. | Commit [`b063640`](https://github.com/PovilJ/adaptive-heating/commit/b0636402ddad06b678b57fc907ce77d12e8291e6), [legacy archive](../legacy/README.md), [migration guide](MIGRATION.md). No controller behavior changed. |
| 2026-09-24 — HACS custom-repository setup | Added HACS metadata and installation-by-URL instructions, fixing the download rejection for commits such as `b063640` without `hacs.json`. HACS handles downloading and placing the component; the package installer remains available. Documented the different update behavior of each route. | Commit `0a65aba`, [hacs.json](../hacs.json), [installation instructions](../README.md#first-installation-through-hacs). Reproduced the rejection and checked the fix using upstream HACS download-eligibility code; live installation had not yet been performed at this stage. |
| 2026-09-24 — first-house installation and dashboard migration | HACS reports installed commit `0a65aba`; the integration entry is loaded on HA 2026.7.4 in Observe. Rebuilt the heating dashboard into Heating, Activity & trends, and Equipment views, using the new controls and decision records. | Live REST/WebSocket reads, dashboard save/read-back, template rendering and Chrome inspection. Old heating enable helper is off; the heat pump reports OFF, so the new controller is paused and has sent no command. [Dashboard record and rollback](DASHBOARD.md). This establishes installation and UI migration, not an Automatic cutover or field-performance validation. |
| 2026-09-24 — setpoint-based disinfection rewrite | Integration 0.2.0 adds optional tank mappings, independent modes, continuous fresh-temperature hold, enforced timeout, command acknowledgment, persisted restoration/history, manual-override handling, and heating/solar/battery scheduling. Corrected dashboard controls after the owner confirmed deleting PyScript. | [Disinfection design and operation](DISINFECTION.md). 81 tests pass with HA 2026.7.4, including an isolated setup/options/reload/unload and simulated tank restoration. Live dashboard save/read-back and template checks verify the UI correction. Integration 0.2.0 is not yet loaded on the real HA; no real tank cycle or temperature command was issued. |
| 2026-09-25 — cold-night preparation and AC assistance | Local integration 0.3.0 adds opt-in preparation/coasting/recovery, up to 24-hour weather coverage, separate low-water cooldown learning, optional room protection, independent AC Observe/Automatic/Off with owned-session recovery and optional sampled electrical budgets, plus offline dashboard cards. | [Cold-night guide](COLD_NIGHTS.md) and the automated checks below. Owner reported successful use of the old PyScript last winter and a usual 22–23 °C to approximately 20 °C overnight drop; these are qualitative observations, not imported model data. No live equipment operation, deployment or publication was performed for 0.3.0. |
| 2026-10-08 — floor-memory and anticipatory recovery, 0.3.1 | Separated heating mode from compressor activity, retained slow floor heat through pauses, added sustained forecast/cooling preparation and bounded recovery assistance, and updated two dashboard cards. Installed all 21 component files, restarted HA, verified options and restored the owner's existing Automatic/Off/Observe modes. | 205 tests pass with simulated devices on HA 2026.7.4. Live 0.3.1 reports loaded on HA 2026.9.3, heating enabled and compressor idle; recommendation 31.68 °C, startup-limited water target 25 °C. Source and dashboard read-back, template rendering and zero integration log entries verified. No hardware setpoint change or room recovery is claimed from this initial evaluation. |

Legacy heating `0.3.2`, disinfection `1.0.0` and integration `0.1.0` are three
separate version histories. The smaller integration number does not indicate a
downgrade of the legacy script. No intervening legacy releases are archived here.

## Where we are

| Area | Status as of this review | What that means |
| --- | --- | --- |
| Source preservation | Committed in `b063640` | Both supplied scripts remain unchanged; their checksums and known gaps are recorded. |
| Reusable integration | Implemented; automated coverage | Entity selection and tuning use HA configuration entries/options. Learned parameters and the room target are stored per entry, outside Git and release archives. |
| Heating controller | Installed 0.3.1; Automatic restored | Curve/forecast/room-trend feedback and bounded learned correction/recovery. Enabled-but-idle evaluation verified; representative equipment operation remains open. See the [comparison](MIGRATION.md#behavior-and-feature-disposition). |
| Cold-night planning | Installed; enabled in the first house, default disabled elsewhere | Adaptive room reserve and conservative low-water cooldown support preparation, coasting and early recovery while existing water rate limits remain authoritative. No COP, tariff or thermal-capacity optimizer. |
| AC assistance | Installed and mapped; Observe restored | Optional external thermometer and climate mapping; starts only with both controllers Automatic, borrows an Off unit, bounds sessions, detects manual edits, persists recovery and excludes AC-influenced learning. A power meter enables sampled session-kWh accounting; otherwise only runtime is bounded. |
| Command handling and diagnostics | Implemented; automated coverage | Operating-state/inhibit gates, final limits and device steps, manual-change holds, Observe on restart, and separate proposed/limited/commanded/actual values. |
| Installation and manual updates | Manual 0.3.1 update/restart verified | Component-only ZIP/checksum validates 21 files. File editor API installation and source read-back, HA restart, options save/read-back and mode restoration are verified. Interrupted hardware-session recovery remains simulated. |
| Installation by repository URL | Earlier HACS installation; latest update installed manually | Before the manual update HACS reported commit `cb33aec` and the integration reported 0.3.0. HACS's repository metadata is separate from the verified running integration version 0.3.1. The HA Apps repository screen remains a different installation mechanism. |
| HA compatibility | Automated checks target HA 2026.7.4 | Isolated setup, platform/entity creation, options/reload and simulated recovery checks establish software compatibility within that environment. Hardware/network behavior still needs field validation. The version-specific results below preserve their original scope. |
| Live use and another house | First-house Automatic restored after update | Ordinary compressor idle no longer blocks evaluation. Device acknowledgment, representative heating observations, comfort/energy comparison and a second-house trial remain pending. |
| Dashboard | Three live views; two cards updated and rendered October 8 | Native cards add plan reasons, targets, forecast/cooldown diagnostics, floor/recovery learning and AC status/metering. Other live layout changes were preserved. |
| Published release | None published as of 2026-09-24 | Checked with the GitHub releases API. HACS can install `main` without a release; the built-in stable-release updater needs published release assets. |
| Domestic-hot-water disinfection | Installed and mapped; scheduling Off restored | Replaces the legacy normal-setpoint boost with continuous hold and recovery. A first monitored cycle and field validation remain pending. |

## Validation evidence

- **Earlier baseline:** commit `d7aedad` records all 59 tests passing with Home
  Assistant 2026.7.4 available. This review preserves that report as historical
  evidence rather than claiming to have repeated it.
- **September 24 documentation review:** `python3 -m unittest discover -s tests -v` on
  Python 3.14.7 discovered 59 tests: **57 passed, 2 skipped** because Home Assistant
  is not installed in this environment. The skipped tests are the two real-HA
  smoke checks in [test_homeassistant.py](../tests/test_homeassistant.py).
- Engine, fake-HA adapter and archive/installer tests cover the rewritten
  integration. They do not validate the archived PyScript code, actual equipment,
  achieved comfort or electricity savings.
- That review also built the release ZIP and ran the installer's validation-only
  mode with `--ha-version 2026.7.4`: all 17 integration files validated, and the
  archive contained neither legacy script. Both legacy checksums matched. No
  files were installed into Home Assistant by these checks.
- **HACS follow-up:** checked the metadata/layout and reproduced the reported
  `b063640` rejection with HACS 2.0.5's upstream `_ensure_download_capabilities`
  method in isolation. The new metadata passes that same check for HA 2026.7.4
  and still rejects a version below HA 2026.7.0. This isolates the missing-file
  cause; it is not a full HACS download or HA setup test.
- **First-house dashboard follow-up:** live HA 2026.7.4 reports the integration
  loaded and HACS commit `0a65aba` installed. Verified 46 mapped entities and
  rendered all 26 dashboard Markdown templates through HA. Saved and re-read
  the dashboard, inspected all three desktop views, and verified phone layout
  and the responsive decision list. Both the live and example entity mappings
  generate valid JSON without unresolved placeholders. Controller code was not
  changed, and no heating service was called. Control remained Observe, with
  the heat pump OFF and the old enable helper off.

- **Disinfection 0.2.0:** Python 3.14.7 with the pinned Home Assistant 2026.7.4
  development dependencies passes **81 tests with no skips**. The isolated HA
  test uses real config entries, selectors, platforms, registries and storage,
  with simulated number services; setup, options save/reload, entity creation,
  tank boost/restoration on unload, and subsequent setup are verified. Pure and
  boundary tests cover hold duration/dips/gaps, stale data, timeout, manual changes,
  restart recovery, bounded restoration retries, units/limits, concurrent mode
  changes, deadline guards and heating exclusion. These do not validate equipment
  performance or water hygiene. Legacy source remains byte-identical.

- **Cold-night/AC 0.3.0, September 25:** the baseline was repeated in the existing
  Python 3.14.7 / Home Assistant 2026.7.4 development environment before editing:
  all 81 prior tests passed. New tests exercise sustained cold forecasts, local
  and midnight timing, preparation limits, conservative coasting and early
  recovery, forecast failure, solar conditions, cooldown learning, AC ownership,
  mode races, temperature/device units, metering gaps, budgets, manual changes,
  and interrupted-session recovery. Dashboard checks cover every combination of
  the five optional mappings and render the new templates through real HA with
  missing and populated data. Final validation with
  `.local/ha-test-venv/bin/python -m unittest discover -s tests -q` passed **169
  tests with no skips** on Python 3.14.7 / Home Assistant 2026.7.4. All device
  actions use simulated services. The 0.3.0 ZIP and adjacent checksum were built;
  installer `--check --ha-version 2026.7.4` validated all **21 integration files**
  against a temporary path without installing anything. Both archived legacy
  SHA-256 checks passed, and the diff whitespace check was clean. The offline
  dashboard generated all three views, with all 32 combinations of its new
  optional mappings covered. No live deployment or publication is implied by
  the local version number.

## Next milestones

### October 8 local correction: compressor cycles and floor memory

Live reads showed Automatic control paused on an OFF activity sensor while the
Versati heating-mode number remained `4.0`; the room was 21.7 °C against a
22 °C target and the water target was 26 °C. OFF described a compressor pause,
not disabled heating. The corrected local build adds a separately configured
heating-mode mapping (numeric `4` / `4.0` match), permits bounded water changes
during confirmed idle heating, and learns both floor charging and cooling.
Activity/defrost events preserve short cycles between five-minute evaluations.
Stored floor heat decays over a configurable response time rather than resetting
when the compressor stops. AC operation and settling exclude fitting; valid
temperature observations continue through ordinary idle, tank and defrost phases.
Sunshine labels no longer exclude response fitting. Predictions include water
recovery before floor warming, and night recovery reserves the configured delay.

The full suite passed **187 tests with no skips** using Python 3.14.7 and Home
Assistant 2026.7.4. Device actions were simulated. The installed coordinator
matched the original source baseline, and live source/options were backed up
locally. At that validation stage no heating command, live configuration
change, installation or restart had been performed. Automatic lag identification and
field validation remain outstanding.

### October 8 legacy and external-controller review

Reviewed the archived controller against the owner's report of good operation
last winter. An offline harness with fake HA state/services confirmed that the
legacy cycle continues with compressor activity OFF, reproduced inconsistent
momentum/final-rate-limit paths, and compared early forecast recommendations
against the new untrained basic curve. Read-only HA checks found the existing
loss/gain helpers at 0.01567/0.03318; their calibration date is unknown. Both
archived checksums still match. The comparison does not establish field comfort
or electricity savings, and no runtime code was changed for this review.

The owner supplied ESPHome Ecodan as a reference. Reviewed its adaptive-control
documentation and relevant source at commit
`a64d1b05cd3b53b708df675e010bfa0404f2c410`, plus its link to the separate ODIN
optimizer guide. Useful ideas include enabled-mode/activity separation,
floor-specific feedback timing, gradual assistance for a stalled recovery,
cooldown learning and expected-versus-measured temperature comparisons. No
external implementation was copied or installed. Detailed findings and
limitations are in the [dated migration review](MIGRATION.md#review-against-the-working-controller--october-8-2026).

### October 8 anticipatory recovery improvement — 0.3.1

Implemented sustained cold-forecast preparation before model calibration,
including the configured floor response and the time to raise water. Added a
30–60 minute continuous room-temperature trend, bounded early cooling
compensation, and gradual assistance after below-target recovery has stalled
for the floor-response allowance. A cold falling room cannot lower ordinary
floor heat; intentional night coasting/ceiling reductions remain separate.
All final actuator, cadence, device-step and operating/ownership checks remain
authoritative. AC operation and settling clear recovery feedback and exclude
model fitting. Floor response is still configured, not automatically learned.

The full Python 3.14.7 / HA 2026.7.4 suite passes **205 tests with no skips**.
New cases exercise day-one/distant/spurious cold forecasts, water-ramp lead,
cooling before target, recovery timing/decay/gaps/AC, command-limit preservation,
and real-HA rendering of dashboard floor/recovery diagnostics. These are
simulated-device results, not evidence of improved field comfort or savings.
Version metadata identifies the new build as 0.3.1.

### October 8 authorized live installation and restart

After the owner explicitly requested pushing Git, updating Adaptive Heating and
restarting, installed the complete validated artifact through the File editor
API. All 21 files matched the previous repository baseline before the update
and the new artifact after writing. Updated only the decision and floor/recovery
dashboard cards through the Lovelace API; read-back and live template rendering
passed. Backups, previous options and latest control modes are kept in the
ignored `.local/deployment-0.3.1/` directory. The installer was adapted to File
editor's `text/json` response after an initial write/rollback; the original
source was verified again before the completed installation.

Restarted HA and verified integration 0.3.1 loaded on **HA 2026.9.3**. The
automated suite targets 2026.7.4; the newer live version has runtime checks,
not a repeated full automated suite. Saved/read-back the Versati heating mode
mapping (`4`, matching `4.0`), idle state OFF and configured three-hour response.
Restored the latest pre-update modes: main Automatic, tank Off and AC Observe,
with the existing 22 °C room target. The first Automatic evaluation reported
heating enabled, compressor inactive, status maintaining, recommendation
31.68 °C and allowed/actual target 25 °C under startup slew limits. No integration
log entries were present. AC startup/settling exclusion is active and accepted
learning hours are initially zero. Device command acknowledgment, learned
response and room recovery are not established by this initial evaluation.


### October 8 compact dashboard and live power correction

Redesigned all three dashboard views as **Now**, **Trends** and **System**, keeping
paths `0`, `adaptive-heating` and `equipment`. The owner emphasized the original
compact cards, controls inside their readings, icons and meaningful colors.
The first-house presentation groups measured room temperature with target
buttons, current activity with floor-control mode, and tank/AC information with
their controls. It reuses existing Mushroom and Stack In Card resources; native
cards remain the offline generator's default for other installations. No
frontend resource was installed or reordered. The activity badge remains at the
top right of Room comfort.

Now has paired live power/water readings and a brief conditional next plan;
history, learning and full session explanations are in Trends. System retains
quiet mode, manual water adjustment, disinfection Run/Cancel with the Run
confirmation, Evaluate now, integration settings and HACS updates. The phone
shows five recent decision explanations; the wider table retains up to 20 and
spans the available view width. Coming next reads the live device target rather
than the coordinator's pre-command snapshot. Observe and unavailable-controller
wording do not imply a pending automatic action.

Corrected the existing total-power template, which summed native phase kW but
labeled the result W: the sum is now multiplied by 1000. Adjusted its COP
consumer to divide W by 1000, preserving that calculation's scale. Configuration
validation and template reload passed; a live check showed 1430 W against
1.430 kW across the phase meters. Earlier mis-scaled power/calculated-energy
history was preserved. Now uses the corrected native total-power entity, while
Trends uses native combined/daily/monthly energy counters. Existing COP remains
a sensor estimate, not newly validated physical efficiency.

Seven dashboard tests pass on Python 3.14.7 / HA 2026.7.4, including the live-
target-versus-pre-command regression in both presentations. All 128 combinations
of seven optional compact mappings rendered with missing data without inventing
measurements. The final dashboard's 48 entity references and 29 templates were
checked against live HA; save/read-back matched. Phone and desktop layouts were
inspected in Chrome. Main Automatic, tank Off, AC Observe and the owner's latest
22.5 °C room target remained unchanged. Dashboard verification did not operate
equipment, reload the integration or restart HA.

Original and immediately preceding dashboard configurations are preserved in
ignored backups and exported as YAML. The final dashboard/mapping, live renders,
control snapshots and complete pre-redesign configuration are kept in
`.local/ha-dashboard-backups/<timestamp>-redesign/`; power-source backups are in
a separate `<timestamp>-live-power/` directory. This establishes compact
presentation and current power units, not field comfort or energy savings.

These are pending work, not promised release dates or completed acceptance checks.

1. **Deployment validation:** isolated setup/options/reload/unload and the live
   0.3.1 update/restart/options/mode restoration now pass. Continue checking
   command acknowledgment, representative input freshness/state labels and
   interrupted hardware-session recovery. HACS metadata synchronization remains
   separate from this verified manual installation.
2. **First-house Observe trial:** follow the [migration guide](MIGRATION.md),
   resolve old-writer and shared-helper dependencies, observe ordinary heating,
   hot water, defrost, missing inputs and manual changes; compare predictions
   with later measurements.
3. **Controlled first-house cutover:** commission curve/limits, disable the old
   heating writer, explicitly enable Automatic, and record comfort and measured
   electricity against a comparable baseline. Preserve a rollback path.
   Commission cold-night limits, low-water behavior, the AC outdoor limit and
   external room/protection sensors separately; inspect Observe recommendations
   before enabling preparation or AC Automatic.
4. **Second-house installation:** install the same numbered artifact and select
   that house's entities without source edits or copied learned state. Record
   equipment differences and any setup gaps.
5. **Release readiness:** close the relevant [acceptance checks](DESIGN.md#tests-before-field-use),
   select a repository license, and publish tested assets with release notes
   using the [release procedure](RELEASING.md).

Before enabling tank scheduling, monitor an explicitly requested first cycle
using the installed controller and mappings. The legacy completion timestamp
is not imported.

Later candidates are automatic lag identification, fuller multi-room planning,
rolling prediction-error evaluation, learned window-gain timing, measured
electricity modeling, tariff/export economics and direct signed-power setup.
Version 0.3.0 reintroduces the intention of anticipatory cold-night preparation
through a new bounded policy; it does not copy the legacy strategy rules.
Disinfection, cold-night operation and AC assistance still need field validation.

## Keeping this record useful

For each meaningful implementation, validation, deployment or release milestone,
append a dated timeline entry with the commit/tag or test evidence and update the
status and pending work above. Distinguish implemented, automatically tested,
tested in isolated HA and observed on real equipment. Record unknown dates as
unknown and leave historical validation results attached to their original
version/environment. Update the migration comparison when behavior changes.

### October 8 tabbed dashboard

Replaced Now/Trends/System/Original with five icon tabs — Home, Trends, Plan,
Hot water and System — built from Mushroom cards and apexcharts-card in the
style of the original dashboard. The generator's native fallback, the
`presentation.compact_mushroom` switch and the `comparison_view` copy were
removed. Six dashboard tests pass; all 89 templates rendered against live HA
2026.9.3 and the saved dashboard was read back. The layout was not inspected in
a browser. See [DASHBOARD.md](DASHBOARD.md).

### October 8 learning returned to the original pace — 0.3.2

Response learning used five-minute steps, during which the room moves less than
the sensor's 0.1 °C resolution, and declared itself usable after two hours.
Restored the PyScript's rules inside the lag model: 2–3 hour night windows, a
fit every 30 minutes, loss fitted with the floor off and gain with it heating,
0.5 % steps capped per fit. Stored revision-2 counts are discarded and the
coefficients start once from the PyScript helpers (0.01567 / 0.03318 in the
first house). Night-cooldown samples now span an hour and calibration needs six
hours. 209 tests pass on HA 2026.7.4. No field result is claimed.

### October 10 predictive planner — 0.4.0

After two days of Automatic on 0.3.2 the room sat above its 22.5 °C target 88 %
of the time once reached, with water about 2 °C hotter than the archived
PyScript requests for the same readings. The owner asked for a controller better
than both. Version 0.4.0 adds a model-predictive planner: a three-store house
model fitted to January–May statistics and the October cold start, a 36-hour
plan over forecast temperature, cloud and sun position, a comfort band with an
optional night floor, and a guard for model error. Evaluation and command now
share the 30-minute control interval, as in the PyScript, and a command stamped
just after its cycle no longer loses a whole step at the next one. Design, fit,
replay results and the follow-up checklist are in [PREDICTIVE.md](PREDICTIVE.md).

219 tests pass on Python 3.14.7 / HA 2026.7.4, including nine planner tests and
one adapter test of the predictive path and its fallback. Replays against the
fitted house rank the planner below the PyScript and the 0.3.2 curve on
electricity in mild, spring and −22 °C weather; this is simulation, not a
measured saving. An unpublished 0.3.3 (interval and limiter fix only) was
superseded before installation. Live installation status is recorded below.

### October 10 authorized 0.4.0 installation

The owner asked to push, update the installed package and restart for a live
trial. Commit `4c56599` was pushed to `main`. HACS still reported `cb33aec` as
both installed and latest after a refresh and its `update.install` returned
HTTP 500, so the eight changed component files were written through the File
editor API and read back identical to the repository. HA 2026.9.3 restarted
(the proxy answered 502 to the restart call itself); the integration reports
0.4.0. Options saved and read back: predictive on, curve offset 0.5, stale
limit 360 min, rise 6 / fall 10 °C per hour, night floor 21.5 °C, night 22:00,
warm by 07:00. Modes restored to main Automatic, tank Observe, AC Off; room
target unchanged at 22.5 °C. HACS's own version record remains stale.

For the first hour after any restart the AC settling window keeps the planner
on the fallback curve; the first evaluation proposed minimum water for a
23.7 °C room. Backups are in the ignored `.local/deployment-0.4.0/`; the
installer is `.local/install_040.py` and `.local/check_040.py` reads the live
plan. Field results are pending the owner's trial.
