from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QRect, QTimer
from PySide6.QtGui import QAction, QMovie, QPainter, QPixmap, QTransform
from PySide6.QtWidgets import QMenu, QMessageBox

from frontengine.show.base_widget import BaseWidget
from frontengine.show.window_helpers import apply_overlay_window_flags
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class PetMotion:
    """
    純邏輯的移動模型（不依賴 Qt，便於測試）。gravity=True 時寵物沿著底部
    行走並在左右邊緣轉向；否則在四邊之間自由彈跳。
    Pure movement model (no Qt, easy to test). With gravity the pet walks
    along the floor and turns at the left/right edges; otherwise it bounces
    freely between all four edges.
    """

    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        bounds: Tuple[int, int, int, int],
        speed: int = 3,
        gravity: bool = True,
    ) -> None:
        self.x = float(x)
        self.y = float(y)
        self.width = int(width)
        self.height = int(height)
        self.bounds = bounds  # (left, top, right, bottom)
        self.speed = max(1, int(speed))
        self.gravity = bool(gravity)
        self.vx = float(self.speed)
        self.vy = 0.0 if gravity else float(self.speed)

    @property
    def facing_left(self) -> bool:
        return self.vx < 0

    def set_bounds(self, bounds: Tuple[int, int, int, int]) -> None:
        self.bounds = bounds

    def step(self) -> Tuple[int, int]:
        left, top, right, bottom = self.bounds
        self.x += self.vx
        if self.gravity:
            self.y = float(bottom - self.height)
        else:
            self.y += self.vy
            if self.y <= top:
                self.y = float(top)
                self.vy = abs(self.vy)
            elif self.y + self.height >= bottom:
                self.y = float(bottom - self.height)
                self.vy = -abs(self.vy)
        if self.x <= left:
            self.x = float(left)
            self.vx = abs(self.vx)
        elif self.x + self.width >= right:
            self.x = float(right - self.width)
            self.vx = -abs(self.vx)
        return int(self.x), int(self.y)


class DesktopPetWidget(BaseWidget):
    """
    桌面寵物：可自主走動、可拖曳的動畫精靈。支援 GIF（QMovie）與靜態圖。
    A draggable, self-walking animated sprite. Supports GIF (QMovie) and
    static images.
    """

    def __init__(self, image_path: str, size: int = 128, speed: int = 3, gravity: bool = True):
        front_engine_logger.info(
            f"[DesktopPetWidget] Init | path={image_path}, size={size}, speed={speed}, gravity={gravity}"
        )
        super().__init__()
        self.opacity = 1.0
        self.pet_size: int = max(16, int(size))
        self.image_path: Path = Path(image_path)
        self.movie: Optional[QMovie] = None
        self.pixmap: Optional[QPixmap] = None
        self._dragging: bool = False
        self._drag_offset = None

        if self.image_path.exists() and self.image_path.is_file():
            if self.image_path.suffix.lower() in (".gif", ".webp"):
                self.movie = QMovie(str(self.image_path))
                self.movie.frameChanged.connect(self.update)
                self.movie.start()
            else:
                self.pixmap = QPixmap(str(self.image_path))
        else:
            front_engine_logger.error(f"[DesktopPetWidget] File not found: {self.image_path}")
            message_box = QMessageBox(self)
            message_box.setText(language_wrapper.language_word_dict.get("pet_message_box_text", "Pet image not found"))
            message_box.show()

        self.resize(self.pet_size, self.pet_size)
        self.motion = PetMotion(0, 0, self.pet_size, self.pet_size, (0, 0, 1920, 1080), speed, gravity)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

        # Right-click to close
        self.close_action = QAction(language_wrapper.language_word_dict.get("control_center_close_all", "Close"), self)
        self.close_action.triggered.connect(self.close)
        self.menu = QMenu(self)
        self.menu.addAction(self.close_action)

    def set_pet_window_flag(self) -> None:
        """寵物需接收滑鼠以便拖曳，故 allow_input=True 並置頂。"""
        apply_overlay_window_flags(self, show_on_bottom=False, allow_input=True)

    def _current_pixmap(self) -> Optional[QPixmap]:
        if self.movie is not None:
            return self.movie.currentPixmap()
        return self.pixmap

    def draw_content(self, painter: QPainter) -> None:
        pixmap = self._current_pixmap()
        if pixmap is None or pixmap.isNull():
            return
        if self.motion.facing_left:
            # Mirror horizontally so the sprite faces its walking direction.
            pixmap = pixmap.transformed(QTransform().scale(-1, 1))
        painter.drawPixmap(QRect(0, 0, self.width(), self.height()), pixmap)

    def start_moving(self, bounds: Tuple[int, int, int, int], interval_ms: int = 33) -> None:
        """在指定範圍內開始走動 / Start walking within `bounds` (left, top, right, bottom)."""
        front_engine_logger.info(f"[DesktopPetWidget] start_moving | bounds={bounds}")
        left, top, right, bottom = bounds
        self.motion.set_bounds(bounds)
        self.motion.x = float(left)
        self.motion.y = float(bottom - self.pet_size)
        self.move(int(self.motion.x), int(self.motion.y))
        self._timer.start(max(10, int(interval_ms)))

    def _on_tick(self) -> None:
        if self._dragging:
            return
        x, y = self.motion.step()
        self.move(x, y)

    # --- dragging ---
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._dragging and self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._dragging:
            self._dragging = False
            self.motion.x = float(self.x())
            self.motion.y = float(self.y())
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:
        self.menu.popup(event.globalPos())

    def closeEvent(self, event) -> None:
        if self._timer.isActive():
            self._timer.stop()
        if self.movie is not None:
            self.movie.stop()
        super().closeEvent(event)
