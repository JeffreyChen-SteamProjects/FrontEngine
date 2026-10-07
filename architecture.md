# FrontEngine Architecture

Windows requirements include the PyWinRT Media.Control projection for song metadata. Nuitka explicitly includes `winrt` because the Now playing loader imports its namespace dynamically; legacy `winsdk` remains a runtime fallback.

The executable builder checks platform-filtered dependency metadata and version constraints before invoking Nuitka, preventing incomplete build environments from silently producing broken distributions.

Scene editing uses `utils/scene_format/scene_editor_document.py` for validated undoable entry snapshots and `ui/page/scene_setting/scene_visual_editor.py` for image/GIF/text and explicitly enabled media preview, layer selection and transforms. It synchronizes with the existing Script tab and portable scene formats. `SceneManager` applies explicit dimensions, scale, rotation and visibility to playback proxies.

Workshop publications use account-scoped durable records in `utils/workshop/workshop_publications.py`. `workshop_publisher.py` verifies remote ownership before updates, preserves created IDs before uploading and retains snapshots for interrupted operations; Qt service shutdown marks pending outcomes uncertain before releasing Steam.

Subscription install flags and callbacks are reconciled by `workshop_subscriptions.py`. `workshop_jobs.py` runs at most two validation/copy jobs per controller; `workshop_cache.py` keeps validated content versions outside Steam folders, retains old versions for scene leases and requires explicit activation for local-change conflicts.

`ui/dialog/workshop_dialog.py` is a persistent, hideable management window reached from Presets, Scene and Pet. Main UI owns the lazy Steam service and stops it during shutdown. File preparation/import runs through Qt workers; scene extraction leases are adopted on the GUI thread. `exe/build_exe.py --steam-runtime PATH` validates and copies the selected Windows x64 DLL beside the built executable without shipping the SDK or a development App ID file.

> Short overview for people and agents. Per-module detail lives in [`architecture_explore.md`](architecture_explore.md).
> Last verified: 2026-10-03; macOS native operations require target-host verification.

## 1. Purpose

FrontEngine is a PySide6 desktop overlay app. It places video, images, GIFs, web pages, text,
particles, sound and desktop pets above (or below) all windows, and adds screen tools: eye-care
filters, presentation annotation, measuring, recording, a virtual camera and focus masks. It is
published on PyPI in two channels, `frontengine` (stable) and `frontengine_dev` (dev). It also ships
on Steam (app 2793470) with Workshop import. JEditor embeds its main window as a tab and as a dock.

## 2. Layers and directories

| Path | Responsibility |
| --- | --- |
| `frontengine/__init__.py` | Public API: overlay widgets, setting pages, `ControlCenterUI`, `FrontEngineMainUI`, `FrontEngine_EXTEND_TAB`, `start_front_engine`, `language_wrapper`, `RedirectManager`. It imports `ui/main_ui.py`, so `import frontengine` loads the whole UI |
| `frontengine/__main__.py` | `python -m frontengine` → `main()` |
| `frontengine/ui/main_ui.py` | `FrontEngineMainUI`: assembles pages, menus and tray; owns the background services; dispatches hotkey, remote and MIDI actions; handles shutdown. Also holds `start_front_engine()` and `main()` |
| `frontengine/ui/page/` | One folder per feature page, built on `layout_kit.py` (`SettingPage`, `Section`). `control_center/` provides batch control, `scene_setting/` is the scene editor, and `utils.py` handles multi-monitor dispatch |
| `frontengine/ui/nav/`, `menu/`, `dialog/`, `style/` | Sidebar navigation; language/help/how-to/preset/settings menus; dialogs (file choosers, rules, schedules, remote, privacy, …); stylesheet layered on qt-material |
| `frontengine/show/` | Overlay widgets. Shared base `base_widget.py` (`BaseWidget`), `window_helpers.py`, and `overlay_factory.py` (scene JSON → widget) |
| `frontengine/show/compositor/` | Shared layers, real OpenGL shader/texture renderer, software fallback and RGBA output; BaseWidget caches CPU raster content |
| `frontengine/utils/imervue/`, `scene_format/` | Validated puppet container, optional upstream runtime, scene envelopes and portable package extraction leases |
| `frontengine/utils/macos/` | Public-framework capability/permission checks, capture, audio and MIDI sessions; native operations isolated behind injectable boundaries |
| `frontengine/system_tray/` | Tray icon and menu |
| `frontengine/user_setting/` | `user_setting.json` (`user_setting_file.py`), preset repository (`presets/*.json` and zip packages), scene files |
| `frontengine/utils/` | Services and pure logic: platform info, hotkeys, input watch, remote/MIDI, audio, rules/schedules/state machines, recording, virtual camera, window pinning, translations with live retranslation (`multi_language/`), `plugins/`, `steam/`, `workshop/`, logging, JSON |
| `tests/` | `tests/unit_test/` runs headless (`tests/conftest.py` forces offscreen); `tests/unit_test/start/` holds the launch scripts CI runs |
| `docs/source/docs/` | Sphinx docs, one tree per UI language |
| `exe/` | Packaged entry `start_front_engine.py`; Nuitka build `build_exe.py` |
| `steam_assets/`, `Update Note.txt` | Steam store-art generator; Steam announcement (BBCode) |
| `pyproject.toml`, `stable.toml`, `MANIFEST.in` | Dev (`frontengine_dev`) and stable (`frontengine`) metadata; `release.yml` bumps both. Package discovery is limited to `frontengine`, and `MANIFEST.in` keeps `tests/` out of the sdist |
| `.github/workflows/` | `ci.yml` (compile, tests, wheel smoke run), `nightly.yml` (cron only), `release.yml` |
| `.github/requirements/` | `publish.in` and the hash-locked `publish.txt` generated from it: the only packages the `release.yml` job, which holds the PyPI token, installs. The build backend (`setuptools`) is in the lock too and the job builds with `python -m build --no-isolation`, so the build downloads nothing outside it. `tests/test_workflow_actions.py` guards it; Dependabot keeps it current |

Dependencies point downwards: `ui/` → `show/` → `user_setting/` + `utils/`. The one known inversion
is `user_setting/scene_setting.py`, which imports `ui/dialog/choose_file_dialog`.

## 3. Entry points and public interfaces

- **CLI**: the `frontengine` console script (`[project.scripts]` → `frontengine.ui.main_ui:main`) and
  `python -m frontengine`. Both accept `--preset NAME` and `--debug`.
- **Programmatic**: `start_front_engine(debug=False, preset=None)`. It creates its own `QApplication`
  and ends with `sys.exit`.
- **Embedding**: `FrontEngineMainUI(main_app=None, debug=False, show_system_tray_ray=True,
  redirect_output=True)`. The constructor reads `user_setting.json` from the working directory and
  starts the global hotkey listener, F12 critical exit and background services. A host inherits
  those side effects.
- **Custom tabs**: `FrontEngine_EXTEND_TAB: Dict[str, Type[QWidget]]` in `ui/main_ui.py`.
- **Persisted state**: `user_setting.json` and `presets/` under the working directory.

## 4. Main flows

**Startup**

```
frontengine | python -m frontengine → main() → start_front_engine() → QApplication
  → FrontEngineMainUI.__init__
      [read_user_setting() → language_wrapper.reset_language() → sidebar + page stack
       → ControlCenterUI + _register_extra_overlays()
       → load_plugins(FrontEngine_EXTEND_TAB, enabled=user_setting_dict["load_plugins"])
       → _add_tabs() → menus → CriticalExit + HotkeyService + background services
       → restore last session / sticky notes → apply_startup_preset()]
  → apply_named_preset() if --preset → startup_setting() → sys.exit(app.exec())
```

**Show an overlay**

```
feature page (ui/page/<kind>/) → dispatch_to_monitors() (ui/page/utils.py)
  → show/<kind> widget(s) on the chosen monitor(s) (BaseWidget.paintEvent → draw_content())
  → page's widget list, registered via ControlCenterUI.register_overlay_source()
  → control center hides / closes / locks / re-tiers every overlay in one action
```

**Shutdown**

```
closeEvent() | close() → _shutdown() (runs once) → save session if enabled → stop _CLOSING_SERVICES
  → cancel recording/native sessions → close scenes → release scene extraction leases
  → save page state and geometry → write_user_setting() → close overlays
```

## 5. Extension points

- **Plugins**: `frontengine/utils/plugins/plugin_loader.py` loads `plugins/<name>/plugin.py` or
  `plugins/<name>.py` under the working directory. A module exposes
  `FRONTENGINE_TABS = {name: QWidget subclass}` and/or `register(registry)`; both fill
  `FrontEngine_EXTEND_TAB`. Loading is off by default (`load_plugins` setting, toggled in
  `ui/menu/settings_menu.py`) because plugins run with full app privileges. A versioned permission declaration (or explicit legacy full-trust approval) is checked before import; grants are bound to plugin content and location. See `docs/formats/interoperability.md`.
- **Host-supplied tabs**: add to `FrontEngine_EXTEND_TAB` before start
  (see `tests/unit_test/start/extend_front_engine.py`).
- **Control-center registry**: `ControlCenterUI.register_overlay_source(provider)` and
  `register_cleanup(callback)` in `ui/page/control_center/control_center_ui.py`, wired in
  `main_ui._register_extra_overlays()`. Shutdown lists are `_CLOSING_WIDGET_LISTS` and
  `_CLOSING_SERVICES`.
- **New overlay kind**: see the full checklist in `architecture_explore.md` §7. In short:
  - `show/<kind>/` (`BaseWidget` + `draw_content()`);
  - a page in `ui/page/<kind>/` (`SettingPage`, `get_state()` / `set_state()`);
  - `main_ui._add_tabs()` and the control-center registration;
  - keys in every language dictionary and a page in every docs tree;
  - an `__init__.py` in each new folder.
- **Scene kinds**: `show/overlay_factory.py` plus `ui/page/scene_setting/scene_page/registry.py`.
- **Languages**: `language_wrapper.register(name, word_dict)` (`utils/multi_language/language_wrapper.py`).
- **Hotkey actions**: `default_hotkeys` (`user_setting/user_setting_file.py`) plus
  `main_ui._handle_hotkey()`.

## 6. Cross-project boundaries

- **Imervue (optional upstream)**: the `puppet` extra installs `Imervue>=1.0.90`.
  `utils/imervue/runtime.py` consumes `Imervue.puppet.document_io.load_puppet`,
  `Imervue.puppet.canvas.PuppetCanvas`, the motion/idle/input controllers and
  `Imervue.desktop_pet.pet_script` loader/engine. Version 1 `.puppet` ZIP resources are validated
  before invoking the reader. FrontEngine owns window geometry, lifecycle and settings;
  it does not instantiate Imervue's PetWindow or write Imervue preferences.
  Scenes reference puppets via version 1 PUPPET entries; `.fescene` bundles referenced
  resources. Imervue is not expected to read the FrontEngine scene envelope.
  Detailed formats and capability boundaries: `docs/formats/interoperability.md`.

- **JEditor (downstream)**: JEditor lists `frontengine` as a dependency and embeds
  `FrontEngineMainUI` as a tab (`je_editor/pyside_ui/main_ui/menu/tab_menu/build_tab_tools_menu.py`,
  `show_system_tray_ray=False, redirect_output=False`) and as a dock
  (`je_editor/pyside_ui/main_ui/menu/dock_menu/build_dock_menu.py`, `redirect_output=False`). The
  constructor's keywords and side effects are therefore a contract. PyBreeze inherits both entries
  through `EditorMain`.
- **Release channel**: JEditor depends on the stable `frontengine` package. A change reaches it only
  after a `dev → main` release. `release.yml` copies `stable.toml` over `pyproject.toml` to build it.
- **PySide6 pin**: it must match JEditor and PyBreeze. FrontEngine pins it in `pyproject.toml`,
  `stable.toml`, `requirements.txt` and `dev_requirements.txt`. At last verification FrontEngine pinned
  6.11.1, PyBreeze 6.11.0, and JEditor 6.11.1 (stable) / 6.11.0 (dev).
- **Steam**: `utils/steam/steam_language.py` picks the first-launch language from the Steam client.
  `utils/workshop/workshop_content.py` imports subscribed Workshop items. `Update Note.txt` is the
  store announcement.

## 7. Design constraints

- Update `architecture_explore.md` in the same commit as any structural change (CLAUDE.md § Architecture).
- User paths stay inside their directory, and preset zips extract only the final path segment.
  External data is validated at the boundary. Subprocesses use a fixed allow-list of absolute paths
  with `shell=False`. API keys come from the environment only (§ Conventions › Security).
- Never block the GUI thread (`QTimer`, not `sleep`). Cross-thread signals use `QueuedConnection`.
  Overlays use translucent + delete-on-close, default to 0.2 opacity, and take intervals from
  `utils/power_mode`. Release resources in `closeEvent` (§ Conventions › Qt / performance).
- Type hints on public signatures; English comments in new code; functions under 50 lines
  (§ Conventions › Style).
- `python -m pytest tests/ -q` must pass headless. Anything that touches the outside world takes an
  injectable source (§ Conventions › Testing).
- Work flows feature → `dev` → `main`, and only a `dev → main` merge publishes. Never hand-edit the
  versions in `pyproject.toml` / `stable.toml`. Don't write the skip-CI directive in commit messages
  (§ Git workflow).
- `Update Note.txt` is BBCode, one paragraph per line, with no version number (§ Release announcements).

## 8. When to update this file

Update it in the same commit when any of these changes:

- a top-level package or directory in §2;
- an entry point, console script or `frontengine/__init__.py` export;
- the startup, overlay or shutdown flow in §4;
- an extension point in §5 (plugin contract, control-center registry, `FrontEngine_EXTEND_TAB`);
- the `FrontEngineMainUI` constructor or its side effects, the release channels, or the PySide6 pin
  (§6);
- a CLAUDE.md section that §7 points to is renamed.

Per-module changes go to `architecture_explore.md`. Refresh the "Last verified" line when you
re-check this file.

## Workshop publication boundaries

`utils/workshop/workshop_manifest.py` validates versioned scene/preset/pet-pack declarations and confines resources. `workshop_package.py` creates validated publication snapshots with explicit media only. Native publishing is implemented separately. Legacy empty/known presets remain readable; arbitrary metadata JSON cannot become preset settings. Preset ZIP imports validate archive limits and reject flat-name collisions before extraction.

`utils/steam/steam_runtime.py` lazily loads the Windows x64 flat API, checks interface 021 and App identity, owns copied manual-dispatch events and shuts down exactly once. `utils/workshop/workshop_service.py` pumps a bounded callback batch through a Qt timer. Native ABI and read-only initialization checks are explicit tools in `tests/integration/steam_workshop_abi.cpp` and `steam_workshop_smoke.py`; native availability is not inferred from fake tests.

Application actions: `utils/actions/action_registry.py` owns stable built-in IDs and translated labels. MainUI binds instance callbacks once; hotkeys, authenticated remote commands, MIDI and rule dispatch use the same registry. Existing remote/rule allow-lists remain at their input boundaries. Duplicate IDs are rejected, unknown IDs are ignored, and parameterized actions require values. Hotkey/rule dialogs share these label definitions.

`utils/actions/command_history.py` validates bounded recent/favorite stable IDs in user settings and searches localized labels plus English/IDs with Unicode folding. `ui/dialog/command_palette_dialog.py` provides keyboard search/selection/value input and queued-free GUI-thread dispatch through ActionRegistry. MainUI registers built-in page and tool commands, owns one persistent dialog, installs Ctrl+K/Ctrl+Shift+P application shortcuts and closes the palette on shutdown. Arguments/search queries are not persisted.

`utils/text_source/local_file_source.py` reads bounded regular UTF-8 TXT/JSON/CSV files with a single pending QRunnable per QObject feed, explicit queued delivery, metadata cache and recoverable status codes. LocalFileTextSource owns its polling timer; TextWidget adopts its lifetime and stops it on replacement/close. TextSettingUI exposes file/field/interval and bounded previews; MainUI stops page previews during shutdown. Scene text factories accept the same local source fields; scene asset normalization/packages include text_file explicitly. Preset state preserves source configuration. No file I/O occurs on the GUI thread.

`utils/measure/color_palette.py` validates and persists bounded named/grouped RGB swatches and recent samples, rejects duplicate group/name identities, rolls back failed saves and atomically exports JSON/CSS with unique slugs. `MeasureWidget.color_sampled` emits canonical hex on clicks only. ToolsSettingUI collects only when enabled and owns `ui/dialog/color_palette_dialog.py`; the manager edits/searches/exports the model, and MainUI registers its command and closes it during shutdown. Palette settings are separate from overlay preset state.

`user_setting/preset_history.py` keeps bounded immutable SHA-256 configuration snapshots under `presets/.versions/<sanitized-name>/`, validates finite JSON/digests/timestamps and prunes to 50 distinct versions. PresetRepository records old/new configurations before atomic active-file replacement and discards a newly prepared candidate on failure. `ui/menu/preset_menu.apply_state_transaction` snapshots every target page before strict application and restores touched pages (including a partially failed page) on error. `ui/dialog/preset_versions_dialog.py` compares settings, applies a cancellable preview to page controls and restores/saves a selected version transactionally. MainUI closes the manager before shutdown session persistence. Media files remain referenced, and existing JSON/ZIP preset layouts do not change.

`user_setting/pet_profiles.py` provides independent UUID pet records in the versioned pet_profiles section of user settings. It validates 256 bounded named records and mood/fullness/affection ranges, migrates legacy shared stats into the first identity only, commits record changes without overwriting peers and restores settings on save failure. Atomic portable frontengine.pet-save v1 JSON exports contain one identity only; imports always receive a new ID. `show/pet/pet_profile_session.py` leases one live session per settings/identity, reads current widget stats, debounces sprite saves and flushes/stops/releases on close. DesktopPetWidget uses record stats instead of shared globals; PuppetPetWidget retains its upstream rendering/geometry and supports independent feeding stats. `ui/page/pet/pet_profile_controls.py` selects saved/new identities, renames, refreshes and imports/exports saves (flushing live stats first); PetSettingUI clones into a new identity. Local profile IDs stay outside portable presets.

`show/reference/image_compare.py` bounds image file/dimension/canvas sizes, decodes oriented first frames, aligns RGBA images at origin/center or proportionally fits B inside A, and computes absolute RGB differences after compositing on white. `ui/dialog/image_compare_dialog.py` decodes/aligns/compares through a shared two-thread comparison pool with one outstanding request per dialog, close-cancellation checks and generation-based latest-selection coalescing and explicit queued delivery. A shared QGraphicsView synchronizes zoom/pan; retained pixmaps support side/overlay/clipped-wipe/difference modes without re-decoding on slider changes. ImageSettingUI owns the comparison dialog; page/main shutdown clears pixmaps and ignores late worker output. Invalid replacements preserve the previous pair and alignment.

`utils/rules/rule_engine.py` normalizes stable independent IDs, bounded priorities/cooldowns and at most 200 rules; RuleTracker uses monotonic cooldowns, consumes suppressed rising edges without delayed execution and sorts low-to-high priority with stable ties. RuleEngineService exposes non-mutating previews and a bounded session-only receipt deque with sampled context/conditions; transient receipt IDs pair application outcomes even across nested dispatch. ActionRegistry honors explicit False callback results. MainUI records failed/executed outcomes without stopping later rules. RulesDialog edits priority/cooldown, preserves identity and non-table conditions, rejects invalid named rows, rolls settings back on persistence failure and previews unsaved rows / displays execution receipts without internal IDs. Scene/layer actions use deferred completion receipts and named playback instances.

`utils/scene_format/scene_source.py` reads bounded scene files without changing globals and owns rejected extraction leases. `scene_action_values.py` validates scene paths/explicit screen selection and exact layer action values. `ui/page/scene_setting/scene_actions.py` owns one worker read plus one latest queued request, cancellation, GUI-thread hidden candidate construction and adoption into existing SceneManager list objects. Following layer actions wait for their scene result; superseded/failed/stopped requests resolve their deferred receipts explicitly. `utils/actions/deferred_action.py` provides one-shot completion; ActionRegistry.invoke returns receipts while execute preserves acceptance semantics. MainUI records asynchronous outcomes on completion. SceneManager tags named proxies/native monitor instances and synchronizes document geometry/visibility/opacity edits and undo; invisible proxies are excluded from compositor frames. RulesDialog uses `ui/dialog/scene_action_dialog.py` for file/monitor/layer selection. SceneSettingUI closes views/previews before extraction leases on shutdown; stopping playback preserves editor assets. Current-scene playback rejects a document changed during preparation. Legacy unnamed add_* methods remain compatible.

`utils/scene_format/scene_templates.py` defines three self-contained translated TEXT layouts, independent editable entries, proportional fitting to logical available screen size and missing-resource diagnostics. `ui/dialog/scene_templates_dialog.py` owns bounded QGraphics preview items, template/screen selection, target revalidation and owner-specific cancellation. SceneManagerUI and the command palette open one page-owned library. SceneActions.request_entries uses the same hidden candidate/adoption path as file scenes; cancel_request cancels only its matching pending/wanted operation. Application replaces the document after successful candidate preparation, preserving existing portable scene exports. The focus starter contains static editable reminders; existing scheduling/timer tools retain those responsibilities.

`show/scene/media_frame.py` owns bounded Qt video sink polling, hidden web surfaces and Imervue public offscreen Puppet rendering. Native decoder callbacks never run Python directly: polling retains the newest sink frame without queued-frame accumulation or stop/GIL deadlocks. Explicit activity pauses media and hidden hosts; shutdown stops and disconnects before disposal. Named VIDEO/WEB/PUPPET scene entries now share software/GPU layer transforms/z with IMAGE/GIF/TEXT; SOUND exposes a transparent frame. Standalone overlays and legacy unnamed add_puppet remain compatible. SceneCompositorView tracks visible-view owners, forwards mute and opens the same native web/Puppet host on double-click. `ui/page/scene_setting/scene_media_preview.py` retains at most eight manually enabled, initially muted providers across geometry edits; disabling/replacing closes them. Hidden editor previews pause, scripts are disabled for preview, and scene Puppet profiles are ephemeral. Provider factories permit device/network-free tests.

`utils/recording/avi_writer.py` implements silent incremental MJPEG AVI using Qt JPEG encoding, disk-streamed RIFF chunks and a disk index (one JPEG retained; 2 GiB/one hour/72,000 frames bounded). Dropped-frame intervals repeat the last JPEG to retain effective timing. It implements the existing AsyncGifWriter worker factory contract without changing GIF import paths. FrameRecorder selects GIF/AVI, exposes recording/paused/finalizing/cancelling/idle signals and accepted-frame/effective-duration/drop progress, excludes pauses using a monotonic offset and stops native region capture during pause. Resume reopens capture; stop while paused finalizes the same clip. GIF defaults/limits remain compatible; AVI supports teaching-length clips. ToolsSettingUI owns format, pause/resume/cancel controls and localized live status. Worker errors/cancel remove temporary output before any target replacement; index storage does not grow RAM with clip length.

`utils/scene_format/scene_animation.py` validates optional animation tracks at normalize_scene boundaries (128 unique increasing frames/layer, one hour, finite bounded x/y/opacity, linear/smooth interpolation). Scene v1 and portable exports retain tracks. `show/scene/timeline.py` shares monotonic pause/resume/seek/replay clocks, hidden suspension and baseline restoration across editor/playback. Scene-owned callbacks do not retain closed views; clear stops/disposes timelines. Named proxies retain saved entries separately from sampled geometry. `ui/dialog/scene_animation_dialog.py` edits tracks as one undoable change with fade/slide starters. SceneVisualEditor scrubs transient values, blocks geometry edits during preview and restores saved values on reset; playback controls reach each unique scene clock. SceneActions snapshots at most eight outgoing composed views (1920x1080 maximum), closes old native resources before adoption and starts a 0.5s dissolve on new views. Transition composition temporarily uses software raster plus premultiplied RGBA mixing with bounded row temporaries, then returns to normal layers. Animation pause also suspends media; replay applies to animation tracks, not arbitrary web application state.

`show/scene/render_session.py` owns an independent, hidden, software SceneCompositorView at fixed 640x480/1280x720/1920x1080 physical pixels, normalizes device-pixel ratio and never captures desktop pixels. It validates 256 layers/eight native sources/16 MP total raster bounds, source image sizes/resources and forwards media errors. Named SOUND uses a suspended SceneMediaFrame (transparent outside editor preview) so output can mute before any playback; legacy unnamed add_sound retains its factory behavior. `utils/virtual_camera/frame_sender.py` owns one camera worker and one latest detached RGB pending frame; startup/send/close occur off the GUI thread with explicit queued signal delivery. `ui/dialog/scene_output_dialog.py` requires explicit preview/send, displays renderer surfaces, keeps audio muted, handles slow/failing devices and closes on stop/Escape/owner shutdown/editor changes. It stops old file readers synchronously before SceneActions releases extraction leases; camera disposal is asynchronous and independent of files. SceneSettingUI owns/reuses one output dialog and closes it before SceneActions shutdown.

`utils/pet_pack/pack_builder.py` validates image action mappings and bounded traits, reads legacy aliases, copies only selected resources with cancellation into a staged new directory, and exports portable canonical sprites plus pet.json; no .puppet conversion or sound/script import. `ui/dialog/pet_pack_editor.py` runs at most one bounded file worker with queued results and cancellation, maps six actions and selects a completed export on PetSettingUI without spawning it. `pet_pack_preview.py` owns uncached scaled QMovie/static preview and a walk-speed timer, suspends on hide and releases on replacement/close. MainUI closes the editor before scene asset leases; no overlay registry entry because the preview is an ordinary child QWidget.

`utils/capture_editor/document.py` owns one detached physical-pixel original, a crop, bounded vector marks and twenty undo states; render flattens current edits with solid redactions last, QSaveFile atomically writes PNG only. `ui/dialog/capture_editor.py` maps view gestures through the crop offset, has a read-only original toggle and explicit edited copy/save/pin, and never mutates ToolsSettingUI.last_capture. ToolsSettingUI owns one delete-on-close editor, identity-checks dialog completion during replacement and adds pinned results to its existing registered pinned_widget_list. MainUI closes the editor at shutdown.

`utils/whiteboard/document.py` validates version-one .fewhiteboard JSON (50 pages/2000 strokes per page/100000 total points/eight MiB) and publishes atomic cancellable QSaveFile snapshots; WhiteboardDocument owns independent page views and twenty bounded active-page undo snapshots globally. `utils/whiteboard/raster.py` validates and renders one page using QPainter/QImage with full pen margins and bounds 8192 pixels/side/16 MP; no controls, selection or pan/zoom appear in exported PNG. `show/canvas/whiteboard_widget.py` keeps legacy active-page strokes/zoom/offset interfaces, selects by canvas-space segment distance and converts movement deltas through zoom. `whiteboard_controls.py` is a show-layer child toolbar (no upward UI dependency), owns one queued file worker, snapshots before background writes, applies fully validated reads on GUI, disables gestures while work is pending, requests cancellation and ignores late callbacks on close. Existing PresentationSettingUI whiteboard_widget_list remains the control-center/preset lifecycle source; no new registry required.

`utils/image_history/repository.py` is a worker-owned SQLite repository (memory by default, clipboard-images.sqlite3 beside settings only with consent). PNG payloads are bounded to 16 MP/eight MiB each, 10–200 images/8–128 MiB total; favorites count toward hard bounds. SQL transactions deduplicate, evict unpinned images and delete associated OCR text together; QImageReader checks dimensions before decoding database payloads. Persistent opt-out migrates to memory and removes disk data; clear VACUUM releases pages. Database max_page_count bounds main-file size to 132 MiB, not temporary rollback journals. `service.py` starts lazily, reads QClipboard only after opt-in, owns one repository thread and one latest pending detached image. Command and result mailboxes retain one newest value per allowed kind; GUI QTimer polls results, avoiding queued-image accumulation and cross-thread QWidget calls. Stop drops queues/disconnects clipboard and asynchronously closes the database. MainUI owns/configures/stops it; `ui/dialog/image_history_dialog.py` offers explicit settings, bounded thumbnail lists and explicit copy/pin/reference output. Pinned images and reference boards join existing registered lists; `ReferenceBoardWidget.add_pixmap` accepts bounded memory images. This does not enable existing text clipboard history, cloud upload or OCR.

`utils/screen_text/live_ocr.py` owns one GUI RegionSource (screen-local Qt coordinates on Windows/X11, one-frame asynchronous RegionCaptureAdapter on macOS) and one detached daemon OCR job per LiveOcrSession. GUI timers poll one result; close drops late results without waiting on an external API request. make_live_reader keeps local-only calls out of ScreenTextService cloud fallback even if global consent exists. `show/pinned/live_ocr_widget.py` is a temporary topmost QDialog with explicit refresh/5–60s automation, overlap rejection, twenty unique memory texts and explicit displayed-text copy; cloud fallback is opt-in per window and asks ToolsSettingUI to review existing screenshot/text consent only on an explicit button. No translation or cloud text action is implemented. ToolsSettingUI limits four windows, owns capture pickers and ocr_widget_list, while MainUI adds the list to control-center batch operations and closes windows during shutdown. These capture regions are not automatically resumed from sessions.

`utils/image_history/capture_service.py` specializes the bounded image history worker with local-only OCR and no clipboard provider. MainUI owns a separate default-off capture_history setting and capture-history.sqlite3; ToolsSettingUI.captured emits only explicit region capture QImages. The same single pending input/result mailbox bounds OCR work. Recognition failure saves the image with empty text and an explicit reason; successful text stays in the same SQL row, so remove/clear atomically remove the index. ImageHistoryDialog capture_mode adds debounced case-insensitive text/exact local-day search, reuse controls and independent opt-in. UTC/offset timestamps remain stored; repository date filtering and UI display use the user local timezone. No ScreenTextService/cloud consent/network path is involved. Lifecycle stops capture history with other MainUI services and closes both history dialogs.

`utils/todo/calendar_import.py` implements bounded local UTF-8 RFC5545 VEVENT/VTODO records: byte unfolding/TEXT decoding, UID+RECURRENCE-ID hashing, sequence/cancellation, date/floating/UTC/IANA-zone normalization and DST RelativeToBefore. DURATION nominal days preserve wall time; all-day/midnight end is exclusive in today_items. Unsupported recurrence sets and unknown TZID reject the whole transaction; no calendar synchronization, alarm, attachment or URL execution. `repository.py` validates version-one tasks.json, 500 records/four MiB and atomic QSaveFile save-before-publish, merging imports without duplicating checked items. `service.py` lazily starts one daemon document job, rejects overlap and polls one result; stop prevents not-yet-started writes and ignores late results without blocking. MainUI owns/stops TodoService. WidgetsSettingUI exposes TodoDialog and one todo_widget_list; MainUI registers/clears this list for batches/shutdown. `ui/dialog/todo_dialog.py` shares TodoPanel between manager and Today overlay; `show/notes/todo_widget.py` receives an injected panel factory to keep show→ui inversion out of modules. Date polling stops while hidden/closed. Task data persists independently from explicit widget visibility, is not part of presets and does not auto-reopen widgets.

Cancellation tombstones count toward the 500-record limit and prevent stale imports from resurrecting cancelled events. Clear all asks for confirmation and removes tasks, events and cancellation metadata. Interactive Today controls use ordinary Qt software painting so the compositor cannot cover them.

`utils/asset_library/inspect.py` decodes one bounded static image/GIF frame, first sprite/puppet texture and static scene image/text composition without executing native content. Portable scene extraction leases close after thumbnailing. `repository.py` persists 200 bounded version-one asset-library.json records independently from resources; tags/favorite/search retain missing files. `references.py` restricts rewrites to exact scene ASSET_FIELDS and known preset page path fields, leaves immutable history/literal text alone, and treats packages/external/managed Workshop documents as read-only. Relink plans snapshot reviewed raw bytes, validate matching type and limit 50 files/16 MiB. Atomic .asset-relink.json journals known old bytes/new hashes before multi-file updates; recovery verifies every current target and registered local scene/active preset authority before restoring, retaining unexpected conflicts. `file_lock.py` wraps OS-owned nonblocking byte/flock locks across a whole lazy serialized service job, so another app instance cannot recover a live transaction. `service.py` polls one result and cancels pending commit writes on stop. MainUI owns service/dialog and restores an unchanged in-flight editor path edit before scene teardown. `ui/dialog/asset_library_dialog.py` offers static thumbnail search/organization/reference review, applies current SceneEditorDocument as an undoable edit before durable commit, and restores it on failure only if the user has not subsequently edited it. Restart live playback after media path changes. No automatic scan, resource deletion or Steam content mutation.

`utils/window_pin/follow_window.py` isolates Win32 selected-target identity cookies/PID/thread checks and physical frame/move/monitor geometry. SetProp registration is reversible and may fail under UIPI; absence on HWND reuse stops following. WindowFollowService holds at most 64 weak temporary overlay bindings, polls only while bound, preserves initial proportional anchor, moves without native size/activation and clamps physical work areas. Event filters detach closing overlays and preserve manual visibility; ControlCenterUI.overlay_visibility_changed prevents target restoration undoing hide-all. MainUI owns/stops service, registers detach_all cleanup and reuses window_follow_dialog with existing overlay registry. Dialog never persists target handles; only verified Windows backend is enabled. Target hidden/closed/lost cookie detaches; minimize temporarily hides. Current native environment has one 125% display, so cross-monitor mixed-DPI remains explicit acceptance work.
