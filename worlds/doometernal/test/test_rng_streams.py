import unittest

from test.general import gen_steps, setup_multiworld
from worlds.AutoWorld import call_all
from worlds.doometernal import DoomEternalWorld


class TestRngStreams(unittest.TestCase):
    options = {"mission_pool": "base", "mission_count": 6,
               "mission_order": "mission_access_as_items", "starting_weapon": "random"}

    def generation_result(self, mw, player=1):
        world = mw.worlds[player]
        progression = [item for item in mw.itempool if item.player == player and item.advancement]
        world.fill_hook(progression, [], [], mw.get_unfilled_locations(player))
        return {
            "campaign_plan": world.campaign_plan,
            "enemy_plan": world.enemy_plan,
            "items": [(item.name, item.classification) for item in mw.itempool if item.player == player],
            "placements": sorted((loc.name, loc.item.name, loc.item.player)
                                 for loc in mw.get_filled_locations(player)),
            "precollected": [item.name for item in mw.precollected_items[player]],
            "frontloaded": world.frontloaded_arsenal,
            "priority": [item.name for item in progression],
        }

    def test_same_seed_replays_generation(self):
        for options in (self.options, {**self.options, "mission_order": "random_mission_order",
                                       "enemy_preset": "cultist_chaos"}):
            with self.subTest(options=options):
                expected = setup_multiworld(DoomEternalWorld, seed=42, options=options)
                replay = setup_multiworld(DoomEternalWorld, seed=42, options=options)
                self.assertEqual(self.generation_result(replay), self.generation_result(expected))

    def test_filler_randomness_does_not_change_campaign_or_enemy_seed(self):
        expected = setup_multiworld(DoomEternalWorld, seed=42, options=self.options)
        changed = setup_multiworld(DoomEternalWorld, steps=(), seed=42, options=self.options)
        changed.worlds[1].item_pool_rng.randbytes(4096)
        for step in gen_steps:
            call_all(changed, step)
        expected_result = self.generation_result(expected)
        changed_result = self.generation_result(changed)
        self.assertNotEqual(changed_result["items"], expected_result["items"])
        for name in ("campaign_plan", "enemy_plan"):
            self.assertEqual(changed_result[name], expected_result[name])
        self.assertIsNotNone(expected_result["enemy_plan"])
        self.assertEqual(changed_result["placements"], expected_result["placements"])
        self.assertEqual([name for name in changed_result["priority"] if name.endswith(" Access")],
                         [name for name in expected_result["priority"] if name.endswith(" Access")])

    def test_other_slot_generation_does_not_change_this_slot_plan(self):
        worlds = [DoomEternalWorld, DoomEternalWorld]
        expected = setup_multiworld(worlds, steps=(), seed=42, options=self.options)
        changed = setup_multiworld(worlds, steps=(), seed=42, options=self.options)
        for step in gen_steps:
            getattr(expected.worlds[1], step)()
        for step in gen_steps:
            getattr(changed.worlds[2], step)()
        changed.worlds[2].fill_hook([], [], [], changed.get_unfilled_locations(2))
        for step in gen_steps:
            getattr(changed.worlds[1], step)()
        self.assertEqual(self.generation_result(changed), self.generation_result(expected))
