"""
寵物鬼抓人的純邏輯測試（不建立 widget）。
Tests for the pets' tag game — pure logic, no widgets.
"""
from frontengine.show.pet.desktop_pet import TAG_CHASE, TAG_FLEE, PetTagGame


def test_a_game_needs_two_players() -> None:
    game = PetTagGame()
    assert game.update({}) == {}
    assert game.update({"a": (0, 0)}) == {}
    assert game.it is None


def test_first_update_picks_an_it_and_assigns_every_role() -> None:
    game = PetTagGame()
    roles = game.update({"a": (0, 0), "b": (500, 0)})
    assert game.it in ("a", "b")
    assert set(roles) == {"a", "b"}
    assert roles[game.it][0] == TAG_CHASE
    others = [role for key, role in roles.items() if key != game.it]
    assert all(role[0] == TAG_FLEE for role in others)


def test_the_chaser_heads_for_its_nearest_peer() -> None:
    game = PetTagGame()
    game.it = "a"
    roles = game.update({"a": (0, 0), "b": (700, 0), "c": (300, 0)})
    assert roles["a"] == (TAG_CHASE, 300.0, 0.0)


def test_runners_head_away_from_the_chaser() -> None:
    game = PetTagGame()
    game.it = "a"
    roles = game.update({"a": (400, 0), "b": (600, 0), "c": (200, 0)})
    assert roles["b"][1] > 600, "a peer on the right runs further right"
    assert roles["c"][1] < 200, "a peer on the left runs further left"


def test_runners_flee_diagonally_when_they_are_not_in_line() -> None:
    game = PetTagGame(flee_distance=100.0)
    game.it = "a"
    roles = game.update({"a": (0, 0), "b": (60, 80)})  # 3-4-5 triangle, out of reach
    _role, target_x, target_y = roles["b"]
    assert round(target_x) == 120, "runs 100 further along the same direction"
    assert round(target_y) == 160


def test_overlapping_runners_still_get_a_direction() -> None:
    # Seeded by update() so the opening cooldown holds the tag off, leaving two
    # pets standing on exactly the same spot with no direction to flee along.
    game = PetTagGame(flee_distance=50.0, cooldown_ticks=99)
    roles = game.update({"a": (100, 100), "b": (100, 100)})
    assert game.it == "a"
    assert roles["b"] == (TAG_FLEE, 150.0, 100.0)


def test_catching_passes_the_tag_on() -> None:
    game = PetTagGame(cooldown_ticks=0)
    game.it = "a"
    game.update({"a": (0, 0), "b": (10, 0)})
    assert game.it == "b"
    assert game.just_tagged == "b"


def test_a_distant_peer_is_not_caught() -> None:
    game = PetTagGame(cooldown_ticks=0)
    game.it = "a"
    game.update({"a": (0, 0), "b": (500, 0)})
    assert game.it == "a"
    assert game.just_tagged is None


def test_cooldown_stops_the_tag_bouncing_straight_back() -> None:
    game = PetTagGame(cooldown_ticks=3)
    game.it = "a"
    positions = {"a": (0, 0), "b": (10, 0)}
    game.update(positions)
    assert game.it == "b", "touching peers are tagged straight away"
    for _ in range(3):
        game.update(positions)
        assert game.it == "b", "the new chaser cannot be tagged back while cooling down"
        assert game.just_tagged is None
    game.update(positions)
    assert game.it == "a", "once the cooldown is over the tag can pass again"


def test_a_leaving_player_hands_the_tag_to_someone_present() -> None:
    game = PetTagGame()
    game.update({"a": (0, 0), "b": (500, 0), "c": (900, 0)})
    game.it = "gone"
    roles = game.update({"a": (0, 0), "b": (500, 0), "c": (900, 0)})
    assert game.it in ("a", "b", "c")
    assert roles[game.it][0] == TAG_CHASE


def test_dropping_below_two_players_ends_the_game() -> None:
    game = PetTagGame()
    game.update({"a": (0, 0), "b": (500, 0)})
    assert game.update({"a": (0, 0)}) == {}
    assert game.it is None
    assert game.just_tagged is None


def test_reset_clears_everything() -> None:
    game = PetTagGame()
    game.update({"a": (0, 0), "b": (500, 0)})
    game.reset()
    assert game.it is None
    assert game.just_tagged is None


def test_just_tagged_only_lasts_one_update() -> None:
    game = PetTagGame(cooldown_ticks=0)
    game.it = "a"
    game.update({"a": (0, 0), "b": (10, 0)})
    assert game.just_tagged == "b"
    game.update({"a": (0, 0), "b": (900, 0)})
    assert game.just_tagged is None


def test_the_chase_converges_when_the_chaser_is_faster() -> None:
    """跑一段模擬：鬼走得比逃的快，最後一定抓得到 / A faster chaser eventually tags."""
    game = PetTagGame(cooldown_ticks=0)
    game.it = "a"
    positions = {"a": [0.0, 0.0], "b": [400.0, 0.0]}
    tagged = False
    for _ in range(300):
        roles = game.update({key: tuple(value) for key, value in positions.items()})
        if game.just_tagged is not None:
            tagged = True
            break
        for key, (role, target_x, _target_y) in roles.items():
            speed = 6.0 if role == TAG_CHASE else 3.0
            step = speed if target_x > positions[key][0] else -speed
            positions[key][0] += step
    assert tagged
