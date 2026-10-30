"""Puppet pets stroll or act on their own and yield to everything that already moves them."""
import random

import pytest
from PySide6.QtCore import QRect

import test_puppet_petting as fixtures

puppet = fixtures.puppet


def prepare(pet, monkeypatch, x=-700, choice='walk'):
    class Screen:
        def availableGeometry(self):
            return QRect(-1000, -800, 1000, 800)
    monkeypatch.setattr(pet, 'screen', lambda: Screen())
    pet._stroll.rng = random.Random(4)
    if choice is not None:
        monkeypatch.setattr(pet._stroll, '_choose', lambda: choice)
    pet.move(x, -400)


def walk_to_end(pet, ticks=400):
    for _ in range(ticks):
        if not pet._stroll.walking:
            break
        pet._stroll.tick(0.05)


def test_a_shown_puppet_schedules_a_stroll(puppet):
    assert puppet._stroll._rest.isActive()
    assert 3000 <= puppet._stroll._rest.remainingTime() <= 8000


def test_puppet_walks_along_its_height_with_the_walk_reaction_then_rests(puppet, monkeypatch):
    prepare(puppet, monkeypatch)
    walked = []
    monkeypatch.setattr(puppet.reactions, 'update', lambda action: walked.append(action))
    start_y = puppet.y()
    puppet._stroll._begin()
    assert puppet._stroll.walking and walked[-1] == 'walk'
    target = puppet._stroll.target_x
    assert 120 <= abs(target - puppet.x()) <= 420
    puppet._stroll.tick(0.05)
    assert puppet.x() != -700 and puppet.y() == start_y
    walk_to_end(puppet)
    assert not puppet._stroll.walking and puppet.x() == target and puppet.y() == start_y
    assert walked[-1] != 'walk'
    assert puppet._stroll._rest.isActive()


@pytest.mark.parametrize('x', [-1000, -1000 + 1000 - 128])
def test_strolls_end_inside_the_work_area_at_either_edge(puppet, monkeypatch, x):
    prepare(puppet, monkeypatch, x=x)
    for _ in range(6):
        puppet._stroll._begin()
        walk_to_end(puppet)
        assert -1000 <= puppet.x() <= -128


@pytest.mark.parametrize('interrupt', ['call', 'settle', 'work', 'hide', 'drag'])
def test_stroll_yields_to_what_already_moves_the_pet(puppet, monkeypatch, interrupt):
    prepare(puppet, monkeypatch)
    puppet._stroll._begin()
    puppet._stroll.tick(0.05)
    if interrupt == 'call':
        assert puppet.start_call() == 'accepted'
        puppet._stroll.tick(0.05)
        assert not puppet._stroll.walking
        puppet.stop_toy()
    elif interrupt == 'settle':
        puppet.set_settled(True)
        assert not puppet._stroll.walking and not puppet._stroll._rest.isActive()
    elif interrupt == 'work':
        puppet.profile_session.set_mode('work')
        before = puppet.pos()
        puppet._stroll.tick(0.05)
        assert not puppet._stroll.walking and puppet.pos() == before
        puppet._stroll._begin()
        assert not puppet._stroll.walking
    elif interrupt == 'hide':
        puppet.hide()
        assert not puppet._stroll.walking and not puppet._stroll._rest.isActive()
    elif interrupt == 'drag':
        puppet._drag_origin = puppet.pos()
        before = puppet.pos()
        puppet._stroll.tick(0.05)
        assert not puppet._stroll.walking and puppet.pos() == before
        puppet._drag_origin = None


def test_closing_stops_the_stroll(puppet, monkeypatch):
    prepare(puppet, monkeypatch)
    puppet._stroll._begin()
    assert puppet.shutdown()
    assert not puppet._stroll.walking
    assert not puppet._stroll._rest.isActive() and not puppet._stroll._step.isActive()


def test_after_a_rest_the_puppet_picks_a_walk_or_any_of_its_actions(puppet, monkeypatch):
    prepare(puppet, monkeypatch, choice=None)
    picks = {puppet._stroll._choose() for _ in range(400)}
    assert picks == {name for name, _weight in puppet._stroll.CHOICES}
    assert {'sit', 'play', 'groom', 'greet', 'celebrate'} <= picks


@pytest.mark.parametrize('action', ['sit', 'play', 'groom', 'greet', 'celebrate'])
def test_an_action_plays_in_place_then_the_puppet_rests(puppet, monkeypatch, action):
    prepare(puppet, monkeypatch, choice=action)
    shown = []
    monkeypatch.setattr(puppet.reactions, 'update', lambda name: shown.append(name))
    before = puppet.pos()
    puppet._stroll._begin()
    assert puppet._stroll.acting == action and shown[-1] == action
    held = 0.0
    while puppet._stroll.acting is not None and held < 5:
        puppet._stroll.tick(0.05)
        held += 0.05
    assert puppet.pos() == before
    assert (2.9 <= held <= 3.1) if action == 'groom' else (1.9 <= held <= 4.1)
    assert shown[-1] != action and puppet._stroll._rest.isActive()


def test_an_action_yields_to_a_call(puppet, monkeypatch):
    prepare(puppet, monkeypatch, choice='play')
    puppet._stroll._begin()
    assert puppet.start_call() == 'accepted'
    puppet._stroll.tick(0.05)
    assert puppet._stroll.acting is None
    puppet.stop_toy()

