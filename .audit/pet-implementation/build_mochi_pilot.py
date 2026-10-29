"""Write only metadata and verify original generated images without editing pixels."""
import json
import os
from pathlib import Path
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
asset_root = root / 'docs/design/assets/pet-animation-pilot-2026-10-28/mochi-draft-1'
from PIL import Image
import numpy as np

report = {}
for path in asset_root.glob('*.png'):
    with Image.open(path) as image:
        alpha = np.asarray(image.getchannel('A'))
        y, x = np.where(alpha >= 200)
        report[path.name] = {'size': list(image.size), 'alpha_range': [int(alpha.min()), int(alpha.max())],
                             'visible_bounds': list(image.getchannel('A').getbbox()),
                             'opaque_bounds': [int(x.min()), int(y.min()), int(x.max()) + 1, int(y.max()) + 1],
                             'translucent_pixels': int(np.count_nonzero((alpha > 0) & (alpha < 200)))}
        assert image.mode == 'RGBA' and image.size == (1254, 1254)
        assert alpha.min() == 0 and alpha.max() == 255

def frame(image, duration, offset_y=0):
    return {'duration_ms': duration, 'anchors': {},
            'layers': [{'image': image, 'z': 0, 'anchor': None, 'offset': [0, offset_y]}]}

manifest = {'format': 'frontengine.layered-pet/1', 'id': 'inkside-mochi-pilot', 'version': 'draft-1',
            'name': 'MOCHI - animation pilot (unfinished)', 'kind': 'character',
            'template': 'inkside-mochi-pilot-1254', 'canvas': [1254, 1254], 'slots': [],
            'license': 'Project development draft generated with OpenAI image_gen; see ../provenance.md. Not approved production art.',
            'actions': {'idle': {'loop': True, 'frames': [frame('idle.png', 1000)]},
                        'walk': {'loop': True, 'frames': [frame('idle.png', 220), frame('walk-step.png', 220, 22)]},
                        'sleep': {'loop': True, 'frames': [frame('sleep.png', 1000, 24)]}}}
(asset_root / 'layered-pet.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

from PySide6.QtWidgets import QApplication
app = QApplication([])
with tempfile.TemporaryDirectory() as directory:
    os.chdir(directory)
    from frontengine.show.pet.asset_library import PetAssetLibrary
    from frontengine.show.pet.wardrobe import WardrobeDraft, asset_reference
    from frontengine.show.pet.desktop_pet import DesktopPetWidget
    from frontengine.user_setting.pet_profiles import PetProfiles
    library = PetAssetLibrary(Path(directory) / 'installed')
    installed = library.install(asset_root)
    catalog, errors = library.scan()
    assert not errors
    profiles = PetProfiles({}, lambda: None)
    identity = profiles.create('MOCHI pilot')
    draft = WardrobeDraft(profiles, identity['id'], catalog)
    draft.choose_character(asset_reference(installed))
    prepared = draft.apply()
    assert prepared.render('walk', 0) != prepared.render('walk', 220)
    pet = DesktopPetWidget(str(asset_root / 'idle.png'), profiles=profiles, profile_id=identity['id'],
                           asset_library=library, talk=False, sit_on_windows=False)
    try:
        assert pet.appearance_error is None
        pet._set_active_sprite('sleep')
        assert not pet._current_pixmap().isNull()
        report['runtime'] = {'installed': True, 'restart_restored': True,
                             'walk_frames_differ': True, 'sleep_frame_loaded': True,
                             'native_desktop_verified': False}
    finally:
        pet.close()
        app.processEvents()
        os.chdir(root)
(asset_root.parent / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report))
