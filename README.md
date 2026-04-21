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
  - Stable release:
    ```bash
    pip install frontengine
    ```
  - Development release (tracks the `dev` branch):
    ```bash
    pip install frontengine_dev
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

This repository ships three GitHub Actions workflows:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `CI` (`.github/workflows/ci.yml`) | Push / PR to `main` or `dev`, daily cron | Matrix smoke test across Python 3.10 / 3.11 / 3.12 on Windows |
| `Release Dev` (`.github/workflows/release-dev.yml`) | Push to `dev`, or manual dispatch | Builds `frontengine_dev`, uploads to PyPI via `twine`, creates a GitHub **prerelease** tagged `dev-v<version>` |
| `Release Stable` (`.github/workflows/release-stable.yml`) | Push to `main`, or manual dispatch | Swaps `stable.toml` → `pyproject.toml`, builds `frontengine`, uploads via `twine`, creates a GitHub release tagged `v<version>` |

Each release workflow reads the version from the relevant pyproject file and
**skips cleanly** when the corresponding git tag already exists, so code-only
pushes to `main`/`dev` never republish the same version.

### Cutting a new release

1. Bump `version` in `pyproject.toml` (dev) or `stable.toml` (stable).
2. Commit and push to `dev` (or `main`).
3. The matching release workflow runs automatically.

### Required repository secrets

| Secret | Used by | Contents |
|--------|---------|----------|
| `PYPI_DEV_API_TOKEN` | `release-dev.yml` | A PyPI API token scoped to the `frontengine_dev` project |
| `PYPI_STABLE_API_TOKEN` | `release-stable.yml` | A PyPI API token scoped to the `frontengine` project |

The workflows use `__token__` as the twine username, so only the token itself
needs to be stored in secrets.
