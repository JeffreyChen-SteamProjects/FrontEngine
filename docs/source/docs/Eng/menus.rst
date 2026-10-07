Presets and Settings
--------------------

Presets menu

* Save preset... - remember everything the pages are set to, under a name.
* Load preset... - bring one back.
* Delete preset...
* Export preset... / Import preset... - move a preset between machines as a
  json file.
* Export package (+media) / Import package (+media) - the same, but with the
  images, videos and sounds it refers to, as a zip.
* Set as startup preset... - apply one automatically when FrontEngine starts.
* Import Workshop content... - install presets and pet packs you subscribed to
  on Steam.

Settings menu

* Hotkeys... - global shortcuts for hide all, show all, close all, mute all,
  opacity up and down, next dashboard page, lock, freeze the screen, the
  shortcut list, media play/pause, next and previous track, and moving the
  foreground window to the next monitor with its proportions kept.
* Scheduled day/night theme - a light theme by day and a dark one at night.
* Start with the system - launch FrontEngine at login.
* Restore last session - reopen what was on screen last time.
* Load plugins (advanced) - plugins are Python and run with the same rights as
  FrontEngine, so only install ones you trust.
* Smart pause... - hide the overlays while a fullscreen application is running,
  while on battery, or while named applications have focus.
* Keep the screen awake - stop the display sleeping while you have something on
  screen. It is released when you switch it off and when FrontEngine closes, so
  the machine goes back to its own power settings.
* App profiles... - apply a preset automatically when a given application comes
  to the front.
* Reminders... - a message every so many minutes, or at a time of day.
* Rules... - "when these conditions hold, do this". Combine a weekday, a time
  window, and which application has focus, then apply a preset, hide, show or
  close the overlays, or set the quality. A blank condition means "any", and a
  rule runs once when its conditions start holding rather than repeatedly while
  they do.
* Screensaver... - after so many minutes with no mouse or keyboard, put a
  chosen page's overlay on screen; moving the mouse takes it away again. It
  uses that page as you have it set up, and closes only what it opened, so
  anything you left running is still there when you come back.
* Scheduled preset... - apply a preset at a time of day, on the days you choose.
  With no day ticked it runs every day. It fires as the time passes, so starting
  FrontEngine later does not apply it late.
* Signage mode... - rotate through a list of presets on a timer, for a machine
  left running as a display. The main window can go to the tray while it runs -
  but only when there is a tray to bring it back from.
* Phone control: Settings → Remote control serves HTTPS only, with a token that changes on every start and a fixed action list. The local self-signed certificate is not automatically trusted by a phone. Export the public certificate and compare the displayed SHA-256 fingerprint before importing or trusting it through your phone/browser settings. The private key stays in the user data directory. Changed IP addresses, expiry or regeneration may require trusting a new certificate. TLS startup failure does not fall back to HTTP.
* Screen-sharing privacy... - hide the overlays from a screen capture while a
  meeting application is open. Matched against window titles, so a meeting held
  in a browser tab is caught too. Windows only.
* Screen time... - how long you spend in each application. Kept on this machine
  and never sent anywhere.
* Clipboard history... - what you copied recently, searchable, with pinning.
  Kept in memory unless you ask for it to persist, because clipboards often
  hold passwords.
* Export settings... / Import settings...

Help menu

* **How to use...** - a short guide inside the application: your first
  overlay, the settings every page shares, and how to clear the screen again.
* **Shortcut list...** - the global shortcuts as they are actually bound, shown
  over the screen. Rebinding them changes this list too. Press the shortcut for it
  again, or Escape, to put it away.
* Open issue tracker, and a reminder that F12 closes FrontEngine at once.

Plugins: enabling loading does not authorize a plugin. A plugin.json or single-file sidecar declares version, identity, entrypoint and capabilities; approval is checked before Python import and tied to the content digest. Changed code or declarations require approval again; legacy plugins require explicit full trust. Settings → Revoke plugin grants removes stored approvals; restart to unload already running code. Python plugins still run with full application privileges: declarations and consent are not an OS sandbox.

Rendering: Settings → Overlay rendering selects Auto, GPU or Software and shows the backend actually used. The GPU compositor uses OpenGL textures, shaders and framebuffers for layer order, transforms, opacity and clipping; initialization failure falls back to software with a reason. Existing QPainter content can still be rasterized on the CPU before texture upload; web/video/native widgets may use separate windows. Capture or recording may read a GPU frame back to the CPU. These paths are not a promise of zero-copy capture or measured speed gains. Scene GPU composition currently covers IMAGE, GIF and TEXT; puppet rendering uses its own Imervue window.

:doc:`runtime_interoperability`

Settings → macOS permissions and capabilities lists each feature as available, unavailable or unsupported and shows the permission or installation reason.

Open Commands from the menu bar or press Ctrl+K / Ctrl+Shift+P inside FrontEngine. Search the current interface language, English labels or stable command names; Up/Down selects and Enter runs. Commands include page navigation, capture, notes, the screen filter, Workshop and existing global actions. Preset/quality actions accept a value. Favorites and the last 20 commands survive restart; arguments and search text are not saved.

Presets → Preset versions keeps up to 50 distinct settings snapshots per preset across restarts. Saving records the previous and new configurations; identical settings are deduplicated. Select a version to compare field changes with the current page settings. Preview applies that exact configuration to page controls; Cancel preview, Escape or closing restores the original settings. Restore version applies and saves it, rolling page settings back if application or saving fails. Snapshots contain media paths, not copies of media files; preview does not open overlays. Existing JSON/ZIP presets remain compatible. History lives under presets/.versions; deleting a preset leaves its history available if the name is reused.

Settings → Rules adds priority (-1000…1000), cooldown (0…86400 whole seconds), condition preview and session execution history. Triggered rules execute from lower to higher priority, keeping table order for ties; higher priorities run last. Cooldown uses a monotonic clock: a blocked rising edge is consumed, and expiry does not execute while conditions remain true. Preview inspects unsaved rows without running actions or consuming edges. The last 200 receipts retain rule conditions, sampled context and dispatched/executed/failed/cooldown outcomes; history stays in memory. Invalid named rows prevent saving. Up to 200 rules are supported, with stable independent identities even for duplicate labels. Existing non-table conditions survive edits. An action callback reporting failure is recorded as failed, and one failure does not stop later rules.

Rules can load, play or stop a scene and show, hide, move or change the opacity of a named layer. Select the row and use Choose scene / layer target to browse JSON, .fescene or .puppet files, choose the primary/all/indexed screen, or select an editor layer. Playing with an empty path uses the current editor scene. File reads run in the background; a failed candidate leaves existing playback intact. The latest scene request replaces earlier pending requests; subsequent layer actions wait for it and fail if it fails. Locked or missing layers are rejected. Layer edits support undo and update playback; opacity is 0–100 and positions are limited to ±100000. Stop cancels pending requests and closes playback, keeping editor assets until replacement or application shutdown. Execution history records actual asynchronous completion. Scene actions also appear in the command palette: use a path or {"path":"scene.fescene","screen":"primary"}, a layer key for show/hide, {"layer":"title","opacity":50}, or {"layer":"title","x":20,"y":30}.

Settings → Image clipboard history is separately opt-in and off by default; opening it neither enables monitoring nor reads the clipboard. Apply settings enables recording and optional between-session local SQLite persistence. Choose 10–200 images and 8–128 MiB of PNG payloads; favorites protect from eviction while counting toward both limits, and a full favorite set rejects new images explicitly. Images are limited to 16 megapixels/eight MiB encoded each. One worker owns compression, thumbnails and database writes, with one latest pending clipboard image and coalesced result mailboxes; slow compression drops intermediate images. Thumbnails support favorite/delete/clear, copying the original image, desktop pinning and an in-memory reference board. Clear includes favorites and frees stored payload pages; turning persistence off deletes the local database while retaining current memory history. The database is clipboard-images.sqlite3 beside settings (132 MiB database bound, transient SQLite journals may add disk usage); no uploads or automatic OCR. Shutdown disconnects monitoring and requests asynchronous worker cleanup.

Settings → Capture history and search is separately opt-in. Opening does not save or recognize anything. Only explicit Tools region captures enter its local OCR worker, never clipboard monitoring or cloud fallback. Successful OCR becomes a case-insensitive text index; failures still save the image and show a reason tooltip. Date search uses exact YYYY-MM-DD in the user’s local timezone; leave fields empty for all entries. Copy, pin, reference board, favorites and deletion reuse image history controls. Optional capture-history.sqlite3 beside settings persists 10–200 captures / 8–128 MiB PNG data (16 MP/eight MiB per image; main database at most 132 MiB plus temporary journals). Delete removes OCR text together; clear includes favorites; persistence opt-out deletes the database. One latest pending capture skips intermediate inputs when slow; closing drops pending work/results without waiting for an active local recognizer.
