# Per-region wardrobe colors

Layered assets can declare up to eight default color regions and mark individual
PNG layers as tint masks. The renderer preserves each mask's alpha while replacing
its RGB color, leaving untinted outline and detail layers unchanged. Tint variants
count toward the same bounded decoded-image budget as regular layers.

The wardrobe now lists regions available on the selected character and clothing.
Choose color previews a change on the detached draft; restoring a region removes
its override. Apply saves per-identity overrides, and saved outfits keep their own
color snapshots. Export/import preserves overrides. Old assets and profiles remain
valid without optional palette, tint or colors fields.

113 tests passed across palettes, profiles, wardrobe controller/dialog, asset
library, layered composition, translations and documentation. Pixel assertions
verify alpha preservation, unchanged black details, independent renderer colors,
saved-outfit snapshots and export/import restoration. UI tests exercise selection,
color preview, Apply and restore-then-Cancel. Malformed colors, undeclared regions
and unequipped references are rejected. Pyflakes passed for the touched modules.

The updated wardrobe was rendered and inspected offscreen with explicit QA
fixtures. Seven dictionaries, ten READMEs, seven pet documentation pages and the
asset format documentation were updated. Production artwork, face/part variants,
remaining interactions and native/performance acceptance are still pending.
