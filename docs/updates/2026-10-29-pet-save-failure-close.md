# Preserve pets when saving during close fails

Previously PetProfileSession.close ignored a failed flush and released its live
state. It now returns failure while retaining the identity lease, renderer and
retry timer. Sprite and Puppet windows reject that close event; Puppet native
resources remain intact until a successful save. Closing again after storage
recovers saves the original live care state and completes cleanup.

ControlCenter now keeps overlays that explicitly reject closing in their owner
lists, including close-by-type. It does not run shared cleanup callbacks while
such overlays remain. MainUI flushes distinct active pet sessions before starting
application teardown. A failure displays the existing localized save-failure
message and leaves shutdown unstarted. Already closed sessions are skipped.

PetGrowth now uses the same affection maximum as profile validation. A reward at
the upper bound no longer creates a profile that cannot be saved.

Regression cases exercise a real sprite window, real available Puppet runtime,
batch retention and skipped cleanup, pre-shutdown failure, and a completed feed
at the affection limit. Tests use offscreen Qt and injected failing storage.
The supported recovery is retry within the running application; this does not
claim protection from forced process termination or power loss. Ten READMEs and
seven pet documentation pages describe the behavior.

Full pet functionality, finished artwork and native/performance acceptance remain
open in the main implementation checklist.

Validation: 148 selected pet, lifecycle, batch-control, documentation and translation tests passed. Pyflakes passed for the modified implementation modules.
