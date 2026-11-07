import unittest

from Options import OptionError
from test.general import setup_multiworld
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.enemy_options import SPECIES_IDS


class TestEnemyOptionErrors(unittest.TestCase):
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
