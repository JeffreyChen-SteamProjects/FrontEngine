"""Draws one home zone from world state; clicks are reported, never applied here.

The view reads the world and emits what was clicked. It never changes wallets,
tasks or furniture, so the same drawing can serve the overview page and,
later, the transparent desktop strip without either one computing rewards.
"""
from __future__ import annotations

import zlib

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.pet_game.catalog import CELL_PIXELS
from frontengine.utils.pet_game.world import World

# Footprint heights in cells, so a bed reads lower than a desk at a glance.
HEIGHTS = {"bed": 1.3, "table": 1.6, "workstation": 1.9, "leisure": 1.4, "decoration": 1.5}
COLORS = {"bed": "#7c9fd6", "table": "#c99a63", "workstation": "#8fb67a", "leisure": "#d58fb8",
          "decoration": "#6fbfb3"}
FLOOR_HEIGHT = 16
MIN_CELL = 20.0          # below this, furniture labels stop being readable
MAX_CELL = 40.0
GLYPHS = {"sleep": "Zz", "nap": "Zz", "eat": "~", "snack": "~", "work": "✎", "play": "♪",
          "relax": "☕", "wait": "…", "wander": "", "idle": "", "drag": "✋"}


def resident_color(identifier: str) -> QColor:
    """A stable, readable hue per identity."""
    return QColor.fromHsv(zlib.crc32(identifier.encode("ascii")) % 360, 120, 225)


class HomeView(QWidget):
    """Overview drawing. Subclasses change the backdrop and where residents appear."""

    caption_backdrop = False      # a dark plate behind names, for drawing over any desktop
    resident_selected = Signal(str)
    furniture_selected = Signal(str)
    cell_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.world: World | None = None
        self.zone: str | None = None
        self.selected: str | None = None
        self.preview: tuple[str, int, bool, str | None] | None = None
        self.setFixedHeight(170)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setAccessibleName(translate("pet_home_view", "Home view"))

    def set_world(self, world: World | None, zone: str | None) -> None:
        """A wide zone keeps readable cells and scrolls instead of shrinking."""
        self.world, self.zone = world, zone
        cells = world.zones[zone].width_cells if world is not None and zone in world.zones else 0
        self.setMinimumWidth(int(cells * MIN_CELL) + 2)
        self.update()

    def set_selected(self, identifier: str | None) -> None:
        self.selected = identifier
        self.update()

    def set_preview(self, preview: tuple[str, int, bool, str | None] | None) -> None:
        """(definition, cell, flipped, problem) of a placement being chosen, or None."""
        self.preview = preview
        self.update()

    def cell_width(self) -> float:
        if self.world is None or self.zone not in self.world.zones:
            return MIN_CELL
        cells = self.world.zones[self.zone].width_cells
        return max(MIN_CELL, min(MAX_CELL, (self.width() - 2) / cells))

    def _floor_y(self) -> float:
        return self.height() - FLOOR_HEIGHT - 4

    # ----- painting ---------------------------------------------------------------

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.world is None or self.zone not in self.world.zones:
            painter.fillRect(self.rect(), self.palette().base())
            painter.end()
            return
        self.paint_backdrop(painter)
        for piece, definition in self.world.in_zone(self.zone):
            self._paint_piece(painter, piece, definition)
        if self.preview is not None:
            self._paint_preview(painter)
        for resident in self.world.residents.values():
            if resident.zone == self.zone:
                self._paint_resident(painter, resident)
        painter.end()

    def paint_backdrop(self, painter: QPainter) -> None:
        """The overview fills its background and always shows the floor."""
        painter.fillRect(self.rect(), self.palette().base())
        self._paint_floor(painter)

    def _paint_floor(self, painter: QPainter) -> None:
        zone = self.world.zones[self.zone]
        width = self.cell_width()
        floor = QRectF(0, self._floor_y(), width * zone.width_cells, FLOOR_HEIGHT)
        painter.fillRect(floor, QColor(150, 120, 90, 150))
        for cell in zone.restricted:
            painter.fillRect(QRectF(cell * width, floor.top(), width, FLOOR_HEIGHT),
                             QColor(200, 70, 70, 120))
        door = QRectF(zone.entrance * width, self._floor_y() - width * 2, width, width * 2)
        painter.setPen(QPen(self.palette().text().color(), 1, Qt.PenStyle.DashLine))
        painter.drawRect(door)
        if self.preview is not None:
            painter.setPen(QPen(self.palette().mid().color(), 1))
            for cell in range(zone.width_cells + 1):
                painter.drawLine(QPointF(cell * width, floor.top()), QPointF(cell * width, floor.bottom()))

    def piece_rect(self, piece, definition) -> QRectF:
        width = self.cell_width()
        height = min(self._floor_y() - 24, HEIGHTS[definition.category] * width)
        return QRectF(piece.cell * width, self._floor_y() - height, definition.width * width, height)

    def _paint_piece(self, painter: QPainter, piece, definition) -> None:
        rect = self.piece_rect(piece, definition)
        color = QColor(COLORS[definition.category])
        if not definition.solid:
            color.setAlpha(170)
        painter.setPen(QPen(self.palette().highlight().color(), 3) if piece.identifier == self.selected
                       else QPen(color.darker(140), 1))
        painter.setBrush(color)
        painter.drawRoundedRect(rect, 4, 4)
        painter.setPen(QColor("#1d1d1d"))
        font = QFont(self.font())
        font.setPointSizeF(max(7.5, min(10.0, self.cell_width() / 2.5)))
        painter.setFont(font)
        label = painter.fontMetrics().elidedText(translate(definition.label_key, definition.fallback),
                                                 Qt.TextElideMode.ElideRight, int(rect.width()) - 4)
        painter.drawText(rect.adjusted(2, 2, -2, -2), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, label)
        if piece.owner is not None and piece.owner in self.world.residents:
            painter.setBrush(resident_color(piece.owner))
            painter.drawEllipse(QRectF(rect.right() - 9, rect.top() + 3, 6, 6))

    def _paint_preview(self, painter: QPainter) -> None:
        definition_id, cell, _flipped, problem = self.preview
        definition = self.world.catalog.furniture.get(definition_id)
        if definition is None:
            return
        width = self.cell_width()
        height = min(self._floor_y() - 24, HEIGHTS[definition.category] * width)
        rect = QRectF(cell * width, self._floor_y() - height, definition.width * width, height)
        color = QColor(70, 170, 90, 110) if problem is None else QColor(210, 60, 60, 120)
        painter.setPen(QPen(color.darker(150), 2, Qt.PenStyle.DashLine))
        painter.setBrush(color)
        painter.drawRect(rect)
        if problem is not None:
            painter.setPen(self.palette().text().color())
            painter.drawText(QRectF(rect.left() - 60, 2, rect.width() + 120, 18), Qt.AlignmentFlag.AlignCenter,
                             translate("pet_home_problem_" + problem, problem))

    def resident_x_milli(self, resident) -> float:
        """Where to draw a resident; the desktop strip interpolates between world steps."""
        return resident.x_milli

    def resident_center(self, resident) -> QPointF:
        width = self.cell_width()
        x = self.resident_x_milli(resident) / 1000 / CELL_PIXELS * width
        return QPointF(x, self._floor_y() - max(8.0, width * 0.55))

    def _paint_resident(self, painter: QPainter, resident) -> None:
        center = self.resident_center(resident)
        radius = self.resident_radius()
        color = resident_color(resident.identifier)
        if resident.away or resident.parked:
            color.setAlpha(90)
        painter.setPen(QPen(self.palette().highlight().color(), 3) if resident.identifier == self.selected
                       else QPen(color.darker(160), 1))
        painter.setBrush(color)
        painter.drawEllipse(center, radius, radius)
        kind = resident.activity.kind if resident.activity is not None else "idle"
        caption = resident.name + (" " + GLYPHS.get(kind, "") if GLYPHS.get(kind) else "")
        box = self.caption_rect(resident)
        if self.caption_backdrop:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 150))
            plate = painter.fontMetrics().horizontalAdvance(caption) + 10
            painter.drawRoundedRect(QRectF(center.x() - plate / 2, box.top(), plate, box.height()), 5, 5)
            painter.setPen(QColor("white"))
        else:
            painter.setPen(self.palette().text().color())
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, caption)

    def resident_radius(self) -> float:
        return max(7.0, self.cell_width() * 0.5)

    def caption_rect(self, resident) -> QRectF:
        center = self.resident_center(resident)
        return QRectF(center.x() - 70, center.y() - self.resident_radius() - 20, 140, 18)

    # ----- input -----------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.world is None or self.zone not in self.world.zones or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        point = event.position()
        radius = max(7.0, self.cell_width() * 0.5) + 3
        for resident in sorted(self.world.residents.values(), key=lambda item: item.identifier):
            if resident.zone == self.zone:
                center = self.resident_center(resident)
                if (center - point).manhattanLength() <= radius * 1.4:
                    self.resident_selected.emit(resident.identifier)
                    return
        if self.preview is None:
            for piece, definition in self.world.in_zone(self.zone):
                if self.piece_rect(piece, definition).contains(point):
                    self.furniture_selected.emit(piece.identifier)
                    return
        cell = int(point.x() // self.cell_width())
        if 0 <= cell < self.world.zones[self.zone].width_cells:
            self.cell_clicked.emit(cell)
