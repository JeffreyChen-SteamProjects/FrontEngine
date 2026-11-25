"""The pet home: what the whole-project review found."""
import json

import pytest
from PySide6.QtCore import QEvent, QPointF
from PySide6.QtWidgets import QMenu

from frontengine.show.pet.pet_profile_session import PetProfileSession
from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.resident_art import LOOK_SECONDS, ResidentArt
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.pet_game import simulation, snapshot
from frontengine.utils.pet_game.arrangement import decode_layout
from frontengine.utils.pet_game.blueprint import visit_blueprint
from frontengine.utils.pet_game.catalog import FURNITURE_PREFIX, builtin_catalog, check_furniture
from frontengine.utils.pet_game.commission_work import dispatch
from frontengine.utils.pet_game.content_pack import load_packs
from frontengine.utils.pet_game.jobs import MAX_TASKS
from frontengine.utils.pet_game.layout import MAX_FURNITURE
from frontengine.utils.pet_game.world import World

DEEP = "[" * 60000
PET = "a" * 32


def _world(mode="manage"):
    world = World(builtin_catalog(), "b" * 32, mode, 7)
    world.add_zone("screen", 0, 900, 40)
    world.grant_starter_kit()
    return world


def _resident(world, identifier=PET, name="Pip", fullness=70):
    record = {"id": identifier, "name": name, "energy": 70, "fullness": fullness, "mood": 60, "affection": 0}
    assert world.add_resident(record, next(iter(world.zones))) == "accepted"
    return world.residents[identifier]


@pytest.fixture
def home(tmp_path, *, home_store_factory):
    profiles = PetProfiles({}, lambda: None)
    service = HomeService(None, home_store_factory(tmp_path / "home", builtin_catalog()), profiles)
    service.create_home("screen", 0, 900, 40, seed=3)
    yield service, profiles
    service.shutdown()


def test_furniture_from_a_pack_that_is_gone_sells_for_nothing():
    catalog = builtin_catalog()
    assert catalog.sell_price(FURNITURE_PREFIX + "good__bed") == 0 and catalog.sell_price("good__herb") == 0
    assert catalog.sell_price(FURNITURE_PREFIX + "armchair") > 0


def test_the_home_page_opens_with_stored_furniture_of_a_missing_pack(make_main_window):
    page = make_main_window().pet_home_ui
    page.create_home()
    page.service.run(lambda world: world.ledger.items.update({FURNITURE_PREFIX + "good__bed": 1}))
    page.refresh()


def test_json_nested_too_deeply_is_refused_not_raised_through(tmp_path):
    pack = tmp_path / "deep"
    pack.mkdir()
    (pack / "pack.json").write_text(DEEP, encoding="utf-8")
    packs, errors = load_packs(tmp_path)
    assert packs == [] and "deep" in errors
    with pytest.raises(ValueError):
        decode_layout(DEEP[:8000], builtin_catalog())
    with pytest.raises(ValueError):
        visit_blueprint(DEEP, builtin_catalog())


def test_care_earned_on_the_desktop_is_kept_when_the_home_takes_the_pet_back(home):
    service, profiles = home
    record = profiles.create("Pip")
    assert service.adopt(record["id"]) == "accepted"
    service.save_now()
    for session in service.sessions.values():          # the home lets go, the pet runs on the desktop
        session.close()
    service.sessions.clear()
    profiles.update(record["id"], {"affection": 50, "mood": 99, "name": "Pippa"})
    resident = service.world.residents[record["id"]]
    resident.away = True
    service._look_for_returns()
    assert not resident.away and (resident.affection, resident.needs["mood"], resident.name) == (50, 99, "Pippa")
    service.save_now()
    assert profiles.get(record["id"])["affection"] == 50
    resident.affection = 80                              # the home's own, not mirrored yet: the higher one stays
    service.sessions.pop(record["id"]).close()
    profiles.update(record["id"], {"affection": 60})
    service.retry_leases()
    assert resident.affection == 80


def test_a_pet_still_on_the_desktop_stays_away(home):
    service, profiles = home
    record = profiles.create("Pip")
    assert service.adopt(record["id"]) == "accepted"
    service.sessions.pop(record["id"]).close()
    outside = PetProfileSession(None, record["id"], profiles)
    resident = service.world.residents[record["id"]]
    resident.away = True
    service._look_for_returns()
    assert resident.away
    outside.close()
    service._look_for_returns()
    assert not resident.away


def test_a_renamed_pet_has_its_new_name_at_home(home):
    service, profiles = home
    record = profiles.create("Pip")
    service.adopt(record["id"])
    profiles.update(record["id"], {"name": "Nova"})
    service.save_now()
    assert service.world.residents[record["id"]].name == "Nova"


def test_drawing_a_pet_does_not_read_every_profile_each_time(home, *, lifetime_factory, monkeypatch):
    service, profiles = home
    record = profiles.create("Pip")
    service.adopt(record["id"])
    art = ResidentArt(service, lifetime=lifetime_factory())
    reads, clock = [], [0.0]
    real = PetProfileSession.state
    monkeypatch.setattr(PetProfileSession, "state", lambda self: reads.append(True) or real(self))
    monkeypatch.setattr("frontengine.show.pet_game.resident_art.monotonic", lambda: clock[0])
    for _frame in range(50):
        art.renderer(record["id"])
    assert len(reads) == 1
    clock[0] = LOOK_SECONDS + .1
    art.renderer(record["id"])
    assert len(reads) == 2
    art.forget_looks()
    art.renderer(record["id"])
    assert len(reads) == 3
    art.shutdown()


def test_a_pet_parked_with_its_screen_comes_back_with_it_even_after_a_restart():
    world = _world()
    resident = _resident(world)
    world.set_offline(set(world.zones))
    assert resident.parked
    again = snapshot.from_dict(json.loads(json.dumps(snapshot.to_dict(world))), builtin_catalog())
    assert again.residents[PET].parked                   # the screen may still be away
    again.set_offline(set())
    assert not again.residents[PET].parked


def test_a_pet_moved_out_of_an_offline_zone_lives_on():
    world = _world()
    resident = _resident(world)
    first = next(iter(world.zones))
    second = world.add_zone("other", 0, 900, 40)
    world.set_offline({first})
    assert resident.parked
    world.transfer_resident(PET, second)
    assert not resident.parked
    world.transfer_resident(PET, first)
    assert resident.parked


def test_moving_a_zone_to_a_screen_that_is_there_wakes_it(make_main_window):
    window = make_main_window()
    page = window.pet_home_ui
    page.create_home()
    world = page.service.world
    zone = page.zone
    world.zones[zone].screen = "unplugged"
    page.screens_changed()
    assert world.offline_zones == {zone}
    page.move_zone(page.screens()[0])
    assert world.offline_zones == set()


def test_a_place_to_sleep_or_eat_must_fill_what_it_is_for():
    catalog = builtin_catalog()
    for name in ("bed_cozy", "table_basic"):
        check_furniture(catalog.furniture[name])
        from dataclasses import replace
        with pytest.raises(ValueError):
            check_furniture(replace(catalog.furniture[name], effects={}))


def test_unreadable_pet_profiles_do_not_stop_the_window(make_main_window):
    window = make_main_window({"pet_profiles": {"version": 3, "migrated": True, "records": {}}})
    page = window.pet_home_ui
    assert page.saved_profiles() == [] and page.newcomers.count() == 0


def test_a_hungry_pet_waits_its_turn_at_a_full_table():
    world = _world()
    resident = _resident(world, fullness=22)
    from frontengine.utils.pet_game.behaviour import start
    start(world, resident, "wait", "table_full", duration=20000)
    for _step in range(20):
        simulation.advance(world, 200)
    events = [event for event in world.drain_events() if event.get("kind") == "interrupted"]
    assert events == [] and resident.activity.kind == "wait"


def test_focus_ending_leaves_the_work_the_player_asked_for(monkeypatch):
    from frontengine.utils.pet_game import commission_work
    world = _world()
    resident = _resident(world)
    recipe = next(iter(world.catalog.recipes))
    monkeypatch.setattr(commission_work, "plan", lambda _world, _index: commission_work.Dispatch("accepted", PET, recipe, 1))
    monkeypatch.setattr(commission_work, "refusal", lambda *_arguments: None)
    world._focus_owned.add(PET)                          # queued by the focus session first
    resident.commands.append("work")
    assert dispatch(world, 0).result == "accepted"
    assert world.focus_end() == [] and "work" in resident.commands


def test_a_home_full_of_one_removed_pack_still_loads():
    assert snapshot.MAX_DORMANT >= MAX_FURNITURE + MAX_TASKS


def test_pausing_from_the_desktop_is_remembered(make_main_window):
    page = make_main_window().pet_home_ui
    page.create_home()
    page.service.start()
    page.desktop_check.setChecked(True)
    page.sync_strip()
    strip = page.strip_list[0]
    strip._fill_home_menu()
    pause = strip.button.menu().actions()[1]
    pause.trigger()
    assert not page.service.running and user_setting_dict["pet_home_running"] is False
    strip._fill_home_menu()
    strip.button.menu().actions()[1].trigger()
    assert page.service.running and user_setting_dict["pet_home_running"] is True


def test_the_desktop_toolbar_follows_the_language(make_main_window):
    from frontengine.utils.multi_language.language_wrapper import language_wrapper
    from frontengine.utils.multi_language.retranslate import retranslator
    page = make_main_window().pet_home_ui
    page.create_home()
    page.desktop_check.setChecked(True)
    page.sync_strip()
    strip = page.strip_list[0]
    before = [button.text() for button in strip.shortcut_buttons] + [strip.button.toolTip()]
    try:
        language_wrapper.reset_language("Deutsch")
        retranslator.apply()
        after = [button.text() for button in strip.shortcut_buttons] + [strip.button.toolTip()]
    finally:
        language_wrapper.reset_language("English")
        retranslator.apply()
    assert all(old != new for old, new in zip(before, after))


def test_a_context_menu_is_gone_once_closed(make_main_window):
    from PySide6.QtCore import QCoreApplication, QPoint
    page = make_main_window().pet_home_ui
    page.create_home()
    page.desktop_check.setChecked(True)
    page.sync_strip()
    strip = page.strip_list[0]
    for _time in range(3):
        strip._context_menu(None, None, QPoint(5, 5))
        strip.last_menu.hide()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert len([menu for menu in strip.findChildren(QMenu) if menu.parent() is strip]) == 0


def test_an_outing_pet_whose_drag_was_cut_short_moves_on():
    from types import SimpleNamespace
    from frontengine.show.pet_game.home_outing import OutingPet
    thrown = []
    pet = OutingPet.__new__(OutingPet)
    super(OutingPet, pet).__init__()
    pet._press, pet._dragging = QPointF(1, 1), True
    pet.motion = SimpleNamespace(throw=lambda x, y: thrown.append((x, y)))
    pet.event(QEvent(QEvent.Type.UngrabMouse))
    assert pet._press is None and pet._dragging is False and thrown == [(0.0, 0.0)]
    pet.deleteLater()
