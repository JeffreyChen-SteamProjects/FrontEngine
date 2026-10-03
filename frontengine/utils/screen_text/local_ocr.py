"""Offline OCR adapters. Empty recognition is a successful result, never a fallback."""
from __future__ import annotations

import asyncio
import importlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Protocol, Sequence


@dataclass(frozen=True)
class OcrResult:
    status: str
    text: str = ""
    backend: str = ""
    error: str = ""

    @property
    def successful(self) -> bool:
        return self.status == "success"


class OcrBackend(Protocol):
    name: str

    def available(self) -> bool: ...

    def recognize(self, png_bytes: bytes) -> OcrResult: ...


def _modules_available(names: Sequence[str]) -> bool:
    try:
        for name in names:
            importlib.import_module(name)
        return True
    except (ImportError, OSError):
        return False


class WindowsOcr:
    name = "Windows.Media.Ocr"

    def available(self) -> bool:
        return sys.platform == "win32" and _modules_available((
            "winrt.windows.media.ocr", "winrt.windows.graphics.imaging",
            "winrt.windows.storage.streams", "winrt.windows.globalization"))

    def recognize(self, png_bytes: bytes) -> OcrResult:
        if not self.available():
            return OcrResult("unavailable", backend=self.name,
                             error="Windows OCR bindings are unavailable")
        try:
            import winrt.runtime

            winrt.runtime.init_apartment(0)
            try:
                return asyncio.run(self._recognize(png_bytes))
            finally:
                winrt.runtime.uninit_apartment()
        except Exception as error:
            return OcrResult("error", backend=self.name, error=str(error))

    async def _recognize(self, png_bytes: bytes) -> OcrResult:
        from winrt.windows.graphics.imaging import BitmapDecoder, BitmapPixelFormat
        from winrt.windows.media.ocr import OcrEngine
        from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream

        engine = OcrEngine.try_create_from_user_profile_languages()
        if engine is None:
            return OcrResult("unavailable", backend=self.name,
                             error="Install an OCR language in Windows Language settings")
        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream)
        bitmap = None
        try:
            writer.write_bytes(png_bytes)
            await writer.store_async()
            writer.detach_stream()
            stream.seek(0)
            decoder = await BitmapDecoder.create_async(stream)
            bitmap = await decoder.get_software_bitmap_async()
            if bitmap.bitmap_pixel_format not in (BitmapPixelFormat.BGRA8, BitmapPixelFormat.GRAY8):
                from winrt.windows.graphics.imaging import SoftwareBitmap
                converted = SoftwareBitmap.convert(bitmap, BitmapPixelFormat.BGRA8)
                bitmap.close()
                bitmap = converted
            if max(bitmap.pixel_width, bitmap.pixel_height) > OcrEngine.max_image_dimension:
                return OcrResult("error", backend=self.name,
                                 error="Selected image exceeds the Windows OCR size limit")
            response = await engine.recognize_async(bitmap)
            return OcrResult("success", "\n".join(line.text for line in response.lines), self.name)
        finally:
            if bitmap is not None:
                bitmap.close()
            writer.close()
            stream.close()


class VisionOcr:
    name = "macOS Vision"

    def __init__(self, languages: Optional[Sequence[str]] = None,
                 recognizer: Optional[Callable[[bytes], str]] = None) -> None:
        self.languages = list(languages or [])
        self._recognizer = recognizer

    def available(self) -> bool:
        return self._recognizer is not None or (sys.platform == "darwin"
                                               and _modules_available(("Vision", "Foundation", "objc")))

    def recognize(self, png_bytes: bytes) -> OcrResult:
        if not self.available():
            return OcrResult("unavailable", backend=self.name,
                             error="Install the PyObjC Vision framework binding")
        try:
            text = self._recognizer(png_bytes) if self._recognizer else self._native(png_bytes)
            return OcrResult("success", str(text or ""), self.name)
        except Exception as error:
            return OcrResult("error", backend=self.name, error=str(error))

    def _native(self, png_bytes: bytes) -> str:
        import objc
        import Vision
        from Foundation import NSData

        with objc.autorelease_pool():
            data = NSData.dataWithBytes_length_(png_bytes, len(png_bytes))
            request = Vision.VNRecognizeTextRequest.alloc().init()
            request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
            request.setUsesLanguageCorrection_(True)
            if self.languages:
                request.setRecognitionLanguages_(self.languages)
            handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(data, {})
            success, error = handler.performRequests_error_([request], None)
            if not success:
                raise RuntimeError(str(error or "Vision text recognition failed"))
            lines = []
            for observation in request.results() or []:
                candidates = observation.topCandidates_(1)
                if candidates:
                    lines.append(str(candidates[0].string()))
            return "\n".join(lines)


class TesseractOcr:
    name = "Tesseract"

    def __init__(self, language: str = "eng", executable: Optional[str] = None,
                 runner: Callable = subprocess.run) -> None:
        candidate = executable or shutil.which("tesseract")
        self.executable = str(Path(candidate).resolve()) if candidate else None
        self.language = language
        self._runner = runner

    def available(self) -> bool:
        return self.executable is not None and Path(self.executable).is_file()

    def recognize(self, png_bytes: bytes) -> OcrResult:
        if not self.available():
            return OcrResult("unavailable", backend=self.name,
                             error="Install Tesseract and its recognition language data")
        try:
            response = self._runner([self.executable, "stdin", "stdout", "-l", self.language],
                                    input=png_bytes, capture_output=True, shell=False, timeout=30)
            if response.returncode:
                return OcrResult("error", backend=self.name,
                                 error=response.stderr.decode("utf-8", errors="replace").strip())
            return OcrResult("success", response.stdout.decode("utf-8").strip(), self.name)
        except Exception as error:
            return OcrResult("error", backend=self.name, error=str(error))


class LocalOcr:
    """Try available native OCR first, then optional local Tesseract."""
    name = "local OCR"

    def __init__(self, backends: Optional[Sequence[OcrBackend]] = None) -> None:
        self.backends = list(backends) if backends is not None else [
            WindowsOcr(), VisionOcr(), TesseractOcr()]

    def available(self) -> bool:
        return any(backend.available() for backend in self.backends)

    def recognize(self, png_bytes: bytes) -> OcrResult:
        failures = []
        for backend in self.backends:
            if not backend.available():
                continue
            result = backend.recognize(png_bytes)
            if result.successful:
                return result
            failures.append(result)
        if failures:
            status = "error" if any(item.status == "error" for item in failures) else "unavailable"
            return OcrResult(status, backend=failures[-1].backend,
                             error="; ".join(f"{item.backend}: {item.error}" for item in failures))
        return OcrResult("unavailable", backend=self.name,
                         error="No local OCR backend is installed")
