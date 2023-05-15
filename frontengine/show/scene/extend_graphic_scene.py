from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem


class ExtendGraphicScene(QGraphicsScene):

    def __init__(self):
        super().__init__()
        pixmap = self.addPixmap(QPixmap().fromImage(QImage(r"C:\Users\JeffreyChen\Desktop\test.png")))
