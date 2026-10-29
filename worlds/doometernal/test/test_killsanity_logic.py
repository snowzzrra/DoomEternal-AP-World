from types import SimpleNamespace

import pytest

from BaseClasses import Item, ItemClassification, MultiWorld, PlandoOptions, Region
from Options import ExcludeLocations, PlandoItems, StartLocationHints
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.campaign import completion_event, STAGE_BY_ID
from worlds.doometernal.killsanity_logic import build_kill_rewards, create_killsanity_locations
from worlds.doometernal.locations import kill_reward_name_to_id


def world_with_kill_rewards():
    multiworld = MultiWorld(1)
    menu = Region("Menu", 1, multiworld)
    multiworld.regions.append(menu)
    world = SimpleNamespace(
        multiworld=multiworld, player=1,
        killsanity_plan=build_kill_rewards({"enabled": True, "interval": 100, "maximum_milestones": 4}, [
            {"source_id": "intro", "map_key": list(STAGE_BY_ID)[0], "count": 100, "repeatable": True},
            {"source_id": "exultia", "map_key": list(STAGE_BY_ID)[1], "count": 250, "repeatable": True},
        ]),
        campaign_plan={"stage_ids": list(STAGE_BY_ID)[:2]},
    )
    return world


def test_each_progression_milestone_requires_its_distinct_finite_budget():
    world = world_with_kill_rewards()
    create_killsanity_locations(world)
    region = world.multiworld.get_region("Killsanity", 1)
    def available(completed):
        state = SimpleNamespace(has=lambda event, player: player == 1 and event in completed)
        return [check.name for check in region.locations if check.access_rule(state)]
    assert available(set()) == []
    first, second = map(completion_event, world.campaign_plan["stage_ids"])
    assert available({first}) == ["Kill Reward 0001", "Kill Reward 0004"]
    assert available({second}) == ["Kill Reward 0001", "Kill Reward 0002", "Kill Reward 0004"]
    assert len(available({first, second})) == 4
    progression = Item('Progression', ItemClassification.progression, None, 1)
    assert all(check.item_rule(progression) for check in region.locations[:3])
    assert not region.locations[3].item_rule(progression)
    assert region.locations[3].item_rule(Item('Useful', ItemClassification.useful, None, 1))
    assert DoomEternalWorld.location_id_to_name[2_200_000_004] == "Kill Reward 0004"
    assert "Kill Reward 0004" in DoomEternalWorld.location_name_groups["Everywhere"]


def test_replay_only_milestones_require_a_repeatable_completed_source():
    world = world_with_kill_rewards()
    for source in world.killsanity_plan["finite_sources"]:
        source["repeatable"] = False
    create_killsanity_locations(world)
    region = world.multiworld.get_region("Killsanity", 1)
    state = SimpleNamespace(has=lambda *args: True)
    assert all(check.access_rule(state) for check in region.locations[:3])
    assert not region.locations[3].access_rule(state)








def test_source_cannot_borrow_another_missions_access():
    world = world_with_kill_rewards()
    region = Region("Exultia - Hell - Ichor Expanse", 1, world.multiworld)
    world.multiworld.regions.append(region)
    world.killsanity_plan["finite_sources"][0]["region"] = region.name
    with pytest.raises(ValueError, match="another mission"):
        create_killsanity_locations(world)


def test_reward_names_resolve_before_generation():
    names = {"Kill Reward 0001", "Kill Reward 2000"}
    for option_type in (ExcludeLocations, StartLocationHints):
        option = option_type.from_any(names)
        option.verify(DoomEternalWorld, "Tester", PlandoOptions.items)
        assert option.value == names
    plando = PlandoItems.from_any([{"item": "Small Health", "location": "Kill Reward 0001"}])
    plando.verify(DoomEternalWorld, "Tester", PlandoOptions.items)
    group = ExcludeLocations.from_any({"Killsanity"})
    group.verify(DoomEternalWorld, "Tester", PlandoOptions.items)
    assert group.value == set(kill_reward_name_to_id)
    package = DoomEternalWorld.get_data_package_data()
    assert package["location_name_to_id"]["Kill Reward 2000"] == 2_200_002_000


def test_reward_identities_stay_fixed_across_intervals():
    checks = []
    for interval in (25, 100):
        world = world_with_kill_rewards()
        world.killsanity_plan = build_kill_rewards(
            {"enabled": True, "interval": interval, "maximum_milestones": 4},
            world.killsanity_plan["finite_sources"])
        create_killsanity_locations(world)
        checks.append(world.multiworld.get_region("Killsanity", 1).locations)
    assert [(loc.name, loc.address) for loc in checks[0]] == [(loc.name, loc.address) for loc in checks[1]]
    assert checks[0][0].display_name == "Killed 25 Enemies"
    assert checks[1][0].display_name == "Killed 100 Enemies"


def test_registered_reward_limit_constructs_last_reward():
    world = world_with_kill_rewards()
    world.killsanity_plan = build_kill_rewards(
        {"enabled": True, "interval": 100, "maximum_milestones": 2000}, world.killsanity_plan["finite_sources"])
    create_killsanity_locations(world)
    checks = world.multiworld.get_region("Killsanity", 1).locations
    assert len(checks) == 2000
    assert (checks[-1].name, checks[-1].address) == ("Kill Reward 2000", 2_200_002_000)
