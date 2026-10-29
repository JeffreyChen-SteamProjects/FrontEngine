import os
from pathlib import Path
import sys
import tempfile

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root), str(root / 'tests/unit_test')]
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication
from test_pet_palette import palette_asset
from frontengine.show.pet.asset_library import PetAssetLibrary
from frontengine.show.pet.wardrobe import asset_reference
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog

app = QApplication([])
font_id = QFontDatabase.addApplicationFont('C:/Windows/Fonts/msjh.ttc')
assert font_id >= 0
app.setFont(QFont(QFontDatabase.applicationFontFamilies(font_id)[0], 10))
with tempfile.TemporaryDirectory() as temporary:
    try:
        os.chdir(temporary)
        path = Path(temporary)
        palette_asset(path / 'cat')
        library = PetAssetLibrary(path / 'library')
        asset = library.install(path / 'cat')
        profiles = PetProfiles({}, lambda: None)
        record = profiles.create('MOCHI color controls')
        dialog = PetWardrobeDialog(profiles, record['id'], library=library)
        dialog.character.setCurrentIndex(dialog.character.findData(asset_reference(asset)))
        dialog._choose_character()
        dialog.show()
        QCoreApplication.processEvents()
        dialog.swatches['#ff7417'].setFocus()
        assert dialog.grab().save(str(root / '.audit/pet-implementation/wardrobe-swatches.png'))
        dialog.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    finally:
        os.chdir(root)
