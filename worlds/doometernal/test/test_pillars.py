import json
from collections import Counter
from pathlib import Path

import pytest
from BaseClasses import CollectionState
from Options import OptionError
from test.general import gen_steps, setup_multiworld
from worlds.AutoWorld import call_all
from worlds.doometernal import DoomEternalWorld

from .generation_support import (
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
    ("randomized_enemies", 230001, {**PRESETS[0]["options"], "enemy_randomizer": True}),
    ("starting_inventory", 230001, {**PRESETS[0]["options"], "start_inventory": {"Ballista": 1},
                            "start_inventory_from_pool": {"Heavy Cannon": 1}}),
]


def walk_spheres(mw):
    state = CollectionState(mw)
    checked = set()
    for sphere in mw.get_spheres():
        assert sphere and all(location.can_reach(state) for location in sphere)
        assert checked.isdisjoint(sphere)
        collect_sphere_items(state, sphere)
        checked.update(sphere)
    assert checked == set(mw.get_filled_locations())
    return state


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


def test_multiworld_spheres_deliver_foreign_items_to_their_player():
    mw = setup_multiworld([DoomEternalWorld, DoomEternalWorld], seed=230001,
                          options=[PRESETS[0]["options"], PRESETS[1]["options"]])
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
