import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWebEngineWidgets import QWebEngineView


class WebWidget(QWebEngineView):

    def __init__(self, url: str, opacity: float = 0.2):
        super().__init__()
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.load(url)
        self.setWindowOpacity(opacity)
        # Set Icon
        self.icon_path = Path(os.getcwd() + "/je_driver_icon.ico")
