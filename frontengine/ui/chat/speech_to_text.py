import sys
import time

from PySide6.QtWidgets import QWidget, QPushButton, QBoxLayout, QLineEdit
from speech_recognition import Microphone
from speech_recognition import Recognizer
from speech_recognition import RequestError, UnknownValueError
from threading import Thread

from frontengine.utils.multi_language.language_wrapper import language_wrapper


def callback(recognizer: Recognizer, audio):
    try:
        print(recognizer.recognize_google(audio))
    except (RequestError, UnknownValueError) as error:
        print(repr(error), file=sys.stderr)


class ChatSpeechToText(QWidget):

    def __init__(self):
        super().__init__()
        # Recognize
        self.recognizer = Recognizer()
        try:
            self.microphone = Microphone()
        except IOError as error:
            print(repr(error), file=sys.stderr)
        # UI
        self.box_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.voice_text_edit = QLineEdit()
        self.start_listen_button = QPushButton(
            language_wrapper.language_word_dict.get("chat_recognizer_voice_button"))
        self.start_listen_button.clicked.connect(self.start_listener_thread)
        self.send_text_button = QPushButton(
            language_wrapper.language_word_dict.get("chat_scene_send_chat"))
        self.box_layout.addWidget(self.voice_text_edit)
        self.box_layout.addWidget(self.start_listen_button)
        self.box_layout.addWidget(self.send_text_button)
        self.setLayout(self.box_layout)

    def start_listener_thread(self):
        listener_thread = Thread(target=self.start_listener)
        listener_thread.daemon = True
        listener_thread.start()

    def start_listener(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
        stop_listening = self.recognizer.listen_in_background(self.microphone, callback)
        for receive_sound_time in range(50):
            time.sleep(0.1)
        stop_listening(wait_for_stop=False)
