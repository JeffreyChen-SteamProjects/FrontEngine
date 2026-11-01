"""Residents appear as their own characters, prepared off the GUI thread, posed by what they do."""
import time

import pytest
from PySide6.QtCore import QCoreApplication, QThreadPool

from frontengine.show.pet.asset_library import PetAssetLibrary
from frontengine.show.pet.wardrobe import WardrobeDraft, asset_reference
from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.home_view import SPRITE_CELLS, HomeView
from frontengine.show.pet_game.resident_art import ResidentArt, fallback_character, semantic_action
from frontengine.user_setting.pet_game_save import HomeSaveStore
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.resident import Activity
from test_pet_variants import variant_asset


def _wait(condition, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        QThreadPool.globalInstance().waitForDone(50)
        QCoreApplication.processEvents()
        assert time.monotonic() < deadline, "timed out"


@pytest.fixture
def home(tmp_path):
    library = PetAssetLibrary(tmp_path / "library")
    asset = library.install(variant_asset(tmp_path / "cat").root)
    profiles = PetProfiles({}, lambda: None)
    service = HomeService(None, HomeSaveStore(tmp_path, builtin_catalog()), profiles)
    service.create_home("screen", 0, 900, 40, seed=3)
    record = profiles.create("Mochi")
    assert service.adopt(record["id"]) == "accepted"
    art = ResidentArt(service, library_factory=lambda: library)
    yield service, art, library, asset, record["id"]
    service.shutdown()


def _dress(service, library, asset, identifier) -> None:
    catalog, _ = library.scan()
    draft = WardrobeDraft(service.profiles, identifier, catalog)
    draft.choose_character(asset_reference(asset))
    draft.apply()


@pytest.mark.parametrize("kind, phase, action", [
    ("sleep", "using", "sleep"), ("nap", "using", "sleep"), ("eat", "using", "feed"), ("work", "using", "sit"),
    ("relax", "using", "sit"), ("play", "using", "play"), ("greet", "using", "greet"), ("work", "moving", "walk"),
    ("wait", "using", "idle"), ("drag", "moving", "drag"),
])
def test_activities_map_onto_character_actions(kind, phase, action):
    class Resident:
        activity = Activity(kind, "", phase=phase)
    assert semantic_action(Resident()) == action


def test_pets_without_a_character_appear_as_a_built_in_stand_in(home):
    service, art, _library, _asset, identifier = home
    assert art.renderer(identifier) is None                      # loading in the background
    changed = []
    art.changed.connect(lambda: changed.append(True))
    _wait(lambda: changed, timeout=60)
    renderer = art.renderer(identifier)
    assert renderer is not None
    assert renderer.character.identifier == fallback_character(identifier)
    frame = art.frame(service.world.residents[identifier])
    assert frame is not None
    assert not frame.isNull()
    assert service.profiles.get(identifier)["appearance"]["character"] is None   # its own look is untouched
    assert service.sessions[identifier].appearance_renderer is None              # nor the desktop pet's


def test_a_dressed_pet_is_prepared_in_the_background_and_drawn(home):
    service, art, library, asset, identifier = home
    _dress(service, library, asset, identifier)
    service.sessions[identifier].appearance_renderer = None       # force the background path
    changed = []
    art.changed.connect(lambda: changed.append(True))
    assert art.renderer(identifier) is None
    _wait(lambda: changed)
    resident = service.world.residents[identifier]
    frame = art.frame(resident)
    assert frame is not None and not frame.isNull()
    assert service.sessions[identifier].appearance_renderer is not None
    view = HomeView()
    view.art = art
    view.set_world(service.world, next(iter(service.world.zones)))
    view.resize(900, 170)
    box = view.resident_box(resident)
    assert box.height() == pytest.approx(view.cell_width() * SPRITE_CELLS)
    assert box.bottom() == pytest.approx(view._floor_y())
    view.grab()


def test_a_new_outfit_from_the_wardrobe_is_picked_up(home):
    service, art, library, asset, identifier = home
    _dress(service, library, asset, identifier)
    first = art.renderer(identifier)
    assert first is service.sessions[identifier].appearance_renderer
    catalog, _ = library.scan()
    draft = WardrobeDraft(service.profiles, identifier, catalog)
    draft.set_variant("eyes", "sleepy")
    draft.apply()
    second = art.renderer(identifier)
    assert second is not None
    assert second is not first
