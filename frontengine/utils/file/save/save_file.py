from threading import Lock
from pathlib import Path
from typing import Union

from frontengine.utils.exception.exceptions import FrontEngineSaveFileException

# 全域鎖，確保多執行緒同時寫入時安全
# Global lock to ensure thread safety when writing files
_file_lock = Lock()


def write_file(file: Union[str, Path], content: Union[str, bytes]) -> None:
    """
    將內容寫入檔案
    Write content into a file

    :param file: 檔案路徑 (File path)
    :param content: 要寫入的內容 (Content to write)
    :raises FrontEngineSaveFileException: 當寫入失敗時拋出 (Raised if writing fails)
    """
    if not file:
        raise FrontEngineSaveFileException("File path is empty or None")

    file_path = Path(file)

    # 確保多執行緒安全
    # Ensure thread safety
    with _file_lock:
        try:
            with open(file_path, "w", encoding="utf-8") as file_to_write:
                file_to_write.write(str(content))
        except Exception as error:
            raise FrontEngineSaveFileException(f"Failed to write file: {error}")