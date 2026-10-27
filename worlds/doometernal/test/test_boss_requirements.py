import unittest

from test.general import setup_multiworld
from worlds.doometernal import DoomEternalWorld


class TestBossRequirements(unittest.TestCase):
    def test_boss_completion_requires_its_tools_even_with_a_full_loadout(self):
        for order in ("random_mission_order", "mission_access_as_items"):
            with self.subTest(order=order):
                multiworld = setup_multiworld(DoomEternalWorld, seed=20261025, options={
                    "mission_pool": "full_saga", "mission_order": order,
                    "randomize_dash": True, "enemy_randomizer": False,
                })
                for location_name, required in (
                    ("Urdak - Mission Complete", ("Blood Punch", "Dash")),
                    ("The Holt - Mission Complete", ("Plasma Rifle", "Microwave Beam")),
                ):
                    location = multiworld.get_location(location_name, 1)
                    for missing in required:
                        with self.subTest(location=location_name, missing=missing):
                            state = multiworld.get_all_state()
                            self.assertTrue(location.can_reach(state))
                            state.prog_items[1][missing] = 0
                            state.stale[1] = True
                            self.assertFalse(location.can_reach(state))
                            state.prog_items[1][missing] = 1
                            state.stale[1] = True
                            self.assertTrue(location.can_reach(state))
