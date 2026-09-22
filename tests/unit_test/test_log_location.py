"""Where FrontEngine's log goes, and that importing the package writes nothing (workspace item X-6)."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

from frontengine.utils.logging import loggin_instance
from frontengine.utils.logging.loggin_instance import (
    LOG_FILE_ENV,
    FrontEngineLoggingHandler,
    default_log_file,
)

MODULE_FILE = Path(loggin_instance.__file__)

# Load just this module in a fresh interpreter (skipping the package __init__, which pulls in
# Qt), then list the working directory.
_IMPORT_ONLY = (
    "import importlib.util, os, sys\n"
    "spec = importlib.util.spec_from_file_location('probe', sys.argv[1])\n"
    "spec.loader.exec_module(importlib.util.module_from_spec(spec))\n"
    "print(sorted(os.listdir('.')))\n"
)


def _log(handler: logging.Handler, message: str) -> None:
    log = logging.getLogger(f"test_log_location.{id(handler)}")
    log.propagate = False
    log.setLevel(logging.DEBUG)
    log.addHandler(handler)
    try:
        log.warning(message)
    finally:
        log.removeHandler(handler)
        handler.close()


def test_default_is_under_the_home_directory(monkeypatch, tmp_path):
    monkeypatch.delenv(LOG_FILE_ENV, raising=False)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    assert default_log_file() == tmp_path / ".frontengine" / "logs" / "FrontEngine.log"


def test_environment_variable_overrides_the_location(monkeypatch, tmp_path):
    monkeypatch.setenv(LOG_FILE_ENV, str(tmp_path / "custom.log"))
    assert default_log_file() == tmp_path / "custom.log"


def test_importing_writes_no_file(tmp_path):
    target = tmp_path / "home" / "FrontEngine.log"
    result = subprocess.run(  # nosec B603 - fixed interpreter, test-controlled arguments
        [sys.executable, "-c", _IMPORT_ONLY, str(MODULE_FILE)],
        cwd=tmp_path, env={**_base_env(), LOG_FILE_ENV: str(target)},
        capture_output=True, text=True, timeout=120, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]"
    assert not target.parent.exists()


def test_first_record_creates_the_directory_and_appends(tmp_path):
    target = tmp_path / "nested" / "FrontEngine.log"
    _log(FrontEngineLoggingHandler(filename=str(target), delay=True), "first")
    _log(FrontEngineLoggingHandler(filename=str(target), delay=True), "second")
    lines = target.read_text(encoding="utf-8").splitlines()
    assert [line.rsplit(" | ", 1)[1] for line in lines] == ["first", "second"]


def test_text_outside_cp950_and_lone_surrogates_are_kept(tmp_path):
    target = tmp_path / "FrontEngine.log"
    _log(FrontEngineLoggingHandler(filename=str(target)), "繁體 ⠐ \U0001F600 \udcff")
    written = target.read_text(encoding="utf-8")
    assert "繁體 ⠐ \U0001F600" in written
    assert "\\udcff" in written


def test_an_unopenable_path_turns_file_logging_off(tmp_path):
    blocker = tmp_path / "a_file"
    blocker.write_text("x", encoding="utf-8")
    handler = FrontEngineLoggingHandler(filename=str(blocker / "FrontEngine.log"), delay=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _log(handler, "goes nowhere")
    assert any(issubclass(item.category, RuntimeWarning) for item in caught)


@pytest.mark.parametrize("attribute", ["baseFilename", "mode", "encoding"])
def test_package_handler_defaults(attribute):
    expected = {"baseFilename": str(default_log_file().resolve()), "mode": "a", "encoding": "utf-8"}
    actual = getattr(loggin_instance.file_handler, attribute)
    if attribute == "baseFilename":
        actual = str(Path(actual).resolve())
    assert actual == expected[attribute]


def _base_env() -> dict:
    return {key: value for key, value in os.environ.items() if key != LOG_FILE_ENV}
