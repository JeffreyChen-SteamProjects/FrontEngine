from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QMessageBox, QSlider, QLineEdit, QPushButton, QCheckBox,
    QComboBox, QPlainTextEdit,
)

from frontengine.show.web.webview import WebWidget
from frontengine.ui.page.utils import (
    apply_checkbox_state,
    apply_combobox_text_state,
    apply_slider_state,
    build_target_monitor_combobox,
    dispatch_to_monitors,
    resolve_preferred_monitor,
    resolve_span,
)
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import tr
from frontengine.ui.page.layout_kit import SettingPage
from frontengine.utils.web_url import next_page_index, normalize_web_url, parse_dashboard_urls


class WEBSettingUI(SettingPage):
    def __init__(self):
        front_engine_logger.info("[WEBSettingUI] Init")
        super().__init__("tab_web_text", "page_subtitle_web",
                         "Web", "Keep a web page on top of everything else.")

        # Init variable
        self.web_widget_list = []
        self.show_all_screen = False
        self.open_file = False
        self.enable_input = False
        # 網頁儀表板：一次開多個網址，一次只顯示一頁，可循環切換
        # Web dashboard: open several URLs at once, show one page at a time.
        self.dashboard_widgets: list = []
        self.dashboard_index = 0

        # Opacity setting
        self.opacity_label = tr(QLabel(), "Opacity")
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(1, 100)
        self.opacity_slider.setValue(20)
        self.opacity_slider_value_label = QLabel(str(self.opacity_slider.value()))
        self.opacity_slider.valueChanged.connect(self.opacity_trick)

        # WEB URL input
        self.web_url_input = QLineEdit()

        # Start url button
        self.start_button = tr(QPushButton(), "web_setting_open_url")
        self.start_button.clicked.connect(self.start_open_web_with_url)

        # Show on all screen
        self.show_on_all_screen_checkbox = tr(QCheckBox(), "Show on all screen")
        self.show_on_all_screen_checkbox.clicked.connect(self.set_show_all_screen)

        # Open local html file
        self.open_local_html_checkbox = tr(QCheckBox(), "web_setting_open_local_file")
        self.open_local_html_checkbox.clicked.connect(self.set_open_file)

        # Enable input
        self.enable_input_checkbox = tr(QCheckBox(), "web_setting_open_enable_input")
        self.enable_input_checkbox.clicked.connect(self.set_enable_input)

        # Show on bottom
        self.show_on_bottom_checkbox = tr(QCheckBox(), "Show on bottom")

        # Zoom
        self.zoom_label = tr(QLabel(), "web_zoom_label", "Zoom")
        self.zoom_combobox = QComboBox()
        for label, factor in (("50%", 0.5), ("75%", 0.75), ("100%", 1.0),
                              ("125%", 1.25), ("150%", 1.5), ("200%", 2.0)):
            self.zoom_combobox.addItem(label, factor)
        self.zoom_combobox.setCurrentText("100%")

        # Auto refresh
        self.refresh_label = tr(QLabel(), "web_refresh_label", "Auto refresh")
        self.refresh_combobox = QComboBox()
        _off = language_wrapper.language_word_dict.get("web_refresh_off", "Off")
        for label, seconds in ((_off, 0), ("30s", 30), ("1m", 60), ("5m", 300), ("15m", 900)):
            self.refresh_combobox.addItem(label, seconds)

        # Target monitor selector
        self.target_monitor_label = tr(QLabel(), "target_monitor_label", "Target monitor")
        self.target_monitor_combobox = build_target_monitor_combobox()

        # Dashboard: one URL per line, shown one page at a time
        self.dashboard_label = tr(QLabel(), "web_dashboard_label", "Dashboard URLs")
        self.dashboard_edit = QPlainTextEdit()
        self.dashboard_edit.setPlaceholderText(
            language_wrapper.language_word_dict.get(
                "web_dashboard_hint", "One URL per line; lines starting with # are ignored."))
        self.dashboard_edit.setMaximumHeight(90)
        self.dashboard_start_button = tr(QPushButton(), "web_dashboard_start", "Start dashboard")
        self.dashboard_start_button.clicked.connect(self.start_dashboard)
        self.dashboard_next_button = tr(QPushButton(), "web_dashboard_next", "Next page")
        self.dashboard_next_button.clicked.connect(self.show_next_dashboard_page)

        # Layout
        source = self.add_section("section_source", "Source")
        source.add_row("url", self.web_url_input, "URL")
        source.add_inline(self.open_local_html_checkbox, self.enable_input_checkbox)

        appearance = self.add_section("section_appearance", "Appearance")
        appearance.add_slider_row(
            self.opacity_label, self.opacity_slider, self.opacity_slider_value_label)
        appearance.add_row(self.zoom_label, self.zoom_combobox)
        appearance.add_row(self.refresh_label, self.refresh_combobox)

        # 儀表板是「一次開好幾個網址、輪流顯示」，和放單一網頁不是同一件事
        # The dashboard opens several URLs and cycles them - a different errand
        # from putting one page on screen.
        dashboard = self.add_section("section_content", "Dashboard")
        dashboard.add_widget(self.dashboard_edit, self.dashboard_label)
        dashboard.add_inline(self.dashboard_start_button, self.dashboard_next_button)

        where = self.add_section("section_where", "Where")
        where.add_row(self.target_monitor_label, self.target_monitor_combobox)
        where.add_inline(self.show_on_all_screen_checkbox, self.show_on_bottom_checkbox)

        self.finish_body()
        self.set_footer(primary=self.start_button)

    def set_show_all_screen(self) -> None:
        front_engine_logger.info("[WEBSettingUI] set_show_all_screen")
        self.show_all_screen = self.show_on_all_screen_checkbox.isChecked()

    def set_open_file(self) -> None:
        front_engine_logger.info("[WEBSettingUI] set_open_file")
        self.open_file = self.open_local_html_checkbox.isChecked()

    def set_enable_input(self) -> None:
        front_engine_logger.info("[WEBSettingUI] set_enable_input")
        self.enable_input = self.enable_input_checkbox.isChecked()

    def _create_web_widget(self) -> WebWidget:
        front_engine_logger.info("[WEBSettingUI] _create_web_widget")
        url_text = self.web_url_input.text()
        if not self.open_file:
            # Turn YouTube links into an autoplay embed; other URLs unchanged.
            url_text = normalize_web_url(url_text)
        web_widget = WebWidget(url_text, is_file=self.open_file)
        web_widget.set_ui_variable(float(self.opacity_slider.value()) / 100)
        web_widget.set_ui_window_flag(
            enable_input=self.enable_input,
            show_on_bottom=self.show_on_bottom_checkbox.isChecked()
        )
        web_widget.set_zoom(self.zoom_combobox.currentData())
        web_widget.set_auto_refresh(self.refresh_combobox.currentData())
        self.web_widget_list.append(web_widget)
        return web_widget

    def opacity_trick(self) -> None:
        front_engine_logger.info("[WEBSettingUI] opacity_trick")
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    # --- dashboard -------------------------------------------------------
    def dashboard_urls(self) -> list:
        """目前設定的儀表板網址清單 / The dashboard URLs as currently configured."""
        return parse_dashboard_urls(self.dashboard_edit.toPlainText())

    def start_dashboard(self) -> None:
        """
        一次開啟所有儀表板網址，但只顯示第一頁；其餘先隱藏，之後可循環切換。
        Open every dashboard URL at once but show only the first page; the rest
        stay hidden until the user cycles to them.
        """
        front_engine_logger.info("[WEBSettingUI] start_dashboard")
        self.close_dashboard()
        urls = self.dashboard_urls()
        if not urls:
            return
        monitor_index = resolve_preferred_monitor(self.target_monitor_combobox)
        original_url = self.web_url_input.text()
        try:
            for url in urls:
                self.web_url_input.setText(url)
                widget = self._create_web_widget()
                self.dashboard_widgets.append(widget)
                self._present_dashboard_widget(widget, monitor_index)
        finally:
            self.web_url_input.setText(original_url)
        self.dashboard_index = 0
        self._apply_dashboard_visibility()

    def _present_dashboard_widget(self, widget: WebWidget, monitor_index) -> None:
        """把儀表板頁面放到目標螢幕上（先建立後再依索引決定顯示哪一頁）。"""
        from PySide6.QtGui import QGuiApplication

        screens = QGuiApplication.screens()
        if monitor_index is not None and 0 <= monitor_index < len(screens):
            widget.setScreen(screens[monitor_index])
            widget.move(screens[monitor_index].availableGeometry().topLeft())
        widget.showFullScreen()

    def show_next_dashboard_page(self) -> None:
        """切換到下一頁（循環）；沒有儀表板時什麼都不做。"""
        if not self._alive_dashboard_widgets():
            return
        self.dashboard_index = next_page_index(self.dashboard_index, len(self.dashboard_widgets))
        self._apply_dashboard_visibility()

    def close_dashboard(self) -> None:
        """關閉整組儀表板 / Close the whole dashboard."""
        for widget in self.dashboard_widgets[:]:
            try:
                widget.close()
            except RuntimeError:
                pass  # already destroyed
            if widget in self.web_widget_list:
                self.web_widget_list.remove(widget)
        self.dashboard_widgets.clear()
        self.dashboard_index = 0

    def _alive_dashboard_widgets(self) -> list:
        """清掉已被銷毀的頁面後回傳仍存活者。"""
        alive = []
        for widget in self.dashboard_widgets[:]:
            try:
                widget.isVisible()
            except RuntimeError:
                self.dashboard_widgets.remove(widget)
                continue
            alive.append(widget)
        return alive

    def _apply_dashboard_visibility(self) -> None:
        """只顯示目前索引的那一頁。"""
        widgets = self._alive_dashboard_widgets()
        if not widgets:
            return
        self.dashboard_index = self.dashboard_index % len(widgets)
        for index, widget in enumerate(widgets):
            if index == self.dashboard_index:
                widget.show()
                widget.raise_()
            else:
                widget.hide()

    def get_state(self) -> dict:
        return {
            "opacity": self.opacity_slider.value(),
            "url": self.web_url_input.text(),
            "open_file": self.open_local_html_checkbox.isChecked(),
            "enable_input": self.enable_input_checkbox.isChecked(),
            "show_on_all_screen": self.show_on_all_screen_checkbox.isChecked(),
            "show_on_bottom": self.show_on_bottom_checkbox.isChecked(),
            "target_monitor": self.target_monitor_combobox.currentText(),
            "zoom": self.zoom_combobox.currentText(),
            "refresh": self.refresh_combobox.currentText(),
            "dashboard": self.dashboard_edit.toPlainText(),
        }

    def set_state(self, state: dict) -> None:
        """把預設集的內容還原到這一頁的控制項上。"""
        apply_slider_state(state, ((self.opacity_slider, "opacity"),))
        apply_combobox_text_state(state, (
            (self.target_monitor_combobox, "target_monitor"),
            (self.zoom_combobox, "zoom"),
            (self.refresh_combobox, "refresh"),
        ))
        apply_checkbox_state(state, (
            (self.open_local_html_checkbox, "open_file"),
            (self.enable_input_checkbox, "enable_input"),
            (self.show_on_all_screen_checkbox, "show_on_all_screen"),
            (self.show_on_bottom_checkbox, "show_on_bottom"),
        ))
        # 這三個旗標同時記在屬性上，勾選框以外也要跟著更新
        # These three are mirrored on attributes, which need updating as well.
        for attribute, key in (("open_file", "open_file"),
                               ("enable_input", "enable_input"),
                               ("show_all_screen", "show_on_all_screen")):
            if key in state:
                setattr(self, attribute, bool(state[key]))
        if "url" in state:
            self.web_url_input.setText(str(state.get("url") or ""))
        if state.get("dashboard") is not None:
            self.dashboard_edit.setPlainText(str(state["dashboard"]))

    def start_open_web_with_url(self) -> None:
        front_engine_logger.info("[WEBSettingUI] start_open_web_with_url")
        if not self.web_url_input.text().strip():
            # 網址空白時開出來的是一層全螢幕、點擊穿透的空白網頁：看不見也點不到，
            # 只能從控制中心關掉。其他分頁都會先擋下來，這裡也該一樣。
            # An empty URL opens a blank fullscreen click-through page: invisible,
            # unclickable, and only closable from the control center. Every other
            # page stops first; this one should too.
            message_box = QMessageBox(self)
            message_box.setText(language_wrapper.language_word_dict.get("not_prepare"))
            message_box.exec()
            return

        def present_on_monitor(widget: WebWidget, monitor, _idx: int) -> None:
            widget.setScreen(monitor)
            widget.move(monitor.availableGeometry().topLeft())
            widget.showFullScreen()

        dispatch_to_monitors(
            parent=self,
            show_all_screen=self.show_all_screen,
            factory=lambda _monitor: self._create_web_widget(),
            present_primary=lambda widget: widget.showFullScreen(),
            present_on_monitor=present_on_monitor,
            preferred_monitor_index=resolve_preferred_monitor(self.target_monitor_combobox),
            span_all_screens=resolve_span(self.target_monitor_combobox),
        )