"""
覆蓋層位置記憶的測試（純設定層，不建立 widget）。
Tests for remembered overlay positions — settings layer only, no widgets.
"""
import pytest

from frontengine.user_setting.user_setting_file import (
    clear_overlay_geometry, default_hotkeys, get_overlay_geometry, save_overlay_geometry,
    user_setting_dict,
)


@pytest.fixture(autouse=True)
def _clean_geometry():
    """每個測試都從乾淨的狀態開始，也不留下痕跡。"""
    clear_overlay_geometry()
    yield
    clear_overlay_geometry()


def test_saved_geometry_round_trips() -> None:
    save_overlay_geometry("GifWidget", 10, 20, 300, 200)
    assert get_overlay_geometry("GifWidget") == [10, 20, 300, 200]


def test_unknown_kind_has_no_geometry() -> None:
    assert get_overlay_geometry("NeverDragged") is None


def test_saving_twice_keeps_the_latest() -> None:
    save_overlay_geometry("TextWidget", 1, 2, 3, 4)
    save_overlay_geometry("TextWidget", 5, 6, 7, 8)
    assert get_overlay_geometry("TextWidget") == [5, 6, 7, 8]


def test_each_kind_is_remembered_separately() -> None:
    save_overlay_geometry("TextWidget", 1, 1, 100, 100)
    save_overlay_geometry("WebWidget", 2, 2, 200, 200)
    assert get_overlay_geometry("TextWidget") == [1, 1, 100, 100]
    assert get_overlay_geometry("WebWidget") == [2, 2, 200, 200]


def test_clearing_forgets_everything() -> None:
    save_overlay_geometry("TextWidget", 1, 2, 3, 4)
    clear_overlay_geometry()
    assert get_overlay_geometry("TextWidget") is None


def test_malformed_settings_are_ignored() -> None:
    user_setting_dict["overlay_geometry"] = {"TextWidget": [1, 2, 3]}
    assert get_overlay_geometry("TextWidget") is None
    user_setting_dict["overlay_geometry"] = {"TextWidget": ["a", "b", "c", "d"]}
    assert get_overlay_geometry("TextWidget") is None
    user_setting_dict["overlay_geometry"] = "not a mapping"
    assert get_overlay_geometry("TextWidget") is None


def test_saving_repairs_a_broken_settings_value() -> None:
    user_setting_dict["overlay_geometry"] = "not a mapping"
    save_overlay_geometry("TextWidget", 1, 2, 3, 4)
    assert get_overlay_geometry("TextWidget") == [1, 2, 3, 4]


def test_lock_has_a_default_hotkey() -> None:
    assert default_hotkeys.get("toggle_lock")
