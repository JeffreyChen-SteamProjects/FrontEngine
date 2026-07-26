"""
剪貼簿監看：把使用者複製的文字送進 ClipboardHistory。只有被明確 start()
之後才會監看，stop() 立刻停止；不監看時完全不碰剪貼簿。

Watch the clipboard and feed copied text into ClipboardHistory. It only listens
after an explicit start(), stops immediately on stop(), and does not touch the
clipboard at all while it is off.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication

from frontengine.utils.clipboard.clipboard_history import ClipboardHistory
from frontengine.utils.logging.loggin_instance import front_engine_logger


class ClipboardWatcher(QObject):
    """把 QClipboard 的變更接到歷史紀錄上。"""

    captured = Signal(str)

    def __init__(self, history: ClipboardHistory, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.history = history
        self._clipboard = None
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> bool:
        """開始監看；沒有剪貼簿（無視窗環境）回傳 False。"""
        if self._running:
            return True
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:  # pragma: no cover - no clipboard at all
            return False
        self._clipboard = clipboard
        clipboard.dataChanged.connect(self._on_changed)
        self._running = True
        front_engine_logger.info("[ClipboardWatcher] start")
        return True

    def stop(self) -> None:
        """停止監看。"""
        if not self._running:
            return
        try:
            self._clipboard.dataChanged.disconnect(self._on_changed)
        except (RuntimeError, TypeError):  # pragma: no cover - already disconnected
            pass
        self._clipboard = None
        self._running = False
        front_engine_logger.info("[ClipboardWatcher] stop")

    def _on_changed(self) -> None:
        if not self._running or self._clipboard is None:
            return
        try:
            text = self._clipboard.text()
        except RuntimeError:  # pragma: no cover - clipboard torn down
            return
        self.capture(text)

    def capture(self, text: str) -> bool:
        """收下一筆內容（測試會直接呼叫）；沒收下就回傳 False。"""
        entry = self.history.add(text)
        if entry is None:
            return False
        self.captured.emit(entry["text"])
        return True
