from pathlib import Path
from typing import Any, Optional, Union

from frontengine.utils.json.json_file import read_json, write_json


class JsonRepository:
    """
    Thin Repository around a single JSON document on disk. Callers hold
    an instance per file, so file-path plumbing does not leak into every
    consumer and tests can swap the implementation.
    """

    def __init__(self, file_path: Union[str, Path]):
        self._path: Path = Path(file_path)

    @property
    def path(self) -> Path:
        return self._path

    def exists(self) -> bool:
        return self._path.exists() and self._path.is_file()

    def load(self) -> Optional[Any]:
        return read_json(str(self._path))

    def load_into(self, target: dict, *, replace: bool = False) -> None:
        """
        Read the document into `target`. When replace is True, target is
        cleared first so stale keys from a previous document do not
        survive a reload.
        """
        data = self.load()
        if not isinstance(data, dict):
            return
        if replace:
            target.clear()
        target.update(data)

    def save(self, data: Union[dict, list]) -> Path:
        write_json(str(self._path), data)
        return self._path
