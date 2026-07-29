from pathlib import Path
from typing import Any, Optional, Union

from frontengine.utils.exception.exceptions import FrontEngineJsonFileException
from frontengine.utils.json.json_file import read_json, write_json
from frontengine.utils.logging.loggin_instance import front_engine_logger


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
        try:
            data = self.load()
        except FrontEngineJsonFileException as error:
            # 設定檔壞掉不該讓程式打不開。留著壞檔案不動（使用者也許想手動救），
            # 這次就用預設值跑；下次存檔會把它覆蓋掉。
            # A damaged settings file must not stop the app from opening. Leave
            # the file alone - the user may want to salvage it - and run on the
            # defaults; the next save replaces it.
            front_engine_logger.warning(f"[JsonRepository] unreadable {self._path}: {error}")
            return
        if not isinstance(data, dict):
            return
        if replace:
            target.clear()
        target.update(data)

    def save(self, data: Union[dict, list]) -> Path:
        write_json(str(self._path), data)
        return self._path
