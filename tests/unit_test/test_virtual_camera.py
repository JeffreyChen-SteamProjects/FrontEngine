"""
虛擬攝影機輸出的純邏輯測試：尺寸與張數的正規化、畫面縮放、沒有裝置時的行為。

Pure-logic tests for the virtual camera: size and rate normalisation, frame
fitting, and what happens when there is no device.
"""
import numpy
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QPixmap

from frontengine.utils.virtual_camera.camera_feed import VirtualCameraFeed
from frontengine.utils.virtual_camera.virtual_camera import (
    DEFAULT_FPS, DEFAULT_HEIGHT, DEFAULT_WIDTH, MAX_FPS, MIN_FPS, VirtualCameraOutput, available,
    clamp_fps, even_size, fit_frame,
)


def solid(width: int, height: int, rgb) -> numpy.ndarray:
    frame = numpy.zeros((height, width, 3), dtype=numpy.uint8)
    frame[:, :] = rgb
    return frame


# --- normalisation --------------------------------------------------------
def test_the_frame_rate_is_clamped() -> None:
    assert clamp_fps(1) == MIN_FPS
    assert clamp_fps(1000) == MAX_FPS
    assert clamp_fps("nonsense") == DEFAULT_FPS


def test_odd_sizes_are_made_even() -> None:
    # NV12 以 2x2 為單位取樣，奇數尺寸會被驅動拒絕
    assert even_size(641, 361) == (640, 360)
    assert even_size(1, 1) == (2, 2)
    assert even_size(None, "nonsense") == (DEFAULT_WIDTH, DEFAULT_HEIGHT)


# --- fitting --------------------------------------------------------------
def test_a_larger_frame_is_scaled_down_to_the_camera_size() -> None:
    fitted = fit_frame(solid(400, 200, (10, 20, 30)), 100, 100)
    assert fitted.shape == (100, 100, 3)
    assert tuple(fitted[50, 50]) == (10, 20, 30)


def test_a_smaller_frame_is_centred_on_black() -> None:
    fitted = fit_frame(solid(10, 10, (200, 100, 50)), 40, 40)
    assert tuple(fitted[20, 20]) == (200, 100, 50)
    assert tuple(fitted[0, 0]) == (0, 0, 0)


def test_a_malformed_frame_becomes_a_black_frame_of_the_right_size() -> None:
    assert fit_frame(numpy.zeros((4, 4)), 8, 8).shape == (8, 8, 3)
    assert fit_frame(numpy.zeros((0, 0, 3)), 8, 8).shape == (8, 8, 3)


def test_the_aspect_ratio_is_kept_when_scaling_down() -> None:
    # 400x200 放進 100x100：應該變成 100x50 置中，上下留黑
    fitted = fit_frame(solid(400, 200, (255, 255, 255)), 100, 100)
    assert tuple(fitted[5, 50]) == (0, 0, 0), "top is padding"
    assert tuple(fitted[50, 50]) == (255, 255, 255), "middle is content"


# --- output ---------------------------------------------------------------
def test_availability_is_a_plain_bool() -> None:
    assert isinstance(available(), bool)


def test_an_output_normalises_what_it_was_asked_for() -> None:
    output = VirtualCameraOutput(width=641, height=361, fps=999)
    assert (output.width, output.height) == (640, 360)
    assert output.fps == MAX_FPS
    assert output.running is False


def test_sending_before_starting_is_refused() -> None:
    output = VirtualCameraOutput()
    assert output.send(solid(10, 10, (1, 2, 3))) is False
    assert output.frames_sent == 0


def test_stopping_something_that_never_started_is_safe() -> None:
    output = VirtualCameraOutput()
    output.stop()
    assert output.running is False


# --- the feed -------------------------------------------------------------
def test_an_invalid_region_is_refused_with_a_reason() -> None:
    feed = VirtualCameraFeed()
    reasons = []
    feed.failed.connect(reasons.append)
    assert feed.start(QRect(0, 0, 0, 0), 20) is False
    assert feed.start(None, 20) is False
    assert reasons == ["invalid region", "invalid region"]


def test_sending_without_an_open_camera_is_refused() -> None:
    feed = VirtualCameraFeed()
    assert feed.send_frame() is False
    assert feed.device_name() == ""


def test_a_failing_grab_does_not_raise() -> None:
    feed = VirtualCameraFeed()

    def boom(_rect):
        raise RuntimeError("no screen")

    feed.set_grabber(boom)
    assert feed.send_frame() is False


def test_stopping_a_feed_that_never_started_is_safe() -> None:
    feed = VirtualCameraFeed()
    feed.stop()
    assert feed.running is False
