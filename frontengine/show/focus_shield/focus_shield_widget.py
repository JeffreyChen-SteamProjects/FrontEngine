"""
專注用的兩種遮罩：
  - DimBackgroundWidget：把作用中視窗以外的地方壓暗，視線自然留在手上的工作
  - DistractionMaskWidget：蓋住指定的螢幕區域（工作列、通知角落）
兩者都是點擊穿透的，所以被遮住的地方仍然可以正常點擊。

Two focus masks: one dims everything except the active window so your eye stays
on the work, the other covers a chosen strip of the screen (the taskbar, a
notification corner). Both pass clicks through, so what is covered still works.
"""
from __future__ import annotations

import sys
from typing import List, Optional, Tuple

from PySide6.QtCore import QRect, QTimer
from PySide6.QtGui import QColor, QPainter

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.focus_shield.focus_shield import (
    REGION_BOTTOM, clamp_percent, mask_rect, surrounding_rects,
)
from frontengine.utils.logging.loggin_instance import front_engine_logger

DEFAULT_DIM = 45


def active_window_rect() -> Optional[Tuple[int, int, int, int]]:
    """
    回傳目前作用中視窗的 (x, y, w, h)；取不到或非 Windows 回傳 None
    （其他平台會退化成「整片壓暗」，仍然可用）。
    The active window's rectangle, or None off Windows — where the dimmer simply
    shades the whole screen instead.
    """
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
        return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.debug(f"[focus_shield] active window unavailable: {error!r}")
        return None


class DimBackgroundWidget(BaseWidget):
    """
    背景變暗：只有作用中視窗保持原樣，其餘壓暗；視窗換了會自動跟上。
    """

    REFRESH_MS = 250

    def __init__(self, dim: int = DEFAULT_DIM) -> None:
        front_engine_logger.info(f"[DimBackgroundWidget] Init | dim={dim}")
        super().__init__()
        self.opacity = 1.0
        self.dim = clamp_percent(dim, DEFAULT_DIM)
        self.shaded: List[Tuple[int, int, int, int]] = []
        self._window_provider = active_window_rect
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)

    def set_window_provider(self, provider) -> None:
        """注入作用中視窗來源（測試用）。"""
        self._window_provider = provider

    def set_dim(self, dim: int) -> None:
        self.dim = clamp_percent(dim, DEFAULT_DIM)
        self.update()

    def start_following(self, interval_ms: int = REFRESH_MS) -> None:
        self.refresh()
        self._timer.start(max(50, int(interval_ms)))

    def screen_rect(self) -> Tuple[int, int, int, int]:
        geometry = self.geometry()
        return (geometry.x(), geometry.y(), geometry.width(), geometry.height())

    def _to_logical(self, rect: Optional[Tuple[int, int, int, int]]):
        """
        把 Win32 的視窗矩形換算成 Qt 的邏輯座標。GetWindowRect 給的是實體像素，
        screen_rect() 給的是邏輯像素，顯示縮放不是 100% 時兩者對不起來：在 150%
        的螢幕上，最大化的視窗會算成比整個螢幕還大，結果一塊都不壓暗。
        Convert a Win32 window rect into Qt's logical coordinates. GetWindowRect
        reports physical pixels while screen_rect() is logical, and the two
        disagree at any scaling other than 100%: on a 150% display a maximised
        window measures larger than the whole screen, so nothing gets dimmed.
        """
        if rect is None:
            return None
        ratio = self.devicePixelRatio() or 1.0
        if ratio == 1.0:
            return rect
        return tuple(int(round(value / ratio)) for value in rect)

    def refresh(self) -> None:
        """重新計算要壓暗的區塊。"""
        try:
            active = self._window_provider()
        except Exception:  # pragma: no cover - defensive around providers
            active = None
        active = self._to_logical(active)
        rects = surrounding_rects(self.screen_rect(), active)
        origin_x, origin_y = self.x(), self.y()
        # 換算成本視窗的座標系 / Convert to this widget's own coordinates
        self.shaded = [(x - origin_x, y - origin_y, w, h) for x, y, w, h in rects]
        self.update()

    def draw_content(self, painter: QPainter) -> None:
        shade = QColor(0, 0, 0, int(255 * self.dim / 100.0))
        for x, y, width, height in self.shaded:
            painter.fillRect(QRect(x, y, width, height), shade)

    def closeEvent(self, event) -> None:
        if self._timer.isActive():
            self._timer.stop()
        super().closeEvent(event)


class DistractionMaskWidget(BaseWidget):
    """
    干擾遮罩：把螢幕的某個區域（預設底部，正好蓋住工作列）以不透明色蓋掉。
    """

    def __init__(self, region: str = REGION_BOTTOM, percent: int = 6,
                 color: str = "#101010") -> None:
        front_engine_logger.info(
            f"[DistractionMaskWidget] Init | region={region}, percent={percent}")
        super().__init__()
        self.opacity = 1.0
        # 這一層是拿來遮住東西的，分享畫面時必須留在擷取結果裡
        # This layer exists to cover something, so it stays in the capture.
        self.keep_in_capture = True
        self.region = region
        self.percent = clamp_percent(percent)
        self.mask_color = QColor(color) if QColor(color).isValid() else QColor("#101010")

    def geometry_for(self, screen_rect: Tuple[int, int, int, int]) -> QRect:
        """算出這個遮罩該放在哪裡、多大。"""
        x, y, width, height = mask_rect(screen_rect, self.region, self.percent)
        return QRect(x, y, width, height)

    def set_region(self, region: Optional[str] = None, percent: Optional[int] = None) -> None:
        if region is not None:
            self.region = region
        if percent is not None:
            self.percent = clamp_percent(percent)

    def draw_content(self, painter: QPainter) -> None:
        painter.fillRect(self.rect(), self.mask_color)
