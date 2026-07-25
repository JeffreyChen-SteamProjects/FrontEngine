"""
護眼與無障礙用的螢幕覆蓋層：
  - ScreenFilterWidget：整片色彩濾鏡（暖色調光、色弱／閱讀障礙用的色片）
  - ReadingRulerWidget：跟隨游標的閱讀尺，只留一條亮帶、其餘壓暗
兩者都是點擊穿透的置頂層，不影響底下程式的操作。

Screen overlays for eye comfort and accessibility: a whole-screen colour filter
(warm dimming, or a tint for visual stress) and a reading ruler that follows the
cursor, dimming everything except one band. Both are click-through, so the
programs underneath still receive every click.
"""
from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import QRect, QTimer, Qt
from PySide6.QtGui import QColor, QCursor, QPainter

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger

# 常用的護眼色片（名稱 -> HEX）；暖色調光最常見，其餘給視覺壓力／閱讀障礙使用。
# Common eye-comfort tints. Warm dimming is the usual pick; the rest help with
# visual stress and reading difficulties.
FILTER_COLORS = (
    ("Warm", "#ff9640"),
    ("Amber", "#ffb75e"),
    ("Rose", "#ff8f8f"),
    ("Yellow", "#ffe066"),
    ("Green", "#8fd694"),
    ("Blue", "#7fb2ff"),
    ("Grey", "#808080"),
)
DEFAULT_FILTER_COLOR = "#ff9640"
MIN_STRENGTH = 1
MAX_STRENGTH = 80


def clamp_strength(value, fallback: int = 15) -> int:
    """
    把濾鏡濃度夾在可用範圍：太淡沒效果，太濃會蓋掉畫面看不見東西。
    Clamp the filter strength — too light does nothing, too heavy hides the screen.
    """
    try:
        return max(MIN_STRENGTH, min(MAX_STRENGTH, int(value)))
    except (TypeError, ValueError):
        return fallback


def ruler_band(cursor_y: int, height: int, band_height: int) -> Tuple[int, int]:
    """
    依游標位置算出閱讀亮帶的 (top, bottom)，並保證不超出畫面。
    The (top, bottom) of the reading band for a cursor position, kept on screen.
    """
    band = max(10, int(band_height))
    half = band // 2
    top = int(cursor_y) - half
    top = max(0, min(top, max(0, int(height) - band)))
    return (top, top + band)


class ScreenFilterWidget(BaseWidget):
    """整片色彩濾鏡：以指定顏色與濃度覆蓋螢幕，滑鼠事件穿透。"""

    def __init__(self, color: str = DEFAULT_FILTER_COLOR, strength: int = 15) -> None:
        front_engine_logger.info(f"[ScreenFilterWidget] Init | color={color}, strength={strength}")
        super().__init__()
        self.filter_color = QColor(color) if QColor(color).isValid() else QColor(DEFAULT_FILTER_COLOR)
        self.strength = clamp_strength(strength)
        self.opacity = self.strength / 100.0

    def set_filter(self, color: Optional[str] = None, strength: Optional[int] = None) -> None:
        """調整顏色或濃度並立即重繪。"""
        if color is not None:
            candidate = QColor(color)
            if candidate.isValid():
                self.filter_color = candidate
        if strength is not None:
            self.strength = clamp_strength(strength)
            self.opacity = self.strength / 100.0
        self.update()

    def draw_content(self, painter: QPainter) -> None:
        painter.fillRect(self.rect(), self.filter_color)


class ReadingRulerWidget(BaseWidget):
    """
    閱讀尺：整片壓暗，只留一條跟著游標移動的亮帶，幫助視線定位。
    A reading ruler: the screen dims except for one band that tracks the cursor.
    """

    DEFAULT_BAND_HEIGHT = 90
    REFRESH_MS = 33

    def __init__(self, band_height: int = DEFAULT_BAND_HEIGHT, strength: int = 45) -> None:
        front_engine_logger.info(
            f"[ReadingRulerWidget] Init | band={band_height}, strength={strength}")
        super().__init__()
        self.band_height = max(10, int(band_height))
        self.strength = clamp_strength(strength, fallback=45)
        self.opacity = 1.0  # the dimming lives in the fill colour's alpha
        self.cursor_y = 0
        self._cursor_provider = lambda: QCursor.pos().y()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.follow_cursor)

    def set_cursor_provider(self, provider) -> None:
        """注入游標位置來源（測試用）/ Inject the cursor source (used by tests)."""
        self._cursor_provider = provider

    def start_following(self, interval_ms: int = REFRESH_MS) -> None:
        """開始跟隨游標 / Start tracking the cursor."""
        self.follow_cursor()
        self._timer.start(max(10, int(interval_ms)))

    def set_band(self, band_height: Optional[int] = None, strength: Optional[int] = None) -> None:
        """調整亮帶高度或壓暗程度。"""
        if band_height is not None:
            self.band_height = max(10, int(band_height))
        if strength is not None:
            self.strength = clamp_strength(strength, fallback=45)
        self.update()

    def follow_cursor(self) -> None:
        """把亮帶移到游標所在的高度（位置沒變就不重繪）。"""
        try:
            position = int(self._cursor_provider())
        except Exception:  # pragma: no cover - defensive around injected providers
            return
        local_y = position - self.y()
        if local_y == self.cursor_y:
            return
        self.cursor_y = local_y
        self.update()

    def draw_content(self, painter: QPainter) -> None:
        shade = QColor(0, 0, 0, int(255 * self.strength / 100.0))
        top, bottom = ruler_band(self.cursor_y, self.height(), self.band_height)
        painter.fillRect(QRect(0, 0, self.width(), max(0, top)), shade)
        painter.fillRect(
            QRect(0, bottom, self.width(), max(0, self.height() - bottom)), shade)

    def closeEvent(self, event) -> None:
        if self._timer.isActive():
            self._timer.stop()
        super().closeEvent(event)
