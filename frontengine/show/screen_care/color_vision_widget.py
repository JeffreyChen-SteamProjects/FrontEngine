"""
色覺模擬覆蓋層：抓一張畫面、套上色覺缺陷的轉換、再整片蓋回去。

這一層和其他覆蓋層不同：它必須是不透明的，因為「模擬看不清楚的顏色」沒辦法
用半透明疊色做到——得真的把底下的畫面重畫一次。畫面只在記憶體裡轉換，不存檔。

先前是「藏起自己、擷取、再顯示」每秒五次：整個螢幕跟著閃，而且藏起來那一刻
桌面合成器往往還沒更新，擷取到的是上一次的模擬結果，顏色越疊越偏、跳來跳去。
現在視窗設成不被擷取（WDA_EXCLUDEFROMCAPTURE），不必藏，由背景執行緒擷取與轉換。
做不到的平台改成靜止畫面：只在開始與改設定時拍一張。

A colour-vision overlay: read the screen, apply the deficiency transform, and
paint the result back over everything.

It is opaque, unlike the other overlays: simulating a colour deficiency cannot
be done by tinting, it needs the picture underneath redrawn. The picture is
transformed in memory and never saved.

It used to hide itself, grab and show itself again five times a second. The whole
screen flickered with it, and the desktop compositor had often not caught up with
the hiding, so the grab caught the previous simulation: the colours were
transformed twice, then three times, and jumped about. The window is now excluded
from capture instead and never hides, and a worker thread does the reading and
transforming. Where that is not available the layer is a still picture, taken when
it starts and when a setting changes.
"""
from __future__ import annotations

from typing import Optional

import numpy
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPainter, QPixmap

from frontengine.show.screen_care.screen_filter import ScreenCareOverlay
from frontengine.utils.color_vision.color_vision import (
    KIND_DEUTERANOPIA, clamp_severity, normalize_kind, simulate_array,
)
from frontengine.utils.color_vision.live_simulation import LiveSimulation
from frontengine.utils.color_vision.screen_source import open_source
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.power_mode.power_mode import tier_interval
from frontengine.utils.screen_privacy import capture_affinity

# The pause between frames. Reading and transforming one takes longer than this on a full-HD
# screen, so it is a floor that keeps the worker from spinning, not a frame rate.
REFRESH_INTERVAL_MS = 50
# Still mode: how long the compositor gets to take the hidden layer off the screen.
HIDE_SETTLE_MS = 150


def image_to_array(image: QImage) -> Optional[numpy.ndarray]:
    """
    QImage -> H x W x 3 的 uint8 陣列。每列可能有補齊位元組，所以要照
    bytesPerLine 切，不能直接 reshape。
    QImage to an H x W x 3 uint8 array. Rows can be padded, so slice by
    bytesPerLine rather than reshaping the raw buffer.
    """
    if image is None or image.isNull():
        return None
    converted = image.convertToFormat(QImage.Format.Format_RGB888)
    width, height, stride = converted.width(), converted.height(), converted.bytesPerLine()
    if width <= 0 or height <= 0:
        return None
    buffer = numpy.frombuffer(converted.constBits(), dtype=numpy.uint8, count=stride * height)
    return buffer.reshape((height, stride))[:, : width * 3].reshape(
        (height, width, 3)).copy()


def array_to_image(pixels: numpy.ndarray) -> Optional[QImage]:
    """H x W x 3 的 uint8 陣列 -> QImage（複製一份，不依賴呼叫端的緩衝區）。"""
    data = numpy.ascontiguousarray(pixels, dtype=numpy.uint8)
    if data.ndim != 3 or data.shape[2] != 3:
        return None
    height, width, _channels = data.shape
    image = QImage(data.tobytes(), width, height, width * 3, QImage.Format.Format_RGB888)
    return image.copy()


class ColorVisionWidget(ScreenCareOverlay):
    """
    色覺模擬層。擷取函式可注入，所以不需要真的螢幕也測得到轉換流程。
    """

    stays_while_paused = True
    # The control center's "hide from capture" must not undo the exclusion the live picture needs.
    needs_capture_exclusion = True

    # (BGRX frame) from the worker thread
    frame_ready = Signal(object)

    def __init__(self, kind: str = KIND_DEUTERANOPIA, severity: float = 1.0) -> None:
        front_engine_logger.info(f"[ColorVisionWidget] Init | kind={kind}")
        super().__init__()
        self.kind = normalize_kind(kind)
        self.severity = clamp_severity(severity)
        self.opacity = 1.0
        self.simulated: Optional[QPixmap] = None
        self._grabber = self._default_grabber
        self._exclude = capture_affinity.apply_to_widget
        self._open_source = open_source
        self._live: Optional[LiveSimulation] = None
        self._running = False
        self._retaking = False
        self._own_show = False             # this show was asked for here, with a fresh picture
        self.frame_ready.connect(self._show_frame, Qt.ConnectionType.QueuedConnection)
        # 這一層是不透明的：它要蓋掉底下的畫面，而不是疊在上面
        # This layer is opaque - it replaces what is underneath rather than
        # tinting it.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

    def _default_grabber(self, rect):  # pragma: no cover - needs a real screen
        screen = self.screen()
        if screen is None:
            return None
        origin = screen.geometry().topLeft()        # grabWindow counts from the screen's own corner
        return screen.grabWindow(0, rect.x() - origin.x(), rect.y() - origin.y(), rect.width(), rect.height())

    def set_grabber(self, grabber) -> None:
        """設定螢幕擷取函式（測試會換成假的）。"""
        self._grabber = grabber or self._default_grabber

    def set_capture_boundary(self, exclude, source_opener) -> None:
        """Inject how the window is excluded from capture and how the desktop is read (tests)."""
        self._exclude, self._open_source = exclude, source_opener

    @property
    def live(self) -> bool:
        """Whether the picture follows the screen; otherwise it is a still one."""
        return self._live is not None

    def set_simulation(self, kind: Optional[str] = None,
                       severity: Optional[float] = None) -> None:
        """換一種色覺類型或嚴重程度，立刻重畫。"""
        if kind is not None:
            self.kind = normalize_kind(kind)
        if severity is not None:
            self.severity = clamp_severity(severity)
        if self._live is not None:
            self._live.set_simulation(self.kind, self.severity)
        elif self._running:
            self.retake()
        else:
            self.refresh()

    def start(self) -> None:
        """Take the first picture while still hidden, show, then follow the screen if possible."""
        self._running = True
        if not self.isVisible():
            self.refresh()
            self._show_fresh()
        if self._exclude(self, True) and self._start_live():
            return
        if self.simulated is None:
            self.retake()

    def _start_live(self) -> bool:
        source = self._open_source(int(self.winId()))
        if source is None:
            return False
        # Opened here to learn whether it works; the worker opens its own on its thread.
        source.close()
        handle = int(self.winId())
        self._live = LiveSimulation(lambda: self._open_source(handle), self.frame_ready.emit,
                                    self._interval_seconds())
        self._live.set_simulation(self.kind, self.severity)
        self._live.start()
        return True

    def _interval_seconds(self) -> float:
        return tier_interval(REFRESH_INTERVAL_MS, self.quality_tier) / 1000.0

    def stop(self) -> None:
        self._running = False
        live, self._live = self._live, None
        if live is not None:
            live.stop()

    def apply_quality_tier(self) -> None:
        if self._live is not None:
            self._live.interval_seconds = self._interval_seconds()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._running or self._own_show:
            return
        # Changing window flags (locking overlays) makes a new native window: exclude that one too,
        # and read through its handle.
        if self._live is not None:
            self._live.stop()
            self._live = None
            if self._exclude(self, True) and self._start_live():
                return
            front_engine_logger.warning("[ColorVisionWidget] the new window cannot be excluded")
        # Still mode: what it last photographed is whatever was on screen before it was hidden.
        QTimer.singleShot(0, self, self.retake)

    def _show_fresh(self) -> None:
        self._own_show = True
        try:
            self.show()
        finally:
            self._own_show = False

    def _show_frame(self, frame: numpy.ndarray) -> None:
        if not self._running:
            return
        height, width = frame.shape[:2]
        image = QImage(frame.data, width, height, width * 4, QImage.Format.Format_RGB32)
        self.simulated = QPixmap.fromImage(image)
        self.update()

    def retake(self) -> None:
        """Still mode: step aside, give the compositor time to show it, take the picture, come back."""
        if self._retaking:
            return
        self._retaking = True
        was_visible = self.isVisible()
        self.setVisible(False)
        QTimer.singleShot(HIDE_SETTLE_MS, self, lambda: self._finish_retake(was_visible))

    def _finish_retake(self, was_visible: bool) -> None:
        self._retaking = False
        self.refresh()
        if was_visible and self._running:
            self._show_fresh()

    def refresh(self) -> None:
        """抓一次畫面、轉換、準備重畫。呼叫時這一層不能在畫面上，否則會拍到自己。
        Grab once, transform, repaint. The layer must not be on screen, or it photographs itself."""
        try:
            pixmap = self._grabber(self.geometry())
        except Exception as error:  # pragma: no cover - screen grab boundary
            front_engine_logger.warning(f"[ColorVisionWidget] grab failed: {error!r}")
            return
        if pixmap is None or pixmap.isNull():
            return
        pixels = image_to_array(pixmap.toImage())
        if pixels is None:
            return
        image = array_to_image(simulate_array(pixels, self.kind, self.severity))
        if image is not None:
            self.simulated = QPixmap.fromImage(image)
            self.update()

    def draw_content(self, painter: QPainter) -> None:
        if self.simulated is None or self.simulated.isNull():
            return
        painter.setOpacity(1.0)         # a replacement picture, never a blend with what it replaces
        painter.drawPixmap(self.rect(), self.simulated)

    def closeEvent(self, event) -> None:
        self.stop()
        super().closeEvent(event)
