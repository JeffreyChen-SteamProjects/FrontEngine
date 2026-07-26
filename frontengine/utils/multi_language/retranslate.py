"""
即時換語言：記住每個控制項的文字是從哪個鍵來的，換語言時原地重寫一遍。

以前換語言要重開程式，因為每個標籤都是在建構時查一次字典就固定了。這裡在
查字典的當下把「控制項 + 要呼叫的 setter + 鍵」記下來，換語言時照著重設。

控制項用弱參考持有：覆蓋層關掉之後不該因為這張表而活著。底層 C++ 物件先被
銷毀時 setter 會丟 RuntimeError，遇到就把那筆刪掉。

Live language switching: remember which key produced each widget's text, and
write it again when the language changes.

Changing language used to need a restart, because every label looked the
dictionary up once at construction and kept the result. This records the
widget, the setter to call and the key at the moment of that lookup, and
replays it later.

Widgets are held weakly - an overlay that was closed must not stay alive just
because this table mentions it. When the underlying C++ object goes first the
setter raises RuntimeError, and that entry is dropped.
"""
from __future__ import annotations

import weakref
from typing import Any, Callable, List, Optional, Tuple

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


def translate(key: str, fallback: str = "") -> str:
    """查目前語言的字串；查不到就用 fallback（再不然就用鍵本身）。"""
    return language_wrapper.language_word_dict.get(key) or fallback or key


class Retranslator:
    """
    控制項與鍵的對照表。bind() 記一筆，apply() 用目前語言重寫全部。
    A table of widgets and the keys behind them: bind() records one, apply()
    rewrites them all in the current language.
    """

    def __init__(self) -> None:
        # (widget 弱參考, setter 名稱, 鍵, fallback, 額外參數)
        self._entries: List[Tuple[Any, str, str, str, tuple]] = []
        self._callbacks: List[Any] = []

    def __len__(self) -> int:
        return len(self._entries)

    def bind(self, widget: Any, key: str, fallback: str = "",
             setter: str = "setText", *args: Any) -> str:
        """
        立刻把文字設上去，並記住它來自哪個鍵；回傳的也是同一個字串。

        設定與登記寫在一起，呼叫端就不必把同一段文字寫兩遍——先前建構時寫一次、
        登記時再寫一次，長句子等於在檔案裡出現兩份。
        額外參數給 setTabText 這種需要索引的 setter 用（索引寫在文字前面）。

        Set the text now and remember the key behind it, returning that same
        string. Doing both here means the caller writes the wording once: it
        used to appear twice, once at construction and once at registration,
        which for the longer sentences meant two copies in the file.
        """
        text = translate(key, fallback)
        if widget is None:
            return text
        try:
            reference: Any = weakref.ref(widget)
        except TypeError:  # pragma: no cover - 少數 Qt 型別不支援弱參考
            reference = lambda widget=widget: widget  # noqa: E731
        self._entries.append((reference, setter, key, fallback, args))
        method = getattr(widget, setter, None)
        if method is not None:
            method(*args, text)
        return text

    def set_text(self, widget: Any, key: str, fallback: str = "",
                 setter: str = "setText") -> None:
        """
        立刻用目前語言設定文字，並把這個控制項改記到這個鍵。
        給執行期會換字的按鈕用（例如「開始塗鴉」/「停止塗鴉」）：換語言時要跟著
        目前的狀態走，而不是回到建構當下那一個。
        Set the text now and re-point this widget at this key. For buttons whose
        wording changes at runtime ("Start drawing" / "Stop drawing"), so a
        language switch follows the state they are actually in.
        """
        if widget is None:
            return
        self.forget(widget)
        text = self.bind(widget, key, fallback, setter)
        getattr(widget, setter)(text)

    def bind_call(self, callback: Callable[[], Any]) -> None:
        """
        給「文字是組出來的」情況用的逃生口——例如提示句後面還要接一段樣板，
        那不是單一個鍵能表達的。換語言時把這個函式再叫一次就好。
        以弱參考記住繫結方法，頁面關掉就不會因為這張表而活著。
        An escape hatch for text that is composed rather than looked up - a hint
        with a template appended, say, which no single key can express. On a
        language change the callback simply runs again. Bound methods are held
        weakly, so a page that goes away is not kept alive by this table.
        """
        try:
            reference: Any = weakref.WeakMethod(callback)  # type: ignore[arg-type]
        except TypeError:
            reference = lambda callback=callback: callback  # noqa: E731
        self._callbacks.append(reference)

    def forget(self, widget: Any) -> None:
        """移除某個控制項先前的登記。"""
        self._entries = [entry for entry in self._entries
                         if entry[0]() is not None and entry[0]() is not widget]

    def apply(self) -> int:
        """
        用目前語言重寫每一筆，回傳成功重寫的數量。已消失的控制項順手清掉。
        Rewrite every entry in the current language and return how many were
        rewritten, pruning whatever has gone away.
        """
        alive: List[Tuple[Any, str, str, str, tuple]] = []
        applied = 0
        for reference, setter, key, fallback, args in self._entries:
            widget = reference()
            if widget is None:
                continue
            method: Optional[Callable[..., Any]] = getattr(widget, setter, None)
            if method is None:
                continue
            try:
                method(*args, translate(key, fallback))
            except RuntimeError:
                # 底層物件已被銷毀，這筆不用留 / The C++ object is gone.
                continue
            alive.append((reference, setter, key, fallback, args))
            applied += 1
        self._entries = alive
        alive_callbacks = []
        for reference in self._callbacks:
            callback = reference()
            if callback is None:
                continue
            try:
                callback()
            except RuntimeError:
                continue
            alive_callbacks.append(reference)
            applied += 1
        self._callbacks = alive_callbacks
        front_engine_logger.info(
            f"[Retranslator] applied {applied} strings in {language_wrapper.language}")
        return applied


retranslator = Retranslator()


def tr(widget: Any, key: str, fallback: str = "", setter: str = "setText", *args: Any) -> Any:
    """
    設定文字、登記，然後把控制項本身傳回來，所以可以直接寫在指派的右邊：

        self.hint_label = tr(QLabel(), "signage_hint", "Presets are saved from ...")

    寫成一行是有意的。先前是「建一行、登記一行」，同一個形狀重複兩百多次，
    連工具都看得出來那是樣板。
    Set the text, register it, and hand the widget back so it can sit on the
    right of an assignment. One line on purpose: building and registering as two
    lines repeated the same shape over two hundred times, plainly boilerplate.
    """
    retranslator.bind(widget, key, fallback, setter, *args)
    return widget
