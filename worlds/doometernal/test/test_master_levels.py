import pytest

from BaseClasses import CollectionState
from Fill import distribute_items_restrictive
from Options import OptionError
from test.general import setup_multiworld
from worlds.AutoWorld import call_all
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.campaign import STAGE_BY_ID, completion_event
from worlds.doometernal.generated_content import ARENA_LOCATION_KINDS

MISSIONS = {"e1m1_intro", "e1m2_war", "e1m4_boss", "e3m2_hell", "e3m2_hell_b", "e3m4_boss"}
MASTERS = {"ml_e2m1_nest": (7776001, 7772100), "ml_e2m3_core": (7776002, 7772200),
           "ml_e5m1_spear": (7776003, 7772300), "ml_e1m3_cult": (7776004, 7772130),
           "ml_e2m2_base": (7776005, 7772230), "ml_e3m1_slayer": (7776006, 7772330)}


@pytest.mark.parametrize("order", ["vanilla_order", "random_mission_order", "mission_access_as_items"])
@pytest.mark.parametrize("arenas", ["all_levels", "dlc_and_master_levels", "only_dlc_levels", "only_master_levels", "no_levels"])
def test_master_levels_generate_independently_of_normal_missions(order, arenas):
    mw = setup_multiworld(DoomEternalWorld, seed=42, options={
        "mission_pool": "custom", "custom_missions": MISSIONS, "mission_order": order,
        "include_master_levels": True, "goal": "complete_n_master_levels", "master_level_count": 6,
        "arena_checks": arenas, "enemy_randomizer": False,
    })
    world = mw.worlds[1]
    plan = world.campaign_plan
    _assert_access(plan)
    _assert_checks(mw, arenas)
    distribute_items_restrictive(mw)
    call_all(mw, "post_fill")
    call_all(mw, "finalize_multiworld")
    data = world.fill_slot_data()
    assert data["campaign"]["goal"]["count"] == 6
    assert set(data["stage_profiles"]) == set(plan["stage_ids"])
    assert not MASTERS.keys() & set(data["recipes"]["maps"])
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

    mw = setup_multiworld(DoomEternalWorld, seed=42, options={
        "mission_pool": "custom", "custom_missions": {"Cultist Base", "Super Gore Nest", "ARC Complex", "Mars Core", "Taras Nabad", "The World Spear", "Final Sin"},
        "include_master_levels": True, "goal": goal, "master_level_count": 1,
        "additional_victory_requirements": {"Complete all Master Levels"},
        "enemy_randomizer": True, "killsanity": True, "use_dlc_content": False,
    })
    world = mw.worlds[1]
    assert not MASTERS.keys() & world.enemy_plan["maps"].keys()
    _assert_vanilla_master_enemies(world, source_is_master)
    state = _normal_campaign_complete(mw)
    for key in list(MASTERS)[:-1]:
        state.set_item(completion_event(key), 1, 1)
    assert not mw.completion_condition[1](state)
    state.set_item(completion_event("ml_e3m1_slayer"), 1, 1)
    assert mw.completion_condition[1](state)
    state = mw.get_all_state()
    state.set_item("Microwave Beam", 1, 0)
    assert "Plasma Rifle and Microwave Beam" in evaluate_mission_readiness(state, 1, "ml_e5m1_spear", world).missing_requirements


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


def _assert_access(plan):
    assert set(plan["master_level_stage_ids"]) == MASTERS.keys()
    assert all(STAGE_BY_ID[key]["map_key"] not in plan["sequence"] for key in MASTERS)
    assert not MASTERS.keys() & set(plan["sequence"])
    for key, (access, completion) in MASTERS.items():
        assert (STAGE_BY_ID[key]["access_id"], STAGE_BY_ID[key]["completion_id"]) == (access, completion)
        assert str(access) in plan["access_items"]
        assert plan["semantic_placement_counts"][STAGE_BY_ID[key]["name"] + " Access"] == 1


def _assert_checks(mw, arenas):
    names = {loc.name for loc in mw.get_locations(1)}
    master_arenas = {name for name, kind in ARENA_LOCATION_KINDS.items() if kind == "master"}
    assert names & master_arenas == (master_arenas if arenas in {"all_levels", "dlc_and_master_levels", "only_master_levels"} else set())
    all_state = mw.get_all_state()
    for key in MASTERS:
        all_state.set_item(completion_event(key), 1, 0)
    assert all(mw.get_location(STAGE_BY_ID[key]["completion"], 1).can_reach(all_state) for key in MASTERS)
