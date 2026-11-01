"""Pets keep the player company during focus sessions, and a dropped file is only a treat."""
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent

from frontengine.show.pet_game.home_service import HomeService
from frontengine.ui.page.pet_game.home_page import PetHomePage
from frontengine.user_setting.pet_game_save import HomeSaveStore
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.pet_game import behaviour
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.world import World

CATALOG = builtin_catalog()
A, B = "b" * 32, "c" * 32


def _world():
    world = World(CATALOG, "a" * 32, seed=6)
    zone = world.add_zone("s", 0, 0, 40)
    world.grant_starter_kit()
    world.furnish(zone)
    for identifier in (A, B):
        world.add_resident({"id": identifier, "name": identifier[:4], "mood": 80, "fullness": 80,
                            "affection": 1, "energy": 90}, zone)
    return world


def test_a_focus_session_queues_work_without_interrupting_anything():
    world = _world()
    busy = world.residents[A]
    behaviour.start(world, busy, "relax", "free_time", duration=60000)
    world.park(B, True)
    assert world.focus_begin() == [A]
    assert busy.activity.kind == "relax"                        # nothing running is cut short
    assert busy.commands == ["work"]
    assert world.open_tasks(A)                                  # it took a job the normal way
    assert world.focus_begin() == []                            # never queued twice


def test_ending_takes_back_only_its_own_untouched_requests():
    world = _world()
    world.residents[B].commands.append("play")                  # the player's own request stays
    world.focus_begin()
    assert world.residents[B].commands == ["play", "work"]
    world.residents[A].commands.clear()                          # A already acted on it
    assert world.focus_end() == [B]
    assert world.residents[B].commands == ["play"]
    assert world.focus_end() == []


def _page(tmp_path, monkeypatch, focus):
    monkeypatch.setitem(user_setting_dict, "pet_home_running", False)
    monkeypatch.setitem(user_setting_dict, "pet_home_on_desktop", True)
    monkeypatch.setitem(user_setting_dict, "pet_home_focus_companion", focus)
    service = HomeService(None, HomeSaveStore(tmp_path, CATALOG), PetProfiles({}, lambda: None))
    page = PetHomePage(service)
    page.create_home()
    page.residents.new_pet()
    return page


def test_the_page_follows_the_focus_timer_only_when_asked(tmp_path, monkeypatch):
    page = _page(tmp_path, monkeypatch, False)
    try:
        resident = next(iter(page.service.world.residents.values()))
        page.focus_phase_changed("focus")
        assert "work" not in resident.commands
        page.work.focus_check.setChecked(True)
        page.focus_phase_changed("focus")
        assert "work" in resident.commands
        page.focus_phase_changed("break")
        assert "work" not in resident.commands
    finally:
        page.shutdown()
        page.deleteLater()


def test_a_file_dropped_on_a_pet_feeds_it_and_is_never_opened(tmp_path, monkeypatch):
    page = _page(tmp_path, monkeypatch, False)
    try:
        strip = page.strip_list[0]
        resident = next(iter(page.service.world.residents.values()))
        resident.needs["fullness"] = 40
        dropped = tmp_path / "notes.txt"
        dropped.write_text("keep me", encoding="utf-8")
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(dropped))])
        point = QPointF(strip.resident_center(resident))
        event = QDropEvent(point, Qt.DropAction.CopyAction, mime, Qt.MouseButton.NoButton,
                           Qt.KeyboardModifier.NoModifier)
        coins, items = page.service.world.ledger.coins, page.service.world.ledger.to_dict()
        strip.dropEvent(event)
        assert resident.needs["fullness"] == 55
        assert dropped.read_text(encoding="utf-8") == "keep me"
        assert page.service.world.ledger.coins == coins
        assert page.service.world.ledger.to_dict() == items
    finally:
        page.shutdown()
        page.deleteLater()


def test_the_main_window_passes_focus_phases_to_the_home(make_main_window):
    from PySide6.QtCore import SIGNAL
    window = make_main_window({"language": "English"})
    assert window.pet_setting_ui.receivers(SIGNAL("focus_phase(QString)")) >= 1
    seen = []
    window.pet_setting_ui.focus_phase.connect(seen.append)
    window.pet_setting_ui.start_focus_session()
    window.pet_setting_ui.stop_focus_session()
    assert seen == ["focus", "stopped"]
