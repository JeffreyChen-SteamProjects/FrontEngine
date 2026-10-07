"""Workshop management with lazy Steam initialization and background file work."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout,
)

from frontengine.ui.page.layout_kit import SettingPage
from frontengine.user_setting.preset_repository import PresetRepository
from frontengine.user_setting.scene_setting import adopt_scene_entries
from frontengine.utils.multi_language.retranslate import retranslator, tr, translate
from frontengine.utils.scene_format.scene_package import load_package
from frontengine.utils.workshop.workshop_cache import WorkshopCache
from frontengine.utils.workshop.workshop_jobs import WorkshopJobs
from frontengine.utils.workshop.workshop_publications import PublicationStore
from frontengine.utils.workshop.workshop_publisher import WorkshopPublisher
from frontengine.utils.workshop.workshop_subscriptions import WorkshopSubscriptions


class WorkshopDialog(QDialog):
    def __init__(self, owner, service, storage_root: Path | None = None) -> None:
        super().__init__(owner)
        self.owner, self.service, self.storage_root = owner, service, storage_root
        self.store = self.cache = self.publisher = self.subscriptions = None
        self.jobs = WorkshopJobs(self)
        self.jobs.completed.connect(self._job_done)
        self.jobs.failed.connect(self._job_failed)
        service.stopping.connect(self.jobs.stop)
        service.availability_changed.connect(self._availability)
        self.resize(850, 750)
        retranslator.bind(self, "workshop_manage", setter="setWindowTitle")
        layout = QVBoxLayout(self)
        self.page = SettingPage("workshop_manage", "workshop_manage_hint")
        layout.addWidget(self.page)
        self._build_session()
        self._build_publish()
        self._build_subscriptions()
        retranslator.bind_call(self._retranslate)

    def _button(self, key: str, callback) -> QPushButton:
        button = tr(QPushButton(), key)
        button.clicked.connect(callback)
        return button

    def _build_session(self) -> None:
        section = self.page.add_section("workshop_session")
        self.status = tr(QLabel(), "workshop_connect_hint")
        self.status.setWordWrap(True)
        section.add_widget(self.status)
        section.add_inline(self._button("workshop_connect", self.connect_steam),
                           self._button("workshop_terms", self._terms))

    def _build_publish(self) -> None:
        section = self.page.add_section("workshop_publish")
        self.kind, self.visibility = QComboBox(), QComboBox()
        for kind in ("scene", "preset", "pet_pack"):
            self.kind.addItem(translate("workshop_kind_" + kind), kind)
        for visibility in (2, 1, 0, 3):
            self.visibility.addItem(translate("workshop_visibility_" + str(visibility)), visibility)
        self.source, self.preview, self.title, self.tags, self.published_id = (QLineEdit() for _ in range(5))
        self.description = QPlainTextEdit()
        self.description.setMaximumHeight(90)
        for key, widget in (("workshop_kind", self.kind), ("workshop_source", self.source),
                            ("workshop_preview", self.preview), ("workshop_title", self.title),
                            ("workshop_description", self.description), ("workshop_tags", self.tags),
                            ("workshop_visibility", self.visibility), ("workshop_item_id", self.published_id)):
            section.add_row(key, widget)
        section.add_inline(self._button("workshop_choose_source", self._choose_source),
                           self._button("workshop_choose_preview", self._choose_preview))
        self.publish_button = self._button("workshop_publish", self._prepare)
        self.retry_button = self._button("workshop_retry", self._retry)
        section.add_inline(self.publish_button, self.retry_button,
                           self._button("workshop_open_item", self._open_item))
        self.progress_bar = QProgressBar()
        section.add_widget(self.progress_bar)
        self.upload_status = QLabel()
        self.upload_status.setWordWrap(True)
        section.add_widget(self.upload_status)
        self.operations = QListWidget()
        self.operations.setMaximumHeight(120)
        section.add_widget(self.operations)

    def _build_subscriptions(self) -> None:
        section = self.page.add_section("workshop_subscriptions")
        self.items = QListWidget()
        self.items.setMinimumHeight(100)
        section.add_widget(self.items)
        section.add_inline(self._button("workshop_refresh", self._refresh),
                           self._button("workshop_use", self._use),
                           self._button("workshop_accept_update", self._accept_update),
                           self._button("workshop_keep_local", self._keep_local))

    def select_source(self, kind: str = "scene", path: str = "") -> None:
        index = self.kind.findData(kind)
        if index >= 0:
            self.kind.setCurrentIndex(index)
        if path:
            self.source.setText(path)
            self.title.setText(Path(path).stem)

    def connect_steam(self) -> None:
        if not self.service.start():
            return
        if self.store is not None:
            self._refresh()
            return
        try:
            user_id = self.service.backend.user_id
            self.store = PublicationStore(user_id, self.storage_root)
            self.cache = WorkshopCache(user_id, self.storage_root)
            self.publisher = WorkshopPublisher(self.service, self.store, self)
            self.publisher.changed.connect(self._publication_changed)
            self.publisher.progress.connect(self._progress)
            self.subscriptions = WorkshopSubscriptions(self.service, self.cache, self)
            self.subscriptions.changed.connect(self._items_changed)
            self.subscriptions.failed.connect(self._error)
            self._operations_changed(self.store.records(recover=True))
            self._refresh()
        except (OSError, ValueError) as error:
            self._error(str(error))

    def _availability(self, available: bool, reason: str) -> None:
        retranslator.set_text(self.status, "workshop_connected" if available else "workshop_connect_hint")
        if reason:
            self.status.setText(self.status.text() + "\n" + reason)

    def _choose_source(self) -> None:
        if self.kind.currentData() == "pet_pack":
            path = QFileDialog.getExistingDirectory(self, translate("workshop_choose_source"))
        else:
            file_filter = "Scene (*.fescene *.json)" if self.kind.currentData() == "scene" else "Preset (*.zip)"
            path, _ = QFileDialog.getOpenFileName(self, translate("workshop_choose_source"), "", file_filter)
        if path:
            self.source.setText(path)
            if not self.title.text():
                self.title.setText(Path(path).stem)

    def _choose_preview(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, translate("workshop_choose_preview"), "", "PNG / JPEG (*.png *.jpg *.jpeg)")
        if path:
            self.preview.setText(path)

    def _prepare(self) -> None:
        if self.publisher is None:
            self.connect_steam()
        if self.publisher is None or self.publisher.busy or self.jobs.pending:
            return
        values = (self.kind.currentData(), Path(self.source.text()), self.title.text(),
                  Path(self.preview.text()), self.description.toPlainText(),
                  [tag.strip() for tag in self.tags.text().split(",") if tag.strip()],
                  self.visibility.currentData(), self.published_id.text().strip())
        self.publish_button.setEnabled(False)
        retranslator.set_text(self.upload_status, "workshop_state_preparing")
        self.jobs.submit("prepare", lambda: self.store.prepare(*values))

    def _retry(self) -> None:
        selected = self.operations.currentItem()
        if selected is None or self.publisher is None or self.publisher.busy or self.jobs.pending:
            return
        operation = selected.data(Qt.ItemDataRole.UserRole)["operation"]
        self.jobs.submit("verify", lambda: self.store.load(operation))
        self.publish_button.setEnabled(False)

    def _job_done(self, key: str, result) -> None:
        try:
            if key in ("prepare", "verify"):
                self.publisher.start_verified(result)
            elif key == "scene":
                entries, lease = result
                adopt_scene_entries(entries, lease)
                self.owner.scene_setting_ui.scene_manager_ui.renew_json_plain_text()
                retranslator.set_text(self.upload_status, "workshop_loaded")
            elif key == "preset":
                retranslator.set_text(self.upload_status, "preset_imported")
            elif key == "activate":
                self.subscriptions.refresh()
            elif key == "local" and result:
                self._load_item(result)
        except (OSError, ValueError, RuntimeError) as error:
            self._error(str(error))
            self.publish_button.setEnabled(True)

    def _job_failed(self, key: str, reason: str) -> None:
        self.publish_button.setEnabled(True)
        self._error(reason)

    def _publication_changed(self, record: dict) -> None:
        self.published_id.setText(record["published_id"])
        self.publish_button.setEnabled(not self.publisher.busy)
        retranslator.set_text(self.upload_status, "workshop_state_" + record["state"])
        if record["error"]:
            self.upload_status.setText(self.upload_status.text() + "\n" + record["error"])
        self._operations_changed(self.store.records())

    def _operations_changed(self, records: list[dict]) -> None:
        selected = self.operations.currentItem()
        operation = selected.data(Qt.ItemDataRole.UserRole)["operation"] if selected else ""
        self.operations.clear()
        for record in records:
            row = QListWidgetItem(f'{record["manifest"]["title"]} · {record["published_id"] or "—"} · '
                                  + translate("workshop_state_" + record["state"]))
            row.setData(Qt.ItemDataRole.UserRole, record)
            self.operations.addItem(row)
            if record["operation"] == operation:
                self.operations.setCurrentItem(row)

    def _progress(self, phase: int, processed: int, total: int) -> None:
        self.progress_bar.setRange(0, 100 if total else 0)
        self.progress_bar.setValue(min(100, round(processed * 100 / total)) if total else 0)

    def _refresh(self) -> None:
        if self.subscriptions is not None:
            self.subscriptions.refresh()

    def _items_changed(self, items: list[dict]) -> None:
        selected = self.items.currentItem()
        selected_id = selected.data(Qt.ItemDataRole.UserRole)["id"] if selected else ""
        self.items.clear()
        for item in items:
            row = QListWidgetItem(f'{item["title"]} · {item["id"]} · '
                                  + translate("workshop_state_" + item["status"]))
            row.setToolTip(item.get("error", ""))
            row.setData(Qt.ItemDataRole.UserRole, item)
            self.items.addItem(row)
            if item["id"] == selected_id:
                self.items.setCurrentItem(row)

    def _selected(self) -> dict | None:
        row = self.items.currentItem()
        return row.data(Qt.ItemDataRole.UserRole) if row else None

    def _use(self) -> None:
        item = self._selected()
        if not item or item["status"] != "ready":
            return
        try:
            self._load_item(item)
        except (OSError, ValueError, RuntimeError, StopIteration) as error:
            self._error(str(error))

    def _load_item(self, item: dict) -> None:
        entry = self.cache.entry(item)
        if item["kind"] == "scene":
            self.jobs.submit("scene", lambda: load_package(entry))
        elif item["kind"] == "preset":
            name, ok = QInputDialog.getText(self, translate("workshop_use"), translate("preset_save_label"),
                                          text=f'Workshop_{item["id"]}_{item["title"]}')
            if ok and name.strip():
                repository = PresetRepository(Path.cwd() / "presets")
                self.jobs.submit("preset", lambda: self.cache.import_preset(item, name.strip(), repository))
        elif item["kind"] in ("pet_pack", "media"):
            if item["kind"] == "media":
                entry = next(path for path in entry.iterdir() if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"})
            page = self.owner.pet_setting_ui
            page.set_state({"pet_image_path": str(entry)})
            retranslator.set_text(self.upload_status, "workshop_loaded")

    def _accept_update(self) -> None:
        item = self._selected()
        if item and item["status"] == "conflict":
            self.jobs.submit("activate", lambda: self.cache.activate(item))

    def _keep_local(self) -> None:
        item = self._selected()
        if item and item["status"] == "conflict":
            self.jobs.submit("local", lambda: self.cache.current(item["id"]))

    def _open_item(self) -> None:
        row = self.operations.currentItem()
        published_id = row.data(Qt.ItemDataRole.UserRole)["published_id"] if row else self.published_id.text().strip()
        if published_id.isascii() and published_id.isdigit():
            QDesktopServices.openUrl(QUrl("https://steamcommunity.com/sharedfiles/filedetails/?id=" + published_id))

    def _terms(self) -> None:
        QDesktopServices.openUrl(QUrl("https://steamcommunity.com/workshop/workshoplegalagreement/"))

    def _error(self, reason: str) -> None:
        QMessageBox.warning(self, translate("workshop_manage"), reason)

    def _retranslate(self) -> None:
        for index in range(self.kind.count()):
            self.kind.setItemText(index, translate("workshop_kind_" + self.kind.itemData(index)))
        for index in range(self.visibility.count()):
            self.visibility.setItemText(index, translate("workshop_visibility_" + str(self.visibility.itemData(index))))
        if self.store:
            self._operations_changed(self.store.records())
        if self.subscriptions:
            self._items_changed(list(self.subscriptions.items.values()))
