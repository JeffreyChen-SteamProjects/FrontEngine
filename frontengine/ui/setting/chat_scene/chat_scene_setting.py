from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QTextEdit, QScrollArea
from frontengine.utils.multi_language.language_wrapper import language_wrapper

from frontengine.ui.input.chat_scene_input import ChatInputDialog


class ChatSceneUI(QWidget):

    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_input = ChatInputDialog()
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
        self.grid_layout.addWidget(self.start_button, 0, 0)
        self.grid_layout.addWidget(self.chat_panel_scroll_area, 1, 0, -1, -1)
        self.setLayout(self.grid_layout)

    def start_chat(self) -> None:
        self.chat_input.show()

    def close_chat_ui(self):
        self.chat_input.close()
