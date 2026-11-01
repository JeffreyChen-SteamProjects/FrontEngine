"""The home on the desktop: a transparent strip along the bottom of the work area.

Only residents, furniture and the small home button take the mouse; a window
mask leaves every other pixel of the strip to the windows underneath, so the
home never blocks the desktop. The strip never takes focus or activates.

The world moves in 200 ms steps; the strip draws in between at the quality
tier's frame rate (60 / 30 / 15 FPS) by interpolating resident positions, so
smoothness costs rendering only and never changes what the world computes.
"""
from __future__ import annotations

from time import monotonic
from typing import Callable

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QCloseEvent, QColor, QGuiApplication, QHideEvent, QMouseEvent, QPen, QRegion, QShowEvent,
)
from PySide6.QtWidgets import QMenu, QToolButton, QToolTip

from frontengine.show.pet_game.captions import card_text
from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.home_view import HomeView
from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.pet_game.catalog import CELL_PIXELS
from frontengine.utils.pet_game.simulation import STEP_MS
from frontengine.utils.pet_game.world import COMMANDS
from frontengine.utils.power_mode.power_mode import normalize_tier

STRIP_HEIGHT = 150
FRAME_MS = {"high": 16, "balanced": 33, "saver": 66}
DRAG_START_PX = 6
LAYERS = ("top", "bottom")
HIDDEN_REASON = "hidden"


def strip_flags(layer: str) -> Qt.WindowType:
    stack = Qt.WindowType.WindowStaysOnBottomHint if layer == "bottom" else Qt.WindowType.WindowStaysOnTopHint
    return (Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus | stack)


class HomeStrip(HomeView):
    """One zone drawn on its screen. Hiding it pauses the home; closing it does not."""

    caption_backdrop = True
    open_requested = Signal()
    layer_requested = Signal(str)
    closed = Signal()                      # at close time, before the deferred delete
    overlay_lockable = False              # lock-all must not make the home unclickable
    overlay_remembers_geometry = False

    def __init__(self, service: HomeService, zone: str, layer: str = "top", tier: str = "high",
                 clock: Callable[[], float] = monotonic) -> None:
        super().__init__(None)
        self.service, self._clock = service, clock
        self.layer = layer if layer in LAYERS else "top"
        self.arranging = False
        self._before: dict[str, int] = {}
        self._after: dict[str, int] = {}
        self._stepped_at = clock()
        self._press: tuple[str, QPointF] | None = None
        self._dragging: tuple[str, float] | None = None
        self.setWindowFlags(strip_flags(self.layer))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWindowTitle(translate("tab_pet_home_text", "Pet home"))
        self.setFixedHeight(STRIP_HEIGHT)
        self.button = self._home_button()
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self.update)
        self.set_quality_tier(tier)
        service.ticked.connect(self._stepped)
        self.set_world(service.world, zone)
        self.place_on_screen()
        self._stepped()

    # ----- placement and layer -------------------------------------------------------

    def screen_for_zone(self):
        name = self.service.world.zones[self.zone].screen if self.service.world else ""
        for screen in QGuiApplication.screens():
            if screen.name() == name:
                return screen
        return QGuiApplication.primaryScreen()

    def place_on_screen(self) -> None:
        """Sit on the bottom edge of the zone's screen work area, above the taskbar."""
        area = self.screen_for_zone().availableGeometry()
        width = min(area.width(), self.world.zones[self.zone].width_pixels + 2)
        self.setFixedWidth(width)
        self.move(area.left(), area.bottom() - STRIP_HEIGHT + 1)

    def cell_width(self) -> float:
        return float(CELL_PIXELS)        # on the desktop one cell is exactly one grid cell

    def set_layer(self, layer: str) -> None:
        """Above every window (default) or below them, like a wallpaper."""
        if layer not in LAYERS or layer == self.layer:
            return
        visible = self.isVisible()
        self.layer = layer
        self.setWindowFlags(strip_flags(layer))
        if visible:
            self.show()

    def set_quality_tier(self, tier: str) -> None:
        """Control Center quality tiers set the frame rate; the world speed never changes."""
        self.frame_timer.start(FRAME_MS[normalize_tier(tier)])

    # ----- interpolation ---------------------------------------------------------------

    def _stepped(self) -> None:
        world = self.service.world
        if world is None:
            return
        self._before = self._after or {key: r.x_milli for key, r in world.residents.items()}
        self._after = {key: resident.x_milli for key, resident in world.residents.items()}
        self._stepped_at = self._clock()
        self.update_mask()

    def resident_x_milli(self, resident) -> float:
        if self._dragging is not None and self._dragging[0] == resident.identifier:
            return self._dragging[1]
        start = self._before.get(resident.identifier, resident.x_milli)
        end = self._after.get(resident.identifier, resident.x_milli)
        share = min(1.0, max(0.0, (self._clock() - self._stepped_at) * 1000 / STEP_MS))
        return start + (end - start) * share

    # ----- input region ------------------------------------------------------------------

    def interactive_region(self) -> QRegion:
        """Residents, furniture and the button; the whole strip only while arranging."""
        if self.arranging:
            return QRegion(self.rect())
        region = QRegion(self.button.geometry().adjusted(-2, -2, 2, 2))
        world = self.service.world
        if world is None:
            return region
        for piece, definition in world.in_zone(self.zone):
            region = region.united(self.piece_rect(piece, definition).toAlignedRect())
        reach = CELL_PIXELS            # covers the step a resident may take before the next mask
        for resident in world.residents.values():
            if resident.zone == self.zone:
                box = self.caption_rect(resident).united(self._resident_box(resident))
                region = region.united(box.toAlignedRect().adjusted(-reach, 0, reach, 0))
        return region

    def _resident_box(self, resident) -> QRectF:
        center, radius = self.resident_center(resident), self.resident_radius()
        return QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)

    def update_mask(self) -> None:
        self.setMask(self.interactive_region())

    def set_arranging(self, arranging: bool) -> None:
        self.arranging = arranging
        self.update_mask()
        self.update()

    def paint_backdrop(self, painter) -> None:
        """No background on the desktop; while arranging, a faint tint shows the home's bounds.

        The tint is also what lets the whole strip take clicks then: on Windows a
        translucent window passes clicks through fully transparent pixels whatever
        its mask says.
        """
        if not self.arranging:
            return
        painter.fillRect(self.rect(), QColor(40, 120, 200, 40))
        painter.setPen(QPen(QColor(40, 120, 200, 200), 1, Qt.PenStyle.DashLine))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        zone, width = self.world.zones[self.zone], self.cell_width()
        floor = self._floor_y()
        for cell in range(zone.width_cells + 1):
            painter.drawLine(QPointF(cell * width, floor - 6), QPointF(cell * width, floor))
        for cell in zone.restricted:
            painter.fillRect(QRectF(cell * width, floor - 6, width, 6), QColor(200, 70, 70, 160))
        painter.drawRect(QRectF(zone.entrance * width, floor - width * 2, width, width * 2))

    def _floor_y(self) -> float:
        """Furniture stands on the bottom edge of the work area, right on the taskbar."""
        return float(self.height() - 1)

    # ----- the home button -------------------------------------------------------------------

    def _home_button(self) -> QToolButton:
        button = QToolButton(self)
        button.setText("⌂")
        button.setToolTip(translate("tab_pet_home_text", "Pet home"))
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setStyleSheet("QToolButton { background: rgba(0,0,0,150); color: white; border-radius: 6px;"
                             " padding: 2px 6px; font-size: 14px; }")
        button.setMenu(QMenu(button))
        button.menu().aboutToShow.connect(self._fill_home_menu)
        button.adjustSize()
        button.move(2, 2)
        return button

    def _fill_home_menu(self) -> None:
        menu = self.button.menu()
        menu.clear()
        menu.addAction(translate("pet_home_open", "Open Pet home"), self.open_requested.emit)
        running = self.service.running
        menu.addAction(translate("pet_home_pause" if running else "pet_home_start", "Pause" if running else "Start"),
                       (lambda: self.service.pause("stopped")) if running else self.service.start)
        other = "bottom" if self.layer == "top" else "top"
        menu.addAction(translate("pet_home_layer_to_" + other, "Move below windows" if other == "bottom"
                                 else "Move above windows"), lambda: self.layer_requested.emit(other))
        menu.addAction(translate("pet_home_hide", "Hide the home"), self.hide)

    # ----- mouse -------------------------------------------------------------------------------

    def _resident_at(self, point: QPointF) -> str | None:
        world = self.service.world
        for resident in sorted(world.residents.values(), key=lambda item: item.identifier):
            if resident.zone == self.zone and self._resident_box(resident).adjusted(-4, -4, 4, 4).contains(point):
                return resident.identifier
        return None

    def _piece_at(self, point: QPointF) -> str | None:
        for piece, definition in self.service.world.in_zone(self.zone):
            if self.piece_rect(piece, definition).contains(point):
                return piece.identifier
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.service.world is None:
            return
        point = event.position()
        resident = self._resident_at(point)
        if event.button() == Qt.MouseButton.RightButton:
            self._context_menu(resident, self._piece_at(point), event.globalPosition().toPoint())
        elif event.button() == Qt.MouseButton.LeftButton and resident is not None:
            self._press = (resident, point)
        elif event.button() == Qt.MouseButton.LeftButton and self.arranging:
            self.cell_clicked.emit(int(point.x() // self.cell_width()))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._press is None:
            return
        identifier, origin = self._press
        if self._dragging is None:
            if (event.position() - origin).manhattanLength() < DRAG_START_PX:
                return
            self.service.run(lambda world: world.drag(identifier, None))
            self.setMask(QRegion(self.rect()))      # keep receiving the drag everywhere
        self._dragging = (identifier, event.position().x() / self.cell_width() * CELL_PIXELS * 1000)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._press is None:
            return
        identifier, _origin = self._press
        self._press = None
        if self._dragging is not None:
            x_milli = int(self._dragging[1])
            self._dragging = None
            self.service.run(lambda world: world.drag(identifier, x_milli))
            self._after[identifier] = self._before[identifier] = self.service.world.residents[identifier].x_milli
            self.update_mask()
            return
        self.resident_selected.emit(identifier)
        self.show_card(identifier, event.globalPosition().toPoint())

    def show_card(self, identifier: str, where: QPoint) -> None:
        """A non-activating tooltip card: name, what it is doing, and its needs."""
        resident = self.service.world.residents.get(identifier)
        if resident is None:
            return
        QToolTip.showText(where, card_text(resident), self, QRect(), 6000)

    def _context_menu(self, resident: str | None, piece: str | None, where: QPoint) -> None:
        menu = QMenu(self)
        if resident is not None:
            for command in COMMANDS:
                menu.addAction(translate("pet_home_cmd_" + command, command.title()),
                               lambda c=command: self.service.run(lambda world: world.command(resident, c)))
            menu.addSeparator()
        elif piece is not None:
            menu.addAction(translate("pet_home_store", "Put away"),
                           lambda: self.service.run(lambda world: world.store(piece)))
            menu.addSeparator()
        menu.addAction(translate("pet_home_open", "Open Pet home"), self.open_requested.emit)
        self.last_menu = menu
        menu.popup(where)

    # ----- lifecycle ---------------------------------------------------------------------------

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.service.resume(HIDDEN_REASON)

    def hideEvent(self, event: QHideEvent) -> None:
        """Hidden (for example by Hide all) means paused, and the status says so."""
        super().hideEvent(event)
        if not self.isVisible() and not getattr(self, "_closing", False):
            self.service.pause(HIDDEN_REASON)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Closing removes the desktop drawing only; the home keeps its state and clock."""
        self._closing = True
        self.frame_timer.stop()
        try:
            self.service.ticked.disconnect(self._stepped)
        except (RuntimeError, TypeError):
            pass
        self.service.resume(HIDDEN_REASON)
        super().closeEvent(event)
        self.closed.emit()

