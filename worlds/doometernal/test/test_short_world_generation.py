import unittest
from test.general import gen_steps, setup_multiworld
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.campaign import (
    BASE_GATE_STAGE_IDS,
    CAMPAIGN_STAGES,
    STAGE_BY_ID,
)
from worlds.doometernal.items import suit_perk_item_names
from worlds.doometernal.planner import STAGE_SLAYER_GATE_KEYS


class TestShortWorldGeneration(unittest.TestCase):
    """Generation and cardinality checks for supported short campaigns."""


    def test_full_saga_baseline(self) -> None:
        """Full Saga exports the selected missions, resources and active checks."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "full_saga",
                "mission_count": "all",
                "enemy_randomizer": False,
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        unfilled = [loc for loc in mw.get_locations(1) if not loc.item]

        self.assertEqual(len(unfilled), len(mw.itempool))

        plan = world.campaign_plan
        self.assertEqual(len(plan["active_normal_mission_ids"]), 19)
        self.assertTrue(plan["dark_lord_active"])

        item_names = [item.name for item in mw.itempool]
        self.assertEqual(item_names.count("Weapon Upgrade Points (3)"), 39)
        self.assertEqual(item_names.count("Sentinel Battery"), 28)
        praetor_count = sum(item_names.count(p) for p in suit_perk_item_names)
        self.assertEqual(praetor_count, 17)

        mastery_locs = [loc for loc in unfilled if loc.parent_region.name == "Weapon Masteries"]
        self.assertEqual(len(mastery_locs), 13)

        hub_locs = [loc for loc in unfilled if "Fortress of Doom" in loc.parent_region.name]
        self.assertEqual(len(hub_locs), 20)  # 6 non-consumer + 13 consumer + Unmaykr (13 consumers + 7 other)

        gate_keys = [name for name in item_names if "Slayer Gate Key" in name]
        self.assertEqual(len(gate_keys), 8)

        slot_data = world.fill_slot_data()
        self.assertEqual(slot_data["mission_pool"], "full_saga")
        self.assertTrue(slot_data["dark_lord_enabled"])
        self.assertEqual(slot_data["effective_mission_count"], 19)
        self.assertEqual(slot_data["active_location_count"], len(unfilled))


    def test_base_campaign_mission_count_6(self) -> None:
        """Base campaign with the smallest supported mission count."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=100,
            options={
                "mission_pool": "base",
                "mission_count": 6,
                "mission_order": "random_mission_order",
                "goal": "kill_the_icon_of_sin",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        unfilled = [loc for loc in mw.get_locations(1) if not loc.item]

        self.assertEqual(len(unfilled), len(mw.itempool))
        plan = world.campaign_plan
        self.assertEqual(len(plan["active_normal_mission_ids"]), 6)
        self.assertFalse(plan["dark_lord_active"])
        self.assertIn("e3m4_boss", plan["active_normal_mission_ids"])
        self.assertGreaterEqual(len(unfilled), 30)


    def test_dlc_only_count_6(self) -> None:
        """Six DLC missions fit all upgrades with optional checks disabled."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=77,
            options={
                "mission_pool": "dlc_only",
                "mission_count": 6,
                "mission_order": "random_mission_order",
                "goal": "kill_the_dark_lord",
                "include_slayer_gates": False,
                "include_secret_encounters": False,
                "include_weapon_mastery_challenges": False,
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        unfilled = [loc for loc in mw.get_locations(1) if not loc.item]

        self.assertEqual(len(unfilled), len(mw.itempool))
        plan = world.campaign_plan
        self.assertEqual(len(plan["active_normal_mission_ids"]), 6)
        self.assertTrue(plan["dark_lord_active"])
        from worlds.doometernal.combat_rating import NORMAL_RUNE_NAMES, SUPPORT_RUNE_NAMES
        counts = [item.name for item in mw.itempool + mw.precollected_items[1]] + [
            loc.item.name for loc in mw.get_filled_locations(1) if loc.address is not None]
        for name in NORMAL_RUNE_NAMES | SUPPORT_RUNE_NAMES | set(suit_perk_item_names):
            self.assertEqual(counts.count(name), 1, name)
        for stat in ('Health', 'Armor', 'Ammo'):
            self.assertEqual(counts.count(f'Progressive {stat} Upgrade'), 4)


    def test_goal_acquire_unmaykr_forces_6_gates_and_count_ge_6(self) -> None:
        """Goal Acquire the Unmaykr forces 6 Base Slayer Gates and clamps count >= 6."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "base",
                "mission_count": 6,
                "goal": "acquire_the_unmaykr",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        plan = world.campaign_plan
        self.assertGreaterEqual(len(plan["active_normal_mission_ids"]), 6)
        for gate_stage in BASE_GATE_STAGE_IDS:
            self.assertIn(gate_stage, plan["active_normal_mission_ids"])
            key = STAGE_SLAYER_GATE_KEYS[gate_stage]
            owned = [item.name for item in mw.itempool + mw.precollected_items[1]]
            self.assertEqual(owned.count(key), 1)
            names = {location.name for location in mw.get_locations(1)}
            prefix = STAGE_BY_ID[gate_stage]["name"]
            self.assertTrue(any(name.startswith(prefix + " - Slayer Key -") for name in names))
            self.assertIn(prefix + " - Slayer Gate Complete", names)

    def test_goal_acquire_unmaykr_rejects_dlc_only(self) -> None:
        """Goal Acquire the Unmaykr cannot be generated with DLC Only pool."""
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
        """An undersized custom pool must fail before generation."""
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




    def test_start_inventory_preserves_cardinality_and_reserves_items(self) -> None:
        """Items in start_inventory are reserved into quotas without increasing pool cardinality."""
        mw = setup_multiworld(
            DoomEternalWorld,
            steps=gen_steps[:-1],
            seed=42,
            options={
                "mission_pool": "custom",
                "custom_missions": {"e1m1_intro", "e1m2_war", "e1m3_cult", "e3m4_boss", "e5m1_spear", "e5m2_earth"},
                "custom_dark_lord": 0,
                "mission_count": 6,
                "mission_order": "random_mission_order",
                "goal": "kill_the_icon_of_sin",
                "start_inventory": {
                    "Lock-on Burst": 1,
                    "Sentinel Battery": 2,
                },
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        for name, quantity in world.options.start_inventory.value.items():
            for _ in range(quantity):
                mw.push_precollected(world.create_item(name))
        world.pre_fill()
        unfilled = [loc for loc in mw.get_unfilled_locations(1) if loc.address is not None]
        start_inv = world.effective_starting_inventory()
        self.assertEqual(start_inv["Lock-on Burst"], 1)
        self.assertEqual(start_inv["Sentinel Battery"], 2)
        self.assertEqual(len(mw.itempool), len(unfilled))

    def test_mai_access_cardinality_goal_mission_as_item_toggle(self) -> None:
        """Goal Mission as Item toggles whether the final goal stage generates an Access item."""
        mw_on = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "custom",
                "custom_missions": {"e1m1_intro", "e1m2_war", "e1m3_cult", "e3m4_boss", "e5m1_spear", "e5m2_earth"},
                "custom_dark_lord": 0,
                "mission_count": 6,
                "mission_order": "mission_access_as_items",
                "starting_missions": 1,
                "goal": "kill_the_icon_of_sin",
                "goal_mission_as_item": 1,
            },
        )
        item_names_on = [item.name for item in mw_on.itempool]
        access_on = [name for name in item_names_on if " Access" in name]
        self.assertEqual(len(access_on), 5)
        self.assertIn("Final Sin Access", access_on)

        mw_off = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "custom",
                "custom_missions": {"e1m1_intro", "e1m2_war", "e1m3_cult", "e3m4_boss", "e5m1_spear", "e5m2_earth"},
                "custom_dark_lord": 0,
                "mission_count": 6,
                "mission_order": "mission_access_as_items",
                "starting_missions": 1,
                "goal": "kill_the_icon_of_sin",
                "goal_mission_as_item": 0,
            },
        )
        item_names_off = [item.name for item in mw_off.itempool]
        access_off = [name for name in item_names_off if " Access" in name]
        self.assertEqual(len(access_off), 4)
        self.assertNotIn("Final Sin Access", access_off)

    def test_complete_all_included_missions_victory_semantics(self) -> None:
        """Complete All Included Missions requires clearances for all active missions."""
        from BaseClasses import CollectionState, ItemClassification
        from worlds.doometernal.items import DoomEternalItem
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "custom",
                "custom_missions": {"e1m1_intro", "e1m2_war", "e1m3_cult", "e3m4_boss", "e5m1_spear", "e5m2_earth"},
                "custom_dark_lord": 1,
                "mission_count": 6,
                "mission_order": "random_mission_order",
                "goal": "kill_the_icon_of_sin",
                "additional_victory_requirements": {"Complete All Included Missions"},
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        condition = mw.completion_condition[1]

        state = CollectionState(mw)
        self.assertFalse(condition(state))

        state.collect(DoomEternalItem("Internal Goal Endpoint: Kill the Icon of Sin", ItemClassification.progression, None, 1))
        self.assertFalse(condition(state))

        state.collect(DoomEternalItem("Internal Mission Clear: The World Spear", ItemClassification.progression, None, 1))
        state.collect(DoomEternalItem("Internal Mission Clear: Reclaimed Earth", ItemClassification.progression, None, 1))
        self.assertFalse(condition(state))

        state.collect(DoomEternalItem("Internal Mission Clear: Final Sin", ItemClassification.progression, None, 1))
        self.assertFalse(condition(state))  # Dark Lord still active and required!

        for name in ("Hell on Earth", "Exultia", "Cultist Base"):
            state.collect(DoomEternalItem("Internal Mission Clear: " + name, ItemClassification.progression, None, 1))

        state.collect(DoomEternalItem("Internal Goal Endpoint: Kill the Dark Lord", ItemClassification.progression, None, 1))
        self.assertTrue(condition(state))


if __name__ == "__main__":
    unittest.main()
