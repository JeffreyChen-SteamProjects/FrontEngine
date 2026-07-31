"""
把截下來的一塊畫面釘在螢幕上。

區域截圖原本只能送到剪貼簿或存成檔案——想「一邊看著這段規格一邊改程式」的話，
得自己找一個看圖程式打開再想辦法讓它保持在最上層。釘選就是把中間那幾步拿掉。

和圖片覆蓋層的差別在來源與互動：圖片覆蓋層吃**檔案路徑**、點擊穿透；這個吃記憶體
裡的 `QPixmap`，而且要能拖、能縮放、能關掉——截下來的東西是拿來對照的，不是背景。

Pin a captured piece of screen on top.

Region capture could only reach the clipboard or a file: wanting to read a
specification while editing code meant opening an image viewer and finding a way
to keep it on top. Pinning removes the steps in between.

It differs from the image overlay in both source and behaviour: that one takes a
**file path** and passes clicks through, while this takes a `QPixmap` already in
memory and has to be draggable, resizable and closable - a capture is something
you refer to, not a backdrop.
"""
from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from frontengine.utils.logging.loggin_instance import front_engine_logger

MIN_PINNED_SIZE = 48
MAX_ZOOM = 4.0
MIN_ZOOM = 0.1
ZOOM_STEP = 1.1


def zoom_size(base: Tuple[int, int], zoom: float) -> Tuple[int, int]:
    """
    縮放後的大小，維持長寬比並夾在可用範圍內。

    純算術，所以縮放不必開視窗就能驗。下限存在的理由和複本一樣：縮到剩幾像素的
    圖片既拖不動也關不掉，等於卡在畫面上。
    The scaled size, keeping the aspect ratio and clamped to a usable range.

    Pure arithmetic, so zooming can be checked without a window. The floor is
    there for the same reason as the replica's: an image a few pixels across can
    be neither dragged nor closed, so it is simply stuck on screen.
    """
    width, height = base
    if width <= 0 or height <= 0:
        return (MIN_PINNED_SIZE, MIN_PINNED_SIZE)
    factor = max(MIN_ZOOM, min(MAX_ZOOM, float(zoom)))
    return (max(MIN_PINNED_SIZE, int(width * factor)),
            max(MIN_PINNED_SIZE, int(height * factor)))


def clamp_zoom(zoom: float) -> float:
    """把縮放倍率夾在可用範圍內。"""
    try:
        return max(MIN_ZOOM, min(MAX_ZOOM, float(zoom)))
    except (TypeError, ValueError):
        return 1.0


class PinnedImageWidget(QWidget):
    """釘在最上層的一張圖：可拖曳、可滾輪縮放、雙擊或 Escape 關閉。"""

    def __init__(self, pixmap: QPixmap, opacity_percent: int = 100,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool)
        self.setWindowTitle("FrontEngine")

        self.pixmap = pixmap if pixmap is not None else QPixmap()
        self.zoom = 1.0
        self._drag_origin: Optional[QPoint] = None
        self.setWindowOpacity(max(0.1, min(1.0, opacity_percent / 100.0)))

        base = (self.pixmap.width(), self.pixmap.height())
        front_engine_logger.info(f"[PinnedImageWidget] Init | size={base}")
        self.resize(*zoom_size(base, 1.0))

    def base_size(self) -> Tuple[int, int]:
        return (self.pixmap.width(), self.pixmap.height())

    def apply_zoom(self, zoom: float) -> None:
        """套用縮放倍率並跟著改變視窗大小。"""
        self.zoom = clamp_zoom(zoom)
        self.resize(*zoom_size(self.base_size(), self.zoom))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        if self.pixmap.isNull():
            return
        # 縮放時用平滑轉換：釘起來的多半是文字或介面截圖，鋸齒會直接讓它讀不了。
        # Smooth transformation: what gets pinned is usually text or an interface,
        # and aliasing makes exactly that unreadable.
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawPixmap(self.rect(), self.pixmap)

    def wheelEvent(self, event) -> None:
        steps = event.angleDelta().y() / 120.0
        if steps:
            self.apply_zoom(self.zoom * (ZOOM_STEP ** steps))
            event.accept()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_origin)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_origin = None
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        """雙擊關掉——沒有標題列，總得有一個看得懂的出口。"""
        self.close()
        event.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)
