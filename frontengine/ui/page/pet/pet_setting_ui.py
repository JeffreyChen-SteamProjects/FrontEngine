from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QPushButton, QMessageBox, QComboBox, QCheckBox, QFileDialog,
)

from frontengine.show.pet.desktop_pet import (
    DesktopPetWidget, BEHAVIOUR_FLOOR, BEHAVIOUR_WANDER, BEHAVIOUR_CHASE, PetTagGame, scan_pet_pack,
)
from frontengine.ui.dialog.choose_file_dialog import choose_pet, choose_wav_sound
from frontengine.ui.page.utils import (
    apply_checkbox_state,
    apply_combobox_data_state,
    apply_combobox_text_state,
    build_recent_combobox,
    build_target_monitor_combobox,
    enable_file_drop,
    reload_recent_combobox,
    resolve_preferred_monitor,
)
from frontengine.user_setting.user_setting_file import add_recent_file
from frontengine.utils.audio_meter.microphone_meter import microphone_level
from frontengine.utils.audio_meter.screen_audio import audio_level_provider_for_screen
from frontengine.utils.pet_chat.pet_chat_service import PetChatService
from frontengine.utils.focus_timer.focus_timer import (
    PHASE_BREAK, PHASE_FOCUS, PHASE_LONG_BREAK, FocusTimer,
)
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator

_PET_EXTENSIONS = (".gif", ".webp", ".png", ".jpg")


# 多處共用的英文備援字串（只有在翻譯缺漏時才會看到）
# The English fallback shared by several call sites, seen only when a
# translation is missing.
_CHOOSE_PACK = "Choose pet pack..."


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
        self.pet_sound_path: Optional[str] = None
        # 鬼抓人：由本頁統一驅動，寵物只負責套用被指派的角色
        # Tag game: driven from this page, pets only apply the role they are given.
        self.tag_game = PetTagGame()
        self.tag_timer = QTimer(self)
        self.tag_timer.timeout.connect(self._tick_tag_game)
        # 專注計時：寵物在每個階段開始時說一句，並在旁邊陪著
        # Focus timer: the pet announces each phase and keeps you company.
        self.focus_timer = FocusTimer()
        self.focus_tick_timer = QTimer(self)
        self.focus_tick_timer.timeout.connect(self._tick_focus_timer)
        # AI 對話服務（懶建立，沒有金鑰就自動不可用）
        # Lazily built chat service; reports itself unavailable without a key.
        self._chat_service = None

        # Choose file
        self.choose_file_button = QPushButton()
        retranslator.bind(self.choose_file_button, "pet_choose_file",
                          "Choose pet sprite")
        self.choose_file_button.clicked.connect(self.choose_and_play)
        self.choose_pack_button = QPushButton()
        retranslator.bind(self.choose_pack_button, "pet_choose_pack",
                          _CHOOSE_PACK)
        self.choose_pack_button.clicked.connect(self.choose_pack)
        self.choose_sound_button = QPushButton()
        retranslator.bind(self.choose_sound_button, "pet_choose_sound",
                          "Choose sound (optional)")
        self.choose_sound_button.clicked.connect(self.choose_sound)
        self.ready_label = QLabel()
        retranslator.bind(self.ready_label, "Not Ready")

        # Size
        self.size_label = QLabel()
        retranslator.bind(self.size_label, "pet_size_label",
                          "Size")
        self.size_combobox = QComboBox()
        self.size_combobox.addItems(["64", "96", "128", "192", "256"])
        self.size_combobox.setCurrentText("128")

        # Speed
        self.speed_label = QLabel()
        retranslator.bind(self.speed_label, "pet_speed_label",
                          "Speed")
        self.speed_combobox = QComboBox()
        self.speed_combobox.addItems([str(n) for n in range(1, 11)])
        self.speed_combobox.setCurrentText("3")

        # Behaviour
        self.behaviour_label = QLabel()
        retranslator.bind(self.behaviour_label, "pet_behaviour_label",
                          "Behaviour")
        self.behaviour_combobox = QComboBox()
        self.behaviour_combobox.addItem(
            language_wrapper.language_word_dict.get("pet_behaviour_floor", "Walk on floor"), BEHAVIOUR_FLOOR)
        self.behaviour_combobox.addItem(
            language_wrapper.language_word_dict.get("pet_behaviour_wander", "Free wander"), BEHAVIOUR_WANDER)
        self.behaviour_combobox.addItem(
            language_wrapper.language_word_dict.get("pet_behaviour_chase", "Chase cursor"), BEHAVIOUR_CHASE)

        # Climb walls / ceiling (only meaningful in floor mode)
        self.climb_checkbox = QCheckBox()
        retranslator.bind(self.climb_checkbox, "pet_climb_label",
                          "Climb walls")
        self.climb_checkbox.setChecked(True)
        self.talk_checkbox = QCheckBox()
        retranslator.bind(self.talk_checkbox, "pet_talk_label",
                          "Speech bubbles")
        self.talk_checkbox.setChecked(True)
        self.sit_checkbox = QCheckBox()
        retranslator.bind(self.sit_checkbox, "pet_sit_label",
                          "Sit on windows")
        self.sit_checkbox.setChecked(True)
        self.tag_checkbox = QCheckBox()
        retranslator.bind(self.tag_checkbox, "pet_tag_label",
                          "Play tag with each other")
        self.tag_checkbox.toggled.connect(self._on_tag_toggled)
        self.speech_checkbox = QCheckBox()
        retranslator.bind(self.speech_checkbox, "pet_speech_label",
                          "Speak out loud")
        self.chat_checkbox = QCheckBox()
        retranslator.bind(self.chat_checkbox, "pet_chat_label",
                          "AI chat (needs API key)")
        self.chat_checkbox.setToolTip(
            language_wrapper.language_word_dict.get(
                "pet_chat_hint",
                "Reads the ANTHROPIC_API_KEY environment variable; the key is never stored."))

        # Focus timer (pomodoro) controls
        self.focus_label = QLabel()
        retranslator.bind(self.focus_label, "pet_focus_label",
                          "Focus timer (min)")
        self.focus_minutes_combobox = QComboBox()
        self.focus_minutes_combobox.addItems(["15", "20", "25", "30", "45", "50"])
        self.focus_minutes_combobox.setCurrentText("25")
        self.break_minutes_combobox = QComboBox()
        self.break_minutes_combobox.addItems(["3", "5", "10", "15"])
        self.break_minutes_combobox.setCurrentText("5")
        self.focus_button = QPushButton()
        retranslator.bind(self.focus_button, "pet_focus_start",
                          "Start focus")
        self.focus_button.clicked.connect(self.toggle_focus_session)

        # Target monitor + sound volume
        self.target_monitor_label = QLabel()
        retranslator.bind(self.target_monitor_label, "target_monitor_label",
                          "Target monitor")
        self.target_monitor_combobox = build_target_monitor_combobox()
        self.volume_label = QLabel()
        retranslator.bind(self.volume_label, "pet_volume_label",
                          "Volume")
        self.volume_combobox = QComboBox()
        for label, value in (("0%", 0), ("25%", 25), ("50%", 50), ("75%", 75), ("100%", 100)):
            self.volume_combobox.addItem(label, value)
        self.volume_combobox.setCurrentText("100%")
        self.audio_source_combobox = QComboBox()
        self.audio_source_combobox.addItem(
            language_wrapper.language_word_dict.get("pet_audio_speakers", "Speakers"), "speakers")
        self.audio_source_combobox.addItem(
            language_wrapper.language_word_dict.get("pet_audio_microphone", "Microphone"),
            "microphone")
        self.audio_react_checkbox = QCheckBox()
        retranslator.bind(self.audio_react_checkbox, "pet_audio_label",
                          "React to audio")
        self.drop_hint_label = QLabel()
        retranslator.bind(self.drop_hint_label, "pet_drop_hint",
                          "Tip: drop an image or pet pack onto the pet to change its look, "
                "or any other file to feed it.")
        self.drop_hint_label.setWordWrap(True)

        # Start
        self.start_button = QPushButton()
        retranslator.bind(self.start_button, "pet_start",
                          "Spawn pet")
        self.start_button.clicked.connect(self.start_play_pet)

        # Recent files
        self.recent_files_label = QLabel()
        retranslator.bind(self.recent_files_label, "recent_files_label",
                          "Recent")
        self.recent_files_combobox = build_recent_combobox("pet")
        self.recent_files_combobox.activated.connect(self._apply_recent_file)

        # Drag and drop
        self._drop_filter = enable_file_drop(self, _PET_EXTENSIONS, self._on_file_dropped)

        # Layout
        self.grid_layout.addWidget(self.choose_file_button, 0, 0)
        self.grid_layout.addWidget(self.ready_label, 0, 1)
        self.grid_layout.addWidget(self.choose_pack_button, 0, 2)
        self.grid_layout.addWidget(self.choose_sound_button, 1, 2)
        self.grid_layout.addWidget(self.size_label, 1, 0)
        self.grid_layout.addWidget(self.size_combobox, 1, 1)
        self.grid_layout.addWidget(self.speed_label, 2, 0)
        self.grid_layout.addWidget(self.speed_combobox, 2, 1)
        self.grid_layout.addWidget(self.behaviour_label, 3, 0)
        self.grid_layout.addWidget(self.behaviour_combobox, 3, 1)
        self.grid_layout.addWidget(self.climb_checkbox, 3, 2)
        self.grid_layout.addWidget(self.talk_checkbox, 2, 2)
        self.grid_layout.addWidget(self.sit_checkbox, 4, 2)
        self.grid_layout.addWidget(self.start_button, 4, 0)
        self.grid_layout.addWidget(self.recent_files_label, 5, 0)
        self.grid_layout.addWidget(self.recent_files_combobox, 5, 1)
        self.grid_layout.addWidget(self.target_monitor_label, 6, 0)
        self.grid_layout.addWidget(self.target_monitor_combobox, 6, 1)
        self.grid_layout.addWidget(self.volume_label, 6, 2)
        self.grid_layout.addWidget(self.volume_combobox, 7, 2)
        self.grid_layout.addWidget(self.audio_react_checkbox, 7, 0)
        self.grid_layout.addWidget(self.audio_source_combobox, 7, 1)
        self.grid_layout.addWidget(self.tag_checkbox, 7, 1)
        self.grid_layout.addWidget(self.speech_checkbox, 7, 2)
        self.grid_layout.addWidget(self.focus_label, 8, 0)
        self.grid_layout.addWidget(self.focus_minutes_combobox, 8, 1)
        self.grid_layout.addWidget(self.break_minutes_combobox, 8, 2)
        self.grid_layout.addWidget(self.focus_button, 9, 0)
        self.grid_layout.addWidget(self.chat_checkbox, 9, 1)
        self.grid_layout.addWidget(self.drop_hint_label, 10, 0, 1, 3)

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
            talk=self.talk_checkbox.isChecked(),
            sound_path=self.pet_sound_path,
            sit_on_windows=self.sit_checkbox.isChecked(),
            volume=int(self.volume_combobox.currentData()) / 100.0,
            audio_react=self.audio_react_checkbox.isChecked(),
        )
        pet.clone_requested.connect(self._spawn_pet)
        pet.set_peers_provider(lambda me=pet: self._peer_centers(me))
        if self.speech_checkbox.isChecked():
            pet.set_speech_enabled(True)
        if self.chat_checkbox.isChecked():
            pet.set_chat_service(self.chat_service())
        geometry = self._target_geometry()
        if self.audio_react_checkbox.isChecked():
            pet.set_audio_level_provider(self._audio_provider(geometry))
        pet.set_pet_window_flag()
        self.pet_list.append(pet)
        pet.show()
        self._start_tag_game()
        if geometry is not None:
            pet.setScreen(geometry[1])
            bounds = geometry[0]
            pet.start_moving((bounds.left(), bounds.top(), bounds.right(), bounds.bottom()))

    def chat_service(self) -> PetChatService:
        """共用的 AI 對話服務（懶建立；沒有金鑰時它自己會回報不可用）。"""
        if self._chat_service is None:
            self._chat_service = PetChatService()
        return self._chat_service

    # --- focus timer -----------------------------------------------------
    FOCUS_TICK_MS = 1000

    def toggle_focus_session(self) -> None:
        """開始或停止一次專注（沒有寵物時仍可計時，只是沒人陪你）。"""
        if self.focus_timer.running:
            self.stop_focus_session()
        else:
            self.start_focus_session()

    def start_focus_session(self) -> None:
        """依目前設定開始專注，並讓寵物宣布 / Start focusing; the pet announces it."""
        self.focus_timer.focus_minutes = int(self.focus_minutes_combobox.currentText())
        self.focus_timer.break_minutes = int(self.break_minutes_combobox.currentText())
        self.focus_timer.start()
        front_engine_logger.info(
            f"[PetSettingUI] focus started | focus={self.focus_timer.focus_minutes}, "
            f"break={self.focus_timer.break_minutes}"
        )
        self.focus_tick_timer.start(self.FOCUS_TICK_MS)
        self._announce_focus("focus_start")
        self.focus_button.setText(
            language_wrapper.language_word_dict.get("pet_focus_stop", "Stop focus"))

    def stop_focus_session(self) -> None:
        """停止專注 / Stop the focus session."""
        front_engine_logger.info("[PetSettingUI] focus stopped")
        self.focus_timer.stop()
        self.focus_tick_timer.stop()
        self.focus_button.setText(
            language_wrapper.language_word_dict.get("pet_focus_start", "Start focus"))

    def _tick_focus_timer(self) -> None:
        """每秒推進一次；換階段時讓寵物說話。"""
        phase = self.focus_timer.tick()
        if phase is None:
            return
        if phase == PHASE_FOCUS:
            self._announce_focus("focus_back")
        elif phase == PHASE_BREAK:
            self._announce_focus("focus_break")
        elif phase == PHASE_LONG_BREAK:
            self._announce_focus("focus_done")

    def _announce_focus(self, pool_name: str) -> None:
        """讓所有寵物說出該階段的台詞（沒有寵物就安靜略過）。"""
        for pet in self._alive_pets():
            pool = pet._messages.get(pool_name) or []
            if pool:
                pet.say(pool[0])

    def _target_geometry(self):
        """回傳 (available_geometry, screen) 依所選目標螢幕，否則主螢幕。"""
        screens = QGuiApplication.screens()
        index = resolve_preferred_monitor(self.target_monitor_combobox)
        if index is not None and 0 <= index < len(screens):
            screen = screens[index]
        else:
            screen = QGuiApplication.primaryScreen()
        if screen is None:
            return None
        return (screen.availableGeometry(), screen)

    def _alive_pets(self) -> list:
        """回傳仍存活的寵物，並把已被銷毀者從清單移除。"""
        alive = []
        for pet in self.pet_list[:]:
            try:
                pet.center()
            except RuntimeError:
                self.pet_list.remove(pet)  # underlying C++ object already deleted
                continue
            alive.append(pet)
        return alive

    def _peer_centers(self, me) -> list:
        """回傳其他仍存活寵物的中心座標（略過已被銷毀者）。"""
        return [pet.center() for pet in self._alive_pets() if pet is not me]

    TAG_INTERVAL_MS = 100

    def _on_tag_toggled(self, checked: bool) -> None:
        """切換鬼抓人：關掉時停錶並把所有寵物放回平常的行為。"""
        front_engine_logger.info(f"[PetSettingUI] tag game | enabled={checked}")
        if checked:
            self._start_tag_game()
            return
        self.tag_timer.stop()
        self.tag_game.reset()
        for pet in self._alive_pets():
            pet.apply_tag_role(None)

    def _start_tag_game(self) -> None:
        """有兩隻以上寵物且已勾選時才需要開錶 / Only run the game with 2+ pets."""
        if self.tag_checkbox.isChecked() and len(self._alive_pets()) >= 2:
            if not self.tag_timer.isActive():
                self.tag_timer.start(self.TAG_INTERVAL_MS)

    def _tick_tag_game(self) -> None:
        """每一拍把座標餵給遊戲，再把角色發回各隻寵物。"""
        pets = self._alive_pets()
        if len(pets) < 2:
            self.tag_timer.stop()
            self.tag_game.reset()
            for pet in pets:
                pet.apply_tag_role(None)
            return
        # 用每隻寵物的物件識別碼當鍵，避免有寵物關閉後索引位移導致「鬼」換人
        # Key by object identity so closing a pet cannot shift who is "it".
        by_key = {id(pet): pet for pet in pets}
        roles = self.tag_game.update({key: pet.center() for key, pet in by_key.items()})
        tagged = self.tag_game.just_tagged
        for key, pet in by_key.items():
            pet.apply_tag_role(roles.get(key))
            if key == tagged:
                pet.on_tagged()

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

    def choose_sound(self) -> None:
        """選擇點擊時播放的音效（選填）/ Choose an optional click sound."""
        front_engine_logger.info("[PetSettingUI] choose_sound")
        path = choose_wav_sound(self)
        if path:
            self.pet_sound_path = path

    def choose_pack(self) -> None:
        """選擇動作包資料夾（依 walk/idle/climb/fall/drag 檔名對應狀態）。"""
        front_engine_logger.info("[PetSettingUI] choose_pack")
        folder = QFileDialog.getExistingDirectory(
            self, language_wrapper.language_word_dict.get("pet_choose_pack", _CHOOSE_PACK)
        )
        if not folder:
            return
        if not scan_pet_pack(folder):
            QMessageBox.warning(
                self,
                language_wrapper.language_word_dict.get("pet_choose_pack", _CHOOSE_PACK),
                language_wrapper.language_word_dict.get(
                    "pet_pack_empty", "No sprites (walk/idle/climb/fall/drag) found in that folder."),
            )
            return
        self.pet_image_path = folder
        self.ready_to_play = True
        self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
        add_recent_file("pet", folder)
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

    def _audio_provider(self, geometry):
        """
        寵物要跟著什麼聲音動：喇叭（跟隨牠所在螢幕的輸出裝置）或麥克風
        （你說話時牠才動）。兩者都只讀電表數值，不擷取音訊內容。
        What the pet reacts to: the speakers on its own screen, or the
        microphone so it only moves while you talk. Both read a meter value and
        capture no audio content.
        """
        if self.audio_source_combobox.currentData() == "microphone":
            return microphone_level
        # 跟隨寵物所在螢幕的音源（比對不到就用系統預設輸出裝置）
        # Follow the audio of the screen the pet lives on; default endpoint otherwise.
        return audio_level_provider_for_screen(geometry[1] if geometry is not None else None)

    def get_state(self) -> dict:
        return {
            "pet_image_path": self.pet_image_path,
            "size": self.size_combobox.currentText(),
            "speed": self.speed_combobox.currentText(),
            "behaviour": self.behaviour_combobox.currentData(),
            "climb": self.climb_checkbox.isChecked(),
            "talk": self.talk_checkbox.isChecked(),
            "sound": self.pet_sound_path,
            "sit": self.sit_checkbox.isChecked(),
            "target_monitor": self.target_monitor_combobox.currentText(),
            "volume": self.volume_combobox.currentText(),
            "audio_react": self.audio_react_checkbox.isChecked(),
            "audio_source": self.audio_source_combobox.currentData(),
            "tag": self.tag_checkbox.isChecked(),
            "speech": self.speech_checkbox.isChecked(),
            "chat": self.chat_checkbox.isChecked(),
            "focus_minutes": self.focus_minutes_combobox.currentText(),
            "break_minutes": self.break_minutes_combobox.currentText(),
        }

    def set_state(self, state: dict) -> None:
        """把預設集的內容還原到這一頁的控制項上。"""
        self._restore_media(state)
        apply_combobox_data_state(self.behaviour_combobox, self._behaviour_from(state))
        apply_combobox_data_state(self.audio_source_combobox, state.get("audio_source"))
        apply_combobox_text_state(state, (
            (self.size_combobox, "size"),
            (self.speed_combobox, "speed"),
            (self.target_monitor_combobox, "target_monitor"),
            (self.volume_combobox, "volume"),
            (self.focus_minutes_combobox, "focus_minutes"),
            (self.break_minutes_combobox, "break_minutes"),
        ))
        apply_checkbox_state(state, (
            (self.climb_checkbox, "climb"),
            (self.talk_checkbox, "talk"),
            (self.sit_checkbox, "sit"),
            (self.audio_react_checkbox, "audio_react"),
            (self.tag_checkbox, "tag"),
            (self.speech_checkbox, "speech"),
            (self.chat_checkbox, "chat"),
        ))

    def _restore_media(self, state: dict) -> None:
        """還原圖片與音效的路徑（有圖才算準備好可以放）。"""
        if state.get("pet_image_path"):
            self.pet_image_path = state["pet_image_path"]
            self.ready_to_play = True
            self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
        if state.get("sound"):
            self.pet_sound_path = str(state["sound"])

    @staticmethod
    def _behaviour_from(state: dict):
        """
        取出行為模式。舊的預設集只存了 gravity 布林值，這裡把它翻譯成對應的
        行為，免得舊檔案還原後寵物不會動。
        The behaviour to use. Older presets only stored a `gravity` flag, so it
        is translated here rather than leaving an old file with no behaviour.
        """
        behaviour = state.get("behaviour")
        if behaviour is None and "gravity" in state:
            behaviour = BEHAVIOUR_FLOOR if state.get("gravity") else BEHAVIOUR_WANDER
        return behaviour
