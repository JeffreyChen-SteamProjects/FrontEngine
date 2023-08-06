import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QMainWindow, QApplication, QGridLayout, QTabWidget, QSystemTrayIcon, QMenuBar
from qt_material import apply_stylesheet, QtStyleTools

from frontengine.ui.main.language_menu import build_language_menu
from frontengine.ui.setting.chat_scene.chat_scene_setting import ChatSceneUI
from frontengine.ui.setting.control_center.control_center_ui import ControlCenterUI
from frontengine.ui.setting.gif.gif_setting_ui import GIFSettingUI
from frontengine.ui.setting.image.image_setting_ui import ImageSettingUI
from frontengine.ui.setting.scene_setting.scene_setting_ui import SceneSettingUI
from frontengine.ui.setting.sound_player.sound_player_setting_ui import SoundPlayerSettingUI
from frontengine.ui.setting.text.text_setting_ui import TextSettingUI
from frontengine.ui.setting.video.video_setting_ui import VideoSettingUI
from frontengine.ui.setting.web.web_setting_ui import WEBSettingUI
from frontengine.user_setting.user_setting_file import write_user_setting, read_user_setting, user_setting_dict
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class FrontEngineMainUI(QMainWindow, QtStyleTools):

    def __init__(self, debug: bool = False):
        super().__init__()
        # User setting
        self.id = "FrontEngine"
        if sys.platform in ["win32", "cygwin", "msys"]:
            from ctypes import windll
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(self.id)
        read_user_setting()
        # Language Support
        self.language_wrapper = language_wrapper
        self.language_wrapper.reset_language(user_setting_dict.get("language", "English"))
        # Init setting ui
        self.setWindowTitle("FrontEngine")
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_widget = QTabWidget(self)
        self.video_setting_ui = VideoSettingUI()
        self.image_setting_ui = ImageSettingUI()
        self.web_setting_ui = WEBSettingUI()
        self.gif_setting_ui = GIFSettingUI()
        self.sound_player_setting_ui = SoundPlayerSettingUI()
        self.text_setting_ui = TextSettingUI()
        self.scene_setting_ui = SceneSettingUI()
        self.chat_scene_ui = ChatSceneUI()
        self.control_center_ui = ControlCenterUI(
            self.video_setting_ui,
            self.image_setting_ui,
            self.web_setting_ui,
            self.gif_setting_ui,
            self.sound_player_setting_ui,
            self.text_setting_ui,
            self.scene_setting_ui,
            self.chat_scene_ui
        )
        # Style menu bar
        self.menu_bar = QMenuBar()
        build_language_menu(self)
        self.add_style_menu()
        self.setMenuBar(self.menu_bar)
        self.tab_widget.addTab(
            self.video_setting_ui, language_wrapper.language_word_dict.get("tab_video_text"))
        self.tab_widget.addTab(
            self.image_setting_ui, language_wrapper.language_word_dict.get("tab_image_text"))
        self.tab_widget.addTab(
            self.web_setting_ui, language_wrapper.language_word_dict.get("tab_web_text"))
        self.tab_widget.addTab(
            self.gif_setting_ui,
            language_wrapper.language_word_dict.get("tab_gif_text")
        )
        self.tab_widget.addTab(
            self.sound_player_setting_ui,
            language_wrapper.language_word_dict.get("tab_sound_text")
        )
        self.tab_widget.addTab(
            self.text_setting_ui,
            language_wrapper.language_word_dict.get("tab_text_text")
        )
        self.tab_widget.addTab(
            self.scene_setting_ui,
            language_wrapper.language_word_dict.get("tab_scene_text")
        )
        self.tab_widget.addTab(
            self.chat_scene_ui,
            language_wrapper.language_word_dict.get("chat_ui_text")
        )
        self.tab_widget.addTab(
            self.control_center_ui,
            language_wrapper.language_word_dict.get("tab_control_center_text")
        )
        self.setCentralWidget(self.tab_widget)
        self.icon_path = Path(os.getcwd() + "/je_driver_icon.ico")
        self.icon = QIcon(str(self.icon_path))
        if self.icon.isNull() is False:
            self.setWindowIcon(self.icon)
            self.system_icon = QSystemTrayIcon()
            self.system_icon.setIcon(self.icon)
        if debug:
            self.debug_timer = QTimer()
            self.debug_timer.setInterval(10000)
            self.debug_timer.timeout.connect(self.close)
            self.debug_timer.start()

    def startup_setting(self) -> None:
        pass

    def add_style_menu(self) -> None:
        self.menu_bar.style_menu = self.menu_bar.addMenu(
            language_wrapper.language_word_dict.get("menu_bar_ui_style")
        )
        for style in [
            'dark_amber.xml', 'dark_blue.xml', 'dark_cyan.xml', 'dark_lightgreen.xml', 'dark_pink.xml',
            'dark_purple.xml', 'dark_red.xml', 'dark_teal.xml', 'dark_yellow.xml', 'light_amber.xml',
            'light_blue.xml', 'light_cyan.xml', 'light_cyan_500.xml', 'light_lightgreen.xml',
            'light_pink.xml', 'light_purple.xml', 'light_red.xml', 'light_teal.xml', 'light_yellow.xml'
        ]:
            change_style_action = QAction(style, parent=self)
            change_style_action.triggered.connect(self.set_style)
            self.menu_bar.style_menu.addAction(change_style_action)

    def set_style(self) -> None:
        self.apply_stylesheet(self, self.sender().text())

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
        self.video_setting_ui.video_widget_list.clear()
        self.image_setting_ui.image_widget_list.clear()
        self.web_setting_ui.web_widget_list.clear()
        self.gif_setting_ui.gif_widget_list.clear()
        self.sound_player_setting_ui.sound_widget_list.clear()
        self.text_setting_ui.text_widget_list.clear()
        self.chat_scene_ui.close_scene()
        self.chat_scene_ui.close()
        write_user_setting()


def start_front_engine(debug: bool = False) -> None:
    new_editor = QApplication(sys.argv)
    window = FrontEngineMainUI(debug=debug)
    apply_stylesheet(new_editor, theme='dark_amber.xml')
    window.showMaximized()
    try:
        window.startup_setting()
    except Exception as error:
        print(repr(error))
    sys.exit(new_editor.exec())
