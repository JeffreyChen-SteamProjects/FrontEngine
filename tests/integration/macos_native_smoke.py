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
from frontengine.utils.macos.region_capture import RegionCaptureAdapter


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
    widget = QWidget()
    widget.setWindowTitle('FrontEngine native integration smoke')
    widget.setStyleSheet('background: rgb(255, 0, 255);')
    area = app.primaryScreen().availableGeometry()
    widget.setGeometry(area.x() + 80, area.y() + 80, 96, 64)
    widget.show()
    capture = RegionCaptureAdapter()
    errors, frames = [], []
    timer = QTimer()
    timer.setInterval(30)

    def check_frame():
        image = capture.latest_frame()
        if image is not None and not image.isNull():
            frames.append(image.toImage())
            app.quit()

    capture.failed.connect(lambda error: (errors.append(error), app.quit()))
    timer.timeout.connect(check_frame)
    QTimer.singleShot(300, lambda: capture.start(QRect(widget.mapToGlobal(widget.rect().topLeft()), widget.size())))
    QTimer.singleShot(8000, lambda: (errors.append('Native frame timed out'), app.quit()))
    timer.start()
    try:
        app.exec()
        if errors or not frames:
            raise RuntimeError(errors or 'No frame delivered')
        color = frames[0].pixelColor(48, 32)
        assert color.red() > 240 and color.blue() > 240 and color.green() < 15, color
        moved = False
        if status['window_move']['available']:
            handle = next(handle for handle, title in backend.list_windows() if title == widget.windowTitle())
            original = backend.window_geometry(handle)
            try:
                moved = backend.move_window(handle, original[0] + 10, original[1] + 10, *original[2:])
                assert moved, backend.last_error
            finally:
                if moved:
                    assert backend.move_window(handle, *original), backend.last_error
        print(json.dumps({'status': 'passed', 'screen_pixels': True, 'own_window_move': moved,
                          'capabilities': status}))
    finally:
        timer.stop()
        capture.stop()
        widget.close()


if __name__ == '__main__':
    main()
