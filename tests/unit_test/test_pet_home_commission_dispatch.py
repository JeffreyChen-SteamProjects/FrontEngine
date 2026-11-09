"""Sending a pet to a commission from the Goals tab and from the desktop strip's toolbar."""
import pytest
from PySide6.QtCore import QCoreApplication

from frontengine.show.pet_game.captions import DISPATCH_TEXT
from frontengine.show.pet_game.home_service import HomeService
from frontengine.ui.page.pet_game.home_page import PetHomePage
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.multi_language.english import english_word_dict
from frontengine.utils.multi_language.france import french_word_dict
from frontengine.utils.multi_language.germany import germany_word_dict
from frontengine.utils.multi_language.italy import italian_word_dict
from frontengine.utils.multi_language.russian import russian_word_dict
from frontengine.utils.multi_language.simplified_chinese import simplified_chinese_word_dict
from frontengine.utils.multi_language.traditional_chinese import traditional_chinese_word_dict
from frontengine.utils.pet_game.catalog import builtin_catalog

CATALOG = builtin_catalog()
LANGUAGES = (english_word_dict, traditional_chinese_word_dict, simplified_chinese_word_dict, germany_word_dict,
             french_word_dict, italian_word_dict, russian_word_dict)


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    for key, value in (("pet_home_running", False), ("pet_home_on_desktop", True), ("pet_home_layer", "top"),
                       ("pet_home_toolbar_open", True), ("pet_home_toolbar_dock", "left")):
        monkeypatch.setitem(user_setting_dict, key, value)


@pytest.fixture
def page(tmp_path, *, home_store_factory, lifetime_factory):
    lifetime_factory()
    service = HomeService(None, home_store_factory(tmp_path, CATALOG), PetProfiles({}, lambda: None))
    widget = PetHomePage(service, lifetime=lifetime_factory())
    widget.create_home()                        # a first pet moves in with the home
    yield widget
    widget.shutdown()
    widget.deleteLater()


def _herbs_wanted(page, *, planter: bool = True) -> str:
    """Today's only commission asks for herbs; the home may or may not have a planter."""
    def change(world):
        world.automatic = False                 # nothing hands it in or takes up work by itself here
        world.progress.commissions = {"day": world.progress.commissions["day"],
                                      "offers": [{"item": "herb", "count": 3, "coins": 18, "done": False}]}
        if planter:
            world.ledger.apply("coins-for-planter", "test", 1000)
            assert world.buy("planter", "buy-planter") == "accepted"
            free = [cell for cell in range(world.zones[page.zone].width_cells - 1)
                    if world.preview("planter", page.zone, cell) is None]
            assert world.place("planter", page.zone, free[-1])[0] == "accepted"
        return next(iter(world.residents))
    pet = page.service.run(change)
    page.refresh()
    return pet


def test_double_clicking_a_commission_sends_a_pet_and_says_who(page):
    pet = _herbs_wanted(page)
    goals = page.goals
    goals.commissions.setCurrentRow(0)
    assert goals.dispatch_button.isEnabled()
    goals.commissions.itemDoubleClicked.emit(goals.commissions.item(0))
    world = page.service.world
    [task] = world.tasks.values()
    assert (task.recipe, task.resident, task.units) == ("herbs", pet, 2)      # two herbs a unit
    assert "work" in world.residents[pet].commands
    assert world.residents[pet].name in page.message.text()
    goals.dispatch_button.click()                            # the herbs are on their way already
    assert len(world.tasks) == 1
    assert page.message.text() == english_word_dict["pet_home_dispatch_already_queued"]


def test_without_a_workstation_the_reason_is_shown_and_nothing_is_queued(page):
    _herbs_wanted(page, planter=False)
    page.goals.commissions.setCurrentRow(0)
    page.goals.dispatch()
    assert not page.service.world.tasks
    assert page.message.text() == english_word_dict["pet_home_dispatch_no_station"].format(trade="Gardening")


def test_a_handed_in_commission_cannot_be_sent_again(page):
    _herbs_wanted(page)
    page.service.run(lambda world: world.progress.commissions["offers"][0].update(done=True))
    page.refresh()
    page.goals.commissions.setCurrentRow(0)
    assert not page.goals.dispatch_button.isEnabled()


def test_the_strip_toolbar_lists_todays_commissions_and_sends_a_pet(page):
    pet = _herbs_wanted(page)
    strip = page.strip_list[0]
    assert strip.commission_button.isHidden()                # folded away with the rest of the toolbar
    strip.set_toolbar_open(True)
    assert strip.commission_button in strip.shortcut_buttons
    assert not strip.commission_button.isHidden()
    menu = strip.commission_button.menu()
    menu.aboutToShow.emit()
    [action] = menu.actions()
    assert action.isEnabled()
    assert "3" in action.text()
    action.trigger()
    QCoreApplication.processEvents()
    world = page.service.world
    assert [task.resident for task in world.tasks.values()] == [pet]
    page.service.run(lambda w: w.progress.commissions["offers"][0].update(done=True))
    menu.aboutToShow.emit()
    assert not menu.actions()[0].isEnabled()
    assert menu.actions()[0].text().startswith("✔")
    page.service.run(lambda w: w.progress.commissions.update(offers=[]))
    menu.aboutToShow.emit()
    assert [a.text() for a in menu.actions()] == [english_word_dict["pet_home_commissions_none"]]


def test_the_strip_says_why_nobody_can_go(page):
    _herbs_wanted(page, planter=False)
    text = page.strip_list[0].dispatch_commission(0, "herb")
    assert text == english_word_dict["pet_home_dispatch_no_station"].format(trade="Gardening")
    assert not page.service.world.tasks


@pytest.mark.parametrize("words", LANGUAGES, ids=lambda words: words["language_menu_title"]
                         if "language_menu_title" in words else str(id(words)))
def test_every_language_fills_every_dispatch_sentence(words):
    values = {"pet": "Mochi", "units": 2, "item": "Herb", "trade": "Gardening", "level": 2, "items": "4 × Wood"}
    for key, fallback in DISPATCH_TEXT.values():
        text = words[key].format(**values)
        for name in ("pet", "units", "item", "trade", "level", "items"):
            assert ("{" + name + "}" in fallback) == ("{" + name + "}" in words[key]), (key, name)
        assert "{" not in text, key
