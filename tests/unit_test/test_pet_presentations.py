from frontengine.show.pet.focus_companions import FocusCompanions
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_companion.companion import CompanionState
import test_pet_social_modes as fixtures

social_pets = fixtures.social_pets


def test_cosmetic_reaction_expires_without_reward_and_is_not_saved():
    record = PetProfiles({}, lambda: None).create()
    state = CompanionState(record)
    before = state.snapshot()
    assert state.present('outfit_show')
    assert not state.allows_autonomy
    assert state.visual_action == 'outfit_show'
    state.advance(1.99)
    assert state.visual_action == 'outfit_show'
    state.advance(0.01)
    assert state.visual_action is None
    assert state.allows_autonomy
    assert state.snapshot() == before
    assert not state.present('unknown')


def test_user_action_cancels_cosmetic_without_cancelling_interaction():
    state = CompanionState(PetProfiles({}, lambda: None).create())
    state.present('celebrate')
    assert state.request('groom') == 'accepted'
    assert state.visual_action == 'groom'
    assert not state.present('celebrate')
    state.advance(2)
    assert state.action == 'groom'
    state.advance(1)
    assert state.growth.affection == 3
    assert state.visual_action is None
    state.present('celebrate')
    state.set_mode('rest')
    assert state.visual_action == 'sleep_in'
    state.advance(1.5)
    assert state.visual_action == 'sleep'


def test_focus_celebrates_once_then_rest_without_losing_ownership(social_pets):
    _, pets = social_pets
    pet = pets[0]
    focus = FocusCompanions()
    focus.begin([pet])
    focus.transition('break', 1)
    assert pet.companion.mode == 'rest'
    assert pet.companion.visual_action == 'celebrate'
    pet.profile_session.advance(1)
    focus.transition('break', 1)
    assert pet.companion.visual_action == 'celebrate'
    pet.profile_session.advance(1)
    assert pet.companion.visual_action == 'sleep'
    assert pet.companion.growth.affection == 3
    focus.stop()
    assert pet.companion.mode == 'play'


def test_focus_hidden_pet_has_no_celebration_and_manual_override_wins(social_pets):
    _, pets = social_pets
    focus = FocusCompanions()
    focus.begin(pets)
    pets[0].hide()
    focus.transition('break', 1)
    assert pets[0].companion.visual_action == 'sleep_in'
    pets[0].profile_session.advance(1.5)
    assert pets[0].companion.visual_action == 'sleep'
    pets[1].profile_session.set_mode('work')
    assert pets[1].companion.visual_action == 'wake'
    pets[1].profile_session.advance(1.4)
    assert pets[1].companion.visual_action == 'sit'
    focus.stop()
    assert pets[1].companion.mode == 'work'


def test_expiring_presentation_notifies_widget(social_pets):
    _, pets = social_pets
    pet = pets[0]
    changes = []
    pet.profile_session.changed.connect(lambda: changes.append(pet.companion.visual_action))
    assert pet.profile_session.present('outfit_show')
    pet.profile_session.advance(2)
    assert changes == ['outfit_show', None]


def test_desktop_renders_celebration_then_rest_frame(social_pets, tmp_path):
    import copy
    from PySide6.QtGui import QColor, QImage
    from frontengine.show.pet.layered_renderer import LayeredRenderer
    from frontengine.utils.pet_pack.layered import load_layered_asset
    from test_pet_layered import make_asset, write

    root = tmp_path / 'celebrating'
    data = make_asset(root)
    data['actions']['sleep'] = copy.deepcopy(data['actions']['idle'])
    data['actions']['celebrate'] = copy.deepcopy(data['actions']['idle'])
    red = QImage(2, 2, QImage.Format.Format_ARGB32)
    red.fill(QColor('red'))
    assert red.save(str(root / 'celebrate.png'))
    for frame in data['actions']['celebrate']['frames']:
        frame['layers'][0]['image'] = 'celebrate.png'
    write(root, data)
    _, pets = social_pets
    pet = pets[0]
    pet._layered_playback.clock = lambda: 0.0
    pet.profile_session.appearance_renderer = LayeredRenderer(load_layered_asset(root))
    pet.profile_session.changed.emit()
    focus = FocusCompanions()
    focus.begin([pet])
    focus.transition('break', 1)
    assert pet._current_pixmap().toImage().pixelColor(2, 2) == QColor('red')
    pet.profile_session.advance(2)
    assert pet._current_pixmap().toImage().pixelColor(2, 2) == QColor('blue')
    focus.stop()
