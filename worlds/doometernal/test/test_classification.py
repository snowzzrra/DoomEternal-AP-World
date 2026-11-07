import unittest

from BaseClasses import CollectionState, Item, ItemClassification, Location, Region
from Fill import distribute_items_restrictive

from test.general import setup_multiworld
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.classification import (
    build_progression_only_state,
)


class TestDynamicProgressionClassification(unittest.TestCase):
    def test_base_without_dlc_classifies_the_effective_crucible_requirement(self):
        for special in ("progressive_special_weapon", "progressive_sentinel_hammer", "the_crucible"):
            with self.subTest(special=special):
                mw = setup_multiworld(
                    DoomEternalWorld,
                    seed=1000,
                    options={
                        "mission_pool": "base",
                        "mission_order": "vanilla_order",
                        "goal": "kill_the_icon_of_sin",
                        "use_dlc_content": False,
                        "enemy_randomizer": False,
                        "special_weapon": special,
                        "additional_victory_requirements": {"Complete All Mission Challenges"},
                    },
                )
                crucible = next(item for item in mw.itempool if item.name == "The Crucible")
                self.assertTrue(crucible.advancement)
                state = mw.get_all_state(False)
                state.sweep_for_advancements()
                self.assertTrue(mw.get_location("Nekravol - Mission Challenge - Die by the Sword", 1).can_reach(state))
                distribute_items_restrictive(mw)
                self.assertTrue(mw.can_beat_game())

    def test_classification_does_not_sweep_unconnected_foreign_world(self):
        from test.general import TestWorld

        mw = setup_multiworld(
            [DoomEternalWorld, TestWorld],
            seed=42,
            steps=("generate_early", "create_regions"),
            options={"enemy_randomizer": False},
        )
        menu = Region("Menu", 2, mw)
        unfinished = Region("Unconnected", 2, mw)
        mw.regions.extend((menu, unfinished))
        event = Location(2, "Foreign Event", None, unfinished)
        event.place_locked_item(Item("Foreign Progress", ItemClassification.progression, None, 2))
        unfinished.locations.append(event)
        mw.worlds[1].create_items()
        state = build_progression_only_state(mw.worlds[1])
        self.assertFalse(state.has("Foreign Progress", 2))
        self.assertTrue(mw.worlds[1].classification_ledger.all_targets_satisfied)

    def test_fortress_spend_group_atomicity(self):
        from worlds.doometernal.campaign import FORTRESS_BOOTSTRAP_LOCATIONS, completion_event

        mw = setup_multiworld(DoomEternalWorld, seed=42, options={"enemy_randomizer": False})
        state = CollectionState(mw)
        reachable = {
            loc.name
            for loc in mw.get_reachable_locations(state, 1)
            if loc.address is not None and loc.name.startswith("Fortress of Doom - ")
        }
        self.assertEqual(reachable, FORTRESS_BOOTSTRAP_LOCATIONS)
        for name in ("Fortress of Doom - Fully Upgraded Suit Cheat Code", "Fortress of Doom - Unmaykr Acquired"):
            self.assertFalse(mw.get_location(name, 1).can_reach(state))
        praetor = mw.get_location("Fortress of Doom - Praetor Suit", 1)
        runes = mw.get_location("Fortress of Doom - All Runes Cheat Code", 1)
        for key in mw.worlds[1].campaign_plan["sequence"]:
            state.collect(Item(completion_event(key), ItemClassification.progression, None, 1), prevent_sweep=True)
        for _ in range(10):
            state.collect(mw.create_item("Sentinel Battery Bundle", 1))
        self.assertFalse(praetor.can_reach(state))
        self.assertFalse(runes.can_reach(state))
        state.collect(mw.create_item("Sentinel Battery Bundle", 1))
        self.assertTrue(praetor.can_reach(state))
        self.assertTrue(runes.can_reach(state))
