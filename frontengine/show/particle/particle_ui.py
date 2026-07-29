import random
import sys

# 明確列出用到的 OpenGL 名稱。星號匯入會讓靜態檢查完全看不出哪些名字存在，
# 也就是說整個檔案的「未定義名稱」檢查等於失效。
# The OpenGL names this file uses, spelled out. A star import blinds static
# analysis to what exists, which switches off undefined-name checking for the
# whole file.
from OpenGL.GL import (
    GL_BLEND, GL_COLOR_BUFFER_BIT, GL_CULL_FACE, GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST,
    GL_LINEAR, GL_MODELVIEW, GL_ONE_MINUS_SRC_ALPHA, GL_PROJECTION, GL_QUADS, GL_RGBA,
    GL_SRC_ALPHA, GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_TEXTURE_MIN_FILTER,
    GL_UNSIGNED_BYTE, glBegin, glBindTexture, glBlendFunc, glClear, glClearColor, glColor4f,
    glDisable, glEnable, glEnd, glGenTextures, glLoadIdentity, glMatrixMode, glOrtho,
    glTexCoord2f, glTexImage2D, glTexParameteri, glTranslatef, glVertex2f, glViewport,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QSurfaceFormat, QPixmap
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from frontengine.show.window_helpers import apply_overlay_window_flags, load_overlay_icon

if sys.platform == "win32":
    import ctypes


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

        apply_overlay_window_flags(self, show_on_bottom=False)

        self.resize(screen_width, screen_height)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAutoFillBackground(False)
        load_overlay_icon(self)

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
        # QPixmap.toImage() 給的是 ARGB32（記憶體順序 BGRA），直接當成 GL_RGBA 上傳
        # 會把紅藍對調。轉成 RGBA8888 才和下面的 glTexImage2D 對得起來，
        # 順帶去掉預乘 alpha，符合 GL_SRC_ALPHA 混色的預期。
        # toImage() hands back ARGB32, i.e. BGRA in memory; uploading that as
        # GL_RGBA swaps red and blue. RGBA8888 matches the glTexImage2D call
        # below and is un-premultiplied, which is what GL_SRC_ALPHA expects.
        self.image = scaled_pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)

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

        if sys.platform == "win32":
            QTimer.singleShot(0, self.apply_winapi)

    def apply_winapi(self):
        if sys.platform != "win32":
            return
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

        if self.image.isNull():
            # 沒有材質就別上傳 0x0 的貼圖，畫的時候直接跳過
            # No texture: skip the 0x0 upload and let paintGL bail out.
            return

        w, h = self.image.width(), self.image.height()

        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, self.image.bits())
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    # 每個方向：(要移動的軸, 每步的位移正負, 越過哪一邊算離場)
    # Per direction: which axis moves, the sign of each step, and which edge
    # counts as leaving the screen.
    _DIRECTIONS = {
        "down": (1, -1, -1.0),
        "up": (1, +1, +1.0),
        "left": (0, -1, -1.0),
        "right": (0, +1, +1.0),
    }

    def update_particles(self):
        """把每個粒子往設定的方向推一步，離開畫面的就從對面重新進場。"""
        movement = self._DIRECTIONS.get(self.particle_direction)
        if movement is None:
            self.update()
            return
        axis, sign, edge = movement
        other = 1 - axis
        for particle in self.particles:
            particle[axis] += sign * self.particle_speed
            if self._left_the_screen(particle[axis], sign, edge):
                # 從對面邊緣回來，另一軸重新隨機，看起來才像源源不絕
                # Re-enter from the opposite edge with a fresh position on the
                # other axis, so the stream never looks like a repeating loop.
                particle[axis] = -edge
                particle[other] = random.uniform(-1, 1)  # nosec B311 - visual only
        self.update()

    @staticmethod
    def _left_the_screen(value: float, sign: int, edge: float) -> bool:
        """這個粒子是不是已經越過它前進方向的那一邊。"""
        return value < edge if sign < 0 else value > edge

    def paintGL(self):
        glClearColor(0, 0, 0, 0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if self.texture_id is None:
            return

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

    def set_ui_window_flag(self, show_on_bottom: bool = False) -> None:
        apply_overlay_window_flags(self, show_on_bottom=show_on_bottom)

    def closeEvent(self, event) -> None:
        # 關掉之後還在跑 60Hz 更新上萬顆粒子，畫面卻早就沒了
        # Without this the 60 Hz update keeps churning through every particle
        # long after the overlay has gone from the screen.
        self.timer.stop()
        super().closeEvent(event)
