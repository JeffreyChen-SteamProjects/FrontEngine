"""The home pauses while the computer is locked, and furniture shows what is happening at it."""
from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.home_strip import LOCKED_REASON
from frontengine.show.pet_game.home_view import HomeView
from frontengine.ui.page.pet_game.home_page import PetHomePage
from frontengine.user_setting.pet_game_save import HomeSaveStore
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.world import World
from frontengine.utils.session_lock.session_lock import SessionLockWatcher

CATALOG = builtin_catalog()


def test_the_watcher_reports_changes_only_and_treats_errors_as_unlocked():
    states = [False, True, True, False]
    seen = []
    watcher = SessionLockWatcher(probe=lambda: states.pop(0))
    watcher.locked_changed.connect(seen.append)
    for _ in range(4):
        watcher.check()
    assert seen == [True, False]

    def broken():
        raise OSError("no desktop")
    watcher.probe = broken
    assert watcher.check() is False


def test_locking_pauses_the_home_and_unlocking_resumes_it(tmp_path, monkeypatch):
    monkeypatch.setitem(user_setting_dict, "pet_home_running", True)
    monkeypatch.setitem(user_setting_dict, "pet_home_on_desktop", False)
    service = HomeService(None, HomeSaveStore(tmp_path, CATALOG), PetProfiles({}, lambda: None))
    page = PetHomePage(service)
    try:
        page.create_home()
        service.start()
        page.lock_watcher.probe = lambda: True
        page.lock_watcher.check()
        assert LOCKED_REASON in service.pause_reasons
        assert not service.running
        assert "locked" in page._status_text(service.world, False)
        page.lock_watcher.probe = lambda: False
        page.lock_watcher.check()
        assert LOCKED_REASON not in service.pause_reasons
    finally:
        page.shutdown()
        page.deleteLater()


def _world():
    world = World(CATALOG, "a" * 32, seed=1)
    zone = world.add_zone("s", 0, 0, 30)
    world.grant_starter_kit()
    world.furnish(zone)
    return world, zone


def test_badges_show_use_the_trade_and_a_finished_job():
    world, zone = _world()
    view = HomeView()
    view.set_world(world, zone)
    now = [100.0]
    view.badge_clock = lambda: now[0]
    desk = next(p for p in world.furniture.values() if p.definition == "desk_basic")
    table = next(p for p in world.furniture.values() if p.definition == "table_basic")
    assert view.piece_badge(desk, world.definition(desk)) == ""
    desk.users[0] = "x" * 32
    table.users[0] = "x" * 32
    assert view.piece_badge(desk, world.definition(desk)) == "✎"
    assert view.piece_badge(table, world.definition(table)) == "•"
    view.badges[desk.identifier] = now[0] + 4
    assert view.piece_badge(desk, world.definition(desk)) == "✓"
    now[0] += 5
    assert view.piece_badge(desk, world.definition(desk)) == "✎"
    view.deleteLater()
