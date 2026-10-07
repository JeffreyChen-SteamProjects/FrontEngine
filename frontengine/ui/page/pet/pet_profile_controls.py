"""Local identity selection and portable single-pet state management."""
from pathlib import Path

from PySide6.QtWidgets import QComboBox, QFileDialog, QLabel, QLineEdit, QPushButton

from frontengine.show.pet.pet_profile_session import PetProfileSession
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.multi_language.retranslate import retranslator, tr, translate


class PetProfileControls:
    """Keep local save identity separate from portable overlay preset settings."""

    def __init__(self, page) -> None:
        self.page = page
        self.profiles = PetProfiles(user_setting_dict, write_user_setting)
        self.selector = QComboBox()
        self.name = QLineEdit()
        retranslator.bind(self.name, 'pet_profile_name', setter='setPlaceholderText')
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.rename = tr(QPushButton(), 'pet_profile_rename')
        self.export = tr(QPushButton(), 'pet_profile_export')
        self.import_button = tr(QPushButton(), 'pet_profile_import')
        self.refresh_button = tr(QPushButton(), 'pet_profile_refresh')
        section = page.add_section('pet_profile_title', 'Pet identities')
        section.add_row(tr(QLabel(), 'pet_profile_select'), self.selector)
        section.add_row(tr(QLabel(), 'pet_profile_name'), self.name)
        section.add_inline(self.rename, self.export, self.import_button, self.refresh_button)
        hint = tr(QLabel(), 'pet_profile_hint')
        hint.setWordWrap(True)
        section.add_widget(hint)
        section.add_widget(self.status)
        self.selector.currentIndexChanged.connect(self._selected)
        self.rename.clicked.connect(self.rename_selected)
        self.export.clicked.connect(self.export_selected)
        self.import_button.clicked.connect(self.import_save)
        self.refresh_button.clicked.connect(self.refresh)
        retranslator.bind_call(self.refresh)
        self.refresh()

    def refresh(self, *_args, selected: str | None = None) -> None:
        """Refresh saved names and retain the explicitly selected local identity."""
        identifier = selected if selected is not None else self.selector.currentData()
        self.selector.blockSignals(True)
        self.selector.clear()
        self.selector.addItem(translate('pet_profile_new'), None)
        try:
            for record in self.profiles.profiles():
                self.selector.addItem(record['name'] + ' · ' + record['id'][:8], record['id'])
        except ValueError as error:
            self.status.setText(str(error))
        index = self.selector.findData(identifier)
        self.selector.setCurrentIndex(max(0, index))
        self.selector.blockSignals(False)
        self._selected()

    def _selected(self, *_args) -> None:
        identifier = self.selector.currentData()
        self.rename.setEnabled(identifier is not None)
        self.export.setEnabled(identifier is not None)
        if identifier is None:
            self.name.clear()
            self.status.clear()
            return
        try:
            session = PetProfileSession.active(self.profiles, identifier)
            record = session.state() if session else self.profiles.get(identifier)
            self.name.setText(record['name'])
            self.status.setText(translate('pet_profile_stats').format(**record))
        except (OSError, ValueError) as error:
            self.status.setText(str(error))

    def rename_selected(self) -> None:
        """Change the saved name without modifying this or any other pet's stats."""
        try:
            identifier = self.selector.currentData()
            self.profiles.update(identifier, {'name': self.name.text()})
            self.refresh(selected=identifier)
        except (OSError, ValueError, KeyError) as error:
            self.status.setText(str(error))

    def export_selected(self) -> None:
        """Flush live state before exporting the selected individual save."""
        destination, _filter = QFileDialog.getSaveFileName(self.page, translate('pet_profile_export'),
                                                          'pet-save.json', 'JSON (*.json)')
        if not destination:
            return
        try:
            identifier = self.selector.currentData()
            session = PetProfileSession.active(self.profiles, identifier)
            if session and not session.flush():
                raise OSError(translate('pet_profile_save_failed'))
            self.profiles.export_profile(identifier, Path(destination))
            self._selected()
        except (OSError, ValueError) as error:
            self.status.setText(str(error))

    def import_save(self) -> None:
        """Import into a fresh identity; choose a sprite/puppet before spawning."""
        source, _filter = QFileDialog.getOpenFileName(self.page, translate('pet_profile_import'), '', 'JSON (*.json)')
        if not source:
            return
        try:
            record = self.profiles.import_profile(Path(source))
            self.refresh(selected=record['id'])
        except (OSError, ValueError) as error:
            self.status.setText(str(error))
