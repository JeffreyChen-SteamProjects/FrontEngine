"""Home blueprints: shared without anything personal, validated when read, visited read-only."""
import json

import pytest

from frontengine.show.pet_game.home_service import HomeService
from frontengine.ui.page.pet_game.home_page import PetHomePage
from frontengine.user_setting.pet_game_save import HomeSaveStore
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.pet_game.blueprint import (
    MAX_BLUEPRINT_BYTES, export_blueprint, parse_blueprint, visit_blueprint,
)
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.world import World

CATALOG = builtin_catalog()
PET = "b" * 32


def _home():
    world = World(CATALOG, "a" * 32, seed=4)
    zone = world.add_zone("DISPLAY1-secret-monitor", 0, 0, 30)
    world.grant_starter_kit()
    world.furnish(zone)
    world.set_area(zone, 0, 5, "living")
    world.add_resident({"id": PET, "name": "Mochi", "mood": 50, "fullness": 50, "affection": 9, "energy": 50}, zone)
    return world, zone


def test_a_blueprint_holds_rooms_and_furniture_only():
    world, _zone = _home()
    text = export_blueprint(world)
    for private in (PET, "Mochi", world.home, "DISPLAY1", "coins", "residents", "ledger"):
        assert private not in text
    data = json.loads(text)
    assert set(data) == {"format", "version", "zones", "pieces"}
    assert len(data["pieces"]) == len(world.furniture)


def test_visiting_rebuilds_the_same_home_without_anyone_in_it():
    world, zone = _home()
    visit, missing = visit_blueprint(export_blueprint(world), CATALOG)
    assert missing == {}
    assert visit.residents == {}
    assert visit.sandbox
    assert sorted((p.definition, p.cell, p.flipped) for p in visit.furniture.values()) == \
        sorted((p.definition, p.cell, p.flipped) for p in world.furniture.values())
    assert next(iter(visit.zones.values())).areas == world.zones[zone].areas


def test_unknown_pieces_are_counted_as_missing_not_trusted():
    world, _zone = _home()
    data = json.loads(export_blueprint(world))
    data["pieces"].append([0, "spaceship", 20, False])
    _visit, missing = visit_blueprint(json.dumps(data), CATALOG)
    assert missing == {"spaceship": 1}


@pytest.mark.parametrize("change", [
    lambda d: d.update(format="something-else"),
    lambda d: d.update(version=2),
    lambda d: d.update(extra=1),
    lambda d: d["zones"].clear(),
    lambda d: d["zones"][0].update(theme="lava"),
    lambda d: d["zones"][0].update(width_cells=10 ** 6),
    lambda d: d["zones"][0].update(areas=[[0, 99, "living"]]),
    lambda d: d["pieces"].append([5, "bed_basic", 1, False]),
    lambda d: d["pieces"].append([0, "bed_basic", "1", False]),
    lambda d: d["pieces"].append([0, "../../evil", 1, False]),
])
def test_a_malformed_blueprint_is_refused(change):
    world, _zone = _home()
    data = json.loads(export_blueprint(world))
    change(data)
    with pytest.raises(ValueError):
        visit_blueprint(json.dumps(data), CATALOG)


def test_an_oversized_blueprint_is_refused_before_parsing():
    with pytest.raises(ValueError):
        parse_blueprint(" " * (MAX_BLUEPRINT_BYTES + 1))


@pytest.fixture
def page(tmp_path, monkeypatch):
    monkeypatch.setitem(user_setting_dict, "pet_home_running", False)
    monkeypatch.setitem(user_setting_dict, "pet_home_on_desktop", False)
    service = HomeService(None, HomeSaveStore(tmp_path, CATALOG), PetProfiles({}, lambda: None))
    widget = PetHomePage(service)
    widget.create_home()
    yield widget
    widget.shutdown()
    widget.deleteLater()


def test_sharing_and_visiting_from_the_page(page, tmp_path, monkeypatch):
    panel = page.layout_panel
    target = tmp_path / "shared.json"
    monkeypatch.setattr(panel, "choose_save_path", lambda: str(target))
    assert panel.share_blueprint() == target
    monkeypatch.setattr(panel, "choose_open_path", lambda: str(target))
    dialog = panel.visit_blueprint()
    assert dialog is not None
    assert len(dialog.world.furniture) == len(page.service.world.furniture)
    assert dialog.world is not page.service.world
    assert dialog.missing.isHidden()
    dialog.close()


def test_a_file_that_is_not_a_blueprint_is_reported(page, tmp_path, monkeypatch):
    bad = tmp_path / "notes.json"
    bad.write_text("{\"hello\": 1}", encoding="utf-8")
    monkeypatch.setattr(page.layout_panel, "choose_open_path", lambda: str(bad))
    assert page.layout_panel.visit_blueprint() is None
    assert "not a home blueprint" in page.message.text()
