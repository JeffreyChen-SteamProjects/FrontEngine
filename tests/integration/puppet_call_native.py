"""Native GL call/light/ball probe with a synthetic area outside all screens.

Uses real Qt timers and window movement. The work-area provider alone is
substituted to keep every test window off the user's desktop. Launch via
pythonw with an absolute output path and the Windows Qt platform.
"""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
import traceback

from PySide6.QtCore import QRect, QTimer, Qt
from PySide6.QtWidgets import QApplication

from puppet_photo_native import fixture


def require(condition, message: str) -> None:
    """Fail the probe with a recorded reason; unlike assert it survives -O and is not an AssertionError."""
    if not condition:
        raise RuntimeError(message)


def main():
    from frontengine.show.pet.puppet_pet import PuppetPetWidget
    from frontengine.user_setting.pet_profiles import PetProfiles

    output = Path(sys.argv[1]).resolve()
    activity = sys.argv[2] if len(sys.argv) > 2 else 'call'
    require(activity in ('call', 'light', 'ball'), "activity in ('call', 'light', 'ball')")
    arrival_action, reward = {'call': ('greet', 1), 'light': ('play', 3), 'ball': (None, 1)}[activity]
    output.mkdir(parents=True, exist_ok=True)
    ctypes.windll.kernel32.SetErrorMode(3)
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    require(app.platformName() == 'windows', "app.platformName() == 'windows'")
    fixture(output / 'fixture.puppet')
    script_path = output / 'fixture.petscript.json'
    script_path.write_text(json.dumps({
        'version': 1, 'frontengine_actions': {'walk': {'expression': 'care'}}}), encoding='utf-8')
    pet = PuppetPetWidget(output / 'fixture.puppet', size=(128, 128),
                          script_path=str(script_path), profiles=PetProfiles({}, lambda: None))
    pet.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
    pet.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    pet.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    right = max(screen.geometry().right() for screen in app.screens())
    area = QRect(right + 2048, 0, 800, 600)
    pet.move(area.x() + 160, area.y() + 200)
    pet._target._geometry = lambda: (area.x(), area.y(), area.width(), area.height(), pet.width(), pet.height())
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    observations, handles = [], set()
    result = {'status': 'failed', 'platform': app.platformName(), 'activity': activity, 'synthetic_work_area': True,
              'fixture_only': True, 'helper_show_without_focus': True, 'native_gl': False}
    state = {'phase': 'warm', 'finished': False, 'moving_frame': False, 'saw_arrival_action': False}
    start = (lambda **_kwargs: pet.start_ball()) if activity == 'ball' else getattr(pet, 'start_' + activity)
    phases = set()

    def observe():
        point = wintypes.POINT()
        require(user32.GetCursorPos(ctypes.byref(point)), 'user32.GetCursorPos(ctypes.byref(point))')
        foreground = int(user32.GetForegroundWindow() or 0)
        observations.append({'foreground': foreground, 'cursor': [point.x, point.y],
                             'position': [pet.x(), pet.y()], 'phase': state['phase']})
        require(foreground not in handles, 'A probe window became foreground')
        for window in (pet, pet._target.marker):
            if window is None:
                continue
            require(all(not window.frameGeometry().intersects(screen.geometry()) for screen in app.screens()), 'all(not window.frameGeometry().intersects(screen.geometry()) for screen in app.screens())')
            require(area.contains(window.geometry()), 'Window left the synthetic work area')

    def finish(error=None):
        if state['finished']:
            return
        state['finished'] = True
        poll.stop()
        deadline.stop()
        if error:
            result.update(error=repr(error), traceback=traceback.format_exc())
        else:
            result['status'] = 'passed'
        pet.close()
        result['observations'] = observations
        result['handles'] = sorted(handles)
        (output / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        app.quit()

    def begin():
        try:
            require(pet.canvas.isValid(), 'pet.canvas.isValid()')
            result['native_gl'] = True
            state['baseline'] = pet.photo_image()
            require(state['baseline'].pixelColor(64, 64).alpha() == 128, "state['baseline'].pixelColor(64, 64).alpha() == 128")
            require(state['baseline'].save(str(output / 'baseline.png')), "state['baseline'].save(str(output / 'baseline.png'))")
            state['before'] = pet.profile_session.state()
            state['start'] = (pet.x(), pet.y())
            require(start(offset=(160, 60)) == 'accepted', "start(offset=(160, 60)) == 'accepted'")
            marker = pet._target.marker
            handles.add(int(marker.winId()))
            state['target'] = marker.origin if activity == 'ball' else marker.target
            state['phase'] = 'moving'
            observe()
        except Exception as error:
            finish(error)

    def check():
        try:
            observe()
            if state['phase'] == 'warm':
                return
            if arrival_action is not None and pet.profile_session.companion.action == arrival_action:
                state['saw_arrival_action'] = True
            if pet._target.marker is not None:
                if activity == 'ball':
                    phases.add(pet._target.marker.phase)
                if (pet.x(), pet.y()) != state['start'] and not state['moving_frame']:
                    moving = pet.photo_image()
                    alpha = moving.pixelColor(64, 64).alpha()
                    require(60 <= alpha <= 68, f'Walk binding not rendered: {alpha}')
                    require(moving.save(str(output / 'walking.png')), "moving.save(str(output / 'walking.png'))")
                    state['moving_frame'] = True
                    result['walk_alpha'] = alpha
                return
            require(not pet._target.timer.isActive(), 'not pet._target.timer.isActive()')
            require(state['moving_frame'], 'No rendered frame during actual movement')
            require(pet.photo_image() == state['baseline'], 'Walk binding did not release at arrival')
            cx, cy = pet.center()
            tx, ty = state['target']
            require((cx - tx) ** 2 + (cy - ty) ** 2 <= 4, '(cx - tx) ** 2 + (cy - ty) ** 2 <= 4')
            if pet.profile_session.companion.growth.affection == 0:
                return
            require('return' in phases if activity == 'ball' else state['saw_arrival_action'], "'return' in phases if activity == 'ball' else state['saw_arrival_action']")
            require(pet.profile_session.companion.growth.affection == reward, 'pet.profile_session.companion.growth.affection == reward')
            require(pet.profile_session.companion.action is None, 'pet.profile_session.companion.action is None')
            require(pet.photo_image().save(str(output / 'arrived.png')), "pet.photo_image().save(str(output / 'arrived.png'))")
            after = pet.profile_session.state()
            for key in ('id', 'name', 'appearance', 'preferences'):
                require(after[key] == state['before'][key], "after[key] == state['before'][key]")
            pet._choose_expression('care', True)
            manual = pet.photo_image()
            require(start(offset=(-120, 0)) == 'accepted', "start(offset=(-120, 0)) == 'accepted'")
            handles.add(int(pet._target.marker.winId()))
            pet.profile_session.set_mode('work')
            require(pet._target.marker is None and not pet._target.timer.isActive(), 'pet._target.marker is None and not pet._target.timer.isActive()')
            require(pet.canvas.active_expressions() == ['care'], "pet.canvas.active_expressions() == ['care']")
            require(pet.photo_image() == manual, 'Cancellation removed a manual expression')
            require(pet.profile_session.companion.growth.affection == reward, 'pet.profile_session.companion.growth.affection == reward')
            pet._choose_expression('care', False)
            require(pet.photo_image() == state['baseline'], "pet.photo_image() == state['baseline']")
            result.update(start=state['start'], end=[pet.x(), pet.y()], target=state['target'],
                          arrival_action_completed=arrival_action or 'ball_return', ball_phases=sorted(phases),
                          timer_stopped=True, manual_expression_preserved=True,
                          reward=reward, pixels_restored=True)
            observe()
            finish()
        except Exception as error:
            finish(error)

    poll, deadline = QTimer(), QTimer()
    poll.timeout.connect(check)
    deadline.setSingleShot(True)
    deadline.timeout.connect(lambda: finish(TimeoutError('Native call did not complete within 15 seconds')))
    observe()
    pet.show()
    handles.add(int(pet.winId()))
    poll.start(50)
    deadline.start(15000)
    QTimer.singleShot(1500, begin)
    app.exec()
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
