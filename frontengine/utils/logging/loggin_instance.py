import logging
from logging.handlers import RotatingFileHandler

logging.root.setLevel(logging.DEBUG)
front_engine_logger = logging.getLogger("FrontEngine")
front_engine_logger.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')


class FrontEngineLoggingHandler(RotatingFileHandler):

    # redirect logging stderr output to queue

    def __init__(self, filename: str = "FrontEngine.log", mode="w",
                 maxBytes:int=1073741824, backupCount:int=0):
        super().__init__(filename=filename, mode=mode, maxBytes=maxBytes, backupCount=backupCount)
        self.formatter = formatter
        self.setLevel(logging.DEBUG)

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)


# File handler
file_handler = FrontEngineLoggingHandler()
front_engine_logger.addHandler(file_handler)
