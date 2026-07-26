"""
系統監控覆蓋層：把 CPU／記憶體／磁碟的近況畫成小折線圖，數字疊在圖上。
平均值看不出卡頓，折線可以——這也是硬體 OSD 常見的做法。

A system monitor overlay: recent CPU, memory and disk history as small
sparklines with the current number on top. An average hides a stall; a line
does not - which is why hardware OSDs draw one.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.power_mode.power_mode import tier_interval
from frontengine.utils.system_stats.system_stats import system_stats

DEFAULT_HISTORY = 60
MIN_HISTORY = 10
MAX_HISTORY = 600
UPDATE_INTERVAL_MS = 1000

# 每條線：(system_stats 的欄位, 顯示名稱, 顏色)
# Each line: (key in system_stats, label, colour).
LINES: Tuple[Tuple[str, str, str], ...] = (
    ("cpu", "CPU", "#4dd0e1"),
    ("ram", "RAM", "#ffb74d"),
    ("disk", "DISK", "#81c784"),
)
_ROW_HEIGHT = 34
_LABEL_WIDTH = 46
_PADDING = 6


def clamp_history(value, fallback: int = DEFAULT_HISTORY) -> int:
    """歷史長度夾在畫得出來的範圍。"""
    try:
        return max(MIN_HISTORY, min(MAX_HISTORY, int(value)))
    except (TypeError, ValueError):
        return fallback


def stat_percent(stats: Dict[str, object], key: str) -> Optional[float]:
    """
    取出某個百分比欄位並夾在 0~100；還沒有讀數（例如第一次取樣的 CPU）
    回傳 None，讓折線知道「這一刻沒有資料」而不是畫成 0。
    Pull a percentage field and clamp it to 0..100. A field with no reading yet
    - CPU on the very first sample - gives None, so the line can tell "no data"
    apart from "zero".
    """
    value = stats.get(key)
    if not isinstance(value, (int, float)):
        return None
    return max(0.0, min(100.0, float(value)))


def sparkline_path(values: List[float], width: float, height: float) -> QPainterPath:
    """
    把一串 0~100 的數值畫成一條折線（左舊右新）。少於兩點時回傳空路徑。
    A polyline over 0..100 values, oldest on the left. Fewer than two points
    gives an empty path.
    """
    path = QPainterPath()
    if len(values) < 2 or width <= 0 or height <= 0:
        return path
    step = width / (len(values) - 1)
    for index, value in enumerate(values):
        clamped = max(0.0, min(100.0, float(value)))
        point_y = height - (clamped / 100.0) * height
        if index == 0:
            path.moveTo(0.0, point_y)
        else:
            path.lineTo(index * step, point_y)
    return path


class SystemMonitorWidget(BaseWidget):
    """
    系統監控小圖。統計來源可注入（正式用 system_stats，測試餵假資料）。
    """

    def __init__(self, history: int = DEFAULT_HISTORY, stats_provider=None) -> None:
        front_engine_logger.info(f"[SystemMonitorWidget] Init | history={history}")
        super().__init__()
        self.history_length = clamp_history(history)
        self.opacity = 0.9
        self._stats_provider = stats_provider or system_stats
        self._series: Dict[str, Deque[float]] = {
            key: deque(maxlen=self.history_length) for key, _label, _color in LINES
        }
        self._latest: Dict[str, float] = dict.fromkeys(
            (key for key, _label, _color in LINES), 0.0)
        self._font = QFont()
        self._font.setPointSize(9)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.sample)
        self.resize(240, _ROW_HEIGHT * len(LINES) + _PADDING * 2)

    def series(self, key: str) -> List[float]:
        """某一條線目前的歷史值（最舊在前）。"""
        return list(self._series.get(key, ()))

    def latest(self, key: str) -> float:
        return float(self._latest.get(key, 0.0))

    def set_history(self, history: int) -> None:
        """改變保留的取樣數量（保留既有資料的尾端）。"""
        self.history_length = clamp_history(history)
        for key, samples in self._series.items():
            self._series[key] = deque(list(samples)[-self.history_length:],
                                      maxlen=self.history_length)
        self.update()

    def start(self) -> None:
        self.sample()
        self._timer.start(tier_interval(UPDATE_INTERVAL_MS, self.quality_tier))

    def stop(self) -> None:
        self._timer.stop()

    def apply_quality_tier(self) -> None:
        if self._timer.isActive():
            self._timer.start(tier_interval(UPDATE_INTERVAL_MS, self.quality_tier))

    def sample(self) -> None:
        """取一次系統狀態並推進每條線。"""
        try:
            stats = self._stats_provider() or {}
        except Exception as error:  # pragma: no cover - defensive around providers
            front_engine_logger.warning(f"[SystemMonitorWidget] stats failed: {error!r}")
            return
        for key, _label, _color in LINES:
            value = stat_percent(stats, key)
            if value is None:
                # 讀不到就沿用上一筆，折線不會憑空掉到 0
                # Nothing to read: carry the last value so the line does not dive to 0.
                value = self._latest.get(key, 0.0)
            self._series[key].append(value)
            self._latest[key] = value
        self.update()

    def draw_content(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setFont(self._font)
        graph_width = max(10, self.width() - _LABEL_WIDTH - _PADDING * 2)
        for row, (key, label, color) in enumerate(LINES):
            top = _PADDING + row * _ROW_HEIGHT
            painter.setPen(QColor(color))
            painter.drawText(QRectF(_PADDING, top, _LABEL_WIDTH, _ROW_HEIGHT),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             f"{label}\n{self._latest[key]:.0f}%")
            painter.save()
            painter.translate(_LABEL_WIDTH + _PADDING, top + 4)
            pen = painter.pen()
            pen.setWidthF(1.6)
            painter.setPen(pen)
            painter.drawPath(sparkline_path(self.series(key), graph_width, _ROW_HEIGHT - 8))
            painter.restore()

    def closeEvent(self, event) -> None:
        self.stop()
        super().closeEvent(event)


class NowPlayingWidget(BaseWidget):
    """
    「正在播放」一行字。來源可注入；查不到時保留上一則一小段時間，
    避免曲目換場的空檔讓字閃掉。
    A single "now playing" line. The source is injectable, and a blank reading
    keeps the previous text briefly so the line does not blink between tracks.
    """

    UPDATE_INTERVAL_MS = 2000
    KEEP_STALE_TICKS = 3

    def __init__(self, provider=None, prefix: str = "♪ ") -> None:
        front_engine_logger.info("[NowPlayingWidget] Init")
        super().__init__()
        self.opacity = 0.9
        self.prefix = str(prefix)
        self.text: str = ""
        self.text_color = QColor("#ffffff")
        self._provider = provider
        self._stale_ticks = 0
        self._font = QFont()
        self._font.setPointSize(12)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self.resize(320, 40)

    def set_provider(self, provider) -> None:
        self._provider = provider

    def start(self) -> None:
        self.refresh()
        self._timer.start(tier_interval(self.UPDATE_INTERVAL_MS, self.quality_tier))

    def stop(self) -> None:
        self._timer.stop()

    def apply_quality_tier(self) -> None:
        if self._timer.isActive():
            self._timer.start(tier_interval(self.UPDATE_INTERVAL_MS, self.quality_tier))

    def refresh(self) -> None:
        """問一次現在播什麼。"""
        value: Optional[str] = None
        if self._provider is not None:
            try:
                value = self._provider()
            except Exception:  # pragma: no cover - defensive around providers
                value = None
        text = str(value or "").strip()
        if text:
            self.text = text
            self._stale_ticks = 0
        elif self.text:
            self._stale_ticks += 1
            if self._stale_ticks >= self.KEEP_STALE_TICKS:
                self.text = ""
        self.update()

    def draw_content(self, painter: QPainter) -> None:
        if not self.text:
            return
        painter.setFont(self._font)
        painter.setPen(self.text_color)
        painter.drawText(self.rect(),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         f"{self.prefix}{self.text}")

    def closeEvent(self, event) -> None:
        self.stop()
        super().closeEvent(event)
