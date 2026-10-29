# Wardrobe interface

The Pet identities section and sprite pet menu now open one wardrobe dialog per
identity. Users can select installed layered characters, equip or remove four
clothing slots, preview each available action and facing, and create, update,
wear or delete named outfit snapshots. Apply persists before updating the live
pet; Cancel discards changes since the last successful Apply. Active Puppet pets
reject layered Sprite wardrobe edits.

Asset folder installation runs on the global thread pool, copies validated
resources into the local pet-assets library, and returns results through a queued
GUI connection. Closing requests cancellation before publication and releases
the preview timer and renderer. Resource refresh preserves the draft and reports
missing resources. Installing a resource is independent of applying an outfit.

67 tests passed across the wardrobe dialog/controller, library, profile sessions,
translations and documentation. New cases exercise the page entry, reuse of an
existing dialog, queued install completion, cancellation without partial packages,
Apply/Cancel and save failure. Pyflakes passed after correcting fixture imports.
The offscreen rendering script and inspected QA screenshot are under
.audit/pet-implementation. The screenshot uses colored test fixtures, not pet art.

The screenshot review changed the form to a shorter side-by-side layout and
corrected outfit-name/resource-refresh labels. Seven UI dictionaries, ten READMEs
and seven pet documentation pages describe the new flow. Earlier statements that
no wardrobe exists were removed; missing production layered artwork remains explicit.

Remaining work includes palette/face customization, approved character and clothing
animation assets, complete interaction/toy/photo flows, wider lifecycle testing,
performance and native desktop acceptance. The full goal remains active.
