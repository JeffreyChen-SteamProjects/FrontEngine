import os
import sys
from os import getcwd
from pathlib import Path
from typing import Any, Dict, Optional, Type

from PySide6.QtCore import QByteArray, QTimer
from PySide6.QtGui import QIcon, Qt
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QGridLayout, QHBoxLayout, QStackedWidget, QStyle,
    QMenuBar, QWidget,
)
from qt_material import apply_stylesheet

from frontengine.ui.nav.sidebar import NavigationSidebar
from frontengine.ui.style.app_style import apply_app_style

from frontengine.show.shortcuts.shortcut_sheet import build_sheet
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
from frontengine.ui.page.tools.tools_setting_ui import ToolsSettingUI
from frontengine.ui.page.video.video_setting_ui import VideoSettingUI
from frontengine.ui.page.wallpaper.wallpaper_setting_ui import WallpaperSettingUI
from frontengine.ui.page.web.web_setting_ui import WEBSettingUI
from frontengine.ui.page.widgets.widgets_setting_ui import WidgetsSettingUI
from frontengine.user_setting.user_setting_file import (
    get_hotkey_bindings,
    is_stored,
    read_user_setting,
    user_setting_dict,
    write_user_setting,
)
from frontengine.utils.steam.steam_language import steam_language
from frontengine.utils.critical_exit.critical_exit import CriticalExit
from frontengine.utils.critical_exit.win32_vk import keyboard_keys_table
from frontengine.utils.hotkey.hotkey_service import HotkeyService
from frontengine.utils.keep_awake.keep_awake import KeepAwake
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator, translate
from frontengine.utils.plugins.plugin_loader import load_plugins
from frontengine.utils.preset_schedule.preset_schedule_service import PresetScheduleService
from frontengine.ui.dialog.remote_control_dialog import (
    MIDI_KEY, current_bindings, remote_enabled,
)
from frontengine.ui.dialog.screen_privacy_dialog import current_settings as current_privacy_settings
from frontengine.ui.dialog.signage_dialog import current_settings as current_signage_settings
from frontengine.utils.signage.signage_service import SignageService
from frontengine.utils.midi.midi_input import MidiInput, binding_key
from frontengine.utils.remote.remote_server import RemoteServer
from frontengine.ui.dialog.hotkey_settings_dialog import action_label as hotkey_action_label
from frontengine.ui.dialog.smart_pause_dialog import current_rules
from frontengine.utils.screen_privacy.share_watch import ShareWatchService
from frontengine.utils.screensaver.screensaver_service import ScreensaverService
from frontengine.utils.app_profile.app_profile_service import AppProfileService
from frontengine.utils.clipboard.clipboard_history import DEFAULT_LIMIT, ClipboardHistory
from frontengine.utils.clipboard.clipboard_watcher import ClipboardWatcher
from frontengine.utils.json.json_repository import JsonRepository
from frontengine.utils.usage_tracking.usage_service import UsageTrackingService
from frontengine.utils.usage_tracking.usage_tracker import USAGE_FILE, UsageTracker
from frontengine.utils.reminder.reminder_service import ReminderService
from frontengine.utils.smart_pause.smart_pause_service import SmartPauseService
from frontengine.utils.theme_schedule.theme_schedule_service import ThemeScheduleService

# 可擴充的外部 Tab 註冊表
# Registry for external tabs
FrontEngine_EXTEND_TAB: Dict[str, Type[QWidget]] = {}


def tray_can_restore_window(window: Any) -> bool:
    """
    系統匣能不能把主視窗叫回來。任何「把主視窗藏起來」的功能都得先問這件事，
    不然藏掉的就是唯一能把該功能關掉的畫面。
    Whether the tray can bring the main window back. Anything that hides the
    window has to ask first: otherwise what it hides is the only screen that
    can turn that same thing off.
    """
    tray = getattr(window, "system_tray", None)
    return bool(ExtendSystemTray.isSystemTrayAvailable()
                and getattr(window, "show_system_tray_ray", False)
                and tray is not None and tray.isVisible())


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
        self._shutdown_done = False
        # Qt 6 一律啟用高 DPI 縮放，AA_EnableHighDpiScaling 已無作用且被標為棄用
        # Qt 6 always scales for high DPI; AA_EnableHighDpiScaling is a deprecated
        # no-op there.

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
        self.language_wrapper.reset_language(self._startup_language())

        # 初始化 UI
        # Initialize UI
        self.setWindowTitle("FrontEngine")
        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        # 主介面：左側導覽 + 右側頁面堆疊
        # Main interface: navigation on the left, the page stack on the right
        self.sidebar = NavigationSidebar(self)
        self.page_stack = QStackedWidget(self)
        self.page_stack.setObjectName("pageBody")
        self.sidebar.page_requested.connect(self.page_stack.setCurrentIndex)

        central = QWidget(self)
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.sidebar)
        central_layout.addWidget(self.page_stack, 1)
        self.setCentralWidget(central)

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
        self.widgets_setting_ui = WidgetsSettingUI()
        self.tools_setting_ui = ToolsSettingUI()

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

        # 手機遙控與 MIDI：兩者都只呼叫既有的快速鍵動作，做不到別的事
        # The phone remote and MIDI both call the existing hotkey actions and
        # can do nothing beyond them.
        # 兩者的訊息都來自別的執行緒（HTTP 伺服器、winmm），所以明確用
        # QueuedConnection 接回 UI 執行緒——和全域快速鍵同樣的理由。
        # Both deliver from another thread (the HTTP server, winmm), so an
        # explicit QueuedConnection brings them back to the UI thread - the same
        # reason the global hotkeys use one.
        self.remote_server = RemoteServer()
        self.remote_server.action_requested.connect(
            self._handle_hotkey, Qt.ConnectionType.QueuedConnection)
        if remote_enabled():
            self.remote_server.start()
        self.midi_input = MidiInput()
        self.midi_input.message_received.connect(
            self._on_midi_message, Qt.ConnectionType.QueuedConnection)
        if user_setting_dict.get(MIDI_KEY):
            self.midi_input.start(user_setting_dict.get("midi_device") or 0)

        # 看板模式：依序輪播預設集，主視窗可以收起來
        # Signage mode: rotate presets, with the main window out of the way.
        self.signage_service = SignageService(config_provider=current_signage_settings)
        self.signage_service.preset_due.connect(lambda name: apply_named_preset(self, name))
        if current_signage_settings().get("enabled"):
            self.start_signage()

        # 分享畫面時把覆蓋層藏出擷取結果（自己仍看得到）
        # Hide the overlays from the capture while sharing; they stay on screen here.
        self.share_watch_service = ShareWatchService(config_provider=current_privacy_settings)
        self.share_watch_service.sharing_changed.connect(self._on_sharing_changed)
        self.share_watch_service.start()

        # 使用時間統計：預設關閉，只寫本機檔案，使用者可隨時清除
        # Usage tracking: off by default, local file only, clearable at any time.
        self.usage_tracker = UsageTracker(JsonRepository(Path(getcwd()) / USAGE_FILE))
        self.usage_service = UsageTrackingService(self.usage_tracker)
        if user_setting_dict.get("usage_tracking"):
            self.usage_service.start()

        # 剪貼簿歷史：預設關閉；未勾選保存時只留在記憶體
        # Clipboard history: off by default, memory only unless saving is on.
        self.clipboard_history = ClipboardHistory(
            limit=user_setting_dict.get("clipboard_limit", DEFAULT_LIMIT))
        if user_setting_dict.get("clipboard_persist"):
            self.clipboard_history.load(user_setting_dict.get("clipboard_entries"))
        self.clipboard_watcher = ClipboardWatcher(self.clipboard_history)
        if user_setting_dict.get("clipboard_history"):
            self.clipboard_watcher.start()

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

        # 保持喚醒：覆蓋層放著的時候別讓螢幕睡著
        # Keep awake: do not let the display sleep while an overlay is up
        self.keep_awake = KeepAwake()
        if user_setting_dict.get("keep_awake"):
            self.keep_awake.enable()

        # 閒置夠久就把選定的覆蓋層放上來 / Show the chosen overlay once idle
        self._screensaver_overlays: list = []
        self.screensaver_service = ScreensaverService(
            config_provider=lambda: user_setting_dict.get("screensaver", {})
        )
        self.screensaver_service.screensaver_started.connect(self._start_screensaver)
        self.screensaver_service.screensaver_stopped.connect(self._stop_screensaver)
        self.screensaver_service.start()

        # 還原上次工作階段（若有開啟），再套用啟動預設集
        # Restore the last session when enabled, then apply the startup preset.
        if user_setting_dict.get("restore_last_session"):
            restore_last_session(self)
        if user_setting_dict.get("sticky_notes_restore"):
            self.widgets_setting_ui.restore_saved_notes()
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
                                           "break_overlay_list", "color_vision_widget_list")),
            (self.presentation_setting_ui, ("annotation_widget_list", "cursor_widget_list",
                                            "keystroke_widget_list", "magnifier_widget_list",
                                            "whiteboard_widget_list")),
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
        self.control_center_ui.register_overlay_source(
            lambda: getattr(self.web_setting_ui, "dashboard_widgets", []))
        # 批次關閉之後，沒有覆蓋層在聽就把全域輸入監聽收掉
        # After a batch close nothing is listening, so drop the global input hook.
        self.control_center_ui.register_cleanup(
            self.presentation_setting_ui.release_input_watch)
        for attribute in ("spectrum_widget_list", "monitor_widget_list",
                          "now_playing_widget_list", "note_widget_list"):
            self.control_center_ui.register_overlay_source(
                lambda attribute=attribute: getattr(self.widgets_setting_ui, attribute, []))
        for attribute in ("measure_widget_list", "capture_widget_list", "camera_widget_list",
                          "pinned_widget_list"):
            self.control_center_ui.register_overlay_source(
                lambda attribute=attribute: getattr(self.tools_setting_ui, attribute, []))

    # 螢幕保護能顯示哪些分頁：來源名稱 -> (頁面屬性, 啟動方法, 覆蓋層清單屬性)
    # What the screensaver can show: source -> (page attribute, start method,
    # the page's overlay list).
    _SCREENSAVER_SOURCES = {
        "video": ("video_setting_ui", "start_play_video", "video_widget_list"),
        "image": ("image_setting_ui", "start_play_image", "image_widget_list"),
        "gif": ("gif_setting_ui", "start_play_gif", "gif_widget_list"),
        "particle": ("particle_setting_ui", "start_play_particle", "particle_list"),
        "web": ("web_setting_ui", "start_open_web_with_url", "web_widget_list"),
    }

    @staticmethod
    def _screensaver_ready(source: str, page: Any) -> bool:
        """
        這一頁現在按下開始會不會出東西。

        非問不可：每個分頁在沒選檔案時都會跳一個 modal 訊息框，而螢幕保護正好是
        在沒有人的時候啟動的——那個對話框會擋在畫面上直到有人回來按掉。
        Whether pressing start on this page would actually show something.

        This has to be asked: every page opens a modal message box when no file
        is chosen, and the screensaver fires precisely when nobody is there - the
        dialog would sit on screen until someone came back and dismissed it.
        """
        if source == "web":
            field = getattr(page, "web_url_input", None)
            return bool(field is not None and field.text().strip())
        return bool(getattr(page, "ready_to_play", False))

    def _start_screensaver(self, source: str) -> None:
        """閒置夠久了：把選定分頁的覆蓋層放上來，並記住是哪幾個。"""
        entry = self._SCREENSAVER_SOURCES.get(source)
        if entry is None:
            return
        attribute, start_method, list_name = entry
        page = getattr(self, attribute, None)
        overlays = getattr(page, list_name, None) if page is not None else None
        if page is None or overlays is None:
            return
        if not self._screensaver_ready(source, page):
            front_engine_logger.info(
                f"[FrontEngineMainUI] screensaver source '{source}' has nothing set up")
            return
        before = len(overlays)
        try:
            getattr(page, start_method)()
        except Exception as error:  # pragma: no cover - defensive boundary
            front_engine_logger.warning(f"[FrontEngineMainUI] screensaver start failed: {error!r}")
            return
        # 只記下這次新增的那幾個。人回來時關掉的就只有這些，使用者自己開著的
        # 覆蓋層不會跟著被收走。
        # Only what this call added. Coming back closes these and nothing else,
        # so overlays the user opened themselves survive.
        self._screensaver_overlays = [(overlays, widget) for widget in overlays[before:]]

    def _stop_screensaver(self) -> None:
        """人回來了：關掉螢幕保護開的那幾個覆蓋層，其他的留著。"""
        for overlays, widget in self._screensaver_overlays:
            try:
                # 先 close() 再從清單移除：只丟掉參考不會跑 closeEvent，計時器與
                # 媒體都停不下來。
                # close() before dropping the reference: dropping it alone never
                # runs closeEvent, so timers and media keep going.
                widget.close()
            except RuntimeError:  # pragma: no cover - 底層物件已消失
                pass
            if widget in overlays:
                overlays.remove(widget)
        self._screensaver_overlays = []

    @staticmethod
    def _startup_language() -> str:
        """
        啟動要用哪一個語言。使用者挑過就用他挑的；還沒挑過而 Steam 有裝，就跟著
        Steam 客戶端的語言，並寫回設定——寫回之後這件事就只會發生這一次。
        Which language to start in. The user's choice if they have made one;
        otherwise the Steam client's language when Steam is installed, written
        back to the settings so it happens exactly once.
        """
        if is_stored("language"):
            return user_setting_dict.get("language", "English")
        from_steam = steam_language()
        if from_steam is None:
            return user_setting_dict.get("language", "English")
        front_engine_logger.info(f"[FrontEngineMainUI] first launch, following Steam: {from_steam}")
        user_setting_dict["language"] = from_steam
        return from_steam

    def _add_tabs(self) -> None:
        """
        建立左側導覽與頁面堆疊 / Build the sidebar and the page stack.

        分頁依用途分組。先前十六個分頁擠成一排，視窗一窄就長出捲動箭頭，而且並排
        的十六個詞看不出誰跟誰是一類；分組之後「我要放東西上螢幕」和「我要專心
        工作」是兩件不同的事，找起來不必逐一讀過去。
        The pages are grouped by what they are for. Sixteen tabs in one row grew
        scroll arrows as soon as the window narrowed, and gave no clue which
        belonged together; grouped, "put something on screen" and "help me
        concentrate" are visibly different errands rather than sixteen words to
        read through.
        """
        groups = [
            ("nav_group_on_screen", "On screen", [
                (self.video_setting_ui, "tab_video_text"),
                (self.image_setting_ui, "tab_image_text"),
                (self.web_setting_ui, "tab_web_text"),
                (self.gif_setting_ui, "tab_gif_text"),
                (self.text_setting_ui, "tab_text_text"),
                (self.sound_player_setting_ui, "tab_sound_text"),
                (self.scene_setting_ui, "tab_scene_text"),
                (self.particle_setting_ui, "tab_particle_text"),
            ]),
            ("nav_group_desktop", "Desktop", [
                (self.pet_setting_ui, "tab_pet_text"),
                (self.wallpaper_setting_ui, "tab_wallpaper_text"),
                (self.widgets_setting_ui, "tab_widgets_text"),
            ]),
            ("nav_group_work", "Work", [
                (self.focus_setting_ui, "tab_focus_text"),
                (self.screen_care_setting_ui, "tab_screen_care_text"),
                (self.presentation_setting_ui, "tab_presentation_text"),
                (self.tools_setting_ui, "tab_tools_text"),
            ]),
            ("nav_group_control", "Control", [
                (self.control_center_ui, "tab_control_center_text"),
            ]),
        ]

        for group_key, group_fallback, entries in groups:
            self.sidebar.add_group(group_key, group_fallback)
            for widget, lang_key in entries:
                index = self.page_stack.addWidget(widget)
                self.sidebar.add_page(lang_key, index)

        # 外掛註冊的分頁自成一組，使用者才看得出哪些不是內建的
        # Plugin tabs get their own group, so it is visible which pages did not
        # ship with the application.
        if FrontEngine_EXTEND_TAB:
            self.sidebar.add_group("nav_group_extensions", "Extensions")
            for widget_name, widget in FrontEngine_EXTEND_TAB.items():
                index = self.page_stack.addWidget(widget())
                self.sidebar.add_page(widget_name, index, widget_name)

        self.sidebar.select_page(0)

    def _setup_icon(self, show_system_tray_ray: bool) -> None:
        """設定視窗 Icon 與系統托盤 / Setup window icon and system tray"""
        self.icon_path = Path(os.getcwd()) / "frontengine.ico"
        self.icon = QIcon(str(self.icon_path))
        self.show_system_tray_ray = show_system_tray_ray
        self.system_tray: Optional[ExtendSystemTray] = None

        if self.icon.isNull():
            # 從別的目錄啟動（pip 安裝的情況幾乎都是）就找不到 frontengine.ico。
            # 托盤選單是唯一會存檔再離開的出口，不能因為少一張圖就整個不見，
            # 改用系統內建圖示。
            # Launched from any other directory - which is the normal case for a
            # pip install - frontengine.ico is simply not there. The tray menu is
            # the only exit that saves settings, so it must not disappear along
            # with the picture; fall back to a built-in icon.
            front_engine_logger.info(f"[FrontEngineMainUI] icon not found: {self.icon_path}")
            self.icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.setWindowIcon(self.icon)

        if ExtendSystemTray.isSystemTrayAvailable() and self.show_system_tray_ray:
            self.system_tray = ExtendSystemTray(main_window=self)
            self.system_tray.setIcon(self.icon)
            self.system_tray.show()
            self.system_tray.setToolTip("FrontEngine")

    def startup_setting(self) -> None:
        """啟動時套用樣式並還原視窗大小/位置（無記錄時最大化） / Apply stylesheet
        and restore the saved window geometry (maximize when none is stored)."""
        theme = user_setting_dict.get("theme")
        apply_stylesheet(self, theme=theme)
        # qt-material 會把樣式表整份寫掉，所以自訂樣式一定要接在它後面
        # apply_stylesheet replaces the whole stylesheet, so ours goes after it
        apply_app_style(self, theme)
        # 還原上次選的畫質檔位（設定檔一直有存，只是從來沒有人讀回來）
        # Restore the quality tier chosen last time: it was always written to the
        # settings file, just never read back.
        self.control_center_ui.set_quality_tier(user_setting_dict.get("quality_tier"))
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

    def retranslate(self) -> int:
        """
        用目前語言把畫面上的文字重寫一遍，回傳重寫了幾條。
        換語言不必重開程式，所以開著的覆蓋層與各分頁的設定都留在原地。
        Rewrite the interface in the current language and return how many
        strings were rewritten. Changing language needs no restart, so open
        overlays and the settings on every page stay exactly where they are.
        """
        applied = retranslator.apply()
        front_engine_logger.info(f"[FrontEngineMainUI] retranslate | {applied} strings")
        return applied

    def _apply_theme(self, theme: str) -> None:
        """套用主題並記住 / Apply a theme and remember it."""
        front_engine_logger.info(f"[FrontEngineMainUI] _apply_theme | theme={theme}")
        try:
            apply_stylesheet(self, theme=theme)
            apply_app_style(self, theme)
            user_setting_dict["theme"] = theme
        except Exception as error:
            front_engine_logger.warning(f"[FrontEngineMainUI] apply theme failed: {error!r}")

    def closeEvent(self, event) -> None:
        """關閉事件：若系統托盤可用則隱藏視窗 / Close event: hide window if system tray is available"""
        # 托盤有可能沒建起來（平台不支援、或啟動時關掉了），沒有就照一般關閉走
        # The tray may not exist at all - unsupported platform, or switched off at
        # startup - in which case this is an ordinary close.
        if self.system_tray is not None and self.system_tray.isVisible():
            self.hide()
            event.ignore()
            return
        # 這條路是真的要關了（X 按鈕、登出、closeAllWindows），所以收尾要在這裡做
        # This branch really is closing - X button, logout, closeAllWindows - so
        # the teardown belongs here.
        self._shutdown()
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
        elif action == "show_shortcuts":
            self.toggle_shortcut_sheet()

    def toggle_shortcut_sheet(self) -> None:
        """
        開關快速鍵速查表。已經開著就收起來，所以同一個快速鍵按第二次是關閉——
        不然使用者得去找別的方法把它關掉。
        Toggle the shortcut sheet: pressing the same shortcut again closes it,
        rather than leaving the user hunting for another way to dismiss it.
        """
        existing = getattr(self, "shortcut_sheet", None)
        if existing is not None:
            try:
                existing.close()
            except RuntimeError:  # pragma: no cover - 底層物件已消失
                pass
            self.shortcut_sheet = None
            return
        sheet = build_sheet(
            get_hotkey_bindings(),
            lambda action: hotkey_action_label(action),
            title=translate("shortcut_sheet_title", "Shortcuts"))
        if sheet is None:
            return
        sheet.set_ui_window_flag()
        sheet.showFullScreen()
        self.shortcut_sheet = sheet

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

    def _on_midi_message(self, message: dict) -> None:
        """
        處理一則 MIDI 訊息（已經由 QueuedConnection 帶回 UI 執行緒）。
        旋鈕轉到底才算一次按下，避免轉動途中連續觸發。
        Handle one MIDI message, already brought back to the UI thread by the
        queued connection. A knob only counts once it reaches the top, so
        turning it does not fire repeatedly on the way.
        """
        if message.get("kind") == "note" and not message.get("pressed"):
            return
        if message.get("kind") == "control" and int(message.get("value", 0)) < 127:
            return
        key = binding_key(message)
        # 遙控設定對話框正在「學習」的話，這一則訊息是拿來新增綁定的，不是拿來
        # 觸發動作的。少了這一段，那顆「學習」按鈕從頭到尾沒有任何東西呼叫它，
        # 整個 UI 也就沒有辦法建立 MIDI 綁定。
        # While the remote dialog is learning, this message defines a binding
        # rather than triggering one. Without this the Learn button had no caller
        # at all, and there was no way to create a MIDI binding from the UI.
        dialog = getattr(self, "remote_dialog", None)
        if dialog is not None:
            try:
                if dialog.learn(key):
                    return
            except RuntimeError:  # pragma: no cover - dialog closed mid-message
                self.remote_dialog = None
        action = current_bindings().get(key)
        if action:
            self._handle_hotkey(action)

    def start_signage(self) -> Optional[str]:
        """開始輪播；設定要求、而且托盤能把視窗叫回來時才收起主視窗。"""
        first = self.signage_service.start()
        if first is not None and current_signage_settings().get("hide_window", True):
            self._hide_for_signage()
        return first

    def _hide_for_signage(self) -> None:
        """
        收起主視窗——但只在系統匣真的能把它叫回來的時候。沒有系統匣就等於
        把唯一能關掉輪播的畫面藏起來，重開也只會再被藏一次，使用者就只能去
        手動改設定檔了。
        Put the main window away - but only when the tray can actually bring it
        back. Without a tray this would hide the only screen that can turn the
        rotation off, and restarting just hides it again, leaving the settings
        file as the only way out.
        """
        if tray_can_restore_window(self):
            self.hide()
            return
        front_engine_logger.info(
            "[FrontEngineMainUI] signage kept the window visible: no tray to restore it from")

    def stop_signage(self) -> None:
        """停止輪播並把主視窗放回來。"""
        self.signage_service.stop()
        self.show()

    def _on_sharing_changed(self, sharing: bool, match: str) -> None:
        """
        偵測到會議程式開著／關掉時，自動把覆蓋層藏出擷取結果或放回去。
        遮蔽用的覆蓋層不受影響——它們本來就是要被看到的。
        Hide the overlays from the capture when a meeting app appears, and put
        them back when it goes. Masking overlays are left alone: being seen is
        the whole point of them.
        """
        front_engine_logger.info(
            f"[MainUI] screen sharing={sharing}" + (f" | {match}" if match else ""))
        self.control_center_ui.set_hide_from_capture(sharing)
        if sharing:
            self._last_toast = show_toast(
                language_wrapper.language_word_dict.get(
                    "screen_privacy_toast", "Overlays hidden from screen capture"))

    def _show_reminder(self, label: str) -> None:
        """提醒到期：在畫面上方顯示一張會自己消失的提示卡。"""
        front_engine_logger.info(f"[MainUI] reminder | {label}")
        self._last_toast = show_toast(label)

    def _persist_clipboard(self) -> None:
        """
        只有使用者勾選「保存到檔案」時才把剪貼簿歷史寫下來；沒勾就確保
        設定裡不留任何內容。
        Write the clipboard history down only when the user asked for it; when
        they did not, make sure nothing is left behind in the settings.
        """
        if user_setting_dict.get("clipboard_persist"):
            user_setting_dict["clipboard_entries"] = self.clipboard_history.to_list()
        else:
            user_setting_dict["clipboard_entries"] = []

    def set_usage_tracking(self, enabled: bool) -> None:
        """開關使用時間統計並記住選擇。"""
        user_setting_dict["usage_tracking"] = bool(enabled)
        write_user_setting()
        if enabled:
            self.usage_service.start()
        else:
            self.usage_service.stop()

    def set_clipboard_history(self, enabled: bool) -> None:
        """開關剪貼簿歷史紀錄並記住選擇。"""
        user_setting_dict["clipboard_history"] = bool(enabled)
        write_user_setting()
        if enabled:
            self.clipboard_watcher.start()
        else:
            self.clipboard_watcher.stop()

    def refresh_rule_services(self) -> None:
        """
        設定對話框按下確定後呼叫：規則與對照表都是每次輪詢重讀，所以只要把
        提醒的計時歸零，其餘服務下一輪就會自己拿到新設定。
        Called after a rule dialog is accepted. Rules and profiles are re-read on
        every poll, so only the reminder timers need resetting here.
        """
        if getattr(self, "reminder_service", None) is not None:
            self.reminder_service.tracker.reset()

    # 關閉時要停掉的背景服務，依相依性由外而內排列
    # The background services to stop on close, outermost first.
    _CLOSING_SERVICES = (
        "preset_schedule_service", "theme_schedule_service", "usage_service",
        "signage_service", "screensaver_service",
        "remote_server", "midi_input", "share_watch_service", "reminder_service",
        "app_profile_service", "smart_pause_service", "hotkey_service",
    )
    # 關閉時要清空的覆蓋層清單
    # The overlay lists to empty on close.
    _CLOSING_WIDGET_LISTS = (
        ("video_setting_ui", "video_widget_list"),
        ("image_setting_ui", "image_widget_list"),
        ("web_setting_ui", "web_widget_list"),
        ("gif_setting_ui", "gif_widget_list"),
        ("sound_player_setting_ui", "sound_widget_list"),
        ("text_setting_ui", "text_widget_list"),
        ("particle_setting_ui", "particle_list"),
        ("pet_setting_ui", "pet_list"),
    )

    def _shutdown(self) -> None:
        """
        存檔並停掉所有服務。放在這裡而不是 close() 裡面，是因為 Qt 的
        QWidget::close() 不是虛擬函式：從標題列的 X、工作階段登出、或
        closeAllWindows() 關閉時，Qt 只會走到 closeEvent，永遠不會呼叫這個
        Python 的 close() 覆寫。收尾工作只寫在 close() 裡，等於只有系統匣的
        「關閉」那一條路會存檔。
        Save everything and stop every service. This lives here rather than in
        close() because QWidget::close() is not virtual in Qt: closing from the
        title-bar X, a session logout, or closeAllWindows() only ever reaches
        closeEvent, never this Python close() override. With the teardown living
        in close() alone, the tray's Quit item was the only exit that saved.
        """
        if self._shutdown_done:
            return
        self._shutdown_done = True
        front_engine_logger.info("[FrontEngineMainUI] shutdown")
        if user_setting_dict.get("restore_last_session"):
            save_last_session(self)
        self._stop_services()
        # 執行緒執行狀態跟著行程活著，不放開的話關掉程式之後螢幕還是不會睡。
        # The execution state lives with the process: without releasing it the
        # display keeps refusing to sleep after the application is gone.
        if getattr(self, "keep_awake", None) is not None:
            self.keep_awake.disable()
        self._save_page_state()
        self._save_window_geometry()
        write_user_setting()
        self._clear_overlays()
        self.scene_setting_ui.close_scene()

    def close(self) -> None:
        """關閉程式並清理資源 / Close application and clear resources"""
        self._shutdown()
        super().close()
        if self.main_app:
            self.main_app.exit(0)

    def _stop_services(self) -> None:
        """停掉所有背景服務（沒建立起來的就跳過）。"""
        for name in self._CLOSING_SERVICES:
            service = getattr(self, name, None)
            if service is not None:
                service.stop()
        if getattr(self, "clipboard_watcher", None) is not None:
            self.clipboard_watcher.stop()
            self._persist_clipboard()

    def _save_page_state(self) -> None:
        """讓幾個分頁在關閉前把自己的東西收好。"""
        if getattr(self, "widgets_setting_ui", None) is not None:
            self.widgets_setting_ui.save_notes()
            self.widgets_setting_ui.stop_spectrum()
        if getattr(self, "tools_setting_ui", None) is not None:
            self.tools_setting_ui.release_pinned_windows()
            self.tools_setting_ui.close_pinned()
            # 複本註冊的是 DWM 縮圖，那是系統資源：視窗沒了也不會自己消失。
            # A replica holds a DWM thumbnail, a system resource that does not
            # go away just because the process is closing.
            self.tools_setting_ui.close_replicas()
            self.tools_setting_ui.stop_camera()
            self.tools_setting_ui.stop_virtual_camera()

    def _clear_overlays(self) -> None:
        """
        關閉並清空各分頁記著的覆蓋層。要先 close() 才丟參考：closeEvent 才是
        停計時器、放掉媒體與攝影機的地方。
        Close the overlays each page is holding, then empty the lists. close()
        comes first because closeEvent is what stops timers and releases media.
        """
        for page_name, attribute in self._CLOSING_WIDGET_LISTS:
            page = getattr(self, page_name, None)
            widget_list = getattr(page, attribute, None) if page is not None else None
            if widget_list is None:
                continue
            for widget in widget_list[:]:
                try:
                    widget.close()
                except RuntimeError:  # 使用者已經關掉，C++ 物件不在了
                    continue
            widget_list.clear()

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