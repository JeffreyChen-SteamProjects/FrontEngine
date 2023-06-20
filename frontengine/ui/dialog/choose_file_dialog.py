import shutil
from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QWidget, QFileDialog

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


def choose_file(
        trigger_ui: QWidget, file_filter: str, save_path: Path, extensions: list, warning_message: str) -> str:
    front_engine_logger.info("choose_file")
    file_path = QFileDialog().getOpenFileName(
        parent=trigger_ui,
        dir=str(Path.cwd()),
        filter=file_filter
    )[0]
    file_path = Path(file_path)
    if file_path.is_file() and file_path.exists():
        file_save_path = save_path
        if not file_save_path.exists() or not file_save_path.is_dir():
            file_save_path.mkdir(parents=True, exist_ok=True)
        if file_path.suffix.lower() in extensions:
            try:
                new_file_path = shutil.copy(file_path, file_save_path)
            except shutil.SameFileError:
                new_file_path = str(Path(f"{file_save_path}/{file_path.name}"))
            return new_file_path
        else:
            message_box = QMessageBox(trigger_ui)
            message_box.setText(
                warning_message
            )
            message_box.show()


def choose_gif(
        trigger_ui: QWidget, file_filter: str = "GIF WEBP (*.gif;*.webp)",
        save_path: Path = Path(str(Path.cwd()) + "/gif"), extensions: list = None) -> str:
    front_engine_logger.info("choose_gif")
    extensions = extensions or [".gif", ".webp"]
    return choose_file(
        trigger_ui=trigger_ui, file_filter=file_filter, save_path=save_path, extensions=extensions,
        warning_message=language_wrapper.language_word_dict.get("gif_setting_message_box"))


def choose_image(
        trigger_ui: QWidget, file_filter: str = "Images (*.png;*.jpg;*.webp)",
        save_path: Path = Path(str(Path.cwd()) + "/image"), extensions: list = None) -> str:
    front_engine_logger.info("choose_image")
    extensions = extensions or [".png", ".jpg", ".webp"]
    return choose_file(
        trigger_ui=trigger_ui, file_filter=file_filter, save_path=save_path, extensions=extensions,
        warning_message=language_wrapper.language_word_dict.get("image_setting_message_box"))


def choose_wav_sound(
        trigger_ui: QWidget, file_filter: str = "WAV (*.wav)",
        save_path: Path = Path(str(Path.cwd()) + "/sound"), extensions: list = None) -> str:
    front_engine_logger.info("choose_wav_sound")
    extensions = extensions or [".wav"]
    return choose_file(
        trigger_ui=trigger_ui, file_filter=file_filter, save_path=save_path, extensions=extensions,
        warning_message=language_wrapper.language_word_dict.get("sound_player_setting_message_box_sound"))


def choose_player_sound(
        trigger_ui: QWidget, file_filter: str = "Sound (*.mp4;*.mp3;*.wav)",
        save_path: Path = Path(str(Path.cwd()) + "/sound"), extensions: list = None) -> str:
    front_engine_logger.info("choose_player_sound")
    extensions = extensions or [".mp3", ".mp4", ".wav"]
    return choose_file(
        trigger_ui=trigger_ui, file_filter=file_filter, save_path=save_path, extensions=extensions,
        warning_message=language_wrapper.language_word_dict.get("sound_player_setting_message_box_sound"))


def choose_video(
        trigger_ui: QWidget, file_filter: str = "Video (*.mp4;)",
        save_path: Path = Path(str(Path.cwd()) + "/video"), extensions: list = None) -> str:
    front_engine_logger.info("choose_video")
    extensions = extensions or [".mp4"]
    return choose_file(
        trigger_ui=trigger_ui, file_filter=file_filter, save_path=save_path, extensions=extensions,
        warning_message=language_wrapper.language_word_dict.get("video_setting_message_box"))


def choose_scene_json(
        trigger_ui: QWidget, file_filter: str = "Json (*.json;)",
        save_path: Path = Path(str(Path.cwd()) + "/scene"), extensions: list = None) -> str:
    front_engine_logger.info("choose_scene_json")
    extensions = extensions or [".json"]
    return choose_file(
        trigger_ui=trigger_ui, file_filter=file_filter, save_path=save_path, extensions=extensions,
        warning_message=language_wrapper.language_word_dict.get("scene_choose_message_box"))
