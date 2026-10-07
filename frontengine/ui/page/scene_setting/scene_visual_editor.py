"""Visual scene layers with local image/GIF/text preview and undoable transforms."""
from __future__ import annotations

import copy
from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QTimer, QSize
from PySide6.QtGui import QColor, QImageReader, QMovie, QPen, QFont, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QFileDialog, QGraphicsItem, QGraphicsObject,
    QGraphicsScene, QGraphicsView, QInputDialog, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QSplitter, QLabel,
)

from frontengine.ui.page.layout_kit import SettingPage
from frontengine.user_setting.scene_setting import scene_json, write_scene_file
from frontengine.utils.multi_language.retranslate import tr, translate, retranslator
from frontengine.utils.scene_format.scene_editor_document import SceneEditorDocument
from frontengine.ui.page.scene_setting.scene_media_preview import SceneMediaPreview


class SceneCanvas(QGraphicsView):
    """Zoom around the pointer with Ctrl+wheel; retain ordinary scrolling."""

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
            if 0.03 <= self.transform().m11() * factor <= 8:
                self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
                self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)


class SceneLayerItem(QGraphicsObject):
    def __init__(self, editor, key: str, entry: dict) -> None:
        super().__init__()
        self.editor, self.key, self.entry = editor, key, entry
        size = entry.get('size', (320, 480)) if entry.get('type') == 'PUPPET' else (320, 180)
        self.width, self.height = float(entry.get("width", size[0])), float(entry.get("height", size[1]))
        self.image = None
        self.movie = None
        self.resizing = False
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not entry.get("locked", False))
        self.setPos(entry.get("x", 0), entry.get("y", 0))
        self.setZValue(entry.get("z", 0))
        self.setScale(entry.get("scale", 1))
        self.setRotation(entry.get("rotation", 0))
        self.setOpacity(entry.get("opacity", 100) / 100 if entry.get("visible", True) else 0.15)
        self._load_preview()

    def _load_preview(self) -> None:
        if self.entry.get("type") not in ("IMAGE", "GIF"):
            return
        path = self.entry.get("file_path", "")
        reader = QImageReader(path)
        size = reader.size()
        if not reader.canRead() or not 0 < size.width() * size.height() <= 16_777_216:
            return
        if self.entry.get("type") == "GIF":
            self.movie = QMovie(path, parent=self)
            self.movie.setScaledSize(size.scaled(QSize(640, 640), Qt.AspectRatioMode.KeepAspectRatio))
            self.movie.frameChanged.connect(lambda _frame: self.update())
            if self.editor.isVisible():
                self.movie.start()
        else:
            reader.setScaledSize(size.scaled(QSize(640, 640), Qt.AspectRatioMode.KeepAspectRatio))
            self.image = reader.read()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget=None) -> None:
        rect = self.boundingRect()
        painter.fillRect(rect, QColor(45, 48, 54))
        image = self.movie.currentImage() if self.movie else self.image
        preview = getattr(self.editor, 'media_preview', None)
        if preview is not None and self.entry.get('type') in ('VIDEO', 'WEB', 'PUPPET', 'SOUND'):
            image = preview.image(self.key)
        if image is not None and not image.isNull():
            painter.drawImage(rect, image)
        else:
            painter.setPen(QColor("#eeeeee"))
            try:
                font_size = max(6, min(200, int(self.entry.get("font_size", 32))))
            except (TypeError, ValueError, OverflowError):
                font_size = 32
            painter.setFont(QFont(painter.font().family(), font_size))
            text = self.entry.get("text", "") if self.entry.get("type") == "TEXT" else self.entry.get("type", "?")
            painter.drawText(rect.adjusted(8, 8, -8, -8), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, str(text))
        if self.isSelected():
            painter.setPen(QPen(QColor("#FFD740"), 2))
            painter.drawRect(rect.adjusted(1, 1, -1, -1))
            painter.fillRect(QRectF(self.width - 12, self.height - 12, 12, 12), QColor("#FFD740"))

    def mousePressEvent(self, event) -> None:
        self.resizing = (not self.entry.get("locked") and event.button() == Qt.MouseButton.LeftButton and
                         event.pos().x() >= self.width - 16 and event.pos().y() >= self.height - 16)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self.resizing:
            self.prepareGeometryChange()
            self.width = max(16, min(8192, event.pos().x()))
            self.height = max(16, min(8192, event.pos().y()))
            self.update()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if not self.entry.get("locked"):
            editor = self.editor
            # Rebuilding the scene must happen after this item's event returns.
            QTimer.singleShot(0, editor, editor.commit_canvas)
        self.resizing = False


class SceneVisualEditor(SettingPage):
    def __init__(self, manager, parent=None) -> None:
        super().__init__("scene_visual_editor", "scene_visual_hint")
        self.setParent(parent)
        self.manager = manager
        self.document = SceneEditorDocument(self)
        QShortcut(QKeySequence.StandardKey.Undo, self, activated=self.document.undo.undo)
        QShortcut(QKeySequence.StandardKey.Redo, self, activated=self.document.undo.redo)
        self.syncing = False
        self.media_preview = SceneMediaPreview(self)
        self.canvas = QGraphicsScene(self)
        self.canvas.setSceneRect(0, 0, 1920, 1080)
        self.view = SceneCanvas(self.canvas)
        self.view.setMinimumSize(360, 240)
        self.layers = QListWidget()
        self.layers.setMaximumWidth(240)
        self.layers.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        split = QSplitter()
        split.addWidget(self.layers)
        split.addWidget(self.view)
        split.setStretchFactor(1, 1)
        self.add_body_widget(split, 1)
        self._build_actions()
        self._build_media_actions()
        self._build_properties()
        self.document.changed.connect(self._changed)
        manager.entries_changed.connect(self.load_entries)
        self.layers.itemSelectionChanged.connect(self._list_selected)
        self.canvas.selectionChanged.connect(self._canvas_selected)
        self.load_entries(scene_json)
        self._show_properties()

    def _button(self, key: str, callback) -> QPushButton:
        button = tr(QPushButton(), key)
        button.clicked.connect(callback)
        return button

    def _build_actions(self) -> None:
        section = self.add_section("section_actions")
        section.add_inline(self._button("scene_add_image", lambda: self._add_media("IMAGE")),
                           self._button("scene_add_gif", lambda: self._add_media("GIF")),
                           self._button("scene_add_text", self._add_text),
                           self._button("scene_duplicate", self._duplicate),
                           self._button("scene_remove_layer", self._remove))
        section.add_inline(self._button("scene_undo", self.document.undo.undo),
                           self._button("scene_redo", self.document.undo.redo),
                           self._button("scene_fit_canvas", self._fit),
                           self._button("scene_output", lambda: write_scene_file(self)))
        section.add_inline(*(self._button("scene_align_" + direction, lambda checked=False, value=direction: self._align(value))
                             for direction in ("left", "center", "right", "top", "middle", "bottom")))
        section.add_inline(*(self._button('scene_add_' + kind.lower(),
            lambda checked=False, value=kind: self._add_native_media(value))
            for kind in ('VIDEO', 'WEB', 'PUPPET', 'SOUND')))

    def _build_properties(self) -> None:
        section = self.add_section("scene_layer_properties")
        self.fields = {}
        for name, minimum, maximum in (("x", -100000, 100000), ("y", -100000, 100000),
                                       ("width", 16, 8192), ("height", 16, 8192), ("scale", 0.01, 100),
                                       ("rotation", -360, 360), ("z", -10000, 10000), ("opacity", 0, 100)):
            field = QDoubleSpinBox()
            field.setRange(minimum, maximum)
            field.setDecimals(2)
            field.editingFinished.connect(self._apply_properties)
            self.fields[name] = field
            section.add_row("scene_property_" + name, field)
        self.locked = tr(QCheckBox(), "scene_layer_locked")
        self.visible = tr(QCheckBox(), "scene_layer_visible")
        self.locked.clicked.connect(self._apply_properties)
        self.visible.clicked.connect(self._apply_properties)
        section.add_inline(self.locked, self.visible)

    def _build_media_actions(self) -> None:
        section = self.add_section('scene_media_preview_title')
        self.media_enabled = tr(QCheckBox(), 'scene_media_preview_enable')
        self.media_enabled.toggled.connect(self.media_preview.set_enabled)
        section.add_inline(self.media_enabled,
            self._button('scene_media_interact', self._interact_media),
            self._button('scene_media_audition', self._audition_media))
        self.media_status = tr(QLabel(), 'scene_media_preview_hint')
        self.media_status.setWordWrap(True)
        section.add_widget(self.media_status)
        self.media_preview.changed.connect(self._media_changed)
        self.media_preview.failed.connect(self._media_failed)

    def _media_failed(self, message: str) -> None:
        retranslator.forget(self.media_status)
        self.media_status.setText(message)

    def _media_changed(self, key: str) -> None:
        for item in self.canvas.items():
            if item.key == key:
                item.update()

    def _interact_media(self) -> None:
        for key in self._selected_keys():
            self.media_preview.interact(key)

    def _audition_media(self) -> None:
        for key in self._selected_keys():
            self.media_preview.audition(key)

    def load_entries(self, entries: dict) -> None:
        if not self.syncing and entries != self.document.entries:
            try:
                self.document.reset(entries)
            except ValueError as error:
                QMessageBox.warning(self, translate("scene_visual_editor"), str(error))

    def _changed(self, entries: dict) -> None:
        self.media_preview.sync(entries)
        selected = self._selected_keys()
        self.syncing = True
        try:
            scene_json.clear()
            scene_json.update(entries)
            self.manager.renew_json_plain_text()
            self.layers.blockSignals(True)
            self.canvas.blockSignals(True)
            self.layers.clear()
            self.canvas.clear()
            for key, entry in sorted(entries.items(), key=lambda pair: pair[1].get("z", 0), reverse=True):
                row = QListWidgetItem(f'{key} · {entry.get("type", "?")}')
                row.setData(Qt.ItemDataRole.UserRole, key)
                self.layers.addItem(row)
                item = SceneLayerItem(self, key, entry)
                self.canvas.addItem(item)
                row.setSelected(key in selected)
                item.setSelected(key in selected)
        finally:
            self.layers.blockSignals(False)
            self.canvas.blockSignals(False)
            self.syncing = False
        self._show_properties()

    def _selected_keys(self) -> list[str]:
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.layers.selectedItems()]

    def _list_selected(self) -> None:
        keys = self._selected_keys()
        self.canvas.blockSignals(True)
        for item in self.canvas.items():
            item.setSelected(item.key in keys)
        self.canvas.blockSignals(False)
        self._show_properties()

    def _canvas_selected(self) -> None:
        keys = {item.key for item in self.canvas.selectedItems()}
        self.layers.blockSignals(True)
        for index in range(self.layers.count()):
            row = self.layers.item(index)
            row.setSelected(row.data(Qt.ItemDataRole.UserRole) in keys)
        self.layers.blockSignals(False)
        self._show_properties()

    def _show_properties(self) -> None:
        keys = self._selected_keys()
        entry = self.document.entries[keys[0]] if len(keys) == 1 else None
        defaults = {"width": 320, "height": 180, "scale": 1, "opacity": 100}
        for name, field in self.fields.items():
            field.setEnabled(entry is not None and not entry.get("locked", False))
            field.setValue(entry.get(name, defaults.get(name, 0)) if entry else defaults.get(name, 0))
        for checkbox, key, default in ((self.locked, "locked", False), (self.visible, "visible", True)):
            checkbox.setEnabled(entry is not None)
            checkbox.setChecked(entry.get(key, default) if entry else default)

    def _apply_properties(self) -> None:
        keys = self._selected_keys()
        if len(keys) == 1:
            changes = {name: field.value() for name, field in self.fields.items()}
            changes.update(locked=self.locked.isChecked(), visible=self.visible.isChecked())
            self.document.update(keys[0], changes)

    def commit_canvas(self) -> None:
        after = copy.deepcopy(self.document.entries)
        for item in self.canvas.items():
            if item.isSelected() and not item.entry.get("locked"):
                after[item.key].update(x=item.pos().x(), y=item.pos().y(), width=item.width, height=item.height)
        self.document.replace(after, "Move / resize layers")

    def _add_media(self, kind: str) -> None:
        file_filter = "GIF (*.gif *.webp)" if kind == "GIF" else "Image (*.png *.jpg *.jpeg *.webp *.bmp)"
        path, _ = QFileDialog.getOpenFileName(self, translate("scene_add_" + kind.lower()), "", file_filter)
        if path:
            if not QImageReader(path).canRead():
                QMessageBox.warning(self, translate("scene_visual_editor"), translate("scene_invalid_media"))
                return
            self._select_layer(self.document.add({"type": kind, "file_path": path}))

    def _add_text(self) -> None:
        text, ok = QInputDialog.getMultiLineText(self, translate("scene_add_text"), translate("scene_text"))
        if ok and text:
            self._select_layer(self.document.add({"type": "TEXT", "text": text, "font_size": 32}))

    def _add_native_media(self, kind: str) -> None:
        if kind == 'WEB':
            url, accepted = QInputDialog.getText(self, translate('scene_add_web'), translate('web_url'))
            if accepted and url.strip():
                self._select_layer(self.document.add({'type': 'WEB', 'url': url.strip()}))
            return
        filters = {'VIDEO': 'Video (*.mp4 *.webm *.avi *.mov *.mkv)',
                   'SOUND': 'Audio (*.wav *.mp3 *.ogg *.flac *.m4a)', 'PUPPET': 'Puppet (*.puppet)'}
        path, _filter = QFileDialog.getOpenFileName(self, translate('scene_add_' + kind.lower()), '', filters[kind])
        if not path:
            return
        try:
            if not Path(path).is_file():
                raise ValueError(translate('scene_invalid_media'))
            if kind == 'PUPPET':
                from frontengine.utils.imervue.puppet_asset import validate_puppet
                validate_puppet(path)
            self._select_layer(self.document.add({'type': kind, 'file_path': path}))
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, translate('scene_visual_editor'), str(error))

    def _select_layer(self, key: str) -> None:
        self.layers.clearSelection()
        for index in range(self.layers.count()):
            row = self.layers.item(index)
            if row.data(Qt.ItemDataRole.UserRole) == key:
                row.setSelected(True)
                self.layers.scrollToItem(row)
                break

    def _duplicate(self) -> None:
        for key in self._selected_keys():
            self.document.duplicate(key)

    def _remove(self) -> None:
        for key in self._selected_keys():
            self.document.remove(key)

    def _align(self, direction: str) -> None:
        self.document.align(self._selected_keys(), direction)

    def _fit(self) -> None:
        self.view.fitInView(self.canvas.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def showEvent(self, event) -> None:
        self.media_preview.resume()
        self._fit()
        for item in self.canvas.items():
            if item.movie:
                item.movie.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self.media_preview.suspend()
        for item in self.canvas.items():
            if item.movie:
                item.movie.stop()
        super().hideEvent(event)

    def closeEvent(self, event) -> None:
        self.media_preview.shutdown()
        self.canvas.clear()
        super().closeEvent(event)
