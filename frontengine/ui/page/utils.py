from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QEvent, QObject, QRect
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
        # 全螢幕顯示 / Show in fullscreen
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
    span_all_screens: bool = False,
    screens: Optional[list] = None,
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
    monitors = QGuiApplication.screens() if screens is None else screens

    # 橫跨模式：一個覆蓋層蓋滿整個桌面，而不是每個螢幕各一個。要放在最前面判斷，
    # 因為它和「問使用者要哪一個螢幕」是互斥的——已經選了全部就沒什麼好問的。
    # Spanning: one overlay over the whole desktop rather than one per screen.
    # It is decided first because it rules out asking which screen to use: the
    # user has already said all of them.
    if span_all_screens and len(monitors) > 1:
        widget = factory(None)
        geometry = virtual_desktop_geometry(monitors)
        widget.setGeometry(geometry)
        widget.show()
        widget.raise_()
        return

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


# 「橫跨所有螢幕」在下拉選單裡用這個值標記，和「第 N 個螢幕」的整數區分開。
# The "span every screen" entry carries this instead of a monitor index.
SPAN_ALL_DATA = "span"


def virtual_desktop_geometry(screens=None) -> QRect:
    """
    所有螢幕聯集起來的矩形，也就是整個桌面的範圍。

    橫跨模式要的是一個蓋滿這塊範圍的覆蓋層，而不是每個螢幕各一個。螢幕不一定排成
    一直線也不一定同樣高，所以要用聯集而不是把寬度加起來。
    The union of every screen: the whole desktop. Spanning wants one overlay
    covering that, not one per screen. Screens are not necessarily in a row or
    the same height, so this unites rather than summing widths.
    """
    geometry = QRect()
    for screen in (QGuiApplication.screens() if screens is None else screens):
        geometry = geometry.united(screen.geometry())
    return geometry


def build_target_monitor_combobox(screens=None) -> QComboBox:
    """
    Build a combobox listing the current monitors plus an initial "Ask"
    entry. Selection "Ask" (data=None) preserves today's prompt flow;
    selecting a monitor index pre-selects that screen.

    多螢幕時多一個「橫跨所有螢幕」。只有一個螢幕時不提供——那和一般顯示完全一樣，
    列出來只會讓人以為自己漏掉了什麼。
    On a multi-monitor system there is also a "span every screen" entry. It is
    not offered on a single screen, where it would do exactly what the normal
    path does and only leave the user wondering what they missed.
    """
    monitors = QGuiApplication.screens() if screens is None else screens
    combobox = QComboBox()
    combobox.addItem(language_wrapper.language_word_dict.get("target_monitor_ask", "Ask"), None)
    for index, _ in enumerate(monitors):
        combobox.addItem(str(index), index)
    if len(monitors) > 1:
        combobox.addItem(
            language_wrapper.language_word_dict.get("target_monitor_span", "Span all screens"),
            SPAN_ALL_DATA)
    return combobox


def resolve_span(combobox: Optional[QComboBox]) -> bool:
    """使用者是不是選了「橫跨所有螢幕」。"""
    return combobox is not None and combobox.currentData() == SPAN_ALL_DATA


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

# --- 還原預設集的共用小工具 / shared preset-restoring helpers ---------------
# 每個分頁的 set_state 幾乎都是同一段話重複很多次：「設定裡有這個鍵，就把值
# 放進這個控制項」。把它抽出來之後，各頁只剩下「哪個控制項配哪個鍵」的表格，
# 讀起來是一份對照表而不是一長串 if。
#
# Every page's set_state repeated the same sentence over and over: "if the state
# carries this key, put it in this widget". Pulled out here, each page is left
# with a table of widget-to-key pairs, which reads as a mapping rather than a
# wall of ifs.
def apply_checkbox_state(state: dict, pairs) -> None:
    """把設定裡的布林值套進對應的勾選框（沒有那個鍵就不動）。"""
    for checkbox, key in pairs:
        if key in state:
            checkbox.setChecked(bool(state[key]))


def apply_combobox_text_state(state: dict, pairs) -> None:
    """依顯示文字選取下拉選單的項目；找不到就保持原狀。"""
    for combobox, key in pairs:
        value = state.get(key)
        if value is None:
            continue
        index = combobox.findText(str(value))
        if index >= 0:
            combobox.setCurrentIndex(index)


def apply_combobox_data_state(combobox: QComboBox, value: object) -> bool:
    """依附帶資料選取下拉選單的項目；回傳是否真的選到。"""
    if value is None:
        return False
    index = combobox.findData(str(value))
    if index < 0:
        return False
    combobox.setCurrentIndex(index)
    return True


def apply_slider_state(state: dict, pairs) -> None:
    """把設定裡的整數套進滑桿，並夾在滑桿自己的範圍內。"""
    for slider, key in pairs:
        value = coerce_int(state.get(key))
        if value is not None:
            slider.setValue(max(slider.minimum(), min(slider.maximum(), value)))


def apply_spinbox_state(state: dict, pairs) -> None:
    """把設定裡的整數套進數字框，並夾在數字框自己的範圍內。"""
    apply_slider_state(state, pairs)
