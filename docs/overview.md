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
| Battery lifetime charged / discharged energy (kWh) | (3299, 3300) / (3292, 3293), U32 ×1 | Earlier totals matched Sync; too coarse for small transfers | Diagnostics only |
| Daily battery charged / discharged energy (kWh) | 3301 / 3294, U16 ×0.1 | Used by agreement; raw 3 / 0 gives 0.3 / 0.0 kWh; Sync reported 0.1 / 0.0 kWh | Enabled; new entity IDs |
| Grid import/export power and energy | Existing P1 entities | P1 is the grid source | Existing P1 |
| Total house power (W) | Sum 3144–3146, three U16 ×1 | Reported spikes near 200 kW; decoding/validity unresolved | Enabled; unreliable during spikes |
| Load consumed energy (kWh) | (3152, 3153), U32 ×0.1 | Accepted accumulated consumption; changes agree within 0.1 kWh; lifetime/reset scope unconfirmed | Enabled |
| AC PV power (W) | House − battery + grid export-signed sum − DC PV | Inherits house-power spikes; calculated estimate needs validation | Enabled; unreliable during spikes |
| AC PV energy (kWh) | Counter changes: load + daily battery charge − daily battery discharge + export − import − DC PV | Calculated estimate; common baseline within each local day | Enabled; persistent total |
| Future DC PV1 / PV2 power (W) | 3024 / 3025, S16 ×1 | Accepted published mappings for this build; inputs unconnected | Enabled |
| DC PV energy (kWh) | (3041, 3042), U32 ×0.1 | Accepted as DC energy by agreement; not a nonzero live comparison | Enabled |
| Battery temperature (°C) | 3067, S16 ×0.1 | Accepted; matches Sync; pack/aggregate scope unspecified | Enabled |
| Inverter / battery radiator / chassis temperature (°C) | 3055 / 3056 / 3057, S16 ×0.1 | Published; plausible readings; no matching Sync fields | Enabled |
| System / inverter / DCDC status | 3046 / 3047 / 3048 | Raw codes; meanings need comparison with operating state | Enabled |
| Alarm / fault flags | (3049, 3050) / (3051, 3052), U32 | Raw masks available; D22 meanings and coverage incomplete | Masks, hex, active bits |
| Named alarms and severity | Incomplete mapping | D22 manual categories exceed older map coverage | Missing |
| Combined BMS alarm/protection/fault status | Unknown | Documented register mapping needed | Missing |

House and AC PV power are reported jumping between zero and roughly 200,000 W.
The U16 phase-sum decoder accepts (65535, 65535, 65535) as 196,605 W, its maximum;
(65500, 65500, 65500) gives 196,500 W. This reproduces the reported scale in
software, not the device's actual raw sample. Negative S16 values decoded as U16
or invalid device words are possible explanations. V2.9.1 lists 3144–3146 as U16;
switching to signed decoding is not yet justified. Raw words from a spike and
simultaneous Sync Load/AC_PV are needed. AC PV power's existing minimum-zero
clamp can also hide a negative balance; there is no explicit upper clamp.
Power readings do not feed the separate AC PV energy counter calculation.
Diagnostics retain five recent power polls and five house-phase high-bit polls,
with UTC read-window timestamps, raw words and decoded calculation inputs. The
high-bit condition is a capture trigger, not evidence of signedness or invalid
data. Normal polling supplies all samples; there are no extra device reads.
The bounded in-memory history survives normal polls and transport failures but
clears on integration reload/restart. A later diagnostic download can therefore
capture a prior spike without manually synchronizing HA and Sync.

Battery charged/discharged and calculated AC PV energy are reported unchanged
since 16 October 2026, 17:31, despite observed charging and substantial AC PV
power. Recorder exclusions have been removed; live entity states are also flat.
Earlier counter comparisons do not establish current operation. Supplied HA
diagnostics show a successful 60-second poll with no errors: raw battery counters
(0, 6) charged / (0, 13) discharged decode to 6 / 13 kWh. Battery power is 0 W,
SoC 12%, load energy 28.6 kWh, grid import/export 10 / 1.7 kWh, DC energy 0 kWh,
calculated AC PV power 272 W and AC PV energy 0.3 kWh. The file has no sample
timestamp. There is no raw/decoded mismatch in this sample; simultaneous Sync
totals and a later sample spanning a known battery transfer would establish
whether the old totals track current app totals.
Unchanged HA state timestamps alone do not establish stopped polling.
Diagnostics now include the persisted AC PV accumulator's previous counters,
signed balance and displayed total so a balance below its prior peak is visible.
The DC PV energy entity is named “DC PV generated energy”; it does not include
the external AC inverter's generation.

The user reports Sync showing 0.1 kWh charged while the total counter stays
unchanged. Protocol V2.9.1 table 3.1.1 distinguishes whole-kWh battery totals
from 0.1-kWh daily counters at 3301 (charge) and 3294 (discharge). Bounded FC04
reads on 17 October 2026 at 12:15:51 Europe/Amsterdam returned raw 3 / 0,
interpreted as 0.3 / 0.0 kWh. The preceding user Sync report was 0.1 / 0.0 kWh;
elapsed charging or app refresh delay could explain the difference but is not
established. These remain candidates; Sync's use of these particular registers
is unconfirmed. Sync still showed 0.1 kWh after a reported four-percentage-point
SoC gain on a 10 kWh battery (roughly 0.4 kWh). The daily mappings are used by
agreement, without treating this discrepancy as independent validation.

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
not sampled power. Its common baseline, local date, signed balance and total
persist across restarts. Same-day gaps retain counter changes. A different local
date or any decreasing source establishes a fresh common baseline and skips the
ambiguous interval; day-end energy between polls and gaps spanning midnight cannot
be recovered. A poll crossing midnight makes AC PV energy unavailable until the
next complete sample. This avoids interpreting daily resets as solar production.
Upgrade from lifetime battery inputs preserves the published AC PV total, clears
the old baseline and starts its balance at that total. Signed corrections are
retained thereafter; the displayed counter is the nonnegative high-water mark.
The 0.1 kWh steps and conversion losses can still delay or bias the estimate.
Missing inputs produce unavailable results without changing baselines.

Daily battery entities expose device readings directly as `total_increasing`;
HA handles their resets. They replace the old lifetime battery registrations with
new IDs, so old statistics are not reinterpreted. Diagnostics retain raw lifetime
totals; a lifetime register failure does not block daily energy or AC PV energy.

22 overview entities, enabled by default; explicit user disables respected.
Obsolete registrations are removed on setup. Plain HA names; IDs retain
`sensor.kstar_lan_` for Recorder exclusion. One shared client/coordinator,
at most 25 reads per interval, each bounded to 16 words. Calculation dependencies
are read even if their individual entities are disabled; internal grid reads stop
when both AC PV entities are disabled.

Unavailable values stay unavailable. Zero alarm masks do not establish system
safety or complete alarm coverage. No invented severity or code mappings.

Next comparison: House power versus Sync Load, AC PV power versus Sync AC_PV,
and calculated AC PV energy changes over a day. Allow normal refresh differences.
Energy dashboard inputs must be included in Recorder.
Hardware snapshots require separately agreed scope.

Sources and mapping detail: [registers](registers.md), [alarms](alarms.md).
