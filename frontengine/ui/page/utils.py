from typing import Callable, Optional

from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QGridLayout, QLabel, QPushButton, QWidget

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


def dispatch_to_monitors(
    parent: QWidget,
    show_all_screen: bool,
    factory: Callable[[Optional[QScreen]], QWidget],
    present_primary: Callable[[QWidget], None],
    present_on_monitor: Callable[[QWidget, QScreen, int], None],
    preferred_monitor_index: Optional[int] = None,
) -> None:
    """
    Run the canonical monitor-dispatch flow the setting pages share:
    on a single-monitor system run `present_primary`, on a multi-monitor
    system either prompt the user to pick one or iterate all monitors.

    `factory` receives the target monitor (or None for the primary path)
    so callers can pass monitor geometry into widget construction if
    needed. `preferred_monitor_index` lets callers pre-select a specific
    monitor so the user is not prompted; out-of-range values fall back
    to the prompt flow.
    """
    monitors = QGuiApplication.screens()
    if not show_all_screen and len(monitors) <= 1:
        widget = factory(None)
        present_primary(widget)
        return

    if not show_all_screen and preferred_monitor_index is not None and \
            0 <= preferred_monitor_index < len(monitors):
        monitor = monitors[preferred_monitor_index]
        widget = factory(monitor)
        present_on_monitor(widget, monitor, preferred_monitor_index)
        return

    if not show_all_screen and len(monitors) >= 2:
        input_dialog, combobox = create_monitor_selection_dialog(parent, monitors)
        if input_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        index = int(combobox.currentText())
        if index >= len(monitors):
            return
        monitor = monitors[index]
        widget = factory(monitor)
        present_on_monitor(widget, monitor, index)
        return

    for index, monitor in enumerate(monitors):
        widget = factory(monitor)
        present_on_monitor(widget, monitor, index)


def build_target_monitor_combobox() -> QComboBox:
    """
    Build a combobox listing the current monitors plus an initial "Ask"
    entry. Selection "Ask" (data=None) preserves today's prompt flow;
    selecting a monitor index pre-selects that screen.
    """
    combobox = QComboBox()
    combobox.addItem(language_wrapper.language_word_dict.get("target_monitor_ask", "Ask"), None)
    for index, _ in enumerate(QGuiApplication.screens()):
        combobox.addItem(str(index), index)
    return combobox


def resolve_preferred_monitor(combobox: Optional[QComboBox]) -> Optional[int]:
    """Return the selected monitor index, or None for the Ask entry."""
    if combobox is None:
        return None
    data = combobox.currentData()
    return int(data) if isinstance(data, int) else None