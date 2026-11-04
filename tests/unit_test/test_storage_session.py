"""Owned snapshots cannot outlive the directory that admitted them."""
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Event, Thread
from time import monotonic, sleep

import pytest

from frontengine.user_setting.storage_session import (
    LOCK_NAME, StorageBusy, StorageClosed, StorageInUse, StorageSession, StorageUnavailable,
)
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.exception.exceptions import FrontEngineJsonFileException
from frontengine.utils.json.json_repository import JsonRepository


@pytest.fixture
def owner(tmp_path):
    session = StorageSession.open(tmp_path / "owned")
    yield session
    session.close()


def test_loads_fresh_defaults_after_acquiring_and_keeps_captured_directory(tmp_path, monkeypatch):
    directory = tmp_path / "original"
    directory.mkdir()
    (directory / "user_setting.json").write_text('{"pet_mood": 42}', encoding="utf-8")
    monkeypatch.setitem(user_setting_dict, "pet_affection", 12345)
    session = StorageSession.open(directory)
    try:
        assert session.settings["pet_mood"] == 42
        assert session.settings["pet_affection"] == 0
        other = tmp_path / "other"
        other.mkdir()
        monkeypatch.chdir(other)
        session.settings["pet_mood"] = 43
        assert session.save_settings() == directory / "user_setting.json"
        assert not (other / "user_setting.json").exists()
    finally:
        session.close()
    successor = StorageSession.open(directory)
    try:
        assert successor.settings["pet_mood"] == 43
    finally:
        successor.close()


def test_competing_owner_refuses_before_settings_read(owner, monkeypatch):
    def forbidden_load(*_args, **_kwargs):
        pytest.fail("Contender read protected settings before owning the directory")

    monkeypatch.setattr(JsonRepository, "load", forbidden_load)
    with pytest.raises(StorageInUse):
        StorageSession.open(owner.directory / ".")
    if os.name == "nt":
        with pytest.raises(StorageInUse):
            StorageSession.open(Path(str(owner.directory).upper()))


def test_independent_directories_have_independent_nested_settings(owner, tmp_path):
    other = StorageSession.open(tmp_path / "other")
    try:
        owner.settings["overlay_geometry"]["Pet"] = [1, 2, 3, 4]
        assert other.settings["overlay_geometry"] == {}
        owner.save_settings()
        other.save_settings()
    finally:
        other.close()


def test_failed_initial_load_releases_ownership_for_retry(tmp_path, monkeypatch):
    def fail_load(*_args):
        raise ValueError("load")

    with monkeypatch.context() as patch:
        patch.setattr(JsonRepository, "load", fail_load)
        with pytest.raises(ValueError, match="load"):
            StorageSession.open(tmp_path)
    session = StorageSession.open(tmp_path)
    session.close()


def test_settings_access_failure_is_typed_and_releases_owner(tmp_path, monkeypatch):
    original = Path.lstat

    def deny_settings(path):
        if path.name == "user_setting.json":
            raise PermissionError("settings metadata denied")
        return original(path)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "lstat", deny_settings)
        with pytest.raises(StorageUnavailable, match="settings metadata denied"):
            StorageSession.open(tmp_path)
    session = StorageSession.open(tmp_path)
    session.close()


def test_unreadable_settings_do_not_become_a_writable_default_snapshot(tmp_path, monkeypatch):
    def deny_read(_repository):
        try:
            raise PermissionError("settings read denied")
        except OSError as error:
            raise FrontEngineJsonFileException("read failed") from error

    with monkeypatch.context() as patch:
        patch.setattr(JsonRepository, "load", deny_read)
        with pytest.raises(StorageUnavailable, match="settings read denied"):
            StorageSession.open(tmp_path)
    session = StorageSession.open(tmp_path)
    session.close()


def test_live_idle_client_prevents_close_and_repeated_release_is_safe(owner):
    client = owner._hold("pet")
    try:
        with pytest.raises(StorageBusy):
            owner.close()
        with pytest.raises(StorageInUse):
            StorageSession.open(owner.directory)
    finally:
        client.release()
    client.release()
    owner.close()
    owner.close()


def test_admitted_worker_prevents_release_and_stale_callback_cannot_write(owner, monkeypatch):
    entered, finish = Event(), Event()
    errors = []
    original = JsonRepository.save

    def delayed_save(repository, data):
        entered.set()
        assert finish.wait(10)
        return original(repository, data)

    def save():
        try:
            owner.save_settings()
        except BaseException as error:
            errors.append(error)

    callback = owner.save_settings
    with monkeypatch.context() as patch:
        patch.setattr(JsonRepository, "save", delayed_save)
        worker = Thread(target=save)
        worker.start()
        try:
            assert entered.wait(10)
            with pytest.raises(StorageBusy):
                owner.close()
            with pytest.raises(StorageInUse):
                StorageSession.open(owner.directory)
        finally:
            finish.set()
            worker.join(10)
        assert not worker.is_alive() and not errors
    owner.close()
    successor = StorageSession.open(owner.directory)
    try:
        successor.settings["pet_mood"] = 90
        successor.save_settings()
        before = (owner.directory / "user_setting.json").read_bytes()
        with pytest.raises(StorageClosed):
            callback()
        assert (owner.directory / "user_setting.json").read_bytes() == before
        assert successor.settings["pet_mood"] == 90
    finally:
        successor.close()


@pytest.mark.parametrize("name", ["user_setting.json", "user_setting.json.tmp", LOCK_NAME])
def test_managed_hardlinks_are_rejected_without_changing_target(tmp_path, name):
    target = tmp_path / "external.json"
    target.write_text('{"keep": true}', encoding="utf-8")
    directory = tmp_path / "owned"
    directory.mkdir()
    os.link(target, directory / name)
    before = target.read_bytes()
    if name.endswith(".tmp"):
        session = StorageSession.open(directory)
        try:
            with pytest.raises(StorageUnavailable):
                session.save_settings()
        finally:
            session.close()
    else:
        with pytest.raises(StorageUnavailable):
            StorageSession.open(directory)
    assert target.read_bytes() == before


def test_write_failure_retains_owner_and_last_good_file(owner, monkeypatch):
    owner.save_settings()
    before = (owner.directory / "user_setting.json").read_bytes()

    def deny_replace(*_args):
        raise PermissionError("disk unavailable")

    with monkeypatch.context() as patch:
        patch.setattr(os, "replace", deny_replace)
        with pytest.raises(FrontEngineJsonFileException, match="disk unavailable"):
            owner.save_settings()
        with pytest.raises(StorageInUse):
            StorageSession.open(owner.directory)
        assert (owner.directory / "user_setting.json").read_bytes() == before
    owner.settings["pet_mood"] = 12
    owner.save_settings()
    assert json.loads((owner.directory / "user_setting.json").read_text())["pet_mood"] == 12


_CHILD = """
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from frontengine.user_setting.storage_session import StorageSession
owner = StorageSession.open(Path(sys.argv[2]))
owner.settings['pet_mood'] = 88
owner.save_settings()
print('OWNER_READY', flush=True)
sys.stdin.readline()
owner.close()
"""


@pytest.mark.parametrize("crash", [False, True])
def test_actual_process_owner_release_and_crash_reacquisition(tmp_path, crash):
    root = Path(__file__).resolve().parents[2]
    process = subprocess.Popen([sys.executable, "-u", "-c", _CHILD, str(root), str(tmp_path)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
    try:
        assert process.stdout.readline().strip() == "OWNER_READY"
        assert process.poll() is None
        with pytest.raises(StorageInUse):
            StorageSession.open(tmp_path)
        if crash:
            process.kill()
            process.communicate(timeout=10)
            assert process.returncode != 0
        else:
            _, stderr = process.communicate("close\n", timeout=10)
            assert process.returncode == 0, stderr
        deadline = monotonic() + 3
        while True:
            try:
                successor = StorageSession.open(tmp_path)
                break
            except StorageInUse:
                assert monotonic() < deadline
                sleep(0.02)
        try:
            assert successor.settings["pet_mood"] == 88
        finally:
            successor.close()
        assert (tmp_path / LOCK_NAME).is_file()
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=10)


@pytest.mark.skipif(not hasattr(os, "fork"), reason="Requires POSIX fork")
def test_forked_child_cannot_use_or_release_parent_owner(owner):
    ready_read, ready_write = os.pipe()
    finish_read, finish_write = os.pipe()
    child = os.fork()
    if child == 0:
        try:
            os.close(ready_read)
            os.close(finish_write)
            for action in (owner.save_settings, owner.close):
                try:
                    action()
                except StorageClosed:
                    pass
                else:
                    os._exit(3)
            os.write(ready_write, b"ready")
            os.read(finish_read, 1)
            os._exit(0)
        except BaseException:
            os._exit(4)
    os.close(ready_write)
    os.close(finish_read)
    try:
        import select
        assert select.select([ready_read], [], [], 10)[0], "Fork child did not become ready"
        assert os.read(ready_read, 5) == b"ready"
        with pytest.raises(StorageInUse):
            StorageSession.open(owner.directory)
        owner.close()
        successor = StorageSession.open(owner.directory)
        successor.save_settings()
        successor.close()
    finally:
        os.write(finish_write, b"x")
        os.close(ready_read)
        os.close(finish_write)
        _, status = os.waitpid(child, 0)
    assert os.waitstatus_to_exitcode(status) == 0
