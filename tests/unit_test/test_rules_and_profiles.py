"""
智慧暫停規則、程式對應預設集、自訂提醒與畫質檔位的純邏輯測試。
Pure-logic tests for the smart-pause rules, per-app profiles, custom reminders
and the quality tiers.
"""
from datetime import datetime, timedelta

from frontengine.show.toast.toast_widget import DEFAULT_DURATION_MS, MIN_DURATION_MS, clamp_duration
from frontengine.utils.app_profile.app_profile_service import normalize_profiles, preset_for_app
from frontengine.utils.platform_info.platform_info import parse_front_app_output
from frontengine.utils.power_mode.power_mode import (
    DEFAULT_TIER, TIER_BALANCED, TIER_HIGH, TIER_SAVER, normalize_tier, tier_interval,
    tier_render_scale,
)
from frontengine.utils.reminder.reminder_service import (
    KIND_AT, KIND_EVERY, MAX_EVERY_MINUTES, ReminderTracker, clamp_every_minutes,
    normalize_reminder, normalize_reminders, parse_time_of_day,
)
from frontengine.utils.smart_pause.pause_rules import (
    REASON_APP, REASON_BATTERY, REASON_FULLSCREEN, app_matches, normalize_app_name, parse_app_list,
    pause_reason, should_pause,
)

ALL_RULES = {"fullscreen": True, "battery": True, "apps": ["photoshop"]}


# --- app name matching ----------------------------------------------------
def test_a_full_path_reduces_to_the_program_name() -> None:
    assert normalize_app_name(r"C:\Program Files\Adobe\Photoshop.exe") == "photoshop"


def test_a_posix_path_reduces_the_same_way() -> None:
    assert normalize_app_name("/usr/bin/blender") == "blender"


def test_quotes_and_spaces_are_stripped() -> None:
    assert normalize_app_name('  "Premiere.EXE" ') == "premiere"


def test_nothing_useful_gives_an_empty_name() -> None:
    assert normalize_app_name(None) == ""
    assert normalize_app_name("   ") == ""


def test_an_app_list_is_split_normalized_and_deduplicated() -> None:
    assert parse_app_list("Photoshop.exe, blender\nPHOTOSHOP") == ["photoshop", "blender"]


def test_a_list_of_names_is_accepted_too() -> None:
    assert parse_app_list(["Krita.exe", " "]) == ["krita"]


def test_a_nonsense_app_list_is_empty() -> None:
    assert parse_app_list(42) == []


def test_matching_ignores_the_folder_and_suffix() -> None:
    assert app_matches(r"D:\tools\Blender.exe", "blender") is True
    assert app_matches("gimp", ["blender"]) is False


# --- pause rules ----------------------------------------------------------
def test_a_fullscreen_app_pauses_by_default() -> None:
    assert pause_reason(None, fullscreen=True) == REASON_FULLSCREEN


def test_fullscreen_can_be_turned_off() -> None:
    assert pause_reason({"fullscreen": False}, fullscreen=True) is None


def test_battery_only_pauses_when_that_rule_is_on() -> None:
    assert pause_reason({"battery": False}, on_battery=True) is None
    assert pause_reason({"battery": True}, on_battery=True) == REASON_BATTERY


def test_a_listed_app_pauses() -> None:
    assert pause_reason(ALL_RULES, active_app="Photoshop.exe") == REASON_APP


def test_an_unlisted_app_does_not_pause() -> None:
    assert pause_reason(ALL_RULES, active_app="notepad.exe") is None


def test_fullscreen_wins_when_several_rules_hold() -> None:
    assert pause_reason(ALL_RULES, fullscreen=True, on_battery=True,
                        active_app="photoshop") == REASON_FULLSCREEN


def test_should_pause_is_the_boolean_view() -> None:
    assert should_pause(ALL_RULES, on_battery=True) is True
    assert should_pause(ALL_RULES) is False


def test_a_malformed_rule_set_falls_back_to_the_defaults() -> None:
    assert pause_reason("not a dict", fullscreen=True) == REASON_FULLSCREEN


# --- foreground app output ------------------------------------------------
def test_the_first_line_of_the_probe_output_is_the_app() -> None:
    assert parse_front_app_output("Code\nsomething else\n") == "Code"


def test_no_probe_output_means_unknown() -> None:
    assert parse_front_app_output("") is None
    assert parse_front_app_output(None) is None
    assert parse_front_app_output("   \n") is None


# --- per-app profiles -----------------------------------------------------
def test_profiles_are_normalized_on_both_sides() -> None:
    assert normalize_profiles({"Photoshop.exe": " Work "}) == {"photoshop": "Work"}


def test_entries_without_an_app_or_a_preset_are_dropped() -> None:
    assert normalize_profiles({"": "Work", "gimp": "  ", "krita": "Art"}) == {"krita": "Art"}


def test_a_malformed_profile_map_is_empty() -> None:
    assert normalize_profiles(["photoshop"]) == {}


def test_looking_up_the_preset_for_an_app() -> None:
    profiles = {"blender": "3D"}
    assert preset_for_app(r"C:\apps\Blender.exe", profiles) == "3D"
    assert preset_for_app("chrome", profiles) is None
    assert preset_for_app(None, profiles) is None


# --- reminders ------------------------------------------------------------
def test_a_time_of_day_is_parsed() -> None:
    assert parse_time_of_day("14:30") == (14, 30)
    assert parse_time_of_day(" 9:05 ") == (9, 5)


def test_an_impossible_time_is_rejected() -> None:
    assert parse_time_of_day("24:00") is None
    assert parse_time_of_day("12:60") is None
    assert parse_time_of_day("noon") is None
    assert parse_time_of_day(None) is None


def test_the_interval_is_clamped_to_something_sane() -> None:
    assert clamp_every_minutes(0) == 1
    assert clamp_every_minutes(10 ** 6) == MAX_EVERY_MINUTES
    assert clamp_every_minutes("abc") == 45


def test_a_recurring_reminder_is_normalized() -> None:
    entry = normalize_reminder({"label": " Water ", "kind": "every", "minutes": "30"})
    assert entry == {"label": "Water", "kind": KIND_EVERY, "minutes": 30, "enabled": True}


def test_a_daily_reminder_keeps_a_padded_time() -> None:
    entry = normalize_reminder({"label": "Standup", "kind": "at", "at": "9:5"})
    assert entry["at"] == "09:05" and entry["kind"] == KIND_AT


def test_reminders_without_a_label_or_with_a_bad_time_are_skipped() -> None:
    assert normalize_reminder({"label": "", "kind": "every"}) is None
    assert normalize_reminder({"label": "x", "kind": "at", "at": "99:99"}) is None
    assert normalize_reminder({"label": "x", "kind": "sometimes"}) is None
    assert normalize_reminder("not a reminder") is None


def test_one_broken_entry_does_not_lose_the_others() -> None:
    reminders = normalize_reminders([
        {"label": "Water", "kind": "every", "minutes": 45},
        {"label": "", "kind": "every"},
        {"label": "Pills", "kind": "at", "at": "21:00"},
    ])
    assert [entry["label"] for entry in reminders] == ["Water", "Pills"]


def test_a_recurring_reminder_does_not_fire_at_startup() -> None:
    now = {"value": datetime(2026, 7, 25, 9, 0)}
    tracker = ReminderTracker(
        lambda: [{"label": "Water", "kind": "every", "minutes": 45}], lambda: now["value"])
    assert tracker.tick() == []


def test_a_recurring_reminder_fires_once_the_interval_passes() -> None:
    now = {"value": datetime(2026, 7, 25, 9, 0)}
    tracker = ReminderTracker(
        lambda: [{"label": "Water", "kind": "every", "minutes": 45}], lambda: now["value"])
    tracker.tick()
    now["value"] += timedelta(minutes=44)
    assert tracker.tick() == []
    now["value"] += timedelta(minutes=2)
    assert tracker.tick() == ["Water"]
    assert tracker.tick() == []


def test_a_daily_reminder_fires_once_that_day() -> None:
    now = {"value": datetime(2026, 7, 25, 8, 0)}
    tracker = ReminderTracker(
        lambda: [{"label": "Standup", "kind": "at", "at": "09:30"}], lambda: now["value"])
    assert tracker.tick() == []
    now["value"] = datetime(2026, 7, 25, 9, 31)
    assert tracker.tick() == ["Standup"]
    now["value"] = datetime(2026, 7, 25, 18, 0)
    assert tracker.tick() == []
    now["value"] = datetime(2026, 7, 26, 9, 30)
    assert tracker.tick() == ["Standup"]


def test_a_disabled_reminder_stays_quiet() -> None:
    now = {"value": datetime(2026, 7, 25, 10, 0)}
    tracker = ReminderTracker(
        lambda: [{"label": "Water", "kind": "every", "minutes": 1, "enabled": False}],
        lambda: now["value"])
    tracker.tick()
    now["value"] += timedelta(hours=3)
    assert tracker.tick() == []


def test_resetting_forgets_the_timers() -> None:
    now = {"value": datetime(2026, 7, 25, 10, 0)}
    tracker = ReminderTracker(
        lambda: [{"label": "Water", "kind": "every", "minutes": 30}], lambda: now["value"])
    tracker.tick()
    tracker.reset()
    now["value"] += timedelta(minutes=31)
    # 歸零後這一刻只是「重新開始計時」，不該立刻補響一次
    # After a reset this tick just restarts the clock; it must not fire late.
    assert tracker.tick() == []


# --- quality tiers --------------------------------------------------------
def test_an_unknown_tier_falls_back_to_the_best_one() -> None:
    assert normalize_tier("nonsense") == DEFAULT_TIER == TIER_HIGH
    assert normalize_tier(None) == TIER_HIGH


def test_the_high_tier_leaves_the_interval_alone() -> None:
    assert tier_interval(16, TIER_HIGH) == 16


def test_lower_tiers_slow_the_refresh_down() -> None:
    assert tier_interval(16, TIER_BALANCED) == 33
    assert tier_interval(16, TIER_SAVER) == 100


def test_a_slower_timer_is_never_sped_up_by_a_tier() -> None:
    assert tier_interval(1000, TIER_SAVER) == 1000


def test_a_bad_interval_still_produces_something_usable() -> None:
    assert tier_interval("abc", TIER_HIGH) == 33


def test_render_scale_shrinks_as_the_tier_drops() -> None:
    assert tier_render_scale(TIER_HIGH) == 1.0
    assert tier_render_scale(TIER_SAVER) < tier_render_scale(TIER_BALANCED) < 1.0


# --- toast ----------------------------------------------------------------
def test_a_toast_is_shown_long_enough_to_read() -> None:
    assert clamp_duration(0) == MIN_DURATION_MS
    assert clamp_duration(8000) == 8000
    assert clamp_duration("abc") == DEFAULT_DURATION_MS
