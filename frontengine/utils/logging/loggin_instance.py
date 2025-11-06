import logging
from logging.handlers import RotatingFileHandler

# 設定 root logger 層級
# Set root logger level
logging.root.setLevel(logging.DEBUG)

# 建立 FrontEngine logger
front_engine_logger = logging.getLogger("FrontEngine")
front_engine_logger.setLevel(logging.DEBUG)  # 建議與 handler 一致

# 日誌格式
# Log format
formatter = logging.Formatter(
    '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)


class FrontEngineLoggingHandler(RotatingFileHandler):
    """
    FrontEngine 專用日誌處理器
    FrontEngine custom logging handler using RotatingFileHandler
    """

    def __init__(
        self,
        filename: str = "FrontEngine.log",
        mode: str = "a",  # 建議使用 append 模式
        max_bytes: int = 1073741824,  # 1GB
        backup_count: int = 3         # 保留 3 個備份檔案
    ):
        super().__init__(filename=filename, mode=mode, maxBytes=max_bytes, backupCount=backup_count)
        self.setFormatter(formatter)  # 正確套用 formatter
        self.setLevel(logging.DEBUG)

    def emit(self, record: logging.LogRecord) -> None:
        """
        實際輸出日誌紀錄
        Emit log record
        """
        super().emit(record)


# 建立並加入 handler
file_handler = FrontEngineLoggingHandler()
front_engine_logger.addHandler(file_handler)