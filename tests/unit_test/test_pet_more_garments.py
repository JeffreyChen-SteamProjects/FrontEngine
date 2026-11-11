"""The second wardrobe: five more outfits, every new piece drawn and named in every language, and an
opened wardrobe that fetches built-in clothes added since the character was installed."""
from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtWidgets import QComboBox

from frontengine.show.pet.inkside.assemble import build_character, build_garment, garment_identifier
from frontengine.show.pet.inkside.cast import TEMPLATES
from frontengine.show.pet.inkside.garments import GARMENTS, OUTFITS
from frontengine.show.pet.inkside.labels import label
from frontengine.show.pet.inkside.library import VERSION, builtin_names
from frontengine.show.pet.layered_renderer import LayeredRenderer
from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog
from frontengine.utils.pet_pack.layered import load_layered_asset

NEW_OUTFITS = ("WINTER WALK", "KITCHEN", "PARTY", "SCHOOL DAY", "BEACH DAY")
NEW_PIECES = ("knit-beanie", "puffer-jacket", "chef-hat", "neckerchief", "chef-jacket", "party-hat",
              "confetti-shirt", "student-cap", "blazer", "satchel", "straw-hat", "flower-lei", "striped-tee")


def test_the_wardrobe_has_nineteen_outfits_and_every_piece_exists():
    names = [name for name, _home, _pieces in OUTFITS]
    assert len(OUTFITS) == 19
    assert set(NEW_OUTFITS) <= set(names)
    known = {garment.ident for garment in GARMENTS}
    assert set(NEW_PIECES) <= known
    assert len(known) == len(GARMENTS) == 43
    for _name, home, pieces in OUTFITS:
        assert home in {identifier for identifier, _ in builtin_names()}
        assert set(pieces) <= known
        slots = [slot for piece in pieces for slot in next(g for g in GARMENTS if g.ident == piece).slots]
        assert len(slots) == len(set(slots)), pieces                 # an outfit never doubles a slot


def test_every_new_piece_is_named_in_every_language():
    import re
    from frontengine.utils.multi_language import (english, france, germany, italy, russian, simplified_chinese,
                                                  traditional_chinese)
    for garment in GARMENTS:
        if garment.ident not in NEW_PIECES:
            continue
        key = "inkside_" + re.sub(r"[^a-z0-9]+", "_", garment.name.lower()).strip("_")
        for module in (english, france, germany, italy, russian, simplified_chinese, traditional_chinese):
            words = next(value for name, value in vars(module).items() if isinstance(value, dict) and key in value)
            assert words[key].strip(), (module.__name__, key)
    assert label("inkside-x", "Knit beanie") == "Knit beanie"                # English shows the name itself


def test_each_new_piece_changes_how_a_pet_looks(tmp_path):
    template = TEMPLATES[0]
    character = load_layered_asset(build_character(template, tmp_path / template.ident))
    bare = LayeredRenderer(character).render("idle", 0)
    for garment in GARMENTS:
        if garment.ident not in NEW_PIECES:
            continue
        piece = load_layered_asset(build_garment(garment, template, tmp_path / garment_identifier(garment, template)))
        assert LayeredRenderer(character, (piece,)).render("idle", 0) != bare, garment.ident


class _Library:
    def __init__(self, installed: set[str]) -> None:
        self.installed = installed

    def is_installed(self, identifier: str, version: str) -> bool:
        return version == VERSION and identifier in self.installed


def _wardrobe(character, installed, lifetime):
    builtin = QComboBox()
    for identifier, name in builtin_names():
        builtin.addItem(name, identifier)
    wardrobe = SimpleNamespace(lifetime=lifetime, draft=SimpleNamespace(appearance={"character": character}),
                               library=_Library(installed), _install_job=None, builtin=builtin,
                               _install_builtin=Mock(), _adding_new_clothes=False)
    wardrobe.missing_builtin_clothes = lambda: PetWardrobeDialog.missing_builtin_clothes(wardrobe)
    return wardrobe


def test_an_opened_wardrobe_fetches_new_built_in_clothes_by_itself(lifetime_factory):
    lifetime = lifetime_factory()
    template = next(t for t in TEMPLATES if t.ident == "inkside-pip")
    everything = {garment_identifier(garment, template) for garment in GARMENTS}
    reference = {"id": "inkside-pip", "version": VERSION}
    older = _wardrobe(reference, everything - {garment_identifier(GARMENTS[-1], template)}, lifetime)
    assert PetWardrobeDialog.missing_builtin_clothes(older) == "inkside-pip"
    PetWardrobeDialog.add_new_builtin_clothes(older)
    older._install_builtin.assert_called_once_with()
    assert older._adding_new_clothes is True
    assert older.builtin.currentData() == "inkside-pip"
    current = _wardrobe(reference, everything, lifetime)
    assert PetWardrobeDialog.missing_builtin_clothes(current) is None
    own = _wardrobe({"id": "my-cat", "version": "1"}, set(), lifetime)
    assert PetWardrobeDialog.missing_builtin_clothes(own) is None              # not a built-in character
    busy = _wardrobe(reference, set(), lifetime)
    busy._install_job = object()
    PetWardrobeDialog.add_new_builtin_clothes(busy)
    busy._install_builtin.assert_not_called()
