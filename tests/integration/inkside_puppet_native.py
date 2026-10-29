"""Windows native GL probe for a built-in INKSIDE character exported as a Puppet model.

Run with an absolute output directory. The probe re-launches itself on a hidden
Win32 desktop (hidden_desktop.py) and places the pet inside the real primary
monitor's work area there, with in-memory profiles, so the user's pets, settings,
screen and foreground are untouched.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
import traceback

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication

# Companion actions and the bound native reaction each should show while it runs.
ACTIONS = (('greet', 'request'), ('pet_motion', 'motion:pet'), ('feed', 'request'), ('groom', 'request'),
           ('play', 'request'), ('celebrate', 'present'), ('sleep_in', 'present'), ('happy', 'expression:happy'),
           ('sleepy', 'expression:sleepy'))


def require(condition, message: str) -> None:
    """Fail the probe with a recorded reason; unlike assert it survives -O and is not an AssertionError."""
    if not condition:
        raise RuntimeError(message)


def _start(pet, name: str, how: str) -> None:
    if how == 'request':
        require(pet.profile_session.request(name) == 'accepted', name)
    elif how == 'present':
        require(pet.profile_session.present(name), name)
    elif how.startswith('motion:'):
        require(pet.play_motion(how.split(':', 1)[1]), how)
    else:
        pet._choose_expression(how.split(':', 1)[1], True)


def _stop(pet, how: str) -> None:
    if how.startswith('expression:'):
        pet._choose_expression(how.split(':', 1)[1], False)
    elif how.startswith('motion:'):
        pet.player.stop()
    pet.profile_session.request('cancel')
    pet.profile_session.advance(5)


def _differs(first, second) -> int:
    changed = 0
    for y in range(0, first.height(), 4):
        for x in range(0, first.width(), 4):
            changed += first.pixelColor(x, y) != second.pixelColor(x, y)
    return changed


def main() -> int:
    from frontengine.show.pet.inkside.puppet_export import export_puppet
    from frontengine.show.pet.puppet_pet import PuppetPetWidget
    from frontengine.user_setting.pet_profiles import PetProfiles

    from hidden_desktop import is_child, run_on_hidden_desktop
    from PySide6.QtGui import QSurfaceFormat
    output = Path(sys.argv[1]).resolve()
    character = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != '--child' else 'inkside-mochi'
    output.mkdir(parents=True, exist_ok=True)
    if not is_child(output):
        return run_on_hidden_desktop(__file__, str(output), character)
    surface = QSurfaceFormat.defaultFormat()
    surface.setSwapInterval(0)  # the hidden desktop is never presented; do not wait for vsync
    QSurfaceFormat.setDefaultFormat(surface)
    app = QApplication([])
    if app.platformName() != 'windows':
        raise RuntimeError('This probe requires the native Windows Qt platform')
    model, script = export_puppet(character, output)
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    observations = []
    pet = PuppetPetWidget(model, size=(256, 256), script_path=str(script), profiles=PetProfiles({}, lambda: None))
    pet.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
    pet.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    pet.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    area = app.primaryScreen().availableGeometry()
    pet.move(area.left() + 80, area.bottom() - pet.height())
    result = {'status': 'failed', 'platform': app.platformName(), 'character': character, 'reactions': {},
              'real_work_area': [area.x(), area.y(), area.width(), area.height()]}
    steps = list(ACTIONS)
    state = {}

    def observe():
        observations.append(int(user32.GetForegroundWindow() or 0))

    def finish(error=None):
        if error is not None:
            result['error'] = repr(error)
            result['traceback'] = traceback.format_exc()
        else:
            require(area.contains(pet.geometry()), 'The pet left the real work area')
            result.update(status='passed', native_gl=True, foreground_samples=len(observations))
        poll.stop()
        pet.close()
        (output / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        app.quit()

    def capture_baseline():
        try:
            require(pet.canvas.isValid(), 'Native OpenGL context is invalid')
            state['baseline'] = pet.photo_image()
            require(state['baseline'].pixelColor(0, 0).alpha() == 0, 'Background is not transparent')
            require(state['baseline'].save(str(output / 'baseline.png'), 'PNG'), "state['baseline'].save(str(output / 'baseline.png'), 'PNG')")
            next_step()
        except Exception as error:  # report every failure in result.json
            finish(error)

    def next_step():
        if not steps:
            finish()
            return
        name, how = steps[0]
        try:
            _start(pet, name, how)
            QTimer.singleShot(350, check_step)
        except Exception as error:
            finish(error)

    def check_step():
        name, how = steps.pop(0)
        try:
            image = pet.photo_image()
            require(image.save(str(output / f'{name}.png'), 'PNG'), "image.save(str(output / f'{name}.png'), 'PNG')")
            changed = _differs(state['baseline'], image)
            # Expressions only swap the eyes, which are tiny on some bodies (GILL).
            require(changed > (8 if how.startswith('expression:') else 20), f'{name} did not change ({changed})')
            _stop(pet, how)
            QTimer.singleShot(900, lambda: confirm(name, changed))
        except Exception as error:
            finish(error)

    def confirm(name, changed):
        try:
            after = pet.photo_image()
            require(after.save(str(output / f'{name}-after.png'), 'PNG'), "after.save(str(output / f'{name}-after.png'), 'PNG')")
            restored = _differs(state['baseline'], after)
            require(restored <= 4, f'{name} did not return to the baseline ({restored} samples differ)')
            result['reactions'][name] = {'changed_samples': changed, 'restored_difference': restored}
            next_step()
        except Exception as error:
            finish(error)

    observe()
    pet.show()
    poll = QTimer()
    poll.timeout.connect(observe)
    poll.start(50)
    QTimer.singleShot(1500, capture_baseline)
    app.exec()
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
