# Steering future work

This repository targets a local, read-only KSTAR BlueSpark E10KT-D22 integration.
Work in agreed phases and report back at each boundary. The intended endpoint is
running in the user's HA instance with maintainable code and documentation;
publishing or pushing is not implied. Keep installation/user guidance in README.md.

## Architecture that matters when changing code

- `custom_components/kstar_lan/registers.py` is the declarative FC04 map and numeric
  decoder. Addresses are zero-based wire addresses; `words` lists high word first,
  independently of ascending request order. Source lists may use another order.
- `modbus.py` is the only network layer. One serialized async PyModbus client per
  config entry; reads are bounded to 16 words. Do not add write methods, arbitrary
  scans, control entities, scheduling or cloud calls.
- `coordinator.py` selects enabled entities from HA's registry, polls through that
  shared client and isolates rejected registers with a 10-minute backoff. Transport
  failures make all measurements unavailable. Disabled candidates must not be read.
- `sensor.py` publishes declarative measurements under one device. Preserve entity
  keys/identifiers when possible; changing them can split statistics/history.
  Suggest `sensor.kstar_lan_<key>` for every entity so the documented Recorder
  exclusion works. Respect existing registry IDs and user renames.
- `config_flow.py` validates connection/profile with the two known FC04 addresses.
  Options reload the entry. Setup/unload/shutdown own connection cleanup in
  `__init__.py`; do not create connections per sensor.
- `diagnostics.py` intentionally omits endpoint and device identifiers. Keep it safe
  to share; measurement data still describes the user's energy usage.

## Evidence before promoting measurements

Only SoC at 3066 (×0.1) and raw model-code readability at 3045 are device-verified.
Readability/plausibility alone is not semantic validation. Other sensors remain
reference-only, disabled by default and named unverified, except the three battery
power entities explicitly enabled provisionally at the user's request. They share
register 3065, assume positive discharge/negative charge and are named assumed.
A discharge sample matched the app; charging remains pending. Do not translate model
code 40 using the older lookup. Hardware model naming is user supplied.

Consult `docs/registers.md` for source provenance and conflicts. Never assume 3100
or 3144 is a three-phase total. Do not infer AC_PV from battery charging or DC PV.
Verify scale, signedness, word order, direction and counter resets against
simultaneous app/independent readings before changing verification or statistics.
Record that evidence and update the inventory when modifying the map.

## Verification expectations

Tests use actual HA Core 2026.10.0 and a mocked transport. The in-process platform
check exercises registration and serializes config/options forms through HA's
HTTP flow helper; it is not full HA OS/UI or hardware validation. Keep custom
validators out of displayed form schemas unless HA can serialize them. Decoder
and availability tests prove behavior, not the reference map. Prefer tests of
failure modes and contracts over duplicating guessed addresses as assertions.

Run `python -m pytest`, `ruff check custom_components tests scripts`, and
`ruff format --check custom_components tests scripts` in the project test environment
(Python 3.14.2+). Rebuild the ignored archive with `python scripts/package.py` after
source changes if delivering it. Keep the PyModbus requirement aligned with the
target HA Core's pin; updating it requires compatibility evidence. No test should
contact hardware. Use small, explicit read-only requests in a separately agreed
hardware-validation phase.
