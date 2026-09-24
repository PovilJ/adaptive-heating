# Adaptive Heating

An experimental Home Assistant custom integration for predictive heat-pump water
temperature control. It uses existing Home Assistant entities from any compatible
device integration. Each installation owns its settings and learned response.

**0.1.0 is an initial development build.** The recorded validation baseline is 59
passing tests, including controller, adapter and installer tests, plus
platform-import and setup-form smoke checks against Home Assistant 2026.7.4.
See the [validation record](docs/HISTORY.md#validation-evidence) for environments
and the latest local run. Loading the complete integration in an isolated
Home Assistant instance and observing real heating behavior are still required
before relying on Automatic mode. It has not been installed into the live heating
system during development.

## Origins and project status

This is a rewrite of the original house-specific PyScript heating controller into
a reusable integration. The original heating `0.3.2` and companion water
disinfection `1.0.0` scripts are preserved in [the legacy archive](legacy/README.md).
Integration `0.1.0` starts its own version series. The rewrite includes behavior
changes; hot-water disinfection remains separate and is not part of the package.

- [Timeline, completed work and next milestones](docs/HISTORY.md)
- [Legacy behavior comparison and migration guide](docs/MIGRATION.md)
- [Original source, dependencies and preservation checksums](legacy/README.md)

## What this build includes

- UI entity selectors and editable options, with no house-specific IDs in code.
- Observe (default), Automatic, and Off modes; an integration-owned room target.
- Weather compensation, room feedback, and a bounded predictive correction from
  an empirical model with a lagged heat-emitter state.
- Persistent per-installation model coefficients and target; mapping changes
  reset the model. Every startup or settings reload returns to Observe.
- Unit conversion for °C/°F and W/kW, fresh-temperature checks, operating-state,
  defrost and optional external-controller inhibition, final output limits,
  hardware-step handling, and manual-change/command-confirmation holds.
- Optional measured PV surplus awareness. Batteries retain household priority;
  charge percentage or zero grid import alone never authorizes preheating.
- Proposed, limited, commanded and actual setpoints, prediction diagnostics,
  electrical measurements, and a bounded recent-decision log.
- A manual **Check for updates** button and a standard **Install update** entity
  for this repository's stable releases. No HACS dependency or automatic update.

This build does **not** calculate COP, infer flow from pump speed, operate battery
charging settings, or manage domestic-hot-water disinfection. Measured electrical
power/energy is exposed for evaluation; the controller does not yet fit an
electricity-consumption model or optimize prices. The predictive objective uses
water temperature as an efficiency proxy, not a claim of measured savings.

## Requirements and entities

Target Home Assistant: **2026.7.0 or newer**, with import/schema smoke checks
verified on 2026.7.4. A writable `custom_components` directory is needed for installation.

Required selectors:

| Role | Entity |
| --- | --- |
| Room temperature | A temperature `sensor` |
| Weather and hourly forecast | A `weather` entity |
| Heating-water setpoint | A writable temperature `number` with min/max/step |
| Operating state | `sensor`, `binary_sensor`, or `select`, plus the exact state meaning space heating |

Optional selectors include outdoor temperature, return/supply temperatures,
defrost, another controller's enabled flag, electrical W/kWh, measured PV power,
positive grid import/export power, and battery SoC/charging/discharging power.

All battery selectors must be provided together or omitted together. In this
version, grid and battery powers must be separate nonnegative entities. If an
inverter exposes one signed power sensor, use its integration's split entities
or template sensors to expose charging/discharging separately. The sign meaning
must be checked for that inverter. Battery and solar inputs are never mandatory
for normal temperature control.

Return and supply temperatures are required only for model fitting. Without them
the integration keeps using the heating curve and room feedback. The first model
has a fixed three-hour lag; estimating the lag automatically is future work.

The integration controls a water-temperature number, **not a compressor power
switch**. Off means stop automatic writes; it does not turn off the heat pump.
Hot-water, defrost, off or unknown operating states prevent writes. A configured
inhibit input also blocks writes when on or unavailable. Map the existing
controller's enable flag to this input during migration.

## First installation (manual, once per house)

**Use the package installer, then Settings → Devices & services → Add integration.**
Adaptive Heating runs inside Home Assistant as a custom integration. The
Settings → Apps → Install app → Repositories screen accepts a different kind of
repository; it cannot install this project. See [installation troubleshooting](#installation-troubleshooting)
if it reports “not a valid app repository”. HACS is not required.

1. Download/clone [the project](https://github.com/PovilJ/adaptive-heating).
   Download the numbered release ZIP and adjacent `.sha256` asset into `dist/`
   if that release has been published, using a project checkout of the same
   version. Alternatively, build both assets from the checkout:

   ```sh
   python3 scripts/build_release.py
   ```

   This produces `dist/adaptive_heating-0.1.0.zip` and its checksum. GitHub's
   **Code → Download ZIP** is the project source and must be extracted and built;
   it is not the installable component archive.

2. Use a terminal with Python 3 and writable access to the actual Home Assistant
   configuration directory. From the project directory, validate the archive:

   ```sh
   python3 scripts/install.py dist/adaptive_heating-0.1.0.zip --config /config --check
   ```

   `/config` must be the target house's HA configuration directory as seen from
   that terminal. If it is mounted elsewhere, substitute that path. Running the
   command on a laptop does not install anything on a remote HA instance. The
   installer reads the target's `.HA_VERSION`; if that file is absent, pass
   `--ha-version` with the actual installed HA version to both commands.

3. Install when ready:

   ```sh
   python3 scripts/install.py dist/adaptive_heating-0.1.0.zip --config /config
   ```

   Alternatively extract the archive's `adaptive_heating` folder into
   `/config/custom_components/`. Do not copy the whole repository into that folder.

4. Restart Home Assistant manually. Add **Adaptive Heating** from Settings →
   Devices & services → Add integration, and select that house's entities.
5. Keep Observe selected while checking readings, limits, and recommendations.
   Disable the old writer before selecting Automatic. Control resumes only when
   space heating is positively confirmed. Startup rate limiting begins from the
   existing water setpoint; it never immediately jumps to the recommendation.

On the second house, repeat setup using its own entities. Learned parameters and
targets are stored through Home Assistant's storage API; they are not in the Git
repository or release archive. No copying of `.storage` between houses is needed.

### Installation troubleshooting

**“https://github.com/PovilJ/adaptive-heating.git is not a valid app repository”**
means the URL was submitted to the Apps repository manager. Apps are separate
applications; this repository supplies a custom integration loaded from
`custom_components/adaptive_heating/`. Removing `.git` from the URL will not
change its type. See Home Assistant's [app repository format](https://developers.home-assistant.io/docs/apps/repository/)
and [custom integration location](https://developers.home-assistant.io/docs/creating_integration_file_structure/#where-home-assistant-looks-for-integrations).

Use the package steps above. After installation, confirm that the HA configuration
directory contains `custom_components/adaptive_heating/manifest.json` directly,
restart Home Assistant, then add **Adaptive Heating** under **Devices & services**.
If it is still missing, check HA's logs for an integration import/version error
and confirm that the archive was not extracted into an extra nested directory.
Adding a repository URL alone does not place the integration files in HA.

## Normal controls

- **Room target:** the desired indoor temperature. Native internal units are °C.
- **Observe:** calculate and learn without sending water-setpoint commands.
- **Automatic:** permit bounded commands while all operating checks pass.
- **Off:** stop commands and learning, while keeping diagnostics available.
- **Evaluate now:** recompute; it does not bypass command intervals or slew limits.
- **Configure:** update mappings and tuning; changing them returns to Observe.

The initial curve is only a starting point, not a commissioned setting for every
house. Configure water limits appropriate for the equipment and emitters. A
manual setpoint change, or a command that is not confirmed, creates a hold; inspect
the cause, then select Observe followed by Automatic to resume. The controller
does not overwrite an externally selected setpoint outside its configured limits.

The predicted minimum is conditional on the **proposed** water temperature and
available forecast horizon. Actual commands may differ because of limits. It is
an estimate, not a guarantee, and remains unavailable until sufficient suitable
observations have been collected. Model fitting uses stable ordinary-heating
intervals and rejects detected disturbances; it cannot identify all internal gains.

## Solar and battery policy

Solar preheating defaults to disabled. Enabling it allows only a small increase
within the chosen comfort band. A minimum of fifteen minutes of sampled surplus
is needed. Missing/invalid measurements or a sampling gap reset qualification.

- Sunny weather or a full battery alone is insufficient.
- Snow-covered panels producing zero power never qualify as electrical surplus.
- A sunny room can still warm naturally; room feedback works independently of PV.
- Battery discharge, material battery charging, insufficient SoC, or grid import
  prevents extra preheating. The inverter continues to determine actual dispatch.
- Optional preheating should be enabled only when its use fits the household's
  export credit/banking arrangement; this build does not model export economics.

## Manual updates

Click **Check for updates**, review the offered stable version and release notes,
then click **Install update**. An update is never installed by a timer. Installation
validates the archive, checksum, expected repository/version, Python/JSON syntax,
and minimum Home Assistant version before replacing integration files. Old code is
kept in `/config/.adaptive_heating_backups/`; configuration entries and learned
data stay in their normal HA storage. These code copies are not full HA backups.

Controllers enter Observe before file replacement. Once installed, the update
card says **Restart required**. Restart when convenient and explicitly select
Automatic after checking operation. No automatic restart occurs. If replacement
fails, old code is restored; review the error before re-enabling Automatic. A
failed release check or download does not stop the running controller.

Update checks need outbound HTTPS to GitHub. Heating itself has no dependency on
GitHub availability. The existing weather integration may have its own network
requirements. Only the latest published stable release is offered; branch heads,
drafts and prereleases are not installed.

## Development and packaging

Core tests require only Python's standard library:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build_release.py
python3 scripts/install.py dist/adaptive_heating-0.1.0.zip --config /config --check
```

For the two real-HA import/schema smoke checks, create a separate Python 3.14
virtual environment and install `requirements-dev.txt`, then run the same test
command with that environment's Python. Those tests are explicitly skipped when
HA is absent. The adapter tests use in-memory fake services and never contact
equipment. Exercise an isolated HA installation before deploying live.

See [design and acceptance criteria](docs/DESIGN.md), [releasing](docs/RELEASING.md),
and [repository access](docs/GITHUB_ACCESS.md). No open-source license has yet been
selected by the repository owner; public visibility alone is not a license grant.
