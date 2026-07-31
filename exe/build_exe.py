"""Build the Windows executable with Nuitka.

Run from the repository root with the project virtualenv:

    .venv\\Scripts\\python.exe exe/build_exe.py            # standalone folder
    .venv\\Scripts\\python.exe exe/build_exe.py --onefile  # single .exe

Output lands in ``build/nuitka`` which is git-ignored. The build flags live here
rather than in a shell history so they survive between machines and sessions.
"""
from __future__ import annotations

import subprocess  # nosec B404 - only ever runs the argv that build_command assembles
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
    # argv 全部在 build_command() 裡組好：sys.executable、寫死的旗標、由這個檔案
    # 位置算出來的 repo 路徑，以及 pyproject.toml 的版本字串。命令列參數只用來判斷
    # 有沒有 --onefile，內容不會進到 argv。list 形式、shell=False，沒有注入面。
    # Every element comes from build_command(): sys.executable, literal flags,
    # repo paths derived from this file's location, and the version string in
    # pyproject.toml. The command line is only checked for --onefile; its content
    # never reaches argv. List form, shell=False, so there is no injection surface.
    result = subprocess.run(  # nosec B603 # nosemgrep - argv assembled here, shell=False
        command, cwd=PROJECT_ROOT, check=False)
    if result.returncode == 0:
        built = OUTPUT_DIR / ("FrontEngine.exe" if onefile
                              else "start_front_engine.dist/FrontEngine.exe")
        print(f"Built {built}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
