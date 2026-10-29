from argparse import Namespace
from collections import Counter
from unittest.mock import patch

import pytest

from BaseClasses import PlandoOptions
from Main import main
from Options import OptionError
from test.general import setup_multiworld
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.items import item_name_to_id
from worlds.doometernal.slot_data import build_slot_data


CAMPAIGN = {
    "mission_pool": "base", "mission_count": "all", "mission_order": "vanilla_order",
    "goal": "kill_the_icon_of_sin", "enemy_randomizer": False,
    "randomize_dash": True, "randomize_chainsaw": True,
}


def core_args(options):
    args = Namespace(multi=1, outputpath=None, race=False, outputname=None, plando=PlandoOptions.none,
        game={1: DoomEternalWorld.game}, name={1: "Starting items"}, sprite={}, sprite_pool={},
        csv_output=False, skip_output=True, spoiler_only=False, skip_prog_balancing=True)
    for name, option in DoomEternalWorld.options_dataclass.type_hints.items():
        setattr(args, name, {1: option.from_any(options.get(name, option.default))})
    return args


@pytest.fixture(scope="module")
def core_world():
    options = {**CAMPAIGN, "mission_pool": "custom", "mission_count": 6,
        "custom_missions": {"Exultia", "Cultist Base", "Doom Hunter Base", "Super Gore Nest", "ARC Complex", "Final Sin"},
        "randomize_chainsaw": False,
        "start_inventory": {"Flame Belch": 1, "Progressive Health Upgrade": 1, "Progressive Blood Punch": 2},
        "start_inventory_from_pool": {"Ice Bomb": 1, "Progressive Health Upgrade": 2, "Progressive Blood Punch": 2}}
    before = Counter()

    def record_pool(world):
        before.update(item.name for item in world.multiworld.itempool)

    with patch.object(DoomEternalWorld, "generate_basic", record_pool), \
            patch.object(DoomEternalWorld, "create_filler", autospec=True,
                         side_effect=DoomEternalWorld.create_filler) as replace:
        mw = main(core_args(options), seed=42, baked_server_options={"test": True})
    return mw, before, replace.call_count


def test_additive_start_keeps_pool_copies(core_world):
    mw, before, _ = core_world
    placed = Counter(loc.item.name for loc in mw.get_filled_locations(1) if loc.address is not None)
    assert before["Flame Belch"] == placed["Flame Belch"] == 1
    assert before["Progressive Health Upgrade"] == 4
    assert Counter(item.name for item in mw.precollected_items[1])["Flame Belch"] == 1


def test_core_removes_from_pool_once_and_replacements_conserve_locations(core_world):
    mw, before, replacements = core_world
    placed = Counter(loc.item.name for loc in mw.get_filled_locations(1) if loc.address is not None)
    assert (before["Ice Bomb"], placed["Ice Bomb"]) == (1, 0)
    assert placed["Progressive Health Upgrade"] == 2
    assert placed["Progressive Blood Punch"] == 2
    assert replacements == 5
    assert sum(before.values()) == sum(placed.values())
    assert not mw.get_unfilled_locations(1)
    assert mw.can_beat_game()


def test_exported_starting_block_equals_precollected_items(core_world):
    mw, _, _ = core_world
    world = mw.worlds[1]
    actual = Counter(item.code for item in mw.precollected_items[1])
    data = build_slot_data(world)
    assert data["starting"] == {
        "items": sorted([code, count] for code, count in actual.items()),
        "weapon_item_id": item_name_to_id[world.starting_weapon_name],
    }
    assert actual[data["starting"]["weapon_item_id"]] == 1
    assert actual[item_name_to_id["Progressive Health Upgrade"]] == 3
    assert actual[item_name_to_id["Progressive Blood Punch"]] == 4
    assert actual[item_name_to_id["Chainsaw"]] == 1
    assert data["tracker_options"]["start_inventory_from_pool"] == world.options.start_inventory_from_pool.value


@pytest.mark.parametrize("name,first,second", [
    ("Progressive Blood Punch", 2, 3), ("Progressive Health Upgrade", 3, 2),
    ("Progressive Armor Upgrade", 4, 1), ("Progressive Ammo Upgrade", 1, 4),
    ("Progressive Special Weapon", 1, 3), ("Faster Weapon Swap", 1, 1),
])
def test_combined_tier_limits_are_enforced(name, first, second):
    mw = setup_multiworld(DoomEternalWorld, steps=(), seed=42, options={**CAMPAIGN,
        "start_inventory": {name: first}, "start_inventory_from_pool": {name: second}})
    with pytest.raises(OptionError, match="invalid quantity"):
        mw.worlds[1].generate_early()


@pytest.mark.parametrize("source", ["start_inventory", "start_inventory_from_pool"])
def test_early_readiness_includes_both_sources(source):
    equipment = {"Super Shotgun": 1, "Meat Hook": 1, "Ice Bomb": 1}
    mw = setup_multiworld(DoomEternalWorld, steps=(), seed=42, options={**CAMPAIGN,
        "mission_pool": "dlc_only", "mission_count": 6, "goal": "kill_the_dark_lord",
        source: equipment})
    world = mw.worlds[1]
    world.generate_early()
    assert set(equipment) <= world.initial_logical_items
    assert not (set(equipment) & set(world.campaign_plan["bootstrap_placed_items"]))


@pytest.mark.parametrize("requested,overrides", [
    ({"Progressive Blood Punch": 5}, {}),
    ({"Progressive Health Upgrade": 2}, {"Progressive Health Upgrade": 1}),
    ({"Ice Bomb": 1}, {"Ice Bomb": 0}),
    ({"Slayer Gate Key The Holt": 1}, {}),
])
def test_from_pool_over_available_copies_raises_option_error(requested, overrides):
    mw = setup_multiworld(DoomEternalWorld, steps=(), seed=42, options={**CAMPAIGN,
        "start_inventory_from_pool": requested, "item_pool_counts": overrides})
    with pytest.raises(OptionError, match="eligible pool copies"):
        mw.worlds[1].generate_early()


@pytest.mark.parametrize("source", ["start_inventory", "start_inventory_from_pool"])
@pytest.mark.parametrize("quantity", [-1, True, "2"])
def test_invalid_quantities_are_rejected_before_planning(source, quantity):
    mw = setup_multiworld(DoomEternalWorld, steps=(), seed=42, options=CAMPAIGN)
    getattr(mw.worlds[1].options, source).value["Progressive Blood Punch"] = quantity
    with pytest.raises(OptionError, match="invalid quantity"):
        mw.worlds[1].generate_early()


@pytest.mark.parametrize("source", ["start_inventory", "start_inventory_from_pool"])
@pytest.mark.parametrize("name,options", [
    ("Imp Trap", {}), ("Small Health", {}), ("Victory", {}),
    ("Desperate Punch", {"use_dlc_content": False}),
    ("The Crucible", {"special_weapon": "progressive_special_weapon"}),
    ("Dash", {"randomize_dash": False}), ("Chainsaw", {"randomize_chainsaw": False}),
])
def test_both_sources_enforce_item_legality(source, name, options):
    mw = setup_multiworld(DoomEternalWorld, steps=(), seed=42,
                         options={**CAMPAIGN, **options, source: {name: 1}})
    with pytest.raises(OptionError):
        mw.worlds[1].generate_early()
