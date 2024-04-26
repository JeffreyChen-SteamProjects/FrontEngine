from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QLabel, QSlider, QMessageBox

from frontengine.ui.dialog.choose_file_dialog import choose_image
from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.user_setting.scene_setting import scene_json
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ImageSceneSettingUI(QWidget):

    def __init__(self, script_ui: SceneManagerUI):
        super().__init__()
        self.script_ui = script_ui
        self.image_path: [str, None] = None
        self.ready_to_play = False
        # UI components
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
        # Choose file button
        self.choose_file_button = QPushButton(
            language_wrapper.language_word_dict.get("image_setting_choose_file")
        )
        self.choose_file_button.clicked.connect(self.get_image)
        self.ready_label = QLabel(
            language_wrapper.language_word_dict.get("Not Ready")
        )
        self.update_scene_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_image")
        )
        self.update_scene_button.clicked.connect(self.update_scene_json)
        # Add to layout
        self.grid_layout = QGridLayout()
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.choose_file_button, 1, 0)
        self.grid_layout.addWidget(self.ready_label, 1, 1)
        self.grid_layout.addWidget(self.update_scene_button, 2, 0)
        self.setLayout(self.grid_layout)

    def opacity_trick(self) -> None:
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def get_image(self):
        self.ready_label.setText(
            language_wrapper.language_word_dict.get("Not Ready")
        )
        self.ready_to_play = False
        self.image_path = choose_image(self)
        if self.image_path is not None:
            self.ready_label.setText(
                language_wrapper.language_word_dict.get("Ready")
            )
            self.ready_to_play = True

    def update_scene_json(self):
        if self.image_path is None:
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get('not_prepare')
            )
            message_box.show()
        else:
            scene_json.update(
                {
                    f"{len(scene_json)}": {
                        "type": "IMAGE",
                        "file_path": self.image_path,
                        "opacity": self.opacity_slider.value()
                    }
                }
            )
            self.script_ui.renew_json_plain_text()
