from __future__ import annotations

from typing import Optional
from urllib.parse import parse_qs, urlparse


def _youtube_video_id(url: str) -> Optional[str]:
    """從常見的 YouTube 連結取出影片 ID，非 YouTube 連結回傳 None。"""
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    host = (parsed.netloc or "").lower()
    for prefix in ("www.", "m."):
        if host.startswith(prefix):
            host = host[len(prefix):]
    if host == "youtu.be":
        video_id = parsed.path.lstrip("/").split("/")[0]
        return video_id or None
    if host in ("youtube.com", "music.youtube.com"):
        if parsed.path == "/watch":
            values = parse_qs(parsed.query).get("v")
            return values[0] if values else None
        for segment in ("/embed/", "/shorts/", "/v/"):
            if parsed.path.startswith(segment):
                video_id = parsed.path[len(segment):].split("/")[0]
                return video_id or None
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
