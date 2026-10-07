Scene Page
----------

.. image:: ../image/scene/scene.png

A scene holds several overlays at once and can be saved to a file.

* Add web to scene - address and opacity.
* Add video to scene - file, opacity, play rate, volume.
* Add image to scene - file and opacity.
* Add gif to scene - file, opacity, speed.
* Add sound to scene - file and volume.
* Add text to scene - text, opacity, font size, alignment.
* Start scene - show everything that was added.
* output scene file - save what you built.
* load scene file - bring a saved scene back.
* clear all script - start again.
* Show on all screen - one copy per monitor.

Scenes: the Scene page accepts old entry-mapping JSON, a versioned frontengine.scene envelope, and portable .fescene packages. Add a PUPPET entry with position, size, opacity, finite numeric parameters, optional motion, expression and script. Paths in JSON resolve relative to the scene file. A .fescene includes the referenced media, original .puppet and optional .petscript.json so it can move between machines. Import checks paths, symlinks, versions and extraction limits. A FrontEngine scene remains a scene package; .puppet remains one Imervue character.

:doc:`runtime_interoperability`

Scene → Visual editor provides an image/GIF/text layer list and preview, group dragging, corner resizing, position/size/scale/rotation/order/opacity controls, canvas alignment, layout locking, visibility, duplication and 100-step undo/redo (Ctrl+Z/Ctrl+Y). Export portable .fescene packages directly; the Script tab also supports editing and applying JSON. Explicit dimensions, scale, rotation and visibility are restored during scene playback. Loading/applying external JSON starts a new undo history; existing scene fields remain intact.

Scene → Script → Scene templates (also in the command palette) provides Work desktop, Teaching and Focus starter layouts with localized editable text. Preview the layout and choose the primary or a numbered screen before Apply and play; proportions fit its available logical size. Templates include all required resources. Missing resources are listed with layer/field/path and block application. Applying replaces the editor and playback through the same scene candidate transaction; failed preparation preserves the old scene. Edit the resulting text, add media and use Scene output to save JSON or a portable .fescene. Closing the library cancels only its pending application. Focus includes editable reminder text; scheduling and timers remain separate tools.

Scene → Visual editor can add video, web, Puppet and audio alongside image/GIF/text. Enable live previews explicitly: at most eight sources, muted until Listen to selected media, paused when hidden, closed on disable or shutdown. Frames are bounded to 1280 pixels per side; unavailable sources show an error. Named scene playback composes video frames, the web renderer’s own surface and Imervue offscreen Puppet frames with all visual layers in z order; audio has no visible playback layer. Double-click a web/Puppet layer in playback or choose Interact with selected media in the editor to open its own native input window. Puppet preview needs native OpenGL and the optional runtime; preview does not execute pet scripts, and scene pets use temporary stats. Standalone web/video/Puppet windows remain available. JSON/.fescene export preserves every supported type and media reference.

Scene → Visual editor → Animation timeline edits x/y/opacity keyframes for one unlocked layer, with fade-in and slide-in starters. Times are unique and increasing, 0–3600 seconds, up to 128 frames per layer; opacity is 0–100, positions ±100000, easing linear or smooth. Empty cells leave that channel unchanged. Apply creates one undoable edit; JSON and portable .fescene retain animation tracks. Scrub, play, pause, resume or replay preview without saving temporary positions; Reset restores saved geometry before editing. Scene playback has separate animation controls and one shared monotonic clock across screens. Hidden views suspend it; explicit pause persists after showing. Media suspends during animation pause; replay controls animation tracks. Scene-action replacement dissolves an outgoing composed snapshot into the new scene over 0.5 seconds, releases old renderers immediately and starts the new timeline at zero. Legacy scenes without tracks remain compatible.
