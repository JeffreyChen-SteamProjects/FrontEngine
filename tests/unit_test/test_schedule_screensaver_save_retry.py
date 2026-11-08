"""Schedule and screensaver dialogs keep the old settings when saving fails, and
the screensaver source labels follow a live language change."""
import json

import pytest
from PySide6.QtWidgets import QDialog

from frontengine.ui.menu.language_menu import LANGUAGES
from frontengine.utils.multi_language.retranslate import translate


class FakePresets:
    def list_presets(self):
        return ['Morning', 'Evening']


def _screensaver(module):
    dialog = module.ScreensaverDialog()
    original = {'enabled': False, 'idle_minutes': 9, 'source': 'image'}
    dialog.enable_checkbox.setChecked(True)
    dialog.idle_spinbox.setValue(17)
    dialog.source_combobox.setCurrentIndex(dialog.source_combobox.findData('web'))
    return dialog, original


def _schedule(module):
    dialog = module.PresetScheduleDialog(repository=FakePresets())
    original = {'enabled': False, 'preset': 'Morning', 'hour': 7, 'minute': 5, 'days': [0]}
    dialog.enable_checkbox.setChecked(True)
    dialog.preset_combobox.setCurrentIndex(dialog.preset_combobox.findData('Evening'))
    dialog.hour_spinbox.setValue(21)
    dialog.minute_spinbox.setValue(45)
    dialog.day_checkboxes[4].setChecked(True)
    return dialog, original


def _modules():
    from frontengine.ui.dialog import preset_schedule_dialog, screensaver_dialog
    return {'screensaver': (screensaver_dialog, _screensaver),
            'schedule': (preset_schedule_dialog, _schedule)}


@pytest.mark.parametrize('kind', ['screensaver', 'schedule'])
@pytest.mark.parametrize('stored', ['missing', 'null', 'settings'])
@pytest.mark.parametrize('failure', [OSError, ValueError])
def test_save_failure_keeps_previous_settings_and_allows_retry(
        tmp_path, monkeypatch, kind, stored, failure):
    module, build = _modules()[kind]
    state = {'unrelated': 'keep'}
    monkeypatch.setattr(module, 'user_setting_dict', state)
    dialog, original = build(module)
    if stored != 'missing':
        state[module.SETTING_KEY] = original if stored == 'settings' else None
    before = dict(state)
    destination = tmp_path / 'settings.json'
    destination.write_text(json.dumps(state), encoding='utf-8')
    before_bytes = destination.read_bytes()
    attempts = []

    def write():
        attempts.append(True)
        if len(attempts) == 1:
            raise failure('Cannot save settings')
        destination.write_text(json.dumps(state), encoding='utf-8')

    monkeypatch.setattr(module, 'write_user_setting', write)
    dialog.show()
    desired = dialog.collect()
    try:
        dialog.accept()
        assert state == before
        if stored == 'settings':
            assert state[module.SETTING_KEY] is original
        assert destination.read_bytes() == before_bytes
        assert dialog.isVisible() and dialog.result() != QDialog.DialogCode.Accepted
        assert 'Cannot save settings' in dialog.status.text()
        assert dialog.collect() == desired
        dialog.accept()
        assert dialog.result() == QDialog.DialogCode.Accepted
        assert not dialog.isVisible()
        assert state[module.SETTING_KEY] == desired
        assert json.loads(destination.read_text(encoding='utf-8')) == state
        assert state['unrelated'] == 'keep' and len(attempts) == 2
        assert dialog.status.text() == ''
    finally:
        dialog.close()


def test_screensaver_source_labels_follow_language_without_changing_selection(make_main_window):
    from frontengine.ui.dialog.screensaver_dialog import SOURCE_LABEL_KEYS, ScreensaverDialog
    window = make_main_window()
    dialog = ScreensaverDialog(window)
    combo = dialog.source_combobox
    combo.setCurrentIndex(combo.count() - 1)
    selected = combo.currentData()
    values = [combo.itemData(i) for i in range(combo.count())]
    changes = []
    combo.currentIndexChanged.connect(changes.append)
    try:
        for index in [*range(len(LANGUAGES)), 0]:
            window.language_menu.actions()[index].trigger()
            assert [combo.itemText(i) for i in range(combo.count())] == [
                translate(*SOURCE_LABEL_KEYS[value]) for value in values]
            assert combo.currentData() == selected
            assert [combo.itemData(i) for i in range(combo.count())] == values
            assert not changes
            assert dialog.collect()['source'] == selected
    finally:
        window.language_menu.actions()[0].trigger()
        dialog.close()
        dialog.deleteLater()


@pytest.mark.parametrize('action, dialog_type', [
    ('screensaver_action', 'ScreensaverDialog'),
    ('preset_schedule_action', 'PresetScheduleDialog'),
])
def test_menu_releases_each_settings_dialog_after_it_closes(
        make_main_window, monkeypatch, action, dialog_type):
    from PySide6.QtCore import QCoreApplication, QEvent
    from shiboken6 import isValid
    window = make_main_window()
    opened = []
    monkeypatch.setattr(QDialog, 'exec', lambda self: opened.append(self) or 0)
    for _ in range(3):
        getattr(window, action).trigger()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert [type(dialog).__name__ for dialog in opened] == [dialog_type] * 3
    assert not any(isValid(dialog) for dialog in opened)
    assert not [child for child in window.findChildren(QDialog)
                if type(child).__name__ == dialog_type]
