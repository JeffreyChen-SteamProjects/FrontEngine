from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QTabWidget
from frontengine.ui.page.scene_setting.scene_page.gif import GIFSceneSettingUI

from frontengine.show.scene.scene import SceneManager
from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.ui.page.scene_setting.scene_page.image import ImageSceneSettingUI
from frontengine.ui.page.scene_setting.scene_page.sound import SoundSceneSettingUI
from frontengine.ui.page.scene_setting.scene_page.text import TextSceneSettingUI
from frontengine.ui.page.scene_setting.scene_page.video import VideoSceneSettingUI
from frontengine.ui.page.scene_setting.scene_page.web import WebSceneSettingUI
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SceneSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # scene
        self.scene = SceneManager()
        # Tab
        self.tab_widget = QTabWidget(self)
        self.scene_manager_ui = SceneManagerUI()
        self.tab_widget.addTab(
            self.scene_manager_ui, language_wrapper.language_word_dict.get("scene_script")
        )
        self.tab_widget.addTab(
            GIFSceneSettingUI(self.scene_manager_ui), language_wrapper.language_word_dict.get("tab_gif_text")
        )
        self.tab_widget.addTab(
            ImageSceneSettingUI(self.scene_manager_ui), language_wrapper.language_word_dict.get("tab_image_text")
        )
        self.tab_widget.addTab(
            SoundSceneSettingUI(self.scene_manager_ui), language_wrapper.language_word_dict.get("tab_sound_text")
        )
        self.tab_widget.addTab(
            TextSceneSettingUI(self.scene_manager_ui), language_wrapper.language_word_dict.get("tab_text_text")
        )
        self.tab_widget.addTab(
            VideoSceneSettingUI(self.scene_manager_ui), language_wrapper.language_word_dict.get("tab_video_text")
        )
        self.tab_widget.addTab(
            WebSceneSettingUI(self.scene_manager_ui), language_wrapper.language_word_dict.get("tab_web_text")
        )
        # Add to layout
        self.grid_layout.addWidget(self.tab_widget, 0, 0, -1, -1)
        self.setLayout(self.grid_layout)

    def close_scene(self) -> None:
        self.scene.widget_list.clear()
        if self.scene.graphic_view.isEnabled() and self.scene.graphic_view.isVisible():
            self.scene.graphic_view.close()
