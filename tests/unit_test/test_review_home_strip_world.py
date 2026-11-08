"""A desktop strip kept across a manage/sandbox switch follows the current home.

Both homes number their first zone "z1", so the strip survives the switch; it
must then draw and act on the home that is now running, not the one it was
built with.
"""
import pytest

from frontengine.show.pet_game.home_service import HomeService
from frontengine.ui.page.pet_game.home_page import DESKTOP_KEY, SAVE_MODE_KEY, PetHomePage
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_game.catalog import builtin_catalog


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    monkeypatch.setitem(user_setting_dict, "pet_home_running", False)
    monkeypatch.setitem(user_setting_dict, SAVE_MODE_KEY, "manage")
    monkeypatch.setitem(user_setting_dict, DESKTOP_KEY, True)


@pytest.fixture
def page(tmp_path, monkeypatch, *, home_store_factory, lifetime_factory):
    lifetime_factory()
    service = HomeService(None, home_store_factory(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    widget = PetHomePage(service, lifetime=lifetime_factory())
    yield widget
    monkeypatch.undo()
    assert widget.shutdown()
    widget.deleteLater()


def _switch_to_sandbox_and_back(page):
    page.desktop_check.setChecked(True)
    page.create_home()
    assert page.set_free_arranging(True)
    page.create_home()
    sandbox = page.service.world
    assert page.set_free_arranging(False)
    return sandbox


def test_kept_strip_follows_the_home_after_a_mode_switch(page):
    sandbox = _switch_to_sandbox_and_back(page)
    current = page.service.world
    assert current is not sandbox
    assert page.strip_list
    for strip in page.strip_list:
        assert strip.world is current
        assert strip.zone in current.zones


def test_drag_on_a_kept_strip_finishes_after_a_mode_switch(page):
    _switch_to_sandbox_and_back(page)
    strip = page.strip_list[0]
    world = page.service.world
    identifier = next(iter(world.residents))
    strip._press = (identifier, None)
    page.service.run(lambda current: current.drag(identifier, None))
    assert world.residents[identifier].activity.kind == "drag"
    strip._dragging = (identifier, 5000)
    strip._finish_pointer(commit=True)
    activity = world.residents[identifier].activity
    assert activity is None or activity.kind != "drag"
