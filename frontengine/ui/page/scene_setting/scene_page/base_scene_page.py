from typing import Any, Callable, Dict, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QMessageBox, QSlider, QWidget

from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.user_setting.scene_setting import scene_json
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator, translate


# 建構、登記與「重選檔案」時各用一次，提成常數免得三份各自漂移。
# Used at construction, at registration and when a file is re-chosen.
_NOT_READY = "Not Ready"


class BaseSceneSettingUI(QWidget):
    """
    Template Method base for the scene-setting pages. Subclasses lay out
    their own grid but share the slider wiring, the choose-file ready
    flow, and the "append to scene_json" idiom so neither the slider
    factory nor the scene-append logic has to be re-implemented per page.
    """

    def __init__(self, script_ui: SceneManagerUI) -> None:
        front_engine_logger.info(f"[{type(self).__name__}] Init | script_ui={script_ui}")
        super().__init__()
        self.script_ui = script_ui
        self.grid_layout = QGridLayout(self)

    def _build_slider(
        self,
        label_key: str,
        minimum: int,
        maximum: int,
        default: int,
    ) -> Tuple[QLabel, QLabel, QSlider]:
        label = QLabel(translate(label_key))
        retranslator.bind(label, label_key)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(default)
        value_label = QLabel(str(slider.value()))
        slider.valueChanged.connect(lambda v, lbl=value_label: lbl.setText(str(v)))
        return label, value_label, slider

    def _make_ready_label(self) -> QLabel:
        label = QLabel(translate(_NOT_READY))
        retranslator.bind(label, _NOT_READY)
        return label

    def _wire_chooser(
        self,
        chooser: Callable[[QWidget], Optional[str]],
        ready_label: QLabel,
        on_chosen: Callable[[str], None],
        on_reset: Callable[[], None] = lambda: None,
    ) -> Callable[[], None]:
        """
        Wire a choose-file button: reset state, ask the chooser for a
        path, and if one is picked call `on_chosen` and flip the ready
        label to "Ready".
        """
        def handler() -> None:
            # set_text 而不是 setText：換語言時要跟著目前是就緒還是未就緒
            # set_text, not setText, so a language change follows whichever
            # state the label is actually in.
            retranslator.set_text(ready_label, _NOT_READY)
            on_reset()
            path = chooser(self)
            if path:
                retranslator.set_text(ready_label, "Ready")
                on_chosen(path)
        return handler

    def _warn_not_prepared(self) -> None:
        message_box = QMessageBox(self)
        message_box.setText(language_wrapper.language_word_dict.get("not_prepare"))
        message_box.exec()

    def _append_scene(self, payload: Dict[str, Any]) -> None:
        scene_json[str(len(scene_json))] = payload
        self.script_ui.renew_json_plain_text()
