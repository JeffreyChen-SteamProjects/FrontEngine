"""Both release channels must install the same runtime dependencies."""
from pathlib import Path

import pytest

tomllib = pytest.importorskip("tomllib")


def test_release_channels_use_the_same_runtime_dependencies():
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle:
        development = tomllib.load(handle)["project"]["dependencies"]
    with (root / "stable.toml").open("rb") as handle:
        stable = tomllib.load(handle)["project"]["dependencies"]
    assert sorted(stable) == sorted(development)
