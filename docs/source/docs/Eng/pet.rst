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

Puppet pets also stroll on their own: after a few seconds' rest they walk a short way left or right along their current height with the walk motion, stay inside the screen's work area, then rest again. A stroll gives way to dragging, petting, Come here and toys, settling while typing, and modes that do not allow acting alone.

:doc:`runtime_interoperability`

Pet → Pet identities saves an independent UUID, name, mood, fullness and affection for every sprite or puppet pet. Choose a saved identity before spawning to resume it after restart; New pet creates fresh state. The first identity migrates the old shared values once. Cloning copies current stats to a new identity; feeding never changes another pet. Rename, refresh, export or import individual JSON saves; import always creates a new identity. One saved identity can be active only once. Saves contain no sprites, scripts or chat history, and local identity IDs are excluded from portable presets. Up to 256 identities are stored in user settings; sprite changes are saved after a short debounce and on close. Puppet feeding updates only saved stats and does not alter Imervue motions or geometry.

Pet → Sprite pet pack editor maps walk/idle/sleep/climb/fall/drag images, previews size and walking speed, and exports a portable folder with pet.json. At least one action is required; missing actions are listed and use the existing loader fallback. PNG/JPEG/GIF/WebP sprites are limited to 64 MiB and 16 megapixels each, 256 MiB total. Import/export runs off the GUI thread, can be cancelled and never overwrites an existing export folder. Exported folders can be relocated, selected on the Pet page and shared as Workshop pet packs. Import retains selected sprites, name, size and speed only; sounds, scripts and speech are not copied. Imervue .puppet uses its separate authoring format. Closing or Escape releases preview movies and cancels pending file work.

Companion interactions and saved state
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Version 2 pet profiles preserve the UUID and stats of version 1 saves and add energy, the selected mode, preferences and validated appearance references. 

The sprite pet menu offers Say hello, Pet gently and Groom, plus persistent Play together, Work together and Rest modes. End interaction cancels the current action. Timed actions award their benefits only when completed; cancellation gives no reward. A full pet refuses food, repeated actions have a cooldown, and dragging or changing appearance gives no reward. This release has no toy interface.

Care advances with active time independently of speech bubbles. Hidden pets and offline time do not accumulate catch-up care or rewards. Sprite pets use the shared interaction session for menu actions and mode control. Puppet pets share the session and feeding rules; their native visual responses depend on the runtime and model capabilities.

Choose an identity on the Pet page and open Customize pet, or open it from that pet's menu. Each identity can keep its own size (16–512), speed (1–20), floor/wander/chase behaviour, wall climbing, window sitting, speech bubbles, volume (0–100), settling while typing, automatic rest, throwing and social preferences. Use page defaults inherits the page's presentation settings; cloning and importing retain individual settings. Apply saves atomically before updating the active pet. Cancel changes nothing; Reset defaults only stages changes until Apply. A failed save or conflicting edit retains your draft. Puppet disables unsupported controls and applies only size, speech bubbles and settling while typing among presentation settings. Native wardrobe controls and layered artwork remain unfinished.

Pet identities → Wardrobe opens a separate animated preview for an installed layered character. Install asset folder copies validated layered-pet.json resources into pet-assets beside the local settings. Choose head, neck, body and back items, preview actions and facing, and save up to 20 outfits per identity. Equipping an item replaces whatever shares its slots and names what was replaced; Cancel restores it. Only pieces for the current body type are listed, and pieces missing animations are shown disabled. Trying an item on plays a short outfit show, and Pin for comparison keeps the current look beside the draft. A pet that is being dragged or is mid-interaction switches clothes once it finishes. Pets showing whole-image sprites are told to choose a layered character first. Apply saves and updates the active sprite; Cancel discards edits since the last Apply. Missing resources remain referenced and can be repaired, then rescanned with Refresh. Puppet models do not accept layered Sprite clothing. Add built-in character draws one of six INKSIDE characters (MOCHI, MOSS, PIP, BOLT, INK or GILL) with thirty wardrobe pieces from fourteen outfits fitted to its body, then installs them through the same validation in the background; closing the wardrobe cancels it. Each character offers eye, mouth and three body-part choices plus recolorable regions, and every piece follows all of its animations. Part and garment names follow the interface language.

An undressed built-in character with its default parts and colors walks and climbs with hand-drawn whole-body step frames; with clothing or changed parts it uses the layered animation so every piece stays fitted.

Desktop pets always paint through ordinary Qt painting, whatever Overlay rendering is set to: a pet moves its window every tick, and on the GPU path its animation frames stopped changing while it moved.

Pets now settle into poses: Work mode sits, entering Rest plays a short falling-asleep clip and leaving it plays a wake-up clip. Playing, ball and fetch games and tag cost a little energy; below 20 energy an idle pet sits even with automatic rest off, and it still obeys every command. Landing after a drop or throw, grabbing a thrown ball and meeting another pet show brief land, catch and wave reactions without interrupting movement, toys or your commands. Sprite packs without these clips fall back to their idle or sleep images. Grooming ends with a stretch, and pets that keep meeting wave to each other at most once a minute.

Relationships grow with affection through four stages: Just met, Familiar (20), Close (100) and In sync (250). The stage appears in Status. Each stage has its own greeting line, Close pets wave and In sync pets jump for joy, and reaching a new stage plays a one-time celebration; nothing is locked or lost. A saved pet summoned again says welcome back, and Close from the pet’s own menu waves goodbye before the window closes. Puppet pets now separate a click from a drag the same way as Sprite pets: a click greets on release, and only movement beyond the system drag distance moves the window, without rewards.

Customize pet also sets Chatter (Off, Rarely, Normal, Often) for lines the pet starts on its own and Animation size (Calm, Normal, Lively) for the audio pulse and quick land and catch reactions, separately from speech bubbles and volume. Replies to what you do still appear with chatter off. Puppet pets apply Chatter to scheduled script lines. Presentations saved earlier keep working and use Normal for both.

The pet manager's interaction list also offers the selected live pet's own menu commands: photo, status, reminder, chat when a chat service is attached, clone and close, plus every motion and expression of a Puppet model. Everything in a pet's right-click menu can therefore be done with the keyboard.

Use built-in Puppet model on the Pet page draws the chosen INKSIDE character as an Imervue .puppet model in the background: rigged head, arms, tail and body, ten motions, three expressions and a pet script that maps companion actions to them. It is saved under pet-assets/puppets and selected as the source with its script, so Start spawns it as a Puppet pet.

On setups with several monitors at different scaling, a pet dragged or brought back to another monitor keeps its size, stays inside that monitor’s work area and walks there. Window ledges on scaled monitors are measured in the same coordinates as the pet, so it perches exactly on top of windows.

Wardrobe color controls appear for regions declared by the selected character or clothing asset. Choose a region and color, or restore its authored color. Only designated mask layers are tinted; outlines and unmarked details remain unchanged. Colors are previewed before Apply and saved per identity and outfit, including profile export/import. Assets without declared regions have no color controls enabled.

If a pet save fails during close, the pet remains open with its current state and retry timer. Close all retains pets that could not close, and application exit waits for successful pet saves before teardown. Affection stops at the supported save limit so further rewards cannot make the profile unsaveable.

Peer greetings and tag require both pets to be visible, in Play mode, idle, socially enabled and not being carried or settled for typing. Unavailable pets are removed from targets and tag roles. Tag pauses below two eligible pets and resumes when they become available. Disabling speech bubbles only silences greeting text; it does not remove social rewards.

Starting the pet focus timer puts currently visible, idle pets into Work mode; breaks use Rest mode. Stop restores previous modes unless you changed a mode yourself. Each completed focus round awards eligible visible companions 3 affection and 5 mood once; stopping early or hiding a pet gives no completion reward. Work/Rest suppress proactive chatter. The default timer uses monotonic elapsed time, not wall-clock changes.

Focus mode arranges companions in the lower-right work area of their screen when space permits. Stopping restores their previous positions only if you have not moved them or changed their mode.

Layered characters can declare selectable face/body parts. Wardrobe previews part choices per pet; Apply persists them and saved outfits retain the character and parts. Every declared choice must cover every animation frame. Production artwork for the six characters remains unfinished.

The sprite pet menu offers Pet photo: freeze its current appearance or select an authored layered pose, then save a transparent PNG. Captures contain only the pet, without desktop pixels or speech bubbles. Puppet pets also offer a frozen transparent photo through a compatible initialized Imervue renderer; no desktop pixels are captured. Native GL photo acceptance remains pending.

For sprite pets, choose Pet gently, then move the pointer back and forth over the pet. Three deliberate stroke segments start one petting reaction; jitter does not count. Dragging and social play pause during this mode. Leaving, hiding, changing mode or End interaction cancels unfinished petting. Rewards remain subject to completion and cooldown.

Sprite pets offer Throw a ball and Put ball away. Drag and release the ball to throw it again, or right-click it to dismiss. The pet chases the bounded ball and carries it back near its starting point; a completed return grants one affection with a 30-second active-time cooldown. Work/rest, other interactions, hiding, typing-settle or timeout cancel without a reward. Puppet pets can fetch the ball too (see below).

Floor pets leave window ledges to fetch a ball. Window perching pauses during the game and resumes afterward; the return point is on the floor near the original horizontal position.

Play with a light spot adds a small draggable target near the pet. Its range is bounded; floor pets chase along the floor. Release the target and let the pet reach it to start a short play reaction, rewarded only on completion under the existing play cooldown. Right-click the spot or choose Put toy away to stop. Only one ball or light toy can be active per pet.

Cloning uses the selected pet’s own sprite/model, appearance, preferences and asset library, even if the settings page now selects another asset. The clone receives a new identity; later outfit or part edits do not change the original. Puppet clones also retain their source script, parameter values and active expressions.

Eligible focus completion briefly requests the celebrate animation, then returns to Rest. Applying a changed wardrobe briefly requests outfit_show. These two-second active-time reactions add no rewards and are not saved; manual actions or mode changes interrupt them. Assets without those animations use the existing idle fallback. Finished reaction artwork and native Puppet animation mapping remain pending.

Select an active identity and choose Bring pet back to move it into the selected monitor’s work area. Hidden pets become visible, unfinished interactions and toys stop, and sprite physics bounds follow the new screen. Appearance and care values remain unchanged. Inactive pets require Start; oversized pets require a smaller size first.

Puppet scripts may declare frontengine_actions to map companion states to existing model motions and expressions. Names are validated before startup; missing bindings do not guess animations. Completion releases reaction-owned effects while preserving manual choices. See docs/formats/puppet-companion-actions.md. Native visual acceptance remains pending.

Puppet petting now waits for back-and-forth pointer strokes after choosing Pet gently. Leaving, Escape, hiding, changing mode or settling cancels unfinished petting. Dragging is suppressed while petting. Native gesture acceptance remains pending.

Wardrobe style colors offer six quick swatches for the selected declared color region. Preview first, then Apply; Cancel preserves the saved appearance. Free color selection and restoring the region default remain available.

Sprite and Puppet menus now offer four fictional treats without requiring a file drop. They share feeding completion, fullness limits and cooldowns. Feeding ends petting first; unfinished petting gives no reward, and Sprite toys are put away.

Each pet can save a favorite and a different disliked treat in Customize pet. These affect mood only after feeding completes; fullness, affection and cooldown are unchanged. Mid-meal edits affect the next meal. Old profiles remain neutral. Optional food_like and food_dislike artwork or Puppet bindings provide short reactions; production artwork is pending.

Sprite pets offer Come here with a draggable nearby marker. Floor pets approach along the floor; wander/chase pets follow in two dimensions. Arrival triggers a short greeting with the normal greeting cooldown. Right-click the marker or End interaction to cancel. Work/rest, hiding, feeding or a new toy also cancel.

Pet identities now provides an Interaction picker and Perform interaction button for the selected live pet. Keyboard users can greet, pet briefly, groom, choose treats, change play/work/rest mode or cancel. Manager petting uses the same timed care rules without pointer strokes. Hidden or inactive pets show feedback instead of spawning.

Changing the interface language while the wardrobe is open updates its None, Missing and Reset defaults choices without discarding pending colors, parts, outfit names or the preview position. Asset-provided names stay as authored.

For keyboard destination selection, choose Come here in the pet manager and enter horizontal/vertical offsets in logical pixels. Negative values mean left/up. The target is constrained to the nearby work area, and floor mode ignores vertical offsets. Perform interaction starts the call; End interaction cancels it. Busy or unsupported pets keep their current interaction.

Puppet also supports Come here from its menu or the manager’s keyboard offsets. Its window moves toward the marker with the entire pet and marker constrained to the work area. Arrival is measured at the pet center and triggers the shared greeting after half a second. Dragging the pet, care, mode changes, hiding, resizing, screen-area changes or manual model commands cancel the call. A declared walk reaction is used while moving; models without one retain their native appearance. The movement timer runs only during a call. Native GL/focus acceptance remains pending.

Puppet can chase a draggable light spot from its menu. Both Sprite and Puppet managers offer light play with keyboard offsets. Releasing the light near the pet for half a second starts the shared three-second play action; affection is awarded only on completion and follows the normal cooldown. Calls and light play share one target. Put toy away, End interaction, care, manual dragging, mode changes or hiding cancel it.

Puppet pets also offer Throw a ball from their menu, and both Sprite and Puppet managers can throw one for the selected identity. The ball physics, drag-to-rethrow, right-click dismissal, one-affection reward and 30-second cooldown are shared with Sprite; the Puppet window chases, picks up and carries the ball back to its original centre, staying inside the work area. Each rethrow starts a fresh timeout. Ball, light and Come here share one target, so starting one replaces the other. Care, manual dragging, mode changes or hiding cancel without a reward. Authored fetch animation remains pending.
