"""Detached per-pet preferences with explicit, atomic application."""
from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from frontengine.show.pet.pet_profile_session import PetProfileSession
from frontengine.user_setting.pet_profile_schema import (
    checked_profile, presentation_defaults as default_presentation, profile_defaults,
)
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.multi_language.retranslate import retranslator, tr
from frontengine.utils.pet_companion.stats import TREAT_KINDS


class PetCustomizationDialog(QDialog):
    """Edit one identity without changing its name, care state or wardrobe."""

    def __init__(self, profiles: PetProfiles, identifier: str,
                 parent: QWidget | None = None,
                 presentation_defaults: dict | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        tr(self, 'pet_custom_title', 'Customize pet', 'setWindowTitle')
        self.profiles, self.identifier = profiles, identifier
        session = PetProfileSession.active(profiles, identifier)
        record = session.state() if session else profiles.get(identifier)
        self.expected = copy.deepcopy(record['preferences'])
        owner = session.parent() if session else None
        self.defaults = copy.deepcopy(getattr(owner, '_presentation_defaults', None)
                                      or presentation_defaults or default_presentation())
        self.supported = getattr(owner, 'customization_fields', None)
        checked_profile({**record, 'preferences': {**self.expected, 'presentation': self.defaults}})
        self.controls: dict[str, QWidget] = {}
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)
        self._care_controls(form)
        self._presentation_controls(form)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        for key, fallback, callback in (
            ('apply', 'Apply', self.apply_changes),
            ('reset', 'Reset defaults', self.reset_defaults),
            ('cancel', 'Cancel', self.reject),
        ):
            button = tr(QPushButton(), 'pet_custom_' + key, fallback)
            button.clicked.connect(callback)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self._load(self.expected)
        if self.supported is not None:
            for key in ('auto_rest', 'allow_throw', 'allow_social'):
                self.controls[key].setEnabled(key in self.supported)

    def _care_controls(self, form: QFormLayout) -> None:
        for key, fallback in (('auto_rest', 'Rest automatically'),
                              ('allow_throw', 'Allow throwing'),
                              ('allow_social', 'Allow social interactions'),
                              ('use_defaults', 'Use page defaults')):
            control = tr(QCheckBox(), 'pet_custom_' + key, fallback)
            self.controls[key] = control
            form.addRow(control)
        self.controls['use_defaults'].toggled.connect(self._toggle_presentation)
        for key, fallback in (('favorite', 'Favorite treat'), ('disliked', 'Disliked treat')):
            control = QComboBox()
            control.addItem('', None)
            tr(control, 'pet_taste_none', 'No preference', 'setItemText', 0)
            for index, kind in enumerate(TREAT_KINDS, 1):
                control.addItem('', kind)
                tr(control, 'pet_treat_' + kind, kind.title(), 'setItemText', index)
            self.controls[key] = control
            form.addRow(tr(QLabel(), 'pet_taste_' + key, fallback), control)

    def _presentation_controls(self, form: QFormLayout) -> None:
        for key, low, high in (('size', 16, 512), ('speed', 1, 20), ('volume', 0, 100)):
            control = QSpinBox()
            control.setRange(low, high)
            self.controls[key] = control
            form.addRow(tr(QLabel(), 'pet_' + key + '_label', key.title()), control)
        behaviour = QComboBox()
        for index, value in enumerate(('floor', 'wander', 'chase')):
            behaviour.addItem('', value)
            tr(behaviour, 'pet_behaviour_' + value, value.title(), 'setItemText', index)
        self.controls['behaviour'] = behaviour
        form.addRow(tr(QLabel(), 'pet_behaviour_label', 'Behaviour'), behaviour)
        for key, label, fallback in (
            ('climb', 'pet_climb_label', 'Climb walls'),
            ('sit_on_windows', 'pet_sit_label', 'Sit on windows'),
            ('speech_bubbles', 'pet_talk_label', 'Speech bubbles'),
            ('settle_typing', 'pet_settle_typing', 'Settle while typing'),
        ):
            control = tr(QCheckBox(), label, fallback)
            self.controls[key] = control
            form.addRow(control)

    def _toggle_presentation(self, use_defaults: bool) -> None:
        for key in self.defaults:
            self.controls[key].setEnabled(not use_defaults and (
                self.supported is None or key in self.supported))

    def _load(self, preferences: dict) -> None:
        for key in ('favorite', 'disliked'):
            control = self.controls[key]
            control.setCurrentIndex(control.findData(preferences.get('taste', {}).get(key)))
        for key in ('auto_rest', 'allow_throw', 'allow_social'):
            self.controls[key].setChecked(preferences[key])
        self.controls['use_defaults'].setChecked(preferences['presentation'] is None)
        values = preferences['presentation'] or self.defaults
        for key, value in values.items():
            control = self.controls[key]
            if isinstance(control, QSpinBox):
                control.setValue(value)
            elif isinstance(control, QComboBox):
                control.setCurrentIndex(control.findData(value))
            else:
                control.setChecked(value)
        self._toggle_presentation(preferences['presentation'] is None)

    def reset_defaults(self) -> None:
        """Stage defaults; nothing is persisted until Apply."""
        self._load(profile_defaults()['preferences'])

    def _candidate(self) -> dict:
        candidate = {key: self.controls[key].isChecked()
                     for key in ('auto_rest', 'allow_throw', 'allow_social')}
        values = {}
        for key in self.defaults:
            control = self.controls[key]
            if isinstance(control, QSpinBox):
                values[key] = control.value()
            elif isinstance(control, QComboBox):
                values[key] = control.currentData()
            else:
                values[key] = control.isChecked()
        candidate['presentation'] = None if self.controls['use_defaults'].isChecked() else values
        taste = {key: self.controls[key].currentData() for key in ('favorite', 'disliked')}
        if any(value is not None for value in taste.values()):
            candidate['taste'] = taste
        return candidate

    def apply_changes(self) -> bool:
        """Commit a detached draft, retaining it on conflicts or save errors."""
        candidate = self._candidate()
        taste = candidate.get('taste', {})
        if taste.get('favorite') is not None and taste.get('favorite') == taste.get('disliked'):
            retranslator.set_text(self.status, 'pet_taste_conflict',
                                  'Choose different treats for favorite and disliked.')
            return False
        try:
            session = PetProfileSession.active(self.profiles, self.identifier)
            if session:
                session.apply_preferences(self.expected, candidate)
            else:
                if self.profiles.get(self.identifier)['preferences'] != self.expected:
                    raise ValueError('Pet preferences changed while editing')
                self.profiles.update(self.identifier, {'preferences': candidate})
            self.expected = self.profiles.get(self.identifier)['preferences']
        except (OSError, ValueError, KeyError):
            retranslator.set_text(self.status, 'pet_custom_conflict',
                                  'Could not save. Your draft is unchanged; reopen if this pet changed elsewhere.')
            return False
        retranslator.set_text(self.status, 'pet_custom_saved', 'Preferences saved')
        return True
