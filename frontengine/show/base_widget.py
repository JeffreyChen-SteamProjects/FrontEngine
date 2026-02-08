import os
from abc import abstractmethod
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QIcon
from PySide6.QtWidgets import QWidget

from frontengine.utils.logging.loggin_instance import front_engine_logger


class BaseWidget(QWidget):
    """
    BaseWidget: 提供共用 UI 屬性與事件處理的基底類別
    BaseWidget: Base class providing shared UI attributes and event handling
    """

    def __init__(self, draw_location_x: int = 0, draw_location_y: int = 0):
        super().__init__()
        self.draw_location_x: int = draw_location_x
        self.draw_location_y: int = draw_location_y
        self.opacity: float = 0.2

        # 設定視窗屬性 / Set widget attributes
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 設定視窗 Icon / Set window icon
        self.icon_path: Path = Path(os.getcwd()) / "frontengine.ico"
        if self.icon_path.exists() and self.icon_path.is_file():
            self.setWindowIcon(QIcon(str(self.icon_path)))

    def set_ui_window_flag(self, show_on_bottom: bool = False) -> None:
        """
        設定視窗旗標 (保持最上層或最下層)
        Set window flags (stay on top or bottom)
        """
        front_engine_logger.info(f"{self.__class__.__name__} set_ui_window_flag | show_on_bottom: {show_on_bottom}")
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        if not show_on_bottom:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnBottomHint)

    def set_ui_variable(self, opacity: float = 0.2) -> None:
        """
        設定 UI 透明度
        Set UI opacity
        """
        front_engine_logger.info(f"{self.__class__.__name__} set_ui_variable | opacity: {opacity}")
        self.opacity = opacity

    def paintEvent(self, event) -> None:
        """
        呼叫子類別的繪製方法
        Call subclass draw_content method
        """
        front_engine_logger.debug(f"{self.__class__.__name__} paintEvent | event: {event}")
        painter = QPainter(self)
        painter.setOpacity(self.opacity)
        self.draw_content(painter)
        painter.restore()

    @abstractmethod
    def draw_content(self, painter: QPainter) -> None:
        """
        子類別必須實作的繪製方法
        Subclasses must implement this drawing method
        """
        pass

    # --- 共用滑鼠事件 / Shared mouse events ---
    def mousePressEvent(self, event) -> None:
        front_engine_logger.debug(f"{self.__class__.__name__} mousePressEvent | event: {event}")
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        front_engine_logger.debug(f"{self.__class__.__name__} mouseDoubleClickEvent | event: {event}")
        super().mouseDoubleClickEvent(event)
