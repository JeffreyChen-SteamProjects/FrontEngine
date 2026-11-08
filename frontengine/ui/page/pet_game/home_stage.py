"""The pet home as a game screen: tabs for the panels and a picture of the home-to-be.

The home overview sits on top of the page like a stage; everything you do to the
home - residents, work, furniture, shop, backpack, goals, inbox and its settings -
lives in tabs underneath, so the overview stays on screen while you use them.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QComboBox, QSizePolicy, QSlider, QTabWidget, QVBoxLayout, QWidget

from frontengine.show.pet_game.furniture_art import picture
from frontengine.utils.multi_language.retranslate import retranslator, translate

# Tab order: what the player does most often first, settings last.
TAB_ORDER = ("pet_home_residents_section", "pet_home_work_section", "pet_home_layout_section",
             "pet_home_shop_section", "pet_home_storage_section", "pet_home_goals_section",
             "pet_home_inbox_section", "pet_home_collection_section", "pet_home_settings_section")


class HomeTabs(QTabWidget):
    """One tab per home panel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("homeTabs")
        self.setDocumentMode(True)
        self._keys: list[tuple[str, str]] = []
        retranslator.bind_call(self.retranslate)

    def add_section(self, key: str, fallback: str, section: QWidget) -> None:
        for combo in section.findChildren(QComboBox):
            combo.setMinimumWidth(100)
            combo.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        for slider in section.findChildren(QSlider):
            slider.setMinimumWidth(80)
        holder = QWidget()
        holder.setObjectName("homeTabPage")
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(0, 14, 0, 14)
        layout.addWidget(section)
        layout.addStretch(1)
        self.addTab(holder, translate(key, fallback))     # the page itself scrolls, not each tab
        self._keys.append((key, fallback))

    def keys(self) -> list[str]:
        return [key for key, _fallback in self._keys]

    def select(self, key: str) -> bool:
        if key not in self.keys():
            return False
        self.setCurrentIndex(self.keys().index(key))
        return True

    def retranslate(self) -> None:
        for index, (key, fallback) in enumerate(self._keys):
            self.setTabText(index, translate(key, fallback))


class EmptyHome(QWidget):
    """What a new home starts with - bed, table and desk on the floor - shown before there is one."""

    PIECES = (("bed_basic", 4), ("table_basic", 4), ("desk_basic", 3))

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("emptyHome")
        self.setFixedHeight(150)

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        cell = 30.0
        gap = cell
        total = sum(width for _name, width in self.PIECES) * cell + gap * (len(self.PIECES) - 1)
        floor = self.height() - 18.0
        mid = self.palette().color(self.palette().ColorRole.Mid)
        painter.fillRect(QRectF(0, floor, self.width(), 3), QColor(mid))
        x = (self.width() - total) / 2
        for name, width in self.PIECES:
            image = picture("warm_home", name)
            if image is not None:
                span = width * cell
                height = span * image.height() / image.width()
                painter.drawImage(QRectF(x, floor - height + 2, span, height), image)
            x += width * cell + gap
        painter.end()


def make_tab_ready(section) -> None:
    """A section shown as a tab already has its title on the tab itself."""
    section.title_label.hide()
    section.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
