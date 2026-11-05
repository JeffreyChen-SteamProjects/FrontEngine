"""The 1.0 furniture collection, level unlocks, the furniture guide, creations and the album."""
import pytest
from PySide6.QtGui import QColor, QImage

from frontengine.show.pet_game.home_service import HomeService
from frontengine.ui.page.pet_game.collection_panel import album_photos, creations, how_to_get, owned_count
from frontengine.ui.page.pet_game.home_page import PetHomePage
from frontengine.ui.page.pet_game.home_stage import TAB_ORDER
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.pet_game import behaviour, goals
from frontengine.utils.pet_game.catalog import NEEDS, builtin_catalog
from frontengine.utils.pet_game.goals import Progress
from frontengine.utils.pet_game.world import World

CATALOG = builtin_catalog()


def _world(mode="manage"):
    world = World(CATALOG, "a" * 32, mode, seed=2)
    zone = world.add_zone("screen", 0, 0, 40)
    if mode == "manage":
        world.grant_starter_kit()
        world.ledger.apply("gift", "test", 2000)
    return world, zone


def test_the_collection_reaches_the_1_0_target_with_every_category():
    assert len(CATALOG.furniture) >= 30
    categories = {definition.category for definition in CATALOG.furniture.values()}
    assert categories == {"bed", "table", "workstation", "leisure", "decoration", "bath"}
    for definition in CATALOG.furniture.values():
        assert set(definition.effects) <= set(NEEDS), definition.identifier
        assert 1 <= definition.unlock_level <= 5
    professions = {d.profession for d in CATALOG.furniture.values() if d.profession}
    assert all(sum(1 for d in CATALOG.furniture.values() if d.profession == p) >= 2 for p in professions)


def test_locked_pieces_and_jobs_open_with_the_home_level(monkeypatch):
    world, zone = _world()
    assert world.buy("piano", "t1") == "locked"
    assert world.buy("bean_bag", "t2") == "accepted"
    monkeypatch.setattr(goals, "home_level", lambda _world: 4)
    assert world.buy("piano", "t3") == "accepted"
    sandbox, _zone = _world("sandbox")
    assert sandbox.buy("grandfather_clock", "t4") == "accepted"            # free arranging has everything


def test_jobs_beyond_the_home_level_are_never_taken_up_by_themselves():
    world, zone = _world()
    world.place("desk_basic", zone, 12)
    world.add_resident({"id": "b" * 32, "name": "Mochi", "mood": 70, "fullness": 80, "affection": 3,
                        "energy": 90}, zone)
    resident = world.residents["b" * 32]
    resident.skills["writing"] = 500                                       # skilled enough for stories
    identifier = behaviour.auto_task(world, resident)
    assert world.tasks[identifier].recipe == "letter"                     # stories wait for level 2


def test_an_old_routine_goal_carries_over_without_paying_twice():
    world, _zone = _world()
    data = world.progress.to_dict()
    data["goals"] = {"set_routine": "claimed", "move_in": "claimed"}
    progress = Progress.from_dict(data)
    assert progress.goals == {"decorate": "claimed", "move_in": "claimed"}


def test_the_guide_says_how_to_get_every_piece(monkeypatch):
    world, zone = _world()
    world.furnish(zone)
    lines = {key: how_to_get(world, CATALOG.furniture[key]) for key in ("bed_basic", "stool", "piano", "rug")}
    assert lines["bed_basic"] == translate("pet_home_owned", "owned × {count}").format(count=1)
    assert lines["stool"] == translate("pet_home_made_at_station", "made at a workstation")
    assert lines["piano"] == translate("pet_home_unlock_level", "home level {level}").format(level=4)
    assert lines["rug"] == translate("pet_home_price_short", "{price} coins").format(price=40)
    assert owned_count(world, "table_basic") == 1
    world.progress.stats["settled:letter"] = 3
    assert ("letter", 3) in creations(world)


def test_only_pngs_inside_the_album_are_listed(tmp_path):
    album = tmp_path / "pet-album"
    album.mkdir()
    image = QImage(8, 8, QImage.Format.Format_ARGB32)
    image.fill(QColor("orange"))
    for name in ("a.png", "b.png"):
        image.save(str(album / name))
    (album / "notes.txt").write_text("x", encoding="utf-8")
    assert {path.name for path in album_photos(album)} == {"a.png", "b.png"}
    assert album_photos(tmp_path / "missing") == []
    assert len(album_photos(album, limit=1)) == 1


@pytest.fixture
def page(tmp_path, monkeypatch, *, home_store_factory, lifetime_factory):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    lifetime_factory()
    monkeypatch.setitem(user_setting_dict, "pet_home_running", False)
    service = HomeService(None, home_store_factory(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    widget = PetHomePage(service, lifetime=lifetime_factory())
    yield widget
    widget.shutdown()
    widget.deleteLater()


def test_the_collection_tab_and_locked_shop_captions(page):
    page.create_home()
    page.refresh()
    assert "pet_home_collection_section" in TAB_ORDER
    assert page.tabs.widget(TAB_ORDER.index("pet_home_collection_section")).isAncestorOf(page.collection.section)
    assert page.collection.encyclopedia.count() == len(CATALOG.furniture)
    assert page.collection.made.count() == len(CATALOG.recipes)
    texts = [page.shop.items.item(row).text() for row in range(page.shop.items.count())]
    level = translate("pet_home_unlock_level", "home level {level}").format(level=4)
    assert any(level in text for text in texts)
    assert page.shop.items.select_key("furniture:piano")
    page.shop.buy()
    assert page.message.text() == translate("pet_home_result_locked")


def test_same_second_photos_preserve_each_image(page, tmp_path, monkeypatch):
    from datetime import datetime
    from PySide6.QtGui import QPixmap
    from frontengine.ui.page.pet_game import goals_panel

    class FrozenTime:
        @staticmethod
        def now():
            return datetime(2026, 11, 5, 12, 0, 0)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(goals_panel, 'datetime', FrozenTime)
    page.create_home()
    picture = QPixmap(8, 8)
    picture.fill(QColor('red'))
    first = page.goals.save_photo(picture, 'Mochi')
    picture.fill(QColor('blue'))
    second = page.goals.save_photo(picture, 'Mochi')
    assert first != second
    assert QImage(str(first)).pixelColor(4, 4) == QColor('red')
    assert QImage(str(second)).pixelColor(4, 4) == QColor('blue')


@pytest.mark.parametrize('failure', ['folder', 'image'])
def test_failed_photo_leaves_no_album_file(page, tmp_path, monkeypatch, failure):
    from PySide6.QtGui import QPixmap

    monkeypatch.chdir(tmp_path)
    page.create_home()
    folder = tmp_path / 'pet-album'
    picture = QPixmap()
    if failure == 'folder':
        folder.write_text('occupied', encoding='utf-8')
        picture = QPixmap(8, 8)
        picture.fill(QColor('red'))
    assert page.goals.save_photo(picture) is None
    assert page.message.text() == translate('pet_home_photo_failed')
    if failure == 'folder':
        assert folder.read_text(encoding='utf-8') == 'occupied'
    else:
        assert list(folder.iterdir()) == []
