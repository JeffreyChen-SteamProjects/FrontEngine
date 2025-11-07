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

# 可擴充的外部 Tab 註冊表
# Registry for external tabs
FrontEngine_EXTEND_TAB: Dict[str, Type[QWidget]] = {}


class FrontEngineMainUI(QMainWindow):
    """
    FrontEngine 主視窗
    FrontEngine Main Window
    """

    def __init__(self,
                 main_app: QApplication = None,
                 debug: bool = False,
                 show_system_tray_ray: bool = True,
                 redirect_output: bool = True):
        super().__init__()

        # 基本設定
        # Basic settings
        self.id = "FrontEngine"
        self.main_app = main_app
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)

        # Windows 平台設定 AppUserModelID
        # Set AppUserModelID for Windows platform
        if sys.platform in ["win32", "cygwin", "msys"]:
            from ctypes import windll
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(self.id)

        # 讀取使用者設定
        # Load user settings
        read_user_setting()

        # 語言支援
        # Language support
        self.language_wrapper = language_wrapper
        self.language_wrapper.reset_language(user_setting_dict.get("language", "English"))

        # 初始化 UI
        # Initialize UI
        self.setWindowTitle("FrontEngine")
        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        # Tab Widget 作為主介面
        # Tab widget as main interface
        self.tab_widget = QTabWidget(self)
        self.setCentralWidget(self.tab_widget)

        # 各功能頁面初始化
        # Initialize each functional page
        self.video_setting_ui = VideoSettingUI()
        self.image_setting_ui = ImageSettingUI()
        self.web_setting_ui = WEBSettingUI()
        self.gif_setting_ui = GIFSettingUI()
        self.sound_player_setting_ui = SoundPlayerSettingUI()
        self.text_setting_ui = TextSettingUI()
        self.scene_setting_ui = SceneSettingUI()
        self.particle_setting_ui = ParticleSettingUI()

        # 控制中心
        # Control Center
        self.control_center_ui = ControlCenterUI(
            self.video_setting_ui,
            self.image_setting_ui,
            self.web_setting_ui,
            self.gif_setting_ui,
            self.sound_player_setting_ui,
            self.text_setting_ui,
            self.scene_setting_ui,
            self.particle_setting_ui,
            redirect_output
        )

        # Menu Bar
        self.menu_bar = QMenuBar()
        self.setMenuBar(self.menu_bar)

        # 加入各 Tab
        # Add tabs
        self._add_tabs()

        # 建立選單
        # Build menus
        build_language_menu(self)
        build_help_menu(self)
        build_how_to_menu(self)

        # 致命退出設定
        # Critical exit setting
        self.critical_ext = CriticalExit()
        self.critical_ext.set_critical_key(keyboard_keys_table.get("f12"))
        self.critical_ext.init_critical_exit()

        # 設定 Icon 與系統托盤
        # Set icon and system tray
        self._setup_icon(show_system_tray_ray)

        # Debug 模式下自動關閉
        # Auto close in debug mode
        if debug:
            self.debug_timer = QTimer()
            self.debug_timer.setInterval(10000)
            self.debug_timer.timeout.connect(self.debug_close)
            self.debug_timer.start()

    def _add_tabs(self) -> None:
        """加入所有內建與擴充的 Tab / Add all built-in and extended tabs"""
        tabs = [
            (self.video_setting_ui, "tab_video_text"),
            (self.image_setting_ui, "tab_image_text"),
            (self.web_setting_ui, "tab_web_text"),
            (self.gif_setting_ui, "tab_gif_text"),
            (self.sound_player_setting_ui, "tab_sound_text"),
            (self.text_setting_ui, "tab_text_text"),
            (self.scene_setting_ui, "tab_scene_text"),
            (self.particle_setting_ui, "tab_particle_text"),
            (self.control_center_ui, "tab_control_center_text"),
        ]

        for widget, lang_key in tabs:
            self.tab_widget.addTab(widget, language_wrapper.language_word_dict.get(lang_key))

        # 加入外部擴充 Tab
        # Add external extension tabs
        for widget_name, widget in FrontEngine_EXTEND_TAB.items():
            self.tab_widget.addTab(widget(), widget_name)

    def _setup_icon(self, show_system_tray_ray: bool) -> None:
        """設定視窗 Icon 與系統托盤 / Setup window icon and system tray"""
        self.icon_path = Path(os.getcwd()) / "je_driver_icon.ico"
        self.icon = QIcon(str(self.icon_path))
        self.show_system_tray_ray = show_system_tray_ray

        if not self.icon.isNull():
            self.setWindowIcon(self.icon)
            if ExtendSystemTray.isSystemTrayAvailable() and self.show_system_tray_ray:
                self.system_tray = ExtendSystemTray(main_window=self)
                self.system_tray.setIcon(self.icon)
                self.system_tray.show()
                self.system_tray.setToolTip("FrontEngine")

    def startup_setting(self) -> None:
        """啟動時套用樣式並最大化 / Apply stylesheet and maximize window on startup"""
        apply_stylesheet(self, theme=user_setting_dict.get("theme"))
        self.showMaximized()

    def set_style(self) -> None:
        """更新使用者選擇的主題 / Update user-selected theme"""
        user_setting_dict.update({"theme": self.sender().text()})

    def closeEvent(self, event) -> None:
        """關閉事件：若系統托盤可用則隱藏視窗 / Close event: hide window if system tray is available"""
        if ExtendSystemTray.isSystemTrayAvailable() and self.show_system_tray_ray:
            if self.system_tray.isVisible():
                self.hide()
                event.ignore()
        else:
            super().closeEvent(event)

    def close(self) -> None:
        """關閉程式並清理資源 / Close application and clear resources"""
        write_user_setting()
        self.video_setting_ui.video_widget_list.clear()
        self.image_setting_ui.image_widget_list.clear()
        self.web_setting_ui.web_widget_list.clear()
        self.gif_setting_ui.gif_widget_list.clear()
        self.sound_player_setting_ui.sound_widget_list.clear()
        self.text_setting_ui.text_widget_list.clear()
        super().close()
        if self.main_app:
            self.main_app.exit(0)

    @classmethod
    def debug_close(cls) -> None:
        """Debug 模式下強制退出 / Force exit in debug mode"""
        sys.exit(0)


def start_front_engine(debug: bool = False) -> None:
    """
    啟動 FrontEngine 主程式
    Start FrontEngine main application

    :param debug: 是否啟用 Debug 模式 (Enable debug mode)
    """
    main_app = QApplication(sys.argv)
    window = FrontEngineMainUI(main_app=main_app, debug=debug)
    try:
        window.startup_setting()
    except Exception as error:
        print(repr(error))
    sys.exit(main_app.exec())