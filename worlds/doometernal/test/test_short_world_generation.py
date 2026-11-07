import unittest

from Fill import distribute_items_restrictive

from test.general import setup_multiworld
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.campaign import (
    BASE_GATE_STAGE_IDS,
    STAGE_BY_ID,
)
from worlds.doometernal.planner import STAGE_SLAYER_GATE_KEYS


class TestShortWorldGeneration(unittest.TestCase):
    def test_compact_campaign_battery_surplus_fits_budget(self):
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=1,
            options={
                "enemy_randomizer": False,
                "mission_order": "vanilla_order",
                "starting_weapon": "ballista",
                "include_weapon_mastery_challenges": False,
                "goal": "kill_the_icon_of_sin",
                "custom_dark_lord": False,
                "mission_pool": "custom",
                "custom_missions": {
                    "Final Sin",
                    "The World Spear",
                    "Reclaimed Earth",
                    "Immora",
                    "The Blood Swamps",
                    "Sentinel Prime",
                },
            },
        )
        distribute_items_restrictive(mw)
        self.assertTrue(mw.can_beat_game())

    def test_unmaykr_goal_is_beatable_and_gate_keys_are_required(self):
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "base",
                "mission_count": 6,
                "goal": "acquire_the_unmaykr",
                "enemy_randomizer": False,
            },
        )
        distribute_items_restrictive(mw)
        self.assertTrue(mw.can_beat_game())
        for gate_stage in BASE_GATE_STAGE_IDS:
            state = mw.get_all_state()
            location = mw.get_location(STAGE_BY_ID[gate_stage]["name"] + " - Slayer Gate Complete", 1)
            self.assertTrue(location.can_reach(state))
            state.set_item(STAGE_SLAYER_GATE_KEYS[gate_stage], 1, 0)
            self.assertFalse(location.can_reach(state))

    def test_goal_acquire_unmaykr_rejects_dlc_only(self) -> None:
        with self.assertRaises(ValueError):
            setup_multiworld(
                DoomEternalWorld,
                seed=42,
                options={
                    "mission_pool": "dlc_only",
                    "goal": "acquire_the_unmaykr",
                },
            )

    def test_custom_pool_requires_at_least_6_missions(self) -> None:
        with self.assertRaises(ValueError):
            setup_multiworld(
                DoomEternalWorld,
                seed=42,
                options={
                    "mission_pool": "custom",
                    "custom_missions": {"e1m1_intro", "e1m2_war", "e1m3_cult", "e1m4_boss", "e2m1_nest"},
                    "custom_dark_lord": 0,
                    "goal": "kill_the_icon_of_sin",
                },
            )


if __name__ == "__main__":
    unittest.main()
