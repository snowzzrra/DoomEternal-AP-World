import json
from collections import Counter
from pathlib import Path

import pytest
from BaseClasses import CollectionState, Item, ItemClassification, LocationProgressType
from Options import OptionError
from test.general import gen_steps, setup_multiworld
from worlds.AutoWorld import call_all
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.campaign import completion_event
from worlds.doometernal.native_enemy_balance import _arena_reference_count_floor

from .generation_support import (
    assert_optional_reward,
    collect_sphere_items,
    fill,
    filled_item_counts,
    item_counts,
    physical_items,
)

PRESETS = json.loads(Path(__file__).with_name("pillar_presets.json").read_text())
CASES = [(case["id"], case["seed"], case["options"]) for case in PRESETS] + [
    ("unmaykr", 230001, {**PRESETS[0]["options"], "goal": "acquire_the_unmaykr"}),
    ("master_goal", 230001, {**PRESETS[1]["options"], "goal": "complete_n_master_levels", "master_level_count": 2}),
    ("randomized_enemies", 230001, {**PRESETS[0]["options"], "enemy_randomizer": True,
                                   "killsanity": True, "killsanity_maximum_milestones": 50}),
    ("starting_inventory", 230001, {**PRESETS[0]["options"], "start_inventory": {"Ballista": 1},
                            "start_inventory_from_pool": {"Heavy Cannon": 1}}),
    ("killsanity_auto", 230001, {**PRESETS[0]["options"], "killsanity": True}),
    ("killsanity_fixed", 230002, {**PRESETS[0]["options"], "killsanity": True,
                               "mission_order": "random_mission_order", "killsanity_maximum_milestones": 50,
                               "accessibility": "full"}),
]


def walk_spheres(mw):
    state = CollectionState(mw)
    checked = set()
    for sphere in mw.get_spheres():
        for world in mw.worlds.values():
            assert_killsanity_budget(world, state)
        assert all(location.can_reach(state) for location in sphere)
        assert checked.isdisjoint(sphere)
        collect_sphere_items(state, sphere)
        checked.update(sphere)
    assert checked == set(mw.get_filled_locations())
    assert mw.fulfills_accessibility()
    return state


def assert_killsanity_budget(world, state):
    plan = world.killsanity_plan
    budget = sum(count for key, count in plan["stage_estimates"].items()
                 if world.get_location(completion_event(key)).can_reach(state))
    campaign_complete = all(world.get_location(completion_event(key)).can_reach(state)
                            for key in world.campaign_plan["stage_ids"])
    for ordinal, row in enumerate(plan["milestones"], 1):
        location = world.get_location(f"Kill Reward {ordinal:04d}")
        if row["threshold"] * 100 > sum(plan["stage_estimates"].values()) * 110:
            assert location.can_reach(state) == campaign_complete
            assert_optional_reward(location)
        else:
            assert location.can_reach(state) == (row["threshold"] * 100 <= budget * 110)


def assert_tracker_killsanity(world, seed):
    mw = setup_multiworld(DoomEternalWorld, steps=(), seed=seed)
    mw.re_gen_passthrough = {world.game: world.fill_slot_data()}
    for step in gen_steps:
        call_all(mw, step)
    tracker = mw.worlds[1]
    assert tracker.killsanity_plan["stage_estimates"] == world.killsanity_plan["stage_estimates"]
    state = CollectionState(mw)
    assert_killsanity_budget(tracker, state)
    for sphere in world.multiworld.get_spheres():
        for location in sphere:
            state.collect(location.item, prevent_sweep=True)
        assert_killsanity_budget(tracker, state)


@pytest.mark.parametrize("name,seed,options", CASES, ids=[name for name, _, _ in CASES])
def test_generation_reaches_goal_and_conserves_items(name, seed, options):
    mw = setup_multiworld(DoomEternalWorld, steps=gen_steps[:-1], seed=seed, options=options)
    world = mw.worlds[1]
    for item_name, count in world.options.start_inventory.value.items():
        for _ in range(count):
            mw.push_precollected(world.create_item(item_name))
    before = item_counts(physical_items(mw))
    call_all(mw, "pre_fill")

    fill(mw)
    state = walk_spheres(mw)

    assert mw.has_beaten_game(state, 1)
    assert not mw.get_unfilled_locations()
    assert filled_item_counts(mw) == before
    assert Counter(item.name for item in mw.precollected_items[1]) >= Counter(options.get("start_inventory", {}))
    if world.options.killsanity.value:
        assert_tracker_killsanity(world, seed)


def test_fixed_killsanity_has_rewards_above_budget():
    _, seed, options = next(case for case in CASES if case[0] == "killsanity_fixed")
    mw = setup_multiworld(DoomEternalWorld, seed=seed, options=options)
    assert mw.worlds[1].get_region("Killsanity").locations[-1].progress_type == LocationProgressType.EXCLUDED


def test_arena_reference_count_floor():
    own = {"finite_total": 24}
    for revision, kind, count, use_own in (
        (21, "arena_encounter", 11, True),
        (21, "arena_encounter", 12, False),
        (21, "arena_encounter", 0, True),
        (20, "arena_encounter", 3, False),
        (21, "ambient_encounter", 3, False),
        (21, "secret_encounter", 3, False),
        (21, "specialized_encounter", 3, False),
    ):
        reference = {"finite_total": count}
        result = _arena_reference_count_floor(reference, kind, "own_map", own, revision, "other_map", "vanilla_encounter")
        expected = (own, "own_map", "native_arena_count_floor") if use_own else (
            reference, "other_map", "vanilla_encounter")
        assert result == expected


def test_slayer_gate_rewards_restrict_useful_items():
    options = {**PRESETS[0]["options"], "mission_count": 13, "useful_slayer_gate_rewards": 75}
    mw = setup_multiworld([DoomEternalWorld, DoomEternalWorld], seed=230001, options=[options, options])
    gates = [loc for loc in mw.get_locations(1)
             if loc.address is not None and loc.name.endswith(" - Slayer Gate Complete")]
    filler = Item("Foreign filler", ItemClassification.filler, 1, 2)
    restricted = [loc for loc in gates if not loc.item_rule(filler)]
    assert len(gates) == 6
    assert len(restricted) == 5
    fill(mw)
    useful = ItemClassification.progression | ItemClassification.useful
    assert all(loc.item.classification & useful for loc in restricted)


def test_multiworld_spheres_deliver_foreign_items_to_their_player():
    mw = setup_multiworld([DoomEternalWorld, DoomEternalWorld], seed=230001,
                            options=[{**PRESETS[0]["options"], "killsanity": True,
                                      "killsanity_maximum_milestones": 50,
                                      "accessibility": "full"}, PRESETS[1]["options"]])
    before = item_counts(physical_items(mw))
    fill(mw)
    assert any(location.item.player != location.player for location in mw.get_filled_locations())
    state = walk_spheres(mw)
    assert all(mw.has_beaten_game(state, player) for player in mw.player_ids)
    assert filled_item_counts(mw) == before


@pytest.mark.parametrize("options", [
    {**PRESETS[2]["options"], "goal": "acquire_the_unmaykr"},
    {**PRESETS[0]["options"], "goal": "complete_n_master_levels"},
    {**PRESETS[1]["options"], "custom_missions": ["Hell on Earth"]},
])
def test_invalid_campaign_options_refuse_generation(options):
    with pytest.raises(OptionError):
        setup_multiworld(DoomEternalWorld, seed=230001, options=options)
