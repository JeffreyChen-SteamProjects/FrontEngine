from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QComboBox, QGridLayout, QLabel, QPushButton, QScrollArea, QTextEdit, QWidget,
)

from frontengine.show.window_helpers import set_overlay_locked
from frontengine.ui.color.global_color import error_color, output_color
from frontengine.ui.page.gif.gif_setting_ui import GIFSettingUI
from frontengine.ui.page.image.image_setting_ui import ImageSettingUI
from frontengine.ui.page.particle.particle_setting_ui import ParticleSettingUI
from frontengine.ui.page.scene_setting.scene_setting_ui import SceneSettingUI
from frontengine.ui.page.sound_player.sound_player_setting_ui import SoundPlayerSettingUI
from frontengine.ui.page.text.text_setting_ui import TextSettingUI
from frontengine.ui.page.video.video_setting_ui import VideoSettingUI
from frontengine.ui.page.web.web_setting_ui import WEBSettingUI
from frontengine.user_setting.user_setting_file import clear_overlay_geometry
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.power_mode.power_mode import (
    TIER_BALANCED, TIER_HIGH, TIER_SAVER, normalize_tier,
)
from frontengine.utils.redirect_manager.redirect_manager_class import redirect_manager_instance


class ControlCenterUI(QWidget):
    """
    ControlCenterUI: 控制中心面板，集中管理各種 widget 與 log panel
    ControlCenterUI: Control center panel to manage widgets and log panel
    """

    def __init__(
            self,
            video_setting_ui: VideoSettingUI,
            image_setting_ui: ImageSettingUI,
            web_setting_ui: WEBSettingUI,
            gif_setting_ui: GIFSettingUI,
            sound_player_setting_ui: SoundPlayerSettingUI,
            text_setting_ui: TextSettingUI,
            scene_setting_ui: SceneSettingUI,
            particle_setting_ui: ParticleSettingUI,
            redirect_output: bool = True,
            pet_setting_ui=None,
    ):
        front_engine_logger.info(
            f"[ControlCenterUI] Init | video={video_setting_ui}, image={image_setting_ui}, web={web_setting_ui}, "
            f"gif={gif_setting_ui}, sound={sound_player_setting_ui}, text={text_setting_ui}, "
            f"scene={scene_setting_ui}, particle={particle_setting_ui}, redirect_output={redirect_output}"
        )
        super().__init__()

        # Layout
        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # UI instance
        self.video_setting_ui = video_setting_ui
        self.image_setting_ui = image_setting_ui
        self.web_setting_ui = web_setting_ui
        self.gif_setting_ui = gif_setting_ui
        self.sound_player_setting_ui = sound_player_setting_ui
        self.text_setting_ui = text_setting_ui
        self.scene_setting_ui = scene_setting_ui
        self.particle_setting_ui = particle_setting_ui
        self.pet_setting_ui = pet_setting_ui

        # Buttons
        self.clear_video_button = self._create_button("control_center_close_all_video", self.clear_video)
        self.clear_image_button = self._create_button("control_center_close_all_image", self.clear_image)
        self.clear_gif_button = self._create_button("control_center_close_all_gif", self.clear_gif)
        self.clear_web_button = self._create_button("control_center_close_all_web", self.clear_web)
        self.clear_sound_button = self._create_button("control_center_close_all_sound", self.clear_sound)
        self.clear_text_button = self._create_button("control_center_close_all_text", self.clear_text)
        self.clear_scene_button = self._create_button("control_center_scene", self.clear_scene)
        self.clear_redirect_button = self._create_button("control_center_clear_log_panel", self.clear_redirect)
        self.clear_chat_button = self._create_button("chat_scene_close", self.clear_scene)  # 修正：應該關閉場景而不是 redirect
        self.hide_all_button = self._create_button("control_center_hide_all", self.hide_all)
        self.show_all_button = self._create_button("control_center_show_all", self.show_all)
        # 全域靜音狀態 / Global mute state
        self._muted = False
        # 全域不透明度（None 表示尚未使用過）/ Global opacity level (None until first used)
        self._global_opacity = None
        self.mute_all_button = self._create_button("control_center_mute_all", self.toggle_mute_all)
        # 覆蓋層鎖定（點擊穿透）與綠幕背景 / Overlay lock (click-through) and chroma key
        self._overlays_locked = True
        self._chroma_key = False
        self.lock_all_button = self._create_button("control_center_unlock_all", self.toggle_lock_all)
        self.chroma_key_button = self._create_button("control_center_chroma_key_on", self.toggle_chroma_key)
        self.reset_positions_button = self._create_button(
            "control_center_reset_positions", self.reset_overlay_positions)
        self._low_power = False
        # 其他分頁登記進來的覆蓋層來源（桌布、專注、護眼、簡報…）
        # Overlay sources registered by the other pages: wallpaper, focus, screen care, presenting.
        self._extra_overlay_sources: list = []
        self.low_power_button = self._create_button(
            "control_center_low_power_on", self.toggle_low_power)
        self.clear_all_button = self._create_button("control_center_close_all", self.clear_all)

        # 畫質檔位：比省電模式更細，一次套用到所有覆蓋層
        # Quality tier: finer than the low-power switch, applied to every overlay.
        self.quality_label = QLabel(
            language_wrapper.language_word_dict.get("control_center_quality", "Quality"))
        self.quality_combobox = QComboBox()
        for tier, key, fallback in (
                (TIER_HIGH, "control_center_quality_high", "High"),
                (TIER_BALANCED, "control_center_quality_balanced", "Balanced"),
                (TIER_SAVER, "control_center_quality_saver", "Saver")):
            self.quality_combobox.addItem(
                language_wrapper.language_word_dict.get(key, fallback), tier)
        self.quality_combobox.currentIndexChanged.connect(self._apply_quality_tier)

        # Log panel
        self.log_panel = QTextEdit()
        self.log_panel.setLineWrapMode(self.log_panel.LineWrapMode.NoWrap)
        self.log_panel.setReadOnly(True)
        self.log_panel_scroll_area = QScrollArea()
        self.log_panel_scroll_area.setWidgetResizable(True)
        self.log_panel_scroll_area.setViewportMargins(0, 0, 0, 0)
        self.log_panel_scroll_area.setWidget(self.log_panel)

        # Add to layout
        self.grid_layout.addWidget(self.clear_video_button, 0, 0)
        self.grid_layout.addWidget(self.clear_image_button, 1, 0)
        self.grid_layout.addWidget(self.clear_gif_button, 2, 0)
        self.grid_layout.addWidget(self.clear_web_button, 3, 0)
        self.grid_layout.addWidget(self.clear_sound_button, 4, 0)
        self.grid_layout.addWidget(self.clear_text_button, 5, 0)
        self.grid_layout.addWidget(self.clear_redirect_button, 6, 0)
        self.grid_layout.addWidget(self.hide_all_button, 7, 0)
        self.grid_layout.addWidget(self.show_all_button, 8, 0)
        self.grid_layout.addWidget(self.mute_all_button, 9, 0)
        self.grid_layout.addWidget(self.lock_all_button, 10, 0)
        self.grid_layout.addWidget(self.chroma_key_button, 11, 0)
        self.grid_layout.addWidget(self.reset_positions_button, 12, 0)
        self.grid_layout.addWidget(self.low_power_button, 13, 0)
        self.grid_layout.addWidget(self.quality_label, 14, 0)
        self.grid_layout.addWidget(self.quality_combobox, 15, 0)
        self.grid_layout.addWidget(self.clear_all_button, 16, 0)
        self.grid_layout.addWidget(self.log_panel_scroll_area, 0, 1, 17, 1)  # rowSpan covers every button
        self.setLayout(self.grid_layout)

        # Redirect
        if redirect_output:
            self.redirect_timer = QTimer(self)
            self.redirect_timer.setInterval(10)
            self.redirect_timer.timeout.connect(self.redirect)
            self.redirect_timer.start()
            redirect_manager_instance.set_redirect()

    def _create_button(self, label_key: str, callback) -> QPushButton:
        """建立按鈕並綁定事件 / Create button and bind callback"""
        button = QPushButton(language_wrapper.language_word_dict.get(label_key))
        button.clicked.connect(callback)
        return button

    def _clear_widget_list(self, widget_list: list, name: str) -> None:
        front_engine_logger.info(f"[ControlCenterUI] clear_{name}")
        widget_list.clear()

    def clear_video(self) -> None:
        self._clear_widget_list(self.video_setting_ui.video_widget_list, "video")

    def clear_image(self) -> None:
        self._clear_widget_list(self.image_setting_ui.image_widget_list, "image")

    def clear_gif(self) -> None:
        self._clear_widget_list(self.gif_setting_ui.gif_widget_list, "gif")

    def clear_web(self) -> None:
        self._clear_widget_list(self.web_setting_ui.web_widget_list, "web")

    def clear_sound(self) -> None:
        self._clear_widget_list(self.sound_player_setting_ui.sound_widget_list, "sound")

    def clear_text(self) -> None:
        self._clear_widget_list(self.text_setting_ui.text_widget_list, "text")

    def clear_redirect(self) -> None:
        front_engine_logger.info("ControlCenterUI clear_redirect")
        self.log_panel.clear()

    def clear_scene(self) -> None:
        front_engine_logger.info("ControlCenterUI clear_scene")
        self.scene_setting_ui.close_scene()

    def clear_all(self) -> None:
        front_engine_logger.info("ControlCenterUI clear_all")
        self.video_setting_ui.video_widget_list.clear()
        self.image_setting_ui.image_widget_list.clear()
        self.web_setting_ui.web_widget_list.clear()
        self.gif_setting_ui.gif_widget_list.clear()
        self.sound_player_setting_ui.sound_widget_list.clear()
        self.text_setting_ui.text_widget_list.clear()
        self.particle_setting_ui.particle_list.clear()
        if self.pet_setting_ui is not None:
            self.pet_setting_ui.pet_list.clear()
        self.scene_setting_ui.close_scene()

    def register_overlay_source(self, provider) -> None:
        """
        讓控制中心也管得到其他分頁開的覆蓋層。provider 是一個回傳 widget 清單
        的函式（每次都重新問，才拿得到當下還活著的那些）。
        Let a page hand its overlays to the control center. The provider returns
        the widget list and is asked again every time, so it always reflects
        what is actually on screen right now.
        """
        self._extra_overlay_sources.append(provider)

    def _all_overlay_widget_lists(self) -> list:
        """回傳所有覆蓋層 widget 清單 / All overlay widget lists."""
        lists = [
            self.video_setting_ui.video_widget_list,
            self.image_setting_ui.image_widget_list,
            self.web_setting_ui.web_widget_list,
            self.gif_setting_ui.gif_widget_list,
            self.sound_player_setting_ui.sound_widget_list,
            self.text_setting_ui.text_widget_list,
            self.particle_setting_ui.particle_list,
        ]
        if self.pet_setting_ui is not None:
            lists.append(self.pet_setting_ui.pet_list)
        for provider in self._extra_overlay_sources:
            try:
                widgets = provider()
            except Exception as error:  # pragma: no cover - defensive boundary
                front_engine_logger.warning(f"[ControlCenterUI] overlay source failed: {error!r}")
                continue
            if widgets:
                lists.append(list(widgets))
        return lists

    def _for_each_overlay(self, action) -> None:
        """
        對每個仍存活的覆蓋層 widget 執行 action(widget)。手動關閉的覆蓋層因
        WA_DeleteOnClose 已被銷毀，其 Python 參考仍留在清單中，呼叫時會
        丟出 RuntimeError，這裡逐一保護並清除，避免崩潰。
        Run `action(widget)` on every live overlay widget. A widget the user
        already closed is deleted (WA_DeleteOnClose) while its Python
        reference lingers in the list, so calls raise RuntimeError — each is
        guarded and the dead reference is pruned so one cannot crash the batch.
        """
        for widget_list in self._all_overlay_widget_lists():
            for widget in widget_list[:]:
                try:
                    action(widget)
                except RuntimeError:
                    # Underlying C++ object already deleted; drop it.
                    try:
                        widget_list.remove(widget)
                    except ValueError:
                        pass

    def hide_all(self) -> None:
        """暫時隱藏所有覆蓋層 / Temporarily hide every overlay."""
        front_engine_logger.info("ControlCenterUI hide_all")
        self._for_each_overlay(lambda widget: widget.hide())

    def show_all(self) -> None:
        """重新顯示所有覆蓋層 / Re-show every overlay."""
        front_engine_logger.info("ControlCenterUI show_all")
        self._for_each_overlay(lambda widget: widget.show())

    def set_mute_all(self, muted: bool) -> None:
        """靜音／取消靜音所有支援的覆蓋層 / Mute or unmute every overlay that supports it."""
        front_engine_logger.info(f"ControlCenterUI set_mute_all | muted={muted}")
        self._muted = bool(muted)

        def apply(widget) -> None:
            setter = getattr(widget, "set_muted", None)
            if setter is not None:
                setter(self._muted)

        self._for_each_overlay(apply)
        self.mute_all_button.setText(
            language_wrapper.language_word_dict.get(
                "control_center_unmute_all" if self._muted else "control_center_mute_all",
                "Unmute all" if self._muted else "Mute all",
            )
        )

    def toggle_mute_all(self) -> None:
        """切換全域靜音狀態 / Toggle the global mute state."""
        self.set_mute_all(not getattr(self, "_muted", False))

    # --- lock / chroma key / positions -----------------------------------
    CHROMA_KEY_COLOR = "#00ff00"

    def set_lock_all(self, locked: bool) -> None:
        """
        鎖定＝所有覆蓋層點擊穿透；解鎖＝可以用滑鼠把覆蓋層拖到想要的位置，
        放開時位置會被記住。寵物不受影響（它本來就要接收滑鼠）。
        Locked overlays are click-through; unlocked ones can be dragged into
        place and remember where they were dropped. The pet is left alone as it
        needs the mouse either way.
        """
        front_engine_logger.info(f"ControlCenterUI set_lock_all | locked={locked}")
        self._overlays_locked = bool(locked)
        self._for_each_overlay(lambda widget: set_overlay_locked(widget, self._overlays_locked))
        self.lock_all_button.setText(
            language_wrapper.language_word_dict.get(
                "control_center_unlock_all" if self._overlays_locked else "control_center_lock_all",
                "Unlock overlays" if self._overlays_locked else "Lock overlays",
            )
        )

    def toggle_lock_all(self) -> None:
        """切換覆蓋層鎖定狀態 / Toggle the overlay lock."""
        self.set_lock_all(not getattr(self, "_overlays_locked", True))

    def set_chroma_key(self, enabled: bool) -> None:
        """開關綠幕背景（給 OBS 之類的軟體去背用）。"""
        front_engine_logger.info(f"ControlCenterUI set_chroma_key | enabled={enabled}")
        self._chroma_key = bool(enabled)
        color = self.CHROMA_KEY_COLOR if self._chroma_key else None

        def apply(widget) -> None:
            setter = getattr(widget, "set_background_color", None)
            if setter is not None:
                setter(color)

        self._for_each_overlay(apply)
        self.chroma_key_button.setText(
            language_wrapper.language_word_dict.get(
                "control_center_chroma_key_off" if self._chroma_key else "control_center_chroma_key_on",
                "Chroma key off" if self._chroma_key else "Chroma key on",
            )
        )

    def toggle_chroma_key(self) -> None:
        """切換綠幕背景 / Toggle the chroma key background."""
        self.set_chroma_key(not getattr(self, "_chroma_key", False))

    def reset_overlay_positions(self) -> None:
        """忘掉記住的覆蓋層位置，之後開的覆蓋層回到各自的預設顯示方式。"""
        front_engine_logger.info("ControlCenterUI reset_overlay_positions")
        clear_overlay_geometry()

    def set_low_power(self, enabled: bool) -> None:
        """省電模式：讓支援的覆蓋層把更新頻率調慢。"""
        front_engine_logger.info(f"ControlCenterUI set_low_power | enabled={enabled}")
        self._low_power = bool(enabled)

        def apply(widget) -> None:
            setter = getattr(widget, "set_low_power", None)
            if setter is not None:
                setter(self._low_power)

        self._for_each_overlay(apply)
        self.low_power_button.setText(
            language_wrapper.language_word_dict.get(
                "control_center_low_power_off" if self._low_power else "control_center_low_power_on",
                "Low power off" if self._low_power else "Low power on",
            )
        )

    def toggle_low_power(self) -> None:
        """切換省電模式 / Toggle low-power mode."""
        self.set_low_power(not getattr(self, "_low_power", False))

    def current_quality_tier(self) -> str:
        """目前選到的畫質檔位。"""
        return normalize_tier(self.quality_combobox.currentData())

    def set_quality_tier(self, tier: str) -> None:
        """把畫質檔位套用到所有支援的覆蓋層。"""
        tier = normalize_tier(tier)
        front_engine_logger.info(f"ControlCenterUI set_quality_tier | tier={tier}")
        index = self.quality_combobox.findData(tier)
        if index >= 0 and index != self.quality_combobox.currentIndex():
            self.quality_combobox.setCurrentIndex(index)
            return  # currentIndexChanged 會再走一次 _apply_quality_tier

        def apply(widget) -> None:
            setter = getattr(widget, "set_quality_tier", None)
            if setter is not None:
                setter(tier)

        self._for_each_overlay(apply)

    def _apply_quality_tier(self) -> None:
        self.set_quality_tier(self.current_quality_tier())

    def _sample_overlay_opacity(self) -> float:
        """取一個現有覆蓋層的不透明度作為起始值 / Seed from an existing overlay's opacity."""
        for widget_list in self._all_overlay_widget_lists():
            for widget in widget_list:
                value = getattr(widget, "opacity", None)
                if isinstance(value, (int, float)) and 0.0 < value <= 1.0:
                    return float(value)
        return 0.2

    def step_opacity_all(self, delta: float) -> None:
        """
        以 delta 調整所有覆蓋層的不透明度（夾在 0.1~1.0），套用到支援
        set_ui_variable 的覆蓋層並重繪。
        Step every overlay's opacity by `delta` (clamped to 0.1..1.0) and apply
        it to overlays exposing set_ui_variable, repainting each.
        """
        if self._global_opacity is None:
            self._global_opacity = self._sample_overlay_opacity()
        self._global_opacity = round(min(1.0, max(0.1, self._global_opacity + delta)), 2)
        value = self._global_opacity
        front_engine_logger.info(f"ControlCenterUI step_opacity_all | value={value}")

        def apply(widget) -> None:
            setter = getattr(widget, "set_ui_variable", None)
            if setter is None:
                return
            setter(value)
            updater = getattr(widget, "update", None)
            if callable(updater):
                updater()

        self._for_each_overlay(apply)

    def redirect(self) -> None:
        if not redirect_manager_instance.std_out_queue.empty():
            output_message = redirect_manager_instance.std_out_queue.get_nowait()
            output_message = str(output_message).strip()
            if output_message:
                self.log_panel.append(output_message)
        self.log_panel.setTextColor(error_color)
        if not redirect_manager_instance.std_err_queue.empty():
            error_message = redirect_manager_instance.std_err_queue.get_nowait()
            error_message = str(error_message).strip()
            if error_message:
                self.log_panel.append(error_message)
        self.log_panel.setTextColor(output_color)
