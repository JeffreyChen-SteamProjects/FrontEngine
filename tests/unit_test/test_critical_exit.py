"""The emergency-exit listener can be stopped, so nothing polls native key state at exit."""
from frontengine.utils.critical_exit import critical_exit
from frontengine.utils.critical_exit.critical_exit import CriticalExit


def test_stop_ends_the_listener(monkeypatch):
    polls = []
    monkeypatch.setattr(critical_exit, 'check_key_is_press', lambda key: polls.append(key) or False)
    listener = CriticalExit()
    listener.start()
    listener.stop(timeout=2.0)
    assert not listener.is_alive()


def test_stop_before_start_is_safe():
    listener = CriticalExit()
    listener.stop()
    assert not listener.is_alive()
