"""Document routing and failed 3D playback must preserve the existing workflow."""
import json
from time import monotonic

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QTest

from frontengine.ui.page.scene_setting.scene_setting_ui import SceneSettingUI
from frontengine.utils.scene_format.scene_3d_document import make_3d_scene
from frontengine.user_setting.scene_setting import current_scene_document, adopt_scene_document


def wait_for(condition):
    deadline = monotonic()+5
    while not condition() and monotonic() < deadline:
        QCoreApplication.processEvents()
        QTest.qWait(5)
    assert condition()


@pytest.fixture
def page():
    previous = current_scene_document()
    adopt_scene_document({})
    widget = SceneSettingUI()
    try:
        yield widget
    finally:
        widget.close()
        adopt_scene_document(previous)


def test_mode_switch_json_and_undo_keep_camera_and_settings(page):
    editor = page.visual_editor
    editor.document.reset({'title': {'type': 'TEXT', 'text': 'Keep', 'x': 12}})
    editor.scene_mode.setCurrentIndex(1)
    assert editor.document.scene.mode == '3d'
    data = json.loads(page.scene_manager_ui.json_plaintext.toPlainText())
    assert data['camera'] == editor.document.scene.camera
    assert data['entries']['title']['x'] == 12
    editor.document.undo.undo()
    assert editor.document.scene.mode == '2d'
    editor.document.undo.redo()
    assert editor.document.scene.mode == '3d'
    data['playback'] = {'rate': 2, 'loop': True}
    page.scene_manager_ui.json_plaintext.setPlainText(json.dumps(data))
    page.scene_manager_ui.apply_json()
    assert editor.document.scene.playback['rate'] == 2
    assert current_scene_document().camera == data['camera']


def test_failed_gpu_request_preserves_editor_and_old_playback(page, monkeypatch):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    original = {'title': {'type': 'TEXT', 'text': 'Keep'}}
    page.visual_editor.document.reset(original)
    page.scene.add_entry('title', original['title'])
    proxy = page.scene.widget_list[0]
    monkeypatch.setitem(user_setting_dict, 'render_backend', 'software')
    receipt = page.actions.request_entries(make_3d_scene({'cube': {'type': 'CUBE'}}))
    wait_for(lambda: receipt.result is not None)
    assert receipt.result is False
    assert 'OpenGL' in receipt.error
    assert page.visual_editor.document.entries == original
    assert page.scene.widget_list == [proxy]
    assert page.scene.runtime3d is None


def test_3d_animation_dialog_saves_numeric_rotation_with_undo(page):
    from frontengine.ui.dialog.scene_3d_animation_dialog import Scene3DAnimationDialog
    document = page.visual_editor.document
    document.reset(make_3d_scene({'cube': {'type': 'CUBE'}}))
    dialog = Scene3DAnimationDialog(document, 'cube', page)
    try:
        dialog.channels.setCurrentIndex(dialog.channels.findData('rotation'))
        dialog._add()
        dialog._add()
        dialog.table.item(1, 2).setText('90')
        dialog._save()
        frames = document.entries['cube']['tracks']['rotation']
        assert len(frames) == 2 and len(frames[1]['value']) == 4
        document.undo.undo()
        assert 'tracks' not in document.entries['cube']
    finally:
        dialog.close()


def test_3d_templates_keep_full_documents_in_library(page):
    from frontengine.ui.dialog.scene_templates_dialog import SceneTemplatesDialog
    from frontengine.utils.scene_format.scene_3d_templates import BUILTIN_3D_TEMPLATES
    from frontengine.utils.scene_format.scene_templates import fit_template, missing_template_assets
    dialog = SceneTemplatesDialog(page)
    try:
        assert dialog.list.count() == 6
        for row, template in enumerate(BUILTIN_3D_TEMPLATES, 3):
            document = fit_template(template.entries(lambda key: key), (1920, 1080))
            assert document.mode == '3d' and document.camera in document.entries
            assert not missing_template_assets(document)
            dialog.list.setCurrentRow(row)
            assert dialog.apply_button.isEnabled()
            assert dialog.preview_stack.currentIndex() == 1
    finally:
        dialog.close()


def test_rapid_structural_edits_keep_latest_requested_document(page):
    from threading import Event
    from types import SimpleNamespace
    from frontengine.utils.actions.deferred_action import DeferredAction
    original = make_3d_scene({'cube': {'type': 'CUBE'}})
    page.scene.runtime3d = SimpleNamespace(document=original, update_document=lambda _doc: False)
    receipt = DeferredAction(page)
    page.actions.pending = {'cancel': Event(), 'request': (receipt, '', 'primary', False, original, True)}
    try:
        first = original.copy()
        first.entries['sphere'] = {'type': 'SPHERE'}
        page.actions._synchronize_document(first)
        assert page.actions.wanted is not None
        old_receipt = page.actions.wanted[0]
        latest = first.copy()
        latest.entries['plane'] = {'type': 'PLANE'}
        page.actions._synchronize_document(latest)
        assert old_receipt.result is False
        assert page.actions.wanted[4].entries.keys() == latest.entries.keys()
        assert page.actions.pending['cancel'].is_set()
    finally:
        page.actions.pending = page.actions.wanted = None
        page.scene.runtime3d = None
