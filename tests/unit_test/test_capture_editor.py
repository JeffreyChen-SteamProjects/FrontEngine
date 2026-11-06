"""Flattened redaction pixels, crop coordinates and injected clipboard outputs."""
import math

import pytest
from PySide6.QtCore import QRect, Qt, QEvent, QCoreApplication
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from frontengine.utils.capture_editor.document import CaptureDocument
from frontengine.ui.dialog.capture_editor import CaptureEditor


def image():
    result = QImage(200, 120, QImage.Format.Format_ARGB32)
    result.fill(QColor('yellow'))
    result.setDevicePixelRatio(2)
    return result


def test_crop_after_redaction_and_flattened_file_contains_no_source(tmp_path):
    document = CaptureDocument(image())
    document.add('redact', (20, 20), (50, 50))
    document.add('text', (20, 20), (70, 60), 'secret')
    document.set_crop((10, 10), (100, 80))
    result = document.render()
    assert result.size().width() == 90 and result.height() == 70
    assert result.devicePixelRatio() == 1
    assert result.pixelColor(12, 12) == QColor('black')
    assert result.pixelColor(80, 60) == QColor('yellow')
    assert document.original.pixelColor(25, 25) == QColor('yellow')
    path = tmp_path / 'edited.png'
    assert document.save(str(path))
    decoded = QImage(str(path))
    assert decoded == result and decoded.textKeys() == []
    assert not document.save(str(tmp_path / 'absent' / 'x.png'))


def test_arrow_number_text_and_undo_keep_original_coordinates():
    document = CaptureDocument(image())
    document.set_crop((10, 10), (190, 110))
    document.add('arrow', (20, 20), (100, 20))
    document.add('number', (120, 60), (120, 60))
    document.add('text', (50, 60), (100, 100), 'A')
    result = document.render()
    assert result.pixelColor(30, 10).red() > 200 and result.pixelColor(30, 10).green() < 100
    assert document.marks[1]['text'] == '1'
    assert result != document.original.copy(document.crop)
    for _index in range(3):
        assert document.undo()
    assert document.crop == QRect(10, 10, 180, 100) and document.marks == []
    document.reset()
    assert document.crop == document.original.rect()
    assert document.undo() and document.crop == QRect(10, 10, 180, 100)


@pytest.mark.parametrize('points', [((math.nan, 0), (20, 30)), ((0, math.inf), (10, 10)), ((1,), (2, 3))])
def test_invalid_marks_do_not_change_document(points):
    document = CaptureDocument(image())
    with pytest.raises(ValueError):
        document.add('arrow', *points)
    assert not document.marks and not document.history


def test_bounds_and_undo_capacity():
    with pytest.raises(ValueError):
        CaptureDocument(QImage())
    document = CaptureDocument(image())
    with pytest.raises(ValueError):
        document.set_crop((1, 1), (1, 1))
    with pytest.raises(ValueError):
        document.add('text', (1, 1), (50, 50), 'x' * 2001)
    for index in range(25):
        document.add('number', (index, index), (index, index))
    assert len(document.history) == 20
    document.marks = [document.marks[0]] * 1000
    with pytest.raises(ValueError):
        document.add('arrow', (1, 1), (20, 20))


def test_scaled_view_gestures_map_to_crop_and_copy_pin_share_result():
    dialog = CaptureEditor(image())
    selected = []
    dialog.pin_requested.connect(selected.append)
    clipboard = type('Clipboard', (), {'setImage': lambda self, result: setattr(self, 'image', result)})()
    try:
        dialog.show()
        QApplication.processEvents()
        dialog.document.set_crop((10, 10), (190, 110))
        dialog.canvas.refresh()
        dialog.canvas.mode = 'redact'
        start = dialog.canvas.mapFromScene(10, 10)
        end = dialog.canvas.mapFromScene(40, 40)
        QTest.mousePress(dialog.canvas.viewport(), Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(dialog.canvas.viewport(), end)
        QTest.mouseRelease(dialog.canvas.viewport(), Qt.MouseButton.LeftButton, pos=end)
        assert dialog.document.marks[0]['start'] == pytest.approx((20, 20), abs=1)
        assert dialog.document.render().pixelColor(20, 20) == QColor('black')
        dialog.original_button.setChecked(True)
        assert not dialog.tools.isEnabled() and dialog.canvas.original_view
        dialog.copy_result(clipboard=clipboard)
        dialog.pin_result()
        assert selected == [clipboard.image] and selected[0] == dialog.document.render()
        assert dialog.document.original.pixelColor(20, 20) == QColor('yellow')
    finally:
        dialog.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_editor_replacement_old_destroyed_signal_does_not_clear_new(tmp_path, monkeypatch, *, lifetime_factory):
    from frontengine.ui.page.tools.tools_setting_ui import ToolsSettingUI
    monkeypatch.chdir(tmp_path)
    lifetime_factory()
    page = ToolsSettingUI(lifetime=lifetime_factory())
    try:
        page.last_capture = QPixmap.fromImage(image())
        page.edit_last_capture()
        page.edit_last_capture()
        replacement = page.capture_editor
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        assert page.capture_editor is replacement
        assert page.last_capture.toImage().pixelColor(20, 20) == QColor('yellow')
        page.close_capture_editor()
        assert page.capture_editor is None
    finally:
        page.close_capture_editor()
        page.close()
        page.deleteLater()
        QCoreApplication.sendPostedEvents(page, QEvent.Type.DeferredDelete)


@pytest.mark.parametrize('closing', ['reject', 'close', 'destroy', 'reject_pending_delete'])
@pytest.mark.parametrize('existing', [False, True])
def test_closed_capture_editor_does_not_write_picker_destination(tmp_path, monkeypatch, closing, existing):
    from PySide6.QtWidgets import QFileDialog
    from shiboken6 import isValid

    dialog = CaptureEditor(image())
    destination = tmp_path / 'capture.png'
    if existing:
        destination.write_bytes(b'original file contents')
    def choose_then_close(*_args):
        if closing in ('reject', 'reject_pending_delete'):
            dialog.reject()
        elif closing == 'close':
            dialog.close()
        else:
            dialog.deleteLater()
        if closing != 'reject_pending_delete':
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        return str(destination), ''
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', choose_then_close)
    try:
        dialog.save_result()
        assert destination.read_bytes() == b'original file contents' if existing else not destination.exists()
        def unexpected_picker(*_args):
            pytest.fail('closed capture editor reopened its save picker')
        monkeypatch.setattr(QFileDialog, 'getSaveFileName', unexpected_picker)
        dialog.save_result()
    finally:
        if isValid(dialog):
            dialog.close()


def test_capture_save_picker_cancel_then_retry_preserves_edits(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    dialog = CaptureEditor(image())
    dialog.document.add('redact', (20, 20), (50, 50))
    expected = dialog.document.render()
    destination = tmp_path / 'capture.png'
    choices = iter([('', ''), (str(destination), '')])
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *_args: next(choices))
    try:
        dialog.save_result()
        assert not destination.exists()
        assert dialog.document.render() == expected
        dialog.save_result()
        assert QImage(str(destination)) == expected
        assert QImage(str(destination)).pixelColor(25, 25) == QColor('black')
    finally:
        dialog.close()


@pytest.mark.parametrize('closing', ['reject', 'close', 'destroy', 'reject_pending_delete'])
@pytest.mark.parametrize('accepted', [False, True])
def test_text_prompt_discards_result_after_capture_closes(monkeypatch, closing, accepted):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QInputDialog
    from shiboken6 import isValid

    dialog = CaptureEditor(image())
    document = dialog.document
    changed = []
    canvas = dialog.canvas
    canvas.changed.connect(lambda: changed.append(True))
    dialog.show()
    QApplication.processEvents()
    canvas.mode = 'text'
    start = canvas.mapFromScene(10, 10)
    end = canvas.mapFromScene(40, 40)
    QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=start)
    def prompt_then_close(*_args):
        if closing in ('reject', 'reject_pending_delete'):
            dialog.reject()
        elif closing == 'close':
            dialog.close()
        else:
            dialog.deleteLater()
        if closing != 'reject_pending_delete':
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        return 'discard this text', accepted
    monkeypatch.setattr(QInputDialog, 'getMultiLineText', prompt_then_close)
    event = QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(end), QPointF(end),
                        Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    try:
        canvas.mouseReleaseEvent(event)
        assert document.marks == [] and document.history == []
        assert changed == []
    finally:
        if isValid(dialog):
            dialog.close()


def test_capture_text_cancel_then_retry(monkeypatch):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QInputDialog

    dialog = CaptureEditor(image())
    choices = iter([('discard', False), ('keep', True)])
    monkeypatch.setattr(QInputDialog, 'getMultiLineText', lambda *_args: next(choices))
    try:
        dialog.show()
        QApplication.processEvents()
        canvas = dialog.canvas
        canvas.mode = 'text'
        for attempt in range(2):
            start = canvas.mapFromScene(10, 10)
            end = canvas.mapFromScene(40, 40)
            QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=start)
            event = QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(end), QPointF(end),
                                Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
            canvas.mouseReleaseEvent(event)
            if attempt == 0:
                assert dialog.document.marks == [] and dialog.document.history == []
                assert canvas.origin is None and canvas.rubber is None
        assert len(dialog.document.marks) == 1
        assert dialog.document.marks[0]['text'] == 'keep'
        assert dialog.document.render() != dialog.document.original
    finally:
        dialog.close()
