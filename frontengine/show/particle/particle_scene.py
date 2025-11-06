import random
from typing import Callable, List

from PySide6.QtCore import QTimer, QRect
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsScene

from frontengine.show.particle.particle_model import Particle
from frontengine.show.particle.particle_utils import (
    particle_down, particle_up, particle_left, particle_right,
    particle_left_down, particle_left_up, particle_right_down, particle_right_up,
    particle_random_minus, particle_random_add, particle_random
)
from frontengine.utils.logging.loggin_instance import front_engine_logger


class ParticleGraphicScene(QGraphicsScene):
    """粒子特效場景，用於顯示粒子動畫"""

    def __init__(self,
                 particle_pixmap: QPixmap,
                 particle_direction: str,
                 particle_count: int = 500,
                 screen_height: int = 1920,
                 screen_width: int = 1080,
                 opacity: float = 0.2,
                 particle_speed: int = 1):

        front_engine_logger.info(
            f"Init ParticleGraphicScene | "
            f"particle_direction={particle_direction}, "
            f"particle_count={particle_count}, "
            f"screen_height={screen_height}, screen_width={screen_width}, "
            f"opacity={opacity}, particle_speed={particle_speed}"
        )
        super().__init__()

        # --- 基本屬性 ---
        self.particle_pixmap = particle_pixmap
        self.particle_count = particle_count
        self.opacity = opacity
        self.particle_speed = particle_speed
        self.screen_height = screen_height
        self.screen_width = screen_width

        # 儲存粒子資訊的 list
        self.particles: List[Particle] = []

        # 建立粒子
        self.create_particle()

        # 更新函式
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
        }.get(particle_direction)

        if not self.update_function:
            front_engine_logger.error(f"Invalid particle direction: {particle_direction}")
            raise ValueError(f"Unsupported particle direction: {particle_direction}")

        # 設定場景大小
        self.setSceneRect(QRect(0, 0, screen_width, screen_height))
        self._scene_rect = self.sceneRect()  # cache 避免重複呼叫

        # 啟動定時器
        self.update_timer = QTimer()
        self.update_timer.setInterval(100)  # 更新間隔 (毫秒)
        self.update_timer.timeout.connect(self.update_particle_xy)
        self.update_timer.start()

    def create_particle(self) -> None:
        """建立粒子並隨機分布在場景中"""
        front_engine_logger.info("ParticleGraphicScene create_particle")
        self.particles.clear()

        for _ in range(self.particle_count):
            item = self.addPixmap(self.particle_pixmap)
            item.setOpacity(self.opacity)
            particle = Particle(
                x=random.randrange(self.screen_width),
                y=random.randrange(self.screen_height),
                pixmap_item=item
            )
            self.particles.append(particle)

    def update_particle_xy(self) -> None:
        """更新粒子座標並重新繪製"""
        front_engine_logger.debug("ParticleGraphicScene update_particle_xy")

        # 更新粒子座標
        self.update_function(self.particles, self.particle_speed)

        # 更新場景中的粒子位置
        to_remove = []
        for particle in self.particles:
            particle.pixmap_item.setPos(particle.x, particle.y)

            # 超出範圍 -> 標記移除
            if not self._scene_rect.contains(particle.x, particle.y):
                to_remove.append(particle)

        # 批次移除
        for particle in to_remove:
            self.removeItem(particle.pixmap_item)
            self.particles.remove(particle)

        # 如果場景中沒有粒子，重新建立
        if not self.particles:
            self.create_particle()