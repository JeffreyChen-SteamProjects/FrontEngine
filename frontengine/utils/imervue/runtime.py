"""Lazy public runtime imports; no dependency on a developer checkout path."""
from types import SimpleNamespace


def puppet_runtime() -> SimpleNamespace:
    try:
        from rigora.puppet.canvas import PuppetCanvas
        from rigora.puppet.document_io import load_puppet
        from rigora.puppet.idle_driver import IdleDriver
        from rigora.puppet.input_engine import InputEngine
        from rigora.puppet.motion_player import MotionPlayer
        from rigora.desktop_pet.pet_script import PetScriptEngine, load_script
    except ImportError as error:
        raise ValueError('Install Rigora GUI from an authorized local checkout or wheel to use .puppet pets; '
                         f'a runtime dependency is unavailable: {error.name}') from error
    return SimpleNamespace(Canvas=PuppetCanvas, load=load_puppet, Idle=IdleDriver,
                           Input=InputEngine, Player=MotionPlayer,
                           Script=PetScriptEngine, load_script=load_script)
