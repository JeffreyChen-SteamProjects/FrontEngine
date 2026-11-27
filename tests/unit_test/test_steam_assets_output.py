"""steam_assets/generate.py reads a relative output folder against where it was started.

Importing the script would run trailer.py's staging (it changes the working directory and the Qt
platform), so the function is taken from the source and run on its own.
"""
import ast
import os
from pathlib import Path

import pytest

_SOURCE = Path(__file__).resolve().parents[2] / "steam_assets" / "generate.py"
_TREE = ast.parse(_SOURCE.read_text(encoding="utf-8"))


def _output_folder():
    node = next(item for item in _TREE.body if isinstance(item, ast.FunctionDef) and item.name == "output_folder")
    namespace = {"os": os}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(_SOURCE), "exec"), namespace)  # noqa: S102
    return namespace["output_folder"]


@pytest.fixture()
def elsewhere(tmp_path, monkeypatch):
    """The process sits in another folder, as it does once trailer.py has moved it."""
    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.chdir(staging)
    return tmp_path / "launch"


def test_a_relative_output_is_read_against_the_launch_folder(elsewhere):
    assert _output_folder()([os.path.join("art", "out")], elsewhere, "default") == str(elsewhere / "art" / "out")


def test_an_absolute_output_is_kept(elsewhere, tmp_path):
    target = tmp_path / "absolute"
    assert _output_folder()([str(target)], elsewhere, "default") == str(target)


def test_without_an_argument_the_default_is_used(elsewhere):
    assert _output_folder()([], elsewhere, "default") == "default"


def test_the_script_passes_trailers_launch_folder():
    assignment = next(item for item in _TREE.body if isinstance(item, ast.Assign)
                      and [target.id for target in item.targets if isinstance(target, ast.Name)] == ["OUT"])
    call = assignment.value
    assert isinstance(call, ast.Call) and call.func.id == "output_folder"
    assert ast.unparse(call.args[0]) == "sys.argv[1:]" and ast.unparse(call.args[1]) == "trailer.LAUNCH_DIR"
