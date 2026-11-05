"""Home save files: temp write, validation, atomic replace and a last-good backup.

The home has its own versioned file beside the settings, separate from pet
profiles (which keep their 256-record / 256 KiB limits). Managed play and free
layout use different files, so free layout can never write coins, unlocks or
progress into the managed home. A save from a newer FrontEngine is never
overwritten; a damaged save is left in place and its backup offered instead.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from contextlib import contextmanager
from functools import wraps
from threading import RLock
from pathlib import Path
from typing import Callable

from frontengine.user_setting.storage_session import StorageSession, StorageBusy, StorageClosed, HomeRuntimeInUse
from frontengine.utils.pet_game import snapshot
from frontengine.utils.pet_game.catalog import Catalog
from frontengine.utils.pet_game.world import World

MAX_SAVE_BYTES = 2 * 1024 * 1024
FILE_NAMES = {"manage": "pet-home.json", "sandbox": "pet-home-sandbox.json"}


@dataclass
class LoadResult:
    status: str                  # missing / loaded / corrupt / newer
    world: World | None = None
    error: str = ""
    backup_available: bool = False


def _write_file(path: Path, data: bytes) -> None:
    temporary = path.with_name(path.name + ".tmp")
    try:
        with open(temporary, "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    except OSError:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise


def _owned_store_operation(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._operation():
            return method(self, *args, **kwargs)
    return call


class HomeSaveStore:
    """One mode's save file. ``write`` is injectable so tests can fail the disk."""

    def __init__(self, storage: StorageSession, catalog: Catalog, mode: str = "manage",
                 write: Callable[[Path, bytes], None] = _write_file) -> None:
        if mode not in FILE_NAMES:
            raise ValueError("Unknown home save mode")
        self.storage = storage
        self._claim = storage._claim_home(mode)
        self._mutex = RLock()
        self._io_mutex = RLock()
        self._operations = 0
        self._closed = False
        self._service = None
        self.path = storage.directory / FILE_NAMES[mode]
        self.backup = self.path.with_name(self.path.name + ".bak")
        self.catalog = catalog
        self.mode = mode
        self._write = write
        self.read_only = False

    @contextmanager
    def _operation(self):
        with self.storage._operation():
            with self._mutex:
                if self._closed:
                    raise StorageClosed('Home store is closed')
                self._operations += 1
            try:
                with self._io_mutex:
                    for path in (self.path, self.backup):
                        self.storage._checked_path(path.name)
                        self.storage._checked_path(path.name + '.tmp')
                    yield
            finally:
                with self._mutex:
                    self._operations -= 1

    def _attach_service(self, service) -> None:
        with self._operation():
            with self._mutex:
                if self._service is not None:
                    raise HomeRuntimeInUse('Home store already has a service')
                self._service = service

    def _detach_service(self, service) -> None:
        self.storage._check_pid()
        with self._mutex:
            if self._service is service:
                self._service = None

    def _close_service(self, service) -> None:
        self.storage._check_pid()
        with self._mutex:
            if self._closed:
                return
            if self._service not in (None, service) or self._operations:
                raise StorageBusy('Home service still has admitted operations')
            self._claim.release()
            self._service = None
            self._closed = True

    def for_mode(self, mode: str) -> HomeSaveStore:
        with self._operation():
            return HomeSaveStore(self.storage, self.catalog, mode, self._write)

    def close(self) -> None:
        """Release the mode only after its service and admitted writes finish."""
        self.storage._check_pid()
        with self._mutex:
            if self._closed:
                return
            if self._service is not None or self._operations:
                raise StorageBusy('Home store still has a service or operation')
            self._closed = True
            self._claim.release()

    def _read(self, path: Path) -> World:
        with open(path, "rb") as file:
            raw = file.read(MAX_SAVE_BYTES + 1)
        if len(raw) > MAX_SAVE_BYTES:
            raise ValueError("Home save exceeds the size limit")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
            raise ValueError(f"Home save is not valid JSON: {error}") from error
        world = snapshot.from_dict(data, self.catalog)
        if world.mode != self.mode:
            raise ValueError("Home save belongs to another mode")
        return world

    @_owned_store_operation
    def load(self) -> LoadResult:
        """Read the save without ever modifying it."""
        backup = self.backup.is_file()
        if not self.path.is_file():
            return LoadResult("missing", backup_available=backup)
        try:
            return LoadResult("loaded", self._read(self.path), backup_available=backup)
        except snapshot.NewerSaveError as error:
            self.read_only = True
            return LoadResult("newer", error=str(error), backup_available=backup)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.read_only = True
            return LoadResult("corrupt", error=str(error), backup_available=backup)

    @_owned_store_operation
    def restore_backup(self) -> LoadResult:
        """Load the last good save; it becomes current only on the next successful save."""
        try:
            world = self._read(self.backup)
        except snapshot.NewerSaveError as error:
            return LoadResult("newer", error=str(error), backup_available=True)
        except (OSError, ValueError, KeyError, TypeError) as error:
            return LoadResult("corrupt", error=str(error), backup_available=True)
        self.read_only = False
        return LoadResult("loaded", world, backup_available=True)

    @_owned_store_operation
    def set_aside(self, suffix: str) -> Path | None:
        """Keep an unreadable or newer save under another name so a new home can start."""
        if not suffix.isalnum() or len(suffix) > 32:
            raise ValueError("Invalid set-aside suffix")
        target = None
        if self.path.is_file():
            target = self.storage._checked_path(f"{self.path.name}.{suffix}")
            if target.exists():
                raise FileExistsError("A set-aside save with this name already exists")
            os.replace(self.path, target)
        self.read_only = False
        return target

    def encode(self, world: World) -> bytes:
        """Serialize a snapshot. Cheap enough for the GUI thread; the reload check runs in the writer."""
        if world.mode != self.mode:
            raise ValueError("World mode does not match this save file")
        data = json.dumps(snapshot.to_dict(world), allow_nan=False, separators=(",", ":")).encode("utf-8")
        if len(data) > MAX_SAVE_BYTES:
            raise ValueError("Home save exceeds the size limit")
        return data

    def verify(self, data: bytes) -> None:
        """Prove the bytes load back into a valid home; pure CPU work on detached data."""
        snapshot.from_dict(json.loads(data.decode("utf-8")), self.catalog)

    @_owned_store_operation
    def write_encoded(self, data: bytes) -> None:
        """Worker-safe: verify, back up the last good file, then replace. Nothing unverified reaches disk."""
        if self.read_only:
            raise PermissionError("Home save is protected; restore a backup or update FrontEngine")
        self.verify(data)
        if self.path.is_file():
            try:
                self._read(self.path)
                self._write(self.backup, self.path.read_bytes())
            except (ValueError, KeyError, TypeError):
                pass          # never let a damaged file replace the last good backup
        self._write(self.path, data)

    @_owned_store_operation
    def save(self, world: World) -> None:
        """Raise on failure; the caller keeps the in-memory world and may retry."""
        if self.read_only:
            raise PermissionError("Home save is protected; restore a backup or update FrontEngine")
        self.write_encoded(self.encode(world))
