from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout

from frontengine.show.clicker.clicker_scene import ClickerGraphicScene
from frontengine.show.scene.extend_graphic_view import ExtendGraphicView
from frontengine.utils.logging.loggin_instance import front_engine_logger


class ClickerWidget(QWidget):

    def __init__(self):
        front_engine_logger.info("Init ClickerWidget")
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.clicker_view = ExtendGraphicView()
        self.clicker_scene = ClickerGraphicScene()
        self.clicker_view.setScene(self.clicker_scene)
        self.grid_layout = QGridLayout()
        self.grid_layout.addWidget(self.clicker_view, 0, 0, -1, -1)
        self.setLayout(self.grid_layout)

    def set_ui_window_flag(self, show_on_bottom: bool = False) -> None:
        front_engine_logger.info("ClickerWidget set_ui_window_flag")
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        if not show_on_bottom:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnBottomHint)
