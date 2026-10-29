# Puppet call movement

- [x] Ground: Puppet has native canvas and manual dragging, no Sprite physics. Recovery branches on motion; a fake motion attribute would break it.
- [x] Sketch: independent review chose a call controller plus shared visual target marker over full Sprite physics. Marker bounds are target-center limits, movement and arrival remain owner-specific.
- [x] Agree: skip checkpoint; implementation authorized.
- [x] Implement: shared marker extraction, Puppet controller, lifecycle adapters, manager/menu, focused tests and docs. 413 all-pet tests pass; 132 earlier focused/localization/docs tests pass; pyflakes clean.
- [x] Scrap not needed: Sprite physics remains in LightToy; Puppet has no fake motion attribute.

Contract: TargetMarker owns radius, target limits, drag and paint, without movement. LightToy retains Sprite guidance/arrival tick. PuppetCallController owns an active-only timer, float window position and center arrival. Puppet exposes start_call and stop_toy, no motion attribute. Native model parameters are untouched; optional walk mapping uses existing reaction bindings.

Throughput checkpoint: first pass shared marker against existing Sprite tests, then complete Puppet controller and lifecycle checks, followed by documentation. Native GL/focus and authored animation remain separate acceptance work.

Independent review confirmed controller/marker ownership and found the small-pet marker edge case. Regression reproduced a marker at (-1009,-809) outside an area starting (-1000,-800). Reachable-center limits now intersect marker-safe bounds and tiny areas are refused. Four small-pet corners pass. Recovery now separates generic cancellation from Sprite drag fields and clears Puppet's actual drag origin.
