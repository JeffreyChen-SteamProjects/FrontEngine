import random
from typing import Callable, Dict, Any

from PySide6.QtCore import QTimer, QPoint, QRect
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsScene

from frontengine.show.particle.particle_utils import (
    particle_down, particle_up, particle_left, particle_right,
    particle_left_down, particle_left_up, particle_right_down, particle_right_up,
    particle_random_minus, particle_random_add, particle_random
)
from frontengine.utils.logging.loggin_instance import front_engine_logger


class ParticleGraphicScene(QGraphicsScene):
    """
    粒子特效場景，用於顯示粒子動畫
    ParticleGraphicScene: A QGraphicsScene subclass for particle animation
    """

    def __init__(self,
                 particle_pixmap: QPixmap,
                 particle_direction: str,
                 particle_count: int = 500,
                 screen_height: int = 1920,
                 screen_width: int = 1080,
                 opacity: float = 0.2,
                 particle_speed: int = 1):
        """
        初始化粒子場景
        Initialize particle scene

        :param particle_pixmap: 粒子圖片 / Particle pixmap
        :param particle_direction: 粒子移動方向 / Particle movement direction
        :param particle_count: 粒子數量 / Number of particles
        :param screen_height: 畫布高度 / Screen height
        :param screen_width: 畫布寬度 / Screen width
        :param opacity: 粒子透明度 / Particle opacity
        :param particle_speed: 粒子移動速度 / Particle speed
        """
        front_engine_logger.info(
            f"Init ParticleGraphicScene | "
            f"particle_direction={particle_direction}, "
            f"particle_count={particle_count}, "
            f"screen_height={screen_height}, screen_width={screen_width}, "
            f"opacity={opacity}, particle_speed={particle_speed}"
        )
        super().__init__()

        # --- 基本屬性 / Basic attributes ---
        self.particle_pixmap: QPixmap = particle_pixmap
        self.particle_direction: str = particle_direction
        self.particle_count: int = particle_count
        self.opacity: float = opacity
        self.particle_speed: int = particle_speed
        self.screen_height: int = screen_height
        self.screen_width: int = screen_width

        # 儲存粒子資訊的字典 / Dictionary to store particle info
        self.particle_dict: Dict[str, Dict[str, Any]] = {}

        # 建立粒子 / Create particles
        self.create_particle()

        # 設定更新函式 / Set update function
        self.update_function: Callable = {
            "down": particle_down,
            "up": particle_up,
            "left": particle_left,
            "right": particle_right,
            "left_down": particle_left_down,
            "left_up": particle_left_up,
            "right_down": particle_right_down,
            "right_up": particle_right_up,
            "random_minus": particle_random_minus,
            "random_add": particle_random_add,
            "random": particle_random
        }.get(self.particle_direction)

        if not self.update_function:
            front_engine_logger.error(f"Invalid particle direction: {self.particle_direction}")
            raise ValueError(f"Unsupported particle direction: {self.particle_direction}")

        # 設定場景大小 / Set scene size
        self.setSceneRect(QRect(0, 0, screen_width, screen_height))

        # 啟動定時器 / Start update timer
        self.update_timer: QTimer = QTimer()
        self.update_timer.setInterval(100)  # 更新間隔 (毫秒) / Update interval (ms)
        self.update_timer.timeout.connect(self.update_particle_xy)
        self.update_timer.start()

    def create_particle(self) -> None:
        """
        建立粒子並隨機分布在場景中
        Create particles and randomly distribute them in the scene
        """
        front_engine_logger.info("ParticleGraphicScene create_particle")
        self.particle_dict.clear()

        for count in range(self.particle_count):
            item = self.addPixmap(self.particle_pixmap)
            item.setOpacity(self.opacity)
            self.particle_dict[f"particle_{count}"] = {
                "x": random.randint(0, self.screen_width),
                "y": random.randint(0, self.screen_height),
                "height": self.screen_height,
                "width": self.screen_width,
                "pixmap_item": item,
            }

    def update_particle_xy(self) -> None:
        """
        更新粒子座標並重新繪製
        Update particle positions and redraw
        """
        front_engine_logger.debug("ParticleGraphicScene update_particle_xy")

        # 更新粒子座標 / Update particle positions
        self.update_function(self.particle_dict, self.particle_speed)

        # 更新場景中的粒子位置 / Update positions in scene
        for particle in self.particle_dict.values():
            pixmap_item = particle["pixmap_item"]
            pixmap_item.setPos(particle["x"], particle["y"])

            # 如果粒子超出場景範圍，移除它 / Remove particle if out of bounds
            if not self.sceneRect().contains(QPoint(particle["x"], particle["y"])):
                self.removeItem(pixmap_item)

        # 如果場景中沒有粒子，重新建立 / Recreate particles if all removed
        if not self.items():
            self.create_particle()