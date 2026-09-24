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

## Architecture

`engine.py` contains deterministic unit conversion, validation, bounded learning,
thermal-response simulation, the curve/prediction decision and final output
constraints. It has no Home Assistant or network dependency.

`coordinator.py` owns entity reads, forecast caching, observations and all actuator
writes. Every command passes fresh operating checks after external awaits. Modes
and in-flight commands are serialized. The final command is both recorded and
checked against the device's later state. A manual edit or failed confirmation
holds control until explicitly resumed.

`config_flow.py` keeps mappings and tuning in HA configuration entries/options.
The coordinator stores fitted coefficients and target per entry via `Store`.
Mapping fingerprints prevent accidental reuse after changing the controlled
system. No installation-specific IDs are defaults in published code.

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

This first release explores constant water-temperature candidates, not an optimal
multi-period electricity schedule. The latter needs measured electrical-response
fitting, held-out validation and explicit tariff/export policy. Energy efficiency
must be assessed against a baseline under comparable weather and comfort.

## Tests before field use

- Load all platforms and complete setup/options forms in a real isolated HA.
- Confirm units, device step/min/max, operating-state labels, defrost and inhibit.
- Run Observe across ordinary heating, solar warmth, hot water and defrost.
- Compare predicted temperatures with later measurements; examine systematic bias.
- Test missing forecasts, unavailable indoor sensors and manual device changes.
- Confirm actual command acknowledgements and the interpretation of energy flows.
- Test installation/restart of a numbered release and code recovery on failure.
- Commission limits/curve, stop the old writer, then enable Automatic deliberately.

## Following development

Priority follow-ups are automatic lag identification, multi-room references,
rolling forecast error evaluation, measured electricity comparisons, optional
tariff/export economics, and support for signed power sensors directly in setup.
Domestic-hot-water disinfection remains a separate, unmodified controller. Changes
to that controller require their own specification and validation.
