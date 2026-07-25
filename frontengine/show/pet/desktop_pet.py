import json
import random as _random_module
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QRect, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QFontMetrics, QMovie, QPainter, QPixmap, QTransform
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import QMenu, QMessageBox, QWidget

from frontengine.show.base_widget import BaseWidget
from frontengine.show.window_helpers import apply_overlay_window_flags
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.audio_meter.audio_envelope import AudioEnvelope
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


# 可以請寵物幫忙開啟的網址協定 / URL schemes the pet will open for you
_WEB_SCHEMES = frozenset({"http", "https"})


# 拖進寵物的檔案分類 / What a file dropped onto the pet means
DROP_SPRITE = "sprite"  # 圖片或動作包 -> 換一套外觀
DROP_FOOD = "food"      # 其他檔案 -> 當成食物餵給寵物


def classify_drop(path) -> Optional[str]:
    """
    判斷拖到寵物身上的檔案要換裝還是當食物；路徑無效或空資料夾回傳 None。
    Classify a file dropped onto the pet: a sprite/pack to wear, food to eat,
    or None when the path is unusable.
    """
    try:
        target = Path(path)
        if not target.exists():
            return None
    except (OSError, TypeError, ValueError):
        return None
    if target.is_dir():
        return DROP_SPRITE if scan_pet_pack(str(target)) else None
    return DROP_SPRITE if target.suffix.lower() in _PACK_EXTS else DROP_FOOD


# 食物種類（依副檔名猜）與各自的效果 / Food kinds guessed from the suffix
FOOD_SNACK = "snack"    # 一般點心 / an ordinary snack
FOOD_FEAST = "feast"    # 壓縮檔＝大餐 / an archive is a hearty meal
FOOD_MUSIC = "music"    # 音樂檔＝聽了很開心 / music cheers it up more than it fills
FOOD_BOOK = "book"      # 文件檔＝細嚼慢嚥 / a document is chewed slowly
FOOD_HARD = "hard"      # 可執行檔＝咬不動 / a binary is too hard to chew

_FOOD_SUFFIXES = {
    FOOD_FEAST: (".zip", ".7z", ".rar", ".tar", ".gz", ".iso"),
    FOOD_MUSIC: (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"),
    FOOD_BOOK: (".txt", ".md", ".pdf", ".doc", ".docx", ".rtf", ".epub"),
    FOOD_HARD: (".exe", ".dll", ".msi", ".sys", ".bat"),
}

# 每種食物的飽足／心情／親密度變化（心情為負代表不喜歡）
# Fullness / mood / affection change per food kind (negative mood = dislikes it).
FOOD_EFFECTS = {
    FOOD_SNACK: {"fullness": 30, "mood": 12, "affection": 5},
    FOOD_FEAST: {"fullness": 45, "mood": 8, "affection": 6},
    FOOD_MUSIC: {"fullness": 15, "mood": 20, "affection": 5},
    FOOD_BOOK: {"fullness": 20, "mood": 6, "affection": 4},
    FOOD_HARD: {"fullness": 2, "mood": -6, "affection": 1},
}


def classify_food(path) -> str:
    """依副檔名判斷食物種類；認不出來就當一般點心 / Guess the food kind from the suffix."""
    try:
        suffix = Path(path).suffix.lower()
    except (OSError, TypeError, ValueError):
        return FOOD_SNACK
    for kind, suffixes in _FOOD_SUFFIXES.items():
        if suffix in suffixes:
            return kind
    return FOOD_SNACK


# 動作包設定檔：放在動作包資料夾裡，用來描述這隻寵物的個性與參數
# Pack manifest: sits inside a pet pack folder describing that pet's traits.
PACK_MANIFEST_NAME = "pet.json"
_MANIFEST_NUMBERS = ("size", "speed")
_MANIFEST_FLAGS = ("climb", "talk", "sit_on_windows")


def read_pet_manifest(folder) -> dict:
    """
    讀取動作包裡的 pet.json（可選）。只取認得的欄位，型別不符就略過，
    讀不到或格式錯誤一律回傳空 dict，讓動作包永遠不會弄壞寵物。

    Read a pack's optional pet.json. Only known, well-typed fields are kept and
    anything unreadable yields {}, so a pack can never break the pet.
    """
    manifest: dict = {}
    try:
        path = Path(folder) / PACK_MANIFEST_NAME
        if not path.is_file():
            return manifest
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError, TypeError):
        return manifest
    if not isinstance(raw, dict):
        return manifest
    for key in _MANIFEST_NUMBERS:
        try:
            if key in raw:
                manifest[key] = max(1, int(raw[key]))
        except (TypeError, ValueError):
            continue
    for key in _MANIFEST_FLAGS:
        if isinstance(raw.get(key), bool):
            manifest[key] = raw[key]
    if isinstance(raw.get("name"), str):
        manifest["name"] = raw["name"]
    if isinstance(raw.get("sound"), str):
        manifest["sound"] = raw["sound"]
    lines = raw.get("lines")
    if isinstance(lines, dict):
        manifest["lines"] = {
            str(pool): [str(line) for line in values if str(line).strip()]
            for pool, values in lines.items()
            if isinstance(values, list) and values
        }
    return manifest


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


# 列舉可站立視窗時要略過的外殼視窗類別
# Shell window classes skipped when enumerating standable windows.
_PLATFORM_SKIP_CLASSES = {"WorkerW", "Progman", "Shell_TrayWnd", "Button"}


def windows_platforms(exclude_hwnds=()) -> list:
    """
    回傳目前可見頂層視窗的上緣做為可站立平台 (left, right, top_y)。僅 Windows
    有效，其餘平台或發生錯誤時回傳空清單。
    Return the top edges of visible top-level windows as standable platforms
    (left, right, top_y). Windows only; returns [] elsewhere or on error.
    """
    if sys.platform != "win32":
        return []
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        exclude = {int(h) for h in exclude_hwnds}
        platforms: list = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def _collect(hwnd, _lparam):
            if int(hwnd) in exclude or not user32.IsWindowVisible(hwnd):
                return True
            rect = wintypes.RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return True
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            if width < 80 or height < 40:
                return True
            class_buffer = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, class_buffer, 64)
            if class_buffer.value in _PLATFORM_SKIP_CLASSES:
                return True
            platforms.append((rect.left, rect.right, rect.top))
            return True

        user32.EnumWindows(_collect, 0)
        return platforms
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.warning(f"[windows_platforms] error: {error!r}")
        return []


def idle_seconds():
    """
    回傳使用者未操作的秒數；無法取得時回傳 None。僅 Windows 實作。
    Seconds since the last user input, or None when unavailable (Windows only).
    """
    if sys.platform != "win32":
        return None
    try:
        import ctypes

        class _LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        info = _LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return None
        elapsed_ms = ctypes.windll.kernel32.GetTickCount() - info.dwTime
        return max(0.0, elapsed_ms / 1000.0)
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.warning(f"[idle_seconds] error: {error!r}")
        return None


class PetTimeline:
    """
    寵物動作時間軸：一連串 (offset_seconds, action_dict)，依經過秒數依序觸發。
    A scene-timeline of (offset_seconds, action_dict) events fired in order as
    elapsed time passes. Events are sorted; pop_due advances an internal index.
    """

    def __init__(self, events) -> None:
        self._events = sorted(list(events), key=lambda item: item[0])
        self._index = 0

    def __len__(self) -> int:
        return len(self._events)

    def reset(self) -> None:
        self._index = 0

    def pop_due(self, elapsed: float) -> list:
        due = []
        while self._index < len(self._events) and self._events[self._index][0] <= elapsed:
            due.append(self._events[self._index][1])
            self._index += 1
        return due


def parse_timeline(raw) -> list:
    """把設定裡的 [{'at': 秒, ...}] 轉成 (offset, action_dict) 清單，忽略格式錯誤者。"""
    events = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict) or "at" not in item:
                continue
            try:
                offset = float(item["at"])
            except (TypeError, ValueError):
                continue
            events.append((offset, item))
    return events


def pop_due_reminders(now, reminders):
    """
    依 now 分出已到期與未到期的提醒。reminders 為 (due_datetime, text) 清單。
    Split reminders into (due, remaining) at `now`. Each reminder is a
    (due_datetime, text) tuple.
    """
    due = [item for item in reminders if item[0] <= now]
    remaining = [item for item in reminders if item[0] > now]
    return due, remaining


def read_battery():
    """
    回傳 (電量百分比, 是否充電中)；無法取得時回傳 None。僅 Windows 實作。
    Return (percent, charging) or None when unavailable. Windows only.
    """
    if sys.platform != "win32":
        return None
    try:
        import ctypes

        class _SPS(ctypes.Structure):
            _fields_ = [
                ("ACLineStatus", ctypes.c_byte),
                ("BatteryFlag", ctypes.c_byte),
                ("BatteryLifePercent", ctypes.c_byte),
                ("SystemStatusFlag", ctypes.c_byte),
                ("BatteryLifeTime", ctypes.c_ulong),
                ("BatteryFullLifeTime", ctypes.c_ulong),
            ]

        status = _SPS()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            return None
        percent = status.BatteryLifePercent & 0xFF
        if percent == 255:  # unknown / no battery
            return None
        return (int(percent), status.ACLineStatus == 1)
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.warning(f"[read_battery] error: {error!r}")
        return None


def nearest_peer(center, peers):
    """
    回傳離 center 最近的同伴座標與距離；無同伴回傳 (None, inf)。
    Return the nearest peer center and its distance to `center`, or
    (None, inf) when there are no peers.
    """
    best = None
    best_distance = float("inf")
    cx, cy = center
    for peer_x, peer_y in peers:
        distance = ((peer_x - cx) ** 2 + (peer_y - cy) ** 2) ** 0.5
        if distance < best_distance:
            best_distance = distance
            best = (peer_x, peer_y)
    return best, best_distance


# 鬼抓人角色 / Roles in the tag game
TAG_CHASE = "chase"
TAG_FLEE = "flee"


class PetTagGame:
    """
    多隻寵物的鬼抓人：一隻當鬼追最近的同伴，其他往反方向逃；抓到就換人當鬼，
    並有短暫冷卻避免立刻抓回去。純邏輯、不依賴 Qt，由外部每一拍餵入座標。

    Tag between pets: one is "it" and chases its nearest peer while the others
    run the other way; catching someone passes "it" on, with a short cooldown so
    the tag cannot bounce straight back. Pure logic — positions are fed in each
    tick from outside.
    """

    CATCH_DISTANCE = 60.0
    FLEE_DISTANCE = 220.0
    COOLDOWN_TICKS = 20

    def __init__(self, catch_distance: float = CATCH_DISTANCE, flee_distance: float = FLEE_DISTANCE,
                 cooldown_ticks: int = COOLDOWN_TICKS) -> None:
        self.catch_distance = float(catch_distance)
        self.flee_distance = float(flee_distance)
        self.cooldown_ticks = max(0, int(cooldown_ticks))
        self.it = None
        self.just_tagged = None
        self._cooldown = 0

    def reset(self) -> None:
        """重置遊戲（參與者換人或停玩時呼叫）。"""
        self.it = None
        self.just_tagged = None
        self._cooldown = 0

    @staticmethod
    def _nearest(positions: dict, source):
        """回傳離 source 最近的其他參與者 (id, 距離)；只有一人時回傳 (None, inf)。"""
        source_x, source_y = positions[source]
        best, best_distance = None, float("inf")
        for participant, (x, y) in positions.items():
            if participant == source:
                continue
            distance = ((x - source_x) ** 2 + (y - source_y) ** 2) ** 0.5
            if distance < best_distance:
                best, best_distance = participant, distance
        return best, best_distance

    def update(self, positions: dict) -> dict:
        """
        餵入 {參與者: (x, y)}，回傳 {參與者: (角色, 目標 x)}。少於兩人時不開局。
        Feed in {participant: (x, y)} and get {participant: (role, target_x)}.
        """
        self.just_tagged = None
        if not positions or len(positions) < 2:
            self.reset()
            return {}
        if self.it not in positions:
            self.it = sorted(positions)[0]
            self._cooldown = self.cooldown_ticks
        # 冷卻期間只是跑給對方追，不換鬼；先判斷再遞減，冷卻 N 拍就真的保護 N 拍。
        # While cooling down nobody can be tagged; check before decrementing so a
        # cooldown of N protects exactly N updates.
        can_tag = self._cooldown <= 0
        if self._cooldown > 0:
            self._cooldown -= 1
        prey, distance = self._nearest(positions, self.it)
        if prey is not None and can_tag and distance <= self.catch_distance:
            self.it = prey
            self.just_tagged = prey
            self._cooldown = self.cooldown_ticks
            prey, _distance = self._nearest(positions, self.it)
        return self._roles(positions, prey)

    def _roles(self, positions: dict, prey) -> dict:
        """
        依目前的鬼與獵物組出每個人的 (角色, 目標 x, 目標 y)。逃跑方向取兩點連線的反向，
        讓地板模式（只用 x）與飄移／追游標模式（用整個點）都有合理目標。
        Build each participant's (role, target_x, target_y). Runners head along
        the line away from "it", which suits floor pets (x only) and wander or
        chase pets (the whole point) alike.
        """
        it_x, it_y = positions[self.it]
        prey_position = positions[prey] if prey is not None else (it_x, it_y)
        roles = {self.it: (TAG_CHASE, float(prey_position[0]), float(prey_position[1]))}
        for participant, (x, y) in positions.items():
            if participant == self.it:
                continue
            dx, dy = x - it_x, y - it_y
            length = (dx * dx + dy * dy) ** 0.5
            if length < 1e-9:  # standing on each other: just pick a direction
                dx, dy, length = 1.0, 0.0, 1.0
            roles[participant] = (
                TAG_FLEE,
                x + self.flee_distance * dx / length,
                y + self.flee_distance * dy / length,
            )
        return roles


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


class PetGrowth:
    """
    親密度累積與等級：互動會累加親密度，跨過門檻即升級。
    Affection points accrue from interactions; crossing a threshold levels up.
    """

    THRESHOLDS = (0, 100, 250, 500, 1000, 2000)

    def __init__(self, affection: int = 0) -> None:
        self.affection = self._clamp(affection)

    @staticmethod
    def _clamp(value) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    def level(self) -> int:
        return max(1, sum(1 for threshold in self.THRESHOLDS if self.affection >= threshold))

    def add(self, amount: int) -> bool:
        """累加親密度；若因此升級回傳 True。"""
        before = self.level()
        self.affection = self._clamp(self.affection + int(amount))
        return self.level() > before


def format_status(level: int, mood_level: str, hunger_level: str, labels: dict) -> str:
    """
    組出「等級 · 心情 · 飽足」狀態字串;labels 提供各狀態的顯示文字。
    Compose a "Lv.N · mood · hunger" status string using `labels`.
    """
    level_label = labels.get("level", "Lv.")
    mood_text = labels.get(mood_level, mood_level)
    hunger_text = labels.get(hunger_level, hunger_level)
    return f"{level_label}{level} · {mood_text} · {hunger_text}"


def audio_pulse_scale(level, base: float = 0.7, amplitude: float = 0.3) -> float:
    """把音訊音量 (0~1) 轉成脈動縮放比例 / Map an audio level (0..1) to a pulse scale."""
    try:
        clamped = max(0.0, min(1.0, float(level)))
    except (TypeError, ValueError):
        return 1.0
    return base + amplitude * clamped


def size_for_level(base_size: int, level: int) -> int:
    """依等級放大基礎尺寸（每級 +8%，上限 +50%）/ Grow base size by level (cap +50%)."""
    factor = min(1.5, 1.0 + 0.08 * max(0, int(level) - 1))
    return max(16, int(round(int(base_size) * factor)))


class PetHunger:
    """
    寵物飽足值 0~100：餵食上升、隨時間下降；level() 回傳 full/ok/hungry。
    Pet fullness 0..100: feeding raises it, time lowers it; level() buckets it.
    """

    FULL = "full"
    OK = "ok"
    HUNGRY = "hungry"

    def __init__(self, value: int = 70) -> None:
        self.value = self._clamp(value)

    @staticmethod
    def _clamp(value) -> int:
        try:
            return max(0, min(100, int(value)))
        except (TypeError, ValueError):
            return 70

    def feed(self, amount: int = 30) -> None:
        self.value = self._clamp(self.value + amount)

    def decay(self, amount: int = 1) -> None:
        self.value = self._clamp(self.value - amount)

    def level(self) -> str:
        if self.value >= 60:
            return self.FULL
        if self.value <= 25:
            return self.HUNGRY
        return self.OK


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
        # 可站立的視窗平台 (left, right, top_y)；站在平台上時的狀態
        # Standable window platforms (left, right, top_y) and platform state.
        self.platforms: list = []
        self.on_platform = False
        self.platform_span: Optional[Tuple[float, float]] = None
        self.ground_feet = 0.0
        # 追向某個 x（用於朝同伴走過去玩耍）/ Horizontal target to walk toward (play).
        self.follow_target_x: Optional[float] = None
        # 引導目標 (x, y)：三種行為模式都會朝它移動（鬼抓人用），優先於各自的預設動線。
        # Guidance point (x, y) honoured by every behaviour (used by the tag
        # game); it takes precedence over each mode's own default movement.
        self.guidance: Optional[Tuple[float, float]] = None

    @property
    def facing_left(self) -> bool:
        return self.vx < 0

    def set_bounds(self, bounds: Tuple[int, int, int, int]) -> None:
        self.bounds = bounds

    def set_platforms(self, platforms) -> None:
        """設定可站立的視窗上緣平台 / Set standable window top-edge platforms."""
        self.platforms = list(platforms)

    def grab_nearest_wall(self, threshold: float = 40.0) -> bool:
        """
        若目前貼近左/右螢幕邊緣，就抓住該牆開始往上爬；成功回傳 True。
        If close to the left/right screen edge, grab that wall and start
        climbing it. Returns True when a wall was grabbed.
        """
        if not self.climb:
            return False
        left, _top, right, _bottom = self.bounds
        if self.x <= left + threshold:
            self.x = float(left)
            surface = SURFACE_LEFT
        elif self.x + self.width >= right - threshold:
            self.x = float(right - self.width)
            surface = SURFACE_RIGHT
        else:
            return False
        self.surface = surface
        self.vy = float(-self.speed)
        self._airborne = False
        self.on_platform = False
        self.platform_span = None
        self.follow_target_x = None
        return True

    def set_follow(self, target_x) -> None:
        """設定要走向的 x 座標（朝同伴玩耍）/ Set a horizontal target to walk toward."""
        self.follow_target_x = float(target_x)

    def clear_follow(self) -> None:
        self.follow_target_x = None

    def set_target(self, x: float, y: float) -> None:
        self.target = (float(x), float(y))

    def set_guidance(self, x: float, y: Optional[float] = None) -> None:
        """
        設定引導目標；地板模式走向該 x，飄移／追游標模式則朝該點移動。
        Set the guidance point: floor pets walk toward its x, wander and chase
        pets steer toward the point itself.
        """
        centre_y = self.y + self.height / 2.0
        self.guidance = (float(x), centre_y if y is None else float(y))
        if self.behaviour == BEHAVIOUR_FLOOR:
            self.follow_target_x = self.guidance[0]

    def clear_guidance(self) -> None:
        """取消引導，回到該模式原本的動線 / Drop the guidance and resume normal movement."""
        self.guidance = None
        self.follow_target_x = None

    STEER_BLEND = 0.4

    def _steer_toward(self, point: Tuple[float, float]) -> None:
        """把速度往目標點轉一些（保持速率），轉彎自然而不是瞬間轉向。"""
        target_x, target_y = point
        dx = target_x - (self.x + self.width / 2.0)
        dy = target_y - (self.y + self.height / 2.0)
        distance = (dx * dx + dy * dy) ** 0.5
        if distance < 1e-9:
            return
        desired_x = self.speed * dx / distance
        desired_y = self.speed * dy / distance
        blended_x = self.vx + self.STEER_BLEND * (desired_x - self.vx)
        blended_y = self.vy + self.STEER_BLEND * (desired_y - self.vy)
        magnitude = (blended_x * blended_x + blended_y * blended_y) ** 0.5
        if magnitude < 1e-9:
            self.vx, self.vy = desired_x, desired_y
            return
        self.vx = self.speed * blended_x / magnitude
        self.vy = self.speed * blended_y / magnitude

    def throw(self, vx: float, vy: float) -> None:
        """拖曳放開後以動量丟出（只在重力模式有意義）。"""
        self.vx = float(vx)
        self.vy = float(vy)
        self._airborne = True
        self.asleep = False
        self.surface = SURFACE_FLOOR
        self.on_platform = False
        self.platform_span = None
        self.follow_target_x = None

    def step(self) -> Tuple[int, int]:
        left, top, right, bottom = self.bounds
        floor_y = bottom - self.height
        if self.behaviour == BEHAVIOUR_CHASE:
            return self._step_chase(left, top, right, bottom)
        if self.behaviour == BEHAVIOUR_WANDER:
            return self._step_wander(left, top, right, bottom)
        return self._step_floor(left, top, right, bottom, floor_y)

    # --- floor / gravity / climbing / window platforms ---
    def _step_floor(self, left, top, right, bottom, floor_y) -> Tuple[int, int]:
        airborne = self._airborne or (
            not self.on_platform and self.surface == SURFACE_FLOOR and self.y < floor_y - 0.5
        )
        if airborne:
            return self._step_fall(left, top, right, bottom, floor_y)
        if self.follow_target_x is not None:
            return self._step_follow(left, top, right, bottom, floor_y)
        if self.on_platform:
            return self._step_platform(left, top, right, bottom, floor_y)
        if self.surface != SURFACE_FLOOR:
            return self._step_climb(left, top, right, bottom, floor_y)

        # grounded on the screen floor: random walk / idle, with a chance to climb a wall
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

    def _step_fall(self, left, top, right, bottom, floor_y) -> Tuple[int, int]:
        """落下：撞牆/天花板反彈，並在越過視窗平台或螢幕地板時落地。"""
        prev_feet = self.y + self.height
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
        new_feet = self.y + self.height
        center_x = self.x + self.width / 2.0

        land_feet = None
        land_span = None
        for platform_left, platform_right, platform_y in self.platforms:
            if platform_left <= center_x <= platform_right and prev_feet <= platform_y <= new_feet:
                if land_feet is None or platform_y < land_feet:
                    land_feet = float(platform_y)
                    land_span = (float(platform_left), float(platform_right))
        if prev_feet <= bottom <= new_feet and (land_feet is None or bottom < land_feet):
            land_feet = float(bottom)
            land_span = None

        if land_feet is not None:
            self.y = float(land_feet - self.height)
            if abs(self.vy) > self.BOUNCE_THRESHOLD:
                self.vy = -self.vy * self.BOUNCE_DAMPING
            else:
                self.vy = 0.0
                self._airborne = False
                self.surface = SURFACE_FLOOR
                self.on_platform = land_span is not None
                self.platform_span = land_span
                self.ground_feet = land_feet
                self.vx = float(self.speed) if self.vx >= 0 else float(-self.speed)
                self._new_state(force_walk=True)
        return int(self.x), int(self.y)

    def _step_follow(self, left, top, right, bottom, floor_y) -> Tuple[int, int]:
        """朝 follow_target_x 走過去；抵達附近即清除並恢復隨機行為。"""
        center_x = self.x + self.width / 2.0
        if abs(center_x - self.follow_target_x) <= self.speed + 2.0:
            self.follow_target_x = None
            self._new_state()
            return int(self.x), int(self.y)
        self.state = "walk"
        self.vx = float(self.speed) if self.follow_target_x >= center_x else float(-self.speed)
        self.x += self.vx
        if self.on_platform and self.platform_span is not None:
            span_left, span_right = self.platform_span
            self.x = min(max(self.x, span_left), span_right - self.width)
            self.y = float(self.ground_feet - self.height)
        else:
            self.x = min(max(self.x, float(left)), float(right - self.width))
            self.y = float(floor_y)
        return int(self.x), int(self.y)

    def _platform_under(self) -> Optional[Tuple[float, float]]:
        """回傳目前站立平台的水平範圍；平台已消失（視窗移走/關閉）則回傳 None。"""
        body_left = self.x
        body_right = self.x + self.width
        for platform_left, platform_right, platform_y in self.platforms:
            if abs(platform_y - self.ground_feet) <= 2.0 and not (platform_right < body_left or platform_left > body_right):
                return (float(platform_left), float(platform_right))
        return None

    def _step_platform(self, left, top, right, bottom, floor_y) -> Tuple[int, int]:
        """站在視窗平台上走動；到平台兩端轉向；平台消失則掉落。"""
        span = self._platform_under()
        if span is None:
            self._airborne = True
            self.on_platform = False
            self.platform_span = None
            return self._step_fall(left, top, right, bottom, floor_y)
        self.platform_span = span
        span_left, span_right = span
        self.y = float(self.ground_feet - self.height)
        if self._state_ticks <= 0:
            self._new_state()
        self._state_ticks -= 1
        if self.state != "walk":
            return int(self.x), int(self.y)
        self.x += self.vx
        if self.x <= span_left:
            self.x = float(span_left)
            self.vx = abs(self.vx)
        elif self.x + self.width >= span_right:
            self.x = float(span_right - self.width)
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

    def sleep(self) -> None:
        """讓寵物進入睡眠（使用者閒置時呼叫）/ Put the pet to sleep."""
        self.state = STATE_SLEEP
        self._state_ticks = self._rng.randint(300, 600)
        self.follow_target_x = None

    # --- free wander ---
    def _step_wander(self, left, top, right, bottom) -> Tuple[int, int]:
        if abs(self.vy) < 1e-9:
            self.vy = float(self.speed)
        if self.guidance is not None:
            self._steer_toward(self.guidance)
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
        # 被引導時（鬼抓人）以引導目標為準，而不是游標
        # While guided (tag game) the guidance point wins over the cursor.
        chase_target = self.guidance if self.guidance is not None else self.target
        if chase_target is None:
            return int(self.x), int(self.y)
        target_x, target_y = chase_target
        dx = target_x - (self.x + self.width / 2)
        dy = target_y - (self.y + self.height / 2)
        distance = (dx * dx + dy * dy) ** 0.5
        if distance <= self.CHASE_STOP_DISTANCE:
            # 追到游標會睡著；玩鬼抓人時只是站在對方身上，不睡。
            # Catching the cursor means a nap; catching a playmate does not.
            self.asleep = self.guidance is None
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
                 behaviour: str = BEHAVIOUR_FLOOR, climb: bool = True, talk: bool = True,
                 sound_path: Optional[str] = None, sit_on_windows: bool = True,
                 volume: float = 1.0, audio_react: bool = False):
        front_engine_logger.info(
            f"[DesktopPetWidget] Init | path={image_path}, size={size}, speed={speed}, "
            f"behaviour={behaviour}, climb={climb}, talk={talk}, sound={sound_path}, "
            f"sit_on_windows={sit_on_windows}"
        )
        super().__init__()
        self.opacity = 1.0
        # 基礎尺寸依已存等級放大 / Base size grown by the persisted level.
        self._base_size: int = max(16, int(size))
        self._growth = PetGrowth(user_setting_dict.get("pet_affection", 0))
        self.pet_size: int = size_for_level(self._base_size, self._growth.level())
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
        self.setAcceptDrops(True)  # drop an image to dress it up, anything else to feed it
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
        self._hunger = PetHunger(user_setting_dict.get("pet_hunger", 70))
        self._hunger_warned = False
        self._messages = self._load_messages()
        # 動作包自帶的設定（可含台詞、速度、體型、音效）
        # Traits shipped inside the pack (lines, speed, size, sound).
        self.manifest = read_pet_manifest(self.image_path) if self.image_path.is_dir() else {}
        self._apply_manifest()
        self._volume = max(0.0, min(1.0, float(volume)))
        self._sound: Optional[QSoundEffect] = None
        self._init_sound(self.manifest.get("sound_path", sound_path))
        # 語音朗讀（可選，缺少 QtTextToSpeech 時自動停用）
        # Optional spoken lines; disabled automatically without QtTextToSpeech.
        self._speech = None
        self._speak = False
        # AI 對話（可選，需環境變數金鑰；預設關閉）
        # Optional AI chat; needs an env-var key and is off by default.
        self._chat_service = None
        self._pending_chat_reply: Optional[str] = None
        self._sit_on_windows = bool(sit_on_windows)
        self._platform_tick = 0
        # 音訊視覺化：依可注入的音量 provider 脈動 / Audio-reactive pulse
        self._audio_react = bool(audio_react)
        self._audio_level_provider = None  # callable -> level 0..1 or None
        self._audio_scale = 1.0
        # 峰值抖動大，先過 RMS + 快起慢降包絡再驅動脈動
        # Raw peaks jitter, so smooth them through an RMS + attack/decay envelope.
        self._audio_envelope = AudioEnvelope()
        # 多寵物互動 / Multi-pet interaction
        self._peers_provider = None
        self._peer_greeted = False
        self._peer_tick = 0
        # 鬼抓人角色（由外部的 PetTagGame 指派）/ Tag role assigned by a PetTagGame
        self._tag_role = None
        # 電量提醒 / Low-battery reaction
        self._battery_provider = read_battery
        self._battery_warned = False
        # 閒置反應 / Idle reaction
        self._idle_provider = idle_seconds
        self._idle_reacted = False
        # 提醒事項 / Reminders
        self._now_provider = datetime.now
        self._reminders: list = []
        self._reminder_timer = QTimer(self)
        self._reminder_timer.timeout.connect(self._on_schedule_tick)
        # 場景時間軸 / Scene timeline of scheduled actions
        self._timeline = PetTimeline(parse_timeline(user_setting_dict.get("pet_timeline", [])))
        self._timeline_start = None
        self._bubble = SpeechBubble()
        self._chatter_timer = QTimer(self)
        self._chatter_timer.setSingleShot(True)
        self._chatter_timer.timeout.connect(self._on_chatter)

        self.menu = QMenu(self)
        self.clone_action = QAction(language_wrapper.language_word_dict.get("pet_clone", "Clone"), self)
        self.clone_action.triggered.connect(self.clone_requested.emit)
        self.menu.addAction(self.clone_action)
        self.feed_action = QAction(language_wrapper.language_word_dict.get("pet_feed", "Feed"), self)
        self.feed_action.triggered.connect(self.feed)
        self.menu.addAction(self.feed_action)
        self.status_action = QAction(language_wrapper.language_word_dict.get("pet_status", "Status"), self)
        self.status_action.triggered.connect(self.show_status)
        self.menu.addAction(self.status_action)
        self.reminder_action = QAction(
            language_wrapper.language_word_dict.get("pet_set_reminder", "Set reminder..."), self)
        self.reminder_action.triggered.connect(self._prompt_reminder)
        self.menu.addAction(self.reminder_action)
        self.chat_action = QAction(
            language_wrapper.language_word_dict.get("pet_chat_menu", "Talk to me..."), self)
        self.chat_action.triggered.connect(self._prompt_chat)
        self.chat_action.setVisible(False)  # shown only when a chat service is attached
        self.menu.addAction(self.chat_action)
        self.close_action = QAction(language_wrapper.language_word_dict.get("control_center_close_all", "Close"), self)
        self.close_action.triggered.connect(self.close)
        self.menu.addAction(self.close_action)

    MEET_DISTANCE = 90.0
    PLAY_RANGE = 320.0
    PLAY_CHANCE = 0.25

    def set_pet_window_flag(self) -> None:
        """寵物需接收滑鼠以便拖曳，故 allow_input=True 並置頂，也不參與全域鎖定。"""
        apply_overlay_window_flags(self, show_on_bottom=False, allow_input=True)
        self.overlay_lockable = False

    def center(self) -> Tuple[int, int]:
        return (self.x() + self.width() // 2, self.y() + self.height() // 2)

    def set_peers_provider(self, provider) -> None:
        """設定回傳其他寵物中心座標清單的函式 / Provider of other pets' centres."""
        self._peers_provider = provider

    def apply_tag_role(self, role) -> None:
        """
        套用鬼抓人角色 (角色, 目標 x, 目標 y)；None 代表沒在玩，恢復平常的同伴互動。
        Apply a tag role; None means the game is off and normal peer play resumes.
        """
        if role is None:
            if self._tag_role is not None:
                self._tag_role = None
                self.motion.clear_guidance()
            return
        self._tag_role, target_x, target_y = role
        self.motion.wake()
        self.motion.set_guidance(target_x, target_y)

    def on_tagged(self) -> None:
        """換自己當鬼時喊一句 / Shout when the tag lands on this pet."""
        self._gain_affection(1)
        pool = self._messages.get("tag") or []
        if pool:
            self.say(pool[self._chatter_rng.randrange(len(pool))])

    def _check_peers(self) -> None:
        """靠近其他寵物時走過去玩耍、抵達後轉向打招呼（帶遲滯，避免重複）。"""
        if self._tag_role is not None:
            return  # the tag game owns where this pet is heading
        if self._peers_provider is None:
            return
        try:
            peers = self._peers_provider()
        except Exception:  # pragma: no cover - defensive
            return
        my_center = self.center()
        peer, distance = nearest_peer(my_center, peers)
        if peer is None:
            self._peer_greeted = False
            self.motion.clear_follow()
            return
        # play: a floor pet may walk over to a near-ish peer
        if self.motion.behaviour == BEHAVIOUR_FLOOR:
            if self.MEET_DISTANCE < distance <= self.PLAY_RANGE:
                if self.motion.follow_target_x is not None or self._chatter_rng.random() < self.PLAY_CHANCE:
                    self.motion.set_follow(peer[0])
            elif distance > self.PLAY_RANGE:
                self.motion.clear_follow()
        # greet: face and say a meet line once per approach
        if distance <= self.MEET_DISTANCE:
            self.motion.clear_follow()
            if self._talk and not self._peer_greeted:
                self._peer_greeted = True
                self._gain_affection(3)
                self.motion.vx = abs(self.motion.vx) if peer[0] >= my_center[0] else -abs(self.motion.vx)
                pool = self._messages.get("meet") or []
                if pool:
                    self.say(pool[self._chatter_rng.randrange(len(pool))])
        elif distance > self.MEET_DISTANCE * 1.6:
            self._peer_greeted = False

    def _load_sprite(self, path: str):
        """載入一張精靈；檔案損毀或格式不支援時回傳 None。"""
        if Path(path).suffix.lower() in (".gif", ".webp"):
            movie = QMovie(str(path))
            if not movie.isValid():
                return None
            movie.frameChanged.connect(self.update)
            return ("movie", movie)
        pixmap = QPixmap(str(path))
        return None if pixmap.isNull() else ("pixmap", pixmap)

    def _load_sprites(self, image_path: Path) -> None:
        """單一檔 -> 所有狀態共用；資料夾 -> 依檔名對應各狀態；載不起來的略過。"""
        if image_path.is_dir():
            for state, path in scan_pet_pack(str(image_path)).items():
                sprite = self._load_sprite(path)
                if sprite is not None:
                    self._sprites[state] = sprite
        elif image_path.is_file():
            sprite = self._load_sprite(str(image_path))
            if sprite is not None:
                self._sprites["default"] = sprite

    def change_sprite(self, path) -> None:
        """換一套外觀（拖圖片或動作包到寵物身上時觸發）；載不到就維持原樣。"""
        image_path = Path(path)
        previous = self._sprites
        self._sprites = {}
        self._load_sprites(image_path)
        if not self._sprites:
            front_engine_logger.warning(f"[DesktopPetWidget] change_sprite ignored: {image_path}")
            self._sprites = previous
            return
        front_engine_logger.info(f"[DesktopPetWidget] change_sprite | path={image_path}")
        for kind, obj in previous.values():
            if kind == "movie":
                obj.stop()
        self.image_path = image_path
        self._active = None
        self._active_state = None
        self._set_active_sprite(self._visual_state())
        self._gain_affection(2)
        pool = self._messages.get("costume") or []
        if pool:
            self.say(pool[self._chatter_rng.randrange(len(pool))])

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

    def set_audio_level_provider(self, provider) -> None:
        """設定回傳目前音量 (0~1 或 None) 的函式 / Provider of the current audio level."""
        self._audio_level_provider = provider
        self._audio_envelope.reset()

    def _update_audio_scale(self) -> None:
        """取一次音量取樣，經包絡平滑後換算成脈動比例（無音源則不脈動）。"""
        if not self._audio_react or self._audio_level_provider is None:
            self._audio_scale = 1.0
            self._audio_envelope.reset()
            return
        try:
            level = self._audio_level_provider()
        except Exception:  # pragma: no cover - defensive
            level = None
        if level is None:
            self._audio_scale = 1.0
            self._audio_envelope.reset()
            return
        self._audio_scale = audio_pulse_scale(self._audio_envelope.push(level))

    def draw_content(self, painter: QPainter) -> None:
        pixmap = self._current_pixmap()
        if pixmap is None or pixmap.isNull():
            return
        if self.motion.facing_left:
            pixmap = pixmap.transformed(QTransform().scale(-1, 1))
        scale = self._audio_scale if self._audio_react else 1.0
        if scale >= 0.999:
            painter.drawPixmap(QRect(0, 0, self.width(), self.height()), pixmap)
        else:
            # Anchor to the bottom so the feet stay on the ground while it pulses.
            width = int(self.width() * scale)
            height = int(self.height() * scale)
            painter.drawPixmap(
                QRect((self.width() - width) // 2, self.height() - height, width, height), pixmap)

    def start_moving(self, bounds: Tuple[int, int, int, int], interval_ms: int = 33) -> None:
        front_engine_logger.info(f"[DesktopPetWidget] start_moving | bounds={bounds}")
        left, top, right, bottom = bounds
        self.motion.set_bounds(bounds)
        self.motion.x = float(left)
        self.motion.y = float(bottom - self.pet_size)
        self.move(int(self.motion.x), int(self.motion.y))
        self._timer.start(max(10, int(interval_ms)))
        self._schedule_chatter()
        self._reminder_timer.start(10000)
        if self._timeline_start is None:
            self._timeline_start = self._now_provider()

    def _apply_manifest(self) -> None:
        """套用動作包設定：台詞併入句庫，速度／體型／音效覆寫預設值。"""
        if not self.manifest:
            return
        front_engine_logger.info(f"[DesktopPetWidget] pack manifest | {self.manifest}")
        for pool, lines in (self.manifest.get("lines") or {}).items():
            self._messages[pool] = list(lines)
        if "speed" in self.manifest:
            self.motion.speed = max(1, int(self.manifest["speed"]))
        if "size" in self.manifest:
            self._base_size = max(16, int(self.manifest["size"]))
            self._apply_growth_size()
        if "climb" in self.manifest:
            self.motion.climb = bool(self.manifest["climb"])
        if "talk" in self.manifest:
            self._talk = bool(self.manifest["talk"])
        sound = self.manifest.get("sound")
        if sound:
            candidate = self.image_path / sound
            if candidate.is_file():
                self.manifest["sound_path"] = str(candidate)

    def set_speech_enabled(self, enabled: bool) -> bool:
        """
        開關語音朗讀；系統缺少 QtTextToSpeech 時回傳 False 並維持關閉。
        Toggle spoken lines, returning False when QtTextToSpeech is unavailable.
        """
        if not enabled:
            self._speak = False
            return False
        if self._speech is None:
            try:
                from PySide6.QtTextToSpeech import QTextToSpeech

                self._speech = QTextToSpeech(self)
            except Exception as error:  # pragma: no cover - optional Qt module
                front_engine_logger.warning(f"[DesktopPetWidget] speech unavailable: {error!r}")
                self._speech = None
                self._speak = False
                return False
        self._speak = True
        return True

    def _speak_text(self, text: str) -> None:
        """把台詞念出來（未啟用或失敗時安靜略過）。"""
        if not self._speak or self._speech is None or not text:
            return
        try:
            self._speech.say(text)
        except Exception as error:  # pragma: no cover - speech backend guard
            front_engine_logger.warning(f"[DesktopPetWidget] speech failed: {error!r}")

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
            "meet": lines("pet_chatter_meet", "Hi friend!|Hello!|Let's play!"),
            "battery": lines("pet_chatter_battery", "Battery's low - plug me in?|Low power!|Find a charger?"),
            "hungry": lines("pet_chatter_hungry", "I'm hungry...|Got a snack?|Feed me?"),
            "fed": lines("pet_chatter_fed", "Yum!|Thank you!|Delicious!"),
            "fed_feast": lines("pet_chatter_fed_feast", "What a feast!|So full!|That was huge!"),
            "fed_music": lines("pet_chatter_fed_music", "Tasty tune!|That one sings!|Encore!"),
            "fed_book": lines("pet_chatter_fed_book", "Food for thought.|Chewy words!|Mmm, a story."),
            "fed_hard": lines("pet_chatter_fed_hard", "Too hard to chew!|Ouch, my teeth!|Not food!"),
            "away": lines("pet_chatter_away", "Still there?|I'll nap till you're back~|Zzz..."),
            "levelup": lines("pet_chatter_levelup", "Level up!|I'm growing!|We're getting closer!"),
            "costume": lines("pet_chatter_costume", "New look!|How do I look?|Nice fit!"),
            "fetch": lines("pet_chatter_fetch", "Fetch!|On it!|Opening that for you!"),
            "focus_start": lines("pet_chatter_focus_start", "Focus time!|Let's concentrate!|I'll wait here."),
            "focus_break": lines("pet_chatter_focus_break", "Break time!|Stretch a little!|Rest your eyes."),
            "focus_back": lines("pet_chatter_focus_back", "Back to it!|Round two!|Let's keep going."),
            "focus_done": lines("pet_chatter_focus_done", "Long break earned!|Great run!|Take a proper rest."),
            "tag": lines("pet_chatter_tag", "You're it!|Caught you!|My turn to chase!"),
            "any": lines("pet_chatter_any", "Hi there!|(^_^)|Keep going!"),
        }

    def _gain_affection(self, amount: int) -> None:
        """互動累加親密度；升級時長大、慶祝一下並保存。"""
        leveled = self._growth.add(amount)
        user_setting_dict["pet_affection"] = self._growth.affection
        if leveled:
            self._apply_growth_size()
            if self._talk:
                pool = self._messages.get("levelup") or []
                if pool:
                    self.say(pool[self._chatter_rng.randrange(len(pool))])

    def show_status(self) -> None:
        """顯示等級 · 心情 · 飽足 / Show level · mood · fullness."""
        get = language_wrapper.language_word_dict.get
        labels = {
            "level": get("pet_status_level", "Lv."),
            PetMood.HAPPY: get("pet_mood_happy", "happy"),
            PetMood.CONTENT: get("pet_mood_content", "content"),
            PetMood.SAD: get("pet_mood_sad", "sad"),
            PetHunger.FULL: get("pet_hunger_full", "full"),
            PetHunger.OK: get("pet_hunger_ok", "ok"),
            PetHunger.HUNGRY: get("pet_hunger_hungry", "hungry"),
        }
        text = format_status(self._growth.level(), self._mood.level(), self._hunger.level(), labels)
        self._bubble.show_message(text, self, duration_ms=8000)

    def _apply_growth_size(self) -> None:
        """依目前等級調整體型（motion 下一步會自動重新落地）。"""
        new_size = size_for_level(self._base_size, self._growth.level())
        if new_size == self.pet_size:
            return
        self.pet_size = new_size
        self.resize(new_size, new_size)
        self.motion.width = new_size
        self.motion.height = new_size

    def _persist_mood(self) -> None:
        user_setting_dict["pet_mood"] = self._mood.value

    def add_reminder(self, text: str, minutes: int) -> None:
        """在 minutes 分鐘後提醒 text / Remind `text` in `minutes` minutes."""
        due = self._now_provider() + timedelta(minutes=max(1, int(minutes)))
        self._reminders.append((due, str(text)))
        front_engine_logger.info(f"[DesktopPetWidget] reminder set | due={due}, text={text}")

    def _on_schedule_tick(self) -> None:
        self._check_reminders()
        self._check_timeline()

    def set_timeline(self, raw) -> None:
        """設定場景時間軸並從現在起算 / Set the timeline and start its clock now."""
        self._timeline = PetTimeline(parse_timeline(raw))
        self._timeline_start = self._now_provider()

    def _check_timeline(self) -> None:
        if self._timeline is None or self._timeline_start is None or len(self._timeline) == 0:
            return
        elapsed = (self._now_provider() - self._timeline_start).total_seconds()
        for action in self._timeline.pop_due(elapsed):
            self._run_timeline_action(action)

    def _run_timeline_action(self, action) -> None:
        if not isinstance(action, dict):
            return
        if action.get("say"):
            self.say(str(action["say"]))
        if action.get("sleep"):
            self.motion.sleep()
        if action.get("wake"):
            self.motion.wake()
        if action.get("feed"):
            self.feed()
        if action.get("status"):
            self.show_status()
        behaviour = action.get("behaviour")
        if behaviour in (BEHAVIOUR_FLOOR, BEHAVIOUR_WANDER, BEHAVIOUR_CHASE):
            self.motion.behaviour = behaviour

    def _check_reminders(self) -> None:
        if not self._reminders:
            return
        due, remaining = pop_due_reminders(self._now_provider(), self._reminders)
        self._reminders = remaining
        if due:
            # Reminders are explicit user requests: deliver even if chatter is off.
            self._bubble.show_message(due[-1][1], self, duration_ms=12000)
            self._play_sound()

    def _prompt_reminder(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        title = language_wrapper.language_word_dict.get("pet_set_reminder", "Set reminder...")
        text, ok = QInputDialog.getText(
            self, title, language_wrapper.language_word_dict.get("pet_reminder_prompt", "Remind me to:"))
        if not ok or not text.strip():
            return
        minutes, ok_minutes = QInputDialog.getInt(
            self, title, language_wrapper.language_word_dict.get("pet_reminder_minutes", "In how many minutes?"),
            5, 1, 1440)
        if not ok_minutes:
            return
        self.add_reminder(text.strip(), minutes)

    # --- optional AI chat --------------------------------------------------
    def set_chat_service(self, service) -> None:
        """
        接上 AI 對話服務（None 表示關閉）；服務不可用時右鍵選單不會出現該項目。
        Attach the AI chat service (None disables it); the menu entry only
        appears when the service is actually usable.
        """
        self._chat_service = service
        usable = service is not None and bool(getattr(service, "available", lambda: False)())
        self.chat_action.setVisible(usable)

    def _prompt_chat(self) -> None:
        """問使用者要說什麼，然後在背景等回覆（不卡 UI）。"""
        from PySide6.QtWidgets import QInputDialog

        if self._chat_service is None:
            return
        title = language_wrapper.language_word_dict.get("pet_chat_menu", "Talk to me...")
        text, ok = QInputDialog.getText(
            self, title, language_wrapper.language_word_dict.get("pet_chat_prompt", "Say something:"))
        if not ok or not text.strip():
            return
        self.ask_chat(text.strip())

    def ask_chat(self, message: str) -> None:
        """送出一句話並在收到回覆時說出來；失敗則說一句抱歉。"""
        if self._chat_service is None:
            return
        self.say(language_wrapper.language_word_dict.get("pet_chat_thinking", "Hmm, let me think..."))
        self._chat_service.ask_async(message, self.handle_chat_reply)

    def handle_chat_reply(self, reply: Optional[str]) -> None:
        """處理回覆（可能來自背景執行緒）；空回覆時說一句抱歉。"""
        if reply:
            self._pending_chat_reply = reply
        else:
            self._pending_chat_reply = language_wrapper.language_word_dict.get(
                "pet_chat_failed", "I couldn't reach my thoughts just now.")
        # 回覆可能在背景執行緒抵達，透過計時器回到 UI 執行緒再顯示
        # The reply may arrive off-thread; hop back to the UI thread to show it.
        QTimer.singleShot(0, self._say_pending_chat_reply)

    def _say_pending_chat_reply(self) -> None:
        if self._pending_chat_reply:
            self.say(self._pending_chat_reply)
            self._pending_chat_reply = None

    def _init_sound(self, sound_path: Optional[str]) -> None:
        if not sound_path:
            return
        path = Path(sound_path)
        if not (path.exists() and path.is_file()):
            return
        try:
            self._sound = QSoundEffect(self)
            self._sound.setSource(QUrl.fromLocalFile(str(path)))
            self._sound.setVolume(self._volume)
        except Exception as error:  # pragma: no cover - audio backend guard
            front_engine_logger.warning(f"[DesktopPetWidget] sound load failed: {error!r}")
            self._sound = None

    def _play_sound(self) -> None:
        if self._sound is None:
            return
        try:
            self._sound.play()
        except Exception as error:  # pragma: no cover - audio backend guard
            front_engine_logger.warning(f"[DesktopPetWidget] sound play failed: {error!r}")

    def _schedule_chatter(self) -> None:
        if self._talk:
            self._chatter_timer.start(self._chatter_rng.randint(15000, 35000))

    def _on_chatter(self) -> None:
        self._mood.decay()  # a little neglect over time
        self._hunger.decay()
        self._persist_mood()
        # priority: user idle (nap), low battery, hunger, otherwise normal chatter
        if not self._check_idle() and not self._warn_battery() and not self._warn_hungry():
            self.say()
        self._schedule_chatter()

    IDLE_THRESHOLD = 120.0

    def _check_idle(self) -> bool:
        """使用者閒置久了打盹並說一句；回來後醒。回傳是否有反應（抑制一般閒聊）。"""
        seconds = self._idle_provider()
        if seconds is None:
            return False
        if seconds >= self.IDLE_THRESHOLD:
            if not self._idle_reacted:
                self._idle_reacted = True
                self.motion.sleep()
                if self._talk:
                    pool = self._messages.get("away") or []
                    if pool:
                        self.say(pool[self._chatter_rng.randrange(len(pool))])
                        return True
            return False
        if seconds < 5.0 and self._idle_reacted:
            self._idle_reacted = False
            self.motion.wake()
        return False

    def _persist_hunger(self) -> None:
        user_setting_dict["pet_hunger"] = self._hunger.value

    def feed(self, kind: str = FOOD_SNACK) -> None:
        """餵食：依食物種類調整飽足與心情，並說一句對應的話。"""
        effect = FOOD_EFFECTS.get(kind, FOOD_EFFECTS[FOOD_SNACK])
        self._hunger.feed(effect["fullness"])
        mood_change = effect["mood"]
        if mood_change >= 0:
            self._mood.pet(mood_change)
        else:
            self._mood.decay(-mood_change)
        self._persist_hunger()
        self._persist_mood()
        self._gain_affection(effect["affection"])
        pool = self._messages.get(f"fed_{kind}") or self._messages.get("fed") or []
        if pool:
            self.say(pool[self._chatter_rng.randrange(len(pool))])

    def _warn_hungry(self) -> bool:
        """飢餓時討食一次；吃飽後重置。回傳是否有討食。"""
        self._persist_hunger()
        if not self._talk:
            return False
        if self._hunger.level() == PetHunger.HUNGRY:
            if not self._hunger_warned:
                self._hunger_warned = True
                pool = self._messages.get("hungry") or []
                if pool:
                    self.say(pool[self._chatter_rng.randrange(len(pool))])
                    return True
        elif self._hunger.level() == PetHunger.FULL:
            self._hunger_warned = False
        return False

    BATTERY_THRESHOLD = 20

    def _warn_battery(self) -> bool:
        """低電量時提醒一次；充電或回升後重置。回傳是否有發出提醒。"""
        if not self._talk:
            return False
        status = self._battery_provider()
        if status is None:
            return False
        percent, charging = status
        if not charging and percent <= self.BATTERY_THRESHOLD:
            if not self._battery_warned:
                self._battery_warned = True
                pool = self._messages.get("battery") or []
                if pool:
                    self.say(pool[self._chatter_rng.randrange(len(pool))])
                    return True
        elif charging or percent > self.BATTERY_THRESHOLD + 10:
            self._battery_warned = False
        return False

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
            self._speak_text(text)

    def _on_tick(self) -> None:
        if self._dragging:
            self._set_active_sprite(STATE_DRAG)
            return
        if self.motion.behaviour == BEHAVIOUR_CHASE:
            cursor = QCursor.pos()
            self.motion.set_target(cursor.x(), cursor.y())
        elif self._sit_on_windows and self.motion.behaviour == BEHAVIOUR_FLOOR:
            self._platform_tick += 1
            if self._platform_tick >= 10:
                self._platform_tick = 0
                self.motion.set_platforms(windows_platforms(exclude_hwnds=(int(self.winId()),)))
        x, y = self.motion.step()
        self.move(x, y)
        self._set_active_sprite(self._visual_state())
        if self._audio_react:
            self._update_audio_scale()
            self.update()
        self._peer_tick += 1
        if self._peer_tick >= 5:
            self._peer_tick = 0
            self._check_peers()
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
            self.motion.clear_follow()
            self._mood.pet()    # petting cheers it up
            self._persist_mood()
            self._gain_affection(2)
            self._play_sound()
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
                if self.motion.behaviour == BEHAVIOUR_FLOOR:
                    # Dropping against a screen edge grabs the wall; otherwise fling.
                    if not self.motion.grab_nearest_wall():
                        self.motion.throw(self._last_move_delta[0], self._last_move_delta[1])
            else:
                self.say()  # a click (no drag) makes the pet talk
        super().mouseReleaseEvent(event)

    # --- drop a file onto the pet: wear it (image / pack) or eat it ---
    @staticmethod
    def dropped_path(mime_data) -> Optional[str]:
        """從拖曳資料取出第一個可用的本機路徑；沒有可用者回傳 None。"""
        if mime_data is None or not mime_data.hasUrls():
            return None
        for url in mime_data.urls():
            local_path = url.toLocalFile()
            if local_path and classify_drop(local_path) is not None:
                return local_path
        return None

    @staticmethod
    def dropped_link(mime_data) -> Optional[str]:
        """
        從拖曳資料取出網址（拖連結到寵物身上請牠幫忙開啟）；沒有則回傳 None。
        Pull an http(s) link out of a drop so the pet can open it for you.
        """
        if mime_data is None:
            return None
        candidates = []
        if mime_data.hasUrls():
            candidates += [url.toString() for url in mime_data.urls() if not url.isLocalFile()]
        if mime_data.hasText():
            candidates.append(mime_data.text())
        for candidate in candidates:
            text = str(candidate or "").strip()
            # 用網址解析判斷通訊協定，比字串開頭比對穩，也不必在程式碼裡寫死協定前綴。
            # Parse the URL instead of prefix-matching: sturdier, and no scheme
            # literals baked into the source.
            try:
                scheme = urlparse(text).scheme.lower()
            except ValueError:
                continue
            if scheme in _WEB_SCHEMES:
                return text
        return None

    def _accepts_drop(self, mime_data) -> bool:
        return self.dropped_path(mime_data) is not None or self.dropped_link(mime_data) is not None

    def dragEnterEvent(self, event) -> None:
        if self._accepts_drop(event.mimeData()):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        if self._accepts_drop(event.mimeData()):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        path = self.dropped_path(event.mimeData())
        link = self.dropped_link(event.mimeData()) if path is None else None
        if path is None and link is None:
            return
        front_engine_logger.info(f"[DesktopPetWidget] dropEvent | path={path}, link={link}")
        self.motion.wake()
        if link is not None:
            self.fetch_link(link)
        elif classify_drop(path) == DROP_SPRITE:
            self.change_sprite(path)
        else:
            self.feed(classify_food(path))
        event.acceptProposedAction()

    def fetch_link(self, url: str) -> None:
        """把拖進來的連結叼去瀏覽器開啟，並說一句 / Fetch a dropped link in the browser."""
        from frontengine.utils.browser.browser import open_browser

        front_engine_logger.info(f"[DesktopPetWidget] fetch_link | url={url}")
        self._gain_affection(1)
        pool = self._messages.get("fetch") or []
        if pool:
            self.say(pool[self._chatter_rng.randrange(len(pool))])
        try:
            open_browser(url)
        except Exception as error:  # pragma: no cover - browser boundary
            front_engine_logger.warning(f"[DesktopPetWidget] open_browser failed: {error!r}")

    def contextMenuEvent(self, event) -> None:
        self.menu.popup(event.globalPos())

    def closeEvent(self, event) -> None:
        if self._timer.isActive():
            self._timer.stop()
        if self._chatter_timer.isActive():
            self._chatter_timer.stop()
        if self._reminder_timer.isActive():
            self._reminder_timer.stop()
        self._bubble.close()
        for kind, obj in self._sprites.values():
            if kind == "movie":
                obj.stop()
        super().closeEvent(event)
