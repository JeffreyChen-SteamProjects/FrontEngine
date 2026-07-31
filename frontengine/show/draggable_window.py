"""
可拖曳的置頂小視窗：釘選截圖與視窗複本共用的底座。

這兩者都是「拿來對照的東西」而不是背景，所以都需要同一套行為：沒有邊框、永遠在
最上層、可以拖到順手的位置、雙擊或 Escape 關掉。兩邊各寫一份的話，改了其中一個
的關閉方式，另一個就會變成另一種操作邏輯——而使用者不會知道為什麼。

A draggable always-on-top window: the base shared by the pinned capture and the
window replica.

Both are things you refer to rather than backdrops, so both need the same
behaviour: no frame, always on top, draggable somewhere convenient, closed with a
double-click or Escape. Written twice, changing how one of them closes would
quietly leave the other behaving differently, with nothing to explain why.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QWidget


class DraggableTopWindow(QWidget):
    """無邊框、置頂、可拖曳、雙擊或 Escape 關閉。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool)
        self.setWindowTitle("FrontEngine")
        self._drag_origin: Optional[QPoint] = None

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
        """
        雙擊關掉。沒有標題列就沒有右上角的叉，總得留一個看得懂的出口，否則使用者
        只能去工作管理員。
        Double-click closes. With no title bar there is no cross in the corner, and
        something covering the screen with no way out leaves only the task manager.
        """
        self.close()
        event.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)
