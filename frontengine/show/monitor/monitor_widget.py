"""
系統監控覆蓋層：把 CPU／記憶體／磁碟／電池／網路流量的近況畫成小折線圖，
數字疊在圖上。平均值看不出卡頓，折線可以——這也是硬體 OSD 常見的做法。

百分比與速率兩種線分開處理：百分比的縱軸固定 0~100，速率沒有天花板，
所以縱軸取視窗內的最大值（並給一個下限，免得閒置時把雜訊放大成滿格）。

A system monitor overlay: recent CPU, memory, disk, battery and network history
as small sparklines with the current number on top. An average hides a stall; a
line does not - which is why hardware OSDs draw one.

Percentage and rate lines scale differently: a percentage axis is fixed at
0..100, while a throughput rate has no ceiling, so its axis follows the window's
own peak - with a floor, or idle noise would be magnified to full scale.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, Dict, Iterable, List, Optional, Sequence, Tuple

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.power_mode.power_mode import tier_interval
from frontengine.utils.system_stats.system_stats import format_bytes, system_stats

DEFAULT_HISTORY = 60
MIN_HISTORY = 10
MAX_HISTORY = 600
UPDATE_INTERVAL_MS = 1000

KIND_PERCENT = "percent"
KIND_RATE = "rate"

# 每條線：(system_stats 的欄位, 顯示名稱, 顏色, 種類)
# Each line: (key in system_stats, label, colour, kind).
LINES: Tuple[Tuple[str, str, str, str], ...] = (
    ("cpu", "CPU", "#4dd0e1", KIND_PERCENT),
    ("ram", "RAM", "#ffb74d", KIND_PERCENT),
    ("disk", "DISK", "#81c784", KIND_PERCENT),
    ("battery", "BATT", "#ba68c8", KIND_PERCENT),
    ("down_bytes", "DOWN", "#64b5f6", KIND_RATE),
    ("up_bytes", "UP", "#e57373", KIND_RATE),
)
LINE_BY_KEY: Dict[str, Tuple[str, str, str, str]] = {line[0]: line for line in LINES}
# 預設維持原本的三條，不會有人一升級就多出兩條沒要求過的線
# The original three stay the default: nobody upgrades into two lines they never asked for.
DEFAULT_LINES: Tuple[str, ...] = ("cpu", "ram", "disk")
_ROW_HEIGHT = 34
# 標籤欄要放得下最寬的讀數。百分比是「42%」，速率是「1.2MB/s」——
# 原本的 46px 是照百分比抓的，速率會被裁掉。
# The label column has to fit the widest reading. A percentage is "42%", a rate
# is "1.2MB/s"; the original 46px was sized for the former and clipped the latter.
_LABEL_WIDTH = 64
_PADDING = 6
# 速率縱軸的下限（64KB/s）。完全沒有流量時若照視窗最大值縮放，
# 幾百 bytes 的背景雜訊會被畫成滿格的尖峰。
# Floor for the rate axis (64KB/s). Scaling to the window peak while idle would
# draw a few hundred bytes of background chatter as a full-height spike.
_RATE_FLOOR = 64 * 1024.0


def clamp_history(value, fallback: int = DEFAULT_HISTORY) -> int:
    """歷史長度夾在畫得出來的範圍。"""
    try:
        return max(MIN_HISTORY, min(MAX_HISTORY, int(value)))
    except (TypeError, ValueError):
        return fallback


def normalize_lines(keys, fallback: Sequence[str] = DEFAULT_LINES) -> Tuple[str, ...]:
    """
    整理要顯示哪幾條線：只留認得的欄位、去重、保持 LINES 的順序。
    全部都不認得就退回預設，因為一個沒有任何線的監控視窗只是一塊空方框。
    Tidy the requested lines: known keys only, de-duplicated, in LINES order.
    Nothing recognised falls back to the default - a monitor with no lines at
    all is just an empty box.
    """
    if isinstance(keys, str) or not isinstance(keys, Iterable):
        return tuple(fallback)
    wanted = {str(key) for key in keys}
    chosen = tuple(key for key, _label, _color, _kind in LINES if key in wanted)
    return chosen or tuple(fallback)


def stat_percent(stats: Dict[str, object], key: str) -> Optional[float]:
    """
    取出某個百分比欄位並夾在 0~100；還沒有讀數（例如第一次取樣的 CPU）
    回傳 None，讓折線知道「這一刻沒有資料」而不是畫成 0。
    Pull a percentage field and clamp it to 0..100. A field with no reading yet
    - CPU on the very first sample - gives None, so the line can tell "no data"
    apart from "zero".
    """
    value = stats.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return max(0.0, min(100.0, float(value)))


def stat_rate(stats: Dict[str, object], key: str) -> Optional[float]:
    """
    取出某個速率欄位（bytes/s）。沒有上限所以不夾，但負數沒有意義，當成沒讀到。
    Pull a rate field (bytes per second). No ceiling to clamp against, but a
    negative rate is meaningless, so it counts as no reading.
    """
    value = stats.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return float(value) if value >= 0 else None


def stat_for(stats: Dict[str, object], key: str) -> Optional[float]:
    """依這條線的種類取值。"""
    line = LINE_BY_KEY.get(key)
    if line is None:
        return None
    return stat_rate(stats, key) if line[3] == KIND_RATE else stat_percent(stats, key)


def rate_scale(values: Iterable[float], floor: float = _RATE_FLOOR) -> float:
    """速率折線的縱軸上限：視窗內的最大值，但不低於 floor。"""
    peak = max((float(value) for value in values if value is not None), default=0.0)
    return max(peak, floor)


def format_row_value(key: str, value: float) -> str:
    """一條線目前的讀數要怎麼寫：百分比加 %，速率寫成 1.2MB/s。"""
    line = LINE_BY_KEY.get(key)
    if line is not None and line[3] == KIND_RATE:
        return f"{format_bytes(value)}/s"
    return f"{value:.0f}%"


def sparkline_path(values: List[float], width: float, height: float,
                   maximum: float = 100.0) -> QPainterPath:
    """
    把一串數值畫成一條折線（左舊右新），縱軸上限為 maximum。
    少於兩點時回傳空路徑。
    A polyline over the values, oldest on the left, scaled against `maximum`.
    Fewer than two points gives an empty path.
    """
    path = QPainterPath()
    if len(values) < 2 or width <= 0 or height <= 0 or maximum <= 0:
        return path
    step = width / (len(values) - 1)
    for index, value in enumerate(values):
        clamped = max(0.0, min(float(maximum), float(value)))
        point_y = height - (clamped / float(maximum)) * height
        if index == 0:
            path.moveTo(0.0, point_y)
        else:
            path.lineTo(index * step, point_y)
    return path


class SystemMonitorWidget(BaseWidget):
    """
    系統監控小圖。統計來源可注入（正式用 system_stats，測試餵假資料）。
    """

    def __init__(self, history: int = DEFAULT_HISTORY, stats_provider=None,
                 lines: Sequence[str] = DEFAULT_LINES) -> None:
        front_engine_logger.info(f"[SystemMonitorWidget] Init | history={history}")
        super().__init__()
        self.history_length = clamp_history(history)
        self.opacity = 0.9
        self._stats_provider = stats_provider or system_stats
        self.lines: Tuple[str, ...] = normalize_lines(lines)
        self._series: Dict[str, Deque[float]] = {
            key: deque(maxlen=self.history_length) for key, _label, _color, _kind in LINES
        }
        self._latest: Dict[str, float] = dict.fromkeys(
            (key for key, _label, _color, _kind in LINES), 0.0)
        self._font = QFont()
        self._font.setPointSize(9)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.sample)
        self.resize(240, self._preferred_height())

    def _preferred_height(self) -> int:
        return _ROW_HEIGHT * max(1, len(self.lines)) + _PADDING * 2

    def set_lines(self, keys: Sequence[str]) -> None:
        """
        改變要顯示哪幾條線並跟著調整高度。歷史值全部留著——使用者把網路那條
        關掉再打開時，看到的應該是這段時間發生的事，不是一條從零開始的線。
        Change which lines are shown and resize to match. Every series keeps its
        history: turning the network line off and on again should show what
        happened meanwhile, not restart from zero.
        """
        self.lines = normalize_lines(keys)
        self.resize(self.width(), self._preferred_height())
        self.update()

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
        for key, _label, _color, _kind in LINES:
            value = stat_for(stats, key)
            if value is None:
                # 讀不到就沿用上一筆，折線不會憑空掉到 0
                # Nothing to read: carry the last value so the line does not dive to 0.
                value = self._latest.get(key, 0.0)
            self._series[key].append(value)
            self._latest[key] = value
        self.update()

    def axis_maximum(self, key: str) -> float:
        """這條線的縱軸上限：百分比固定 100，速率跟著視窗內的最大值。"""
        line = LINE_BY_KEY.get(key)
        if line is not None and line[3] == KIND_RATE:
            return rate_scale(self._series.get(key, ()))
        return 100.0

    def draw_content(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setFont(self._font)
        graph_width = max(10, self.width() - _LABEL_WIDTH - _PADDING * 2)
        for row, key in enumerate(self.lines):
            _key, label, color, _kind = LINE_BY_KEY[key]
            top = _PADDING + row * _ROW_HEIGHT
            painter.setPen(QColor(color))
            painter.drawText(QRectF(_PADDING, top, _LABEL_WIDTH, _ROW_HEIGHT),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             f"{label}\n{format_row_value(key, self._latest[key])}")
            painter.save()
            painter.translate(_LABEL_WIDTH + _PADDING, top + 4)
            pen = painter.pen()
            pen.setWidthF(1.6)
            painter.setPen(pen)
            painter.drawPath(sparkline_path(self.series(key), graph_width, _ROW_HEIGHT - 8,
                                            self.axis_maximum(key)))
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
