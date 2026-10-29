# Design verdict

| Criterion | Candidate A | Candidate B |
| --- | ---: | ---: |
| One owner per stat | 5 | 3 |
| Small API integrating sprite and Puppet | 3 | 4 |
| Atomic profile and wardrobe preservation | 4 | 4 |
| Mode arbitration against legacy idle/tag | 5 | 3 |
| Testable without desktop input | 5 | 4 |

**Use A as the base**, grafting B's narrow presentation capability port, explicit unsupported/missing-asset results, and wardrobe baseline comparison and staged composite. A gives session-owned stats and a pure transition policy, and explicitly gates legacy idle, peer, tag, and focus paths. B retains widget-owned stat objects and leaves Puppet's direct profile writes to a later phase; those paths need a single shared identity policy before consistent ownership can be claimed. Its QObject coordinator is nevertheless a useful model for adapting existing sprite and Puppet presentation without putting rendering in the reducer.

For either design, preserve unrelated record fields and concurrent renames when saving, validate migrations as a whole, and distinguish settings rollback from crash durability. Stage wardrobe resources before commit and define recovery if the post-commit renderer swap fails. Do not assume durable focus IDs or unavailable art capabilities exist.

The first unit can ship core modes and interactions with truthful fallback presentation and fake-clock/offscreen verification. It must route every existing stat writer, including Puppet where applicable, through the same ownership boundary and gate old autonomous behavior. Wardrobe transactions, asset compatibility, and the planned character/outfit coverage remain required subsequent work; the first unit is not the full implementation.
