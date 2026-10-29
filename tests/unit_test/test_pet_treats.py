import pytest
from PySide6.QtWidgets import QMenu

from frontengine.show.pet.companion_menu import add_food_actions
from frontengine.utils.pet_companion.stats import FOOD_EFFECTS
import test_pet_social_modes as fixtures
import test_puppet_petting as puppet_fixtures

social_pets = fixtures.social_pets
puppet = puppet_fixtures.puppet


@pytest.mark.parametrize('kind', ['snack', 'feast', 'music', 'book'])
def test_sprite_menu_treat_uses_shared_effects_and_cooldown(social_pets, kind):
    _, pets = social_pets
    pet = pets[0]
    pet.companion.hunger.value = 20
    pet.companion.mood.value = 30
    before = pet.profile_session.state()
    pet.food_actions[kind].trigger()
    assert pet.companion.action == 'feed'
    assert pet.profile_session.state() == before
    pet.profile_session.advance(2)
    effect = FOOD_EFFECTS[kind]
    assert pet.companion.hunger.value == 20 + effect['fullness']
    assert pet.companion.mood.value == 30 + effect['mood']
    assert pet.companion.growth.affection == effect['affection']
    pet.food_actions['snack'].trigger()
    assert pet.companion.action is None


@pytest.mark.parametrize('kind', ['snack', 'feast', 'music', 'book'])
def test_puppet_treat_menu_passes_kind_without_checked_boolean(puppet, kind):
    puppet.profile_session.companion.hunger.value = 20
    menu = QMenu(puppet)
    actions = add_food_actions(menu, puppet.feed)
    actions[kind].trigger()
    assert puppet.profile_session.companion.action == 'feed'
    puppet.profile_session.advance(2)
    assert puppet.profile_session.companion.hunger.value == 20 + FOOD_EFFECTS[kind]['fullness']
    menu.close()


def test_full_pet_declines_every_treat_and_food_removes_toy(social_pets):
    _, pets = social_pets
    pet = pets[0]
    pet.start_ball()
    assert pet._toy is not None
    pet.companion.hunger.value = 100
    before = pet.profile_session.state()
    for action in pet.food_actions.values():
        action.trigger()
        assert pet.companion.action is None
        assert pet.profile_session.state() == before
    assert pet._toy is None


def test_puppet_context_menu_exposes_treats(puppet, monkeypatch):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QContextMenuEvent
    from frontengine.utils.multi_language.retranslate import translate

    class Menu(QMenu):
        def exec(self, *args):
            treats = next(action.menu() for action in self.actions()
                          if action.text() == translate('pet_treats'))
            next(action for action in treats.actions()
                 if action.text() == translate('pet_treat_music')).trigger()

    monkeypatch.setattr('frontengine.show.pet.puppet_pet.QMenu', Menu)
    puppet.profile_session.companion.hunger.value = 20
    puppet.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(10, 10)))
    puppet.profile_session.advance(2)
    assert puppet.profile_session.companion.hunger.value == 35
