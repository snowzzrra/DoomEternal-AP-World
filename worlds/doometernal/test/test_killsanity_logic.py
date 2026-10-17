from types import SimpleNamespace

from BaseClasses import LocationProgressType, MultiWorld, Region
from worlds.doometernal.campaign import completion_event, STAGE_BY_ID
from worlds.doometernal.killsanity_logic import create_killsanity_locations
from worlds.doometernal.killsanity_plan import build_killsanity_plan


def world_with_kill_rewards():
    multiworld = MultiWorld(1)
    menu = Region("Menu", 1, multiworld)
    multiworld.regions.append(menu)
    world = SimpleNamespace(
        multiworld=multiworld, player=1,
        killsanity_plan=build_killsanity_plan({"enabled": True, "interval": 100, "maximum_milestones": 4}, [
            {"source_id": "intro", "map_key": list(STAGE_BY_ID)[0], "count": 100, "repeatable": True},
            {"source_id": "exultia", "map_key": list(STAGE_BY_ID)[1], "count": 250, "repeatable": True},
        ]),
        campaign_plan={"stage_ids": list(STAGE_BY_ID)[:2]},
        location_name_to_id={}, location_name_groups={},
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
    assert available({first}) == ["Killed 100 Enemies", "Killed 400 Enemies"]
    assert available({second}) == ["Killed 100 Enemies", "Killed 200 Enemies", "Killed 400 Enemies"]
    assert len(available({first, second})) == 4
    assert all(check.progress_type != LocationProgressType.EXCLUDED for check in region.locations[:3])
    assert region.locations[3].progress_type == LocationProgressType.EXCLUDED
    assert world.location_id_to_name[7800400] == "Killed 400 Enemies"
    assert "Killed 400 Enemies" in world.location_name_groups["Everywhere"]


def test_replay_only_milestones_require_a_repeatable_completed_source():
    world = world_with_kill_rewards()
    for source in world.killsanity_plan["finite_sources"]:
        source["repeatable"] = False
    create_killsanity_locations(world)
    region = world.multiworld.get_region("Killsanity", 1)
    state = SimpleNamespace(has=lambda *args: True)
    assert all(check.access_rule(state) for check in region.locations[:3])
    assert not region.locations[3].access_rule(state)


def test_disabled_killsanity_leaves_the_campaign_regions_alone():
    world = world_with_kill_rewards()
    world.killsanity_plan = build_killsanity_plan({})
    create_killsanity_locations(world)
    assert len(world.multiworld.regions) == 1
