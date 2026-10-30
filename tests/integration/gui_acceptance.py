"""Drive the real FrontEngine main window on an isolated desktop and record what breaks.

Usage (Windows, from the repository root)::

    py tests/integration/gui_acceptance.py OUTPUT_DIR

OUTPUT_DIR receives result.json (every step, its return value or traceback, the
windows it opened or closed, and every exception, Qt critical message, logged
warning or auto-dismissed dialog), a screenshot of each page and stderr.txt.

Visits every page, runs each page's main features with fixture files, closes everything
through the Control Center and shuts the window down. Runs in a temporary working
directory, so the user's settings are untouched; modal dialogs are auto-dismissed and
recorded. Features with effects outside the app (registry, clipboard, media keys, real
windows, network, global keystroke capture, manual region selection) are not exercised.
"""
import json
import logging
import os
import sys
import tempfile
import traceback
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hidden_desktop import is_child, run_on_hidden_desktop  # noqa: E402

OUTPUT = Path(sys.argv[1]).resolve()
OUTPUT.mkdir(parents=True, exist_ok=True)
if not is_child(OUTPUT):
    raise SystemExit(run_on_hidden_desktop(__file__, str(OUTPUT)))

WORK = Path(tempfile.mkdtemp(prefix='fe-gui-acceptance-'))
os.chdir(WORK)
from PySide6.QtCore import QThreadPool, QTimer, QtMsgType, qInstallMessageHandler  # noqa: E402
from PySide6.QtGui import QColor, QImage, QSurfaceFormat  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox  # noqa: E402

surface = QSurfaceFormat.defaultFormat()
surface.setSwapInterval(0)
QSurfaceFormat.setDefaultFormat(surface)
app = QApplication(sys.argv)

# --- error capture ----------------------------------------------------------
events, current = [], {'step': 'startup'}


def record(kind, text):
    events.append({'step': current['step'], 'kind': kind, 'text': str(text)[:1500]})


sys.excepthook = lambda kind, value, tb: record('exception', ''.join(traceback.format_exception(kind, value, tb)))


def qt_messages(mode, _context, message):
    if mode in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
        record('qt-critical', message)
    elif mode == QtMsgType.QtWarningMsg:
        record('qt-warning', message)


qInstallMessageHandler(qt_messages)


class LogTrap(logging.Handler):
    def emit(self, entry):
        if entry.levelno >= logging.WARNING:
            record('log-' + entry.levelname.lower(), entry.getMessage())


# --- fixtures -----------------------------------------------------------------
fixtures = WORK / 'fixtures'
fixtures.mkdir()
image = QImage(320, 200, QImage.Format.Format_ARGB32)
image.fill(QColor('#3a7bd5'))
image.save(str(fixtures / 'picture.png'))
for index in range(2):
    image.fill(QColor(['#d53a3a', '#3ad57b'][index]))
    (fixtures / 'wallpapers').mkdir(exist_ok=True)
    image.save(str(fixtures / 'wallpapers' / f'wall{index}.png'))
gif_path = fixtures / 'moving.gif'
try:
    from PIL import Image as PILImage
    frames = [PILImage.new('RGB', (120, 80), colour) for colour in ('red', 'green', 'blue')]
    frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=120, loop=0)
except ImportError:
    gif_path = None
with wave.open(str(fixtures / 'quiet.wav'), 'wb') as sound:
    sound.setnchannels(1)
    sound.setsampwidth(2)
    sound.setframerate(8000)
    sound.writeframes(b'\0\0' * 8000)
(fixtures / 'page.html').write_text('<html><body style="background:#eee"><h1>FrontEngine GUI check</h1></body></html>',
                                    encoding='utf-8')
VIDEO = REPO / 'exe' / 'daisy bell.mp4'

# --- dialogs never block ------------------------------------------------------
QMessageBox.exec = lambda self, *a: record('dialog', f'QMessageBox: {self.text()}') or 0
for name in ('information', 'warning', 'critical', 'question'):
    setattr(QMessageBox, name, staticmethod(lambda *a, _n=name, **k: record('dialog', f'QMessageBox.{_n}: {a[2] if len(a) > 2 else ""}') or QMessageBox.StandardButton.No))
QDialog.exec = lambda self, *a: record('dialog', f'{type(self).__name__}.exec') or 0
QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: str(fixtures / 'wallpapers'))
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ('', ''))

from frontengine.utils.logging.loggin_instance import front_engine_logger  # noqa: E402
front_engine_logger.addHandler(LogTrap())
from frontengine.ui.main_ui import FrontEngineMainUI  # noqa: E402
import frontengine.ui.page.image.image_setting_ui as image_page  # noqa: E402
import frontengine.ui.page.gif.gif_setting_ui as gif_page  # noqa: E402
import frontengine.ui.page.video.video_setting_ui as video_page  # noqa: E402
import frontengine.ui.page.particle.particle_setting_ui as particle_page  # noqa: E402
import frontengine.ui.page.pet.pet_setting_ui as pet_page  # noqa: E402
import frontengine.ui.page.sound_player.sound_player_setting_ui as sound_page  # noqa: E402

image_page.choose_image = lambda *a, **k: str(fixtures / 'picture.png')
particle_page.choose_image = image_page.choose_image
gif_page.choose_gif = lambda *a, **k: str(gif_path) if gif_path else ''
video_page.choose_video = lambda *a, **k: str(VIDEO)
sound_page.choose_wav_sound = lambda *a, **k: str(fixtures / 'quiet.wav')
pet_page.choose_pet = lambda *a, **k: str(fixtures / 'picture.png')

window = FrontEngineMainUI(main_app=app, debug=False, show_system_tray_ray=False)
window.show()
results = []


def overlays():
    return [w for w in app.topLevelWidgets() if w.isVisible() and w is not window]


def screenshot(name):
    window.grab().save(str(OUTPUT / f'{name}.png'))


def page_steps():
    steps = []
    for index in range(window.page_stack.count()):
        def visit(index=index):
            window.sidebar.select_page(index)
            app.processEvents()
            widget = window.page_stack.currentWidget()
            assert window.page_stack.currentIndex() == index, 'page did not switch'
            screenshot(f'page-{index:02d}-{type(widget).__name__}')
            return type(widget).__name__
        steps.append((f'visit page {index}', visit, None))
    return steps


def pet_builtin():
    page = window.pet_setting_ui
    page.use_builtin_character()
    QThreadPool.globalInstance().waitForDone(180000)
    app.processEvents()
    assert page.ready_to_play, 'built-in character did not become ready'
    page.start_play_pet()
    return type(page.pet_list[-1]).__name__


def pet_moved():
    pet = window.pet_setting_ui.pet_list[-1]
    return {'x': pet.x(), 'mode': pet.motion.mode, 'state': pet.motion.state}


def command_search(text):
    W.open_command_palette()
    palette = W.command_palette
    palette.search_input.setText(text)
    palette.refresh()
    assert palette.results.count() > 0, 'no command matched'
    palette.results.setCurrentRow(0)
    first = palette.results.currentItem().text()
    palette.execute_selected()
    app.processEvents()
    palette.close()
    return {'first_result': first, 'page_now': type(W.page_stack.currentWidget()).__name__}


def presets_round_trip():
    from frontengine.ui.menu.preset_menu import _collect_state, apply_state_transaction
    state = _collect_state(W)
    apply_state_transaction(W, state)
    assert _collect_state(W) == state, 're-applying a preset changed the settings'
    return sorted(state)[:6]


def languages():
    from frontengine.ui.menu.language_menu import set_language
    from frontengine.utils.multi_language.language_wrapper import language_wrapper
    start = language_wrapper.language
    switched = {name: set_language(name, W) for name in language_wrapper.choose_language_dict}
    W.sidebar.select_page(8)
    screenshot('pet-page-' + language_wrapper.language)
    set_language(start, W)
    assert all(switched.values()), switched
    return {'switched': len(switched), 'back_to': language_wrapper.language}


def scene_template():
    page = W.scene_setting_ui
    page.open_templates()
    dialog = page.templates_dialog
    dialog.list.setCurrentRow(0)
    dialog.apply_template()
    return {'template': dialog.list.currentItem().text(), 'status': dialog.status.text()[:80]}


def scene_applied():
    dialog = W.scene_setting_ui.templates_dialog
    for _ in range(100):
        if dialog.pending is None:
            break
        app.processEvents()
        QThreadPool.globalInstance().waitForDone(100)
    assert dialog.pending is None, 'template never finished applying'
    return {'status': dialog.status.text()[:120], 'dialog_hidden': not dialog.isVisible(),
            'scene_windows': [type(w).__name__ for w in overlays()]}


W = window


def first_monitor(page):
    combo = page.target_monitor_combobox
    combo.setCurrentIndex(combo.findData(0))
    return combo.currentData()


ACTIONS = [
    ('image: choose then start', lambda: (W.image_setting_ui.choose_and_copy_file_to_cwd_image_dir_then_play(),
                                          first_monitor(W.image_setting_ui), W.image_setting_ui.start_play_image()), 1),
    ('gif: choose then start', lambda: (W.gif_setting_ui.choose_and_copy_file_to_cwd_gif_dir_then_play(),
                                        first_monitor(W.gif_setting_ui), W.gif_setting_ui.start_play_gif()), 1),
    ('video (muted): choose then start', lambda: (W.video_setting_ui.volume_slider.setValue(0),
                                                  W.video_setting_ui.choose_and_copy_file_to_cwd_video_dir_then_play(),
                                                  first_monitor(W.video_setting_ui), W.video_setting_ui.start_play_video()), 1),
    ('web: open local page', lambda: (W.web_setting_ui.web_url_input.setText((fixtures / 'page.html').as_uri()),
                                      first_monitor(W.web_setting_ui), W.web_setting_ui.start_open_web_with_url()), 1),
    ('text: draw on screen', lambda: (W.text_setting_ui.line_edit.setText('FrontEngine GUI check'),
                                      first_monitor(W.text_setting_ui), W.text_setting_ui.start_draw_text_on_screen()), 1),
    ('sound (muted): play wav', lambda: (W.sound_player_setting_ui.volume_slider.setValue(0),
                                         W.sound_player_setting_ui.choose_and_copy_wav_file_to_cwd_sound_dir_then_play()), 0),
    ('particle: choose then start', lambda: (W.particle_setting_ui.choose_and_copy_file_to_cwd_image_dir_then_play(),
                                             first_monitor(W.particle_setting_ui), W.particle_setting_ui.start_play_particle()), 1),
    ('pet: picture pet', lambda: (W.pet_setting_ui.choose_and_play(), W.pet_setting_ui.start_play_pet()), 1),
    ('pet: built-in character', pet_builtin, 1),
    ('pet: is moving', pet_moved, 0),
    ('wallpaper: choose folder and show', lambda: (W.wallpaper_setting_ui.choose_folder(),
                                                   W.wallpaper_setting_ui.toggle_wallpaper()), 1),
    ('widgets: spectrum', lambda: W.widgets_setting_ui.toggle_spectrum(), 1),
    ('widgets: system monitor', lambda: W.widgets_setting_ui.toggle_monitor(), 1),
    ('widgets: now playing', lambda: W.widgets_setting_ui.toggle_now_playing(), 1),
    ('widgets: today', lambda: W.widgets_setting_ui.show_today(), 1),
    ('focus: dim', lambda: W.focus_setting_ui.toggle_dim(), 1),
    ('focus: mask', lambda: W.focus_setting_ui.toggle_mask(), 1),
    ('screen care: colour filter', lambda: W.screen_care_setting_ui.toggle_filter(), 1),
    ('screen care: reading ruler', lambda: W.screen_care_setting_ui.toggle_ruler(), 1),
    ('screen care: colour vision', lambda: W.screen_care_setting_ui.toggle_color_vision(), 1),
    ('screen care: break reminder', lambda: W.screen_care_setting_ui.toggle_break_reminder(), 0),
    ('presentation: annotation', lambda: W.presentation_setting_ui.toggle_annotation(), 1),
    ('presentation: annotation off', lambda: W.presentation_setting_ui.toggle_annotation(), -1),
    ('presentation: cursor effects', lambda: W.presentation_setting_ui.toggle_cursor_effects(), 0),
    ('presentation: magnifier', lambda: W.presentation_setting_ui.toggle_magnifier(), 1),
    ('presentation: whiteboard', lambda: W.presentation_setting_ui.toggle_whiteboard(), 1),
    ('tools: measure on', lambda: W.tools_setting_ui.toggle_measure(), 1),
    ('tools: measure off', lambda: W.tools_setting_ui.toggle_measure(), -1),
    ('tools: colour palette', lambda: W.tools_setting_ui.open_palette(), 1),
    ('control center: hide all', lambda: W.control_center_ui.hide_all(), None),
    ('control center: show all', lambda: W.control_center_ui.show_all(), None),
    ('control center: close all', lambda: W.control_center_ui.clear_all(), None),
    ('command search: find and run "pet"', lambda: command_search('pet'), None),
    ('presets: collect and re-apply every page', presets_round_trip, None),
    ('language: switch through all seven and back', languages, None),
    ('scene: apply the first template', scene_template, None),
    ('scene: template applied', scene_applied, None),
    ('control center: close all again', lambda: W.control_center_ui.clear_all(), None),
]


def run(steps):
    if not steps:
        finish()
        return
    name, action, expected = steps[0]
    current['step'] = name
    before_windows = overlays()
    before = len(before_windows)
    entry = {'step': name}
    try:
        entry['returned'] = repr(action())[:200]
    except Exception:
        entry['raised'] = traceback.format_exc()[-1500:]
    def settle():
        app.processEvents()
        after = overlays()
        entry['new_windows'] = len(after) - before
        entry['open_windows'] = len(after)
        from collections import Counter
        names_before, names_after = Counter(type(w).__name__ for w in before_windows), Counter(type(w).__name__ for w in after)
        entry['added'] = sorted((names_after - names_before).elements())
        entry['removed'] = sorted((names_before - names_after).elements())
        if expected is not None and 'raised' not in entry:
            entry['window_ok'] = (len(after) - before >= expected) if expected >= 0 else (len(after) < before)
        results.append(entry)
        if name.startswith('control center: close all'):
            entry['left_open'] = sorted(type(w).__name__ for w in after)
        run(steps[1:])
    QTimer.singleShot(1500, settle)


def finish():
    current['step'] = 'shutdown'
    screenshot('final')
    leftovers = sorted(type(w).__name__ for w in overlays())
    closed = window.close()
    report = {'results': results, 'events': events, 'leftover_before_close': leftovers, 'window_closed': closed}
    (OUTPUT / 'result.json').write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
    QTimer.singleShot(500, app.quit)


QTimer.singleShot(3000, lambda: run(page_steps() + ACTIONS))
app.exec()
