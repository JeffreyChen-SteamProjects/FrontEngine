"""
凍結畫面：把某個螢幕現在的樣子拍下來，鋪滿那個螢幕蓋在最上層。

用途是講解的節奏控制——切去別的地方操作、開別的檔案、把東西準備好，而投影出去
或被分享的那個畫面停在原地。

**一定要能在看不見主視窗的情況下解除。** 凍結之後畫面上就只剩那張靜止圖，
FrontEngine 的視窗在它後面，按鈕點不到。所以解除的出口有三個：Escape、雙擊、
以及全域快速鍵；三個都不通的話，使用者只剩工作管理員。

Freeze the screen: photograph a display as it is now and cover that display with
the picture.

It is for pacing an explanation - stepping away to open something, getting the
next thing ready - while what is projected or shared stays where it was.

**Unfreezing must work without seeing the main window.** Once frozen, the still
image is all there is; FrontEngine's own window is behind it and its buttons
cannot be clicked. So there are three ways out - Escape, a double-click, and the
global shortcut - because with none of them the user is left with the task
manager.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap, QScreen
from PySide6.QtWidgets import QWidget

from frontengine.utils.logging.loggin_instance import front_engine_logger


def capture_screen(screen: Optional[QScreen]) -> QPixmap:
    """
    把整個螢幕拍成一張圖。拍不到就回傳空的 QPixmap，呼叫端負責不要顯示它。
    Photograph a whole screen. An unavailable screen gives a null pixmap and the
    caller is responsible for not showing it.
    """
    if screen is None:
        return QPixmap()
    try:
        geometry = screen.geometry()
        return screen.grabWindow(0, 0, 0, geometry.width(), geometry.height())
    except Exception as error:  # pragma: no cover - platform boundary
        front_engine_logger.warning(f"[Freeze] capture failed: {error!r}")
        return QPixmap()


class FreezeWidget(QWidget):
    """一張靜止的螢幕畫面，鋪滿目標螢幕。"""

    def __init__(self, pixmap: QPixmap, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        # 不用 Tool：Tool 視窗在部分平台不吃鍵盤焦點，那樣 Escape 就按不掉了。
        # Not a Tool window: on some platforms those do not take keyboard focus,
        # which is exactly how Escape would stop working.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("FrontEngine")
        self.pixmap = pixmap if pixmap is not None else QPixmap()
        front_engine_logger.info(
            f"[FreezeWidget] Init | size=({self.pixmap.width()}, {self.pixmap.height()})")

    def show_on(self, screen: Optional[QScreen]) -> None:
        """在指定螢幕上鋪滿顯示，並取得鍵盤焦點好讓 Escape 有效。"""
        if screen is not None:
            self.setScreen(screen)
            self.setGeometry(screen.geometry())
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def paintEvent(self, event) -> None:
        if self.pixmap.isNull():
            return
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.pixmap)

    def mouseDoubleClickEvent(self, event) -> None:
        self.close()
        event.accept()

    def keyPressEvent(self, event) -> None:
        # 任何鍵都解除，不只是 Escape。畫面被一張靜止圖蓋住的時候，使用者最可能做的
        # 就是「隨便按一個鍵看看」，那時候應該要有反應。
        # Any key unfreezes, not only Escape. Faced with a screen that has stopped
        # responding, pressing something at random is the first thing anyone tries,
        # and it should work.
        self.close()
        event.accept()
