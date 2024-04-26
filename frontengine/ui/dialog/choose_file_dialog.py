from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QWidget, QFileDialog

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


def choose_file(
        trigger_ui: QWidget, file_filter: str, extensions: list, warning_message: str) -> str:
    front_engine_logger.info("choose_file")
    file_path = QFileDialog().getOpenFileName(
        parent=trigger_ui,
        dir=str(Path.cwd()),
        filter=file_filter
    )[0]
    file_path = Path(file_path)
    if file_path.is_file() and file_path.exists() and file_path.suffix.lower() in extensions:
        return str(file_path)
    else:
        message_box = QMessageBox(trigger_ui)
        message_box.setText(
            warning_message
        )
        message_box.show()


def choose_gif(
        trigger_ui: QWidget, file_filter: str = "GIF WEBP (*.gif;*.webp)", extensions: list = None) -> str:
    front_engine_logger.info("choose_gif")
    extensions = extensions or [".gif", ".webp"]
    return choose_file(
        trigger_ui=trigger_ui, file_filter=file_filter, extensions=extensions,
        warning_message=language_wrapper.language_word_dict.get("gif_setting_message_box"))


def choose_image(
        trigger_ui: QWidget, file_filter: str = "Images (*.png;*.jpg;*.webp)", extensions: list = None) -> str:
    front_engine_logger.info("choose_image")
    extensions = extensions or [".png", ".jpg", ".webp"]
    return choose_file(
        trigger_ui=trigger_ui, file_filter=file_filter, extensions=extensions,
        warning_message=language_wrapper.language_word_dict.get("image_setting_message_box"))


def choose_wav_sound(
        trigger_ui: QWidget, file_filter: str = "WAV (*.wav)", extensions: list = None) -> str:
    front_engine_logger.info("choose_wav_sound")
    extensions = extensions or [".wav"]
    return choose_file(
        trigger_ui=trigger_ui, file_filter=file_filter, extensions=extensions,
        warning_message=language_wrapper.language_word_dict.get("sound_player_setting_message_box_sound"))


def choose_player_sound(
        trigger_ui: QWidget, file_filter: str = "Sound (*.mp4;*.mp3;*.wav)", extensions: list = None) -> str:
    front_engine_logger.info("choose_player_sound")
    extensions = extensions or [".mp3", ".mp4", ".wav"]
    return choose_file(
        trigger_ui=trigger_ui, file_filter=file_filter, extensions=extensions,
        warning_message=language_wrapper.language_word_dict.get("sound_player_setting_message_box_sound"))


def choose_video(
        trigger_ui: QWidget, file_filter: str = "Video (*.mp4;)", extensions: list = None) -> str:
    front_engine_logger.info("choose_video")
    extensions = extensions or [".mp4"]
    return choose_file(
        trigger_ui=trigger_ui, file_filter=file_filter, extensions=extensions,
        warning_message=language_wrapper.language_word_dict.get("video_setting_message_box"))
