"""
全域鍵盤／滑鼠監聽，供「按鍵顯示」與「點擊漣漪」使用。與熱鍵服務一樣建立在
pynput 之上，缺少或載入失敗時整個功能安靜停用（不影響其他覆蓋層）。

事件在 pynput 的背景執行緒觸發，因此一律以 Qt signal 轉回 UI 執行緒再處理。

Global keyboard and mouse watching for the keystroke display and click ripples.
Like the hotkey service it sits on pynput and disables itself quietly when that
is unavailable. Events fire on pynput's own thread, so they are re-emitted as Qt
signals and handled on the UI thread.
"""
from __future__ import annotations

from typing import Any, List, Optional

from PySide6.QtCore import QObject, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger

try:  # pynput ships native backends that may not load on every platform
    from pynput import keyboard as _pynput_keyboard  # type: ignore
    from pynput import mouse as _pynput_mouse  # type: ignore
except Exception as _import_error:  # pragma: no cover - environment guard
    _pynput_keyboard = None
    _pynput_mouse = None
    _PYNPUT_ERROR: Optional[BaseException] = _import_error
else:
    _PYNPUT_ERROR = None

# 這些鍵按住時算修飾鍵，會和下一個鍵組成 `Ctrl + S`
# Held modifiers combine with the next key into e.g. "Ctrl + S".
_MODIFIER_PREFIXES = ("ctrl", "alt", "shift", "cmd")


def key_name(key) -> str:
    """
    把 pynput 的按鍵物件轉成名稱字串；取不到就用 str()。
    Turn a pynput key object into a name; falls back to str().
    """
    for attribute in ("char", "name"):
        value = getattr(key, attribute, None)
        if value:
            return str(value)
    return str(key).replace("Key.", "").strip("'")


def is_modifier(name: str) -> bool:
    """該按鍵是否為修飾鍵。"""
    return str(name).lower().startswith(_MODIFIER_PREFIXES)


def combo_with_modifiers(name: str, held: List[str]) -> List[str]:
    """把目前按住的修飾鍵和這次的按鍵組成一組（修飾鍵在前）。"""
    combo = [modifier for modifier in held if is_modifier(modifier)]
    if name and (not is_modifier(name) or not combo):
        combo.append(name)
    return combo


class InputWatchService(QObject):
    """
    監聽全域按鍵與滑鼠點擊，並以 Qt signal 送出：
      - key_pressed(list)：按鍵組合（例如 ["ctrl", "s"]）
      - mouse_clicked(int, int)：點擊座標
    pynput 不可用時 start() 回傳 False，其餘功能照常。
    """

    key_pressed = Signal(list)
    mouse_clicked = Signal(int, int)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._keyboard_listener: Optional[Any] = None
        self._mouse_listener: Optional[Any] = None
        self._held: List[str] = []

    @staticmethod
    def available() -> bool:
        """pynput 是否可用 / Whether pynput loaded."""
        return _pynput_keyboard is not None and _pynput_mouse is not None

    def start(self, keyboard: bool = True, mouse: bool = True) -> bool:
        """開始監聽；pynput 不可用時記錄原因並回傳 False。"""
        if not self.available():
            front_engine_logger.warning(
                f"[InputWatchService] pynput unavailable, input watching disabled ({_PYNPUT_ERROR!r})")
            return False
        try:
            if keyboard and self._keyboard_listener is None:
                self._keyboard_listener = _pynput_keyboard.Listener(
                    on_press=self._on_press, on_release=self._on_release)
                self._keyboard_listener.start()
            if mouse and self._mouse_listener is None:
                self._mouse_listener = _pynput_mouse.Listener(on_click=self._on_click)
                self._mouse_listener.start()
        except Exception as error:  # pragma: no cover - backend boundary
            front_engine_logger.warning(f"[InputWatchService] listener failed: {error!r}")
            self.stop()
            return False
        return True

    def stop(self) -> None:
        """停止監聽並釋放 listener。"""
        for attribute in ("_keyboard_listener", "_mouse_listener"):
            listener = getattr(self, attribute, None)
            if listener is not None:
                try:
                    listener.stop()
                except Exception as error:  # pragma: no cover - backend boundary
                    front_engine_logger.debug(f"[InputWatchService] stop failed: {error!r}")
                setattr(self, attribute, None)
        self._held = []

    # --- callbacks (pynput thread) ---------------------------------------
    def _on_press(self, key) -> None:
        name = key_name(key)
        if is_modifier(name):
            if name not in self._held:
                self._held.append(name)
            return
        self.key_pressed.emit(combo_with_modifiers(name, self._held))

    def _on_release(self, key) -> None:
        name = key_name(key)
        if name in self._held:
            self._held.remove(name)

    def _on_click(self, x, y, _button, pressed) -> None:
        if pressed:
            self.mouse_clicked.emit(int(x), int(y))
