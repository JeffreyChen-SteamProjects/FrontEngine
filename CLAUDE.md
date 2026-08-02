# CLAUDE.md - FrontEngine

PySide6 desktop overlay app (Python 3.10+, qt-material, PyOpenGL, numpy).
Published on PyPI as `frontengine` (stable, `stable.toml`) and `frontengine_dev`
(dev, `pyproject.toml`). What it does and how to run it: `README.md`.

## Session progress log (check first)

`.claude/PROGRESS.md` records in-flight / unfinished work. Read it before
planning so you resume where the last session stopped.

- While working, record in-progress and pending items there.
- When **all** listed items are done, **clear the file** back to its header —
  leave no stale entries.
- It is tracked, so keep it free of anything that should not be public. Only
  `.claude/settings.local.json` stays ignored.

## Architecture

`architecture_explore.md` (repository root) is the authoritative map: every
module, the layering and dependency direction, the overlay contract, the
cross-cutting conventions and the extension points. **Read it before planning
structural work** — it lists what has to change together (the control-center
registry, seven language dictionaries, seven documentation trees).

**Keep it current.** Any structural change updates it **in the same commit as
the code**:

- adding, removing, renaming or moving a module, package, page or overlay
- changing what a module is responsible for, or the dependency direction
- changing a cross-cutting convention (`BaseWidget` contract, control-center
  registration, threading rules, settings persistence)
- adding or removing an extension point

Behaviour changes inside a module that keep its stated responsibility need no
edit. When unsure, open the file and check whether it is still true — a stale
map gets trusted before anyone notices it drifted. Line counts there are
indicative; refresh them when you touch the surrounding entry, don't chase them.

## Conventions

**Security** — the boundaries that actually exist in this code:

- User-supplied paths (media, pet packs, capture targets) go through
  `pathlib.Path` and must stay inside their intended directory. Preset packages
  take only the final path segment when extracting (zip-slip).
- External data — scene JSON, `user_setting.json`, Workshop items, plugin
  manifests — is validated at the boundary; malformed entries are skipped or
  rejected explicitly, never trusted through.
- Subprocess calls use list form with `shell=False` and a fixed allow-list of
  absolute paths (see `utils/platform_info`). Never interpolate user input.
- API keys come from the environment only and are never written to a settings
  file. No secrets in the repository.

**Qt / performance**:

- `QTimer` over `time.sleep()`; never block the GUI thread. Cross-thread
  signals need an explicit `QueuedConnection`.
- Overlays set `WA_TranslucentBackground` + `WA_DeleteOnClose`, default to
  opacity 0.2, and take their refresh interval from `utils/power_mode` so the
  quality tier reaches them.
- Release media, timers and native handles in `closeEvent` — closing is what
  runs it, dropping a Python reference is not.

**Style** — type hints on public signatures; bilingual (Chinese/English)
comments where they already exist, English-only for new code; functions under
50 lines.

**Testing** — `python -m pytest tests/ -q`, headless (`QT_QPA_PLATFORM=offscreen`,
set by `conftest.py`). Everything must pass before a PR. Anything touching the
outside world takes an injectable source so it can be tested with a fake.

## Git workflow

- **Branches**: `main` (stable releases), `dev` (active development).
- **Commits**: concise, imperative, say *what* and *why*.
  Good: `Fix particle widget memory leak on resize`. Bad: `update stuff`.
- **Authorship**: do NOT mention any AI tool or assistant in commit messages or
  `Co-Authored-By` lines. Commits are authored by the developer.
- **PRs**: one feature per PR, all CI green, and a structural change carries its
  `architecture_explore.md` update.
- **Versions**: `pyproject.toml` = dev, `stable.toml` = stable.

## Release announcements

`Update Note.txt` is the Steam announcement. It is **BBCode, not Markdown** —
`**bold**` and `### heading` would appear literally.

- Tags: `[h2]`, `[b]`, `[list]`/`[*]`, `[hr][/hr]`. There is no inline code —
  write formats and variable names as prose, or leave them out.
- **One paragraph per line, however long.** Steam turns a single newline into a
  hard line break, so 80-column wrapping arrives broken mid-sentence.
- `.txt` on purpose: BBCode in a `.md` renders as noise on GitHub.
- No title inside the file (Steam has its own field) and no `[img]` tags —
  screenshots are uploaded to Steam first and referenced by the URL it returns.
- **No version number.** Every merge to `main` bumps the version, so whatever is
  written is wrong the moment it lands. State the window the announcement
  covers instead.

Announce what a user can see. Workflow fixes, lint debt and tracked files do
not belong in it.
