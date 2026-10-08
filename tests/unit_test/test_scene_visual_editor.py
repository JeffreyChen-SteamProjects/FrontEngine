"""GUI/document synchronization and grouped canvas edits."""
import json

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QImage

from frontengine.ui.page.scene_setting.scene_setting_ui import SceneSettingUI
from frontengine.user_setting.scene_setting import scene_json


def make_page():
    scene_json.clear()
    return SceneSettingUI()


def test_visual_editor_and_json_apply_share_scene_without_recursive_resets():
    page = make_page()
    editor, manager = page.visual_editor, page.scene_manager_ui
    key = editor.document.add({"type": "TEXT", "text": "Hello"})
    editor.document.update(key, {"x": 25})
    assert scene_json[key]["x"] == 25
    assert editor.document.undo.count() == 2
    assert json.loads(manager.json_plaintext.toPlainText())[key]["text"] == "Hello"
    editor.document.undo.undo()
    assert scene_json[key]["x"] == 0
    manager.json_plaintext.setPlainText('{"imported":{"type":"TEXT","text":"JSON"}}')
    manager.apply_json()
    assert editor.document.entries == scene_json
    assert editor.document.undo.count() == 0
    assert editor.layers.count() == 1
    manager.clear_json()
    assert not editor.document.entries and editor.layers.count() == 0
    page.close()


def test_group_drag_and_lock_preserve_positions_and_undo():
    page = make_page()
    editor = page.visual_editor
    first = editor.document.add({"type": "TEXT", "text": "First"})
    second = editor.document.add({"type": "TEXT", "text": "Second"})
    for item in editor.canvas.items():
        item.setSelected(True)
        item.moveBy(20, 40)
    editor.commit_canvas()
    assert editor.document.entries[first]["x"] == editor.document.entries[second]["x"] == 20
    editor.document.undo.undo()
    assert editor.document.entries[first]["x"] == editor.document.entries[second]["x"] == 0
    editor.document.update(first, {"locked": True})
    item = next(item for item in editor.canvas.items() if item.key == first)
    assert not item.flags() & item.GraphicsItemFlag.ItemIsMovable
    item.setSelected(True)
    item.moveBy(100, 100)
    editor.commit_canvas()
    assert editor.document.entries[first]["x"] == 0
    page.close()


def test_properties_resize_and_hide_are_undoable():
    page = make_page()
    editor = page.visual_editor
    key = editor.document.add({"type": "TEXT", "text": "First"})
    editor.layers.item(0).setSelected(True)
    editor.fields["width"].setValue(600)
    editor.visible.setChecked(False)
    editor._apply_properties()
    assert scene_json[key]["width"] == 600
    assert not scene_json[key]["visible"]
    editor.document.undo.undo()
    assert scene_json[key]["width"] == 320 and scene_json[key]["visible"]
    page.close()


def test_static_image_preview_does_not_open_overlay_windows(tmp_path):
    page = make_page()
    editor = page.visual_editor
    image = QImage(40, 30, QImage.Format.Format_RGB32)
    image.fill(Qt.GlobalColor.blue)
    path = tmp_path / "reference.png"
    assert image.save(str(path))
    key = editor.document.add({"type": "IMAGE", "file_path": str(path)})
    item = next(item for item in editor.canvas.items() if item.key == key)
    assert item.image is not None and not item.image.isNull()
    assert page.scene.widget_list == []
    page.show()
    QCoreApplication.processEvents()
    assert not page.grab().isNull()
    page.close()


def test_empty_properties_disabled_and_bad_legacy_font_can_render():
    page = make_page()
    editor = page.visual_editor
    assert all(not field.isEnabled() for field in editor.fields.values())
    key = editor.document.add({"type": "TEXT", "text": "Legacy", "font_size": "invalid"})
    editor._select_layer(key)
    assert editor._selected_keys() == [key]
    page.show()
    QCoreApplication.processEvents()
    assert not editor.view.grab().isNull()
    page.close()
