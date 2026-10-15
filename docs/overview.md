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
| AC PV power (W) | Candidates 3092 / 3327 / 3427, U16 assuming ×1 W | 3092 has earlier near-app comparisons; others are weaker numeric matches | Three enabled sensors named “AC PV candidate [address]”; compare with Sync AC_PV |
| AC PV energy (kWh) | Unknown | Register mapping needed | Missing |
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
216 set aside as settings/control, metadata or internal-use fields. Filter:
raw 60–100, excluding identified measurements. Shortlist: 3092 (83), 3327 (100),
3427 (90). Older map: 3092/3327 reserved; 3427 unspecified among grid-support
settings, so both new candidates are weaker and may be constants. Earlier
3092 readings 87–89 agreed with app 88–93, but remained 83 after app 65–67.
Compare all three during daylight; nighttime app AC_PV is not established as
actual solar production. No mappings promoted.

23 overview entities including three temporary AC PV candidates, enabled by default;
explicit user disables respected.
Obsolete registrations are removed on setup. Plain HA names; IDs retain
`sensor.kstar_lan_` for Recorder exclusion. One shared client/coordinator,
at most 21 reads per interval, each bounded to 16 words.

Unavailable values stay unavailable. Zero alarm masks do not establish system
safety or complete alarm coverage. No invented severity or code mappings.

Remaining checks are in the table. Next capture: existing overview registers
plus 3144–3146, with decoded values and corresponding raw words in one result.
Compare total load, status and alarm flags with Sync during natural charging and
discharging. Accepted readings need no repeat campaign. Capture scope must be
agreed before hardware reads; AC PV/BMS additions require documented addresses.

Sources and mapping detail: [registers](registers.md), [alarms](alarms.md).
