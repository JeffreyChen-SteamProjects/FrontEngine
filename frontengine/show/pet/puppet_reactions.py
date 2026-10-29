"""Explicit script bindings between companion actions and native puppet assets."""
import json
from pathlib import Path

from frontengine.utils.pet_pack.layered import ACTIONS


def load_reactions(script_path, document):
    if not script_path:
        return {}
    try:
        with Path(script_path).open('rb') as stream:
            raw = stream.read(1024 * 1024 + 1)
    except OSError as error:
        raise ValueError(f'Cannot read puppet reaction script: {error}') from error
    if len(raw) > 1024 * 1024:
        raise ValueError('Puppet reaction script exceeds 1 MiB')
    try:
        data = json.loads(raw.decode('utf-8-sig'))
    except RecursionError as error:
        raise ValueError('Puppet reaction script is nested too deeply') from error
    if not isinstance(data, dict):
        raise ValueError('Puppet script must be an object')
    bindings = data.get('frontengine_actions', {})
    if not isinstance(bindings, dict) or set(bindings) - set(ACTIONS):
        raise ValueError('Unknown puppet companion action')
    motions = {motion.name for motion in document.motions}
    expressions = {expression.name for expression in document.expressions}
    for action, binding in bindings.items():
        if (not isinstance(binding, dict) or not binding
                or set(binding) - {'motion', 'expression'}):
            raise ValueError(f'Invalid puppet reaction: {action}')
        for field, names in (('motion', motions), ('expression', expressions)):
            if field in binding and (not isinstance(binding[field], str) or binding[field] not in names):
                raise ValueError(f'Unknown puppet {field} for {action}')
    return bindings


class PuppetReactions:
    def __init__(self, canvas, player, play, bindings):
        self.canvas, self.player, self.play, self.bindings = canvas, player, play, bindings
        self.action = None
        self.motion = None
        self.expression = None

    def release(self):
        if self.motion is not None and self.player.motion() is self.motion:
            self.player.stop()
        if self.expression is not None:
            self.canvas.remove_expression(self.expression)
        self.motion = self.expression = None

    def update(self, action):
        if action == self.action:
            return
        self.release()
        self.action = action
        binding = self.bindings.get(action, {})
        motion = binding.get('motion')
        if motion and self.play(motion):
            self.motion = self.player.motion()
        expression = binding.get('expression')
        if expression and expression not in self.canvas.active_expressions():
            if self.canvas.add_expression(expression):
                self.expression = expression

    def reset(self):
        self.release()
        self.action = None
