"""Built-in characters exported as Imervue Puppet models: valid, rigged, bound and usable from the Pet page."""
import json
import zipfile

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QThreadPool
from PySide6.QtTest import QTest

from frontengine.show.pet.inkside.cast import TEMPLATES
from frontengine.show.pet.inkside.puppet_export import BINDINGS, export_puppet
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_pack.layered import ACTIONS

pytest.importorskip('Imervue.puppet.document_io')


@pytest.mark.parametrize('template', TEMPLATES, ids=lambda template: template.ident)
def test_every_character_exports_a_valid_bound_puppet(tmp_path, template):
    from Imervue.puppet.document_io import load_puppet
    from Imervue.puppet.validator import validate
    model, script = export_puppet(template.ident, tmp_path)
    with zipfile.ZipFile(model) as archive:
        assert archive.namelist()[0] == 'mimetype'
        assert archive.getinfo('mimetype').compress_type == zipfile.ZIP_STORED
    document = load_puppet(model)
    assert validate(document) == []
    motions = {motion.name for motion in document.motions}
    expressions = {expression.name for expression in document.expressions}
    actions = json.loads(script.read_text(encoding='utf-8'))['frontengine_actions']
    assert set(actions) <= set(ACTIONS)
    for binding in actions.values():
        assert binding.get('motion', 'idle') in motions and binding.get('expression', 'happy') in expressions
    for motion in document.motions:
        assert motion.fade_out_duration > 0  # stopping eases back instead of snapping to frame 0


def test_reactions_move_the_rig_and_return_to_defaults(tmp_path):
    from frontengine.show.pet.puppet_pet import PuppetPetWidget
    model, script = export_puppet('inkside-mochi', tmp_path)
    pet = PuppetPetWidget(model, size=(256, 256), script_path=str(script), profiles=PetProfiles({}, lambda: None))
    try:
        pet.show()
        values = pet.canvas.parameter_values
        defaults = dict(values())
        assert pet.profile_session.request('greet') == 'accepted'
        QTest.qWait(400)
        assert values()['ArmR'] < -1.0
        assert pet.canvas.active_expressions() == ['happy']  # eyes are owned by the expression
        pet.profile_session.advance(1)
        QTest.qWait(600)
        assert pet.canvas.active_expressions() == []
        assert {key: round(value, 3) for key, value in values().items()} == {
            key: round(value, 3) for key, value in defaults.items()}
    finally:
        pet.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_pet_page_generates_and_spawns_a_builtin_puppet(tmp_path, monkeypatch):
    from frontengine.show.pet.puppet_pet import PuppetPetWidget
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
    monkeypatch.chdir(tmp_path)
    page = PetSettingUI()
    try:
        page.profile_controls.profiles = PetProfiles({}, lambda: None)
        page.builtin_puppet.setCurrentIndex(page.builtin_puppet.findData('inkside-gill'))
        page.use_builtin_puppet()
        assert not page.builtin_puppet_button.isEnabled()
        assert QThreadPool.globalInstance().waitForDone(60000)
        QCoreApplication.processEvents()
        assert page.builtin_puppet_button.isEnabled()
        assert page.pet_image_path == str(tmp_path / 'pet-assets' / 'puppets' / 'inkside-gill.puppet')
        assert page.puppet_script_path.endswith('inkside-gill.petscript.json')
        page._spawn_pet()
        assert isinstance(page.pet_list[-1], PuppetPetWidget)
    finally:
        for pet in page.pet_list:
            pet.close()
        page.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_bindings_cover_the_companion_states_puppet_enters():
    assert {'greet', 'pet', 'feed', 'groom', 'play', 'celebrate', 'sleep', 'sleep_in', 'wake', 'walk',
            'sit', 'food_like', 'food_dislike', 'outfit_show', 'peer_greet', 'catch'} <= set(BINDINGS)
