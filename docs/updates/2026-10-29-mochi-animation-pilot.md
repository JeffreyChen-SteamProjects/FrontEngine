# MOCHI animation asset pilot

Produced transparent idle, walking-step and sleeping keyframes using the approved
MOCHI sheet as the identity reference through the built-in image_gen workflow.
Original generated pixels are retained. The attempted orange-region extraction
is archived as rejected because it has speckled edges and stray alpha.

The three keyframes form an installable development package at
docs/design/assets/pet-animation-pilot-2026-10-28/mochi-draft-1. Its displayed name
explicitly says unfinished. A two-keyframe walk loop is only a timing experiment;
idle and sleep each have one keyframe. Per-action metadata offsets align the
strong-alpha foot baselines without modifying the source artwork.

Actual generated dimensions are 1254×1254, so the layered authoring canvas limit
was raised from 1024 to 2048 per side while retaining the existing 16-megapixel
decoded outfit and file-byte limits. A boundary test accepts 2048 and rejects 2049.
The format documentation reflects this bound.

The verification script inspected transparency, installed the real images into a
temporary library, applied the appearance, confirmed distinct walk frames and
reopened a DesktopPetWidget with the stored appearance. 19 layered/library tests
passed; Pyflakes passed for the modified loader and tests. No native window or
user-input automation was used.

This is not a finished asset delivery: gradients and low-alpha stray pixels remain,
and the poses lack production cleanup, true component separation, complete action
coverage, clothing alignment and native/performance acceptance. The provenance
record and validation.json distinguish source/art defects from runtime success.
The full pet goal remains active.
