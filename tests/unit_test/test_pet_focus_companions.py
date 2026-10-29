from frontengine.show.pet.focus_companions import FocusCompanions
import test_pet_social_modes as fixtures

social_pets = fixtures.social_pets


def test_corner_packing_negative_monitor_and_overflow():
    from frontengine.show.pet.focus_placement import corner_positions

    assert corner_positions((-300, -200, 300, 200), [(100, 60)] * 5) == [
        (-112, -72), (-224, -72), (-112, -144), (-224, -144), None]
    assert corner_positions((0, 0, 100, 100), [(100, 100), (20, 20)]) == [None, (68, 68)]


def test_focus_parks_physics_and_restores_unmoved_pet(social_pets):
    _, pets = social_pets
    pet = pets[0]
    area = pet.screen().availableGeometry()
    original = (area.x() + 20, area.y() + 20)
    pet.place_for_focus(*original)
    pet.motion._airborne = True
    focus = FocusCompanions()
    focus.begin([pet])
    assert (pet.x(), pet.y()) != original
    assert (pet.motion.x, pet.motion.y) == (pet.x(), pet.y())
    assert not pet.motion._airborne
    focus.stop()
    assert (pet.x(), pet.y()) == original
    assert (pet.motion.x, pet.motion.y) == original


def test_focus_keeps_position_after_manual_drag_away_and_back(social_pets):
    _, pets = social_pets
    pet = pets[0]
    focus = FocusCompanions()
    focus.begin([pet])
    parked = (pet.x(), pet.y())
    pet.placement_revision += 1
    focus.stop()
    assert (pet.x(), pet.y()) == parked


def test_focus_modes_restore_and_each_completed_round_rewards_once(social_pets):
    _, pets = social_pets
    pets[1].profile_session.set_mode('rest')
    focus = FocusCompanions()
    focus.begin(pets)
    assert all(pet.companion.mode == 'work' for pet in pets)
    focus.transition('break', 1)
    assert all(pet.companion.mode == 'rest' for pet in pets)
    assert all(pet.companion.growth.affection == 3 for pet in pets)
    focus.transition('break', 1)
    assert all(pet.companion.growth.affection == 3 for pet in pets)
    focus.transition('focus', 1)
    focus.transition('long_break', 2)
    assert all(pet.companion.growth.affection == 6 for pet in pets)
    focus.stop()
    assert [pet.companion.mode for pet in pets] == ['play', 'rest', 'play']


def test_manual_choice_even_same_mode_is_not_overwritten(social_pets):
    _, pets = social_pets
    focus = FocusCompanions()
    focus.begin(pets)
    pets[0].profile_session.set_mode('work')
    pets[1].profile_session.set_mode('play')
    focus.transition('break', 1)
    focus.stop()
    assert [pet.companion.mode for pet in pets] == ['work', 'play', 'play']
    assert [pet.companion.growth.affection for pet in pets] == [0, 0, 3]


def test_stop_and_hidden_completion_do_not_award(social_pets):
    _, pets = social_pets
    focus = FocusCompanions()
    focus.begin(pets)
    focus.stop()
    assert all(pet.companion.growth.affection == 0 for pet in pets)
    focus.begin(pets)
    pets[0].hide()
    focus.transition('break', 1)
    pets[0].show()
    focus.transition('break', 1)
    assert pets[0].companion.growth.affection == 0
    focus.stop()


def test_page_focus_timer_drives_modes_and_completion(social_pets):
    from datetime import datetime, timedelta
    from frontengine.utils.focus_timer.focus_timer import FocusTimer

    page, pets = social_pets
    now = [datetime(2026, 1, 1)]
    page.focus_timer = FocusTimer(now_provider=lambda: now[0])
    page.start_focus_session()
    assert pets[0].companion.mode == 'work'
    now[0] += timedelta(minutes=page.focus_timer.focus_minutes)
    page._tick_focus_timer()
    page._tick_focus_timer()
    assert pets[0].companion.mode == 'rest'
    assert pets[0].companion.growth.affection == 3
    page.stop_focus_session()
    assert pets[0].companion.mode == 'play'


def test_default_focus_timer_uses_elapsed_time(monkeypatch):
    from frontengine.utils.focus_timer import focus_timer as module

    now = [100.0]
    monkeypatch.setattr(module, 'monotonic', lambda: now[0])
    timer = module.FocusTimer(focus_minutes=1)
    timer.start()
    now[0] += 59
    assert timer.tick() is None
    now[0] += 1
    assert timer.tick() == 'break'
    assert timer.tick() is None


def test_work_and_rest_suppress_proactive_chatter(social_pets, monkeypatch):
    _, pets = social_pets
    pet = pets[0]
    lines = []
    monkeypatch.setattr(pet, 'say', lambda *args: lines.append(args))
    monkeypatch.setattr(pet, '_check_idle', lambda: False)
    monkeypatch.setattr(pet, '_warn_battery', lambda: False)
    monkeypatch.setattr(pet, '_warn_hungry', lambda: False)
    for mode in ('work', 'rest'):
        pet.profile_session.set_mode(mode)
        pet._on_chatter()
    assert lines == []
    pet.profile_session.set_mode('play')
    pet.profile_session.advance(1.4)  # waking up is a short presentation, then chatter resumes
    pet._on_chatter()
    assert len(lines) == 1
