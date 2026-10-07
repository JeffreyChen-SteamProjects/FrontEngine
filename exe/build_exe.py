"""Build the Windows executable with Nuitka.

Run from the repository root with the project virtualenv:

    .venv\\Scripts\\python.exe exe/build_exe.py            # standalone folder
    .venv\\Scripts\\python.exe exe/build_exe.py --onefile  # single .exe

Output lands in ``build/nuitka`` which is git-ignored. The build flags live here
rather than in a shell history so they survive between machines and sessions.
"""
from __future__ import annotations

import subprocess  # nosec B404 - only ever runs the argv that build_command assembles
import argparse
import shutil
from importlib import metadata
from importlib.util import find_spec
import sys
import tomllib
from pathlib import Path

from packaging.requirements import Requirement

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
                    "OpenGL_accelerate", "winrt")


def read_version() -> str:
    """Return the version declared in pyproject.toml."""
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as toml_file:
        return tomllib.load(toml_file)["project"]["version"]


def check_dependencies(version_lookup=None) -> list[str]:
    """Fail before a costly compile when the build environment lacks runtime requirements."""
    lookup = version_lookup or metadata.version
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as stream:
        requirements = tomllib.load(stream)["project"]["dependencies"]
    missing = []
    for specification in requirements:
        requirement = Requirement(specification)
        if requirement.marker and not requirement.marker.evaluate():
            continue
        try:
            installed = lookup(requirement.name)
            if installed not in requirement.specifier:
                missing.append(f"{specification} (installed {installed})")
        except metadata.PackageNotFoundError:
            missing.append(specification)
    return missing


def build_command(version: str, onefile: bool) -> list[str]:
    """Assemble the Nuitka command line."""
    command = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--enable-plugin=pyside6",
        "--include-qt-plugins=multimedia,vectorimageformats",
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
    # Pillow loads decoder plugins dynamically; optional puppet assets may need package data.
    if find_spec('PIL') is not None:
        command.append('--include-package=PIL')
    if find_spec('Imervue') is not None:
        command.append('--include-package-data=Imervue')
    if onefile:
        command.append("--onefile")
    command.append(str(ENTRY_POINT))
    return command


def validated_runtime(source: str) -> Path:
    """Require an explicitly selected Windows x64 Steam runtime, not the whole SDK."""
    path = Path(source).absolute()
    if path.name.lower() != "steam_api64.dll" or path.is_symlink() or not path.is_file():
        raise ValueError("Choose the SDK's Windows x64 steam_api64.dll")
    with path.open("rb") as stream:
        header = stream.read(64)
        if len(header) != 64 or header[:2] != b"MZ":
            raise ValueError("Steam runtime is not a Windows DLL")
        stream.seek(int.from_bytes(header[60:64], "little"))
        if stream.read(6) != b"PE\0\0\x64\x86":
            raise ValueError("Steam runtime must target Windows x64")
    return path


def main() -> int:
    """Run the build and report where the executable landed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onefile", action="store_true")
    parser.add_argument("--steam-runtime", help="Explicit steam_api64.dll to ship beside the executable")
    args = parser.parse_args()
    missing = check_dependencies()
    if missing:
        parser.error("Install requirements.txt in this Python environment before building: " + "; ".join(missing))
    try:
        runtime = validated_runtime(args.steam_runtime) if args.steam_runtime else None
    except (OSError, ValueError) as error:
        parser.error(str(error))
    onefile = args.onefile
    command = build_command(read_version(), onefile)
    print(" ".join(command), flush=True)
    # argv 全部在 build_command() 裡組好：sys.executable、寫死的旗標、由這個檔案
    # 位置算出來的 repo 路徑，以及 pyproject.toml 的版本字串。命令列參數只用來判斷
    # 有沒有 --onefile，內容不會進到 argv。list 形式、shell=False，沒有注入面。
    # Build arguments are assembled as a list, with shell=False. The selected
    # runtime is validated separately and copied only after a successful build.
    result = subprocess.run(  # nosec B603 # nosemgrep - argv assembled here, shell=False
        command, cwd=PROJECT_ROOT, check=False)
    if result.returncode == 0:
        built = OUTPUT_DIR / ("FrontEngine.exe" if onefile
                              else "start_front_engine.dist/FrontEngine.exe")
        print(f"Built {built}")
        if runtime:
            shutil.copyfile(runtime, built.parent / "steam_api64.dll")
            print("Included the selected Steam runtime beside the executable")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
