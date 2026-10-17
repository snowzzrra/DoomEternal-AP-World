from BaseClasses import LocationProgressType, Region

from .campaign import completion_event
from .killsanity_plan import milestone_name, milestone_names
from .locations import DoomEternalLocation


def create_killsanity_locations(world):
    plan = world.killsanity_plan
    if not plan["milestones"]:
        return
    multiworld, player = world.multiworld, world.player
    budgets, replay_events = {}, set()
    for row in plan["finite_sources"]:
        event = completion_event(row["map_key"])
        budgets[event] = budgets.get(event, 0) + row["count"]
        if row["repeatable"]:
            replay_events.add(event)
    region = Region("Killsanity", player, multiworld)
    multiworld.regions.append(region)
    entrance = multiworld.get_region("Menu", player).connect(region)
    entrance.access_rule = lambda state: any(state.has(event, player) for event in budgets)
    for row in plan["milestones"]:
        threshold = row["threshold"]
        location = DoomEternalLocation(player, milestone_name(threshold), row["location_id"], region)
        if row["finite_supported"]:
            location.access_rule = lambda state, threshold=threshold: sum(
                count for event, count in budgets.items() if state.has(event, player)) >= threshold
        else:
            location.progress_type = LocationProgressType.EXCLUDED
            location.access_rule = lambda state: any(
                state.has(event, player) for event in replay_events)
        region.locations.append(location)

    world.location_name_to_id = {**world.location_name_to_id, **milestone_names(plan)}
    world.location_id_to_name = {code: name for name, code in world.location_name_to_id.items()}
    world.location_names = frozenset(world.location_name_to_id)
    world.location_name_groups = {**world.location_name_groups, "Everywhere": world.location_names}
