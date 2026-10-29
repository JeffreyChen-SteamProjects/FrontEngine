# Keyboard call destination

- [x] Ground: manager resolves the selected live session; DesktopPetWidget owns one target; LightToy.place_target owns radius, floor projection and work-area limits.
- [x] Sketch: independent reviewer confirms manager offsets preserve target ownership; separate dialog/focusable marker rejected.
- [x] Agree: skip human checkpoint; implementation is authorized.
- [x] Implement: keyboard-editable destination, selected identity, bounds, busy/unsupported refusal and normal arrival verified; 95 tests pass and actual UI inspected.
- [x] Scrap: not needed; ownership remains unchanged.

Throughput checkpoint: one owner API and two manager fields, then component tests and translated documentation. No new movement timer, native input injection or separate saved destination state.

Candidate A: horizontal/vertical logical-pixel offsets on manager, passed to start_call with keyword-only offset. Existing target constrains the requested position; the call returns accepted/refused.

Candidate B: a separate destination dialog or keyboard-focusable marker. This adds dialog lifetime and a second input context; a focusable desktop marker conflicts with existing nonactivating overlay behavior. Candidate A keeps keyboard input in the manager and leaves target ownership unchanged.

Accepted contract: start_call(*, offset=None) returns accepted/busy; _start_toy returns bool. CallTarget applies offset before its first show. Manager call branch does not run generic interaction cleanup before eligibility. Independent review found floor radius limiting included ignored vertical input; failing-before regression demonstrated differing x values. Shared LightToy now discards dy first in floor mode. No additional stored state or timers.
