"""Personal wishes require the resident's own completed activity."""
import pytest

from frontengine.utils.pet_game import simulation, snapshot
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.world import World

A, B, C = ('b' * 32, 'c' * 32, 'd' * 32)


def home(activity='play'):
    world = World(builtin_catalog(), 'a' * 32, seed=5)
    world.automatic = False
    shared = world.add_zone('shared', 0, 0, 40)
    separate = world.add_zone('separate', 1000, 0, 40)
    world.grant_starter_kit()
    world.furnish(shared)
    world.ledger.apply('fixture', 'fixture', 40)
    assert world.buy_and_place('toy_box', shared, 'toy') == 'accepted'
    for identifier, zone in ((A, shared), (B, shared), (C, separate)):
        world.add_resident({'id': identifier, 'name': identifier[0], 'mood': 80,
                            'fullness': 20 if activity == 'eat' else 90,
                            'energy': 90, 'affection': 0}, zone)
    return world


def run(world, steps=900):
    events = []
    for _ in range(steps):
        simulation.step(world)
        events.extend(world.drain_events())
    return events


def wish(world, identifier, kind):
    world.progress.wishes[identifier] = {'wish': kind, 'base': 0, 'ready': 0}


def test_other_residents_play_does_not_fulfil_personal_wish():
    world = home()
    wish(world, C, 'play_time')
    assert world.command(A, 'play') == 'accepted'
    events = run(world)
    assert any(e['kind'] == 'completed' and e.get('activity') == 'play' and e['resident'] == A for e in events)
    assert not any(e['kind'] == 'completed' and e.get('activity') == 'play' and e['resident'] == C for e in events)
    assert not [e for e in events if e['kind'] == 'wish_granted' and e['resident'] == C]
    assert world.residents[C].affection == 0


@pytest.mark.parametrize('activity', ['play', 'eat'])
def test_meal_wish_requires_a_meal_and_credits_only_participants(activity):
    world = home(activity)
    for identifier in (A, B, C):
        wish(world, identifier, 'friend_meal')
    for identifier in (A, B):
        assert world.command(identifier, activity) == 'accepted'
    events = run(world)
    assert any(e['kind'] == 'shared' for e in events), 'Fixture did not complete a shared activity'
    granted = [e['resident'] for e in events if e['kind'] == 'wish_granted' and e['wish'] == 'friend_meal']
    assert sorted(granted) == ([A, B] if activity == 'eat' else [])


def test_own_play_completes_legacy_wish_once_and_survives_save():
    world = home()
    wish(world, A, 'play_time')
    world.progress.wishes[A]['base'] = 999  # Legacy global counter must not block the next personal action.
    saved = snapshot.to_dict(world)
    saved['version'] = 7
    saved['progress'].pop('event_days')
    world = snapshot.from_dict(saved, world.catalog)
    world.automatic = False
    assert world.progress.wishes[A]['base'] == 999
    assert world.command(A, 'play') == 'accepted'
    events = run(world)
    assert len([e for e in events if e['kind'] == 'wish_granted' and e['resident'] == A]) == 1
    assert world.residents[A].affection == 3
    loaded = snapshot.from_dict(snapshot.to_dict(world), world.catalog)
    assert loaded.progress.wishes[A] == world.progress.wishes[A]
    assert not [e for e in run(loaded, 155) if e['kind'] == 'wish_granted' and e['resident'] == A]


@pytest.mark.parametrize('cancel', ['stop', 'store'])
def test_interrupted_play_does_not_complete_wish(cancel):
    world = home()
    wish(world, A, 'play_time')
    assert world.command(A, 'play') == 'accepted'
    for _ in range(300):
        simulation.step(world)
        if world.residents[A].activity is not None and world.residents[A].activity.kind == 'play':
            break
    assert world.residents[A].activity.kind == 'play'
    if cancel == 'stop':
        assert world.command(A, 'stop') == 'accepted'
    toy = next(p.identifier for p in world.furniture.values() if p.definition == 'toy_box')
    assert world.store(toy) == 'accepted'
    events = run(world, 155)
    assert not [e for e in events if e['kind'] == 'wish_granted' and e['resident'] == A]
    assert world.progress.wishes[A]['wish'] == 'play_time'
    assert world.residents[A].affection == 0


def test_meal_wish_is_independent_of_social_notification_cooldown():
    world = home('eat')
    world.social_ready['shared:' + world.pair(A, B)] = world.time_ms + 600000
    for identifier in (A, B):
        wish(world, identifier, 'friend_meal')
        assert world.command(identifier, 'eat') == 'accepted'
    events = run(world)
    assert not [e for e in events if e['kind'] == 'shared']
    assert sorted(e['resident'] for e in events if e['kind'] == 'wish_granted') == [A, B]
