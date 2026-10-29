"""Render the wardrobe offscreen using unmistakable colored test fixtures."""
import os
from pathlib import Path
import sys
import tempfile

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root), str(root / 'tests/unit_test')]
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase

app = QApplication([])
font = QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
assert font >= 0
app.setFont(QFont(QFontDatabase.applicationFontFamilies(font)[0], 10))
with tempfile.TemporaryDirectory() as directory:
    os.chdir(directory)
    from test_pet_palette import palette_asset
    from frontengine.show.pet.asset_library import PetAssetLibrary
    from frontengine.show.pet.wardrobe import asset_reference
    from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog
    from frontengine.user_setting.pet_profiles import PetProfiles

    source = Path(directory) / 'fixture-cat'
    palette_asset(source)
    library = PetAssetLibrary(Path(directory) / 'library')
    asset = library.install(source)
    profiles = PetProfiles({}, lambda: None)
    identity = profiles.create('QA fixture — not production artwork')
    dialog = PetWardrobeDialog(profiles, identity['id'], library=library)
    dialog.character.setCurrentIndex(dialog.character.findData(asset_reference(asset)))
    dialog._choose_character()
    dialog.show()
    app.processEvents()
    assert dialog.grab().save(str(root / '.audit/pet-implementation/wardrobe-preview.png'))
    dialog.close()
    app.processEvents()
    os.chdir(root)
