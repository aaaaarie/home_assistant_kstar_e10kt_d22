# KSTAR LAN

Read-only Modbus TCP monitoring for my KSTAR BlueSpark E10KT-D22:
one inverter, two battery packs, one Home Assistant device.

Tested with HA Core **2026.10.0** and **PyModbus 3.13.1**.

Measurements, registers and remaining work: [overview](docs/overview.md).

## HACS installation and updates

Repository: `https://github.com/aaaaarie/home_assistant_kstar_e10kt_d22`

1. Add it under **HACS → Custom repositories**, type **Integration**, if absent.
2. Download **KSTAR LAN** and restart HA.
3. Add **KSTAR LAN** under **Settings → Devices & services**:
   host `192.168.178.238`, port `502`, unit ID `1`.

After code changes: commit/push, use **HACS → KSTAR LAN → Redownload**, then restart.
Keep the config entry; the update automatically removes obsolete sensor registrations.

Polling defaults to **60 seconds**, adjustable through **Configure**.

## Recording during validation

Keep this exclusion in `/config/configuration.yaml` while checking candidates:

```yaml
recorder:
  exclude:
    entity_globs:
      - "sensor.kstar_lan_*"
```

Merge into the existing `recorder:` section and restart. Live readings remain
available. Remove the exclusion when ready to record; it doesn't delete older data.

## Troubleshooting

- Setup/connectivity: check access from HA to `192.168.178.238:502`, unit ID `1`.
- Config-flow 500: inspect **Settings → System → Logs** for the traceback.
- Unavailable candidates: download integration diagnostics. Rejected registers
  retry after 10 minutes; connection failures retry on subsequent polls.
- Wrong readings: compare units, sign and scope with Sync; update the overview.

## Development

Python **3.14.2+**. Install test dependencies with `pip install -e '.[test]'`, then:

```sh
python -m pytest
ruff check custom_components tests scripts
ruff format --check custom_components tests scripts
```
