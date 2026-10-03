"""Local extraction and explicit text/image cloud consent boundaries."""
from frontengine.utils.screen_text.screen_text_service import ScreenTextService
import sys
import threading

import pytest


def result(text="hello", status="success", backend="test-local", error=""):
    from frontengine.utils.screen_text.local_ocr import OcrResult
    return OcrResult(status=status, text=text, backend=backend, error=error)


class Local:
    name = "test-local"

    def __init__(self, value):
        self.value = value

    def available(self):
        return self.value.status != "unavailable"

    def recognize(self, _png):
        return self.value


class Client:
    def __init__(self):
        self.messages = self
        self.sent = []

    def create(self, **kwargs):
        self.sent.append(kwargs)
        block = type("Block", (), {"text": "translated"})()
        return type("Response", (), {"content": [block], "stop_reason": "end_turn"})()


def service(local, image_consent=False, text_consent=False, key=None):
    instance = ScreenTextService(local_backend=Local(local),
                                 consent_provider=lambda: image_consent,
                                 text_consent_provider=lambda: text_consent,
                                 key_provider=lambda: key)
    instance._client = Client()
    return instance


def test_local_extraction_needs_neither_key_nor_cloud_consent():
    instance = service(result())
    assert instance.available()
    assert instance.read(b"png") == "hello"
    assert instance.last_result.backend == "test-local"
    assert instance._client.sent == []


def test_empty_local_success_never_uploads_capture():
    instance = service(result(""), image_consent=True, text_consent=True, key="test")
    assert instance.read(b"png") == ""
    assert instance.last_result.status == "success"
    assert instance._client.sent == []


def test_unavailable_and_failed_ocr_are_distinct_and_require_image_consent():
    for status in ("unavailable", "error"):
        instance = service(result(status=status, error="missing language model"),
                           text_consent=True, key="test")
        answer = instance.read_result(b"png")
        assert answer.status == status
        assert answer.consent_required == "image"
        assert instance._client.sent == []


def test_translation_sends_local_text_without_image_with_text_consent():
    instance = service(result("a secret sign"), text_consent=True, key="test")
    assert instance.read(b"png", "translate", "German") == "translated"
    parts = instance._client.sent[0]["messages"][0]["content"]
    assert all(part["type"] == "text" for part in parts)
    assert "a secret sign" in parts[0]["text"]
    assert "German" in parts[-1]["text"]


def test_question_requires_text_consent_even_when_local_extraction_succeeds():
    instance = service(result(), key="test")
    answer = instance.read_result(b"png", "ask", question="What does it mean?")
    assert answer.consent_required == "text"
    assert instance._client.sent == []


def test_image_fallback_is_permitted_only_with_explicit_image_consent_and_key():
    instance = service(result(status="unavailable"), image_consent=True, key="test")
    assert instance.read(b"png") == "translated"
    assert instance._client.sent[0]["messages"][0]["content"][0]["type"] == "image"


def test_local_failure_and_empty_success_are_not_conflated():
    instance = service(result("", "error", error="decoder failed"))
    assert instance.read(b"png") is None
    assert instance.last_result.error == "decoder failed"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows native OCR integration")
def test_windows_ocr_reads_a_real_rendered_image_on_worker_thread():
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter
    from pathlib import Path
    import os
    from frontengine.utils.screen_text.local_ocr import WindowsOcr

    backend = WindowsOcr()
    if not backend.available():
        pytest.skip("Windows OCR projection packages are not installed")
    font_file = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arial.ttf"
    assert QFontDatabase.addApplicationFont(str(font_file)) >= 0
    image = QImage(1100, 180, QImage.Format.Format_RGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    painter.setPen(QColor("black"))
    painter.setFont(QFont("Arial", 48))
    painter.drawText(30, 110, "FRONT ENGINE 2026")
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, "PNG")
    replies = []
    worker = threading.Thread(target=lambda: replies.append(backend.recognize(bytes(data))))
    worker.start()
    worker.join(timeout=15)
    assert not worker.is_alive()
    assert replies[0].status == "success", replies[0].error
    assert "FRONT" in replies[0].text.upper()
    assert "ENGINE" in replies[0].text.upper()
    assert "2026" in replies[0].text


def test_vision_failure_and_empty_success_are_explicit():
    from frontengine.utils.screen_text.local_ocr import VisionOcr

    assert VisionOcr(recognizer=lambda _: "").recognize(b"png").status == "success"
    def fail(_png):
        raise RuntimeError("Vision language is unavailable")
    result = VisionOcr(recognizer=fail).recognize(b"png")
    assert result.status == "error"
    assert "language" in result.error


def test_local_chain_stops_on_empty_success():
    from frontengine.utils.screen_text.local_ocr import LocalOcr

    class Forbidden(Local):
        def recognize(self, _png):
            raise AssertionError("must not fall back after empty success")
    instance = LocalOcr([Local(result("")), Forbidden(result())])
    assert instance.recognize(b"png").successful


def test_tesseract_reports_missing_language_without_shell_execution(tmp_path):
    from frontengine.utils.screen_text.local_ocr import TesseractOcr

    executable = tmp_path / "tesseract"
    executable.write_bytes(b"placeholder")
    commands = []
    def runner(command, **kwargs):
        commands.append((command, kwargs))
        return type("Response", (), {"returncode": 1, "stderr": b"missing eng.traineddata"})()
    answer = TesseractOcr(executable=str(executable), runner=runner).recognize(b"png")
    assert answer.status == "error"
    assert "eng.traineddata" in answer.error
    assert commands[0][0][0] == str(executable.resolve())
    assert commands[0][1]["shell"] is False


def test_revoked_consent_prevents_cloud_send_even_after_request_is_prepared():
    granted = [True]
    def key():
        granted[0] = False
        return "test-key"
    instance = ScreenTextService(local_backend=Local(result()),
                                 text_consent_provider=lambda: granted[0], key_provider=key)
    instance._client = Client()
    answer = instance.read_result(b"png", "translate", "German")
    assert instance._client.sent == []
    assert answer.consent_required == "text"


def test_raised_local_error_can_use_explicitly_consented_image_fallback():
    class Broken(Local):
        def recognize(self, _png):
            raise RuntimeError("native worker failed")
    instance = ScreenTextService(local_backend=Broken(result()),
                                 consent_provider=lambda: True, key_provider=lambda: "test")
    instance._client = Client()
    assert instance.read(b"png") == "translated"
    assert instance._client.sent[0]["messages"][0]["content"][0]["type"] == "image"
