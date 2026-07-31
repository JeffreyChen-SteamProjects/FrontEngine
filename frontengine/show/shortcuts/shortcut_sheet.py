"""
快速鍵速查表：把目前綁定的全域快速鍵列在畫面上。

快速鍵改得掉，所以印在說明文件裡的那份遲早會過時；這一份是直接從實際生效的綁定
讀出來的，改過就跟著改。

排版與文字是純函式（`sheet_rows`），所以「顯示的內容對不對」不必開視窗就能驗。

A shortcut cheat sheet: the global shortcuts as they are actually bound.

Shortcuts can be rebound, so any list written into the documentation goes stale;
this one is read from the bindings in force and follows them.

The rows are produced by a pure function (`sheet_rows`), so what it says can be
checked without opening a window.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QApplication

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger

# pynput 的寫法轉成看得懂的樣子
# pynput spellings turned into something readable
_PRETTY = {
    "ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "cmd": "Cmd",
    "up": "Up", "down": "Down", "left": "Left", "right": "Right",
    "space": "Space", "enter": "Enter", "esc": "Esc", "tab": "Tab",
}


def pretty_combo(combo: str) -> str:
    """
    把 `<ctrl>+<shift>+<f12>` 變成 `Ctrl + Shift + F12`。

    使用者是在對照畫面上按下去的手指，不是在讀設定檔，所以尖括號和小寫都要去掉。
    Turn `<ctrl>+<shift>+<f12>` into `Ctrl + Shift + F12`. The reader is matching
    this against their fingers, not against a settings file, so the angle
    brackets and the lower case go.
    """
    parts = []
    for raw in str(combo or "").split("+"):
        name = raw.strip().strip("<>").strip()
        if not name:
            continue
        if name in _PRETTY:
            parts.append(_PRETTY[name])
        elif len(name) > 1 and name[0] == "f" and name[1:].isdigit():
            parts.append(name.upper())
        else:
            parts.append(name.upper() if len(name) == 1 else name.capitalize())
    return " + ".join(parts)


def sheet_rows(bindings: Dict[str, str], label_for) -> List[Tuple[str, str]]:
    """
    產生 (快速鍵, 動作說明) 的清單，依動作說明排序。

    `bindings` 是「組合字串 -> 動作名稱」，和 HotkeyService 用的同一份，所以這裡
    列出來的一定就是實際會生效的。沒有綁定時回傳空清單，呼叫端才能說「沒有」而
    不是開一個空白視窗。
    Rows of (shortcut, what it does), sorted by the description.

    `bindings` is the same combo-to-action mapping HotkeyService uses, so what
    is listed is what will actually fire. With nothing bound this returns an
    empty list, so the caller can say so rather than opening a blank window.
    """
    rows = []
    for combo, action in (bindings or {}).items():
        if not combo or not action:
            continue
        rows.append((pretty_combo(combo), label_for(action)))
    return sorted(rows, key=lambda row: row[1].lower())


class ShortcutSheetWidget(BaseWidget):
    """把速查表畫在畫面中央，點擊穿透。"""

    PADDING = 28
    LINE_SPACING = 10

    def __init__(self, rows: List[Tuple[str, str]], title: str = "Shortcuts",
                 font_size: int = 20, opacity: float = 0.9) -> None:
        front_engine_logger.info(f"[ShortcutSheetWidget] Init | rows={len(rows)}")
        super().__init__()
        self.opacity = max(0.1, min(1.0, float(opacity)))
        self.rows = list(rows)
        self.title = title
        self.font_size = max(10, int(font_size))
        self.text_color = QColor("#ffffff")
        self.key_color = QColor("#ffd740")
        self.background_color = QColor(0, 0, 0, 210)

    def sizeHint(self):  # pragma: no cover - Qt geometry
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen is not None else None
        if available is None:
            return super().sizeHint()
        return available.size() / 2

    def draw_content(self, painter: QPainter) -> None:
        painter.fillRect(self.rect(), self.background_color)

        title_font = QFont()
        title_font.setPixelSize(int(self.font_size * 1.3))
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(self.text_color)
        y = self.PADDING + int(self.font_size * 1.3)
        painter.drawText(self.PADDING, y, self.title)

        row_font = QFont()
        row_font.setPixelSize(self.font_size)
        painter.setFont(row_font)
        y += int(self.font_size * 1.4)

        # 左欄放快速鍵、右欄放說明。欄寬固定，兩欄才會各自對齊成一直線。
        # Shortcut on the left, description on the right, at a fixed column so
        # both line up rather than drifting with the text.
        key_column = self.PADDING
        text_column = self.PADDING + int(self.font_size * 11)
        for combo, description in self.rows:
            y += self.font_size + self.LINE_SPACING
            painter.setPen(self.key_color)
            painter.drawText(key_column, y, combo)
            painter.setPen(self.text_color)
            painter.drawText(text_column, y, description)

    def keyPressEvent(self, event) -> None:  # pragma: no cover - Qt event
        if event.key() in (Qt.Key.Key_Escape,):
            self.close()
            return
        super().keyPressEvent(event)


def build_sheet(bindings: Dict[str, str], label_for, title: str = "Shortcuts",
                font_size: int = 20) -> Optional[ShortcutSheetWidget]:
    """
    建立速查表；沒有任何綁定時回傳 None。
    Build the sheet, or None when nothing is bound - an empty black rectangle
    explains nothing.
    """
    rows = sheet_rows(bindings, label_for)
    if not rows:
        front_engine_logger.info("[ShortcutSheetWidget] nothing bound, not showing")
        return None
    return ShortcutSheetWidget(rows, title=title, font_size=font_size)
