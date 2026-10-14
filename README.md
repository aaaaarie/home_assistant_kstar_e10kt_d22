# KSTAR LAN

Read-only Modbus TCP monitoring for my KSTAR BlueSpark E10KT-D22:
one inverter, two battery packs, one Home Assistant device.

The overview focuses on battery/solar/house energy flows, temperatures and alarms.
My P1 meter supplies grid import/export. PV is currently AC-coupled through a
separate inverter; direct DC PV on the KSTAR is also in scope.

Tested with HA Core **2026.10.0** and **PyModbus 3.13.1**.

## Current state

- Four entities enabled by default: SoC, signed battery power, charging power and
  discharging power. SoC matches Sync; charging direction remains assumed.
- Fifteen optional candidates: energy counters, temperatures, status codes,
  alarm/fault masks and DC PV measurements. Enable them for comparison with Sync.
- AC_PV and whole-house power are still unresolved. Alarm coverage is incomplete.
- Phase measurements, volts/amps and individual-pack details are deferred.

The [working table](docs/overview.md) is the source of truth for scope and evidence.
Use the [comparison checklist](docs/validation.md) for observations, and
[register provenance](docs/registers.md) / [alarm notes](docs/alarms.md) for mappings.

## HACS installation and updates

Repository: `https://github.com/aaaaarie/home_assistant_kstar_e10kt_d22`

1. Add it under **HACS → Custom repositories**, type **Integration**, if absent.
2. Download **KSTAR LAN** and restart HA.
3. Add **KSTAR LAN** under **Settings → Devices & services**:
   host `192.168.178.238`, port `502`, unit ID `1`.

After code changes: commit/push, use **HACS → KSTAR LAN → Redownload**, then restart.
Keep the existing config entry and entity IDs to retain history.

Polling defaults to **60 seconds**, adjustable through **Configure**. Enable optional
sensors in the device's entity settings, including disabled entities. Disabled and
deferred measurements aren't polled. On update, retired entities are disabled
without deleting their history.

## Recording during validation

Keep this exclusion in `/config/configuration.yaml` while checking candidates:

```yaml
recorder:
  exclude:
    entity_globs:
      - "sensor.kstar_lan_*"
```

Merge into the existing `recorder:` section. Restart after changes. Live readings
remain available, but save comparison screenshots yourself. Remove the exclusion
when ready to record; it doesn't delete older data. Renamed entity IDs need matching
exclusions. Keep provisional counters out of the Energy dashboard until validated.

## Troubleshooting

- Setup/connectivity: check access from HA to `192.168.178.238:502`, unit ID `1`.
- Config-flow 500: inspect **Settings → System → Logs** for the traceback.
- Unavailable candidates: download integration diagnostics. Rejected registers
  retry after 10 minutes; connection failures retry on subsequent polls.
- Wrong readings: compare timestamp, units, sign and scope with Sync. Record the
  mismatch in [observations](docs/observations.md); don't shift every address by one.

## Development

Python **3.14.2+**. Install test dependencies with `pip install -e '.[test]'`, then:

```sh
python -m pytest
ruff check custom_components tests scripts
ruff format --check custom_components tests scripts
```

Tests use actual HA Core classes and mocked transport, including UI form
serialization. They establish software behavior; app/device comparisons establish
measurement accuracy.
