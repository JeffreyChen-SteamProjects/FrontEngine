"""
專注遮罩與桌布播放清單的純邏輯測試。
Pure-logic tests for the focus masks and the wallpaper playlist.
"""
import random

from frontengine.show.wallpaper.wallpaper_widget import MAX_REACT_SCALE, MIN_REACT_SCALE, react_scale
from frontengine.utils.focus_shield.focus_shield import (
    REGION_BOTTOM, REGION_BOTTOM_RIGHT, REGION_FULL, REGION_LEFT, REGION_RIGHT, REGION_TOP,
    clamp_percent, intersects, mask_rect, surrounding_rects,
)
from frontengine.utils.playlist.playlist import (
    MIN_INTERVAL_SECONDS, Playlist, ScheduledPlaylists, clamp_interval, collect_media, in_window,
)

SCREEN = (0, 0, 1920, 1080)


def area(rect) -> int:
    return rect[2] * rect[3]


# --- dimming geometry -----------------------------------------------------
def test_no_active_window_dims_the_whole_screen() -> None:
    assert surrounding_rects(SCREEN, None) == [SCREEN]


def test_a_window_on_another_screen_dims_everything() -> None:
    assert surrounding_rects(SCREEN, (5000, 0, 800, 600)) == [SCREEN]


def test_the_active_window_is_left_clear() -> None:
    active = (400, 300, 800, 400)
    rects = surrounding_rects(SCREEN, active)
    assert all(not intersects(rect, active) for rect in rects), "nothing may cover the window"
    assert sum(area(rect) for rect in rects) == area(SCREEN) - area(active)


def test_a_fullscreen_window_leaves_nothing_to_dim() -> None:
    assert surrounding_rects(SCREEN, SCREEN) == []


def test_a_window_hanging_off_the_edge_is_clipped() -> None:
    rects = surrounding_rects(SCREEN, (-200, -200, 600, 600))
    assert all(rect[0] >= 0 and rect[1] >= 0 for rect in rects)
    assert all(rect[0] + rect[2] <= 1920 and rect[1] + rect[3] <= 1080 for rect in rects)


# --- mask geometry --------------------------------------------------------
def test_percent_is_clamped() -> None:
    assert clamp_percent(6) == 6
    assert clamp_percent(0) == 1
    assert clamp_percent(999) == 100
    assert clamp_percent("some") == 6


def test_bottom_mask_covers_a_taskbar_sized_strip() -> None:
    x, y, width, height = mask_rect(SCREEN, REGION_BOTTOM, 6)
    assert (x, width) == (0, 1920)
    assert height == 64 and y + height == 1080


def test_every_region_stays_inside_the_screen() -> None:
    for region in (REGION_BOTTOM, REGION_TOP, REGION_LEFT, REGION_RIGHT, REGION_BOTTOM_RIGHT,
                   REGION_FULL):
        x, y, width, height = mask_rect(SCREEN, region, 10)
        assert x >= 0 and y >= 0
        assert x + width <= 1920 and y + height <= 1080
        assert width > 0 and height > 0


def test_full_region_covers_everything() -> None:
    assert mask_rect(SCREEN, REGION_FULL, 5) == SCREEN


def test_mask_respects_a_screen_offset() -> None:
    x, y, _width, height = mask_rect((1920, 0, 1280, 720), REGION_BOTTOM, 10)
    assert x == 1920 and y + height == 720


# --- playlist -------------------------------------------------------------
def test_interval_has_a_floor() -> None:
    assert clamp_interval(300) == 300
    assert clamp_interval(1) == MIN_INTERVAL_SECONDS
    assert clamp_interval("soon") == 300


def test_playlist_cycles_in_order() -> None:
    playlist = Playlist(["a", "b", "c"])
    assert [playlist.next() for _ in range(4)] == ["a", "b", "c", "a"]


def test_empty_playlist_yields_nothing() -> None:
    playlist = Playlist([])
    assert playlist.next() is None
    assert playlist.current() is None
    assert len(playlist) == 0


def test_shuffled_playlist_covers_every_item_once_per_round() -> None:
    playlist = Playlist(["a", "b", "c", "d"], shuffle=True, rng=random.Random(7))
    first_round = [playlist.next() for _ in range(4)]
    assert sorted(first_round) == ["a", "b", "c", "d"], "a round must not repeat"
    second_round = [playlist.next() for _ in range(4)]
    assert sorted(second_round) == ["a", "b", "c", "d"]


def test_setting_new_items_restarts() -> None:
    playlist = Playlist(["a", "b"])
    playlist.next()
    playlist.set_items(["x", "y"])
    assert playlist.next() == "x"


def test_blank_entries_are_dropped() -> None:
    assert len(Playlist(["a", "", "  "])) == 1


def test_collect_media_finds_supported_files(tmp_path) -> None:
    (tmp_path / "one.png").write_bytes(b"x")
    (tmp_path / "two.gif").write_bytes(b"x")
    (tmp_path / "notes.txt").write_bytes(b"x")
    found = collect_media(str(tmp_path))
    assert len(found) == 2
    assert all(path.endswith((".png", ".gif")) for path in found)


def test_collect_media_can_recurse(tmp_path) -> None:
    nested = tmp_path / "sub"
    nested.mkdir()
    (tmp_path / "top.png").write_bytes(b"x")
    (nested / "deep.jpg").write_bytes(b"x")
    assert len(collect_media(str(tmp_path))) == 1
    assert len(collect_media(str(tmp_path), recursive=True)) == 2


def test_collect_media_on_a_bad_path(tmp_path) -> None:
    assert collect_media(str(tmp_path / "missing")) == []
    assert collect_media("") == []


# --- scheduling -----------------------------------------------------------
def test_time_windows() -> None:
    assert in_window(10, 8, 18) is True
    assert in_window(20, 8, 18) is False


def test_time_windows_wrap_across_midnight() -> None:
    assert in_window(23, 20, 6) is True
    assert in_window(3, 20, 6) is True
    assert in_window(12, 20, 6) is False


def test_scheduled_playlists_pick_by_hour() -> None:
    day = Playlist(["day.png"])
    night = Playlist(["night.png"])
    schedule = ScheduledPlaylists(default=day)
    schedule.add_window(20, 6, night)
    assert schedule.playlist_for(22) is night
    assert schedule.playlist_for(12) is day


# --- audio reaction -------------------------------------------------------
def test_quiet_audio_leaves_the_wallpaper_alone() -> None:
    assert react_scale(0.0) == MIN_REACT_SCALE


def test_loud_audio_grows_the_wallpaper() -> None:
    assert react_scale(1.0) == MAX_REACT_SCALE
    assert MIN_REACT_SCALE < react_scale(0.5) < MAX_REACT_SCALE


def test_strength_scales_the_effect() -> None:
    assert react_scale(1.0, strength=0) == MIN_REACT_SCALE, "zero strength means no movement"
    assert react_scale(1.0, strength=50) < react_scale(1.0, strength=100)


def test_react_scale_tolerates_bad_input() -> None:
    assert react_scale(None) == MIN_REACT_SCALE
    assert react_scale("loud") == MIN_REACT_SCALE
    assert react_scale(5.0) == MAX_REACT_SCALE
