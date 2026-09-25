# Design and acceptance criteria

For the rewrite's origin and progress, see [project history](HISTORY.md), the
[legacy comparison and migration guide](MIGRATION.md), and the
[preserved source snapshots](../legacy/README.md).

## Agreed product constraints

- Preserve adaptive, anticipatory water-temperature control and indoor comfort.
- A public standalone repository; HACS is not required.
- Per-house UI entity selections independent of manufacturer and released code.
- No flow meter, COP, guessed flow-rate model, or claimed thermal-output data.
- Solar production is distinct from passive warmth through the windows.
- Normal household demand already uses the battery; SoC is not spare energy.
- Keep household/battery dispatch separate from discretionary heating changes.
- Snow, cloudy spells, missing sensors, bad forecasts, hot water, defrost, stale
  measurements and manual changes must have explicit behavior and tests.
- Version check and installation are manual. Restart is a separate user action.
- Cold-night preparation may shift comfort within commissioned limits; it must
  preserve early recovery and existing water slew limits.
- Optional AC supplies bounded assistance, respects manual ownership, and does
  not contaminate the floor-heating or cooldown models.

## Architecture

`engine.py` contains deterministic unit conversion, validation, bounded learning,
thermal-response simulation, the curve/prediction decision and final output
constraints. It has no Home Assistant or network dependency.

`coordinator.py` owns entity reads, forecast caching, observations and the shared
lock used by heating, tank and AC writers. Every command passes fresh operating
and ownership checks after external awaits. Modes
and in-flight commands are serialized. The final command is both recorded and
checked against the device's later state. A manual edit or failed confirmation
holds control until explicitly resumed.

`planner.py` contains the independent cold-night settings, hourly forecast
validation, empirical low-water cooldown model and phase policy. It has no Home
Assistant dependency. `ac_controller.py` owns the optional climate session state
machine, separate recovery journal, confirmation/manual-override behavior, and
sampled electrical budget. `disinfection.py` and `disinfection_controller.py`
retain the separate tank policy and its restoration lifecycle.

`config_flow.py` keeps mappings and tuning in HA configuration entries/options.
The coordinator stores fitted coefficients and target per entry via `Store`.
Mapping fingerprints prevent accidental reuse after changing the controlled
system. The cooldown model is additive to existing per-entry storage; legacy
entries without new mappings preserve their original identity. AC sessions use
a separate journal that retains the original entity for interrupted recovery.
No installation-specific IDs are defaults in published code.

`release.py` is independently tested for archive validation and recoverable
replacement. `updater.py` downloads only from this repository's stable release
assets when explicitly asked. Version detection and download failure do not enter
the heating control path.

## Deliberately bounded first model

The starting model has room temperature and a lagged emitter/building heat state.
It fits two bounded temperature-response coefficients from suitable consecutive
measurements. The three-hour lag is currently a fixed assumption. Coefficients
and predicted temperature errors are empirical; none represents measured COP.

Forecast correction remains within 2 °C of the curve. The model has no influence
until 24 accepted samples exist and its recent one-step residual is small. This
is a conservative gate, not a statistical confidence guarantee or proof of
twelve-hour forecast accuracy. There is no automatic sunny-weather heat injection.

The original water model explores constant water-temperature candidates, not an optimal
multi-period electricity schedule. The latter needs measured electrical-response
fitting, held-out validation and explicit tariff/export policy. Energy efficiency
must be assessed against a baseline under comparable weather and comfort.

## Cold-night policy in 0.3.0

Planning is optional and disabled by default. It uses up to 24 hours of continuous
hourly weather through the relevant morning/recovery window. Sustained cold or a
substantial fall can schedule preparation using sunset, a fallback local hour and
the floor lead time. An estimated shortfall sets the preparation target up to the
comfort ceiling; an already sufficient reserve avoids additional preheat.

A separate empirical coefficient describes room cooldown under settled low-water
operation. Fitting requires fresh room/outdoor and measured water temperatures,
at least 60 minutes with the target at minimum and actual water near that setting,
a stable rolling hour, dark conditions and no AC/tank interference. Changing the
low-water or Sun configuration invalidates cooldown calibration. This is not a
measured unheated-building loss coefficient: residual
floor heat, continued low-water output and unobserved gains can affect it. The
model starts with a conservative prior, keeps an uncertainty allowance, and never
converts room-temperature reserve into thermal kWh.

Coasting lowers the water recommendation while a conservative projection leaves
headroom above the night minimum. Recovery allows time for both the floor delay
and raising the water target within the commissioned slew limits, device steps
and command cadence. The ramp budget begins from the lower of current water
target and planned minimum, avoiding a falsely short estimate before a coast.
These limits
remain authoritative, including the default 4 °C/hour rise and 2 °C/hour fall;
rapid overnight load shifting is not guaranteed. Measured faster cooling can
advance recovery. A configured protection-room sensor vetoes reduced heating when
it is too cool or unavailable; it is not full multi-zone optimization.

Sunshine never supplies an assumed thermal gain to a projection. Consecutive sunny
morning forecasts can alter preferred recovery only when coverage and the
projected reserve permit it. Waiting during the morning also requires measured
room warming. A missing or unusable forecast returns control to the normal curve.
PV electrical surplus is an independent policy.

AC assistance has a separate initial Observe mode and requires both AC and main
control Automatic for a new session. It borrows only a verified Off unit,
persists ownership before commanding Heat and a bounded target, confirms the
reported state, and restores Off only while ownership still matches. Manual
operation is left alone. Duration/rest/temperature limits and optional sampled
electrical kWh bound assistance; an absent meter never implies zero consumption
or proven savings. Session energy is not a cumulative lifetime meter.

AC operation, including manual use and a settling period afterward, excludes
both learning paths and prevents an uncertain local air-temperature reserve from
authorizing coasting. Disabling/restarting the integration cannot erase recovery
ownership. Detailed settings and operational limits are in
[COLD_NIGHTS.md](COLD_NIGHTS.md).

## Tests before field use

- Load all platforms and complete setup/options forms in a real isolated HA.
- Confirm units, device step/min/max, operating-state labels, defrost and inhibit.
- Run Observe across ordinary heating, solar warmth, hot water and defrost.
- Compare predicted temperatures with later measurements; examine systematic bias.
- Test missing forecasts, unavailable indoor sensors and manual device changes.
- Exercise cold-night preparation, the preheat ceiling, midnight/DST transitions,
  insufficient forecast coverage, ramp-aware recovery and faster-than-learned cooling.
- Verify protection-room vetoes and learning exclusions across manual/automatic
  AC operation, startup, sensor events and settling intervals.
- Test independent modes, partial/unconfirmed AC acknowledgments, manual takeover,
  stale metering, duration/energy limits, interrupted recovery and unload behavior.
- Confirm actual command acknowledgements and the interpretation of energy flows.
- Test installation/restart of a numbered release and code recovery on failure.
- Commission limits/curve, stop the old writer, then enable Automatic deliberately.

## Following development

Priority follow-ups are automatic lag identification, fuller multi-room planning,
learned window-gain timing, rolling forecast error evaluation, measured electricity comparisons, optional
tariff/export economics, and support for signed power sensors directly in setup.
Domestic-hot-water disinfection is implemented as an optional coordinated controller
in 0.2.0; cold-night/AC coordination is implemented locally in 0.3.0. See
[the tank policy and recovery design](DISINFECTION.md). Changes
to that controller require their own specification and validation.
