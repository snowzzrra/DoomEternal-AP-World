from types import SimpleNamespace

import pytest

from BaseClasses import Item, ItemClassification, MultiWorld, Region
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
    progression = Item('Progression', ItemClassification.progression, None, 1)
    assert all(check.item_rule(progression) for check in region.locations[:3])
    assert not region.locations[3].item_rule(progression)
    assert region.locations[3].item_rule(Item('Useful', ItemClassification.useful, None, 1))
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








def test_source_cannot_borrow_another_missions_access():
    world = world_with_kill_rewards()
    region = Region("Exultia - Hell - Ichor Expanse", 1, world.multiworld)
    world.multiworld.regions.append(region)
    world.killsanity_plan["finite_sources"][0]["region"] = region.name
    with pytest.raises(ValueError, match="another mission"):
        create_killsanity_locations(world)
