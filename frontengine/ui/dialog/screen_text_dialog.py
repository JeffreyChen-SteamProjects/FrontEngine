"""Show OCR results and backend status, with separate text and screenshot cloud consent."""
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
from frontengine.utils.screen_text.screen_text_service import API_KEY_ENV, ScreenTextResult, api_key
from frontengine.utils.screen_text.local_ocr import LocalOcr

CONSENT_KEY = "screen_text_consent"
TEXT_CONSENT_KEY = "screen_text_text_consent"


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


def has_text_consent() -> bool:
    return bool(user_setting_dict.get(TEXT_CONSENT_KEY))


def set_text_consent(granted: bool) -> None:
    user_setting_dict[TEXT_CONSENT_KEY] = bool(granted)
    write_user_setting()


def ask_for_text_consent(parent: Optional[QWidget] = None) -> bool:
    if has_text_consent():
        return True
    answer = QMessageBox.question(
        parent, _t("screen_text_text_consent_title", "Send recognized text?"),
        _t("screen_text_text_consent_body",
           "Translation and questions use Anthropic's API. Only the locally recognized text "
           "will be sent; it leaves this machine. Your own ANTHROPIC_API_KEY is used. "
           "Allow recognized text to be sent?"),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No)
    granted = answer == QMessageBox.StandardButton.Yes
    set_text_consent(granted)
    return granted


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
           "Local recognition did not succeed. Cloud fallback sends the captured area to "
           "Anthropic's API. It leaves this machine, including everything visible in the "
           "selection. Your own ANTHROPIC_API_KEY is used. Allow captures to be sent?"),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No)
    granted = answer == QMessageBox.StandardButton.Yes
    set_consent(granted)
    return granted


class ScreenTextDialog(QDialog):
    """顯示讀到的文字，可複製，也可以在這裡收回同意。"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None,
                 result: Optional[ScreenTextResult] = None) -> None:
        front_engine_logger.info("[ScreenTextDialog] Init")
        super().__init__(parent)
        self.setWindowTitle(_t("screen_text_title", "Text on screen"))

        self.text_edit = QPlainTextEdit(result.text if result is not None else str(text))
        self.text_edit.setReadOnly(False)
        self.copy_button = tr(QPushButton(), "screen_text_copy", "Copy")
        self.copy_button.clicked.connect(self.copy_text)
        self.consent_checkbox = tr(QCheckBox(), "screen_text_consent_toggle",
            "Allow sending captures to Anthropic")
        self.consent_checkbox.setChecked(has_consent())
        self.consent_checkbox.toggled.connect(set_consent)
        self.text_consent_checkbox = tr(QCheckBox(), "screen_text_text_consent_toggle",
                                        "Allow sending recognized text to Anthropic")
        self.text_consent_checkbox.setChecked(has_text_consent())
        self.text_consent_checkbox.toggled.connect(set_text_consent)
        details = result.backend if result is not None else ""
        if result is not None and result.error:
            details += "\n" + result.error
        self.backend_label = QLabel(_t("screen_text_backend", "Backend: {backend}").format(
            backend=details or _t("screen_text_backend_none", "No recognition yet")))
        self.backend_label.setWordWrap(True)
        self.hint_label = QLabel(self.status_text())
        self.hint_label.setWordWrap(True)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)

        layout = QGridLayout(self)
        layout.addWidget(self.text_edit, 0, 0, 1, 2)
        layout.addWidget(self.copy_button, 1, 0)
        layout.addWidget(self.consent_checkbox, 1, 1)
        layout.addWidget(self.text_consent_checkbox, 2, 0, 1, 2)
        layout.addWidget(self.backend_label, 3, 0, 1, 2)
        layout.addWidget(self.hint_label, 4, 0, 1, 2)
        layout.addWidget(self.button_box, 5, 0, 1, 2)

    @staticmethod
    def status_text() -> str:
        """說明目前為什麼可用或不可用。"""
        local = _t("screen_text_local_ready", "Local OCR works without a key or cloud consent.")
        if not LocalOcr().available():
            local = _t("screen_text_local_missing", "Install a local OCR backend to extract text offline.")
        cloud = _t("screen_text_cloud_consent", "Cloud processing requires the corresponding consent above.")
        if api_key() is None:
            cloud = _t("screen_text_cloud_no_key", "Cloud translation/fallback needs {env}.").format(
                env=API_KEY_ENV)
        return local + " " + cloud

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
