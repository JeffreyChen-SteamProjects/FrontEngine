import json
from types import SimpleNamespace

import pytest
from frontengine.show.pet.puppet_reactions import load_reactions


@pytest.mark.parametrize('binding', [
    {'feed': {'motion': 'missing'}}, {'feed': {'expression': 'missing'}},
    {'unknown': {'motion': 'wave'}}, {'feed': {}}, {'feed': {'motion': 1}},
])
def test_reaction_bindings_reject_unknown_native_assets(tmp_path, binding):
    path = tmp_path / 'script.json'
    path.write_text(json.dumps({'frontengine_actions': binding}), encoding='utf-8')
    document = SimpleNamespace(motions=[SimpleNamespace(name='wave')], expressions=[])
    with pytest.raises(ValueError):
        load_reactions(path, document)


def test_reactions_use_native_player_and_restore_only_owned_expression(tmp_path, monkeypatch):
    pytest.importorskip('Imervue.puppet.document_io')
    from Imervue.puppet.document import Motion, Expression
    from frontengine.show.pet.puppet_pet import PuppetPetWidget
    from frontengine.user_setting.pet_profiles import PetProfiles
    from test_puppet_startup_lifecycle import asset

    pet = PuppetPetWidget(asset(tmp_path), profiles=PetProfiles({}, lambda: None))
    try:
        document = pet.canvas.document()
        motion = Motion(name='wave', duration=3.0)
        expression = Expression(name='happy')
        document.motions.append(motion)
        document.expressions.append(expression)
        script = tmp_path / 'script.json'
        script.write_text(json.dumps({'frontengine_actions': {
            'feed': {'motion': 'wave', 'expression': 'happy'},
            'celebrate': {'motion': 'wave', 'expression': 'happy'}}}), encoding='utf-8')
        pet.reactions.bindings = load_reactions(script, document)
        pet.show()
        pet.feed()
        assert pet.player.motion() is motion
        assert pet.canvas.active_expressions() == ['happy']
        pet.profile_session.advance(2)
        assert pet.canvas.active_expressions() == []
        # A user-selected expression predating the reaction remains selected.
        pet._choose_expression('happy', True)
        pet.profile_session.present('celebrate')
        pet.profile_session.advance(2)
        assert pet.canvas.active_expressions() == ['happy']
        pet._choose_expression('happy', False)
        pet.profile_session.present('celebrate')
        assert pet.canvas.active_expressions() == ['happy']
        # Taking manual control releases the reaction before applying the choice.
        pet._choose_expression('happy', True)
        pet.profile_session.advance(2)
        assert pet.canvas.active_expressions() == ['happy']
        pet.profile_session.present('celebrate')
        pet.set_settled(True)
        assert pet.reactions.motion is None
        pet.set_settled(False)
        assert pet.reactions.motion is motion
        pet.hide()
        assert pet.reactions.motion is None
    finally:
        pet.close()
