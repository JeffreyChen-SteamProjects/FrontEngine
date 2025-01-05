from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QMessageBox, QSlider, QLabel, QLineEdit, QPushButton, QComboBox

from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.user_setting.scene_setting import scene_json
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class TextSceneSettingUI(QWidget):

    def __init__(self, script_ui: SceneManagerUI):
        front_engine_logger.info(f"Init TextSceneSettingUI script_ui: {script_ui}")
        super().__init__()
        self.script_ui = script_ui
        # Opacity setting
        self.opacity_slider = QSlider()
        self.opacity_slider.setOrientation(Qt.Orientation.Horizontal)
        self.opacity_label = QLabel(
            language_wrapper.language_word_dict.get("Opacity")
        )
        self.opacity_slider.setMinimum(1)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(20)
        self.opacity_slider.setTickInterval(1)
        self.opacity_slider_value_label = QLabel(str(self.opacity_slider.value()))
        self.opacity_slider.actionTriggered.connect(self.opacity_trick)
        # Font size setting
        self.font_size_slider = QSlider()
        self.font_size_slider.setOrientation(Qt.Orientation.Horizontal)
        self.font_size_label = QLabel(
            language_wrapper.language_word_dict.get("Font size")
        )
        self.font_size_slider.setMinimum(1)
        self.font_size_slider.setMaximum(600)
        self.font_size_slider.setValue(100)
        self.font_size_slider.setTickInterval(1)
        self.font_size_slider_value_label = QLabel(str(self.font_size_slider.value()))
        self.font_size_slider.actionTriggered.connect(self.font_size_trick)
        # Font input button
        self.line_edit = QLineEdit()
        self.update_scene_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_text")
        )
        self.update_scene_button.clicked.connect(self.update_scene_json)
        # Text position
        self.text_position_label = QLabel(
            language_wrapper.language_word_dict.get("text_setting_choose_alignment")
        )
        self.text_position_combobox = QComboBox()
        self.text_position_combobox.addItem("TopLeft")
        self.text_position_combobox.addItem("TopRight")
        self.text_position_combobox.addItem("BottomLeft")
        self.text_position_combobox.addItem("BottomRight")
        self.text_position_combobox.addItem("Center")

        self.grid_layout = QGridLayout()
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.font_size_label, 1, 0)
        self.grid_layout.addWidget(self.font_size_slider_value_label, 1, 1)
        self.grid_layout.addWidget(self.font_size_slider, 1, 2)
        self.grid_layout.addWidget(self.text_position_label, 2, 0)
        self.grid_layout.addWidget(self.text_position_combobox, 2, 1)
        self.grid_layout.addWidget(self.update_scene_button, 3, 0)
        self.grid_layout.addWidget(self.line_edit, 3, 1)
        self.setLayout(self.grid_layout)

    def opacity_trick(self) -> None:
        front_engine_logger.info("TextSceneSettingUI opacity_trick")
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def font_size_trick(self) -> None:
        front_engine_logger.info("TextSceneSettingUI font_size_trick")
        self.font_size_slider_value_label.setText(str(self.font_size_slider.value()))

    def update_scene_json(self):
        front_engine_logger.info("TextSceneSettingUI update_scene_json")
        if self.line_edit.text() == "" or self.line_edit.text().strip() == "":
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get('not_prepare')
            )
            message_box.show()
        else:
            scene_json.update(
                {
                    f"{len(scene_json)}": {
                        "type": "TEXT",
                        "text": self.line_edit.text(),
                        "font_size": self.font_size_slider.value(),
                        "opacity": self.opacity_slider.value(),
                        "alignment": self.text_position_combobox.currentText()
                    }
                }
            )
            self.script_ui.renew_json_plain_text()
