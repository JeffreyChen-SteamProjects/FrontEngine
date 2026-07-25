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
                 color: str = "#ffffff", background: str = "#000000") -> None:
        front_engine_logger.info(f"[KeystrokeDisplayWidget] Init | hold={hold_seconds}s")
        super().__init__()
        self.opacity = 1.0
        self.hold_seconds = max(0.2, float(hold_seconds))
        self.text_color = QColor(color) if QColor(color).isValid() else QColor("#ffffff")
        self.background_color = QColor(background) if QColor(background).isValid() else QColor("#000000")
        self.font_size = max(8, int(font_size))
        self.entries: List[Tuple[str, float]] = []
        self._now = time.monotonic
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._expire)

    def set_clock(self, clock) -> None:
        """注入時間來源（測試用）。"""
        self._now = clock

    def start(self, interval_ms: int = REFRESH_MS) -> None:
        """開始定期清掉過期的按鍵。"""
        self._timer.start(max(30, int(interval_ms)))

    def push_keys(self, keys) -> None:
        """
        推入一次按鍵事件（單一鍵或組合鍵）；空的輸入忽略。
        Record one keypress (single key or combination); blanks are ignored.
        """
        text = format_combo(keys if isinstance(keys, (list, tuple, set)) else [keys])
        if not text:
            return
        self.entries.append((text, self._now()))
        self.entries = self.entries[-(MAX_KEYS_SHOWN * 2):]
        self.update()

    def current_text(self) -> str:
        """目前該顯示的字串。"""
        return "   ".join(visible_keys(self.entries, self._now(), self.hold_seconds))

    def _expire(self) -> None:
        before = len(visible_keys(self.entries, self._now(), self.hold_seconds))
        if before != len(self.entries):
            self.entries = [
                (text, stamp) for text, stamp in self.entries
                if self._now() - stamp <= self.hold_seconds
            ]
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
        box = QRect(max(0, (self.width() - width) // 2),
                    max(0, self.height() - height - self.PADDING), width, height)
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
