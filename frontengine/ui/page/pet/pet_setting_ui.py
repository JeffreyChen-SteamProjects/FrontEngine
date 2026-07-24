from typing import Optional

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QPushButton, QMessageBox, QComboBox, QCheckBox,
)

from frontengine.show.pet.desktop_pet import (
    DesktopPetWidget, BEHAVIOUR_FLOOR, BEHAVIOUR_WANDER, BEHAVIOUR_CHASE,
)
from frontengine.ui.dialog.choose_file_dialog import choose_pet
from frontengine.ui.page.utils import (
    build_recent_combobox,
    enable_file_drop,
    reload_recent_combobox,
)
from frontengine.user_setting.user_setting_file import add_recent_file
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper

_PET_EXTENSIONS = (".gif", ".webp", ".png", ".jpg")


class PetSettingUI(QWidget):
    def __init__(self):
        front_engine_logger.info("[PetSettingUI] Init")
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        # Init variable
        self.pet_list: list = []
        self.ready_to_play = False
        self.pet_image_path: Optional[str] = None

        # Choose file
        self.choose_file_button = QPushButton(
            language_wrapper.language_word_dict.get("pet_choose_file", "Choose pet sprite")
        )
        self.choose_file_button.clicked.connect(self.choose_and_play)
        self.ready_label = QLabel(language_wrapper.language_word_dict.get("Not Ready"))

        # Size
        self.size_label = QLabel(language_wrapper.language_word_dict.get("pet_size_label", "Size"))
        self.size_combobox = QComboBox()
        self.size_combobox.addItems(["64", "96", "128", "192", "256"])
        self.size_combobox.setCurrentText("128")

        # Speed
        self.speed_label = QLabel(language_wrapper.language_word_dict.get("pet_speed_label", "Speed"))
        self.speed_combobox = QComboBox()
        self.speed_combobox.addItems([str(n) for n in range(1, 11)])
        self.speed_combobox.setCurrentText("3")

        # Behaviour
        self.behaviour_label = QLabel(language_wrapper.language_word_dict.get("pet_behaviour_label", "Behaviour"))
        self.behaviour_combobox = QComboBox()
        self.behaviour_combobox.addItem(
            language_wrapper.language_word_dict.get("pet_behaviour_floor", "Walk on floor"), BEHAVIOUR_FLOOR)
        self.behaviour_combobox.addItem(
            language_wrapper.language_word_dict.get("pet_behaviour_wander", "Free wander"), BEHAVIOUR_WANDER)
        self.behaviour_combobox.addItem(
            language_wrapper.language_word_dict.get("pet_behaviour_chase", "Chase cursor"), BEHAVIOUR_CHASE)

        # Climb walls / ceiling (only meaningful in floor mode)
        self.climb_checkbox = QCheckBox(language_wrapper.language_word_dict.get("pet_climb_label", "Climb walls"))
        self.climb_checkbox.setChecked(True)

        # Start
        self.start_button = QPushButton(language_wrapper.language_word_dict.get("pet_start", "Spawn pet"))
        self.start_button.clicked.connect(self.start_play_pet)

        # Recent files
        self.recent_files_label = QLabel(language_wrapper.language_word_dict.get("recent_files_label", "Recent"))
        self.recent_files_combobox = build_recent_combobox("pet")
        self.recent_files_combobox.activated.connect(self._apply_recent_file)

        # Drag and drop
        self._drop_filter = enable_file_drop(self, _PET_EXTENSIONS, self._on_file_dropped)

        # Layout
        self.grid_layout.addWidget(self.choose_file_button, 0, 0)
        self.grid_layout.addWidget(self.ready_label, 0, 1)
        self.grid_layout.addWidget(self.size_label, 1, 0)
        self.grid_layout.addWidget(self.size_combobox, 1, 1)
        self.grid_layout.addWidget(self.speed_label, 2, 0)
        self.grid_layout.addWidget(self.speed_combobox, 2, 1)
        self.grid_layout.addWidget(self.behaviour_label, 3, 0)
        self.grid_layout.addWidget(self.behaviour_combobox, 3, 1)
        self.grid_layout.addWidget(self.climb_checkbox, 3, 2)
        self.grid_layout.addWidget(self.start_button, 4, 0)
        self.grid_layout.addWidget(self.recent_files_label, 5, 0)
        self.grid_layout.addWidget(self.recent_files_combobox, 5, 1)

    def _spawn_pet(self) -> None:
        """建立、顯示並開始移動一隻寵物（供 Start 與右鍵複製共用）。"""
        if not self.pet_image_path:
            return
        pet = DesktopPetWidget(
            image_path=self.pet_image_path,
            size=int(self.size_combobox.currentText()),
            speed=int(self.speed_combobox.currentText()),
            behaviour=self.behaviour_combobox.currentData(),
            climb=self.climb_checkbox.isChecked(),
        )
        pet.clone_requested.connect(self._spawn_pet)
        pet.set_pet_window_flag()
        self.pet_list.append(pet)
        screen = QGuiApplication.primaryScreen()
        geometry = screen.availableGeometry() if screen is not None else None
        pet.show()
        if geometry is not None:
            pet.start_moving((geometry.left(), geometry.top(), geometry.right(), geometry.bottom()))

    def start_play_pet(self) -> None:
        front_engine_logger.info("[PetSettingUI] start_play_pet")
        if not self.pet_image_path or not self.ready_to_play:
            message_box = QMessageBox(self)
            message_box.setText(language_wrapper.language_word_dict.get("not_prepare"))
            message_box.exec()
            return
        self._spawn_pet()

    def choose_and_play(self) -> None:
        front_engine_logger.info("[PetSettingUI] choose_and_play")
        self.ready_label.setText(language_wrapper.language_word_dict.get("Not Ready"))
        self.ready_to_play = False
        self.pet_image_path = choose_pet(self)
        if self.pet_image_path:
            self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
            self.ready_to_play = True
            add_recent_file("pet", self.pet_image_path)
            reload_recent_combobox(self.recent_files_combobox, "pet")

    def _apply_recent_file(self, _index: int = 0) -> None:
        path = self.recent_files_combobox.currentData()
        self.recent_files_combobox.setCurrentIndex(0)
        if not path:
            return
        self.pet_image_path = path
        self.ready_to_play = True
        self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))

    def _on_file_dropped(self, path: str) -> None:
        front_engine_logger.info(f"[PetSettingUI] _on_file_dropped | path={path}")
        self.pet_image_path = path
        self.ready_to_play = True
        self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
        add_recent_file("pet", path)
        reload_recent_combobox(self.recent_files_combobox, "pet")

    def get_state(self) -> dict:
        return {
            "pet_image_path": self.pet_image_path,
            "size": self.size_combobox.currentText(),
            "speed": self.speed_combobox.currentText(),
            "behaviour": self.behaviour_combobox.currentData(),
            "climb": self.climb_checkbox.isChecked(),
        }

    def set_state(self, state: dict) -> None:
        if state.get("pet_image_path"):
            self.pet_image_path = state["pet_image_path"]
            self.ready_to_play = True
            self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
        for combobox, key in ((self.size_combobox, "size"), (self.speed_combobox, "speed")):
            if state.get(key) is not None:
                index = combobox.findText(str(state[key]))
                if index >= 0:
                    combobox.setCurrentIndex(index)
        behaviour = state.get("behaviour")
        if behaviour is None and "gravity" in state:  # back-compat with old presets
            behaviour = BEHAVIOUR_FLOOR if state.get("gravity") else BEHAVIOUR_WANDER
        if behaviour is not None:
            index = self.behaviour_combobox.findData(behaviour)
            if index >= 0:
                self.behaviour_combobox.setCurrentIndex(index)
        if "climb" in state:
            self.climb_checkbox.setChecked(bool(state["climb"]))
