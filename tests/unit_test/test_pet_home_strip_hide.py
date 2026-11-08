"""Hiding the desktop home from its own menu also unticks *Show the home on the desktop*."""
import pytest

from frontengine.show.pet_game.home_service import HomeService
from frontengine.ui.page.pet_game.home_page import DESKTOP_KEY, PetHomePage
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.pet_game.catalog import builtin_catalog


@pytest.fixture
def page(tmp_path, monkeypatch, *, home_store_factory, lifetime_factory):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    monkeypatch.setitem(user_setting_dict, "pet_home_running", False)
    monkeypatch.setitem(user_setting_dict, DESKTOP_KEY, True)
    lifetime_factory()
    service = HomeService(None, home_store_factory(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    widget = PetHomePage(service, lifetime=lifetime_factory())
    yield widget
    monkeypatch.undo()
    assert widget.shutdown()
    widget.deleteLater()


def _hide_action(strip):
    strip._fill_home_menu()
    return next(action for action in strip.button.menu().actions()
                if action.text() == translate("pet_home_hide", "Hide the home"))


def test_hiding_the_home_from_its_menu_unticks_the_setting(page):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    page.desktop_check.setChecked(True)
    page.create_home()
    assert page.strip_list and page.desktop_check.isChecked()
    _hide_action(page.strip_list[0]).trigger()
    assert not page.desktop_check.isChecked()
    assert user_setting_dict[DESKTOP_KEY] is False
    assert page.strip_list == []
    page.desktop_check.setChecked(True)               # ticking it again brings the home back
    assert page.strip_list and page.strip_list[0].isVisible()
