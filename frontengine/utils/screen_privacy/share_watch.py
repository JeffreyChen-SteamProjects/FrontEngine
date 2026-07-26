"""
偵測「可能正在分享畫面」：看使用者指定的會議程式在不在。

Windows 沒有可靠的「我現在被擷取了嗎」API，所以這裡用的是誠實的近似：
使用者自己列出會議軟體（Zoom、Teams、Discord…），只要那些程式有開著視窗，
就當作可能在分享。這是刻意選擇的做法——與其猜錯，不如讓使用者說了算。

Spot "probably sharing the screen" by watching for the meeting apps the user
named.

Windows has no dependable "am I being captured" API, so this is an honest
approximation: the user lists their conferencing apps, and any of them having a
window open counts as possibly sharing. That is deliberate - better to let the
user decide than to guess wrong.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.smart_pause.pause_rules import normalize_app_name, parse_app_list
from frontengine.utils.window_pin.window_pin import list_windows

# 常見的會議／串流程式，當作預設值；使用者可以自己改
# The usual conferencing and streaming apps, as a starting point the user edits.
DEFAULT_SHARING_APPS = ("zoom", "teams", "ms-teams", "discord", "obs64", "obs",
                        "slack", "webex", "gotomeeting")
DEFAULT_INTERVAL_MS = 3000


def running_app_names(lister: Optional[Callable[[], List]] = None) -> List[str]:
    """
    目前有視窗的程式名稱（正規化過）。用視窗列舉而不是列舉所有程序：
    看得見的視窗才可能被分享，也不需要更高的權限。
    The normalized names of apps that currently have a window. Window
    enumeration rather than a full process list: only visible windows can be
    shared, and it needs no extra privileges.
    """
    names = []
    for _handle, title in (lister or list_windows)() or []:
        name = normalize_app_name(title)
        if name and name not in names:
            names.append(name)
    return names


def sharing_app_running(watched: Any, window_titles: List[str]) -> Optional[str]:
    """
    有沒有被盯著的程式開著視窗。比對是「視窗標題裡含有那個名字」——會議軟體
    的標題通常帶著自己的名字（例如 "Zoom Meeting"），比對執行檔名反而抓不到
    瀏覽器裡開的會議。回傳第一個命中的名字，沒有就 None。
    Whether one of the watched apps has a window. Matching is "the title
    contains the name", because meeting windows usually carry their app's name
    ("Zoom Meeting") while an executable-name match would miss a meeting held
    in a browser tab. Returns the first hit, or None.
    """
    wanted = parse_app_list(watched) or list(DEFAULT_SHARING_APPS)
    haystack = [title.lower() for title in window_titles]
    for name in wanted:
        if any(name in title for title in haystack):
            return name
    return None


class ShareWatchService(QObject):
    """
    定時檢查有沒有會議程式開著，狀態改變時發出訊號。視窗來源與設定都可注入。
    Poll for a conferencing app and signal when that changes. Both the window
    source and the configuration are injectable.
    """

    sharing_changed = Signal(bool, str)  # (可能在分享, 命中的程式名稱)

    def __init__(self, config_provider: Optional[Callable[[], Dict[str, Any]]] = None,
                 window_provider: Optional[Callable[[], List]] = None,
                 interval_ms: int = DEFAULT_INTERVAL_MS,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._config_provider = config_provider or (lambda: {})
        self._window_provider = window_provider or list_windows
        self._sharing = False
        self._match = ""
        self._timer = QTimer(self)
        self._timer.setInterval(max(1000, int(interval_ms)))
        self._timer.timeout.connect(self.poll_once)

    @property
    def sharing(self) -> bool:
        return self._sharing

    @property
    def match(self) -> str:
        """目前是哪個程式讓它判斷成「在分享」。"""
        return self._match

    def start(self) -> None:
        front_engine_logger.info("[ShareWatch] start")
        self._timer.start()

    def stop(self) -> None:
        front_engine_logger.info("[ShareWatch] stop")
        self._timer.stop()

    def poll_once(self) -> None:
        """檢查一次（測試會直接呼叫）。"""
        try:
            config = self._config_provider() or {}
            if not config.get("enabled", False):
                self._update(False, "")
                return
            titles = [str(title) for _handle, title in (self._window_provider() or [])]
            match = sharing_app_running(config.get("apps"), titles)
        except Exception as error:  # pragma: no cover - defensive boundary
            front_engine_logger.warning(f"[ShareWatch] poll error: {error!r}")
            return
        self._update(match is not None, match or "")

    def _update(self, sharing: bool, match: str) -> None:
        if sharing == self._sharing:
            self._match = match
            return
        self._sharing = sharing
        self._match = match
        front_engine_logger.info(
            f"[ShareWatch] sharing={sharing}" + (f" | {match}" if match else ""))
        self.sharing_changed.emit(sharing, match)
