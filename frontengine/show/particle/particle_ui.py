import random
import sys
from dataclasses import dataclass
from typing import Callable, Optional

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
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QSurfaceFormat, QPixmap
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from frontengine.show.compositor.surface_check import see_through_problem
from frontengine.show.window_helpers import apply_overlay_window_flags, load_overlay_icon
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.power_mode.power_mode import normalize_tier, scaled_interval, tier_interval

if sys.platform == "win32":
    import ctypes

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000


@dataclass(frozen=True)
class ExStyleApi:
    """The four Win32 calls an extended-style update needs; tests pass fakes."""
    get_long: Callable[[int, int], int]
    set_long: Callable[[int, int, int], int]
    set_last_error: Callable[[int], object]
    get_last_error: Callable[[], int]

    @classmethod
    def native(cls) -> "ExStyleApi":
        """user32 with use_last_error, through the pointer-sized calls where they exist (64-bit)."""
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        get_long = getattr(user32, "GetWindowLongPtrW", None) or user32.GetWindowLongW
        set_long = getattr(user32, "SetWindowLongPtrW", None) or user32.SetWindowLongW
        get_long.argtypes, get_long.restype = (ctypes.c_void_p, ctypes.c_int), ctypes.c_ssize_t
        set_long.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t)
        set_long.restype = ctypes.c_ssize_t
        return cls(get_long, set_long, ctypes.set_last_error, ctypes.get_last_error)


def add_layered_style(hwnd: int, api: ExStyleApi) -> bool:
    """OR ``WS_EX_LAYERED`` into the window's extended style, keeping every bit already set.

    A read of 0 is ambiguous: a window may have no extended style, or the call failed. Only the
    last error tells them apart, so it is cleared first. After a failed read nothing is written,
    because writing ``0 | WS_EX_LAYERED`` would drop ``WS_EX_TRANSPARENT`` and with it the
    click-through the overlay flags set.
    """
    api.set_last_error(0)
    style = api.get_long(hwnd, GWL_EXSTYLE)
    if style == 0 and api.get_last_error():
        front_engine_logger.warning(
            f"[ParticleOpenGLWidget] extended style unreadable (error {api.get_last_error()}); left as is")
        return False
    if style & WS_EX_LAYERED:
        return True
    api.set_last_error(0)
    if api.set_long(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED) == 0 and api.get_last_error():
        front_engine_logger.warning(
            f"[ParticleOpenGLWidget] extended style not written (error {api.get_last_error()})")
        return False
    return True


class ParticleOpenGLWidget(QOpenGLWidget):
    # The context cannot draw this see-through window (surface_check): the reason, then it closes
    # rather than leave the screen black behind a full-screen field.
    failed = Signal(str)

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
        super().__init__()
        self.setFormat(fmt)

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
        self.quality_tier = normalize_tier(user_setting_dict.get("quality_tier"))
        self.low_power = bool(user_setting_dict.get("low_power"))
        self._start_timer()

        if sys.platform == "win32":
            QTimer.singleShot(0, self.apply_winapi)

    def _start_timer(self) -> None:
        self.timer.start(tier_interval(scaled_interval(16, self.low_power), self.quality_tier))

    def set_quality_tier(self, tier: str) -> None:
        self.quality_tier = normalize_tier(tier)
        if self.timer.isActive():
            self._start_timer()

    def set_low_power(self, enabled: bool) -> None:
        self.low_power = bool(enabled)
        if self.timer.isActive():
            self._start_timer()

    def apply_winapi(self, api: Optional[ExStyleApi] = None) -> bool:
        """Make the window layered on Windows; ``api`` replaces user32 in tests."""
        if api is None:
            if sys.platform != "win32":
                return False
            api = ExStyleApi.native()
        return add_layered_style(int(self.winId()), api)

    def initializeGL(self):
        # Checked once the context exists, outside initializeGL, like the GPU compositor.
        QTimer.singleShot(0, self, self._check_surface)
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

    def _check_surface(self) -> None:
        problem = see_through_problem(self)
        if not problem:
            return
        front_engine_logger.warning(f"[ParticleOpenGLWidget] stopped: {problem}")
        self.timer.stop()
        self.failed.emit(problem)
        self.close()

    def set_ui_window_flag(self, show_on_bottom: bool = False) -> None:
        apply_overlay_window_flags(self, show_on_bottom=show_on_bottom)

    def closeEvent(self, event) -> None:
        # 關掉之後還在跑 60Hz 更新上萬顆粒子，畫面卻早就沒了
        # Without this the 60 Hz update keeps churning through every particle
        # long after the overlay has gone from the screen.
        self.timer.stop()
        super().closeEvent(event)
