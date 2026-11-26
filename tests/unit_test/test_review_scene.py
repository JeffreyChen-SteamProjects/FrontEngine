"""Scenes, whiteboard, assets and Workshop: what the whole-project review found."""
import json
import zipfile
from threading import Event

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox

from frontengine.show.scene.model_asset import model_dependencies
from frontengine.show.scene.timeline import SceneTimeline
from frontengine.ui.page.scene_setting.scene_actions import _SceneRead, _SceneSignals
from frontengine.ui.page.scene_setting.scene_setting_ui import SceneSettingUI
from frontengine.user_setting import scene_setting
from frontengine.user_setting.scene_setting import current_scene_document, scene_json
from frontengine.utils.asset_library.inspect import read_scene
from frontengine.utils.asset_library.references import rewrite_scene
from frontengine.utils.scene_format.scene_3d_document import make_3d_scene, read_scene_document
from frontengine.utils.scene_format.scene_document import resolve_asset, scene_envelope
from frontengine.utils.scene_format.scene_editor_document import validate_geometry
from frontengine.utils.scene_format.scene_package import load_package, save_package
from frontengine.utils.workshop.workshop_content import classify_item
from frontengine.utils.workshop.workshop_manifest import is_legacy_preset, read_manifest
from frontengine.utils.workshop.workshop_subscriptions import WorkshopSubscriptions

DEEP = "[" * 60000
HUGE = 10 ** 400


def _picture(path):
    image = QImage(1000, 700, QImage.Format.Format_RGB32)
    image.fill(QColor("red"))
    image.save(str(path))
    return str(path)


@pytest.fixture
def page(*, lifetime_factory):
    scene_json.clear()
    scene_setting.adopt_scene_document({})
    page = SceneSettingUI(lifetime=lifetime_factory())
    yield page
    page.close()
    scene_setting.adopt_scene_document({})


def test_a_workshop_item_nested_too_deeply_is_skipped(tmp_path):
    (tmp_path / "preset.json").write_text(DEEP, encoding="utf-8")
    assert is_legacy_preset(tmp_path / "preset.json") is False and classify_item(tmp_path) is None
    (tmp_path / "workshop.json").write_text(DEEP, encoding="utf-8")
    with pytest.raises(ValueError):
        read_manifest(tmp_path)
    assert classify_item(tmp_path) is None


@pytest.mark.parametrize("error", [KeyError("file_path"), TypeError("x"), AttributeError("n_frames"), OverflowError("big")])
def test_a_scene_that_fails_in_any_way_is_answered(error):
    answers, signals = [], _SceneSignals()
    signals.finished.connect(lambda result, text: answers.append((result, text)), Qt.ConnectionType.DirectConnection)

    def fails():
        raise error
    _SceneRead(fails, Event(), signals).run()
    assert len(answers) == 1 and answers[0][0] is None and answers[0][1]


def test_numbers_too_long_to_be_numbers_are_refused():
    with pytest.raises(ValueError):
        validate_geometry({"a": {"type": "TEXT", "text": "x", "x": HUGE}})
    document = make_3d_scene({}).envelope()
    document["entries"]["m"] = {"type": "MODEL", "file_path": None}
    with pytest.raises(ValueError):
        read_scene_document(document)
    document["entries"]["m"] = {"type": "CUBE", "transform": {"position": [HUGE, 0, 0]}}
    with pytest.raises(ValueError):
        read_scene_document(document)


def _until(condition):
    for _try in range(400):
        if condition():
            return True
        QTest.qWait(10)
    return False


def test_playing_keeps_the_undo_history_and_later_edits(page):
    document = page.visual_editor.document
    key = document.add({"type": "TEXT", "text": "before"})
    document.update(key, {"x": 5})
    steps = document.undo.count()
    operation = page.actions.request_entries(json.loads(page.scene_manager_ui.json_plaintext.toPlainText()))
    document.update(key, {"x": 77})                      # while it is being prepared
    assert _until(lambda: operation.result is not None) and operation.result
    assert document.entries[key]["x"] == 77 and document.undo.count() == steps + 1
    operation = page.actions.request_entries({"t": {"type": "TEXT", "text": "template"}})
    assert _until(lambda: operation.result is not None) and operation.result
    assert list(document.entries) == ["t"]               # a template is still taken into the editor


def test_adding_a_layer_never_replaces_one(page):
    from frontengine.ui.page.scene_setting.scene_page.base_scene_page import BaseSceneSettingUI
    tab = next(child for child in page.findChildren(BaseSceneSettingUI))
    scene_json.clear()
    scene_json.update({"1": {"type": "TEXT", "text": "kept"}})
    tab._append_scene({"type": "TEXT", "text": "new"})
    assert scene_json["1"]["text"] == "kept" and len(scene_json) == 2


def test_2d_json_applied_over_a_3d_scene_makes_a_scene_that_opens(page):
    scene_setting.adopt_scene_document(make_3d_scene({}))
    manager = page.scene_manager_ui
    manager.json_plaintext.setPlainText('{"a": {"type": "TEXT", "text": "flat"}}')
    manager.apply_json()
    document = current_scene_document()
    assert document.mode == "2d" and list(document.entries) == ["a"]
    read_scene_document(document.envelope())


def test_touching_a_layer_changes_nothing_it_did_not_change(page, tmp_path):
    editor = page.visual_editor
    key = editor.document.add({"type": "IMAGE", "file_path": _picture(tmp_path / "a.png")})
    scene_json[key] = {"type": "IMAGE", "file_path": str(tmp_path / "a.png")}          # as added from its own tab
    editor.document.reset(current_scene_document())
    editor._select_layer(key)
    before, steps = dict(editor.document.entries[key]), editor.document.undo.count()
    editor.commit_canvas()
    editor._apply_properties()
    after = editor.document.entries[key]
    assert after == before and editor.document.undo.count() == steps
    item = next(item for item in editor.canvas.items() if item.key == key)
    item.setPos(QPointF(30, 40))
    item.setSelected(True)
    editor.commit_canvas()
    after = editor.document.entries[key]
    assert (after["x"], after["y"]) == (30, 40) and "width" not in after
    editor._select_layer(key)
    editor.fields["scale"].setValue(2)
    editor._apply_properties()
    after = editor.document.entries[key]
    assert after["scale"] == 2 and "opacity" not in before and "opacity" not in after


def test_a_3d_value_finer_than_the_field_is_kept(page):
    scene_setting.adopt_scene_document(make_3d_scene({"c": {"type": "CUBE", "transform": {"scale": [.0005, 1, 1]}}}))
    page.visual_editor.document.reset(current_scene_document())
    editor = page.visual_editor.editor3d
    editor.select(["c"])
    editor.fields["position_x"].setValue(3)
    editor._apply()
    transform = page.visual_editor.document.entries["c"]["transform"]
    assert transform["position"][0] == 3 and transform["scale"][0] == .0005


def test_a_time_being_typed_is_left_alone(page, monkeypatch):
    from types import SimpleNamespace
    editor = page.visual_editor.editor3d
    editor.runtime = SimpleNamespace(timeline=SimpleNamespace(position=1.0))
    monkeypatch.setattr(editor.position, "hasFocus", lambda: True)
    editor.position.setMaximum(100)
    editor.position.setValue(2.5)
    editor._refresh()
    assert editor.position.value() == 2.5
    monkeypatch.setattr(editor.position, "hasFocus", lambda: False)
    editor._refresh()
    assert editor.position.value() == 1.0
    editor.runtime = None


def test_a_scene_that_cannot_be_saved_says_so(page, monkeypatch, tmp_path):
    told = []
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *arguments: told.append(arguments[-1])))
    monkeypatch.setattr(scene_setting.QFileDialog, "getSaveFileName", lambda *_a, **_k: (str(tmp_path / "a.fescene"), ""))
    scene_setting.adopt_scene_document({"a": {"type": "IMAGE", "file_path": str(tmp_path / "gone.png")}})
    scene_setting.write_scene_file(page.scene_manager_ui)
    assert _until(lambda: told)
    scene_setting.adopt_scene_document({"a": {"type": "TEXT", "text": "x"}})
    scene_setting.write_scene_file(page.scene_manager_ui)
    assert _until((tmp_path / "a.fescene").is_file) and len(told) == 1


def test_a_scene_file_is_opened_off_the_gui_thread_and_a_bad_one_says_so(page, monkeypatch, tmp_path):
    from frontengine.ui.page.scene_setting import scene_manager
    told = []
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *arguments: told.append(arguments[-1])))
    save_package({"opened": {"type": "TEXT", "text": "x"}}, tmp_path / "good.fescene")
    monkeypatch.setattr(scene_manager, "choose_scene_file", lambda _ui: str(tmp_path / "good.fescene"))
    page.scene_manager_ui.update_scene_json()
    assert "opened" not in scene_json                    # still being read
    assert _until(lambda: "opened" in scene_json) and "opened" in page.scene_manager_ui.json_plaintext.toPlainText()
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    monkeypatch.setattr(scene_manager, "choose_scene_file", lambda _ui: str(tmp_path / "bad.json"))
    page.scene_manager_ui.update_scene_json()
    assert _until(lambda: told) and "opened" in scene_json


def test_a_package_names_its_files_the_same_on_every_system(tmp_path):
    save_package({"a": {"type": "IMAGE", "file_path": _picture(tmp_path / "a.png")}}, tmp_path / "s.fescene")
    with zipfile.ZipFile(tmp_path / "s.fescene") as archive:
        stored = json.loads(archive.read("scene.json"))["entries"]["a"]["file_path"]
        assert "\\" not in stored and stored in archive.namelist()
    entries, lease = load_package(tmp_path / "s.fescene")
    assert entries["a"]["file_path"].endswith("a.png")
    lease.cleanup()
    assert scene_envelope({"a": {"type": "IMAGE", "file_path": "x/y.png"}})["entries"]["a"]["file_path"] == "x/y.png"
    assert resolve_asset("assets/a.png", None) == "assets/a.png"


def test_the_whiteboard_can_be_saved_however_it_was_moved_and_clicks_are_not_undo_steps(*, lifetime_factory):
    from frontengine.show.canvas.whiteboard_widget import WhiteboardWidget
    board = WhiteboardWidget("#ff0000", 4, lifetime=lifetime_factory())
    board.resize(400, 300)
    board.show()
    for _turn in range(30):
        board.zoom_at(QPoint(10, 10), .8)
    board.pan(90_000, 0)
    for _turn in range(60):
        board.zoom_at(QPoint(390, 290), 1.3)
    assert all(abs(value) <= 100_000 for value in board.offset)
    board.reset_view()
    board.begin_stroke(QPoint(50, 50))
    board.extend_stroke(QPoint(90, 90)) if hasattr(board, "extend_stroke") else None
    board.end_stroke() if hasattr(board, "end_stroke") else None
    checkpoints = []
    board.document.checkpoint = lambda: checkpoints.append(True)
    board.select_mode = True
    board.select_at = lambda *_arguments, **_named: board.selected.__class__
    board.selected = {0} if isinstance(board.selected, set) else [0]
    moved = []
    board.move_selected = lambda dx, dy: moved.append((dx, dy))
    for _click in range(5):
        QTest.mouseClick(board, Qt.MouseButton.LeftButton, pos=QPoint(60, 60))
    assert checkpoints == []
    QTest.mousePress(board, Qt.MouseButton.LeftButton, pos=QPoint(60, 60))
    QTest.mouseMove(board, QPoint(80, 80))
    QTest.mouseMove(board, QPoint(90, 90))
    QTest.mouseRelease(board, Qt.MouseButton.LeftButton, pos=QPoint(90, 90))
    assert len(checkpoints) == (1 if moved else 0)
    board.close()


def test_the_asset_library_knows_3d_scenes(tmp_path):
    document = make_3d_scene({"c": {"type": "CUBE"}}).envelope()
    path = tmp_path / "scene.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    entries, _lease = read_scene(path)
    assert "c" in entries
    picture = _picture(tmp_path / "a.png")
    document["entries"]["i"] = {"type": "IMAGE", "file_path": picture}
    rewritten, where = rewrite_scene(document, picture, str(tmp_path / "b.png"), tmp_path)
    assert where == ["i/file_path"] and rewritten["entries"]["i"]["file_path"].endswith("b.png")
    assert rewritten["mode"] == "3d" and rewritten["camera"] == document["camera"]


def test_one_unreadable_scene_does_not_hide_the_references_in_the_others(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from frontengine.utils.asset_library import references
    picture = _picture(tmp_path / "a.png")
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    (tmp_path / "good.json").write_text(json.dumps({"a": {"type": "IMAGE", "file_path": picture}}), encoding="utf-8")
    monkeypatch.setattr(references, "_source_paths", lambda _repository: [(tmp_path / "bad.json", "scene"),
                                                                         (tmp_path / "good.json", "scene")])
    found = references._reference_only(SimpleNamespace(root=tmp_path), picture, {})
    assert [entry["locations"] for entry in found] == [["a/file_path"]]


@pytest.mark.parametrize("material, texture, statement", [
    ("chair.mtl", "wood.png", "map_Kd wood.png"), ("my chair.mtl", "my wood.png", "map_Kd my wood.png"),
    ("chair.mtl", "textures/wood.png", "map_Kd textures\\wood.png"),
    ("chair.mtl", "wood.png", "map_Kd -s 1 1 1 -clamp on wood.png"), ("chair.mtl", "bump map.png", "bump -bm 0.5 bump map.png")])
def test_ordinary_obj_files_are_accepted(tmp_path, material, texture, statement):
    (tmp_path / texture).parent.mkdir(parents=True, exist_ok=True)
    _picture(tmp_path / texture)
    (tmp_path / material).write_text(f"newmtl Bob's wood\n{statement}\n", encoding="utf-8")
    (tmp_path / "chair.obj").write_text(f"# it's mine\nmtllib {material}\no Bob's chair\nv 0 0 0\n", encoding="utf-8")
    names = {path.relative_to(tmp_path.resolve()).as_posix() for path in model_dependencies(tmp_path / "chair.obj")}
    assert names == {"chair.obj", material, texture}


def test_the_first_keyframes_start_a_scene_already_playing():
    clock = [0.0]
    timeline = SceneTimeline(None, lambda _values: None, clock=lambda: clock[0])
    timeline.active = True
    timeline.configure({"a": {"type": "TEXT", "text": "x"}})
    timeline.play()
    assert not timeline.timer.isActive()
    timeline.configure({"a": {"type": "TEXT", "text": "x", "animation": [{"time": 0, "x": 0}, {"time": 3, "x": 9}]}})
    assert timeline.duration == 3 and timeline.timer.isActive()
    timeline.pause()
    timeline.configure({"a": {"type": "TEXT", "text": "x", "animation": [{"time": 0, "x": 0}, {"time": 4, "x": 9}]}})
    assert not timeline.timer.isActive()


def test_a_layer_resized_while_playing_is_resized_on_screen(tmp_path):
    from frontengine.show.scene.scene import SceneManager
    manager = SceneManager()
    entry = {"type": "IMAGE", "file_path": _picture(tmp_path / "a.png"), "width": 320, "height": 180, "opacity": 100}
    manager.add_entry("a", entry)
    proxy = manager.widget_list[0]
    manager._update_proxy(proxy, {**entry, "width": 640, "height": 360})
    assert (proxy.widget().width(), proxy.widget().height()) == (640, 360)


def test_unchanged_workshop_content_is_not_staged_again():
    from types import SimpleNamespace
    from PySide6.QtCore import QObject, Signal

    class Service(QObject):
        event_received = Signal(object)
        stopping = Signal()
    item = {"id": "456", "path": "somewhere", "state": 5, "timestamp": 10}

    class Jobs(QObject):
        completed = Signal(str, object)
        failed = Signal(str, str)
        submitted = []
        pending = {}

        def submit(self, key, _function):
            self.submitted.append(key)

        def stop(self):
            """Nothing running."""
    service, jobs = Service(), Jobs()
    service.backend = SimpleNamespace(initialized=True, subscribed_items=lambda: [dict(item)])
    subscriptions = WorkshopSubscriptions(service, SimpleNamespace(stage=lambda _item: None), jobs=jobs)
    subscriptions.refresh()
    jobs.completed.emit("456", {"id": "456", "status": "ready", "path": "cache"})
    subscriptions.refresh()
    subscriptions.refresh()
    assert jobs.submitted == ["456"]
    item["timestamp"] = 11
    subscriptions.refresh()
    assert jobs.submitted == ["456", "456"]
    subscriptions.stop()


def test_a_damaged_cached_version_does_not_block_the_next(tmp_path):
    from frontengine.utils.workshop.workshop_cache import WorkshopCache
    source = tmp_path / "steam" / "456"
    source.mkdir(parents=True)
    (source / "preset.json").write_text(json.dumps({"__preset_name__": "one", "image": {}}), encoding="utf-8")
    cache = WorkshopCache(123, tmp_path / "cache")
    item = {"id": "456", "path": str(source), "state": 5, "timestamp": 10}
    first = cache.stage(item)
    for path in list((tmp_path / "cache").rglob("preset.json")):
        path.unlink()
    assert first["status"] == "ready"
    (source / "preset.json").write_text(json.dumps({"__preset_name__": "two", "image": {}}), encoding="utf-8")
    assert cache.stage({**item, "timestamp": 11})["status"] == "ready"
