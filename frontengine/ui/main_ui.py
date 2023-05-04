import sys

from PySide6.QtWidgets import QMainWindow, QApplication, QGridLayout

from frontengine.show.web.webview import WebWidget


class FrontEngineMainUI(QMainWindow):

    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.test_widget = WebWidget()
        self.test_widget.showMaximized()


def start_front_engine():
    new_editor = QApplication(sys.argv)
    window = FrontEngineMainUI()
    window.showMaximized()
    sys.exit(new_editor.exec())


start_front_engine()
