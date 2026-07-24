# CLAUDE.md - FrontEngine

## Session Progress Log (check first)

At the start of every session, check `.claude/PROGRESS.md` — a local, git-ignored
scratch record of in-flight / unfinished work. Read it before planning so you can
resume where the last session left off.

- While working: record in-progress and pending items there.
- When **all** listed items are done (merged/verified), **clear the file** — reset it
  to just its header/instructions, leaving no stale entries.
- It is local-only (ignored via `/.claude/`); never rely on it being committed.

## Project Overview

FrontEngine is a PySide6-based desktop overlay framework for displaying GIFs, images, videos, web content, particles, text, and sound on screen. It supports Windows, macOS, and Linux. Published on PyPI as `frontengine` (stable) and `frontengine_dev` (dev).

- **Language**: Python 3.10+
- **UI Framework**: PySide6, qt-material theme
- **Graphics**: PyOpenGL, numpy
- **Build**: setuptools via `pyproject.toml` (dev) / `stable.toml` (stable)

## Architecture

```
frontengine/
  show/          # Display widgets (GIF, image, video, web, particle, text, sound, scene)
    base_widget.py   # Abstract base for all overlay widgets
  ui/            # Main UI, settings pages, menus, dialogs
    main_ui.py       # Application main window
    page/            # Tabbed setting pages per feature
    menu/            # Help, how-to, language menus
    dialog/          # File chooser, save dialogs
  system_tray/   # System tray integration
  worker/        # QThread-based background workers
  user_setting/  # User preference persistence
  utils/         # Browser, logging, JSON, i18n, file, exception utilities
```

## Design Patterns & Principles

- **Template Method**: `BaseWidget` defines the skeleton; subclasses override rendering.
- **Strategy**: Each show widget (GIF, video, web, etc.) is an interchangeable display strategy.
- **Observer**: Qt signal/slot for decoupled UI event handling.
- **Single Responsibility**: Each module under `show/`, `ui/page/`, `utils/` owns one concern.
- **Open/Closed**: Add new widget types by extending `BaseWidget`, not modifying existing code.
- **DRY**: Shared logic lives in `base_widget.py` and `utils/`.

## Coding Standards

### Security (Mandatory)

- **No eval/exec**: Never use `eval()`, `exec()`, or `__import__()` with user input.
- **Path traversal**: Always validate and sanitize file paths. Use `pathlib.Path` and reject paths containing `..` when handling user-supplied paths.
- **Input validation**: Validate all external input (file dialogs, user settings JSON, command-line args) at system boundaries.
- **No hardcoded secrets**: Never commit API keys, tokens, or credentials.
- **Dependency awareness**: Pin dependency versions. Review CVEs before upgrading.
- **Subprocess safety**: If calling subprocesses, never pass unsanitized user input. Use list form, never shell=True with user data.
- **Deserialization**: Never use `pickle.loads()` or `yaml.load()` on untrusted data. Use `json.loads()` or `yaml.safe_load()`.

### Performance

- **Lazy loading**: Load heavy resources (videos, images, OpenGL contexts) only when needed.
- **Object pooling**: Reuse widget instances where possible instead of recreating.
- **Minimize paint calls**: Batch UI updates; avoid redundant `update()` / `repaint()`.
- **Use Qt timers**: Prefer `QTimer` over Python `time.sleep()` to avoid blocking the event loop.
- **Memory management**: Set `Qt.WA_DeleteOnClose`; explicitly release large buffers and media resources.
- **Thread offloading**: Use `QThread` workers for I/O and computation; never block the main thread.

### Code Style

- Follow PEP 8. Use snake_case for functions/variables, PascalCase for classes.
- Type hints on all public function signatures.
- Bilingual comments (Chinese/English) where they already exist; English-only for new code.
- Keep functions under 50 lines. Extract helpers when complexity grows.
- No unused imports, dead code, or commented-out blocks.

### Testing

- Tests live in `tests/unit_test/`.
- All tests must pass before opening a PR.
- Ensure cross-platform compatibility (Windows, macOS, Linux).

## Git Workflow

- **Branches**: `main` (stable releases), `dev` (active development).
- **Commit messages**: Concise, imperative mood. Describe *what* and *why*.
  - Good: `Fix particle widget memory leak on resize`
  - Good: `Add WebP animation support to GIF widget`
  - Bad: `update stuff`
- **Commit authorship**: Do NOT mention any AI tool or assistant in commit messages or Co-Authored-By lines. Commits are authored by the developer.
- **PR rules**: One feature per PR. All CI checks must pass.
- **Version updates**: `pyproject.toml` = dev version, `stable.toml` = stable version.

## Build & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Install in dev mode
pip install -e .

# Run tests
python -m pytest tests/

# Build package
python -m build
```

## Key Conventions

- Widget opacity defaults to 0.2 (translucent overlay).
- All overlay windows use `WA_TranslucentBackground` and `WA_DeleteOnClose`.
- User settings are stored as JSON via `user_setting/` module.
- Multi-language support via `utils/multi_language/`.
