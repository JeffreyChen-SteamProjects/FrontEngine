from PySide6.QtCore import QPoint
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QWidget


class MainWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.qimg = QImage("../test_using_melting.png")

    def paintEvent(self, paint_event):
        painter = QPainter(self)
        painter.setOpacity(0.20)
        # painter.drawImage(
        #     QRect(self.x(), self.y(), self.width(), self.height()),
        #     self.qimg)
        painter.drawImage(
            QPoint(
                int((self.x() + self.width()) / 2),
                int((self.y() + self.height()) / 2)
            ),
            self.qimg)
        painter.restore()
