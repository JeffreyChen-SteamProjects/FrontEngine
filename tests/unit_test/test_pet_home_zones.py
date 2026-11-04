"""Zones on several screens, labelled floor areas, transfers and screens that go away."""
import pytest
from PySide6.QtCore import QEvent, QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent

from frontengine.show.pet_game.home_service import HomeService
from frontengine.ui.page.pet_game.home_page import PetHomePage
from frontengine.user_setting.pet_game_save import HomeSaveStore
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_game import behaviour, snapshot
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.layout import Zone
from frontengine.utils.pet_game.world import World

CATALOG = builtin_catalog()
PET = "b" * 32


def _world():
    world = World(CATALOG, "a" * 32, seed=4)
    zone = world.add_zone("left", 0, 0, 40)
    world.grant_starter_kit()
    world.furnish(zone)
    world.add_resident({"id": PET, "name": "Mochi", "mood": 60, "fullness": 60, "affection": 1, "energy": 60}, zone)
    return world, zone


def test_labelling_areas_trims_neighbours_and_survives_a_save():
    world, zone = _world()
    assert world.set_area(zone, 0, 9, "living") == "accepted"
    assert world.set_area(zone, 5, 14, "dining") == "accepted"
    assert world.zones[zone].areas == ((0, 4, "living"), (5, 14, "dining"))
    assert world.set_area(zone, 6, 8, None) == "accepted"
    assert world.zones[zone].areas == ((0, 4, "living"), (5, 5, "dining"), (9, 14, "dining"))
    assert world.set_area(zone, 0, 1, "nonsense") == "unknown"
    loaded = snapshot.from_dict(snapshot.to_dict(world), CATALOG)
    assert loaded.zones[zone].areas == world.zones[zone].areas


def test_overlapping_or_unknown_areas_are_rejected_on_load():
    raw = Zone("z1", "s", 0, 0, 20).to_dict()
    for areas in ([[0, 5, "living"], [4, 8, "work"]], [[0, 5, "party"]], [[5, 2, "work"]], [[0, 99, "work"]]):
        with pytest.raises(ValueError):
            Zone.from_dict({**raw, "areas": areas})


def test_old_saves_load_without_areas():
    world, zone = _world()
    data = snapshot.to_dict(world)
    data["version"] = 3
    for raw in data["zones"]:
        del raw["areas"]
    assert snapshot.from_dict(data, CATALOG).zones[zone].areas == ()


def test_pets_prefer_furniture_inside_a_matching_area():
    world, zone = _world()
    world.ledger.apply("gift", "test", 500)
    world.buy_and_place("snack_bar", zone, "t1")
    snack = next(piece for piece in world.furniture.values() if piece.definition == "snack_bar")
    world.set_area(zone, snack.cell, snack.cell + 1, "dining")
    world.residents[PET].x_milli = 0                                  # the dining table is nearer
    piece, _point = behaviour._free_piece(world, world.residents[PET], "eat")
    assert piece == snack.identifier


def test_moving_a_zone_and_a_pet_between_zones():
    world, zone = _world()
    other = world.add_zone("right", 1920, 0, 30)
    assert world.move_zone(other, "left", 0, 0, 30) == "screen_taken"
    assert world.transfer_resident(PET, other) == "accepted"
    assert world.residents[PET].zone == other
    assert world.transfer_resident(PET, other) == "duplicate"
    stored_before = sum(world.stored(name) for name in CATALOG.furniture)
    assert world.move_zone(zone, "middle", 0, 0, 12) == "accepted"     # narrower: the desk no longer fits
    assert sum(world.stored(name) for name in CATALOG.furniture) > stored_before
    assert world.zones[zone].screen == "middle"


def test_a_missing_screen_parks_its_pets_without_copying_anything():
    world, zone = _world()
    world.park(PET, False)
    furniture = dict(world.furniture)
    assert world.set_offline({zone}) == [PET]
    assert world.residents[PET].parked
    assert world.furniture == furniture
    assert world.set_offline(set()) == [PET]
    assert not world.residents[PET].parked
    world.park(PET, True)                                             # parked on purpose stays parked
    world.set_offline({zone})
    world.set_offline(set())
    assert world.residents[PET].parked


class FakeScreen:
    def __init__(self, name, x):
        self._name, self._x = name, x

    def name(self):
        return self._name

    def availableGeometry(self):
        return QRect(self._x, 0, 1280, 1000)


@pytest.fixture
def page(tmp_path, monkeypatch):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    monkeypatch.setitem(user_setting_dict, "pet_home_running", False)
    monkeypatch.setitem(user_setting_dict, "pet_home_on_desktop", True)
    service = HomeService(None, HomeSaveStore(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    widget = PetHomePage(service)
    widget.resize(1200, 900)
    widget.show()
    widget.create_home()
    yield widget
    widget.shutdown()
    widget.close()
    widget.deleteLater()


def test_a_second_screen_gets_its_own_zone_and_strip(page, monkeypatch):
    first = page.zone
    first_screen = page.service.world.zones[first].screen
    screens = [FakeScreen(first_screen, 0), FakeScreen("second", 1280)]
    monkeypatch.setattr(page, "screens", lambda: screens)
    page.refresh()
    assert page.layout_panel.zone_screens.count() == 1
    page.layout_panel.add_zone()
    second = page.zone
    assert second != first
    assert {strip.zone for strip in page.strip_list} == {first, second}
    assert not page.zone_combo.isHidden()
    screens.pop()                                                     # the second monitor is unplugged
    page.screens_changed()
    assert page.service.world.offline_zones == {second}
    assert {strip.zone for strip in page.strip_list} == {first}


def test_painting_an_area_on_the_overview(page):
    panel, view = page.layout_panel, page.view
    panel.area_tag.setCurrentIndex(panel.area_tag.findData("work"))
    panel.area_paint.setChecked(True)
    panel._area_tool_changed()
    width = view.cell_width()
    for kind, cell in ((QEvent.Type.MouseButtonPress, 2), (QEvent.Type.MouseMove, 6), (QEvent.Type.MouseButtonRelease, 6)):
        point = QPointF(cell * width + 2, view.height() - 10)
        event = QMouseEvent(kind, point, point, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                            Qt.KeyboardModifier.NoModifier)
        {QEvent.Type.MouseButtonPress: view.mousePressEvent, QEvent.Type.MouseMove: view.mouseMoveEvent,
         QEvent.Type.MouseButtonRelease: view.mouseReleaseEvent}[kind](event)
    assert page.service.world.zones[page.zone].areas == ((2, 6, "work"),)


def test_strip_placement_uses_clicked_room(page):
    world = page.service.world
    first = page.zone
    second = page.add_zone(FakeScreen('second', 1280))
    bed = next(piece for piece in world.furniture.values() if piece.definition == 'bed_basic')
    world.store(bed.identifier)
    page.choose_zone(first)
    page.layout_panel.toggle_arrange()
    assert page.layout_panel.storage.select_key('bed_basic')
    strip = next(strip for strip in page.strip_list if strip.zone == second)
    strip.cell_clicked.emit(20)
    placed = next(piece for piece in world.furniture.values() if piece.definition == 'bed_basic')
    assert (placed.zone, placed.cell) == (second, 20)
    assert page.zone == second


def test_preview_only_appears_in_selected_room(page):
    first = page.zone
    page.add_zone(FakeScreen('second', 1280))
    page.choose_zone(first)
    preview = ('bed_basic', 5, False, None)
    page.set_preview(preview)
    for strip in page.strip_list:
        assert strip.preview == (preview if strip.zone == first else None)


def test_follow_from_other_strip_selects_residents_room(page):
    world = page.service.world
    first = page.zone
    second = page.add_zone(FakeScreen('second', 1280))
    resident = next(iter(world.residents))
    assert world.transfer_resident(resident, second) == 'accepted'
    page.choose_zone(first)
    strip = next(strip for strip in page.strip_list if strip.zone == second)
    strip.action_requested.emit('follow', resident)
    assert page.zone == second
    assert page.followed == resident


def test_strip_move_does_not_place_previously_selected_storage_item(page):
    world = page.service.world
    bed = next(piece for piece in world.furniture.values() if piece.definition == 'bed_basic')
    desk = next(piece for piece in world.furniture.values() if piece.definition == 'desk_basic')
    world.store(bed.identifier)
    page.refresh()
    assert page.layout_panel.storage.select_key('bed_basic')
    strip = page.strip_list[0]
    strip.action_requested.emit('move', desk.identifier)
    strip.cell_clicked.emit(20)
    assert desk.cell == 20
    assert world.stored('bed_basic') == 1
