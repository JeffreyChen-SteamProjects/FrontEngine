from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QLabel, QGridLayout


class ImageGenerateShow(QWidget):

    def __init__(self, pixmap: QPixmap):
        super().__init__()
        self.label = QLabel()
        self.label.setPixmap(pixmap)
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.addWidget(self.label)
        self.setLayout(self.grid_layout)
