# MOCHI animation pilot, draft 1

This is a development asset experiment, not approved production artwork or a
completed character. The user approved the art direction of
`../pet-concepts-2026-10-28/mochi-v3-ink-chibi.png`; that does not approve this
new draft automatically.

Generation used the built-in OpenAI image_gen tool with transparent_background=true.
No API keys, CLI fallback, Tripo service or local pixel-editing script were used.
The generated 1254×1254 RGBA files were copied unchanged into this workspace.

## Inputs and outputs

| Output | Generation source basename | Reference and instruction summary |
| --- | --- | --- |
| Initial idle exploration, not packaged | exec-2e8f5769-87a0-442c-af70-63906f137eca.png | Approved MOCHI sheet; extract one unclothed neutral full-body sprite, preserve asymmetric ears, face patch, narrow eyes, square tooth and lightning tail; transparent exterior; remove grain and gradients |
| mochi-draft-1/idle.png | exec-927174c6-a6b5-45b3-a8e3-eaa5f9122c01.png | Initial idle exploration; preserve geometry and flatten to ink #171715, orange #F56A24, cream #FFF3D9 |
| rejected/orange-mask-v1.png | exec-c4cad77a-6709-4ded-9156-8bcaa50f311d.png | Revised idle; extract orange areas into white alpha mask while preserving original alignment; other colors transparent |
| mochi-draft-1/walk-step.png | exec-d32a4714-ce3b-40a6-bf89-a43f32bd1a37.png | Revised idle; change short limbs into one waddling step while preserving head, face and tail identity |
| mochi-draft-1/sleep.png | exec-29f7c847-bce9-4112-9be1-d14058585e1e.png | Revised idle; lower head, closed narrow eyes, hands on belly and lowered angular tail; same head scale and ground baseline requested |

The summaries above describe prompts; they are not verbatim transcripts.
The tool call history contains the exact prompts and reference paths.

## What is actually usable

`mochi-draft-1` is installable through the wardrobe's asset-folder installer.
Its manifest contains idle, walk and sleep actions. Idle and sleep are single
keyframes. Walk alternates the neutral and step keyframes at 220 ms each as a
timing prototype; it is not a finished alternating-foot walk cycle. Manifest
offsets align strong-alpha foot baselines: idle 0, walk step +22, sleep +24 pixels.

The whole character is one raster layer per pose. It does not yet expose color
regions, face parts or independently replaceable clothing. The orange-mask
experiment was rejected because of speckled edges and stray opacity.

## Validation and remaining defects

The build/verification script is `.audit/pet-implementation/build_mochi_pilot.py`.
It writes manifest metadata, inspects source alpha, installs into a temporary
library, applies through WardrobeDraft and reopens an actual DesktopPetWidget
offscreen. It does not modify any image pixels. Results are in validation.json.

All three sources have alpha from 0 to 255 and retain the main MOCHI identity.
However, source gradients remain despite the flattening request, and low-alpha
pixels extend beyond the main silhouette. No production-flat-color, clean-edge,
96-pixel readability, frame-continuity or clothing-alignment gate is claimed.
Next art work must clean these issues through the image-generation workflow,
produce true component layers and full action coverage, then verify them against
the approved style. Native desktop and performance acceptance remain pending.
