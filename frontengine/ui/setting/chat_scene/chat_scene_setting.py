from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QTextEdit, QScrollArea, QComboBox, QLabel

from frontengine.ui.chat.chat_scene_input import ChatInputDialog
from frontengine.ui.chat.chatthread import ChatThread, DELEGATE_CHAT
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ChatSceneUI(QWidget):

    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout()
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
        # New topic button
        self.new_topic_button = QPushButton(language_wrapper.language_word_dict.get("chat_scene_new_topic"))
        self.new_topic_button.clicked.connect(self.new_topic)
        # Start button
        self.start_button = QPushButton(language_wrapper.language_word_dict.get("chat_scene_start_button"))
        self.start_button.clicked.connect(self.start_chat)
        # Chat panel
        self.chat_panel = QTextEdit()
        self.chat_panel.setLineWrapMode(self.chat_panel.LineWrapMode.NoWrap)
        self.chat_panel.setReadOnly(True)
        self.chat_panel_scroll_area = QScrollArea()
        self.chat_panel_scroll_area.setWidgetResizable(True)
        self.chat_panel_scroll_area.setViewportMargins(0, 0, 0, 0)
        self.chat_panel_scroll_area.setWidget(self.chat_panel)
        # Add to layout
        self.grid_layout.addWidget(self.choose_style_combobox, 0, 0)
        self.grid_layout.addWidget(self.new_topic_button, 0, 1)
        self.grid_layout.addWidget(self.start_button, 0, 2)
        self.grid_layout.addWidget(self.chat_panel_scroll_area, 1, 0, -1, -1)
        self.setLayout(self.grid_layout)

    def start_chat(self) -> None:
        self.chat_input = ChatInputDialog()
        self.chat_input.show()
        self.chat_input.send_text_button.clicked.connect(self.send_chat)

    def send_chat(self):
        chat_thread = ChatThread(self.chat_panel, self.chat_input.chat_input.toPlainText())
        chat_thread.start()

    def change_style(self):
        DELEGATE_CHAT.change_style(self.choose_style_combobox.currentText())

    def new_topic(self):
        DELEGATE_CHAT.new_topic(self.chat_panel)

    def close_chat_ui(self):
        self.chat_input.close()
        self.chat_list.clear()

    def close(self) -> bool:
        self.close_chat_ui()
        return super().close()
