import json
import unittest

from Fill import distribute_items_restrictive
from Options import OptionError
from test.general import gen_steps, setup_multiworld
from worlds.AutoWorld import call_all
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.enemy_options import SPECIES_IDS


class TestEnemyOptionErrors(unittest.TestCase):
    def test_too_many_kill_rewards_reports_option_error(self):
        from worlds.doometernal.options import KillsanityMaximumMilestones

        self.assertEqual(KillsanityMaximumMilestones(2000).value, 2000)
        with self.assertRaisesRegex(OptionError, "1..2000"):
            setup_multiworld(DoomEternalWorld, steps=(), options={"killsanity_maximum_milestones": 2001})

    def assert_option_error(self, options, message):
        world = setup_multiworld(DoomEternalWorld, steps=(), seed=42, options=options).worlds[1]
        with self.assertRaisesRegex(OptionError, message) as raised:
            world.generate_early()
        self.assertIsInstance(raised.exception.__cause__, ValueError)
        self.assertEqual(str(raised.exception), str(raised.exception.__cause__))

    def test_inverted_enemy_health_reports_option_error(self):
        self.assert_option_error(
            {"enemy_health": {"minimum": 200, "maximum": 100}},
            "enemy_health.global minimum exceeds maximum",
        )

    def test_zero_eligible_enemy_weights_reports_option_error(self):
        for dlc_weight in (0, 100):
            with self.subTest(dlc_weight=dlc_weight):
                self.assert_option_error(
                    {"use_dlc_content": False,
                     "enemy_weights": {**dict.fromkeys(SPECIES_IDS, 0), "spirit": dlc_weight}},
                    "Enemy Weights exclude every eligible random combat species",
                )

    def test_valid_enemy_options_preserve_slot_data(self):
        mw = setup_multiworld(DoomEternalWorld, seed=42, options={
            "mission_pool": "base", "mission_count": 6,
            "enemy_health": {"minimum": 75, "maximum": 125},
            "enemy_weights": {"imp": 200},
        })
        distribute_items_restrictive(mw)
        original = mw.worlds[1]
        slot_data = json.loads(json.dumps(original.fill_slot_data()))
        tracker = setup_multiworld(DoomEternalWorld, steps=(), seed=9876)
        tracker.generation_is_fake = True
        tracker.re_gen_passthrough = {original.game: DoomEternalWorld.interpret_slot_data(slot_data)}
        for step in gen_steps[:-1]:
            call_all(tracker, step)
        restored = tracker.worlds[1]
        restored_data = restored.fill_slot_data()
        self.assertEqual(restored_data, slot_data)
        self.assertEqual(restored_data["tracker_options"]["enemy_health"], {"minimum": 75, "maximum": 125})
        self.assertEqual(restored_data["tracker_options"]["enemy_weights"], {"imp": 200})
        self.assertTrue(restored_data["recipes"]["enabled"])
        profiles = restored_data["recipes"]["profiles"]
        self.assertTrue(profiles)
        self.assertTrue(all(75 <= profile[1] <= 125 for profile in profiles))
        self.assertTrue(any(profile[0] == "imp" for profile in profiles))
