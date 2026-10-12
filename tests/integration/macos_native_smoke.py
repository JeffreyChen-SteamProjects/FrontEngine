"""Run via runpy on a real Mac. Reports TCC skips without requesting permissions.

With Screen Recording authorized, capture a window owned by this process and verify
its pixels. With Accessibility authorized, move and restore that same test window.
No external application, media player, microphone, or MIDI device is manipulated.
"""
import json
import sys
from dataclasses import asdict

from PySide6.QtCore import QTimer, QRect
from PySide6.QtWidgets import QApplication, QWidget

from frontengine.utils.macos import get_backend
from frontengine.utils.macos.backend import MacOSBackend
from frontengine.utils.macos.region_capture import RegionCaptureAdapter


def own_window_number(widget: QWidget) -> int:
    """Qt's cocoa winId is an owned NSView pointer; use its NSWindow identifier."""
    import ctypes
    import objc
    view = objc.objc_object(c_void_p=ctypes.c_void_p(int(widget.winId())))
    return int(view.window().windowNumber())


def move_and_restore_owned_window(widget: QWidget, backend: MacOSBackend) -> bool:
    """Check native geometry after moving and restoring only this probe's NSWindow."""
    from PySide6.QtTest import QTest
    handle = own_window_number(widget)
    original = backend.window_geometry(handle)
    if original is None:
        raise RuntimeError(f'Owned native window geometry is unavailable: id={handle}, visible={widget.isVisible()}')
    target = (original[0] + 10, original[1] + 10, *original[2:])
    moved = False
    try:
        moved = backend.move_window(handle, *target)
        if not moved:
            raise RuntimeError(backend.last_error)
        QTest.qWait(150)
        actual = backend.window_geometry(handle)
        if actual is None or any(abs(a - b) > 2 for a, b in zip(actual, target)):
            raise RuntimeError(f'Native move did not reach its target: {actual} versus {target}')
        return True
    finally:
        if moved:
            if not backend.move_window(handle, *original):
                raise RuntimeError('Owned window restoration failed: ' + backend.last_error)
            QTest.qWait(150)
            actual = backend.window_geometry(handle)
            if actual is None or any(abs(a - b) > 2 for a, b in zip(actual, original)):
                raise RuntimeError('Owned window geometry was not restored')


def main() -> None:
    if sys.platform != 'darwin':
        print(json.dumps({'status': 'skipped', 'reason': 'macOS is required'}))
        return
    app = QApplication.instance() or QApplication([])
    backend = get_backend()
    names = ('screen_capture', 'system_audio', 'microphone', 'window_geometry',
             'window_move', 'midi', 'media_keys', 'global_hotkey', 'foreign_topmost',
             'foreign_opacity', 'spaces', 'capture_exclusion')
    status = {name: asdict(backend.capability(name)) for name in names}
    if not status['screen_capture']['available']:
        print(json.dumps({'status': 'skipped', 'capabilities': status}))
        return
    _run_fixture(app, backend, status)


def _run_fixture(app: QApplication, backend: MacOSBackend, status: dict) -> None:
    widget = QWidget()
    widget.setWindowTitle('FrontEngine native integration smoke')
    widget.setStyleSheet('background: rgb(255, 0, 255);')
    area = app.primaryScreen().availableGeometry()
    widget.setGeometry(area.x() + 80, area.y() + 80, 96, 64)
    widget.show()
    capture = RegionCaptureAdapter()
    errors, frames, moved = [], [], [False]
    timer = QTimer()
    timer.setInterval(30)

    def check_frame():
        image = capture.latest_frame()
        if image is not None and not image.isNull():
            frames.append(image.toImage())
            timer.stop()
            try:
                color = frames[0].pixelColor(48, 32)
                if not (color.red() > 240 and color.blue() > 240 and color.green() < 15):
                    raise RuntimeError(f'Owned window capture pixels differ: {color.name()}')
                if status['window_move']['available']:
                    moved[0] = move_and_restore_owned_window(widget, backend)
            except Exception as error:
                errors.append(str(error))
            finally:
                app.exit(0)

    capture.failed.connect(lambda error: (errors.append(error), app.quit()))
    timer.timeout.connect(check_frame)
    QTimer.singleShot(300, lambda: capture.start(QRect(widget.mapToGlobal(widget.rect().topLeft()), widget.size())))
    QTimer.singleShot(8000, lambda: (errors.append('Native frame timed out'), app.quit()))
    timer.start()
    try:
        app.exec()
        if errors or not frames:
            raise RuntimeError(errors or 'No frame delivered')
        print(json.dumps({'status': 'passed', 'screen_pixels': True, 'own_window_move': moved[0],
                          'capabilities': status}))
    finally:
        timer.stop()
        capture.stop()
        widget.close()


if __name__ == '__main__':
    main()
