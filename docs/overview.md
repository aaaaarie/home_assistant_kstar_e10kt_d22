# System overview

One KSTAR system: energy flows, counters, temperatures and alarms.
P1 supplies grid measurements. AC PV uses the existing external inverter;
direct DC PV is not connected yet. Read-only LAN monitoring.

Addresses are zero-based FC04. Multiword tuples below are high-word first.
Accepted means sufficient agreement for this installation.

| Measurement | Register / decoding | Finding | HA |
| --- | --- | --- | --- |
| Battery SoC (%) | 3066 ×0.1 | Accepted; matches Sync | Enabled |
| Signed battery power (W) | 3065, S16 | Accepted; positive discharge, negative charge | Enabled |
| Charging / discharging power (W) | max(−3065, 0) / max(3065, 0) | Accepted in both directions | Enabled |
| Battery charged / discharged energy (kWh) | (3299, 3300) / (3292, 3293), U32 ×1 | Accepted; totals match Sync; observed whole-kWh steps | Enabled |
| Grid import/export power and energy | Existing P1 entities | P1 is the grid source | Existing P1 |
| Total house power (W) | Sum 3144–3146, three U16 ×1 | Published phase loads; total needs comparison with Sync | Implemented locally |
| Load consumed energy (kWh) | (3152, 3153), U32 ×0.1 | Accepted accumulated consumption; changes agree within 0.1 kWh; lifetime/reset scope unconfirmed | Enabled |
| AC PV power (W) | House − battery + grid export-signed sum − DC PV | Calculated estimate; compare with Sync | Enabled; rejected candidates removed |
| AC PV energy (kWh) | Counter changes: load + battery charge − battery discharge + export − import − DC PV | Calculated estimate; starts at zero from a common baseline | Enabled; persistent total |
| Future DC PV1 / PV2 power (W) | 3024 / 3025, S16 ×1 | Accepted published mappings for this build; inputs unconnected | Enabled |
| DC PV energy (kWh) | (3041, 3042), U32 ×0.1 | Accepted as DC energy by agreement; not a nonzero live comparison | Enabled |
| Battery temperature (°C) | 3067, S16 ×0.1 | Accepted; matches Sync; pack/aggregate scope unspecified | Enabled |
| Inverter / battery radiator / chassis temperature (°C) | 3055 / 3056 / 3057, S16 ×0.1 | Published; plausible readings; no matching Sync fields | Enabled |
| System / inverter / DCDC status | 3046 / 3047 / 3048 | Raw codes; meanings need comparison with operating state | Enabled |
| Alarm / fault flags | (3049, 3050) / (3051, 3052), U32 | Raw masks available; D22 meanings and coverage incomplete | Masks, hex, active bits |
| Named alarms and severity | Incomplete mapping | D22 manual categories exceed older map coverage | Missing |
| Combined BMS alarm/protection/fault status | Unknown | Documented register mapping needed | Missing |

Comparison measurements, 15 October 2026. Pairs are HA / Sync; energy in kWh.

| Time | SoC (%) | Battery temperature (°C) | Charged / discharged totals, both sources | HA load total / Sync daily load |
| --- | --- | --- | --- | --- |
| 00:02–00:03 | 30 / 30 | 20.9 / 20.9 | 1 / 4 | 5.10 / 0.0 |
| 13:10–13:11 | 26 / 26 | 21.8 / 21.8 | 2 / 6 | 9.10 / 3.9 |
| 18:17–18:18 | 50 / 50 | 24.0 / 24.0 | 5 / 7 | 11.50 / 6.3 |
| 19:12 | 37 / 37 | 23.4 / 23.4 | 5 / 8 | 13.10 / 8.0 |

Battery power HA / Sync: discharge 363 / 368 W, charging 1125 / 607 W,
discharge 1226 W / 1.2 kW, discharge 480 / 495 W. Differences are accepted
as normal refresh/solar variation. Use Sync real-time counters for comparisons;
its chart lags and showed inconsistent daily values around midnight.

AC_PV search coverage: 225 of 441 slots in 3000–3440 read successfully;
216 set aside as settings/control, metadata or internal-use fields. Raw 60–100
filter produced 3092, 3327 and 3427; daytime comparison rejected all three.
Experiment stopped. Sync's nighttime AC_PV meaning remains unresolved.

AC PV calculations use internal FC04 grid power 3100 / 3104 / 3108 (S16,
positive export), import energy (3114, 3115) and export energy (3121, 3122)
(U32 ×0.1 kWh). No P1 dependency or additional grid entities. DC PV remains
directly measured and is subtracted from the balances for future direct wiring.
Grid sign reference: [KSTAR integration discussion](https://github.com/davidrapan/ha-solarman/discussions/886).

Calculated power is limited to a minimum of zero. Energy uses counter deltas,
not sampled power. Its common baseline and accumulated result persist across
restarts; source resets establish a new baseline and skip the reset interval.
Signed corrections are retained internally; the displayed counter is its
nonnegative high-water mark. Whole-kWh battery steps can advance the total early
or hold it flat until corrections catch up. Conversion losses can bias both
estimates. Missing inputs produce unavailable results without changing baselines.

22 overview entities, enabled by default; explicit user disables respected.
Obsolete registrations are removed on setup. Plain HA names; IDs retain
`sensor.kstar_lan_` for Recorder exclusion. One shared client/coordinator,
at most 23 reads per interval, each bounded to 16 words. Calculation dependencies
are read even if their individual entities are disabled; internal grid reads stop
when both AC PV entities are disabled.

Unavailable values stay unavailable. Zero alarm masks do not establish system
safety or complete alarm coverage. No invented severity or code mappings.

Next comparison: House power versus Sync Load, AC PV power versus Sync AC_PV,
and calculated AC PV energy changes over a day. Allow normal refresh differences.
Keep Recorder exclusions during comparison; enable recording when accepted.
Hardware snapshots require separately agreed scope.

Sources and mapping detail: [registers](registers.md), [alarms](alarms.md).
