import os
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QApplication, QGridLayout, QTabWidget, QSystemTrayIcon
from qt_material import apply_stylesheet

from frontengine.ui.setting.gif.gif_setting_ui import GIFSettingUI
from frontengine.ui.setting.image.image_setting_ui import ImageSettingUI
from frontengine.ui.setting.sound_player.sound_player_setting_ui import SoundPlayerSettingUI
from frontengine.ui.setting.text.text_setting_ui import TextSettingUI
from frontengine.ui.setting.video.video_setting_ui import VideoSettingUI
from frontengine.ui.setting.web.web_setting_ui import WEBSettingUI


class FrontEngineMainUI(QMainWindow):

    def __init__(self):
        super().__init__()
        # User setting
        self.id = "FrontEngine"
        if sys.platform in ["win32", "cygwin", "msys"]:
            from ctypes import windll
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(self.id)
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
        self.tab_widget.addTab(self.video_setting_ui, "Video")
        self.tab_widget.addTab(self.image_setting_ui, "Image")
        self.tab_widget.addTab(self.web_setting_ui, "WEB")
        self.tab_widget.addTab(self.gif_setting_ui, "GIF AND WEBP")
        self.tab_widget.addTab(self.sound_player_setting_ui, "Sound")
        self.tab_widget.addTab(self.text_setting_ui, "Text")
        self.setCentralWidget(self.tab_widget)
        self.icon_path = Path(os.getcwd() + "/je_driver_icon.ico")
        self.icon = QIcon(str(self.icon_path))
        if self.icon.isNull() is False:
            self.setWindowIcon(self.icon)
            self.system_icon = QSystemTrayIcon()
            self.system_icon.setIcon(self.icon)

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
        self.video_setting_ui.video_widget_list.clear()
        self.image_setting_ui.image_widget_list.clear()
        self.web_setting_ui.web_widget_list.clear()
        self.gif_setting_ui.gif_widget_list.clear()
        self.sound_player_setting_ui.sound_widget_list.clear()
        self.text_setting_ui.text_widget_list.clear()


def start_front_engine():
    new_editor = QApplication(sys.argv)
    window = FrontEngineMainUI()
    apply_stylesheet(new_editor, theme='dark_amber.xml')
    window.showMaximized()
    sys.exit(new_editor.exec())
