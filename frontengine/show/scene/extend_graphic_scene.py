from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QGraphicsScene

from frontengine.utils.logging.loggin_instance import front_engine_logger


class ExtendGraphicScene(QGraphicsScene):
    """
    ExtendGraphicScene: 可擴展的 QGraphicsScene 基底類別
    ExtendGraphicScene: A base class extending QGraphicsScene for custom scenes
    """

    def __init__(self, background_color: QColor = QColor(0, 0, 0, 0)):
        """
        初始化場景
        Initialize the scene

        :param background_color: 場景背景顏色 (預設透明) / Scene background color (default transparent)
        """
        front_engine_logger.info("Init ExtendGraphicScene")
        super().__init__()

        # 設定背景顏色 / Set background color
        self.setBackgroundBrush(QBrush(background_color))

    def clear_scene(self) -> None:
        """
        清除場景內所有項目
        Clear all items in the scene
        """
        front_engine_logger.debug("ExtendGraphicScene clear_scene")
        self.clear()
