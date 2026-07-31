"""
預設集排程的星期限制。

時鐘可注入，所以這裡不必等到下週一。要釘住的是兩件會安靜出錯的事：不該跑的日子
不能跑，以及**不該跑的日子仍要記下目前時間**——少了後者，隔天第一次輪詢沒有
「上次」可比，當天的觸發點就會被整個跳過。

Weekday limits on the scheduled preset.

The clock is injected, so nothing waits for Monday. Two things that would fail
quietly are pinned: days that should not run do not, and days that do not run
**still record the current minute** - without that, the first poll of the next day
has no previous value and the crossing is missed entirely.
"""
from datetime import datetime

import pytest

from frontengine.utils.preset_schedule.preset_schedule_service import (
    PresetScheduleService, normalize_days, runs_today,
)

MONDAY = datetime(2026, 8, 3, 8, 59)
TUESDAY = datetime(2026, 8, 4, 8, 59)
SATURDAY = datetime(2026, 8, 8, 8, 59)


@pytest.mark.parametrize("value,expected", [
    (None, []),
    ([], []),
    ([0, 1, 2], [0, 1, 2]),
    ([2, 0, 1], [0, 1, 2]),
    ([1, 1, 1], [1]),
    (["0", 3], [0, 3]),
    ([-1, 7, 99], []),
    ("monday", []),
    (5, []),
])
def test_days_from_a_hand_edited_file_are_tidied(value, expected):
    """設定檔可能被手動改過。壞掉的項目丟掉，不要讓排程在半夜爆掉。"""
    assert normalize_days(value) == expected


def test_no_days_means_every_day():
    """
    勾了零天卻把排程留著開啟，意思幾乎一定是「每天」而不是「永不」——真的不想要
    的話關掉排程就好。
    """
    for weekday in range(7):
        assert runs_today({"days": []}, weekday) is True
        assert runs_today({}, weekday) is True


def test_only_the_chosen_days_run():
    weekdays = {"days": [0, 1, 2, 3, 4]}
    assert runs_today(weekdays, 0) is True     # 週一
    assert runs_today(weekdays, 4) is True     # 週五
    assert runs_today(weekdays, 5) is False    # 週六
    assert runs_today(weekdays, 6) is False    # 週日


def make_service(config, clock):
    return PresetScheduleService(config_provider=lambda: config, now_provider=clock)


def test_it_fires_on_a_chosen_day():
    now = {"value": MONDAY}
    config = {"enabled": True, "preset": "Work", "hour": 9, "minute": 0, "days": [0]}
    service = make_service(config, lambda: now["value"])

    fired = []
    service.preset_due.connect(fired.append)

    service.poll_once()                                   # 08:59, 記下起點
    now["value"] = MONDAY.replace(hour=9, minute=0)
    service.poll_once()                                   # 跨過 09:00
    assert fired == ["Work"]


def test_it_stays_quiet_on_a_day_that_was_not_chosen():
    now = {"value": SATURDAY}
    config = {"enabled": True, "preset": "Work", "hour": 9, "minute": 0, "days": [0, 1, 2, 3, 4]}
    service = make_service(config, lambda: now["value"])

    fired = []
    service.preset_due.connect(fired.append)

    service.poll_once()
    now["value"] = SATURDAY.replace(hour=9, minute=0)
    service.poll_once()
    assert fired == []


def test_a_skipped_day_does_not_break_the_next_one():
    """
    這條是重點。週六不跑，但仍要記下時間；否則週日（或下一個該跑的日子）的第一次
    輪詢沒有「上次」可比，那一天的觸發點就會被整個跳過——而且完全沒有徵兆。
    """
    now = {"value": SATURDAY.replace(hour=8, minute=59)}
    config = {"enabled": True, "preset": "Work", "hour": 9, "minute": 0, "days": [5, 6]}
    service = make_service(config, lambda: now["value"])
    fired = []
    service.preset_due.connect(fired.append)

    # 週六有在清單裡，先確認正常
    service.poll_once()
    now["value"] = SATURDAY.replace(hour=9, minute=0)
    service.poll_once()
    assert fired == ["Work"]

    # 換成只跑週日：週六這一輪不該觸發，但要留下時間記號
    config["days"] = [6]
    fired.clear()
    now["value"] = SATURDAY.replace(hour=8, minute=59)
    service.poll_once()
    now["value"] = SATURDAY.replace(hour=9, minute=0)
    service.poll_once()
    assert fired == []
    assert service._prev_minutes == 9 * 60


def test_the_dialog_offers_exactly_seven_days():
    """
    少一天就是使用者永遠設不到那一天，而且畫面上看不出來少了什麼。
    """
    from frontengine.ui.dialog.preset_schedule_dialog import DAY_KEYS

    assert len(DAY_KEYS) == 7


def test_the_dialog_collects_what_was_ticked(tmp_path, monkeypatch):
    from frontengine.ui.dialog.preset_schedule_dialog import PresetScheduleDialog

    class FakeRepository:
        @staticmethod
        def list_presets():
            return ["Work", "__last_session__", "Evening"]

    dialog = PresetScheduleDialog(repository=FakeRepository())
    # 內部用的預設集不該出現在選單裡
    assert [dialog.preset_combobox.itemText(i) for i in range(dialog.preset_combobox.count())] \
        == ["Work", "Evening"]

    dialog.enable_checkbox.setChecked(True)
    dialog.hour_spinbox.setValue(18)
    dialog.minute_spinbox.setValue(30)
    for index in (0, 4):
        dialog.day_checkboxes[index].setChecked(True)

    collected = dialog.collect()
    assert collected["enabled"] is True
    assert collected["hour"] == 18
    assert collected["minute"] == 30
    assert collected["days"] == [0, 4]
