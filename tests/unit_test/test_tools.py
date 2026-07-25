"""
量測、截圖路徑保護、視窗釘選與攝影機外框的純邏輯測試。
Pure-logic tests for measuring, the capture path guard, window pinning and the
camera frame shapes.
"""
import tempfile
from pathlib import Path

from frontengine.show.camera.camera_widget import (
    SHAPE_CIRCLE, SHAPE_RECTANGLE, SHAPE_ROUNDED, normalize_shape,
)
from frontengine.show.capture.region_capture import MIN_CAPTURE_SIZE, is_usable, safe_capture_path
from frontengine.show.measure.measure_widget import MODE_ANGLE, MODE_COLOR, MODE_RULER, normalize_mode
from frontengine.utils.measure.measure import (
    FORMAT_CSS_VAR, FORMAT_HEX, FORMAT_HSL, FORMAT_RGB, angle_at, clamp_channel, distance,
    format_color, measurement_text, to_hex, to_hsl,
)
from frontengine.utils.window_pin.window_pin import (
    MAX_OPACITY_PERCENT, MIN_OPACITY_PERCENT, alpha_from_percent, clamp_opacity,
)


# --- colour formats -------------------------------------------------------
def test_a_channel_is_clamped_to_a_byte() -> None:
    assert clamp_channel(-20) == 0
    assert clamp_channel(300) == 255
    assert clamp_channel("nonsense") == 0
    assert clamp_channel(127.6) == 128


def test_hex_is_lowercase_and_padded() -> None:
    assert to_hex((18, 52, 86)) == "#123456"
    assert to_hex((0, 0, 0)) == "#000000"


def test_pure_red_reads_as_full_saturation() -> None:
    assert to_hsl((255, 0, 0)) == (0, 100, 50)


def test_grey_has_no_hue_or_saturation() -> None:
    assert to_hsl((128, 128, 128)) == (0, 0, 50)


def test_each_colour_notation_is_paste_ready() -> None:
    assert format_color((255, 0, 0), FORMAT_HEX) == "#ff0000"
    assert format_color((255, 0, 0), FORMAT_RGB) == "rgb(255, 0, 0)"
    assert format_color((255, 0, 0), FORMAT_HSL) == "hsl(0, 100%, 50%)"
    assert format_color((18, 52, 86), FORMAT_CSS_VAR) == "--color: #123456;"


def test_an_unknown_notation_falls_back_to_hex() -> None:
    assert format_color((18, 52, 86), "klingon") == "#123456"


def test_a_short_colour_tuple_is_padded_rather_than_crashing() -> None:
    assert format_color((255,)) == "#ff0000"
    assert format_color(None) == "#000000"


# --- measuring ------------------------------------------------------------
def test_distance_is_the_straight_line() -> None:
    assert distance((0, 0), (3, 4)) == 5.0


def test_the_readout_names_width_height_and_diagonal() -> None:
    assert measurement_text((10, 10), (110, 60)) == "100 x 50 px  (111.8 px)"


def test_measuring_backwards_reads_the_same() -> None:
    assert measurement_text((110, 60), (10, 10)) == measurement_text((10, 10), (110, 60))


def test_a_square_corner_is_ninety_degrees() -> None:
    assert angle_at((0, 0), (1, 0), (0, 1)) == 90.0


def test_a_straight_line_is_one_hundred_and_eighty() -> None:
    assert angle_at((0, 0), (1, 0), (-1, 0)) == 180.0


def test_the_same_direction_twice_is_zero_degrees() -> None:
    # acos of a value a hair under 1 leaves floating-point dust, so allow for it
    assert angle_at((0, 0), (2, 2), (5, 5)) < 0.001


def test_an_arm_of_no_length_reports_no_angle() -> None:
    assert angle_at((0, 0), (0, 0), (1, 1)) == 0.0


def test_an_unknown_measure_mode_falls_back_to_the_picker() -> None:
    assert normalize_mode("nonsense") == MODE_COLOR
    assert normalize_mode("RULER") == MODE_RULER
    assert normalize_mode(None) == MODE_COLOR
    assert normalize_mode(MODE_ANGLE) == MODE_ANGLE


# --- capture --------------------------------------------------------------
def test_a_tiny_drag_is_not_a_capture() -> None:
    from PySide6.QtCore import QRect

    assert is_usable(QRect(0, 0, MIN_CAPTURE_SIZE, MIN_CAPTURE_SIZE)) is True
    assert is_usable(QRect(0, 0, 1, 100)) is False
    assert is_usable(QRect(0, 0, 0, 0)) is False


def test_a_plain_filename_saves_inside_the_folder() -> None:
    with tempfile.TemporaryDirectory() as folder:
        path = safe_capture_path(folder, "shot.png")
        assert path is not None and path.parent == Path(folder).resolve()


def test_a_traversing_name_is_reduced_to_its_last_part() -> None:
    with tempfile.TemporaryDirectory() as folder:
        path = safe_capture_path(folder, "../../escape.png")
        assert path is not None
        assert path.parent == Path(folder).resolve() and path.name == "escape.png"


def test_an_absolute_name_cannot_escape_either() -> None:
    with tempfile.TemporaryDirectory() as folder:
        path = safe_capture_path(folder, "C:/Windows/evil.png")
        assert path is not None and path.parent == Path(folder).resolve()


def test_a_name_that_is_only_a_traversal_is_refused() -> None:
    with tempfile.TemporaryDirectory() as folder:
        assert safe_capture_path(folder, "..") is None
        assert safe_capture_path(folder, "") is None


# --- window pinning -------------------------------------------------------
def test_opacity_stays_visible() -> None:
    assert clamp_opacity(0) == MIN_OPACITY_PERCENT
    assert clamp_opacity(500) == MAX_OPACITY_PERCENT
    assert clamp_opacity(55) == 55
    assert clamp_opacity("nonsense") == MAX_OPACITY_PERCENT


def test_percentages_map_onto_the_full_alpha_range() -> None:
    assert alpha_from_percent(100) == 255
    assert alpha_from_percent(MIN_OPACITY_PERCENT) == 51
    assert alpha_from_percent(50) == 128


# --- camera ---------------------------------------------------------------
def test_an_unknown_camera_shape_falls_back_to_a_rectangle() -> None:
    assert normalize_shape("triangle") == SHAPE_RECTANGLE
    assert normalize_shape("CIRCLE") == SHAPE_CIRCLE
    assert normalize_shape(None) == SHAPE_RECTANGLE
    assert normalize_shape(SHAPE_ROUNDED) == SHAPE_ROUNDED
