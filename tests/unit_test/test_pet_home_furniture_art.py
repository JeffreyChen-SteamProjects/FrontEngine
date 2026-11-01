"""Furniture pictures rendered in Blender: one per built-in piece and theme, shipped and drawn."""
import re
from pathlib import Path

import pytest
from PySide6.QtGui import QImage

from frontengine.show.pet_game import furniture_art
from frontengine.show.pet_game.home_view import HomeView
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.layout import THEMES
from frontengine.utils.pet_game.world import World

ROOT = Path(__file__).resolve().parents[2]
CATALOG = builtin_catalog()


@pytest.mark.parametrize("theme", THEMES)
def test_every_builtin_piece_has_a_picture_per_theme(theme):
    for identifier, definition in CATALOG.furniture.items():
        path = furniture_art.FOLDER / theme / f"{identifier}.png"
        image = QImage(str(path))
        assert not image.isNull(), path
        assert image.width() == definition.width * 96, identifier
        assert image.hasAlphaChannel()
        assert image.pixelColor(0, 0).alpha() == 0, identifier   # transparent around the piece


def test_pictures_stand_on_the_bottom_edge():
    for identifier in CATALOG.furniture:
        image = QImage(str(furniture_art.FOLDER / "warm_home" / f"{identifier}.png"))
        bottom = [image.pixelColor(x, image.height() - 1).alpha() for x in range(image.width())]
        above = [image.pixelColor(x, image.height() - 12).alpha() for x in range(image.width())]
        assert max(bottom) > 0 or max(above) > 0, identifier


def test_themes_fall_back_to_warm_home_and_unknown_pieces_have_none():
    assert furniture_art.picture("no_such_theme", "bed_basic") == furniture_art.picture("warm_home", "bed_basic")
    assert furniture_art.picture("warm_home", "content_pack_piece") is None
    assert furniture_art.aspect("warm_home", "content_pack_piece") is None


def test_pictures_ship_as_package_data_in_both_manifests_and_the_executable():
    for manifest in ("pyproject.toml", "stable.toml"):
        text = (ROOT / manifest).read_text(encoding="utf-8")
        assert re.search(r'"frontengine\.show\.pet_game" = \["furniture/\*/\*\.png", "items/\*\.png"\]', text), manifest
    assert "--include-package-data=frontengine.show.pet_game" in (ROOT / "exe/build_exe.py").read_text("utf-8")


def _world():
    world = World(CATALOG, "a" * 32, seed=1)
    zone = world.add_zone("screen", 0, 0, 30)
    world.grant_starter_kit()
    return world, zone


def test_view_sizes_pieces_by_their_picture():
    world, zone = _world()
    assert world.place("bed_basic", zone, 2)[0] == "accepted"
    view = HomeView()
    view.set_world(world, zone)
    view.resize(900, 200)
    piece = next(iter(world.furniture.values()))
    definition = CATALOG.furniture["bed_basic"]
    rect = view.piece_rect(piece, definition)
    ratio = furniture_art.aspect("warm_home", "bed_basic")
    assert rect.width() == pytest.approx(4 * view.cell_width())
    assert rect.height() == pytest.approx(min(rect.width() * ratio, view._floor_y() - 24))
    assert rect.bottom() == pytest.approx(view._floor_y())
    assert view.grab().toImage().pixelColor(int(rect.center().x()), int(rect.center().y())).alpha() == 255


def test_view_switches_pictures_with_the_theme():
    world, zone = _world()
    world.place("bed_basic", zone, 2)
    view = HomeView()
    view.set_world(world, zone)
    view.resize(900, 200)
    piece = next(iter(world.furniture.values()))
    rect = view.piece_rect(piece, CATALOG.furniture["bed_basic"]).toAlignedRect()
    before = view.grab().toImage().copy(rect)
    world.set_theme(zone, "night_studio")
    view.update()
    after = view.grab().toImage().copy(rect)
    assert before != after


def test_residents_rest_on_the_bed_surface_while_sleeping():
    from types import SimpleNamespace
    from frontengine.utils.pet_game.resident import Activity
    world, zone = _world()
    world.place("bed_basic", zone, 2)
    piece = next(iter(world.furniture.values()))
    view = HomeView()
    view.set_world(world, zone)
    view.resize(900, 200)
    resident = SimpleNamespace(activity=Activity("sleep", "", furniture=piece.identifier, phase="using"))
    height = view.piece_rect(piece, CATALOG.furniture["bed_basic"]).height()
    assert view._rest_height(resident) == pytest.approx(height * furniture_art.SURFACES["bed_basic"])
    resident.activity = Activity("sleep", "", furniture=piece.identifier, phase="moving")
    assert view._rest_height(resident) == 0.0
    resident.activity = None
    assert view._rest_height(resident) == 0.0
