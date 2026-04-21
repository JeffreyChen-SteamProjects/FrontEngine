from abc import abstractmethod

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from frontengine.show.window_helpers import apply_overlay_window_flags, load_overlay_icon
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

        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        load_overlay_icon(self)

    def set_ui_window_flag(self, show_on_bottom: bool = False) -> None:
        front_engine_logger.info(f"{self.__class__.__name__} set_ui_window_flag | show_on_bottom: {show_on_bottom}")
        apply_overlay_window_flags(self, show_on_bottom=show_on_bottom)

    def set_ui_variable(self, opacity: float = 0.2) -> None:
        front_engine_logger.info(f"{self.__class__.__name__} set_ui_variable | opacity: {opacity}")
        self.opacity = opacity

    def paintEvent(self, event) -> None:
        front_engine_logger.debug(f"{self.__class__.__name__} paintEvent | event: {event}")
        painter = QPainter(self)
        painter.save()
        painter.setOpacity(self.opacity)
        try:
            self.draw_content(painter)
        finally:
            painter.restore()

    @abstractmethod
    def draw_content(self, painter: QPainter) -> None:
        """Subclass hook that renders the widget content onto the shared painter."""
