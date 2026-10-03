Pet Page
--------

A companion that lives on the desktop.

* Choose pet sprite - a single image.
* Choose pet pack... - a folder holding walk / idle / sleep / climb / fall /
  drag frames, for a pet that animates.
* Choose sound (optional) - a sound it plays.
* Spawn pet - put it on screen. Spawning again adds another one.
* Size, Speed - how big and how fast.
* Behaviour - walk on floor, free wander, or chase the cursor.
* Climb walls - let it climb window edges.
* Sit on windows - let it rest on the top edge of other windows.
* Speech bubbles - short remarks as the day goes on, when it is fed, and so on.
* Settle while typing - the pet stops moving while you are at the keyboard and
  carries on a couple of seconds after you stop, so it does not walk across the
  line you are reading.
* Speak out loud - read those remarks aloud.
* Play tag with each other - two or more pets chase one another.
* React to audio - the pet moves in time with sound. It can follow your
  **speakers** or your **microphone**; either way it reads a level, a single
  number, and never captures what is being said. Windows and macOS (optional macos extra and permission; native macOS unverified here).
* AI chat (needs API key) - talk to it. This reads the ANTHROPIC_API_KEY
  environment variable and the key is never stored.
* Focus timer (min) - a work timer the pet keeps for you, with breaks.

Drop a file onto the pet to feed it, or drop an image or a pet pack to change
how it looks.

Puppet pets: install the optional puppet extra and an available Imervue runtime, then choose an original Imervue .puppet v1 file on the Pet page or drop it there. Existing image/sprite pet packs still work. Puppet pets use Imervue's canvas, motions and expressions, can be cloned or closed, and participate in FrontEngine's overlay controls and presets. Choose an optional .petscript.json for Imervue's existing script engine; do not treat FrontEngine pet.json packs as puppet files. Unknown versions, unsafe archive paths and invalid assets are rejected before runtime loading.

:doc:`runtime_interoperability`
