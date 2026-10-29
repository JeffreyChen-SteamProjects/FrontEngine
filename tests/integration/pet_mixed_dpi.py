"""Two screens with different scale factors: pets perch, move, recover and get called correctly.

Run with a working directory that holds the screen layout file named in
QT_QPA_PLATFORM (offscreen:configfile=<relative name>; a drive colon would split the
platform argument). DISPLAY1 is 1920x1080 at 100%; DISPLAY2 sits to its right at
125%. Prints one JSON result line and exits non-zero on failure.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

LAYOUT = {'synchronousWindowSystemEvents': True, 'windowFrameMargins': False, 'screens': [
    {'name': 'DISPLAY1', 'x': 0, 'y': 0, 'width': 1920, 'height': 1080, 'logicalDpi': 96, 'logicalBaseDpi': 96,
     'dpr': 1.0},
    {'name': 'DISPLAY2', 'x': 1920, 'y': 0, 'width': 1536, 'height': 960, 'logicalDpi': 96, 'logicalBaseDpi': 96,
     'dpr': 1.25}]}


def _inside(widget, area) -> bool:
    return area.contains(widget.geometry())


def check_edges(app) -> dict:
    from frontengine.show.pet.desktop_pet import native_edges_to_logical
    physical = [(100, 900, 300, 'DISPLAY1', 0, 0, 1920, 1080),
                (2420, 3420, 500, 'DISPLAY2', 1920, 0, 1920, 1200), (5, 50, 7, 'UNKNOWN', 9000, 0, 10, 10)]
    logical = native_edges_to_logical(physical, app.screens())
    assert logical == [(100, 900, 300), (2320, 3120, 400), (5, 50, 7)], logical
    return {'converted': logical}


def _sprite(folder: Path, profiles):
    from frontengine.show.pet.desktop_pet import DesktopPetWidget
    image = QImage(64, 64, QImage.Format.Format_ARGB32)
    image.fill(QColor(240, 96, 42))
    image.save(str(folder / 'pet.png'))
    pet = DesktopPetWidget(str(folder / 'pet.png'), size=128, profiles=profiles, talk=False, sit_on_windows=False)
    pet.set_pet_window_flag()
    return pet


def check_sprite(app, folder: Path) -> dict:
    from frontengine.show.pet.recovery import recover_pet
    from frontengine.user_setting.pet_profiles import PetProfiles
    first, second = (_screen(app, name) for name in ('DISPLAY1', 'DISPLAY2'))
    pet = _sprite(folder, PetProfiles({}, lambda: None))
    try:
        pet.move(-400, -400)  # lost off every screen
        pet.show()
        recover_pet(pet, second)
        area = second.availableGeometry()
        assert _inside(pet, area) and pet.screen() is second, (pet.geometry(), pet.screen().name())
        assert pet.motion.bounds[0] >= area.left() and pet.motion.bounds[2] <= area.right() + 1, pet.motion.bounds
        # Perch on a window of the 125% screen whose physical top is 500 -> logical 400.
        pet.motion.set_platforms([(2320, 3120, 400)])
        pet.motion.x, pet.motion.y = 2500.0, 100.0
        pet.motion.throw(0, 1)
        for _ in range(400):
            pet._on_tick()
            assert _inside(pet, area), pet.geometry()
            if not pet.motion._airborne:
                break
        assert pet.y() + pet.height() == 400, ('perched at', pet.y() + pet.height())
        perched = pet.y() + pet.height()
        assert pet.start_ball() == 'accepted'
        for _ in range(900):
            pet._on_tick()
            QCoreApplication.processEvents()
            assert _inside(pet, area), ('ball', pet.geometry())
        # Windows rescales a window crossing to another DPI; the pet must put its size back.
        pet.resize(160, 160)
        _wait(100)
        assert (pet.width(), pet.height()) == (128, 128) and _inside(pet, area), pet.geometry()
        recover_pet(pet, first)
        assert _inside(pet, first.availableGeometry()) and pet.screen() is first
        return {'perched_logical_feet': perched, 'recovered_to': [second.name(), first.name()]}
    finally:
        pet.close()


def _wait(ms: int) -> None:
    from PySide6.QtCore import QEventLoop, QTimer
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def _screen(app, name: str):
    # The offscreen platform recreates its QScreen objects when a GL context starts,
    # so screens are looked up by name each time rather than held across calls.
    return next(screen for screen in app.screens() if screen.name() == name)


def check_puppet(app, folder: Path) -> dict:
    from frontengine.show.pet.inkside.puppet_export import export_puppet
    from frontengine.show.pet.puppet_pet import PuppetPetWidget
    from frontengine.show.pet.recovery import recover_pet
    from frontengine.user_setting.pet_profiles import PetProfiles
    model, script = export_puppet('inkside-bolt', folder)
    pet = PuppetPetWidget(model, size=(160, 160), script_path=str(script), profiles=PetProfiles({}, lambda: None))
    results = {}
    try:
        pet.show()
        for name, offset in (('DISPLAY2', (5000, 5000)), ('DISPLAY1', (-5000, -5000))):
            recover_pet(pet, _screen(app, name))  # the product path that moves a pet to another monitor
            QCoreApplication.processEvents()
            area = _screen(app, name).availableGeometry()
            assert pet.screen().name() == name, (name, pet.screen().name(), pet.geometry())
            assert pet.start_call(offset=offset) == 'accepted'
            assert _inside(pet._target.marker, area), 'call target left its screen'
            for _ in range(300):  # the controller's own 33 ms timer drives movement and dwell
                _wait(50)
                assert _inside(pet, area), (name, pet.geometry())
                if pet._target.marker is None:
                    break
            assert pet._target.marker is None, 'Puppet did not arrive'
            pet.profile_session.advance(2)
            pet.resize(200, 200)  # a DPI rescale after crossing monitors
            _wait(100)
            assert (pet.width(), pet.height()) == (160, 160) and _inside(pet, area), pet.geometry()
            results[name] = [pet.x(), pet.y()]
        return {'puppet_arrivals': results}
    finally:
        pet.close()


def check_focus(app, folder: Path) -> dict:
    from frontengine.show.pet.focus_placement import park_companions
    from frontengine.user_setting.pet_profiles import PetProfiles
    area = _screen(app, 'DISPLAY2').availableGeometry()
    pets = [_sprite(folder, PetProfiles({}, lambda: None)) for _ in range(2)]
    try:
        for index, pet in enumerate(pets):
            pet.move(area.x() + 200 + index * 300, area.y() + 200)
            pet.show()
        park_companions(pets)
        assert all(_inside(pet, area) for pet in pets), [pet.geometry() for pet in pets]
        return {'focus_parked': [[pet.x(), pet.y()] for pet in pets]}
    finally:
        for pet in pets:
            pet.close()


def main() -> int:
    app = QApplication([])
    names = [(screen.name(), screen.devicePixelRatio()) for screen in app.screens()]
    result = {'screens': names}
    try:
        assert names == [('DISPLAY1', 1.0), ('DISPLAY2', 1.25)], names
        with tempfile.TemporaryDirectory(prefix='frontengine-mixed-dpi-') as folder:
            for check in (check_edges, lambda a: check_sprite(a, Path(folder)),
                          lambda a: check_puppet(a, Path(folder)), lambda a: check_focus(a, Path(folder))):
                result.update(check(app))
        result['status'] = 'passed'
    except Exception as error:  # report every failure in the JSON line
        import traceback
        result.update(status='failed', error=repr(error), traceback=traceback.format_exc())
    print(json.dumps(result))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
