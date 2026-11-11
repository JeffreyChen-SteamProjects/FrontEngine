"""Free arranging cannot create currency through ordinary home actions."""
import pytest

from frontengine.utils.pet_game import goals, simulation, snapshot
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.world import World


@pytest.mark.parametrize("mode", ["manage", "sandbox"])
@pytest.mark.parametrize("route", ["goal", "automatic_goal", "commission", "celebration", "sale", "work", "starter"])
def test_home_currency_routes_respect_mode(mode, route):
    world = World(builtin_catalog(), "a" * 32, mode, seed=5)
    world.automatic = False
    zone = world.add_zone("screen", 0, 900, 48)
    pet = "b" * 32
    world.add_resident({"id": pet, "name": "Pet", "mood": 90, "fullness": 90,
                        "energy": 90, "affection": 0}, zone)
    world.residents[pet].traits = ()
    if route == "goal":
        assert goals.claim(world, "move_in") == "accepted"
    elif route == "automatic_goal":
        world.automatic = True
        goals.update(world)
        assert world.progress.goals.get("move_in") == "claimed"
    elif route == "commission":
        goals.refresh_commissions(world)
        offer = world.progress.commissions["offers"][0]
        world.ledger.apply("materials", "fixture", items={offer["item"]: offer["count"]})
        assert goals.deliver(world, 0) == "accepted"
        assert offer["done"]
    elif route == "celebration":
        world.add_resident({"id": "c" * 32, "name": "Friend", "mood": 90, "fullness": 90, "energy": 90, "affection": 0}, zone)
        for recipe in ("letter", "herbs", "toy"):
            world.progress.stats["settled:" + recipe] = 1
        assert goals.celebrate(world) == "accepted"
    elif route == "sale":
        world.ledger.apply("goods", "fixture", items={"herb": 3})
        assert world.sell_item("herb", 3, "sale") == "accepted"
        assert world.ledger.count("herb") == 0
    elif route == "work":
        world.ledger.apply("desk", "fixture", items={"furniture:desk_basic": 1})
        assert world.place_anywhere("desk_basic", zone)[0] == "accepted"
        assert world.create_task("letter", pet)[0] == "accepted"
        for _ in range(1500):
            simulation.step(world)
            if not world.tasks:
                break
        assert not world.tasks
        assert any(event["kind"] == "settled" for event in world.events)
    else:
        assert world.grant_starter_kit() == "accepted"
    if mode == "manage":
        assert world.ledger.coins > 0
    else:
        assert world.ledger.coins == 0
        assert all(event.get("coins", 0) == 0 for event in world.events)
        restored = snapshot.from_dict(snapshot.to_dict(world), world.catalog)
        assert restored.ledger.coins == 0


@pytest.mark.parametrize("mode", ["manage", "sandbox"])
def test_old_home_currency_load_preserves_items_and_transaction_history(mode):
    world = World(builtin_catalog(), "a" * 32, mode)
    world.add_zone("screen", 0, 900, 48)
    world.ledger.apply("old-reward", "goal", 17, {"wood": 3})
    assert world.ledger.reserve({"wood": 1})
    saved = snapshot.to_dict(world)
    restored = snapshot.from_dict(saved, world.catalog)
    assert restored.ledger.coins == (17 if mode == "manage" else 0)
    assert restored.ledger.items == {"wood": 3}
    assert restored.ledger.applied("old-reward")
    assert list(restored.ledger.journal) == saved["ledger"]["journal"]
    assert saved["ledger"]["coins"] == 17
    assert snapshot.to_dict(snapshot.from_dict(snapshot.to_dict(restored), world.catalog)) == snapshot.to_dict(restored)


@pytest.mark.parametrize("kind, expected", [
    ("settled", "Pet finished Letter"),
    ("commission_done", "Commission delivered"),
    ("goal_claimed", "Goal completed"),
])
def test_zero_currency_completion_notice_has_no_reward_claim(kind, expected):
    from frontengine.ui.page.pet_game.inbox_panel import line
    event = {"kind": kind, "coins": 0, "resident_name": "Pet", "recipe_label": ("", "Letter")}
    assert line(event) == expected


@pytest.mark.parametrize("mode", ["manage", "sandbox"])
def test_material_purchase_and_sale_keep_currency_policy_and_duplicate_protection(mode):
    world = World(builtin_catalog(), "a" * 32, mode)
    if mode == "manage":
        world.ledger.apply("funding", "fixture", 1000)
    before = world.ledger.coins
    wood = world.catalog.items["wood"]
    assert world.buy_item("wood", 2, "purchase") == "accepted"
    purchased = world.ledger.to_dict()
    assert world.buy_item("wood", 2, "purchase") == "duplicate"
    assert world.ledger.to_dict() == purchased
    assert world.ledger.coins == before - (wood.buy_price * 2 if mode == "manage" else 0)
    assert world.sell_item("wood", 1, "sale") == "accepted"
    sold = world.ledger.to_dict()
    assert world.sell_item("wood", 1, "sale") == "duplicate"
    assert world.ledger.to_dict() == sold
    assert world.ledger.count("wood") == 1
    assert world.ledger.coins == before + ((wood.sell_price - wood.buy_price * 2) if mode == "manage" else 0)


@pytest.mark.parametrize("mode", ["manage", "sandbox"])
def test_displayed_goal_commission_work_and_sale_amounts_match_mode(mode):
    from frontengine.ui.page.pet_game.goals_panel import GoalsPanel
    from frontengine.ui.page.pet_game.home_panels import StoragePanel, recipe_details
    from frontengine.utils.multi_language.retranslate import translate
    world = World(builtin_catalog(), "a" * 32, mode)
    goal = goals.TUTORIAL[0]
    reward = goal.coins if mode == "manage" else 0
    name = translate("pet_game_goal_" + goal.identifier, goal.identifier)
    assert GoalsPanel._goal_line(world, goal) == translate("pet_home_goal_line").format(
        mark="○", name=name, current=0, target=1, coins=reward)
    goals.refresh_commissions(world)
    offer = world.progress.commissions["offers"][0]
    commission = GoalsPanel._offer_line(world, offer)
    assert f"{offer['coins'] if mode == 'manage' else 0} coins" in commission
    recipe = world.catalog.recipes["letter"]
    assert f"{recipe.coins if mode == 'manage' else 0} coins" in recipe_details(world, recipe)
    sale = StoragePanel._line(world, "herb", 1)
    assert ("sells for" in sale) is (mode == "manage")


def test_automatic_job_notice_describes_start_not_completion():
    from frontengine.ui.page.pet_game.inbox_panel import line
    assert line({"kind": "auto_job", "resident_name": "Pet", "recipe_label": ("", "Letter")}) == "Pet took up Letter"
