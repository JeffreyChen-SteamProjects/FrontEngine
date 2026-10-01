"""The wheels install ``frontengine`` and nothing else.

With no ``include`` under ``[tool.setuptools.packages] find``, setuptools takes
every top-level directory that has an ``__init__.py``. Only ``frontengine/`` had
one, so the wheels were right by accident: an ``__init__.py`` added to ``tests/``,
``exe/`` or ``steam_assets/`` would have installed that directory as a top-level
package. Nothing is built here. The setting is read from both metadata files and
its patterns are matched the way setuptools matches them, against the packages in
the checkout. The TOML is read as text: ``tomllib`` is not in Python 3.10.
"""
from __future__ import annotations

import re
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Iterator

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "frontengine"
METADATA_FILES = ["pyproject.toml", "stable.toml"]
_FIND = re.compile(r"^\[tool\.setuptools\.packages\]\s*\nfind\s*=\s*\{(.*)\}\s*$", re.MULTILINE)


def _find_settings(metadata: str) -> dict[str, object]:
    """Return the inline ``find`` table of ``[tool.setuptools.packages]`` in a metadata file."""
    body = _FIND.search((REPO_ROOT / metadata).read_text(encoding="utf-8")).group(1)
    include = re.search(r"\binclude\s*=\s*\[([^\]]*)\]", body)
    namespaces = re.search(r"\bnamespaces\s*=\s*(true|false)\b", body)
    return {
        "keys": sorted(re.findall(r"(\w+)\s*=", body)),
        "include": re.findall(r'"([^"]+)"', include.group(1)) if include else None,
        "namespaces": namespaces.group(1) == "true" if namespaces else None,
    }


def _packages(directory: Path, prefix: str = "") -> Iterator[str]:
    """Yield the dotted name of every regular package below ``directory``."""
    for child in sorted(directory.iterdir()):
        if child.is_dir() and (child / "__init__.py").is_file():
            name = f"{prefix}{child.name}"
            yield name
            yield from _packages(child, f"{name}.")


@pytest.mark.parametrize("metadata", METADATA_FILES)
def test_discovery_is_limited_to_the_package(metadata):
    assert _find_settings(metadata) == {
        "keys": ["include", "namespaces"],
        "include": [PACKAGE, f"{PACKAGE}.*"],
        "namespaces": False,
    }


@pytest.mark.parametrize("metadata", METADATA_FILES)
def test_only_the_package_and_all_of_its_subpackages_are_selected(metadata):
    include = _find_settings(metadata)["include"]
    on_disk = set(_packages(REPO_ROOT))
    selected = {name for name in on_disk if any(fnmatchcase(name, pattern) for pattern in include)}
    assert PACKAGE in selected
    assert selected == {name for name in on_disk if name.split(".")[0] == PACKAGE}
