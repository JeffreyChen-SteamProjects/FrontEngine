"""Local identity selection and portable single-pet state management."""
from pathlib import Path

from PySide6.QtWidgets import QComboBox, QFileDialog, QLabel, QLineEdit, QPushButton, QSpinBox

from frontengine.show.pet.pet_profile_session import PetProfileSession
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.multi_language.retranslate import retranslator, tr, translate
from frontengine.show.pet.companion_menu import companion_status
from frontengine.utils.pet_companion.stats import TREAT_KINDS


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
        self.customize_button = tr(QPushButton(), 'pet_custom_title', 'Customize pet')
        self.wardrobe_button = tr(QPushButton(), 'pet_wardrobe_title', 'Wardrobe')
        self.recover_button = tr(QPushButton(), 'pet_recover', 'Bring pet back')
        self.interaction = QComboBox()
        tr(self.interaction, 'pet_interact_label', 'Interaction', 'setAccessibleName')
        self.interact_button = tr(QPushButton(), 'pet_interact_run', 'Perform interaction')
        self.call_x, self.call_y = QSpinBox(), QSpinBox()
        for control, key, fallback in (
                (self.call_x, 'pet_call_horizontal', 'Left / right (px)'),
                (self.call_y, 'pet_call_vertical', 'Up / down (px)')):
            control.setRange(-320, 320)
            control.setSingleStep(16)
            tr(control, key, fallback, 'setAccessibleName')
            tr(control, 'pet_call_offset_hint',
               'Negative values move left/up. The destination is limited to nearby work space; floor mode ignores vertical movement.',
               'setToolTip')
        self.call_x.setValue(120)
        self._dialogs = {}
        self._wardrobes = {}
        section = page.add_section('pet_profile_title', 'Pet identities')
        section.add_row(tr(QLabel(), 'pet_profile_select'), self.selector)
        section.add_row(tr(QLabel(), 'pet_profile_name'), self.name)
        section.add_actions(self.rename, self.export, self.import_button, self.refresh_button, self.customize_button)
        section.add_actions(self.wardrobe_button, self.recover_button)
        section.add_row(tr(QLabel(), 'pet_interact_label', 'Interaction'), self.interaction)
        section.add_row(tr(QLabel(), 'pet_call_horizontal', 'Left / right (px)'), self.call_x)
        section.add_row(tr(QLabel(), 'pet_call_vertical', 'Up / down (px)'), self.call_y)
        self.call_hint = tr(QLabel(), 'pet_call_offset_hint',
                            'Negative values move left/up. The destination is limited to nearby work space; floor mode ignores vertical movement.')
        self.call_hint.setWordWrap(True)
        section.add_widget(self.call_hint)
        section.add_actions(self.interact_button)
        hint = tr(QLabel(), 'pet_profile_hint')
        hint.setWordWrap(True)
        section.add_widget(hint)
        section.add_widget(self.status)
        self.selector.currentIndexChanged.connect(self._selected)
        self.rename.clicked.connect(self.rename_selected)
        self.export.clicked.connect(self.export_selected)
        self.import_button.clicked.connect(self.import_save)
        self.refresh_button.clicked.connect(self.refresh)
        self.customize_button.clicked.connect(lambda: self.customize())
        self.wardrobe_button.clicked.connect(lambda: self.wardrobe())
        self.recover_button.clicked.connect(self.recover_selected)
        self.interact_button.clicked.connect(self.interact_selected)
        self.interaction.currentIndexChanged.connect(self._update_call_controls)
        retranslator.bind_call(self.refresh)
        self.refresh()

    def refresh(self, *_args, selected: str | None = None) -> None:
        """Refresh saved names and retain the explicitly selected local identity."""
        identifier = selected if selected is not None else self.selector.currentData()
        selected_action = self.interaction.currentData()
        self.interaction.clear()
        for action in ('greet', 'pet', 'groom', 'cancel', 'play', 'work', 'rest'):
            self.interaction.addItem(translate('pet_companion_' + action), action)
        for kind in TREAT_KINDS:
            self.interaction.addItem(translate('pet_treat_' + kind), 'feed:' + kind)
        self.interaction.addItem(translate('pet_ball_start', 'Throw a ball'), 'ball')
        self.interaction.addItem(translate('pet_light_start', 'Play with a light spot'), 'light')
        self.interaction.addItem(translate('pet_come', 'Come here'), 'call')
        self._selected_action = selected_action
        self.interaction.setCurrentIndex(max(0, self.interaction.findData(selected_action)))
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
        self.customize_button.setEnabled(identifier is not None)
        self.wardrobe_button.setEnabled(identifier is not None)
        self.recover_button.setEnabled(identifier is not None)
        self.interaction.setEnabled(identifier is not None)
        self.interact_button.setEnabled(identifier is not None)
        self._list_pet_commands(identifier)
        self._update_call_controls()
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

    def _list_pet_commands(self, identifier) -> None:
        """Offer the selected live pet's own menu commands (photo, status, model motions...)."""
        selected = self.interaction.currentData() or getattr(self, '_selected_action', None)
        for index in reversed(range(self.interaction.count())):
            if str(self.interaction.itemData(index)).startswith('cmd:'):
                self.interaction.removeItem(index)
        session = PetProfileSession.active(self.profiles, identifier) if identifier else None
        commands = getattr(session.parent(), 'manager_commands', None) if session else None
        position = self.interaction.findData('rest') + 1
        for offset, (command, label) in enumerate(commands() if commands else ()):
            self.interaction.insertItem(position + offset, label, 'cmd:' + command)
        self.interaction.setCurrentIndex(max(0, self.interaction.findData(selected)))

    def _update_call_controls(self, *_args) -> None:
        enabled = self.selector.currentData() is not None and self.interaction.currentData() in ('call', 'light')
        self.call_x.setEnabled(enabled)
        self.call_y.setEnabled(enabled)
        self.call_hint.setVisible(enabled)

    def rename_selected(self) -> None:
        """Change the saved name without modifying this or any other pet's stats."""
        try:
            identifier = self.selector.currentData()
            self.profiles.update(identifier, {'name': self.name.text()})
            self.refresh(selected=identifier)
        except (OSError, ValueError, KeyError) as error:
            self.status.setText(str(error))

    def recover_selected(self) -> None:
        from frontengine.show.pet.recovery import recover_pet

        identifier = self.selector.currentData()
        session = PetProfileSession.active(self.profiles, identifier) if identifier else None
        if session is None:
            self.status.setText(translate('pet_recover_inactive', 'This pet is not active. Start it first.'))
            return
        target = self.page._target_geometry()
        try:
            recover_pet(session.parent(), target[1] if target else None)
        except (ValueError, RuntimeError):
            self.status.setText(translate('pet_recover_failed', 'Could not bring the pet back. Check the screen and reduce the pet size if needed.'))
            return
        self.status.setText(translate('pet_recover_done', 'Pet returned to the selected screen.'))

    def interact_selected(self) -> None:
        identifier = self.selector.currentData()
        session = PetProfileSession.active(self.profiles, identifier) if identifier else None
        if session is None or not session.parent().isVisible():
            self.status.setText(translate('pet_interact_unavailable',
                                          'Start or show this pet before interacting.'))
            return
        command = self.interaction.currentData()
        if command is None:
            return
        pet = session.parent()
        if command.startswith('cmd:'):
            pet.run_manager_command(command[4:])
            self.status.setText(translate('pet_command_done', 'Done.'))
            return
        action, _, kind = command.partition(':')
        if action in ('call', 'light', 'ball'):
            start = getattr(pet, 'start_' + action, None)
            if start is None:
                self.status.setText(translate('pet_call_unsupported', 'This pet does not support movement calls yet.'))
                return
            result = start() if action == 'ball' else start(offset=(self.call_x.value(), self.call_y.value()))
            message = (translate('pet_call_started', 'Destination placed. End interaction cancels the call.')
                       if action == 'call' else translate('pet_light_started', 'Light placed. End interaction puts it away.'))
            if action == 'ball':
                message = translate('pet_ball_started', 'Ball thrown. End interaction puts it away.')
            self.status.setText(message
                                if result == 'accepted' else translate('pet_companion_' + result, result))
            return
        pet._end_petting()
        if hasattr(pet, 'stop_toy'):
            pet.stop_toy()
        if action in ('play', 'work', 'rest'):
            result = session.set_mode(action)
        else:
            result = session.request(action, kind or 'snack')
        pet._interaction_feedback(result)
        self.status.setText(companion_status(session) if result == 'accepted' else translate(
            'pet_companion_' + result, result))

    def customize(self, identifier: str | None = None) -> None:
        from frontengine.ui.dialog.pet_customization import PetCustomizationDialog

        identifier = identifier or self.selector.currentData()
        if identifier is None:
            return
        if identifier in self._dialogs:
            self._dialogs[identifier].show()
            return
        dialog = PetCustomizationDialog(self.profiles, identifier, self.page,
                                        self.page.customization_defaults())
        self._dialogs[identifier] = dialog
        dialog.destroyed.connect(lambda: self._dialogs.pop(identifier, None))
        dialog.show()

    def wardrobe(self, identifier: str | None = None) -> None:
        from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog
        from frontengine.show.pet.puppet_pet import PuppetPetWidget

        identifier = identifier or self.selector.currentData()
        if identifier is None:
            return
        session = PetProfileSession.active(self.profiles, identifier)
        owner = session.parent() if session else None
        if isinstance(owner, PuppetPetWidget):
            self.status.setText(translate('pet_wardrobe_unsupported', 'This model does not support layered sprite clothing'))
            return
        if identifier in self._wardrobes:
            self._wardrobes[identifier].show()
            return
        try:
            dialog = PetWardrobeDialog(self.profiles, identifier, self.page,
                                       library=getattr(owner, 'asset_library', None))
        except (OSError, ValueError) as error:
            self.status.setText(str(error))
            return
        self._wardrobes[identifier] = dialog
        dialog.destroyed.connect(lambda: self._wardrobes.pop(identifier, None))
        dialog.show()

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
