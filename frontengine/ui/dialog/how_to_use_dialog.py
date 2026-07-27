"""
使用說明：在程式裡直接講清楚 FrontEngine 是什麼、第一個覆蓋層怎麼開出來、
每個分頁共通的那幾個設定是什麼意思，以及東西開太多時怎麼一次收乾淨。

刻意寫成「快速上手」而不是完整手冊——完整的在文件站上，最後一顆按鈕就是去那裡。
使用者第一次打開程式時真正需要知道的，其實只有這幾件事。

How to use: say in the application itself what FrontEngine is, how to get a
first overlay on screen, what the settings every page shares actually mean, and
how to clear everything away when there is too much of it.

Deliberately a quick start rather than the whole manual - the manual is on the
documentation site and the last button goes there. What someone opening this
for the first time actually needs is only this much.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from frontengine.utils.browser.browser import open_browser
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.retranslate import retranslator, tr, translate

DOC_URL = "https://frontengine.readthedocs.io/en/latest/"

# (標題鍵, 標題預設, 內文鍵, 內文預設)
SECTIONS: List[Tuple[str, str, str, str]] = [
    ("how_to_use_start_title", "Your first overlay",
     "how_to_use_start_body",
     "Pick a tab for the kind of thing you want on screen - a video, an image, "
     "a web page, some text - choose the file or address, then press the start "
     "button on that page. It appears on top of everything else and stays there "
     "until you close it."),
    ("how_to_use_shared_title", "Settings every page shares",
     "how_to_use_shared_body",
     "Opacity decides how much of the desktop shows through. Target monitor "
     "chooses the screen, or asks each time. Show on all screens puts a copy on "
     "each monitor, and Show on all window bottom drops it beneath your windows "
     "so it behaves like a backdrop rather than something in front."),
    ("how_to_use_clicks_title", "Overlays do not get in the way",
     "how_to_use_clicks_body",
     "Clicks pass straight through an overlay to whatever is underneath, so the "
     "window below keeps working normally. The two exceptions are the pet and "
     "the drawing layer on the Presenting page, which need the mouse to do what "
     "they do."),
    ("how_to_use_control_title", "Managing several at once",
     "how_to_use_control_body",
     "The Control Center reaches every overlay, whichever page opened it: hide "
     "them for a moment, mute them, lock them so they stop moving, or lower the "
     "quality when the battery matters. Unlock them first if you want to drag "
     "one somewhere else - it remembers where you dropped it."),
    ("how_to_use_escape_title", "Clearing the screen",
     "how_to_use_escape_body",
     "Close all in the Control Center closes everything at once, and you can "
     "bind a global shortcut to it under Settings, Hotkeys. If something ever "
     "stops responding, pressing F12 shuts FrontEngine down immediately."),
    ("how_to_use_more_title", "Keeping what you set up",
     "how_to_use_more_body",
     "The Presets menu saves how every page is configured under a name and "
     "brings it back later, and one preset can be applied automatically at "
     "startup. The Settings menu holds the rest: shortcuts, reminders, a phone "
     "remote, screen-sharing privacy and more."),
]


class HowToUseDialog(QDialog):
    """
    使用說明。內容放在捲動區裡，視窗小的時候也讀得完。
    A quick start, in a scroll area so it stays readable on a small window.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        front_engine_logger.info("[HowToUseDialog] Init")
        super().__init__(parent)
        self.setWindowTitle(translate("how_to_use_title", "How to use FrontEngine"))
        retranslator.bind(self, "how_to_use_title", "How to use FrontEngine", "setWindowTitle")
        self.resize(560, 520)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.intro_label = tr(
            QLabel(), "how_to_use_intro",
            "FrontEngine puts things on top of your screen - videos, images, web pages, "
            "text, a desktop pet - and keeps them there while you work.")
        self.intro_label.setWordWrap(True)
        self.content_layout.addWidget(self.intro_label)

        self.section_labels: List[QLabel] = []
        for title_key, title_text, body_key, body_text in SECTIONS:
            heading = tr(QLabel(), title_key, title_text)
            heading.setStyleSheet("font-weight: bold; margin-top: 10px;")
            body = tr(QLabel(), body_key, body_text)
            body.setWordWrap(True)
            self.content_layout.addWidget(heading)
            self.content_layout.addWidget(body)
            self.section_labels += [heading, body]
        self.content_layout.addStretch(1)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.content)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.doc_button = QPushButton()
        tr(self.doc_button, "how_to_use_open_doc", "Full documentation")
        self.doc_button.clicked.connect(lambda: open_browser(DOC_URL))
        self.button_box.addButton(self.doc_button, QDialogButtonBox.ButtonRole.ActionRole)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.scroll_area)
        layout.addWidget(self.button_box)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
