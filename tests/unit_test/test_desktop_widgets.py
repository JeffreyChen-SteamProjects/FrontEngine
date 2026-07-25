"""
音訊頻譜、正在播放、系統監控與便利貼的純邏輯測試（不需要音效卡）。
Pure-logic tests for the spectrum, now playing, system monitor and sticky
notes - no sound card required.
"""
import numpy

from frontengine.show.monitor.monitor_widget import (
    DEFAULT_HISTORY, MAX_HISTORY, MIN_HISTORY, clamp_history, sparkline_path, stat_percent,
)
from frontengine.show.notes.sticky_note_widget import (
    DEFAULT_COLOR, DEFAULT_HEIGHT, DEFAULT_WIDTH, MIN_SIZE, clamp_size, normalize_note_states,
)
from frontengine.show.spectrum.spectrum_widget import (
    STYLE_BARS, STYLE_RING, bar_rects, normalize_style,
)
from frontengine.utils.audio_meter.loopback_capture import samples_from_buffer
from frontengine.utils.audio_meter.spectrum_analyzer import (
    MAX_BANDS, MIN_BANDS, SpectrumSmoother, band_edges, clamp_bands, magnitudes_to_levels,
    spectrum_bands, to_mono,
)
from frontengine.utils.now_playing.now_playing import format_now_playing

SAMPLE_RATE = 48000


def tone(frequency: float, length: int = 4096) -> numpy.ndarray:
    return numpy.sin(2 * numpy.pi * frequency * numpy.arange(length) / SAMPLE_RATE)


# --- spectrum maths -------------------------------------------------------
def test_the_band_count_is_clamped() -> None:
    assert clamp_bands(1) == MIN_BANDS
    assert clamp_bands(1000) == MAX_BANDS
    assert clamp_bands("nonsense") == 24


def test_band_edges_never_go_backwards() -> None:
    edges = band_edges(16, SAMPLE_RATE, 1024)
    assert edges == sorted(edges)
    assert len(edges) == 17


def test_every_band_owns_at_least_one_bin() -> None:
    edges = band_edges(32, SAMPLE_RATE, 512)
    assert all(high > low for low, high in zip(edges, edges[1:]))


def test_interleaved_stereo_is_averaged_to_mono() -> None:
    assert list(to_mono([1.0, 0.0, 0.5, 0.5], channels=2)) == [0.5, 0.5]


def test_an_odd_tail_is_dropped_rather_than_misaligned() -> None:
    assert list(to_mono([1.0, 1.0, 1.0], channels=2)) == [1.0]


def test_silence_maps_to_zero() -> None:
    assert list(magnitudes_to_levels(numpy.zeros(4))) == [0.0, 0.0, 0.0, 0.0]


def test_a_full_scale_magnitude_maps_to_one() -> None:
    assert magnitudes_to_levels(numpy.array([1.0]))[0] == 1.0


def test_a_low_tone_lights_up_a_low_band() -> None:
    bands = spectrum_bands(tone(200), SAMPLE_RATE, bands=12)
    assert bands.index(max(bands)) < 6


def test_a_high_tone_lights_up_a_high_band() -> None:
    bands = spectrum_bands(tone(9000), SAMPLE_RATE, bands=12)
    assert bands.index(max(bands)) >= 8


def test_silence_gives_a_flat_spectrum() -> None:
    assert spectrum_bands(numpy.zeros(4096), SAMPLE_RATE, bands=8) == [0.0] * 8


def test_too_few_samples_are_reported_as_silence() -> None:
    assert spectrum_bands([0.5] * 8, SAMPLE_RATE, bands=6) == [0.0] * 6


def test_the_requested_number_of_bands_comes_back() -> None:
    assert len(spectrum_bands(tone(440), SAMPLE_RATE, bands=31)) == 31


# --- smoothing ------------------------------------------------------------
def test_bars_rise_towards_a_loud_signal() -> None:
    smoother = SpectrumSmoother(3)
    first = smoother.push([1.0, 1.0, 1.0])[0]
    second = smoother.push([1.0, 1.0, 1.0])[0]
    assert 0.0 < first < second <= 1.0


def test_bars_fall_back_gradually_rather_than_snapping_to_zero() -> None:
    smoother = SpectrumSmoother(2)
    for _ in range(20):
        smoother.push([1.0, 1.0])
    loud = smoother.levels[0]
    quiet = smoother.push([0.0, 0.0])[0]
    assert 0.0 < quiet < loud


def test_no_signal_is_treated_as_silence() -> None:
    smoother = SpectrumSmoother(2)
    for _ in range(10):
        smoother.push([1.0, 1.0])
    assert smoother.push(None)[0] < smoother.levels[0] + 1e-9


def test_peaks_hold_above_the_level_and_drift_down() -> None:
    smoother = SpectrumSmoother(1, peak_decay=0.1)
    for _ in range(20):
        smoother.push([1.0])
    peak_when_loud = smoother.peaks[0]
    for _ in range(5):
        smoother.push([0.0])
    assert smoother.peaks[0] < peak_when_loud
    assert smoother.peaks[0] >= smoother.levels[0]


def test_garbage_values_do_not_break_the_smoother() -> None:
    smoother = SpectrumSmoother(2)
    assert smoother.push(["loud", None]) == [0.0, 0.0]


def test_changing_the_band_count_starts_over() -> None:
    smoother = SpectrumSmoother(4)
    smoother.push([1.0, 1.0, 1.0, 1.0])
    smoother.set_bands(8)
    assert smoother.levels == [0.0] * 8


# --- drawing helpers ------------------------------------------------------
def test_bars_span_the_width_and_stand_on_the_bottom() -> None:
    rects = bar_rects([1.0, 0.5], 100, 50)
    assert len(rects) == 2
    assert rects[0][1] == 0.0                      # full bar starts at the top
    assert abs(rects[1][1] - 25.0) < 1e-6          # half bar starts halfway down
    assert rects[1][0] > rects[0][0]


def test_no_bands_or_no_room_draws_nothing() -> None:
    assert bar_rects([], 100, 50) == []
    assert bar_rects([1.0], 0, 50) == []


def test_an_unknown_style_falls_back_to_bars() -> None:
    assert normalize_style("nonsense") == STYLE_BARS
    assert normalize_style("RING") == STYLE_RING


# --- capture buffers ------------------------------------------------------
def test_float_samples_come_through_unchanged() -> None:
    raw = numpy.array([0.25, -0.75], dtype=numpy.float32).tobytes()
    assert list(samples_from_buffer(raw, 32)) == [0.25, -0.75]


def test_sixteen_bit_samples_are_scaled_to_minus_one_to_one() -> None:
    raw = numpy.array([16384, -16384], dtype=numpy.int16).tobytes()
    assert list(samples_from_buffer(raw, 16)) == [0.5, -0.5]


def test_an_unsupported_bit_depth_yields_nothing() -> None:
    assert samples_from_buffer(b"\x00\x00\x00", 24).size == 0
    assert samples_from_buffer(b"", 32).size == 0


# --- now playing ----------------------------------------------------------
def test_a_track_with_an_artist_reads_naturally() -> None:
    assert format_now_playing("Clair de Lune", "Debussy") == "Debussy - Clair de Lune"


def test_a_title_alone_is_enough() -> None:
    assert format_now_playing("Untitled", "") == "Untitled"


def test_only_knowing_the_app_still_says_something() -> None:
    assert format_now_playing(None, None, "Spotify") == "Spotify"


def test_knowing_nothing_says_nothing() -> None:
    assert format_now_playing(None, None, None) == ""


# --- system monitor -------------------------------------------------------
def test_history_length_is_clamped() -> None:
    assert clamp_history(1) == MIN_HISTORY
    assert clamp_history(99999) == MAX_HISTORY
    assert clamp_history(None) == DEFAULT_HISTORY


def test_a_percentage_field_is_read_and_clamped() -> None:
    assert stat_percent({"cpu": 42.5}, "cpu") == 42.5
    assert stat_percent({"cpu": 140}, "cpu") == 100.0
    assert stat_percent({"cpu": -3}, "cpu") == 0.0


def test_a_missing_reading_is_none_not_zero() -> None:
    assert stat_percent({"cpu": None}, "cpu") is None
    assert stat_percent({}, "cpu") is None
    assert stat_percent({"cpu": "45%"}, "cpu") is None


def test_a_sparkline_needs_at_least_two_points() -> None:
    assert sparkline_path([], 100, 20).isEmpty()
    assert sparkline_path([50.0], 100, 20).isEmpty()
    assert not sparkline_path([10.0, 90.0], 100, 20).isEmpty()


def test_a_sparkline_puts_a_high_value_near_the_top() -> None:
    path = sparkline_path([0.0, 100.0], 100, 20)
    assert path.elementAt(0).y > path.elementAt(1).y


# --- sticky notes ---------------------------------------------------------
def test_a_note_cannot_be_shrunk_to_nothing() -> None:
    assert clamp_size(2, DEFAULT_WIDTH) == MIN_SIZE
    assert clamp_size(None, DEFAULT_HEIGHT) == DEFAULT_HEIGHT
    assert clamp_size(300, DEFAULT_WIDTH) == 300


def test_saved_notes_are_restored_with_their_place_and_colour() -> None:
    states = normalize_note_states([
        {"text": "buy milk", "color": "#ff0000", "x": 10, "y": 20, "width": 200, "height": 150}])
    assert states == [{"text": "buy milk", "color": "#ff0000", "x": 10, "y": 20,
                       "width": 200, "height": 150}]


def test_a_blank_note_is_still_a_note() -> None:
    assert normalize_note_states([{"text": ""}])[0]["text"] == ""


def test_a_broken_colour_falls_back_to_the_default() -> None:
    assert normalize_note_states([{"color": "not a colour"}])[0]["color"] == DEFAULT_COLOR


def test_junk_entries_are_skipped() -> None:
    assert normalize_note_states(["note", 5, None]) == []
    assert normalize_note_states("notes") == []


def test_unreadable_coordinates_fall_back_instead_of_crashing() -> None:
    state = normalize_note_states([{"x": "left", "width": "wide"}])[0]
    assert state["x"] == 120 and state["width"] == DEFAULT_WIDTH
