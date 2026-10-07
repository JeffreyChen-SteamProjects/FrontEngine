"""Acceptance boundaries and entry routing without starting native media or listeners."""
import json
import sys
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QUrl
from exe import scene_build_acceptance as acceptance
from exe import start_front_engine as entry


@pytest.fixture
def fixtures(tmp_path):
    entries = {}
    for kind in acceptance.KINDS:
        item = {'type': kind}
        if kind == 'WEB':
            path = tmp_path / 'web.html'
            path.write_text('<body>own fixture</body>', encoding='utf-8')
            item['url'] = QUrl.fromLocalFile(str(path)).toString()
        elif kind != 'TEXT':
            path = tmp_path / (kind.lower() + '.fixture')
            path.write_bytes(b'own fixture')
            item['file_path'] = path.name
        entries[kind.lower()] = item
    (tmp_path / 'scene.json').write_text(json.dumps(entries), encoding='utf-8')
    return tmp_path, entries


def test_acceptance_requires_local_assets_and_preserves_legacy_mapping(fixtures):
    directory, entries = fixtures
    loaded = acceptance.checked_fixtures(directory)
    assert {entry['type'] for entry in loaded.values()} == acceptance.KINDS
    assert loaded['image']['file_path'] == str(directory / entries['image']['file_path'])


@pytest.mark.parametrize('change, reason', [
    (lambda data: data.pop('gif'), 'exactly one'),
    (lambda data: data['web'].update(url='https://example.test'), 'must be local'),
    (lambda data: data['image'].update(file_path='../outside.png'), 'outside'),
    (lambda data: data['puppet'].update(script_path='script.py'), 'must not contain scripts'),
])
def test_acceptance_rejects_missing_types_network_escaping_assets_and_scripts(fixtures, change, reason):
    directory, entries = fixtures
    change(entries)
    (directory / 'scene.json').write_text(json.dumps(entries), encoding='utf-8')
    with pytest.raises(ValueError, match=reason):
        acceptance.checked_fixtures(directory)


def test_packaged_entry_routes_acceptance_before_application_import(monkeypatch):
    calls = []
    arguments = ['FrontEngine.exe', '--verify-scene-build', 'fixtures', 'report']
    monkeypatch.setattr(sys, 'argv', arguments)
    monkeypatch.setitem(sys.modules, 'scene_build_acceptance', SimpleNamespace(main=lambda args: calls.append(args) or 3))
    with pytest.raises(SystemExit) as result:
        entry.main()
    assert result.value.code == 3 and calls == [arguments[1:]]


def test_packaged_normal_entry_keeps_preset_debug_arguments(monkeypatch):
    from frontengine.ui import main_ui
    calls = []
    arguments = ['FrontEngine.exe', '--preset', 'own', '--debug']
    monkeypatch.setattr(sys, 'argv', arguments)
    monkeypatch.setattr(main_ui, 'main', lambda: calls.append(sys.argv[:]))
    entry.main()
    assert calls == [arguments]
