"""Frozen pet-only photographs; no desktop capture or live-state mutation."""
from pathlib import Path

from PySide6.QtCore import QIODevice, QSaveFile, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout,
)

from frontengine.utils.multi_language.retranslate import tr, translate


def save_photo(image: QImage, destination: str | Path) -> None:
    if image.isNull():
        raise ValueError('No pet image to save')
    file = QSaveFile(str(destination))
    if not file.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError(file.errorString())
    if not image.save(file, 'PNG'):
        file.cancelWriting()
        raise OSError('Could not encode pet PNG')
    if not file.commit():
        raise OSError(file.errorString())


class PetPhotoDialog(QDialog):
    def __init__(self, snapshot: QImage, renderer=None, *, mirrored=False, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        tr(self, 'pet_photo_title', 'Pet photo', 'setWindowTitle')
        self.snapshot = snapshot.copy()
        self.renderer, self.mirrored = renderer, mirrored
        self.image = self.snapshot.copy()
        layout = QVBoxLayout(self)
        hint = tr(QLabel(), 'pet_photo_hint', 'Only the pet is saved, with a transparent background.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.preview = QLabel()
        self.preview.setFixedSize(320, 320)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview)
        form = QFormLayout()
        layout.addLayout(form)
        self.pose = QComboBox()
        self.pose.addItem(translate('pet_photo_current', 'Captured pose'), None)
        if renderer:
            for action in renderer.character.actions:
                self.pose.addItem(action, action)
        form.addRow(tr(QLabel(), 'pet_photo_pose', 'Pose'), self.pose)
        self.time = QSpinBox()
        self.time.setSuffix(' ms')
        form.addRow(tr(QLabel(), 'pet_photo_time', 'Pose time'), self.time)
        self.pose.currentIndexChanged.connect(self._pose_changed)
        self.time.valueChanged.connect(self._render)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.save_button = tr(QPushButton(), 'pet_photo_save', 'Save transparent PNG')
        self.save_button.clicked.connect(self.choose_destination)
        layout.addWidget(self.save_button)
        self._pose_changed()

    def _pose_changed(self):
        action = self.pose.currentData()
        self.time.blockSignals(True)
        total = sum(frame.duration_ms for frame in self.renderer.character.actions[action].frames) if action else 1
        self.time.setRange(0, total - 1)
        self.time.setValue(0)
        self.time.setEnabled(action is not None)
        self.time.blockSignals(False)
        self._render()

    def _render(self):
        action = self.pose.currentData()
        self.image = (self.renderer.render(action, self.time.value(), mirrored=self.mirrored)
                      if action else self.snapshot.copy())
        self.preview.setPixmap(QPixmap.fromImage(self.image).scaled(
            self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        self.save_button.setEnabled(not self.image.isNull())

    def save_to(self, destination) -> bool:
        try:
            save_photo(self.image, destination)
        except (OSError, ValueError):
            self.status.setText(translate('pet_photo_failed', 'Could not save. Choose another location and retry.'))
            return False
        self.status.setText(translate('pet_photo_saved', 'Photo saved'))
        return True

    def choose_destination(self):
        destination, _ = QFileDialog.getSaveFileName(
            self, translate('pet_photo_save', 'Save transparent PNG'), 'pet.png', 'PNG (*.png)')
        if destination:
            self.save_to(destination)
