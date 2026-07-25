"""
頻譜視覺化覆蓋層：把系統輸出的音訊畫成長條或環形，含平滑與會慢慢落下的峰值。

音訊來源見 utils/audio_meter/loopback_capture：**這個功能會擷取系統輸出的音訊
串流**（算頻率非得有取樣資料不可），和寵物／桌布那種「只讀電表」不同。樣本只
在記憶體裡算 FFT，不寫檔也不外傳，關掉就停止擷取。

A spectrum overlay: draw the system output as bars or a ring, smoothed, with
peaks that drift down. See utils/audio_meter/loopback_capture for the source -
**this feature captures the output audio stream**, unlike the meter-only pet and
wallpaper reactions. Samples are FFT'd in memory, never stored or sent, and
capture stops when the overlay does.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.audio_meter.spectrum_analyzer import DEFAULT_BANDS, SpectrumSmoother, clamp_bands
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.power_mode.power_mode import tier_interval

STYLE_BARS = "bars"
STYLE_RING = "ring"
STYLES = (STYLE_BARS, STYLE_RING)

DEFAULT_COLOR = "#4dd0e1"
_UPDATE_INTERVAL_MS = 33
_PEAK_THICKNESS = 3
_RING_INNER_SHARE = 0.45


def normalize_style(style) -> str:
    """把樣式正規化；不認得的一律當長條。"""
    name = str(style or "").strip().lower()
    return name if name in STYLES else STYLE_BARS


def bar_rects(levels: List[float], width: int, height: int, gap: int = 2) -> List[tuple]:
    """
    把每個頻段的強度換成一根長條的 (x, y, w, h)。條數為 0 或畫布太小時回傳空清單。
    Turn band levels into (x, y, w, h) bars; empty when there is nothing to draw.
    """
    count = len(levels)
    if count <= 0 or width <= 0 or height <= 0:
        return []
    slot = width / count
    bar_width = max(1.0, slot - gap)
    rects = []
    for index, level in enumerate(levels):
        clamped = max(0.0, min(1.0, float(level)))
        bar_height = max(1.0, clamped * height)
        rects.append((index * slot + (slot - bar_width) / 2.0, height - bar_height,
                      bar_width, bar_height))
    return rects


class SpectrumWidget(BaseWidget):
    """
    頻譜覆蓋層。強度來源以 provider 注入（正式是 LoopbackSpectrum.bands，
    測試可以直接餵假資料），所以這個 widget 本身不碰任何音訊 API。
    """

    def __init__(self, bands: int = DEFAULT_BANDS, style: str = STYLE_BARS,
                 color: str = DEFAULT_COLOR) -> None:
        front_engine_logger.info(f"[SpectrumWidget] Init | bands={bands}, style={style}")
        super().__init__()
        self.band_count = clamp_bands(bands)
        self.style = normalize_style(style)
        self.color = QColor(color) if QColor(color).isValid() else QColor(DEFAULT_COLOR)
        self.opacity = 0.85
        self.smoother = SpectrumSmoother(self.band_count)
        self._provider = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)

    def set_level_provider(self, provider) -> None:
        """設定頻段強度來源（回傳一串 0~1，或 None 代表沒有訊號）。"""
        self._provider = provider
        self.smoother.reset()

    def set_bands(self, bands: int) -> None:
        self.band_count = clamp_bands(bands)
        self.smoother.set_bands(self.band_count)
        self.update()

    def set_style(self, style: str) -> None:
        self.style = normalize_style(style)
        self.update()

    def set_color(self, color) -> None:
        candidate = QColor(color)
        if candidate.isValid():
            self.color = candidate
            self.update()

    def start(self) -> None:
        """開始定時更新畫面。"""
        self._timer.start(tier_interval(_UPDATE_INTERVAL_MS, self.quality_tier))

    def stop(self) -> None:
        self._timer.stop()

    def apply_quality_tier(self) -> None:
        if self._timer.isActive():
            self._timer.start(tier_interval(_UPDATE_INTERVAL_MS, self.quality_tier))

    def refresh(self) -> None:
        """取一次強度、平滑後重畫。"""
        values: Optional[List[float]] = None
        if self._provider is not None:
            try:
                values = self._provider()
            except Exception:  # pragma: no cover - defensive around providers
                values = None
        self.smoother.push(values)
        self.update()

    def draw_content(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self.style == STYLE_RING:
            self._draw_ring(painter)
        else:
            self._draw_bars(painter)

    def _draw_bars(self, painter: QPainter) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        peak_color = QColor(self.color)
        peak_color.setAlpha(180)
        for index, rect in enumerate(bar_rects(self.smoother.levels, self.width(), self.height())):
            painter.setBrush(self.color)
            painter.drawRect(QRectF(*rect))
            peak = max(0.0, min(1.0, self.smoother.peaks[index]))
            painter.setBrush(peak_color)
            painter.drawRect(QRectF(rect[0], self.height() - peak * self.height() - _PEAK_THICKNESS,
                                    rect[2], _PEAK_THICKNESS))

    def _draw_ring(self, painter: QPainter) -> None:
        """環形：每個頻段是一根從內圈往外長的輻條。"""
        levels = self.smoother.levels
        if not levels:
            return
        centre_x, centre_y = self.width() / 2.0, self.height() / 2.0
        radius = min(centre_x, centre_y)
        inner = radius * _RING_INNER_SHARE
        span = 360.0 / len(levels)
        pen_width = max(2.0, (2 * 3.14159 * inner) / max(1, len(levels)) * 0.7)
        pen = painter.pen()
        pen.setColor(self.color)
        pen.setWidthF(pen_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        for index, level in enumerate(levels):
            angle = index * span
            length = inner + max(0.0, min(1.0, level)) * (radius - inner)
            painter.save()
            painter.translate(centre_x, centre_y)
            painter.rotate(angle)
            painter.drawLine(0, int(-inner), 0, int(-length))
            painter.restore()

    def closeEvent(self, event) -> None:
        self.stop()
        super().closeEvent(event)
