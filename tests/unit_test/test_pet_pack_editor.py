"""Portable pack boundaries, legacy compatibility and preview ownership."""
import shutil
import threading
import time

import pytest
from PySide6.QtCore import QThreadPool
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from frontengine.utils.pet_pack import pack_builder as packs
from frontengine.show.pet.desktop_pet import scan_pet_pack, read_pet_manifest
from frontengine.ui.dialog.pet_pack_editor import PetPackEditor


def sprite(tmp_path, name='source.png'):
    image = QImage(32, 20, QImage.Format.Format_RGBA8888)
    image.fill(QColor('red'))
    path = tmp_path / name
    assert image.save(str(path))
    return str(path)


def wait(predicate):
    deadline = time.monotonic() + 5
    while not predicate() and time.monotonic() < deadline:
        QApplication.processEvents()
        threading.Event().wait(.005)
    assert predicate()


def test_export_moves_to_another_environment_and_legacy_loader_accepts(tmp_path):
    source = sprite(tmp_path)
    destination = tmp_path / 'export'
    draft = packs.PackDraft({'walk': source, 'sleep': source}, 'A pet', 192, 7)
    packs.export_pack(draft, destination)
    shutil.move(destination, tmp_path / 'relocated')
    relocated = tmp_path / 'relocated'
    assert set(scan_pet_pack(str(relocated))) == {'walk', 'sleep'}
    manifest = read_pet_manifest(relocated)
    assert (manifest['name'], manifest['size'], manifest['speed']) == ('A pet', 192, 7)
    loaded = packs.load_pack(relocated)
    assert packs.missing_actions(loaded) == ['idle', 'climb', 'fall', 'drag']
    assert all(str(relocated) in path for path in loaded.actions.values())
    assert not any(str(tmp_path / 'source') in path for path in loaded.actions.values())


@pytest.mark.parametrize('change', [{'name': ''}, {'size': True}, {'speed': 11}, {'actions': {}}, {'actions': {'unknown': 'x'}}])
def test_invalid_drafts_never_create_destination(tmp_path, change):
    values = dict(actions={'walk': sprite(tmp_path)}, name='Pet', size=128, speed=3)
    values.update(change)
    with pytest.raises(ValueError):
        packs.export_pack(packs.PackDraft(**values), tmp_path / 'output')
    assert not (tmp_path / 'output').exists()


def test_invalid_resource_and_manifest_rejected(tmp_path):
    invalid = tmp_path / 'walk.png'
    invalid.write_bytes(b'not an image')
    with pytest.raises(ValueError, match='invalid'):
        packs.load_pack(tmp_path)
    invalid.unlink()
    sprite(tmp_path, 'run.png')
    manifest = tmp_path / 'pet.json'
    manifest.write_text('[]')
    with pytest.raises(ValueError, match='object'):
        packs.load_pack(tmp_path)
    manifest.write_bytes(b' ' * 65537)
    with pytest.raises(ValueError, match='64 KiB'):
        packs.load_pack(tmp_path)
    with pytest.raises(ValueError, match='.puppet'):
        packs.validate_sprite(tmp_path / 'source.puppet')


def test_cancel_or_copy_failure_leaves_no_partial_folder(tmp_path, monkeypatch):
    draft = packs.PackDraft({'walk': sprite(tmp_path)})
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(InterruptedError):
        packs.export_pack(draft, tmp_path / 'output', cancel=cancel)
    def fail(*_args):
        raise OSError('disk failure')
    monkeypatch.setattr(packs, '_copy_sprite', fail)
    with pytest.raises(OSError, match='disk failure'):
        packs.export_pack(draft, tmp_path / 'output')
    assert not list(tmp_path.glob('.frontengine-pet-*'))
    assert not (tmp_path / 'output').exists()


def test_existing_destination_is_untouched_and_alias_import_is_bounded(tmp_path, monkeypatch):
    draft = packs.PackDraft({'walk': sprite(tmp_path)})
    target = tmp_path / 'target'
    target.mkdir()
    sentinel = target / 'sentinel'
    sentinel.write_text('keep')
    with pytest.raises(ValueError, match='new folder'):
        packs.export_pack(draft, target)
    assert sentinel.read_text() == 'keep'
    sprite(tmp_path, 'run.png')
    assert packs.load_pack(tmp_path).actions['walk'].endswith('run.png')
    monkeypatch.setattr(packs, 'MAX_FILE_BYTES', 1)
    with pytest.raises(ValueError, match='64 MiB'):
        packs.validate_sprite(draft.actions['walk'])


def test_preview_speed_size_and_shutdown(tmp_path):
    dialog = PetPackEditor()
    try:
        dialog.actions['walk'] = sprite(tmp_path)
        dialog.show()
        QApplication.processEvents()
        dialog.size_field.setValue(192)
        dialog.speed.setValue(7)
        assert dialog.preview.pet_size == 192 and dialog.preview.speed == 7
        before = dialog.preview.position
        dialog.preview._tick()
        assert dialog.preview.position - before == 7
        assert dialog.preview.timer.isActive()
        dialog.reject()
        assert not dialog.preview.timer.isActive() and dialog.preview.image is None
    finally:
        dialog.close()


def test_worker_error_preserves_choices_and_close_cancels(tmp_path):
    dialog = PetPackEditor()
    source = sprite(tmp_path)
    dialog.actions['walk'] = source
    entered, release = threading.Event(), threading.Event()
    observed = []
    def operation(cancel):
        entered.set()
        assert release.wait(5)
        observed.append(cancel.is_set())
        raise ValueError('injected failure')
    try:
        dialog.show()
        dialog._start_job('import', operation)
        wait(entered.is_set)
        assert not dialog.name.isEnabled()
        dialog.reject()
        release.set()
        wait(lambda: dialog.pending is None)
        assert observed == [True] and dialog.actions == {'walk': source}
        assert dialog.closed and not dialog.preview.timer.isActive()
    finally:
        release.set()
        QThreadPool.globalInstance().waitForDone(5000)
        dialog.close()


def test_export_selection_does_not_spawn_a_pet(tmp_path):
    dialog = PetPackEditor()
    selected = []
    dialog.pack_selected.connect(selected.append)
    try:
        dialog.show()
        draft = packs.PackDraft({'walk': sprite(tmp_path)})
        dialog._start_job('export', lambda cancel: packs.export_pack(draft, tmp_path / 'output', cancel=cancel))
        wait(lambda: dialog.pending is None)
        assert selected == [] and dialog.use_button.isEnabled()
        dialog.use_export()
        assert selected == [str(tmp_path / 'output')]
        assert dialog.status_kind == 'exported'
        dialog._retranslate()
        assert str(tmp_path / 'output') in dialog.status.text()
    finally:
        dialog.close()
