"""Mode transitions, tiredness, energy costs and short physical reactions on desktop pets."""
import pytest

from frontengine.show.pet import desktop_pet
from frontengine.utils.pet_companion.companion import CompanionState
import test_pet_social_modes as fixtures

social_pets = fixtures.social_pets


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch):
    fake = Clock()
    monkeypatch.setattr(desktop_pet, 'monotonic', fake)
    return fake


def test_entering_and_leaving_rest_play_their_transitions():
    state = CompanionState({})
    state.set_mode('rest')
    assert state.visual_action == 'sleep_in' and not state.allows_autonomy
    state.advance(1.49)
    assert state.visual_action == 'sleep_in'
    state.advance(0.01)
    assert state.visual_action == 'sleep'
    state.set_mode('work')
    assert state.visual_action == 'wake'
    state.advance(1.4)
    assert state.visual_action == 'sit'
    state.set_mode('play')
    assert state.visual_action is None and state.allows_autonomy
    before = state.snapshot()
    state.set_mode('play')
    assert state.snapshot() == before and state.visual_action is None


def test_automatic_rest_also_plays_the_falling_asleep_transition():
    state = CompanionState({'energy': 11, 'preferences': {'auto_rest': True}})
    state.advance(30)
    assert state.mode == 'rest' and state.visual_action == 'sleep_in'
    state.advance(1.5)
    assert state.visual_action == 'sleep'


def test_play_and_toys_cost_energy_and_low_energy_is_visible_without_auto_rest():
    state = CompanionState({'energy': 30, 'preferences': {'auto_rest': False}})
    assert state.request('play') == 'accepted'
    state.advance(3)
    assert state.energy == 26
    assert state.reward('ball') == 'accepted'
    assert state.energy == 24 and not state.tired
    assert state.reward('fetch') == 'accepted' and state.energy == 22
    assert state.reward('tag') == 'accepted' and state.energy == 21
    state.advance(30)
    assert state.energy == 20 and state.tired and state.mode == 'play'
    assert state.request('greet') == 'accepted'  # tiredness never refuses the user


def test_tired_idle_pet_sits_and_flashes_expire_on_the_active_clock(social_pets, clock):
    _, pets = social_pets
    pet = pets[0]
    pet.motion.state = 'idle'
    assert pet._autonomous_visual() == 'idle'
    pet.companion.energy = 15
    assert pet._autonomous_visual() == 'sit'
    pet.flash('land')
    assert pet._autonomous_visual() == 'land'
    clock.now += 0.279
    assert pet._autonomous_visual() == 'land'
    clock.now += 0.002
    assert pet._autonomous_visual() == 'sit'


def test_landing_and_catching_the_ball_trigger_reactions(social_pets, clock):
    _, pets = social_pets
    pet = pets[0]
    pet.motion.landings += 1
    pet._watch_reactions(None)
    assert pet._flash[0] == 'land'
    pet._flash = None
    pet._watch_reactions(None)
    assert pet._flash is None

    class Ball:
        phase = 'return'
    pet._toy = Ball()
    pet._watch_reactions('chase')
    assert pet._flash[0] == 'catch'
    pet._flash = None
    pet._watch_reactions('return')
    assert pet._flash is None
    pet._toy = None


def test_meeting_a_peer_waves_once_per_approach(social_pets, clock):
    _, pets = social_pets
    pet = pets[0]
    center = (pet.x() + pet.width() / 2, pet.y() + pet.height() / 2)
    pet._greet_peer((center[0] + 10, center[1]), 10, center)
    assert pet._flash[0] == 'peer_greet'
    pet._flash = None
    pet._greet_peer((center[0] + 10, center[1]), 10, center)
    assert pet._flash is None


def test_user_interactions_take_priority_over_flashes(social_pets, clock):
    _, pets = social_pets
    pet = pets[0]
    pet.flash('peer_greet')
    assert pet.profile_session.request('groom') == 'accepted'
    pet._on_tick()
    assert pet._layered_playback.action == 'groom'


def test_legacy_sprite_packs_fall_back_for_new_actions(social_pets):
    _, pets = social_pets
    pet = pets[0]
    for action in ('sit', 'land', 'catch', 'peer_greet', 'wake', 'sleep_in'):
        assert pet._sprite_for(action) is not None


def test_bond_stages_vary_greetings_and_celebrate_once_when_reached():
    from frontengine.utils.pet_companion.stats import bond_stage
    assert [bond_stage(value) for value in (0, 19, 20, 99, 100, 249, 250)] == [
        'new', 'new', 'familiar', 'familiar', 'close', 'close', 'in_sync']
    state = CompanionState({'affection': 19})
    assert state.request('greet') == 'accepted'
    assert state.visual_action == 'greet'
    state.advance(0.75)
    assert state.bond == 'familiar' and state.visual_action == 'celebrate'
    state.advance(2)
    assert state.visual_action is None
    for affection, visual in ((100, 'peer_greet'), (300, 'celebrate')):
        warm = CompanionState({'affection': affection})
        warm.request('greet')
        assert warm.visual_action == visual


def test_status_names_the_relationship_stage(social_pets):
    from frontengine.show.pet.companion_menu import companion_status
    from frontengine.utils.multi_language.retranslate import translate
    _, pets = social_pets
    pets[0].companion.growth.affection = 120
    assert companion_status(pets[0].profile_session).endswith(translate('pet_bond_close'))


def test_resummoned_pet_welcomes_once_and_new_pet_stays_quiet(tmp_path, monkeypatch):
    from frontengine.show.pet.desktop_pet import DesktopPetWidget
    from frontengine.user_setting.pet_profiles import PetProfiles
    from test_pet_profile_sessions import _sprite
    profiles = PetProfiles({}, lambda: None)
    known = profiles.create('Known')
    profiles.update(known['id'], {'affection': 30})
    lines = []
    monkeypatch.setattr(DesktopPetWidget, 'say', lambda self, text=None: lines.append((self, text)))
    fresh = DesktopPetWidget(_sprite(tmp_path), profiles=profiles, talk=True, sit_on_windows=False)
    returning = DesktopPetWidget(_sprite(tmp_path), profiles=profiles, profile_id=known['id'], talk=True,
                                 sit_on_windows=False)
    try:
        for pet in (fresh, returning):
            pet.show()
            pet.hide()
            pet.show()
        welcomes = [pet for pet, _ in lines]
        assert welcomes == [returning]
        assert returning._flash[0] == 'peer_greet'
    finally:
        fresh.close()
        returning.close()


def test_menu_close_waves_goodbye_before_closing(tmp_path, monkeypatch):
    from PySide6.QtTest import QTest
    from shiboken6 import isValid
    from frontengine.show.pet.desktop_pet import DesktopPetWidget
    from frontengine.user_setting.pet_profiles import PetProfiles
    from test_pet_profile_sessions import _sprite
    pet = DesktopPetWidget(_sprite(tmp_path), profiles=PetProfiles({}, lambda: None), sit_on_windows=False)
    pet.show()
    lines = []
    monkeypatch.setattr(pet, 'say', lambda text=None: lines.append(text))
    pet.close_action.trigger()
    pet.close_action.trigger()
    assert pet.isVisible() and len(lines) == 1 and pet._flash[0] == 'peer_greet'
    # The close follows the 900 ms wave; wait for it instead of a fixed 950 ms,
    # which left 50 ms of margin and failed on a loaded macOS runner.
    for _ in range(60):
        QTest.qWait(50)
        if not isValid(pet) or not pet.isVisible():
            break
    assert not isValid(pet) or not pet.isVisible()


def test_peer_greetings_repeat_at_most_once_a_minute(social_pets, clock):
    _, pets = social_pets
    pet = pets[0]
    center = (pet.x() + pet.width() / 2, pet.y() + pet.height() / 2)
    near, far = (center[0] + 10, center[1]), (center[0] + 900, center[1])
    pet._greet_peer(near, 10, center)
    assert pet._flash[0] == 'peer_greet'
    pet._flash = None
    pet._greet_peer(far, 900, center)  # walk away, then come back quickly
    pet._greet_peer(near, 10, center)
    assert pet._flash is None
    clock.now += 61
    pet._greet_peer(far, 900, center)
    pet._greet_peer(near, 10, center)
    assert pet._flash[0] == 'peer_greet'


def test_grooming_ends_in_a_stretch_that_fits_the_three_second_action():
    from frontengine.show.pet.inkside.rig import timelines
    from frontengine.utils.pet_companion.companion import ACTION_SECONDS
    loop, frames = timelines()['groom']
    assert not loop
    assert sum(frame.duration for frame in frames) == int(ACTION_SECONDS['groom'] * 1000)
    stretch = frames[-1]
    assert stretch.eyes == 'happy' and stretch.angle('arm_l') > 90 and stretch.angle('arm_r') < -90
