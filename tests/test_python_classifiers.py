"""The PyPI classifiers name exactly the Python versions CI tests.

The package metadata listed only 3.10 while CI ran 3.10 to 3.12, so PyPI showed
the package as 3.10-only. A workflow matrix ``python-version: ["3.10", "3.11"]``
needs ``Programming Language :: Python :: 3.10`` and ``:: 3.11``, nothing more.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_MATRIX = re.compile(r"python-version:\s*\[([^\]]*)\]")
_CLASSIFIER = re.compile(r"Programming Language :: Python :: (3\.\d+)")


def _tested_versions() -> set[str]:
    """Return every Python version named in a workflow's ``python-version`` matrix."""
    versions: set[str] = set()
    for workflow in (REPO_ROOT / ".github" / "workflows").glob("*.yml"):
        for match in _MATRIX.finditer(workflow.read_text(encoding="utf-8")):
            versions.update(re.findall(r"3\.\d+", match.group(1)))
    return versions


def test_ci_has_a_python_matrix():
    assert _tested_versions()


@pytest.mark.parametrize("metadata", ["pyproject.toml", "stable.toml"])
def test_classifiers_match_the_ci_matrix(metadata):
    declared = set(_CLASSIFIER.findall((REPO_ROOT / metadata).read_text(encoding="utf-8")))
    assert declared == _tested_versions()
