from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap, Qt
from PySide6.QtWidgets import QWidget, QGridLayout

from frontengine.show.particle.particle_scene import ParticleGraphicScene
from frontengine.show.scene.extend_graphic_view import ExtendGraphicView
from frontengine.utils.logging.loggin_instance import front_engine_logger


class ParticleWidget(QWidget):
    """
    粒子特效顯示元件
    ParticleWidget: A QWidget wrapper for displaying particle effects
    """

    def __init__(self,
                 pixmap: QPixmap,
                 particle_size: int,
                 particle_direction: str,
                 particle_count: int = 50,
                 screen_height: int = 1080,
                 screen_width: int = 1920,
                 opacity: float = 0.2,
                 particle_speed: int = 1):
        """
        初始化粒子元件
        Initialize particle widget

        :param pixmap: 粒子圖片 / Particle pixmap
        :param particle_size: 粒子大小 / Particle size
        :param particle_direction: 粒子方向 / Particle direction
        :param particle_count: 粒子數量 / Number of particles
        :param screen_height: 畫布高度 / Screen height
        :param screen_width: 畫布寬度 / Screen width
        :param opacity: 粒子透明度 / Particle opacity
        :param particle_speed: 粒子速度 / Particle speed
        """
        front_engine_logger.info(
            f"[ParticleWidget] Init | direction={particle_direction}, "
            f"count={particle_count}, size={particle_size}, "
            f"screen=({screen_width}x{screen_height}), opacity={opacity}, speed={particle_speed}"
        )
        super().__init__()

        # 設定視窗屬性 / Set widget attributes
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # --- 設定粒子圖片大小 / Scale particle pixmap ---
        target_size = QSize(particle_size, particle_size) if particle_size else QSize(pixmap.width(), pixmap.height())
        self.pixmap: QPixmap = pixmap.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio)

        # --- 建立場景與視圖 / Create scene and view ---
        self.particle_view: ExtendGraphicView = ExtendGraphicView()
        self.particle_scene: ParticleGraphicScene = ParticleGraphicScene(
            self.pixmap, particle_direction, particle_count,
            screen_height, screen_width, opacity, particle_speed
        )
        self.particle_view.setScene(self.particle_scene)

        # --- 設定版面配置 / Set layout ---
        self.grid_layout: QGridLayout = QGridLayout()
        self.grid_layout.addWidget(self.particle_view, 0, 0, -1, -1)
        self.setLayout(self.grid_layout)

    def set_ui_window_flag(self, show_on_bottom: bool = False) -> None:
        """
        設定視窗旗標 (保持最上層或最下層)
        Set window flags (stay on top or bottom)
        """
        front_engine_logger.info(f"[ParticleWidget] set_ui_window_flag | show_on_bottom={show_on_bottom}")
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        if not show_on_bottom:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnBottomHint)