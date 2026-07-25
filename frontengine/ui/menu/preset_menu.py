from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from frontengine.user_setting.preset_repository import PresetRepository
from frontengine.utils.workshop.workshop_content import (
    KIND_PET_PACK, KIND_PRESET, find_workshop_dir, preset_files, scan_workshop_items,
)
from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper

if TYPE_CHECKING:
    from frontengine.ui.main_ui import FrontEngineMainUI


_PRESET_PAGES = (
    ("video", "video_setting_ui"),
    ("image", "image_setting_ui"),
    ("web", "web_setting_ui"),
    ("gif", "gif_setting_ui"),
    ("sound", "sound_player_setting_ui"),
    ("text", "text_setting_ui"),
    ("particle", "particle_setting_ui"),
    ("pet", "pet_setting_ui"),
)


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


def _collect_state(ui: "FrontEngineMainUI") -> dict:
    state: dict = {}
    for name, attribute in _PRESET_PAGES:
        page = getattr(ui, attribute, None)
        if page is not None and hasattr(page, "get_state"):
            state[name] = page.get_state()
    return state


def _apply_state(ui: "FrontEngineMainUI", state: dict) -> None:
    for name, attribute in _PRESET_PAGES:
        page = getattr(ui, attribute, None)
        section = state.get(name)
        if page is not None and isinstance(section, dict) and hasattr(page, "set_state"):
            # Isolate each page: a malformed section (e.g. a hand-edited
            # preset) must not crash the load or block the other pages.
            try:
                page.set_state(section)
            except Exception as error:  # pragma: no cover - defensive boundary
                front_engine_logger.warning(
                    f"[PresetMenu] Failed to apply '{name}' preset section: {error!r}"
                )


def _pick_preset(ui: "FrontEngineMainUI", title: str) -> str:
    repository = PresetRepository()
    presets = repository.list_presets()
    if not presets:
        QMessageBox.information(ui, title, _t("preset_no_presets", "No presets saved yet."))
        return ""
    preset, ok = QInputDialog.getItem(ui, title, _t("preset_pick_label", "Preset:"), presets, 0, False)
    if not ok or not preset:
        return ""
    return preset


def _save_action(ui: "FrontEngineMainUI") -> Callable[[], None]:
    def handler() -> None:
        front_engine_logger.info("[PresetMenu] save")
        name, ok = QInputDialog.getText(
            ui,
            _t("preset_save_title", "Save preset"),
            _t("preset_save_label", "Preset name:"),
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        title = _t("preset_save_title", "Save preset")
        repository = PresetRepository()
        try:
            if repository.exists(name):
                confirm = QMessageBox.question(
                    ui,
                    title,
                    _t(
                        "preset_overwrite_confirm",
                        "Preset '{name}' already exists. Overwrite?",
                    ).format(name=name),
                )
                if confirm != QMessageBox.StandardButton.Yes:
                    return
            repository.save(name, _collect_state(ui))
        except (OSError, ValueError) as error:
            QMessageBox.warning(ui, title, str(error))
            return
        QMessageBox.information(ui, title, _t("preset_saved", "Preset saved."))

    return handler


def _load_action(ui: "FrontEngineMainUI") -> Callable[[], None]:
    def handler() -> None:
        front_engine_logger.info("[PresetMenu] load")
        title = _t("preset_load_title", "Load preset")
        preset = _pick_preset(ui, title)
        if not preset:
            return
        try:
            data = PresetRepository().load(preset)
        except (OSError, FileNotFoundError, ValueError) as error:
            QMessageBox.warning(ui, title, str(error))
            return
        _apply_state(ui, data)
        QMessageBox.information(ui, title, _t("preset_loaded", "Preset loaded."))

    return handler


def _delete_action(ui: "FrontEngineMainUI") -> Callable[[], None]:
    def handler() -> None:
        front_engine_logger.info("[PresetMenu] delete")
        title = _t("preset_delete_title", "Delete preset")
        preset = _pick_preset(ui, title)
        if not preset:
            return
        confirm = QMessageBox.question(
            ui,
            title,
            _t("preset_delete_confirm", "Delete preset '{name}'?").format(name=preset),
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            PresetRepository().delete(preset)
        except (OSError, ValueError) as error:
            QMessageBox.warning(ui, title, str(error))

    return handler


def _export_action(ui: "FrontEngineMainUI") -> Callable[[], None]:
    def handler() -> None:
        front_engine_logger.info("[PresetMenu] export")
        title = _t("preset_export_title", "Export preset")
        preset = _pick_preset(ui, title)
        if not preset:
            return
        destination, _ok = QFileDialog.getSaveFileName(
            ui, title, f"{preset}.json", _t("preset_file_filter", "Preset files (*.json)")
        )
        if not destination:
            return
        try:
            PresetRepository().export_preset(preset, Path(destination))
        except (OSError, FileNotFoundError, ValueError) as error:
            QMessageBox.warning(ui, title, str(error))
            return
        QMessageBox.information(ui, title, _t("preset_exported", "Preset exported."))

    return handler


def _import_action(ui: "FrontEngineMainUI") -> Callable[[], None]:
    def handler() -> None:
        front_engine_logger.info("[PresetMenu] import")
        title = _t("preset_import_title", "Import preset")
        source, _ok = QFileDialog.getOpenFileName(
            ui, title, "", _t("preset_file_filter", "Preset files (*.json)")
        )
        if not source:
            return
        try:
            PresetRepository().import_preset(Path(source))
        except (OSError, FileNotFoundError, ValueError) as error:
            QMessageBox.warning(ui, title, str(error))
            return
        QMessageBox.information(ui, title, _t("preset_imported", "Preset imported."))

    return handler


def _set_startup_action(ui: "FrontEngineMainUI") -> Callable[[], None]:
    def handler() -> None:
        front_engine_logger.info("[PresetMenu] set startup preset")
        title = _t("preset_startup_title", "Startup preset")
        preset = _pick_preset(ui, title)
        if not preset:
            return
        user_setting_dict["startup_preset"] = preset
        write_user_setting()
        QMessageBox.information(ui, title, _t("preset_startup_set", "Startup preset set."))

    return handler


def _clear_startup_action(ui: "FrontEngineMainUI") -> Callable[[], None]:
    def handler() -> None:
        front_engine_logger.info("[PresetMenu] clear startup preset")
        title = _t("preset_startup_title", "Startup preset")
        user_setting_dict["startup_preset"] = ""
        write_user_setting()
        QMessageBox.information(ui, title, _t("preset_startup_cleared", "Startup preset cleared."))

    return handler


def apply_named_preset(ui: "FrontEngineMainUI", name: str) -> bool:
    """
    依名稱套用預設集；缺失或損毀時僅記錄警告並回傳 False，不丟出例外。
    Apply a preset by name. A missing or corrupt preset is logged and
    skipped (returns False) rather than raising.
    """
    if not isinstance(name, str) or not name.strip():
        return False
    front_engine_logger.info(f"[PresetMenu] apply_named_preset | name={name}")
    try:
        data = PresetRepository().load(name)
    except (OSError, FileNotFoundError, ValueError) as error:
        front_engine_logger.warning(f"[PresetMenu] preset '{name}' failed: {error!r}")
        return False
    _apply_state(ui, data)
    return True


LAST_SESSION_PRESET = "__last_session__"


def save_last_session(ui: "FrontEngineMainUI") -> bool:
    """
    把目前各頁面的設定存成「上次工作階段」預設集（關閉程式時呼叫）。
    Store the current page settings as the last-session preset on exit.
    """
    try:
        PresetRepository().save(LAST_SESSION_PRESET, _collect_state(ui))
        return True
    except (OSError, ValueError) as error:
        front_engine_logger.warning(f"[PresetMenu] save_last_session failed: {error!r}")
        return False


def restore_last_session(ui: "FrontEngineMainUI") -> bool:
    """啟動時還原上次的設定；沒存過或讀不到就跳過。"""
    return apply_named_preset(ui, LAST_SESSION_PRESET)


def apply_startup_preset(ui: "FrontEngineMainUI") -> None:
    """
    啟動時套用設定的預設集；缺失或損毀時僅記錄警告，不影響啟動。
    Apply the configured startup preset on launch. A missing or corrupt
    preset is logged and skipped so startup never fails because of it.
    """
    apply_named_preset(ui, user_setting_dict.get("startup_preset", ""))


def _export_package_action(ui: "FrontEngineMainUI") -> Callable[[], None]:
    def handler() -> None:
        front_engine_logger.info("[PresetMenu] export package")
        title = _t("preset_export_package_title", "Export package")
        preset = _pick_preset(ui, title)
        if not preset:
            return
        destination, _ok = QFileDialog.getSaveFileName(
            ui, title, f"{preset}.zip", _t("preset_package_filter", "Preset packages (*.zip)")
        )
        if not destination:
            return
        try:
            PresetRepository().export_package(preset, Path(destination))
        except (OSError, FileNotFoundError, ValueError) as error:
            QMessageBox.warning(ui, title, str(error))
            return
        QMessageBox.information(ui, title, _t("preset_exported", "Preset exported."))

    return handler


def _import_package_action(ui: "FrontEngineMainUI") -> Callable[[], None]:
    def handler() -> None:
        front_engine_logger.info("[PresetMenu] import package")
        title = _t("preset_import_package_title", "Import package")
        source, _ok = QFileDialog.getOpenFileName(
            ui, title, "", _t("preset_package_filter", "Preset packages (*.zip)")
        )
        if not source:
            return
        try:
            PresetRepository().import_package(Path(source))
        except (OSError, FileNotFoundError, ValueError) as error:
            QMessageBox.warning(ui, title, str(error))
            return
        QMessageBox.information(ui, title, _t("preset_imported", "Preset imported."))

    return handler


def _workshop_action(ui: "FrontEngineMainUI") -> Callable[[], None]:
    """
    匯入 Steam 創意工坊已訂閱的內容：掃描 Steam 下載的資料夾，把預設集複製進來，
    動作包則列出路徑供寵物頁選用。找不到 Steam 時請使用者自己指定路徑。
    Import subscribed Steam Workshop content: copy presets in, and list pet packs
    with their paths so the pet page can point at them. If Steam is not where we
    expect, ask the user where it is.
    """
    def handler() -> None:
        front_engine_logger.info("[PresetMenu] import workshop content")
        title = _t("workshop_menu_import", "Import Workshop content...")
        content_dir = find_workshop_dir()
        if content_dir is None:
            chosen = QFileDialog.getExistingDirectory(
                ui, _t("workshop_pick_steam", "Where is Steam installed?"))
            if not chosen:
                return
            content_dir = find_workshop_dir(extra_paths=[chosen])
        if content_dir is None:
            QMessageBox.information(
                ui, title, _t("workshop_not_found", "No Workshop content found for FrontEngine."))
            return
        items = scan_workshop_items(content_dir)
        if not items:
            QMessageBox.information(
                ui, title,
                _t("workshop_no_items", "Nothing subscribed yet - subscribe in Steam first."))
            return
        imported, packs = _install_workshop_items(items)
        lines = [
            _t("workshop_imported_presets", "Presets imported: {count}").format(count=imported),
            _t("workshop_found_packs", "Pet packs available: {count}").format(count=len(packs)),
        ]
        lines.extend(f"- {title_}: {path}" for title_, path in packs[:8])
        QMessageBox.information(ui, title, chr(10).join(lines))

    return handler


def _install_workshop_items(items) -> tuple:
    """把預設集複製進本機的 presets/，並回傳可用的動作包 (名稱, 路徑)。"""
    repository = PresetRepository()
    imported = 0
    packs = []
    for item in items:
        if item["kind"] == KIND_PET_PACK:
            packs.append((item["title"], item["path"]))
            continue
        if item["kind"] != KIND_PRESET:
            continue
        for preset_path in preset_files(item["path"]):
            try:
                repository.import_preset(Path(preset_path))
                imported += 1
            except Exception as error:  # pragma: no cover - third-party content
                front_engine_logger.warning(
                    f"[PresetMenu] workshop preset failed: {preset_path} ({error!r})")
    return (imported, packs)


def build_preset_menu(ui: "FrontEngineMainUI") -> None:
    """
    Build the Presets menu with Save / Load / Delete / Export / Import actions.
    """
    front_engine_logger.info(f"[PresetMenu] build_preset_menu | ui={ui}")
    menu = ui.menu_bar.addMenu(_t("menu_bar_presets", "Presets"))
    ui.preset_menu = menu

    for label_key, fallback, callback_factory in (
        ("preset_menu_save", "Save preset...", _save_action),
        ("preset_menu_load", "Load preset...", _load_action),
        ("preset_menu_delete", "Delete preset...", _delete_action),
        ("preset_menu_export", "Export preset...", _export_action),
        ("preset_menu_import", "Import preset...", _import_action),
        ("preset_menu_export_package", "Export package (+media)...", _export_package_action),
        ("preset_menu_import_package", "Import package (+media)...", _import_package_action),
        ("preset_menu_set_startup", "Set as startup preset...", _set_startup_action),
        ("preset_menu_clear_startup", "Clear startup preset", _clear_startup_action),
        ("workshop_menu_import", "Import Workshop content...", _workshop_action),
    ):
        action = QAction(_t(label_key, fallback), menu)
        action.triggered.connect(callback_factory(ui))
        menu.addAction(action)
