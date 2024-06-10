from PySide6.QtGui import QScreen
from PySide6.QtWidgets import QWidget, QDialog, QGridLayout, QLabel, QComboBox, QPushButton, QCheckBox

from frontengine.utils.multi_language.language_wrapper import language_wrapper


def monitor_choose_dialog(parent: QWidget, monitors: list):
    input_dialog = QDialog(parent)
    input_dialog.setWindowTitle(language_wrapper.language_word_dict.get("show_on_which_monitor"))
    grid_layout = QGridLayout()
    label = QLabel(language_wrapper.language_word_dict.get("show_on_which_monitor"))
    combobox = QComboBox()
    ok_button = QPushButton(language_wrapper.language_word_dict.get("ok"))
    ok_button.clicked.connect(input_dialog.accept)
    no_button = QPushButton(language_wrapper.language_word_dict.get("no"))
    no_button.clicked.connect(input_dialog.reject)
    for index in range(len(monitors)):
        combobox.addItem(str(index))
    grid_layout.addWidget(label, 0, 0)
    grid_layout.addWidget(combobox, 1, 0)
    grid_layout.addWidget(ok_button, 2, 0)
    grid_layout.addWidget(no_button, 2, 1)
    input_dialog.setLayout(grid_layout)
    return input_dialog, combobox


def check_show_fullscreen_multi_screen(widget: QWidget, fullscreen_checkbox: QCheckBox, monitor: QScreen):
    if fullscreen_checkbox.isChecked():
        widget.setScreen(monitor)
        widget.move(monitor.availableGeometry().topLeft())
        widget.showFullScreen()
    else:
        widget.setScreen(monitor)
        center = monitor.availableGeometry().center()
        widget.move(center - widget.rect().center())
        widget.show()


def check_show_fullscreen_one_screen(widget: QWidget, fullscreen_checkbox: QCheckBox):
    if fullscreen_checkbox.isChecked():
        widget.showFullScreen()
    else:
        widget.show()
