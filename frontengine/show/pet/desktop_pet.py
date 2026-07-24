import random as _random_module
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QRect, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QFontMetrics, QMovie, QPainter, QPixmap, QTransform
from PySide6.QtWidgets import QMenu, QMessageBox, QWidget

from frontengine.show.base_widget import BaseWidget
from frontengine.show.window_helpers import apply_overlay_window_flags
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper

# 行為模式 / Behaviour modes
BEHAVIOUR_FLOOR = "floor"    # walk on the floor with gravity, throw & bounce
BEHAVIOUR_WANDER = "wander"  # free 2D bounce, no gravity
BEHAVIOUR_CHASE = "chase"    # chase the mouse cursor, sleep when caught

# 攀爬時所在的表面 / Surface the pet is crawling on while climbing
SURFACE_FLOOR = "floor"
SURFACE_LEFT = "left"
SURFACE_CEILING = "ceiling"
SURFACE_RIGHT = "right"

# 視覺狀態（決定顯示哪張精靈）/ Visual states (which sprite to show)
STATE_WALK = "walk"
STATE_IDLE = "idle"
STATE_SLEEP = "sleep"
STATE_CLIMB = "climb"
STATE_FALL = "fall"
STATE_DRAG = "drag"

# 動作包（資料夾）中，各狀態可接受的檔名（不含副檔名，先命中者為準）
# Accepted file stems per state inside a pet pack folder (first match wins).
_PACK_STATE_ALIASES = {
    STATE_WALK: ("walk", "run", "move"),
    STATE_IDLE: ("idle", "sit", "stand"),
    STATE_SLEEP: ("sleep", "zzz", "rest"),
    STATE_CLIMB: ("climb", "grab", "wall"),
    STATE_FALL: ("fall", "jump"),
    STATE_DRAG: ("drag", "pinch", "grabbed", "held"),
}
_PACK_EXTS = (".gif", ".webp", ".png", ".jpg", ".jpeg")

# 缺該狀態精靈時的退回順序 / Fallback order when a state's sprite is missing
_STATE_FALLBACKS = {
    STATE_SLEEP: (STATE_IDLE, STATE_WALK),
    STATE_IDLE: (STATE_WALK,),
    STATE_CLIMB: (STATE_WALK,),
    STATE_FALL: (STATE_WALK,),
    STATE_DRAG: (STATE_WALK,),
}


def scan_pet_pack(folder: str) -> dict:
    """
    掃描動作包資料夾，回傳「視覺狀態 -> 圖片路徑」對應。非資料夾回傳空 dict。
    Scan a pet-pack folder and return a ``state -> image path`` mapping.
    Returns {} when `folder` is not a directory.
    """
    result: dict = {}
    try:
        folder_path = Path(folder)
        if not folder_path.is_dir():
            return result
        by_stem = {
            path.stem.lower(): path
            for path in sorted(folder_path.iterdir())
            if path.is_file() and path.suffix.lower() in _PACK_EXTS
        }
        for state, aliases in _PACK_STATE_ALIASES.items():
            for alias in aliases:
                if alias in by_stem:
                    result[state] = str(by_stem[alias])
                    break
    except OSError:
        pass
    return result


def derive_visual_state(dragging: bool, airborne: bool, surface: str, motion_state: str) -> str:
    """依目前情形推導應顯示的視覺狀態 / Derive which sprite state to show."""
    if dragging:
        return STATE_DRAG
    if airborne:
        return STATE_FALL
    if surface in (SURFACE_LEFT, SURFACE_RIGHT, SURFACE_CEILING):
        return STATE_CLIMB
    if surface == SURFACE_FLOOR and motion_state == STATE_SLEEP:
        return STATE_SLEEP
    if surface == SURFACE_FLOOR and motion_state == "idle":
        return STATE_IDLE
    return STATE_WALK


def message_bucket(hour: int) -> str:
    """依小時回傳時段 / Time-of-day bucket for the given hour."""
    hour = int(hour) % 24
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 22:
        return "evening"
    return "night"


def pick_message(hour: int, rng, messages: dict, mood: Optional[str] = None) -> str:
    """
    挑一句台詞：先放心情句庫（若有），再放時段句庫、通用句庫。皆空回傳空字串。
    Pick a chatter line: mood pool (if any) first, then the time-of-day pool,
    then the generic pool. rng needs ``randrange``.
    """
    pool = []
    if mood and mood in messages:
        pool += list(messages[mood])
    pool += list(messages.get(message_bucket(hour), []))
    pool += list(messages.get("any", []))
    if not pool:
        return ""
    return pool[rng.randrange(len(pool))]


class PetMood:
    """
    寵物心情值 0~100：互動會上升、被忽略會慢慢下降；level() 回傳 happy/content/sad。
    Pet happiness 0..100: petting raises it, neglect decays it; level() buckets it.
    """

    HAPPY = "happy"
    CONTENT = "content"
    SAD = "sad"

    def __init__(self, value: int = 60) -> None:
        self.value = self._clamp(value)

    @staticmethod
    def _clamp(value) -> int:
        try:
            return max(0, min(100, int(value)))
        except (TypeError, ValueError):
            return 60

    def pet(self, amount: int = 12) -> None:
        self.value = self._clamp(self.value + amount)

    def decay(self, amount: int = 1) -> None:
        self.value = self._clamp(self.value - amount)

    def level(self) -> str:
        if self.value >= 70:
            return self.HAPPY
        if self.value <= 30:
            return self.SAD
        return self.CONTENT


class SpeechBubble(QWidget):
    """寵物頭上的小對話泡泡，數秒後自動消失 / A small speech bubble that auto-hides."""

    def __init__(self) -> None:
        super().__init__()
        self._text = ""
        self._font = QFont()
        self._font.setPointSize(11)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        apply_overlay_window_flags(self, show_on_bottom=False, allow_input=False)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def show_message(self, text: str, anchor: QWidget, duration_ms: int = 4000) -> None:
        self._text = text
        width = min(260, QFontMetrics(self._font).horizontalAdvance(text) + 28)
        self.resize(max(60, width), 44)
        self.reposition(anchor)
        self.show()
        self.raise_()
        self.update()
        self._hide_timer.start(max(500, int(duration_ms)))

    def reposition(self, anchor: QWidget) -> None:
        geo = anchor.frameGeometry()
        self.move(geo.center().x() - self.width() // 2, geo.top() - self.height() - 6)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setBrush(QColor(255, 255, 240, 235))
        painter.setPen(QColor(90, 90, 90))
        painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(QColor(30, 30, 30))
        painter.setFont(self._font)
        painter.drawText(
            rect.adjusted(8, 2, -8, -2),
            int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
            self._text,
        )


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
    CLIMB_CHANCE = 0.5      # chance to grab a wall (vs. turn around) at a floor corner
    DROP_CHANCE = 0.008     # chance per step to let go while on a wall/ceiling

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
        climb: bool = True,
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
        self.state = "walk"  # walk | idle | sleep
        self._state_ticks = 0
        self._idle_count = 0
        self.target: Optional[Tuple[float, float]] = None
        self.asleep = False
        self.climb = bool(climb)
        self.surface = SURFACE_FLOOR

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
        self.surface = SURFACE_FLOOR

    def step(self) -> Tuple[int, int]:
        left, top, right, bottom = self.bounds
        floor_y = bottom - self.height
        if self.behaviour == BEHAVIOUR_CHASE:
            return self._step_chase(left, top, right, bottom)
        if self.behaviour == BEHAVIOUR_WANDER:
            return self._step_wander(left, top, right, bottom)
        return self._step_floor(left, top, right, bottom, floor_y)

    # --- floor / gravity / climbing ---
    def _step_floor(self, left, top, right, bottom, floor_y) -> Tuple[int, int]:
        airborne = self._airborne or (self.surface == SURFACE_FLOOR and self.y < floor_y - 0.5)
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
                    self.surface = SURFACE_FLOOR
                    self.vx = float(self.speed) if self.vx >= 0 else float(-self.speed)
                    self._new_state(force_walk=True)
            return int(self.x), int(self.y)

        if self.surface != SURFACE_FLOOR:
            return self._step_climb(left, top, right, bottom, floor_y)

        # grounded on the floor: random walk / idle, with a chance to climb a wall
        self.y = float(floor_y)
        if self._state_ticks <= 0:
            self._new_state()
        self._state_ticks -= 1
        if self.state != "walk":
            return int(self.x), int(self.y)
        self.x += self.vx
        if self.x <= left:
            self.x = float(left)
            if self.climb and self._rng.random() < self.CLIMB_CHANCE:
                self.surface = SURFACE_LEFT
                self.vy = float(-self.speed)
            else:
                self.vx = abs(self.vx)
        elif self.x + self.width >= right:
            self.x = float(right - self.width)
            if self.climb and self._rng.random() < self.CLIMB_CHANCE:
                self.surface = SURFACE_RIGHT
                self.vy = float(-self.speed)
            else:
                self.vx = -abs(self.vx)
        return int(self.x), int(self.y)

    def _step_climb(self, left, top, right, bottom, floor_y) -> Tuple[int, int]:
        """沿螢幕邊緣爬行；隨機放手則掉落 / Crawl the screen perimeter; may let go and fall."""
        if self._rng.random() < self.DROP_CHANCE:
            self.surface = SURFACE_FLOOR
            self._airborne = True
            self.vy = 1.0
            return int(self.x), int(self.y)

        if self.surface == SURFACE_RIGHT:
            self.x = float(right - self.width)
            self.y += self.vy
            if self.vy < 0 and self.y <= top:            # reached the ceiling, crawl left
                self.y = float(top)
                self.surface = SURFACE_CEILING
                self.vx = float(-self.speed)
            elif self.vy > 0 and self.y >= floor_y:      # climbed back down
                self.y = float(floor_y)
                self.surface = SURFACE_FLOOR
                self.vx = float(-self.speed)
                self._new_state(force_walk=True)
        elif self.surface == SURFACE_LEFT:
            self.x = float(left)
            self.y += self.vy
            if self.vy < 0 and self.y <= top:
                self.y = float(top)
                self.surface = SURFACE_CEILING
                self.vx = float(self.speed)
            elif self.vy > 0 and self.y >= floor_y:
                self.y = float(floor_y)
                self.surface = SURFACE_FLOOR
                self.vx = float(self.speed)
                self._new_state(force_walk=True)
        elif self.surface == SURFACE_CEILING:
            self.y = float(top)
            self.x += self.vx
            if self.vx < 0 and self.x <= left:           # corner -> climb down the left wall
                self.x = float(left)
                self.surface = SURFACE_LEFT
                self.vy = float(self.speed)
            elif self.vx > 0 and self.x + self.width >= right:
                self.x = float(right - self.width)
                self.surface = SURFACE_RIGHT
                self.vy = float(self.speed)
        return int(self.x), int(self.y)

    def _new_state(self, force_walk: bool = False) -> None:
        if force_walk or self._rng.random() < 0.65:
            self.state = "walk"
            self._idle_count = 0
            if not force_walk:
                self.vx = float(self.speed) if self._rng.random() < 0.5 else float(-self.speed)
            self._state_ticks = self._rng.randint(30, 120)
        elif self._idle_count >= 2:
            # been idling a while -> doze off
            self.state = STATE_SLEEP
            self._idle_count = 0
            self._state_ticks = self._rng.randint(120, 300)
        else:
            self.state = "idle"
            self._idle_count += 1
            self._state_ticks = self._rng.randint(20, 80)

    def wake(self) -> None:
        """喚醒寵物並恢復走動（互動時呼叫）/ Wake the pet and resume walking."""
        self._idle_count = 0
        self._new_state(force_walk=True)

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

    clone_requested = Signal()

    def __init__(self, image_path: str, size: int = 128, speed: int = 3,
                 behaviour: str = BEHAVIOUR_FLOOR, climb: bool = True, talk: bool = True):
        front_engine_logger.info(
            f"[DesktopPetWidget] Init | path={image_path}, size={size}, speed={speed}, "
            f"behaviour={behaviour}, climb={climb}, talk={talk}"
        )
        super().__init__()
        self.opacity = 1.0
        self.pet_size: int = max(16, int(size))
        self.image_path: Path = Path(image_path)
        self._dragging: bool = False
        self._drag_offset = None
        self._last_move_delta: Tuple[int, int] = (0, 0)
        # 視覺狀態 -> ("movie"|"pixmap", 物件) / state -> sprite
        self._sprites: dict = {}
        self._active = None
        self._active_state = None

        self._load_sprites(self.image_path)
        if not self._sprites:
            front_engine_logger.error(f"[DesktopPetWidget] No sprite found: {self.image_path}")
            message_box = QMessageBox(self)
            message_box.setText(language_wrapper.language_word_dict.get("pet_message_box_text", "Pet image not found"))
            message_box.show()

        self.resize(self.pet_size, self.pet_size)
        self.motion = PetMotion(
            0, 0, self.pet_size, self.pet_size, (0, 0, 1920, 1080), speed, behaviour, climb=climb
        )
        self._set_active_sprite(STATE_WALK)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

        # Speech bubbles / chatter / mood
        self._talk = bool(talk)
        self._moved = False
        self._chatter_rng = _random_module.SystemRandom()
        self._mood = PetMood(user_setting_dict.get("pet_mood", 60))
        self._messages = self._load_messages()
        self._bubble = SpeechBubble()
        self._chatter_timer = QTimer(self)
        self._chatter_timer.setSingleShot(True)
        self._chatter_timer.timeout.connect(self._on_chatter)

        self.menu = QMenu(self)
        self.clone_action = QAction(language_wrapper.language_word_dict.get("pet_clone", "Clone"), self)
        self.clone_action.triggered.connect(self.clone_requested.emit)
        self.menu.addAction(self.clone_action)
        self.close_action = QAction(language_wrapper.language_word_dict.get("control_center_close_all", "Close"), self)
        self.close_action.triggered.connect(self.close)
        self.menu.addAction(self.close_action)

    def set_pet_window_flag(self) -> None:
        """寵物需接收滑鼠以便拖曳，故 allow_input=True 並置頂。"""
        apply_overlay_window_flags(self, show_on_bottom=False, allow_input=True)

    def _load_sprite(self, path: str):
        if Path(path).suffix.lower() in (".gif", ".webp"):
            movie = QMovie(str(path))
            movie.frameChanged.connect(self.update)
            return ("movie", movie)
        return ("pixmap", QPixmap(str(path)))

    def _load_sprites(self, image_path: Path) -> None:
        """單一檔 -> 所有狀態共用；資料夾 -> 依檔名對應各狀態。"""
        if image_path.is_dir():
            for state, path in scan_pet_pack(str(image_path)).items():
                self._sprites[state] = self._load_sprite(path)
        elif image_path.is_file():
            self._sprites["default"] = self._load_sprite(str(image_path))

    def _sprite_for(self, state: str):
        if "default" in self._sprites:
            return self._sprites["default"]
        if state in self._sprites:
            return self._sprites[state]
        for fallback in _STATE_FALLBACKS.get(state, (STATE_WALK,)):
            if fallback in self._sprites:
                return self._sprites[fallback]
        return next(iter(self._sprites.values()), None)

    def _set_active_sprite(self, state: str) -> None:
        sprite = self._sprite_for(state)
        if sprite is None or sprite is self._active:
            return
        if self._active is not None and self._active[0] == "movie":
            self._active[1].stop()
        self._active = sprite
        self._active_state = state
        if sprite[0] == "movie":
            sprite[1].start()
        self.update()

    def _visual_state(self) -> str:
        return derive_visual_state(
            self._dragging, self.motion._airborne, self.motion.surface, self.motion.state
        )

    def _current_pixmap(self) -> Optional[QPixmap]:
        if self._active is None:
            return None
        kind, obj = self._active
        return obj.currentPixmap() if kind == "movie" else obj

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
        self._schedule_chatter()

    def _load_messages(self) -> dict:
        d = language_wrapper.language_word_dict

        def lines(key: str, fallback: str) -> list:
            return [part.strip() for part in str(d.get(key, fallback)).split("|") if part.strip()]

        return {
            "morning": lines("pet_chatter_morning", "Good morning!|Ready for the day?"),
            "afternoon": lines("pet_chatter_afternoon", "Good afternoon!|Taking a break?"),
            "evening": lines("pet_chatter_evening", "Good evening!|How was your day?"),
            "night": lines("pet_chatter_night", "It's late - get some rest!|Still up?"),
            "happy": lines("pet_chatter_happy", "I'm so happy!|You're the best!|(^o^)"),
            "sad": lines("pet_chatter_sad", "Feeling a bit lonely...|Pet me?|(._.)"),
            "any": lines("pet_chatter_any", "Hi there!|(^_^)|Keep going!"),
        }

    def _persist_mood(self) -> None:
        user_setting_dict["pet_mood"] = self._mood.value

    def _schedule_chatter(self) -> None:
        if self._talk:
            self._chatter_timer.start(self._chatter_rng.randint(15000, 35000))

    def _on_chatter(self) -> None:
        self._mood.decay()  # a little neglect over time
        self._persist_mood()
        self.say()
        self._schedule_chatter()

    def say(self, text: Optional[str] = None) -> None:
        """顯示一句台詞（text 為 None 時依心情/時段隨機挑）。"""
        if not self._talk:
            return
        if text is None:
            level = self._mood.level()
            mood = level if level in (PetMood.HAPPY, PetMood.SAD) else None
            text = pick_message(datetime.now().hour, self._chatter_rng, self._messages, mood=mood)
        if text:
            self._bubble.show_message(text, self)

    def _on_tick(self) -> None:
        if self._dragging:
            self._set_active_sprite(STATE_DRAG)
            return
        if self.motion.behaviour == BEHAVIOUR_CHASE:
            cursor = QCursor.pos()
            self.motion.set_target(cursor.x(), cursor.y())
        x, y = self.motion.step()
        self.move(x, y)
        self._set_active_sprite(self._visual_state())
        if self._bubble.isVisible():
            self._bubble.reposition(self)

    # --- dragging + throwing ---
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._moved = False
            self._last_move_delta = (0, 0)
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.motion.wake()  # interacting wakes a sleeping pet
            self._mood.pet()    # petting cheers it up
            self._persist_mood()
            self._set_active_sprite(STATE_DRAG)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._dragging and self._drag_offset is not None:
            new_top_left = event.globalPosition().toPoint() - self._drag_offset
            self._last_move_delta = (new_top_left.x() - self.x(), new_top_left.y() - self.y())
            self._moved = True
            self.move(new_top_left)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._dragging:
            self._dragging = False
            self.motion.x = float(self.x())
            self.motion.y = float(self.y())
            if self._moved:
                # Fling with the momentum of the last drag movement (floor mode).
                if self.motion.behaviour == BEHAVIOUR_FLOOR:
                    self.motion.throw(self._last_move_delta[0], self._last_move_delta[1])
            else:
                self.say()  # a click (no drag) makes the pet talk
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:
        self.menu.popup(event.globalPos())

    def closeEvent(self, event) -> None:
        if self._timer.isActive():
            self._timer.stop()
        if self._chatter_timer.isActive():
            self._chatter_timer.stop()
        self._bubble.close()
        for kind, obj in self._sprites.values():
            if kind == "movie":
                obj.stop()
        super().closeEvent(event)
