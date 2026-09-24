# Releasing

The updater expects a stable three-part version such as `0.1.0` in all of:

- `custom_components/adaptive_heating/manifest.json`
- `custom_components/adaptive_heating/const.py`
- `custom_components/adaptive_heating/release.json`

Update the minimum HA version in `const.py`, `release.json` and root `hacs.json`
when needed.
Changing config-entry or stored-data schemas requires a tested migration; never
replace users' selections with new defaults.

1. Run unit tests and real-HA smoke checks; validate in a separate HA instance.
   Record the version/environment and results in [the project history](HISTORY.md),
   update its current status and pending milestones, and update the
   [migration comparison](MIGRATION.md) if behavior or compatibility changed.
2. Build with `python3 scripts/build_release.py`.
3. Commit reviewed source and tag the exact commit, for example `v0.1.0`.
4. Create a GitHub release for that tag with useful release notes.
5. Attach both assets from `dist/`:
   - `adaptive_heating-0.1.0.zip`
   - `adaptive_heating-0.1.0.zip.sha256`

The recorded first 0.1.0 baseline passed all 59 tests, including platform-import
and setup-form checks against Home Assistant 2026.7.4; see the
[validation record](HISTORY.md#validation-evidence) for the latest local run.
Full integration setup/unload and heating
trials are still pending. Keep it a development build until that validation is
done. The updater ignores draft and prerelease releases, so use those for public
testing rather than advertising an untested build as a stable update.

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

The integration never restarts Home Assistant. After an update, each controller
starts in Observe; users check status and explicitly re-enable Automatic.
