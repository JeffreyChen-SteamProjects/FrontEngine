import pytest
from accessibility_assertions import assert_named_by

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
        label = getattr(dialog, label_name)
        assert label.text() == expected
        assert_named_by(control, label)
        label.setText('Updated ' + expected)
        assert_named_by(control, label)
        assert dialog.collect() == before
    finally:
        dialog.reject()
