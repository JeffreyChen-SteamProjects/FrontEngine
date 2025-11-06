from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import QMessageBox, QWidget, QFileDialog

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


def choose_file(
        trigger_ui: QWidget,
        file_filter: str,
        extensions: List[str],
        warning_message: str
) -> Optional[str]:
    """
    開啟檔案選擇對話框並驗證副檔名
    Open file dialog and validate extension

    :param trigger_ui: 觸發的 UI 元件 / Triggering UI widget
    :param file_filter: 檔案過濾器 / File filter string
    :param extensions: 允許的副檔名清單 / Allowed file extensions
    :param warning_message: 錯誤訊息 / Warning message if invalid
    :return: 檔案路徑或 None / File path or None
    """
    front_engine_logger.info(
        f"[choose_file] filter={file_filter}, extensions={extensions}, warning={warning_message}"
    )

    file_path_str = QFileDialog().getOpenFileName(
        parent=trigger_ui,
        dir=str(Path.cwd()),
        filter=file_filter
    )[0]

    file_path = Path(file_path_str) if file_path_str else None

    if file_path and file_path.is_file() and file_path.suffix.lower() in extensions:
        return str(file_path)

    # 顯示錯誤訊息 / Show warning message
    message_box = QMessageBox(trigger_ui)
    message_box.setText(warning_message)
    message_box.show()
    return None


def choose_gif(trigger_ui: QWidget) -> Optional[str]:
    """選擇 GIF 或 WebP 檔案 / Choose GIF or WebP file"""
    return choose_file(
        trigger_ui,
        file_filter="GIF WEBP (*.gif;*.webp)",
        extensions=[".gif", ".webp"],
        warning_message=language_wrapper.language_word_dict.get("gif_setting_message_box")
    )


def choose_image(trigger_ui: QWidget) -> Optional[str]:
    """選擇圖片檔案 / Choose image file"""
    return choose_file(
        trigger_ui,
        file_filter="Images (*.png;*.jpg;*.webp)",
        extensions=[".png", ".jpg", ".webp"],
        warning_message=language_wrapper.language_word_dict.get("image_setting_message_box")
    )


def choose_wav_sound(trigger_ui: QWidget) -> Optional[str]:
    """選擇 WAV 音效檔案 / Choose WAV sound file"""
    return choose_file(
        trigger_ui,
        file_filter="WAV (*.wav)",
        extensions=[".wav"],
        warning_message=language_wrapper.language_word_dict.get("sound_player_setting_message_box_sound")
    )


def choose_player_sound(trigger_ui: QWidget) -> Optional[str]:
    """選擇音樂檔案 (mp3/mp4/wav) / Choose audio file"""
    return choose_file(
        trigger_ui,
        file_filter="Sound (*.mp4;*.mp3;*.wav)",
        extensions=[".mp3", ".mp4", ".wav"],
        warning_message=language_wrapper.language_word_dict.get("sound_player_setting_message_box_sound")
    )


def choose_video(trigger_ui: QWidget) -> Optional[str]:
    """選擇影片檔案 (mp4) / Choose video file"""
    return choose_file(
        trigger_ui,
        file_filter="Video (*.mp4;)",
        extensions=[".mp4"],
        warning_message=language_wrapper.language_word_dict.get("video_setting_message_box")
    )
