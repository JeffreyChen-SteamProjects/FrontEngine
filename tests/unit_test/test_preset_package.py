"""Preset packages: which fields travel as media, the shared archive budget, and empty media fields."""
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from frontengine.ui.menu.preset_menu import apply_state_transaction, package_too_large_text
from frontengine.user_setting.preset_repository import PresetRepository
from frontengine.utils.imervue import puppet_asset
from frontengine.utils.imervue.puppet_asset import ArchiveBudgetError
from frontengine.utils.multi_language.language_wrapper import language_wrapper


def _files(tmp_path, **contents):
    folder = tmp_path / "fixtures"
    folder.mkdir(exist_ok=True)
    paths = {}
    for name, text in contents.items():
        paths[name] = folder / name.replace("_", ".")
        paths[name].write_text(text, encoding="utf-8")
    return paths


def _archived_preset(package):
    with zipfile.ZipFile(package) as archive:
        return sorted(archive.namelist()), json.loads(archive.read("preset.json"))


# --- F05: only the portable media fields are packed --------------------------------------------------------

def test_export_packs_only_the_media_fields_the_pages_picked(tmp_path):
    files = _files(tmp_path, clip_mp4="video", notes_txt="private notes", page_html="<p>page</p>",
                   other_html="<p>other</p>", feed_txt="live feed")
    repository = PresetRepository(tmp_path / "presets")
    repository.save("Share", {
        "video": {"video_path": str(files["clip_mp4"])},
        "text": {"text": str(files["notes_txt"]), "text_file": str(files["feed_txt"])},
        "web": {"url": str(files["page_html"]), "open_file": True},
        "plugin:clock": {"caption": str(files["other_html"])},
    })
    names, preset = _archived_preset(repository.export_package("Share", tmp_path / "share.zip"))
    assert names == ["media/clip.mp4", "media/page.html", "preset.json"]
    assert preset["video"]["video_path"] == "media/clip.mp4"
    assert preset["web"]["url"] == "media/page.html"
    assert preset["text"] == {"text": str(files["notes_txt"]), "text_file": str(files["feed_txt"])}
    assert preset["plugin:clock"] == {"caption": str(files["other_html"])}


def test_a_web_address_is_not_packed_unless_the_page_opens_a_local_file(tmp_path):
    files = _files(tmp_path, page_html="<p>page</p>")
    repository = PresetRepository(tmp_path / "presets")
    repository.save("Web", {"web": {"url": str(files["page_html"]), "open_file": False}})
    names, preset = _archived_preset(repository.export_package("Web", tmp_path / "web.zip"))
    assert names == ["preset.json"] and preset["web"]["url"] == str(files["page_html"])


def test_text_and_labels_round_trip_unchanged(tmp_path):
    files = _files(tmp_path, clip_mp4="video", notes_txt="private notes")
    text = {"text": str(files["notes_txt"]), "weather_location": "media/Taipei"}
    labels = {"caption": "media/banner.png", "title": str(files["notes_txt"])}
    repository = PresetRepository(tmp_path / "presets")
    repository.save("Trip", {"video": {"video_path": str(files["clip_mp4"])}, "text": text, "plugin:clock": labels})
    package = repository.export_package("Trip", tmp_path / "trip.zip")
    stored = repository.load(repository.import_package(package))
    assert stored["text"] == text and stored["plugin:clock"] == labels
    imported = Path(stored["video"]["video_path"])
    assert imported.parent.parent == repository.directory / "media" and imported.read_text() == "video"


# --- F07: export enforces the budget import enforces --------------------------------------------------------

def _two_media_preset(tmp_path):
    files = _files(tmp_path, clip_mp4="v" * 300, still_png="i" * 200)
    repository = PresetRepository(tmp_path / "presets")
    repository.save("Big", {"video": {"video_path": str(files["clip_mp4"])},
                            "image": {"image_path": str(files["still_png"])}})
    return repository


def _uncompressed_size(package):
    with zipfile.ZipFile(package) as archive:
        return sum(item.file_size for item in archive.infolist())


def test_a_package_exactly_at_the_byte_limit_exports_and_imports(tmp_path, monkeypatch):
    repository = _two_media_preset(tmp_path)
    size = _uncompressed_size(repository.export_package("Big", tmp_path / "probe.zip"))
    monkeypatch.setattr(puppet_asset, "MAX_ARCHIVE_BYTES", size)
    package = repository.export_package("Big", tmp_path / "at-limit.zip")
    stored = repository.load(repository.import_package(package))
    assert Path(stored["video"]["video_path"]).read_text() == "v" * 300


def test_a_package_over_the_byte_limit_is_refused_before_writing(tmp_path, monkeypatch):
    repository = _two_media_preset(tmp_path)
    probe = repository.export_package("Big", tmp_path / "probe.zip")
    monkeypatch.setattr(puppet_asset, "MAX_ARCHIVE_BYTES", _uncompressed_size(probe) - 1)
    with pytest.raises(ValueError, match="resource limit"):
        repository.import_package(probe)             # what an unchecked export would have handed the user
    target = tmp_path / "over.zip"
    target.write_bytes(b"previous backup")
    with pytest.raises(ArchiveBudgetError):
        repository.export_package("Big", target)
    assert target.read_bytes() == b"previous backup"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["fixtures", "over.zip", "presets", "probe.zip"]


def test_the_member_limit_is_shared_at_and_over_the_limit(tmp_path, monkeypatch):
    repository = _two_media_preset(tmp_path)
    monkeypatch.setattr(puppet_asset, "MAX_ARCHIVE_MEMBERS", 3)
    package = repository.export_package("Big", tmp_path / "at-limit.zip")
    assert len(_archived_preset(package)[0]) == 3
    repository.import_package(package)
    monkeypatch.setattr(puppet_asset, "MAX_ARCHIVE_MEMBERS", 2)
    with pytest.raises(ArchiveBudgetError):
        repository.export_package("Big", tmp_path / "over.zip")
    assert not (tmp_path / "over.zip").exists()


def test_a_failed_write_keeps_the_previous_package(tmp_path, monkeypatch):
    repository = _two_media_preset(tmp_path)
    target = tmp_path / "backup.zip"
    target.write_bytes(b"previous backup")

    def broken_write(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(zipfile.ZipFile, "write", broken_write)
    with pytest.raises(OSError, match="disk full"):
        repository.export_package("Big", target)
    assert target.read_bytes() == b"previous backup"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["backup.zip", "fixtures", "presets"]


def test_the_export_error_names_the_shared_limits():
    message = package_too_large_text()
    assert str(puppet_asset.MAX_ARCHIVE_MEMBERS) in message and "256" in message


# --- F06: an explicitly empty media field clears the page ---------------------------------------------------

def _page(kind, lifetime):
    if kind == "video":
        from frontengine.ui.page.video.video_setting_ui import VideoSettingUI
        return VideoSettingUI(lifetime=lifetime), "video_setting_ui", "video_path", "ready_to_play", "ready_label"
    if kind == "image":
        from frontengine.ui.page.image.image_setting_ui import ImageSettingUI
        return ImageSettingUI(lifetime=lifetime), "image_setting_ui", "image_path", "ready_to_play", "ready_label"
    if kind == "gif":
        from frontengine.ui.page.gif.gif_setting_ui import GIFSettingUI
        return GIFSettingUI(lifetime=lifetime), "gif_setting_ui", "gif_image_path", "ready_to_play", "ready_label"
    from frontengine.ui.page.sound_player.sound_player_setting_ui import SoundPlayerSettingUI
    return (SoundPlayerSettingUI(lifetime=lifetime), "sound_player_setting_ui", "wav_sound_path",
            "wav_ready_to_play", "wav_ready_label")


class _FailingPage:
    def get_state(self):
        return {}

    def set_state(self, _state):
        raise ValueError("bad page")


def _assert_cleared(page, field, flag, label):
    assert getattr(page, field) is None and getattr(page, flag) is False
    assert getattr(page, label).text() == language_wrapper.language_word_dict.get("Not Ready")


@pytest.mark.parametrize("kind", ["video", "image", "gif", "sound"])
def test_an_empty_preset_clears_the_previous_media(tmp_path, kind, *, lifetime_factory):
    lifetime_factory()
    page, attribute, field, flag, label = _page(kind, lifetime_factory())
    ui = SimpleNamespace(**{attribute: page})
    section = {"video": "video", "image": "image", "gif": "gif"}.get(kind, "sound")
    try:
        empty = page.get_state()
        demo = str(tmp_path / "demo.mp4")
        apply_state_transaction(ui, {section: dict(empty, **{field: demo})})
        assert getattr(page, field) == demo and getattr(page, flag) is True
        page.set_state({})                                  # an older preset without the field keeps the file
        assert getattr(page, field) == demo
        apply_state_transaction(ui, {section: empty})
        _assert_cleared(page, field, flag, label)
        failing = SimpleNamespace(**{attribute: page, "text_setting_ui": _FailingPage()})
        with pytest.raises(RuntimeError, match="bad page"):
            apply_state_transaction(failing, {section: dict(empty, **{field: demo}), "text": {}})
        _assert_cleared(page, field, flag, label)           # the rollback restored the empty snapshot
    finally:
        page.close()


def test_an_empty_music_field_clears_the_music_too(tmp_path, *, lifetime_factory):
    lifetime_factory()
    page = _page("sound", lifetime_factory())[0]
    try:
        page.set_state({"player_sound_path": str(tmp_path / "song.mp3")})
        page.set_state({"player_sound_path": None})
        assert page.player_sound_path is None
        assert page.player_ready_label.text() == language_wrapper.language_word_dict.get("Not Ready")
    finally:
        page.close()
