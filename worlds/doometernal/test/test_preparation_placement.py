import unittest

from BaseClasses import PlandoItemBlock
from Fill import FillError, distribute_items_restrictive, distribute_planned_blocks
from test.general import gen_steps, setup_multiworld
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.campaign import FORTRESS_BOOTSTRAP_LOCATIONS
from worlds.generic.Rules import exclusion_rules, forbid_item


class TestPreparationPlacement(unittest.TestCase):
    def setUp(self):
        self.multiworld = setup_multiworld(DoomEternalWorld, steps=gen_steps[:-1], seed=230001, options={
            'mission_pool': 'custom',
            'custom_missions': {'Hell on Earth', 'Exultia', 'Cultist Base',
                                'Super Gore Nest', 'Mars Core', 'Final Sin'},
            'mission_order': 'mission_access_as_items', 'starting_missions': 2,
            'campaign_difficulty': 'nightmare', 'enemy_randomizer': True,
            'enemy_preset': 'hells_vanguard', 'randomize_dash': False, 'randomize_chainsaw': False,
        })
        self.world = self.multiworld.worlds[1]

    def test_excluded_preparation_checks_fail_clearly(self):
        exclusion_rules(self.multiworld, 1, set(FORTRESS_BOOTSTRAP_LOCATIONS))
        with self.assertRaisesRegex(FillError, 'preparation cannot place.*excluded locations'):
            self.world.pre_fill()
        for name in FORTRESS_BOOTSTRAP_LOCATIONS:
            self.assertIsNone(self.multiworld.get_location(name, 1).item)

    def test_preparation_respects_item_rules(self):
        location = self.multiworld.get_location(sorted(FORTRESS_BOOTSTRAP_LOCATIONS)[0], 1)
        name = self.world.campaign_plan['bootstrap_placed_items'][0]
        forbid_item(location, name, 1)
        self.world.pre_fill()
        self.assertNotEqual(location.item.name, name)
        self.assertTrue(any(loc.item.name == name for loc in self.multiworld.get_filled_locations(1)))

    def test_plando_preparation_item_preserves_pool_and_progression(self):
        mw = self.multiworld
        location = mw.get_location(sorted(FORTRESS_BOOTSTRAP_LOCATIONS)[0], 1)
        name = 'Lock-on Burst'
        self.assertIn(name, self.world.campaign_plan['bootstrap_placed_items'])
        item = next(item for item in mw.itempool if item.player == 1 and item.name == name)
        distribute_planned_blocks(mw, [PlandoItemBlock(
            player=1, from_pool=True, force=True, worlds={1}, items=[name],
            resolved_locations=[location], count={'min': 1, 'max': 1, 'target': 1},
        )])
        self.world.pre_fill()
        self.assertIs(location.item, item)
        items = mw.itempool + [loc.item for loc in mw.get_filled_locations(1)]
        self.assertEqual(sum(item.name == name for item in items), 1)
        self.assertEqual(len(mw.itempool), len(mw.get_unfilled_locations(1)))
        distribute_items_restrictive(mw)
        self.assertTrue(mw.can_beat_game())
