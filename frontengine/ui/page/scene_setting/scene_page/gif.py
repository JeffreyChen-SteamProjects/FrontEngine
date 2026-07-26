from typing import Optional

from PySide6.QtWidgets import QPushButton

from frontengine.ui.dialog.choose_file_dialog import choose_gif
from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.ui.page.scene_setting.scene_page.base_scene_page import BaseSceneSettingUI
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator


class GIFSceneSettingUI(BaseSceneSettingUI):
    def __init__(self, script_ui: SceneManagerUI):
        super().__init__(script_ui)
        self.gif_image_path: Optional[str] = None

        opacity_label, self.opacity_value, self.opacity_slider = self._build_slider("Opacity", 1, 100, 20)
        speed_label, self.speed_value, self.speed_slider = self._build_slider("Speed", 1, 200, 100)

        self.choose_file_button = QPushButton(language_wrapper.language_word_dict.get("gif_setting_ui_choose_file"))
        retranslator.bind(self.choose_file_button, "gif_setting_ui_choose_file", "")
        self.ready_label = self._make_ready_label()
        self.choose_file_button.clicked.connect(
            self._wire_chooser(
                choose_gif,
                self.ready_label,
                on_chosen=lambda path: setattr(self, "gif_image_path", path),
                on_reset=lambda: setattr(self, "gif_image_path", None),
            )
        )

        self.update_scene_button = QPushButton(language_wrapper.language_word_dict.get("scene_add_gif"))
        retranslator.bind(self.update_scene_button, "scene_add_gif", "")
        self.update_scene_button.clicked.connect(self._update_scene)

        self.grid_layout.addWidget(opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_value, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(speed_label, 1, 0)
        self.grid_layout.addWidget(self.speed_value, 1, 1)
        self.grid_layout.addWidget(self.speed_slider, 1, 2)
        self.grid_layout.addWidget(self.choose_file_button, 2, 0)
        self.grid_layout.addWidget(self.ready_label, 2, 1)
        self.grid_layout.addWidget(self.update_scene_button, 3, 0)

    def _update_scene(self) -> None:
        if not self.gif_image_path:
            self._warn_not_prepared()
            return
        self._append_scene({
            "type": "GIF",
            "file_path": self.gif_image_path,
            "opacity": self.opacity_slider.value(),
            "speed": self.speed_slider.value(),
        })
