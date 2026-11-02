"""Furniture content packs: checked at the boundary, namespaced, drawn, and safe to remove."""
import json
import os

import pytest
from PySide6.QtGui import QColor, QImage

from frontengine.show.pet_game.furniture_art import PACK_PICTURES, picture, register_pack_pictures
from frontengine.ui.page.pet_game.home_page import packs_text
from frontengine.utils.pet_game import snapshot
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.content_pack import catalog_with_packs, load_pack, load_packs
from frontengine.utils.pet_game.world import World

LAMP = {"id": "moon_lamp", "name": "Moon lamp", "category": "decoration", "width": 1, "solid": False,
        "price": 40, "comfort": 2}
SEAT = {"id": "egg_chair", "name": "Egg chair", "category": "leisure", "width": 2, "solid": True, "points": [0],
        "activity": "relax", "effects": {"mood": 8, "comfort": 12}, "price": 70, "poses": ["sit"], "art": "egg"}


def _png(path, height=96):
    path.parent.mkdir(parents=True, exist_ok=True)
    image = QImage(96, height, QImage.Format.Format_ARGB32)
    image.fill(QColor("#C98A4B"))
    assert image.save(str(path), "PNG")


def _pack(folder, identifier="cozy", furniture=(LAMP, SEAT), **changes):
    root = folder / identifier
    root.mkdir(parents=True, exist_ok=True)
    manifest = {"format": "frontengine.home-pack", "version": 1, "id": identifier, "name": "Cozy nights",
                "source": "Made for the tests", "license": "CC0-1.0", "furniture": list(furniture)}
    manifest.update(changes)
    (root / "pack.json").write_text(json.dumps(manifest), encoding="utf-8")
    for piece in furniture:
        _png(root / "furniture" / "warm_home" / f"{piece.get('art', piece['id'])}.png")
    return root


def test_a_pack_adds_namespaced_furniture_with_its_pictures(tmp_path):
    root = _pack(tmp_path)
    _png(root / "furniture" / "night_studio" / "egg.png", height=120)
    pack = load_pack(root)
    assert [piece.identifier for piece in pack.furniture] == ["cozy__moon_lamp", "cozy__egg_chair"]
    assert (pack.source, pack.license) == ("Made for the tests", "CC0-1.0")
    catalog = catalog_with_packs([pack])
    chair = catalog.furniture["cozy__egg_chair"]
    assert (chair.sell_back, chair.poses, chair.unlock_level) == (35, ("sit",), 1)
    assert "bed_basic" in catalog.furniture
    register_pack_pictures(pack.pictures)
    try:
        assert picture("night_studio", "cozy__egg_chair").height() == 120
        assert picture("green_studio", "cozy__egg_chair").height() == 96          # warm home fallback
    finally:
        for key in pack.pictures:
            PACK_PICTURES.pop(key, None)


@pytest.mark.parametrize("change, reason", [
    (dict(format="other"), "format"),
    (dict(version=2), "format"),
    (dict(id="other"), "folder"),
    (dict(extra=1), "format"),
    (dict(furniture=[]), "at least one piece"),
    (dict(furniture=[dict(LAMP, id="Bad-Id")]), "id"),
    (dict(furniture=[dict(LAMP, colour="red")]), "fields"),
    (dict(furniture=[LAMP, LAMP]), "Duplicate"),
    (dict(furniture=[dict(SEAT, poses=["dance"])]), "poses"),
    (dict(furniture=[dict(LAMP, category="workstation")]), "profession"),
    (dict(furniture=[dict(LAMP, art="../../escape")]), "art"),
    (dict(name="x" * 200), "name"),
])
def test_a_bad_manifest_refuses_the_whole_pack(tmp_path, change, reason):
    root = _pack(tmp_path)                                   # a good pack with its pictures...
    manifest = json.loads((root / "pack.json").read_text(encoding="utf-8"))
    manifest.update(change)                                  # ...then one thing wrong in its manifest
    (root / "pack.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match=reason):
        load_pack(root)


def test_anything_that_could_run_refuses_the_pack(tmp_path):
    root = _pack(tmp_path)
    (root / "furniture" / "helper.py").write_text("print('hi')", encoding="utf-8")
    with pytest.raises(ValueError, match="could run"):
        load_pack(root)


def test_pictures_must_be_real_small_pngs_inside_the_pack(tmp_path):
    root = _pack(tmp_path, furniture=(LAMP,))
    (root / "furniture" / "warm_home" / "moon_lamp.png").write_bytes(b"GIF89a not a png")
    with pytest.raises(ValueError, match="not a PNG"):
        load_pack(root)
    (root / "furniture" / "warm_home" / "moon_lamp.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * (3 * 1024 * 1024))
    with pytest.raises(ValueError, match="Invalid pack picture"):
        load_pack(root)
    (root / "furniture" / "warm_home" / "moon_lamp.png").unlink()
    with pytest.raises(ValueError, match="warm_home picture"):
        load_pack(root)


def test_a_link_inside_a_pack_is_refused(tmp_path):
    root = _pack(tmp_path, furniture=(LAMP,))
    outside = tmp_path / "outside.png"
    _png(outside)
    link = root / "furniture" / "green_studio" / "moon_lamp.png"
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        pytest.skip("this account cannot create symbolic links")
    with pytest.raises(ValueError, match="link"):
        load_pack(root)


def test_the_folder_loads_good_packs_and_explains_the_rest(tmp_path):
    _pack(tmp_path, "cozy")
    _pack(tmp_path, "broken", version=9)
    packs, errors = load_packs(tmp_path)
    assert [pack.identifier for pack in packs] == ["cozy"]
    assert set(errors) == {"broken"}
    store = type("Store", (), {"packs": packs, "pack_errors": errors})()
    text = packs_text(store)
    assert "Cozy nights - 2 pieces · Made for the tests · CC0-1.0" in text
    assert "broken was not loaded" in text
    assert load_packs(tmp_path / "missing") == ([], {})


def test_removing_a_pack_keeps_its_pieces_dormant_until_it_returns(tmp_path):
    pack = load_pack(_pack(tmp_path))
    with_pack = catalog_with_packs([pack])
    world = World(with_pack, "a" * 32, "sandbox", seed=1)
    zone = world.add_zone("s", 0, 0, 30)
    assert world.place("cozy__moon_lamp", zone, 5)[0] == "accepted"
    data = snapshot.to_dict(world)
    without = snapshot.from_dict(data, builtin_catalog())
    assert not any(piece.definition == "cozy__moon_lamp" for piece in without.furniture.values())
    back = snapshot.from_dict(snapshot.to_dict(without), with_pack)
    assert any(piece.definition == "cozy__moon_lamp" for piece in back.furniture.values())
