"""Windows native GL photo probe; never activates or places a window on a screen.

Run with pythonw and an absolute output directory. Uses an isolated synthetic
asset and in-memory profiles, not the user's pets or settings.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
import traceback

from PySide6.QtCore import QBuffer, QIODevice, QTimer, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication


def fixture(path: Path) -> None:
    from Imervue.puppet.document import Drawable, Expression, ExpressionParam, Parameter, PuppetDocument
    from Imervue.puppet.document_io import save_puppet

    texture = QImage(8, 8, QImage.Format.Format_RGBA8888)
    texture.fill(QColor(255, 128, 0, 128))
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert texture.save(buffer, 'PNG')
    doc = PuppetDocument(size=(128, 128), drawables=[Drawable(
        'square', 'textures/square.png', [(32, 32), (96, 32), (96, 96), (32, 96)],
        [0, 1, 2, 0, 2, 3], [(0, 0), (1, 0), (1, 1), (0, 1)],
        opacity_keys=[{'parameter': 'CareOpacity', 'stops': [
            {'value': 0.0, 'alpha': 0.0}, {'value': 1.0, 'alpha': 1.0}]}])],
        parameters=[Parameter('CareOpacity', 0.0, 1.0, 1.0)],
        expressions=[Expression('care', [ExpressionParam('CareOpacity', 0.5, 'overwrite')])],
        textures={'textures/square.png': bytes(buffer.data())})
    save_puppet(doc, path)
    path.with_suffix('.petscript.json').write_text(json.dumps({
        'version': 1, 'frontengine_actions': {'feed': {'expression': 'care'}}}), encoding='utf-8')


def verify_reaction(pet, output: Path, baseline: QImage) -> dict:
    pet.feed()
    assert pet.profile_session.companion.action == 'feed'
    active = pet.photo_image()
    alpha = active.pixelColor(64, 64).alpha()
    assert 60 <= alpha <= 68, f'Care expression did not halve alpha: {alpha}'
    assert active.save(str(output / 'reaction.png'), 'PNG')
    pet.profile_session.advance(2)
    assert pet.profile_session.companion.action is None
    assert pet.photo_image() == baseline, 'Reaction completion did not restore the image'
    pet._choose_expression('care', True)
    pet.profile_session.advance(60)
    pet.feed()
    assert pet.profile_session.companion.action == 'feed'
    pet.profile_session.advance(2)
    assert pet.canvas.active_expressions() == ['care'], 'Completion removed a manual expression'
    assert pet.photo_image() == active, 'Manual expression pixels changed after completion'
    pet._choose_expression('care', False)
    assert pet.photo_image() == baseline
    return {'active_alpha': alpha, 'completion_restores_image': True,
            'manual_expression_preserved': True}


def main() -> int:
    from frontengine.show.pet.puppet_pet import PuppetPetWidget
    from frontengine.user_setting.pet_profiles import PetProfiles

    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    if app.platformName() != 'windows':
        raise RuntimeError('This probe requires the native Windows Qt platform')
    fixture(output / 'fixture.puppet')
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    observations = []
    pet = PuppetPetWidget(output / 'fixture.puppet', size=(128, 128),
                          script_path=str(output / 'fixture.petscript.json'),
                          profiles=PetProfiles({}, lambda: None))
    pet.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
    pet.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    pet.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    right = max(screen.geometry().right() for screen in app.screens())
    pet.move(right + 1024, 0)
    result = {'status': 'failed', 'platform': app.platformName()}

    def observe():
        point = wintypes.POINT()
        if not user32.GetCursorPos(ctypes.byref(point)):
            raise ctypes.WinError(ctypes.get_last_error())
        observations.append({'foreground': int(user32.GetForegroundWindow() or 0),
                             'cursor': [point.x, point.y]})

    def verify():
        try:
            observe()
            assert all(not pet.frameGeometry().intersects(s.geometry()) for s in app.screens())
            assert pet.canvas.isValid(), 'Native OpenGL context is invalid'
            before = pet.profile_session.state()
            first = pet.photo_image()
            second = pet.photo_image()
            assert first == second, 'Repeated capture changed pixels'
            assert before == pet.profile_session.state(), 'Photo changed profile'
            assert first.pixelColor(0, 0).alpha() == 0, 'Background is not transparent'
            center = first.pixelColor(64, 64)
            assert 120 <= center.alpha() <= 136, center.getRgb()
            assert center.red() > 240 and 115 <= center.green() <= 140, center.getRgb()
            assert first.save(str(output / 'photo.png'), 'PNG')
            saved = QImage(str(output / 'photo.png'))
            assert saved.convertToFormat(QImage.Format.Format_RGBA8888) == first.convertToFormat(
                QImage.Format.Format_RGBA8888), 'Saved PNG pixels differ'
            pet.canvas.grabFramebuffer()
            assert pet.photo_image() == first, 'Canvas repaint changed subsequent photo'
            result['reaction'] = verify_reaction(pet, output, first)
            own_handle = int(pet.winId())
            assert all(item['foreground'] != own_handle for item in observations)
            result.update(status='passed', center_rgba=center.getRgb(),
                          size=[first.width(), first.height()], native_gl=True,
                          fixture_only=True, pet_handle=own_handle)
        except Exception as exc:
            result['error'] = repr(exc)
            result['traceback'] = traceback.format_exc()
        finally:
            poll.stop()
            pet.close()
            observe()
            result['observations'] = observations
            (output / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            app.quit()

    observe()
    pet.show()
    poll = QTimer()
    poll.timeout.connect(observe)
    poll.start(50)
    QTimer.singleShot(1500, verify)
    app.exec()
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
