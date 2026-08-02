"""
按鍵顯示：把剛按下的按鍵顯示在畫面角落，做教學影片或直播時觀眾才知道你按了什麼。
PowerToys 至今沒有內建這個功能，而本專案本來就有全域鍵盤監聽（pynput），
所以只需要一層顯示。按鍵格式化是純函式，可獨立測試。

Keystroke display: show what you just pressed in a screen corner, so viewers of
a tutorial or stream can follow along. PowerToys still has no built-in version;
this project already listens for global hotkeys, so only the display is new.
The formatting is pure and independently testable.
"""
from __future__ import annotations

import time
from typing import List, Tuple

from PySide6.QtCore import QRect, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger

DEFAULT_HOLD_SECONDS = 2.0
MAX_KEYS_SHOWN = 6
MIN_FONT_SIZE = 8
MAX_FONT_SIZE = 96

# 顯示位置。底部置中是預設，但簡報者的投影片字幕常常也在底部，
# 所以要能挪開。
# Where the panel sits. Bottom centre is the default, but a presenter's own
# subtitles often live there too, so it has to be movable.
POSITION_BOTTOM = "bottom"
POSITION_TOP = "top"
POSITION_BOTTOM_LEFT = "bottom_left"
POSITION_BOTTOM_RIGHT = "bottom_right"
POSITIONS = (POSITION_BOTTOM, POSITION_TOP, POSITION_BOTTOM_LEFT, POSITION_BOTTOM_RIGHT)

# 滑鼠鍵的顯示名稱 / How mouse buttons are shown
_MOUSE_NAMES = {
    "left": "Left Click",
    "right": "Right Click",
    "middle": "Middle Click",
    "button8": "Mouse 4",
    "button9": "Mouse 5",
    "x1": "Mouse 4",
    "x2": "Mouse 5",
}
_SCROLL_NAMES = {"up": "Scroll Up", "down": "Scroll Down"}

# 修飾鍵的顯示名稱 / How modifier keys are shown
_MODIFIER_NAMES = {
    "ctrl": "Ctrl", "ctrl_l": "Ctrl", "ctrl_r": "Ctrl",
    "alt": "Alt", "alt_l": "Alt", "alt_r": "Alt", "alt_gr": "AltGr",
    "shift": "Shift", "shift_l": "Shift", "shift_r": "Shift",
    "cmd": "Win", "cmd_l": "Win", "cmd_r": "Win",
}
# 特殊鍵的顯示名稱 / Friendlier names for special keys
_SPECIAL_NAMES = {
    "space": "Space", "enter": "Enter", "return": "Enter", "tab": "Tab",
    "backspace": "Backspace", "delete": "Del", "esc": "Esc", "escape": "Esc",
    "up": "↑", "down": "↓", "left": "←", "right": "→",
    "page_up": "PgUp", "page_down": "PgDn", "home": "Home", "end": "End",
}


def format_key(name) -> str:
    """
    把按鍵名稱轉成畫面上好讀的字（修飾鍵、方向鍵、功能鍵各有寫法）。
    Turn a key name into something readable on screen.
    """
    text = str(name or "").strip().strip("'")
    if not text:
        return ""
    lowered = text.lower()
    if lowered in _MODIFIER_NAMES:
        return _MODIFIER_NAMES[lowered]
    if lowered in _SPECIAL_NAMES:
        return _SPECIAL_NAMES[lowered]
    if lowered.startswith("key."):
        return format_key(text[4:])
    if len(text) == 1:
        return text.upper()
    if lowered.startswith("f") and lowered[1:].isdigit():
        return text.upper()
    return text.replace("_", " ").title()


def format_combo(keys) -> str:
    """把同時按著的按鍵組成 `Ctrl + Shift + S` 這種字串（去重、保留順序）。"""
    parts: List[str] = []
    for key in keys or ():
        formatted = format_key(key)
        if formatted and formatted not in parts:
            parts.append(formatted)
    return " + ".join(parts)


def format_mouse_button(name) -> str:
    """
    把滑鼠鍵名稱轉成畫面上的字。認不得的鍵原樣顯示（側鍵的名稱各家不同，
    寧可顯示一個怪名字，也不要什麼都不顯示讓人以為壞掉了）。
    A mouse button as shown on screen. An unknown button keeps its own name -
    side buttons are named differently per backend, and showing something odd
    beats showing nothing and looking broken.
    """
    text = str(name or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    if lowered in _MOUSE_NAMES:
        return _MOUSE_NAMES[lowered]
    if lowered.startswith("button."):
        return format_mouse_button(text.split(".", 1)[1])
    return text.replace("_", " ").title()


def normalize_position(position) -> str:
    """把顯示位置正規化；不認得的一律當底部置中。"""
    return position if position in POSITIONS else POSITION_BOTTOM


def clamp_font_size(value, fallback: int = 28) -> int:
    """字級夾在看得見又不至於蓋滿螢幕的範圍。"""
    try:
        return max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, int(value)))
    except (TypeError, ValueError):
        return fallback


def panel_origin(position: str, panel: Tuple[int, int], area: Tuple[int, int],
                 padding: int) -> Tuple[int, int]:
    """
    依位置算出面板左上角座標。純算術，所以排版不必開視窗就驗得了。
    The panel's top-left for a position. Pure arithmetic, so the layout is
    testable without showing a window.
    """
    panel_width, panel_height = panel
    area_width, area_height = area
    centre_x = max(0, (area_width - panel_width) // 2)
    left_x = padding
    right_x = max(0, area_width - panel_width - padding)
    bottom_y = max(0, area_height - panel_height - padding)
    place = normalize_position(position)
    if place == POSITION_TOP:
        return centre_x, padding
    if place == POSITION_BOTTOM_LEFT:
        return left_x, bottom_y
    if place == POSITION_BOTTOM_RIGHT:
        return right_x, bottom_y
    return centre_x, bottom_y


def visible_keys(entries, now: float, hold_seconds: float = DEFAULT_HOLD_SECONDS,
                 limit: int = MAX_KEYS_SHOWN) -> List[str]:
    """
    從 (文字, 時間) 清單裡挑出還沒過期的按鍵，最多顯示 limit 個（最新在後）。
    The still-fresh entries from a list of (text, timestamp) pairs.
    """
    fresh = [text for text, stamp in entries or () if now - stamp <= max(0.1, float(hold_seconds))]
    return fresh[-max(1, int(limit)):]


class KeystrokeDisplayWidget(BaseWidget):
    """
    按鍵顯示層：把最近按下的按鍵排成一列顯示，過幾秒自動淡出。點擊穿透。
    按鍵來源由外部推入（`push_keys`），因此不需要在這裡自己開監聽器。
    """

    REFRESH_MS = 100
    PADDING = 12

    def __init__(self, hold_seconds: float = DEFAULT_HOLD_SECONDS, font_size: int = 28,
                 color: str = "#ffffff", background: str = "#000000",
                 position: str = POSITION_BOTTOM, show_mouse: bool = True) -> None:
        front_engine_logger.info(f"[KeystrokeDisplayWidget] Init | hold={hold_seconds}s")
        super().__init__()
        self.opacity = 1.0
        self.hold_seconds = max(0.2, float(hold_seconds))
        self.text_color = QColor(color) if QColor(color).isValid() else QColor("#ffffff")
        self.background_color = QColor(background) if QColor(background).isValid() else QColor("#000000")
        self.font_size = clamp_font_size(font_size)
        self.position = normalize_position(position)
        self.show_mouse = bool(show_mouse)
        self.entries: List[Tuple[str, float]] = []
        self._now = time.monotonic
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._expire)

    def set_clock(self, clock) -> None:
        """注入時間來源（測試用）。"""
        self._now = clock

    def set_style(self, font_size=None, color=None, background=None,
                  position=None) -> None:
        """
        改外觀。給 None 的欄位不動——呼叫端常常只想改一項。
        Restyle. A None field is left alone: callers usually change one thing.
        """
        if font_size is not None:
            self.font_size = clamp_font_size(font_size, self.font_size)
        if color is not None and QColor(color).isValid():
            self.text_color = QColor(color)
        if background is not None and QColor(background).isValid():
            self.background_color = QColor(background)
        if position is not None:
            self.position = normalize_position(position)
        self.update()

    def set_show_mouse(self, enabled: bool) -> None:
        """要不要把滑鼠點擊也顯示出來。"""
        self.show_mouse = bool(enabled)

    def start(self, interval_ms: int = REFRESH_MS) -> None:
        """開始定期清掉過期的按鍵。"""
        self._timer.start(max(30, int(interval_ms)))

    def push_keys(self, keys) -> None:
        """
        推入一次按鍵事件（單一鍵或組合鍵）；空的輸入忽略。
        Record one keypress (single key or combination); blanks are ignored.
        """
        text = format_combo(keys if isinstance(keys, (list, tuple, set)) else [keys])
        self._push_text(text)

    def push_mouse(self, button) -> None:
        """
        推入一次滑鼠點擊。關掉顯示滑鼠時直接忽略——教學影片裡滑鼠移動本來就
        看得到，但按了哪一顆看不到，所以這是可選的而不是硬塞的。
        Record one mouse click, ignored while mouse display is off: a tutorial
        already shows the pointer moving, only which button was pressed is
        invisible, so this is opt-out rather than forced.
        """
        if not self.show_mouse:
            return
        self._push_text(format_mouse_button(button))

    def _push_text(self, text: str) -> None:
        if not text:
            return
        self.entries.append((text, self._now()))
        self.entries = self.entries[-(MAX_KEYS_SHOWN * 2):]
        self.update()

    def current_text(self) -> str:
        """目前該顯示的字串。"""
        return "   ".join(visible_keys(self.entries, self._now(), self.hold_seconds))

    def _expire(self) -> None:
        # 拿還沒過期的「全部」數量來比，不要用 visible_keys——它只回傳最多
        # MAX_KEYS_SHOWN 筆，一旦按超過那個數量，這個比較就永遠不相等，
        # 每 100ms 都會重建清單並重畫一次，其實什麼都沒過期。
        # Compare against the full count of unexpired entries, not visible_keys:
        # that returns at most MAX_KEYS_SHOWN, so past that many keys the test is
        # never equal and every 100 ms tick rebuilds the list and repaints with
        # nothing actually having expired.
        now = self._now()
        fresh = [
            (text, stamp) for text, stamp in self.entries
            if now - stamp <= self.hold_seconds
        ]
        if len(fresh) != len(self.entries):
            self.entries = fresh
            self.update()

    def draw_content(self, painter: QPainter) -> None:
        text = self.current_text()
        if not text:
            return
        font = QFont(self.font().family(), self.font_size)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        width = metrics.horizontalAdvance(text) + self.PADDING * 2
        height = metrics.height() + self.PADDING
        origin = panel_origin(self.position, (width, height),
                              (self.width(), self.height()), self.PADDING)
        box = QRect(origin[0], origin[1], width, height)
        background = QColor(self.background_color)
        background.setAlpha(170)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(box, 8, 8)
        painter.setPen(self.text_color)
        painter.drawText(box, int(Qt.AlignmentFlag.AlignCenter), text)

    def closeEvent(self, event) -> None:
        if self._timer.isActive():
            self._timer.stop()
        super().closeEvent(event)
