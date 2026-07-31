"""Build the Windows executable with Nuitka.

Run from the repository root with the project virtualenv:

    .venv\\Scripts\\python.exe exe/build_exe.py            # standalone folder
    .venv\\Scripts\\python.exe exe/build_exe.py --onefile  # single .exe

Output lands in ``build/nuitka`` which is git-ignored. The build flags live here
rather than in a shell history so they survive between machines and sessions.
"""
from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENTRY_POINT = PROJECT_ROOT / "exe" / "start_front_engine.py"
ICON = PROJECT_ROOT / "exe" / "frontengine.ico"
OUTPUT_DIR = PROJECT_ROOT / "build" / "nuitka"

# These packages are reached through dynamic imports (Qt style sheets, backend
# selection, ctypes bindings), so Nuitka cannot see them by following imports.
# OpenGL_accelerate must be named explicitly: PyOpenGL only imports its
# submodules inside try/except blocks, so letting Nuitka discover them by
# following imports ships an incomplete set of .pyd files. The first partial
# import then fails with ImportError (swallowed), and the second attempt at the
# half-initialised Cython module aborts start-up with
# KeyError('__reduce_cython__').
DYNAMIC_PACKAGES = ("frontengine", "qt_material", "pynput", "OpenGL",
                    "OpenGL_accelerate")


def read_version() -> str:
    """Return the version declared in pyproject.toml."""
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as toml_file:
        return tomllib.load(toml_file)["project"]["version"]


def build_command(version: str, onefile: bool) -> list[str]:
    """Assemble the Nuitka command line."""
    command = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--enable-plugin=pyside6",
        "--windows-console-mode=disable",
        f"--windows-icon-from-ico={ICON}",
        "--output-filename=FrontEngine.exe",
        f"--output-dir={OUTPUT_DIR}",
        "--include-package-data=qt_material",
        # main_ui.py looks for frontengine.ico next to the working directory.
        f"--include-data-files={ICON}=frontengine.ico",
        "--company-name=JE-Chen",
        "--product-name=FrontEngine",
        f"--file-version={version}",
        f"--product-version={version}",
        "--file-description=FrontEngine desktop overlay",
        "--assume-yes-for-downloads",
        "--remove-output",
    ]
    command += [f"--include-package={package}" for package in DYNAMIC_PACKAGES]
    if onefile:
        command.append("--onefile")
    command.append(str(ENTRY_POINT))
    return command


def main() -> int:
    """Run the build and report where the executable landed."""
    onefile = "--onefile" in sys.argv[1:]
    command = build_command(read_version(), onefile)
    print(" ".join(command), flush=True)
    result = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if result.returncode == 0:
        built = OUTPUT_DIR / ("FrontEngine.exe" if onefile
                              else "start_front_engine.dist/FrontEngine.exe")
        print(f"Built {built}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
