from math import ceil

import pytest
from BaseClasses import Item, LocationProgressType
from BaseClasses import ItemClassification as Classification
from Fill import distribute_items_restrictive

from test.general import gen_steps, setup_multiworld
from worlds.AutoWorld import call_all
from worlds.doometernal import DoomEternalWorld
from worlds.generic.Rules import add_item_rule, exclusion_rules

pytestmark = pytest.mark.slow


def battery_locations(mw, player):
    return [mw.get_location(name, player) for group in mw.worlds[player].active_spend_groups
            for name in group["locations"]]


def chosen_locations(mw, player):
    foreign_filler = Item("Reward probe", Classification.filler, 1, 3)
    return {loc.name for loc in battery_locations(mw, player) if not loc.item_rule(foreign_filler)}


def generate(players, percent, mission_count):
    return setup_multiworld([DoomEternalWorld] * players, seed=230001, options={
        "mission_pool": "base", "mission_count": mission_count, "resource_profile": "lean",
        "goal": "kill_the_icon_of_sin",
        "enemy_randomizer": False, "include_slayer_gates": False,
        "include_secret_encounters": False, "include_weapon_mastery_challenges": False,
        "useful_fortress_rewards": percent,
    })


def assert_reward_rules(mw, player, chosen):
    classifications = (Classification.filler, Classification.trap, Classification.progression,
                       Classification.useful, Classification.progression_skip_balancing,
                       Classification.trap | Classification.useful, Classification.trap | Classification.progression)
    for loc in battery_locations(mw, player):
        for owner in (player, 3):
            for classification in classifications:
                item = Item("Reward probe", classification, 1, owner)
                useful = bool(classification & (Classification.progression | Classification.useful))
                expected = useful or (loc.name not in chosen and (owner != player or mw.players == 1))
                assert loc.item_rule(item) == expected, (loc.name, owner, classification)
        assert not loc.item_rule(mw.worlds[player].create_item("Sentinel Battery"))


def assert_filled_rewards(mw, player):
    chosen = chosen_locations(mw, player)
    for loc in battery_locations(mw, player):
        item = loc.item
        assert item is not None
        if loc.name in chosen or (mw.players > 1 and item.player == player):
            assert item.classification & (Classification.progression | Classification.useful)


@pytest.mark.parametrize("players", [1, 2])
@pytest.mark.parametrize("percent", [0, 75, 100])
@pytest.mark.parametrize("mission_count,location_count", [(6, 8), ("all", 12)])
def test_useful_fortress_rewards_fill(players, percent, mission_count, location_count):
    mw = generate(players, percent, mission_count)
    replay = generate(players, percent, mission_count)
    for player in mw.player_ids:
        chosen = chosen_locations(mw, player)
        assert len(battery_locations(mw, player)) == location_count
        assert len(chosen) == ceil(location_count * percent / 100)
        assert chosen == chosen_locations(replay, player)
        assert_reward_rules(mw, player, chosen)
    distribute_items_restrictive(mw)
    for player in mw.player_ids:
        assert_filled_rewards(mw, player)


def generate_with_exclusions(percent):
    mw = setup_multiworld([DoomEternalWorld] * 2, steps=gen_steps[:4], seed=230001, options={
        "mission_pool": "base", "mission_count": "all", "enemy_randomizer": False,
        "useful_fortress_rewards": percent,
    })
    locations = battery_locations(mw, 1)
    excluded = {loc.name for loc in locations[:2]}
    exclusion_rules(mw, 1, excluded)
    for loc in locations:
        add_item_rule(loc, lambda item: item.name != "Blocked reward")
    outside = [loc for loc in mw.get_locations(1) if loc not in locations]
    outside_rules = [loc.item_rule for loc in outside]
    for step in gen_steps[4:]:
        call_all(mw, step)
    assert [loc.item_rule for loc in outside] == outside_rules
    return mw, locations, excluded


@pytest.mark.parametrize("percent", [0, 75, 100])
def test_fortress_exclusions_and_existing_rules(percent):
    mw, locations, excluded = generate_with_exclusions(percent)
    chosen = chosen_locations(mw, 1)
    assert len(chosen) == min(len(locations) - len(excluded), ceil(len(locations) * percent / 100))
    assert chosen.isdisjoint(excluded)
    assert all(mw.get_location(name, 1).progress_type == LocationProgressType.EXCLUDED for name in excluded)
    for loc in locations:
        assert not loc.item_rule(Item("Blocked reward", Classification.progression, 1, 3))
    distribute_items_restrictive(mw)
