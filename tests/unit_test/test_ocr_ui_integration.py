from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QColor, QPixmap

from frontengine.ui.page.tools import tools_setting_ui as tools
from frontengine.utils.screen_text.screen_text_service import ScreenTextResult


def test_local_capture_starts_without_cloud_consent(monkeypatch):
    monkeypatch.setattr(tools, 'ask_for_consent', lambda *_args: (_ for _ in ()).throw(AssertionError('cloud prompt')))
    page = tools.ToolsSettingUI()
    picker = page.start_screen_text()
    assert picker is not None
    picker.close()
    page.close()


def test_empty_local_success_stays_empty_in_tools_ui(monkeypatch):
    page = tools.ToolsSettingUI()
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
