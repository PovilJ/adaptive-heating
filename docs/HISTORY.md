# Project history and status

Last reviewed: **2026-09-24**. Current integration version: **0.1.0, experimental**.

Adaptive Heating began as house-specific PyScript code. The rewrite keeps the
goal of adaptive, anticipatory water-temperature control and makes it a standalone
Home Assistant integration: install the same release at each house, select local
entities in the UI, and keep each house's settings and learning in its HA instance.
The space-heating rewrite is implemented; commissioning and field validation
remain open. The companion hot-water disinfection controller remains separate.

## Timeline

| Date / stage | What happened | Evidence and limits |
| --- | --- | --- |
| Before the repository rewrite; exact dates unknown | House-specific heating and disinfection scripts formed the original system described by the owner. | [Archived source and provenance](../legacy/README.md). Only one snapshot of each script is available; earlier versions and operating results cannot be reconstructed from their headers. |
| 2026-09-24 — initial rewrite | Integration `0.1.0`: UI configuration, Observe/Automatic/Off, empirical prediction, per-installation storage, command guards, diagnostics, installer, manual updater and tests. | Commit [`1e788e3`](https://github.com/PovilJ/adaptive-heating/commit/1e788e33bc3e428fd6d3a4978ba847189d91b4f6). First commit in the available repository history. |
| 2026-09-24 — validation record | Documentation recorded 59 passing tests, including platform imports and the setup form against Home Assistant 2026.7.4; repository access instructions were expanded. | Commit [`d7aedad`](https://github.com/PovilJ/adaptive-heating/commit/d7aedad41c2a38ccb6e891e14d0c9f1017328dbd). These smoke checks do not establish full integration setup/unload or field performance. |
| 2026-09-24 — legacy archive and documentation | Owner-supplied scripts preserved, checksums recorded, behavior differences and migration dependencies documented, and this status record added. Package installation clarified after the Apps repository error. | Commit [`b063640`](https://github.com/PovilJ/adaptive-heating/commit/b0636402ddad06b678b57fc907ce77d12e8291e6), [legacy archive](../legacy/README.md), [migration guide](MIGRATION.md). No controller behavior changed. |
| 2026-09-24 — HACS custom-repository setup | Added HACS metadata and installation-by-URL instructions, fixing the download rejection for commits such as `b063640` without `hacs.json`. HACS handles downloading and placing the component; the package installer remains available. Documented the different update behavior of each route. | Commit `0a65aba`, [hacs.json](../hacs.json), [installation instructions](../README.md#first-installation-through-hacs). Reproduced the rejection and checked the fix using upstream HACS download-eligibility code; live installation had not yet been performed at this stage. |
| 2026-09-24 — first-house installation and dashboard migration | HACS reports installed commit `0a65aba`; the integration entry is loaded on HA 2026.7.4 in Observe. Rebuilt the heating dashboard into Heating, Activity & trends, and Equipment views, using the new controls and decision records. | Live REST/WebSocket reads, dashboard save/read-back, template rendering and Chrome inspection. Old heating enable helper is off; the heat pump reports OFF, so the new controller is paused and has sent no command. [Dashboard record and rollback](DASHBOARD.md). This establishes installation and UI migration, not an Automatic cutover or field-performance validation. |

Legacy heating `0.3.2`, disinfection `1.0.0` and integration `0.1.0` are three
separate version histories. The smaller integration number does not indicate a
downgrade of the legacy script. No intervening legacy releases are archived here.

## Where we are

| Area | Status as of this review | What that means |
| --- | --- | --- |
| Source preservation | Committed in `b063640` | Both supplied scripts remain unchanged; their checksums and known gaps are recorded. |
| Reusable integration | Implemented; automated coverage | Entity selection and tuning use HA configuration entries/options. Learned parameters and the room target are stored per entry, outside Git and release archives. |
| Heating controller | Implemented; automated coverage | Curve and room feedback plus a bounded learned forecast correction. This is changed behavior, not complete legacy feature parity; see the [comparison](MIGRATION.md#behavior-and-feature-disposition). |
| Command handling and diagnostics | Implemented; automated coverage | Operating-state/inhibit gates, final limits and device steps, manual-change holds, Observe on restart, and separate proposed/limited/commanded/actual values. |
| Installation and manual updates | Implemented; automated coverage | Component-only ZIP and checksum, validated installation, code backups and explicit update/restart controls. A real HA installation/update/recovery trial is still needed. |
| Installation by repository URL | First-house HACS installation observed | HACS reports `0a65aba`, and integration 0.1.0 is loaded on HA 2026.7.4. Later HACS update/restart/recovery trials remain pending. The HA Apps repository screen remains a different installation mechanism. |
| HA compatibility | Partial validation recorded | Earlier real-HA imports/setup-form smoke checks are recorded. Full setup, options, reload and unload in an isolated HA instance remain pending. |
| Live use and another house | Installed in first house; Observe trial started | Entity reads and migrated dashboard verified while the heat pump was OFF. Automatic cutover, representative heating observations, comfort/energy comparison and a second-house trial remain pending. |
| Dashboard | Rebuilt and verified in first house | Native cards show mode, target, reasons, actual/proposed/allowed/sent temperatures, history, learning and solar readings. An offline generator accepts each house's entity mapping; local backups are excluded from Git. |
| Published release | None published as of 2026-09-24 | Checked with the GitHub releases API. HACS can install `main` without a release; the built-in stable-release updater needs published release assets. |
| Domestic-hot-water disinfection | Archived; outside integration scope | No migration or replacement is implemented. Existing helpers and the separate controller need their own treatment. |

## Validation evidence

- **Earlier baseline:** commit `d7aedad` records all 59 tests passing with Home
  Assistant 2026.7.4 available. This review preserves that report as historical
  evidence rather than claiming to have repeated it.
- **This documentation review:** `python3 -m unittest discover -s tests -v` on
  Python 3.14.7 discovered 59 tests: **57 passed, 2 skipped** because Home Assistant
  is not installed in this environment. The skipped tests are the two real-HA
  smoke checks in [test_homeassistant.py](../tests/test_homeassistant.py).
- Engine, fake-HA adapter and archive/installer tests cover the rewritten
  integration. They do not validate the archived PyScript code, actual equipment,
  achieved comfort or electricity savings.
- This review also built the release ZIP and ran the installer's validation-only
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

## Next milestones

These are pending work, not promised release dates or completed acceptance checks.

1. **Isolated HA validation:** run full setup/options/reload/unload; verify entity
   units, state labels and device limits; exercise a numbered install, update,
   restart and recovery. The initial live HACS installation is now recorded;
   update/restart/recovery checks and recording the exact HACS version remain.
2. **First-house Observe trial:** follow the [migration guide](MIGRATION.md),
   resolve old-writer and shared-helper dependencies, observe ordinary heating,
   hot water, defrost, missing inputs and manual changes; compare predictions
   with later measurements.
3. **Controlled first-house cutover:** commission curve/limits, disable the old
   heating writer, explicitly enable Automatic, and record comfort and measured
   electricity against a comparable baseline. Preserve a rollback path.
4. **Second-house installation:** install the same numbered artifact and select
   that house's entities without source edits or copied learned state. Record
   equipment differences and any setup gaps.
5. **Release readiness:** close the relevant [acceptance checks](DESIGN.md#tests-before-field-use),
   select a repository license, and publish tested assets with release notes
   using the [release procedure](RELEASING.md).

Later candidates from the design are automatic lag identification, multi-room
references, rolling prediction-error evaluation, measured electricity modeling,
tariff/export economics and direct support for signed power sensors. Reintroducing
legacy sun/time strategies or rewriting disinfection requires an explicit scope
decision and validation; neither is implied by preserving the old source.

## Keeping this record useful

For each meaningful implementation, validation, deployment or release milestone,
append a dated timeline entry with the commit/tag or test evidence and update the
status and pending work above. Distinguish implemented, automatically tested,
tested in isolated HA and observed on real equipment. Record unknown dates as
unknown and leave historical validation results attached to their original
version/environment. Update the migration comparison when behavior changes.
