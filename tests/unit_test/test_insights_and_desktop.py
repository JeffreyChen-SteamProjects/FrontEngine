"""
使用時間統計、色覺模擬、剪貼簿歷史與視窗版面的純邏輯測試。
Pure-logic tests for usage tracking, colour-vision simulation, clipboard
history and window layouts.
"""
from datetime import datetime, timedelta

from frontengine.utils.clipboard.clipboard_history import (
    MAX_ENTRY_LENGTH, MAX_LIMIT, MIN_LIMIT, ClipboardHistory, clamp_limit, normalize_entries,
    normalize_entry, preview,
)
from frontengine.utils.color_vision.color_vision import (
    KIND_ACHROMATOPSIA, KIND_DEUTERANOPIA, KIND_PROTANOPIA, KIND_TRITANOPIA, clamp_severity,
    distinguishable, normalize_kind, simulate_rgb,
)
from frontengine.utils.usage_tracking.usage_tracker import (
    MAX_SAMPLE_SECONDS, UsageTracker, clamp_seconds, day_key, format_duration, normalize_history,
)
from frontengine.utils.window_pin.window_layout import (
    MIN_SIZE, capture_layout, normalize_layout, normalize_title, restore_layout,
)

START = datetime(2026, 7, 26, 9, 0)


def tracker_at(clock) -> UsageTracker:
    return UsageTracker(repository=None, now_provider=lambda: clock["now"])


# --- usage tracking -------------------------------------------------------
def test_a_sample_is_capped_so_sleep_is_not_counted_as_work() -> None:
    assert clamp_seconds(30) == 30
    assert clamp_seconds(10 ** 6) == MAX_SAMPLE_SECONDS
    assert clamp_seconds(-5) == 0.0
    assert clamp_seconds("nonsense") == 0.0


def test_the_first_observation_records_nothing() -> None:
    clock = {"now": START}
    tracker = tracker_at(clock)
    assert tracker.observe("code.exe") == 0.0
    assert tracker.totals_for(day_key(START)) == {}


def test_time_is_booked_against_the_previous_app() -> None:
    clock = {"now": START}
    tracker = tracker_at(clock)
    tracker.observe("code.exe")
    clock["now"] += timedelta(seconds=30)
    tracker.observe("code.exe")
    clock["now"] += timedelta(seconds=15)
    tracker.observe("chrome.exe")
    totals = tracker.totals_for(day_key(START))
    assert totals == {"code": 45.0}


def test_switching_apps_splits_the_time() -> None:
    clock = {"now": START}
    tracker = tracker_at(clock)
    tracker.observe("code.exe")
    clock["now"] += timedelta(seconds=60)
    tracker.observe("chrome.exe")
    clock["now"] += timedelta(seconds=20)
    tracker.observe("chrome.exe")
    totals = tracker.totals_for(day_key(START))
    assert totals["code"] == 60.0 and totals["chrome"] == 20.0


def test_pausing_does_not_bill_the_gap_to_the_last_app() -> None:
    clock = {"now": START}
    tracker = tracker_at(clock)
    tracker.observe("code.exe")
    clock["now"] += timedelta(seconds=30)
    tracker.observe("code.exe")
    tracker.pause()
    clock["now"] += timedelta(hours=2)
    tracker.observe("code.exe")
    assert tracker.totals_for(day_key(START)) == {"code": 30.0}


def test_the_report_ranks_apps_by_time() -> None:
    clock = {"now": START}
    tracker = tracker_at(clock)
    for app, seconds in (("chrome.exe", 30), ("code.exe", 90), ("chrome.exe", 10)):
        tracker.observe(app)
        clock["now"] += timedelta(seconds=seconds)
    tracker.observe("code.exe")
    top = tracker.top_apps(day_key(START), limit=2)
    assert [name for name, _seconds in top] == ["code", "chrome"]


def test_totals_and_recent_days_line_up() -> None:
    clock = {"now": START}
    tracker = tracker_at(clock)
    tracker.observe("code.exe")
    clock["now"] += timedelta(seconds=45)
    tracker.observe("code.exe")
    assert tracker.total_seconds(day_key(START)) == 45.0
    days = tracker.recent_days(3)
    assert len(days) == 3 and days[-1][0] == day_key(START) and days[-1][1] == 45.0


def test_a_hand_edited_history_file_does_not_break_the_report() -> None:
    history = normalize_history({
        "2026-07-25": {"Code.exe": 60, "broken": "lots"},
        "2026-07-24": "not a mapping",
        5: {"x.exe": 10},
    })
    assert history["2026-07-25"] == {"code": 60.0}
    assert "2026-07-24" not in history


def test_durations_read_naturally() -> None:
    assert format_duration(45) == "45s"
    assert format_duration(600) == "10m"
    assert format_duration(3900) == "1h 05m"
    assert format_duration("nonsense") == "0s"


def test_clearing_forgets_everything() -> None:
    clock = {"now": START}
    tracker = tracker_at(clock)
    tracker.observe("code.exe")
    clock["now"] += timedelta(seconds=30)
    tracker.observe("code.exe")
    tracker.clear()
    assert tracker.history == {} and tracker.total_seconds(day_key(START)) == 0.0


# --- colour vision --------------------------------------------------------
def test_an_unknown_deficiency_falls_back_to_the_commonest() -> None:
    assert normalize_kind("nonsense") == KIND_DEUTERANOPIA
    assert normalize_kind(None) == KIND_DEUTERANOPIA
    assert normalize_kind("TRITANOPIA") == KIND_TRITANOPIA


def test_severity_is_clamped() -> None:
    assert clamp_severity(-1) == 0.0
    assert clamp_severity(5) == 1.0
    assert clamp_severity("nonsense") == 1.0


def test_no_severity_leaves_the_colour_alone() -> None:
    assert simulate_rgb((10, 120, 240), KIND_PROTANOPIA, 0.0) == (10, 120, 240)


def test_greys_survive_every_deficiency() -> None:
    for kind in (KIND_PROTANOPIA, KIND_DEUTERANOPIA, KIND_TRITANOPIA, KIND_ACHROMATOPSIA):
        assert simulate_rgb((255, 255, 255), kind) == (255, 255, 255)
        assert simulate_rgb((0, 0, 0), kind) == (0, 0, 0)


def test_achromatopsia_leaves_no_colour_at_all() -> None:
    red, green, blue = simulate_rgb((255, 0, 0), KIND_ACHROMATOPSIA)
    assert red == green == blue


def test_a_red_green_pair_collapses_for_a_deuteranope() -> None:
    # 這兩個顏色在一般色覺下差很多，綠色盲眼中卻幾乎一樣
    first, second = (170, 110, 90), (140, 125, 90)
    assert distinguishable(first, second, KIND_DEUTERANOPIA, 0.0) is True
    assert distinguishable(first, second, KIND_DEUTERANOPIA, 1.0) is False


def test_a_short_colour_is_padded_rather_than_crashing() -> None:
    assert simulate_rgb((255,), KIND_PROTANOPIA)[0] >= 0
    assert simulate_rgb(None, KIND_PROTANOPIA) == (0, 0, 0)


# --- clipboard history ----------------------------------------------------
def test_the_history_limit_is_clamped() -> None:
    assert clamp_limit(1) == MIN_LIMIT
    assert clamp_limit(10 ** 6) == MAX_LIMIT
    assert clamp_limit("nonsense") == 50


def test_blank_and_oversized_entries_are_refused() -> None:
    assert normalize_entry("   ") is None
    assert normalize_entry("x" * (MAX_ENTRY_LENGTH + 1)) is None
    assert normalize_entry(None) is None
    assert normalize_entries("not a list") == []


def test_a_plain_string_becomes_an_entry() -> None:
    entry = normalize_entry("hello")
    assert entry["text"] == "hello" and entry["pinned"] is False


def test_the_newest_copy_comes_first() -> None:
    history = ClipboardHistory()
    history.add("one")
    history.add("two")
    assert [entry["text"] for entry in history.ordered()] == ["two", "one"]


def test_copying_the_same_thing_again_moves_it_up_rather_than_duplicating() -> None:
    history = ClipboardHistory()
    history.add("one")
    history.add("two")
    history.add("one")
    assert [entry["text"] for entry in history.ordered()] == ["one", "two"]
    assert len(history) == 2


def test_pinned_entries_sort_first_and_survive_eviction() -> None:
    history = ClipboardHistory(limit=MIN_LIMIT)
    history.add("keep me")
    history.set_pinned("keep me", True)
    for index in range(MIN_LIMIT + 3):
        history.add(f"entry {index}")
    texts = [entry["text"] for entry in history.ordered()]
    assert texts[0] == "keep me"
    assert len(history) == MIN_LIMIT


def test_clearing_keeps_the_pinned_phrases_by_default() -> None:
    history = ClipboardHistory()
    history.add("throwaway")
    history.add("snippet")
    history.set_pinned("snippet", True)
    history.clear()
    assert [entry["text"] for entry in history.entries] == ["snippet"]
    history.clear(keep_pinned=False)
    assert history.entries == []


def test_searching_is_case_insensitive_and_empty_means_everything() -> None:
    history = ClipboardHistory()
    history.add("Hello world")
    history.add("goodbye")
    assert [entry["text"] for entry in history.search("HELLO")] == ["Hello world"]
    assert len(history.search("")) == 2
    assert history.search("nothing here") == []


def test_removing_an_entry_that_is_not_there_is_harmless() -> None:
    history = ClipboardHistory()
    assert history.remove("missing") is False
    assert history.set_pinned("missing", True) is False


def test_a_preview_is_one_line_and_bounded() -> None:
    assert preview("line one\nline two") == "line one line two"
    long_preview = preview("x" * 200, width=20)
    assert len(long_preview) == 20 and long_preview.endswith("…")


def test_saving_can_be_limited_to_pinned_phrases() -> None:
    history = ClipboardHistory()
    history.add("secret")
    history.add("snippet")
    history.set_pinned("snippet", True)
    assert [entry["text"] for entry in history.to_list(include_unpinned=False)] == ["snippet"]


# --- window layouts -------------------------------------------------------
def test_titles_are_compared_loosely() -> None:
    assert normalize_title("  My  Editor ") == normalize_title("my editor")


def test_a_layout_records_every_window_it_can_measure() -> None:
    windows = [(1, "Editor"), (2, "Browser")]
    geometry = {1: (0, 0, 800, 600), 2: None}
    layout = capture_layout(lister=lambda: windows, geometry_reader=geometry.get)
    assert layout == [{"title": "Editor", "x": 0, "y": 0, "width": 800, "height": 600}]


def test_a_malformed_layout_entry_is_skipped() -> None:
    layout = normalize_layout([
        {"title": "Editor", "x": 1, "y": 2, "width": 300, "height": 200},
        {"title": "", "x": 0, "y": 0},
        {"title": "Bad", "x": "left"},
        "not an entry",
    ])
    assert [entry["title"] for entry in layout] == ["Editor"]


def test_a_tiny_saved_size_is_raised_to_something_usable() -> None:
    assert normalize_layout([{"title": "x", "width": 1, "height": 1}])[0]["width"] == MIN_SIZE


def test_restoring_moves_what_it_finds_and_counts_what_it_cannot() -> None:
    moved = []
    layout = [
        {"title": "Editor", "x": 10, "y": 20, "width": 640, "height": 480},
        {"title": "Gone", "x": 0, "y": 0, "width": 100, "height": 100},
    ]

    def mover(handle, x, y, width, height):
        moved.append((handle, x, y, width, height))
        return True

    result = restore_layout(layout, lister=lambda: [(7, "  editor ")], mover=mover)
    assert result == (1, 1)
    assert moved == [(7, 10, 20, 640, 480)]


def test_restoring_nothing_is_not_an_error() -> None:
    assert restore_layout([], lister=lambda: [], mover=lambda *args: True) == (0, 0)
    assert restore_layout("junk", lister=lambda: [], mover=lambda *args: True) == (0, 0)
