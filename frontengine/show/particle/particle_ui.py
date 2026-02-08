import random
import ctypes
import sys

from OpenGL.GL import *
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage, QPixmap, Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from frontengine.utils.logging.loggin_instance import front_engine_logger


class ParticleOpenGLWidget(QOpenGLWidget):
    """
    OpenGL-based particle widget
    (Replacement for QGraphicsView + QGraphicsScene)
    """

    def __init__(self,
                 pixmap: QPixmap,
                 particle_size: int,
                 particle_direction: str = "down",
                 particle_count: int = 50,
                 opacity: float = 0.2,
                 screen_height: int = 1080,
                 screen_width: int = 1920,
                 particle_speed: float = 0.003):
        super().__init__()

        # Window size
        self.width = screen_width
        self.height = screen_height

        # ---- QWidget attributes (對齊原本 ParticleWidget) ----
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)

        if sys.platform == "win32":
            hwnd = int(self.winId())
            extended_style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            ctypes.windll.user32.SetWindowLongW(hwnd, -20,
                                                extended_style | 0x80000 | 0x20)  # WS_EX_LAYERED | WS_EX_TRANSPARENT

        # ---- Particle image ----
        target_size = pixmap.size().scaled(
            particle_size, particle_size,
            Qt.AspectRatioMode.KeepAspectRatio
        )
        self.image = pixmap.toImage().scaled(target_size)

        # ---- Particle parameters ----
        self.particle_count = particle_count
        self.particle_speed = particle_speed
        self.opacity = opacity
        self.direction = particle_direction

        # ---- Particle state (Scene replacement) ----
        self.particles = [
            [random.uniform(-1, 1), random.uniform(-1, 1)]
            for _ in range(particle_count)
        ]

        self.texture_id = None

        # ---- Animation timer ----
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(16)

    # ================= OpenGL lifecycle =================

    def initializeGL(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)

        image = self.image.convertToFormat(QImage.Format.Format_RGBA8888)
        width, height = image.width(), image.height()

        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGBA,
            width, height, 0,
            GL_RGBA, GL_UNSIGNED_BYTE,
            image.bits()
        )

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    def paintGL(self):
        glClearColor(0, 0, 0, 0)
        glClear(GL_COLOR_BUFFER_BIT)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glColor4f(1.0, 1.0, 1.0, self.opacity)

        size = 0.04

        glBegin(GL_QUADS)
        for x, y in self.particles:
            glTexCoord2f(0, 0)
            glVertex2f(x - size, y - size)
            glTexCoord2f(1, 0)
            glVertex2f(x + size, y - size)
            glTexCoord2f(1, 1)
            glVertex2f(x + size, y + size)
            glTexCoord2f(0, 1)
            glVertex2f(x - size, y + size)
        glEnd()

        self._update_particles()

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(-1, 1, -1, 1, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    # ================= Logic (Scene replacement) =================

    def _update_particles(self):

        for p in self.particles:
            if self.direction == "down":
                p[1] -= self.particle_speed
                if p[1] < -1:
                    p[1] = 1
                    p[0] = random.uniform(-1, 1)

            elif self.direction == "up":
                p[1] += self.particle_speed
                if p[1] > 1:
                    p[1] = -1
                    p[0] = random.uniform(-1, 1)

            elif self.direction == "left":
                p[0] -= self.particle_speed
                if p[0] < -1:
                    p[0] = 1
                    p[1] = random.uniform(-1, 1)

            elif self.direction == "right":
                p[0] += self.particle_speed
                if p[0] > 1:
                    p[0] = -1
                    p[1] = random.uniform(-1, 1)

            # Diagonal directions
            elif self.direction == "left_down":
                p[0] -= self.particle_speed
                p[1] -= self.particle_speed
                if p[0] < -1 or p[1] < -1:
                    p[0] = random.uniform(-1, 1)
                    p[1] = 1

            elif self.direction == "left_up":
                p[0] -= self.particle_speed
                p[1] += self.particle_speed
                if p[0] < -1 or p[1] > 1:
                    p[0] = random.uniform(-1, 1)
                    p[1] = -1

            elif self.direction == "right_down":
                p[0] += self.particle_speed
                p[1] -= self.particle_speed
                if p[0] > 1 or p[1] < -1:
                    p[0] = random.uniform(-1, 1)
                    p[1] = 1

            elif self.direction == "right_up":
                p[0] += self.particle_speed
                p[1] += self.particle_speed
                if p[0] > 1 or p[1] > 1:
                    p[0] = random.uniform(-1, 1)
                    p[1] = -1

            # Randomized modes
            elif self.direction == "random_minus":
                p[0] -= random.uniform(0, self.particle_speed)
                p[1] -= random.uniform(0, self.particle_speed)
                if p[0] < -1 or p[1] < -1:
                    p[0] = random.uniform(-1, 1)
                    p[1] = random.uniform(-1, 1)

            elif self.direction == "random_add":
                p[0] += random.uniform(0, self.particle_speed)
                p[1] += random.uniform(0, self.particle_speed)
                if p[0] > 1 or p[1] > 1:
                    p[0] = random.uniform(-1, 1)
                    p[1] = random.uniform(-1, 1)

            elif self.direction == "random":
                p[0] += random.uniform(-self.particle_speed, self.particle_speed)
                p[1] += random.uniform(-self.particle_speed, self.particle_speed)
                # Wrap-around if out of bounds
                if p[0] < -1 or p[0] > 1 or p[1] < -1 or p[1] > 1:
                    p[0] = random.uniform(-1, 1)
                    p[1] = random.uniform(-1, 1)

    def set_ui_window_flag(self) -> None:
        """ 設定視窗旗標 (保持最上層或最下層) Set window flags (stay on top or bottom) """
        front_engine_logger.info(f"[ParticleWidget] set_ui_window_flag")
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool)
