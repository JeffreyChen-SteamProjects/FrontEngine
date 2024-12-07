import logging

logging.root.setLevel(logging.DEBUG)
front_engine_logger = logging.getLogger("FrontEngine")
formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
# File handler
file_handler = logging.FileHandler(filename="FrontEngine.log", mode="w")
file_handler.setFormatter(formatter)
front_engine_logger.addHandler(file_handler)

class FrontEngineLoggingHandler(logging.Handler):

    # redirect logging stderr output to queue

    def __init__(self):
        super().__init__()
        self.formatter = formatter
        self.setLevel(logging.DEBUG)

    def emit(self, record: logging.LogRecord) -> None:
        print(self.format(record))


# Stream handler
front_engine_logger.addHandler(FrontEngineLoggingHandler())
