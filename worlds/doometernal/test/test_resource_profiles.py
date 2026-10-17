from collections import Counter
import random

import pytest

from test.general import setup_multiworld
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.items import FILLER_WEIGHT_NAMES, SAFE_TRAP_NAMES, suit_perk_item_names
from worlds.doometernal.combat_rating import ALL_MOD_NAMES
from worlds.doometernal.options import ItemPoolCounts, ResourceProfile
from worlds.doometernal.planner import ITEM_DEPENDENCIES, build_semantic_counts
from worlds.doometernal import campaign as campaign_module
from worlds.doometernal import logic


CAMPAIGN = {"mission_pool": "custom", "custom_missions": {"Hell on Earth", "Exultia", "Final Sin"},
            "mission_count": 3, "goal": "kill_the_icon_of_sin", "mission_order": "random_mission_order"}


@pytest.mark.parametrize("campaign", [CAMPAIGN, {
    "mission_pool": "custom", "custom_missions": {"The Holt", "The World Spear", "Immora"},
    "mission_count": 3, "goal": "kill_the_dark_lord", "mission_order": "random_mission_order",
}], ids=["base", "dlc"])
def test_resource_profiles_generate_bounded_campaigns_with_variety(campaign):
    totals = {}
    for profile in ("balanced", "generous", "lean"):
        mw = setup_multiworld(DoomEternalWorld, seed=700, options={**campaign, "resource_profile": profile})
        world = mw.worlds[1]
        counts = Counter(world.campaign_plan["semantic_counts"])
        totals[profile] = sum(counts.values())
        assert world.campaign_plan["readiness_final_deficit"] <= 0
        assert len(mw.itempool) == len([loc for loc in mw.get_locations(1) if loc.address is not None])
        assert len({name for name in counts if name.endswith(" Mastery")}) >= 2
        assert all(counts[f"Progressive {stat} Upgrade"] <= 4 for stat in ("Health", "Armor", "Ammo"))
        if profile != "lean" and not world.campaign_plan["resource_auto_adjustments"]:
            for weapon in ("Combat Shotgun", "Heavy Cannon", "Plasma Rifle", "Rocket Launcher", "Ballista", "Chaingun"):
                assert any(counts[mod] and weapon in ITEM_DEPENDENCIES.get(mod, ()) for mod in ALL_MOD_NAMES)
        for weapon in ("Combat Shotgun", "Heavy Cannon", "Plasma Rifle", "Rocket Launcher", "Super Shotgun", "Ballista", "Chaingun"):
            assert counts[weapon] or world.campaign_plan["starting_weapon"] == weapon
    assert totals["generous"] >= totals["balanced"] >= totals["lean"]
    if campaign == CAMPAIGN:
        assert totals["generous"] > totals["lean"]


def test_resource_neutral_pickups_do_not_increase_permanent_resources(monkeypatch):
    mw = setup_multiworld(DoomEternalWorld, seed=704, options={**CAMPAIGN, "resource_profile": "generous"})
    world = mw.worlds[1]
    with_pickups = campaign_module.make_plan(world.options, random.Random(700), world)
    monkeypatch.setattr(campaign_module, "location_data_table", {
        name: data for name, data in campaign_module.location_data_table.items()
        if name not in campaign_module.RESOURCE_NEUTRAL_LOCATION_NAMES
    })
    without_pickups = campaign_module.make_plan(world.options, random.Random(700), world)
    assert with_pickups["semantic_counts"] == without_pickups["semantic_counts"]
    assert with_pickups["resource_permanent_budget"] == without_pickups["resource_permanent_budget"]


def test_explicit_suits_and_start_inventory_keep_counts_when_checks_change():
    counts_by_checks = []
    for checks in (False, True):
        mw = setup_multiworld(DoomEternalWorld, seed=701, options={
            **CAMPAIGN, "include_secret_encounters": checks, "praetor_suit_upgrades_in_pool": 4,
            "start_inventory": {"Progressive Health Upgrade": 2},
            "item_pool_counts": {"Progressive Health Upgrade": 4}, "enabled_traps": set(),
        })
        items = Counter(item.name for item in mw.itempool + mw.precollected_items[1])
        # setup_multiworld runs world hooks; AP core materializes Starting Inventory separately.
        items.update(mw.worlds[1].options.start_inventory.value)
        assert items["Progressive Health Upgrade"] == 4
        assert sum(items[name] for name in suit_perk_item_names) == 4
        counts_by_checks.append(mw.worlds[1].campaign_plan["semantic_counts"])
    assert counts_by_checks[0] == counts_by_checks[1]


def test_override_dependency_conflicts_and_invalid_native_tiers_are_rejected():
    with pytest.raises(ValueError, match="requires Ballista"):
        setup_multiworld(DoomEternalWorld, seed=702, options={
            **CAMPAIGN, "item_pool_counts": {"Arbalest": 1, "Ballista": 0},
        })
    for value in ({"Progressive Health Upgrade": 5}, {"Air Control": 2}, {"Ballista": True}):
        with pytest.raises(ValueError, match="invalid override"):
            ItemPoolCounts.from_any(value)


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


def test_disabling_mastery_locations_preserves_items_hosts_and_upgrade_currency():
    resources = []
    for challenges in (True, False):
        mw = setup_multiworld(DoomEternalWorld, seed=706, options={**CAMPAIGN, "include_weapon_mastery_challenges": challenges})
        assert bool(mw.worlds[1].options.include_weapon_mastery_challenges.value) is challenges
        counts = Counter(mw.worlds[1].campaign_plan["semantic_counts"])
        masteries = {name for name, count in counts.items() if count and name.endswith(" Mastery")}
        names = masteries | {dep for name in masteries for dep in ITEM_DEPENDENCIES[name]} | {"Weapon Upgrade Points (3)"}
        resources.append({name: counts[name] for name in names})
    assert resources[0] == resources[1]
    mw = setup_multiworld(DoomEternalWorld, seed=706, options={
        **CAMPAIGN, "include_weapon_mastery_challenges": False,
        "item_pool_counts": {"Sticky Bombs Mastery": 0},
    })
    assert not mw.worlds[1].campaign_plan["semantic_counts"].get("Sticky Bombs Mastery", 0)


def test_mastery_currency_supports_progression_without_a_mastery_victory():
    name = "Weapon Upgrade Points (3)"
    mw = setup_multiworld(DoomEternalWorld, seed=707, options={
        "mission_pool": "full_saga", "mission_count": "all",
        "additional_victory_requirements": set(),
    })
    active = sum(location.address is not None and location.name.endswith(logic.MASTERY_SUFFIX)
                 for location in mw.get_locations(1))
    assert active == 13
    available = sum(item.name == name and item.advancement for item in mw.itempool)
    available += sum(item.name == name for item in mw.precollected_items[1])
    assert available >= 3 * active


def test_full_trap_padding_accepts_zero_filler_weights():
    trap = sorted(SAFE_TRAP_NAMES)[0]
    mw = setup_multiworld(DoomEternalWorld, seed=703, options={
        **CAMPAIGN, "trap_percentage": 100, "enabled_traps": {trap},
        "filler_weights": dict.fromkeys(FILLER_WEIGHT_NAMES, 0), "trap_weights": {trap: 10},
    })
    counts = Counter(item.name for item in mw.itempool)
    assert counts[trap] > 0
    assert not any(counts[name] for name in FILLER_WEIGHT_NAMES)
