from PySide6.QtWidgets import QGraphicsScene

from frontengine.utils.logging.loggin_instance import front_engine_logger


class ExtendGraphicScene(QGraphicsScene):

    def __init__(self):
        front_engine_logger.info("Init ExtendGraphicScene")
        super().__init__()
