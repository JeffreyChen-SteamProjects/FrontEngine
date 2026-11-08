"""The macOS branch of the accessible-name check runs here too, so it cannot rot unnoticed."""
from PySide6.QtWidgets import QComboBox, QFormLayout, QWidget

import accessibility_assertions
from accessibility_assertions import assert_named_by


def test_macos_combo_boxes_are_checked_through_their_label_relation(monkeypatch):
    holder = QWidget()
    form = QFormLayout(holder)
    combo = QComboBox()
    combo.addItems(['One', 'Two'])
    form.addRow('Character', combo)
    label = form.labelForField(combo)
    monkeypatch.setattr(accessibility_assertions.sys, 'platform', 'darwin')
    assert_named_by(combo, label)
    other = QComboBox()
    form.addRow('Other', other)
    try:
        assert_named_by(other, label)
    except AssertionError:
        pass
    else:
        raise AssertionError('a combo box labelled by something else passed')
    holder.close()
