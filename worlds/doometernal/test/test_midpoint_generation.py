import unittest
from collections import Counter

from BaseClasses import CollectionState
from Fill import distribute_items_restrictive
from test.general import setup_multiworld
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.combat_readiness import (
    SPIRIT_BREAKPOINTS, evaluate_mission_readiness, get_mission_skull_tier,
)
from worlds.doometernal.combat_rating import NORMAL_RUNE_NAMES, evaluate_player_loadout_cr
from worlds.doometernal.items import LEGACY_AUTOMAP_PERK_IDS, item_data_table, suit_perk_item_names
from worlds.doometernal.logic import connection_requirement, requirement_satisfied
from worlds.doometernal.planner import FastState


class TestMidpointGeneration(unittest.TestCase):
    def test_late_start_witness_is_placed_in_initial_reachable_checks(self):
        mw = setup_multiworld(DoomEternalWorld, seed=1112, options={
            "mission_pool": "dlc_only", "mission_order": "random_mission_order",
            "goal": "kill_the_icon_of_sin", "campaign_difficulty": 0,
            "randomize_dash": False, "randomize_chainsaw": False,
        })
        state = CollectionState(mw)
        initial = {location for location in mw.get_reachable_locations(state, 1) if location.address is not None}
        witness = Counter(mw.worlds[1].campaign_plan["bootstrap_placed_items"])
        self.assertTrue(witness)
        distribute_items_restrictive(mw)
        self.assertFalse(witness - Counter(location.item.name for location in initial))
        self.assertTrue(mw.can_beat_game())

    def test_short_dlc_campaign_keeps_endurance_preparation(self):
        mw = setup_multiworld(DoomEternalWorld, seed=1077, options={
            "mission_pool": "full_saga", "mission_order": "random_mission_order",
            "mission_count": 3, "goal": "kill_the_dark_lord", "campaign_difficulty": 1,
            "randomize_dash": True,
            "randomize_chainsaw": True,
        })
        state = mw.get_all_state(False)
        state.sweep_for_advancements()
        result = evaluate_mission_readiness(state, 1, "e4m1_rig", mw.worlds[1])
        self.assertEqual(result.effective_cr, result.mission_base_cr)
        self.assertTrue(result.ready)
        distribute_items_restrictive(mw)
        self.assertTrue(mw.can_beat_game())

    def test_vanilla_full_saga_icon_is_last(self):
        mw = setup_multiworld(DoomEternalWorld, seed=19, options={
            "mission_pool": "full_saga", "mission_order": "vanilla_order", "goal": "kill_the_icon_of_sin"})
        plan = mw.worlds[1].campaign_plan
        self.assertEqual(len(plan["sequence"]), 20)
        self.assertEqual(plan["sequence"][-2:], ["e5m4_boss", "e3m4_boss"])
        self.assertEqual(plan["starting_stages"], [plan["sequence"][0]])

    def test_enemizer_frontloads_arsenal_without_adding_item_copies(self):
        from worlds.doometernal.combat_rating import WEAPON_NAMES, MOD_HOST
        mw = setup_multiworld(DoomEternalWorld, seed=29, options={
            'mission_order': 'random_mission_order', 'mission_count': 6,
            'enemy_randomizer': True, 'enemy_preset': 'slayers_path'})
        early = mw.worlds[1].frontloaded_arsenal
        weapons = set(early) & set(WEAPON_NAMES)
        self.assertEqual(len(weapons), 2)
        for weapon in weapons:
            self.assertEqual(sum(item.name == weapon for item in mw.itempool), 1)
            if any(MOD_HOST.get(item.name) == weapon for item in mw.itempool):
                self.assertTrue(any(MOD_HOST.get(name) == weapon for name in early))
        self.assertTrue(all(item.advancement for item in mw.itempool if item.name in early))
        distribute_items_restrictive(mw)
        self.assertTrue(mw.can_beat_game())

    def test_traversal_and_endurance(self):
        state = FastState(item_data_table.keys())
        state.prog_items.update({f"Progressive {stat} Upgrade": 4 for stat in ("Health", "Armor", "Ammo")})
        full = evaluate_mission_readiness(state, 1, "e5m1_spear", logic_difficulty=1)
        self.assertTrue(full.ready)
        state.prog_items.pop("Dash")
        self.assertFalse(evaluate_mission_readiness(state, 1, "e5m1_spear", logic_difficulty=1).ready)
        state.collect("Dash")
        state.prog_items.pop("Super Shotgun")
        self.assertIn("Super Shotgun", evaluate_mission_readiness(state, 1, "e5m1_spear").missing_requirements)
        state.collect("Super Shotgun")
        for name in NORMAL_RUNE_NAMES:
            state.prog_items.pop(name, None)
        self.assertFalse(evaluate_mission_readiness(state, 1, "e5m1_spear").ready)
        for randomized in (False, True):
            requirement = connection_requirement({"soft_capabilities": ["requires_dash"]}, randomize_dash=randomized)
            self.assertFalse(requirement_satisfied(requirement, FastState(), 1))

    def test_new_generation_matrix_and_reachable_frontiers(self):
        cases = (
            (6, {"mission_pool": "custom", "custom_missions": {
                "Hell on Earth", "Exultia", "Mars Core", "The World Spear", "Reclaimed Earth", "Final Sin"},
                 "mission_order": "random_mission_order", "mission_count": 6,
                 "goal": "kill_the_icon_of_sin",
                 "randomize_dash": False, "reveal_ap_locations_on_automap": True}),
            (19, {"mission_pool": "full_saga", "mission_order": "mission_access_as_items", "mission_count": "all"}),
            (3, {"mission_pool": "dlc_only", "mission_order": "random_mission_order", "mission_count": 3,
                 "goal": "kill_the_dark_lord", "randomize_dash": True}),
        )
        for seed, options in cases:
            with self.subTest(seed=seed):
                mw = setup_multiworld(DoomEternalWorld, seed=seed, options=options)
                world = mw.worlds[1]
                plan = world.campaign_plan
                self.assertEqual(len(mw.itempool), len(mw.get_unfilled_locations(1)))
                self.assertFalse(any(item.code in LEGACY_AUTOMAP_PERK_IDS for item in mw.itempool + mw.precollected_items[1]))
                counts = Counter(item.name for item in mw.itempool + mw.precollected_items[1])
                for name, quantity in plan["semantic_counts"].items():
                    self.assertEqual(counts[name], quantity, name)
                if options.get("randomize_dash") is False:
                    self.assertEqual(plan["fixed_dash_completion_stage"], plan["sequence"][0])
                if len(plan["active_normal_mission_ids"]) < 9:
                    self.assertGreaterEqual(sum(counts[name] for name in NORMAL_RUNE_NAMES), 2)
                    for stat in ("Health", "Armor", "Ammo"):
                        self.assertGreaterEqual(counts[f"Progressive {stat} Upgrade"], 1)
                self.assertEqual(len(suit_perk_item_names), 17)
                presentation = world.fill_slot_data()["mission_presentation_v2"]
                for stage, rating in presentation.items():
                    self.assertEqual(rating["skull_tier"], get_mission_skull_tier(stage, world))
                    self.assertNotIn("expected_player_cr", rating)
                distribute_items_restrictive(mw)
                self.assertTrue(mw.can_beat_game())
                state = CollectionState(mw)
                physical_items = Counter(
                    "Blood Punch" if item.name == "Progressive Blood Punch" else item.name
                    for item in mw.precollected_items[1])
                observed = set()
                for sphere in mw.get_spheres():
                    for stage in plan["sequence"]:
                        if stage in observed:
                            continue
                        region = mw.get_region(next(s["entry_region"] for s in plan["stages"] if s["id"] == stage), 1)
                        if state.can_reach(region):
                            result = evaluate_mission_readiness(state, 1, stage, world)
                            physical_state = state.copy()
                            for name, quantity in physical_items.items():
                                physical_state.prog_items[1][name] = max(
                                    quantity, physical_state.prog_items[1][name])
                            cr = evaluate_player_loadout_cr(physical_state, 1, world)
                            print("FRONTIER", seed, stage, "logical_CR", result.player_cr,
                                  "physical_CR", cr.total, dict(cr.categories),
                                  "runes", sum(physical_state.has(name, 1) for name in NORMAL_RUNE_NAMES),
                                  "capacity", [physical_state.count(f"Progressive {stat} Upgrade", 1) for stat in ("Health", "Armor", "Ammo")],
                                  "suits", sum(physical_state.has(name, 1) for name in suit_perk_item_names),
                                  "missing", result.missing_requirements)
                            self.assertTrue(result.ready)
                            if stage == "e5m1_spear":
                                pair = next(pair for pair, owner in SPIRIT_BREAKPOINTS.items() if owner == stage)
                                self.assertTrue(any(e.connected_region.name == pair[1] for e in mw.get_region(pair[0], 1).exits))
                            observed.add(stage)
                    if not sphere:
                        break
                    for location in sphere:
                        state.collect(location.item, True, location)
                        name = location.item.name
                        physical_items["Blood Punch" if name == "Progressive Blood Punch" else name] += 1


if __name__ == "__main__":
    unittest.main()
