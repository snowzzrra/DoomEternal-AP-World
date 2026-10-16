from BaseClasses import Region

from .campaign import completion_event
from .killsanity_plan import milestone_name, milestone_names
from .locations import DoomEternalLocation


def create_killsanity_locations(world):
    plan = world.killsanity_plan
    if not plan["milestones"]:
        return
    multiworld, player = world.multiworld, world.player
    region = Region("Killsanity", player, multiworld)
    multiworld.regions.append(region)
    entrance = multiworld.get_region("Menu", player).connect(region)
    events = tuple(completion_event(stage) for stage in world.campaign_plan["stage_ids"])
    # finishing one mission provides repeatable fights for the remaining kill rewards.
    entrance.access_rule = lambda state: any(state.has(event, player) for event in events)
    for row in plan["milestones"]:
        threshold = row["threshold"]
        location = DoomEternalLocation(player, milestone_name(threshold), row["location_id"], region)
        region.locations.append(location)

    world.location_name_to_id = {**world.location_name_to_id, **milestone_names(plan)}
    world.location_id_to_name = {code: name for name, code in world.location_name_to_id.items()}
    world.location_names = frozenset(world.location_name_to_id)
    world.location_name_groups = {**world.location_name_groups, "Everywhere": world.location_names}
