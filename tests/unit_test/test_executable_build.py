"""Reject incomplete build environments before invoking a compiler."""
import importlib.util
from importlib import metadata
from pathlib import Path

import pytest


@pytest.fixture
def builder():
    source = Path(__file__).parents[2] / "exe/build_exe.py"
    specification = importlib.util.spec_from_file_location("checked_build_exe", source)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_missing_cryptography_is_reported_before_compile(builder):
    def versions(name):
        if name == "cryptography":
            raise metadata.PackageNotFoundError(name)
        return "6.11.2" if name == "PySide6" else "999.0.0"
    assert builder.check_dependencies(versions) == ["cryptography>=42"]


def test_incompatible_qt_version_is_reported(builder):
    def versions(name):
        return "6.8.0" if name == "PySide6" else "999.0.0"
    errors = builder.check_dependencies(versions)
    assert len(errors) == 1 and "PySide6==6.11.2" in errors[0]


def test_dynamic_projection_is_packaged_and_appid_is_not(builder):
    command = builder.build_command("1.0.81", False)
    assert "--include-package=winrt" in command
    assert '--include-qt-plugins=multimedia,vectorimageformats' in command
    assert not any("steam_appid" in argument or "steam_sdk" in argument for argument in command)


def test_installed_optional_image_plugins_and_puppet_data_are_packaged(builder, monkeypatch):
    monkeypatch.setattr(builder, 'find_spec', lambda name: object())
    command = builder.build_command('1.0.81', False)
    assert '--include-package=PIL' in command
    assert '--include-package-data=Imervue' in command
    monkeypatch.setattr(builder, 'find_spec', lambda name: None)
    command = builder.build_command('1.0.81', False)
    assert '--include-package=PIL' not in command
    assert '--include-package-data=Imervue' not in command
