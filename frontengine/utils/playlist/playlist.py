"""
桌布播放清單：一批媒體檔輪流播放，可隨機、可循環，並能依時段自動換清單
（例如白天一組、晚上一組）。純邏輯、不依賴 Qt，時間由外部提供。

A wallpaper playlist: rotate through a set of media files, optionally shuffled,
and switch sets by time of day (one for daytime, another for the evening). Pure
logic — the clock is passed in.
"""
from __future__ import annotations

import random as _random_module
from pathlib import Path
from typing import List, Optional, Sequence

MEDIA_EXTENSIONS = (".gif", ".webp", ".png", ".jpg", ".jpeg", ".bmp", ".mp4", ".webm", ".avi")
MIN_INTERVAL_SECONDS = 5
DEFAULT_INTERVAL_SECONDS = 300


def clamp_interval(value, fallback: int = DEFAULT_INTERVAL_SECONDS) -> int:
    """把換圖間隔夾在 5 秒以上（更短只是在閃）。"""
    try:
        return max(MIN_INTERVAL_SECONDS, int(value))
    except (TypeError, ValueError):
        return fallback


def collect_media(folder: str, recursive: bool = False) -> List[str]:
    """
    掃描資料夾裡可用的媒體檔（依檔名排序）；不是資料夾就回傳空清單。
    Media files in a folder, sorted by name; [] when it is not a folder.
    """
    try:
        base = Path(folder)
        if not base.is_dir():
            return []
        paths = base.rglob("*") if recursive else base.iterdir()
        return sorted(
            str(path) for path in paths
            if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS
        )
    except OSError:
        return []


def in_window(hour: int, start_hour: int, end_hour: int) -> bool:
    """
    判斷 hour 是否落在 [start, end) 的時段內，支援跨午夜（例如 20 點到 6 點）。
    Whether `hour` falls in [start, end), wrapping across midnight.
    """
    hour = int(hour) % 24
    start = int(start_hour) % 24
    end = int(end_hour) % 24
    if start == end:
        return True
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


class Playlist:
    """
    播放清單：next() 取下一個項目，支援循環與隨機（隨機時一輪內不重複）。
    """

    def __init__(self, items: Sequence[str] = (), shuffle: bool = False,
                 interval_seconds: int = DEFAULT_INTERVAL_SECONDS, rng=None) -> None:
        self.items: List[str] = [str(item) for item in items if str(item).strip()]
        self.shuffle = bool(shuffle)
        self.interval_seconds = clamp_interval(interval_seconds)
        self._rng = rng if rng is not None else _random_module.Random()
        self._order: List[int] = []
        self._position = -1

    def __len__(self) -> int:
        return len(self.items)

    def set_items(self, items: Sequence[str]) -> None:
        """換一批項目並重新開始。"""
        self.items = [str(item) for item in items if str(item).strip()]
        self.reset()

    def reset(self) -> None:
        """回到清單開頭（隨機模式會重新洗牌）。"""
        self._order = []
        self._position = -1

    def _rebuild_order(self) -> None:
        self._order = list(range(len(self.items)))
        if self.shuffle:
            self._rng.shuffle(self._order)

    def current(self) -> Optional[str]:
        """目前的項目；還沒開始或清單為空時回傳 None。"""
        if not self.items or self._position < 0 or not self._order:
            return None
        return self.items[self._order[self._position % len(self._order)]]

    def next(self) -> Optional[str]:
        """
        取下一個項目；走到底會重新開始（隨機模式重新洗牌）。清單空時回傳 None。
        The next item, wrapping at the end (reshuffling when shuffled).
        """
        if not self.items:
            return None
        if not self._order or self._position + 1 >= len(self._order):
            self._rebuild_order()
            self._position = 0
        else:
            self._position += 1
        return self.current()


class ScheduledPlaylists:
    """
    依時段挑選播放清單：每個項目是 (起始小時, 結束小時, Playlist)，
    找不到符合的時段就用預設清單。
    """

    def __init__(self, default: Optional[Playlist] = None) -> None:
        self.default = default
        self.windows: List[tuple] = []

    def add_window(self, start_hour: int, end_hour: int, playlist: Playlist) -> None:
        """新增一個時段清單。"""
        self.windows.append((int(start_hour) % 24, int(end_hour) % 24, playlist))

    def playlist_for(self, hour: int) -> Optional[Playlist]:
        """回傳該小時應使用的清單。"""
        for start, end, playlist in self.windows:
            if in_window(hour, start, end):
                return playlist
        return self.default
