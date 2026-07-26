"""
螢幕分享隱私設定：偵測到會議程式時，自動把覆蓋層藏出擷取畫面。

Windows 沒有可靠的「我正在被擷取嗎」API，所以判斷依據是使用者自己列出的
會議程式有沒有開著視窗。這是刻意的：與其猜錯，不如讓使用者說了算。

Screen-sharing privacy: hide the overlays from the capture when a meeting app
turns up.

Windows offers no dependable "am I being captured" API, so the trigger is
whether one of the apps the user listed has a window open. That is deliberate -
better their list than our guess.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QGridLayout, QLabel, QLineEdit, QWidget,
)

from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator
from frontengine.utils.screen_privacy import capture_affinity
from frontengine.utils.screen_privacy.share_watch import DEFAULT_SHARING_APPS
from frontengine.utils.smart_pause.pause_rules import parse_app_list

SETTING_KEY = "screen_share_privacy"
DEFAULT_SETTINGS: Dict[str, Any] = {"enabled": False, "apps": list(DEFAULT_SHARING_APPS)}


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


def current_settings() -> Dict[str, Any]:
    """目前的分享隱私設定（缺項目補預設值）。"""
    stored = user_setting_dict.get(SETTING_KEY)
    settings = dict(DEFAULT_SETTINGS)
    if isinstance(stored, dict):
        settings.update({key: stored[key] for key in DEFAULT_SETTINGS if key in stored})
    settings["apps"] = parse_app_list(settings.get("apps")) or list(DEFAULT_SHARING_APPS)
    return settings


class ScreenPrivacyDialog(QDialog):
    """設定哪些程式算是「正在分享」，以及要不要自動隱藏。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        front_engine_logger.info("[ScreenPrivacyDialog] Init")
        super().__init__(parent)
        self.setWindowTitle(_t("screen_privacy_title", "Screen-sharing privacy"))
        settings = current_settings()

        self.enable_checkbox = QCheckBox(
            _t("screen_privacy_enable", "Hide overlays while one of these apps is open"))
        retranslator.bind(self.enable_checkbox, "screen_privacy_enable", "Hide overlays while one of these apps is open")
        self.enable_checkbox.setChecked(bool(settings.get("enabled")))
        self.apps_label = QLabel(_t("screen_privacy_apps_label", "Meeting and capture apps:"))
        retranslator.bind(self.apps_label, "screen_privacy_apps_label", "Meeting and capture apps:")
        self.apps_edit = QLineEdit(", ".join(settings.get("apps", [])))
        self.apps_edit.setPlaceholderText("zoom, teams, discord")
        self.hint_label = QLabel(
            _t("screen_privacy_hint",
               "Matched against window titles, so a meeting held in a browser tab is caught "
               "too. Your overlays stay on your own screen - only the capture is blank. "
               "Masks stay visible, since covering something is what they are for.")
            if capture_affinity.available() else
            _t("screen_privacy_unsupported",
               "Hiding overlays from screen capture is Windows only."))
        retranslator.bind(self.hint_label, "screen_privacy_hint", "Matched against window titles, so a meeting held in a browser tab is caught " "too. Your overlays stay on your own screen - only the capture is blank. " "Masks stay visible, since covering something is what they are for.") if capture_affinity.available() else _t("screen_privacy_unsupported", "Hiding overlays from screen capture is Windows only.")
        self.hint_label.setWordWrap(True)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QGridLayout(self)
        layout.addWidget(self.enable_checkbox, 0, 0, 1, 2)
        layout.addWidget(self.apps_label, 1, 0, 1, 2)
        layout.addWidget(self.apps_edit, 2, 0, 1, 2)
        layout.addWidget(self.hint_label, 3, 0, 1, 2)
        layout.addWidget(self.button_box, 4, 0, 1, 2)
        for widget in (self.enable_checkbox, self.apps_edit):
            widget.setEnabled(capture_affinity.available())

    def settings(self) -> Dict[str, Any]:
        """對話框上目前的設定。"""
        return {
            "enabled": self.enable_checkbox.isChecked(),
            "apps": parse_app_list(self.apps_edit.text()) or list(DEFAULT_SHARING_APPS),
        }

    def accept(self) -> None:
        settings = self.settings()
        user_setting_dict[SETTING_KEY] = settings
        write_user_setting()
        front_engine_logger.info(f"[ScreenPrivacyDialog] saved | {settings}")
        super().accept()
