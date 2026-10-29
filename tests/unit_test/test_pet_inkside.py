"""Built-in INKSIDE characters and wardrobe: generated assets pass the real loader and renderer."""
import json
from pathlib import Path

import numpy
import pytest
from PySide6.QtGui import QImage

from frontengine.show.pet.asset_library import PetAssetLibrary
from frontengine.show.pet.inkside.assemble import build_character, build_garment, garment_identifier
from frontengine.show.pet.inkside.cast import TEMPLATES
from frontengine.show.pet.inkside.garments import GARMENTS, OUTFITS
from frontengine.show.pet.inkside.library import install_builtin
from frontengine.show.pet.layered_renderer import LayeredRenderer
from frontengine.utils.pet_pack.layered import ACTIONS, SPRITE_ACTIONS, load_layered_asset, validate_outfit


def _pixels(image: QImage) -> bytes:
    image = image.convertToFormat(QImage.Format.Format_ARGB32)
    return bytes(image.constBits())


def _alpha(image: QImage) -> numpy.ndarray:
    image = image.convertToFormat(QImage.Format.Format_ARGB32)
    data = numpy.frombuffer(bytes(image.constBits()), dtype=numpy.uint8)
    return data.reshape((image.height(), image.bytesPerLine() // 4, 4))[:, :image.width(), 3].copy()


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp('inkside')
    assets = {}
    for template in TEMPLATES:
        character = load_layered_asset(build_character(template, root / template.ident))
        garments = {garment.ident: load_layered_asset(build_garment(garment, template,
                                                                    root / garment_identifier(garment, template)))
                    for garment in GARMENTS}
        assets[template.ident] = (character, garments)
    return assets


def test_every_character_covers_every_action_and_part_choice(built):
    for character, _ in built.values():
        assert set(ACTIONS) <= set(character.actions) <= set(ACTIONS) | set(SPRITE_ACTIONS)
        assert {'eyes', 'mouth'} <= set(character.variants)
        assert len(character.variants) >= 4
        for group, spec in character.variants.items():
            assert len(spec['choices']) >= 2
            images = {_pixels(LayeredRenderer(character, variants={group: choice}).render('idle', 0))
                      for choice in spec['choices']}
            assert len(images) == len(spec['choices']), (character.identifier, group)


def test_every_garment_fits_every_body_type_and_outfits_combine(built):
    for character, garments in built.values():
        for garment in garments.values():
            validate_outfit(character, (garment,))
        for _name, _home, pieces in OUTFITS:
            validate_outfit(character, tuple(garments[piece] for piece in pieces))


def _outfits_for_clipping(character, garments):
    for garment in GARMENTS:
        if 'head' in garment.slots:
            extra = ('gear-pack',) if 'body' in garment.slots else ('moon-cape', 'gear-pack', 'big-scarf')
            yield {}, (garments[garment.ident], *(garments[piece] for piece in extra))
    for group, spec in character.variants.items():
        for choice in spec['choices']:
            yield {group: choice}, (garments['top-hat'],)


def test_no_frame_is_clipped_by_the_canvas(built):
    """Jumps, lying down and swaying keep every hat, tail and part choice on the canvas."""
    for ident, (character, garments) in built.items():
        for variants, outfit in _outfits_for_clipping(character, garments):
            renderer = LayeredRenderer(character, outfit, variants=variants)
            for action, animation in character.actions.items():
                elapsed = 0
                for frame in animation.frames:
                    alpha = _alpha(renderer.render(action, elapsed))
                    edges = (alpha[0, :], alpha[-1, :], alpha[:, 0], alpha[:, -1])
                    assert all(edge.max() == 0 for edge in edges), (ident, variants, outfit[0].identifier,
                                                                    action, elapsed)
                    elapsed += frame.duration_ms


def test_garments_move_with_the_pose_and_cover_the_body(built):
    character, garments = built['inkside-mochi']
    bare = LayeredRenderer(character)
    dressed = LayeredRenderer(character, (garments['work-cap'], garments['work-jacket']))
    for action in ('idle', 'walk', 'sleep', 'climb', 'greet'):
        assert dressed.render(action, 0) != bare.render(action, 0)
    walk = [dressed.render('walk', time) for time in (0, 140, 280)]
    assert walk[0] != walk[1] != walk[2]


def test_palette_regions_recolor_only_their_own_pixels(built):
    character, _ = built['inkside-mochi']
    plain = _alpha(LayeredRenderer(character).render('idle', 0))
    recolored = LayeredRenderer(character, colors={'inkside-mochi@1': {'coat': '#00a080'}}).render('idle', 0)
    original = LayeredRenderer(character).render('idle', 0)
    assert recolored != original
    assert numpy.array_equal(_alpha(recolored), plain)


def test_assets_pack_images_into_a_few_atlases(built, tmp_path):
    character, _ = built['inkside-gill']
    files = list(character.root.glob('*.png'))
    assert 1 <= len(files) <= 12
    manifest = json.loads((character.root / 'layered-pet.json').read_text(encoding='utf-8'))
    layer = manifest['actions']['idle']['frames'][0]['layers'][0]
    assert len(layer['source']) == 4


def _single_layer_asset(folder: Path, image: QImage, source, canvas=(64, 64)) -> Path:
    folder.mkdir()
    image.fill(0xff000000)
    assert image.save(str(folder / 'atlas.png'))
    layer = {'image': 'atlas.png', 'z': 0, 'anchor': None, 'offset': [0, 0]}
    if source is not None:
        layer['source'] = source
    manifest = {'format': 'frontengine.layered-pet/1', 'id': 'atlas', 'version': '1', 'name': 'Atlas',
                'kind': 'character', 'template': 't', 'canvas': list(canvas), 'slots': [], 'license': 'test',
                'actions': {'idle': {'loop': True, 'frames': [{'duration_ms': 100, 'anchors': {},
                                                                'layers': [layer]}]}}}
    (folder / 'layered-pet.json').write_text(json.dumps(manifest), encoding='utf-8')
    return folder


def test_atlas_source_rectangles_are_bounded(tmp_path):
    big = QImage(300, 120, QImage.Format.Format_ARGB32)
    good = load_layered_asset(_single_layer_asset(tmp_path / 'good', big, [200, 20, 40, 30]))
    assert LayeredRenderer(good).render('idle', 0).pixelColor(39, 29).alpha() == 255
    outside = load_layered_asset(_single_layer_asset(tmp_path / 'outside', big, [280, 0, 40, 30]))
    with pytest.raises(ValueError, match='exceeds its image'):
        LayeredRenderer(outside)
    with pytest.raises(ValueError, match='fit the canvas'):
        load_layered_asset(_single_layer_asset(tmp_path / 'wide', big, [0, 0, 80, 30]))
    whole = load_layered_asset(_single_layer_asset(tmp_path / 'whole', big, None))
    with pytest.raises(ValueError, match='canvas'):
        LayeredRenderer(whole)
    with pytest.raises(ValueError, match='canvas or atlas'):
        PetAssetLibrary(tmp_path / 'lib').install(tmp_path / 'whole')


def test_builtin_install_is_validated_and_idempotent(tmp_path):
    library = PetAssetLibrary(tmp_path / 'library')
    progress = []
    assert install_builtin(library, 'inkside-ink', progress=lambda done, total: progress.append(done)) == 1 + len(GARMENTS)
    assert progress[-1] == 1 + len(GARMENTS)
    assert install_builtin(library, 'inkside-ink') == 0
    catalog, errors = library.scan()
    assert errors == ()
    assert len(catalog.assets('character')) == 1 and len(catalog.assets('garment')) == len(GARMENTS)
    with pytest.raises(ValueError, match='Unknown built-in'):
        install_builtin(library, 'nobody')


def _finish_jobs():
    from PySide6.QtCore import QCoreApplication, QThreadPool
    assert QThreadPool.globalInstance().waitForDone(120000)
    QCoreApplication.processEvents()


def test_wardrobe_installs_dresses_and_applies_a_builtin_character(tmp_path):
    from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog
    from frontengine.user_setting.pet_profiles import PetProfiles

    profiles = PetProfiles({}, lambda: None)
    record = profiles.create('Mochi')
    dialog = PetWardrobeDialog(profiles, record['id'], library=PetAssetLibrary(tmp_path / 'library'))
    try:
        assert dialog.builtin.count() == len(TEMPLATES)
        dialog.builtin.setCurrentIndex(dialog.builtin.findData('inkside-mochi'))
        dialog._install_builtin()
        assert not dialog.builtin_button.isEnabled() and not dialog.install_button.isEnabled()
        _finish_jobs()
        assert dialog._install_job is None and dialog.builtin_button.isEnabled()
        character = {'id': 'inkside-mochi', 'version': '1'}
        dialog.character.setCurrentIndex(dialog.character.findData(character))
        dialog._choose_character()
        for slot, piece in (('head', 'work-cap'), ('body', 'work-jacket')):
            control = dialog.slots[slot]
            control.setCurrentIndex(control.findData({'id': f'inkside-mochi-{piece}', 'version': '1'}))
            dialog._choose_slot(slot)
        assert dialog.apply_changes()
        appearance = profiles.get(record['id'])['appearance']
        assert appearance['character'] == character
        assert appearance['equipped']['head'] == {'id': 'inkside-mochi-work-cap', 'version': '1'}
        assert dialog.preview.pixmap() is not None
    finally:
        dialog.close()


def test_closing_the_wardrobe_cancels_a_builtin_install(tmp_path):
    from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog
    from frontengine.user_setting.pet_profiles import PetProfiles

    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    library = PetAssetLibrary(tmp_path / 'library')
    dialog = PetWardrobeDialog(profiles, record['id'], library=library)
    dialog._install_builtin()
    job = dialog._install_job
    dialog.reject()
    assert job.cancel.is_set()
    _finish_jobs()
    assert library.scan()[0].assets('character') == ()
    assert not any(path.name.startswith('.install-') for path in (tmp_path / 'library').glob('*'))


def test_builtin_part_and_garment_labels_follow_the_language(tmp_path):
    from frontengine.show.pet.inkside.labels import asset_label, label
    from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog
    from frontengine.user_setting.pet_profiles import PetProfiles
    from frontengine.utils.multi_language.language_wrapper import language_wrapper
    from frontengine.utils.multi_language.retranslate import retranslator

    library = PetAssetLibrary(tmp_path / 'library')
    install_builtin(library, 'inkside-moss')
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    original = language_wrapper.language
    dialog = PetWardrobeDialog(profiles, record['id'], library=library)
    try:
        dialog.character.setCurrentIndex(dialog.character.findData({'id': 'inkside-moss', 'version': '1'}))
        dialog._choose_character()
        dialog.variant_group.setCurrentIndex(dialog.variant_group.findData('eyes'))
        dialog.variant_choice.setCurrentIndex(dialog.variant_choice.findData('half'))
        dialog._choose_variant()
        for language, eyes, half, hat in (('Traditional_Chinese', '眼睛', '半閉眼', '遮陽帽'),
                                          ('English', 'Eyes', 'Half closed', 'Sun hat')):
            language_wrapper.reset_language(language)
            retranslator.apply()
            assert dialog.variant_group.currentText() == eyes
            assert dialog.variant_choice.currentText() == half
            head = dialog.slots['head']
            sun_hat = head.findData({'id': 'inkside-moss-sun-hat', 'version': '1'})
            assert head.itemText(sun_hat).startswith('SEED KEEPER · ' + hat)
        assert label('third-party-pack', 'Eyes') == 'Eyes'
        assert asset_label(type('Asset', (), {'identifier': 'other', 'name': 'A · B'})()) == 'A · B'
    finally:
        language_wrapper.reset_language(original)
        retranslator.apply()
        dialog.close()


@pytest.mark.parametrize('ident', [template.ident for template in TEMPLATES])
def test_sprite_walk_replaces_the_layered_walk_only_for_an_undressed_default_pet(built, ident):
    character, garments = built[ident]
    assert {'walk_sprite', 'climb_sprite'} <= set(character.actions)
    bare = LayeredRenderer(character)
    frames = {_pixels(bare.render('walk', index * 90)) for index in range(8)}
    assert len(frames) == 8
    assert _pixels(bare.render('walk', 0)) == _pixels(bare.render('walk_sprite', 0))
    dressed = LayeredRenderer(character, (next(iter(garments.values())),))
    assert _pixels(dressed.render('walk', 0)) != _pixels(dressed.render('walk_sprite', 0))
    group, spec = next(iter(character.variants.items()))
    other = next(choice for choice in spec['choices'] if choice != spec['default'])
    varied = LayeredRenderer(character, variants={group: other})
    assert _pixels(varied.render('walk', 0)) != _pixels(varied.render('walk_sprite', 0))


def test_builtin_install_works_when_the_temp_folder_is_reached_through_a_symlink(tmp_path, monkeypatch):
    """macOS temp lives under /var, a symlink to /private/var; layered assets reject symlinked ancestors."""
    import tempfile
    physical = tmp_path / 'physical'
    physical.mkdir()
    alias = tmp_path / 'alias'
    try:
        alias.symlink_to(physical, target_is_directory=True)
    except OSError as failure:
        pytest.skip(f'Directory symlinks are unavailable: {failure}')
    monkeypatch.setattr(tempfile, 'tempdir', str(alias))
    library = PetAssetLibrary(tmp_path / 'library')
    assert install_builtin(library, 'inkside-pip') == 1 + len(GARMENTS)

