"""
The one-line instruction a full-screen tool shows while it waits for the mouse.

Without it, pressing "Record an area" only dimmed the screen: nothing said what
to do next or how to get out.
"""
from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter

_PADDING_X, _PADDING_Y, _TOP = 22, 12, 36
_BACKGROUND = QColor(23, 23, 21, 235)
_TEXT = QColor("#FFFDF6")
_ACCENT = QColor("#F56A24")


def hint_rect(painter: QPainter, area: QRect, text: str) -> QRect:
    """Where the banner goes: top centre of ``area``, wrapped to fit it."""
    limit = QRect(0, 0, max(120, area.width() - 80), area.height())
    bounds = painter.boundingRect(limit, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)
    width, height = bounds.width() + 2 * _PADDING_X, bounds.height() + 2 * _PADDING_Y
    return QRect(area.x() + (area.width() - width) // 2, area.y() + _TOP, width, height)


def draw_hint(painter: QPainter, area: QRect, text: str) -> None:
    """Paint the instruction banner; the painter's state is left as it was."""
    if not text:
        return
    painter.save()
    font = QFont(painter.font())
    font.setPointSize(12)
    font.setBold(True)
    painter.setFont(font)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    rect = hint_rect(painter, area, text)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_BACKGROUND)
    painter.drawRoundedRect(QRectF(rect), 12, 12)
    painter.setBrush(_ACCENT)
    painter.drawRoundedRect(QRectF(rect.x() + 8, rect.y() + 10, 4, rect.height() - 20), 2, 2)
    painter.setPen(_TEXT)
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)
    painter.restore()
