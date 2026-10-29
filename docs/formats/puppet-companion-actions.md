# Puppet companion action bindings

FrontEngine reads the optional `frontengine_actions` object from the selected
`.petscript.json`. The existing Imervue message/schedule fields remain unchanged.
No bindings means no guessed native motion names.

```json
{
  "version": 1,
  "greetings": ["Hello!"],
  "frontengine_actions": {
    "feed": {"motion": "eat", "expression": "happy"},
    "groom": {"expression": "relaxed"},
    "sleep": {"motion": "nap"},
    "celebrate": {"motion": "wave", "expression": "happy"}
  }
}
```

Names on the right must exist in the selected model. Each binding has `motion`,
`expression`, or both, with no other fields. Supported action names are the
layered pet action vocabulary: idle, walk, sleep, climb, fall, drag, greet, pet,
feed, groom, play, celebrate, outfit_show, wake, sleep_in, food_like, food_dislike, sit,
land, peer_greet and catch. A declared binding
does not make an unsupported movement/interaction available to Puppet; it only
maps action states the companion actually enters. The script read is bounded to
1 MiB. Invalid references fail before allocating a pet window.

The native player/expression stack renders the reaction. Repeated notifications
for the same action do not restart it. Completion or interruption stops only the
reaction-owned motion and removes only an expression the reaction added.
Expressions already selected by the user remain selected. Choosing a motion,
expression or model hit area manually releases reaction ownership before making
the manual change. Hiding or typing-settle releases reactions; showing or resuming
can apply the current companion action again.

This mapping changes presentation only. CompanionState still owns completion,
cooldown and rewards. Native GL visual correctness and model-specific animation
quality need separate acceptance; runtime API tests do not prove those gates.

The optional per-identity `preferences.taste` contains `favorite` and `disliked`,
each null or one of snack, feast, music and book. Non-null choices must differ.
Missing taste means neutral. Feeding captures the preference when accepted;
changing preferences mid-meal affects the next meal. Completion can present
food_like or food_dislike for two active seconds. These presentations add no
affection or fullness and do not bypass the shared feeding cooldown. Bind them
only to reactions that the model actually provides.

## Built-in models

`frontengine/show/pet/inkside/puppet_export.py` writes each built-in character as a v1 `.puppet` plus a
`.petscript.json` with these bindings. Its parts are textured quads: rotation deformers turn the head,
arms and tail; warps move the whole body and push a raised arm's shoulder outward; opacity keys switch
eye and mouth states. Eye states belong to expressions only, and every motion declares a fade-out,
because Imervue snaps a stopped motion without one to frame 0 and restores pre-motion values that
already include an expression overlay.
