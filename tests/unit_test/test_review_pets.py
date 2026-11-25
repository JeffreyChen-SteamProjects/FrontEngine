"""Desktop pets: what the whole-project review found."""
import json
import random
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QThreadPool
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox, QWidget

from frontengine.show.pet import asset_library
from frontengine.show.pet.asset_library import MAX_ASSETS, PetAssetLibrary
from frontengine.show.pet.desktop_pet import (
    BEHAVIOUR_CHASE, BEHAVIOUR_FLOOR, BEHAVIOUR_WANDER, SURFACE_FLOOR, SURFACE_LEFT, PetMotion, SpeechBubble,
)
from frontengine.show.pet.focus_companions import FocusCompanions, _Participant
from frontengine.ui.dialog.pet_asset_install import PetAssetInstall
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_chat.pet_chat_service import REQUEST_SECONDS, PetChatService
from frontengine.utils.pet_pack.layered import load_layered_asset

BOUNDS = (0, 0, 1920, 1031)


def _motion(**named):
    return PetMotion(300, 400, 128, 128, BOUNDS, rng=random.Random(3), **named)


@pytest.mark.parametrize("velocity", [(0.0, 0.0), (0.0, 12.0), (0.0, -3.0)])
def test_a_pet_let_go_below_the_floor_lands_on_it(velocity):
    motion = _motion()
    motion.y = 1068.0 - motion.height
    motion.throw(*velocity)
    for _step in range(300):
        motion.step()
    assert motion.y + motion.height == pytest.approx(1031, abs=1) and not motion._airborne


def test_a_pet_that_grows_in_mid_air_still_lands():
    motion = _motion()
    motion.y = 890.0
    motion.throw(0.0, 5.0)
    motion.height = 192
    for _step in range(300):
        motion.step()
    assert motion.y + motion.height == pytest.approx(1031, abs=1)


def test_following_from_a_wall_lets_go_and_falls_instead_of_jumping_to_the_floor():
    motion = _motion(climb=True)
    motion.surface, motion.x, motion.y = SURFACE_LEFT, 0.0, 400.0
    motion.follow_target_x = 600.0
    before = motion.y
    motion.step()
    assert motion.surface == SURFACE_FLOOR and abs(motion.y - before) < 60
    for _step in range(600):
        motion.step()
        if motion.follow_target_x is None:
            break
    assert motion.follow_target_x is None and motion.y + motion.height == pytest.approx(1031, abs=1)


@pytest.mark.parametrize("behaviour", [BEHAVIOUR_WANDER, BEHAVIOUR_CHASE])
def test_changing_behaviour_on_a_wall_gets_off_it(behaviour):
    motion = _motion(climb=True)
    motion.surface, motion._airborne = SURFACE_LEFT, True
    motion.behaviour = behaviour
    assert motion.surface == SURFACE_FLOOR and not motion._airborne
    motion.surface = SURFACE_LEFT
    motion.behaviour = BEHAVIOUR_FLOOR
    assert motion.surface == SURFACE_LEFT                # still a floor pet: it may go on climbing


def test_a_bubble_is_as_tall_as_what_it_says_and_stays_on_screen():
    from PySide6.QtGui import QFontMetrics
    bubble, anchor = SpeechBubble(), QWidget()
    anchor.setGeometry(10, 0, 64, 64)
    anchor.show()
    text = "A longer answer that takes more than one line, and then another sentence to be sure of it. " * 2
    bubble.show_message(text, anchor)
    needed = QFontMetrics(bubble._font).boundingRect(0, 0, bubble.width() - 18, 4000, 0x1000 | 0x84, text).height()
    assert bubble.height() >= needed + 4 and bubble.width() <= SpeechBubble.MAX_WIDTH
    area = anchor.screen().availableGeometry()
    assert area.contains(bubble.geometry())
    bubble.show_message("Hi", anchor)
    assert bubble.height() == 44
    bubble.close()
    anchor.close()


def _asset(folder, identifier="one", **changes):
    folder.mkdir(parents=True)
    from PySide6.QtGui import QColor, QImage
    image = QImage(16, 16, QImage.Format.Format_ARGB32)
    image.fill(QColor("red"))
    image.save(str(folder / "a.png"))
    frame = {"duration_ms": 100, "anchors": {}, "layers": [{"image": "a.png", "z": 0, "anchor": None, "offset": [0, 0]}]}
    manifest = {"format": "frontengine.layered-pet/1", "id": identifier, "version": "1", "name": "One",
                "kind": "character", "template": "t", "canvas": [16, 16], "slots": [],
                "actions": {"idle": {"loop": True, "frames": [frame]}}, "license": "CC0-1.0", **changes}
    (folder / "layered-pet.json").write_text(json.dumps(manifest), encoding="utf-8")
    return folder


@pytest.mark.parametrize("image", [["a.png"], {}, None, 3])
def test_a_layer_whose_image_is_no_name_is_refused(tmp_path, image):
    layer = {"image": image, "z": 0, "anchor": None, "offset": [0, 0]}
    folder = _asset(tmp_path / "a", actions={"idle": {"loop": True, "frames": [{"duration_ms": 100, "anchors": {}, "layers": [layer]}]}})
    with pytest.raises(ValueError):
        load_layered_asset(folder)


def test_a_manifest_nested_too_deeply_is_refused_and_the_installer_answers(tmp_path):
    folder = tmp_path / "deep"
    folder.mkdir()
    (folder / "layered-pet.json").write_text("[" * 60000, encoding="utf-8")
    with pytest.raises(ValueError):
        load_layered_asset(folder)

    class Library:
        @staticmethod
        def install(_source, cancel=None):
            raise TypeError("unhashable")
    answers, job = [], PetAssetInstall(Library, folder)
    job.setAutoDelete(False)
    job.signals.finished.connect(answers.append)
    QThreadPool.globalInstance().start(job)
    for _try in range(200):
        if answers:
            break
        QTest.qWait(10)
    assert answers == ["unhashable"]


def test_looking_through_the_library_again_reads_only_what_changed(tmp_path, monkeypatch):
    library, loads = PetAssetLibrary(tmp_path / "lib"), []
    real = asset_library.load_layered_asset
    folders = []
    library.root.mkdir()
    for name in ("one", "two"):
        target = library.root / library._folder(SimpleNamespace(identifier=name, version="1"))
        folders.append(target)
        try:
            real(_asset(target, name))
        except ValueError as error:
            pytest.skip(f"the sample asset does not match the format: {error}")
    monkeypatch.setattr(asset_library, "load_layered_asset", lambda folder: loads.append(folder) or real(folder))
    library.scan()
    library.scan()
    assert len(loads) == 2
    manifest = folders[0] / "layered-pet.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    manifest.write_text(json.dumps({**data, "name": "Another name"}), encoding="utf-8")
    catalog, _errors = library.scan()
    assert len(loads) == 3 and catalog.resolve({"id": "one", "version": "1"}, "character").name == "Another name"


def test_the_library_holds_every_built_in_version_many_times_over():
    assert MAX_ASSETS >= 264 * 8


def test_a_question_without_an_answer_is_not_asked_again_with_the_next():
    asked, answers = [], iter([RuntimeError("down"), "", "Hello"])

    class Messages:
        @staticmethod
        def create(**named):
            asked.append([entry["content"] for entry in named["messages"]])
            answer = next(answers)
            if isinstance(answer, Exception):
                raise answer
            return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=answer)])
    service = PetChatService(client_factory=lambda: SimpleNamespace(messages=Messages))
    assert service.ask("first") is None
    service.ask("second")
    assert service.ask("third") == "Hello"
    assert asked == [["first"], ["second"], ["third"]]
    assert [entry["content"] for entry in service.history] == ["third", "Hello"]


def test_a_chat_request_gives_up_in_time_to_close(monkeypatch):
    made = {}
    anthropic = SimpleNamespace(Anthropic=lambda **named: made.update(named) or SimpleNamespace())
    monkeypatch.setitem(__import__("sys").modules, "anthropic", anthropic)
    PetChatService(key_provider=lambda: "key")._build_client()
    assert made["timeout"] == REQUEST_SECONDS <= 60 and made["max_retries"] <= 1


class _Session:
    def __init__(self, action):
        self._closed, self.mode_revision = False, 4
        self.companion = SimpleNamespace(action=action, mode="work")

    def set_mode(self, mode):
        self.companion.mode = mode
        self.mode_revision += 1


@pytest.mark.parametrize("action", [None, "groom"])
def test_a_pet_busy_as_focus_ends_goes_back_to_what_it_did(action, monkeypatch):
    monkeypatch.setattr("frontengine.show.pet.focus_companions.restore_placement", lambda *_arguments: None)
    companions, pet = FocusCompanions(), SimpleNamespace(profile_session=_Session(action))
    companions._participants = [_Participant(pet, "play", 4)]
    companions.stop()
    assert pet.profile_session.companion.mode == "play"
    chosen = SimpleNamespace(profile_session=_Session(action))
    companions._participants = [_Participant(chosen, "play", 3)]          # changed by hand meanwhile
    companions.stop()
    assert chosen.profile_session.companion.mode == "work"


def test_identities_can_be_deleted_but_never_a_live_one(make_main_window, monkeypatch):
    window = make_main_window()
    controls = window.pet_setting_ui.profile_controls
    record = controls.profiles.create("Extra")
    controls.refresh(selected=record["id"])
    asked = []
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *_arguments: asked.append(True) or QMessageBox.StandardButton.No))
    controls.delete_button.click()
    assert asked and controls.profiles.get(record["id"])
    from frontengine.ui.page.pet import pet_profile_controls as module
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *_arguments: QMessageBox.StandardButton.Yes))
    with monkeypatch.context() as live:
        live.setattr(module.PetProfileSession, "active", staticmethod(lambda *_arguments: object()))
        controls.delete_selected()
        assert controls.profiles.get(record["id"]) and controls.status.text()
    controls.delete_selected()
    with pytest.raises(ValueError):
        controls.profiles.get(record["id"])
    assert controls.selector.findData(record["id"]) < 0
    controls.selector.setCurrentIndex(0)
    assert not controls.delete_button.isEnabled()


def test_deleting_an_identity_frees_its_place():
    profiles = PetProfiles({}, lambda: None)
    first = profiles.create("A")
    profiles.delete(first["id"])
    assert profiles.profiles() == []
    with pytest.raises(ValueError):
        profiles.delete(first["id"])


def test_a_clone_that_never_came_leaves_no_identity(make_main_window, monkeypatch):
    page = make_main_window().pet_setting_ui
    source = page.profile_controls.profiles.create("Source")
    count = len(page.profile_controls.profiles.profiles())

    def fails(*_arguments, **_named):
        raise ValueError("no character")
    monkeypatch.setattr(page, "_spawn_profile_pet", fails)
    page._spawn_pet(source)
    assert len(page.profile_controls.profiles.profiles()) == count


def test_a_built_in_chosen_for_one_pet_does_not_dress_another(make_main_window, monkeypatch):
    page = make_main_window().pet_setting_ui
    controls = page.profile_controls
    rex = controls.profiles.create("Rex")
    own = {"id": "ink", "version": "1"}
    real = controls.profiles.get
    monkeypatch.setattr(controls.profiles, "get", lambda key: {**real(key), "appearance": {"character": own}})
    monkeypatch.setattr(page, "_resolves", lambda _reference: True)
    controls.refresh()
    controls.selector.setCurrentIndex(0)
    page._choose_character("mochi")
    assert page._wanted_character(None, returning=False, source_pet=None) == "mochi"
    assert page._wanted_character(rex["id"], returning=False, source_pet=None) is None
    controls.refresh(selected=rex["id"])
    page._choose_character("mochi")                      # chosen with Rex selected: meant for Rex
    assert page._wanted_character(rex["id"], returning=False, source_pet=None) == "mochi"


def test_settling_while_typing_is_part_of_a_preset_and_scripts_must_be_names(make_main_window):
    page = make_main_window().pet_setting_ui
    page.settle_typing_checkbox.setChecked(True)
    state = page.get_state()
    page.settle_typing_checkbox.setChecked(False)
    page.set_state(state)
    assert page.settle_typing_checkbox.isChecked()
    page.set_state({"puppet_script": ["not", "a", "name"], "settle_typing": False})
    assert page.puppet_script_path is None


def test_closing_gives_up_on_wardrobes_being_drawn(make_main_window, monkeypatch):
    page = make_main_window().pet_setting_ui
    rejected = []
    monkeypatch.setattr(page.profile_controls, "open_wardrobes",
                        lambda: [SimpleNamespace(reject=lambda: rejected.append(True))])
    page.stop_asset_preparation()
    assert rejected == [True]


def test_a_look_from_an_older_version_takes_the_current_one_with_the_new_clothes(monkeypatch):
    from frontengine.show.pet.inkside.library import VERSION, builtin_identifiers, upgrade_builtin
    from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog
    old = {"character": {"id": sorted(builtin_identifiers())[0], "version": "1"}, "equipped": {}, "colors": {}}
    if upgrade_builtin(old) is None:
        pytest.skip("no older built-in version")
    staged = []
    dialog = SimpleNamespace(draft=SimpleNamespace(appearance=old, replace_appearance=staged.append),
                             _attempt=lambda operation: operation())
    PetWardrobeDialog._upgrade_look(dialog)
    assert staged[0]["character"]["version"] == VERSION
