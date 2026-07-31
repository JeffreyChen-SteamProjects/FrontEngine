"""
視窗複本覆蓋層：一個小視窗，裡面是另一個視窗的即時畫面。

和其他覆蓋層不同，這一個**不能點擊穿透**：使用者要能把它拖到順手的位置、拉大縮小、
關掉。所以它是一個可以拖曳的無邊框視窗，而不是一層蓋在畫面上的東西。

A window replica overlay: a small window showing another window, live.

Unlike the other overlays this one must **not** pass clicks through: the user has
to be able to drag it somewhere convenient, resize it and close it. So it is a
draggable frameless window rather than a sheet laid over the screen.
"""
from __future__ import annotations

from typing import Optional

from frontengine.show.draggable_window import DraggableTopWindow
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.window_replica.dwm_thumbnail import (
    DEFAULT_REPLICA_WIDTH, MIN_REPLICA_SIZE, DwmThumbnail, available, crop_rect, fit_within,
)


class WindowReplicaWidget(DraggableTopWindow):
    """顯示另一個視窗即時畫面的小視窗。"""

    def __init__(self, source_handle: int, title: str = "",
                 opacity_percent: int = 100, parent: Optional[QWidget] = None,
                 crop: Optional[tuple] = None) -> None:
        front_engine_logger.info(f"[WindowReplicaWidget] Init | source={source_handle}")
        super().__init__(parent)
        self.setWindowTitle(title or "FrontEngine")
        self.setMinimumSize(MIN_REPLICA_SIZE, MIN_REPLICA_SIZE)

        self.source_handle = int(source_handle)
        self.source_title = title
        self.opacity_percent = max(1, min(100, int(opacity_percent)))
        # 裁切用比例存：來源視窗被調整大小時，框到的還是同一塊。
        # The crop is kept as fractions so it still points at the same part of
        # the source after that window is resized.
        self.crop = crop
        self.thumbnail = DwmThumbnail()

        self.resize(DEFAULT_REPLICA_WIDTH, int(DEFAULT_REPLICA_WIDTH * 9 / 16))

    def start(self) -> bool:
        """
        接上來源視窗並依它的長寬比調整大小。接不上就回 False，呼叫端不要把一個
        空視窗留在畫面上。
        Attach to the source and take its aspect ratio. False when it could not
        attach, so the caller does not leave an empty window on screen.
        """
        if not available():
            front_engine_logger.info("[WindowReplicaWidget] not supported on this platform")
            return False
        # 縮圖要接在「這個視窗的 handle」上，所以必須先讓它有 handle。
        # The thumbnail attaches to this window's handle, so it needs one first.
        self.show()
        if not self.thumbnail.register(int(self.winId()), self.source_handle):
            return False
        source_size = self.thumbnail.source_size()
        # 有裁切的話，長寬比要照框出來的那一塊算，不是照整個視窗算——否則框一條
        # 細長的聊天欄會得到一個又寬又空的複本。
        # With a crop the aspect ratio comes from the cropped part, not the whole
        # window: cropping a narrow chat column would otherwise give a wide,
        # mostly empty replica.
        cropped = crop_rect(source_size, self.crop)
        if cropped is not None:
            source_size = (cropped[2] - cropped[0], cropped[3] - cropped[1])
        width, height = fit_within(source_size, (DEFAULT_REPLICA_WIDTH,
                                                 int(DEFAULT_REPLICA_WIDTH * 9 / 16)))
        self.resize(width, height)
        self._refresh()
        return True

    def _refresh(self) -> None:
        self.thumbnail.update(self.width(), self.height(),
                              opacity=int(self.opacity_percent * 255 / 100),
                              source_rect=crop_rect(self.thumbnail.source_size(), self.crop))

    def set_crop(self, crop: Optional[tuple]) -> None:
        """換一塊要顯示的區域（None 表示整個視窗）。"""
        self.crop = crop
        self._refresh()

    def set_opacity_percent(self, percent: int) -> None:
        self.opacity_percent = max(1, min(100, int(percent)))
        self._refresh()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh()

    def paintEvent(self, event) -> None:
        # DWM 把縮圖合成上來之前，先鋪一層不透明底色。少了這一步，來源還沒畫上來的
        # 那一瞬間會透出後面的東西，看起來像破圖。
        # An opaque backing before DWM composites the thumbnail. Without it the
        # moment before the source arrives shows whatever is behind, which reads
        # as a rendering fault.
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))


    def closeEvent(self, event) -> None:
        # 縮圖是系統資源，視窗沒了也不會自己消失。從標題列以外的任何路徑關閉時
        # closeEvent 是唯一會被呼叫到的地方，所以收尾放這裡。
        # The thumbnail is a system resource and does not go away with the
        # window. closeEvent is the one place every close path reaches.
        self.thumbnail.unregister()
        super().closeEvent(event)
