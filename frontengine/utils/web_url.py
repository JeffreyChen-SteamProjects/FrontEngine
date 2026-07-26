from __future__ import annotations

from typing import Optional
from urllib.parse import parse_qs, urlparse


# YouTube 影片 ID 會出現在路徑裡的這幾種前綴之後
# The path prefixes a YouTube video id can follow.
_YOUTUBE_PATH_PREFIXES = ("/embed/", "/shorts/", "/v/")
_YOUTUBE_HOSTS = ("youtube.com", "music.youtube.com")


def _bare_host(netloc: Optional[str]) -> str:
    """去掉 www. / m. 這類前綴後的主機名稱（小寫）。"""
    host = (netloc or "").lower()
    for prefix in ("www.", "m."):
        if host.startswith(prefix):
            return host[len(prefix):]
    return host


def _first_path_segment(path: str, after: str = "") -> Optional[str]:
    """取出路徑（去掉 after 前綴後）的第一段；空的回傳 None。"""
    remainder = path[len(after):] if after else path.lstrip("/")
    segment = remainder.split("/")[0]
    return segment or None


def _youtube_video_id(url: str) -> Optional[str]:
    """從常見的 YouTube 連結取出影片 ID，非 YouTube 連結回傳 None。"""
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    host = _bare_host(parsed.netloc)
    if host == "youtu.be":
        return _first_path_segment(parsed.path)
    if host not in _YOUTUBE_HOSTS:
        return None
    if parsed.path == "/watch":
        values = parse_qs(parsed.query).get("v")
        return values[0] if values else None
    for prefix in _YOUTUBE_PATH_PREFIXES:
        if parsed.path.startswith(prefix):
            return _first_path_segment(parsed.path, prefix)
    return None


def parse_dashboard_urls(text: str) -> list:
    """
    把多行文字拆成儀表板網址清單：一行一個，忽略空行與 `#` 開頭的註解。
    Split multi-line text into dashboard URLs — one per line, ignoring blank
    lines and `#` comments.
    """
    if not isinstance(text, str):
        return []
    urls = []
    for line in text.splitlines():
        candidate = line.strip()
        if candidate and not candidate.startswith("#"):
            urls.append(candidate)
    return urls


def next_page_index(current: int, count: int, step: int = 1) -> int:
    """回傳下一頁索引（循環）；沒有頁面時回傳 0。"""
    if count <= 0:
        return 0
    try:
        return (int(current) + int(step)) % count
    except (TypeError, ValueError):
        return 0


def normalize_web_url(url: str) -> str:
    """
    將 YouTube 觀看連結轉為可自動播放、循環的內嵌網址，方便當成覆蓋層播放；
    其他網址原樣回傳。
    Convert a YouTube watch/short/youtu.be link into an autoplay+loop embed
    URL so it plays cleanly as an overlay. Any other URL is returned as-is.
    """
    if not isinstance(url, str):
        return url
    stripped = url.strip()
    if not stripped:
        return stripped
    video_id = _youtube_video_id(stripped)
    if video_id:
        return (
            f"https://www.youtube.com/embed/{video_id}"
            f"?autoplay=1&mute=1&loop=1&playlist={video_id}"
        )
    return stripped
