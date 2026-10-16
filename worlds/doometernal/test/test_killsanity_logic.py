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
        killsanity_plan=build_killsanity_plan({"enabled": True, "interval": 100, "maximum_milestones": 4}),
        campaign_plan={"stage_ids": list(STAGE_BY_ID)[:2]},
        location_name_to_id={}, location_name_groups={},
    )
    return world


def test_replaying_one_completed_mission_makes_every_kill_reward_available():
    world = world_with_kill_rewards()
    create_killsanity_locations(world)
    region = world.multiworld.get_region("Killsanity", 1)
    assert not region.entrances[0].access_rule(SimpleNamespace(has=lambda *args: False))
    for stage in world.campaign_plan["stage_ids"]:
        completed = SimpleNamespace(has=lambda event, player: event == completion_event(stage) and player == 1)
        assert region.entrances[0].access_rule(completed)
    assert all(check.progress_type != LocationProgressType.EXCLUDED for check in region.locations)
    assert world.location_id_to_name[7800400] == "Killed 400 Enemies"
    assert "Killed 400 Enemies" in world.location_name_groups["Everywhere"]


def test_disabled_killsanity_leaves_the_campaign_regions_alone():
    world = world_with_kill_rewards()
    world.killsanity_plan = build_killsanity_plan({})
    create_killsanity_locations(world)
    assert len(world.multiworld.regions) == 1
