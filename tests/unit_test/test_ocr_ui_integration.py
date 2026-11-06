from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QColor, QPixmap
import pytest

from frontengine.ui.page.tools import tools_setting_ui as tools
from frontengine.utils.screen_text.screen_text_service import ScreenTextResult


@pytest.mark.parametrize('kind', ['text', 'capture'])
@pytest.mark.parametrize('destroy', [False, True])
def test_ocr_consent_return_after_page_closure_does_not_present_or_retry(monkeypatch, lifetime_factory, kind, destroy):
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QMessageBox
    from shiboken6 import isValid
    from frontengine.ui.dialog import screen_text_dialog

    page = tools.ToolsSettingUI(lifetime=lifetime_factory())
    page.show()
    page.last_screen_text = 'Previous result'
    key = screen_text_dialog.TEXT_CONSENT_KEY if kind == 'text' else screen_text_dialog.CONSENT_KEY
    monkeypatch.setitem(screen_text_dialog.user_setting_dict, key, False)
    monkeypatch.setattr(tools, 'api_key', lambda: 'test-placeholder')
    writes, presented, requests = [], [], []
    monkeypatch.setattr(screen_text_dialog, 'write_user_setting', lambda: writes.append(True))
    monkeypatch.setattr(page, '_present_screen_text_result', presented.append)
    monkeypatch.setattr(page, '_request_screen_text', lambda *_args: requests.append(True))
    def answer(*_args):
        page.close()
        if destroy:
            page.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        return QMessageBox.StandardButton.Yes
    monkeypatch.setattr(QMessageBox, 'question', answer)
    try:
        result = ScreenTextResult('consent_required', 'Recognized locally', 'local', consent_required=kind)
        page._handle_screen_text_result(result, b'test image', 'translate', 'English', '')
        assert presented == [] and requests == [] and writes == []
        assert page.last_screen_text == 'Previous result'
    finally:
        if isValid(page):
            page.close()


@pytest.mark.parametrize('kind', ['text', 'capture'])
@pytest.mark.parametrize('granted', [False, True])
def test_live_ocr_consent_result_presents_or_retries_once(monkeypatch, lifetime_factory, kind, granted):
    from PySide6.QtWidgets import QMessageBox
    from frontengine.ui.dialog import screen_text_dialog

    page = tools.ToolsSettingUI(lifetime=lifetime_factory())
    page.show()
    page.last_screen_text = 'Previous result'
    key = screen_text_dialog.TEXT_CONSENT_KEY if kind == 'text' else screen_text_dialog.CONSENT_KEY
    monkeypatch.setitem(screen_text_dialog.user_setting_dict, key, False)
    monkeypatch.setattr(tools, 'api_key', lambda: 'test-placeholder')
    monkeypatch.setattr(screen_text_dialog, 'write_user_setting', lambda: None)
    monkeypatch.setattr(QMessageBox, 'question', lambda *_args:
                        QMessageBox.StandardButton.Yes if granted else QMessageBox.StandardButton.No)
    presented, requests = [], []
    monkeypatch.setattr(page, '_present_screen_text_result', presented.append)
    monkeypatch.setattr(page, '_request_screen_text', lambda *args: requests.append(args))
    result = ScreenTextResult('consent_required', 'Recognized locally', 'local', consent_required=kind)
    try:
        page._handle_screen_text_result(result, b'test image', 'translate', 'English', '')
        assert screen_text_dialog.user_setting_dict[key] is granted
        assert presented == ([] if granted else [result])
        assert requests == ([(b'test image', 'translate', 'English', '')] if granted else [])
        assert page.last_screen_text == ('Previous result' if granted else None)
    finally:
        page.close()


def test_local_capture_starts_without_cloud_consent(monkeypatch, *, lifetime_factory):
    lifetime_factory()
    monkeypatch.setattr(tools, 'ask_for_consent', lambda *_args: (_ for _ in ()).throw(AssertionError('cloud prompt')))
    page = tools.ToolsSettingUI(lifetime=lifetime_factory())
    picker = page.start_screen_text()
    assert picker is not None
    picker.close()
    page.close()


def test_empty_local_success_stays_empty_in_tools_ui(monkeypatch, *, lifetime_factory):
    lifetime_factory()
    page = tools.ToolsSettingUI(lifetime=lifetime_factory())
    result = ScreenTextResult('success', '', 'Windows.Media.Ocr')
    shown = []
    class LocalService:
        def read_result_async(self, data, callback, **kwargs):
            callback(result)
    page.screen_text_service = LocalService()
    monkeypatch.setattr(page, '_present_screen_text_result', shown.append)
    image = QPixmap(64, 32)
    image.fill(QColor('white'))
    page._read_capture(image)
    QCoreApplication.processEvents()
    assert page.last_screen_text == ''
    assert shown == [result]
    page.close()
