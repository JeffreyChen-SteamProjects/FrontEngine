"""Raised pieces reached by climbing or pet stairs, and crossing points between zones."""
from frontengine.utils.pet_game import arrangement, behaviour, simulation, snapshot
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.world import World

CATALOG = builtin_catalog()
PET = "b" * 32
OTHER = "c" * 32


def _world(traits=("quiet", "bookish")):
    world = World(CATALOG, "a" * 32, "sandbox", seed=5)
    zone = world.add_zone("left", 0, 0, 40)
    world.add_resident({"id": PET, "name": "Mochi", "mood": 60, "fullness": 60, "affection": 1, "energy": 60}, zone)
    world.residents[PET].traits = tuple(traits)
    return world, zone


def _place(world, name, zone, cell):
    world.buy(name, f"buy-{name}-{cell}")
    return world.place(name, zone, cell)


def test_raised_pieces_never_hold_work_and_stairs_are_walkable():
    raised = [d for d in CATALOG.furniture.values() if d.raised]
    assert {d.identifier for d in raised} == {"cat_tree", "climbing_wall"}
    assert all(d.profession is None for d in raised)              # ordinary work stays on the ground
    assert not CATALOG.furniture["pet_stairs"].solid


def test_a_raised_piece_needs_stairs_beside_it_unless_a_pet_climbs():
    world, zone = _world()
    assert world.preview("cat_tree", zone, 10) == "unreachable"
    assert _place(world, "cat_tree", zone, 10)[0] == "unreachable"
    assert _place(world, "pet_stairs", zone, 12)[0] == "accepted"
    result, tree = _place(world, "cat_tree", zone, 10)
    assert result == "accepted"
    stairs = next(p.identifier for p in world.furniture.values() if p.definition == "pet_stairs")
    assert world.move(stairs, 30) == "unreachable"                # moving them away would strand the tree
    world.residents[PET].traits = ("playful", "quiet")
    assert world.move(stairs, 30) == "accepted"                   # a climber reaches it without them
    assert world.reachable(world.residents[PET], world.furniture[tree])


def test_pets_skip_pieces_they_cannot_reach():
    world, zone = _world(("playful", "quiet"))
    tree = _place(world, "cat_tree", zone, 10)[1]
    climber = world.residents[PET]
    assert behaviour._free_piece(world, climber, "relax")[0] == tree
    climber.traits = ("quiet", "bookish")                         # stranded: no stairs, no climbing
    assert behaviour._free_piece(world, climber, "relax") is None


def test_layouts_set_out_stairs_before_raised_pieces():
    world, zone = _world()
    pieces = [("cat_tree", 10, False), ("pet_stairs", 12, False)]
    assert arrangement.apply_layout(world, zone, pieces, "t1", buy_missing=True) == ("accepted", 0)
    assert sorted(name for name, _c, _f in arrangement.layout_of(world, zone)) == ["cat_tree", "pet_stairs"]


def test_linking_zones_is_symmetric_and_saved():
    world, left = _world()
    right = world.add_zone("right", 1920, 0, 30)
    third = world.add_zone("third", 3840, 0, 30)
    assert world.link_zones(left, left) == "unknown"
    assert world.link_zones(left, right) == "accepted"
    assert (world.zones[left].link, world.zones[right].link) == (right, left)
    assert world.link_zones(third, right) == "accepted"             # right now leads to third only
    assert (world.zones[left].link, world.zones[right].link, world.zones[third].link) == (None, third, right)
    loaded = snapshot.from_dict(snapshot.to_dict(world), CATALOG)
    assert loaded.zones[right].link == third
    world.set_offline({third})
    assert world.crossing(right) is None                          # never into a disconnected screen
    assert world.link_zones(right, None) == "accepted"
    assert world.zones[third].link is None


def test_older_saves_load_without_crossings():
    world, zone = _world()
    data = snapshot.to_dict(world)
    data["version"] = 4
    for raw in data["zones"]:
        del raw["link"]
    assert snapshot.from_dict(data, CATALOG).zones[zone].link is None


def test_a_pet_crosses_over_and_walks_home_to_its_own_bed():
    world, left = _world()
    right = world.add_zone("right", 1920, 0, 30)
    world.link_zones(left, right)
    bed = _place(world, "bed_basic", left, 3)[1]
    world.assign_bed(bed, PET)
    pet = world.residents[PET]
    pet.x_milli = 20 * 32 * 1000
    behaviour.start_visit(world, pet, "visiting")
    for _ in range(4000):
        simulation.step(world)
        if pet.zone == right:
            break
    assert pet.zone == right
    assert world.furniture[bed].owner == PET                       # walking over keeps its bed
    behaviour.start_rest(world, pet, "tired")
    assert (pet.activity.kind, pet.activity.reason) == ("visit", "going_home")


def test_choosing_where_the_entrance_leads_on_the_page(tmp_path, monkeypatch):
    from frontengine.show.pet_game.home_service import HomeService
    from frontengine.ui.page.pet_game.home_page import PetHomePage
    from frontengine.user_setting.pet_game_save import HomeSaveStore
    from frontengine.user_setting.pet_profiles import PetProfiles
    from frontengine.user_setting.user_setting_file import user_setting_dict
    monkeypatch.setitem(user_setting_dict, "pet_home_running", False)
    monkeypatch.setitem(user_setting_dict, "pet_home_on_desktop", False)
    service = HomeService(None, HomeSaveStore(tmp_path, CATALOG), PetProfiles({}, lambda: None))
    page = PetHomePage(service)
    try:
        page.create_home()
        first = page.zone
        second = service.run(lambda world: world.add_zone("second", 1920, 0, 30))
        page.refresh()
        combo = page.layout_panel.crossing
        assert combo.isEnabled()
        combo.setCurrentIndex(combo.findData(second))
        page.layout_panel.link_zone()
        assert service.world.zones[first].link == second
        assert service.world.zones[second].link == first
    finally:
        page.shutdown()
        page.deleteLater()
