from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
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

        # 定期自動重新整理（適合網頁儀表板）/ Periodic auto-refresh (dashboards)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.reload)

        load_overlay_icon(self)

    def set_zoom(self, factor: float) -> None:
        front_engine_logger.info(f"[WebWidget] set_zoom | factor={factor}")
        try:
            self.setZoomFactor(max(0.25, min(5.0, float(factor))))
        except (TypeError, ValueError):
            pass

    def set_auto_refresh(self, seconds: int) -> None:
        """每 seconds 秒重新整理一次；<=0 表示停用。"""
        front_engine_logger.info(f"[WebWidget] set_auto_refresh | seconds={seconds}")
        try:
            interval = int(seconds)
        except (TypeError, ValueError):
            interval = 0
        if interval > 0:
            self._refresh_timer.start(interval * 1000)
        else:
            self._refresh_timer.stop()

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
