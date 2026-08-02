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
* Remote control... - control FrontEngine from a phone on the same network, and
  bind a MIDI controller. The link carries a one-time token that changes at
  every start, and only the buttons on the page can be triggered. It is plain
  HTTP, so leave it off on networks you do not trust.
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
