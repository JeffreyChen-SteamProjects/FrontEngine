"""
螢幕量測的純計算：色碼格式、兩點距離、三點夾角。不依賴 Qt，方便測試。

The maths behind the on-screen measuring tools: colour formats, the distance
between two points, and the angle at a corner. Qt-free, so it is easy to test.
"""
from __future__ import annotations

import math
from typing import Sequence, Tuple

FORMAT_HEX = "hex"
FORMAT_RGB = "rgb"
FORMAT_HSL = "hsl"
FORMAT_CSS_VAR = "css"
COLOR_FORMATS = (FORMAT_HEX, FORMAT_RGB, FORMAT_HSL, FORMAT_CSS_VAR)


def clamp_channel(value) -> int:
    """把單一色版夾在 0~255。"""
    try:
        return max(0, min(255, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def to_hex(rgb: Sequence[int]) -> str:
    """(r, g, b) -> #rrggbb（小寫）。"""
    red, green, blue = (clamp_channel(part) for part in _as_rgb(rgb))
    return f"#{red:02x}{green:02x}{blue:02x}"


def to_hsl(rgb: Sequence[int]) -> Tuple[int, int, int]:
    """(r, g, b) -> (色相 0~359, 飽和度 %, 亮度 %)。"""
    red, green, blue = (clamp_channel(part) / 255.0 for part in _as_rgb(rgb))
    highest, lowest = max(red, green, blue), min(red, green, blue)
    lightness = (highest + lowest) / 2.0
    if highest == lowest:
        return (0, 0, int(round(lightness * 100)))
    delta = highest - lowest
    saturation = delta / (2.0 - highest - lowest if lightness > 0.5 else highest + lowest)
    if highest == red:
        hue = ((green - blue) / delta) % 6
    elif highest == green:
        hue = (blue - red) / delta + 2
    else:
        hue = (red - green) / delta + 4
    return (int(round(hue * 60)) % 360, int(round(saturation * 100)),
            int(round(lightness * 100)))


def format_color(rgb: Sequence[int], color_format: str = FORMAT_HEX) -> str:
    """
    依指定格式輸出色碼，方便直接貼進程式碼。不認得的格式退回十六進位。
    The colour in the requested notation, ready to paste into code. An unknown
    format falls back to hex.
    """
    name = str(color_format or "").strip().lower()
    red, green, blue = (clamp_channel(part) for part in _as_rgb(rgb))
    if name == FORMAT_RGB:
        return f"rgb({red}, {green}, {blue})"
    if name == FORMAT_HSL:
        hue, saturation, lightness = to_hsl((red, green, blue))
        return f"hsl({hue}, {saturation}%, {lightness}%)"
    if name == FORMAT_CSS_VAR:
        return f"--color: {to_hex((red, green, blue))};"
    return to_hex((red, green, blue))


def distance(start: Sequence[float], end: Sequence[float]) -> float:
    """兩點之間的直線距離（像素）。"""
    (start_x, start_y), (end_x, end_y) = _as_point(start), _as_point(end)
    return math.hypot(end_x - start_x, end_y - start_y)


def measurement_text(start: Sequence[float], end: Sequence[float]) -> str:
    """量測結果的一行說明：寬、高、對角線長度。"""
    (start_x, start_y), (end_x, end_y) = _as_point(start), _as_point(end)
    width = abs(end_x - start_x)
    height = abs(end_y - start_y)
    return f"{width:.0f} x {height:.0f} px  ({distance(start, end):.1f} px)"


def angle_at(vertex: Sequence[float], first: Sequence[float], second: Sequence[float]) -> float:
    """
    以 vertex 為頂點、兩條邊分別指向 first 與 second 的夾角（0~180 度）。
    任一邊長度為 0（點重疊）時回傳 0。
    The angle at `vertex` between the arms reaching `first` and `second`, in
    degrees. A zero-length arm - two points on top of each other - gives 0.
    """
    (vertex_x, vertex_y) = _as_point(vertex)
    (first_x, first_y), (second_x, second_y) = _as_point(first), _as_point(second)
    one = (first_x - vertex_x, first_y - vertex_y)
    two = (second_x - vertex_x, second_y - vertex_y)
    length_one = math.hypot(*one)
    length_two = math.hypot(*two)
    if length_one == 0 or length_two == 0:
        return 0.0
    cosine = (one[0] * two[0] + one[1] * two[1]) / (length_one * length_two)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def _as_point(point: Sequence[float]) -> Tuple[float, float]:
    """把輸入整理成 (x, y)；缺項補 0。"""
    values = list(point) if point is not None else []
    while len(values) < 2:
        values.append(0)
    return (float(values[0]), float(values[1]))


def _as_rgb(rgb: Sequence[int]) -> Tuple[int, int, int]:
    """把輸入整理成 (r, g, b)；缺項補 0。"""
    values = list(rgb) if rgb is not None else []
    while len(values) < 3:
        values.append(0)
    return (values[0], values[1], values[2])
