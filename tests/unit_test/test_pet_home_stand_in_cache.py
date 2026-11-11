"""A built-in stand-in character is built once per process and shared by every pet that needs it."""
import threading

from frontengine.show.pet_game import resident_art
from frontengine.show.pet_game.resident_art import FALLBACK_PREFIX, _PrepareFallback


class _Owner:
    """Stands in for ResidentArt, which the job holds weakly."""


def _prepare(key, owner):
    job = _PrepareFallback(owner, "b" * 32, key)
    job.run()


def test_the_same_stand_in_is_built_once_and_shared(monkeypatch):
    from frontengine.show.pet.inkside import assemble
    builds, delivered = [], []
    original = assemble.build_character

    def counted(template, folder):
        builds.append(template.ident)
        return original(template, folder)

    monkeypatch.setattr(assemble, "build_character", counted)
    monkeypatch.setattr(resident_art, "_deliver", lambda _ref, _identifier, key, result: delivered.append(result[0]))
    monkeypatch.setattr(resident_art, "_STAND_INS", {})
    owner = _Owner()
    key = FALLBACK_PREFIX + "inkside-pip"
    threads = [threading.Thread(target=_prepare, args=(key, owner)) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(120)
    _prepare(key, owner)
    assert builds == ["inkside-pip"]
    assert len(delivered) == 4
    assert delivered[0] is not None
    assert all(renderer is delivered[0] for renderer in delivered)
