# System overview — working evidence table

Scope: one KSTAR system device, combined battery behavior, energy distribution,
temperatures and alarms. Individual pack details, phase measurements, volts,
amps, frequency and model diagnostics are deferred. The existing P1 meter
supplies grid import/export; this integration does not connect to or copy its data.
PV monitoring covers both current AC coupling and future direct DC connection to
KSTAR. The external PV inverter brand is not an integration dependency.

“Known” is limited to the observed states. “Provisional” means published reference
and/or a plausible observation, not D22 semantic validation. A documented address
and a live match are different evidence. See `observations.md` and `registers.md`.

| Wanted measurement | Evidence now | Source / next step | Current HA behavior |
| --- | --- | --- | --- |
| Battery SoC (%) | Known: exact app matches | FC04 3066 ×0.1 | Enabled |
| Signed battery power / discharge (W) | App-matched positive discharge | FC04 3065; verify opposite direction | Enabled, assumed |
| Battery charging power (W) | Provisional: negative means charge | max(-3065, 0); compare during charging | Enabled, assumed |
| Battery charged/discharged energy (kWh) | Published counters; small values, scale/reset behavior unverified | FC04 3299–3300 / 3292–3293 | Optional, unverified |
| Grid import/export power and energy | User has another source; its entities/units not yet reviewed here | Existing P1 meter in HA; use as grid reference | KSTAR grid entities deferred |
| Total house consumption power (W) | Provisional candidate: sum of phase loads; last sample 650 W | FC04 3144–3146; confirm coverage against app | Aggregate not implemented; phase entities deferred |
| House/load energy (kWh) | Published counter; scope/scale unverified | FC04 3152–3153; compare app total and changes | Optional, unverified |
| AC solar production / AC_PV (W) | Needed; address unknown | D22 register evidence needed; app last reported 77 W | No guessed entity |
| AC solar production energy (kWh) | Needed; KSTAR AC counter unknown | Identify KSTAR AC-side counter independently of external inverter brand | Not implemented |
| DC PV1/PV2 power (W), for future direct PV wiring | Published addresses; both read zero under current wiring | FC04 3024 / 3025; verify nonzero scaling after installation changes | Optional, unverified |
| PV generated energy (kWh), future DC use candidate | Published generic PV counter; D22 DC/AC scope unverified | FC04 3041–3042 ×0.1; confirm scope and changes before labeling DC energy | Optional, unverified |
| Battery temperature (°C) | Published scalar; plausible 20.8 °C; pack/aggregate scope unconfirmed | FC04 3067; identify app's temperature scope | Optional, unverified |
| Inverter, battery radiator and chassis temperatures (°C) | Published scalars; plausible 35.8 / 36.3 / 43.6 °C | FC04 3055 / 3056 / 3057; app exposes no matching radiator/chassis values, so independent comparison is unavailable | Optional, unverified |
| Operating/system status | Published codes; observed 2 / 2 / 3 suggest grid-connected discharge | FC04 3046 / 3047 / 3048; older lookups | Optional raw codes |
| Alarm and fault flags | Published 32-bit warning/fault bitmaps; no D22 live comparison yet | FC04 3049–3050 / 3051–3052; confirm bit meanings and app severity correspondence | Optional raw masks, hex and active bit positions |
| Named alarm messages and severity levels | D22 manual defines system errors/alarms and separate BMS alarms/protections/faults; complete register mapping and app levels still unknown | Cross-check manual §8.3 with Modbus protocol, including extended codes | Raw sensors only; named mapping pending |
| Combined battery/BMS safety status | Needed; per-pack detail is not required in the overview | Identify documented BMS alarm/protection/fault registers and combine while retaining unknown states | Not implemented |

Four entities are enabled by default: SoC and three battery-power representations.
Fifteen candidate entities are optional/disabled by default. Their values remain
labeled unverified; the battery power entities remain labeled assumed.

Existing deferred entities from earlier builds are disabled during entry setup,
without removing registry records or history. New installations create only the
19 overview entities. Stable keys and the `sensor.kstar_lan_` prefix are preserved.
The complete register-reference definitions remain in code for bounded research,
but deferred definitions are not polled even if an old registry entry is enabled.

## Alarms without an app

The published protocol provides local warning and fault bitfields, allowing a
monitoring system to poll them and translate validated set bits into messages or
notifications. This implementation initially exposes only the raw unsigned mask,
hex value and active bit positions. It does not assert an app severity or claim
that a zero mask establishes system safety. Unknown/unavailable data is not
translated into an all-clear state. No automatic notification is configured.

Protocol references: [Solarman register map](https://github.com/StephanJoubert/home_assistant_solarman/blob/fe261ddfb03821c29580dbc8ddbfb81ef130041d/custom_components/solarman/inverter_definitions/kstar_hybrid.yaml),
[KSTAR-authored protocol V2.9.1, third-party-hosted copy, tables 3.1.1–3.1.3](https://www.scribd.com/document/1021396207/KSTAR-Hybrid-Inverter-Modbus-V2-9-1-2024-07-21).
Applicability and coverage of D22 firmware still need confirmation.

The [D22 manual](alarms.md) supplies code descriptions and distinguishes BMS alarm,
protection and fault categories. It also documents codes beyond the older masks;
readable raw flags do not establish full alarm coverage.

## Period energy values

Prefer validated lifetime counters for the Energy dashboard. HA statistics can
report energy usage over time from them; Utility Meter helpers can track daily,
monthly or yearly periods. Device period counters can later provide comparisons,
but are not priority entities. Power (W) and cumulative energy (kWh) must retain
different meanings. Keep the Recorder exclusion during provisional testing.

The [comparison checklist](validation.md) maps every wanted measurement to its
HA entities and the observations to collect during natural operating states.

## Next useful comparisons

1. Compare signed battery power during natural charging.
2. Confirm whether 3144–3146 cover the house's total consumption.
3. Check alarm/fault readability and map app messages when naturally present;
   do not induce a fault to validate telemetry.
4. Track counter changes over a measurable energy transfer.
5. Obtain documented KSTAR AC_PV evidence; retain the DC PV candidates for future direct PV wiring.
