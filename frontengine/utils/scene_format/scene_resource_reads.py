"""Keep extracted assets alive until queued/background readers have finished."""
from pathlib import Path
from threading import RLock

from .scene_document import ASSET_FIELDS

_lock = RLock()
_readers = {}
_closing = []


def _in_use(root):
    return any(path.is_relative_to(root) for path in _readers)


def release_scene_lease(lease):
    """Transfer deferred cleanup ownership; no GUI blocking or open-file deletion."""
    with _lock:
        name = getattr(lease, 'name', None)
        if name is not None and _in_use(Path(name).resolve()):
            if lease not in _closing:
                _closing.append(lease)
        else:
            lease.cleanup()


class SceneResourceRead:
    def __init__(self, document):
        self.paths = {Path(entry[field]).resolve() for entry in document.entries.values()
                      for field in ASSET_FIELDS if entry.get(field)}
        self.closed = False
        with _lock:
            for path in self.paths:
                _readers[path] = _readers.get(path, 0)+1

    def close(self):
        with _lock:
            if self.closed:
                return
            self.closed = True
            for path in self.paths:
                if _readers[path] == 1:
                    del _readers[path]
                else:
                    _readers[path] -= 1
            for lease in tuple(_closing):
                if not _in_use(Path(lease.name).resolve()):
                    lease.cleanup()
                    _closing.remove(lease)
