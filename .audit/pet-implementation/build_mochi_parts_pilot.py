"""Copy generated sources unchanged and verify them through the real wardrobe."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
from PySide6.QtWidgets import QApplication
from PIL import Image
from frontengine.show.pet.asset_library import PetAssetLibrary
from frontengine.show.pet.wardrobe import WardrobeDraft, asset_reference
from frontengine.user_setting.pet_profiles import PetProfiles

app = QApplication.instance() or QApplication([])
source = Path('C:/Users/USER/.codex/generated_images/01a181f4-55e5-7273-ac56-4e68ff5e7fb8')
parent = root / 'docs/design/assets/pet-parts-pilot-2026-10-29'
package = parent / 'mochi-face-draft-1'
package.mkdir(parents=True, exist_ok=True)
sources = {
    'base.png': 'exec-13b3ca6a-ac7e-44f9-8a05-9a384ad4feb0.png',
    'deadpan.png': 'exec-91ba09e8-ba29-4dd0-ab48-72d5708e3985.png',
    'drowsy.png': 'exec-66ca5365-97c9-426b-a982-d3d7ecad664f.png',
}
inspection = {}
for name, original in sources.items():
    target = package / name
    shutil.copyfile(source / original, target)
    with Image.open(target) as image:
        alpha = image.getchannel('A')
        inspection[name] = {'source': original, 'size': image.size, 'mode': image.mode,
                            'alpha_extrema': alpha.getextrema(),
                            'low_alpha_pixels': sum(alpha.histogram()[1:16]),
                            'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
rejected = parent / 'rejected'
rejected.mkdir(exist_ok=True)
shutil.copyfile(source / 'exec-87d671f0-f4f0-419c-a13e-791e26696ada.png', rejected / 'registration-attempt.png')
layers = [{'image': 'base.png', 'z': 0, 'anchor': None, 'offset': [0, 0]}]
for choice in ('deadpan', 'drowsy'):
    layers.append({'image': choice + '.png', 'z': 10, 'anchor': None, 'offset': [-65, -30],
                   'variant': ['face', choice]})
manifest = {'format': 'frontengine.layered-pet/1', 'id': 'inkside-mochi-face-pilot',
            'version': 'draft-1', 'name': 'MOCHI face study — unfinished', 'kind': 'character',
            'template': 'mochi-face-pilot', 'canvas': [1254, 1254], 'slots': [],
            'license': 'Project-generated development artwork; see ../provenance.md',
            'variants': {'face': {'name': 'Face study', 'default': 'deadpan',
                                  'choices': {'deadpan': 'Deadpan', 'drowsy': 'Drowsy'}}},
            'actions': {'idle': {'loop': True, 'frames': [{'duration_ms': 1000, 'anchors': {}, 'layers': layers}]}}}
(package / 'layered-pet.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
with tempfile.TemporaryDirectory(prefix='frontengine-parts-') as temporary:
    library = PetAssetLibrary(Path(temporary) / 'library')
    installed = library.install(package)
    catalog, errors = library.scan()
    assert not errors
    profiles = PetProfiles({}, lambda: None)
    first, second = profiles.create('MOCHI'), profiles.create('Other')
    draft = WardrobeDraft(profiles, first['id'], catalog)
    draft.choose_character(asset_reference(installed))
    original = draft.preview.render('idle', 0)
    assert original.save(str(parent / 'deadpan-runtime-preview.png'))
    draft.set_variant('face', 'drowsy')
    changed = draft.preview.render('idle', 0)
    assert changed != original
    assert changed.save(str(parent / 'drowsy-runtime-preview.png'))
    draft.save_outfit('Drowsy study')
    draft.apply()
    assert profiles.get(second['id']) == second
    reopened = WardrobeDraft(profiles, first['id'], catalog)
    assert reopened.prepare_preview().render('idle', 0) == changed
inspection['runtime'] = {'installed': True, 'variant_pixels_differ': True,
                          'apply_reopen_matches': True, 'second_identity_unchanged': True,
                          'production_art_approved': False, 'native_acceptance': False}
(parent / 'validation.json').write_text(json.dumps(inspection, indent=2), encoding='utf-8')
print(json.dumps({'package': str(package), 'runtime': inspection['runtime']}))
