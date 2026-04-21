from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QInputDialog, QMessageBox

from frontengine.user_setting.preset_repository import PresetRepository
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
            page.set_state(section)


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
        try:
            PresetRepository().save(name.strip(), _collect_state(ui))
        except (OSError, ValueError) as error:
            QMessageBox.warning(ui, _t("preset_save_title", "Save preset"), str(error))
            return
        QMessageBox.information(
            ui,
            _t("preset_save_title", "Save preset"),
            _t("preset_saved", "Preset saved."),
        )

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


def build_preset_menu(ui: "FrontEngineMainUI") -> None:
    """
    Build the Presets menu with Save / Load / Delete actions.
    """
    front_engine_logger.info(f"[PresetMenu] build_preset_menu | ui={ui}")
    menu = ui.menu_bar.addMenu(_t("menu_bar_presets", "Presets"))
    ui.preset_menu = menu

    for label_key, fallback, callback_factory in (
        ("preset_menu_save", "Save preset...", _save_action),
        ("preset_menu_load", "Load preset...", _load_action),
        ("preset_menu_delete", "Delete preset...", _delete_action),
    ):
        action = QAction(_t(label_key, fallback), menu)
        action.triggered.connect(callback_factory(ui))
        menu.addAction(action)
