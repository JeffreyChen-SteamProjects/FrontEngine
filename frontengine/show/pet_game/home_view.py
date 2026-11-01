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

from frontengine.show.pet_game.furniture_art import SURFACES, aspect, picture
from frontengine.show.pet_game.themes import floor_color, paint_sky
from frontengine.utils.pet_game.environment import daylight
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
SPRITE_CELLS = 2.2           # a character stands a little over two cells tall
ZOOMS = (1.0, 1.25, 1.5, 2.0)
AREA_COLORS = {"living": "#B8C7E6", "work": "#C9D9A5", "leisure": "#F2C6A8", "dining": "#F1DD9A",
               "clear": "#D8D2C6"}
GLYPHS = {"sleep": "Zz", "nap": "Zz", "eat": "~", "snack": "~", "work": "✎", "play": "♪",
          "relax": "☕", "wait": "…", "wander": "", "visit": "", "help": "🤝", "idle": "", "drag": "✋"}


def resident_color(identifier: str) -> QColor:
    """A stable, readable hue per identity."""
    return QColor.fromHsv(zlib.crc32(identifier.encode("ascii")) % 360, 120, 225)


class HomeView(QWidget):
    """Overview drawing. Subclasses change the backdrop and where residents appear."""

    caption_backdrop = False      # a dark plate behind names, for drawing over any desktop
    art = None                    # ResidentArt; without it residents are drawn as markers
    reduced_motion = False        # no in-between movement and no moving rain
    zoom = 1.0                    # cell size multiplier (ZOOMS); the desktop strip stays at 1
    zoomable = False              # Ctrl+wheel zooms only where the page allows it
    zoom_changed = Signal(float)
    drag_enabled = False          # while arranging, pieces can be dragged to a new cell
    area_tool: str | None = None  # an area tag (or "clear") while painting floor areas
    area_painted = Signal(int, int)
    piece_hovered = Signal(str, int)
    piece_dropped = Signal(str, int)
    resident_selected = Signal(str)
    furniture_selected = Signal(str)
    cell_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.world: World | None = None
        self.zone: str | None = None
        self.selected: str | None = None
        self.preview: tuple[str, int, bool, str | None] | None = None
        self._painting: tuple[int, int] | None = None
        self.setFixedHeight(170)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setAccessibleName(translate("pet_home_view", "Home view"))

    def set_world(self, world: World | None, zone: str | None) -> None:
        """A wide zone keeps readable cells and scrolls instead of shrinking."""
        self.world, self.zone = world, zone
        self._fit_width()
        self.update()

    def _fit_width(self) -> None:
        cells = self.world.zones[self.zone].width_cells if self.world is not None and self.zone in self.world.zones else 0
        self.setMinimumWidth(int(cells * MIN_CELL * self.zoom) + 2)

    def set_zoom(self, zoom: float) -> float:
        """Make cells (and everything on them) bigger; the overview then scrolls sideways."""
        self.zoom = min(ZOOMS[-1], max(ZOOMS[0], zoom))
        self._fit_width()
        self.update()
        self.zoom_changed.emit(self.zoom)
        return self.zoom

    def step_zoom(self, steps: int) -> float:
        index = min(range(len(ZOOMS)), key=lambda i: abs(ZOOMS[i] - self.zoom))
        return self.set_zoom(ZOOMS[max(0, min(len(ZOOMS) - 1, index + steps))])

    def wheelEvent(self, event) -> None:
        """Ctrl+wheel zooms; a plain wheel still scrolls the page."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and self.zoomable:
            self.step_zoom(1 if event.angleDelta().y() > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)

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
        return max(MIN_CELL * self.zoom, min(MAX_CELL * self.zoom, (self.width() - 2) / cells))

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
        """The overview shows the zone's theme, the time of day and the weather, then the floor."""
        zone = self.world.zones[self.zone]
        paint_sky(painter, QRectF(self.rect()), zone.theme, self.world.home, self.world.time_ms,
                  not self.reduced_motion)
        self._paint_floor(painter)

    def _paint_floor(self, painter: QPainter) -> None:
        zone = self.world.zones[self.zone]
        width = self.cell_width()
        floor = QRectF(0, self._floor_y(), width * zone.width_cells, FLOOR_HEIGHT)
        painter.fillRect(floor, floor_color(zone.theme))
        self._paint_areas(painter, floor)
        for cell in zone.restricted:
            painter.fillRect(QRectF(cell * width, floor.top(), width, FLOOR_HEIGHT),
                             QColor(200, 70, 70, 120))
        door = QRectF(zone.entrance * width, self._floor_y() - width * 2, width, width * 2)
        linked = self.world.crossing(self.zone) is not None
        painter.setPen(QPen(self.ink(), 2 if linked else 1, Qt.PenStyle.SolidLine if linked else Qt.PenStyle.DashLine))
        painter.drawRect(door)
        if linked:                    # a crossing point: pets may walk through to the linked zone
            painter.drawText(door, Qt.AlignmentFlag.AlignCenter, "⇄")
        if self.preview is not None:
            painter.setPen(QPen(self.palette().mid().color(), 1))
            for cell in range(zone.width_cells + 1):
                painter.drawLine(QPointF(cell * width, floor.top()), QPointF(cell * width, floor.bottom()))

    def _paint_areas(self, painter: QPainter, floor: QRectF) -> None:
        """Labelled stretches of floor: a coloured band with the label, and the one being painted."""
        zone, width = self.world.zones[self.zone], self.cell_width()
        bands = list(zone.areas)
        if self._painting is not None:
            first, last = sorted(self._painting)
            bands.append((first, last, self.area_tool))
        font = QFont(self.font())
        font.setPointSizeF(7.5)
        painter.setFont(font)
        for first, last, tag in bands:
            color = QColor(AREA_COLORS.get(tag, "#9A9284"))
            color.setAlpha(150)
            band = QRectF(first * width, floor.top(), (last - first + 1) * width, FLOOR_HEIGHT)
            painter.fillRect(band, color)
            painter.setPen(QColor("#171715"))
            painter.drawText(band, Qt.AlignmentFlag.AlignCenter, translate("pet_home_area_" + tag, tag))

    def _theme(self) -> str:
        return self.world.zones[self.zone].theme

    def piece_rect(self, piece, definition) -> QRectF:
        return self.footprint_rect(piece.cell, definition)

    def footprint_rect(self, cell: int, definition) -> QRectF:
        """The footprint's width; the picture's own height when there is one, else a height per category."""
        width = self.cell_width()
        ratio = aspect(self._theme(), definition.identifier)
        height = definition.width * width * ratio if ratio is not None else HEIGHTS[definition.category] * width
        height = min(self._floor_y() - 24, height)
        return QRectF(cell * width, self._floor_y() - height, definition.width * width, height)

    def _paint_piece(self, painter: QPainter, piece, definition) -> None:
        rect = self.piece_rect(piece, definition)
        image = picture(self._theme(), definition.identifier)
        if image is not None:
            painter.save()
            if piece.flipped:                          # mirrored about the piece's own centre
                painter.translate(rect.center().x() * 2, 0)
                painter.scale(-1, 1)
            painter.drawImage(rect, image)
            painter.restore()
        else:
            self._paint_block(painter, rect, definition)
        if piece.identifier == self.selected:
            painter.setPen(QPen(self.palette().highlight().color(), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 5, 5)
        if image is None or piece.identifier == self.selected or self.preview is not None:
            self._paint_label(painter, rect, definition, below=image is not None)
        if piece.owner is not None and piece.owner in self.world.residents:
            painter.setPen(QPen(QColor("#1d1d1d"), 1))
            painter.setBrush(resident_color(piece.owner))
            painter.drawEllipse(QRectF(rect.right() - 10, rect.top() + 3, 7, 7))

    def _paint_block(self, painter: QPainter, rect: QRectF, definition) -> None:
        """Pieces without a picture: a block in the category's colour."""
        color = QColor(COLORS[definition.category])
        if not definition.solid:
            color.setAlpha(170)
        painter.setPen(QPen(color.darker(140), 1))
        painter.setBrush(color)
        painter.drawRoundedRect(rect, 4, 4)

    def _paint_label(self, painter: QPainter, rect: QRectF, definition, below: bool) -> None:
        font = QFont(self.font())
        font.setPointSizeF(max(7.5, min(10.0, self.cell_width() / 2.5)))
        painter.setFont(font)
        label = painter.fontMetrics().elidedText(translate(definition.label_key, definition.fallback),
                                                 Qt.TextElideMode.ElideRight, int(rect.width()) - 4)
        if below:                                      # on a plate over the picture's lower edge
            plate = QRectF(rect.left(), rect.bottom() - 18, rect.width(), 16)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 200))
            painter.drawRoundedRect(plate, 4, 4)
            painter.setPen(QColor("#1d1d1d"))
            painter.drawText(plate, Qt.AlignmentFlag.AlignCenter, label)
            return
        painter.setPen(QColor("#1d1d1d"))
        painter.drawText(rect.adjusted(2, 2, -2, -2), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, label)

    def _paint_preview(self, painter: QPainter) -> None:
        definition_id, cell, _flipped, problem = self.preview
        definition = self.world.catalog.furniture.get(definition_id)
        if definition is None:
            return
        rect = self.footprint_rect(cell, definition)
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

    def _sprite_size(self, resident) -> tuple[float, float] | None:
        """Width and height of the resident's character on screen, or None when drawn as a marker."""
        renderer = self.art.renderer(resident.identifier) if self.art is not None else None
        if renderer is None:
            return None
        canvas_width, canvas_height = renderer.character.canvas
        height = self.cell_width() * SPRITE_CELLS
        return canvas_width * height / canvas_height, height

    def resident_box(self, resident) -> QRectF:
        """Where the resident is drawn and clicked: its character standing on the floor, or the marker."""
        width = self.cell_width()
        x = self.resident_x_milli(resident) / 1000 / CELL_PIXELS * width
        size = self._sprite_size(resident)
        if size is not None:
            floor = self._floor_y() - self._rest_height(resident)
            return QRectF(x - size[0] / 2, floor - size[1], size[0], size[1])
        radius = self.resident_radius()
        center_y = self._floor_y() - max(8.0, width * 0.55)
        return QRectF(x - radius, center_y - radius, radius * 2, radius * 2)

    def _rest_height(self, resident) -> float:
        """How far above the floor a resident using a bed or armchair rests (its surface in the picture)."""
        activity = resident.activity
        if activity is None or activity.phase != "using" or activity.furniture is None:
            return 0.0
        piece = self.world.furniture.get(activity.furniture)
        surface = SURFACES.get(piece.definition) if piece is not None else None
        if surface is None or picture(self._theme(), piece.definition) is None:
            return 0.0
        return self.piece_rect(piece, self.world.definition(piece)).height() * surface

    def resident_center(self, resident) -> QPointF:
        return self.resident_box(resident).center()

    def _paint_body(self, painter: QPainter, resident) -> None:
        frame = self.art.frame(resident, still=self.reduced_motion) if self.art is not None else None
        box = self.resident_box(resident)
        if frame is not None and self._sprite_size(resident) is not None:
            painter.setOpacity(0.4 if resident.away or resident.parked else 1.0)
            painter.drawImage(box, frame)
            painter.setOpacity(1.0)
            if resident.identifier == self.selected:
                painter.setPen(QPen(self.palette().highlight().color(), 2, Qt.PenStyle.DashLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(box, 6, 6)
            return
        color = resident_color(resident.identifier)
        if resident.away or resident.parked:
            color.setAlpha(90)
        painter.setPen(QPen(self.palette().highlight().color(), 3) if resident.identifier == self.selected
                       else QPen(color.darker(160), 1))
        painter.setBrush(color)
        painter.drawEllipse(box)

    def _paint_resident(self, painter: QPainter, resident) -> None:
        center = self.resident_center(resident)
        self._paint_body(painter, resident)
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
            painter.setPen(self.ink())
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, caption)

    def ink(self) -> QColor:
        """Text colour that stays readable on the sky: light at night, the palette's by day."""
        if self.world is not None and daylight(self.world.time_ms) < 0.45:
            return QColor(240, 240, 250)
        return self.palette().text().color()

    def resident_radius(self) -> float:
        return max(7.0, self.cell_width() * 0.5)

    def caption_rect(self, resident) -> QRectF:
        box = self.resident_box(resident)
        return QRectF(box.center().x() - 70, box.top() - 20, 140, 18)

    # ----- input -----------------------------------------------------------------------

    def _drag_cell(self, event: QMouseEvent) -> int:
        _identifier, grab = self._dragging
        return max(0, int(round((event.position().x() - grab) / self.cell_width())))

    def _floor_cell(self, x: float) -> int:
        cells = self.world.zones[self.zone].width_cells
        return max(0, min(cells - 1, int(x // self.cell_width())))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._painting is not None:
            self._painting = (self._painting[0], self._floor_cell(event.position().x()))
            self.update()
            return
        if getattr(self, "_dragging", None) is not None:
            self.piece_hovered.emit(self._dragging[0], self._drag_cell(event))
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._painting is not None:
            first, last = sorted(self._painting)
            self._painting = None
            self.update()
            self.area_painted.emit(first, last)
            return
        if getattr(self, "_dragging", None) is not None:
            identifier, cell = self._dragging[0], self._drag_cell(event)
            self._dragging = None
            self.piece_dropped.emit(identifier, cell)
            return
        super().mouseReleaseEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.world is None or self.zone not in self.world.zones or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        point = event.position()
        if self.area_tool is not None:
            cell = self._floor_cell(point.x())
            self._painting = (cell, cell)
            self.update()
            return
        if self.drag_enabled:
            for piece, definition in self.world.in_zone(self.zone):
                if self.piece_rect(piece, definition).contains(point):
                    self._dragging = (piece.identifier, point.x() - self.piece_rect(piece, definition).left())
                    self.furniture_selected.emit(piece.identifier)
                    return
        for resident in sorted(self.world.residents.values(), key=lambda item: item.identifier):
            if resident.zone == self.zone:
                if self.resident_box(resident).adjusted(-3, -3, 3, 3).contains(point):
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
