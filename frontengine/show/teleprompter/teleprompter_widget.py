"""
提詞機：把講稿以可調速度往上捲，字夠大、可以左右鏡像（配提詞玻璃用）。

捲動用「每次前進幾個像素」而不是「每次一行」，這樣速度才會平順；到底之後
會停在最後一行，不會自己跳回開頭把人嚇一跳。

A teleprompter: scroll a script upward at an adjustable speed, in large type,
optionally mirrored for prompter glass.

Scrolling advances by pixels rather than by lines so the motion stays smooth,
and it stops at the last line rather than snapping back to the top mid-read.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QTransform

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.power_mode.power_mode import tier_interval

DEFAULT_SPEED = 40          # 像素/秒 / pixels per second
MIN_SPEED = 5
MAX_SPEED = 400
DEFAULT_FONT_SIZE = 32
MIN_FONT_SIZE = 10
MAX_FONT_SIZE = 120
_TICK_MS = 33
_SIDE_MARGIN = 40


def clamp_speed(value, fallback: int = DEFAULT_SPEED) -> int:
    """捲動速度夾在讀得完又跟得上的範圍。"""
    try:
        return max(MIN_SPEED, min(MAX_SPEED, int(value)))
    except (TypeError, ValueError):
        return fallback


def clamp_font_size(value, fallback: int = DEFAULT_FONT_SIZE) -> int:
    """字級夾在看得見的範圍。"""
    try:
        return max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, int(value)))
    except (TypeError, ValueError):
        return fallback


def wrap_lines(text: str, metrics: QFontMetrics, width: int) -> List[str]:
    """
    依實際字寬把講稿折行；空行會保留（那是段落之間的呼吸）。
    Wrap the script to the actual text width, keeping blank lines - they are the
    pauses between paragraphs.
    """
    usable = max(40, int(width))
    lines: List[str] = []
    for paragraph in str(text or "").splitlines():
        if not paragraph.strip():
            lines.append("")
            continue
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if current and metrics.horizontalAdvance(candidate) > usable:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
    return lines


class TeleprompterWidget(BaseWidget):
    """
    提詞機覆蓋層。捲動位置以像素計，速度、字級與鏡像都可以邊跑邊調。
    """

    def __init__(self, text: str = "", speed: int = DEFAULT_SPEED,
                 font_size: int = DEFAULT_FONT_SIZE, mirrored: bool = False) -> None:
        front_engine_logger.info("[TeleprompterWidget] Init")
        super().__init__()
        self.script = str(text)
        self.speed = clamp_speed(speed)
        self.mirrored = bool(mirrored)
        self.text_color = QColor("#ffffff")
        self.opacity = 0.9
        self.offset = 0.0
        self._font = QFont()
        self._font.setPointSize(clamp_font_size(font_size))
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.advance)

    @property
    def font_size(self) -> int:
        return self._font.pointSize()

    def set_script(self, text: str) -> None:
        """換一份講稿並回到開頭。"""
        self.script = str(text)
        self.offset = 0.0
        self.update()

    def set_speed(self, speed: int) -> None:
        self.speed = clamp_speed(speed)

    def set_font_size(self, size: int) -> None:
        self._font.setPointSize(clamp_font_size(size))
        self.update()

    def set_mirrored(self, mirrored: bool) -> None:
        """左右鏡像：透過提詞玻璃反射後才是正的。"""
        self.mirrored = bool(mirrored)
        self.update()

    def lines(self) -> List[str]:
        """目前折行後的講稿。"""
        return wrap_lines(self.script, QFontMetrics(self._font),
                          max(40, self.width() - _SIDE_MARGIN * 2))

    def content_height(self) -> int:
        """整份講稿捲完需要多高。"""
        return len(self.lines()) * QFontMetrics(self._font).lineSpacing()

    def max_offset(self) -> float:
        """捲到底的位置（不會捲過頭）。"""
        return float(max(0, self.content_height() - self.height() // 2))

    def start(self) -> None:
        self._timer.start(tier_interval(_TICK_MS, self.quality_tier))

    def stop(self) -> None:
        self._timer.stop()

    def apply_quality_tier(self) -> None:
        if self._timer.isActive():
            self._timer.start(tier_interval(_TICK_MS, self.quality_tier))

    def rewind(self) -> None:
        """回到講稿開頭。"""
        self.offset = 0.0
        self.update()

    def advance(self, seconds: Optional[float] = None) -> float:
        """
        前進一小段（預設一個 tick 的量），回傳新的捲動位置。捲到底就停住。
        Advance one tick's worth and return the new offset, stopping at the end.
        """
        step = self.speed * (seconds if seconds is not None else _TICK_MS / 1000.0)
        self.offset = min(self.max_offset(), self.offset + step)
        self.update()
        return self.offset

    def draw_content(self, painter: QPainter) -> None:
        painter.setFont(self._font)
        painter.setPen(self.text_color)
        if self.mirrored:
            painter.setTransform(QTransform().translate(self.width(), 0).scale(-1, 1))
        spacing = QFontMetrics(self._font).lineSpacing()
        top = self.height() // 2 - int(self.offset)
        for index, line in enumerate(self.lines()):
            y = top + index * spacing
            if y < -spacing or y > self.height():
                continue
            painter.drawText(_SIDE_MARGIN, y, self.width() - _SIDE_MARGIN * 2, spacing,
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, line)

    def closeEvent(self, event) -> None:
        self.stop()
        super().closeEvent(event)
