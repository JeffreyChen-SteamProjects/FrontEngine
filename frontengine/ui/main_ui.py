import os
import sys
from pathlib import Path
from typing import Dict, Optional, Type

from PySide6.QtCore import QByteArray, QTimer, QCoreApplication
from PySide6.QtGui import QIcon, Qt
from PySide6.QtWidgets import QMainWindow, QApplication, QGridLayout, QTabWidget, QMenuBar, QWidget
from qt_material import apply_stylesheet

from frontengine.show.toast.toast_widget import show_toast
from frontengine.system_tray.extend_system_tray import ExtendSystemTray
from frontengine.ui.menu.help_menu import build_help_menu
from frontengine.ui.menu.how_to_menu import build_how_to_menu
from frontengine.ui.menu.language_menu import build_language_menu
from frontengine.ui.menu.preset_menu import (
    apply_named_preset, apply_startup_preset, build_preset_menu, restore_last_session,
    save_last_session,
)
from frontengine.ui.menu.settings_menu import build_settings_menu
from frontengine.ui.page.control_center.control_center_ui import ControlCenterUI
from frontengine.ui.page.focus.focus_setting_ui import FocusSettingUI
from frontengine.ui.page.gif.gif_setting_ui import GIFSettingUI
from frontengine.ui.page.image.image_setting_ui import ImageSettingUI
from frontengine.ui.page.particle.particle_setting_ui import ParticleSettingUI
from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
from frontengine.ui.page.scene_setting.scene_setting_ui import SceneSettingUI
from frontengine.ui.page.presentation.presentation_setting_ui import PresentationSettingUI
from frontengine.ui.page.screen_care.screen_care_setting_ui import ScreenCareSettingUI
from frontengine.ui.page.sound_player.sound_player_setting_ui import SoundPlayerSettingUI
from frontengine.ui.page.text.text_setting_ui import TextSettingUI
from frontengine.ui.page.video.video_setting_ui import VideoSettingUI
from frontengine.ui.page.wallpaper.wallpaper_setting_ui import WallpaperSettingUI
from frontengine.ui.page.web.web_setting_ui import WEBSettingUI
from frontengine.user_setting.user_setting_file import (
    get_hotkey_bindings,
    read_user_setting,
    user_setting_dict,
    write_user_setting,
)
from frontengine.utils.critical_exit.critical_exit import CriticalExit
from frontengine.utils.critical_exit.win32_vk import keyboard_keys_table
from frontengine.utils.hotkey.hotkey_service import HotkeyService
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.plugins.plugin_loader import load_plugins
from frontengine.utils.preset_schedule.preset_schedule_service import PresetScheduleService
from frontengine.ui.dialog.smart_pause_dialog import current_rules
from frontengine.utils.app_profile.app_profile_service import AppProfileService
from frontengine.utils.reminder.reminder_service import ReminderService
from frontengine.utils.smart_pause.smart_pause_service import SmartPauseService
from frontengine.utils.theme_schedule.theme_schedule_service import ThemeScheduleService

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
        if sys.platform == "win32":
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
        self.pet_setting_ui = PetSettingUI()
        self.screen_care_setting_ui = ScreenCareSettingUI()
        self.presentation_setting_ui = PresentationSettingUI()
        self.wallpaper_setting_ui = WallpaperSettingUI()
        self.focus_setting_ui = FocusSettingUI()

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
            redirect_output,
            pet_setting_ui=self.pet_setting_ui,
        )
        self._register_extra_overlays()

        # Menu Bar
        self.menu_bar = QMenuBar()
        self.setMenuBar(self.menu_bar)

        # 使用者明確開啟時才載入外掛（外掛與本程式同權限，無法沙箱化）
        # Plugins load only when explicitly enabled; they run with our privileges.
        loaded_plugins = load_plugins(
            FrontEngine_EXTEND_TAB, enabled=bool(user_setting_dict.get("load_plugins")))
        if loaded_plugins:
            front_engine_logger.info(f"[FrontEngineMainUI] plugin tabs: {loaded_plugins}")

        # 加入各 Tab
        # Add tabs
        self._add_tabs()

        # 建立選單
        # Build menus
        build_language_menu(self)
        build_help_menu(self)
        build_how_to_menu(self)
        build_preset_menu(self)
        build_settings_menu(self)

        # 致命退出設定
        # Critical exit setting
        self.critical_ext = CriticalExit()
        self.critical_ext.set_critical_key(keyboard_keys_table.get("f12"))
        self.critical_ext.init_critical_exit()

        # 全域快速鍵 / Global hotkeys
        # 快速鍵在 pynput 的背景執行緒觸發，明確使用 QueuedConnection 確保
        # 對應動作在 UI 主執行緒執行，避免跨執行緒操作 Qt widget 造成崩潰。
        # The hotkey fires on pynput's background thread; use an explicit
        # QueuedConnection so the action runs on the GUI thread rather than
        # mutating Qt widgets off-thread.
        self.hotkey_service = HotkeyService(get_hotkey_bindings())
        self.hotkey_service.hotkey_triggered.connect(
            self._handle_hotkey, Qt.ConnectionType.QueuedConnection
        )
        self.hotkey_service.start()

        # 設定 Icon 與系統托盤
        # Set icon and system tray
        self._setup_icon(show_system_tray_ray)

        # 智慧暫停：全螢幕程式、電池供電或指定程式取得焦點時暫時收起覆蓋層
        # Smart pause: stand the overlays down for a fullscreen app, battery
        # power, or one of the user's own apps taking focus.
        self._smart_pause_hid = False
        self.smart_pause_service = None
        if user_setting_dict.get("smart_pause", True):
            self.smart_pause_service = SmartPauseService(rules_provider=current_rules)
            self.smart_pause_service.pause_changed.connect(self._on_smart_pause_changed)
            self.smart_pause_service.start()

        # 依前景程式自動套用預設集 / Apply a preset when a configured app takes focus
        self.app_profile_service = AppProfileService(
            config_provider=lambda: user_setting_dict.get("app_profiles", {})
        )
        self.app_profile_service.profile_due.connect(
            lambda name: apply_named_preset(self, name)
        )
        self.app_profile_service.start()

        # 自訂提醒（喝水、久坐、每日鬧鐘），到期時以提示卡顯示
        # Custom reminders - water, posture, a daily alarm - shown as a toast.
        self.reminder_service = ReminderService(
            config_provider=lambda: user_setting_dict.get("reminders", [])
        )
        self.reminder_service.reminder_due.connect(self._show_reminder)
        self.reminder_service.start()
        # 最近一張提示卡；它會自己關掉，這裡留著只是為了測試與除錯
        # The most recent toast. It closes itself; this reference is for tests and debugging.
        self._last_toast = None

        # 依時間自動切換日/夜主題（始終運行，尊重 enabled 旗標）
        # Scheduled day/night theme (always running; respects the enabled flag)
        self.theme_schedule_service = ThemeScheduleService(
            config_provider=lambda: user_setting_dict.get("theme_schedule", {})
        )
        self.theme_schedule_service.theme_changed.connect(self._apply_theme)
        self.theme_schedule_service.start()

        # 每天在指定時間自動套用預設集 / Scheduled daily preset apply
        self.preset_schedule_service = PresetScheduleService(
            config_provider=lambda: user_setting_dict.get("preset_schedule", {})
        )
        self.preset_schedule_service.preset_due.connect(
            lambda name: apply_named_preset(self, name)
        )
        self.preset_schedule_service.start()

        # 還原上次工作階段（若有開啟），再套用啟動預設集
        # Restore the last session when enabled, then apply the startup preset.
        if user_setting_dict.get("restore_last_session"):
            restore_last_session(self)
        apply_startup_preset(self)

        # Debug 模式下自動關閉
        # Auto close in debug mode
        if debug:
            self.debug_timer = QTimer()
            self.debug_timer.setInterval(10000)
            self.debug_timer.timeout.connect(self.debug_close)
            self.debug_timer.start()

    def _register_extra_overlays(self) -> None:
        """
        把較新的分頁（護眼、簡報、桌布、專注）開的覆蓋層也交給控制中心管理，
        「全部隱藏／鎖定／畫質檔位」這些整批操作才不會漏掉它們。
        Hand the newer pages' overlays - screen care, presenting, wallpaper,
        focus - to the control center, so the batch actions (hide all, lock,
        quality tier) reach them too.
        """
        sources = (
            (self.screen_care_setting_ui, ("filter_widget_list", "ruler_widget_list",
                                           "break_overlay_list")),
            (self.presentation_setting_ui, ("annotation_widget_list", "cursor_widget_list",
                                            "keystroke_widget_list", "magnifier_widget_list")),
            (self.focus_setting_ui, ("dim_widget_list", "mask_widget_list")),
        )
        for page, attributes in sources:
            for attribute in attributes:
                self.control_center_ui.register_overlay_source(
                    lambda page=page, attribute=attribute: getattr(page, attribute, []))
        # 桌布是以螢幕編號為鍵的 dict，取它的值
        # The wallpaper page keys its widgets by monitor, so hand over the values.
        self.control_center_ui.register_overlay_source(
            lambda: list(self.wallpaper_setting_ui.wallpaper_widgets.values()))

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
            (self.pet_setting_ui, "tab_pet_text"),
            (self.screen_care_setting_ui, "tab_screen_care_text"),
            (self.presentation_setting_ui, "tab_presentation_text"),
            (self.wallpaper_setting_ui, "tab_wallpaper_text"),
            (self.focus_setting_ui, "tab_focus_text"),
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
        self.icon_path = Path(os.getcwd()) / "frontengine.ico"
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
        """啟動時套用樣式並還原視窗大小/位置（無記錄時最大化） / Apply stylesheet
        and restore the saved window geometry (maximize when none is stored)."""
        apply_stylesheet(self, theme=user_setting_dict.get("theme"))
        if not self._restore_window_geometry():
            self.showMaximized()

    def _restore_window_geometry(self) -> bool:
        """
        還原上次的視窗大小/位置。無記錄、格式錯誤或還原失敗時回傳 False，
        讓呼叫端退回最大化。
        Restore the previous window geometry. Returns False on missing /
        malformed / failed data so the caller can fall back to maximizing.
        """
        stored = user_setting_dict.get("window_geometry")
        if not isinstance(stored, str) or not stored:
            return False
        try:
            if not self.restoreGeometry(QByteArray.fromBase64(stored.encode("ascii"))):
                return False
        except Exception as error:
            front_engine_logger.warning(f"[FrontEngineMainUI] restore geometry failed: {error!r}")
            return False
        if user_setting_dict.get("window_maximized"):
            self.showMaximized()
        else:
            self.show()
        return True

    def _save_window_geometry(self) -> None:
        """將目前視窗大小/位置寫入設定 / Persist the current window geometry."""
        try:
            encoded = bytes(self.saveGeometry().toBase64().data()).decode("ascii")
            user_setting_dict["window_geometry"] = encoded
            user_setting_dict["window_maximized"] = self.isMaximized()
        except Exception as error:
            front_engine_logger.warning(f"[FrontEngineMainUI] save geometry failed: {error!r}")

    def set_style(self) -> None:
        """更新使用者選擇的主題 / Update user-selected theme"""
        user_setting_dict.update({"theme": self.sender().text()})

    def _apply_theme(self, theme: str) -> None:
        """套用主題並記住 / Apply a theme and remember it."""
        front_engine_logger.info(f"[FrontEngineMainUI] _apply_theme | theme={theme}")
        try:
            apply_stylesheet(self, theme=theme)
            user_setting_dict["theme"] = theme
        except Exception as error:
            front_engine_logger.warning(f"[FrontEngineMainUI] apply theme failed: {error!r}")

    def closeEvent(self, event) -> None:
        """關閉事件：若系統托盤可用則隱藏視窗 / Close event: hide window if system tray is available"""
        if ExtendSystemTray.isSystemTrayAvailable() and self.show_system_tray_ray:
            if self.system_tray.isVisible():
                self.hide()
                event.ignore()
        else:
            super().closeEvent(event)

    def reload_hotkeys(self) -> None:
        """
        以最新設定重建全域快速鍵服務（設定對話框存檔後呼叫）。
        Rebuild the global hotkey service from the latest settings (called
        after the settings dialog saves).
        """
        front_engine_logger.info("[FrontEngineMainUI] reload_hotkeys")
        if getattr(self, "hotkey_service", None) is not None:
            self.hotkey_service.stop()
        self.hotkey_service = HotkeyService(get_hotkey_bindings())
        self.hotkey_service.hotkey_triggered.connect(
            self._handle_hotkey, Qt.ConnectionType.QueuedConnection
        )
        self.hotkey_service.start()

    def _handle_hotkey(self, action: str) -> None:
        """
        分派全域快速鍵到對應動作。
        Dispatch global hotkey to the matching action on the UI thread.
        """
        if action == "close_all":
            self.control_center_ui.clear_all()
        elif action == "hide_all":
            self.control_center_ui.hide_all()
        elif action == "show_all":
            self.control_center_ui.show_all()
        elif action == "mute_all":
            self.control_center_ui.toggle_mute_all()
        elif action == "opacity_up":
            self.control_center_ui.step_opacity_all(0.1)
        elif action == "opacity_down":
            self.control_center_ui.step_opacity_all(-0.1)
        elif action == "dashboard_next":
            self.web_setting_ui.show_next_dashboard_page()
        elif action == "toggle_lock":
            self.control_center_ui.toggle_lock_all()

    def _on_smart_pause_changed(self, paused: bool, reason: str) -> None:
        """
        智慧暫停回呼：規則成立時隱藏覆蓋層，規則解除時還原（僅還原本服務
        自己隱藏的部分，避免覆蓋使用者手動操作）。
        Smart-pause callback: hide the overlays while a rule holds and restore
        them when it lifts — only restoring what this service hid.
        """
        front_engine_logger.info(f"[MainUI] smart pause | paused={paused}, reason={reason or '-'}")
        if paused:
            self.control_center_ui.hide_all()
            self._smart_pause_hid = True
        elif self._smart_pause_hid:
            self.control_center_ui.show_all()
            self._smart_pause_hid = False

    def _show_reminder(self, label: str) -> None:
        """提醒到期：在畫面上方顯示一張會自己消失的提示卡。"""
        front_engine_logger.info(f"[MainUI] reminder | {label}")
        self._last_toast = show_toast(label)

    def refresh_rule_services(self) -> None:
        """
        設定對話框按下確定後呼叫：規則與對照表都是每次輪詢重讀，所以只要把
        提醒的計時歸零，其餘服務下一輪就會自己拿到新設定。
        Called after a rule dialog is accepted. Rules and profiles are re-read on
        every poll, so only the reminder timers need resetting here.
        """
        if getattr(self, "reminder_service", None) is not None:
            self.reminder_service.tracker.reset()

    def close(self) -> None:
        """關閉程式並清理資源 / Close application and clear resources"""
        if user_setting_dict.get("restore_last_session"):
            save_last_session(self)
        if getattr(self, "preset_schedule_service", None) is not None:
            self.preset_schedule_service.stop()
        if getattr(self, "theme_schedule_service", None) is not None:
            self.theme_schedule_service.stop()
        if getattr(self, "reminder_service", None) is not None:
            self.reminder_service.stop()
        if getattr(self, "app_profile_service", None) is not None:
            self.app_profile_service.stop()
        if getattr(self, "smart_pause_service", None) is not None:
            self.smart_pause_service.stop()
        if getattr(self, "hotkey_service", None) is not None:
            self.hotkey_service.stop()
        self._save_window_geometry()
        write_user_setting()
        self.video_setting_ui.video_widget_list.clear()
        self.image_setting_ui.image_widget_list.clear()
        self.web_setting_ui.web_widget_list.clear()
        self.gif_setting_ui.gif_widget_list.clear()
        self.sound_player_setting_ui.sound_widget_list.clear()
        self.text_setting_ui.text_widget_list.clear()
        self.particle_setting_ui.particle_list.clear()
        self.pet_setting_ui.pet_list.clear()
        self.scene_setting_ui.close_scene()
        super().close()
        if self.main_app:
            self.main_app.exit(0)

    @classmethod
    def debug_close(cls) -> None:
        """Debug 模式下強制退出 / Force exit in debug mode"""
        sys.exit(0)


def start_front_engine(debug: bool = False, preset: Optional[str] = None) -> None:
    """
    啟動 FrontEngine 主程式
    Start FrontEngine main application

    :param debug: 是否啟用 Debug 模式 (Enable debug mode)
    :param preset: 啟動時要套用的預設集名稱，覆蓋設定中的啟動預設集
        (Preset name to apply on launch; overrides the configured startup preset)
    """
    main_app = QApplication(sys.argv)
    window = FrontEngineMainUI(main_app=main_app, debug=debug)
    if preset:
        apply_named_preset(window, preset)
    try:
        window.startup_setting()
    except Exception as error:
        print(repr(error))
    sys.exit(main_app.exec())


def main() -> None:
    """
    命令列進入點，支援 --preset 與 --debug。
    Command-line entry point supporting --preset and --debug.
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="frontengine", description="FrontEngine desktop overlay"
    )
    parser.add_argument(
        "--preset", default=None, help="Preset name to auto-apply on launch"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug auto-close timer"
    )
    # Ignore unknown args so Qt's own flags don't break parsing.
    args, _unknown = parser.parse_known_args()
    start_front_engine(debug=args.debug, preset=args.preset)