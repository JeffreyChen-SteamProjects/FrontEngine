"""
工具分頁：取色器／像素尺／量角器、區域截圖、視窗釘選、攝影機覆蓋層。
這些是「拿來量、拿來抓、拿來擺」的工具，和其他分頁的「拿來顯示」不同。

The tools page: colour picker / pixel ruler / protractor, region capture,
window pinning and the camera overlay. These are for measuring, grabbing and
arranging - as opposed to the other pages, which are for showing.
"""
from typing import List, Optional

from PySide6.QtCore import QBuffer, QIODevice, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QSpinBox,
    QWidget,
)

from frontengine.show.camera.camera_widget import (
    SHAPE_CIRCLE, SHAPE_RECTANGLE, SHAPE_ROUNDED, CameraWidget, list_cameras,
)
from frontengine.show.capture.region_capture import RegionCaptureWidget, is_usable
from frontengine.show.measure.measure_widget import (
    MODE_ANGLE, MODE_COLOR, MODE_RULER, MeasureWidget,
)
from frontengine.ui.dialog.screen_text_dialog import (
    ScreenTextDialog, ask_for_consent, has_consent,
)
from frontengine.ui.dialog.window_pin_dialog import WindowPinDialog
from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.ui.page.utils import coerce_int
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.measure.measure import (
    FORMAT_CSS_VAR, FORMAT_HEX, FORMAT_HSL, FORMAT_RGB,
)
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.screen_text.screen_text_service import (
    ACTION_ASK, ACTION_EXTRACT, ACTION_TRANSLATE, DEFAULT_LANGUAGE, ScreenTextService,
)
from frontengine.utils.recording.frame_recorder import (
    DEFAULT_FPS, DEFAULT_MAX_SECONDS, MAX_FPS, MIN_FPS, FrameRecorder,
)
from frontengine.utils.window_pin import window_pin
from frontengine.utils.window_pin.window_layout import capture_layout, restore_layout


# 三個地方共用的英文備援字串（翻譯缺漏時才會看到）
# The English fallback shared by three call sites, seen only when a
# translation is missing.
_RECORD_AREA = "Record area"


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


class ToolsSettingUI(QWidget):
    """工具設定頁 / The tools page."""

    def __init__(self):
        front_engine_logger.info("[ToolsSettingUI] Init")
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        self.measure_widget_list: List[MeasureWidget] = []
        self.recorder = FrameRecorder(self)
        self.screen_text_service = ScreenTextService(consent_provider=has_consent)
        self.last_screen_text: Optional[str] = None
        self.last_recording: Optional[str] = None
        self.capture_widget_list: List[RegionCaptureWidget] = []
        self.camera_widget_list: List[CameraWidget] = []
        self.last_capture: Optional[RegionCaptureWidget] = None
        self.pin_dialog: Optional[WindowPinDialog] = None

        self._build_measure_row()
        self._build_capture_row()
        self._build_screen_text_row()
        self._build_record_row()
        self._build_camera_row()
        self.pin_button = QPushButton(_t("tools_pin_window", "Pin a window..."))
        self.pin_button.clicked.connect(self.open_pin_dialog)

        # 視窗版面：記下每個視窗的位置，之後一鍵擺回去
        # Window layouts: remember where the windows are and put them back later.
        self.layout_label = QLabel(_t("tools_layout_label", "Window layout"))
        self.layout_name_edit = QLineEdit()
        self.layout_name_edit.setPlaceholderText(_t("tools_layout_name", "Layout name"))
        self.layout_save_button = QPushButton(_t("tools_layout_save", "Save layout"))
        self.layout_save_button.clicked.connect(self.save_layout)
        self.layout_combobox = QComboBox()
        self.layout_restore_button = QPushButton(_t("tools_layout_restore", "Restore"))
        self.layout_restore_button.clicked.connect(self.restore_selected_layout)
        for button in (self.layout_save_button, self.layout_restore_button):
            button.setEnabled(window_pin.available())
        self.reload_layouts()
        self.hint_label = QLabel(
            _t("tools_hint",
               "Click to measure; right-click clears. What you measure is copied to the "
               "clipboard. The camera is shown locally only - nothing is recorded."))
        self.hint_label.setWordWrap(True)

        self.grid_layout.addWidget(self.measure_label, 0, 0)
        self.grid_layout.addWidget(self.measure_mode_combobox, 0, 1)
        self.grid_layout.addWidget(self.measure_button, 0, 2)
        self.grid_layout.addWidget(self.color_format_label, 1, 0)
        self.grid_layout.addWidget(self.color_format_combobox, 1, 1)
        self.grid_layout.addWidget(self.capture_label, 2, 0)
        self.grid_layout.addWidget(self.capture_button, 2, 1)
        self.grid_layout.addWidget(self.capture_copy_button, 2, 2)
        self.grid_layout.addWidget(self.screen_text_label, 3, 0)
        self.grid_layout.addWidget(self.screen_text_combobox, 3, 1)
        self.grid_layout.addWidget(self.screen_text_button, 3, 2)
        self.grid_layout.addWidget(self.screen_text_input, 4, 1, 1, 2)
        self.grid_layout.addWidget(self.record_label, 5, 0)
        self.grid_layout.addWidget(self.record_fps_spinbox, 5, 1)
        self.grid_layout.addWidget(self.record_button, 5, 2)
        self.grid_layout.addWidget(self.record_seconds_spinbox, 6, 1)
        self.grid_layout.addWidget(self.record_camera_checkbox, 6, 2)
        self.grid_layout.addWidget(self.camera_label, 7, 0)
        self.grid_layout.addWidget(self.camera_shape_combobox, 7, 1)
        self.grid_layout.addWidget(self.camera_button, 7, 2)
        self.grid_layout.addWidget(self.camera_device_combobox, 8, 0, 1, 2)
        self.grid_layout.addWidget(self.camera_mirror_checkbox, 8, 2)
        self.grid_layout.addWidget(self.camera_border_label, 9, 0)
        self.grid_layout.addWidget(self.camera_border_spinbox, 9, 1)
        self.grid_layout.addWidget(self.pin_button, 10, 0)
        self.grid_layout.addWidget(self.layout_label, 11, 0)
        self.grid_layout.addWidget(self.layout_name_edit, 11, 1)
        self.grid_layout.addWidget(self.layout_save_button, 11, 2)
        self.grid_layout.addWidget(self.layout_combobox, 12, 0, 1, 2)
        self.grid_layout.addWidget(self.layout_restore_button, 12, 2)
        self.grid_layout.addWidget(self.hint_label, 13, 0, 1, 3)

    # --- construction helpers -------------------------------------------
    def _build_measure_row(self) -> None:
        self.measure_label = QLabel(_t("tools_measure_label", "Measure"))
        self.measure_mode_combobox = QComboBox()
        for mode, key, fallback in ((MODE_COLOR, "tools_measure_color", "Colour picker"),
                                    (MODE_RULER, "tools_measure_ruler", "Pixel ruler"),
                                    (MODE_ANGLE, "tools_measure_angle", "Protractor")):
            self.measure_mode_combobox.addItem(_t(key, fallback), mode)
        self.measure_mode_combobox.currentIndexChanged.connect(self._apply_measure_settings)
        self.color_format_label = QLabel(_t("tools_color_format", "Copy colour as"))
        self.color_format_combobox = QComboBox()
        for value, label in ((FORMAT_HEX, "#rrggbb"), (FORMAT_RGB, "rgb(r, g, b)"),
                             (FORMAT_HSL, "hsl(h, s%, l%)"), (FORMAT_CSS_VAR, "--color: ...;")):
            self.color_format_combobox.addItem(label, value)
        self.color_format_combobox.currentIndexChanged.connect(self._apply_measure_settings)
        self.measure_button = QPushButton(_t("tools_measure_start", "Start measuring"))
        self.measure_button.clicked.connect(self.toggle_measure)

    def _build_capture_row(self) -> None:
        self.capture_label = QLabel(_t("tools_capture_label", "Region capture"))
        self.capture_button = QPushButton(_t("tools_capture_start", "Capture area"))
        self.capture_button.clicked.connect(self.start_capture)
        self.capture_copy_button = QPushButton(_t("tools_capture_copy", "Copy last"))
        self.capture_copy_button.clicked.connect(self.copy_last_capture)

    def _build_screen_text_row(self) -> None:
        self.screen_text_label = QLabel(_t("tools_screen_text_label", "Read text"))
        self.screen_text_combobox = QComboBox()
        for action, key, fallback in ((ACTION_EXTRACT, "tools_screen_text_extract", "Copy text"),
                                      (ACTION_TRANSLATE, "tools_screen_text_translate", "Translate"),
                                      (ACTION_ASK, "tools_screen_text_ask", "Ask about it")):
            self.screen_text_combobox.addItem(_t(key, fallback), action)
        self.screen_text_input = QLineEdit()
        self.screen_text_input.setPlaceholderText(
            _t("tools_screen_text_input", "Language, or your question"))
        self.screen_text_input.setText(DEFAULT_LANGUAGE)
        self.screen_text_button = QPushButton(_t("tools_screen_text_start", "Read an area"))
        self.screen_text_button.clicked.connect(self.start_screen_text)

    def _build_record_row(self) -> None:
        self.record_label = QLabel(_t("tools_record_label", _RECORD_AREA))
        self.record_fps_spinbox = QSpinBox()
        self.record_fps_spinbox.setRange(MIN_FPS, MAX_FPS)
        self.record_fps_spinbox.setValue(DEFAULT_FPS)
        self.record_seconds_spinbox = QSpinBox()
        self.record_seconds_spinbox.setRange(1, 120)
        self.record_seconds_spinbox.setValue(DEFAULT_MAX_SECONDS)
        self.record_camera_checkbox = QCheckBox(_t("tools_record_camera", "Include camera"))
        self.record_button = QPushButton(_t("tools_record_start", _RECORD_AREA))
        self.record_button.clicked.connect(self.toggle_recording)

    def _build_camera_row(self) -> None:
        self.camera_label = QLabel(_t("tools_camera_label", "Camera"))
        self.camera_shape_combobox = QComboBox()
        for shape, key, fallback in ((SHAPE_CIRCLE, "tools_camera_circle", "Circle"),
                                     (SHAPE_ROUNDED, "tools_camera_rounded", "Rounded"),
                                     (SHAPE_RECTANGLE, "tools_camera_rectangle", "Rectangle")):
            self.camera_shape_combobox.addItem(_t(key, fallback), shape)
        self.camera_shape_combobox.currentIndexChanged.connect(self._apply_camera_settings)
        self.camera_device_combobox = QComboBox()
        for camera_id, description in list_cameras():
            self.camera_device_combobox.addItem(description, camera_id)
        if self.camera_device_combobox.count() == 0:
            self.camera_device_combobox.addItem(_t("tools_camera_none", "No camera found"), "")
        self.camera_mirror_checkbox = QCheckBox(_t("tools_camera_mirror", "Mirror"))
        self.camera_mirror_checkbox.setChecked(True)
        self.camera_mirror_checkbox.toggled.connect(self._apply_camera_settings)
        self.camera_border_label = QLabel(_t("tools_camera_border", "Border"))
        self.camera_border_spinbox = QSpinBox()
        self.camera_border_spinbox.setRange(0, 20)
        self.camera_border_spinbox.setValue(4)
        self.camera_border_spinbox.valueChanged.connect(self._apply_camera_settings)
        self.camera_button = QPushButton(_t("tools_camera_start", "Show camera"))
        self.camera_button.clicked.connect(self.toggle_camera)

    # --- measuring -------------------------------------------------------
    def toggle_measure(self) -> None:
        if self.measure_widget_list:
            self.stop_measure()
        else:
            self.start_measure()

    def start_measure(self) -> None:
        """開一層全螢幕量測覆蓋層。"""
        front_engine_logger.info("[ToolsSettingUI] start_measure")
        widget = MeasureWidget(self.measure_mode_combobox.currentData(),
                               self.color_format_combobox.currentData())
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            widget.setGeometry(screen.geometry())
        widget.setMouseTracking(True)
        widget.show()
        self.measure_widget_list.append(widget)
        self.measure_button.setText(_t("tools_measure_stop", "Stop measuring"))

    def stop_measure(self) -> None:
        for widget in self.measure_widget_list[:]:
            try:
                widget.close()
            except RuntimeError:
                pass
        self.measure_widget_list.clear()
        self.measure_button.setText(_t("tools_measure_start", "Start measuring"))

    def _apply_measure_settings(self) -> None:
        for widget in self.measure_widget_list[:]:
            try:
                widget.set_mode(self.measure_mode_combobox.currentData())
                widget.set_color_format(self.color_format_combobox.currentData())
            except RuntimeError:
                self.measure_widget_list.remove(widget)

    # --- region capture --------------------------------------------------
    def start_capture(self) -> RegionCaptureWidget:
        """開一層框選截圖（放開滑鼠就擷取並自己關掉）。"""
        front_engine_logger.info("[ToolsSettingUI] start_capture")
        widget = RegionCaptureWidget(on_captured=lambda pixmap, rect: self._on_captured(widget))
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            widget.setGeometry(screen.geometry())
        widget.setMouseTracking(True)
        widget.show()
        self.capture_widget_list.append(widget)
        return widget

    def _on_captured(self, widget: RegionCaptureWidget) -> None:
        """擷取完成：記住它並直接複製到剪貼簿。"""
        self.last_capture = widget
        widget.copy_to_clipboard()
        if widget in self.capture_widget_list:
            self.capture_widget_list.remove(widget)

    def copy_last_capture(self) -> bool:
        """把最近一次的截圖再放進剪貼簿一次。"""
        if self.last_capture is None:
            return False
        try:
            return self.last_capture.copy_to_clipboard()
        except RuntimeError:
            self.last_capture = None
            return False

    # --- camera ----------------------------------------------------------
    def toggle_camera(self) -> None:
        if self.camera_widget_list:
            self.stop_camera()
        else:
            self.start_camera()

    def start_camera(self) -> bool:
        """開一個攝影機覆蓋層；沒有裝置就什麼都不做。"""
        front_engine_logger.info("[ToolsSettingUI] start_camera")
        widget = CameraWidget(self.camera_shape_combobox.currentData(),
                              self.camera_border_spinbox.value(),
                              self.camera_mirror_checkbox.isChecked())
        widget.set_ui_window_flag(show_on_bottom=False)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            widget.move(area.x() + area.width() - widget.width() - 60,
                        area.y() + area.height() - widget.height() - 60)
        if not widget.start(self.camera_device_combobox.currentData() or None):
            widget.close()
            return False
        widget.show()
        self.camera_widget_list.append(widget)
        self.camera_button.setText(_t("tools_camera_stop", "Hide camera"))
        return True

    def stop_camera(self) -> None:
        for widget in self.camera_widget_list[:]:
            try:
                widget.close()
            except RuntimeError:
                pass
        self.camera_widget_list.clear()
        self.camera_button.setText(_t("tools_camera_start", "Show camera"))

    def _apply_camera_settings(self) -> None:
        for widget in self.camera_widget_list[:]:
            try:
                widget.set_shape(self.camera_shape_combobox.currentData())
                widget.set_border(self.camera_border_spinbox.value())
                widget.set_mirrored(self.camera_mirror_checkbox.isChecked())
            except RuntimeError:
                self.camera_widget_list.remove(widget)

    # --- window pinning --------------------------------------------------
    def open_pin_dialog(self) -> WindowPinDialog:
        """開視窗釘選對話框（關掉時會把釘過的視窗放開）。"""
        self.pin_dialog = WindowPinDialog(self)
        self.pin_dialog.exec()
        return self.pin_dialog

    def release_pinned_windows(self) -> None:
        """把釘過的別人視窗放開（主程式關閉時呼叫）。"""
        if self.pin_dialog is not None:
            try:
                self.pin_dialog.release_all()
            except RuntimeError:
                self.pin_dialog = None

    # --- reading text on screen ------------------------------------------
    def start_screen_text(self):
        """
        框一塊畫面來讀文字。第一次會先問過同意，沒同意就什麼都不做——
        這是唯一會把畫面內容送出機器的功能。
        Pick an area to read. The first use asks for consent and does nothing
        without it: this is the only feature that sends screen content off the
        machine.
        """
        if not ask_for_consent(self):
            front_engine_logger.info("[ToolsSettingUI] screen text cancelled: no consent")
            return None
        picker = RegionCaptureWidget(on_captured=lambda pixmap, rect: self._read_capture(pixmap))
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            picker.setGeometry(screen.geometry())
        picker.setMouseTracking(True)
        picker.show()
        self.capture_widget_list.append(picker)
        return picker

    def _read_capture(self, pixmap) -> None:
        """把框到的畫面送出去讀（在背景執行緒，UI 不會卡住）。"""
        data = pixmap_to_png(pixmap)
        if not data:
            return
        self.screen_text_service.read_async(
            data, self.show_screen_text,
            action=self.screen_text_combobox.currentData(),
            language=self.screen_text_input.text(),
            question=self.screen_text_input.text())

    def show_screen_text(self, text) -> None:
        """收到結果：切回 UI 執行緒再開視窗（回呼來自背景執行緒）。"""
        self.last_screen_text = text
        QTimer.singleShot(0, lambda: self._present_screen_text(text))

    def _present_screen_text(self, text):
        dialog = ScreenTextDialog(
            text or _t("tools_screen_text_empty", "Nothing came back."), self)
        dialog.exec()
        return dialog

    # --- recording -------------------------------------------------------
    def toggle_recording(self) -> None:
        if self.recorder.running:
            self.finish_recording()
        else:
            self.start_recording()

    def start_recording(self) -> RegionCaptureWidget:
        """先框一塊範圍，放開滑鼠後就從那塊開始錄。"""
        front_engine_logger.info("[ToolsSettingUI] start_recording")
        picker = RegionCaptureWidget()
        picker.finish = _recording_region_picker(self, picker)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            picker.setGeometry(screen.geometry())
        picker.setMouseTracking(True)
        picker.show()
        self.capture_widget_list.append(picker)
        return picker

    def begin_recording(self, region) -> bool:
        """對指定範圍開始錄製。"""
        inset = self.camera_inset if self.record_camera_checkbox.isChecked() else None
        self.recorder.set_inset_provider(inset)
        started = self.recorder.start(region, self.record_fps_spinbox.value(),
                                      self.record_seconds_spinbox.value())
        if started:
            self.record_button.setText(_t("tools_record_stop", "Stop recording"))
        return started

    def camera_inset(self) -> Optional[object]:
        """錄影時要疊上去的攝影機畫面（沒開攝影機就沒有）。"""
        for widget in self.camera_widget_list[:]:
            try:
                if widget.frame is not None:
                    return widget.frame
            except RuntimeError:
                self.camera_widget_list.remove(widget)
        return None

    def finish_recording(self) -> Optional[str]:
        """停止錄製並存成 GIF，回傳檔案路徑。"""
        self.recorder.stop()
        self.record_button.setText(_t("tools_record_start", _RECORD_AREA))
        if not self.recorder.frames:
            return None
        target = QFileDialog.getSaveFileName(
            self, _t("tools_record_save", "Save recording"), "recording.gif", "GIF (*.gif)")[0]
        if not target:
            self.recorder.clear()
            return None
        self.last_recording = self.recorder.save_gif(target)
        self.recorder.clear()
        return self.last_recording

    # --- window layouts --------------------------------------------------
    def saved_layouts(self) -> dict:
        """設定裡目前存了哪些版面。"""
        layouts = user_setting_dict.get("window_layouts")
        return layouts if isinstance(layouts, dict) else {}

    def reload_layouts(self) -> int:
        """重畫版面下拉選單，回傳數量。"""
        self.layout_combobox.clear()
        for name in sorted(self.saved_layouts()):
            self.layout_combobox.addItem(name, name)
        return self.layout_combobox.count()

    def save_layout(self) -> Optional[str]:
        """把目前所有視窗的位置存成一個版面；沒填名稱就不存。"""
        name = self.layout_name_edit.text().strip()
        if not name:
            return None
        layouts = dict(self.saved_layouts())
        layouts[name] = capture_layout()
        user_setting_dict["window_layouts"] = layouts
        write_user_setting()
        front_engine_logger.info(
            f"[ToolsSettingUI] saved layout {name!r} with {len(layouts[name])} window(s)")
        self.reload_layouts()
        index = self.layout_combobox.findData(name)
        if index >= 0:
            self.layout_combobox.setCurrentIndex(index)
        return name

    def restore_selected_layout(self) -> tuple:
        """把選到的版面套回去，回傳 (搬動數, 找不到數)。"""
        name = self.layout_combobox.currentData()
        if not name:
            return (0, 0)
        return restore_layout(self.saved_layouts().get(name, []))

    # --- preset state ----------------------------------------------------
    def get_state(self) -> dict:
        return {
            "measure_mode": self.measure_mode_combobox.currentData(),
            "color_format": self.color_format_combobox.currentData(),
            "camera_shape": self.camera_shape_combobox.currentData(),
            "camera_border": self.camera_border_spinbox.value(),
            "camera_mirror": self.camera_mirror_checkbox.isChecked(),
        }

    def set_state(self, state: dict) -> None:
        for combobox, key in ((self.measure_mode_combobox, "measure_mode"),
                              (self.color_format_combobox, "color_format"),
                              (self.camera_shape_combobox, "camera_shape")):
            value = state.get(key)
            if value is not None:
                index = combobox.findData(str(value))
                if index >= 0:
                    combobox.setCurrentIndex(index)
        border = coerce_int(state.get("camera_border"))
        if border is not None:
            self.camera_border_spinbox.setValue(max(0, min(20, border)))
        if "camera_mirror" in state:
            self.camera_mirror_checkbox.setChecked(bool(state["camera_mirror"]))


def _recording_region_picker(page: "ToolsSettingUI", picker: RegionCaptureWidget):
    """
    把框選層的 finish() 換成「不擷取畫面、只回報範圍給錄影」。錄影要的是
    連續的畫面，不是放開當下那一張。
    Replace the picker's finish() so it reports the region to the recorder
    instead of grabbing one still: a recording wants the frames that follow.
    """
    original_close = picker.close

    def finish(point):
        picker.extend(point)
        region = picker.selection()
        picker.origin = picker.current = None
        if picker in page.capture_widget_list:
            page.capture_widget_list.remove(picker)
        original_close()
        if region is not None and is_usable(region):
            page.begin_recording(region)
        return None

    return finish


def pixmap_to_png(pixmap) -> bytes:
    """
    把擷取到的畫面轉成 PNG 位元組（送出去用）。轉不出來就回傳空的，
    呼叫端會因此什麼都不送。
    The capture as PNG bytes, ready to send. An empty result means nothing is
    sent at all.
    """
    if pixmap is None or pixmap.isNull():
        return b""
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    saved = pixmap.save(buffer, "PNG")
    data = bytes(buffer.data()) if saved else b""
    buffer.close()
    return data
