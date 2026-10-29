# Layered pet rendering foundation

Added a separate layered-pet.json format with immutable animation frames,
character anchors and per-frame layer order. Garments declare occupied slots
and must match their character's template, canvas and action timelines. Missing
actions, mismatched timing, missing anchors and slot conflicts fail before
rendering. Existing pet.json sprite packs keep their previous loader.

The timer-free renderer loads bounded static PNG resources, samples every layer
using the character's single frame index, composites back/body/front pieces,
and mirrors the finished image. It retains one frame cache and returns detached
images, so previews cannot mutate cached output.

On 2026-10-28, 26 tests passed across the new layered tests and existing sprite
pack editor tests. Pixel assertions cover anchor movement, frame boundaries,
looping, final-frame hold, front/back occlusion, whole-pet mirroring and cache
isolation. Rejection cases cover path traversal, incompatible outfits, invalid
durations, frame limits and corrupt PNG data. Pyflakes passed for both new
modules and their tests. Execution used Qt offscreen, without desktop input.

This is not a completed wardrobe: live pet integration, asset installation,
preview/apply/cancel UI, palette masks, face variants, approved character/clothes
animation assets, and native/performance verification remain pending. Fixture
images are colored squares for pixel verification, not delivered pet artwork.
