import json
import os
from pathlib import Path
from threading import Lock
from typing import Union, Optional, Any

from frontengine.utils.exception.exception_tags import cant_find_json_error
from frontengine.utils.exception.exception_tags import cant_save_json_error
from frontengine.utils.exception.exception_tags import wrong_json_data_error
from frontengine.utils.exception.exceptions import FrontEngineJsonFileException

_lock = Lock()


def read_json(json_file_path: str) -> Optional[Any]:
    """
    Read JSON from disk. Returns None when the file does not exist.
    """
    with _lock:
        file_path = Path(json_file_path)
        if not (file_path.exists() and file_path.is_file()):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as read_file:
                return json.loads(read_file.read())
        except OSError as error:
            raise FrontEngineJsonFileException(f"{cant_find_json_error}: {error}") from error
        except json.JSONDecodeError as error:
            # 檔案在，是內容壞了。講「找不到檔案」只會把人帶去找錯地方。
            # The file is there, its contents are not. Saying "cannot find" sends
            # the reader looking in the wrong place.
            raise FrontEngineJsonFileException(f"{wrong_json_data_error}: {error}") from error


def write_json(json_save_path: str, data_to_output: Union[dict, list]) -> None:
    """
    Write JSON to disk atomically: serialise first, write a temporary file next
    to the target, then rename over it. Opening the real file with "w" truncates
    it before anything has been serialised, so an interrupted save - a power
    cut, the F12 critical exit, a value json cannot encode - used to leave the
    user with a zero-byte settings file and no way back.
    """
    with _lock:
        target = Path(json_save_path)
        try:
            text = json.dumps(data_to_output, indent=4)
        except (TypeError, ValueError) as error:
            raise FrontEngineJsonFileException(f"{cant_save_json_error}: {error}") from error
        temp_path = target.with_name(target.name + ".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as file_to_write:
                file_to_write.write(text)
                file_to_write.flush()
                os.fsync(file_to_write.fileno())
            os.replace(temp_path, target)
        except OSError as error:
            try:
                temp_path.unlink()
            except OSError:  # pragma: no cover - nothing more we can do
                pass
            raise FrontEngineJsonFileException(f"{cant_save_json_error}: {error}") from error
