"""Real-screen acceptance for built-in pets: toys, calls and petting strokes, isolated from the user.

Run with an absolute output directory. The probe re-launches itself on a hidden
Win32 desktop (see hidden_desktop.py). There it uses the real primary monitor's
work area, real OpenGL and the real built-in assets: the INKSIDE MOCHI Puppet
model and a dressed layered MOCHI sprite. Nothing is substituted in the pets'
geometry. Petting strokes are real WM_LBUTTONDOWN / WM_MOUSEMOVE / WM_LBUTTONUP
messages. A hidden desktop has no physical pointer, so Windows still reports the
pointer as having left the window; the probe holds back only those Leave events
(and reports how many) to stand in for a hand resting on the pet. Every move,
press and release still arrives through Qt's Windows message path.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
import tempfile
import traceback

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON = 0x0200, 0x0201, 0x0202, 0x0001
user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
STROKE = (20, 50, 80, 110, 80, 50, 20, 50, 80, 110, 80, 50, 20, 50, 80, 110, 80, 50, 20)


def _mouse(hwnd: int, message: int, x: int, y: int, buttons: int) -> None:
    user32.PostMessageW(hwnd, message, buttons, (y << 16) | (x & 0xFFFF))


class Steps:
    """Run generator steps on the Qt event loop; each yield is a wait in milliseconds."""

    def __init__(self, app, steps, finish) -> None:
        self.app, self.steps, self.finish, self.current = app, list(steps), finish, None
        self.progress = []

    def start(self) -> None:
        QTimer.singleShot(0, self._advance)

    def _advance(self) -> None:
        try:
            if self.current is None:
                if not self.steps:
                    self.finish()
                    return
                step = self.steps.pop(0)
                print('step', step.__name__, file=sys.stderr)
                self.current = step()
            QTimer.singleShot(next(self.current), self._advance)
        except StopIteration:
            self.current = None
            QTimer.singleShot(0, self._advance)
        except Exception as error:  # every failure is reported in result.json
            self.finish(error)


def _rect(rect) -> list:
    return [rect.x(), rect.y(), rect.width(), rect.height()]


def _physical_size(hwnd: int) -> tuple:
    rect = wintypes.RECT()
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.right - rect.left, rect.bottom - rect.top


def _inside(window, area) -> bool:
    return area.contains(window.geometry())


def _wait_until(condition, check, limit_ms: int):
    """Yield 50 ms waits until condition() holds, calling check() each time."""
    for index in range(limit_ms // 50):
        check()
        if condition():
            return
        if index % 40 == 0:
            print('waiting', index * 50, 'ms', file=sys.stderr)
        yield 50
    raise TimeoutError('Condition not reached in time')


class Probe:
    def __init__(self, app, output: Path, folder: Path) -> None:
        self.app, self.output, self.folder = app, output, folder
        self.screen = app.primaryScreen()
        self.area = self.screen.availableGeometry()
        self.result = {'status': 'failed', 'platform': app.platformName(),
                       'work_area': [self.area.x(), self.area.y(), self.area.width(), self.area.height()],
                       'device_pixel_ratio': self.screen.devicePixelRatio(), 'synthetic_work_area': False}
        self.pets = []

    def perch_edges(self):
        """Real EnumWindows/GetWindowRect edges come back in Qt's logical coordinates on every monitor."""
        from PySide6.QtWidgets import QWidget
        from frontengine.show.pet.desktop_pet import windows_platforms
        self.result['screens'] = [[screen.name(), screen.devicePixelRatio(), _rect(screen.availableGeometry())]
                                  for screen in self.app.screens()]
        edges = {}
        for screen in self.app.screens():
            area = screen.availableGeometry()
            window = QWidget()
            window.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
            window.show()
            window.setGeometry(area.left() + 300, area.top() + 200, 500, 300)
            yield 400
            assert window.screen().name() == screen.name(), (window.screen().name(), window.geometry())
            expected = (window.x(), window.x() + window.width(), window.y())
            found = windows_platforms()
            match = min(found, key=lambda edge: sum(abs(a - b) for a, b in zip(edge, expected)))
            window.close()
            assert all(abs(a - b) <= 1 for a, b in zip(match, expected)), (screen.name(), match, expected)
            edges[screen.name()] = {'logical_window': list(expected), 'converted_edge': list(match)}
        self.result['perch_edges'] = edges

    def cross_monitor(self):
        """Move both pet kinds between the real monitors; sizes, bounds and calls follow each screen."""
        from frontengine.show.pet.recovery import recover_pet
        screens = self.app.screens()
        if len(screens) < 2:
            self.result['cross_monitor'] = 'single screen'
            return
        report = {}
        for pet in self.pets:
            kind = type(pet).__name__
            for screen in (screens[1], screens[0], screens[1]):
                area = screen.availableGeometry()
                recover_pet(pet, screen)
                yield 400
                physical = _physical_size(int(pet.winId()))
                ratio = screen.devicePixelRatio()
                assert pet.screen().name() == screen.name(), (kind, pet.screen().name(), screen.name())
                assert _inside(pet, area), (kind, pet.geometry(), area)
                assert abs(physical[0] - round(pet.width() * ratio)) <= 2, (kind, physical, pet.width(), ratio)
                if hasattr(pet, '_toy'):
                    gained_before = pet.profile_session.companion.growth.affection
                    pet.profile_session.advance(60)  # clear the ball reward cooldown
                    assert pet.start_ball() == 'accepted'

                    def contained(pet=pet, area=area):
                        assert _inside(pet, area), (kind, 'ball', pet.geometry(), area)
                    yield from _wait_until(lambda pet=pet: pet._toy is None
                                           and pet.profile_session.companion.action is None, contained, 25000)
                    report.setdefault(kind, []).append({'screen': screen.name(), 'ratio': ratio,
                                                        'physical_size': physical,
                                                        'ball_reward': pet.profile_session.companion.growth.affection
                                                        - gained_before})
                if hasattr(pet, '_target'):
                    pet.profile_session.advance(60)
                    assert pet.start_call(offset=(5000, 5000)) == 'accepted'
                    assert _inside(pet._target.marker, area), 'call target left its monitor'

                    def stays(pet=pet, area=area):
                        assert _inside(pet, area), (kind, 'call', pet.geometry(), area)
                    yield from _wait_until(lambda pet=pet: pet._target.marker is None, stays, 20000)
                    report.setdefault(kind, []).append({'screen': screen.name(), 'ratio': ratio,
                                                        'physical_size': physical, 'arrived': [pet.x(), pet.y()]})
        self.result['cross_monitor'] = report

    def puppet_toys(self):
        from frontengine.show.pet.inkside.puppet_export import export_puppet
        from frontengine.show.pet.puppet_pet import PuppetPetWidget
        from frontengine.user_setting.pet_profiles import PetProfiles
        print('exporting', file=sys.stderr)
        model, script = export_puppet('inkside-mochi', self.folder / 'puppets')
        print('exported', file=sys.stderr)
        pet = PuppetPetWidget(model, size=(192, 192), script_path=str(script), profiles=PetProfiles({}, lambda: None))
        self.pets.append(pet)
        print('created', file=sys.stderr)
        pet.move(self.area.left() + 40, self.area.bottom() - pet.height() - 20)
        pet.show()
        print('show returned', file=sys.stderr)
        yield 800
        print('puppet shown', pet.geometry(), pet.canvas.isValid(), file=sys.stderr)
        assert pet.canvas.isValid(), 'Native OpenGL context is invalid on the real screen'
        results = {}
        for activity, offset, gained in (('call', (260, -40), 1), ('light', (-180, 0), 3), ('ball', None, 1)):
            before = pet.profile_session.companion.growth.affection
            start = getattr(pet, 'start_' + activity)
            print('start', activity, file=sys.stderr)
            assert (start() if offset is None else start(offset=offset)) == 'accepted', activity
            print('marker', pet._target.marker is not None, pet._target.timer.isActive(), file=sys.stderr)

            def contained(pet=pet):
                assert _inside(pet, self.area), 'Puppet left the real work area'
                if pet._target.marker is not None:
                    assert _inside(pet._target.marker, self.area), 'Target left the real work area'
            yield from _wait_until(lambda: pet._target.marker is None and pet.profile_session.companion.action is None,
                                   contained, 20000)
            pet.profile_session.advance(4)
            assert pet.profile_session.companion.growth.affection - before == gained, activity
            assert not pet._target.timer.isActive()
            results[activity] = {'affection_gained': gained, 'end': [pet.x(), pet.y()]}
            yield 300
        self.result['puppet_toys'] = results

    def sprite_toys(self):
        from frontengine.show.pet.asset_library import PetAssetLibrary
        from frontengine.show.pet.desktop_pet import DesktopPetWidget
        from frontengine.show.pet.inkside.library import install_builtin
        from frontengine.show.pet.wardrobe import WardrobeDraft
        from frontengine.user_setting.pet_profiles import PetProfiles
        library = PetAssetLibrary(self.folder / 'library')
        install_builtin(library, 'inkside-mochi')
        image = QImage(64, 64, QImage.Format.Format_ARGB32)
        image.fill(QColor(240, 96, 42))
        image.save(str(self.folder / 'pet.png'))
        pet = DesktopPetWidget(str(self.folder / 'pet.png'), size=160, profiles=PetProfiles({}, lambda: None),
                               talk=False, sit_on_windows=False, asset_library=library)
        self.pets.append(pet)
        draft = WardrobeDraft(pet.profile_session.profiles, pet.profile_session.identifier, library.scan()[0])
        draft.choose_character({'id': 'inkside-mochi', 'version': '1'})
        for piece in ('work-cap', 'work-jacket'):
            draft.equip({'id': f'inkside-mochi-{piece}', 'version': '1'})
        draft.apply()
        assert pet._layered_playback.renderer is not None, 'Layered outfit was not adopted'
        pet.set_pet_window_flag()  # as PetSettingUI does when it spawns a sprite pet
        pet.move(self.area.left() + 300, self.area.bottom() - pet.height())
        pet.show()
        pet.start_moving((self.area.left(), self.area.top(), self.area.right(), self.area.bottom()))
        yield 800
        results = {}
        for activity, gained in (('ball', 1), ('light', 3)):
            before = pet.profile_session.companion.growth.affection
            assert (pet.start_ball() if activity == 'ball' else pet.start_light(offset=(-200, 0))) == 'accepted'

            def contained(pet=pet):
                assert _inside(pet, self.area), (f'Sprite left the real work area: {pet.geometry()} in {self.area}, '
                                                 f'motion {pet.motion.x:.1f},{pet.motion.y:.1f} bounds {pet.motion.bounds} '
                                                 f'state {pet.motion.state} airborne {pet.motion._airborne}')
            yield from _wait_until(lambda: pet._toy is None and pet.profile_session.companion.action is None,
                                   contained, 25000)
            pet.profile_session.advance(4)
            assert pet.profile_session.companion.growth.affection - before == gained, activity
            results[activity] = {'affection_gained': gained}
            yield 300
        frame = pet.photo_image()
        assert frame.save(str(self.output / 'sprite-outfit.png'))
        self.result['sprite_toys'] = results

    def strokes(self):
        for pet in self.pets:
            kind = type(pet).__name__
            before = pet.profile_session.companion.growth.affection
            pet.stop_toy()
            assert pet._request_interaction('pet') == 'accepted', kind
            hwnd = int(pet.winId())
            y = pet.height() // 2
            from PySide6.QtCore import QEvent, QObject
            seen = {}

            class Count(QObject):
                """Count what arrives; hold back Leave, which only exists because no pointer is present."""
                def eventFilter(self, obj, event):
                    name = event.type().name
                    if name in ('MouseMove', 'MouseButtonPress', 'MouseButtonRelease', 'Leave', 'Enter'):
                        seen[f'{type(obj).__name__}.{name}'] = seen.get(f'{type(obj).__name__}.{name}', 0) + 1
                    return event.type() == QEvent.Type.Leave
            counter = Count()
            for target in (pet, getattr(pet, 'canvas', pet)):
                target.installEventFilter(counter)
            _mouse(hwnd, WM_LBUTTONDOWN, STROKE[0], y, MK_LBUTTON)
            yield 60
            for x in STROKE:
                _mouse(hwnd, WM_MOUSEMOVE, x, y, MK_LBUTTON)
                yield 30
            _mouse(hwnd, WM_LBUTTONUP, STROKE[-1], y, 0)
            yield 120
            self.result.setdefault('stroke_events', {})[kind] = dict(seen)
            self.result.setdefault('stroke_petting_armed', {})[kind] = pet._petting is not None
            for target in (pet, getattr(pet, 'canvas', pet)):
                target.removeEventFilter(counter)
            assert pet.profile_session.companion.action == 'pet', f'{kind}: strokes did not start petting'
            pet.profile_session.advance(3)
            gained = pet.profile_session.companion.growth.affection - before
            assert gained > 0, f'{kind}: completed petting gave no affection'
            self.result.setdefault('strokes', {})[kind] = {'affection_gained': gained}
            yield 200

    def drag_across(self):
        """Drag each pet with real mouse messages from the 100% monitor onto the 125% one."""
        from frontengine.show.pet.recovery import recover_pet
        screens = self.app.screens()
        if len(screens) < 2:
            return
        source, target = screens[0], screens[1]
        report = {}
        for pet in self.pets:
            kind = type(pet).__name__
            pet.stop_toy()
            recover_pet(pet, source)
            yield 400
            pet.profile_session.request('cancel')
            area = source.availableGeometry()
            pet.move(area.right() - pet.width() - 20, area.bottom() - pet.height() - 40)
            if hasattr(pet, 'motion'):
                pet.motion.x, pet.motion.y = float(pet.x()), float(pet.y())
            yield 300
            hwnd, x, y = int(pet.winId()), pet.width() // 2, pet.height() // 2
            _mouse(hwnd, WM_LBUTTONDOWN, x, y, MK_LBUTTON)
            yield 80
            steps = 0
            while pet.screen().name() != target.name() and steps < 60:
                _mouse(hwnd, WM_MOUSEMOVE, x + 30, y, MK_LBUTTON)
                steps += 1
                yield 40
            for _ in range(8):  # a little further so the pet is well inside the new monitor
                _mouse(hwnd, WM_MOUSEMOVE, x + 30, y, MK_LBUTTON)
                yield 40
            _mouse(hwnd, WM_LBUTTONUP, x + 30, y, 0)
            yield 1500
            new_area = target.availableGeometry()
            size = (pet.pet_size, pet.pet_size) if hasattr(pet, 'pet_size') else pet._logical_size()
            assert pet.screen().name() == target.name(), (kind, pet.screen().name())
            assert (pet.width(), pet.height()) == tuple(size), (kind, pet.size(), size)
            assert _inside(pet, new_area), (kind, pet.geometry(), new_area)
            report[kind] = {'screen': pet.screen().name(), 'logical_size': [pet.width(), pet.height()],
                            'physical_size': list(_physical_size(hwnd)), 'drag_steps': steps}
        self.result['drag_across'] = report

    def finish(self, error=None) -> None:
        if self.result.get('finished'):
            return
        self.result['finished'] = True
        if error is not None:
            self.result.update(error=repr(error), traceback=traceback.format_exc())
        else:
            self.result['status'] = 'passed'
        for pet in self.pets:
            pet.close()
        (self.output / 'result.json').write_text(json.dumps(self.result, indent=2), encoding='utf-8')
        self.app.quit()


def main() -> int:
    from hidden_desktop import is_child, run_on_hidden_desktop
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if not is_child(output):
        return run_on_hidden_desktop(__file__, str(output))
    from PySide6.QtGui import QSurfaceFormat
    # A hidden desktop is never presented, so a vsync-waiting buffer swap would stall
    # the event loop; the probe renders without waiting for a refresh.
    surface = QSurfaceFormat.defaultFormat()
    surface.setSwapInterval(0)
    QSurfaceFormat.setDefaultFormat(surface)
    import faulthandler
    faulthandler.dump_traceback_later(25, repeat=False, file=sys.stderr)
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    if app.platformName() != 'windows':
        raise RuntimeError('This probe requires the native Windows Qt platform')
    with tempfile.TemporaryDirectory(prefix='frontengine-real-desktop-') as folder:
        probe = Probe(app, output, Path(folder))
        runner = Steps(app, (probe.perch_edges, probe.puppet_toys, probe.sprite_toys, probe.strokes,
                             probe.cross_monitor, probe.drag_across), probe.finish)
        runner.start()  # the runner must stay referenced while its timers are pending
        QTimer.singleShot(280000, lambda: probe.finish(TimeoutError('Probe did not finish within 280 seconds')))
        app.exec()
    return 0 if probe.result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
