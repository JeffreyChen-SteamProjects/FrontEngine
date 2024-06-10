import os
import sys
from pathlib import Path
from typing import Dict, Type

from PySide6.QtCore import QTimer, QCoreApplication
from PySide6.QtGui import QIcon, Qt
from PySide6.QtWidgets import QMainWindow, QApplication, QGridLayout, QTabWidget, QMenuBar, QWidget
from qt_material import apply_stylesheet

from frontengine.system_tray.extend_system_tray import ExtendSystemTray
from frontengine.ui.menu.help_menu import build_help_menu
from frontengine.ui.menu.how_to_menu import build_how_to_menu
from frontengine.ui.menu.language_menu import build_language_menu
from frontengine.ui.page.control_center.control_center_ui import ControlCenterUI
from frontengine.ui.page.gif.gif_setting_ui import GIFSettingUI
from frontengine.ui.page.image.image_setting_ui import ImageSettingUI
from frontengine.ui.page.particle.particle_setting_ui import ParticleSettingUI
from frontengine.ui.page.scene_setting.scene_setting_ui import SceneSettingUI
from frontengine.ui.page.sound_player.sound_player_setting_ui import SoundPlayerSettingUI
from frontengine.ui.page.text.text_setting_ui import TextSettingUI
from frontengine.ui.page.video.video_setting_ui import VideoSettingUI
from frontengine.ui.page.web.web_setting_ui import WEBSettingUI
from frontengine.user_setting.user_setting_file import write_user_setting, read_user_setting, user_setting_dict
from frontengine.utils.critical_exit.critical_exit import CriticalExit
from frontengine.utils.critical_exit.win32_vk import keyboard_keys_table
from frontengine.utils.multi_language.language_wrapper import language_wrapper

FrontEngine_EXTEND_TAB: Dict[str, Type[QWidget]] = {}


class FrontEngineMainUI(QMainWindow):

    def __init__(self, debug: bool = False, show_system_tray_ray: bool = True):
        super().__init__()
        # User setting
        self.id = "FrontEngine"
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
        if sys.platform in ["win32", "cygwin", "msys"]:
            from ctypes import windll
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(self.id)
        read_user_setting()
        # Language Support
        self.language_wrapper = language_wrapper
        self.language_wrapper.reset_language(user_setting_dict.get("language", "English"))
        # Init setting ui
        self.setWindowTitle("FrontEngine")
        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_widget = QTabWidget(self)
        self.setCentralWidget(self.tab_widget)
        self.video_setting_ui = VideoSettingUI()
        self.image_setting_ui = ImageSettingUI()
        self.web_setting_ui = WEBSettingUI()
        self.gif_setting_ui = GIFSettingUI()
        self.sound_player_setting_ui = SoundPlayerSettingUI()
        self.text_setting_ui = TextSettingUI()
        self.scene_setting_ui = SceneSettingUI()
        self.particle_setting_ui = ParticleSettingUI()
        self.control_center_ui = ControlCenterUI(
            self.video_setting_ui,
            self.image_setting_ui,
            self.web_setting_ui,
            self.gif_setting_ui,
            self.sound_player_setting_ui,
            self.text_setting_ui,
            self.scene_setting_ui,
            self.particle_setting_ui
        )
        # Style menu bar
        self.menu_bar = QMenuBar()
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
            self.particle_setting_ui,
            language_wrapper.language_word_dict.get("tab_particle_text")
        )
        self.tab_widget.addTab(
            self.control_center_ui,
            language_wrapper.language_word_dict.get("tab_control_center_text")
        )
        for widget_name, widget in FrontEngine_EXTEND_TAB.items():
            self.tab_widget.addTab(widget(), widget_name)
        build_language_menu(self)
        build_help_menu(self)
        build_how_to_menu(self)
        # Set critical exit
        self.critical_ext = CriticalExit()
        self.critical_ext.set_critical_key(keyboard_keys_table.get("f12"))
        self.critical_ext.init_critical_exit()
        # Set Icon
        self.icon_path = Path(os.getcwd() + "/je_driver_icon.ico")
        self.icon = QIcon(str(self.icon_path))
        self.show_system_tray_ray = show_system_tray_ray
        if self.icon.isNull() is False:
            self.setWindowIcon(self.icon)
            if ExtendSystemTray.isSystemTrayAvailable() and self.show_system_tray_ray:
                self.system_tray = ExtendSystemTray(main_window=self)
                self.system_tray.setIcon(self.icon)
                self.system_tray.show()
                self.system_tray.setToolTip("FrontEngine")
        if debug:
            self.debug_timer = QTimer()
            self.debug_timer.setInterval(10000)
            self.debug_timer.timeout.connect(self.debug_close)
            self.debug_timer.start()

    def startup_setting(self) -> None:
        apply_stylesheet(self, theme=user_setting_dict.get("theme"))
        self.showMaximized()

    def set_style(self) -> None:
        user_setting_dict.update({"theme": self.sender().text()})

    def closeEvent(self, event) -> None:
        if ExtendSystemTray.isSystemTrayAvailable() and self.show_system_tray_ray:
            if self.system_tray.isVisible():
                self.hide()
                event.ignore()
        else:
            super().closeEvent(event)

    def close(self):
        write_user_setting()
        self.video_setting_ui.video_widget_list.clear()
        self.image_setting_ui.image_widget_list.clear()
        self.web_setting_ui.web_widget_list.clear()
        self.gif_setting_ui.gif_widget_list.clear()
        self.sound_player_setting_ui.sound_widget_list.clear()
        self.text_setting_ui.text_widget_list.clear()
        super().close()
        QCoreApplication.exit(0)

    @classmethod
    def debug_close(cls):
        sys.exit(0)


def start_front_engine(debug: bool = False) -> None:
    main_app = QApplication(sys.argv)
    window = FrontEngineMainUI(debug=debug)
    try:
        window.startup_setting()
    except Exception as error:
        print(repr(error))
    sys.exit(main_app.exec())
