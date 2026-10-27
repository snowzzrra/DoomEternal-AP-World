import json
import unittest
from collections import Counter

from BaseClasses import CollectionState
from Options import OptionError
from test.general import gen_steps, setup_multiworld
from worlds.AutoWorld import call_all
from worlds.doometernal import DoomEternalWorld


class TestTracker(unittest.TestCase):
    def test_room_reconstruction_preserves_locations_and_logic(self):
        cases = (
            {"mission_pool": "full_saga", "mission_order": "random_mission_order",
             "mission_count": "all", "killsanity": True, "kills_per_check": 25,
             "start_inventory": {"Flame Belch": 1}, "starting_weapon": "random",
             "randomize_chainsaw": True, "randomize_dash": True},
            {"mission_pool": "base", "mission_count": 6, "mission_order": "mission_access_as_items",
             "starting_missions": 2, "goal": "kill_the_icon_of_sin", "logic_difficulty": "expert",
             "mastery_requirements": "quarter", "resource_profile": "generous"},
            {"mission_pool": "dlc_only", "mission_count": 6, "mission_order": "vanilla_order",
             "goal": "kill_the_dark_lord", "enemy_randomizer": False,
             "include_secret_encounters": False, "include_weapon_mastery_challenges": False},
        )
        for options in cases:
            with self.subTest(options=options):
                original = setup_multiworld(DoomEternalWorld, steps=gen_steps[:-1], seed=42, options=options)
                world = original.worlds[1]
                encoded = json.dumps(world.fill_slot_data())
                self.assertLess(len(encoded.encode()), 1024 * 1024)
                slot_data = json.loads(encoded)
                tracker = setup_multiworld(DoomEternalWorld, steps=(), seed=9876)
                tracker.generation_is_fake = True
                tracker.re_gen_passthrough = {world.game: DoomEternalWorld.interpret_slot_data(slot_data)}
                for step in gen_steps[:-1]:
                    call_all(tracker, step)
                restored = tracker.worlds[1]
                self.assertEqual(restored.campaign_plan, slot_data["campaign_plan"])
                self.assertEqual(restored.enemy_plan, world.enemy_plan)
                self.assertEqual(restored.killsanity_plan, world.killsanity_plan)
                self.assertEqual(restored._mission_presentation(), world._mission_presentation())
                self.assertEqual({(loc.name, loc.address) for loc in tracker.get_locations(1)},
                                 {(loc.name, loc.address) for loc in original.get_locations(1)})
                items = [item for item in original.itempool if item.advancement]
                reachable = []
                for inventory in ([], items[:20], items):
                    states = [CollectionState(mw) for mw in (original, tracker)]
                    for mw, state in zip((original, tracker), states):
                        for name, quantity in options.get("start_inventory", {}).items():
                            for _ in range(quantity):
                                state.collect(mw.worlds[1].create_item(name), True)
                        for item in inventory:
                            copy = mw.worlds[1].create_item(item.name)
                            copy.classification = item.classification
                            state.collect(copy, True)
                        state.sweep_for_advancements(locations=[loc for loc in mw.get_locations(1)
                                                               if loc.address is None])
                    actual = [{loc.name for loc in mw.get_reachable_locations(state, 1)}
                              for mw, state in zip((original, tracker), states)]
                    self.assertEqual(*actual)
                    reachable.append(actual[0])
                self.assertGreater(len(reachable[-1]), len(reachable[0]))
                self.assertEqual(Counter(item.name for item in original.precollected_items[1]),
                                 Counter(item.name for item in tracker.precollected_items[1]))
                self.assertEqual(json.loads(encoded), slot_data)

    def test_room_without_tracker_options_fails_explicitly(self):
        world = setup_multiworld(DoomEternalWorld, steps=(), seed=42).worlds[1]
        from worlds.doometernal.version import SLOT_DATA_REVISION
        with self.assertRaisesRegex(OptionError, "tracker options"):
            world._restore_tracker_slot({"slot_data_revision": SLOT_DATA_REVISION})
