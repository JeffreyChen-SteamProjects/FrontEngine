"""The Pet home page: the home overview plus residents, furniture, shop and work.

Opening the page never creates a home and never starts anything with a side
effect: it reads the save (or reports why it cannot) and waits. A home that
was running when FrontEngine closed starts again when the page is built.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from os import getcwd
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtWidgets import QLabel, QPushButton

from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.home_view import HomeView
from frontengine.ui.page.layout_kit import SettingPage
from frontengine.ui.page.pet_game.home_panels import (
    LayoutPanel, ResidentPanel, ShopPanel, WorkPanel, result_text,
)
from frontengine.user_setting.pet_game_save import HomeSaveStore
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.multi_language.retranslate import retranslator, translate, tr
from frontengine.utils.pet_game.catalog import CELL_PIXELS, builtin_catalog
from frontengine.utils.pet_game.schedule import clock_text, game_day

RUNNING_KEY = "pet_home_running"


def default_service(parent) -> HomeService:
    store = HomeSaveStore(Path(getcwd()), builtin_catalog())
    return HomeService(parent, store, PetProfiles(user_setting_dict, write_user_setting),
                       executor=ThreadPoolExecutor(1, thread_name_prefix="pet-home-save"))


class PetHomePage(SettingPage):
    def __init__(self, service: HomeService | None = None) -> None:
        super().__init__("pet_home_title", "pet_home_subtitle", "Pet home",
                         "Your pets live, work and rest in a small home of their own.")
        self.service = service or default_service(self)
        self.profiles = self.service.profiles
        self.selected_resident: str | None = None
        self.selected_furniture: str | None = None
        self._build_status()
        self.view = HomeView()
        self.add_body_widget(self.view)
        self.residents = ResidentPanel(self)
        self.layout_panel = LayoutPanel(self)
        self.shop = ShopPanel(self)
        self.work = WorkPanel(self)
        self.finish_body()
        self._connect()
        self.load_result = self.service.open()
        if self.service.world is not None and user_setting_dict.get(RUNNING_KEY) is True:
            self.service.start()
        retranslator.bind_call(self.refresh)
        self.refresh()

    @property
    def zone(self) -> str | None:
        world = self.service.world
        return next(iter(world.zones), None) if world is not None else None

    def _build_status(self) -> None:
        section = self.add_section("pet_home_status_section", "Home")
        self.status = QLabel()
        self.status.setWordWrap(True)
        section.add_widget(self.status)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        section.add_widget(self.message)
        self.create_button = tr(QPushButton(), "pet_home_create", "Create a home")
        self.create_button.clicked.connect(self.create_home)
        self.run_button = tr(QPushButton(), "pet_home_start", "Start")
        self.run_button.clicked.connect(self.toggle_running)
        self.restore_button = tr(QPushButton(), "pet_home_restore_backup", "Restore the backup")
        self.restore_button.clicked.connect(self.restore_backup)
        self.aside_button = tr(QPushButton(), "pet_home_set_aside", "Keep the old file and start over")
        self.aside_button.clicked.connect(self.set_aside)
        section.add_inline(self.create_button, self.run_button, self.restore_button, self.aside_button)

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
            self.service.create_home((screen.name() or "primary")[:128], area.x(), area.bottom(), width)
        except (OSError, ValueError) as error:
            self.report_text(str(error))
            return
        self._set_running(True)
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
        return self.service.shutdown()

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

    def _on_events(self, events: list) -> None:
        kinds = {event["kind"] for event in events}
        if kinds & {"settled", "placed", "arrived", "settle_failed"}:
            self.refresh()

    def _on_save_failed(self, error: str) -> None:
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
        for panel in (self.residents, self.layout_panel, self.shop, self.work):
            panel.refresh_lists()
        self.refresh_live()

    def refresh_live(self) -> None:
        """Cheap per-tick update of the numbers and the drawing."""
        self._refresh_status()
        self.residents.refresh_live()
        self.work.refresh_live()
        self.view.update()

    def _refresh_status(self) -> None:
        world = self.service.world
        has_home = world is not None
        protected = self.load_result.status in ("corrupt", "newer") and not has_home
        self.create_button.setVisible(not has_home and not protected)
        self.run_button.setVisible(has_home)
        self.restore_button.setVisible(protected and self.load_result.backup_available)
        self.aside_button.setVisible(protected)
        for panel in (self.residents, self.layout_panel, self.shop, self.work):
            panel.section.setEnabled(has_home)
        retranslator.set_text(self.run_button, "pet_home_pause" if self.service.running else "pet_home_start",
                              "Pause" if self.service.running else "Start")
        if protected:
            key = "pet_home_newer" if self.load_result.status == "newer" else "pet_home_corrupt"
            self.status.setText(translate(key, "The home save could not be read. It has not been changed."))
        elif not has_home:
            self.status.setText(translate("pet_home_create_hint", "No home yet."))
        else:
            state = translate("pet_home_running" if self.service.running else "pet_home_paused")
            self.status.setText(translate("pet_home_status", "Day {day} · {time} · {coins} coins · {state}")
                                .format(day=game_day(world.time_ms), time=clock_text(world.time_ms),
                                        coins=world.ledger.coins, state=state))
