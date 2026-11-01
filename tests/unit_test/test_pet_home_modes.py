"""Home modes keep the desktop usable; the inbox collects quietly and folds repeats."""
import pytest

from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.home_strip import FRAME_MS
from frontengine.ui.page.pet_game.home_page import MEETING_REASON, PetHomePage
from frontengine.ui.page.pet_game.inbox_panel import category
from frontengine.user_setting.pet_game_save import HomeSaveStore
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_game.catalog import builtin_catalog


@pytest.fixture
def page(tmp_path, monkeypatch):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    for key, value in (("pet_home_running", False), ("pet_home_on_desktop", True), ("pet_home_mode", "normal"),
                       ("pet_home_auto_meeting", True), ("quality_tier", "high")):
        monkeypatch.setitem(user_setting_dict, key, value)
    for name in ("work", "needs", "life", "errors"):
        monkeypatch.setitem(user_setting_dict, "pet_home_notify_" + name, True)
    service = HomeService(None, HomeSaveStore(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    widget = PetHomePage(service)
    widget.create_home()
    widget.residents.new_pet()
    yield widget
    widget.shutdown()


def test_meeting_mode_hides_and_pauses_and_says_so(page):
    strip = page.strip_list[0]
    assert page.service.running
    page.set_mode("meeting")
    assert not strip.isVisible()
    assert MEETING_REASON in page.service.pause_reasons
    assert not page.service.running
    assert "meeting" in page.status.text()
    page.set_mode("normal")
    assert strip.isVisible()
    assert page.service.running


def test_focus_mode_is_quiet_and_saver_only_slows_drawing(page):
    strip = page.strip_list[0]
    page.set_mode("focus")
    resident = next(iter(page.service.world.residents))
    strip._events([{"kind": "greeted", "resident": resident}])
    assert strip.bubbles == {}
    page.set_mode("saver")
    assert strip.frame_timer.interval() == FRAME_MS["saver"]
    assert page.service.timer.interval() == 200          # the world keeps its pace
    page.set_mode("normal")
    assert strip.frame_timer.interval() == FRAME_MS["high"]


def test_screen_sharing_borrows_meeting_mode_and_gives_it_back(page):
    page.set_mode("focus")
    page.sharing_changed(True)
    assert MEETING_REASON in page.service.pause_reasons
    page.sharing_changed(False)
    assert page.service.running
    assert page.mode == "focus"


def test_inbox_sorts_and_folds_everything_that_happened(page):
    world = page.service.world
    resident = next(iter(world.residents))
    paid = {"kind": "settled", "resident": resident, "recipe": "letter", "coins": 12, "time": 1000}
    page.inbox.on_events([paid, {**paid, "time": 30000}, {"kind": "completed", "resident": resident,
                                                          "activity": "eat", "time": 31000}], world)
    assert page.inbox.list.count() == 1
    assert page.inbox.list.item(0).text().endswith("×2")
    assert page.inbox.unread == 2
    page.inbox.on_events([{"kind": "life_event", "event": "birthday", "resident": resident, "time": 40000}], world)
    assert page.inbox.list.count() == 2
    page.inbox.add_error("disk full", 50000)
    assert page.inbox.list.item(0).text() == "disk full"
    page.inbox.mark_read()
    assert page.inbox.count.text() == "0 new"


@pytest.mark.parametrize("event, expected", [
    ({"kind": "settled"}, "work"), ({"kind": "interrupted", "reason": "tired"}, "needs"),
    ({"kind": "interrupted", "reason": "furniture_moved"}, None), ({"kind": "completed"}, None),
    ({"kind": "wish_granted"}, "life"), ({"kind": "settle_failed"}, "errors"),
])
def test_only_meaningful_events_reach_the_inbox(event, expected):
    assert category(event) == expected
