from BaseClasses import LocationProgressType, Region

from .campaign import completion_event, REGION_STAGE
from .items import item_data_table
from .killsanity_plan import milestone_name, milestone_names
from .locations import DoomEternalLocation


def create_killsanity_locations(world):
    plan = world.killsanity_plan
    if not plan["milestones"]:
        return
    multiworld, player = world.multiworld, world.player
    sources = []
    for row in plan["finite_sources"]:
        if row["map_key"] not in world.campaign_plan["stage_ids"]:
            raise ValueError(f"Killsanity source references an inactive mission: {row['map_key']}")
        items = tuple(row.get("required_items", ()))
        if set(items) - item_data_table.keys():
            raise ValueError(f"Killsanity source references unknown items: {row['source_id']}")
        if "location" in row:
            target = multiworld.get_location(row["location"], player)
            access_region = target.parent_region
        elif "region" in row:
            target = access_region = multiworld.get_region(row["region"], player)
        else:
            event = completion_event(row["map_key"])
            sources.append((row, lambda state, event=event, items=items: all(
                state.has(item, player) for item in items) and state.has(event, player)))
            continue
        if REGION_STAGE.get(access_region.name) != row["map_key"]:
            raise ValueError(f"Killsanity source access belongs to another mission: {row['source_id']}")
        sources.append((row, lambda state, target=target, items=items: all(
            state.has(item, player) for item in items) and target.can_reach(state)))
    repeatable = [(completion_event(row["map_key"]), access) for row, access in sources if row["repeatable"]]
    for key in world.campaign_plan['stage_ids']:
        if not any(row['map_key'] == key for row, _ in sources):
            event = completion_event(key)
            repeatable.append((event, lambda state, event=event: state.has(event, player)))
    region = Region("Killsanity", player, multiworld)
    multiworld.regions.append(region)
    entrance = multiworld.get_region("Menu", player).connect(region)
    entrance.access_rule = lambda state: any(access(state) for _, access in sources) or any(
        state.has(event, player) and access(state) for event, access in repeatable)
    for row in plan["milestones"]:
        threshold = row["threshold"]
        location = DoomEternalLocation(player, milestone_name(threshold), row["location_id"], region)
        if row["finite_supported"]:
            location.access_rule = lambda state, threshold=threshold: sum(
                source["count"] for source, access in sources if access(state)) >= threshold
        else:
            location.progress_type = LocationProgressType.EXCLUDED
            location.access_rule = lambda state: any(
                state.has(event, player) and access(state) for event, access in repeatable)
        region.locations.append(location)

    world.location_name_to_id = {**world.location_name_to_id, **milestone_names(plan)}
    world.location_id_to_name = {code: name for name, code in world.location_name_to_id.items()}
    world.location_names = frozenset(world.location_name_to_id)
    world.location_name_groups = {**world.location_name_groups, "Everywhere": world.location_names}
