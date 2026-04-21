from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMessageBox, QMenu

from frontengine.show.window_helpers import apply_overlay_window_flags, load_overlay_icon
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class WebWidget(QWebEngineView):
    """
    WebWidget: 顯示網頁或本地 HTML 檔案的自訂元件
    WebWidget: A custom widget for displaying web pages or local HTML files
    """

    def __init__(self, url: str, is_file: bool = False):
        front_engine_logger.info(f"[WebWidget] Init | url={url}, is_file={is_file}")
        super().__init__()

        self.opacity: float = 0.2
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

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

        self.close_action = QAction("Close", self)
        self.close_action.triggered.connect(self.close)
        self.menu = QMenu(self)
        self.menu.addAction(self.close_action)

        load_overlay_icon(self)

    def contextMenuEvent(self, event):
        front_engine_logger.debug(f"[WebWidget] contextMenuEvent | event={event}")
        self.menu.popup(event.globalPos())

    def set_ui_variable(self, opacity: float = 0.2) -> None:
        front_engine_logger.info(f"[WebWidget] set_ui_variable | opacity={opacity}")
        self.opacity = opacity
        self.setWindowOpacity(opacity)

    def set_ui_window_flag(self, enable_input: bool = False, show_on_bottom: bool = False) -> None:
        front_engine_logger.info(
            f"[WebWidget] set_ui_window_flag | enable_input={enable_input}, show_on_bottom={show_on_bottom}"
        )
        if not enable_input:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        apply_overlay_window_flags(self, show_on_bottom=show_on_bottom, allow_input=enable_input)
