from types import SimpleNamespace

from BaseClasses import MultiWorld, Region

from worlds.doometernal.campaign import STAGE_BY_ID
from worlds.doometernal.killsanity_logic import build_kill_rewards, create_killsanity_locations


def world_with_kill_rewards():
    multiworld = MultiWorld(1)
    menu = Region("Menu", 1, multiworld)
    multiworld.regions.append(menu)
    return SimpleNamespace(
        multiworld=multiworld,
        player=1,
        killsanity_plan=build_kill_rewards(
            {"enabled": True, "interval": 100, "maximum_milestones": 4},
            [
                {"source_id": "intro", "map_key": next(iter(STAGE_BY_ID)), "count": 100, "repeatable": True},
                {"source_id": "exultia", "map_key": list(STAGE_BY_ID)[1], "count": 250, "repeatable": True},
            ],
        ),
        campaign_plan={"stage_ids": list(STAGE_BY_ID)[:2]},
    )


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
