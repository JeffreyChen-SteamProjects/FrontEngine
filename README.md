# FrontEngine

[Support this project on Steam](https://store.steampowered.com/app/2793470/FrontEngine/)

## About

FrontEngine is a lightweight and flexible framework designed to simplify automation and visualization tasks.  
It provides an intuitive interface and supports multiple media formats for interactive demonstrations.

![FrontEngine UI](image/FrontEngine.png)

---

## Features

- **GIFs & Animations**  
  *(GIFs may take time to load)*  
  ![GIF](gifs/play_gif.gif)  
  ![WEBP](gifs/webp.gif)

- **Video**  
  ![Video](gifs/video.gif)

- **Website**  
  ![Website](gifs/website.gif)

- **YouTube Showcase**  
  [Watch on YouTube](https://youtu.be/fewogcb3b8Y)

---

## Install

- **System Requirements**
  - Python **3.10+**
  - Windows 10/11 is the primary target; macOS and Linux are supported but may need extra OS dependencies.

- **From PyPI**
  ```bash
  pip install frontengine
  ```

- **Pre-built binaries**
  - [GitHub Releases](https://github.com/Intergration-Automation-Testing/FrontEngine/releases)

---

## Development

- Requires **Python 3.10+**.
- Install the dev toolchain:
  ```bash
  pip install -r dev_requirements.txt
  pip install -e .
  ```
- Run the unit smoke tests:
  ```bash
  python ./tests/unit_test/start/start_front_engine.py
  python ./tests/unit_test/start/extend_front_engine.py
  ```
- Contributions and pull requests are welcome!

---

## Continuous Integration & Release

This repository ships two GitHub Actions workflows:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `CI` (`.github/workflows/ci.yml`) | Push / PR to `main` or `dev`, daily cron | Matrix smoke test across Python 3.10 / 3.11 / 3.12 on Windows |
| `Release` (`.github/workflows/release.yml`) | A pull request is merged into `main` (or manual dispatch) | Auto-bumps the version in `stable.toml`/`pyproject.toml`, commits the bump back to `main`, swaps `stable.toml` → `pyproject.toml`, builds sdist + wheel, uploads to PyPI as `frontengine` via `twine`, creates a GitHub release tagged `v<version>` |

Publishing **only happens on merge to `main`** — pushing to `dev` runs CI but
never publishes. On merge, the workflow **automatically bumps the patch
segment** of the version (configurable via manual dispatch: `patch` / `minor`
/ `major`), commits the bump back to `main` with `[skip ci]`, then builds,
uploads, and releases under the new version. Both the PyPI upload and the
GitHub release see the bumped version, not the previous one.

### Cutting a new release

1. Merge a pull request into `main` — the patch version bumps automatically.
2. That's it. PyPI publish and GitHub release happen in one workflow run.

For a minor or major bump, trigger the workflow manually via *Actions →
Release → Run workflow* and pick the `bump` segment. That path also works
when you need to re-run a failed publish without a new merge.

### Required repository secrets

| Secret | Used by | Contents |
|--------|---------|----------|
| `PYPI_API_TOKEN` | `release.yml` | A PyPI API token scoped to the `frontengine` project |

The workflow uses `__token__` as the twine username, so only the token itself
needs to be stored.
