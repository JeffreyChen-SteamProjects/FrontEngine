# Per-pet customization implementation

Each saved pet identity now has its own presentation and interaction preferences. The editor stages edits until Apply, preserves drafts on save failures or conflicting edits, and stages Reset without writing. Active sprite pets apply size, speed, movement, climbing, window sitting, bubbles and volume after persistence succeeds. Puppet pets apply proportional size and bubbles, expose settling while typing, and disable unsupported movement, volume, throwing and social controls.

The dialog takes inherited defaults from the active pet so changes to page controls do not misrepresent that pet's current baseline. Reopening a sprite identity restores its custom values; another pet retains its own values. Native Puppet size reset restores its original aspect and dimensions.

Validation on 2026-10-28: 172 tests passed across profiles, live sessions, customization, companion rules, movement, drops, feeding, tag, typing settlement, Puppet lifecycle and documentation. Pyflakes passed for the touched pet implementation modules and customization tests. Tests ran with QT_QPA_PLATFORM=offscreen. These results do not verify native desktop rendering, mixed DPI or foreground behavior.

The domain is session-owned: legacy mood, hunger and growth accessors reference the same objects inside CompanionState. They are not independent copies of persistent state. Preference commits validate and save first, then publish to the live session.

Remaining work includes appearance masks and palettes, face variants, layered wardrobe preview and saved outfits, complete six-character animation assets, toys and remaining interaction flows, and isolated native/performance acceptance. The full goal remains active. The high-customization acceptance scope is recorded in section 13 of the design specification.
