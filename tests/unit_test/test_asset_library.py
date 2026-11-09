"""Static catalog behavior, exact reference repair, rollback and owner lifecycle."""
from copy import deepcopy
import json
import base64
import zipfile
from pathlib import Path
from threading import Event
import time

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QApplication, QWidget

from frontengine.utils.asset_library.repository import AssetRepository
from frontengine.utils.asset_library.inspect import inspect_asset
from frontengine.utils.asset_library.references import plan_relink, commit_relink, recover_relink, list_references
from frontengine.utils.asset_library.service import AssetLibraryService
from frontengine.utils.asset_library.file_lock import catalog_lock
from frontengine.utils.scene_format.scene_editor_document import SceneEditorDocument
from frontengine.ui.dialog.asset_library_dialog import AssetLibraryDialog
from frontengine.utils.todo.repository import atomic_write


def picture(path: Path, color: str = 'red') -> Path:
    image = QImage(32, 24, QImage.Format.Format_RGBA8888)
    image.fill(QColor(color))
    assert image.save(str(path))
    return path


def wait(predicate) -> None:
    deadline = time.monotonic() + 5
    while not predicate() and time.monotonic() < deadline:
        QApplication.processEvents()
        Event().wait(.005)
    assert predicate()


def fixture(tmp_path):
    old, new = picture(tmp_path/'old.png'), picture(tmp_path/'new.png', 'blue')
    repository = AssetRepository(tmp_path)
    identity = repository.add(old)
    scene = {'layer': {'type': 'IMAGE', 'file_path': str(old), 'opacity': 100, 'width': 320, 'height': 180}}
    scene_path = tmp_path/'scene.json'
    scene_path.write_text(json.dumps(scene), encoding='utf-8')
    repository.add(scene_path)
    directory = tmp_path/'presets'
    directory.mkdir()
    preset = directory/'example.json'
    preset.write_text(json.dumps({'image': {'image_path': str(old)}, 'text': {'text': str(old)}}), encoding='utf-8')
    return repository, identity, old, new, scene, scene_path, preset


def test_static_thumbnails_tags_favorites_search_and_missing_path_retention(tmp_path):
    repository, identity, old, _new, scene, scene_path, _preset = fixture(tmp_path)
    repository.edit(identity, tags=['work', 'color', 'work'], favorite=True)
    assert repository.add(old) == identity
    entries = repository.entries(text='WORK', favorites=True)
    assert len(entries) == 1 and entries[0]['thumbnail'].pixelColor(0, 0) == QColor('red')
    assert entries[0]['tags'] == ['work', 'color']
    kind, thumbnail = inspect_asset(scene_path)
    assert kind == 'scene' and not thumbnail.isNull()
    old.unlink()
    missing = AssetRepository(tmp_path).entries(text='old.png')[0]
    assert missing['error'] and missing['thumbnail'].isNull()
    assert len(list_references(repository, identity, scene)) == 3
    repository.remove(identity)
    assert scene_path.exists() and identity not in repository.assets


def test_gif_puppet_and_portable_scene_static_thumbnails_and_no_pet_folders(tmp_path):
    gif = tmp_path/'one.gif'
    gif.write_bytes(base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'))
    assert inspect_asset(gif)[0] == 'gif'
    pet = tmp_path/'pet'
    pet.mkdir()
    texture = picture(pet/'walk.png')
    with pytest.raises(ValueError):             # sprite pet folders: pets are layered only
        inspect_asset(pet)
    puppet = tmp_path/'fixture.puppet'
    manifest = {'version': 1, 'size': [32, 24], 'drawables': [{'texture': 'textures/one.png'}],
                'deformers': [], 'parameters': []}
    with zipfile.ZipFile(puppet, 'w') as archive:
        archive.writestr('puppet.json', json.dumps(manifest))
        archive.write(texture, 'textures/one.png')
    kind, thumbnail = inspect_asset(puppet)
    assert kind == 'puppet' and thumbnail.pixelColor(0, 0) == QColor('red')
    from frontengine.utils.scene_format.scene_package import save_package
    package = tmp_path/'scene.fescene'
    save_package({'one': {'type': 'IMAGE', 'file_path': str(texture)}}, package)
    assert inspect_asset(package)[0] == 'scene'


def test_forged_recovery_journal_cannot_overwrite_unregistered_workspace_json(tmp_path):
    repository, _identity, _old, _new, _scene, _scene_path, _preset = fixture(tmp_path)
    target = tmp_path/'tasks.json'
    target.write_text('{}', encoding='utf-8')
    import hashlib
    records = [dict(path=str(target), before=base64.b64encode(b'{"bad":true}').decode(),
                    after_hash=hashlib.sha256(b'{}').hexdigest()),
               dict(path=str(repository.path), before=base64.b64encode(repository.path.read_bytes()).decode(),
                    after_hash=hashlib.sha256(repository.path.read_bytes()).hexdigest())]
    (tmp_path/'.asset-relink.json').write_text(json.dumps({'version': 1, 'files': records}), encoding='utf-8')
    with pytest.raises(ValueError, match='not a registered'):
        recover_relink(tmp_path)
    assert target.read_text() == '{}'


def test_relink_updates_exact_scene_and_preset_fields_but_preserves_literal_text(tmp_path):
    repository, identity, old, new, scene, scene_path, preset = fixture(tmp_path)
    old.unlink()
    plan = plan_relink(repository, identity, str(new), scene)
    assert len(plan['references']) == 3
    assert plan['scene_after']['layer']['file_path'] == str(new)
    commit_relink(repository, plan)
    assert json.loads(scene_path.read_text())['layer']['file_path'] == str(new)
    state = json.loads(preset.read_text())
    assert state['image']['image_path'] == str(new) and state['text']['text'] == str(old)
    assert AssetRepository(tmp_path).assets[identity]['path'] == str(new)
    assert not (tmp_path/'.asset-relink.json').exists()


def test_relink_failure_rolls_back_all_replaced_documents_and_catalog(tmp_path):
    repository, identity, _old, new, scene, scene_path, preset = fixture(tmp_path)
    before = {path: path.read_bytes() for path in (scene_path, preset, repository.path)}
    calls = []
    def writer(path, data):
        calls.append(path)
        if len(calls) == 2:
            raise OSError('injected disk failure')
        atomic_write(path, data)
    with pytest.raises(OSError, match='injected'):
        commit_relink(repository, plan_relink(repository, identity, str(new), scene), writer=writer)
    assert all(path.read_bytes() == value for path, value in before.items())
    assert not (tmp_path/'.asset-relink.json').exists()


def test_crash_journal_restores_partial_writes_on_next_job(tmp_path, monkeypatch):
    repository, identity, _old, new, scene, scene_path, preset = fixture(tmp_path)
    import frontengine.utils.asset_library.references as module
    before = {path: path.read_bytes() for path in (scene_path, preset, repository.path)}
    actual_recover = module.recover_relink
    monkeypatch.setattr(module, 'recover_relink', lambda _root: None)
    calls = []
    def crash(path, data):
        calls.append(path)
        if len(calls) == 2:
            raise SystemExit('simulated process interruption')
        atomic_write(path, data)
    with pytest.raises(SystemExit):
        commit_relink(repository, plan_relink(repository, identity, str(new), scene), writer=crash)
    assert (tmp_path/'.asset-relink.json').exists() and preset.read_bytes() != before[preset]
    actual_recover(tmp_path)
    assert all(path.read_bytes() == value for path, value in before.items())


def test_changed_reference_rejects_review_and_external_workshop_scenes_are_readonly(tmp_path):
    repository, identity, old, new, scene, scene_path, preset = fixture(tmp_path)
    managed = tmp_path/'managed'
    managed.mkdir()
    (managed/'workshop.json').write_text('{}', encoding='utf-8')
    workshop_scene = managed/'shared.json'
    workshop_scene.write_text(json.dumps(scene), encoding='utf-8')
    repository.add(workshop_scene)
    plan = plan_relink(repository, identity, str(new), scene)
    assert any(not item['writable'] and item['owner'] == str(workshop_scene) for item in plan['references'])
    assert all(record['path'] != str(workshop_scene) for record in plan['files'])
    before = repository.path.read_bytes()
    preset.write_text('{"image":{}}', encoding='utf-8')
    with pytest.raises(ValueError, match='changed'):
        commit_relink(repository, plan)
    assert repository.path.read_bytes() == before
    assert json.loads(scene_path.read_text())['layer']['file_path'] == str(old)


def test_recovery_conflict_does_not_overwrite_unrelated_changes(tmp_path, monkeypatch):
    repository, identity, _old, new, scene, _scene_path, preset = fixture(tmp_path)
    import frontengine.utils.asset_library.references as module
    monkeypatch.setattr(module, 'recover_relink', lambda _root: None)
    def failure(_path, _data):
        raise OSError('retain journal')
    with pytest.raises(OSError):
        commit_relink(repository, plan_relink(repository, identity, str(new), scene), writer=failure)
    preset.write_text('{"image":{}}', encoding='utf-8')
    with pytest.raises(ValueError, match='conflict'):
        recover_relink(tmp_path)
    assert preset.read_text() == '{"image":{}}' and (tmp_path/'.asset-relink.json').exists()


def test_catalog_bounds_type_compatibility_and_os_owned_lock(tmp_path):
    repository, identity, _old, _new, scene, scene_path, _preset = fixture(tmp_path)
    with pytest.raises(ValueError, match='same asset type'):
        plan_relink(repository, identity, str(scene_path), scene)
    with pytest.raises(ValueError, match='tags'):
        repository.edit(identity, tags=['x'*41], favorite=True)
    with catalog_lock(tmp_path):
        with pytest.raises(ValueError, match='Another instance'):
            with catalog_lock(tmp_path):
                pass
    with catalog_lock(tmp_path):
        pass


def test_dialog_static_search_and_commit_restore_scene_on_worker_failure(tmp_path):
    repository, identity, _old, new, scene, _scene_path, _preset = fixture(tmp_path)
    service = AssetLibraryService(tmp_path)
    document = SceneEditorDocument()
    document.reset(scene)
    owner = QWidget()
    dialog = AssetLibraryDialog(service, document, owner)
    try:
        assert service.thread is None
        dialog.show()
        wait(lambda: dialog.entries.count() == 2)
        dialog.search.setText('old.png')
        wait(lambda: dialog.entries.count() == 1)
        dialog.entries.setCurrentRow(0)
        dialog.tags.setText('selected, blue')
        dialog.favorite.setChecked(True)
        dialog._save()
        wait(lambda: not service.busy and AssetRepository(tmp_path).assets[identity]['favorite'])
        plan = plan_relink(AssetRepository(tmp_path), identity, str(new), deepcopy(document.entries))
        plan['files'][0]['before'] = b'changed after review'
        dialog.commit_plan(plan)
        wait(lambda: not service.busy and dialog.plan is None)
        assert document.entries == scene and 'changed' in dialog.status.text().lower()
        assert document.undo.canUndo()
    finally:
        service.stop()
        if service.thread:
            service.thread.join(5)
        dialog.close()
        owner.deleteLater()
        QCoreApplication.sendPostedEvents(owner, QEvent.Type.DeferredDelete)


@pytest.mark.parametrize('destroy', [False, True])
@pytest.mark.parametrize('operation', ['add', 'relink', 'review'])
def test_closed_asset_dialog_discards_modal_result(tmp_path, monkeypatch, destroy, operation):
    from PySide6.QtWidgets import QFileDialog, QMessageBox
    from shiboken6 import isValid

    repository, identity, _old, new, scene, scene_path, preset = fixture(tmp_path)
    service = AssetLibraryService(tmp_path)
    document = SceneEditorDocument()
    document.reset(scene)
    dialog = AssetLibraryDialog(service, document)
    dialog.show()
    wait(lambda: not service.busy)
    from PySide6.QtCore import Qt
    for row in range(dialog.entries.count()):
        if dialog.entries.item(row).data(Qt.ItemDataRole.UserRole)['id'] == identity:
            dialog.entries.setCurrentRow(row)
            break
    started = []
    service.started.connect(started.append)
    original_assets = deepcopy(AssetRepository(tmp_path).assets)
    originals = {path: path.read_bytes() for path in (scene_path, preset)}
    def retire():
        dialog.reject()
        if destroy:
            dialog.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    def choose_file(*_args):
        retire()
        return str(new), ''
    def confirm(*_args):
        retire()
        return QMessageBox.StandardButton.Yes
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', choose_file)
    monkeypatch.setattr(QMessageBox, 'question', confirm)
    try:
        if operation == 'review':
            plan = plan_relink(repository, identity, str(new), deepcopy(document.entries))
            dialog._review(plan)
        elif operation == 'relink':
            dialog._relink()
        else:
            dialog._add()
        wait(lambda: not service.busy)
        assert started == []
        assert document.entries == scene
        assert AssetRepository(tmp_path).assets == original_assets
        assert {path: path.read_bytes() for path in originals} == originals
        def unexpected_prompt(*_args):
            pytest.fail('closed asset dialog reopened a prompt')
        monkeypatch.setattr(QFileDialog, 'getOpenFileName', unexpected_prompt)
        monkeypatch.setattr(QMessageBox, 'question', unexpected_prompt)
        dialog._add()
        dialog._relink()
        dialog._review({})
    finally:
        service.stop()
        if service.thread:
            service.thread.join(5)
        if isValid(dialog):
            dialog.close()


def test_asset_relink_confirmation_cancel_then_retry(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    repository, identity, _old, new, scene, scene_path, preset = fixture(tmp_path)
    service = AssetLibraryService(tmp_path)
    document = SceneEditorDocument()
    document.reset(scene)
    dialog = AssetLibraryDialog(service, document)
    answers = iter([QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes])
    monkeypatch.setattr(QMessageBox, 'question', lambda *_args: next(answers))
    try:
        dialog.show()
        wait(lambda: not service.busy)
        plan = plan_relink(repository, identity, str(new), deepcopy(scene))
        before = {path: path.read_bytes() for path in (scene_path, preset)}
        dialog._review(plan)
        assert document.entries == scene
        assert {path: path.read_bytes() for path in before} == before
        assert not service.busy
        dialog._review(plan)
        wait(lambda: not service.busy and dialog.plan is None)
        assert document.entries == plan['scene_after']
        assert document.entries['layer']['file_path'] == str(new)
        assert AssetRepository(tmp_path).assets[identity]['path'] == str(new)
        assert json.loads(scene_path.read_text(encoding='utf-8'))['layer']['file_path'] == str(new)
        assert json.loads(preset.read_text(encoding='utf-8'))['image']['image_path'] == str(new)
    finally:
        service.stop()
        if service.thread:
            service.thread.join(5)
        dialog.close()


@pytest.mark.parametrize('operation', ['add', 'relink'])
def test_asset_picker_cancel_allows_retry(tmp_path, monkeypatch, operation):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    repository, identity, _old, replacement, scene, _scene_path, _preset = fixture(tmp_path)
    service = AssetLibraryService(tmp_path)
    document = SceneEditorDocument()
    document.reset(scene)
    dialog = AssetLibraryDialog(service, document)
    choices = iter(['', str(replacement)])
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *_args: (next(choices), ''))
    monkeypatch.setattr(QMessageBox, 'question', lambda *_args: QMessageBox.StandardButton.Yes)
    try:
        dialog.show()
        wait(lambda: not service.busy)
        for row in range(dialog.entries.count()):
            if dialog.entries.item(row).data(Qt.ItemDataRole.UserRole)['id'] == identity:
                dialog.entries.setCurrentRow(row)
                break
        before = deepcopy(AssetRepository(tmp_path).assets)
        action = dialog._add if operation == 'add' else dialog._relink
        action()
        assert not service.busy
        assert AssetRepository(tmp_path).assets == before
        assert document.entries == scene
        action()
        wait(lambda: not service.busy and dialog.plan is None)
        assets = AssetRepository(tmp_path).assets
        if operation == 'relink':
            assert len(assets) == len(before)
            assert assets[identity]['path'] == str(replacement)
        else:
            assert len(assets) == len(before) + 1
            assert any(asset['path'] == str(replacement) for asset in assets.values())
    finally:
        service.stop()
        if service.thread:
            service.thread.join(5)
        dialog.close()


def test_sprite_pet_folders_saved_before_pets_were_layered_only_are_dropped_on_load(tmp_path):
    from frontengine.utils.asset_library.repository import checked_assets
    folder = tmp_path / 'old-pet'
    folder.mkdir()
    entries = [{'id': 'a' * 32, 'path': str(folder), 'kind': 'pet', 'tags': [], 'favorite': False},
               {'id': 'b' * 32, 'path': str(tmp_path / 'one.png'), 'kind': 'image', 'tags': [], 'favorite': True}]
    assert list(checked_assets(entries)) == ['b' * 32]
