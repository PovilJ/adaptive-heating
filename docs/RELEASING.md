# Releasing

The updater expects a stable three-part version such as `0.3.0` in all of:

- `custom_components/adaptive_heating/manifest.json`
- `custom_components/adaptive_heating/const.py`
- `custom_components/adaptive_heating/release.json`

Update the minimum HA version in `const.py`, `release.json` and root `hacs.json`
when needed.
Changing config-entry or stored-data schemas requires a tested migration; never
replace users' selections with new defaults.

Current source is **local experimental 0.3.0**. Updating version metadata or
building an archive does not publish it or change a live HA installation.
Publication and deployment are separate actions after review and commissioning.

1. Run unit tests and real-HA smoke checks; validate in a separate HA instance.
   Record the version/environment and results in [the project history](HISTORY.md),
   update its current status and pending milestones, and update the
   [migration comparison](MIGRATION.md) if behavior or compatibility changed.
2. Build with `python3 scripts/build_release.py`.
3. Commit reviewed source and tag the exact commit, for example `v0.3.0`.
4. Create a GitHub release for that tag with useful release notes.
5. Attach both assets from `dist/`:
   - `adaptive_heating-0.3.0.zip`
   - `adaptive_heating-0.3.0.zip.sha256`

The recorded first 0.1.0 baseline passed all 59 tests, including platform-import
and setup-form checks against Home Assistant 2026.7.4; see the
[validation record](HISTORY.md#validation-evidence) for the latest local run.
Later isolated lifecycle checks cover real HA setup/options/reload/unload with
simulated equipment, including tank and AC recovery. Live 0.3.0 deployment,
heating/AC performance and actual energy comparisons remain pending. Keep this
experimental status explicit. The updater ignores draft and prerelease releases, so use those for public
testing rather than advertising an untested build as a stable update.

For 0.3.0, verify backward loading of existing entries and water-model storage,
default-disabled planning and Observe modes, optional mapping removal, cooldown
storage, AC journal restart/recovery and preservation on failed unload/removal.
Exercise the full suite in the isolated Python 3.14 environment with pinned
`requirements-dev.txt`; dependency-free checks skip real-HA tests and are not
equivalent evidence. Validate the built archive with the installer `--check`
against the target HA version before offering it. Keep historical checksums and
archive-exclusion checks for the legacy scripts.

GitHub's automatically generated source archive has a different layout and is not
an installable integration asset. Publish the archive made by the build script.
Only integration files are included: no live HA configuration, `.storage`, entity
mappings, credentials, history, tests or unrelated integrations. The historical
scripts in [legacy/](../legacy/README.md) are also excluded; installing a release
does not install, migrate or disable those PyScript controllers.

## HACS custom repository

Root [hacs.json](../hacs.json) selects the existing
`custom_components/adaptive_heating/` layout. `zip_release` is false: HACS downloads
the component from repository source, so users do not build, download or unpack
the installer assets themselves. HACS can use the default branch before releases
exist; keep that development status visible in the README. Once numbered releases
exist, users can select them in HACS.

Continue publishing ZIP/checksum assets for the separate built-in updater and
package installer. HACS does not invoke that updater's validation, Observe
transition or code-backup path. Document each update route accurately and test
HACS installation/download/restart in an isolated HA instance before marking that
route as validated. Adding a custom repository is separate from admission to
HACS's default catalog.

## Recovering code

The installer preserves the previous component directory under
`/config/.adaptive_heating_backups/previous-*/adaptive_heating`. Restore it from a
terminal/file editor with Home Assistant stopped, then start HA again. This is
code recovery, not a guarantee of data-schema downgrade compatibility. Use a full
HA backup before future releases that introduce data migrations.

Before replacing files or downgrading, put main, tank and AC controls in Observe
and wait for owned tank/AC restoration to finish. HACS does not perform that
transition. The built-in updater requires it before replacement. Do not delete
outstanding recovery journals to force an update; old code may not understand
new session data, and code restoration alone does not restore equipment settings.

The integration never restarts Home Assistant. After an update, each controller
starts in Observe; users check status and explicitly re-enable Automatic.
