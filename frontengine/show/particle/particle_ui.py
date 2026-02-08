import random

from OpenGL.GL import *
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QSurfaceFormat, QPixmap
from PySide6.QtOpenGLWidgets import QOpenGLWidget


class ParticleOpenGLWidget(QOpenGLWidget):
    def __init__(self,
                 pixmap: QPixmap,
                 particle_size: int,
                 particle_direction: str = "down",
                 particle_count: int = 50,
                 opacity: float = 0.2,
                 screen_height: int = 1080,
                 screen_width: int = 1920,
                 particle_speed: float = 0.003):

        fmt = QSurfaceFormat()
        fmt.setAlphaBufferSize(8)
        fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
        QSurfaceFormat.setDefaultFormat(fmt)
        super().__init__()

        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        # 視窗大小
        self.resize(screen_width, screen_height)

        # Qt 透明背景設定
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        # 縮放 pixmap 成 particle_size（保持比例）
        target_size = pixmap.size().scaled(
            particle_size, particle_size,
            Qt.AspectRatioMode.KeepAspectRatio
        )
        scaled_pixmap = pixmap.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image = scaled_pixmap.toImage()

        self.particle_count = particle_count
        self.particle_direction = particle_direction
        self.opacity = opacity
        self.particle_speed = particle_speed

        # 粒子狀態 [x, y]
        self.particles = [
            [random.uniform(-1, 1), random.uniform(-1, 1)]
            for _ in range(particle_count)
        ]

        self.texture_id = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_particles)
        self.timer.start(16)

        QTimer.singleShot(0, self.apply_winapi)

    def apply_winapi(self):
        hwnd = int(self.winId())
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x80000
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED)

    def initializeGL(self):
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)

        w, h = self.image.width(), self.image.height()

        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, self.image.bits())
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    def update_particles(self):
        for p in self.particles:
            x, y = p
            if self.particle_direction == "down":
                y -= self.particle_speed
                if y < -1:
                    y = 1
                    x = random.uniform(-1, 1)

            elif self.particle_direction == "up":
                y += self.particle_speed
                if y > 1:
                    y = -1
                    x = random.uniform(-1, 1)

            elif self.particle_direction == "left":
                x -= self.particle_speed
                if x < -1:
                    x = 1
                    y = random.uniform(-1, 1)

            elif self.particle_direction == "right":
                x += self.particle_speed
                if x > 1:
                    x = -1
                    y = random.uniform(-1, 1)

            # 你可以自行擴充其他方向

            p[0] = x
            p[1] = y

        self.update()

    def paintGL(self):
        glClearColor(0, 0, 0, 0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glColor4f(1, 1, 1, self.opacity)

        size_x = self.image.width() / 2000  # 根據解析度調整大小
        size_y = self.image.height() / 2000

        for x, y in self.particles:
            glLoadIdentity()
            glTranslatef(x, y, 0)

            glBegin(GL_QUADS)
            glTexCoord2f(0, 1)
            glVertex2f(-size_x, -size_y)
            glTexCoord2f(1, 1)
            glVertex2f(size_x, -size_y)
            glTexCoord2f(1, 0)
            glVertex2f(size_x, size_y)
            glTexCoord2f(0, 0)
            glVertex2f(-size_x, size_y)
            glEnd()

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(-1, 1, -1, 1, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def set_ui_window_flag(self) -> None:
        """ 設定視窗旗標 (保持最上層或最下層) Set window flags (stay on top or bottom) """
        self.setWindowFlag(
            Qt.WindowType.Window |
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool)
