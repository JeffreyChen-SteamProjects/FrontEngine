# MOCHI face-part development pilot

This package demonstrates actual generated artwork in the character-part wardrobe.
It is not production-ready art or a complete animated character.

All sources were generated with the built-in image tool and copied unchanged.
No CLI/API fallback or local pixel cleanup was used. The original reference was
`../pet-animation-pilot-2026-10-28/mochi-draft-1/idle.png`.

| File | Generated source | Instruction summary |
| --- | --- | --- |
| base.png | exec-13b3ca6a-ac7e-44f9-8a05-9a384ad4feb0.png | Remove facial marks while retaining body/ears/tail/face patches; request flat three-color fills and true alpha |
| deadpan.png | exec-91ba09e8-ba29-4dd0-ab48-72d5708e3985.png | Extract only eyes, eyebrow, nose, mouth and tooth to a registered transparent canvas |
| drowsy.png | exec-66ca5365-97c9-426b-a982-d3d7ecad664f.png | Change extracted eyes to closed strokes while preserving remaining facial marks |
| rejected/registration-attempt.png | exec-87d671f0-f4f0-419c-a13e-791e26696ada.png | Requested 80% scaling and translation; output drifted downward and introduced colored edge defects, so it is not packaged |

The summaries are not verbatim prompts. Exact prompts and reference paths are in
the tool-call history. Source hashes and read-only alpha inspection are stored in
`validation.json`.

The installed package has one static idle action and a `face` choice with deadpan
and drowsy alternatives. It uses the existing renderer's offset `[-65, -30]` to
place both overlays on the base, with no source-pixel editing. This is a grouped
face study, not independent eyes/nose/mouth editing. Drowsy is an appearance
choice, not a completed sleeping animation.

`.audit/pet-implementation/build_mochi_parts_pilot.py` writes the manifest,
installs into a temporary library, previews both choices through LayeredRenderer,
applies and reopens the saved appearance, and checks another identity is untouched.
The two runtime-preview PNGs are renderer outputs for visual inspection, not new
source art. The script only inspects source images and copies their bytes.

Known defects: the generation did not remove gradients; fine colored edge flecks
remain in extracted facial marks; proportions differ from the original whole
sprite. The face offset fits inside the base but is not an exact reconstruction.
Full animations, separate ears/tail, masks, garments, small-size readability and
native/performance acceptance remain incomplete. Low-alpha counts include normal
antialiasing and do not by themselves prove stray-pixel severity.
