"""Pet home content on the Workshop: furniture packs, themes and blueprints as their own kinds,
published from checked parts only, loaded into the home, and missing content packs named."""
import json

import pytest
from PySide6.QtGui import QColor, QImage

from frontengine.show.pet_game import themes
from frontengine.show.pet_game.furniture_art import picture
from frontengine.ui.page.pet_game.blueprint_dialog import missing_packs, missing_text
from frontengine.utils.pet_game import snapshot
from frontengine.utils.pet_game.blueprint import (
    canonical_blueprint, export_blueprint, parse_blueprint, required_packs, visit_blueprint,
)
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.content_pack import catalog_with_packs, load_pack, load_packs
from frontengine.utils.pet_game.world import World
from frontengine.utils.workshop.workshop_content import home_pack_roots, missing_requirements
from frontengine.utils.workshop.workshop_manifest import validate_manifest
from frontengine.utils.workshop.workshop_package import create_snapshot
from test_pet_home_content_packs import LAMP, _pack, _png

DUSK = {"id": "dusk", "name": "Dusk cabin", "base": "night_studio", "floor": [60, 40, 30], "day": [240, 200, 160],
        "night": [20, 10, 40]}


def _theme_pack(folder, identifier="moods", themes_=(DUSK,)):
    return _pack(folder, identifier, furniture=(), themes=list(themes_))


def _preview(tmp_path):
    path = tmp_path / "preview.png"
    image = QImage(16, 16, QImage.Format.Format_ARGB32)
    image.fill(QColor("orange"))
    image.save(str(path))
    return path


def _blueprint_text(theme="warm_home", pieces=(("bed_basic", 1),)):
    world = World(builtin_catalog(), "a" * 32, "sandbox", seed=1)
    zone = world.add_zone("s", 0, 0, 24)
    for name, cell in pieces:
        world.buy(name, f"b-{name}-{cell}")
        world.place(name, zone, cell)
    data = json.loads(export_blueprint(world))
    data["zones"][0]["theme"] = theme
    return json.dumps(data)


# ----- themes in content packs ---------------------------------------------------------------------

def test_a_pack_can_bring_themes_alone_and_they_join_the_catalog(tmp_path):
    pack = load_pack(_theme_pack(tmp_path))
    assert pack.furniture == []
    assert [theme.identifier for theme in pack.themes] == ["moods__dusk"]
    catalog = catalog_with_packs([pack])
    assert catalog.themes["moods__dusk"].base == "night_studio"
    world = World(catalog, "a" * 32, seed=1)
    zone = world.add_zone("s", 0, 0, 24)
    assert world.set_theme(zone, "moods__dusk") == "accepted"
    assert world.set_theme(zone, "other__dusk") == "unknown"            # a theme nobody installed


@pytest.mark.parametrize("change", [
    {"base": "space"}, {"floor": [1, 2]}, {"day": [0, 0, 256]}, {"night": "black"}, {"id": "Bad id"},
    {"extra": 1},
])
def test_a_bad_theme_refuses_the_whole_pack(tmp_path, change):
    root = _theme_pack(tmp_path, themes_=({**DUSK, **change},))
    with pytest.raises(ValueError):
        load_pack(root)


def test_a_pack_with_neither_furniture_nor_themes_is_refused(tmp_path):
    root = _pack(tmp_path, furniture=(), themes=[])
    with pytest.raises(ValueError, match="at least one"):
        load_pack(root)


def test_a_pack_theme_is_drawn_in_its_colours_over_its_base_pictures(tmp_path):
    pack = load_pack(_theme_pack(tmp_path))
    themes.register_themes(pack.themes)
    assert themes.palette("moods__dusk")["floor"] == (60, 40, 30)
    assert themes.base_theme("moods__dusk") == "night_studio"
    assert themes.palette("gone__theme") == themes.PALETTES["warm_home"]
    assert themes.base_theme("gone__theme") == "warm_home"
    drawn, base = picture("moods__dusk", "bed_basic"), picture("night_studio", "bed_basic")
    assert drawn is not None
    assert drawn.size() == base.size()


def test_a_save_keeps_a_pack_theme_while_its_pack_is_missing(tmp_path):
    catalog = catalog_with_packs([load_pack(_theme_pack(tmp_path))])
    world = World(catalog, "a" * 32, seed=1)
    zone = world.add_zone("s", 0, 0, 24)
    world.set_theme(zone, "moods__dusk")
    loaded = snapshot.from_dict(snapshot.to_dict(world), builtin_catalog())
    assert loaded.zones[zone].theme == "moods__dusk"


# ----- blueprints ------------------------------------------------------------------------------------

def test_a_shared_blueprint_is_rewritten_from_its_checked_parts():
    text = _blueprint_text(pieces=(("bed_basic", 1), ("plant_pot", 8)))
    assert parse_blueprint(canonical_blueprint(text)) == parse_blueprint(text)
    personal = json.loads(text)
    personal["coins"], personal["pets"] = 999, [{"name": "Mochi"}]
    personal_text = json.dumps(personal)
    with pytest.raises(ValueError):
        canonical_blueprint(personal_text)
    zone_with_owner = json.loads(text)
    zone_with_owner["zones"][0]["owner"] = "someone"
    owner_text = json.dumps(zone_with_owner)
    with pytest.raises(ValueError):
        canonical_blueprint(owner_text)


def test_a_blueprint_names_the_content_packs_it_needs():
    text = _blueprint_text(theme="moods__dusk")
    data = json.loads(text)
    data["pieces"].append([0, "cozy__moon_lamp", 12, False])
    text = json.dumps(data)
    assert required_packs(text) == ["cozy", "moods"]
    world, missing = visit_blueprint(text, builtin_catalog())
    assert missing == {"cozy__moon_lamp": 1}
    assert missing_packs(world, missing) == ["cozy", "moods"]
    assert "cozy, moods" in missing_text(world, missing)
    plain_world, plain_missing = visit_blueprint(_blueprint_text(), builtin_catalog())
    assert missing_text(plain_world, plain_missing) == ""


# ----- the Workshop -----------------------------------------------------------------------------------

@pytest.mark.parametrize("kind, entry_is_dir", [("home_furniture", True), ("home_theme", True),
                                                 ("home_blueprint", False)])
def test_home_kinds_check_their_entry_type(tmp_path, kind, entry_is_dir):
    (tmp_path / "content" / "x").mkdir(parents=True)
    (tmp_path / "content" / "x.json").write_text("{}", encoding="utf-8")
    manifest = {"format": "frontengine.workshop", "version": 1, "kind": kind, "title": "T",
                "entry": "content/x" if entry_is_dir else "content/x.json"}
    assert validate_manifest(manifest, tmp_path)["requires"] == []
    wrong = {**manifest, "entry": "content/x.json" if entry_is_dir else "content/x"}
    with pytest.raises(ValueError):
        validate_manifest(wrong, tmp_path)


def test_required_packs_in_a_manifest_are_checked_and_sorted(tmp_path):
    (tmp_path / "b.json").write_text("{}", encoding="utf-8")
    base = {"format": "frontengine.workshop", "version": 1, "kind": "home_blueprint", "title": "T",
            "entry": "b.json"}
    assert validate_manifest({**base, "requires": ["moods", "cozy", "cozy"]}, tmp_path)["requires"] == ["cozy", "moods"]
    for bad in (["../up"], ["Cozy"], "cozy", [1], ["a"] * 17):
        with pytest.raises(ValueError):
            validate_manifest({**base, "requires": bad}, tmp_path)


def test_publishing_a_furniture_pack_copies_only_its_manifest_and_pictures(tmp_path):
    source = _pack(tmp_path / "packs")
    (source / "notes.txt").write_text("not shipped", encoding="utf-8")
    _png(source / "thumbnail.png")
    manifest = create_snapshot("home_furniture", source, "Cozy", _preview(tmp_path), tmp_path / "out")
    root = tmp_path / "out" / "content" / "cozy"
    assert manifest["entry"] == "content/cozy"
    assert manifest["requires"] == []
    assert sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()) == [
        "furniture/warm_home/egg.png", "furniture/warm_home/moon_lamp.png", "pack.json", "thumbnail.png"]
    preview = _preview(tmp_path)
    with pytest.raises(ValueError, match="theme"):
        create_snapshot("home_theme", source, "Cozy", preview, tmp_path / "out2")


def test_publishing_a_blueprint_ships_only_the_layout_and_lists_its_packs(tmp_path):
    data = json.loads(_blueprint_text(theme="moods__dusk"))
    data["pieces"].append([0, "cozy__moon_lamp", 12, False])
    source = tmp_path / "my-home.json"
    source.write_text(json.dumps(data, indent=2), encoding="utf-8")
    manifest = create_snapshot("home_blueprint", source, "My home", _preview(tmp_path), tmp_path / "out")
    shipped = (tmp_path / "out" / "content" / "blueprint.json").read_text(encoding="utf-8")
    assert shipped == canonical_blueprint(source.read_text(encoding="utf-8"))
    assert manifest["requires"] == ["cozy", "moods"]
    assert missing_requirements(tmp_path / "out", {"cozy"}) == ["moods"]
    assert missing_requirements(tmp_path / "out", {"cozy", "moods"}) == []


def test_subscribed_home_packs_load_into_the_home_after_local_ones(tmp_path):
    content = tmp_path / "workshop"
    create_snapshot("home_theme", _theme_pack(tmp_path / "src"), "Moods", _preview(tmp_path), content / "101")
    create_snapshot("home_furniture", _pack(tmp_path / "src2"), "Cozy", _preview(tmp_path), content / "102")
    roots = home_pack_roots(content)
    assert sorted(root.name for root in roots) == ["cozy", "moods"]
    local = tmp_path / "local"
    _pack(local, "cozy", furniture=(LAMP,))
    packs, errors = load_packs(local, roots)
    assert [pack.identifier for pack in packs] == ["cozy", "moods"]
    assert errors == {"cozy": "Duplicate pack id"}                 # the local copy wins


def test_the_workshop_list_says_which_packs_an_item_needs(tmp_path):
    from frontengine.ui.dialog.workshop_dialog import _needs
    source = tmp_path / "home.json"
    source.write_text(_blueprint_text(theme="moods__dusk"), encoding="utf-8")
    create_snapshot("home_blueprint", source, "Home", _preview(tmp_path), tmp_path / "item")
    item = {"kind": "home_blueprint", "path": str(tmp_path / "item")}
    assert "moods" in _needs(item, set())
    assert _needs(item, {"moods"}) == ""
    assert _needs({"kind": "scene", "path": str(tmp_path)}, set()) == ""
