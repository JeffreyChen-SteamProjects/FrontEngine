"""
便利貼：一張浮在所有視窗上的小紙條，可以直接在上面打字，內容跨工作階段保存。
和其他覆蓋層不同，它必須收得到鍵盤與滑鼠，所以不做點擊穿透。

A sticky note: a small card that floats above every window, typed into
directly, and remembered between sessions. Unlike the other overlays it has to
receive the keyboard and the mouse, so it is never click-through.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QTextEdit, QVBoxLayout

from frontengine.show.base_widget import BaseWidget
from frontengine.show.window_helpers import apply_overlay_window_flags
from frontengine.utils.logging.loggin_instance import front_engine_logger

DEFAULT_COLOR = "#fff59d"
DEFAULT_WIDTH = 240
DEFAULT_HEIGHT = 180
MIN_SIZE = 80
_TEXT_MARGIN = 10


def clamp_size(value, fallback: int) -> int:
    """便利貼不能小到看不見。"""
    try:
        return max(MIN_SIZE, int(value))
    except (TypeError, ValueError):
        return fallback


def note_state(note: "StickyNoteWidget") -> Dict[str, Any]:
    """把一張便利貼的內容與位置整理成可以存進設定的資料。"""
    geometry = note.geometry()
    return {
        "text": note.text(),
        "color": note.color.name(),
        "x": geometry.x(), "y": geometry.y(),
        "width": geometry.width(), "height": geometry.height(),
    }


def normalize_note_states(states: Any) -> List[Dict[str, Any]]:
    """
    整理設定裡的便利貼清單，跳過壞掉的項目；沒有文字也保留（空紙條也是紙條）。
    Normalize the saved notes, skipping malformed entries. A blank note is kept:
    an empty card is still a card the user put there.
    """
    if not isinstance(states, (list, tuple)):
        return []
    notes: List[Dict[str, Any]] = []
    for state in states:
        if not isinstance(state, dict):
            continue
        color = QColor(str(state.get("color", DEFAULT_COLOR)))
        notes.append({
            "text": str(state.get("text", "")),
            "color": color.name() if color.isValid() else DEFAULT_COLOR,
            "x": _coerce(state.get("x"), 120),
            "y": _coerce(state.get("y"), 120),
            "width": clamp_size(state.get("width"), DEFAULT_WIDTH),
            "height": clamp_size(state.get("height"), DEFAULT_HEIGHT),
        })
    return notes


def _coerce(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


class StickyNoteWidget(BaseWidget):
    """
    可編輯的便利貼。內部放一個透明背景的 QTextEdit 負責輸入，紙張本身由
    BaseWidget 畫；沒有鎖定／點擊穿透，因為那會讓它無法打字。
    """

    def __init__(self, text: str = "", color: str = DEFAULT_COLOR,
                 width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> None:
        front_engine_logger.info("[StickyNoteWidget] Init")
        super().__init__()
        candidate = QColor(color)
        self.color = candidate if candidate.isValid() else QColor(DEFAULT_COLOR)
        self.opacity = 1.0
        # 要打字就不能點擊穿透，也就不提供鎖定
        # Typing needs the mouse and keyboard, so this one is never lockable.
        self.overlay_lockable = False
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self.text_edit = QTextEdit(self)
        self.text_edit.setFrameStyle(0)
        self.text_edit.setFont(QFont("", 11))
        self.text_edit.setStyleSheet(
            f"QTextEdit {{ background: {self.color.name()}; border: none; color: #333333; }}")
        self.text_edit.setPlainText(str(text))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(_TEXT_MARGIN, _TEXT_MARGIN, _TEXT_MARGIN, _TEXT_MARGIN)
        layout.addWidget(self.text_edit)

        apply_overlay_window_flags(self, show_on_bottom=False, allow_input=True)
        self.resize(clamp_size(width, DEFAULT_WIDTH), clamp_size(height, DEFAULT_HEIGHT))

    def text(self) -> str:
        return self.text_edit.toPlainText()

    def set_text(self, text: str) -> None:
        self.text_edit.setPlainText(str(text))

    def set_color(self, color) -> None:
        """換一張紙的顏色。"""
        candidate = QColor(color)
        if not candidate.isValid():
            return
        self.color = candidate
        self.text_edit.setStyleSheet(
            f"QTextEdit {{ background: {self.color.name()}; border: none; color: #333333; }}")
        self.update()

    def apply_state(self, state: Dict[str, Any]) -> None:
        """套用一筆已正規化的便利貼資料。"""
        self.set_text(state.get("text", ""))
        self.set_color(state.get("color", DEFAULT_COLOR))
        self.setGeometry(QRect(
            _coerce(state.get("x"), 120), _coerce(state.get("y"), 120),
            clamp_size(state.get("width"), DEFAULT_WIDTH),
            clamp_size(state.get("height"), DEFAULT_HEIGHT)))

    def draw_content(self, painter) -> None:
        """紙張本體（QTextEdit 疊在上面，所以這裡只要畫底色與邊）。"""
        painter.fillRect(self.rect(), self.color)
        painter.setPen(QColor(0, 0, 0, 40))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))


def restore_notes(states: Any, parent_list: Optional[List] = None) -> List[StickyNoteWidget]:
    """
    依儲存的資料重新開出便利貼並回傳；順便附加到呼叫端的清單（如果有給）。
    Reopen the saved notes and hand them back, appending to the caller's list.
    """
    notes: List[StickyNoteWidget] = []
    for state in normalize_note_states(states):
        note = StickyNoteWidget(state["text"], state["color"], state["width"], state["height"])
        note.apply_state(state)
        notes.append(note)
        if parent_list is not None:
            parent_list.append(note)
    return notes
