"""The strip's collapsible toolbar, care from the player, and the richer right-click menus."""
import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.home_strip import piece_lines
from frontengine.ui.page.pet_game.home_page import PetHomePage
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.world import INTERACT_COOLDOWN_MS, World

CATALOG = builtin_catalog()
PET = "b" * 32


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    for key, value in (("pet_home_running", False), ("pet_home_on_desktop", True), ("pet_home_layer", "top"),
                       ("pet_home_toolbar_open", False), ("pet_home_toolbar_dock", "left")):
        monkeypatch.setitem(user_setting_dict, key, value)


@pytest.fixture
def page(tmp_path, *, home_store_factory, lifetime_factory):
    lifetime_factory()
    service = HomeService(None, home_store_factory(tmp_path, CATALOG), PetProfiles({}, lambda: None))
    widget = PetHomePage(service, lifetime=lifetime_factory())
    widget.create_home()
    # creating a home with no pets brings a first one
    yield widget
    widget.shutdown()
    widget.deleteLater()


def _world():
    world = World(CATALOG, "a" * 32, seed=2)
    zone = world.add_zone("s", 0, 0, 30)
    world.add_resident({"id": PET, "name": "Mochi", "mood": 50, "fullness": 50, "affection": 1, "energy": 60}, zone)
    return world


def test_care_lifts_needs_once_per_cooldown_and_never_for_parked_pets():
    world = _world()
    pet = world.residents[PET]
    assert world.interact(PET, "feed") == "accepted"
    assert pet.needs["fullness"] == 65
    assert world.interact(PET, "feed") == "too_soon"
    assert world.interact(PET, "pat") == "accepted"                # another kind has its own cooldown
    assert pet.affection == 2
    world.time_ms += INTERACT_COOLDOWN_MS
    assert world.interact(PET, "feed") == "accepted"
    assert world.interact(PET, "dance") == "unknown"
    world.park(PET, True)
    assert world.interact(PET, "talk") == "parked"


def test_the_toolbar_opens_docks_and_is_remembered(page):
    strip = page.strip_list[0]
    assert strip.info.isHidden()
    strip.toggle.click()
    assert user_setting_dict["pet_home_toolbar_open"] is True
    assert not strip.info.isHidden()
    assert "coins" in strip.info.text()
    assert strip.toolbar.x() > strip.button.x()
    strip.set_dock("right")
    assert user_setting_dict["pet_home_toolbar_dock"] == "right"
    assert strip.button.geometry().right() > strip.toolbar.geometry().right()
    assert strip.interactive_region().contains(strip.toolbar.geometry().center())


def test_toolbar_shortcuts_reach_the_page(page):
    strip = page.strip_list[0]
    strip.set_toolbar_open(True)
    opened = []
    page.open_requested.connect(lambda: opened.append(True))
    work = next(button for button in strip.shortcut_buttons if button.text() == "Work")
    work.click()
    assert opened
    assert page.tabs.keys()[page.tabs.currentIndex()] == "pet_home_work_section"
    arrange = next(button for button in strip.shortcut_buttons if button.text() == "Arrange")
    arrange.click()
    assert page.layout_panel.arranging


def test_right_click_on_a_pet_offers_care_and_follow(page):
    strip = page.strip_list[0]
    world = page.service.world
    resident = next(iter(world.residents.values()))
    center = strip.resident_center(resident)
    point = QPointF(center)
    strip.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, point, point, Qt.MouseButton.RightButton,
                                      Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier))
    actions = {action.text(): action for action in strip.last_menu.actions()}
    assert {"Feed", "Pat", "Talk", "Ask to", "Wardrobe…", "Work for this pet…"} <= set(actions)
    before = resident.needs["social"]
    actions["Talk"].trigger()
    assert resident.needs["social"] > before
    actions["Follow in the overview"].trigger()
    assert page.followed == resident.identifier
    assert page.selected_resident == resident.identifier
    strip.last_menu.close()


def test_a_piece_menu_says_what_it_is_for_and_moves_it(page):
    world = page.service.world
    piece = next(p for p in world.furniture.values() if p.definition == "desk_basic")
    lines = piece_lines(world, piece)
    assert lines[1] == "For: Writing"
    assert lines[2] == "Nobody is using it"
    page.strip_list[0].action_requested.emit("move", piece.identifier)
    assert page.layout_panel.arranging
    assert page.selected_furniture == piece.identifier
