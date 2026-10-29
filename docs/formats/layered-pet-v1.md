# Layered pet asset format, version 1

Implementation: `utils/pet_pack/layered.py` and `show/pet/layered_renderer.py`.
The wardrobe UI installs these assets and previews or applies them to desktop pets.
Existing `pet.json` sprite packs keep their original format and loader.

Each character or garment occupies a folder containing `layered-pet.json` and
static PNG images. No scripts or archive extraction are involved. The manifest
has exactly these fields:

```json
{
  "format": "frontengine.layered-pet/1",
  "id": "mochi",
  "version": "1",
  "name": "MOCHI",
  "kind": "character",
  "template": "inkside-cat-v1",
  "canvas": [256, 256],
  "slots": [],
  "license": "Asset license and provenance reference",
  "actions": {
    "idle": {
      "loop": true,
      "frames": [{
        "duration_ms": 120,
        "anchors": {"head": [128, 48]},
        "layers": [{"image": "idle/body.png", "z": 0,
                    "anchor": null, "offset": [0, 0]}]
      }]
    }
  }
}
```

Garments use `kind: "garment"` and one or more occupied `slots`: head, neck,
body, back. A one-piece garment can occupy multiple slots, preventing another
item from occupying any of them. A garment requires the same template, canvas,
action coverage, loop values, frame counts and frame durations as its character.
Each garment layer references the character frame's anchors. Garment anchors
are not used for positioning; authors should leave that map empty.

Layer offsets place the image's top-left corner relative to the specified
anchor, or the canvas origin when the anchor is null. Per-frame z values range
from -100 to 100. Back pieces may use negative z, the body zero, straps positive
z, and hands higher z. Equal z preserves character-first, then garment order,
then layer order. Authors should choose distinct z values when overlap matters.
Final composition is flipped as a whole, preserving clothing alignment.

Every character requires idle. Supported actions are idle, walk, sleep, climb,
fall, drag, greet, pet, feed, groom, play, celebrate, outfit_show, wake,
sleep_in, food_like, food_dislike, sit, land, peer_greet and catch. A missing requested interaction renders idle; a garment missing a
character action is rejected. This permits the planned three-action art pilot
without representing it as a complete six-action character.

One character timeline samples all layers. Looping clips wrap; nonlooping clips
hold their final frame. The renderer has no timer and accepts nonnegative
integer milliseconds. The caller controls pause, action changes and elapsed
time. It caches only one composed frame and returns detached images.

A layer may add `"source": [x, y, width, height]` to draw only that rectangle of
its image, so many small cells can share one atlas PNG. An image used only through
source rectangles may be up to 2048 pixels a side; each rectangle must fit both
its image and the canvas. Whole-image layers must still fit the canvas. The
built-in characters pack their cells into one atlas per layer kind, which keeps
a character and its wardrobe to a few dozen files.

Limits: 1 MiB manifest; 16–2048 pixels per canvas side; 120 frames per action,
512 per asset; 16–10000 ms per frame; 72 layers including alternatives and 32 anchors per frame;
four garments per outfit. PNG files are at most 16 MiB each and 64 MiB total;
decoded unique images are limited to 16 megapixels per outfit. Each image must
fit the canvas. Relative paths cannot contain traversal, absolute paths,
backslashes, drive names or symlinks. Image format and dimensions are checked
before decoding.

## Optional palette masks

An asset may add `"palette": {"fur": "#F37620"}` to its manifest, with up to
eight identifier-named regions and six-digit RGB colors. A layer may add
`"tint": "fur"` to use that region. Its PNG alpha is the coverage mask; its RGB
values are replaced with the chosen color. Untinted layers preserve all original
pixels. Authors must separate outlines, highlights and details they want to keep
from recolorable masks. Render order and anchors still apply to every layer.

Profiles may include an optional appearance `colors` map, for example
`{"mochi@1": {"fur": "#00A080"}}`. It holds up to five exact asset references,
each with at most eight region overrides. Undeclared regions or unequipped assets
are rejected before applying. Saved outfits retain their own detached colors map.
Old profiles and assets without color fields retain their original behavior.
Restoring a region removes its override and uses the asset's authored default.
Decoded and tinted image variants share the 16-megapixel outfit budget.

## Optional character part variants

Characters may declare up to eight groups with up to eight choices each:

```json
"variants": {
  "eyes": {
    "name": "Eyes",
    "default": "narrow",
    "choices": {"narrow": "Narrow", "sleepy": "Sleepy"}
  }
}
```

A layer tagged `"variant": ["eyes", "sleepy"]` renders only for that selection.
Untagged layers always render. Every choice must have at least one layer in every
frame of every action; undeclared choices and missing coverage fail loading.
Multiple layers may share a choice for front/back pieces. To intentionally hide
a part, supply a transparent PNG for its choice. Garments cannot declare variants.
All alternatives share the existing resource and decoding limits and the same
character timeline, anchors, tint processing and whole-character mirroring.
The 72-layer bound permits eight base layers plus eight groups of eight alternatives;
multipart alternatives count toward the same bound.

Appearance optionally stores `"variants": {"eyes": "sleepy"}`. Missing selections
use authored defaults. Wardrobe validates choices against the exact character
version before preview or commit. Newly saved outfits snapshot `character` and
`variants` alongside clothing and colors; wearing them restores that character.
Older outfits without `character` retain the current character. Unknown/missing
assets retain stored references and require repair rather than silent substitution.
