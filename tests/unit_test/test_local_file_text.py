"""UTF-8 feeds, queued delivery, recovery and portable scene integration."""
import json
import threading
import time

import pytest
from PySide6.QtCore import QCoreApplication

from frontengine.show.text.draw_text import TextWidget
from frontengine.utils.scene_format.scene_package import load_package, save_package
from frontengine.show.overlay_factory import build_overlay
from frontengine.utils.text_source.local_file_source import (
    FileTextResult, LocalFileTextSource, MAX_FILE_BYTES, read_file_text,
)


def wait_until(condition):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and not condition():
        QCoreApplication.processEvents()
        time.sleep(.005)
    assert condition()


def test_txt_json_csv_selection_and_error_recovery(tmp_path):
    path = tmp_path / "status.txt"
    assert read_file_text(str(path)).status == "missing"
    path.write_text("Ready\n準備好", encoding="utf-8-sig")
    first = read_file_text(str(path))
    assert first.status == "ready" and first.value == "Ready\n準備好"
    assert read_file_text(str(path), previous=first) is first
    path = tmp_path / "stats.json"
    path.write_text(json.dumps({"result": {"count": 3}, "a/b": ["OK"]}), encoding="utf-8")
    result = read_file_text(str(path), "/result/count")
    assert result.value == "3" and "/a~1b/0" in result.fields
    assert read_file_text(str(path), "/a~1b/0", result).value == "OK"
    assert read_file_text(str(path), "/gone").status == "missing_field"
    path.write_text("broken", encoding="utf-8")
    assert read_file_text(str(path)).status == "invalid"
    path = tmp_path / "build.csv"
    path.write_text('name,state\nOne,OK\nTwo,"Ready, now"\n', encoding="utf-8")
    result = read_file_text(str(path), "state")
    assert result.value == "OK\nReady, now" and result.fields == ("name", "state")
    assert read_file_text(str(path), "missing").status == "missing_field"
    path.write_text("duplicate,duplicate\na,b", encoding="utf-8")
    assert read_file_text(str(path)).status == "invalid"
    path.write_text('name,state\n"unfinished', encoding="utf-8")
    assert read_file_text(str(path)).status == "invalid"


@pytest.mark.parametrize("suffix,content,status", [
    (".txt", b"x" * (MAX_FILE_BYTES + 1), "too_large"),
    (".txt", b"x" * 65537, "too_large"),
    (".txt", b"\xff", "invalid"),
    (".exe", b"text", "unsupported"),
], ids=["file_size", "display_size", "encoding", "unsupported"])
def test_reader_enforces_file_and_display_limits(tmp_path, suffix, content, status):
    path = tmp_path / ("input" + suffix)
    path.write_bytes(content)
    assert read_file_text(str(path)).status == status


def test_async_feed_is_bounded_and_ignores_late_result_after_stop():
    entered, release, calls = threading.Event(), threading.Event(), []
    def reader(*_args):
        calls.append(threading.get_ident())
        entered.set()
        assert release.wait(3)
        return FileTextResult("ready", "late")
    source = LocalFileTextSource("unused.txt", reader=reader)
    changed = []
    source.changed.connect(lambda: changed.append(True))
    source.start()
    try:
        wait_until(entered.is_set)
        for _ in range(10):
            source.refresh()
        assert len(calls) == 1 and calls[0] != threading.get_ident()
        source.stop()
    finally:
        release.set()
    wait_until(lambda: source.pending is None)
    assert source.result.status == "loading" and changed == []
    assert not source.timer.isActive()


def test_overlay_updates_changed_file_and_releases_source_on_close(tmp_path):
    path = tmp_path / "live.txt"
    path.write_text("First", encoding="utf-8")
    source = LocalFileTextSource(str(path))
    widget = TextWidget("")
    widget.set_text_source(source)
    wait_until(lambda: widget.text == "First")
    path.write_text("Second value", encoding="utf-8")
    source.refresh()
    wait_until(lambda: widget.text == "Second value")
    path.unlink()
    source.refresh()
    wait_until(lambda: source.result.status == "missing")
    path.write_text("Recovered", encoding="utf-8")
    source.refresh()
    wait_until(lambda: widget.text == "Recovered")
    widget.close()
    assert source.closed and not source.timer.isActive()


def test_portable_scene_copies_file_feed_and_replays_it(tmp_path):
    path = tmp_path / "values.json"
    path.write_text('{"count":42}', encoding="utf-8")
    target = tmp_path / "live.fescene"
    save_package({"label": {"type": "TEXT", "text_source": "local_file",
                            "text_file": str(path), "text_file_field": "/count"}}, target)
    entries, lease = load_package(target)
    try:
        assert entries["label"]["text_file"] != str(path)
        widget = build_overlay("text", entries["label"])
        wait_until(lambda: widget.text == "42")
        widget.close()
    finally:
        lease.cleanup()


def test_imported_file_feed_cannot_read_outside_scene_package(tmp_path):
    import zipfile
    target = tmp_path / "external.fescene"
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("scene.json", json.dumps({"feed": {"type": "TEXT", "text_source": "local_file",
                                                          "text_file": str(tmp_path / "private.txt")}}))
    with pytest.raises(ValueError, match="outside its package"):
        load_package(target)


def test_ui_settings_restore_file_field_interval_and_preview(tmp_path):
    from frontengine.ui.page.text.text_setting_ui import TextSettingUI
    path = tmp_path / "stats.json"
    path.write_text('{"count":3}', encoding="utf-8")
    page = TextSettingUI()
    page.set_state({"text_source": "local_file", "text_file": str(path),
                    "text_file_field": "/count", "text_file_interval": 2})
    wait_until(lambda: page._file_preview.result.status == "ready")
    assert page.get_state()["text_file_field"] == "/count"
    assert page.get_state()["text_file_interval"] == 2
    assert "/count" in [page.file_field_combo.itemText(index) for index in range(page.file_field_combo.count())]
    source = page._file_preview
    page.close()
    assert source.closed
