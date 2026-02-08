from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QGridLayout, QWidget, QPushButton, QTextEdit, QScrollArea

from frontengine.ui.color.global_color import error_color, output_color
from frontengine.ui.page.gif.gif_setting_ui import GIFSettingUI
from frontengine.ui.page.image.image_setting_ui import ImageSettingUI
from frontengine.ui.page.particle.particle_setting_ui import ParticleSettingUI
from frontengine.ui.page.scene_setting.scene_setting_ui import SceneSettingUI
from frontengine.ui.page.sound_player.sound_player_setting_ui import SoundPlayerSettingUI
from frontengine.ui.page.text.text_setting_ui import TextSettingUI
from frontengine.ui.page.video.video_setting_ui import VideoSettingUI
from frontengine.ui.page.web.web_setting_ui import WEBSettingUI
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
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
            redirect_output: bool = True
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
        self.clear_all_button = self._create_button("control_center_close_all", self.clear_all)

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
        self.grid_layout.addWidget(self.clear_all_button, 7, 0)
        self.grid_layout.addWidget(self.log_panel_scroll_area, 0, 1, 8, 1)  # 明確指定 rowSpan=8, colSpan=1
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
        self.scene_setting_ui.close_scene()

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
