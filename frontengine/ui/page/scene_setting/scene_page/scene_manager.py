from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QPlainTextEdit


class SceneManagerUI(QWidget):

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # Json plaintext
        self.json_plaintext = QPlainTextEdit()
        self.json_plaintext.setReadOnly(True)
        self.json_plaintext.appendPlainText("{}")
        # Add to layout
        self.grid_layout.addWidget(self.json_plaintext, 0, 0, -1, -1)
        self.setLayout(self.grid_layout)
