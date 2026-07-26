"""
區域截圖：拖出一塊範圍，放開後把那塊畫面抓下來，可以存檔或複製到剪貼簿，
也可以直接交給塗鴉層繼續標註。

Region capture: drag out an area, and on release grab it - to a file, to the
clipboard, or straight into the annotation layer to mark up.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen, QPixmap

from frontengine.show.base_widget import BaseWidget
from frontengine.show.window_helpers import apply_overlay_window_flags
from frontengine.utils.logging.loggin_instance import front_engine_logger

MIN_CAPTURE_SIZE = 4
_DIM_COLOR = QColor(0, 0, 0, 110)
_EDGE_COLOR = "#4dd0e1"


def normalize_rect(start: QPoint, end: QPoint) -> QRect:
    """
    把兩個角落整理成正的矩形（不管往哪個方向拖）。
    Two corners to a positive rectangle, whichever way the drag went.
    """
    left, right = sorted((int(start.x()), int(end.x())))
    top, bottom = sorted((int(start.y()), int(end.y())))
    return QRect(left, top, right - left, bottom - top)


def is_usable(rect: QRect) -> bool:
    """太小的框（多半是誤點）不算一次截圖。"""
    return rect.width() >= MIN_CAPTURE_SIZE and rect.height() >= MIN_CAPTURE_SIZE


def safe_capture_path(folder: str, name: str) -> Optional[Path]:
    """
    組出儲存路徑並擋掉路徑穿越：檔名只取最後一段，且結果必須仍在資料夾底下。
    Build the save path and refuse path traversal: only the final component of
    the name is used, and the result must still sit inside the folder.
    """
    try:
        base = Path(folder).resolve()
        candidate = (base / Path(str(name)).name).resolve()
    except (OSError, ValueError):
        return None
    if base != candidate.parent:
        front_engine_logger.warning(f"[RegionCapture] refusing path outside {base}: {name!r}")
        return None
    return candidate


class RegionCaptureWidget(BaseWidget):
    """
    全螢幕的截圖框選層：按住拖曳畫出範圍，放開就擷取。擷取函式與完成後的
    處理都可注入，所以整個流程不需要真的螢幕也測得到。
    """

    def __init__(self, on_captured: Optional[Callable[[QPixmap, QRect], None]] = None) -> None:
        front_engine_logger.info("[RegionCaptureWidget] Init")
        super().__init__()
        self.opacity = 1.0
        self.overlay_lockable = False
        self.origin: Optional[QPoint] = None
        self.current: Optional[QPoint] = None
        self.captured: Optional[QPixmap] = None
        self._on_captured = on_captured
        self._grabber = self._default_grabber
        apply_overlay_window_flags(self, show_on_bottom=False, allow_input=True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    @staticmethod
    def _default_grabber(rect: QRect):  # pragma: no cover - needs a real screen
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return None
        return screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())

    def set_grabber(self, grabber) -> None:
        self._grabber = grabber or self._default_grabber

    def selection(self) -> Optional[QRect]:
        """目前框出來的範圍；還沒開始拖就是 None。"""
        if self.origin is None or self.current is None:
            return None
        return normalize_rect(self.origin, self.current)

    # --- interaction -----------------------------------------------------
    def begin(self, point: QPoint) -> None:
        self.origin = QPoint(point)
        self.current = QPoint(point)
        self.update()

    def extend(self, point: QPoint) -> None:
        if self.origin is not None:
            self.current = QPoint(point)
            self.update()

    def finish(self, point: QPoint) -> Optional[QPixmap]:
        """
        放開滑鼠：框太小就當作取消，否則擷取那塊畫面並回傳。
        Releasing the mouse: too small counts as a cancel, otherwise grab that
        part of the screen and hand it back.
        """
        self.extend(point)
        rect = self.selection()
        self.origin = self.current = None
        if rect is None or not is_usable(rect):
            self.update()
            return None
        try:
            pixmap = self._grabber(rect)
        except Exception as error:  # pragma: no cover - screen grab boundary
            front_engine_logger.warning(f"[RegionCaptureWidget] grab failed: {error!r}")
            pixmap = None
        if pixmap is None or pixmap.isNull():
            self.update()
            return None
        self.captured = pixmap
        if self._on_captured is not None:
            self._on_captured(pixmap, rect)
        self.update()
        return pixmap

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.begin(event.position().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        self.extend(event.position().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.finish(event.position().toPoint())
            self.close()
        super().mouseReleaseEvent(event)

    # --- outputs ---------------------------------------------------------
    def copy_to_clipboard(self) -> bool:
        """把剛擷取的畫面放進剪貼簿。"""
        if self.captured is None or self.captured.isNull():
            return False
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:  # pragma: no cover - no clipboard at all
            return False
        clipboard.setPixmap(self.captured)
        return True

    def save_to(self, folder: str, name: str) -> Optional[str]:
        """存成檔案並回傳實際路徑；沒有畫面或路徑不合法時回傳 None。"""
        if self.captured is None or self.captured.isNull():
            return None
        path = safe_capture_path(folder, name)
        if path is None:
            return None
        if not self.captured.save(str(path)):
            front_engine_logger.warning(f"[RegionCaptureWidget] save failed: {path}")
            return None
        front_engine_logger.info(f"[RegionCaptureWidget] saved | {path}")
        return str(path)

    # --- painting --------------------------------------------------------
    def draw_content(self, painter: QPainter) -> None:
        rect = self.selection()
        painter.fillRect(self.rect(), _DIM_COLOR)
        if rect is None or rect.isEmpty():
            return
        # 框內回復原本亮度，框線標出範圍
        # Clear the selection back to full brightness and outline it.
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(rect, Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setPen(QPen(QColor(_EDGE_COLOR), 2))
        painter.drawRect(rect)
