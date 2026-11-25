"""A pet home resident out on the desktop: its own small window, walking the screen like a desktop pet.

While a resident's ``outing`` is under way, the desktop strip stops drawing it and one of these
carries it instead. It moves with the desktop pet's ``PetMotion`` (floor, screen edges, window tops)
inside the work area of the strip's screen, is drawn by the home's own ``ResidentArt`` (the pet's
own character and outfit), and answers the mouse the way the strip does: click for the card,
double-click to pat, right-click for the menu, drag to carry and throw. It never takes focus.

When the outing ends (time up, *Come home*, a command, hunger) it walks back to the pet's spot on
the strip and closes; the strip draws the pet again from then on. The world is never changed from
here except through the strip's own actions, so rewards and needs stay the simulation's business.
"""
from __future__ import annotations

from time import monotonic

from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QMenu, QWidget

from frontengine.utils.screen_privacy import capture_affinity
from frontengine.show.pet.desktop_pet import (BEHAVIOUR_ACTIONS, POSE_STATES, SURFACE_FLOOR, PetMotion,
                                              windows_platforms)
from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.pet_game.catalog import CELL_PIXELS

TICK_MS = 33
SPEED = 3                     # px per tick, about a desktop pet's default pace
PLATFORM_EVERY = 10           # refresh the window tops every this many ticks
HOP = (5.0, -20.0)            # leaving the strip: a small jump up and out
RETURN_TIMEOUT_MS = 10_000    # a pet that cannot get back (stuck behind a ledge) simply goes home
DRAG_START_PX = 6
THROW_SCALE = 1.0


def outing_action(motion: PetMotion, renderer, dragging: bool = False) -> str:
    """The character's action for what the motion is doing, falling back to what the character has."""
    if dragging:
        wanted = ("drag", "fall", "idle")
    elif motion._airborne:
        wanted = ("fall", "idle")
    elif motion.surface != SURFACE_FLOOR:
        wanted = ("climb", "walk", "idle")
    elif motion.state == "walk":
        wanted = ("walk", "idle")
    elif motion.state in POSE_STATES or motion.state == "sleep":
        wanted = (motion.state, "idle")
    else:
        wanted = ("idle",)
    return next((action for action in wanted if renderer.has_action(action)), "idle")


def home_flags(layer: str) -> Qt.WindowType:
    stack = Qt.WindowType.WindowStaysOnBottomHint if layer == "bottom" else Qt.WindowType.WindowStaysOnTopHint
    return (Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus | stack)


class OutingPet(QWidget):
    """One resident roaming the desktop for the strip that owns it."""

    closed = Signal(str)                  # the resident, once its window has closed

    def __init__(self, strip, identifier: str, size: tuple[float, float], start: QPointF,
                 clock=monotonic, platforms=windows_platforms) -> None:
        super().__init__(None)
        self.strip, self.identifier = strip, identifier
        self._clock, self._platforms = clock, platforms
        self._started = clock()
        self.returning_since: float | None = None
        self._tick = 0
        self._press: QPointF | None = None
        self._grab = QPointF()
        self._dragging = False
        self._delta = QPointF()
        self.setWindowFlags(home_flags(strip.layer))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWindowTitle(translate("tab_pet_home_text", "Pet home"))
        width, height = max(16, round(size[0])), max(16, round(size[1]))
        self.setFixedSize(width, height)
        area = strip.screen_for_zone().availableGeometry()
        bounds = (area.left(), area.top(), area.left() + area.width(), area.top() + area.height())
        self.motion = PetMotion(round(start.x() - width / 2), round(start.y() - height), width, height,
                                bounds, SPEED, BEHAVIOUR_ACTIONS)
        self.motion.throw(HOP[0] if self.motion.vx >= 0 else -HOP[0], HOP[1])
        self.move(int(self.motion.x), int(self.motion.y))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.step)
        self.timer.start(TICK_MS)

    # ----- movement ---------------------------------------------------------------------

    def resident(self):
        world = self.strip.service.world
        return world.residents.get(self.identifier) if world is not None else None

    def home_x(self) -> float | None:
        """Where the pet stands on the strip, in global x, or None when it no longer lives there."""
        resident = self.resident()
        if resident is None or resident.zone != self.strip.zone:
            return None
        return self.strip.mapToGlobal(self.strip.resident_box(resident).center().toPoint()).x()

    def go_home(self) -> None:
        """The outing is over: drop to the floor and walk back to the pet's spot on the strip."""
        if self.returning_since is not None:
            return
        self.returning_since = self._clock()
        self.motion.set_platforms([])                 # no perching on the way down
        if self.motion.on_platform or self.motion.surface != SURFACE_FLOOR:
            self.motion.surface = SURFACE_FLOOR
            self.motion.throw(0.0, 1.0)

    def step(self) -> None:
        if self._dragging:
            return
        if self.returning_since is not None:
            target = self.home_x()
            if target is not None:
                # A spot near the screen edge is closer to it than half the pet's width: the
                # nearest the pet's middle can get is close enough.
                left, _top, right, _bottom = self.motion.bounds
                half = self.motion.width / 2
                target = min(max(target, left + half), right - half)
            late = (self._clock() - self.returning_since) * 1000 >= RETURN_TIMEOUT_MS
            grounded = not self.motion._airborne and not self.motion.on_platform \
                and self.motion.surface == SURFACE_FLOOR
            centre = self.motion.x + self.motion.width / 2
            if target is None or late or (grounded and abs(centre - target) <= SPEED + 2):
                self.close()
                return
            if grounded:
                self.motion.set_follow(target)
        else:
            self._tick += 1
            if self._tick % PLATFORM_EVERY == 1:
                exclude = tuple(int(widget.winId()) for widget in self.strip.home_windows())
                self.motion.set_platforms(self._platforms(exclude_hwnds=exclude))
        x, y = self.motion.step()
        self.move(x, y)
        self.update()

    # ----- drawing --------------------------------------------------------------------------

    def showEvent(self, event) -> None:
        super().showEvent(event)
        capture_affinity.follow(self)

    def paintEvent(self, _event) -> None:
        renderer = self.strip.art.renderer(self.identifier) if self.strip.art is not None else None
        if renderer is None:
            return
        elapsed = 0 if self.strip.reduced_motion else int((self._clock() - self._started) * 1000)
        try:
            frame = renderer.render(outing_action(self.motion, renderer, self._dragging), elapsed,
                                    mirrored=self.motion.facing_left)
        except (KeyError, ValueError):
            return
        painter = QPainter(self)
        painter.drawImage(QRectF(self.rect()), frame)
        painter.end()

    # ----- the mouse: the strip's own card, menu and pat --------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = event.globalPosition()
            self._grab = event.position()
            self._delta = QPointF()
        elif event.button() == Qt.MouseButton.RightButton:
            self.menu(event.globalPosition().toPoint())

    def event(self, event) -> bool:
        # The mouse was taken away mid-drag (a menu, the lock screen): no release will come.
        if event.type() == QEvent.Type.UngrabMouse and getattr(self, "_press", None) is not None:
            self._press = None
            if self._dragging:
                self._dragging = False
                self.motion.throw(0.0, 0.0)
        return super().event(event)

    def mouseMoveEvent(self, event) -> None:
        if self._press is None:
            return
        where = event.globalPosition()
        if not self._dragging and (where - self._press).manhattanLength() < DRAG_START_PX:
            return
        self._dragging = True
        target = where - self._grab
        self._delta = target - QPointF(self.pos())
        self.move(target.toPoint())
        self.motion.x, self.motion.y = float(self.x()), float(self.y())
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._press is None:
            return
        self._press = None
        if self._dragging:
            self._dragging = False
            self.motion.throw(self._delta.x() * THROW_SCALE, self._delta.y() * THROW_SCALE)
            return
        strip = self.strip
        strip.chosen = self.identifier
        strip.refresh_info()
        strip.resident_selected.emit(self.identifier)
        strip.show_card(self.identifier, event.globalPosition().toPoint())

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = None
            self.strip._interact(self.identifier, "pat")

    def menu(self, where: QPoint) -> QMenu:
        """*Come home* first, then the strip's usual menu for this pet."""
        strip, identifier = self.strip, self.identifier
        menu = QMenu(self)
        menu.addAction(translate("pet_home_call_home", "Come home"),
                       lambda: strip.service.run(lambda world: world.call_home(identifier)))
        menu.addSeparator()
        local = strip.mapFromGlobal(where)
        width = strip.service.world.zones[strip.zone].width_pixels if strip.service.world else 0
        strip._menu_x_milli = max(0, min(width * 1000 - 1, int(strip.x_cell(local.x()) * CELL_PIXELS * 1000)))
        strip._resident_menu(menu, identifier)
        self.last_menu = menu
        menu.aboutToHide.connect(menu.deleteLater)
        menu.popup(where)
        return menu

    def set_layer(self, layer: str) -> None:
        visible = self.isVisible()
        self.setWindowFlags(home_flags(layer))
        if visible:
            self.show()

    def closeEvent(self, event) -> None:
        self.timer.stop()
        self.closed.emit(self.identifier)
        super().closeEvent(event)
