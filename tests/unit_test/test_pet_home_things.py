"""Every furniture piece, item and job the home lists has a picture."""
import pytest

from frontengine.show.pet_game.furniture_art import ITEM_FOLDER, item_picture
from frontengine.show.pet_game.home_service import HomeService
from frontengine.ui.page.pet_game.home_page import PetHomePage
from frontengine.ui.page.pet_game.home_things import RECIPE_ICONS, ROLE_KEY, ThingGrid, thing_icon, thing_pixmap
from frontengine.user_setting.pet_game_save import HomeSaveStore
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_game.catalog import FURNITURE_PREFIX, builtin_catalog

CATALOG = builtin_catalog()


def _painted(pixmap) -> int:
    image = pixmap.toImage()
    return sum(1 for x in range(0, image.width(), 4) for y in range(0, image.height(), 4)
               if image.pixelColor(x, y).alpha() > 0)


def test_every_item_and_job_has_a_picture():
    for identifier in CATALOG.items:
        assert item_picture(identifier) is not None, identifier
        assert _painted(thing_pixmap(identifier)) > 20, identifier
    for recipe in CATALOG.recipes:
        assert recipe in RECIPE_ICONS, recipe
        assert _painted(thing_pixmap("recipe:" + recipe)) > 20, recipe
    for identifier in CATALOG.furniture:
        assert _painted(thing_pixmap(FURNITURE_PREFIX + identifier)) > 20, identifier
    assert item_picture("coin") is not None


def test_item_names_cannot_reach_outside_the_icon_folder():
    assert item_picture("../furniture/warm_home/bed_basic") is None
    assert item_picture("nothing") is None
    assert all(path.parent == ITEM_FOLDER for path in ITEM_FOLDER.glob("*.png"))


def test_grid_keeps_the_selection_when_refilled():
    grid = ThingGrid()
    grid.set_things([("a", thing_icon("wood"), "Wood"), ("b", thing_icon("toy"), "Toy")])
    assert grid.select_key("b")
    grid.set_things([("a", thing_icon("wood"), "Wood × 2"), ("b", thing_icon("toy"), "Toy")])
    assert grid.current_key() == "b"
    assert grid.item(0).text() == "Wood × 2"
    grid.set_things([("c", thing_icon("herb"), "Herbs"), ("b", thing_icon("toy"), "Toy")])
    assert grid.current_key() == "b"
    assert not grid.select_key("missing")


def test_grid_refreshes_icon_and_tooltip_without_losing_selection():
    from PySide6.QtGui import QColor, QIcon, QPixmap

    grid = ThingGrid()
    first, second = QPixmap(8, 8), QPixmap(8, 8)
    first.fill(QColor('red'))
    second.fill(QColor('blue'))
    grid.set_things([('bed', QIcon(first), 'Bed × 1')])
    grid.select_key('bed')
    grid.set_things([('bed', QIcon(second), 'Bed × 2')])
    assert grid.current_key() == 'bed'
    assert grid.item(0).icon().pixmap(8, 8).toImage().pixelColor(4, 4) == QColor('blue')
    assert grid.item(0).toolTip() == 'Bed × 2'


@pytest.fixture
def page(tmp_path, monkeypatch):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    monkeypatch.setitem(user_setting_dict, "pet_home_running", False)
    service = HomeService(None, HomeSaveStore(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    widget = PetHomePage(service)
    widget.create_home()
    yield widget
    widget.shutdown()
    widget.deleteLater()


def test_shop_backpack_and_storage_are_pictures(page):
    world = page.service.world
    world.ledger.apply("gift", "test", 200, {"herb": 2, "wood": 1})
    page.refresh()
    shop_keys = [page.shop.items.item(row).data(ROLE_KEY) for row in range(page.shop.items.count())]
    assert "wood" in shop_keys
    assert all(key.startswith(FURNITURE_PREFIX) or key in CATALOG.items for key in shop_keys)
    for grid in (page.shop.items, page.storage.list):
        assert grid.count()
        assert all(not grid.item(row).icon().isNull() for row in range(grid.count()))
    bed = next(piece.identifier for piece in world.furniture.values() if piece.definition == "bed_basic")
    page.service.run(lambda w: w.store(bed))
    page.refresh()
    assert page.layout_panel.storage.count() == 1
    assert not page.layout_panel.storage.item(0).icon().isNull()
    page.layout_panel.place()                                   # back into a free spot by itself
    assert world.stored("bed_basic") == 0
