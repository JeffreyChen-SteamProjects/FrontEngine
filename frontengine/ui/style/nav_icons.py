"""
Line icons for the sidebar and the shell, drawn as SVG paths in one style.

24 x 24 view box, round 1.8 px strokes, no fill unless a shape needs one. Icons
are rendered in a token colour at run time (``icon(name, color)``), so a theme
change only re-renders them; there are no per-theme image files to keep in step.
"""
from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_STROKE = ('fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"')

# name -> SVG body (paths, circles, rects) using {c} for the colour.
SHAPES = {
    "home": '<path d="M3.5 10.5 12 3.5l8.5 7V20a1 1 0 0 1-1 1H15v-6h-6v6H4.5a1 1 0 0 1-1-1z" S/>',
    "video": '<rect x="3" y="6" width="13" height="12" rx="2" S/><path d="m16 10.5 5-3v9l-5-3" S/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="2" S/><circle cx="9" cy="9.5" r="1.8" S/>'
             '<path d="m3.5 18 5.5-5.5 4 4 2.5-2.5 5 5" S/>',
    "web": '<circle cx="12" cy="12" r="9" S/><path d="M3 12h18M12 3c2.6 2.8 3.8 5.8 3.8 9s-1.2 6.2-3.8 9'
           'M12 3C9.4 5.8 8.2 8.8 8.2 12s1.2 6.2 3.8 9" S/>',
    "gif": '<rect x="3" y="4" width="18" height="16" rx="2" S/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4" S/>',
    "text": '<path d="M5 6V4.5h14V6M12 4.5v15M9 19.5h6" S/>',
    "sound": '<path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z" S/><path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11" S/>',
    "scene": '<path d="m12 3.5 9 4.5-9 4.5-9-4.5z" S/><path d="m3 12 9 4.5 9-4.5M3 16l9 4.5 9-4.5" S/>',
    "particle": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6" S/>',
    "pet": '<circle cx="7" cy="9" r="1.9" S/><circle cx="12" cy="6.5" r="1.9" S/><circle cx="17" cy="9" r="1.9" S/>'
           '<path d="M12 12c-3 0-5.5 3.3-5.5 5.5 0 1.7 1.2 2.5 2.7 2.5 1.2 0 1.7-.6 2.8-.6s1.6.6 2.8.6c1.5 0 2.7-.8 2.7'
           '-2.5C17.5 15.3 15 12 12 12z" S/>',
    "wallpaper": '<rect x="3" y="4" width="18" height="13" rx="2" S/><path d="M8 21h8M12 17v4M6.5 14l3.5-3.5 2.5 2.5'
                 ' 2-2 3 3" S/>',
    "widgets": '<rect x="3.5" y="3.5" width="7" height="7" rx="1.5" S/><rect x="13.5" y="3.5" width="7" height="7" '
               'rx="1.5" S/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5" S/><rect x="13.5" y="13.5" width="7" '
               'height="7" rx="1.5" S/>',
    "focus": '<circle cx="12" cy="12" r="8.5" S/><circle cx="12" cy="12" r="4.5" S/><circle cx="12" cy="12" r="1" S/>',
    "eye": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" S/>'
           '<circle cx="12" cy="12" r="3" S/>',
    "present": '<rect x="3" y="4" width="18" height="12" rx="1.5" S/><path d="M12 16v4M8 20h8M7.5 12l3-3 2 2 4-4" S/>',
    "tools": '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4l-5.8 5.8a1.5 1.5 0 0 0 0 2.1l.9.9a1.5 1.5 0 0 0 2.1 0l5.8-5.8a4 '
             '4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z" S/>',
    "control": '<path d="M5 4v16M12 4v16M19 4v16" S/><circle cx="5" cy="9" r="2" S/><circle cx="12" cy="15" r="2" S/>'
               '<circle cx="19" cy="8" r="2" S/>',
    "extension": '<path d="M9 4.5a2 2 0 1 1 4 0V6h4v4h1.5a2 2 0 1 1 0 4H17v5H6v-4H4.5a2 2 0 1 1 0-4H6V6h3z" S/>',
    "chevron-down": '<path d="m8 10 4 4 4-4" S/>',
    "chevron-right": '<path d="m10 8 4 4-4 4" S/>',
    "search": '<circle cx="11" cy="11" r="6.5" S/><path d="m16 16 4.5 4.5" S/>',
}


def svg(name: str, color: str) -> str:
    body = SHAPES[name].replace(" S/>", f" {_STROKE}/>").replace("{c}", color)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{body}</svg>'


@lru_cache(maxsize=256)
def pixmap(name: str, color: str, size: int = 18, ratio: float = 2.0) -> QPixmap:
    """The icon rendered at ``size`` logical pixels (sharp on high-DPI screens)."""
    renderer = QSvgRenderer(QByteArray(svg(name, color).encode("utf-8")))
    side = max(1, round(size * ratio))
    image = QImage(side, side, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, side, side))
    painter.end()
    result = QPixmap.fromImage(image)
    result.setDevicePixelRatio(ratio)
    return result


def icon(name: str, color: str, active: str | None = None, size: int = 18) -> QIcon:
    """``color`` normally; ``active`` (if given) while the row is selected."""
    result = QIcon()
    result.addPixmap(pixmap(name, color, size), QIcon.Mode.Normal)
    result.addPixmap(pixmap(name, active or color, size), QIcon.Mode.Selected)
    result.addPixmap(pixmap(name, active or color, size), QIcon.Mode.Active)
    return result


ICON_SIZE = QSize(18, 18)
