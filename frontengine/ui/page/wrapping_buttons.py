"""Native checkboxes and buttons whose captions follow the available width."""
from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QPaintEvent, QTextLayout, QTextOption
from PySide6.QtWidgets import QCheckBox, QPushButton, QSizePolicy, QStyle, QStyleOptionButton, QStylePainter, QWidget


class _WrappingCaption:
    def __init__(self, text: str = '', parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        policy = self.sizePolicy()
        policy.setHorizontalPolicy(QSizePolicy.Policy.Preferred)
        policy.setVerticalPolicy(QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

    def _wrapped_text(self, width: int) -> str:
        option = QStyleOptionButton()
        self.initStyleOption(option)
        contents = self.style().subElementRect(self._contents_element, option, self)
        available = max(1, width - (self.width() - contents.width()))
        layout = QTextLayout(self.text(), self.font())
        wrapping = QTextOption()
        wrapping.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        layout.setTextOption(wrapping)
        text = self.text().encode('utf-16-le')
        lines = []
        layout.beginLayout()
        while (line := layout.createLine()).isValid():
            line.setLineWidth(available)
            start, end = line.textStart(), line.textStart() + line.textLength()
            lines.append(text[start * 2:end * 2].decode('utf-16-le').rstrip())
        layout.endLayout()
        return '\n'.join(lines)

    def heightForWidth(self, width: int) -> int:  # NOSONAR - Qt override name
        metrics = self.fontMetrics()
        text_height = metrics.size(Qt.TextFlag.TextShowMnemonic, self._wrapped_text(width)).height()
        return max(super().sizeHint().height(), text_height + 8)

    def minimumSizeHint(self) -> QSize:  # NOSONAR - Qt override name
        option = QStyleOptionButton()
        self.initStyleOption(option)
        contents = self.style().subElementRect(self._contents_element, option, self)
        inset = self.width() - contents.width()
        return QSize(inset + self.fontMetrics().averageCharWidth() + 8, super().sizeHint().height())

    def hitButton(self, position: QPoint) -> bool:  # NOSONAR - Qt override name
        return self.rect().contains(position)

    def paintEvent(self, event: QPaintEvent) -> None:  # NOSONAR - Qt override name
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.text = self._wrapped_text(self.width())
        painter = QStylePainter(self)
        painter.drawControl(self._control_element, option)


class WrappingCheckBox(_WrappingCaption, QCheckBox):
    _contents_element = QStyle.SubElement.SE_CheckBoxContents
    _control_element = QStyle.ControlElement.CE_CheckBox


class WrappingPushButton(_WrappingCaption, QPushButton):
    _contents_element = QStyle.SubElement.SE_PushButtonContents
    _control_element = QStyle.ControlElement.CE_PushButton
