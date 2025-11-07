import os
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMessageBox, QMenu

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class WebWidget(QWebEngineView):
    """
    WebWidget: 顯示網頁或本地 HTML 檔案的自訂元件
    WebWidget: A custom widget for displaying web pages or local HTML files
    """

    def __init__(self, url: str, is_file: bool = False):
        """
        初始化 WebWidget
        Initialize WebWidget

        :param url: 網址或檔案路徑 / URL or file path
        :param is_file: 是否為本地檔案 / Whether the input is a local file
        """
        front_engine_logger.info(f"[WebWidget] Init | url={url}, is_file={is_file}")
        super().__init__()

        self.opacity: float = 0.2
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # --- 載入網頁或本地檔案 / Load web page or local file ---
        if not is_file:
            self.load(url)
        else:
            self.web_url = Path(url)
            if self.web_url.exists() and self.web_url.is_file():
                source = QUrl.fromLocalFile(str(self.web_url))
                front_engine_logger.info(f"[WebWidget] Loading local file: {self.web_url}")
                self.load(source)
            else:
                front_engine_logger.error(f"[WebWidget] File not found: {url}")
                message_box = QMessageBox(self)
                message_box.setText(
                    language_wrapper.language_word_dict.get("webview_message_box_text")
                )
                message_box.show()

        # --- 設定右鍵選單 / Setup context menu ---
        self.close_action = QAction("Close", self)
        self.close_action.triggered.connect(self.close)
        self.menu = QMenu(self)
        self.menu.addAction(self.close_action)

        # --- 設定 Icon / Set window icon ---
        self.icon_path = Path(os.getcwd()) / "je_driver_icon.ico"
        if self.icon_path.exists() and self.icon_path.is_file():
            self.setWindowIcon(QIcon(str(self.icon_path)))

    def contextMenuEvent(self, event):
        """
        自訂右鍵選單事件
        Custom context menu event
        """
        front_engine_logger.debug(f"[WebWidget] contextMenuEvent | event={event}")
        self.menu.popup(event.globalPos())

    def set_ui_variable(self, opacity: float = 0.2) -> None:
        """
        設定透明度
        Set opacity
        """
        front_engine_logger.info(f"[WebWidget] set_ui_variable | opacity={opacity}")
        self.opacity = opacity
        self.setWindowOpacity(opacity)

    def set_ui_window_flag(self, enable_input: bool = False, show_on_bottom: bool = False) -> None:
        """
        設定視窗旗標
        Set window flags
        """
        front_engine_logger.info(
            f"[WebWidget] set_ui_window_flag | enable_input={enable_input}, show_on_bottom={show_on_bottom}"
        )

        if not enable_input:
            self.setWindowFlag(Qt.WindowType.WindowTransparentForInput)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)

        if show_on_bottom:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnBottomHint)
        else:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

    def mousePressEvent(self, event) -> None:
        front_engine_logger.debug(f"[WebWidget] mousePressEvent | button={event.button()}")
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        front_engine_logger.debug(f"[WebWidget] mouseDoubleClickEvent | event={event}")
        super().mouseDoubleClickEvent(event)

    def mouseGrabber(self) -> None:
        front_engine_logger.debug("[WebWidget] mouseGrabber")
        super().mouseGrabber()