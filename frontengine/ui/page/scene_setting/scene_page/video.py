from typing import Optional

from PySide6.QtWidgets import QPushButton

from frontengine.ui.dialog.choose_file_dialog import choose_video
from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.ui.page.scene_setting.scene_page.base_scene_page import BaseSceneSettingUI
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class VideoSceneSettingUI(BaseSceneSettingUI):
    def __init__(self, script_ui: SceneManagerUI):
        super().__init__(script_ui)
        self.video_path: Optional[str] = None

        opacity_label, self.opacity_value, self.opacity_slider = self._build_slider("Opacity", 1, 100, 20)
        play_rate_label, self.play_rate_value, self.play_rate_slider = self._build_slider("Play rate", 1, 200, 100)
        volume_label, self.volume_value, self.volume_slider = self._build_slider("Volume", 1, 100, 100)

        self.choose_file_button = QPushButton(language_wrapper.language_word_dict.get("video_setting_choose_file"))
        self.ready_label = self._make_ready_label()
        self.choose_file_button.clicked.connect(
            self._wire_chooser(
                choose_video,
                self.ready_label,
                on_chosen=lambda path: setattr(self, "video_path", path),
                on_reset=lambda: setattr(self, "video_path", None),
            )
        )

        self.update_scene_button = QPushButton(language_wrapper.language_word_dict.get("scene_add_video"))
        self.update_scene_button.clicked.connect(self._update_scene)

        self.grid_layout.addWidget(opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_value, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(play_rate_label, 1, 0)
        self.grid_layout.addWidget(self.play_rate_value, 1, 1)
        self.grid_layout.addWidget(self.play_rate_slider, 1, 2)
        self.grid_layout.addWidget(volume_label, 2, 0)
        self.grid_layout.addWidget(self.volume_value, 2, 1)
        self.grid_layout.addWidget(self.volume_slider, 2, 2)
        self.grid_layout.addWidget(self.choose_file_button, 3, 0)
        self.grid_layout.addWidget(self.ready_label, 3, 1)
        self.grid_layout.addWidget(self.update_scene_button, 4, 0)

    def _update_scene(self) -> None:
        if not self.video_path:
            self._warn_not_prepared()
            return
        self._append_scene({
            "type": "VIDEO",
            "file_path": self.video_path,
            "opacity": self.opacity_slider.value(),
            "volume": self.volume_slider.value(),
            "play_rate": self.play_rate_slider.value(),
        })
