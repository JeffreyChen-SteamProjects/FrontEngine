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
    QCloseEvent, QColor, QGuiApplication, QHideEvent, QMouseEvent, QPainter, QPen, QRegion, QShowEvent,
)
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QToolButton, QToolTip

from frontengine.show.pet_game.captions import card_text, result_text
from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.home_view import HomeView
from frontengine.show.pet_game.themes import floor_color, glyph
from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.pet_game.catalog import CELL_PIXELS
from frontengine.utils.pet_game.simulation import STEP_MS
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.pet_game.world import COMMANDS, INTERACTIONS
from frontengine.utils.power_mode.power_mode import normalize_tier

STRIP_HEIGHT = 150
BUBBLE_SECONDS = 3.0
FRAME_MS = {"high": 16, "balanced": 33, "saver": 66}
DRAG_START_PX = 6
LAYERS = ("top", "bottom")
HOME_MODES = ("normal", "focus", "meeting", "saver")
HIDDEN_REASON = "hidden"
TOOLBAR_OPEN_KEY = "pet_home_toolbar_open"
TOOLBAR_DOCK_KEY = "pet_home_toolbar_dock"
DOCKS = ("left", "right")
TOOLBAR = (("pet_home_toolbar_arrange", "Arrange", "arrange", ""),
           ("pet_home_toolbar_residents", "Residents", "tab", "pet_home_residents_section"),
           ("pet_home_toolbar_work", "Work", "tab", "pet_home_work_section"))
RESIDENT_ACTIONS = (("wardrobe", "pet_home_wardrobe", "Wardrobe…"),
                    ("work", "pet_home_work_for_pet", "Work for this pet…"),
                    ("follow", "pet_home_follow", "Follow in the overview"))


def strip_flags(layer: str) -> Qt.WindowType:
    stack = Qt.WindowType.WindowStaysOnBottomHint if layer == "bottom" else Qt.WindowType.WindowStaysOnTopHint
    return (Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus | stack)


class HomeStrip(HomeView):
    """One zone drawn on its screen. Hiding it pauses the home; closing it does not."""

    caption_backdrop = True
    open_requested = Signal()
    action_requested = Signal(str, str)    # (action, pet or piece): wardrobe, work, follow, move, tab, arrange
    layer_requested = Signal(str)
    mode_requested = Signal(str)
    quiet = False                          # focus mode: no bubbles and no cards
    closed = Signal()                      # at close time, before the deferred delete
    arrange_finished = Signal()            # the strip's own way out of arranging (it takes no keys)
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
        self.chosen: str | None = None        # the pet last clicked here, shown in the toolbar
        self.button = self._home_button()
        self.toolbar = self._toolbar()
        self.done_button = self._done_button()
        self.place_toolbar()
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self.update)
        self.set_quality_tier(tier)
        self.bubbles: dict[str, tuple[str, float]] = {}     # resident -> (text, shown until)
        service.ticked.connect(self._stepped)
        service.events_ready.connect(self._events)
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
        text = "⌂ " + glyph(world.home, world.time_ms)
        if self.button.text() != text:
            self.button.setText(text)
            self.place_toolbar()              # the glyph widens the button; never elide it
        self.refresh_info()
        self.update_mask()

    def resident_x_milli(self, resident) -> float:
        if self._dragging is not None and self._dragging[0] == resident.identifier:
            return self._dragging[1]
        if self.reduced_motion:
            return resident.x_milli
        start = self._before.get(resident.identifier, resident.x_milli)
        end = self._after.get(resident.identifier, resident.x_milli)
        share = min(1.0, max(0.0, (self._clock() - self._stepped_at) * 1000 / STEP_MS))
        return start + (end - start) * share

    # ----- speech bubbles -----------------------------------------------------------------

    def _events(self, events: list) -> None:
        """Short bubbles say what a pet just started, who it greeted, or what it earned."""
        if self.quiet:
            return
        for event in events:
            text = bubble_text(event)
            if text and event.get("resident") in self.service.world.residents:
                self.bubbles[event["resident"]] = (text, self._clock() + BUBBLE_SECONDS)

    def bubble_rect(self, resident) -> QRectF | None:
        bubble = self.bubbles.get(resident.identifier)
        if bubble is None or bubble[1] < self._clock():
            return None
        width = self.fontMetrics().horizontalAdvance(bubble[0]) + 14
        caption = self.caption_rect(resident)
        return QRectF(caption.center().x() - width / 2, caption.top() - 24, width, 20)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.service.world is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for resident in self.service.world.residents.values():
            rect = self.bubble_rect(resident) if resident.zone == self.zone else None
            if rect is not None:
                painter.setPen(QPen(QColor(60, 60, 60), 1))
                painter.setBrush(QColor(255, 255, 255, 235))
                painter.drawRoundedRect(rect, 8, 8)
                painter.setPen(QColor(30, 30, 30))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.bubbles[resident.identifier][0])
        painter.end()

    # ----- input region ------------------------------------------------------------------

    def interactive_region(self) -> QRegion:
        """Residents, furniture and the button; the whole strip only while arranging."""
        if self.arranging:
            return QRegion(self.rect())
        region = QRegion(self.button.geometry().adjusted(-2, -2, 2, 2))
        region = region.united(QRegion(self.toolbar.geometry().adjusted(-2, -2, 2, 2)))
        world = self.service.world
        if world is None:
            return region
        for piece, definition in world.in_zone(self.zone):
            region = region.united(self.piece_rect(piece, definition).toAlignedRect())
        reach = CELL_PIXELS            # covers the step a resident may take before the next mask
        for resident in world.residents.values():
            if resident.zone == self.zone:
                box = self.caption_rect(resident).united(self.resident_box(resident))
                bubble = self.bubble_rect(resident)
                if bubble is not None:                     # painting is clipped to the mask too
                    box = box.united(bubble)
                region = region.united(box.toAlignedRect().adjusted(-reach, 0, reach, 0))
        return region

    def update_mask(self) -> None:
        self.setMask(self.interactive_region())

    def set_arranging(self, arranging: bool) -> None:
        self.arranging = arranging
        self.done_button.setText("✓ " + translate("pet_home_arrange_done", "Done arranging"))
        self.done_button.setVisible(arranging)
        self.place_toolbar()
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
        painter.fillRect(QRectF(0, self._floor_y() - 4, self.width(), 4),
                         floor_color(self.world.zones[self.zone].theme))
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
        return button

    def _toolbar(self) -> QFrame:
        """Beside ⌂: a toggle that opens shortcuts and, while open, coins, the chosen pet and the jobs."""
        bar = QFrame(self)
        bar.setStyleSheet("QFrame { background: rgba(0,0,0,150); border-radius: 6px; }"
                          " QToolButton, QLabel { color: white; font-size: 12px; padding: 2px 6px; }")
        row = QHBoxLayout(bar)
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(2)
        self.toggle = QToolButton(bar)
        self.toggle.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.toggle.clicked.connect(lambda: self.set_toolbar_open(not self.toolbar_open))
        row.addWidget(self.toggle)
        self.shortcut_buttons = []
        for key, fallback, action, target in TOOLBAR:
            button = QToolButton(bar)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setText(translate(key, fallback))
            button.clicked.connect(lambda _checked=False, a=action, t=target: self.action_requested.emit(a, t))
            row.addWidget(button)
            self.shortcut_buttons.append(button)
        self.info = QLabel(bar)
        row.addWidget(self.info)
        return bar

    @property
    def toolbar_open(self) -> bool:
        return bool(user_setting_dict.get(TOOLBAR_OPEN_KEY, False))

    @property
    def dock(self) -> str:
        dock = user_setting_dict.get(TOOLBAR_DOCK_KEY, "left")
        return dock if dock in DOCKS else "left"

    def set_toolbar_open(self, opened: bool) -> None:
        user_setting_dict[TOOLBAR_OPEN_KEY] = bool(opened)
        self.place_toolbar()

    def set_dock(self, dock: str) -> None:
        if dock in DOCKS:
            user_setting_dict[TOOLBAR_DOCK_KEY] = dock
            self.place_toolbar()

    def place_toolbar(self) -> None:
        """⌂ and the toolbar sit at the top of the strip, on the remembered side, clear of the taskbar."""
        opened = self.toolbar_open
        self.toggle.setText(("‹" if self.dock == "left" else "›") if opened else ("›" if self.dock == "left" else "‹"))
        for widget in (*self.shortcut_buttons, self.info):
            widget.setVisible(opened)
        self.refresh_info()
        self.toolbar.adjustSize()
        self.button.adjustSize()
        if self.dock == "left":
            self.button.move(2, 2)
            self.toolbar.move(self.button.geometry().right() + 4, 2)
            edge = self.toolbar.geometry().right()
        else:
            self.button.move(self.width() - self.button.width() - 2, 2)
            self.toolbar.move(self.button.x() - self.toolbar.width() - 4, 2)
            edge = self.toolbar.x() - 6
        if hasattr(self, "done_button"):
            self.done_button.adjustSize()
            self.done_button.move(edge + 6 if self.dock == "left" else edge - self.done_button.width(), 2)
        self.update_mask()

    def refresh_info(self) -> None:
        world = self.service.world
        if world is None or not self.toolbar_open:
            return
        parts = [translate("pet_home_toolbar_coins", "{coins} coins").format(coins=world.ledger.coins)]
        selected = world.residents.get(self.chosen or "")
        if selected is not None:
            parts.append(selected.name)
        jobs = sum(1 for task in world.tasks.values() if task.open)
        parts.append(translate("pet_home_toolbar_jobs", "{count} jobs").format(count=jobs))
        text = " · ".join(parts)
        if self.info.text() != text:
            self.info.setText(text)
            self.toolbar.adjustSize()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.place_toolbar()

    def _done_button(self) -> QToolButton:
        """Shown only while arranging: the strip never takes focus, so Esc cannot reach it."""
        button = QToolButton(self)
        button.setText("✓ " + translate("pet_home_arrange_done", "Done arranging"))
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setStyleSheet("QToolButton { background: rgba(0,0,0,170); color: white; border-radius: 6px;"
                             " padding: 2px 8px; font-size: 13px; }")
        button.clicked.connect(self.arrange_finished.emit)
        button.adjustSize()
        button.hide()
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
        other_dock = "right" if self.dock == "left" else "left"
        menu.addAction(translate("pet_home_dock_" + other_dock, "Move the toolbar to the " + other_dock),
                       lambda: self.set_dock(other_dock))
        modes = menu.addMenu(translate("pet_home_mode", "Mode"))
        for mode in HOME_MODES:
            modes.addAction(translate("pet_home_mode_" + mode, mode), lambda m=mode: self.mode_requested.emit(m))
        menu.addAction(translate("pet_home_hide", "Hide the home"), self.hide)

    # ----- mouse -------------------------------------------------------------------------------

    def _resident_at(self, point: QPointF) -> str | None:
        world = self.service.world
        for resident in sorted(world.residents.values(), key=lambda item: item.identifier):
            if resident.zone == self.zone and self.resident_box(resident).adjusted(-4, -4, 4, 4).contains(point):
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
        self.chosen = identifier
        self.refresh_info()
        self.resident_selected.emit(identifier)
        self.show_card(identifier, event.globalPosition().toPoint())

    def show_card(self, identifier: str, where: QPoint) -> None:
        """A non-activating tooltip card: name, what it is doing, and its needs."""
        resident = self.service.world.residents.get(identifier)
        if resident is None or self.quiet:
            return
        QToolTip.showText(where, card_text(resident, self.service.world), self, QRect(), 6000)

    def _context_menu(self, resident: str | None, piece: str | None, where: QPoint) -> None:
        menu = QMenu(self)
        if resident is not None:
            self._resident_menu(menu, resident)
        elif piece is not None:
            self._piece_menu(menu, piece)
        menu.addSeparator()
        menu.addAction(translate("pet_home_open", "Open Pet home"), self.open_requested.emit)
        self.last_menu = menu
        menu.popup(where)

    def _resident_menu(self, menu: QMenu, resident: str) -> None:
        """Care first (feed, pat, talk), then what to ask, then the wardrobe, work and the camera."""
        for kind in INTERACTIONS:
            menu.addAction(translate("pet_home_interact_" + kind, kind.title()),
                           lambda k=kind: self._interact(resident, k))
        ask = menu.addMenu(translate("pet_home_ask", "Ask to"))
        for command in COMMANDS:
            ask.addAction(translate("pet_home_cmd_" + command, command.title()),
                          lambda c=command: self.service.run(lambda world: world.command(resident, c)))
        menu.addSeparator()
        for action, key, fallback in RESIDENT_ACTIONS:
            menu.addAction(translate(key, fallback), lambda a=action: self.action_requested.emit(a, resident))

    def _interact(self, resident: str, kind: str) -> None:
        result = self.service.run(lambda world: world.interact(resident, kind))
        if result != "accepted":
            self.bubbles[resident] = (result_text(result), self._clock() + BUBBLE_SECONDS)

    def _piece_menu(self, menu: QMenu, piece: str) -> None:
        """Who is using it and what it is for (as plain lines), then move or put away."""
        world = self.service.world
        found = world.furniture.get(piece)
        if found is None:
            return
        for line in piece_lines(world, found):
            menu.addAction(line).setEnabled(False)
        menu.addSeparator()
        menu.addAction(translate("pet_home_move_piece", "Move"), lambda: self.action_requested.emit("move", piece))
        menu.addAction(translate("pet_home_store", "Put away"),
                       lambda: self.service.run(lambda world: world.store(piece)))

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
        for signal, slot in ((self.service.ticked, self._stepped), (self.service.events_ready, self._events)):
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass
        self.service.resume(HIDDEN_REASON)
        super().closeEvent(event)
        self.closed.emit()

def piece_lines(world, piece) -> list[str]:
    """What a piece is for and who is using it, for its right-click menu."""
    definition = world.definition(piece)
    lines = [translate(definition.label_key, definition.fallback)]
    if definition.profession is not None:
        use = translate("pet_home_profession_" + definition.profession, definition.profession)
    elif definition.activity is not None:
        use = translate("pet_home_cmd_" + definition.activity, definition.activity)
    else:
        use = translate("pet_home_piece_decoration", "Decoration")
    lines.append(translate("pet_home_piece_use", "For: {use}").format(use=use))
    users = sorted(world.residents[r].name for r in piece.users.values() if r in world.residents)
    lines.append(translate("pet_home_piece_users", "Used by: {names}").format(names=", ".join(users)) if users
                 else translate("pet_home_piece_free", "Nobody is using it"))
    if piece.owner in world.residents:
        lines.append(translate("pet_home_piece_owner", "{name}'s bed").format(name=world.residents[piece.owner].name))
    return lines


def bubble_text(event: dict) -> str:
    """Bubble wording for a world event, or nothing for events that need no bubble."""
    kind = event.get("kind")
    if kind == "activity" and event.get("activity") not in ("idle", "wander"):
        return translate("pet_home_activity_" + event["activity"], event["activity"])
    if kind == "greeted":
        return translate("pet_home_bubble_hello", "Hi!")
    if kind == "interacted":
        return translate("pet_home_bubble_" + event["interaction"], "♥")
    if kind == "squabble":
        return translate("pet_home_bubble_squabble", "Hmph!")
    if kind == "settled" and event.get("coins"):
        return f"+{event['coins']}"
    if kind == "wish_granted":
        return translate("pet_home_bubble_wish", "Thank you!")
    if kind == "life_event" and event.get("resident"):
        return translate("pet_game_event_" + event["event"], event["event"])
    return ""
