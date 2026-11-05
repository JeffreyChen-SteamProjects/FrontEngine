"""Picture and Puppet pets appear in the home as themselves: the pet page records their look,
the home decodes it off the GUI thread, makes up missing motion the same way for every pet,
and falls back to a built-in stand-in only when the look cannot be used."""
import time

import pytest
from PIL import Image
from PySide6.QtCore import QCoreApplication, QThreadPool
from PySide6.QtGui import QColor, QImage

from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.picture_renderer import MAX_HEIGHT, PictureRenderer, load_picture
from frontengine.show.pet_game.resident_art import ResidentArt, fallback_character
from frontengine.user_setting.pet_looks import LOOKS_KEY, look_for, remember_portrait, remember_sprite
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.resident import Activity

PET = "d" * 32


def _png(path, color, size=(40, 60)):
    Image.new("RGBA", size, color).save(path)
    return path


def _gif(path, colors):
    frames = [Image.new("RGB", (30, 30), color) for color in colors]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=80, loop=0)
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

def test_only_readable_pictures_and_well_formed_ids_are_recorded(tmp_path):
    settings = {}
    picture = _png(tmp_path / "cat.png", "orange")
    assert remember_sprite(settings, PET, picture)
    assert look_for(settings, PET) == ("sprite", picture.resolve())
    assert not remember_sprite(settings, "not-an-id", picture)
    assert not remember_sprite(settings, PET, tmp_path / "missing.png")
    (tmp_path / "notes.txt").write_text("x", encoding="utf-8")
    assert not remember_sprite(settings, PET, tmp_path / "notes.txt")
    assert remember_sprite(settings, PET, tmp_path)                       # a sprite-pack folder
    assert look_for(settings, PET) == ("sprite", tmp_path.resolve())


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

def test_a_still_picture_bounces_while_walking_and_settles_while_sleeping(tmp_path):
    renderer = load_picture("sprite", _png(tmp_path / "cat.png", "orange"), PET)
    assert renderer.has_action("idle")
    assert not renderer.has_action("walk")
    resting = _lowest_opaque_row(renderer.render("idle", 0))
    bounced = _lowest_opaque_row(renderer.render("walk", 90))
    assert bounced < resting                                                # lifted off the floor
    sleeping = renderer.render("sleep", 0)
    tallest = next(y for y in range(sleeping.height()) if sleeping.pixelColor(20, y).alpha())
    standing = renderer.render("idle", 0)
    assert tallest > next(y for y in range(standing.height()) if standing.pixelColor(20, y).alpha())


def test_an_animated_gif_plays_its_own_frames(tmp_path):
    renderer = load_picture("sprite", _gif(tmp_path / "cat.gif", ["red", "blue"]), PET)
    first = renderer.render("idle", 10)
    second = renderer.render("idle", 90)
    width, height = renderer.character.canvas
    point = (width // 2, height - 5)
    assert first.pixelColor(*point) != second.pixelColor(*point)


def test_a_sprite_pack_uses_its_actions_and_borrows_for_the_rest(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    _png(pack / "walk.png", "red")
    _png(pack / "idle.png", "blue")
    _png(pack / "sleep.png", "green")
    renderer = load_picture("sprite", pack, PET)
    width, height = renderer.character.canvas
    color = lambda action: renderer.render(action, 0).pixelColor(width // 2, height - 5)   # noqa: E731
    assert color("walk") == QColor("red")
    assert color("sleep") == QColor("green")
    assert color("sit") == QColor("blue")              # no sitting sprite: idle
    assert color("play") == QColor("red")              # playing borrows the walk


def test_mirroring_and_size_limits(tmp_path):
    image = Image.new("RGBA", (300, 600), (0, 0, 0, 0))
    image.paste((255, 0, 0, 255), (0, 0, 150, 600))         # left half red
    image.save(tmp_path / "big.png")
    renderer = load_picture("sprite", tmp_path / "big.png", PET)
    width, height = renderer.character.canvas
    assert max(frame.height() for frame, _ in renderer.actions["idle"]) == MAX_HEIGHT
    plain = renderer.render("idle", 0)
    flipped = renderer.render("idle", 0, mirrored=True)
    assert plain.pixelColor(5, height - 5).alpha()
    assert not flipped.pixelColor(5, height - 5).alpha()
    with pytest.raises(ValueError):
        load_picture("sprite", tmp_path / "missing.png", PET)
    with pytest.raises(ValueError):
        load_picture("sprite", tmp_path, PET)                          # a folder with no sprites in it


# ----- in the home ----------------------------------------------------------------------------------

@pytest.fixture
def home(tmp_path, *, home_store_factory, lifetime_factory):
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


def test_a_picture_pet_is_drawn_from_its_own_picture_and_its_profile_is_untouched(home, tmp_path):
    service, art, identifier = home
    assert remember_sprite(service.profiles.settings, identifier, _gif(tmp_path / "own.gif", ["red", "blue"]))
    assert art.renderer(identifier) is None                                 # decoding in the background
    _wait(lambda: art.renderer(identifier) is not None)
    renderer = art.renderer(identifier)
    assert isinstance(renderer, PictureRenderer)
    resident = service.world.residents[identifier]
    resident.activity = Activity("work", "", phase="using")
    assert art.frame(resident) is not None
    assert service.profiles.get(identifier)["appearance"]["character"] is None
    assert service.sessions[identifier].appearance_renderer is None


def test_an_unusable_look_falls_back_to_the_stand_in(home, tmp_path):
    service, art, identifier = home
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not a picture")
    assert remember_sprite(service.profiles.settings, identifier, broken)
    _wait(lambda: art.renderer(identifier) is not None, timeout=60)
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
