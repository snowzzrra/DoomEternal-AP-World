import unittest
from test.general import setup_multiworld
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.campaign import (
    BASE_GATE_STAGE_IDS,
    CAMPAIGN_STAGES,
    STAGE_BY_ID,
)
from worlds.doometernal.items import suit_perk_item_names


class TestShortWorldGeneration(unittest.TestCase):
    """Systematic generation and cardinality test suite for P7.3 short worlds."""

    # -------------------------------------------------------------------------
    # 1. Full Saga Baseline
    # -------------------------------------------------------------------------
    def test_full_saga_baseline(self) -> None:
        """Full Saga default options must match canonical baseline exactly."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "full_saga",
                "mission_count": "all",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        unfilled = [loc for loc in mw.get_locations(1) if not loc.item]

        # 439 enabled locations, 439 items in itempool
        self.assertEqual(len(unfilled), 439)
        self.assertEqual(len(mw.itempool), 439)

        # Plan inspection
        plan = world.campaign_plan
        self.assertEqual(len(plan["active_normal_mission_ids"]), 19)
        self.assertTrue(plan["dark_lord_active"])

        # Economy inspection
        item_names = [item.name for item in mw.itempool]
        self.assertEqual(item_names.count("Weapon Upgrade Points (3)"), 39)
        self.assertEqual(item_names.count("Sentinel Battery Bundle"), 13)  # 12 spend groups + 1 surplus bundle (value 26)
        self.assertEqual(item_names.count("Sentinel Battery"), 0)
        praetor_count = sum(item_names.count(p) for p in suit_perk_item_names)
        self.assertEqual(praetor_count, 21)

        # 13 mastery locations
        mastery_locs = [loc for loc in unfilled if loc.parent_region.name == "Weapon Masteries"]
        self.assertEqual(len(mastery_locs), 13)

        # 13 Fortress consumer checks unlocked from 12 spend groups
        hub_locs = [loc for loc in unfilled if "Fortress of Doom" in loc.parent_region.name]
        self.assertEqual(len(hub_locs), 20)  # 6 non-consumer + 13 consumer + Unmaykr (13 consumers + 7 other)

        # Gate keys: 8 (6 Base + 2 TAG1)
        gate_keys = [name for name in item_names if "Slayer Gate Key" in name]
        self.assertEqual(len(gate_keys), 8)

        # Slot data verification
        slot_data = world.fill_slot_data()
        self.assertEqual(slot_data["mission_pool"], "full_saga")
        self.assertTrue(slot_data["dark_lord_enabled"])
        self.assertEqual(slot_data["effective_mission_count"], 19)
        self.assertEqual(slot_data["active_location_count"], 439)

    # -------------------------------------------------------------------------
    # 2. Base Campaign Presets
    # -------------------------------------------------------------------------
    def test_base_campaign_all(self) -> None:
        """Base campaign with all 13 missions."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "base",
                "mission_count": "all",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        unfilled = [loc for loc in mw.get_locations(1) if not loc.item]

        # 439 - 67 DLC locations = 372
        self.assertEqual(len(unfilled), 372)
        self.assertEqual(len(mw.itempool), 372)

        plan = world.campaign_plan
        self.assertEqual(len(plan["active_normal_mission_ids"]), 13)
        self.assertFalse(plan["dark_lord_active"])

        item_names = [item.name for item in mw.itempool]
        self.assertEqual(item_names.count("Weapon Upgrade Points (3)"), 39)
        self.assertEqual(item_names.count("Sentinel Battery Bundle"), 13)
        self.assertEqual(item_names.count("Sentinel Battery"), 0)

        gate_keys = [name for name in item_names if "Slayer Gate Key" in name]
        self.assertEqual(len(gate_keys), 6)  # Exactly 6 Base keys, no TAG keys

    def test_base_campaign_mission_count_3(self) -> None:
        """Base campaign scaled to 3 missions with Kill the Icon of Sin."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=100,
            options={
                "mission_pool": "base",
                "mission_count": 3,
                "mission_order": "random_mission_order",
                "goal": "kill_the_icon_of_sin",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        unfilled = [loc for loc in mw.get_locations(1) if not loc.item]

        self.assertEqual(len(unfilled), len(mw.itempool))
        plan = world.campaign_plan
        self.assertEqual(len(plan["active_normal_mission_ids"]), 3)
        self.assertFalse(plan["dark_lord_active"])
        self.assertIn("e3m4_boss", plan["active_normal_mission_ids"])
        self.assertGreaterEqual(len(unfilled), 30)

    # -------------------------------------------------------------------------
    # 3. DLC Only Presets
    # -------------------------------------------------------------------------
    def test_dlc_only_all(self) -> None:
        """DLC Only with all 6 missions + Dark Lord."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "dlc_only",
                "mission_count": "all",
                "goal": "kill_the_dark_lord",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        unfilled = [loc for loc in mw.get_locations(1) if not loc.item]

        self.assertEqual(len(unfilled), len(mw.itempool))
        plan = world.campaign_plan
        self.assertEqual(len(plan["active_normal_mission_ids"]), 6)
        self.assertTrue(plan["dark_lord_active"])

        # 6 DLC stages + Dark Lord: Gate keys for Atlantica & Holt only (2 keys)
        item_names = [item.name for item in mw.itempool]
        gate_keys = [name for name in item_names if "Slayer Gate Key" in name]
        self.assertEqual(len(gate_keys), 2)

    def test_dlc_only_count_3(self) -> None:
        """DLC Only with 3 missions + Dark Lord."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=77,
            options={
                "mission_pool": "dlc_only",
                "mission_count": 3,
                "mission_order": "random_mission_order",
                "goal": "kill_the_dark_lord",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        unfilled = [loc for loc in mw.get_locations(1) if not loc.item]

        self.assertEqual(len(unfilled), len(mw.itempool))
        plan = world.campaign_plan
        self.assertEqual(len(plan["active_normal_mission_ids"]), 3)
        self.assertTrue(plan["dark_lord_active"])

    # -------------------------------------------------------------------------
    # 4. Custom Pool & Extreme 3-Mission Outliers
    # -------------------------------------------------------------------------
    def test_extreme_3_mission_outlier_final_sin_spear_earth_rmo(self) -> None:
        """Shortest possible 3-mission world: Final Sin (6) + World Spear (8) + Reclaimed Earth (10) = 24 mission locs."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "custom",
                "custom_missions": {"e3m4_boss", "e5m1_spear", "e5m2_earth"},
                "custom_dark_lord": 0,
                "mission_count": 3,
                "mission_order": "random_mission_order",
                "goal": "kill_the_icon_of_sin",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        unfilled = [loc for loc in mw.get_locations(1) if not loc.item]

        # 24 mission locs + 7 fortress locs (6 non-consumer + 1 consumer from 1 spend group) = 31 total locs
        self.assertEqual(len(unfilled), 31)
        self.assertEqual(len(mw.itempool), 31)

        # In micro-world (< 28 locs), Masteries M=0, WUP=0, Praetor=3 (floor)
        item_names = [item.name for item in mw.itempool]
        self.assertEqual(item_names.count("Weapon Upgrade Points (3)"), 0)
        praetor_count = sum(item_names.count(p) for p in suit_perk_item_names)
        self.assertEqual(praetor_count, 3)
        self.assertEqual(item_names.count("Sentinel Battery Bundle"), 2)  # 1 req + 1 surp in RMO
        self.assertEqual(item_names.count("Sentinel Battery"), 0)

        # Weapon Masteries region should not even have locations
        mastery_locs = [loc for loc in unfilled if loc.parent_region.name == "Weapon Masteries"]
        self.assertEqual(len(mastery_locs), 0)

    def test_extreme_3_mission_outlier_final_sin_spear_earth_mai(self) -> None:
        """Shortest possible 3-mission world in MAI mode (starting_missions=1): exactly 0 flex capacity, 100% balance."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "custom",
                "custom_missions": {"e3m4_boss", "e5m1_spear", "e5m2_earth"},
                "custom_dark_lord": 0,
                "mission_count": 3,
                "mission_order": "mission_access_as_items",
                "starting_missions": 1,
                "goal": "kill_the_icon_of_sin",
                "goal_mission_as_item": 1,
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        unfilled = [loc for loc in mw.get_locations(1) if not loc.item]

        self.assertEqual(len(unfilled), 31)
        self.assertEqual(len(mw.itempool), 31)

        # In MAI with M=0 and L_miss < 28, battery surplus scales to 0, exactly matching capacity
        item_names = [item.name for item in mw.itempool]
        self.assertEqual(item_names.count("Weapon Upgrade Points (3)"), 0)
        self.assertEqual(item_names.count("Sentinel Battery Bundle"), 1)  # 1 req + 0 surp
        self.assertEqual(item_names.count("Sentinel Battery"), 0)

        # Exactly 2 Access items for the 2 non-starting active stages
        access_items = [name for name in item_names if " Access" in name]
        self.assertEqual(len(access_items), 2)

    def test_extreme_3_mission_with_dark_lord(self) -> None:
        """Shortest 3-mission world + Dark Lord Special."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "custom",
                "custom_missions": {"e3m4_boss", "e5m1_spear", "e5m2_earth"},
                "custom_dark_lord": 1,
                "mission_count": 3,
                "mission_order": "random_mission_order",
                "goal": "kill_the_dark_lord",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        unfilled = [loc for loc in mw.get_locations(1) if not loc.item]

        # 31 + 1 (The Dark Lord - Defeated) = 32 locations
        self.assertEqual(len(unfilled), 32)
        self.assertEqual(len(mw.itempool), 32)
        self.assertTrue(world.campaign_plan["dark_lord_active"])

    # -------------------------------------------------------------------------
    # 5. Mission Orders & Sequences
    # -------------------------------------------------------------------------
    def test_vanilla_order_sequence(self) -> None:
        """Vanilla Order preserves chronological sequence across active pool."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "custom",
                "custom_missions": {"e1m1_intro", "e1m3_cult", "e3m4_boss"},
                "custom_dark_lord": 0,
                "mission_order": "vanilla_order",
                "goal": "kill_the_icon_of_sin",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        plan = world.campaign_plan
        # Chronological order of e1m1, e1m3, e3m4
        stage_ids = [s["id"] for s in plan["stages"]]
        self.assertEqual(stage_ids, ["e1m1_intro", "e1m3_cult", "e3m4_boss"])

    def test_rmo_dark_lord_is_final(self) -> None:
        """In RMO with Dark Lord active, Dark Lord must be the final stage in sequence."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "custom",
                "custom_missions": {"e1m1_intro", "e1m2_war", "e1m3_cult"},
                "custom_dark_lord": 1,
                "mission_count": 3,
                "mission_order": "random_mission_order",
                "goal": "kill_the_dark_lord",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        plan = world.campaign_plan
        self.assertEqual(plan["stages"][-1]["id"], "e5m4_boss")

    # -------------------------------------------------------------------------
    # 6. Goal Normalizations
    # -------------------------------------------------------------------------
    def test_goal_kill_icon_of_sin_forces_final_sin(self) -> None:
        """Goal Kill the Icon of Sin forces Final Sin active even if not selected in custom."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "custom",
                "custom_missions": {"e1m1_intro", "e1m2_war", "e1m3_cult"},
                "custom_dark_lord": 0,
                "mission_count": 3,
                "goal": "kill_the_icon_of_sin",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        plan = world.campaign_plan
        self.assertIn("e3m4_boss", plan["active_normal_mission_ids"])
        self.assertEqual(len(plan["active_normal_mission_ids"]), 3)

    def test_goal_kill_dark_lord_forces_dark_lord(self) -> None:
        """Goal Kill the Dark Lord forces Dark Lord active even in Base pool or custom without DL."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "base",
                "mission_count": 5,
                "goal": "kill_the_dark_lord",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        plan = world.campaign_plan
        self.assertTrue(plan["dark_lord_active"])

    def test_goal_acquire_unmaykr_forces_6_gates_and_count_ge_6(self) -> None:
        """Goal Acquire the Unmaykr forces 6 Base Slayer Gates and clamps count >= 6."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "base",
                "mission_count": 3,  # Requested 3, should clamp to 6
                "goal": "acquire_the_unmaykr",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        plan = world.campaign_plan
        self.assertGreaterEqual(len(plan["active_normal_mission_ids"]), 6)
        for gate_stage in BASE_GATE_STAGE_IDS:
            self.assertIn(gate_stage, plan["active_normal_mission_ids"])

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

    def test_goal_complete_full_saga_forces_full_saga(self) -> None:
        """Goal Complete the Full Saga normalizes to Full Saga preset and all 19 missions + Dark Lord."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "base",
                "mission_count": 3,
                "goal": "complete_the_full_saga",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        plan = world.campaign_plan
        self.assertEqual(len(plan["active_normal_mission_ids"]), 19)
        self.assertTrue(plan["dark_lord_active"])

    # -------------------------------------------------------------------------
    # 7. Validation Rejections
    # -------------------------------------------------------------------------
    def test_custom_pool_requires_at_least_3_missions(self) -> None:
        """Custom pool with fewer than 3 normal missions must raise ValueError."""
        with self.assertRaises(ValueError):
            setup_multiworld(
                DoomEternalWorld,
                seed=42,
                options={
                    "mission_pool": "custom",
                    "custom_missions": {"e1m1_intro", "e1m2_war"},
                    "custom_dark_lord": 0,
                    "goal": "kill_the_icon_of_sin",
                },
            )

    def test_custom_pool_dark_lord_only_rejected(self) -> None:
        """Dark Lord only without at least 3 normal missions must raise ValueError."""
        with self.assertRaises(ValueError):
            setup_multiworld(
                DoomEternalWorld,
                seed=42,
                options={
                    "mission_pool": "custom",
                    "custom_missions": set(),
                    "custom_dark_lord": 1,
                    "goal": "kill_the_dark_lord",
                },
            )

    # -------------------------------------------------------------------------
    # 8. Mission Count 5 & 8 Scaling
    # -------------------------------------------------------------------------
    def test_mission_count_5_scaling(self) -> None:
        """5-mission world correctly scales spend groups, masteries, and runes."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "base",
                "mission_count": 5,
                "mission_order": "random_mission_order",
                "goal": "kill_the_icon_of_sin",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        unfilled = [loc for loc in mw.get_locations(1) if loc.address is not None]
        self.assertEqual(len(unfilled), len(mw.itempool))
        plan = world.campaign_plan
        self.assertEqual(len(plan["active_normal_mission_ids"]), 5)
        # 5 missions: 4 spend groups, 3 masteries, 5 normal runes
        self.assertEqual(len(world.active_spend_groups), 4)
        self.assertEqual(world.active_masteries_count, 3)

    def test_mission_count_8_scaling(self) -> None:
        """8-mission world correctly scales spend groups, masteries, and runes."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "full_saga",
                "mission_count": 8,
                "mission_order": "random_mission_order",
                "goal": "kill_the_dark_lord",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        unfilled = [loc for loc in mw.get_locations(1) if loc.address is not None]
        self.assertEqual(len(unfilled), len(mw.itempool))
        plan = world.campaign_plan
        self.assertEqual(len(plan["active_normal_mission_ids"]), 8)
        # 8 missions: 8 spend groups, 5 masteries, 7 normal runes
        self.assertEqual(len(world.active_spend_groups), 8)
        self.assertEqual(world.active_masteries_count, 5)

    # -------------------------------------------------------------------------
    # 9. All 4 Pathological 3-Mission Outliers
    # -------------------------------------------------------------------------
    def test_pathological_outlier_final_sin_spear_immora(self) -> None:
        """Final Sin (6) + World Spear (8) + Immora (10) = 24 locs."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "custom",
                "custom_missions": {"e3m4_boss", "e5m1_spear", "e5m3_hell"},
                "custom_dark_lord": 0,
                "mission_count": 3,
                "mission_order": "random_mission_order",
                "goal": "kill_the_icon_of_sin",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        unfilled = [loc for loc in mw.get_locations(1) if loc.address is not None]
        self.assertEqual(len(unfilled), 31)
        self.assertEqual(len(mw.itempool), 31)

    def test_pathological_outlier_final_sin_spear_swamps(self) -> None:
        """Final Sin (6) + World Spear (8) + Blood Swamps (11) = 25 locs."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "custom",
                "custom_missions": {"e3m4_boss", "e5m1_spear", "e4m2_swamp"},
                "custom_dark_lord": 0,
                "mission_count": 3,
                "mission_order": "random_mission_order",
                "goal": "kill_the_icon_of_sin",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        unfilled = [loc for loc in mw.get_locations(1) if loc.address is not None]
        self.assertEqual(len(unfilled), 32)
        self.assertEqual(len(mw.itempool), 32)

    def test_pathological_outlier_final_sin_earth_immora(self) -> None:
        """Final Sin (6) + Reclaimed Earth (10) + Immora (10) = 26 locs."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "custom",
                "custom_missions": {"e3m4_boss", "e5m2_earth", "e5m3_hell"},
                "custom_dark_lord": 0,
                "mission_count": 3,
                "mission_order": "random_mission_order",
                "goal": "kill_the_icon_of_sin",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        unfilled = [loc for loc in mw.get_locations(1) if loc.address is not None]
        self.assertEqual(len(unfilled), 33)
        self.assertEqual(len(mw.itempool), 33)

    # -------------------------------------------------------------------------
    # 10. Auto-Promotion of Use DLC Content
    # -------------------------------------------------------------------------
    def test_dlc_mission_auto_promotes_use_dlc_content(self) -> None:
        """Selecting DLC mission pool when use_dlc_content=0 auto-promotes to 1."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "dlc_only",
                "use_dlc_content": 0,
                "goal": "kill_the_dark_lord",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        self.assertTrue(bool(world.options.use_dlc_content.value))


    # -------------------------------------------------------------------------
    # 11. Start Inventory Integration in Short Worlds
    # -------------------------------------------------------------------------
    def test_start_inventory_preserves_cardinality_and_reserves_items(self) -> None:
        """Items in start_inventory are reserved into quotas without increasing pool cardinality."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "custom",
                "custom_missions": {"e3m4_boss", "e5m1_spear", "e5m2_earth"},
                "custom_dark_lord": 0,
                "mission_count": 3,
                "mission_order": "random_mission_order",
                "goal": "kill_the_icon_of_sin",
                "start_inventory": {
                    "Lock-on Burst": 1,
                    "Sentinel Battery Bundle": 1,
                },
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        unfilled = [loc for loc in mw.get_locations(1) if loc.address is not None]
        start_inv = world.effective_starting_inventory()
        self.assertEqual(start_inv["Lock-on Burst"], 1)
        self.assertEqual(start_inv["Sentinel Battery Bundle"], 1)
        # Total pool count must equal unfilled location count exactly
        self.assertEqual(len(mw.itempool), len(unfilled))

    # -------------------------------------------------------------------------
    # 12. MAI Access Cardinality: Goal Mission as Item ON vs OFF
    # -------------------------------------------------------------------------
    def test_mai_access_cardinality_goal_mission_as_item_toggle(self) -> None:
        """Goal Mission as Item toggles whether the final goal stage generates an Access item."""
        # Case A: Goal Mission as Item ON
        mw_on = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "custom",
                "custom_missions": {"e3m4_boss", "e5m1_spear", "e5m2_earth"},
                "custom_dark_lord": 0,
                "mission_count": 3,
                "mission_order": "mission_access_as_items",
                "starting_missions": 1,
                "goal": "kill_the_icon_of_sin",
                "goal_mission_as_item": 1,
            },
        )
        item_names_on = [item.name for item in mw_on.itempool]
        access_on = [name for name in item_names_on if " Access" in name]
        self.assertEqual(len(access_on), 2)  # 1 non-starting normal + 1 goal stage
        self.assertIn("Final Sin Access", access_on)

        # Case B: Goal Mission as Item OFF
        mw_off = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "custom",
                "custom_missions": {"e3m4_boss", "e5m1_spear", "e5m2_earth"},
                "custom_dark_lord": 0,
                "mission_count": 3,
                "mission_order": "mission_access_as_items",
                "starting_missions": 1,
                "goal": "kill_the_icon_of_sin",
                "goal_mission_as_item": 0,
            },
        )
        item_names_off = [item.name for item in mw_off.itempool]
        access_off = [name for name in item_names_off if " Access" in name]
        self.assertEqual(len(access_off), 1)  # 1 non-starting normal, 0 for goal stage
        self.assertNotIn("Final Sin Access", access_off)

    # -------------------------------------------------------------------------
    # 13. Complete All Included Missions Victory Semantics
    # -------------------------------------------------------------------------
    def test_complete_all_included_missions_victory_semantics(self) -> None:
        """Complete All Included Missions requires clearances for all active missions."""
        from BaseClasses import CollectionState, ItemClassification
        from worlds.doometernal.items import DoomEternalItem
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "custom",
                "custom_missions": {"e3m4_boss", "e5m1_spear", "e5m2_earth"},
                "custom_dark_lord": 1,
                "mission_count": 3,
                "mission_order": "random_mission_order",
                "goal": "kill_the_icon_of_sin",
                "additional_victory_requirements": {"Complete All Included Missions"},
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        condition = mw.completion_condition[1]

        state = CollectionState(mw)
        # Empty state: not complete
        self.assertFalse(condition(state))

        # Giving goal endpoint event alone: still incomplete because active missions and dark lord are not cleared
        state.collect(DoomEternalItem("Internal Goal Endpoint: Kill the Icon of Sin", ItemClassification.progression, None, 1))
        self.assertFalse(condition(state))

        # Clear active missions except one
        state.collect(DoomEternalItem("Internal Mission Clear: The World Spear", ItemClassification.progression, None, 1))
        state.collect(DoomEternalItem("Internal Mission Clear: Reclaimed Earth", ItemClassification.progression, None, 1))
        self.assertFalse(condition(state))

        # Clear final sin
        state.collect(DoomEternalItem("Internal Mission Clear: Final Sin", ItemClassification.progression, None, 1))
        self.assertFalse(condition(state))  # Dark Lord still active and required!

        # Clear Dark Lord endpoint
        state.collect(DoomEternalItem("Internal Goal Endpoint: Kill the Dark Lord", ItemClassification.progression, None, 1))
        self.assertTrue(condition(state))


if __name__ == "__main__":
    unittest.main()
