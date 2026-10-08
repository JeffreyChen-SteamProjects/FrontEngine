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


def test_gif_sprite_pet_puppet_and_portable_scene_static_thumbnails(tmp_path):
    gif = tmp_path/'one.gif'
    gif.write_bytes(base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'))
    assert inspect_asset(gif)[0] == 'gif'
    pet = tmp_path/'pet'
    pet.mkdir()
    texture = picture(pet/'walk.png')
    assert inspect_asset(pet)[0] == 'pet'
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
