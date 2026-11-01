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
from pathlib import Path
from typing import Callable

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


class HomeSaveStore:
    """One mode's save file. ``write`` is injectable so tests can fail the disk."""

    def __init__(self, directory: Path, catalog: Catalog, mode: str = "manage",
                 write: Callable[[Path, bytes], None] = _write_file) -> None:
        if mode not in FILE_NAMES:
            raise ValueError("Unknown home save mode")
        self.path = Path(directory) / FILE_NAMES[mode]
        self.backup = self.path.with_name(self.path.name + ".bak")
        self.catalog = catalog
        self.mode = mode
        self._write = write
        self.read_only = False

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

    def set_aside(self, suffix: str) -> Path | None:
        """Keep an unreadable or newer save under another name so a new home can start."""
        if not suffix.isalnum() or len(suffix) > 32:
            raise ValueError("Invalid set-aside suffix")
        target = None
        if self.path.is_file():
            target = self.path.with_name(f"{self.path.name}.{suffix}")
            if target.exists():
                raise FileExistsError("A set-aside save with this name already exists")
            os.replace(self.path, target)
        self.read_only = False
        return target

    def encode(self, world: World) -> bytes:
        """Serialize and prove the bytes load back. Pure CPU work; touches no file."""
        if world.mode != self.mode:
            raise ValueError("World mode does not match this save file")
        data = json.dumps(snapshot.to_dict(world), allow_nan=False, separators=(",", ":")).encode("utf-8")
        if len(data) > MAX_SAVE_BYTES:
            raise ValueError("Home save exceeds the size limit")
        snapshot.from_dict(json.loads(data.decode("utf-8")), self.catalog)
        return data

    def write_encoded(self, data: bytes) -> None:
        """Blocking file work, safe on a worker thread: backup the last good file, then replace."""
        if self.read_only:
            raise PermissionError("Home save is protected; restore a backup or update FrontEngine")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_file():
            try:
                self._read(self.path)
                self._write(self.backup, self.path.read_bytes())
            except (ValueError, KeyError, TypeError):
                pass          # never let a damaged file replace the last good backup
        self._write(self.path, data)

    def save(self, world: World) -> None:
        """Raise on failure; the caller keeps the in-memory world and may retry."""
        if self.read_only:
            raise PermissionError("Home save is protected; restore a backup or update FrontEngine")
        self.write_encoded(self.encode(world))
