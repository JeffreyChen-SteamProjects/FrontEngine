"""The home on the desktop: a transparent strip along the bottom of the work area.

Only residents, furniture and the small home button take the mouse; a window
mask leaves every other pixel of the strip to the windows underneath, so the
home never blocks the desktop. The strip never takes focus or activates.

The world moves in 200 ms steps; the strip draws in between at the quality
tier's frame rate (60 / 30 / 15 FPS) by interpolating resident positions, so
smoothness costs rendering only and never changes what the world computes.
"""
from __future__ import annotations

import uuid
from time import monotonic
from typing import Callable

from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QCloseEvent, QColor, QGuiApplication, QHideEvent, QMouseEvent, QPainter, QPen, QRegion, QShowEvent,
)
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QToolButton, QToolTip

from frontengine.show.pet_game.captions import card_text, dispatch_text, item_label, result_text
from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.home_view import HomeView
from frontengine.show.pet_game.strip_weather import StripWeather
from frontengine.show.pet_game.themes import NIGHT_TINT, floor_color, glyph, night_shade
from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.pet_game.catalog import CELL_PIXELS
from frontengine.utils.pet_game.commission_work import dispatch
from frontengine.utils.pet_game.simulation import STEP_MS
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.pet_game.world import COMMANDS, INTERACTIONS
from frontengine.utils.power_mode.power_mode import normalize_tier

STRIP_HEIGHT = 150                    # at 100 %
SCALES = (75, 100, 125, 150, 200)     # strip sizes in percent; furniture, pets and height all follow
DEFAULT_SCALE = 100
FOLLOW_MARGIN = 0.25                  # scroll once the followed spot leaves the middle half of the screen
SCROLL_EASE = 0.25                    # share of the remaining distance scrolled per frame
BUBBLE_SECONDS = 3.0
FRAME_MS = {"high": 16, "balanced": 33, "saver": 66}
DRAG_START_PX = 6
LAYERS = ("top", "bottom")
HOME_MODES = ("normal", "focus", "meeting", "saver")
HIDDEN_REASON = "hidden"
LOCKED_REASON = "locked"                # the computer is locked: the home waits
TOOLBAR_OPEN_KEY = "pet_home_toolbar_open"
TOOLBAR_DOCK_KEY = "pet_home_toolbar_dock"
DOCKS = ("left", "right")
TOOLBAR = (("pet_home_toolbar_arrange", "Arrange", "arrange", ""),
           ("pet_home_toolbar_residents", "Residents", "tab", "pet_home_residents_section"),
           ("pet_home_toolbar_work", "Work", "tab", "pet_home_work_section"))
RESIDENT_ACTIONS = (("photo", "pet_home_photo_of", "Take a photo"),
                    ("wardrobe", "pet_home_wardrobe", "Wardrobe…"),
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
    scale_requested = Signal(int)          # a size in percent chosen on the strip (Ctrl+wheel or the ⌂ menu)
    quiet = False                          # focus mode: no bubbles and no cards
    closed = Signal()                      # at close time, before the deferred delete
    arrange_finished = Signal()            # the strip's own way out of arranging (it takes no keys)
    hide_requested = Signal()              # "Hide the home": the page unticks Show the home on the desktop
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
        # Arranging: (piece, where it was pressed, grab offset, cell it started on, moved yet)
        self._piece_press: tuple[str, QPointF, float, int, bool] | None = None
        self.setWindowFlags(strip_flags(self.layer))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAcceptDrops(True)
        self.setWindowTitle(translate("tab_pet_home_text", "Pet home"))
        self.scale = DEFAULT_SCALE / 100
        self._scroll_goal = 0.0
        self.setFixedHeight(STRIP_HEIGHT)
        self.chosen: str | None = None        # the pet last clicked here, shown in the toolbar
        self._menu_x_milli = 0                # where the last right-click was, for "Come here"
        self.button = self._home_button()
        self.toolbar = self._toolbar()
        self.done_button = self._done_button()
        self.place_toolbar()
        self.weather_layer = StripWeather(self)     # rain and snow: its own window, never takes input
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self.update)
        self.frame_timer.timeout.connect(self._weather_frame)
        self.frame_timer.timeout.connect(self._ease_scroll)
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
        """Sit on the bottom edge of the zone's screen work area, above the taskbar, at the chosen size.

        A home larger than the screen at this size keeps its window on the screen and scrolls
        its content instead (see ``_scroll_target``), so it never spills onto another monitor.
        """
        area = self.screen_for_zone().availableGeometry()
        height = round(STRIP_HEIGHT * self.scale)
        self.setFixedSize(min(area.width(), self.content_width() + 2), height)
        self.move(area.left(), area.bottom() - height + 1)
        self.scroll_x = self._scroll_goal = min(self.scroll_x, self.max_scroll())

    def cell_width(self) -> float:
        return CELL_PIXELS * self.scale        # at 100 % one cell is exactly one grid cell

    def content_width(self) -> int:
        return round(self.world.zones[self.zone].width_pixels * self.scale) if self.world else 0

    def max_scroll(self) -> float:
        return float(max(0, self.content_width() + 2 - self.width()))

    def set_scale(self, percent: int) -> None:
        """Bigger or smaller furniture, pets and strip; the world and its layout do not change."""
        if percent not in SCALES or round(self.scale * 100) == percent:
            return
        self.scale = percent / 100
        self.place_on_screen()
        self._scroll_goal = self._scroll_target()
        self.scroll_x = self._scroll_goal
        self.place_toolbar()
        self.update_mask()
        self.update()

    def _scroll_target(self) -> float:
        """Keep the pet last clicked (else the pets' middle) in the middle half of the screen."""
        limit = self.max_scroll()
        world = self.service.world
        if limit <= 0 or world is None:
            return 0.0
        pets = [r for r in world.residents.values() if r.zone == self.zone]
        followed = [r for r in pets if r.identifier == self.chosen] or pets
        if not followed:
            return self._scroll_goal
        middle = sum(self.resident_x_milli(r) for r in followed) / len(followed) / 1000 / CELL_PIXELS
        x = middle * self.cell_width() - self._scroll_goal          # where it would be drawn now
        if self.width() * FOLLOW_MARGIN <= x <= self.width() * (1 - FOLLOW_MARGIN):
            return self._scroll_goal
        return max(0.0, min(limit, middle * self.cell_width() - self.width() / 2))

    def _ease_scroll(self) -> None:
        """Glide toward the scroll goal a little each frame; the input mask moves with the content."""
        distance = self._scroll_goal - self.scroll_x
        if abs(distance) < 0.5:
            if distance:
                self.scroll_x = self._scroll_goal
                self.update_mask()
            return
        self.scroll_x += distance if self.reduced_motion else distance * SCROLL_EASE
        self.update_mask()

    def wheelEvent(self, event) -> None:
        """Ctrl+wheel over a pet, a piece or ⌂ makes the strip bigger or smaller."""
        if not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            event.ignore()
            return
        current = SCALES.index(min(SCALES, key=lambda value: abs(value - self.scale * 100)))
        step = 1 if event.angleDelta().y() > 0 else -1
        target = SCALES[max(0, min(len(SCALES) - 1, current + step))]
        if target != round(self.scale * 100):
            self.scale_requested.emit(target)
        event.accept()

    def set_layer(self, layer: str) -> None:
        """Above every window (default) or below them, like a wallpaper."""
        if layer not in LAYERS or layer == self.layer:
            return
        visible = self.isVisible()
        self.layer = layer
        self.setWindowFlags(strip_flags(layer))
        self.weather_layer.apply_layer()
        if visible:
            self.show()

    def set_quality_tier(self, tier: str) -> None:
        """Control Center quality tiers set the frame rate; the world speed never changes."""
        self.frame_timer.start(FRAME_MS[normalize_tier(tier)])

    # ----- interpolation ---------------------------------------------------------------

    def follow_world(self, world) -> None:
        """Rebind a kept strip to the home now running.

        Both homes number their first zone "z1", so a strip survives a manage/sandbox switch;
        without this it kept drawing the other home and could not finish a drag on this one.
        """
        if world is self.world:
            return
        self._finish_pointer(commit=False)
        self._before, self._after = {}, {}
        self.bubbles.clear()
        self.set_world(world, self.zone)
        self.place_on_screen()
        self._stepped()

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
        self._scroll_goal = self._scroll_target()
        self.update_mask()
        self.weather_layer.sync()

    def _weather_frame(self) -> None:
        if self.weather_layer.isVisible():
            self.weather_layer.update()

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
        self.note_events(events)
        for event in events:
            text = bubble_text(event)
            if text and event.get("resident") in self.service.world.residents:
                self.bubbles[event["resident"]] = (text, self._clock() + BUBBLE_SECONDS)

    def bubble_rect(self, resident) -> QRectF | None:
        bubble = self.bubbles.get(resident.identifier)
        if self.quiet or bubble is None or bubble[1] < self._clock():
            return None
        if not QRectF(self.rect()).intersects(self.resident_box(resident)):
            return None
        width = min(self.width(), self.fontMetrics().horizontalAdvance(bubble[0]) + 14)
        caption = self.caption_rect(resident)
        left = max(0.0, min(caption.center().x() - width / 2, self.width() - width))
        return QRectF(left, caption.top() - 24, width, 20)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.service.world is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_dusk(painter)
        for resident in self.service.world.residents.values():
            rect = self.bubble_rect(resident) if resident.zone == self.zone else None
            if rect is not None:
                painter.setPen(QPen(QColor(60, 60, 60), 1))
                painter.setBrush(QColor(255, 255, 255, 235))
                painter.drawRoundedRect(rect, 8, 8)
                painter.setPen(QColor(30, 30, 30))
                text = painter.fontMetrics().elidedText(self.bubbles[resident.identifier][0],
                                                       Qt.TextElideMode.ElideRight, max(0, int(rect.width()) - 14))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.end()

    def _paint_dusk(self, painter: QPainter) -> None:
        """Evening and night dim what is already drawn - only those pixels, never the clear ones.

        The strip has no background: painting rain or a sky over it would make those pixels
        catch the mouse on Windows. Source-atop tints pieces and pets only, so the click-through
        area and the input mask stay exactly as they were.
        """
        shade = night_shade(self.service.world.time_ms)
        if shade <= 0:
            return
        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        painter.fillRect(self.rect(), QColor(NIGHT_TINT.red(), NIGHT_TINT.green(), NIGHT_TINT.blue(), shade))
        painter.restore()

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
            painter.drawLine(QPointF(self.cell_x(cell), floor - 6), QPointF(self.cell_x(cell), floor))
        for cell in zone.restricted:
            painter.fillRect(QRectF(self.cell_x(cell), floor - 6, width, 6), QColor(200, 70, 70, 160))
        painter.drawRect(QRectF(self.cell_x(zone.entrance), floor - width * 2, width, width * 2))

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
        self.commission_button = self._commission_button(bar)
        row.addWidget(self.commission_button)
        self.shortcut_buttons.append(self.commission_button)
        self.info = QLabel(bar)
        row.addWidget(self.info)
        return bar

    def _commission_button(self, bar: QFrame) -> QToolButton:
        """Today's commissions; choosing one sends the best-suited pet to make what it still lacks."""
        button = QToolButton(bar)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setText(translate("pet_home_toolbar_commissions", "Commissions"))
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(button)
        menu.aboutToShow.connect(lambda: self._fill_commission_menu(menu))
        button.setMenu(menu)
        return button

    def _fill_commission_menu(self, menu: QMenu) -> None:
        menu.clear()
        world = self.service.world
        offers = world.progress.commissions["offers"] if world is not None else []
        for index, offer in enumerate(offers):
            line = translate("pet_home_offer_line", "{count} × {item} → {coins} coins").format(
                count=offer["count"], item=item_label(world, offer["item"]), coins=world.coin_amount(offer["coins"]))
            action = menu.addAction(("✔ " if offer["done"] else "") + line,
                                    lambda i=index, item=offer["item"]: self.dispatch_commission(i, item))
            action.setEnabled(not offer["done"])
        if not offers:
            menu.addAction(translate("pet_home_commissions_none", "No commissions today.")).setEnabled(False)

    def dispatch_commission(self, index: int, item: str) -> str:
        """Send a pet for commission ``index`` and say who goes, or why nobody can, beside the button."""
        sent = self.service.run(lambda world: dispatch(world, index))
        text = dispatch_text(self.service.world, sent, item)
        QToolTip.showText(self.commission_button.mapToGlobal(self.commission_button.rect().bottomLeft()), text, self)
        self.refresh_info()
        self.update()
        return text

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
        points_left = opened == (self.dock == "left")
        self.toggle.setText("‹" if points_left else "›")
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
        self.weather_layer.sync()

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self.weather_layer.sync()

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
        sizes = menu.addMenu(translate("pet_home_strip_size", "Size"))
        for percent in SCALES:
            action = sizes.addAction(f"{percent}%", lambda p=percent: self.scale_requested.emit(p))
            action.setCheckable(True)
            action.setChecked(round(self.scale * 100) == percent)
        modes = menu.addMenu(translate("pet_home_mode", "Mode"))
        for mode in HOME_MODES:
            modes.addAction(translate("pet_home_mode_" + mode, mode), lambda m=mode: self.mode_requested.emit(m))
        menu.addAction(translate("pet_home_hide", "Hide the home"), self._hide_home)

    def _hide_home(self) -> None:
        # The page turns the setting off and closes every strip; hiding first also covers a strip
        # that nothing is listening to.
        self.hide_requested.emit()
        self.hide()

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
            self._menu_x_milli = int(self.x_cell(point.x()) * CELL_PIXELS * 1000)
            self._context_menu(resident, self._piece_at(point), event.globalPosition().toPoint())
        elif event.button() == Qt.MouseButton.LeftButton and resident is not None:
            self._press = (resident, point)
        elif event.button() == Qt.MouseButton.LeftButton and self.arranging:
            if not self._press_piece(point):
                self.cell_clicked.emit(int(self.x_cell(point.x())))

    def _press_piece(self, point: QPointF) -> bool:
        """Arranging: pressing on a piece selects it and starts a drag; a click alone only selects it."""
        identifier = self._piece_at(point)
        piece = self.service.world.furniture.get(identifier) if identifier else None
        if piece is None:
            return False
        rect = self.piece_rect(piece, self.service.world.definition(piece))
        self._piece_press = (identifier, point, point.x() - rect.left(), piece.cell, False)
        self.furniture_selected.emit(identifier)
        return True

    def _piece_cell(self, x: float) -> int:
        return max(0, int(round(self.x_cell(x - self._piece_press[2]))))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._piece_press is not None:
            identifier, origin, grab, start, moved = self._piece_press
            if not moved and (event.position() - origin).manhattanLength() < DRAG_START_PX:
                return
            self._piece_press = (identifier, origin, grab, start, True)
            self.piece_hovered.emit(identifier, self._piece_cell(event.position().x()))
            return
        if self._press is None:
            return
        identifier, origin = self._press
        if self._dragging is None:
            if (event.position() - origin).manhattanLength() < DRAG_START_PX:
                return
            self.service.run(lambda world: world.drag(identifier, None))
            self.setMask(QRegion(self.rect()))      # keep receiving the drag everywhere
        self._dragging = (identifier, self.x_cell(event.position().x()) * CELL_PIXELS * 1000)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._piece_press is not None:
            identifier, _origin, _grab, _start, moved = self._piece_press
            cell = self._piece_cell(event.position().x())
            self._piece_press = None
            if moved:
                self.piece_dropped.emit(identifier, cell)
            return
        if event.button() != Qt.MouseButton.LeftButton or self._press is None:
            return
        identifier, _origin = self._press
        self._press = None
        if self._dragging is not None:
            self._finish_pointer(commit=True)
            return
        self.chosen = identifier
        self.refresh_info()
        self.resident_selected.emit(identifier)
        self.show_card(identifier, event.globalPosition().toPoint())

    def _cancel_piece_drag(self) -> None:
        """A furniture drag that loses the mouse leaves the piece where it was and clears the preview."""
        press, self._piece_press = getattr(self, "_piece_press", None), None
        if press is not None and press[4]:
            self.piece_dropped.emit(press[0], press[3])

    def _finish_pointer(self, *, commit: bool) -> None:
        self._cancel_piece_drag()
        dragging = self._dragging
        self._press = self._dragging = None
        world = self.service.world
        if dragging is not None and world is not None and world is self.world:
            identifier, preview = dragging
            resident = world.residents.get(identifier)
            if resident is not None:
                if resident.activity is not None and resident.activity.kind == "drag":
                    position = int(preview) if commit else resident.x_milli
                    self.service.run(lambda current: current.drag(identifier, position))
                self._after[identifier] = self._before[identifier] = resident.x_milli
        self.update_mask()
        self.update()

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.UngrabMouse and (getattr(self, "_press", None) is not None
                                                        or getattr(self, "_piece_press", None) is not None):
            self._finish_pointer(commit=False)
        return super().event(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Double-clicking a pet pats it: the most common care without opening a menu."""
        resident = self._resident_at(event.position()) if self.service.world is not None else None
        if event.button() == Qt.MouseButton.LeftButton and resident is not None:
            self._press = None
            self._interact(resident, "pat")
            event.accept()

    @staticmethod
    def _dropped_files(mime) -> bool:
        return mime.hasUrls() and any(url.isLocalFile() for url in mime.urls())

    def dragEnterEvent(self, event) -> None:
        if self.service.world is not None and self._dropped_files(event.mimeData()):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        if self._dropped_files(event.mimeData()) and self._resident_at(event.position()) is not None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        """A file dropped on a pet is a treat and nothing more: it is never opened, changed or
        deleted, and it never turns into materials or coins."""
        resident = self._resident_at(event.position()) if self.service.world is not None else None
        if resident is None or not self._dropped_files(event.mimeData()):
            event.ignore()
            return
        self._interact(resident, "feed")
        event.acceptProposedAction()

    def show_card(self, identifier: str, where: QPoint) -> None:
        """A non-activating tooltip card: name, what it is doing, and its needs."""
        resident = self.service.world.residents.get(identifier)
        if resident is None or self.quiet:
            return
        hint = translate("pet_home_card_hint", "Double-click to pat · right-click for more")
        QToolTip.showText(where, card_text(resident, self.service.world) + "\n" + hint, self, QRect(), 6000)

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
        menu.addAction(translate("pet_home_call", "Come here"),
                       lambda: self._ask(resident, lambda world: world.call(resident, self._menu_x_milli)))
        menu.addAction(translate("pet_home_tag", "Play tag"),
                       lambda: self._ask(resident, lambda world: world.play_tag(resident)))
        ask = menu.addMenu(translate("pet_home_ask", "Ask to"))
        for command in COMMANDS:
            ask.addAction(translate("pet_home_cmd_" + command, command.title()),
                          lambda c=command: self.service.run(lambda world: world.command(resident, c)))
        menu.addSeparator()
        for action, key, fallback in RESIDENT_ACTIONS:
            menu.addAction(translate(key, fallback), lambda a=action: self.action_requested.emit(a, resident))

    def _ask(self, resident: str, change) -> None:
        result = self.service.run(change)
        if result != "accepted":
            self.bubbles[resident] = (result_text(result), self._clock() + BUBBLE_SECONDS)

    def _interact(self, resident: str, kind: str) -> None:
        result = self.service.run(lambda world: world.interact(resident, kind))
        if result != "accepted":
            self.bubbles[resident] = (result_text(result), self._clock() + BUBBLE_SECONDS)

    def _upgrade(self, definition: str) -> None:
        transaction = "upgrade-" + uuid.uuid4().hex
        result = self.service.run(lambda world: world.upgrade(definition, transaction))
        if result != "accepted":
            QToolTip.showText(self.mapToGlobal(self.button.geometry().bottomLeft()), result_text(result), self)

    def _piece_menu(self, menu: QMenu, piece: str) -> None:
        """Who is using it and what it is for (as plain lines), then move or put away."""
        world = self.service.world
        found = world.furniture.get(piece)
        if found is None:
            return
        for line in piece_lines(world, found):
            menu.addAction(line).setEnabled(False)
        menu.addSeparator()
        cost = world.upgrade_cost(found.definition)
        if cost is not None:
            menu.addAction(translate("pet_home_upgrade", "Upgrade ({cost} coins)").format(cost=cost),
                           lambda: self._upgrade(found.definition))
        menu.addAction(translate("pet_home_move_piece", "Move"), lambda: self.action_requested.emit("move", piece))
        menu.addAction(translate("pet_home_store", "Put away"),
                       lambda: self.service.run(lambda world: world.store(piece)))

    # ----- lifecycle ---------------------------------------------------------------------------

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.service.resume(HIDDEN_REASON)
        self.weather_layer.sync()

    def hideEvent(self, event: QHideEvent) -> None:
        """Hidden (for example by Hide all) means paused, and the status says so."""
        self._finish_pointer(commit=False)
        super().hideEvent(event)
        self.weather_layer.sync()
        if not self.isVisible() and not getattr(self, "_closing", False):
            self.service.pause(HIDDEN_REASON)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Closing removes the desktop drawing only; the home keeps its state and clock."""
        self._finish_pointer(commit=False)
        self._closing = True
        self.frame_timer.stop()
        self.weather_layer.close()
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
    if definition.profession is not None:
        level = world.station_level(piece.definition)
        lines.append(translate("pet_home_station_level", "Level {level} · {speed}% speed").format(
            level=level, speed=75 + 25 * level))
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
    if kind == "tagged":
        return translate("pet_home_bubble_tag", "Tag!")
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
