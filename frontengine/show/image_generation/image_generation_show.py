from pathlib import Path

import PySide6
from PySide6.QtGui import QPixmap, QAction, Qt
from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QFileDialog, QMenu

from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ImageGenerateShow(QWidget):

    def __init__(self, pixmap: QPixmap, title: str):
        super().__init__()
        self.setWindowTitle(title)
        self.pixmap = pixmap
        self.label = QLabel()
        self.label.setPixmap(pixmap)
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.addWidget(self.label)
        self.setLayout(self.grid_layout)

        # Menubar
        self.menu = QMenu(self)
        self.save_image_action = QAction(language_wrapper.language_word_dict.get("save_generation_image"))
        self.save_image_action.triggered.connect(self.save_image)
        self.menu.addAction(self.save_image_action)

    def save_image(self):
        file_path = QFileDialog().getSaveFileName(
            parent=self,
            dir=str(Path.cwd()),
            filter="Images (*.png;*.jpg;*.webp)"
        )[0]
        file_path = Path(file_path)
        if file_path.is_file():
            self.pixmap.save(str(file_path))

    def mousePressEvent(self, event: PySide6.QtGui.QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self.menu.move(self.x() + event.x(), self.y() + event.y())
            self.menu.show()
        super().mousePressEvent(event)
