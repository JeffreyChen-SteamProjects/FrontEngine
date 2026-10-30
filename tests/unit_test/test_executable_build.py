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
        return {"PySide6": "6.12.0", "pygltflib": "1.16.5", "trimesh": "5.1.1"}.get(name, "999.0.0")
    assert builder.check_dependencies(versions) == ["cryptography>=42"]


def test_incompatible_qt_version_is_reported(builder):
    def versions(name):
        return {"PySide6": "6.8.0", "pygltflib": "1.16.5", "trimesh": "5.1.1"}.get(name, "999.0.0")
    errors = builder.check_dependencies(versions)
    assert len(errors) == 1 and "PySide6>=6.11.2,<6.13" in errors[0]


def test_dynamic_projection_is_packaged_and_appid_is_not(builder):
    command = builder.build_command("1.0.81", False)
    assert "--include-package=winrt" in command
    assert '--include-qt-plugins=multimedia,vectorimageformats' in command
    assert not any("steam_appid" in argument or "steam_sdk" in argument for argument in command)


def test_models_and_isolated_build_destination_are_packaged(builder, tmp_path):
    command = builder.build_command('1.0.81', False, tmp_path, jobs=2)
    assert '--include-package=pygltflib' in command
    assert '--include-package=trimesh' in command
    assert '--include-package-data=trimesh' in command
    assert '--output-dir='+str(tmp_path) in command
    assert '--jobs=2' in command


def test_nonpositive_build_jobs_are_rejected(builder, monkeypatch):
    monkeypatch.setattr(builder.sys, 'argv', ['build_exe.py', '--jobs', '0'])
    with pytest.raises(SystemExit) as error:
        builder.main()
    assert error.value.code == 2


@pytest.mark.parametrize('value, expected', [(None, 8), ('auto', 8), ('AUTO', 8), ('3', 3), ('16', 16),
                                             ('-1', 7), ('-7', 1)])
def test_build_jobs_default_to_every_core_and_accept_caps_or_spare_cores(builder, value, expected):
    assert builder.resolve_jobs(value, cpu_count=lambda: 8) == expected


@pytest.mark.parametrize('value', ['0', '-8', '-20', 'many', '2.5'])
def test_build_jobs_that_leave_nothing_to_build_with_are_rejected(builder, value):
    with pytest.raises(ValueError):
        builder.resolve_jobs(value, cpu_count=lambda: 8)


def test_unknown_core_count_still_builds_with_one_job(builder):
    assert builder.resolve_jobs(None, cpu_count=lambda: None) == 1


def test_installed_optional_image_plugins_and_puppet_data_are_packaged(builder, monkeypatch):
    monkeypatch.setattr(builder, 'find_spec', lambda name: object())
    command = builder.build_command('1.0.81', False)
    assert '--include-package=PIL' in command
    assert '--include-package-data=Imervue' in command
    monkeypatch.setattr(builder, 'find_spec', lambda name: None)
    command = builder.build_command('1.0.81', False)
    assert '--include-package=PIL' not in command
    assert '--include-package-data=Imervue' not in command
