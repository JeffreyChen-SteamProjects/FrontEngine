Control Center Page
-------------------

.. image:: ../image/control_center/control_center.png

One page that reaches every overlay, including the ones the other pages opened.

Closing

* Close all video / image / gif / web / sound / text - close that kind.
* Close all - close every overlay on screen, whichever page opened it.
* Clear Log - empty the message area on the right.

Everything at once

* Hide all / Show all - put the overlays away for a moment and bring them back.
* Mute all - silence everything that makes sound.
* Lock / Unlock overlays - unlocked overlays can be dragged into place with the
  mouse and remember where they were dropped; locked ones pass clicks through.
* Chroma key - paint the background a solid colour for keying in OBS or similar.
* Reset overlay positions - put everything back where it started.
* Low power - cut refresh rates and render resolution when the battery matters.
* Quality - High, Balanced or Saver, a finer version of the same idea.
* Hide from capture - keep the overlays on your own screen but leave them out
  of what a screen share records. Windows only. A cover from the Focus page
  stays visible, since covering something is the one thing it is for.
* Pin to this desktop - keep the overlays on the virtual desktop they were
  opened on. Switch to another desktop and they step aside; come back and they
  return. Unpinning brings back whatever it had put away. Windows only.

Control Center → Follow a window selects an existing registered top-level overlay and a visible Windows target. Bind preserves the current proportional offset as the target moves/resizes; follower size remains logical and native movement uses physical coordinates with no activation/resize request. It clamps to the target monitor work area and rechecks on each 250 ms poll. Target minimize hides, restore respects user hide/hide-all, and close/hidden target or lost identity detaches. A unique reversible window property plus PID/thread checks prevents HWND reuse from inheriting a binding; elevated/UIPI targets can explicitly deny registration. Detach before manually dragging to a new offset. At most 64 temporary bindings, none restored across sessions; overlay close/close-all/app shutdown remove cookies and stop idle timer. This is the verified Windows adapter only; unsupported platforms show a reason. Native acceptance used own windows on one 125% display; cross-monitor mixed-DPI acceptance still requires another display.

Control Center → Monitor profiles explicitly saves/restores positions for each hardware monitor combination (20 profiles, 200 windows, 512 KiB local monitor-profiles.json). Proportional work-area positions adapt to resolution/primary/DPI changes while preserving logical window sizes; unavailable profiles clamp existing windows onto the primary work area. Automatic adaptation is separately opt-in, debounced 500 ms, and observes new overlays and Qt screen changes without modifying OS display settings. Hardware identity ambiguity is reported; same-kind/title duplicates are excluded from saved restoration but can be brought back into view. Fullscreen/scene windows and active target-follow bindings are excluded. It never creates overlays or guesses native handles. Movement stays entirely in Qt logical coordinates. Native save/restore/off-screen recovery passed on one Windows 125% display; real monitor plug/unplug, primary changes and mixed DPI still require additional hardware.

Static software composition now reuses one cached frame (up to 16 MP); image content/DPR, transforms, opacity, stacking, clip, output size and output DPI invalidate it. Unchanged layer submissions skip repaint; animated/video frames still refresh. GPU readback is unchanged. App exit and Close all share the registered overlay sources, close each object once before clearing, reset wallpaper playlists and run cleanup before releasing scene assets. Qt stays alive while canceled local file/raster workers finish, using a nonblocking timer. Plugin API v1 remains the supported manifest version; examples/plugins/clock provides a trusted QWidget page with overlay_widgets, optional release_overlay_resources/shutdown and get_state/set_state. Loaded plugin state is namespaced as plugin:<page name> in presets, including transactional rollback; presets never load code. Copy the selected example folder into plugins/, then explicitly enable and approve its content digest. Declarations/grants do not create an OS sandbox. Developer software benchmark: py -m benchmarks.scene_composition --output build/scene-benchmark.json; an optional trusted --baseline-file compares exact output pixels. Measurements and baseline procedure are in docs/benchmarks/README.md.
