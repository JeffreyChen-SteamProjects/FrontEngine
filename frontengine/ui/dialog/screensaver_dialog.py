"""
螢幕保護設定：閒置多久之後，把哪一頁的覆蓋層放上來。

Screensaver settings: how long idle, and which page's overlay to put on screen.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QGridLayout, QLabel, QSpinBox, QWidget,
)

from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import tr
from frontengine.utils.screensaver.screensaver_service import (
    DEFAULT_SCREENSAVER, MAX_IDLE_MINUTES, MIN_IDLE_MINUTES, SOURCES, clamp_idle_minutes,
    normalize_source,
)

SETTING_KEY = "screensaver"

# 下拉選單的文字用各分頁既有的鍵，省得同一個詞在七種語言裡再翻一次。
# The dropdown reuses each page's existing key rather than translating the same
# word a second time in seven languages.
SOURCE_LABEL_KEYS = {
    "video": ("tab_video_text", "Video"),
    "image": ("tab_image_text", "Image"),
    "gif": ("tab_gif_text", "GIF and WEBP"),
    "particle": ("tab_particle_text", "Particle"),
    "web": ("tab_web_text", "Web"),
}


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


def current_settings() -> Dict[str, Any]:
    """目前的螢幕保護設定（缺項目補預設值）。"""
    stored = user_setting_dict.get(SETTING_KEY)
    settings = dict(DEFAULT_SCREENSAVER)
    if isinstance(stored, dict):
        settings.update({key: stored[key] for key in DEFAULT_SCREENSAVER if key in stored})
    settings["idle_minutes"] = clamp_idle_minutes(settings.get("idle_minutes"))
    settings["source"] = normalize_source(settings.get("source"))
    settings["enabled"] = bool(settings.get("enabled"))
    return settings


class ScreensaverDialog(QDialog):
    """設定閒置多久、顯示哪一頁。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        front_engine_logger.info("[ScreensaverDialog] Init")
        super().__init__(parent)
        self.setWindowTitle(_t("screensaver_title", "Screensaver"))
        settings = current_settings()

        self.enable_checkbox = tr(QCheckBox(), "screensaver_enable", "Show something when idle")
        self.enable_checkbox.setChecked(settings["enabled"])

        self.idle_label = tr(QLabel(), "screensaver_idle_minutes", "Idle for (minutes)")
        self.idle_spinbox = QSpinBox()
        self.idle_spinbox.setRange(MIN_IDLE_MINUTES, MAX_IDLE_MINUTES)
        self.idle_spinbox.setValue(settings["idle_minutes"])

        self.source_label = tr(QLabel(), "screensaver_source", "Show")
        self.source_combobox = QComboBox()
        for name in SOURCES:
            key, fallback = SOURCE_LABEL_KEYS[name]
            self.source_combobox.addItem(_t(key, fallback), name)
        index = self.source_combobox.findData(settings["source"])
        if index >= 0:
            self.source_combobox.setCurrentIndex(index)

        self.hint_label = tr(
            QLabel(), "screensaver_hint",
            "It uses that page as you have it set up, so choose the file there first. "
            "Nothing appears while the page has nothing to show. Moving the mouse or "
            "pressing a key takes it away again, and anything you opened yourself stays.")
        self.hint_label.setWordWrap(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QGridLayout(self)
        layout.addWidget(self.enable_checkbox, 0, 0, 1, 2)
        layout.addWidget(self.idle_label, 1, 0)
        layout.addWidget(self.idle_spinbox, 1, 1)
        layout.addWidget(self.source_label, 2, 0)
        layout.addWidget(self.source_combobox, 2, 1)
        layout.addWidget(self.hint_label, 3, 0, 1, 2)
        layout.addWidget(buttons, 4, 0, 1, 2)

    def collect(self) -> Dict[str, Any]:
        """把畫面上的選擇讀成設定。"""
        return {
            "enabled": self.enable_checkbox.isChecked(),
            "idle_minutes": clamp_idle_minutes(self.idle_spinbox.value()),
            "source": normalize_source(self.source_combobox.currentData()),
        }

    def accept(self) -> None:
        user_setting_dict[SETTING_KEY] = self.collect()
        write_user_setting()
        front_engine_logger.info(
            f"[ScreensaverDialog] saved | {user_setting_dict[SETTING_KEY]}")
        super().accept()
