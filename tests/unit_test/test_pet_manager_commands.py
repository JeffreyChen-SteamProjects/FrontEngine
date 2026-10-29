"""Every pet menu command is reachable from the pet manager with the keyboard."""
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

import test_pet_social_modes as fixtures
import test_puppet_petting as puppet_fixtures

social_pets = fixtures.social_pets
puppet = puppet_fixtures.puppet


def _controls(page, pet):
    controls = page.profile_controls
    controls.profiles = pet.profile_session.profiles
    controls.refresh(selected=pet.profile_session.identifier)
    return controls


def _run(controls, command):
    index = controls.interaction.findData('cmd:' + command)
    assert index >= 0, command
    controls.interaction.setFocus()
    controls.interaction.setCurrentIndex(index)
    controls.interact_button.setFocus()
    QTest.keyClick(controls.interact_button, Qt.Key.Key_Space)


def test_sprite_menu_commands_run_from_the_manager(social_pets, monkeypatch):
    page, pets = social_pets
    pet = pets[0]
    calls = []
    for name in ('open_photo', 'show_status', '_prompt_reminder', 'say_goodbye'):
        monkeypatch.setattr(pet, name, lambda name=name: calls.append(name))
    pet.clone_requested.connect(lambda: calls.append('clone'))
    controls = _controls(page, pet)
    offered = {controls.interaction.itemData(i) for i in range(controls.interaction.count())}
    assert {'cmd:photo', 'cmd:status', 'cmd:reminder', 'cmd:clone', 'cmd:close'} <= offered
    assert 'cmd:chat' not in offered  # only when a chat service is attached
    for command in ('photo', 'status', 'reminder', 'clone', 'close'):
        _run(controls, command)
    assert calls == ['open_photo', 'show_status', '_prompt_reminder', 'clone', 'say_goodbye']
    assert controls.interaction.itemData(controls.interaction.count() - 1) == 'call'


def test_switching_pets_replaces_the_command_list(social_pets):
    page, pets = social_pets
    controls = _controls(page, pets[0])
    first = [controls.interaction.itemData(i) for i in range(controls.interaction.count())]
    controls.selector.setCurrentIndex(0)  # "new pet": no live pet, no pet commands
    assert not any(str(data).startswith('cmd:') for data in
                   (controls.interaction.itemData(i) for i in range(controls.interaction.count())))
    controls.refresh(selected=pets[0].profile_session.identifier)
    assert [controls.interaction.itemData(i) for i in range(controls.interaction.count())] == first


def test_puppet_motions_and_expressions_are_listed_and_run(social_pets, puppet, monkeypatch):
    page, _ = social_pets
    played = []
    monkeypatch.setattr(puppet, 'play_motion', lambda name: played.append(name))
    controls = _controls(page, puppet)
    document = puppet.canvas.document()
    for motion in document.motions:
        _run(controls, 'motion:' + motion.name)
    assert played == [motion.name for motion in document.motions]
    for expression in document.expressions:
        _run(controls, 'expression:' + expression.name)
        assert expression.name in puppet.canvas.active_expressions()
        _run(controls, 'expression:' + expression.name)
        assert expression.name not in puppet.canvas.active_expressions()
