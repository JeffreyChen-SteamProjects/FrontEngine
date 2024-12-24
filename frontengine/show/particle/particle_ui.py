from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap, Qt
from PySide6.QtWidgets import QWidget, QGridLayout

from frontengine.show.particle.particle_scene import ParticleGraphicScene
from frontengine.show.scene.extend_graphic_view import ExtendGraphicView
from frontengine.utils.logging.loggin_instance import front_engine_logger


class ParticleWidget(QWidget):

    def __init__(self, pixmap: QPixmap, particle_size: int, particle_direction: str, particle_count: int = 50,
                 screen_height: int = 1080, screen_width: int = 1920, opacity: float = 0.2,
                 particle_speed: int = 1):
        front_engine_logger.info("Init ParticleWidget "
                                 f"pixmap: {pixmap} "
                                 f"particle_size: {particle_size} "
                                 f"particle_direction: {particle_direction} "
                                 f"particle_count: {particle_count} "
                                 f"screen_height: {screen_height} "
                                 f"screen_width: {screen_width} "
                                 f"opacity: {opacity} "
                                 f"particle_speed: {particle_speed}")
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        if particle_size:
            self.pixmap = pixmap.scaled(QSize(particle_size, particle_size), Qt.AspectRatioMode.KeepAspectRatio)
        else:
            self.pixmap = pixmap.scaled(QSize(pixmap.width(), pixmap.height()), Qt.AspectRatioMode.KeepAspectRatio)
        self.particle_view = ExtendGraphicView()
        self.particle_scene = ParticleGraphicScene(
            self.pixmap, particle_direction, particle_count,
            screen_height, screen_width, opacity, particle_speed)
        self.particle_view.setScene(self.particle_scene)
        self.grid_layout = QGridLayout()
        self.grid_layout.addWidget(self.particle_view, 0, 0, -1, -1)
        self.setLayout(self.grid_layout)

    def set_ui_window_flag(self, show_on_bottom: bool = False) -> None:
        front_engine_logger.info("ParticleWidget set_ui_window_flag "
                                 f"show_on_bottom: {show_on_bottom}")
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        if not show_on_bottom:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnBottomHint)
