# Focus companion mode integration

The existing pet focus timer now drives temporary Work mode during focus and
Rest mode during breaks. FocusCompanions records the original mode and the
session's mode revision for each initially visible, non-interacting pet. Stop
restores a mode only if the user or automatic care has not superseded it. Even a
manual selection of the same mode counts as a new user choice.

Each newly completed round grants eligible visible working pets 3 affection and
5 mood once. Repeated delivery of the same completion does not reward again;
early stop, hidden pets and manually overridden participants do not receive the
completion reward. The session owns the care mutation and persistence scheduling.
Existing non-modal focus messages remain the notification path.

Default FocusTimer timing now derives from monotonic elapsed time. Injectable
datetime clocks remain supported for deterministic tests. Work and Rest suppress
proactive sprite chatter. Application shutdown ends focus and restores owned
modes before flushing pets.

89 selected focus, companion, social, profile-session, control-center and
documentation tests passed. Coverage includes repeated completion, two rounds,
manual same-mode choice, original Rest restoration, hidden completion, real page
timer transitions, elapsed-time boundaries and quiet Work/Rest behavior. Pyflakes
passed for the new controller and touched focus/session/page modules and tests.
Ten READMEs and seven pet documentation pages were updated.

This does not finish the entire focus presentation: safe-position placement and
approved celebration animation remain pending, along with other interactions,
production assets and native/performance acceptance.
