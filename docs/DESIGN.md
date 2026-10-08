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
It fits two bounded temperature-response coefficients the way the original
PyScript did: at most every 30 minutes it compares the room with itself 2–3
hours earlier, only at night, adjusting heat loss while the floor is off and
floor gain while it is heating, by 0.5 % of the error with a hard cap per fit.
Five-minute polls only track the floor-heat estimate; one poll moves the room
less than a sensor step and teaches nothing. On first use the coefficients start
from the PyScript's `input_number.heating_k_loss`/`heating_k_gain` when present. The initial three-hour
floor response is now configurable; automatic identification remains future work. Coefficients
and predicted temperature errors are empirical; none represents measured COP.

Forecast correction remains within 2 °C of the curve. The model has no influence
until 24 accepted fits exist (about two nights) and its recent error across the
2–3 hour window is at most 0.3 °C. This
is a conservative gate, not a statistical confidence guarantee or proof of
twelve-hour forecast accuracy. There is no automatic sunny-weather heat injection.
Daylight intervals are not fitted, so sunshine through the windows does not
enter loss/gain; internal gains at night still can. In continuous cold-weather
heating the floor is never off, so loss stays at its last value and gain absorbs
the difference.

In 0.3.1, the baseline itself anticipates sustained forecast cooling within the
configured floor delay, water ramp and one command opportunity. Two adjacent
cold hours are required; future warming cannot lower the baseline early. This
policy works before model calibration. A continuous 30–60 minute room trend
can add up to 2 °C of water compensation for expected cooling during the floor
response. Sustained stalled recovery adds a separate 0.5 °C per command interval
after the floor-response allowance, capped at 2 °C and decaying as the room warms.
The model cannot cancel these recovery additions through a negative correction
while measured cooling or stalled recovery warrants them. A below-target falling
room holds ordinary floor reductions. Intentional night coasting and comfort
ceiling reductions retain precedence, and all final actuator limits still apply.
AC operation/settling exclude room-trend recovery as well as model fitting.
These are bounded recovery policies, not measured slab energy or guaranteed
future temperatures.

Heating enablement and compressor activity are distinct. An optional mode entity
confirms heating remains enabled while the activity sensor reports idle. Activity
and defrost events capture short floor-heating cycles between five-minute polls.
The floor state follows measured circuit water while charging and relaxes toward
room temperature over hours when idle or heating the tank. It is never instantly
set to room temperature just because the compressor stops. Both heating and idle
intervals fit the empirical response, with accepted hours exposed separately.
AC operation and settling exclude both fitting paths. Unknown phases and invalid
temperature data cannot establish a fit; normal tank/defrost pauses still permit
observing the floor's residual heat while preventing space-heating writes.

Forecast candidates start from current measured water and include the configured
water rise/fall rates and command cadence before the floor delay. Device-specific
steps, compressor modulation and weather/internal gains remain uncertainties;
these are conditional temperature projections, not a certified slab model.
Recovery planning reserves at least the configured floor-response duration plus
the existing water ramp budget. Previous response fits are invalidated by the
model revision, while the room target is retained.

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
in 0.2.0; cold-night/AC coordination was added in 0.3.0 and is installed with the
0.3.1 controller in the first house. Representative operation remains to be
validated. See
[the tank policy and recovery design](DISINFECTION.md). Changes
to that controller require their own specification and validation.
