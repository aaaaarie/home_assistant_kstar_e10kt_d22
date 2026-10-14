# Tomorrow's comparison plan

Keep a local worksheet or screenshots for seven comparison rows, observed when
up, around midday and after sunset. Enter HA / app together where available;
screenshots can use the app's own terminology/layout. Alarm details are needed
only if something is present. Worksheets are working notes and are not versioned.

SoC, battery power and battery temperature are already sufficiently checked for
this exercise. Skip missing app values and exact timing. The fuller map below is
our backlog, not a requirement to fill every measurement.

Use the current focused draft (19 entities). These changes are local until pushed;
then use HACS Redownload and restart HA. Keep `sensor.kstar_lan_*` excluded from
Recorder while testing. Live values still work, but save screenshots/notes because
HA is not retaining the comparison history. Do not add provisional counters to the
Energy dashboard or feed them into energy helpers yet.

The focused validation build enables all 19 overview entities automatically.
Previously integration-disabled candidates are enabled on entry setup; explicit
user disables remain in place. Out-of-scope registrations are removed automatically. All readings share
at most 17 bounded requests each 60-second interval. Check Recorder exclusions
still cover any manually renamed IDs.

## Full overview and what to compare

All listed KSTAR entity IDs start with `sensor.kstar_lan_`; suffixes are below.

| Wanted measurement | Evidence / HA entities | What the user should check |
| --- | --- | --- |
| Battery SoC | Known; `battery_soc` | HA versus app at each interval |
| Signed battery power | Discharge matched; `battery_power` | Positive in discharge, provisionally negative in charge |
| Battery charging power | Assumed; `battery_charging_power` | Positive magnitude during app-confirmed charging, otherwise zero |
| Battery discharging power | Discharge matched; `battery_discharging_power` | Positive magnitude during discharge, otherwise zero; both components share one raw sample |
| Charged/discharged battery energy | Candidates; `battery_total_charge`, `battery_total_discharge` | Compare app lifetime counters and changes from morning to evening; note units and rounding |
| Grid import/export W and kWh | Existing P1 device; no duplicate KSTAR grid sensors | Capture P1 readings and units as context, including direction; this validates the grid source separately |
| Whole-house consumption W | Candidate phase sum; no aggregate entity yet | Capture app consumption; mapping work remains before HA comparison |
| House/load consumed energy | Candidate; `house_energy` | Compare same-scope app lifetime total and changes, not daily/monthly values |
| AC_PV W | Needed, address unresolved; no entity | Capture app AC_PV at each interval, especially daylight; these observations alone do not identify a register |
| AC solar energy kWh | Needed, counter unresolved; no entity | Capture app AC-specific totals if exposed and note their period |
| DC PV power, future direct wiring | Candidates; `pv1_power`, `pv2_power` | Expect zero while KSTAR DC inputs have no panels; nonzero scale validation waits for actual DC production |
| Generic PV energy | Candidate; `pv_total_energy` | Capture app PV counter and whether it changes during AC production while DC inputs remain zero; scope may remain unresolved |
| Battery temperature | Candidate; `battery_temperature` | Compare the app's displayed temperature and identify its scope if shown |
| Other temperatures | Reference-only; app has no matching measurements | Omitted from comparison checklist; no independent app verification available |
| Operating/system codes | Candidates; `system_status`, `inverter_status`, `dcdc_status` | Record alongside app operating state; older DCDC lookup says 2 charging / 3 discharging / 0 standby |
| Alarm/fault masks | Candidates; `alarm_flags`, `fault_flags` | Record numeric value and `raw_hex` / `active_bits` attributes; compare app's active alarms/codes and levels |
| Named/extended system alarms | Manual definitions; binding/coverage incomplete | Capture naturally present messages; no named HA mapping yet |
| Combined BMS alarm/protection/fault status | Needed; register mapping incomplete | Capture naturally present app BMS messages without needing individual-pack entities in HA |

## Observation intervals

Use the workbook when convenient: after getting up (even if solar is already up),
around midday and after sunset. Note time and battery direction in the top row.
Take HA and app readings close together. No extra early-morning observation is
needed. Capture counters, AC_PV and house power; omit temperatures the app does not expose. Alarm details matter only when naturally present.

Counter comparison should use differences between the same two times as well as
absolute readings. A coarse counter may not change over a short observation; that
does not establish that its mapping is wrong or correct. Do not induce an alarm,
reset counters or alter battery controls for these checks.

If an alarm is present, capture what is already shown; this telemetry exercise
is not a replacement for the manufacturer's troubleshooting instructions. Zero
masks do not establish comprehensive alarm coverage or system safety.
