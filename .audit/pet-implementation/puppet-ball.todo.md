# Puppet ball retrieval

- [x] Ground: BallToy owns flight, pickup, carry, rethrow and semantic ball reward; Sprite moves after its tick. PuppetTargetController owns one target/timer and center translation.
- [x] Sketch: compare explicit BallToy movement adapter against a duplicated Puppet ball implementation; independent review requested.
- [x] Agree: skip checkpoint; implementation authorized.
- [x] Implement: shared ball physics, Puppet movement adapter/menu, lifecycle and completion checks, docs.
- [x] Not scrapped: adapter needed no fake pet.motion and no duplicated ball state. Scrap if adapter forces a fake pet.motion or duplicates ball state.

Candidate A: BallToy accepts an explicit movement owner and return tolerance. Default Sprite path stays unchanged. Puppet target controller exposes real work-area bounds and guidance, advances the ball, then moves once per tick using its existing float translation. The pet has no motion attribute.

Candidate B: duplicate ball flight/drag/carry logic in a Puppet-specific widget. Rejected provisionally because every bound, timeout and reward change would need two implementations.

Throughput checkpoint: preserve Sprite tests first, then full Puppet round/rethrow/cancellation and native probe if practical. Full art/Steam/performance scope remains unchanged.
