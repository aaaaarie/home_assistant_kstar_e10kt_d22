# KSTAR LAN

Local, read-only Home Assistant monitoring for a KSTAR BlueSpark E10KT-D22 battery/inverter over **direct Modbus TCP**. No Solarman logger framing, cloud account, controls, scheduling or write commands. Frank Energie remains responsible for battery control.

Requires Home Assistant **2026.10.0 or newer**. The tested target is Core 2026.10.0 and its `pymodbus==3.13.1` dependency. A newer Core release that changes the PyModbus pin may require an integration update.

## Current support

One device, with **48 sensor definitions**:

- Battery SoC and raw model code enabled by default, verified on the local device.
- Signed battery power, charging power and discharging power enabled by default, explicitly marked **assumed** until charging direction is checked.
- Optional battery voltage, signed current/power, temperatures, charged/discharged energy totals and raw status codes.
- Optional grid and inverter R/S/T voltage, current, frequency and power; per-phase load power; grid import/export and load energy totals.
- Optional DC PV power; these are not the separate Huawei inverter's AC PV production.

Other optional sensors include **“unverified”** in their names and are disabled by default. Disabled sensors are **not polled**. A register responding successfully does not establish that its meaning, scale or direction matches the D22. Enable a few candidates at a time and compare them with KSTAR Sync and independent measurements before using them in automation or energy statistics.

**AC_PV remains unidentified.** It is not exposed under a guessed address or substituted with battery charging power. Grid import/export power splits and a total house-power sensor await verification of phase coverage and direction. The integration exposes their reference per-phase measurements instead. See [register provenance and limitations](docs/registers.md).

## Install through HACS

1. In HACS, open the menu → **Custom repositories**.
2. Add `https://github.com/aaaaarie/home_assistant_kstar_e10kt_d22` with category **Integration**. The implementation must first be pushed to that repository; local changes are not available through HACS.
3. Download **KSTAR LAN**, then restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration → KSTAR LAN**.
5. Enter host `192.168.178.238`, port `502`, unit ID `1` (or your device's values).

This is a custom HACS repository, not a claim of inclusion in the HACS default catalog.

## Manual installation

Copy `custom_components/kstar_lan/` into `/config/custom_components/kstar_lan/`, or extract the generated `dist/kstar_lan.zip` into `/config/`. Check that `manifest.json` is directly in `/config/custom_components/kstar_lan/` with no extra enclosing folder. Restart Home Assistant and add the integration in the UI. No YAML configuration is required.

Setup checks FC04 registers 3045 and 3066. Invalid SoC or rejected required registers produce an unsupported-device error. Two valid responses establish compatibility with this profile, not cryptographic manufacturer identification. Model code 40 is kept numeric; it is not translated using an older model lookup.

## Keep testing data out of Recorder

Every new entity defaults to `sensor.kstar_lan_<measurement>`, for example
`sensor.kstar_lan_battery_charging_power`. To test live readings without accumulating
history or long-term statistics, merge this into `configuration.yaml` before
adding the integration and restart Home Assistant:

```yaml
recorder:
  exclude:
    entity_globs:
      - sensor.kstar_lan_*
```

Merge into any existing `recorder:` block rather than adding a second one. Remove
the exclusion and restart when you want recording to begin. This does not delete
previous data. HA preserves existing or manually renamed entity IDs; those need
to match the prefix or be excluded separately. Collision suffixes such as `_2`
still match the pattern. Live sensor values remain available during exclusion.

## Polling and optional entities

Default polling is **60 seconds**; **Configure** on the integration allows 30–3600 seconds. Requests share one serialized connection. Each enabled definition reads only its own one- or two-word range, never more than 16 words. The default sends three requests per interval for five entities. The three battery power entities share the same register read and sample. All 48 entities enabled would send at most 46 requests per normal interval; leave unnecessary candidates disabled.

Enable an optional sensor under the device's entities, including disabled entities, then open its settings and enable it. Allow Home Assistant to reload the entry and/or wait one polling interval. A rejected range is unavailable and is retried after **10 minutes**, preserving other sensors. A transport failure makes all entities unavailable and the coordinator reconnects on a later refresh. No stale sample is advertised as available.

Energy sensors have `energy` device class and kWh units. Battery lifetime counters use the reference's `total_increasing`; grid and load counters preserve its `total` state class. These are valid Home Assistant statistics types, but the counters' scale, word order and reset behavior still need D22 validation before adding them to the Energy dashboard. Do not use daily/monthly counters as lifetime totals. Battery power is provisionally interpreted as positive for discharge and negative for charge: `discharging = max(power, 0)`, `charging = max(-power, 0)`. A discharge sample matched KSTAR Sync; charging is assumed from the signed reference map at the user's request. When Sync shows charging, check that signed power is negative, charging power is positive and discharging power is zero. At idle both components should be near zero. These are power measurements, not verified energy totals and not AC_PV. Existing HA entries may retain a previously disabled signed-power entity; enable it manually if desired.

## Update and troubleshoot

Use HACS updates, or replace the integration folder manually, then restart Home Assistant. Keep the existing config entry to retain entity identifiers. Reserve the inverter's DHCP address: this release identifies an endpoint by normalized host, TCP port and unit ID. Hostname and IP aliases can create duplicates; address changes require removing/re-adding the entry in this release.

If setup fails, check LAN routing from **Home Assistant itself**, TCP port 502, unit ID, and concurrent client limits. A working test on a laptop does not guarantee HA network access. If communication drops when other software connects, increase the interval and check whether the inverter permits simultaneous clients. Do not change Frank Energie's settings to troubleshoot this integration.

For unavailable optional entities, check downloaded diagnostics for `register_rejected`, `register_rejected_backoff` or `invalid_value`. Rejected addresses can indicate firmware/profile differences. Do not change all addresses by ±1: 3045 and 3066 have been confirmed as zero-based wire addresses on this installation. Zero is a valid sensor value; it is not treated as missing.

Download diagnostics from the integration menu. It contains only measurement keys, raw words, decoded values, update health and sanitized error codes. It omits IP, host, port, unit ID, device identifiers and serial numbers. For temporary debug logging:

```yaml
logger:
  logs:
    custom_components.kstar_lan: debug
```

PyModbus debug logging can expose connection details; review logs before sharing them.

## Development and validation

Use Python **3.14.2+**, matching Core's minimum:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m pytest
.venv/bin/ruff check custom_components tests
.venv/bin/ruff format --check custom_components tests
python3 scripts/package.py
```

Tests run against actual Home Assistant 2026.10.0 classes with a mocked Modbus transport. A suite-wide guard blocks network connections. The in-process integration test runs the real config and options flows, serializes their forms through HA's HTTP helper, checks duplicate detection, loads the sensor platform, verifies one device and applies a polling interval change through an entry reload. They cover unsigned/signed decoding, multiword order, bounds, malformed replies, failed connections, serialization, registry enable/disable, unavailable sensors, rejected-register backoff, recovery, config validation, duplicate handling, options, diagnostics and connection lifecycle. CI repeats tests/lint and creates an installable archive. These checks establish software behavior; they do not validate candidate register meanings or replace HA OS/UI testing.

A limited live smoke test on 2026-10-14 using the actual `KstarClient` and PyModbus 3.13.1 returned model `[40]` and SoC `[530]` (53.0%). The earlier user measurement `[550]` (55.0%) matched KSTAR Sync. Other definitions have not been live-validated. Full installation and UI behavior on HA OS remain to be checked on the user's instance.
