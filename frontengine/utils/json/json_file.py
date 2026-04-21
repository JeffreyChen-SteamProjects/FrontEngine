import json
from pathlib import Path
from threading import Lock
from typing import Union, Optional, Any

from frontengine.utils.exception.exception_tags import cant_find_json_error
from frontengine.utils.exception.exception_tags import cant_save_json_error
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
        except (OSError, json.JSONDecodeError) as error:
            raise FrontEngineJsonFileException(f"{cant_find_json_error}: {error}") from error


def write_json(json_save_path: str, data_to_output: Union[dict, list]) -> None:
    """
    Write JSON to disk atomically enough for our overlay app.
    """
    with _lock:
        try:
            with open(json_save_path, "w", encoding="utf-8") as file_to_write:
                file_to_write.write(json.dumps(data_to_output, indent=4))
        except OSError as error:
            raise FrontEngineJsonFileException(f"{cant_save_json_error}: {error}") from error
