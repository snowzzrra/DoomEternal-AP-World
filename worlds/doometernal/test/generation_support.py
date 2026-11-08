from collections import Counter

import pytest
from BaseClasses import Item, ItemClassification, LocationProgressType
from Fill import distribute_items_restrictive

from worlds.AutoWorld import call_all

pytestmark = pytest.mark.slow

PREPARATION_OPTIONS = {
    "mission_pool": "custom",
    "custom_missions": {"Hell on Earth", "Exultia", "Cultist Base", "Super Gore Nest", "Mars Core", "Final Sin"},
    "mission_order": "mission_access_as_items",
    "starting_missions": 2,
    "campaign_difficulty": "nightmare",
    "enemy_randomizer": True,
    "enemy_preset": "hells_vanguard",
    "randomize_dash": False,
    "randomize_chainsaw": False,
}


def physical_items(multiworld):
    held = [item for world in multiworld.worlds.values() for item in world.get_pre_fill_items()]
    return [item for item in multiworld.get_items() + held if item.code is not None]


def item_counts(items):
    return Counter((item.player, item.name, item.code, item.classification) for item in items)


def filled_item_counts(mw):
    return item_counts(loc.item for loc in mw.get_filled_locations() if loc.address is not None)


def fill(multiworld):
    distribute_items_restrictive(multiworld)
    call_all(multiworld, "post_fill")
    call_all(multiworld, "finalize_multiworld")


def collect_sphere_items(state, sphere):
    for location in sphere:
        before = state.prog_items[location.player].copy()
        state.collect(location.item, prevent_sweep=True, location=location)
        if location.item.player != location.player:
            assert state.prog_items[location.player] == before


def assert_optional_reward(location):
    assert location.progress_type == LocationProgressType.EXCLUDED
    assert not getattr(location.item, "advancement", False)
    assert not getattr(location.item, "useful", False)
    for classification in (ItemClassification.progression, ItemClassification.useful):
        assert not location.item_rule(Item("Foreign item", classification, 1, 2))
    assert location.item_rule(Item("Foreign filler", ItemClassification.filler, 2, 2))
