"""Geometry edits, legacy preservation, undo and portable scene round trips."""
import copy

import pytest

from frontengine.utils.scene_format.scene_editor_document import SceneEditorDocument
from frontengine.utils.scene_format.scene_package import save_package, load_package


def test_undo_and_redo_preserve_all_legacy_fields():
    document = SceneEditorDocument()
    legacy = {"old": {"type": "TEXT", "text": "Hello", "custom": {"keep": True}}}
    document.reset(legacy)
    document.update("old", {"x": 25, "width": 400})
    assert document.entries["old"]["custom"] == {"keep": True}
    document.undo.undo()
    assert document.entries == legacy
    document.undo.redo()
    assert document.entries["old"]["x"] == 25
    legacy["old"]["custom"]["keep"] = False
    assert document.entries["old"]["custom"]["keep"]


def test_add_duplicate_remove_and_alignment_are_undoable():
    document = SceneEditorDocument()
    first = document.add({"type": "TEXT", "text": "Hello"})
    second = document.duplicate(first)
    assert document.entries[second]["x"] == 20
    document.update(first, {"locked": True})
    document.align([first, second], "right", (1000, 600))
    assert document.entries[first]["x"] == 0
    assert document.entries[second]["x"] == 680
    document.remove(second)
    document.undo.undo()
    assert second in document.entries


@pytest.mark.parametrize("change", [{"x": float("nan")}, {"width": 0}, {"height": 100000},
                                   {"opacity": 101}, {"scale": -1}, {"locked": 1}, {"visible": "yes"}])
def test_invalid_geometry_never_changes_document(change):
    document = SceneEditorDocument()
    key = document.add({"type": "TEXT", "text": "Safe"})
    before = copy.deepcopy(document.entries)
    with pytest.raises(ValueError):
        document.update(key, change)
    assert document.entries == before
    assert document.undo.count() == 1


def test_editor_transforms_survive_package_export_and_playback(tmp_path):
    from frontengine.show.scene.scene import SceneManager
    document = SceneEditorDocument()
    key = document.add({"type": "TEXT", "text": "Portable", "font_size": 24,
                        "width": 300, "height": 100, "scale": 1.5, "rotation": 15})
    document.update(key, {"x": 40, "y": 60})
    source = tmp_path / "edited.fescene"
    save_package(document.entries, source)
    entries, lease = load_package(source)
    scene = SceneManager()
    try:
        proxy = scene.add_text(entries[key])
        assert proxy.pos().x() == 40 and proxy.pos().y() == 60
        assert proxy.scale() == 1.5 and proxy.rotation() == 15
        assert proxy.widget().size().width() == 300
        assert not proxy.widget().output_frame().isNull()
    finally:
        scene.clear()
        lease.cleanup()
