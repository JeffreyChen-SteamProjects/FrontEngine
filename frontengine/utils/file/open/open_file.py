from pathlib import Path
from threading import Lock
from typing import Tuple

from frontengine.utils.exception.exceptions import FrontEngineOpenFileException

# 全域鎖，確保多執行緒同時讀取時安全
# Global lock to ensure thread safety when reading files
_file_lock = Lock()


def read_file(file: str) -> Tuple[str, str]:
    """
    檢查檔案是否存在並讀取內容
    Check if the file exists and read its content

    :param file: 檔案完整路徑 (Full file path)
    :return: (檔案路徑, 檔案內容) (file path, file content)
    :raises FrontEngineOpenFileException: 當檔案不存在或讀取失敗時拋出
                                          Raised if file does not exist or cannot be read
    """
    if not file:
        raise FrontEngineOpenFileException("File path is empty or None")

    file_path = Path(file)

    if not file_path.exists() or not file_path.is_file():
        raise FrontEngineOpenFileException(f"File does not exist: {file}")

    with _file_lock:  # 確保多執行緒安全 / Ensure thread safety
        try:
            with open(file_path, "r", encoding="utf-8") as open_read_file:
                content = open_read_file.read()
                return file, content
        except Exception as error:
            raise FrontEngineOpenFileException(f"Failed to read file: {error}")