import sys

from PySide6.QtWidgets import QMainWindow, QApplication, QGridLayout

from frontengine.show.sound.sound_effect import SoundEffectWidget


class FrontEngineMainUI(QMainWindow):

    def __init__(self):
        super().__init__()
        # User setting
        self.audio_device = None
        self.screen_device = None
        self.play_volume = None
        self.play_rate = None
        self.opacity = None
        # Init setting ui
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.test_widget = SoundEffectWidget()
        self.test_widget.showMaximized()

    def startup_setting(self):
        pass


def start_front_engine():
    new_editor = QApplication(sys.argv)
    window = FrontEngineMainUI()
    window.showMaximized()
    sys.exit(new_editor.exec())


start_front_engine()
