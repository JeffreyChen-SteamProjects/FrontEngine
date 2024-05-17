import sys

from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap, Qt
from PySide6.QtWidgets import QWidget, QApplication, QMainWindow, QGridLayout
from qt_material import QtStyleTools

from frontengine.show.particle.particle_scene import ParticleGraphicScene
from frontengine.show.scene.extend_graphic_view import ExtendGraphicView


class ParticleWidget(QWidget):

    def __init__(self, pixmap: QPixmap, particle_size: QSize, particle_direction: str):
        super().__init__()
        self.pixmap = pixmap
        self.pixmap.scaled(particle_size, Qt.AspectRatioMode.KeepAspectRatio)
        self.particle_view = ExtendGraphicView()
        self.particle_scene = ParticleGraphicScene(self.pixmap, particle_direction)
        self.particle_view.setScene(self.particle_scene)
        self.grid_layout = QGridLayout()
        self.grid_layout.addWidget(self.particle_view, 0, 0, -1, -1)
        self.setLayout(self.grid_layout)


class TestUI(QMainWindow, QtStyleTools):

    def __init__(self):
        super().__init__()
        self.main_widget = ParticleWidget()
        self.setCentralWidget(self.main_widget)
        self.showMaximized()


if __name__ == "__main__":
    main_app = QApplication(sys.argv)
    window = TestUI()
    sys.exit(main_app.exec())
