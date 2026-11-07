import pytest
from BaseClasses import CollectionState
from Fill import distribute_items_restrictive

from Options import OptionError
from test.general import setup_multiworld
from worlds.AutoWorld import call_all
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.campaign import STAGE_BY_ID, completion_event

pytestmark = pytest.mark.slow

MISSIONS = {"e1m1_intro", "e1m2_war", "e1m4_boss", "e3m2_hell", "e3m2_hell_b", "e3m4_boss"}
MASTERS = ("ml_e2m1_nest", "ml_e2m3_core", "ml_e5m1_spear", "ml_e1m3_cult", "ml_e2m2_base", "ml_e3m1_slayer")


def assert_master_access(mw):
    world = mw.worlds[1]
    state = mw.get_all_state()
    for key in MASTERS:
        state.set_item(completion_event(key), 1, 0)
    for key in MASTERS:
        location = mw.get_location(STAGE_BY_ID[key]["completion"], 1)
        access = world.create_item(STAGE_BY_ID[key]["name"] + " Access")
        assert location.can_reach(state)
        state.remove(access)
        assert not location.can_reach(state)
        state.collect(access)
        assert location.can_reach(state)


@pytest.mark.parametrize("order", ["vanilla_order", "random_mission_order", "mission_access_as_items"])
def test_master_levels_generate_independently_of_normal_missions(order):
    mw = setup_multiworld(
        DoomEternalWorld,
        seed=42,
        options={
            "mission_pool": "custom",
            "custom_missions": MISSIONS,
            "mission_order": order,
            "include_master_levels": True,
            "goal": "complete_n_master_levels",
            "master_level_count": 6,
            "enemy_randomizer": False,
        },
    )
    assert_master_access(mw)
    distribute_items_restrictive(mw)
    call_all(mw, "post_fill")
    call_all(mw, "finalize_multiworld")
    assert mw.can_beat_game()
    state = CollectionState(mw)
    state.set_item(completion_event("ml_e2m1_nest"), 1, 2)
    assert not mw.completion_condition[1](state)
    for key in list(MASTERS)[1:-1]:
        state.set_item(completion_event(key), 1, 1)
    assert not mw.completion_condition[1](state)
    state.set_item(completion_event("ml_e3m1_slayer"), 1, 1)
    assert mw.completion_condition[1](state)


@pytest.mark.parametrize("options", [
    {"goal": "complete_n_master_levels"},
    {"goal": "kill_the_icon_of_sin", "additional_victory_requirements": {"Complete all Master Levels"}},
])
def test_master_objectives_reject_disabled_master_levels(options):
    with pytest.raises(OptionError, match="requires Include Master Levels"):
        setup_multiworld(DoomEternalWorld, options={**options, "include_master_levels": False})


@pytest.mark.parametrize("goal", ["complete_n_master_levels", "kill_the_icon_of_sin"])
def test_vanilla_master_profiles_and_all_master_requirement_with_expanded_enemies(goal):
    from worlds.doometernal.combat_readiness import evaluate_mission_readiness
    from worlds.doometernal.vanilla_enemy_profiles import source_is_master

    mw = setup_multiworld(
        DoomEternalWorld,
        seed=42,
        options={
            "mission_pool": "custom",
            "custom_missions": {
                "Cultist Base",
                "Super Gore Nest",
                "ARC Complex",
                "Mars Core",
                "Taras Nabad",
                "The World Spear",
                "Final Sin",
            },
            "include_master_levels": True,
            "goal": goal,
            "master_level_count": 1,
            "additional_victory_requirements": {"Complete all Master Levels"},
            "enemy_randomizer": True,
            "killsanity": True,
            "use_dlc_content": False,
        },
    )
    world = mw.worlds[1]
    assert not set(MASTERS) & world.enemy_plan["maps"].keys()
    _assert_vanilla_master_enemies(world, source_is_master)
    state = _normal_campaign_complete(mw)
    for key in list(MASTERS)[:-1]:
        state.set_item(completion_event(key), 1, 1)
    assert not mw.completion_condition[1](state)
    state.set_item(completion_event("ml_e3m1_slayer"), 1, 1)
    assert mw.completion_condition[1](state)
    state = mw.get_all_state()
    state.set_item("Microwave Beam", 1, 0)
    assert (
        "Plasma Rifle and Microwave Beam"
        in evaluate_mission_readiness(state, 1, "ml_e5m1_spear", world).missing_requirements
    )


def _normal_campaign_complete(mw):
    from worlds.doometernal.logic import goal_endpoint_event_name

    state = CollectionState(mw)
    for key in mw.worlds[1].campaign_plan["sequence"]:
        state.set_item(completion_event(key), 1, 1)
    state.set_item(goal_endpoint_event_name("Kill the Icon of Sin"), 1, 1)
    return state


def _assert_vanilla_master_enemies(world, source_is_master):
    import json
    from importlib.resources import files

    native = json.loads(files("worlds.doometernal").joinpath("native_enemy_catalog.json").read_bytes())
    masters = {source["id"] for row in native["maps"].values() for source in row["origins"] if source_is_master(source)}
    recipes = {recipe["id"] for row in world.enemy_plan["maps"].values() for recipe in row["recipes"]}
    assert masters.isdisjoint(recipes)
    assert not any(row["map_key"].startswith("ml_") for row in world.killsanity_plan["finite_sources"])
