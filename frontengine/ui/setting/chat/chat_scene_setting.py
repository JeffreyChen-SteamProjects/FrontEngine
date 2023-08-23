from typing import Dict, Callable

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QScrollArea, QComboBox, QLabel, \
    QPlainTextEdit, QLineEdit, QBoxLayout

from frontengine.show.scene.scene import SceneManager
from frontengine.ui.setting.chat.chat_model import load_scene_json, chat_model
from frontengine.ui.setting.chat.chat_scene_input import ChatInputDialog
from frontengine.ui.setting.chat.chatthread import ChatThread, DELEGATE_CHAT, PANEL_MESSAGE_QUEUE
from frontengine.ui.setting.chat.speech_to_text import ChatSpeechToText
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ChatSceneUI(QWidget):

    def __init__(self):
        super().__init__()
        self.voice_input = None
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # Init
        self.chat_input = ChatInputDialog()
        self.chat_list = list()
        self.choose_style_combobox = QComboBox()
        self.choose_style_combobox.addItems([
            language_wrapper.language_word_dict.get("chat_scene_creative"),
            language_wrapper.language_word_dict.get("chat_scene_precise"),
            language_wrapper.language_word_dict.get("chat_scene_balanced")
        ])
        self.choose_style_combobox.currentTextChanged.connect(self.change_style)
        self.param_key_name_list = [
            "widget_type", "file_path", "url", "text", "opacity", "speed", "volume", "font_size", "play_rate",
            "web_setting_open_local_file", "web_setting_open_enable_input", "position_x", "position_y"
        ]
        # New topic button
        self.new_topic_button = QPushButton(language_wrapper.language_word_dict.get("chat_scene_new_topic"))
        self.new_topic_button.clicked.connect(self.new_topic)
        # Start button
        self.start_button = QPushButton(language_wrapper.language_word_dict.get("chat_scene_start_button"))
        self.start_button.clicked.connect(self.start_chat)
        # Chat panel
        self.chat_panel = QPlainTextEdit()
        self.chat_panel.setLineWrapMode(self.chat_panel.LineWrapMode.NoWrap)
        self.chat_panel.setReadOnly(True)
        self.chat_panel_scroll_area = QScrollArea()
        self.chat_panel_scroll_area.setWidgetResizable(True)
        self.chat_panel_scroll_area.setViewportMargins(0, 0, 0, 0)
        self.chat_panel_scroll_area.setWidget(self.chat_panel)
        self.chat_panel.setFont(QFontDatabase.font(self.font().family(), "", 16))
        # Scene
        self.scene = SceneManager()
        self.scene_component: Dict[str, Callable] = {
            "IMAGE": self.scene.add_image,
            "GIF": self.scene.add_gif,
            "SOUND": self.scene.add_sound,
            "TEXT": self.scene.add_text,
            "VIDEO": self.scene.add_video,
            "WEB": self.scene.add_web,
            "EXTEND_UI_FILE": self.scene.add_extend_ui_file
        }
        # Font size combobox
        self.font_size_label = QLabel(language_wrapper.language_word_dict.get("Font size"))
        self.font_size_combobox = QComboBox()
        for font_size in range(2, 101, 2):
            self.font_size_combobox.addItem(str(font_size))
        self.font_size_combobox.setCurrentText("16")
        self.font_size_combobox.currentTextChanged.connect(self.update_panel_text_size)
        # Close delay combobox
        self.close_delay_label = QLabel(language_wrapper.language_word_dict.get("close_delay"))
        self.close_delay_combobox = QComboBox()
        for sec in range(1, 101, 1):
            self.close_delay_combobox.addItem(str(sec))
        self.close_delay_combobox.setCurrentText("10")
        # Load scene
        self.scene_input_button = QPushButton(language_wrapper.language_word_dict.get("scene_input"))
        self.scene_input_button.clicked.connect(lambda: load_scene_json(self))
        # Locale box
        self.locale_label = QLabel(language_wrapper.language_word_dict.get("country_code"))
        self.locale_input = QLineEdit()
        self.locale_input.setText("zh-tw")
        self.local_box = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.local_box.addWidget(self.locale_label)
        self.local_box.addWidget(self.locale_input)
        # Start voice input
        self.start_voice_input_button = QPushButton(
            language_wrapper.language_word_dict.get("start_chat_voice_input_ui"))
        self.start_voice_input_button.clicked.connect(self.start_voice_input)
        # Add to layout
        self.grid_layout.addWidget(self.choose_style_combobox, 0, 0)
        self.grid_layout.addWidget(self.close_delay_label, 0, 1)
        self.grid_layout.addWidget(self.close_delay_combobox, 0, 2)
        self.grid_layout.addWidget(self.font_size_label, 0, 3)
        self.grid_layout.addWidget(self.font_size_combobox, 0, 4)
        self.grid_layout.addLayout(self.local_box, 0, 5)
        self.grid_layout.addWidget(self.new_topic_button, 0, 6)
        self.grid_layout.addWidget(self.scene_input_button, 0, 7)
        self.grid_layout.addWidget(self.start_voice_input_button, 0, 8)
        self.grid_layout.addWidget(self.start_button, 0, 9)
        self.grid_layout.addWidget(self.chat_panel_scroll_area, 1, 0, -1, -1)
        self.setLayout(self.grid_layout)
        # update panel timer
        self.update_panel_timer = QTimer()
        self.update_panel_timer.setInterval(10)
        self.update_panel_timer.timeout.connect(self.update_panel)
        self.update_panel_timer.start()

    def update_panel(self):
        if not PANEL_MESSAGE_QUEUE.empty():
            text = PANEL_MESSAGE_QUEUE.get_nowait()
            self.chat_panel.appendPlainText(text)
            self.chat_panel.appendPlainText("\n")

    def update_panel_text_size(self):
        self.chat_panel.setFont(
            QFontDatabase.font(self.font().family(), "", int(self.font_size_combobox.currentText())))

    def start_chat(self) -> None:
        self.chat_input = ChatInputDialog(
            close_time=int(self.close_delay_combobox.currentText()) * 1000,
            font_size=int(self.font_size_combobox.currentText())
        )
        self.chat_input.show()
        self.chat_input.send_text_button.clicked.connect(self.send_chat)
        if chat_model.rowCount() > 0:
            self.start_scene()

    def start_voice_input(self):
        self.voice_input = ChatSpeechToText()
        self.voice_input.show()
        self.voice_input.send_text_button.clicked.connect(self.send_voice_chat)

    def send_voice_chat(self):
        chat_thread = ChatThread(self.voice_input.voice_text_edit.text(), self.locale_input.text())
        chat_thread.start()

    def send_chat(self):
        chat_thread = ChatThread(self.chat_input.chat_input.toPlainText(), self.locale_input.text())
        chat_thread.start()

    def change_style(self):
        DELEGATE_CHAT.change_style(self.choose_style_combobox.currentText())

    def new_topic(self):
        DELEGATE_CHAT.new_topic(self.chat_panel)
        self.chat_input.close()

    def close_chat_ui(self):
        self.chat_input.close()
        self.chat_input = None
        self.chat_list.clear()
        self.close_scene()

    def close_scene(self) -> None:
        self.scene.widget_list.clear()
        self.scene.graphic_view.close()
        front_engine_logger.info("close_scene")

    def start_scene(self) -> None:
        front_engine_logger.info("start_scene")
        for row in range(chat_model.rowCount()):
            widget_type_text = chat_model.item(row, 0).text()
            add_widget_function = self.scene_component.get(widget_type_text)
            param_dict: Dict[str, str] = dict()
            for column in range(1, chat_model.columnCount()):
                param = chat_model.item(row, column).text()
                if param != "":
                    param_dict.update({self.param_key_name_list[column]: param})
            add_widget_function(param_dict)
            front_engine_logger.info(f"start_scene type: {widget_type_text}, param: {param_dict}")
        self.scene.show()

    def close(self) -> bool:
        self.close_chat_ui()
        return super().close()
