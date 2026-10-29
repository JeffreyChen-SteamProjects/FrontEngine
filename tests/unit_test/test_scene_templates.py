"""Template fitting, editable portable scenes, missing assets and owner cancellation."""
from threading import Event
from time import monotonic
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QTest

from frontengine.ui.dialog.scene_templates_dialog import SceneTemplatesDialog
from frontengine.ui.page.scene_setting.scene_actions import SceneActions
from frontengine.ui.page.scene_setting.scene_setting_ui import SceneSettingUI
from frontengine.utils.scene_format.scene_package import save_package
from frontengine.utils.scene_format.scene_source import PreparedScene, read_scene_source
from frontengine.utils.scene_format.scene_templates import BUILTIN_TEMPLATES, fit_template, missing_template_assets


def _wait(condition):
    deadline = monotonic() + 5
    while not condition() and monotonic() < deadline:
        QCoreApplication.processEvents()
        QTest.qWait(5)
    assert condition()


def test_builtin_templates_are_independent_finite_self_contained_layouts():
    assert {template.identifier for template in BUILTIN_TEMPLATES} == {'work', 'teaching', 'focus'}
    for template in BUILTIN_TEMPLATES:
        first = template.entries(lambda key: 'Translated ' + key)
        first[next(iter(first))]['text'] = 'Changed'
        second = template.entries(lambda key: 'Translated ' + key)
        assert all(entry['text'].startswith('Translated ') for entry in second.values())
        assert missing_template_assets(second) == []
        for size in ((800, 600), (2560, 1440)):
            fitted = fit_template(second, size)
            for entry in fitted.values():
                assert 0 <= entry['x'] and 0 <= entry['y']
                assert entry['x'] + entry['width'] <= size[0]
                assert entry['y'] + entry['height'] <= size[1]
                assert 6 <= entry['font_size'] <= 200
        assert second != fitted
    for size in ((True, 720), (100, 720), (1280, 99999)):
        with pytest.raises(ValueError):
            fit_template(second, size)


def test_missing_assets_disable_template_apply_and_leave_editor_unchanged(tmp_path):
    page = SceneSettingUI()
    page.visual_editor.document.reset({'original': {'type': 'TEXT', 'text': 'Keep'}})
    missing = tmp_path / 'missing.png'
    template = SimpleNamespace(identifier='missing', title_key='template_work',
        description_key='template_work_description',
        entries=lambda _translate: {'reference': {'type': 'IMAGE', 'file_path': str(missing)}})
    dialog = SceneTemplatesDialog(page, templates=(template,))
    try:
        assert not dialog.apply_button.isEnabled()
        assert 'reference / file_path:' in dialog.status.text()
        assert str(missing) in dialog.status.text()
        dialog.apply_template()
        assert dialog.pending is None
        assert page.visual_editor.document.entries['original']['text'] == 'Keep'
        assert not page.scene.widget_list
    finally:
        dialog.close()
        page.close()


def test_apply_template_creates_editable_playback_and_portable_export(tmp_path):
    page = SceneSettingUI()
    dialog = SceneTemplatesDialog(page)
    try:
        dialog.list.setCurrentRow(2)
        dialog.apply_template()
        operation = dialog.pending
        assert operation is not None
        _wait(lambda: operation.result is not None)
        assert operation.result is True
        assert len(page.scene.widget_list) == 3
        assert page.tab_widget.currentWidget() is page.visual_editor
        key = next(iter(page.visual_editor.document.entries))
        page.visual_editor.document.update(key, {'text': 'My focus task'})
        path = tmp_path / 'saved.fescene'
        save_package(page.visual_editor.document.entries, path)
        loaded = read_scene_source(path)
        try:
            assert loaded.entries[key]['text'] == 'My focus task'
            assert loaded.entries == page.visual_editor.document.entries
        finally:
            loaded.close()
        page.open_templates()
        first = page.templates_dialog
        page.open_templates()
        assert page.templates_dialog is first
    finally:
        dialog.close()
        page.close()


def test_close_template_dialog_cancels_only_its_waiting_request():
    page = SceneSettingUI()
    page.actions.deleteLater()
    gate, started = Event(), Event()
    original = {'original': {'type': 'TEXT', 'text': 'Keep'}}
    def reader(_path):
        started.set()
        assert gate.wait(3)
        return PreparedScene(original)
    actions = SceneActions(page, reader=reader)
    page.actions = actions
    page.visual_editor.document.reset(original)
    page.scene.add_entry('original', original['original'])
    dialog = SceneTemplatesDialog(page)
    try:
        actions.request('slow.json')
        assert started.wait(2)
        dialog.apply_template()
        operation = dialog.pending
        dialog.close()
        assert operation.result is False
        gate.set()
        _wait(lambda: actions.pending is None)
        assert page.visual_editor.document.entries == original
        assert len(page.scene.widget_list) == 1
        assert not dialog.canvas.items()
    finally:
        gate.set()
        dialog.close()
        page.close()


def test_closed_old_dialog_does_not_cancel_a_newer_scene_request():
    page = SceneSettingUI()
    dialog = SceneTemplatesDialog(page)
    try:
        dialog.apply_template()
        old = dialog.pending
        newer = page.actions.request_entries({'new': {'type': 'TEXT', 'text': 'Newest'}})
        assert old.result is False and dialog.pending is None
        dialog.close()
        _wait(lambda: newer.result is not None)
        assert newer.result is True
        assert page.visual_editor.document.entries['new']['text'] == 'Newest'
    finally:
        page.close()


def test_template_requests_validate_screen_values_before_allocation():
    page = SceneSettingUI()
    try:
        for screen in (True, -1, 'unknown'):
            with pytest.raises(ValueError):
                page.actions.request_entries({'text': {'type': 'TEXT', 'text': 'x'}}, screen)
        assert page.actions.pending is None
        with pytest.raises(ValueError, match='256'):
            page.actions.request_entries({str(index): {'type': 'TEXT', 'text': 'x'} for index in range(257)})
    finally:
        page.close()
