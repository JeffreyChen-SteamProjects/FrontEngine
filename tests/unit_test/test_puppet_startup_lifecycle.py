"""Failed native scene starts must release their windows and leave other monitors alone."""
import json
import zipfile

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QWidget

from frontengine.show.scene.scene import SceneManager
from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI


def asset(tmp_path):
    path = tmp_path / "tiny.puppet"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("puppet.json", json.dumps({"version": 1, "size": [16, 16],
                                                   "drawables": [], "deformers": [],
                                                   "parameters": []}))
    return path


@pytest.mark.parametrize("malformed", [False, True])
def test_reference_runtime_script_failure_allocates_no_child_window(tmp_path, malformed):
    pytest.importorskip("Imervue.puppet.document_io")
    from frontengine.show.pet.puppet_pet import PuppetPetWidget
    owner = QWidget()
    script = tmp_path / "lines.petscript.json"
    if malformed:
        script.write_text("{", encoding="utf-8")
    try:
        with pytest.raises(ValueError):
            PuppetPetWidget(asset(tmp_path), parent=owner, script_path=str(script))
        assert owner.children() == []
    finally:
        owner.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_missing_runtime_leaves_no_visible_or_retained_scene_view(tmp_path, monkeypatch):
    from frontengine.show.pet import puppet_pet
    scene = SceneManager()
    scene.add_puppet({"file_path": str(asset(tmp_path))})
    def unavailable():
        raise ValueError("Install frontengine[puppet]")
    monkeypatch.setattr(puppet_pet, "puppet_runtime", unavailable)
    warnings = []
    monkeypatch.setattr("frontengine.ui.page.scene_setting.scene_manager.QMessageBox.warning",
                        lambda *args: warnings.append(args[-1]))
    page = SceneManagerUI(scene)
    try:
        assert page._open_view(None) is False
        assert scene.native_widgets == []
        assert scene.view_list == []
        assert warnings == ["Install frontengine[puppet]"]
    finally:
        for view in scene.view_list:
            view.close()
        scene.clear()
        page.close()


def test_partial_native_failure_rolls_back_only_current_monitor(monkeypatch):
    scene = SceneManager()
    previous_native, previous_view, newly_started = QWidget(), QWidget(), QWidget()
    previous_native.show()
    previous_view.show()
    scene.native_widgets.append(previous_native)
    scene.view_list.append(previous_view)
    def partial(_monitor):
        scene.native_widgets.append(newly_started)
        newly_started.show()
        raise ValueError("second puppet failed")
    monkeypatch.setattr(scene, "open_native_widgets", partial)
    monkeypatch.setattr("frontengine.ui.page.scene_setting.scene_manager.QMessageBox.warning",
                        lambda *_args: None)
    page = SceneManagerUI(scene)
    try:
        assert page._open_view(None) is False
        assert scene.native_widgets == [previous_native]
        assert scene.view_list == [previous_view]
        assert previous_native.isVisible() and previous_view.isVisible()
        assert not newly_started.isVisible()
    finally:
        for view in scene.view_list:
            view.close()
        scene.clear()
        page.close()


def test_puppet_only_success_opens_native_window_without_empty_graphics_view(monkeypatch):
    scene = SceneManager()
    native = QWidget()
    def start(_monitor):
        scene.native_widgets.append(native)
        native.show()
    monkeypatch.setattr(scene, "open_native_widgets", start)
    page = SceneManagerUI(scene)
    try:
        assert page._open_view(None) is True
        assert native.isVisible()
        assert scene.view_list == []
    finally:
        for view in scene.view_list:
            view.close()
        scene.clear()
        page.close()


def test_real_canvas_left_drag_moves_pet_window(tmp_path):
    pytest.importorskip("Imervue.puppet.document_io")
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from frontengine.show.pet.puppet_pet import PuppetPetWidget
    pet = PuppetPetWidget(asset(tmp_path), size=(128, 192))
    try:
        pet.move(100, 100)
        pet.show()
        QCoreApplication.processEvents()
        before = pet.pos()
        QTest.mousePress(pet.canvas, Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
        QTest.mouseMove(pet.canvas, QPoint(50, 35))
        assert pet.pos() == before + QPoint(40, 25)
        QTest.mouseRelease(pet.canvas, Qt.MouseButton.LeftButton, pos=QPoint(50, 35))
        assert pet._drag_origin is None
    finally:
        pet.close()


@pytest.mark.parametrize("hit_response", [False, True])
def test_hit_signal_plays_linked_motion_toggles_expression_and_selects_script_line(tmp_path, hit_response):
    pytest.importorskip("Imervue.puppet.document_io")
    from Imervue.puppet.document import HitArea, Motion, Expression
    from frontengine.show.pet.puppet_pet import PuppetPetWidget
    script = tmp_path / "lines.petscript.json"
    script.write_text(json.dumps({"greetings": ["generic hello"],
                                  "motion_lines": {"wave": ["wave hello"]},
                                  "hit_responses": {"head": ["head hello"]} if hit_response else {}}),
                      encoding="utf-8")
    pet = PuppetPetWidget(asset(tmp_path), script_path=str(script))
    try:
        document = pet.canvas.document()
        document.motions.append(Motion("wave", 1.0))
        document.expressions.append(Expression("smile"))
        document.hit_areas.append(HitArea("head", [], "wave", "smile"))
        pet.canvas.hit_area_triggered.emit("head")
        assert pet.player.motion().name == "wave"
        assert "smile" in pet.canvas.active_expressions()
        assert pet.bubble.text() == ("head hello" if hit_response else "wave hello")
        pet.canvas.hit_area_triggered.emit("head")
        assert "smile" not in pet.canvas.active_expressions()
    finally:
        pet.close()


def test_hit_without_specific_line_uses_time_of_day_greeting(tmp_path):
    pytest.importorskip("Imervue.puppet.document_io")
    from frontengine.show.pet.puppet_pet import PuppetPetWidget
    script = tmp_path / "lines.petscript.json"
    script.write_text(json.dumps({"greetings": ["generic hello"],
                                  "time_of_day_greetings": {band: ["daily hello"] for band in
                                                            ("morning", "afternoon", "evening", "night")}}),
                      encoding="utf-8")
    pet = PuppetPetWidget(asset(tmp_path), script_path=str(script))
    try:
        pet.canvas.hit_area_triggered.emit("unscripted")
        assert pet.bubble.text() == "daily hello"
    finally:
        pet.close()
