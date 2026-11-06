import pytest

from Fill import distribute_items_restrictive
from test.general import setup_multiworld
from worlds.AutoWorld import call_all
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.campaign import REGION_STAGE
from worlds.doometernal.generated_content import ARENA_LOCATION_KINDS
from worlds.doometernal.locations import location_data_table


@pytest.mark.parametrize("choice,kinds", [
    ("all_levels", {"base", "dlc", "master"}),
    ("dlc_and_master_levels", {"dlc", "master"}),
    ("only_dlc_levels", {"dlc"}),
    ("only_master_levels", {"master"}),
    ("no_levels", set()),
])
@pytest.mark.parametrize("missions", [
    {"Hell on Earth", "Exultia", "Cultist Base", "Super Gore Nest", "Mars Core", "Final Sin"},
    {"Hell on Earth", "Exultia", "UAC Atlantica Facility", "The Blood Swamps", "The Holt", "Final Sin"},
    {"Hell on Earth", "Exultia", "The World Spear", "Reclaimed Earth", "Immora", "Final Sin"},
], ids=["base", "tag1", "tag2"])
def test_arena_checks_follow_choice_and_active_missions(choice, kinds, missions):
    mw = setup_multiworld(DoomEternalWorld, seed=42, options={
        "arena_checks": choice, "mission_pool": "custom", "custom_missions": missions,
        "mission_order": "vanilla_order", "goal": "kill_the_icon_of_sin", "enemy_randomizer": False,
    })
    world = mw.worlds[1]
    expected = {name for name, kind in ARENA_LOCATION_KINDS.items()
                if kind in kinds and REGION_STAGE[location_data_table[name].region] in world.campaign_plan["stage_ids"]}
    present = {loc.name for loc in mw.get_locations(1)} & ARENA_LOCATION_KINDS.keys()
    assert present == expected
    state = mw.get_all_state()
    for name in present:
        loc = mw.get_location(name, 1)
        assert loc.parent_region.name == location_data_table[name].region
        assert loc.can_reach(state), name
    distribute_items_restrictive(mw)
    call_all(mw, "post_fill")
    call_all(mw, "finalize_multiworld")
    assert world.fill_slot_data()["runtime"]["checks"]["arena_checks"] == world.options.arena_checks.value


def test_dark_lord_arena_uses_boss_readiness():
    mw = setup_multiworld(DoomEternalWorld, seed=42, options={
        "mission_pool": "dlc_only", "goal": "kill_the_dark_lord", "enemy_randomizer": False,
    })
    location = mw.get_location("The Dark Lord - Arena - Dark Lord", 1)
    assert location.address == 7774901
    state = mw.get_all_state()
    assert location.can_reach(state)
    state.set_item("Blood Punch", 1, 0)
    assert not location.access_rule(state)
