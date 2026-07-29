"""
剪貼簿歷史：記住最近複製過的文字，可以搜尋、釘選常用片語，再貼回去。

**剪貼簿常常裝著密碼**，所以這裡的預設是最保守的一組：**預設關閉**、
**只留在記憶體**（除非使用者自己打開「保存到檔案」）、可以隨時清空，
而且永遠不會把內容送到任何地方。

Clipboard history: remember what was copied recently, search it, pin the
phrases you reuse, and put them back.

**Clipboards routinely hold passwords**, so the defaults here are the cautious
ones: **off by default**, **memory only** unless the user explicitly turns on
saving, clearable at any time, and never sent anywhere.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

DEFAULT_LIMIT = 50
MIN_LIMIT = 5
MAX_LIMIT = 500
# 超過這個長度就不收（多半是整份文件，留著只會吃記憶體）
# Longer than this is not kept: it is usually a whole document and only costs memory.
MAX_ENTRY_LENGTH = 20000


def clamp_limit(value: Any, fallback: int = DEFAULT_LIMIT) -> int:
    """保留筆數夾在合理範圍。"""
    try:
        return max(MIN_LIMIT, min(MAX_LIMIT, int(value)))
    except (TypeError, ValueError):
        return fallback


def normalize_entry(entry: Any) -> Optional[Dict[str, Any]]:
    """
    整理一筆剪貼簿紀錄；沒有文字或格式不對就回傳 None。
    Normalize one clipboard entry; None when there is no text or it is malformed.
    """
    if isinstance(entry, str):
        entry = {"text": entry}
    if not isinstance(entry, dict):
        return None
    text = str(entry.get("text", ""))
    if not text.strip() or len(text) > MAX_ENTRY_LENGTH:
        return None
    return {
        "text": text,
        "pinned": bool(entry.get("pinned", False)),
        "at": str(entry.get("at", "")),
    }


def normalize_entries(entries: Any) -> List[Dict[str, Any]]:
    """整理整份歷史，跳過壞掉的項目。"""
    if not isinstance(entries, (list, tuple)):
        return []
    cleaned = []
    for entry in entries:
        normalized = normalize_entry(entry)
        if normalized is not None:
            cleaned.append(normalized)
    return cleaned


def preview(text: Any, width: int = 60) -> str:
    """把一筆內容縮成一行預覽（換行變成空白，太長就截斷）。"""
    single_line = " ".join(str(text or "").split())
    limit = max(8, int(width))
    if len(single_line) <= limit:
        return single_line
    return single_line[: limit - 1] + "…"


class ClipboardHistory:
    """
    最近複製過的內容。釘選的項目永遠排在前面，也不會因為超過上限被擠掉。
    Recently copied items. Pinned entries sort first and are never evicted by
    the size limit.
    """

    def __init__(self, limit: int = DEFAULT_LIMIT,
                 now_provider: Callable[[], datetime] = datetime.now) -> None:
        self.limit = clamp_limit(limit)
        self._now = now_provider
        self.entries: List[Dict[str, Any]] = []

    def __len__(self) -> int:
        return len(self.entries)

    def set_limit(self, limit: int) -> None:
        self.limit = clamp_limit(limit)
        self._evict()

    def add(self, text: Any) -> Optional[Dict[str, Any]]:
        """
        收下一筆新複製的內容。和最近一筆相同就不重複收；已經存在的舊項目
        會被移到最前面而不是變成第二份。
        Take a newly copied item. An exact repeat of the newest entry is
        ignored, and an item already in the list moves to the front instead of
        being duplicated.
        """
        entry = normalize_entry({"text": text, "at": self._now().isoformat(timespec="seconds")})
        if entry is None:
            return None
        existing = self._find(entry["text"])
        if existing is not None:
            entry["pinned"] = existing["pinned"]
            self.entries.remove(existing)
        self.entries.insert(0, entry)
        self._evict()
        return entry

    def _find(self, text: str) -> Optional[Dict[str, Any]]:
        for entry in self.entries:
            if entry["text"] == text:
                return entry
        return None

    def _evict(self) -> None:
        """超過上限時丟掉最舊的未釘選項目。"""
        while len(self.entries) > self.limit:
            # 掃到 index 1 為止：index 0 是剛剛才收下的那一筆。掃到 0 的話，
            # 當比較舊的項目全被釘選時，被丟掉的就是使用者這一秒複製的東西——
            # add() 照樣回報成功，剪貼簿紀錄卻再也沒有新內容進得去。
            # Stop at index 1: index 0 is the entry just taken. Scanning down to
            # 0 means that once every older entry is pinned, the one thrown away
            # is what the user copied a moment ago - add() still reports success
            # while nothing new can ever enter the history again.
            for index in range(len(self.entries) - 1, 0, -1):
                if not self.entries[index]["pinned"]:
                    self.entries.pop(index)
                    break
            else:
                # 全部都被釘選了，那就尊重使用者的選擇，不再丟
                # Everything is pinned: respect that and stop evicting.
                return

    def set_pinned(self, text: Any, pinned: bool) -> bool:
        """釘選或取消釘選某一筆；找不到回傳 False。"""
        entry = self._find(str(text))
        if entry is None:
            return False
        entry["pinned"] = bool(pinned)
        return True

    def remove(self, text: Any) -> bool:
        """刪掉某一筆。"""
        entry = self._find(str(text))
        if entry is None:
            return False
        self.entries.remove(entry)
        return True

    def clear(self, keep_pinned: bool = True) -> None:
        """清空歷史；預設保留釘選的片語。"""
        self.entries = [entry for entry in self.entries if entry["pinned"]] if keep_pinned else []

    def ordered(self) -> List[Dict[str, Any]]:
        """釘選的在前，其餘依加入順序（新的在前）。"""
        pinned = [entry for entry in self.entries if entry["pinned"]]
        rest = [entry for entry in self.entries if not entry["pinned"]]
        return pinned + rest

    def search(self, needle: Any) -> List[Dict[str, Any]]:
        """依關鍵字過濾（不分大小寫）；空字串代表全部。"""
        text = str(needle or "").strip().lower()
        if not text:
            return self.ordered()
        return [entry for entry in self.ordered() if text in entry["text"].lower()]

    def to_list(self, include_unpinned: bool = True) -> List[Dict[str, Any]]:
        """
        轉成可儲存的資料。預設只有在使用者選擇保存時才會被呼叫；
        include_unpinned=False 就只留釘選的片語。
        The storable form. This is only called when the user opted into saving;
        include_unpinned=False keeps just the pinned phrases.
        """
        source = self.ordered() if include_unpinned else \
            [entry for entry in self.ordered() if entry["pinned"]]
        return [dict(entry) for entry in source]

    def load(self, entries: Any) -> None:
        """從儲存的資料還原。"""
        self.entries = normalize_entries(entries)[: self.limit]
