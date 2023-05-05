import sys

from PySide6.QtWidgets import QMainWindow, QApplication, QGridLayout, QTabWidget
from qt_material import apply_stylesheet

from frontengine.show.image.paint_image import ImageWidget
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
        self.audio_device = None
        self.screen_device = None
        self.play_volume = None
        self.play_rate = None
        self.opacity = None
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
        self.tab_widget.addTab(self.gif_setting_ui, "GIF")
        self.tab_widget.addTab(self.sound_player_setting_ui, "Sound")
        self.tab_widget.addTab(self.text_setting_ui, "Text")
        self.setCentralWidget(self.tab_widget)



def start_front_engine():
    new_editor = QApplication(sys.argv)
    window = FrontEngineMainUI()
    apply_stylesheet(new_editor, theme='dark_amber.xml')
    window.showMaximized()
    sys.exit(new_editor.exec())


start_front_engine()
