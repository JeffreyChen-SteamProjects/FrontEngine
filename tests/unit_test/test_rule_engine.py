"""
條件式規則引擎的測試。

環境（時間、前景程式、電池、閒置）全部由 context 傳入，所以每一種組合都能直接
擺出來驗，不必等到那個時間、也不必真的拔電源。

Tests for the conditional rule engine.

The environment - time, foreground app, battery, idle - arrives in the context,
so every combination can be stated outright instead of waiting for the hour or
actually unplugging the machine.
"""
from datetime import datetime

from frontengine.ui.dialog.rules_dialog import format_days, format_minute, parse_days
from frontengine.utils.rules.rule_engine import (
    ACTION_APPLY_PRESET, ACTION_HIDE_ALL, RuleEngineService, RuleTracker, evaluate,
    has_any_condition, in_time_window, normalize_days, normalize_rule, normalize_rules,
    parse_minute_of_day,
)

MONDAY_EVENING = datetime(2026, 8, 3, 19, 30)   # a Monday
SATURDAY_MORNING = datetime(2026, 8, 8, 9, 0)   # a Saturday


def rule(**overrides):
    """一條有效的規則，測試再各自蓋掉需要的欄位。"""
    base = {
        "label": "night",
        "enabled": True,
        "action": ACTION_APPLY_PRESET,
        "value": "Night",
        "when": {"from": "19:00", "to": "23:00"},
    }
    base.update(overrides)
    return base


def context(**overrides):
    base = {"now": MONDAY_EVENING, "app": "explorer", "fullscreen": False,
            "on_battery": False, "idle_seconds": 0}
    base.update(overrides)
    return base


# --- parsing --------------------------------------------------------------
def test_times_are_parsed_into_minutes() -> None:
    assert parse_minute_of_day("19:30") == 19 * 60 + 30
    assert parse_minute_of_day("00:00") == 0
    assert parse_minute_of_day("24:00") is None
    assert parse_minute_of_day("half past seven") is None
    assert parse_minute_of_day(None) is None


def test_a_time_window_can_cross_midnight() -> None:
    """「睡前」本來就跨午夜；不支援的話那個情境根本寫不出來。"""
    assert in_time_window(23 * 60, 22 * 60, 6 * 60) is True
    assert in_time_window(2 * 60, 22 * 60, 6 * 60) is True
    assert in_time_window(12 * 60, 22 * 60, 6 * 60) is False


def test_days_are_tidied() -> None:
    assert normalize_days([2, 0, 0, 9, "1"]) == [0, 1, 2]
    assert normalize_days(None) == []
    assert normalize_days("monday") == []


# --- normalizing ----------------------------------------------------------
def test_a_rule_without_a_label_is_dropped() -> None:
    assert normalize_rule(rule(label="  ")) is None


def test_an_unknown_action_is_dropped() -> None:
    assert normalize_rule(rule(action="format_the_disk")) is None


def test_an_action_that_needs_a_value_is_dropped_without_one() -> None:
    """「套用預設集」沒有預設集名稱時什麼都做不了，存起來只是個看不懂的空殼。"""
    assert normalize_rule(rule(value="")) is None
    assert normalize_rule(rule(action=ACTION_HIDE_ALL, value="")) is not None


def test_broken_rules_do_not_take_the_good_ones_with_them() -> None:
    rules = normalize_rules([rule(), {"nonsense": True}, rule(label="other")])
    assert [entry["label"] for entry in rules] == ["night", "other"]


# --- evaluating -----------------------------------------------------------
def test_a_time_rule_holds_inside_its_window() -> None:
    assert evaluate(normalize_rule(rule()), context()) is True
    assert evaluate(normalize_rule(rule()), context(now=SATURDAY_MORNING)) is False


def test_a_disabled_rule_never_holds() -> None:
    assert evaluate(normalize_rule(rule(enabled=False)), context()) is False


def test_an_empty_condition_never_holds() -> None:
    """
    全空的條件永遠成立，等於「一啟動就套用」，幾乎都是還沒填完的規則。
    An empty condition is always true - "apply at startup" - and is almost
    always a half-filled rule.
    """
    empty = normalize_rule(rule(when={}))
    assert has_any_condition(empty["when"]) is False
    assert evaluate(empty, context()) is False


def test_conditions_combine_with_and() -> None:
    """
    這正是既有四套排程做不到的：時段、星期、程式三個條件同時成立才動作。
    This is what the four existing schedulers cannot do: time, weekday and app
    all having to hold at once.
    """
    combined = normalize_rule(rule(when={
        "from": "19:00", "to": "23:00", "days": [0], "apps": "code"}))
    assert evaluate(combined, context(app="code.exe")) is True
    assert evaluate(combined, context(app="chrome")) is False, "wrong app"
    assert evaluate(combined, context(now=SATURDAY_MORNING, app="code")) is False, "wrong day"


def test_a_missing_reading_does_not_satisfy_a_condition() -> None:
    """讀不到前景程式時，不該把「這個程式在前景」當成成立。"""
    app_rule = normalize_rule(rule(when={"apps": "code"}))
    assert evaluate(app_rule, context(app=None)) is False
    battery_rule = normalize_rule(rule(when={"battery": True}))
    assert evaluate(battery_rule, context(on_battery=None)) is False


def test_a_boolean_condition_matches_both_ways() -> None:
    not_gaming = normalize_rule(rule(when={"fullscreen": False}))
    assert evaluate(not_gaming, context(fullscreen=False)) is True
    assert evaluate(not_gaming, context(fullscreen=True)) is False


def test_idle_is_a_threshold_not_an_equality() -> None:
    idle_rule = normalize_rule(rule(when={"idle_minutes": 5}))
    assert evaluate(idle_rule, context(idle_seconds=299)) is False
    assert evaluate(idle_rule, context(idle_seconds=300)) is True
    assert evaluate(idle_rule, context(idle_seconds=None)) is False


# --- edge triggering ------------------------------------------------------
def test_a_rule_fires_once_not_every_poll() -> None:
    """
    每幾秒重套一次預設集，會把使用者手動改的東西一直蓋掉。這是整個引擎最
    重要的一條性質。
    Re-applying a preset every few seconds would keep overwriting whatever the
    user changed by hand. This is the engine's most important property.
    """
    tracker = RuleTracker()
    rules = [rule()]
    assert len(tracker.tick(rules, context())) == 1
    assert tracker.tick(rules, context()) == [], "still true, already done"
    assert tracker.tick(rules, context()) == []


def test_a_rule_rearms_after_going_false() -> None:
    tracker = RuleTracker()
    rules = [rule()]
    tracker.tick(rules, context())
    tracker.tick(rules, context(now=SATURDAY_MORNING))       # falls false
    assert len(tracker.tick(rules, context())) == 1, "true again, so it fires again"


def test_a_deleted_rule_is_forgotten() -> None:
    """
    忘不掉的話，同名規則之後再建立時會被當成「還在成立」而永遠不觸發。
    Without forgetting, recreating a rule with the same label looks like it was
    still true and never fires again.
    """
    tracker = RuleTracker()
    tracker.tick([rule()], context())
    assert tracker.active("night") is True
    tracker.tick([], context())
    assert tracker.active("night") is False
    assert len(tracker.tick([rule()], context())) == 1


# --- service --------------------------------------------------------------
def test_the_service_emits_what_fired() -> None:
    fired = []
    service = RuleEngineService(rules_provider=lambda: [rule()],
                                context_provider=context)
    service.rule_fired.connect(fired.append)
    service.poll_once()
    assert [entry["label"] for entry in fired] == ["night"]
    service.poll_once()
    assert len(fired) == 1, "edge triggered through the service too"


def test_a_failing_provider_does_not_break_the_poll() -> None:
    def broken():
        raise RuntimeError("settings went away")

    service = RuleEngineService(rules_provider=broken, context_provider=context)
    assert service.poll_once() == []


def test_stopping_rearms_everything() -> None:
    service = RuleEngineService(rules_provider=lambda: [rule()], context_provider=context)
    service.poll_once()
    service.stop()
    assert len(service.poll_once()) == 1, "a fresh start re-evaluates from scratch"


# --- dialog round trip ----------------------------------------------------
def test_days_survive_a_round_trip_through_the_table() -> None:
    assert format_days([0, 1, 4]) == "Mon,Tue,Fri"
    assert parse_days("Mon,Tue,Fri") == [0, 1, 4]
    assert parse_days("0, 1,4") == [0, 1, 4], "typed numbers are accepted too"
    assert parse_days("") == []


def test_times_survive_a_round_trip_through_the_table() -> None:
    assert format_minute(parse_minute_of_day("19:30")) == "19:30"
    assert format_minute(None) == ""
