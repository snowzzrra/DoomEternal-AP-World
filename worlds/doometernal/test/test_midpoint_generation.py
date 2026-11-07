import unittest
from collections import Counter

from BaseClasses import CollectionState
from Fill import distribute_items_restrictive

from test.general import setup_multiworld
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.combat_rating import NORMAL_RUNE_NAMES
from worlds.doometernal.combat_readiness import (
    evaluate_mission_readiness,
)
from worlds.doometernal.items import item_data_table
from worlds.doometernal.logic import connection_requirement, requirement_satisfied
from worlds.doometernal.planner import FastState
import pytest

pytestmark = pytest.mark.slow


def _collect_outside_opening(mw, stage, state):
    from worlds.doometernal.native_enemy_safety import OPENING_REGIONS
    for loc in mw.get_reachable_locations(state, 1):
        if loc.address is not None and loc.item is not None and loc.parent_region.name not in OPENING_REGIONS[stage]:
            state.collect(loc.item, True, loc)


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

    def _assert_varied_opening(self, options, seed):
        from worlds.doometernal.campaign import _start_stage_readiness
        mw = setup_multiworld(DoomEternalWorld, seed=seed, options=options)
        world = mw.worlds[1]
        plan = world.campaign_plan
        state = CollectionState(mw)
        placed = [loc.item for loc in mw.get_filled_locations(1) if loc.item]
        for name in plan["bootstrap_placed_items"]:
            item = next(item for item in placed if item.player == 1 and item.name == name and item.advancement)
            state.collect(item)
            placed.remove(item)
        self.assertTrue(_start_stage_readiness(state, 1, plan["opening_stage"], world).ready)
        distribute_items_restrictive(mw)
        self.assertTrue(mw.can_beat_game())


    def test_varied_openings_fit_fortress_preparation(self):
        from worlds.doometernal.enemy_options import SPECIES_GROUPS

        weights = {
            name: {"fodder": 20, "heavy": 20, "superheavy": 10, "support": 7, "stationary": 0}[role]
            for role, names in SPECIES_GROUPS.items()
            for name in names
        }
        weights.update(buff_pod=7, zombie_t1_screecher=7)
        attributes = {"early_minimum": 100, "early_maximum": 100, "late_minimum": 100, "late_maximum": 100}
        options = {
            "mission_pool": "full_saga",
            "mission_count": 6,
            "mission_order": "random_mission_order",
            "campaign_difficulty": "ultra_violence",
            "starting_weapon": "random_weapon",
            "randomize_dash": False,
            "randomize_chainsaw": False,
            "enemy_weights": weights,
            "enemy_health": attributes,
            "enemy_damage": attributes,
            "enemy_speed": attributes,
            "enemy_size_variation_chance": 3,
        }
        for seed in (89654039614909134671, 348679427, 164570677, 427264797):
            with self.subTest(seed=seed):
                self._assert_varied_opening(options, seed)

    def test_starting_arsenal_is_earned_before_later_encounters(self):
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
        _collect_outside_opening(mw, stage, state)
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


if __name__ == "__main__":
    unittest.main()
