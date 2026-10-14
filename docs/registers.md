# Register evidence and remaining gaps

All addresses in the implementation are **zero-based wire addresses**, with **FC04** input-register reads. We do not subtract one. Holding register 0 was previously reported working via FC03, but is not needed for polling or configuration.

## Sources reviewed on 2026-10-14

- [Solarman KSTAR register map](https://github.com/StephanJoubert/home_assistant_solarman/blob/fe261ddfb03821c29580dbc8ddbfb81ef130041d/custom_components/solarman/inverter_definitions/kstar_hybrid.yaml), last map-change commit `fe261ddfb03821c29580dbc8ddbfb81ef130041d`. Its header attributes the map to KSTAR MODBUS RS485 Communication Protocol V2.5. This is a reference for numeric facts, not evidence that a Solarman transport works on direct TCP or that every register fits D22.
- [Solarman decoder](https://github.com/StephanJoubert/home_assistant_solarman/blob/main/custom_components/solarman/parser.py). It lists multiword addresses from **least to most significant**. Our declarative `words` tuples list them in **most to least significant** order, with the lower wire address holding the high word. Standard two's-complement signed decoding is used; the old parser's subtraction of 65535 rather than 65536 is not reproduced.
- [KSTAR Hybrid Inverter MODBUS RS485 Communication Protocol V2.9.1, dated 2024-07-21](https://www.scribd.com/document/1021396207/KSTAR-Hybrid-Inverter-Modbus-V2-9-1-2024-07-21), document SFT-KSE-001. This is a publicly uploaded **third-party-hosted** copy of a KSTAR-authored document, not a verified D22-specific publication. Table 3.1.1 supplies S/T phase references and clarifies that 3100 and 3144 are R-phase measurements. D22 applicability remains unverified. No document is redistributed here.
- [wills106 SolaX Modbus repository](https://github.com/wills106/homeassistant-solax-modbus) and its [KSTAR support discussion #932](https://github.com/wills106/homeassistant-solax-modbus/discussions/932). The checked main tree contained no KSTAR plugin; the discussion requests support and links the same Solarman reference. Its other inverter maps are not interchangeable with KSTAR.
- [Official E(4–12)KT-D22 installation and operation manual](https://www.kstarnewenergy.com/DOWNLOADS/INSTALLATION%20AND%20OPERATION%20MANUAL%20for%20E%284-12%29KT-D22%20ESS.pdf), sections 3.10.2 and 4.4.9. It documents AC-coupled installations and third-party EMS through RS485. It does not establish the AC_PV telemetry register. No control settings from the manual are implemented.
- [Core 2026.10.0 Modbus manifest](https://github.com/home-assistant/core/blob/2026.10.0/homeassistant/components/modbus/manifest.json) establishes the `pymodbus==3.13.1` pin. Our client uses its keyword-only `count` and `device_id` API.

## Confirmed device reads

| Function | Wire address | Reported raw value | Interpretation |
| --- | --- | --- | --- |
| 03 | 0 | 1 (user test) | Connectivity only; unused by integration |
| 04 | 3045 | 40 (user and live client tests) | Numeric model code; model lookup unverified |
| 04 | 3066 | 550 (user); 530 (live client, 2026-10-14) | ×0.1 = 55.0% / 53.0%; user matched 55.0% with Sync |

Only model-code readability and SoC are marked device-verified. Model code 40 is absent from the older Solarman lookup; that lookup must not label this device. The device's display name is based on the hardware supplied by the user.

## Reference conflicts and AC_PV

Solarman assigns 3100 to both “Total Grid Power” and R-phase power, and 3144 to total consumption. The newer protocol describes both as R-phase values. This integration labels them per phase and does not use them as household or grid totals.

The reviewed sources do not identify a D22 AC_PV power register. Register 3259 in the older protocol is an **AC-coupling enable setting**, not AC-side generation power, and is not queried. DC PV1/PV2 power at 3024/3025 may correctly remain zero with a separate Huawei inverter. Battery power at 3065 cannot identify solar production: charging can originate from solar or grid.

Next evidence needed: a KSTAR-issued telemetry map for the installed D22 firmware, specifically AC-side generation power, sign convention and aggregate grid/load measurements. Once a documented candidate exists, compare a small fixed read against simultaneous KSTAR Sync AC_PV and Huawei output in daylight and at night, with battery charging and discharging and grid import/export. Do not sweep arbitrary register ranges, change device settings or infer AC_PV solely from energy balance.

## Candidate verification

Enable a small set of entities, download diagnostics and record firmware, raw words, time and simultaneous reference readings. For battery and grid power, verify both directions and near-zero readings; positive discharge at 3065 has an app comparison; negative charge is now provisionally assumed at the user's request. Other power directions are unverified. For energy totals, verify high/low words, units, changes across a known energy transfer and reset behavior. Zero-valued high words alone cannot establish a 32-bit interpretation. Code sensors retain numeric values because the older status lookup may not describe D22 firmware accurately.

The implementation applies only broad sanity bounds to SoC and temperatures. A plausible value does not validate a mapping. Evidence status stays in the overview table; HA names and attributes do not mark verification. All wanted sensors are enabled for validation.

## D22 alarm manual evidence

The official D22 manual supplied by the user provides system/BMS code categories
and reveals gaps in the older protocol. See [alarm evidence](alarms.md). These
descriptions do not independently establish every LAN register binding.

## Reference inventory and current scope

Only the 19 overview definitions remain in code. Model-code readability is still
checked during configuration, without creating a model-code entity. All overview
entities are enabled for validation; enabling does not establish register correctness.

Words are listed high first; wire requests use ascending addresses. All use FC04.
Multiword interpretations and alarm bit meanings still need D22 verification.

| Key | Words (high first) | Decode | Unit |
| --- | --- | --- | --- |
| `battery_soc` | 3066 | U16 ×0.1 | % |
| `battery_power` | 3065 | S16 ×1 | W |
| `battery_charging_power` | 3065 | charging component of signed W | W |
| `battery_discharging_power` | 3065 | discharging component of signed W | W |
| `battery_temperature` | 3067 | S16 ×0.1 | °C |
| `battery_total_discharge` | 3292, 3293 | U32 ×1 | kWh |
| `battery_total_charge` | 3299, 3300 | U32 ×1 | kWh |
| `house_energy` | 3152, 3153 | U32 ×0.1 | kWh |
| `inverter_temperature` | 3055 | S16 ×0.1 | °C |
| `battery_radiator_temperature` | 3056 | S16 ×0.1 | °C |
| `chassis_temperature` | 3057 | S16 ×0.1 | °C |
| `system_status` | 3046 | U16 ×1 | — |
| `inverter_status` | 3047 | U16 ×1 | — |
| `dcdc_status` | 3048 | U16 ×1 | — |
| `pv1_power` | 3024 | S16 ×1 | W |
| `pv2_power` | 3025 | S16 ×1 | W |
| `pv_total_energy` | 3041, 3042 | U32 ×0.1 | kWh |
| `alarm_flags` | 3049, 3050 | U32 ×1 | — |
| `fault_flags` | 3051, 3052 | U32 ×1 | — |
