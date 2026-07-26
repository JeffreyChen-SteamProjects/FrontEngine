"""
GIF 編碼與畫面錄製的純邏輯測試。編出來的 GIF 會用 Qt 自己讀回來驗證，
因為「能不能被讀懂」才是這個編碼器唯一該證明的事。

Tests for the GIF encoder and the frame recorder. The encoded GIF is read back
with Qt, because "can it actually be read" is the only thing that matters here.
"""
import numpy
import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QImageReader, QMovie, QPixmap

from frontengine.utils.recording.frame_recorder import (
    DEFAULT_FPS, MAX_FPS, MAX_FRAMES, MIN_FPS, FrameRecorder, clamp_fps, clamp_max_seconds,
    composite_inset, frame_budget, image_to_rgb,
)
from frontengine.utils.recording.gif_writer import (
    MIN_DELAY_MS, build_palette, clamp_delay, encode_gif, lzw_encode, quantize,
)


def solid(width: int, height: int, rgb) -> numpy.ndarray:
    frame = numpy.zeros((height, width, 3), dtype=numpy.uint8)
    frame[:, :] = rgb
    return frame


def solid_pixmap(width: int, height: int, color: str) -> QPixmap:
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor(color))
    return pixmap


# --- palette and quantising -----------------------------------------------
def test_the_palette_fills_every_slot() -> None:
    palette = build_palette()
    assert len(palette) == 256
    assert palette[0] == (0, 0, 0) and (255, 255, 255) in palette


def test_primary_colours_survive_quantising_exactly() -> None:
    palette = build_palette()
    for rgb in ((255, 0, 0), (0, 204, 0), (0, 0, 255), (255, 255, 255)):
        index = quantize(solid(2, 2, rgb))[0, 0]
        assert palette[index] == rgb


def test_an_off_palette_colour_maps_to_its_nearest_neighbour() -> None:
    palette = build_palette()
    index = quantize(solid(2, 2, (250, 5, 5)))[0, 0]
    assert palette[index] == (255, 0, 0)


def test_a_frame_of_the_wrong_shape_is_rejected() -> None:
    flat = numpy.zeros((4, 4), dtype=numpy.uint8)
    with pytest.raises(ValueError):
        quantize(flat)


# --- LZW ------------------------------------------------------------------
def test_the_stream_starts_with_a_clear_code() -> None:
    encoded = lzw_encode([0, 0, 0, 0])
    assert len(encoded) > 0


def test_a_long_run_compresses_far_below_its_length() -> None:
    encoded = lzw_encode([7] * 4000)
    assert len(encoded) < 500


def test_encoding_nothing_still_ends_the_stream() -> None:
    assert len(lzw_encode([])) > 0


# --- GIF ------------------------------------------------------------------
def test_no_frames_gives_no_file() -> None:
    assert encode_gif([]) is None
    assert encode_gif([numpy.zeros((4, 4), dtype=numpy.uint8)]) is None


def test_the_delay_is_never_shorter_than_the_format_allows() -> None:
    assert clamp_delay(0) == MIN_DELAY_MS
    assert clamp_delay(120) == 120
    assert clamp_delay("nonsense") == 100


def test_an_encoded_gif_reads_back_with_the_right_frames(tmp_path) -> None:
    frames = [solid(30, 20, rgb) for rgb in ((255, 0, 0), (0, 204, 0), (0, 0, 255))]
    path = tmp_path / "clip.gif"
    path.write_bytes(encode_gif(frames, delay_ms=80))

    reader = QImageReader(str(path))
    assert reader.canRead() and bytes(reader.format()) == b"gif"
    movie = QMovie(str(path))
    assert movie.isValid() and movie.frameCount() == 3
    seen = []
    for index in range(3):
        movie.jumpToFrame(index)
        image = movie.currentImage()
        assert (image.width(), image.height()) == (30, 20)
        seen.append(image.pixelColor(5, 5).name())
    assert seen == ["#ff0000", "#00cc00", "#0000ff"]


def test_a_frame_of_a_different_size_is_skipped_rather_than_misdrawn(tmp_path) -> None:
    frames = [solid(20, 20, (255, 0, 0)), solid(10, 10, (0, 0, 255)), solid(20, 20, (0, 204, 0))]
    path = tmp_path / "mixed.gif"
    path.write_bytes(encode_gif(frames))
    movie = QMovie(str(path))
    assert movie.frameCount() == 2


# --- recorder -------------------------------------------------------------
def test_the_frame_rate_is_clamped() -> None:
    assert clamp_fps(0) == MIN_FPS
    assert clamp_fps(1000) == MAX_FPS
    assert clamp_fps("nonsense") == DEFAULT_FPS


def test_the_length_is_clamped() -> None:
    assert clamp_max_seconds(0) == 1
    assert clamp_max_seconds(10 ** 6) == 120
    assert clamp_max_seconds(None) == 30


def test_the_frame_budget_respects_both_limits() -> None:
    assert frame_budget(5, 4) == 20
    assert frame_budget(MAX_FPS, 120) == MAX_FRAMES


def test_an_empty_region_is_refused() -> None:
    recorder = FrameRecorder()
    assert recorder.start(QRect(0, 0, 0, 0)) is False
    assert recorder.start(None) is False


def test_recording_stops_itself_at_the_budget() -> None:
    recorder = FrameRecorder()
    recorder.set_grabber(lambda rect: solid_pixmap(20, 20, "#123456"))
    recorder.start(QRect(0, 0, 20, 20), fps=4, max_seconds=1)
    for _ in range(20):
        recorder.capture_frame()
    assert len(recorder.frames) == 4
    assert recorder.running is False


def test_a_failing_grab_records_nothing_but_does_not_raise() -> None:
    recorder = FrameRecorder()

    def boom(_rect):
        raise RuntimeError("no screen")

    recorder.set_grabber(boom)
    recorder.start(QRect(0, 0, 10, 10))
    assert recorder.capture_frame() is False
    assert recorder.frames == []


def test_nothing_recorded_saves_nothing(tmp_path) -> None:
    assert FrameRecorder().save_gif(str(tmp_path / "x.gif")) is None


def test_a_recording_saves_and_reads_back(tmp_path) -> None:
    recorder = FrameRecorder()
    recorder.set_grabber(lambda rect: solid_pixmap(24, 16, "#00cc00"))
    recorder.start(QRect(0, 0, 24, 16), fps=5, max_seconds=1)
    for _ in range(3):
        recorder.capture_frame()
    recorder.stop()
    path = recorder.save_gif(str(tmp_path / "clip.gif"))
    assert path is not None
    movie = QMovie(path)
    assert movie.isValid() and movie.frameCount() == len(recorder.frames)


def test_clearing_frees_the_frames() -> None:
    recorder = FrameRecorder()
    recorder.set_grabber(lambda rect: solid_pixmap(8, 8, "#ffffff"))
    recorder.start(QRect(0, 0, 8, 8))
    recorder.capture_frame()
    recorder.clear()
    assert recorder.frames == []


# --- picture in picture ---------------------------------------------------
def test_the_camera_is_drawn_into_the_corner() -> None:
    base = solid_pixmap(80, 60, "#000000")
    merged = composite_inset(base, solid_pixmap(20, 20, "#ffffff")).toImage()
    assert merged.pixelColor(55, 35).name() == "#ffffff"   # inside the inset
    assert merged.pixelColor(5, 5).name() == "#000000"     # away from it


def test_without_a_camera_the_frame_is_untouched() -> None:
    base = solid_pixmap(40, 30, "#112233")
    assert composite_inset(base, None) is base
    assert composite_inset(base, QPixmap()) is base


def test_the_recorder_composites_the_camera_when_asked() -> None:
    recorder = FrameRecorder()
    recorder.set_grabber(lambda rect: solid_pixmap(80, 60, "#000000"))
    recorder.set_inset_provider(lambda: solid_pixmap(20, 20, "#ffffff"))
    recorder.start(QRect(0, 0, 80, 60))
    frame = recorder.frames[0]
    assert tuple(frame[35, 55]) == (255, 255, 255)
    assert tuple(frame[5, 5]) == (0, 0, 0)


def test_a_failing_camera_does_not_lose_the_frame() -> None:
    recorder = FrameRecorder()
    recorder.set_grabber(lambda rect: solid_pixmap(20, 20, "#334455"))

    def boom():
        raise RuntimeError("camera died")

    recorder.set_inset_provider(boom)
    recorder.start(QRect(0, 0, 20, 20))
    assert len(recorder.frames) == 1


def test_a_null_image_converts_to_nothing() -> None:
    from PySide6.QtGui import QImage

    assert image_to_rgb(QImage()) is None
    assert image_to_rgb(None) is None
