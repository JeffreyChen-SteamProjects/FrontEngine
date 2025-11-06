from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget

from frontengine.show.scene.scene import SceneManager
from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.ui.page.scene_setting.scene_page.gif import GIFSceneSettingUI
from frontengine.ui.page.scene_setting.scene_page.image import ImageSceneSettingUI
from frontengine.ui.page.scene_setting.scene_page.sound import SoundSceneSettingUI
from frontengine.ui.page.scene_setting.scene_page.text import TextSceneSettingUI
from frontengine.ui.page.scene_setting.scene_page.video import VideoSceneSettingUI
from frontengine.ui.page.scene_setting.scene_page.web import WebSceneSettingUI
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SceneSettingUI(QWidget):
    def __init__(self):
        front_engine_logger.info("[SceneSettingUI] Init")
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # scene
        self.scene = SceneManager()

        # Tab
        self.tab_widget = QTabWidget(self)
        self.scene_manager_ui = SceneManagerUI(self.scene)
        self.tab_widget.addTab(
            self.scene_manager_ui, language_wrapper.language_word_dict.get("scene_script")
        )

        tabs = [
            (GIFSceneSettingUI, "tab_gif_text"),
            (ImageSceneSettingUI, "tab_image_text"),
            (SoundSceneSettingUI, "tab_sound_text"),
            (TextSceneSettingUI, "tab_text_text"),
            (VideoSceneSettingUI, "tab_video_text"),
            (WebSceneSettingUI, "tab_web_text"),
        ]

        for ui_class, label_key in tabs:
            self.tab_widget.addTab(ui_class(self.scene_manager_ui), language_wrapper.language_word_dict.get(label_key))

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

    def close_scene(self) -> None:
        front_engine_logger.info("[SceneSettingUI] close_scene")
        self.scene.widget_list.clear()
        for view in self.scene.view_list:
            view.close()
            view.deleteLater()
        self.scene.view_list.clear()
