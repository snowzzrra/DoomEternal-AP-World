

import pytest

from test.general import setup_multiworld
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.options import ItemPoolCounts, ResourceProfile
from worlds.doometernal.planner import build_semantic_counts
from worlds.doometernal import campaign as campaign_module
from worlds.doometernal import logic
from worlds.doometernal.combat_rating import NORMAL_RUNE_NAMES, SUPPORT_RUNE_NAMES
from worlds.doometernal.items import suit_perk_item_names


CAMPAIGN = {"mission_pool": "custom", "custom_missions": {
    "Hell on Earth", "Exultia", "Cultist Base", "Super Gore Nest", "ARC Complex", "Final Sin"},
    "mission_count": 6, "goal": "kill_the_icon_of_sin", "mission_order": "random_mission_order"}


@pytest.mark.parametrize("source,remaining", [("start_inventory", 4), ("start_inventory_from_pool", 2)])
def test_starting_sources_keep_separate_pool_forecasts(source, remaining):
    mw = setup_multiworld(DoomEternalWorld, steps=(), seed=705, options={**CAMPAIGN,
        source: {"Progressive Health Upgrade": 2}})
    pool = build_semantic_counts(
        mw.worlds[1].options, active_normal_ids=('e1m1_intro',), starting_weapon='Combat Shotgun',
        active_sg=(), active_masteries_count=0, battery_surplus=0, targets=(),
    )
    assert pool.placement_counts['Progressive Health Upgrade'] == remaining
    assert pool.total_counts['Progressive Health Upgrade'] == 4










def test_hard_quantities_and_explicit_items_survive_auto_budget(monkeypatch):
    mw = setup_multiworld(DoomEternalWorld, seed=705, options=CAMPAIGN)
    options = mw.worlds[1].options
    options.resource_profile = ResourceProfile.from_any("generous")
    options.item_pool_counts = ItemPoolCounts.from_any({"Progressive Armor Upgrade": 4})
    requirement = logic.LocationRequirement(
        all_of=("Progressive Health Upgrade",),
        custom_rule=lambda state, player: state.has("Progressive Health Upgrade", player, 3),
    )
    monkeypatch.setattr(logic, "build_location_prerequisites", lambda *args, **kwargs: {"quantity": requirement})
    pool = build_semantic_counts(
        options, active_normal_ids=tuple(stage["id"] for stage in campaign_module.CAMPAIGN_STAGES
                                        if stage["source"] == "base")[:6],
        starting_weapon="Combat Shotgun", active_sg=(), active_masteries_count=0,
        battery_surplus=0, targets=(), placement_budget=0,
    )
    assert pool.total_counts["Progressive Health Upgrade"] >= 3
    assert pool.total_counts["Progressive Armor Upgrade"] == 4


def test_short_campaign_keeps_all_upgrades_instead_of_fillers():
    mw = setup_multiworld(DoomEternalWorld, seed=705, options=CAMPAIGN)
    options = mw.worlds[1].options
    pool = build_semantic_counts(
        options, active_normal_ids=('e1m1_intro',), starting_weapon='Combat Shotgun',
        active_sg=(), active_masteries_count=0, battery_surplus=0, targets=(),
        suit_counts={name: 1 for name in suit_perk_item_names}, placement_budget=156,
    )
    for name in NORMAL_RUNE_NAMES | SUPPORT_RUNE_NAMES | set(suit_perk_item_names):
        assert pool.total_counts[name] == 1
    assert all(pool.total_counts[f'Progressive {stat} Upgrade'] == 4 for stat in ('Health', 'Armor', 'Ammo'))
    assert pool.total_counts['Faster Weapon Swap'] == 1
