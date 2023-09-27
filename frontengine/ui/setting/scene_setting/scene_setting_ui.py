from typing import Union

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QTabWidget

from frontengine.show.scene.scene import SceneManager
from frontengine.ui.setting.scene_setting.scene_tabs.Image import ImageSceneSettingUI
from frontengine.ui.setting.scene_setting.scene_tabs.gif import GIFSceneSettingUI
from frontengine.ui.setting.scene_setting.scene_tabs.scene_control import SceneControlSettingUI
from frontengine.ui.setting.scene_setting.scene_tabs.sound import SoundSceneSettingUI
from frontengine.ui.setting.scene_setting.scene_tabs.text import TextSceneSettingUI
from frontengine.ui.setting.scene_setting.scene_tabs.ui import UISceneSettingUI
from frontengine.ui.setting.scene_setting.scene_tabs.video import VideoSceneSettingUI
from frontengine.ui.setting.scene_setting.scene_tabs.web import WEBSceneSettingUI
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SceneSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # Init variable
        self.scene: Union[None, SceneManager] = None
        self.scene_control_setting = SceneControlSettingUI()
        # Tab widget
        self.tab_widget = QTabWidget(self)
        self.tab_widget.addTab(
            SceneControlSettingUI(), language_wrapper.language_word_dict.get("scene_control_panel"))
        self.tab_widget.addTab(
            ImageSceneSettingUI(), language_wrapper.language_word_dict.get("tab_image_text"))
        self.tab_widget.addTab(
            GIFSceneSettingUI(), language_wrapper.language_word_dict.get("tab_gif_text"))
        self.tab_widget.addTab(
            TextSceneSettingUI(), language_wrapper.language_word_dict.get("tab_text_text"))
        self.tab_widget.addTab(
            VideoSceneSettingUI(), language_wrapper.language_word_dict.get("tab_video_text"))
        self.tab_widget.addTab(
            WEBSceneSettingUI(), language_wrapper.language_word_dict.get("tab_web_text"))
        self.tab_widget.addTab(
            SoundSceneSettingUI(), language_wrapper.language_word_dict.get("tab_sound_text"))
        self.tab_widget.addTab(
            UISceneSettingUI(), language_wrapper.language_word_dict.get("tab_external_ui"))
        # Add to layout
        self.grid_layout.addWidget(self.tab_widget, 0, 0, -1, -1)
        self.setLayout(self.grid_layout)
