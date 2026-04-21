from typing import Optional

from PySide6.QtWidgets import QPushButton

from frontengine.ui.dialog.choose_file_dialog import choose_image
from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.ui.page.scene_setting.scene_page.base_scene_page import BaseSceneSettingUI
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ImageSceneSettingUI(BaseSceneSettingUI):
    def __init__(self, script_ui: SceneManagerUI):
        super().__init__(script_ui)
        self.image_path: Optional[str] = None

        opacity_label, self.opacity_value, self.opacity_slider = self._build_slider("Opacity", 1, 100, 20)

        self.choose_file_button = QPushButton(language_wrapper.language_word_dict.get("image_setting_choose_file"))
        self.ready_label = self._make_ready_label()
        self.choose_file_button.clicked.connect(
            self._wire_chooser(
                choose_image,
                self.ready_label,
                on_chosen=lambda path: setattr(self, "image_path", path),
                on_reset=lambda: setattr(self, "image_path", None),
            )
        )

        self.update_scene_button = QPushButton(language_wrapper.language_word_dict.get("scene_add_image"))
        self.update_scene_button.clicked.connect(self._update_scene)

        self.grid_layout.addWidget(opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_value, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.choose_file_button, 1, 0)
        self.grid_layout.addWidget(self.ready_label, 1, 1)
        self.grid_layout.addWidget(self.update_scene_button, 2, 0)

    def _update_scene(self) -> None:
        if not self.image_path:
            self._warn_not_prepared()
            return
        self._append_scene({
            "type": "IMAGE",
            "file_path": self.image_path,
            "opacity": self.opacity_slider.value(),
        })
