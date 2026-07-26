from typing import Optional

from PySide6.QtWidgets import QPushButton

from frontengine.ui.dialog.choose_file_dialog import choose_player_sound
from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.ui.page.scene_setting.scene_page.base_scene_page import BaseSceneSettingUI
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator


class SoundSceneSettingUI(BaseSceneSettingUI):
    def __init__(self, script_ui: SceneManagerUI):
        super().__init__(script_ui)
        self.player_sound_path: Optional[str] = None

        volume_label, self.volume_value, self.volume_slider = self._build_slider("Volume", 1, 100, 100)

        self.choose_player_file_button = QPushButton(
            language_wrapper.language_word_dict.get("sound_player_setting_choose_sound_file")
        )
        retranslator.bind(self.choose_player_file_button, "sound_player_setting_choose_sound_file", "")
        self.player_ready_label = self._make_ready_label()
        self.choose_player_file_button.clicked.connect(
            self._wire_chooser(
                choose_player_sound,
                self.player_ready_label,
                on_chosen=lambda path: setattr(self, "player_sound_path", path),
                on_reset=lambda: setattr(self, "player_sound_path", None),
            )
        )

        self.update_scene_button = QPushButton(language_wrapper.language_word_dict.get("scene_add_sound"))
        retranslator.bind(self.update_scene_button, "scene_add_sound", "")
        self.update_scene_button.clicked.connect(self._update_scene)

        self.grid_layout.addWidget(volume_label, 0, 0)
        self.grid_layout.addWidget(self.volume_value, 0, 1)
        self.grid_layout.addWidget(self.volume_slider, 0, 2)
        self.grid_layout.addWidget(self.choose_player_file_button, 1, 0)
        self.grid_layout.addWidget(self.player_ready_label, 1, 1)
        self.grid_layout.addWidget(self.update_scene_button, 2, 0)

    def _update_scene(self) -> None:
        if not self.player_sound_path:
            self._warn_not_prepared()
            return
        self._append_scene({
            "type": "SOUND",
            "file_path": self.player_sound_path,
            "volume": self.volume_slider.value(),
        })
