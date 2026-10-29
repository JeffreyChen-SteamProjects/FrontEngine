# Wardrobe draft transactions

Added `show/pet/wardrobe.py` with a version-exact asset catalog and an isolated
wardrobe draft. Selecting a character starts a bare outfit. Equipping clothes
checks all declared slots, and removing a multi-slot garment clears all its
slots. Saved combinations can be created, updated by ID, selected or deleted;
they keep detached snapshots rather than references to the changing outfit.

Preview operations validate and decode before replacing the draft. Apply loads
the candidate again before saving, rejects stale appearance edits and uses the
active profile session to preserve current care values. Save failure retains
the staged outfit. Cancel releases the preview and restores the last applied
appearance. No operation awards affection for changing clothes.

Missing exact asset versions are reported without modifying saved references.
Explicit removal works even when the garment itself is unavailable. The catalog
rejects duplicate asset identities rather than choosing one by load order.

Validation: 19 wardrobe and layered-renderer tests passed with Qt offscreen;
Pyflakes passed for the new controller and tests. Coverage includes independent
pet identities, detached saved outfits, cancel/apply/reopen, multi-slot removal,
missing assets, stale edits, disk failure, live care preservation and the
20-outfit bound. Test images remain colored fixtures, not production artwork.

Remaining: wardrobe dialog and asset installation, publication of the prepared
renderer to live desktop pets, approved animation assets and native verification.
The full pet implementation goal remains active.
