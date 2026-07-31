"""
預設集排程設定：星期幾、幾點幾分，套用哪一個預設集。

這個排程本來就在跑，卻沒有任何介面——只能手動改 `user_setting.json`，連時間都
不能在畫面上設。所以這裡不只是加上星期，是讓這個功能第一次真的到得了。

Preset schedule settings: which days, what time, which preset.

The schedule was already running with no interface at all - it could only be
configured by hand-editing `user_setting.json`, down to the time of day. So this
is not only about adding days: it is what makes the feature reachable at all.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QGridLayout, QLabel, QSpinBox, QWidget,
)

from frontengine.user_setting.preset_repository import PresetRepository
from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import tr
from frontengine.utils.preset_schedule.preset_schedule_service import (
    DEFAULT_PRESET_SCHEDULE, normalize_days,
)

SETTING_KEY = "preset_schedule"

# 0 = 週一，和 datetime.weekday() 一致
# 0 = Monday, matching datetime.weekday()
DAY_KEYS = (
    ("weekday_monday", "Mon"),
    ("weekday_tuesday", "Tue"),
    ("weekday_wednesday", "Wed"),
    ("weekday_thursday", "Thu"),
    ("weekday_friday", "Fri"),
    ("weekday_saturday", "Sat"),
    ("weekday_sunday", "Sun"),
)


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


def current_settings() -> Dict[str, Any]:
    """目前的排程設定（缺項目補預設值）。"""
    stored = user_setting_dict.get(SETTING_KEY)
    settings = dict(DEFAULT_PRESET_SCHEDULE)
    if isinstance(stored, dict):
        settings.update({key: stored[key] for key in DEFAULT_PRESET_SCHEDULE if key in stored})
    settings["days"] = normalize_days(settings.get("days"))
    settings["enabled"] = bool(settings.get("enabled"))
    return settings


class PresetScheduleDialog(QDialog):
    """設定哪幾天、幾點，自動套用哪一個預設集。"""

    def __init__(self, parent: Optional[QWidget] = None, repository=None) -> None:
        front_engine_logger.info("[PresetScheduleDialog] Init")
        super().__init__(parent)
        self.setWindowTitle(_t("preset_schedule_title", "Scheduled preset"))
        settings = current_settings()
        self._repository = repository or PresetRepository()

        self.enable_checkbox = tr(QCheckBox(), "preset_schedule_enable", "Apply a preset on a schedule")
        self.enable_checkbox.setChecked(settings["enabled"])

        self.preset_label = tr(QLabel(), "preset_schedule_preset", "Preset")
        self.preset_combobox = QComboBox()
        # 只列真的存在的預設集：讓人自己打名字的話，打錯了要等到排程觸發的那一刻
        # 才會發現什麼都沒發生。
        # Only presets that exist are listed: with a free-text name, a typo is
        # discovered when the schedule fires and nothing happens.
        for name in self._preset_names():
            self.preset_combobox.addItem(name, name)
        index = self.preset_combobox.findData(settings.get("preset"))
        if index >= 0:
            self.preset_combobox.setCurrentIndex(index)

        self.time_label = tr(QLabel(), "preset_schedule_time", "At")
        self.hour_spinbox = QSpinBox()
        self.hour_spinbox.setRange(0, 23)
        self.hour_spinbox.setValue(int(settings.get("hour", 9)) % 24)
        self.minute_spinbox = QSpinBox()
        self.minute_spinbox.setRange(0, 59)
        self.minute_spinbox.setValue(int(settings.get("minute", 0)) % 60)

        self.days_label = tr(QLabel(), "preset_schedule_days", "On")
        self.day_checkboxes: List[QCheckBox] = []
        days_holder = QWidget()
        days_layout = QGridLayout(days_holder)
        days_layout.setContentsMargins(0, 0, 0, 0)
        for index, (key, fallback) in enumerate(DAY_KEYS):
            checkbox = tr(QCheckBox(), key, fallback)
            checkbox.setChecked(index in settings["days"])
            days_layout.addWidget(checkbox, index // 4, index % 4)
            self.day_checkboxes.append(checkbox)

        self.hint_label = tr(
            QLabel(), "preset_schedule_hint",
            "With no day ticked it runs every day. It fires once as the time passes, "
            "so starting FrontEngine after that time will not apply it late.")
        self.hint_label.setWordWrap(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QGridLayout(self)
        layout.addWidget(self.enable_checkbox, 0, 0, 1, 3)
        layout.addWidget(self.preset_label, 1, 0)
        layout.addWidget(self.preset_combobox, 1, 1, 1, 2)
        layout.addWidget(self.time_label, 2, 0)
        layout.addWidget(self.hour_spinbox, 2, 1)
        layout.addWidget(self.minute_spinbox, 2, 2)
        layout.addWidget(self.days_label, 3, 0)
        layout.addWidget(days_holder, 3, 1, 1, 2)
        layout.addWidget(self.hint_label, 4, 0, 1, 3)
        layout.addWidget(buttons, 5, 0, 1, 3)

    def _preset_names(self) -> List[str]:
        try:
            return [name for name in self._repository.list_presets()
                    if not name.startswith("__")]
        except OSError as error:  # pragma: no cover - filesystem boundary
            front_engine_logger.warning(f"[PresetScheduleDialog] list failed: {error!r}")
            return []

    def collect(self) -> Dict[str, Any]:
        """把畫面上的選擇讀成設定。"""
        return {
            "enabled": self.enable_checkbox.isChecked(),
            "preset": self.preset_combobox.currentData() or "",
            "hour": self.hour_spinbox.value(),
            "minute": self.minute_spinbox.value(),
            "days": [index for index, box in enumerate(self.day_checkboxes) if box.isChecked()],
        }

    def accept(self) -> None:
        user_setting_dict[SETTING_KEY] = self.collect()
        write_user_setting()
        front_engine_logger.info(
            f"[PresetScheduleDialog] saved | {user_setting_dict[SETTING_KEY]}")
        super().accept()
