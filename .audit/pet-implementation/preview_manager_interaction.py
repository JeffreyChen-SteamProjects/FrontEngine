import os
from pathlib import Path
import sys
import tempfile

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication
from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
from frontengine.ui.page.layout_kit import Section
from frontengine.user_setting.pet_profiles import PetProfiles

app = QApplication([])
font_id = QFontDatabase.addApplicationFont('C:/Windows/Fonts/msjh.ttc')
app.setFont(QFont(QFontDatabase.applicationFontFamilies(font_id)[0], 10))
with tempfile.TemporaryDirectory() as temporary:
    try:
        os.chdir(temporary)
        page = PetSettingUI()
        controls = page.profile_controls
        controls.profiles = PetProfiles({}, lambda: None)
        record = controls.profiles.create('MOCHI')
        controls.refresh(selected=record['id'])
        controls.interaction.setCurrentIndex(controls.interaction.findData('call'))
        controls.call_x.setValue(-80)
        controls.call_y.setValue(-40)
        page.resize(980, 850)
        page.show()
        app.processEvents()
        section = controls.selector.parentWidget()
        while not isinstance(section, Section):
            section = section.parentWidget()
        assert section.grab().save(str(root / '.audit/pet-implementation/manager-interaction.png'))
        page.close()
    finally:
        os.chdir(root)
