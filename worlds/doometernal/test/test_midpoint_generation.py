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
from .bases import DLC_START_INVENTORY


class TestMidpointGeneration(unittest.TestCase):
    def test_unprepared_start_keeps_inventory_and_progression_without_refusing_generation(self):
        from worlds.doometernal.combat_readiness import is_mission_ready
        mw = setup_multiworld(DoomEternalWorld, seed=429261552, options={
            'mission_pool': 'custom', 'mission_count': 6, 'goal': 'kill_the_icon_of_sin',
            'custom_missions': {'Cultist Base', 'Doom Hunter Base', 'Super Gore Nest',
                                'ARC Complex', 'Mars Core', 'Taras Nabad'},
            'mission_order': 'vanilla_order', 'campaign_difficulty': 'nightmare',
            'logic_difficulty': 'expert', 'starting_weapon': 'heavy_cannon',
            'randomize_dash': True, 'randomize_chainsaw': True,
        })
        world = mw.worlds[1]
        plan = world.campaign_plan
        self.assertEqual(plan['unprepared_start_stages'], ['e1m3_cult'])
        self.assertEqual(Counter(item.name for item in mw.precollected_items[1]), Counter({'Heavy Cannon': 1}))
        self.assertFalse(plan['bootstrap_placed_items'])
        state = CollectionState(mw)
        self.assertFalse(evaluate_mission_readiness(state, 1, 'e1m3_cult', world, context='opening').ready)
        self.assertTrue(is_mission_ready(state, 1, 'e1m3_cult', world, context='opening'))
        self.assertTrue(mw.get_entrance('Mission Select: Cultist Base', 1).can_reach(state))
        self.assertFalse(mw.get_entrance('Mission Select: Doom Hunter Base', 1).can_reach(state))
        distribute_items_restrictive(mw)
        self.assertTrue(mw.can_beat_game())

    def test_dlc_mission_gate_keys_follow_missions_with_dlc_gear_disabled(self):
        mw = setup_multiworld(DoomEternalWorld, seed=141104560, options={
            'mission_pool': 'full_saga', 'goal': 'complete_the_full_saga',
            'use_dlc_content': False, 'enemy_randomizer': False, 'include_slayer_gates': True,
        })
        state = mw.get_all_state(False)
        state.sweep_for_advancements()
        for mission in ('UAC Atlantica Facility', 'The Holt'):
            self.assertTrue(state.has(f'Slayer Gate Key {mission}', 1))
            self.assertTrue(mw.get_location(f'{mission} - Slayer Gate Complete', 1).can_reach(state))
        distribute_items_restrictive(mw)
        self.assertTrue(mw.can_beat_game())

    def test_varied_openings_fit_fortress_preparation(self):
        from worlds.doometernal.enemy_options import SPECIES_GROUPS
        from worlds.doometernal.campaign import _start_stage_readiness
        weights = {name: {'fodder': 20, 'heavy': 20, 'superheavy': 10, 'support': 7,
                         'stationary': 0}[role] for role, names in SPECIES_GROUPS.items() for name in names}
        weights.update(buff_pod=7, zombie_t1_screecher=7)
        attributes = dict(early_minimum=100, early_maximum=100, late_minimum=100, late_maximum=100)
        options = {
            'mission_pool': 'full_saga', 'mission_count': 6, 'mission_order': 'random_mission_order',
            'campaign_difficulty': 'ultra_violence', 'starting_weapon': 'random_weapon',
            'randomize_dash': False, 'randomize_chainsaw': False, 'enemy_weights': weights,
            'enemy_health': attributes, 'enemy_damage': attributes, 'enemy_speed': attributes,
            'enemy_size_variation_chance': 3,
        }
        for seed in (89654039614909134671, 348679427, 164570677, 427264797):
            with self.subTest(seed=seed):
                mw = setup_multiworld(DoomEternalWorld, seed=seed, options=options)
                world = mw.worlds[1]
                plan = world.campaign_plan
                state = CollectionState(mw)
                placed = [loc.item for loc in mw.get_filled_locations(1) if loc.item]
                for name in plan['bootstrap_placed_items']:
                    item = next(item for item in placed if item.player == 1 and item.name == name and item.advancement)
                    state.collect(item)
                    placed.remove(item)
                self.assertTrue(_start_stage_readiness(state, 1, plan['opening_stage'], world).ready)
                distribute_items_restrictive(mw)
                self.assertTrue(mw.can_beat_game())

    def test_starting_arsenal_is_earned_before_later_encounters(self):
        from worlds.doometernal.native_enemy_safety import OPENING_REGIONS
        mw = setup_multiworld(DoomEternalWorld, seed=230001, options={
            'mission_pool': 'custom', 'custom_missions': {'Hell on Earth', 'Exultia', 'Cultist Base', 'Super Gore Nest', 'Mars Core', 'Final Sin'},
            'mission_order': 'mission_access_as_items', 'starting_missions': 2,
            'campaign_difficulty': 'nightmare', 'enemy_randomizer': True,
            'enemy_preset': 'hells_vanguard', 'randomize_dash': False, 'randomize_chainsaw': False,
        })
        world = mw.worlds[1]
        plan = world.campaign_plan
        self.assertEqual(Counter(item.name for item in mw.precollected_items[1]),
                         Counter({'Combat Shotgun': 1, 'Chainsaw': 1,
                                  'Dash': int(any(stage not in {'e1m1_intro', 'e1m2_war'}
                                                 for stage in plan['starting_stages']))}))
        stage = plan['opening_stage']
        state = CollectionState(mw)
        for loc in mw.get_reachable_locations(state, 1):
            if loc.address is not None and loc.item is not None and loc.parent_region.name not in OPENING_REGIONS[stage]:
                state.collect(loc.item, True, loc)
        self.assertTrue(evaluate_mission_readiness(state, 1, stage, world, context='opening').ready)
        for loc in mw.get_reachable_locations(state, 1):
            if loc.address is not None and loc.item is not None:
                state.collect(loc.item, True, loc)
        self.assertTrue(evaluate_mission_readiness(state, 1, stage, world).ready)
        all_items = mw.itempool + mw.precollected_items[1] + [
            loc.item for loc in mw.get_filled_locations(1) if loc.address is not None]
        counts = Counter(item.name for item in all_items)
        for name, quantity in plan['semantic_counts'].items():
            self.assertEqual(counts[name], quantity, name)
        distribute_items_restrictive(mw)
        self.assertTrue(mw.can_beat_game())


    def test_short_dlc_campaign_keeps_endurance_preparation(self):
        mw = setup_multiworld(DoomEternalWorld, seed=1077, options={
            "mission_pool": "full_saga", "mission_order": "random_mission_order",
            "mission_count": 6, "goal": "kill_the_dark_lord", "campaign_difficulty": 1,
            "randomize_dash": True,
            "randomize_chainsaw": True,
            "start_inventory": DLC_START_INVENTORY,
        })
        for name, quantity in DLC_START_INVENTORY.items():
            for _ in range(quantity):
                mw.push_precollected(mw.worlds[1].create_item(name))
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
            (3, {"mission_pool": "dlc_only", "mission_order": "random_mission_order", "mission_count": 6,
                 "goal": "kill_the_dark_lord", "randomize_dash": True, "start_inventory": DLC_START_INVENTORY}),
        )
        for seed, options in cases:
            with self.subTest(seed=seed):
                mw = setup_multiworld(DoomEternalWorld, seed=seed, options=options)
                world = mw.worlds[1]
                for name, quantity in options.get('start_inventory', {}).items():
                    for _ in range(quantity):
                        mw.push_precollected(world.create_item(name))
                plan = world.campaign_plan
                self.assertEqual(len(mw.itempool), len(mw.get_unfilled_locations(1)))
                self.assertFalse(any(item.code in LEGACY_AUTOMAP_PERK_IDS for item in mw.itempool + mw.precollected_items[1]))
                counts = Counter(item.name for item in mw.itempool + mw.precollected_items[1] + [
                    loc.item for loc in mw.get_filled_locations(1) if loc.address is not None])
                for name, quantity in plan["semantic_counts"].items():
                    self.assertEqual(counts[name], quantity + options.get('start_inventory', {}).get(name, 0), name)
                if options.get("randomize_dash") is False:
                    self.assertEqual(plan["fixed_dash_completion_stage"], plan["sequence"][0])
                if len(plan["active_normal_mission_ids"]) < 9:
                    self.assertGreaterEqual(sum(counts[name] for name in NORMAL_RUNE_NAMES), 9)
                    for stat in ("Health", "Armor", "Ammo"):
                        self.assertGreaterEqual(counts[f"Progressive {stat} Upgrade"], 4)
                self.assertEqual(len(suit_perk_item_names), 17)
                distribute_items_restrictive(mw)
                presentation = world.fill_slot_data()["stage_profiles"]
                for stage, rating in presentation.items():
                    self.assertEqual(rating["skulls"], get_mission_skull_tier(stage, world))
                    self.assertNotIn("expected_player_cr", rating)
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
                            result = evaluate_mission_readiness(state, 1, stage, world,
                                context='opening' if stage == plan.get('opening_stage') else 'base')
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
