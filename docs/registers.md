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

The implementation applies only broad sanity bounds to SoC and temperatures. A plausible value does not validate a mapping. Reference-only measurements remain visibly unverified and disabled by default, except the battery power entities explicitly enabled provisionally and labeled assumed.

## Implemented inventory

`words` below are in significance order (high first), not request order. Requests start at the minimum address and read contiguous ascending addresses. All rows use FC04. `U16`/`U32` are unsigned; `S16` uses two's complement. The two confirmed rows and three provisional battery power entities are enabled by default. Multiword values are candidates even though the reference word order is known.

| Entity key | Words (high first) | Decode | Unit | State class | Evidence |
| --- | --- | --- | --- | --- | --- |
| `battery_soc` | 3066 | U16 ×0.1 | % | measurement | Device |
| `model_code` | 3045 | U16 ×1 | — | — | Device |
| `battery_voltage` | 3063 | U16 ×0.01 | V | measurement | Solarman reference |
| `battery_current` | 3064 | S16 ×0.1 | A | measurement | Solarman reference |
| `battery_power` | 3065 | S16 ×1 | W | measurement | Discharge matched; charging assumed |
| `battery_charging_power` | 3065 | max(-signed power, 0) | W | measurement | Assumed |
| `battery_discharging_power` | 3065 | max(signed power, 0) | W | measurement | Assumed |
| `battery_temperature` | 3067 | S16 ×0.1 | °C | measurement | Solarman reference |
| `battery_total_discharge` | 3292, 3293 | U32 ×1 | kWh | total_increasing | Solarman reference |
| `battery_total_charge` | 3299, 3300 | U32 ×1 | kWh | total_increasing | Solarman reference |
| `grid_import_energy` | 3114, 3115 | U32 ×0.1 | kWh | total | Solarman reference |
| `grid_export_energy` | 3121, 3122 | U32 ×0.1 | kWh | total | Solarman reference |
| `load_r_power` | 3144 | U16 ×1 | W | measurement | V2.9.1 copy |
| `house_energy` | 3152, 3153 | U32 ×0.1 | kWh | total | Solarman reference |
| `grid_r_voltage` | 3097 | U16 ×0.1 | V | measurement | Solarman reference |
| `grid_r_frequency` | 3098 | U16 ×0.01 | Hz | measurement | Solarman reference |
| `grid_r_current` | 3099 | S16 ×0.001 | A | measurement | Solarman reference |
| `grid_r_power` | 3100 | S16 ×1 | W | measurement | Solarman reference |
| `inverter_r_voltage` | 3123 | U16 ×0.1 | V | measurement | Solarman reference |
| `inverter_r_current` | 3124 | S16 ×0.01 | A | measurement | Solarman reference |
| `inverter_r_frequency` | 3125 | U16 ×0.01 | Hz | measurement | Solarman reference |
| `inverter_r_power` | 3126 | S16 ×1 | W | measurement | Solarman reference |
| `inverter_temperature` | 3055 | S16 ×0.1 | °C | measurement | Solarman reference |
| `battery_radiator_temperature` | 3056 | S16 ×0.1 | °C | measurement | Solarman reference |
| `chassis_temperature` | 3057 | S16 ×0.1 | °C | measurement | Solarman reference |
| `system_status` | 3046 | U16 ×1 | — | — | Solarman reference |
| `inverter_status` | 3047 | U16 ×1 | — | — | Solarman reference |
| `dcdc_status` | 3048 | U16 ×1 | — | — | Solarman reference |
| `pv1_power` | 3024 | S16 ×1 | W | measurement | Solarman reference |
| `pv2_power` | 3025 | S16 ×1 | W | measurement | Solarman reference |
| `grid_s_voltage` | 3101 | U16 ×0.1 | V | measurement | V2.9.1 copy |
| `grid_s_frequency` | 3102 | U16 ×0.01 | Hz | measurement | V2.9.1 copy |
| `grid_s_current` | 3103 | S16 ×0.001 | A | measurement | V2.9.1 copy |
| `grid_s_power` | 3104 | S16 ×1 | W | measurement | V2.9.1 copy |
| `inverter_s_voltage` | 3127 | U16 ×0.1 | V | measurement | V2.9.1 copy |
| `inverter_s_current` | 3128 | S16 ×0.01 | A | measurement | V2.9.1 copy |
| `inverter_s_frequency` | 3129 | U16 ×0.01 | Hz | measurement | V2.9.1 copy |
| `inverter_s_power` | 3130 | S16 ×1 | W | measurement | V2.9.1 copy |
| `load_s_power` | 3145 | U16 ×1 | W | measurement | V2.9.1 copy |
| `grid_t_voltage` | 3105 | U16 ×0.1 | V | measurement | V2.9.1 copy |
| `grid_t_frequency` | 3106 | U16 ×0.01 | Hz | measurement | V2.9.1 copy |
| `grid_t_current` | 3107 | S16 ×0.001 | A | measurement | V2.9.1 copy |
| `grid_t_power` | 3108 | S16 ×1 | W | measurement | V2.9.1 copy |
| `inverter_t_voltage` | 3131 | U16 ×0.1 | V | measurement | V2.9.1 copy |
| `inverter_t_current` | 3132 | S16 ×0.01 | A | measurement | V2.9.1 copy |
| `inverter_t_frequency` | 3133 | U16 ×0.01 | Hz | measurement | V2.9.1 copy |
| `inverter_t_power` | 3134 | S16 ×1 | W | measurement | V2.9.1 copy |
| `load_t_power` | 3146 | U16 ×1 | W | measurement | V2.9.1 copy |
