"""Reviewable certificate controls and separate cloud consent in result UI."""
from frontengine.ui.dialog.remote_control_dialog import RemoteControlDialog
from frontengine.ui.dialog import screen_text_dialog
from frontengine.utils.remote.remote_server import RemoteServer
from frontengine.utils.screen_text.screen_text_service import ScreenTextResult


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
