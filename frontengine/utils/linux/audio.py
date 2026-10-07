"""Opt-in PulseAudio capture: one bounded float frame, never disk/network output."""
from __future__ import annotations
import math
import subprocess  # nosec B404 - owned parec from an absolute allow-list, argv only, shell=False.
import threading
import weakref
from typing import Callable
import numpy
from frontengine.utils.linux.capabilities import parec_path

_captures = weakref.WeakSet()


class PulseCapture:
    """One owned parec process/worker; stop kills only that process and never joins Qt."""
    def __init__(self, device: str | None = None, *, microphone: bool = False,
                 launcher: Callable = subprocess.Popen, executable: Callable = parec_path) -> None:
        self.device = device or ('@DEFAULT_SOURCE@' if microphone else '@DEFAULT_MONITOR@')
        if not isinstance(self.device, str) or not 1 <= len(self.device) <= 512 or '\0' in self.device:
            raise ValueError('Invalid PulseAudio source name')
        self.launcher, self.executable = launcher, executable
        self.lock, self.cancelled = threading.Lock(), threading.Event()
        self.thread, self.process, self.running, self.last_error = None, None, False, ''
        self.frame = numpy.zeros(0, dtype=numpy.float32)
        self.updated = 0.0
        _captures.add(self)

    def start(self) -> bool:
        """Asynchronous startup; actual connection/permission failures remain visible."""
        if self.thread is not None and self.thread.is_alive():
            return self.running
        path = self.executable()
        if path is None:
            self.last_error = 'Install pulseaudio-utils and run PulseAudio or PipeWire Pulse compatibility.'
            return False
        self.cancelled.clear()
        with self.lock:
            self.frame = numpy.zeros(0, dtype=numpy.float32)
            self.updated = 0.0
        self.running, self.last_error = True, ''
        self.thread = threading.Thread(target=self._run, args=(path,), name='FrontEnginePulse', daemon=True)
        self.thread.start()
        return True

    def _run(self, path: str) -> None:
        process = None
        try:
            # All audio stays in a stdout pipe; stderr is discarded to avoid a second blocking/unbounded pipe.
            process = self.launcher([path, '--record', '--raw', '--format=float32le', '--rate=48000',
                                     '--channels=1', '--latency-msec=40', '--client-name=FrontEngine',
                                     '--device=' + self.device], stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, bufsize=0, shell=False)
            with self.lock:
                self.process = process
                if self.cancelled.is_set():
                    process.kill()
            self._read(process)
            if not self.cancelled.is_set():
                self.last_error = 'PulseAudio capture ended: check server, source name and recording permissions.'
        except (OSError, ValueError) as error:
            self.last_error = str(error)[:500]
        finally:
            if process is not None:
                if process.poll() is None:
                    process.kill()
                process.wait()
                if process.stdout:
                    process.stdout.close()
            with self.lock:
                self.process, self.running = None, False

    def _read(self, process) -> None:
        from time import monotonic
        pending = b''
        while not self.cancelled.is_set():
            data = process.stdout.read(8192 - len(pending))
            if not data:
                break
            pending += data
            if len(pending) < 8192:
                continue
            frame = numpy.frombuffer(pending, dtype='<f4').copy()
            frame = numpy.clip(numpy.nan_to_num(frame, nan=0, posinf=0, neginf=0), -1, 1)
            with self.lock:
                if not self.cancelled.is_set():
                    self.frame, self.updated = frame, monotonic()
            pending = b''

    def samples(self) -> numpy.ndarray:
        """Drop stale audio rather than leaving a disconnected device apparently active."""
        from time import monotonic
        with self.lock:
            if not self.running or monotonic() - self.updated > .5:
                return numpy.zeros(0, dtype=numpy.float32)
            return self.frame.copy()

    def level(self) -> float | None:
        samples = self.samples()
        if not len(samples):
            return None
        value = float(numpy.max(numpy.abs(samples)))
        return value if math.isfinite(value) else None

    def stop(self) -> None:
        """Cancel even a worker still spawning; terminate only the owned capture child."""
        self.cancelled.set()
        with self.lock:
            self.running = False
            self.frame = numpy.zeros(0, dtype=numpy.float32)
            if self.process is not None and self.process.poll() is None:
                self.process.kill()


class PulseMeter:
    """Lazy sampling keeps meter construction from recording disabled reactive overlays."""
    def __init__(self, device: str | None = None, *, microphone: bool = False) -> None:
        from PySide6.QtCore import QTimer
        self.capture = PulseCapture(device, microphone=microphone)
        self.started, self.closed = False, False
        self.last_demand = 0.0
        self.idle_timer = QTimer()
        self.idle_timer.setInterval(250)
        self.idle_timer.timeout.connect(self._expire)

    @property
    def last_error(self) -> str:
        return self.capture.last_error

    def level(self) -> float | None:
        from time import monotonic
        if self.closed:
            return None
        self.last_demand = monotonic()
        if not self.started:
            self.started = True
            self.capture.start()
            self.idle_timer.start()
        return self.capture.level()

    def _expire(self) -> None:
        from time import monotonic
        if monotonic() - self.last_demand > 1:
            self.capture.stop()
            self.started = False
            self.idle_timer.stop()

    def close(self) -> None:
        self.closed = True
        self.idle_timer.stop()
        self.capture.stop()


def stop_all() -> None:
    """Stop capture children owned by this FrontEngine process, including lazy shared meters."""
    for capture in list(_captures):
        capture.stop()


def pending() -> bool:
    """Keep the host Qt lifecycle alive until all owned capture workers have reaped children."""
    return any(capture.thread is not None and capture.thread.is_alive() for capture in list(_captures))


def errors() -> list[str]:
    """Report only bounded owned capture failures without reading any new audio."""
    return sorted({capture.last_error for capture in list(_captures) if capture.last_error})[:8]
