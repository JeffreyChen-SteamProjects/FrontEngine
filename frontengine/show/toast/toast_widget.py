"""
提示卡：在畫面上方短暫顯示一行字（提醒到期、規則觸發等），時間到自己關掉。
點擊穿透，不會擋到底下的操作。

A toast: a line of text shown briefly near the top of the screen - a reminder
coming due, a rule firing - that closes itself. Click-through, so it never gets
in the way of what is underneath.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger

DEFAULT_DURATION_MS = 5000
MIN_DURATION_MS = 500
_PADDING = 18
_CORNER_RADIUS = 10


def clamp_duration(value, fallback: int = DEFAULT_DURATION_MS) -> int:
    """顯示時間至少半秒，避免設成 0 讓提示閃一下就不見。"""
    try:
        return max(MIN_DURATION_MS, int(value))
    except (TypeError, ValueError):
        return fallback


class ToastWidget(BaseWidget):
    """
    一張自動消失的提示卡。文字寬度決定卡片寬度，位置預設貼在主螢幕上方置中。
    An auto-dismissing toast. The card is sized to its text and sits centred
    near the top of the primary screen by default.
    """

    def __init__(self, message: str = "", duration_ms: int = DEFAULT_DURATION_MS,
                 font_size: int = 18) -> None:
        front_engine_logger.info(f"[ToastWidget] Init | message={message!r}")
        super().__init__()
        self.message: str = str(message)
        self.duration_ms: int = clamp_duration(duration_ms)
        self.text_color = QColor("#ffffff")
        self.card_color = QColor(20, 20, 20, 230)
        self.opacity = 1.0
        # 提示卡不該被拖曳擺位，也不接受點擊
        # A toast is never dragged into place and never takes clicks.
        self.overlay_lockable = False
        self._font = QFont()
        self._font.setPointSize(max(8, int(font_size)))
        self._close_timer = QTimer(self)
        self._close_timer.setSingleShot(True)
        self._close_timer.timeout.connect(self.close)
        self.set_ui_window_flag(show_on_bottom=False)
        self.resize_to_message()

    def set_message(self, message: str) -> None:
        """換一則訊息並重新計算卡片大小。"""
        self.message = str(message)
        self.resize_to_message()
        self.update()

    def card_size(self) -> tuple:
        """
        依文字算出卡片的寬高（含內距），寬度以螢幕為上限、超過就換行。
        沒有上限的話，一段長一點的提醒文字會算出好幾千像素寬的卡片，
        move_to_top_centre 把它置中之後左右兩邊都跑出螢幕，字反而看不到。
        Size the card to its text, capped at the screen width and wrapped beyond
        that. Uncapped, a longer reminder produced a card thousands of pixels
        wide; centring it then ran off both edges and hid the very text it was
        supposed to show.
        """
        metrics = QFontMetrics(self._font)
        max_width = self._available_width()
        width = metrics.horizontalAdvance(self.message) + _PADDING * 2
        if width <= max_width:
            return (max(80, width), max(36, metrics.height() + _PADDING))
        bounds = metrics.boundingRect(
            0, 0, max_width - _PADDING * 2, 0,
            int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap), self.message)
        return (max_width, max(36, bounds.height() + _PADDING))

    def _available_width(self) -> int:
        """卡片最寬能到多少（螢幕可用寬度再留一點邊）。"""
        target = self.screen() or QGuiApplication.primaryScreen()
        if target is None:  # pragma: no cover - no screen at all
            return 800
        return max(160, target.availableGeometry().width() - _PADDING * 4)

    def resize_to_message(self) -> None:
        width, height = self.card_size()
        self.resize(width, height)
        self.move_to_top_centre()

    def move_to_top_centre(self, screen=None) -> None:
        """擺到螢幕上方置中（離頂端一小段距離，避開全螢幕程式的標題列）。"""
        target = screen or QGuiApplication.primaryScreen()
        if target is None:  # pragma: no cover - no screen at all
            return
        available = target.availableGeometry()
        self.move(
            available.x() + (available.width() - self.width()) // 2,
            available.y() + max(24, available.height() // 12),
        )

    def show_toast(self, screen=None) -> None:
        """顯示並在時間到時自動關閉。"""
        self.resize_to_message()
        self.move_to_top_centre(screen)
        self.show()
        self._close_timer.start(self.duration_ms)

    def draw_content(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.card_color)
        painter.drawRoundedRect(self.rect(), _CORNER_RADIUS, _CORNER_RADIUS)
        painter.setFont(self._font)
        painter.setPen(self.text_color)
        painter.drawText(
            self.rect(),
            int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
            self.message)


def show_toast(message: str, duration_ms: int = DEFAULT_DURATION_MS,
               screen=None) -> Optional[ToastWidget]:
    """
    顯示一則提示卡並回傳它（訊息為空就不顯示，回傳 None）。呼叫端不必自己
    管生命週期：時間到會自己 close，而 BaseWidget 帶著 WA_DeleteOnClose。
    Show a toast and hand it back (None for an empty message). Callers do not
    have to manage its life: it closes itself, and BaseWidget carries
    WA_DeleteOnClose.
    """
    text = str(message or "").strip()
    if not text:
        return None
    toast = ToastWidget(text, duration_ms)
    toast.show_toast(screen)
    return toast
