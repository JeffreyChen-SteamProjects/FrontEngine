"""
簡報頁：螢幕塗鴉、游標強調（亮環／漣漪／聚光燈）、按鍵顯示、區域放大鏡。
除了塗鴉需要接收滑鼠之外，其餘都是點擊穿透的覆蓋層。

The presentation page: screen annotation, cursor emphasis (ring, click ripple,
spotlight), a keystroke display and a region magnifier. Everything except the
annotation layer passes clicks straight through.
"""
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QCheckBox, QComboBox, QLabel, QPushButton, QSlider,
)

from frontengine.show.canvas.whiteboard_widget import WhiteboardWidget
from frontengine.show.presentation.annotation_overlay import (
    PEN_COLORS, TOOL_ERASER, TOOL_HIGHLIGHTER, TOOL_PEN, AnnotationOverlay,
)
from frontengine.show.presentation.cursor_effects import CursorEffectWidget
from frontengine.show.presentation.keystroke_display import KeystrokeDisplayWidget
from frontengine.show.presentation.magnifier import MagnifierWidget
from frontengine.show.freeze.freeze_widget import FreezeWidget, capture_screen
from frontengine.ui.page.utils import build_target_monitor_combobox, coerce_int, resolve_preferred_monitor
from frontengine.utils.input_watch.input_watch_service import InputWatchService
from frontengine.ui.page.layout_kit import SettingPage
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator, tr


class PresentationSettingUI(SettingPage):
    """簡報與教學工具設定頁。"""

    def __init__(self):
        front_engine_logger.info("[PresentationSettingUI] Init")
        super().__init__("tab_presentation_text", "page_subtitle_presentation",
                         "Presenting", "Draw, magnify and highlight while you present.")

        self.annotation_widget_list: List[AnnotationOverlay] = []
        self.whiteboard_widget_list: List[WhiteboardWidget] = []
        self.cursor_widget_list: List[CursorEffectWidget] = []
        self.keystroke_widget_list: List[KeystrokeDisplayWidget] = []
        self.magnifier_widget_list: List[MagnifierWidget] = []
        # 全域輸入監聽（按鍵顯示與點擊漣漪共用；pynput 不可用時自動停用）
        # Shared global input watching; disables itself without pynput.
        self.input_watch = InputWatchService(self)
        self.input_watch.key_pressed.connect(self._on_key_pressed, Qt.ConnectionType.QueuedConnection)
        self.input_watch.mouse_clicked.connect(self._on_mouse_clicked, Qt.ConnectionType.QueuedConnection)

        # Annotation
        self.annotate_label = tr(QLabel(), "annotate_label", "Screen annotation")
        self.annotate_tool_combobox = QComboBox()
        for tool, fallback in ((TOOL_PEN, "Pen"), (TOOL_HIGHLIGHTER, "Highlighter"),
                               (TOOL_ERASER, "Eraser")):
            self.annotate_tool_combobox.addItem(
                language_wrapper.language_word_dict.get(f"annotate_tool_{tool}", fallback), tool)
        self.annotate_tool_combobox.currentIndexChanged.connect(self._apply_annotation_settings)
        self.annotate_color_combobox = QComboBox()
        for name, hex_value in PEN_COLORS:
            self.annotate_color_combobox.addItem(name, hex_value)
        self.annotate_color_combobox.currentIndexChanged.connect(self._apply_annotation_settings)
        self.annotate_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.annotate_width_slider.setRange(1, 40)
        self.annotate_width_slider.setValue(4)
        self.annotate_width_slider.valueChanged.connect(self._apply_annotation_settings)
        self.annotate_button = tr(QPushButton(), "annotate_start", "Start drawing")
        self.annotate_button.clicked.connect(self.toggle_annotation)
        self.annotate_undo_button = tr(QPushButton(), "annotate_undo", "Undo")
        self.annotate_undo_button.clicked.connect(self.undo_annotation)
        self.annotate_clear_button = tr(QPushButton(), "annotate_clear", "Clear")
        self.annotate_clear_button.clicked.connect(self.clear_annotation)

        # Cursor effects
        self.cursor_label = tr(QLabel(), "cursor_effect_label", "Cursor emphasis")
        self.cursor_ring_checkbox = tr(QCheckBox(), "cursor_effect_ring", "Highlight")
        self.cursor_ring_checkbox.setChecked(True)
        self.cursor_ripple_checkbox = tr(QCheckBox(), "cursor_effect_ripple", "Click ripple")
        self.cursor_ripple_checkbox.setChecked(True)
        self.cursor_spotlight_checkbox = tr(QCheckBox(), "cursor_effect_spotlight", "Spotlight")
        for checkbox in (self.cursor_ring_checkbox, self.cursor_ripple_checkbox,
                         self.cursor_spotlight_checkbox):
            checkbox.toggled.connect(self._apply_cursor_settings)
        self.cursor_button = tr(QPushButton(), "cursor_effect_start", "Turn cursor effects on")
        self.cursor_button.clicked.connect(self.toggle_cursor_effects)

        # Keystroke display
        self.keystroke_label = tr(QLabel(), "keystroke_label", "Keystroke display")
        self.keystroke_button = tr(QPushButton(), "keystroke_start", "Show keystrokes")
        self.keystroke_button.clicked.connect(self.toggle_keystrokes)

        # Magnifier
        self.magnifier_label = tr(QLabel(), "magnifier_label", "Magnifier")
        self.magnifier_zoom_combobox = QComboBox()
        self.magnifier_zoom_combobox.addItems(["1.5", "2.0", "3.0", "4.0", "6.0"])
        self.magnifier_zoom_combobox.setCurrentText("2.0")
        self.magnifier_zoom_combobox.currentIndexChanged.connect(self._apply_magnifier_settings)
        self.magnifier_button = tr(QPushButton(), "magnifier_start", "Turn magnifier on")
        self.magnifier_button.clicked.connect(self.toggle_magnifier)

        # Shared
        self.whiteboard_button = tr(QPushButton(), "whiteboard_start", "Whiteboard")
        self.whiteboard_button.clicked.connect(self.toggle_whiteboard)
        self.whiteboard_save_button = tr(QPushButton(), "whiteboard_save", "Save whiteboard")
        self.whiteboard_save_button.clicked.connect(self.save_whiteboard)
        self.target_monitor_label = tr(QLabel(), "target_monitor_label", "Target monitor")
        self.target_monitor_combobox = build_target_monitor_combobox()

        # 凍結畫面：把目標螢幕現在的樣子拍下來蓋上去，講解時可以先停住畫面
        # Freeze: cover the target screen with a photograph of itself, so an
        # explanation can be paced without the audience watching you work.
        self.freeze_widget_list: list = []
        self.freeze_label = tr(QLabel(), "presentation_freeze_label", "Freeze screen")
        self.freeze_button = tr(QPushButton(), "presentation_freeze_start", "Freeze")
        self.freeze_button.clicked.connect(self.toggle_freeze)
        self.hint_label = tr(QLabel(), "presentation_hint",
            "Drawing takes the mouse while it is on; the other overlays pass clicks through.")
        self.hint_label.setWordWrap(True)

        # Layout
        # 簡報頁是五個各自獨立的工具，開關互不相干，所以一個工具一個分區
        # Five independent tools whose switches have nothing to do with each
        # other, so each gets its own section.
        annotate = self.add_section(self.annotate_label)
        annotate.add_row("presentation_tool", self.annotate_tool_combobox, "Tool")
        annotate.add_row("presentation_colour", self.annotate_color_combobox, "Colour")
        annotate.add_row("presentation_width", self.annotate_width_slider, "Width")
        annotate.add_inline(self.annotate_button, self.annotate_undo_button,
                            self.annotate_clear_button)

        cursor = self.add_section(self.cursor_label)
        cursor.add_inline(self.cursor_ring_checkbox, self.cursor_ripple_checkbox,
                          self.cursor_spotlight_checkbox)
        cursor.add_inline(self.cursor_button)

        keystroke = self.add_section(self.keystroke_label)
        keystroke.add_inline(self.keystroke_button)

        magnifier = self.add_section(self.magnifier_label)
        magnifier.add_row("presentation_zoom", self.magnifier_zoom_combobox, "Zoom")
        magnifier.add_inline(self.magnifier_button)

        whiteboard = self.add_section("section_actions", "Whiteboard")
        whiteboard.add_inline(self.whiteboard_button, self.whiteboard_save_button)

        where = self.add_section("section_where", "Where")
        freeze = self.add_section(self.freeze_label)
        freeze.add_inline(self.freeze_button)

        where.add_row(self.target_monitor_label, self.target_monitor_combobox)

        self.add_body_widget(self.hint_label)
        self.finish_body()

    # --- shared ----------------------------------------------------------
    def target_screen(self):
        """回傳要覆蓋的螢幕（未指定則主螢幕）。"""
        screens = QGuiApplication.screens()
        index = resolve_preferred_monitor(self.target_monitor_combobox)
        if index is not None and 0 <= index < len(screens):
            return screens[index]
        return QGuiApplication.primaryScreen()

    def _present(self, widget) -> None:
        screen = self.target_screen()
        if screen is not None:
            widget.setScreen(screen)
            widget.setGeometry(screen.geometry())
        widget.show()

    @staticmethod
    def _close_all(widgets: list) -> None:
        for widget in widgets[:]:
            try:
                widget.close()
            except RuntimeError:
                pass
        widgets.clear()

    def _ensure_input_watch(self) -> None:
        """需要按鍵或點擊事件時才啟動全域監聽。"""
        if self.keystroke_widget_list or self.cursor_widget_list:
            self.input_watch.start()

    def release_input_watch(self) -> None:
        """沒有覆蓋層要聽了就收掉全域輸入監聽（批次關閉之後也會呼叫）。"""
        if not self.keystroke_widget_list and not self.cursor_widget_list:
            self.input_watch.stop()

    # --- annotation ------------------------------------------------------
    def toggle_annotation(self) -> None:
        if self.annotation_widget_list:
            self.stop_annotation()
        else:
            self.start_annotation()

    def start_annotation(self) -> None:
        front_engine_logger.info("[PresentationSettingUI] start_annotation")
        self.stop_annotation()
        widget = AnnotationOverlay(
            self.annotate_color_combobox.currentData(), self.annotate_width_slider.value(),
            self.annotate_tool_combobox.currentData())
        widget.set_annotation_window_flag()
        self.annotation_widget_list.append(widget)
        self._present(widget)
        retranslator.set_text(
            self.annotate_button, "annotate_stop", "Stop drawing")

    def stop_annotation(self) -> None:
        self._close_all(self.annotation_widget_list)
        retranslator.set_text(
            self.annotate_button, "annotate_start", "Start drawing")

    def undo_annotation(self) -> None:
        for widget in self.annotation_widget_list:
            widget.undo()

    def clear_annotation(self) -> None:
        for widget in self.annotation_widget_list:
            widget.clear()

    def _apply_annotation_settings(self) -> None:
        for widget in self.annotation_widget_list[:]:
            try:
                widget.set_tool(self.annotate_tool_combobox.currentData())
                widget.set_pen(self.annotate_color_combobox.currentData(),
                               self.annotate_width_slider.value())
            except RuntimeError:
                self.annotation_widget_list.remove(widget)

    # --- cursor effects --------------------------------------------------
    def toggle_cursor_effects(self) -> None:
        if self.cursor_widget_list:
            self.stop_cursor_effects()
        else:
            self.start_cursor_effects()

    def start_cursor_effects(self) -> None:
        front_engine_logger.info("[PresentationSettingUI] start_cursor_effects")
        self.stop_cursor_effects()
        widget = CursorEffectWidget(
            ring=self.cursor_ring_checkbox.isChecked(),
            ripple=self.cursor_ripple_checkbox.isChecked(),
            spotlight=self.cursor_spotlight_checkbox.isChecked())
        widget.set_ui_window_flag(show_on_bottom=False)
        self.cursor_widget_list.append(widget)
        self._present(widget)
        widget.start_following()
        self._ensure_input_watch()
        retranslator.set_text(
            self.cursor_button, "cursor_effect_stop", "Turn cursor effects off")

    def stop_cursor_effects(self) -> None:
        self._close_all(self.cursor_widget_list)
        self.release_input_watch()
        retranslator.set_text(
            self.cursor_button, "cursor_effect_start", "Turn cursor effects on")

    def _apply_cursor_settings(self) -> None:
        for widget in self.cursor_widget_list[:]:
            try:
                widget.set_effects(
                    ring=self.cursor_ring_checkbox.isChecked(),
                    ripple=self.cursor_ripple_checkbox.isChecked(),
                    spotlight=self.cursor_spotlight_checkbox.isChecked())
            except RuntimeError:
                self.cursor_widget_list.remove(widget)

    # --- keystroke display -----------------------------------------------
    def toggle_keystrokes(self) -> None:
        if self.keystroke_widget_list:
            self.stop_keystrokes()
        else:
            self.start_keystrokes()

    def start_keystrokes(self) -> None:
        front_engine_logger.info("[PresentationSettingUI] start_keystrokes")
        self.stop_keystrokes()
        widget = KeystrokeDisplayWidget()
        widget.set_ui_window_flag(show_on_bottom=False)
        self.keystroke_widget_list.append(widget)
        self._present(widget)
        widget.start()
        self._ensure_input_watch()
        retranslator.set_text(
            self.keystroke_button, "keystroke_stop", "Hide keystrokes")

    def stop_keystrokes(self) -> None:
        self._close_all(self.keystroke_widget_list)
        self.release_input_watch()
        retranslator.set_text(
            self.keystroke_button, "keystroke_start", "Show keystrokes")

    def _on_key_pressed(self, keys) -> None:
        for widget in self.keystroke_widget_list[:]:
            try:
                widget.push_keys(keys)
            except RuntimeError:
                self.keystroke_widget_list.remove(widget)

    def _on_mouse_clicked(self, x: int, y: int) -> None:
        from PySide6.QtCore import QPoint

        for widget in self.cursor_widget_list[:]:
            try:
                widget.add_ripple(QPoint(int(x) - widget.x(), int(y) - widget.y()))
            except RuntimeError:
                self.cursor_widget_list.remove(widget)

    # --- magnifier -------------------------------------------------------
    def toggle_magnifier(self) -> None:
        if self.magnifier_widget_list:
            self.stop_magnifier()
        else:
            self.start_magnifier()

    def start_magnifier(self) -> None:
        front_engine_logger.info("[PresentationSettingUI] start_magnifier")
        self.stop_magnifier()
        widget = MagnifierWidget(float(self.magnifier_zoom_combobox.currentText()))
        widget.set_ui_window_flag(show_on_bottom=False)
        widget.resize(widget.view_size, widget.view_size)
        screen = self.target_screen()
        if screen is not None:
            widget.setScreen(screen)
            corner = screen.geometry().topRight()
            widget.move(corner.x() - widget.view_size - 20, corner.y() + 20)
        widget.show()
        self.magnifier_widget_list.append(widget)
        widget.start_following()
        retranslator.set_text(
            self.magnifier_button, "magnifier_stop", "Turn magnifier off")

    def stop_magnifier(self) -> None:
        self._close_all(self.magnifier_widget_list)
        retranslator.set_text(
            self.magnifier_button, "magnifier_start", "Turn magnifier on")

    def _apply_magnifier_settings(self) -> None:
        for widget in self.magnifier_widget_list[:]:
            try:
                widget.set_zoom(float(self.magnifier_zoom_combobox.currentText()))
            except RuntimeError:
                self.magnifier_widget_list.remove(widget)

    # --- whiteboard ------------------------------------------------------
    def toggle_whiteboard(self) -> None:
        if self.whiteboard_widget_list:
            self.stop_whiteboard()
        else:
            self.start_whiteboard()

    def toggle_freeze(self):
        """
        凍結／解除目標螢幕。已經凍結就解除，所以同一顆按鈕（和同一個快速鍵）
        兩種方向都走得通。
        Freeze or unfreeze the target screen. Frozen already means unfreeze, so
        the same button - and the same shortcut - works both ways.
        """
        if self.freeze_widget_list:
            self.unfreeze()
            return None

        screens = QGuiApplication.screens()
        index = resolve_preferred_monitor(self.target_monitor_combobox)
        screen = screens[index] if index is not None and 0 <= index < len(screens)             else QGuiApplication.primaryScreen()

        pixmap = capture_screen(screen)
        if pixmap.isNull():
            # 拍不到就不要蓋一塊空白上去：那會讓整個螢幕變成一片黑，而且看起來
            # 像當機而不是「凍結失敗」。
            # Without a picture, do not cover anything: a blank sheet turns the
            # screen black and reads as a crash rather than a failed freeze.
            front_engine_logger.info("[PresentationSettingUI] nothing captured, not freezing")
            return None

        widget = FreezeWidget(pixmap)
        widget.destroyed.connect(lambda: self._forget_freeze(widget))
        widget.show_on(screen)
        self.freeze_widget_list.append(widget)
        retranslator.set_text(self.freeze_button, "presentation_freeze_stop", "Unfreeze")
        return widget

    def unfreeze(self) -> None:
        """解除凍結。"""
        for widget in self.freeze_widget_list[:]:
            try:
                widget.close()
            except RuntimeError:  # pragma: no cover - 底層物件已消失
                pass
        self.freeze_widget_list.clear()
        retranslator.set_text(self.freeze_button, "presentation_freeze_start", "Freeze")

    def _forget_freeze(self, widget) -> None:
        """
        使用者自己按 Escape 或雙擊關掉時也要回到「凍結」字樣，否則按鈕會一直
        寫著「解除凍結」，而畫面上根本沒有凍結的東西。
        Coming back to "Freeze" when the user dismissed it themselves; otherwise
        the button keeps offering to unfreeze something that is no longer there.
        """
        if widget in self.freeze_widget_list:
            self.freeze_widget_list.remove(widget)
        if self.freeze_widget_list:
            return
        try:
            retranslator.set_text(self.freeze_button, "presentation_freeze_start", "Freeze")
        except RuntimeError:
            # destroyed 是在 C++ 物件消失之後才送到的，關閉程式時這一頁可能已經
            # 先走了。那時候沒有按鈕可以改，也不需要改。
            # destroyed arrives after the C++ object is gone, and on shutdown this
            # page may already have followed it. There is no button left to
            # relabel, and nothing that needs relabelling.
            pass

    def start_whiteboard(self) -> None:
        """開一塊無限畫布（可平移縮放，畫過的東西留在畫布座標上）。"""
        front_engine_logger.info("[PresentationSettingUI] start_whiteboard")
        board = WhiteboardWidget(self.annotate_color_combobox.currentData(),
                                 self.annotate_width_slider.value())
        self._present(board)
        self.whiteboard_widget_list.append(board)
        retranslator.set_text(
            self.whiteboard_button, "whiteboard_stop", "Close whiteboard")

    def stop_whiteboard(self) -> None:
        self._close_all(self.whiteboard_widget_list)
        retranslator.set_text(
            self.whiteboard_button, "whiteboard_start", "Whiteboard")

    def save_whiteboard(self) -> Optional[str]:
        """把白板存成圖片；沒畫東西就不存。"""
        for board in self.whiteboard_widget_list[:]:
            try:
                target = QFileDialog.getSaveFileName(
                    self, language_wrapper.language_word_dict.get(
                        "whiteboard_save", "Save whiteboard"), "whiteboard.png", "PNG (*.png)")[0]
                if target:
                    return board.save_image(target)
            except RuntimeError:
                self.whiteboard_widget_list.remove(board)
        return None

    # --- preset state ----------------------------------------------------
    def get_state(self) -> dict:
        return {
            "annotate_tool": self.annotate_tool_combobox.currentData(),
            "annotate_color": self.annotate_color_combobox.currentText(),
            "annotate_width": self.annotate_width_slider.value(),
            "cursor_ring": self.cursor_ring_checkbox.isChecked(),
            "cursor_ripple": self.cursor_ripple_checkbox.isChecked(),
            "cursor_spotlight": self.cursor_spotlight_checkbox.isChecked(),
            "magnifier_zoom": self.magnifier_zoom_combobox.currentText(),
            "target_monitor": self.target_monitor_combobox.currentText(),
        }

    def set_state(self, state: dict) -> None:
        if state.get("annotate_tool") is not None:
            index = self.annotate_tool_combobox.findData(str(state["annotate_tool"]))
            if index >= 0:
                self.annotate_tool_combobox.setCurrentIndex(index)
        for combobox, key in ((self.annotate_color_combobox, "annotate_color"),
                              (self.magnifier_zoom_combobox, "magnifier_zoom"),
                              (self.target_monitor_combobox, "target_monitor")):
            if state.get(key) is not None:
                index = combobox.findText(str(state[key]))
                if index >= 0:
                    combobox.setCurrentIndex(index)
        width = coerce_int(state.get("annotate_width"))
        if width is not None:
            self.annotate_width_slider.setValue(width)
        for checkbox, key in ((self.cursor_ring_checkbox, "cursor_ring"),
                              (self.cursor_ripple_checkbox, "cursor_ripple"),
                              (self.cursor_spotlight_checkbox, "cursor_spotlight")):
            if key in state:
                checkbox.setChecked(bool(state[key]))
