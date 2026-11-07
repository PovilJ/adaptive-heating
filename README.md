# Adaptive Heating

An experimental Home Assistant custom integration for heat-pump water temperature
control of slab underfloor heating. It uses existing Home Assistant entities, but from
0.6.0 its controller relies on firmware that behaves like the **Gree Versati**'s (see
[Requirements](#requirements-and-entities)). Each installation owns its settings and
learned response.

**0.6.0 is an experimental build.** It replaces the 36-hour planner with a thermostat on
the floor slab, read from the water sensors: it decides when the compressor starts and stops,
starts it gently, holds it at an efficient mid output, and anticipates forecast cold, forecast
sun and the house's own daily pattern. In the lab simulator of the first house it uses about
6–7 % less metered electricity than 0.5.3 and holds the room on target instead of 0.3 °C warm;
see [docs/CONTROLLER.md](docs/CONTROLLER.md). **These are simulated numbers only.** The
electricity half depends on the unit's measured part-load efficiency, which the two-hold field
test should confirm (with flat efficiency the saving is about 1.4 %), and the lab's port of
0.5.3 may run slightly warmer than the real 0.5.3. Expect less electricity in cold and mixed
weather, and about the same electricity with a room closer to target in mild weather. Field
results in the house are pending. Tests and their environment are recorded in the
[validation record](docs/HISTORY.md#validation-evidence).
No numbered GitHub release is published; HACS installs the `main` branch.

## Origins and project status

This is a rewrite of the original house-specific PyScript heating controller into
a reusable integration. The original heating `0.3.2` and companion water
disinfection `1.0.0` scripts are preserved in [the legacy archive](legacy/README.md).
Integration `0.1.0` started its own version series. Version **0.2.0** added optional
tank disinfection using the normal tank setpoint, with a continuous measured hold,
recovery journal, and shared heating/solar scheduling inputs. The rewrite includes
behavior changes; see the [disinfection guide](docs/DISINFECTION.md).
Version **0.3.0** adds a new implementation of cold-night preparation and
coasting, with optional AC sessions and separate empirical cooldown learning.
It does not reproduce the legacy script's strategy rules verbatim.
Version **0.3.1** separates heating enablement from compressor activity, retains
floor heat across pauses, and adds forecast/trend preparation and bounded
assistance for sustained failed recovery. Versions **0.4–0.5** planned the water
36 hours ahead with a fitted house model. Version **0.6.0** replaces all heating
logic with the [slab thermostat](docs/CONTROLLER.md) that won the
[lab comparison](docs/research/CONTROLLER_COMPARISON.md).

- [Timeline, completed work and next milestones](docs/HISTORY.md)
- [Legacy behavior comparison and migration guide](docs/MIGRATION.md)
- [Original source, dependencies and preservation checksums](legacy/README.md)
- [Dashboard layout, reuse and rollback](docs/DASHBOARD.md)
- [Disinfection setup, scheduling and recovery](docs/DISINFECTION.md)
- [How the 0.6 heating controller works](docs/CONTROLLER.md)
- [Offline lab simulator and controller race](lab/README.md)

## What this build includes

- A slab thermostat that owns the compressor's runs: floor estimate from the
  return/supply water, a floor target from the room, the forecast (cold and sun,
  1–9 hours ahead) and a learned level and daily pattern; gentle starts, mid-output
  riding, one-write stops and an outage-safe parked setpoint. Evaluated every minute,
  at most 46 setpoint writes a day. See [docs/CONTROLLER.md](docs/CONTROLLER.md).
- Fail-safes for link drops, hot water, defrost, a missing forecast and a lost room
  thermometer (it keeps heating on a learned outdoor curve and notifies you).
- Learned state kept across restarts per installation; mapping changes restart it.
- Optional AC assistance with independent modes, external room feedback,
  outdoor-temperature and session limits, manual ownership handling, restart
  recovery, and measured session kWh when an AC power meter is configured. It is
  asked for only while the floor is heating and the room is clearly under target.
- Optional tank disinfection with independent Observe/Automatic/Off, continuous
  temperature hold, bounded timeout/restoration, and persistent cycle history.
- UI entity selectors and editable options, with no house-specific IDs in code.
- Observe (default), Automatic, and Off modes; an integration-owned room target.
- Unit conversion for °C/°F and W/kW, operating-state, defrost and optional
  external-controller inhibition, device limits and steps, and
  manual-change/command-confirmation holds.
- Optional measured PV surplus awareness. Batteries retain household priority;
  charge percentage or zero grid import alone never authorizes preheating.
- Floor estimate and target, proposed, limited, commanded and actual setpoints,
  electrical measurements, and a bounded recent-decision log.
- A manual **Check for updates** button and a standard **Install update** entity
  for this repository's stable releases. No HACS dependency or automatic update.
- Optional installation by repository URL through HACS, with no manual archive
  handling or source copying.

This build does **not** infer flow from pump speed, operate battery charging
settings, write any heat-pump register other than the heating-water setpoint, or
invoke native heat-pump disinfection modes. Measured electrical power/energy is
exposed for evaluation; it is not used by the controller.

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

**The heat pump must behave like the Gree Versati.** The 0.6 controller starts, rides
and stops runs through the leaving-water setpoint and reads the floor from the return
water, so it needs:

- a circulation pump that keeps running while the compressor rests (the return water is
  then the floor temperature);
- a compressor start when setpoint − control sensor reaches the restart hysteresis, a stop
  when the control sensor is 2 °C over the setpoint, and modulation in between.

On a unit whose pump stops with the compressor, or whose start/stop rules differ, the floor
estimate and the start, ride, park and stop setpoints are wrong: use Observe only, or stay on
0.5.x. The house constants (loop flow, sensor offsets, hysteresis) must be measured for each
house; see [commissioning](docs/CONTROLLER.md#commissioning-another-house).

Return- and supply-water temperature sensors are required: the controller reads
the floor from them. For **Automatic**, also map the **heating-mode entity** and
the value that means space heating is enabled: the controller starts and stops the
compressor itself and must tell "resting with heating on" from "heating off".
Optional selectors include the unit's restart-hysteresis register (read only),
outdoor temperature, defrost, another controller's enabled flag, electrical W/kWh,
measured PV power, positive grid import/export power, and battery
SoC/charging/discharging power.

All battery selectors must be provided together or omitted together. In this
version, grid and battery powers must be separate nonnegative entities. If an
inverter exposes one signed power sensor, use its integration's split entities
or template sensors to expose charging/discharging separately. The sign meaning
must be checked for that inverter. Battery and solar inputs are never mandatory
for normal temperature control.

The forecast's cloud cover becomes forecast sun through the house's location in
Home Assistant (Settings → System → General); without a location no sun is
credited. AC assistance needs a `climate` entity with Heat/Off support and an
external room temperature sensor; an AC electrical-power sensor is optional.
No additional helpers are required.

The integration controls a water-temperature number, **not a compressor power
switch**. It starts and stops runs only through that setpoint and the unit's own
restart and stop rules. Off means stop automatic writes; it does not turn off the
heat pump. Hot water, defrost and operating states that no mapping names pause the
run; an unavailable unit link, a disabled heating mode and a configured inhibit input
(on or unavailable) prevent writes. Map the existing controller's enable flag to the
inhibit input during migration.

Use the unit's activity sensor for active heating and hot-water detection, with
its idle value (for example `OFF`) as the compressor-idle state; numeric mode
values such as `4` and `4.0` match. Map the restart-hysteresis register if the
unit exposes it, so the controller always uses the unit's own value; otherwise
set the *Restart hysteresis* option to the unit's setting (a larger value than the
unit's would let the parked setpoint start the compressor).

## First installation through HACS

**To install by repository URL without handling ZIP files, use HACS.** Adaptive
Heating is a custom integration. HACS downloads and places its files for you.
Home Assistant's **Apps → Repositories** screen installs standalone apps and
cannot install this integration.

1. If HACS is not already available in your HA sidebar, follow its official
   [installation and setup guide](https://www.hacs.xyz/docs/use/).
2. Open **HACS → ⋮ → Custom repositories**.
3. Enter `https://github.com/PovilJ/adaptive-heating` and select type
   **Integration**, then **Add**.
4. Find **Adaptive Heating** in HACS, open it and select **Download**. Until a
   numbered release is published, HACS uses the default `main` branch; this is
   the experimental development build.
5. Restart Home Assistant, then open **Settings → Devices & services → Add
   integration → Adaptive Heating** and select this house's entities.
6. Keep **Observe** selected while checking readings, limits and recommendations.
   Follow the [migration guide](docs/MIGRATION.md) when replacing the old heating
   script, and disable the old writer before selecting Automatic.

Repeat those steps at the other house with its own entities. Configuration and
learned data stay in each HA instance. HACS installs only the component directory;
the legacy scripts are not installed. The repository is added manually as a
custom repository; it is not listed in the default HACS catalog.

See the official [HACS custom-repository instructions](https://www.hacs.xyz/docs/faq/custom_repositories/).
If you prefer not to use HACS, the package installer below remains available.

## First installation (manual, once per house)

This alternative installs the same integration without HACS. For installation
by URL, use [the HACS steps above](#first-installation-through-hacs).

1. Download/clone [the project](https://github.com/PovilJ/adaptive-heating).
   Download the numbered release ZIP and adjacent `.sha256` asset into `dist/`
   if that release has been published, using a project checkout of the same
   version. Alternatively, build both assets from the checkout:

   ```sh
   python3 scripts/build_release.py
   ```

   This produces `dist/adaptive_heating-0.6.0.zip` and its checksum. GitHub's
   **Code → Download ZIP** is the project source and must be extracted and built;
   it is not the installable component archive.

2. Use a terminal with Python 3 and writable access to the actual Home Assistant
   configuration directory. From the project directory, validate the archive:

   ```sh
   python3 scripts/install.py dist/adaptive_heating-0.6.0.zip --config /config --check
   ```

   `/config` must be the target house's HA configuration directory as seen from
   that terminal. If it is mounted elsewhere, substitute that path. Running the
   command on a laptop does not install anything on a remote HA instance. The
   installer reads the target's `.HA_VERSION`; if that file is absent, pass
   `--ha-version` with the actual installed HA version to both commands.

3. Install when ready:

   ```sh
   python3 scripts/install.py dist/adaptive_heating-0.6.0.zip --config /config
   ```

   Alternatively extract the archive's `adaptive_heating` folder into
   `/config/custom_components/`. Do not copy the whole repository into that folder.

4. Restart Home Assistant manually. Add **Adaptive Heating** from Settings →
   Devices & services → Add integration, and select that house's entities.
5. Keep Observe selected while checking readings, limits, and recommendations.
   Disable the old writer before selecting Automatic. Control resumes only when
   space heating is positively confirmed.

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

Use **HACS → Custom repositories → Integration** with the URL above, or the
package installer. After installation, confirm that the HA configuration
directory contains `custom_components/adaptive_heating/manifest.json` directly,
restart Home Assistant, then add **Adaptive Heating** under **Devices & services**.
If it is still missing, check HA's logs for an integration import/version error
and confirm that the archive was not extracted into an extra nested directory.
In HACS, adding the repository is followed by downloading the integration; the
repository entry alone does not install it.

**“The version b063640 for this integration can not be used with HACS”** refers
to a commit before `hacs.json` was added. Refresh this repository's information
in HACS and retry the latest `main` commit. Do not select `b063640` or another
older commit without that file. HACS needs to read the metadata at the selected
commit; a GitHub release is not required for branch installation. If the same
error occurs on a newer commit, inspect HA's HACS logs for a metadata download
failure. A separate minimum-version message means HA must meet the documented
2026.7.0 requirement.

## Normal controls

- **Room target:** the desired indoor temperature. Native internal units are °C.
- **Observe:** decide every minute and show what would be written, without
  writing or learning.
- **Automatic:** write the heating-water setpoint while all operating checks pass,
  and learn. A run already in progress is taken over, not stopped. Automatic resumes
  by itself after a Home Assistant restart or a reload of the same version and options.
- **Off:** stop commands and learning, while keeping diagnostics available.
- **Evaluate now:** run the controller once more now.
- **Configure:** update mappings and options; changing them returns to Observe.

Leaving Automatic (selecting Observe or Off, an options change, a reload, an update)
writes the controller's idle setpoint once, so the unit keeps the floor near its start
point by itself and is never left riding a run nobody watches. It is not written while
another controller's inhibit is on or after you set the value by hand. If Home Assistant
stops and does not come back, the unit keeps the last setpoint.

A manual setpoint change creates a hold. A command the unit does not show within five
minutes is sent once more; a second unconfirmed command, or three failed ones, also
create a hold. A hold raises a Home Assistant notification; inspect the cause, then
select Observe followed by Automatic to resume. The **Heating cycle** sensor shows what the controller is doing (`idle`,
`kick`, `ride`, `stop`, `wait`, `hold`) and its attributes show the floor estimate,
the floor target and its parts, and what it has learned. The learned level adapts
within hours; the daily pattern needs one to two weeks. The house constants in the
options default to the first house; see [docs/CONTROLLER.md](docs/CONTROLLER.md#options)
before changing them.

## AC assistance

AC assistance starts in Observe and requires both its own mode and main control
to be Automatic before it can start an owned session. It is asked for only while
the floor is already heating and the room is at least *AC help below target*
(1 °C by default) under its target; the floor never relies on it. It only borrows
an Off unit, returns it to Off after assistance, and respects external changes. An
unavailable AC counts as off. While a session runs, its warmth cannot lower the
floor target, and manual or automatic AC operation pauses learning, including a
settling period. With no AC power meter, only the runtime cap applies; electricity
and savings are not inferred.

## Solar and battery policy

Solar preheating defaults to disabled. Enabling it raises the room target by the
preheat degrees (within the chosen comfort band) while a measured surplus lasts,
and pauses learning meanwhile. A minimum of fifteen minutes of sampled surplus
is needed. Missing/invalid measurements or a sampling gap reset qualification.

- Sunny weather or a full battery alone is insufficient.
- Snow-covered panels producing zero power never qualify as electrical surplus.
- A sunny room can still warm naturally; the forecast sun and room terms work
  independently of PV.
- Battery discharge, material battery charging, insufficient SoC, or grid import
  prevents extra preheating. The inverter continues to determine actual dispatch.
- Optional preheating should be enabled only when its use fits the household's
  export credit/banking arrangement; this build does not model export economics.

## Manual updates

If you installed through HACS, use HACS for subsequent downloads/updates. Cancel
any tank cycle and wait for confirmed normal-target restoration. Select Observe
for main heating, tank disinfection and AC assistance, and wait for any owned AC
session to confirm Off before downloading. Restart Home Assistant afterward, then check operation
before re-enabling Automatic. HACS handles file replacement itself and does not
run this project's installer or its pre-install Observe transition. Its downloads
also do not create this project's `.adaptive_heating_backups` code copies. Keep
updates manual and use one update route consistently so HACS's installed-version
record stays aligned with the files. HACS can track `main` commits before numbered
releases exist.

For installations managed by this project's package installer, use the built-in
release controls:

Click **Check for updates**, review the offered stable version and release notes,
then click **Install update**. An update is never installed by a timer. Installation
validates the archive, checksum, expected repository/version, Python/JSON syntax,
and minimum Home Assistant version before replacing integration files. Old code is
kept in `/config/.adaptive_heating_backups/`; configuration entries and learned
data stay in their normal HA storage. These code copies are not full HA backups.

Controllers enter Observe and require tank/AC recovery to finish before file
replacement. Once installed, the update
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
python3 scripts/install.py dist/adaptive_heating-0.6.0.zip --config /config --check
```

For the real-HA import/schema and isolated lifecycle checks, create a separate Python 3.14
virtual environment and install `requirements-dev.txt`, then run the same test
command with that environment's Python. Those tests are explicitly skipped when
HA is absent. The adapter tests use in-memory fake services and never contact
equipment. Exercise an isolated HA installation before deploying live.

The lab simulator drives the production controller file through
`lab/controllers/production.py`:

```sh
.local/lab-venv/bin/python lab/run.py --rank -c reference_tuned,hybrid,production -s season --seeds 5-9
```

See [design and acceptance criteria](docs/DESIGN.md), [releasing](docs/RELEASING.md),
and [repository access](docs/GITHUB_ACCESS.md). No open-source license has yet been
selected by the repository owner; public visibility alone is not a license grant.
