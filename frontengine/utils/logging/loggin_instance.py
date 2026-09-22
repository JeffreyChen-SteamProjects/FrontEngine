"""
The ``FrontEngine`` logger and the file it writes to.

The log file is ``~/.frontengine/logs/FrontEngine.log`` unless the
``FRONTENGINE_LOG_FILE`` environment variable names another path (a relative one
resolves against the cwd at import time; ``os.devnull`` turns the file off). It
used to be ``FrontEngine.log`` in the working directory, opened at import, so
every process that imported the package -- JEditor and PyBreeze embed it -- left
a log in whatever directory it started in, and a launch from a read-only
directory had to fall back through a chain of candidates.

The package's handler opens the file on the first record, so importing writes
nothing. Every process on the account shares the file, so it is opened for
append, each line carries the process id, and it is rotated only when a process
opens it: Windows refuses to rename a file another process holds open, and a
rotation attempted inside ``emit()`` would then fail on every later record.
"""
import logging
import os
import warnings
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
    '%(asctime)s | %(process)d | %(name)s | %(levelname)s | %(message)s'
)

#: Environment variable that overrides where the log file is written.
LOG_FILE_ENV = "FRONTENGINE_LOG_FILE"

#: A file past this size is moved to ``<name>.1`` when a process opens it.
ROTATE_AT_BYTES = 10 * 1024 * 1024


def default_log_file() -> Path:
    """Return the log file path: ``$FRONTENGINE_LOG_FILE``, else the home default."""
    configured = os.environ.get(LOG_FILE_ENV, "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".frontengine" / "logs" / "FrontEngine.log"


def _rotate_if_large(path: Path, limit: int) -> None:
    """Move ``path`` to ``<path>.1`` when it is larger than ``limit`` bytes.

    Best effort: while another process holds the file open Windows refuses the
    rename, and the file is simply appended to until a later open succeeds.
    """
    try:
        if limit <= 0 or not path.is_file() or path.stat().st_size <= limit:
            return
        os.replace(path, path.with_name(path.name + ".1"))
    except OSError:
        return


class FrontEngineLoggingHandler(RotatingFileHandler):
    """
    FrontEngine 專用日誌處理器
    FrontEngine's file handler: ``default_log_file()``, append, UTF-8.

    ``delay=True`` defers opening (and creating the directory) to the first
    record, which is how the package's own handler is built. A file that cannot
    be opened is swapped for ``os.devnull`` with one ``RuntimeWarning``: losing
    the log is acceptable, failing to start is not.
    """

    def __init__(
        self,
        filename: str | None = None,
        mode: str = "a",
        max_bytes: int = 0,
        backup_count: int = 0,
        errors: str = "backslashreplace",
        delay: bool = False,
    ):
        # encoding="utf-8"：日誌會寫進翻譯過的字串與使用者的檔案路徑。
        # 用系統預設編碼的話，cp950／cp1252 遇到俄文或中文就整行寫不進去，
        # 還會把 logging 自己的錯誤倒進被導向的輸出面板。
        # encoding="utf-8": the log carries translated strings and user file
        # paths. On the locale codepage, cp950 or cp1252 drops any line with
        # Russian or Chinese in it and spills logging's own traceback into the
        # redirected output panel.
        # errors="backslashreplace" (logging.basicConfig's own default): a lone
        # surrogate from a Windows path still raises under strict, and an
        # escaped record beats a lost one.
        path = filename if filename is not None else str(default_log_file())
        super().__init__(
            filename=path, mode=mode, maxBytes=max_bytes,
            backupCount=backup_count, encoding="utf-8", delay=delay,
            errors=errors)
        self.setFormatter(formatter)  # 正確套用 formatter
        self.setLevel(logging.DEBUG)

    def _open(self):
        """Create the directory and rotate before opening; fall back to devnull."""
        path = Path(self.baseFilename)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            _rotate_if_large(path, ROTATE_AT_BYTES)
            return super()._open()
        except OSError as error:
            warnings.warn(
                f"FrontEngine log file {path} unavailable, file logging off: {error!r}",
                RuntimeWarning, stacklevel=2)
            # The handler owns and closes this stream.
            return open(os.devnull, self.mode, encoding=self.encoding, errors=self.errors)  # noqa: SIM115

    def emit(self, record: logging.LogRecord) -> None:
        """
        實際輸出日誌紀錄
        Emit log record
        """
        super().emit(record)


# The file is opened on the first record, never at import.
file_handler = FrontEngineLoggingHandler(delay=True)
front_engine_logger.addHandler(file_handler)
