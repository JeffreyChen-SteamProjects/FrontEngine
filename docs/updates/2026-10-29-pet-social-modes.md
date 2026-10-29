# Social participation follows each pet's state

Peer target lists and tag participants previously included resting, working or
socially disabled pets even when those pets rejected their own assigned roles.
Both sides now require the same availability check: visible, session active,
Play mode, no current interaction, social preference enabled, not dragged and
not settled while typing. Excluded roles and stale movement guidance are cleared.
Tag pauses below two eligible participants and can restart when visibility,
mode or typing availability returns.

Greeting rewards no longer depend on whether speech bubbles are enabled. Quiet
pets still receive the semantic greeting reward; existing cooldown/hysteresis
prevents repeated rewards. The bubble remains hidden.

69 tests passed across social-mode integration, tag rules, typing settlement,
profile sessions and documentation. Tests use three real offscreen desktop pets
to verify work/rest/interaction/social-off/hidden/typing exclusion, no reward for
excluded participants, role cleanup, hide/show and typing resume, and silent
greeting deduplication. Pyflakes passed for the touched implementation and tests.
No host keyboard hooks or foreground input were used for the typing test.

Ten READMEs and seven pet documentation pages describe participation rules.
Remaining toy, focus, photo and gesture flows, full artwork and native acceptance
remain tracked under the original full pet goal.
