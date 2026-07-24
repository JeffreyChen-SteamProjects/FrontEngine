import random as _random_module
from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QRect, QTimer
from PySide6.QtGui import QAction, QCursor, QMovie, QPainter, QPixmap, QTransform
from PySide6.QtWidgets import QMenu, QMessageBox

from frontengine.show.base_widget import BaseWidget
from frontengine.show.window_helpers import apply_overlay_window_flags
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper

# 行為模式 / Behaviour modes
BEHAVIOUR_FLOOR = "floor"    # walk on the floor with gravity, throw & bounce
BEHAVIOUR_WANDER = "wander"  # free 2D bounce, no gravity
BEHAVIOUR_CHASE = "chase"    # chase the mouse cursor, sleep when caught


class PetMotion:
    """
    純邏輯的寵物移動模型（不依賴 Qt，完全可測試）。包含：
      - 重力落下、落地、彈跳（受動量丟出後）
      - 走路/發呆的隨機行為狀態機（rng 可注入以利測試）
      - 追逐游標模式（追到後進入睡眠，游標移動即醒）
    A pure, Qt-free motion model: gravity fall/land/bounce (after a throw),
    a random walk/idle behaviour state machine (injectable rng), and a
    cursor-chase mode that sleeps once it catches the target.
    """

    GRAVITY = 2.0
    BOUNCE_DAMPING = 0.55
    WALL_DAMPING = 0.6
    BOUNCE_THRESHOLD = 8.0
    CHASE_STOP_DISTANCE = 10.0
    CHASE_SPEED_FACTOR = 2.0

    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        bounds: Tuple[int, int, int, int],
        speed: int = 3,
        behaviour: str = BEHAVIOUR_FLOOR,
        rng=None,
    ) -> None:
        self.x = float(x)
        self.y = float(y)
        self.width = int(width)
        self.height = int(height)
        self.bounds = bounds  # (left, top, right, bottom)
        self.speed = max(1, int(speed))
        self.behaviour = behaviour
        self._rng = rng if rng is not None else _random_module.SystemRandom()
        self.vx = float(self.speed)
        self.vy = 0.0 if behaviour != BEHAVIOUR_WANDER else float(self.speed)
        self._airborne = False
        self.state = "walk"  # walk | idle
        self._state_ticks = 0
        self.target: Optional[Tuple[float, float]] = None
        self.asleep = False

    @property
    def facing_left(self) -> bool:
        return self.vx < 0

    def set_bounds(self, bounds: Tuple[int, int, int, int]) -> None:
        self.bounds = bounds

    def set_target(self, x: float, y: float) -> None:
        self.target = (float(x), float(y))

    def throw(self, vx: float, vy: float) -> None:
        """拖曳放開後以動量丟出（只在重力模式有意義）。"""
        self.vx = float(vx)
        self.vy = float(vy)
        self._airborne = True
        self.asleep = False

    def step(self) -> Tuple[int, int]:
        left, top, right, bottom = self.bounds
        floor_y = bottom - self.height
        if self.behaviour == BEHAVIOUR_CHASE:
            return self._step_chase(left, top, right, bottom)
        if self.behaviour == BEHAVIOUR_WANDER:
            return self._step_wander(left, top, right, bottom)
        return self._step_floor(left, top, right, bottom, floor_y)

    # --- floor / gravity ---
    def _step_floor(self, left, top, right, bottom, floor_y) -> Tuple[int, int]:
        airborne = self._airborne or self.y < floor_y - 0.5
        if airborne:
            self.vy += self.GRAVITY
            self.x += self.vx
            self.y += self.vy
            if self.x <= left:
                self.x = float(left)
                self.vx = abs(self.vx) * self.WALL_DAMPING
            elif self.x + self.width >= right:
                self.x = float(right - self.width)
                self.vx = -abs(self.vx) * self.WALL_DAMPING
            if self.y <= top:
                self.y = float(top)
                self.vy = abs(self.vy) * self.WALL_DAMPING
            if self.y >= floor_y:
                self.y = float(floor_y)
                if abs(self.vy) > self.BOUNCE_THRESHOLD:
                    self.vy = -self.vy * self.BOUNCE_DAMPING
                else:
                    self.vy = 0.0
                    self._airborne = False
                    self.vx = float(self.speed) if self.vx >= 0 else float(-self.speed)
                    self._new_state(force_walk=True)
            return int(self.x), int(self.y)

        # grounded: random walk / idle
        self.y = float(floor_y)
        if self._state_ticks <= 0:
            self._new_state()
        self._state_ticks -= 1
        if self.state == "walk":
            self.x += self.vx
            if self.x <= left:
                self.x = float(left)
                self.vx = abs(self.vx)
            elif self.x + self.width >= right:
                self.x = float(right - self.width)
                self.vx = -abs(self.vx)
        return int(self.x), int(self.y)

    def _new_state(self, force_walk: bool = False) -> None:
        if force_walk or self._rng.random() < 0.65:
            self.state = "walk"
            if not force_walk:
                self.vx = float(self.speed) if self._rng.random() < 0.5 else float(-self.speed)
            self._state_ticks = self._rng.randint(30, 120)
        else:
            self.state = "idle"
            self._state_ticks = self._rng.randint(20, 80)

    # --- free wander ---
    def _step_wander(self, left, top, right, bottom) -> Tuple[int, int]:
        if abs(self.vy) < 1e-9:
            self.vy = float(self.speed)
        self.x += self.vx
        self.y += self.vy
        if self.x <= left:
            self.x = float(left)
            self.vx = abs(self.vx)
        elif self.x + self.width >= right:
            self.x = float(right - self.width)
            self.vx = -abs(self.vx)
        if self.y <= top:
            self.y = float(top)
            self.vy = abs(self.vy)
        elif self.y + self.height >= bottom:
            self.y = float(bottom - self.height)
            self.vy = -abs(self.vy)
        return int(self.x), int(self.y)

    # --- chase cursor ---
    def _step_chase(self, left, top, right, bottom) -> Tuple[int, int]:
        if self.target is None:
            return int(self.x), int(self.y)
        target_x, target_y = self.target
        dx = target_x - (self.x + self.width / 2)
        dy = target_y - (self.y + self.height / 2)
        distance = (dx * dx + dy * dy) ** 0.5
        if distance <= self.CHASE_STOP_DISTANCE:
            self.asleep = True
            return int(self.x), int(self.y)
        self.asleep = False
        step = float(self.speed) * self.CHASE_SPEED_FACTOR
        self.x += step * (dx / distance)
        self.y += step * (dy / distance)
        self.vx = abs(self.vx) if dx >= 0 else -abs(self.vx)
        self.x = min(max(self.x, float(left)), float(right - self.width))
        self.y = min(max(self.y, float(top)), float(bottom - self.height))
        return int(self.x), int(self.y)


class DesktopPetWidget(BaseWidget):
    """
    桌面寵物：可自主走動、可拖曳丟出、可追游標的動畫精靈。支援 GIF 與靜態圖。
    A draggable, throwable, cursor-chasing animated sprite (GIF or image).
    """

    def __init__(self, image_path: str, size: int = 128, speed: int = 3,
                 behaviour: str = BEHAVIOUR_FLOOR):
        front_engine_logger.info(
            f"[DesktopPetWidget] Init | path={image_path}, size={size}, speed={speed}, behaviour={behaviour}"
        )
        super().__init__()
        self.opacity = 1.0
        self.pet_size: int = max(16, int(size))
        self.image_path: Path = Path(image_path)
        self.movie: Optional[QMovie] = None
        self.pixmap: Optional[QPixmap] = None
        self._dragging: bool = False
        self._drag_offset = None
        self._last_move_delta: Tuple[int, int] = (0, 0)

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
        self.motion = PetMotion(0, 0, self.pet_size, self.pet_size, (0, 0, 1920, 1080), speed, behaviour)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

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
            pixmap = pixmap.transformed(QTransform().scale(-1, 1))
        painter.drawPixmap(QRect(0, 0, self.width(), self.height()), pixmap)

    def start_moving(self, bounds: Tuple[int, int, int, int], interval_ms: int = 33) -> None:
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
        if self.motion.behaviour == BEHAVIOUR_CHASE:
            cursor = QCursor.pos()
            self.motion.set_target(cursor.x(), cursor.y())
        x, y = self.motion.step()
        self.move(x, y)

    # --- dragging + throwing ---
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._last_move_delta = (0, 0)
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._dragging and self._drag_offset is not None:
            new_top_left = event.globalPosition().toPoint() - self._drag_offset
            self._last_move_delta = (new_top_left.x() - self.x(), new_top_left.y() - self.y())
            self.move(new_top_left)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._dragging:
            self._dragging = False
            self.motion.x = float(self.x())
            self.motion.y = float(self.y())
            # Fling with the momentum of the last drag movement (floor mode).
            if self.motion.behaviour == BEHAVIOUR_FLOOR:
                self.motion.throw(self._last_move_delta[0], self._last_move_delta[1])
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:
        self.menu.popup(event.globalPos())

    def closeEvent(self, event) -> None:
        if self._timer.isActive():
            self._timer.stop()
        if self.movie is not None:
            self.movie.stop()
        super().closeEvent(event)
