# Releasing

The updater expects a stable three-part version such as `0.1.0` in all of:

- `custom_components/adaptive_heating/manifest.json`
- `custom_components/adaptive_heating/const.py`
- `custom_components/adaptive_heating/release.json`

Update the minimum HA version in both `const.py` and `release.json` when needed.
Changing config-entry or stored-data schemas requires a tested migration; never
replace users' selections with new defaults.

1. Run unit tests and real-HA smoke checks; validate in a separate HA instance.
2. Build with `python3 scripts/build_release.py`.
3. Commit reviewed source and tag the exact commit, for example `v0.1.0`.
4. Create a GitHub release for that tag with useful release notes.
5. Attach both assets from `dist/`:
   - `adaptive_heating-0.1.0.zip`
   - `adaptive_heating-0.1.0.zip.sha256`

The first 0.1.0 build has not yet passed actual HA runtime validation. Keep it a
development build until that validation is done. The updater ignores draft and
prerelease releases, so use those for public testing rather than advertising an
untested build as a stable update.

GitHub's automatically generated source archive has a different layout and is not
an installable integration asset. Publish the archive made by the build script.
Only integration files are included: no live HA configuration, `.storage`, entity
mappings, credentials, history, tests or unrelated integrations.

## Recovering code

The installer preserves the previous component directory under
`/config/.adaptive_heating_backups/previous-*/adaptive_heating`. Restore it from a
terminal/file editor with Home Assistant stopped, then start HA again. This is
code recovery, not a guarantee of data-schema downgrade compatibility. Use a full
HA backup before future releases that introduce data migrations.

The integration never restarts Home Assistant. After an update, each controller
starts in Observe; users check status and explicitly re-enable Automatic.
