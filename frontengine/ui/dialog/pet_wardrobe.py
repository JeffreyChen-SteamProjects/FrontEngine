"""Identity-specific wardrobe preview and explicit appearance commits."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QThreadPool, Slot
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QVBoxLayout, QFileDialog, QColorDialog,
)

from frontengine.show.pet.asset_library import PetAssetLibrary
from frontengine.show.pet.layered_playback import LayeredPlayback
from frontengine.show.pet.wardrobe import WardrobeDraft, WardrobeError, asset_reference, garment_fit
from frontengine.user_setting.pet_profile_schema import SLOTS
from frontengine.utils.multi_language.retranslate import retranslator, tr, translate
from frontengine.show.pet.inkside.labels import asset_label, label
from frontengine.show.pet.inkside.library import builtin_names
from frontengine.ui.dialog.pet_asset_install import PetAssetInstall, PetBuiltinInstall


class PetWardrobeDialog(QDialog):
    """Stage clothes on a separate clock; the desktop changes only on Apply."""

    def __init__(self, profiles, identifier, parent=None, library=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        tr(self, 'pet_wardrobe_title', 'Wardrobe', 'setWindowTitle')
        self.library = library or PetAssetLibrary()
        catalog, errors = self.library.scan()
        self.draft = WardrobeDraft(profiles, identifier, catalog)
        self.playback = LayeredPlayback()
        self._install_job = None
        self._closed = False
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(profiles.get(identifier)['name']))
        self.preview = QLabel()
        self.preview.setFixedSize(288, 288)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # A pinned look renders beside the draft on the same clock for comparison.
        self.compare_preview = QLabel()
        self.compare_preview.setFixedSize(288, 288)
        self.compare_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.compare_preview.hide()
        self._compare = None
        self._show_until = 0
        columns = QHBoxLayout()
        layout.addLayout(columns)
        previews = QVBoxLayout()
        previews.addWidget(self.preview)
        previews.addWidget(self.compare_preview)
        self.compare_button = tr(QPushButton(), 'pet_wardrobe_compare', 'Pin for comparison')
        self.compare_button.setCheckable(True)
        self.compare_button.toggled.connect(self._pin_comparison)
        previews.addWidget(self.compare_button)
        previews.addStretch()
        columns.addLayout(previews)
        form = QFormLayout()
        columns.addLayout(form)
        self.character = QComboBox()
        self.character.setMinimumWidth(180)
        form.addRow(tr(QLabel(), 'pet_wardrobe_character', 'Character'), self.character)
        self.slots = {}
        for slot in SLOTS:
            control = QComboBox()
            self.slots[slot] = control
            form.addRow(tr(QLabel(), 'pet_wardrobe_' + slot, slot.title()), control)
            control.activated.connect(lambda _index, name=slot: self._choose_slot(name))
        self.action = QComboBox()
        self.mirror = tr(QCheckBox(), 'pet_wardrobe_mirror', 'Face left')
        form.addRow(tr(QLabel(), 'pet_wardrobe_preview', 'Preview action'), self.action)
        form.addRow(self.mirror)
        self.color_region = QComboBox()
        form.addRow(tr(QLabel(), 'pet_wardrobe_region', 'Color region'), self.color_region)
        self.color_button = tr(QPushButton(), 'pet_wardrobe_color', 'Choose color')
        self.color_reset = tr(QPushButton(), 'pet_wardrobe_color_reset', 'Restore region color')
        self.color_button.clicked.connect(self._choose_color)
        self.color_reset.clicked.connect(self._reset_color)
        form.addRow(self.color_button, self.color_reset)
        swatch_row = QHBoxLayout()
        self.swatches = {}
        for value in ('#171613', '#ff7417', '#fff1cf', '#c8f141', '#24b8b0', '#f45588'):
            button = QPushButton()
            button.setFixedSize(28, 28)
            button.setAccessibleName(value)
            button.setToolTip(value)
            button.setStyleSheet(
                f'QPushButton {{ background: {value}; border: 2px solid #777; border-radius: 4px; }}'
                'QPushButton:focus { border: 3px solid #2487ff; }'
                'QPushButton:disabled { background: #777; border: 2px solid #555; }')
            button.clicked.connect(lambda _checked=False, color=value: self._choose_swatch(color))
            self.swatches[value] = button
            swatch_row.addWidget(button)
        swatch_row.addStretch()
        form.addRow(tr(QLabel(), 'pet_wardrobe_swatches', 'Style colors'), swatch_row)
        self.variant_group = QComboBox()
        self.variant_choice = QComboBox()
        form.addRow(tr(QLabel(), 'pet_wardrobe_part', 'Character part'), self.variant_group)
        form.addRow(tr(QLabel(), 'pet_wardrobe_part_choice', 'Part style'), self.variant_choice)
        self.variant_group.currentIndexChanged.connect(self._refresh_variant_choices)
        self.variant_choice.activated.connect(self._choose_variant)
        self.outfits = QComboBox()
        self.outfit_name = QLineEdit()
        form.addRow(tr(QLabel(), 'pet_wardrobe_outfits', 'Saved outfits'), self.outfits)
        form.addRow(tr(QLabel(), 'pet_wardrobe_name', 'Outfit name'), self.outfit_name)
        self._buttons(layout, (
            ('pet_wardrobe_save', 'Save new outfit', self._save_outfit),
            ('pet_wardrobe_update', 'Update selected', self._update_outfit),
            ('pet_wardrobe_wear', 'Wear selected', self._wear_outfit),
            ('pet_wardrobe_delete', 'Delete selected', self._delete_outfit),
        ))
        self.status = QLabel('\n'.join(errors))
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.install_button = tr(QPushButton(), 'pet_wardrobe_install', 'Install asset folder')
        self.install_button.clicked.connect(self._install)
        layout.addWidget(self.install_button)
        builtin_row = QHBoxLayout()
        self.builtin = QComboBox()
        tr(self.builtin, 'pet_wardrobe_builtin_pick', 'Built-in character', 'setAccessibleName')
        for identifier, name in builtin_names():
            self.builtin.addItem(name, identifier)
        self.builtin_button = tr(QPushButton(), 'pet_wardrobe_builtin', 'Add built-in character')
        self.builtin_button.clicked.connect(self._install_builtin)
        builtin_row.addWidget(self.builtin)
        builtin_row.addWidget(self.builtin_button)
        layout.addLayout(builtin_row)
        self._buttons(layout, (('pet_wardrobe_refresh', 'Refresh assets', self.refresh_library),))
        self._buttons(layout, (
            ('pet_custom_apply', 'Apply', self.apply_changes),
            ('pet_custom_cancel', 'Cancel', self.reject),
        ))
        self.character.activated.connect(self._choose_character)
        self.action.currentTextChanged.connect(self.playback.set_action)
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._render)
        self._refresh_controls()
        self._attempt(self.draft.prepare_preview)
        retranslator.bind_call(self._retranslate_choices)
        if errors:
            self.status.setText('\n'.join((*errors, self.status.text())))

    def _buttons(self, layout, entries) -> None:
        row = QHBoxLayout()
        for key, fallback, callback in entries:
            button = tr(QPushButton(), key, fallback)
            button.clicked.connect(callback)
            row.addWidget(button)
        layout.addLayout(row)

    def refresh_library(self) -> None:
        try:
            catalog, errors = self.library.scan()
        except (OSError, ValueError) as error:
            self.status.setText(str(error))
            return
        self.draft.catalog = catalog
        self._attempt(self.draft.prepare_preview)
        if errors:
            self.status.setText('\n'.join((*errors, self.status.text())))

    def _install(self) -> None:
        source = QFileDialog.getExistingDirectory(self, translate('pet_wardrobe_install', 'Install asset folder'))
        if not source or self._install_job is not None:
            return
        self.install_button.setEnabled(False)
        job = PetAssetInstall(self.library, source)
        self._install_job = job
        job.signals.finished.connect(self._installed, Qt.ConnectionType.QueuedConnection)
        QThreadPool.globalInstance().start(job)

    def _install_builtin(self) -> None:
        if self._install_job is not None:
            return
        self.install_button.setEnabled(False)
        self.builtin_button.setEnabled(False)
        self.status.setText(translate('pet_wardrobe_builtin_busy', 'Drawing the character and its wardrobe…'))
        job = PetBuiltinInstall(self.library, self.builtin.currentData())
        self._install_job = job
        job.signals.finished.connect(self._builtin_installed, Qt.ConnectionType.QueuedConnection)
        QThreadPool.globalInstance().start(job)

    @Slot(str)
    def _builtin_installed(self, error: str) -> None:
        self._installed(error)
        if not error and not self._closed:
            self.status.setText(translate('pet_wardrobe_builtin_done',
                                          'Built-in character ready. Choose it under Character.'))

    @Slot(str)
    def _installed(self, error: str) -> None:
        self._install_job = None
        if self._closed:
            return
        self.install_button.setEnabled(True)
        self.builtin_button.setEnabled(True)
        self.refresh_library()
        if error:
            self.status.setText(error)

    def _attempt(self, operation) -> bool:
        try:
            operation()
        except WardrobeError as error:
            self.status.setText(error.localized(translate))
            self._refresh_controls()
            return False
        except (OSError, ValueError, KeyError) as error:
            self.status.setText(str(error))
            self._refresh_controls()
            return False
        self.status.clear()
        self.playback.set_renderer(self.draft.preview)
        self._refresh_controls()
        self._render()
        return True

    def _retranslate_choices(self) -> None:
        appearance = self.draft.appearance
        self._fill(self.character, self.draft.catalog.assets('character'), appearance['character'])
        character = self.draft.preview.character if self.draft.preview else None
        for slot, control in self.slots.items():
            fits = [(asset, garment_fit(character, asset)) for asset in self.draft.catalog.assets('garment')
                    if slot in asset.slots]
            # Garments for other body types are not offered; same-body garments that
            # lack animations stay visible but disabled, with the reason.
            self._fill(control, tuple(asset for asset, fit in fits if fit is None),
                       appearance['equipped'][slot])
            for asset, fit in fits:
                if fit == 'missing_actions':
                    control.addItem(asset_label(asset) + ' · ' + translate('pet_wardrobe_incompatible',
                                                                     'missing animations'), asset_reference(asset))
                    control.model().item(control.count() - 1).setEnabled(False)
            control.setEnabled(character is not None)
        if self.variant_choice.count():
            self.variant_choice.setItemText(0, translate('pet_custom_reset', 'Reset defaults'))
        self._relabel_parts(character)
        if character is None and not self.status.text():
            self.status.setText(translate('pet_wardrobe_legacy', 'This pet shows a whole-image sprite. Choose '
                                          'a layered character to dress it piece by piece.'))

    def _relabel_parts(self, character) -> None:
        """Rename part entries in place so a language switch keeps every selection."""
        if character is None:
            return
        for index in range(self.variant_group.count()):
            group = self.variant_group.itemData(index)
            self.variant_group.setItemText(index, label(character.identifier, character.variants[group]['name']))
        group = self.variant_group.currentData()
        for index in range(1, self.variant_choice.count()):
            name = character.variants[group]['choices'][self.variant_choice.itemData(index)]
            self.variant_choice.setItemText(index, label(character.identifier, name))

    def _refresh_controls(self) -> None:
        self._retranslate_choices()
        appearance = self.draft.appearance
        selected = self.outfits.currentData()
        self.outfits.clear()
        for outfit in appearance['saved_outfits']:
            self.outfits.addItem(outfit['name'], outfit['id'])
        self.outfits.setCurrentIndex(max(0, self.outfits.findData(selected)))
        action = self.action.currentText()
        self.action.clear()
        if self.draft.preview:
            self.action.addItems(list(self.draft.preview.character.actions))
            index = self.action.findText(action)
            if index >= 0:
                self.action.setCurrentIndex(index)
        selected_region = self.color_region.currentData()
        self.color_region.clear()
        if self.draft.preview:
            for asset in (self.draft.preview.character, *self.draft.preview.garments):
                for region in asset.palette:
                    self.color_region.addItem(asset_label(asset) + ' / ' + region, (asset_reference(asset), region))
        self.color_region.setCurrentIndex(max(0, self.color_region.findData(selected_region)))
        for control in (self.color_button, self.color_reset, self.color_region, *self.swatches.values()):
            control.setEnabled(self.color_region.count() > 0)
        selected_group = self.variant_group.currentData()
        self.variant_group.blockSignals(True)
        self.variant_group.clear()
        if self.draft.preview:
            character = self.draft.preview.character
            for group, spec in character.variants.items():
                self.variant_group.addItem(label(character.identifier, spec['name']), group)
        self.variant_group.setCurrentIndex(max(0, self.variant_group.findData(selected_group)))
        self.variant_group.blockSignals(False)
        self.variant_group.setEnabled(self.variant_group.count() > 0)
        self._refresh_variant_choices()

    def _refresh_variant_choices(self) -> None:
        self.variant_choice.clear()
        group = self.variant_group.currentData()
        if group is not None and self.draft.preview:
            spec = self.draft.preview.character.variants[group]
            self.variant_choice.addItem(translate('pet_custom_reset', 'Reset defaults'), None)
            for choice, name in spec['choices'].items():
                self.variant_choice.addItem(label(self.draft.preview.character.identifier, name), choice)
            selected = self.draft.appearance.get('variants', {}).get(group)
            self.variant_choice.setCurrentIndex(max(0, self.variant_choice.findData(selected)))
        self.variant_choice.setEnabled(self.variant_choice.count() > 0)

    def _choose_variant(self, _index=0) -> None:
        group, choice = self.variant_group.currentData(), self.variant_choice.currentData()
        if group is not None:
            self._attempt(lambda: self.draft.set_variant(group, choice))

    def _choose_color(self) -> None:
        selected = self.color_region.currentData()
        if selected is None:
            return
        reference, region = selected
        key = reference['id'] + '@' + reference['version']
        asset = next(asset for asset in (self.draft.preview.character, *self.draft.preview.garments)
                     if asset_reference(asset) == reference)
        value = self.draft.appearance.get('colors', {}).get(key, {}).get(region, asset.palette[region])
        color = QColorDialog.getColor(QColor(value), self, translate('pet_wardrobe_color', 'Choose color'))
        if color.isValid():
            self._attempt(lambda: self.draft.set_color(reference, region, color.name()))

    def _reset_color(self) -> None:
        selected = self.color_region.currentData()
        if selected is not None:
            self._attempt(lambda: self.draft.set_color(*selected, None))

    def _choose_swatch(self, color: str) -> None:
        selected = self.color_region.currentData()
        if selected is not None:
            self._attempt(lambda: self.draft.set_color(*selected, color))

    @staticmethod
    def _fill(control, assets, selected) -> None:
        control.clear()
        control.addItem(translate('pet_wardrobe_none', 'None'), None)
        for asset in assets:
            control.addItem(asset_label(asset) + ' · ' + asset.version, asset_reference(asset))
        index = control.findData(selected)
        if index < 0 and selected is not None:
            control.addItem(translate('pet_wardrobe_missing', 'Missing') + ': ' + selected['id'], selected)
            index = control.count() - 1
        control.setCurrentIndex(max(0, index))

    def _choose_character(self, _index=0) -> None:
        reference = self.character.currentData()
        self._attempt(lambda: self.draft.choose_character(reference))

    def _choose_slot(self, slot: str) -> None:
        reference = self.slots[slot].currentData()
        if reference is None:
            self._attempt(lambda: self.draft.unequip(slot))
            return
        if self._attempt(lambda: self.draft.equip(reference)):
            self._try_on()
            if self.draft.replaced:
                self.status.setText(translate('pet_wardrobe_replaced', 'Replaced: {items}').format(
                    items=', '.join(self.draft.replaced)))

    def _try_on(self) -> None:
        """Trying a garment on plays the outfit-show pose once in the preview."""
        if self.draft.preview is not None and 'outfit_show' in self.draft.preview.character.actions:
            self.playback.set_action('outfit_show')
            QTimer.singleShot(900, self, lambda: self.playback.set_action(self.action.currentText() or 'idle'))

    def _pin_comparison(self, pinned: bool) -> None:
        self._compare = self.draft.preview if pinned else None
        self.compare_preview.setVisible(self._compare is not None)
        if self._compare is None:
            self.compare_preview.clear()
        self._render()

    def _save_outfit(self) -> None:
        self._attempt(lambda: self.draft.save_outfit(self.outfit_name.text()))

    def _wear_outfit(self) -> None:
        self._attempt(lambda: self.draft.wear_outfit(self.outfits.currentData()))

    def _update_outfit(self) -> None:
        identifier = self.outfits.currentData()
        if identifier is not None:
            self._attempt(lambda: self.draft.save_outfit(self.outfit_name.text(), identifier))

    def _delete_outfit(self) -> None:
        self._attempt(lambda: self.draft.delete_outfit(self.outfits.currentData()))

    def apply_changes(self) -> bool:
        if not self._attempt(self.draft.apply):
            return False
        self.status.setText(translate('pet_wardrobe_saved', 'Appearance saved'))
        return True

    def _render(self) -> None:
        image = self.playback.frame()
        if image is None:
            self.preview.clear()
        else:
            self._show(self.preview, image)
        if self._compare is not None:
            elapsed = self.playback.elapsed_ms()
            self._show(self.compare_preview, self._compare.render(self.playback.action, elapsed))

    def _show(self, label, image) -> None:
        if self.mirror.isChecked():
            from PySide6.QtGui import QTransform
            image = image.transformed(QTransform().scale(-1, 1))
        label.setPixmap(QPixmap.fromImage(image).scaled(
            label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.playback.resume()
        self.timer.start()

    def hideEvent(self, event) -> None:
        self.timer.stop()
        self.playback.pause()
        super().hideEvent(event)

    def done(self, result: int) -> None:
        self._closed = True
        if self._install_job is not None:
            self._install_job.cancel.set()
        self.timer.stop()
        self.draft.cancel()
        self._compare = None
        self.playback.set_renderer(None)
        super().done(result)
