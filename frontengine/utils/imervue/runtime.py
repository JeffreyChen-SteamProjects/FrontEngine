"""Lazy public runtime imports; no dependency on a developer checkout path."""
from types import SimpleNamespace


def puppet_runtime():
    try:
        from Imervue.puppet.canvas import PuppetCanvas
        from Imervue.puppet.document_io import load_puppet
        from Imervue.puppet.idle_driver import IdleDriver
        from Imervue.puppet.input_engine import InputEngine
        from Imervue.puppet.motion_player import MotionPlayer
        from Imervue.desktop_pet.pet_script import PetScriptEngine, load_script
    except ImportError as error:
        raise ValueError('Install frontengine[puppet] to use Imervue .puppet pets; '
                         f'a runtime dependency is unavailable: {error.name}') from error
    return SimpleNamespace(Canvas=PuppetCanvas, load=load_puppet, Idle=IdleDriver,
                           Input=InputEngine, Player=MotionPlayer,
                           Script=PetScriptEngine, load_script=load_script)
