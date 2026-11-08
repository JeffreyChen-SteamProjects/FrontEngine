import json
import os
import pytest
from frontengine.user_setting.default_storage import acquire_default_binding, default_storage
from frontengine.user_setting.storage_session import StorageSession, StorageClosed, StorageInUse
from frontengine.user_setting.user_setting_file import user_setting_dict, read_user_setting, write_user_setting


def test_default_registry_rejects_inherited_process_before_mutex(monkeypatch):
    import importlib
    registry = importlib.import_module('frontengine.user_setting.default_storage')
    class UnavailableMutex:
        def __enter__(self):
            pytest.fail('Inherited registry attempted to enter its mutex')
        def __exit__(self, *_args):
            pass
    assert registry._owner is None
    monkeypatch.setattr(registry, '_pid', -1, raising=False)
    monkeypatch.setattr(registry, '_mutex', UnavailableMutex())
    with pytest.raises(StorageClosed):
        acquire_default_binding()


@pytest.mark.skipif(not hasattr(os, 'fork'), reason='Requires POSIX fork')
def test_forked_empty_default_registry_rejects_inherited_locked_mutex(monkeypatch):
    import importlib
    import select
    import signal
    from threading import Lock
    registry = importlib.import_module('frontengine.user_setting.default_storage')
    assert registry._owner is None
    mutex = Lock()
    monkeypatch.setattr(registry, '_mutex', mutex)
    mutex.acquire()
    read_fd, write_fd = os.pipe()
    child = os.fork()
    if child == 0:
        try:
            os.close(read_fd)
            try:
                acquire_default_binding()
            except StorageClosed:
                os.write(write_fd, b'ok')
                os._exit(0)
            os._exit(3)
        except BaseException:
            os._exit(4)
    os.close(write_fd)
    ready = False
    try:
        ready = bool(select.select([read_fd], [], [], 10)[0])
        assert ready, 'Inherited registry waited on its locked mutex'
        assert os.read(read_fd, 2) == b'ok'
    finally:
        if not ready:
            os.kill(child, signal.SIGKILL)
        _, status = os.waitpid(child, 0)
        os.close(read_fd)
        mutex.release()
    assert os.waitstatus_to_exitcode(status) == 0


def test_default_binding_never_reloads_live_and_reopens_latest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'user_setting.json').write_text('{"pet_mood": 31}')
    identity = id(user_setting_dict)
    first = acquire_default_binding()
    second = acquire_default_binding()
    try:
        assert id(user_setting_dict) == identity
        assert first.storage is second.storage
        user_setting_dict['pet_mood'] = 32
        read_user_setting()
        assert user_setting_dict['pet_mood'] == 32
        write_user_setting()
        stale = first.storage.profiles()
    finally:
        assert first.close()
        assert second.close()
    successor = StorageSession.open(tmp_path)
    successor.settings['pet_mood'] = 44
    successor.save_settings()
    successor.close()
    third = acquire_default_binding()
    try:
        assert user_setting_dict['pet_mood'] == 44
        with pytest.raises(StorageClosed):
            stale.create('old')
    finally:
        assert third.close()


def test_last_binding_waits_for_live_client_and_blocks_new_scope(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    binding = acquire_default_binding()
    client = binding.storage._hold('client')
    assert binding.close() is False
    with pytest.raises(StorageClosed):
        default_storage()
    with pytest.raises(StorageInUse):
        acquire_default_binding()
    client.release()
    assert binding.close()
    with pytest.raises(StorageClosed):
        default_storage()


def test_conflicting_ambient_root_cannot_rebind(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    binding = acquire_default_binding()
    other = tmp_path / 'other'
    other.mkdir()
    monkeypatch.chdir(other)
    try:
        with pytest.raises(StorageInUse):
            acquire_default_binding()
        assert binding.storage.directory == tmp_path
    finally:
        assert binding.close()


def test_bound_adapters_reject_before_successor_memory_mutation(tmp_path, monkeypatch):
    from frontengine.utils.actions.command_history import CommandHistory
    from frontengine.utils.measure.color_palette import ColorPalette
    monkeypatch.chdir(tmp_path)
    binding = acquire_default_binding()
    history = CommandHistory.for_storage(binding.storage)
    first = ColorPalette.for_storage(binding.storage)
    second = ColorPalette.for_storage(binding.storage)
    first.add('one', '', '#123456')
    second.add('two', '', '#654321')
    assert len(first.entries) == 2
    assert binding.close()
    successor = acquire_default_binding()
    try:
        before = json.dumps(user_setting_dict, sort_keys=True)
        with pytest.raises(StorageClosed):
            history.record('test', {'test'})
        with pytest.raises(StorageClosed):
            first.add('stale', '', '#ffffff')
        with pytest.raises(StorageClosed):
            _ = second.entries
        assert json.dumps(user_setting_dict, sort_keys=True) == before
    finally:
        assert successor.close()


def test_import_failure_restores_exported_mapping(tmp_path, monkeypatch):
    from frontengine.user_setting.user_setting_file import import_user_setting
    monkeypatch.chdir(tmp_path)
    binding = acquire_default_binding()
    source = tmp_path / 'import.json'
    source.write_text('{"pet_mood": 17, "new_key": 99}')
    before = dict(user_setting_dict)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(binding.storage, 'save_settings', lambda: (_ for _ in ()).throw(PermissionError('disk')))
            with pytest.raises(PermissionError):
                import_user_setting(source)
        assert user_setting_dict == before
    finally:
        assert binding.close()


def test_bound_portrait_uses_captured_root_and_rejects_old_callback(tmp_path, monkeypatch):
    from PySide6.QtGui import QImage
    owner = StorageSession.open(tmp_path / 'owned')
    profiles = owner.profiles()
    identifier = profiles.create()['id']
    other = tmp_path / 'other'
    other.mkdir()
    monkeypatch.chdir(other)
    image = QImage(4, 4, QImage.Format.Format_ARGB32)
    image.fill(0xff123456)
    assert profiles.remember_portrait(identifier, image)
    assert profiles.look_for(identifier)[1] == owner.directory / 'pet-home-looks' / (identifier + '.png')
    assert not (other / 'pet-home-looks').exists()
    owner.close()
    with pytest.raises(StorageClosed):
        profiles.remember_portrait(identifier, image)


@pytest.mark.parametrize('owned', [False, True])
def test_palette_export_cannot_replace_managed_files(tmp_path, owned):
    from frontengine.utils.measure.color_palette import ColorPalette
    owner = StorageSession.open(tmp_path) if owned else None
    palette = ColorPalette.for_storage(owner) if owned else ColorPalette({}, lambda: None)
    try:
        target = tmp_path / 'pet-home.json'
        target.write_bytes(b'preserved home')
        with pytest.raises(OSError):
            palette.export(target, 'json')
        assert target.read_bytes() == b'preserved home'
        output = tmp_path / 'palette.json'
        palette.export(output, 'json')
        assert json.loads(output.read_text())['format'] == 'frontengine.palette'
    finally:
        if owner is not None:
            owner.close()
