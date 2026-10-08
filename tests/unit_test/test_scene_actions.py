"""Scene automation uses real editor/proxy frames and isolated worker inputs."""
import json
from pathlib import Path
from threading import Event, get_ident
from time import monotonic
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QWidget

from frontengine.show.scene.compositor_view import SceneCompositorView
from frontengine.show.scene.scene import SceneManager
from frontengine.ui.main_ui import FrontEngineMainUI
from frontengine.ui.page.scene_setting.scene_actions import SceneActions
from frontengine.ui.page.scene_setting.scene_setting_ui import SceneSettingUI
from frontengine.utils.actions.action_registry import Action, ActionRegistry
from frontengine.utils.rules.rule_engine import RuleEngineService, normalize_rule
from frontengine.utils.scene_format.scene_action_values import scene_request, layer_changes
from frontengine.utils.scene_format.scene_package import save_package
from frontengine.utils.scene_format.scene_source import PreparedScene, read_scene_source


def _wait(condition):
    deadline = monotonic() + 5
    while not condition() and monotonic() < deadline:
        QCoreApplication.processEvents()
        QTest.qWait(5)
    assert condition()


def _image_scene(tmp_path):
    image = QImage(16, 16, QImage.Format.Format_RGBA8888)
    image.fill(QColor('red'))
    path = tmp_path / 'red.png'
    assert image.save(str(path))
    return {'reference': {'type': 'IMAGE', 'file_path': str(path), 'width': 16, 'height': 16,
                          'opacity': 100, 'x': 0, 'y': 0}}


def test_hidden_proxies_do_not_produce_compositor_pixels(tmp_path):
    manager = SceneManager()
    manager.add_entry('reference', _image_scene(tmp_path)['reference'])
    view = SceneCompositorView(manager.graphic_scene, 'software')
    view.resize(32, 32)
    try:
        assert view.output_frame().pixelColor(8, 8).red() == 255
        manager.widget_list[0].setVisible(False)
        assert view.output_frame().pixelColor(8, 8).alpha() == 0
    finally:
        view.close()
        manager.clear()


def test_scene_values_validate_optional_path_screens_layers_and_geometry():
    assert scene_request('') == ('', 'primary')
    assert scene_request('{"path":"sample.fescene","screen":0}') == ('sample.fescene', 0)
    for value in ('{"screen":true}', '{"screen":-1}', '{"screen":"other"}', '{"unexpected":1}'):
        with pytest.raises(ValueError):
            scene_request(value)
    with pytest.raises(ValueError):
        scene_request('', load_only=True)
    assert layer_changes('layer_hide', ' exact ') == ('exact', {'visible': False})
    for value in ('{"layer":"ref","opacity":NaN}', '{"layer":"ref","opacity":101}',
                  '{"layer":"ref","opacity":true}', '{"layer":"ref","opacity":50,"other":1}'):
        with pytest.raises(ValueError):
            layer_changes('layer_opacity', value)
    with pytest.raises(ValueError):
        layer_changes('layer_position', '{"layer":"ref","x":100001,"y":0}')
    assert normalize_rule({'label': 'Play', 'action': 'scene_start'}) is not None
    assert normalize_rule({'label': 'Bad', 'action': 'layer_opacity', 'value': 'wrong'}) is None


def test_background_source_read_does_not_modify_shared_scene(tmp_path):
    from frontengine.user_setting.scene_setting import scene_json
    original = dict(scene_json)
    entries = _image_scene(tmp_path)
    path = tmp_path / 'source.json'
    path.write_text(json.dumps({'reference': {**entries['reference'], 'file_path': 'red.png'}}), encoding='utf-8')
    prepared = read_scene_source(path)
    assert prepared.entries['reference']['file_path'] == str((tmp_path / 'red.png').resolve())
    assert scene_json == original
    path.write_text(json.dumps({str(index): {'type': 'TEXT', 'text': 'x'} for index in range(257)}), encoding='utf-8')
    with pytest.raises(ValueError, match='256'):
        read_scene_source(path)


def test_layer_actions_update_pixels_document_and_undo_without_doubled_opacity(tmp_path):
    page = SceneSettingUI()
    entries = _image_scene(tmp_path)
    page.visual_editor.document.reset(entries)
    page.scene.add_entry('reference', entries['reference'])
    view = SceneCompositorView(page.scene.graphic_scene, 'software')
    view.resize(64, 64)
    page.scene.view_list.append(view)
    try:
        assert page.actions.layer('layer_opacity', '{"layer":"reference","opacity":50}')
        assert 126 <= view.output_frame().pixelColor(8, 8).alpha() <= 129
        page.actions.layer('layer_position', '{"layer":"reference","x":20,"y":10}')
        assert view.output_frame().pixelColor(8, 8).alpha() == 0
        assert view.output_frame().pixelColor(28, 18).alpha() > 0
        page.actions.layer('layer_hide', 'reference')
        assert view.output_frame().pixelColor(28, 18).alpha() == 0
        page.visual_editor.document.undo.undo()
        assert view.output_frame().pixelColor(28, 18).alpha() > 0
        page.visual_editor.document.undo.undo()
        assert page.scene.widget_list[0].pos().x() == 0
        page.visual_editor.document.update('reference', {'locked': True})
        with pytest.raises(ValueError, match='locked'):
            page.actions.layer('layer_hide', 'reference')
        with pytest.raises(ValueError, match='Unknown'):
            page.actions.layer('layer_show', 'missing')
    finally:
        page.close()


def test_native_instances_follow_each_monitor_origin_without_hiding_peers():
    manager = SceneManager()
    manager.layer_settings['pet'] = {'type': 'PUPPET', 'file_path': 'own.puppet'}
    manager.layer_settings['peer'] = {'type': 'PUPPET', 'file_path': 'own.puppet'}
    widgets = []
    for key, origin in [('pet', (0, 0)), ('pet', (400, 100)), ('peer', (20, 20))]:
        widget = QWidget()
        widget.scene_layer_key, widget.scene_monitor_origin = key, origin
        widget.set_ui_variable = lambda opacity, target=widget: target.setWindowOpacity(opacity)
        widgets.append(widget)
    manager.native_widgets.extend(widgets)
    try:
        manager.synchronize_layers({'pet': {'type': 'PUPPET', 'file_path': 'own.puppet',
                                           'x': 30, 'y': 40, 'opacity': 70},
                                    'peer': {'type': 'PUPPET', 'file_path': 'own.puppet'}})
        assert [(widget.x(), widget.y()) for widget in widgets] == [(30, 40), (430, 140), (20, 20)]
        manager.synchronize_layers({'pet': {'type': 'PUPPET', 'file_path': 'own.puppet', 'visible': False},
                                    'peer': {'type': 'PUPPET', 'file_path': 'own.puppet'}})
        assert not widgets[0].isVisible() and not widgets[1].isVisible() and widgets[2].isVisible()
    finally:
        manager.clear()


def test_async_playback_failure_keeps_old_scene_and_receipts_wait_for_completion(tmp_path):
    page = SceneSettingUI()
    page.actions.deleteLater()
    gate = Event()
    threads = []
    entries = _image_scene(tmp_path)
    def reader(_path):
        threads.append(get_ident())
        assert gate.wait(3)
        return PreparedScene(entries)
    def builder(_entries, _screens):
        raise ValueError('candidate failed')
    actions = SceneActions(page, reader=reader, builder=builder)
    page.actions = actions
    page.visual_editor.document.reset(entries)
    page.scene.add_entry('reference', entries['reference'])
    old_scene, old_list = page.scene.graphic_scene, page.scene.widget_list
    registry = ActionRegistry()
    registry.register(Action('scene_start', 'label', 'Play', actions.request, True, True))
    rules = [{'label': 'Play', 'action': 'scene_start', 'value': 'source.json', 'when': {'apps': 'code'}}]
    service = RuleEngineService(lambda: rules, lambda: {'app': 'code'})
    window = SimpleNamespace(action_registry=registry, rule_engine_service=service)
    service.rule_fired.connect(lambda rule: FrontEngineMainUI._on_rule_fired(window, rule))
    try:
        service.poll_once()
        assert service.history[-1]['status'] == 'dispatched'
        gate.set()
        _wait(lambda: actions.pending is None)
        assert threads[0] != get_ident()
        assert service.history[-1]['status'] == 'failed'
        assert service.history[-1]['error'] == 'candidate failed'
        assert page.scene.graphic_scene is old_scene and page.scene.widget_list is old_list
        assert len(old_list) == 1 and old_list[0].widget() is not None
    finally:
        gate.set()
        page.close()


def test_latest_request_wins_and_stop_cleans_cancelled_package_results(tmp_path):
    page = SceneSettingUI()
    page.actions.deleteLater()
    gate, started = Event(), Event()
    results = []
    path = tmp_path / 'source.fescene'
    save_package(_image_scene(tmp_path), path)
    def reader(_path):
        started.set()
        assert gate.wait(3)
        prepared = read_scene_source(path)
        results.append(prepared)
        return prepared
    actions = SceneActions(page, reader=reader)
    page.actions = actions
    try:
        first = actions.request(str(path), load_only=True)
        assert started.wait(2)
        second = actions.request(str(path), load_only=True)
        third = actions.request(str(path), load_only=True)
        assert first.result is False and second.result is False
        gate.set()
        _wait(lambda: third.result is not None)
        assert third.result is True and len(results) == 2
        assert results[0].lease is None
        resource = Path(actions.prepared.entries['reference']['file_path'])
        assert resource.is_file()
        started.clear()
        gate.clear()
        cancelled = actions.request(str(path))
        assert started.wait(2)
        actions.stop_playback()
        assert cancelled.result is False
        gate.set()
        _wait(lambda: actions.pending is None)
        assert results[-1].lease is None
        assert resource.is_file(), 'the still-editable scene owns its assets'
    finally:
        gate.set()
        page.close()
    assert not resource.exists()


def test_successful_scene_replacement_retains_control_center_lists(tmp_path):
    page = SceneSettingUI()
    page.visual_editor.document.reset(_image_scene(tmp_path))
    lists = [page.scene.widget_list, page.scene.view_list, page.scene.native_widgets]
    try:
        operation = page.actions.request('')
        _wait(lambda: operation.result is not None)
        assert operation.result is True
        assert lists == [page.scene.widget_list, page.scene.view_list, page.scene.native_widgets]
        assert all(old is new for old, new in zip(lists, [page.scene.widget_list, page.scene.view_list,
                                                       page.scene.native_widgets]))
        assert len(lists[0]) == 1 and len(lists[1]) == 1
        page.close_scene()
        assert not any(lists)
        assert page.visual_editor.document.entries
    finally:
        page.close()


def test_target_picker_preserves_optional_scene_targets_and_generates_layer_values():
    from frontengine.ui.dialog.scene_action_dialog import SceneActionDialog
    from frontengine.ui.dialog.rules_dialog import RulesDialog, _COLUMN_ACTION, _COLUMN_VALUE
    dialog = SceneActionDialog('scene_start', '{"path":"","screen":"all"}', {})
    try:
        assert scene_request(dialog.action_value()) == ('', 'all')
    finally:
        dialog.close()
    dialog = SceneActionDialog('layer_position', '', {'title': {'type': 'TEXT', 'x': 24, 'y': 36}})
    try:
        assert layer_changes('layer_position', dialog.action_value()) == ('title', {'x': 24.0, 'y': 36.0})
    finally:
        dialog.close()
    rules = RulesDialog()
    try:
        rules.add_row({'label': 'Play', 'action': 'scene_start', 'value': '{"screen":"all"}'})
        row = rules.table.rowCount() - 1
        assert rules.table.cellWidget(row, _COLUMN_ACTION).currentData() == 'scene_start'
        assert rules.rules()[-1]['value'] == rules.table.item(row, _COLUMN_VALUE).text()
    finally:
        rules.close()


def test_layer_rules_wait_for_preceding_scene_and_failed_load_cannot_mutate_old_content(tmp_path):
    page = SceneSettingUI()
    page.actions.deleteLater()
    gate = Event()
    entries = _image_scene(tmp_path)
    def reader(path):
        assert gate.wait(3)
        if path == 'bad.json':
            raise ValueError('invalid source')
        return PreparedScene(entries)
    actions = SceneActions(page, reader=reader)
    page.actions = actions
    try:
        loading = actions.request('good.json')
        hiding = actions.layer('layer_hide', 'reference')
        assert loading.result is None and hiding.result is None
        gate.set()
        _wait(lambda: hiding.result is not None)
        assert loading.result is True and hiding.result is True
        assert not page.scene.widget_list[0].isVisible()
        gate.clear()
        failing = actions.request('bad.json')
        showing = actions.layer('layer_show', 'reference')
        gate.set()
        _wait(lambda: showing.result is not None)
        assert failing.result is False and showing.result is False
        assert not page.scene.widget_list[0].isVisible()
    finally:
        gate.set()
        page.close()


def test_layers_after_superseding_scene_belong_to_latest_request(tmp_path):
    page = SceneSettingUI()
    page.actions.deleteLater()
    gate, started = Event(), Event()
    def reader(_path):
        started.set()
        assert gate.wait(3)
        return PreparedScene(_image_scene(tmp_path))
    actions = SceneActions(page, reader=reader)
    page.actions = actions
    try:
        first = actions.request('first.json')
        assert started.wait(2)
        old_layer = actions.layer('layer_hide', 'reference')
        latest = actions.request('latest.json')
        latest_layer = actions.layer('layer_position', '{"layer":"reference","x":12,"y":18}')
        assert first.result is False and old_layer.result is False
        gate.set()
        _wait(lambda: latest_layer.result is not None)
        assert latest.result is True and latest_layer.result is True
        assert page.scene.widget_list[0].pos().x() == 12
    finally:
        gate.set()
        page.close()
