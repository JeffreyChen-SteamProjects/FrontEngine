"""
The colour-vision layer's worker: grab, transform, deliver - off the GUI thread.

Reading a full-HD desktop takes around a tenth of a second and transforming it
takes nearly as long again, so doing it in a timer on the GUI thread made the
whole application stutter. Only rows that changed since the last frame are
transformed, and a frame with no change delivers nothing, so a still screen is
never repainted.
"""
from __future__ import annotations

from threading import Event, Thread
from typing import Callable, Optional

import numpy

from frontengine.utils.color_vision.color_vision import matrix_for
from frontengine.utils.logging.loggin_instance import front_engine_logger

STOP_TIMEOUT_SECONDS = 2.0


class FrameSimulator:
    """Transforms BGRX frames, reusing every row the last frame already had."""

    def __init__(self) -> None:
        self._source: Optional[numpy.ndarray] = None
        self._result: Optional[numpy.ndarray] = None
        self._setting: Optional[tuple] = None

    def transform(self, frame: numpy.ndarray, kind: str, severity: float) -> Optional[numpy.ndarray]:
        """The simulated BGRX frame, or None when nothing changed since the last call."""
        setting = (kind, severity)
        previous = self._source
        if previous is None or setting != self._setting or previous.shape != frame.shape:
            rows = numpy.ones(frame.shape[0], dtype=bool)
            result = numpy.empty_like(frame)
        else:
            rows = (frame[:, :, :3] != previous[:, :, :3]).any(axis=(1, 2))
            if not rows.any():
                return None
            result = self._result.copy()
        result[rows] = simulate_bgrx(frame[rows], kind, severity)
        self._source, self._result, self._setting = frame, result, setting
        return result


def simulate_bgrx(pixels: numpy.ndarray, kind: str, severity: float) -> numpy.ndarray:
    """N x W x 4 BGRX pixels as that kind of colour vision sees them; opaque."""
    # The matrix works on RGB; reversing both axes makes the same matrix work on BGR.
    matrix = matrix_for(kind, severity)[::-1, ::-1]
    converted = pixels[:, :, :3].astype(numpy.float32) @ matrix.T
    result = numpy.empty(pixels.shape, dtype=numpy.uint8)
    result[:, :, :3] = numpy.clip(converted + 0.5, 0, 255).astype(numpy.uint8)
    result[:, :, 3] = 255
    return result


class LiveSimulation:
    """Runs grab-transform-deliver on one thread until stopped."""

    def __init__(self, open_source: Callable[[], object], deliver: Callable[[numpy.ndarray], None],
                 interval_seconds: float) -> None:
        self._open_source = open_source
        self._deliver = deliver
        self.interval_seconds = interval_seconds
        self.kind, self.severity = "", 1.0
        self._stopping, self._wake = Event(), Event()
        self._thread: Optional[Thread] = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def set_simulation(self, kind: str, severity: float) -> None:
        self.kind, self.severity = kind, severity
        self._wake.set()

    def start(self) -> None:
        if self.running:
            return
        self._stopping.clear()
        self._thread = Thread(target=self._run, name="ColorVisionSimulation", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop and wait for the grab in progress; nothing is delivered afterwards."""
        self._stopping.set()
        self._wake.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(STOP_TIMEOUT_SECONDS)

    def _run(self) -> None:
        source = self._open_source()
        if source is None:
            return
        simulator = FrameSimulator()
        try:
            while not self._stopping.is_set():
                self._wake.clear()
                frame = source.grab()
                result = None if frame is None else simulator.transform(frame, self.kind, self.severity)
                if result is not None and not self._stopping.is_set():
                    self._deliver(result)
                self._wake.wait(self.interval_seconds)
        except Exception as error:  # the layer then keeps its last picture instead of crashing
            front_engine_logger.warning(f"[ColorVision] live simulation stopped: {error!r}")
        finally:
            source.close()
