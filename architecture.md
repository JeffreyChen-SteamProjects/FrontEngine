# FrontEngine Architecture

> Short overview for people and agents. Per-module detail lives in [`architecture_explore.md`](architecture_explore.md).
> Last verified: 2026-09-22 against `cee1fe6` on `main`.

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
| `frontengine/system_tray/` | Tray icon and menu |
| `frontengine/user_setting/` | `user_setting.json` (`user_setting_file.py`), preset repository (`presets/*.json` and zip packages), scene files |
| `frontengine/utils/` | Services and pure logic: platform info, hotkeys, input watch, remote/MIDI, audio, rules/schedules/state machines, recording, virtual camera, window pinning, translations with live retranslation (`multi_language/`), `plugins/`, `steam/`, `workshop/`, logging, JSON |
| `tests/` | `tests/unit_test/` runs headless (`tests/conftest.py` forces offscreen); `tests/unit_test/start/` holds the launch scripts CI runs |
| `docs/source/docs/` | Sphinx docs, one tree per UI language |
| `exe/` | Packaged entry `start_front_engine.py`; Nuitka build `build_exe.py` |
| `steam_assets/`, `Update Note.txt` | Steam store-art generator; Steam announcement (BBCode) |
| `pyproject.toml`, `stable.toml` | Dev (`frontengine_dev`) and stable (`frontengine`) metadata; `release.yml` bumps both |
| `.github/workflows/` | `ci.yml` (compile, tests, wheel smoke run), `nightly.yml` (cron only), `release.yml` |

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
  → save page state and geometry → write_user_setting() → close overlays → close scene
```

## 5. Extension points

- **Plugins**: `frontengine/utils/plugins/plugin_loader.py` loads `plugins/<name>/plugin.py` or
  `plugins/<name>.py` under the working directory. A module exposes
  `FRONTENGINE_TABS = {name: QWidget subclass}` and/or `register(registry)`; both fill
  `FrontEngine_EXTEND_TAB`. Loading is off by default (`load_plugins` setting, toggled in
  `ui/menu/settings_menu.py`) because plugins run with full app privileges.
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
