"""The Pet home page: the home overview as a stage, with residents, work, furniture, shop,
backpack, goals, inbox and settings in tabs underneath.

Opening the page never creates a home and never starts anything with a side
effect: it reads the save (or reports why it cannot) and waits. A home that
was running when FrontEngine closed starts again when the page is built.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from os import getcwd
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtWidgets import QCheckBox, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget

from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.home_strip import HIDDEN_REASON, HOME_MODES, LAYERS, HomeStrip
from frontengine.show.pet_game.home_view import HomeView
from frontengine.show.pet_game.resident_art import ResidentArt
from frontengine.show.pet_game.themes import glyph
from frontengine.utils.pet_game.environment import weather
from frontengine.ui.page.layout_kit import Section, SettingPage
from frontengine.ui.page.pet_game.home_stage import EmptyHome, HomeTabs, TAB_ORDER, make_tab_ready
from frontengine.ui.page.pet_game.home_panels import (
    LayoutPanel, ResidentPanel, ShopPanel, StoragePanel, WorkPanel,
)
from frontengine.show.pet_game.captions import result_text
from frontengine.ui.page.pet_game.goals_panel import GoalsPanel
from frontengine.ui.page.pet_game.inbox_panel import InboxPanel
from frontengine.user_setting.pet_game_save import HomeSaveStore
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.multi_language.retranslate import retranslator, translate, tr
from frontengine.utils.pet_game.catalog import CELL_PIXELS, builtin_catalog
from frontengine.utils.pet_game.schedule import clock_text, game_day

RUNNING_KEY = "pet_home_running"
DESKTOP_KEY = "pet_home_on_desktop"
INTRO_KEY = "pet_home_intro_seen"
MOTION_KEY = "pet_home_reduced_motion"
MODE_KEY = "pet_home_mode"
MEETING_REASON = "meeting"
# The overview on this page is a stage, taller than the desktop strip.
STAGE_HEIGHT = 220
LAYER_KEY = "pet_home_layer"


def default_service(parent) -> HomeService:
    store = HomeSaveStore(Path(getcwd()), builtin_catalog())
    return HomeService(parent, store, PetProfiles(user_setting_dict, write_user_setting),
                       executor=ThreadPoolExecutor(1, thread_name_prefix="pet-home-save"))


class PetHomePage(SettingPage):
    open_requested = Signal()

    def __init__(self, service: HomeService | None = None) -> None:
        super().__init__("pet_home_title", "pet_home_subtitle", "Pet home",
                         "Your pets live, work and rest in a small home of their own.", wide=True)
        self.service = service or default_service(self)
        self.profiles = self.service.profiles
        self.selected_resident: str | None = None
        self.selected_furniture: str | None = None
        self.strip_list: list[HomeStrip] = []      # registered with the Control Center
        self.art = ResidentArt(self.service)
        self.art.changed.connect(self._art_changed)
        self._tab_sections: dict | None = None
        self._build_intro()
        self.view = HomeView()
        self.view.setFixedHeight(STAGE_HEIGHT)
        self.view.art = self.art
        self._build_status()
        # Panels ask for sections like any page; on this page they become tabs.
        self._tab_sections = {}
        self.residents = ResidentPanel(self)
        self.goals = GoalsPanel(self)
        self.inbox = InboxPanel(self)
        self.layout_panel = LayoutPanel(self)
        self.shop = ShopPanel(self)
        self.storage = StoragePanel(self)
        self.work = WorkPanel(self)
        self._build_settings()
        self.view.reduced_motion = self.motion_check.isChecked()
        self.tabs = HomeTabs()
        for key in TAB_ORDER:
            fallback, section = self._tab_sections[key]
            self.tabs.add_section(key, fallback, section)
        self._tab_sections = None
        self.add_body_widget(self.tabs)
        self.finish_body()
        self._connect()
        self.load_result = self.service.open()
        if self.service.world is not None and user_setting_dict.get(RUNNING_KEY) is True:
            self.service.start()
        self.sync_strip()
        self.apply_mode()
        retranslator.bind_call(self.refresh)
        self.refresh()

    def add_section(self, title: "str | QLabel", fallback: str = "", *, collapsed: bool = False) -> Section:
        """While the panels are built, their sections are collected for the tabs instead of stacked."""
        if self._tab_sections is None or not isinstance(title, str):
            return super().add_section(title, fallback, collapsed=collapsed)
        section = Section(title, fallback)
        make_tab_ready(section)
        self._tab_sections[title] = (fallback, section)
        return section

    @property
    def zone(self) -> str | None:
        world = self.service.world
        return next(iter(world.zones), None) if world is not None else None

    def _build_intro(self) -> None:
        """Shown once: where the old tools went, and that none of them needs a home."""
        section = self.intro_section = self.add_section("pet_home_intro_title", "Welcome to the pet home")
        text = tr(QLabel(), "pet_home_intro", "FrontEngine now opens on your pets' home.")
        text.setWordWrap(True)
        section.add_widget(text)
        done = tr(QPushButton(), "pet_home_intro_ok", "Got it")
        done.clicked.connect(self.dismiss_intro)
        section.add_inline(done)
        section.setVisible(user_setting_dict.get(INTRO_KEY) is not True)

    def dismiss_intro(self) -> None:
        user_setting_dict[INTRO_KEY] = True
        self.intro_section.setVisible(False)

    def _build_status(self) -> None:
        """The stage: what is happening in the home, its controls, and the home itself."""
        section = self.stage = self.add_section("pet_home_status_section", "Home")
        section.title_label.hide()             # the page title already says it
        self.status = QLabel()
        self.status.setObjectName("homeStatus")
        self.status.setWordWrap(True)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.message.hide()                    # shown only while it has something to say
        self.create_button = tr(QPushButton(), "pet_home_create", "Create a home")
        self.create_button.clicked.connect(self.create_home)
        self.run_button = tr(QPushButton(), "pet_home_start", "Start")
        self.run_button.clicked.connect(self.toggle_running)
        self.restore_button = tr(QPushButton(), "pet_home_restore_backup", "Restore the backup")
        self.restore_button.clicked.connect(self.restore_backup)
        self.aside_button = tr(QPushButton(), "pet_home_set_aside", "Keep the old file and start over")
        self.aside_button.clicked.connect(self.set_aside)
        for button in (self.create_button, self.run_button):
            button.setObjectName("primaryAction")
        # One line on top of the stage: what is happening on the left, what you can do on the right.
        bar = QWidget()
        bar.setObjectName("inlineActions")
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        row.addWidget(self.status, 1)
        for button in (self.restore_button, self.aside_button, self.create_button, self.run_button):
            row.addWidget(button)
        section.add_widget(bar)
        section.add_widget(self.message)
        self.empty_home = EmptyHome()
        section.add_widget(self.empty_home)
        self.view_area = self._scroller(self.view)
        section.add_widget(self.view_area)

    def _build_settings(self) -> None:
        """How the home behaves on the desktop: a tab of its own, out of the way of playing."""
        section = self.add_section("pet_home_settings_section", "Settings")
        self.desktop_check = tr(QCheckBox(), "pet_home_on_desktop", "Show the home on the desktop")
        self.desktop_check.setChecked(user_setting_dict.get(DESKTOP_KEY, True) is not False)
        self.desktop_check.toggled.connect(self._desktop_toggled)
        section.add_widget(self.desktop_check)
        self.motion_check = tr(QCheckBox(), "pet_home_reduced_motion", "Reduce motion")
        self.motion_check.setChecked(user_setting_dict.get(MOTION_KEY) is True)
        self.motion_check.toggled.connect(self._motion_toggled)
        section.add_widget(self.motion_check)
        where = tr(QLabel(), "pet_home_settings_strip_hint",
                   "Mode and layer are on the desktop strip's ⌂ menu; meeting mode turns on by itself while "
                   "the screen is shared.")
        where.setWordWrap(True)
        section.add_widget(where)

    @staticmethod
    def _scroller(view: HomeView) -> QScrollArea:
        """Scroll a home wider than the page sideways; its height never changes."""
        area = QScrollArea()
        area.setWidget(view)
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        area.setFixedHeight(view.height() + area.horizontalScrollBar().sizeHint().height() + 2)
        return area

    def _connect(self) -> None:
        self.service.ticked.connect(self.refresh_live)
        self.service.events_ready.connect(self._on_events)
        self.service.save_failed.connect(self._on_save_failed)
        self.service.running_changed.connect(lambda _running: self._refresh_status())
        self.view.resident_selected.connect(self.select_resident)
        self.view.furniture_selected.connect(self.select_furniture)
        self.view.cell_clicked.connect(self.layout_panel.cell_clicked)

    # ----- home lifecycle ------------------------------------------------------------

    def create_home(self) -> None:
        if self.service.world is not None or self.service.store.read_only:
            return
        screen = QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        width = max(16, min(60, area.width() // CELL_PIXELS))
        try:
            self.service.create_home((screen.name() or "primary")[:128], area.x(), area.bottom(), width,
                                     furnish=True)
        except (OSError, ValueError) as error:
            self.report_text(str(error))
            return
        self._set_running(True)
        self.sync_strip()
        self.refresh()

    def toggle_running(self) -> None:
        self._set_running(not self.service.running)

    def _set_running(self, running: bool) -> None:
        if running:
            self.service.start()
        else:
            self.service.pause("stopped")
        user_setting_dict[RUNNING_KEY] = running
        self._refresh_status()

    def restore_backup(self) -> None:
        result = self.service.restore_backup()
        self.load_result = result
        self.report_text("" if result.world is not None else result.error)
        self.refresh()

    def set_aside(self) -> None:
        from datetime import datetime
        try:
            kept = self.service.store.set_aside("kept" + datetime.now().strftime("%Y%m%d%H%M%S"))
        except OSError as error:
            self.report_text(str(error))
            return
        self.load_result = self.service.store.load()
        self.report_text(translate("pet_home_kept_as", "The old file was kept as {name}.").format(
            name=kept.name if kept else "-"))
        self.refresh()

    def shutdown(self) -> bool:
        for dialog in list(self.residents.wardrobes.values()):
            dialog.close()
        self.close_strip()
        return self.service.shutdown()

    # ----- desktop strip ---------------------------------------------------------------

    @property
    def layer(self) -> str:
        layer = user_setting_dict.get(LAYER_KEY, "top")
        return layer if layer in LAYERS else "top"

    def sync_strip(self) -> None:
        """Show the home on the desktop when there is a home and the user wants it there."""
        wanted = self.service.world is not None and self.desktop_check.isChecked()
        if wanted and not self.strip_list:
            strip = HomeStrip(self.service, self.zone, self.layer, str(user_setting_dict.get("quality_tier", "")))
            strip.open_requested.connect(self.open_requested.emit)
            strip.layer_requested.connect(self.choose_layer)
            strip.resident_selected.connect(self.select_resident)
            strip.cell_clicked.connect(self.layout_panel.cell_clicked)
            strip.closed.connect(lambda s=strip: self._forget_strip(s))
            strip.set_arranging(self.layout_panel.arranging)
            self.strip_list.append(strip)
            strip.reduced_motion = self.motion_check.isChecked()
            strip.art = self.art
            strip.mode_requested.connect(self.set_mode)
            strip.show()
            self.apply_mode()
        elif not wanted:
            self.close_strip()

    def _art_changed(self) -> None:
        """A character finished loading or changed outfit: redraw and refit the desktop input mask."""
        self.view.update()
        for strip in self.strip_list:
            strip.update_mask()
            strip.update()

    def _forget_strip(self, strip: HomeStrip) -> None:
        if strip in self.strip_list:
            self.strip_list.remove(strip)

    def close_strip(self) -> None:
        for strip in list(self.strip_list):
            strip.close()
        self.strip_list.clear()

    @property
    def mode(self) -> str:
        mode = user_setting_dict.get(MODE_KEY, "normal")
        return mode if mode in HOME_MODES else "normal"

    def set_mode(self, mode: str) -> None:
        """Normal; focus (quiet strip); meeting (hidden and paused); saver (slow drawing, same time)."""
        if mode not in HOME_MODES:
            return
        user_setting_dict[MODE_KEY] = mode
        self._sharing_meeting = False
        self.apply_mode()

    def apply_mode(self) -> None:
        mode = getattr(self, "_effective_mode", None) or self.mode
        if mode == "meeting":
            self.service.pause(MEETING_REASON)
        else:
            self.service.resume(MEETING_REASON)
        tier = "saver" if mode == "saver" else str(user_setting_dict.get("quality_tier", ""))
        for strip in self.strip_list:
            strip.quiet = mode in ("focus", "meeting")
            strip.set_quality_tier(tier)
            strip.setVisible(mode != "meeting")
        self._refresh_status()

    def sharing_changed(self, sharing: bool) -> None:
        """Screen sharing puts the home into meeting mode for as long as it lasts."""
        self._effective_mode = "meeting" if sharing else None
        self.apply_mode()

    def _motion_toggled(self, checked: bool) -> None:
        user_setting_dict[MOTION_KEY] = checked
        self.apply_motion()

    def apply_motion(self) -> None:
        """Reduced motion: residents jump between world steps and the rain stands still."""
        reduced = self.motion_check.isChecked()
        for view in (self.view, *self.strip_list):
            view.reduced_motion = reduced
            view.update()

    def _desktop_toggled(self, checked: bool) -> None:
        user_setting_dict[DESKTOP_KEY] = checked
        self.sync_strip()

    def choose_layer(self, layer: str) -> None:
        if layer not in LAYERS:
            return
        user_setting_dict[LAYER_KEY] = layer
        for strip in self.strip_list:
            strip.set_layer(layer)

    def set_preview(self, preview) -> None:
        self.view.set_preview(preview)
        for strip in self.strip_list:
            strip.set_preview(preview)

    def set_arranging(self, arranging: bool) -> None:
        for strip in self.strip_list:
            strip.set_arranging(arranging)

    # ----- selection and feedback --------------------------------------------------------

    def select_resident(self, identifier: str | None) -> None:
        self.selected_resident = identifier
        self.view.set_selected(identifier or self.selected_furniture)
        self.residents.refresh_lists()
        self.residents.refresh_live()

    def select_furniture(self, identifier: str | None) -> None:
        self.selected_furniture = identifier
        self.view.set_selected(identifier)
        self.layout_panel.refresh_lists()

    def report(self, code: object) -> None:
        self.report_text(result_text(code) if isinstance(code, str) else "")

    def report_text(self, text: str) -> None:
        self.message.setText(text)
        self.message.setVisible(bool(text))

    def _on_events(self, events: list) -> None:
        self.inbox.on_events(events, self.service.world)
        kinds = {event["kind"] for event in events}
        if kinds & {"settled", "placed", "arrived", "settle_failed", "life_event", "wish_granted",
                    "goal_claimed", "commission_done", "bought", "routine_set"}:
            self.refresh()

    def _on_save_failed(self, error: str) -> None:
        world = self.service.world
        self.inbox.add_error(translate("pet_home_save_failed", "The home could not be saved ({error}).")
                             .format(error=error), world.time_ms if world else 0)
        self.report_text(translate("pet_home_save_failed",
                                   "The home could not be saved ({error}). It will retry; nothing is lost yet.")
                         .format(error=error))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and self.layout_panel.arranging:
            self.layout_panel.toggle_arrange()
            event.accept()
            return
        super().keyPressEvent(event)

    # ----- refresh -------------------------------------------------------------------------

    def refresh(self) -> None:
        """Rebuild lists (after commands, events and language changes)."""
        self.view.set_world(self.service.world, self.zone)
        for panel in (self.residents, self.goals, self.layout_panel, self.shop, self.storage, self.work):
            panel.refresh_lists()
        self.refresh_live()
        for strip in self.strip_list:         # a new pet or piece must take clicks even while paused
            strip.update_mask()

    def refresh_live(self) -> None:
        """Cheap per-tick update of the numbers and the drawing."""
        self._refresh_status()
        self.residents.refresh_live()
        self.work.refresh_live()
        self.view.update()

    @staticmethod
    def _time_text(world) -> str:
        current = weather(world.home, world.time_ms)
        return (f"{clock_text(world.time_ms)} {glyph(world.home, world.time_ms)} "
                f"{translate('pet_game_weather_' + current, current)}")

    def _refresh_status(self) -> None:
        world = self.service.world
        has_home = world is not None
        protected = self.load_result.status in ("corrupt", "newer") and not has_home
        self.create_button.setVisible(not has_home and not protected)
        self.run_button.setVisible(has_home)
        self.restore_button.setVisible(protected and self.load_result.backup_available)
        self.aside_button.setVisible(protected)
        for panel in (self.residents, self.goals, self.layout_panel, self.shop, self.storage, self.work):
            panel.section.setEnabled(has_home)
        self.empty_home.setVisible(not has_home)
        self.view_area.setVisible(has_home)
        self.tabs.setVisible(has_home)
        self.desktop_check.setEnabled(has_home)
        retranslator.set_text(self.run_button, "pet_home_pause" if self.service.running else "pet_home_start",
                              "Pause" if self.service.running else "Start")
        self.status.setText(self._status_text(world, protected))

    def _status_text(self, world, protected: bool) -> str:
        if protected:
            key = "pet_home_newer" if self.load_result.status == "newer" else "pet_home_corrupt"
            return translate(key, "The home save could not be read. It has not been changed.")
        if world is None:
            return translate("pet_home_create_hint", "No home yet.")
        state = translate("pet_home_running" if self.service.running else "pet_home_paused")
        if MEETING_REASON in self.service.pause_reasons:
            state = translate("pet_home_paused_meeting", "paused for a meeting")
        elif HIDDEN_REASON in self.service.pause_reasons:
            state = translate("pet_home_paused_hidden", "paused while the home is hidden")
        return translate("pet_home_status", "Day {day} · {time} · {coins} coins · {state}").format(
            day=game_day(world.time_ms), time=self._time_text(world), coins=world.ledger.coins, state=state)
