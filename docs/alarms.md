# Alarm evidence and coverage gaps

[Official E10KT-D22 manual, January 2026, version 1.0](https://www.kstarnewenergy.com/DOWNLOADS/E10KT-D22%20Series%20User%20Manual%20KSTAR%20%28English%20version,%20adapted%20for%20BP48100PF1-G2%20battery%20pack%29.pdf),
section 8.3, printed pages 119–128 (PDF pages 123–132).

The manual distinguishes system error codes (`F…`), system alarm codes (`W…`),
and separate BMS alarm, protection and fault bit tables. These are useful semantic
references; they do not by themselves identify LAN addresses or the app's levels.

Cross-check with the older [Modbus protocol](https://www.scribd.com/document/1021396207/KSTAR-Hybrid-Inverter-Modbus-V2-9-1-2024-07-21):

- The D22 manual includes `W32`, beyond the old 32-bit warning mask's positions 0–31.
- `W29` has different meanings: grid synchronization in the D22 manual, versus
  clock failure in the older protocol. Blindly copying the old labels would mislead.
- The same BMS bit position can mean different things in the alarm/protection/fault
  tables. Identify the source register/category before attaching a description.

Current code exposes optional raw masks at 3049–3052, without named messages or
severity claims. Complete D22 coverage, extended codes and BMS register bindings
remain unresolved. A combined system safety overview may summarize BMS sources
without exposing individual-pack entities, but must preserve unknown/unavailable
states. No intentional fault triggering or device writes are part of validation.

The manual is linked, not redistributed. The operating mode and actual installed
battery variant should be recorded when checking applicability.
