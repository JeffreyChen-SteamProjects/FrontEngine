"""Nonblocking OS-owned catalog job lock, released automatically on process exit."""
from contextlib import contextmanager
from pathlib import Path
import sys


@contextmanager
def catalog_lock(root: Path):
    """Prevent another app instance from recovering a transaction that is still active."""
    path = root / '.asset-library.lock'
    if path.is_symlink():
        raise ValueError('Asset lock cannot be a symlink')
    with path.open('a+b') as stream:
        if not path.stat().st_size:
            stream.write(b'\0')
            stream.flush()
        stream.seek(0)
        try:
            if sys.platform == 'win32':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError('Another instance is using this asset library; retry after it finishes') from error
        try:
            yield
        finally:
            stream.seek(0)
            if sys.platform == 'win32':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
