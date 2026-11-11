"""Run image overlays across real monitors on an isolated Windows desktop.

Usage: python tests/integration/overlay_mixed_dpi_native.py OUTPUT_DIR
No desktop input is sent. Each backend crosses every screen and returns to the first.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hidden_desktop import is_child, run_on_hidden_desktop


def run(output: Path) -> dict:
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtGui import QColor, QImage
    from PySide6.QtWidgets import QApplication, QCheckBox

    from frontengine.show.image.paint_image import ImageWidget
    from frontengine.ui.page.utils import show_on_selected_monitor
    from frontengine.user_setting.user_setting_file import user_setting_dict

    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    screens = app.screens()
    if len({screen.devicePixelRatio() for screen in screens}) < 2:
        return {'passed': False, 'blocked': 'Acceptance needs two real screens with different DPI scales',
                'screens': [{'name': screen.name(), 'dpr': screen.devicePixelRatio(),
                             'geometry': screen.geometry().getRect()} for screen in screens]}
    names = [screen.name() for screen in screens]
    source = QImage(320, 180, QImage.Format.Format_ARGB32)
    source.fill(QColor('#ef602a'))
    source.save('source.png')
    observations = []
    for backend in ('software', 'gpu'):
        user_setting_dict['render_backend'] = backend
        widget = ImageWidget('source.png')
        widget.set_ui_window_flag()
        widget.set_ui_variable(1)
        try:
            show_on_selected_monitor(widget, QCheckBox(), app.screens()[0])
            for index, name in enumerate([*names, names[0]]):
                screen = next(screen for screen in app.screens() if screen.name() == name)
                widget.move(screen.availableGeometry().center() - widget.rect().center())
                loop = QEventLoop()
                QTimer.singleShot(700, loop.quit)
                loop.exec()
                picture = widget.grab().toImage()
                picture.save(str(output / f'{backend}-{index}.png'))
                ratio = screen.devicePixelRatio()
                center = picture.pixelColor(picture.width() // 2, picture.height() // 2)
                row = {
                    'requested_backend': backend, 'actual_backend': widget.render_backend,
                    'target': screen.name(), 'screen': widget.screen().name(), 'dpr': ratio,
                    'geometry': widget.geometry().getRect(), 'pixels': [picture.width(), picture.height()],
                    'center': center.name(),
                    'on_screen': screen.availableGeometry().contains(widget.geometry()),
                }
                row['passed'] = (row['screen'] == row['target'] and row['on_screen']
                                 and widget.size() == source.size()
                                 and row['pixels'] == [round(320 * ratio), round(180 * ratio)]
                                 and center == QColor('#ef602a') and row['actual_backend'] == backend)
                observations.append(row)
        finally:
            widget.close()
            app.processEvents()
    return {'observations': observations, 'passed': all(row['passed'] for row in observations)}


def main() -> int:
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if not is_child(output):
        return run_on_hidden_desktop(__file__, str(output))
    with tempfile.TemporaryDirectory(prefix='fe-overlay-dpi-') as temporary:
        previous = Path.cwd()
        os.chdir(temporary)
        try:
            result = run(output)
        except Exception:
            result = {'passed': False, 'error': traceback.format_exc()}
        finally:
            os.chdir(previous)
    (output / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
