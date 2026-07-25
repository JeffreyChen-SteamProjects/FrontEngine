"""
簡報工具的純邏輯測試：筆畫樣式、漣漪動畫、按鍵格式化與放大鏡取樣區域。
Pure-logic tests for the presenting tools: stroke styling, ripple animation,
key formatting, and the magnifier's source rectangle.
"""
from frontengine.show.presentation.annotation_overlay import (
    DEFAULT_PEN_COLOR, MAX_WIDTH, MIN_WIDTH, TOOL_ERASER, TOOL_HIGHLIGHTER, TOOL_PEN, clamp_width,
    stroke_style,
)
from frontengine.show.presentation.cursor_effects import (
    RIPPLE_STEPS, clamp_radius, ripple_alpha, ripple_radius,
)
from frontengine.show.presentation.keystroke_display import (
    format_combo, format_key, visible_keys,
)
from frontengine.show.presentation.magnifier import MAX_ZOOM, MIN_ZOOM, clamp_zoom, source_rect
from frontengine.utils.input_watch.input_watch_service import combo_with_modifiers, is_modifier


# --- annotation -----------------------------------------------------------
def test_pen_width_is_clamped() -> None:
    assert clamp_width(4) == 4
    assert clamp_width(0) == MIN_WIDTH
    assert clamp_width(999) == MAX_WIDTH
    assert clamp_width("thick") == 4


def test_pen_draws_solid_at_the_chosen_width() -> None:
    color, width = stroke_style(TOOL_PEN, "#ff3b30", 6)
    assert color.name() == "#ff3b30"
    assert color.alpha() == 255
    assert width == 6


def test_highlighter_is_translucent_and_wider() -> None:
    color, width = stroke_style(TOOL_HIGHLIGHTER, "#ffcc00", 5)
    assert color.alpha() < 255, "a highlighter must let the screen show through"
    assert width > 5


def test_eraser_is_wider_than_the_pen() -> None:
    _pen_color, pen_width = stroke_style(TOOL_PEN, "#000000", 4)
    _eraser_color, eraser_width = stroke_style(TOOL_ERASER, "#000000", 4)
    assert eraser_width > pen_width


def test_invalid_colour_falls_back() -> None:
    color, _width = stroke_style(TOOL_PEN, "not a colour", 4)
    assert color.name() == DEFAULT_PEN_COLOR


# --- cursor effects -------------------------------------------------------
def test_radius_is_clamped() -> None:
    assert clamp_radius(28) == 28
    assert clamp_radius(0) >= 8
    assert clamp_radius(99999) <= 600
    assert clamp_radius(None) == 28


def test_ripple_grows_outward() -> None:
    radii = [ripple_radius(step, 30) for step in range(RIPPLE_STEPS + 1)]
    assert radii == sorted(radii)
    assert radii[0] == 30
    assert radii[-1] > radii[0]


def test_ripple_fades_out() -> None:
    alphas = [ripple_alpha(step) for step in range(RIPPLE_STEPS + 1)]
    assert alphas == sorted(alphas, reverse=True)
    assert alphas[-1] == 0, "the ripple must disappear at the end"


def test_ripple_tolerates_out_of_range_steps() -> None:
    assert ripple_alpha(-5) <= 200
    assert ripple_alpha(999) == 0
    assert ripple_radius(999, 30) > 0


# --- keystroke formatting -------------------------------------------------
def test_single_keys_read_naturally() -> None:
    assert format_key("a") == "A"
    assert format_key("'s'") == "S"
    assert format_key("space") == "Space"
    assert format_key("Key.enter") == "Enter"
    assert format_key("f5") == "F5"
    assert format_key("up") == "↑"
    assert format_key("") == ""


def test_modifiers_get_friendly_names() -> None:
    assert format_key("ctrl_l") == "Ctrl"
    assert format_key("shift_r") == "Shift"
    assert format_key("cmd") == "Win"


def test_combos_are_joined_and_deduped() -> None:
    assert format_combo(["ctrl", "shift", "s"]) == "Ctrl + Shift + S"
    assert format_combo(["ctrl_l", "ctrl_r", "c"]) == "Ctrl + C", "one Ctrl is enough"
    assert format_combo([]) == ""


def test_visible_keys_expire() -> None:
    entries = [("A", 100.0), ("B", 101.0), ("C", 102.0)]
    assert visible_keys(entries, now=102.0, hold_seconds=2.0) == ["A", "B", "C"]
    assert visible_keys(entries, now=103.0, hold_seconds=2.0) == ["B", "C"], "A aged out"
    assert visible_keys(entries, now=200.0, hold_seconds=2.0) == []


def test_visible_keys_are_capped() -> None:
    entries = [(str(index), 100.0) for index in range(20)]
    assert len(visible_keys(entries, now=100.0, hold_seconds=5.0, limit=6)) == 6


# --- input watching -------------------------------------------------------
def test_modifier_detection() -> None:
    assert is_modifier("ctrl_l") is True
    assert is_modifier("shift") is True
    assert is_modifier("a") is False


def test_held_modifiers_join_the_next_key() -> None:
    assert combo_with_modifiers("s", ["ctrl", "shift"]) == ["ctrl", "shift", "s"]
    assert combo_with_modifiers("a", []) == ["a"]
    assert combo_with_modifiers("ctrl", ["ctrl"]) == ["ctrl"], "a modifier alone is not doubled"


# --- magnifier ------------------------------------------------------------
def test_zoom_is_clamped() -> None:
    assert clamp_zoom(2.0) == 2.0
    assert clamp_zoom(0.1) == MIN_ZOOM
    assert clamp_zoom(100) == MAX_ZOOM
    assert clamp_zoom("big") == 2.0


def test_source_rect_centres_on_the_cursor() -> None:
    rect = source_rect((500, 500), 240, 2.0, (0, 0, 1920, 1080))
    assert rect.width() == 120 and rect.height() == 120
    assert rect.center().x() in (499, 500) and rect.center().y() in (499, 500)


def test_higher_zoom_grabs_a_smaller_area() -> None:
    low = source_rect((500, 500), 240, 2.0, (0, 0, 1920, 1080))
    high = source_rect((500, 500), 240, 4.0, (0, 0, 1920, 1080))
    assert high.width() < low.width()


def test_source_rect_stays_on_screen() -> None:
    for point in ((0, 0), (1920, 1080), (-50, -50)):
        rect = source_rect(point, 240, 2.0, (0, 0, 1920, 1080))
        assert rect.left() >= 0 and rect.top() >= 0
        assert rect.right() <= 1920 and rect.bottom() <= 1080
