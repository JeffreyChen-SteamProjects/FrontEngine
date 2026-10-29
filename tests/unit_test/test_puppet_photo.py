import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QMessageBox

from test_puppet_startup_lifecycle import asset


@pytest.fixture
def puppet(tmp_path):
    pytest.importorskip('Imervue.puppet.document_io')
    from frontengine.show.pet.puppet_pet import PuppetPetWidget
    from frontengine.user_setting.pet_profiles import PetProfiles
    pet = PuppetPetWidget(asset(tmp_path), size=(128, 192), profiles=PetProfiles({}, lambda: None))
    yield pet
    pet.close()


def test_native_photo_adapter_preserves_alpha_and_state(puppet, tmp_path, monkeypatch):
    image = QImage(128, 192, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    image.setPixelColor(64, 96, QColor(255, 128, 0, 128))
    calls = []
    monkeypatch.setattr(puppet.canvas, 'isValid', lambda: True)
    def render(width, height, **kwargs):
        calls.append((width, height, kwargs))
        return image
    monkeypatch.setattr(puppet.canvas, 'render_offscreen_puppet', render)
    before = puppet.profile_session.state()
    puppet.open_photo()
    dialog = puppet._photo_dialog
    assert calls == [(128, 192, {'background_rgba': (0.0, 0.0, 0.0, 0.0)})]
    image.fill(QColor('black'))
    assert dialog.image.pixelColor(0, 0).alpha() == 0
    assert dialog.image.pixelColor(64, 96) == QColor(255, 128, 0, 128)
    assert dialog.pose.count() == 1
    assert not dialog.time.isEnabled()
    puppet.open_photo()
    assert puppet._photo_dialog is dialog
    assert len(calls) == 1
    target = tmp_path / 'puppet.png'
    assert dialog.save_to(target)
    saved = QImage(str(target))
    assert saved.pixelColor(64, 96) == QColor(255, 128, 0, 128)
    assert puppet.profile_session.state() == before
    dialog.close()


@pytest.mark.parametrize('failure', ['invalid_context', 'missing_method', 'empty', 'driver'])
def test_native_photo_failure_does_not_open_empty_dialog(puppet, monkeypatch, failure):
    warnings, renders = [], []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args))
    monkeypatch.setattr(puppet.canvas, 'isValid', lambda: failure != 'invalid_context')
    def render(*args, **kwargs):
        renders.append(True)
        if failure == 'driver':
            raise RuntimeError('GL context lost')
        return None
    monkeypatch.setattr(puppet.canvas, 'render_offscreen_puppet', None if failure == 'missing_method' else render)
    puppet.open_photo()
    assert puppet._photo_dialog is None
    assert len(warnings) == 1
    assert len(renders) == (1 if failure in ('empty', 'driver') else 0)
