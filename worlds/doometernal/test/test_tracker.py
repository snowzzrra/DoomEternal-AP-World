import json
import unittest
from collections import Counter
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from BaseClasses import CollectionState
from Options import OptionError
from test.general import gen_steps, setup_multiworld
from worlds.AutoWorld import call_all
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.slot_data import build_slot_data
from worlds.doometernal.slot_data_contract import ContractError, generation_fingerprint
from .test_starting_inventory import core_args


class TestTracker(unittest.TestCase):
    def test_room_without_resolved_data_fails_explicitly(self):
        world = setup_multiworld(DoomEternalWorld, steps=(), seed=42).worlds[1]
        with self.assertRaises(OptionError) as raised:
            world._restore_tracker_slot({"tracker_options": {}})
        self.assertIsInstance(raised.exception.__cause__, ContractError)


RESOLVED_CASES = [
    {"mission_pool": "full_saga", "mission_count": "all", "mission_order": "random_mission_order",
     "killsanity": True, "kills_per_check": 1000, "killsanity_maximum_milestones": 12,
     "randomize_chainsaw": True, "randomize_dash": True},
    {"mission_pool": "base", "mission_count": 6, "mission_order": "mission_access_as_items",
     "starting_missions": 2, "goal": "kill_the_icon_of_sin", "logic_difficulty": "expert",
     "start_inventory": {"Flame Belch": 1, "Progressive Health Upgrade": 1, "Progressive Blood Punch": 1},
     "start_inventory_from_pool": {"Progressive Ammo Upgrade": 2, "Progressive Blood Punch": 1}},
    {"mission_pool": "dlc_only", "mission_count": 6, "mission_order": "vanilla_order",
     "goal": "kill_the_dark_lord", "enemy_randomizer": False,
     "include_secret_encounters": False, "include_weapon_mastery_challenges": False},
    {"mission_pool": "custom", "mission_count": 6, "goal": "kill_the_icon_of_sin",
     "custom_missions": {"Cultist Base", "Doom Hunter Base", "Super Gore Nest", "ARC Complex", "Mars Core", "Taras Nabad"},
     "mission_order": "vanilla_order", "campaign_difficulty": "nightmare", "logic_difficulty": "expert",
     "starting_weapon": "heavy_cannon", "randomize_dash": True, "randomize_chainsaw": True},
    {"mission_pool": "full_saga", "mission_order": "random_mission_order",
     "mission_count": "all", "killsanity": True, "kills_per_check": 25,
     "start_inventory": {"Flame Belch": 1}, "starting_weapon": "random",
     "randomize_chainsaw": True, "randomize_dash": True},
    {"mission_pool": "base", "mission_count": 6, "mission_order": "mission_access_as_items",
     "starting_missions": 2, "goal": "kill_the_icon_of_sin", "logic_difficulty": "expert",
     "mastery_requirements": "quarter", "resource_profile": "generous"},
]


def reconstruct_resolved(slot_data, seed):
    tracker = setup_multiworld(DoomEternalWorld, steps=(), seed=seed)
    tracker.generation_is_fake = True
    tracker.re_gen_passthrough = {DoomEternalWorld.game: DoomEternalWorld.interpret_slot_data(slot_data)}
    world = tracker.worlds[1]
    for code, count in slot_data["starting"]["items"]:
        for _ in range(2 * count):
            tracker.push_precollected(world.create_item(world.item_id_to_name[code]))
    streams = (world.random, world.campaign_rng, world.enemy_rng, world.item_pool_rng,
               world.placement_rng, world.access_priority_rng, tracker.random)
    before = [rng.getstate() for rng in streams]
    with ExitStack() as stack:
        for target in ("worlds.doometernal.make_plan", "worlds.doometernal.build_native_recipes",
                       "worlds.doometernal.normalize_enemy_options", "random.Random.random", "random.Random.getrandbits"):
            stack.enter_context(patch(target, side_effect=AssertionError("Tracker recomputed room decisions")))
        for step in gen_steps:
            call_all(tracker, step)
        world.create_items()
    assert before == [rng.getstate() for rng in streams]
    assert not tracker.itempool
    assert world.fill_slot_data() == slot_data
    return tracker


def assert_reconstructed_graph(original, tracker):
    assert {(loc.name, loc.address) for loc in original.get_locations(1)} == {
        (loc.name, loc.address) for loc in tracker.get_locations(1)}
    assert entrance_edges(original) == entrance_edges(tracker)
    assert indirect_edges(original) == indirect_edges(tracker)
    assert Counter(item.name for item in original.precollected_items[1]) == Counter(
        item.name for item in tracker.precollected_items[1])


def entrance_edges(mw):
    return {(region.name, edge.name, edge.connected_region.name)
            for region in mw.get_regions(1) for edge in region.exits}


def indirect_edges(mw):
    return {(region.name, entrance.name) for region, entrances in mw.indirect_connections.items()
            for entrance in entrances}


def reachable_with_inventory(mw, items):
    state = CollectionState(mw)
    for item in items:
        copy = mw.worlds[1].create_item(item.name)
        copy.classification = item.classification
        state.collect(copy, True)
    state.sweep_for_advancements(locations=[loc for loc in mw.get_locations(1) if loc.address is None])
    return {loc.name for loc in mw.get_reachable_locations(state, 1)}, state.prog_items[1].copy()


@pytest.mark.parametrize("options", RESOLVED_CASES)
def test_resolved_room_reconstruction_preserves_reachability(options):
    from Main import main

    original = main(core_args(options), seed=429261552, baked_server_options={"test": True})
    world = original.worlds[1]
    slot_data = json.loads(json.dumps(build_slot_data(world)))
    assert_resolved_campaign(world, slot_data)
    items = [loc.item for loc in original.get_filled_locations(1) if loc.address is not None]
    inventories = ([], items[:len(items) // 2], items)
    expected = [reachable_with_inventory(original, inventory) for inventory in inventories]
    assert len(expected[-1][0]) > len(expected[0][0])
    for seed in (9876, 123):
        tracker = reconstruct_resolved(slot_data, seed)
        assert_reconstructed_graph(original, tracker)
        assert expected == [reachable_with_inventory(tracker, inventory) for inventory in inventories]


def assert_resolved_campaign(world, slot_data):
    plan, campaign = world.campaign_plan, slot_data["campaign"]
    assert campaign["unprepared_start_stages"] == sorted(plan.get("unprepared_start_stages", []))
    assert campaign["opening_stage"] == plan.get("opening_stage")
    assert campaign["goal_as_item"] == plan["goal_as_item"]
    assert campaign["active_masteries_count"] == plan["active_masteries_count"]


def test_resolved_tracker_rejects_changed_room_before_restoring_options():
    from Main import main

    original = main(core_args(RESOLVED_CASES[2]), seed=42, baked_server_options={"test": True}).worlds[1]
    slot_data = build_slot_data(original)
    tracker = setup_multiworld(DoomEternalWorld, steps=(), seed=9876).worlds[1]
    before = tracker.options.as_dict(*DoomEternalWorld.options_dataclass.__annotations__)
    slot_data["campaign"]["active_masteries_count"] += 1
    with pytest.raises(OptionError, match="digest mismatch"):
        tracker._restore_tracker_slot(slot_data)
    assert tracker.options.as_dict(*DoomEternalWorld.options_dataclass.__annotations__) == before
    slot_data["native_generation_fingerprint"] = generation_fingerprint(slot_data)
    slot_data["killsanity"]["count"] = 2001
    with pytest.raises(OptionError, match="integer in range"):
        tracker._restore_tracker_slot(slot_data)
