from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton

from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.ui.page.scene_setting.scene_page.base_scene_page import BaseSceneSettingUI
from frontengine.utils.multi_language.retranslate import tr


class WebSceneSettingUI(BaseSceneSettingUI):
    def __init__(self, script_ui: SceneManagerUI):
        super().__init__(script_ui)

        opacity_label, self.opacity_value, self.opacity_slider = self._build_slider("Opacity", 1, 100, 20)

        self.url_label = tr(QLabel(), "scene_url_label")
        self.web_url_input = QLineEdit()

        self.update_scene_button = tr(QPushButton(), "scene_add_web")
        self.update_scene_button.clicked.connect(self._update_scene)

        self.grid_layout.addWidget(opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_value, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.url_label, 1, 0)
        self.grid_layout.addWidget(self.web_url_input, 1, 1)
        self.grid_layout.addWidget(self.update_scene_button, 2, 0)

    def _update_scene(self) -> None:
        if not self.web_url_input.text().strip():
            self._warn_not_prepared()
            return
        self._append_scene({
            "type": "WEB",
            "url": self.web_url_input.text(),
            "opacity": self.opacity_slider.value(),
        })
