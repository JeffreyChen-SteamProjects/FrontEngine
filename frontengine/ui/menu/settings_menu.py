from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from frontengine.ui.dialog.app_profile_dialog import AppProfileDialog
from frontengine.ui.dialog.clipboard_dialog import ClipboardDialog
from frontengine.ui.dialog.hotkey_settings_dialog import HotkeySettingsDialog
from frontengine.ui.dialog.reminder_dialog import ReminderDialog
from frontengine.ui.dialog.rules_dialog import RulesDialog
from frontengine.ui.dialog.remote_control_dialog import RemoteControlDialog
from frontengine.ui.dialog.screen_privacy_dialog import ScreenPrivacyDialog
from frontengine.ui.dialog.preset_schedule_dialog import PresetScheduleDialog
from frontengine.ui.dialog.screensaver_dialog import ScreensaverDialog
from frontengine.utils.keep_awake.keep_awake import available as keep_awake_available
from frontengine.ui.dialog.signage_dialog import SignageDialog
from frontengine.ui.dialog.smart_pause_dialog import SmartPauseDialog
from frontengine.ui.dialog.usage_report_dialog import UsageReportDialog
from frontengine.user_setting.user_setting_file import (
    export_user_setting,
    import_user_setting,
    user_setting_dict,
    write_user_setting,
)
from frontengine.utils.autostart import autostart_service
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator

if TYPE_CHECKING:
    from frontengine.ui.main_ui import FrontEngineMainUI


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


# 同一段文字會出現在建構、登記與警告框三個地方，提成常數免得三份各自漂移。
# The same wording appears at construction, at registration and in a warning
# box; a constant keeps the three from drifting apart.
_AUTOSTART = "Start with the system"
_PLUGINS = "Load plugins (advanced)"
_EXPORT_SETTINGS = "Export settings..."
_IMPORT_SETTINGS = "Import settings..."


def build_settings_menu(ui: "FrontEngineMainUI") -> None:
    """Build the Settings menu with hotkey configuration and settings I/O."""
    front_engine_logger.info(f"[SettingsMenu] build_settings_menu | ui={ui}")
    menu = ui.menu_bar.addMenu(_t("menu_bar_settings", "Settings"))
    retranslator.bind(menu, "menu_bar_settings", "Settings", "setTitle")
    ui.settings_menu = menu

    hotkey_action = QAction(_t("settings_menu_hotkeys", "Hotkeys..."), menu)
    retranslator.bind(hotkey_action, "settings_menu_hotkeys", "Hotkeys...")
    hotkey_action.triggered.connect(lambda: _open_hotkey_dialog(ui))
    menu.addAction(hotkey_action)

    schedule = user_setting_dict.get("theme_schedule")
    theme_schedule_action = QAction(_t("settings_menu_theme_schedule", "Scheduled day/night theme"), menu)
    retranslator.bind(theme_schedule_action, "settings_menu_theme_schedule", "Scheduled day/night theme")
    theme_schedule_action.setCheckable(True)
    theme_schedule_action.setChecked(bool(isinstance(schedule, dict) and schedule.get("enabled")))
    theme_schedule_action.toggled.connect(lambda checked: _toggle_theme_schedule(ui, checked))
    menu.addAction(theme_schedule_action)
    ui.theme_schedule_action = theme_schedule_action

    autostart_action = QAction(_t("settings_menu_autostart", _AUTOSTART), menu)
    retranslator.bind(autostart_action, "settings_menu_autostart", _AUTOSTART)
    autostart_action.setCheckable(True)
    autostart_action.setChecked(autostart_service.is_enabled())
    autostart_action.toggled.connect(lambda checked: _toggle_autostart(ui, checked))
    menu.addAction(autostart_action)
    ui.autostart_action = autostart_action

    keep_awake_action = QAction(_t("settings_menu_keep_awake", "Keep the screen awake"), menu)
    retranslator.bind(keep_awake_action, "settings_menu_keep_awake", "Keep the screen awake")
    keep_awake_action.setCheckable(True)
    keep_awake_action.setChecked(bool(user_setting_dict.get("keep_awake")))
    keep_awake_action.setEnabled(keep_awake_available())
    keep_awake_action.toggled.connect(lambda checked: _toggle_keep_awake(ui, checked))
    menu.addAction(keep_awake_action)
    ui.keep_awake_action = keep_awake_action

    restore_action = QAction(_t("settings_menu_restore_session", "Restore last session"), menu)
    retranslator.bind(restore_action, "settings_menu_restore_session", "Restore last session")
    restore_action.setCheckable(True)
    restore_action.setChecked(bool(user_setting_dict.get("restore_last_session")))
    restore_action.toggled.connect(lambda checked: _toggle_restore_session(checked))
    menu.addAction(restore_action)
    ui.restore_session_action = restore_action

    plugins_action = QAction(_t("settings_menu_plugins", _PLUGINS), menu)
    retranslator.bind(plugins_action, "settings_menu_plugins", _PLUGINS)
    plugins_action.setCheckable(True)
    plugins_action.setChecked(bool(user_setting_dict.get("load_plugins")))
    plugins_action.toggled.connect(lambda checked: _toggle_plugins(ui, checked))
    menu.addAction(plugins_action)
    ui.plugins_action = plugins_action

    menu.addSeparator()
    smart_pause_action = QAction(_t("settings_menu_smart_pause", "Smart pause..."), menu)
    retranslator.bind(smart_pause_action, "settings_menu_smart_pause", "Smart pause...")
    smart_pause_action.triggered.connect(lambda: _open_dialog(ui, SmartPauseDialog))
    menu.addAction(smart_pause_action)
    ui.smart_pause_action = smart_pause_action

    app_profile_action = QAction(_t("settings_menu_app_profiles", "App profiles..."), menu)
    retranslator.bind(app_profile_action, "settings_menu_app_profiles", "App profiles...")
    app_profile_action.triggered.connect(lambda: _open_dialog(ui, AppProfileDialog))
    menu.addAction(app_profile_action)
    ui.app_profile_action = app_profile_action

    reminder_action = QAction(_t("settings_menu_reminders", "Reminders..."), menu)
    retranslator.bind(reminder_action, "settings_menu_reminders", "Reminders...")
    reminder_action.triggered.connect(lambda: _open_dialog(ui, ReminderDialog))
    menu.addAction(reminder_action)
    ui.reminder_action = reminder_action

    # 條件式規則。規則是每次輪詢重讀的，所以存檔後不必重啟服務。
    # The rules are re-read on every poll, so saving needs no service restart.
    rules_action = QAction(_t("settings_menu_rules", "Rules..."), menu)
    retranslator.bind(rules_action, "settings_menu_rules", "Rules...")
    rules_action.triggered.connect(lambda: _open_dialog(ui, RulesDialog))
    menu.addAction(rules_action)
    ui.rules_action = rules_action

    screensaver_action = QAction(_t("settings_menu_screensaver", "Screensaver..."), menu)
    retranslator.bind(screensaver_action, "settings_menu_screensaver", "Screensaver...")
    screensaver_action.triggered.connect(lambda: ScreensaverDialog(ui).exec())
    menu.addAction(screensaver_action)
    ui.screensaver_action = screensaver_action

    preset_schedule_action = QAction(
        _t("settings_menu_preset_schedule", "Scheduled preset..."), menu)
    retranslator.bind(preset_schedule_action, "settings_menu_preset_schedule",
                      "Scheduled preset...")
    preset_schedule_action.triggered.connect(lambda: PresetScheduleDialog(ui).exec())
    menu.addAction(preset_schedule_action)
    ui.preset_schedule_action = preset_schedule_action

    signage_action = QAction(_t("settings_menu_signage", "Signage mode..."), menu)
    retranslator.bind(signage_action, "settings_menu_signage", "Signage mode...")
    signage_action.triggered.connect(lambda: _open_signage_dialog(ui))
    menu.addAction(signage_action)
    ui.signage_action = signage_action

    remote_action = QAction(_t("settings_menu_remote", "Remote control..."), menu)
    retranslator.bind(remote_action, "settings_menu_remote", "Remote control...")
    remote_action.triggered.connect(lambda: _open_remote_dialog(ui))
    menu.addAction(remote_action)
    ui.remote_action = remote_action

    privacy_action = QAction(_t("settings_menu_screen_privacy", "Screen-sharing privacy..."), menu)
    retranslator.bind(privacy_action, "settings_menu_screen_privacy", "Screen-sharing privacy...")
    privacy_action.triggered.connect(lambda: _open_dialog(ui, ScreenPrivacyDialog))
    menu.addAction(privacy_action)
    ui.screen_privacy_action = privacy_action

    usage_action = QAction(_t("settings_menu_usage", "Screen time..."), menu)
    retranslator.bind(usage_action, "settings_menu_usage", "Screen time...")
    usage_action.triggered.connect(lambda: _open_usage_dialog(ui))
    menu.addAction(usage_action)
    ui.usage_action = usage_action

    clipboard_action = QAction(_t("settings_menu_clipboard", "Clipboard history..."), menu)
    retranslator.bind(clipboard_action, "settings_menu_clipboard", "Clipboard history...")
    clipboard_action.triggered.connect(lambda: _open_clipboard_dialog(ui))
    menu.addAction(clipboard_action)
    ui.clipboard_action = clipboard_action

    clipboard_toggle = QAction(_t("settings_menu_clipboard_record", "Record clipboard"), menu)
    retranslator.bind(clipboard_toggle, "settings_menu_clipboard_record", "Record clipboard")
    clipboard_toggle.setCheckable(True)
    clipboard_toggle.setChecked(bool(user_setting_dict.get("clipboard_history")))
    clipboard_toggle.toggled.connect(lambda checked: ui.set_clipboard_history(checked))
    menu.addAction(clipboard_toggle)
    ui.clipboard_toggle_action = clipboard_toggle

    menu.addSeparator()
    export_action = QAction(_t("settings_menu_export", _EXPORT_SETTINGS), menu)
    retranslator.bind(export_action, "settings_menu_export", _EXPORT_SETTINGS)
    export_action.triggered.connect(lambda: _export_settings(ui))
    menu.addAction(export_action)

    import_action = QAction(_t("settings_menu_import", _IMPORT_SETTINGS), menu)
    retranslator.bind(import_action, "settings_menu_import", _IMPORT_SETTINGS)
    import_action.triggered.connect(lambda: _import_settings(ui))
    menu.addAction(import_action)


def _dispose(dialog: QDialog) -> None:
    """
    對話框用完就排定銷毀。它們的 parent 是主視窗，也就是說 C++ 這邊由主視窗
    持有——放掉 Python 參考什麼都不會發生，每開一次設定就多留一個活著的對話框
    （連同它抓著的剪貼簿內容）直到程式結束。用 deleteLater 而不是
    WA_DeleteOnClose：exec() 回來之後呼叫端還要讀 dialog.settings()。
    Schedule the dialog for destruction once it is done with. They are parented
    to the main window, so C++ owns them: dropping the Python reference does
    nothing, and every visit to the menu left another live dialog - along with
    whatever clipboard text it held - alive until the process ended.
    deleteLater rather than WA_DeleteOnClose, because callers still read
    dialog.settings() after exec() returns.
    """
    dialog.deleteLater()


def _toggle_keep_awake(ui: "FrontEngineMainUI", enabled: bool) -> None:
    """開關保持喚醒，並把選擇記下來。做不到時把勾勾拿掉，不要留一個假的開著。"""
    service = getattr(ui, "keep_awake", None)
    if service is None:
        return
    if enabled and not service.enable():
        # 開不起來就把選單的勾勾收回去：勾著卻沒生效比沒有這個選項更糟。
        # If it could not be held, untick: a ticked box that does nothing is
        # worse than no box at all.
        action = getattr(ui, "keep_awake_action", None)
        if action is not None:
            action.setChecked(False)
        return
    if not enabled:
        service.disable()
    user_setting_dict["keep_awake"] = bool(enabled)
    write_user_setting()


def _open_signage_dialog(ui: "FrontEngineMainUI") -> None:
    """開看板設定；按下確定後立刻套用新的輪播狀態。"""
    front_engine_logger.info("[SettingsMenu] open SignageDialog")
    dialog = SignageDialog(ui)
    accepted = dialog.exec() == QDialog.DialogCode.Accepted
    if accepted:
        if dialog.settings().get("enabled"):
            ui.start_signage()
        else:
            ui.stop_signage()
    _dispose(dialog)


def _open_remote_dialog(ui: "FrontEngineMainUI") -> None:
    """開遙控設定，並把它接上 MIDI 的「學習」流程。"""
    front_engine_logger.info("[SettingsMenu] open RemoteControlDialog")
    dialog = RemoteControlDialog(ui, remote=getattr(ui, "remote_server", None),
                                 midi=getattr(ui, "midi_input", None))
    ui.remote_dialog = dialog
    dialog.exec()
    ui.remote_dialog = None
    _dispose(dialog)


def _open_usage_dialog(ui: "FrontEngineMainUI") -> None:
    """開使用時間報告；開關與清除都由對話框直接作用在主視窗的服務上。"""
    front_engine_logger.info("[SettingsMenu] open UsageReportDialog")
    dialog = UsageReportDialog(
        ui.usage_tracker, ui,
        enabled=bool(user_setting_dict.get("usage_tracking")),
        on_toggle=ui.set_usage_tracking)
    dialog.exec()
    _dispose(dialog)


def _open_clipboard_dialog(ui: "FrontEngineMainUI") -> None:
    """開剪貼簿歷史。"""
    front_engine_logger.info("[SettingsMenu] open ClipboardDialog")
    dialog = ClipboardDialog(ui.clipboard_history, ui)
    dialog.exec()
    _dispose(dialog)


def _open_dialog(ui: "FrontEngineMainUI", dialog_class) -> bool:
    """
    開一個設定對話框並回傳使用者是否按下確定。三個規則類對話框都自己負責寫回
    設定，這裡只管開窗與記錄。
    Open one of the rule dialogs and report whether it was accepted. Each dialog
    persists its own settings; this only opens it and logs the outcome.
    """
    front_engine_logger.info(f"[SettingsMenu] open {dialog_class.__name__}")
    dialog = dialog_class(ui)
    accepted = dialog.exec() == QDialog.DialogCode.Accepted
    if accepted:
        refresh = getattr(ui, "refresh_rule_services", None)
        if refresh is not None:
            refresh()
    _dispose(dialog)
    return accepted


def _toggle_autostart(ui: "FrontEngineMainUI", enabled: bool) -> None:
    """開關開機自動啟動；設定失敗時把勾選狀態改回去並告知使用者。"""
    if autostart_service.set_enabled(enabled):
        return
    action = getattr(ui, "autostart_action", None)
    if action is not None:
        action.blockSignals(True)
        action.setChecked(not enabled)
        action.blockSignals(False)
    QMessageBox.warning(
        ui,
        _t("settings_menu_autostart", _AUTOSTART),
        _t("settings_autostart_failed", "Could not change the autostart setting."),
    )


def _toggle_restore_session(enabled: bool) -> None:
    """開關「還原上次工作階段」。"""
    user_setting_dict["restore_last_session"] = bool(enabled)
    write_user_setting()
def _toggle_plugins(ui: "FrontEngineMainUI", enabled: bool) -> None:
    """
    開關外掛載入。外掛是 Python 程式、與本程式同權限，無法沙箱化，
    因此開啟時明確告知風險，並在下次啟動才生效。
    Toggle plugin loading. Plugins are Python and run with this application's
    own privileges — they cannot be sandboxed — so say so plainly when it is
    switched on. It takes effect on the next launch.
    """
    user_setting_dict["load_plugins"] = bool(enabled)
    write_user_setting()
    if enabled:
        QMessageBox.warning(
            ui,
            _t("settings_menu_plugins", _PLUGINS),
            _t("settings_plugins_warning",
               "Plugins are Python code and run with the same privileges as FrontEngine. "
               "Only install plugins you trust. Takes effect on the next launch."),
        )


def _toggle_theme_schedule(ui: "FrontEngineMainUI", enabled: bool) -> None:
    """啟用/停用排程主題並立即套用 / Enable/disable scheduled theme and apply now."""
    front_engine_logger.info(f"[SettingsMenu] toggle theme schedule | enabled={enabled}")
    schedule = user_setting_dict.get("theme_schedule")
    if not isinstance(schedule, dict):
        from frontengine.utils.theme_schedule.theme_schedule_service import DEFAULT_THEME_SCHEDULE

        schedule = dict(DEFAULT_THEME_SCHEDULE)
        user_setting_dict["theme_schedule"] = schedule
    schedule["enabled"] = bool(enabled)
    write_user_setting()
    service = getattr(ui, "theme_schedule_service", None)
    if service is not None:
        service.poll_once()  # apply the scheduled theme immediately when enabling


def _open_hotkey_dialog(ui: "FrontEngineMainUI") -> None:
    dialog = HotkeySettingsDialog(ui)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        ui.reload_hotkeys()
    _dispose(dialog)


def _export_settings(ui: "FrontEngineMainUI") -> None:
    title = _t("settings_menu_export", _EXPORT_SETTINGS)
    destination, _ok = QFileDialog.getSaveFileName(
        ui, title, "frontengine_settings.json", _t("settings_file_filter", "Settings files (*.json)")
    )
    if not destination:
        return
    try:
        export_user_setting(Path(destination))
    except (OSError, ValueError) as error:
        QMessageBox.warning(ui, title, str(error))
        return
    QMessageBox.information(ui, title, _t("settings_exported", "Settings exported."))


def _import_settings(ui: "FrontEngineMainUI") -> None:
    title = _t("settings_menu_import", _IMPORT_SETTINGS)
    source, _ok = QFileDialog.getOpenFileName(
        ui, title, "", _t("settings_file_filter", "Settings files (*.json)")
    )
    if not source:
        return
    try:
        import_user_setting(Path(source))
    except (OSError, ValueError) as error:
        QMessageBox.warning(ui, title, str(error))
        return
    # Hotkeys can be re-applied live; language/theme need a restart.
    if hasattr(ui, "reload_hotkeys"):
        ui.reload_hotkeys()
    QMessageBox.information(
        ui, title, _t("settings_imported", "Settings imported. Restart to apply theme/language.")
    )
