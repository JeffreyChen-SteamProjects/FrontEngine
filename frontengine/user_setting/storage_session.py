"""Directory ownership for disk-backed settings and home clients."""
from __future__ import annotations

from contextlib import contextmanager, nullcontext
from functools import wraps
import errno
import os
from pathlib import Path
import stat
from threading import RLock
from typing import TYPE_CHECKING, Iterator

from frontengine.utils.exception.exceptions import FrontEngineJsonFileException
from frontengine.utils.json.json_repository import JsonRepository
from frontengine.utils.logging.loggin_instance import front_engine_logger

if TYPE_CHECKING:
    from frontengine.user_setting.pet_profiles import PetProfiles

LOCK_NAME = ".frontengine-owner.lock"
SETTINGS_NAME = "user_setting.json"
_locks: dict[int, _DirectoryLock] = {}
_locks_mutex = RLock()


class StorageInUse(OSError):
    """A live owner already holds the requested directory."""


class StorageUnavailable(OSError):
    """The storage layout or locking operation cannot safely be used."""


class StorageClosed(OSError):
    """An old or inherited capability cannot access persistent state."""


class StorageBusy(RuntimeError):
    """Clients or admitted operations still require this owner."""


class HomeRuntimeInUse(StorageBusy):
    """Another store or service owns this home snapshot."""


def _regular_file(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    except OSError as error:
        raise StorageUnavailable(f"Cannot inspect managed storage {path}: {error}") from error
    reparse = getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or reparse:
        raise StorageUnavailable(f"Managed storage must be a regular file without aliases: {path}")


def checked_export_destination(destination: Path) -> Path:
    """Keep portable exports and their temporary writes away from managed files."""
    from frontengine.user_setting.pet_game_save import FILE_NAMES
    reserved = {LOCK_NAME, SETTINGS_NAME, *FILE_NAMES.values()}
    reserved |= {name + suffix for name in tuple(reserved) for suffix in ('.tmp', '.bak', '.bak.tmp')}
    destination = Path(destination)
    if os.name == 'nt' and any(part.endswith((' ', '.')) or ':' in part
                               for part in destination.parts if part not in (destination.anchor, '.', '..')):
        raise StorageUnavailable(f"Export path uses a Windows filename alias: {destination}")
    resolved_destination = destination.resolve()
    paths = (destination, destination.with_name(destination.name + '.tmp'),
             resolved_destination, resolved_destination.with_name(resolved_destination.name + '.tmp'))
    for path in paths:
        _regular_file(path)
        resolved = path.resolve()
        if path.name.casefold() in reserved or resolved.name.casefold() in reserved:
            raise StorageUnavailable(f"Cannot export over managed storage: {path}")
        _regular_file(resolved)
    return resolved_destination


def owned_settings_operation(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._owner._settings_transaction() if self._owner is not None else nullcontext():
            return method(self, *args, **kwargs)
    return call


class _DirectoryLock:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.fd = -1
        self.pid = os.getpid()
        path = directory / LOCK_NAME
        with _locks_mutex:
            try:
                _regular_file(path)
                self.fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
                _regular_file(path)
                if not os.path.samestat(os.fstat(self.fd), path.stat()):
                    raise StorageUnavailable(f"Storage lock changed while opening: {path}")
                self._acquire()
                _locks[self.fd] = self
            except OSError as error:
                if self.fd >= 0:
                    os.close(self.fd)
                    self.fd = -1
                if isinstance(error, (StorageInUse, StorageUnavailable)):
                    raise
                raise StorageUnavailable(f"Cannot own storage directory {directory}: {error}") from error

    def _acquire(self) -> None:
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            if error.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise StorageInUse(f"Storage directory is already in use: {self.directory}") from error
            raise

    def release(self) -> None:
        if self.pid != os.getpid():
            raise StorageClosed("Storage ownership cannot be inherited by a child process")
        with _locks_mutex:
            if self.fd < 0:
                return
            os.close(self.fd)
            _locks.pop(self.fd)
            self.fd = -1


def _after_fork() -> None:
    global _locks_mutex
    for descriptor, lock in _locks.items():
        # Close the child's duplicate without unlocking the parent's shared description.
        os.close(descriptor)
        lock.fd = -1
    _locks.clear()
    _locks_mutex = RLock()


def _before_fork() -> None:
    _locks_mutex.acquire()


def _after_fork_parent() -> None:
    _locks_mutex.release()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(before=_before_fork, after_in_parent=_after_fork_parent,
                        after_in_child=_after_fork)


class _Use:
    def __init__(self, owner: StorageSession, kind: str) -> None:
        self.owner, self.kind = owner, kind
        self.released = False

    def release(self) -> None:
        self.owner._check_pid()
        with self.owner._mutex:
            if not self.released:
                self.owner._uses.remove(self)
                self.released = True


class _HomeUse(_Use):
    def release(self) -> None:
        self.owner._check_pid()
        with self.owner._mutex:
            if not self.released:
                self.owner._home_claims.pop(self.kind)
                super().release()


class StorageSession:
    """Keep a directory owned from its first read through its last client/write."""

    def __init__(self, directory: Path, lock: _DirectoryLock) -> None:
        self._directory, self._lock = directory, lock
        self._identity = directory.stat()
        self._pid = os.getpid()
        self._mutex = RLock()
        self._settings_mutex = RLock()
        self._closed = False
        self._operations = 0
        self._uses: set[_Use] = set()
        self._settings: dict = {}
        self._profiles: PetProfiles | None = None
        self._home_claims: dict[str, _HomeUse] = {}

    @classmethod
    def open(cls, directory: Path) -> StorageSession:
        """Acquire before loading, with defaults independent of the ambient UI."""
        from frontengine.user_setting.user_setting_file import default_settings
        try:
            directory = Path(directory).resolve()
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise StorageUnavailable(f"Cannot open storage directory {directory}: {error}") from error
        lock = _DirectoryLock(directory)
        try:
            owner = cls(directory, lock)
            with owner._operation():
                owner._settings = default_settings()
                owner._load_settings()
        except BaseException as error:
            lock.release()
            if isinstance(error, OSError) and not isinstance(error, StorageUnavailable):
                raise StorageUnavailable(f"Cannot load storage directory {directory}: {error}") from error
            raise
        return owner

    def _load_settings(self) -> None:
        path = self._checked_path(SETTINGS_NAME)
        try:
            data = JsonRepository(path).load()
        except FrontEngineJsonFileException as error:
            if isinstance(error.__cause__, OSError):
                raise StorageUnavailable(f"Cannot read settings {path}: {error.__cause__}") from error
            front_engine_logger.warning(f"[StorageSession] unreadable {path}: {error}")
            return
        if isinstance(data, dict):
            self._settings.update(data)

    @property
    def directory(self) -> Path:
        return self._directory

    @property
    def settings(self) -> dict:
        with self._operation():
            return self._settings

    def profiles(self) -> PetProfiles:
        from frontengine.user_setting.pet_profiles import PetProfiles
        with self._settings_transaction():
            if self._profiles is None:
                self._profiles = PetProfiles._for_storage(self)
            return self._profiles

    def _check_pid(self) -> None:
        if self._pid != os.getpid():
            raise StorageClosed("Storage ownership cannot be inherited by a child process")

    def _require_open(self) -> None:
        if self._closed:
            raise StorageClosed(f"Storage session is closed: {self.directory}")

    @contextmanager
    def _operation(self) -> Iterator[None]:
        self._check_pid()
        with self._mutex:
            self._require_open()
            try:
                same_directory = os.path.samestat(self._identity, self.directory.stat())
            except OSError as error:
                raise StorageUnavailable(f"Cannot access storage directory {self.directory}: {error}") from error
            if not same_directory:
                raise StorageUnavailable(f"Storage directory changed while owned: {self.directory}")
            self._operations += 1
        try:
            yield
        finally:
            self._check_pid()
            with self._mutex:
                self._operations -= 1

    def _checked_path(self, name: str) -> Path:
        if not name or Path(name).name != name or name in (".", ".."):
            raise ValueError("Managed storage requires a single filename")
        path = self.directory / name
        _regular_file(path)
        return path

    @contextmanager
    def _settings_transaction(self) -> Iterator[None]:
        with self._operation(), self._settings_mutex:
            yield

    def _hold(self, kind: str) -> _Use:
        self._check_pid()
        with self._mutex:
            self._require_open()
            use = _Use(self, kind)
            self._uses.add(use)
            return use

    def _claim_home(self, mode: str) -> _Use:
        self._check_pid()
        with self._mutex:
            self._require_open()
            if mode in self._home_claims:
                raise HomeRuntimeInUse(f"Home mode is already owned: {mode}")
            use = _HomeUse(self, mode)
            self._home_claims[mode] = use
            self._uses.add(use)
            return use

    def save_settings(self) -> Path:
        """Persist to the captured root; a stale callback never opens a new owner."""
        with self._settings_transaction():
            path = self._checked_path(SETTINGS_NAME)
            self._checked_path(SETTINGS_NAME + ".tmp")
            return JsonRepository(path).save(self._settings)

    def close(self) -> None:
        """Release only when every admitted operation and registered client ended."""
        self._check_pid()
        with self._mutex:
            if self._closed:
                return
            if self._uses or self._operations:
                raise StorageBusy(f"Storage still has live clients or operations: {self.directory}")
            self._lock.release()
            self._closed = True
