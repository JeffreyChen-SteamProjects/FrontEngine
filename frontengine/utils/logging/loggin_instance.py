import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 只調自己這個 logger 的層級。動 root logger 會把 DEBUG 強加給任何
# `import frontengine` 的程式，連帶它用的每一個第三方套件。
# Only this logger's level is ours to set. Touching the root logger forces DEBUG
# onto any application that imports frontengine, and every library it uses.

# 建立 FrontEngine logger
front_engine_logger = logging.getLogger("FrontEngine")
front_engine_logger.setLevel(logging.DEBUG)  # 建議與 handler 一致

# 日誌格式
# Log format
formatter = logging.Formatter(
    '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)

# 日誌檔名 / The log file's name
LOG_FILE_NAME = "FrontEngine.log"


class FrontEngineLoggingHandler(RotatingFileHandler):
    """
    FrontEngine 專用日誌處理器
    FrontEngine custom logging handler using RotatingFileHandler
    """

    def __init__(
        self,
        filename: str = LOG_FILE_NAME,
        mode: str = "a",  # 建議使用 append 模式
        max_bytes: int = 1073741824,  # 1GB
        backup_count: int = 3         # 保留 3 個備份檔案
    ):
        # encoding="utf-8"：日誌會寫進翻譯過的字串與使用者的檔案路徑。
        # 用系統預設編碼的話，cp950／cp1252 遇到俄文或中文就整行寫不進去，
        # 還會把 logging 自己的錯誤倒進被導向的輸出面板。
        # encoding="utf-8": the log carries translated strings and user file
        # paths. On the locale codepage, cp950 or cp1252 drops any line with
        # Russian or Chinese in it and spills logging's own traceback into the
        # redirected output panel.
        super().__init__(
            filename=filename, mode=mode, maxBytes=max_bytes,
            backupCount=backup_count, encoding="utf-8")
        self.setFormatter(formatter)  # 正確套用 formatter
        self.setLevel(logging.DEBUG)

    def emit(self, record: logging.LogRecord) -> None:
        """
        實際輸出日誌紀錄
        Emit log record
        """
        super().emit(record)


def _build_file_handler() -> logging.Handler:
    """
    日誌優先寫在工作目錄，寫不了就退到家目錄，再不行就不寫檔。
    從唯讀目錄或系統目錄啟動（自動啟動很容易這樣）不該讓程式打不開——
    少一份日誌可以接受，開不起來不行。
    Prefer the working directory, fall back to the home directory, and give up
    on file logging if neither works. Being launched from a read-only or system
    directory - which autostart makes easy - must not stop the app from opening:
    losing the log is acceptable, failing to start is not.
    """
    for candidate in (LOG_FILE_NAME, str(Path.home() / LOG_FILE_NAME)):
        try:
            # 建構子本身就會開檔，所以「開得起來」就是這裡的測試
            # The constructor opens the file, so building it is the test.
            return FrontEngineLoggingHandler(filename=candidate)
        except OSError:
            continue
    return logging.NullHandler()


# 建立並加入 handler
file_handler = _build_file_handler()
front_engine_logger.addHandler(file_handler)