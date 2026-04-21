from PySide6.QtWidgets import QComboBox, QLabel, QLineEdit, QPushButton

from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.ui.page.scene_setting.scene_page.base_scene_page import BaseSceneSettingUI
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class TextSceneSettingUI(BaseSceneSettingUI):
    def __init__(self, script_ui: SceneManagerUI):
        super().__init__(script_ui)

        opacity_label, self.opacity_value, self.opacity_slider = self._build_slider("Opacity", 1, 100, 20)
        font_size_label, self.font_size_value, self.font_size_slider = self._build_slider("Font size", 1, 600, 100)

        self.line_edit = QLineEdit()

        self.text_position_label = QLabel(language_wrapper.language_word_dict.get("text_setting_choose_alignment"))
        self.text_position_combobox = QComboBox()
        self.text_position_combobox.addItems(["TopLeft", "TopRight", "BottomLeft", "BottomRight", "Center"])

        self.update_scene_button = QPushButton(language_wrapper.language_word_dict.get("scene_add_text"))
        self.update_scene_button.clicked.connect(self._update_scene)

        self.grid_layout.addWidget(opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_value, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(font_size_label, 1, 0)
        self.grid_layout.addWidget(self.font_size_value, 1, 1)
        self.grid_layout.addWidget(self.font_size_slider, 1, 2)
        self.grid_layout.addWidget(self.text_position_label, 2, 0)
        self.grid_layout.addWidget(self.text_position_combobox, 2, 1)
        self.grid_layout.addWidget(self.update_scene_button, 3, 0)
        self.grid_layout.addWidget(self.line_edit, 3, 1)

    def _update_scene(self) -> None:
        if not self.line_edit.text().strip():
            self._warn_not_prepared()
            return
        self._append_scene({
            "type": "TEXT",
            "text": self.line_edit.text(),
            "font_size": self.font_size_slider.value(),
            "opacity": self.opacity_slider.value(),
            "alignment": self.text_position_combobox.currentText(),
        })
