"""Explicit capture history with local OCR only and no clipboard monitoring."""
from pathlib import Path
from typing import Callable

from frontengine.utils.image_history.service import ImageHistoryService
from frontengine.utils.screen_text.local_ocr import LocalOcr


class CaptureHistoryService(ImageHistoryService):
    """Keep screenshot history independent from clipboard consent and persistence."""

    def __init__(self, path: str | Path, config: dict | None = None, parent=None,
                 *, indexer: Callable | None = None) -> None:
        super().__init__(path, config, parent, clipboard_provider=lambda: None,
                         indexer=indexer or LocalOcr().recognize)
