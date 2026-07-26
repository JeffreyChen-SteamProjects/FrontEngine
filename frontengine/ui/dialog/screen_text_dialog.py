"""
畫面文字視窗：顯示 Claude 從截圖讀出來的結果，並提供複製。

第一次使用會先問一次「要把截圖送到 Anthropic 的 API 嗎」，同意後才會送，
而且這個選擇記在設定裡，隨時可以在這裡收回。

The screen-text window: show what Claude read from the capture, and offer to
copy it.

The first use asks whether the screenshot may be sent to Anthropic's API.
Nothing is sent before that is answered, the choice is remembered, and it can
be withdrawn from right here.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QGridLayout, QLabel, QMessageBox, QPlainTextEdit,
    QPushButton, QWidget,
)

from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import tr
from frontengine.utils.screen_text.screen_text_service import API_KEY_ENV, api_key

CONSENT_KEY = "screen_text_consent"


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


def has_consent() -> bool:
    """使用者是否已經同意把截圖送出去。"""
    return bool(user_setting_dict.get(CONSENT_KEY))


def set_consent(granted: bool) -> None:
    """記住（或收回）同意。"""
    user_setting_dict[CONSENT_KEY] = bool(granted)
    write_user_setting()
    front_engine_logger.info(f"[ScreenText] consent = {bool(granted)}")


def ask_for_consent(parent: Optional[QWidget] = None) -> bool:
    """
    問使用者要不要把截圖送到 Anthropic。已經同意過就直接回 True，不再打擾。
    Ask whether screenshots may go to Anthropic. Already-granted consent returns
    True without asking again.
    """
    if has_consent():
        return True
    answer = QMessageBox.question(
        parent,
        _t("screen_text_consent_title", "Send this screenshot?"),
        _t("screen_text_consent_body",
           "Reading text needs the captured area sent to Anthropic's API. It leaves this "
           "machine, and anything visible in the selection goes with it. Your own "
           "ANTHROPIC_API_KEY is used. Send captures?"),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No)
    granted = answer == QMessageBox.StandardButton.Yes
    set_consent(granted)
    return granted


class ScreenTextDialog(QDialog):
    """顯示讀到的文字，可複製，也可以在這裡收回同意。"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        front_engine_logger.info("[ScreenTextDialog] Init")
        super().__init__(parent)
        self.setWindowTitle(_t("screen_text_title", "Text on screen"))

        self.text_edit = QPlainTextEdit(str(text))
        self.text_edit.setReadOnly(False)
        self.copy_button = tr(QPushButton(), "screen_text_copy", "Copy")
        self.copy_button.clicked.connect(self.copy_text)
        self.consent_checkbox = tr(QCheckBox(), "screen_text_consent_toggle",
            "Allow sending captures to Anthropic")
        self.consent_checkbox.setChecked(has_consent())
        self.consent_checkbox.toggled.connect(set_consent)
        self.hint_label = QLabel(self.status_text())
        self.hint_label.setWordWrap(True)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)

        layout = QGridLayout(self)
        layout.addWidget(self.text_edit, 0, 0, 1, 2)
        layout.addWidget(self.copy_button, 1, 0)
        layout.addWidget(self.consent_checkbox, 1, 1)
        layout.addWidget(self.hint_label, 2, 0, 1, 2)
        layout.addWidget(self.button_box, 3, 0, 1, 2)

    @staticmethod
    def status_text() -> str:
        """說明目前為什麼可用或不可用。"""
        if api_key() is None:
            return _t("screen_text_no_key",
                      "Set {env} in your environment to use this.").format(env=API_KEY_ENV)
        return _t("screen_text_ready",
                  "Captures are sent to Anthropic only while the box above is ticked.")

    def set_text(self, text: str) -> None:
        self.text_edit.setPlainText(str(text or ""))

    def text(self) -> str:
        return self.text_edit.toPlainText()

    def copy_text(self) -> bool:
        """把結果放到剪貼簿。"""
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:  # pragma: no cover - no clipboard at all
            return False
        clipboard.setText(self.text())
        return True
