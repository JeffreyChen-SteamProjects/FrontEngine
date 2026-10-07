"""
工具分頁：取色器／像素尺／量角器、區域截圖、視窗釘選、攝影機覆蓋層。
這些是「拿來量、拿來抓、拿來擺」的工具，和其他分頁的「拿來顯示」不同。

The tools page: colour picker / pixel ruler / protractor, region capture,
window pinning and the camera overlay. These are for measuring, grabbing and
arranging - as opposed to the other pages, which are for showing.
"""
from typing import List, Optional
from pathlib import Path
import sys

from PySide6.QtCore import QBuffer, QIODevice, QTimer, QRect
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QLabel, QLineEdit, QPushButton, QSpinBox, QMessageBox,
)

from frontengine.show.camera.camera_widget import (
    SHAPE_CIRCLE, SHAPE_RECTANGLE, SHAPE_ROUNDED, CameraWidget, list_cameras,
)
from frontengine.show.capture.region_capture import RegionCaptureWidget, is_usable
from frontengine.show.pinned.pinned_image import PinnedImageWidget
from frontengine.show.measure.measure_widget import (
    MODE_ANGLE, MODE_COLOR, MODE_RULER, MeasureWidget,
)
from frontengine.ui.dialog.screen_text_dialog import (
    ScreenTextDialog, ask_for_consent, has_consent, has_text_consent, ask_for_text_consent,
)
from frontengine.ui.dialog.color_palette_dialog import ColorPaletteDialog
from frontengine.utils.measure.color_palette import ColorPalette
from frontengine.ui.dialog.window_pin_dialog import WindowPinDialog
from frontengine.ui.dialog.window_replica_dialog import WindowReplicaDialog
from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.ui.page.utils import coerce_int
from frontengine.ui.page.layout_kit import SettingPage
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.measure.measure import (
    FORMAT_CSS_VAR, FORMAT_HEX, FORMAT_HSL, FORMAT_RGB,
)
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator, tr
from frontengine.utils.screen_text.screen_text_service import (
    ACTION_ASK, ACTION_EXTRACT, ACTION_TRANSLATE, DEFAULT_LANGUAGE, ScreenTextService, api_key,
)
from frontengine.utils.virtual_camera import virtual_camera
from frontengine.utils.virtual_camera.camera_feed import VirtualCameraFeed
from frontengine.utils.virtual_camera.virtual_camera import (
    DEFAULT_FPS as DEFAULT_VCAM_FPS, MAX_FPS as MAX_VCAM_FPS, MIN_FPS as MIN_VCAM_FPS,
)
from frontengine.utils.recording.frame_recorder import (
    DEFAULT_FPS, DEFAULT_MAX_SECONDS, MAX_FPS, MIN_FPS, FrameRecorder,
)
from frontengine.utils.window_pin.window_layout import capture_layout, restore_layout, available as layout_available


# 三個地方共用的英文備援字串（翻譯缺漏時才會看到）
# The English fallback shared by three call sites, seen only when a
# translation is missing.
_RECORD_AREA = "Record area"
_RECORD_AN_AREA = "Record an area"


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


class ToolsSettingUI(SettingPage):
    """工具設定頁 / The tools page."""

    def __init__(self):
        front_engine_logger.info("[ToolsSettingUI] Init")
        super().__init__("tab_tools_text", "page_subtitle_tools",
                         "Tools", "Measure, capture, record and pin what is on screen.")

        self._initialize_state()
        self._build_measure_row()
        self._build_capture_row()
        self._build_screen_text_row()
        self._build_record_row()
        self._build_virtual_camera_row()
        self._build_camera_row()
        self._build_window_row()
        self._add_tool_sections()
        self.add_body_widget(self.hint_label)
        self.finish_body()

    def _initialize_state(self) -> None:
        self.measure_widget_list: List[MeasureWidget] = []
        self.palette = ColorPalette(user_setting_dict, write_user_setting)
        self.palette_dialog = None
        self.recorder = FrameRecorder(self)
        self.virtual_camera_feed = VirtualCameraFeed(self)
        self.virtual_camera_feed.failed.connect(self._on_virtual_camera_failed)
        self.screen_text_service = ScreenTextService(consent_provider=has_consent,
                                                     text_consent_provider=has_text_consent)
        self.last_screen_text: Optional[str] = None
        self.last_recording: Optional[str] = None
        self.capture_widget_list: List[RegionCaptureWidget] = []
        # 釘住的截圖：使用者自己關掉之外，主程式結束時也要收乾淨
        # Pinned captures: closed by the user, and swept up on shutdown too
        self.pinned_widget_list: List[PinnedImageWidget] = []
        self.camera_widget_list: List[CameraWidget] = []
        # 存畫面本身，不要存那個覆蓋層：框選完它就自己 close() 了，而
        # WA_DeleteOnClose 會把底層物件銷毀，留下來的參考碰一下就 RuntimeError，
        # 「複製上一張」因此永遠是靜悄悄的沒反應。
        # Keep the pixmap, not the overlay: it closes itself once the selection
        # is made and WA_DeleteOnClose destroys it, so the surviving reference
        # raises RuntimeError on touch and "copy last" was a silent no-op.
        self.last_capture: Optional[QPixmap] = None
        self.capture_editor = None
        self.ocr_widget_list = []
        self.pin_dialog: Optional[WindowPinDialog] = None
        self.replica_dialog: Optional[WindowReplicaDialog] = None

    def _build_window_row(self) -> None:
        self.pin_button = tr(QPushButton(), "tools_pin_window", "Pin a window...")
        self.pin_button.clicked.connect(self.open_pin_dialog)

        # 視窗複本：原視窗留在原地，另外開一個小視窗顯示它的即時畫面
        # Window replica: the original stays put, a small window shows it live
        self.replica_button = tr(QPushButton(), "tools_replicate_window", "Replicate a window...")
        self.replica_button.clicked.connect(self.open_replica_dialog)

        # 視窗版面：記下每個視窗的位置，之後一鍵擺回去
        # Window layouts: remember where the windows are and put them back later.
        self.layout_label = tr(QLabel(), "tools_layout_label", "Window layout")
        self.layout_name_edit = QLineEdit()
        self.layout_name_edit.setPlaceholderText(_t("tools_layout_name", "Layout name"))
        self.layout_save_button = tr(QPushButton(), "tools_layout_save", "Save layout")
        self.layout_save_button.clicked.connect(self.save_layout)
        self.layout_combobox = QComboBox()
        self.layout_restore_button = tr(QPushButton(), "tools_layout_restore", "Restore")
        self.layout_restore_button.clicked.connect(self.restore_selected_layout)
        for button in (self.layout_save_button, self.layout_restore_button):
            button.setEnabled(layout_available())
        self.reload_layouts()
        self.hint_label = tr(QLabel(), "tools_hint",
            "Click to measure; right-click clears. What you measure is copied to the "
            "clipboard. The camera is shown locally only - nothing is recorded.")
        self.hint_label.setWordWrap(True)

    def _add_tool_sections(self) -> None:
        # 工具頁是八個彼此無關的工具。攤在同一個網格裡時，量測的設定看起來像是
        # 錄影也要用的，其實兩者毫無關係。
        # Eight unrelated tools. Flattened into one grid, the measuring settings
        # looked as if recording used them too; they have nothing to do with
        # each other.
        measure = self.add_section(self.measure_label)
        measure.add_row("tools_mode", self.measure_mode_combobox, "Mode")
        measure.add_row(self.color_format_label, self.color_format_combobox)
        measure.add_inline(self.measure_button, self.palette_collect, self.palette_button)
        measure.add_widget(self.palette_status)

        capture = self.add_section(self.capture_label)
        capture.add_inline(self.capture_button, self.capture_copy_button,
                           self.capture_pin_button, self.capture_edit_button)

        screen_text = self.add_section(self.screen_text_label)
        screen_text.add_row("tools_action", self.screen_text_combobox, "Action")
        screen_text.add_widget(self.screen_text_input)
        screen_text.add_inline(self.screen_text_button)
        self.live_ocr_button = tr(QPushButton(), 'live_ocr_title')
        self.live_ocr_button.clicked.connect(self.start_live_ocr)
        screen_text.add_inline(self.live_ocr_button)

        self._add_record_section()

        virtual_camera = self.add_section(self.virtual_camera_label)
        virtual_camera.add_row("tools_fps", self.virtual_camera_fps_spinbox,
                               "Frames per second")
        virtual_camera.add_inline(self.virtual_camera_button)
        virtual_camera.add_widget(self.virtual_camera_status)

        camera = self.add_section(self.camera_label)
        camera.add_row("tools_device", self.camera_device_combobox, "Device")
        camera.add_row("tools_shape", self.camera_shape_combobox, "Shape")
        camera.add_row(self.camera_border_label, self.camera_border_spinbox)
        camera.add_inline(self.camera_mirror_checkbox)
        camera.add_inline(self.camera_button)

        windows = self.add_section(self.layout_label)
        windows.add_row("tools_name", self.layout_name_edit, "Name")
        windows.add_inline(self.layout_save_button)
        windows.add_row("tools_saved", self.layout_combobox, "Saved")
        windows.add_inline(self.layout_restore_button, self.pin_button, self.replica_button)

    # --- construction helpers -------------------------------------------
    def _build_measure_row(self) -> None:
        self.measure_label = tr(QLabel(), "tools_measure_label", "Measure")
        self.measure_mode_combobox = QComboBox()
        for mode, key, fallback in ((MODE_COLOR, "tools_measure_color", "Colour picker"),
                                    (MODE_RULER, "tools_measure_ruler", "Pixel ruler"),
                                    (MODE_ANGLE, "tools_measure_angle", "Protractor")):
            self.measure_mode_combobox.addItem(_t(key, fallback), mode)
        self.measure_mode_combobox.currentIndexChanged.connect(self._apply_measure_settings)
        self.color_format_label = tr(QLabel(), "tools_color_format", "Copy colour as")
        self.color_format_combobox = QComboBox()
        for value, label in ((FORMAT_HEX, "#rrggbb"), (FORMAT_RGB, "rgb(r, g, b)"),
                             (FORMAT_HSL, "hsl(h, s%, l%)"), (FORMAT_CSS_VAR, "--color: ...;")):
            self.color_format_combobox.addItem(label, value)
        self.color_format_combobox.currentIndexChanged.connect(self._apply_measure_settings)
        self.measure_button = tr(QPushButton(), "tools_measure_start", "Start measuring")
        self.measure_button.clicked.connect(self.toggle_measure)
        self.palette_collect = tr(QCheckBox(), "palette_collect")
        self.palette_collect.setChecked(user_setting_dict.get("color_palette_collect") is True)
        self.palette_collect.toggled.connect(self._save_palette_collect)
        self.palette_button = tr(QPushButton(), "palette_title")
        self.palette_button.clicked.connect(self.open_palette)
        self.palette_status = QLabel()
        self.palette_status.setWordWrap(True)

    def _build_capture_row(self) -> None:
        self.capture_label = tr(QLabel(), "tools_capture_label", "Region capture")
        self.capture_button = tr(QPushButton(), "tools_capture_start", "Capture area")
        self.capture_button.clicked.connect(self.start_capture)
        self.capture_copy_button = tr(QPushButton(), "tools_capture_copy", "Copy last")
        self.capture_pin_button = tr(QPushButton(), "tools_capture_pin", "Pin last")
        self.capture_pin_button.clicked.connect(self.pin_last_capture)
        self.capture_copy_button.clicked.connect(self.copy_last_capture)
        self.capture_edit_button = tr(QPushButton(), 'capture_edit_title')
        self.capture_edit_button.clicked.connect(self.edit_last_capture)

    def _build_screen_text_row(self) -> None:
        self.screen_text_label = tr(QLabel(), "tools_screen_text_label", "Read text")
        self.screen_text_combobox = QComboBox()
        for action, key, fallback in ((ACTION_EXTRACT, "tools_screen_text_extract", "Copy text"),
                                      (ACTION_TRANSLATE, "tools_screen_text_translate", "Translate"),
                                      (ACTION_ASK, "tools_screen_text_ask", "Ask about it")):
            self.screen_text_combobox.addItem(_t(key, fallback), action)
        self.screen_text_input = QLineEdit()
        self.screen_text_input.setPlaceholderText(
            _t("tools_screen_text_input", "Language, or your question"))
        self.screen_text_input.setText(DEFAULT_LANGUAGE)
        self.screen_text_button = tr(QPushButton(), "tools_screen_text_start", "Read an area")
        self.screen_text_button.clicked.connect(self.start_screen_text)

    def _build_record_row(self) -> None:
        self.record_label = tr(QLabel(), "tools_record_label", _RECORD_AREA)
        self.record_fps_spinbox = QSpinBox()
        self.record_fps_spinbox.setRange(MIN_FPS, MAX_FPS)
        self.record_fps_spinbox.setValue(DEFAULT_FPS)
        self.record_seconds_spinbox = QSpinBox()
        self.record_seconds_spinbox.setRange(1, 120)
        self.record_seconds_spinbox.setValue(DEFAULT_MAX_SECONDS)
        self.record_format = QComboBox()
        self.record_format.addItem('GIF', 'gif')
        self.record_format.addItem('AVI (Motion JPEG)', 'avi')
        self.record_format.currentIndexChanged.connect(self._record_format_changed)
        self.record_camera_checkbox = tr(QCheckBox(), "tools_record_camera", "Include camera")
        self.record_button = tr(QPushButton(), "tools_record_start", _RECORD_AN_AREA)
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_pause = tr(QPushButton(), 'tools_record_pause')
        self.record_pause.clicked.connect(self._toggle_record_pause)
        self.record_pause.setEnabled(False)
        self.record_cancel = tr(QPushButton(), 'tools_record_cancel')
        self.record_cancel.clicked.connect(self.recorder.close)
        self.record_cancel.setEnabled(False)
        self.record_status = tr(QLabel(), "tools_record_ready", "Ready")
        self._recording_error = ""
        self._recording_detail = (0, 0.0, 0)
        retranslator.bind_call(self._update_recording_error)
        retranslator.bind_call(self._update_recording_detail)
        self.recorder.finished.connect(self._on_recording_stopped)
        self.recorder.completed.connect(self._on_recording_completed)
        self.recorder.failed.connect(self._on_recording_failed)
        self.recorder.state_changed.connect(self._recording_state_changed)
        self.recorder.progress.connect(self._recording_progress)

    def _add_record_section(self) -> None:
        section = self.add_section(self.record_label)
        section.add_row('tools_record_format', self.record_format)
        section.add_row('tools_fps', self.record_fps_spinbox)
        section.add_row('tools_seconds', self.record_seconds_spinbox)
        section.add_inline(self.record_camera_checkbox)
        section.add_inline(self.record_button, self.record_pause, self.record_cancel)
        section.add_widget(self.record_status)

    def _record_format_changed(self, _index: int) -> None:
        self.record_seconds_spinbox.setMaximum(3600 if self.record_format.currentData() == 'avi' else 120)

    def _toggle_record_pause(self) -> None:
        self.recorder.resume() if self.recorder.state == 'paused' else self.recorder.pause()

    def _recording_state_changed(self, state: str) -> None:
        editable = state == 'idle'
        for widget in (self.record_format, self.record_fps_spinbox, self.record_seconds_spinbox,
                       self.record_camera_checkbox):
            widget.setEnabled(editable)
        self.record_button.setEnabled(state in ('idle', 'recording', 'paused'))
        self.record_pause.setEnabled(state in ('recording', 'paused'))
        self.record_cancel.setEnabled(state in ('recording', 'paused', 'finalizing'))
        retranslator.set_text(self.record_pause, 'tools_record_resume' if state == 'paused' else 'tools_record_pause')
        self._update_recording_detail()

    def _recording_progress(self, frames: int, seconds: float, dropped: int) -> None:
        self._recording_detail = (frames, seconds, dropped)
        self._update_recording_detail()

    def _update_recording_detail(self) -> None:
        if self.recorder.state not in ('recording', 'paused'):
            return
        frames, seconds, dropped = self._recording_detail
        label = _t('tools_record_paused', 'Paused') if self.recorder.state == 'paused' else _t('tools_record_active', 'Recording')
        retranslator.forget(self.record_status)
        self.record_status.setText(_t('tools_record_detail', '{state} · {seconds:.1f}s · {frames} frames · {dropped} dropped').format(
            state=label, seconds=seconds, frames=frames, dropped=dropped))

    def _build_virtual_camera_row(self) -> None:
        self.virtual_camera_label = tr(QLabel(), "tools_vcam_label", "Virtual camera")
        self.virtual_camera_fps_spinbox = QSpinBox()
        self.virtual_camera_fps_spinbox.setRange(MIN_VCAM_FPS, MAX_VCAM_FPS)
        self.virtual_camera_fps_spinbox.setValue(DEFAULT_VCAM_FPS)
        self.virtual_camera_button = tr(QPushButton(), "tools_vcam_start", "Send an area")
        self.virtual_camera_button.clicked.connect(self.toggle_virtual_camera)
        status_key, status_fallback = (
            ("tools_vcam_ready", "Ready") if virtual_camera.available()
            else ("tools_vcam_missing", "Install pyvirtualcam and a virtual camera driver"))
        self.virtual_camera_status = QLabel(_t(status_key, status_fallback))
        retranslator.bind(self.virtual_camera_status, status_key, status_fallback)
        self.virtual_camera_status.setWordWrap(True)
        self.virtual_camera_button.setEnabled(virtual_camera.available())

    def _build_camera_row(self) -> None:
        self.camera_label = tr(QLabel(), "tools_camera_label", "Camera")
        self.camera_shape_combobox = QComboBox()
        for shape, key, fallback in ((SHAPE_CIRCLE, "tools_camera_circle", "Circle"),
                                     (SHAPE_ROUNDED, "tools_camera_rounded", "Rounded"),
                                     (SHAPE_RECTANGLE, "tools_camera_rectangle", "Rectangle")):
            self.camera_shape_combobox.addItem(_t(key, fallback), shape)
        self.camera_shape_combobox.currentIndexChanged.connect(self._apply_camera_settings)
        self.camera_device_combobox = QComboBox()
        self.reload_cameras()
        self.camera_mirror_checkbox = tr(QCheckBox(), "tools_camera_mirror", "Mirror")
        self.camera_mirror_checkbox.setChecked(True)
        self.camera_mirror_checkbox.toggled.connect(self._apply_camera_settings)
        self.camera_border_label = tr(QLabel(), "tools_camera_border", "Border")
        self.camera_border_spinbox = QSpinBox()
        self.camera_border_spinbox.setRange(0, 20)
        self.camera_border_spinbox.setValue(4)
        self.camera_border_spinbox.valueChanged.connect(self._apply_camera_settings)
        self.camera_button = tr(QPushButton(), "tools_camera_start", "Show camera")
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
        widget.color_sampled.connect(self._record_palette_color)
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

    def open_palette(self) -> None:
        """Show one persistent manager for stored colors and recent samples."""
        if self.palette_dialog is None:
            self.palette_dialog = ColorPaletteDialog(self, self.palette)
        self.palette_dialog.show()
        self.palette_dialog.raise_()
        self.palette_dialog.activateWindow()

    def start_palette_pick(self) -> None:
        """Enable consecutive color collection using the existing picker overlay."""
        self.palette_collect.setChecked(True)
        self.measure_mode_combobox.setCurrentIndex(self.measure_mode_combobox.findData(MODE_COLOR))
        if not self.measure_widget_list:
            self.start_measure()

    def _save_palette_collect(self, enabled: bool) -> None:
        user_setting_dict["color_palette_collect"] = enabled
        try:
            write_user_setting()
        except OSError as error:
            self.palette_status.setText(str(error))

    def _record_palette_color(self, color: str) -> None:
        if not self.palette_collect.isChecked():
            return
        try:
            self.palette.sample(color)
            self.palette_status.clear()
        except (OSError, ValueError) as error:
            self.palette_status.setText(str(error))
        if self.palette_dialog is not None:
            self.palette_dialog.refresh()

    def close_palette(self) -> None:
        """Hide the management dialog during application shutdown."""
        if self.palette_dialog is not None:
            self.palette_dialog.close()

    def closeEvent(self, event) -> None:
        self.close_palette()
        super().closeEvent(event)

    # --- region capture --------------------------------------------------
    def start_capture(self) -> RegionCaptureWidget:
        """開一層框選截圖（放開滑鼠就擷取並自己關掉）。"""
        front_engine_logger.info("[ToolsSettingUI] start_capture")
        widget = RegionCaptureWidget(
            on_captured=lambda pixmap, rect: self._on_captured(widget, pixmap))
        widget.failed.connect(self._on_capture_failed)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            widget.setGeometry(screen.geometry())
        widget.setMouseTracking(True)
        widget.show()
        self.capture_widget_list.append(widget)
        return widget

    def _on_captured(self, widget: RegionCaptureWidget, pixmap: QPixmap) -> None:
        """擷取完成：記住畫面並直接複製到剪貼簿。"""
        self.last_capture = pixmap
        widget.copy_to_clipboard()
        if widget in self.capture_widget_list:
            self.capture_widget_list.remove(widget)

    def pin_last_capture(self) -> Optional[PinnedImageWidget]:
        """
        把最近一次的截圖釘在畫面上。沒有截過就什麼都不做——開一個空白視窗只會讓
        使用者以為截圖壞了。
        Pin the most recent capture. With nothing captured this does nothing: an
        empty window would read as the capture having failed.
        """
        if self.last_capture is None or self.last_capture.isNull():
            front_engine_logger.info("[ToolsSettingUI] nothing captured to pin")
            return None
        pinned = PinnedImageWidget(self.last_capture)
        pinned.show()
        self.pinned_widget_list.append(pinned)
        return pinned

    def edit_last_capture(self) -> None:
        """Edit a detached copy so the last original capture stays available."""
        if self.last_capture is None or self.last_capture.isNull():
            return
        from frontengine.ui.dialog.capture_editor import CaptureEditor
        self.close_capture_editor()
        self.capture_editor = CaptureEditor(self.last_capture.toImage(), self)
        self.capture_editor.pin_requested.connect(self._pin_edited_capture)
        editor = self.capture_editor
        editor.finished.connect(lambda _result: self._capture_editor_finished(editor))
        self.capture_editor.show()

    def _capture_editor_finished(self, editor) -> None:
        if self.capture_editor is editor:
            self.capture_editor = None

    def _pin_edited_capture(self, image) -> None:
        pinned = PinnedImageWidget(QPixmap.fromImage(image))
        pinned.show()
        self.pinned_widget_list.append(pinned)

    def close_capture_editor(self) -> None:
        """Close the capture document before releasing its owner."""
        if self.capture_editor is not None:
            self.capture_editor.close()
            self.capture_editor = None

    def close_pinned(self) -> None:
        """關掉所有釘住的截圖（主程式關閉時呼叫）。"""
        # 用切片而不是 list()：邊走邊關的時候原清單有可能被動到，而 Sonar 對
        # list() 會抱怨、對切片不會。
        # A slice rather than list(): the original can still be touched while
        # closing, and Sonar objects to list() but not to slicing.
        for pinned in self.pinned_widget_list[:]:
            try:
                pinned.close()
            except RuntimeError:  # pragma: no cover - 底層物件已消失
                pass
        self.pinned_widget_list.clear()

    def copy_last_capture(self) -> bool:
        """把最近一次的截圖再放進剪貼簿一次。"""
        if self.last_capture is None or self.last_capture.isNull():
            return False
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:  # pragma: no cover - no clipboard at all
            return False
        clipboard.setPixmap(self.last_capture)
        return True

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

    def open_replica_dialog(self) -> WindowReplicaDialog:
        """開視窗複本對話框（關掉主程式時會把開過的複本收乾淨）。"""
        self.replica_dialog = WindowReplicaDialog(self)
        self.replica_dialog.exec()
        return self.replica_dialog

    def close_replicas(self) -> None:
        """關掉開過的視窗複本（主程式關閉時呼叫）。"""
        if self.replica_dialog is not None:
            try:
                self.replica_dialog.close_all()
            except RuntimeError:
                self.replica_dialog = None

    def release_pinned_windows(self) -> None:
        """把釘過的別人視窗放開（主程式關閉時呼叫）。"""
        if self.pin_dialog is not None:
            try:
                self.pin_dialog.release_all()
            except RuntimeError:
                self.pin_dialog = None

    def reload_cameras(self) -> int:
        """
        重新列出可用的視訊來源。擷取卡與外接攝影機常常是程式開著才插上去的，
        所以清單要能重新整理，不然只有重開才看得到。
        Re-list the available video sources. Capture cards and external cameras
        are usually plugged in while the app is already running, so the list has
        to be refreshable or they only appear after a restart.
        """
        self.camera_device_combobox.clear()
        for camera_id, description in list_cameras():
            self.camera_device_combobox.addItem(description, camera_id)
        if self.camera_device_combobox.count() == 0:
            self.camera_device_combobox.addItem(_t("tools_camera_none", "No camera found"), "")
        return self.camera_device_combobox.count()

    # --- virtual camera ---------------------------------------------------
    def toggle_virtual_camera(self):
        if self.virtual_camera_feed.running:
            self.stop_virtual_camera()
            return None
        return self.start_virtual_camera()

    def start_virtual_camera(self):
        """框一塊畫面，放開滑鼠後把那塊持續送進虛擬攝影機。"""
        front_engine_logger.info("[ToolsSettingUI] start_virtual_camera")
        picker = RegionCaptureWidget()
        picker.finish = _virtual_camera_region_picker(self, picker)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            picker.setGeometry(screen.geometry())
        picker.setMouseTracking(True)
        picker.show()
        self.capture_widget_list.append(picker)
        return picker

    def begin_virtual_camera(self, region) -> bool:
        """對指定範圍開始輸出。"""
        started = self.virtual_camera_feed.start(region, self.virtual_camera_fps_spinbox.value())
        if started:
            self.virtual_camera_button.setText(_t("tools_vcam_stop", "Stop sending"))
            self.virtual_camera_status.setText(
                _t("tools_vcam_sending", "Sending to {device}").format(
                    device=self.virtual_camera_feed.device_name()))
        return started

    def stop_virtual_camera(self) -> None:
        self.virtual_camera_feed.stop()
        self.virtual_camera_button.setText(_t("tools_vcam_start", "Send an area"))
        self.virtual_camera_status.setText(_t("tools_vcam_ready", "Ready"))

    def _on_virtual_camera_failed(self, reason: str) -> None:
        """開不起來時照實說明，不要只是沒反應。"""
        front_engine_logger.warning(f"[ToolsSettingUI] virtual camera failed: {reason}")
        self.virtual_camera_status.setText(
            _t("tools_vcam_failed", "Could not start: {reason}").format(reason=reason))

    # --- reading text on screen ------------------------------------------
    def start_screen_text(self):
        """
        框一塊畫面來讀文字。第一次會先問過同意，沒同意就什麼都不做——
        這是唯一會把畫面內容送出機器的功能。
        Pick an area to read. The first use asks for consent and does nothing
        without it: this is the only feature that sends screen content off the
        machine.
        """
        picker = RegionCaptureWidget(on_captured=lambda pixmap, rect: self._read_capture(pixmap))
        picker.failed.connect(self._on_capture_failed)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            picker.setGeometry(screen.geometry())
        picker.setMouseTracking(True)
        picker.show()
        self.capture_widget_list.append(picker)
        return picker

    def start_live_ocr(self) -> RegionCaptureWidget | None:
        """Select one fixed screen region for a manual-first, locally recognized OCR window."""
        if len(self.ocr_widget_list) >= 4:
            self.ocr_widget_list = [widget for widget in self.ocr_widget_list if not widget.closed]
        if len(self.ocr_widget_list) >= 4:
            self._on_capture_failed(_t('live_ocr_limit', 'Close an OCR window before opening another (maximum four).'))
            return None
        picker = RegionCaptureWidget(on_captured=lambda pixmap, rect: self._live_ocr_selected(picker, rect))
        picker.failed.connect(self._on_capture_failed)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            picker.setGeometry(screen.geometry())
        picker.setMouseTracking(True)
        picker.show()
        self.capture_widget_list.append(picker)
        return picker

    def _live_ocr_selected(self, picker, rect: QRect) -> None:
        from frontengine.show.pinned.live_ocr_widget import LiveOcrWidget
        from frontengine.utils.screen_text.live_ocr import make_live_reader
        region = QRect(rect) if sys.platform == 'darwin' else QRect(picker.mapToGlobal(rect.topLeft()), rect.size())
        widget = LiveOcrWidget(region, make_live_reader(self.screen_text_service))
        widget.consent_requested.connect(lambda kind: self._review_ocr_consent(widget, kind))
        screen = QGuiApplication.screenAt(region.center())
        if screen is not None:
            available = screen.availableGeometry()
            x = max(available.left(), min(available.right()-widget.width()+1, region.right()+12))
            y = max(available.top(), min(available.bottom()-widget.height()+1, region.top()))
            widget.move(x, y)
        widget.show()
        self.ocr_widget_list.append(widget)
        if picker in self.capture_widget_list:
            self.capture_widget_list.remove(picker)
        QTimer.singleShot(100, widget, widget.refresh)

    def _review_ocr_consent(self, widget, kind: str) -> None:
        if api_key() is None:
            widget._failed('Set ANTHROPIC_API_KEY to enable explicitly requested cloud fallback')
            return
        granted = ask_for_text_consent(widget) if kind == 'text' else ask_for_consent(widget)
        if granted:
            widget.refresh()

    def close_live_ocr(self) -> None:
        """Stop region sources and late OCR result delivery before clearing the widget registry."""
        for widget in self.ocr_widget_list[:]:
            try:
                widget.close()
            except RuntimeError:
                pass
        self.ocr_widget_list.clear()

    def _read_capture(self, pixmap) -> None:
        """把框到的畫面送出去讀（在背景執行緒，UI 不會卡住）。"""
        data = pixmap_to_png(pixmap)
        if not data:
            return
        action = self.screen_text_combobox.currentData()
        value = self.screen_text_input.text()
        self._request_screen_text(data, action, value, value)

    def _request_screen_text(self, data, action, language, question) -> None:
        def reply(result):
            QTimer.singleShot(0, self, lambda: self._handle_screen_text_result(
                result, data, action, language, question))
        self.screen_text_service.read_result_async(data, reply, action=action,
                                                  language=language, question=question)

    def _handle_screen_text_result(self, result, data, action, language, question) -> None:
        if result.consent_required and api_key() is not None:
            consent = ask_for_text_consent(self) if result.consent_required == 'text' else ask_for_consent(self)
            if consent:
                self._request_screen_text(data, action, language, question)
                return
        self.last_screen_text = result.text if result.status == 'success' else None
        self._present_screen_text_result(result)

    def _present_screen_text_result(self, result) -> None:
        ScreenTextDialog(parent=self, result=result).exec()

    def _on_capture_failed(self, reason: str) -> None:
        QMessageBox.warning(self, _t('tab_tools_text', 'Tools'),
                            _t('tools_capture_failed', 'Capture failed: {reason}').format(reason=reason))

    def show_screen_text(self, text) -> None:
        """收到結果：切回 UI 執行緒再開視窗（回呼來自背景執行緒）。"""
        self.last_screen_text = text
        # 一定要傳 context 物件（self），否則計時器會被建在沒有事件迴圈的背景
        # 執行緒上，永遠不會觸發，結果視窗根本不會打開。
        # The context object (self) is essential: without it the timer is created
        # on the worker thread, which has no event loop, so it never fires and
        # the result window simply never opens.
        QTimer.singleShot(0, self, lambda: self._present_screen_text(text))

    def _present_screen_text(self, text):
        dialog = ScreenTextDialog(
            text or _t("tools_screen_text_empty", "Nothing came back."), self)
        dialog.exec()
        return dialog

    # --- recording -------------------------------------------------------
    def toggle_recording(self) -> None:
        if self.recorder.state in ('recording', 'paused'):
            self.finish_recording()
        elif not self.recorder.busy:
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
        if self.recorder.busy:
            return False
        output_format = self.record_format.currentData()
        file_filter = 'AVI (*.avi)' if output_format == 'avi' else 'GIF (*.gif)'
        target = QFileDialog.getSaveFileName(
            self, _t("tools_record_save", "Save recording"), 'recording.' + output_format, file_filter)[0]
        if not target:
            return False
        target = str(Path(target).with_suffix('.' + output_format))
        self._recording_error = ""
        inset = self.camera_inset if self.record_camera_checkbox.isChecked() else None
        self.recorder.set_inset_provider(inset)
        started = self.recorder.start(region, target, self.record_fps_spinbox.value(),
                                     self.record_seconds_spinbox.value(), output_format=output_format)
        if started and self.recorder.running:
            retranslator.set_text(self.record_button, "tools_record_stop", "Stop recording")
            self._update_recording_detail()
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

    def finish_recording(self) -> None:
        """Stop capture; the background writer reports the finalized path."""
        self.recorder.stop()

    def _on_recording_stopped(self, _count: int) -> None:
        self.record_button.setEnabled(False)
        retranslator.set_text(self.record_button, "tools_record_finalizing", "Saving recording…")
        retranslator.set_text(self.record_status, "tools_record_finalizing", "Saving recording…")

    def _on_recording_completed(self, path: Optional[str]) -> None:
        self._recording_error = ""
        self.last_recording = path
        self.record_button.setEnabled(True)
        retranslator.set_text(self.record_button, "tools_record_start", _RECORD_AN_AREA)
        key = "tools_record_saved" if path else "tools_record_ready"
        fallback = "Recording saved" if path else "Ready"
        retranslator.set_text(self.record_status, key, fallback)

    def _on_recording_failed(self, reason: str) -> None:
        self.record_button.setEnabled(True)
        retranslator.set_text(self.record_button, "tools_record_start", _RECORD_AN_AREA)
        self._recording_error = reason
        retranslator.forget(self.record_status)
        self._update_recording_error()

    def _update_recording_error(self) -> None:
        if self._recording_error:
            self.record_status.setText(
                _t("tools_record_failed", "Recording failed: {reason}").format(
                    reason=self._recording_error))

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


def _virtual_camera_region_picker(page: "ToolsSettingUI", picker: RegionCaptureWidget):
    """框選層放開滑鼠時，把範圍交給虛擬攝影機而不是擷取一張靜態畫面。"""
    original_close = picker.close

    def finish(point):
        picker.extend(point)
        region = picker.selection()
        picker.origin = picker.current = None
        if picker in page.capture_widget_list:
            page.capture_widget_list.remove(picker)
        original_close()
        if region is not None and is_usable(region):
            page.begin_virtual_camera(region)
        return None

    return finish
