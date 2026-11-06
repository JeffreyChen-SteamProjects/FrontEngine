"""Reviewable certificate controls and separate cloud consent in result UI."""
import pytest
from frontengine.ui.dialog.remote_control_dialog import RemoteControlDialog
from frontengine.ui.dialog import screen_text_dialog
from frontengine.utils.remote.remote_server import RemoteServer
from frontengine.utils.screen_text.screen_text_service import ScreenTextResult


@pytest.mark.parametrize('kind', ['text', 'capture'])
@pytest.mark.parametrize('destroy', [False, True])
def test_closed_ocr_parent_discards_consent_answer(monkeypatch, kind, destroy):
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QDialog, QMessageBox
    from shiboken6 import isValid

    key = screen_text_dialog.TEXT_CONSENT_KEY if kind == 'text' else screen_text_dialog.CONSENT_KEY
    ask = screen_text_dialog.ask_for_text_consent if kind == 'text' else screen_text_dialog.ask_for_consent
    monkeypatch.setitem(screen_text_dialog.user_setting_dict, key, False)
    writes = []
    monkeypatch.setattr(screen_text_dialog, 'write_user_setting', lambda: writes.append(True))
    parent = QDialog()
    parent.show()
    def answer(*_args):
        parent.reject()
        if destroy:
            parent.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        return QMessageBox.StandardButton.Yes
    monkeypatch.setattr(QMessageBox, 'question', answer)
    try:
        assert not ask(parent)
        assert screen_text_dialog.user_setting_dict[key] is False
        assert writes == []
        def unexpected(*_args):
            pytest.fail('Closed OCR parent reopened consent')
        monkeypatch.setattr(QMessageBox, 'question', unexpected)
        assert not ask(parent)
    finally:
        if isValid(parent):
            parent.close()


@pytest.mark.parametrize('kind', ['text', 'capture'])
def test_ocr_consent_refuse_reopen_accept_keeps_permissions_separate(monkeypatch, kind):
    from PySide6.QtWidgets import QDialog, QMessageBox

    key = screen_text_dialog.TEXT_CONSENT_KEY if kind == 'text' else screen_text_dialog.CONSENT_KEY
    other = screen_text_dialog.CONSENT_KEY if kind == 'text' else screen_text_dialog.TEXT_CONSENT_KEY
    ask = screen_text_dialog.ask_for_text_consent if kind == 'text' else screen_text_dialog.ask_for_consent
    for name in (key, other):
        monkeypatch.setitem(screen_text_dialog.user_setting_dict, name, False)
    writes = []
    monkeypatch.setattr(screen_text_dialog, 'write_user_setting',
                        lambda: writes.append((screen_text_dialog.user_setting_dict[key], screen_text_dialog.user_setting_dict[other])))
    choices = iter([QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes])
    monkeypatch.setattr(QMessageBox, 'question', lambda *_args: next(choices))
    parent = QDialog()
    try:
        parent.show()
        assert not ask(parent)
        assert writes == [(False, False)]
        parent.reject()
        parent.show()
        assert ask(parent)
        assert writes == [(False, False), (True, False)]
        assert ask(parent)
        assert len(writes) == 2
    finally:
        parent.close()


@pytest.mark.parametrize('closing', ['reject', 'close', 'destroy'])
@pytest.mark.parametrize('existing', [False, True])
def test_remote_export_discards_path_after_dialog_closes(tmp_path, monkeypatch, closing, existing):
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QFileDialog
    from shiboken6 import isValid
    from frontengine.ui.dialog import remote_control_dialog
    from frontengine.utils.remote import remote_server

    monkeypatch.setattr(remote_control_dialog, 'remote_enabled', lambda: False)
    monkeypatch.setattr(remote_server, 'local_address', lambda: '127.0.0.1')
    server = RemoteServer(port=0, certificate_dir=tmp_path / 'private')
    monkeypatch.setattr(server, 'start', lambda: pytest.fail('Export test must not start a listener'))
    dialog = RemoteControlDialog(remote=server)
    dialog.show()
    destination = tmp_path / 'public.crt'
    if existing:
        destination.write_bytes(b'original certificate file')
    def choose_then_close(*_args):
        if closing == 'reject':
            dialog.reject()
        elif closing == 'close':
            dialog.close()
        else:
            dialog.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        return str(destination), ''
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', choose_then_close)
    try:
        assert not dialog.export_certificate()
        assert destination.read_bytes() == b'original certificate file' if existing else not destination.exists()
        assert server.certificate is None and not server.running
        def unexpected(*_args):
            pytest.fail('Closed remote dialog reopened the export picker')
        monkeypatch.setattr(QFileDialog, 'getSaveFileName', unexpected)
        assert not dialog.export_certificate()
    finally:
        if isValid(dialog):
            dialog.reject()
        server.stop()


def test_remote_export_picker_cancel_then_retry_without_listener(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    from frontengine.ui.dialog import remote_control_dialog
    from frontengine.utils.remote import remote_server

    monkeypatch.setattr(remote_control_dialog, 'remote_enabled', lambda: False)
    monkeypatch.setattr(remote_server, 'local_address', lambda: '127.0.0.1')
    server = RemoteServer(port=0, certificate_dir=tmp_path / 'private')
    monkeypatch.setattr(server, 'start', lambda: pytest.fail('Export test must not start a listener'))
    dialog = RemoteControlDialog(remote=server)
    target = tmp_path / 'public.crt'
    choices = iter([('', ''), (str(target), '')])
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *_args: next(choices))
    try:
        assert not dialog.export_certificate()
        assert not target.exists() and server.certificate is None
        assert dialog.export_certificate()
        assert target.read_bytes() == server.certificate.certificate_path.read_bytes()
        assert target.read_bytes().startswith(b'-----BEGIN CERTIFICATE-----')
        assert b'PRIVATE KEY' not in target.read_bytes()
        assert not server.running
    finally:
        dialog.reject()
        server.stop()


def test_remote_dialog_reports_certificate_fingerprint_and_exports_public_certificate(tmp_path, monkeypatch):
    from frontengine.utils.remote import remote_server
    monkeypatch.setattr(remote_server, "local_address", lambda: "127.0.0.1")
    server = RemoteServer(port=0, certificate_dir=tmp_path / "private")
    assert server.start(), server.last_error
    try:
        dialog = RemoteControlDialog(remote=server)
        assert server.certificate.fingerprint in dialog.certificate_label.text()
        target = tmp_path / "public.crt"
        monkeypatch.setattr("frontengine.ui.dialog.remote_control_dialog.QFileDialog.getSaveFileName",
                            lambda *_args: (str(target), ""))
        assert dialog.export_certificate()
        assert target.read_bytes().startswith(b"-----BEGIN CERTIFICATE-----")
        assert b"PRIVATE KEY" not in target.read_bytes()
    finally:
        server.stop()


def test_remote_dialog_shows_failed_tls_start_and_unchecks_enable(tmp_path, monkeypatch):
    server = RemoteServer(port=0, certificate_dir=tmp_path)
    monkeypatch.setattr(server._certificate_store, "provision",
                        lambda *_args: (_ for _ in ()).throw(OSError("private key denied")))
    dialog = RemoteControlDialog(remote=server)
    dialog.remote_checkbox.setChecked(True)
    assert "private key denied" in dialog.remote_url_label.text()
    assert not dialog.remote_checkbox.isChecked()


def test_screen_text_result_displays_backend_and_preserves_empty_success():
    result = ScreenTextResult("success", "", "Windows.Media.Ocr")
    dialog = screen_text_dialog.ScreenTextDialog(result=result)
    assert dialog.text() == ""
    assert "Windows.Media.Ocr" in dialog.backend_label.text()
    assert hasattr(dialog, "text_consent_checkbox")


def test_local_ocr_status_does_not_require_an_api_key(monkeypatch):
    monkeypatch.setattr(screen_text_dialog, "api_key", lambda: None)
    monkeypatch.setattr(screen_text_dialog.LocalOcr, "available", lambda _self: True)
    assert "local" in screen_text_dialog.ScreenTextDialog.status_text().lower()
