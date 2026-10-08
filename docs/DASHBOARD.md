# Heating dashboard

The **2026-10-08** tabbed dashboard follows the original Mushroom layout: one
compact card per reading, value on top, label underneath, and an icon whose
colour carries the state. Controls sit inside the card they belong to.

It needs these frontend resources that the first house already has:
[Mushroom](https://github.com/piitaya/lovelace-mushroom), Stack In Card,
card-mod and apexcharts-card. The generator does not install them and has no native fallback.

## Tabs

| Tab | Path | What is there |
| --- | --- | --- |
| **Home** | `/dashboard-heating/home` | Outdoor weather chip, room temperature with target ± buttons, heat-pump activity with the control-mode selector, power, COP, water out/in, water target, tank, the night plan, the latest reason and a 24-hour room graph. Read-only apart from room target and mode. |
| **Trends** | `/dashboard-heating/trends` | Room, outdoor, heating-water, tank, power and COP graphs, energy today/month/total, a 7-day energy bar chart, state timelines and the last 10 decisions. |
| **Plan** | `/dashboard-heating/plan` | Hourly forecast, cold-night plan with its times and estimates, AC assistance with its mode, and learning progress. |
| **Hot water** | `/dashboard-heating/water` | Tank temperature with target ± buttons, tank graph, disinfection status/mode, hold progress, Run (asks to confirm) and Cancel, and cycle history. |
| **System** | `/dashboard-heating/system` | Efficiency (COP, lift, economizer), equipment states, quiet mode, manual water target, Evaluate now, integration settings and updates. |

## Colours

| Card | Colour meaning |
| --- | --- |
| Room | blue more than 0.5 °C below target, green within 0.5 °C, deep orange above |
| Heat pump | orange heating floor, red hot water, indigo defrost, blue compressor resting (heating still enabled), grey off |
| Power | grey under 100 W, green under 1.5 kW, amber under 3 kW, red above |
| COP | green from 4, light green from 3, orange from 2, red below, grey when not running |
| Tank | red from 45 °C, orange from 38 °C, blue below |
| Mode selectors | green Automatic, amber Observe, grey Off |

A missing reading shows **—**, never zero. Tank-disinfection and AC notices
appear on Home only while active or needing attention. The arrow after the room
target (↘ → ↗) is the measured room trend. **Water target · next N°** compares
the live device target with the latest permitted candidate; it is not a
guaranteed command.

## October 8 power correction and deployment

The first-house `sensor.oras_vanduo_total_power` previously summed three phase
readings in kW while declaring W. Corrected the existing template to multiply
that sum by 1000 and its COP consumer to divide W by 1000. This preserves the
COP calculation's scale and fixes the existing power-to-energy integration's
source unit. A live check showed **1430 W** against a **1.430 kW** phase sum.
HA configuration validation and template reload succeeded. Earlier power history and values
from the previously mis-scaled calculated-energy helper were not rewritten.
Now uses this corrected live power sensor; Trends uses the native combined
energy meter and daily/monthly counters.

## Deploy and roll back

Every deployment first saves the live dashboard to the ignored
`.local/ha-dashboard-backups/<timestamp>-tabs/dashboard-before.json`, checks
that every referenced entity exists, renders every template through HA, saves
with `lovelace/config/save` and reads the result back. Roll back by saving that
`dashboard-before.json` the same way. This restores cards only, not equipment
targets or modes. Never edit HA `.storage` directly.

## Reuse in another house

[`scripts/build_dashboard.py`](../scripts/build_dashboard.py) is an offline
generator. It reads explicit entity mappings and writes JSON; it never reads
credentials, connects to HA or operates equipment.

```sh
python3 scripts/build_dashboard.py \
  --mapping /path/to/house-entities.json \
  --output /path/to/heating-dashboard.json
```

Start from [`dashboard-mapping.example.json`](dashboard-mapping.example.json).
Required keys are `REQUIRED` in the generator; any card whose entity is not
mapped is omitted. Optional keys: `inlet`, `outlet`, `defrost`, `live_power`
(falls back to `power`), `energy`, `energy_daily`, `energy_monthly`, `cop`,
`carnot`, `thermal`, `lift`, `economizer`, `tank`, `tank_target`,
`water_heater`, `heater1`, `heater2`, `quiet`, `disinfection_status`,
`disinfection_mode`, `disinfection_run`, `disinfection_cancel`,
`planner_status`, `ac_status`, `ac_mode`, `ac_climate`, `ac_power`,
`ac_energy`, `prediction`, `samples`, `error`, `hacs_update`.
