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

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication, QKeyEvent, QKeySequence
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QPushButton, QScrollArea, QSlider, QVBoxLayout, QWidget)

from frontengine.show.pet_game.ambience import DEFAULT_VOLUME, Ambience
from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.home_strip import (
    DEFAULT_SCALE, HIDDEN_REASON, HOME_MODES, LAYERS, LOCKED_REASON, SCALES, HomeStrip,
)
from frontengine.show.pet_game.home_view import HomeView
from frontengine.show.pet_game.resident_art import ResidentArt
from frontengine.show.pet_game.themes import glyph
from frontengine.utils.pet_game.environment import season, weather
from frontengine.show.pet_game.home_view import ZOOMS
from frontengine.utils.pet_game.world import MODES
from frontengine.ui.dialog.dialog_kit import button_row
from frontengine.ui.page.layout_kit import Section, SettingPage
from frontengine.ui.page.pet_game.collection_panel import CollectionPanel
from frontengine.ui.page.pet_game.home_pending import pending
from frontengine.utils.browser.browser import open_browser
from frontengine.utils.session_lock.session_lock import SessionLockWatcher
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
from frontengine.utils.pet_game.catalog import CELL_PIXELS
from frontengine.utils.pet_game.content_pack import PACK_FOLDER, catalog_with_packs, load_packs
from frontengine.show.pet_game.furniture_art import register_pack_pictures
from frontengine.show.pet_game.themes import register_themes
from frontengine.utils.workshop.workshop_content import find_workshop_dir, home_pack_roots
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.pet_game.schedule import clock_text, game_day

RUNNING_KEY = "pet_home_running"
DESKTOP_KEY = "pet_home_on_desktop"
INTRO_KEY = "pet_home_intro_seen"
MOTION_KEY = "pet_home_reduced_motion"
SCALE_KEY = "pet_home_strip_scale"           # desktop strip size in percent (SCALES)
AMBIENT_KEY = "pet_home_ambient"             # ambient sound on (off by default)
AMBIENT_VOLUME_KEY = "pet_home_ambient_volume"   # 0-100, its own volume
MODE_KEY = "pet_home_mode"
MEETING_REASON = "meeting"
SAVE_MODE_KEY = "pet_home_save_mode"      # "manage" or "sandbox" (free arranging), its own save each
# Where a newer FrontEngine comes from, when a save was written by one.
UPDATE_URL = "https://pypi.org/project/frontengine/"
# The overview on this page is a stage, taller than the desktop strip.
STAGE_HEIGHT = 220
LAYER_KEY = "pet_home_layer"


def workshop_pack_roots() -> list[Path]:
    """Furniture and theme packs subscribed on the Steam Workshop, when Steam's folder is there."""
    content = find_workshop_dir()
    return home_pack_roots(content) if content is not None else []


def default_service(parent) -> HomeService:
    mode = user_setting_dict.get(SAVE_MODE_KEY)
    packs, errors = load_packs(Path(getcwd()) / PACK_FOLDER, workshop_pack_roots())
    for name, reason in errors.items():
        front_engine_logger.warning(f"[PetHome] content pack {name} refused: {reason}")
    register_pack_pictures({key: value for pack in packs for key, value in pack.pictures.items()})
    register_themes([theme for pack in packs for theme in pack.themes])
    store = HomeSaveStore(Path(getcwd()), catalog_with_packs(packs), mode if mode in MODES else "manage")
    store.packs, store.pack_errors = packs, errors
    return HomeService(parent, store, PetProfiles(user_setting_dict, write_user_setting),
                       executor=ThreadPoolExecutor(1, thread_name_prefix="pet-home-save"))


def packs_text(store) -> str:
    """Which packs are in use (with source and licence) and why any folder was refused."""
    packs, errors = getattr(store, "packs", []), getattr(store, "pack_errors", {})
    lines = [translate("pet_home_pack_line", "{name} - {count} pieces · {source} · {license}").format(
        name=pack.name, count=len(pack.furniture), source=pack.source, license=pack.license)
        + (" · " + translate("pet_home_pack_themes", "{count} themes").format(count=len(pack.themes))
           if pack.themes else "") for pack in packs]
    lines += [translate("pet_home_pack_refused", "{name} was not loaded: {reason}").format(name=name, reason=reason)
              for name, reason in sorted(errors.items())]
    return "\n".join(lines) or translate("pet_home_no_packs",
                                          "No furniture packs. Put a pack folder in the packs folder and restart.")


class PetHomePage(SettingPage):
    open_requested = Signal()
    desktop_requested = Signal()          # "Back to the desktop": the window steps aside

    def __init__(self, service: HomeService | None = None) -> None:
        super().__init__("pet_home_title", "pet_home_subtitle", "Pet home",
                         "Your pets live, work and rest in a small home of their own.", wide=True)
        self.service = service or default_service(self)
        self.profiles = self.service.profiles
        self.selected_resident: str | None = None
        self.selected_furniture: str | None = None
        self._save_failure_message = False
        self.strip_list: list[HomeStrip] = []      # registered with the Control Center
        self.art = ResidentArt(self.service)
        self.art.changed.connect(self._art_changed)
        self.ambience = Ambience(parent=self)
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
        self.collection = CollectionPanel(self)
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
        """The zone the page shows: the one chosen in the zone menu, else the first."""
        world = self.service.world
        if world is None:
            return None
        if getattr(self, "_zone_id", None) in world.zones:
            return self._zone_id
        return next(iter(world.zones), None)

    @staticmethod
    def screens() -> list:
        """The connected screens (a method so tests can stand in other monitors)."""
        return list(QGuiApplication.screens())

    def choose_zone(self, zone: str | None) -> None:
        self.layout_panel.preview_cell = None
        self.set_preview(None)
        self._zone_id = zone
        self.selected_furniture = None
        self.refresh()

    def free_screens(self) -> list:
        """Connected screens that do not hold a zone yet."""
        world = self.service.world
        taken = {zone.screen for zone in world.zones.values()} if world is not None else set()
        return [screen for screen in self.screens() if (screen.name() or "primary")[:128] not in taken]

    def add_zone(self, screen) -> str | None:
        """A home zone on another screen, as wide as that screen allows."""
        area = screen.availableGeometry()
        width = max(16, min(60, area.width() // CELL_PIXELS))
        name = (screen.name() or "primary")[:128]
        try:
            zone = self.service.run(lambda world: world.add_zone(name, area.x(), area.bottom(), width))
        except ValueError as error:
            self.report_text(str(error))
            return None
        self.choose_zone(zone)
        self.sync_strip()
        return zone

    def move_zone(self, screen) -> str:
        zone, area = self.zone, screen.availableGeometry()
        width = max(16, min(60, area.width() // CELL_PIXELS))
        result = self.service.run(lambda world: world.move_zone(zone, (screen.name() or "primary")[:128],
                                                                area.x(), area.bottom(), width))
        self.report(result)
        self.close_strip()
        self.sync_strip()
        self.refresh()
        return result

    def screens_changed(self, *_args) -> None:
        """A monitor came or went: zones on a missing screen wait, the rest carry on."""
        world = self.service.world
        if world is None:
            return
        names = {(screen.name() or "primary")[:128] for screen in self.screens()}
        offline = {key for key, zone in world.zones.items() if zone.screen not in names}
        if offline != world.offline_zones:
            self.service.run(lambda w: w.set_offline(offline))
        self.close_strip()
        self.sync_strip()
        self.refresh()

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
        self.update_button = tr(QPushButton(), "pet_home_get_update", "Get the latest FrontEngine")
        self.update_button.clicked.connect(lambda: open_browser(UPDATE_URL))
        for button in (self.create_button, self.run_button):
            button.setObjectName("primaryAction")
        # One line on top of the stage: what is happening on the left, what you can do on the right.
        bar = QWidget()
        bar.setObjectName("inlineActions")
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        row.addWidget(self.status, 1)
        self.sandbox_button = tr(QPushButton(), "pet_home_free_arranging", "Free arranging")
        self.sandbox_button.setCheckable(True)
        self.sandbox_button.setChecked(self.service.mode == "sandbox")
        tr(self.sandbox_button, "pet_home_free_arranging_hint",
           "A separate home with every piece of furniture and no costs; nothing done there reaches your "
           "home, coins, goals or pets.", "setToolTip")
        self.sandbox_button.toggled.connect(self.set_free_arranging)
        for button in (self.sandbox_button, self.update_button, self.restore_button, self.aside_button,
                       self.create_button, self.run_button):
            row.addWidget(button)
        section.add_widget(bar)
        section.add_widget(self.message)
        self.empty_home = EmptyHome()
        section.add_widget(self.empty_home)
        self.newcomers_box = QWidget()
        box = QVBoxLayout(self.newcomers_box)
        box.setContentsMargins(0, 0, 0, 0)
        caption = tr(QLabel(), "pet_home_newcomers", "Pets moving in with you (tick the ones you want)")
        caption.setWordWrap(True)
        self.newcomers = QListWidget()
        self.newcomers.setMaximumHeight(140)
        caption.setBuddy(self.newcomers)
        box.addWidget(caption)
        box.addWidget(self.newcomers)
        section.add_widget(self.newcomers_box)
        self.view_area = self._scroller(self.view)
        self.view.zoomable = True
        self.view.zoom_changed.connect(self._zoom_changed)
        section.add_widget(self.view_area)
        self._build_shortcuts(section)

    def _build_shortcuts(self, section) -> None:
        """Under the stage: where to go next, what is waiting, and the zoom."""
        self.desktop_button = tr(QPushButton(), "pet_home_back_to_desktop", "Back to the desktop")
        self.desktop_button.clicked.connect(self.desktop_requested.emit)
        self.backpack_button = tr(QPushButton(), "pet_home_storage_section", "Backpack")
        self.backpack_button.clicked.connect(lambda: self.tabs.select("pet_home_storage_section"))
        self.goals_button = tr(QPushButton(), "pet_home_goals_section", "Goals")
        self.goals_button.clicked.connect(lambda: self.tabs.select("pet_home_goals_section"))
        self.zoom_out = QPushButton("−")
        self.zoom_in = QPushButton("+")
        for button, steps, key, fallback in ((self.zoom_out, -1, "pet_home_zoom_out", "Zoom out"),
                                             (self.zoom_in, 1, "pet_home_zoom_in", "Zoom in")):
            tr(button, key, fallback, "setToolTip")
            tr(button, key, fallback, "setAccessibleName")
            button.setFixedWidth(40)
            button.clicked.connect(lambda _checked=False, s=steps: self.view.step_zoom(s))
        self.shortcuts = button_row(self.desktop_button, self.backpack_button, self.goals_button)
        self.zone_combo = QComboBox()
        tr(self.zone_combo, "pet_home_zone", "Zone", "setAccessibleName")
        self.zone_combo.activated.connect(lambda _index: self.choose_zone(self.zone_combo.currentData()))
        self.shortcuts.layout().addWidget(self.zone_combo)
        self.shortcuts.layout().addWidget(self.zoom_out)
        self.shortcuts.layout().addWidget(self.zoom_in)
        section.add_widget(self.shortcuts)
        self.pending_box = QWidget()
        self.pending_box.setObjectName("inlineActions")
        box = QVBoxLayout(self.pending_box)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(4)
        box.addWidget(tr(QLabel(), "pet_home_pending", "Waiting for you"))
        self.pending_list = QListWidget()
        self.pending_list.setObjectName("pendingList")
        self.pending_list.itemActivated.connect(self._open_pending)
        self.pending_list.itemClicked.connect(self._open_pending)
        box.addWidget(self.pending_list)
        section.add_widget(self.pending_box)

    def _refresh_zone_combo(self, world) -> None:
        zones = list(world.zones.values()) if world is not None else []
        items = [(zone.identifier, zone.screen + (" · " + translate("pet_home_zone_offline", "screen not connected")
                                                    if zone.identifier in world.offline_zones else ""))
                 for zone in zones]
        if [(self.zone_combo.itemData(i), self.zone_combo.itemText(i)) for i in range(self.zone_combo.count())] != items:
            self.zone_combo.clear()
            for key, text in items:
                self.zone_combo.addItem(text, key)
        self.zone_combo.setCurrentIndex(max(0, self.zone_combo.findData(self.zone)))
        self.zone_combo.setVisible(len(zones) > 1)

    def _open_pending(self, item) -> None:
        self.tabs.select(item.data(Qt.ItemDataRole.UserRole))

    def _refresh_pending(self) -> None:
        items = pending(self.service.world, self.inbox.unread)
        texts = [text for text, _key in items]
        if [self.pending_list.item(row).text() for row in range(self.pending_list.count())] == texts:
            return
        self.pending_list.clear()
        for text, key in items:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.pending_list.addItem(item)
        rows = max(1, len(items))
        row = self.pending_list.sizeHintForRow(0) if items else self.pending_list.fontMetrics().height() + 12
        self.pending_list.setFixedHeight(rows * max(row, 1) + 2 * self.pending_list.frameWidth() + 12)

    def _zoom_changed(self, zoom: float) -> None:
        self.view.setFixedHeight(round(STAGE_HEIGHT * zoom))
        self.view_area.setFixedHeight(self.view.height() + self.view_area.horizontalScrollBar().sizeHint().height() + 2)
        self.zoom_out.setEnabled(zoom > ZOOMS[0])
        self.zoom_in.setEnabled(zoom < ZOOMS[-1])

    def _build_settings(self) -> None:
        """How the home behaves on the desktop: a tab of its own, out of the way of playing."""
        section = self.add_section("pet_home_settings_section", "Settings")
        self.desktop_check = tr(QCheckBox(), "pet_home_on_desktop", "Show the home on the desktop")
        self.desktop_check.setChecked(user_setting_dict.get(DESKTOP_KEY, True) is not False)
        self.desktop_check.toggled.connect(self._desktop_toggled)
        section.add_widget(self.desktop_check)
        self.mode_combo = QComboBox()
        for index, mode in enumerate(HOME_MODES):
            self.mode_combo.addItem('', mode)
            retranslator.bind(self.mode_combo, 'pet_home_mode_' + mode, mode, 'setItemText', index)
        self.mode_combo.setCurrentIndex(self.mode_combo.findData(self.mode))
        self.mode_combo.activated.connect(lambda _index: self.set_mode(self.mode_combo.currentData()))
        section.add_row('pet_home_mode', self.mode_combo, 'Mode')
        self.motion_check = tr(QCheckBox(), "pet_home_reduced_motion", "Reduce motion")
        self.motion_check.setChecked(user_setting_dict.get(MOTION_KEY) is True)
        self.motion_check.toggled.connect(self._motion_toggled)
        section.add_widget(self.motion_check)
        self.scale_combo = QComboBox()
        for percent in SCALES:
            self.scale_combo.addItem(f"{percent}%", percent)
        self.scale_combo.setCurrentIndex(SCALES.index(self.strip_scale))
        self.scale_combo.activated.connect(lambda _index: self.set_strip_scale(self.scale_combo.currentData()))
        section.add_row("pet_home_strip_size_setting", self.scale_combo, "Size on the desktop")
        hint = tr(QLabel(), "pet_home_strip_size_hint",
                  "Ctrl + mouse wheel over a pet or piece on the desktop also changes it.")
        hint.setWordWrap(True)
        section.add_widget(hint)
        self._build_ambience_settings(section)
        where = tr(QLabel(), "pet_home_settings_strip_hint",
                   "Mode and layer are on the desktop strip's ⌂ menu; meeting mode turns on by itself while "
                   "the screen is shared.")
        where.setWordWrap(True)
        section.add_widget(where)
        self.packs_label = QLabel()
        self.packs_label.setWordWrap(True)
        section.add_widget(self.packs_label, "pet_home_packs", "Furniture packs")
        self.packs_button = tr(QPushButton(), "pet_home_open_packs", "Open the packs folder")
        self.packs_button.clicked.connect(self.open_packs_folder)
        section.add_inline(self.packs_button)

    def _build_ambience_settings(self, section: Section) -> None:
        """Ambient sound: off unless chosen, with a volume of its own that nothing else shares."""
        self.ambient_check = tr(QCheckBox(), "pet_home_ambient", "Ambient sound (birds, crickets, rain)")
        self.ambient_check.setChecked(user_setting_dict.get(AMBIENT_KEY) is True)
        self.ambient_check.toggled.connect(self._ambient_toggled)
        section.add_widget(self.ambient_check)
        volume = user_setting_dict.get(AMBIENT_VOLUME_KEY, DEFAULT_VOLUME)
        volume = volume if type(volume) is int and 0 <= volume <= 100 else DEFAULT_VOLUME
        self.ambient_slider = QSlider(Qt.Orientation.Horizontal)
        self.ambient_slider.setRange(0, 100)
        self.ambient_slider.setValue(volume)
        self.ambient_value = QLabel(f"{volume}%")
        self.ambient_slider.valueChanged.connect(self._ambient_volume_changed)
        section.add_slider_row(tr(QLabel(), "pet_home_ambient_volume", "Ambient volume"), self.ambient_slider,
                               self.ambient_value)
        self.ambience.set_enabled(self.ambient_check.isChecked())
        self.ambience.set_volume(volume)
        self.ambient_slider.setEnabled(self.ambient_check.isChecked())

    def _ambient_toggled(self, checked: bool) -> None:
        user_setting_dict[AMBIENT_KEY] = checked
        self.ambient_slider.setEnabled(checked)
        self.ambience.set_enabled(checked)
        self.update_ambience()

    def _ambient_volume_changed(self, value: int) -> None:
        user_setting_dict[AMBIENT_VOLUME_KEY] = value
        self.ambient_value.setText(f"{value}%")
        self.ambience.set_volume(value)
        self.update_ambience()

    def update_ambience(self) -> None:
        world = self.service.world
        self.ambience.update(world.home if world is not None else None, world.time_ms if world is not None else 0,
                             self.service.running)

    def open_packs_folder(self) -> None:
        folder = Path(getcwd()) / PACK_FOLDER
        folder.mkdir(exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

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

    def set_free_arranging(self, free: bool) -> bool:
        """Swap to the free-arranging home (or back); the button follows what really happened."""
        mode = "sandbox" if free else "manage"
        if self.service.mode == mode:
            return True
        if self.layout_panel.arranging:
            self.layout_panel.toggle_arrange()
        result = self.service.switch_mode(mode)
        self.sandbox_button.blockSignals(True)
        self.sandbox_button.setChecked(self.service.mode == "sandbox")
        self.sandbox_button.blockSignals(False)
        if result is None:
            self.report("save_failed")
            return False
        user_setting_dict[SAVE_MODE_KEY] = mode
        self.load_result = result
        self.selected_resident = self.selected_furniture = None
        self.sync_strip()
        self.refresh()
        return True

    def _strip_done_arranging(self) -> None:
        if self.layout_panel.arranging:
            self.layout_panel.toggle_arrange()

    def _connect(self) -> None:
        self.service.ticked.connect(self.refresh_live)
        self.service.events_ready.connect(self._on_events)
        self.lock_watcher = SessionLockWatcher(self)
        self.lock_watcher.locked_changed.connect(self._session_locked)
        self.lock_watcher.start()
        self.service.save_failed.connect(self._on_save_failed)
        self.service.saved.connect(self._on_saved)
        self.service.running_changed.connect(lambda _running: self._refresh_status())
        self.service.running_changed.connect(lambda _running: self.update_ambience())
        self.view.resident_selected.connect(self.select_resident)
        self.view.furniture_selected.connect(self.select_furniture)
        self.view.cell_clicked.connect(self.layout_panel.cell_clicked)
        self.view.piece_hovered.connect(self.layout_panel.drag_hover)
        self.view.piece_dropped.connect(self.layout_panel.drop)
        self.view.edit_cancelled.connect(lambda: self.set_preview(None))
        self.view.area_painted.connect(self.layout_panel.paint_area)
        application = QGuiApplication.instance()
        application.screenAdded.connect(self.screens_changed)
        application.screenRemoved.connect(self.screens_changed)

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
        moved = self.move_in_newcomers()
        first = None
        if not self.service.world.residents and not self.newcomers.count():
            # Nobody to move in yet: a first pet comes along, so the home is never empty to start with.
            first = self.profiles.create()["id"]
            moved = int(self.service.adopt(first) == "accepted")
        if moved:
            self.report_text(translate("pet_home_moved_in", "{count} pets moved in.").format(count=moved))
        self._set_running(True)
        self.sync_strip()
        self.refresh()
        if first is not None and first in self.service.world.residents:
            self.select_resident(first)

    def chosen_newcomers(self) -> list[str]:
        return [self.newcomers.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.newcomers.count())
                if self.newcomers.item(i).checkState() == Qt.CheckState.Checked]

    def move_in_newcomers(self) -> int:
        """The ticked pets move in as themselves (same identity, name, closeness, needs, look and wardrobe).

        Nothing is copied or reset, and running it again later only moves in who is not living
        here yet; the starter kit belongs to the home and is never handed out twice.
        """
        moved = 0
        for identifier in self.chosen_newcomers():
            if self.service.adopt(identifier) == "accepted":
                moved += 1
        return moved

    def _refresh_newcomers(self, has_home: bool) -> None:
        living = set(self.service.world.residents) if has_home else set()
        records = [] if has_home else [r for r in self.profiles.profiles() if r["id"] not in living]
        current = [self.newcomers.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.newcomers.count())]
        if current != [record["id"] for record in records]:
            self.newcomers.clear()
            for record in records:
                item = QListWidgetItem(record["name"])
                item.setData(Qt.ItemDataRole.UserRole, record["id"])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self.newcomers.addItem(item)
        self.newcomers_box.setVisible(bool(records))

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
        if not self.service.shutdown():
            return False
        for dialog in [*self.residents.wardrobes.values(), *self.layout_panel.visits]:
            dialog.close()
        self.close_strip()
        self.lock_watcher.stop()
        self.art.shutdown()
        self.ambience.shutdown()
        return True

    # ----- desktop strip ---------------------------------------------------------------

    @property
    def layer(self) -> str:
        layer = user_setting_dict.get(LAYER_KEY, "top")
        return layer if layer in LAYERS else "top"

    def sync_strip(self) -> None:
        """Show the home on the desktop when there is a home and the user wants it there."""
        world = self.service.world
        wanted = world is not None and self.desktop_check.isChecked()
        zones = [key for key in world.zones if key not in world.offline_zones] if wanted else []
        for strip in [strip for strip in self.strip_list if strip.zone not in zones]:
            strip.close()
            self._forget_strip(strip)
        for zone in [key for key in zones if key not in {strip.zone for strip in self.strip_list}]:
            strip = HomeStrip(self.service, zone, self.layer, str(user_setting_dict.get("quality_tier", "")))
            strip.open_requested.connect(self.open_requested.emit)
            strip.action_requested.connect(lambda action, target, z=zone: self.strip_action(action, target, z))
            strip.arrange_finished.connect(self._strip_done_arranging)
            strip.layer_requested.connect(self.choose_layer)
            strip.resident_selected.connect(self.select_resident)
            strip.cell_clicked.connect(lambda cell, z=zone: self._strip_cell_clicked(z, cell))
            strip.closed.connect(lambda s=strip: self._forget_strip(s))
            strip.set_arranging(self.layout_panel.arranging)
            self.strip_list.append(strip)
            strip.reduced_motion = self.motion_check.isChecked()
            strip.art = self.art
            strip.mode_requested.connect(self.set_mode)
            strip.scale_requested.connect(self.set_strip_scale)
            strip.set_scale(self.strip_scale)
            strip.show()
        if zones:
            self.apply_mode()
        else:
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
        self.mode_combo.setCurrentIndex(self.mode_combo.findData(mode))
        self.mode_combo.setEnabled(not bool(getattr(self, "_effective_mode", None)))
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

    @property
    def strip_scale(self) -> int:
        value = user_setting_dict.get(SCALE_KEY, DEFAULT_SCALE)
        return value if value in SCALES else DEFAULT_SCALE

    def set_strip_scale(self, percent: int) -> None:
        """Bigger or smaller desktop home, remembered; every strip follows at once."""
        if percent not in SCALES:
            return
        user_setting_dict[SCALE_KEY] = percent
        self.scale_combo.setCurrentIndex(SCALES.index(percent))
        for strip in self.strip_list:
            strip.set_scale(percent)

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
            strip.set_preview(preview if strip.zone == self.zone else None)

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
        if identifier is not None:
            self.layout_panel.storage.clearSelection()
        self.selected_furniture = identifier
        self.view.set_selected(identifier)
        self.layout_panel.refresh_lists()

    def report(self, code: object) -> None:
        self.report_text(result_text(code) if isinstance(code, str) else "")
        self._save_failure_message = code == "save_failed"

    def report_text(self, text: str) -> None:
        self._save_failure_message = False
        self.message.setText(text)
        self.message.setVisible(bool(text))

    def focus_phase_changed(self, phase: str) -> None:
        """The focus timer as a schedule request: work while focusing, and only our own requests
        are taken back on a break or when it stops. Nothing reads what you type or punishes a pause."""
        if self.service.world is None:
            return
        if phase == "focus" and self.work.focus_check.isChecked():
            self.service.run(lambda world: world.focus_begin())
        elif phase in ("break", "long_break", "stopped"):
            self.service.run(lambda world: world.focus_end())

    def _session_locked(self, locked: bool) -> None:
        """A locked session pauses the home like hiding it does; unlocking lets it carry on."""
        if locked:
            self.service.pause(LOCKED_REASON)
        else:
            self.service.resume(LOCKED_REASON)
        self._refresh_status()

    def _on_events(self, events: list) -> None:
        self.view.note_events(events)
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
        self._save_failure_message = True

    def _on_saved(self) -> None:
        if self._save_failure_message:
            self.report_text("")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and (self.layout_panel.arranging
                                               or self.layout_panel.area_paint.isChecked()):
            if self.layout_panel.area_paint.isChecked():
                self.layout_panel.area_paint.click()
            if self.layout_panel.arranging:
                self.layout_panel.toggle_arrange()
            event.accept()
            return
        steps = {Qt.Key.Key_Left: -1, Qt.Key.Key_Right: 1}.get(event.key())
        if steps and self.layout_panel.arranging and self.layout_panel.nudge(steps):
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Undo):
            self.layout_panel.undo()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Redo):
            self.layout_panel.redo()
            event.accept()
            return
        super().keyPressEvent(event)

    # ----- refresh -------------------------------------------------------------------------

    def refresh(self) -> None:
        """Rebuild lists (after commands, events and language changes)."""
        self.packs_label.setText(packs_text(self.service.store))
        self.view.set_world(self.service.world, self.zone)
        for panel in (self.residents, self.goals, self.layout_panel, self.shop, self.storage, self.work,
                      self.collection):
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
        self._follow()
        self.update_ambience()

    def _strip_cell_clicked(self, zone: str, cell: int) -> None:
        world = self.service.world
        if world is None or zone not in world.zones:
            return
        if zone != self.zone:
            self.choose_zone(zone)
        self.layout_panel.cell_clicked(cell)

    def strip_action(self, action: str, target: str, zone: str | None = None) -> None:
        """The desktop strip's toolbar and right-click menus: arranging stays on the desktop, the rest opens here."""
        world = self.service.world
        if world is None:
            return
        item = world.furniture.get(target) if action == "move" else world.residents.get(target)
        zone = item.zone if item is not None else zone
        if zone is not None:
            if zone not in world.zones:
                return
            if zone != self.zone:
                self.choose_zone(zone)
        if action in ("arrange", "move"):
            if action == "move":
                self.select_furniture(target)
            if not self.layout_panel.arranging:
                self.layout_panel.toggle_arrange()
            return
        self.open_requested.emit()
        if action == "tab":
            self.tabs.select(target)
            return
        self.select_resident(target)
        if action == "wardrobe":
            self.residents.wardrobe()
        elif action == "work":
            self.tabs.select("pet_home_work_section")
        elif action == "follow":
            self.followed = target
            self._follow()
        elif action == "photo":
            self.photo_of(target)

    def photo_of(self, identifier: str):
        """A photo of one pet from the overview, saved to the album; nothing on the desktop is captured."""
        world = self.service.world
        resident = world.residents.get(identifier) if world is not None else None
        if resident is None:
            return None
        if resident.zone != self.zone:
            self.choose_zone(resident.zone)
        box = self.view.resident_box(resident).adjusted(-70, -40, 70, 12)
        area = box.toAlignedRect().intersected(self.view.rect())
        return self.goals.save_photo(self.view.grab(area), resident.name)

    def _follow(self) -> None:
        """Keep the followed pet in view while the overview is zoomed in; it stops when the pet leaves the zone."""
        world, identifier = self.service.world, getattr(self, "followed", None)
        resident = world.residents.get(identifier) if world is not None and identifier else None
        if resident is None or resident.zone != self.zone:
            self.followed = None
            return
        center = self.view.resident_center(resident)
        self.view_area.ensureVisible(round(center.x()), round(center.y()), self.view_area.width() // 3, 0)

    @staticmethod
    def _time_text(world) -> str:
        current, now = weather(world.home, world.time_ms), season(world.time_ms)
        return (f"{clock_text(world.time_ms)} {glyph(world.home, world.time_ms)} "
                f"{translate('pet_game_weather_' + current, current)} · "
                f"{translate('pet_game_season_' + now, now)}")

    def _refresh_status(self) -> None:
        world = self.service.world
        has_home = world is not None
        protected = self.load_result.status in ("corrupt", "newer") and not has_home
        self.create_button.setVisible(not has_home and not protected)
        self._refresh_newcomers(has_home)
        self.run_button.setVisible(has_home)
        self.restore_button.setVisible(protected and self.load_result.backup_available)
        self.aside_button.setVisible(protected)
        self.update_button.setVisible(self.load_result.status == "newer" and not has_home)
        self.shortcuts.setVisible(has_home)
        self._refresh_pending()
        self.pending_box.setVisible(has_home and self.pending_list.count() > 0)
        self._refresh_zone_combo(world)
        for panel in (self.residents, self.goals, self.layout_panel, self.shop, self.storage, self.work,
                      self.collection):
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
        elif LOCKED_REASON in self.service.pause_reasons:
            state = translate("pet_home_paused_locked", "paused while the computer is locked")
        elif HIDDEN_REASON in self.service.pause_reasons:
            state = translate("pet_home_paused_hidden", "paused while the home is hidden")
        if world.sandbox:
            state = translate("pet_home_free_arranging", "Free arranging") + " · " + state
        return translate("pet_home_status", "Day {day} · {time} · {coins} coins · {state}").format(
            day=game_day(world.time_ms), time=self._time_text(world), coins=world.ledger.coins, state=state)
