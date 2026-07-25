"""
專注輔助的純邏輯：
  - 前景視窗以外的區域要壓暗哪些矩形（背景變暗）
  - 依比例把螢幕的某個邊緣算成要遮蔽的區域（遮住工作列／通知角落）
兩者都只做幾何計算，不碰 Qt，方便測試。

Pure geometry for the focus tools: which rectangles to dim around the active
window, and which strip of a screen to cover when masking a distraction (the
taskbar, a notification corner). No Qt here — just maths.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

Rect = Tuple[int, int, int, int]  # (x, y, width, height)

# 可遮蔽的螢幕區域 / Regions of a screen that can be masked
REGION_BOTTOM = "bottom"
REGION_TOP = "top"
REGION_LEFT = "left"
REGION_RIGHT = "right"
REGION_BOTTOM_RIGHT = "bottom_right"
REGION_FULL = "full"
REGIONS = (REGION_BOTTOM, REGION_TOP, REGION_LEFT, REGION_RIGHT, REGION_BOTTOM_RIGHT, REGION_FULL)

DEFAULT_MASK_PERCENT = 6


def clamp_percent(value, fallback: int = DEFAULT_MASK_PERCENT) -> int:
    """把比例夾在 1~100（0 等於沒遮，超過 100 沒有意義）。"""
    try:
        return max(1, min(100, int(value)))
    except (TypeError, ValueError):
        return fallback


def intersects(first: Rect, second: Rect) -> bool:
    """兩個矩形是否重疊。"""
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


def surrounding_rects(screen: Rect, active: Optional[Rect]) -> List[Rect]:
    """
    回傳「螢幕扣掉作用中視窗」後要壓暗的矩形（上、下、左、右四塊）。
    沒有作用中視窗或它不在這個螢幕上時，整個螢幕都壓暗。

    The rectangles to dim once the active window is cut out of the screen (top,
    bottom, left, right). With no active window on this screen, dim all of it.
    """
    sx, sy, sw, sh = screen
    if active is None or not intersects(screen, active):
        return [(sx, sy, sw, sh)]
    ax, ay, aw, ah = active
    # 把作用中視窗裁到螢幕範圍內 / Clip the window to the screen
    left = max(sx, ax)
    top = max(sy, ay)
    right = min(sx + sw, ax + aw)
    bottom = min(sy + sh, ay + ah)
    rects: List[Rect] = []
    if top > sy:
        rects.append((sx, sy, sw, top - sy))
    if bottom < sy + sh:
        rects.append((sx, bottom, sw, sy + sh - bottom))
    if left > sx:
        rects.append((sx, top, left - sx, bottom - top))
    if right < sx + sw:
        rects.append((right, top, sx + sw - right, bottom - top))
    return [rect for rect in rects if rect[2] > 0 and rect[3] > 0]


def mask_rect(screen: Rect, region: str, percent: int = DEFAULT_MASK_PERCENT) -> Rect:
    """
    依區域與比例算出要遮蔽的矩形（例如「底部 6%」正好蓋住工作列）。
    The rectangle to cover for a region and percentage — "bottom 6%" is about
    the height of a taskbar.
    """
    sx, sy, sw, sh = screen
    share = clamp_percent(percent)
    height = max(1, int(sh * share / 100))
    width = max(1, int(sw * share / 100))
    if region == REGION_FULL:
        return (sx, sy, sw, sh)
    if region == REGION_TOP:
        return (sx, sy, sw, height)
    if region == REGION_LEFT:
        return (sx, sy, width, sh)
    if region == REGION_RIGHT:
        return (sx + sw - width, sy, width, sh)
    if region == REGION_BOTTOM_RIGHT:
        return (sx + sw - max(width, sw // 4), sy + sh - height, max(width, sw // 4), height)
    return (sx, sy + sh - height, sw, height)  # bottom is the default
