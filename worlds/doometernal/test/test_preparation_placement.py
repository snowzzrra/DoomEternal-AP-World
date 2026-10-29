import unittest
from collections import Counter
from io import StringIO

from BaseClasses import CollectionState, PlandoItemBlock
from Fill import FillError, distribute_items_restrictive, distribute_planned_blocks
from Options import ItemLinks, PlandoItems
from test.general import gen_steps, setup_multiworld
from worlds.AutoWorld import call_all
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.campaign import FORTRESS_BOOTSTRAP_LOCATIONS, STAGE_BY_ID
from worlds.generic.Rules import exclusion_rules, forbid_item


class TestPreparationPlacement(unittest.TestCase):
    def setUp(self):
        self.multiworld = setup_multiworld(DoomEternalWorld, steps=gen_steps[:2], seed=230002, options={
            'mission_pool': 'custom',
            'custom_missions': {'Hell on Earth', 'Exultia', 'Cultist Base',
                                'Super Gore Nest', 'Mars Core', 'Final Sin'},
            'mission_order': 'mission_access_as_items', 'starting_missions': 2,
            'campaign_difficulty': 'nightmare', 'enemy_randomizer': True,
            'enemy_preset': 'hells_vanguard', 'randomize_dash': False, 'randomize_chainsaw': False,
        })
        self.world = self.multiworld.worlds[1]
        if self._testMethodName == 'test_plando_preparation_item_preserves_pool_and_progression':
            self.world.options.plando_items = PlandoItems.from_any([{
                'item': self.single_planned_item(), 'location': min(FORTRESS_BOOTSTRAP_LOCATIONS),
                'from_pool': True,
            }])
        for step in gen_steps[2:-1]:
            call_all(self.multiworld, step)

    def single_planned_item(self):
        # a name planned twice can't be forbidden at one of the two opening checks
        planned = Counter(self.world.campaign_plan['bootstrap_placed_items'])
        return next(name for name, count in planned.items() if count == 1)

    def test_excluded_preparation_checks_fail_clearly(self):
        exclusion_rules(self.multiworld, 1, set(FORTRESS_BOOTSTRAP_LOCATIONS))
        with self.assertRaisesRegex(FillError, 'preparation cannot place.*excluded locations'):
            self.world.pre_fill()
        for name in FORTRESS_BOOTSTRAP_LOCATIONS:
            self.assertIsNone(self.multiworld.get_location(name, 1).item)

    def test_preparation_respects_item_rules(self):
        location = self.multiworld.get_location(sorted(FORTRESS_BOOTSTRAP_LOCATIONS)[0], 1)
        name = self.single_planned_item()
        forbid_item(location, name, 1)
        self.world.pre_fill()
        self.assertNotEqual(location.item.name, name)
        self.assertTrue(any(loc.item.name == name for loc in self.multiworld.get_filled_locations(1)))

    def test_plando_preparation_item_preserves_pool_and_progression(self):
        mw = self.multiworld
        location = mw.get_location(sorted(FORTRESS_BOOTSTRAP_LOCATIONS)[0], 1)
        name = self.single_planned_item()
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

    def test_late_plando_copy_does_not_credit_opening_preparation(self):
        mw = self.multiworld
        name = self.single_planned_item()
        regions = STAGE_BY_ID[self.world.campaign_plan['sequence'][-1]]['regions']
        location = next(loc for loc in mw.get_unfilled_locations(1) if loc.address is not None
                        and loc.parent_region.name in regions)
        self.assertFalse(location.can_reach(CollectionState(mw)))
        distribute_planned_blocks(mw, [PlandoItemBlock(
            player=1, from_pool=False, force=True, worlds={1}, items=[name],
            resolved_locations=[location], count={'min': 1, 'max': 1, 'target': 1},
        )])
        self.world.pre_fill()
        opening = [loc for loc in mw.get_filled_locations(1) if loc.name in FORTRESS_BOOTSTRAP_LOCATIONS]
        self.assertTrue(any(loc.item.name == name for loc in opening))
        output = StringIO()
        self.world.write_spoiler(output)
        self.assertNotIn(f'{name} at {location.name}', output.getvalue())

    def test_item_link_event_does_not_credit_opening_preparation(self):
        name = self.single_planned_item()
        self.world.options.item_links = ItemLinks.from_any([{
            'name': 'Shared preparation', 'item_pool': [name],
            'replacement_item': None, 'link_replacement': False,
        }])
        self.multiworld.set_item_links()
        self.multiworld.link_items()
        pool = self.multiworld.itempool.copy()
        self.world.pre_fill()
        self.assertEqual(self.multiworld.itempool, pool)
        self.assertTrue(any(loc.address is not None and loc.item.player == 1 and loc.item.name == name
                            for loc in self.world.preparation_placements))

    def test_spoiler_reports_opening_preparation(self):
        self.world.pre_fill()
        output = StringIO()
        self.world.write_spoiler(output)
        text = output.getvalue()
        self.assertIn(self.world.options.enemy_preset.current_option_name, text)
        names = self.world.campaign_plan['bootstrap_placed_items'] + self.world.campaign_plan['opening_placed_items']
        for name in names:
            location = next(loc for loc in self.multiworld.get_filled_locations(1) if loc.item.name == name)
            self.assertIn(f'{name} at {location.name}', text)

    def test_preparation_places_every_required_copy(self):
        self.world.pre_fill()
        plan = self.world.campaign_plan
        expected = Counter(plan['bootstrap_placed_items']) + Counter(plan['opening_placed_items'])
        placed = Counter(loc.item.name for loc in self.multiworld.get_filled_locations(1)
                         if loc.address is not None)
        self.assertEqual(placed & expected, expected)
