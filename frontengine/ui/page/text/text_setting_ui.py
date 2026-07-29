import threading

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QGridLayout, QSlider, QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox, \
    QFontComboBox, QMessageBox

from frontengine.show.text.draw_text import TextWidget
from frontengine.ui.page.utils import (
    apply_checkbox_state,
    apply_combobox_data_state,
    apply_combobox_text_state,
    apply_slider_state,
    build_target_monitor_combobox,
    dispatch_to_monitors,
    resolve_preferred_monitor,
)
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator, tr
from frontengine.utils.system_stats.system_stats import system_stats
from frontengine.utils.text_source.text_source import (
    DEFAULT_TEMPLATES, SOURCE_CLOCK, SOURCE_COUNTDOWN, SOURCE_DATE, SOURCE_STATIC,
    SOURCE_STOPWATCH, SOURCE_SYSTEM, SOURCE_WEATHER, TextSource,
)
from frontengine.utils.weather.weather_service import current_weather, lookup_city, weather_service

# 名稱 -> HEX 顏色 / Named text colors -> hex
_TEXT_COLORS = [
    ("Black", "#000000"), ("White", "#ffffff"), ("Red", "#ff0000"),
    ("Green", "#00ff00"), ("Blue", "#0000ff"), ("Yellow", "#ffff00"),
    ("Cyan", "#00ffff"), ("Magenta", "#ff00ff"),
]


class TextSettingUI(QWidget):
    def __init__(self):
        front_engine_logger.info("[TextSettingUI] Init")
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        # Init variable
        self.text_widget_list = []
        self.show_all_screen = False
        # 已經解析過座標的地名，避免每台螢幕都重新查一次
        # The city already resolved to coordinates, so each monitor does not
        # trigger another lookup.
        self._weather_city_resolved = None

        # Opacity setting
        self.opacity_label = tr(QLabel(), "Opacity")
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(1, 100)
        self.opacity_slider.setValue(20)
        self.opacity_slider_value_label = QLabel(str(self.opacity_slider.value()))
        self.opacity_slider.valueChanged.connect(self.opacity_trick)

        # Font size setting
        self.font_size_label = tr(QLabel(), "Font size")
        self.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_size_slider.setRange(1, 600)
        self.font_size_slider.setValue(100)
        self.font_size_slider_value_label = QLabel(str(self.font_size_slider.value()))
        self.font_size_slider.valueChanged.connect(self.font_size_trick)

        # Text input
        self.line_edit = QLineEdit()

        # Start Button
        self.start_button = tr(QPushButton(), "text_setting_start_draw")
        self.start_button.clicked.connect(self.start_draw_text_on_screen)

        # Show on all screen
        self.show_on_all_screen_checkbox = tr(QCheckBox(), "Show on all screen")
        self.show_on_all_screen_checkbox.clicked.connect(self.set_show_all_screen)

        # Show on bottom
        self.show_on_bottom_checkbox = tr(QCheckBox(), "Show on bottom")

        # Text position
        self.text_position_label = tr(QLabel(), "text_setting_choose_alignment")
        self.text_position_combobox = QComboBox()
        self.text_position_combobox.addItems(["TopLeft", "TopRight", "BottomLeft", "BottomRight", "Center"])

        # Text color
        self.text_color_label = tr(QLabel(), "text_color_label", "Color")
        self.text_color_combobox = QComboBox()
        for name, hex_value in _TEXT_COLORS:
            self.text_color_combobox.addItem(name, hex_value)

        # Font family
        self.font_family_label = tr(QLabel(), "font_family_label", "Font")
        self.font_family_combobox = QFontComboBox()

        # Marquee scroll
        self.marquee_checkbox = tr(QCheckBox(), "marquee_label", "Marquee")
        self.marquee_speed_label = tr(QLabel(), "marquee_speed_label", "Speed")
        self.marquee_speed_combobox = QComboBox()
        self.marquee_speed_combobox.addItems(["2", "4", "6", "8", "12"])
        self.marquee_speed_combobox.setCurrentText("4")

        # Outline (readability on any background)
        self.outline_checkbox = tr(QCheckBox(), "outline_label", "Outline")
        self.outline_color_combobox = QComboBox()
        for name, hex_value in _TEXT_COLORS:
            self.outline_color_combobox.addItem(name, hex_value)
        self.outline_color_combobox.setCurrentText("White")

        # Target monitor selector
        self.target_monitor_label = tr(QLabel(), "target_monitor_label", "Target monitor")
        self.target_monitor_combobox = build_target_monitor_combobox()

        # 文字來源：靜態字串或時鐘／日期／倒數／碼表／系統資訊／天氣
        # Text source: a fixed string, or a clock/date/countdown/stopwatch/stats/weather feed.
        self.text_source_label = tr(QLabel(), "text_source_label", "Text source")
        self.text_source_combobox = QComboBox()
        for kind, fallback in (
            (SOURCE_STATIC, "Static text"), (SOURCE_CLOCK, "Clock"), (SOURCE_DATE, "Date"),
            (SOURCE_COUNTDOWN, "Countdown"), (SOURCE_STOPWATCH, "Stopwatch"),
            (SOURCE_SYSTEM, "System stats"), (SOURCE_WEATHER, "Weather"),
        ):
            self.text_source_combobox.addItem(
                language_wrapper.language_word_dict.get(f"text_source_{kind}", fallback), kind)
        self.text_source_combobox.currentIndexChanged.connect(self._update_source_hint)
        self.text_source_hint_label = QLabel("")
        # 這句是「提示 + 樣板」組出來的，不是單一個鍵，換語言時整段重算
        # Composed from a hint plus a template, so recompute it wholesale.
        retranslator.bind_call(self._update_source_hint)
        self.text_source_hint_label.setWordWrap(True)

        # 天氣地點（只有天氣來源會用到）/ Weather location (only used by the weather source)
        self.weather_location_label = tr(QLabel(), "weather_location_label", "Weather city")
        self.weather_location_edit = QLineEdit()
        self.weather_location_edit.setPlaceholderText(
            language_wrapper.language_word_dict.get("weather_location_hint", "e.g. Taipei"))

        # Layout
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.font_size_label, 1, 0)
        self.grid_layout.addWidget(self.font_size_slider_value_label, 1, 1)
        self.grid_layout.addWidget(self.font_size_slider, 1, 2)
        self.grid_layout.addWidget(self.show_on_all_screen_checkbox, 2, 0)
        self.grid_layout.addWidget(self.show_on_bottom_checkbox, 2, 1)
        self.grid_layout.addWidget(self.text_position_label, 3, 0)
        self.grid_layout.addWidget(self.text_position_combobox, 3, 1)
        self.grid_layout.addWidget(self.start_button, 4, 0)
        self.grid_layout.addWidget(self.line_edit, 4, 1)
        self.grid_layout.addWidget(self.target_monitor_label, 5, 0)
        self.grid_layout.addWidget(self.target_monitor_combobox, 5, 1)
        self.grid_layout.addWidget(self.text_color_label, 6, 0)
        self.grid_layout.addWidget(self.text_color_combobox, 6, 1)
        self.grid_layout.addWidget(self.font_family_label, 7, 0)
        self.grid_layout.addWidget(self.font_family_combobox, 7, 1)
        self.grid_layout.addWidget(self.marquee_checkbox, 8, 0)
        self.grid_layout.addWidget(self.marquee_speed_label, 8, 1)
        self.grid_layout.addWidget(self.marquee_speed_combobox, 8, 2)
        self.grid_layout.addWidget(self.outline_checkbox, 9, 0)
        self.grid_layout.addWidget(self.outline_color_combobox, 9, 1)
        self.grid_layout.addWidget(self.text_source_label, 10, 0)
        self.grid_layout.addWidget(self.text_source_combobox, 10, 1)
        self.grid_layout.addWidget(self.weather_location_label, 11, 0)
        self.grid_layout.addWidget(self.weather_location_edit, 11, 1)
        self.grid_layout.addWidget(self.text_source_hint_label, 12, 0, 1, 3)
        self._update_source_hint()

    def set_show_all_screen(self) -> None:
        front_engine_logger.info("[TextSettingUI] set_show_all_screen")
        self.show_all_screen = self.show_on_all_screen_checkbox.isChecked()

    def _update_source_hint(self) -> None:
        """依所選來源說明文字欄位的意義（樣板、倒數分鐘數…）。"""
        kind = self.text_source_combobox.currentData() or SOURCE_STATIC
        default = DEFAULT_TEMPLATES.get(kind, "")
        hint = language_wrapper.language_word_dict.get(f"text_source_hint_{kind}", "")
        self.text_source_hint_label.setText(f"{hint}  ({default})" if default else hint)
        self.weather_location_label.setVisible(kind == SOURCE_WEATHER)
        self.weather_location_edit.setVisible(kind == SOURCE_WEATHER)

    def _build_text_source(self) -> TextSource:
        """依目前設定組出文字來源；天氣來源會先把地名解析成座標。"""
        kind = self.text_source_combobox.currentData() or SOURCE_STATIC
        if kind == SOURCE_WEATHER:
            self._apply_weather_location()
        return TextSource(
            kind=kind,
            template=self.line_edit.text(),
            stats_provider=system_stats,
            weather_provider=current_weather,
        )

    def _apply_weather_location(self) -> None:
        """
        把使用者填的地名換成座標；查不到就沿用預設地點。

        查詢在背景執行緒進行。lookup_city 是同步的網路請求（逾時 10 秒，再加上
        沒有上限的 DNS），而這裡是由「開始」按鈕的槽函式呼叫、而且每一台螢幕
        各呼叫一次：勾了「顯示在所有螢幕」又剛好斷網的話，三螢幕就是整個介面
        僵住三十幾秒，畫面上什麼提示也沒有。同一個地名只查一次。

        The lookup runs on a background thread. lookup_city is a synchronous
        network request - a 10 second timeout plus uncapped DNS - called from the
        Start button's slot once per monitor: with "show on all screens" ticked
        and the network down, three monitors froze the whole interface for half a
        minute with nothing on screen to explain it. Each city is resolved once.
        """
        city = self.weather_location_edit.text().strip()
        if not city or city == self._weather_city_resolved:
            return
        self._weather_city_resolved = city

        def resolve() -> None:
            found = lookup_city(city)
            if found is None:
                front_engine_logger.warning(f"[TextSettingUI] weather city not found: {city}")
                # 查失敗就忘掉，下次按開始才會再試一次
                # Forget a failure so the next Start tries again.
                self._weather_city_resolved = None
                return
            weather_service().set_location(found[0], found[1])

        threading.Thread(target=resolve, name="frontengine-city-lookup", daemon=True).start()

    def _create_text_widget(self) -> TextWidget:
        front_engine_logger.info("[TextSettingUI] _create_text_widget")
        text_widget = TextWidget(
            text=self.line_edit.text(),
            alignment=self.text_position_combobox.currentText()
        )
        text_widget.set_font_variable(self.font_size_slider.value())
        text_widget.set_font_family(self.font_family_combobox.currentFont().family())
        text_widget.set_color(self.text_color_combobox.currentData())
        text_widget.set_outline(
            self.outline_checkbox.isChecked(), self.outline_color_combobox.currentData()
        )
        text_widget.set_ui_variable(float(self.opacity_slider.value()) / 100)
        text_widget.set_ui_window_flag(self.show_on_bottom_checkbox.isChecked())
        text_widget.set_marquee(
            self.marquee_checkbox.isChecked(),
            int(self.marquee_speed_combobox.currentText()),
        )
        text_widget.set_text_source(self._build_text_source())
        self.text_widget_list.append(text_widget)
        return text_widget

    def opacity_trick(self) -> None:
        front_engine_logger.info("[TextSettingUI] opacity_trick")
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def font_size_trick(self) -> None:
        front_engine_logger.info("[TextSettingUI] font_size_trick")
        self.font_size_slider_value_label.setText(str(self.font_size_slider.value()))

    def get_state(self) -> dict:
        return {
            "opacity": self.opacity_slider.value(),
            "font_size": self.font_size_slider.value(),
            "text": self.line_edit.text(),
            "alignment": self.text_position_combobox.currentText(),
            "show_on_all_screen": self.show_on_all_screen_checkbox.isChecked(),
            "show_on_bottom": self.show_on_bottom_checkbox.isChecked(),
            "target_monitor": self.target_monitor_combobox.currentText(),
            "color": self.text_color_combobox.currentText(),
            "font_family": self.font_family_combobox.currentFont().family(),
            "marquee": self.marquee_checkbox.isChecked(),
            "marquee_speed": self.marquee_speed_combobox.currentText(),
            "outline": self.outline_checkbox.isChecked(),
            "outline_color": self.outline_color_combobox.currentText(),
            "text_source": self.text_source_combobox.currentData(),
            "weather_location": self.weather_location_edit.text(),
        }

    def set_state(self, state: dict) -> None:
        """把預設集的內容還原到這一頁的控制項上。"""
        apply_slider_state(state, ((self.opacity_slider, "opacity"),
                                   (self.font_size_slider, "font_size")))
        apply_combobox_text_state(state, (
            (self.text_position_combobox, "alignment"),
            (self.target_monitor_combobox, "target_monitor"),
            (self.text_color_combobox, "color"),
            (self.marquee_speed_combobox, "marquee_speed"),
            (self.outline_color_combobox, "outline_color"),
        ))
        apply_checkbox_state(state, (
            (self.show_on_all_screen_checkbox, "show_on_all_screen"),
            (self.show_on_bottom_checkbox, "show_on_bottom"),
            (self.marquee_checkbox, "marquee"),
            (self.outline_checkbox, "outline"),
        ))
        apply_combobox_data_state(self.text_source_combobox, state.get("text_source"))
        if "show_on_all_screen" in state:
            # 這個旗標同時記在一個屬性上，勾選框以外也要跟著更新
            # The flag is mirrored on an attribute, so it needs updating too.
            self.show_all_screen = bool(state["show_on_all_screen"])
        if "text" in state:
            self.line_edit.setText(str(state.get("text") or ""))
        if state.get("font_family"):
            self.font_family_combobox.setCurrentFont(QFont(str(state["font_family"])))
        if state.get("weather_location") is not None:
            self.weather_location_edit.setText(str(state["weather_location"]))

    def start_draw_text_on_screen(self) -> None:
        front_engine_logger.info("[TextSettingUI] start_draw_text_on_screen")

        # 動態來源不需要固定文字（樣板留白就用預設）；只有靜態文字必須填。
        # Dynamic sources fall back to their default template, so only static
        # text has to be filled in.
        is_static = (self.text_source_combobox.currentData() or SOURCE_STATIC) == SOURCE_STATIC
        if is_static and not self.line_edit.text().strip():
            QMessageBox.warning(self, "Warning", language_wrapper.language_word_dict.get("not_prepare"))
            return

        def present_on_monitor(widget: TextWidget, monitor, _idx: int) -> None:
            widget.setScreen(monitor)
            widget.move(monitor.availableGeometry().topLeft())
            widget.showFullScreen()

        dispatch_to_monitors(
            parent=self,
            show_all_screen=self.show_all_screen,
            factory=lambda _monitor: self._create_text_widget(),
            present_primary=lambda widget: widget.showFullScreen(),
            present_on_monitor=present_on_monitor,
            preferred_monitor_index=resolve_preferred_monitor(self.target_monitor_combobox),
        )