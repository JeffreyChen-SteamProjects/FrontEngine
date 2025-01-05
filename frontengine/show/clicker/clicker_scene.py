from PySide6.QtWidgets import QGraphicsScene

from frontengine.utils.logging.loggin_instance import front_engine_logger


class ClickerGraphicScene(QGraphicsScene):

    def __init__(self):
        front_engine_logger.info("Init ClickerGraphicScene")
        super().__init__()
