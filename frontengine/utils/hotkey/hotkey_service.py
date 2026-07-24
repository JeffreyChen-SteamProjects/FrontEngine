from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger

try:  # pynput ships native backends that may not load on every platform
    from pynput import keyboard as _pynput_keyboard  # type: ignore
except Exception as _import_error:  # pragma: no cover - environment guard
    _pynput_keyboard = None
    _PYNPUT_ERROR: Optional[BaseException] = _import_error
else:
    _PYNPUT_ERROR = None


def is_valid_hotkey(combo: str) -> bool:
    """
    檢查組合鍵字串是否可被 pynput 解析。pynput 不可用時無法驗證，一律視為
    有效（交由執行期處理）。
    Return True if `combo` parses as a pynput hotkey. When pynput is
    unavailable it cannot be validated, so it is accepted.
    """
    if not isinstance(combo, str) or not combo.strip():
        return False
    if _pynput_keyboard is None:
        return True
    try:
        _pynput_keyboard.HotKey.parse(combo)
        return True
    except Exception:
        return False


class HotkeyService(QObject):
    """
    Thin wrapper around pynput.keyboard.GlobalHotKeys that re-emits every
    hotkey press as a Qt signal so slots run on the UI thread. Bindings
    are a mapping of pynput hotkey strings to action names, e.g.
    ``{"<ctrl>+<shift>+<f12>": "close_all"}``.

    If pynput is missing or fails to import (headless CI, unsupported
    backend), the service degrades to a no-op and logs the reason.
    """

    hotkey_triggered = Signal(str)

    def __init__(self, bindings: Dict[str, str], parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._bindings: Dict[str, str] = dict(bindings)
        self._listener: Optional[Any] = None

    def start(self) -> bool:
        if self._listener is not None:
            return True
        if _pynput_keyboard is None:
            front_engine_logger.warning(
                f"[HotkeyService] pynput unavailable, hotkeys disabled ({_PYNPUT_ERROR!r})"
            )
            return False
        if not self._bindings:
            return False
        dispatch = {}
        for combo, action in self._bindings.items():
            # Validate each combo up front so one malformed binding cannot
            # take down every hotkey when GlobalHotKeys parses the map.
            try:
                _pynput_keyboard.HotKey.parse(combo)
            except Exception as parse_error:  # pragma: no cover - defensive boundary
                front_engine_logger.warning(
                    f"[HotkeyService] Ignoring invalid hotkey {combo!r}: {parse_error!r}"
                )
                continue
            dispatch[combo] = (lambda name=action: self.hotkey_triggered.emit(name))
        if not dispatch:
            front_engine_logger.warning("[HotkeyService] No valid hotkeys to bind")
            return False
        try:
            self._listener = _pynput_keyboard.GlobalHotKeys(dispatch)
            self._listener.daemon = True
            self._listener.start()
            front_engine_logger.info(
                f"[HotkeyService] Started with bindings {list(self._bindings)}"
            )
            return True
        except Exception as error:
            front_engine_logger.warning(f"[HotkeyService] Failed to start: {error!r}")
            self._listener = None
            return False

    def stop(self) -> None:
        listener = self._listener
        self._listener = None
        if listener is not None:
            try:
                listener.stop()
            except Exception as error:
                front_engine_logger.warning(f"[HotkeyService] Stop error: {error!r}")
