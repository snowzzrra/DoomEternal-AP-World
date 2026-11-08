from collections import Counter

import pytest
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
