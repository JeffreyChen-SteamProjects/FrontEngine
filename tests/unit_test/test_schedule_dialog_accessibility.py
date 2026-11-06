import pytest
from PySide6.QtGui import QAccessible

from frontengine.ui.dialog.preset_schedule_dialog import PresetScheduleDialog
from frontengine.ui.dialog.screensaver_dialog import ScreensaverDialog


class Presets:
    def list_presets(self):
        return ['Work', 'Evening']


@pytest.mark.parametrize('kind,field,label_name,expected', [
    ('schedule', 'preset_combobox', 'preset_label', 'Preset'),
    ('schedule', 'hour_spinbox', 'hour_label', 'Hour'),
    ('schedule', 'minute_spinbox', 'minute_label', 'Minute'),
    ('screensaver', 'idle_spinbox', 'idle_label', 'Idle for (minutes)'),
    ('screensaver', 'source_combobox', 'source_label', 'Show'),
])
def test_schedule_field_names_follow_labels_without_changing_values(kind, field, label_name, expected):
    dialog = PresetScheduleDialog(repository=Presets()) if kind == 'schedule' else ScreensaverDialog()
    try:
        before = dialog.collect()
        control = getattr(dialog, field)
        accessible = QAccessible.queryAccessibleInterface(control)
        assert accessible.text(QAccessible.Text.Name) == expected
        label = getattr(dialog, label_name)
        assert label.text() == expected
        label.setText('Updated ' + expected)
        assert accessible.text(QAccessible.Text.Name) == label.text()
        assert dialog.collect() == before
    finally:
        dialog.reject()
