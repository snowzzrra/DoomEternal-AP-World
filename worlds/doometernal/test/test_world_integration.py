from collections import Counter
from io import StringIO

import pytest

from BaseClasses import CollectionState
from Options import OptionError, get_option_groups
from test.general import gen_steps, setup_multiworld
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.campaign import STAGE_BY_ID
from worlds.doometernal.items import FILLER_WEIGHT_NAMES, POOL_ITEM_LIMITS


CAMPAIGN = {"mission_pool": "base", "mission_count": 6, "goal": "kill_the_icon_of_sin"}


def test_item_link_replacements_follow_filler_weights():
    options = {**CAMPAIGN, "enemy_randomizer": False,
               "filler_weights": {**dict.fromkeys(FILLER_WEIGHT_NAMES, 0), "Small Health": 1},
               "item_links": [{"name": "Shared arsenal", "item_pool": ["Heavy Cannon", "Plasma Rifle",
                               "Rocket Launcher", "Ballista", "Chaingun", "Super Shotgun"],
                               "replacement_item": None, "link_replacement": False}]}
    mw = setup_multiworld([DoomEternalWorld, DoomEternalWorld], steps=gen_steps[:-1], seed=42, options=options)
    original = {id(item) for item in mw.itempool}
    mw.set_item_links()
    mw.link_items()
    replacements = [item for item in mw.itempool if id(item) not in original and item.player in mw.player_ids]
    assert len(replacements) == 6
    assert {item.name for item in replacements} == {"Small Health"}
    assert all(not item.advancement for item in replacements)


def test_replacement_reports_disabled_filler_weights():
    mw = setup_multiworld(DoomEternalWorld, steps=(), seed=42, options={
        "filler_weights": dict.fromkeys(FILLER_WEIGHT_NAMES, 0), "trap_percentage": 100,
    })
    with pytest.raises(OptionError, match="positive weight for replacement items"):
        mw.worlds[1].create_filler()


@pytest.mark.parametrize("kills_first", [True, False])
def test_killsanity_core_search_retries_source_dependencies(kills_first):
    mw = setup_multiworld(DoomEternalWorld, steps=gen_steps[:-1], seed=42, options={
        **CAMPAIGN, "mission_order": "vanilla_order", "killsanity": True,
        "kills_per_check": 1, "killsanity_maximum_milestones": 1,
    })
    menu = mw.get_region("Menu", 1)
    exits = sorted(menu.exits, key=lambda entrance: (entrance.connected_region.name == "Killsanity") != kills_first)
    menu.exits = exits
    state = CollectionState(mw)
    for item in mw.itempool:
        state.collect(item, True)
    assert state.can_reach_location("Kill Reward 0001", 1)


@pytest.mark.parametrize(("overrides", "message"), [
    ({"use_dlc_content": False, "item_pool_counts": {"Desperate Punch": 1}}, "unavailable in this campaign"),
    ({"use_dlc_content": False, "item_pool_counts": {"Progressive Sentinel Hammer": 1}},
     "unavailable in this campaign"),
    ({"item_pool_counts": {"Super Shotgun": 0}}, "requires Super Shotgun"),
    ({"item_pool_counts": {"Sticky Bombs": 0, "Sticky Bombs Mastery": 0}}, "required by active challenges"),
    ({"item_pool_counts": {"Weapon Upgrade Points (3)": 0}}, "do not cover active mastery challenges"),
    ({"start_inventory": {"Sentinel Battery Bundle": 1}}, "belongs to legacy rooms"),
    ({"start_inventory": {"Sentinel Battery": 100}}, "starting inventory exceeds"),
    ({"item_pool_counts": {**dict.fromkeys(POOL_ITEM_LIMITS, 0), "Meat Hook": 1, "Super Shotgun": 1,
                           "Precision Bolt": 1, "Heavy Cannon": 1}, "logic_difficulty": "expert",
      "include_weapon_mastery_challenges": False},
     "cannot satisfy campaign readiness"),
])
def test_pool_configuration_errors_reach_apworld_boundary(overrides, message):
    mw = setup_multiworld(DoomEternalWorld, steps=(), seed=42, options={**CAMPAIGN, **overrides})
    with pytest.raises(OptionError, match=message) as raised:
        mw.worlds[1].generate_early()
    assert isinstance(raised.value.__cause__, ValueError)
    assert str(raised.value) == str(raised.value.__cause__)


def test_web_option_groups_cover_game_options_once():
    groups = get_option_groups(DoomEternalWorld)
    expected = {"Campaign and Missions", "Items and Pool", "Enemies", "Killsanity", "Difficulty", "Extras"}
    assert expected <= groups.keys()
    grouped = Counter(option for group in DoomEternalWorld.web.option_groups if group.name in expected
                      for option in group.options)
    assert all(count == 1 for count in grouped.values())
    assert set(grouped) == {DoomEternalWorld.options_dataclass.type_hints[name]
                            for name in DoomEternalWorld.options_dataclass.__annotations__.keys()
                            - {"start_inventory", "start_inventory_from_pool"}}
    assert {"start_inventory", "start_inventory_from_pool"} <= groups["Item & Location Options"].keys()


@pytest.mark.parametrize("order", ["random_mission_order", "mission_access_as_items"])
def test_spoiler_describes_generated_campaign(order):
    mw = setup_multiworld(DoomEternalWorld, seed=42, options={**CAMPAIGN, "mission_order": order})
    world = mw.worlds[1]
    output = StringIO()
    world.write_spoiler(output)
    text = output.getvalue()
    assert "Tester1" in text
    assert world.options.mission_order.current_option_name in text
    sequence = " -> ".join(STAGE_BY_ID[stage]["name"] for stage in world.campaign_plan["sequence"])
    assert sequence in text
    assert world.options.goal.current_option_name in text
    assert world.options.enemy_preset.current_option_name in text
    assert "{" not in text
    assert_spoiler_access(world, text)
    assert_spoiler_preparation(world, text)


def assert_spoiler_access(world, text):
    for stage in world.campaign_plan["access_items"].values():
        name = STAGE_BY_ID[stage]["name"]
        assert f"{name}: {name} Access" in text


def assert_spoiler_preparation(world, text):
    for name in world.campaign_plan["bootstrap_placed_items"] + world.campaign_plan["opening_placed_items"]:
        assert name in text
        placements = [location for location in world.multiworld.get_filled_locations() if location.item.player == 1
                      and location.item.name == name]
        assert placements
        assert any(location.name in text for location in placements)
