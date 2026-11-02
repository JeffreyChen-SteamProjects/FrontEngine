"""Cleanliness: it wears down slowly, a pet tidies itself up when grubby, a bath tub is quicker,
grooming helps, and older homes load with freshly washed pets."""
from frontengine.ui.page.pet_game.home_pending import pending
from frontengine.utils.pet_game import behaviour, simulation, snapshot
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.resident import FRESH_HYGIENE
from frontengine.utils.pet_game.world import World

CATALOG = builtin_catalog()
PET = "b" * 32
MINUTE_STEPS = 60_000 // simulation.STEP_MS


def _world(mode="manage"):
    world = World(CATALOG, "a" * 32, mode, seed=3)
    zone = world.add_zone("s", 0, 0, 40)
    world.add_resident({"id": PET, "name": "Mochi", "mood": 60, "fullness": 90, "affection": 1,
                        "energy": 90}, zone)
    return world, zone


def _steps(world, count):
    for _ in range(count):
        simulation.step(world)


def test_a_new_pet_arrives_clean_and_cleanliness_wears_down_by_a_point_a_minute():
    world, _zone = _world()
    pet = world.residents[PET]
    assert pet.needs["hygiene"] == FRESH_HYGIENE
    pet.activity = None
    pet.decide_after_ms = 10 ** 12                     # keep it idle so only the base rate applies
    _steps(world, 5 * MINUTE_STEPS)
    assert pet.needs["hygiene"] == FRESH_HYGIENE - 5


def test_a_grubby_pet_without_a_tub_tidies_itself_up_until_clean():
    world, _zone = _world()
    pet = world.residents[PET]
    pet.needs["hygiene"] = behaviour.LOW_HYGIENE
    pet.activity = None
    behaviour.decide(world, pet)
    assert (pet.activity.kind, pet.activity.reason) == ("tidy", "grubby")
    for step in range(6 * MINUTE_STEPS):
        simulation.step(world)
        if pet.activity is None or pet.activity.kind != "tidy":
            break
    assert pet.needs["hygiene"] >= 95                     # it stops once clean
    assert step > 3 * MINUTE_STEPS                         # 20 points a minute on its own


def test_a_bath_tub_is_used_when_there_is_one_and_is_quicker():
    world, zone = _world("sandbox")
    world.buy("bath_tub", "buy-tub")
    assert world.place("bath_tub", zone, 20)[0] == "accepted"
    pet = world.residents[PET]
    pet.needs["hygiene"] = 20
    pet.activity = None
    behaviour.decide(world, pet)
    assert pet.activity.kind == "wash"
    assert world.furniture[pet.activity.furniture].definition == "bath_tub"
    for minutes in range(1, 6):
        _steps(world, MINUTE_STEPS)
        if pet.needs["hygiene"] >= 95:
            break
    assert pet.needs["hygiene"] >= 95
    assert minutes <= 3                                   # tidying alone would take about four


def test_asking_a_pet_to_wash_and_grooming_both_help():
    world, _zone = _world()
    pet = world.residents[PET]
    pet.needs["hygiene"] = 50
    assert world.interact(PET, "groom") == "accepted"
    assert pet.needs["hygiene"] == 65
    assert world.command(PET, "wash") == "accepted"
    behaviour.decide(world, pet)
    assert (pet.activity.kind, pet.activity.reason) == ("tidy", "command")


def test_feeling_grubby_wears_on_mood():
    world, _zone = _world()
    pet = world.residents[PET]
    clean = simulation._rates(world, pet)["mood"]
    pet.needs["hygiene"] = behaviour.LOW_HYGIENE - 1
    assert simulation._rates(world, pet)["mood"] == clean - 1


def test_older_homes_load_with_washed_pets_and_new_homes_keep_cleanliness():
    world, _zone = _world()
    world.residents[PET].needs["hygiene"] = 42
    data = snapshot.to_dict(world)
    assert data["version"] == 7
    assert snapshot.from_dict(data, CATALOG).residents[PET].needs["hygiene"] == 42
    old = snapshot.to_dict(world)
    old["version"] = 6
    for resident in old["residents"]:
        del resident["needs"]["hygiene"]
    assert snapshot.from_dict(old, CATALOG).residents[PET].needs["hygiene"] == FRESH_HYGIENE


def test_the_waiting_list_suggests_a_tub_only_when_there_is_none():
    world, zone = _world()
    world.residents[PET].needs["hygiene"] = 10
    lines = [text for text, _tab in pending(world)]
    assert any("Mochi" in text and "tub" in text for text in lines)
    world.ledger.apply("test-coins", "test", 500)
    assert world.buy("bath_tub", "buy-tub") == "accepted"
    world.place("bath_tub", zone, 20)
    assert not any("tub" in text for text, _tab in pending(world))
