"""Color identity, persistence, limits, export and picker/editor integration."""
import json
import uuid

import pytest
from PySide6.QtCore import QPoint, QCoreApplication
from PySide6.QtGui import QColor, QPixmap

from frontengine.show.measure.measure_widget import MeasureWidget
from frontengine.utils.json.json_repository import JsonRepository
from frontengine.utils.measure.color_palette import ColorPalette, MAX_RECENT, MAX_SWATCHES


def test_palette_reopens_and_exports_exact_rgb(tmp_path):
    settings = {}
    repository = JsonRepository(tmp_path / "settings.json")
    palette = ColorPalette(settings, lambda: repository.save(settings))
    identifier = palette.sample("#AbC")
    palette.update(identifier, "Accent", "Brand", "#112233")
    palette.sample("#aabbcc")
    reopened = ColorPalette(repository.load(), lambda: None)
    assert reopened.entries[0] == {"id": identifier, "name": "Accent", "group": "Brand", "color": "#112233"}
    assert reopened.recent == ["#aabbcc"]
    destination = tmp_path / "colors.json"
    reopened.export(destination, "json")
    assert json.loads(destination.read_text(encoding="utf-8"))["swatches"][0]["color"] == "#112233"
    assert "--brand-accent: #112233;" in reopened.export_text("css")


def test_duplicates_casefold_names_and_css_slug_collisions_are_explicit():
    palette = ColorPalette({}, lambda: None)
    identifier = palette.add("Accent", "Brand", "#abc")
    with pytest.raises(ValueError, match="already contains"):
        palette.add("accent", "brand", "#123456")
    palette.add("Accent", "Other", "#123456")
    palette.add("a.b", "", "#111111")
    palette.add("a b", "", "#222222")
    css = palette.export_text("css")
    assert "--a-b: #111111;" in css and "--a-b-2: #222222;" in css
    with pytest.raises(ValueError):
        palette.update(identifier, "Accent", "Other", "#abcdef")
    assert palette.entries[0]["group"] == "Brand"


def test_sampling_is_bounded_and_invalid_saved_values_are_reported():
    entries = [{"id": uuid.uuid4().hex, "name": f"color-{index}", "group": "", "color": f"#{index:06x}"}
               for index in range(MAX_SWATCHES)]
    palette = ColorPalette({"color_palette": {"swatches": [*entries, {}], "recent": ["bad"]}}, lambda: None)
    assert len(palette.entries) == MAX_SWATCHES and palette.load_errors == 2
    for index in range(70):
        palette.sample(f"#{index:06x}")
    assert len(palette.recent) == MAX_RECENT and len(palette.entries) == MAX_SWATCHES
    with pytest.raises(ValueError, match="512"):
        palette.sample("#ffffff")


def test_failed_save_and_failed_export_preserve_existing_state(tmp_path, monkeypatch):
    settings = {}
    palette = ColorPalette(settings, lambda: None)
    palette.add("Stable", "", "#abcdef")
    previous = json.dumps(settings, sort_keys=True)
    def fail():
        raise OSError("disk unavailable")
    palette.save = fail
    with pytest.raises(OSError):
        palette.add("Failed", "", "#111111")
    assert len(palette.entries) == 1 and json.dumps(settings, sort_keys=True) == previous
    target = tmp_path / "existing.css"
    target.write_text("original", encoding="utf-8")
    import frontengine.utils.measure.color_palette as module
    monkeypatch.setattr(module.os, "replace", lambda *_args: fail())
    with pytest.raises(OSError):
        palette.export(target, "css")
    assert target.read_text(encoding="utf-8") == "original"
    assert not list(tmp_path.glob(".palette-*"))


def test_picker_samples_clicks_only_and_preserves_exact_color():
    widget = MeasureWidget()
    image = QPixmap(1, 1)
    image.fill(QColor("#13579b"))
    widget.set_grabber(lambda _rect: image)
    colors = []
    widget.color_sampled.connect(colors.append)
    widget.track_cursor(QPoint(10, 10))
    assert colors == []
    assert widget.add_point(QPoint(10, 10)) == "#13579b"
    assert widget.add_point(QPoint(15, 15)) == "#13579b"
    assert colors == ["#13579b", "#13579b"]
    widget.close()


def test_tools_collection_and_edit_dialog_share_persistent_model(monkeypatch):
    import frontengine.ui.page.tools.tools_setting_ui as module
    monkeypatch.setattr(module, "user_setting_dict", {})
    monkeypatch.setattr(module, "write_user_setting", lambda: None)
    page = module.ToolsSettingUI()
    page._record_palette_color("#123456")
    assert not page.palette.entries
    page.palette_collect.setChecked(True)
    page._record_palette_color("#123456")
    page.open_palette()
    dialog = page.palette_dialog
    assert dialog.table.rowCount() == 1
    from qt_material import apply_stylesheet
    apply_stylesheet(dialog, theme="dark_amber.xml")
    QCoreApplication.processEvents()
    rectangle = dialog.table.visualItemRect(dialog.table.item(0, 2))
    pixel = dialog.table.viewport().grab().toImage().pixelColor(rectangle.right() - 20, rectangle.center().y())
    assert pixel.name() == "#123456"
    dialog.table.item(0, 0).setText("Reference")
    dialog.table.item(0, 1).setText("Design")
    assert page.palette.entries[0]["name"] == "Reference"
    assert page.palette.entries[0]["group"] == "Design"
    dialog.table.item(0, 2).setText("invalid")
    assert page.palette.entries[0]["color"] == "#123456"
    assert dialog.status.text()
    dialog.search.setText("design")
    assert dialog.table.rowCount() == 1
    page.close_palette()
    assert not dialog.isVisible()
    page.close()
