import json
import importlib.util
import os
import py_compile
import sys

import pytest

from frontengine.utils.plugins.plugin_loader import load_plugins


def plugin(tmp_path, permissions=None):
    directory = tmp_path / 'hello'
    directory.mkdir()
    marker = tmp_path / 'executed'
    (directory / 'plugin.py').write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\nFRONTENGINE_TABS = {{'hello': type('Tab', (), {{}})}}\n",
        encoding='utf-8')
    if permissions is not None:
        (directory / 'plugin.json').write_text(json.dumps({
            'version': 1, 'id': 'hello', 'api_version': 1,
            'entrypoint': 'plugin.py', 'permissions': permissions}), encoding='utf-8')
    return directory, marker


def test_enabled_without_grant_does_not_execute_plugin(tmp_path):
    _, marker = plugin(tmp_path, ['network'])
    assert load_plugins({}, enabled=True, base=str(tmp_path)) == []
    assert not marker.exists()


def test_grant_is_bound_to_all_plugin_content(tmp_path):
    directory, marker = plugin(tmp_path, ['filesystem'])
    grants = {}
    assert load_plugins({}, True, str(tmp_path), grants=grants,
                        authorizer=lambda manifest: True) == ['hello']
    marker.unlink()
    assert load_plugins({}, True, str(tmp_path), grants=grants) == ['hello']
    marker.unlink()
    (directory / 'helper.py').write_text('changed = True\n', encoding='utf-8')
    assert load_plugins({}, True, str(tmp_path), grants=grants) == []
    assert not marker.exists()


def test_unknown_permission_rejected_before_import(tmp_path):
    _, marker = plugin(tmp_path, ['whatever'])
    assert load_plugins({}, True, str(tmp_path), authorizer=lambda manifest: True) == []
    assert not marker.exists()


def test_legacy_plugin_requires_explicit_full_trust(tmp_path):
    _, marker = plugin(tmp_path)
    assert load_plugins({}, True, str(tmp_path)) == []
    assert not marker.exists()
    seen = []
    assert load_plugins({}, True, str(tmp_path),
                        authorizer=lambda manifest: seen.append(manifest.legacy) or True) == ['hello']
    assert seen == [True]


@pytest.mark.parametrize('entry', ['../plugin.py', '/plugin.py', 'nested/../plugin.py'])
def test_manifest_entry_cannot_escape_plugin(tmp_path, entry):
    directory, marker = plugin(tmp_path, [])
    manifest = json.loads((directory / 'plugin.json').read_text())
    manifest['entrypoint'] = entry
    (directory / 'plugin.json').write_text(json.dumps(manifest), encoding='utf-8')
    assert load_plugins({}, True, str(tmp_path), authorizer=lambda manifest: True) == []
    assert not marker.exists()


def test_imported_settings_cannot_grant_plugin_execution(tmp_path, monkeypatch):
    from frontengine.user_setting import user_setting_file as settings
    monkeypatch.setattr(settings, 'write_user_setting', lambda: None)
    monkeypatch.setattr(settings, 'user_setting_dict', {'plugin_grants': {'original': 'digest'}})
    path = tmp_path / 'settings.json'
    path.write_text(json.dumps({'plugin_grants': {'attacker': 'digest'}, 'opacity': 20}), encoding='utf-8')
    settings.import_user_setting(path)
    assert settings.user_setting_dict['plugin_grants'] == {'original': 'digest'}


def test_modified_timestamp_valid_bytecode_requires_approval(tmp_path):
    from frontengine.utils.plugins.plugin_manifest import read_manifest
    directory, marker = plugin(tmp_path, [])
    entry = directory / 'plugin.py'
    manifest = read_manifest(entry)
    grants = {manifest.grant_key: manifest.digest}
    original = entry.read_text(encoding='utf-8')
    evil = tmp_path / 'evil.py'
    evil.write_text(original.replace("'hello'", "'owned'"), encoding='utf-8')
    assert evil.stat().st_size == entry.stat().st_size
    stamp = entry.stat()
    os.utime(evil, (stamp.st_atime, stamp.st_mtime))
    cached = __import__('pathlib').Path(importlib.util.cache_from_source(str(entry)))
    cached.parent.mkdir()
    py_compile.compile(str(evil), cfile=str(cached), dfile=str(entry), doraise=True)
    assert load_plugins({}, True, str(tmp_path), grants=grants) == []
    assert not marker.exists()


def test_plugin_loading_does_not_generate_cache_or_invalidate_grant(tmp_path):
    directory, _ = plugin(tmp_path, [])
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = False
    try:
        grants = {}
        assert load_plugins({}, True, str(tmp_path), grants=grants,
                            authorizer=lambda _: True) == ['hello']
        assert not (directory / '__pycache__').exists()
        assert sys.dont_write_bytecode is False
        assert load_plugins({}, True, str(tmp_path), grants=grants) == ['hello']
    finally:
        sys.dont_write_bytecode = previous


def test_single_file_plugin_grant_includes_helper_bytecode(tmp_path):
    from frontengine.utils.plugins.plugin_manifest import read_manifest
    entry = tmp_path / 'simple.py'
    entry.write_text('FRONTENGINE_TABS = {}\n', encoding='utf-8')
    before = read_manifest(entry).digest
    helper = tmp_path / '__pycache__'
    helper.mkdir()
    (helper / 'helper.pyc').write_bytes(b'modified executable cache')
    assert read_manifest(entry).digest != before
