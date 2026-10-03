"""FrontEngine-owned pet window sharing Imervue's canvas, drivers and script."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtWidgets import QLabel, QMenu, QVBoxLayout

from frontengine.show.draggable_window import DraggableTopWindow
from frontengine.utils.imervue.puppet_asset import finite_parameters, validate_puppet
from frontengine.utils.imervue.runtime import puppet_runtime
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class PuppetPetWidget(DraggableTopWindow):
    clone_requested = Signal()
    overlay_lockable = False

    def __init__(self, path: str | Path, size: tuple[int, int] = (320, 480), *,
                 parameters: dict | None = None, motion: str | None = None,
                 expression: str | None = None, script_path: str | None = None,
                 opacity: float = 1.0, parent=None) -> None:
        validate_puppet(path)
        values = finite_parameters(parameters or {})
        if (len(size) != 2 or any(type(v) is not int or not 16 <= v <= 4096 for v in size)):
            raise ValueError('Puppet display size must be two integers between 16 and 4096')
        runtime = puppet_runtime()
        script = runtime.Script(runtime.load_script(script_path) if script_path else None)
        document = runtime.load(path)
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.path = str(Path(path).resolve())
        self.opacity = 1.0
        self._closed = False
        self._settled = False
        self._messages = {}
        self.canvas = runtime.Canvas(self, pet_mode=True)
        self.canvas.installEventFilter(self)
        self.canvas.load_document(document)
        self.canvas.set_parameter_values(values)
        self.player = runtime.Player(self.canvas, parent=self)
        self.idle = runtime.Idle(self.canvas, parent=self)
        self.inputs = runtime.Input(self.canvas, parent=self)
        self.inputs.set_blink_enabled(True)
        self.script = script
        self.canvas.hit_area_triggered.connect(self._hit_area)
        self.bubble = QLabel(self)
        self.bubble.setStyleSheet('color:white;background:rgba(30,30,30,190);padding:6px;border-radius:6px')
        self.bubble.hide()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self.resize(*size)
        self.script_timer = QTimer(self)
        self.script_timer.setInterval(1000)
        self.script_timer.timeout.connect(self._script_tick)
        self.set_ui_variable(opacity)
        self._configure_initial(motion, expression)

    def _configure_initial(self, motion, expression) -> None:
        try:
            if motion and not self.play_motion(motion):
                raise ValueError(f'Unknown puppet motion: {motion}')
            if expression and not self.canvas.add_expression(expression):
                raise ValueError(f'Unknown puppet expression: {expression}')
        except BaseException:
            self.shutdown()
            self.close()
            raise

    def set_ui_variable(self, opacity: float = 1.0) -> None:
        self.opacity = max(0.0, min(1.0, float(opacity)))
        self.setWindowOpacity(self.opacity)

    def center(self) -> tuple[int, int]:
        point = self.geometry().center()
        return point.x(), point.y()

    def play_motion(self, name: str) -> bool:
        motion = next((m for m in self.canvas.document().motions if m.name == name), None)
        if motion is None:
            return False
        self.player.set_motion(motion)
        self.player.play()
        return True

    def _hit_area(self, area: str) -> None:
        document = self.canvas.document()
        hit = next((item for item in document.hit_areas if item.id == area), None) if document else None
        motion = hit.motion if hit else None
        if motion:
            self.play_motion(motion)
        if hit and hit.expression:
            if hit.expression in self.canvas.active_expressions():
                self.canvas.remove_expression(hit.expression)
            else:
                self.canvas.add_expression(hit.expression)
        line = (self.script.pick_for_hit_area(area) or self.script.pick_for_motion(motion)
                or self.script.pick_time_of_day_greeting() or self.script.pick_greeting())
        if line:
            self.say(line)

    def eventFilter(self, watched, event) -> bool:
        if watched is self.canvas:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            elif (event.type() == QEvent.Type.MouseMove and self._drag_origin is not None
                  and event.buttons() & Qt.MouseButton.LeftButton):
                self.move(event.globalPosition().toPoint() - self._drag_origin)
                return True
            elif event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self._drag_origin = None
        return super().eventFilter(watched, event)

    def _script_tick(self) -> None:
        line = self.script.due_scheduled_message()
        if line:
            self.say(line)

    def say(self, text: str) -> None:
        self.bubble.setText(str(text))
        self.bubble.adjustSize()
        self.bubble.move(4, 4)
        self.bubble.raise_()
        self.bubble.show()
        QTimer.singleShot(4000, self.bubble, self.bubble.hide)

    def set_settled(self, settled: bool) -> None:
        self._settled = bool(settled)
        self.idle.set_enabled(self.isVisible() and not settled)
        if settled:
            self.player.stop()

    def contextMenuEvent(self, event) -> None:
        words = language_wrapper.language_word_dict
        menu = QMenu(self)
        motions = menu.addMenu(words.get('pet_puppet_motions', 'Motions'))
        for motion in self.canvas.document().motions:
            action = motions.addAction(motion.name)
            action.triggered.connect(lambda checked=False, name=motion.name: self.play_motion(name))
        expressions = menu.addMenu(words.get('pet_puppet_expressions', 'Expressions'))
        for expression in self.canvas.document().expressions:
            action = expressions.addAction(expression.name)
            action.setCheckable(True)
            action.setChecked(expression.name in self.canvas.active_expressions())
            action.toggled.connect(lambda on, name=expression.name: self.canvas.add_expression(name)
                                   if on else self.canvas.remove_expression(name))
        menu.addAction(words.get('pet_puppet_clone', 'Clone'), self.clone_requested.emit)
        menu.addAction(words.get('pet_puppet_close', 'Close'), self.close)
        menu.exec(event.globalPos())
        menu.deleteLater()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._closed:
            self.idle.set_enabled(not self._settled)
            self.script_timer.start()

    def hideEvent(self, event) -> None:
        if not self._closed:
            self.idle.set_enabled(False)
            self.player.stop()
            self.script_timer.stop()
        super().hideEvent(event)

    def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.script_timer.stop()
        self.idle.set_enabled(False)
        self.idle.shutdown()
        self.inputs.shutdown()
        self.player.set_motion(None)
        self.canvas.load_document(None)
        self.canvas.close()

    def closeEvent(self, event) -> None:
        self.shutdown()
        super().closeEvent(event)
