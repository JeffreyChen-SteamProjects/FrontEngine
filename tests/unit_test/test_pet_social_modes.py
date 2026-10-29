"""Both participants must be available; speech is independent of social care."""
import pytest

from frontengine.show.pet.desktop_pet import DesktopPetWidget
from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
from frontengine.user_setting.pet_profiles import PetProfiles
from test_pet_profile_sessions import _sprite


@pytest.fixture
def social_pets(tmp_path):
    page = PetSettingUI()
    profiles = PetProfiles({}, lambda: None)
    pets = [DesktopPetWidget(_sprite(tmp_path), profiles=profiles, talk=False,
                             sit_on_windows=False) for _ in range(3)]
    page.pet_list.extend(pets)
    for index, pet in enumerate(pets):
        pet.move(index * 200, 100)
        pet.profile_session.changed.connect(page._start_tag_game)
        pet.show()
    yield page, pets
    page.tag_timer.stop()
    for pet in pets:
        pet.close()
    page.close()


@pytest.mark.parametrize('restriction', ['work', 'rest', 'interaction', 'social_off', 'hidden', 'typing'])
def test_unavailable_pet_is_neither_peer_target_nor_tag_player(social_pets, restriction):
    page, pets = social_pets
    excluded = pets[1]
    page.tag_checkbox.setChecked(True)
    page._tick_tag_game()
    assert excluded._tag_role is not None
    if restriction in ('work', 'rest'):
        excluded.profile_session.set_mode(restriction)
    elif restriction == 'interaction':
        excluded.profile_session.request('groom')
    elif restriction == 'social_off':
        before = excluded.companion.preferences
        excluded.profile_session.apply_preferences(before, {**before, 'allow_social': False})
    elif restriction == 'hidden':
        excluded.hide()
    else:
        excluded.motion.settled = True
    page._tick_tag_game()
    assert excluded._tag_role is None
    assert excluded.center() not in page._peer_centers(pets[0])
    assert page._peer_centers(excluded) == []
    assert excluded.companion.growth.affection == 0
    assert pets[0]._tag_role is not None and pets[2]._tag_role is not None


def test_game_stops_below_two_players_and_restarts_on_show(social_pets):
    page, pets = social_pets
    page.tag_checkbox.setChecked(True)
    page._tick_tag_game()
    pets[1].hide()
    pets[2].profile_session.set_mode('rest')
    assert not page.tag_timer.isActive()
    assert all(pet._tag_role is None for pet in pets)
    pets[1].show()
    assert page.tag_timer.isActive()
    page._tick_tag_game()
    assert pets[0]._tag_role is not None
    assert pets[1]._tag_role is not None
    assert pets[2]._tag_role is None


def test_quiet_pet_still_greets_without_repeated_reward(social_pets):
    _, pets = social_pets
    pet = pets[0]
    assert not pet._talk
    pet._greet_peer((20, 0), 20, (0, 0))
    assert pet.companion.growth.affection == 3
    pet._greet_peer((20, 0), 20, (0, 0))
    assert pet.companion.growth.affection == 3
    assert not pet._bubble.isVisible()


def test_typing_pause_restarts_tag_when_typing_settles(social_pets, monkeypatch):
    page, pets = social_pets
    monkeypatch.setattr(page, '_pet_typing_enabled', lambda _pet: True)
    page.tag_checkbox.setChecked(True)
    page._tick_tag_game()
    page._apply_settled(True)
    assert not page.tag_timer.isActive()
    assert all(pet._tag_role is None for pet in pets)
    page._apply_settled(False)
    assert page.tag_timer.isActive()
