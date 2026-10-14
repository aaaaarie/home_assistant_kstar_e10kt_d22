# Device observations

These are read-only snapshots, not semantic validation. Record simultaneous app
comparisons here before promoting reference-only sensors. All requests below used
FC04, unit ID 1 and zero-based wire addresses. Words are in ascending wire order.

## 2026-10-14, 19:35:47–19:35:49 Europe/Amsterdam

| Measurement | Address(es) | Raw decimal words | Reference interpretation |
| --- | --- | --- | --- |
| Battery SoC | 3066 | 510 | 51.0% |
| Battery voltage | 3063 | 5160 | 51.60 V |
| Battery current | 3064 | 80 | +8.0 A |
| Battery power | 3065 | 412 | +412 W |
| Battery temperature | 3067 | 209 | 20.9 °C |
| DCDC status | 3048 | 3 | Older reference lookup: discharging mode |
| Lifetime charged energy | 3299–3300 | 0, 1 | Candidate U32 high-first ×1: 1 kWh |
| Lifetime discharged energy | 3292–3293 | 0, 1 | Candidate U32 high-first ×1: 1 kWh |

Voltage × current is 412.8 W, close to the power reading. This is internal
consistency, not independent validation of units. Status code 3 suggests
positive power corresponds to discharge under the older reference; the D22 app
must confirm it, followed by a sample in the opposite direction.

Energy counters remain uncertain: both were 1 under the reference interpretation.
Zero high words do not independently establish word order or units.

KSTAR Sync comparison supplied by the user: SoC **51.0%**, battery power
**+422 W**, and **discharging**. SoC matches exactly. The 10 W power difference
is consistent with sample timing/load changes, but that cause is not established.
This supports the power register's watt scale and positive-discharge direction
in this operating state. A negative-power charging sample is still needed.
Voltage, current, temperature and lifetime counters have no independent app
comparison yet. No verification flags changed from this snapshot.


## 2026-10-14, 19:39:08 Europe/Amsterdam — operating mode

The user reported KSTAR Sync Op Mode **Self-consumption**. A single FC04 read of
wire address **3044** returned **0**, matching the older reference lookup's
self-consumption mode. This is one matched state; other mode codes remain
unverified. No setting was changed. There is no operating-mode entity in the
current integration draft yet.

Charging validation is deferred until natural charging occurs; the user expects
this after sunrise under the current settings. No scheduling or control action
is authorized or needed for that validation.


## Provisional implementation decision

The user requested assuming charging behavior and checking it later in HA.
Signed power at 3065 is treated as positive discharge / negative charge, with
separate nonnegative components. All three power entities are enabled by default
and labeled assumed. No negative charging sample has been observed yet. Their
verification flags remain false. The components share a single raw read per poll.
