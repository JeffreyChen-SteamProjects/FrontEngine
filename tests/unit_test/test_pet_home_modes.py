"""Home modes keep the desktop usable; the inbox collects quietly and folds repeats."""
import pytest

from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.home_strip import FRAME_MS
from frontengine.ui.page.pet_game.home_page import MEETING_REASON, PetHomePage
from frontengine.ui.page.pet_game.inbox_panel import category
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_game.catalog import builtin_catalog


@pytest.fixture
def page(tmp_path, monkeypatch, *, home_store_factory, lifetime_factory):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    lifetime_factory()
    for key, value in (("pet_home_running", False), ("pet_home_on_desktop", True), ("pet_home_mode", "normal"),
                       ("pet_home_auto_meeting", True), ("quality_tier", "high")):
        monkeypatch.setitem(user_setting_dict, key, value)
    for name in ("work", "needs", "life", "errors"):
        monkeypatch.setitem(user_setting_dict, "pet_home_notify_" + name, True)
    service = HomeService(None, home_store_factory(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    widget = PetHomePage(service, lifetime=lifetime_factory())
    widget.create_home()
    # creating a home with no pets brings a first one
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


def test_settings_can_leave_meeting_without_the_hidden_strip(page):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    page.set_mode('meeting')
    assert all(not strip.isVisible() for strip in page.strip_list)
    assert page.mode_combo.currentData() == 'meeting'
    assert page.mode_combo.isEnabled()
    QTest.keyClick(page.mode_combo, Qt.Key.Key_Home)
    assert page.mode == 'normal'
    assert page.service.running
    assert all(strip.isVisible() for strip in page.strip_list)


def test_settings_show_temporary_sharing_mode_without_overwriting_preference(page):
    page.set_mode('focus')
    page.sharing_changed(True)
    assert page.mode_combo.currentData() == 'meeting'
    assert not page.mode_combo.isEnabled()
    assert page.mode == 'focus'
    page.sharing_changed(False)
    assert page.mode_combo.currentData() == 'focus'
    assert page.mode_combo.isEnabled()


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


def test_inbox_history_follows_language_changes_and_keeps_repeat_counts(make_main_window):
    from frontengine.ui.menu.language_menu import set_language
    from frontengine.utils.multi_language.retranslate import translate

    window = make_main_window()
    assert set_language('English', window)
    page = window.pet_home_ui
    page.create_home()
    page.service.pause('test')
    world = page.service.world
    resident = next(iter(world.residents.values()))
    event = {'kind': 'settled', 'resident': resident.identifier, 'recipe': 'letter', 'coins': 12, 'time': 1000}
    page.inbox.on_events([event, {**event, 'time': 2000}], world)
    english = page.inbox.list.item(0).text()
    try:
        assert set_language('France', window)
        recipe = world.catalog.recipes['letter']
        expected = translate('pet_home_note_settled').format(
            name=resident.name, recipe=translate(recipe.label_key, recipe.fallback), coins=12)
        assert expected not in english
        assert page.inbox.list.item(0).text() == expected + ' ' + translate('pet_home_note_times').format(count=2)
        assert page.inbox.count.text() == translate('pet_home_inbox_unread').format(count=2)
        page.inbox.on_events([{**event, 'time': 3000}], world)
        assert page.inbox.list.count() == 1
        assert page.inbox.entries[0]['count'] == 3
    finally:
        set_language('English', window)


def test_inbox_history_keeps_names_and_rewards_from_when_the_event_arrived(page):
    world = page.service.world
    resident = next(iter(world.residents.values()))
    resident.name = 'Original name'
    event = {'kind': 'settled', 'resident': resident.identifier, 'recipe': 'letter', 'coins': 12, 'time': 1000}
    page.inbox.on_events([event], world)
    original = page.inbox.list.item(0).text()
    resident.name = 'New name'
    event['coins'] = 99
    page.inbox.refresh_lists()
    assert page.inbox.list.item(0).text() == original
    assert 'Original name' in original
    assert '(+12)' in original
    page.inbox.on_events([{**event, 'coins': 24, 'time': 2000}], world)
    assert page.inbox.list.count() == 2
    assert 'New name' in page.inbox.list.item(0).text()
    assert '(+24)' in page.inbox.list.item(0).text()


@pytest.mark.parametrize("event, expected", [
    ({"kind": "settled"}, "work"), ({"kind": "interrupted", "reason": "tired"}, "needs"),
    ({"kind": "interrupted", "reason": "furniture_moved"}, None), ({"kind": "completed"}, None),
    ({"kind": "wish_granted"}, "life"), ({"kind": "settle_failed"}, "errors"),
])
def test_only_meaningful_events_reach_the_inbox(event, expected):
    assert category(event) == expected


def test_inbox_keeps_different_life_events_and_errors_distinct(page):
    world = page.service.world
    resident = next(iter(world.residents))
    page.inbox.on_events([
        {'kind': 'life_event', 'event': 'friend', 'resident': resident, 'time': 1000},
        {'kind': 'life_event', 'event': 'skilled', 'resident': resident, 'time': 1000},
        {'kind': 'life_event', 'event': 'skilled', 'resident': resident, 'time': 2000},
    ], world)
    assert page.inbox.list.count() == 2
    assert page.inbox.entries[-1]['count'] == 2
    page.inbox.add_error('disk full', 3000)
    page.inbox.add_error('permission denied', 4000)
    assert page.inbox.list.count() == 4
    assert page.inbox.list.item(0).text() == 'permission denied'


def test_inbox_does_not_fold_across_a_clock_reset(page):
    page.inbox.add_error('disk full', 60000)
    page.inbox.add_error('disk full', 0)
    assert page.inbox.list.count() == 2
