# Puppet light play

- [x] Ground: call and light share movement, bounds and cancellation; only marker appearance and arrival action differ.
- [x] Sketch: independent design compared one fixed activity map/shared controller against a second controller. Chose shared ownership.
- [x] Agree: skip checkpoint; implementation authorized.
- [x] Implement: migrated controller and all callers, added menu/manager light, hints, completion/cooldown/drag tests and translated docs. 118 checks pass and native light probe passes.
- [x] Scrap: unnecessary; no parallel timer or controller introduced.

Throughput checkpoint: use existing target owner, then test both activities' interruptions, then native light proof. Core data is the fixed call/light to appearance/arrival map. Native proof covers synthetic GL and off-screen movement, not production animation or actual monitor boundaries.
