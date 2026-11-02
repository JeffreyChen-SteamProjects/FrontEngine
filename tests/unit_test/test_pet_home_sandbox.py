"""Free arranging: its own save, every piece free, nothing reaching the managed home or the pets."""
import pytest

from frontengine.show.pet_game.home_service import HomeService
from frontengine.ui.page.pet_game.home_page import SAVE_MODE_KEY, PetHomePage
from frontengine.user_setting.pet_game_save import HomeSaveStore
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_game.catalog import builtin_catalog


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    monkeypatch.setitem(user_setting_dict, "pet_home_running", False)
    monkeypatch.setitem(user_setting_dict, SAVE_MODE_KEY, "manage")


@pytest.fixture
def page(tmp_path):
    profiles = PetProfiles({}, lambda: None)
    service = HomeService(None, HomeSaveStore(tmp_path, builtin_catalog()), profiles)
    widget = PetHomePage(service)
    widget.tmp_path = tmp_path
    yield widget
    widget.shutdown()
    widget.deleteLater()


def test_switching_keeps_two_separate_saves(page):
    page.create_home()
    # creating a home with no pets brings a first one
    managed = page.service.world
    coins = managed.ledger.coins
    assert page.set_free_arranging(True)
    assert page.service.mode == "sandbox"
    assert page.service.world is None                             # its own, still empty, save
    assert page.sandbox_button.isChecked()
    page.create_home()
    sandbox = page.service.world
    assert sandbox.sandbox
    assert sandbox.home != managed.home
    assert page.layout_panel.storage.count() == len(builtin_catalog().furniture)   # every piece, unlimited
    page.service.run(lambda world: world.buy("workbench", "free"))
    assert sandbox.ledger.coins == 0                              # free, and no coins exist here
    assert (page.tmp_path / "pet-home-sandbox.json").is_file()
    assert page.set_free_arranging(False)
    assert page.service.world.home == managed.home
    assert page.service.world.ledger.coins == coins
    assert not (page.tmp_path / "pet-home.json").read_text(encoding="utf-8").count("workbench")


def test_a_pet_can_visit_free_arranging_without_its_profile_changing(page):
    page.set_free_arranging(True)
    page.create_home()
    # creating a home with no pets brings a first one
    identifier = page.selected_resident
    before = dict(page.profiles.get(identifier))
    page.service.world.residents[identifier].needs["mood"] = 1
    page.service.world.residents[identifier].affection = 99
    assert page.set_free_arranging(False)
    after = page.profiles.get(identifier)
    assert after["mood"] == before["mood"]
    assert after["affection"] == before["affection"]
    assert identifier not in page.service.sessions                # released on the way out


def test_leaving_cancels_activities_and_remembers_the_mode(page):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    page.create_home()
    # creating a home with no pets brings a first one
    resident = next(iter(page.service.world.residents.values()))
    page.service.run(lambda world: world.residents[resident.identifier].commands.append("play"))
    page.set_free_arranging(True)
    assert user_setting_dict[SAVE_MODE_KEY] == "sandbox"
    page.set_free_arranging(False)
    assert page.service.world.residents[resident.identifier].activity is None
    assert user_setting_dict[SAVE_MODE_KEY] == "manage"
    assert page.set_free_arranging(False)                         # already there: nothing happens


def test_a_failed_save_keeps_the_current_home(page, monkeypatch):
    page.create_home()
    monkeypatch.setattr(page.service, "save_now", lambda: False)
    assert not page.set_free_arranging(True)
    assert page.service.mode == "manage"
    assert page.service.world is not None
    assert not page.sandbox_button.isChecked()
