import logging
import sys

front_engine_logger = logging.getLogger("FrontEngine")
front_engine_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
# Stream handler
stream_handler = logging.StreamHandler(stream=sys.stderr)
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.WARNING)
front_engine_logger.addHandler(stream_handler)
# File handler
file_handler = logging.FileHandler(filename="FrontEngine.log", mode="w")
file_handler.setFormatter(formatter)
front_engine_logger.addHandler(file_handler)
