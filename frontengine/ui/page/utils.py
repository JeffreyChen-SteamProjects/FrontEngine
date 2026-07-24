from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QGridLayout, QLabel, QPushButton, QWidget

from frontengine.user_setting.user_setting_file import get_recent_files
from frontengine.utils.logging.loggin_instance import front_engine_logger
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


class _DropFileFilter(QObject):
    """
    事件過濾器：接受拖入且副檔名符合的檔案，並以其路徑呼叫 on_file。
    Event filter that accepts a dropped file whose suffix is allowed and calls
    ``on_file(path)`` with it. Installed via ``enable_file_drop``.
    """

    def __init__(self, extensions, on_file: Callable[[str], None], parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._extensions = {ext.lower() for ext in extensions}
        self._on_file = on_file

    def matching_path(self, mime_data) -> Optional[str]:
        if mime_data is None or not mime_data.hasUrls():
            return None
        for url in mime_data.urls():
            local = url.toLocalFile()
            if local and Path(local).suffix.lower() in self._extensions:
                return local
        return None

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        event_type = event.type()
        if event_type in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
            if self.matching_path(event.mimeData()) is not None:
                event.acceptProposedAction()
                return True
        elif event_type == QEvent.Type.Drop:
            path = self.matching_path(event.mimeData())
            if path is not None:
                event.acceptProposedAction()
                try:
                    self._on_file(path)
                except Exception as error:  # pragma: no cover - defensive boundary
                    front_engine_logger.warning(f"[DropFileFilter] handler error: {error!r}")
                return True
        return False


def enable_file_drop(widget: QWidget, extensions, on_file: Callable[[str], None]) -> _DropFileFilter:
    """
    讓 widget 接受拖放檔案；副檔名符合時以路徑呼叫 on_file。回傳的過濾器需由
    呼叫端保留參考以免被回收。
    Let `widget` accept dropped files, calling ``on_file(path)`` for an allowed
    suffix. The returned filter must be kept alive by the caller.
    """
    widget.setAcceptDrops(True)
    drop_filter = _DropFileFilter(extensions, on_file, widget)
    widget.installEventFilter(drop_filter)
    return drop_filter


def list_media_files(folder: str, extensions, recursive: bool = False) -> list:
    """
    回傳資料夾內符合副檔名的檔案（依路徑排序）。recursive=True 會遞迴子資料夾。
    資料夾不存在時回傳空清單。
    Return files in `folder` whose suffix is in `extensions`, sorted by path.
    `recursive=True` walks subfolders. Returns [] when the folder is missing.
    """
    try:
        folder_path = Path(folder)
        if not folder_path.is_dir():
            return []
        allowed = {ext.lower() for ext in extensions}
        iterator = folder_path.rglob("*") if recursive else folder_path.iterdir()
        return sorted(
            str(path)
            for path in iterator
            if path.is_file() and path.suffix.lower() in allowed
        )
    except OSError:
        return []


def reload_recent_combobox(combobox: QComboBox, category: str) -> None:
    """
    以某分類最近使用的檔案重建下拉選單：第一項為佔位提示 (data=None)，
    其後每項顯示檔名、data 存完整路徑。
    Rebuild a recent-files combobox: a placeholder first item (data=None)
    followed by one entry per recent path (label=filename, data=full path).
    """
    combobox.blockSignals(True)
    combobox.clear()
    combobox.addItem(language_wrapper.language_word_dict.get("recent_files_label", "Recent"), None)
    for path in get_recent_files(category):
        combobox.addItem(Path(path).name, path)
    combobox.setCurrentIndex(0)
    combobox.blockSignals(False)


def build_recent_combobox(category: str) -> QComboBox:
    """Build a combobox populated with the recent files for `category`."""
    combobox = QComboBox()
    reload_recent_combobox(combobox, category)
    return combobox


def coerce_int(value: object) -> Optional[int]:
    """
    盡力將載入的設定值轉為 int，失敗時回傳 None。
    Best-effort ``int()`` for values loaded from preset JSON. Returns None
    when the value is missing or cannot be parsed, so callers skip the
    field instead of crashing on malformed / hand-edited input.
    """
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None