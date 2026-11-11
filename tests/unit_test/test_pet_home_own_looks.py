"""Puppet pets appear in the home as themselves: the pet page records a portrait, the home decodes
it off the GUI thread, makes up the motion, and falls back to a built-in stand-in only when the
portrait cannot be used. Pets are layered only, so sprite looks recorded before are ignored."""
import time

import pytest
from PIL import Image
from PySide6.QtCore import QCoreApplication, QThreadPool
from PySide6.QtGui import QColor, QImage

from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.picture_renderer import MAX_HEIGHT, PictureRenderer, load_picture
from frontengine.show.pet_game.resident_art import ResidentArt, fallback_character
from frontengine.user_setting.pet_looks import LOOKS_KEY, look_for, remember_portrait
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.resident import Activity

PET = "d" * 32


def _png(path, color, size=(40, 60)):
    Image.new("RGBA", size, color).save(path)
    return path


def _wait(condition, timeout=30.0):
    deadline = time.monotonic() + timeout
    while not condition():
        QThreadPool.globalInstance().waitForDone(50)
        QCoreApplication.processEvents()
        assert time.monotonic() < deadline, "timed out"


def _lowest_opaque_row(image: QImage) -> int:
    for y in range(image.height() - 1, -1, -1):
        if any(image.pixelColor(x, y).alpha() for x in range(image.width())):
            return y
    return -1


# ----- the registry ------------------------------------------------------------------------------

def test_sprite_looks_recorded_before_pets_were_layered_only_are_ignored(tmp_path):
    picture = _png(tmp_path / "cat.png", "orange")
    for entry in ({"kind": "sprite", "path": str(picture.resolve())}, {"kind": "sprite", "path": str(tmp_path)}):
        assert look_for({LOOKS_KEY: {PET: entry}}, PET) is None


@pytest.mark.parametrize("entry", [
    "cat.png", {"kind": "sprite"}, {"kind": "sprite", "path": 3}, {"kind": "sprite", "path": "relative.png"},
    {"kind": "portrait", "path": "../../elsewhere.png"}, {"kind": "script", "path": "x"},
])
def test_malformed_registry_entries_are_ignored(entry):
    assert look_for({LOOKS_KEY: {PET: entry}}, PET) is None
    assert look_for({LOOKS_KEY: "nonsense"}, PET) is None


def test_a_portrait_is_saved_small_and_read_only_from_its_own_file(tmp_path):
    settings = {}
    image = QImage(200, 600, QImage.Format.Format_ARGB32)
    image.fill(QColor(20, 120, 220))
    assert remember_portrait(settings, PET, image, tmp_path)
    saved = QImage(str(tmp_path / f"{PET}.png"))
    assert saved.height() == 256
    assert look_for(settings, PET, tmp_path) == ("portrait", tmp_path / f"{PET}.png")
    assert not remember_portrait(settings, "../" + PET, image, tmp_path)
    (tmp_path / f"{PET}.png").unlink()
    assert look_for(settings, PET, tmp_path) is None


# ----- drawing ------------------------------------------------------------------------------------

def test_a_portrait_bounces_while_walking_and_settles_while_sleeping(tmp_path):
    renderer = load_picture("portrait", _png(tmp_path / "cat.png", "orange"), PET)
    assert renderer.has_action("idle")
    assert not renderer.has_action("walk")
    resting = _lowest_opaque_row(renderer.render("idle", 0))
    bounced = _lowest_opaque_row(renderer.render("walk", 90))
    assert bounced < resting                                                # lifted off the floor
    sleeping = renderer.render("sleep", 0)
    tallest = next(y for y in range(sleeping.height()) if sleeping.pixelColor(20, y).alpha())
    standing = renderer.render("idle", 0)
    assert tallest > next(y for y in range(standing.height()) if standing.pixelColor(20, y).alpha())


def test_only_portraits_are_drawn(tmp_path):
    picture = _png(tmp_path / "cat.png", "orange")
    for kind in ("sprite", "pack", "gif"):
        with pytest.raises(ValueError):
            load_picture(kind, picture, PET)


def test_mirroring_and_size_limits(tmp_path):
    image = Image.new("RGBA", (300, 600), (0, 0, 0, 0))
    image.paste((255, 0, 0, 255), (0, 0, 150, 600))         # left half red
    image.save(tmp_path / "big.png")
    renderer = load_picture("portrait", tmp_path / "big.png", PET)
    width, height = renderer.character.canvas
    assert max(frame.height() for frame, _ in renderer.actions["idle"]) == MAX_HEIGHT
    plain = renderer.render("idle", 0)
    flipped = renderer.render("idle", 0, mirrored=True)
    assert plain.pixelColor(5, height - 5).alpha()
    assert not flipped.pixelColor(5, height - 5).alpha()
    with pytest.raises(ValueError):
        load_picture("portrait", tmp_path / "missing.png", PET)


# ----- in the home ----------------------------------------------------------------------------------

@pytest.fixture
def home(tmp_path, monkeypatch, *, home_store_factory, lifetime_factory):
    monkeypatch.chdir(tmp_path)                      # portraits are kept under ./pet-home-looks
    lifetime = lifetime_factory()
    profiles = PetProfiles({}, lambda: None)
    service = HomeService(None, home_store_factory(tmp_path, builtin_catalog()), profiles)
    service.create_home("screen", 0, 900, 40, seed=3)
    record = profiles.create("Mochi")
    assert service.adopt(record["id"]) == "accepted"
    art = ResidentArt(service, lifetime=lifetime)
    yield service, art, record["id"]
    art.shutdown()
    service.shutdown()


def _portrait(color: str) -> QImage:
    image = QImage(64, 96, QImage.Format.Format_ARGB32)
    image.fill(QColor(color))
    return image


def test_a_puppet_pet_is_drawn_from_its_portrait_and_its_profile_is_untouched(home):
    service, art, identifier = home
    assert service.profiles.remember_portrait(identifier, _portrait("purple"))
    assert art.renderer(identifier) is None                                 # decoding in the background
    _wait(lambda: art.renderer(identifier) is not None)
    renderer = art.renderer(identifier)
    assert isinstance(renderer, PictureRenderer)
    resident = service.world.residents[identifier]
    resident.activity = Activity("work", "", phase="using")
    assert art.frame(resident) is not None
    assert service.profiles.get(identifier)["appearance"]["character"] is None
    assert service.sessions[identifier].appearance_renderer is None


def test_an_unusable_portrait_or_an_old_sprite_look_falls_back_to_the_stand_in(home, tmp_path):
    service, art, identifier = home
    service.profiles.settings[LOOKS_KEY] = {identifier: {"kind": "sprite", "path": str(_png(tmp_path / "a.png", "red"))}}
    _wait(lambda: art.renderer(identifier) is not None, timeout=60)
    assert art.renderer(identifier).character.identifier == fallback_character(identifier)
    assert service.profiles.remember_portrait(identifier, _portrait("purple"))
    (tmp_path / "pet-home-looks" / f"{identifier}.png").write_bytes(b"not a picture")
    _wait(lambda: not isinstance(art.renderer(identifier), PictureRenderer)
          and art.renderer(identifier) is not None, timeout=60)
    assert art.renderer(identifier).character.identifier == fallback_character(identifier)


def test_the_pet_page_keeps_a_puppet_portrait_only_when_its_canvas_can_render(tmp_path, monkeypatch, *, lifetime_factory):
    from frontengine.ui.page.pet import pet_setting_ui
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI

    monkeypatch.chdir(tmp_path)
    lifetime_factory()
    page = PetSettingUI(lifetime=lifetime_factory())
    settings = page.profile_controls.profiles.settings

    class Pet:
        class profile_session:
            identifier = PET

        def __init__(self, image):
            self.image = image

        def photo_image(self):
            if self.image is None:
                raise ValueError("no GL canvas")
            return self.image

    try:
        page._remember_portrait(Pet(None))
        assert look_for(settings, PET) is None
        image = QImage(64, 96, QImage.Format.Format_ARGB32)
        image.fill(QColor("purple"))
        page._remember_portrait(Pet(image))
        assert look_for(settings, PET) == ("portrait", tmp_path / "pet-home-looks" / f"{PET}.png")
        assert pet_setting_ui.PORTRAIT_DELAY_MS > 0
    finally:
        settings.get(LOOKS_KEY, {}).pop(PET, None)
        page.close()
