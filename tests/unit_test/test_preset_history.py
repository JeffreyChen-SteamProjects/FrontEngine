from copy import deepcopy
from types import SimpleNamespace

import pytest

from frontengine.user_setting.preset_history import PresetHistory, checked_state, compare_states
from frontengine.user_setting.preset_repository import PresetRepository
from frontengine.ui.menu.preset_menu import apply_state_transaction
from frontengine.ui.dialog.preset_versions_dialog import PresetVersionsDialog


def test_saved_versions_reopen_deduplicate_and_restore(tmp_path):
    repo = PresetRepository(tmp_path)
    first = {"text": {"text": "Original", "opacity": 23}}
    second = {"text": {"text": "Changed", "opacity": 80}}
    repo.save("Work", first)
    repo.save("Work", second)
    repo.save("Work", second)
    reopened = PresetRepository(tmp_path)
    history = reopened.history("Work")
    assert len(history.versions()) == 2
    version = next(identifier for identifier, _ in history.versions() if history.load(identifier) == first)
    reopened.save("Work", history.load(version))
    assert reopened.load("Work") == first
    assert reopened.list_presets() == ["Work"]
    assert "Original" in compare_states(second, first)


def test_history_validates_digest_structure_paths_and_limits(tmp_path):
    history = PresetHistory(tmp_path)
    identifier, created = history.snapshot({"text": {"text": "Safe"}})
    assert created
    path = tmp_path / (identifier + ".json")
    path.write_text(path.read_text(encoding="utf-8").replace("Safe", "Unsafe"), encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        history.load(identifier)
    with pytest.raises(ValueError):
        history.load("../settings")
    with pytest.raises(ValueError):
        checked_state({"value": float("nan")})
    with pytest.raises(ValueError):
        checked_state({"value": "x" * 1048576})
    value = {}
    for _ in range(34):
        value = {"value": value}
    with pytest.raises(ValueError, match="structural"):
        checked_state(value)


def test_retention_and_failed_save_preserve_active_preset(tmp_path, monkeypatch):
    from frontengine.utils.json.json_repository import JsonRepository
    repo = PresetRepository(tmp_path)
    for index in range(55):
        repo.save("Work", {"text": {"text": str(index)}})
    assert len(repo.history("Work").versions()) == 50
    before = (tmp_path / "Work.json").read_bytes()
    original_save = JsonRepository.save

    def failing_save(self, data):
        if self.path == tmp_path / "Work.json":
            raise OSError("disk full")
        return original_save(self, data)

    monkeypatch.setattr(JsonRepository, "save", failing_save)
    with pytest.raises(OSError, match="disk full"):
        repo.save("Work", {"text": {"text": "Not committed"}})
    assert (tmp_path / "Work.json").read_bytes() == before
    assert len(repo.history("Work").versions()) == 50


class Page:
    def __init__(self, value):
        self.state = {"text": value}

    def get_state(self):
        return deepcopy(self.state)

    def set_state(self, value):
        self.state = deepcopy(value)
        if value.get("text") == "fail":
            raise ValueError("bad page")


def test_transaction_restores_partial_failing_page_and_preceding_pages():
    image, text = Page("Image"), Page("Text")
    ui = SimpleNamespace(image_setting_ui=image, text_setting_ui=text)
    with pytest.raises(RuntimeError, match="bad page"):
        apply_state_transaction(ui, {"image": {"text": "New"}, "text": {"text": "fail"}})
    assert image.state == {"text": "Image"}
    assert text.state == {"text": "Text"}
    with pytest.raises(ValueError):
        apply_state_transaction(ui, {"image": {"text": "New"}, "text": []})
    assert image.state == {"text": "Image"}


def _dialog(tmp_path):
    repo = PresetRepository(tmp_path)
    repo.save("Work", {"text": {"text": "Old"}})
    repo.save("Work", {"text": {"text": "Saved"}})
    page = Page("Current")
    ui = SimpleNamespace(text_setting_ui=page)
    dialog = PresetVersionsDialog(repo, lambda: {"text": page.get_state()},
                                  lambda state: apply_state_transaction(ui, state))
    dialog.reload_presets()
    for row in range(dialog.versions.count()):
        dialog.versions.setCurrentRow(row)
        if dialog._candidate()["text"]["text"] == "Old":
            break
    return dialog, repo, page


def test_preview_cancel_escape_and_actual_restore_agree(tmp_path):
    dialog, repo, page = _dialog(tmp_path)
    assert "Current" in dialog.diff.toPlainText()
    dialog.preview_selected()
    assert page.state["text"] == "Old"
    assert repo.load("Work")["text"]["text"] == "Saved"
    dialog.reject()
    assert page.state["text"] == "Current"
    dialog.preview_selected()
    dialog.restore_selected()
    assert page.state["text"] == repo.load("Work")["text"]["text"] == "Old"
    dialog.close()
    assert page.state["text"] == "Old"


def test_restore_save_failure_restores_ui_and_file(tmp_path, monkeypatch):
    dialog, repo, page = _dialog(tmp_path)
    original = repo.load("Work")
    monkeypatch.setattr(repo, "save", lambda *_args: (_ for _ in ()).throw(OSError("save failed")))
    dialog.preview_selected()
    dialog.restore_selected()
    assert page.state["text"] == "Current"
    assert repo.load("Work") == original
    assert "save failed" in dialog.status.text()
    dialog.close()
