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

## Energy dashboard

After updating and restarting HA, replace the old battery sources in
**Settings → Dashboards → Energy**:

| Energy input | New sensor |
| --- | --- |
| Energy charged into the battery | `sensor.kstar_lan_battery_daily_charge` |
| Energy discharged from the battery | `sensor.kstar_lan_battery_daily_discharge` |
| Solar production, external AC inverter | `sensor.kstar_lan_ac_pv_energy` |

Battery energy uses device counters with 0.1 kWh resolution. HA tracks their daily
resets; no helpers or templates are required. New battery entity IDs keep their
statistics separate from the old lifetime counters. Old battery registrations are
removed automatically; historical statistics are not converted. AC PV keeps its
existing entity ID and accumulated total. “DC PV generated energy” only covers
panels connected directly to the KSTAR DC inputs.

## Recording during validation

Energy dashboard sources must be recorded. Remove this validation exclusion from
`/config/configuration.yaml` if present, then restart HA:

```yaml
recorder:
  exclude:
    entity_globs:
      - "sensor.kstar_lan_*"
```

The exclusion leaves live readings available but prevents Energy statistics.
Removing it does not backfill the excluded period.

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
