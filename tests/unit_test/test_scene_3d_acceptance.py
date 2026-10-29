"""Acceptance reports cannot mistake source execution or an omitted gate for success."""
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from frontengine.utils.scene_format import scene_3d_acceptance as acceptance


@pytest.mark.skipif(sys.platform not in ('win32', 'linux'), reason='Native image locator for this platform')
def test_hash_uses_running_image_when_runtime_executable_and_argv_are_invalid(monkeypatch, tmp_path):
    image = acceptance.executable_image()
    monkeypatch.setattr(sys, 'executable', str(tmp_path/'missing-python.exe'))
    monkeypatch.setattr(sys, 'argv', [str(tmp_path/'missing-entry.exe')])
    assert acceptance.executable_image() == image
    assert image.is_file()


def test_source_cannot_pass_frozen_gate_and_writes_durable_failure(tmp_path):
    report = tmp_path/'report'
    original = Path.cwd()
    assert acceptance.main(['--report', str(report), '--require-compiled']) == 1
    result = json.loads((report/'result.json').read_text(encoding='utf-8'))
    assert not result['completed'] and not result['compiled']
    assert result['camera'] == result['stress'] == result['media'] == 'not_run'
    assert 'requires the compiled executable' in result['error']
    assert Path.cwd() == original


def test_acceptance_rejects_reusing_evidence_directory(tmp_path):
    with pytest.raises(FileExistsError):
        acceptance.main(['--report', str(tmp_path), '--require-compiled'])


@pytest.mark.parametrize('vertices', ['9999', '1000001', '-1'])
def test_stress_workload_is_bounded_before_native_allocation(vertices):
    with pytest.raises(SystemExit) as error:
        acceptance.main(['--stress-vertices', vertices])
    assert error.value.code == 2


def test_executable_routes_3d_acceptance_before_application_import(monkeypatch):
    source = Path(__file__).parents[2]/'exe/start_front_engine.py'
    spec = importlib.util.spec_from_file_location('scene3d_entry', source)
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)
    arguments = ['--verify-3d-scene-build', 'report', '--require-compiled']
    received = []
    monkeypatch.setattr(sys, 'argv', ['FrontEngine.exe', *arguments])
    monkeypatch.setitem(sys.modules, 'frontengine.utils.scene_format.scene_3d_acceptance',
                        SimpleNamespace(main=lambda argv: received.append(argv) or 17))
    monkeypatch.setitem(sys.modules, 'frontengine.ui.main_ui',
                        SimpleNamespace(main=lambda: pytest.fail('Application imported before acceptance isolation')))
    with pytest.raises(SystemExit) as error:
        entry.main()
    assert error.value.code == 17 and received == [arguments]
