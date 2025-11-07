from PySide6.QtGui import QScreen
from PySide6.QtWidgets import QWidget, QDialog, QGridLayout, QLabel, QComboBox, QPushButton, QCheckBox

from frontengine.utils.multi_language.language_wrapper import language_wrapper


def create_monitor_selection_dialog(parent: QWidget, monitors: list) -> tuple[QDialog, QComboBox]:
    """
    建立一個對話框，讓使用者選擇要顯示的螢幕
    Create a dialog for selecting which monitor to display on

    :param parent: 父視窗 (Parent widget)
    :param monitors: 可用螢幕清單 (List of available monitors)
    :return: (對話框物件, 下拉選單物件) (Dialog object, ComboBox object)
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(language_wrapper.language_word_dict.get("show_on_which_monitor"))

    layout = QGridLayout(dialog)

    # 標籤：顯示提示文字
    # Label: Display prompt text
    label = QLabel(language_wrapper.language_word_dict.get("show_on_which_monitor"))

    # 下拉選單：列出所有螢幕
    # ComboBox: List all monitors
    monitor_combobox = QComboBox()
    for index, _ in enumerate(monitors):
        monitor_combobox.addItem(str(index))

    # 確認與取消按鈕
    # OK and Cancel buttons
    ok_button = QPushButton(language_wrapper.language_word_dict.get("ok"))
    ok_button.clicked.connect(dialog.accept)

    cancel_button = QPushButton(language_wrapper.language_word_dict.get("no"))
    cancel_button.clicked.connect(dialog.reject)

    # 佈局配置
    # Layout arrangement
    layout.addWidget(label, 0, 0, 1, 2)
    layout.addWidget(monitor_combobox, 1, 0, 1, 2)
    layout.addWidget(ok_button, 2, 0)
    layout.addWidget(cancel_button, 2, 1)

    return dialog, monitor_combobox


def show_on_selected_monitor(widget: QWidget, fullscreen_checkbox: QCheckBox, monitor: QScreen) -> None:
    """
    在指定螢幕上顯示視窗，並依據是否全螢幕顯示
    Show the widget on the selected monitor, fullscreen if checked

    :param widget: 要顯示的視窗 (Widget to display)
    :param fullscreen_checkbox: 是否全螢幕的勾選框 (Checkbox for fullscreen option)
    :param monitor: 目標螢幕 (Target monitor)
    """
    widget.setScreen(monitor)

    if fullscreen_checkbox.isChecked():
        # 全螢幕顯示
        # Show in fullscreen
        widget.move(monitor.availableGeometry().topLeft())
        widget.showFullScreen()
    else:
        # 視窗置中顯示
        # Show centered on screen
        center = monitor.availableGeometry().center()
        widget.move(center - widget.rect().center())
        widget.show()


def show_on_primary_screen(widget: QWidget, fullscreen_checkbox: QCheckBox) -> None:
    """
    在主要螢幕顯示視窗，並依據是否全螢幕顯示
    Show the widget on the primary screen, fullscreen if checked

    :param widget: 要顯示的視窗 (Widget to display)
    :param fullscreen_checkbox: 是否全螢幕的勾選框 (Checkbox for fullscreen option)
    """
    if fullscreen_checkbox.isChecked():
        widget.showFullScreen()
    else:
        widget.show()