from types import SimpleNamespace

import pytest

from BaseClasses import CollectionState, Item, ItemClassification, MultiWorld, Region
from worlds.AutoWorld import World
from worlds.doometernal.campaign import completion_event, STAGE_BY_ID
from worlds.doometernal.killsanity_logic import create_killsanity_locations
from worlds.doometernal.killsanity_plan import build_killsanity_plan
from worlds.doometernal.locations import DoomEternalLocation


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


def test_disabled_killsanity_leaves_the_campaign_regions_alone():
    world = world_with_kill_rewards()
    world.killsanity_plan = build_killsanity_plan({})
    create_killsanity_locations(world)
    assert len(world.multiworld.regions) == 1


def test_estimated_rewards_without_guaranteed_sources_require_replay():
    world = world_with_kill_rewards()
    world.killsanity_plan = build_killsanity_plan(
        {"enabled": True, "interval": 100, "maximum_milestones": "auto"},
        [], estimated_kills=1000)
    create_killsanity_locations(world)
    region = world.multiworld.get_region("Killsanity", 1)
    assert len(region.locations) == 11
    for player in (1, 2):
        progression = Item('Progression', ItemClassification.progression, None, player)
        assert not any(check.item_rule(progression) for check in region.locations)
    completed = set()
    state = SimpleNamespace(has=lambda event, player: player == 1 and event in completed)
    entrance = world.multiworld.get_region("Menu", 1).exits[0]
    assert not entrance.access_rule(state)
    assert not any(check.access_rule(state) for check in region.locations)
    completed.add(completion_event(world.campaign_plan["stage_ids"][0]))
    assert entrance.access_rule(state)
    assert all(check.access_rule(state) for check in region.locations)


def test_optional_source_needs_its_fight_and_kit_instead_of_mission_completion():
    world = world_with_kill_rewards()
    multiworld = world.multiworld
    multiworld.worlds[1] = World(multiworld, 1)
    multiworld.worlds[1].game = "DOOM Eternal"
    gate = Region("Exultia - Hell - Ichor Expanse", 1, multiworld)
    multiworld.regions.append(gate)
    multiworld.get_region("Menu", 1).connect(gate).access_rule = lambda state: state.has(
        "Slayer Gate Key Exultia", 1)
    gate.locations.append(DoomEternalLocation(1, "Exultia - Slayer Gate Complete", None, gate))
    source = world.killsanity_plan["finite_sources"][1]
    source.update(location="Exultia - Slayer Gate Complete", required_items=["Plasma Rifle", "Microwave Beam"])
    create_killsanity_locations(world)
    reward = multiworld.get_location("Killed 200 Enemies", 1)
    state = CollectionState(multiworld)
    for name in map(completion_event, world.campaign_plan["stage_ids"]):
        state.collect(Item(name, ItemClassification.progression, None, 1))
    assert not reward.can_reach(state)
    for name in ("Slayer Gate Key Exultia", "Plasma Rifle"):
        state.collect(Item(name, ItemClassification.progression, None, 1))
    assert not reward.can_reach(state)
    state.collect(Item("Microwave Beam", ItemClassification.progression, None, 1))
    assert reward.can_reach(state)
    replay_reward = multiworld.get_location("Killed 400 Enemies", 1)
    assert replay_reward.can_reach(state)
    for name in map(completion_event, world.campaign_plan["stage_ids"]):
        state.remove(Item(name, ItemClassification.progression, None, 1))
    assert reward.can_reach(state)
    assert not replay_reward.can_reach(state)


def test_source_cannot_borrow_another_missions_access():
    world = world_with_kill_rewards()
    region = Region("Exultia - Hell - Ichor Expanse", 1, world.multiworld)
    world.multiworld.regions.append(region)
    world.killsanity_plan["finite_sources"][0]["region"] = region.name
    with pytest.raises(ValueError, match="another mission"):
        create_killsanity_locations(world)


@pytest.mark.parametrize('pool, count, enemy, multiplier, interval, maximum, order, enabled', [
    ('base', 3, False, 100, 100, 'auto', 'random_mission_order', False),
    ('base', 3, False, 100, 100, 'auto', 'random_mission_order', True),
    ('base', 3, True, 50, 100, 'auto', 'random_mission_order', True),
    ('base', 3, True, 100, 100, 'auto', 'mission_access_as_items', True),
    ('base', 3, True, 200, 100, 'auto', 'random_mission_order', True),
    ('dlc_only', 3, True, 100, 100, 'auto', 'random_mission_order', True),
    ('full_saga', 'all', True, 100, 1, 'auto', 'random_mission_order', True),
    ('base', 3, False, 100, 100, 75, 'random_mission_order', True),
])
def test_campaign_budget_reaches_locations_fill_and_slot_data(
        pool, count, enemy, multiplier, interval, maximum, order, enabled):
    from Fill import distribute_items_restrictive
    from test.general import setup_multiworld
    from worlds.doometernal import DoomEternalWorld
    from worlds.doometernal.killsanity_plan import build_campaign_kill_budget, milestone_name, validate_killsanity_plan

    options = dict(mission_pool=pool, mission_count=count, mission_order=order,
                   goal='kill_the_dark_lord' if pool == 'dlc_only' else 'kill_the_icon_of_sin',
                   use_dlc_content=False, enemy_randomizer=enemy, enemy_count_mode='multiplier',
                   enemy_count_multiplier=multiplier, killsanity=enabled, kills_per_check=interval,
                   killsanity_maximum_milestones=maximum)
    multiworld = setup_multiworld(DoomEternalWorld, seed=71430, options=options)
    world = multiworld.worlds[1]
    plan = world.killsanity_plan
    rewards = [location for location in multiworld.get_locations(1) if location.parent_region.name == 'Killsanity']
    if not enabled:
        assert not rewards and not plan['milestones']
        return
    budget = build_campaign_kill_budget(world.campaign_plan, world.enemy_plan)
    assert plan['estimated_kills'] == budget['estimated_kills']
    assert plan['finite_sources'] == budget['finite_sources']
    assert len(rewards) == (min(50, plan['estimated_kills'] * 110 // (interval * 100))
                            if maximum == 'auto' else maximum)
    stages = set(world.campaign_plan['stage_ids'])
    assert {row['map_key'] for row in plan['finite_sources']} <= stages
    assert (world.enemy_plan is not None) == enemy
    if enemy:
        assert world.enemy_plan['kind'] == 'native_recipes'
        assert set(world.enemy_plan['maps']) == stages
    if pool == 'base':
        assert all(not key.startswith(('e4', 'e5')) for key in stages)
    elif pool == 'dlc_only':
        assert all(key.startswith(('e4', 'e5')) for key in stages)
    if pool == 'full_saga':
        assert len(rewards) == 50
    distribute_items_restrictive(multiworld)
    assert multiworld.can_beat_game()
    reached = {location.name for sphere in multiworld.get_spheres() for location in sphere}
    for row in plan['milestones']:
        location = multiworld.get_location(milestone_name(row['threshold']), 1)
        assert location.name in reached
        if not row['finite_supported']:
            assert not location.item_rule(Item('Progression', ItemClassification.progression, None, 2))
            assert not location.item.advancement
    slot = world.fill_slot_data()
    assert slot['killsanity_options']['maximum_milestones'] == maximum
    assert validate_killsanity_plan(slot['killsanity_options'], slot['killsanity']) == plan
