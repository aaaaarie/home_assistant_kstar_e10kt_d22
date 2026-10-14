# Working rules

- Work in agreed phases; report back at each boundary. Pushing is not implied.
- Target one KSTAR system overview: energy flows, counters, temperatures and alarms.
  P1 supplies grid data. Support AC PV now and direct DC PV later; no Huawei dependency.
- Read-only LAN monitoring. No writes, controls, scheduling, cloud calls or arbitrary scans.

# Implementation pitfalls

- Keep one shared async client/coordinator; reads are bounded to 16 words.
- `REGISTER_DEFINITIONS` retains references; only `SENSORS` creates entities/polls.
  Disabled/deferred measurements must not be polled.
- Preserve entity keys, registry history and the `sensor.kstar_lan_` ID prefix.
- Addresses are zero-based. Our `words` tuples are high-word first; Solarman lists
  multiword addresses low-word first. Registers 3100 and 3144 are phase values.
- HA must serialize displayed form schemas. Custom validators previously caused a
  config-flow 500; keep normalization in backend validation.
- Keep unavailable values unavailable and diagnostics free of endpoint identifiers.

# Evidence pitfalls

- SoC matches Sync. Positive battery power matched discharge; negative charging is
  still assumed. Model code 40 must not use the older model-name lookup.
- Readability/plausibility is not validation. Check scale, sign, scope and counter
  behavior before promoting candidates. AC_PV is distinct from battery power/DC PV.
- D22 alarm definitions differ from the older map and exceed its coverage. Zero flags
  do not establish safety; don't invent severity or mask-to-code mappings.
- Keep scope/evidence in `docs/overview.md`; consult `docs/registers.md`,
  `docs/observations.md` and `docs/alarms.md` when changing mappings.

# Checks

Use Python 3.14.2+; keep PyModbus aligned with the target HA Core pin. Run `python -m pytest`, `ruff check custom_components tests scripts`, and
`ruff format --check custom_components tests scripts`. Tests block network access and verify software, not register meanings.
Hardware comparisons use separately agreed, bounded read-only snapshots.
