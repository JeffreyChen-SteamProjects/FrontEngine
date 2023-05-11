from PySide6.QtWidgets import QTabWidget

from frontengine.ui.setting.control_center.control_center_ui import ControlCenterUI
from frontengine.ui.setting.gif.gif_setting_ui import GIFSettingUI
from frontengine.ui.setting.image.image_setting_ui import ImageSettingUI
from frontengine.ui.setting.sound_player.sound_player_setting_ui import SoundPlayerSettingUI
from frontengine.ui.setting.text.text_setting_ui import TextSettingUI
from frontengine.ui.setting.video.video_setting_ui import VideoSettingUI
from frontengine.ui.setting.web.web_setting_ui import WEBSettingUI
from frontengine.utils.multi_language.english import english_word_dict
from frontengine.utils.multi_language.traditional_chinese import traditional_chinese_word_dict


class LanguageWrapper(object):

    def __init__(
            self
    ):
        self.tab_widget = None
        self.control_center_ui = None
        self.text_setting_ui = None
        self.sound_player_setting_ui = None
        self.gif_setting_ui = None
        self.web_setting_ui = None
        self.image_setting_ui = None
        self.video_setting_ui = None
        self.language: str = "en"
        self.choose_language_dict = {
            "en": english_word_dict,
            "tw": traditional_chinese_word_dict
        }
        self.language_word_dict: dict = english_word_dict

    def init_later(
            self,
            video_setting_ui: VideoSettingUI,
            image_setting_ui: ImageSettingUI,
            web_setting_ui: WEBSettingUI,
            gif_setting_ui: GIFSettingUI,
            sound_player_setting_ui: SoundPlayerSettingUI,
            text_setting_ui: TextSettingUI,
            control_center_ui: ControlCenterUI,
            tab_widget: QTabWidget
    ):
        # UI instance
        self.video_setting_ui = video_setting_ui
        self.image_setting_ui = image_setting_ui
        self.web_setting_ui = web_setting_ui
        self.gif_setting_ui = gif_setting_ui
        self.sound_player_setting_ui = sound_player_setting_ui
        self.text_setting_ui = text_setting_ui
        self.control_center_ui = control_center_ui
        self.tab_widget = tab_widget

    def reset_language(self, language) -> None:
        self.language = language

    def reset_tab_widget(self):
        pass

    def reset_video_setting_ui(self) -> None:
        pass

    def reset_image_setting_ui(self) -> None:
        pass

    def reset_web_setting_ui(self) -> None:
        pass

    def reset_gif_setting_ui(self) -> None:
        pass

    def reset_sound_player_setting_ui(self) -> None:
        pass

    def reset_control_center_ui(self) -> None:
        pass


language_wrapper = LanguageWrapper()
