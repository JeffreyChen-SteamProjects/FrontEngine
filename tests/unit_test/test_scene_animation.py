"""Validated keyframes, shared clocks, reversible preview and composed fades."""
from copy import deepcopy
import json

import pytest
from PySide6.QtCore import QObject, QCoreApplication, QEvent
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QMessageBox
from shiboken6 import isValid

from frontengine.utils.scene_format.scene_animation import sample_animation
from frontengine.utils.scene_format.scene_document import normalize_scene, scene_envelope
from frontengine.show.scene.timeline import SceneTimeline


def animated():
    return {'type': 'TEXT', 'text': 'Animated', 'x': 10, 'y': 20, 'opacity': 100,
            'animation': [{'time': 0, 'x': 0, 'opacity': 0},
                          {'time': 2, 'x': 100, 'opacity': 100, 'easing': 'smooth'},
                          {'time': 4, 'y': 80}]}


@pytest.mark.parametrize('frames', [None, {}, [True], [{'time': 1}],
    [{'time': True, 'x': 1}], [{'time': float('nan'), 'x': 1}],
    [{'time': 3601, 'x': 1}], [{'time': 0, 'x': 100001}],
    [{'time': 0, 'opacity': 101}], [{'time': 0, 'y': float('inf')}],
    [{'time': 0, 'x': 1, 'evil': 2}], [{'time': 0, 'x': 1, 'easing': 'unknown'}],
    [{'time': 1, 'x': 1}, {'time': 1, 'x': 2}], [{'time': i, 'x': 0} for i in range(129)]])
def test_external_animation_rejected_at_scene_boundary(frames):
    with pytest.raises(ValueError):
        normalize_scene({'title': {'type': 'TEXT', 'animation': frames}})


def test_channels_interpolate_independently_and_hold_endpoints():
    entry = animated()
    before = deepcopy(entry)
    assert sample_animation(entry, None) == {'x': 10, 'y': 20, 'opacity': 100}
    assert sample_animation(entry, 0) == {'x': 0, 'y': 20, 'opacity': 0}
    assert sample_animation(entry, 1) == {'x': 50, 'y': 35, 'opacity': 50}
    assert sample_animation(entry, 2)['y'] == 50
    assert sample_animation(entry, 20) == {'x': 100, 'y': 80, 'opacity': 100}
    assert sample_animation(entry, .5)['x'] == 15.625
    assert entry == before


def test_pause_hide_resume_seek_and_replay_use_effective_monotonic_time():
    now, seen = [10.0], []
    owner = QObject()
    timeline = SceneTimeline(owner, seen.append, clock=lambda: now[0])
    timeline.configure({'title': animated()})
    timeline.set_active(True)
    timeline.play()
    now[0] = 11
    timeline.tick()
    assert timeline.position == 1 and seen[-1]['title']['x'] == 50
    timeline.pause()
    now[0] = 111
    timeline.tick()
    assert timeline.position == 1
    timeline.set_active(False)
    timeline.set_active(True)
    assert not timeline.timer.isActive()
    timeline.play()
    now[0] = 112
    timeline.set_active(False)
    assert timeline.position == 2
    now[0] = 212
    timeline.set_active(True)
    now[0] = 213
    timeline.tick()
    assert timeline.position == 3
    timeline.seek(.5)
    assert not timeline.timer.isActive() and seen[-1]['title']['x'] == 15.625
    timeline.play(restart=True)
    assert timeline.position == 0
    now[0] += 10
    timeline.tick()
    assert timeline.position == 4 and timeline.state == 'finished'
    timeline.reset()
    assert seen[-1]['title']['x'] == 10 and not timeline.previewing
    timeline.shutdown()


def test_animation_round_trip_in_json_and_portable_scene(tmp_path):
    from frontengine.utils.scene_format.scene_package import save_package, load_package
    entries = {'title': animated()}
    assert normalize_scene(json.loads(json.dumps(scene_envelope(entries)))) == entries
    path = tmp_path / 'animated.fescene'
    save_package(entries, path)
    loaded, lease = load_package(path)
    try:
        assert loaded == entries
    finally:
        lease.cleanup()


def test_editor_scrub_does_not_save_transient_positions_and_dialog_is_undoable(monkeypatch):
    from frontengine.ui.page.scene_setting.scene_setting_ui import SceneSettingUI
    from frontengine.ui.dialog.scene_animation_dialog import SceneAnimationDialog
    page = SceneSettingUI()
    editor = page.visual_editor
    editor.document.reset({'title': animated()})
    editor._select_layer('title')
    before = deepcopy(editor.document.entries)
    editor.timeline.seek(1)
    item = editor.canvas.items()[0]
    assert item.pos().x() == 50 and item.opacity() == .5
    item.moveBy(999, 999)
    editor.commit_canvas()
    assert editor.document.entries == before and editor.document.undo.count() == 0
    editor.timeline.reset()
    assert item.pos().x() == 10 and item.opacity() == 1
    dialog = SceneAnimationDialog(editor.document, 'title', editor)
    dialog._preset(True)
    assert dialog._frames()[0]['opacity'] == 0
    dialog._apply()
    assert len(editor.document.entries['title']['animation']) == 2
    editor.document.undo.undo()
    assert editor.document.entries == before
    errors = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: errors.append(args[-1]))
    dialog = SceneAnimationDialog(editor.document, 'title', editor)
    dialog.table.item(0, 0).setText('NaN')
    dialog._apply()
    assert errors and editor.document.entries == before
    dialog.close()
    page.close()


def test_shared_playback_clock_retains_no_closed_view_and_crossfade_colors(tmp_path):
    from frontengine.show.scene.scene import SceneManager
    from frontengine.show.scene.compositor_view import SceneCompositorView
    image = QImage(32, 32, QImage.Format.Format_RGBA8888)
    image.fill(QColor('red'))
    path = tmp_path / 'red.png'
    image.save(str(path))
    manager = SceneManager()
    manager.add_entry('image', {'type': 'IMAGE', 'file_path': str(path), 'opacity': 100,
                              'width': 32, 'height': 32})
    first = SceneCompositorView(manager.graphic_scene, 'software')
    second = SceneCompositorView(manager.graphic_scene, 'software')
    first.close()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert not isValid(first)
    previous = QImage(image)
    previous.fill(QColor('blue'))
    second.resize(32, 32)
    second.begin_transition(previous, 1)
    second.timeline.seek(0)
    assert second.output_frame().pixelColor(10, 10) == QColor('blue')
    second.timeline.seek(.5)
    halfway = second.output_frame().pixelColor(10, 10)
    assert 126 <= halfway.red() <= 129 and 126 <= halfway.blue() <= 129 and halfway.alpha() == 255
    second.timeline.seek(1)
    assert second.output_frame().pixelColor(10, 10) == QColor('red')
    assert second.previous_frame.isNull()
    timer = second.timeline.timer
    second.close()
    manager.clear()
    assert not timer.isActive()
