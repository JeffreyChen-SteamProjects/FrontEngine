from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from frontengine.ui.dialog.app_profile_dialog import AppProfileDialog
from frontengine.ui.dialog.clipboard_dialog import ClipboardDialog
from frontengine.ui.dialog.hotkey_settings_dialog import HotkeySettingsDialog
from frontengine.ui.dialog.reminder_dialog import ReminderDialog
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

if TYPE_CHECKING:
    from frontengine.ui.main_ui import FrontEngineMainUI


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


def build_settings_menu(ui: "FrontEngineMainUI") -> None:
    """Build the Settings menu with hotkey configuration and settings I/O."""
    front_engine_logger.info(f"[SettingsMenu] build_settings_menu | ui={ui}")
    menu = ui.menu_bar.addMenu(_t("menu_bar_settings", "Settings"))
    ui.settings_menu = menu

    hotkey_action = QAction(_t("settings_menu_hotkeys", "Hotkeys..."), menu)
    hotkey_action.triggered.connect(lambda: _open_hotkey_dialog(ui))
    menu.addAction(hotkey_action)

    schedule = user_setting_dict.get("theme_schedule")
    theme_schedule_action = QAction(
        _t("settings_menu_theme_schedule", "Scheduled day/night theme"), menu
    )
    theme_schedule_action.setCheckable(True)
    theme_schedule_action.setChecked(bool(isinstance(schedule, dict) and schedule.get("enabled")))
    theme_schedule_action.toggled.connect(lambda checked: _toggle_theme_schedule(ui, checked))
    menu.addAction(theme_schedule_action)
    ui.theme_schedule_action = theme_schedule_action

    autostart_action = QAction(_t("settings_menu_autostart", "Start with the system"), menu)
    autostart_action.setCheckable(True)
    autostart_action.setChecked(autostart_service.is_enabled())
    autostart_action.toggled.connect(lambda checked: _toggle_autostart(ui, checked))
    menu.addAction(autostart_action)
    ui.autostart_action = autostart_action

    restore_action = QAction(_t("settings_menu_restore_session", "Restore last session"), menu)
    restore_action.setCheckable(True)
    restore_action.setChecked(bool(user_setting_dict.get("restore_last_session")))
    restore_action.toggled.connect(lambda checked: _toggle_restore_session(checked))
    menu.addAction(restore_action)
    ui.restore_session_action = restore_action

    plugins_action = QAction(_t("settings_menu_plugins", "Load plugins (advanced)"), menu)
    plugins_action.setCheckable(True)
    plugins_action.setChecked(bool(user_setting_dict.get("load_plugins")))
    plugins_action.toggled.connect(lambda checked: _toggle_plugins(ui, checked))
    menu.addAction(plugins_action)
    ui.plugins_action = plugins_action

    menu.addSeparator()
    smart_pause_action = QAction(_t("settings_menu_smart_pause", "Smart pause..."), menu)
    smart_pause_action.triggered.connect(lambda: _open_dialog(ui, SmartPauseDialog))
    menu.addAction(smart_pause_action)
    ui.smart_pause_action = smart_pause_action

    app_profile_action = QAction(_t("settings_menu_app_profiles", "App profiles..."), menu)
    app_profile_action.triggered.connect(lambda: _open_dialog(ui, AppProfileDialog))
    menu.addAction(app_profile_action)
    ui.app_profile_action = app_profile_action

    reminder_action = QAction(_t("settings_menu_reminders", "Reminders..."), menu)
    reminder_action.triggered.connect(lambda: _open_dialog(ui, ReminderDialog))
    menu.addAction(reminder_action)
    ui.reminder_action = reminder_action

    usage_action = QAction(_t("settings_menu_usage", "Screen time..."), menu)
    usage_action.triggered.connect(lambda: _open_usage_dialog(ui))
    menu.addAction(usage_action)
    ui.usage_action = usage_action

    clipboard_action = QAction(_t("settings_menu_clipboard", "Clipboard history..."), menu)
    clipboard_action.triggered.connect(lambda: _open_clipboard_dialog(ui))
    menu.addAction(clipboard_action)
    ui.clipboard_action = clipboard_action

    clipboard_toggle = QAction(_t("settings_menu_clipboard_record", "Record clipboard"), menu)
    clipboard_toggle.setCheckable(True)
    clipboard_toggle.setChecked(bool(user_setting_dict.get("clipboard_history")))
    clipboard_toggle.toggled.connect(lambda checked: ui.set_clipboard_history(checked))
    menu.addAction(clipboard_toggle)
    ui.clipboard_toggle_action = clipboard_toggle

    menu.addSeparator()
    export_action = QAction(_t("settings_menu_export", "Export settings..."), menu)
    export_action.triggered.connect(lambda: _export_settings(ui))
    menu.addAction(export_action)

    import_action = QAction(_t("settings_menu_import", "Import settings..."), menu)
    import_action.triggered.connect(lambda: _import_settings(ui))
    menu.addAction(import_action)


def _open_usage_dialog(ui: "FrontEngineMainUI") -> None:
    """開使用時間報告；開關與清除都由對話框直接作用在主視窗的服務上。"""
    front_engine_logger.info("[SettingsMenu] open UsageReportDialog")
    dialog = UsageReportDialog(
        ui.usage_tracker, ui,
        enabled=bool(user_setting_dict.get("usage_tracking")),
        on_toggle=ui.set_usage_tracking)
    dialog.exec()


def _open_clipboard_dialog(ui: "FrontEngineMainUI") -> None:
    """開剪貼簿歷史。"""
    front_engine_logger.info("[SettingsMenu] open ClipboardDialog")
    ClipboardDialog(ui.clipboard_history, ui).exec()


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
        _t("settings_menu_autostart", "Start with the system"),
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
            _t("settings_menu_plugins", "Load plugins (advanced)"),
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


def _export_settings(ui: "FrontEngineMainUI") -> None:
    title = _t("settings_menu_export", "Export settings...")
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
    title = _t("settings_menu_import", "Import settings...")
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
