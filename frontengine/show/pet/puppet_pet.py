"""FrontEngine-owned pet window sharing Imervue's canvas, drivers and script."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QMessageBox, QVBoxLayout

from frontengine.show.draggable_window import DraggableTopWindow
from frontengine.utils.imervue.puppet_asset import finite_parameters, validate_puppet
from frontengine.utils.imervue.runtime import puppet_runtime
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.show.pet.pet_profile_session import PetProfileSession
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.pet_profile_schema import presentation_defaults
from frontengine.utils.multi_language.retranslate import translate
from frontengine.show.pet.companion_menu import add_companion_actions, add_food_actions, companion_status
from frontengine.show.pet.puppet_reactions import PuppetReactions, load_reactions
from frontengine.utils.pet_companion.petting import PettingGesture
from frontengine.show.pet.puppet_target import PuppetTargetController


class PuppetPetWidget(DraggableTopWindow):
    clone_requested = Signal()
    customize_requested = Signal()
    overlay_lockable = False
    supports_layered_wardrobe = False
    customization_fields = frozenset({'size', 'speech_bubbles', 'settle_typing', 'auto_rest', 'chatter'})

    def __init__(self, path: str | Path, size: tuple[int, int] = (320, 480), *,
                 parameters: dict | None = None, motion: str | None = None,
                 expression: str | None = None, script_path: str | None = None,
                 opacity: float = 1.0, parent=None, profile_id: str | None = None,
                 profiles: PetProfiles | None = None, profile_name: str = "") -> None:
        validate_puppet(path)
        values = finite_parameters(parameters or {})
        if (len(size) != 2 or any(type(v) is not int or not 16 <= v <= 4096 for v in size)):
            raise ValueError('Puppet display size must be two integers between 16 and 4096')
        runtime = puppet_runtime()
        document = runtime.load(path)
        reactions = load_reactions(script_path, document)
        script = runtime.Script(runtime.load_script(script_path) if script_path else None)
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.path = str(Path(path).resolve())
        self.script_path = str(Path(script_path).resolve()) if script_path else None
        self.opacity = 1.0
        self._closed = False
        self._photo_dialog = None
        self._settled = False
        self._petting = None
        self._dragged = False
        self._press_point = None
        self._welcomed = False
        self._leaving = False
        self._petting_revision = None
        self._target = PuppetTargetController(self)
        self.placement_revision = 0
        self._talk = True
        self._initial_size = size
        self._presentation_defaults = {**presentation_defaults(), 'size': min(512, size[0])}
        self._messages = {}
        self.canvas = runtime.Canvas(self, pet_mode=True)
        self.canvas.installEventFilter(self)
        self.canvas.load_document(document)
        self.canvas.set_parameter_values(values)
        self.player = runtime.Player(self.canvas, parent=self)
        self.reactions = PuppetReactions(self.canvas, self.player, self._play_native_motion, reactions)
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
        try:
            self.profile_session = PetProfileSession(self, profile_id, profiles, profile_name)
            self.profile_session.changed.connect(self._companion_changed)
            self._companion_changed()
        except (OSError, ValueError):
            self.shutdown()
            self.close()
            raise

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
        self.stop_toy()
        self._end_petting()
        self.reactions.release()
        return self._play_native_motion(name)

    def _play_native_motion(self, name: str) -> bool:
        motion = next((m for m in self.canvas.document().motions if m.name == name), None)
        if motion is None:
            return False
        self.player.set_motion(motion)
        self.player.play()
        return True

    def _hit_area(self, area: str) -> None:
        self.stop_toy()
        active_expressions = self.canvas.active_expressions()
        self.reactions.release()
        document = self.canvas.document()
        hit = next((item for item in document.hit_areas if item.id == area), None) if document else None
        motion = hit.motion if hit else None
        if motion:
            self.play_motion(motion)
        if hit and hit.expression:
            if hit.expression in active_expressions:
                self.canvas.remove_expression(hit.expression)
            else:
                self.canvas.add_expression(hit.expression)
        line = (self.script.pick_for_hit_area(area) or self.script.pick_for_motion(motion)
                or self.script.pick_time_of_day_greeting() or self.script.pick_greeting())
        if line:
            self.say(line)

    def eventFilter(self, watched, event) -> bool:
        if watched is self.canvas:
            if self._petting is not None:
                if event.type() == QEvent.Type.Leave:
                    self._end_petting()
                elif event.type() == QEvent.Type.MouseMove:
                    point = event.position()
                    if not self.canvas.rect().contains(point.toPoint()):
                        self._end_petting()
                    elif self._petting.move(point.x(), point.y()):
                        self._interaction_feedback(self.profile_session.request('pet'))
                    return True
                elif event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease,
                                      QEvent.Type.MouseButtonDblClick):
                    if event.button() == Qt.MouseButton.LeftButton:
                        return True
                elif event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
                    self._end_petting()
                    return True
            if self._pointer_event(event):
                return True
        return super().eventFilter(watched, event)

    def _pointer_event(self, event) -> bool:
        """A click greets on release; only movement past the drag distance drags, without rewards."""
        left = getattr(event, 'button', lambda: None)() == Qt.MouseButton.LeftButton
        if event.type() == QEvent.Type.MouseButtonPress and left:
            self.stop_toy()
            self._press_point = event.globalPosition().toPoint()
            self._dragged = False
            self._drag_origin = self._press_point - self.frameGeometry().topLeft()
        elif (event.type() == QEvent.Type.MouseMove and self._drag_origin is not None
              and event.buttons() & Qt.MouseButton.LeftButton):
            point = event.globalPosition().toPoint()
            if not self._dragged and (point - self._press_point).manhattanLength() < QApplication.startDragDistance():
                return True
            if not self._dragged:
                self._dragged = True
                self.profile_session.request('drag')
            self.placement_revision += 1
            self.move(point - self._drag_origin)
            return True
        elif event.type() == QEvent.Type.MouseButtonRelease and left and self._drag_origin is not None:
            self._drag_origin = None
            if self._dragged:
                self._dragged = False
                self.profile_session.request('cancel')
            else:
                self._interaction_feedback(self.profile_session.request('greet'))
        return False

    def _script_tick(self) -> None:
        if self._petting is not None or self._target.marker is not None or not self.profile_session.companion.allows_autonomy:
            return
        values = self.profile_session.companion.preferences.get('presentation') or {}
        if values.get('chatter') == 'off':
            return  # scheduled script lines are proactive chatter
        line = self.script.due_scheduled_message()
        if line:
            self.say(line)

    def say(self, text: str) -> None:
        if not self._talk:
            return
        self.bubble.setText(str(text))
        self.bubble.adjustSize()
        self.bubble.move(4, 4)
        self.bubble.raise_()
        self.bubble.show()
        QTimer.singleShot(4000, self.bubble, self.bubble.hide)

    def set_settled(self, settled: bool) -> None:
        self._settled = bool(settled)
        if settled:
            self.stop_toy()
            self._end_petting()
        self.idle.set_enabled(self.isVisible() and not settled
                              and self._petting is None
                              and self._target.marker is None
                              and self.profile_session.companion.allows_autonomy)
        if settled:
            self.reactions.reset()
            self.player.stop()
        elif self.isVisible():
            self.reactions.update('walk' if self._target.marker is not None else self.profile_session.companion.visual_action)

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
            action.toggled.connect(lambda on, name=expression.name: self._choose_expression(name, on))
        menu.addAction(words.get('pet_puppet_clone', 'Clone'), self.clone_requested.emit)
        menu.addAction(words.get('pet_status', 'Status'), self.show_profile_status)
        menu.addAction(words.get('pet_feed', 'Feed'), lambda: self.feed())
        add_food_actions(menu, self.feed)
        menu.addAction(translate('pet_custom_title', 'Customize pet'), self.customize_requested.emit)
        menu.addAction(translate('pet_photo_title', 'Pet photo'), self.open_photo)
        menu.addAction(translate('pet_come', 'Come here'), lambda: self.start_call())
        menu.addAction(translate('pet_light_start', 'Play with a light spot'), lambda: self.start_light())
        menu.addAction(translate('pet_ball_start', 'Throw a ball'), lambda: self.start_ball())
        menu.addAction(translate('pet_toy_stop', 'Put toy away'), self.stop_toy)
        add_companion_actions(menu, self.profile_session, self._interaction_feedback,
                              request=self._request_interaction)
        menu.addAction(words.get('pet_puppet_close', 'Close'), self.say_goodbye)
        menu.exec(event.globalPos())
        menu.deleteLater()

    def _choose_expression(self, name, enabled):
        self.stop_toy()
        self._end_petting()
        self.reactions.release()
        if enabled:
            self.canvas.add_expression(name)
        else:
            self.canvas.remove_expression(name)

    def photo_image(self):
        """Use the runtime's character-only FBO, never a desktop screenshot."""
        render = getattr(self.canvas, 'render_offscreen_puppet', None)
        if self._closed or not callable(render) or not self.canvas.isValid():
            raise ValueError('Puppet photo requires an initialized compatible GL canvas')
        image = render(self.width(), self.height(), background_rgba=(0.0, 0.0, 0.0, 0.0))
        if image is None or image.isNull():
            raise ValueError('Puppet renderer did not produce a photo')
        return image.copy()

    def open_photo(self) -> None:
        from frontengine.ui.dialog.pet_photo import PetPhotoDialog

        if self._photo_dialog is None:
            try:
                snapshot = self.photo_image()
            except Exception:
                # Native context/driver failures must not escape a GUI signal handler.
                QMessageBox.warning(self, translate('pet_photo_title', 'Pet photo'), translate(
                    'pet_photo_unavailable', 'The pet image is not ready. Show the pet and try again.'))
                return
            self._photo_dialog = PetPhotoDialog(snapshot, parent=self)
            self._photo_dialog.destroyed.connect(self._photo_closed)
        self._photo_dialog.show()

    def _photo_closed(self) -> None:
        self._photo_dialog = None

    def show_profile_status(self) -> None:
        """Show the same saved identity fields without altering puppet geometry."""
        record = self.profile_session.state()
        self.say(record['name'] + ' · ' + translate('pet_profile_stats').format(**record))

    def feed(self, kind: str = 'snack') -> None:
        """Use common care rules without inventing a model's native animation."""
        self.stop_toy()
        self._end_petting()
        self._interaction_feedback(self.profile_session.request('feed', kind))

    def _request_interaction(self, action: str) -> str:
        self.stop_toy()
        if action != 'pet':
            self._end_petting()
            return self.profile_session.request(action)
        if (self._closed or not self.isVisible() or self._settled
                or self.profile_session.companion.action is not None or self._drag_origin is not None):
            return 'busy'
        if self._petting is None:
            self._petting_tracking = self.canvas.hasMouseTracking()
        self._petting = PettingGesture(max(4, self.canvas.width() * 0.08))
        self._petting_revision = self.profile_session.mode_revision
        self.canvas.setMouseTracking(True)
        self.idle.set_enabled(False)
        return 'accepted'

    def _end_petting(self) -> None:
        if self._petting is None:
            return
        self._petting = None
        self._drag_origin = None
        self.canvas.setMouseTracking(self._petting_tracking)
        if self.profile_session.companion.action == 'pet':
            self.profile_session.request('cancel')
        self.idle.set_enabled(not self._closed and self.isVisible() and not self._settled
                              and self.profile_session.companion.allows_autonomy)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape and self._target.marker is not None:
            self.stop_toy()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape and self._petting is not None:
            self._end_petting()
            event.accept()
            return
        super().keyPressEvent(event)

    def _interaction_feedback(self, result: str) -> None:
        if result == 'accepted' and self._petting is not None:
            self.say(translate('pet_petting_hint', 'Move back and forth over the pet. Leave to stop.'))
            return
        if result == 'accepted' and self.profile_session.companion.action == 'greet':
            self.say(translate('pet_greet_' + self.profile_session.companion.bond))
            return
        self.say(companion_status(self.profile_session) if result == "accepted" else translate(
            "pet_companion_" + result, result))

    def manager_commands(self) -> list[tuple[str, str]]:
        """Menu commands, including model motions and expressions, for the pet manager."""
        words = language_wrapper.language_word_dict
        commands = [('photo', translate('pet_photo_title', 'Pet photo')), ('status', words.get('pet_status', 'Status'))]
        document = self.canvas.document()
        if document is not None:
            motion = words.get('pet_puppet_motions', 'Motions')
            expression = words.get('pet_puppet_expressions', 'Expressions')
            commands += [('motion:' + item.name, f'{motion}: {item.name}') for item in document.motions]
            commands += [('expression:' + item.name, f'{expression}: {item.name}') for item in document.expressions]
        return commands + [('clone', words.get('pet_puppet_clone', 'Clone')),
                           ('close', translate('pet_close_pet', 'Close this pet'))]

    def run_manager_command(self, command: str) -> None:
        kind, _, name = command.partition(':')
        if kind == 'motion':
            self.stop_toy()
            self._end_petting()
            self.reactions.release()
            self.play_motion(name)
        elif kind == 'expression':
            self._choose_expression(name, name not in self.canvas.active_expressions())
        else:
            {'photo': self.open_photo, 'status': self.show_profile_status,
             'clone': self.clone_requested.emit, 'close': self.say_goodbye}[kind]()

    def say_goodbye(self) -> None:
        """Closing from the pet's own menu says goodbye briefly before the window closes."""
        if self._leaving:
            return
        self._leaving = True
        self.stop_toy()
        self.say(translate('pet_goodbye', 'See you soon!'))
        QTimer.singleShot(900, self, self._finish_goodbye)

    def _finish_goodbye(self) -> None:
        if not self.close():
            self._leaving = False

    def _companion_changed(self) -> None:
        if self._petting is not None and (
                self._petting_revision != self.profile_session.mode_revision
                or self.profile_session.companion.action not in (None, 'pet')):
            self._end_petting()
        values = self.profile_session.companion.preferences.get('presentation')
        if values is None:
            self.resize(*self._initial_size)
            self._talk = True
        else:
            width = values['size']
            self.resize(width, max(16, round(width * self._initial_size[1] / self._initial_size[0])))
            self._talk = values['speech_bubbles']
        if not self._talk:
            self.bubble.hide()
        self.set_settled(self._settled)
        self._target.validate()

    @property
    def can_play_with_toy(self) -> bool:
        return (not self._closed and self.isVisible() and not self._settled
                and not self.profile_session._closed and self._drag_origin is None
                and self._petting is None and self.profile_session.companion.allows_autonomy)

    def start_call(self, *, offset: tuple[int, int] | None = None) -> str:
        result = self._target.start(offset=offset)
        self._interaction_feedback(result)
        return result

    def stop_toy(self) -> None:
        self._target.stop()

    def start_light(self, *, offset: tuple[int, int] | None = None) -> str:
        result = self._target.start(activity='light', offset=offset)
        self._interaction_feedback(result)
        return result

    def start_ball(self) -> str:
        result = self._target.start(activity='ball')
        self._interaction_feedback(result)
        return result

    def place_for_focus(self, x: int, y: int) -> None:
        self.stop_toy()
        self._drag_origin = None
        self._dragged = False
        self.move(x, y)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.stop_toy()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.placement_revision += 1
        super().mouseMoveEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._closed:
            self.profile_session.resume()
            self.set_settled(self._settled)
            self.script_timer.start()
            if not self._welcomed:
                self._welcomed = True
                if self.profile_session.companion.growth.affection > 0:
                    self.say(translate('pet_welcome_back', 'Welcome back!'))

    def hideEvent(self, event) -> None:
        if not self._closed:
            self.stop_toy()
            self._end_petting()
            self.reactions.reset()
            self.profile_session.pause()
            self.profile_session.request("cancel")
            self.idle.set_enabled(False)
            self.player.stop()
            self.script_timer.stop()
        super().hideEvent(event)

    def shutdown(self) -> bool:
        if self._closed:
            return True
        session = getattr(self, 'profile_session', None)
        if session is not None and not session.close():
            return False
        self._closed = True
        self.stop_toy()
        self._end_petting()
        self.reactions.reset()
        self.script_timer.stop()
        self.idle.set_enabled(False)
        self.idle.shutdown()
        self.inputs.shutdown()
        self.player.set_motion(None)
        self.canvas.load_document(None)
        self.canvas.close()
        return True

    def closeEvent(self, event) -> None:
        if not self.shutdown():
            self.say(translate('pet_profile_save_failed'))
            event.ignore()
            return
        super().closeEvent(event)
