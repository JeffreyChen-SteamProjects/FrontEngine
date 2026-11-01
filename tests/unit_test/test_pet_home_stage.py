"""The pet home as a game screen: a stage on top, the panels in tabs underneath."""
import pytest

from frontengine.show.pet_game.home_service import HomeService
from frontengine.ui.page.pet_game.home_page import STAGE_HEIGHT, PetHomePage
from frontengine.ui.page.pet_game.home_stage import TAB_ORDER, EmptyHome
from frontengine.user_setting.pet_game_save import HomeSaveStore
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.pet_game.catalog import builtin_catalog


@pytest.fixture(autouse=True)
def _running_setting(monkeypatch):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    monkeypatch.setitem(user_setting_dict, "pet_home_running", False)


@pytest.fixture
def page(tmp_path):
    service = HomeService(None, HomeSaveStore(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    widget = PetHomePage(service)
    widget.resize(1200, 900)
    widget.show()
    yield widget
    widget.shutdown()
    widget.deleteLater()


def test_every_panel_is_a_tab_in_the_planned_order(page):
    assert page.tabs.keys() == list(TAB_ORDER)
    panels = (page.residents, page.work, page.layout_panel, page.shop, page.storage, page.goals, page.inbox)
    for index, panel in enumerate(panels):
        assert page.tabs.widget(index).isAncestorOf(panel.section)
        assert panel.section.title_label.isHidden()             # the tab carries the title
    assert page.tabs.widget(TAB_ORDER.index("pet_home_settings_section")).isAncestorOf(page.desktop_check)
    assert page.tabs.tabText(0) == translate("pet_home_residents_section", "Residents")


def test_without_a_home_the_stage_shows_what_a_home_starts_with(page):
    assert page.empty_home.isVisible()
    assert page.create_button.isVisible()
    assert page.create_button.objectName() == "primaryAction"
    assert not page.view_area.isVisible()
    assert not page.tabs.isVisible()
    image = page.empty_home.grab().toImage()
    assert len({image.pixel(x, image.height() - 40) for x in range(0, image.width(), 7)}) > 3


def test_creating_a_home_opens_the_stage_and_the_tabs(page):
    page.create_home()
    assert not page.empty_home.isVisible()
    assert page.view_area.isVisible()
    assert page.view.height() == STAGE_HEIGHT
    assert page.tabs.isVisible()
    assert page.run_button.isVisible()
    assert page.tabs.select("pet_home_shop_section")
    assert page.tabs.currentWidget().isAncestorOf(page.shop.section)
    assert not page.tabs.select("nothing")


def test_messages_appear_only_when_there_is_one(page):
    assert page.message.isHidden()
    page.report_text("Something happened")
    assert not page.message.isHidden()
    page.report_text("")
    assert page.message.isHidden()


def test_empty_home_paints_its_starter_furniture():
    widget = EmptyHome()
    widget.resize(700, widget.height())
    image = widget.grab().toImage()
    painted = sum(1 for x in range(0, 700, 5) if image.pixelColor(x, widget.height() - 30).alpha() > 0
                  and image.pixelColor(x, widget.height() - 30) != image.pixelColor(2, 2))
    assert painted > 10
